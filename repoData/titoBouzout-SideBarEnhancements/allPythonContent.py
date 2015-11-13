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
__FILENAME__ = filesize

traditional = [
    (1024 ** 5, 'P'),
    (1024 ** 4, 'T'), 
    (1024 ** 3, 'G'), 
    (1024 ** 2, 'M'), 
    (1024 ** 1, 'K'),
    (1024 ** 0, 'B'),
    ]

alternative = [
    (1024 ** 5, ' PB'),
    (1024 ** 4, ' TB'), 
    (1024 ** 3, ' GB'), 
    (1024 ** 2, ' MB'), 
    (1024 ** 1, ' KB'),
    (1024 ** 0, (' byte', ' bytes')),
    ]

verbose = [
    (1024 ** 5, (' petabyte', ' petabytes')),
    (1024 ** 4, (' terabyte', ' terabytes')), 
    (1024 ** 3, (' gigabyte', ' gigabytes')), 
    (1024 ** 2, (' megabyte', ' megabytes')), 
    (1024 ** 1, (' kilobyte', ' kilobytes')),
    (1024 ** 0, (' byte', ' bytes')),
    ]

iec = [
    (1024 ** 5, 'Pi'),
    (1024 ** 4, 'Ti'),
    (1024 ** 3, 'Gi'), 
    (1024 ** 2, 'Mi'), 
    (1024 ** 1, 'Ki'),
    (1024 ** 0, ''),
    ]

si = [
    (1000 ** 5, 'P'),
    (1000 ** 4, 'T'), 
    (1000 ** 3, 'G'), 
    (1000 ** 2, 'M'), 
    (1000 ** 1, 'K'),
    (1000 ** 0, 'B'),
    ]



def size(bytes, system=traditional):
    """Human-readable file size.

    Using the traditional system, where a factor of 1024 is used::
    
    >>> size(10)
    '10B'
    >>> size(100)
    '100B'
    >>> size(1000)
    '1000B'
    >>> size(2000)
    '1K'
    >>> size(10000)
    '9K'
    >>> size(20000)
    '19K'
    >>> size(100000)
    '97K'
    >>> size(200000)
    '195K'
    >>> size(1000000)
    '976K'
    >>> size(2000000)
    '1M'
    
    Using the SI system, with a factor 1000::

    >>> size(10, system=si)
    '10B'
    >>> size(100, system=si)
    '100B'
    >>> size(1000, system=si)
    '1K'
    >>> size(2000, system=si)
    '2K'
    >>> size(10000, system=si)
    '10K'
    >>> size(20000, system=si)
    '20K'
    >>> size(100000, system=si)
    '100K'
    >>> size(200000, system=si)
    '200K'
    >>> size(1000000, system=si)
    '1M'
    >>> size(2000000, system=si)
    '2M'
    
    """
    for factor, suffix in system:
        if bytes >= factor:
            break
    amount = int(bytes/factor)
    if isinstance(suffix, tuple):
        singular, multiple = suffix
        if amount == 1:
            suffix = singular
        else:
            suffix = multiple
    return str(amount) + suffix


########NEW FILE########
__FILENAME__ = plat_osx
# Copyright 2010 Hardcoded Software (http://www.hardcoded.net)

# This software is licensed under the "BSD" License as described in the "LICENSE" file,
# which should be included with this package. The terms are also available at
# http://www.hardcoded.net/licenses/bsd_license

from ctypes import cdll, byref, Structure, c_char, c_char_p
from ctypes.util import find_library

Foundation = cdll.LoadLibrary(find_library('Foundation'))
CoreServices = cdll.LoadLibrary(find_library('CoreServices'))

GetMacOSStatusCommentString = Foundation.GetMacOSStatusCommentString
GetMacOSStatusCommentString.restype = c_char_p
FSPathMakeRefWithOptions = CoreServices.FSPathMakeRefWithOptions
FSMoveObjectToTrashSync = CoreServices.FSMoveObjectToTrashSync

kFSPathMakeRefDefaultOptions = 0
kFSPathMakeRefDoNotFollowLeafSymlink = 0x01

kFSFileOperationDefaultOptions = 0
kFSFileOperationOverwrite = 0x01
kFSFileOperationSkipSourcePermissionErrors = 0x02
kFSFileOperationDoNotMoveAcrossVolumes = 0x04
kFSFileOperationSkipPreflight = 0x08

class FSRef(Structure):
    _fields_ = [('hidden', c_char * 80)]

def check_op_result(op_result):
    if op_result:
        msg = GetMacOSStatusCommentString(op_result).decode('utf-8')
        raise OSError(msg)

def send2trash(path):
    if not isinstance(path, bytes):
        path = path.encode('utf-8')
    fp = FSRef()
    opts = kFSPathMakeRefDoNotFollowLeafSymlink
    op_result = FSPathMakeRefWithOptions(path, opts, byref(fp), None)
    check_op_result(op_result)
    opts = kFSFileOperationDefaultOptions
    op_result = FSMoveObjectToTrashSync(byref(fp), None, opts)
    check_op_result(op_result)

########NEW FILE########
__FILENAME__ = plat_other
# Copyright 2010 Hardcoded Software (http://www.hardcoded.net)

# This software is licensed under the "BSD" License as described in the "LICENSE" file,
# which should be included with this package. The terms are also available at
# http://www.hardcoded.net/licenses/bsd_license

# This is a reimplementation of plat_other.py with reference to the
# freedesktop.org trash specification:
#   [1] http://www.freedesktop.org/wiki/Specifications/trash-spec
#   [2] http://www.ramendik.ru/docs/trashspec.html
# See also:
#   [3] http://standards.freedesktop.org/basedir-spec/basedir-spec-latest.html
#
# For external volumes this implementation will raise an exception if it can't
# find or create the user's trash directory.

#import sys
import os
import os.path as op
from datetime import datetime
import stat
import shutil
from urllib.parse import quote

FILES_DIR = 'files'
INFO_DIR = 'info'
INFO_SUFFIX = '.trashinfo'

# Default of ~/.local/share [3]
XDG_DATA_HOME = op.expanduser(os.environ.get('XDG_DATA_HOME', '~/.local/share'))
HOMETRASH = op.join(XDG_DATA_HOME, 'Trash')

uid = os.getuid()
TOPDIR_TRASH = '.Trash'
TOPDIR_FALLBACK = '.Trash-' + str(uid)

def is_parent(parent, path):
    path = op.realpath(path) # In case it's a symlink
    parent = op.realpath(parent)
    return path.startswith(parent)

def format_date(date):
    return date.strftime("%Y-%m-%dT%H:%M:%S")

def info_for(src, topdir):
    # ...it MUST not include a ".."" directory, and for files not "under" that
    # directory, absolute pathnames must be used. [2]
    if topdir is None or not is_parent(topdir, src):
        src = op.abspath(src)
    else:
        src = op.relpath(src, topdir)

    info  = "[Trash Info]\n"
    info += "Path=" + quote(src) + "\n"
    info += "DeletionDate=" + format_date(datetime.now()) + "\n"
    return info

def check_create(dir):
    # use 0700 for paths [3]
    if not op.exists(dir):
        os.makedirs(dir, 0o700)

def trash_move(src, dst, topdir=None):
    filename = op.basename(src)
    filespath = op.join(dst, FILES_DIR)
    infopath = op.join(dst, INFO_DIR)
    base_name, ext = op.splitext(filename)

    counter = 0
    destname = filename
    while op.exists(op.join(filespath, destname)) or op.exists(op.join(infopath, destname + INFO_SUFFIX)):
        counter += 1
        destname = '%s %s%s' % (base_name, counter, ext)

    check_create(filespath)
    check_create(infopath)
    try:
        os.rename(src, op.join(filespath, destname))
    except:
        shutil.move(src, op.join(filespath, destname))
    f = open(op.join(infopath, destname + INFO_SUFFIX), 'w')
    f.write(info_for(src, topdir))
    f.close()

def find_mount_point(path):
    # Even if something's wrong, "/" is a mount point, so the loop will exit.
    # Use realpath in case it's a symlink
    path = op.realpath(path) # Required to avoid infinite loop
    while not op.ismount(path):
        path = op.split(path)[0]
    return path

def find_ext_volume_global_trash(volume_root):
    # from [2] Trash directories (1) check for a .Trash dir with the right
    # permissions set.
    trash_dir = op.join(volume_root, TOPDIR_TRASH)
    if not op.exists(trash_dir):
        return None

    mode = os.lstat(trash_dir).st_mode
    # vol/.Trash must be a directory, cannot be a symlink, and must have the
    # sticky bit set.
    if not op.isdir(trash_dir) or op.islink(trash_dir) or not (mode & stat.S_ISVTX):
        return None

    trash_dir = op.join(trash_dir, str(uid))
    try:
        check_create(trash_dir)
    except OSError:
        return None
    return trash_dir

def find_ext_volume_fallback_trash(volume_root):
    # from [2] Trash directories (1) create a .Trash-$uid dir.
    trash_dir = op.join(volume_root, TOPDIR_FALLBACK)
    # Try to make the directory, if we can't the OSError exception will escape
    # be thrown out of send2trash.
    check_create(trash_dir)
    return trash_dir

def find_ext_volume_trash(volume_root):
    trash_dir = find_ext_volume_global_trash(volume_root)
    if trash_dir is None:
        trash_dir = find_ext_volume_fallback_trash(volume_root)
    return trash_dir

# Pull this out so it's easy to stub (to avoid stubbing lstat itself)
def get_dev(path):
    return os.lstat(path).st_dev

def send2trash(path):
    #if not isinstance(path, str):
    #    path = str(path, sys.getfilesystemencoding())
    #if not op.exists(path):
    #    raise OSError("File not found: %s" % path)
    # ...should check whether the user has the necessary permissions to delete
    # it, before starting the trashing operation itself. [2]
    #if not os.access(path, os.W_OK):
    #    raise OSError("Permission denied: %s" % path)
    # if the file to be trashed is on the same device as HOMETRASH we
    # want to move it there.
    path_dev = get_dev(path)

    # If XDG_DATA_HOME or HOMETRASH do not yet exist we need to stat the
    # home directory, and these paths will be created further on if needed.
    trash_dev = get_dev(op.expanduser('~'))

    if path_dev == trash_dev or ( os.path.exists(XDG_DATA_HOME) and os.path.exists(HOMETRASH) ):
        topdir = XDG_DATA_HOME
        dest_trash = HOMETRASH
    else:
        topdir = find_mount_point(path)
        trash_dev = get_dev(topdir)
        if trash_dev != path_dev:
            raise OSError("Couldn't find mount point for %s" % path)
        dest_trash = find_ext_volume_trash(topdir)
    trash_move(path, dest_trash, topdir)

########NEW FILE########
__FILENAME__ = plat_win
# Copyright 2010 Hardcoded Software (http://www.hardcoded.net)

# This software is licensed under the "BSD" License as described in the "LICENSE" file, 
# which should be included with this package. The terms are also available at 
# http://www.hardcoded.net/licenses/bsd_license

from ctypes import windll, Structure, byref, c_uint
from ctypes.wintypes import HWND, UINT, LPCWSTR, BOOL
#import os.path as op

shell32 = windll.shell32
SHFileOperationW = shell32.SHFileOperationW

class SHFILEOPSTRUCTW(Structure):
    _fields_ = [
        ("hwnd", HWND),
        ("wFunc", UINT),
        ("pFrom", LPCWSTR),
        ("pTo", LPCWSTR),
        ("fFlags", c_uint),
        ("fAnyOperationsAborted", BOOL),
        ("hNameMappings", c_uint),
        ("lpszProgressTitle", LPCWSTR),
        ]

FO_MOVE = 1
FO_COPY = 2
FO_DELETE = 3
FO_RENAME = 4

FOF_MULTIDESTFILES = 1
FOF_SILENT = 4
FOF_NOCONFIRMATION = 16
FOF_ALLOWUNDO = 64
FOF_NOERRORUI = 1024

