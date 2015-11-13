__FILENAME__ = build
#!/usr/bin/env python
import os

source_dir = 'src'
output_dir = 'ftplugin'


def build():
    py_src = file(os.path.join(source_dir, 'python_unittests.py')).read()
    vim_src = file(os.path.join(source_dir, 'base.vim')).read()
    combined_src = vim_src.replace('__PYTHON_SOURCE__', py_src)
    if not os.path.exists(output_dir):
        os.mkdir(output_dir)
    output_path = os.path.join(output_dir, 'python_pyunit.vim')
    file(output_path, 'w').write(combined_src)

if __name__ == '__main__':
    build()

########NEW FILE########
__FILENAME__ = python_unittests
import vim
import os
import os.path
from vim_bridge import bridged


#
# General helper functions
#

def _relpath(path, start='.', try_stdlib=True):
    """Returns the relative version of the path.  This is a backport of
    Python's stdlib routine os.path.relpath(), which is not yet available in
    Python 2.4.

    """
    # Fall back onto stdlib version of it, if available
    if try_stdlib:
        try:
            return os.path.relpath(path, start)
        except AttributeError:
            # Python versions below 2.6 don't have the relpath function
            # It's ok, we fall back onto our own implementation
            pass

    fullp = os.path.abspath(path)
    fulls = os.path.abspath(start)
    matchs = os.path.normpath(start)
    if not matchs.endswith(os.sep):
        matchs += os.sep

    if fullp == fulls:
        return '.'
    elif fullp.startswith(matchs):
        return fullp[len(matchs):]
    else:
        # Strip dirs off of fulls until it is a prefix of fullp
        path_prefixes = []
        while True:
            path_prefixes.append(os.path.pardir)
            fulls = os.path.dirname(fulls)
            if fullp.startswith(fulls):
                break
        remainder = fullp[len(fulls):]
        if remainder.startswith(os.sep):
            remainder = remainder[len(os.sep):]
        path_prefix = os.sep.join(path_prefixes)
        return os.path.join(path_prefix, remainder)


def strip_prefix(s, prefix):
    if prefix != "" and s.startswith(prefix):
        return s[len(prefix):]
    else:
        return s


def is_home_dir(path):
    return os.path.realpath(path) == os.path.expandvars("$HOME")


def is_fs_root(path):
    return os.path.realpath(path) == "/" or \
           (int(vim.eval("g:ProjRootStopAtHomeDir")) and is_home_dir(path))


def find_project_root(path='.'):
    if not os.path.isdir(path):
        return find_project_root(os.path.dirname(os.path.realpath(path)))

    indicators = vim.eval("g:ProjRootIndicators")
    while not is_fs_root(path):
        for i in indicators:
            if os.path.exists(os.path.join(path, i)):
                return os.path.realpath(path)
        path = os.path.join(path, os.path.pardir)
    raise Exception("Could not find project root")


#
# Classes that implement TestLayouts
#

class BaseTestLayout(object):
    def __init__(self):
        self.source_root = vim.eval('g:PyUnitSourceRoot')
        self.test_root = vim.eval('g:PyUnitTestsRoot')
        self.prefix = vim.eval('g:PyUnitTestPrefix')


    # Helper methods, to be used in subclasses
    def break_down(self, path):
        parts = path.split(os.sep)
        if len(parts) > 0:
            if parts[-1] == '__init__.py':
                del parts[-1]
            elif parts[-1].endswith(".py"):
                parts[-1] = parts[-1][:-len(".py")]
        return parts

    def glue_parts(self, parts, use_under_under_init=False):
        if use_under_under_init:
            parts = parts + ['__init__.py']
        else:
            parts = parts[:-1] + [parts[-1] + '.py']
        return os.sep.join(parts)

    def relatize(self, path):
        return _relpath(path, find_project_root())

    def absolutify(self, path):
        if os.path.isabs(path):
            return path
        return os.sep.join([find_project_root(), path])


    # The actual BaseTestLayout methods that need implementation
    def is_test_file(self, some_file):
        raise NotImplemented("Implement this method in a subclass.")

    def get_test_file(self, source_file):
        raise NotImplemented("Implement this method in a subclass.")

    def get_source_candidates(self, test_file):
        raise NotImplemented("Implement this method in a subclass.")

    def get_source_file(self, test_file):
        for candidate in self.get_source_candidates(test_file):
            if os.path.exists(candidate):
                return candidate
        raise RuntimeError("Source file not found.")


class SideBySideLayout(BaseTestLayout):
    def is_test_file(self, some_file):
        some_file = self.relatize(some_file)
        parts = self.break_down(some_file)
        filepart = parts[-1]
        return filepart.startswith(self.prefix)

    def get_test_file(self, source_file):
        source_file = self.relatize(source_file)
        parts = self.break_down(source_file)
        parts[-1] = self.prefix + parts[-1]
        return self.glue_parts(parts)

    def get_source_candidates(self, test_file):
        test_file = self.relatize(test_file)
        parts = self.break_down(test_file)
        filepart = parts[-1]
        if not filepart.startswith(self.prefix):
            raise RuntimeError("Not a test file.")
        parts[-1] = filepart[len(self.prefix):]
        return [self.glue_parts(parts)]


