__FILENAME__ = pythonrc

scheme = 'unix'
#extra_paths = ['/path/to/inheriting/site-packages/',] # add some if you need access to other venvs


########NEW FILE########
__FILENAME__ = boot
import sys
from os import path

import rvirtualenvinstall.install
from rvirtualenvinstall import scheme
import pythonrc

base = path.abspath(path.dirname(pythonrc.__file__))

# real_prefix is useful for pip and uninstalling system pkgs
sys.real_prefix = sys.prefix
# python uses this almost everywhere
sys.prefix = base

this_site_packages = [
    scheme.get_scheme(pythonrc.scheme, 'purelib'),
    scheme.get_scheme(pythonrc.scheme, 'platlib'),
]

scheme.add_to_path(getattr(pythonrc, 'extra_paths', []))
scheme.add_to_path(this_site_packages)


########NEW FILE########
__FILENAME__ = develop
import setuptools
from setuptools.command.develop import develop as _develop


class develop(_develop):
    description = "rvirtualenv's %s" % _develop.description
    def run(self):
        print('WTF')

# don't know why isn't it overriden by entry_points
setuptools.command.develop.develop = develop


########NEW FILE########
__FILENAME__ = install
import distutils
from distutils.command.install import install as _install

import pythonrc
from rvirtualenvinstall import scheme


class install(_install):
    description = "rvirtualenv's %s" % _install.description
    def finalize_options(self):
        _install.finalize_options(self)

        vars = {'dist_name': self.distribution.get_name(),}
        self.install_purelib = scheme.get_scheme(pythonrc.scheme, 'purelib')
        self.install_platlib = scheme.get_scheme(pythonrc.scheme, 'purelib')
        self.install_headers = scheme.get_scheme(pythonrc.scheme, 'headers', vars=vars)
        self.install_scripts = scheme.get_scheme(pythonrc.scheme, 'scripts')
        self.install_data = scheme.get_scheme(pythonrc.scheme, 'data')

        if self.distribution.ext_modules: # has extensions: non-pure
            self.install_lib = self.install_platlib
        else:
            self.install_lib = self.install_purelib

# monkey patch for distutils
distutils.command.install.install = install


########NEW FILE########
__FILENAME__ = scheme
import sys
from os import path
import site
from distutils.util import subst_vars

INSTALL_SCHEMES = {
    'custom': {
        'purelib': '$base/lib/python/site-packages',
        'platlib': '$base/lib/python$py_version_short/site-packages',
        'headers': '$base/include/python$py_version_short/$dist_name',
        'scripts': '$base/bin',
        'data'   : '$base',
        },
    'unix': {
        'purelib': '$base/lib/python$py_version_short/site-packages',
        'platlib': '$base/lib/python$py_version_short/site-packages',
        'headers': '$base/include/python$py_version_short/$dist_name',
        'scripts': '$base/bin',
        'data'   : '$base',
        },
    'windows': {
        'purelib': '$base/Lib/site-packages',
        'platlib': '$base/Lib/site-packages',
        'headers': '$base/Include/$dist_name',
        'scripts': '$base/Scripts',
        'data'   : '$base',
        },
    'os2': {
        'purelib': '$base/Lib/site-packages',
        'platlib': '$base/Lib/site-packages',
        'headers': '$base/Include/$dist_name',
        'scripts': '$base/Scripts',
        'data'   : '$base',
        },
    'darwin': {
        'purelib': '$base/Library/Python$py_version_short/site-packages',
        'platlib': '$base/Library/Python$py_version_short/site-packages',
        'headers': '$base/Include/$dist_name',
        'scripts': '$base/bin',
        'data'   : '$base',
        },
    }

def guess_scheme():
    return 'unix'

def get_scheme(platform, what, vars={}):
    # TODO: maybe use syslinux.get_path in next versions
    replace = {
        'base': sys.prefix,
        'py_version_short': sys.version[:3],
        'dist_name': 'UNKNOWN',
    }
    replace.update(vars)
    line = INSTALL_SCHEMES[platform][what]
    line = path.join(*line.split('/'))
    return subst_vars(line, replace)

def add_to_path(new_paths):
    "add dirs to the beginnig of sys.path"
    __plen = len(sys.path)
    for i in new_paths:
        if i not in sys.path:
            site.addsitedir(i)
    new = sys.path[__plen:]
    del sys.path[__plen:]
    sys.path[0:0] = new


########NEW FILE########
__FILENAME__ = site
def __boot():
    import sys, imp, os, os.path   
    PYTHONPATH = os.environ.get('PYTHONPATH')
    if PYTHONPATH is None or (sys.platform=='win32' and not PYTHONPATH):
        PYTHONPATH = []
    else:
        PYTHONPATH = PYTHONPATH.split(os.pathsep)

    pic = getattr(sys,'path_importer_cache',{})
    stdpath = sys.path[len(PYTHONPATH):]
    mydir = os.path.dirname(__file__)
    #print "searching",stdpath,sys.path

    for item in stdpath:
        if item==mydir or not item:
            continue    # skip if current dir. on Windows, or my own directory
        importer = pic.get(item)
        if importer is not None:
            loader = importer.find_module('site')
            if loader is not None:
                # This should actually reload the current module
                loader.load_module('site')
                break
        else:
            try:
                stream, path, descr = imp.find_module('site',[item])
            except ImportError:
                continue
            if stream is None:
                continue
            try:
                # This should actually reload the current module
                imp.load_module('site',stream,path,descr)
            finally:
                stream.close()
            break
    else:
        raise ImportError("Couldn't find the real 'site' module")

    #print "loaded", __file__

    known_paths = dict([(makepath(item)[1],1) for item in sys.path]) # 2.2 comp

    oldpos = getattr(sys,'__egginsert',0)   # save old insertion position
    sys.__egginsert = 0                     # and reset the current one

    for item in PYTHONPATH:
        addsitedir(item)

    sys.__egginsert += oldpos           # restore effective old position
    
    d,nd = makepath(stdpath[0])
    insert_at = None
    new_path = []

    for item in sys.path:
        p,np = makepath(item)

        if np==nd and insert_at is None:
            # We've hit the first 'system' path entry, so added entries go here
            insert_at = len(new_path)

        if np in known_paths or insert_at is None:
            new_path.append(item)
        else:
            # new path after the insert point, back-insert it
            new_path.insert(insert_at, item)
            insert_at += 1
            
    sys.path[:] = new_path

    import rvirtualenvinstall.boot

if __name__=='site':    
    __boot()
    del __boot
    








########NEW FILE########
__FILENAME__ = install

import distutils.command.install
import distutils.core
from distutils import command, core

i = command.install.install(core.Distribution())

i.initialize_options()
i.finalize_options()

for a in dir(i):
    if a.startswith('install_'):
        print '%s: %s' % (a, getattr(i, a))


########NEW FILE########
__FILENAME__ = sysconfig27
"""Provide access to Python's configuration information.

"""
import sys
import os
from os.path import pardir, realpath
from string import Template

_INSTALL_SCHEMES = {
    'posix_prefix': {
        'stdlib': '{base}/lib/python{py_version_short}',
        'platstdlib': '{platbase}/lib/python{py_version_short}',
        'purelib': '{base}/lib/python{py_version_short}/site-packages',
        'platlib': '{platbase}/lib/python{py_version_short}/site-packages',
        'include': '{base}/include/python{py_version_short}',
        'platinclude': '{platbase}/include/python{py_version_short}',
        'scripts': '{base}/bin',
        'data': '{base}',
        },
    'posix_home': {
        'stdlib': '{base}/lib/python',
        'platstdlib': '{base}/lib/python',
        'purelib': '{base}/lib/python',
        'platlib': '{base}/lib/python',
        'include': '{base}/include/python',
        'platinclude': '{base}/include/python',
        'scripts': '{base}/bin',
        'data'   : '{base}',
        },
    'nt': {
        'stdlib': '{base}/Lib',
        'platstdlib': '{base}/Lib',
        'purelib': '{base}/Lib/site-packages',
        'platlib': '{base}/Lib/site-packages',
        'include': '{base}/Include',
        'platinclude': '{base}/Include',
        'scripts': '{base}/Scripts',
        'data'   : '{base}',
        },
    'os2': {
        'stdlib': '{base}/Lib',
        'platstdlib': '{base}/Lib',
        'purelib': '{base}/Lib/site-packages',
        'platlib': '{base}/Lib/site-packages',
        'include': '{base}/Include',
        'platinclude': '{base}/Include',
        'scripts': '{base}/Scripts',
        'data'   : '{base}',
        },
    'os2_home': {
        'stdlib': '{userbase}/lib/python{py_version_short}',
        'platstdlib': '{userbase}/lib/python{py_version_short}',
        'purelib': '{userbase}/lib/python{py_version_short}/site-packages',
        'platlib': '{userbase}/lib/python{py_version_short}/site-packages',
        'include': '{userbase}/include/python{py_version_short}',
        'scripts': '{userbase}/bin',
        'data'   : '{userbase}',
        },
    'nt_user': {
        'stdlib': '{userbase}/Python{py_version_nodot}',
        'platstdlib': '{userbase}/Python{py_version_nodot}',
        'purelib': '{userbase}/Python{py_version_nodot}/site-packages',
        'platlib': '{userbase}/Python{py_version_nodot}/site-packages',
        'include': '{userbase}/Python{py_version_nodot}/Include',
        'scripts': '{userbase}/Scripts',
        'data'   : '{userbase}',
        },
    'posix_user': {
        'stdlib': '{userbase}/lib/python{py_version_short}',
        'platstdlib': '{userbase}/lib/python{py_version_short}',
        'purelib': '{userbase}/lib/python{py_version_short}/site-packages',
        'platlib': '{userbase}/lib/python{py_version_short}/site-packages',
        'include': '{userbase}/include/python{py_version_short}',
        'scripts': '{userbase}/bin',
        'data'   : '{userbase}',
        },
    'osx_framework_user': {
        'stdlib': '{userbase}/lib/python',
        'platstdlib': '{userbase}/lib/python',
        'purelib': '{userbase}/lib/python/site-packages',
        'platlib': '{userbase}/lib/python/site-packages',
        'include': '{userbase}/include',
        'scripts': '{userbase}/bin',
        'data'   : '{userbase}',
        },
    }

_SCHEME_KEYS = ('stdlib', 'platstdlib', 'purelib', 'platlib', 'include',
                'scripts', 'data')
_PY_VERSION = sys.version.split()[0]
_PY_VERSION_SHORT = sys.version[:3]
_PY_VERSION_SHORT_NO_DOT = _PY_VERSION[0] + _PY_VERSION[2]
_PREFIX = os.path.normpath(sys.prefix)
_EXEC_PREFIX = os.path.normpath(sys.exec_prefix)
_CONFIG_VARS = None
_USER_BASE = None

def _safe_realpath(path):
    try:
        return realpath(path)
    except OSError:
        return path

