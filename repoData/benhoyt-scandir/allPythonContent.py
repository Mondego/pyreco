__FILENAME__ = benchmark
"""Simple benchmark to compare the speed of scandir.walk() with os.walk()."""

import optparse
import os
import stat
import sys
import timeit

import scandir

DEPTH = 4
NUM_DIRS = 5
NUM_FILES = 50

# ctypes versions of os.listdir() so benchmark can compare apples with apples
if sys.platform == 'win32':
    import ctypes
    from ctypes import wintypes

    def os_listdir(path):
        data = wintypes.WIN32_FIND_DATAW()
        data_p = ctypes.byref(data)
        filename = os.path.join(path, '*.*')
        handle = scandir.FindFirstFile(filename, data_p)
        if handle == scandir.INVALID_HANDLE_VALUE:
            error = ctypes.GetLastError()
            if error == scandir.ERROR_FILE_NOT_FOUND:
                return []
            raise scandir.win_error(error, path)
        names = []
        try:
            while True:
                name = data.cFileName
                if name not in ('.', '..'):
                    names.append(name)
                success = scandir.FindNextFile(handle, data_p)
                if not success:
                    error = ctypes.GetLastError()
                    if error == scandir.ERROR_NO_MORE_FILES:
                        break
                    raise scandir.win_error(error, path)
        finally:
            if not scandir.FindClose(handle):
                raise scandir.win_error(ctypes.GetLastError(), path)
        return names

elif sys.platform.startswith(('linux', 'darwin')) or 'bsd' in sys.platform:
    def os_listdir(path):
        dir_p = scandir.opendir(path.encode(scandir.file_system_encoding))
        if not dir_p:
            raise scandir.posix_error(path)
        names = []
        try:
            entry = scandir.Dirent()
            result = scandir.Dirent_p()
            while True:
                if scandir.readdir_r(dir_p, entry, result):
                    raise scandir.posix_error(path)
                if not result:
                    break
                name = entry.d_name.decode(scandir.file_system_encoding)
                if name not in ('.', '..'):
                    names.append(name)
        finally:
            if scandir.closedir(dir_p):
                raise scandir.posix_error(path)
        return names

else:
    os_listdir = os.listdir

def os_walk(top, topdown=True, onerror=None, followlinks=False):
    """Identical to os.walk(), but use ctypes-based listdir() so benchmark
    against ctypes-based scandir() is valid.
    """
    try:
        names = os_listdir(top)
    except OSError as err:
        if onerror is not None:
            onerror(err)
        return

    dirs, nondirs = [], []
    for name in names:
        if os.path.isdir(os.path.join(top, name)):
            dirs.append(name)
        else:
            nondirs.append(name)

    if topdown:
        yield top, dirs, nondirs
    for name in dirs:
        new_path = os.path.join(top, name)
        if followlinks or not os.path.islink(new_path):
            for x in os_walk(new_path, topdown, onerror, followlinks):
                yield x
    if not topdown:
        yield top, dirs, nondirs

def create_tree(path, depth=DEPTH):
    """Create a directory tree at path with given depth, and NUM_DIRS and
    NUM_FILES at each level.
    """
    os.mkdir(path)
    for i in range(NUM_FILES):
        filename = os.path.join(path, 'file{0:03}.txt'.format(i))
        with open(filename, 'wb') as f:
            f.write(b'foo')
    if depth <= 1:
        return
    for i in range(NUM_DIRS):
        dirname = os.path.join(path, 'dir{0:03}'.format(i))
        create_tree(dirname, depth - 1)

def get_tree_size(path):
    """Return total size of all files in directory tree at path."""
    size = 0
    try:
        for entry in scandir.scandir(path):
            if entry.is_dir():
                size += get_tree_size(os.path.join(path, entry.name))
            else:
                size += entry.lstat().st_size
    except OSError:
        pass
    return size

