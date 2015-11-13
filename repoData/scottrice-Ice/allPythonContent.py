__FILENAME__ = build
#!/usr/bin/env python
# encoding: utf-8
"""
build.py

Created by Scott on 2013-10-03.
Copyright (c) 2013 Scott Rice. All rights reserved.

Code to generate an exe file out of Ice, along with any extra metadata needed.
"""

import os

import subprocess
import datetime
import zipfile
import shutil

ice_dir = os.path.dirname(os.path.realpath(__file__))
dist_dir = os.path.join(ice_dir,"dist")
zip_dir = os.path.join(dist_dir,"Ice")

def remove_previous_builds():
	"""Remove all of the artifacts from previous builds"""
	def remove_if_needed(path):
		if os.path.exists(path):
			shutil.rmtree(path)
	remove_if_needed(os.path.join(ice_dir,"build"))
	remove_if_needed(dist_dir)

def create_zip_directory():
	"""Creates a directory called 'Ice' inside dist that will be zipped"""
	os.makedirs(zip_dir)

def build_exe():
	command = "python %s/pyinstaller/pyinstaller.py --onefile --icon=icon.ico ice.py" % ice_dir
	subprocess.call(command)

def add_file(name, directory, new_name=None):
	"""Adds a file named 'name' in 'directory' to the zip directory"""
	if new_name is None:
		new_name = name
	src = os.path.join(directory, name)
	dst = os.path.join(zip_dir, new_name)
	shutil.copyfile(src, dst)

def add_extra_files():
	shutil.move(os.path.join(dist_dir,"ice.exe"),os.path.join(zip_dir,"Ice.exe"))
	add_file("config.txt",ice_dir)
	add_file("consoles.txt",ice_dir)
	add_file("emulators.txt",ice_dir)
	add_file("Binary-README.txt",ice_dir,"README.txt")
	add_file("ExitCombo.cfg",os.path.join(ice_dir,"config"),"ExitCombination.cfg")

def add_version_file():
	pfgit = os.path.join("C:/", "Program Files (x86)","Git","bin","git.exe")
	pfgit_exists = os.path.exists(pfgit)
	pfx86git = os.path.join("C:/", "Program Files (x86)","Git","bin","git.exe")
	pfx86git_exists = os.path.exists(pfx86git)
	if not pfgit_exists and not pfx86git_exists:
		# Whoever is building this doesn't have git installed, so I can't get
		# the revision. In that case, bail.
		return
	if pfgit_exists:
		git = pfgit
	else:
		git = pfx86git
	git_rev = subprocess.check_output("%s rev-parse --short HEAD" % git).strip()
	current_time = datetime.datetime.now().strftime("%I:%M%p on %B %d, %Y")
	version_path = os.path.join(zip_dir,"version.txt")
	version_file = open(version_path,"w+")
	version_file.write("Built at %s\n\nRevision %s" % (current_time, git_rev))

def zip_everything():
	# Taken from http://stackoverflow.com/questions/1855095/how-to-create-a-zip-archive-of-a-directory-in-python
	ice_zip = zipfile.ZipFile(os.path.join(dist_dir,'ice.zip'), 'w')
	for root, dirs, files in os.walk(zip_dir):
		for f in files:
			ice_zip.write(os.path.join(root, f),os.path.join("Ice",f))
	ice_zip.close()

def main():
	remove_previous_builds()
	create_zip_directory()
	build_exe()
	add_extra_files()
	add_version_file()
	zip_everything()

if __name__ == "__main__":
	main()
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
__FILENAME__ = console
#!/usr/bin/env python
# encoding: utf-8
"""
console.py

Created by Scott on 2012-12-24.
Copyright (c) 2012 Scott Rice. All rights reserved.

This class represents the Console datatype. Each ROM is associated with a
Console, and each Console has many ROMs. A Console also is associated with an
emulator, which can be used to play a ROM.

Functionality should be added to this class/module if it deals with Consoles or
their emulators. This includes finding a list of ROMs in this console's folder.
"""

import os

import settings
import platform_helper as pf
import filesystem_helper
import utils
from ice_logging import ice_logger
from emulator import Emulator
from rom import ROM

class Console():

    def __init__(self, name, options={}):
        self.fullname = name
        self.shortname = utils.idx(options, 'nickname', name)
        self.extensions = utils.idx(options, 'extensions', "")
        self.custom_roms_directory = utils.idx(options, 'roms directory', None)
        self.prefix = utils.idx(options, 'prefix', "")
        self.icon = os.path.expanduser(utils.idx(options, 'icon', ""))
        self.images_directory = os.path.expanduser(utils.idx(options, 'images directory', ""))

        self.emulator = Emulator.lookup(utils.idx(options, 'emulator', ""))
        
    def __repr__(self):
        return self.shortname

    def is_enabled(self,verbose=False):
        if self.emulator is None:
            if verbose:
                ice_logger.log("Skipping %s (no emulator provided)" % self)
            return False
        if self.custom_roms_directory and not filesystem_helper.available_to_use(self.custom_roms_directory, create_if_needed=True):
            if verbose:
                ice_logger.log("Skipping %s (ROMs directory provided either doesn't exist or is not writable)" % self)
            return False
        return True

    def roms_directory(self):
        """
        If the user has specified a ROMs directory in consoles.txt and it is
        accessible to Ice, returns that.

        Otherwise, appends the shortname of the console to the default ROMs
        directory given by config.txt.
        """
        if self.custom_roms_directory:
            return self.custom_roms_directory
        return os.path.join(filesystem_helper.roms_directory(),self.shortname)
      
    def is_valid_rom(self,path):
        """
        This function determines if a given path is actually a valid ROM file.
        If a list of extensions is supplied for this console, we check if the path has a valid extension
        If no extensions are defined for this console, we just accept any file
        """

        if self.extensions == "":
            return True
        extension = os.path.splitext(path)[1].lower()
        return any(extension == ('.'+x.strip().lower()) for x in self.extensions.split(','))
  
    def find_roms(self):
        """
        Reads a list of all the ROMs from the appropriate directory for the
        console
        """
        roms = []
        if not os.path.exists(self.roms_directory()):
            ice_logger.log("Creating %s directory at %s" % (self.shortname,self.roms_directory()))
            os.makedirs(self.roms_directory())
        for filename in os.listdir(self.roms_directory()):
            file_path = os.path.join(self.roms_directory(),filename)
            if not os.path.isdir(file_path):
                # On Linux/OSX, we want to make sure hidden files don't get
                # accidently added as well
                if not pf.is_windows() and filename.startswith('.'):
                    continue
                if self.emulator is not None and not self.is_valid_rom(file_path):
                    ice_logger.log_warning("Ignoring Non-ROM file: %s" % file_path)
                    continue
                roms.append(ROM(file_path,self))
        return roms

@utils.memoize
def find_all_roms():
    """
    Gets the roms for every console in the list of supported consoles
    """
    all_roms = []
    for console in supported_consoles():
        all_roms.extend(console.find_roms())
    return all_roms

@utils.memoize
def settings_consoles():
    consoles = []
    consoles_dict = settings.consoles()
    for name in consoles_dict.keys():
        console_data = consoles_dict[name]
        console = Console(name, console_data)
        consoles.append(console)
    return consoles

@utils.memoize
def supported_consoles():
    consoles = settings_consoles()
    # Remove any consoles from supported_consoles if there does not exist an
    # emulator for them
    for console in list(consoles):
        if not console.is_enabled(verbose=True):
            consoles.remove(console)
    # Print out all of the detected consoles so the user knows what is going
    # on.
    for console in consoles:
        ice_logger.log("Detected Console: %s => %s" % (console.fullname, console.emulator.name))
    return consoles

########NEW FILE########
__FILENAME__ = crc_algorithms
#  pycrc -- parameterisable CRC calculation utility and C source code generator
#
#  Copyright (c) 2006-2013  Thomas Pircher  <tehpeh@gmx.net>
#
#  Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to
#  deal in the Software without restriction, including without limitation the
#  rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
#  sell copies of the Software, and to permit persons to whom the Software is
#  furnished to do so, subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included in
#  all copies or substantial portions of the Software.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
#  FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
#  IN THE SOFTWARE.


"""
CRC algorithms implemented in Python.
If you want to study the Python implementation of the CRC routines, then this
is a good place to start from.

The algorithms Bit by Bit, Bit by Bit Fast and Table-Driven are implemented.

This module can also be used as a library from within Python.

Examples
========

This is an example use of the different algorithms:

>>> from crc_algorithms import Crc
>>>
>>> crc = Crc(width = 16, poly = 0x8005,
...           reflect_in = True, xor_in = 0x0000,
...           reflect_out = True, xor_out = 0x0000)
>>> print("0x%x" % crc.bit_by_bit("123456789"))
>>> print("0x%x" % crc.bit_by_bit_fast("123456789"))
>>> print("0x%x" % crc.table_driven("123456789"))
"""

# Class Crc
###############################################################################
class Crc(object):
    """
    A base class for CRC routines.
    """

    # Class constructor
    ###############################################################################
    def __init__(self, width, poly, reflect_in, xor_in, reflect_out, xor_out, table_idx_width = None):
        """The Crc constructor.

        The parameters are as follows:
            width
            poly
            reflect_in
            xor_in
            reflect_out
            xor_out
        """
        self.Width          = width
        self.Poly           = poly
        self.ReflectIn      = reflect_in
        self.XorIn          = xor_in
        self.ReflectOut     = reflect_out
        self.XorOut         = xor_out
        self.TableIdxWidth  = table_idx_width

        self.MSB_Mask = 0x1 << (self.Width - 1)
        self.Mask = ((self.MSB_Mask - 1) << 1) | 1
        if self.TableIdxWidth != None:
            self.TableWidth = 1 << self.TableIdxWidth
        else:
            self.TableIdxWidth = 8
            self.TableWidth = 1 << self.TableIdxWidth

        self.DirectInit = self.XorIn
        self.NonDirectInit = self.__get_nondirect_init(self.XorIn)
        if self.Width < 8:
            self.CrcShift = 8 - self.Width
        else:
            self.CrcShift = 0


    # function __get_nondirect_init
    ###############################################################################
    def __get_nondirect_init(self, init):
        """
        return the non-direct init if the direct algorithm has been selected.
        """
        crc = init
        for i in range(self.Width):
            bit = crc & 0x01
            if bit:
                crc^= self.Poly
            crc >>= 1
            if bit:
                crc |= self.MSB_Mask
        return crc & self.Mask


    # function reflect
    ###############################################################################
    def reflect(self, data, width):
        """
        reflect a data word, i.e. reverts the bit order.
        """
        x = data & 0x01
        for i in range(width - 1):
            data >>= 1
            x = (x << 1) | (data & 0x01)
        return x


    # function bit_by_bit
    ###############################################################################
    def bit_by_bit(self, in_str):
        """
        Classic simple and slow CRC implementation.  This function iterates bit
        by bit over the augmented input message and returns the calculated CRC
        value at the end.
        """
        register = self.NonDirectInit
        for c in in_str:
            octet = ord(c)
            if self.ReflectIn:
                octet = self.reflect(octet, 8)
            for i in range(8):
                topbit = register & self.MSB_Mask
                register = ((register << 1) & self.Mask) | ((octet >> (7 - i)) & 0x01)
                if topbit:
                    register ^= self.Poly

        for i in range(self.Width):
            topbit = register & self.MSB_Mask
            register = ((register << 1) & self.Mask)
            if topbit:
                register ^= self.Poly

        if self.ReflectOut:
            register = self.reflect(register, self.Width)
        return register ^ self.XorOut


    # function bit_by_bit_fast
    ###############################################################################
    def bit_by_bit_fast(self, in_str):
        """
        This is a slightly modified version of the bit-by-bit algorithm: it
        does not need to loop over the augmented bits, i.e. the Width 0-bits
        wich are appended to the input message in the bit-by-bit algorithm.
        """
        register = self.DirectInit
        for c in in_str:
            octet = ord(c)
            if self.ReflectIn:
                octet = self.reflect(octet, 8)
            for i in range(8):
                topbit = register & self.MSB_Mask
                if octet & (0x80 >> i):
                    topbit ^= self.MSB_Mask
                register <<= 1
                if topbit:
                    register ^= self.Poly
            register &= self.Mask
        if self.ReflectOut:
            register = self.reflect(register, self.Width)
        return register ^ self.XorOut


    # function gen_table
    ###############################################################################
    def gen_table(self):
        """
        This function generates the CRC table used for the table_driven CRC
        algorithm.  The Python version cannot handle tables of an index width
        other than 8.  See the generated C code for tables with different sizes
        instead.
        """
        table_length = 1 << self.TableIdxWidth
        tbl = [0] * table_length
        for i in range(table_length):
            register = i
            if self.ReflectIn:
                register = self.reflect(register, self.TableIdxWidth)
            register = register << (self.Width - self.TableIdxWidth + self.CrcShift)
            for j in range(self.TableIdxWidth):
                if register & (self.MSB_Mask << self.CrcShift) != 0:
                    register = (register << 1) ^ (self.Poly << self.CrcShift)
                else:
                    register = (register << 1)
            if self.ReflectIn:
                register = self.reflect(register >> self.CrcShift, self.Width) << self.CrcShift
            tbl[i] = register & (self.Mask << self.CrcShift)
        return tbl


    # function table_driven
    ###############################################################################
    def table_driven(self, in_str):
        """
        The Standard table_driven CRC algorithm.
        """
        tbl = self.gen_table()

        register = self.DirectInit << self.CrcShift
        if not self.ReflectIn:
            for c in in_str:
                tblidx = ((register >> (self.Width - self.TableIdxWidth + self.CrcShift)) ^ ord(c)) & 0xff
                register = ((register << (self.TableIdxWidth - self.CrcShift)) ^ tbl[tblidx]) & (self.Mask << self.CrcShift)
            register = register >> self.CrcShift
        else:
            register = self.reflect(register, self.Width + self.CrcShift) << self.CrcShift
            for c in in_str:
                tblidx = ((register >> self.CrcShift) ^ ord(c)) & 0xff
                register = ((register >> self.TableIdxWidth) ^ tbl[tblidx]) & (self.Mask << self.CrcShift)
            register = self.reflect(register, self.Width + self.CrcShift) & self.Mask

        if self.ReflectOut:
            register = self.reflect(register, self.Width)
        return register ^ self.XorOut