class FlatLayout(BaseTestLayout):
    def is_test_file(self, some_file):
        some_file = self.relatize(some_file)
        if not some_file.startswith(self.test_root):
            return False

        some_file = _relpath(some_file, self.test_root)

        parts = self.break_down(some_file)
        if len(parts) != 1:
            return False
        return parts[0].startswith(self.prefix)

    def get_test_file(self, source_file):
        source_file = self.relatize(source_file)
        if not source_file.startswith(self.source_root):
            raise RuntimeError("File %s is not under the source root." % source_file)

        source_file = _relpath(source_file, self.source_root)
        parts = self.break_down(source_file)
        flat_file_name = "_".join(parts)
        parts = [self.test_root] + [self.prefix + flat_file_name]
        return self.glue_parts(parts)

    def get_source_candidates(self, test_file):
        test_file = self.relatize(test_file)
        if not test_file.startswith(self.test_root):
            raise RuntimeError("File %s is not under the test root." % test_file)

        test_file = _relpath(test_file, self.test_root)
        parts = self.break_down(test_file)
        if len(parts) != 1:
            raise RuntimeError("Flat tests layout does not allow tests to be more than one directory deep.")
        file_name = strip_prefix(parts[0], self.prefix)
        parts = file_name.split("_")
        parts = [self.source_root] + parts
        return [self.glue_parts(parts, x) for x in (False, True)]


class FollowHierarchyLayout(BaseTestLayout):
    def is_test_file(self, some_file):
        some_file = self.relatize(some_file)
        if not some_file.startswith(self.test_root):
            return False

        some_file = _relpath(some_file, self.test_root)

        parts = self.break_down(some_file)
        for p in parts:
            if not p.startswith(self.prefix):
                return False
        return True

    def get_test_file(self, source_file):
        source_file = self.relatize(source_file)
        if not source_file.startswith(self.source_root):
            raise RuntimeError("File %s is not under the source root." % source_file)

        source_file = _relpath(source_file, self.source_root)
        parts = self.break_down(source_file)
        parts = map(lambda p: self.prefix + p, parts)
        parts = [self.test_root] + parts
        return self.glue_parts(parts)

    def get_source_candidates(self, test_file):
        test_file = self.relatize(test_file)
        if not test_file.startswith(self.test_root):
            raise RuntimeError("File %s is not under the test root." % test_file)

        test_file = _relpath(test_file, self.test_root)
        parts = self.break_down(test_file)
        parts = [strip_prefix(p, self.prefix) for p in parts]
        if self.source_root:
            parts = [self.source_root] + parts
        result = [self.glue_parts(parts, x) for x in (False, True)]
        return result


class NoseLayout(BaseTestLayout):
    def is_test_file(self, some_file):
        some_file = self.relatize(some_file)
        if not some_file.startswith(self.test_root):
            return False

        some_file = _relpath(some_file, self.test_root)

        parts = self.break_down(some_file)
        return parts[-1].startswith(self.prefix)

    def get_test_file(self, source_file):
        source_file = self.relatize(source_file)
        if not source_file.startswith(self.source_root):
            raise RuntimeError("File %s is not under the source root." % source_file)

        source_file = _relpath(source_file, self.source_root)
        parts = self.break_down(source_file)
        parts[-1] = self.prefix + parts[-1]
        parts = [self.test_root] + parts
        return self.glue_parts(parts)

    def get_source_candidates(self, test_file):
        test_file = self.relatize(test_file)
        if not test_file.startswith(self.test_root):
            raise RuntimeError("File %s is not under the test root." % test_file)

        test_file = _relpath(test_file, self.test_root)
        parts = self.break_down(test_file)
        parts = [strip_prefix(p, self.prefix) for p in parts]
        if self.source_root:
            parts = [self.source_root] + parts
        result = [self.glue_parts(parts, x) for x in (False, True)]
        return result


def get_implementing_class():
    implementations = {
        'flat': FlatLayout,
        'follow-hierarchy': FollowHierarchyLayout,
        'side-by-side': SideBySideLayout,
        'nose': NoseLayout,
    }
    test_layout = vim.eval('g:PyUnitTestsStructure')
    try:
        return implementations[test_layout]
    except KeyError:
        raise RuntimeError('No such test layout: %s' % test_layout)


#
# The main functions
#

def get_test_file_for_source_file(path):
    impl = get_implementing_class()()
    return impl.get_test_file(path)


def find_source_file_for_test_file(path):
    impl = get_implementing_class()()
    for f in impl.get_source_candidates(path):
        if os.path.exists(f):
            return f
    raise Exception("Source file not found.")


def is_test_file(path):
    impl = get_implementing_class()()
    return impl.is_test_file(path)


def _vim_split_cmd(inverted=False):
    invert = {'top': 'bottom', 'left': 'right',
              'right': 'left', 'bottom': 'top', 'no': 'no'}
    mapping = {'top': 'lefta', 'left': 'vert lefta',
               'right': 'vert rightb', 'bottom': 'rightb', 'no': ''}
    splitoff_direction = vim.eval("g:PyUnitTestsSplitWindow")
    if inverted:
        return mapping[invert[splitoff_direction]]
    else:
        return mapping[splitoff_direction]


def _open_buffer_cmd(path, opposite=False):
    splitopts = _vim_split_cmd(opposite)
    if not splitopts:
        splitcmd = 'edit'
    elif int(vim.eval('bufexists("%s")' % path)):
        splitcmd = splitopts + ' sbuffer'
    else:
        splitcmd = splitopts + ' split'
    command = "%s %s" % (splitcmd, path)
    return command


def lcd_to_project_root(path):
    vim.command("lcd %s" % find_project_root(path))