def benchmark(path, get_size=False):
    sizes = {}

    if get_size:
        def do_os_walk():
            size = 0
            for root, dirs, files in os_walk(path):
                for filename in files:
                    fullname = os.path.join(root, filename)
                    size += os.path.getsize(fullname)
            sizes['os_walk'] = size

        def do_scandir_walk():
            sizes['scandir_walk'] = get_tree_size(path)

    else:
        def do_os_walk():
            for root, dirs, files in os_walk(path):
                pass

        def do_scandir_walk():
            for root, dirs, files in scandir.walk(path):
                pass

    # Run this once first to cache things, so we're not benchmarking I/O
    print("Priming the system's cache...")
    do_scandir_walk()

    # Use the best of 3 time for each of them to eliminate high outliers
    os_walk_time = 1000000
    scandir_walk_time = 1000000
    N = 3
    for i in range(N):
        print('Benchmarking walks on {0}, repeat {1}/{2}...'.format(
            path, i + 1, N))
        os_walk_time = min(os_walk_time, timeit.timeit(do_os_walk, number=1))
        scandir_walk_time = min(scandir_walk_time, timeit.timeit(do_scandir_walk, number=1))

    if get_size:
        if sizes['os_walk'] == sizes['scandir_walk']:
            equality = 'equal'
        else:
            equality = 'NOT EQUAL!'
        print('os.walk size {0}, scandir.walk size {1} -- {2}'.format(
            sizes['os_walk'], sizes['scandir_walk'], equality))

    print('os.walk took {0:.3f}s, scandir.walk took {1:.3f}s -- {2:.1f}x as fast'.format(
          os_walk_time, scandir_walk_time, os_walk_time / scandir_walk_time))

def main():
    """Usage: benchmark.py [-h] [tree_dir]

Create a large directory tree named "benchtree" (relative to this script) and
benchmark os.walk() versus scandir.walk(). If tree_dir is specified, benchmark
using it instead of creating a tree.
"""
    parser = optparse.OptionParser(usage=main.__doc__.rstrip())
    parser.add_option('-s', '--size', action='store_true',
                      help='get size of directory tree while walking')
    parser.add_option('-r', '--real-os-walk', action='store_true',
                      help='use real os.walk() instead of ctypes emulation')
    options, args = parser.parse_args()

    if args:
        tree_dir = args[0]
    else:
        tree_dir = os.path.join(os.path.dirname(__file__), 'benchtree')
        if not os.path.exists(tree_dir):
            print('Creating tree at {0}: depth={1}, num_dirs={2}, num_files={3}'.format(
                tree_dir, DEPTH, NUM_DIRS, NUM_FILES))
            create_tree(tree_dir)

    if options.real_os_walk:
        global os_walk
        os_walk = os.walk

    if scandir._scandir:
        print 'Using fast C version of scandir'
    else:
        print 'Using slower ctypes version of scandir'

    benchmark(tree_dir, get_size=options.size)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = scandir
"""scandir, a better directory iterator that exposes all file info OS provides

scandir is a generator version of os.listdir() that returns an iterator over
files in a directory, and also exposes the extra information most OSes provide
while iterating files in a directory.

See README.md or https://github.com/benhoyt/scandir for rationale and docs.

scandir is released under the new BSD 3-clause license. See LICENSE.txt for
the full license text.
"""

from __future__ import division

import ctypes
import os
import stat
import sys

__version__ = '0.3'
__all__ = ['scandir', 'walk']

# Shortcuts to these functions for speed and ease
join = os.path.join
lstat = os.lstat

S_IFDIR = stat.S_IFDIR
S_IFREG = stat.S_IFREG
S_IFLNK = stat.S_IFLNK

# 'unicode' isn't defined on Python 3
try:
    unicode
except NameError:
    unicode = str

_scandir = None


class GenericDirEntry(object):
    __slots__ = ('name', '_lstat', '_path')

    def __init__(self, path, name):
        self._path = path
        self.name = name
        self._lstat = None

    def lstat(self):
        if self._lstat is None:
            self._lstat = lstat(join(self._path, self.name))
        return self._lstat

    def is_dir(self):
        try:
            self.lstat()
        except OSError:
            return False
        return self._lstat.st_mode & 0o170000 == S_IFDIR

    def is_file(self):
        try:
            self.lstat()
        except OSError:
            return False
        return self._lstat.st_mode & 0o170000 == S_IFREG

    def is_symlink(self):
        try:
            self.lstat()
        except OSError:
            return False
        return self._lstat.st_mode & 0o170000 == S_IFLNK

    def __str__(self):
        return '<{0}: {1!r}>'.format(self.__class__.__name__, self.name)

    __repr__ = __str__