########NEW FILE########
__FILENAME__ = emulator
#!/usr/bin/env python
# encoding: utf-8
"""
Emulator.py

Created by Scott on 2013-01-04.
Copyright (c) 2013 Scott Rice. All rights reserved.

Emulator is the base class of all my emulators.

Functionality should be added here if every single emulator (whether downloaded
or not) would use it
"""

import os
import tempfile
import shutil

from error.config_error import ConfigError
from ice_logging import ice_logger
import filesystem_helper
import settings
import utils

class Emulator(object):

    @classmethod
    def lookup(self, name):
        for emulator in settings_emulators():
            if emulator.name == name:
                return emulator
        return None

    def __init__(self, name, location, options={}):
        self.name = name
        self.location = os.path.expanduser(location)
        self.format = utils.idx(options, 'command', "%l %r")
        filesystem_helper.assert_file_exists(self.location, self.__config_error_for_missing_emulator__())

    def __config_error_for_missing_emulator__(self):
        fix = "Cannot read file '%s'. Ensure that the file exists, and that the path is spelled correctly." % self.location
        return ConfigError(self.name, "location", fix, file="emulators.txt")

    def __add_quotes_if_needed__(self, string):
        if string.startswith("\"") and string.endswith("\""):
            return string
        else:
            return "\"%s\"" % string

    def is_enabled(self, verbose=False):
        """
        Checks to see whether enough information has been entered by the user
        to make the emulator useable
        """
        # Right now the only thing we care about is whether a file exists where
        # the user says the emulator is.
        if not os.path.isfile(self.location):
            if verbose:
                ice_logger.log("(Emulator) File does not exist at '%s'. Ignoring %s" % (self.location, self.name))
            return False
        return True
    
    def command_string(self, rom):
        """Generates a command string using the format specified by the user"""
        # We don't know if the user put quotes around the emulator location. If
        # so, we dont want to add another pair and screw things up.
        quoted_location = self.__add_quotes_if_needed__(self.location)
        # The user didnt give us the ROM information, but screw it, I already
        # have some code to add quotes to a string, might as well use it.
        quoted_rom = self.__add_quotes_if_needed__(rom.path)
        return self.format.replace("%l", quoted_location).replace("%r", quoted_rom)
        
    def startdir(self,rom):
        """
        Returns the directory which stores the emulator. This value is useful
        as the 'StartDir' option of a Steam Shortcut
        """
        return os.path.dirname(self.location)

@utils.memoize
def settings_emulators():
    emulators = []
    emulators_dict = settings.emulators()
    for name in emulators_dict.keys():
        emulator_data = emulators_dict[name]
        location = utils.idx(emulator_data, 'location', "")
        current_emulator = Emulator(name, location, emulator_data)
        if current_emulator.is_enabled(verbose=True):
            emulators.append(current_emulator)
    # After all of the invalid emulators have been removed, let the user know
    # which emulators have initialized successfully
    for emulator in emulators:
        ice_logger.log("Detected Emulator: %s" % emulator.name)
    return emulators

########NEW FILE########
__FILENAME__ = config_error
#!/usr/bin/env python
# encoding: utf-8
"""
config_error.py

Created by Scott on 2013-05-23.
Copyright (c) 2013 Scott Rice. All rights reserved.
"""


class ConfigError(StandardError):
    def __init__(self, section, key, fix_instructions, file="config.txt"):
        self.section = section
        self.key = key
        self.fix_instructions = fix_instructions
        self.file = file
        
    def __str__(self):
        return repr("[%s] %s || %s" % (self.section, self.key, self.fix_instructions))
########NEW FILE########
__FILENAME__ = provider_error
#!/usr/bin/env python
# encoding: utf-8
"""
provider_error.py

Created by Scott on 2014-01-07.
Copyright (c) 2014 Scott Rice. All rights reserved.

Represents an issue with getting an image from a Grid Image Provider (like
ConsoleGrid).
"""

class ProviderError(StandardError):
    pass

########NEW FILE########
__FILENAME__ = filesystem_helper
#!/usr/bin/env python
# encoding: utf-8
"""
filesystem_helper.py

Created by Scott on 2012-12-24.
Copyright (c) 2012 Scott Rice. All rights reserved.

Abstracts away filesystem specific information into app-specific methods. For
example, the app doesn't care about where exactly on the filesystem the ROMs
directory is located, it just wants to know what ROMs are a part of it. This
module is meant to deal with that abstraction.

Functionality should be added to this module if it involves the filesystem, but
doesn't heavily involve any of the other datatypes used by this app (Consoles,
ROMs, etc)
"""

import os

import appdirs

import settings
from error.config_error import ConfigError
from ice_logging import ice_logger

def highest_directory_in_path(path):
    """
    Returns the 'highest' directory in a path, which is defined as the first
    path component
    
    Example In => Out
    (Mac)
    /Users/scottrice/Documents/Resume.pdf => /
    Users/scottrice/Documents/Resume.pdf => Users
    (Windows)
    C:\\Users\Scott\Documents\Resume.pdf => C:\
    bsnes\\bsnes.exe => bsnes
    """
    # We don't support absolute paths because of how os.path.split handles the
    # path = "/" case
    if path.startswith("/"):
        return "/"
    (head,tail) = os.path.split(path)
    # Empty string is falsy, so this is checking for "if head is not empty"
    if head:
        return highest_directory_in_path(head)
    else:
        return tail

def create_directory_if_needed(dir, log=None):
    """
    Checks to see if a directory exists and, if not, creates it
    """
    if not os.path.exists(dir):
        if log is not None:
            ice_logger.log(log)
        os.makedirs(dir)

def assert_file_exists(path, exception=None):
    if not os.path.isfile(path):
        raise exception

def available_to_use(path, create_if_needed=False):
    """
    Checks a boolean based on whether a directory is 'available' for Ice to use.
    This means that not only does the path exist, but Ice has write access to it
    as well.

    When create_if_needed is set to True, Ice will attempt to create a directory
    if one does not exist at path. Any errors in this operation will be logged
    to the log file and this function will return False
    """
    # Ensure the directory exists
    try:
        if create_if_needed:
            create_directory_if_needed(path, log="Creating directory at %s" % path)
        # Ensure that it worked
        if not os.path.exists(path):
            return False
    # Might not be necessary, but in case create_directory_if_needed fails...
    except:
        return False

    # Check that we have write access to the directory
    if not os.access(path, os.W_OK):
        return False

    # Woohoo!
    return True


def roms_directory():
    """
    Returns the path to the ROMs directory, as specified by config.txt.
    """
    path = os.path.expanduser(settings.config()['Storage']['roms directory'])
    if path == "":
        path = os.path.join(os.path.expanduser("~"), "ROMs")
    if not available_to_use(path, create_if_needed=True):
        fix_instructions = "Ice does not have permission to write to your ROMs Directory, %s. Please choose a different folder or change your permissions." % path
        raise ConfigError("Storage","ROMs Directory", fix_instructions)
    return path

def log_file():
    """
    Should return the path for the log file. The log file should be located in
    the app's data directory and should be called 'log.txt'
    
    Example...
    Windows: C:\Users\<username>\AppData\Local\Scott Rice\Ice\log.txt
    Max OS X: ~/Library/Application Support/Ice/log.txt
    """
    return os.path.join(app_data_directory(),"log.txt")

########NEW FILE########
__FILENAME__ = consolegrid_provider
#!/usr/bin/env python
# encoding: utf-8
"""
consolegrid_provider.py

Created by Scott on 2013-12-26.
Copyright (c) 2013 Scott Rice. All rights reserved.
"""

import sys
import os
import urllib
import urllib2

import grid_image_provider
from ice.error.config_error import ConfigError
from ice.error.provider_error import ProviderError

class ConsoleGridProvider(grid_image_provider.GridImageProvider):
    @staticmethod
    def api_url():
        return "http://consolegrid.com/api/top_picture"

    @staticmethod
    def is_enabled():
        # TODO: Return True/False based on the current network status
        return True

    def consolegrid_top_picture_url(self,rom):
        host = self.api_url()
        quoted_name = urllib.quote(rom.name())
        return "%s?console=%s&game=%s" % (host,rom.console.shortname,quoted_name)

    def find_url_for_rom(self,rom):
        """
        Determines a suitable grid image for a given ROM by hitting
        ConsoleGrid.com
        """
        try:
            response = urllib2.urlopen(self.consolegrid_top_picture_url(rom))
            if response.getcode() == 204:
              raise ProviderError("ConsoleGrid has no game called %s for %s. Try going to http://consolegrid.com and submitting the game yourself" % (rom.name(), rom.console.fullname))
            else:
              return response.read()
        except urllib2.URLError as error:
            # Connection was refused. ConsoleGrid may be down, or something bad
            # may have happened
            raise ConfigError("Grid Images", "Source", "The source of game images is unavailable.")

    def download_image(self,rom):
        """
        Downloads the image at 'image_url' and returns the path to the image on
        the local filesystem
        """
        image_url = self.find_url_for_rom(rom)
        if image_url == "":
          raise ProviderError("We couldn't find an image for %s. If you find one you like, upload it to http://consolegrid.com, and next time Ice runs it will be used" % rom.name())
        (path,headers) = urllib.urlretrieve(image_url)
        return path

    def image_for_rom(self, rom):
        try:
            path = self.download_image(rom)
            return (path, None)
        except ProviderError as e:
            return (None, e)

########NEW FILE########
__FILENAME__ = grid_image_provider
#!/usr/bin/env python
# encoding: utf-8
"""
grid_image_provider.py

Created by Scott on 2013-12-26.
Copyright (c) 2013 Scott Rice. All rights reserved.
"""

import sys
import os
import abc

class GridImageProvider(object):

    def is_enabled(self):
        """
        Returns whether the GridImageProvider is available to use.
        """
        return True

    def image_for_rom(self, rom):
        """
        Returns a tuple of (image, error). If an image was found, 'image'
        should be the path of the image on disc and 'error' should be None. If
        no image was found, then 'image' should be None and error should be
        a subclass of 'StandardError'.
        """
        raise NotImplementedError("Not yet implemented")

########NEW FILE########
__FILENAME__ = local_provider
#!/usr/bin/env python
# encoding: utf-8
"""
local_provider.py

Created by Scott on 2013-12-26.
Copyright (c) 2013 Scott Rice. All rights reserved.
"""

import sys
import os

import grid_image_provider
from ice.error.provider_error import ProviderError

class LocalProvider(grid_image_provider.GridImageProvider):

    def valid_extensions(self):
        return ['.png', '.jpg', '.jpeg', '.tiff']

    def image_for_rom(self, rom):
        """
        Checks the filesystem for images for a given ROM. To do so, it makes
        use of a consoles 'images' directory. If it finds an image in that
        directory with the same name as the ROMs name then it will return that.
        """
        img_dir = rom.console.images_directory
        if img_dir == "":
            return (None, ProviderError("No images directory specified for %s" % rom.console.shortname))
        for extension in self.valid_extensions():
            filename = rom.name() + extension
            path = os.path.join(img_dir, filename)
            if os.path.isfile(path):
                # We found a valid path, return it
                return (path, None)
        # We went through all of the possible filenames for this ROM and a
        # file didnt exist with any of them. There is no image for this ROM in
        # the consoles image directory
        return (None, ProviderError("No image named '%s' with a valid file extension was found in '%s'" % (rom.name(), img_dir)))

########NEW FILE########
__FILENAME__ = grid_image_manager
#!/usr/bin/env python
# encoding: utf-8
"""
IceGridImageManager.py

Created by Scott on 2012-12-24.
Copyright (c) 2012 Scott Rice. All rights reserved.

The purpose of this class is to handle the downloading and setting of Steam
App Grid images for each shortcut.

Functionality should be added to this class if it involves Steam App Grid 
images.
"""

import urllib
import urllib2
import urlparse
import steam_user_manager
import steam_grid
import settings
from ice_logging import ice_logger
from error.config_error import ConfigError

# Providers
from gridproviders import local_provider
from gridproviders import consolegrid_provider

class IceGridImageManager():
    
    def __init__(self):
        self.providers = [
            local_provider.LocalProvider(),
            consolegrid_provider.ConsoleGridProvider(),
        ]
    
    def image_for_rom(self, rom):
        """
        Goes through each provider until one successfully finds an image.
        Returns None if no provider was able to find an image
        """
        for provider in self.providers:
            (path, error) = provider.image_for_rom(rom)
            if path is not None:
                return path
            # TODO: Log the error for the provider
            # ice_logger.log_error(error)
        return None

    def update_user_images(self, user_id, roms):
        """
        Sets a suitable grid image for every rom in 'roms' for the user
        defined by 'user_id'
        """
        grid = steam_grid.SteamGrid(steam_user_manager.userdata_directory_for_user_id(user_id))
        for rom in roms:
            shortcut = rom.to_shortcut()
            if not grid.existing_image_for_filename(grid.filename_for_shortcut(shortcut.appname, shortcut.exe)):
                path = self.image_for_rom(rom)
                if path is None:
                    # TODO: Tell the user what went wrong
                    pass
                else:
                    # TODO: Tell the user that an image was found
                    ice_logger.log("Found grid image for %s" % shortcut.appname)
                    grid.set_image_for_shortcut(path, shortcut.appname, shortcut.exe)

########NEW FILE########
__FILENAME__ = gui
import sys
from PyQt4.QtGui import QApplication, QMainWindow, QFileDialog
from PyQt4 import QtCore
from ui import ui_windowMain, ui_windowSettings

# Ice
import ConfigParser
import settings

