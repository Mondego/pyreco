__FILENAME__ = bdist_bbfreeze
"""bbfreeze.bdist_bbfreeze

Implements the distutils 'bdist_bbfreeze' command.
"""

__author__ = "Hartmut Goebel <h.goebel@goebel-consult.de>"
__copyright__ = "Copyright 2008 by Hartmut Goebel <h.goebel@goebel-consult.de>"
__licence__ = "Same as bbfreeze"
__version__ = "0.1"

import os

from distutils.util import get_platform
from distutils import log

from setuptools.command.easy_install import easy_install, get_script_args
from pkg_resources import Distribution, PathMetadata, normalize_path


class bdist_bbfreeze(easy_install):
    # this is a bit hackish: we inherit from easy_install,
    # but discard most of it

    description = "freeze scripts using bbfreeze"

    user_options = [
        ('bdist-base=', 'b',
         "temporary directory for creating built distributions"),
        ('plat-name=', 'p',
         "platform name to embed in generated filenames "
         "(default: %s)" % get_platform()),
        ('dist-dir=', 'd',
         "directory to put final built distributions in "
         "[default: dist/<egg_name-egg_version>]"),
        # todo: include_py
        ]

    boolean_options = []
    negative_opt = {}

    def initialize_options(self):
        self.bdist_base = None
        self.plat_name = None
        self.dist_dir = None
        self.include_py = False
        easy_install.initialize_options(self)
        self.outputs = []

    def finalize_options(self):
        # have to finalize 'plat_name' before 'bdist_base'
        if self.plat_name is None:
            self.plat_name = get_platform()

        # 'bdist_base' -- parent of per-built-distribution-format
        # temporary directories (eg. we'll probably have
        # "build/bdist.<plat>/dumb", "build/bdist.<plat>/rpm", etc.)
        if self.bdist_base is None:
            build_base = self.get_finalized_command('build').build_base
            self.bdist_base = os.path.join(build_base,
                                           'bbfreeze.' + self.plat_name)
        self.script_dir = self.bdist_base

        if self.dist_dir is None:
            self.dist_dir = "dist"

    def run(self, wininst=False):
        # import bbfreeze only thenabout to run the command
        from bbfreeze import Freezer

        # get information from egg_info
        ei = self.get_finalized_command("egg_info")
        target = normalize_path(self.bdist_base)
        dist = Distribution(
            target,
            PathMetadata(target, os.path.abspath(ei.egg_info)),
            project_name=ei.egg_name)

        # install wrapper_Scripts into self.bdist_base == self.script_dir
        self.install_wrapper_scripts(dist)

        # now get a Freezer()
        f = Freezer(os.path.join(self.dist_dir,
                                 "%s-%s" % (ei.egg_name, ei.egg_version)))
        f.include_py = self.include_py

        # freeze each of the scripts
        for args in get_script_args(dist, wininst=wininst):
            name = args[0]
            if name.endswith('.exe') or name.endswith(".exe.manifest"):
                # skip .exes
                continue
            log.info('bbfreezing %s', os.path.join(self.script_dir, name))
            f.addScript(os.path.join(self.script_dir, name),
                        gui_only=name.endswith('.pyw'))
        # starts the freezing process
        f()

########NEW FILE########
__FILENAME__ = codehack
"""bytecode manipulation"""


def replace_functions(co, repl):
    """replace the functions in the code object co with those from repl.
       repl can either be a code object or a source code string.
       returns a new code object.
    """
    import new
    if isinstance(repl, basestring):
        repl = compile(repl, co.co_name, "exec")

    name2repl = {}
    for c in repl.co_consts:
        if isinstance(c, type(repl)):
            name2repl[c.co_name] = c

    consts = list(co.co_consts)
    for i in range(len(consts)):
        c = consts[i]
        if isinstance(c, type(repl)):
            if c.co_name in name2repl:
                consts[i] = name2repl[c.co_name]
                print "codehack: replaced %s in %s" % (c.co_name, co.co_filename)

    return new.code(co.co_argcount, co.co_nlocals, co.co_stacksize,
                     co.co_flags, co.co_code, tuple(consts), co.co_names,
                     co.co_varnames, co.co_filename, co.co_name,
                     co.co_firstlineno, co.co_lnotab,
                     co.co_freevars, co.co_cellvars)

########NEW FILE########
__FILENAME__ = eggutil
#! /usr/bin/env python

import sys
import os
import stat
import zipfile
import struct
import imp
import marshal
import time


class Entry(object):
    read = None
    stat = None

    def __init__(self, **kw):
        self.__dict__.update(kw)

    def __repr__(self):
        return "<Entry %r>" % (self.__dict__,)

    def isdir(self):
        return self.read is None

    def read_replace(self):
        if not self.name.endswith(".pyc"):
            return self.read()

        data = self.read()
        if data[:4] != imp.get_magic():
            return data
        mtime = data[4:8]

        code = marshal.loads(data[8:])
        from bbfreeze import freezer
        code = freezer.replace_paths_in_code(code, self.name)
        return "".join([imp.get_magic(), mtime, marshal.dumps(code)])


def walk(path):
    if os.path.isfile(path):
        return walk_zipfile(path)
    else:
        return walk_dir(path)


def walk_zipfile(path):
    zfobj = zipfile.ZipFile(path)
    for name in zfobj.namelist():
        if name.endswith("/"):
            yield Entry(name=name)
        else:
            yield Entry(name=name, read=lambda name=name: zfobj.read(name))


def walk_dir(path):
    path = os.path.normpath(path)

    def relname(n):
        return os.path.join(dirpath, n)[len(path) + 1:]

    for dirpath, dirnames, filenames in os.walk(path):
        for x in dirnames:
            fp = os.path.join(path, dirpath, x)
            yield Entry(name=relname(x), stat=lambda fp=fp: os.stat(fp))

        for x in filenames:
            fp = os.path.join(path, dirpath, x)
            yield Entry(name=relname(x),
                        read=lambda fp=fp: open(fp, "rb").read(),
                        stat=lambda fp=fp: os.stat(fp))


def default_filter(entries):
    for x in entries:
        if x.name.endswith(".py"):
            continue

        if x.name.endswith(".pyo"):
            continue

        yield x


def write_zipfile(path, entries):
    zf = zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED)
    for x in entries:
        if x.isdir():
            continue

        zf.writestr(x.name, x.read_replace())
    zf.close()


def write_directory(path, entries):
    os.mkdir(path)
    for x in entries:
        fn = os.path.join(path, x.name)
        if x.isdir():
            os.mkdir(fn)
        else:
            dn = os.path.dirname(fn)
            if not os.path.isdir(dn):
                os.makedirs(dn)
            open(fn, "wb").write(x.read_replace())

        if x.stat is None:
            continue

        if x.isdir() and sys.platform == 'win32':
            continue

        st = x.stat()
        mode = stat.S_IMODE(st.st_mode)
        if hasattr(os, 'utime'):
            os.utime(fn, (st.st_atime, st.st_mtime))
        if hasattr(os, 'chmod'):
            os.chmod(fn, mode)


def copyDistribution(distribution, destdir):
    import pkg_resources
    location = distribution.location

    if (isinstance(distribution._provider, pkg_resources.PathMetadata)
        and not distribution.location.lower().endswith(".egg")
        and os.path.exists(os.path.join(distribution.location, "setup.py"))):
        # this seems to be a development egg. FIXME the above test looks fragile

        setuptools_dist = pkg_resources.working_set.find(pkg_resources.Requirement.parse("setuptools"))
        if setuptools_dist:
            os.environ["PYTHONPATH"] = setuptools_dist.location

        cwd = os.getcwd()
        os.chdir(distribution.location)
        try:
            print distribution.location, "looks like a development egg. need to run setup.py bdist_egg"

            from distutils.spawn import spawn
            import tempfile
            import atexit
            import shutil
            tmp = tempfile.mkdtemp()
            atexit.register(shutil.rmtree, tmp)
            cmd = [sys.executable, "-c", "import sys,__main__,setuptools; del sys.argv[0]; __main__.__file__=sys.argv[0], execfile(sys.argv[0],__main__.__dict__,__main__.__dict__)", "setup.py", "-q", "bdist_egg", "--dist", tmp]

            print "running %r in %r" % (" ".join(cmd), os.getcwd())
            spawn(cmd)
            print "====> setup.py bdist_egg finished in", os.getcwd()
            files = os.listdir(tmp)
            assert len(files) > 0, "output directory of bdist_egg command is empty"
            assert len(files) == 1, "expected exactly one file in output directory of bdist_egg command"

            location = os.path.join(tmp, files[0])
        finally:
            os.chdir(cwd)

    dest = os.path.join(destdir, distribution.egg_name() + ".egg")
    print "Copying", location, "to", dest

    entries = list(walk(location))
    name2compile = {}

    for x in entries:
        if x.name.endswith(".py"):
            name2compile[x.name] = x

    entries = list(default_filter(entries))
    for x in entries:
        if x.name.endswith(".pyc"):
            try:
                del name2compile[x.name[:-1]]
            except KeyError:
                pass

    mtime = int(time.time())

    for x in name2compile.values():
        try:
            code = compile(x.read() + '\n', x.name, 'exec')
        except Exception, err:
            print "WARNING: Could not compile %r: %r" % (x.name, err)
            continue

        data = imp.get_magic() + struct.pack("<i", mtime) + marshal.dumps(code)
        entries.append(Entry(name=x.name + 'c', read=lambda data=data: data))

    if distribution.has_metadata("zip-safe") and not os.path.isdir(location):
        write_zipfile(dest, entries)
    else:
        write_directory(dest, entries)

########NEW FILE########
__FILENAME__ = freezer
import os
import sys
import re
import time
import shutil
import struct
import zipfile
import imp
import marshal
import zipimport
import commands

from modulegraph import modulegraph
modulegraph.ReplacePackage("_xmlplus", "xml")

# workaround for win32com hacks.
# see: http://starship.python.net/crew/theller/moin.cgi/WinShell

try:
    import win32com
    for p in win32com.__path__[1:]:
        modulegraph.AddPackagePath("win32com", p)
    for extra in ["win32com.shell", "win32com.mapi"]:
        try:
            __import__(extra)
        except ImportError:
            continue
        m = sys.modules[extra]
        for p in m.__path__[1:]:
            modulegraph.AddPackagePath(extra, p)
except ImportError:
    pass

try:
    import xml
except ImportError:
    pass
else:
    for p in xml.__path__:
        modulegraph.AddPackagePath("xml", p)

from bbfreeze import recipes, eggutil

try:
    import pkg_resources
except ImportError:
    pkg_resources = None

dont_copy_as_egg = set(["bbfreeze", "PyXML"])


def normalize_pkgname(name):
    return name.lower().replace("-", "_")


class EggAnalyzer(object):
    def __init__(self):
        self.used = set()

        if pkg_resources is None:
            return

        self.locations = [x.location for x in list(pkg_resources.working_set)]
        self.usable = None

    def add(self, dist):
        if dist in self.used:
            return

        self.used.add(dist)
        deps = pkg_resources.working_set.resolve(dist.requires())
        for x in deps:
            if x not in self.used:
                print "adding %s as a dependency of %s" % (x, dist)
                self.used.add(x)

    def usableWorkingSet(self):
        from distutils.sysconfig import get_python_lib as gl
        pathcount = {}
        for lib in [gl(0, 0), gl(0, 1), gl(1, 0), gl(1, 1)]:
            pathcount[lib] = 2
            pathcount[os.path.realpath(lib)] = 2  # handle symlinks!

        for x in pkg_resources.working_set:
            try:
                pathcount[x.location] += 1
            except KeyError:
                pathcount[x.location] = 1

        normalized_dont_copy = set([normalize_pkgname(x) for x in dont_copy_as_egg])

        def is_good(dist):
            if normalize_pkgname(dist.project_name) in normalized_dont_copy:
                return False

            if not dist.has_metadata("top_level.txt"):
                return False

            if type(dist._provider) == pkg_resources.FileMetadata:  # no real egg
                return False

            return True

        ws = []
        for x in pkg_resources.working_set:
            if pathcount[x.location] == 1 and is_good(x):
                x._freeze_usable = True
                ws.append(x)
            else:
                x._freeze_usable = False
        return ws

    def findDistribution(self, m):
        if isinstance(m, modulegraph.Script):
            return None

        if pkg_resources is None:
            return None
        if m.filename is None:
            return None
        if self.usable is None:
            self.usable = self.usableWorkingSet()

        fn = m.filename
        for dist in self.usable:
            if fn.startswith(dist.location):
                # do not include eggs if this is a namespace package
                # e.g. "import zope" can find any of "zope.deferredimport", "zope.interface",...
                if dist.has_metadata("namespace_packages.txt"):
                    ns = list(dist.get_metadata_lines("namespace_packages.txt"))
                    if isinstance(m, modulegraph.Package) and m.identifier in ns:
                        #print "SKIP:", ns, m
                        return None

                self.add(dist)
                return dist

    def report(self):
        tmp = [(x.project_name, x) for x in self.used]
        tmp.sort()
        if tmp:
            print "=" * 50
            print "The following eggs are being used:"
            for x in tmp:
                print repr(x[1])
            print "=" * 50

    def copy(self, destdir):
        for x in self.used:
            if x._freeze_usable:
                eggutil.copyDistribution(x, destdir)
            else:
                try:
                    path = getattr(x._provider, "egg_info", None) or x._provider.path
                except AttributeError:
                    print "Warning: cannot copy egg-info for", x
                    continue
                print "Copying egg-info of %s from %r" % (x, path)
                if os.path.isdir(path):
                    basename = "%s.egg-info" % x.project_name
                    shutil.copytree(path, os.path.join(destdir, basename))
                else:
                    shutil.copy2(path, destdir)