if sys.platform == 'win32':
    from ctypes import wintypes

    # Various constants from windows.h
    INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value
    ERROR_FILE_NOT_FOUND = 2
    ERROR_NO_MORE_FILES = 18
    FILE_ATTRIBUTE_READONLY = 1
    FILE_ATTRIBUTE_DIRECTORY = 16
    FILE_ATTRIBUTE_REPARSE_POINT = 1024

    # Numer of seconds between 1601-01-01 and 1970-01-01
    SECONDS_BETWEEN_EPOCHS = 11644473600

    kernel32 = ctypes.windll.kernel32

    # ctypes wrappers for (wide string versions of) FindFirstFile,
    # FindNextFile, and FindClose
    FindFirstFile = kernel32.FindFirstFileW
    FindFirstFile.argtypes = [
        wintypes.LPCWSTR,
        ctypes.POINTER(wintypes.WIN32_FIND_DATAW),
    ]
    FindFirstFile.restype = wintypes.HANDLE

    FindNextFile = kernel32.FindNextFileW
    FindNextFile.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(wintypes.WIN32_FIND_DATAW),
    ]
    FindNextFile.restype = wintypes.BOOL

    FindClose = kernel32.FindClose
    FindClose.argtypes = [wintypes.HANDLE]
    FindClose.restype = wintypes.BOOL

    def filetime_to_time(filetime):
        """Convert Win32 FILETIME to time since Unix epoch in seconds."""
        total = filetime.dwHighDateTime << 32 | filetime.dwLowDateTime
        return total / 10000000 - SECONDS_BETWEEN_EPOCHS

    def find_data_to_stat(data):
        """Convert Win32 FIND_DATA struct to stat_result."""
        # First convert Win32 dwFileAttributes to st_mode
        attributes = data.dwFileAttributes
        st_mode = 0
        if attributes & FILE_ATTRIBUTE_DIRECTORY:
            st_mode |= S_IFDIR | 0o111
        else:
            st_mode |= S_IFREG
        if attributes & FILE_ATTRIBUTE_READONLY:
            st_mode |= 0o444
        else:
            st_mode |= 0o666
        if attributes & FILE_ATTRIBUTE_REPARSE_POINT:
            st_mode |= S_IFLNK

        st_size = data.nFileSizeHigh << 32 | data.nFileSizeLow
        st_atime = filetime_to_time(data.ftLastAccessTime)
        st_mtime = filetime_to_time(data.ftLastWriteTime)
        st_ctime = filetime_to_time(data.ftCreationTime)

        # Some fields set to zero per CPython's posixmodule.c: st_ino, st_dev,
        # st_nlink, st_uid, st_gid
        return os.stat_result((st_mode, 0, 0, 0, 0, 0, st_size, st_atime,
                               st_mtime, st_ctime))

    class Win32DirEntry(object):
        __slots__ = ('name', '_lstat', '_find_data')

        def __init__(self, name, find_data):
            self.name = name
            self._lstat = None
            self._find_data = find_data

        def lstat(self):
            if self._lstat is None:
                # Lazily convert to stat object, because it's slow, and often
                # we only need is_dir() etc
                self._lstat = find_data_to_stat(self._find_data)
            return self._lstat

        def is_dir(self):
            return (self._find_data.dwFileAttributes &
                    FILE_ATTRIBUTE_DIRECTORY != 0)

        def is_file(self):
            return (self._find_data.dwFileAttributes &
                    FILE_ATTRIBUTE_DIRECTORY == 0)

        def is_symlink(self):
            return (self._find_data.dwFileAttributes &
                    FILE_ATTRIBUTE_REPARSE_POINT != 0)

        def __str__(self):
            return '<{0}: {1!r}>'.format(self.__class__.__name__, self.name)

        __repr__ = __str__

    def win_error(error, filename):
        exc = WindowsError(error, ctypes.FormatError(error))
        exc.filename = filename
        return exc

    def scandir(path='.', windows_wildcard='*.*'):
        """Like os.listdir(), but yield DirEntry objects instead of returning
        a list of names.
        """
        # Call FindFirstFile and handle errors
        data = wintypes.WIN32_FIND_DATAW()
        data_p = ctypes.byref(data)
        filename = join(path, windows_wildcard)
        handle = FindFirstFile(filename, data_p)
        if handle == INVALID_HANDLE_VALUE:
            error = ctypes.GetLastError()
            if error == ERROR_FILE_NOT_FOUND:
                # No files, don't yield anything
                return
            raise win_error(error, path)

        # Call FindNextFile in a loop, stopping when no more files
        try:
            while True:
                # Skip '.' and '..' (current and parent directory), but
                # otherwise yield (filename, stat_result) tuple
                name = data.cFileName
                if name not in ('.', '..'):
                    yield Win32DirEntry(name, data)

                data = wintypes.WIN32_FIND_DATAW()
                data_p = ctypes.byref(data)
                success = FindNextFile(handle, data_p)
                if not success:
                    error = ctypes.GetLastError()
                    if error == ERROR_NO_MORE_FILES:
                        break
                    raise win_error(error, path)
        finally:
            if not FindClose(handle):
                raise win_error(ctypes.GetLastError(), path)

    try:
        import _scandir

        scandir_helper = _scandir.scandir_helper

        class Win32DirEntry(object):
            __slots__ = ('name', '_lstat')

            def __init__(self, name, lstat):
                self.name = name
                self._lstat = lstat

            def lstat(self):
                return self._lstat

            def is_dir(self):
                return self._lstat.st_mode & 0o170000 == S_IFDIR

            def is_file(self):
                return self._lstat.st_mode & 0o170000 == S_IFREG

            def is_symlink(self):
                return self._lstat.st_mode & 0o170000 == S_IFLNK

            def __str__(self):
                return '<{0}: {1!r}>'.format(self.__class__.__name__, self.name)

            __repr__ = __str__

        def scandir(path='.'):
            for name, stat in scandir_helper(unicode(path)):
                yield Win32DirEntry(name, stat)

    except ImportError:
        pass