from error.config_error import ConfigError

from steam_shortcut_manager import SteamShortcutManager

import steam_user_manager
import filesystem_helper as fs
import console
from rom_manager import IceROMManager
from process_helper import steam_is_running
from grid_image_manager import IceGridImageManager
from ice_logging import ice_logger

class WindowSettings(QMainWindow):
    def __init__(self, parent=None):
        QMainWindow.__init__(self, parent)

        self.ui = ui_windowSettings.Ui_windowSettings()
        self.ui.setupUi(self)

        # actions
        self.ui.btnSave.pressed.connect(self._saveSettings)
        self.ui.btnCancel.pressed.connect(self._cancel)

        self.ui.openBinNES.pressed.connect(self.openBinNES)
        self.ui.openBinSNES.pressed.connect(self.openBinSNES)
        self.ui.openBinN64.pressed.connect(self.openBinN64)
        self.ui.openBinGameCube.pressed.connect(self.openBinGameCube)
        self.ui.openBinWii.pressed.connect(self.openBinWii)
        self.ui.openBinPS1.pressed.connect(self.openBinPS1)
        self.ui.openBinPS2.pressed.connect(self.openBinPS2)
        self.ui.openBinGenesis.pressed.connect(self.openBinGenesis)
        self.ui.openBinDreamcast.pressed.connect(self.openBinDreamcast)
        self.ui.openBinGameBoy.pressed.connect(self.openBinGameBoy)
        self.ui.openBinGBA.pressed.connect(self.openBinGBA)
        self.ui.openBinNDS.pressed.connect(self.openBinNDS)

        # load current saved settings
        self._loadSettings()

    def _loadSettings(self):
        try:
            for consoleentry in settings.consoles():
                if settings.consoles()[consoleentry]['emulator'] != '':
                    emulator = settings.consoles()[consoleentry]['emulator']

                    if consoleentry == 'Nintendo Entertainment System':
                        self.ui.pathNES.setText(settings.emulators()[emulator]['location'])
                        self.ui.cmdNES.setText(settings.emulators()[emulator]['command'])
                    elif consoleentry == 'Super Nintendo':
                        self.ui.pathSNES.setText(settings.emulators()[emulator]['location'])
                        self.ui.cmdSNES.setText(settings.emulators()[emulator]['command'])
                    elif consoleentry == 'Nintendo 64':
                        self.ui.pathN64.setText(settings.emulators()[emulator]['location'])
                        self.ui.cmdN64.setText(settings.emulators()[emulator]['command'])
                    elif consoleentry == 'Nintendo Gamecube':
                        self.ui.pathGameCube.setText(settings.emulators()[emulator]['location'])
                        self.ui.cmdGameCube.setText(settings.emulators()[emulator]['command'])
                    elif consoleentry == 'Nintendo Wii':
                        self.ui.pathWii.setText(settings.emulators()[emulator]['location'])
                        self.ui.cmdWii.setText(settings.emulators()[emulator]['command'])
                    elif consoleentry == 'Playstation 1':
                        self.ui.pathPS1.setText(settings.emulators()[emulator]['location'])
                        self.ui.cmdPS1.setText(settings.emulators()[emulator]['command'])
                    elif consoleentry == 'Playstation 2':
                        self.ui.pathPS2.setText(settings.emulators()[emulator]['location'])
                        self.ui.cmdPS2.setText(settings.emulators()[emulator]['command'])
                    elif consoleentry == 'Sega Genesis':
                        self.ui.pathGenesis.setText(settings.emulators()[emulator]['location'])
                        self.ui.cmdGenesis.setText(settings.emulators()[emulator]['command'])
                    elif consoleentry == 'Sega Dreamcast':
                        self.ui.pathDreamcast.setText(settings.emulators()[emulator]['location'])
                        self.ui.cmdDreamcast.setText(settings.emulators()[emulator]['command'])
                    elif consoleentry == 'Nintendo Gameboy':
                        self.ui.pathGameBoy.setText(settings.emulators()[emulator]['location'])
                        self.ui.cmdGameBoy.setText(settings.emulators()[emulator]['command'])
                    elif consoleentry == 'Gameboy Advance':
                        self.ui.pathGBA.setText(settings.emulators()[emulator]['location'])
                        self.ui.cmdGBA.setText(settings.emulators()[emulator]['command'])
                    elif consoleentry == 'Nintendo DS':
                        self.ui.pathNDS.setText(settings.emulators()[emulator]['location'])
                        self.ui.cmdNDS.setText(settings.emulators()[emulator]['command'])

        except:
            print 'An error occured while loading configs'
            return

    def _saveSettings(self):
        # initialize config
        configEmulators = ConfigParser.ConfigParser()
        configEmulators.read(settings.user_emulators_path())
        configConsoles = ConfigParser.ConfigParser()
        configConsoles.read(settings.user_consoles_path())

        # check if emulator paths are empty - if so, don't save
        if self.ui.pathNES.text() != '':
            # add NES section to emulators.txt
            configEmulators.add_section('NES')
            configEmulators.set('NES', 'location', self.ui.pathNES.text())
            configEmulators.set('NES', 'command', self.ui.cmdNES.text())

            # add emulator NES to consoles.txt
            configConsoles.set('Nintendo Entertainment System', 'emulator', 'NES')

        # proceed with the rest of the support consoles
        if self.ui.pathSNES.text() != '':
            configEmulators.add_section('SNES')
            configEmulators.set('SNES', 'location', self.ui.pathSNES.text())
            configEmulators.set('SNES', 'command', self.ui.cmdSNES.text())
            configConsoles.set('Super Nintendo', 'emulator', 'SNES')
        if self.ui.pathN64.text() != '':
            configEmulators.add_section('N64')
            configEmulators.set('N64', 'location', self.ui.pathN64.text())
            configEmulators.set('N64', 'command', self.ui.cmdN64.text())
            configConsoles.set('Nintendo 64', 'emulator', 'N64')
        if self.ui.pathGameCube.text() != '':
            configEmulators.add_section('Gamecube')
            configEmulators.set('Gamecube', 'location', self.ui.pathGameCube.text())
            configEmulators.set('Gamecube', 'command', self.ui.cmdGameCube.text())
            configConsoles.set('Nintendo Gamecube', 'emulator', 'Gamecube')
        if self.ui.pathWii.text() != '':
            configEmulators.add_section('Wii')
            configEmulators.set('Wii', 'location', self.ui.pathWii.text())
            configEmulators.set('Wii', 'command', self.ui.cmdWii.text())
            configConsoles.set('Nintendo Wii', 'emulator', 'Wii')
        if self.ui.pathPS1.text() != '':
            configEmulators.add_section('PS1')
            configEmulators.set('PS1', 'location', self.ui.pathPS1.text())
            configEmulators.set('PS1', 'command', self.ui.cmdPS1.text())
            configConsoles.set('Playstation 1', 'emulator', 'PS1')
        if self.ui.pathPS2.text() != '':
            configEmulators.add_section('PS2')
            configEmulators.set('PS2', 'location', self.ui.pathPS2.text())
            configEmulators.set('PS2', 'command', self.ui.cmdPS2.text())
            configConsoles.set('Playstation 2', 'emulator', 'PS2')
        if self.ui.pathGenesis.text() != '':
            configEmulators.add_section('Genesis')
            configEmulators.set('Genesis', 'location', self.ui.pathGenesis.text())
            configEmulators.set('Genesis', 'command', self.ui.cmdGenesis.text())
            configConsoles.set('Sega Genesis', 'emulator', 'Genesis')
        if self.ui.pathDreamcast.text() != '':
            configEmulators.add_section('Dreamcast')
            configEmulators.set('Dreamcast', 'location', self.ui.pathDreamcast.text())
            configEmulators.set('Dreamcast', 'command', self.ui.cmdDreamcast.text())
            configConsoles.set('Sega Dreamcast', 'emulator', 'Dreamcast')
        if self.ui.pathGameBoy.text() != '':
            configEmulators.add_section('Gameboy')
            configEmulators.set('Gameboy', 'location', self.ui.pathGameBoy.text())
            configEmulators.set('Gameboy', 'command', self.ui.cmdGameBoy.text())
            configConsoles.set('Nintendo Gameboy', 'emulator', 'Gameboy')
        if self.ui.pathGBA.text() != '':
            configEmulators.add_section('GBA')
            configEmulators.set('GBA', 'location', self.ui.pathGBA.text())
            configEmulators.set('GBA', 'command', self.ui.cmdGBA.text())
            configConsoles.set('Gameboy Advance', 'emulator', 'GBA')
        if self.ui.pathNDS.text() != '':
            configEmulators.add_section('NDS')
            configEmulators.set('NDS', 'location', self.ui.pathNDS.text())
            configEmulators.set('NDS', 'command', self.ui.cmdNDS.text())
            configConsoles.set('Nintendo DS', 'emulator', 'NDS')

        # save configs
        configEmulators.write(open(settings.user_emulators_path(), 'wb'))
        configConsoles.write(open(settings.user_consoles_path(), 'wb'))

        # hide settings windows
        self.setVisible(False)

    def _cancel(self):
        self.setVisible(False)

    def openBinNES(self):
        self.ui.pathNES.setText(QFileDialog.getOpenFileName())
    def openBinSNES(self):
        self.ui.pathSNES.setText(QFileDialog.getOpenFileName())
    def openBinN64(self):
        self.ui.pathN64.setText(QFileDialog.getOpenFileName())
    def openBinGameCube(self):
        self.ui.pathGameCube.setText(QFileDialog.getOpenFileName())
    def openBinWii(self):
        self.ui.pathWii.setText(QFileDialog.getOpenFileName())
    def openBinPS1(self):
        self.ui.pathPS1.setText(QFileDialog.getOpenFileName())
    def openBinPS2(self):
        self.ui.pathPS2.setText(QFileDialog.getOpenFileName())
    def openBinGenesis(self):
        self.ui.pathGenesis.setText(QFileDialog.getOpenFileName())
    def openBinDreamcast(self):
        self.ui.pathDreamcast.setText(QFileDialog.getOpenFileName())
    def openBinGameBoy(self):
        self.ui.pathGameBoy.setText(QFileDialog.getOpenFileName())
    def openBinGBA(self):
        self.ui.pathGBA.setText(QFileDialog.getOpenFileName())
    def openBinNDS(self):
        self.ui.pathNDS.setText(QFileDialog.getOpenFileName())

class WindowMain(QMainWindow):
    def __init__(self, parent=None):
        QMainWindow.__init__(self, parent)

        self.ui = ui_windowMain.Ui_MainWindow()
        self.ui.setupUi(self)

        # actions
        QtCore.QObject.connect(self.ui.actionQuit, QtCore.SIGNAL("triggered()"), self._exitApp)
        QtCore.QObject.connect(self.ui.btnRunIce, QtCore.SIGNAL("pressed()"), self.startIce)
        QtCore.QObject.connect(self.ui.btnSettings, QtCore.SIGNAL("pressed()"), self.showSettings)

        # multiple windows
        self.windowSettings = WindowSettings()

    def startIce(self):
        # very similar to the one in ice.py
        try:
            if steam_is_running():
                ice_logger.log_error("Ice cannot be run while Steam is open. Please close Steam and try again")
                return
            ice_logger.log("Starting Ice")
            fs.create_directory_if_needed(fs.roms_directory(), log="Creating ROMs directory at %s" % fs.roms_directory())
            # Find all of the ROMs that are currently in the designated folders
            roms = console.find_all_roms()
            # Find the Steam Account that the user would like to add ROMs for
            user_ids = steam_user_manager.user_ids_on_this_machine()
            grid_manager = IceGridImageManager()
            for user_id in user_ids:
                ice_logger.log("Running for user %s" % str(user_id))
                # Load their shortcuts into a SteamShortcutManager object
                shortcuts_path = steam_user_manager.shortcuts_file_for_user_id(user_id)
                shortcuts_manager = SteamShortcutManager(shortcuts_path)
                rom_manager = IceROMManager(shortcuts_manager)
                # Add the new ROMs in each folder to our Shortcut Manager
                rom_manager.sync_roms(roms)
                # Generate a new shortcuts.vdf file with all of the new additions
                shortcuts_manager.save()
                if IceGridImageManager.should_download_images():
                    ice_logger.log("Downloading grid images")
                    grid_manager.update_user_images(user_id,roms)
                else:
                    ice_logger.log("Skipping 'Download Image' step")
            ice_logger.log("Finished")
        except ConfigError as error:
            ice_logger.log_error('Stopping')
            ice_logger.log_config_error(error)
            ice_logger.log_exception()
        except StandardError as error:
            ice_logger.log_error("An Error has occurred:")
            ice_logger.log_exception()

    def showSettings(self):
        self.windowSettings.setVisible(True)

    def _exitApp(self):
        self.close()




# initialize gui
qtApp = QApplication(sys.argv)
qtWindow = WindowMain()

########NEW FILE########
__FILENAME__ = ice_logging
#!/usr/bin/env python
# encoding: utf-8
"""
IceLogging.py

Created by Scott on 2013-01-24.
Copyright (c) 2013 Scott Rice. All rights reserved.
"""

import sys
import os
import time
import traceback
import settings

import logging
import logging.handlers