def fullname(p):
    import _bbfreeze_loader
    return os.path.join(os.path.dirname(_bbfreeze_loader.__file__), p)


def getRecipes():
    res = []
    for x in dir(recipes):
        if x.startswith("recipe_"):
            r = getattr(recipes, x)
            if r:
                res.append(r)

    return res


class SharedLibrary(modulegraph.Node):
    def __init__(self, identifier):
        self.graphident = identifier
        self.identifier = identifier
        self.filename = None


class Executable(modulegraph.Node):
    def __init__(self, identifier):
        self.graphident = identifier
        self.identifier = identifier
        self.filename = None


class CopyTree(modulegraph.Node):
    def __init__(self, identifier, dest):
        self.graphident = identifier
        self.identifier = identifier
        self.filename = identifier
        self.dest = dest


class ZipModule(modulegraph.BaseModule):
    pass


class MyModuleGraph(modulegraph.ModuleGraph):
    def _find_single_path(self, name, p, parent=None):
        """find module or zip module in directory or zipfile p"""
        if parent is not None:
            # assert path is not None
            fullname = parent.identifier + '.' + name
        else:
            fullname = name

        try:
            return modulegraph.ModuleGraph.find_module(self, name, [p], parent)
        except ImportError, err:
            pass

        if not os.path.isfile(p):
            raise err

        zi = zipimport.zipimporter(p)
        m = zi.find_module(fullname.replace(".", "/"))
        if m:
            code = zi.get_code(fullname.replace(".", "/"))
            return zi, p, ('', '', 314)
        raise err

    def copyTree(self, source, dest, parent):
        n = self.createNode(CopyTree, source, dest)
        self.createReference(parent, n)

    def find_module(self, name, path, parent=None):
        paths_seen = set()

        if parent is not None:
            # assert path is not None
            fullname = parent.identifier + '.' + name
        else:
            fullname = name

        #print "FIND_MODULE:", name, path, parent

        if path is None:
            path = self.path

        found = []

        def append_if_uniq(r):
            for t in found:
                if r[1] == t[1]:
                    return
            found.append(r)

        for p in path:
            try:
                p = os.path.normcase(os.path.normpath(os.path.abspath(p)))
                if p in paths_seen:
                    continue
                paths_seen.add(p)
                #res = modulegraph.ModuleGraph.find_module(self, name, [p], parent)
                res = self._find_single_path(name, p, parent)
                if found:
                    if res[2][2] == imp.PKG_DIRECTORY:
                        append_if_uniq(res)
                else:
                    if res[2][2] == imp.PKG_DIRECTORY:
                        append_if_uniq(res)
                    else:
                        return res
            except ImportError, err:
                pass

        if len(found) > 1:
            print "WARNING: found %s in multiple directories. Assuming it's a namespace package. (found in %s)" % (
                fullname, ", ".join(x[1] for x in found))
            for x in found[1:]:
                modulegraph.AddPackagePath(fullname, x[1])

        if found:
            return found[0]

        raise err

    def load_module(self, fqname, fp, pathname, (suffix, mode, typ)):
        if typ == 314:
            m = self.createNode(ZipModule, fqname)
            code = fp.get_code(fqname.replace(".", "/"))
            m.filename = fp.archive
            m.packagepath = [fp.archive]
            m.code = code
            m.is_package = fp.is_package(fqname.replace(".", "/"))

            self.scan_code(m.code, m)
            return m
        else:
            return modulegraph.ModuleGraph.load_module(self, fqname, fp, pathname, (suffix, mode, typ))


def replace_paths_in_code(co, newname):
    import new
    if newname.endswith('.pyc'):
        newname = newname[:-1]

    consts = list(co.co_consts)

    for i in range(len(consts)):
        if isinstance(consts[i], type(co)):
            consts[i] = replace_paths_in_code(consts[i], newname)

    return new.code(co.co_argcount, co.co_nlocals, co.co_stacksize,
                     co.co_flags, co.co_code, tuple(consts), co.co_names,
                     co.co_varnames, newname, co.co_name,
                     co.co_firstlineno, co.co_lnotab,
                     co.co_freevars, co.co_cellvars)

def make_extension_loader(modname):
    src = """
def _bbfreeze_import_dynamic_module():
    global _bbfreeze_import_dynamic_module
    del _bbfreeze_import_dynamic_module
"""
    if sys.version_info[:2] < (2, 5):
        src += """
    sys = __import__("sys")
    os = __import__("os")
    imp = __import__("imp")
"""
    else:
        src += """
    sys = __import__("sys", level=0)
    os = __import__("os", level=0)
    imp = __import__("imp", level=0)
"""

    src += """
    found = False
    for p in sys.path:
        if not os.path.isdir(p):
            continue
        f = os.path.join(p, "%s")
        if not os.path.exists(f):
            continue
        sys.modules[__name__] = imp.load_dynamic(__name__, f)
        found = True
        break
    if not found:
        try:
            raise ImportError, "No module named %%s" %% __name__
        finally:
            del sys.modules[__name__]

_bbfreeze_import_dynamic_module()
""" % modname

    return src



def get_implies():
    implies = {
        "wxPython.wx": modulegraph.Alias('wx'),
        }

    try:
        from email import _LOWERNAMES, _MIMENAMES
    except ImportError:
        return implies

    for x in _LOWERNAMES:
        implies['email.' + x] = modulegraph.Alias('email.' + x.lower())
    for x in _MIMENAMES:
        implies['email.MIME' + x] = modulegraph.Alias('email.mime.' + x.lower())

    return implies