def send2trash(path):
		#	
    #if not isinstance(path, str):
    #    path = str(path, 'mbcs')
    #if not op.isabs(path):
    #    path = op.abspath(path)
    fileop = SHFILEOPSTRUCTW()
    fileop.hwnd = 0
    fileop.wFunc = FO_DELETE
    fileop.pFrom = LPCWSTR(path + '\0')
    fileop.pTo = None
    fileop.fFlags = FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_NOERRORUI | FOF_SILENT
    fileop.fAnyOperationsAborted = 0
    fileop.hNameMappings = 0
    fileop.lpszProgressTitle = None
    result = SHFileOperationW(byref(fileop))
    if result:
        msg = "Couldn't perform operation. Error code: %d" % result
        raise OSError(msg)


########NEW FILE########
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
        "Mac OS X", "Windows".

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
__FILENAME__ = SideBarItem
# coding=utf8
import sublime
import os
import re
import shutil

from .SideBarProject import SideBarProject

class Object():
	pass

def expandVars(path):
	for k, v in list(os.environ.items()):
		path = path.replace('%'+k+'%', v).replace('%'+k.lower()+'%', v)
	return path

class SideBarItem:

	def __init__(self, path, is_directory):
		self._path = path
		self._is_directory = is_directory

	def path(self, path = ''):
		if path == '':
			return self._path
		else:
			self._path = path
			self._is_directory = os.path.isdir(path)
			return path

	def pathWithoutProject(self):
		path = self.path()
		for directory in SideBarProject().getDirectories():
			path = path.replace(directory, '', 1)
		return path.replace('\\', '/')

	def pathProject(self):
		path = self.path()
		for directory in SideBarProject().getDirectories():
			path2 = path.replace(directory, '', 1)
			if path2 != path:
				return directory
		return False

	def url(self, type):

		filenames = []

		# scans a la htaccess
		item = SideBarItem(self.path(), self.isDirectory())
		while not os.path.exists(item.join('.sublime/SideBarEnhancements.json')):
			if item.dirname() == item.path():
				break;
			item.path(item.dirname())
		item  = SideBarItem(item.join('.sublime/SideBarEnhancements.json'), False);
		if item.exists():
			filenames.append(item.path())

		filenames.append(os.path.dirname(sublime.packages_path())+'/Settings/SideBarEnhancements.json')

		import collections
		for filename in filenames:
			if os.path.lexists(filename):
				import json
				data = open(filename, 'r').read()
				data = data.replace('\t', ' ').replace('\\', '/').replace('\\', '/').replace('//', '/').replace('//', '/').replace('http:/', 'http://').replace('https:/', 'https://')
				data = json.loads(data, strict=False, object_pairs_hook=collections.OrderedDict)
				for key in list(data.keys()):
					#	print('-------------------------------------------------------')
					#	print(key);
					if filename == filenames[len(filenames)-1]:
						base = expandVars(key)
					else:
						base = os.path.normpath(expandVars(os.path.dirname(os.path.dirname(filename))+'/'+key))
					base = base.replace('\\', '/').replace('\\', '/').replace('//', '/').replace('//', '/')
					#	print(base)
					current = self.path().replace('\\', '/').replace('\\', '/').replace('//', '/').replace('//', '/')
					#	print(current)
					url_path = re.sub(re.compile("^"+re.escape(base), re.IGNORECASE), '', current);
					#	print(url_path)
					if url_path != current:
						url = data[key][type]
						if url:
							if url[-1:] != '/':
								url = url+'/'
						import urllib.request, urllib.parse, urllib.error
						return url+(re.sub("^/", '', urllib.parse.quote(url_path)));
		return False

	def isUnderCurrentProject(self):
		path = self.path()
		path2 = self.path()
		for directory in SideBarProject().getDirectories():
			path2 = path2.replace(directory, '', 1)
		return path != path2

	def pathRelativeFromProject(self):
		return re.sub('^/+', '', self.pathWithoutProject())

	def pathRelativeFromProjectEncoded(self):
		import urllib.request, urllib.parse, urllib.error
		return urllib.parse.quote(self.pathRelativeFromProject())

	def pathRelativeFromView(self):
		return os.path.relpath(self.path(), os.path.dirname(sublime.active_window().active_view().file_name())).replace('\\', '/')

	def pathRelativeFromViewEncoded(self):
		import urllib.request, urllib.parse, urllib.error
		return urllib.parse.quote(os.path.relpath(self.path(), os.path.dirname(sublime.active_window().active_view().file_name())).replace('\\', '/'))

	def pathAbsoluteFromProject(self):
		return self.pathWithoutProject()

	def pathAbsoluteFromProjectEncoded(self):
		import urllib.request, urllib.parse, urllib.error
		return urllib.parse.quote(self.pathAbsoluteFromProject())

	def uri(self):
		uri = 'file:'+(self.path().replace('\\', '/').replace('//', '/'));
		return uri

	def join(self, name):
		return os.path.join(self.path(), name)

	def dirname(self):
		branch, leaf = os.path.split(self.path())
		return branch;

	def forCwdSystemPath(self):
		if self.isDirectory():
			return self.path()
		else:
			return self.dirname()

	def forCwdSystemName(self):
		if self.isDirectory():
			return '.'
		else:
			path = self.path()
			branch = self.dirname()
			leaf = path.replace(branch, '', 1).replace('\\', '').replace('/', '')
			return leaf

	def forCwdSystemPathRelativeFrom(self, relativeFrom):
		relative = SideBarItem(relativeFrom, os.path.isdir(relativeFrom))
		path = self.path().replace(relative.path(), '', 1).replace('\\', '/')
		if path == '':
			return '.'
		else:
			return re.sub('^/+', '', path)

	def forCwdSystemPathRelativeFromRecursive(self, relativeFrom):
		relative = SideBarItem(relativeFrom, os.path.isdir(relativeFrom))
		path = self.path().replace(relative.path(), '', 1).replace('\\', '/')
		if path == '':
			return '.'
		else:
			if self.isDirectory():
				return re.sub('^/+', '', path)+'/'
			else:
				return re.sub('^/+', '', path)

	def dirnameCreate(self):
		try:
			os.makedirs(self.dirname())
		except:
			pass

	def name(self):
		branch, leaf = os.path.split(self.path())
		return leaf;

	def nameEncoded(self):
		import urllib.request, urllib.parse, urllib.error
		return urllib.parse.quote(self.name());

	def namePretty(self):
		return self.name().replace(self.extension(), '').replace('-', ' ').replace('_', ' ').strip();

	def open(self):
		if self.isDirectory():
			import subprocess
			if sublime.platform() == 'osx':
				subprocess.Popen(['/Applications/Utilities/Terminal.app/Contents/MacOS/Terminal', '.'], cwd=self.forCwdSystemPath())
			elif sublime.platform() == 'windows':
				try:
					subprocess.Popen(['start', 'powershell'], cwd=self.forCwdSystemPath(), shell=True)
				except:
					subprocess.Popen(['start', 'cmd', '.'], cwd=self.forCwdSystemPath(), shell=True)
			elif sublime.platform() == 'linux':
				subprocess.Popen(['gnome-terminal', '.'], cwd=self.forCwdSystemPath())
		else:
			if sublime.platform() == 'osx':
				import subprocess
				subprocess.Popen(['open', self.name()], cwd=self.dirname())
			elif sublime.platform() == 'windows':
				import subprocess
				subprocess.Popen(['start',  '', self.path()], cwd=self.dirname(), shell=True)
			else:
				from . import desktop
				desktop.open(self.path())

	def edit(self):
		view = sublime.active_window().open_file(self.path())
		view.settings().set('open_with_edit', True);
		return view

	def isDirectory(self):
		return self._is_directory

	def isFile(self):
		return self.isDirectory() == False

	def contentUTF8(self):
		return open(self.path(), 'r', newline='').read()

	def contentBinary(self):
		return open(self.path(), "rb").read()

	def contentBase64(self):
		import base64
		base64text = base64.b64encode(self.contentBinary()).decode('utf-8')
		return 'data:'+self.mime()+';charset=utf-8;base64,'+(base64text.replace('\n', ''))

	def reveal(self):
		if sublime.platform() == 'windows':
			import subprocess
			if self.isDirectory():
				subprocess.Popen(["explorer", self.path()])
			else:
				subprocess.Popen(["explorer", '/select,', self.path()])
		else:
			sublime.active_window().run_command("open_dir", {"dir": self.dirname(), "file": self.name()} )

	def write(self, content):
		open(self.path(), 'w+', encoding='utf8', newline='').write(str(content))

	def mime(self):
		import mimetypes
		return mimetypes.guess_type(self.path())[0] or 'application/octet-stream'

	def extension(self):
		return os.path.splitext('name'+self.name())[1].lower()

	def exists(self):
		return os.path.isdir(self.path()) or os.path.isfile(self.path())

	def overwrite(self):
		overwrite = sublime.ok_cancel_dialog("Destination exists", "Delete, and overwrite")
		if overwrite:
			from SideBarEnhancements.send2trash import send2trash
			send2trash(self.path())
			return True
		else:
			return False

	def create(self):
		if self.isDirectory():
			self.dirnameCreate()
			os.makedirs(self.path())
		else:
			self.dirnameCreate()
			self.write('')

	def copy(self, location, replace = False):
		location = SideBarItem(location, os.path.isdir(location));
		if location.exists() and replace == False:
			return False
		elif location.exists() and location.isFile():
			os.remove(location.path())

		location.dirnameCreate();
		if self.isDirectory():
			if location.exists():
				self.copyRecursive(self.path(), location.path())
			else:
				shutil.copytree(self.path(), location.path())
		else:
			shutil.copy2(self.path(), location.path())
		return True

	def copyRecursive(self, _from, _to):

		if os.path.isfile(_from) or os.path.islink(_from):
			try:
				os.makedirs(os.path.dirname(_to));
			except:
				pass
			if os.path.exists(_to):
				os.remove(_to)
			shutil.copy2(_from, _to)
		else:
			try:
				os.makedirs(_to);
			except:
				pass
			for content in os.listdir(_from):
				__from = os.path.join(_from, content)
				__to = os.path.join(_to, content)
				self.copyRecursive(__from, __to)

	def move(self, location, replace = False):
		location = SideBarItem(location, os.path.isdir(location));
		if location.exists() and replace == False:
			if self.path().lower() == location.path().lower():
				pass
			else:
				return False
		elif location.exists() and location.isFile():
			os.remove(location.path())

		if self.path().lower() == location.path().lower():
			location.dirnameCreate();
			os.rename(self.path(), location.path()+'.sublime-temp')
			os.rename(location.path()+'.sublime-temp', location.path())
			self._moveMoveViews(self.path(), location.path())
		else:
			location.dirnameCreate();
			if location.exists():
				self.moveRecursive(self.path(), location.path())
			else:
				os.rename(self.path(), location.path())
			self._moveMoveViews(self.path(), location.path())
		return True

	def moveRecursive(self, _from, _to):
		if os.path.isfile(_from) or os.path.islink(_from):
			try:
				os.makedirs(os.path.dirname(_to));
			except:
				pass
			if os.path.exists(_to):
				os.remove(_to)
			os.rename(_from, _to)
		else:
			try:
				os.makedirs(_to);
			except:
				pass
			for content in os.listdir(_from):
				__from = os.path.join(_from, content)
				__to = os.path.join(_to, content)
				self.moveRecursive(__from, __to)
			os.rmdir(_from)

	def _moveMoveViews(self, old, location):
		for window in sublime.windows():
			active_view = window.active_view()
			views = []
			for view in window.views():
				if view.file_name():
					views.append(view)
			views.reverse();
			for view in views:
				if old == view.file_name():
					active_view = self._moveMoveView(window, view, location, active_view)
				elif view.file_name().find(old+'\\') == 0:
					active_view = self._moveMoveView(window, view, view.file_name().replace(old+'\\', location+'\\', 1), active_view)
				elif view.file_name().find(old+'/') == 0:
					active_view = self._moveMoveView(window, view, view.file_name().replace(old+'/', location+'/', 1), active_view)

	def _moveMoveView(self, window, view, location, active_view):
		view.retarget(location)

	def closeViews(self):
		path = self.path()
		closed_items = []
		for window in sublime.windows():
			active_view = window.active_view()
			views = []
			for view in window.views():
				if view.file_name():
					views.append(view)
			views.reverse();
			for view in views:
				if path == view.file_name():
					if view.window():
						closed_items.append([view.file_name(), view.window(), view.window().get_view_index(view)])
					if len(window.views()) == 1:
						window.new_file()
					window.focus_view(view)
					window.run_command('revert')
					window.run_command('close')
				elif view.file_name().find(path+'\\') == 0:
					if view.window():
						closed_items.append([view.file_name(), view.window(), view.window().get_view_index(view)])
					if len(window.views()) == 1:
						window.new_file()
					window.focus_view(view)
					window.run_command('revert')
					window.run_command('close')
				elif view.file_name().find(path+'/') == 0:
					if view.window():
						closed_items.append([view.file_name(), view.window(), view.window().get_view_index(view)])
					if len(window.views()) == 1:
						window.new_file()
					window.focus_view(view)
					window.run_command('revert')
					window.run_command('close')

			# try to repaint
			try:
				window.focus_view(active_view)
				window.focus_view(window.active_view())
			except:
				try:
					window.focus_view(window.active_view())
				except:
					pass
		return closed_items