def switch_to_test_file_for_source_file(path):
    testfile = get_test_file_for_source_file(path)
    testdir = os.path.dirname(testfile)
    if not os.path.isfile(testfile):
        if int(vim.eval('g:PyUnitConfirmTestCreation')):
            # Ask the user for confirmation
            rel_testfile = _relpath(testfile, find_project_root(path))
            msg = 'confirm("Test file does not exist yet. Create %s now?", "&Yes\n&No")' % rel_testfile
            if int(vim.eval(msg)) != 1:
                return

        # Create the directory up until the file (if it doesn't exist yet)
        if not os.path.exists(testdir):
            os.makedirs(testdir)

    vim.command(_open_buffer_cmd(testfile))
    lcd_to_project_root(path)


def switch_to_source_file_for_test_file(path):
    sourcefile = find_source_file_for_test_file(path)
    vim.command(_open_buffer_cmd(sourcefile, opposite=True))
    lcd_to_project_root(path)


@bridged
def PyUnitSwitchToCounterpartOfFile(path):
    if is_test_file(path):
        switch_to_source_file_for_test_file(path)
    else:
        switch_to_test_file_for_source_file(path)


@bridged
def PyUnitRunTestsForFile(path):
    if not is_test_file(path):
        path = get_test_file_for_source_file(path)
    relpath = _relpath(path, '.')
    vim.command('call PyUnitRunTestsForTestFile("%s")' % relpath)

########NEW FILE########
__FILENAME__ = vim
from mock import Mock

eval = Mock()
command = Mock()

########NEW FILE########
__FILENAME__ = test_python_unittests
# Mock out the vim library
import sys
sys.path = ['tests/mocks'] + sys.path
import vim

vimvar = {}


def fake_eval(x):
    global vimvar
    return vimvar[x]

vim.eval = fake_eval
vimvar['foo'] = 'bar'

# Now start loading normally
import unittest
import os
import python_unittests as mod


# Calculate the *real* project root for this test scenario
# I should probably mock this out, but for the current state of affairs, this is
# too much overkill
proj_root = os.getcwd()
currfile = __file__.replace('.pyc', '.py')


def setUpVimEnvironment():
    vimvar.clear()
    vimvar.update({
        'g:PyUnitShowTests': '1',
        'g:PyUnitCmd': 'nosetests -q --with-machineout',
        'g:PyUnitTestPrefix': 'test_',
        'g:ProjRootIndicators': ['.git', 'setup.py', 'setup.cfg'],
        'g:ProjRootStopAtHomeDir': '1',
        'g:PyUnitTestsStructure': 'follow-hierarchy',
        'g:PyUnitTestsRoot': 'tests',
        'g:PyUnitSourceRoot': '',
        'g:PyUnitTestsSplitWindow': 'right',
    })

class FileAwareTestCase(unittest.TestCase):
    def assertSameFile(self, x, y):
        self.assertEquals(os.path.realpath(x), os.path.realpath(y))


class TestTestLayout(FileAwareTestCase):
    def testBreakDownSimple(self):
        layout = mod.BaseTestLayout()
        self.assertEquals(layout.break_down('foo.py'), ['foo'])
        self.assertEquals(layout.break_down('foo/bar.py'), ['foo', 'bar'])
        self.assertEquals(layout.break_down('foo/bar/baz.py'), ['foo', 'bar', 'baz'])

    def testBreakDownWithUnderUnderInits(self):
        layout = mod.BaseTestLayout()
        self.assertEquals(layout.break_down('__init__.py'), [])
        self.assertEquals(layout.break_down('foo/__init__.py'), ['foo'])
        self.assertEquals(layout.break_down('foo/bar/baz/__init__.py'), ['foo', 'bar', 'baz'])

    def testGlueSimple(self):
        layout = mod.BaseTestLayout()
        self.assertEquals(layout.glue_parts(['foo']), 'foo.py')
        self.assertEquals(layout.glue_parts(['foo', 'bar', 'baz']), 'foo/bar/baz.py')
        self.assertRaises(IndexError, layout.glue_parts, [])

    def testGlueWithUnderUnderInits(self):
        layout = mod.BaseTestLayout()
        self.assertEquals(layout.glue_parts(['foo'], True), 'foo/__init__.py')
        self.assertEquals(layout.glue_parts(['foo', 'bar', 'baz'], True), 'foo/bar/baz/__init__.py')
        self.assertEquals(layout.glue_parts([], True), '__init__.py')

    def testRelatize(self):
        layout = mod.BaseTestLayout()
        self.assertEquals(layout.relatize("%s/foo/bar.py" % proj_root), "foo/bar.py")
        self.assertEquals(layout.relatize("foo/bar.py"), "foo/bar.py")

    def testAbsolutify(self):
        layout = mod.BaseTestLayout()
        self.assertEquals(layout.absolutify("foo/bar.py"), "%s/foo/bar.py" % proj_root)
        self.assertEquals(layout.absolutify("/tmp/foo/bar.py"), "/tmp/foo/bar.py")


