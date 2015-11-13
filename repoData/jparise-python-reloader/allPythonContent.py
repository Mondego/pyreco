__FILENAME__ = monitor
# Python Module Reloader
#
# Copyright (c) 2009, 2010 Jon Parise <jon@indelible.org>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import imp
import os
try:
    import queue
except ImportError:
    #python 2.x
    import Queue as queue
import reloader
import sys
import threading
import time

_win32 = (sys.platform == 'win32')

def _normalize_filename(filename):
    if filename is not None:
        if filename.endswith('.pyc') or filename.endswith('.pyo'):
            filename = filename[:-1]
        elif filename.endswith('$py.class'):
            filename = filename[:-9] + '.py'
    return filename

class ModuleMonitor(threading.Thread):
    """Monitor module source file changes"""

    def __init__(self, interval=1):
        threading.Thread.__init__(self)
        self.daemon = True
        self.mtimes = {}
        self.queue = queue.Queue()
        self.interval = interval

    def run(self):
        while True:
            self._scan()
            time.sleep(self.interval)

    def _scan(self):
        # We're only interested in file-based modules (not C extensions).
        modules = [m.__file__ for m in sys.modules.values()
                   if m and getattr(m, '__file__', None)]

        for filename in modules:
            # We're only interested in the source .py files.
            filename = _normalize_filename(filename)

            # stat() the file.  This might fail if the module is part of a
            # bundle (.egg).  We simply skip those modules because they're
            # not really reloadable anyway.
            try:
                stat = os.stat(filename)
            except OSError:
                continue

            # Check the modification time.  We need to adjust on Windows.
            mtime = stat.st_mtime
            if _win32:
                mtime -= stat.st_ctime

            # Check if we've seen this file before.  We don't need to do
            # anything for new files.
            if filename in self.mtimes:
                # If this file's mtime has changed, queue it for reload.
                if mtime != self.mtimes[filename]:
                    self.queue.put(filename)

            # Record this filename's current mtime.
            self.mtimes[filename] = mtime

class Reloader(object):

    def __init__(self, interval=1):
        self.monitor = ModuleMonitor(interval=interval)
        self.monitor.start()

    def poll(self):
        filenames = set()
        while not self.monitor.queue.empty():
            try:
                filenames.add(self.monitor.queue.get_nowait())
            except queue.Empty:
                break
        if filenames:
            self._reload(filenames)

    def _reload(self, filenames):
        modules = [m for m in sys.modules.values()
            if _normalize_filename(getattr(m, '__file__', None)) in filenames]

        for mod in modules:
            reloader.reload(mod)

########NEW FILE########
__FILENAME__ = reloader
# Python Module Reloader
#
# Copyright (c) 2009-2014 Jon Parise <jon@indelible.org>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

"""Python Module Reloader"""

try:
    import builtins
except ImportError:
    import __builtin__ as builtins

import imp
import sys
import types

__author__ = 'Jon Parise <jon@indelible.org>'
__version__ = '0.5'

__all__ = ('enable', 'disable', 'get_dependencies', 'reload')

_baseimport = builtins.__import__
_blacklist = None
_dependencies = dict()
_parent = None

# Jython doesn't have imp.reload().
if not hasattr(imp, 'reload'):
    imp.reload = reload

# PEP 328 changed the default level to 0 in Python 3.3.
_default_level = -1 if sys.version_info < (3, 3) else 0

def enable(blacklist=None):
    """Enable global module dependency tracking.

    A blacklist can be specified to exclude specific modules (and their import
    hierachies) from the reloading process.  The blacklist can be any iterable
    listing the fully-qualified names of modules that should be ignored.  Note
    that blacklisted modules will still appear in the dependency graph; they
    will just not be reloaded.
    """
    global _blacklist
    builtins.__import__ = _import
    if blacklist is not None:
        _blacklist = frozenset(blacklist)

def disable():
    """Disable global module dependency tracking."""
    global _blacklist, _parent
    builtins.__import__ = _baseimport
    _blacklist = None
    _dependencies.clear()
    _parent = None

def get_dependencies(m):
    """Get the dependency list for the given imported module."""
    name = m.__name__ if isinstance(m, types.ModuleType) else m
    return _dependencies.get(name, None)

def _deepcopy_module_dict(m):
    """Make a deep copy of a module's dictionary."""
    import copy

    # We can't deepcopy() everything in the module's dictionary because some
    # items, such as '__builtins__', aren't deepcopy()-able.  To work around
    # that, we start by making a shallow copy of the dictionary, giving us a
    # way to remove keys before performing the deep copy.
    d = vars(m).copy()
    del d['__builtins__']
    return copy.deepcopy(d)