if sys.executable:
    _PROJECT_BASE = os.path.dirname(_safe_realpath(sys.executable))
else:
    # sys.executable can be empty if argv[0] has been changed and Python is
    # unable to retrieve the real program name
    _PROJECT_BASE = _safe_realpath(os.getcwd())

if os.name == "nt" and "pcbuild" in _PROJECT_BASE[-8:].lower():
    _PROJECT_BASE = _safe_realpath(os.path.join(_PROJECT_BASE, pardir))
# PC/VS7.1
if os.name == "nt" and "\\pc\\v" in _PROJECT_BASE[-10:].lower():
    _PROJECT_BASE = _safe_realpath(os.path.join(_PROJECT_BASE, pardir, pardir))
# PC/AMD64
if os.name == "nt" and "\\pcbuild\\amd64" in _PROJECT_BASE[-14:].lower():
    _PROJECT_BASE = _safe_realpath(os.path.join(_PROJECT_BASE, pardir, pardir))

def is_python_build():
    for fn in ("Setup.dist", "Setup.local"):
        if os.path.isfile(os.path.join(_PROJECT_BASE, "Modules", fn)):
            return True
    return False

_PYTHON_BUILD = is_python_build()

if _PYTHON_BUILD:
    for scheme in ('posix_prefix', 'posix_home'):
        _INSTALL_SCHEMES[scheme]['include'] = '{projectbase}/Include'
        _INSTALL_SCHEMES[scheme]['platinclude'] = '{srcdir}'

def _format_template(s, **kwargs):
    if hasattr(s, 'format'):
        return s.format(**kwargs)
    t = Template(s.replace('{', '${'))
    return t.substitute(**kwargs)

def _subst_vars(s, local_vars):
    try:
        return _format_template(s, **local_vars)
    except KeyError:
        try:
            return _format_template(s, **os.environ)
        except KeyError, var:
            raise AttributeError('{%s}' % var)

def _extend_dict(target_dict, other_dict):
    target_keys = target_dict.keys()
    for key, value in other_dict.items():
        if key in target_keys:
            continue
        target_dict[key] = value

def _expand_vars(scheme, vars):
    res = {}
    if vars is None:
        vars = {}
    _extend_dict(vars, get_config_vars())

    for key, value in _INSTALL_SCHEMES[scheme].items():
        if os.name in ('posix', 'nt'):
            value = os.path.expanduser(value)
        res[key] = os.path.normpath(_subst_vars(value, vars))
    return res

def _get_default_scheme():
    if os.name == 'posix':
        # the default scheme for posix is posix_prefix
        return 'posix_prefix'
    return os.name

def _getuserbase():
    env_base = os.environ.get("PYTHONUSERBASE", None)
    def joinuser(*args):
        return os.path.expanduser(os.path.join(*args))

    # what about 'os2emx', 'riscos' ?
    if os.name == "nt":
        base = os.environ.get("APPDATA") or "~"
        return env_base and env_base or joinuser(base, "Python")

    if sys.platform == "darwin":
        framework = get_config_var("PYTHONFRAMEWORK")
        if framework:
            return joinuser("~", "Library", framework, "%d.%d"%(
                sys.version_info[:2]))

    return env_base and env_base or joinuser("~", ".local")


def _parse_makefile(filename, vars=None):
    """Parse a Makefile-style file.

    A dictionary containing name/value pairs is returned.  If an
    optional dictionary is passed in as the second argument, it is
    used instead of a new dictionary.
    """
    import re
    # Regexes needed for parsing Makefile (and similar syntaxes,
    # like old-style Setup files).
    _variable_rx = re.compile("([a-zA-Z][a-zA-Z0-9_]+)\s*=\s*(.*)")
    _findvar1_rx = re.compile(r"\$\(([A-Za-z][A-Za-z0-9_]*)\)")
    _findvar2_rx = re.compile(r"\${([A-Za-z][A-Za-z0-9_]*)}")

    if vars is None:
        vars = {}
    done = {}
    notdone = {}

    f = open(filename)
    try:
        lines = f.readlines()
    finally:
        f.close()

    for line in lines:
        if line.startswith('#') or line.strip() == '':
            continue
        m = _variable_rx.match(line)
        if m:
            n, v = m.group(1, 2)
            v = v.strip()
            # `$$' is a literal `$' in make
            tmpv = v.replace('$$', '')

            if "$" in tmpv:
                notdone[n] = v
            else:
                try:
                    v = int(v)
                except ValueError:
                    # insert literal `$'
                    done[n] = v.replace('$$', '$')
                else:
                    done[n] = v

    # do variable interpolation here
    while notdone:
        for name in notdone.keys():
            value = notdone[name]
            m = _findvar1_rx.search(value) or _findvar2_rx.search(value)
            if m:
                n = m.group(1)
                found = True
                if n in done:
                    item = str(done[n])
                elif n in notdone:
                    # get it on a subsequent round
                    found = False
                elif n in os.environ:
                    # do it like make: fall back to environment
                    item = os.environ[n]
                else:
                    done[n] = item = ""
                if found:
                    after = value[m.end():]
                    value = value[:m.start()] + item + after
                    if "$" in after:
                        notdone[name] = value
                    else:
                        try: value = int(value)
                        except ValueError:
                            done[name] = value.strip()
                        else:
                            done[name] = value
                        del notdone[name]
            else:
                # bogus variable reference; just drop it since we can't deal
                del notdone[name]
    # strip spurious spaces
    for k, v in done.items():
        if isinstance(v, str):
            done[k] = v.strip()

    # save the results in the global dictionary
    vars.update(done)
    return vars


def _get_makefile_filename():
    if _PYTHON_BUILD:
        return os.path.join(_PROJECT_BASE, "Makefile")
    return os.path.join(get_path('stdlib'), "config", "Makefile")


def _init_posix(vars):
    """Initialize the module as appropriate for POSIX systems."""
    # load the installed Makefile:
    makefile = _get_makefile_filename()
    try:
        _parse_makefile(makefile, vars)
    except IOError, e:
        msg = "invalid Python installation: unable to open %s" % makefile
        if hasattr(e, "strerror"):
            msg = msg + " (%s)" % e.strerror
        raise IOError(msg)

    # load the installed pyconfig.h:
    config_h = get_config_h_filename()
    try:
        f = open(config_h)
        try:
            parse_config_h(f, vars)
        finally:
            f.close()
    except IOError, e:
        msg = "invalid Python installation: unable to open %s" % config_h
        if hasattr(e, "strerror"):
            msg = msg + " (%s)" % e.strerror
        raise IOError(msg)

    # On MacOSX we need to check the setting of the environment variable
    # MACOSX_DEPLOYMENT_TARGET: configure bases some choices on it so
    # it needs to be compatible.
    # If it isn't set we set it to the configure-time value
    if sys.platform == 'darwin' and 'MACOSX_DEPLOYMENT_TARGET' in vars:
        cfg_target = vars['MACOSX_DEPLOYMENT_TARGET']
        cur_target = os.getenv('MACOSX_DEPLOYMENT_TARGET', '')
        if cur_target == '':
            cur_target = cfg_target
            os.putenv('MACOSX_DEPLOYMENT_TARGET', cfg_target)
        elif map(int, cfg_target.split('.')) > map(int, cur_target.split('.')):
            msg = ('$MACOSX_DEPLOYMENT_TARGET mismatch: now "%s" but "%s" '
                   'during configure' % (cur_target, cfg_target))
            raise IOError(msg)

    # On AIX, there are wrong paths to the linker scripts in the Makefile
    # -- these paths are relative to the Python source, but when installed
    # the scripts are in another directory.
    if _PYTHON_BUILD:
        vars['LDSHARED'] = vars['BLDSHARED']

def _init_non_posix(vars):
    """Initialize the module as appropriate for NT"""
    # set basic install directories
    vars['LIBDEST'] = get_path('stdlib')
    vars['BINLIBDEST'] = get_path('platstdlib')
    vars['INCLUDEPY'] = get_path('include')
    vars['SO'] = '.pyd'
    vars['EXE'] = '.exe'
    vars['VERSION'] = _PY_VERSION_SHORT_NO_DOT
    vars['BINDIR'] = os.path.dirname(_safe_realpath(sys.executable))

#
# public APIs
#


def parse_config_h(fp, vars=None):
    """Parse a config.h-style file.

    A dictionary containing name/value pairs is returned.  If an
    optional dictionary is passed in as the second argument, it is
    used instead of a new dictionary.
    """
    import re
    if vars is None:
        vars = {}
    define_rx = re.compile("#define ([A-Z][A-Za-z0-9_]+) (.*)\n")
    undef_rx = re.compile("/[*] #undef ([A-Z][A-Za-z0-9_]+) [*]/\n")

    while True:
        line = fp.readline()
        if not line:
            break
        m = define_rx.match(line)
        if m:
            n, v = m.group(1, 2)
            try: v = int(v)
            except ValueError: pass
            vars[n] = v
        else:
            m = undef_rx.match(line)
            if m:
                vars[m.group(1)] = 0
    return vars

def get_config_h_filename():
    """Returns the path of pyconfig.h."""
    if _PYTHON_BUILD:
        if os.name == "nt":
            inc_dir = os.path.join(_PROJECT_BASE, "PC")
        else:
            inc_dir = _PROJECT_BASE
    else:
        inc_dir = get_path('platinclude')
    return os.path.join(inc_dir, 'pyconfig.h')

def get_scheme_names():
    """Returns a tuple containing the schemes names."""
    schemes = _INSTALL_SCHEMES.keys()
    schemes.sort()
    return tuple(schemes)

def get_path_names():
    """Returns a tuple containing the paths names."""
    return _SCHEME_KEYS

def get_paths(scheme=_get_default_scheme(), vars=None, expand=True):
    """Returns a mapping containing an install scheme.

    ``scheme`` is the install scheme name. If not provided, it will
    return the default scheme for the current platform.
    """
    if expand:
        return _expand_vars(scheme, vars)
    else:
        return _INSTALL_SCHEMES[scheme]

def get_path(name, scheme=_get_default_scheme(), vars=None, expand=True):
    """Returns a path corresponding to the scheme.

    ``scheme`` is the install scheme name.
    """
    return get_paths(scheme, vars, expand)[name]