class Freezer(object):
    use_compression = True
    include_py = True
    implies = get_implies()

    def __init__(self, distdir="dist", includes=(), excludes=()):
        self.distdir = os.path.abspath(distdir)
        self._recipes = None
        self.icon = None

        self.mf = MyModuleGraph(excludes=excludes, implies=self.implies, debug=0)

        # workaround for virtualenv's distutils monkeypatching
        import distutils
        self.mf.load_package("distutils", distutils.__path__[0])

        self._loaderNode = None
        if sys.platform == 'win32':
            self.linkmethod = 'loader'
        else:
            self.linkmethod = 'hardlink'

        self.console = fullname("console.exe")
        if sys.platform == 'win32':
            self.consolew = fullname("consolew.exe")

        self._have_console = False
        self.binaries = []

        for x in includes:
            self.addModule(x)

    def _get_mtime(self, fn):
        if fn and os.path.exists(fn):
            mtime = os.stat(fn).st_mtime
        else:
            mtime = time.time()
        return mtime

    def _entry_script(self, path):
        f = open(path, 'r')
        lines = [f.readline(), f.readline()]
        del f
        eicomment = "# EASY-INSTALL-ENTRY-SCRIPT: "
        for line in lines:
            if line.startswith(eicomment):
                values = [x.strip("'\"") for x in line[len(eicomment):].strip().split(",")]
                print path, "is an easy install entry script. running pkg_resources.require(%r)" % (values[0],)
                pkg_resources.require(values[0])
                ep = pkg_resources.get_entry_info(*values)
                print "entry point is", ep
                return ep.module_name
        return None

    def addEntryPoint(self, name, importspec):
        modname, attr = importspec.split(":")
        m = self.mf.createNode(modulegraph.Script, name)
        m.code = compile("""
if __name__ == '__main__':
    import sys, %s
    sys.exit(%s.%s())
""" % (modname, modname, attr), name, "exec")
        self.mf.createReference(None, m)
        self.mf.scan_code(m.code, m)
        return m

    def addScript(self, path, gui_only=False):
        dp = os.path.dirname(os.path.abspath(path))
        self.mf.path.insert(0, dp)
        ep_module_name = self._entry_script(path)
        s = self.mf.run_script(path)
        s.gui_only = gui_only
        del self.mf.path[0]
        if ep_module_name:
            self.mf.import_hook(ep_module_name, s)

    def addModule(self, name):
        if name.endswith(".*"):
            self.mf.import_hook(name[:-2], fromlist="*")
        else:
            if name not in sys.builtin_module_names:
                self.mf.import_hook(name)

    
    def setIcon(self, filename):
        self.icon = filename

    def _add_loader(self):
        if self._loaderNode is not None:
            return
        loader = os.path.join(os.path.dirname(__file__), "load_console.py")
        assert os.path.exists(loader)

        m = self.mf.run_script(loader)
        self._loaderNode = m

    def _handleRecipes(self):
        if self._recipes is None:
            self._recipes = getRecipes()

        numApplied = 0
        for x in self._recipes:
            if x(self.mf):
                print "*** applied", x
                self._recipes.remove(x)
                numApplied += 1
        return numApplied

    def _handle_CopyTree(self, n):
        shutil.copytree(n.filename, os.path.join(self.distdir, n.dest))

    def addExecutable(self, exe):
        from bbfreeze import getdeps
        e = self.mf.createNode(Executable, os.path.basename(exe))
        e.filename = exe
        self.mf.createReference(self.mf, e)

        for so in getdeps.getDependencies(exe):
            n = self.mf.createNode(SharedLibrary, os.path.basename(so))
            n.filename = so
            self.mf.createReference(e, n)

    def findBinaryDependencies(self):
        from bbfreeze import getdeps
        assert os.access(self.console, os.X_OK), "%r is not executable" % (self.console,)

        for so in getdeps.getDependencies(self.console):
            n = self.mf.createNode(SharedLibrary, os.path.basename(so))
            n.filename = so
            self.mf.createReference(self.mf, n)

        for x in list(self.mf.flatten()):
            if isinstance(x, modulegraph.Extension):
                for so in getdeps.getDependencies(x.filename):
                    n = self.mf.createNode(SharedLibrary, os.path.basename(so))
                    n.filename = so
                    self.mf.createReference(x, n)

    def _getRPath(self, exe):
        os.environ["S"] = exe

        status, out = commands.getstatusoutput("patchelf --version")

        if status == 0:
            status, out = commands.getstatusoutput("patchelf --print-rpath $S")
            if status:
                raise RuntimeError("patchelf failed: %r" % out)
            return out.strip() or None

        status, out = commands.getstatusoutput("objdump -x $S")
        if status:
            print "WARNING: objdump failed: could not determine RPATH by running 'objdump -x %s'" % exe
            return None

        tmp = re.findall("[ \t]+RPATH[ \t]*(.*)", out)
        if len(tmp) == 1:
            return tmp[0].strip()

        if len(tmp) > 1:
            raise RuntimeError("Could not determine RPATH from objdump output: %r" % out)

        return ""

    def _setRPath(self, exe, rpath):
        os.environ["S"] = exe
        os.environ["R"] = rpath
        print "running 'patchelf --set-rpath '%s' %s'" % (rpath, exe)
        status, out = commands.getstatusoutput("patchelf --set-rpath $R $S")
        if status != 0:
            print "WARNING: failed to set RPATH for %s: %s" % (exe, out)

    def ensureRPath(self, exe):
        if sys.platform not in ("linux2", "linux3", "sunos5"):
            return

        expected_rpath = "${ORIGIN}:${ORIGIN}/../lib"
        if sys.platform == "sunos5":
            # RPATH shouldn't have the squiggly braces on sunos
            expected_rpath = "$ORIGIN:$ORIGIN/../lib"
        current_rpath = self._getRPath(exe)
        if current_rpath is None:
            return

        if current_rpath == expected_rpath:
            # print "RPATH %s of %s is fine" % (current_rpath, exe)
            return

        print "RPATH %r of %s needs adjustment. make sure you have the patchelf executable installed." % (current_rpath, exe)
        self._setRPath(exe, expected_rpath)

    def __call__(self):
        if self.include_py:
            pyscript = os.path.join(os.path.dirname(__file__), 'py.py')
            s = self.mf.run_script(pyscript)
            s.gui_only = False

        self.addModule("encodings.*")
        self._add_loader()

        if os.path.exists(self.distdir):
            shutil.rmtree(self.distdir)
        os.makedirs(self.distdir)

        # work around easy_install which doesn't preserve the
        # executable bit
        xconsole = os.path.join(self.distdir, "bbfreeze-console.exe")
        shutil.copy2(self.console, xconsole)
        os.chmod(xconsole, 0755)
        self.console = xconsole

        while 1:
            self.findBinaryDependencies()
            if not self._handleRecipes():
                break

        zipfilepath = os.path.join(self.distdir, "library.zip")
        self.zipfilepath = zipfilepath
        if self.linkmethod == 'loader' and sys.platform == 'win32':
            pass  # open(library, 'w')
        else:
            shutil.copy(self.console, zipfilepath)
            self.ensureRPath(zipfilepath)

        if os.path.exists(zipfilepath):
            mode = 'a'
        else:
            mode = 'w'

        self.outfile = zipfile.PyZipFile(zipfilepath, mode, zipfile.ZIP_DEFLATED)

        mods = [(x.identifier, x) for x in self.mf.flatten()]
        mods.sort()
        mods = [x[1] for x in mods]

        analyzer = EggAnalyzer()

        use_mods = []
        for x in mods:
            if x is self._loaderNode:
                use_mods.append(x)
                continue

            dist = analyzer.findDistribution(x)
            if not dist:
                use_mods.append(x)

        analyzer.report()
        analyzer.copy(self.distdir)

        for x in use_mods:
            try:
                m = getattr(self, "_handle_" + x.__class__.__name__)
            except AttributeError:
                print "WARNING: dont know how to handle", x
                continue
            m(x)

        self.outfile.close()

        if xconsole:
            os.unlink(xconsole)

        self.finish_dist()

        if os.environ.get("XREF") or os.environ.get("xref"):
            self.showxref()

    def finish_dist(self):
        if sys.platform != 'darwin':
            return

        from macholib.MachOStandalone import MachOStandalone
        d = os.path.join(os.path.abspath(self.distdir), "")
        m = MachOStandalone(d, d)
        m.run(contents="@executable_path/")

    def _handle_ExcludedModule(self, m):
        pass

    def _handle_MissingModule(self, m):
        pass

    def _handle_BuiltinModule(self, m):
        pass

    def _handle_AliasNode(self, m):
        pass

    def _handle_NamespaceModule(self, m):
        fn = "%s/__init__.py" % (m.identifier.replace(".", "/"),)
        code = compile("", fn, "exec")
        self._writecode(fn + "c", time.time(), code)

    def _handle_Extension(self, m):
        name = m.identifier

        basefilename = os.path.basename(m.filename)
        base, ext = os.path.splitext(basefilename)
        # fedora has zlibmodule.so, timemodule.so,...
        if base not in [name, name + "module"]:
            code = compile(make_extension_loader(name + ext),
                           "ExtensionLoader.py", "exec")
            fn = name.replace(".", "/") + ".pyc"
            self._writecode(fn, time.time(), code)

        dst = os.path.join(self.distdir, name + ext)
        shutil.copy2(m.filename, dst)
        os.chmod(dst, 0755)
        # when searching for DLL's the location matters, so don't
        # add the destination file, but rather the source file
        self.binaries.append(m.filename)
        self.adaptBinary(dst)

    def _handle_Package(self, m):
        fn = m.identifier.replace(".", "/") + "/__init__.pyc"
        mtime = self._get_mtime(m.filename)
        self._writecode(fn, mtime, m.code)

    def _handle_SourceModule(self, m):
        fn = m.identifier.replace(".", "/") + '.pyc'
        mtime = self._get_mtime(m.filename)
        self._writecode(fn, mtime, m.code)

    def _handle_ZipModule(self, m):
        fn = m.identifier.replace(".", "/")
        if m.is_package:
            fn += "/__init__"
        fn += ".pyc"
        mtime = self._get_mtime(m.filename)

        self._writecode(fn, mtime, m.code)

    def _handle_CompiledModule(self, m):
        fn = m.identifier.replace(".", "/") + '.pyc'
        print "WARNING: using .pyc file %r for which no source file could be found." % (fn,)
        mtime = self._get_mtime(m.filename)
        self._writecode(fn, mtime, m.code)

    def _handle_Script(self, m):
        exename = None
        mtime = self._get_mtime(m.filename)
        if m is self._loaderNode:
            fn = "__main__.pyc"
        else:
            fn = os.path.basename(m.filename)
            if fn.endswith(".py"):
                fn = fn[:-3]
            elif fn.endswith(".pyw"):
                fn = fn[:-4]

            exename = fn
            fn = '__main__%s__.pyc' % fn.replace(".", "_")

        self._writecode(fn, mtime, m.code)
        if exename:
            if sys.platform == 'win32':
                exename += '.exe'
            gui_only = getattr(m, 'gui_only', False)

            self.link(self.zipfilepath, os.path.join(self.distdir, exename), gui_only=gui_only)

    def _writecode(self, fn, mtime, code):
        code = replace_paths_in_code(code, fn)
        ziptime = time.localtime(mtime)[:6]
        data = imp.get_magic() + struct.pack("<i", mtime) + marshal.dumps(code)
        zinfo = zipfile.ZipInfo(fn, ziptime)
        if self.use_compression:
            zinfo.compress_type = zipfile.ZIP_DEFLATED
        self.outfile.writestr(zinfo, data)

    def link(self, src, dst, gui_only):
        if not self._have_console:
            self.binaries.append(dst)
            self._have_console = True

        if os.path.exists(dst) or os.path.islink(dst):
            os.unlink(dst)

        lm = self.linkmethod
        if lm == 'symlink':
            assert os.path.dirname(src) == os.path.dirname(dst)
            os.symlink(os.path.basename(src), dst)
            os.chmod(dst, 0755)
        elif lm == 'hardlink':
            os.link(src, dst)
            os.chmod(dst, 0755)
        elif lm == 'loader':
            if gui_only and sys.platform == 'win32':
                shutil.copy2(self.consolew, dst)
            else:
                shutil.copy2(self.console, dst)
            os.chmod(dst, 0755)
            
            if self.icon and sys.platform == 'win32':
                try:
                    from bbfreeze import winexeutil
                    # Set executable icon
                    winexeutil.set_icon(dst, self.icon)
                except ImportError, e:
                    raise RuntimeError("Cannot add icon to executable. Error: %s" % (e.message))
        else:
            raise RuntimeError("linkmethod %r not supported" % (self.linkmethod,))

    def adaptBinary(self, p):
        self.stripBinary(p)
        self.ensureRPath(p)

    def stripBinary(self, p):
        if sys.platform == 'win32' or sys.platform == 'darwin':
            return
        os.environ['S'] = p
        os.system('strip $S')

    def _handle_Executable(self, m):
        dst = os.path.join(self.distdir, os.path.basename(m.filename))
        shutil.copy2(m.filename, dst)
        os.chmod(dst, 0755)
        self.adaptBinary(dst)

    def _handle_SharedLibrary(self, m):
        dst = os.path.join(self.distdir, os.path.basename(m.filename))
        shutil.copy2(m.filename, dst)
        os.chmod(dst, 0755)
        self.adaptBinary(dst)

    def showxref(self):
        import tempfile

        fd, htmlfile = tempfile.mkstemp(".html")
        ofi = open(htmlfile, "w")
        os.close(fd)

        self.mf.create_xref(ofi)
        ofi.close()

        import webbrowser
        try:
            webbrowser.open("file://" + htmlfile)
        except webbrowser.Error:
            # sometimes there is no browser (e.g. in chroot environments)
            pass
        # how long does it take to start the browser?
        import threading
        threading.Timer(5, os.remove, args=[htmlfile])

########NEW FILE########
__FILENAME__ = getdeps
#! /usr/bin/env python

import sys, os, re, commands

if sys.platform == 'win32':

    # -----------------------
    ## http://mail.python.org/pipermail/python-win32/2005-June/003446.html:
    ##
    ## Using it I found this: win32net.pyd from build 204 does *not* use the
    ## LsaLookupNames2 function in advapi32.dll.  However, win32net.pyd links
    ## to netapi32.dll (among others), and netapi32.dll links to advapi32.dll,
    ## using the name LsaLookupNames2.  This was on WinXP.

    ## On win2k, netapi32.dll will not link to advapi32's LsaLookupNames2 -
    ## otherwise it would not work.

    ## So, your exe *should* be able to run on win2k - except if you distribute
    ## XP's netapi32.dll with your exe (I've checked this with a trivial
    ## py2exe'd script).
    #
    # ----> EXCLUDE NETAPI32.DLL

    #-----------------------------------------
    # as found on the internet:
    # shlwapi.dll is installed as a tied component of Internet Explorer, and
    # the version should always match that of the installed version of Internet Explorer
    # so better exclude it
    #
    # ----> EXCLUDE SHLWAPI.DLL

    excludes = set(
        ['ADVAPI.DLL',
         'ADVAPI32.DLL',
         'COMCTL32.DLL',
         'COMDLG32.DLL',
         'CRTDLL.DLL',
         'CRYPT32.DLL',
         'DCIMAN32.DLL',
         'DDRAW.DLL',
         'GDI32.DLL',
         'GLU32.DLL',
         'GLUB32.DLL',
         'IMM32.DLL',
         'KERNEL32.DLL',
         'MFC42.DLL',
         'MSVCRT.DLL',
         'MSWSOCK.DLL',
         'NTDLL.DLL',
         'NETAPI32.DLL',
         'ODBC32.DLL',
         'OLE32.DLL',
         'OLEAUT32.DLL',
         'OPENGL32.DLL',
         'RPCRT4.DLL',
         'SHELL32.DLL',
         'SHLWAPI.DLL',
         'USER32.DLL',
         'VERSION.DLL',
         'WINMM.DLL',
         'WINSPOOL.DRV',
         'WS2HELP.DLL',
         'WS2_32.DLL',
         'WSOCK32.DLL',
         'MSVCR90.DLL',
         'POWRPROF.DLL',
         'SHFOLDER.DLL',
         'QUERY.DLL',
         ])

    def getImports(path):
        """Find the binary dependencies of PTH.

            This implementation walks through the PE header"""
        import pefile
        try:
            pe = pefile.PE(path, True)
            dlls = [x.dll for x in pe.DIRECTORY_ENTRY_IMPORT]
        except Exception, err:
            print "WARNING: could not determine binary dependencies for %r:%s" % (path, err)
            dlls = []
        return dlls

    _bpath = None

    def getWindowsPath():
        """Return the path that Windows will search for dlls."""
        global _bpath
        if _bpath is None:
            _bpath = [os.path.dirname(sys.executable)]
            if sys.platform == 'win32':

                try:
                    import win32api
                except ImportError:

                    print "Warning: Cannot determine your Windows or System directories because pywin32 is not installed."
                    print "Warning: Either install it from http://sourceforge.net/projects/pywin32/ or"
                    print "Warning: add them to your PATH if .dlls are not found."
                else:
                    sysdir = win32api.GetSystemDirectory()
                    sysdir2 = os.path.join(sysdir, '../SYSTEM')
                    windir = win32api.GetWindowsDirectory()
                    _bpath.extend([sysdir, sysdir2, windir])
            _bpath.extend(os.environ.get('PATH', '').split(os.pathsep))
        return _bpath

    def _getDependencies(path):
        """Return a set of direct dependencies of executable given in path"""

        dlls = getImports(path)
        winpath = [os.path.dirname(os.path.abspath(path))] + getWindowsPath()
        deps = set()
        for dll in dlls:
            if exclude(dll):
                continue

            for x in winpath:
                fp = os.path.join(x, dll)
                if os.path.exists(fp):
                    deps.add(fp)
                    break
            else:
                print "WARNING: could not find dll %r needed by %r in %r" % (dll, path, winpath)
        return deps

    def exclude(fp):
        u = os.path.basename(fp).upper()
        return  u in excludes or u.startswith("API-MS-WIN-")

elif sys.platform.startswith("freebsd"):

    def _getDependencies(path):
        os.environ["P"] = path
        s = commands.getoutput("ldd $P")
        res = [x for x in re.compile(r"^ *.* => (.*) \(.*", re.MULTILINE).findall(s) if x]
        return res

    def exclude(fp):
        return bool(re.match(r"^/usr/lib/.*$", fp))

elif sys.platform.startswith("sunos5"):

    def _getDependencies(path):
        os.environ["P"] = path
        s = commands.getoutput("ldd $P")
        res = [x for x in re.compile(r"^\t* *.*=>\t* (.*)", re.MULTILINE).findall(s) if x]
        return res

    def exclude(fp):
        return bool(re.match(r"^/lib/.*$|^/usr/lib/.*$", fp))

elif sys.platform.startswith("linux"):

    def _getDependencies(path):
        os.environ["P"] = path
        s = commands.getoutput("ldd $P")
        res = [x for x in re.compile(r"^ *.* => (.*) \(.*", re.MULTILINE).findall(s) if x]
        return res

    def exclude(fp):
        return re.match(r"^libc\.|^librt\.|^libcrypt\.|^libm\.|^libdl\.|^libpthread\.|^libnsl\.|^libutil\.|^libresolv\.|^ld-linux\.|^ld-linux-", os.path.basename(fp))
