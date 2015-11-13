__FILENAME__ = cli
# -*- coding: utf-8 -*-

"""
envy.cli
~~~~~~~~

This module contains the CLI for Envy.
"""

import sys

from .version import __version__
from .packages.clint import args
from .packages.clint.textui import colored, puts

class Command(object):
    COMMANDS = {}
    SHORT_MAP = {}

    @classmethod
    def register(klass, command):
        klass.COMMANDS[command.name] = command
        if command.short:
            for short in command.short:
                klass.SHORT_MAP[short] = command

    @classmethod
    def lookup(klass, name):
        if name in klass.SHORT_MAP:
            return klass.SHORT_MAP[name]
        if name in klass.COMMANDS:
            return klass.COMMANDS[name]
        else:
            return None

    @classmethod
    def all_commands(klass):
        return sorted(klass.COMMANDS.values(),
                      key=lambda cmd: cmd.name)

    def __init__(self, name=None, short=None, fn=None, usage=None, help=None):
        self.name = name
        self.short = short
        self.fn = fn
        self.usage = usage
        self.help = help

    def __call__(self, *args, **kw_args):
        return self.fn(*args, **kw_args)


def def_cmd(name=None, short=None, fn=None, usage=None, help=None):
    command = Command(name=name, short=short, fn=fn, usage=usage, help=help)
    Command.register(command)

def display_help():
    """Displays Legit help."""

    display_info()


def display_version():
    """Displays Legit version/release."""


    puts('{0} v{1}'.format(
        colored.yellow('envy'),
        __version__
    ))


def display_info():
    puts('{0}. {1}\n'.format(
        colored.yellow('envy'),
        'A Kenneth Reitz Project'
    ))


def show_error(msg):
    sys.stdout.flush()
    sys.stderr.write(msg + '\n')

def dispatch():
    command = Command.lookup(args.get(0))
    if command:
        arg = args.get(0)
        args.remove(arg)

        command.__call__(args)
        sys.exit()

    elif args.contains(('-h', '--help')):
        display_help()
        sys.exit(1)

    elif args.contains(('-v', '--version')):
        display_version()
        sys.exit(1)

    else:
        git_args = list(sys.argv)

        show_error(colored.red('Unknown command {0}'.format(args.get(0))))
        display_info()
        sys.exit(1)

def cmd_init(args):
    print 'init!'

def_cmd(
    name='init',
    fn=cmd_init,
    usage='init',
    help='Get a nice pretty list of branches.')

def main():
    dispatch()

########NEW FILE########
__FILENAME__ = core

########NEW FILE########
__FILENAME__ = arguments
# -*- coding: utf-8 -*-

"""
clint.arguments
~~~~~~~~~~~~~~~

This module provides the CLI argument interface.

"""


from __future__ import absolute_import

import os
from sys import argv

try:
    from collections import OrderedDict
except ImportError:
    from .packages.ordereddict import OrderedDict

from .utils import expand_path, is_collection

__all__ = ('Args', )


class Args(object):
    """CLI Argument management."""

    def __init__(self, args=None, no_argv=False):
        if not args:
            if not no_argv:
                self._args = argv[1:]
            else:
                self._args = []
        else:
            self._args = args


    def __len__(self):
        return len(self._args)


    def __repr__(self):
        return '<args %s>' % (repr(self._args))


    def __getitem__(self, i):
        try:
            return self.all[i]
        except IndexError:
            return None


    def __contains__(self, x):
        return self.first(x) is not None


    def get(self, x):
        """Returns argument at given index, else none."""
        try:
            return self.all[x]
        except IndexError:
            return None


    def get_with(self, x):
        """Returns first argument that contains given string."""
        return self.all[self.first_with(x)]


    def remove(self, x):
        """Removes given arg (or list thereof) from Args object."""

        def _remove(x):
            found = self.first(x)
            if found is not None:
                self._args.pop(found)

        if is_collection(x):
            for item in x:
                _remove(x)
        else:
            _remove(x)


    def pop(self, x):
        """Removes and Returns value at given index, else none."""
        try:
            return self._args.pop(x)
        except IndexError:
            return None


    def any_contain(self, x):
        """Tests if given string is contained in any stored argument."""

        return bool(self.first_with(x))


    def contains(self, x):
        """Tests if given object is in arguments list.
           Accepts strings and lists of strings."""

        return self.__contains__(x)


    def first(self, x):
        """Returns first found index of given value (or list of values)"""

        def _find( x):
            try:
                return self.all.index(str(x))
            except ValueError:
                return None

        if is_collection(x):
            for item in x:
                found = _find(item)
                if found is not None:
                    return found
            return None
        else:
            return _find(x)


    def first_with(self, x):
        """Returns first found index containing value (or list of values)"""

        def _find(x):
            try:
                for arg in self.all:
                    if x in arg:
                        return self.all.index(arg)
            except ValueError:
                return None

        if is_collection(x):
            for item in x:
                found = _find(item)
                if found:
                    return found
            return None
        else:
            return _find(x)


    def first_without(self, x):
        """Returns first found index not containing value (or list of values)"""

        def _find(x):
            try:
                for arg in self.all:
                    if x not in arg:
                        return self.all.index(arg)
            except ValueError:
                return None

        if is_collection(x):
            for item in x:
                found = _find(item)
                if found:
                    return found
            return None
        else:
            return _find(x)


    def start_with(self, x):
           """Returns all arguments beginning with given string (or list thereof)"""

           _args = []

           for arg in self.all:
               if is_collection(x):
                   for _x in x:
                       if arg.startswith(x):
                           _args.append(arg)
                           break
               else:
                   if arg.startswith(x):
                       _args.append(arg)

           return Args(_args, no_argv=True)


    def contains_at(self, x, index):
        """Tests if given [list of] string is at given index."""

        try:
            if is_collection(x):
                for _x in x:
                    if (_x in self.all[index]) or (_x == self.all[index]):
                        return True
                    else:
                        return False
            else:
                return (x in self.all[index])

        except IndexError:
            return False


    def has(self, x):
        """Returns true if argument exists at given index.
           Accepts: integer.
        """

        try:
            self.all[x]
            return True
        except IndexError:
            return False


    def value_after(self, x):
        """Returns value of argument after given found argument (or list thereof)."""

        try:
            try:
                i = self.all.index(x)
            except ValueError:
                return None

            return self.all[i + 1]

        except IndexError:
            return None


    @property
    def grouped(self):
        """Extracts --flag groups from argument list.
           Returns {format: Args, ...}
        """

        collection = OrderedDict(_=Args(no_argv=True))

        _current_group = None

        for arg in self.all:
            if arg.startswith('-'):
                _current_group = arg
                collection.setdefault(arg, Args(no_argv=True))
            else:
                if _current_group:
                    collection[_current_group]._args.append(arg)
                else:
                    collection['_']._args.append(arg)

        return collection


    @property
    def last(self):
        """Returns last argument."""

        try:
            return self.all[-1]
        except IndexError:
            return None


    @property
    def all(self):
        """Returns all arguments."""

        return self._args


    def all_with(self, x):
        """Returns all arguments containing given string (or list thereof)"""

        _args = []

        for arg in self.all:
            if is_collection(x):
                for _x in x:
                    if _x in arg:
                        _args.append(arg)
                        break
            else:
                if x in arg:
                    _args.append(arg)

        return Args(_args, no_argv=True)


    def all_without(self, x):
        """Returns all arguments not containing given string (or list thereof)"""

        _args = []

        for arg in self.all:
            if is_collection(x):
                for _x in x:
                    if _x not in arg:
                        _args.append(arg)
                        break
            else:
                if x not in arg:
                    _args.append(arg)

        return Args(_args, no_argv=True)


    @property
    def flags(self):
        """Returns Arg object including only flagged arguments."""

        return self.start_with('-')


    @property
    def not_flags(self):
        """Returns Arg object excluding flagged arguments."""

        return self.all_without('-')


    @property
    def files(self, absolute=False):
        """Returns an expanded list of all valid paths that were passed in."""

        _paths = []

        for arg in self.all:
            for path in expand_path(arg):
                if os.path.exists(path):
                    if absolute:
                        _paths.append(os.path.abspath(path))
                    else:
                        _paths.append(path)

        return _paths


    @property
    def not_files(self):
        """Returns a list of all arguments that aren't files/globs."""

        _args = []

        for arg in self.all:
            if not len(expand_path(arg)):
                if not os.path.exists(arg):
                    _args.append(arg)

        return Args(_args, no_argv=True)

    @property
    def copy(self):
        """Returns a copy of Args object for temporary manipulation."""

        return Args(self.all)