def get_config_vars(*args):
    """With no arguments, return a dictionary of all configuration
    variables relevant for the current platform.

    On Unix, this means every variable defined in Python's installed Makefile;
    On Windows and Mac OS it's a much smaller set.

    With arguments, return a list of values that result from looking up
    each argument in the configuration variable dictionary.
    """
    import re
    global _CONFIG_VARS
    if _CONFIG_VARS is None:
        _CONFIG_VARS = {}
        # Normalized versions of prefix and exec_prefix are handy to have;
        # in fact, these are the standard versions used most places in the
        # Distutils.
        _CONFIG_VARS['prefix'] = _PREFIX
        _CONFIG_VARS['exec_prefix'] = _EXEC_PREFIX
        _CONFIG_VARS['py_version'] = _PY_VERSION
        _CONFIG_VARS['py_version_short'] = _PY_VERSION_SHORT
        _CONFIG_VARS['py_version_nodot'] = _PY_VERSION[0] + _PY_VERSION[2]
        _CONFIG_VARS['base'] = _PREFIX
        _CONFIG_VARS['platbase'] = _EXEC_PREFIX
        _CONFIG_VARS['projectbase'] = _PROJECT_BASE

        if os.name in ('nt', 'os2'):
            _init_non_posix(_CONFIG_VARS)
        if os.name == 'posix':
            _init_posix(_CONFIG_VARS)

        # Setting 'userbase' is done below the call to the
        # init function to enable using 'get_config_var' in
        # the init-function.
        _CONFIG_VARS['userbase'] = _getuserbase()

        if 'srcdir' not in _CONFIG_VARS:
            _CONFIG_VARS['srcdir'] = _PROJECT_BASE

        # Convert srcdir into an absolute path if it appears necessary.
        # Normally it is relative to the build directory.  However, during
        # testing, for example, we might be running a non-installed python
        # from a different directory.
        if _PYTHON_BUILD and os.name == "posix":
            base = _PROJECT_BASE
            try:
                cwd = os.getcwd()
            except OSError:
                cwd = None
            if (not os.path.isabs(_CONFIG_VARS['srcdir']) and
                base != cwd):
                # srcdir is relative and we are not in the same directory
                # as the executable. Assume executable is in the build
                # directory and make srcdir absolute.
                srcdir = os.path.join(base, _CONFIG_VARS['srcdir'])
                _CONFIG_VARS['srcdir'] = os.path.normpath(srcdir)

        if sys.platform == 'darwin':
            kernel_version = os.uname()[2] # Kernel version (8.4.3)
            major_version = int(kernel_version.split('.')[0])

            if major_version < 8:
                # On Mac OS X before 10.4, check if -arch and -isysroot
                # are in CFLAGS or LDFLAGS and remove them if they are.
                # This is needed when building extensions on a 10.3 system
                # using a universal build of python.
                for key in ('LDFLAGS', 'BASECFLAGS',
                        # a number of derived variables. These need to be
                        # patched up as well.
                        'CFLAGS', 'PY_CFLAGS', 'BLDSHARED'):
                    flags = _CONFIG_VARS[key]
                    flags = re.sub('-arch\s+\w+\s', ' ', flags)
                    flags = re.sub('-isysroot [^ \t]*', ' ', flags)
                    _CONFIG_VARS[key] = flags
            else:
                # Allow the user to override the architecture flags using
                # an environment variable.
                # NOTE: This name was introduced by Apple in OSX 10.5 and
                # is used by several scripting languages distributed with
                # that OS release.
                if 'ARCHFLAGS' in os.environ:
                    arch = os.environ['ARCHFLAGS']
                    for key in ('LDFLAGS', 'BASECFLAGS',
                        # a number of derived variables. These need to be
                        # patched up as well.
                        'CFLAGS', 'PY_CFLAGS', 'BLDSHARED'):

                        flags = _CONFIG_VARS[key]
                        flags = re.sub('-arch\s+\w+\s', ' ', flags)
                        flags = flags + ' ' + arch
                        _CONFIG_VARS[key] = flags

                # If we're on OSX 10.5 or later and the user tries to
                # compiles an extension using an SDK that is not present
                # on the current machine it is better to not use an SDK
                # than to fail.
                #
                # The major usecase for this is users using a Python.org
                # binary installer  on OSX 10.6: that installer uses
                # the 10.4u SDK, but that SDK is not installed by default
                # when you install Xcode.
                #
                CFLAGS = _CONFIG_VARS.get('CFLAGS', '')
                m = re.search('-isysroot\s+(\S+)', CFLAGS)
                if m is not None:
                    sdk = m.group(1)
                    if not os.path.exists(sdk):
                        for key in ('LDFLAGS', 'BASECFLAGS',
                             # a number of derived variables. These need to be
                             # patched up as well.
                            'CFLAGS', 'PY_CFLAGS', 'BLDSHARED'):

                            flags = _CONFIG_VARS[key]
                            flags = re.sub('-isysroot\s+\S+(\s|$)', ' ', flags)
                            _CONFIG_VARS[key] = flags

    if args:
        vals = []
        for name in args:
            vals.append(_CONFIG_VARS.get(name))
        return vals
    else:
        return _CONFIG_VARS

def get_config_var(name):
    """Return the value of a single variable using the dictionary returned by
    'get_config_vars()'.

    Equivalent to get_config_vars().get(name)
    """
    return get_config_vars().get(name)

def get_platform():
    """Return a string that identifies the current platform.

    This is used mainly to distinguish platform-specific build directories and
    platform-specific built distributions.  Typically includes the OS name
    and version and the architecture (as supplied by 'os.uname()'),
    although the exact information included depends on the OS; eg. for IRIX
    the architecture isn't particularly important (IRIX only runs on SGI
    hardware), but for Linux the kernel version isn't particularly
    important.

    Examples of returned values:
       linux-i586
       linux-alpha (?)
       solaris-2.6-sun4u
       irix-5.3
       irix64-6.2

    Windows will return one of:
       win-amd64 (64bit Windows on AMD64 (aka x86_64, Intel64, EM64T, etc)
       win-ia64 (64bit Windows on Itanium)
       win32 (all others - specifically, sys.platform is returned)

    For other non-POSIX platforms, currently just returns 'sys.platform'.
    """
    import re
    if os.name == 'nt':
        # sniff sys.version for architecture.
        prefix = " bit ("
        i = sys.version.find(prefix)
        if i == -1:
            return sys.platform
        j = sys.version.find(")", i)
        look = sys.version[i+len(prefix):j].lower()
        if look == 'amd64':
            return 'win-amd64'
        if look == 'itanium':
            return 'win-ia64'
        return sys.platform

    if os.name != "posix" or not hasattr(os, 'uname'):
        # XXX what about the architecture? NT is Intel or Alpha,
        # Mac OS is M68k or PPC, etc.
        return sys.platform

    # Try to distinguish various flavours of Unix
    osname, host, release, version, machine = os.uname()

    # Convert the OS name to lowercase, remove '/' characters
    # (to accommodate BSD/OS), and translate spaces (for "Power Macintosh")
    osname = osname.lower().replace('/', '')
    machine = machine.replace(' ', '_')
    machine = machine.replace('/', '-')

    if osname[:5] == "linux":
        # At least on Linux/Intel, 'machine' is the processor --
        # i386, etc.
        # XXX what about Alpha, SPARC, etc?
        return  "%s-%s" % (osname, machine)
    elif osname[:5] == "sunos":
        if release[0] >= "5":           # SunOS 5 == Solaris 2
            osname = "solaris"
            release = "%d.%s" % (int(release[0]) - 3, release[2:])
        # fall through to standard osname-release-machine representation
    elif osname[:4] == "irix":              # could be "irix64"!
        return "%s-%s" % (osname, release)
    elif osname[:3] == "aix":
        return "%s-%s.%s" % (osname, version, release)
    elif osname[:6] == "cygwin":
        osname = "cygwin"
        rel_re = re.compile (r'[\d.]+')
        m = rel_re.match(release)
        if m:
            release = m.group()
    elif osname[:6] == "darwin":
        #
        # For our purposes, we'll assume that the system version from
        # distutils' perspective is what MACOSX_DEPLOYMENT_TARGET is set
        # to. This makes the compatibility story a bit more sane because the
        # machine is going to compile and link as if it were
        # MACOSX_DEPLOYMENT_TARGET.
        cfgvars = get_config_vars()
        macver = os.environ.get('MACOSX_DEPLOYMENT_TARGET')
        if not macver:
            macver = cfgvars.get('MACOSX_DEPLOYMENT_TARGET')

        if 1:
            # Always calculate the release of the running machine,
            # needed to determine if we can build fat binaries or not.

            macrelease = macver
            # Get the system version. Reading this plist is a documented
            # way to get the system version (see the documentation for
            # the Gestalt Manager)
            try:
                f = open('/System/Library/CoreServices/SystemVersion.plist')
            except IOError:
                # We're on a plain darwin box, fall back to the default
                # behaviour.
                pass
            else:
                try:
                    m = re.search(
                            r'<key>ProductUserVisibleVersion</key>\s*' +
                            r'<string>(.*?)</string>', f.read())
                    f.close()
                    if m is not None:
                        macrelease = '.'.join(m.group(1).split('.')[:2])
                    # else: fall back to the default behaviour
                finally:
                    f.close()

        if not macver:
            macver = macrelease

        if macver:
            release = macver
            osname = "macosx"

            if (macrelease + '.') >= '10.4.' and \
                    '-arch' in get_config_vars().get('CFLAGS', '').strip():
                # The universal build will build fat binaries, but not on
                # systems before 10.4
                #
                # Try to detect 4-way universal builds, those have machine-type
                # 'universal' instead of 'fat'.

                machine = 'fat'
                cflags = get_config_vars().get('CFLAGS')

                archs = re.findall('-arch\s+(\S+)', cflags)
                archs = tuple(sorted(set(archs)))

                if len(archs) == 1:
                    machine = archs[0]
                elif archs == ('i386', 'ppc'):
                    machine = 'fat'
                elif archs == ('i386', 'x86_64'):
                    machine = 'intel'
                elif archs == ('i386', 'ppc', 'x86_64'):
                    machine = 'fat3'
                elif archs == ('ppc64', 'x86_64'):
                    machine = 'fat64'
                elif archs == ('i386', 'ppc', 'ppc64', 'x86_64'):
                    machine = 'universal'
                else:
                    raise ValueError(
                       "Don't know machine value for archs=%r"%(archs,))

            elif machine == 'i386':
                # On OSX the machine type returned by uname is always the
                # 32-bit variant, even if the executable architecture is
                # the 64-bit variant
                if sys.maxint >= 2**32:
                    machine = 'x86_64'

            elif machine in ('PowerPC', 'Power_Macintosh'):
                # Pick a sane name for the PPC architecture.
                # See 'i386' case
                if sys.maxint >= 2**32:
                    machine = 'ppc64'
                else:
                    machine = 'ppc'

    return "%s-%s-%s" % (osname, release, machine)


def get_python_version():
    return _PY_VERSION_SHORT

########NEW FILE########
__FILENAME__ = sysconfig32
"""Provide access to Python's configuration information.

"""
import sys
import os
from os.path import pardir, realpath

__all__ = [
    'get_config_h_filename',
    'get_config_var',
    'get_config_vars',
    'get_makefile_filename',
    'get_path',
    'get_path_names',
    'get_paths',
    'get_platform',
    'get_python_version',
    'get_scheme_names',
    'parse_config_h',
    ]