else:
    if sys.platform != 'darwin':
        print "Warning: don't know how to handle binary dependencies on this platform (%s)" % (sys.platform,)

    def _getDependencies(fp):
        return []

    def exclude(fp):
        return False

_cache = {}


def getDependencies(path):
    """Get direct and indirect dependencies of executable given in path"""
    def normedDeps(p):
        try:
            return _cache[p]
        except KeyError:
            r = set(os.path.normpath(x) for x in _getDependencies(p) if not exclude(x))
            _cache[p] = r
            return r

    if not isinstance(path, basestring):
        deps = set()
        for p in path:
            deps.update(getDependencies(p))
        return list(deps)

    deps = normedDeps(path)
    while True:
        newdeps = set(deps)  # copy
        for d in deps:
            newdeps.update(normedDeps(d))
        if deps == newdeps:
            return list(deps)
        deps = newdeps


def main():
    deps = set()
    deps = getDependencies(sys.argv[1:])
    deps = list(deps)
    deps.sort()
    print "\n".join(deps)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = load_console
#! /usr/bin/env python

import sys, os, zlib, zipimport

installdir = os.path.normpath(os.path.dirname(sys.path[0]))  # sys.path[0] == '.../library.zip'


def find_eggs():
    for x in os.listdir(installdir):
        if x.endswith(".egg"):
            fp = os.path.join(installdir, x)
            sys.path.append(fp)

find_eggs()


def addldlibrarypath():

    if sys.platform == 'darwin':
        LD_LIBRARY_PATH = 'DYLD_LIBRARY_PATH'
    else:
        LD_LIBRARY_PATH = 'LD_LIBRARY_PATH'

    #p = os.path.normpath(os.path.dirname(sys.executable))
    p = installdir
    try:
        paths = os.environ[LD_LIBRARY_PATH].split(os.pathsep)
    except KeyError:
        paths = []

    if p not in paths:
        paths.insert(0, p)
        os.environ[LD_LIBRARY_PATH] = os.pathsep.join(paths)
        #print "SETTING", LD_LIBRARY_PATH, os.environ[LD_LIBRARY_PATH]
        os.execv(sys.executable, sys.argv)


def addpath():
    # p = os.path.normpath(os.path.dirname(sys.executable))
    p = installdir
    try:
        paths = os.environ['PATH'].split(os.pathsep)
    except KeyError:
        paths = []

    if p not in paths:
        paths.insert(0, p)
        os.environ['PATH'] = os.pathsep.join(paths)
        #print "SETTING PATH:", os.environ['PATH']


def addtcltk():
    libtk = os.path.join(installdir, "lib-tk")
    libtcl = os.path.join(installdir, "lib-tcl")

    if os.path.isdir(libtk):
        os.environ['TK_LIBRARY'] = libtk

    if os.path.isdir(libtcl):
        os.environ['TCL_LIBRARY'] = libtcl


def fixwin32com():
    """setup win32com to 'genpy' in a tmp directory
    """
    if sys.platform != 'win32':
        return

    # hide imports by using exec. bbfreeze analyzes this file.
    exec """
try:
    import win32com.client
    import win32com.gen_py
    import win32api
except ImportError:
    pass
else:
    win32com.client.gencache.is_readonly=False
    tmpdir = os.path.join(win32api.GetTempPath(),
                          "frozen-genpy-%s%s" % sys.version_info[:2])
    if not os.path.isdir(tmpdir):
        os.makedirs(tmpdir)
    win32com.__gen_path__ = tmpdir
    win32com.gen_py.__path__=[tmpdir]
"""

#print "EXE:", sys.executable
#print "SYS.PATH:", sys.path

addpath()
#if sys.platform!='win32': # and hasattr(os, 'execv'):
#    addldlibrarypath()

addtcltk()

try:
    import encodings
except ImportError:
    pass

fixwin32com()

exe = os.path.basename(sys.argv[0])
if exe.lower().endswith(".exe"):
    exe = exe[:-4]


m = __import__("__main__")

# add '.py' suffix to prevent garbage from the warnings module
m.__dict__['__file__'] = exe + '.py'
exe = exe.replace(".", "_")
importer = zipimport.zipimporter(sys.path[0])
while 1:
    # if exe is a-b-c, try loading a-b-c, a-b and a
    try:
        code = importer.get_code("__main__%s__" % exe)
    except zipimport.ZipImportError, err:
        if '-' in exe:
            exe = exe[:exe.find('-')]
        else:
            raise err
    else:
        break
if exe == "py":
    exec code
else:
    exec code in m.__dict__

########NEW FILE########
__FILENAME__ = find_modules
"""
High-level module dependency finding interface

See find_modules(...)

Originally (loosely) based on code in py2exe's build_exe.py by Thomas Heller.
"""

import sys
import os
import imp
import warnings
try:
    set
except NameError:
    from sets import Set as set

#from modulegraph import modulegraph
#from modulegraph.modulegraph import Alias
#from modulegraph.util import imp_find_module
import modulegraph
from modulegraph import Alias
from util import imp_find_module

__all__ = [
    'find_modules', 'parse_mf_results'
]

def get_implies():
    return {
        # imports done from builtin modules in C code (untrackable by modulegraph)
        "time":         ["_strptime"],
        "datetime":     ["time"],
        "MacOS":        ["macresource"],
        "cPickle":      ["copy_reg", "cStringIO"],
        "parser":       ["copy_reg"],
        "codecs":       ["encodings"],
        "cStringIO":    ["copy_reg"],
        "_sre":         ["copy", "string", "sre"],
        "zipimport":    ["zlib"],
        # mactoolboxglue can do a bunch more of these
        # that are far harder to predict, these should be tracked
        # manually for now.

        # this isn't C, but it uses __import__
        "anydbm":       ["dbhash", "gdbm", "dbm", "dumbdbm", "whichdb"],
        # package aliases
        "wxPython.wx":  Alias('wx'),
    }

def parse_mf_results(mf):
    #for name, imports in get_hidden_imports().items():
    #    if name in mf.modules.keys():
    #        for mod in imports:
    #            mf.import_hook(mod)

    # Retrieve modules from modulegraph
    py_files = []
    extensions = []

    for item in mf.flatten():
        # There may be __main__ modules (from mf.run_script), but
        # we don't need it in the zipfile we build.
        if item.identifier == "__main__":
            continue
        src = item.filename
        if src:
            suffix = os.path.splitext(src)[1]

            if suffix in PY_SUFFIXES:
                py_files.append(item)
            elif suffix in C_SUFFIXES:
                extensions.append(item)
            else:
                raise RuntimeError("Don't know how to handle '%s'" % repr(src))

    # sort on the file names, the output is nicer to read
    py_files.sort(lambda a,b:cmp(a.filename, b.filename))
    extensions.sort(lambda a,b:cmp(a.filename, b.filename))
    return py_files, extensions


def plat_prepare(includes, packages, excludes):
    # used by Python itself
    includes.update(["warnings", "unicodedata", "weakref"])

    if not sys.platform.startswith('irix'):
        excludes.update([
            'AL',
            'sgi',
        ])

    if not sys.platform in ('mac', 'darwin'):
        # XXX - this doesn't look nearly complete
        excludes.update([
            'Audio_mac',
            'Carbon.File',
            'Carbon.Folder',
            'Carbon.Folders',
            'EasyDialogs',
            'MacOS',
            'macfs',
            'macostools',
            'macpath',
        ])

    if not sys.platform == 'mac':
        excludes.update([
            'mkcwproject',
        ])

    if not sys.platform == 'win32':
        # only win32
        excludes.update([
            'ntpath',
            'nturl2path',
            'win32api',
            'win32con',
            'win32event',
            'win32evtlogutil',
            'win32evtlog',
            'win32file',
            'win32gui',
            'win32pipe',
            'win32process',
            'win32security',
            'pywintypes',
            'winsound',
            'win32',
            '_winreg',
         ])

    if not sys.platform == 'riscos':
        excludes.update([
             'riscosenviron',
             'riscospath',
             'rourl2path',
          ])

    if not sys.platform == 'dos' or sys.platform.startswith('ms-dos'):
        excludes.update([
            'dos',
        ])

    if not sys.platform == 'os2emx':
        excludes.update([
            'os2emxpath'
        ])

    excludes.update(set(['posix', 'nt', 'os2', 'mac', 'ce', 'riscos']) - set(sys.builtin_module_names))

    try:
        imp_find_module('poll')
    except ImportError:
        excludes.update([
            'poll',
        ])

def find_needed_modules(mf=None, scripts=(), includes=(), packages=(), warn=warnings.warn):
    if mf is None:
        mf = modulegraph.ModuleGraph()
    # feed Modulefinder with everything, and return it.

    for path in scripts:
        mf.run_script(path)

    for mod in includes:
        if mod[-2:] == '.*':
            mf.import_hook(mod[:-2], None, ['*'])
        else:
            mf.import_hook(mod)

    for f in packages:
        # If modulegraph has seen a reference to the package, then
        # we prefer to believe that (imp_find_module doesn't seem to locate
        # sub-packages)
        m = mf.findNode(f)
        if m is not None:
            path = m.packagepath[0]
        else:
            # Find path of package
            try:
                path = imp_find_module(f)[1]
            except ImportError:
                warn("No package named %s" % f)
                continue

        # walk the path to find subdirs containing __init__.py files
        # scan the results (directory of __init__.py files)
        # first trim the path (of the head package),
        # then convert directory name in package name,
        # finally push into modulegraph.
        for (dirpath, dirnames, filenames) in os.walk(path):
            if '__init__.py' in filenames and dirpath.startswith(path):
                package = f + '.' + path[len(path)+1:].replace(os.sep, '.')
                mf.import_hook(package, None, ["*"])

    return mf

#
# resource constants
#
PY_SUFFIXES = ['.py', '.pyw', '.pyo', '.pyc']
C_SUFFIXES = [
    _triple[0] for _triple in imp.get_suffixes()
    if _triple[2] == imp.C_EXTENSION
]

#
# side-effects
#

def _replacePackages():
    REPLACEPACKAGES = {
        '_xmlplus':     'xml',
    }
    for k,v in REPLACEPACKAGES.iteritems():
        modulegraph.ReplacePackage(k, v)

_replacePackages()

def find_modules(scripts=(), includes=(), packages=(), excludes=(), path=None, debug=0):
    """
    High-level interface, takes iterables for:
        scripts, includes, packages, excludes

    And returns a ModuleGraph instance, python_files, and extensions

    python_files is a list of pure python dependencies as modulegraph.Module objects,
    extensions is a list of platform-specific C extension dependencies as modulegraph.Module objects
    """
    scripts = set(scripts)
    includes = set(includes)
    packages = set(packages)
    excludes = set(excludes)
    plat_prepare(includes, packages, excludes)
    mf = modulegraph.ModuleGraph(
        path=path,
        excludes=(excludes - includes),
        implies=get_implies(),
        debug=debug,
    )
    find_needed_modules(mf, scripts, includes, packages)
    return mf

def test():
    if '-g' in sys.argv[1:]:
        sys.argv.remove('-g')
        dograph = True
    else:
        dograph = False
    if '-x' in sys.argv[1:]:
        sys.argv.remove('-x')
        doxref = True
    else:
        doxref= False

    scripts = sys.argv[1:] or [__file__]
    mf = find_modules(scripts=scripts)
    if doxref:
        mf.create_xref()
    elif dograph:
        mf.graphreport()
    else:
        mf.report()

if __name__ == '__main__':
    test()

########NEW FILE########
__FILENAME__ = modulegraph
"""
Find modules used by a script, using bytecode analysis.

Based on the stdlib modulefinder by Thomas Heller and Just van Rossum,
but uses a graph data structure and 2.3 features
"""

from pkg_resources import require
require("altgraph")

import dis
import imp
import marshal
import os
import sys
import new
import struct
import urllib
from itertools import ifilter, imap

from altgraph.Dot import Dot
from altgraph.ObjectGraph import ObjectGraph
from altgraph.GraphUtil import filter_stack
from altgraph.compat import *

READ_MODE = "U"  # universal line endings

LOAD_CONST = chr(dis.opname.index('LOAD_CONST'))
IMPORT_NAME = chr(dis.opname.index('IMPORT_NAME'))
STORE_NAME = chr(dis.opname.index('STORE_NAME'))
STORE_GLOBAL = chr(dis.opname.index('STORE_GLOBAL'))
STORE_OPS = [STORE_NAME, STORE_GLOBAL]
HAVE_ARGUMENT = chr(dis.HAVE_ARGUMENT)

# Modulegraph does a good job at simulating Python's, but it can not
# handle packagepath modifications packages make at runtime.  Therefore there
# is a mechanism whereby you can register extra paths in this map for a
# package, and it will be honored.

