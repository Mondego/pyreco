__FILENAME__ = appdirs
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2005-2010 ActiveState Software Inc.
# Copyright (c) 2013 Eddy Petrișor

"""Utilities for determining application-specific dirs.

See <http://github.com/ActiveState/appdirs> for details and usage.
"""
# Dev Notes:
# - MSDN on where to store app data files:
#   http://support.microsoft.com/default.aspx?scid=kb;en-us;310294#XSLTH3194121123120121120120
# - Mac OS X: http://developer.apple.com/documentation/MacOSX/Conceptual/BPFileSystem/index.html
# - XDG spec for Un*x: http://standards.freedesktop.org/basedir-spec/basedir-spec-latest.html

__version_info__ = (1, 4, 0)
__version__ = '.'.join(map(str, __version_info__))


import sys
import os

PY3 = sys.version_info[0] == 3

if PY3:
    unicode = str

if sys.platform.startswith('java'):
    import platform
    os_name = platform.java_ver()[3][0]
    if os_name.startswith('Windows'): # "Windows XP", "Windows 7", etc.
        system = 'win32'
    elif os_name.startswith('Mac'): # "Mac OS X", etc.
        system = 'darwin'
    else: # "Linux", "SunOS", "FreeBSD", etc.
        # Setting this to "linux2" is not ideal, but only Windows or Mac
        # are actually checked for and the rest of the module expects
        # *sys.platform* style strings.
        system = 'linux2'
else:
    system = sys.platform



def user_data_dir(appname=None, appauthor=None, version=None, roaming=False):
    r"""Return full path to the user-specific data dir for this application.

        "appname" is the name of application.
            If None, just the system directory is returned.
        "appauthor" (only used on Windows) is the name of the
            appauthor or distributing body for this application. Typically
            it is the owning company name. This falls back to appname. You may
            pass False to disable it.
        "version" is an optional version path element to append to the
            path. You might want to use this if you want multiple versions
            of your app to be able to run independently. If used, this
            would typically be "<major>.<minor>".
            Only applied when appname is present.
        "roaming" (boolean, default False) can be set True to use the Windows
            roaming appdata directory. That means that for users on a Windows
            network setup for roaming profiles, this user data will be
            sync'd on login. See
            <http://technet.microsoft.com/en-us/library/cc766489(WS.10).aspx>
            for a discussion of issues.

    Typical user data directories are:
        Mac OS X:               ~/Library/Application Support/<AppName>
        Unix:                   ~/.local/share/<AppName>    # or in $XDG_DATA_HOME, if defined
        Win XP (not roaming):   C:\Documents and Settings\<username>\Application Data\<AppAuthor>\<AppName>
        Win XP (roaming):       C:\Documents and Settings\<username>\Local Settings\Application Data\<AppAuthor>\<AppName>
        Win 7  (not roaming):   C:\Users\<username>\AppData\Local\<AppAuthor>\<AppName>
        Win 7  (roaming):       C:\Users\<username>\AppData\Roaming\<AppAuthor>\<AppName>

    For Unix, we follow the XDG spec and support $XDG_DATA_HOME.
    That means, by default "~/.local/share/<AppName>".
    """
    if system == "win32":
        if appauthor is None:
            appauthor = appname
        const = roaming and "CSIDL_APPDATA" or "CSIDL_LOCAL_APPDATA"
        path = os.path.normpath(_get_win_folder(const))
        if appname:
            if appauthor is not False:
                path = os.path.join(path, appauthor, appname)
            else:
                path = os.path.join(path, appname)
    elif system == 'darwin':
        path = os.path.expanduser('~/Library/Application Support/')
        if appname:
            path = os.path.join(path, appname)
    else:
        path = os.getenv('XDG_DATA_HOME', os.path.expanduser("~/.local/share"))
        if appname:
            path = os.path.join(path, appname)
    if appname and version:
        path = os.path.join(path, version)
    return path