# Linux, OS X, and BSD implementation
elif sys.platform.startswith(('linux', 'darwin')) or 'bsd' in sys.platform:
    import ctypes.util

    DIR_p = ctypes.c_void_p

    # Rather annoying how the dirent struct is slightly different on each
    # platform. The only fields we care about are d_name and d_type.
    class Dirent(ctypes.Structure):
        if sys.platform.startswith('linux'):
            _fields_ = (
                ('d_ino', ctypes.c_ulong),
                ('d_off', ctypes.c_long),
                ('d_reclen', ctypes.c_ushort),
                ('d_type', ctypes.c_byte),
                ('d_name', ctypes.c_char * 256),
            )
        else:
            _fields_ = (
                ('d_ino', ctypes.c_uint32),  # must be uint32, not ulong
                ('d_reclen', ctypes.c_ushort),
                ('d_type', ctypes.c_byte),
                ('d_namlen', ctypes.c_byte),
                ('d_name', ctypes.c_char * 256),
            )

    DT_UNKNOWN = 0
    DT_DIR = 4
    DT_REG = 8
    DT_LNK = 10

    Dirent_p = ctypes.POINTER(Dirent)
    Dirent_pp = ctypes.POINTER(Dirent_p)

    libc = ctypes.CDLL(ctypes.util.find_library('c'), use_errno=True)
    opendir = libc.opendir
    opendir.argtypes = [ctypes.c_char_p]
    opendir.restype = DIR_p

    readdir_r = libc.readdir_r
    readdir_r.argtypes = [DIR_p, Dirent_p, Dirent_pp]
    readdir_r.restype = ctypes.c_int

    closedir = libc.closedir
    closedir.argtypes = [DIR_p]
    closedir.restype = ctypes.c_int

    file_system_encoding = sys.getfilesystemencoding()

    class PosixDirEntry(object):
        __slots__ = ('name', '_d_type', '_lstat', '_path')

        def __init__(self, path, name, d_type):
            self._path = path
            self.name = name
            self._d_type = d_type
            self._lstat = None

        def lstat(self):
            if self._lstat is None:
                self._lstat = lstat(join(self._path, self.name))
            return self._lstat

        # Ridiculous duplication between these is* functions -- helps a little
        # bit with os.walk() performance compared to calling another function.
        def is_dir(self):
            d_type = self._d_type
            if d_type != DT_UNKNOWN:
                return d_type == DT_DIR
            try:
                self.lstat()
            except OSError:
                return False
            return self._lstat.st_mode & 0o170000 == S_IFDIR

        def is_file(self):
            d_type = self._d_type
            if d_type != DT_UNKNOWN:
                return d_type == DT_REG
            try:
                self.lstat()
            except OSError:
                return False
            return self._lstat.st_mode & 0o170000 == S_IFREG

        def is_symlink(self):
            d_type = self._d_type
            if d_type != DT_UNKNOWN:
                return d_type == DT_LNK
            try:
                self.lstat()
            except OSError:
                return False
            return self._lstat.st_mode & 0o170000 == S_IFLNK

        def __str__(self):
            return '<{0}: {1!r}>'.format(self.__class__.__name__, self.name)

        __repr__ = __str__

    def posix_error(filename):
        errno = ctypes.get_errno()
        exc = OSError(errno, os.strerror(errno))
        exc.filename = filename
        return exc

    def scandir(path='.'):
        """Like os.listdir(), but yield DirEntry objects instead of returning
        a list of names.
        """
        dir_p = opendir(path.encode(file_system_encoding))
        if not dir_p:
            raise posix_error(path)
        try:
            result = Dirent_p()
            while True:
                entry = Dirent()
                if readdir_r(dir_p, entry, result):
                    raise posix_error(path)
                if not result:
                    break
                name = entry.d_name.decode(file_system_encoding)
                if name not in ('.', '..'):
                    yield PosixDirEntry(path, name, entry.d_type)
        finally:
            if closedir(dir_p):
                raise posix_error(path)

    try:
        import _scandir

        scandir_helper = _scandir.scandir_helper

        def scandir(path='.'):
            for name, d_type in scandir_helper(unicode(path)):
                yield PosixDirEntry(path, name, d_type)

    except ImportError:
        pass