########NEW FILE########
__FILENAME__ = SideBarProject
import sublime

class SideBarProject:

	def getDirectories(self):
		return sublime.active_window().folders()

	def hasDirectories(self):
		return len(self.getDirectories()) > 0

	def hasOpenedProject(self):
		return self.getProjectFile() != None

	def getDirectoryFromPath(self, path):
		for directory in self.getDirectories():
			maybe_path = path.replace(directory, '', 1)
			if maybe_path != path:
				return directory

	def getProjectFile(self):
		return sublime.active_window().project_file_name()

	def getProjectJson(self):
		return sublime.active_window().project_data()

	def setProjectJson(self, data):
		return sublime.active_window().set_project_data(data)

	def excludeDirectory(self, path, exclude):
		data = self.getProjectJson()
		from .SideBarItem import SideBarItem
		for folder in data['folders']:
			project_folder = folder['path']
			if project_folder == '.':
				project_folder = SideBarItem(self.getProjectFile(), False).dirname();
			if path.find(project_folder) == 0:
				try:
					folder['folder_exclude_patterns'].append(exclude)
				except:
					folder['folder_exclude_patterns'] = [exclude]
				self.setProjectJson(data);
				return

	def excludeFile(self, path, exclude):
		data = self.getProjectJson()
		from .SideBarItem import SideBarItem
		for folder in data['folders']:
			project_folder = folder['path']
			if project_folder == '.':
				project_folder = SideBarItem(self.getProjectFile(), False).dirname();
			if path.find(project_folder) == 0:
				try:
					folder['file_exclude_patterns'].append(exclude)
				except:
					folder['file_exclude_patterns'] = [exclude]
				self.setProjectJson(data);
				return

	def add(self, path):
		data = self.getProjectJson()
		data['folders'].append({'follow_symlinks':True, 'path':path});
		self.setProjectJson(data);

	def refresh(self):
		try:
			sublime.set_timeout(lambda:sublime.active_window().run_command('refresh_folder_list'), 200);
			sublime.set_timeout(lambda:sublime.active_window().run_command('refresh_folder_list'), 1300);
		except:
			pass
########NEW FILE########
__FILENAME__ = SideBarSelection
# coding=utf8
import sublime
import os
import re

from .SideBarProject import SideBarProject
from .SideBarItem import SideBarItem

class SideBarSelection:

	def __init__(self, paths = []):

		if len(paths) < 1:
			try:
				path = sublime.active_window().active_view().file_name()
				if self.isNone(path):
					paths = []
				else:
					paths = [path]
			except:
				paths = []
		self._paths = paths
		self._paths.sort()
		self._obtained_selection_information_basic = False
		self._obtained_selection_information_extended = False

	def len(self):
		return len(self._paths)

	def hasDirectories(self):
		self._obtainSelectionInformationBasic()
		return self._has_directories

	def hasFiles(self):
		self._obtainSelectionInformationBasic()
		return self._has_files

	def hasOnlyDirectories(self):
		self._obtainSelectionInformationBasic()
		return self._only_directories

	def hasOnlyFiles(self):
		self._obtainSelectionInformationBasic()
		return self._only_files

	def hasProjectDirectories(self):
		if self.hasDirectories():
			project_directories = SideBarProject().getDirectories()
			for item in self.getSelectedDirectories():
				if item.path() in project_directories:
					return True
			return False
		else:
			return False

	def hasItemsUnderProject(self):
		for item in self.getSelectedItems():
			if item.isUnderCurrentProject():
				return True
		return False

	def hasImages(self):
		return self.hasFilesWithExtension('gif|jpg|jpeg|png')

	def hasFilesWithExtension(self, extensions):
		extensions = re.compile('('+extensions+')$', re.I);
		for item in self.getSelectedFiles():
			if extensions.search(item.path()):
				return True;
		return False

	def getSelectedItems(self):
		self._obtainSelectionInformationExtended()
		return self._files + self._directories;

	def getSelectedItemsWithoutChildItems(self):
		self._obtainSelectionInformationExtended()
		items = []
		for item in self._items_without_containing_child_items:
			items.append(SideBarItem(item, os.path.isdir(item)))
		return items

	def getSelectedDirectories(self):
		self._obtainSelectionInformationExtended()
		return self._directories;

	def getSelectedFiles(self):
		self._obtainSelectionInformationExtended()
		return self._files;

	def getSelectedDirectoriesOrDirnames(self):
		self._obtainSelectionInformationExtended()
		return self._directories_or_dirnames;

	def getSelectedImages(self):
		return self.getSelectedFilesWithExtension('gif|jpg|jpeg|png')

	def getSelectedFilesWithExtension(self, extensions):
		items = []
		extensions = re.compile('('+extensions+')$', re.I);
		for item in self.getSelectedFiles():
			if extensions.search(item.path()):
				items.append(item)
		return items

	def _obtainSelectionInformationBasic(self):
		if not self._obtained_selection_information_basic:
			self._obtained_selection_information_basic = True

			self._has_directories = False
			self._has_files = False
			self._only_directories = False
			self._only_files = False

			for path in self._paths:
				if self._has_directories == False and os.path.isdir(path):
					self._has_directories = True
				if self._has_files == False and os.path.isdir(path) == False:
					self._has_files = True
				if self._has_files and self._has_directories:
					break

			if self._has_files and self._has_directories:
				self._only_directories = False
				self._only_files 	= False
			elif self._has_files:
				self._only_files 	= True
			elif self._has_directories:
				self._only_directories = True

	def _obtainSelectionInformationExtended(self):
		if not self._obtained_selection_information_extended:
			self._obtained_selection_information_extended = True

			self._directories = []
			self._files = []
			self._directories_or_dirnames = []
			self._items_without_containing_child_items = []

			_directories = []
			_files = []
			_directories_or_dirnames = []
			_items_without_containing_child_items = []

			for path in self._paths:
				if os.path.isdir(path):
					item = SideBarItem(path, True)
					if item.path() not in _directories:
						_directories.append(item.path())
						self._directories.append(item)
					if item.path() not in _directories_or_dirnames:
						_directories_or_dirnames.append(item.path())
						self._directories_or_dirnames.append(item)
					_items_without_containing_child_items = self._itemsWithoutContainingChildItems(_items_without_containing_child_items, item.path())
				else:
					item = SideBarItem(path, False)
					if item.path() not in _files:
						_files.append(item.path())
						self._files.append(item)
					_items_without_containing_child_items = self._itemsWithoutContainingChildItems(_items_without_containing_child_items, item.path())
					item = SideBarItem(os.path.dirname(path), True)
					if item.path() not in _directories_or_dirnames:
						_directories_or_dirnames.append(item.path())
						self._directories_or_dirnames.append(item)

			self._items_without_containing_child_items = _items_without_containing_child_items

	def _itemsWithoutContainingChildItems(self, items, item):
		new_list = []
		add = True
		for i in items:
			if i.find(item+'\\') == 0 or i.find(item+'/') == 0:
				continue
			else:
				new_list.append(i)
			if (item+'\\').find(i+'\\') == 0 or (item+'/').find(i+'/') == 0:
				add = False
		if add:
			new_list.append(item)
		return new_list

	def isNone(self, path):
		if path == None or path == '' or path == '.' or path == '..' or path == './' or path == '../' or path == '/' or path == '//' or path == '\\' or path == '\\\\' or path == '\\\\\\\\' or path == '\\\\?\\' or path == '\\\\?' or path == '\\\\\\\\?\\\\':
			return True
		else:
			return False

########NEW FILE########
__FILENAME__ = SideBar
# coding=utf8
import sublime, sublime_plugin
import os, shutil

import threading, time

from .sidebar.SideBarItem import SideBarItem
from .sidebar.SideBarSelection import SideBarSelection
from .sidebar.SideBarProject import SideBarProject

from .Edit import Edit as Edit

# needed for getting local app data path on windows
if sublime.platform() == 'windows':
	import winreg

def expandVars(path):
	for k, v in list(os.environ.items()):
		path = path.replace('%'+k+'%', v).replace('%'+k.lower()+'%', v)
	return path

#NOTES
# A "directory" for this plugin is a "directory"
# A "directory" for a user is a "folder"

s = {}

def checkVersion():
	version = '2014';
	if s.get('version') != version:
		s.set('version', "setting no longer updated");
		sublime.save_settings('Side Bar.sublime-settings')

def plugin_loaded():
	global s
	s = sublime.load_settings('Side Bar.sublime-settings')
	checkVersion()

def Window():
	return sublime.active_window()

class OpenWithListener(sublime_plugin.EventListener):

	def on_load_async(self, view):
		if view and view.file_name() and not view.settings().get('open_with_edit'):
			item = SideBarItem(os.path.join(sublime.packages_path(), 'User', 'SideBarEnhancements', 'Open With', 'Side Bar.sublime-menu'), False)
			if item.exists():
				settings = sublime.decode_value(item.contentUTF8())
				selection = SideBarSelection([view.file_name()])
				for item in settings[0]['children']:
					try:
						if item['open_automatically'] and selection.hasFilesWithExtension(item['args']['extensions']):
							SideBarFilesOpenWithCommand(sublime_plugin.WindowCommand).run([view.file_name()], item['args']['application'], item['args']['extensions'])
							view.window().run_command('close')
							break
					except:
						pass

class SideBarNewFile2Command(sublime_plugin.WindowCommand):
	def run(self, paths = [], name = ""):
		import functools
		Window().run_command('hide_panel');
		Window().show_input_panel("File Name:", name, functools.partial(SideBarNewFileCommand(sublime_plugin.WindowCommand).on_done, paths, True), None, None)

class SideBarNewFileCommand(sublime_plugin.WindowCommand):
	def run(self, paths = [], name = ""):
		import functools
		Window().run_command('hide_panel');
		Window().show_input_panel("File Name:", name, functools.partial(self.on_done, paths, False), None, None)

	def on_done(self, paths, relative_to_project, name):
		if relative_to_project or s.get('new_files_relative_to_project_root'):
			paths = SideBarProject().getDirectories()
			if paths:
				paths = [SideBarItem(paths[0], False)]
			if not paths:
				paths = SideBarSelection(paths).getSelectedDirectoriesOrDirnames()
		else:
			paths = SideBarSelection(paths).getSelectedDirectoriesOrDirnames()
		if not paths:
			paths = SideBarProject().getDirectories()
			if paths:
				paths = [SideBarItem(paths[0], False)]
		if not paths:
			sublime.active_window().new_file()
		else:
			for item in paths:
				item = SideBarItem(item.join(name), False)
				if item.exists():
					sublime.error_message("Unable to create file, file or folder exists.")
					self.run(paths, name)
					return
				else:
					try:
						item.create()
						item.edit()
					except:
						sublime.error_message("Unable to create file:\n\n"+item.path())
						self.run(paths, name)
						return
			SideBarProject().refresh();