_INSTALL_SCHEMES = {
    'posix_prefix': {
        'stdlib': '{base}/lib/python{py_version_short}',
        'platstdlib': '{platbase}/lib/python{py_version_short}',
        'purelib': '{base}/lib/python{py_version_short}/site-packages',
        'platlib': '{platbase}/lib/python{py_version_short}/site-packages',
        'include':
            '{base}/include/python{py_version_short}{abiflags}',
        'platinclude':
            '{platbase}/include/python{py_version_short}{abiflags}',
        'scripts': '{base}/bin',
        'data': '{base}',
        },
    'posix_home': {
        'stdlib': '{base}/lib/python',
        'platstdlib': '{base}/lib/python',
        'purelib': '{base}/lib/python',
        'platlib': '{base}/lib/python',
        'include': '{base}/include/python',
        'platinclude': '{base}/include/python',
        'scripts': '{base}/bin',
        'data'   : '{base}',
        },
    'nt': {
        'stdlib': '{base}/Lib',
        'platstdlib': '{base}/Lib',
        'purelib': '{base}/Lib/site-packages',
        'platlib': '{base}/Lib/site-packages',
        'include': '{base}/Include',
        'platinclude': '{base}/Include',
        'scripts': '{base}/Scripts',
        'data'   : '{base}',
        },
    'os2': {
        'stdlib': '{base}/Lib',
        'platstdlib': '{base}/Lib',
        'purelib': '{base}/Lib/site-packages',
        'platlib': '{base}/Lib/site-packages',
        'include': '{base}/Include',
        'platinclude': '{base}/Include',
        'scripts': '{base}/Scripts',
        'data'   : '{base}',
        },
    'os2_home': {
        'stdlib': '{userbase}/lib/python{py_version_short}',
        'platstdlib': '{userbase}/lib/python{py_version_short}',
        'purelib': '{userbase}/lib/python{py_version_short}/site-packages',
        'platlib': '{userbase}/lib/python{py_version_short}/site-packages',
        'include': '{userbase}/include/python{py_version_short}',
        'scripts': '{userbase}/bin',
        'data'   : '{userbase}',
        },
    'nt_user': {
        'stdlib': '{userbase}/Python{py_version_nodot}',
        'platstdlib': '{userbase}/Python{py_version_nodot}',
        'purelib': '{userbase}/Python{py_version_nodot}/site-packages',
        'platlib': '{userbase}/Python{py_version_nodot}/site-packages',
        'include': '{userbase}/Python{py_version_nodot}/Include',
        'scripts': '{userbase}/Scripts',
        'data'   : '{userbase}',
        },
    'posix_user': {
        'stdlib': '{userbase}/lib/python{py_version_short}',
        'platstdlib': '{userbase}/lib/python{py_version_short}',
        'purelib': '{userbase}/lib/python{py_version_short}/site-packages',
        'platlib': '{userbase}/lib/python{py_version_short}/site-packages',
        'include': '{userbase}/include/python{py_version_short}',
        'scripts': '{userbase}/bin',
        'data'   : '{userbase}',
        },
    'osx_framework_user': {
        'stdlib': '{userbase}/lib/python',
        'platstdlib': '{userbase}/lib/python',
        'purelib': '{userbase}/lib/python/site-packages',
        'platlib': '{userbase}/lib/python/site-packages',
        'include': '{userbase}/include',
        'scripts': '{userbase}/bin',
        'data'   : '{userbase}',
        },
    }

_SCHEME_KEYS = ('stdlib', 'platstdlib', 'purelib', 'platlib', 'include',
                'scripts', 'data')
_PY_VERSION = sys.version.split()[0]
_PY_VERSION_SHORT = sys.version[:3]
_PY_VERSION_SHORT_NO_DOT = _PY_VERSION[0] + _PY_VERSION[2]
_PREFIX = os.path.normpath(sys.prefix)
_EXEC_PREFIX = os.path.normpath(sys.exec_prefix)
_CONFIG_VARS = None
_USER_BASE = None

def _safe_realpath(path):
    try:
        return realpath(path)
    except OSError:
        return path

if sys.executable:
    _PROJECT_BASE = os.path.dirname(_safe_realpath(sys.executable))
else:
    # sys.executable can be empty if argv[0] has been changed and Python is
    # unable to retrieve the real program name
    _PROJECT_BASE = _safe_realpath(os.getcwd())

if os.name == "nt" and "pcbuild" in _PROJECT_BASE[-8:].lower():
    _PROJECT_BASE = _safe_realpath(os.path.join(_PROJECT_BASE, pardir))
# PC/VS7.1
if os.name == "nt" and "\\pc\\v" in _PROJECT_BASE[-10:].lower():
    _PROJECT_BASE = _safe_realpath(os.path.join(_PROJECT_BASE, pardir, pardir))
# PC/AMD64
if os.name == "nt" and "\\pcbuild\\amd64" in _PROJECT_BASE[-14:].lower():
    _PROJECT_BASE = _safe_realpath(os.path.join(_PROJECT_BASE, pardir, pardir))

def is_python_build():
    for fn in ("Setup.dist", "Setup.local"):
        if os.path.isfile(os.path.join(_PROJECT_BASE, "Modules", fn)):
            return True
    return False

_PYTHON_BUILD = is_python_build()

if _PYTHON_BUILD:
    for scheme in ('posix_prefix', 'posix_home'):
        _INSTALL_SCHEMES[scheme]['include'] = '{srcdir}/Include'
        _INSTALL_SCHEMES[scheme]['platinclude'] = '{projectbase}/.'

def _subst_vars(s, local_vars):
    try:
        return s.format(**local_vars)
    except KeyError:
        try:
            return s.format(**os.environ)
        except KeyError as var:
            raise AttributeError('{%s}' % var)

def _extend_dict(target_dict, other_dict):
    target_keys = target_dict.keys()
    for key, value in other_dict.items():
        if key in target_keys:
            continue
        target_dict[key] = value

def _expand_vars(scheme, vars):
    res = {}
    if vars is None:
        vars = {}
    _extend_dict(vars, get_config_vars())

    for key, value in _INSTALL_SCHEMES[scheme].items():
        if os.name in ('posix', 'nt'):
            value = os.path.expanduser(value)
        res[key] = os.path.normpath(_subst_vars(value, vars))
    return res

def _get_default_scheme():
    if os.name == 'posix':
        # the default scheme for posix is posix_prefix
        return 'posix_prefix'
    return os.name

def _getuserbase():
    env_base = os.environ.get("PYTHONUSERBASE", None)
    def joinuser(*args):
        return os.path.expanduser(os.path.join(*args))

    # what about 'os2emx', 'riscos' ?
    if os.name == "nt":
        base = os.environ.get("APPDATA") or "~"
        return env_base if env_base else joinuser(base, "Python")

    if sys.platform == "darwin":
        framework = get_config_var("PYTHONFRAMEWORK")
        if framework:
            return env_base if env_base else joinuser("~", "Library", framework, "%d.%d"%(
                sys.version_info[:2]))

    return env_base if env_base else joinuser("~", ".local")


def _parse_makefile(filename, vars=None):
    """Parse a Makefile-style file.

    A dictionary containing name/value pairs is returned.  If an
    optional dictionary is passed in as the second argument, it is
    used instead of a new dictionary.
    """
    import re
    # Regexes needed for parsing Makefile (and similar syntaxes,
    # like old-style Setup files).
    _variable_rx = re.compile("([a-zA-Z][a-zA-Z0-9_]+)\s*=\s*(.*)")
    _findvar1_rx = re.compile(r"\$\(([A-Za-z][A-Za-z0-9_]*)\)")
    _findvar2_rx = re.compile(r"\${([A-Za-z][A-Za-z0-9_]*)}")

    if vars is None:
        vars = {}
    done = {}
    notdone = {}

    with open(filename, errors="surrogateescape") as f:
        lines = f.readlines()

    for line in lines:
        if line.startswith('#') or line.strip() == '':
            continue
        m = _variable_rx.match(line)
        if m:
            n, v = m.group(1, 2)
            v = v.strip()
            # `$$' is a literal `$' in make
            tmpv = v.replace('$$', '')

            if "$" in tmpv:
                notdone[n] = v
            else:
                try:
                    v = int(v)
                except ValueError:
                    # insert literal `$'
                    done[n] = v.replace('$$', '$')
                else:
                    done[n] = v

    # do variable interpolation here
    variables = list(notdone.keys())

    # Variables with a 'PY_' prefix in the makefile. These need to
    # be made available without that prefix through sysconfig.
    # Special care is needed to ensure that variable expansion works, even
    # if the expansion uses the name without a prefix.
    renamed_variables = ('CFLAGS', 'LDFLAGS', 'CPPFLAGS')

    while len(variables) > 0:
        for name in tuple(variables):
            value = notdone[name]
            m = _findvar1_rx.search(value) or _findvar2_rx.search(value)
            if m is not None:
                n = m.group(1)
                found = True
                if n in done:
                    item = str(done[n])
                elif n in notdone:
                    # get it on a subsequent round
                    found = False
                elif n in os.environ:
                    # do it like make: fall back to environment
                    item = os.environ[n]

                elif n in renamed_variables:
                    if name.startswith('PY_') and name[3:] in renamed_variables:
                        item = ""

                    elif 'PY_' + n in notdone:
                        found = False

                    else:
                        item = str(done['PY_' + n])

                else:
                    done[n] = item = ""

                if found:
                    after = value[m.end():]
                    value = value[:m.start()] + item + after
                    if "$" in after:
                        notdone[name] = value
                    else:
                        try:
                            value = int(value)
                        except ValueError:
                            done[name] = value.strip()
                        else:
                            done[name] = value
                        variables.remove(name)

                        if name.startswith('PY_') \
                                and name[3:] in renamed_variables:

                            name = name[3:]
                            if name not in done:
                                done[name] = value


            else:
                # bogus variable reference; just drop it since we can't deal
                variables.remove(name)

    # strip spurious spaces
    for k, v in done.items():
        if isinstance(v, str):
            done[k] = v.strip()

    # save the results in the global dictionary
    vars.update(done)
    return vars


def get_makefile_filename():
    """Return the path of the Makefile."""
    if _PYTHON_BUILD:
        return os.path.join(_PROJECT_BASE, "Makefile")
    return os.path.join(get_path('stdlib'),
                        'config-{}{}'.format(_PY_VERSION_SHORT, sys.abiflags),
                        'Makefile')