# Note this is a mapping is lists of paths.
packagePathMap = {}

def moduleInfoForPath(path, suffixes=imp.get_suffixes()):
    for (ext, readmode, typ) in imp.get_suffixes():
        if path.endswith(ext):
            return os.path.basename(path)[:-len(ext)], readmode, typ
    return None

# A Public interface
def AddPackagePath(packagename, path):
    paths = packagePathMap.get(packagename, [])
    paths.append(path)
    packagePathMap[packagename] = paths

replacePackageMap = {}

# This ReplacePackage mechanism allows modulefinder to work around the
# way the _xmlplus package injects itself under the name "xml" into
# sys.modules at runtime by calling ReplacePackage("_xmlplus", "xml")
# before running ModuleGraph.

def ReplacePackage(oldname, newname):
    replacePackageMap[oldname] = newname

class Node(object):
    def __init__(self, identifier):
        self.graphident = identifier
        self.identifier = identifier
        self.namespace = {}
        self.filename = None
        self.packagepath = None
        self.code = None
        # The set of global names that are assigned to in the module.
        # This includes those names imported through starimports of
        # Python modules.
        self.globalnames = set()
        # The set of starimports this module did that could not be
        # resolved, ie. a starimport from a non-Python module.
        self.starimports = set()

    def __contains__(self, name):
        return name in self.namespace

    def __getitem__(self, name):
        return self.namespace[name]

    def __setitem__(self, name, value):
        self.namespace[name] = value

    def get(self, *args):
        return self.namespace.get(*args)

    def __cmp__(self, other):
        return cmp(self.graphident, other.graphident)

    def __hash__(self):
        return hash(self.graphident)

    def infoTuple(self):
        return (self.identifier,)

    def __repr__(self):
        return '%s%r' % (type(self).__name__, self.infoTuple())

class Alias(str):
    pass

class AliasNode(Node):
    def __init__(self, name, node):
        super(AliasNode, self).__init__(name)
        for k in ['identifier', 'packagepath', 'namespace', 'globalnames', 'startimports']:
            setattr(self, k, getattr(node, k, None))

    def infoTuple(self):
        return (self.graphident, self.identifier)

class BadModule(Node):
    pass

class ExcludedModule(BadModule):
    pass

class MissingModule(BadModule):
    pass

class Script(Node):
    def __init__(self, filename):
        super(Script, self).__init__(filename)
        self.filename = filename

    def infoTuple(self):
        return (self.filename,)

class BaseModule(Node):
    def __init__(self, name, filename=None, path=None):
        super(BaseModule, self).__init__(name)
        self.filename = filename
        self.packagepath = path

    def infoTuple(self):
        return tuple(filter(None, (self.identifier, self.filename, self.packagepath)))

class BuiltinModule(BaseModule):
    pass

class SourceModule(BaseModule):
    pass

class CompiledModule(BaseModule):
    pass

class Package(BaseModule):
    pass

class FlatPackage(BaseModule):
    pass

class Extension(BaseModule):
    pass

class NamespaceModule(BaseModule):
    pass