def site_data_dir(appname=None, appauthor=None, version=None, multipath=False):
    """Return full path to the user-shared data dir for this application.

        "appname" is the name of application.
            If None, just the system directory is returned.
        "appauthor" (only used on Windows) is the name of the
            appauthor or distributing body for this application. Typically
            it is the owning company name. This falls back to appname. You may
            pass False to disable it.
        "version" is an optional version path element to append to the
            path. You might want to use this if you want multiple versions
            of your app to be able to run independently. If used, this
            would typically be "<major>.<minor>".
            Only applied when appname is present.
        "multipath" is an optional parameter only applicable to *nix
            which indicates that the entire list of data dirs should be
            returned. By default, the first item from XDG_DATA_DIRS is
            returned, or '/usr/local/share/<AppName>',
            if XDG_DATA_DIRS is not set

    Typical user data directories are:
        Mac OS X:   /Library/Application Support/<AppName>
        Unix:       /usr/local/share/<AppName> or /usr/share/<AppName>
        Win XP:     C:\Documents and Settings\All Users\Application Data\<AppAuthor>\<AppName>
        Vista:      (Fail! "C:\ProgramData" is a hidden *system* directory on Vista.)
        Win 7:      C:\ProgramData\<AppAuthor>\<AppName>   # Hidden, but writeable on Win 7.

    For Unix, this is using the $XDG_DATA_DIRS[0] default.

    WARNING: Do not use this on Windows. See the Vista-Fail note above for why.
    """
    if system == "win32":
        if appauthor is None:
            appauthor = appname
        path = os.path.normpath(_get_win_folder("CSIDL_COMMON_APPDATA"))
        if appname:
            if appauthor is not False:
                path = os.path.join(path, appauthor, appname)
            else:
                path = os.path.join(path, appname)
    elif system == 'darwin':
        path = os.path.expanduser('/Library/Application Support')
        if appname:
            path = os.path.join(path, appname)
    else:
        # XDG default for $XDG_DATA_DIRS
        # only first, if multipath is False
        path = os.getenv('XDG_DATA_DIRS',
                         os.pathsep.join(['/usr/local/share', '/usr/share']))
        pathlist = [os.path.expanduser(x.rstrip(os.sep)) for x in path.split(os.pathsep)]
        if appname:
            if version:
                appname = os.path.join(appname, version)
            pathlist = [os.sep.join([x, appname]) for x in pathlist]

        if multipath:
            path = os.pathsep.join(pathlist)
        else:
            path = pathlist[0]
        return path

    if appname and version:
        path = os.path.join(path, version)
    return path


def user_config_dir(appname=None, appauthor=None, version=None, roaming=False):
    r"""Return full path to the user-specific config dir for this application.

        "appname" is the name of application.
            If None, just the system directory is returned.
        "appauthor" (only used on Windows) is the name of the
            appauthor or distributing body for this application. Typically
            it is the owning company name. This falls back to appname. You may
            pass False to disable it.
        "version" is an optional version path element to append to the
            path. You might want to use this if you want multiple versions
            of your app to be able to run independently. If used, this
            would typically be "<major>.<minor>".
            Only applied when appname is present.
        "roaming" (boolean, default False) can be set True to use the Windows
            roaming appdata directory. That means that for users on a Windows
            network setup for roaming profiles, this user data will be
            sync'd on login. See
            <http://technet.microsoft.com/en-us/library/cc766489(WS.10).aspx>
            for a discussion of issues.

    Typical user data directories are:
        Mac OS X:               same as user_data_dir
        Unix:                   ~/.config/<AppName>     # or in $XDG_CONFIG_HOME, if defined
        Win *:                  same as user_data_dir

    For Unix, we follow the XDG spec and support $XDG_CONFIG_HOME.
    That means, by deafult "~/.config/<AppName>".
    """
    if system in ["win32", "darwin"]:
        path = user_data_dir(appname, appauthor, None, roaming)
    else:
        path = os.getenv('XDG_CONFIG_HOME', os.path.expanduser("~/.config"))
        if appname:
            path = os.path.join(path, appname)
    if appname and version:
        path = os.path.join(path, version)
    return path