class TestSideBySideLayout(FileAwareTestCase):
    def setUp(self):
        setUpVimEnvironment()

    def testDetectTestFile(self):
        vimvar['g:PyUnitSourceRoot'] = 'src'
        layout = mod.SideBySideLayout()
        self.assertTrue(layout.is_test_file('test_foo.py'))
        self.assertTrue(layout.is_test_file('foo/test_bar.py'))
        self.assertTrue(layout.is_test_file('tests/foo/test_bar.py'))
        self.assertTrue(layout.is_test_file('test_foo/test_bar.py'))
        self.assertFalse(layout.is_test_file('foo.py'))
        self.assertFalse(layout.is_test_file('src/foo.py'))
        self.assertFalse(layout.is_test_file('src/foo/bar.py'))

    def testDetectTestFileWithAlternatePrefix(self):
        vimvar['g:PyUnitTestPrefix'] = '_'
        vimvar['g:PyUnitSourceRoot'] = 'src'
        layout = mod.SideBySideLayout()
        self.assertTrue(layout.is_test_file('_foo.py'))
        self.assertTrue(layout.is_test_file('foo/_bar.py'))
        self.assertTrue(layout.is_test_file('tests/foo/_bar.py'))
        self.assertTrue(layout.is_test_file('test_foo/_bar.py'))
        self.assertFalse(layout.is_test_file('foo.py'))
        self.assertFalse(layout.is_test_file('src/foo.py'))
        self.assertFalse(layout.is_test_file('src/foo/bar.py'))

    def testDetectAbsoluteTestFile(self):
        vimvar['g:PyUnitTestPrefix'] = '_'
        vimvar['g:PyUnitSourceRoot'] = 'src'
        absdir = os.path.realpath(proj_root)
        layout = mod.SideBySideLayout()
        self.assertTrue(layout.is_test_file('%s/_foo.py' % absdir))
        self.assertTrue(layout.is_test_file('%s/foo/_bar.py' % absdir))
        self.assertTrue(layout.is_test_file('%s/tests/foo/_bar.py' % absdir))
        self.assertTrue(layout.is_test_file('%s/test_foo/_bar.py' % absdir))
        self.assertFalse(layout.is_test_file('%s/foo.py' % absdir))
        self.assertFalse(layout.is_test_file('%s/src/foo.py' % absdir))
        self.assertFalse(layout.is_test_file('%s/src/foo/bar.py' % absdir))

    def testSourceToTest(self):
        vimvar['g:PyUnitSourceRoot'] = 'src'
        layout = mod.SideBySideLayout()
        self.assertEquals(layout.get_test_file('src/foo.py'), 'src/test_foo.py')
        self.assertEquals(layout.get_test_file('src/bar.py'), 'src/test_bar.py')
        self.assertEquals(layout.get_test_file('src/bar/baz.py'), 'src/bar/test_baz.py')
        self.assertEquals(layout.get_test_file('foo.py'), 'test_foo.py')

    def testSourceToTestWithAlternatePrefix(self):
        vimvar['g:PyUnitTestPrefix'] = '_'
        vimvar['g:PyUnitSourceRoot'] = 'src'
        layout = mod.SideBySideLayout()
        self.assertEquals(layout.get_test_file('src/foo.py'), 'src/_foo.py')
        self.assertEquals(layout.get_test_file('src/bar.py'), 'src/_bar.py')
        self.assertEquals(layout.get_test_file('src/bar/baz.py'), 'src/bar/_baz.py')
        self.assertEquals(layout.get_test_file('foo.py'), '_foo.py')

    def testTestToSource(self):
        vimvar['g:PyUnitSourceRoot'] = 'src'
        layout = mod.SideBySideLayout()
        self.assertEquals(layout.get_source_candidates('src/test_foo.py'), ['src/foo.py'])
        self.assertEquals(layout.get_source_candidates('src/test_bar.py'), ['src/bar.py'])
        self.assertEquals(layout.get_source_candidates('src/bar/test_baz.py'), ['src/bar/baz.py'])
        self.assertEquals(layout.get_source_candidates('test_foo.py'), ['foo.py'])

    def testTestToSourceWithAlternatePrefix(self):
        vimvar['g:PyUnitTestPrefix'] = '_'
        vimvar['g:PyUnitSourceRoot'] = 'src'
        layout = mod.SideBySideLayout()
        self.assertEquals(layout.get_source_candidates('src/_foo.py'), ['src/foo.py'])
        self.assertEquals(layout.get_source_candidates('src/_bar.py'), ['src/bar.py'])
        self.assertEquals(layout.get_source_candidates('src/bar/_baz.py'), ['src/bar/baz.py'])
        self.assertEquals(layout.get_source_candidates('_foo.py'), ['foo.py'])


