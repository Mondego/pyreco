__FILENAME__ = cli
# -*- coding: utf-8 -*-

"""
dotfiles.cli

This module provides the CLI interface to dotfiles.
"""

from __future__ import absolute_import

import os
from . import core
try:
    import ConfigParser as configparser
except ImportError:
    import configparser
from optparse import OptionParser, OptionGroup

from dotfiles.utils import compare_path, realpath_expanduser


defaults = {
        'prefix': '',
        'homedir': '~/',
        'repository': '~/Dotfiles',
        'config_file': '~/.dotfilesrc'}

settings = {
        'prefix': None,
        'homedir': None,
        'repository': None,
        'config_file': None,
        'ignore': set(['.dotfilesrc']),
        'externals': dict(),
        'packages': set()}


def missing_default_repo():
    """Print a helpful message when the default repository is missing."""

    print("""
If this is your first time running dotfiles, you must first create
a repository.  By default, dotfiles will look for '{0}'.
Something like:

    $ mkdir {0}

is all you need to do.  If you don't like the default, you can put your
repository wherever you like.  You have two choices once you've created your
repository.  You can specify the path to the repository on the command line
using the '-R' flag.  Alternatively, you can create a configuration file at
'~/.dotfilesrc' and place the path to your repository in there.  The contents
would look like:

    [dotfiles]
    repository = {0}

Type 'dotfiles -h' to see detailed usage information.""".format(
        defaults['repository']))


def add_global_flags(parser):
    parser.add_option("-v", "--version",
            action="store_true", dest="show_version", default=False,
            help="show version number and exit")

    parser.add_option("-f", "--force",
            action="store_true", dest="force", default=False,
            help="overwrite colliding dotfiles (use with --sync)")

    parser.add_option("-R", "--repo",
            type="string", dest="repository",
            help="set repository location (default: %s)" % (
                defaults['repository']))

    parser.add_option("-p", "--prefix",
            type="string", dest="prefix",
            help="set prefix character (default: %s)" % (
                "None" if not defaults['prefix'] else defaults['prefix']))

    parser.add_option("-C", "--config",
            type="string", dest="config_file",
            help="set configuration file location (default: %s)" % (
                defaults['config_file']))

    parser.add_option("-H", "--home",
            type="string", dest="homedir",
            help="set home directory location (default: %s)" % (
                defaults['homedir']))

    parser.add_option("-d", "--dry-run",
            action="store_true", default=False,
            help="don't modify anything, just print commands")


def add_action_group(parser):
    action_group = OptionGroup(parser, "Actions")

    action_group.add_option("-a", "--add",
            action="store_const", dest="action", const="add",
            help="add dotfile(s) to the repository")

    action_group.add_option("-c", "--check",
            action="store_const", dest="action", const="check",
            help="check for broken and unsynced dotfiles")

    action_group.add_option("-l", "--list",
            action="store_const", dest="action", const="list",
            help="list currently managed dotfiles")

    action_group.add_option("-r", "--remove",
            action="store_const", dest="action", const="remove",
            help="remove dotfile(s) from the repository")

    action_group.add_option("-s", "--sync",
            action="store_const", dest="action", const="sync",
            help="update dotfile symlinks")

    action_group.add_option("-m", "--move",
            action="store_const", dest="action", const="move",
            help="move dotfiles repository to another location")

    parser.add_option_group(action_group)


def parse_args():

    parser = OptionParser(usage="%prog ACTION [OPTION...] [FILE...]")

    add_global_flags(parser)
    add_action_group(parser)

    (opts, args) = parser.parse_args()

    if opts.show_version:
        print('dotfiles v%s' % core.__version__)
        exit(0)

    if not opts.action:
        print("Error: An action is required. Type 'dotfiles -h' to see " \
              "detailed usage information.")
        exit(-1)

    return (opts, args)


def parse_config(config_file):

    parser = configparser.SafeConfigParser()
    parser.read(config_file)

    opts = {'repository': None,
            'prefix': None,
            'ignore': set(),
            'externals': dict(),
            'packages': set()}

    for entry in ('repository', 'prefix'):
        try:
            opts[entry] = parser.get('dotfiles', entry)
        except configparser.NoOptionError:
            pass
        except configparser.NoSectionError:
            break

    for entry in ('ignore', 'externals', 'packages'):
        try:
            opts[entry] = eval(parser.get('dotfiles', entry))
        except configparser.NoOptionError:
            pass
        except configparser.NoSectionError:
            break

    return opts