def site_config_dir(appname=None, appauthor=None, version=None, multipath=False):
    """Return full path to the user-shared data dir for this application.

        "appname" is the name of application.
            If None, just the system directory is returned.
        "appauthor" (only used on Windows) is the name of the
            appauthor or distributing body for this application. Typically
            it is the owning company name. This falls back to appname. You may
            pass False to disable it.
        "version" is an optional version path element to append to the
            path. You might want to use this if you want multiple versions
            of your app to be able to run independently. If used, this
            would typically be "<major>.<minor>".
            Only applied when appname is present.
        "multipath" is an optional parameter only applicable to *nix
            which indicates that the entire list of config dirs should be
            returned. By default, the first item from XDG_CONFIG_DIRS is
            returned, or '/etc/xdg/<AppName>', if XDG_CONFIG_DIRS is not set

    Typical user data directories are:
        Mac OS X:   same as site_data_dir
        Unix:       /etc/xdg/<AppName> or $XDG_CONFIG_DIRS[i]/<AppName> for each value in
                    $XDG_CONFIG_DIRS
        Win *:      same as site_data_dir
        Vista:      (Fail! "C:\ProgramData" is a hidden *system* directory on Vista.)

    For Unix, this is using the $XDG_CONFIG_DIRS[0] default, if multipath=False

    WARNING: Do not use this on Windows. See the Vista-Fail note above for why.
    """
    if system in ["win32", "darwin"]:
        path = site_data_dir(appname, appauthor)
        if appname and version:
            path = os.path.join(path, version)
    else:
        # XDG default for $XDG_CONFIG_DIRS
        # only first, if multipath is False
        path = os.getenv('XDG_CONFIG_DIRS', '/etc/xdg')
        pathlist = [os.path.expanduser(x.rstrip(os.sep)) for x in path.split(os.pathsep)]
        if appname:
            if version:
                appname = os.path.join(appname, version)
            pathlist = [os.sep.join([x, appname]) for x in pathlist]

        if multipath:
            path = os.pathsep.join(pathlist)
        else:
            path = pathlist[0]
    return path


