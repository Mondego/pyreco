__FILENAME__ = test
import pbundler
pbundler.PBundler.setup()
import sys

import PIL # actually pillow

print(repr(PIL))



########NEW FILE########
__FILENAME__ = sitecustomize
from __future__ import print_function

import traceback

try:
    import pbundler
    pbundler.PBundler.setup()
except:
    print("E: Exception in pbundler activation code.")
    print("")
    print("Please report this to the pbundler developers:")
    print("    http://github.com/zeha/pbundler/issues")
    print("")
    traceback.print_exc()
    print("")

########NEW FILE########
__FILENAME__ = bundle
from __future__ import print_function
from __future__ import absolute_import

__all__ = ['Bundle']

import os
import sys

from . import PBundlerException
from .util import PBFile
from .pypath import PyPath
from .cheesefile import Cheesefile, CheesefileLock, Cheese, CHEESEFILE, CHEESEFILE_LOCK
from .sources import FilesystemSource
from .localstore import LocalStore


class Bundle:

    def __init__(self, path):
        self.path = path
        self.current_platform = 'cpython'

        self.cheesefile = Cheesefile(os.path.join(self.path, CHEESEFILE))
        self.cheesefile.parse()
        cheesefile_lock_path = os.path.join(self.path, CHEESEFILE_LOCK)
        if os.path.exists(cheesefile_lock_path):
            self.cheesefile_lock = CheesefileLock(cheesefile_lock_path)
            self.cheesefile_lock.parse()
        else:
            self.cheesefile_lock = None

        self.localstore = LocalStore()

    @classmethod
    def load(cls, path=None):
        """Preferred constructor."""

        if path is None:
            path = PBFile.find_upwards(CHEESEFILE)
            if path is None:
                message = ("Could not find %s in path from here to " +
                           "filesystem root.") % (CHEESEFILE)
                raise PBundlerException(message)

        return cls(path)

    def validate_requirements(self):
        self.calculate_requirements()
        pass

    def _add_new_dep(self, dep):
        cheese = Cheese.from_requirement(dep)
        existing = self.required.get(cheese.name)
        if existing:
            # FIXME: check if we're compatible
            return None
        self.required[cheese.name] = cheese
        return cheese

    def _resolve_deps(self):
        for pkg in self.required.values():
            if pkg.source or pkg.dist:
                # don't touch packages where we already know a source (& version)
                continue

            if pkg.path:
                source = FilesystemSource(pkg.path)
                available_versions = source.available_versions(pkg)
                if len(available_versions) == 0:
                    raise PBundlerException("Package %s is not available in %r" % (pkg.name, pkg.path))
                if len(available_versions) != 1:
                    raise PBundlerException("Package %s has multiple versions in %r" % (pkg.name, pkg.path))

                version = available_versions[0]
                pkg.use_from(version, source)

            else:
                req = pkg.requirement()
                for source in self.cheesefile.sources:
                    for version in source.available_versions(pkg):
                        if version in req:
                            pkg.use_from(version, source)
                            break

                if pkg.source is None:
                    raise PBundlerException("Package %s %s is not available on any sources." % (pkg.name, pkg.version_req))

        new_deps = []

        for pkg in self.required.values():
            if pkg.dist:
                # don't touch packages where we already have a (s)dist
                continue

            if pkg.path:
                # FIXME: not really the truth
                dist = pkg.source.get_distribution(pkg.source)
                print("Using %s %s from %s" % (pkg.name, pkg.exact_version, pkg.path))
            else:
                dist = self.localstore.get(pkg)
                if dist:
                    print("Using %s %s" % (pkg.name, pkg.exact_version))
                else:
                    # download and unpack
                    dist = self.localstore.prepare(pkg, pkg.source)

            pkg.use_dist(dist)

            for dep in dist.requires():
                new_deps.append(self._add_new_dep(dep))

        # super ugly:
        new_deps = list(set(new_deps))
        if None in new_deps:
            new_deps.remove(None)
        return new_deps

    def install(self, groups):
        self.required = self.cheesefile.collect(groups, self.current_platform)

        while True:
            new_deps = self._resolve_deps()
            if len(new_deps) == 0:
                # done resolving!
                break

        for pkg in self.required.values():
            if getattr(pkg.dist, 'is_sdist', False) is True:
                dist = self.localstore.install(pkg, pkg.dist)
                pkg.use_dist(dist)  # mark as installed

        self._write_cheesefile_lock()
        print("Your bundle is complete.")

    def _write_cheesefile_lock(self):
        # TODO: file format is wrong. at least we must consider groups,
        # and we shouldn't rewrite the entire file (think groups, platforms).
        # TODO: write source to lockfile.
        with file(os.path.join(self.path, CHEESEFILE_LOCK), 'wt') as lockfile:
            indent = ' '*4
            lockfile.write("with Cheesefile():\n")
            for pkg in self.cheesefile.collect(['default'], self.current_platform).itervalues():
                lockfile.write(indent+"req(%r, %r, path=%r)\n" % (pkg.name, pkg.exact_version, pkg.path))
            lockfile.write(indent+"pass\n")
            lockfile.write("\n")

            for source in self.cheesefile.sources:
                lockfile.write("with from_source(%r):\n" % (source.url))
                for name, pkg in self.required.items():
                    # ignore ourselves and our dependencies (which should
                    # only ever be distribute).
                    if name in ['pbundler','distribute']:
                        continue
                    if pkg.source != source:
                        continue
                    lockfile.write(indent+"with resolved_req(%r, %r):\n" % (pkg.name, pkg.exact_version))
                    for dep in pkg.requirements:
                        lockfile.write(indent+indent+"req(%r, %r)\n" % (dep.name, dep.version_req))
                    lockfile.write(indent+indent+"pass\n")
                lockfile.write(indent+"pass\n")

    def _check_sys_modules_is_clean(self):
        # TODO: Possibly remove this when resolver/activation development is done.
        unclean = []
        for name, module in sys.modules.iteritems():
            source = getattr(module, '__file__', None)
            if source is None or name == '__main__':
                continue
            in_path = False
            for path in sys.path:
                if source.startswith(path):
                    in_path = True
                    break
            if in_path:
                continue
            unclean.append('%s from %s' % (name, source))
        if len(unclean) > 0:
            raise PBundlerException("sys.modules contains foreign modules: %s" % ','.join(unclean))

    def load_cheese(self):
        if getattr(self, 'required', None) is None:
            # while we don't have a lockfile reader:
            self.install(['default'])
            #raise PBundlerException("Your bundle is not installed.")

    def enable(self, groups):
        # TODO: remove groups from method sig
        self.load_cheese()

        # reset import path
        new_path = [sys.path[0]]
        new_path.extend(PyPath.clean_path())
        PyPath.replace_sys_path(new_path)

        enabled_path = []
        for pkg in self.required.values():
            pkg.dist.activate(enabled_path)

        new_path = [sys.path[0]]
        new_path.extend(enabled_path)
        new_path.extend(PyPath.clean_path())
        PyPath.replace_sys_path(new_path)

        self._check_sys_modules_is_clean()

    def exec_enabled(self, command):
        # We don't actually need all the cheese loaded, but it's great to
        # fail fast.
        self.load_cheese()

        import pkg_resources
        dist = pkg_resources.get_distribution('pbundler')
        activation_path = os.path.join(dist.location, 'pbundler', 'activation')
        os.putenv('PYTHONPATH', activation_path)
        os.putenv('PBUNDLER_CHEESEFILE', self.cheesefile.path)
        os.execvp(command[0], command)

    def get_cheese(self, name, default=None):
        self.load_cheese()
        return self.required.get(name, default)

