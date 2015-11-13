__FILENAME__ = test
#!/usr/bin/env python
"""Unit tests for unipath.py

Environment variables:
    DUMP : List the contents of test direcories after each test.
    NO_CLEANUP : Don't delete test directories.
(These are not command-line args due to the difficulty of merging my args
with unittest's.)

IMPORTANT: Tests may not assume what the current directory is because the tests
may have been started from anywhere, and some tests chdir to the temprorary
test directory which is then deleted.
"""
from __future__ import print_function

import ntpath
import os
import posixpath
import tempfile
import time
import sys

import pytest

from unipath import *
from unipath.errors import *
from unipath.tools import dict2dir, dump_path

AbstractPath.auto_norm = False

class PosixPath(AbstractPath):
    pathlib = posixpath


class NTPath(AbstractPath):
    pathlib = ntpath

# Global flags
cleanup = not bool(os.environ.get("NO_CLEANUP"))
dump = bool(os.environ.get("DUMP"))
        

class TestPathConstructor(object):
    def test_posix(self):
        assert str(PosixPath()) == posixpath.curdir
        assert str(PosixPath("foo/bar.py")) == "foo/bar.py"
        assert str(PosixPath("foo", "bar.py")) == "foo/bar.py"
        assert str(PosixPath("foo", "bar", "baz.py")) == "foo/bar/baz.py"
        assert str(PosixPath("foo", PosixPath("bar", "baz.py"))) == "foo/bar/baz.py"
        assert str(PosixPath("foo", ["", "bar", "baz.py"])) == "foo/bar/baz.py"
        assert str(PosixPath("")) == ""
        assert str(PosixPath()) == "."
        assert str(PosixPath("foo", 1, "bar")) == "foo/1/bar"

    def test_nt(self):
        assert str(NTPath()) == ntpath.curdir
        assert str(NTPath(r"foo\bar.py")) == r"foo\bar.py"
        assert str(NTPath("foo", "bar.py")), r"foo\bar.py"
        assert str(NTPath("foo", "bar", "baz.py")) == r"foo\bar\baz.py"
        assert str(NTPath("foo", NTPath("bar", "baz.py"))) == r"foo\bar\baz.py"
        assert str(NTPath("foo", ["", "bar", "baz.py"])) == r"foo\bar\baz.py"
        assert str(PosixPath("")) == ""
        assert str(NTPath()) == "."
        assert str(NTPath("foo", 1, "bar")) == r"foo\1\bar"

    def test_int_arg(self):
        assert str(PosixPath("a", 1)) == "a/1"


class TestNorm(object):
    def test_posix(self):
        assert PosixPath("a//b/../c").norm() == "a/c"
        assert PosixPath("a/./b").norm() == "a/b"
        assert PosixPath("a/./b", norm=True) == "a/b"
        assert PosixPath("a/./b", norm=False) == "a/./b"

        class AutoNormPath(PosixPath):
            auto_norm = True
        assert AutoNormPath("a/./b") == "a/b"
        assert AutoNormPath("a/./b", norm=True) == "a/b"
        assert AutoNormPath("a/./b", norm=False) == "a/./b"

    def test_nt(self):
        assert NTPath(r"a\\b\..\c").norm() == r"a\c"
        assert NTPath(r"a\.\b").norm() == r"a\b"
        assert NTPath("a\\.\\b", norm=True) == "a\\b"
        assert NTPath("a\\.\\b", norm=False) == "a\\.\\b"

        class AutoNormPath(NTPath):
            auto_norm = True
        assert AutoNormPath("a\\.\\b") == "a\\b"
        assert AutoNormPath("a\\.\\b", norm=True) == "a\\b"
        assert AutoNormPath("a\\.\\b", norm=False) == "a\\.\\b"