def _init_posix(vars):
    """Initialize the module as appropriate for POSIX systems."""
    # load the installed Makefile:
    makefile = get_makefile_filename()
    try:
        _parse_makefile(makefile, vars)
    except IOError as e:
        msg = "invalid Python installation: unable to open %s" % makefile
        if hasattr(e, "strerror"):
            msg = msg + " (%s)" % e.strerror
        raise IOError(msg)
    # load the installed pyconfig.h:
    config_h = get_config_h_filename()
    try:
        with open(config_h) as f:
            parse_config_h(f, vars)
    except IOError as e:
        msg = "invalid Python installation: unable to open %s" % config_h
        if hasattr(e, "strerror"):
            msg = msg + " (%s)" % e.strerror
        raise IOError(msg)
    # On MacOSX we need to check the setting of the environment variable
    # MACOSX_DEPLOYMENT_TARGET: configure bases some choices on it so
    # it needs to be compatible.
    # If it isn't set we set it to the configure-time value
    if sys.platform == 'darwin' and 'MACOSX_DEPLOYMENT_TARGET' in vars:
        cfg_target = vars['MACOSX_DEPLOYMENT_TARGET']
        cur_target = os.getenv('MACOSX_DEPLOYMENT_TARGET', '')
        if cur_target == '':
            cur_target = cfg_target
            os.putenv('MACOSX_DEPLOYMENT_TARGET', cfg_target)
        elif (list(map(int, cfg_target.split('.'))) >
              list(map(int, cur_target.split('.')))):
            msg = ('$MACOSX_DEPLOYMENT_TARGET mismatch: now "%s" but "%s" '
                   'during configure' % (cur_target, cfg_target))
            raise IOError(msg)
    # On AIX, there are wrong paths to the linker scripts in the Makefile
    # -- these paths are relative to the Python source, but when installed
    # the scripts are in another directory.
    if _PYTHON_BUILD:
        vars['LDSHARED'] = vars['BLDSHARED']

def _init_non_posix(vars):
    """Initialize the module as appropriate for NT"""
    # set basic install directories
    vars['LIBDEST'] = get_path('stdlib')
    vars['BINLIBDEST'] = get_path('platstdlib')
    vars['INCLUDEPY'] = get_path('include')
    vars['SO'] = '.pyd'
    vars['EXE'] = '.exe'
    vars['VERSION'] = _PY_VERSION_SHORT_NO_DOT
    vars['BINDIR'] = os.path.dirname(_safe_realpath(sys.executable))

#
# public APIs
#


def parse_config_h(fp, vars=None):
    """Parse a config.h-style file.

    A dictionary containing name/value pairs is returned.  If an
    optional dictionary is passed in as the second argument, it is
    used instead of a new dictionary.
    """
    import re
    if vars is None:
        vars = {}
    define_rx = re.compile("#define ([A-Z][A-Za-z0-9_]+) (.*)\n")
    undef_rx = re.compile("/[*] #undef ([A-Z][A-Za-z0-9_]+) [*]/\n")

    while True:
        line = fp.readline()
        if not line:
            break
        m = define_rx.match(line)
        if m:
            n, v = m.group(1, 2)
            try: v = int(v)
            except ValueError: pass
            vars[n] = v
        else:
            m = undef_rx.match(line)
            if m:
                vars[m.group(1)] = 0
    return vars

def get_config_h_filename():
    """Return the path of pyconfig.h."""
    if _PYTHON_BUILD:
        if os.name == "nt":
            inc_dir = os.path.join(_PROJECT_BASE, "PC")
        else:
            inc_dir = _PROJECT_BASE
    else:
        inc_dir = get_path('platinclude')
    return os.path.join(inc_dir, 'pyconfig.h')

def get_scheme_names():
    """Return a tuple containing the schemes names."""
    schemes = list(_INSTALL_SCHEMES.keys())
    schemes.sort()
    return tuple(schemes)

def get_path_names():
    """Return a tuple containing the paths names."""
    return _SCHEME_KEYS

def get_paths(scheme=_get_default_scheme(), vars=None, expand=True):
    """Return a mapping containing an install scheme.

    ``scheme`` is the install scheme name. If not provided, it will
    return the default scheme for the current platform.
    """
    if expand:
        return _expand_vars(scheme, vars)
    else:
        return _INSTALL_SCHEMES[scheme]

def get_path(name, scheme=_get_default_scheme(), vars=None, expand=True):
    """Return a path corresponding to the scheme.

    ``scheme`` is the install scheme name.
    """
    return get_paths(scheme, vars, expand)[name]

def get_config_vars(*args):
    """With no arguments, return a dictionary of all configuration
    variables relevant for the current platform.

    On Unix, this means every variable defined in Python's installed Makefile;
    On Windows and Mac OS it's a much smaller set.

    With arguments, return a list of values that result from looking up
    each argument in the configuration variable dictionary.
    """
    import re
    global _CONFIG_VARS
    if _CONFIG_VARS is None:
        _CONFIG_VARS = {}
        # Normalized versions of prefix and exec_prefix are handy to have;
        # in fact, these are the standard versions used most places in the
        # Distutils.
        _CONFIG_VARS['prefix'] = _PREFIX
        _CONFIG_VARS['exec_prefix'] = _EXEC_PREFIX
        _CONFIG_VARS['py_version'] = _PY_VERSION
        _CONFIG_VARS['py_version_short'] = _PY_VERSION_SHORT
        _CONFIG_VARS['py_version_nodot'] = _PY_VERSION[0] + _PY_VERSION[2]
        _CONFIG_VARS['base'] = _PREFIX
        _CONFIG_VARS['platbase'] = _EXEC_PREFIX
        _CONFIG_VARS['projectbase'] = _PROJECT_BASE
        try:
            _CONFIG_VARS['abiflags'] = sys.abiflags
        except AttributeError:
            # sys.abiflags may not be defined on all platforms.
            _CONFIG_VARS['abiflags'] = ''

        if os.name in ('nt', 'os2'):
            _init_non_posix(_CONFIG_VARS)
        if os.name == 'posix':
            _init_posix(_CONFIG_VARS)
        # Setting 'userbase' is done below the call to the
        # init function to enable using 'get_config_var' in
        # the init-function.
        _CONFIG_VARS['userbase'] = _getuserbase()

        if 'srcdir' not in _CONFIG_VARS:
            _CONFIG_VARS['srcdir'] = _PROJECT_BASE
        else:
            _CONFIG_VARS['srcdir'] = _safe_realpath(_CONFIG_VARS['srcdir'])


        # Convert srcdir into an absolute path if it appears necessary.
        # Normally it is relative to the build directory.  However, during
        # testing, for example, we might be running a non-installed python
        # from a different directory.
        if _PYTHON_BUILD and os.name == "posix":
            base = _PROJECT_BASE
            try:
                cwd = os.getcwd()
            except OSError:
                cwd = None
            if (not os.path.isabs(_CONFIG_VARS['srcdir']) and
                base != cwd):
                # srcdir is relative and we are not in the same directory
                # as the executable. Assume executable is in the build
                # directory and make srcdir absolute.
                srcdir = os.path.join(base, _CONFIG_VARS['srcdir'])
                _CONFIG_VARS['srcdir'] = os.path.normpath(srcdir)

        if sys.platform == 'darwin':
            kernel_version = os.uname()[2] # Kernel version (8.4.3)
            major_version = int(kernel_version.split('.')[0])

            if major_version < 8:
                # On Mac OS X before 10.4, check if -arch and -isysroot
                # are in CFLAGS or LDFLAGS and remove them if they are.
                # This is needed when building extensions on a 10.3 system
                # using a universal build of python.
                for key in ('LDFLAGS', 'BASECFLAGS',
                        # a number of derived variables. These need to be
                        # patched up as well.
                        'CFLAGS', 'PY_CFLAGS', 'BLDSHARED'):
                    flags = _CONFIG_VARS[key]
                    flags = re.sub('-arch\s+\w+\s', ' ', flags)
                    flags = re.sub('-isysroot [^ \t]*', ' ', flags)
                    _CONFIG_VARS[key] = flags
            else:
                # Allow the user to override the architecture flags using
                # an environment variable.
                # NOTE: This name was introduced by Apple in OSX 10.5 and
                # is used by several scripting languages distributed with
                # that OS release.
                if 'ARCHFLAGS' in os.environ:
                    arch = os.environ['ARCHFLAGS']
                    for key in ('LDFLAGS', 'BASECFLAGS',
                        # a number of derived variables. These need to be
                        # patched up as well.
                        'CFLAGS', 'PY_CFLAGS', 'BLDSHARED'):

                        flags = _CONFIG_VARS[key]
                        flags = re.sub('-arch\s+\w+\s', ' ', flags)
                        flags = flags + ' ' + arch
                        _CONFIG_VARS[key] = flags

                # If we're on OSX 10.5 or later and the user tries to
                # compiles an extension using an SDK that is not present
                # on the current machine it is better to not use an SDK
                # than to fail.
                #
                # The major usecase for this is users using a Python.org
                # binary installer  on OSX 10.6: that installer uses
                # the 10.4u SDK, but that SDK is not installed by default
                # when you install Xcode.
                #
                CFLAGS = _CONFIG_VARS.get('CFLAGS', '')
                m = re.search('-isysroot\s+(\S+)', CFLAGS)
                if m is not None:
                    sdk = m.group(1)
                    if not os.path.exists(sdk):
                        for key in ('LDFLAGS', 'BASECFLAGS',
                             # a number of derived variables. These need to be
                             # patched up as well.
                            'CFLAGS', 'PY_CFLAGS', 'BLDSHARED'):

                            flags = _CONFIG_VARS[key]
                            flags = re.sub('-isysroot\s+\S+(\s|$)', ' ', flags)
                            _CONFIG_VARS[key] = flags

    if args:
        vals = []
        for name in args:
            vals.append(_CONFIG_VARS.get(name))
        return vals
    else:
        return _CONFIG_VARS

def get_config_var(name):
    """Return the value of a single variable using the dictionary returned by
    'get_config_vars()'.

    Equivalent to get_config_vars().get(name)
    """
    return get_config_vars().get(name)