########NEW FILE########
__FILENAME__ = cheesefile
from __future__ import print_function
from __future__ import absolute_import

__all__ = ['Cheesefile', 'Cheese', 'CHEESEFILE', 'CHEESEFILE_LOCK']

import os
from contextlib import contextmanager
import pkg_resources

from . import PBundlerException
from .dsl import DslRunner
from .sources import CheeseshopSource


CHEESEFILE = 'Cheesefile'
CHEESEFILE_LOCK = 'Cheesefile.lock'


class Cheese(object):
    """A package. A distribution. A requirement. A cheese.
    Whatever you want to call it.
    """

    def __init__(self, name, version_req, platform=None, path=None, source=None):
        self.name = name
        self.version_req = version_req
        self.platform = platform
        self.path = path
        self.source = source
        self.dist = None
        self._requirements = None

    @classmethod
    def from_requirement(cls, req):
        version = ','.join([op + ver for (op, ver) in req.specs])
        if version == '':
            version = None
        return cls(req.project_name, version, None, None)

    def applies_to(self, platform):
        if self.platform is None:
            return True
        return (self.platform == platform)

    def is_exact_version(self):
        return self.version_req.startswith('==')

    @property
    def exact_version(self):
        """Returns the version number, without an operator. If the operator
        was not '==', an Exception is raised."""

        if not self.is_exact_version():
            raise Exception("Cheese %s didn't have an exact version (%s)" %
                            (self.name, self.version_req))

        return self.version_req[2:]

    def use_from(self, version, source):
        self.version_req = '==' + version
        self.source = source

    def use_dist(self, dist):
        self.dist = dist

    def requirement(self):
        """Return pkg_resources.Requirement matching this object."""

        version = self.version_req
        if version is None:
            version = ''
        else:
            if not ('>' in version or '<' in version or '=' in version):
                version = '==' + version
        return pkg_resources.Requirement.parse(self.name + version)

    @property
    def requirements(self):
        assert(self.dist is not None)
        if self._requirements is None:
            self._requirements = [Cheese.from_requirement(dep) for dep in self.dist.requires()]
        return self._requirements