# Some other system -- no d_type or stat information
else:
    def scandir(path='.'):
        """Like os.listdir(), but yield DirEntry objects instead of returning
        a list of names.
        """
        for name in os.listdir(path):
            yield GenericDirEntry(path, name)


def walk(top, topdown=True, onerror=None, followlinks=False):
    """Like os.walk(), but faster, as it uses scandir() internally."""
    # Determine which are files and which are directories
    dirs = []
    nondirs = []
    try:
        for entry in scandir(top):
            if entry.is_dir():
                dirs.append(entry)
            else:
                nondirs.append(entry)
    except OSError as error:
        if onerror is not None:
            onerror(error)
        return

    # Yield before recursion if going top down
    if topdown:
        # Need to do some fancy footwork here as caller is allowed to modify
        # dir_names, and we really want them to modify dirs (list of DirEntry
        # objects) instead. Keep a mapping of entries keyed by name.
        dir_names = []
        entries_by_name = {}
        for entry in dirs:
            dir_names.append(entry.name)
            entries_by_name[entry.name] = entry

        yield top, dir_names, [e.name for e in nondirs]

        dirs = []
        for dir_name in dir_names:
            entry = entries_by_name.get(dir_name)
            if entry is None:
                # Only happens when caller creates a new directory and adds it
                # to dir_names
                entry = GenericDirEntry(top, dir_name)
            dirs.append(entry)

    # Recurse into sub-directories, following symbolic links if "followlinks"
    for entry in dirs:
        if followlinks or not entry.is_symlink():
            new_path = join(top, entry.name)
            for x in walk(new_path, topdown, onerror, followlinks):
                yield x

    # Yield before recursion if going bottom up
    if not topdown:
        yield top, [e.name for e in dirs], [e.name for e in nondirs]