class TestAbstractPath(object):
    def test_repr(self):
        assert repr(Path("la_la_la")) == "Path('la_la_la')"
        assert repr(NTPath("la_la_la")) == "NTPath('la_la_la')"

    # Not testing expand_user, expand_vars, or expand: too dependent on the
    # OS environment.

    def test_properties(self):
        p = PosixPath("/first/second/third.jpg")
        assert p.parent == "/first/second"
        assert p.name == "third.jpg"
        assert p.ext == ".jpg"
        assert p.stem == "third"

    def test_properties2(self):
        # Usage sample in README is based on this.
        p = PosixPath("/usr/lib/python2.5/gopherlib.py")
        assert p.parent == Path("/usr/lib/python2.5")
        assert p.name == Path("gopherlib.py")
        assert p.ext == ".py"
        assert p.stem == Path("gopherlib")
        q = PosixPath(p.parent, p.stem + p.ext)
        assert q == p

    def test_split_root(self):
        assert PosixPath("foo/bar.py").split_root() == ("", "foo/bar.py")
        assert PosixPath("/foo/bar.py").split_root() == ("/", "foo/bar.py")
        assert NTPath("foo\\bar.py").split_root() == ("", "foo\\bar.py")
        assert NTPath("\\foo\\bar.py").split_root() == ("\\", "foo\\bar.py")
        assert NTPath("C:\\foo\\bar.py").split_root() == ("C:\\", "foo\\bar.py")
        assert NTPath("C:foo\\bar.py").split_root() == ("C:", "foo\\bar.py")
        assert NTPath("\\\\share\\base\\foo\\bar.py").split_root() == ("\\\\share\\base\\", "foo\\bar.py")

    def test_split_root_vs_isabsolute(self):
        assert not PosixPath("a/b/c").isabsolute()
        assert not PosixPath("a/b/c").split_root()[0]
        assert PosixPath("/a/b/c").isabsolute()
        assert PosixPath("/a/b/c").split_root()[0]
        assert not NTPath("a\\b\\c").isabsolute()
        assert not NTPath("a\\b\\c").split_root()[0]
        assert NTPath("\\a\\b\\c").isabsolute()
        assert NTPath("\\a\\b\\c").split_root()[0]
        assert NTPath("C:\\a\\b\\c").isabsolute()
        assert NTPath("C:\\a\\b\\c").split_root()[0]
        assert NTPath("C:a\\b\\c").isabsolute()
        assert NTPath("C:a\\b\\c").split_root()[0]
        assert NTPath("\\\\share\\b\\c").isabsolute()
        assert NTPath("\\\\share\\b\\c").split_root()[0]

    def test_components(self):
        P = PosixPath
        assert P("a").components() == [P(""), P("a")]
        assert P("a/b/c").components() == [P(""), P("a"), P("b"), P("c")]
        assert P("/a/b/c").components() == [P("/"), P("a"), P("b"), P("c")]
        P = NTPath
        assert P("a\\b\\c").components() == [P(""), P("a"), P("b"), P("c")]
        assert P("\\a\\b\\c").components() == [P("\\"), P("a"), P("b"), P("c")]
        assert P("C:\\a\\b\\c").components() == [P("C:\\"), P("a"), P("b"), P("c")]
        assert P("C:a\\b\\c").components() == [P("C:"), P("a"), P("b"), P("c")]
        assert P("\\\\share\\b\\c").components() == [P("\\\\share\\b\\"), P("c")]

    def test_child(self):
        PosixPath("foo/bar").child("baz")
        with pytest.raises(UnsafePathError):
            PosixPath("foo/bar").child("baz/fred")
            PosixPath("foo/bar").child("..", "baz")
            PosixPath("foo/bar").child(".", "baz")


class TestStringMethods(object):
    def test_add(self):
        P = PosixPath
        assert P("a") + P("b") == P("ab")
        assert P("a") + "b" == P("ab")
        assert "a" + P("b") == P("ab")


class FilesystemTest(object):
    TEST_HIERARCHY = {
        "a_file":  "Nothing important.",
        "animals": {
            "elephant":  "large",
            "gonzo":  "unique",
            "mouse":  "small"},
        "images": {
            "image1.gif": "",
            "image2.jpg": "",
            "image3.png": ""},
        "swedish": {
            "chef": {
                "bork": {
                    "bork": "bork!"}}},
    }

    def setup_method(self, method):
        self.d = d = Path(tempfile.mkdtemp())
        dict2dir(d, self.TEST_HIERARCHY)
        self.a_file = Path(d, "a_file")
        self.animals = Path(d, "animals")
        self.images = Path(d, "images")
        self.chef = Path(d, "swedish", "chef", "bork", "bork")
        if hasattr(self.d, "write_link"):
            self.link_to_chef_file = Path(d, "link_to_chef_file")
            self.link_to_chef_file.write_link(self.chef)
            self.link_to_images_dir = Path(d, "link_to_images_dir")
            self.link_to_images_dir.write_link(self.images)
            self.dead_link = self.d.child("dead_link")
            self.dead_link.write_link("nowhere")
        self.missing = Path(d, "MISSING")
        self.d.chdir()

    def teardown_method(self, method):
        d = self.d
        d.parent.chdir()  # Always need a valid curdir to avoid OSErrors.
        if dump:
            dump_path(d)
        if cleanup:
            d.rmtree()
            if d.exists():
                raise AssertionError("unable to delete temp dir %s" % d)
        else:
            print("Not deleting test directory", d)