class CheesefileContext(object):
    """DSL Context class. All methods not starting with an underscore
    are exposed to the Cheesefile."""

    def __init__(self):
        self.sources = []
        self.groups = {}
        with self.group('default'):
            pass

    def __str__(self):
        s = []

        for source in self.sources:
            s.append('source(%r)' % source)
        s.append('')

        for name, group in self.groups.items():
            indent = '  '
            if name == 'default':
                indent = ''
            else:
                s.append('with group(%r):' % name)
            for egg in group:
                s.append(indent + ('%r' % (egg,)))
            s.append('')

        return "\n".join(s)

    def source(self, name_or_url):
        if name_or_url == 'pypi':
            name_or_url = 'http://pypi.python.org/pypi'

        self.sources.append(CheeseshopSource(name_or_url))

    @contextmanager
    def group(self, name):
        self.current_group = name
        self.groups[name] = self.groups.get(name, [])
        yield
        self.current_group = 'default'

    def req(self, name, version=None, platform=None, path=None):
        self.groups[self.current_group].append(
            Cheese(name, version, platform, path)
            )


class Cheesefile(object):
    """Parses and holds Cheesefiles."""

    def __init__(self, path):
        self.path = path

    @classmethod
    def generate_empty_file(cls, path):
        filepath = os.path.join(path, CHEESEFILE)
        if os.path.exists(filepath):
            raise PBundlerException("Cowardly refusing, as %s already exists here." %
                                    (CHEESEFILE,))
        print("Writing new %s to %s" % (CHEESEFILE, filepath))
        with open(filepath, "w") as f:
            f.write("# PBundler Cheesefile\n")
            f.write("\n")
            f.write("source(\"pypi\")\n")
            f.write("\n")
            f.write("# req(\"Flask\")\n")
            f.write("\n")

    def parse(self):
        runner = DslRunner(CheesefileContext)
        ctx = runner.execfile(self.path)
        for attr, val in ctx.__dict__.items():
            self.__setattr__(attr, val)

    def collect(self, groups, platform):
        collection = {}
        groups = [group for name, group in self.groups.iteritems() if name in groups]
        for pkgs in groups:
            for pkg in pkgs:
                if pkg.applies_to(platform):
                    collection[pkg.name] = pkg
        return collection


class CheesefileLockContext(object):
    """DSL Context class. All methods not starting with an underscore
    are exposed to the Cheesefile.lock."""

    def __init__(self):
        self.cheesefile_data = []
        self.from_source_data = {}

    @contextmanager
    def from_source(self, url):
        self.from_source_data[url] = []
        self.current_req_context = self.from_source_data[url]
        yield
        self.current_req_context = None

    @contextmanager
    def Cheesefile(self):
        self.current_req_context = self.cheesefile_data
        yield
        self.current_req_context = None

    def req(self, name, version, platform=None, path=None):
        req = Cheese(name, version, platform, path)
        self.current_req_context.append(req)

    @contextmanager
    def resolved_req(self, name, version):
        prev_req_context = self.current_req_context
        solved_req = Cheese(name, version)
        self.current_req_context = solved_req.requirements
        yield
        self.current_req_context = prev_req_context
        self.current_req_context.append(solved_req)