class TestFlatLayout(FileAwareTestCase):
    def setUp(self):
        setUpVimEnvironment()

    def testDetectTestFile(self):
        vimvar['g:PyUnitSourceRoot'] = 'src'
        layout = mod.FlatLayout()
        self.assertTrue(layout.is_test_file('tests/test_foo.py'))
        self.assertTrue(layout.is_test_file('tests/test_foo_bar.py'))
        self.assertTrue(layout.is_test_file('tests/test_foo_bar_baz.py'))
        self.assertFalse(layout.is_test_file('tests/test_foo/test_bar.py'))
        self.assertFalse(layout.is_test_file('foo.py'))
        self.assertFalse(layout.is_test_file('test_foo/test_bar.py'))
        self.assertFalse(layout.is_test_file('tests/foo/test_bar.py'))
        self.assertFalse(layout.is_test_file('src/foo.py'))
        self.assertFalse(layout.is_test_file('src/foo/bar.py'))

    def testDetectTestFileWithAlternatePrefix(self):
        vimvar['g:PyUnitTestPrefix'] = '_'
        vimvar['g:PyUnitSourceRoot'] = 'src'
        vimvar['g:PyUnitTestsRoots'] = 'tests'
        layout = mod.FlatLayout()
        self.assertTrue(layout.is_test_file('tests/_foo.py'))
        self.assertTrue(layout.is_test_file('tests/_foo_bar.py'))
        self.assertTrue(layout.is_test_file('tests/_foo_bar_baz.py'))
        self.assertFalse(layout.is_test_file('tests/_foo/_bar.py'))
        self.assertFalse(layout.is_test_file('foo.py'))
        self.assertFalse(layout.is_test_file('_foo/_bar.py'))
        self.assertFalse(layout.is_test_file('tests/foo/_bar.py'))
        self.assertFalse(layout.is_test_file('src/foo.py'))
        self.assertFalse(layout.is_test_file('src/foo/bar.py'))

    def testDetectAbsoluteTestFile(self):
        vimvar['g:PyUnitTestPrefix'] = '_'
        vimvar['g:PyUnitSourceRoot'] = 'src'
        vimvar['g:PyUnitTestsRoots'] = 'tests'
        absdir = os.path.realpath(proj_root)
        layout = mod.FlatLayout()
        self.assertTrue(layout.is_test_file('%s/tests/_foo.py' % absdir))
        self.assertTrue(layout.is_test_file('%s/tests/_foo_bar.py' % absdir))
        self.assertFalse(layout.is_test_file('%s/tests/_foo/_bar.py' % absdir))
        self.assertFalse(layout.is_test_file('%s/foo.py' % absdir))
        self.assertFalse(layout.is_test_file('%s/_foo/_bar.py' % absdir))
        self.assertFalse(layout.is_test_file('%s/tests/foo/_bar.py' % absdir))
        self.assertFalse(layout.is_test_file('%s/src/foo.py' % absdir))
        self.assertFalse(layout.is_test_file('%s/src/foo/bar.py' % absdir))

    def testSourceToTestFailsForNonSourceFiles(self):
        vimvar['g:PyUnitSourceRoot'] = 'src'
        layout = mod.FlatLayout()
        self.assertRaises(RuntimeError, layout.get_test_file, 'nonsrc/foo.py')
        self.assertRaises(RuntimeError, layout.get_test_file, 'foo.py')
        #self.assertRaises(RuntimeError, layout.get_test_file, 'src.py')

    def testSourceToTest(self):
        vimvar['g:PyUnitSourceRoot'] = 'src'
        layout = mod.FlatLayout()
        self.assertEquals(layout.get_test_file('src/foo.py'), 'tests/test_foo.py')
        self.assertEquals(layout.get_test_file('src/bar.py'), 'tests/test_bar.py')
        self.assertEquals(layout.get_test_file('src/bar/baz.py'), 'tests/test_bar_baz.py')

    def testSourceToTestWithAlternatePrefix(self):
        vimvar['g:PyUnitTestPrefix'] = '_'
        vimvar['g:PyUnitSourceRoot'] = 'src'
        layout = mod.FlatLayout()
        self.assertEquals(layout.get_test_file('src/foo.py'), 'tests/_foo.py')
        self.assertEquals(layout.get_test_file('src/bar.py'), 'tests/_bar.py')
        self.assertEquals(layout.get_test_file('src/bar/baz.py'), 'tests/_bar_baz.py')

    def testTestToSource(self):
        vimvar['g:PyUnitSourceRoot'] = 'src'
        layout = mod.FlatLayout()
        self.assertEquals(layout.get_source_candidates('tests/test_foo.py'), ['src/foo.py', 'src/foo/__init__.py'])
        self.assertEquals(layout.get_source_candidates('tests/test_bar.py'), ['src/bar.py', 'src/bar/__init__.py'])
        self.assertEquals(layout.get_source_candidates('tests/test_foo_bar.py'), ['src/foo/bar.py', 'src/foo/bar/__init__.py'])
        self.assertRaises(RuntimeError, layout.get_source_candidates, 'tests/foo/test_bar.py')
        self.assertRaises(RuntimeError, layout.get_source_candidates, 'test_foo.py')

    def testTestToSourceWithAlternatePrefix(self):
        vimvar['g:PyUnitSourceRoot'] = 'src'
        vimvar['g:PyUnitTestPrefix'] = '_'
        layout = mod.FlatLayout()
        self.assertEquals(layout.get_source_candidates('tests/_foo.py'), ['src/foo.py', 'src/foo/__init__.py'])
        self.assertEquals(layout.get_source_candidates('tests/_bar.py'), ['src/bar.py', 'src/bar/__init__.py'])
        self.assertEquals(layout.get_source_candidates('tests/_foo_bar.py'), ['src/foo/bar.py', 'src/foo/bar/__init__.py'])