class TestCalculatingPaths(FilesystemTest):
    def test_inheritance(self):
        assert Path.cwd().name   # Can we access the property?

    def test_cwd(self):
        assert str(Path.cwd()) == os.getcwd()

    def test_chdir_absolute_relative(self):
        save_dir = Path.cwd()
        self.d.chdir()
        assert Path.cwd() == self.d
        assert Path("swedish").absolute() == Path(self.d, "swedish")
        save_dir.chdir()
        assert Path.cwd() == save_dir

    def test_chef(self):
        p = Path(self.d, "swedish", "chef", "bork", "bork")
        assert p.read_file() == "bork!"

    def test_absolute(self):
        p1 = Path("images").absolute()
        p2 = self.d.child("images")
        assert p1 == p2

    def test_relative(self):
        p = self.d.child("images").relative()
        assert p == "images"

    def test_resolve(self):
        p1 = Path(self.link_to_images_dir, "image3.png")
        p2 = p1.resolve()
        assert p1.components()[-2:] == ["link_to_images_dir", "image3.png"]
        assert p2.components()[-2:] == ["images", "image3.png"]
        assert p1.exists()
        assert p2.exists()
        assert p1.same_file(p2)
        assert p2.same_file(p1)


class TestRelPathTo(FilesystemTest):
    def test1(self):
        p1 = Path("animals", "elephant")
        p2 = Path("animals", "mouse")
        assert p1.rel_path_to(p2) == Path("mouse")

    def test2(self):
        p1 = Path("animals", "elephant")
        p2 = Path("images", "image1.gif")
        assert p1.rel_path_to(p2) == Path(os.path.pardir, "images", "image1.gif")

    def test3(self):
        p1 = Path("animals", "elephant")
        assert p1.rel_path_to(self.d) == Path(os.path.pardir)

    def test4(self):
        p1 = Path("swedish", "chef")
        assert p1.rel_path_to(self.d) == Path(os.path.pardir, os.path.pardir)


class TestListingDirectories(FilesystemTest):
    def test_listdir_names_only(self):
        result = self.images.listdir(names_only=True)
        control = ["image1.gif", "image2.jpg", "image3.png"]
        assert result == control

    def test_listdir_arg_errors(self):
        with pytest.raises(TypeError):
            self.d.listdir(filter=FILES, names_only=True)

    def test_listdir(self):
        result = Path("images").listdir()
        control = [
            Path("images", "image1.gif"),
            Path("images", "image2.jpg"),
            Path("images", "image3.png")]
        assert result == control

    def test_listdir_all(self):
        result = Path("").listdir()
        control = [
            "a_file",
            "animals",
            "dead_link",
            "images",
            "link_to_chef_file",
            "link_to_images_dir",
            "swedish",
        ]
        assert result == control

    def test_listdir_files(self):
        result = Path("").listdir(filter=FILES)
        control = [
            "a_file",
            "link_to_chef_file",
        ]
        assert result == control

    def test_listdir_dirs(self):
        result = Path("").listdir(filter=DIRS)
        control = [
            "animals",
            "images",
            "link_to_images_dir",
            "swedish",
        ]
        assert result == control

    @pytest.mark.skipif("not hasattr(os, 'symlink')")
    def test_listdir_links(self):
        result = Path("").listdir(filter=LINKS)
        control = [
            "dead_link",
            "link_to_chef_file",
            "link_to_images_dir",
            ]
        assert result == control

    def test_listdir_files_no_links(self):
        result = Path("").listdir(filter=FILES_NO_LINKS)
        control = [
            "a_file",
        ]
        assert result == control

    def test_listdir_dirs_no_links(self):
        result = Path("").listdir(filter=DIRS_NO_LINKS)
        control = [
            "animals",
            "images",
            "swedish",
        ]
        assert result == control

    def test_listdir_dead_links(self):
        result = Path("").listdir(filter=DEAD_LINKS)
        control = [
            "dead_link",
        ]
        assert result == control

    def test_listdir_pattern_names_only(self):
        result = self.images.name.listdir("*.jpg", names_only=True)
        control = ["image2.jpg"]
        assert result == control

    def test_listdir_pattern(self):
        result = self.images.name.listdir("*.jpg")
        control = [Path("images", "image2.jpg")]
        assert result == control

    def test_walk(self):
        result = list(self.d.walk())
        control = [
            Path(self.a_file),
            Path(self.animals),
            Path(self.animals, "elephant"),
            Path(self.animals, "gonzo"),
            Path(self.animals, "mouse"),
        ]
        result = result[:len(control)]
        assert result == control

    def test_walk_bottom_up(self):
        result = list(self.d.walk(top_down=False))
        control = [
            Path(self.a_file),
            Path(self.animals, "elephant"),
            Path(self.animals, "gonzo"),
            Path(self.animals, "mouse"),
            Path(self.animals),
        ]
        result = result[:len(control)]
        assert result == control

    def test_walk_files(self):
        result = list(self.d.walk(filter=FILES))
        control = [
            Path(self.a_file),
            Path(self.animals, "elephant"),
            Path(self.animals, "gonzo"),
            Path(self.animals, "mouse"),
            Path(self.images, "image1.gif"),
        ]
        result = result[:len(control)]
        assert result == control

    def test_walk_dirs(self):
        result = list(self.d.walk(filter=DIRS))
        control = [
            Path(self.animals),
            Path(self.images),
            Path(self.link_to_images_dir),
            Path(self.d, "swedish"),
            ]
        result = result[:len(control)]
        assert result == control

    def test_walk_links(self):
        result = list(self.d.walk(filter=LINKS))
        control = [
            Path(self.dead_link),
            Path(self.link_to_chef_file),
            Path(self.link_to_images_dir),
            ]
        result = result[:len(control)]
        assert result == control