def dispatch(dotfiles, action, force, args):
    if action in ['list', 'check']:
        getattr(dotfiles, action)()
    elif action in ['add', 'remove']:
        getattr(dotfiles, action)(args)
    elif action == 'sync':
        getattr(dotfiles, action)(files=args, force=force)
    elif action == 'move':
        if len(args) > 1:
            print("Error: Move cannot handle multiple targets.")
            exit(-1)
        dotfiles.move(args[0])
    else:
        print("Error: Something truly terrible has happened.")
        exit(-1)


def check_repository_exists():
    if not os.path.exists(settings['repository']):
        print('Error: Could not find dotfiles repository \"%s\"' % (
                settings['repository']))
        if compare_path(settings['repository'], defaults['repository']):
            missing_default_repo()
        exit(-1)


def update_settings(opts, key):
    global settings

    settings[key].update(opts[key])


def main():

    global settings

    (cli_opts, args) = parse_args()

    settings['homedir'] = realpath_expanduser(cli_opts.homedir or
            defaults['homedir'])
    settings['config_file'] = realpath_expanduser(cli_opts.config_file or
            defaults['config_file'])

    config_opts = parse_config(settings['config_file'])

    settings['repository'] = realpath_expanduser(cli_opts.repository or
            config_opts['repository'] or defaults['repository'])

    check_repository_exists()

    update_settings(config_opts, 'ignore')
    update_settings(config_opts, 'externals')
    update_settings(config_opts, 'packages')

    repo_config_file = os.path.join(settings['repository'], '.dotfilesrc')
    repo_config_opts = parse_config(repo_config_file)

    settings['prefix'] = (cli_opts.prefix or
                          repo_config_opts['prefix'] or
                          config_opts['prefix'] or
                          defaults['prefix'])

    settings['dry_run'] = cli_opts.dry_run

    update_settings(repo_config_opts, 'ignore')
    update_settings(repo_config_opts, 'externals')
    update_settings(repo_config_opts, 'packages')

    dotfiles = core.Dotfiles(**settings)

    dispatch(dotfiles, cli_opts.action, cli_opts.force, args)

########NEW FILE########
__FILENAME__ = compat
"""
Provides :func:`os.symlink`, :func:`os.path.islink` and
:func:`os.path.realpath` implementations for win32.
"""

import os
import os.path


if hasattr(os, 'symlink'):
    symlink = os.symlink
    islink = os.path.islink
    realpath = os.path.realpath
