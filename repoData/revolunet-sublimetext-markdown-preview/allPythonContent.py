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
__FILENAME__ = helper
import sublime, os, pkgutil
import os.path
import re
import sys

'''
INSTALLED_DIRECTORY - The install directory name for this plugin.

For ST3
    As descriped in http://www.sublimetext.com/docs/3/packages.html this script locations is one of
    Zipped: 
        "<executable_path>/Packages/Markdown Preview.sublime-package/Markdown Preview.MarkdownPreview"
        "<data_path>/Installed Packages/Markdown Preview.sublime-package/Markdown Preview.MarkdownPreview"
    Not Zipped:
        "<data_path>/Packages/Markdown Preview/MarkdownPreview.py"

    All passable path for ST3 are abspath (tested on windows)

For ST2
    The __file__ will be '.\MarkdownPreview.pyc' that means when this script is loaded,
    Sublime Text entered the directoy of this script. So we make use of os.path.abspath()
'''
try:
    INSTALLED_DIRECTORY = re.search("[ \\\\/]Packages[\\\\/]([^\\\\/\.]+)", os.path.abspath(__file__)).group(1)
except:
    print('Warning failed to detect the install directory, defaulting to: "Markdown Preview"')
    INSTALLED_DIRECTORY = "Markdown Preview"




"""
Preload all python-markdown extensions (ST2 only)
"""

# By default sublime 2 only imports python packages from the top level of the plugin directory.
# Trying to import packages from subdirectories dynamically at a later time is NOT possible.

# This package automatically imports all packages from the extension directory
# so they are available when we need them.


def is_ST3():
    ''' check if ST3 based on python version '''
    version = sys.version_info
    if isinstance(version, tuple):
        version = version[0]
    elif getattr(version, 'major', None):
        version = version.major
    return (version >= 3)

if not is_ST3():
    packages_path = sublime.packages_path()
    extension_module = "markdown.extensions"

    for  _, package, _ in pkgutil.walk_packages("."):
        if package.startswith(extension_module):
            print ("Reloading plugin extension " + os.path.join(packages_path, INSTALLED_DIRECTORY, *package.split(".")) + ".py")
            __import__(package)

########NEW FILE########
__FILENAME__ = ssl
# Wrapper module for _ssl, providing some additional facilities
# implemented in Python.  Written by Bill Janssen.

"""\
This module provides some more Pythonic support for SSL.

Object types:

  SSLSocket -- subtype of socket.socket which does SSL over the socket

Exceptions:

  SSLError -- exception raised for I/O errors

Functions:

  cert_time_to_seconds -- convert time string used for certificate
                          notBefore and notAfter functions to integer
                          seconds past the Epoch (the time values
                          returned from time.time())

  fetch_server_certificate (HOST, PORT) -- fetch the certificate provided
                          by the server running on HOST at port PORT.  No
                          validation of the certificate is performed.

Integer constants:

SSL_ERROR_ZERO_RETURN
SSL_ERROR_WANT_READ
SSL_ERROR_WANT_WRITE
SSL_ERROR_WANT_X509_LOOKUP
SSL_ERROR_SYSCALL
SSL_ERROR_SSL
SSL_ERROR_WANT_CONNECT

SSL_ERROR_EOF
SSL_ERROR_INVALID_ERROR_CODE

The following group define certificate requirements that one side is
allowing/requiring from the other side:

CERT_NONE - no certificates from the other side are required (or will
            be looked at if provided)
CERT_OPTIONAL - certificates are not required, but if provided will be
                validated, and if validation fails, the connection will
                also fail
CERT_REQUIRED - certificates are required, and will be validated, and
                if validation fails, the connection will also fail

The following constants identify various SSL protocol variants:

PROTOCOL_SSLv2
PROTOCOL_SSLv3
PROTOCOL_SSLv23
PROTOCOL_TLSv1
"""

import textwrap

import _ssl             # if we can't import it, let the error propagate

from _ssl import SSLError
from _ssl import CERT_NONE, CERT_OPTIONAL, CERT_REQUIRED
from _ssl import PROTOCOL_SSLv3, PROTOCOL_SSLv23, PROTOCOL_TLSv1
from _ssl import RAND_status, RAND_egd, RAND_add
from _ssl import \
     SSL_ERROR_ZERO_RETURN, \
     SSL_ERROR_WANT_READ, \
     SSL_ERROR_WANT_WRITE, \
     SSL_ERROR_WANT_X509_LOOKUP, \
     SSL_ERROR_SYSCALL, \
     SSL_ERROR_SSL, \
     SSL_ERROR_WANT_CONNECT, \
     SSL_ERROR_EOF, \
     SSL_ERROR_INVALID_ERROR_CODE

from socket import socket, _fileobject, _delegate_methods
from socket import error as socket_error
from socket import getnameinfo as _getnameinfo
import base64        # for DER-to-PEM translation
import errno

class SSLSocket(socket):

    """This class implements a subtype of socket.socket that wraps
    the underlying OS socket in an SSL context when necessary, and
    provides read and write methods over that channel."""

    def __init__(self, sock, keyfile=None, certfile=None,
                 server_side=False, cert_reqs=CERT_NONE,
                 ssl_version=PROTOCOL_SSLv23, ca_certs=None,
                 do_handshake_on_connect=True,
                 suppress_ragged_eofs=True):
        socket.__init__(self, _sock=sock._sock)
        # The initializer for socket overrides the methods send(), recv(), etc.
        # in the instancce, which we don't need -- but we want to provide the
        # methods defined in SSLSocket.
        for attr in _delegate_methods:
            try:
                delattr(self, attr)
            except AttributeError:
                pass

        if certfile and not keyfile:
            keyfile = certfile
        # see if it's connected
        try:
            socket.getpeername(self)
        except socket_error, e:
            if e.errno != errno.ENOTCONN:
                raise
            # no, no connection yet
            self._sslobj = None
        else:
            # yes, create the SSL object
            self._sslobj = _ssl.sslwrap(self._sock, server_side,
                                        keyfile, certfile,
                                        cert_reqs, ssl_version, ca_certs)
            if do_handshake_on_connect:
                self.do_handshake()
        self.keyfile = keyfile
        self.certfile = certfile
        self.cert_reqs = cert_reqs
        self.ssl_version = ssl_version
        self.ca_certs = ca_certs
        self.do_handshake_on_connect = do_handshake_on_connect
        self.suppress_ragged_eofs = suppress_ragged_eofs
        self._makefile_refs = 0

    def read(self, len=1024):

        """Read up to LEN bytes and return them.
        Return zero-length string on EOF."""

        try:
            return self._sslobj.read(len)
        except SSLError, x:
            if x.args[0] == SSL_ERROR_EOF and self.suppress_ragged_eofs:
                return ''
            else:
                raise

    def write(self, data):

        """Write DATA to the underlying SSL channel.  Returns
        number of bytes of DATA actually transmitted."""

        return self._sslobj.write(data)

    def getpeercert(self, binary_form=False):

        """Returns a formatted version of the data in the
        certificate provided by the other end of the SSL channel.
        Return None if no certificate was provided, {} if a
        certificate was provided, but not validated."""

        return self._sslobj.peer_certificate(binary_form)

    def cipher(self):

        if not self._sslobj:
            return None
        else:
            return self._sslobj.cipher()

    def send(self, data, flags=0):
        if self._sslobj:
            if flags != 0:
                raise ValueError(
                    "non-zero flags not allowed in calls to send() on %s" %
                    self.__class__)
            while True:
                try:
                    v = self._sslobj.write(data)
                except SSLError, x:
                    if x.args[0] == SSL_ERROR_WANT_READ:
                        return 0
                    elif x.args[0] == SSL_ERROR_WANT_WRITE:
                        return 0
                    else:
                        raise
                else:
                    return v
        else:
            return socket.send(self, data, flags)

    def sendto(self, data, addr, flags=0):
        if self._sslobj:
            raise ValueError("sendto not allowed on instances of %s" %
                             self.__class__)
        else:
            return socket.sendto(self, data, addr, flags)

    def sendall(self, data, flags=0):
        if self._sslobj:
            if flags != 0:
                raise ValueError(
                    "non-zero flags not allowed in calls to sendall() on %s" %
                    self.__class__)
            amount = len(data)
            count = 0
            while (count < amount):
                v = self.send(data[count:])
                count += v
            return amount
        else:
            return socket.sendall(self, data, flags)

    def recv(self, buflen=1024, flags=0):
        if self._sslobj:
            if flags != 0:
                raise ValueError(
                    "non-zero flags not allowed in calls to recv() on %s" %
                    self.__class__)
            return self.read(buflen)
        else:
            return socket.recv(self, buflen, flags)

    def recv_into(self, buffer, nbytes=None, flags=0):
        if buffer and (nbytes is None):
            nbytes = len(buffer)
        elif nbytes is None:
            nbytes = 1024
        if self._sslobj:
            if flags != 0:
                raise ValueError(
                  "non-zero flags not allowed in calls to recv_into() on %s" %
                  self.__class__)
            tmp_buffer = self.read(nbytes)
            v = len(tmp_buffer)
            buffer[:v] = tmp_buffer
            return v
        else:
            return socket.recv_into(self, buffer, nbytes, flags)

    def recvfrom(self, addr, buflen=1024, flags=0):
        if self._sslobj:
            raise ValueError("recvfrom not allowed on instances of %s" %
                             self.__class__)
        else:
            return socket.recvfrom(self, addr, buflen, flags)

    def recvfrom_into(self, buffer, nbytes=None, flags=0):
        if self._sslobj:
            raise ValueError("recvfrom_into not allowed on instances of %s" %
                             self.__class__)
        else:
            return socket.recvfrom_into(self, buffer, nbytes, flags)

    def pending(self):
        if self._sslobj:
            return self._sslobj.pending()
        else:
            return 0

    def unwrap(self):
        if self._sslobj:
            s = self._sslobj.shutdown()
            self._sslobj = None
            return s
        else:
            raise ValueError("No SSL wrapper around " + str(self))

    def shutdown(self, how):
        self._sslobj = None
        socket.shutdown(self, how)

    def close(self):
        if self._makefile_refs < 1:
            self._sslobj = None
            socket.close(self)
        else:
            self._makefile_refs -= 1

    def do_handshake(self):

        """Perform a TLS/SSL handshake."""

        self._sslobj.do_handshake()

    def connect(self, addr):

        """Connects to remote ADDR, and then wraps the connection in
        an SSL channel."""

        # Here we assume that the socket is client-side, and not
        # connected at the time of the call.  We connect it, then wrap it.
        if self._sslobj:
            raise ValueError("attempt to connect already-connected SSLSocket!")
        socket.connect(self, addr)
        self._sslobj = _ssl.sslwrap(self._sock, False, self.keyfile, self.certfile,
                                    self.cert_reqs, self.ssl_version,
                                    self.ca_certs)
        if self.do_handshake_on_connect:
            self.do_handshake()

    def accept(self):

        """Accepts a new connection from a remote client, and returns
        a tuple containing that new connection wrapped with a server-side
        SSL channel, and the address of the remote client."""

        newsock, addr = socket.accept(self)
        return (SSLSocket(newsock,
                          keyfile=self.keyfile,
                          certfile=self.certfile,
                          server_side=True,
                          cert_reqs=self.cert_reqs,
                          ssl_version=self.ssl_version,
                          ca_certs=self.ca_certs,
                          do_handshake_on_connect=self.do_handshake_on_connect,
                          suppress_ragged_eofs=self.suppress_ragged_eofs),
                addr)

    def makefile(self, mode='r', bufsize=-1):

        """Make and return a file-like object that
        works with the SSL connection.  Just use the code
        from the socket module."""

        self._makefile_refs += 1
        # close=True so as to decrement the reference count when done with
        # the file-like object.
        return _fileobject(self, mode, bufsize, close=True)



def wrap_socket(sock, keyfile=None, certfile=None,
                server_side=False, cert_reqs=CERT_NONE,
                ssl_version=PROTOCOL_SSLv23, ca_certs=None,
                do_handshake_on_connect=True,
                suppress_ragged_eofs=True):

    return SSLSocket(sock, keyfile=keyfile, certfile=certfile,
                     server_side=server_side, cert_reqs=cert_reqs,
                     ssl_version=ssl_version, ca_certs=ca_certs,
                     do_handshake_on_connect=do_handshake_on_connect,
                     suppress_ragged_eofs=suppress_ragged_eofs)


# some utility functions

def cert_time_to_seconds(cert_time):

    """Takes a date-time string in standard ASN1_print form
    ("MON DAY 24HOUR:MINUTE:SEC YEAR TIMEZONE") and return
    a Python time value in seconds past the epoch."""

    import time
    return time.mktime(time.strptime(cert_time, "%b %d %H:%M:%S %Y GMT"))

PEM_HEADER = "-----BEGIN CERTIFICATE-----"
PEM_FOOTER = "-----END CERTIFICATE-----"

def DER_cert_to_PEM_cert(der_cert_bytes):

    """Takes a certificate in binary DER format and returns the
    PEM version of it as a string."""

    if hasattr(base64, 'standard_b64encode'):
        # preferred because older API gets line-length wrong
        f = base64.standard_b64encode(der_cert_bytes)
        return (PEM_HEADER + '\n' +
                textwrap.fill(f, 64) + '\n' +
                PEM_FOOTER + '\n')
    else:
        return (PEM_HEADER + '\n' +
                base64.encodestring(der_cert_bytes) +
                PEM_FOOTER + '\n')

def PEM_cert_to_DER_cert(pem_cert_string):

    """Takes a certificate in ASCII PEM format and returns the
    DER-encoded version of it as a byte sequence"""

    if not pem_cert_string.startswith(PEM_HEADER):
        raise ValueError("Invalid PEM encoding; must start with %s"
                         % PEM_HEADER)
    if not pem_cert_string.strip().endswith(PEM_FOOTER):
        raise ValueError("Invalid PEM encoding; must end with %s"
                         % PEM_FOOTER)
    d = pem_cert_string.strip()[len(PEM_HEADER):-len(PEM_FOOTER)]
    return base64.decodestring(d)

def get_server_certificate(addr, ssl_version=PROTOCOL_SSLv3, ca_certs=None):

    """Retrieve the certificate from the server at the specified address,
    and return it as a PEM-encoded string.
    If 'ca_certs' is specified, validate the server cert against it.
    If 'ssl_version' is specified, use it in the connection attempt."""

    host, port = addr
    if (ca_certs is not None):
        cert_reqs = CERT_REQUIRED
    else:
        cert_reqs = CERT_NONE
    s = wrap_socket(socket(), ssl_version=ssl_version,
                    cert_reqs=cert_reqs, ca_certs=ca_certs)
    s.connect(addr)
    dercert = s.getpeercert(True)
    s.close()
    return DER_cert_to_PEM_cert(dercert)

def get_protocol_name(protocol_code):
    if protocol_code == PROTOCOL_TLSv1:
        return "TLSv1"
    elif protocol_code == PROTOCOL_SSLv23:
        return "SSLv23"
    elif protocol_code == PROTOCOL_SSLv3:
        return "SSLv3"
    else:
        return "<unknown>"


# a replacement for the old socket.ssl function

def sslwrap_simple(sock, keyfile=None, certfile=None):

    """A replacement for the old socket.ssl function.  Designed
    for compability with Python 2.5 and earlier.  Will disappear in
    Python 3.0."""

    if hasattr(sock, "_sock"):
        sock = sock._sock

    ssl_sock = _ssl.sslwrap(sock, 0, keyfile, certfile, CERT_NONE,
                            PROTOCOL_SSLv23, None)
    try:
        sock.getpeername()
    except:
        # no, no connection yet
        pass
    else:
        # yes, do the handshake
        ssl_sock.do_handshake()

    return ssl_sock

########NEW FILE########
__FILENAME__ = blockparser
from __future__ import unicode_literals
from __future__ import absolute_import
from . import util
from . import odict

class State(list):
    """ Track the current and nested state of the parser. 
    
    This utility class is used to track the state of the BlockParser and 
    support multiple levels if nesting. It's just a simple API wrapped around
    a list. Each time a state is set, that state is appended to the end of the
    list. Each time a state is reset, that state is removed from the end of
    the list.

    Therefore, each time a state is set for a nested block, that state must be 
    reset when we back out of that level of nesting or the state could be
    corrupted.

    While all the methods of a list object are available, only the three
    defined below need be used.

    """

    def set(self, state):
        """ Set a new state. """
        self.append(state)

    def reset(self):
        """ Step back one step in nested state. """
        self.pop()

    def isstate(self, state):
        """ Test that top (current) level is of given state. """
        if len(self):
            return self[-1] == state
        else:
            return False

class BlockParser:
    """ Parse Markdown blocks into an ElementTree object. 
    
    A wrapper class that stitches the various BlockProcessors together,
    looping through them and creating an ElementTree object.
    """

    def __init__(self, markdown):
        self.blockprocessors = odict.OrderedDict()
        self.state = State()
        self.markdown = markdown

    def parseDocument(self, lines):
        """ Parse a markdown document into an ElementTree. 
        
        Given a list of lines, an ElementTree object (not just a parent Element)
        is created and the root element is passed to the parser as the parent.
        The ElementTree object is returned.
        
        This should only be called on an entire document, not pieces.

        """
        # Create a ElementTree from the lines
        self.root = util.etree.Element(self.markdown.doc_tag)
        self.parseChunk(self.root, '\n'.join(lines))
        return util.etree.ElementTree(self.root)

    def parseChunk(self, parent, text):
        """ Parse a chunk of markdown text and attach to given etree node. 
        
        While the ``text`` argument is generally assumed to contain multiple
        blocks which will be split on blank lines, it could contain only one
        block. Generally, this method would be called by extensions when
        block parsing is required. 
        
        The ``parent`` etree Element passed in is altered in place. 
        Nothing is returned.

        """
        self.parseBlocks(parent, text.split('\n\n'))

    def parseBlocks(self, parent, blocks):
        """ Process blocks of markdown text and attach to given etree node. 
        
        Given a list of ``blocks``, each blockprocessor is stepped through
        until there are no blocks left. While an extension could potentially
        call this method directly, it's generally expected to be used internally.

        This is a public method as an extension may need to add/alter additional
        BlockProcessors which call this method to recursively parse a nested
        block.

        """
        while blocks:
            for processor in self.blockprocessors.values():
                if processor.test(parent, blocks[0]):
                    if processor.run(parent, blocks) is not False:
                        # run returns True or None
                        break



########NEW FILE########
__FILENAME__ = blockprocessors
"""
CORE MARKDOWN BLOCKPARSER
===========================================================================

This parser handles basic parsing of Markdown blocks.  It doesn't concern itself
with inline elements such as **bold** or *italics*, but rather just catches
blocks, lists, quotes, etc.

The BlockParser is made up of a bunch of BlockProssors, each handling a
different type of block. Extensions may add/replace/remove BlockProcessors
as they need to alter how markdown blocks are parsed.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals
import logging
import re
from . import util
from .blockparser import BlockParser

logger =  logging.getLogger('MARKDOWN')


def build_block_parser(md_instance, **kwargs):
    """ Build the default block parser used by Markdown. """
    parser = BlockParser(md_instance)
    parser.blockprocessors['empty'] = EmptyBlockProcessor(parser)
    parser.blockprocessors['indent'] = ListIndentProcessor(parser)
    parser.blockprocessors['code'] = CodeBlockProcessor(parser)
    parser.blockprocessors['hashheader'] = HashHeaderProcessor(parser)
    parser.blockprocessors['setextheader'] = SetextHeaderProcessor(parser)
    parser.blockprocessors['hr'] = HRProcessor(parser)
    parser.blockprocessors['olist'] = OListProcessor(parser)
    parser.blockprocessors['ulist'] = UListProcessor(parser)
    parser.blockprocessors['quote'] = BlockQuoteProcessor(parser)
    parser.blockprocessors['paragraph'] = ParagraphProcessor(parser)
    return parser


class BlockProcessor:
    """ Base class for block processors. 
    
    Each subclass will provide the methods below to work with the source and
    tree. Each processor will need to define it's own ``test`` and ``run``
    methods. The ``test`` method should return True or False, to indicate
    whether the current block should be processed by this processor. If the
    test passes, the parser will call the processors ``run`` method.

    """

    def __init__(self, parser):
        self.parser = parser
        self.tab_length = parser.markdown.tab_length

    def lastChild(self, parent):
        """ Return the last child of an etree element. """
        if len(parent):
            return parent[-1]
        else:
            return None

    def detab(self, text):
        """ Remove a tab from the front of each line of the given text. """
        newtext = []
        lines = text.split('\n')
        for line in lines:
            if line.startswith(' '*self.tab_length):
                newtext.append(line[self.tab_length:])
            elif not line.strip():
                newtext.append('')
            else:
                break
        return '\n'.join(newtext), '\n'.join(lines[len(newtext):])

    def looseDetab(self, text, level=1):
        """ Remove a tab from front of lines but allowing dedented lines. """
        lines = text.split('\n')
        for i in range(len(lines)):
            if lines[i].startswith(' '*self.tab_length*level):
                lines[i] = lines[i][self.tab_length*level:]
        return '\n'.join(lines)

    def test(self, parent, block):
        """ Test for block type. Must be overridden by subclasses. 
        
        As the parser loops through processors, it will call the ``test`` method
        on each to determine if the given block of text is of that type. This
        method must return a boolean ``True`` or ``False``. The actual method of
        testing is left to the needs of that particular block type. It could 
        be as simple as ``block.startswith(some_string)`` or a complex regular
        expression. As the block type may be different depending on the parent
        of the block (i.e. inside a list), the parent etree element is also 
        provided and may be used as part of the test.

        Keywords:
        
        * ``parent``: A etree element which will be the parent of the block.
        * ``block``: A block of text from the source which has been split at 
            blank lines.
        """
        pass

    def run(self, parent, blocks):
        """ Run processor. Must be overridden by subclasses. 
        
        When the parser determines the appropriate type of a block, the parser
        will call the corresponding processor's ``run`` method. This method
        should parse the individual lines of the block and append them to
        the etree. 

        Note that both the ``parent`` and ``etree`` keywords are pointers
        to instances of the objects which should be edited in place. Each
        processor must make changes to the existing objects as there is no
        mechanism to return new/different objects to replace them.

        This means that this method should be adding SubElements or adding text
        to the parent, and should remove (``pop``) or add (``insert``) items to
        the list of blocks.

        Keywords:

        * ``parent``: A etree element which is the parent of the current block.
        * ``blocks``: A list of all remaining blocks of the document.
        """
        pass


class ListIndentProcessor(BlockProcessor):
    """ Process children of list items. 
    
    Example:
        * a list item
            process this part

            or this part

    """

    ITEM_TYPES = ['li']
    LIST_TYPES = ['ul', 'ol']

    def __init__(self, *args):
        BlockProcessor.__init__(self, *args)
        self.INDENT_RE = re.compile(r'^(([ ]{%s})+)'% self.tab_length)

    def test(self, parent, block):
        return block.startswith(' '*self.tab_length) and \
                not self.parser.state.isstate('detabbed') and  \
                (parent.tag in self.ITEM_TYPES or \
                    (len(parent) and parent[-1] and \
                        (parent[-1].tag in self.LIST_TYPES)
                    )
                )

    def run(self, parent, blocks):
        block = blocks.pop(0)
        level, sibling = self.get_level(parent, block)
        block = self.looseDetab(block, level)

        self.parser.state.set('detabbed')
        if parent.tag in self.ITEM_TYPES:
            # It's possible that this parent has a 'ul' or 'ol' child list
            # with a member.  If that is the case, then that should be the
            # parent.  This is intended to catch the edge case of an indented 
            # list whose first member was parsed previous to this point
            # see OListProcessor
            if len(parent) and parent[-1].tag in self.LIST_TYPES:
                self.parser.parseBlocks(parent[-1], [block])
            else:
                # The parent is already a li. Just parse the child block.
                self.parser.parseBlocks(parent, [block])
        elif sibling.tag in self.ITEM_TYPES:
            # The sibling is a li. Use it as parent.
            self.parser.parseBlocks(sibling, [block])
        elif len(sibling) and sibling[-1].tag in self.ITEM_TYPES:
            # The parent is a list (``ol`` or ``ul``) which has children.
            # Assume the last child li is the parent of this block.
            if sibling[-1].text:
                # If the parent li has text, that text needs to be moved to a p
                # The p must be 'inserted' at beginning of list in the event
                # that other children already exist i.e.; a nested sublist.
                p = util.etree.Element('p')
                p.text = sibling[-1].text
                sibling[-1].text = ''
                sibling[-1].insert(0, p)
            self.parser.parseChunk(sibling[-1], block)
        else:
            self.create_item(sibling, block)
        self.parser.state.reset()

    def create_item(self, parent, block):
        """ Create a new li and parse the block with it as the parent. """
        li = util.etree.SubElement(parent, 'li')
        self.parser.parseBlocks(li, [block])
 
    def get_level(self, parent, block):
        """ Get level of indent based on list level. """
        # Get indent level
        m = self.INDENT_RE.match(block)
        if m:
            indent_level = len(m.group(1))/self.tab_length
        else:
            indent_level = 0
        if self.parser.state.isstate('list'):
            # We're in a tightlist - so we already are at correct parent.
            level = 1
        else:
            # We're in a looselist - so we need to find parent.
            level = 0
        # Step through children of tree to find matching indent level.
        while indent_level > level:
            child = self.lastChild(parent)
            if child and (child.tag in self.LIST_TYPES or child.tag in self.ITEM_TYPES):
                if child.tag in self.LIST_TYPES:
                    level += 1
                parent = child
            else:
                # No more child levels. If we're short of indent_level,
                # we have a code block. So we stop here.
                break
        return level, parent


class CodeBlockProcessor(BlockProcessor):
    """ Process code blocks. """

    def test(self, parent, block):
        return block.startswith(' '*self.tab_length)
    
    def run(self, parent, blocks):
        sibling = self.lastChild(parent)
        block = blocks.pop(0)
        theRest = ''
        if sibling and sibling.tag == "pre" and len(sibling) \
                    and sibling[0].tag == "code":
            # The previous block was a code block. As blank lines do not start
            # new code blocks, append this block to the previous, adding back
            # linebreaks removed from the split into a list.
            code = sibling[0]
            block, theRest = self.detab(block)
            code.text = util.AtomicString('%s\n%s\n' % (code.text, block.rstrip()))
        else:
            # This is a new codeblock. Create the elements and insert text.
            pre = util.etree.SubElement(parent, 'pre')
            code = util.etree.SubElement(pre, 'code')
            block, theRest = self.detab(block)
            code.text = util.AtomicString('%s\n' % block.rstrip())
        if theRest:
            # This block contained unindented line(s) after the first indented 
            # line. Insert these lines as the first block of the master blocks
            # list for future processing.
            blocks.insert(0, theRest)


class BlockQuoteProcessor(BlockProcessor):

    RE = re.compile(r'(^|\n)[ ]{0,3}>[ ]?(.*)')

    def test(self, parent, block):
        return bool(self.RE.search(block))

    def run(self, parent, blocks):
        block = blocks.pop(0)
        m = self.RE.search(block)
        if m:
            before = block[:m.start()] # Lines before blockquote
            # Pass lines before blockquote in recursively for parsing forst.
            self.parser.parseBlocks(parent, [before])
            # Remove ``> `` from begining of each line.
            block = '\n'.join([self.clean(line) for line in 
                            block[m.start():].split('\n')])
        sibling = self.lastChild(parent)
        if sibling and sibling.tag == "blockquote":
            # Previous block was a blockquote so set that as this blocks parent
            quote = sibling
        else:
            # This is a new blockquote. Create a new parent element.
            quote = util.etree.SubElement(parent, 'blockquote')
        # Recursively parse block with blockquote as parent.
        # change parser state so blockquotes embedded in lists use p tags
        self.parser.state.set('blockquote')
        self.parser.parseChunk(quote, block)
        self.parser.state.reset()

    def clean(self, line):
        """ Remove ``>`` from beginning of a line. """
        m = self.RE.match(line)
        if line.strip() == ">":
            return ""
        elif m:
            return m.group(2)
        else:
            return line

class OListProcessor(BlockProcessor):
    """ Process ordered list blocks. """

    TAG = 'ol'
    # Detect an item (``1. item``). ``group(1)`` contains contents of item.
    RE = re.compile(r'^[ ]{0,3}\d+\.[ ]+(.*)')
    # Detect items on secondary lines. they can be of either list type.
    CHILD_RE = re.compile(r'^[ ]{0,3}((\d+\.)|[*+-])[ ]+(.*)')
    # Detect indented (nested) items of either type
    INDENT_RE = re.compile(r'^[ ]{4,7}((\d+\.)|[*+-])[ ]+.*')
    # The integer (python string) with which the lists starts (default=1)
    # Eg: If list is intialized as)
    #   3. Item
    # The ol tag will get starts="3" attribute
    STARTSWITH = '1'
    # List of allowed sibling tags. 
    SIBLING_TAGS = ['ol', 'ul']

    def test(self, parent, block):
        return bool(self.RE.match(block))

    def run(self, parent, blocks):
        # Check fr multiple items in one block.
        items = self.get_items(blocks.pop(0))
        sibling = self.lastChild(parent)

        if sibling and sibling.tag in self.SIBLING_TAGS:
            # Previous block was a list item, so set that as parent
            lst = sibling
            # make sure previous item is in a p- if the item has text, then it
            # it isn't in a p
            if lst[-1].text: 
                # since it's possible there are other children for this sibling,
                # we can't just SubElement the p, we need to insert it as the 
                # first item
                p = util.etree.Element('p')
                p.text = lst[-1].text
                lst[-1].text = ''
                lst[-1].insert(0, p)
            # if the last item has a tail, then the tail needs to be put in a p
            # likely only when a header is not followed by a blank line
            lch = self.lastChild(lst[-1])
            if lch is not None and lch.tail:
                p = util.etree.SubElement(lst[-1], 'p')
                p.text = lch.tail.lstrip()
                lch.tail = ''

            # parse first block differently as it gets wrapped in a p.
            li = util.etree.SubElement(lst, 'li')
            self.parser.state.set('looselist')
            firstitem = items.pop(0)
            self.parser.parseBlocks(li, [firstitem])
            self.parser.state.reset()
        elif parent.tag in ['ol', 'ul']:
            # this catches the edge case of a multi-item indented list whose 
            # first item is in a blank parent-list item:
            # * * subitem1
            #     * subitem2
            # see also ListIndentProcessor
            lst = parent
        else:
            # This is a new list so create parent with appropriate tag.
            lst = util.etree.SubElement(parent, self.TAG)
            # Check if a custom start integer is set
            if not self.parser.markdown.lazy_ol and self.STARTSWITH !='1':
                lst.attrib['start'] = self.STARTSWITH

        self.parser.state.set('list')
        # Loop through items in block, recursively parsing each with the
        # appropriate parent.
        for item in items:
            if item.startswith(' '*self.tab_length):
                # Item is indented. Parse with last item as parent
                self.parser.parseBlocks(lst[-1], [item])
            else:
                # New item. Create li and parse with it as parent
                li = util.etree.SubElement(lst, 'li')
                self.parser.parseBlocks(li, [item])
        self.parser.state.reset()

    def get_items(self, block):
        """ Break a block into list items. """
        items = []
        for line in block.split('\n'):
            m = self.CHILD_RE.match(line)
            if m:
                # This is a new list item
                # Check first item for the start index
                if not items and self.TAG=='ol':
                    # Detect the integer value of first list item
                    INTEGER_RE = re.compile('(\d+)')
                    self.STARTSWITH = INTEGER_RE.match(m.group(1)).group()
                # Append to the list
                items.append(m.group(3))
            elif self.INDENT_RE.match(line):
                # This is an indented (possibly nested) item.
                if items[-1].startswith(' '*self.tab_length):
                    # Previous item was indented. Append to that item.
                    items[-1] = '%s\n%s' % (items[-1], line)
                else:
                    items.append(line)
            else:
                # This is another line of previous item. Append to that item.
                items[-1] = '%s\n%s' % (items[-1], line)
        return items


class UListProcessor(OListProcessor):
    """ Process unordered list blocks. """

    TAG = 'ul'
    RE = re.compile(r'^[ ]{0,3}[*+-][ ]+(.*)')


class HashHeaderProcessor(BlockProcessor):
    """ Process Hash Headers. """

    # Detect a header at start of any line in block
    RE = re.compile(r'(^|\n)(?P<level>#{1,6})(?P<header>.*?)#*(\n|$)')

    def test(self, parent, block):
        return bool(self.RE.search(block))

    def run(self, parent, blocks):
        block = blocks.pop(0)
        m = self.RE.search(block)
        if m:
            before = block[:m.start()] # All lines before header
            after = block[m.end():]    # All lines after header
            if before:
                # As the header was not the first line of the block and the
                # lines before the header must be parsed first,
                # recursively parse this lines as a block.
                self.parser.parseBlocks(parent, [before])
            # Create header using named groups from RE
            h = util.etree.SubElement(parent, 'h%d' % len(m.group('level')))
            h.text = m.group('header').strip()
            if after:
                # Insert remaining lines as first block for future parsing.
                blocks.insert(0, after)
        else:
            # This should never happen, but just in case...
            logger.warn("We've got a problem header: %r" % block)


class SetextHeaderProcessor(BlockProcessor):
    """ Process Setext-style Headers. """

    # Detect Setext-style header. Must be first 2 lines of block.
    RE = re.compile(r'^.*?\n[=-]+[ ]*(\n|$)', re.MULTILINE)

    def test(self, parent, block):
        return bool(self.RE.match(block))

    def run(self, parent, blocks):
        lines = blocks.pop(0).split('\n')
        # Determine level. ``=`` is 1 and ``-`` is 2.
        if lines[1].startswith('='):
            level = 1
        else:
            level = 2
        h = util.etree.SubElement(parent, 'h%d' % level)
        h.text = lines[0].strip()
        if len(lines) > 2:
            # Block contains additional lines. Add to  master blocks for later.
            blocks.insert(0, '\n'.join(lines[2:]))


class HRProcessor(BlockProcessor):
    """ Process Horizontal Rules. """

    RE = r'^[ ]{0,3}((-+[ ]{0,2}){3,}|(_+[ ]{0,2}){3,}|(\*+[ ]{0,2}){3,})[ ]*'
    # Detect hr on any line of a block.
    SEARCH_RE = re.compile(RE, re.MULTILINE)

    def test(self, parent, block):
        m = self.SEARCH_RE.search(block)
        # No atomic grouping in python so we simulate it here for performance.
        # The regex only matches what would be in the atomic group - the HR.
        # Then check if we are at end of block or if next char is a newline.
        if m and (m.end() == len(block) or block[m.end()] == '\n'):
            # Save match object on class instance so we can use it later.
            self.match = m
            return True
        return False

    def run(self, parent, blocks):
        block = blocks.pop(0)
        # Check for lines in block before hr.
        prelines = block[:self.match.start()].rstrip('\n')
        if prelines:
            # Recursively parse lines before hr so they get parsed first.
            self.parser.parseBlocks(parent, [prelines])
        # create hr
        util.etree.SubElement(parent, 'hr')
        # check for lines in block after hr.
        postlines = block[self.match.end():].lstrip('\n')
        if postlines:
            # Add lines after hr to master blocks for later parsing.
            blocks.insert(0, postlines)



class EmptyBlockProcessor(BlockProcessor):
    """ Process blocks that are empty or start with an empty line. """

    def test(self, parent, block):
        return not block or block.startswith('\n')

    def run(self, parent, blocks):
        block = blocks.pop(0)
        filler = '\n\n'
        if block:
            # Starts with empty line
            # Only replace a single line.
            filler = '\n'
            # Save the rest for later.
            theRest = block[1:]
            if theRest:
                # Add remaining lines to master blocks for later.
                blocks.insert(0, theRest)
        sibling = self.lastChild(parent)
        if sibling and sibling.tag == 'pre' and len(sibling) and sibling[0].tag == 'code':
            # Last block is a codeblock. Append to preserve whitespace.
            sibling[0].text = util.AtomicString('%s%s' % (sibling[0].text, filler))


class ParagraphProcessor(BlockProcessor):
    """ Process Paragraph blocks. """

    def test(self, parent, block):
        return True

    def run(self, parent, blocks):
        block = blocks.pop(0)
        if block.strip():
            # Not a blank block. Add to parent, otherwise throw it away.
            if self.parser.state.isstate('list'):
                # The parent is a tight-list.
                #
                # Check for any children. This will likely only happen in a 
                # tight-list when a header isn't followed by a blank line.
                # For example:
                #
                #     * # Header
                #     Line 2 of list item - not part of header.
                sibling = self.lastChild(parent)
                if sibling is not None:
                    # Insetrt after sibling.
                    if sibling.tail:
                        sibling.tail = '%s\n%s' % (sibling.tail, block)
                    else:
                        sibling.tail = '\n%s' % block
                else:
                    # Append to parent.text
                    if parent.text:
                        parent.text = '%s\n%s' % (parent.text, block)
                    else:
                        parent.text = block.lstrip()
            else:
                # Create a regular paragraph
                p = util.etree.SubElement(parent, 'p')
                p.text = block.lstrip()

########NEW FILE########
__FILENAME__ = abbr
'''
Abbreviation Extension for Python-Markdown
==========================================

This extension adds abbreviation handling to Python-Markdown.

Simple Usage:

    >>> import markdown
    >>> text = """
    ... Some text with an ABBR and a REF. Ignore REFERENCE and ref.
    ...
    ... *[ABBR]: Abbreviation
    ... *[REF]: Abbreviation Reference
    ... """
    >>> print markdown.markdown(text, ['abbr'])
    <p>Some text with an <abbr title="Abbreviation">ABBR</abbr> and a <abbr title="Abbreviation Reference">REF</abbr>. Ignore REFERENCE and ref.</p>

Copyright 2007-2008
* [Waylan Limberg](http://achinghead.com/)
* [Seemant Kulleen](http://www.kulleen.org/)
	

'''

from __future__ import absolute_import
from __future__ import unicode_literals
from . import Extension
from ..preprocessors import Preprocessor
from ..inlinepatterns import Pattern
from ..util import etree
import re

# Global Vars
ABBR_REF_RE = re.compile(r'[*]\[(?P<abbr>[^\]]*)\][ ]?:\s*(?P<title>.*)')

class AbbrExtension(Extension):
    """ Abbreviation Extension for Python-Markdown. """

    def extendMarkdown(self, md, md_globals):
        """ Insert AbbrPreprocessor before ReferencePreprocessor. """
        md.preprocessors.add('abbr', AbbrPreprocessor(md), '<reference')
        
           
class AbbrPreprocessor(Preprocessor):
    """ Abbreviation Preprocessor - parse text for abbr references. """

    def run(self, lines):
        '''
        Find and remove all Abbreviation references from the text.
        Each reference is set as a new AbbrPattern in the markdown instance.
        
        '''
        new_text = []
        for line in lines:
            m = ABBR_REF_RE.match(line)
            if m:
                abbr = m.group('abbr').strip()
                title = m.group('title').strip()
                self.markdown.inlinePatterns['abbr-%s'%abbr] = \
                    AbbrPattern(self._generate_pattern(abbr), title)
            else:
                new_text.append(line)
        return new_text
    
    def _generate_pattern(self, text):
        '''
        Given a string, returns an regex pattern to match that string. 
        
        'HTML' -> r'(?P<abbr>[H][T][M][L])' 
        
        Note: we force each char as a literal match (in brackets) as we don't 
        know what they will be beforehand.

        '''
        chars = list(text)
        for i in range(len(chars)):
            chars[i] = r'[%s]' % chars[i]
        return r'(?P<abbr>\b%s\b)' % (r''.join(chars))


class AbbrPattern(Pattern):
    """ Abbreviation inline pattern. """

    def __init__(self, pattern, title):
        super(AbbrPattern, self).__init__(pattern)
        self.title = title

    def handleMatch(self, m):
        abbr = etree.Element('abbr')
        abbr.text = m.group('abbr')
        abbr.set('title', self.title)
        return abbr

def makeExtension(configs=None):
    return AbbrExtension(configs=configs)

########NEW FILE########
__FILENAME__ = admonition
"""
Admonition extension for Python-Markdown
========================================