class TestStatAttributes(FilesystemTest):
    def test_exists(self):
        assert self.a_file.exists()
        assert self.images.exists()
        assert self.link_to_chef_file.exists()
        assert self.link_to_images_dir.exists()
        assert not self.dead_link.exists()
        assert not self.missing.exists()

    def test_lexists(self):
        assert self.a_file.lexists()
        assert self.images.lexists()
        assert self.link_to_chef_file.lexists()
        assert self.link_to_images_dir.lexists()
        assert self.dead_link.lexists()
        assert not self.missing.lexists()

    def test_isfile(self):
        assert self.a_file.isfile()
        assert not self.images.isfile()
        assert self.link_to_chef_file.isfile()
        assert not self.link_to_images_dir.isfile()
        assert not self.dead_link.isfile()
        assert not self.missing.isfile()

    def test_isdir(self):
        assert not self.a_file.isdir()
        assert self.images.isdir()
        assert not self.link_to_chef_file.isdir()
        assert self.link_to_images_dir.isdir()
        assert not self.dead_link.isdir()
        assert not self.missing.isdir()

    def test_islink(self):
        assert not self.a_file.islink()
        assert not self.images.islink()
        assert self.link_to_chef_file.islink()
        assert self.link_to_images_dir.islink()
        assert self.dead_link.islink()
        assert not self.missing.islink()

    def test_ismount(self):
        # Can't test on a real mount point because we don't know where it is
        assert not self.a_file.ismount()
        assert not self.images.ismount()
        assert not self.link_to_chef_file.ismount()
        assert not self.link_to_images_dir.ismount()
        assert not self.dead_link.ismount()
        assert not self.missing.ismount()

    def test_times(self):
        self.set_times()
        assert self.a_file.mtime() == 50000
        assert self.a_file.atime() == 60000
        # Can't set ctime to constant, so just make sure it returns a positive number.
        assert self.a_file.ctime() > 0

    def test_size(self):
        assert self.chef.size() == 5

    def test_same_file(self):
        if hasattr(self.a_file, "same_file"):
            control = Path(self.d, "a_file")
            assert self.a_file.same_file(control)
            assert not self.a_file.same_file(self.chef)

    def test_stat(self):
        st = self.chef.stat()
        assert hasattr(st, "st_mode")

    def test_statvfs(self):
        if hasattr(self.images, "statvfs"):
            stv = self.images.statvfs()
            assert hasattr(stv, "f_files")

    def test_chmod(self):
        self.a_file.chmod(0o600)
        newmode = self.a_file.stat().st_mode
        assert newmode & 0o777 == 0o600

    # Can't test chown: requires root privilege and knowledge of local users.

    def set_times(self):
        self.a_file.set_times()
        self.a_file.set_times(50000)
        self.a_file.set_times(50000, 60000)


class TestCreateRenameRemove(FilesystemTest):
    def test_mkdir_and_rmdir(self):
        self.missing.mkdir()
        assert self.missing.isdir()
        self.missing.rmdir()
        assert not self.missing.exists()

    def test_mkdir_and_rmdir_with_parents(self):
        abc = Path(self.d, "a", "b", "c")
        abc.mkdir(parents=True)
        assert abc.isdir()
        abc.rmdir(parents=True)
        assert not Path(self.d, "a").exists()

    def test_remove(self):
        self.a_file.remove()
        assert not self.a_file.exists()
        self.missing.remove()  # Removing a nonexistent file should succeed.

    if hasattr(os, 'symlink'):
        @pytest.mark.skipif("not hasattr(os, 'symlink')")
        def test_remove_broken_symlink(self):
            symlink = Path(self.d, "symlink")
            symlink.write_link("broken")
            assert symlink.lexists()
            symlink.remove()
            assert not symlink.lexists()

        @pytest.mark.skipif("not hasattr(os, 'symlink')")
        def test_rmtree_broken_symlink(self):
            symlink = Path(self.d, "symlink")
            symlink.write_link("broken")
            assert symlink.lexists()
            symlink.rmtree()
            assert not symlink.lexists()

    def test_rename(self):
        a_file = self.a_file
        b_file = Path(a_file.parent, "b_file")
        a_file.rename(b_file)
        assert not a_file.exists()
        assert b_file.exists()

    def test_rename_with_parents(self):
        pass  # @@MO: Write later.


class TestLinks(FilesystemTest):
    # @@MO: Write test_hardlink, test_symlink, test_write_link later.

    def test_read_link(self):
        assert self.dead_link.read_link() == "nowhere"