class IceLogger():
    ''' initialize our loggers '''
    def __init__(self):
        # steam handler (only print info messages to terminal)
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        ch.setFormatter(logging.Formatter('%(asctime)s (%(name)s) %(levelname)s: %(message)s'))

        # logfile handler (print all messages to logfile)
        # - max file size of 1mb
        # - log file is stored in root ice folder and is named 'ice.log'
        fh = logging.handlers.RotatingFileHandler(filename='ice.log', maxBytes=1048576, backupCount=5)
        fh.setLevel(logging.INFO)
        fh.setFormatter(logging.Formatter('%(asctime)s (%(name)s) %(levelname)s: %(message)s'))

        # loggers
        self.logger = logging.getLogger('ice')
        self.logger.setLevel(logging.INFO)
        self.logger.addHandler(ch)
        self.logger.addHandler(fh)

    def log(self, message):
        self.logger.info(message)

    def log_debug(self, message):
        self.logger.debug(message)

    def log_warning(self, message):
        self.logger.warning(message)

    def log_error(self, message):
        self.logger.error(message)

    # premade logs
    def log_config_error(self, error):
        self.logger.error("There was a problem with '[%s] %s' in %s" % (error.section, error.key, error.file))
        config = settings.settings_for_file(error.file)
        try:
            self.logger.error("The current value is set to '%s'" % config[error.section][error.key.lower()])
        except KeyError as e:
            if e.message == error.section:
                self.logger.error("No section found named '[%s]'" % e.message)
            else:
                self.logger.error("The key '%s' is missing" % e.message)
        self.logger.error(error.fix_instructions)

    def log_exception(self):
        self.logger.exception("An exception occured!")


# create our IceLogger object
ice_logger = IceLogger()


########NEW FILE########
__FILENAME__ = platform_helper
#!/usr/bin/env python
# encoding: utf-8
"""
platform.py

Created by Scott on 2012-12-24.
Copyright (c) 2012 Scott Rice. All rights reserved.

This file contains functions that help deal with multiple platforms.

Code should be added to this file if it helps support multiple platforms. This
does NOT include code that does platform specific things. A function which gets
a string to represent the platform is a good candidate for this file. A
function that executes some command on windows but some other command on osx
is not a good candidate for this file. In that case, each platform should have
a separate function, and the `platform_specific` function should be used to
select the correct one
"""

import sys


def is_windows():
	return sys.platform.startswith('win')

def is_osx():
	return sys.platform.startswith('darwin')

def is_linux():
    return str(sys.platform).startswith('lin')

def to_string():
    if is_windows():
        return "Windows"
    elif is_osx():
        return "OSX"
    elif is_linux():
        return "Linux"

def _platform_specific_default():
	raise StandardError("The developer didn't test this thoroughly on your platform. Please submit an issue to github.com/scottrice/Ice")

def platform_specific(windows=_platform_specific_default, osx=_platform_specific_default, linux=_platform_specific_default):
	if is_windows():
		return windows
	elif is_osx():
		return osx
	elif is_linux():
		return linux

########NEW FILE########
__FILENAME__ = process_helper
#!/usr/bin/env python
# encoding: utf-8
"""
process_helper.py

Created by Scott on 2013-06-03.
Copyright (c) 2013 Scott Rice. All rights reserved.
"""

import subprocess

import platform_helper as pf
from ice_logging import ice_logger

def windows_steam_is_running():
    """(Windows) Checks if Steam is currently running."""
    return "Steam.exe" in subprocess.check_output("tasklist", shell=True)

def osx_steam_is_running():
    """(OS X) Checks if Steam is currently running."""
    return "Steam.app\n" in subprocess.check_output("ps -A", shell=True)

def linux_steam_is_running():
    """(Linux) Checks if Steam is currently running."""
    return "steam" in subprocess.check_output("ps -A", shell=True)

def steam_is_running():
  check_function = pf.platform_specific(windows=windows_steam_is_running, osx=osx_steam_is_running, linux=linux_steam_is_running)
  try:
    return check_function()
  except:
    ice_logger.log_warning('Could not determine if Steam is running. Make sure Steam is closed before running Ice.')
    return False
########NEW FILE########
__FILENAME__ = rom
#!/usr/bin/env python
# encoding: utf-8
"""
IceROM.py

Created by Scott on 2012-12-24.
Copyright (c) 2012 Scott Rice. All rights reserved.

ROM model. Handles the collection of data that makes up a ROM (as of right now,
just the path to the ROM and what console is is from). Also contains some
convenience methods for the filesystem. 

Functionality should be added to this class if it heavily involves the use of
ROMs
"""

import sys
import os
import stat
import unicodedata

import platform_helper as pf
from steam_shortcut_manager import SteamShortcut

class ROM:
    def __init__(self,path,console):
        self.path = path
        self.console = console

    def __repr__(self):
        return self.name()

    def __eq__(self,other):
        return self.path == other.path and self.console == other.console
        
    def name(self):
        name_with_ext = os.path.basename(self.path)

        # normalize the name to get rid of symbols that break the shortcuts.vdf
        name_with_ext = unicodedata.normalize('NFKD', unicode(name_with_ext.decode('utf-8'))).encode('ascii', 'ignore')

        dot_index = name_with_ext.rfind('.')
        if dot_index == -1:
            # There is no period, so there is no extension. Therefore, the
            # name with extension is the name
            return name_with_ext
        # Return the entire string leading up to (but not including) the period
        return name_with_ext[:dot_index]

    def prefixed_name(self):
        prefix = self.console.prefix
        if prefix:
            return "%s %s" % (prefix, self.name())
        else:
            return self.name()
        
    def to_shortcut(self):
        appname = self.prefixed_name()
        exe = self.console.emulator.command_string(self)
        startdir = self.console.emulator.startdir(self)
        icon = self.console.icon
        category = self.console.fullname
        return SteamShortcut(appname,exe,startdir,icon,category)

########NEW FILE########
__FILENAME__ = rom_manager
#!/usr/bin/env python
# encoding: utf-8
"""
IceROMManager.py

Created by Scott on 2012-12-24.
Copyright (c) 2012 Scott Rice. All rights reserved.

The purpose of this class is to handle the interaction (or some would say 
conversion) between ROMs and Steam Shortcuts. This class also handles checking
to make sure I don't add duplicates of any ROMs to Steam.

Functionality should be added to this class if it involves the interaction
between ROMs and Steam Shortcuts.
"""

import os

import filesystem_helper
import steam_user_manager
from console import supported_consoles
from ice_logging import ice_logger
from steam_grid import SteamGrid

class IceROMManager():
    def __init__(self,shortcut_manager):
        """
        Takes an already initialized SteamShortcutsManager. Then does a O(n)
        computation to figure out which ROMs from Ice are already present and
        caches that result. That way, adding a ROM to the SteamShortcutsManager
        can be a O(1) lookup to see if the ROM is already managed, and a O(1)
        addition to the list (if it does not exist)
        
        Stores the managed ROMs in a set to optimize time complexity. See
        http://wiki.python.org/moin/TimeComplexity
        for details
        """
        self.shortcut_manager = shortcut_manager
        self.managed_shortcuts = set()
        for shortcut in self.shortcut_manager.shortcuts:
            if self.__is_managed_by_ice__(shortcut):
                self.managed_shortcuts.add(shortcut)
    
    def __is_managed_by_ice__(self,shortcut):
        """
        We determine whether a shortcut is managed by ice by whether the app
        directory location is contained in the target string. The way I see it,
        a target that uses Ice will either point to an emulator (which is
        contained in the app dir), or to an Ice exectuable (again, contained
        in the Ice dir). Obviously if we add a method of executing roms which
        doesn't involve the app dir, this method will need to be rethought.
        """
        for console in supported_consoles():
            if console.roms_directory() in shortcut.exe:
                return True
        return False
        
    def rom_already_in_steam(self,rom):
        """
        To check whether a ROM is already managed by Steam, we generate a
        Shortcut for that ROM, and then figure out whether an equal ROM exists
        in our Shortcut Manager.
        """
        generated_shortcut = rom.to_shortcut()
        return generated_shortcut in self.managed_shortcuts
        
    def add_rom(self,rom):
        # Don't add a ROM if we don't have a supported emulator for it
        if rom.console.emulator is None:
            return
        if not self.rom_already_in_steam(rom):
            ice_logger.log("Adding %s" % rom.name())
            generated_shortcut = rom.to_shortcut()
            self.managed_shortcuts.add(generated_shortcut)
            self.shortcut_manager.add(generated_shortcut)
            
    def remove_deleted_roms_from_steam(self,roms):
        # We define 'has been deleted' by checking whether we have a shortcut
        # that was managed by Ice in Steam that is no longer in our ROM folders
        rom_shortcuts = set()
        for rom in roms:
            rom_shortcuts.add(rom.to_shortcut())
        deleted_rom_shortcuts = self.managed_shortcuts - rom_shortcuts
        for shortcut in deleted_rom_shortcuts:
            ice_logger.log("Deleting: %s" % shortcut.appname)
            self.shortcut_manager.shortcuts.remove(shortcut)
            
    def sync_roms(self,roms):
        """
        Two parts to syncing. 
        1) Remove any ROMs which have been deleted
        2) Add any new ROMs
        """
        # 1)
        self.remove_deleted_roms_from_steam(roms)
        # 2)
        for rom in roms:
            self.add_rom(rom)
            
    def update_artwork(self,user_id,roms):
        grid = SteamGrid(steam_user_manager.userdata_directory_for_user_id(user_id))
        for rom in roms:
            pass

########NEW FILE########
__FILENAME__ = settings
#!/usr/bin/env python
# encoding: utf-8
"""
settings.py

Created by Scott on 2012-12-24.
Copyright (c) 2012 Scott Rice. All rights reserved.

Basic settings to be used by the app.
"""

import ConfigParser

appname = "Ice"
appdescription = "ROM Manager for Steam"
appauthor = "Scott Rice"

config_dict = None
consoles_dict = None
emulators_dict = None

def user_settings_path():
  return "config.txt"

def user_consoles_path():
  return "consoles.txt"

def user_emulators_path():
  return "emulators.txt"

def _config_file_to_dictionary(path):
  config = ConfigParser.ConfigParser()
  config.read(path)
  settings = {}
  for section in config.sections():
    settings[section] = {}
    for option in config.options(section):
      settings[section][option] = config.get(section,option)
  return settings

def config():
  global config_dict
  if config_dict == None:
    config_dict = _config_file_to_dictionary(user_settings_path())
  return config_dict

def consoles():
  global consoles_dict
  if consoles_dict == None:
    consoles_dict = _config_file_to_dictionary(user_consoles_path())
  return consoles_dict

def emulators():
  global emulators_dict
  if emulators_dict == None:
    emulators_dict = _config_file_to_dictionary(user_emulators_path())
  return emulators_dict

def settings_for_file(file):
  return {
    "config.txt": config(),
    "consoles.txt": consoles(),
    "emulators.txt": emulators(),
  }[file]
########NEW FILE########
__FILENAME__ = steam_grid
#!/usr/bin/env python
# encoding: utf-8
#
# Copyright (c) 2012-2013, 2013 Scott Rice
# All rights reserved.
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.
#
# SteamGridImageManager is meant to make setting the grid image of a given
# Steam shortcut super easy. Ideally, the user won't need to know anything
# about how steam grid images work, just mention the name and target and we
# will handle the rest
#

import os
import shutil
import crc_algorithms

class SteamGrid(object):
  
  def __init__(self,user_directory):
    """
    Sets up a SteamGridImageManager given the userdata directory for a given
    user.
    """
    self.user_directory = user_directory
    self.grid_image_directory = os.path.join(self.user_directory,"config","grid")
    # Make sure that the Grid Image directory exists
    if not os.path.exists(self.grid_image_directory):
        os.makedirs(self.grid_image_directory)
    
  def filename_for_shortcut(self,name,target):
    """
    Calculates the filename for a given shortcut. This filename is a 64bit
    integer, where the first 32bits are a CRC32 based off of the name and
    target (with the added condition that the first bit is always high), and
    the last 32bits are 0x02000000.
    """
    # This will seem really strange (where I got all of these values), but I
    # got the xor_in and xor_out from disassembling the steamui library for 
    # OSX. The reflect_in, reflect_out, and poly I figured out via trial and
    # error.
    algorithm = crc_algorithms.Crc(width = 32, poly = 0x04C11DB7, reflect_in = True, xor_in = 0xffffffff, reflect_out = True, xor_out = 0xffffffff)
    input_string = ''.join([target,name])
    top_32 = algorithm.bit_by_bit(input_string) | 0x80000000
    full_64 = (top_32 << 32) | 0x02000000
    return str(full_64)
    
  def filename_for_app(self,appid):
    """
    Calculates the filename for a given app. This is just the AppID
    """
    # Easy peasy
    return str(appid)
    
  def full_path_for_filename(self,filename,extension):
    """
    Returns the full, absolute, path to the shortcut. A shortcut is located in
    the userdata/{user_id}/config/grid/{generated_filename}.{extension}
    """
    filename_with_ext = "%s%s" % (filename,extension)
    return os.path.join(self.grid_image_directory,filename_with_ext)
    
  def existing_image_for_filename(self,filename):
    """
    Returns the path for an existing image. There are 4 possible paths an 
    existing image can be at, one for each extension. Returns the one that 
    actually exists
    """
    valid_exts = [".jpg",".jpeg",".png",".tga"]
    for ext in valid_exts:
      full_path = self.full_path_for_filename(filename,ext)
      if os.path.exists(full_path):
        return full_path
    return None
  
  def set_image_for_filename(self,image_path,filename):
    """
    Sets the image at 'image_path' to be the current application grid image for
    the given filename
    """
    # Delete the current image if there is one
    current_image = self.existing_image_for_filename(filename)
    if current_image:
      os.remove(current_image)
    # Set the new image
    _ , extension = os.path.splitext(image_path)
    grid_filepath = self.full_path_for_filename(filename,extension)
    # Copy the file
    shutil.copyfile(image_path,grid_filepath)
    
  def set_image_for_shortcut(self,image_path,name,target):
    """
    Sets the image at 'image_path' to be the current application grid image 
    for the shortcut defined by 'name' and 'target'
    """
    self.set_image_for_filename(image_path,self.filename_for_shortcut(name,target))
    
  def set_image_for_app(self,image_path,appid):
    """
    Sets the image at 'image_path' to be the current application grid image 
    for the app defined by 'appid'
    """
    self.set_image_for_filename(image_path,self.filename_for_app(appid))