########NEW FILE########
__FILENAME__ = eng
# -*- coding: utf-8 -*-

"""
clint.eng
~~~~~~~~~

This module provides English language string helpers.

"""
from __future__ import print_function

MORON_MODE = False
COMMA = ','
CONJUNCTION = 'and'
SPACE = ' '

try:
    unicode
except NameError:
    unicode = str


def join(l, conj=CONJUNCTION, im_a_moron=MORON_MODE, seperator=COMMA):
    """Joins lists of words. Oxford comma and all."""

    collector = []
    left = len(l)
    seperator = seperator + SPACE
    conj = conj + SPACE

    for _l in l[:]:

        left += -1

        collector.append(_l)
        if left == 1:
            if len(l) == 2 or im_a_moron:
                collector.append(SPACE)
            else:
                collector.append(seperator)

            collector.append(conj)

        elif left is not 0:
            collector.append(seperator)

    return unicode(str().join(collector))

if __name__ == '__main__':
    print(join(['blue', 'red', 'yellow'], conj='or', im_a_moron=True))
    print(join(['blue', 'red', 'yellow'], conj='or'))
    print(join(['blue', 'red'], conj='or'))
    print(join(['blue', 'red'], conj='and'))
    print(join(['blue'], conj='and'))
    print(join(['blue', 'red', 'yellow', 'green', 'ello'], conj='and'))

########NEW FILE########
__FILENAME__ = appdirs
#!/usr/bin/env python
# Copyright (c) 2005-2010 ActiveState Software Inc.

"""Utilities for determining application-specific dirs.

See <http://github.com/ActiveState/appdirs> for details and usage.
"""
# Dev Notes:
# - MSDN on where to store app data files:
#   http://support.microsoft.com/default.aspx?scid=kb;en-us;310294#XSLTH3194121123120121120120
# - Mac OS X: http://developer.apple.com/documentation/MacOSX/Conceptual/BPFileSystem/index.html
# - XDG spec for Un*x: http://standards.freedesktop.org/basedir-spec/basedir-spec-latest.html

__version_info__ = (1, 2, 0)
__version__ = '.'.join(map(str, __version_info__))


import sys
import os

PY3 = sys.version_info[0] == 3

if PY3:
    unicode = str

class AppDirsError(Exception):
    pass



def user_data_dir(appname, appauthor=None, version=None, roaming=False):
    r"""Return full path to the user-specific data dir for this application.

        "appname" is the name of application.
        "appauthor" (only required and used on Windows) is the name of the
            appauthor or distributing body for this application. Typically
            it is the owning company name.
        "version" is an optional version path element to append to the
            path. You might want to use this if you want multiple versions
            of your app to be able to run independently. If used, this
            would typically be "<major>.<minor>".
        "roaming" (boolean, default False) can be set True to use the Windows
            roaming appdata directory. That means that for users on a Windows
            network setup for roaming profiles, this user data will be
            sync'd on login. See
            <http://technet.microsoft.com/en-us/library/cc766489(WS.10).aspx>
            for a discussion of issues.

    Typical user data directories are:
        Mac OS X:               ~/Library/Application Support/<AppName>
        Unix:                   ~/.config/<appname>    # or in $XDG_CONFIG_HOME if defined
        Win XP (not roaming):   C:\Documents and Settings\<username>\Application Data\<AppAuthor>\<AppName>
        Win XP (roaming):       C:\Documents and Settings\<username>\Local Settings\Application Data\<AppAuthor>\<AppName>
        Win 7  (not roaming):   C:\Users\<username>\AppData\Local\<AppAuthor>\<AppName>
        Win 7  (roaming):       C:\Users\<username>\AppData\Roaming\<AppAuthor>\<AppName>

    For Unix, we follow the XDG spec and support $XDG_CONFIG_HOME. We don't
    use $XDG_DATA_HOME as that data dir is mostly used at the time of
    installation, instead of the application adding data during runtime.
    Also, in practice, Linux apps tend to store their data in
    "~/.config/<appname>" instead of "~/.local/share/<appname>".
    """
    if sys.platform.startswith("win"):
        if appauthor is None:
            raise AppDirsError("must specify 'appauthor' on Windows")
        const = roaming and "CSIDL_APPDATA" or "CSIDL_LOCAL_APPDATA"
        path = os.path.join(_get_win_folder(const), appauthor, appname)
    elif sys.platform == 'darwin':
        path = os.path.join(
            os.path.expanduser('~/Library/Application Support/'),
            appname)
    else:
        path = os.path.join(
            os.getenv('XDG_CONFIG_HOME', os.path.expanduser("~/.config")),
            appname.lower())
    if version:
        path = os.path.join(path, version)
    return path


def site_data_dir(appname, appauthor=None, version=None):
    """Return full path to the user-shared data dir for this application.

        "appname" is the name of application.
        "appauthor" (only required and used on Windows) is the name of the
            appauthor or distributing body for this application. Typically
            it is the owning company name.
        "version" is an optional version path element to append to the
            path. You might want to use this if you want multiple versions
            of your app to be able to run independently. If used, this
            would typically be "<major>.<minor>".

    Typical user data directories are:
        Mac OS X:   /Library/Application Support/<AppName>
        Unix:       /etc/xdg/<appname>
        Win XP:     C:\Documents and Settings\All Users\Application Data\<AppAuthor>\<AppName>
        Vista:      (Fail! "C:\ProgramData" is a hidden *system* directory on Vista.)
        Win 7:      C:\ProgramData\<AppAuthor>\<AppName>   # Hidden, but writeable on Win 7.

    For Unix, this is using the $XDG_CONFIG_DIRS[0] default.

    WARNING: Do not use this on Windows. See the Vista-Fail note above for why.
    """
    if sys.platform.startswith("win"):
        if appauthor is None:
            raise AppDirsError("must specify 'appauthor' on Windows")
        path = os.path.join(_get_win_folder("CSIDL_COMMON_APPDATA"),
                            appauthor, appname)
    elif sys.platform == 'darwin':
        path = os.path.join(
            os.path.expanduser('/Library/Application Support'),
            appname)
    else:
        # XDG default for $XDG_CONFIG_DIRS[0]. Perhaps should actually
        # *use* that envvar, if defined.
        path = "/etc/xdg/"+appname.lower()
    if version:
        path = os.path.join(path, version)
    return path