class TestHighLevel(FilesystemTest):
    def test_copy(self):
        a_file = self.a_file
        b_file = Path(a_file.parent, "b_file")
        a_file.copy(b_file)
        assert b_file.exists()
        a_file.copy_stat(b_file)

    def test_copy_tree(self):
        return  # .copy_tree() not implemented.
        images = self.images
        images2 = Path(self.images.parent, "images2")
        images.copy_tree(images2)

    def test_move(self):
        a_file = self.a_file
        b_file = Path(a_file.parent, "b_file")
        a_file.move(b_file)
        assert not a_file.exists()
        assert b_file.exists()

    def test_needs_update(self):
        control_files = self.images.listdir()
        self.a_file.set_times()
        assert not self.a_file.needs_update(control_files)
        time.sleep(1)
        control = Path(self.images, "image2.jpg")
        control.set_times()
        result = self.a_file.needs_update(self.images.listdir())
        assert self.a_file.needs_update(control_files)

    def test_read_file(self):
        assert self.chef.read_file() == "bork!"

    # .write_file and .rmtree tested in .setUp.



        

########NEW FILE########
__FILENAME__ = abstractpath
"""unipath.py - A two-class approach to file/directory operations in Python.
"""

import os

from unipath.errors import UnsafePathError

__all__ = ["AbstractPath"]

# Use unicode strings if possible
_base = os.path.supports_unicode_filenames and unicode or str