class CheesefileLock(object):
    """Parses and holds Cheesefile.locks."""

    def __init__(self, path):
        self.path = path

    def parse(self):
        runner = DslRunner(CheesefileLockContext)
        ctx = runner.execfile(self.path)
        for attr, val in ctx.__dict__.items():
            self.__setattr__(attr, val)

########NEW FILE########
__FILENAME__ = cli
from __future__ import print_function
from __future__ import absolute_import

__all__ = ['PBCli', 'pbcli', 'pbpy']

import os
import sys
import traceback

import pbundler


USAGE = """
pbundle                  Copyright 2012,2013 Christian Hofstaedtler
pbundle Usage:
  pbundle [install]    - Install the packages from Cheesefile
  pbundle update       - Update dependencies to their latest versions
  pbundle init         - Create a basic Cheesefile
  pbundle exec program - Run "program" in activated environment
  pbundle console      - Start an interactive activated python session

To auto-enable your scripts, use "#!/usr/bin/env pbundle-py" as the
shebang line. Alternatively:
  require pbundler
  pbundler.PBundler.setup()

Website:      https://github.com/zeha/pbundler
Report bugs:  https://github.com/zeha/pbundler/issues
"""


class PBCli():
    def __init__(self):
        self._bundle = None

    @property
    def bundle(self):
        if not self._bundle:
            self._bundle = pbundler.PBundler.load_bundle()
        return self._bundle

    def handle_args(self, argv):
        args = argv[1:]
        command = "install"
        if args:
            command = args.pop(0)
        if command in ['--help', '-h']:
            command = 'help'
        if command == '--version':
            command = 'version'
        if 'cmd_' + command in PBCli.__dict__:
            return PBCli.__dict__['cmd_' + command](self, args)
        else:
            raise pbundler.PBundlerException("Could not find command \"%s\"." %
                                             (command,))

    def run(self, argv):
        try:
            return self.handle_args(argv)
        except pbundler.PBundlerException as ex:
            print("E:", str(ex))
            return 1
        except Exception as ex:
            print("E: Internal error in pbundler:")
            print("  ", ex)
            traceback.print_exc()
            return 120

    def cmd_help(self, args):
        print(USAGE.strip())

    def cmd_init(self, args):
        path = os.getcwd()
        if len(args) > 0:
            path = os.path.abspath(args[0])
        pbundler.cheesefile.Cheesefile.generate_empty_file(path)

    def cmd_install(self, args):
        self.bundle.install(['default'])

    def cmd_update(self, args):
        self.bundle.update()

    def cmd_exec(self, args):
        return self.bundle.exec_enabled(args)

    def cmd_console(self, args):
        plain = False
        for arg in args[:]:
            if arg == '--':
                args.pop(0)
                break
            elif arg == '--plain':
                args.pop(0)
                plain = True
            else:
                break

        command = [sys.executable]
        if not plain:
            # If ipython is part of the bundle, use it.
            for shell_name in ['ipython']:
                shell = self.bundle.get_cheese(shell_name)
                if not shell:
                    continue
                # FIXME: need a way to look this path up.
                command = [os.path.join(shell.dist.location, "..", "bin", shell_name)]

        command.extend(args)
        return self.bundle.exec_enabled(command)

    def cmd_repl(self, args):
        #self.bundle.validate_requirements()
        import pbundler.repl
        pbundler.repl.run()

    def cmd_version(self, args):
        import pkg_resources
        dist = pkg_resources.get_distribution('pbundler')
        print(dist)
        return 0


def pbcli():
    sys.exit(PBCli().run(sys.argv))


def pbpy():
    argv = [sys.argv[0], "console", "--plain", "--"] + sys.argv[1:]
    sys.exit(PBCli().run(argv))

########NEW FILE########
__FILENAME__ = dsl
from __future__ import print_function
from __future__ import absolute_import

__all__ = ['DslRunner']