else:
    # Windows symlinks -- ctypes version
    # symlink, islink, readlink, realpath, is_link_to

    win32_verbose = False       # set to True to debug symlink stuff
    import os, ctypes, struct
    from ctypes import windll, wintypes

    FSCTL_GET_REPARSE_POINT = 0x900a8

    FILE_ATTRIBUTE_READONLY      = 0x0001
    FILE_ATTRIBUTE_HIDDEN        = 0x0002
    FILE_ATTRIBUTE_DIRECTORY     = 0x0010
    FILE_ATTRIBUTE_NORMAL        = 0x0080
    FILE_ATTRIBUTE_REPARSE_POINT = 0x0400


    GENERIC_READ  = 0x80000000
    GENERIC_WRITE = 0x40000000
    OPEN_EXISTING = 3
    FILE_READ_ATTRIBUTES = 0x80
    FILE_FLAG_OPEN_REPARSE_POINT = 0x00200000
    INVALID_HANDLE_VALUE = wintypes.HANDLE(-1).value

    INVALID_FILE_ATTRIBUTES = 0xFFFFFFFF

    FILE_FLAG_OPEN_REPARSE_POINT = 2097152
    FILE_FLAG_BACKUP_SEMANTICS = 33554432
    # FILE_FLAG_OPEN_REPARSE_POINT | FILE_FLAG_BACKUP_SEMANTI
    FILE_FLAG_REPARSE_BACKUP = 35651584


    kdll = windll.LoadLibrary("kernel32.dll")
    CreateSymbolicLinkA = windll.kernel32.CreateSymbolicLinkA
    CreateSymbolicLinkA.restype = wintypes.BOOLEAN
    CreateSymbolicLinkW = windll.kernel32.CreateSymbolicLinkW
    CreateSymbolicLinkW.restype = wintypes.BOOLEAN
    GetFileAttributesA = windll.kernel32.GetFileAttributesA
    GetFileAttributesW = windll.kernel32.GetFileAttributesW
    CloseHandle = windll.kernel32.CloseHandle
    _CreateFileW = windll.kernel32.CreateFileW
    _CreateFileA = windll.kernel32.CreateFileA
    _DevIoCtl = windll.kernel32.DeviceIoControl
    _DevIoCtl.argtypes = [
        wintypes.HANDLE, #HANDLE hDevice
        wintypes.DWORD, #DWORD dwIoControlCode
        wintypes.LPVOID, #LPVOID lpInBuffer
        wintypes.DWORD, #DWORD nInBufferSize
        wintypes.LPVOID, #LPVOID lpOutBuffer
        wintypes.DWORD, #DWORD nOutBufferSize
        ctypes.POINTER(wintypes.DWORD), #LPDWORD lpBytesReturned
        wintypes.LPVOID] #LPOVERLAPPED lpOverlapped
    _DevIoCtl.restype = wintypes.BOOL


    def CreateSymbolicLink(name, target, is_dir):
        assert type(name) == type(target)
        if type(name) == unicode:
            stat = CreateSymbolicLinkW(name, target, is_dir)
        else:
            stat = CreateSymbolicLinkA(name, target, is_dir)
        if win32_verbose:
            print("CreateSymbolicLink(name=%s, target=%s, is_dir=%d) = %#x"%(name,target,is_dir, stat))
        if not stat:
            print("Can't create symlink %s -> %s"%(name, target))
            raise ctypes.WinError()

    def symlink(target, name):
        CreateSymbolicLink(name, target, 0)

    def GetFileAttributes(path):
        if type(path) == unicode:
            return GetFileAttributesW(path)
        else:
            return GetFileAttributesA(path)

    def islink(path):
        assert path
        has_link_attr = GetFileAttributes(path) & FILE_ATTRIBUTE_REPARSE_POINT
        if win32_verbose:
            print("islink(%s): attrs=%#x: %s"%(path, GetFileAttributes(path), has_link_attr != 0))
        return has_link_attr != 0

    def DeviceIoControl(hDevice, ioControlCode, input, output):
        # DeviceIoControl Function
        # http://msdn.microsoft.com/en-us/library/aa363216(v=vs.85).aspx
        if input:
            input_size = len(input)
        else:
            input_size = 0
        if isinstance(output, int):
            output = ctypes.create_string_buffer(output)
        output_size = len(output)
        assert isinstance(output, ctypes.Array)
        bytesReturned = wintypes.DWORD()
        status = _DevIoCtl(hDevice, ioControlCode, input,
                           input_size, output, output_size, bytesReturned, None)
        if win32_verbose:
            print("DeviceIOControl: status = %d" % status)
        if status != 0:
            return output[:bytesReturned.value]
        else:
            return None


    def CreateFile(path, access, sharemode, creation, flags):
        if type(path) == unicode:
            return _CreateFileW(path, access, sharemode, None, creation, flags, None)
        else:
            return _CreateFileA(path, access, sharemode, None, creation, flags, None)

    SymbolicLinkReparseFormat = "LHHHHHHL"
    SymbolicLinkReparseSize = struct.calcsize(SymbolicLinkReparseFormat);

    def readlink(path):
        """ Windows readlink implementation. """
        # This wouldn't return true if the file didn't exist, as far as I know.
        if not islink(path):
            if win32_verbose:
                print("readlink(%s): not a link."%path)
            return None

        # Open the file correctly depending on the string type.
        hfile = CreateFile(path, GENERIC_READ, 0, OPEN_EXISTING, FILE_FLAG_OPEN_REPARSE_POINT)

        # MAXIMUM_REPARSE_DATA_BUFFER_SIZE = 16384 = (16*1024)
        buffer = DeviceIoControl(hfile, FSCTL_GET_REPARSE_POINT, None, 16384)
        CloseHandle(hfile)

        # Minimum possible length (assuming length of the target is bigger than 0)
        if not buffer or len(buffer) < 9:
            if win32_verbose:
                print("readlink(%s): no reparse buffer."%path)
            return None

        # Parse and return our result.
        # typedef struct _REPARSE_DATA_BUFFER {
        #   ULONG  ReparseTag;
        #   USHORT ReparseDataLength;
        #   USHORT Reserved;
        #   union {
        #       struct {
        #           USHORT SubstituteNameOffset;
        #           USHORT SubstituteNameLength;
        #           USHORT PrintNameOffset;
        #           USHORT PrintNameLength;
        #           ULONG Flags;
        #           WCHAR PathBuffer[1];
        #       } SymbolicLinkReparseBuffer;
        #       struct {
        #           USHORT SubstituteNameOffset;
        #           USHORT SubstituteNameLength;
        #           USHORT PrintNameOffset;
        #           USHORT PrintNameLength;
        #           WCHAR PathBuffer[1];
        #       } MountPointReparseBuffer;
        #       struct {
        #           UCHAR  DataBuffer[1];
        #       } GenericReparseBuffer;
        #   } DUMMYUNIONNAME;
        # } REPARSE_DATA_BUFFER, *PREPARSE_DATA_BUFFER;

        # Only handle SymbolicLinkReparseBuffer
        (tag, dataLength, reserver, SubstituteNameOffset, SubstituteNameLength,
         PrintNameOffset, PrintNameLength,
         Flags) = struct.unpack(SymbolicLinkReparseFormat,
                                buffer[:SymbolicLinkReparseSize])
        # print tag, dataLength, reserver, SubstituteNameOffset, SubstituteNameLength
        start = SubstituteNameOffset + SymbolicLinkReparseSize
        actualPath = buffer[start : start + SubstituteNameLength].decode("utf-16")
        # This utf-16 string is null terminated
        index = actualPath.find("\0")
        if index > 0:
            actualPath = actualPath[:index]
        if actualPath.startswith("\\??\\"): # ASCII 92, 63, 63, 92
            ret = actualPath[4:]             # strip off leading junk
        else:
            ret = actualPath
        if win32_verbose:
            print("readlink(%s->%s->%s): index(null) = %d"%\
                (path,repr(actualPath),repr(ret),index))
        return ret

    def realpath(fpath):
        while islink(fpath):
            rpath = readlink(fpath)
            if rpath is None:
                return fpath
            if not os.path.isabs(rpath):
                rpath = os.path.abspath(os.path.join(os.path.dirname(fpath), rpath))
            fpath = rpath
        return fpath