########NEW FILE########
__FILENAME__ = steam_installation_location_manager
#!/usr/bin/env python
"""
steam_installation_location_manager.py

Created by Scott on 2012-12-20.
Copyright (c) 2012 Scott Rice. All rights reserved.

The purpose of this class is to abstract away finding/storing the install
location of Steam. A corrolary of this is that it should be easy to find the
shortcuts.vdf file, which is obviously useful for Ice
"""

import os

import platform_helper as pf
import settings

# Used to find the shortcuts.vdf file
osx_userdata_directory = "~/Library/Application Support/Steam/userdata/"
linux_userdata_directory = "~/.local/share/Steam/userdata/"

def config_userdata_location():
    return os.path.expanduser(settings.config()["Steam"]["userdata directory"])

def windows_steam_location():
    import _winreg as registry
    key = registry.CreateKey(registry.HKEY_CURRENT_USER,"Software\Valve\Steam")
    return registry.QueryValueEx(key,"SteamPath")[0]

def windows_userdata_location():
    # On Windows, the userdata directory is the steam installation directory
    # with 'userdata' appended
    if config_userdata_location() == "":
        try:
            out = os.path.join(windows_steam_location(),"userdata")
        except WindowsError:
            raise IOError("Steam installation not found\n"
                          "Please reinstall Steam or configure its userdata directory in config.txt")
    else:
        out = config_userdata_location()
    return out

def osx_userdata_location():
    # I'm pretty sure the user can't change this on OS X. I think it always
    # goes to the same location
    if config_userdata_location() == "":
        out = os.path.expanduser(osx_userdata_directory)
    else:
        out = config_userdata_location()
    if not os.path.exists(out):
        raise IOError("Steam userdata directory not found in location:\n" + out +
                      "\nPlease configure Steam's userdata directory in config.txt")
    return out

def linux_userdata_location():
    if config_userdata_location() == "":
        out = os.path.expanduser(linux_userdata_directory)
    else:
        out = config_userdata_location()
    if not os.path.exists(out):
        raise IOError("Steam userdata directory not found in location:\n" + out +
                      "\nPlease configure Steam's userdata directory in config.txt")
    return out

steam_userdata_location = pf.platform_specific(windows=windows_userdata_location, osx=osx_userdata_location, linux=linux_userdata_location)

########NEW FILE########
__FILENAME__ = steam_shortcut_manager
#!/usr/bin/env python
# encoding: utf-8
"""
steam_shortcut_manager.py

Created by Scott on 2012-12-20.
Copyright (c) 2012 Scott Rice. All rights reserved.
"""

import sys
import os
import unicodedata
import re
from datetime import datetime
import settings
from ice_logging import ice_logger


x00 = u'\x00'
x01 = u'\x01'
x08 = u'\x08'
x0a = u'\x0a'

class SteamShortcut:
    def __init__(self,appname,exe,startdir,icon,tag):
        self.appname = appname
        self.exe = unicodedata.normalize('NFKD', unicode(exe.decode('utf-8'))).encode('ascii', 'ignore')
        self.startdir = startdir
        self.icon = icon
        self.tag = tag
        
    def __eq__(self,other):
        return (
            isinstance(other,self.__class__) and
            self.appname == other.appname and
            self.exe == other.exe and
            self.startdir == other.startdir and
            self.icon == other.icon and
            self.tag == other.tag
        )
    
    def __ne__(self,other):
        return not self.__eq__(other)
        
    def __hash__(self):
        return "__STEAMSHORTCUT{0}{1}{2}{3}{4}__".format(self.appname,self.exe,self.startdir,self.icon,self.tag).__hash__()
        
    def __repr__(self):
        return "Steam Shortcut: %s" % self.appname


# This class is in charge of outputting a valid shortcuts.vdf file given an
# array of SteamShortcut objects. This allows normal python code to interact
# with Steam's Non-Steam game list.
class SteamShortcutFileFormatter():
    def generate_string(self,shortcuts):
        string = x00 + 'shortcuts' + x00 + self.generate_array_string(shortcuts) + x08 + x08 + x0a
        # rstrip is to remove the eol character that is automatically added.
        # According to vim the files I got from steam don't have the eol character
        return unicode(string).rstrip()
        
    def generate_array_string(self,shortcuts):
        string = ""
        for i in range(len(shortcuts)):
            shortcut = shortcuts[i]
            string += x00 + str(i) + x00 + self.generate_shortcut_string(shortcut)
        return string
            
    def generate_shortcut_string(self,shortcut):
        string = ""
        string += self.generate_keyvalue_pair("AppName",shortcut.appname)
        string += self.generate_keyvalue_pair("Exe",shortcut.exe)
        string += self.generate_keyvalue_pair("StartDir",shortcut.startdir)
        string += self.generate_keyvalue_pair("icon",shortcut.icon)
        # Tags seem to be a special case. It seems to be a key-value pair just
        # like all the others, except it doesnt start with a x01 character. It
        # also seems to be an array, even though Steam wont let more than one
        # be used. I am just going to use a special function to represent this
        # strange case
        string += self.generate_tags_string(shortcut.tag)
        string += x08
        return string
        
    # The 'more' variable was for when I used this function to generate tags
    # I'm not sure if tags are a special case, or if dictionaries keyvalues are
    # supposed to end in x00 when there are more and x08 when there arent. Since
    # I am not sure, I am going to leave the code in for now
    def generate_keyvalue_pair(self,key,value,more=True):
        return x01 + key + x00 + value + (x00 if more else x08)
    
    def generate_tags_string(self,tag):
        string = x00 + "tags" + x00
        if tag == "":
            string += x08
        else:
            string += self.generate_tag_array_string([tag])
        return string
        
    def generate_tag_array_string(self,tags):
        string = ""
        for i in range(len(tags)):
            tag = tags[i]
            string += x01 + str(i) + x00 + str(tag) + x00 + x08
        return string
        
# This class is in charge of parsing a shortcuts.vdf file into an array which
# can be easily manipulated with python code.
class SteamShortcutFileParser():
    # I am going to use regular expressions to parse this file. I haven't used
    # regular expressions in Python before, so I apologize for any terrible
    # code that I write...
    def parse(self,string):
        return self.match_base(string)
        
    def match_base(self,string):
        match = re.match(ur"\u0000shortcuts\u0000(.*)\u0008\u0008$",string, re.IGNORECASE)
        if match:
            return self.match_array_string(match.groups()[0])
        else:
            return None
    
    def match_array_string(self,string):
        # Match backwards (aka match last item first)
        if string == "":
            return []
        # One side effect of matching this way is we are throwing away the
        # array index. I dont think that it is that important though, so I am
        # ignoring it for now
        shortcuts = []
        while True:
            match = re.match(ur"(.*)\u0000[0-9]+\u0000(\u0001AppName.*)\u0008",string, re.IGNORECASE)
            if match:
                groups = match.groups()
                string = groups[0]
                shortcuts.append(self.match_shortcut_string(groups[1]))
            else:
                shortcuts.reverse()
                return shortcuts
            
    def match_shortcut_string(self,string):
        # I am going to cheat a little here. I am going to match specifically
        # for the shortcut string (Appname, Exe, StartDir, etc), as oppposed
        # to matching for general Key-Value pairs. This could possibly create a
        # lot of work for me later, but for now it will get the job done
        match = re.match(ur"\u0001AppName\u0000(.*)\u0000\u0001Exe\u0000(.*)\u0000\u0001StartDir\u0000(.*)\u0000\u0001icon\u0000(.*)\u0000\u0000tags\u0000(.*)\u0008",string, re.IGNORECASE)
        if match:
            # The 'groups' that are returned by the match should be the data
            # contained in the file. Now just make a SteamShortcut out of that
            # data
            groups = match.groups()
            appname = groups[0]
            exe = groups[1]
            startdir = groups[2]
            icon = groups[3]
            tags = self.match_tags_string(groups[4])
            return SteamShortcut(appname,exe,startdir,icon,tags)
        else:
            return None
            
    def match_tags_string(self,string):
        match = re.match(ur"\u00010\u0000(.*)\u0000",string)
        if match:
            groups = match.groups()
            return groups[0]
        else:
            return ""

class SteamShortcutManager():
    
    def __init__(self,file=None):
        self.shortcuts = []
        if file != None:
            self.__load_shortcuts__(file)
            
    def __eq__(self,other):
        return (isinstance(other,self.__class__) and self.shortcuts == other.shortcuts)
        
    def __ne__(self,other):
        return not self.__eq__(other)
            
    def __load_shortcuts__(self,file):
        self.shortcuts_file = file
        try:
            file_contents = open(file,"r").read()
            parsed_shortcuts = SteamShortcutFileParser().parse(file_contents)
            if parsed_shortcuts == None:
                print "Parsing error on file: %s" % file
        except IOError:
            file_contents = ""
            parsed_shortcuts = []
        self.shortcuts = parsed_shortcuts
        # self.games = SteamShortcutFileParser().parse(file_contents)
        
    def save(self,file=None):
        # print "Write to file: %s" % self.shortcuts_file
        # print self.to_shortcuts_string()
        # If they just called save(), then overwrite the file that was used to
        # generate the manager.
        if not file:
            file = self.shortcuts_file
        # If file is still undefined, then we have no idea where to save it, so
        # we just return after printing an error
        if not file:
            print "SteamShortcutManager Save Error: No file specified"
            return None
        open(file,"w").write(self.to_shortcuts_string())

    def backup(self,backup_location=None):
        # If they just called backup(), then use the path specified in the config
        if not backup_location:
            backup_location = settings.config()["Storage"]["backup directory"]
        # If backup_location is still undefined, then we have no idea where to do the backup, so
        # we just return after printing a message
        if not backup_location:
            ice_logger.log("No backup location specified. Not creating backup file.")
            return None

        # If the shortcuts file is undefined, print an error and return
        if not self.shortcuts_file:
            print "SteamShortcutManager Backup Error: No file specified"
            return None

        # Get the user id using the location of the shortcuts file and create a directory
        # in the backup location using the same directory structure Steam uses
        user_id = os.path.split(os.path.dirname(os.path.dirname(self.shortcuts_file)))[1]
        new_dir = os.path.expanduser(os.path.join(os.path.join(backup_location,user_id),"config"))
        try:  # Handle possible race condition
            os.makedirs(new_dir)
        except OSError:
            if not os.path.isdir(new_dir):
                raise

        backup_file_name = "shortcuts." + datetime.now().strftime('%Y%m%d%H%M%S') + ".vdf"
        open(os.path.join(new_dir,backup_file_name),"w").write(open(self.shortcuts_file,"r").read())


    def add(self,shortcut):
        self.shortcuts.append(shortcut) 
            
    def add_shortcut(self,appname,exe,startdir,icon="",tag=""):
        shortcut = SteamShortcut(appname,exe,startdir,icon,tag)
        self.add(shortcut)
        
    def to_shortcuts_string(self):
        return SteamShortcutFileFormatter().generate_string(self.shortcuts)

########NEW FILE########
__FILENAME__ = steam_user_manager
#!/usr/bin/env python
# encoding: utf-8
"""
steam_user_manager.py

Created by Scott on 2012-12-23.
Copyright (c) 2012 Scott Rice. All rights reserved.

The purpose of this class is to handle anything related to Steam user accounts
A big part of that is abstracting away the conversion between Steam usernames
and Steam IDs. It should also be able to determine the path to the userdata 
folder for a given user (finding the directory containing all of the different
userdata folders should be the job of the steam_installation_location_manager) 

Functionality should be added to this module if two conditions are met. The
first is if it is related at all to Steam User accounts, and the second is if
it doesn't involve Ice in any way. If there is functionality related to Steam
Users, but it involves Ice, it should most likely go in the filesystem_helper
(as the filesystem is a big reason Ice needs to know about Steam users)
"""

import os

import httplib

import steam_installation_location_manager

name_to_id_cache = {}
id_to_name_cache = {}

###############################################################################
# Most of the information used in the following 4 methods I obtained via this
# super helpful documentation page. Thank you Valve!
# https://developer.valvesoftware.com/wiki/SteamID
###############################################################################

# This is the V value that is used for individuals. Since we are only 
# converting things for users, we can just hard code it
__v_value__ = 0x0110000100000000

def communityid64_from_name(username):
    """
    The 64 bit id can be retrieved by making a request to the following URL
    http://steamcommunity.com/id/{name}?xml=1
    
    This returns XML, with the 64bit Steam Community ID as an element.
    
    This method also caches the value for a user, so I don't hit the network
    like 8 times trying to do something simple
    """
    if username not in name_to_id_cache:
        # Sometimes Steam will randomly give me a 503 service unavailable.
        # Keep attempting to reach Steam until it gives me a 200
        while True:
            conn = httplib.HTTPConnection("steamcommunity.com")
            url = "/id/%s?xml=1" %  username
            conn.request("GET",url)
            response = conn.getresponse()
            if response.status != 503:
                break
        xml_string = response.read()
        # Rather than parse the XML (which has the possibility of being quite slow,
        # along with adding a dependency on an XML parser), I will instead just do
        # some simple string searching to find the open and close tags for the
        # steamID64 element.
        id_start = xml_string.find("<steamID64>") + len("<steamID64>")
        id_end = xml_string.find("</steamID64>")
        name_to_id_cache[username] = int(xml_string[id_start:id_end])
    return name_to_id_cache[username]

def __y_value__(username):
    """
    Y is either 0 or 1 based on whether the 64 bit community id is even or odd.
    According to the documentation, if W is even then Y is 1, if W is odd Y is
    0. This is the same as doing a binary AND operation between W and 1
    """
    return communityid64_from_name(username) & 1

def steam_id_from_name(username):
    """
    Reverse engineering the Steam ID of a user revolves around the formula
    W = Z * 2 + V + Y, where
    W = The 64 bit Community ID for the user
    Z = The Steam User ID
    V = The 64 bit Steam Account Type Identifier (0x0110000100000000 for users)
    Y = Either 0 or 1, can be determined based on whether W is even or odd
    
    Doing some arithmatic, the formula turns in to Z = (W - V - Y) / 2
    
    Returns Z from the above formula
    """
    w = communityid64_from_name(username)
    v = __v_value__
    y = __y_value__(username)
    z = (w - v - y) / 2
    return z