class ModuleGraph(ObjectGraph):
    def __init__(self, path=None, excludes=(), replace_paths=(), implies=(), graph=None, debug=0):
        super(ModuleGraph, self).__init__(graph=graph, debug=debug)
        if path is None:
            path = sys.path
        self.path = path
        self.lazynodes = {}
        # excludes is stronger than implies
        self.lazynodes.update(dict(implies))
        for m in excludes:
            self.lazynodes[m] = None
        self.replace_paths = replace_paths

    def implyNodeReference(self, node, other):
        """
        Imply that one node depends on another.
        other may be a module name or another node.

        For use by extension modules and tricky import code
        """
        if not isinstance(other, Node):
            if not isinstance(other, tuple):
                other = (other, node)
            others = self.import_hook(*other)
            for other in others:
                self.createReference(node, other)
        elif isinstance(other, AliasNode):
            self.addNode(other)
            other.connectTo(node)
        else:
            self.createReference(node, other)


    def createReference(self, fromnode, tonode, edge_data='direct'):
        return super(ModuleGraph, self).createReference(fromnode, tonode, edge_data=edge_data)

    def findNode(self, name):
        """
        Find a node by identifier.  If a node by that identifier exists,
        it will be returned.

        If a lazy node exists by that identifier with no dependencies (excluded),
        it will be instantiated and returned.

        If a lazy node exists by that identifier with dependencies, it and its
        dependencies will be instantiated and scanned for additional dependencies.
        """
        data = super(ModuleGraph, self).findNode(name)
        if data is not None:
            return data
        if name in self.lazynodes:
            deps = self.lazynodes.pop(name)
            if deps is None:
                # excluded module
                m = self.createNode(ExcludedModule, name)
            elif isinstance(deps, Alias):
                other = self._safe_import_hook(deps, None, None).pop()
                m = self.createNode(AliasNode, name, other)
                self.implyNodeReference(m, other)
            else:
                m = self._safe_import_hook(name, None, None).pop()
                for dep in deps:
                    self.implyNodeReference(m, dep)
            return m
        return None

    def run_script(self, pathname, caller=None):
        """
        Create a node by path (not module name).  It is expected to be a Python
        source file, and will be scanned for dependencies.
        """
        self.msg(2, "run_script", pathname)
        pathname = os.path.realpath(pathname)
        m = self.findNode(pathname)
        if m is not None:
            return m

        co = compile(file(pathname, READ_MODE).read()+'\n', pathname, 'exec')
        if self.replace_paths:
            co = self.replace_paths_in_code(co)
        m = self.createNode(Script, pathname)
        m.code = co
        self.createReference(caller, m)
        self.scan_code(co, m)
        return m

    def import_hook(self, name, caller=None, fromlist=None, level=-1):
        """
        Import a module
        """
        self.msg(3, "import_hook", name, caller, fromlist)
        parent = self.determine_parent(caller, level=level)
        q, tail = self.find_head_package(parent, name)
        m = self.load_tail(q, tail)
        modules = set([m])
        if fromlist and m.packagepath:
            modules.update(self.ensure_fromlist(m, fromlist))
        for m in modules:
            self.createReference(caller, m)
        return modules

    def determine_parent(self, caller, level=-1):
        self.msgin(4, "determine_parent", caller, level)
        if not caller or level == 0:
            self.msgout(4, "determine_parent -> None")
            return None
        pname = caller.identifier
        if level >= 1: # relative import
            if caller.packagepath:
                level -= 1
            if level == 0:
                parent = self.findNode(pname)
                assert parent is caller
                self.msgout(4, "determine_parent ->", parent)
                return parent
            if pname.count(".") < level:
                raise ImportError, "relative importpath too deep"
            pname = ".".join(pname.split(".")[:-level])
            parent = self.findNode(pname)
            self.msgout(4, "determine_parent ->", parent)
            return parent
        if caller.packagepath:
            parent = self.findNode(pname)
            assert caller is parent
            self.msgout(4, "determine_parent ->", parent)
            return parent
        if '.' in pname:
            i = pname.rfind('.')
            pname = pname[:i]
            parent = self.findNode(pname)
            if parent:
                assert parent.identifier == pname
            self.msgout(4, "determine_parent ->", parent)
            return parent
        self.msgout(4, "determine_parent -> None")
        return None


    def find_head_package(self, parent, name):
        """
        Given a calling parent package and an import name determine the containing
        package for the name
        """
        self.msgin(4, "find_head_package", parent, name)
        if '.' in name:
            head, tail = name.split('.', 1)
        else:
            head, tail = name, ''
        if parent:
            qname = parent.identifier + '.' + head
        else:
            qname = head
        q = self.import_module(head, qname, parent)
        if q:
            self.msgout(4, "find_head_package ->", (q, tail))
            return q, tail
        if parent:
            qname = head
            parent = None
            q = self.import_module(head, qname, parent)
            if q:
                self.msgout(4, "find_head_package ->", (q, tail))
                return q, tail
        self.msgout(4, "raise ImportError: No module named", qname)
        raise ImportError, "No module named " + qname

    def load_tail(self, q, tail):
        self.msgin(4, "load_tail", q, tail)
        m = q
        while tail:
            i = tail.find('.')
            if i < 0: i = len(tail)
            head, tail = tail[:i], tail[i+1:]
            mname = "%s.%s" % (m.identifier, head)
            m = self.import_module(head, mname, m)
            if not m:
                self.msgout(4, "raise ImportError: No module named", mname)
                raise ImportError, "No module named " + mname
        self.msgout(4, "load_tail ->", m)
        return m

    def ensure_fromlist(self, m, fromlist):
        fromlist = set(fromlist)
        self.msg(4, "ensure_fromlist", m, fromlist)
        if '*' in fromlist:
            fromlist.update(self.find_all_submodules(m))
            fromlist.remove('*')
        for sub in fromlist:
            submod = m.get(sub)
            if submod is None:
                fullname = m.identifier + '.' + sub
                submod = self.import_module(sub, fullname, m)
                if submod is None:
                    raise ImportError, "No module named " + fullname
            yield submod

    def find_all_submodules(self, m):
        if not m.packagepath:
            return
        # 'suffixes' used to be a list hardcoded to [".py", ".pyc", ".pyo"].
        # But we must also collect Python extension modules - although
        # we cannot separate normal dlls from Python extensions.
        suffixes = [triple[0] for triple in imp.get_suffixes()]
        for path in m.packagepath:
            try:
                names = os.listdir(path)
            except os.error:
                self.msg(2, "can't list directory", path)
                continue
            for (path, mode, typ) in ifilter(None, imap(moduleInfoForPath, names)):
                if path != '__init__':
                    yield path

    def import_module(self, partname, fqname, parent):
        self.msgin(3, "import_module", partname, fqname, parent)
        m = self.findNode(fqname)
        if m is not None:
            self.msgout(3, "import_module ->", m)
            if parent:
                self.createReference(m, parent)
            return m
        if parent and parent.packagepath is None:
            self.msgout(3, "import_module -> None")
            return None
        try:
            fp, pathname, stuff = self.find_module(partname,
                parent and parent.packagepath, parent)
        except ImportError:
            self.msgout(3, "import_module ->", None)
            return None
        m = self.load_module(fqname, fp, pathname, stuff)
        if parent:
            self.createReference(m, parent)
            parent[partname] = m
        self.msgout(3, "import_module ->", m)
        return m

    def load_module(self, fqname, fp, pathname, (suffix, mode, typ)):
        self.msgin(2, "load_module", fqname, fp and "fp", pathname)
        packagepath = None
        if typ == imp.PKG_DIRECTORY:
            m = self.load_package(fqname, pathname)
            self.msgout(2, "load_module ->", m)
            return m
        if typ == imp.PY_SOURCE:
            co = compile(fp.read()+'\n', pathname, 'exec')
            cls = SourceModule
        elif typ == imp.PY_COMPILED:
            if fp.read(4) != imp.get_magic():
                self.msgout(2, "raise ImportError: Bad magic number", pathname)
                raise ImportError, "Bad magic number in %s" % pathname
            fp.read(4)
            co = marshal.load(fp)
            cls = CompiledModule
        elif typ == imp.C_BUILTIN:
            cls = BuiltinModule
            co = None
        elif typ == NamespaceModule:
            cls = NamespaceModule
            co = None
            packagepath = sys.modules[fqname].__path__
        else:
            cls = Extension
            co = None
        m = self.createNode(cls, fqname)
        m.filename = pathname
        if co:
            if self.replace_paths:
                co = self.replace_paths_in_code(co)
            m.code = co
            self.scan_code(co, m)
        if packagepath is not None:
            m.packagepath = packagepath
        self.msgout(2, "load_module ->", m)
        return m

    def _safe_import_hook(self, name, caller, fromlist, level=-1):
        # wrapper for self.import_hook() that won't raise ImportError
        try:
            mods = self.import_hook(name, caller, level=level)
        except ImportError, msg:
            self.msg(2, "ImportError:", str(msg))
            m = self.createNode(MissingModule, name)
            self.createReference(caller, m)
        else:
            assert len(mods) == 1
            m = list(mods)[0]

        subs = set([m])
        for sub in (fromlist or ()):
            # If this name is in the module namespace already,
            # then add the entry to the list of substitutions
            if sub in m:
                sm = m[sub]
                if sm is not None:
                    subs.add(sm)
                self.createReference(caller, sm)
                continue

            # See if we can load it
            fullname = name + '.' + sub
            sm = self.findNode(fullname)
            if sm is None:
                try:
                    sm = self.import_hook(name, caller, [sub], level=level)
                except ImportError, msg:
                    self.msg(2, "ImportError:", str(msg))
                    sm = self.createNode(MissingModule, fullname)
                else:
                    sm = self.findNode(fullname)

            m[sub] = sm
            if sm is not None:
                self.createReference(sm, m)
                subs.add(sm)
        return subs

    def scan_opcodes(self, co,
                     unpack = struct.unpack):
        # Scan the code, and yield 'interesting' opcode combinations
        # Version for Python 2.4 and older
        code = co.co_code
        names = co.co_names
        consts = co.co_consts
        while code:
            c = code[0]
            if c in STORE_OPS:
                oparg, = unpack('<H', code[1:3])
                yield "store", (names[oparg],)
                code = code[3:]
                continue
            if c == LOAD_CONST and code[3] == IMPORT_NAME:
                oparg_1, oparg_2 = unpack('<xHxH', code[:6])
                yield "import", (consts[oparg_1], names[oparg_2])
                code = code[6:]
                continue
            if c >= HAVE_ARGUMENT:
                code = code[3:]
            else:
                code = code[1:]

    def scan_opcodes_25(self, co,
                     unpack = struct.unpack):
        # Scan the code, and yield 'interesting' opcode combinations
        # Python 2.5 version (has absolute and relative imports)
        code = co.co_code
        names = co.co_names
        consts = co.co_consts
        LOAD_LOAD_AND_IMPORT = LOAD_CONST + LOAD_CONST + IMPORT_NAME
        while code:
            c = code[0]
            if c in STORE_OPS:
                oparg, = unpack('<H', code[1:3])
                yield "store", (names[oparg],)
                code = code[3:]
                continue
            if code[:9:3] == LOAD_LOAD_AND_IMPORT:
                oparg_1, oparg_2, oparg_3 = unpack('<xHxHxH', code[:9])
                level = consts[oparg_1]
                if level == -1: # normal import
                    yield "import", (consts[oparg_2], names[oparg_3])
                elif level == 0: # absolute import
                    yield "absolute_import", (consts[oparg_2], names[oparg_3])
                else: # relative import
                    yield "relative_import", (level, consts[oparg_2], names[oparg_3])
                code = code[9:]
                continue
            if c >= HAVE_ARGUMENT:
                code = code[3:]
            else:
                code = code[1:]

    def scan_code(self, co, m):
        code = co.co_code
        if sys.version_info >= (2, 5):
            scanner = self.scan_opcodes_25
        else:
            scanner = self.scan_opcodes

        for what, args in scanner(co):
            if what == "store":
                name, = args
                m.globalnames.add(name)
            elif what in ("import", "absolute_import"):
                fromlist, name = args
                have_star = 0
                if fromlist is not None:
                    if "*" in fromlist:
                        have_star = 1
                    fromlist = [f for f in fromlist if f != "*"]
                if what == "absolute_import": level = 0
                else: level = -1
                self._safe_import_hook(name, m, fromlist, level=level)
                if have_star:
                    # We've encountered an "import *". If it is a Python module,
                    # the code has already been parsed and we can suck out the
                    # global names.
                    mm = None
                    if m.packagepath:
                        # At this point we don't know whether 'name' is a
                        # submodule of 'm' or a global module. Let's just try
                        # the full name first.
                        mm = self.findNode(m.identifier+ "." + name)
                    if mm is None:
                        mm = self.findNode(name)
                    if mm is not None:
                        m.globalnames.update(mm.globalnames)
                        m.starimports.update(mm.starimports)
                        if mm.code is None:
                            m.starimports.add(name)
                    else:
                        m.starimports.add(name)
            elif what == "relative_import":
                level, fromlist, name = args
                if name:
                    self._safe_import_hook(name, m, fromlist, level=level)
                else:
                    parent = self.determine_parent(m, level=level)
                    self._safe_import_hook(parent.identifier, None, fromlist, level=0)
            else:
                # We don't expect anything else from the generator.
                raise RuntimeError(what)

        for c in co.co_consts:
            if isinstance(c, type(co)):
                self.scan_code(c, m)

    def load_package(self, fqname, pathname):
        self.msgin(2, "load_package", fqname, pathname)
        newname = replacePackageMap.get(fqname)
        if newname:
            fqname = newname
        m = self.createNode(Package, fqname)
        m.filename = pathname

        # As per comment at top of file, simulate runtime packagepath additions.
        additions = packagePathMap.get(fqname, [])
        if pathname in additions:
            m.packagepath = additions
        else:
            m.packagepath = [pathname]+additions
            
            
        fp, buf, stuff = self.find_module("__init__", m.packagepath)
        self.load_module(fqname, fp, buf, stuff)
        self.msgout(2, "load_package ->", m)
        return m

    def find_module(self, name, path, parent=None):
        if parent is not None:
            # assert path is not None
            fullname = parent.identifier+'.'+name
        else:
            fullname = name

        node = self.findNode(fullname)
        if node is not None:
            self.msgout(3, "find_module -> already included?", node)
            raise ImportError, name

        if path is None:
            if name in sys.builtin_module_names:
                return (None, None, ("", "", imp.C_BUILTIN))

            path = self.path

        try:
            fp, buf, stuff = imp.find_module(name, path)
        except ImportError:
            # pip installed namespace packages without a __init__
            m = sys.modules.get(fullname)
            if m is None or getattr(m, "__file__", None) or not getattr(m, "__path__", None):
                raise
            return (None, None, ("", "", NamespaceModule))

        if buf:
            buf = os.path.realpath(buf)
        return (fp, buf, stuff)

    def create_xref(self, out=None):
        if out is None:
            out = sys.stdout
        scripts = []
        mods = []
        for mod in self.flatten():
            name = os.path.basename(mod.identifier)
            if isinstance(mod, Script):
                scripts.append((name, mod))
            else:
                mods.append((name, mod))
        scripts.sort()
        mods.sort()
        scriptnames = [name for name, m in scripts]
        scripts.extend(mods)
        mods = scripts

        title = "modulegraph cross reference for "  + ', '.join(scriptnames)
        print >>out, """<html><head><title>%s</title></head>
            <body><h1>%s</h1>""" % (title, title)

        def sorted_namelist(mods):
            lst = [os.path.basename(mod.identifier) for mod in mods if mod]
            lst.sort()
            return lst
        for name, m in mods:
            if isinstance(m, BuiltinModule):
                print >>out, """<a name="%s" /><tt>%s</tt>
                    <i>(builtin module)</i> <br />""" % (name, name)
            elif isinstance(m, Extension):
                print >>out, """<a name="%s" /><tt>%s</tt> <tt>%s</tt></a>
                    <br />""" % (name, name, m.filename)
            else:
                url = urllib.pathname2url(m.filename or "")
                print >>out, """<a name="%s" />
                    <a target="code" href="%s" type="text/plain"><tt>%s</tt></a>
                    <br />""" % (name, url, name)
            oute, ince = map(sorted_namelist, self.get_edges(m))
            if oute:
                print >>out, 'imports:'
                for n in oute:
                    print >>out, """<a href="#%s">%s</a>""" % (n, n)
                print >>out, '<br />'
            if ince:
                print >>out, 'imported by:'
                for n in ince:
                    print >>out, """<a href="#%s">%s</a>""" % (n, n)
                print >>out, '<br />'
            print >>out, '<br/>'
        print >>out, '</body></html>'
        

    def itergraphreport(self, name='G', flatpackages=()):
        nodes = map(self.graph.describe_node, self.graph.iterdfs(self))
        describe_edge = self.graph.describe_edge
        edges = deque()
        packagenodes = set()
        packageidents = {}
        nodetoident = {}
        inpackages = {}
        mainedges = set()

        # XXX - implement
        flatpackages = dict(flatpackages)

        def nodevisitor(node, data, outgoing, incoming):
            if not isinstance(data, Node):
                return {'label': str(node)}
            #if isinstance(d, (ExcludedModule, MissingModule, BadModule)):
            #    return None
            s = '<f0> ' + type(data).__name__
            for i,v in izip(count(1), data.infoTuple()[:1]):
                s += '| <f%d> %s' % (i,v)
            return {'label':s, 'shape':'record'}

        def edgevisitor(edge, data, head, tail):
            if data == 'orphan':
                return {'style':'dashed'}
            elif data == 'pkgref':
                return {'style':'dotted'}
            return {}

        yield 'digraph %s {\n' % (name,)
        attr = dict(rankdir='LR', concentrate='true')
        cpatt  = '%s="%s"'
        for item in attr.iteritems():
            yield '\t%s;\n' % (cpatt % item,)

        # find all packages (subgraphs)
        for (node, data, outgoing, incoming) in nodes:
            nodetoident[node] = getattr(data, 'identifier', None)
            if isinstance(data, Package):
                packageidents[data.identifier] = node
                inpackages[node] = set([node])
                packagenodes.add(node)


        # create sets for subgraph, write out descriptions
        for (node, data, outgoing, incoming) in nodes:
            # update edges
            for edge in imap(describe_edge, outgoing):
                edges.append(edge)

            # describe node
            yield '\t"%s" [%s];\n' % (
                node,
                ','.join([
                    (cpatt % item) for item in
                    nodevisitor(node, data, outgoing, incoming).iteritems()
                ]),
            )

            inside = inpackages.get(node)
            if inside is None:
                inside = inpackages[node] = set()
            ident = nodetoident[node]
            if ident is None:
                continue
            pkgnode = packageidents.get(ident[:ident.rfind('.')])
            if pkgnode is not None:
                inside.add(pkgnode)


        graph = []
        subgraphs = {}
        for key in packagenodes:
            subgraphs[key] = []

        while edges:
            edge, data, head, tail = edges.popleft()
            if ((head, tail)) in mainedges:
                continue
            mainedges.add((head, tail))
            tailpkgs = inpackages[tail]
            common = inpackages[head] & tailpkgs
            if not common and tailpkgs:
                usepkgs = sorted(tailpkgs)
                if len(usepkgs) != 1 or usepkgs[0] != tail:
                    edges.append((edge, data, head, usepkgs[0]))
                    edges.append((edge, 'pkgref', usepkgs[-1], tail))
                    continue
            if common:
                common = common.pop()
                if tail == common:
                    edges.append((edge, data, tail, head))
                elif head == common:
                    subgraphs[common].append((edge, 'pkgref', head, tail))
                else:
                    edges.append((edge, data, common, head))
                    edges.append((edge, data, common, tail))

            else:
                graph.append((edge, data, head, tail))

        def do_graph(edges, tabs):
            edgestr = tabs + '"%s" -> "%s" [%s];\n'
            # describe edge
            for (edge, data, head, tail) in edges:
                attribs = edgevisitor(edge, data, head, tail)
                yield edgestr % (
                    head,
                    tail,
                    ','.join([(cpatt % item) for item in attribs.iteritems()]),
                )

        for g, edges in subgraphs.iteritems():
            yield '\tsubgraph "cluster_%s" {\n' % (g,)
            yield '\t\tlabel="%s";\n' % (nodetoident[g],)
            for s in do_graph(edges, '\t\t'):
                yield s
            yield '\t}\n'

        for s in do_graph(graph, '\t'):
            yield s

        yield '}\n'

    def graphreport(self, fileobj=None, flatpackages=()):
        if fileobj is None:
            fileobj = sys.stdout
        fileobj.writelines(self.itergraphreport(flatpackages=flatpackages))

    def report(self):
        """Print a report to stdout, listing the found modules with their
        paths, as well as modules that are missing, or seem to be missing.
        """
        print
        print "%-15s %-25s %s" % ("Class", "Name", "File")
        print "%-15s %-25s %s" % ("----", "----", "----")
        # Print modules found
        sorted = [(os.path.basename(mod.identifier), mod) for mod in self.flatten()]
        sorted.sort()
        for (name, m) in sorted:
            print "%-15s %-25s %s" % (type(m).__name__, name, m.filename or "")

    def replace_paths_in_code(self, co):
        new_filename = original_filename = os.path.normpath(co.co_filename)
        for f, r in self.replace_paths:
            f = os.path.join(f, '')
            r = os.path.join(r, '')
            if original_filename.startswith(f):
                new_filename = r + original_filename[len(f):]
                break

        consts = list(co.co_consts)
        for i in range(len(consts)):
            if isinstance(consts[i], type(co)):
                consts[i] = self.replace_paths_in_code(consts[i])

        return new.code(co.co_argcount, co.co_nlocals, co.co_stacksize,
                         co.co_flags, co.co_code, tuple(consts), co.co_names,
                         co.co_varnames, new_filename, co.co_name,
                         co.co_firstlineno, co.co_lnotab,
                         co.co_freevars, co.co_cellvars)