class TestFollowHierarcyLayout(FileAwareTestCase):
    def setUp(self):
        setUpVimEnvironment()

    def testDetectTestFile(self):
        vimvar['g:PyUnitSourceRoot'] = 'src'
        vimvar['g:PyUnitTestsRoot'] = 'tests'
        layout = mod.FollowHierarchyLayout()
        self.assertTrue(layout.is_test_file('tests/test_foo.py'))
        self.assertTrue(layout.is_test_file('tests/test_foo/test_bar.py'))
        self.assertFalse(layout.is_test_file('foo.py'))
        self.assertFalse(layout.is_test_file('test_foo/test_bar.py'))
        self.assertFalse(layout.is_test_file('tests/foo/test_bar.py'))
        self.assertFalse(layout.is_test_file('src/foo.py'))
        self.assertFalse(layout.is_test_file('src/foo/bar.py'))

    def testDetectTestFileWithAlternatePrefix(self):
        vimvar['g:PyUnitTestPrefix'] = '_'
        vimvar['g:PyUnitSourceRoot'] = 'src'
        vimvar['g:PyUnitTestsRoots'] = 'tests'
        layout = mod.FollowHierarchyLayout()
        self.assertTrue(layout.is_test_file('tests/_foo.py'))
        self.assertTrue(layout.is_test_file('tests/_foo/_bar.py'))
        self.assertFalse(layout.is_test_file('foo.py'))
        self.assertFalse(layout.is_test_file('_foo/_bar.py'))
        self.assertFalse(layout.is_test_file('tests/foo/_bar.py'))
        self.assertFalse(layout.is_test_file('src/foo.py'))
        self.assertFalse(layout.is_test_file('src/foo/bar.py'))

    def testDetectAbsoluteTestFile(self):
        vimvar['g:PyUnitSourceRoot'] = 'src'
        vimvar['g:PyUnitTestsRoots'] = 'tests'
        absdir = os.path.realpath(proj_root)
        layout = mod.FollowHierarchyLayout()
        self.assertTrue(layout.is_test_file('%s/tests/test_foo.py' % absdir))
        self.assertTrue(layout.is_test_file('%s/tests/test_foo/test_bar.py' % absdir))
        self.assertFalse(layout.is_test_file('%s/foo.py' % absdir))
        self.assertFalse(layout.is_test_file('%s/test_foo/test_bar.py' % absdir))
        self.assertFalse(layout.is_test_file('%s/tests/foo/test_bar.py' % absdir))
        self.assertFalse(layout.is_test_file('%s/src/foo.py' % absdir))
        self.assertFalse(layout.is_test_file('%s/src/foo/bar.py' % absdir))

    def testSourceToTestFailsForNonSourceFiles(self):
        vimvar['g:PyUnitSourceRoot'] = 'src'
        layout = mod.FollowHierarchyLayout()
        self.assertRaises(RuntimeError, layout.get_test_file, 'nonsrc/foo.py')
        self.assertRaises(RuntimeError, layout.get_test_file, 'foo.py')
        #self.assertRaises(RuntimeError, layout.get_test_file, 'src.py')

    def testSourceToTest(self):
        vimvar['g:PyUnitSourceRoot'] = 'src'
        layout = mod.FollowHierarchyLayout()
        self.assertEquals(layout.get_test_file('src/foo.py'), 'tests/test_foo.py')
        self.assertEquals(layout.get_test_file('src/bar.py'), 'tests/test_bar.py')
        self.assertEquals(layout.get_test_file('src/bar/baz.py'), 'tests/test_bar/test_baz.py')

    def testSourceToTestWithAlternatePrefix(self):
        vimvar['g:PyUnitSourceRoot'] = 'src'
        vimvar['g:PyUnitTestPrefix'] = '_'
        layout = mod.FollowHierarchyLayout()
        self.assertEquals(layout.get_test_file('src/foo.py'), 'tests/_foo.py')
        self.assertEquals(layout.get_test_file('src/bar.py'), 'tests/_bar.py')
        self.assertEquals(layout.get_test_file('src/bar/baz.py'), 'tests/_bar/_baz.py')

    def testTestToSource(self):
        vimvar['g:PyUnitSourceRoot'] = ''
        layout = mod.FollowHierarchyLayout()
        self.assertEquals(layout.get_source_candidates('tests/test_foo.py'), ['foo.py', 'foo/__init__.py'])
        self.assertEquals(layout.get_source_candidates('tests/test_bar.py'), ['bar.py', 'bar/__init__.py'])
        self.assertEquals(layout.get_source_candidates('tests/bar/test_baz.py'), ['bar/baz.py', 'bar/baz/__init__.py'])
        self.assertRaises(RuntimeError, layout.get_source_candidates, 'test_foo.py')

    def testTestToCustomSource(self):
        vimvar['g:PyUnitSourceRoot'] = 'src'
        layout = mod.FollowHierarchyLayout()
        self.assertEquals(layout.get_source_candidates('tests/test_foo.py'), ['src/foo.py', 'src/foo/__init__.py'])
        self.assertEquals(layout.get_source_candidates('tests/test_bar.py'), ['src/bar.py', 'src/bar/__init__.py'])
        self.assertEquals(layout.get_source_candidates('tests/bar/test_baz.py'), ['src/bar/baz.py', 'src/bar/baz/__init__.py'])
        self.assertRaises(RuntimeError, layout.get_source_candidates, 'test_foo.py')

    def testTestToSourceWithAlternatePrefix(self):
        vimvar['g:PyUnitSourceRoot'] = 'src'
        vimvar['g:PyUnitTestPrefix'] = '_'
        layout = mod.FollowHierarchyLayout()
        self.assertEquals(layout.get_source_candidates('tests/_foo.py'), ['src/foo.py', 'src/foo/__init__.py'])
        self.assertEquals(layout.get_source_candidates('tests/_bar.py'), ['src/bar.py', 'src/bar/__init__.py'])
        self.assertEquals(layout.get_source_candidates('tests/bar/_baz.py'), ['src/bar/baz.py', 'src/bar/baz/__init__.py'])
        self.assertRaises(RuntimeError, layout.get_source_candidates, '_foo.py')