def communityid32_from_name(username):
    """
    Calculated based on the formula W = Z * 2 + Y where
    W = The 32 bit Community ID for the user
    Z = The Steam ID for the user
    Y = 1 or 0 based on whether W is even or odd
    """
    z = steam_id_from_name(username)
    y = __y_value__(username)
    return (z * 2) + y
    
def name_from_communityid32(user_id):
    w = user_id
    y = w & 1
    z = (w - y) / 2
    v = __v_value__
    return name_from_communityid64((z * 2) + v + y)

def name_from_communityid64(user_id):
    """
    Makes a request to http://steamcommunity.com/profiles/{id64}, which then
    sets the 'location' header variable to the correct location.
    """
    if user_id not in id_to_name_cache:
        while True:
            conn = httplib.HTTPConnection("steamcommunity.com")
            url = "/profiles/%s" % str(user_id)
            conn.request("HEAD",url)
            response = conn.getresponse()
            if response.status != 503:
                break
        # profile_url is of the form "http://steamcommunity.com/id/{username}/"
        profile_url = response.getheader("location")
        # Chop off the beginning of profile url, such that only the name remains
        # The 29 should chop off http://steamcommunity.com/id/ and the -1 should
        # chop off the trailing /
        id_to_name_cache[user_id] = profile_url[29:-1]
    return id_to_name_cache[user_id]

def userdata_directory_for_name(username):
    """
    The userdata directory uses the 32 bit community id as a unique identifier
    for the folders. This function uses that fact and returns the folder by
    converting the name into a 32 bit community id, and then using the
    userdata_directory_for_user_id function to return the directory
    """
    return userdata_directory_for_user_id(communityid32_from_name(username))

def userdata_directory_for_user_id(user_id):
    """
    Returns the path to the userdata directory for a specific user
    
    The userdata directory is where Steam keeps information specific to certain
    users. Of special note for Ice is the config/shortcuts.vdf file, which
    contains all of the 'Non-Steam Games' shortcuts.
    """
    return os.path.join(steam_installation_location_manager.steam_userdata_location(),str(user_id))
    
def shortcuts_file_for_user_id(user_id):
    """
    Returns the path to the shortcuts.vdf file for a specific user
    
    This is really just a convenience method, as it just calls
    userdata_directory_for_user_id, and then adds the path element
    /config/shortcuts.vdf to the result
    """
    return os.path.join(os.path.join(userdata_directory_for_user_id(user_id),"config"),"shortcuts.vdf")
    
def user_ids_on_this_machine():
    """
    Reads the userdata folder to find a list of IDs of Users on this machine.
    This function returns the user_ids in the communityid32 format, so use
    those related methods to convert to other formats
    
    The userdata folder contains a bunch of directories that are all 32 bit
    community ids, so to find a list of ids on the machine we simply find a
    list of subfolders inside the userdata folder
    """
    ids = []
    userdata_dir = steam_installation_location_manager.steam_userdata_location()
    for entry in os.listdir(userdata_dir):
        if os.path.isdir(os.path.join(userdata_dir,entry)):
            ids.append(int(entry))
    return ids
########NEW FILE########
__FILENAME__ = ui_windowMain
# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'windowMain.ui'
#
# Created: Thu Oct 10 10:15:01 2013
#      by: PyQt4 UI code generator 4.10.3
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtGui.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName(_fromUtf8("MainWindow"))
        MainWindow.resize(535, 173)
        self.centralwidget = QtGui.QWidget(MainWindow)
        self.centralwidget.setObjectName(_fromUtf8("centralwidget"))
        self.verticalLayout_2 = QtGui.QVBoxLayout(self.centralwidget)
        self.verticalLayout_2.setObjectName(_fromUtf8("verticalLayout_2"))
        self.btnRunIce = QtGui.QPushButton(self.centralwidget)
        self.btnRunIce.setObjectName(_fromUtf8("btnRunIce"))
        self.verticalLayout_2.addWidget(self.btnRunIce)
        self.btnSettings = QtGui.QPushButton(self.centralwidget)
        self.btnSettings.setObjectName(_fromUtf8("btnSettings"))
        self.verticalLayout_2.addWidget(self.btnSettings)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtGui.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 535, 28))
        self.menubar.setObjectName(_fromUtf8("menubar"))
        self.menu_File = QtGui.QMenu(self.menubar)
        self.menu_File.setObjectName(_fromUtf8("menu_File"))
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtGui.QStatusBar(MainWindow)
        self.statusbar.setObjectName(_fromUtf8("statusbar"))
        MainWindow.setStatusBar(self.statusbar)
        self.actionQuit = QtGui.QAction(MainWindow)
        self.actionQuit.setObjectName(_fromUtf8("actionQuit"))
        self.menu_File.addSeparator()
        self.menu_File.addAction(self.actionQuit)
        self.menubar.addAction(self.menu_File.menuAction())

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(_translate("MainWindow", "Ice", None))
        self.btnRunIce.setText(_translate("MainWindow", "Run Ice", None))
        self.btnSettings.setText(_translate("MainWindow", "Change emulator settings", None))
        self.menu_File.setTitle(_translate("MainWindow", "&File...", None))
        self.actionQuit.setText(_translate("MainWindow", "&Quit", None))


########NEW FILE########
__FILENAME__ = ui_windowSettings
# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'windowSettings.ui'
#
# Created: Thu Oct 10 10:46:46 2013
#      by: PyQt4 UI code generator 4.10.3
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtGui.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig)