def user_cache_dir(appname, appauthor=None, version=None, opinion=True):
    r"""Return full path to the user-specific cache dir for this application.

        "appname" is the name of application.
        "appauthor" (only required and used on Windows) is the name of the
            appauthor or distributing body for this application. Typically
            it is the owning company name.
        "version" is an optional version path element to append to the
            path. You might want to use this if you want multiple versions
            of your app to be able to run independently. If used, this
            would typically be "<major>.<minor>".
        "opinion" (boolean) can be False to disable the appending of
            "Cache" to the base app data dir for Windows. See
            discussion below.

    Typical user cache directories are:
        Mac OS X:   ~/Library/Caches/<AppName>
        Unix:       ~/.cache/<appname> (XDG default)
        Win XP:     C:\Documents and Settings\<username>\Local Settings\Application Data\<AppAuthor>\<AppName>\Cache
        Vista:      C:\Users\<username>\AppData\Local\<AppAuthor>\<AppName>\Cache

    On Windows the only suggestion in the MSDN docs is that local settings go in
    the `CSIDL_LOCAL_APPDATA` directory. This is identical to the non-roaming
    app data dir (the default returned by `user_data_dir` above). Apps typically
    put cache data somewhere *under* the given dir here. Some examples:
        ...\Mozilla\Firefox\Profiles\<ProfileName>\Cache
        ...\Acme\SuperApp\Cache\1.0
    OPINION: This function appends "Cache" to the `CSIDL_LOCAL_APPDATA` value.
    This can be disabled with the `opinion=False` option.
    """
    if sys.platform.startswith("win"):
        if appauthor is None:
            raise AppDirsError("must specify 'appauthor' on Windows")
        path = os.path.join(_get_win_folder("CSIDL_LOCAL_APPDATA"),
                            appauthor, appname)
        if opinion:
            path = os.path.join(path, "Cache")
    elif sys.platform == 'darwin':
        path = os.path.join(
            os.path.expanduser('~/Library/Caches'),
            appname)
    else:
        path = os.path.join(
            os.getenv('XDG_CACHE_HOME', os.path.expanduser('~/.cache')),
            appname.lower())
    if version:
        path = os.path.join(path, version)
    return path

def user_log_dir(appname, appauthor=None, version=None, opinion=True):
    r"""Return full path to the user-specific log dir for this application.

        "appname" is the name of application.
        "appauthor" (only required and used on Windows) is the name of the
            appauthor or distributing body for this application. Typically
            it is the owning company name.
        "version" is an optional version path element to append to the
            path. You might want to use this if you want multiple versions
            of your app to be able to run independently. If used, this
            would typically be "<major>.<minor>".
        "opinion" (boolean) can be False to disable the appending of
            "Logs" to the base app data dir for Windows, and "log" to the
            base cache dir for Unix. See discussion below.

    Typical user cache directories are:
        Mac OS X:   ~/Library/Logs/<AppName>
        Unix:       ~/.cache/<appname>/log  # or under $XDG_CACHE_HOME if defined
        Win XP:     C:\Documents and Settings\<username>\Local Settings\Application Data\<AppAuthor>\<AppName>\Logs
        Vista:      C:\Users\<username>\AppData\Local\<AppAuthor>\<AppName>\Logs

    On Windows the only suggestion in the MSDN docs is that local settings
    go in the `CSIDL_LOCAL_APPDATA` directory. (Note: I'm interested in
    examples of what some windows apps use for a logs dir.)

    OPINION: This function appends "Logs" to the `CSIDL_LOCAL_APPDATA`
    value for Windows and appends "log" to the user cache dir for Unix.
    This can be disabled with the `opinion=False` option.
    """
    if sys.platform == "darwin":
        path = os.path.join(
            os.path.expanduser('~/Library/Logs'),
            appname)
    elif sys.platform == "win32":
        path = user_data_dir(appname, appauthor, version); version=False
        if opinion:
            path = os.path.join(path, "Logs")
    else:
        path = user_cache_dir(appname, appauthor, version); version=False
        if opinion:
            path = os.path.join(path, "log")
    if version:
        path = os.path.join(path, version)
    return path


class AppDirs(object):
    """Convenience wrapper for getting application dirs."""
    def __init__(self, appname, appauthor, version=None, roaming=False):
        self.appname = appname
        self.appauthor = appauthor
        self.version = version
        self.roaming = roaming
    @property
    def user_data_dir(self):
        return user_data_dir(self.appname, self.appauthor,
            version=self.version, roaming=self.roaming)
    @property
    def site_data_dir(self):
        return site_data_dir(self.appname, self.appauthor,
            version=self.version)
    @property
    def user_cache_dir(self):
        return user_cache_dir(self.appname, self.appauthor,
            version=self.version)
    @property
    def user_log_dir(self):
        return user_log_dir(self.appname, self.appauthor,
            version=self.version)




#---- internal support stuff