class SideBarNewDirectoryCommand(sublime_plugin.WindowCommand):
	def run(self, paths = [], name = ""):
		import functools
		Window().run_command('hide_panel');
		Window().show_input_panel("Folder Name:", name, functools.partial(self.on_done, paths), None, None)

	def on_done(self, paths, name):
		for item in SideBarSelection(paths).getSelectedDirectoriesOrDirnames():
			item = SideBarItem(item.join(name), True)
			if item.exists():
				sublime.error_message("Unable to create folder, folder or file exists.")
				self.run(paths, name)
				return
			else:
				item.create()
				if not item.exists():
					sublime.error_message("Unable to create folder:\n\n"+item.path())
					self.run(paths, name)
					return
		SideBarProject().refresh();

	def is_enabled(self, paths = []):
		return SideBarSelection(paths).len() > 0

class SideBarEditCommand(sublime_plugin.WindowCommand):
	def run(self, paths = []):
		for item in SideBarSelection(paths).getSelectedFiles():
			item.edit()

	def is_enabled(self, paths = []):
		return SideBarSelection(paths).hasFiles()

	def is_visible(self, paths =[]):
		return not s.get('disabled_menuitem_edit')

class SideBarOpenCommand(sublime_plugin.WindowCommand):
	def run(self, paths = []):
		for item in SideBarSelection(paths).getSelectedItems():
			item.open()

	def is_enabled(self, paths = []):
		return SideBarSelection(paths).len() > 0

	def is_visible(self, paths =[]):
		return not s.get('disabled_menuitem_open_run')

class SideBarFilesOpenWithEditApplicationsCommand(sublime_plugin.WindowCommand):
	def run(self, paths = []):
		platform = '';
		if sublime.platform() == 'osx':
			platform = 'OSX'
		elif sublime.platform() == 'windows':
			platform = 'Windows'
		else:
			platform = 'Linux'

		item = SideBarItem(os.path.join(sublime.packages_path(), 'User', 'SideBarEnhancements', 'Open With', 'Side Bar.sublime-menu'), False)
		if not item.exists() and False:
			item = SideBarItem(os.path.join(sublime.packages_path(), 'User', 'SideBarEnhancements', 'Open With', 'Side Bar ('+platform+').sublime-menu'), False)

		if not item.exists():
			item.create()
			item.write("""[
	{"id": "side-bar-files-open-with",
		"children":
		[

			//application 1
			{
				"caption": "Photoshop",
				"id": "side-bar-files-open-with-photoshop",

				"command": "side_bar_files_open_with",
				"args": {
									"paths": [],
									"application": "Adobe Photoshop CS5.app", // OSX
									"extensions":"psd|png|jpg|jpeg"  //any file with these extensions
								},
				"open_automatically" : false // will close the view/tab and launch the application
			},

			//separator
			{"caption":"-"},

			//application 2
			{
				"caption": "SeaMonkey",
				"id": "side-bar-files-open-with-seamonkey",

				"command": "side_bar_files_open_with",
				"args": {
									"paths": [],
									"application": "C:\\\\Archivos de programa\\\\SeaMonkey\\\\seamonkey.exe", // WINNT
									"extensions":"" //open all even folders
								},
				"open_automatically" : false // will close the view/tab and launch the application
			},
			//application n
			{
				"caption": "Chrome",
				"id": "side-bar-files-open-with-chrome",

				"command": "side_bar_files_open_with",
				"args": {
									"paths": [],
									"application": "C:\\\\Documents and Settings\\\\tito\\\\local\\\\Datos de programa\\\\Google\\\\Chrome\\\\Application\\\\chrome.exe",
									"extensions":".*" //any file with extension
						},
				"open_automatically" : false // will close the view/tab and launch the application
			},

			{"caption":"-"}
		]
	}
]""");
		item.edit()

	def is_enabled(self, paths = []):
		return True

class SideBarFilesOpenWithCommand(sublime_plugin.WindowCommand):
	def run(self, paths = [], application = "", extensions = "", args=""):
		application_dir, application_name = os.path.split(application)

		if extensions == '*':
			extensions = '.*'
		if extensions == '':
			items = SideBarSelection(paths).getSelectedItems()
		else:
			items = SideBarSelection(paths).getSelectedFilesWithExtension(extensions)

		import subprocess
		try:
			for item in items:
				if sublime.platform() == 'osx':
					subprocess.Popen(['open', '-a', application, item.name()], cwd=item.dirname())
				elif sublime.platform() == 'windows':
					subprocess.Popen([application_name, item.path()], cwd=expandVars(application_dir), shell=True)
				else:
					subprocess.Popen([application_name, item.name()], cwd=item.dirname())
		except:
			sublime.error_message('Unable to "Open With..", probably incorrect path to application, check the Console.')

	def is_enabled(self, paths = [], application = "", extensions = ""):
		if extensions == '*':
			extensions = '.*'
		if extensions == '':
			return SideBarSelection(paths).len() > 0
		else:
			return SideBarSelection(paths).hasFilesWithExtension(extensions)

	def is_visible(self, paths = [], application = "", extensions = ""):
		if extensions == '*':
			extensions = '.*'
		if extensions == '':
			return SideBarSelection(paths).len() > 0
		else:
			has = SideBarSelection(paths).hasFilesWithExtension(extensions)
			return has or (not has and not s.get("hide_open_with_entries_when_there_are_no_applicable"))

class SideBarFindInSelectedCommand(sublime_plugin.WindowCommand):
	def run(self, paths = []):
		window = sublime.active_window()
		views = []
		for view in window.views():
			if view.name() == 'Find Results':
				views.append(view);
		for view in views:
			view.close();
		items = []
		for item in SideBarSelection(paths).getSelectedItemsWithoutChildItems():
			items.append(item.path())
		Window().run_command('hide_panel');
		Window().run_command("show_panel", {"panel": "find_in_files", "where":",".join(items) })

	def is_enabled(self, paths = []):
		return SideBarSelection(paths).len() > 0

class SideBarFindInParentCommand(sublime_plugin.WindowCommand):
	def run(self, paths = []):
		items = []
		for item in SideBarSelection(paths).getSelectedItems():
			items.append(item.dirname())
		items = list(set(items))
		Window().run_command('hide_panel');
		Window().run_command("show_panel", {"panel": "find_in_files", "where":",".join(items) })

	def is_enabled(self, paths = []):
		return SideBarSelection(paths).len() > 0

class SideBarFindInProjectFoldersCommand(sublime_plugin.WindowCommand):
	def run(self):
		Window().run_command('hide_panel');
		Window().run_command("show_panel", {"panel": "find_in_files", "where":"<project>"})

class SideBarFindInProjectCommand(sublime_plugin.WindowCommand):
	def run(self, paths = []):
		Window().run_command('hide_panel');
		Window().run_command("show_panel", {"panel": "find_in_files", "where":"<project>"})

	def is_visible(self, paths = []):
		return not s.get('disabled_menuitem_find_in_project')

class SideBarFindInProjectFolderCommand(sublime_plugin.WindowCommand):
	def run(self, paths = []):
		items = []
		for item in SideBarSelection(paths).getSelectedItemsWithoutChildItems():
			items.append(SideBarProject().getDirectoryFromPath(item.path()))
		items = list(set(items))
		if items:
			Window().run_command('hide_panel');
			Window().run_command("show_panel", {"panel": "find_in_files", "where":",".join(items)})

class SideBarFindInFilesWithExtensionCommand(sublime_plugin.WindowCommand):
	def run(self, paths = []):
		items = []
		for item in SideBarSelection(paths).getSelectedItems():
			items.append('*'+item.extension())
		items = list(set(items))
		Window().run_command('hide_panel');
		Window().run_command("show_panel", {"panel": "find_in_files", "where":",".join(items) })

	def is_enabled(self, paths = []):
		return SideBarSelection(paths).hasFiles()

	def description(self, paths = []):
		items = []
		for item in SideBarSelection(paths).getSelectedFiles():
			items.append('*'+item.extension())
		items = list(set(items))
		if len(items) > 1:
			return 'In Files With Extensions '+(",".join(items))+'…'
		elif len(items) > 0:
			return 'In Files With Extension '+(",".join(items))+'…'
		else:
			return 'In Files With Extension…'

sidebar_instant_search = 0

class SideBarFindFilesPathContainingCommand(sublime_plugin.WindowCommand):
	def run(self, paths = []):
		global sidebar_instant_search
		if paths == [] and SideBarProject().getDirectories():
			paths = SideBarProject().getDirectories()
		else:
			paths = [item.path() for item in SideBarSelection(paths).getSelectedDirectoriesOrDirnames()]
		if paths == []:
			return
		view = Window().new_file()
		view.settings().set('word_wrap', False)
		view.set_name('Instant File Search')
		view.set_syntax_file('Packages/SideBarEnhancements/SideBar Results.hidden-tmLanguage')
		view.set_scratch(True)
		view.settings().set('sidebar_instant_search_paths', paths)
		with Edit(view) as edit:
			edit.replace(sublime.Region(0, view.size()), "Type to search: ")
		view.sel().clear()
		view.sel().add(sublime.Region(16))
		sidebar_instant_search += 1

	def is_enabled(self, paths=[]):
		return True

class SideBarFindResultsViewListener(sublime_plugin.EventListener):

	def on_modified(self, view):
		global sidebar_instant_search
		if sidebar_instant_search > 0 and view.settings().has('sidebar_instant_search_paths'):
			row, col = view.rowcol(view.sel()[0].begin())
			if row != 0 or not view.sel()[0].empty():
				return
			paths = view.settings().get('sidebar_instant_search_paths')
			searchTerm = view.substr(view.line(0)).replace("Type to search:", "").strip()
			start_time = time.time()
			view.settings().set('sidebar_search_paths_start_time', start_time)
			if searchTerm:
				sublime.set_timeout(lambda:SideBarFindFilesPathContainingSearchThread(paths, searchTerm, view, start_time).start(), 300)

	def on_close(self, view):
		if view.settings().has('sidebar_instant_search_paths'):
			global sidebar_instant_search
			sidebar_instant_search -= 1

class SideBarFindFilesPathContainingSearchThread(threading.Thread):
		def __init__(self, paths, searchTerm, view, start_time):
			if view.settings().get('sidebar_search_paths_start_time') != start_time:
				self.should_run = False
			else:
				self.should_run = True
			self.view = view
			self.searchTerm = searchTerm
			self.paths = paths
			self.start_time = start_time
			threading.Thread.__init__(self)

		def run(self):
			if not self.should_run:
				return
			# print 'run forrest run'
			self.total = 0
			self.highlight_from = 0
			self.match_result = ''
			self.match_result += 'Type to search: '+self.searchTerm+'\n'
			for item in SideBarSelection(self.paths).getSelectedDirectoriesOrDirnames():
				self.files = []
				self.num_files = 0
				self.find(item.path())
				self.match_result += '\n'
				length = len(self.files)
				if length > 1:
					self.match_result += str(length)+' matches'
				elif length > 0:
					self.match_result += '1 match'
				else:
					self.match_result += 'No match'
				self.match_result += ' in '+str(self.num_files)+' files for term "'+self.searchTerm+'" under \n"'+item.path()+'"\n\n'
				if self.highlight_from == 0:
					self.highlight_from = len(self.match_result)
				self.match_result += ('\n'.join(self.files))
				self.total = self.total + length
			self.match_result += '\n'
			sublime.set_timeout(lambda:self.on_done(), 0)

		def on_done(self):
			if self.start_time == self.view.settings().get('sidebar_search_paths_start_time'):
				view = self.view;
				sel = sublime.Region(view.sel()[0].begin(), view.sel()[0].end())
				with Edit(view) as edit:
					edit.replace(sublime.Region(0, view.size()), self.match_result);
				view.erase_regions("sidebar_search_instant_highlight")
				if self.total < 30000 and len(self.searchTerm) > 1:
					regions = [item for item in view.find_all(self.searchTerm, sublime.LITERAL|sublime.IGNORECASE) if item.begin() >= self.highlight_from]
					view.add_regions("sidebar_search_instant_highlight", regions, '',  '', sublime.DRAW_EMPTY|sublime.DRAW_OUTLINED|sublime.DRAW_EMPTY_AS_OVERWRITE)
				view.sel().clear()
				view.sel().add(sel)

		def find(self, path):
			if os.path.isfile(path) or os.path.islink(path):
				self.num_files = self.num_files+1
				if self.match(path):
					self.files.append(path)
			elif os.path.isdir(path):
				for content in os.listdir(path):
					file = os.path.join(path, content)
					if os.path.isfile(file) or os.path.islink(file):
						self.num_files = self.num_files+1
						if self.match(file):
							self.files.append(file)
					else:
						self.find(file)

		def match(self, path):
			return False if path.lower().find(self.searchTerm.lower()) == -1 else True