class DslRunner(object):
    """Runs Python code in the context of a class.

    Public methods will be exposed to the DSL code.
    """

    def __init__(self, contextclass):
        self.contextclass = contextclass

    def make_context(self):
        ctx = self.contextclass()
        ctxmap = {}
        method_names = [fun for fun in ctx.__class__.__dict__ if not fun.startswith('_')]
        methods = ctx.__class__.__dict__

        def method_caller(fun):
            unbound = methods[fun]
            def wrapped(*args, **kw):
                args = (ctx,) + args
                return unbound(*args, **kw)
            return wrapped

        for fun in method_names:
            ctxmap[fun] = method_caller(fun)

        return (ctx, ctxmap)

    def execfile(self, filename):
        ctx, ctxmap = self.make_context()
        execfile(filename, {}, ctxmap)
        return ctx

########NEW FILE########
__FILENAME__ = exceptions
from __future__ import print_function
from __future__ import absolute_import

__all__ = ['PBundlerException']


class PBundlerException(Exception):
    pass

########NEW FILE########
__FILENAME__ = localstore
from __future__ import print_function
from __future__ import absolute_import

__all__ = ['LocalStore']

import os
import platform
import pkg_resources
import glob
import subprocess
import sys
import tempfile

from . import PBundlerException
from .util import PBFile, PBArchive


class LocalStore(object):

    def __init__(self, path=None):
        if path is None:
            if os.getenv('PBUNDLER_STORE'):
                self.path = os.getenv('PBUNDLER_STORE')
            else:
                self.path = os.path.expanduser('~/.cache/pbundler/')
        else:
            self.path = path

        PBFile.ensure_dir(self.path)
        self._temp_path = None
        self.python_name = ('%s-%s' % (platform.python_implementation(),
                            ('.'.join(platform.python_version_tuple()[:-1]))))

    @property
    def cache_path(self):
        path = os.path.join(self.path, 'cache')
        PBFile.ensure_dir(path)
        return path

    @property
    def temp_path(self):
        if not self._temp_path:
            self._temp_path = tempfile.mkdtemp(prefix='pbundle')
        return self._temp_path

    def get(self, cheese):
        lib_path = self.path_for(cheese, 'lib')
        if os.path.exists(lib_path):
            dists = [d for d in pkg_resources.find_distributions(lib_path, only=True)]
            if len(dists) == 1:
                return dists[0]

        return None

    def path_for(self, cheese, sub=None):
        path = [self.path, 'cheese', self.python_name,
                '%s-%s' % (cheese.name, cheese.exact_version)]
        if sub is not None:
            path.append(sub)
        return os.path.join(*path)

    def prepare(self, cheese, source):
        """Download and unpack the cheese."""

        print("Downloading %s %s..." % (cheese.name, cheese.exact_version))

        # path we use to install _from_
        source_path = os.path.join(self.temp_path, cheese.name, cheese.exact_version)

        sdist_filepath = source.download(cheese, self.cache_path)
        PBArchive(sdist_filepath).unpack(source_path)

        # FIXME: ugly hack to get the unpacked dir.
        # actually we should say unpack(..., strip_first_dir=True)
        source_path = glob.glob(source_path + '/*')[0]
        return UnpackedSdist(source_path)

    def install(self, cheese, unpackedsdist):
        print("Installing %s %s..." % (cheese.name, cheese.exact_version))
        cheese_path = self.path_for(cheese)
        lib_path = self.path_for(cheese, 'lib')
        PBFile.ensure_dir(lib_path)
        unpackedsdist.run_setup_py(['install',
               '--root', cheese_path,
               '--install-lib', 'lib',
               '--install-scripts', 'bin'], {'PYTHONPATH': lib_path}, "Installing")
        return self.get(cheese)