Adds rST-style admonitions. Inspired by [rST][] feature with the same name.

The syntax is (followed by an indented block with the contents):
    !!! [type] [optional explicit title]

Where `type` is used as a CSS class name of the div. If not present, `title`
defaults to the capitalized `type`, so "note" -> "Note".

rST suggests the following `types`, but you're free to use whatever you want:
    attention, caution, danger, error, hint, important, note, tip, warning


A simple example:
    !!! note
        This is the first line inside the box.

Outputs:
    <div class="admonition note">
    <p class="admonition-title">Note</p>
    <p>This is the first line inside the box</p>
    </div>

You can also specify the title and CSS class of the admonition:
    !!! custom "Did you know?"
        Another line here.

Outputs:
    <div class="admonition custom">
    <p class="admonition-title">Did you know?</p>
    <p>Another line here.</p>
    </div>

[rST]: http://docutils.sourceforge.net/docs/ref/rst/directives.html#specific-admonitions

By [Tiago Serafim](http://www.tiagoserafim.com/).

"""

from __future__ import absolute_import
from __future__ import unicode_literals
from . import Extension
from ..blockprocessors import BlockProcessor
from ..util import etree
import re


class AdmonitionExtension(Extension):
    """ Admonition extension for Python-Markdown. """

    def extendMarkdown(self, md, md_globals):
        """ Add Admonition to Markdown instance. """
        md.registerExtension(self)

        md.parser.blockprocessors.add('admonition',
                                      AdmonitionProcessor(md.parser),
                                      '_begin')


class AdmonitionProcessor(BlockProcessor):

    CLASSNAME = 'admonition'
    CLASSNAME_TITLE = 'admonition-title'
    RE = re.compile(r'(?:^|\n)!!!\ ?([\w\-]+)(?:\ "(.*?)")?')

    def test(self, parent, block):
        sibling = self.lastChild(parent)
        return self.RE.search(block) or \
            (block.startswith(' ' * self.tab_length) and sibling and \
                sibling.get('class', '').find(self.CLASSNAME) != -1)

    def run(self, parent, blocks):
        sibling = self.lastChild(parent)
        block = blocks.pop(0)
        m = self.RE.search(block)

        if m:
            block = block[m.end() + 1:]  # removes the first line

        block, theRest = self.detab(block)

        if m:
            klass, title = self.get_class_and_title(m)
            div = etree.SubElement(parent, 'div')
            div.set('class', '%s %s' % (self.CLASSNAME, klass))
            if title:
                p = etree.SubElement(div, 'p')
                p.text = title
                p.set('class', self.CLASSNAME_TITLE)
        else:
            div = sibling

        self.parser.parseChunk(div, block)

        if theRest:
            # This block contained unindented line(s) after the first indented
            # line. Insert these lines as the first block of the master blocks
            # list for future processing.
            blocks.insert(0, theRest)

    def get_class_and_title(self, match):
        klass, title = match.group(1).lower(), match.group(2)
        if title is None:
            # no title was provided, use the capitalized classname as title
            # e.g.: `!!! note` will render `<p class="admonition-title">Note</p>`
            title = klass.capitalize()
        elif title == '':
            # an explicit blank title should not be rendered
            # e.g.: `!!! warning ""` will *not* render `p` with a title
            title = None
        return klass, title


def makeExtension(configs={}):
    return AdmonitionExtension(configs=configs)

########NEW FILE########
__FILENAME__ = attr_list
"""
Attribute List Extension for Python-Markdown
============================================

Adds attribute list syntax. Inspired by 
[maruku](http://maruku.rubyforge.org/proposal.html#attribute_lists)'s
feature of the same name.

Copyright 2011 [Waylan Limberg](http://achinghead.com/).

Contact: markdown@freewisdom.org

License: BSD (see ../LICENSE.md for details) 

Dependencies:
* [Python 2.4+](http://python.org)
* [Markdown 2.1+](http://packages.python.org/Markdown/)

"""

from __future__ import absolute_import
from __future__ import unicode_literals
from . import Extension
from ..treeprocessors import Treeprocessor
from ..util import isBlockLevel
import re

try:
    Scanner = re.Scanner
except AttributeError:
    # must be on Python 2.4
    from sre import Scanner

def _handle_double_quote(s, t):
    k, v = t.split('=')
    return k, v.strip('"')

def _handle_single_quote(s, t):
    k, v = t.split('=')
    return k, v.strip("'")

def _handle_key_value(s, t): 
    return t.split('=')

def _handle_word(s, t):
    if t.startswith('.'):
        return '.', t[1:]
    if t.startswith('#'):
        return 'id', t[1:]
    return t, t

_scanner = Scanner([
    (r'[^ ]+=".*?"', _handle_double_quote),
    (r"[^ ]+='.*?'", _handle_single_quote),
    (r'[^ ]+=[^ ]*', _handle_key_value),
    (r'[^ ]+', _handle_word),
    (r' ', None)
])

def get_attrs(str):
    """ Parse attribute list and return a list of attribute tuples. """
    return _scanner.scan(str)[0]

def isheader(elem):
    return elem.tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']

class AttrListTreeprocessor(Treeprocessor):
    
    BASE_RE = r'\{\:?([^\}]*)\}'
    HEADER_RE = re.compile(r'[ ]*%s[ ]*$' % BASE_RE)
    BLOCK_RE = re.compile(r'\n[ ]*%s[ ]*$' % BASE_RE)
    INLINE_RE = re.compile(r'^%s' % BASE_RE)
    NAME_RE = re.compile(r'[^A-Z_a-z\u00c0-\u00d6\u00d8-\u00f6\u00f8-\u02ff\u0370-\u037d'
                         r'\u037f-\u1fff\u200c-\u200d\u2070-\u218f\u2c00-\u2fef'
                         r'\u3001-\ud7ff\uf900-\ufdcf\ufdf0-\ufffd'
                         r'\:\-\.0-9\u00b7\u0300-\u036f\u203f-\u2040]+')

    def run(self, doc):
        for elem in doc.getiterator():
            if isBlockLevel(elem.tag):
                # Block level: check for attrs on last line of text
                RE = self.BLOCK_RE
                if isheader(elem):
                    # header: check for attrs at end of line
                    RE = self.HEADER_RE
                if len(elem) and elem[-1].tail:
                    # has children. Get from tail of last child
                    m = RE.search(elem[-1].tail)
                    if m:
                        self.assign_attrs(elem, m.group(1))
                        elem[-1].tail = elem[-1].tail[:m.start()]
                        if isheader(elem):
                            # clean up trailing #s
                            elem[-1].tail = elem[-1].tail.rstrip('#').rstrip()
                elif elem.text:
                    # no children. Get from text.
                    m = RE.search(elem.text)
                    if m:
                        self.assign_attrs(elem, m.group(1))
                        elem.text = elem.text[:m.start()]
                        if isheader(elem):
                            # clean up trailing #s
                            elem.text = elem.text.rstrip('#').rstrip()
            else:
                # inline: check for attrs at start of tail
                if elem.tail:
                    m = self.INLINE_RE.match(elem.tail)
                    if m:
                        self.assign_attrs(elem, m.group(1))
                        elem.tail = elem.tail[m.end():]

    def assign_attrs(self, elem, attrs):
        """ Assign attrs to element. """
        for k, v in get_attrs(attrs):
            if k == '.':
                # add to class
                cls = elem.get('class')
                if cls:
                    elem.set('class', '%s %s' % (cls, v))
                else:
                    elem.set('class', v)
            else:
                # assign attr k with v
                elem.set(self.sanitize_name(k), v)

    def sanitize_name(self, name):
        """
        Sanitize name as 'an XML Name, minus the ":"'.
        See http://www.w3.org/TR/REC-xml-names/#NT-NCName
        """
        return self.NAME_RE.sub('_', name)


class AttrListExtension(Extension):
    def extendMarkdown(self, md, md_globals):
        md.treeprocessors.add('attr_list', AttrListTreeprocessor(md), '>prettify')


def makeExtension(configs={}):
    return AttrListExtension(configs=configs)

########NEW FILE########
__FILENAME__ = codehilite
"""
CodeHilite Extension for Python-Markdown
========================================

Adds code/syntax highlighting to standard Python-Markdown code blocks.

Copyright 2006-2008 [Waylan Limberg](http://achinghead.com/).

Project website: <http://packages.python.org/Markdown/extensions/code_hilite.html>
Contact: markdown@freewisdom.org

License: BSD (see ../LICENSE.md for details)

Dependencies:
* [Python 2.3+](http://python.org/)
* [Markdown 2.0+](http://packages.python.org/Markdown/)
* [Pygments](http://pygments.org/)

"""

from __future__ import absolute_import
from __future__ import unicode_literals
from . import Extension
from ..treeprocessors import Treeprocessor
import warnings
try:
    from pygments import highlight
    from pygments.lexers import get_lexer_by_name, guess_lexer, TextLexer
    from pygments.formatters import HtmlFormatter
    pygments = True
except ImportError:
    pygments = False

# ------------------ The Main CodeHilite Class ----------------------
class CodeHilite(object):
    """
    Determine language of source code, and pass it into the pygments hilighter.

    Basic Usage:
        >>> code = CodeHilite(src = 'some text')
        >>> html = code.hilite()

    * src: Source string or any object with a .readline attribute.

    * linenums: (Boolean) Set line numbering to 'on' (True), 'off' (False) or 'auto'(None). 
    Set to 'auto' by default.

    * guess_lang: (Boolean) Turn language auto-detection 'on' or 'off' (on by default).

    * css_class: Set class name of wrapper div ('codehilite' by default).

    Low Level Usage:
        >>> code = CodeHilite()
        >>> code.src = 'some text' # String or anything with a .readline attr.
        >>> code.linenos = True  # True or False; Turns line numbering on or of.
        >>> html = code.hilite()

    """

    def __init__(self, src=None, linenums=None, guess_lang=True,
                css_class="codehilite", lang=None, style='default',
                noclasses=False, tab_length=4):
        self.src = src
        self.lang = lang
        self.linenums = linenums
        self.guess_lang = guess_lang
        self.css_class = css_class
        self.style = style
        self.noclasses = noclasses
        self.tab_length = tab_length

    def hilite(self):
        """
        Pass code to the [Pygments](http://pygments.pocoo.org/) highliter with
        optional line numbers. The output should then be styled with css to
        your liking. No styles are applied by default - only styling hooks
        (i.e.: <span class="k">).

        returns : A string of html.

        """

        self.src = self.src.strip('\n')

        if self.lang is None:
            self._getLang()

        if pygments:
            try:
                lexer = get_lexer_by_name(self.lang)
            except ValueError:
                try:
                    if self.guess_lang:
                        lexer = guess_lexer(self.src)
                    else:
                        lexer = TextLexer()
                except ValueError:
                    lexer = TextLexer()
            formatter = HtmlFormatter(linenos=self.linenums,
                                      cssclass=self.css_class,
                                      style=self.style,
                                      noclasses=self.noclasses)
            return highlight(self.src, lexer, formatter)
        else:
            # just escape and build markup usable by JS highlighting libs
            txt = self.src.replace('&', '&amp;')
            txt = txt.replace('<', '&lt;')
            txt = txt.replace('>', '&gt;')
            txt = txt.replace('"', '&quot;')
            classes = []
            if self.lang:
                classes.append('language-%s' % self.lang)
            if self.linenums:
                classes.append('linenums')
            class_str = ''
            if classes:
                class_str = ' class="%s"' % ' '.join(classes) 
            return '<pre class="%s"><code%s>%s</code></pre>\n'% \
                        (self.css_class, class_str, txt)

    def _getLang(self):
        """
        Determines language of a code block from shebang line and whether said
        line should be removed or left in place. If the sheband line contains a
        path (even a single /) then it is assumed to be a real shebang line and
        left alone. However, if no path is given (e.i.: #!python or :::python)
        then it is assumed to be a mock shebang for language identifitation of a
        code fragment and removed from the code block prior to processing for
        code highlighting. When a mock shebang (e.i: #!python) is found, line
        numbering is turned on. When colons are found in place of a shebang
        (e.i.: :::python), line numbering is left in the current state - off
        by default.

        """

        import re

        #split text into lines
        lines = self.src.split("\n")
        #pull first line to examine
        fl = lines.pop(0)

        c = re.compile(r'''
            (?:(?:^::+)|(?P<shebang>^[#]!))	# Shebang or 2 or more colons.
            (?P<path>(?:/\w+)*[/ ])?        # Zero or 1 path
            (?P<lang>[\w+-]*)               # The language
            ''',  re.VERBOSE)
        # search first line for shebang
        m = c.search(fl)
        if m:
            # we have a match
            try:
                self.lang = m.group('lang').lower()
            except IndexError:
                self.lang = None
            if m.group('path'):
                # path exists - restore first line
                lines.insert(0, fl)
            if self.linenums is None and m.group('shebang'):
                # Overridable and Shebang exists - use line numbers
                self.linenums = True
        else:
            # No match
            lines.insert(0, fl)

        self.src = "\n".join(lines).strip("\n")



# ------------------ The Markdown Extension -------------------------------
class HiliteTreeprocessor(Treeprocessor):
    """ Hilight source code in code blocks. """

    def run(self, root):
        """ Find code blocks and store in htmlStash. """
        blocks = root.getiterator('pre')
        for block in blocks:
            children = block.getchildren()
            if len(children) == 1 and children[0].tag == 'code':
                code = CodeHilite(children[0].text,
                            linenums=self.config['linenums'],
                            guess_lang=self.config['guess_lang'],
                            css_class=self.config['css_class'],
                            style=self.config['pygments_style'],
                            noclasses=self.config['noclasses'],
                            tab_length=self.markdown.tab_length)
                placeholder = self.markdown.htmlStash.store(code.hilite(),
                                                            safe=True)
                # Clear codeblock in etree instance
                block.clear()
                # Change to p element which will later
                # be removed when inserting raw html
                block.tag = 'p'
                block.text = placeholder


class CodeHiliteExtension(Extension):
    """ Add source code hilighting to markdown codeblocks. """

    def __init__(self, configs):
        # define default configs
        self.config = {
            'linenums': [None, "Use lines numbers. True=yes, False=no, None=auto"],
            'force_linenos' : [False, "Depreciated! Use 'linenums' instead. Force line numbers - Default: False"],
            'guess_lang' : [True, "Automatic language detection - Default: True"],
            'css_class' : ["codehilite",
                           "Set class name for wrapper <div> - Default: codehilite"],
            'pygments_style' : ['default', 'Pygments HTML Formatter Style (Colorscheme) - Default: default'],
            'noclasses': [False, 'Use inline styles instead of CSS classes - Default false']
            }

        # Override defaults with user settings
        for key, value in configs:
            # convert strings to booleans
            if value == 'True': value = True
            if value == 'False': value = False
            if value == 'None': value = None

            if key == 'force_linenos':
                warnings.warn('The "force_linenos" config setting'
                    ' to the CodeHilite extension is deprecrecated.'
                    ' Use "linenums" instead.', PendingDeprecationWarning)
                if value:
                    # Carry 'force_linenos' over to new 'linenos'.
                    self.setConfig('linenums', True)

            self.setConfig(key, value)

    def extendMarkdown(self, md, md_globals):
        """ Add HilitePostprocessor to Markdown instance. """
        hiliter = HiliteTreeprocessor(md)
        hiliter.config = self.getConfigs()
        md.treeprocessors.add("hilite", hiliter, "<inline")

        md.registerExtension(self)


def makeExtension(configs={}):
  return CodeHiliteExtension(configs=configs)


########NEW FILE########
__FILENAME__ = def_list
"""
Definition List Extension for Python-Markdown
=============================================

Added parsing of Definition Lists to Python-Markdown.

A simple example:

    Apple
    :   Pomaceous fruit of plants of the genus Malus in 
        the family Rosaceae.
    :   An american computer company.

    Orange
    :   The fruit of an evergreen tree of the genus Citrus.

Copyright 2008 - [Waylan Limberg](http://achinghead.com)

"""

from __future__ import absolute_import
from __future__ import unicode_literals
from . import Extension
from ..blockprocessors import BlockProcessor, ListIndentProcessor
from ..util import etree
import re


class DefListProcessor(BlockProcessor):
    """ Process Definition Lists. """

    RE = re.compile(r'(^|\n)[ ]{0,3}:[ ]{1,3}(.*?)(\n|$)')
    NO_INDENT_RE = re.compile(r'^[ ]{0,3}[^ :]')

    def test(self, parent, block):
        return bool(self.RE.search(block))

    def run(self, parent, blocks):

        raw_block = blocks.pop(0)
        m = self.RE.search(raw_block)
        terms = [l.strip() for l in raw_block[:m.start()].split('\n') if l.strip()]
        block = raw_block[m.end():]
        no_indent = self.NO_INDENT_RE.match(block)
        if no_indent:
            d, theRest = (block, None)
        else:
            d, theRest = self.detab(block)
        if d:
            d = '%s\n%s' % (m.group(2), d)
        else:
            d = m.group(2)
        sibling = self.lastChild(parent)
        if not terms and sibling is None:
            # This is not a definition item. Most likely a paragraph that 
            # starts with a colon at the begining of a document or list.
            blocks.insert(0, raw_block)
            return False
        if not terms and sibling.tag == 'p':
            # The previous paragraph contains the terms
            state = 'looselist'
            terms = sibling.text.split('\n')
            parent.remove(sibling)
            # Aquire new sibling
            sibling = self.lastChild(parent)
        else:
            state = 'list'

        if sibling and sibling.tag == 'dl':
            # This is another item on an existing list
            dl = sibling
            if len(dl) and dl[-1].tag == 'dd' and len(dl[-1]):
                state = 'looselist'
        else:
            # This is a new list
            dl = etree.SubElement(parent, 'dl')
        # Add terms
        for term in terms:
            dt = etree.SubElement(dl, 'dt')
            dt.text = term
        # Add definition
        self.parser.state.set(state)
        dd = etree.SubElement(dl, 'dd')
        self.parser.parseBlocks(dd, [d])
        self.parser.state.reset()

        if theRest:
            blocks.insert(0, theRest)

class DefListIndentProcessor(ListIndentProcessor):
    """ Process indented children of definition list items. """

    ITEM_TYPES = ['dd']
    LIST_TYPES = ['dl']

    def create_item(self, parent, block):
        """ Create a new dd and parse the block with it as the parent. """
        dd = etree.SubElement(parent, 'dd')
        self.parser.parseBlocks(dd, [block])
 


class DefListExtension(Extension):
    """ Add definition lists to Markdown. """

    def extendMarkdown(self, md, md_globals):
        """ Add an instance of DefListProcessor to BlockParser. """
        md.parser.blockprocessors.add('defindent',
                                      DefListIndentProcessor(md.parser),
                                      '>indent')
        md.parser.blockprocessors.add('deflist', 
                                      DefListProcessor(md.parser),
                                      '>ulist')


def makeExtension(configs={}):
    return DefListExtension(configs=configs)


########NEW FILE########
__FILENAME__ = extra
"""
Python-Markdown Extra Extension
===============================

A compilation of various Python-Markdown extensions that imitates
[PHP Markdown Extra](http://michelf.com/projects/php-markdown/extra/).

Note that each of the individual extensions still need to be available
on your PYTHONPATH. This extension simply wraps them all up as a 
convenience so that only one extension needs to be listed when
initiating Markdown. See the documentation for each individual
extension for specifics about that extension.

In the event that one or more of the supported extensions are not 
available for import, Markdown will issue a warning and simply continue 
without that extension. 

There may be additional extensions that are distributed with 
Python-Markdown that are not included here in Extra. Those extensions
are not part of PHP Markdown Extra, and therefore, not part of
Python-Markdown Extra. If you really would like Extra to include
additional extensions, we suggest creating your own clone of Extra
under a differant name. You could also edit the `extensions` global 
variable defined below, but be aware that such changes may be lost 
when you upgrade to any future version of Python-Markdown.

"""

from __future__ import absolute_import
from __future__ import unicode_literals
from . import Extension

extensions = ['smart_strong',
              'fenced_code',
              'footnotes',
              'attr_list',
              'def_list',
              'tables',
              'abbr',
              ]
              

class ExtraExtension(Extension):
    """ Add various extensions to Markdown class."""

    def extendMarkdown(self, md, md_globals):
        """ Register extension instances. """
        md.registerExtensions(extensions, self.config)
        if not md.safeMode:
            # Turn on processing of markdown text within raw html
            md.preprocessors['html_block'].markdown_in_raw = True

def makeExtension(configs={}):
    return ExtraExtension(configs=dict(configs))

########NEW FILE########
__FILENAME__ = fenced_code
"""
Fenced Code Extension for Python Markdown
=========================================

This extension adds Fenced Code Blocks to Python-Markdown.

    >>> import markdown
    >>> text = '''
    ... A paragraph before a fenced code block:
    ...
    ... ~~~
    ... Fenced code block
    ... ~~~
    ... '''
    >>> html = markdown.markdown(text, extensions=['fenced_code'])
    >>> print html
    <p>A paragraph before a fenced code block:</p>
    <pre><code>Fenced code block
    </code></pre>

Works with safe_mode also (we check this because we are using the HtmlStash):

    >>> print markdown.markdown(text, extensions=['fenced_code'], safe_mode='replace')
    <p>A paragraph before a fenced code block:</p>
    <pre><code>Fenced code block
    </code></pre>

Include tilde's in a code block and wrap with blank lines:

    >>> text = '''
    ... ~~~~~~~~
    ...
    ... ~~~~
    ... ~~~~~~~~'''
    >>> print markdown.markdown(text, extensions=['fenced_code'])
    <pre><code>
    ~~~~
    </code></pre>

Language tags:

    >>> text = '''
    ... ~~~~{.python}
    ... # Some python code
    ... ~~~~'''
    >>> print markdown.markdown(text, extensions=['fenced_code'])
    <pre><code class="python"># Some python code
    </code></pre>

Optionally backticks instead of tildes as per how github's code block markdown is identified:

    >>> text = '''
    ... `````
    ... # Arbitrary code
    ... ~~~~~ # these tildes will not close the block
    ... `````'''
    >>> print markdown.markdown(text, extensions=['fenced_code'])
    <pre><code># Arbitrary code
    ~~~~~ # these tildes will not close the block
    </code></pre>

Copyright 2007-2008 [Waylan Limberg](http://achinghead.com/).

Project website: <http://packages.python.org/Markdown/extensions/fenced_code_blocks.html>
Contact: markdown@freewisdom.org

License: BSD (see ../docs/LICENSE for details)

Dependencies:
* [Python 2.4+](http://python.org)
* [Markdown 2.0+](http://packages.python.org/Markdown/)
* [Pygments (optional)](http://pygments.org)

"""

from __future__ import absolute_import
from __future__ import unicode_literals
from . import Extension
from ..preprocessors import Preprocessor
from .codehilite import CodeHilite, CodeHiliteExtension
import re

# Global vars
FENCED_BLOCK_RE = re.compile( \
    r'(?P<fence>^(?:~{3,}|`{3,}))[ ]*(\{?\.?(?P<lang>[a-zA-Z0-9_+-]*)\}?)?[ ]*\n(?P<code>.*?)(?<=\n)(?P=fence)[ ]*$',
    re.MULTILINE|re.DOTALL
    )
CODE_WRAP = '<pre><code%s>%s</code></pre>'
LANG_TAG = ' class="%s"'

class FencedCodeExtension(Extension):

    def extendMarkdown(self, md, md_globals):
        """ Add FencedBlockPreprocessor to the Markdown instance. """
        md.registerExtension(self)

        md.preprocessors.add('fenced_code_block',
                                 FencedBlockPreprocessor(md),
                                 ">normalize_whitespace")


class FencedBlockPreprocessor(Preprocessor):

    def __init__(self, md):
        super(FencedBlockPreprocessor, self).__init__(md)

        self.checked_for_codehilite = False
        self.codehilite_conf = {}

    def run(self, lines):
        """ Match and store Fenced Code Blocks in the HtmlStash. """

        # Check for code hilite extension
        if not self.checked_for_codehilite:
            for ext in self.markdown.registeredExtensions:
                if isinstance(ext, CodeHiliteExtension):
                    self.codehilite_conf = ext.config
                    break

            self.checked_for_codehilite = True

        text = "\n".join(lines)
        while 1:
            m = FENCED_BLOCK_RE.search(text)
            if m:
                lang = ''
                if m.group('lang'):
                    lang = LANG_TAG % m.group('lang')

                # If config is not empty, then the codehighlite extension
                # is enabled, so we call it to highlite the code
                if self.codehilite_conf:
                    highliter = CodeHilite(m.group('code'),
                            linenums=self.codehilite_conf['linenums'][0],
                            guess_lang=self.codehilite_conf['guess_lang'][0],
                            css_class=self.codehilite_conf['css_class'][0],
                            style=self.codehilite_conf['pygments_style'][0],
                            lang=(m.group('lang') or None),
                            noclasses=self.codehilite_conf['noclasses'][0])

                    code = highliter.hilite()
                else:
                    code = CODE_WRAP % (lang, self._escape(m.group('code')))

                placeholder = self.markdown.htmlStash.store(code, safe=True)
                text = '%s\n%s\n%s'% (text[:m.start()], placeholder, text[m.end():])
            else:
                break
        return text.split("\n")

    def _escape(self, txt):
        """ basic html escaping """
        txt = txt.replace('&', '&amp;')
        txt = txt.replace('<', '&lt;')
        txt = txt.replace('>', '&gt;')
        txt = txt.replace('"', '&quot;')
        return txt


def makeExtension(configs=None):
    return FencedCodeExtension(configs=configs)

########NEW FILE########
__FILENAME__ = footnotes
"""
========================= FOOTNOTES =================================

This section adds footnote handling to markdown.  It can be used as
an example for extending python-markdown with relatively complex
functionality.  While in this case the extension is included inside
the module itself, it could just as easily be added from outside the
module.  Not that all markdown classes above are ignorant about
footnotes.  All footnote functionality is provided separately and
then added to the markdown instance at the run time.

Footnote functionality is attached by calling extendMarkdown()
method of FootnoteExtension.  The method also registers the
extension to allow it's state to be reset by a call to reset()
method.

Example:
    Footnotes[^1] have a label[^label] and a definition[^!DEF].

    [^1]: This is a footnote
    [^label]: A footnote on "label"
    [^!DEF]: The footnote for definition

"""

from __future__ import absolute_import
from __future__ import unicode_literals
from . import Extension
from ..preprocessors import Preprocessor
from ..inlinepatterns import Pattern
from ..treeprocessors import Treeprocessor
from ..postprocessors import Postprocessor
from ..util import etree, text_type
from ..odict import OrderedDict
import re

FN_BACKLINK_TEXT = "zz1337820767766393qq"
NBSP_PLACEHOLDER =  "qq3936677670287331zz"
DEF_RE = re.compile(r'[ ]{0,3}\[\^([^\]]*)\]:\s*(.*)')
TABBED_RE = re.compile(r'((\t)|(    ))(.*)')

class FootnoteExtension(Extension):
    """ Footnote Extension. """

    def __init__ (self, configs):
        """ Setup configs. """
        self.config = {'PLACE_MARKER':
                       ["///Footnotes Go Here///",
                        "The text string that marks where the footnotes go"],
                       'UNIQUE_IDS':
                       [False,
                        "Avoid name collisions across "
                        "multiple calls to reset()."],
                       "BACKLINK_TEXT":
                       ["&#8617;",
                        "The text string that links from the footnote to the reader's place."]
                       }

        for key, value in configs:
            self.config[key][0] = value

        # In multiple invocations, emit links that don't get tangled.
        self.unique_prefix = 0

        self.reset()

    def extendMarkdown(self, md, md_globals):
        """ Add pieces to Markdown. """
        md.registerExtension(self)
        self.parser = md.parser
        self.md = md
        self.sep = ':'
        if self.md.output_format in ['html5', 'xhtml5']:
            self.sep = '-'
        # Insert a preprocessor before ReferencePreprocessor
        md.preprocessors.add("footnote", FootnotePreprocessor(self),
                             "<reference")
        # Insert an inline pattern before ImageReferencePattern
        FOOTNOTE_RE = r'\[\^([^\]]*)\]' # blah blah [^1] blah
        md.inlinePatterns.add("footnote", FootnotePattern(FOOTNOTE_RE, self),
                              "<reference")
        # Insert a tree-processor that would actually add the footnote div
        # This must be before all other treeprocessors (i.e., inline and 
        # codehilite) so they can run on the the contents of the div.
        md.treeprocessors.add("footnote", FootnoteTreeprocessor(self),
                                 "_begin")
        # Insert a postprocessor after amp_substitute oricessor
        md.postprocessors.add("footnote", FootnotePostprocessor(self),
                                  ">amp_substitute")

    def reset(self):
        """ Clear the footnotes on reset, and prepare for a distinct document. """
        self.footnotes = OrderedDict()
        self.unique_prefix += 1

    def findFootnotesPlaceholder(self, root):
        """ Return ElementTree Element that contains Footnote placeholder. """
        def finder(element):
            for child in element:
                if child.text:
                    if child.text.find(self.getConfig("PLACE_MARKER")) > -1:
                        return child, element, True
                if child.tail:
                    if child.tail.find(self.getConfig("PLACE_MARKER")) > -1:
                        return child, element, False
                finder(child)
            return None
                
        res = finder(root)
        return res

    def setFootnote(self, id, text):
        """ Store a footnote for later retrieval. """
        self.footnotes[id] = text

    def makeFootnoteId(self, id):
        """ Return footnote link id. """
        if self.getConfig("UNIQUE_IDS"):
            return 'fn%s%d-%s' % (self.sep, self.unique_prefix, id)
        else:
            return 'fn%s%s' % (self.sep, id)

    def makeFootnoteRefId(self, id):
        """ Return footnote back-link id. """
        if self.getConfig("UNIQUE_IDS"):
            return 'fnref%s%d-%s' % (self.sep, self.unique_prefix, id)
        else:
            return 'fnref%s%s' % (self.sep, id)

    def makeFootnotesDiv(self, root):
        """ Return div of footnotes as et Element. """

        if not list(self.footnotes.keys()):
            return None

        div = etree.Element("div")
        div.set('class', 'footnote')
        etree.SubElement(div, "hr")
        ol = etree.SubElement(div, "ol")

        for id in self.footnotes.keys():
            li = etree.SubElement(ol, "li")
            li.set("id", self.makeFootnoteId(id))
            self.parser.parseChunk(li, self.footnotes[id])
            backlink = etree.Element("a")
            backlink.set("href", "#" + self.makeFootnoteRefId(id))
            if self.md.output_format not in ['html5', 'xhtml5']:
                backlink.set("rev", "footnote") # Invalid in HTML5
            backlink.set("class", "footnote-backref")
            backlink.set("title", "Jump back to footnote %d in the text" % \
                            (self.footnotes.index(id)+1))
            backlink.text = FN_BACKLINK_TEXT

            if li.getchildren():
                node = li[-1]
                if node.tag == "p":
                    node.text = node.text + NBSP_PLACEHOLDER
                    node.append(backlink)
                else:
                    p = etree.SubElement(li, "p")
                    p.append(backlink)
        return div


class FootnotePreprocessor(Preprocessor):
    """ Find all footnote references and store for later use. """

    def __init__ (self, footnotes):
        self.footnotes = footnotes

    def run(self, lines):
        """
        Loop through lines and find, set, and remove footnote definitions.

        Keywords:

        * lines: A list of lines of text

        Return: A list of lines of text with footnote definitions removed.

        """
        newlines = []
        i = 0
        while True:
            m = DEF_RE.match(lines[i])
            if m:
                fn, _i = self.detectTabbed(lines[i+1:])
                fn.insert(0, m.group(2))
                i += _i-1 # skip past footnote
                self.footnotes.setFootnote(m.group(1), "\n".join(fn))
            else:
                newlines.append(lines[i])
            if len(lines) > i+1:
                i += 1
            else:
                break
        return newlines

    def detectTabbed(self, lines):
        """ Find indented text and remove indent before further proccesing.

        Keyword arguments:

        * lines: an array of strings

        Returns: a list of post processed items and the index of last line.

        """
        items = []
        blank_line = False # have we encountered a blank line yet?
        i = 0 # to keep track of where we are

        def detab(line):
            match = TABBED_RE.match(line)
            if match:
               return match.group(4)

        for line in lines:
            if line.strip(): # Non-blank line
                detabbed_line = detab(line)
                if detabbed_line:
                    items.append(detabbed_line)
                    i += 1
                    continue
                elif not blank_line and not DEF_RE.match(line):
                    # not tabbed but still part of first par.
                    items.append(line)
                    i += 1
                    continue
                else:
                    return items, i+1

            else: # Blank line: _maybe_ we are done.
                blank_line = True
                i += 1 # advance

                # Find the next non-blank line
                for j in range(i, len(lines)):
                    if lines[j].strip():
                        next_line = lines[j]; break
                else:
                    break # There is no more text; we are done.

                # Check if the next non-blank line is tabbed
                if detab(next_line): # Yes, more work to do.
                    items.append("")
                    continue
                else:
                    break # No, we are done.
        else:
            i += 1

        return items, i


class FootnotePattern(Pattern):
    """ InlinePattern for footnote markers in a document's body text. """

    def __init__(self, pattern, footnotes):
        super(FootnotePattern, self).__init__(pattern)
        self.footnotes = footnotes

    def handleMatch(self, m):
        id = m.group(2)
        if id in self.footnotes.footnotes.keys():
            sup = etree.Element("sup")
            a = etree.SubElement(sup, "a")
            sup.set('id', self.footnotes.makeFootnoteRefId(id))
            a.set('href', '#' + self.footnotes.makeFootnoteId(id))
            if self.footnotes.md.output_format not in ['html5', 'xhtml5']:
                a.set('rel', 'footnote') # invalid in HTML5
            a.set('class', 'footnote-ref')
            a.text = text_type(self.footnotes.footnotes.index(id) + 1)
            return sup
        else:
            return None


class FootnoteTreeprocessor(Treeprocessor):
    """ Build and append footnote div to end of document. """

    def __init__ (self, footnotes):
        self.footnotes = footnotes

    def run(self, root):
        footnotesDiv = self.footnotes.makeFootnotesDiv(root)
        if footnotesDiv:
            result = self.footnotes.findFootnotesPlaceholder(root)
            if result:
                child, parent, isText = result
                ind = parent.getchildren().index(child)
                if isText:
                    parent.remove(child)
                    parent.insert(ind, footnotesDiv)
                else:
                    parent.insert(ind + 1, footnotesDiv)
                    child.tail = None
            else:
                root.append(footnotesDiv)

class FootnotePostprocessor(Postprocessor):
    """ Replace placeholders with html entities. """
    def __init__(self, footnotes):
        self.footnotes = footnotes

    def run(self, text):
        text = text.replace(FN_BACKLINK_TEXT, self.footnotes.getConfig("BACKLINK_TEXT"))
        return text.replace(NBSP_PLACEHOLDER, "&#160;")

def makeExtension(configs=[]):
    """ Return an instance of the FootnoteExtension """
    return FootnoteExtension(configs=configs)


########NEW FILE########
__FILENAME__ = headerid
"""
HeaderID Extension for Python-Markdown
======================================

Auto-generate id attributes for HTML headers.

Basic usage:

    >>> import markdown
    >>> text = "# Some Header #"
    >>> md = markdown.markdown(text, ['headerid'])
    >>> print md
    <h1 id="some-header">Some Header</h1>

All header IDs are unique:

    >>> text = '''
    ... #Header
    ... #Header
    ... #Header'''
    >>> md = markdown.markdown(text, ['headerid'])
    >>> print md
    <h1 id="header">Header</h1>
    <h1 id="header_1">Header</h1>
    <h1 id="header_2">Header</h1>

To fit within a html template's hierarchy, set the header base level:

    >>> text = '''
    ... #Some Header
    ... ## Next Level'''
    >>> md = markdown.markdown(text, ['headerid(level=3)'])
    >>> print md
    <h3 id="some-header">Some Header</h3>
    <h4 id="next-level">Next Level</h4>

Works with inline markup.

    >>> text = '#Some *Header* with [markup](http://example.com).'
    >>> md = markdown.markdown(text, ['headerid'])
    >>> print md
    <h1 id="some-header-with-markup">Some <em>Header</em> with <a href="http://example.com">markup</a>.</h1>

Turn off auto generated IDs:

    >>> text = '''
    ... # Some Header
    ... # Another Header'''
    >>> md = markdown.markdown(text, ['headerid(forceid=False)'])
    >>> print md
    <h1>Some Header</h1>
    <h1>Another Header</h1>

Use with MetaData extension:

    >>> text = '''header_level: 2
    ... header_forceid: Off
    ...
    ... # A Header'''
    >>> md = markdown.markdown(text, ['headerid', 'meta'])
    >>> print md
    <h2>A Header</h2>

Copyright 2007-2011 [Waylan Limberg](http://achinghead.com/).

Project website: <http://packages.python.org/Markdown/extensions/header_id.html>
Contact: markdown@freewisdom.org

License: BSD (see ../docs/LICENSE for details) 

Dependencies:
* [Python 2.3+](http://python.org)
* [Markdown 2.0+](http://packages.python.org/Markdown/)

"""

from __future__ import absolute_import
from __future__ import unicode_literals
from . import Extension
from ..treeprocessors import Treeprocessor
import re
import logging
from string import punctuation

logger = logging.getLogger('MARKDOWN')


DISALLOW_RE = re.compile(r'([\s{0}]+)'.format(re.escape(punctuation)))
IDCOUNT_RE = re.compile(r'^(.*)_([0-9]+)$')


def slugify(value, separator):
    """ Slugify a string, to make it URL friendly. """
    return re.sub(DISALLOW_RE, separator, value.lower()).strip(separator)


def unique(id, ids):
    """ Ensure id is unique in set of ids. Append '_1', '_2'... if not """
    while id in ids or not id:
        m = IDCOUNT_RE.match(id)
        if m:
            id = '%s_%d'% (m.group(1), int(m.group(2))+1)
        else:
            id = '%s_%d'% (id, 1)
    ids.add(id)
    return id


def itertext(elem):
    """ Loop through all children and return text only. 
    
    Reimplements method of same name added to ElementTree in Python 2.7
    
    """
    if elem.text:
        yield elem.text
    for e in elem:
        for s in itertext(e):
            yield s
        if e.tail:
            yield e.tail


class HeaderIdTreeprocessor(Treeprocessor):
    """ Assign IDs to headers. """

    IDs = set()

    def run(self, doc):
        start_level, force_id = self._get_meta()
        slugify = self.config['slugify']
        sep = self.config['separator']
        for elem in doc.getiterator():
            if elem.tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                if force_id:
                    if "id" in elem.attrib:
                        id = elem.get('id')
                    else:
                        id = slugify(''.join(itertext(elem)), sep)
                    elem.set('id', unique(id, self.IDs))
                if start_level:
                    level = int(elem.tag[-1]) + start_level
                    if level > 6:
                        level = 6
                    elem.tag = 'h%d' % level


    def _get_meta(self):
        """ Return meta data suported by this ext as a tuple """
        level = int(self.config['level']) - 1
        force = self._str2bool(self.config['forceid'])
        if hasattr(self.md, 'Meta'):
            if 'header_level' in self.md.Meta:
                level = int(self.md.Meta['header_level'][0]) - 1
            if 'header_forceid' in self.md.Meta: 
                force = self._str2bool(self.md.Meta['header_forceid'][0])
        return level, force

    def _str2bool(self, s, default=False):
        """ Convert a string to a booleen value. """
        s = str(s)
        if s.lower() in ['0', 'f', 'false', 'off', 'no', 'n']:
            return False
        elif s.lower() in ['1', 't', 'true', 'on', 'yes', 'y']:
            return True
        return default


class HeaderIdExtension(Extension):
    def __init__(self, configs):
        # set defaults
        self.config = {
                'level' : ['1', 'Base level for headers.'],
                'forceid' : ['True', 'Force all headers to have an id.'],
                'separator' : ['-', 'Word separator.'],
                'slugify' : [slugify, 'Callable to generate anchors'], 
            }

        for key, value in configs:
            self.setConfig(key, value)

    def extendMarkdown(self, md, md_globals):
        md.registerExtension(self)
        self.processor = HeaderIdTreeprocessor()
        self.processor.md = md
        self.processor.config = self.getConfigs()
        if 'attr_list' in md.treeprocessors.keys():
            # insert after attr_list treeprocessor
            md.treeprocessors.add('headerid', self.processor, '>attr_list')
        else:
            # insert after 'prettify' treeprocessor.
            md.treeprocessors.add('headerid', self.processor, '>prettify')

    def reset(self):
        self.processor.IDs = set()


def makeExtension(configs=None):
    return HeaderIdExtension(configs=configs)

########NEW FILE########
__FILENAME__ = meta
"""
Meta Data Extension for Python-Markdown
=======================================

This extension adds Meta Data handling to markdown.

Basic Usage:

    >>> import markdown
    >>> text = '''Title: A Test Doc.
    ... Author: Waylan Limberg
    ...         John Doe
    ... Blank_Data:
    ...
    ... The body. This is paragraph one.
    ... '''
    >>> md = markdown.Markdown(['meta'])
    >>> print md.convert(text)
    <p>The body. This is paragraph one.</p>
    >>> print md.Meta
    {u'blank_data': [u''], u'author': [u'Waylan Limberg', u'John Doe'], u'title': [u'A Test Doc.']}

Make sure text without Meta Data still works (markdown < 1.6b returns a <p>).

    >>> text = '    Some Code - not extra lines of meta data.'
    >>> md = markdown.Markdown(['meta'])
    >>> print md.convert(text)
    <pre><code>Some Code - not extra lines of meta data.
    </code></pre>
    >>> md.Meta
    {}

Copyright 2007-2008 [Waylan Limberg](http://achinghead.com).

Project website: <http://packages.python.org/Markdown/meta_data.html>
Contact: markdown@freewisdom.org

License: BSD (see ../LICENSE.md for details)

"""

from __future__ import absolute_import
from __future__ import unicode_literals
from . import Extension
from ..preprocessors import Preprocessor
import re

# Global Vars
META_RE = re.compile(r'^[ ]{0,3}(?P<key>[A-Za-z0-9_-]+):\s*(?P<value>.*)')
META_MORE_RE = re.compile(r'^[ ]{4,}(?P<value>.*)')

class MetaExtension (Extension):
    """ Meta-Data extension for Python-Markdown. """

    def extendMarkdown(self, md, md_globals):
        """ Add MetaPreprocessor to Markdown instance. """

        md.preprocessors.add("meta", MetaPreprocessor(md), "_begin")


class MetaPreprocessor(Preprocessor):
    """ Get Meta-Data. """

    def run(self, lines):
        """ Parse Meta-Data and store in Markdown.Meta. """
        meta = {}
        key = None
        while 1:
            line = lines.pop(0)
            if line.strip() == '':
                break # blank line - done
            m1 = META_RE.match(line)
            if m1:
                key = m1.group('key').lower().strip()
                value = m1.group('value').strip()
                try:
                    meta[key].append(value)
                except KeyError:
                    meta[key] = [value]
            else:
                m2 = META_MORE_RE.match(line)
                if m2 and key:
                    # Add another line to existing key
                    meta[key].append(m2.group('value').strip())
                else:
                    lines.insert(0, line)
                    break # no meta data - done
        self.markdown.Meta = meta
        return lines
        

def makeExtension(configs={}):
    return MetaExtension(configs=configs)

########NEW FILE########
__FILENAME__ = nl2br
"""
NL2BR Extension
===============

A Python-Markdown extension to treat newlines as hard breaks; like
GitHub-flavored Markdown does.

Usage:

    >>> import markdown
    >>> print markdown.markdown('line 1\\nline 2', extensions=['nl2br'])
    <p>line 1<br />
    line 2</p>

Copyright 2011 [Brian Neal](http://deathofagremmie.com/)

Dependencies:
* [Python 2.4+](http://python.org)
* [Markdown 2.1+](http://packages.python.org/Markdown/)

"""

from __future__ import absolute_import
from __future__ import unicode_literals
from . import Extension
from ..inlinepatterns import SubstituteTagPattern

BR_RE = r'\n'

class Nl2BrExtension(Extension):

    def extendMarkdown(self, md, md_globals):
        br_tag = SubstituteTagPattern(BR_RE, 'br')
        md.inlinePatterns.add('nl', br_tag, '_end')


def makeExtension(configs=None):
    return Nl2BrExtension(configs)

########NEW FILE########
__FILENAME__ = sane_lists
"""
Sane List Extension for Python-Markdown
=======================================

Modify the behavior of Lists in Python-Markdown t act in a sane manor.

In standard Markdown sytex, the following would constitute a single 
ordered list. However, with this extension, the output would include 
two lists, the first an ordered list and the second and unordered list.

    1. ordered
    2. list

    * unordered
    * list

Copyright 2011 - [Waylan Limberg](http://achinghead.com)

"""

from __future__ import absolute_import
from __future__ import unicode_literals
from . import Extension
from ..blockprocessors import OListProcessor, UListProcessor
import re


class SaneOListProcessor(OListProcessor):
    
    CHILD_RE = re.compile(r'^[ ]{0,3}((\d+\.))[ ]+(.*)')
    SIBLING_TAGS = ['ol']


class SaneUListProcessor(UListProcessor):
    
    CHILD_RE = re.compile(r'^[ ]{0,3}(([*+-]))[ ]+(.*)')
    SIBLING_TAGS = ['ul']


class SaneListExtension(Extension):
    """ Add sane lists to Markdown. """

    def extendMarkdown(self, md, md_globals):
        """ Override existing Processors. """
        md.parser.blockprocessors['olist'] = SaneOListProcessor(md.parser)
        md.parser.blockprocessors['ulist'] = SaneUListProcessor(md.parser)


def makeExtension(configs={}):
    return SaneListExtension(configs=configs)


########NEW FILE########
__FILENAME__ = smart_strong
'''
Smart_Strong Extension for Python-Markdown
==========================================

This extention adds smarter handling of double underscores within words.

Simple Usage:

    >>> import markdown
    >>> print markdown.markdown('Text with double__underscore__words.',
    ...                   extensions=['smart_strong'])
    <p>Text with double__underscore__words.</p>
    >>> print markdown.markdown('__Strong__ still works.',
    ...                   extensions=['smart_strong'])
    <p><strong>Strong</strong> still works.</p>
    >>> print markdown.markdown('__this__works__too__.',
    ...                   extensions=['smart_strong'])
    <p><strong>this__works__too</strong>.</p>

Copyright 2011
[Waylan Limberg](http://achinghead.com)

'''

from __future__ import absolute_import
from __future__ import unicode_literals
from . import Extension
from ..inlinepatterns import SimpleTagPattern

SMART_STRONG_RE = r'(?<!\w)(_{2})(?!_)(.+?)(?<!_)\2(?!\w)'
STRONG_RE = r'(\*{2})(.+?)\2'

class SmartEmphasisExtension(Extension):
    """ Add smart_emphasis extension to Markdown class."""

    def extendMarkdown(self, md, md_globals):
        """ Modify inline patterns. """
        md.inlinePatterns['strong'] = SimpleTagPattern(STRONG_RE, 'strong')
        md.inlinePatterns.add('strong2', SimpleTagPattern(SMART_STRONG_RE, 'strong'), '>emphasis2')

def makeExtension(configs={}):
    return SmartEmphasisExtension(configs=dict(configs))

########NEW FILE########
__FILENAME__ = tables
"""
Tables Extension for Python-Markdown
====================================

Added parsing of tables to Python-Markdown.

A simple example:

    First Header  | Second Header
    ------------- | -------------
    Content Cell  | Content Cell
    Content Cell  | Content Cell

Copyright 2009 - [Waylan Limberg](http://achinghead.com)
"""

from __future__ import absolute_import
from __future__ import unicode_literals
from . import Extension
from ..blockprocessors import BlockProcessor
from ..util import etree

class TableProcessor(BlockProcessor):
    """ Process Tables. """

    def test(self, parent, block):
        rows = block.split('\n')
        return (len(rows) > 2 and '|' in rows[0] and 
                '|' in rows[1] and '-' in rows[1] and 
                rows[1].strip()[0] in ['|', ':', '-'])

    def run(self, parent, blocks):
        """ Parse a table block and build table. """
        block = blocks.pop(0).split('\n')
        header = block[0].strip()
        seperator = block[1].strip()
        rows = block[2:]
        # Get format type (bordered by pipes or not)
        border = False
        if header.startswith('|'):
            border = True
        # Get alignment of columns
        align = []
        for c in self._split_row(seperator, border):
            if c.startswith(':') and c.endswith(':'):
                align.append('center')
            elif c.startswith(':'):
                align.append('left')
            elif c.endswith(':'):
                align.append('right')
            else:
                align.append(None)
        # Build table
        table = etree.SubElement(parent, 'table')
        thead = etree.SubElement(table, 'thead')
        self._build_row(header, thead, align, border)
        tbody = etree.SubElement(table, 'tbody')
        for row in rows:
            self._build_row(row.strip(), tbody, align, border)

    def _build_row(self, row, parent, align, border):
        """ Given a row of text, build table cells. """
        tr = etree.SubElement(parent, 'tr')
        tag = 'td'
        if parent.tag == 'thead':
            tag = 'th'
        cells = self._split_row(row, border)
        # We use align here rather than cells to ensure every row 
        # contains the same number of columns.
        for i, a in enumerate(align):
            c = etree.SubElement(tr, tag)
            try:
                c.text = cells[i].strip()
            except IndexError:
                c.text = ""
            if a:
                c.set('align', a)

    def _split_row(self, row, border):
        """ split a row of text into list of cells. """
        if border:
            if row.startswith('|'):
                row = row[1:]
            if row.endswith('|'):
                row = row[:-1]
        return row.split('|')


class TableExtension(Extension):
    """ Add tables to Markdown. """

    def extendMarkdown(self, md, md_globals):
        """ Add an instance of TableProcessor to BlockParser. """
        md.parser.blockprocessors.add('table', 
                                      TableProcessor(md.parser),
                                      '<hashheader')


def makeExtension(configs={}):
    return TableExtension(configs=configs)

########NEW FILE########
__FILENAME__ = toc
"""
Table of Contents Extension for Python-Markdown
* * *

(c) 2008 [Jack Miller](http://codezen.org)

Dependencies:
* [Markdown 2.1+](http://packages.python.org/Markdown/)

"""

from __future__ import absolute_import
from __future__ import unicode_literals
from . import Extension
from ..treeprocessors import Treeprocessor
from ..util import etree
from .headerid import slugify, unique, itertext
import re


def order_toc_list(toc_list):
    """Given an unsorted list with errors and skips, return a nested one.
    [{'level': 1}, {'level': 2}]
    =>
    [{'level': 1, 'children': [{'level': 2, 'children': []}]}]
    
    A wrong list is also converted:
    [{'level': 2}, {'level': 1}]
    =>
    [{'level': 2, 'children': []}, {'level': 1, 'children': []}]
    """
    
    def build_correct(remaining_list, prev_elements=[{'level': 1000}]):
        
        if not remaining_list:
            return [], []
        
        current = remaining_list.pop(0)
        if not 'children' in current.keys():
            current['children'] = []
        
        if not prev_elements:
            # This happens for instance with [8, 1, 1], ie. when some
            # header level is outside a scope. We treat it as a
            # top-level
            next_elements, children = build_correct(remaining_list, [current])
            current['children'].append(children)
            return [current] + next_elements, []
        
        prev_element = prev_elements.pop()
        children = []
        next_elements = []
        # Is current part of the child list or next list?
        if current['level'] > prev_element['level']:
            #print "%d is a child of %d" % (current['level'], prev_element['level'])
            prev_elements.append(prev_element)
            prev_elements.append(current)
            prev_element['children'].append(current)
            next_elements2, children2 = build_correct(remaining_list, prev_elements)
            children += children2
            next_elements += next_elements2
        else:
            #print "%d is ancestor of %d" % (current['level'], prev_element['level'])
            if not prev_elements:
                #print "No previous elements, so appending to the next set"
                next_elements.append(current)
                prev_elements = [current]
                next_elements2, children2 = build_correct(remaining_list, prev_elements)
                current['children'].extend(children2)
            else:
                #print "Previous elements, comparing to those first"
                remaining_list.insert(0, current)
                next_elements2, children2 = build_correct(remaining_list, prev_elements)
                children.extend(children2)
            next_elements += next_elements2
        
        return next_elements, children
    
    ordered_list, __ = build_correct(toc_list)
    return ordered_list


class TocTreeprocessor(Treeprocessor):
    
    # Iterator wrapper to get parent and child all at once
    def iterparent(self, root):
        for parent in root.getiterator():
            for child in parent:
                yield parent, child
    
    def add_anchor(self, c, elem_id): #@ReservedAssignment
        if self.use_anchors:
            anchor = etree.Element("a")
            anchor.text = c.text
            anchor.attrib["href"] = "#" + elem_id
            anchor.attrib["class"] = "toclink"
            c.text = ""
            for elem in c.getchildren():
                anchor.append(elem)
                c.remove(elem)
            c.append(anchor)
    
    def build_toc_etree(self, div, toc_list):
        # Add title to the div
        if self.config["title"]:
            header = etree.SubElement(div, "span")
            header.attrib["class"] = "toctitle"
            header.text = self.config["title"]

        def build_etree_ul(toc_list, parent):
            ul = etree.SubElement(parent, "ul")
            for item in toc_list:
                # List item link, to be inserted into the toc div
                li = etree.SubElement(ul, "li")
                link = etree.SubElement(li, "a")
                link.text = item.get('name', '')
                link.attrib["href"] = '#' + item.get('id', '')
                if item['children']:
                    build_etree_ul(item['children'], li)
            return ul
        
        return build_etree_ul(toc_list, div)
        
    def run(self, doc):

        div = etree.Element("div")
        div.attrib["class"] = "toc"
        header_rgx = re.compile("[Hh][123456]")
        
        self.use_anchors = self.config["anchorlink"] in [1, '1', True, 'True', 'true']
        
        # Get a list of id attributes
        used_ids = set()
        for c in doc.getiterator():
            if "id" in c.attrib:
                used_ids.add(c.attrib["id"])

        toc_list = []
        marker_found = False
        for (p, c) in self.iterparent(doc):
            text = ''.join(itertext(c)).strip()
            if not text:
                continue

            # To keep the output from screwing up the
            # validation by putting a <div> inside of a <p>
            # we actually replace the <p> in its entirety.
            # We do not allow the marker inside a header as that
            # would causes an enless loop of placing a new TOC 
            # inside previously generated TOC.
            if c.text and c.text.strip() == self.config["marker"] and \
               not header_rgx.match(c.tag) and c.tag not in ['pre', 'code']:
                for i in range(len(p)):
                    if p[i] == c:
                        p[i] = div
                        break
                marker_found = True
                            
            if header_rgx.match(c.tag):
                
                # Do not override pre-existing ids 
                if not "id" in c.attrib:
                    elem_id = unique(self.config["slugify"](text, '-'), used_ids)
                    c.attrib["id"] = elem_id
                else:
                    elem_id = c.attrib["id"]

                tag_level = int(c.tag[-1])
                
                toc_list.append({'level': tag_level,
                    'id': elem_id,
                    'name': text})
                
                self.add_anchor(c, elem_id)
                
        toc_list_nested = order_toc_list(toc_list)
        self.build_toc_etree(div, toc_list_nested)
        prettify = self.markdown.treeprocessors.get('prettify')
        if prettify: prettify.run(div)
        if not marker_found:
            # serialize and attach to markdown instance.
            toc = self.markdown.serializer(div)
            for pp in self.markdown.postprocessors.values():
                toc = pp.run(toc)
            self.markdown.toc = toc


class TocExtension(Extension):
    
    TreeProcessorClass = TocTreeprocessor
    
    def __init__(self, configs=[]):
        self.config = { "marker" : ["[TOC]", 
                            "Text to find and replace with Table of Contents -"
                            "Defaults to \"[TOC]\""],
                        "slugify" : [slugify,
                            "Function to generate anchors based on header text-"
                            "Defaults to the headerid ext's slugify function."],
                        "title" : [None,
                            "Title to insert into TOC <div> - "
                            "Defaults to None"],
                        "anchorlink" : [0,
                            "1 if header should be a self link"
                            "Defaults to 0"]}

        for key, value in configs:
            self.setConfig(key, value)

    def extendMarkdown(self, md, md_globals):
        tocext = self.TreeProcessorClass(md)
        tocext.config = self.getConfigs()
        # Headerid ext is set to '>prettify'. With this set to '_end',
        # it should always come after headerid ext (and honor ids assinged 
        # by the header id extension) if both are used. Same goes for 
        # attr_list extension. This must come last because we don't want
        # to redefine ids after toc is created. But we do want toc prettified.
        md.treeprocessors.add("toc", tocext, "_end")


def makeExtension(configs={}):
    return TocExtension(configs=configs)

########NEW FILE########
__FILENAME__ = wikilinks
'''
WikiLinks Extension for Python-Markdown
======================================

Converts [[WikiLinks]] to relative links.  Requires Python-Markdown 2.0+

Basic usage:

    >>> import markdown
    >>> text = "Some text with a [[WikiLink]]."
    >>> html = markdown.markdown(text, ['wikilinks'])
    >>> print html
    <p>Some text with a <a class="wikilink" href="/WikiLink/">WikiLink</a>.</p>

Whitespace behavior:

    >>> print markdown.markdown('[[ foo bar_baz ]]', ['wikilinks'])
    <p><a class="wikilink" href="/foo_bar_baz/">foo bar_baz</a></p>
    >>> print markdown.markdown('foo [[ ]] bar', ['wikilinks'])
    <p>foo  bar</p>

To define custom settings the simple way:

    >>> print markdown.markdown(text, 
    ...     ['wikilinks(base_url=/wiki/,end_url=.html,html_class=foo)']
    ... )
    <p>Some text with a <a class="foo" href="/wiki/WikiLink.html">WikiLink</a>.</p>
    
Custom settings the complex way:

    >>> md = markdown.Markdown(
    ...     extensions = ['wikilinks'], 
    ...     extension_configs = {'wikilinks': [
    ...                                 ('base_url', 'http://example.com/'), 
    ...                                 ('end_url', '.html'),
    ...                                 ('html_class', '') ]},
    ...     safe_mode = True)
    >>> print md.convert(text)
    <p>Some text with a <a href="http://example.com/WikiLink.html">WikiLink</a>.</p>

Use MetaData with mdx_meta.py (Note the blank html_class in MetaData):

    >>> text = """wiki_base_url: http://example.com/
    ... wiki_end_url:   .html
    ... wiki_html_class:
    ...
    ... Some text with a [[WikiLink]]."""
    >>> md = markdown.Markdown(extensions=['meta', 'wikilinks'])
    >>> print md.convert(text)
    <p>Some text with a <a href="http://example.com/WikiLink.html">WikiLink</a>.</p>

MetaData should not carry over to next document:

    >>> print md.convert("No [[MetaData]] here.")
    <p>No <a class="wikilink" href="/MetaData/">MetaData</a> here.</p>

Define a custom URL builder:

    >>> def my_url_builder(label, base, end):
    ...     return '/bar/'
    >>> md = markdown.Markdown(extensions=['wikilinks'], 
    ...         extension_configs={'wikilinks' : [('build_url', my_url_builder)]})
    >>> print md.convert('[[foo]]')
    <p><a class="wikilink" href="/bar/">foo</a></p>

From the command line:

    python markdown.py -x wikilinks(base_url=http://example.com/,end_url=.html,html_class=foo) src.txt

By [Waylan Limberg](http://achinghead.com/).

License: [BSD](http://www.opensource.org/licenses/bsd-license.php) 

Dependencies:
* [Python 2.3+](http://python.org)
* [Markdown 2.0+](http://packages.python.org/Markdown/)
'''

from __future__ import absolute_import
from __future__ import unicode_literals
from . import Extension
from ..inlinepatterns import Pattern
from ..util import etree
import re

def build_url(label, base, end):
    """ Build a url from the label, a base, and an end. """
    clean_label = re.sub(r'([ ]+_)|(_[ ]+)|([ ]+)', '_', label)
    return '%s%s%s'% (base, clean_label, end)


class WikiLinkExtension(Extension):
    def __init__(self, configs):
        # set extension defaults
        self.config = {
                        'base_url' : ['/', 'String to append to beginning or URL.'],
                        'end_url' : ['/', 'String to append to end of URL.'],
                        'html_class' : ['wikilink', 'CSS hook. Leave blank for none.'],
                        'build_url' : [build_url, 'Callable formats URL from label.'],
        }
        
        # Override defaults with user settings
        for key, value in configs :
            self.setConfig(key, value)
        
    def extendMarkdown(self, md, md_globals):
        self.md = md
    
        # append to end of inline patterns
        WIKILINK_RE = r'\[\[([\w0-9_ -]+)\]\]'
        wikilinkPattern = WikiLinks(WIKILINK_RE, self.getConfigs())
        wikilinkPattern.md = md
        md.inlinePatterns.add('wikilink', wikilinkPattern, "<not_strong")


class WikiLinks(Pattern):
    def __init__(self, pattern, config):
        super(WikiLinks, self).__init__(pattern)
        self.config = config
  
    def handleMatch(self, m):
        if m.group(2).strip():
            base_url, end_url, html_class = self._getMeta()
            label = m.group(2).strip()
            url = self.config['build_url'](label, base_url, end_url)
            a = etree.Element('a')
            a.text = label 
            a.set('href', url)
            if html_class:
                a.set('class', html_class)
        else:
            a = ''
        return a

    def _getMeta(self):
        """ Return meta data or config data. """
        base_url = self.config['base_url']
        end_url = self.config['end_url']
        html_class = self.config['html_class']
        if hasattr(self.md, 'Meta'):
            if 'wiki_base_url' in self.md.Meta:
                base_url = self.md.Meta['wiki_base_url'][0]
            if 'wiki_end_url' in self.md.Meta:
                end_url = self.md.Meta['wiki_end_url'][0]
            if 'wiki_html_class' in self.md.Meta:
                html_class = self.md.Meta['wiki_html_class'][0]
        return base_url, end_url, html_class
    

def makeExtension(configs=None) :
    return WikiLinkExtension(configs=configs)

########NEW FILE########
__FILENAME__ = inlinepatterns
"""
INLINE PATTERNS
=============================================================================

Inline patterns such as *emphasis* are handled by means of auxiliary
objects, one per pattern.  Pattern objects must be instances of classes
that extend markdown.Pattern.  Each pattern object uses a single regular
expression and needs support the following methods:

    pattern.getCompiledRegExp() # returns a regular expression

    pattern.handleMatch(m) # takes a match object and returns
                           # an ElementTree element or just plain text

All of python markdown's built-in patterns subclass from Pattern,
but you can add additional patterns that don't.

Also note that all the regular expressions used by inline must
capture the whole block.  For this reason, they all start with
'^(.*)' and end with '(.*)!'.  In case with built-in expression
Pattern takes care of adding the "^(.*)" and "(.*)!".

Finally, the order in which regular expressions are applied is very
important - e.g. if we first replace http://.../ links with <a> tags
and _then_ try to replace inline html, we would end up with a mess.
So, we apply the expressions in the following order:

* escape and backticks have to go before everything else, so
  that we can preempt any markdown patterns by escaping them.

* then we handle auto-links (must be done before inline html)

* then we handle inline HTML.  At this point we will simply
  replace all inline HTML strings with a placeholder and add
  the actual HTML to a hash.

* then inline images (must be done before links)

* then bracketed links, first regular then reference-style

* finally we apply strong and emphasis
"""

from __future__ import absolute_import
from __future__ import unicode_literals
from . import util
from . import odict
import re
try:
    from urllib.parse import urlparse, urlunparse
except ImportError:
    from urlparse import urlparse, urlunparse
try:
    from html import entities
except ImportError:
    import htmlentitydefs as entities


def build_inlinepatterns(md_instance, **kwargs):
    """ Build the default set of inline patterns for Markdown. """
    inlinePatterns = odict.OrderedDict()
    inlinePatterns["backtick"] = BacktickPattern(BACKTICK_RE)
    inlinePatterns["escape"] = EscapePattern(ESCAPE_RE, md_instance)
    inlinePatterns["reference"] = ReferencePattern(REFERENCE_RE, md_instance)
    inlinePatterns["link"] = LinkPattern(LINK_RE, md_instance)
    inlinePatterns["image_link"] = ImagePattern(IMAGE_LINK_RE, md_instance)
    inlinePatterns["image_reference"] = \
            ImageReferencePattern(IMAGE_REFERENCE_RE, md_instance)
    inlinePatterns["short_reference"] = \
            ReferencePattern(SHORT_REF_RE, md_instance)
    inlinePatterns["autolink"] = AutolinkPattern(AUTOLINK_RE, md_instance)
    inlinePatterns["automail"] = AutomailPattern(AUTOMAIL_RE, md_instance)
    inlinePatterns["linebreak"] = SubstituteTagPattern(LINE_BREAK_RE, 'br')
    if md_instance.safeMode != 'escape':
        inlinePatterns["html"] = HtmlPattern(HTML_RE, md_instance)
    inlinePatterns["entity"] = HtmlPattern(ENTITY_RE, md_instance)
    inlinePatterns["not_strong"] = SimpleTextPattern(NOT_STRONG_RE)
    inlinePatterns["strong_em"] = DoubleTagPattern(STRONG_EM_RE, 'strong,em')
    inlinePatterns["strong"] = SimpleTagPattern(STRONG_RE, 'strong')
    inlinePatterns["emphasis"] = SimpleTagPattern(EMPHASIS_RE, 'em')
    if md_instance.smart_emphasis:
        inlinePatterns["emphasis2"] = SimpleTagPattern(SMART_EMPHASIS_RE, 'em')
    else:
        inlinePatterns["emphasis2"] = SimpleTagPattern(EMPHASIS_2_RE, 'em')
    return inlinePatterns

"""
The actual regular expressions for patterns
-----------------------------------------------------------------------------
"""

NOBRACKET = r'[^\]\[]*'
BRK = ( r'\[('
        + (NOBRACKET + r'(\[')*6
        + (NOBRACKET+ r'\])*')*6
        + NOBRACKET + r')\]' )
NOIMG = r'(?<!\!)'

BACKTICK_RE = r'(?<!\\)(`+)(.+?)(?<!`)\2(?!`)' # `e=f()` or ``e=f("`")``
ESCAPE_RE = r'\\(.)'                             # \<
EMPHASIS_RE = r'(\*)([^\*]+)\2'                    # *emphasis*
STRONG_RE = r'(\*{2}|_{2})(.+?)\2'                      # **strong**
STRONG_EM_RE = r'(\*{3}|_{3})(.+?)\2'            # ***strong***
SMART_EMPHASIS_RE = r'(?<!\w)(_)(?!_)(.+?)(?<!_)\2(?!\w)'  # _smart_emphasis_
EMPHASIS_2_RE = r'(_)(.+?)\2'                 # _emphasis_
LINK_RE = NOIMG + BRK + \
r'''\(\s*(<.*?>|((?:(?:\(.*?\))|[^\(\)]))*?)\s*((['"])(.*?)\12\s*)?\)'''
# [text](url) or [text](<url>) or [text](url "title")

IMAGE_LINK_RE = r'\!' + BRK + r'\s*\((<.*?>|([^\)]*))\)'
# ![alttxt](http://x.com/) or ![alttxt](<http://x.com/>)
REFERENCE_RE = NOIMG + BRK+ r'\s?\[([^\]]*)\]'           # [Google][3]
SHORT_REF_RE = NOIMG + r'\[([^\]]+)\]'                   # [Google]
IMAGE_REFERENCE_RE = r'\!' + BRK + '\s?\[([^\]]*)\]' # ![alt text][2]
NOT_STRONG_RE = r'((^| )(\*|_)( |$))'                        # stand-alone * or _
AUTOLINK_RE = r'<((?:[Ff]|[Hh][Tt])[Tt][Pp][Ss]?://[^>]*)>' # <http://www.123.com>
AUTOMAIL_RE = r'<([^> \!]*@[^> ]*)>'               # <me@example.com>

HTML_RE = r'(\<([a-zA-Z/][^\>]*?|\!--.*?--)\>)'               # <...>
ENTITY_RE = r'(&[\#a-zA-Z0-9]*;)'               # &amp;
LINE_BREAK_RE = r'  \n'                     # two spaces at end of line


def dequote(string):
    """Remove quotes from around a string."""
    if ( ( string.startswith('"') and string.endswith('"'))
         or (string.startswith("'") and string.endswith("'")) ):
        return string[1:-1]
    else:
        return string

ATTR_RE = re.compile("\{@([^\}]*)=([^\}]*)}") # {@id=123}

def handleAttributes(text, parent):
    """Set values of an element based on attribute definitions ({@id=123})."""
    def attributeCallback(match):
        parent.set(match.group(1), match.group(2).replace('\n', ' '))
    return ATTR_RE.sub(attributeCallback, text)


"""
The pattern classes
-----------------------------------------------------------------------------
"""

class Pattern(object):
    """Base class that inline patterns subclass. """

    def __init__(self, pattern, markdown_instance=None):
        """
        Create an instant of an inline pattern.

        Keyword arguments:

        * pattern: A regular expression that matches a pattern

        """
        self.pattern = pattern
        self.compiled_re = re.compile("^(.*?)%s(.*?)$" % pattern, 
                                      re.DOTALL | re.UNICODE)

        # Api for Markdown to pass safe_mode into instance
        self.safe_mode = False
        if markdown_instance:
            self.markdown = markdown_instance

    def getCompiledRegExp(self):
        """ Return a compiled regular expression. """
        return self.compiled_re

    def handleMatch(self, m):
        """Return a ElementTree element from the given match.

        Subclasses should override this method.

        Keyword arguments:

        * m: A re match object containing a match of the pattern.

        """
        pass

    def type(self):
        """ Return class name, to define pattern type """
        return self.__class__.__name__

    def unescape(self, text):
        """ Return unescaped text given text with an inline placeholder. """
        try:
            stash = self.markdown.treeprocessors['inline'].stashed_nodes
        except KeyError:
            return text
        def itertext(el):
            ' Reimplement Element.itertext for older python versions '
            tag = el.tag
            if not isinstance(tag, util.string_type) and tag is not None:
                return
            if el.text:
                yield el.text
            for e in el:
                for s in itertext(e):
                    yield s
                if e.tail:
                    yield e.tail
        def get_stash(m):
            id = m.group(1)
            if id in stash:
                value = stash.get(id)
                if isinstance(value, util.string_type):
                    return value
                else:
                    # An etree Element - return text content only
                    return ''.join(itertext(value)) 
        return util.INLINE_PLACEHOLDER_RE.sub(get_stash, text)


class SimpleTextPattern(Pattern):
    """ Return a simple text of group(2) of a Pattern. """
    def handleMatch(self, m):
        text = m.group(2)
        if text == util.INLINE_PLACEHOLDER_PREFIX:
            return None
        return text


class EscapePattern(Pattern):
    """ Return an escaped character. """

    def handleMatch(self, m):
        char = m.group(2)
        if char in self.markdown.ESCAPED_CHARS:
            return '%s%s%s' % (util.STX, ord(char), util.ETX)
        else:
            return '\\%s' % char


class SimpleTagPattern(Pattern):
    """
    Return element of type `tag` with a text attribute of group(3)
    of a Pattern.

    """
    def __init__ (self, pattern, tag):
        Pattern.__init__(self, pattern)
        self.tag = tag

    def handleMatch(self, m):
        el = util.etree.Element(self.tag)
        el.text = m.group(3)
        return el


class SubstituteTagPattern(SimpleTagPattern):
    """ Return an element of type `tag` with no children. """
    def handleMatch (self, m):
        return util.etree.Element(self.tag)


class BacktickPattern(Pattern):
    """ Return a `<code>` element containing the matching text. """
    def __init__ (self, pattern):
        Pattern.__init__(self, pattern)
        self.tag = "code"

    def handleMatch(self, m):
        el = util.etree.Element(self.tag)
        el.text = util.AtomicString(m.group(3).strip())
        return el


class DoubleTagPattern(SimpleTagPattern):
    """Return a ElementTree element nested in tag2 nested in tag1.

    Useful for strong emphasis etc.

    """
    def handleMatch(self, m):
        tag1, tag2 = self.tag.split(",")
        el1 = util.etree.Element(tag1)
        el2 = util.etree.SubElement(el1, tag2)
        el2.text = m.group(3)
        return el1


class HtmlPattern(Pattern):
    """ Store raw inline html and return a placeholder. """
    def handleMatch (self, m):
        rawhtml = self.unescape(m.group(2))
        place_holder = self.markdown.htmlStash.store(rawhtml)
        return place_holder

    def unescape(self, text):
        """ Return unescaped text given text with an inline placeholder. """
        try:
            stash = self.markdown.treeprocessors['inline'].stashed_nodes
        except KeyError:
            return text
        def get_stash(m):
            id = m.group(1)
            value = stash.get(id)
            if value is not None:
                try:
                    return self.markdown.serializer(value)
                except:
                    return '\%s' % value
            
        return util.INLINE_PLACEHOLDER_RE.sub(get_stash, text)


class LinkPattern(Pattern):
    """ Return a link element from the given match. """
    def handleMatch(self, m):
        el = util.etree.Element("a")
        el.text = m.group(2)
        title = m.group(13)
        href = m.group(9)

        if href:
            if href[0] == "<":
                href = href[1:-1]
            el.set("href", self.sanitize_url(self.unescape(href.strip())))
        else:
            el.set("href", "")

        if title:
            title = dequote(self.unescape(title)) 
            el.set("title", title)
        return el

    def sanitize_url(self, url):
        """
        Sanitize a url against xss attacks in "safe_mode".

        Rather than specifically blacklisting `javascript:alert("XSS")` and all
        its aliases (see <http://ha.ckers.org/xss.html>), we whitelist known
        safe url formats. Most urls contain a network location, however some
        are known not to (i.e.: mailto links). Script urls do not contain a
        location. Additionally, for `javascript:...`, the scheme would be
        "javascript" but some aliases will appear to `urlparse()` to have no
        scheme. On top of that relative links (i.e.: "foo/bar.html") have no
        scheme. Therefore we must check "path", "parameters", "query" and
        "fragment" for any literal colons. We don't check "scheme" for colons
        because it *should* never have any and "netloc" must allow the form:
        `username:password@host:port`.

        """
        url = url.replace(' ', '%20')
        if not self.markdown.safeMode:
            # Return immediately bipassing parsing.
            return url
        
        try:
            scheme, netloc, path, params, query, fragment = url = urlparse(url)
        except ValueError:
            # Bad url - so bad it couldn't be parsed.
            return ''
        
        locless_schemes = ['', 'mailto', 'news']
        allowed_schemes = locless_schemes + ['http', 'https', 'ftp', 'ftps']
        if scheme not in allowed_schemes:
            # Not a known (allowed) scheme. Not safe.
            return ''
            
        if netloc == '' and scheme not in locless_schemes:
            # This should not happen. Treat as suspect.
            return ''

        for part in url[2:]:
            if ":" in part:
                # A colon in "path", "parameters", "query" or "fragment" is suspect.
                return ''

        # Url passes all tests. Return url as-is.
        return urlunparse(url)

class ImagePattern(LinkPattern):
    """ Return a img element from the given match. """
    def handleMatch(self, m):
        el = util.etree.Element("img")
        src_parts = m.group(9).split()
        if src_parts:
            src = src_parts[0]
            if src[0] == "<" and src[-1] == ">":
                src = src[1:-1]
            el.set('src', self.sanitize_url(self.unescape(src)))
        else:
            el.set('src', "")
        if len(src_parts) > 1:
            el.set('title', dequote(self.unescape(" ".join(src_parts[1:]))))

        if self.markdown.enable_attributes:
            truealt = handleAttributes(m.group(2), el)
        else:
            truealt = m.group(2)

        el.set('alt', self.unescape(truealt))
        return el

class ReferencePattern(LinkPattern):
    """ Match to a stored reference and return link element. """

    NEWLINE_CLEANUP_RE = re.compile(r'[ ]?\n', re.MULTILINE)

    def handleMatch(self, m):
        try:
            id = m.group(9).lower()
        except IndexError:
            id = None
        if not id:
            # if we got something like "[Google][]" or "[Goggle]"
            # we'll use "google" as the id
            id = m.group(2).lower()

        # Clean up linebreaks in id
        id = self.NEWLINE_CLEANUP_RE.sub(' ', id)
        if not id in self.markdown.references: # ignore undefined refs
            return None
        href, title = self.markdown.references[id]

        text = m.group(2)
        return self.makeTag(href, title, text)

    def makeTag(self, href, title, text):
        el = util.etree.Element('a')

        el.set('href', self.sanitize_url(href))
        if title:
            el.set('title', title)

        el.text = text
        return el


class ImageReferencePattern(ReferencePattern):
    """ Match to a stored reference and return img element. """
    def makeTag(self, href, title, text):
        el = util.etree.Element("img")
        el.set("src", self.sanitize_url(href))
        if title:
            el.set("title", title)

        if self.markdown.enable_attributes:
            text = handleAttributes(text, el)

        el.set("alt", self.unescape(text))
        return el


class AutolinkPattern(Pattern):
    """ Return a link Element given an autolink (`<http://example/com>`). """
    def handleMatch(self, m):
        el = util.etree.Element("a")
        el.set('href', self.unescape(m.group(2)))
        el.text = util.AtomicString(m.group(2))
        return el

class AutomailPattern(Pattern):
    """
    Return a mailto link Element given an automail link (`<foo@example.com>`).
    """
    def handleMatch(self, m):
        el = util.etree.Element('a')
        email = self.unescape(m.group(2))
        if email.startswith("mailto:"):
            email = email[len("mailto:"):]

        def codepoint2name(code):
            """Return entity definition by code, or the code if not defined."""
            entity = entities.codepoint2name.get(code)
            if entity:
                return "%s%s;" % (util.AMP_SUBSTITUTE, entity)
            else:
                return "%s#%d;" % (util.AMP_SUBSTITUTE, code)

        letters = [codepoint2name(ord(letter)) for letter in email]
        el.text = util.AtomicString(''.join(letters))

        mailto = "mailto:" + email
        mailto = "".join([util.AMP_SUBSTITUTE + '#%d;' %
                          ord(letter) for letter in mailto])
        el.set('href', mailto)
        return el


########NEW FILE########
__FILENAME__ = odict
from __future__ import unicode_literals
from __future__ import absolute_import
from . import util

from copy import deepcopy

def iteritems_compat(d):
    """Return an iterator over the (key, value) pairs of a dictionary.
    Copied from `six` module."""
    return iter(getattr(d, _iteritems)())

class OrderedDict(dict):
    """
    A dictionary that keeps its keys in the order in which they're inserted.
    
    Copied from Django's SortedDict with some modifications.

    """
    def __new__(cls, *args, **kwargs):
        instance = super(OrderedDict, cls).__new__(cls, *args, **kwargs)
        instance.keyOrder = []
        return instance

    def __init__(self, data=None):
        if data is None or isinstance(data, dict):
            data = data or []
            super(OrderedDict, self).__init__(data)
            self.keyOrder = list(data) if data else []
        else:
            super(OrderedDict, self).__init__()
            super_set = super(OrderedDict, self).__setitem__
            for key, value in data:
                # Take the ordering from first key
                if key not in self:
                    self.keyOrder.append(key)
                # But override with last value in data (dict() does this)
                super_set(key, value)

    def __deepcopy__(self, memo):
        return self.__class__([(key, deepcopy(value, memo))
                               for key, value in self.items()])

    def __copy__(self):
        # The Python's default copy implementation will alter the state
        # of self. The reason for this seems complex but is likely related to
        # subclassing dict.
        return self.copy()

    def __setitem__(self, key, value):
        if key not in self:
            self.keyOrder.append(key)
        super(OrderedDict, self).__setitem__(key, value)

    def __delitem__(self, key):
        super(OrderedDict, self).__delitem__(key)
        self.keyOrder.remove(key)

    def __iter__(self):
        return iter(self.keyOrder)

    def __reversed__(self):
        return reversed(self.keyOrder)

    def pop(self, k, *args):
        result = super(OrderedDict, self).pop(k, *args)
        try:
            self.keyOrder.remove(k)
        except ValueError:
            # Key wasn't in the dictionary in the first place. No problem.
            pass
        return result

    def popitem(self):
        result = super(OrderedDict, self).popitem()
        self.keyOrder.remove(result[0])
        return result

    def _iteritems(self):
        for key in self.keyOrder:
            yield key, self[key]

    def _iterkeys(self):
        for key in self.keyOrder:
            yield key

    def _itervalues(self):
        for key in self.keyOrder:
            yield self[key]

    if util.PY3:
        items = _iteritems
        keys = _iterkeys
        values = _itervalues
    else:
        iteritems = _iteritems
        iterkeys = _iterkeys
        itervalues = _itervalues

        def items(self):
            return [(k, self[k]) for k in self.keyOrder]

        def keys(self):
            return self.keyOrder[:]

        def values(self):
            return [self[k] for k in self.keyOrder]

    def update(self, dict_):
        for k, v in iteritems_compat(dict_):
            self[k] = v

    def setdefault(self, key, default):
        if key not in self:
            self.keyOrder.append(key)
        return super(OrderedDict, self).setdefault(key, default)

    def value_for_index(self, index):
        """Returns the value of the item at the given zero-based index."""
        return self[self.keyOrder[index]]

    def insert(self, index, key, value):
        """Inserts the key, value pair before the item with the given index."""
        if key in self.keyOrder:
            n = self.keyOrder.index(key)
            del self.keyOrder[n]
            if n < index:
                index -= 1
        self.keyOrder.insert(index, key)
        super(OrderedDict, self).__setitem__(key, value)

    def copy(self):
        """Returns a copy of this object."""
        # This way of initializing the copy means it works for subclasses, too.
        return self.__class__(self)

    def __repr__(self):
        """
        Replaces the normal dict.__repr__ with a version that returns the keys
        in their Ordered order.
        """
        return '{%s}' % ', '.join(['%r: %r' % (k, v) for k, v in iteritems_compat(self)])

    def clear(self):
        super(OrderedDict, self).clear()
        self.keyOrder = []

    def index(self, key):
        """ Return the index of a given key. """
        try:
            return self.keyOrder.index(key)
        except ValueError:
            raise ValueError("Element '%s' was not found in OrderedDict" % key)

    def index_for_location(self, location):
        """ Return index or None for a given location. """
        if location == '_begin':
            i = 0
        elif location == '_end':
            i = None
        elif location.startswith('<') or location.startswith('>'):
            i = self.index(location[1:])
            if location.startswith('>'):
                if i >= len(self):
                    # last item
                    i = None
                else:
                    i += 1
        else:
            raise ValueError('Not a valid location: "%s". Location key '
                             'must start with a ">" or "<".' % location)
        return i

    def add(self, key, value, location):
        """ Insert by key location. """
        i = self.index_for_location(location)
        if i is not None:
            self.insert(i, key, value)
        else:
            self.__setitem__(key, value)

    def link(self, key, location):
        """ Change location of an existing item. """
        n = self.keyOrder.index(key)
        del self.keyOrder[n]
        try:
            i = self.index_for_location(location)
            if i is not None:
                self.keyOrder.insert(i, key)
            else:
                self.keyOrder.append(key)
        except Exception as e:
            # restore to prevent data loss and reraise
            self.keyOrder.insert(n, key)
            raise e

########NEW FILE########
__FILENAME__ = postprocessors
"""
POST-PROCESSORS
=============================================================================

Markdown also allows post-processors, which are similar to preprocessors in
that they need to implement a "run" method. However, they are run after core
processing.

"""

from __future__ import absolute_import
from __future__ import unicode_literals
from . import util
from . import odict
import re


def build_postprocessors(md_instance, **kwargs):
    """ Build the default postprocessors for Markdown. """
    postprocessors = odict.OrderedDict()
    postprocessors["raw_html"] = RawHtmlPostprocessor(md_instance)
    postprocessors["amp_substitute"] = AndSubstitutePostprocessor()
    postprocessors["unescape"] = UnescapePostprocessor()
    return postprocessors


class Postprocessor(util.Processor):
    """
    Postprocessors are run after the ElementTree it converted back into text.

    Each Postprocessor implements a "run" method that takes a pointer to a
    text string, modifies it as necessary and returns a text string.

    Postprocessors must extend markdown.Postprocessor.

    """

    def run(self, text):
        """
        Subclasses of Postprocessor should implement a `run` method, which
        takes the html document as a single text string and returns a
        (possibly modified) string.

        """
        pass


class RawHtmlPostprocessor(Postprocessor):
    """ Restore raw html to the document. """

    def run(self, text):
        """ Iterate over html stash and restore "safe" html. """
        for i in range(self.markdown.htmlStash.html_counter):
            html, safe  = self.markdown.htmlStash.rawHtmlBlocks[i]
            if self.markdown.safeMode and not safe:
                if str(self.markdown.safeMode).lower() == 'escape':
                    html = self.escape(html)
                elif str(self.markdown.safeMode).lower() == 'remove':
                    html = ''
                else:
                    html = self.markdown.html_replacement_text
            if self.isblocklevel(html) and (safe or not self.markdown.safeMode):
                text = text.replace("<p>%s</p>" % 
                            (self.markdown.htmlStash.get_placeholder(i)),
                            html + "\n")
            text =  text.replace(self.markdown.htmlStash.get_placeholder(i), 
                                 html)
        return text

    def escape(self, html):
        """ Basic html escaping """
        html = html.replace('&', '&amp;')
        html = html.replace('<', '&lt;')
        html = html.replace('>', '&gt;')
        return html.replace('"', '&quot;')

    def isblocklevel(self, html):
        m = re.match(r'^\<\/?([^ >]+)', html)
        if m:
            if m.group(1)[0] in ('!', '?', '@', '%'):
                # Comment, php etc...
                return True
            return util.isBlockLevel(m.group(1))
        return False


class AndSubstitutePostprocessor(Postprocessor):
    """ Restore valid entities """

    def run(self, text):
        text =  text.replace(util.AMP_SUBSTITUTE, "&")
        return text


class UnescapePostprocessor(Postprocessor):
    """ Restore escaped chars """

    RE = re.compile('%s(\d+)%s' % (util.STX, util.ETX))

    def unescape(self, m):
        return util.int2str(int(m.group(1)))

    def run(self, text):
        return self.RE.sub(self.unescape, text)

########NEW FILE########
__FILENAME__ = preprocessors
"""
PRE-PROCESSORS
=============================================================================

Preprocessors work on source text before we start doing anything too
complicated. 
"""

from __future__ import absolute_import
from __future__ import unicode_literals
from . import util
from . import odict
import re


def build_preprocessors(md_instance, **kwargs):
    """ Build the default set of preprocessors used by Markdown. """
    preprocessors = odict.OrderedDict()
    preprocessors['normalize_whitespace'] = NormalizeWhitespace(md_instance)
    if md_instance.safeMode != 'escape':
        preprocessors["html_block"] = HtmlBlockPreprocessor(md_instance)
    preprocessors["reference"] = ReferencePreprocessor(md_instance)
    return preprocessors


class Preprocessor(util.Processor):
    """
    Preprocessors are run after the text is broken into lines.

    Each preprocessor implements a "run" method that takes a pointer to a
    list of lines of the document, modifies it as necessary and returns
    either the same pointer or a pointer to a new list.

    Preprocessors must extend markdown.Preprocessor.

    """
    def run(self, lines):
        """
        Each subclass of Preprocessor should override the `run` method, which
        takes the document as a list of strings split by newlines and returns
        the (possibly modified) list of lines.

        """
        pass


class NormalizeWhitespace(Preprocessor):
    """ Normalize whitespace for consistant parsing. """

    def run(self, lines):
        source = '\n'.join(lines)
        source = source.replace(util.STX, "").replace(util.ETX, "")
        source = source.replace("\r\n", "\n").replace("\r", "\n") + "\n\n"
        source = source.expandtabs(self.markdown.tab_length)
        source = re.sub(r'(?<=\n) +\n', '\n', source)
        return source.split('\n')


class HtmlBlockPreprocessor(Preprocessor):
    """Remove html blocks from the text and store them for later retrieval."""

    right_tag_patterns = ["</%s>", "%s>"]
    attrs_pattern = r"""
        \s+(?P<attr>[^>"'/= ]+)=(?P<q>['"])(?P<value>.*?)(?P=q)   # attr="value"
        |                                                         # OR 
        \s+(?P<attr1>[^>"'/= ]+)=(?P<value1>[^> ]+)               # attr=value
        |                                                         # OR
        \s+(?P<attr2>[^>"'/= ]+)                                  # attr
        """
    left_tag_pattern = r'^\<(?P<tag>[^> ]+)(?P<attrs>(%s)*)\s*\/?\>?' % attrs_pattern
    attrs_re = re.compile(attrs_pattern, re.VERBOSE)
    left_tag_re = re.compile(left_tag_pattern, re.VERBOSE)
    markdown_in_raw = False

    def _get_left_tag(self, block):
        m = self.left_tag_re.match(block)
        if m:
            tag = m.group('tag')
            raw_attrs = m.group('attrs')
            attrs = {}
            if raw_attrs:
                for ma in self.attrs_re.finditer(raw_attrs):
                    if ma.group('attr'):
                        if ma.group('value'):
                            attrs[ma.group('attr').strip()] = ma.group('value')
                        else:
                            attrs[ma.group('attr').strip()] = ""
                    elif ma.group('attr1'):
                        if ma.group('value1'):
                            attrs[ma.group('attr1').strip()] = ma.group('value1')
                        else:
                            attrs[ma.group('attr1').strip()] = ""
                    elif ma.group('attr2'):
                        attrs[ma.group('attr2').strip()] = ""
            return tag, len(m.group(0)), attrs
        else:
            tag = block[1:].split(">", 1)[0].lower()
            return tag, len(tag)+2, {}

    def _recursive_tagfind(self, ltag, rtag, start_index, block):
        while 1:
            i = block.find(rtag, start_index)
            if i == -1:
                return -1
            j = block.find(ltag, start_index) 
            # if no ltag, or rtag found before another ltag, return index
            if (j > i or j == -1):
                return i + len(rtag)
            # another ltag found before rtag, use end of ltag as starting
            # point and search again
            j = block.find('>', j)
            start_index = self._recursive_tagfind(ltag, rtag, j + 1, block)
            if start_index == -1:
                # HTML potentially malformed- ltag has no corresponding 
                # rtag
                return -1

    def _get_right_tag(self, left_tag, left_index, block):
        for p in self.right_tag_patterns:
            tag = p % left_tag
            i = self._recursive_tagfind("<%s" % left_tag, tag, left_index, block)
            if i > 2:
                return tag.lstrip("<").rstrip(">"), i
        return block.rstrip()[-left_index:-1].lower(), len(block)
    
    def _equal_tags(self, left_tag, right_tag):
        if left_tag[0] in ['?', '@', '%']: # handle PHP, etc.
            return True
        if ("/" + left_tag) == right_tag:
            return True
        if (right_tag == "--" and left_tag == "--"):
            return True
        elif left_tag == right_tag[1:] \
            and right_tag[0] == "/":
            return True
        else:
            return False

    def _is_oneliner(self, tag):
        return (tag in ['hr', 'hr/'])

    def run(self, lines):
        text = "\n".join(lines)
        new_blocks = []
        text = text.rsplit("\n\n")
        items = []
        left_tag = ''
        right_tag = ''
        in_tag = False # flag

        while text:
            block = text[0]
            if block.startswith("\n"):
                block = block[1:]
            text = text[1:]

            if block.startswith("\n"):
                block = block[1:]

            if not in_tag:
                if block.startswith("<") and len(block.strip()) > 1:

                    if block[1] == "!":
                        # is a comment block
                        left_tag, left_index, attrs  = "--", 2, {}
                    else:
                        left_tag, left_index, attrs = self._get_left_tag(block)
                    right_tag, data_index = self._get_right_tag(left_tag, 
                                                                left_index,
                                                                block)
                    # keep checking conditions below and maybe just append
                    
                    if data_index < len(block) \
                        and (util.isBlockLevel(left_tag)
                        or left_tag == '--'): 
                        text.insert(0, block[data_index:])
                        block = block[:data_index]

                    if not (util.isBlockLevel(left_tag) \
                        or block[1] in ["!", "?", "@", "%"]):
                        new_blocks.append(block)
                        continue

                    if self._is_oneliner(left_tag):
                        new_blocks.append(block.strip())
                        continue

                    if block.rstrip().endswith(">") \
                        and self._equal_tags(left_tag, right_tag):
                        if self.markdown_in_raw and 'markdown' in attrs.keys():
                            start = re.sub(r'\smarkdown(=[\'"]?[^> ]*[\'"]?)?', 
                                           '', block[:left_index])
                            end = block[-len(right_tag)-2:]
                            block = block[left_index:-len(right_tag)-2]
                            new_blocks.append(
                                self.markdown.htmlStash.store(start))
                            new_blocks.append(block)
                            new_blocks.append(
                                self.markdown.htmlStash.store(end))
                        else:
                            new_blocks.append(
                                self.markdown.htmlStash.store(block.strip()))
                        continue
                    else: 
                        # if is block level tag and is not complete

                        if util.isBlockLevel(left_tag) or left_tag == "--" \
                            and not block.rstrip().endswith(">"):
                            items.append(block.strip())
                            in_tag = True
                        else:
                            new_blocks.append(
                            self.markdown.htmlStash.store(block.strip()))

                        continue

                new_blocks.append(block)

            else:
                items.append(block)

                right_tag, data_index = self._get_right_tag(left_tag, 0, block)

                if self._equal_tags(left_tag, right_tag):
                    # if find closing tag
                    
                    if data_index < len(block):
                        # we have more text after right_tag
                        items[-1] = block[:data_index]
                        text.insert(0, block[data_index:])

                    in_tag = False
                    if self.markdown_in_raw and 'markdown' in attrs.keys():
                        start = re.sub(r'\smarkdown(=[\'"]?[^> ]*[\'"]?)?', 
                                       '', items[0][:left_index])
                        items[0] = items[0][left_index:]
                        end = items[-1][-len(right_tag)-2:]
                        items[-1] = items[-1][:-len(right_tag)-2]
                        new_blocks.append(
                            self.markdown.htmlStash.store(start))
                        new_blocks.extend(items)
                        new_blocks.append(
                            self.markdown.htmlStash.store(end))
                    else:
                        new_blocks.append(
                            self.markdown.htmlStash.store('\n\n'.join(items)))
                    items = []

        if items:
            if self.markdown_in_raw and 'markdown' in attrs.keys():
                start = re.sub(r'\smarkdown(=[\'"]?[^> ]*[\'"]?)?', 
                               '', items[0][:left_index])
                items[0] = items[0][left_index:]
                end = items[-1][-len(right_tag)-2:]
                items[-1] = items[-1][:-len(right_tag)-2]
                new_blocks.append(
                    self.markdown.htmlStash.store(start))
                new_blocks.extend(items)
                if end.strip():
                    new_blocks.append(
                        self.markdown.htmlStash.store(end))
            else:
                new_blocks.append(
                    self.markdown.htmlStash.store('\n\n'.join(items)))
            #new_blocks.append(self.markdown.htmlStash.store('\n\n'.join(items)))
            new_blocks.append('\n')

        new_text = "\n\n".join(new_blocks)
        return new_text.split("\n")


class ReferencePreprocessor(Preprocessor):
    """ Remove reference definitions from text and store for later use. """

    TITLE = r'[ ]*(\"(.*)\"|\'(.*)\'|\((.*)\))[ ]*'
    RE = re.compile(r'^[ ]{0,3}\[([^\]]*)\]:\s*([^ ]*)[ ]*(%s)?$' % TITLE, re.DOTALL)
    TITLE_RE = re.compile(r'^%s$' % TITLE)

    def run (self, lines):
        new_text = [];
        while lines:
            line = lines.pop(0)
            m = self.RE.match(line)
            if m:
                id = m.group(1).strip().lower()
                link = m.group(2).lstrip('<').rstrip('>')
                t = m.group(5) or m.group(6) or m.group(7)
                if not t:
                    # Check next line for title
                    tm = self.TITLE_RE.match(lines[0])
                    if tm:
                        lines.pop(0)
                        t = tm.group(2) or tm.group(3) or tm.group(4)
                self.markdown.references[id] = (link, t)
            else:
                new_text.append(line)

        return new_text #+ "\n"

########NEW FILE########
__FILENAME__ = serializers
# markdown/searializers.py
#
# Add x/html serialization to Elementree
# Taken from ElementTree 1.3 preview with slight modifications
#
# Copyright (c) 1999-2007 by Fredrik Lundh.  All rights reserved.
#
# fredrik@pythonware.com
# http://www.pythonware.com
#
# --------------------------------------------------------------------
# The ElementTree toolkit is
#
# Copyright (c) 1999-2007 by Fredrik Lundh
#
# By obtaining, using, and/or copying this software and/or its
# associated documentation, you agree that you have read, understood,
# and will comply with the following terms and conditions:
#
# Permission to use, copy, modify, and distribute this software and
# its associated documentation for any purpose and without fee is
# hereby granted, provided that the above copyright notice appears in
# all copies, and that both that copyright notice and this permission
# notice appear in supporting documentation, and that the name of
# Secret Labs AB or the author not be used in advertising or publicity
# pertaining to distribution of the software without specific, written
# prior permission.
#
# SECRET LABS AB AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH REGARD
# TO THIS SOFTWARE, INCLUDING ALL IMPLIED WARRANTIES OF MERCHANT-
# ABILITY AND FITNESS.  IN NO EVENT SHALL SECRET LABS AB OR THE AUTHOR
# BE LIABLE FOR ANY SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY
# DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS,
# WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS
# ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE
# OF THIS SOFTWARE.
# --------------------------------------------------------------------


from __future__ import absolute_import
from __future__ import unicode_literals
from . import util
ElementTree = util.etree.ElementTree
QName = util.etree.QName
if hasattr(util.etree, 'test_comment'):
    Comment = util.etree.test_comment
else:
    Comment = util.etree.Comment
PI = util.etree.PI
ProcessingInstruction = util.etree.ProcessingInstruction

__all__ = ['to_html_string', 'to_xhtml_string']

HTML_EMPTY = ("area", "base", "basefont", "br", "col", "frame", "hr",
              "img", "input", "isindex", "link", "meta" "param")

try:
    HTML_EMPTY = set(HTML_EMPTY)
except NameError:
    pass

_namespace_map = {
    # "well-known" namespace prefixes
    "http://www.w3.org/XML/1998/namespace": "xml",
    "http://www.w3.org/1999/xhtml": "html",
    "http://www.w3.org/1999/02/22-rdf-syntax-ns#": "rdf",
    "http://schemas.xmlsoap.org/wsdl/": "wsdl",
    # xml schema
    "http://www.w3.org/2001/XMLSchema": "xs",
    "http://www.w3.org/2001/XMLSchema-instance": "xsi",
    # dublic core
    "http://purl.org/dc/elements/1.1/": "dc",
}


def _raise_serialization_error(text):
    raise TypeError(
        "cannot serialize %r (type %s)" % (text, type(text).__name__)
        )

def _encode(text, encoding):
    try:
        return text.encode(encoding, "xmlcharrefreplace")
    except (TypeError, AttributeError):
        _raise_serialization_error(text)

def _escape_cdata(text):
    # escape character data
    try:
        # it's worth avoiding do-nothing calls for strings that are
        # shorter than 500 character, or so.  assume that's, by far,
        # the most common case in most applications.
        if "&" in text:
            text = text.replace("&", "&amp;")
        if "<" in text:
            text = text.replace("<", "&lt;")
        if ">" in text:
            text = text.replace(">", "&gt;")
        return text
    except (TypeError, AttributeError):
        _raise_serialization_error(text)


def _escape_attrib(text):
    # escape attribute value
    try:
        if "&" in text:
            text = text.replace("&", "&amp;")
        if "<" in text:
            text = text.replace("<", "&lt;")
        if ">" in text:
            text = text.replace(">", "&gt;")
        if "\"" in text:
            text = text.replace("\"", "&quot;")
        if "\n" in text:
            text = text.replace("\n", "&#10;")
        return text
    except (TypeError, AttributeError):
        _raise_serialization_error(text)

def _escape_attrib_html(text):
    # escape attribute value
    try:
        if "&" in text:
            text = text.replace("&", "&amp;")
        if "<" in text:
            text = text.replace("<", "&lt;")
        if ">" in text:
            text = text.replace(">", "&gt;")
        if "\"" in text:
            text = text.replace("\"", "&quot;")
        return text
    except (TypeError, AttributeError):
        _raise_serialization_error(text)


def _serialize_html(write, elem, qnames, namespaces, format):
    tag = elem.tag
    text = elem.text
    if tag is Comment:
        write("<!--%s-->" % _escape_cdata(text))
    elif tag is ProcessingInstruction:
        write("<?%s?>" % _escape_cdata(text))
    else:
        tag = qnames[tag]
        if tag is None:
            if text:
                write(_escape_cdata(text))
            for e in elem:
                _serialize_html(write, e, qnames, None, format)
        else:
            write("<" + tag)
            items = elem.items()
            if items or namespaces:
                items.sort() # lexical order
                for k, v in items:
                    if isinstance(k, QName):
                        k = k.text
                    if isinstance(v, QName):
                        v = qnames[v.text]
                    else:
                        v = _escape_attrib_html(v)
                    if qnames[k] == v and format == 'html':
                        # handle boolean attributes
                        write(" %s" % v)
                    else:
                        write(" %s=\"%s\"" % (qnames[k], v))
                if namespaces:
                    items = namespaces.items()
                    items.sort(key=lambda x: x[1]) # sort on prefix
                    for v, k in items:
                        if k:
                            k = ":" + k
                        write(" xmlns%s=\"%s\"" % (k, _escape_attrib(v)))
            if format == "xhtml" and tag in HTML_EMPTY:
                write(" />")
            else:
                write(">")
                tag = tag.lower()
                if text:
                    if tag == "script" or tag == "style":
                        write(text)
                    else:
                        write(_escape_cdata(text))
                for e in elem:
                    _serialize_html(write, e, qnames, None, format)
                if tag not in HTML_EMPTY:
                    write("</" + tag + ">")
    if elem.tail:
        write(_escape_cdata(elem.tail))

def _write_html(root,
                encoding=None,
                default_namespace=None,
                format="html"):
    assert root is not None
    data = []
    write = data.append
    qnames, namespaces = _namespaces(root, default_namespace)
    _serialize_html(write, root, qnames, namespaces, format)
    if encoding is None:
        return "".join(data)
    else:
        return _encode("".join(data))


# --------------------------------------------------------------------
# serialization support

def _namespaces(elem, default_namespace=None):
    # identify namespaces used in this tree

    # maps qnames to *encoded* prefix:local names
    qnames = {None: None}

    # maps uri:s to prefixes
    namespaces = {}
    if default_namespace:
        namespaces[default_namespace] = ""

    def add_qname(qname):
        # calculate serialized qname representation
        try:
            if qname[:1] == "{":
                uri, tag = qname[1:].split("}", 1)
                prefix = namespaces.get(uri)
                if prefix is None:
                    prefix = _namespace_map.get(uri)
                    if prefix is None:
                        prefix = "ns%d" % len(namespaces)
                    if prefix != "xml":
                        namespaces[uri] = prefix
                if prefix:
                    qnames[qname] = "%s:%s" % (prefix, tag)
                else:
                    qnames[qname] = tag # default element
            else:
                if default_namespace:
                    raise ValueError(
                        "cannot use non-qualified names with "
                        "default_namespace option"
                        )
                qnames[qname] = qname
        except TypeError:
            _raise_serialization_error(qname)

    # populate qname and namespaces table
    try:
        iterate = elem.iter
    except AttributeError:
        iterate = elem.getiterator # cET compatibility
    for elem in iterate():
        tag = elem.tag
        if isinstance(tag, QName) and tag.text not in qnames:
            add_qname(tag.text)
        elif isinstance(tag, util.string_type):
            if tag not in qnames:
                add_qname(tag)
        elif tag is not None and tag is not Comment and tag is not PI:
            _raise_serialization_error(tag)
        for key, value in elem.items():
            if isinstance(key, QName):
                key = key.text
            if key not in qnames:
                add_qname(key)
            if isinstance(value, QName) and value.text not in qnames:
                add_qname(value.text)
        text = elem.text
        if isinstance(text, QName) and text.text not in qnames:
            add_qname(text.text)
    return qnames, namespaces

def to_html_string(element):
    return _write_html(ElementTree(element).getroot(), format="html")

def to_xhtml_string(element):
    return _write_html(ElementTree(element).getroot(), format="xhtml")

########NEW FILE########
__FILENAME__ = treeprocessors
from __future__ import unicode_literals
from __future__ import absolute_import
from . import util
from . import odict
from . import inlinepatterns


def build_treeprocessors(md_instance, **kwargs):
    """ Build the default treeprocessors for Markdown. """
    treeprocessors = odict.OrderedDict()
    treeprocessors["inline"] = InlineProcessor(md_instance)
    treeprocessors["prettify"] = PrettifyTreeprocessor(md_instance)
    return treeprocessors


def isString(s):
    """ Check if it's string """
    if not isinstance(s, util.AtomicString):
        return isinstance(s, util.string_type)
    return False


class Treeprocessor(util.Processor):
    """
    Treeprocessors are run on the ElementTree object before serialization.

    Each Treeprocessor implements a "run" method that takes a pointer to an
    ElementTree, modifies it as necessary and returns an ElementTree
    object.

    Treeprocessors must extend markdown.Treeprocessor.

    """
    def run(self, root):
        """
        Subclasses of Treeprocessor should implement a `run` method, which
        takes a root ElementTree. This method can return another ElementTree 
        object, and the existing root ElementTree will be replaced, or it can 
        modify the current tree and return None.
        """
        pass


class InlineProcessor(Treeprocessor):
    """
    A Treeprocessor that traverses a tree, applying inline patterns.
    """

    def __init__(self, md):
        self.__placeholder_prefix = util.INLINE_PLACEHOLDER_PREFIX
        self.__placeholder_suffix = util.ETX
        self.__placeholder_length = 4 + len(self.__placeholder_prefix) \
                                      + len(self.__placeholder_suffix)
        self.__placeholder_re = util.INLINE_PLACEHOLDER_RE
        self.markdown = md

    def __makePlaceholder(self, type):
        """ Generate a placeholder """
        id = "%04d" % len(self.stashed_nodes)
        hash = util.INLINE_PLACEHOLDER % id
        return hash, id

    def __findPlaceholder(self, data, index):
        """
        Extract id from data string, start from index

        Keyword arguments:

        * data: string
        * index: index, from which we start search

        Returns: placeholder id and string index, after the found placeholder.
        
        """
        m = self.__placeholder_re.search(data, index)
        if m:
            return m.group(1), m.end()
        else:
            return None, index + 1

    def __stashNode(self, node, type):
        """ Add node to stash """
        placeholder, id = self.__makePlaceholder(type)
        self.stashed_nodes[id] = node
        return placeholder

    def __handleInline(self, data, patternIndex=0):
        """
        Process string with inline patterns and replace it
        with placeholders

        Keyword arguments:

        * data: A line of Markdown text
        * patternIndex: The index of the inlinePattern to start with

        Returns: String with placeholders.

        """
        if not isinstance(data, util.AtomicString):
            startIndex = 0
            while patternIndex < len(self.markdown.inlinePatterns):
                data, matched, startIndex = self.__applyPattern(
                    self.markdown.inlinePatterns.value_for_index(patternIndex),
                    data, patternIndex, startIndex)
                if not matched:
                    patternIndex += 1
        return data

    def __processElementText(self, node, subnode, isText=True):
        """
        Process placeholders in Element.text or Element.tail
        of Elements popped from self.stashed_nodes.

        Keywords arguments:

        * node: parent node
        * subnode: processing node
        * isText: bool variable, True - it's text, False - it's tail

        Returns: None

        """
        if isText:
            text = subnode.text
            subnode.text = None
        else:
            text = subnode.tail
            subnode.tail = None

        childResult = self.__processPlaceholders(text, subnode)

        if not isText and node is not subnode:
            pos = node.getchildren().index(subnode)
            node.remove(subnode)
        else:
            pos = 0

        childResult.reverse()
        for newChild in childResult:
            node.insert(pos, newChild)

    def __processPlaceholders(self, data, parent):
        """
        Process string with placeholders and generate ElementTree tree.

        Keyword arguments:

        * data: string with placeholders instead of ElementTree elements.
        * parent: Element, which contains processing inline data

        Returns: list with ElementTree elements with applied inline patterns.
        
        """
        def linkText(text):
            if text:
                if result:
                    if result[-1].tail:
                        result[-1].tail += text
                    else:
                        result[-1].tail = text
                else:
                    if parent.text:
                        parent.text += text
                    else:
                        parent.text = text
        result = []
        strartIndex = 0
        while data:
            index = data.find(self.__placeholder_prefix, strartIndex)
            if index != -1:
                id, phEndIndex = self.__findPlaceholder(data, index)

                if id in self.stashed_nodes:
                    node = self.stashed_nodes.get(id)

                    if index > 0:
                        text = data[strartIndex:index]
                        linkText(text)

                    if not isString(node): # it's Element
                        for child in [node] + node.getchildren():
                            if child.tail:
                                if child.tail.strip():
                                    self.__processElementText(node, child,False)
                            if child.text:
                                if child.text.strip():
                                    self.__processElementText(child, child)
                    else: # it's just a string
                        linkText(node)
                        strartIndex = phEndIndex
                        continue

                    strartIndex = phEndIndex
                    result.append(node)

                else: # wrong placeholder
                    end = index + len(self.__placeholder_prefix)
                    linkText(data[strartIndex:end])
                    strartIndex = end
            else:
                text = data[strartIndex:]
                if isinstance(data, util.AtomicString):
                    # We don't want to loose the AtomicString
                    text = util.AtomicString(text)
                linkText(text)
                data = ""

        return result

    def __applyPattern(self, pattern, data, patternIndex, startIndex=0):
        """
        Check if the line fits the pattern, create the necessary
        elements, add it to stashed_nodes.

        Keyword arguments:

        * data: the text to be processed
        * pattern: the pattern to be checked
        * patternIndex: index of current pattern
        * startIndex: string index, from which we start searching

        Returns: String with placeholders instead of ElementTree elements.

        """
        match = pattern.getCompiledRegExp().match(data[startIndex:])
        leftData = data[:startIndex]

        if not match:
            return data, False, 0

        node = pattern.handleMatch(match)

        if node is None:
            return data, True, len(leftData)+match.span(len(match.groups()))[0]

        if not isString(node):
            if not isinstance(node.text, util.AtomicString):
                # We need to process current node too
                for child in [node] + node.getchildren():
                    if not isString(node):
                        if child.text: 
                            child.text = self.__handleInline(child.text,
                                                            patternIndex + 1)
                        if child.tail:
                            child.tail = self.__handleInline(child.tail,
                                                            patternIndex)

        placeholder = self.__stashNode(node, pattern.type())

        return "%s%s%s%s" % (leftData,
                             match.group(1),
                             placeholder, match.groups()[-1]), True, 0

    def run(self, tree):
        """Apply inline patterns to a parsed Markdown tree.

        Iterate over ElementTree, find elements with inline tag, apply inline
        patterns and append newly created Elements to tree.  If you don't
        want to process your data with inline paterns, instead of normal string,
        use subclass AtomicString:

            node.text = markdown.AtomicString("This will not be processed.")

        Arguments:

        * tree: ElementTree object, representing Markdown tree.

        Returns: ElementTree object with applied inline patterns.

        """
        self.stashed_nodes = {}

        stack = [tree]

        while stack:
            currElement = stack.pop()
            insertQueue = []
            for child in currElement.getchildren():
                if child.text and not isinstance(child.text, util.AtomicString):
                    text = child.text
                    child.text = None
                    lst = self.__processPlaceholders(self.__handleInline(
                                                    text), child)
                    stack += lst
                    insertQueue.append((child, lst))
                if child.tail:
                    tail = self.__handleInline(child.tail)
                    dumby = util.etree.Element('d')
                    tailResult = self.__processPlaceholders(tail, dumby)
                    if dumby.text:
                        child.tail = dumby.text
                    else:
                        child.tail = None
                    pos = currElement.getchildren().index(child) + 1
                    tailResult.reverse()
                    for newChild in tailResult:
                        currElement.insert(pos, newChild)
                if child.getchildren():
                    stack.append(child)

            for element, lst in insertQueue:
                if self.markdown.enable_attributes:
                    if element.text and isString(element.text):
                        element.text = \
                            inlinepatterns.handleAttributes(element.text, 
                                                                    element)
                i = 0
                for newChild in lst:
                    if self.markdown.enable_attributes:
                        # Processing attributes
                        if newChild.tail and isString(newChild.tail):
                            newChild.tail = \
                                inlinepatterns.handleAttributes(newChild.tail,
                                                                    element)
                        if newChild.text and isString(newChild.text):
                            newChild.text = \
                                inlinepatterns.handleAttributes(newChild.text,
                                                                    newChild)
                    element.insert(i, newChild)
                    i += 1
        return tree


class PrettifyTreeprocessor(Treeprocessor):
    """ Add linebreaks to the html document. """

    def _prettifyETree(self, elem):
        """ Recursively add linebreaks to ElementTree children. """

        i = "\n"
        if util.isBlockLevel(elem.tag) and elem.tag not in ['code', 'pre']:
            if (not elem.text or not elem.text.strip()) \
                    and len(elem) and util.isBlockLevel(elem[0].tag):
                elem.text = i
            for e in elem:
                if util.isBlockLevel(e.tag):
                    self._prettifyETree(e)
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
        if not elem.tail or not elem.tail.strip():
            elem.tail = i

    def run(self, root):
        """ Add linebreaks to ElementTree root object. """

        self._prettifyETree(root)
        # Do <br />'s seperately as they are often in the middle of
        # inline content and missed by _prettifyETree.
        brs = root.getiterator('br')
        for br in brs:
            if not br.tail or not br.tail.strip():
                br.tail = '\n'
            else:
                br.tail = '\n%s' % br.tail
        # Clean up extra empty lines at end of code blocks.
        pres = root.getiterator('pre')
        for pre in pres:
            if len(pre) and pre[0].tag == 'code':
                pre[0].text = pre[0].text.rstrip() + '\n'

########NEW FILE########
__FILENAME__ = util
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import re
import sys


"""
Python 3 Stuff
=============================================================================
"""
PY3 = sys.version_info[0] == 3

if PY3:
    string_type = str
    text_type = str
    int2str = chr
else:
    string_type = basestring
    text_type = unicode
    int2str = unichr


"""
Constants you might want to modify
-----------------------------------------------------------------------------
"""

BLOCK_LEVEL_ELEMENTS = re.compile("^(p|div|h[1-6]|blockquote|pre|table|dl|ol|ul"
                                  "|script|noscript|form|fieldset|iframe|math"
                                  "|hr|hr/|style|li|dt|dd|thead|tbody"
                                  "|tr|th|td|section|footer|header|group|figure"
                                  "|figcaption|aside|article|canvas|output"
                                  "|progress|video)$", re.IGNORECASE)
# Placeholders
STX = '\u0002'  # Use STX ("Start of text") for start-of-placeholder
ETX = '\u0003'  # Use ETX ("End of text") for end-of-placeholder
INLINE_PLACEHOLDER_PREFIX = STX+"klzzwxh:"
INLINE_PLACEHOLDER = INLINE_PLACEHOLDER_PREFIX + "%s" + ETX
INLINE_PLACEHOLDER_RE = re.compile(INLINE_PLACEHOLDER % r'([0-9]{4})')
AMP_SUBSTITUTE = STX+"amp"+ETX

"""
Constants you probably do not need to change
-----------------------------------------------------------------------------
"""

RTL_BIDI_RANGES = ( ('\u0590', '\u07FF'),
                     # Hebrew (0590-05FF), Arabic (0600-06FF),
                     # Syriac (0700-074F), Arabic supplement (0750-077F),
                     # Thaana (0780-07BF), Nko (07C0-07FF).
                    ('\u2D30', '\u2D7F'), # Tifinagh
                    )

# Extensions should use "markdown.util.etree" instead of "etree" (or do `from
# markdown.util import etree`).  Do not import it by yourself.

try: # Is the C implemenation of ElementTree available?
    import xml.etree.cElementTree as etree
    from xml.etree.ElementTree import Comment
    # Serializers (including ours) test with non-c Comment
    etree.test_comment = Comment
    if etree.VERSION < "1.0.5":
        raise RuntimeError("cElementTree version 1.0.5 or higher is required.")
except (ImportError, RuntimeError):
    # Use the Python implementation of ElementTree?
    import xml.etree.ElementTree as etree
    if etree.VERSION < "1.1":
        raise RuntimeError("ElementTree version 1.1 or higher is required")


"""
AUXILIARY GLOBAL FUNCTIONS
=============================================================================
"""


def isBlockLevel(tag):
    """Check if the tag is a block level HTML tag."""
    if isinstance(tag, string_type):
        return BLOCK_LEVEL_ELEMENTS.match(tag)
    # Some ElementTree tags are not strings, so return False.
    return False

"""
MISC AUXILIARY CLASSES
=============================================================================
"""

class AtomicString(text_type):
    """A string which should not be further processed."""
    pass


class Processor(object):
    def __init__(self, markdown_instance=None):
        if markdown_instance:
            self.markdown = markdown_instance


class HtmlStash(object):
    """
    This class is used for stashing HTML objects that we extract
    in the beginning and replace with place-holders.
    """

    def __init__ (self):
        """ Create a HtmlStash. """
        self.html_counter = 0 # for counting inline html segments
        self.rawHtmlBlocks=[]

    def store(self, html, safe=False):
        """
        Saves an HTML segment for later reinsertion.  Returns a
        placeholder string that needs to be inserted into the
        document.

        Keyword arguments:

        * html: an html segment
        * safe: label an html segment as safe for safemode

        Returns : a placeholder string

        """
        self.rawHtmlBlocks.append((html, safe))
        placeholder = self.get_placeholder(self.html_counter)
        self.html_counter += 1
        return placeholder

    def reset(self):
        self.html_counter = 0
        self.rawHtmlBlocks = []

    def get_placeholder(self, key):
        return "%swzxhzdk:%d%s" % (STX, key, ETX)


########NEW FILE########
__FILENAME__ = __main__
"""
COMMAND-LINE SPECIFIC STUFF
=============================================================================

"""

import markdown
import sys
import optparse

import logging
from logging import DEBUG, INFO, CRITICAL

logger =  logging.getLogger('MARKDOWN')

def parse_options():
    """
    Define and parse `optparse` options for command-line usage.
    """
    usage = """%prog [options] [INPUTFILE]
       (STDIN is assumed if no INPUTFILE is given)"""
    desc = "A Python implementation of John Gruber's Markdown. " \
           "http://packages.python.org/Markdown/"
    ver = "%%prog %s" % markdown.version
    
    parser = optparse.OptionParser(usage=usage, description=desc, version=ver)
    parser.add_option("-f", "--file", dest="filename", default=None,
                      help="Write output to OUTPUT_FILE. Defaults to STDOUT.",
                      metavar="OUTPUT_FILE")
    parser.add_option("-e", "--encoding", dest="encoding",
                      help="Encoding for input and output files.",)
    parser.add_option("-q", "--quiet", default = CRITICAL,
                      action="store_const", const=CRITICAL+10, dest="verbose",
                      help="Suppress all warnings.")
    parser.add_option("-v", "--verbose",
                      action="store_const", const=INFO, dest="verbose",
                      help="Print all warnings.")
    parser.add_option("-s", "--safe", dest="safe", default=False,
                      metavar="SAFE_MODE",
                      help="'replace', 'remove' or 'escape' HTML tags in input")
    parser.add_option("-o", "--output_format", dest="output_format", 
                      default='xhtml1', metavar="OUTPUT_FORMAT",
                      help="'xhtml1' (default), 'html4' or 'html5'.")
    parser.add_option("--noisy",
                      action="store_const", const=DEBUG, dest="verbose",
                      help="Print debug messages.")
    parser.add_option("-x", "--extension", action="append", dest="extensions",
                      help = "Load extension EXTENSION.", metavar="EXTENSION")
    parser.add_option("-n", "--no_lazy_ol", dest="lazy_ol", 
                      action='store_false', default=True,
                      help="Observe number of first item of ordered lists.")

    (options, args) = parser.parse_args()

    if len(args) == 0:
        input_file = None
    else:
        input_file = args[0]

    if not options.extensions:
        options.extensions = []

    return {'input': input_file,
            'output': options.filename,
            'safe_mode': options.safe,
            'extensions': options.extensions,
            'encoding': options.encoding,
            'output_format': options.output_format,
            'lazy_ol': options.lazy_ol}, options.verbose

def run():
    """Run Markdown from the command line."""

    # Parse options and adjust logging level if necessary
    options, logging_level = parse_options()
    if not options: sys.exit(2)
    logger.setLevel(logging_level)
    logger.addHandler(logging.StreamHandler())

    # Run
    markdown.markdownFromFile(**options)

if __name__ == '__main__':
    # Support running module as a commandline command. 
    # Python 2.5 & 2.6 do: `python -m markdown.__main__ [options] [args]`.
    # Python 2.7 & 3.x do: `python -m markdown [options] [args]`.
    run()

########NEW FILE########
__FILENAME__ = __version__
#
# markdown/__version__.py
#
# version_info should conform to PEP 386 
# (major, minor, micro, alpha/beta/rc/final, #)
# (1, 1, 2, 'alpha', 0) => "1.1.2.dev"
# (1, 2, 0, 'beta', 2) => "1.2b2"
version_info = (2, 3, 1, 'final', 0)

def _get_version():
    " Returns a PEP 386-compliant version number from version_info. "
    assert len(version_info) == 5
    assert version_info[3] in ('alpha', 'beta', 'rc', 'final')

    parts = 2 if version_info[2] == 0 else 3
    main = '.'.join(map(str, version_info[:parts]))

    sub = ''
    if version_info[3] == 'alpha' and version_info[4] == 0:
        # TODO: maybe append some sort of git info here??
        sub = '.dev'
    elif version_info[3] != 'final':
        mapping = {'alpha': 'a', 'beta': 'b', 'rc': 'c'}
        sub = mapping[version_info[3]] + str(version_info[4])

    return str(main + sub)

version = _get_version()

########NEW FILE########
__FILENAME__ = markdown2
#!/usr/bin/env python
# Copyright (c) 2012 Trent Mick.
# Copyright (c) 2007-2008 ActiveState Corp.
# License: MIT (http://www.opensource.org/licenses/mit-license.php)

from __future__ import generators

r"""A fast and complete Python implementation of Markdown.

[from http://daringfireball.net/projects/markdown/]
> Markdown is a text-to-HTML filter; it translates an easy-to-read /
> easy-to-write structured text format into HTML.  Markdown's text
> format is most similar to that of plain text email, and supports
> features such as headers, *emphasis*, code blocks, blockquotes, and
> links.
>
> Markdown's syntax is designed not as a generic markup language, but
> specifically to serve as a front-end to (X)HTML. You can use span-level
> HTML tags anywhere in a Markdown document, and you can use block level
> HTML tags (like <div> and <table> as well).

Module usage:

    >>> import markdown2
    >>> markdown2.markdown("*boo!*")  # or use `html = markdown_path(PATH)`
    u'<p><em>boo!</em></p>\n'

    >>> markdowner = Markdown()
    >>> markdowner.convert("*boo!*")
    u'<p><em>boo!</em></p>\n'
    >>> markdowner.convert("**boom!**")
    u'<p><strong>boom!</strong></p>\n'

This implementation of Markdown implements the full "core" syntax plus a
number of extras (e.g., code syntax coloring, footnotes) as described on
<https://github.com/trentm/python-markdown2/wiki/Extras>.
"""

cmdln_desc = """A fast and complete Python implementation of Markdown, a
text-to-HTML conversion tool for web writers.

Supported extra syntax options (see -x|--extras option below and
see <https://github.com/trentm/python-markdown2/wiki/Extras> for details):

* code-friendly: Disable _ and __ for em and strong.
* cuddled-lists: Allow lists to be cuddled to the preceding paragraph.
* fenced-code-blocks: Allows a code block to not have to be indented
  by fencing it with '```' on a line before and after. Based on
  <http://github.github.com/github-flavored-markdown/> with support for
  syntax highlighting.
* footnotes: Support footnotes as in use on daringfireball.net and
  implemented in other Markdown processors (tho not in Markdown.pl v1.0.1).
* header-ids: Adds "id" attributes to headers. The id value is a slug of
  the header text.
* html-classes: Takes a dict mapping html tag names (lowercase) to a
  string to use for a "class" tag attribute. Currently only supports
  "pre" and "code" tags. Add an issue if you require this for other tags.
* markdown-in-html: Allow the use of `markdown="1"` in a block HTML tag to
  have markdown processing be done on its contents. Similar to
  <http://michelf.com/projects/php-markdown/extra/#markdown-attr> but with
  some limitations.
* metadata: Extract metadata from a leading '---'-fenced block.
  See <https://github.com/trentm/python-markdown2/issues/77> for details.
* nofollow: Add `rel="nofollow"` to add `<a>` tags with an href. See
  <http://en.wikipedia.org/wiki/Nofollow>.
* pyshell: Treats unindented Python interactive shell sessions as <code>
  blocks.
* link-patterns: Auto-link given regex patterns in text (e.g. bug number
  references, revision number references).
* smarty-pants: Replaces ' and " with curly quotation marks or curly
  apostrophes.  Replaces --, ---, ..., and . . . with en dashes, em dashes,
  and ellipses.
* toc: The returned HTML string gets a new "toc_html" attribute which is
  a Table of Contents for the document. (experimental)
* xml: Passes one-liner processing instructions and namespaced XML tags.
* wiki-tables: Google Code Wiki-style tables. See
  <http://code.google.com/p/support/wiki/WikiSyntax#Tables>.
"""

# Dev Notes:
# - Python's regex syntax doesn't have '\z', so I'm using '\Z'. I'm
#   not yet sure if there implications with this. Compare 'pydoc sre'
#   and 'perldoc perlre'.

__version_info__ = (2, 1, 1)
__version__ = '.'.join(map(str, __version_info__))
__author__ = "Trent Mick"

import os
import sys
from pprint import pprint
import re
import logging
try:
    from hashlib import md5
except ImportError:
    from md5 import md5
import optparse
from random import random, randint
import codecs


#---- Python version compat

try:
    from urllib.parse import quote # python3
except ImportError:
    from urllib import quote # python2

if sys.version_info[:2] < (2,4):
    from sets import Set as set
    def reversed(sequence):
        for i in sequence[::-1]:
            yield i

# Use `bytes` for byte strings and `unicode` for unicode strings (str in Py3).
if sys.version_info[0] <= 2:
    py3 = False
    try:
        bytes
    except NameError:
        bytes = str
    base_string_type = basestring
elif sys.version_info[0] >= 3:
    py3 = True
    unicode = str
    base_string_type = str



#---- globals

DEBUG = False
log = logging.getLogger("markdown")

DEFAULT_TAB_WIDTH = 4


SECRET_SALT = bytes(randint(0, 1000000))
def _hash_text(s):
    return 'md5-' + md5(SECRET_SALT + s.encode("utf-8")).hexdigest()

# Table of hash values for escaped characters:
g_escape_table = dict([(ch, _hash_text(ch))
    for ch in '\\`*_{}[]()>#+-.!'])



#---- exceptions

class MarkdownError(Exception):
    pass



#---- public api

def markdown_path(path, encoding="utf-8",
                  html4tags=False, tab_width=DEFAULT_TAB_WIDTH,
                  safe_mode=None, extras=None, link_patterns=None,
                  use_file_vars=False):
    fp = codecs.open(path, 'r', encoding)
    text = fp.read()
    fp.close()
    return Markdown(html4tags=html4tags, tab_width=tab_width,
                    safe_mode=safe_mode, extras=extras,
                    link_patterns=link_patterns,
                    use_file_vars=use_file_vars).convert(text)

def markdown(text, html4tags=False, tab_width=DEFAULT_TAB_WIDTH,
             safe_mode=None, extras=None, link_patterns=None,
             use_file_vars=False):
    return Markdown(html4tags=html4tags, tab_width=tab_width,
                    safe_mode=safe_mode, extras=extras,
                    link_patterns=link_patterns,
                    use_file_vars=use_file_vars).convert(text)

class Markdown(object):
    # The dict of "extras" to enable in processing -- a mapping of
    # extra name to argument for the extra. Most extras do not have an
    # argument, in which case the value is None.
    #
    # This can be set via (a) subclassing and (b) the constructor
    # "extras" argument.
    extras = None

    urls = None
    titles = None
    html_blocks = None
    html_spans = None
    html_removed_text = "[HTML_REMOVED]"  # for compat with markdown.py

    # Used to track when we're inside an ordered or unordered list
    # (see _ProcessListItems() for details):
    list_level = 0

    _ws_only_line_re = re.compile(r"^[ \t]+$", re.M)

    def __init__(self, html4tags=False, tab_width=4, safe_mode=None,
                 extras=None, link_patterns=None, use_file_vars=False):
        if html4tags:
            self.empty_element_suffix = ">"
        else:
            self.empty_element_suffix = " />"
        self.tab_width = tab_width

        # For compatibility with earlier markdown2.py and with
        # markdown.py's safe_mode being a boolean,
        #   safe_mode == True -> "replace"
        if safe_mode is True:
            self.safe_mode = "replace"
        else:
            self.safe_mode = safe_mode

        # Massaging and building the "extras" info.
        if self.extras is None:
            self.extras = {}
        elif not isinstance(self.extras, dict):
            self.extras = dict([(e, None) for e in self.extras])
        if extras:
            if not isinstance(extras, dict):
                extras = dict([(e, None) for e in extras])
            self.extras.update(extras)
        assert isinstance(self.extras, dict)
        if "toc" in self.extras and not "header-ids" in self.extras:
            self.extras["header-ids"] = None   # "toc" implies "header-ids"
        self._instance_extras = self.extras.copy()

        self.link_patterns = link_patterns
        self.use_file_vars = use_file_vars
        self._outdent_re = re.compile(r'^(\t|[ ]{1,%d})' % tab_width, re.M)

        self._escape_table = g_escape_table.copy()
        if "smarty-pants" in self.extras:
            self._escape_table['"'] = _hash_text('"')
            self._escape_table["'"] = _hash_text("'")

    def reset(self):
        self.urls = {}
        self.titles = {}
        self.html_blocks = {}
        self.html_spans = {}
        self.list_level = 0
        self.extras = self._instance_extras.copy()
        if "footnotes" in self.extras:
            self.footnotes = {}
            self.footnote_ids = []
        if "header-ids" in self.extras:
            self._count_from_header_id = {} # no `defaultdict` in Python 2.4
        if "metadata" in self.extras:
            self.metadata = {}

    # Per <https://developer.mozilla.org/en-US/docs/HTML/Element/a> "rel"
    # should only be used in <a> tags with an "href" attribute.
    _a_nofollow = re.compile(r"<(a)([^>]*href=)", re.IGNORECASE)

    def convert(self, text):
        """Convert the given text."""
        # Main function. The order in which other subs are called here is
        # essential. Link and image substitutions need to happen before
        # _EscapeSpecialChars(), so that any *'s or _'s in the <a>
        # and <img> tags get encoded.

        # Clear the global hashes. If we don't clear these, you get conflicts
        # from other articles when generating a page which contains more than
        # one article (e.g. an index page that shows the N most recent
        # articles):
        self.reset()

        if not isinstance(text, unicode):
            #TODO: perhaps shouldn't presume UTF-8 for string input?
            text = unicode(text, 'utf-8')

        if self.use_file_vars:
            # Look for emacs-style file variable hints.
            emacs_vars = self._get_emacs_vars(text)
            if "markdown-extras" in emacs_vars:
                splitter = re.compile("[ ,]+")
                for e in splitter.split(emacs_vars["markdown-extras"]):
                    if '=' in e:
                        ename, earg = e.split('=', 1)
                        try:
                            earg = int(earg)
                        except ValueError:
                            pass
                    else:
                        ename, earg = e, None
                    self.extras[ename] = earg

        # Standardize line endings:
        text = re.sub("\r\n|\r", "\n", text)

        # Make sure $text ends with a couple of newlines:
        text += "\n\n"

        # Convert all tabs to spaces.
        text = self._detab(text)

        # Strip any lines consisting only of spaces and tabs.
        # This makes subsequent regexen easier to write, because we can
        # match consecutive blank lines with /\n+/ instead of something
        # contorted like /[ \t]*\n+/ .
        text = self._ws_only_line_re.sub("", text)

        # strip metadata from head and extract
        if "metadata" in self.extras:
            text = self._extract_metadata(text)

        text = self.preprocess(text)

        if self.safe_mode:
            text = self._hash_html_spans(text)

        # Turn block-level HTML blocks into hash entries
        text = self._hash_html_blocks(text, raw=True)

        # Strip link definitions, store in hashes.
        if "footnotes" in self.extras:
            # Must do footnotes first because an unlucky footnote defn
            # looks like a link defn:
            #   [^4]: this "looks like a link defn"
            text = self._strip_footnote_definitions(text)
        text = self._strip_link_definitions(text)

        text = self._run_block_gamut(text)

        if "footnotes" in self.extras:
            text = self._add_footnotes(text)

        text = self.postprocess(text)

        text = self._unescape_special_chars(text)

        if self.safe_mode:
            text = self._unhash_html_spans(text)

        if "nofollow" in self.extras:
            text = self._a_nofollow.sub(r'<\1 rel="nofollow"\2', text)

        text += "\n"

        rv = UnicodeWithAttrs(text)
        if "toc" in self.extras:
            rv._toc = self._toc
        if "metadata" in self.extras:
            rv.metadata = self.metadata
        return rv

    def postprocess(self, text):
        """A hook for subclasses to do some postprocessing of the html, if
        desired. This is called before unescaping of special chars and
        unhashing of raw HTML spans.
        """
        return text

    def preprocess(self, text):
        """A hook for subclasses to do some preprocessing of the Markdown, if
        desired. This is called after basic formatting of the text, but prior
        to any extras, safe mode, etc. processing.
        """
        return text

    # Is metadata if the content starts with '---'-fenced `key: value`
    # pairs. E.g. (indented for presentation):
    #   ---
    #   foo: bar
    #   another-var: blah blah
    #   ---
    _metadata_pat = re.compile("""^---[ \t]*\n((?:[ \t]*[^ \t:]+[ \t]*:[^\n]*\n)+)---[ \t]*\n""")

    def _extract_metadata(self, text):
        # fast test
        if not text.startswith("---"):
            return text
        match = self._metadata_pat.match(text)
        if not match:
            return text

        tail = text[len(match.group(0)):]
        metadata_str = match.group(1).strip()
        for line in metadata_str.split('\n'):
            key, value = line.split(':', 1)
            self.metadata[key.strip()] = value.strip()

        return tail


    _emacs_oneliner_vars_pat = re.compile(r"-\*-\s*([^\r\n]*?)\s*-\*-", re.UNICODE)
    # This regular expression is intended to match blocks like this:
    #    PREFIX Local Variables: SUFFIX
    #    PREFIX mode: Tcl SUFFIX
    #    PREFIX End: SUFFIX
    # Some notes:
    # - "[ \t]" is used instead of "\s" to specifically exclude newlines
    # - "(\r\n|\n|\r)" is used instead of "$" because the sre engine does
    #   not like anything other than Unix-style line terminators.
    _emacs_local_vars_pat = re.compile(r"""^
        (?P<prefix>(?:[^\r\n|\n|\r])*?)
        [\ \t]*Local\ Variables:[\ \t]*
        (?P<suffix>.*?)(?:\r\n|\n|\r)
        (?P<content>.*?\1End:)
        """, re.IGNORECASE | re.MULTILINE | re.DOTALL | re.VERBOSE)

    def _get_emacs_vars(self, text):
        """Return a dictionary of emacs-style local variables.

        Parsing is done loosely according to this spec (and according to
        some in-practice deviations from this):
        http://www.gnu.org/software/emacs/manual/html_node/emacs/Specifying-File-Variables.html#Specifying-File-Variables
        """
        emacs_vars = {}
        SIZE = pow(2, 13) # 8kB

        # Search near the start for a '-*-'-style one-liner of variables.
        head = text[:SIZE]
        if "-*-" in head:
            match = self._emacs_oneliner_vars_pat.search(head)
            if match:
                emacs_vars_str = match.group(1)
                assert '\n' not in emacs_vars_str
                emacs_var_strs = [s.strip() for s in emacs_vars_str.split(';')
                                  if s.strip()]
                if len(emacs_var_strs) == 1 and ':' not in emacs_var_strs[0]:
                    # While not in the spec, this form is allowed by emacs:
                    #   -*- Tcl -*-
                    # where the implied "variable" is "mode". This form
                    # is only allowed if there are no other variables.
                    emacs_vars["mode"] = emacs_var_strs[0].strip()
                else:
                    for emacs_var_str in emacs_var_strs:
                        try:
                            variable, value = emacs_var_str.strip().split(':', 1)
                        except ValueError:
                            log.debug("emacs variables error: malformed -*- "
                                      "line: %r", emacs_var_str)
                            continue
                        # Lowercase the variable name because Emacs allows "Mode"
                        # or "mode" or "MoDe", etc.
                        emacs_vars[variable.lower()] = value.strip()

        tail = text[-SIZE:]
        if "Local Variables" in tail:
            match = self._emacs_local_vars_pat.search(tail)
            if match:
                prefix = match.group("prefix")
                suffix = match.group("suffix")
                lines = match.group("content").splitlines(0)
                #print "prefix=%r, suffix=%r, content=%r, lines: %s"\
                #      % (prefix, suffix, match.group("content"), lines)

                # Validate the Local Variables block: proper prefix and suffix
                # usage.
                for i, line in enumerate(lines):
                    if not line.startswith(prefix):
                        log.debug("emacs variables error: line '%s' "
                                  "does not use proper prefix '%s'"
                                  % (line, prefix))
                        return {}
                    # Don't validate suffix on last line. Emacs doesn't care,
                    # neither should we.
                    if i != len(lines)-1 and not line.endswith(suffix):
                        log.debug("emacs variables error: line '%s' "
                                  "does not use proper suffix '%s'"
                                  % (line, suffix))
                        return {}

                # Parse out one emacs var per line.
                continued_for = None
                for line in lines[:-1]: # no var on the last line ("PREFIX End:")
                    if prefix: line = line[len(prefix):] # strip prefix
                    if suffix: line = line[:-len(suffix)] # strip suffix
                    line = line.strip()
                    if continued_for:
                        variable = continued_for
                        if line.endswith('\\'):
                            line = line[:-1].rstrip()
                        else:
                            continued_for = None
                        emacs_vars[variable] += ' ' + line
                    else:
                        try:
                            variable, value = line.split(':', 1)
                        except ValueError:
                            log.debug("local variables error: missing colon "
                                      "in local variables entry: '%s'" % line)
                            continue
                        # Do NOT lowercase the variable name, because Emacs only
                        # allows "mode" (and not "Mode", "MoDe", etc.) in this block.
                        value = value.strip()
                        if value.endswith('\\'):
                            value = value[:-1].rstrip()
                            continued_for = variable
                        else:
                            continued_for = None
                        emacs_vars[variable] = value

        # Unquote values.
        for var, val in list(emacs_vars.items()):
            if len(val) > 1 and (val.startswith('"') and val.endswith('"')
               or val.startswith('"') and val.endswith('"')):
                emacs_vars[var] = val[1:-1]

        return emacs_vars

    # Cribbed from a post by Bart Lateur:
    # <http://www.nntp.perl.org/group/perl.macperl.anyperl/154>
    _detab_re = re.compile(r'(.*?)\t', re.M)
    def _detab_sub(self, match):
        g1 = match.group(1)
        return g1 + (' ' * (self.tab_width - len(g1) % self.tab_width))
    def _detab(self, text):
        r"""Remove (leading?) tabs from a file.

            >>> m = Markdown()
            >>> m._detab("\tfoo")
            '    foo'
            >>> m._detab("  \tfoo")
            '    foo'
            >>> m._detab("\t  foo")
            '      foo'
            >>> m._detab("  foo")
            '  foo'
            >>> m._detab("  foo\n\tbar\tblam")
            '  foo\n    bar blam'
        """
        if '\t' not in text:
            return text
        return self._detab_re.subn(self._detab_sub, text)[0]

    # I broke out the html5 tags here and add them to _block_tags_a and
    # _block_tags_b.  This way html5 tags are easy to keep track of.
    _html5tags = '|article|aside|header|hgroup|footer|nav|section|figure|figcaption'

    _block_tags_a = 'p|div|h[1-6]|blockquote|pre|table|dl|ol|ul|script|noscript|form|fieldset|iframe|math|ins|del'
    _block_tags_a += _html5tags

    _strict_tag_block_re = re.compile(r"""
        (                       # save in \1
            ^                   # start of line  (with re.M)
            <(%s)               # start tag = \2
            \b                  # word break
            (.*\n)*?            # any number of lines, minimally matching
            </\2>               # the matching end tag
            [ \t]*              # trailing spaces/tabs
            (?=\n+|\Z)          # followed by a newline or end of document
        )
        """ % _block_tags_a,
        re.X | re.M)

    _block_tags_b = 'p|div|h[1-6]|blockquote|pre|table|dl|ol|ul|script|noscript|form|fieldset|iframe|math'
    _block_tags_b += _html5tags

    _liberal_tag_block_re = re.compile(r"""
        (                       # save in \1
            ^                   # start of line  (with re.M)
            <(%s)               # start tag = \2
            \b                  # word break
            (.*\n)*?            # any number of lines, minimally matching
            .*</\2>             # the matching end tag
            [ \t]*              # trailing spaces/tabs
            (?=\n+|\Z)          # followed by a newline or end of document
        )
        """ % _block_tags_b,
        re.X | re.M)

    _html_markdown_attr_re = re.compile(
        r'''\s+markdown=("1"|'1')''')
    def _hash_html_block_sub(self, match, raw=False):
        html = match.group(1)
        if raw and self.safe_mode:
            html = self._sanitize_html(html)
        elif 'markdown-in-html' in self.extras and 'markdown=' in html:
            first_line = html.split('\n', 1)[0]
            m = self._html_markdown_attr_re.search(first_line)
            if m:
                lines = html.split('\n')
                middle = '\n'.join(lines[1:-1])
                last_line = lines[-1]
                first_line = first_line[:m.start()] + first_line[m.end():]
                f_key = _hash_text(first_line)
                self.html_blocks[f_key] = first_line
                l_key = _hash_text(last_line)
                self.html_blocks[l_key] = last_line
                return ''.join(["\n\n", f_key,
                    "\n\n", middle, "\n\n",
                    l_key, "\n\n"])
        key = _hash_text(html)
        self.html_blocks[key] = html
        return "\n\n" + key + "\n\n"

    def _hash_html_blocks(self, text, raw=False):
        """Hashify HTML blocks

        We only want to do this for block-level HTML tags, such as headers,
        lists, and tables. That's because we still want to wrap <p>s around
        "paragraphs" that are wrapped in non-block-level tags, such as anchors,
        phrase emphasis, and spans. The list of tags we're looking for is
        hard-coded.

        @param raw {boolean} indicates if these are raw HTML blocks in
            the original source. It makes a difference in "safe" mode.
        """
        if '<' not in text:
            return text

        # Pass `raw` value into our calls to self._hash_html_block_sub.
        hash_html_block_sub = _curry(self._hash_html_block_sub, raw=raw)

        # First, look for nested blocks, e.g.:
        #   <div>
        #       <div>
        #       tags for inner block must be indented.
        #       </div>
        #   </div>
        #
        # The outermost tags must start at the left margin for this to match, and
        # the inner nested divs must be indented.
        # We need to do this before the next, more liberal match, because the next
        # match will start at the first `<div>` and stop at the first `</div>`.
        text = self._strict_tag_block_re.sub(hash_html_block_sub, text)

        # Now match more liberally, simply from `\n<tag>` to `</tag>\n`
        text = self._liberal_tag_block_re.sub(hash_html_block_sub, text)

        # Special case just for <hr />. It was easier to make a special
        # case than to make the other regex more complicated.
        if "<hr" in text:
            _hr_tag_re = _hr_tag_re_from_tab_width(self.tab_width)
            text = _hr_tag_re.sub(hash_html_block_sub, text)

        # Special case for standalone HTML comments:
        if "<!--" in text:
            start = 0
            while True:
                # Delimiters for next comment block.
                try:
                    start_idx = text.index("<!--", start)
                except ValueError:
                    break
                try:
                    end_idx = text.index("-->", start_idx) + 3
                except ValueError:
                    break

                # Start position for next comment block search.
                start = end_idx

                # Validate whitespace before comment.
                if start_idx:
                    # - Up to `tab_width - 1` spaces before start_idx.
                    for i in range(self.tab_width - 1):
                        if text[start_idx - 1] != ' ':
                            break
                        start_idx -= 1
                        if start_idx == 0:
                            break
                    # - Must be preceded by 2 newlines or hit the start of
                    #   the document.
                    if start_idx == 0:
                        pass
                    elif start_idx == 1 and text[0] == '\n':
                        start_idx = 0  # to match minute detail of Markdown.pl regex
                    elif text[start_idx-2:start_idx] == '\n\n':
                        pass
                    else:
                        break

                # Validate whitespace after comment.
                # - Any number of spaces and tabs.
                while end_idx < len(text):
                    if text[end_idx] not in ' \t':
                        break
                    end_idx += 1
                # - Must be following by 2 newlines or hit end of text.
                if text[end_idx:end_idx+2] not in ('', '\n', '\n\n'):
                    continue

                # Escape and hash (must match `_hash_html_block_sub`).
                html = text[start_idx:end_idx]
                if raw and self.safe_mode:
                    html = self._sanitize_html(html)
                key = _hash_text(html)
                self.html_blocks[key] = html
                text = text[:start_idx] + "\n\n" + key + "\n\n" + text[end_idx:]

        if "xml" in self.extras:
            # Treat XML processing instructions and namespaced one-liner
            # tags as if they were block HTML tags. E.g., if standalone
            # (i.e. are their own paragraph), the following do not get
            # wrapped in a <p> tag:
            #    <?foo bar?>
            #
            #    <xi:include xmlns:xi="http://www.w3.org/2001/XInclude" href="chapter_1.md"/>
            _xml_oneliner_re = _xml_oneliner_re_from_tab_width(self.tab_width)
            text = _xml_oneliner_re.sub(hash_html_block_sub, text)

        return text

    def _strip_link_definitions(self, text):
        # Strips link definitions from text, stores the URLs and titles in
        # hash references.
        less_than_tab = self.tab_width - 1

        # Link defs are in the form:
        #   [id]: url "optional title"
        _link_def_re = re.compile(r"""
            ^[ ]{0,%d}\[(.+)\]: # id = \1
              [ \t]*
              \n?               # maybe *one* newline
              [ \t]*
            <?(.+?)>?           # url = \2
              [ \t]*
            (?:
                \n?             # maybe one newline
                [ \t]*
                (?<=\s)         # lookbehind for whitespace
                ['"(]
                ([^\n]*)        # title = \3
                ['")]
                [ \t]*
            )?  # title is optional
            (?:\n+|\Z)
            """ % less_than_tab, re.X | re.M | re.U)
        return _link_def_re.sub(self._extract_link_def_sub, text)

    def _extract_link_def_sub(self, match):
        id, url, title = match.groups()
        key = id.lower()    # Link IDs are case-insensitive
        self.urls[key] = self._encode_amps_and_angles(url)
        if title:
            self.titles[key] = title
        return ""

    def _extract_footnote_def_sub(self, match):
        id, text = match.groups()
        text = _dedent(text, skip_first_line=not text.startswith('\n')).strip()
        normed_id = re.sub(r'\W', '-', id)
        # Ensure footnote text ends with a couple newlines (for some
        # block gamut matches).
        self.footnotes[normed_id] = text + "\n\n"
        return ""

    def _strip_footnote_definitions(self, text):
        """A footnote definition looks like this:

            [^note-id]: Text of the note.

                May include one or more indented paragraphs.

        Where,
        - The 'note-id' can be pretty much anything, though typically it
          is the number of the footnote.
        - The first paragraph may start on the next line, like so:

            [^note-id]:
                Text of the note.
        """
        less_than_tab = self.tab_width - 1
        footnote_def_re = re.compile(r'''
            ^[ ]{0,%d}\[\^(.+)\]:   # id = \1
            [ \t]*
            (                       # footnote text = \2
              # First line need not start with the spaces.
              (?:\s*.*\n+)
              (?:
                (?:[ ]{%d} | \t)  # Subsequent lines must be indented.
                .*\n+
              )*
            )
            # Lookahead for non-space at line-start, or end of doc.
            (?:(?=^[ ]{0,%d}\S)|\Z)
            ''' % (less_than_tab, self.tab_width, self.tab_width),
            re.X | re.M)
        return footnote_def_re.sub(self._extract_footnote_def_sub, text)


    _hr_data = [
        ('*', re.compile(r"^[ ]{0,3}\*(.*?)$", re.M)),
        ('-', re.compile(r"^[ ]{0,3}\-(.*?)$", re.M)),
        ('_', re.compile(r"^[ ]{0,3}\_(.*?)$", re.M)),
    ]

    def _run_block_gamut(self, text):
        # These are all the transformations that form block-level
        # tags like paragraphs, headers, and list items.

        if "fenced-code-blocks" in self.extras:
            text = self._do_fenced_code_blocks(text)

        text = self._do_headers(text)

        # Do Horizontal Rules:
        # On the number of spaces in horizontal rules: The spec is fuzzy: "If
        # you wish, you may use spaces between the hyphens or asterisks."
        # Markdown.pl 1.0.1's hr regexes limit the number of spaces between the
        # hr chars to one or two. We'll reproduce that limit here.
        hr = "\n<hr"+self.empty_element_suffix+"\n"
        for ch, regex in self._hr_data:
            if ch in text:
                for m in reversed(list(regex.finditer(text))):
                    tail = m.group(1).rstrip()
                    if not tail.strip(ch + ' ') and tail.count("   ") == 0:
                        start, end = m.span()
                        text = text[:start] + hr + text[end:]

        text = self._do_lists(text)

        if "pyshell" in self.extras:
            text = self._prepare_pyshell_blocks(text)
        if "wiki-tables" in self.extras:
            text = self._do_wiki_tables(text)

        text = self._do_code_blocks(text)

        text = self._do_block_quotes(text)

        # We already ran _HashHTMLBlocks() before, in Markdown(), but that
        # was to escape raw HTML in the original Markdown source. This time,
        # we're escaping the markup we've just created, so that we don't wrap
        # <p> tags around block-level tags.
        text = self._hash_html_blocks(text)

        text = self._form_paragraphs(text)

        return text

    def _pyshell_block_sub(self, match):
        lines = match.group(0).splitlines(0)
        _dedentlines(lines)
        indent = ' ' * self.tab_width
        s = ('\n' # separate from possible cuddled paragraph
             + indent + ('\n'+indent).join(lines)
             + '\n\n')
        return s

    def _prepare_pyshell_blocks(self, text):
        """Ensure that Python interactive shell sessions are put in
        code blocks -- even if not properly indented.
        """
        if ">>>" not in text:
            return text

        less_than_tab = self.tab_width - 1
        _pyshell_block_re = re.compile(r"""
            ^([ ]{0,%d})>>>[ ].*\n   # first line
            ^(\1.*\S+.*\n)*         # any number of subsequent lines
            ^\n                     # ends with a blank line
            """ % less_than_tab, re.M | re.X)

        return _pyshell_block_re.sub(self._pyshell_block_sub, text)

    def _wiki_table_sub(self, match):
        ttext = match.group(0).strip()
        #print 'wiki table: %r' % match.group(0)
        rows = []
        for line in ttext.splitlines(0):
            line = line.strip()[2:-2].strip()
            row = [c.strip() for c in re.split(r'(?<!\\)\|\|', line)]
            rows.append(row)
        #pprint(rows)
        hlines = ['<table>', '<tbody>']
        for row in rows:
            hrow = ['<tr>']
            for cell in row:
                hrow.append('<td>')
                hrow.append(self._run_span_gamut(cell))
                hrow.append('</td>')
            hrow.append('</tr>')
            hlines.append(''.join(hrow))
        hlines += ['</tbody>', '</table>']
        return '\n'.join(hlines) + '\n'

    def _do_wiki_tables(self, text):
        # Optimization.
        if "||" not in text:
            return text

        less_than_tab = self.tab_width - 1
        wiki_table_re = re.compile(r'''
            (?:(?<=\n\n)|\A\n?)            # leading blank line
            ^([ ]{0,%d})\|\|.+?\|\|[ ]*\n  # first line
            (^\1\|\|.+?\|\|\n)*        # any number of subsequent lines
            ''' % less_than_tab, re.M | re.X)
        return wiki_table_re.sub(self._wiki_table_sub, text)

    def _run_span_gamut(self, text):
        # These are all the transformations that occur *within* block-level
        # tags like paragraphs, headers, and list items.

        text = self._do_code_spans(text)

        text = self._escape_special_chars(text)

        # Process anchor and image tags.
        text = self._do_links(text)

        # Make links out of things like `<http://example.com/>`
        # Must come after _do_links(), because you can use < and >
        # delimiters in inline links like [this](<url>).
        text = self._do_auto_links(text)

        if "link-patterns" in self.extras:
            text = self._do_link_patterns(text)

        text = self._encode_amps_and_angles(text)

        text = self._do_italics_and_bold(text)

        if "smarty-pants" in self.extras:
            text = self._do_smart_punctuation(text)

        # Do hard breaks:
        text = re.sub(r" {2,}\n", " <br%s\n" % self.empty_element_suffix, text)

        return text

    # "Sorta" because auto-links are identified as "tag" tokens.
    _sorta_html_tokenize_re = re.compile(r"""
        (
            # tag
            </?
            (?:\w+)                                     # tag name
            (?:\s+(?:[\w-]+:)?[\w-]+=(?:".*?"|'.*?'))*  # attributes
            \s*/?>
            |
            # auto-link (e.g., <http://www.activestate.com/>)
            <\w+[^>]*>
            |
            <!--.*?-->      # comment
            |
            <\?.*?\?>       # processing instruction
        )
        """, re.X)

    def _escape_special_chars(self, text):
        # Python markdown note: the HTML tokenization here differs from
        # that in Markdown.pl, hence the behaviour for subtle cases can
        # differ (I believe the tokenizer here does a better job because
        # it isn't susceptible to unmatched '<' and '>' in HTML tags).
        # Note, however, that '>' is not allowed in an auto-link URL
        # here.
        escaped = []
        is_html_markup = False
        for token in self._sorta_html_tokenize_re.split(text):
            if is_html_markup:
                # Within tags/HTML-comments/auto-links, encode * and _
                # so they don't conflict with their use in Markdown for
                # italics and strong.  We're replacing each such
                # character with its corresponding MD5 checksum value;
                # this is likely overkill, but it should prevent us from
                # colliding with the escape values by accident.
                escaped.append(token.replace('*', self._escape_table['*'])
                                    .replace('_', self._escape_table['_']))
            else:
                escaped.append(self._encode_backslash_escapes(token))
            is_html_markup = not is_html_markup
        return ''.join(escaped)

    def _hash_html_spans(self, text):
        # Used for safe_mode.

        def _is_auto_link(s):
            if ':' in s and self._auto_link_re.match(s):
                return True
            elif '@' in s and self._auto_email_link_re.match(s):
                return True
            return False

        tokens = []
        is_html_markup = False
        for token in self._sorta_html_tokenize_re.split(text):
            if is_html_markup and not _is_auto_link(token):
                sanitized = self._sanitize_html(token)
                key = _hash_text(sanitized)
                self.html_spans[key] = sanitized
                tokens.append(key)
            else:
                tokens.append(token)
            is_html_markup = not is_html_markup
        return ''.join(tokens)

    def _unhash_html_spans(self, text):
        for key, sanitized in list(self.html_spans.items()):
            text = text.replace(key, sanitized)
        return text

    def _sanitize_html(self, s):
        if self.safe_mode == "replace":
            return self.html_removed_text
        elif self.safe_mode == "escape":
            replacements = [
                ('&', '&amp;'),
                ('<', '&lt;'),
                ('>', '&gt;'),
            ]
            for before, after in replacements:
                s = s.replace(before, after)
            return s
        else:
            raise MarkdownError("invalid value for 'safe_mode': %r (must be "
                                "'escape' or 'replace')" % self.safe_mode)

    _tail_of_inline_link_re = re.compile(r'''
          # Match tail of: [text](/url/) or [text](/url/ "title")
          \(            # literal paren
            [ \t]*
            (?P<url>            # \1
                <.*?>
                |
                .*?
            )
            [ \t]*
            (                   # \2
              (['"])            # quote char = \3
              (?P<title>.*?)
              \3                # matching quote
            )?                  # title is optional
          \)
        ''', re.X | re.S)
    _tail_of_reference_link_re = re.compile(r'''
          # Match tail of: [text][id]
          [ ]?          # one optional space
          (?:\n[ ]*)?   # one optional newline followed by spaces
          \[
            (?P<id>.*?)
          \]
        ''', re.X | re.S)

    def _do_links(self, text):
        """Turn Markdown link shortcuts into XHTML <a> and <img> tags.

        This is a combination of Markdown.pl's _DoAnchors() and
        _DoImages(). They are done together because that simplified the
        approach. It was necessary to use a different approach than
        Markdown.pl because of the lack of atomic matching support in
        Python's regex engine used in $g_nested_brackets.
        """
        MAX_LINK_TEXT_SENTINEL = 3000  # markdown2 issue 24

        # `anchor_allowed_pos` is used to support img links inside
        # anchors, but not anchors inside anchors. An anchor's start
        # pos must be `>= anchor_allowed_pos`.
        anchor_allowed_pos = 0

        curr_pos = 0
        while True: # Handle the next link.
            # The next '[' is the start of:
            # - an inline anchor:   [text](url "title")
            # - a reference anchor: [text][id]
            # - an inline img:      ![text](url "title")
            # - a reference img:    ![text][id]
            # - a footnote ref:     [^id]
            #   (Only if 'footnotes' extra enabled)
            # - a footnote defn:    [^id]: ...
            #   (Only if 'footnotes' extra enabled) These have already
            #   been stripped in _strip_footnote_definitions() so no
            #   need to watch for them.
            # - a link definition:  [id]: url "title"
            #   These have already been stripped in
            #   _strip_link_definitions() so no need to watch for them.
            # - not markup:         [...anything else...
            try:
                start_idx = text.index('[', curr_pos)
            except ValueError:
                break
            text_length = len(text)

            # Find the matching closing ']'.
            # Markdown.pl allows *matching* brackets in link text so we
            # will here too. Markdown.pl *doesn't* currently allow
            # matching brackets in img alt text -- we'll differ in that
            # regard.
            bracket_depth = 0
            for p in range(start_idx+1, min(start_idx+MAX_LINK_TEXT_SENTINEL,
                                            text_length)):
                ch = text[p]
                if ch == ']':
                    bracket_depth -= 1
                    if bracket_depth < 0:
                        break
                elif ch == '[':
                    bracket_depth += 1
            else:
                # Closing bracket not found within sentinel length.
                # This isn't markup.
                curr_pos = start_idx + 1
                continue
            link_text = text[start_idx+1:p]

            # Possibly a footnote ref?
            if "footnotes" in self.extras and link_text.startswith("^"):
                normed_id = re.sub(r'\W', '-', link_text[1:])
                if normed_id in self.footnotes:
                    self.footnote_ids.append(normed_id)
                    result = '<sup class="footnote-ref" id="fnref-%s">' \
                             '<a href="#fn-%s">%s</a></sup>' \
                             % (normed_id, normed_id, len(self.footnote_ids))
                    text = text[:start_idx] + result + text[p+1:]
                else:
                    # This id isn't defined, leave the markup alone.
                    curr_pos = p+1
                continue

            # Now determine what this is by the remainder.
            p += 1
            if p == text_length:
                return text

            # Inline anchor or img?
            if text[p] == '(': # attempt at perf improvement
                match = self._tail_of_inline_link_re.match(text, p)
                if match:
                    # Handle an inline anchor or img.
                    is_img = start_idx > 0 and text[start_idx-1] == "!"
                    if is_img:
                        start_idx -= 1

                    url, title = match.group("url"), match.group("title")
                    if url and url[0] == '<':
                        url = url[1:-1]  # '<url>' -> 'url'
                    # We've got to encode these to avoid conflicting
                    # with italics/bold.
                    url = url.replace('*', self._escape_table['*']) \
                             .replace('_', self._escape_table['_'])
                    if title:
                        title_str = ' title="%s"' % (
                            _xml_escape_attr(title)
                                .replace('*', self._escape_table['*'])
                                .replace('_', self._escape_table['_']))
                    else:
                        title_str = ''
                    if is_img:
                        result = '<img src="%s" alt="%s"%s%s' \
                            % (url.replace('"', '&quot;'),
                               _xml_escape_attr(link_text),
                               title_str, self.empty_element_suffix)
                        if "smarty-pants" in self.extras:
                            result = result.replace('"', self._escape_table['"'])
                        curr_pos = start_idx + len(result)
                        text = text[:start_idx] + result + text[match.end():]
                    elif start_idx >= anchor_allowed_pos:
                        result_head = '<a href="%s"%s>' % (url, title_str)
                        result = '%s%s</a>' % (result_head, link_text)
                        if "smarty-pants" in self.extras:
                            result = result.replace('"', self._escape_table['"'])
                        # <img> allowed from curr_pos on, <a> from
                        # anchor_allowed_pos on.
                        curr_pos = start_idx + len(result_head)
                        anchor_allowed_pos = start_idx + len(result)
                        text = text[:start_idx] + result + text[match.end():]
                    else:
                        # Anchor not allowed here.
                        curr_pos = start_idx + 1
                    continue

            # Reference anchor or img?
            else:
                match = self._tail_of_reference_link_re.match(text, p)
                if match:
                    # Handle a reference-style anchor or img.
                    is_img = start_idx > 0 and text[start_idx-1] == "!"
                    if is_img:
                        start_idx -= 1
                    link_id = match.group("id").lower()
                    if not link_id:
                        link_id = link_text.lower()  # for links like [this][]
                    if link_id in self.urls:
                        url = self.urls[link_id]
                        # We've got to encode these to avoid conflicting
                        # with italics/bold.
                        url = url.replace('*', self._escape_table['*']) \
                                 .replace('_', self._escape_table['_'])
                        title = self.titles.get(link_id)
                        if title:
                            before = title
                            title = _xml_escape_attr(title) \
                                .replace('*', self._escape_table['*']) \
                                .replace('_', self._escape_table['_'])
                            title_str = ' title="%s"' % title
                        else:
                            title_str = ''
                        if is_img:
                            result = '<img src="%s" alt="%s"%s%s' \
                                % (url.replace('"', '&quot;'),
                                   link_text.replace('"', '&quot;'),
                                   title_str, self.empty_element_suffix)
                            if "smarty-pants" in self.extras:
                                result = result.replace('"', self._escape_table['"'])
                            curr_pos = start_idx + len(result)
                            text = text[:start_idx] + result + text[match.end():]
                        elif start_idx >= anchor_allowed_pos:
                            result = '<a href="%s"%s>%s</a>' \
                                % (url, title_str, link_text)
                            result_head = '<a href="%s"%s>' % (url, title_str)
                            result = '%s%s</a>' % (result_head, link_text)
                            if "smarty-pants" in self.extras:
                                result = result.replace('"', self._escape_table['"'])
                            # <img> allowed from curr_pos on, <a> from
                            # anchor_allowed_pos on.
                            curr_pos = start_idx + len(result_head)
                            anchor_allowed_pos = start_idx + len(result)
                            text = text[:start_idx] + result + text[match.end():]
                        else:
                            # Anchor not allowed here.
                            curr_pos = start_idx + 1
                    else:
                        # This id isn't defined, leave the markup alone.
                        curr_pos = match.end()
                    continue

            # Otherwise, it isn't markup.
            curr_pos = start_idx + 1

        return text

    def header_id_from_text(self, text, prefix, n):
        """Generate a header id attribute value from the given header
        HTML content.

        This is only called if the "header-ids" extra is enabled.
        Subclasses may override this for different header ids.

        @param text {str} The text of the header tag
        @param prefix {str} The requested prefix for header ids. This is the
            value of the "header-ids" extra key, if any. Otherwise, None.
        @param n {int} The <hN> tag number, i.e. `1` for an <h1> tag.
        @returns {str} The value for the header tag's "id" attribute. Return
            None to not have an id attribute and to exclude this header from
            the TOC (if the "toc" extra is specified).
        """
        header_id = _slugify(text)
        if prefix and isinstance(prefix, base_string_type):
            header_id = prefix + '-' + header_id
        if header_id in self._count_from_header_id:
            self._count_from_header_id[header_id] += 1
            header_id += '-%s' % self._count_from_header_id[header_id]
        else:
            self._count_from_header_id[header_id] = 1
        return header_id

    _toc = None
    def _toc_add_entry(self, level, id, name):
        if self._toc is None:
            self._toc = []
        self._toc.append((level, id, self._unescape_special_chars(name)))

    _setext_h_re = re.compile(r'^(.+)[ \t]*\n(=+|-+)[ \t]*\n+', re.M)
    def _setext_h_sub(self, match):
        n = {"=": 1, "-": 2}[match.group(2)[0]]
        demote_headers = self.extras.get("demote-headers")
        if demote_headers:
            n = min(n + demote_headers, 6)
        header_id_attr = ""
        if "header-ids" in self.extras:
            header_id = self.header_id_from_text(match.group(1),
                self.extras["header-ids"], n)
            if header_id:
                header_id_attr = ' id="%s"' % header_id
        html = self._run_span_gamut(match.group(1))
        if "toc" in self.extras and header_id:
            self._toc_add_entry(n, header_id, html)
        return "<h%d%s>%s</h%d>\n\n" % (n, header_id_attr, html, n)

    _atx_h_re = re.compile(r'''
        ^(\#{1,6})  # \1 = string of #'s
        [ \t]+
        (.+?)       # \2 = Header text
        [ \t]*
        (?<!\\)     # ensure not an escaped trailing '#'
        \#*         # optional closing #'s (not counted)
        \n+
        ''', re.X | re.M)
    def _atx_h_sub(self, match):
        n = len(match.group(1))
        demote_headers = self.extras.get("demote-headers")
        if demote_headers:
            n = min(n + demote_headers, 6)
        header_id_attr = ""
        if "header-ids" in self.extras:
            header_id = self.header_id_from_text(match.group(2),
                self.extras["header-ids"], n)
            if header_id:
                header_id_attr = ' id="%s"' % header_id
        html = self._run_span_gamut(match.group(2))
        if "toc" in self.extras and header_id:
            self._toc_add_entry(n, header_id, html)
        return "<h%d%s>%s</h%d>\n\n" % (n, header_id_attr, html, n)

    def _do_headers(self, text):
        # Setext-style headers:
        #     Header 1
        #     ========
        #
        #     Header 2
        #     --------
        text = self._setext_h_re.sub(self._setext_h_sub, text)

        # atx-style headers:
        #   # Header 1
        #   ## Header 2
        #   ## Header 2 with closing hashes ##
        #   ...
        #   ###### Header 6
        text = self._atx_h_re.sub(self._atx_h_sub, text)

        return text


    _marker_ul_chars  = '*+-'
    _marker_any = r'(?:[%s]|\d+\.)' % _marker_ul_chars
    _marker_ul = '(?:[%s])' % _marker_ul_chars
    _marker_ol = r'(?:\d+\.)'

    def _list_sub(self, match):
        lst = match.group(1)
        lst_type = match.group(3) in self._marker_ul_chars and "ul" or "ol"
        result = self._process_list_items(lst)
        if self.list_level:
            return "<%s>\n%s</%s>\n" % (lst_type, result, lst_type)
        else:
            return "<%s>\n%s</%s>\n\n" % (lst_type, result, lst_type)

    def _do_lists(self, text):
        # Form HTML ordered (numbered) and unordered (bulleted) lists.

        # Iterate over each *non-overlapping* list match.
        pos = 0
        while True:
            # Find the *first* hit for either list style (ul or ol). We
            # match ul and ol separately to avoid adjacent lists of different
            # types running into each other (see issue #16).
            hits = []
            for marker_pat in (self._marker_ul, self._marker_ol):
                less_than_tab = self.tab_width - 1
                whole_list = r'''
                    (                   # \1 = whole list
                      (                 # \2
                        [ ]{0,%d}
                        (%s)            # \3 = first list item marker
                        [ \t]+
                        (?!\ *\3\ )     # '- - - ...' isn't a list. See 'not_quite_a_list' test case.
                      )
                      (?:.+?)
                      (                 # \4
                          \Z
                        |
                          \n{2,}
                          (?=\S)
                          (?!           # Negative lookahead for another list item marker
                            [ \t]*
                            %s[ \t]+
                          )
                      )
                    )
                ''' % (less_than_tab, marker_pat, marker_pat)
                if self.list_level:  # sub-list
                    list_re = re.compile("^"+whole_list, re.X | re.M | re.S)
                else:
                    list_re = re.compile(r"(?:(?<=\n\n)|\A\n?)"+whole_list,
                                         re.X | re.M | re.S)
                match = list_re.search(text, pos)
                if match:
                    hits.append((match.start(), match))
            if not hits:
                break
            hits.sort()
            match = hits[0][1]
            start, end = match.span()
            text = text[:start] + self._list_sub(match) + text[end:]
            pos = end

        return text

    _list_item_re = re.compile(r'''
        (\n)?                   # leading line = \1
        (^[ \t]*)               # leading whitespace = \2
        (?P<marker>%s) [ \t]+   # list marker = \3
        ((?:.+?)                # list item text = \4
         (\n{1,2}))             # eols = \5
        (?= \n* (\Z | \2 (?P<next_marker>%s) [ \t]+))
        ''' % (_marker_any, _marker_any),
        re.M | re.X | re.S)

    _last_li_endswith_two_eols = False
    def _list_item_sub(self, match):
        item = match.group(4)
        leading_line = match.group(1)
        leading_space = match.group(2)
        if leading_line or "\n\n" in item or self._last_li_endswith_two_eols:
            item = self._run_block_gamut(self._outdent(item))
        else:
            # Recursion for sub-lists:
            item = self._do_lists(self._outdent(item))
            if item.endswith('\n'):
                item = item[:-1]
            item = self._run_span_gamut(item)
        self._last_li_endswith_two_eols = (len(match.group(5)) == 2)
        return "<li>%s</li>\n" % item

    def _process_list_items(self, list_str):
        # Process the contents of a single ordered or unordered list,
        # splitting it into individual list items.

        # The $g_list_level global keeps track of when we're inside a list.
        # Each time we enter a list, we increment it; when we leave a list,
        # we decrement. If it's zero, we're not in a list anymore.
        #
        # We do this because when we're not inside a list, we want to treat
        # something like this:
        #
        #       I recommend upgrading to version
        #       8. Oops, now this line is treated
        #       as a sub-list.
        #
        # As a single paragraph, despite the fact that the second line starts
        # with a digit-period-space sequence.
        #
        # Whereas when we're inside a list (or sub-list), that line will be
        # treated as the start of a sub-list. What a kludge, huh? This is
        # an aspect of Markdown's syntax that's hard to parse perfectly
        # without resorting to mind-reading. Perhaps the solution is to
        # change the syntax rules such that sub-lists must start with a
        # starting cardinal number; e.g. "1." or "a.".
        self.list_level += 1
        self._last_li_endswith_two_eols = False
        list_str = list_str.rstrip('\n') + '\n'
        list_str = self._list_item_re.sub(self._list_item_sub, list_str)
        self.list_level -= 1
        return list_str

    def _get_pygments_lexer(self, lexer_name):
        try:
            from pygments import lexers, util
        except ImportError:
            return None
        try:
            return lexers.get_lexer_by_name(lexer_name)
        except util.ClassNotFound:
            return None

    def _color_with_pygments(self, codeblock, lexer, **formatter_opts):
        import pygments
        import pygments.formatters

        class HtmlCodeFormatter(pygments.formatters.HtmlFormatter):
            def _wrap_code(self, inner):
                """A function for use in a Pygments Formatter which
                wraps in <code> tags.
                """
                yield 0, "<code>"
                for tup in inner:
                    yield tup
                yield 0, "</code>"

            def wrap(self, source, outfile):
                """Return the source with a code, pre, and div."""
                return self._wrap_div(self._wrap_pre(self._wrap_code(source)))

        formatter_opts.setdefault("cssclass", "codehilite")
        formatter = HtmlCodeFormatter(**formatter_opts)
        return pygments.highlight(codeblock, lexer, formatter)

    def _code_block_sub(self, match, is_fenced_code_block=False):
        lexer_name = None
        if is_fenced_code_block:
            lexer_name = match.group(1)
            if lexer_name:
                formatter_opts = self.extras['fenced-code-blocks'] or {}
            codeblock = match.group(2)
            codeblock = codeblock[:-1]  # drop one trailing newline
        else:
            codeblock = match.group(1)
            codeblock = self._outdent(codeblock)
            codeblock = self._detab(codeblock)
            codeblock = codeblock.lstrip('\n')  # trim leading newlines
            codeblock = codeblock.rstrip()      # trim trailing whitespace

            # Note: "code-color" extra is DEPRECATED.
            if "code-color" in self.extras and codeblock.startswith(":::"):
                lexer_name, rest = codeblock.split('\n', 1)
                lexer_name = lexer_name[3:].strip()
                codeblock = rest.lstrip("\n")   # Remove lexer declaration line.
                formatter_opts = self.extras['code-color'] or {}

        if lexer_name:
            lexer = self._get_pygments_lexer(lexer_name)
            if lexer:
                colored = self._color_with_pygments(codeblock, lexer,
                                                    **formatter_opts)
                return "\n\n%s\n\n" % colored

        codeblock = self._encode_code(codeblock)
        pre_class_str = self._html_class_str_from_tag("pre")
        code_class_str = self._html_class_str_from_tag("code")
        return "\n\n<pre%s><code%s>%s\n</code></pre>\n\n" % (
            pre_class_str, code_class_str, codeblock)

    def _html_class_str_from_tag(self, tag):
        """Get the appropriate ' class="..."' string (note the leading
        space), if any, for the given tag.
        """
        if "html-classes" not in self.extras:
            return ""
        try:
            html_classes_from_tag = self.extras["html-classes"]
        except TypeError:
            return ""
        else:
            if tag in html_classes_from_tag:
                return ' class="%s"' % html_classes_from_tag[tag]
        return ""

    def _do_code_blocks(self, text):
        """Process Markdown `<pre><code>` blocks."""
        code_block_re = re.compile(r'''
            (?:\n\n|\A\n?)
            (               # $1 = the code block -- one or more lines, starting with a space/tab
              (?:
                (?:[ ]{%d} | \t)  # Lines must start with a tab or a tab-width of spaces
                .*\n+
              )+
            )
            ((?=^[ ]{0,%d}\S)|\Z)   # Lookahead for non-space at line-start, or end of doc
            ''' % (self.tab_width, self.tab_width),
            re.M | re.X)
        return code_block_re.sub(self._code_block_sub, text)

    _fenced_code_block_re = re.compile(r'''
        (?:\n\n|\A\n?)
        ^```([\w+-]+)?[ \t]*\n      # opening fence, $1 = optional lang
        (.*?)                       # $2 = code block content
        ^```[ \t]*\n                # closing fence
        ''', re.M | re.X | re.S)

    def _fenced_code_block_sub(self, match):
        return self._code_block_sub(match, is_fenced_code_block=True);

    def _do_fenced_code_blocks(self, text):
        """Process ```-fenced unindented code blocks ('fenced-code-blocks' extra)."""
        return self._fenced_code_block_re.sub(self._fenced_code_block_sub, text)

    # Rules for a code span:
    # - backslash escapes are not interpreted in a code span
    # - to include one or or a run of more backticks the delimiters must
    #   be a longer run of backticks
    # - cannot start or end a code span with a backtick; pad with a
    #   space and that space will be removed in the emitted HTML
    # See `test/tm-cases/escapes.text` for a number of edge-case
    # examples.
    _code_span_re = re.compile(r'''
            (?<!\\)
            (`+)        # \1 = Opening run of `
            (?!`)       # See Note A test/tm-cases/escapes.text
            (.+?)       # \2 = The code block
            (?<!`)
            \1          # Matching closer
            (?!`)
        ''', re.X | re.S)

    def _code_span_sub(self, match):
        c = match.group(2).strip(" \t")
        c = self._encode_code(c)
        return "<code>%s</code>" % c

    def _do_code_spans(self, text):
        #   *   Backtick quotes are used for <code></code> spans.
        #
        #   *   You can use multiple backticks as the delimiters if you want to
        #       include literal backticks in the code span. So, this input:
        #
        #         Just type ``foo `bar` baz`` at the prompt.
        #
        #       Will translate to:
        #
        #         <p>Just type <code>foo `bar` baz</code> at the prompt.</p>
        #
        #       There's no arbitrary limit to the number of backticks you
        #       can use as delimters. If you need three consecutive backticks
        #       in your code, use four for delimiters, etc.
        #
        #   *   You can use spaces to get literal backticks at the edges:
        #
        #         ... type `` `bar` `` ...
        #
        #       Turns to:
        #
        #         ... type <code>`bar`</code> ...
        return self._code_span_re.sub(self._code_span_sub, text)

    def _encode_code(self, text):
        """Encode/escape certain characters inside Markdown code runs.
        The point is that in code, these characters are literals,
        and lose their special Markdown meanings.
        """
        replacements = [
            # Encode all ampersands; HTML entities are not
            # entities within a Markdown code span.
            ('&', '&amp;'),
            # Do the angle bracket song and dance:
            ('<', '&lt;'),
            ('>', '&gt;'),
        ]
        for before, after in replacements:
            text = text.replace(before, after)
        hashed = _hash_text(text)
        self._escape_table[text] = hashed
        return hashed

    _strong_re = re.compile(r"(\*\*|__)(?=\S)(.+?[*_]*)(?<=\S)\1", re.S)
    _em_re = re.compile(r"(\*|_)(?=\S)(.+?)(?<=\S)\1", re.S)
    _code_friendly_strong_re = re.compile(r"\*\*(?=\S)(.+?[*_]*)(?<=\S)\*\*", re.S)
    _code_friendly_em_re = re.compile(r"\*(?=\S)(.+?)(?<=\S)\*", re.S)
    def _do_italics_and_bold(self, text):
        # <strong> must go first:
        if "code-friendly" in self.extras:
            text = self._code_friendly_strong_re.sub(r"<strong>\1</strong>", text)
            text = self._code_friendly_em_re.sub(r"<em>\1</em>", text)
        else:
            text = self._strong_re.sub(r"<strong>\2</strong>", text)
            text = self._em_re.sub(r"<em>\2</em>", text)
        return text

    # "smarty-pants" extra: Very liberal in interpreting a single prime as an
    # apostrophe; e.g. ignores the fact that "round", "bout", "twer", and
    # "twixt" can be written without an initial apostrophe. This is fine because
    # using scare quotes (single quotation marks) is rare.
    _apostrophe_year_re = re.compile(r"'(\d\d)(?=(\s|,|;|\.|\?|!|$))")
    _contractions = ["tis", "twas", "twer", "neath", "o", "n",
        "round", "bout", "twixt", "nuff", "fraid", "sup"]
    def _do_smart_contractions(self, text):
        text = self._apostrophe_year_re.sub(r"&#8217;\1", text)
        for c in self._contractions:
            text = text.replace("'%s" % c, "&#8217;%s" % c)
            text = text.replace("'%s" % c.capitalize(),
                "&#8217;%s" % c.capitalize())
        return text

    # Substitute double-quotes before single-quotes.
    _opening_single_quote_re = re.compile(r"(?<!\S)'(?=\S)")
    _opening_double_quote_re = re.compile(r'(?<!\S)"(?=\S)')
    _closing_single_quote_re = re.compile(r"(?<=\S)'")
    _closing_double_quote_re = re.compile(r'(?<=\S)"(?=(\s|,|;|\.|\?|!|$))')
    def _do_smart_punctuation(self, text):
        """Fancifies 'single quotes', "double quotes", and apostrophes.
        Converts --, ---, and ... into en dashes, em dashes, and ellipses.

        Inspiration is: <http://daringfireball.net/projects/smartypants/>
        See "test/tm-cases/smarty_pants.text" for a full discussion of the
        support here and
        <http://code.google.com/p/python-markdown2/issues/detail?id=42> for a
        discussion of some diversion from the original SmartyPants.
        """
        if "'" in text: # guard for perf
            text = self._do_smart_contractions(text)
            text = self._opening_single_quote_re.sub("&#8216;", text)
            text = self._closing_single_quote_re.sub("&#8217;", text)

        if '"' in text: # guard for perf
            text = self._opening_double_quote_re.sub("&#8220;", text)
            text = self._closing_double_quote_re.sub("&#8221;", text)

        text = text.replace("---", "&#8212;")
        text = text.replace("--", "&#8211;")
        text = text.replace("...", "&#8230;")
        text = text.replace(" . . . ", "&#8230;")
        text = text.replace(". . .", "&#8230;")
        return text

    _block_quote_re = re.compile(r'''
        (                           # Wrap whole match in \1
          (
            ^[ \t]*>[ \t]?          # '>' at the start of a line
              .+\n                  # rest of the first line
            (.+\n)*                 # subsequent consecutive lines
            \n*                     # blanks
          )+
        )
        ''', re.M | re.X)
    _bq_one_level_re = re.compile('^[ \t]*>[ \t]?', re.M);

    _html_pre_block_re = re.compile(r'(\s*<pre>.+?</pre>)', re.S)
    def _dedent_two_spaces_sub(self, match):
        return re.sub(r'(?m)^  ', '', match.group(1))

    def _block_quote_sub(self, match):
        bq = match.group(1)
        bq = self._bq_one_level_re.sub('', bq)  # trim one level of quoting
        bq = self._ws_only_line_re.sub('', bq)  # trim whitespace-only lines
        bq = self._run_block_gamut(bq)          # recurse

        bq = re.sub('(?m)^', '  ', bq)
        # These leading spaces screw with <pre> content, so we need to fix that:
        bq = self._html_pre_block_re.sub(self._dedent_two_spaces_sub, bq)

        return "<blockquote>\n%s\n</blockquote>\n\n" % bq

    def _do_block_quotes(self, text):
        if '>' not in text:
            return text
        return self._block_quote_re.sub(self._block_quote_sub, text)

    def _form_paragraphs(self, text):
        # Strip leading and trailing lines:
        text = text.strip('\n')

        # Wrap <p> tags.
        grafs = []
        for i, graf in enumerate(re.split(r"\n{2,}", text)):
            if graf in self.html_blocks:
                # Unhashify HTML blocks
                grafs.append(self.html_blocks[graf])
            else:
                cuddled_list = None
                if "cuddled-lists" in self.extras:
                    # Need to put back trailing '\n' for `_list_item_re`
                    # match at the end of the paragraph.
                    li = self._list_item_re.search(graf + '\n')
                    # Two of the same list marker in this paragraph: a likely
                    # candidate for a list cuddled to preceding paragraph
                    # text (issue 33). Note the `[-1]` is a quick way to
                    # consider numeric bullets (e.g. "1." and "2.") to be
                    # equal.
                    if (li and len(li.group(2)) <= 3 and li.group("next_marker")
                        and li.group("marker")[-1] == li.group("next_marker")[-1]):
                        start = li.start()
                        cuddled_list = self._do_lists(graf[start:]).rstrip("\n")
                        assert cuddled_list.startswith("<ul>") or cuddled_list.startswith("<ol>")
                        graf = graf[:start]

                # Wrap <p> tags.
                graf = self._run_span_gamut(graf)
                grafs.append("<p>" + graf.lstrip(" \t") + "</p>")

                if cuddled_list:
                    grafs.append(cuddled_list)

        return "\n\n".join(grafs)

    def _add_footnotes(self, text):
        if self.footnotes:
            footer = [
                '<div class="footnotes">',
                '<hr' + self.empty_element_suffix,
                '<ol>',
            ]
            for i, id in enumerate(self.footnote_ids):
                if i != 0:
                    footer.append('')
                footer.append('<li id="fn-%s">' % id)
                footer.append(self._run_block_gamut(self.footnotes[id]))
                backlink = ('<a href="#fnref-%s" '
                    'class="footnoteBackLink" '
                    'title="Jump back to footnote %d in the text.">'
                    '&#8617;</a>' % (id, i+1))
                if footer[-1].endswith("</p>"):
                    footer[-1] = footer[-1][:-len("</p>")] \
                        + '&nbsp;' + backlink + "</p>"
                else:
                    footer.append("\n<p>%s</p>" % backlink)
                footer.append('</li>')
            footer.append('</ol>')
            footer.append('</div>')
            return text + '\n\n' + '\n'.join(footer)
        else:
            return text

    # Ampersand-encoding based entirely on Nat Irons's Amputator MT plugin:
    #   http://bumppo.net/projects/amputator/
    _ampersand_re = re.compile(r'&(?!#?[xX]?(?:[0-9a-fA-F]+|\w+);)')
    _naked_lt_re = re.compile(r'<(?![a-z/?\$!])', re.I)
    _naked_gt_re = re.compile(r'''(?<![a-z0-9?!/'"-])>''', re.I)

    def _encode_amps_and_angles(self, text):
        # Smart processing for ampersands and angle brackets that need
        # to be encoded.
        text = self._ampersand_re.sub('&amp;', text)

        # Encode naked <'s
        text = self._naked_lt_re.sub('&lt;', text)

        # Encode naked >'s
        # Note: Other markdown implementations (e.g. Markdown.pl, PHP
        # Markdown) don't do this.
        text = self._naked_gt_re.sub('&gt;', text)
        return text

    def _encode_backslash_escapes(self, text):
        for ch, escape in list(self._escape_table.items()):
            text = text.replace("\\"+ch, escape)
        return text

    _auto_link_re = re.compile(r'<((https?|ftp):[^\'">\s]+)>', re.I)
    def _auto_link_sub(self, match):
        g1 = match.group(1)
        return '<a href="%s">%s</a>' % (g1, g1)

    _auto_email_link_re = re.compile(r"""
          <
           (?:mailto:)?
          (
              [-.\w]+
              \@
              [-\w]+(\.[-\w]+)*\.[a-z]+
          )
          >
        """, re.I | re.X | re.U)
    def _auto_email_link_sub(self, match):
        return self._encode_email_address(
            self._unescape_special_chars(match.group(1)))

    def _do_auto_links(self, text):
        text = self._auto_link_re.sub(self._auto_link_sub, text)
        text = self._auto_email_link_re.sub(self._auto_email_link_sub, text)
        return text

    def _encode_email_address(self, addr):
        #  Input: an email address, e.g. "foo@example.com"
        #
        #  Output: the email address as a mailto link, with each character
        #      of the address encoded as either a decimal or hex entity, in
        #      the hopes of foiling most address harvesting spam bots. E.g.:
        #
        #    <a href="&#x6D;&#97;&#105;&#108;&#x74;&#111;:&#102;&#111;&#111;&#64;&#101;
        #       x&#x61;&#109;&#x70;&#108;&#x65;&#x2E;&#99;&#111;&#109;">&#102;&#111;&#111;
        #       &#64;&#101;x&#x61;&#109;&#x70;&#108;&#x65;&#x2E;&#99;&#111;&#109;</a>
        #
        #  Based on a filter by Matthew Wickline, posted to the BBEdit-Talk
        #  mailing list: <http://tinyurl.com/yu7ue>
        chars = [_xml_encode_email_char_at_random(ch)
                 for ch in "mailto:" + addr]
        # Strip the mailto: from the visible part.
        addr = '<a href="%s">%s</a>' \
               % (''.join(chars), ''.join(chars[7:]))
        return addr

    def _do_link_patterns(self, text):
        """Caveat emptor: there isn't much guarding against link
        patterns being formed inside other standard Markdown links, e.g.
        inside a [link def][like this].

        Dev Notes: *Could* consider prefixing regexes with a negative
        lookbehind assertion to attempt to guard against this.
        """
        link_from_hash = {}
        for regex, repl in self.link_patterns:
            replacements = []
            for match in regex.finditer(text):
                if hasattr(repl, "__call__"):
                    href = repl(match)
                else:
                    href = match.expand(repl)
                replacements.append((match.span(), href))
            for (start, end), href in reversed(replacements):
                escaped_href = (
                    href.replace('"', '&quot;')  # b/c of attr quote
                        # To avoid markdown <em> and <strong>:
                        .replace('*', self._escape_table['*'])
                        .replace('_', self._escape_table['_']))
                link = '<a href="%s">%s</a>' % (escaped_href, text[start:end])
                hash = _hash_text(link)
                link_from_hash[hash] = link
                text = text[:start] + hash + text[end:]
        for hash, link in list(link_from_hash.items()):
            text = text.replace(hash, link)
        return text

    def _unescape_special_chars(self, text):
        # Swap back in all the special characters we've hidden.
        for ch, hash in list(self._escape_table.items()):
            text = text.replace(hash, ch)
        return text

    def _outdent(self, text):
        # Remove one level of line-leading tabs or spaces
        return self._outdent_re.sub('', text)


class MarkdownWithExtras(Markdown):
    """A markdowner class that enables most extras:

    - footnotes
    - code-color (only has effect if 'pygments' Python module on path)

    These are not included:
    - pyshell (specific to Python-related documenting)
    - code-friendly (because it *disables* part of the syntax)
    - link-patterns (because you need to specify some actual
      link-patterns anyway)
    """
    extras = ["footnotes", "code-color"]


#---- internal support functions

class UnicodeWithAttrs(unicode):
    """A subclass of unicode used for the return value of conversion to
    possibly attach some attributes. E.g. the "toc_html" attribute when
    the "toc" extra is used.
    """
    metadata = None
    _toc = None
    def toc_html(self):
        """Return the HTML for the current TOC.

        This expects the `_toc` attribute to have been set on this instance.
        """
        if self._toc is None:
            return None

        def indent():
            return '  ' * (len(h_stack) - 1)
        lines = []
        h_stack = [0]   # stack of header-level numbers
        for level, id, name in self._toc:
            if level > h_stack[-1]:
                lines.append("%s<ul>" % indent())
                h_stack.append(level)
            elif level == h_stack[-1]:
                lines[-1] += "</li>"
            else:
                while level < h_stack[-1]:
                    h_stack.pop()
                    if not lines[-1].endswith("</li>"):
                        lines[-1] += "</li>"
                    lines.append("%s</ul></li>" % indent())
            lines.append('%s<li><a href="#%s">%s</a>' % (
                indent(), id, name))
        while len(h_stack) > 1:
            h_stack.pop()
            if not lines[-1].endswith("</li>"):
                lines[-1] += "</li>"
            lines.append("%s</ul>" % indent())
        return '\n'.join(lines) + '\n'
    toc_html = property(toc_html)

## {{{ http://code.activestate.com/recipes/577257/ (r1)
_slugify_strip_re = re.compile(r'[^\w\s-]')
_slugify_hyphenate_re = re.compile(r'[-\s]+')
def _slugify(value):
    """
    Normalizes string, converts to lowercase, removes non-alpha characters,
    and converts spaces to hyphens.

    From Django's "django/template/defaultfilters.py".
    """

    try:
        import unicodedata
        value = unicodedata.normalize('NFKD', value)
    except ImportError:
        pass
    value = value.encode('ascii', 'ignore').decode()
    value = _slugify_strip_re.sub('', value).strip().lower()
    return _slugify_hyphenate_re.sub('-', value)
## end of http://code.activestate.com/recipes/577257/ }}}


# From http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/52549
def _curry(*args, **kwargs):
    function, args = args[0], args[1:]
    def result(*rest, **kwrest):
        combined = kwargs.copy()
        combined.update(kwrest)
        return function(*args + rest, **combined)
    return result

# Recipe: regex_from_encoded_pattern (1.0)
def _regex_from_encoded_pattern(s):
    """'foo'    -> re.compile(re.escape('foo'))
       '/foo/'  -> re.compile('foo')
       '/foo/i' -> re.compile('foo', re.I)
    """
    if s.startswith('/') and s.rfind('/') != 0:
        # Parse it: /PATTERN/FLAGS
        idx = s.rfind('/')
        pattern, flags_str = s[1:idx], s[idx+1:]
        flag_from_char = {
            "i": re.IGNORECASE,
            "l": re.LOCALE,
            "s": re.DOTALL,
            "m": re.MULTILINE,
            "u": re.UNICODE,
        }
        flags = 0
        for char in flags_str:
            try:
                flags |= flag_from_char[char]
            except KeyError:
                raise ValueError("unsupported regex flag: '%s' in '%s' "
                                 "(must be one of '%s')"
                                 % (char, s, ''.join(list(flag_from_char.keys()))))
        return re.compile(s[1:idx], flags)
    else: # not an encoded regex
        return re.compile(re.escape(s))

# Recipe: dedent (0.1.2)
def _dedentlines(lines, tabsize=8, skip_first_line=False):
    """_dedentlines(lines, tabsize=8, skip_first_line=False) -> dedented lines

        "lines" is a list of lines to dedent.
        "tabsize" is the tab width to use for indent width calculations.
        "skip_first_line" is a boolean indicating if the first line should
            be skipped for calculating the indent width and for dedenting.
            This is sometimes useful for docstrings and similar.

    Same as dedent() except operates on a sequence of lines. Note: the
    lines list is modified **in-place**.
    """
    DEBUG = False
    if DEBUG:
        print("dedent: dedent(..., tabsize=%d, skip_first_line=%r)"\
              % (tabsize, skip_first_line))
    indents = []
    margin = None
    for i, line in enumerate(lines):
        if i == 0 and skip_first_line: continue
        indent = 0
        for ch in line:
            if ch == ' ':
                indent += 1
            elif ch == '\t':
                indent += tabsize - (indent % tabsize)
            elif ch in '\r\n':
                continue # skip all-whitespace lines
            else:
                break
        else:
            continue # skip all-whitespace lines
        if DEBUG: print("dedent: indent=%d: %r" % (indent, line))
        if margin is None:
            margin = indent
        else:
            margin = min(margin, indent)
    if DEBUG: print("dedent: margin=%r" % margin)

    if margin is not None and margin > 0:
        for i, line in enumerate(lines):
            if i == 0 and skip_first_line: continue
            removed = 0
            for j, ch in enumerate(line):
                if ch == ' ':
                    removed += 1
                elif ch == '\t':
                    removed += tabsize - (removed % tabsize)
                elif ch in '\r\n':
                    if DEBUG: print("dedent: %r: EOL -> strip up to EOL" % line)
                    lines[i] = lines[i][j:]
                    break
                else:
                    raise ValueError("unexpected non-whitespace char %r in "
                                     "line %r while removing %d-space margin"
                                     % (ch, line, margin))
                if DEBUG:
                    print("dedent: %r: %r -> removed %d/%d"\
                          % (line, ch, removed, margin))
                if removed == margin:
                    lines[i] = lines[i][j+1:]
                    break
                elif removed > margin:
                    lines[i] = ' '*(removed-margin) + lines[i][j+1:]
                    break
            else:
                if removed:
                    lines[i] = lines[i][removed:]
    return lines

def _dedent(text, tabsize=8, skip_first_line=False):
    """_dedent(text, tabsize=8, skip_first_line=False) -> dedented text

        "text" is the text to dedent.
        "tabsize" is the tab width to use for indent width calculations.
        "skip_first_line" is a boolean indicating if the first line should
            be skipped for calculating the indent width and for dedenting.
            This is sometimes useful for docstrings and similar.

    textwrap.dedent(s), but don't expand tabs to spaces
    """
    lines = text.splitlines(1)
    _dedentlines(lines, tabsize=tabsize, skip_first_line=skip_first_line)
    return ''.join(lines)


class _memoized(object):
   """Decorator that caches a function's return value each time it is called.
   If called later with the same arguments, the cached value is returned, and
   not re-evaluated.

   http://wiki.python.org/moin/PythonDecoratorLibrary
   """
   def __init__(self, func):
      self.func = func
      self.cache = {}
   def __call__(self, *args):
      try:
         return self.cache[args]
      except KeyError:
         self.cache[args] = value = self.func(*args)
         return value
      except TypeError:
         # uncachable -- for instance, passing a list as an argument.
         # Better to not cache than to blow up entirely.
         return self.func(*args)
   def __repr__(self):
      """Return the function's docstring."""
      return self.func.__doc__


def _xml_oneliner_re_from_tab_width(tab_width):
    """Standalone XML processing instruction regex."""
    return re.compile(r"""
        (?:
            (?<=\n\n)       # Starting after a blank line
            |               # or
            \A\n?           # the beginning of the doc
        )
        (                           # save in $1
            [ ]{0,%d}
            (?:
                <\?\w+\b\s+.*?\?>   # XML processing instruction
                |
                <\w+:\w+\b\s+.*?/>  # namespaced single tag
            )
            [ \t]*
            (?=\n{2,}|\Z)       # followed by a blank line or end of document
        )
        """ % (tab_width - 1), re.X)
_xml_oneliner_re_from_tab_width = _memoized(_xml_oneliner_re_from_tab_width)

def _hr_tag_re_from_tab_width(tab_width):
     return re.compile(r"""
        (?:
            (?<=\n\n)       # Starting after a blank line
            |               # or
            \A\n?           # the beginning of the doc
        )
        (                       # save in \1
            [ ]{0,%d}
            <(hr)               # start tag = \2
            \b                  # word break
            ([^<>])*?           #
            /?>                 # the matching end tag
            [ \t]*
            (?=\n{2,}|\Z)       # followed by a blank line or end of document
        )
        """ % (tab_width - 1), re.X)
_hr_tag_re_from_tab_width = _memoized(_hr_tag_re_from_tab_width)


def _xml_escape_attr(attr, skip_single_quote=True):
    """Escape the given string for use in an HTML/XML tag attribute.

    By default this doesn't bother with escaping `'` to `&#39;`, presuming that
    the tag attribute is surrounded by double quotes.
    """
    escaped = (attr
        .replace('&', '&amp;')
        .replace('"', '&quot;')
        .replace('<', '&lt;')
        .replace('>', '&gt;'))
    if not skip_single_quote:
        escaped = escaped.replace("'", "&#39;")
    return escaped


def _xml_encode_email_char_at_random(ch):
    r = random()
    # Roughly 10% raw, 45% hex, 45% dec.
    # '@' *must* be encoded. I [John Gruber] insist.
    # Issue 26: '_' must be encoded.
    if r > 0.9 and ch not in "@_":
        return ch
    elif r < 0.45:
        # The [1:] is to drop leading '0': 0x63 -> x63
        return '&#%s;' % hex(ord(ch))[1:]
    else:
        return '&#%s;' % ord(ch)



#---- mainline

class _NoReflowFormatter(optparse.IndentedHelpFormatter):
    """An optparse formatter that does NOT reflow the description."""
    def format_description(self, description):
        return description or ""

def _test():
    import doctest
    doctest.testmod()

def main(argv=None):
    if argv is None:
        argv = sys.argv
    if not logging.root.handlers:
        logging.basicConfig()

    usage = "usage: %prog [PATHS...]"
    version = "%prog "+__version__
    parser = optparse.OptionParser(prog="markdown2", usage=usage,
        version=version, description=cmdln_desc,
        formatter=_NoReflowFormatter())
    parser.add_option("-v", "--verbose", dest="log_level",
                      action="store_const", const=logging.DEBUG,
                      help="more verbose output")
    parser.add_option("--encoding",
                      help="specify encoding of text content")
    parser.add_option("--html4tags", action="store_true", default=False,
                      help="use HTML 4 style for empty element tags")
    parser.add_option("-s", "--safe", metavar="MODE", dest="safe_mode",
                      help="sanitize literal HTML: 'escape' escapes "
                           "HTML meta chars, 'replace' replaces with an "
                           "[HTML_REMOVED] note")
    parser.add_option("-x", "--extras", action="append",
                      help="Turn on specific extra features (not part of "
                           "the core Markdown spec). See above.")
    parser.add_option("--use-file-vars",
                      help="Look for and use Emacs-style 'markdown-extras' "
                           "file var to turn on extras. See "
                           "<https://github.com/trentm/python-markdown2/wiki/Extras>")
    parser.add_option("--link-patterns-file",
                      help="path to a link pattern file")
    parser.add_option("--self-test", action="store_true",
                      help="run internal self-tests (some doctests)")
    parser.add_option("--compare", action="store_true",
                      help="run against Markdown.pl as well (for testing)")
    parser.set_defaults(log_level=logging.INFO, compare=False,
                        encoding="utf-8", safe_mode=None, use_file_vars=False)
    opts, paths = parser.parse_args()
    log.setLevel(opts.log_level)

    if opts.self_test:
        return _test()

    if opts.extras:
        extras = {}
        for s in opts.extras:
            splitter = re.compile("[,;: ]+")
            for e in splitter.split(s):
                if '=' in e:
                    ename, earg = e.split('=', 1)
                    try:
                        earg = int(earg)
                    except ValueError:
                        pass
                else:
                    ename, earg = e, None
                extras[ename] = earg
    else:
        extras = None

    if opts.link_patterns_file:
        link_patterns = []
        f = open(opts.link_patterns_file)
        try:
            for i, line in enumerate(f.readlines()):
                if not line.strip(): continue
                if line.lstrip().startswith("#"): continue
                try:
                    pat, href = line.rstrip().rsplit(None, 1)
                except ValueError:
                    raise MarkdownError("%s:%d: invalid link pattern line: %r"
                                        % (opts.link_patterns_file, i+1, line))
                link_patterns.append(
                    (_regex_from_encoded_pattern(pat), href))
        finally:
            f.close()
    else:
        link_patterns = None

    from os.path import join, dirname, abspath, exists
    markdown_pl = join(dirname(dirname(abspath(__file__))), "test",
                       "Markdown.pl")
    if not paths:
        paths = ['-']
    for path in paths:
        if path == '-':
            text = sys.stdin.read()
        else:
            fp = codecs.open(path, 'r', opts.encoding)
            text = fp.read()
            fp.close()
        if opts.compare:
            from subprocess import Popen, PIPE
            print("==== Markdown.pl ====")
            p = Popen('perl %s' % markdown_pl, shell=True, stdin=PIPE, stdout=PIPE, close_fds=True)
            p.stdin.write(text.encode('utf-8'))
            p.stdin.close()
            perl_html = p.stdout.read().decode('utf-8')
            if py3:
                sys.stdout.write(perl_html)
            else:
                sys.stdout.write(perl_html.encode(
                    sys.stdout.encoding or "utf-8", 'xmlcharrefreplace'))
            print("==== markdown2.py ====")
        html = markdown(text,
            html4tags=opts.html4tags,
            safe_mode=opts.safe_mode,
            extras=extras, link_patterns=link_patterns,
            use_file_vars=opts.use_file_vars)
        if py3:
            sys.stdout.write(html)
        else:
            sys.stdout.write(html.encode(
                sys.stdout.encoding or "utf-8", 'xmlcharrefreplace'))
        if extras and "toc" in extras:
            log.debug("toc_html: " +
                html.toc_html.encode(sys.stdout.encoding or "utf-8", 'xmlcharrefreplace'))
        if opts.compare:
            test_dir = join(dirname(dirname(abspath(__file__))), "test")
            if exists(join(test_dir, "test_markdown2.py")):
                sys.path.insert(0, test_dir)
                from test_markdown2 import norm_html_from_html
                norm_html = norm_html_from_html(html)
                norm_perl_html = norm_html_from_html(perl_html)
            else:
                norm_html = html
                norm_perl_html = perl_html
            print("==== match? %r ====" % (norm_perl_html == norm_html))


if __name__ == "__main__":
    sys.exit( main(sys.argv) )

########NEW FILE########
__FILENAME__ = MarkdownPreview
# -*- encoding: UTF-8 -*-
import sublime
import sublime_plugin

import os
import sys
import traceback
import tempfile
import re
import json
import time


def is_ST3():
    ''' check if ST3 based on python version '''
    version = sys.version_info
    if isinstance(version, tuple):
        version = version[0]
    elif getattr(version, 'major', None):
        version = version.major
    return (version >= 3)

if is_ST3():
    from . import desktop
    from . import markdown2
    from . import markdown
    from .helper import INSTALLED_DIRECTORY
    from urllib.request import urlopen
    from urllib.error import HTTPError, URLError
    
    def Request(url, data, headers):
        ''' Adapter for urllib2 used in ST2 '''
        import urllib.request
        return urllib.request.Request(url, data=data, headers=headers, method='POST')

else:
    import desktop
    import markdown2
    import markdown
    from helper import INSTALLED_DIRECTORY
    from urllib2 import Request, urlopen, HTTPError, URLError

_CANNOT_CONVERT = u'cannot convert markdown'


def getTempMarkdownPreviewPath(view):
    ''' return a permanent full path of the temp markdown preview file '''

    settings = sublime.load_settings('MarkdownPreview.sublime-settings')

    tmp_filename = '%s.html' % view.id()
    tmp_dir = tempfile.gettempdir();
    if settings.get('path_tempfile'):
        if os.path.isabs(settings.get('path_tempfile')): #absolute path or not
            tmp_dir = settings.get('path_tempfile')
        else:
            tmp_dir = os.path.join(os.path.dirname(view.file_name()), settings.get('path_tempfile'))

    if not os.path.isdir(tmp_dir): #create dir if not exsits
        os.makedirs(tmp_dir)

    tmp_fullpath = os.path.join(tmp_dir, tmp_filename)
    return tmp_fullpath

def save_utf8(filename, text):
    if is_ST3():
        f = open(filename, 'w', encoding='utf-8')
        f.write(text)
        f.close()
    else: # 2.x
        f = open(filename, 'w')
        f.write(text.encode('utf-8'))
        f.close()

def load_utf8(filename):
    if is_ST3():
        return open(filename, 'r', encoding='utf-8').read()
    else: # 2.x
        return open(filename, 'r').read().decode('utf-8')

def load_resource(name):
    ''' return file contents for files within the package root folder '''

    try:
        if is_ST3():
            return sublime.load_resource('Packages/Markdown Preview/{0}'.format(name))
        else:
            filename = os.path.join(sublime.packages_path(), INSTALLED_DIRECTORY, name)
            return load_utf8(filename)
    except:
        print("Error while load_resource('%s')" % filename)
        traceback.print_exc()
        return ''

def exists_resource(resource_file_path):
    filename = os.path.join(os.path.dirname(sublime.packages_path()), resource_file_path)
    return os.path.isfile(filename)

def new_scratch_view(window, text):
    ''' create a new scratch view and paste text content
        return the new view
    '''

    new_view = window.new_file()
    new_view.set_scratch(True)
    if is_ST3():
        new_view.run_command('append', {
            'characters': text,
        })
    else: # 2.x
        new_edit = new_view.begin_edit()
        new_view.insert(new_edit, 0, text)
        new_view.end_edit(new_edit)
    return new_view

class MarkdownPreviewListener(sublime_plugin.EventListener):
    ''' auto update the output html if markdown file has already been converted once '''

    def on_post_save(self, view):
        settings = sublime.load_settings('MarkdownPreview.sublime-settings')
        filetypes = settings.get('markdown_filetypes')
        if filetypes and view.file_name().endswith(tuple(filetypes)):
            temp_file = getTempMarkdownPreviewPath(view)
            if os.path.isfile(temp_file):
                # reexec markdown conversion
                # todo : check if browser still opened and reopen it if needed
                view.run_command('markdown_preview', {
                    'target': 'disk',
                    'parser': view.settings().get('parser')
                })
                sublime.status_message('Markdown preview file updated')



class MarkdownCheatsheetCommand(sublime_plugin.TextCommand):
    ''' open our markdown cheat sheet in ST2 '''
    def run(self, edit):
        lines = '\n'.join(load_resource('sample.md').splitlines())
        view = new_scratch_view(self.view.window(), lines)
        view.set_name("Markdown Cheatsheet")

        # Set syntax file
        syntax_files = ["Packages/Markdown Extended/Syntaxes/Markdown Extended.tmLanguage", "Packages/Markdown/Markdown.tmLanguage"]
        for file in syntax_files:
            if exists_resource(file):
                view.set_syntax_file(file)
                break # Done if any syntax is set.

        sublime.status_message('Markdown cheat sheet opened')



class MarkdownCompiler():
    ''' Do the markdown converting '''

    def isurl(self, css_name):
        match = re.match(r'https?://', css_name)
        if match:
            return True
        return False

    def get_default_css(self, parser):
        ''' locate the correct CSS with the 'css' setting '''
        css_name = self.settings.get('css', 'default')

        if self.isurl(css_name):
            # link to remote URL
            return u"<link href='%s' rel='stylesheet' type='text/css'>" % css_name
        elif os.path.isfile(os.path.expanduser(css_name)):
            # use custom CSS file
            return u"<style>%s</style>" % load_utf8(os.path.expanduser(css_name))
        elif css_name == 'default':
            # use parser CSS file
            return u"<style>%s</style>" % load_resource('github.css' if parser == 'github' else 'markdown.css')


        return ''

    def get_override_css(self):
        ''' handls allow_css_overrides setting. '''

        if self.settings.get('allow_css_overrides'):
            filename = self.view.file_name()
            filetypes = self.settings.get('markdown_filetypes')

            if filename and filetypes:
                for filetype in filetypes:
                    if filename.endswith(filetype):
                        css_filename = filename.rpartition(filetype)[0] + '.css'
                        if (os.path.isfile(css_filename)):
                            return u"<style>%s</style>" % load_utf8(css_filename)
        return ''

    def get_stylesheet(self, parser):
        ''' return the correct CSS file based on parser and settings '''
        return self.get_default_css(parser) + self.get_override_css()

    def get_javascript(self):
        js_files = self.settings.get('js')
        scripts = ''

        if js_files is not None:
            # Ensure string values become a list.
            if isinstance(js_files, str) or isinstance(js_files, unicode):
                js_files = [js_files]
            # Only load scripts if we have a list.
            if isinstance(js_files, list):
                for js_file in js_files:
                    if os.path.isabs(js_file):
                        # Load the script inline to avoid cross-origin.
                        scripts += u"<script>%s</script>" % load_utf8(js_file)
                    else:
                        scripts += u"<script type='text/javascript' src='%s'></script>" % js_file
        return scripts

    def get_mathjax(self):
        ''' return the MathJax script if enabled '''

        if self.settings.get('enable_mathjax') is True:
            return load_resource('mathjax.html')
        return ''

    def get_highlight(self):
        ''' return the Highlight.js and css if enabled '''

        highlight = ''
        if self.settings.get('enable_highlight') is True and self.settings.get('parser') == 'default':
            highlight += "<style>%s</style>" % load_resource('highlight.css')
            highlight += "<script>%s</script>" % load_resource('highlight.js')
            highlight += "<script>hljs.initHighlightingOnLoad();</script>"
        return highlight


    def get_contents(self, wholefile=False):
        ''' Get contents or selection from view and optionally strip the YAML front matter '''
        region = sublime.Region(0, self.view.size())
        contents = self.view.substr(region)
        if not wholefile:
            # use selection if any
            selection = self.view.substr(self.view.sel()[0])
            if selection.strip() != '':
                contents = selection
        if self.settings.get('strip_yaml_front_matter') and contents.startswith('---'):
            title = ''
            title_match = re.search('(?:title:)(.+)', contents, flags=re.IGNORECASE)
            if title_match:
                stripped_title = title_match.group(1).strip()
                title = '%s\n%s\n\n' % (stripped_title, '=' * len(stripped_title))
            contents_without_front_matter = re.sub(r'(?s)^---.*---\n', '', contents)
            contents = '%s%s' % (title, contents_without_front_matter)
        return contents

    def postprocessor(self, html):
        ''' fix relative paths in images, scripts, and links for the internal parser '''
        def tag_fix(match):
            tag, src = match.groups()
            filename = self.view.file_name()
            if filename:
                if not src.startswith(('file://', 'https://', 'http://', '/', '#')):
                    abs_path = u'file://%s/%s' % (os.path.dirname(filename), src)
                    tag = tag.replace(src, abs_path)
            return tag
        RE_SOURCES = re.compile("""(?P<tag><(?:img|script|a)[^>]+(?:src|href)=["'](?P<src>[^"']+)[^>]*>)""")
        html = RE_SOURCES.sub(tag_fix, html)
        return html

    def get_config_extensions(self, default_extensions):
        config_extensions = self.settings.get('enabled_extensions')
        if not config_extensions or config_extensions == 'default':
            return default_extensions
        if 'default' in config_extensions:
            config_extensions.remove( 'default' )
            config_extensions.extend( default_extensions )
        return config_extensions

    def curl_convert(self, data):
        try:
            import subprocess

            # It looks like the text does NOT need to be escaped and
            # surrounded with double quotes.
            # Tested in ubuntu 13.10, python 2.7.5+
            shell_safe_json = data.decode('utf-8')
            curl_args = [
                'curl',
                '-H',
                'Content-Type: application/json',
                '-d',
                shell_safe_json,
                'https://api.github.com/markdown'
            ]

            github_oauth_token = self.settings.get('github_oauth_token')
            if github_oauth_token:
                curl_args[1:1] = [
                    '-u',
                    github_oauth_token
                ]

            markdown_html = subprocess.Popen(curl_args, stdout=subprocess.PIPE).communicate()[0].decode('utf-8')
            return markdown_html
        except subprocess.CalledProcessError as e:
            sublime.error_message('cannot use github API to convert markdown. SSL is not included in your Python installation. And using curl didn\'t work either')
        return None

    def convert_markdown(self, markdown_text, parser):
        ''' convert input markdown to HTML, with github or builtin parser '''

        markdown_html = _CANNOT_CONVERT
        if parser == 'github':
            github_oauth_token = self.settings.get('github_oauth_token')

            # use the github API
            sublime.status_message('converting markdown with github API...')
            github_mode = self.settings.get('github_mode', 'gfm')
            data = {
                "text": markdown_text,
                "mode": github_mode
            }
            data = json.dumps(data).encode('utf-8')

            try:
                headers = {
                    'Content-Type': 'application/json'
                }
                if github_oauth_token:
                    headers['Authorization'] = "token %s" % github_oauth_token
                url = "https://api.github.com/markdown"
                sublime.status_message(url)
                request = Request(url, data, headers)
                markdown_html = urlopen(request).read().decode('utf-8')
            except HTTPError:
                e = sys.exc_info()[1]
                if e.code == 401:
                    sublime.error_message('github API auth failed. Please check your OAuth token.')
                else:
                    sublime.error_message('github API responded in an unfashion way :/')
            except URLError:
                # Maybe this is a Linux-install of ST which doesn't bundle with SSL support
                # So let's try wrapping curl instead
                markdown_html = self.curl_convert(data)
            except:
                e = sys.exc_info()[1]
                print(e)
                traceback.print_exc()
                sublime.error_message('cannot use github API to convert markdown. Please check your settings.')
            else:
                sublime.status_message('converted markdown with github API successfully')

        elif parser == 'markdown2':
            # convert the markdown
            enabled_extras = set(self.get_config_extensions(['footnotes', 'toc', 'fenced-code-blocks', 'cuddled-lists']))
            if self.settings.get("enable_mathjax") is True or self.settings.get("enable_highlight") is True:
                enabled_extras.add('code-friendly')
            markdown_html = markdown2.markdown(markdown_text, extras=list(enabled_extras))
            toc_html = markdown_html.toc_html
            if toc_html:
                toc_markers = ['[toc]', '[TOC]', '<!--TOC-->']
                for marker in toc_markers:
                    markdown_html = markdown_html.replace(marker, toc_html)

        else:
            sublime.status_message('converting markdown with Python markdown...')
            config_extensions = self.get_config_extensions(['extra', 'toc'])
            markdown_html = markdown.markdown(markdown_text, extensions=config_extensions)

        markdown_html = self.postprocessor(markdown_html)
        return markdown_html

    def get_title(self):
        title = self.view.name()
        if not title:
            fn = self.view.file_name()
            title = 'untitled' if not fn else os.path.splitext(os.path.basename(fn))[0]
        return '<title>%s</title>' % title

    def run(self, view, parser, wholefile=False):
        ''' return full html and body html for view. '''
        self.settings = sublime.load_settings('MarkdownPreview.sublime-settings')
        self.view = view
        
        contents = self.get_contents(wholefile)
        
        body = self.convert_markdown(contents, parser)

        html_template = self.settings.get('html_template')

        # use customized html template if given
        if html_template and os.path.exists(html_template):
            head = u''
            if not self.settings.get('skip_default_stylesheet'):
                head += self.get_stylesheet(parser)
            head += self.get_javascript()
            head += self.get_highlight()
            head += self.get_mathjax()
            head += self.get_title()

            html = load_utf8(html_template)
            html = html.replace('{{ HEAD }}', head, 1)
            html = html.replace('{{ BODY }}', body, 1)
        else:
            html = u'<!DOCTYPE html>'
            html += '<html><head><meta charset="utf-8">'
            html += self.get_stylesheet(parser)
            html += self.get_javascript()
            html += self.get_highlight()
            html += self.get_mathjax()
            html += self.get_title()
            html += '</head><body>'
            html += body
            html += '</body>'
            html += '</html>'

        return html, body


compiler = MarkdownCompiler()



class MarkdownPreviewCommand(sublime_plugin.TextCommand):
    def run(self, edit, parser='markdown', target='browser'):
        settings = sublime.load_settings('MarkdownPreview.sublime-settings')

        # backup parser+target for later saves
        self.view.settings().set('parser', parser)
        self.view.settings().set('target', target)

        html, body = compiler.run(self.view, parser)

        if target in ['disk', 'browser']:
            # check if LiveReload ST2 extension installed and add its script to the resulting HTML
            livereload_installed = ('LiveReload' in os.listdir(sublime.packages_path()))
            # build the html
            if livereload_installed:
                port = sublime.load_settings('LiveReload.sublime-settings').get('port', 35729)
                html += '<script>document.write(\'<script src="http://\' + (location.host || \'localhost\').split(\':\')[0] + \':%d/livereload.js?snipver=1"></\' + \'script>\')</script>' % port
            # update output html file
            tmp_fullpath = getTempMarkdownPreviewPath(self.view)
            save_utf8(tmp_fullpath, html)
            # now opens in browser if needed
            if target == 'browser':
                self.__class__.open_in_browser(tmp_fullpath, settings.get('browser', 'default'))
        elif target == 'sublime':
            # create a new buffer and paste the output HTML
            embed_css = settings.get('embed_css_for_sublime_output', True)
            if embed_css:
                new_scratch_view(self.view.window(), html)
            else:
                new_scratch_view(self.view.window(), body)
            sublime.status_message('Markdown preview launched in sublime')
        elif target == 'clipboard':
            # clipboard copy the full HTML
            sublime.set_clipboard(html)
            sublime.status_message('Markdown export copied to clipboard')

    @classmethod
    def open_in_browser(cls, path, browser='default'):
        if browser == 'default':
            if sys.platform == 'darwin':
                # To open HTML files, Mac OS the open command uses the file
                # associated with .html. For many developers this is Sublime,
                # not the default browser. Getting the right value is
                # embarrassingly difficult.
                import shlex, subprocess
                env = {'VERSIONER_PERL_PREFER_32_BIT': 'true'}
                raw = """perl -MMac::InternetConfig -le 'print +(GetICHelper "http")[1]'"""
                process = subprocess.Popen(shlex.split(raw), env=env, stdout=subprocess.PIPE)
                out, err = process.communicate()
                default_browser = out.strip().decode('utf-8')
                cmd = "open -a '%s' %s" % (default_browser, path)
                os.system(cmd)
            else:
                desktop.open(tmp_fullpath)
            sublime.status_message('Markdown preview launched in default browser')
        else:
            cmd = '"%s" %s' % (browser, path)
            if sys.platform == 'darwin':
                cmd = "open -a %s" % cmd
            elif sys.platform == 'linux2':
                cmd += ' &'
            elif sys.platform == 'win32':
                cmd = 'start "" %s' % cmd
            result = os.system(cmd)
            if result != 0:
                sublime.error_message('cannot execute "%s" Please check your Markdown Preview settings' % config_browser)
            else:
                sublime.status_message('Markdown preview launched in %s' % config_browser)

class MarkdownBuildCommand(sublime_plugin.WindowCommand):
    def init_panel(self):
        if not hasattr(self, 'output_view'):
            if is_ST3():
                self.output_view = self.window.create_output_panel("markdown")
            else:
                self.output_view = self.window.get_output_panel("markdown")

    def puts(self, message):
        message = message + '\n'
        if is_ST3():
            self.output_view.run_command('append', {'characters': message, 'force': True, 'scroll_to_end': True})
        else:
            selection_was_at_end = (len(self.output_view.sel()) == 1
            and self.output_view.sel()[0]
                == sublime.Region(self.output_view.size()))
            self.output_view.set_read_only(False)
            edit = self.output_view.begin_edit()
            self.output_view.insert(edit, self.output_view.size(), message)
            if selection_was_at_end:
                self.output_view.show(self.output_view.size())
            self.output_view.end_edit(edit)
            self.output_view.set_read_only(True)

    def run(self):
        view = self.window.active_view()
        if not view:
            return
        start_time = time.time()

        self.init_panel()
        
        settings = sublime.load_settings('MarkdownPreview.sublime-settings')
        parser = settings.get('parser', 'markdown')

        show_panel_on_build = settings.get("show_panel_on_build", True)
        if show_panel_on_build:
            self.window.run_command("show_panel", {"panel": "output.markdown"})
        
        mdfile = view.file_name()
        if mdfile is None:
            self.puts("Can't build a unsaved markdown file.")
            return

        self.puts("Compiling %s..." % mdfile)

        html, body = compiler.run(view, parser, True)

        htmlfile = os.path.splitext(mdfile)[0]+'.html'
        self.puts("        ->"+htmlfile)
        save_utf8(htmlfile, html)

        elapsed = time.time() - start_time
        if body == _CANNOT_CONVERT:
            self.puts(_CANNOT_CONVERT)
        self.puts("[Finished in %.1fs]" % (elapsed))
        sublime.status_message("Build finished")

########NEW FILE########