class SideBarCutCommand(sublime_plugin.WindowCommand):
	def run(self, paths = []):
		s = sublime.load_settings("SideBarEnhancements/Clipboard.sublime-settings")
		items = []
		for item in SideBarSelection(paths).getSelectedItemsWithoutChildItems():
			items.append(item.path())

		if len(items) > 0:
			s.set('cut', "\n".join(items))
			s.set('copy', '')
			if len(items) > 1 :
				sublime.status_message("Items cut")
			else :
				sublime.status_message("Item cut")

	def is_enabled(self, paths = []):
		return SideBarSelection(paths).len() > 0 and SideBarSelection(paths).hasProjectDirectories() == False


class SideBarCopyCommand(sublime_plugin.WindowCommand):
	def run(self, paths = []):
		s = sublime.load_settings("SideBarEnhancements/Clipboard.sublime-settings")
		items = []
		for item in SideBarSelection(paths).getSelectedItemsWithoutChildItems():
			items.append(item.path())

		if len(items) > 0:
			s.set('cut', '')
			s.set('copy', "\n".join(items))
			if len(items) > 1 :
				sublime.status_message("Items copied")
			else :
				sublime.status_message("Item copied")

	def is_enabled(self, paths = []):
		return SideBarSelection(paths).len() > 0

class SideBarPasteCommand(sublime_plugin.WindowCommand):
	def run(self, paths = [], in_parent = 'False', test = 'True', replace = 'False'):
		SideBarPasteThread(paths, in_parent, test, replace).start()

	def is_enabled(self, paths = [], in_parent = False):
		s = sublime.load_settings("SideBarEnhancements/Clipboard.sublime-settings")
		return s.get('cut', '') + s.get('copy', '') != '' and len(SideBarSelection(paths).getSelectedDirectoriesOrDirnames()) == 1

	def is_visible(self, paths = [], in_parent = False):
		if in_parent == 'True':
			return not s.get('disabled_menuitem_paste_in_parent')
		else:
			return True

class SideBarPasteThread(threading.Thread):
	def __init__(self, paths = [], in_parent = 'False', test = 'True', replace = 'False'):
		self.paths = paths
		self.in_parent = in_parent
		self.test = test
		self.replace = replace
		threading.Thread.__init__(self)

	def run(self):
		SideBarPasteCommand2(sublime_plugin.WindowCommand).run(self.paths, self.in_parent, self.test, self.replace)

class SideBarPasteCommand2(sublime_plugin.WindowCommand):
	def run(self, paths = [], in_parent = 'False', test = 'True', replace = 'False'):
		s = sublime.load_settings("SideBarEnhancements/Clipboard.sublime-settings")

		cut = s.get('cut', '')
		copy = s.get('copy', '')

		already_exists_paths = []

		if SideBarSelection(paths).len() > 0:
			if in_parent == 'False':
				location = SideBarSelection(paths).getSelectedItems()[0].path()
			else:
				location = SideBarSelection(paths).getSelectedDirectoriesOrDirnames()[0].dirname()

			if os.path.isdir(location) == False:
				location = SideBarItem(os.path.dirname(location), True)
			else:
				location = SideBarItem(location, True)

			if cut != '':
				cut = cut.split("\n")
				for path in cut:
					path = SideBarItem(path, os.path.isdir(path))
					new  = os.path.join(location.path(), path.name())
					if test == 'True' and os.path.exists(new):
						already_exists_paths.append(new)
					elif test == 'False':
						if os.path.exists(new) and replace == 'False':
							pass
						else:
							try:
								if not path.move(new, replace == 'True'):
									sublime.error_message("Unable to cut and paste, destination exists.")
									return
							except:
								sublime.error_message("Unable to move:\n\n"+path.path()+"\n\nto\n\n"+new)
								return

			if copy != '':
				copy = copy.split("\n")
				for path in copy:
					path = SideBarItem(path, os.path.isdir(path))
					new  = os.path.join(location.path(), path.name())
					if test == 'True' and os.path.exists(new):
						already_exists_paths.append(new)
					elif test == 'False':
						if os.path.exists(new) and replace == 'False':
							pass
						else:
							try:
								if not path.copy(new, replace == 'True'):
									sublime.error_message("Unable to copy and paste, destination exists.")
									return
							except:
								sublime.error_message("Unable to copy:\n\n"+path.path()+"\n\nto\n\n"+new)
								return

			if test == 'True' and len(already_exists_paths):
				self.confirm(paths, in_parent, already_exists_paths)
			elif test == 'True' and not len(already_exists_paths):
				SideBarPasteThread(paths, in_parent, 'False', 'False').start();
			elif test == 'False':
				cut = s.set('cut', '')
				SideBarProject().refresh();

	def confirm(self, paths, in_parent, data):
		import functools
		window = sublime.active_window()
		window.show_input_panel("BUG!", '', '', None, None)
		window.run_command('hide_panel');

		yes = []
		yes.append('Yes, Replace the following items:');
		for item in data:
			yes.append(SideBarItem(item, os.path.isdir(item)).pathWithoutProject())

		no = []
		no.append('No');
		no.append('Continue without replacing');

		while len(no) != len(yes):
			no.append('ST3 BUG');

		window.show_quick_panel([yes, no], functools.partial(self.on_done, paths, in_parent))

	def on_done(self, paths, in_parent, result):
		if result != -1:
			if result == 0:
				SideBarPasteThread(paths, in_parent, 'False', 'True').start()
			else:
				SideBarPasteThread(paths, in_parent, 'False', 'False').start()

class SideBarCopyNameCommand(sublime_plugin.WindowCommand):
	def run(self, paths = []):
		items = []
		for item in SideBarSelection(paths).getSelectedItems():
			items.append(item.name())

		if len(items) > 0:
			sublime.set_clipboard("\n".join(items));
			if len(items) > 1 :
				sublime.status_message("Items copied")
			else :
				sublime.status_message("Item copied")

	def is_enabled(self, paths = []):
		return SideBarSelection(paths).len() > 0

	def is_visible(self, paths =[]):
		return not s.get('disabled_menuitem_copy_name')

class SideBarCopyNameEncodedCommand(sublime_plugin.WindowCommand):
	def run(self, paths = []):
		items = []
		for item in SideBarSelection(paths).getSelectedItems():
			items.append(item.nameEncoded())

		if len(items) > 0:
			sublime.set_clipboard("\n".join(items));
			if len(items) > 1 :
				sublime.status_message("Items copied")
			else :
				sublime.status_message("Item copied")

	def is_enabled(self, paths = []):
		return SideBarSelection(paths).len() > 0


class SideBarCopyPathCommand(sublime_plugin.WindowCommand):
	def run(self, paths = []):
		items = []
		for item in SideBarSelection(paths).getSelectedItems():
			items.append(item.path())

		if len(items) > 0:
			sublime.set_clipboard("\n".join(items));
			if len(items) > 1 :
				sublime.status_message("Items copied")
			else :
				sublime.status_message("Item copied")

	def is_enabled(self, paths = []):
		return SideBarSelection(paths).len() > 0

class SideBarCopyDirPathCommand(sublime_plugin.WindowCommand):
	def run(self, paths = []):
		items = []
		for item in SideBarSelection(paths).getSelectedDirectoriesOrDirnames():
			items.append(item.path())

		if len(items) > 0:
			sublime.set_clipboard("\n".join(items));
			if len(items) > 1 :
				sublime.status_message("Items copied")
			else :
				sublime.status_message("Item copied")

	def is_enabled(self, paths = []):
		return SideBarSelection(paths).len() > 0

	def is_visible(self, paths =[]):
		return not s.get('disabled_menuitem_copy_dir_path')

class SideBarCopyPathEncodedCommand(sublime_plugin.WindowCommand):
	def run(self, paths = []):
		items = []
		for item in SideBarSelection(paths).getSelectedItems():
			items.append(item.uri())

		if len(items) > 0:
			sublime.set_clipboard("\n".join(items));
			if len(items) > 1 :
				sublime.status_message("Items copied")
			else :
				sublime.status_message("Item copied")

	def is_enabled(self, paths = []):
		return SideBarSelection(paths).len() > 0

class SideBarCopyPathRelativeFromProjectCommand(sublime_plugin.WindowCommand):
	def run(self, paths = []):
		items = []
		for item in SideBarSelection(paths).getSelectedItems():
			items.append(item.pathRelativeFromProject())

		if len(items) > 0:
			sublime.set_clipboard("\n".join(items));
			if len(items) > 1 :
				sublime.status_message("Items copied")
			else :
				sublime.status_message("Item copied")

	def is_enabled(self, paths = []):
		return SideBarSelection(paths).len() > 0 and SideBarSelection(paths).hasItemsUnderProject()



class SideBarCopyPathRelativeFromProjectEncodedCommand(sublime_plugin.WindowCommand):
	def run(self, paths = []):
		items = []
		for item in SideBarSelection(paths).getSelectedItems():
			items.append(item.pathRelativeFromProjectEncoded())

		if len(items) > 0:
			sublime.set_clipboard("\n".join(items));
			if len(items) > 1 :
				sublime.status_message("Items copied")
			else :
				sublime.status_message("Item copied")

	def is_enabled(self, paths = []):
		return SideBarSelection(paths).len() > 0 and SideBarSelection(paths).hasItemsUnderProject()

class SideBarCopyPathRelativeFromViewCommand(sublime_plugin.WindowCommand):
	def run(self, paths = []):
		items = []
		for item in SideBarSelection(paths).getSelectedItems():
			items.append(item.pathRelativeFromView())

		if len(items) > 0:
			sublime.set_clipboard("\n".join(items));
			if len(items) > 1 :
				sublime.status_message("Items copied")
			else :
				sublime.status_message("Item copied")

	def is_enabled(self, paths = []):
		return SideBarSelection(paths).len() > 0

class SideBarCopyPathRelativeFromViewEncodedCommand(sublime_plugin.WindowCommand):
	def run(self, paths = []):
		items = []
		for item in SideBarSelection(paths).getSelectedItems():
			items.append(item.pathRelativeFromViewEncoded())

		if len(items) > 0:
			sublime.set_clipboard("\n".join(items));
			if len(items) > 1 :
				sublime.status_message("Items copied")
			else :
				sublime.status_message("Item copied")

	def is_enabled(self, paths = []):
		return SideBarSelection(paths).len() > 0