class UnpackedSdist(object):

    def __init__(self, path):
        self.path = path
        self.is_sdist = True

    def requires(self):
        self.run_setup_py(['egg_info'], {}, "Preparing", raise_on_fail=False)
        egg_info_path = glob.glob(self.path + '/*.egg-info')
        if not egg_info_path:
            return []

        requires_path = os.path.join(egg_info_path[0], 'requires.txt')
        if not os.path.exists(requires_path):
            return []

        requires_raw = []
        with file(requires_path, 'rt') as f:
            requires_raw = f.readlines()

        # requires.txt MAY contain sections, and we ignore all of them except
        # the unnamed section.
        sections = [line for line in requires_raw if line.startswith('[')]
        if sections:
            requires_raw = requires_raw[0:requires_raw.index(sections[0])]
        else:
            requires_raw = requires_raw

        return [req for req in pkg_resources.parse_requirements(requires_raw)]

    def run_setup_py(self, args, envvars, step, raise_on_fail=True):
        setup_cwd = self.path
        cmd = [sys.executable, 'setup.py'] + args
        env = dict(os.environ)
        if envvars:
            env.update(envvars)

        with tempfile.NamedTemporaryFile() as logfile:
            proc = subprocess.Popen(cmd,
                                    cwd=setup_cwd,
                                    close_fds=True,
                                    stdin=subprocess.PIPE,
                                    stdout=logfile,
                                    stderr=subprocess.STDOUT,
                                    env=env)
            proc.stdin.close()
            rv = proc.wait()

            if rv != 0 and raise_on_fail:
                logfile.seek(0, os.SEEK_SET)
                print(logfile.read())
                msg = ("%s failed with exit code %d. Source files have been" +
                       " left in %r for you to examine.\nCommand line was: %s") % (
                           step, rv, setup_cwd, cmd)
                raise PBundlerException(msg)

########NEW FILE########
__FILENAME__ = pypath
from __future__ import print_function
from __future__ import absolute_import

__all__ = ['PyPath']

import ctypes
import sys
import pkg_resources


class PyPath:

    @staticmethod
    def builtin_path():
        """Consumes the C API Py_GetPath function to return the path
        built into the Python interpreter.
        This already takes care of PYTHONPATH.

        Note: actually Py_GetPath dynamically computes the path on
        the first call (which happens during startup).
        """

        Py_GetPath = ctypes.pythonapi.Py_GetPath
        if sys.version_info[0] >= 3:
            # Unicode
            Py_GetPath.restype = ctypes.c_wchar_p
        else:
            Py_GetPath.restype = ctypes.c_char_p

        return Py_GetPath().split(':')

    @staticmethod
    def path_for_pkg_name(pkg_name):
        pkgs = [pkg for pkg in pkg_resources.working_set
                if pkg.project_name == pkg_name]
        if len(pkgs) == 0:
            return None
        return pkgs[0].location

    @classmethod
    def bundler_path(cls):
        """Returns the path to PBundler itself."""

        return cls.path_for_pkg_name("pbundler")

    @classmethod
    def clean_path(cls):
        """Return a list containing the builtin_path and bundler_path.
        Before replacing sys.path with this, realize that sys.path[0]
        will be missing from this list.
        """

        path = [cls.bundler_path()] + cls.builtin_path()
        return path

    @classmethod
    def replace_sys_path(cls, new_path):
        for path in sys.path[:]:
            sys.path.remove(path)
        sys.path.extend(new_path)


PyPath.initial_sys_path_0 = sys.path[0]

########NEW FILE########
__FILENAME__ = repl
from __future__ import print_function
from __future__ import absolute_import

__all__ = ['run']

import PBundler
import traceback
import sys
import code
import rlcompleter
import readline
readline.parse_and_bind("tab: complete")

# readline magically hooks into code.InteractiveConsole somehow.
# don't ask.


def run():
    """minimal interpreter, mostly for debugging purposes."""

    console = code.InteractiveConsole()
    console.interact("PBundler REPL on Python" + str(sys.version))

########NEW FILE########
__FILENAME__ = sources
from __future__ import print_function
from __future__ import absolute_import

__all__ = ['CheeseshopSource']

import os
import pkg_resources
import xmlrpclib

from . import PBundlerException
from .util import PBDownloader