########NEW FILE########
__FILENAME__ = core
# -*- coding: utf-8 -*-

"""
dotfiles.core
~~~~~~~~~~~~~

This module provides the basic functionality of dotfiles.
"""

import os
import os.path
import shutil
import fnmatch

from dotfiles.utils import realpath_expanduser, is_link_to
from dotfiles.compat import symlink


__version__ = '0.6.3'
__author__ = 'Jon Bernard'
__license__ = 'ISC'


class Dotfile(object):

    def __init__(self, name, target, home, add_dot=True, dry_run=False):
        if name.startswith('/'):
            self.name = name
        else:
            if add_dot:
                self.name = os.path.join(home, '.%s' % name.strip('.'))
            else:
                self.name = os.path.join(home, name)
        self.basename = os.path.basename(self.name)
        self.target = target.rstrip('/')
        self.dry_run = dry_run
        self.status = ''
        if not os.path.lexists(self.name):
            self.status = 'missing'
        elif not is_link_to(self.name, self.target):
            self.status = 'unsynced'

    def _symlink(self, target, name):
        if not self.dry_run:
            dirname = os.path.dirname(name)
            if not os.path.isdir(dirname):
                os.makedirs(dirname)
            symlink(target, name)
        else:
            print("Creating symlink %s => %s" % (target, name))

    def _rmtree(self, path):
        if not self.dry_run:
            shutil.rmtree(path)
        else:
            print("Removing %s and everything under it" % path)

    def _remove(self, path):
        if not self.dry_run:
            os.remove(path)
        else:
            print("Removing %s" % path)

    def _move(self, src, dst):
        if not self.dry_run:
            shutil.move(src, dst)
        else:
            print("Moving %s => %s" % (src, dst))

    def sync(self, force):
        if self.status == 'missing':
            self._symlink(self.target, self.name)
        elif self.status == 'unsynced':
            if not force:
                print("Skipping \"%s\", use --force to override"
                        % self.basename)
                return
            if os.path.isdir(self.name) and not os.path.islink(self.name):
                self._rmtree(self.name)
            else:
                self._remove(self.name)
            self._symlink(self.target, self.name)

    def add(self):
        if self.status == 'missing':
            print("Skipping \"%s\", file not found" % self.basename)
            return
        if self.status == '':
            print("Skipping \"%s\", already managed" % self.basename)
            return
        self._move(self.name, self.target)
        self._symlink(self.target, self.name)

    def remove(self):

        if self.status != '':
            print("Skipping \"%s\", file is %s" % (self.basename, self.status))
            return

        # remove the existing symlink
        self._remove(self.name)

        # return dotfile to its original location
        if os.path.exists(self.target):
            self._move(self.target, self.name)

    def __str__(self):
        user_home = os.environ['HOME']
        common_prefix = os.path.commonprefix([user_home, self.name])
        if common_prefix:
            name = '~%s' % self.name[len(common_prefix):]
        else:
            name = self.name
        return '%-18s %-s' % (name, self.status)