def get_platform():
    """Return a string that identifies the current platform.

    This is used mainly to distinguish platform-specific build directories and
    platform-specific built distributions.  Typically includes the OS name
    and version and the architecture (as supplied by 'os.uname()'),
    although the exact information included depends on the OS; eg. for IRIX
    the architecture isn't particularly important (IRIX only runs on SGI
    hardware), but for Linux the kernel version isn't particularly
    important.

    Examples of returned values:
       linux-i586
       linux-alpha (?)
       solaris-2.6-sun4u
       irix-5.3
       irix64-6.2

    Windows will return one of:
       win-amd64 (64bit Windows on AMD64 (aka x86_64, Intel64, EM64T, etc)
       win-ia64 (64bit Windows on Itanium)
       win32 (all others - specifically, sys.platform is returned)

    For other non-POSIX platforms, currently just returns 'sys.platform'.
    """
    import re
    if os.name == 'nt':
        # sniff sys.version for architecture.
        prefix = " bit ("
        i = sys.version.find(prefix)
        if i == -1:
            return sys.platform
        j = sys.version.find(")", i)
        look = sys.version[i+len(prefix):j].lower()
        if look == 'amd64':
            return 'win-amd64'
        if look == 'itanium':
            return 'win-ia64'
        return sys.platform

    if os.name != "posix" or not hasattr(os, 'uname'):
        # XXX what about the architecture? NT is Intel or Alpha,
        # Mac OS is M68k or PPC, etc.
        return sys.platform

    # Try to distinguish various flavours of Unix
    osname, host, release, version, machine = os.uname()

    # Convert the OS name to lowercase, remove '/' characters
    # (to accommodate BSD/OS), and translate spaces (for "Power Macintosh")
    osname = osname.lower().replace('/', '')
    machine = machine.replace(' ', '_')
    machine = machine.replace('/', '-')

    if osname[:5] == "linux":
        # At least on Linux/Intel, 'machine' is the processor --
        # i386, etc.
        # XXX what about Alpha, SPARC, etc?
        return  "%s-%s" % (osname, machine)
    elif osname[:5] == "sunos":
        if release[0] >= "5":           # SunOS 5 == Solaris 2
            osname = "solaris"
            release = "%d.%s" % (int(release[0]) - 3, release[2:])
        # fall through to standard osname-release-machine representation
    elif osname[:4] == "irix":              # could be "irix64"!
        return "%s-%s" % (osname, release)
    elif osname[:3] == "aix":
        return "%s-%s.%s" % (osname, version, release)
    elif osname[:6] == "cygwin":
        osname = "cygwin"
        rel_re = re.compile (r'[\d.]+')
        m = rel_re.match(release)
        if m:
            release = m.group()
    elif osname[:6] == "darwin":
        #
        # For our purposes, we'll assume that the system version from
        # distutils' perspective is what MACOSX_DEPLOYMENT_TARGET is set
        # to. This makes the compatibility story a bit more sane because the
        # machine is going to compile and link as if it were
        # MACOSX_DEPLOYMENT_TARGET.
        cfgvars = get_config_vars()
        macver = os.environ.get('MACOSX_DEPLOYMENT_TARGET')
        if not macver:
            macver = cfgvars.get('MACOSX_DEPLOYMENT_TARGET')

        if 1:
            # Always calculate the release of the running machine,
            # needed to determine if we can build fat binaries or not.

            macrelease = macver
            # Get the system version. Reading this plist is a documented
            # way to get the system version (see the documentation for
            # the Gestalt Manager)
            try:
                f = open('/System/Library/CoreServices/SystemVersion.plist')
            except IOError:
                # We're on a plain darwin box, fall back to the default
                # behaviour.
                pass
            else:
                try:
                    m = re.search(
                            r'<key>ProductUserVisibleVersion</key>\s*' +
                            r'<string>(.*?)</string>', f.read())
                    f.close()
                    if m is not None:
                        macrelease = '.'.join(m.group(1).split('.')[:2])
                    # else: fall back to the default behaviour
                finally:
                    f.close()

        if not macver:
            macver = macrelease

        if macver:
            release = macver
            osname = "macosx"

            if (macrelease + '.') >= '10.4.' and \
                    '-arch' in get_config_vars().get('CFLAGS', '').strip():
                # The universal build will build fat binaries, but not on
                # systems before 10.4
                #
                # Try to detect 4-way universal builds, those have machine-type
                # 'universal' instead of 'fat'.

                machine = 'fat'
                cflags = get_config_vars().get('CFLAGS')

                archs = re.findall('-arch\s+(\S+)', cflags)
                archs = tuple(sorted(set(archs)))

                if len(archs) == 1:
                    machine = archs[0]
                elif archs == ('i386', 'ppc'):
                    machine = 'fat'
                elif archs == ('i386', 'x86_64'):
                    machine = 'intel'
                elif archs == ('i386', 'ppc', 'x86_64'):
                    machine = 'fat3'
                elif archs == ('ppc64', 'x86_64'):
                    machine = 'fat64'
                elif archs == ('i386', 'ppc', 'ppc64', 'x86_64'):
                    machine = 'universal'
                else:
                    raise ValueError(
                       "Don't know machine value for archs=%r"%(archs,))

            elif machine == 'i386':
                # On OSX the machine type returned by uname is always the
                # 32-bit variant, even if the executable architecture is
                # the 64-bit variant
                if sys.maxsize >= 2**32:
                    machine = 'x86_64'

            elif machine in ('PowerPC', 'Power_Macintosh'):
                # Pick a sane name for the PPC architecture.
                # See 'i386' case
                if sys.maxsize >= 2**32:
                    machine = 'ppc64'
                else:
                    machine = 'ppc'

    return "%s-%s-%s" % (osname, release, machine)


def get_python_version():
    return _PY_VERSION_SHORT

def _print_dict(title, data):
    for index, (key, value) in enumerate(sorted(data.items())):
        if index == 0:
            print('{0}: '.format(title))
        print('\t{0} = "{1}"'.format(key, value))

def _main():
    """Display all information sysconfig detains."""
    print('Platform: "{0}"'.format(get_platform()))
    print('Python version: "{0}"'.format(get_python_version()))
    print('Current installation scheme: "{0}"'.format(_get_default_scheme()))
    print('')
    _print_dict('Paths', get_paths())
    print('')
    _print_dict('Variables', get_config_vars())

if __name__ == '__main__':
    _main()

########NEW FILE########
__FILENAME__ = copy

from os.path import join, dirname, isfile
from os import makedirs, walk, remove
import shutil

import rvirtualenv


def ignore(src, names):
    def invalid(s):
        if '__pycache__' in s:
            return True
        if s.endswith('pyc'):
            return True
        return False
    ignored = set()
    ignored.update(( i for i in names if invalid(i) ))
    return ignored

def remove_ignored(src, dst, ignore=None):
    for base, dirs, files in walk(dst):
        ignored = set()
        if ignore is not None:
            ignored = ignore(base.replace(dst, src), dirs+files)
        for i in ignored:
            f = join(base, i)
            if not isfile(f):
                shutil.rmtree(f, True)
            else:
                remove(f)

def copytree(src, dst, symlinks=False, ignore=None):
    shutil.copytree(src, dst, symlinks)
    remove_ignored(src, dst, ignore)

def copy(where):
    '''
    main function for copying template/venv into specified new virtualenv
    '''
    base = dirname(rvirtualenv.__file__)
    copytree(join(base, 'template', 'venv'), where, ignore=ignore)
    makedirs(join(where, 'src'))
    copytree(join(base, 'template', 'inst'), join(where, 'src', 'rvirtualenvkeep'), ignore=ignore)
    copytree(join(base, 'rvirtualenvinstall'), join(where, 'rvirtualenvinstall'), ignore=ignore)


########NEW FILE########
__FILENAME__ = generate

import os
from os import path
import sys
from subprocess import Popen, PIPE

import rvirtualenv
from rvirtualenv.rvirtualenvinstall.scheme import guess_scheme


def run_setup(pythonpath, install_dir):
    '''
    install couple of helper modules via distutils
    because it creates its directory (via the correct schema)

    it must be called in subprocess
    because of possible setuptools monkeypatching
    '''
    os.environ['PYTHONPATH'] = pythonpath
    install = [
        '"%s"' % sys.executable,
        path.join(install_dir, 'setup.py'),
        'install',
    ]
    install = ' '.join(install)

    shell = sys.platform != 'win32'
    stdout = stderr = PIPE
    p = Popen(install, stdout=stdout, stderr=stderr, shell=shell)
    stdoutdata, stderrdata = p.communicate()

    return stdoutdata, stdoutdata

def generate(where, layout=None, sitepackages=True, prompt=None):
    '''
    create dirs and files after virtualenv dir itself is prepared
    '''
    generate_pythonrc_stuff(where, layout, sitepackages, prompt)
    install_venv_keep_package(where, path.join(where, 'src', 'rvirtualenvkeep'))

def install_venv_keep_package(venv_base, install_dir):
    '''
    install setup.py via distutils
    '''
    run_setup(venv_base, install_dir)

def generate_pythonrc_stuff(venv_base, layout, sitepackages, prompt):
    '''
    insert correct lib dirs into pythonrc.py
    '''
    # load pythonrc.py file
    base = path.dirname(rvirtualenv.__file__)
    f = open(path.join(base, 'template', 'venv', 'pythonrc.py'), 'r')
    content = f.read()
    f.close()

    if layout is None:
        layout = guess_scheme()

    # replace pattern in pythonrc.py
    patrn = "scheme = 'custom'"
    repl = "scheme = '%s'" % layout
    content = content.replace(patrn, repl)

    # update no-site-packages option
    patrn = "sitepackages = True"
    repl = "sitepackages = %s" % sitepackages
    content = content.replace(patrn, repl)

    # set custom prompt
    patrn = "#prompt = '[CUSTOM]' # set your custom prompt prefix (see -p option)"
    repl = "prompt = %r" % prompt
    if prompt is not None:
        content = content.replace(patrn, repl)

    # write it
    f = open(path.join(venv_base, 'pythonrc.py'), 'w')
    f.write(content)
    f.close()


########NEW FILE########
__FILENAME__ = boot
import sys
from os import path

from rvirtualenvinstall import (
    scheme,
    install,
)
import pythonrc


def boot():
    base = path.abspath(path.dirname(pythonrc.__file__))

    # real_prefix is useful for pip and uninstalling system pkgs
    sys.real_prefix = sys.prefix
    # python uses this almost everywhere
    sys.prefix = base

    if not pythonrc.sitepackages:
        sys.path = sys.__rvirtualenv_prev_path

    this_site_packages = [
        scheme.get_scheme(pythonrc.scheme, 'purelib'),
        scheme.get_scheme(pythonrc.scheme, 'platlib'),
    ]

    scheme.add_to_path(getattr(pythonrc, 'extra_paths', []))
    scheme.add_to_path(this_site_packages)

    install.monkeypatch()


########NEW FILE########
__FILENAME__ = develop
import setuptools
from setuptools.command.develop import develop as _develop


class develop(_develop):
    description = "rvirtualenv's %s" % _develop.description
    def run(self):
        print('WTF')

# don't know why isn't it overriden by entry_points
setuptools.command.develop.develop = develop


########NEW FILE########
__FILENAME__ = install
import distutils
from distutils.command.install import install as _install

import pythonrc
from rvirtualenvinstall import scheme


class install(_install):
    description = "rvirtualenv's %s" % _install.description
    def finalize_options(self):
        _install.finalize_options(self)

        vars = {'dist_name': self.distribution.get_name(),}
        self.install_purelib = scheme.get_scheme(pythonrc.scheme, 'purelib')
        self.install_platlib = scheme.get_scheme(pythonrc.scheme, 'purelib')
        self.install_headers = scheme.get_scheme(pythonrc.scheme, 'headers', vars=vars)
        self.install_scripts = scheme.get_scheme(pythonrc.scheme, 'scripts')
        self.install_data = scheme.get_scheme(pythonrc.scheme, 'data')

        if self.distribution.ext_modules: # has extensions: non-pure
            self.install_lib = self.install_platlib
        else:
            self.install_lib = self.install_purelib

def monkeypatch():
    "monkey patch for distutils install command"
    distutils.command.install.install = install