class AbstractPath(_base):
    """An object-oriented approach to os.path functions."""
    pathlib = os.path
    auto_norm = False

    #### Special Python methods.
    def __new__(class_, *args, **kw):
        norm = kw.pop("norm", None)
        if norm is None:
            norm = class_.auto_norm
        if kw:
            kw_str = ", ".join(kw.iterkeys())
            raise TypeError("unrecognized keyword args: %s" % kw_str)
        newpath = class_._new_helper(args)
        if isinstance(newpath, class_):
            return newpath
        if norm:
            newpath = class_.pathlib.normpath(newpath)
            # Can't call .norm() because the path isn't instantiated yet.
        return _base.__new__(class_, newpath)

    def __add__(self, more):
        try:
            resultStr = _base.__add__(self, more)
        except TypeError:  #Python bug
            resultStr = NotImplemented
        if resultStr is NotImplemented:
            return resultStr
        return self.__class__(resultStr)
 
    @classmethod
    def _new_helper(class_, args):
        pathlib = class_.pathlib
        # If no args, return "." or platform equivalent.
        if not args:
            return pathlib.curdir
        # Avoid making duplicate instances of the same immutable path
        if len(args) == 1 and isinstance(args[0], class_) and \
            args[0].pathlib == pathlib:
            return args[0]
        try:
            legal_arg_types = (class_, basestring, list, int, long)
        except NameError: # Python 3 doesn't have basestring nor long
            legal_arg_types = (class_, str, list, int)
        args = list(args)
        for i, arg in enumerate(args):
            if not isinstance(arg, legal_arg_types):
                m = "arguments must be str, unicode, list, int, long, or %s"
                raise TypeError(m % class_.__name__)
            try:
                int_types = (int, long)
            except NameError: # We are in Python 3
                int_types = int
            if isinstance(arg, int_types):
                args[i] = str(arg)
            elif isinstance(arg, class_) and arg.pathlib != pathlib:
                arg = getattr(arg, components)()   # Now a list.
                if arg[0]:
                    reason = ("must use a relative path when converting "
                              "from '%s' platform to '%s': %s")
                    tup = arg.pathlib.__name__, pathlib.__name__, arg
                    raise ValueError(reason % tup)
                # Fall through to convert list of components.
            if isinstance(arg, list):
                args[i] = pathlib.join(*arg)
        return pathlib.join(*args)
        
    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, _base(self))

    def norm(self):
        return self.__class__(self.pathlib.normpath(self))

    def expand_user(self):
        return self.__class__(self.pathlib.expanduser(self))
    
    def expand_vars(self):
        return self.__class__(self.pathlib.expandvars(self))
    
    def expand(self):
        """ Clean up a filename by calling expandvars(),
        expanduser(), and norm() on it.

        This is commonly everything needed to clean up a filename
        read from a configuration file, for example.
        """
        newpath = self.pathlib.expanduser(self)
        newpath = self.pathlib.expandvars(newpath)
        newpath = self.pathlib.normpath(newpath)
        return self.__class__(newpath)

    #### Properies: parts of the path.

    @property
    def parent(self):
        """The path without the final component; akin to os.path.dirname().
           Example: Path('/usr/lib/libpython.so').parent => Path('/usr/lib')
        """
        return self.__class__(self.pathlib.dirname(self))
    
    @property
    def name(self):
        """The final component of the path.
           Example: path('/usr/lib/libpython.so').name => Path('libpython.so')
        """
        return self.__class__(self.pathlib.basename(self))
    
    @property
    def stem(self):
        """Same as path.name but with one file extension stripped off.
           Example: path('/home/guido/python.tar.gz').stem => Path('python.tar')
        """
        return self.__class__(self.pathlib.splitext(self.name)[0])
    
    @property
    def ext(self):
        """The file extension, for example '.py'."""
        return self.__class__(self.pathlib.splitext(self)[1])

    #### Methods to extract and add parts to the path.

    def split_root(self):
        """Split a path into root and remainder.  The root is always "/" for
           posixpath, or a backslash-root, drive-root, or UNC-root for ntpath.
           If the path begins with none of these, the root is returned as ""
           and the remainder is the entire path.
        """
        P = self.__class__
        if hasattr(self.pathlib, "splitunc"):
            root, rest = self.pathlib.splitunc(self)
            if root:
                if rest.startswith(self.pathlib.sep):
                    root += self.pathlib.sep
                    rest = rest[len(self.pathlib.sep):]
                return P(root), P(rest)
                # @@MO: Should test altsep too.
        root, rest = self.pathlib.splitdrive(self)
        if root:
            if rest.startswith(self.pathlib.sep):
                root += self.pathlib.sep
                rest = rest[len(self.pathlib.sep):]
            return P(root), P(rest)
            # @@MO: Should test altsep too.
        if self.startswith(self.pathlib.sep):
            return P(self.pathlib.sep), P(rest[len(self.pathlib.sep):])
        if self.pathlib.altsep and self.startswith(self.pathlib.altsep):
            return P(self.pathlib.altsep), P(rest[len(self.pathlib.altsep):])
        return P(""), self

    def components(self):
        # @@MO: Had to prevent "" components from being appended.  I don't
        # understand why Lindqvist didn't have this problem.
        # Also, doesn't this fail to get the beginning components if there's
        # a "." or ".." in the middle of the path?
        root, loc = self.split_root()
        components = []
        while loc != self.pathlib.curdir and loc != self.pathlib.pardir:
            prev = loc
            loc, child = self.pathlib.split(prev)
            #print "prev=%r, loc=%r, child=%r" % (prev, loc, child)
            if loc == prev:
                break
            if child != "":
                components.append(child)
            if loc == "":
                break
        if loc != "":
            components.append(loc)
        components.reverse()
        components.insert(0, root)
        return [self.__class__(x) for x in components]

    def ancestor(self, n):
        p = self
        for i in range(n):
            p = p.parent
        return p

    def child(self, *children):
        # @@MO: Compare against Glyph's method.
        for child in children:
            if self.pathlib.sep in child:
                msg = "arg '%s' contains path separator '%s'"
                tup = child, self.pathlib.sep
                raise UnsafePathError(msg % tup)
            if self.pathlib.altsep and self.pathlib.altsep in child:
                msg = "arg '%s' contains alternate path separator '%s'"
                tup = child, self.pathlib.altsep
                raise UnsafePathError(msg % tup)
            if child == self.pathlib.pardir:
                msg = "arg '%s' is parent directory specifier '%s'"
                tup = child, self.pathlib.pardir
                raise UnsafePathError(msg % tup)
            if child == self.pathlib.curdir:    
                msg = "arg '%s' is current directory specifier '%s'"
                tup = child, self.pathlib.curdir
                raise UnsafePathError(msg % tup)
        newpath = self.pathlib.join(self, *children)
        return self.__class__(newpath)

    def norm_case(self):
        return self.__class__(self.pathlib.normcase(self))
    
    def isabsolute(self):
        """True if the path is absolute.
           Note that we consider a Windows drive-relative path ("C:foo") 
           absolute even though ntpath.isabs() considers it relative.
        """
        return bool(self.split_root()[0])

########NEW FILE########
__FILENAME__ = errors
class UnsafePathError(ValueError):
    pass

class RecursionError(OSError):
    pass

class DebugWarning(UserWarning):
    pass

########NEW FILE########
__FILENAME__ = path
"""unipath.py - A two-class approach to file/directory operations in Python.

Full usage, documentation, changelog, and history are at
http://sluggo.scrapping.cc/python/unipath/

(c) 2007 by Mike Orr (and others listed in "History" section of doc page).
Permission is granted to redistribute, modify, and include in commercial and
noncommercial products under the terms of the Python license (i.e., the "Python
Software Foundation License version 2" at 
http://www.python.org/download/releases/2.5/license/).
"""

import errno
import fnmatch
import glob
import os
import shutil
import stat
import sys
import time
import warnings

from unipath.abstractpath import AbstractPath
from unipath.errors import RecursionError

__all__ = ["Path"]

#warnings.simplefilter("ignore", DebugWarning, append=1)