class Dotfiles(object):
    """A Dotfiles Repository."""

    __attrs__ = ['homedir', 'repository', 'prefix', 'ignore', 'externals',
            'packages', 'dry_run']

    def __init__(self, **kwargs):

        # Map args from kwargs to instance-local variables
        for k, v in kwargs.items():
            if k in self.__attrs__:
                setattr(self, k, v)

        self._load()

    def _load(self):
        """Load each dotfile in the repository."""

        self.dotfiles = list()
        self._load_recursive()

    def _load_recursive(self, sub_dir=''):
        """Recursive helper for :meth:`_load`."""

        src_dir = os.path.join(self.repository, sub_dir)
        if sub_dir:
            # Add a dot to first level of packages
            dst_dir = os.path.join(self.homedir, '.%s' % sub_dir)
        else:
            dst_dir = os.path.join(self.homedir, sub_dir)

        all_repofiles = os.listdir(src_dir)
        repofiles_to_symlink = set(all_repofiles)

        for pat in self.ignore:
            repofiles_to_symlink.difference_update(
                    fnmatch.filter(all_repofiles, pat))

        for dotfile in repofiles_to_symlink:
            pkg_path = os.path.join(sub_dir, dotfile)
            if pkg_path in self.packages:
                self._load_recursive(pkg_path)
            else:
                self.dotfiles.append(Dotfile(dotfile[len(self.prefix):],
                    os.path.join(src_dir, dotfile), dst_dir,
                    add_dot=not bool(sub_dir), dry_run=self.dry_run))

        # Externals are top-level only
        if not sub_dir:
            for dotfile in self.externals.keys():
                self.dotfiles.append(Dotfile(dotfile,
                    os.path.expanduser(self.externals[dotfile]),
                    dst_dir, add_dot=not bool(sub_dir), dry_run=self.dry_run))

    def _fqpn(self, dotfile, pkg_name=None):
        """Return the fully qualified path to a dotfile."""
        if pkg_name is None:
            return os.path.join(self.repository,
                    self.prefix + os.path.basename(dotfile).strip('.'))
        return os.path.join(self.repository, self.prefix + pkg_name,
                os.path.basename(dotfile))

    def list(self, verbose=True):
        """List the contents of this repository."""

        for dotfile in sorted(self.dotfiles, key=lambda dotfile: dotfile.name):
            if dotfile.status or verbose:
                print(dotfile)

    def check(self):
        """List only unsynced and/or missing dotfiles."""

        self.list(verbose=False)

    def sync(self, files=None, force=False):

        """Synchronize this repository, creating and updating the necessary
        symbolic links."""

        # unless a set of files is specified, operate on all files
        if not files:
            dotfiles = self.dotfiles
        else:
            files = set(map(lambda x: os.path.join(self.homedir, x), files))
            dotfiles = [x for x in self.dotfiles if x.name in files]
            if not dotfiles:
                raise Exception("file not found")

        for dotfile in dotfiles:
            dotfile.sync(force)

    def add(self, files):
        """Add dotfile(s) to the repository."""

        self._perform_action('add', files)

    def remove(self, files):
        """Remove dotfile(s) from the repository."""

        self._perform_action('remove', files)

    def _perform_action(self, action, files):
        for file in files:
            file = file.rstrip('/')
            # See if file is inside a package
            file_dir, file_name = os.path.split(file)
            common_prefix = os.path.commonprefix([self.homedir, file_dir])
            sub_dir = file_dir[len(common_prefix) + 1:]
            pkg_name = sub_dir.lstrip('.')
            if pkg_name in self.packages:
                home = os.path.join(self.homedir, sub_dir)
                target = self._fqpn(file, pkg_name=pkg_name)
                dirname = os.path.dirname(target)
                if not os.path.exists(dirname):
                    os.makedirs(dirname)
            else:
                home = self.homedir
                target = self._fqpn(file)
                if action == 'add' and os.path.split(target)[1] in self.packages:
                    print("Skipping \"%s\", packages not yet supported" % file)
                    return
            if sub_dir.startswith('.') or file_name.startswith('.'):
                dotfile = Dotfile(file, target, home, dry_run=self.dry_run)
                getattr(dotfile, action)()
            else:
                print("Skipping \"%s\", not a dotfile" % file)

    def move(self, target):
        """Move the repository to another location."""
        target = realpath_expanduser(target)

        if os.path.exists(target):
            raise ValueError('Target already exists: %s' % (target))

        if not self.dry_run:
            shutil.copytree(self.repository, target, symlinks=True)
            shutil.rmtree(self.repository)
        else:
            print("Recursive copy %s => %s" % (self.repository, target))
            print("Removing %s and everything under it" % self.repository)

        self.repository = target

        if not self.dry_run:
            self._load()
            self.sync(force=True)