########NEW FILE########
__FILENAME__ = scheme
import sys
from os import path
import site
from distutils.util import subst_vars

INSTALL_SCHEMES = {
    'custom': {
        'purelib': '$base/lib/python/site-packages',
        'platlib': '$base/lib/python$py_version_short/site-packages',
        'headers': '$base/include/python$py_version_short/$dist_name',
        'scripts': '$base/bin',
        'data'   : '$base/lib/python$py_version_short/site-packages',
        },
    'unix': {
        'purelib': '$base/lib/python$py_version_short/site-packages',
        'platlib': '$base/lib/python$py_version_short/site-packages',
        'headers': '$base/include/python$py_version_short/$dist_name',
        'scripts': '$base/bin',
        'data'   : '$base/lib/python$py_version_short/site-packages',
        },
    'windows': {
        'purelib': '$base/Lib/site-packages',
        'platlib': '$base/Lib/site-packages',
        'headers': '$base/Include/$dist_name',
        'scripts': '$base/Scripts',
        'data'   : '$base/Lib/site-packages',
        },
    'os2': {
        'purelib': '$base/Lib/site-packages',
        'platlib': '$base/Lib/site-packages',
        'headers': '$base/Include/$dist_name',
        'scripts': '$base/Scripts',
        'data'   : '$base/Lib/site-packages',
        },
    'darwin': {
        'purelib': '$base/Library/Python$py_version_short/site-packages',
        'platlib': '$base/Library/Python$py_version_short/site-packages',
        'headers': '$base/Include/$dist_name',
        'scripts': '$base/bin',
        'data'   : '$base/Library/Python$py_version_short/site-packages',
        },
    }

def guess_scheme():
    return 'unix'

def get_scheme(platform, what, vars={}):
    # TODO: maybe use syslinux.get_path in next versions
    replace = {
        'base': sys.prefix,
        'py_version_short': sys.version[:3],
        'dist_name': 'UNKNOWN',
    }
    replace.update(vars)
    line = INSTALL_SCHEMES[platform][what]
    line = path.join(*line.split('/'))
    return subst_vars(line, replace)

def add_to_path(new_paths):
    "add dirs to the beginnig of sys.path"
    __plen = len(sys.path)
    for i in new_paths:
        if i not in sys.path:
            site.addsitedir(i)
    new = sys.path[__plen:]
    del sys.path[__plen:]
    sys.path[0:0] = new


########NEW FILE########
__FILENAME__ = activate
#!/usr/bin/env python

import sys
from os import path

def get_prompt(vname_path, vname):
    sys.path.insert(0, vname_path)
    import pythonrc
    prompt = getattr(pythonrc, 'prompt', '(%s)' % vname)
    return prompt

def get_subst_values():
    base = path.dirname(__file__)
    vname_path = path.abspath(path.join(base, path.pardir))
    vname = path.split(vname_path)[-1]
    bin_path = path.split(base)[-1]
    prompt = get_prompt(vname_path, vname)
    return {
        '__VIRTUAL_PROMPT__': prompt,
        '__VIRTUAL_WINPROMPT__': prompt, 
        '__VIRTUAL_ENV__': vname_path,
        '__VIRTUAL_NAME__': vname,
        '__BIN_NAME__': bin_path,
    }

def generate(ftemplt, foutput):
    ftemplt = open(ftemplt, 'r').read()
    for k, v in get_subst_values().items():
        ftemplt = ftemplt.replace(k, v)
    f = open(foutput, 'w')
    f.write(ftemplt)
    f.close()

def main(argv=None):
    if argv is None:
        argv = sys.argv
    if len(argv) < 3:
        raise NotImplementedError
    generate(argv[1], argv[2])

if __name__ == '__main__':
    main()


########NEW FILE########
__FILENAME__ = getpythondist
import sys
print(sys.executable)

########NEW FILE########
__FILENAME__ = python
#!/usr/bin/env python

'''
use this file directly, or just set PYTHONPATH to your virtualenv directory
and run system wide python instance
'''

import os, sys
from os import path
from os.path import join, dirname, pardir, abspath


def get_this_path():
    '''
    we do expect scripts are installed just one level deeper from venv
    '''
    base = dirname(__file__)
    thispath = abspath(join(base, pardir))
    return thispath

def inject_pythonpath():
    '''
    insert virtualevn path into pythonpath
    '''
    pypath = os.environ.get('PYTHONPATH', '').split(path.pathsep)
    thispath = get_this_path()
    try:
        pypath.remove('')
        pypath.remove(thispath)
    except ValueError:
        pass
    pypath.insert(0, thispath)
    os.environ['PYTHONPATH'] = path.pathsep.join(pypath)

def prepare_argv(argv=[]):
    '''
    prepare argv to run
      * windows platform needs add quotes around arguments with spaces
    '''
    def q(s):
        return '"%s"' % s.replace('"', '\\"')
    if sys.platform == 'win32':
        argv = map(q, argv)
    return tuple(argv)

def run(argv):
    os.execvp(sys.executable, argv)

def main(argv=None):
    if argv is None:
        argv = sys.argv
    inject_pythonpath()
    run(prepare_argv(argv))

if __name__ == '__main__':
    main()


########NEW FILE########
__FILENAME__ = rvirtualenvkeep
"""
congratulations, it seems, you are inside
python relocatable virtual environment
"""

########NEW FILE########
__FILENAME__ = rvirtualenv
#!/usr/bin/env python

from rvirtualenv import main

if __name__ == '__main__':
    main()


########NEW FILE########
__FILENAME__ = helpers

import os
from os import path
from shutil import rmtree
from unittest import TestCase
from tempfile import mkdtemp

import rvirtualenv


class InTempTestCase(TestCase):
    def setUp(self):
        # unittest limit
        self.maxDiff = None

        # store curr path
        self.oldcwd = os.getcwd()

        # create test dir structure
        self.directory = mkdtemp(prefix='test_rvirtualenv_')

        # new rvirtualenv
        self.virtualenv = path.join(self.directory, 'PY')

        # store base dir
        self.base = path.join(path.dirname(rvirtualenv.__file__), path.pardir)

    def tearDown(self):
        # go back
        os.chdir(self.oldcwd)

        # dir cleanup
        rmtree(self.directory, True)

def store_directory_structure(mypath, content=None):
    '''
    recursivelly traverse directory and store it in format:
    (
      (mypath, None),
      (mypath/to, None),
      (mypath/to/dir, None),
      (mypath/to/dir/file.txt, {{ file's content }}),
    )
    '''
    d = {}
    for base, dirs, files in os.walk(mypath):
        d[base] = None
        for i in files:
            fn = path.join(base, i)
            if content is not None:
                d[fn] = content
                continue
            f = open(fn, 'rb')
            d[fn] = f.read()
            f.close()
    return d.items()

def relpath(p, start):
    "os.path.relpath dummy replacement"
    return p.replace(path.join(start, ''), '', 1)


########NEW FILE########
__FILENAME__ = venvtest
#!/usr/bin/env python

__versionstr__ = '0.1.0'

def main():
    print('venvtest')

if __name__ == '__main__':
    main()


########NEW FILE########
__FILENAME__ = venvtest
#!/usr/bin/env python

__versionstr__ = '0.1.0'

def main():
    print('venvtest')

if __name__ == '__main__':
    main()


########NEW FILE########
__FILENAME__ = print

import sys

if len(sys.argv) > 1:
    print(sys.argv[1:])


########NEW FILE########
__FILENAME__ = test_all
#!/usr/bin/env python

'''
poor man's nosetests
'''

import sys
from os import path
import unittest


def runtests():
    base = path.abspath(path.join(path.dirname(__file__), path.pardir))

    # hack pythonpath to contain dir to load proper module for testing
    oldpath = sys.path[:]
    if base in sys.path:
        sys.path.remove(base)
    sys.path.insert(0, base)

    r = unittest.TextTestRunner()
    l = unittest.TestLoader()

    m = [
        'tests.test_copy',
        'tests.test_generate',
        'tests.test_rvirtualenv',
    ]

    result = r.run(l.loadTestsFromNames(m))
    sys.exit(not result.wasSuccessful())

if __name__ == '__main__':
    runtests()


########NEW FILE########
__FILENAME__ = test_copy

import os
from os import path

from tests.helpers import InTempTestCase, store_directory_structure

import rvirtualenv
from rvirtualenv.copy import copy, ignore, remove_ignored


class TestCopy(InTempTestCase):
    def test_ignore(self):
        names = [
            'abc.txt',
            'koko/koko.pyc',
            'keke/__pycache__',
            'def.py',
        ]
        expected = set([
            'koko/koko.pyc',
            'keke/__pycache__',
        ])
        self.failUnlessEqual(expected, ignore(None, names))

    def test_remove_ignored(self):
        # create some dummy dir structures
        for i in ('FROM', 'TO'):
            os.makedirs(path.join(self.directory, i))
            os.makedirs(path.join(self.directory, i, '__pycache__'))
            f = open(path.join(self.directory, i, 'test.pyc'), 'w'); f.close()
            f = open(path.join(self.directory, i, 'test.py'), 'w'); f.close()
        # call our logic
        remove_ignored(path.join(self.directory, 'FROM'), path.join(self.directory, 'TO'), ignore)
        # some files should be removed
        self.assertFalse(path.exists(path.join(self.directory, 'TO', '__pycache__')))
        self.assertFalse(path.exists(path.join(self.directory, 'TO', 'test.pyc')))
        # other should stay
        self.assertTrue(path.exists(path.join(self.directory, 'TO', 'test.py')))
        # and originals must not be touched
        self.assertTrue(path.exists(path.join(self.directory, 'FROM', '__pycache__')))
        self.assertTrue(path.exists(path.join(self.directory, 'FROM', 'test.pyc')))
        self.assertTrue(path.exists(path.join(self.directory, 'FROM', 'test.py')))

    def test_whole_copy(self):
        base = path.dirname(rvirtualenv.__file__)

        os.chdir(path.join(base, 'template', 'venv'))
        a = list(store_directory_structure('.'))

        os.chdir(base)
        b = store_directory_structure('.')
        # filter only rvirtualenvinstall
        b = [ i for i in b if 'rvirtualenvinstall' in i[0] ]
        # extract not wanted
        b = [ i for i in b if 'template' not in i[0] ]

        os.chdir(path.join(base, 'template'))
        c = store_directory_structure('.')
        patrn = path.join('.', 'inst')
        repl = path.join('.', 'src', 'rvirtualenvkeep')
        c = [ (i.replace(patrn, repl),j) for (i,j) in c if patrn in i ]

        d = [(path.join('.', 'src'), None)]

        expected = sorted(a+b+c+d)
        # extract not wanted - aka those that are ignored
        expected = [ i for i in expected if '__pycache__' not in i[0] ]
        expected = [ i for i in expected if not i[0].endswith('pyc') ]

        copy(self.virtualenv)

        os.chdir(self.virtualenv)
        x = store_directory_structure('.')
        x = [ i for i in x if '__pycache__' not in i[0] ]
        got = sorted(x)

        self.failUnlessEqual([i for (i,j) in expected], [i for (i,j) in got])
        self.failUnlessEqual(expected, got)