def user_cache_dir(appname=None, appauthor=None, version=None, opinion=True):
    r"""Return full path to the user-specific cache dir for this application.

        "appname" is the name of application.
            If None, just the system directory is returned.
        "appauthor" (only used on Windows) is the name of the
            appauthor or distributing body for this application. Typically
            it is the owning company name. This falls back to appname. You may
            pass False to disable it.
        "version" is an optional version path element to append to the
            path. You might want to use this if you want multiple versions
            of your app to be able to run independently. If used, this
            would typically be "<major>.<minor>".
            Only applied when appname is present.
        "opinion" (boolean) can be False to disable the appending of
            "Cache" to the base app data dir for Windows. See
            discussion below.

    Typical user cache directories are:
        Mac OS X:   ~/Library/Caches/<AppName>
        Unix:       ~/.cache/<AppName> (XDG default)
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
    if system == "win32":
        if appauthor is None:
            appauthor = appname
        path = os.path.normpath(_get_win_folder("CSIDL_LOCAL_APPDATA"))
        if appname:
            if appauthor is not False:
                path = os.path.join(path, appauthor, appname)
            else:
                path = os.path.join(path, appname)
            if opinion:
                path = os.path.join(path, "Cache")
    elif system == 'darwin':
        path = os.path.expanduser('~/Library/Caches')
        if appname:
            path = os.path.join(path, appname)
    else:
        path = os.getenv('XDG_CACHE_HOME', os.path.expanduser('~/.cache'))
        if appname:
            path = os.path.join(path, appname)
    if appname and version:
        path = os.path.join(path, version)
    return path


def user_log_dir(appname=None, appauthor=None, version=None, opinion=True):
    r"""Return full path to the user-specific log dir for this application.

        "appname" is the name of application.
            If None, just the system directory is returned.
        "appauthor" (only used on Windows) is the name of the
            appauthor or distributing body for this application. Typically
            it is the owning company name. This falls back to appname. You may
            pass False to disable it.
        "version" is an optional version path element to append to the
            path. You might want to use this if you want multiple versions
            of your app to be able to run independently. If used, this
            would typically be "<major>.<minor>".
            Only applied when appname is present.
        "opinion" (boolean) can be False to disable the appending of
            "Logs" to the base app data dir for Windows, and "log" to the
            base cache dir for Unix. See discussion below.

    Typical user cache directories are:
        Mac OS X:   ~/Library/Logs/<AppName>
        Unix:       ~/.cache/<AppName>/log  # or under $XDG_CACHE_HOME if defined
        Win XP:     C:\Documents and Settings\<username>\Local Settings\Application Data\<AppAuthor>\<AppName>\Logs
        Vista:      C:\Users\<username>\AppData\Local\<AppAuthor>\<AppName>\Logs

    On Windows the only suggestion in the MSDN docs is that local settings
    go in the `CSIDL_LOCAL_APPDATA` directory. (Note: I'm interested in
    examples of what some windows apps use for a logs dir.)

    OPINION: This function appends "Logs" to the `CSIDL_LOCAL_APPDATA`
    value for Windows and appends "log" to the user cache dir for Unix.
    This can be disabled with the `opinion=False` option.
    """
    if system == "darwin":
        path = os.path.join(
            os.path.expanduser('~/Library/Logs'),
            appname)
    elif system == "win32":
        path = user_data_dir(appname, appauthor, version)
        version = False
        if opinion:
            path = os.path.join(path, "Logs")
    else:
        path = user_cache_dir(appname, appauthor, version)
        version = False
        if opinion:
            path = os.path.join(path, "log")
    if appname and version:
        path = os.path.join(path, version)
    return path


class AppDirs(object):
    """Convenience wrapper for getting application dirs."""
    def __init__(self, appname, appauthor=None, version=None, roaming=False,
                 multipath=False):
        self.appname = appname
        self.appauthor = appauthor
        self.version = version
        self.roaming = roaming
        self.multipath = multipath

    @property
    def user_data_dir(self):
        return user_data_dir(self.appname, self.appauthor,
                             version=self.version, roaming=self.roaming)

    @property
    def site_data_dir(self):
        return site_data_dir(self.appname, self.appauthor,
                             version=self.version, multipath=self.multipath)

    @property
    def user_config_dir(self):
        return user_config_dir(self.appname, self.appauthor,
                               version=self.version, roaming=self.roaming)

    @property
    def site_config_dir(self):
        return site_data_dir(self.appname, self.appauthor,
                             version=self.version, multipath=self.multipath)

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

    key = _winreg.OpenKey(
        _winreg.HKEY_CURRENT_USER,
        r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders"
    )
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

def _get_win_folder_with_jna(csidl_name):
    import array
    from com.sun import jna
    from com.sun.jna.platform import win32

    buf_size = win32.WinDef.MAX_PATH * 2
    buf = array.zeros('c', buf_size)
    shell = win32.Shell32.INSTANCE
    shell.SHGetFolderPath(None, getattr(win32.ShlObj, csidl_name), None, win32.ShlObj.SHGFP_TYPE_CURRENT, buf)
    dir = jna.Native.toString(buf.tostring()).rstrip("\0")

    # Downgrade to short path name if have highbit chars. See
    # <http://bugs.activestate.com/show_bug.cgi?id=85099>.
    has_high_char = False
    for c in dir:
        if ord(c) > 255:
            has_high_char = True
            break
    if has_high_char:
        buf = array.zeros('c', buf_size)
        kernel = win32.Kernel32.INSTANCE
        if kernal.GetShortPathName(dir, buf, buf_size):
            dir = jna.Native.toString(buf.tostring()).rstrip("\0")

    return dir

if system == "win32":
    try:
        import win32com.shell
        _get_win_folder = _get_win_folder_with_pywin32
    except ImportError:
        try:
            from ctypes import windll
            _get_win_folder = _get_win_folder_with_ctypes
        except ImportError:
            try:
                import com.sun.jna
                _get_win_folder = _get_win_folder_with_jna
            except ImportError:
                _get_win_folder = _get_win_folder_from_registry


#---- self test code

if __name__ == "__main__":
    appname = "MyApp"
    appauthor = "MyCompany"

    props = ("user_data_dir", "site_data_dir",
             "user_config_dir", "site_config_dir",
             "user_cache_dir", "user_log_dir")

    print("-- app dirs (with optional 'version')")
    dirs = AppDirs(appname, appauthor, version="1.0")
    for prop in props:
        print("%s: %s" % (prop, getattr(dirs, prop)))

    print("\n-- app dirs (without optional 'version')")
    dirs = AppDirs(appname, appauthor)
    for prop in props:
        print("%s: %s" % (prop, getattr(dirs, prop)))

    print("\n-- app dirs (without optional 'appauthor')")
    dirs = AppDirs(appname)
    for prop in props:
        print("%s: %s" % (prop, getattr(dirs, prop)))

    print("\n-- app dirs (with disabled 'appauthor')")
    dirs = AppDirs(appname, appauthor=False)
    for prop in props:
        print("%s: %s" % (prop, getattr(dirs, prop)))

########NEW FILE########
__FILENAME__ = Makefile
# This is a Makefile for the `mk` tool. Install it using,
#
#    pip install which mk


import sys
import os
from os.path import join, dirname, normpath, abspath, exists, basename, expanduser
import re
from glob import glob
import codecs
import webbrowser

import mklib
assert mklib.__version_info__ >= (0,7,2)  # for `mklib.mk`
from mklib.common import MkError
from mklib import Task, mk
from mklib import sh


class bugs(Task):
    """open bug/issues page"""
    def make(self):
        webbrowser.open("http://github.com/ActiveState/appdirs/issues")

class site(Task):
    """open project page"""
    def make(self):
        webbrowser.open("http://github.com/ActiveState/appdirs")

class pypi(Task):
    """open project page"""
    def make(self):
        webbrowser.open("http://pypi.python.org/pypi/appdirs/")

class cut_a_release(Task):
    """automate the steps for cutting a release

    See <http://github.com/trentm/eol/blob/master/docs/devguide.md>
    for details.
    """
    proj_name = "appdirs"
    version_py_path = "appdirs.py"
    version_module = "appdirs"

    # XXX: this needs to be changed from .md to .rst format
    _changes_parser = re.compile(r'^## %s (?P<ver>[\d\.abc]+)'
        r'(?P<nyr>\s+\(not yet released\))?'
        r'(?P<body>.*?)(?=^##|\Z)' % proj_name, re.M | re.S)

    def make(self):
        DRY_RUN = False
        version = self._get_version()

        # Confirm
        if not DRY_RUN:
            answer = query_yes_no("* * *\n"
                "Are you sure you want cut a %s release?\n"
                "This will involved commits and a release to pypi." % version,
                default="no")
            if answer != "yes":
                self.log.info("user abort")
                return
            print "* * *"
        self.log.info("cutting a %s release", version)

        # Checks: Ensure there is a section in changes for this version.
        changes_path = join(self.dir, "CHANGES.rst")
        changes_txt = changes_txt_before = codecs.open(changes_path, 'r', 'utf-8').read()
        raise NotImplementedError('_changes_parser: change me to .rst')
        changes_sections = self._changes_parser.findall(changes_txt)
        top_ver = changes_sections[0][0]
        if top_ver != version:
            raise MkError("top section in `CHANGES.rst' is for "
                "version %r, expected version %r: aborting"
                % (top_ver, version))
        top_nyr = changes_sections[0][1]
        if not top_nyr:
            answer = query_yes_no("\n* * *\n"
                "The top section in `CHANGES.rst' doesn't have the expected\n"
                "'(not yet released)' marker. Has this been released already?",
                default="yes")
            if answer != "no":
                self.log.info("abort")
                return
            print "* * *"
        top_body = changes_sections[0][2]
        if top_body.strip() == "(nothing yet)":
            raise MkError("top section body is `(nothing yet)': it looks like "
                "nothing has been added to this release")

        # Commits to prepare release.
        changes_txt = changes_txt.replace(" (not yet released)", "", 1)
        if not DRY_RUN and changes_txt != changes_txt_before:
            self.log.info("prepare `CHANGES.rst' for release")
            f = codecs.open(changes_path, 'w', 'utf-8')
            f.write(changes_txt)
            f.close()
            sh.run('git commit %s -m "prepare for %s release"'
                % (changes_path, version), self.log.debug)

        # Tag version and push.
        curr_tags = set(t for t in _capture_stdout(["git", "tag", "-l"]).split('\n') if t)
        if not DRY_RUN and version not in curr_tags:
            self.log.info("tag the release")
            sh.run('git tag -a "%s" -m "version %s"' % (version, version),
                self.log.debug)
            sh.run('git push --tags', self.log.debug)

        # Release to PyPI.
        self.log.info("release to pypi")
        if not DRY_RUN:
            mk("pypi_upload")

        # Commits to prepare for future dev and push.
        next_version = self._get_next_version(version)
        self.log.info("prepare for future dev (version %s)", next_version)
        marker = "## %s %s\n" % (self.proj_name, version)
        if marker not in changes_txt:
            raise MkError("couldn't find `%s' marker in `%s' "
                "content: can't prep for subsequent dev" % (marker, changes_path))
        changes_txt = changes_txt.replace("## %s %s\n" % (self.proj_name, version),
            "## %s %s (not yet released)\n\n(nothing yet)\n\n## %s %s\n" % (
                self.proj_name, next_version, self.proj_name, version))
        if not DRY_RUN:
            f = codecs.open(changes_path, 'w', 'utf-8')
            f.write(changes_txt)
            f.close()

        ver_path = join(self.dir, normpath(self.version_py_path))
        ver_content = codecs.open(ver_path, 'r', 'utf-8').read()
        version_tuple = self._tuple_from_version(version)
        next_version_tuple = self._tuple_from_version(next_version)
        marker = "__version_info__ = %r" % (version_tuple,)
        if marker not in ver_content:
            raise MkError("couldn't find `%s' version marker in `%s' "
                "content: can't prep for subsequent dev" % (marker, ver_path))
        ver_content = ver_content.replace(marker,
            "__version_info__ = %r" % (next_version_tuple,))
        if not DRY_RUN:
            f = codecs.open(ver_path, 'w', 'utf-8')
            f.write(ver_content)
            f.close()

        if not DRY_RUN:
            sh.run('git commit %s %s -m "prep for future dev"' % (
                changes_path, ver_path))
            sh.run('git push')

    def _tuple_from_version(self, version):
        def _intify(s):
            try:
                return int(s)
            except ValueError:
                return s
        return tuple(_intify(b) for b in version.split('.'))

    def _get_next_version(self, version):
        last_bit = version.rsplit('.', 1)[-1]
        try:
            last_bit = int(last_bit)
        except ValueError: # e.g. "1a2"
            last_bit = int(re.split('[abc]', last_bit, 1)[-1])
        return version[:-len(str(last_bit))] + str(last_bit + 1)

    def _get_version(self):
        try:
            mod = __import__(self.version_module)
            return mod.__version__
        finally:
            del sys.path[0]


class clean(Task):
    """Clean generated files and dirs."""
    def make(self):
        patterns = [
            "dist",
            "build",
            "MANIFEST",
            "*.pyc",
        ]
        for pattern in patterns:
            p = join(self.dir, pattern)
            for path in glob(p):
                sh.rm(path, log=self.log)

class sdist(Task):
    """python setup.py sdist"""
    def make(self):
        sh.run_in_dir("%spython setup.py sdist --formats zip"
                        % _setup_command_prefix(),
                      self.dir, self.log.debug)

class pypi_upload(Task):
    """Upload release to pypi."""
    def make(self):
        sh.run_in_dir("%spython setup.py sdist --formats zip upload"
                % _setup_command_prefix(),
            self.dir, self.log.debug)

        url = "http://pypi.python.org/pypi/appdirs/"
        import webbrowser
        webbrowser.open_new(url)

class tox(Task):
    """Test on all available Python versions using tox"""
    def make(self):
        sh.run("python toxbootstrap.py")

class test(Task):
    """Run all tests (except known failures)."""
    def make(self):
        for ver, python in self._gen_pythons():
            if ver < (2,3):
                # Don't support Python < 2.3.
                continue
            #elif ver >= (3, 0):
            #    # Don't yet support Python 3.
            #    continue
            ver_str = "%s.%s" % ver
            print "-- test with Python %s (%s)" % (ver_str, python)
            assert ' ' not in python
            sh.run("%s setup.py test" % python)

    def _python_ver_from_python(self, python):
        assert ' ' not in python
        o = os.popen('''%s -c "import sys; print(sys.version)"''' % python)
        ver_str = o.read().strip()
        ver_bits = re.split("\.|[^\d]", ver_str, 2)[:2]
        ver = tuple(map(int, ver_bits))
        return ver

    def _gen_python_names(self):
        yield "python"
        for ver in [(2,4), (2,5), (2,6), (2,7), (3,0), (3,1)]:
            yield "python%d.%d" % ver
            if sys.platform == "win32":
                yield "python%d%d" % ver

    def _gen_pythons(self):
        import which  # `pypm|pip install which`
        python_from_ver = {}
        for name in self._gen_python_names():
            for python in which.whichall(name):
                ver = self._python_ver_from_python(python)
                if ver not in python_from_ver:
                    python_from_ver[ver] = python
        for ver, python in sorted(python_from_ver.items()):
            yield ver, python




#---- internal support stuff

## {{{ http://code.activestate.com/recipes/577058/ (r2)
def query_yes_no(question, default="yes"):
    """Ask a yes/no question via raw_input() and return their answer.

    "question" is a string that is presented to the user.
    "default" is the presumed answer if the user just hits <Enter>.
        It must be "yes" (the default), "no" or None (meaning
        an answer is required of the user).

    The "answer" return value is one of "yes" or "no".
    """
    valid = {"yes":"yes",   "y":"yes",  "ye":"yes",
             "no":"no",     "n":"no"}
    if default == None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while 1:
        sys.stdout.write(question + prompt)
        choice = raw_input().lower()
        if default is not None and choice == '':
            return default
        elif choice in valid.keys():
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'yes' or 'no' "\
                             "(or 'y' or 'n').\n")
## end of http://code.activestate.com/recipes/577058/ }}}


def _setup_command_prefix():
    prefix = ""
    if sys.platform == "darwin":
        # http://forums.macosxhints.com/archive/index.php/t-43243.html
        # This is an Apple customization to `tar` to avoid creating
        # '._foo' files for extended-attributes for archived files.
        prefix = "COPY_EXTENDED_ATTRIBUTES_DISABLE=1 "
    return prefix

def _capture_stdout(argv):
    import subprocess
    p = subprocess.Popen(argv, stdout=subprocess.PIPE)
    return p.communicate()[0]

########NEW FILE########
__FILENAME__ = test_api
import sys
import appdirs

if sys.version_info < (2, 7):
    import unittest2 as unittest
else:
    import unittest

if sys.version_info[0] < 3:
    STRING_TYPE = basestring
else:
    STRING_TYPE = str


class Test_AppDir(unittest.TestCase):
    def test_metadata(self):
        self.assertTrue(hasattr(appdirs, "__version__"))
        self.assertTrue(hasattr(appdirs, "__version_info__"))

    def test_helpers(self):
        self.assertIsInstance(
            appdirs.user_data_dir('MyApp', 'MyCompany'), STRING_TYPE)
        self.assertIsInstance(
            appdirs.site_data_dir('MyApp', 'MyCompany'), STRING_TYPE)
        self.assertIsInstance(
            appdirs.user_cache_dir('MyApp', 'MyCompany'), STRING_TYPE)
        self.assertIsInstance(
            appdirs.user_log_dir('MyApp', 'MyCompany'), STRING_TYPE)

    def test_dirs(self):
        dirs = appdirs.AppDirs('MyApp', 'MyCompany', version='1.0')
        self.assertIsInstance(dirs.user_data_dir, STRING_TYPE)
        self.assertIsInstance(dirs.site_data_dir, STRING_TYPE)
        self.assertIsInstance(dirs.user_cache_dir, STRING_TYPE)
        self.assertIsInstance(dirs.user_log_dir, STRING_TYPE)

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