def flatten(iterable):
    """Yield each element of 'iterable', recursively interpolating 
       lists and tuples.  Examples:
       [1, [2, 3], 4]  =>  iter([1, 2, 3, 4])
       [1, (2, 3, [4]), 5) => iter([1, 2, 3, 4, 5])
    """
    for elm in iterable:
        if isinstance(elm, (list, tuple)):
            for relm in flatten(elm):
                yield relm
        else:
            yield elm

class Path(AbstractPath):

    ##### CURRENT DIRECTORY ####
    @classmethod
    def cwd(class_):
        """ Return the current working directory as a path object. """
        return class_(os.getcwd())

    def chdir(self):
        os.chdir(self)

    #### CALCULATING PATHS ####
    def absolute(self):
        """Return the absolute Path, prefixing the current directory if
           necessary.
        """
        return self.__class__(os.path.abspath(self))

    def relative(self):
        """Return a relative path to self from the current working directory.
        """
        return self.__class__.cwd().rel_path_to(self)

    def rel_path_to(self, dst):
        """ Return a relative path from self to dst.

        This prefixes as many pardirs (``..``) as necessary to reach a common
        ancestor.  If there's no common ancestor (e.g., they're are on 
        different Windows drives), the path will be absolute.
        """
        origin = self.__class__(self).absolute()
        if not origin.isdir():
            origin = origin.parent
        dest = self.__class__(dst).absolute()

        orig_list = origin.norm_case().components()
        # Don't normcase dest!  We want to preserve the case.
        dest_list = dest.components()

        if orig_list[0] != os.path.normcase(dest_list[0]):
            # Can't get here from there.
            return self.__class__(dest)

        # Find the location where the two paths start to differ.
        i = 0
        for start_seg, dest_seg in zip(orig_list, dest_list):
            if start_seg != os.path.normcase(dest_seg):
                break
            i += 1

        # Now i is the point where the two paths diverge.
        # Need a certain number of "os.pardir"s to work up
        # from the origin to the point of divergence.
        segments = [os.pardir] * (len(orig_list) - i)
        # Need to add the diverging part of dest_list.
        segments += dest_list[i:]
        if len(segments) == 0:
            # If they happen to be identical, use os.curdir.
            return self.__class__(os.curdir)
        else:
            newpath = os.path.join(*segments)
            return self.__class__(newpath)
    
    def resolve(self):
        """Return an equivalent Path that does not contain symbolic links."""
        return self.__class__(os.path.realpath(self))
    

    #### LISTING DIRECTORIES ####
    def listdir(self, pattern=None, filter=None, names_only=False):
        if names_only and filter is not None:
            raise TypeError("filter not allowed if 'names_only' is true")
        empty_path = self == ""
        if empty_path:
            names = os.listdir(os.path.curdir)
        else:
            names = os.listdir(self)
        if pattern is not None:
            names = fnmatch.filter(names, pattern)
        names.sort()
        if names_only:
            return names
        ret = [self.child(x) for x in names]
        if filter is not None:
            ret = [x for x in ret if filter(x)]
        return ret

    def walk(self, pattern=None, filter=None, top_down=True):
        return self._walk(pattern, filter, top_down, set())

    def _walk(self, pattern, filter, top_down, seen):
        if not self.isdir():
            raise RecursionError("not a directory: %s" % self)
        real_dir = self.resolve()
        if real_dir in seen:
            return  # We've already recursed this directory.
        seen.add(real_dir)
        for child in self.listdir(pattern):
            is_dir = child.isdir()
            if is_dir and not top_down:
                for grandkid in child._walk(pattern, filter, top_down, seen):
                    yield grandkid
            if filter is None or filter(child):
                yield child
            if is_dir and top_down:
                for grandkid in child._walk(pattern, filter, top_down, seen):
                    yield grandkid
                

    #### STAT ATTRIBUTES ####
    exists = os.path.exists
    lexists = os.path.lexists

    isfile = os.path.isfile
    isdir = os.path.isdir
    islink = os.path.islink
    ismount = os.path.ismount

    atime = os.path.getatime
    ctime = os.path.getctime
    mtime = os.path.getmtime

    size = os.path.getsize

    if hasattr(os.path, 'samefile'):
        same_file = os.path.samefile

    # For some reason these functions have to be wrapped in methods.
    def stat(self):
        return os.stat(self)

    def lstat(self):
        return os.lstat(self)

    if hasattr(os, 'statvfs'):
        def statvfs(self):
            return os.statvfs(self)

    def chmod(self, mode):
        os.chmod(self, mode)

    if hasattr(os, 'chown'):
        def chown(self, uid, gid):
            os.chown(self, uid, gid)

    def set_times(self, mtime=None, atime=None):
        """Set a path's modification and access times.
           Times must be in ticks as returned by ``time.time()``.
           If 'mtime' is None, use the current time.
           If 'atime' is None, use 'mtime'.
           Creates an empty file if the path does not exists.
           On some platforms (Windows), the path must not be a directory.
        """
        if not self.exists():
            fd = os.open(self, os.O_WRONLY | os.O_CREAT, 0o666)
            os.close(fd)
        if mtime is None:
            mtime = time.time()
        if atime is None:
            atime = mtime
        times = atime, mtime
        os.utime(self, times)


    #### CREATING, REMOVING, AND RENAMING ####
    def mkdir(self, parents=False, mode=0o777):
        if self.exists():
            return
        if parents:
            os.makedirs(self, mode)
        else:
            os.mkdir(self, mode)

    def rmdir(self, parents=False):
        if not self.exists():
            return
        if parents:
            os.removedirs(self)
        else:
            os.rmdir(self)

    def remove(self):
        if self.lexists():
            os.remove(self)

    def rename(self, new, parents=False):
        if parents:
            os.renames(self, new)
        else:
            os.rename(self, new)

    #### SYMBOLIC AND HARD LINKS ####
    if hasattr(os, 'link'):
        def hardlink(self, newpath):
            """Create a hard link at 'newpath' pointing to self. """
            os.link(self, newpath)

    if hasattr(os, 'symlink'):
        def write_link(self, link_content):
            """Create a symbolic link at self pointing to 'link_content'.
               This is the same as .symlink but with the args reversed.
            """
            os.symlink(link_content, self)

        def make_relative_link_to(self, dest):
            """Make a relative symbolic link from self to dest.
            
            Same as self.write_link(self.rel_path_to(dest))
            """
            link_content = self.rel_path_to(dest)
            self.write_link(link_content)


    if hasattr(os, 'readlink'):
        def read_link(self, absolute=False):
            p = self.__class__(os.readlink(self))
            if absolute and not p.isabsolute():
                p = self.__class__(self.parent, p)
            return p

    #### HIGH-LEVEL OPERATIONS ####
    def copy(self, dst, times=False, perms=False):
        """Copy the file, optionally copying the permission bits (mode) and
           last access/modify time. If the destination file exists, it will be
           replaced. Raises OSError if the destination is a directory. If the
           platform does not have the ability to set the permission or times,
           ignore it.
           This is shutil.copyfile plus bits of shutil.copymode and
           shutil.copystat's implementation.
           shutil.copy and shutil.copy2 are not supported but are easy to do.
        """
        shutil.copyfile(self, dst)
        if times or perms:
            self.copy_stat(dst, times, perms)

    def copy_stat(self, dst, times=True, perms=True):
        st = os.stat(self)
        if hasattr(os, 'utime'):
            os.utime(dst, (st.st_atime, st.st_mtime))
        if hasattr(os, 'chmod'):
            m = stat.S_IMODE(st.st_mode)
            os.chmod(dst, m)

    # Undocumented, not implemented method.
    def copy_tree(dst, perserve_symlinks=False, times=False, perms=False):
        raise NotImplementedError()
        
    if hasattr(shutil, 'move'):
        move = shutil.move
        
    def needs_update(self, others):
        if not self.exists():
            return True
        control = self.mtime()
        for p in flatten(others):
            if p.isdir():
                for child in p.walk(filter=FILES):
                    if child.mtime() > control:
                        return True
            elif p.mtime() > control:
                return True
        return False
                
    def read_file(self, mode="rU"):
        f = open(self, mode)
        content = f.read()
        f.close()
        return content

    def rmtree(self, parents=False):
        """Delete self recursively, whether it's a file or directory.
           directory, remove it recursively (same as shutil.rmtree). If it
           doesn't exist, do nothing.
           If you're looking for a 'rmtree' method, this is what you want.
        """
        if self.isfile() or self.islink():
           os.remove(self)
        elif self.isdir():
           shutil.rmtree(self)
        if not parents:
            return
        p = self.parent
        while p:
            try:
                 os.rmdir(p)
            except os.error:
                break
            p = p.parent

    def write_file(self, content, mode="w"):
        f = open(self, mode)
        f.write(content)
        f.close()


########NEW FILE########
__FILENAME__ = tools
"""Convenience functions.
"""

from __future__ import print_function, generators
import sys

from unipath import AbstractPath, Path

def dict2dir(dir, dic, mode="w"):
    dir = Path(dir)
    if not dir.exists():
        dir.mkdir()
    for filename, content in dic.items():
        p = Path(dir, filename)
        if isinstance(content, dict):
            dict2dir(p, content)
            continue
        f = open(p, mode)
        f.write(content)
        f.close()

def dump_path(path, prefix="", tab="    ", file=None):
    if file is None:
        file = sys.stdout
    p = AbstractPath(path)
    if   p.islink():
        print("%s%s -> %s" % (prefix, p.name, p.read_link()), file=file)
    elif p.isdir():
        print("%s%s:" % (prefix, p.name), file=file)
        for p2 in p.listdir():
            dump_path(p2, prefix+tab, tab, file)
    else:
        print("%s%s  (%d)" % (prefix, p.name, p.size()), file=file)

########NEW FILE########