def _get_win_folder_from_registry(csidl_name):
    """This is a fallback technique at best. I'm not sure if using the
    registry for this guarantees us the correct answer for all CSIDL_*
    names.
    """
    import _winreg

    shell_folder_name = {
        "CSIDL_APPDATA": "AppData",
        "CSIDL_COMMON_APPDATA": "Common AppData",
        "CSIDL_LOCAL_APPDATA": "Local AppData",
    }[csidl_name]

    key = _winreg.OpenKey(_winreg.HKEY_CURRENT_USER,
        r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders")
    dir, type = _winreg.QueryValueEx(key, shell_folder_name)
    return dir

def _get_win_folder_with_pywin32(csidl_name):
    from win32com.shell import shellcon, shell
    dir = shell.SHGetFolderPath(0, getattr(shellcon, csidl_name), 0, 0)
    # Try to make this a unicode path because SHGetFolderPath does
    # not return unicode strings when there is unicode data in the
    # path.
    try:
        dir = unicode(dir)

        # Downgrade to short path name if have highbit chars. See
        # <http://bugs.activestate.com/show_bug.cgi?id=85099>.
        has_high_char = False
        for c in dir:
            if ord(c) > 255:
                has_high_char = True
                break
        if has_high_char:
            try:
                import win32api
                dir = win32api.GetShortPathName(dir)
            except ImportError:
                pass
    except UnicodeError:
        pass
    return dir

def _get_win_folder_with_ctypes(csidl_name):
    import ctypes

    csidl_const = {
        "CSIDL_APPDATA": 26,
        "CSIDL_COMMON_APPDATA": 35,
        "CSIDL_LOCAL_APPDATA": 28,
    }[csidl_name]

    buf = ctypes.create_unicode_buffer(1024)
    ctypes.windll.shell32.SHGetFolderPathW(None, csidl_const, None, 0, buf)

    # Downgrade to short path name if have highbit chars. See
    # <http://bugs.activestate.com/show_bug.cgi?id=85099>.
    has_high_char = False
    for c in buf:
        if ord(c) > 255:
            has_high_char = True
            break
    if has_high_char:
        buf2 = ctypes.create_unicode_buffer(1024)
        if ctypes.windll.kernel32.GetShortPathNameW(buf.value, buf2, 1024):
            buf = buf2

    return buf.value

if sys.platform == "win32":
    try:
        import win32com.shell
        _get_win_folder = _get_win_folder_with_pywin32
    except ImportError:
        try:
            import ctypes
            _get_win_folder = _get_win_folder_with_ctypes
        except ImportError:
            _get_win_folder = _get_win_folder_from_registry



#---- self test code

if __name__ == "__main__":
    appname = "MyApp"
    appauthor = "MyCompany"

    props = ("user_data_dir", "site_data_dir", "user_cache_dir",
        "user_log_dir")

    print("-- app dirs (without optional 'version')")
    dirs = AppDirs(appname, appauthor, version="1.0")
    for prop in props:
        print("%s: %s" % (prop, getattr(dirs, prop)))

    print("\n-- app dirs (with optional 'version')")
    dirs = AppDirs(appname, appauthor)
    for prop in props:
        print("%s: %s" % (prop, getattr(dirs, prop)))

########NEW FILE########
__FILENAME__ = ansi
'''
This module generates ANSI character codes to printing colors to terminals.
See: http://en.wikipedia.org/wiki/ANSI_escape_code
'''

CSI = '\033['

def code_to_chars(code):
    return CSI + str(code) + 'm'

class AnsiCodes(object):
    def __init__(self, codes):
        for name in dir(codes):
            if not name.startswith('_'):
                value = getattr(codes, name)
                setattr(self, name, code_to_chars(value))

class AnsiFore:
    BLACK   = 30
    RED     = 31
    GREEN   = 32
    YELLOW  = 33
    BLUE    = 34
    MAGENTA = 35
    CYAN    = 36
    WHITE   = 37
    RESET   = 39

class AnsiBack:
    BLACK   = 40
    RED     = 41
    GREEN   = 42
    YELLOW  = 43
    BLUE    = 44
    MAGENTA = 45
    CYAN    = 46
    WHITE   = 47
    RESET   = 49

class AnsiStyle:
    BRIGHT    = 1
    DIM       = 2
    NORMAL    = 22
    RESET_ALL = 0

Fore = AnsiCodes( AnsiFore )
Back = AnsiCodes( AnsiBack )
Style = AnsiCodes( AnsiStyle )


########NEW FILE########
__FILENAME__ = ansitowin32

import re
import sys

from .ansi import AnsiFore, AnsiBack, AnsiStyle, Style
from .winterm import WinTerm, WinColor, WinStyle
from .win32 import windll


if windll is not None:
    winterm = WinTerm()


def is_a_tty(stream):
    return hasattr(stream, 'isatty') and stream.isatty()


class StreamWrapper(object):
    '''
    Wraps a stream (such as stdout), acting as a transparent proxy for all
    attribute access apart from method 'write()', which is delegated to our
    Converter instance.
    '''
    def __init__(self, wrapped, converter):
        # double-underscore everything to prevent clashes with names of
        # attributes on the wrapped stream object.
        self.__wrapped = wrapped
        self.__convertor = converter

    def __getattr__(self, name):
        return getattr(self.__wrapped, name)

    def write(self, text):
        self.__convertor.write(text)


class AnsiToWin32(object):
    '''
    Implements a 'write()' method which, on Windows, will strip ANSI character
    sequences from the text, and if outputting to a tty, will convert them into
    win32 function calls.
    '''
    ANSI_RE = re.compile('\033\[((?:\d|;)*)([a-zA-Z])')

    def __init__(self, wrapped, convert=None, strip=None, autoreset=False):
        # The wrapped stream (normally sys.stdout or sys.stderr)
        self.wrapped = wrapped

        # should we reset colors to defaults after every .write()
        self.autoreset = autoreset

        # create the proxy wrapping our output stream
        self.stream = StreamWrapper(wrapped, self)

        on_windows = sys.platform.startswith('win')

        # should we strip ANSI sequences from our output?
        if strip is None:
            strip = on_windows
        self.strip = strip

        # should we should convert ANSI sequences into win32 calls?
        if convert is None:
            convert = on_windows and is_a_tty(wrapped)
        self.convert = convert

        # dict of ansi codes to win32 functions and parameters
        self.win32_calls = self.get_win32_calls()

        # are we wrapping stderr?
        self.on_stderr = self.wrapped is sys.stderr


    def should_wrap(self):
        '''
        True if this class is actually needed. If false, then the output
        stream will not be affected, nor will win32 calls be issued, so
        wrapping stdout is not actually required. This will generally be
        False on non-Windows platforms, unless optional functionality like
        autoreset has been requested using kwargs to init()
        '''
        return self.convert or self.strip or self.autoreset


    def get_win32_calls(self):
        if self.convert and winterm:
            return {
                AnsiStyle.RESET_ALL: (winterm.reset_all, ),
                AnsiStyle.BRIGHT: (winterm.style, WinStyle.BRIGHT),
                AnsiStyle.DIM: (winterm.style, WinStyle.NORMAL),
                AnsiStyle.NORMAL: (winterm.style, WinStyle.NORMAL),
                AnsiFore.BLACK: (winterm.fore, WinColor.BLACK),
                AnsiFore.RED: (winterm.fore, WinColor.RED),
                AnsiFore.GREEN: (winterm.fore, WinColor.GREEN),
                AnsiFore.YELLOW: (winterm.fore, WinColor.YELLOW),
                AnsiFore.BLUE: (winterm.fore, WinColor.BLUE),
                AnsiFore.MAGENTA: (winterm.fore, WinColor.MAGENTA),
                AnsiFore.CYAN: (winterm.fore, WinColor.CYAN),
                AnsiFore.WHITE: (winterm.fore, WinColor.GREY),
                AnsiFore.RESET: (winterm.fore, ),
                AnsiBack.BLACK: (winterm.back, WinColor.BLACK),
                AnsiBack.RED: (winterm.back, WinColor.RED),
                AnsiBack.GREEN: (winterm.back, WinColor.GREEN),
                AnsiBack.YELLOW: (winterm.back, WinColor.YELLOW),
                AnsiBack.BLUE: (winterm.back, WinColor.BLUE),
                AnsiBack.MAGENTA: (winterm.back, WinColor.MAGENTA),
                AnsiBack.CYAN: (winterm.back, WinColor.CYAN),
                AnsiBack.WHITE: (winterm.back, WinColor.GREY),
                AnsiBack.RESET: (winterm.back, ),
            }


    def write(self, text):
        if self.strip or self.convert:
            self.write_and_convert(text)
        else:
            self.wrapped.write(text)
            self.wrapped.flush()
        if self.autoreset:
            self.reset_all()


    def reset_all(self):
        if self.convert:
            self.call_win32('m', (0,))
        elif is_a_tty(self.wrapped):
            self.wrapped.write(Style.RESET_ALL)


    def write_and_convert(self, text):
        '''
        Write the given text to our wrapped stream, stripping any ANSI
        sequences from the text, and optionally converting them into win32
        calls.
        '''
        cursor = 0
        for match in self.ANSI_RE.finditer(text):
            start, end = match.span()
            self.write_plain_text(text, cursor, start)
            self.convert_ansi(*match.groups())
            cursor = end
        self.write_plain_text(text, cursor, len(text))


    def write_plain_text(self, text, start, end):
        if start < end:
            self.wrapped.write(text[start:end])
            self.wrapped.flush()


    def convert_ansi(self, paramstring, command):
        if self.convert:
            params = self.extract_params(paramstring)
            self.call_win32(command, params)


    def extract_params(self, paramstring):
        def split(paramstring):
            for p in paramstring.split(';'):
                if p != '':
                    yield int(p)
        return tuple(split(paramstring))


    def call_win32(self, command, params):
        if params == []:
            params = [0]
        if command == 'm':
            for param in params:
                if param in self.win32_calls:
                    func_args = self.win32_calls[param]
                    func = func_args[0]
                    args = func_args[1:]
                    kwargs = dict(on_stderr=self.on_stderr)
                    func(*args, **kwargs)
        elif command in ('H', 'f'): # set cursor position
            func = winterm.set_cursor_position
            func(params, on_stderr=self.on_stderr)
        elif command in ('J'):
            func = winterm.erase_data
            func(params, on_stderr=self.on_stderr)


########NEW FILE########
__FILENAME__ = initialise
import atexit
import sys

from .ansitowin32 import AnsiToWin32


orig_stdout = sys.stdout
orig_stderr = sys.stderr

wrapped_stdout = sys.stdout
wrapped_stderr = sys.stderr

atexit_done = False


def reset_all():
    AnsiToWin32(orig_stdout).reset_all()


def init(autoreset=False, convert=None, strip=None, wrap=True):

    if not wrap and any([autoreset, convert, strip]):
        raise ValueError('wrap=False conflicts with any other arg=True')

    global wrapped_stdout, wrapped_stderr
    sys.stdout = wrapped_stdout = \
        wrap_stream(orig_stdout, convert, strip, autoreset, wrap)
    sys.stderr = wrapped_stderr = \
        wrap_stream(orig_stderr, convert, strip, autoreset, wrap)

    global atexit_done
    if not atexit_done:
        atexit.register(reset_all)
        atexit_done = True


def deinit():
    sys.stdout = orig_stdout
    sys.stderr = orig_stderr


def reinit():
    sys.stdout = wrapped_stdout
    sys.stderr = wrapped_stdout


def wrap_stream(stream, convert, strip, autoreset, wrap):
    if wrap:
        wrapper = AnsiToWin32(stream,
            convert=convert, strip=strip, autoreset=autoreset)
        if wrapper.should_wrap():
            stream = wrapper.stream
    return stream



########NEW FILE########
__FILENAME__ = win32

# from winbase.h
STDOUT = -11
STDERR = -12

try:
    from ctypes import windll
except ImportError:
    windll = None
    SetConsoleTextAttribute = lambda *_: None
else:
    from ctypes import (
        byref, Structure, c_char, c_short, c_uint32, c_ushort
    )

    handles = {
        STDOUT: windll.kernel32.GetStdHandle(STDOUT),
        STDERR: windll.kernel32.GetStdHandle(STDERR),
    }

    SHORT = c_short
    WORD = c_ushort
    DWORD = c_uint32
    TCHAR = c_char

    class COORD(Structure):
        """struct in wincon.h"""
        _fields_ = [
            ('X', SHORT),
            ('Y', SHORT),
        ]

    class  SMALL_RECT(Structure):
        """struct in wincon.h."""
        _fields_ = [
            ("Left", SHORT),
            ("Top", SHORT),
            ("Right", SHORT),
            ("Bottom", SHORT),
        ]

    class CONSOLE_SCREEN_BUFFER_INFO(Structure):
        """struct in wincon.h."""
        _fields_ = [
            ("dwSize", COORD),
            ("dwCursorPosition", COORD),
            ("wAttributes", WORD),
            ("srWindow", SMALL_RECT),
            ("dwMaximumWindowSize", COORD),
        ]
        def __str__(self):
            return '(%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d)' % (
                self.dwSize.Y, self.dwSize.X
                , self.dwCursorPosition.Y, self.dwCursorPosition.X
                , self.wAttributes
                , self.srWindow.Top, self.srWindow.Left, self.srWindow.Bottom, self.srWindow.Right
                , self.dwMaximumWindowSize.Y, self.dwMaximumWindowSize.X
            )

    def GetConsoleScreenBufferInfo(stream_id=STDOUT):
        handle = handles[stream_id]
        csbi = CONSOLE_SCREEN_BUFFER_INFO()
        success = windll.kernel32.GetConsoleScreenBufferInfo(
            handle, byref(csbi))
        # This fails when imported via setup.py when installing using 'pip'
        # presumably the fix is that running setup.py should not trigger all
        # this activity.
        # assert success
        return csbi

    def SetConsoleTextAttribute(stream_id, attrs):
        handle = handles[stream_id]
        return windll.kernel32.SetConsoleTextAttribute(handle, attrs)

    def SetConsoleCursorPosition(stream_id, position):
        position = COORD(*position)
        # If the position is out of range, do nothing.
        if position.Y <= 0 or position.X <= 0: 
            return
        # Adjust for Windows' SetConsoleCursorPosition:
        #    1. being 0-based, while ANSI is 1-based.
        #    2. expecting (x,y), while ANSI uses (y,x).
        adjusted_position = COORD(position.Y - 1, position.X - 1)
        # Adjust for viewport's scroll position
        sr = GetConsoleScreenBufferInfo(STDOUT).srWindow
        adjusted_position.Y += sr.Top
        adjusted_position.X += sr.Left
        # Resume normal processing
        handle = handles[stream_id]
        success = windll.kernel32.SetConsoleCursorPosition(handle, adjusted_position)
        return success

    def FillConsoleOutputCharacter(stream_id, char, length, start):
        handle = handles[stream_id]
        char = TCHAR(char)
        length = DWORD(length)
        num_written = DWORD(0)
        # Note that this is hard-coded for ANSI (vs wide) bytes.
        success = windll.kernel32.FillConsoleOutputCharacterA(
            handle, char, length, start, byref(num_written))
        return num_written.value

    def FillConsoleOutputAttribute(stream_id, attr, length, start):
        ''' FillConsoleOutputAttribute( hConsole, csbi.wAttributes, dwConSize, coordScreen, &cCharsWritten )'''
        handle = handles[stream_id]
        attribute = WORD(attr)
        length = DWORD(length)
        num_written = DWORD(0)
        # Note that this is hard-coded for ANSI (vs wide) bytes.
        success = windll.kernel32.FillConsoleOutputAttribute(
            handle, attribute, length, start, byref(num_written))
        return success


if __name__=='__main__':
    x = GetConsoleScreenBufferInfo(STDOUT)
    print(x)
    print('dwSize(height,width)                    = (%d,%d)' % (x.dwSize.Y, x.dwSize.X))
    print('dwCursorPosition(y,x)                   = (%d,%d)' % (x.dwCursorPosition.Y, x.dwCursorPosition.X))
    print('wAttributes(color)                      =  %d = 0x%02x' % (x.wAttributes, x.wAttributes))
    print('srWindow(Top,Left)-(Bottom,Right)       = (%d,%d)-(%d,%d)' % (x.srWindow.Top, x.srWindow.Left, x.srWindow.Bottom, x.srWindow.Right))
    print('dwMaximumWindowSize(maxHeight,maxWidth) = (%d,%d)' % (x.dwMaximumWindowSize.Y, x.dwMaximumWindowSize.X))


########NEW FILE########
__FILENAME__ = winterm

from . import win32


# from wincon.h
class WinColor(object):
    BLACK   = 0
    BLUE    = 1
    GREEN   = 2
    CYAN    = 3
    RED     = 4
    MAGENTA = 5
    YELLOW  = 6
    GREY    = 7

# from wincon.h
class WinStyle(object):
    NORMAL = 0x00 # dim text, dim background
    BRIGHT = 0x08 # bright text, dim background


class WinTerm(object):

    def __init__(self):
        self._default = win32.GetConsoleScreenBufferInfo(win32.STDOUT).wAttributes
        self.set_attrs(self._default)
        self._default_fore = self._fore
        self._default_back = self._back
        self._default_style = self._style

    def get_attrs(self):
        return self._fore + self._back * 16 + self._style

    def set_attrs(self, value):
        self._fore = value & 7
        self._back = (value >> 4) & 7
        self._style = value & WinStyle.BRIGHT

    def reset_all(self, on_stderr=None):
        self.set_attrs(self._default)
        self.set_console(attrs=self._default)

    def fore(self, fore=None, on_stderr=False):
        if fore is None:
            fore = self._default_fore
        self._fore = fore
        self.set_console(on_stderr=on_stderr)

    def back(self, back=None, on_stderr=False):
        if back is None:
            back = self._default_back
        self._back = back
        self.set_console(on_stderr=on_stderr)

    def style(self, style=None, on_stderr=False):
        if style is None:
            style = self._default_style
        self._style = style
        self.set_console(on_stderr=on_stderr)

    def set_console(self, attrs=None, on_stderr=False):
        if attrs is None:
            attrs = self.get_attrs()
        handle = win32.STDOUT
        if on_stderr:
            handle = win32.STDERR
        win32.SetConsoleTextAttribute(handle, attrs)

    def set_cursor_position(self, position=None, on_stderr=False):
        if position is None:
            #I'm not currently tracking the position, so there is no default.
            #position = self.get_position()
            return
        handle = win32.STDOUT
        if on_stderr:
            handle = win32.STDERR
        win32.SetConsoleCursorPosition(handle, position)

    def erase_data(self, mode=0, on_stderr=False):
        # 0 (or None) should clear from the cursor to the end of the screen.
        # 1 should clear from the cursor to the beginning of the screen.
        # 2 should clear the entire screen. (And maybe move cursor to (1,1)?)
        #
        # At the moment, I only support mode 2. From looking at the API, it 
        #    should be possible to calculate a different number of bytes to clear, 
        #    and to do so relative to the cursor position.
        if mode[0] not in (2,):
            return
        handle = win32.STDOUT
        if on_stderr:
            handle = win32.STDERR
        # here's where we'll home the cursor
        coord_screen = win32.COORD(0,0) 
        csbi = win32.GetConsoleScreenBufferInfo(handle)
        # get the number of character cells in the current buffer
        dw_con_size = csbi.dwSize.X * csbi.dwSize.Y
        # fill the entire screen with blanks
        win32.FillConsoleOutputCharacter(handle, ord(' '), dw_con_size, coord_screen)
        # now set the buffer's attributes accordingly
        win32.FillConsoleOutputAttribute(handle, self.get_attrs(), dw_con_size, coord_screen );
        # put the cursor at (0, 0)
        win32.SetConsoleCursorPosition(handle, (coord_screen.X, coord_screen.Y))

########NEW FILE########
__FILENAME__ = ordereddict
# Copyright (c) 2009 Raymond Hettinger
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation files
# (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge,
# publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
#     The above copyright notice and this permission notice shall be
#     included in all copies or substantial portions of the Software.
#
#     THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
#     EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
#     OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
#     NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
#     HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
#     WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
#     FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
#     OTHER DEALINGS IN THE SOFTWARE.

from UserDict import DictMixin

class OrderedDict(dict, DictMixin):

    def __init__(self, *args, **kwds):
        if len(args) > 1:
            raise TypeError('expected at most 1 arguments, got %d' % len(args))
        try:
            self.__end
        except AttributeError:
            self.clear()
        self.update(*args, **kwds)

    def clear(self):
        self.__end = end = []
        end += [None, end, end]         # sentinel node for doubly linked list
        self.__map = {}                 # key --> [key, prev, next]
        dict.clear(self)

    def __setitem__(self, key, value):
        if key not in self:
            end = self.__end
            curr = end[1]
            curr[2] = end[1] = self.__map[key] = [key, curr, end]
        dict.__setitem__(self, key, value)

    def __delitem__(self, key):
        dict.__delitem__(self, key)
        key, prev, next = self.__map.pop(key)
        prev[2] = next
        next[1] = prev

    def __iter__(self):
        end = self.__end
        curr = end[2]
        while curr is not end:
            yield curr[0]
            curr = curr[2]

    def __reversed__(self):
        end = self.__end
        curr = end[1]
        while curr is not end:
            yield curr[0]
            curr = curr[1]

    def popitem(self, last=True):
        if not self:
            raise KeyError('dictionary is empty')
        if last:
            key = reversed(self).next()
        else:
            key = iter(self).next()
        value = self.pop(key)
        return key, value

    def __reduce__(self):
        items = [[k, self[k]] for k in self]
        tmp = self.__map, self.__end
        del self.__map, self.__end
        inst_dict = vars(self).copy()
        self.__map, self.__end = tmp
        if inst_dict:
            return (self.__class__, (items,), inst_dict)
        return self.__class__, (items,)

    def keys(self):
        return list(self)

    setdefault = DictMixin.setdefault
    update = DictMixin.update
    pop = DictMixin.pop
    values = DictMixin.values
    items = DictMixin.items
    iterkeys = DictMixin.iterkeys
    itervalues = DictMixin.itervalues
    iteritems = DictMixin.iteritems

    def __repr__(self):
        if not self:
            return '%s()' % (self.__class__.__name__,)
        return '%s(%r)' % (self.__class__.__name__, self.items())

    def copy(self):
        return self.__class__(self)

    @classmethod
    def fromkeys(cls, iterable, value=None):
        d = cls()
        for key in iterable:
            d[key] = value
        return d

    def __eq__(self, other):
        if isinstance(other, OrderedDict):
            if len(self) != len(other):
                return False
            for p, q in  zip(self.items(), other.items()):
                if p != q:
                    return False
            return True
        return dict.__eq__(self, other)

    def __ne__(self, other):
        return not self == other

########NEW FILE########
__FILENAME__ = pipes
# -*- coding: utf-8 -*-

"""
clint.pipes
~~~~~~~~~~~

This module contains the helper functions for dealing with unix pipes.

"""

from __future__ import absolute_import
from __future__ import with_statement

import sys


__all__ = ('piped_in', )



def piped_in():
    """Returns piped input via stdin, else None."""
    with sys.stdin as stdin:
        # TTY is only way to detect if stdin contains data
        if not stdin.isatty():
            return stdin.read()  
        else:
            return None

########NEW FILE########
__FILENAME__ = resources
# -*- coding: utf-8 -*-

"""
clint.resources
~~~~~~~~~~~~~~~

This module contains all the application resource features of clint.

"""


from __future__ import absolute_import
from __future__ import with_statement

import errno
from os import remove, removedirs
from os.path import isfile, join as path_join

from .packages.appdirs import AppDirs, AppDirsError
from .utils import mkdir_p, is_collection


__all__ = (
    'init', 'user', 'site', 'cache',
    'log', 'NotConfigured'
)


class AppDir(object):
    """Application Directory object."""

    def __init__(self, path=None):
        self.path = path
        self._exists = False

        if path:
            self._create()


    def __repr__(self):
        return '<app-dir: %s>' % (self.path)


    def __getattribute__(self, name):

        if not name in ('_exists', 'path', '_create', '_raise_if_none'):
            if not self._exists:
                self._create()
        return object.__getattribute__(self, name)


    def _raise_if_none(self):
        """Raises if operations are carried out on an unconfigured AppDir."""
        if not self.path:
            raise NotConfigured()


    def _create(self):
        """Creates current AppDir at AppDir.path."""

        self._raise_if_none()
        if not self._exists:
            mkdir_p(self.path)
            self._exists = True


    def open(self, filename, mode='r'):
        """Returns file object from given filename."""

        self._raise_if_none()
        fn = path_join(self.path, filename)

        return open(fn, mode)


    def write(self, filename, content, binary=False):
        """Writes given content to given filename."""
        self._raise_if_none()
        fn = path_join(self.path, filename)

        if binary:
            flags = 'wb'
        else:
            flags = 'w'


        with open(fn, flags) as f:
            f.write(content)


    def append(self, filename, content, binary=False):
        """Appends given content to given filename."""

        self._raise_if_none()
        fn = path_join(self.path, filename)

        if binary:
            flags = 'ab'
        else:
            flags = 'a'

        with open(fn, 'a') as f:
            f.write(content)
            return True

    def delete(self, filename=''):
        """Deletes given file or directory. If no filename is passed, current
        directory is removed.
        """
        self._raise_if_none()
        fn = path_join(self.path, filename)

        try:
            if isfile(fn):
                remove(fn)
            else:
                removedirs(fn)
        except OSError as why:
            if why.errno == errno.ENOENT:
                pass
            else:
                raise why


    def read(self, filename, binary=False):
        """Returns contents of given file with AppDir.
        If file doesn't exist, returns None."""

        self._raise_if_none()
        fn = path_join(self.path, filename)

        if binary:
            flags = 'br'
        else:
            flags = 'r'

        try:
            with open(fn, flags) as f:
                return f.read()
        except IOError:
            return None


    def sub(self, path):
        """Returns AppDir instance for given subdirectory name."""

        if is_collection(path):
            path = path_join(path)

        return AppDir(path_join(self.path, path))


# Module locals

user = AppDir()
site = AppDir()
cache = AppDir()
log = AppDir()


def init(vendor, name):

    global user, site, cache, log

    ad = AppDirs(name, vendor)

    user.path = ad.user_data_dir

    site.path = ad.site_data_dir
    cache.path = ad.user_cache_dir
    log.path = ad.user_log_dir


class NotConfigured(IOError):
    """Application configuration required. Please run resources.init() first."""

########NEW FILE########
__FILENAME__ = colored
# -*- coding: utf-8 -*-

"""
clint.colored
~~~~~~~~~~~~~

This module provides a simple and elegant wrapper for colorama.

"""


from __future__ import absolute_import

import re
import sys

PY3 = sys.version_info[0] >= 3

from ..packages import colorama

__all__ = (
    'red', 'green', 'yellow', 'blue',
    'black', 'magenta', 'cyan', 'white',
    'clean', 'disable'
)

COLORS = __all__[:-2]

if 'get_ipython' in dir():
    """
       when ipython is fired lot of variables like _oh, etc are used.
       There are so many ways to find current python interpreter is ipython.
       get_ipython is easiest is most appealing for readers to understand.
    """
    DISABLE_COLOR = True
else:
    DISABLE_COLOR = False



class ColoredString(object):
    """Enhanced string for __len__ operations on Colored output."""
    def __init__(self, color, s):
        super(ColoredString, self).__init__()
        self.s = s
        self.color = color

    @property
    def color_str(self):
        if sys.stdout.isatty() and not DISABLE_COLOR:
            return '%s%s%s' % (
                getattr(colorama.Fore, self.color), self.s, colorama.Fore.RESET)
        else:
            return self.s


    def __len__(self):
        return len(self.s)

    def __repr__(self):
        return "<%s-string: '%s'>" % (self.color, self.s)

    def __unicode__(self):
        value = self.color_str
        if isinstance(value, bytes):
            return value.decode('utf8')
        return value

    if PY3:
        __str__ = __unicode__
    else:
        def __str__(self):
            return unicode(self).encode('utf8')

    def __iter__(self):
        return iter(self.color_str)

    def __add__(self, other):
        return str(self.color_str) + str(other)

    def __radd__(self, other):
        return str(other) + str(self.color_str)

    def __mul__(self, other):
        return (self.color_str * other)

    def split(self, sep=None):
        return [self._new(s) for s in self.s.split(sep)]

    def _new(self, s):
        return ColoredString(self.color, s)


def clean(s):
    strip = re.compile("([^-_a-zA-Z0-9!@#%&=,/'\";:~`\$\^\*\(\)\+\[\]\.\{\}\|\?\<\>\\]+|[^\s]+)")
    txt = strip.sub('', str(s))

    strip = re.compile(r'\[\d+m')
    txt = strip.sub('', txt)

    return txt


def black(string):
    return ColoredString('BLACK', string)

def red(string):
    return ColoredString('RED', string)

def green(string):
    return ColoredString('GREEN', string)

def yellow(string):
    return ColoredString('YELLOW', string)

def blue(string):
    return ColoredString('BLUE', string)

def magenta(string):
    return ColoredString('MAGENTA', string)

def cyan(string):
    return ColoredString('CYAN', string)

def white(string):
    return ColoredString('WHITE', string)

def disable():
    """Disables colors."""
    global DISABLE_COLOR

    DISABLE_COLOR = True

########NEW FILE########
__FILENAME__ = cols
# -*- coding: utf-8 -*-

"""
clint.textui.columns
~~~~~~~~~~~~~~~~~~~~

Core TextUI functionality for column formatting.

"""

from __future__ import absolute_import

from .formatters import max_width, min_width
from ..utils import tsplit

import sys


NEWLINES = ('\n', '\r', '\r\n')



def _find_unix_console_width():
    import termios, fcntl, struct, sys

    # fcntl.ioctl will fail if stdout is not a tty
    if not sys.stdout.isatty():
        return None

    s = struct.pack("HHHH", 0, 0, 0, 0)
    fd_stdout = sys.stdout.fileno()
    size = fcntl.ioctl(fd_stdout, termios.TIOCGWINSZ, s)
    height, width = struct.unpack("HHHH", size)[:2]
    return width


def _find_windows_console_width():
    # http://code.activestate.com/recipes/440694/
    from ctypes import windll, create_string_buffer
    STDIN, STDOUT, STDERR = -10, -11, -12

    h = windll.kernel32.GetStdHandle(STDERR)
    csbi = create_string_buffer(22)
    res = windll.kernel32.GetConsoleScreenBufferInfo(h, csbi)

    if res:
        import struct
        (bufx, bufy, curx, cury, wattr,
         left, top, right, bottom,
         maxx, maxy) = struct.unpack("hhhhHhhhhhh", csbi.raw)
        sizex = right - left + 1
        sizey = bottom - top + 1
        return sizex


def console_width(kwargs):
    """"Determine console_width."""

    if sys.platform.startswith('win'):
        console_width = _find_windows_console_width()
    else:
        console_width = _find_unix_console_width()

    _width = kwargs.get('width', None)
    if _width:
        console_width = _width
    else:
        if not console_width:
            console_width = 80

    return console_width



def columns(*cols, **kwargs):

    columns = list(cols)

    cwidth = console_width(kwargs)

    _big_col = None
    _total_cols = 0


    for i, (string, width) in enumerate(cols):

        if width is not None:
            _total_cols += (width + 1)
            cols[i][0] = max_width(string, width).split('\n')
        else:
            _big_col = i

    if _big_col:
        cols[_big_col][1] = (cwidth - _total_cols) - len(cols)
        cols[_big_col][0] = max_width(cols[_big_col][0], cols[_big_col][1]).split('\n')

    height = len(max([c[0] for c in cols], key=len))
    
    for i, (strings, width) in enumerate(cols):

        for _ in range(height - len(strings)):
            cols[i][0].append('')

        for j, string in enumerate(strings):
            cols[i][0][j] = min_width(string, width)

    stack =  [c[0] for c in cols]
    _out = []

    for i in range(height):
        _row = ''

        for col in stack:
            _row += col[i]
            _row += ' '

        _out.append(_row)
#            try:
#                pass
#            except:
#                pass




    return '\n'.join(_out)


#        string = max_width(string, width)
#        string = min_width(string, width)
#        pass
#        columns.append()



###########################

a = 'this is text that goes into a small column\n cool?'
b = 'this is other text\nothertext\nothertext'

#columns((a, 10), (b, 20), (b, None))

########NEW FILE########
__FILENAME__ = core
# -*- coding: utf-8 -*-

"""
clint.textui.core
~~~~~~~~~~~~~~~~~

Core TextUI functionality for Puts/Indent/Writer.

"""


from __future__ import absolute_import

import sys

from contextlib import contextmanager

from .formatters import max_width, min_width
from .cols import columns
from ..utils import tsplit


__all__ = ('puts', 'puts_err', 'indent', 'dedent', 'columns', 'max_width',
    'min_width')


STDOUT = sys.stdout.write
STDERR = sys.stderr.write

NEWLINES = ('\n', '\r', '\r\n')

INDENT_STRINGS = []

# Private

def _indent(indent=0, quote='', indent_char=' '):
    """Indent util function, compute new indent_string"""
    if indent > 0:
        indent_string = ''.join((
            str(quote),
            (indent_char * (indent - len(quote)))
        ))
    else:
        indent_string = ''.join((
            ('\x08' * (-1 * (indent - len(quote)))),
            str(quote))
        )

    if len(indent_string):
        INDENT_STRINGS.append(indent_string)

# Public

def puts(s='', newline=True, stream=STDOUT):
    """Prints given string to stdout."""
    if newline:
        s = tsplit(s, NEWLINES)
        s = map(str, s)
        indent = ''.join(INDENT_STRINGS)

        s = (str('\n' + indent)).join(s)

    _str = ''.join((
        ''.join(INDENT_STRINGS),
        str(s),
        '\n' if newline else ''
    ))
    stream(_str)

def puts_err(s='', newline=True, stream=STDERR):
    """Prints given string to stderr."""
    puts(s, newline, stream)

def dedent():
    """Dedent next strings, use only if you use indent otherwise than as a
    context."""
    INDENT_STRINGS.pop()

@contextmanager
def _indent_context():
    """Indentation context manager."""
    yield
    dedent()

def indent(indent=4, quote=''):
    """Indentation manager, return an indentation context manager."""
    _indent(indent, quote)
    return _indent_context()

########NEW FILE########
__FILENAME__ = formatters
# -*- coding: utf-8 -*-

"""
clint.textui.formatters
~~~~~~~~~~~~~~~~~~~~~~~

Core TextUI functionality for text formatting.

"""

from __future__ import absolute_import

from .colored import ColoredString, clean
from ..utils import tsplit, schunk


NEWLINES = ('\n', '\r', '\r\n')


def min_width(string, cols, padding=' '):
    """Returns given string with right padding."""

    is_color = isinstance(string, ColoredString)

    stack = tsplit(str(string), NEWLINES)

    for i, substring in enumerate(stack):
        _sub = clean(substring).ljust((cols + 0), padding)
        if is_color:
            _sub = (_sub.replace(clean(substring), substring))
        stack[i] = _sub
        
    return '\n'.join(stack)


def max_width(string, cols, separator='\n'):
    """Returns a freshly formatted """

    is_color = isinstance(string, ColoredString)

    if is_color:
        offset = 10
        string_copy = string._new('')
    else:
        offset = 0
        
    stack = tsplit(string, NEWLINES)

    for i, substring in enumerate(stack):
        stack[i] = substring.split()

    _stack = []
    
    for row in stack:
        _row = ['',]
        _row_i = 0

        for word in row:
            if (len(_row[_row_i]) + len(word)) < (cols + offset):
                _row[_row_i] += word
                _row[_row_i] += ' '
                
            elif len(word) > (cols - offset):

                # ensure empty row
                if len(_row[_row_i]):
                    _row.append('')
                    _row_i += 1

                chunks = schunk(word, (cols + offset))
                for i, chunk in enumerate(chunks):
                    if not (i + 1) == len(chunks):
                        _row[_row_i] += chunk
                        _row.append('')
                        _row_i += 1
                    else:
                        _row[_row_i] += chunk
                        _row[_row_i] += ' '
            else:
                _row.append('')
                _row_i += 1
                _row[_row_i] += word
                _row[_row_i] += ' '

        _row = map(str, _row)
        _stack.append(separator.join(_row))

    _s = '\n'.join(_stack)
    if is_color:
        _s = string_copy._new(_s)
    return _s

########NEW FILE########
__FILENAME__ = progress
# -*- coding: utf-8 -*-

"""
clint.textui.progress
~~~~~~~~~~~~~~~~~

This module provides the progressbar functionality.

"""

from __future__ import absolute_import

import sys
import time

STREAM = sys.stderr

BAR_TEMPLATE = '%s[%s%s] %i/%i - %s\r'
MILL_TEMPLATE = '%s %s %i/%i\r'  

DOTS_CHAR = '.'
BAR_FILLED_CHAR = '#'
BAR_EMPTY_CHAR = ' '
MILL_CHARS = ['|', '/', '-', '\\']

#How long to wait before recalculating the ETA
ETA_INTERVAL = 1
#How many intervals (excluding the current one) to calculate the simple moving average
ETA_SMA_WINDOW = 9

def bar(it, label='', width=32, hide=False, empty_char=BAR_EMPTY_CHAR, filled_char=BAR_FILLED_CHAR, expected_size=None):
    """Progress iterator. Wrap your iterables with it."""

    def _show(_i):
        if (time.time() - bar.etadelta) > ETA_INTERVAL:
            bar.etadelta = time.time()
            bar.ittimes = bar.ittimes[-ETA_SMA_WINDOW:]+[-(bar.start-time.time())/(_i+1)]
            bar.eta = sum(bar.ittimes)/float(len(bar.ittimes)) * (count-_i)
            bar.etadisp = time.strftime('%H:%M:%S', time.gmtime(bar.eta))
        x = int(width*_i/count)
        if not hide:
            STREAM.write(BAR_TEMPLATE % (
            label, filled_char*x, empty_char*(width-x), _i, count, bar.etadisp))
            STREAM.flush()

    count = len(it) if expected_size is None else expected_size

    bar.start    = time.time()
    bar.ittimes  = []
    bar.eta      = 0
    bar.etadelta = time.time()
    bar.etadisp  = time.strftime('%H:%M:%S', time.gmtime(bar.eta))

    if count:
        _show(0)

    for i, item in enumerate(it):

        yield item
        _show(i+1)

    if not hide:
        STREAM.write('\n')
        STREAM.flush()


def dots(it, label='', hide=False):
    """Progress iterator. Prints a dot for each item being iterated"""

    count = 0

    if not hide:
        STREAM.write(label)

    for item in it:
        if not hide:
            STREAM.write(DOTS_CHAR)
            sys.stderr.flush()

        count += 1

        yield item

    STREAM.write('\n')
    STREAM.flush()


def mill(it, label='', hide=False, expected_size=None):
    """Progress iterator. Prints a mill while iterating over the items."""

    def _mill_char(_i):
        if _i == 100:
            return ' '
        else:
            return MILL_CHARS[_i % len(MILL_CHARS)]

    def _show(_i):
        if not hide:
            STREAM.write(MILL_TEMPLATE % (
                label, _mill_char(_i), _i, count))
            STREAM.flush()

    count = len(it) if expected_size is None else expected_size

    if count:
        _show(0)

    for i, item in enumerate(it):

        yield item
        _show(i+1)

    if not hide:
        STREAM.write('\n')
        STREAM.flush()

########NEW FILE########
__FILENAME__ = prompt
# -*- coding: utf8 -*-

"""
clint.textui.prompt
~~~~~~~~~~~~~~~~~~~

Module for simple interactive prompts handling

"""

from __future__ import absolute_import

from re import match, I

def yn(prompt, default='y', batch=False):
    # A sanity check against default value
    # If not y/n then y is assumed 
    if default not in ['y', 'n']:
        default = 'y'
    
    # Let's build the prompt
    choicebox = '[Y/n]' if default == 'y' else '[y/N]' 
    prompt = prompt + ' ' + choicebox + ' ' 

    # If input is not a yes/no variant or empty
    # keep asking
    while True:
        # If batch option is True then auto reply 
        # with default input
        if not batch:
            input = raw_input(prompt).strip()
        else:
            print prompt
            input = ''

        # If input is empty default choice is assumed
        # so we return True
        if input == '':
            return True

        # Given 'yes' as input if default choice is y
        # then return True, False otherwise 
        if match('y(?:es)?', input, I):
            return True if default == 'y' else False

        # Given 'no' as input if default choice is n
        # then return True, False otherwise
        elif match('n(?:o)?', input, I):
            return True if default == 'n' else False

########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-

"""
clint.utils
~~~~~~~~~~~~

Various Python helpers used within clint.

"""

from __future__ import absolute_import
from __future__ import with_statement

import errno
import os.path
from os import makedirs
from glob import glob

try:
    basestring
except NameError:
    basestring = str

def expand_path(path):
    """Expands directories and globs in given path."""

    paths = []
    path = os.path.expanduser(path)
    path = os.path.expandvars(path)

    if os.path.isdir(path):

        for (dir, dirs, files) in os.walk(path):
            for file in files:
                paths.append(os.path.join(dir, file))
    else:
        paths.extend(glob(path))

    return paths



def is_collection(obj):
    """Tests if an object is a collection. Strings don't count."""

    if isinstance(obj, basestring):
        return False

    return hasattr(obj, '__getitem__')


def mkdir_p(path):
    """Emulates `mkdir -p` behavior."""
    try:
        makedirs(path)
    except OSError as exc: # Python >2.5
        if exc.errno == errno.EEXIST:
            pass
        else:
            raise

def tsplit(string, delimiters):
    """Behaves str.split but supports tuples of delimiters."""

    delimiters = tuple(delimiters)
    stack = [string,]

    for delimiter in delimiters:
        for i, substring in enumerate(stack):
            substack = substring.split(delimiter)
            stack.pop(i)
            for j, _substring in enumerate(substack):
                stack.insert(i+j, _substring)

    return stack

def schunk(string, size):
    """Splits string into n sized chunks."""

    stack = []

    substack = []
    current_count = 0

    for char in string:
        if not current_count < size:
            stack.append(''.join(substack))
            substack = []
            current_count = 0

        substack.append(char)
        current_count += 1

    if len(substack):
        stack.append(''.join(substack))

    return stack

########NEW FILE########
__FILENAME__ = version
__version__ = '0.0.1'
########NEW FILE########