########NEW FILE########
__FILENAME__ = run_tests
"""Run all unit tests."""

import glob
import os
import sys
import unittest

def main():
    test_dir = os.path.dirname(os.path.abspath(__file__))
    test_files = glob.glob(os.path.join(test_dir, 'test_*.py'))
    test_names = [os.path.basename(f)[:-3] for f in test_files]

    sys.path.insert(0, os.path.join(test_dir, '..'))

    suite = unittest.defaultTestLoader.loadTestsFromNames(test_names)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(1 if (result.errors or result.failures) else 0)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = test_scandir
"""Tests for scandir.scandir()."""

import os
import sys
import unittest

import scandir

test_path = os.path.join(os.path.dirname(__file__), 'dir')

class TestScandir(unittest.TestCase):
    def test_basic(self):
        entries = sorted(scandir.scandir(test_path), key=lambda e: e.name)
        self.assertEqual([(e.name, e.isdir()) for e in entries],
                         [('file1.txt', False), ('file2.txt', False), ('subdir', True)])

    def test_dir_entry(self):
        entries = dict((e.name, e) for e in scandir.scandir(test_path))
        e = entries['file1.txt']
        self.assertEquals([e.isdir(), e.isfile(), e.islink()], [False, True, False])
        e = entries['file2.txt']
        self.assertEquals([e.isdir(), e.isfile(), e.islink()], [False, True, False])
        e = entries['subdir']
        self.assertEquals([e.isdir(), e.isfile(), e.islink()], [True, False, False])

        self.assertEquals(entries['file1.txt'].lstat().st_size, 4)
        self.assertEquals(entries['file2.txt'].lstat().st_size, 8)

        if sys.platform == 'win32':
            assert entries['file1.txt'].dirent is None
        else:
            assert entries['file1.txt'].dirent is not None
            assert isinstance(entries['file1.txt'].dirent.d_ino, (int, long))
            assert isinstance(entries['file1.txt'].dirent.d_type, int)

    def test_stat(self):
        entries = list(scandir.scandir(test_path))
        for entry in entries:
            os_stat = os.lstat(os.path.join(test_path, entry.name))
            scandir_stat = entry.lstat()
            self.assertEquals(os_stat.st_mode, scandir_stat.st_mode)
            self.assertEquals(int(os_stat.st_mtime), int(scandir_stat.st_mtime))
            self.assertEquals(int(os_stat.st_ctime), int(scandir_stat.st_ctime))
            self.assertEquals(os_stat.st_size, scandir_stat.st_size)

    def test_returns_iter(self):
        it = scandir.scandir(test_path)
        entry = next(it)
        assert hasattr(entry, 'name')

########NEW FILE########
__FILENAME__ = test_walk
"""Tests for scandir.walk(), copied from CPython's tests for os.walk()."""

import os
import unittest

import scandir

walk_func = scandir.walk