class SideBarCopyPathAbsoluteFromProjectCommand(sublime_plugin.WindowCommand):
	def run(self, paths = []):
		items = []
		for item in SideBarSelection(paths).getSelectedItems():
			items.append(item.pathAbsoluteFromProject())

		if len(items) > 0:
			sublime.set_clipboard("\n".join(items));
			if len(items) > 1 :
				sublime.status_message("Items copied")
			else :
				sublime.status_message("Item copied")

	def is_enabled(self, paths = []):
		return SideBarSelection(paths).len() > 0 and SideBarSelection(paths).hasItemsUnderProject()

class SideBarCopyPathAbsoluteFromProjectEncodedCommand(sublime_plugin.WindowCommand):
	def run(self, paths = []):
		items = []
		for item in SideBarSelection(paths).getSelectedItems():
			items.append(item.pathAbsoluteFromProjectEncoded())

		if len(items) > 0:
			sublime.set_clipboard("\n".join(items));
			if len(items) > 1 :
				sublime.status_message("Items copied")
			else :
				sublime.status_message("Item copied")

	def is_enabled(self, paths = []):
		return SideBarSelection(paths).len() > 0 and SideBarSelection(paths).hasItemsUnderProject()

	def is_visible(self, paths =[]):
		return not s.get('disabled_menuitem_copy_path')

class SideBarCopyTagAhrefCommand(sublime_plugin.WindowCommand):
	def run(self, paths = []):
		items = []
		for item in SideBarSelection(paths).getSelectedItems():
			items.append('<a href="'+item.pathAbsoluteFromProjectEncoded()+'">'+item.namePretty()+'</a>')

		if len(items) > 0:
			sublime.set_clipboard("\n".join(items));
			if len(items) > 1 :
				sublime.status_message("Items copied")
			else :
				sublime.status_message("Item copied")

	def is_enabled(self, paths = []):
		return SideBarSelection(paths).len() > 0 and SideBarSelection(paths).hasItemsUnderProject()

class SideBarCopyTagImgCommand(sublime_plugin.WindowCommand):

	def run(self, paths = []):
		items = []
		for item in SideBarSelection(paths).getSelectedImages():
			try:
				image_type, width, height = self.getImageInfo(item.path())
				items.append('<img src="'+item.pathAbsoluteFromProjectEncoded()+'" width="'+str(width)+'" height="'+str(height)+'">')
			except:
				items.append('<img src="'+item.pathAbsoluteFromProjectEncoded()+'">')
		if len(items) > 0:
			sublime.set_clipboard("\n".join(items));
			if len(items) > 1 :
				sublime.status_message("Items copied")
			else :
				sublime.status_message("Item copied")

	# http://stackoverflow.com/questions/8032642/how-to-obtain-image-size-using-standard-python-class-without-using-external-lib

	def getImageInfo(self, fname):
		import struct
		import imghdr

		'''Determine the image type of fhandle and return its size.
		from draco'''
		fhandle = open(fname, 'rb')
		head = fhandle.read(24)
		if len(head) != 24:
			return
		if imghdr.what(fname) == 'png':
			check = struct.unpack('>i', head[4:8])[0]
			if check != 0x0d0a1a0a:
				return
			width, height = struct.unpack('>ii', head[16:24])
		elif imghdr.what(fname) == 'gif':
			width, height = struct.unpack('<HH', head[6:10])
		elif imghdr.what(fname) == 'jpeg':
			try:
				fhandle.seek(0) # Read 0xff next
				size = 2
				ftype = 0
				while not 0xc0 <= ftype <= 0xcf:
					fhandle.seek(size, 1)
					byte = fhandle.read(1)
					while ord(byte) == 0xff:
						byte = fhandle.read(1)
					ftype = ord(byte)
					size = struct.unpack('>H', fhandle.read(2))[0] - 2
				# We are at a SOFn block
				fhandle.seek(1, 1)  # Skip `precision' byte.
				height, width = struct.unpack('>HH', fhandle.read(4))
			except Exception: #IGNORE:W0703
				return
		else:
			return
		return None, width, height

	def is_enabled(self, paths = []):
		return SideBarSelection(paths).hasImages() and SideBarSelection(paths).hasItemsUnderProject()

class SideBarCopyTagStyleCommand(sublime_plugin.WindowCommand):
	def run(self, paths = []):
		items = []
		for item in SideBarSelection(paths).getSelectedFilesWithExtension('css'):
			items.append('<link rel="stylesheet" type="text/css" href="'+item.pathAbsoluteFromProjectEncoded()+'"/>')

		if len(items) > 0:
			sublime.set_clipboard("\n".join(items));
			if len(items) > 1 :
				sublime.status_message("Items copied")
			else :
				sublime.status_message("Item copied")

	def is_enabled(self, paths = []):
		return SideBarSelection(paths).hasFilesWithExtension('css') and SideBarSelection(paths).hasItemsUnderProject()

class SideBarCopyTagScriptCommand(sublime_plugin.WindowCommand):
	def run(self, paths = []):
		items = []
		for item in SideBarSelection(paths).getSelectedFilesWithExtension('js'):
			items.append('<script type="text/javascript" src="'+item.pathAbsoluteFromProjectEncoded()+'"></script>')

		if len(items) > 0:
			sublime.set_clipboard("\n".join(items));
			if len(items) > 1 :
				sublime.status_message("Items copied")
			else :
				sublime.status_message("Item copied")

	def is_enabled(self, paths = []):
		return SideBarSelection(paths).hasFilesWithExtension('js') and SideBarSelection(paths).hasItemsUnderProject()

class SideBarCopyProjectDirectoriesCommand(sublime_plugin.WindowCommand):
	def run(self, paths = []):
		items = []
		for directory in SideBarProject().getDirectories():
			items.append(directory)

		if len(items) > 0:
			sublime.set_clipboard("\n".join(items));
			if len(items) > 1 :
				sublime.status_message("Items copied")
			else :
				sublime.status_message("Item copied")

	def is_enabled(self, paths = []):
		return True

class SideBarCopyContentUtf8Command(sublime_plugin.WindowCommand):
	def run(self, paths = []):
		items = []
		for item in SideBarSelection(paths).getSelectedFiles():
			items.append(item.contentUTF8())

		if len(items) > 0:
			sublime.set_clipboard("\n".join(items));
			if len(items) > 1 :
				sublime.status_message("Items content copied")
			else :
				sublime.status_message("Item content copied")

	def is_enabled(self, paths = []):
		return SideBarSelection(paths).hasFiles()

class SideBarCopyContentBase64Command(sublime_plugin.WindowCommand):
	def run(self, paths = []):
		items = []
		for item in SideBarSelection(paths).getSelectedFiles():
			items.append(item.contentBase64())

		if len(items) > 0:
			sublime.set_clipboard("\n".join(items));
			if len(items) > 1 :
				sublime.status_message("Items content copied")
			else :
				sublime.status_message("Item content copied")

	def is_enabled(self, paths = []):
		return SideBarSelection(paths).hasFiles()

class SideBarCopyUrlCommand(sublime_plugin.WindowCommand):
	def run(self, paths = []):
		items = []

		for item in SideBarSelection(paths).getSelectedItems():
			if item.isUnderCurrentProject():
				items.append(item.url('url_production'))

		if len(items) > 0:
			sublime.set_clipboard("\n".join(items));
			if len(items) > 1 :
				sublime.status_message("Items URL copied")
			else :
				sublime.status_message("Item URL copied")

	def is_enabled(self, paths = []):
		return SideBarSelection(paths).hasItemsUnderProject()

class SideBarDuplicateCommand(sublime_plugin.WindowCommand):
	def run(self, paths = [], new = False):
		import functools
		Window().run_command('hide_panel');
		view = Window().show_input_panel("Duplicate As:", new or SideBarSelection(paths).getSelectedItems()[0].path(), functools.partial(self.on_done, SideBarSelection(paths).getSelectedItems()[0].path()), None, None)
		view.sel().clear()
		view.sel().add(sublime.Region(view.size()-len(SideBarSelection(paths).getSelectedItems()[0].name()), view.size()-len(SideBarSelection(paths).getSelectedItems()[0].extension())))

	def on_done(self, old, new):
		item = SideBarItem(old, os.path.isdir(old))
		try:
			if not item.copy(new):
				# destination exists
				if SideBarItem(new, os.path.isdir(new)).overwrite():
					self.on_done(old, new)
				else:
					self.run([old], new)
				return
		except:
			sublime.error_message("Unable to copy:\n\n"+old+"\n\nto\n\n"+new)
			self.run([old], new)
			return
		item = SideBarItem(new, os.path.isdir(new))
		if item.isFile():
			item.edit();
		SideBarProject().refresh();

	def is_enabled(self, paths = []):
		return SideBarSelection(paths).len() == 1 and SideBarSelection(paths).hasProjectDirectories() == False

class SideBarRenameCommand(sublime_plugin.WindowCommand):
	def run(self, paths = [], newLeaf = False):
		import functools
		branch, leaf = os.path.split(SideBarSelection(paths).getSelectedItems()[0].path())
		Window().run_command('hide_panel');
		view = Window().show_input_panel("New Name:", newLeaf or leaf, functools.partial(self.on_done, SideBarSelection(paths).getSelectedItems()[0].path(), branch), None, None)
		view.sel().clear()
		view.sel().add(sublime.Region(view.size()-len(SideBarSelection(paths).getSelectedItems()[0].name()), view.size()-len(SideBarSelection(paths).getSelectedItems()[0].extension())))

	def on_done(self, old, branch, leaf):
		Window().run_command('hide_panel');
		leaf = leaf.strip();
		new = os.path.join(branch, leaf)
		item = SideBarItem(old, os.path.isdir(old))
		try:
			if not item.move(new):
				# sublime.error_message("Unable to rename, destination exists.")
				# destination exists
				if SideBarItem(new, os.path.isdir(new)).overwrite():
					self.on_done(old, branch, leaf)
				else:
					self.run([old], leaf)
		except:
			sublime.error_message("Unable to rename:\n\n"+old+"\n\nto\n\n"+new)
			self.run([old], leaf)
			raise
			return
		SideBarProject().refresh();

	def is_enabled(self, paths = []):
		return SideBarSelection(paths).len() == 1 and SideBarSelection(paths).hasProjectDirectories() == False

class SideBarMassRenameCommand(sublime_plugin.WindowCommand):
	def run(self, paths = []):
		import functools
		Window().run_command('hide_panel');
		view = Window().show_input_panel("Find:", '', functools.partial(self.on_find, paths), None, None)

	def on_find(self, paths, find):
		if not find:
			return
		import functools
		Window().run_command('hide_panel');
		view = Window().show_input_panel("Replace:", '', functools.partial(self.on_replace, paths, find), None, None)

	def on_replace(self, paths, find, replace):
		if not replace:
			return
		if find == '' or replace == '':
			return None
		else:
			to_rename_or_move = []
			for item in SideBarSelection(paths).getSelectedItemsWithoutChildItems():
				self.recurse(item.path(), to_rename_or_move)
			to_rename_or_move.sort()
			to_rename_or_move.reverse()
			for item in to_rename_or_move:
				if find in item:
					origin = SideBarItem(item, os.path.isdir(item))
					destination = SideBarItem(origin.pathProject()+''+origin.pathWithoutProject().replace(find, replace), os.path.isdir(item))
					origin.move(destination.path());
			SideBarProject().refresh();

	def recurse(self, path, paths):
		if os.path.isfile(path) or os.path.islink(path):
			paths.append(path)
		else:
			for content in os.listdir(path):
				file = os.path.join(path, content)
				if os.path.isfile(file) or os.path.islink(file):
					paths.append(file)
				else:
					self.recurse(file, paths)
			paths.append(path)

	def is_enabled(self, paths = []):
		return SideBarSelection(paths).len() > 0 and SideBarSelection(paths).hasProjectDirectories() == False