class TestNoseLayout(FileAwareTestCase):
    def setUp(self):
        setUpVimEnvironment()

    def testDetectTestFile(self):
        vimvar['g:PyUnitSourceRoot'] = 'src'
        vimvar['g:PyUnitTestsRoot'] = 'tests'
        layout = mod.NoseLayout()
        self.assertTrue(layout.is_test_file('tests/test_foo.py'))
        self.assertTrue(layout.is_test_file('tests/foo/test_bar.py'))
        self.assertFalse(layout.is_test_file('foo.py'))
        self.assertFalse(layout.is_test_file('test_foo/test_bar.py'))
        self.assertFalse(layout.is_test_file('src/foo.py'))
        self.assertFalse(layout.is_test_file('src/foo/bar.py'))

    def testDetectTestFileWithAlternatePrefix(self):
        vimvar['g:PyUnitTestPrefix'] = '_'
        vimvar['g:PyUnitSourceRoot'] = 'src'
        vimvar['g:PyUnitTestsRoots'] = 'tests'
        layout = mod.NoseLayout()
        self.assertTrue(layout.is_test_file('tests/_foo.py'))
        self.assertTrue(layout.is_test_file('tests/foo/_bar.py'))
        self.assertFalse(layout.is_test_file('foo.py'))
        self.assertFalse(layout.is_test_file('_foo/_bar.py'))
        self.assertFalse(layout.is_test_file('src/foo.py'))
        self.assertFalse(layout.is_test_file('src/foo/bar.py'))

    def testDetectAbsoluteTestFile(self):
        vimvar['g:PyUnitSourceRoot'] = 'src'
        vimvar['g:PyUnitTestsRoots'] = 'tests'
        absdir = os.path.realpath(proj_root)
        layout = mod.NoseLayout()
        self.assertTrue(layout.is_test_file('%s/tests/test_foo.py' % absdir))
        self.assertTrue(layout.is_test_file('%s/tests/foo/test_bar.py' % absdir))
        self.assertFalse(layout.is_test_file('%s/foo.py' % absdir))
        self.assertFalse(layout.is_test_file('%s/test_foo/test_bar.py' % absdir))
        self.assertFalse(layout.is_test_file('%s/src/foo.py' % absdir))
        self.assertFalse(layout.is_test_file('%s/src/foo/bar.py' % absdir))

    def testSourceToTestFailsForNonSourceFiles(self):
        vimvar['g:PyUnitSourceRoot'] = 'src'
        layout = mod.NoseLayout()
        self.assertRaises(RuntimeError, layout.get_test_file, 'nonsrc/foo.py')
        self.assertRaises(RuntimeError, layout.get_test_file, 'foo.py')
        #self.assertRaises(RuntimeError, layout.get_test_file, 'src.py')

    def testSourceToTest(self):
        vimvar['g:PyUnitSourceRoot'] = 'src'
        layout = mod.NoseLayout()
        self.assertEquals(layout.get_test_file('src/foo.py'), 'tests/test_foo.py')
        self.assertEquals(layout.get_test_file('src/bar.py'), 'tests/test_bar.py')
        self.assertEquals(layout.get_test_file('src/bar/baz.py'), 'tests/bar/test_baz.py')

    def testSourceToTestWithAlternatePrefix(self):
        vimvar['g:PyUnitSourceRoot'] = 'src'
        vimvar['g:PyUnitTestPrefix'] = '_'
        layout = mod.NoseLayout()
        self.assertEquals(layout.get_test_file('src/foo.py'), 'tests/_foo.py')
        self.assertEquals(layout.get_test_file('src/bar.py'), 'tests/_bar.py')
        self.assertEquals(layout.get_test_file('src/bar/baz.py'), 'tests/bar/_baz.py')

    def testTestToSource(self):
        vimvar['g:PyUnitSourceRoot'] = ''
        layout = mod.NoseLayout()
        self.assertEquals(layout.get_source_candidates('tests/test_foo.py'),
                ['foo.py', 'foo/__init__.py'])
        self.assertEquals(layout.get_source_candidates('tests/test_bar.py'),
                ['bar.py', 'bar/__init__.py'])
        self.assertEquals(layout.get_source_candidates('tests/bar/test_baz.py'),
                ['bar/baz.py', 'bar/baz/__init__.py'])
        self.assertRaises(RuntimeError, layout.get_source_candidates,
                'test_foo.py')

    def testTestToCustomSource(self):
        vimvar['g:PyUnitSourceRoot'] = 'src'
        layout = mod.NoseLayout()
        self.assertEquals(layout.get_source_candidates('tests/test_foo.py'),
                ['src/foo.py', 'src/foo/__init__.py'])
        self.assertEquals(layout.get_source_candidates('tests/test_bar.py'),
                ['src/bar.py', 'src/bar/__init__.py'])
        self.assertEquals(layout.get_source_candidates('tests/bar/test_baz.py'),
                ['src/bar/baz.py', 'src/bar/baz/__init__.py'])
        self.assertRaises(RuntimeError, layout.get_source_candidates, 'test_foo.py')

    def testTestToSourceWithAlternatePrefix(self):
        vimvar['g:PyUnitSourceRoot'] = 'src'
        vimvar['g:PyUnitTestPrefix'] = '_'
        layout = mod.NoseLayout()
        self.assertEquals(layout.get_source_candidates('tests/_foo.py'),
                ['src/foo.py', 'src/foo/__init__.py'])
        self.assertEquals(layout.get_source_candidates('tests/_bar.py'),
                ['src/bar.py', 'src/bar/__init__.py'])
        self.assertEquals(layout.get_source_candidates('tests/bar/_baz.py'),
                ['src/bar/baz.py', 'src/bar/baz/__init__.py'])
        self.assertRaises(RuntimeError, layout.get_source_candidates, '_foo.py')