########NEW FILE########
__FILENAME__ = test_generate

from os import path

from tests.helpers import InTempTestCase, store_directory_structure

import rvirtualenv
from rvirtualenv.generate import generate
from rvirtualenv.copy import copy
from rvirtualenv.rvirtualenvinstall.scheme import get_scheme, guess_scheme


class TestGenerate(InTempTestCase):
    def test_whole_generate(self, layout=None):
        copy(self.virtualenv)
        generate(self.virtualenv, layout=layout)
        structure = store_directory_structure(self.virtualenv, content='<file>')

        if layout is None:
            layout = guess_scheme()

        paths = set((i for i,j in structure))
        vars = {'base': self.virtualenv}
        self.assertTrue(get_scheme(layout, 'purelib', vars=vars) in paths)
        self.assertTrue(get_scheme(layout, 'scripts', vars=vars) in paths)

        pybin = path.join(get_scheme(layout, 'scripts', vars=vars), 'python.py')
        self.assertTrue(path.exists(pybin))

        pyrc = path.join(self.virtualenv, 'pythonrc.py')
        self.assertTrue(path.exists(pyrc))

        content = open(pyrc, 'r').read()
        self.assertFalse("scheme = 'custom'" in content)


########NEW FILE########
__FILENAME__ = test_rvirtualenv

import sys
import os
from os import path
from subprocess import Popen, PIPE
import textwrap
import logging

from tests.helpers import InTempTestCase, relpath

from rvirtualenv import main
from rvirtualenv.rvirtualenvinstall.scheme import get_scheme, guess_scheme


class TestRVirtualEnv(InTempTestCase):
    def setUp(self):
        super(TestRVirtualEnv, self).setUp()

        vars = {'base': self.virtualenv}
        self.python = path.join(get_scheme(guess_scheme(), 'scripts', vars=vars), 'python.py')

    def install_venv_in_isolation(self, virtualenv=None, sitepackages=True, prompt=None):
        '''
        install rvirtualenv itself, but do it in subprocess,
        because of possible interaction with other imported libraries
        (eg: setuptools and its monkeypatching)
        '''
        if virtualenv is None:
            virtualenv = self.virtualenv
        cmd = ('''%s -c "import sys; sys.path.insert(0, %r); '''
               '''from rvirtualenv import create; create(%r, %s, %r)"''') % \
                (sys.executable, self.base, virtualenv, sitepackages, prompt)
        stdout, stderr = self.run_command(cmd)
        self.failUnlessEqual('', stdout.strip())
        self.failUnlessEqual('', stderr.strip())

    def install_venv(self, args=[], virtualenv=None):
        if virtualenv is None:
            virtualenv = self.virtualenv
        argv = [None, virtualenv]
        argv[1:1] = args
        main(argv)

    def run_rvirtualenv_command(self, virtualenv):
        os.chdir(self.directory)
        self.install_venv_in_isolation(virtualenv)

        pythonrc = path.join(virtualenv, 'pythonrc.py')
        self.assertTrue(path.exists(pythonrc))

        self.assertTrue(path.exists(self.python))

    def test_rvirtualenv_command_creates_distdirs_given_absolute(self):
        self.run_rvirtualenv_command(self.virtualenv)

    def test_rvirtualenv_command_creates_distdirs_given_relative(self):
        self.run_rvirtualenv_command('PY')

    def run_command(self, cmd):
        shell = sys.platform != 'win32'
        p = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=shell)
        return map(lambda b: b.decode(sys.stdout.encoding or 'UTF-8'), p.communicate())

    def test_python_itself(self):
        self.install_venv()

        cmd = '%s %s -c "print(128)"' % (sys.executable, self.python)
        stdout, stderr = self.run_command(cmd)
        self.failUnlessEqual('128', stdout.strip())

    def test_venv_without_site_packages(self):
        '''
        setuptools installed system-wide is needed for this test
        '''
        v1 = path.join(self.directory, 'PY1')
        py1 = path.join(get_scheme(guess_scheme(), 'scripts', vars={'base': v1}), 'python.py')
        self.install_venv(args=[], virtualenv=v1)
        cmd = '%s %s -c "import setuptools"' % (sys.executable, py1)
        stdout, stderr = self.run_command(cmd)
        self.failUnlessEqual('', stderr.strip())
        self.failUnlessEqual('', stdout.strip())

        v2 = path.join(self.directory, 'PY2')
        py2 = path.join(get_scheme(guess_scheme(), 'scripts', vars={'base': v2}), 'python.py')
        self.install_venv(args=['--no-site-packages'], virtualenv=v2)
        cmd = '%s %s -c "import setuptools"' % (sys.executable, py2)
        stdout, stderr = self.run_command(cmd)
        self.assertTrue('ImportError: No module named setuptools' in stderr)

    def test_run_python_script(self):
        self.install_venv()

        script = path.join(self.base, 'tests', 'scripts','print.py')
        cmd = '%s %s %s' % (sys.executable, self.python, script)
        stdout, stderr = self.run_command(cmd)
        self.failUnlessEqual('', stdout)

    def test_run_python_script_with_args(self):
        self.install_venv()

        script = path.join(self.base, 'tests', 'scripts','print.py')
        cmd = '%s %s %s a b c' % (sys.executable, self.python, script)
        stdout, stderr = self.run_command(cmd)
        self.failUnlessEqual("['a', 'b', 'c']", stdout.strip())

    def install_some_way(self, inst_type, inst_command='install'):
        self.install_venv()

        os.chdir(path.join(self.base, 'tests', 'installs',
            'venvtest-%s' % inst_type))
        inst = '%s %s setup.py %s' % \
                (sys.executable, self.python, inst_command)
        stdout, stderr = self.run_command(inst)
        os.chdir(self.oldcwd)

        logging.info('stdout:')
        logging.info(stdout)
        logging.info('stderr:')
        logging.info(stderr)

        self.failUnlessEqual('', stderr)

        cmd = '%s %s -c "import venvtest; print(venvtest.__versionstr__)"' % \
                (sys.executable, self.python)
        stdout, stderr = self.run_command(cmd)
        expected = '0.1.0'
        self.failUnlessEqual(expected, stdout.strip())

        cmd = '%s %s -c "import venvtest; print(venvtest.__file__)"' % \
                (sys.executable, self.python)
        stdout, stderr = self.run_command(cmd)
        a = len(self.virtualenv)
        b = -len('venvtest.pyX')
        env = stdout.strip()[:a]
        mod = stdout.strip()[b:]
        pth = stdout.strip()[a:b]

        logging.info(pth)

        self.failUnlessEqual(self.virtualenv, env)
        # it could be *.py or *.pyc - depending on distro
        self.failUnlessEqual('venvtest.py', mod.strip(r'\c/'))

    def test_install_distutils_way(self):
        self.install_some_way('distutils')

    def test_install_setuptools_way(self):
        '''
        this test should skip if you don't have setuptools
        but other tests could fail too..
        '''
        inst_command = ('install'
                ' --single-version-externally-managed'
                ' --record %s' % path.join(self.directory, 'record.log'))
        self.install_some_way('setuptools', inst_command=inst_command)

    def activate_command_unix(self):
        scripts = relpath(path.dirname(self.python), self.directory)
        activate = 'source %s' % path.join(scripts, 'activate')
        deactivate = 'deactivate'
        run_command = 'bash run'
        run_file = 'run'
        shebang = '#!/bin/sh'
        self.activate_command(activate, deactivate,
            run_command, run_file, shebang)

    def activate_command_win(self):
        scripts = relpath(path.dirname(self.python), self.directory)
        activate = 'call %s' % path.join(scripts, 'activate.bat')
        deactivate = 'call deactivate.bat'
        run_command = 'run.bat'
        run_file = 'run.bat'
        shebang = '@echo off'
        out_filter = lambda x: x.lower()
        self.activate_command(activate, deactivate,
            run_command, run_file, shebang, out_filter)

    def activate_command(self, activate, deactivate,
            run_command, run_file, shebang, out_filter=lambda x:x):
        os.chdir(self.directory)
        self.install_venv()
        f = open(run_file, 'w')
        f.write(textwrap.dedent('''
            %s
            %s
            python -c "import rvirtualenvkeep; print(rvirtualenvkeep.__file__)"
            %s
        ''' % (shebang, activate, deactivate)).strip())
        f.close()
        stdout, stderr = self.run_command(run_command)
        stdout = out_filter(stdout)

        '''
        from shutil import copytree, rmtree
        tempdir = path.join(self.base, 'TSTPY')
        rmtree(tempdir, True)
        copytree(self.directory, tempdir)
        '''

        self.failUnlessEqual(stderr.strip(), '')
        self.assertTrue(stdout.strip().startswith(path.realpath(self.directory)))
        self.assertTrue(
            stdout.strip().endswith('rvirtualenvkeep.pyo') or \
            stdout.strip().endswith('rvirtualenvkeep.pyc') or \
            stdout.strip().endswith('rvirtualenvkeep.py')
            )

    def test_activate_command(self):
        if sys.platform == 'win32':
            self.activate_command_win()
        else:
            self.activate_command_unix()

    def something_is_bad_on_win32_and_subprocess(self, py, command=None):
        replace_command = command

        if sys.platform == 'win32':
            name = 'pokus.bat'
            command = name
            bat = ('@echo off', '"%s" pokus.py' % sys.executable,)
        else:
            name = 'pokus.sh'
            command = 'sh pokus.sh'
            bat = ('#!/bin/sh', 'python pokus.py',)

        if replace_command is not None:
            command = replace_command

        write = '\n'.join(py)
        f = open('pokus.py', 'w'); f.write(write); f.close()

        write = '\n'.join(bat)
        f = open(name, 'w'); f.write(write); f.close()

        shell = True
        p = Popen(command, stdout=PIPE, stderr=PIPE, shell=shell)
        stdout, stderr = map(
            lambda b: b.decode(sys.stdout.encoding or 'UTF-8'), p.communicate())
        self.failUnlessEqual('128', stdout.strip())

    def test_something_is_bad_on_win32_and_os_system(self):
        py = ('import os', 'os.system("echo 128")')
        self.something_is_bad_on_win32_and_subprocess(py)

    def test_something_is_bad_on_win32_and_popen(self):
        py = (
            'from subprocess import Popen, PIPE',
            'p = Popen("echo 128", shell=True)',
            'p.communicate()',
        )
        self.something_is_bad_on_win32_and_subprocess(py)

    def test_something_is_bad_on_win32_but_this_works(self):
        py = ('import os', 'os.system("echo 128")')
        #command = 'call pokus.bat' # this doesn't work either
        command = '"%s" pokus.py' % sys.executable
        self.something_is_bad_on_win32_and_subprocess(py, command)


########NEW FILE########