class CheeseshopSource(object):

    def __init__(self, url):
        self.url = url
        if self.url.endswith('/'):
            self.url = self.url[:-1]

    def _src(self):
        return xmlrpclib.ServerProxy(self.url, xmlrpclib.Transport())

    def available_versions(self, cheese):
        versions = self._src().package_releases(cheese.name, True)
        return versions

    def requires(self, cheese):
        d = self._src().release_data(cheese.name, cheese.exact_version)
        return d["requires"]

    def download(self, cheese, target_path):
        urls = self._src().release_urls(cheese.name, cheese.exact_version)
        filename = None
        url = None
        remote_digest = None
        for urlinfo in urls:
            if urlinfo['packagetype'] != 'sdist':
                continue
            filename = urlinfo['filename']
            url = urlinfo['url']
            remote_digest = urlinfo['md5_digest']
            break

        if not url:
            print(repr(urls))

            raise PBundlerException("Did not find an sdist for %s %s on %s" % (cheese.name, cheese.exact_version, self.url))

        target_file = os.path.join(target_path, filename)
        PBDownloader.download_checked(url, target_file, remote_digest)
        return target_file


class FilesystemSource(object):

    def __init__(self, path):
        self.path = os.path.expanduser(path)

    def available_versions(self, cheese):
        dists = pkg_resources.find_distributions(self.path, only=True)
        return [dist.version for dist in dists]

    def get_distribution(self, cheese):
        dists = pkg_resources.find_distributions(self.path, only=True)
        return [dist for dist in dists][0]

########NEW FILE########
__FILENAME__ = util
from __future__ import print_function
from __future__ import absolute_import

__all__ = ['PBFile', 'PBDownloader', 'PBArchive']

import os
from hashlib import md5
from urllib2 import Request, urlopen
import subprocess
import shutil
import pkg_resources

from . import PBundlerException

# Utility functions. Not for public consumption.
# If you need some of these exposed, please talk to us.


class PBFile(object):

    @staticmethod
    def read(path, filename):
        try:
            with open(os.path.join(path, filename), 'r') as f:
                return f.read()
        except:
            return None

    @staticmethod
    def find_upwards(fn, root=os.path.realpath(os.curdir)):
        if os.path.exists(os.path.join(root, fn)):
            return root
        up = os.path.abspath(os.path.join(root, '..'))
        if up == root:
            return None
        return PBFile.find_upwards(fn, up)

    @staticmethod
    def ensure_dir(path):
        if not os.path.exists(path):
            os.makedirs(path)

    @staticmethod
    def md5_digest(path):
        digest = md5()
        with file(path, 'rb') as f:
            digest.update(f.read())
        return digest.hexdigest()


class PBDownloader(object):

    @classmethod
    def download_checked(cls, url, target_file, expected_digest):
        if os.path.exists(target_file):
            # file already exists, see if we can use it.
            if PBFile.md5_digest(target_file) == expected_digest:
                # local file is ok
                return
            else:
                os.unlink(target_file)

        user_agent = ("pbunder/%s " % (cls.my_version) +
                      "(http://github.com/zeha/pbundler/issues)")

        try:
            req = Request(url)
            req.add_header("User-Agent", user_agent)
            req.add_header("Accept", "*/*")
            with file(target_file, 'wb') as f:
                sock = urlopen(req)
                try:
                    f.write(sock.read())
                finally:
                    sock.close()

        except Exception as ex:
            raise PBundlerException("Downloading %s failed (%s)" % (url, ex))

        local_digest = PBFile.md5_digest(target_file)
        if local_digest != expected_digest:
            os.unlink(target_file)
            msg = ("Downloading %s failed (MD5 Digest %s did not match expected %s)" %
                   (url, local_digest, expected_digest))
            raise PBundlerException(msg)
        else:
            # local file is ok
            return

try:
    PBDownloader.my_version = pkg_resources.get_distribution('pbundler').version
except:
    PBDownloader.my_version = 'DEV'


class PBArchive(object):

    def __init__(self, path):
        self.path = path
        self.filetype = os.path.splitext(path)[1][1:]
        if self.filetype in ['tgz', 'gz', 'bz2', 'xz']:
            self.filetype = 'tar'
        if self.filetype not in ['zip', 'tar']:
            raise PBundlerException("Unsupported Archive file: %s" % (self.path))

    def unpack(self, destination):
        if os.path.exists(destination):
            shutil.rmtree(destination)
        PBFile.ensure_dir(destination)
        # FIXME: implement this stuff in pure python
        if self.filetype == 'zip':
            subprocess.call(['unzip', '-q', self.path, '-d', destination])
        elif self.filetype == 'tar':
            subprocess.call(['tar', 'xf', self.path, '-C', destination])

########NEW FILE########