class TestWalk(unittest.TestCase):
    testfn = os.path.join(os.path.dirname(__file__), 'temp')

    def test_traversal(self):
        # Build:
        #     TESTFN/
        #       TEST1/              a file kid and two directory kids
        #         tmp1
        #         SUB1/             a file kid and a directory kid
        #           tmp2
        #           SUB11/          no kids
        #         SUB2/             a file kid and a dirsymlink kid
        #           tmp3
        #           link/           a symlink to TESTFN.2
        #       TEST2/
        #         tmp4              a lone file
        walk_path = os.path.join(self.testfn, "TEST1")
        sub1_path = os.path.join(walk_path, "SUB1")
        sub11_path = os.path.join(sub1_path, "SUB11")
        sub2_path = os.path.join(walk_path, "SUB2")
        tmp1_path = os.path.join(walk_path, "tmp1")
        tmp2_path = os.path.join(sub1_path, "tmp2")
        tmp3_path = os.path.join(sub2_path, "tmp3")
        link_path = os.path.join(sub2_path, "link")
        t2_path = os.path.join(self.testfn, "TEST2")
        tmp4_path = os.path.join(self.testfn, "TEST2", "tmp4")

        # Create stuff.
        os.makedirs(sub11_path)
        os.makedirs(sub2_path)
        os.makedirs(t2_path)
        for path in tmp1_path, tmp2_path, tmp3_path, tmp4_path:
            f = open(path, "w")
            f.write("I'm " + path + " and proud of it.  Blame test_os.\n")
            f.close()
        has_symlink = hasattr(os, "symlink")
        if has_symlink:
            try:
                os.symlink(os.path.abspath(t2_path), link_path, True)
                sub2_tree = (sub2_path, ["link"], ["tmp3"])
            except NotImplementedError:
                sub2_tree = (sub2_path, [], ["tmp3"])
        else:
            sub2_tree = (sub2_path, [], ["tmp3"])

        # Walk top-down.
        all = list(walk_func(walk_path))
        self.assertEqual(len(all), 4)
        # We can't know which order SUB1 and SUB2 will appear in.
        # Not flipped:  TESTFN, SUB1, SUB11, SUB2
        #     flipped:  TESTFN, SUB2, SUB1, SUB11
        flipped = all[0][1][0] != "SUB1"
        all[0][1].sort()
        self.assertEqual(all[0], (walk_path, ["SUB1", "SUB2"], ["tmp1"]))
        self.assertEqual(all[1 + flipped], (sub1_path, ["SUB11"], ["tmp2"]))
        self.assertEqual(all[2 + flipped], (sub11_path, [], []))
        self.assertEqual(all[3 - 2 * flipped], sub2_tree)

        # Prune the search.
        all = []
        for root, dirs, files in walk_func(walk_path):
            all.append((root, dirs, files))
            # Don't descend into SUB1.
            if 'SUB1' in dirs:
                # Note that this also mutates the dirs we appended to all!
                dirs.remove('SUB1')
        self.assertEqual(len(all), 2)
        self.assertEqual(all[0], (walk_path, ["SUB2"], ["tmp1"]))
        self.assertEqual(all[1], sub2_tree)

        # Walk bottom-up.
        all = list(walk_func(walk_path, topdown=False))
        self.assertEqual(len(all), 4)
        # We can't know which order SUB1 and SUB2 will appear in.
        # Not flipped:  SUB11, SUB1, SUB2, TESTFN
        #     flipped:  SUB2, SUB11, SUB1, TESTFN
        flipped = all[3][1][0] != "SUB1"
        all[3][1].sort()
        self.assertEqual(all[3], (walk_path, ["SUB1", "SUB2"], ["tmp1"]))
        self.assertEqual(all[flipped], (sub11_path, [], []))
        self.assertEqual(all[flipped + 1], (sub1_path, ["SUB11"], ["tmp2"]))
        self.assertEqual(all[2 - 2 * flipped], sub2_tree)

        if has_symlink:
            # Walk, following symlinks.
            for root, dirs, files in walk_func(walk_path, followlinks=True):
                if root == link_path:
                    self.assertEqual(dirs, [])
                    self.assertEqual(files, ["tmp4"])
                    break
            else:
                self.fail("Didn't follow symlink with followlinks=True")

        # Test creating a directory and adding it to dirnames
        sub3_path = os.path.join(walk_path, "SUB3")
        all = []
        for root, dirs, files in walk_func(walk_path):
            all.append((root, dirs, files))
            if 'SUB1' in dirs:
                os.makedirs(sub3_path)
                dirs.append('SUB3')
        all.sort()
        self.assertEqual(os.path.split(all[-1][0])[1], 'SUB3')

    def tearDown(self):
        # Tear everything down.  This is a decent use for bottom-up on
        # Windows, which doesn't have a recursive delete command.  The
        # (not so) subtlety is that rmdir will fail unless the dir's
        # kids are removed first, so bottom up is essential.
        for root, dirs, files in os.walk(self.testfn, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                dirname = os.path.join(root, name)
                if not os.path.islink(dirname):
                    os.rmdir(dirname)
                else:
                    os.remove(dirname)
        os.rmdir(self.testfn)

########NEW FILE########