def _reload(m, visited):
    """Internal module reloading routine."""
    name = m.__name__

    # If this module's name appears in our blacklist, skip its entire
    # dependency hierarchy.
    if _blacklist and name in _blacklist:
        return

    # Start by adding this module to our set of visited modules.  We use this
    # set to avoid running into infinite recursion while walking the module
    # dependency graph.
    visited.add(m)

    # Start by reloading all of our dependencies in reverse order.  Note that
    # we recursively call ourself to perform the nested reloads.
    deps = _dependencies.get(name, None)
    if deps is not None:
        for dep in reversed(deps):
            if dep not in visited:
                _reload(dep, visited)

    # Clear this module's list of dependencies.  Some import statements may
    # have been removed.  We'll rebuild the dependency list as part of the
    # reload operation below.
    try:
        del _dependencies[name]
    except KeyError:
        pass

    # Because we're triggering a reload and not an import, the module itself
    # won't run through our _import hook below.  In order for this module's
    # dependencies (which will pass through the _import hook) to be associated
    # with this module, we need to set our parent pointer beforehand.
    global _parent
    _parent = name

    # If the module has a __reload__(d) function, we'll call it with a copy of
    # the original module's dictionary after it's been reloaded.
    callback = getattr(m, '__reload__', None)
    if callback is not None:
        d = _deepcopy_module_dict(m)
        imp.reload(m)
        callback(d)
    else:
        imp.reload(m)

    # Reset our parent pointer now that the reloading operation is complete.
    _parent = None

def reload(m):
    """Reload an existing module.

    Any known dependencies of the module will also be reloaded.

    If a module has a __reload__(d) function, it will be called with a copy of
    the original module's dictionary after the module is reloaded."""
    _reload(m, set())

def _import(name, globals=None, locals=None, fromlist=None, level=_default_level):
    """__import__() replacement function that tracks module dependencies."""
    # Track our current parent module.  This is used to find our current place
    # in the dependency graph.
    global _parent
    parent = _parent
    _parent = name

    # Perform the actual import work using the base import function.
    base = _baseimport(name, globals, locals, fromlist, level)

    if base is not None and parent is not None:
        m = base

        # We manually walk through the imported hierarchy because the import
        # function only returns the top-level package reference for a nested
        # import statement (e.g. 'package' for `import package.module`) when
        # no fromlist has been specified.
        if fromlist is None:
            for component in name.split('.')[1:]:
                m = getattr(m, component)

        # If this is a nested import for a reloadable (source-based) module,
        # we append ourself to our parent's dependency list.
        if hasattr(m, '__file__'):
            l = _dependencies.setdefault(parent, [])
            l.append(m)

    # Lastly, we always restore our global _parent pointer.
    _parent = parent

    return base

########NEW FILE########
__FILENAME__ = test_reloader
import os
import sys
import unittest

class ReloaderTests(unittest.TestCase):

    def setUp(self):
        self.modules = {}

        # Save the existing system bytecode setting so that it can
        # be restored later.  We need to disable bytecode writing
        # for our module-(re)writing tests.
        self._dont_write_bytecode = sys.dont_write_bytecode
        sys.dont_write_bytecode = True

    def tearDown(self):
        # Clean up any modules that this test wrote.
        for name, filename in self.modules.items():
            if name in sys.modules:
                del sys.modules[name]
            if os.path.exists(filename):
                os.unlink(filename)

        # Restore the system bytecode setting.
        sys.dont_write_bytecode = self._dont_write_bytecode

    def test_import(self):
        import reloader
        self.assertTrue('reloader' in sys.modules)
        self.assertTrue(hasattr(reloader, 'enable'))

    def test_reload(self):
        import reloader
        reloader.enable()

        self.write_module('testmodule', "def func(): return 'Some code.'\n")
        import tests.testmodule
        self.assertEqual('Some code.', tests.testmodule.func())

        self.write_module('testmodule', "def func(): return 'New code.'\n")
        reloader.reload(tests.testmodule)
        self.assertEqual('New code.', tests.testmodule.func())

        self.write_module('testmodule', "def func(): return 'More code.'\n")
        reloader.reload(tests.testmodule)
        self.assertEqual('More code.', tests.testmodule.func())

        reloader.disable()

    def test_blacklist(self):
        import reloader
        reloader.enable(['blacklisted'])

        self.write_module('blacklisted', "def func(): return True\n")
        self.write_module('testmodule', "import tests.blacklisted\n")

        import tests.blacklisted, tests.testmodule

        reloader.disable()

    def write_module(self, name, contents):
        filename = os.path.join(os.path.dirname(__file__), name + '.py')
        self.modules['tests.' + name] = filename

        f = open(filename, 'w')
        f.write(contents)
        f.close()

########NEW FILE########