class Ui_windowSettings(object):
    def setupUi(self, windowSettings):
        windowSettings.setObjectName(_fromUtf8("windowSettings"))
        windowSettings.resize(770, 230)
        self.centralwidget = QtGui.QWidget(windowSettings)
        self.centralwidget.setObjectName(_fromUtf8("centralwidget"))
        self.gridLayout_3 = QtGui.QGridLayout(self.centralwidget)
        self.gridLayout_3.setObjectName(_fromUtf8("gridLayout_3"))
        self.verticalLayout_2 = QtGui.QVBoxLayout()
        self.verticalLayout_2.setObjectName(_fromUtf8("verticalLayout_2"))
        self.tabWidget = QtGui.QTabWidget(self.centralwidget)
        self.tabWidget.setObjectName(_fromUtf8("tabWidget"))
        self.tabNES = QtGui.QWidget()
        self.tabNES.setObjectName(_fromUtf8("tabNES"))
        self.gridLayout = QtGui.QGridLayout(self.tabNES)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.label_4 = QtGui.QLabel(self.tabNES)
        self.label_4.setObjectName(_fromUtf8("label_4"))
        self.gridLayout.addWidget(self.label_4, 1, 0, 1, 1)
        self.label_5 = QtGui.QLabel(self.tabNES)
        self.label_5.setObjectName(_fromUtf8("label_5"))
        self.gridLayout.addWidget(self.label_5, 4, 0, 1, 1)
        self.pathNES = QtGui.QLineEdit(self.tabNES)
        self.pathNES.setObjectName(_fromUtf8("pathNES"))
        self.gridLayout.addWidget(self.pathNES, 1, 1, 1, 1)
        self.openBinNES = QtGui.QPushButton(self.tabNES)
        self.openBinNES.setObjectName(_fromUtf8("openBinNES"))
        self.gridLayout.addWidget(self.openBinNES, 1, 2, 1, 1)
        self.cmdNES = QtGui.QLineEdit(self.tabNES)
        self.cmdNES.setObjectName(_fromUtf8("cmdNES"))
        self.gridLayout.addWidget(self.cmdNES, 4, 1, 1, 1)
        self.tabWidget.addTab(self.tabNES, _fromUtf8(""))
        self.tabSNES = QtGui.QWidget()
        self.tabSNES.setObjectName(_fromUtf8("tabSNES"))
        self.gridLayout_2 = QtGui.QGridLayout(self.tabSNES)
        self.gridLayout_2.setObjectName(_fromUtf8("gridLayout_2"))
        self.label_6 = QtGui.QLabel(self.tabSNES)
        self.label_6.setObjectName(_fromUtf8("label_6"))
        self.gridLayout_2.addWidget(self.label_6, 0, 0, 1, 1)
        self.pathSNES = QtGui.QLineEdit(self.tabSNES)
        self.pathSNES.setObjectName(_fromUtf8("pathSNES"))
        self.gridLayout_2.addWidget(self.pathSNES, 0, 1, 1, 1)
        self.openBinSNES = QtGui.QPushButton(self.tabSNES)
        self.openBinSNES.setObjectName(_fromUtf8("openBinSNES"))
        self.gridLayout_2.addWidget(self.openBinSNES, 0, 2, 1, 1)
        self.label_7 = QtGui.QLabel(self.tabSNES)
        self.label_7.setObjectName(_fromUtf8("label_7"))
        self.gridLayout_2.addWidget(self.label_7, 1, 0, 1, 1)
        self.cmdSNES = QtGui.QLineEdit(self.tabSNES)
        self.cmdSNES.setObjectName(_fromUtf8("cmdSNES"))
        self.gridLayout_2.addWidget(self.cmdSNES, 1, 1, 1, 1)
        self.tabWidget.addTab(self.tabSNES, _fromUtf8(""))
        self.tabN64 = QtGui.QWidget()
        self.tabN64.setObjectName(_fromUtf8("tabN64"))
        self.gridLayout_4 = QtGui.QGridLayout(self.tabN64)
        self.gridLayout_4.setObjectName(_fromUtf8("gridLayout_4"))
        self.label_8 = QtGui.QLabel(self.tabN64)
        self.label_8.setObjectName(_fromUtf8("label_8"))
        self.gridLayout_4.addWidget(self.label_8, 0, 0, 1, 1)
        self.pathN64 = QtGui.QLineEdit(self.tabN64)
        self.pathN64.setObjectName(_fromUtf8("pathN64"))
        self.gridLayout_4.addWidget(self.pathN64, 0, 1, 1, 1)
        self.openBinN64 = QtGui.QPushButton(self.tabN64)
        self.openBinN64.setObjectName(_fromUtf8("openBinN64"))
        self.gridLayout_4.addWidget(self.openBinN64, 0, 2, 1, 1)
        self.label_9 = QtGui.QLabel(self.tabN64)
        self.label_9.setObjectName(_fromUtf8("label_9"))
        self.gridLayout_4.addWidget(self.label_9, 1, 0, 1, 1)
        self.cmdN64 = QtGui.QLineEdit(self.tabN64)
        self.cmdN64.setObjectName(_fromUtf8("cmdN64"))
        self.gridLayout_4.addWidget(self.cmdN64, 1, 1, 1, 1)
        self.tabWidget.addTab(self.tabN64, _fromUtf8(""))
        self.tabGC = QtGui.QWidget()
        self.tabGC.setObjectName(_fromUtf8("tabGC"))
        self.gridLayout_5 = QtGui.QGridLayout(self.tabGC)
        self.gridLayout_5.setObjectName(_fromUtf8("gridLayout_5"))
        self.label_10 = QtGui.QLabel(self.tabGC)
        self.label_10.setObjectName(_fromUtf8("label_10"))
        self.gridLayout_5.addWidget(self.label_10, 0, 0, 1, 1)
        self.pathGameCube = QtGui.QLineEdit(self.tabGC)
        self.pathGameCube.setObjectName(_fromUtf8("pathGameCube"))
        self.gridLayout_5.addWidget(self.pathGameCube, 0, 1, 1, 1)
        self.openBinGameCube = QtGui.QPushButton(self.tabGC)
        self.openBinGameCube.setObjectName(_fromUtf8("openBinGameCube"))
        self.gridLayout_5.addWidget(self.openBinGameCube, 0, 2, 1, 1)
        self.label_11 = QtGui.QLabel(self.tabGC)
        self.label_11.setObjectName(_fromUtf8("label_11"))
        self.gridLayout_5.addWidget(self.label_11, 1, 0, 1, 1)
        self.cmdGameCube = QtGui.QLineEdit(self.tabGC)
        self.cmdGameCube.setObjectName(_fromUtf8("cmdGameCube"))
        self.gridLayout_5.addWidget(self.cmdGameCube, 1, 1, 1, 1)
        self.tabWidget.addTab(self.tabGC, _fromUtf8(""))
        self.tabWii = QtGui.QWidget()
        self.tabWii.setObjectName(_fromUtf8("tabWii"))
        self.gridLayout_6 = QtGui.QGridLayout(self.tabWii)
        self.gridLayout_6.setObjectName(_fromUtf8("gridLayout_6"))
        self.label_12 = QtGui.QLabel(self.tabWii)
        self.label_12.setObjectName(_fromUtf8("label_12"))
        self.gridLayout_6.addWidget(self.label_12, 0, 0, 1, 1)
        self.pathWii = QtGui.QLineEdit(self.tabWii)
        self.pathWii.setObjectName(_fromUtf8("pathWii"))
        self.gridLayout_6.addWidget(self.pathWii, 0, 1, 1, 1)
        self.openBinWii = QtGui.QPushButton(self.tabWii)
        self.openBinWii.setObjectName(_fromUtf8("openBinWii"))
        self.gridLayout_6.addWidget(self.openBinWii, 0, 2, 1, 1)
        self.label_13 = QtGui.QLabel(self.tabWii)
        self.label_13.setObjectName(_fromUtf8("label_13"))
        self.gridLayout_6.addWidget(self.label_13, 1, 0, 1, 1)
        self.cmdWii = QtGui.QLineEdit(self.tabWii)
        self.cmdWii.setObjectName(_fromUtf8("cmdWii"))
        self.gridLayout_6.addWidget(self.cmdWii, 1, 1, 1, 1)
        self.tabWidget.addTab(self.tabWii, _fromUtf8(""))
        self.tabPS1 = QtGui.QWidget()
        self.tabPS1.setObjectName(_fromUtf8("tabPS1"))
        self.gridLayout_7 = QtGui.QGridLayout(self.tabPS1)
        self.gridLayout_7.setObjectName(_fromUtf8("gridLayout_7"))
        self.label_14 = QtGui.QLabel(self.tabPS1)
        self.label_14.setObjectName(_fromUtf8("label_14"))
        self.gridLayout_7.addWidget(self.label_14, 0, 0, 1, 1)
        self.pathPS1 = QtGui.QLineEdit(self.tabPS1)
        self.pathPS1.setObjectName(_fromUtf8("pathPS1"))
        self.gridLayout_7.addWidget(self.pathPS1, 0, 1, 1, 1)
        self.openBinPS1 = QtGui.QPushButton(self.tabPS1)
        self.openBinPS1.setObjectName(_fromUtf8("openBinPS1"))
        self.gridLayout_7.addWidget(self.openBinPS1, 0, 2, 1, 1)
        self.label_15 = QtGui.QLabel(self.tabPS1)
        self.label_15.setObjectName(_fromUtf8("label_15"))
        self.gridLayout_7.addWidget(self.label_15, 1, 0, 1, 1)
        self.cmdPS1 = QtGui.QLineEdit(self.tabPS1)
        self.cmdPS1.setObjectName(_fromUtf8("cmdPS1"))
        self.gridLayout_7.addWidget(self.cmdPS1, 1, 1, 1, 1)
        self.tabWidget.addTab(self.tabPS1, _fromUtf8(""))
        self.tabPS2 = QtGui.QWidget()
        self.tabPS2.setObjectName(_fromUtf8("tabPS2"))
        self.gridLayout_8 = QtGui.QGridLayout(self.tabPS2)
        self.gridLayout_8.setObjectName(_fromUtf8("gridLayout_8"))
        self.label_16 = QtGui.QLabel(self.tabPS2)
        self.label_16.setObjectName(_fromUtf8("label_16"))
        self.gridLayout_8.addWidget(self.label_16, 0, 0, 1, 1)
        self.pathPS2 = QtGui.QLineEdit(self.tabPS2)
        self.pathPS2.setObjectName(_fromUtf8("pathPS2"))
        self.gridLayout_8.addWidget(self.pathPS2, 0, 1, 1, 1)
        self.openBinPS2 = QtGui.QPushButton(self.tabPS2)
        self.openBinPS2.setObjectName(_fromUtf8("openBinPS2"))
        self.gridLayout_8.addWidget(self.openBinPS2, 0, 2, 1, 1)
        self.label_17 = QtGui.QLabel(self.tabPS2)
        self.label_17.setObjectName(_fromUtf8("label_17"))
        self.gridLayout_8.addWidget(self.label_17, 1, 0, 1, 1)
        self.cmdPS2 = QtGui.QLineEdit(self.tabPS2)
        self.cmdPS2.setObjectName(_fromUtf8("cmdPS2"))
        self.gridLayout_8.addWidget(self.cmdPS2, 1, 1, 1, 1)
        self.tabWidget.addTab(self.tabPS2, _fromUtf8(""))
        self.tabGenesis = QtGui.QWidget()
        self.tabGenesis.setObjectName(_fromUtf8("tabGenesis"))
        self.gridLayout_9 = QtGui.QGridLayout(self.tabGenesis)
        self.gridLayout_9.setObjectName(_fromUtf8("gridLayout_9"))
        self.label_18 = QtGui.QLabel(self.tabGenesis)
        self.label_18.setObjectName(_fromUtf8("label_18"))
        self.gridLayout_9.addWidget(self.label_18, 0, 0, 1, 1)
        self.pathGenesis = QtGui.QLineEdit(self.tabGenesis)
        self.pathGenesis.setObjectName(_fromUtf8("pathGenesis"))
        self.gridLayout_9.addWidget(self.pathGenesis, 0, 1, 1, 1)
        self.openBinGenesis = QtGui.QPushButton(self.tabGenesis)
        self.openBinGenesis.setObjectName(_fromUtf8("openBinGenesis"))
        self.gridLayout_9.addWidget(self.openBinGenesis, 0, 2, 1, 1)
        self.label_19 = QtGui.QLabel(self.tabGenesis)
        self.label_19.setObjectName(_fromUtf8("label_19"))
        self.gridLayout_9.addWidget(self.label_19, 1, 0, 1, 1)
        self.cmdGenesis = QtGui.QLineEdit(self.tabGenesis)
        self.cmdGenesis.setObjectName(_fromUtf8("cmdGenesis"))
        self.gridLayout_9.addWidget(self.cmdGenesis, 1, 1, 1, 1)
        self.tabWidget.addTab(self.tabGenesis, _fromUtf8(""))
        self.tabDreamcast = QtGui.QWidget()
        self.tabDreamcast.setObjectName(_fromUtf8("tabDreamcast"))
        self.gridLayout_10 = QtGui.QGridLayout(self.tabDreamcast)
        self.gridLayout_10.setObjectName(_fromUtf8("gridLayout_10"))
        self.label_20 = QtGui.QLabel(self.tabDreamcast)
        self.label_20.setObjectName(_fromUtf8("label_20"))
        self.gridLayout_10.addWidget(self.label_20, 0, 0, 1, 1)
        self.pathDreamcast = QtGui.QLineEdit(self.tabDreamcast)
        self.pathDreamcast.setObjectName(_fromUtf8("pathDreamcast"))
        self.gridLayout_10.addWidget(self.pathDreamcast, 0, 1, 1, 1)
        self.openBinDreamcast = QtGui.QPushButton(self.tabDreamcast)
        self.openBinDreamcast.setObjectName(_fromUtf8("openBinDreamcast"))
        self.gridLayout_10.addWidget(self.openBinDreamcast, 0, 2, 1, 1)
        self.label_21 = QtGui.QLabel(self.tabDreamcast)
        self.label_21.setObjectName(_fromUtf8("label_21"))
        self.gridLayout_10.addWidget(self.label_21, 1, 0, 1, 1)
        self.cmdDreamcast = QtGui.QLineEdit(self.tabDreamcast)
        self.cmdDreamcast.setObjectName(_fromUtf8("cmdDreamcast"))
        self.gridLayout_10.addWidget(self.cmdDreamcast, 1, 1, 1, 1)
        self.tabWidget.addTab(self.tabDreamcast, _fromUtf8(""))
        self.tabGameBoy = QtGui.QWidget()
        self.tabGameBoy.setObjectName(_fromUtf8("tabGameBoy"))
        self.gridLayout_11 = QtGui.QGridLayout(self.tabGameBoy)
        self.gridLayout_11.setObjectName(_fromUtf8("gridLayout_11"))
        self.label_22 = QtGui.QLabel(self.tabGameBoy)
        self.label_22.setObjectName(_fromUtf8("label_22"))
        self.gridLayout_11.addWidget(self.label_22, 0, 0, 1, 1)
        self.pathGameBoy = QtGui.QLineEdit(self.tabGameBoy)
        self.pathGameBoy.setObjectName(_fromUtf8("pathGameBoy"))
        self.gridLayout_11.addWidget(self.pathGameBoy, 0, 1, 1, 1)
        self.openBinGameBoy = QtGui.QPushButton(self.tabGameBoy)
        self.openBinGameBoy.setObjectName(_fromUtf8("openBinGameBoy"))
        self.gridLayout_11.addWidget(self.openBinGameBoy, 0, 2, 1, 1)
        self.label_23 = QtGui.QLabel(self.tabGameBoy)
        self.label_23.setObjectName(_fromUtf8("label_23"))
        self.gridLayout_11.addWidget(self.label_23, 1, 0, 1, 1)
        self.cmdGameBoy = QtGui.QLineEdit(self.tabGameBoy)
        self.cmdGameBoy.setObjectName(_fromUtf8("cmdGameBoy"))
        self.gridLayout_11.addWidget(self.cmdGameBoy, 1, 1, 1, 1)
        self.tabWidget.addTab(self.tabGameBoy, _fromUtf8(""))
        self.tabGBA = QtGui.QWidget()
        self.tabGBA.setObjectName(_fromUtf8("tabGBA"))
        self.gridLayout_12 = QtGui.QGridLayout(self.tabGBA)
        self.gridLayout_12.setObjectName(_fromUtf8("gridLayout_12"))
        self.label_24 = QtGui.QLabel(self.tabGBA)
        self.label_24.setObjectName(_fromUtf8("label_24"))
        self.gridLayout_12.addWidget(self.label_24, 0, 0, 1, 1)
        self.pathGBA = QtGui.QLineEdit(self.tabGBA)
        self.pathGBA.setObjectName(_fromUtf8("pathGBA"))
        self.gridLayout_12.addWidget(self.pathGBA, 0, 1, 1, 1)
        self.openBinGBA = QtGui.QPushButton(self.tabGBA)
        self.openBinGBA.setObjectName(_fromUtf8("openBinGBA"))
        self.gridLayout_12.addWidget(self.openBinGBA, 0, 2, 1, 1)
        self.label_25 = QtGui.QLabel(self.tabGBA)
        self.label_25.setObjectName(_fromUtf8("label_25"))
        self.gridLayout_12.addWidget(self.label_25, 1, 0, 1, 1)
        self.cmdGBA = QtGui.QLineEdit(self.tabGBA)
        self.cmdGBA.setObjectName(_fromUtf8("cmdGBA"))
        self.gridLayout_12.addWidget(self.cmdGBA, 1, 1, 1, 1)
        self.tabWidget.addTab(self.tabGBA, _fromUtf8(""))
        self.tabNDS = QtGui.QWidget()
        self.tabNDS.setObjectName(_fromUtf8("tabNDS"))
        self.gridLayout_13 = QtGui.QGridLayout(self.tabNDS)
        self.gridLayout_13.setObjectName(_fromUtf8("gridLayout_13"))
        self.label_26 = QtGui.QLabel(self.tabNDS)
        self.label_26.setObjectName(_fromUtf8("label_26"))
        self.gridLayout_13.addWidget(self.label_26, 0, 0, 1, 1)
        self.pathNDS = QtGui.QLineEdit(self.tabNDS)
        self.pathNDS.setObjectName(_fromUtf8("pathNDS"))
        self.gridLayout_13.addWidget(self.pathNDS, 0, 1, 1, 1)
        self.openBinNDS = QtGui.QPushButton(self.tabNDS)
        self.openBinNDS.setObjectName(_fromUtf8("openBinNDS"))
        self.gridLayout_13.addWidget(self.openBinNDS, 0, 2, 1, 1)
        self.label_27 = QtGui.QLabel(self.tabNDS)
        self.label_27.setObjectName(_fromUtf8("label_27"))
        self.gridLayout_13.addWidget(self.label_27, 1, 0, 1, 1)
        self.cmdNDS = QtGui.QLineEdit(self.tabNDS)
        self.cmdNDS.setObjectName(_fromUtf8("cmdNDS"))
        self.gridLayout_13.addWidget(self.cmdNDS, 1, 1, 1, 1)
        self.tabWidget.addTab(self.tabNDS, _fromUtf8(""))
        self.verticalLayout_2.addWidget(self.tabWidget)
        self.gridLayout_3.addLayout(self.verticalLayout_2, 0, 0, 1, 1)
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setSizeConstraint(QtGui.QLayout.SetDefaultConstraint)
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        self.btnSave = QtGui.QPushButton(self.centralwidget)
        self.btnSave.setObjectName(_fromUtf8("btnSave"))
        self.horizontalLayout.addWidget(self.btnSave)
        self.btnCancel = QtGui.QPushButton(self.centralwidget)
        self.btnCancel.setObjectName(_fromUtf8("btnCancel"))
        self.horizontalLayout.addWidget(self.btnCancel)
        self.gridLayout_3.addLayout(self.horizontalLayout, 1, 0, 1, 1)
        windowSettings.setCentralWidget(self.centralwidget)
        self.menubar = QtGui.QMenuBar(windowSettings)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 770, 28))
        self.menubar.setObjectName(_fromUtf8("menubar"))
        windowSettings.setMenuBar(self.menubar)
        self.statusbar = QtGui.QStatusBar(windowSettings)
        self.statusbar.setObjectName(_fromUtf8("statusbar"))
        windowSettings.setStatusBar(self.statusbar)

        self.retranslateUi(windowSettings)
        self.tabWidget.setCurrentIndex(0)
        QtCore.QMetaObject.connectSlotsByName(windowSettings)

    def retranslateUi(self, windowSettings):
        windowSettings.setWindowTitle(_translate("windowSettings", "Ice - Settings", None))
        self.label_4.setText(_translate("windowSettings", "Path to emulator binary:", None))
        self.label_5.setText(_translate("windowSettings", "Custom commands:", None))
        self.openBinNES.setText(_translate("windowSettings", "Open binary...", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tabNES), _translate("windowSettings", "NES", None))
        self.label_6.setText(_translate("windowSettings", "Path to emulator binary:", None))
        self.openBinSNES.setText(_translate("windowSettings", "Open binary...", None))
        self.label_7.setText(_translate("windowSettings", "Custom commands:", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tabSNES), _translate("windowSettings", "SNES", None))
        self.label_8.setText(_translate("windowSettings", "Path to emulator binary:", None))
        self.openBinN64.setText(_translate("windowSettings", "Open binary...", None))
        self.label_9.setText(_translate("windowSettings", "Custom commands:", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tabN64), _translate("windowSettings", "N64", None))
        self.label_10.setText(_translate("windowSettings", "Path to emulator binary:", None))
        self.openBinGameCube.setText(_translate("windowSettings", "Open binary...", None))
        self.label_11.setText(_translate("windowSettings", "Custom commands:", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tabGC), _translate("windowSettings", "GameCube", None))
        self.label_12.setText(_translate("windowSettings", "Path to emulator binary:", None))
        self.openBinWii.setText(_translate("windowSettings", "Open binary...", None))
        self.label_13.setText(_translate("windowSettings", "Custom commands:", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tabWii), _translate("windowSettings", "Wii", None))
        self.label_14.setText(_translate("windowSettings", "Path to emulator binary:", None))
        self.openBinPS1.setText(_translate("windowSettings", "Open binary...", None))
        self.label_15.setText(_translate("windowSettings", "Custom commands:", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tabPS1), _translate("windowSettings", "PS 1", None))
        self.label_16.setText(_translate("windowSettings", "Path to emulator binary:", None))
        self.openBinPS2.setText(_translate("windowSettings", "Open binary...", None))
        self.label_17.setText(_translate("windowSettings", "Custom commands:", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tabPS2), _translate("windowSettings", "PS 2", None))
        self.label_18.setText(_translate("windowSettings", "Path to emulator binary:", None))
        self.openBinGenesis.setText(_translate("windowSettings", "Open binary...", None))
        self.label_19.setText(_translate("windowSettings", "Custom commands:", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tabGenesis), _translate("windowSettings", "Genesis", None))
        self.label_20.setText(_translate("windowSettings", "Path to emulator binary:", None))
        self.openBinDreamcast.setText(_translate("windowSettings", "Open binary...", None))
        self.label_21.setText(_translate("windowSettings", "Custom commands:", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tabDreamcast), _translate("windowSettings", "Dreamcast", None))
        self.label_22.setText(_translate("windowSettings", "Path to emulator binary:", None))
        self.openBinGameBoy.setText(_translate("windowSettings", "Open binary...", None))
        self.label_23.setText(_translate("windowSettings", "Custom commands:", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tabGameBoy), _translate("windowSettings", "GameBoy", None))
        self.label_24.setText(_translate("windowSettings", "Path to emulator binary:", None))
        self.openBinGBA.setText(_translate("windowSettings", "Open binary...", None))
        self.label_25.setText(_translate("windowSettings", "Custom commands:", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tabGBA), _translate("windowSettings", "GBA", None))
        self.label_26.setText(_translate("windowSettings", "Path to emulator binary:", None))
        self.openBinNDS.setText(_translate("windowSettings", "Open binary...", None))
        self.label_27.setText(_translate("windowSettings", "Custom commands:", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tabNDS), _translate("windowSettings", "NDS", None))
        self.btnSave.setText(_translate("windowSettings", "Save", None))
        self.btnCancel.setText(_translate("windowSettings", "Cancel", None))