class SideBarMoveCommand(sublime_plugin.WindowCommand):
	def run(self, paths = [], new = False):
		import functools
		Window().run_command('hide_panel');
		view = Window().show_input_panel("New Location:", new or SideBarSelection(paths).getSelectedItems()[0].path(), functools.partial(self.on_done, SideBarSelection(paths).getSelectedItems()[0].path()), None, None)
		view.sel().clear()
		view.sel().add(sublime.Region(view.size()-len(SideBarSelection(paths).getSelectedItems()[0].name()), view.size()-len(SideBarSelection(paths).getSelectedItems()[0].extension())))

	def on_done(self, old, new):
		item = SideBarItem(old, os.path.isdir(old))
		try:
			if not item.move(new):
				# sublime.error_message("Unable to move, destination exists.")
				if SideBarItem(new, os.path.isdir(new)).overwrite():
					self.on_done(old, new)
				else:
					self.run([old], new)
				return
		except:
			sublime.error_message("Unable to move:\n\n"+old+"\n\nto\n\n"+new)
			self.run([old], new)
			return
		SideBarProject().refresh();

	def is_enabled(self, paths = []):
		return SideBarSelection(paths).len() == 1 and SideBarSelection(paths).hasProjectDirectories() == False

class SideBarDeleteCommand(sublime_plugin.WindowCommand):
	def run(self, paths = [], confirmed = 'False'):

		if confirmed == 'False' and s.get('confirm_before_deleting', True):
			if sublime.platform() == 'osx':
				if sublime.ok_cancel_dialog('delete the selected items?'):
					self.run(paths, 'True')
			else:
				self.confirm([item.path() for item in SideBarSelection(paths).getSelectedItems()], [item.pathWithoutProject() for item in SideBarSelection(paths).getSelectedItems()])
		else:
			try:
				from .send2trash import send2trash
				for item in SideBarSelection(paths).getSelectedItemsWithoutChildItems():
					if s.get('close_affected_buffers_when_deleting_even_if_dirty', False):
						item.closeViews()
					if s.get('disable_send_to_trash', False):
						if sublime.platform() == 'windows':
							self.remove('\\\\?\\'+item.path());
						else:
							self.remove(item.path());
					else:
						send2trash(item.path())
				SideBarProject().refresh();
			except:
				import functools
				Window().show_input_panel("BUG!", '', '', None, None)
				Window().run_command('hide_panel');
				Window().show_input_panel("Permanently Delete:", SideBarSelection(paths).getSelectedItems()[0].path(), functools.partial(self.on_done, SideBarSelection(paths).getSelectedItems()[0].path()), None, None)

	def confirm(self, paths, display_paths):
		import functools
		window = sublime.active_window()
		window.show_input_panel("BUG!", '', '', None, None)
		window.run_command('hide_panel');

		yes = []
		yes.append('Yes, delete the selected items.');
		for item in display_paths:
			yes.append(item);

		no = []
		no.append('No');
		no.append('Cancel the operation.');

		while len(no) != len(yes):
			no.append('');

		if sublime.platform() == 'osx':
			sublime.set_timeout(lambda:window.show_quick_panel([yes, no], functools.partial(self.on_confirm, paths)), 200);
		else:
			window.show_quick_panel([yes, no], functools.partial(self.on_confirm, paths))

	def on_confirm(self, paths, result):
		if result != -1:
			if result == 0:
				self.run(paths, 'True')

	def on_done(self, old, new):
		if s.get('close_affected_buffers_when_deleting_even_if_dirty', False):
			item = SideBarItem(new, os.path.isdir(new))
			item.closeViews()
		if sublime.platform() == 'windows':
			self.remove('\\\\?\\'+new);
		else:
			self.remove(new)
		SideBarProject().refresh();

	def remove(self, path):
		if os.path.isfile(path) or os.path.islink(path):
			self.remove_safe_file(path)
		else:
			for content in os.listdir(path):
				file = os.path.join(path, content)
				if os.path.isfile(file) or os.path.islink(file):
					self.remove_safe_file(file)
				else:
					self.remove(file)
			self.remove_safe_dir(path)

	def remove_safe_file(self, path):
		if not SideBarSelection().isNone(path):
			try:
				os.remove(path)
			except:
				print("Unable to remove file:\n\n"+path)
		else:
			print('path is none')
			print(path)

	def remove_safe_dir(self, path):
		if not SideBarSelection().isNone(path):
			try:
				shutil.rmtree(path)
			except:
				print("Unable to remove folder:\n\n"+path)
				if sublime.platform() == 'windows':
					try:
						shutil.rmtree(path)
					except:
						# raise error in case we were unable to delete.
						if os.path.exists(path):
							shutil.rmtree(path)
						else:
							pass

	def is_enabled(self, paths = []):
		return SideBarSelection(paths).len() > 0 and SideBarSelection(paths).hasProjectDirectories() == False


class SideBarEmptyCommand(sublime_plugin.WindowCommand):
	def run(self, paths = [], confirmed = 'False'):

		if confirmed == 'False' and s.get('confirm_before_deleting', True):
			if sublime.platform() == 'osx':
				if sublime.ok_cancel_dialog('empty the content of the folder?'):
					self.run(paths, 'True')
			else:
				self.confirm([item.path() for item in SideBarSelection(paths).getSelectedDirectoriesOrDirnames()], [item.pathWithoutProject() for item in SideBarSelection(paths).getSelectedDirectoriesOrDirnames()])
		else:
			try:
				from .send2trash import send2trash
				for item in SideBarSelection(paths).getSelectedDirectoriesOrDirnames():
					for content in os.listdir(item.path()):
						file = os.path.join(item.path(), content)
						if not SideBarSelection().isNone(file):
							send2trash(file)
					if s.get('close_affected_buffers_when_deleting_even_if_dirty', False):
						item.closeViews()
			except:
				pass
			SideBarProject().refresh();

	def confirm(self, paths, display_paths):
		import functools
		window = sublime.active_window()
		window.show_input_panel("BUG!", '', '', None, None)
		window.run_command('hide_panel');

		yes = []
		yes.append('Yes, empty the selected items.');
		for item in display_paths:
			yes.append(item);

		no = []
		no.append('No');
		no.append('Cancel the operation.');

		while len(no) != len(yes):
			no.append('');

		if sublime.platform() == 'osx':
			sublime.set_timeout(lambda:window.show_quick_panel([yes, no], functools.partial(self.on_confirm, paths)), 200);
		else:
			window.show_quick_panel([yes, no], functools.partial(self.on_confirm, paths))

	def on_confirm(self, paths, result):
		if result != -1:
			if result == 0:
				self.run(paths, 'True')

	def is_enabled(self, paths = []):
		return SideBarSelection(paths).len() > 0

	def is_visible(self, paths =[]):
		return not s.get('disabled_menuitem_empty')

class SideBarRevealCommand(sublime_plugin.WindowCommand):
	def run(self, paths = []):
		for item in SideBarSelection(paths).getSelectedItems():
			item.reveal()

	def is_enabled(self, paths = []):
		return SideBarSelection(paths).len() > 0

class SideBarProjectOpenFileCommand(sublime_plugin.WindowCommand):
	def run(self, paths = []):
		project = SideBarProject()
		if project.hasOpenedProject():
			SideBarItem(project.getProjectFile(), False).edit();

	def is_enabled(self, paths = []):
		return SideBarProject().hasOpenedProject()

class SideBarPreviewEditUrlsCommand(sublime_plugin.WindowCommand):
	def run(self, paths = []):
		item = SideBarItem(os.path.dirname(sublime.packages_path())+'/Settings/SideBarEnhancements.json', False)
		item.dirnameCreate();
		item.edit();

class SideBarProjectItemAddCommand(sublime_plugin.WindowCommand):
	def run(self, paths = []):
		project = SideBarProject()
		for item in SideBarSelection(paths).getSelectedDirectories():
			project.add(item.path())

	def is_enabled(self, paths = []):
		return SideBarSelection(paths).hasDirectories() and SideBarSelection(paths).hasProjectDirectories() == False

class SideBarProjectItemRemoveFolderCommand(sublime_plugin.WindowCommand):
	def run(self, paths = []):
		Window().run_command('remove_folder', {"dirs":paths})

	def is_enabled(self, paths =[]):
		selection = SideBarSelection(paths)
		project = SideBarProject()
		return project.hasDirectories() and all([item.path() in project.getDirectories() or not item.exists() for item in selection.getSelectedItems()])

class SideBarProjectItemExcludeCommand(sublime_plugin.WindowCommand):
	def run(self, paths = []):
		project = SideBarProject()
		for item in SideBarSelection(paths).getSelectedItems():
			if item.isDirectory():
				project.excludeDirectory(item.path(), item.pathRelativeFromProject())
			else:
				project.excludeFile(item.path(), item.pathRelativeFromProject())

	def is_enabled(self, paths = []):
		return SideBarSelection(paths).len() > 0 and SideBarSelection(paths).hasProjectDirectories() == False

class SideBarProjectItemExcludeFromIndexCommand(sublime_plugin.WindowCommand):
	def run(self, paths = [], type = 'item'):
		Preferences = sublime.load_settings("Preferences.sublime-settings")
		excluded = Preferences.get("index_exclude_patterns", [])
		for item in self.items(paths, type):
			excluded.append(item)
		excluded = list(set(excluded))
		Preferences.set("index_exclude_patterns", excluded);
		sublime.save_settings("Preferences.sublime-settings");

	def is_visible(self, paths = [], type = 'item'):
		return len(self.items(paths, type)) > 0

	def description(self, paths = [], type = 'item'):
		items = self.items(paths, type)
		return 'Exclude From the Index "'+(",".join(items))+'"'

	def items(self, paths = [], type = 'item'):
		items = []
		if type == 'item':
			for item in SideBarSelection(paths).getSelectedItems():
				if item.isDirectory():
					items.append(item.path()+'*')
				else:
					items.append(item.path())
		elif type == 'extension':
			for item in SideBarSelection(paths).getSelectedFiles():
				items.append('*'+item.extension())
		elif type == 'file':
			for item in SideBarSelection(paths).getSelectedFiles():
				items.append(item.name())
		items = list(set(items))
		return items

class SideBarDonateCommand(sublime_plugin.WindowCommand):
	def run(self, paths = []):
		import webbrowser
		webbrowser.open_new_tab("https://www.paypal.com/cgi-bin/webscr?cmd=_donations&business=YNNRSS2UJ8P88&lc=UY&item_name=Support%20%20SideBarEnhancements%20Developer&item_number=SideBarEnhancements&currency_code=USD&bn=PP%2dDonationsBF%3abtn_donateCC_LG%2egif%3aNonHosted")