########NEW FILE########
__FILENAME__ = utils
"""
Misc utility functions.
"""

import os.path

from dotfiles.compat import islink, realpath


def compare_path(path1, path2):
    return (realpath_expanduser(path1) == realpath_expanduser(path2))


def realpath_expanduser(path):
    return realpath(os.path.expanduser(path))


def is_link_to(path, target):
    def normalize(path):
        return os.path.normcase(os.path.normpath(path))
    return islink(path) and \
        normalize(realpath(path)) == normalize(realpath(target))

########NEW FILE########
__FILENAME__ = test_dotfiles
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import with_statement

import os
import shutil
import tempfile
import unittest

from dotfiles import core
from dotfiles import cli
from dotfiles.utils import is_link_to


def touch(fname, times=None):
    with open(fname, 'a'):
        os.utime(fname, times)


class DotfilesTestCase(unittest.TestCase):

    def setUp(self):
        """Create a temporary home directory."""

        self.homedir = tempfile.mkdtemp()

        # Create a repository for the tests to use.
        self.repository = os.path.join(self.homedir, 'Dotfiles')
        os.mkdir(self.repository)

    def tearDown(self):
        """Delete the temporary home directory and its contents."""

        shutil.rmtree(self.homedir)

    def assertPathEqual(self, path1, path2):
        self.assertEqual(
            os.path.realpath(path1),
            os.path.realpath(path2))

    def test_force_sync_directory(self):
        """Test forced sync when the dotfile is a directory.

        I installed the lastpass chrome extension which stores a socket in
        ~/.lastpass. So I added that directory as an external to /tmp and
        attempted a forced sync. An error occurred because sync() calls
        os.remove() as it mistakenly assumes the dotfile is a file and not
        a directory.
        """

        os.mkdir(os.path.join(self.homedir, '.lastpass'))
        externals = {'.lastpass': '/tmp'}

        dotfiles = core.Dotfiles(
                homedir=self.homedir, repository=self.repository,
                prefix='', ignore=[], externals=externals, packages=[],
                dry_run=False)

        dotfiles.sync(force=True)

        self.assertPathEqual(
                os.path.join(self.homedir, '.lastpass'),
                '/tmp')

    def test_dispatch(self):
        """Test that the force option is handed on to the sync method."""
        class MockDotfiles(object):
            def sync(self, files=None, force=False):
                assert bool(force)
        dotfiles = MockDotfiles()
        cli.dispatch(dotfiles, 'sync', True, [])

    def test_move_repository(self):
        """Test the move() method for a Dotfiles repository."""

        touch(os.path.join(self.repository, 'bashrc'))

        dotfiles = core.Dotfiles(
                homedir=self.homedir, repository=self.repository,
                prefix='', ignore=[], force=True, externals={}, packages=[],
                dry_run=False)

        dotfiles.sync()

        # Make sure sync() did the right thing.
        self.assertPathEqual(
                os.path.join(self.homedir, '.bashrc'),
                os.path.join(self.repository, 'bashrc'))

        target = os.path.join(self.homedir, 'MyDotfiles')

        dotfiles.move(target)

        self.assertTrue(os.path.exists(os.path.join(target, 'bashrc')))
        self.assertPathEqual(
                os.path.join(self.homedir, '.bashrc'),
                os.path.join(target, 'bashrc'))

    def test_force_sync_directory_symlink(self):
        """Test a forced sync on a directory symlink.

        A bug was reported where a user wanted to replace a dotfile repository
        with an other one. They had a .vim directory in their home directory
        which was obviously also a symbolic link. This caused:

        OSError: Cannot call rmtree on a symbolic link
        """

        # Create a dotfile symlink to some directory
        os.mkdir(os.path.join(self.homedir, 'vim'))
        os.symlink(os.path.join(self.homedir, 'vim'),
                   os.path.join(self.homedir, '.vim'))

        # Create a vim directory in the repository. This will cause the above
        # symlink to be overwritten on sync.
        os.mkdir(os.path.join(self.repository, 'vim'))

        # Make sure the symlink points to the correct location.
        self.assertPathEqual(
                os.path.join(self.homedir, '.vim'),
                os.path.join(self.homedir, 'vim'))

        dotfiles = core.Dotfiles(
                homedir=self.homedir, repository=self.repository,
                prefix='', ignore=[], externals={}, packages=[], dry_run=False)

        dotfiles.sync(force=True)

        # The symlink should now point to the directory in the repository.
        self.assertPathEqual(
                os.path.join(self.homedir, '.vim'),
                os.path.join(self.repository, 'vim'))

    def test_glob_ignore_pattern(self):
        """ Test that the use of glob pattern matching works in the ignores list.

        The following repo dir exists:

        myscript.py
        myscript.pyc
        myscript.pyo
        bashrc
        bashrc.swp
        vimrc
        vimrc.swp
        install.sh

        Using the glob pattern dotfiles should have the following sync result in home:

        .myscript.py -> Dotfiles/myscript.py
        .bashrc -> Dotfiles/bashrc
        .vimrc -> Dotfiles/vimrc

        """
        ignore = ['*.swp', '*.py?', 'install.sh']

        all_repo_files = (
            ('myscript.py', '.myscript.py'),
            ('myscript.pyc', None),
            ('myscript.pyo', None),
            ('bashrc', '.bashrc'),
            ('bashrc.swp', None),
            ('vimrc', '.vimrc'),
            ('vimrc.swp', None),
            ('install.sh', None)
        )

        all_dotfiles = [f for f in all_repo_files if f[1] is not None]

        for original, symlink in all_repo_files:
            touch(os.path.join(self.repository, original))

        dotfiles = core.Dotfiles(
                homedir=self.homedir, repository=self.repository,
                prefix='', ignore=ignore, externals={}, packages=[],
                dry_run=False)

        dotfiles.sync()

        # Now check that the files that should have a symlink
        # point to the correct file and are the only files that
        # exist in the home dir.
        self.assertEqual(
            sorted(os.listdir(self.homedir)),
            sorted([f[1] for f in all_dotfiles] + ['Dotfiles']))

        for original, symlink in all_dotfiles:
            self.assertPathEqual(
                os.path.join(self.repository, original),
                os.path.join(self.homedir, symlink))

    def test_packages(self):
        """
        Test packages.
        """
        files = ['foo', 'package/bar']
        symlinks = ['.foo', '.package/bar']
        join = os.path.join

        # Create files
        for filename in files:
            path = join(self.repository, filename)
            dirname = os.path.dirname(path)
            if not os.path.exists(dirname):
                os.makedirs(dirname)
            touch(path)

        # Create Dotfiles object
        dotfiles = core.Dotfiles(
                homedir=self.homedir, repository=self.repository,
                prefix='', ignore=[], externals={}, packages=['package'],
                dry_run=False)

        # Create symlinks in homedir
        dotfiles.sync()

        # Verify it created what we expect
        def check_all(files, symlinks):
            self.assertTrue(os.path.isdir(join(self.homedir, '.package')))
            for src, dst in zip(files, symlinks):
                self.assertTrue(is_link_to(join(self.homedir, dst),
                    join(self.repository, src)))
        check_all(files, symlinks)

        # Add files to the repository
        new_files = [join(self.homedir, f) for f in ['.bar', '.package/foo']]
        for filename in new_files:
            path = join(self.homedir, filename)
            touch(path)
        new_repo_files = ['bar', 'package/foo']
        dotfiles.add(new_files)
        check_all(files + new_repo_files, symlinks + new_files)

        # Remove them from the repository
        dotfiles.remove(new_files)
        check_all(files, symlinks)

        # Move the repository
        self.repository = join(self.homedir, 'Dotfiles2')
        dotfiles.move(self.repository)
        check_all(files, symlinks)

    def test_missing_package(self):
        """
        Test a non-existent package.
        """

        package_file = '.package/bar'

        # Create Dotfiles object
        dotfiles = core.Dotfiles(
                homedir=self.homedir, repository=self.repository,
                prefix='', ignore=[], externals={}, packages=['package'],
                dry_run=False)

        path = os.path.join(self.homedir, package_file)
        dirname = os.path.dirname(path)
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        touch(path)

        dotfiles.add([os.path.join(self.homedir, package_file)])


    def test_single_sync(self):
        """
        Test syncing a single file in the repo

        The following repo dir exists:

        bashrc
        netrc
        vimrc

        Syncing only vimrc should have the folowing sync result in home:

        .vimrc -> Dotfiles/vimrc

        """

        # define the repository contents
        repo_files = (
            ('bashrc', False),
            ('netrc',  False),
            ('vimrc',  True))

        # populate the repository
        for dotfile, _ in repo_files:
            touch(os.path.join(self.repository, dotfile))

        dotfiles = core.Dotfiles(
                homedir=self.homedir, repository=self.repository,
                prefix='', ignore=[], externals={}, packages=[],
                dry_run=False)

        # sync only certain dotfiles
        for dotfile, should_sync in repo_files:
            if should_sync:
                dotfiles.sync(files=['.%s' % dotfile])

        # verify home directory contents
        for dotfile, should_sync in repo_files:
            if should_sync:
                self.assertPathEqual(
                    os.path.join(self.repository, dotfile),
                    os.path.join(self.homedir, '.%s' % dotfile))
            else:
                self.assertFalse(os.path.exists(
                    os.path.join(self.homedir, dotfile)))


    def test_missing_remove(self):
        """Test removing a dotfile that's been removed from the repository."""

        repo_file = os.path.join(self.repository, 'testdotfile')

        touch(repo_file)

        dotfiles = core.Dotfiles(
                homedir=self.homedir, repository=self.repository,
                prefix='', ignore=[], externals={}, packages=[],
                dry_run=False)

        dotfiles.sync()

        # remove the dotfile from the repository, homedir symlink is now broken
        os.remove(repo_file)

        # remove the broken symlink
        dotfiles.remove(['.testdotfile'])

        # verify symlink was removed
        self.assertFalse(os.path.exists(
            os.path.join(self.homedir, '.testdotfile')))


    def test_add_package(self):
        """
        Test adding a package that isn't already in the repository

        """

        package_dir = os.path.join(self.homedir,
            '.%s/%s' % ('config', 'gtk-3.0'))

        os.makedirs(package_dir)
        touch('%s/testfile' % package_dir)

        dotfiles = core.Dotfiles(
                homedir=self.homedir, repository=self.repository,
                prefix='', ignore=[], externals={}, packages=['config'],
                dry_run=False, quiet=True)

        # This should fail, you should not be able to add dotfiles that are
        # defined to be packages.
        dotfiles.add(['.config'])
        self.assertFalse(os.path.islink(os.path.join(self.homedir, '.config')))


    def test_package_and_prefix(self):
        """Test syncing a package when using a non-default prefix."""

        package_dir = os.path.join(self.repository, '.config/awesome')
        os.makedirs(package_dir)
        touch('%s/testfile' % package_dir)

        dotfiles = core.Dotfiles(homedir=self.homedir,
                                 repository=self.repository,
                                 prefix='.',
                                 ignore=[],
                                 externals={},
                                 packages=['.config'],
                                 dry_run=False,
                                 quiet=True)

        dotfiles.sync()

	expected = os.path.join(self.homedir, ".config")
	self.assertTrue(os.path.islink(expected))

	expected = os.path.join(expected, "awesome")
	self.assertTrue(os.path.isdir(expected))

	expected = os.path.join(expected, "testfile")
	self.assertTrue(os.path.isfile(expected))


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