class TestPlugin(FileAwareTestCase):
    def setUp(self):
        setUpVimEnvironment()

    def test_patch(self):
        self.assertEquals(vim.eval('g:PyUnitTestPrefix'), 'test_')
        self.assertEquals(vim.eval('g:PyUnitShowTests'), '1')


    def test_is_fs_root(self):
        self.assertTrue(mod.is_fs_root('/'))
        self.assertFalse(mod.is_fs_root(''))
        self.assertTrue(mod.is_fs_root(os.path.expandvars('$HOME')))
        vimvar['g:ProjRootStopAtHomeDir'] = '0'
        self.assertFalse(mod.is_fs_root(os.path.expandvars('$HOME')))

    def test_find_project_root(self):
        self.assertEquals(mod.find_project_root(currfile), proj_root)

    def test_relpath(self):
        # Nice and simple
        self.assertEquals(
                mod._relpath('/tmp/foo/bar', '/tmp', try_stdlib=False),
                'foo/bar')
        self.assertEquals(
                mod._relpath('/etc/passwd', '/', try_stdlib=False),
                'etc/passwd')

        # Walking backward
        self.assertEquals(
                mod._relpath('.././foo/bar.py', '.', try_stdlib=False),
                '../foo/bar.py')
        self.assertEquals(
                mod._relpath('/a/b', '/c', try_stdlib=False),
                '../a/b')
        self.assertEquals(
                mod._relpath('/a/b/c', '/d/e', try_stdlib=False),
                '../../a/b/c')
        self.assertEquals(
                mod._relpath('/', '/a/b', try_stdlib=False),
                '../../')

        # Directory signs shouldn't matter
        self.assertEquals(
                mod._relpath('foo/', 'foo', try_stdlib=False), '.')
        self.assertEquals(
                mod._relpath('foo', 'foo/', try_stdlib=False), '.')
        self.assertEquals(
                mod._relpath('foo', 'foo', try_stdlib=False), '.')


    def test_is_test_file(self):
        self.assertTrue(mod.is_test_file('tests/test_foo.py'))

        vimvar['g:PyUnitTestsRoot'] = 'my/test/dir'
        self.assertFalse(mod.is_test_file('tests/test_foo.py'))

    def test_get_test_file_for_normal_source_file(self):
        self.assertSameFile(
                mod.get_test_file_for_source_file('foo/bar/qux.py'),
                'tests/test_foo/test_bar/test_qux.py')

        vimvar['g:PyUnitTestsRoot'] = 'misc/mytests'
        self.assertSameFile(
                mod.get_test_file_for_source_file('foo/bar/qux.py'),
                'misc/mytests/test_foo/test_bar/test_qux.py')

        vimvar['g:PyUnitTestsStructure'] = 'flat'
        self.assertSameFile(
                mod.get_test_file_for_source_file('foo/bar/qux.py'),
                'misc/mytests/test_foo_bar_qux.py')

    def test_get_test_file_for_init_source_file(self):
        self.assertSameFile(
                mod.get_test_file_for_source_file('foo/bar/__init__.py'),
                'tests/test_foo/test_bar.py')

        vimvar['g:PyUnitTestsRoot'] = 'misc/mytests'
        self.assertSameFile(
                mod.get_test_file_for_source_file('foo/bar/__init__.py'),
                'misc/mytests/test_foo/test_bar.py')

        vimvar['g:PyUnitTestsStructure'] = 'flat'
        self.assertSameFile(
                mod.get_test_file_for_source_file('foo/bar/__init__.py'),
                'misc/mytests/test_foo_bar.py')

    def test_get_source_file_for_test_file(self):
        self.assertRaises(Exception,
                mod.find_source_file_for_test_file, currfile)

        vimvar['g:PyUnitSourceRoot'] = 'src'
        self.assertSameFile(
                mod.find_source_file_for_test_file('tests/test_python_unittests.py'),
                os.path.realpath('src/python_unittests.py'))


    def test_vim_split_cmd(self):
        self.assertEquals(mod._vim_split_cmd(), 'vert rightb')
        self.assertEquals(mod._vim_split_cmd(True), 'vert lefta')

        vimvar['g:PyUnitTestsSplitWindow'] = 'left'
        self.assertEquals(mod._vim_split_cmd(), 'vert lefta')
        self.assertEquals(mod._vim_split_cmd(True), 'vert rightb')

        vimvar['g:PyUnitTestsSplitWindow'] = 'top'
        self.assertEquals(mod._vim_split_cmd(), 'lefta')
        self.assertEquals(mod._vim_split_cmd(True), 'rightb')

        vimvar['g:PyUnitTestsSplitWindow'] = 'bottom'
        self.assertEquals(mod._vim_split_cmd(True), 'lefta')
        self.assertEquals(mod._vim_split_cmd(), 'rightb')

    def test_open_buffer_cmd(self):
        vimvar['bufexists("foo")'] = '1'
        self.assertEquals(mod._open_buffer_cmd('foo'),
                'vert rightb sbuffer foo')
        self.assertEquals(mod._open_buffer_cmd('foo', opposite=True),
                'vert lefta sbuffer foo')

        vimvar['bufexists("foo")'] = '0'
        self.assertEquals(mod._open_buffer_cmd('foo'),
                'vert rightb split foo')

        vimvar['g:PyUnitTestsSplitWindow'] = 'no'
        self.assertEquals(mod._open_buffer_cmd('foo'),
                'edit foo')



########NEW FILE########