class SideBarOpenInBrowserCommand(sublime_plugin.WindowCommand):
	def run(self, paths = [], type = False, browser = ""):

		if not browser:
			browser = s.get("default_browser", "")

		if type == False or type == 'testing':
			type = 'url_testing'
		elif type == 'production':
			type = 'url_production'
		else:
			type = 'url_testing'

		for item in SideBarSelection(paths).getSelectedItems():
			url = item.url(type) or item.uri()
			self.try_open(url, browser)

	def try_open(self, url, browser):
		import subprocess

		browser = browser.lower().strip();
		items = []

		if browser == 'chrome':
			if sublime.platform() == 'osx':
				items.extend(['open'])
				commands = ['-a', '/Applications/Google Chrome.app', url]
			elif sublime.platform() == 'windows':
				# read local app data path from registry
				aKey = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders")
				reg_value, reg_type = winreg.QueryValueEx (aKey, "Local AppData")

				if s.get('portable_browser') != '':
					items.extend([s.get('portable_browser')])
				items.extend([
					'%HOMEPATH%\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe'

					,reg_value+'\\Chrome\\Application\\chrome.exe'
					,reg_value+'\\Google\\Chrome\\Application\\chrome.exe'
					,'%HOMEPATH%\\Google\\Chrome\\Application\\chrome.exe'
					,'%PROGRAMFILES%\\Google\\Chrome\\Application\\chrome.exe'
					,'%PROGRAMFILES(X86)%\\Google\\Chrome\\Application\\chrome.exe'
					,'%USERPROFILE%\\Local\ Settings\\Application\ Data\\Google\\Chrome\\chrome.exe'
					,'%HOMEPATH%\\Chromium\\Application\\chrome.exe'
					,'%PROGRAMFILES%\\Chromium\\Application\\chrome.exe'
					,'%PROGRAMFILES(X86)%\\Chromium\\Application\\chrome.exe'
					,'%HOMEPATH%\\Local\ Settings\\Application\ Data\\Google\\Chrome\\Application\\chrome.exe'
					,'%HOMEPATH%\\Local Settings\\Application Data\\Google\\Chrome\\Application\\chrome.exe'
					,'chrome.exe'
				])


				commands = ['-new-tab', url]
			else:
				if s.get('portable_browser') != '':
					items.extend([s.get('portable_browser')])
				items.extend([
					'/usr/bin/google-chrome'
					,'/opt/google/chrome/chrome'
					,'chrome'
					,'google-chrome'
				])
				commands = ['-new-tab', url]

		elif browser == 'canary':
				if sublime.platform() == 'osx':
						items.extend(['open'])
						commands = ['-a', '/Applications/Google Chrome Canary.app', url]
				elif sublime.platform() == 'windows':
					# read local app data path from registry
					aKey = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders")
					reg_value, reg_type = winreg.QueryValueEx (aKey, "Local AppData")

					if s.get('portable_browser') != '':
						items.extend([s.get('portable_browser')])
					items.extend([
						'%HOMEPATH%\\AppData\\Local\\Google\\Chrome SxS\\Application\\chrome.exe'

						,reg_value+'\\Chrome SxS\\Application\\chrome.exe'
						,reg_value+'\\Google\\Chrome SxS\\Application\\chrome.exe'
						,'%HOMEPATH%\\Google\\Chrome SxS\\Application\\chrome.exe'
						,'%PROGRAMFILES%\\Google\\Chrome SxS\\Application\\chrome.exe'
						,'%PROGRAMFILES(X86)%\\Google\\Chrome SxS\\Application\\chrome.exe'
						,'%USERPROFILE%\\Local\ Settings\\Application\ Data\\Google\\Chrome SxS\\chrome.exe'
						,'%HOMEPATH%\\Local\ Settings\\Application\ Data\\Google\\Chrome SxS\\Application\\chrome.exe'
						,'%HOMEPATH%\\Local Settings\\Application Data\\Google\\Chrome SxS\\Application\\chrome.exe'
					])

					commands = ['-new-tab', url]

		elif browser == 'chromium':
			if sublime.platform() == 'osx':
				items.extend(['open'])
				commands = ['-a', '/Applications/Chromium.app', url]
			elif sublime.platform() == 'windows':
				# read local app data path from registry
				aKey = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders")
				reg_value, reg_type = winreg.QueryValueEx (aKey, "Local AppData")
				if s.get('portable_browser') != '':
					items.extend([s.get('portable_browser')])
				items.extend([
					'%HOMEPATH%\\AppData\\Local\\Google\\Chrome SxS\\Application\\chrome.exe'

					, reg_value+'\\Chromium\\Application\\chromium.exe'
					,'%USERPROFILE%\\Local Settings\\Application Data\\Google\\Chrome\\chromium.exe'
					,'%USERPROFILE%\\Local\ Settings\\Application\ Data\\Google\\Chrome\\chromium.exe'
					,'%HOMEPATH%\\Chromium\\Application\\chromium.exe'
					,'%PROGRAMFILES%\\Chromium\\Application\\chromium.exe'
					,'%PROGRAMFILES(X86)%\\Chromium\\Application\\chromium.exe'
					,'%HOMEPATH%\\Local Settings\\Application\ Data\\Google\\Chrome\\Application\\chromium.exe'
					,'%HOMEPATH%\\Local Settings\\Application Data\\Google\\Chrome\\Application\\chromium.exe'
					,'chromium.exe'

					, reg_value+'\\Chromium\\Application\\chrome.exe'
					,'%USERPROFILE%\\Local Settings\\Application Data\\Google\\Chrome\\chrome.exe'
					,'%USERPROFILE%\\Local\ Settings\\Application\ Data\\Google\\Chrome\\chrome.exe'
					,'%HOMEPATH%\\Chromium\\Application\\chrome.exe'
					,'%PROGRAMFILES%\\Chromium\\Application\\chrome.exe'
					,'%PROGRAMFILES(X86)%\\Chromium\\Application\\chrome.exe'
					,'%HOMEPATH%\\Local\ Settings\\Application\ Data\\Google\\Chrome\\Application\\chrome.exe'
					,'%HOMEPATH%\\Local Settings\\Application Data\\Google\\Chrome\\Application\\chrome.exe'
					,'chrome.exe'

				])
				commands = ['-new-tab', url]
			else:
				if s.get('portable_browser') != '':
					items.extend([s.get('portable_browser')])
				items.extend([
					'/usr/bin/chromium'
					,'chromium'
					,'/usr/bin/chromium-browser'
					,'chromium-browser'
				])
				commands = ['-new-tab', url]
		elif browser == 'firefox':
			if sublime.platform() == 'osx':
				items.extend(['open'])
				commands = ['-a', '/Applications/Firefox.app', url]
			else:
				if s.get('portable_browser') != '':
					items.extend([s.get('portable_browser')])
				items.extend([
					'/usr/bin/firefox'

					,'%PROGRAMFILES%\\Nightly\\firefox.exe'
					,'%PROGRAMFILES(X86)%\\Nightly\\firefox.exe'

					,'%PROGRAMFILES%\\Mozilla Firefox\\firefox.exe'
					,'%PROGRAMFILES(X86)%\\Mozilla Firefox\\firefox.exe'

					,'firefox'
					,'firefox.exe'
				])
				commands = ['-new-tab', url]
		elif browser == 'opera':
			if sublime.platform() == 'osx':
				items.extend(['open'])
				commands = ['-a', '/Applications/Opera.app', url]
			else:
				if s.get('portable_browser') != '':
					items.extend([s.get('portable_browser')])
				items.extend([
					'/usr/bin/opera'
					,'/usr/bin/opera-next'
					,'/usr/bin/operamobile'

					,'%PROGRAMFILES%\\Opera\\opera.exe'
					,'%PROGRAMFILES(X86)%\\Opera\\opera.exe'

					,'%PROGRAMFILES%\\Opera Next\\opera.exe'
					,'%PROGRAMFILES(X86)%\\Opera Next\\opera.exe'

					,'%PROGRAMFILES%\\Opera Mobile Emulator\\OperaMobileEmu.exe'
					,'%PROGRAMFILES(X86)%\\Opera Mobile Emulator\\OperaMobileEmu.exe'

					,'opera'
					,'opera.exe'
				])
				commands = ['-newtab', url]
		elif browser == 'safari':
			if sublime.platform() == 'osx':
				items.extend(['open'])
				commands = ['-a', 'Safari', url]
			else:
				if s.get('portable_browser') != '':
					items.extend([s.get('portable_browser')])
				items.extend([
					'/usr/bin/safari'

					,'%PROGRAMFILES%\\Safari\\Safari.exe'
					,'%PROGRAMFILES(X86)%\\Safari\\Safari.exe'

					,'Safari'
					,'Safari.exe'
				])
				commands = ['-new-tab', '-url', url]
		else:
			if s.get('portable_browser') != '':
				items.extend([s.get('portable_browser')])
			commands = ['-new-tab', url]

		for item in items:
			try:
				command2 = list(commands)
				command2.insert(0, expandVars(item))
				subprocess.Popen(command2)
				return
			except:
				try:
					command2 = list(commands)
					command2.insert(0, item)
					subprocess.Popen(command2)
					return
				except:
					pass
		try:
			if sublime.platform() == 'windows':
				commands = ['cmd','/c','start', '', url]
				subprocess.Popen(commands)
			elif sublime.platform() == 'linux':
				commands = ['xdg-open', url]
				subprocess.Popen(commands)
			else:
				commands = ['open', url]
				subprocess.Popen(commands)
			return
		except:
			pass

		sublime.error_message('Browser "'+browser+'" not found!\nIs installed? Which location...?')

	def is_enabled(self, paths = []):
		return SideBarSelection(paths).len() > 0

	def is_visible(self, paths =[]):
		return not s.get('disabled_menuitem_open_in_browser')

class SideBarOpenInNewWindowCommand(sublime_plugin.WindowCommand):
	def run(self, paths = []):
		import subprocess
		items = []

		executable_path = sublime.executable_path()

		if sublime.platform() == 'osx':
			app_path = executable_path[:executable_path.rfind(".app/")+5]
			executable_path = app_path+"Contents/SharedSupport/bin/subl"

		items.append(executable_path)

		for item in SideBarSelection(paths).getSelectedItems():
			items.append(item.forCwdSystemPath())
			items.append(item.path())
		subprocess.Popen(items, cwd=items[1])

	def is_visible(self, paths =[]):
		return not s.get('disabled_menuitem_open_in_new_window')

class SideBarOpenWithFinderCommand(sublime_plugin.WindowCommand):
	def run(self, paths = []):
		import subprocess
		for item in SideBarSelection(paths).getSelectedDirectoriesOrDirnames():
			subprocess.Popen(['open', item.name()], cwd=item.dirname())

	def is_visible(self, paths =[]):
		return sublime.platform() == 'osx'

########NEW FILE########
__FILENAME__ = SideBarDefaultDisable
from Default.side_bar import *

class NewFileAtCommand(sublime_plugin.WindowCommand):
	def is_visible(self):
		return False
	def is_enabled(self):
		return False
class DeleteFileCommand(sublime_plugin.WindowCommand):
	def is_visible(self):
		return False
	def is_enabled(self):
		return False
class NewFolderCommand(sublime_plugin.WindowCommand):
	def is_visible(self):
		return False
	def is_enabled(self):
		return False
class DeleteFolderCommand(sublime_plugin.WindowCommand):
	def is_visible(self):
		return False
	def is_enabled(self):
		return False
class RenamePathCommand(sublime_plugin.WindowCommand):
	def is_visible(self):
		return False
	def is_enabled(self):
		return False
class FindInFolderCommand(sublime_plugin.WindowCommand):
	def is_visible(self):
		return False
	def is_enabled(self):
		return False
class OpenContainingFolderCommand(sublime_plugin.WindowCommand):
	def is_visible(self):
		return False
	def is_enabled(self):
		return False
########NEW FILE########
__FILENAME__ = StatusBarFileSize
import sublime, sublime_plugin
from .hurry.filesize import size
from os.path import getsize

s = {}

def plugin_loaded():
	global s
	s = sublime.load_settings('Side Bar.sublime-settings')

class StatusBarFileSize(sublime_plugin.EventListener):

	def on_activated_async(self, v):
		if s.get('statusbar_file_size') and v.file_name():
			try:
				self.show(v, size(getsize(v.file_name())))
			except:
				pass

	def on_post_save_async(self, v):
		if s.get('statusbar_file_size') and v.file_name():
			try:
				self.show(v, size(getsize(v.file_name())))
			except:
				pass

	def show(self, v, size):
		v.set_status('statusbar_file_size', size);

########NEW FILE########
__FILENAME__ = StatusBarModifiedTime
import sublime, sublime_plugin, time
from os.path import getmtime

s = {}

def plugin_loaded():
	global s
	s = sublime.load_settings('Side Bar.sublime-settings')

class StatusBarModifiedTime(sublime_plugin.EventListener):

	def on_activated_async(self, v):
		if s.get('statusbar_modified_time') and v.file_name():
			try:
				self.show(v, getmtime(v.file_name()))
			except:
				pass

	def on_post_save_async(self, v):
		if s.get('statusbar_modified_time') and v.file_name():
			try:
				self.show(v, getmtime(v.file_name()))
			except:
				pass

	def show(self, v, mtime):
		v.set_status('statusbar_modified_time',  time.strftime(s.get('statusbar_modified_time_format'), time.localtime(mtime)));
########NEW FILE########