def main():
    # Parse command line
    import getopt
    try:
        opts, args = getopt.getopt(sys.argv[1:], "dgmp:qx:")
    except getopt.error, msg:
        print msg
        return

    # Process options
    debug = 1
    domods = 0
    dodot = False
    addpath = []
    excludes = []
    for o, a in opts:
        if o == '-d':
            debug = debug + 1
        if o == '-m':
            domods = 1
        if o == '-p':
            addpath = addpath + a.split(os.pathsep)
        if o == '-q':
            debug = 0
        if o == '-x':
            excludes.append(a)
        if o == '-g':
            dodot = True

    # Provide default arguments
    if not args:
        script = __file__
    else:
        script = args[0]

    # Set the path based on sys.path and the script directory
    path = sys.path[:]
    path[0] = os.path.dirname(script)
    path = addpath + path
    if debug > 1:
        print "path:"
        for item in path:
            print "   ", repr(item)

    # Create the module finder and turn its crank
    mf = ModuleGraph(path, excludes=excludes, debug=debug)
    for arg in args[1:]:
        if arg == '-m':
            domods = 1
            continue
        if domods:
            if arg[-2:] == '.*':
                mf.import_hook(arg[:-2], None, ["*"])
            else:
                mf.import_hook(arg)
        else:
            mf.run_script(arg)
    mf.run_script(script)
    if dodot:
        mf.graphreport()
    else:
        mf.report()
    return mf  # for -i debugging


if __name__ == '__main__':
    try:
        mf = main()
    except KeyboardInterrupt:
        print "\n[interrupt]"

########NEW FILE########
__FILENAME__ = util
import imp

def imp_find_module(name):
    """same as imp.find_module, but handles dotted names"""
    names = name.split('.')
    path = None
    for name in names:
        result = imp.find_module(name, path)
        path = [result[1]]
    return result

def test_imp_find_module():
    import encodings.aliases
    fn = imp_find_module('encodings.aliases')[1]
    assert encodings.aliases.__file__.startswith(fn)

if __name__ == '__main__':
    test_imp_find_module()

########NEW FILE########
__FILENAME__ = py
#! /usr/bin/env python
"""interactive python prompt with tab completion"""

# code inspired by matplotlib
# (http://matplotlib.sourceforge.net/examples/interactive.py)

import sys
main = __import__("__main__")


class error(Exception):
    pass


def parse_options(args, spec):
    needarg = dict()

    for x in spec.split():
        if x.endswith("="):
            needarg[x[:-1]] = True
        else:
            needarg[x] = False

    opts = []
    newargs = []

    i = 0
    while i < len(args):
        a, v = (args[i].split("=", 1) + [None])[:2]
        if a in needarg:
            if v is None and needarg[a]:
                i += 1
                try:
                    v = args[i]
                except IndexError:
                    raise error("option %s needs an argument" % (a, ))
            opts.append((a, v))
            if a == "-c":
                break
        else:
            break

        i += 1

    newargs.extend(args[i:])
    return opts, newargs

opts, args = parse_options(sys.argv[1:], "-u -c=")
opts = dict(opts)
sys.argv = args
if not sys.argv:
    sys.argv.append("")

if opts.get("-c") is not None:
    exec opts.get("-c") in main.__dict__
    sys.exit(0)

if sys.argv[0]:
    main.__dict__['__file__'] = sys.argv[0]
    exec open(sys.argv[0], 'r') in main.__dict__
    sys.exit(0)


from code import InteractiveConsole
import time
try:
    # rlcompleter also depends on readline
    import rlcompleter
    import readline
except ImportError:
    readline = None


class MyConsole(InteractiveConsole):
    needed = 0.0

    def __init__(self, *args, **kwargs):
        InteractiveConsole.__init__(self, *args, **kwargs)

        if not readline:
            return

        try:  # this form only works with python 2.3
            self.completer = rlcompleter.Completer(self.locals)
        except:  # simpler for py2.2
            self.completer = rlcompleter.Completer()

        readline.set_completer(self.completer.complete)
        # Use tab for completions
        readline.parse_and_bind('tab: complete')
        # This forces readline to automatically print the above list when tab
        # completion is set to 'complete'.
        readline.parse_and_bind('set show-all-if-ambiguous on')
        # Bindings for incremental searches in the history. These searches
        # use the string typed so far on the command line and search
        # anything in the previous input history containing them.
        readline.parse_and_bind('"\C-r": reverse-search-history')
        readline.parse_and_bind('"\C-s": forward-search-history')

    def runcode(self, code):
        stime = time.time()
        try:
            return InteractiveConsole.runcode(self, code)
        finally:
            self.needed = time.time() - stime

    def raw_input(self, prompt=""):
        if self.needed > 0.01:
            prompt = "[%.2fs]\n%s" % (self.needed, prompt)
            self.needed = 0.0

        return InteractiveConsole.raw_input(self, prompt)


if readline:
    import os
    histfile = os.path.expanduser("~/.pyhistory")
    if os.path.exists(histfile):
        readline.read_history_file(histfile)

try:
    MyConsole(locals=dict()).interact()
finally:
    if readline:
        readline.write_history_file(histfile)

########NEW FILE########
__FILENAME__ = recipes
import sys
import os


def isRealModule(m):
    from modulegraph.modulegraph import BadModule, MissingModule, ExcludedModule
    if m is None or isinstance(m, (BadModule, MissingModule, ExcludedModule)):
        return False
    else:
        return True


def include_whole_package(name, skip=lambda x: False):
    def recipe(mf):
        m = mf.findNode(name)
        if not isRealModule(m):
            return None

        from bbfreeze.freezer import ZipModule
        if isinstance(m, ZipModule):
            return None

        top = os.path.dirname(m.filename)
        prefixlen = len(os.path.dirname(top)) + 1
        for root, dirs, files in os.walk(top):
            pkgname = root[prefixlen:].replace(os.path.sep, ".")
            for f in files:
                if not f.endswith(".py"):
                    continue

                if f == "__init__.py":
                    modname = pkgname
                else:
                    modname = "%s.%s" % (pkgname, f[:-3])

                if not skip(modname):
                    mf.import_hook(modname, m, ['*'])
        return True

    recipe.__name__ = "recipe_" + name
    return recipe


def find_all_packages(name, skip=lambda x: False):
    def recipe(mf):
        m = mf.findNode(name)
        if not isRealModule(m):
            return None

        from bbfreeze.freezer import ZipModule
        if isinstance(m, ZipModule):
            return None

        import setuptools
        packages = setuptools.find_packages(os.path.dirname(m.filename))

        for pkg in packages:
            pkgname = '%s.%s' % (name, pkg)
            if not skip(pkgname):
                mf.import_hook(pkgname, m, ['*'])
        return True
    recipe.__name__ = "recipe_" + name
    return recipe

recipe_flup = find_all_packages('flup')
recipe_django = find_all_packages('django')
recipe_py = include_whole_package("py", skip=lambda x: x.startswith("py.test.tkinter"))
recipe_IPython = find_all_packages("IPython")


def recipe_django_core_management(mf):
    m = mf.findNode('django.core.management')
    if not isRealModule(m):
        return None
    refs = ["IPython"]
    for ref in refs:
        mf.removeReference(m, ref)
    return True


def recipe_xmlrpclib(mf):
    m = mf.findNode("xmlrpclib")
    if not isRealModule(m):
        return None
    # we have python 2.0, SlowParser is not used as xml.parsers.expat.ParserCreate is available
    mf.removeReference(m, 'xmllib')
    return True


def recipe_ctypes_macholib(mf):
    if os.name == "posix" and sys.platform == "darwin":
        return None
    m = mf.findNode('ctypes.macholib.dyld')
    if not isRealModule(m):
        return None
    mf.removeReference('ctypes.util', m)
    return True


def recipe_doctest(mf):
    m = mf.findNode('doctest')
    if not isRealModule(m):
        return None

    refs = ['collections', 'decimal', 'difflib', 'heapq', 'pickle', 'Cookie', 'pickletools', 'memcache', 'simplegeneric']
    for ref in refs:
        mf.removeReference(ref, m)
    return True


def recipe_twisted_python_versions(mf):
    m = mf.findNode('twisted.python.versions')
    if not isRealModule(m):
        return None
    mf.removeReference(m, 'xml.dom.minidom')
    return True


def recipe_pydoc(mf):
    m = mf.findNode('pydoc')
    if not isRealModule(m):
        return None

    refs = [
        'Tkinter', 'tty', 'BaseHTTPServer', 'mimetools', 'select',
        'threading', 'ic', 'getopt',
    ]
    if sys.platform != 'win32':
        refs.append('nturl2path')
    for ref in refs:
        mf.removeReference(m, ref)
    return True


def recipe_urllib(mf):
    m = mf.findNode('urllib')
    if not isRealModule(m):
        return None
    retval = None

    if sys.platform != 'darwin':
        for ref in ['ctypes', 'ctypes.util']:
            mf.removeReference(m, ref)
        retval = True

    if os.name != 'mac':
        mf.removeReference(m, 'macurl2path')
        retval = True

    if os.name != 'nt':
        mf.removeReference(m, 'nturl2path')
        retval = True
    return retval


def recipe_docutils(mf):
    m = mf.findNode('docutils')
    if not isRealModule(m):
        return None

    for pkg in [
            'languages', 'parsers', 'readers', 'writers',
            'parsers.rst.directives', 'parsers.rst.languages']:
        try:
            mf.import_hook('docutils.' + pkg, m, ['*'])
        except SyntaxError:  # in docutils/writers/newlatex2e.py
            pass
    return True


def recipe_pythoncom(mf):
    m = mf.findNode("pythoncom")
    if not isRealModule(m):
        return None
    import pythoncom
    from bbfreeze.freezer import SharedLibrary
    n = mf.createNode(SharedLibrary, os.path.basename(pythoncom.__file__))
    n.filename = pythoncom.__file__
    mf.createReference(m, n)
    mf.import_hook('pywintypes', m, ['*'])
    return True


def recipe_pywintypes(mf):
    m = mf.findNode("pywintypes")
    if not isRealModule(m):
        return None
    import pywintypes
    from bbfreeze.freezer import SharedLibrary
    n = mf.createNode(SharedLibrary, os.path.basename(pywintypes.__file__))
    n.filename = pywintypes.__file__
    mf.createReference(m, n)
    return True


def recipe_time(mf):
    m = mf.findNode('time')

    # time is a BuiltinModule on win32, therefor m.filename is None
    if m is None:  # or m.filename is None:
        return None

    mf.import_hook('_strptime', m, ['*'])
    return True


def recipe_distutils_util_get_platform(mf):
    m = mf.findNode('distutils.util')
    if not isRealModule(m):
        return None

    import distutils.util
    val = distutils.util.get_platform()

    repl = """
def get_platform():
    return %r
""" % (val,)

    import codehack
    m.code = codehack.replace_functions(m.code, repl)
    return True


def recipe_matplotlib(mf):
    m = mf.findNode('matplotlib')
    if not isRealModule(m):
        return
    import matplotlib

    if 0:  # do not copy matplotlibdata. assume matplotlib is installed as egg
        dp = matplotlib.get_data_path()
        assert dp
        mf.copyTree(dp, "matplotlibdata", m)

    mf.import_hook("matplotlib.numerix.random_array", m)
    backend_name = 'backend_' + matplotlib.get_backend().lower()
    print "recipe_matplotlib: using the %s matplotlib backend" % (backend_name, )
    mf.import_hook('matplotlib.backends.' + backend_name, m)
    return True


def recipe_tkinter(mf):
    m = mf.findNode('_tkinter')
    if m is None or m.filename is None:
        return None

    if sys.platform == 'win32':
        import Tkinter
        tcldir = os.environ.get("TCL_LIBRARY")
        if tcldir:
            mf.copyTree(tcldir, "lib-tcl", m)
        else:
            print "WARNING: recipe_tkinter: TCL_LIBRARY not set. cannot find lib-tcl"

        tkdir = os.environ.get("TK_LIBRARY")
        if tkdir:
            mf.copyTree(tkdir, "lib-tk", m)
        else:
            print "WARNING: recipe_tkinter: TK_LIBRARY not set. cannot find lib-tk"
    else:
        import _tkinter
        from bbfreeze import getdeps

        deps = getdeps.getDependencies(_tkinter.__file__)
        for x in deps:
            if os.path.basename(x).startswith("libtk"):
                tkdir = os.path.join(os.path.dirname(x), "tk%s" % _tkinter.TK_VERSION)
                if os.path.isdir(tkdir):
                    mf.copyTree(tkdir, "lib-tk", m)

        for x in deps:
            if os.path.basename(x).startswith("libtcl"):
                tcldir = os.path.join(os.path.dirname(x), "tcl%s" % _tkinter.TCL_VERSION)
                if os.path.isdir(tcldir):
                    mf.copyTree(tcldir, "lib-tcl", m)

    return True


def recipe_gtk_and_friends(mf):
    retval = False
    from bbfreeze.freezer import SharedLibrary
    from modulegraph.modulegraph import ExcludedModule
    for x in list(mf.flatten()):
        if not isinstance(x, SharedLibrary):
            continue

        prefixes = ["libpango", "libpangocairo", "libpangoft", "libgtk", "libgdk", "libglib", "libgmodule", "libgobject", "libgthread"]

        for p in prefixes:
            if x.identifier.startswith(p):
                print "SKIPPING:", x
                x.__class__ = ExcludedModule
                retval = True
                break

    return retval