########NEW FILE########
__FILENAME__ = utils
#!/usr/bin/env python
# encoding: utf-8
"""
utils.py

Created by Scott on 2013-12-21.
Copyright (c) 2013 Scott Rice. All rights reserved.

Functionality should be added here if it is just general python utility
functions, not related to Ice at all. You should be able to move this file to
another python project and be able to use it out of the box.
"""

import collections
import functools

# Convenient function to check if a key is in a dictionary. If so, uses that,
# otherwise, uses the default.
# Also, 'idx' stands for 'index'.
def idx(dictionary, index, default=None):
    if index in dictionary:
        return dictionary[index]
    else:
        return default

# Decorator for memoization
# Copied from https://wiki.python.org/moin/PythonDecoratorLibrary#Memoize
class memoize(object):
    '''Decorator. Caches a function's return value each time it is called.
    If called later with the same arguments, the cached value is returned
    (not reevaluated).
    '''
    def __init__(self, func):
        self.func = func
        self.cache = {}

    def __call__(self, *args):
        if not isinstance(args, collections.Hashable):
            # uncacheable. a list, for instance.
            # better to not cache than blow up.
            return self.func(*args)
        if args in self.cache:
            return self.cache[args]
        else:
            value = self.func(*args)
            self.cache[args] = value
            return value

    def __repr__(self):
        '''Return the function's docstring.'''
        return self.func.__doc__

    def __get__(self, obj, objtype):
        '''Support instance methods.'''
        return functools.partial(self.__call__, obj)

########NEW FILE########
__FILENAME__ = ice-qt
#!/usr/bin/env python

# gui
import sys
from ice.gui import qtApp, qtWindow

def main():
    qtWindow.show()
    sys.exit(qtApp.exec_())

if __name__ == "__main__":
    main()
########NEW FILE########
__FILENAME__ = ice
#!/usr/bin/env python

from ice.error.config_error import ConfigError

from ice.steam_shortcut_manager import SteamShortcutManager

from ice import steam_user_manager
from ice import filesystem_helper as fs
from ice import console
from ice.rom_manager import IceROMManager
from ice.process_helper import steam_is_running
from ice.grid_image_manager import IceGridImageManager
from ice.ice_logging import ice_logger

def main():
    if steam_is_running():
        ice_logger.log_error("Ice cannot be run while Steam is open. Please close Steam and try again")
        return

    ice_logger.log("Starting Ice")
    # Find all of the ROMs that are currently in the designated folders
    roms = console.find_all_roms()
    # Find the Steam Account that the user would like to add ROMs for
    user_ids = steam_user_manager.user_ids_on_this_machine()
    grid_manager = IceGridImageManager()
    for user_id in user_ids:
        ice_logger.log("Running for user %s" % str(user_id))
        # Load their shortcuts into a SteamShortcutManager object
        shortcuts_path = steam_user_manager.shortcuts_file_for_user_id(user_id)
        shortcuts_manager = SteamShortcutManager(shortcuts_path)
        rom_manager = IceROMManager(shortcuts_manager)
        # Add the new ROMs in each folder to our Shortcut Manager
        rom_manager.sync_roms(roms)
        # Backup the current shortcuts.vdf file
        shortcuts_manager.backup()
        # Generate a new shortcuts.vdf file with all of the new additions
        shortcuts_manager.save()
        grid_manager.update_user_images(user_id,roms)
    ice_logger.log('Ice finished')
        
if __name__ == "__main__":
    try:
        main()
    except ConfigError as error:
        ice_logger.log_error('Stopping')
        ice_logger.log_config_error(error)
        ice_logger.log_exception()
    except StandardError as error:
        ice_logger.log_exception()
    # Keeps the console from closing (until the user hits enter) so they can
    # read any console output
    print ""
    print "Close the window, or hit enter to exit..."
    raw_input()

########NEW FILE########
__FILENAME__ = run_tests
#!/usr/bin/env python
# encoding: utf-8
"""
run_tests.py

Created by Scott on 2012-12-26.
Copyright (c) 2012 Scott Rice. All rights reserved.
"""

import sys
import os
import inspect

from test import run_tests


# The code below is to allow test cases to import the class they are testing by
# using the syntax 'import ice.******'.
#
# This code was taken from a StackOverflow answer by sorin. Thanks bud!
# http://stackoverflow.com/questions/279237/python-import-a-module-from-a-folder
#
# Get a reference to the current directory, without using __file__, which fails
# in certain situations based on how you call the script in Windows
cmd_folder = os.path.realpath(os.path.abspath(os.path.split(inspect.getfile(inspect.currentframe()))[0]))
ice_folder = os.path.join(cmd_folder,"ice")
if cmd_folder not in sys.path:
    sys.path.insert(0,cmd_folder)
if ice_folder not in sys.path:
    sys.path.insert(1,ice_folder)

run_tests()
########NEW FILE########
__FILENAME__ = console_tests
#!/usr/bin/env python
# encoding: utf-8
"""
console_tests.py

Created by Scott on 2012-12-26.
Copyright (c) 2012 Scott Rice. All rights reserved.
"""

import os
import unittest

import filesystem_helper
from console import Console, supported_consoles

class ConsoleTests(unittest.TestCase):
    def setUp(self):
        self.console = Console("Test","Test Console")
        
    # @unittest.skip("Not yet implemented")
    # def test_find_all_roms(self):
    #     pass
    # 
    # @unittest.skip("Not yet implemented")    
    # def test_find_all_roms_for_console(self):
    #     pass
        
    def test_roms_directory(self):
        """
        The ROMs directory for a console should be the ROMs directory from
        filesystem_helper, except the directory name should be equal to the
        shortname for the console
        """
        gba_dir = self.console.roms_directory()
        self.assertEqual(os.path.dirname(gba_dir),filesystem_helper.roms_directory())
        self.assertEqual(os.path.basename(gba_dir),self.console.shortname)

########NEW FILE########
__FILENAME__ = rom_tests
#!/usr/bin/env python
# encoding: utf-8
"""
rom_test.py

Created by Scott on 2012-12-26.
Copyright (c) 2012 Scott Rice. All rights reserved.
"""

import sys
import os
import unittest

from rom import ROM
from console import Console


class ROMTests(unittest.TestCase):

    def test_basename(self):
        """
        Basename should be the name of the ROM file minus the extension.
        If the ROM has no extension, then the name should just be the name of
        the ROM file
        """
        gba = Console("Gameboy Advance")
        prefix_gba = Console("Gameboy Advance", { "prefix":"Any Text" })
        rom_path = "/Users/scottrice/ROMs/GBA/Pokemon Emerald.gba"
        noext_rom_path = "/Users/scottrice/ROMs/GBA/Pokemon Emerald"
        rom = ROM(rom_path,gba)
        noext_rom = ROM(noext_rom_path,gba)
        prefix_rom = ROM(rom_path, prefix_gba)

        # Standard situation
        self.assertEqual(rom.basename(),"Pokemon Emerald")
        # Should correctly figure out the basename when the ROM has no extension
        self.assertEqual(noext_rom.basename(),"Pokemon Emerald")
        # The basename shouldn't include the prefix
        self.assertEqual(prefix_rom.basename(), "Pokemon Emerald")

    def test_name(self):
        prefix = "Any Text"
        gba = Console("Gameboy Advance")
        prefix_gba = Console("Gameboy Advance", { "prefix": prefix })
        empty_prefix_gba = Console("Gameboy Advance", {"prefix": "" })
        rom_path = "/Users/scottrice/ROMs/GBA/Pokemon Emerald.gba"

        rom = ROM(rom_path, gba)
        prefix_rom = ROM(rom_path, prefix_gba)
        empty_prefix_rom = ROM(rom_path, empty_prefix_gba)

        # With no prefix, the name should be the same as the basename
        self.assertEqual(rom.name(), "Pokemon Emerald")
        # When the prefix is the empty string, it should be treated as if no
        # prefix was given
        self.assertEqual(empty_prefix_rom.name(), "Pokemon Emerald")
        # When the console has a prefix, the ROM should begin with that string
        self.assertTrue(prefix_rom.name().startswith(prefix))

########NEW FILE########
__FILENAME__ = steam_user_manager_tests
#!/usr/bin/env python
# encoding: utf-8
"""
steam_user_manager_tests.py

Created by Scott on 2012-12-26.
Copyright (c) 2012 Scott Rice. All rights reserved.
"""

import os
import unittest

import steam_installation_location_manager
from steam_user_manager import *

class SteamUserManagerTests(unittest.TestCase):
    def setUp(self):
        self.steam_name = "meris608"
        self.steam_id = 20293187
        self.community_id_32 = 40586375
        self.community_id_64 = 76561198000852103
    
    def test_community_id_64_from_name(self):
	    self.assertEqual(communityid64_from_name(self.steam_name),self.community_id_64)
	
    def test_steam_id_from_name(self):
        self.assertEqual(steam_id_from_name(self.steam_name),self.steam_id)
	
    def test_community_id_32_from_name(self):
        self.assertEqual(communityid32_from_name(self.steam_name),self.community_id_32)
	
    def test_name_from_communityid64(self):
        self.assertEqual(name_from_communityid64(self.community_id_64),self.steam_name)
    
    def test_name_from_communityid32(self):
        self.assertEqual(name_from_communityid32(self.community_id_32),self.steam_name)
        
    def test_userdata_directory_for_name(self):
        """
        The userdata directory for a name should be the same directory as it is
        for the 32 bit community id associated with the name
        """
        self.assertEqual(userdata_directory_for_name(self.steam_name),userdata_directory_for_user_id(self.community_id_32))
        
    def test_userdata_directory_for_user_id(self):
        """
        The userdata directory for a user_id should be in the userdata 
        directory for the given Steam installation, and the directory should
        be named the same as the user id
        """
        ud_dir = userdata_directory_for_user_id(self.community_id_32)
        # dirname removes the trailing /, which I keep in 
        # steam_userdata_location, so I add that back on for the equality check
        self.assertEqual(os.path.dirname(ud_dir)+os.sep,steam_installation_location_manager.steam_userdata_location())
        self.assertEqual(int(os.path.basename(ud_dir)),self.community_id_32)
        
        
    def test_shortcuts_file_for_user_id(self):
        """
        The shortcuts file for a given user id should be the result of the
        userdata_directory_for_user_id method, with 'config/shortcuts.vdf'
        added on
        """
        my_shortcuts_file = shortcuts_file_for_user_id(self.community_id_32)
        config_dir = os.path.join(userdata_directory_for_user_id(self.community_id_32),"config")
        self.assertEqual(os.path.dirname(my_shortcuts_file),config_dir)
        self.assertEqual(os.path.basename(my_shortcuts_file),"shortcuts.vdf")
        
    def test_user_ids_on_this_machine(self):
        """
        Finds a list of user_ids that have folders defined on this machine.
        There is no requirement that they have an existing shortcuts.vdf file,
        just that they have a folder named after their user id on the userdata
        folder
        """
        # I am going to test this by getting the list of people defined on the
        # current machine (the one running the tests), adding another folder
        # with an arbitrary id, making sure the new results are the old results
        # plus the arbitrary id, and then removing the new id
        existing_ids = user_ids_on_this_machine()
        # 1 is not a valid 32 bit community id, but we dont care about
        # validity, we just want to know that it correctly reads from the
        # directory.
        os.mkdir(userdata_directory_for_user_id(1))
        updated_ids = user_ids_on_this_machine()
        expected_ids = existing_ids
        expected_ids.append(1)
        os.rmdir(userdata_directory_for_user_id(1))
        # We don't care about order, so we convert to a set first, and make
        # sure that updated_ids = existing_ids + 1
        self.assertEqual(set(expected_ids),set(updated_ids))
        
########NEW FILE########