def recipe_cElementTree25(mf):
    m = mf.findNode("_elementtree")

    if not isRealModule(m):
        return None

    mf.import_hook("pyexpat", m, "*")
    mf.import_hook("xml.etree.ElementTree")
    return True


def recipe_cElementTree(mf):
    m = mf.findNode("cElementTree")

    if not isRealModule(m):
        return None

    #mf.import_hook("pyexpat", m, "*")
    mf.import_hook("elementtree.ElementTree")
    return True


def recipe_mercurial(mf):
    m = mf.findNode("mercurial")
    if not isRealModule(m):
        return None
    mf.import_hook("hgext", m, "*")
    mf.import_hook("hgext.convert", m, "*")
    t = os.path.join(os.path.dirname(m.filename), "templates")
    mf.copyTree(t, "templates", m)
    return True


def recipe_kinterbasdb(mf):
    m = mf.findNode("kinterbasdb")
    if not isRealModule(m):
        return
    mods = """typeconv_23plus_lowmem
typeconv_23plus
typeconv_24plus
typeconv_backcompat
typeconv_datetime_mx
typeconv_datetime_naked
typeconv_datetime_stdlib
typeconv_fixed_decimal
typeconv_fixed_fixedpoint
typeconv_fixed_stdlib
typeconv_naked
typeconv_text_unicode""".split()
    for x in mods:
        mf.import_hook("kinterbasdb." + x, m)
    return True


def recipe_gevent_core(mf):
    m = mf.findNode("gevent.core")
    if not isRealModule(m):
        return None

    mf.import_hook("weakref", m)
    return True


def recipe_gevent_hub(mf):
    m = mf.findNode("gevent.hub")
    if not isRealModule(m):
        return None

    deps = mf.import_hook("greenlet", None)
    for n in deps:
        mf.createReference(m, n)
    return True


def recipe_lxml_etree(mf):
    m = mf.findNode("lxml.etree")
    if not isRealModule(m):
        return None
    mf.import_hook("lxml._elementpath", m)
    mf.import_hook("gzip", m)
    mf.import_hook("inspect", m)
    return True

########NEW FILE########
__FILENAME__ = winexeutil
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import struct
import win32api


class Icon:
    """
    Icon class. Represents an Ico file.
    """
    # Parsing constants
    HEADER_FORMAT = "hhh"
    ENTRY_FORMAT = "bbbbhhii"
    ENTRY_FORMAT_ID = "bbbbhhih"
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
    ENTRY_SIZE = struct.calcsize(ENTRY_FORMAT)
    
    def __init__(self, filename):
        """
        Create a Icon object from the path to a .ico file.
        """
        # Icon sections
        self._header = ""
        self._entries = []
        self._images = []
        
        with open(filename, 'rb') as fd:
            self._header = fd.read(self.HEADER_SIZE)
            # Get the tuple of the header and get how many entries we have
            count = self.header()[2]
            
            # Collect entries in the ico file
            for i in range(count):
                # Read entry
                e = fd.read(self.ENTRY_SIZE)
                self._entries.append(e)
            
            # Now collect images
            for i, bentry in enumerate(self._entries):
                entry = struct.unpack(self.ENTRY_FORMAT, bentry)
                # Go to image and read bytes
                fd.seek(entry[7], 0)
                data = fd.read(entry[6])
                self._images.append(data)
                # Remove last item (offset) and add the id
                entry = entry[:-1] + (i+1,)
                # Save change back in bytes
                self._entries[i] = struct.pack(self.ENTRY_FORMAT_ID,
                                               *entry)
                
    
    def header(self):
        """
        Return a tuple with the values in the header of the Icon.
        
        Header is made of three values:
        - a reserved value
        - the type id
        - entries count
        """
        return struct.unpack(self.HEADER_FORMAT, self._header)
    
    def entries(self):
        """
        Return an array with the tuples of the icons entries. An icon entry
        is a special header that describes an image. A single .ico file can
        contain multiple entries.
        
        Each entry contains:
        - width
        - height
        - color count
        - reserved value
        - planes
        - bit count
        - size of image
        - id
        """
        res = []
        for e in self._entries:
            res.append(struct.unpack(self.ENTRY_FORMAT_ID, e))
        return res
    
    def images(self):
        """
        Return an array with the bytes for each of the images in the icon.
        """
        return _images


def set_icon(exe_filename, ico_filename):
    """
    Set the icon on a windows executable.
    """
    # Icon file
    icon = Icon(ico_filename)

    # Begin update of executable
    hdst = win32api.BeginUpdateResource (exe_filename, 0)

    # Update entries
    data = icon._header + reduce(str.__add__, icon._entries)
    win32api.UpdateResource (hdst, 14, 1, data)

    # Update images
    for i, image in enumerate(icon._images):
        win32api.UpdateResource (hdst, 3, i+1, image)

    # Done
    win32api.EndUpdateResource (hdst, 0)

########NEW FILE########
__FILENAME__ = __main__
#! /usr/bin/env python

if __name__=='__main__':
    from bbfreeze import main
    main()

########NEW FILE########
__FILENAME__ = showvars
#! /usr/bin/env python
"""show distutils's config variables"""


def main():
    import distutils.sysconfig
    items = distutils.sysconfig.get_config_vars().items()
    items.sort()
    for k, v in items:
        print "%s: %r" % (k, v)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = expatbuilder
from baz.parsers import expat

########NEW FILE########
__FILENAME__ = expat
# import sys

########NEW FILE########
__FILENAME__ = bazscript
#! /usr/bin/env python

from baz.dom import expatbuilder
from baz.parsers import expat  # this is missing from the dependency graph

########NEW FILE########
__FILENAME__ = conftest
import os


def pytest_configure(config):
    os.chdir(os.path.dirname(__file__))

########NEW FILE########
__FILENAME__ = ex-celementtree
#! /usr/bin/env python

import sys
if sys.version_info >= (2, 5):
    import xml.etree.cElementTree as ET
else:
    import cElementTree as ET

xml = """<?xml version='1.0'?>
<methodCall>
<methodName>echo</methodName>
<params>
<param>
<value><string>bla</string></value>
</param>
</params>
</methodCall>
"""

ET.fromstring(xml)

########NEW FILE########
__FILENAME__ = ex-email_mimetext
from email.MIMEText import MIMEText

########NEW FILE########
__FILENAME__ = ex-fsenc
#! /usr/bin/env python

import sys, os
print sys.getfilesystemencoding(), os.environ.get("LANG", "<>")

########NEW FILE########
__FILENAME__ = ex-kinterbasdb
import kinterbasdb

# The server is named 'bison'; the database file is at '/temp/test.db'.
con = kinterbasdb.connect(dsn='bison:/temp/test.db', user='sysdba', password='pass')

# Or, equivalently:
con = kinterbasdb.connect(
    host='bison', database='/temp/test.db',
    user='sysdba', password='pass')

########NEW FILE########
__FILENAME__ = ex-lxml
import lxml.etree

########NEW FILE########
__FILENAME__ = ex-matplotlib
#! /usr/bin/env python

from pylab import plot, show


def main():
    x = range(10)
    y = range(10)

    plot(x, y)
    show()


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = ex-mbox
#! /usr/bin/env python

if __name__ == '__main__':
    import win32gui
    win32gui.MessageBox(0, "hello from bbfreeze", "bbfreeze: ex-mbox", 1)

########NEW FILE########
__FILENAME__ = ex-pylog
#! /usr/bin/env python

"""test py library"""

import py
p = py.log.Producer("foo")
p.info("hello world")

########NEW FILE########
__FILENAME__ = ex-pythoncom
import pythoncom

########NEW FILE########
__FILENAME__ = ex-pywintypes
import pywintypes

########NEW FILE########
__FILENAME__ = ex-time
import time

if __name__ == '__main__':
    print time.strptime("30 Nov 07", "%d %b %y")

########NEW FILE########
__FILENAME__ = ex-tkinter
import os
import Tkinter


def main():
    msg = 'hello world'

    def show(n):
        m = "%s: %s" % (n, os.environ.get(n))
        print m
        return m

    msg += "\n" + show("TCL_LIBRARY")
    msg += "\n" + show("TK_LIBRARY")

    root = Tkinter.Tk()
    Tkinter.Label(root, text=msg).grid(column=0, row=0)
    root.mainloop()

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = ex-wxpython
from wxPython.wx import *


class MyApp(wxApp):
    def OnInit(self):
        frame = wxFrame(NULL, -1, "Hello from wxPython")
        frame.Show(true)
        self.SetTopWindow(frame)
        return true

app = MyApp(0)
app.MainLoop()

########NEW FILE########
__FILENAME__ = hello-world
#! /usr/bin/env python

import sys
import email

print unicode("hello", "utf8"), unicode("world!", "ascii")

print "sys.path:", sys.path
print "__file__:", __file__
print "__name__:", __name__

print "locals():", locals()

print "sys.argv", sys.argv
print "sys.executable:", sys.executable

########NEW FILE########
__FILENAME__ = forms

########NEW FILE########
__FILENAME__ = test_filesystemencoding
#! /usr/bin/env py.test

import py, sys, os

pyexe = py.path.local(sys.executable)


def check_encoding():
    enc = pyexe.sysexec("ex-fsenc.py")
    print "ENC:", enc
    enc_frozen = py.path.local("dist/ex-fsenc").sysexec()
    assert enc == enc_frozen


def test_getfilesystemencoding(monkeypatch):
    os.system("bbfreeze ex-fsenc.py")

    monkeypatch.setenv("LANG", "en_US.UTF-8")
    check_encoding()

    monkeypatch.setenv("LANG", "")
    check_encoding()

    monkeypatch.setenv("LANG", "de_AT@euro")
    check_encoding()

########NEW FILE########
__FILENAME__ = test_guiscript
#! /usr/bin/env py.test
try:
    import win32ui
except:
    win32ui = None

import os
import bbfreeze

if win32ui:
    def test_guiscript():
        f = bbfreeze.Freezer()
        f.addScript("ex-mbox.py", True)
        f()
        err = os.system("dist\\ex-mbox")
        assert err == 0


def test_guiscript2():
    f = bbfreeze.Freezer()
    f.addScript("hello-world.py", True)
    f()

    cmd = os.path.join("dist", "hello-world")
    err = os.system(cmd)

    assert err == 0

########NEW FILE########
__FILENAME__ = test_icon
#! /usr/bin/env py.test

import os, sys
import bbfreeze

def test_icon():
    pass

if sys.platform == 'win32':
    def test_icon():
        f = bbfreeze.Freezer()
        f.addScript("ex-mbox.py", False)
        f.setIcon('python.ico')
        f()
        err = os.system("dist\\ex-mbox")
        assert err == 0

if __name__ == '__main__':
    test_icon()
########NEW FILE########
__FILENAME__ = test_relimport
#! /usr/bin/env py.test

import sys

if sys.version_info >= (2, 5):
    def test_freeze_relimport():
        from bbfreeze import Freezer
        f = Freezer(includes=['relimport'])
        f()

if __name__ == '__main__':
    test_freeze_relimport()

########NEW FILE########
__FILENAME__ = test_script
#! /usr/bin/env py.test

import sys, os


def fullpath(x):
    dn = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(dn, x)


def compile_and_run(p):
    err = os.system("bbfreeze %s" % p)
    assert err == 0, "bbfreeze failed"
    if p.endswith('.py'):
        p = p[:-3]
    err = os.system(os.path.abspath(os.path.join('dist', p)))
    assert err == 0, "frozen executable failed"


def maybe_compile_and_run(x):
    print "\n\n-----------------> building", x, "<------------"

    assert os.path.exists(x)
    os.environ['S'] = fullpath(x)
    err = os.system("%s %s" % (sys.executable, fullpath(x)))
    if err == 0:
        compile_and_run(x)
    else:
        print "failed"


def test_ex_time():
    maybe_compile_and_run("ex-time.py")


def test_hello_world():
    maybe_compile_and_run("hello-world.py")


def test_pylog():
    maybe_compile_and_run("ex-pylog.py")


def test_celementtree():
    maybe_compile_and_run("ex-celementtree.py")


def test_email_mimetext():
    maybe_compile_and_run("ex-email_mimetext.py")


def test_lxml_etree():
    maybe_compile_and_run("ex-lxml.py")


if sys.platform == 'win32':
    def test_pythoncom():
        maybe_compile_and_run("ex-pythoncom.py")

    def test_pywintypes():
        maybe_compile_and_run("ex-pywintypes.py")


########NEW FILE########
__FILENAME__ = wx-example
#import wx
from wxPython.wx import *


class MyApp(wxApp):
    def OnInit(self):
        frame = wxFrame(NULL, -1, "Hello from wxPython")
        frame.Show(true)
        self.SetTopWindow(frame)
        return true

app = MyApp(0)
app.MainLoop()

########NEW FILE########
