__FILENAME__ = virtualenv
#!/usr/bin/env python
"""Create a "virtual" Python installation
"""

# If you change the version here, change it in setup.py
# and docs/conf.py as well.
__version__ = "1.9.1"  # following best practices
virtualenv_version = __version__  # legacy, again

import base64
import sys
import os
import codecs
import optparse
import re
import shutil
import logging
import tempfile
import zlib
import errno
import glob
import distutils.sysconfig
from distutils.util import strtobool
import struct
import subprocess

if sys.version_info < (2, 5):
    print('ERROR: %s' % sys.exc_info()[1])
    print('ERROR: this script requires Python 2.5 or greater.')
    sys.exit(101)

try:
    set
except NameError:
    from sets import Set as set
try:
    basestring
except NameError:
    basestring = str

try:
    import ConfigParser
except ImportError:
    import configparser as ConfigParser

join = os.path.join
py_version = 'python%s.%s' % (sys.version_info[0], sys.version_info[1])

is_jython = sys.platform.startswith('java')
is_pypy = hasattr(sys, 'pypy_version_info')
is_win = (sys.platform == 'win32')
is_cygwin = (sys.platform == 'cygwin')
is_darwin = (sys.platform == 'darwin')
abiflags = getattr(sys, 'abiflags', '')

user_dir = os.path.expanduser('~')
if is_win:
    default_storage_dir = os.path.join(user_dir, 'virtualenv')
else:
    default_storage_dir = os.path.join(user_dir, '.virtualenv')
default_config_file = os.path.join(default_storage_dir, 'virtualenv.ini')

if is_pypy:
    expected_exe = 'pypy'
elif is_jython:
    expected_exe = 'jython'
else:
    expected_exe = 'python'


REQUIRED_MODULES = ['os', 'posix', 'posixpath', 'nt', 'ntpath', 'genericpath',
                    'fnmatch', 'locale', 'encodings', 'codecs',
                    'stat', 'UserDict', 'readline', 'copy_reg', 'types',
                    're', 'sre', 'sre_parse', 'sre_constants', 'sre_compile',
                    'zlib']

REQUIRED_FILES = ['lib-dynload', 'config']

majver, minver = sys.version_info[:2]
if majver == 2:
    if minver >= 6:
        REQUIRED_MODULES.extend(['warnings', 'linecache', '_abcoll', 'abc'])
    if minver >= 7:
        REQUIRED_MODULES.extend(['_weakrefset'])
    if minver <= 3:
        REQUIRED_MODULES.extend(['sets', '__future__'])
elif majver == 3:
    # Some extra modules are needed for Python 3, but different ones
    # for different versions.
    REQUIRED_MODULES.extend(['_abcoll', 'warnings', 'linecache', 'abc', 'io',
                             '_weakrefset', 'copyreg', 'tempfile', 'random',
                             '__future__', 'collections', 'keyword', 'tarfile',
                             'shutil', 'struct', 'copy', 'tokenize', 'token',
                             'functools', 'heapq', 'bisect', 'weakref',
                             'reprlib'])
    if minver >= 2:
        REQUIRED_FILES[-1] = 'config-%s' % majver
    if minver == 3:
        import sysconfig
        platdir = sysconfig.get_config_var('PLATDIR')
        REQUIRED_FILES.append(platdir)
        # The whole list of 3.3 modules is reproduced below - the current
        # uncommented ones are required for 3.3 as of now, but more may be
        # added as 3.3 development continues.
        REQUIRED_MODULES.extend([
            #"aifc",
            #"antigravity",
            #"argparse",
            #"ast",
            #"asynchat",
            #"asyncore",
            "base64",
            #"bdb",
            #"binhex",
            #"bisect",
            #"calendar",
            #"cgi",
            #"cgitb",
            #"chunk",
            #"cmd",
            #"codeop",
            #"code",
            #"colorsys",
            #"_compat_pickle",
            #"compileall",
            #"concurrent",
            #"configparser",
            #"contextlib",
            #"cProfile",
            #"crypt",
            #"csv",
            #"ctypes",
            #"curses",
            #"datetime",
            #"dbm",
            #"decimal",
            #"difflib",
            #"dis",
            #"doctest",
            #"dummy_threading",
            "_dummy_thread",
            #"email",
            #"filecmp",
            #"fileinput",
            #"formatter",
            #"fractions",
            #"ftplib",
            #"functools",
            #"getopt",
            #"getpass",
            #"gettext",
            #"glob",
            #"gzip",
            "hashlib",
            #"heapq",
            "hmac",
            #"html",
            #"http",
            #"idlelib",
            #"imaplib",
            #"imghdr",
            "imp",
            "importlib",
            #"inspect",
            #"json",
            #"lib2to3",
            #"logging",
            #"macpath",
            #"macurl2path",
            #"mailbox",
            #"mailcap",
            #"_markupbase",
            #"mimetypes",
            #"modulefinder",
            #"multiprocessing",
            #"netrc",
            #"nntplib",
            #"nturl2path",
            #"numbers",
            #"opcode",
            #"optparse",
            #"os2emxpath",
            #"pdb",
            #"pickle",
            #"pickletools",
            #"pipes",
            #"pkgutil",
            #"platform",
            #"plat-linux2",
            #"plistlib",
            #"poplib",
            #"pprint",
            #"profile",
            #"pstats",
            #"pty",
            #"pyclbr",
            #"py_compile",
            #"pydoc_data",
            #"pydoc",
            #"_pyio",
            #"queue",
            #"quopri",
            #"reprlib",
            "rlcompleter",
            #"runpy",
            #"sched",
            #"shelve",
            #"shlex",
            #"smtpd",
            #"smtplib",
            #"sndhdr",
            #"socket",
            #"socketserver",
            #"sqlite3",
            #"ssl",
            #"stringprep",
            #"string",
            #"_strptime",
            #"subprocess",
            #"sunau",
            #"symbol",
            #"symtable",
            #"sysconfig",
            #"tabnanny",
            #"telnetlib",
            #"test",
            #"textwrap",
            #"this",
            #"_threading_local",
            #"threading",
            #"timeit",
            #"tkinter",
            #"tokenize",
            #"token",
            #"traceback",
            #"trace",
            #"tty",
            #"turtledemo",
            #"turtle",
            #"unittest",
            #"urllib",
            #"uuid",
            #"uu",
            #"wave",
            #"weakref",
            #"webbrowser",
            #"wsgiref",
            #"xdrlib",
            #"xml",
            #"xmlrpc",
            #"zipfile",
        ])

if is_pypy:
    # these are needed to correctly display the exceptions that may happen
    # during the bootstrap
    REQUIRED_MODULES.extend(['traceback', 'linecache'])

class Logger(object):

    """
    Logging object for use in command-line script.  Allows ranges of
    levels, to avoid some redundancy of displayed information.
    """

    DEBUG = logging.DEBUG
    INFO = logging.INFO
    NOTIFY = (logging.INFO+logging.WARN)/2
    WARN = WARNING = logging.WARN
    ERROR = logging.ERROR
    FATAL = logging.FATAL

    LEVELS = [DEBUG, INFO, NOTIFY, WARN, ERROR, FATAL]

    def __init__(self, consumers):
        self.consumers = consumers
        self.indent = 0
        self.in_progress = None
        self.in_progress_hanging = False

    def debug(self, msg, *args, **kw):
        self.log(self.DEBUG, msg, *args, **kw)
    def info(self, msg, *args, **kw):
        self.log(self.INFO, msg, *args, **kw)
    def notify(self, msg, *args, **kw):
        self.log(self.NOTIFY, msg, *args, **kw)
    def warn(self, msg, *args, **kw):
        self.log(self.WARN, msg, *args, **kw)
    def error(self, msg, *args, **kw):
        self.log(self.ERROR, msg, *args, **kw)
    def fatal(self, msg, *args, **kw):
        self.log(self.FATAL, msg, *args, **kw)
    def log(self, level, msg, *args, **kw):
        if args:
            if kw:
                raise TypeError(
                    "You may give positional or keyword arguments, not both")
        args = args or kw
        rendered = None
        for consumer_level, consumer in self.consumers:
            if self.level_matches(level, consumer_level):
                if (self.in_progress_hanging
                    and consumer in (sys.stdout, sys.stderr)):
                    self.in_progress_hanging = False
                    sys.stdout.write('\n')
                    sys.stdout.flush()
                if rendered is None:
                    if args:
                        rendered = msg % args
                    else:
                        rendered = msg
                    rendered = ' '*self.indent + rendered
                if hasattr(consumer, 'write'):
                    consumer.write(rendered+'\n')
                else:
                    consumer(rendered)

    def start_progress(self, msg):
        assert not self.in_progress, (
            "Tried to start_progress(%r) while in_progress %r"
            % (msg, self.in_progress))
        if self.level_matches(self.NOTIFY, self._stdout_level()):
            sys.stdout.write(msg)
            sys.stdout.flush()
            self.in_progress_hanging = True
        else:
            self.in_progress_hanging = False
        self.in_progress = msg

    def end_progress(self, msg='done.'):
        assert self.in_progress, (
            "Tried to end_progress without start_progress")
        if self.stdout_level_matches(self.NOTIFY):
            if not self.in_progress_hanging:
                # Some message has been printed out since start_progress
                sys.stdout.write('...' + self.in_progress + msg + '\n')
                sys.stdout.flush()
            else:
                sys.stdout.write(msg + '\n')
                sys.stdout.flush()
        self.in_progress = None
        self.in_progress_hanging = False

    def show_progress(self):
        """If we are in a progress scope, and no log messages have been
        shown, write out another '.'"""
        if self.in_progress_hanging:
            sys.stdout.write('.')
            sys.stdout.flush()

    def stdout_level_matches(self, level):
        """Returns true if a message at this level will go to stdout"""
        return self.level_matches(level, self._stdout_level())

    def _stdout_level(self):
        """Returns the level that stdout runs at"""
        for level, consumer in self.consumers:
            if consumer is sys.stdout:
                return level
        return self.FATAL

    def level_matches(self, level, consumer_level):
        """
        >>> l = Logger([])
        >>> l.level_matches(3, 4)
        False
        >>> l.level_matches(3, 2)
        True
        >>> l.level_matches(slice(None, 3), 3)
        False
        >>> l.level_matches(slice(None, 3), 2)
        True
        >>> l.level_matches(slice(1, 3), 1)
        True
        >>> l.level_matches(slice(2, 3), 1)
        False
        """
        if isinstance(level, slice):
            start, stop = level.start, level.stop
            if start is not None and start > consumer_level:
                return False
            if stop is not None and stop <= consumer_level:
                return False
            return True
        else:
            return level >= consumer_level

    #@classmethod
    def level_for_integer(cls, level):
        levels = cls.LEVELS
        if level < 0:
            return levels[0]
        if level >= len(levels):
            return levels[-1]
        return levels[level]

    level_for_integer = classmethod(level_for_integer)

# create a silent logger just to prevent this from being undefined
# will be overridden with requested verbosity main() is called.
logger = Logger([(Logger.LEVELS[-1], sys.stdout)])

def mkdir(path):
    if not os.path.exists(path):
        logger.info('Creating %s', path)
        os.makedirs(path)
    else:
        logger.info('Directory %s already exists', path)

def copyfileordir(src, dest):
    if os.path.isdir(src):
        shutil.copytree(src, dest, True)
    else:
        shutil.copy2(src, dest)

def copyfile(src, dest, symlink=True):
    if not os.path.exists(src):
        # Some bad symlink in the src
        logger.warn('Cannot find file %s (bad symlink)', src)
        return
    if os.path.exists(dest):
        logger.debug('File %s already exists', dest)
        return
    if not os.path.exists(os.path.dirname(dest)):
        logger.info('Creating parent directories for %s' % os.path.dirname(dest))
        os.makedirs(os.path.dirname(dest))
    if not os.path.islink(src):
        srcpath = os.path.abspath(src)
    else:
        srcpath = os.readlink(src)
    if symlink and hasattr(os, 'symlink') and not is_win:
        logger.info('Symlinking %s', dest)
        try:
            os.symlink(srcpath, dest)
        except (OSError, NotImplementedError):
            logger.info('Symlinking failed, copying to %s', dest)
            copyfileordir(src, dest)
    else:
        logger.info('Copying to %s', dest)
        copyfileordir(src, dest)

def writefile(dest, content, overwrite=True):
    if not os.path.exists(dest):
        logger.info('Writing %s', dest)
        f = open(dest, 'wb')
        f.write(content.encode('utf-8'))
        f.close()
        return
    else:
        f = open(dest, 'rb')
        c = f.read()
        f.close()
        if c != content.encode("utf-8"):
            if not overwrite:
                logger.notify('File %s exists with different content; not overwriting', dest)
                return
            logger.notify('Overwriting %s with new content', dest)
            f = open(dest, 'wb')
            f.write(content.encode('utf-8'))
            f.close()
        else:
            logger.info('Content %s already in place', dest)

def rmtree(dir):
    if os.path.exists(dir):
        logger.notify('Deleting tree %s', dir)
        shutil.rmtree(dir)
    else:
        logger.info('Do not need to delete %s; already gone', dir)

def make_exe(fn):
    if hasattr(os, 'chmod'):
        oldmode = os.stat(fn).st_mode & 0xFFF # 0o7777
        newmode = (oldmode | 0x16D) & 0xFFF # 0o555, 0o7777
        os.chmod(fn, newmode)
        logger.info('Changed mode of %s to %s', fn, oct(newmode))

def _find_file(filename, dirs):
    for dir in reversed(dirs):
        files = glob.glob(os.path.join(dir, filename))
        if files and os.path.isfile(files[0]):
            return True, files[0]
    return False, filename

def _install_req(py_executable, unzip=False, distribute=False,
                 search_dirs=None, never_download=False):

    if search_dirs is None:
        search_dirs = file_search_dirs()

    if not distribute:
        egg_path = 'setuptools-*-py%s.egg' % sys.version[:3]
        found, egg_path = _find_file(egg_path, search_dirs)
        project_name = 'setuptools'
        bootstrap_script = EZ_SETUP_PY
        tgz_path = None
    else:
        # Look for a distribute egg (these are not distributed by default,
        # but can be made available by the user)
        egg_path = 'distribute-*-py%s.egg' % sys.version[:3]
        found, egg_path = _find_file(egg_path, search_dirs)
        project_name = 'distribute'
        if found:
            tgz_path = None
            bootstrap_script = DISTRIBUTE_FROM_EGG_PY
        else:
            # Fall back to sdist
            # NB: egg_path is not None iff tgz_path is None
            # iff bootstrap_script is a generic setup script accepting
            # the standard arguments.
            egg_path = None
            tgz_path = 'distribute-*.tar.gz'
            found, tgz_path = _find_file(tgz_path, search_dirs)
            bootstrap_script = DISTRIBUTE_SETUP_PY

    if is_jython and os._name == 'nt':
        # Jython's .bat sys.executable can't handle a command line
        # argument with newlines
        fd, ez_setup = tempfile.mkstemp('.py')
        os.write(fd, bootstrap_script)
        os.close(fd)
        cmd = [py_executable, ez_setup]
    else:
        cmd = [py_executable, '-c', bootstrap_script]
    if unzip and egg_path:
        cmd.append('--always-unzip')
    env = {}
    remove_from_env = ['__PYVENV_LAUNCHER__']
    if logger.stdout_level_matches(logger.DEBUG) and egg_path:
        cmd.append('-v')

    old_chdir = os.getcwd()
    if egg_path is not None and os.path.exists(egg_path):
        logger.info('Using existing %s egg: %s' % (project_name, egg_path))
        cmd.append(egg_path)
        if os.environ.get('PYTHONPATH'):
            env['PYTHONPATH'] = egg_path + os.path.pathsep + os.environ['PYTHONPATH']
        else:
            env['PYTHONPATH'] = egg_path
    elif tgz_path is not None and os.path.exists(tgz_path):
        # Found a tgz source dist, let's chdir
        logger.info('Using existing %s egg: %s' % (project_name, tgz_path))
        os.chdir(os.path.dirname(tgz_path))
        # in this case, we want to be sure that PYTHONPATH is unset (not
        # just empty, really unset), else CPython tries to import the
        # site.py that it's in virtualenv_support
        remove_from_env.append('PYTHONPATH')
    elif never_download:
        logger.fatal("Can't find any local distributions of %s to install "
                     "and --never-download is set.  Either re-run virtualenv "
                     "without the --never-download option, or place a %s "
                     "distribution (%s) in one of these "
                     "locations: %r" % (project_name, project_name,
                                        egg_path or tgz_path,
                                        search_dirs))
        sys.exit(1)
    elif egg_path:
        logger.info('No %s egg found; downloading' % project_name)
        cmd.extend(['--always-copy', '-U', project_name])
    else:
        logger.info('No %s tgz found; downloading' % project_name)
    logger.start_progress('Installing %s...' % project_name)
    logger.indent += 2
    cwd = None
    if project_name == 'distribute':
        env['DONT_PATCH_SETUPTOOLS'] = 'true'

    def _filter_ez_setup(line):
        return filter_ez_setup(line, project_name)

    if not os.access(os.getcwd(), os.W_OK):
        cwd = tempfile.mkdtemp()
        if tgz_path is not None and os.path.exists(tgz_path):
            # the current working dir is hostile, let's copy the
            # tarball to a temp dir
            target = os.path.join(cwd, os.path.split(tgz_path)[-1])
            shutil.copy(tgz_path, target)
    try:
        call_subprocess(cmd, show_stdout=False,
                        filter_stdout=_filter_ez_setup,
                        extra_env=env,
                        remove_from_env=remove_from_env,
                        cwd=cwd)
    finally:
        logger.indent -= 2
        logger.end_progress()
        if cwd is not None:
            shutil.rmtree(cwd)
        if os.getcwd() != old_chdir:
            os.chdir(old_chdir)
        if is_jython and os._name == 'nt':
            os.remove(ez_setup)

def file_search_dirs():
    here = os.path.dirname(os.path.abspath(__file__))
    dirs = ['.', here,
            join(here, 'virtualenv_support')]
    if os.path.splitext(os.path.dirname(__file__))[0] != 'virtualenv':
        # Probably some boot script; just in case virtualenv is installed...
        try:
            import virtualenv
        except ImportError:
            pass
        else:
            dirs.append(os.path.join(os.path.dirname(virtualenv.__file__), 'virtualenv_support'))
    return [d for d in dirs if os.path.isdir(d)]

def install_setuptools(py_executable, unzip=False,
                       search_dirs=None, never_download=False):
    _install_req(py_executable, unzip,
                 search_dirs=search_dirs, never_download=never_download)

def install_distribute(py_executable, unzip=False,
                       search_dirs=None, never_download=False):
    _install_req(py_executable, unzip, distribute=True,
                 search_dirs=search_dirs, never_download=never_download)

_pip_re = re.compile(r'^pip-.*(zip|tar.gz|tar.bz2|tgz|tbz)$', re.I)
def install_pip(py_executable, search_dirs=None, never_download=False):
    if search_dirs is None:
        search_dirs = file_search_dirs()

    filenames = []
    for dir in search_dirs:
        filenames.extend([join(dir, fn) for fn in os.listdir(dir)
                          if _pip_re.search(fn)])
    filenames = [(os.path.basename(filename).lower(), i, filename) for i, filename in enumerate(filenames)]
    filenames.sort()
    filenames = [filename for basename, i, filename in filenames]
    if not filenames:
        filename = 'pip'
    else:
        filename = filenames[-1]
    easy_install_script = 'easy_install'
    if is_win:
        easy_install_script = 'easy_install-script.py'
    # There's two subtle issues here when invoking easy_install.
    # 1. On unix-like systems the easy_install script can *only* be executed
    #    directly if its full filesystem path is no longer than 78 characters.
    # 2. A work around to [1] is to use the `python path/to/easy_install foo`
    #    pattern, but that breaks if the path contains non-ASCII characters, as
    #    you can't put the file encoding declaration before the shebang line.
    # The solution is to use Python's -x flag to skip the first line of the
    # script (and any ASCII decoding errors that may have occurred in that line)
    cmd = [py_executable, '-x', join(os.path.dirname(py_executable), easy_install_script), filename]
    # jython and pypy don't yet support -x
    if is_jython or is_pypy:
        cmd.remove('-x')
    if filename == 'pip':
        if never_download:
            logger.fatal("Can't find any local distributions of pip to install "
                         "and --never-download is set.  Either re-run virtualenv "
                         "without the --never-download option, or place a pip "
                         "source distribution (zip/tar.gz/tar.bz2) in one of these "
                         "locations: %r" % search_dirs)
            sys.exit(1)
        logger.info('Installing pip from network...')
    else:
        logger.info('Installing existing %s distribution: %s' % (
                os.path.basename(filename), filename))
    logger.start_progress('Installing pip...')
    logger.indent += 2
    def _filter_setup(line):
        return filter_ez_setup(line, 'pip')
    try:
        call_subprocess(cmd, show_stdout=False,
                        filter_stdout=_filter_setup)
    finally:
        logger.indent -= 2
        logger.end_progress()

def filter_ez_setup(line, project_name='setuptools'):
    if not line.strip():
        return Logger.DEBUG
    if project_name == 'distribute':
        for prefix in ('Extracting', 'Now working', 'Installing', 'Before',
                       'Scanning', 'Setuptools', 'Egg', 'Already',
                       'running', 'writing', 'reading', 'installing',
                       'creating', 'copying', 'byte-compiling', 'removing',
                       'Processing'):
            if line.startswith(prefix):
                return Logger.DEBUG
        return Logger.DEBUG
    for prefix in ['Reading ', 'Best match', 'Processing setuptools',
                   'Copying setuptools', 'Adding setuptools',
                   'Installing ', 'Installed ']:
        if line.startswith(prefix):
            return Logger.DEBUG
    return Logger.INFO


class UpdatingDefaultsHelpFormatter(optparse.IndentedHelpFormatter):
    """
    Custom help formatter for use in ConfigOptionParser that updates
    the defaults before expanding them, allowing them to show up correctly
    in the help listing
    """
    def expand_default(self, option):
        if self.parser is not None:
            self.parser.update_defaults(self.parser.defaults)
        return optparse.IndentedHelpFormatter.expand_default(self, option)


class ConfigOptionParser(optparse.OptionParser):
    """
    Custom option parser which updates its defaults by by checking the
    configuration files and environmental variables
    """
    def __init__(self, *args, **kwargs):
        self.config = ConfigParser.RawConfigParser()
        self.files = self.get_config_files()
        self.config.read(self.files)
        optparse.OptionParser.__init__(self, *args, **kwargs)

    def get_config_files(self):
        config_file = os.environ.get('VIRTUALENV_CONFIG_FILE', False)
        if config_file and os.path.exists(config_file):
            return [config_file]
        return [default_config_file]

    def update_defaults(self, defaults):
        """
        Updates the given defaults with values from the config files and
        the environ. Does a little special handling for certain types of
        options (lists).
        """
        # Then go and look for the other sources of configuration:
        config = {}
        # 1. config files
        config.update(dict(self.get_config_section('virtualenv')))
        # 2. environmental variables
        config.update(dict(self.get_environ_vars()))
        # Then set the options with those values
        for key, val in config.items():
            key = key.replace('_', '-')
            if not key.startswith('--'):
                key = '--%s' % key  # only prefer long opts
            option = self.get_option(key)
            if option is not None:
                # ignore empty values
                if not val:
                    continue
                # handle multiline configs
                if option.action == 'append':
                    val = val.split()
                else:
                    option.nargs = 1
                if option.action == 'store_false':
                    val = not strtobool(val)
                elif option.action in ('store_true', 'count'):
                    val = strtobool(val)
                try:
                    val = option.convert_value(key, val)
                except optparse.OptionValueError:
                    e = sys.exc_info()[1]
                    print("An error occured during configuration: %s" % e)
                    sys.exit(3)
                defaults[option.dest] = val
        return defaults

    def get_config_section(self, name):
        """
        Get a section of a configuration
        """
        if self.config.has_section(name):
            return self.config.items(name)
        return []

    def get_environ_vars(self, prefix='VIRTUALENV_'):
        """
        Returns a generator with all environmental vars with prefix VIRTUALENV
        """
        for key, val in os.environ.items():
            if key.startswith(prefix):
                yield (key.replace(prefix, '').lower(), val)

    def get_default_values(self):
        """
        Overridding to make updating the defaults after instantiation of
        the option parser possible, update_defaults() does the dirty work.
        """
        if not self.process_default_values:
            # Old, pre-Optik 1.5 behaviour.
            return optparse.Values(self.defaults)

        defaults = self.update_defaults(self.defaults.copy())  # ours
        for option in self._get_all_options():
            default = defaults.get(option.dest)
            if isinstance(default, basestring):
                opt_str = option.get_opt_string()
                defaults[option.dest] = option.check_value(opt_str, default)
        return optparse.Values(defaults)


def main():
    parser = ConfigOptionParser(
        version=virtualenv_version,
        usage="%prog [OPTIONS] DEST_DIR",
        formatter=UpdatingDefaultsHelpFormatter())

    parser.add_option(
        '-v', '--verbose',
        action='count',
        dest='verbose',
        default=0,
        help="Increase verbosity")

    parser.add_option(
        '-q', '--quiet',
        action='count',
        dest='quiet',
        default=0,
        help='Decrease verbosity')

    parser.add_option(
        '-p', '--python',
        dest='python',
        metavar='PYTHON_EXE',
        help='The Python interpreter to use, e.g., --python=python2.5 will use the python2.5 '
        'interpreter to create the new environment.  The default is the interpreter that '
        'virtualenv was installed with (%s)' % sys.executable)

    parser.add_option(
        '--clear',
        dest='clear',
        action='store_true',
        help="Clear out the non-root install and start from scratch")

    parser.set_defaults(system_site_packages=False)
    parser.add_option(
        '--no-site-packages',
        dest='system_site_packages',
        action='store_false',
        help="Don't give access to the global site-packages dir to the "
             "virtual environment (default)")

    parser.add_option(
        '--system-site-packages',
        dest='system_site_packages',
        action='store_true',
        help="Give access to the global site-packages dir to the "
             "virtual environment")

    parser.add_option(
        '--unzip-setuptools',
        dest='unzip_setuptools',
        action='store_true',
        help="Unzip Setuptools or Distribute when installing it")

    parser.add_option(
        '--relocatable',
        dest='relocatable',
        action='store_true',
        help='Make an EXISTING virtualenv environment relocatable.  '
        'This fixes up scripts and makes all .pth files relative')

    parser.add_option(
        '--distribute', '--use-distribute',  # the second option is for legacy reasons here. Hi Kenneth!
        dest='use_distribute',
        action='store_true',
        help='Use Distribute instead of Setuptools. Set environ variable '
        'VIRTUALENV_DISTRIBUTE to make it the default ')

    parser.add_option(
        '--no-setuptools',
        dest='no_setuptools',
        action='store_true',
        help='Do not install distribute/setuptools (or pip) '
        'in the new virtualenv.')

    parser.add_option(
        '--no-pip',
        dest='no_pip',
        action='store_true',
        help='Do not install pip in the new virtualenv.')

    parser.add_option(
        '--setuptools',
        dest='use_distribute',
        action='store_false',
        help='Use Setuptools instead of Distribute.  Set environ variable '
        'VIRTUALENV_SETUPTOOLS to make it the default ')

    # Set this to True to use distribute by default, even in Python 2.
    parser.set_defaults(use_distribute=False)

    default_search_dirs = file_search_dirs()
    parser.add_option(
        '--extra-search-dir',
        dest="search_dirs",
        action="append",
        default=default_search_dirs,
        help="Directory to look for setuptools/distribute/pip distributions in. "
        "You can add any number of additional --extra-search-dir paths.")

    parser.add_option(
        '--never-download',
        dest="never_download",
        action="store_true",
        help="Never download anything from the network.  Instead, virtualenv will fail "
        "if local distributions of setuptools/distribute/pip are not present.")

    parser.add_option(
        '--prompt',
        dest='prompt',
        help='Provides an alternative prompt prefix for this environment')

    if 'extend_parser' in globals():
        extend_parser(parser)

    options, args = parser.parse_args()

    global logger

    if 'adjust_options' in globals():
        adjust_options(options, args)

    verbosity = options.verbose - options.quiet
    logger = Logger([(Logger.level_for_integer(2 - verbosity), sys.stdout)])

    if options.python and not os.environ.get('VIRTUALENV_INTERPRETER_RUNNING'):
        env = os.environ.copy()
        interpreter = resolve_interpreter(options.python)
        if interpreter == sys.executable:
            logger.warn('Already using interpreter %s' % interpreter)
        else:
            logger.notify('Running virtualenv with interpreter %s' % interpreter)
            env['VIRTUALENV_INTERPRETER_RUNNING'] = 'true'
            file = __file__
            if file.endswith('.pyc'):
                file = file[:-1]
            popen = subprocess.Popen([interpreter, file] + sys.argv[1:], env=env)
            raise SystemExit(popen.wait())

    # Force --distribute on Python 3, since setuptools is not available.
    if majver > 2:
        options.use_distribute = True

    if os.environ.get('PYTHONDONTWRITEBYTECODE') and not options.use_distribute:
        print(
            "The PYTHONDONTWRITEBYTECODE environment variable is "
            "not compatible with setuptools. Either use --distribute "
            "or unset PYTHONDONTWRITEBYTECODE.")
        sys.exit(2)
    if not args:
        print('You must provide a DEST_DIR')
        parser.print_help()
        sys.exit(2)
    if len(args) > 1:
        print('There must be only one argument: DEST_DIR (you gave %s)' % (
            ' '.join(args)))
        parser.print_help()
        sys.exit(2)

    home_dir = args[0]

    if os.environ.get('WORKING_ENV'):
        logger.fatal('ERROR: you cannot run virtualenv while in a workingenv')
        logger.fatal('Please deactivate your workingenv, then re-run this script')
        sys.exit(3)

    if 'PYTHONHOME' in os.environ:
        logger.warn('PYTHONHOME is set.  You *must* activate the virtualenv before using it')
        del os.environ['PYTHONHOME']

    if options.relocatable:
        make_environment_relocatable(home_dir)
        return

    create_environment(home_dir,
                       site_packages=options.system_site_packages,
                       clear=options.clear,
                       unzip_setuptools=options.unzip_setuptools,
                       use_distribute=options.use_distribute,
                       prompt=options.prompt,
                       search_dirs=options.search_dirs,
                       never_download=options.never_download,
                       no_setuptools=options.no_setuptools,
                       no_pip=options.no_pip)
    if 'after_install' in globals():
        after_install(options, home_dir)

def call_subprocess(cmd, show_stdout=True,
                    filter_stdout=None, cwd=None,
                    raise_on_returncode=True, extra_env=None,
                    remove_from_env=None):
    cmd_parts = []
    for part in cmd:
        if len(part) > 45:
            part = part[:20]+"..."+part[-20:]
        if ' ' in part or '\n' in part or '"' in part or "'" in part:
            part = '"%s"' % part.replace('"', '\\"')
        if hasattr(part, 'decode'):
            try:
                part = part.decode(sys.getdefaultencoding())
            except UnicodeDecodeError:
                part = part.decode(sys.getfilesystemencoding())
        cmd_parts.append(part)
    cmd_desc = ' '.join(cmd_parts)
    if show_stdout:
        stdout = None
    else:
        stdout = subprocess.PIPE
    logger.debug("Running command %s" % cmd_desc)
    if extra_env or remove_from_env:
        env = os.environ.copy()
        if extra_env:
            env.update(extra_env)
        if remove_from_env:
            for varname in remove_from_env:
                env.pop(varname, None)
    else:
        env = None
    try:
        proc = subprocess.Popen(
            cmd, stderr=subprocess.STDOUT, stdin=None, stdout=stdout,
            cwd=cwd, env=env)
    except Exception:
        e = sys.exc_info()[1]
        logger.fatal(
            "Error %s while executing command %s" % (e, cmd_desc))
        raise
    all_output = []
    if stdout is not None:
        stdout = proc.stdout
        encoding = sys.getdefaultencoding()
        fs_encoding = sys.getfilesystemencoding()
        while 1:
            line = stdout.readline()
            try:
                line = line.decode(encoding)
            except UnicodeDecodeError:
                line = line.decode(fs_encoding)
            if not line:
                break
            line = line.rstrip()
            all_output.append(line)
            if filter_stdout:
                level = filter_stdout(line)
                if isinstance(level, tuple):
                    level, line = level
                logger.log(level, line)
                if not logger.stdout_level_matches(level):
                    logger.show_progress()
            else:
                logger.info(line)
    else:
        proc.communicate()
    proc.wait()
    if proc.returncode:
        if raise_on_returncode:
            if all_output:
                logger.notify('Complete output from command %s:' % cmd_desc)
                logger.notify('\n'.join(all_output) + '\n----------------------------------------')
            raise OSError(
                "Command %s failed with error code %s"
                % (cmd_desc, proc.returncode))
        else:
            logger.warn(
                "Command %s had error code %s"
                % (cmd_desc, proc.returncode))


def create_environment(home_dir, site_packages=False, clear=False,
                       unzip_setuptools=False, use_distribute=False,
                       prompt=None, search_dirs=None, never_download=False,
                       no_setuptools=False, no_pip=False):
    """
    Creates a new environment in ``home_dir``.

    If ``site_packages`` is true, then the global ``site-packages/``
    directory will be on the path.

    If ``clear`` is true (default False) then the environment will
    first be cleared.
    """
    home_dir, lib_dir, inc_dir, bin_dir = path_locations(home_dir)

    py_executable = os.path.abspath(install_python(
        home_dir, lib_dir, inc_dir, bin_dir,
        site_packages=site_packages, clear=clear))

    install_distutils(home_dir)

    if not no_setuptools:
        if use_distribute:
            install_distribute(py_executable, unzip=unzip_setuptools,
                               search_dirs=search_dirs, never_download=never_download)
        else:
            install_setuptools(py_executable, unzip=unzip_setuptools,
                               search_dirs=search_dirs, never_download=never_download)

        if not no_pip:
            install_pip(py_executable, search_dirs=search_dirs, never_download=never_download)

    install_activate(home_dir, bin_dir, prompt)

def is_executable_file(fpath):
    return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

def path_locations(home_dir):
    """Return the path locations for the environment (where libraries are,
    where scripts go, etc)"""
    # XXX: We'd use distutils.sysconfig.get_python_inc/lib but its
    # prefix arg is broken: http://bugs.python.org/issue3386
    if is_win:
        # Windows has lots of problems with executables with spaces in
        # the name; this function will remove them (using the ~1
        # format):
        mkdir(home_dir)
        if ' ' in home_dir:
            import ctypes
            GetShortPathName = ctypes.windll.kernel32.GetShortPathNameW
            size = max(len(home_dir)+1, 256)
            buf = ctypes.create_unicode_buffer(size)
            try:
                u = unicode
            except NameError:
                u = str
            ret = GetShortPathName(u(home_dir), buf, size)
            if not ret:
                print('Error: the path "%s" has a space in it' % home_dir)
                print('We could not determine the short pathname for it.')
                print('Exiting.')
                sys.exit(3)
            home_dir = str(buf.value)
        lib_dir = join(home_dir, 'Lib')
        inc_dir = join(home_dir, 'Include')
        bin_dir = join(home_dir, 'Scripts')
    if is_jython:
        lib_dir = join(home_dir, 'Lib')
        inc_dir = join(home_dir, 'Include')
        bin_dir = join(home_dir, 'bin')
    elif is_pypy:
        lib_dir = home_dir
        inc_dir = join(home_dir, 'include')
        bin_dir = join(home_dir, 'bin')
    elif not is_win:
        lib_dir = join(home_dir, 'lib', py_version)
        multiarch_exec = '/usr/bin/multiarch-platform'
        if is_executable_file(multiarch_exec):
            # In Mageia (2) and Mandriva distros the include dir must be like:
            # virtualenv/include/multiarch-x86_64-linux/python2.7
            # instead of being virtualenv/include/python2.7
            p = subprocess.Popen(multiarch_exec, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = p.communicate()
            # stdout.strip is needed to remove newline character
            inc_dir = join(home_dir, 'include', stdout.strip(), py_version + abiflags)
        else:
            inc_dir = join(home_dir, 'include', py_version + abiflags)
        bin_dir = join(home_dir, 'bin')
    return home_dir, lib_dir, inc_dir, bin_dir


def change_prefix(filename, dst_prefix):
    prefixes = [sys.prefix]

    if is_darwin:
        prefixes.extend((
            os.path.join("/Library/Python", sys.version[:3], "site-packages"),
            os.path.join(sys.prefix, "Extras", "lib", "python"),
            os.path.join("~", "Library", "Python", sys.version[:3], "site-packages"),
            # Python 2.6 no-frameworks
            os.path.join("~", ".local", "lib","python", sys.version[:3], "site-packages"),
            # System Python 2.7 on OSX Mountain Lion
            os.path.join("~", "Library", "Python", sys.version[:3], "lib", "python", "site-packages")))

    if hasattr(sys, 'real_prefix'):
        prefixes.append(sys.real_prefix)
    if hasattr(sys, 'base_prefix'):
        prefixes.append(sys.base_prefix)
    prefixes = list(map(os.path.expanduser, prefixes))
    prefixes = list(map(os.path.abspath, prefixes))
    # Check longer prefixes first so we don't split in the middle of a filename
    prefixes = sorted(prefixes, key=len, reverse=True)
    filename = os.path.abspath(filename)
    for src_prefix in prefixes:
        if filename.startswith(src_prefix):
            _, relpath = filename.split(src_prefix, 1)
            if src_prefix != os.sep: # sys.prefix == "/"
                assert relpath[0] == os.sep
                relpath = relpath[1:]
            return join(dst_prefix, relpath)
    assert False, "Filename %s does not start with any of these prefixes: %s" % \
        (filename, prefixes)

def copy_required_modules(dst_prefix):
    import imp
    # If we are running under -p, we need to remove the current
    # directory from sys.path temporarily here, so that we
    # definitely get the modules from the site directory of
    # the interpreter we are running under, not the one
    # virtualenv.py is installed under (which might lead to py2/py3
    # incompatibility issues)
    _prev_sys_path = sys.path
    if os.environ.get('VIRTUALENV_INTERPRETER_RUNNING'):
        sys.path = sys.path[1:]
    try:
        for modname in REQUIRED_MODULES:
            if modname in sys.builtin_module_names:
                logger.info("Ignoring built-in bootstrap module: %s" % modname)
                continue
            try:
                f, filename, _ = imp.find_module(modname)
            except ImportError:
                logger.info("Cannot import bootstrap module: %s" % modname)
            else:
                if f is not None:
                    f.close()
                # special-case custom readline.so on OS X, but not for pypy:
                if modname == 'readline' and sys.platform == 'darwin' and not (
                        is_pypy or filename.endswith(join('lib-dynload', 'readline.so'))):
                    dst_filename = join(dst_prefix, 'lib', 'python%s' % sys.version[:3], 'readline.so')
                else:
                    dst_filename = change_prefix(filename, dst_prefix)
                copyfile(filename, dst_filename)
                if filename.endswith('.pyc'):
                    pyfile = filename[:-1]
                    if os.path.exists(pyfile):
                        copyfile(pyfile, dst_filename[:-1])
    finally:
        sys.path = _prev_sys_path


def subst_path(prefix_path, prefix, home_dir):
    prefix_path = os.path.normpath(prefix_path)
    prefix = os.path.normpath(prefix)
    home_dir = os.path.normpath(home_dir)
    if not prefix_path.startswith(prefix):
        logger.warn('Path not in prefix %r %r', prefix_path, prefix)
        return
    return prefix_path.replace(prefix, home_dir, 1)


def install_python(home_dir, lib_dir, inc_dir, bin_dir, site_packages, clear):
    """Install just the base environment, no distutils patches etc"""
    if sys.executable.startswith(bin_dir):
        print('Please use the *system* python to run this script')
        return

    if clear:
        rmtree(lib_dir)
        ## FIXME: why not delete it?
        ## Maybe it should delete everything with #!/path/to/venv/python in it
        logger.notify('Not deleting %s', bin_dir)

    if hasattr(sys, 'real_prefix'):
        logger.notify('Using real prefix %r' % sys.real_prefix)
        prefix = sys.real_prefix
    elif hasattr(sys, 'base_prefix'):
        logger.notify('Using base prefix %r' % sys.base_prefix)
        prefix = sys.base_prefix
    else:
        prefix = sys.prefix
    mkdir(lib_dir)
    fix_lib64(lib_dir)
    stdlib_dirs = [os.path.dirname(os.__file__)]
    if is_win:
        stdlib_dirs.append(join(os.path.dirname(stdlib_dirs[0]), 'DLLs'))
    elif is_darwin:
        stdlib_dirs.append(join(stdlib_dirs[0], 'site-packages'))
    if hasattr(os, 'symlink'):
        logger.info('Symlinking Python bootstrap modules')
    else:
        logger.info('Copying Python bootstrap modules')
    logger.indent += 2
    try:
        # copy required files...
        for stdlib_dir in stdlib_dirs:
            if not os.path.isdir(stdlib_dir):
                continue
            for fn in os.listdir(stdlib_dir):
                bn = os.path.splitext(fn)[0]
                if fn != 'site-packages' and bn in REQUIRED_FILES:
                    copyfile(join(stdlib_dir, fn), join(lib_dir, fn))
        # ...and modules
        copy_required_modules(home_dir)
    finally:
        logger.indent -= 2
    mkdir(join(lib_dir, 'site-packages'))
    import site
    site_filename = site.__file__
    if site_filename.endswith('.pyc'):
        site_filename = site_filename[:-1]
    elif site_filename.endswith('$py.class'):
        site_filename = site_filename.replace('$py.class', '.py')
    site_filename_dst = change_prefix(site_filename, home_dir)
    site_dir = os.path.dirname(site_filename_dst)
    writefile(site_filename_dst, SITE_PY)
    writefile(join(site_dir, 'orig-prefix.txt'), prefix)
    site_packages_filename = join(site_dir, 'no-global-site-packages.txt')
    if not site_packages:
        writefile(site_packages_filename, '')

    if is_pypy or is_win:
        stdinc_dir = join(prefix, 'include')
    else:
        stdinc_dir = join(prefix, 'include', py_version + abiflags)
    if os.path.exists(stdinc_dir):
        copyfile(stdinc_dir, inc_dir)
    else:
        logger.debug('No include dir %s' % stdinc_dir)

    platinc_dir = distutils.sysconfig.get_python_inc(plat_specific=1)
    if platinc_dir != stdinc_dir:
        platinc_dest = distutils.sysconfig.get_python_inc(
            plat_specific=1, prefix=home_dir)
        if platinc_dir == platinc_dest:
            # Do platinc_dest manually due to a CPython bug;
            # not http://bugs.python.org/issue3386 but a close cousin
            platinc_dest = subst_path(platinc_dir, prefix, home_dir)
        if platinc_dest:
            # PyPy's stdinc_dir and prefix are relative to the original binary
            # (traversing virtualenvs), whereas the platinc_dir is relative to
            # the inner virtualenv and ignores the prefix argument.
            # This seems more evolved than designed.
            copyfile(platinc_dir, platinc_dest)

    # pypy never uses exec_prefix, just ignore it
    if sys.exec_prefix != prefix and not is_pypy:
        if is_win:
            exec_dir = join(sys.exec_prefix, 'lib')
        elif is_jython:
            exec_dir = join(sys.exec_prefix, 'Lib')
        else:
            exec_dir = join(sys.exec_prefix, 'lib', py_version)
        for fn in os.listdir(exec_dir):
            copyfile(join(exec_dir, fn), join(lib_dir, fn))

    if is_jython:
        # Jython has either jython-dev.jar and javalib/ dir, or just
        # jython.jar
        for name in 'jython-dev.jar', 'javalib', 'jython.jar':
            src = join(prefix, name)
            if os.path.exists(src):
                copyfile(src, join(home_dir, name))
        # XXX: registry should always exist after Jython 2.5rc1
        src = join(prefix, 'registry')
        if os.path.exists(src):
            copyfile(src, join(home_dir, 'registry'), symlink=False)
        copyfile(join(prefix, 'cachedir'), join(home_dir, 'cachedir'),
                 symlink=False)

    mkdir(bin_dir)
    py_executable = join(bin_dir, os.path.basename(sys.executable))
    if 'Python.framework' in prefix:
        # OS X framework builds cause validation to break
        # https://github.com/pypa/virtualenv/issues/322
        if os.environ.get('__PYVENV_LAUNCHER__'):
          os.unsetenv('__PYVENV_LAUNCHER__')
        if re.search(r'/Python(?:-32|-64)*$', py_executable):
            # The name of the python executable is not quite what
            # we want, rename it.
            py_executable = os.path.join(
                    os.path.dirname(py_executable), 'python')

    logger.notify('New %s executable in %s', expected_exe, py_executable)
    pcbuild_dir = os.path.dirname(sys.executable)
    pyd_pth = os.path.join(lib_dir, 'site-packages', 'virtualenv_builddir_pyd.pth')
    if is_win and os.path.exists(os.path.join(pcbuild_dir, 'build.bat')):
        logger.notify('Detected python running from build directory %s', pcbuild_dir)
        logger.notify('Writing .pth file linking to build directory for *.pyd files')
        writefile(pyd_pth, pcbuild_dir)
    else:
        pcbuild_dir = None
        if os.path.exists(pyd_pth):
            logger.info('Deleting %s (not Windows env or not build directory python)' % pyd_pth)
            os.unlink(pyd_pth)

    if sys.executable != py_executable:
        ## FIXME: could I just hard link?
        executable = sys.executable
        shutil.copyfile(executable, py_executable)
        make_exe(py_executable)
        if is_win or is_cygwin:
            pythonw = os.path.join(os.path.dirname(sys.executable), 'pythonw.exe')
            if os.path.exists(pythonw):
                logger.info('Also created pythonw.exe')
                shutil.copyfile(pythonw, os.path.join(os.path.dirname(py_executable), 'pythonw.exe'))
            python_d = os.path.join(os.path.dirname(sys.executable), 'python_d.exe')
            python_d_dest = os.path.join(os.path.dirname(py_executable), 'python_d.exe')
            if os.path.exists(python_d):
                logger.info('Also created python_d.exe')
                shutil.copyfile(python_d, python_d_dest)
            elif os.path.exists(python_d_dest):
                logger.info('Removed python_d.exe as it is no longer at the source')
                os.unlink(python_d_dest)
            # we need to copy the DLL to enforce that windows will load the correct one.
            # may not exist if we are cygwin.
            py_executable_dll = 'python%s%s.dll' % (
                sys.version_info[0], sys.version_info[1])
            py_executable_dll_d = 'python%s%s_d.dll' % (
                sys.version_info[0], sys.version_info[1])
            pythondll = os.path.join(os.path.dirname(sys.executable), py_executable_dll)
            pythondll_d = os.path.join(os.path.dirname(sys.executable), py_executable_dll_d)
            pythondll_d_dest = os.path.join(os.path.dirname(py_executable), py_executable_dll_d)
            if os.path.exists(pythondll):
                logger.info('Also created %s' % py_executable_dll)
                shutil.copyfile(pythondll, os.path.join(os.path.dirname(py_executable), py_executable_dll))
            if os.path.exists(pythondll_d):
                logger.info('Also created %s' % py_executable_dll_d)
                shutil.copyfile(pythondll_d, pythondll_d_dest)
            elif os.path.exists(pythondll_d_dest):
                logger.info('Removed %s as the source does not exist' % pythondll_d_dest)
                os.unlink(pythondll_d_dest)
        if is_pypy:
            # make a symlink python --> pypy-c
            python_executable = os.path.join(os.path.dirname(py_executable), 'python')
            if sys.platform in ('win32', 'cygwin'):
                python_executable += '.exe'
            logger.info('Also created executable %s' % python_executable)
            copyfile(py_executable, python_executable)

            if is_win:
                for name in 'libexpat.dll', 'libpypy.dll', 'libpypy-c.dll', 'libeay32.dll', 'ssleay32.dll', 'sqlite.dll':
                    src = join(prefix, name)
                    if os.path.exists(src):
                        copyfile(src, join(bin_dir, name))

    if os.path.splitext(os.path.basename(py_executable))[0] != expected_exe:
        secondary_exe = os.path.join(os.path.dirname(py_executable),
                                     expected_exe)
        py_executable_ext = os.path.splitext(py_executable)[1]
        if py_executable_ext == '.exe':
            # python2.4 gives an extension of '.4' :P
            secondary_exe += py_executable_ext
        if os.path.exists(secondary_exe):
            logger.warn('Not overwriting existing %s script %s (you must use %s)'
                        % (expected_exe, secondary_exe, py_executable))
        else:
            logger.notify('Also creating executable in %s' % secondary_exe)
            shutil.copyfile(sys.executable, secondary_exe)
            make_exe(secondary_exe)

    if '.framework' in prefix:
        if 'Python.framework' in prefix:
            logger.debug('MacOSX Python framework detected')
            # Make sure we use the the embedded interpreter inside
            # the framework, even if sys.executable points to
            # the stub executable in ${sys.prefix}/bin
            # See http://groups.google.com/group/python-virtualenv/
            #                              browse_thread/thread/17cab2f85da75951
            original_python = os.path.join(
                prefix, 'Resources/Python.app/Contents/MacOS/Python')
        if 'EPD' in prefix:
            logger.debug('EPD framework detected')
            original_python = os.path.join(prefix, 'bin/python')
        shutil.copy(original_python, py_executable)

        # Copy the framework's dylib into the virtual
        # environment
        virtual_lib = os.path.join(home_dir, '.Python')

        if os.path.exists(virtual_lib):
            os.unlink(virtual_lib)
        copyfile(
            os.path.join(prefix, 'Python'),
            virtual_lib)

        # And then change the install_name of the copied python executable
        try:
            mach_o_change(py_executable,
                          os.path.join(prefix, 'Python'),
                          '@executable_path/../.Python')
        except:
            e = sys.exc_info()[1]
            logger.warn("Could not call mach_o_change: %s. "
                        "Trying to call install_name_tool instead." % e)
            try:
                call_subprocess(
                    ["install_name_tool", "-change",
                     os.path.join(prefix, 'Python'),
                     '@executable_path/../.Python',
                     py_executable])
            except:
                logger.fatal("Could not call install_name_tool -- you must "
                             "have Apple's development tools installed")
                raise

    if not is_win:
        # Ensure that 'python', 'pythonX' and 'pythonX.Y' all exist
        py_exe_version_major = 'python%s' % sys.version_info[0]
        py_exe_version_major_minor = 'python%s.%s' % (
            sys.version_info[0], sys.version_info[1])
        py_exe_no_version = 'python'
        required_symlinks = [ py_exe_no_version, py_exe_version_major,
                         py_exe_version_major_minor ]

        py_executable_base = os.path.basename(py_executable)

        if py_executable_base in required_symlinks:
            # Don't try to symlink to yourself.
            required_symlinks.remove(py_executable_base)

        for pth in required_symlinks:
            full_pth = join(bin_dir, pth)
            if os.path.exists(full_pth):
                os.unlink(full_pth)
            os.symlink(py_executable_base, full_pth)

    if is_win and ' ' in py_executable:
        # There's a bug with subprocess on Windows when using a first
        # argument that has a space in it.  Instead we have to quote
        # the value:
        py_executable = '"%s"' % py_executable
    # NOTE: keep this check as one line, cmd.exe doesn't cope with line breaks
    cmd = [py_executable, '-c', 'import sys;out=sys.stdout;'
        'getattr(out, "buffer", out).write(sys.prefix.encode("utf-8"))']
    logger.info('Testing executable with %s %s "%s"' % tuple(cmd))
    try:
        proc = subprocess.Popen(cmd,
                            stdout=subprocess.PIPE)
        proc_stdout, proc_stderr = proc.communicate()
    except OSError:
        e = sys.exc_info()[1]
        if e.errno == errno.EACCES:
            logger.fatal('ERROR: The executable %s could not be run: %s' % (py_executable, e))
            sys.exit(100)
        else:
            raise e

    proc_stdout = proc_stdout.strip().decode("utf-8")
    proc_stdout = os.path.normcase(os.path.abspath(proc_stdout))
    norm_home_dir = os.path.normcase(os.path.abspath(home_dir))
    if hasattr(norm_home_dir, 'decode'):
        norm_home_dir = norm_home_dir.decode(sys.getfilesystemencoding())
    if proc_stdout != norm_home_dir:
        logger.fatal(
            'ERROR: The executable %s is not functioning' % py_executable)
        logger.fatal(
            'ERROR: It thinks sys.prefix is %r (should be %r)'
            % (proc_stdout, norm_home_dir))
        logger.fatal(
            'ERROR: virtualenv is not compatible with this system or executable')
        if is_win:
            logger.fatal(
                'Note: some Windows users have reported this error when they '
                'installed Python for "Only this user" or have multiple '
                'versions of Python installed. Copying the appropriate '
                'PythonXX.dll to the virtualenv Scripts/ directory may fix '
                'this problem.')
        sys.exit(100)
    else:
        logger.info('Got sys.prefix result: %r' % proc_stdout)

    pydistutils = os.path.expanduser('~/.pydistutils.cfg')
    if os.path.exists(pydistutils):
        logger.notify('Please make sure you remove any previous custom paths from '
                      'your %s file.' % pydistutils)
    ## FIXME: really this should be calculated earlier

    fix_local_scheme(home_dir)

    if site_packages:
        if os.path.exists(site_packages_filename):
            logger.info('Deleting %s' % site_packages_filename)
            os.unlink(site_packages_filename)

    return py_executable


def install_activate(home_dir, bin_dir, prompt=None):
    home_dir = os.path.abspath(home_dir)
    if is_win or is_jython and os._name == 'nt':
        files = {
            'activate.bat': ACTIVATE_BAT,
            'deactivate.bat': DEACTIVATE_BAT,
            'activate.ps1': ACTIVATE_PS,
        }

        # MSYS needs paths of the form /c/path/to/file
        drive, tail = os.path.splitdrive(home_dir.replace(os.sep, '/'))
        home_dir_msys = (drive and "/%s%s" or "%s%s") % (drive[:1], tail)

        # Run-time conditional enables (basic) Cygwin compatibility
        home_dir_sh = ("""$(if [ "$OSTYPE" "==" "cygwin" ]; then cygpath -u '%s'; else echo '%s'; fi;)""" %
                       (home_dir, home_dir_msys))
        files['activate'] = ACTIVATE_SH.replace('__VIRTUAL_ENV__', home_dir_sh)

    else:
        files = {'activate': ACTIVATE_SH}

        # suppling activate.fish in addition to, not instead of, the
        # bash script support.
        files['activate.fish'] = ACTIVATE_FISH

        # same for csh/tcsh support...
        files['activate.csh'] = ACTIVATE_CSH

    files['activate_this.py'] = ACTIVATE_THIS
    if hasattr(home_dir, 'decode'):
        home_dir = home_dir.decode(sys.getfilesystemencoding())
    vname = os.path.basename(home_dir)
    for name, content in files.items():
        content = content.replace('__VIRTUAL_PROMPT__', prompt or '')
        content = content.replace('__VIRTUAL_WINPROMPT__', prompt or '(%s)' % vname)
        content = content.replace('__VIRTUAL_ENV__', home_dir)
        content = content.replace('__VIRTUAL_NAME__', vname)
        content = content.replace('__BIN_NAME__', os.path.basename(bin_dir))
        writefile(os.path.join(bin_dir, name), content)

def install_distutils(home_dir):
    distutils_path = change_prefix(distutils.__path__[0], home_dir)
    mkdir(distutils_path)
    ## FIXME: maybe this prefix setting should only be put in place if
    ## there's a local distutils.cfg with a prefix setting?
    home_dir = os.path.abspath(home_dir)
    ## FIXME: this is breaking things, removing for now:
    #distutils_cfg = DISTUTILS_CFG + "\n[install]\nprefix=%s\n" % home_dir
    writefile(os.path.join(distutils_path, '__init__.py'), DISTUTILS_INIT)
    writefile(os.path.join(distutils_path, 'distutils.cfg'), DISTUTILS_CFG, overwrite=False)

def fix_local_scheme(home_dir):
    """
    Platforms that use the "posix_local" install scheme (like Ubuntu with
    Python 2.7) need to be given an additional "local" location, sigh.
    """
    try:
        import sysconfig
    except ImportError:
        pass
    else:
        if sysconfig._get_default_scheme() == 'posix_local':
            local_path = os.path.join(home_dir, 'local')
            if not os.path.exists(local_path):
                os.mkdir(local_path)
                for subdir_name in os.listdir(home_dir):
                    if subdir_name == 'local':
                        continue
                    os.symlink(os.path.abspath(os.path.join(home_dir, subdir_name)), \
                                                            os.path.join(local_path, subdir_name))

def fix_lib64(lib_dir):
    """
    Some platforms (particularly Gentoo on x64) put things in lib64/pythonX.Y
    instead of lib/pythonX.Y.  If this is such a platform we'll just create a
    symlink so lib64 points to lib
    """
    if [p for p in distutils.sysconfig.get_config_vars().values()
        if isinstance(p, basestring) and 'lib64' in p]:
        logger.debug('This system uses lib64; symlinking lib64 to lib')
        assert os.path.basename(lib_dir) == 'python%s' % sys.version[:3], (
            "Unexpected python lib dir: %r" % lib_dir)
        lib_parent = os.path.dirname(lib_dir)
        top_level = os.path.dirname(lib_parent)
        lib_dir = os.path.join(top_level, 'lib')
        lib64_link = os.path.join(top_level, 'lib64')
        assert os.path.basename(lib_parent) == 'lib', (
            "Unexpected parent dir: %r" % lib_parent)
        if os.path.lexists(lib64_link):
            return
        os.symlink('lib', lib64_link)

def resolve_interpreter(exe):
    """
    If the executable given isn't an absolute path, search $PATH for the interpreter
    """
    if os.path.abspath(exe) != exe:
        paths = os.environ.get('PATH', '').split(os.pathsep)
        for path in paths:
            if os.path.exists(os.path.join(path, exe)):
                exe = os.path.join(path, exe)
                break
    if not os.path.exists(exe):
        logger.fatal('The executable %s (from --python=%s) does not exist' % (exe, exe))
        raise SystemExit(3)
    if not is_executable(exe):
        logger.fatal('The executable %s (from --python=%s) is not executable' % (exe, exe))
        raise SystemExit(3)
    return exe

def is_executable(exe):
    """Checks a file is executable"""
    return os.access(exe, os.X_OK)

############################################################
## Relocating the environment:

def make_environment_relocatable(home_dir):
    """
    Makes the already-existing environment use relative paths, and takes out
    the #!-based environment selection in scripts.
    """
    home_dir, lib_dir, inc_dir, bin_dir = path_locations(home_dir)
    activate_this = os.path.join(bin_dir, 'activate_this.py')
    if not os.path.exists(activate_this):
        logger.fatal(
            'The environment doesn\'t have a file %s -- please re-run virtualenv '
            'on this environment to update it' % activate_this)
    fixup_scripts(home_dir)
    fixup_pth_and_egg_link(home_dir)
    ## FIXME: need to fix up distutils.cfg

OK_ABS_SCRIPTS = ['python', 'python%s' % sys.version[:3],
                  'activate', 'activate.bat', 'activate_this.py']

def fixup_scripts(home_dir):
    # This is what we expect at the top of scripts:
    shebang = '#!%s/bin/python' % os.path.normcase(os.path.abspath(home_dir))
    # This is what we'll put:
    new_shebang = '#!/usr/bin/env python%s' % sys.version[:3]
    if is_win:
        bin_suffix = 'Scripts'
    else:
        bin_suffix = 'bin'
    bin_dir = os.path.join(home_dir, bin_suffix)
    home_dir, lib_dir, inc_dir, bin_dir = path_locations(home_dir)
    for filename in os.listdir(bin_dir):
        filename = os.path.join(bin_dir, filename)
        if not os.path.isfile(filename):
            # ignore subdirs, e.g. .svn ones.
            continue
        f = open(filename, 'rb')
        try:
            try:
                lines = f.read().decode('utf-8').splitlines()
            except UnicodeDecodeError:
                # This is probably a binary program instead
                # of a script, so just ignore it.
                continue
        finally:
            f.close()
        if not lines:
            logger.warn('Script %s is an empty file' % filename)
            continue
        if not lines[0].strip().startswith(shebang):
            if os.path.basename(filename) in OK_ABS_SCRIPTS:
                logger.debug('Cannot make script %s relative' % filename)
            elif lines[0].strip() == new_shebang:
                logger.info('Script %s has already been made relative' % filename)
            else:
                logger.warn('Script %s cannot be made relative (it\'s not a normal script that starts with %s)'
                            % (filename, shebang))
            continue
        logger.notify('Making script %s relative' % filename)
        script = relative_script([new_shebang] + lines[1:])
        f = open(filename, 'wb')
        f.write('\n'.join(script).encode('utf-8'))
        f.close()

def relative_script(lines):
    "Return a script that'll work in a relocatable environment."
    activate = "import os; activate_this=os.path.join(os.path.dirname(os.path.realpath(__file__)), 'activate_this.py'); execfile(activate_this, dict(__file__=activate_this)); del os, activate_this"
    # Find the last future statement in the script. If we insert the activation
    # line before a future statement, Python will raise a SyntaxError.
    activate_at = None
    for idx, line in reversed(list(enumerate(lines))):
        if line.split()[:3] == ['from', '__future__', 'import']:
            activate_at = idx + 1
            break
    if activate_at is None:
        # Activate after the shebang.
        activate_at = 1
    return lines[:activate_at] + ['', activate, ''] + lines[activate_at:]

def fixup_pth_and_egg_link(home_dir, sys_path=None):
    """Makes .pth and .egg-link files use relative paths"""
    home_dir = os.path.normcase(os.path.abspath(home_dir))
    if sys_path is None:
        sys_path = sys.path
    for path in sys_path:
        if not path:
            path = '.'
        if not os.path.isdir(path):
            continue
        path = os.path.normcase(os.path.abspath(path))
        if not path.startswith(home_dir):
            logger.debug('Skipping system (non-environment) directory %s' % path)
            continue
        for filename in os.listdir(path):
            filename = os.path.join(path, filename)
            if filename.endswith('.pth'):
                if not os.access(filename, os.W_OK):
                    logger.warn('Cannot write .pth file %s, skipping' % filename)
                else:
                    fixup_pth_file(filename)
            if filename.endswith('.egg-link'):
                if not os.access(filename, os.W_OK):
                    logger.warn('Cannot write .egg-link file %s, skipping' % filename)
                else:
                    fixup_egg_link(filename)

def fixup_pth_file(filename):
    lines = []
    prev_lines = []
    f = open(filename)
    prev_lines = f.readlines()
    f.close()
    for line in prev_lines:
        line = line.strip()
        if (not line or line.startswith('#') or line.startswith('import ')
            or os.path.abspath(line) != line):
            lines.append(line)
        else:
            new_value = make_relative_path(filename, line)
            if line != new_value:
                logger.debug('Rewriting path %s as %s (in %s)' % (line, new_value, filename))
            lines.append(new_value)
    if lines == prev_lines:
        logger.info('No changes to .pth file %s' % filename)
        return
    logger.notify('Making paths in .pth file %s relative' % filename)
    f = open(filename, 'w')
    f.write('\n'.join(lines) + '\n')
    f.close()

def fixup_egg_link(filename):
    f = open(filename)
    link = f.readline().strip()
    f.close()
    if os.path.abspath(link) != link:
        logger.debug('Link in %s already relative' % filename)
        return
    new_link = make_relative_path(filename, link)
    logger.notify('Rewriting link %s in %s as %s' % (link, filename, new_link))
    f = open(filename, 'w')
    f.write(new_link)
    f.close()

def make_relative_path(source, dest, dest_is_directory=True):
    """
    Make a filename relative, where the filename is dest, and it is
    being referred to from the filename source.

        >>> make_relative_path('/usr/share/something/a-file.pth',
        ...                    '/usr/share/another-place/src/Directory')
        '../another-place/src/Directory'
        >>> make_relative_path('/usr/share/something/a-file.pth',
        ...                    '/home/user/src/Directory')
        '../../../home/user/src/Directory'
        >>> make_relative_path('/usr/share/a-file.pth', '/usr/share/')
        './'
    """
    source = os.path.dirname(source)
    if not dest_is_directory:
        dest_filename = os.path.basename(dest)
        dest = os.path.dirname(dest)
    dest = os.path.normpath(os.path.abspath(dest))
    source = os.path.normpath(os.path.abspath(source))
    dest_parts = dest.strip(os.path.sep).split(os.path.sep)
    source_parts = source.strip(os.path.sep).split(os.path.sep)
    while dest_parts and source_parts and dest_parts[0] == source_parts[0]:
        dest_parts.pop(0)
        source_parts.pop(0)
    full_parts = ['..']*len(source_parts) + dest_parts
    if not dest_is_directory:
        full_parts.append(dest_filename)
    if not full_parts:
        # Special case for the current directory (otherwise it'd be '')
        return './'
    return os.path.sep.join(full_parts)



############################################################
## Bootstrap script creation:

def create_bootstrap_script(extra_text, python_version=''):
    """
    Creates a bootstrap script, which is like this script but with
    extend_parser, adjust_options, and after_install hooks.

    This returns a string that (written to disk of course) can be used
    as a bootstrap script with your own customizations.  The script
    will be the standard virtualenv.py script, with your extra text
    added (your extra text should be Python code).

    If you include these functions, they will be called:

    ``extend_parser(optparse_parser)``:
        You can add or remove options from the parser here.

    ``adjust_options(options, args)``:
        You can change options here, or change the args (if you accept
        different kinds of arguments, be sure you modify ``args`` so it is
        only ``[DEST_DIR]``).

    ``after_install(options, home_dir)``:

        After everything is installed, this function is called.  This
        is probably the function you are most likely to use.  An
        example would be::

            def after_install(options, home_dir):
                subprocess.call([join(home_dir, 'bin', 'easy_install'),
                                 'MyPackage'])
                subprocess.call([join(home_dir, 'bin', 'my-package-script'),
                                 'setup', home_dir])

        This example immediately installs a package, and runs a setup
        script from that package.

    If you provide something like ``python_version='2.5'`` then the
    script will start with ``#!/usr/bin/env python2.5`` instead of
    ``#!/usr/bin/env python``.  You can use this when the script must
    be run with a particular Python version.
    """
    filename = __file__
    if filename.endswith('.pyc'):
        filename = filename[:-1]
    f = codecs.open(filename, 'r', encoding='utf-8')
    content = f.read()
    f.close()
    py_exe = 'python%s' % python_version
    content = (('#!/usr/bin/env %s\n' % py_exe)
               + '## WARNING: This file is generated\n'
               + content)
    return content.replace('##EXT' 'END##', extra_text)

##EXTEND##

def convert(s):
    b = base64.b64decode(s.encode('ascii'))
    return zlib.decompress(b).decode('utf-8')

##file site.py
SITE_PY = convert("""
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
UM3ckC/Q8aP8VLy+mjYY5MxOtAdgjULwf2RtvCc=
""")

##file ez_setup.py
EZ_SETUP_PY = convert("""
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
qL7+C1AkCcw=
""")

##file distribute_from_egg.py
DISTRIBUTE_FROM_EGG_PY = convert("""
eJw9j8tqAzEMRfcG/4MgmxQyptkGusonZBmGoGTUGYFfWPKE6dfXTkM3gqt7rh47OKP3NMF3SQFW
LlrRU1zhybpAxoKBlIqcrNnBdRjQP3GTocYfzmNrrCPQPN9iwzpxSQfQhWBi0cL3qtRtYIG/4Mv0
KApY5hooqrOGQ05FQTaxptF9Fnx16Rq0XofjaE1XGXVxHIWK7j8P8EY/rHndLqQ1a0pe3COFgHFy
hLLdWkDbi/DeEpCjNb3u/zccT2Ob8gtnwVyI
""")

##file distribute_setup.py
DISTRIBUTE_SETUP_PY = convert("""
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
""")

##file activate.sh
ACTIVATE_SH = convert("""
eJytVVFvokAQfudXTLEPtTlLeo9tvMSmJpq02hSvl7u2wRUG2QR2DSxSe7n/frOACEVNLlceRHa+
nfl25pvZDswCnoDPQ4QoTRQsENIEPci4CsBMZBq7CAsuLOYqvmYKTTj3YxnBgiXBudGBjUzBZUJI
BXEqgCvweIyuCjeG4eF2F5x14bcB9KQiQQWrjSddI1/oQIx6SYYeoFjzWIoIhYI1izlbhJjkKO7D
M/QEmKfO9O7WeRo/zr4P7pyHwWxkwitcgwpQ5Ej96OX+PmiFwLeVjFUOrNYKaq1Nud3nR2n8nI2m
k9H0friPTGVsUdptaxGrTEfpNVFEskxpXtUkkCkl1UNF9cgLBkx48J4EXyALuBtAwNYIjF5kcmUU
abMKmMq1ULoiRbgsDEkTSsKSGFCJ6Z8vY/2xYiSacmtyAfCDdCNTVZoVF8vSTQOoEwSnOrngBkws
MYGMBMg8/bMBLSYKS7pYEXP0PqT+ZmBT0Xuy+Pplj5yn4aM9nk72JD8/Wi+Gr98sD9eWSMOwkapD
BbUv91XSvmyVkICt2tmXR4tWmrcUCsjWOpw87YidEC8i0gdTSOFhouJUNxR+4NYBG0MftoCTD9F7
2rTtxG3oPwY1b2HncYwhrlmj6Wq924xtGDWqfdNxap+OYxplEurnMVo9RWks+rH8qKEtx7kZT5zJ
4H7oOFclrN6uFe+d+nW2aIUsSgs/42EIPuOhXq+jEo3S6tX6w2ilNkDnIpHCWdEQhFgwj9pkk7FN
l/y5eQvRSIQ5+TrL05lewxWpt/Lbhes5cJF3mLET1MGhcKCF+40tNWnUulxrpojwDo2sObdje3Bz
N3QeHqf3D7OjEXMVV8LN3ZlvuzoWHqiUcNKHtwNd0IbvPGKYYM31nPKCgkUILw3KL+Y8l7aO1ArS
Ad37nIU0fCj5NE5gQCuC5sOSu+UdI2NeXg/lFkQIlFpdWVaWZRfvqGiirC9o6liJ9FXGYrSY9mI1
D/Ncozgn13vJvsznr7DnkJWXsyMH7e42ljdJ+aqNDF1bFnKWFLdj31xtaJYK6EXFgqmV/ymD/ROG
+n8O9H8f5vsGOWXsL1+1k3g=
""")

##file activate.fish
ACTIVATE_FISH = convert("""
eJyVVWFv2jAQ/c6vuBoqQVWC9nVSNVGVCaS2VC2rNLWVZZILWAs2s52wVvvxsyEJDrjbmgpK7PP5
3bt3d22YLbmGlGcIq1wbmCPkGhPYcLMEEsGciwGLDS+YwSjlekngLFVyBe73GXSXxqw/DwbuTS8x
yyKpFr1WG15lDjETQhpQuQBuIOEKY5O9tlppLqxHKSDByjVAPwEy+mXtCq5MzjIUBTCRgEKTKwFG
gpBqxTLYXgN2myspVigMaYF92tZSowGZJf4mFExxNs9Qb614CgZtmH0BpEOn11f0cXI/+za8pnfD
2ZjA1sg9zlV/8QvcMhxbNu0QwgYokn/d+n02nt6Opzcjcnx1vXcIoN74O4ymWQXmHURfJw9jenc/
vbmb0enj6P5+cuVhqlKm3S0u2XRtRbA2QQAhV7VhBF0rsgUX9Ur1rBUXJgVSy8O751k8mzY5OrKH
RW3eaQhYGTr8hrXO59ALhxQ83mCsDLAid3T72CCSdJhaFE+fXgicXAARUiR2WeVO37gH3oYHzFKo
9k7CaPZ1UeNwH1tWuXA4uFKYYcEa8vaKqXl7q1UpygMPhFLvlVKyNzsSM3S2km7UBOl4xweUXk5u
6e3wZmQ9leY1XE/Ili670tr9g/5POBBpGIJXCCF79L1siarl/dbESa8mD8PL61GpzqpzuMS7tqeB
1YkALrRBloBMbR9yLcVx7frQAgUqR7NZIuzkEu110gbNit1enNs82Rx5utq7Z3prU78HFRgulqNC
OTwbqJa9vkJFclQgZSjbKeBgSsUtCtt9D8OwAbIVJuewQdfvQRaoFE9wd1TmCuRG7OgJ1bVXGHc7
z5WDL/WW36v2oi37CyVBak61+yPBA9C1qqGxzKQqZ0oPuocU9hpud0PIp8sDHkXR1HKkNlzjuUWA
a0enFUyzOWZA4yXGP+ZMI3Tdt2OuqU/SO4q64526cPE0A7ZyW2PMbWZiZ5HamIZ2RcCKLXhcDl2b
vXL+eccQoRzem80mekPDEiyiWK4GWqZmwxQOmPM0eIfgp1P9cqrBsewR2p/DPMtt+pfcYM+Ls2uh
hALufTAdmGl8B1H3VPd2af8fQAc4PgqjlIBL9cGQqNpXaAwe3LrtVn8AkZTUxg==
""")

##file activate.csh
ACTIVATE_CSH = convert("""
eJx9VG1P2zAQ/u5fcYQKNgTNPtN1WxlIQ4KCUEGaxuQ6yYVYSuzKdhqVX7+zk3bpy5YPUXL3PPfc
ne98DLNCWshliVDV1kGCUFvMoJGugMjq2qQIiVSxSJ1cCofD1BYRnOVGV0CfZ0N2DD91DalQSjsw
tQLpIJMGU1euvPe7QeJlkKzgWixlhnAt4aoUVsLnLBiy5NtbJWQ5THX1ZciYKKWwkOFaE04dUm6D
r/zh7pq/3D7Nnid3/HEy+wFHY/gEJydg0aFaQrBFgz1c5DG1IhTs+UZgsBC2GMFBlaeH+8dZXwcW
VPvCjXdlAvCfQsE7al0+07XjZvrSCUevR5dnkVeKlFYZmUztG4BdzL2u9KyLVabTU0bdfg7a0hgs
cSmUg6UwUiQl2iHrcbcVGNvPCiLOe7+cRwG13z9qRGgx2z6DHjfm/Op2yqeT+xvOLzs0PTKHDz2V
tkckFHoQfQRXoGJAj9el0FyJCmEMhzgMS4sB7KPOE2ExoLcSieYwDvR+cP8cg11gKkVJc2wRcm1g
QhYFlXiTaTfO2ki0fQoiFM4tLuO4aZrhOzqR4dIPcWx17hphMBY+Srwh7RTyN83XOWkcSPh1Pg/k
TXX/jbJTbMtUmcxZ+/bbqOsy82suFQg/BhdSOTRhMNBHlUarCpU7JzBhmkKmRejKOQzayQe6MWoa
n1wqWmuh6LZAaHxcdeqIlVLhIBJdO9/kbl0It2oEXQj+eGjJOuvOIR/YGRqvFhttUB2XTvLXYN2H
37CBdbW2W7j2r2+VsCn0doVWcFG1/4y1VwBjfwAyoZhD
""")

##file activate.bat
ACTIVATE_BAT = convert("""
eJx9UdEKgjAUfW6wfxjiIH+hEDKUFHSKLCMI7kNOEkIf9P9pTJ3OLJ/03HPPPed4Es9XS9qqwqgT
PbGKKOdXL4aAFS7A4gvAwgijuiKlqOpGlATS2NeMLE+TjJM9RkQ+SmqAXLrBo1LLIeLdiWlD6jZt
r7VNubWkndkXaxg5GO3UaOOKS6drO3luDDiO5my3iA0YAKGzPRV1ack8cOdhysI0CYzIPzjSiH5X
0QcvC8Lfaj0emsVKYF2rhL5L3fCkVjV76kShi59NHwDniAHzkgDgqBcwOgTMx+gDQQqXCw==
""")

##file deactivate.bat
DEACTIVATE_BAT = convert("""
eJxzSE3OyFfIT0vj4ipOLVEI8wwKCXX0iXf1C7Pl4spMU0hJTcvMS01RiPf3cYmHyQYE+fsGhCho
cCkAAUibEkTEVhWLMlUlLk6QGixStlyaeCyJDPHw9/Pw93VFsQguim4ZXAJoIUw5DhX47XUM8UCx
EchHtwsohN1bILUgw61c/Vy4AJYPYm4=
""")

##file activate.ps1
ACTIVATE_PS = convert("""
eJylWdmS40Z2fVeE/oHT6rCloNUEAXDThB6wAyQAEjsB29GBjdgXYiWgmC/zgz/Jv+AEWNVd3S2N
xuOKYEUxM+/Jmzfvcm7W//zXf/+wUMOoXtyi1F9kbd0sHH/hFc2iLtrK9b3FrSqyxaVQwr8uhqJd
uHaeg9mqzRdR8/13Pyy8qPLdJh0+LMhi0QCoXxYfFh9WtttEnd34H8p6/f1300KauwrULws39e18
0ZaLNm9rgN/ZVf3h++/e124Vlc0vKsspHy+Yyi5+XbzPhijvCtduoiL/kA1ukWV27n0o7Sb8LIFj
CvWR5GQgUJdp1Pw8TS9+rPy6SDv/+e3d+0+4qw8f3v20+PliV37efEYBAB9FTKC+RHn/Cfxn3rdv
00Fube5O+iyCtHDs9BfPfz3q4sfFv9d91Ljhfy7ei0VO+nVTtdOkv/jpt0l2AX6iG1jXgKnnDuD4
ke2k/i8fzzz5UedkVcP4pwF+Wvz2FJl+3vt598urXf5Y6LNA5WcFOP7r0sW7b9a+W/xcu0Xpv5zk
Kfq3P9Dz9di/fCxS72MXVU1rpx9L4Bxl85Wmn5a+zP76Zuh3pL9ROWr87PN+//GHIl+oOtvn9XSU
qH+p0gQBFnx1uV+JLH5O5zv+PXW+WepXVVHZT0+oQezkIATcIm+ivPV/z5J/+cYj3ir4w0Lx09vC
e5n/y5/Y5LPPfdrqb88ga/PabxZRVfmp39l588m/6u+/e+OpP+dF7n1WZpJ9//Z4v372fDDz9eHB
7Juvs/BLMHzrxL9+9twXpJfhd1/DrpQ5Euu/vlss3wp9HXC/54C/Ld69m6zwdx3tC0d8daSv0V8B
n4b9YYF53sJelJV/ix6LZspw/sJtqyl5LJ5r/23htA1Imfm/gt9R7dqVB1LjhydAX4Gb+zksQF59
9+P7H//U+376afFuvh2/T6P85Xr/5c8C6OXyFY4BGuN+EE0+GeR201b+wkkLN5mmBY5TfMw8ngqL
CztXxCSXKMCYrRIElWkEJlEPYsSOeKBVZCAQTKBhApMwRFQzmCThE0YQu2CdEhgjbgmk9GluHpfR
/hhwJCZhGI5jt5FsAkOrObVyE6g2y1snyhMGFlDY1x+BoHpCMulTj5JYWNAYJmnKpvLxXgmQ8az1
4fUGxxcitMbbhDFcsiAItg04E+OSBIHTUYD1HI4FHH4kMREPknuYRMyhh3AARWMkfhCketqD1CWJ
mTCo/nhUScoQcInB1hpFhIKoIXLo5jLpwFCgsnLCx1QlEMlz/iFEGqzH3vWYcpRcThgWnEKm0QcS
rA8ek2a2IYYeowUanOZOlrbWSJUC4c7y2EMI3uJPMnMF/SSXdk6E495VLhzkWHps0rOhKwqk+xBI
DhJirhdUCTamMfXz2Hy303hM4DFJ8QL21BcPBULR+gcdYxoeiDqOFSqpi5B5PUISfGg46gFZBPo4
jdh8lueaWuVSMTURfbAUnLINr/QYuuYoMQV6l1aWxuZVTjlaLC14UzqZ+ziTGDzJzhiYoPLrt3uI
tXkVR47kAo09lo5BD76CH51cTt1snVpMOttLhY93yxChCQPI4OBecS7++h4p4Bdn4H97bJongtPk
s9gQnXku1vzsjjmX4/o4YUDkXkjHwDg5FXozU0fW4y5kyeYW0uJWlh536BKr0kMGjtzTkng6Ep62
uTWnQtiIqKnEsx7e1hLtzlXs7Upw9TwEnp0t9yzCGgUJIZConx9OHJArLkRYW0dW42G9OeR5Nzwk
yk1mX7du5RGHT7dka7N3AznmSif7y6tuKe2N1Al/1TUPRqH6E2GLVc27h9IptMLkCKQYRqPQJgzV
2m6WLsSipS3v3b1/WmXEYY1meLEVIU/arOGVkyie7ZsH05ZKpjFW4cpY0YkjySpSExNG2TS8nnJx
nrQmWh2WY3cP1eISP9wbaVK35ZXc60yC3VN/j9n7UFoK6zvjSTE2+Pvz6Mx322rnftfP8Y0XKIdv
Qd7AfK0nexBTMqRiErvCMa3Hegpfjdh58glW2oNMsKeAX8x6YJLZs9K8/ozjJkWL+JmECMvhQ54x
9rsTHwcoGrDi6Y4I+H7yY4/rJVPAbYymUH7C2D3uiUS3KQ1nrCAUkE1dJMneDQIJMQQx5SONxoEO
OEn1/Ig1eBBUeEDRuOT2WGGGE4bNypBLFh2PeIg3bEbg44PHiqNDbGIQm50LW6MJU62JHCGBrmc9
2F7WBJrrj1ssnTAK4sxwRgh5LLblhwNAclv3Gd+jC/etCfyfR8TMhcWQz8TBIbG8IIyAQ81w2n/C
mHWAwRzxd3WoBY7BZnsqGOWrOCKwGkMMNfO0Kci/joZgEocLjNnzgcmdehPHJY0FudXgsr+v44TB
I3jnMGnsK5veAhgi9iXGifkHMOC09Rh9cAw9sQ0asl6wKMk8mpzFYaaDSgG4F0wisQDDBRpjCINg
FIxhlhQ31xdSkkk6odXZFpTYOQpOOgw9ugM2cDQ+2MYa7JsEirGBrOuxsQy5nPMRdYjsTJ/j1iNw
FeSt1jY2+dd5yx1/pzZMOQXUIDcXeAzR7QlDRM8AMkUldXOmGmvYXPABjxqkYKO7VAY6JRU7kpXr
+Epu2BU3qFFXClFi27784LrDZsJwbNlDw0JzhZ6M0SMXE4iBHehCpHVkrQhpTFn2dsvsZYkiPEEB
GSEAwdiur9LS1U6P2U9JhGp4hnFpJo4FfkdJHcwV6Q5dV1Q9uNeeu7rV8PAjwdFg9RLtroifOr0k
uOiRTo/obNPhQIf42Fr4mtThWoSjitEdAmFW66UCe8WFjPk1YVNpL9srFbond7jrLg8tqAasIMpy
zkH0SY/6zVAwJrEc14zt14YRXdY+fcJ4qOd2XKB0/Kghw1ovd11t2o+zjt+txndo1ZDZ2T+uMVHT
VSXhedBAHoJIID9xm6wPQI3cXY+HR7vxtrJuCKh6kbXaW5KkVeJsdsjqsYsOwYSh0w5sMbu7LF8J
5T7U6LJdiTx+ca7RKlulGgS5Z1JSU2Llt32cHFipkaurtBrvNX5UtvNZjkufZ/r1/XyLl6yOpytL
Km8Fn+y4wkhlqZP5db0rooqy7xdL4wxzFVTX+6HaxuQJK5E5B1neSSovZ9ALB8091dDbbjVxhWNY
Ve5hn1VnI9OF0wpvaRm7SZuC1IRczwC7GnkhPt3muHV1YxUJfo+uh1sYnJy+vI0ZwuPV2uqWJYUH
bmBsi1zmFSxHrqwA+WIzLrHkwW4r+bad7xbOzJCnKIa3S3YvrzEBK1Dc0emzJW+SqysQfdEDorQG
9ZJlbQzEHQV8naPaF440YXzJk/7vHGK2xwuP+Gc5xITxyiP+WQ4x18oXHjFzCBy9kir1EFTAm0Zq
LYwS8MpiGhtfxiBRDXpxDWxk9g9Q2fzPPAhS6VFDAc/aiNGatUkPtZIStZFQ1qD0IlJa/5ZPAi5J
ySp1ETDomZMnvgiysZSBfMikrSDte/K5lqV6iwC5q7YN9I1dBZXUytDJNqU74MJsUyNNLAPopWK3
tzmLkCiDyl7WQnj9sm7Kd5kzgpoccdNeMw/6zPVB3pUwMgi4C7hj4AMFAf4G27oXH8NNT9zll/sK
S6wVlQwazjxWKWy20ZzXb9ne8ngGalPBWSUSj9xkc1drsXkZ8oOyvYT3e0rnYsGwx85xZB9wKeKg
cJKZnamYwiaMymZvzk6wtDUkxmdUg0mPad0YHtvzpjEfp2iMxvORhnx0kCVLf5Qa43WJsVoyfEyI
pzmf8ruM6xBr7dnBgzyxpqXuUPYaKahOaz1LrxNkS/Q3Ae5AC+xl6NbxAqXXlzghZBZHmOrM6Y6Y
ctAkltwlF7SKEsShjVh7QHuxMU0a08/eiu3x3M+07OijMcKFFltByXrpk8w+JNnZpnp3CfgjV1Ax
gUYCnWwYow42I5wHCcTzLXK0hMZN2DrPM/zCSqe9jRSlJnr70BPE4+zrwbk/xVIDHy2FAQyHoomT
Tt5jiM68nBQut35Y0qLclLiQrutxt/c0OlSqXAC8VrxW97lGoRWzhOnifE2zbF05W4xuyhg7JTUL
aqJ7SWDywhjlal0b+NLTpERBgnPW0+Nw99X2Ws72gOL27iER9jgzj7Uu09JaZ3n+hmCjjvZpjNst
vOWWTbuLrg+/1ltX8WpPauEDEvcunIgTxuMEHweWKCx2KQ9DU/UKdO/3za4Szm2iHYL+ss9AAttm
gZHq2pkUXFbV+FiJCKrpBms18zH75vax5jSo7FNunrVWY3Chvd8KKnHdaTt/6ealwaA1x17yTlft
8VBle3nAE+7R0MScC3MJofNCCkA9PGKBgGMYEwfB2QO5j8zUqa8F/EkWKCzGQJ5EZ05HTly1B01E
z813G5BY++RZ2sxbQS8ZveGPJNabp5kXAeoign6Tlt5+L8i5ZquY9+S+KEUHkmYMRFBxRrHnbl2X
rVemKnG+oB1yd9+zT+4c43jQ0wWmQRR6mTCkY1q3VG05Y120ZzKOMBe6Vy7I5Vz4ygPB3yY4G0FP
8RxiMx985YJPXsgRU58EuHj75gygTzejP+W/zKGe78UQN3yOJ1aMQV9hFH+GAfLRsza84WlPLAI/
9G/5JdcHftEfH+Y3/fHUG7/o8bv98dzzy3e8S+XCvgqB+VUf7sH0yDHpONdbRE8tAg9NWOzcTJ7q
TuAxe/AJ07c1Rs9okJvl1/0G60qvbdDzz5zO0FuPFQIHNp9y9Bd1CufYVx7dB26mAxwa8GMNrN/U
oGbNZ3EQ7inLzHy5tRg9AXJrN8cB59cCUBeCiVO7zKM0jU0MamhnRThkg/NMmBOGb6StNeD9tDfA
7czsAWopDdnGoXUHtA+s/k0vNPkBcxEI13jVd/axp85va3LpwGggXXWw12Gwr/JGAH0b8CPboiZd
QO1l0mk/UHukud4C+w5uRoNzpCmoW6GbgbMyaQNkga2pQINB18lOXOCJzSWPFOhZcwzdgrsQnne7
nvjBi+7cP2BbtBeDOW5uOLGf3z94FasKIguOqJl+8ss/6Kumns4cuWbqq5592TN/RNIbn5Qo6qbi
O4F0P9txxPAwagqPlftztO8cWBzdN/jz3b7GD6JHYP/Zp4ToAMaA74M+EGSft3hEGMuf8EwjnTk/
nz/P7SLipB/ogQ6xNX0fDqNncMCfHqGLCMM0ZzFa+6lPJYQ5p81vW4HkCvidYf6kb+P/oB965g8K
C6uR0rdjX1DNKc5pOSTquI8uQ6KXxYaKBn+30/09tK4kMpJPgUIQkbENEPbuezNPPje2Um83SgyX
GTCJb6MnGVIpgncdQg1qz2bvPfxYD9fewCXDomx9S+HQJuX6W3VAL+v5WZMudRQZk9ZdOk6GIUtC
PqEb/uwSIrtR7/edzqgEdtpEwq7p2J5OQV+RLrmtTvFwFpf03M/VrRyTZ73qVod7v7Jh2Dwe5J25
JqFOU2qEu1sP+CRotklediycKfLjeIZzjJQsvKmiGSNQhxuJpKa+hoWUizaE1PuIRGzJqropwgVB
oo1hr870MZLgnXF5ZIpr6mF0L8aSy2gVnTAuoB4WEd4d5NPVC9TMotYXERKlTcwQ2KiB/C48AEfH
Qbyq4CN8xTFnTvf/ebOc3isnjD95s0QF0nx9s+y+zMmz782xL0SgEmRpA3x1w1Ff9/74xcxKEPdS
IEFTz6GgU0+BK/UZ5Gwbl4gZwycxEw+Kqa5QmMkh4OzgzEVPnDAiAOGBFaBW4wkDmj1G4RyElKgj
NlLCq8zsp085MNh/+R4t1Q8yxoSv8PUpTt7izZwf2BTHZZ3pIZpUIpuLkL1nNL6sYcHqcKm237wp
T2+RCjgXweXd2Zp7ZM8W6dG5bZsqo0nrJBTx8EC0+CQQdzEGnabTnkzofu1pYkWl4E7XSniECdxy
vLYavPMcL9LW5SToJFNnos+uqweOHriUZ1ntIYZUonc7ltEQ6oTRtwOHNwez2sVREskHN+bqG3ua
eaEbJ8XpyO8CeD9QJc8nbLP2C2R3A437ISUNyt5Yd0TbDNcl11/DSsOzdbi/VhCC0KE6v1vqVNkq
45ZnG6fiV2NwzInxCNth3BwL0+8814jE6+1W1EeWtpWbSZJOJNYXmWRXa7vLnAljE692eHjZ4y5u
y1u63De0IzKca7As48Z3XshVF+3XiLNz0JIMh/JOpbiNLlMi672uO0wYzOCZjRxcxj3D+gVenGIE
MvFUGGXuRps2RzMcgWIRolHXpGUP6sMsQt1hspUBnVKUn/WQj2u6j3SXd9Xz0QtEzoM7qTu5y7gR
q9gNNsrlEMLdikBt9bFvBnfbUIh6voTw7eDsyTmPKUvF0bHqWLbHe3VRHyRZnNeSGKsB73q66Vsk
taxWYmwz1tYVFG/vOQhlM0gUkyvIab3nv2caJ1udU1F3pDMty7stubTE4OJqm0i0ECfrJIkLtraC
HwRWKzlqpfhEIqYH09eT9WrOhQyt8YEoyBlnXtAT37WHIQ03TIuEHbnRxZDdLun0iok9PUC79prU
m5beZzfQUelEXnhzb/pIROKx3F7qCttYIFGh5dXNzFzID7u8vKykA8Uejf7XXz//S4nKvW//ofS/
QastYw==
""")

##file distutils-init.py
DISTUTILS_INIT = convert("""
eJytV1uL4zYUfvevOE0ottuMW9q3gVDa3aUMXXbLMlDKMBiNrSTqOJKRlMxkf33PkXyRbGe7Dw2E
UXTu37lpxLFV2oIyifAncxmOL0xLIfcG+gv80x9VW6maw7o/CANSWWBwFtqeWMPlGY6qPjV8A0bB
C4eKSTgZ5LRgFeyErMEeOBhbN+Ipgeizhjtnhkn7DdyjuNLPoCS0l/ayQTG0djwZC08cLXozeMss
aG5EzQ0IScpnWtHSTXuxByV/QCmxE7y+eS0uxWeoheaVVfqSJHiU7Mhhi6gULbOHorshkrEnKxpT
0n3A8Y8SMpuwZx6aoix3ouFlmW8gHRSkeSJ2g7hU+kiHLDaQw3bmRDaTGfTnty7gPm0FHbIBg9U9
oh1kZzAFLaue2R6htPCtAda2nGlDSUJ4PZBgCJBGVcwKTAMz/vJiLD+Oin5Z5QlvDPdulC6EsiyE
NFzb7McNTKJzbJqzphx92VKRFY1idenzmq3K0emRcbWBD0ryqc4NZGmKOOOX9Pz5x+/l27tP797c
f/z0d+4NruGNai8uAM0bfsYaw8itFk8ny41jsfpyO+BWlpqfhcG4yxLdi/0tQqoT4a8Vby382mt8
p7XSo7aWGdPBc+b6utaBmCQ7rQKQoWtAuthQCiold2KfJIPTT8xwg9blPumc+YDZC/wYGdAyHpJk
vUbHbHWAp5No6pK/WhhLEWrFjUwtPEv1Agf8YmnsuXUQYkeZoHm8ogP16gt2uHoxcEMdf2C6pmbw
hUMsWGhanboh4IzzmsIpWs134jVPqD/c74bZHdY69UKKSn/+KfVhxLgUlToemayLMYQOqfEC61bh
cbhwaqoGUzIyZRFHPmau5juaWqwRn3mpWmoEA5nhzS5gog/5jbcFQqOZvmBasZtwYlG93k5GEiyw
buHhMWLjDarEGpMGB2LFs5nIJkhp/nUmZneFaRth++lieJtHepIvKgx6PJqIlD9X2j6pG1i9x3pZ
5bHuCPFiirGHeO7McvoXkz786GaKVzC9DSpnOxJdc4xm6NSVq7lNEnKdVlnpu9BNYoKX2Iq3wvgh
gGEUM66kK6j4NiyoneuPLSwaCWDxczgaolEWpiMyDVDb7dNuLAbriL8ig8mmeju31oNvQdpnvEPC
1vAXbWacGRVrGt/uXN/gU0CDDwgooKRrHfTBb1/s9lYZ8ZqOBU0yLvpuP6+K9hLFsvIjeNhBi0KL
MlOuWRn3FRwx5oHXjl0YImUx0+gLzjGchrgzca026ETmYJzPD+IpuKzNi8AFn048Thd63OdD86M6
84zE8yQm0VqXdbbgvub2pKVnS76icBGdeTHHXTKspUmr4NYo/furFLKiMdQzFjHJNcdAnMhltBJK
0/IKX3DVFqvPJ2dLE7bDBkH0l/PJ29074+F0CsGYOxsb7U3myTUncYfXqnLLfa6sJybX4g+hmcjO
kMRBfA1JellfRRKJcyRpxdS4rIl6FdmQCWjo/o9Qz7yKffoP4JHjOvABcRn4CZIT2RH4jnxmfpVG
qgLaAvQBNfuO6X0/Ux02nb4FKx3vgP+XnkX0QW9pLy/NsXgdN24dD3LxO2Nwil7Zlc1dqtP3d7/h
kzp1/+7hGBuY4pk0XD/0Ao/oTe/XGrfyM773aB7iUhgkpy+dwAMalxMP0DrBcsVw/6p25+/hobP9
GBknrWExDhLJ1bwt1NcCNblaFbMKCyvmX0PeRaQ=
""")

##file distutils.cfg
DISTUTILS_CFG = convert("""
eJxNj00KwkAMhfc9xYNuxe4Ft57AjYiUtDO1wXSmNJnK3N5pdSEEAu8nH6lxHVlRhtDHMPATA4uH
xJ4EFmGbvfJiicSHFRzUSISMY6hq3GLCRLnIvSTnEefN0FIjw5tF0Hkk9Q5dRunBsVoyFi24aaLg
9FDOlL0FPGluf4QjcInLlxd6f6rqkgPu/5nHLg0cXCscXoozRrP51DRT3j9QNl99AP53T2Q=
""")

##file activate_this.py
ACTIVATE_THIS = convert("""
eJyNU01v2zAMvetXEB4K21jmDOstQA4dMGCHbeihlyEIDMWmG62yJEiKE//7kXKdpN2KzYBt8euR
fKSyLPs8wiEo8wh4wqZTGou4V6Hm0wJa1cSiTkJdr8+GsoTRHuCotBayiWqQEYGtMCgfD1KjGYBe
5a3p0cRKiAe2NtLADikftnDco0ko/SFEVgEZ8aRC5GLux7i3BpSJ6J1H+i7A2CjiHq9z7JRZuuQq
siwTIvpxJYCeuWaBpwZdhB+yxy/eWz+ZvVSU8C4E9FFZkyxFsvCT/ZzL8gcz9aXVE14Yyp2M+2W0
y7n5mp0qN+avKXvbsyyzUqjeWR8hjGE+2iCE1W1tQ82hsCZN9UzlJr+/e/iab8WfqsmPI6pWeUPd
FrMsd4H/55poeO9n54COhUs+sZNEzNtg/wanpjpuqHJaxs76HtZryI/K3H7KJ/KDIhqcbJ7kI4ar
XL+sMgXnX0D+Te2Iy5xdP8yueSlQB/x/ED2BTAtyE3K4SYUN6AMNfbO63f4lBW3bUJPbTL+mjSxS
PyRfJkZRgj+VbFv+EzHFi5pKwUEepa4JslMnwkowSRCXI+m5XvEOvtuBrxHdhLalG0JofYBok6qj
YdN2dEngUlbC4PG60M1WEN0piu7Nq7on0mgyyUw3iV1etLo6r/81biWdQ9MWHFaePWZYaq+nmp+t
s3az+sj7eA0jfgPfeoN1
""")

MH_MAGIC = 0xfeedface
MH_CIGAM = 0xcefaedfe
MH_MAGIC_64 = 0xfeedfacf
MH_CIGAM_64 = 0xcffaedfe
FAT_MAGIC = 0xcafebabe
BIG_ENDIAN = '>'
LITTLE_ENDIAN = '<'
LC_LOAD_DYLIB = 0xc
maxint = majver == 3 and getattr(sys, 'maxsize') or getattr(sys, 'maxint')


class fileview(object):
    """
    A proxy for file-like objects that exposes a given view of a file.
    Modified from macholib.
    """

    def __init__(self, fileobj, start=0, size=maxint):
        if isinstance(fileobj, fileview):
            self._fileobj = fileobj._fileobj
        else:
            self._fileobj = fileobj
        self._start = start
        self._end = start + size
        self._pos = 0

    def __repr__(self):
        return '<fileview [%d, %d] %r>' % (
            self._start, self._end, self._fileobj)

    def tell(self):
        return self._pos

    def _checkwindow(self, seekto, op):
        if not (self._start <= seekto <= self._end):
            raise IOError("%s to offset %d is outside window [%d, %d]" % (
                op, seekto, self._start, self._end))

    def seek(self, offset, whence=0):
        seekto = offset
        if whence == os.SEEK_SET:
            seekto += self._start
        elif whence == os.SEEK_CUR:
            seekto += self._start + self._pos
        elif whence == os.SEEK_END:
            seekto += self._end
        else:
            raise IOError("Invalid whence argument to seek: %r" % (whence,))
        self._checkwindow(seekto, 'seek')
        self._fileobj.seek(seekto)
        self._pos = seekto - self._start

    def write(self, bytes):
        here = self._start + self._pos
        self._checkwindow(here, 'write')
        self._checkwindow(here + len(bytes), 'write')
        self._fileobj.seek(here, os.SEEK_SET)
        self._fileobj.write(bytes)
        self._pos += len(bytes)

    def read(self, size=maxint):
        assert size >= 0
        here = self._start + self._pos
        self._checkwindow(here, 'read')
        size = min(size, self._end - here)
        self._fileobj.seek(here, os.SEEK_SET)
        bytes = self._fileobj.read(size)
        self._pos += len(bytes)
        return bytes


def read_data(file, endian, num=1):
    """
    Read a given number of 32-bits unsigned integers from the given file
    with the given endianness.
    """
    res = struct.unpack(endian + 'L' * num, file.read(num * 4))
    if len(res) == 1:
        return res[0]
    return res


def mach_o_change(path, what, value):
    """
    Replace a given name (what) in any LC_LOAD_DYLIB command found in
    the given binary with a new name (value), provided it's shorter.
    """

    def do_macho(file, bits, endian):
        # Read Mach-O header (the magic number is assumed read by the caller)
        cputype, cpusubtype, filetype, ncmds, sizeofcmds, flags = read_data(file, endian, 6)
        # 64-bits header has one more field.
        if bits == 64:
            read_data(file, endian)
        # The header is followed by ncmds commands
        for n in range(ncmds):
            where = file.tell()
            # Read command header
            cmd, cmdsize = read_data(file, endian, 2)
            if cmd == LC_LOAD_DYLIB:
                # The first data field in LC_LOAD_DYLIB commands is the
                # offset of the name, starting from the beginning of the
                # command.
                name_offset = read_data(file, endian)
                file.seek(where + name_offset, os.SEEK_SET)
                # Read the NUL terminated string
                load = file.read(cmdsize - name_offset).decode()
                load = load[:load.index('\0')]
                # If the string is what is being replaced, overwrite it.
                if load == what:
                    file.seek(where + name_offset, os.SEEK_SET)
                    file.write(value.encode() + '\0'.encode())
            # Seek to the next command
            file.seek(where + cmdsize, os.SEEK_SET)

    def do_file(file, offset=0, size=maxint):
        file = fileview(file, offset, size)
        # Read magic number
        magic = read_data(file, BIG_ENDIAN)
        if magic == FAT_MAGIC:
            # Fat binaries contain nfat_arch Mach-O binaries
            nfat_arch = read_data(file, BIG_ENDIAN)
            for n in range(nfat_arch):
                # Read arch header
                cputype, cpusubtype, offset, size, align = read_data(file, BIG_ENDIAN, 5)
                do_file(file, offset, size)
        elif magic == MH_MAGIC:
            do_macho(file, 32, BIG_ENDIAN)
        elif magic == MH_CIGAM:
            do_macho(file, 32, LITTLE_ENDIAN)
        elif magic == MH_MAGIC_64:
            do_macho(file, 64, BIG_ENDIAN)
        elif magic == MH_CIGAM_64:
            do_macho(file, 64, LITTLE_ENDIAN)

    assert(len(what) >= len(value))
    do_file(open(path, 'r+b'))


if __name__ == '__main__':
    main()

## TODO:
## Copy python.exe.manifest
## Monkeypatch distutils.sysconfig

########NEW FILE########
__FILENAME__ = virtualenv_1.7
#!/usr/bin/env python
"""Create a "virtual" Python installation
"""

# If you change the version here, change it in setup.py
# and docs/conf.py as well.
virtualenv_version = "1.7"

import base64
import sys
import os
import optparse
import re
import shutil
import logging
import tempfile
import zlib
import errno
import distutils.sysconfig
from distutils.util import strtobool

try:
    import subprocess
except ImportError:
    if sys.version_info <= (2, 3):
        print('ERROR: %s' % sys.exc_info()[1])
        print('ERROR: this script requires Python 2.4 or greater; or at least the subprocess module.')
        print('If you copy subprocess.py from a newer version of Python this script will probably work')
        sys.exit(101)
    else:
        raise
try:
    set
except NameError:
    from sets import Set as set
try:
    basestring
except NameError:
    basestring = str

try:
    import ConfigParser
except ImportError:
    import configparser as ConfigParser

join = os.path.join
py_version = 'python%s.%s' % (sys.version_info[0], sys.version_info[1])

is_jython = sys.platform.startswith('java')
is_pypy = hasattr(sys, 'pypy_version_info')
is_win  = (sys.platform == 'win32')
abiflags = getattr(sys, 'abiflags', '')

user_dir = os.path.expanduser('~')
if sys.platform == 'win32':
    user_dir = os.environ.get('APPDATA', user_dir)  # Use %APPDATA% for roaming
    default_storage_dir = os.path.join(user_dir, 'virtualenv')
else:
    default_storage_dir = os.path.join(user_dir, '.virtualenv')
default_config_file = os.path.join(default_storage_dir, 'virtualenv.ini')

if is_pypy:
    expected_exe = 'pypy'
elif is_jython:
    expected_exe = 'jython'
else:
    expected_exe = 'python'


REQUIRED_MODULES = ['os', 'posix', 'posixpath', 'nt', 'ntpath', 'genericpath',
                    'fnmatch', 'locale', 'encodings', 'codecs',
                    'stat', 'UserDict', 'readline', 'copy_reg', 'types',
                    're', 'sre', 'sre_parse', 'sre_constants', 'sre_compile',
                    'zlib']

REQUIRED_FILES = ['lib-dynload', 'config']

majver, minver = sys.version_info[:2]
if majver == 2:
    if minver >= 6:
        REQUIRED_MODULES.extend(['warnings', 'linecache', '_abcoll', 'abc'])
    if minver >= 7:
        REQUIRED_MODULES.extend(['_weakrefset'])
    if minver <= 3:
        REQUIRED_MODULES.extend(['sets', '__future__'])
elif majver == 3:
    # Some extra modules are needed for Python 3, but different ones
    # for different versions.
    REQUIRED_MODULES.extend(['_abcoll', 'warnings', 'linecache', 'abc', 'io',
                             '_weakrefset', 'copyreg', 'tempfile', 'random',
                             '__future__', 'collections', 'keyword', 'tarfile',
                             'shutil', 'struct', 'copy'])
    if minver >= 2:
        REQUIRED_FILES[-1] = 'config-%s' % majver
    if minver == 3:
        # The whole list of 3.3 modules is reproduced below - the current
        # uncommented ones are required for 3.3 as of now, but more may be
        # added as 3.3 development continues.
        REQUIRED_MODULES.extend([
            #"aifc",
            #"antigravity",
            #"argparse",
            #"ast",
            #"asynchat",
            #"asyncore",
            "base64",
            #"bdb",
            #"binhex",
            "bisect",
            #"calendar",
            #"cgi",
            #"cgitb",
            #"chunk",
            #"cmd",
            #"codeop",
            #"code",
            #"colorsys",
            #"_compat_pickle",
            #"compileall",
            #"concurrent",
            #"configparser",
            #"contextlib",
            #"cProfile",
            #"crypt",
            #"csv",
            #"ctypes",
            #"curses",
            #"datetime",
            #"dbm",
            #"decimal",
            #"difflib",
            #"dis",
            #"doctest",
            #"dummy_threading",
            "_dummy_thread",
            #"email",
            #"filecmp",
            #"fileinput",
            #"formatter",
            #"fractions",
            #"ftplib",
            #"functools",
            #"getopt",
            #"getpass",
            #"gettext",
            #"glob",
            #"gzip",
            "hashlib",
            "heapq",
            "hmac",
            #"html",
            #"http",
            #"idlelib",
            #"imaplib",
            #"imghdr",
            #"importlib",
            #"inspect",
            #"json",
            #"lib2to3",
            #"logging",
            #"macpath",
            #"macurl2path",
            #"mailbox",
            #"mailcap",
            #"_markupbase",
            #"mimetypes",
            #"modulefinder",
            #"multiprocessing",
            #"netrc",
            #"nntplib",
            #"nturl2path",
            #"numbers",
            #"opcode",
            #"optparse",
            #"os2emxpath",
            #"pdb",
            #"pickle",
            #"pickletools",
            #"pipes",
            #"pkgutil",
            #"platform",
            #"plat-linux2",
            #"plistlib",
            #"poplib",
            #"pprint",
            #"profile",
            #"pstats",
            #"pty",
            #"pyclbr",
            #"py_compile",
            #"pydoc_data",
            #"pydoc",
            #"_pyio",
            #"queue",
            #"quopri",
            "reprlib",
            "rlcompleter",
            #"runpy",
            #"sched",
            #"shelve",
            #"shlex",
            #"smtpd",
            #"smtplib",
            #"sndhdr",
            #"socket",
            #"socketserver",
            #"sqlite3",
            #"ssl",
            #"stringprep",
            #"string",
            #"_strptime",
            #"subprocess",
            #"sunau",
            #"symbol",
            #"symtable",
            #"sysconfig",
            #"tabnanny",
            #"telnetlib",
            #"test",
            #"textwrap",
            #"this",
            #"_threading_local",
            #"threading",
            #"timeit",
            #"tkinter",
            #"tokenize",
            #"token",
            #"traceback",
            #"trace",
            #"tty",
            #"turtledemo",
            #"turtle",
            #"unittest",
            #"urllib",
            #"uuid",
            #"uu",
            #"wave",
            "weakref",
            #"webbrowser",
            #"wsgiref",
            #"xdrlib",
            #"xml",
            #"xmlrpc",
            #"zipfile",
        ])

if is_pypy:
    # these are needed to correctly display the exceptions that may happen
    # during the bootstrap
    REQUIRED_MODULES.extend(['traceback', 'linecache'])

class Logger(object):

    """
    Logging object for use in command-line script.  Allows ranges of
    levels, to avoid some redundancy of displayed information.
    """

    DEBUG = logging.DEBUG
    INFO = logging.INFO
    NOTIFY = (logging.INFO+logging.WARN)/2
    WARN = WARNING = logging.WARN
    ERROR = logging.ERROR
    FATAL = logging.FATAL

    LEVELS = [DEBUG, INFO, NOTIFY, WARN, ERROR, FATAL]

    def __init__(self, consumers):
        self.consumers = consumers
        self.indent = 0
        self.in_progress = None
        self.in_progress_hanging = False

    def debug(self, msg, *args, **kw):
        self.log(self.DEBUG, msg, *args, **kw)
    def info(self, msg, *args, **kw):
        self.log(self.INFO, msg, *args, **kw)
    def notify(self, msg, *args, **kw):
        self.log(self.NOTIFY, msg, *args, **kw)
    def warn(self, msg, *args, **kw):
        self.log(self.WARN, msg, *args, **kw)
    def error(self, msg, *args, **kw):
        self.log(self.WARN, msg, *args, **kw)
    def fatal(self, msg, *args, **kw):
        self.log(self.FATAL, msg, *args, **kw)
    def log(self, level, msg, *args, **kw):
        if args:
            if kw:
                raise TypeError(
                    "You may give positional or keyword arguments, not both")
        args = args or kw
        rendered = None
        for consumer_level, consumer in self.consumers:
            if self.level_matches(level, consumer_level):
                if (self.in_progress_hanging
                    and consumer in (sys.stdout, sys.stderr)):
                    self.in_progress_hanging = False
                    sys.stdout.write('\n')
                    sys.stdout.flush()
                if rendered is None:
                    if args:
                        rendered = msg % args
                    else:
                        rendered = msg
                    rendered = ' '*self.indent + rendered
                if hasattr(consumer, 'write'):
                    consumer.write(rendered+'\n')
                else:
                    consumer(rendered)

    def start_progress(self, msg):
        assert not self.in_progress, (
            "Tried to start_progress(%r) while in_progress %r"
            % (msg, self.in_progress))
        if self.level_matches(self.NOTIFY, self._stdout_level()):
            sys.stdout.write(msg)
            sys.stdout.flush()
            self.in_progress_hanging = True
        else:
            self.in_progress_hanging = False
        self.in_progress = msg

    def end_progress(self, msg='done.'):
        assert self.in_progress, (
            "Tried to end_progress without start_progress")
        if self.stdout_level_matches(self.NOTIFY):
            if not self.in_progress_hanging:
                # Some message has been printed out since start_progress
                sys.stdout.write('...' + self.in_progress + msg + '\n')
                sys.stdout.flush()
            else:
                sys.stdout.write(msg + '\n')
                sys.stdout.flush()
        self.in_progress = None
        self.in_progress_hanging = False

    def show_progress(self):
        """If we are in a progress scope, and no log messages have been
        shown, write out another '.'"""
        if self.in_progress_hanging:
            sys.stdout.write('.')
            sys.stdout.flush()

    def stdout_level_matches(self, level):
        """Returns true if a message at this level will go to stdout"""
        return self.level_matches(level, self._stdout_level())

    def _stdout_level(self):
        """Returns the level that stdout runs at"""
        for level, consumer in self.consumers:
            if consumer is sys.stdout:
                return level
        return self.FATAL

    def level_matches(self, level, consumer_level):
        """
        >>> l = Logger([])
        >>> l.level_matches(3, 4)
        False
        >>> l.level_matches(3, 2)
        True
        >>> l.level_matches(slice(None, 3), 3)
        False
        >>> l.level_matches(slice(None, 3), 2)
        True
        >>> l.level_matches(slice(1, 3), 1)
        True
        >>> l.level_matches(slice(2, 3), 1)
        False
        """
        if isinstance(level, slice):
            start, stop = level.start, level.stop
            if start is not None and start > consumer_level:
                return False
            if stop is not None and stop <= consumer_level:
                return False
            return True
        else:
            return level >= consumer_level

    #@classmethod
    def level_for_integer(cls, level):
        levels = cls.LEVELS
        if level < 0:
            return levels[0]
        if level >= len(levels):
            return levels[-1]
        return levels[level]

    level_for_integer = classmethod(level_for_integer)

# create a silent logger just to prevent this from being undefined
# will be overridden with requested verbosity main() is called.
logger = Logger([(Logger.LEVELS[-1], sys.stdout)])

def mkdir(path):
    if not os.path.exists(path):
        logger.info('Creating %s', path)
        os.makedirs(path)
    else:
        logger.info('Directory %s already exists', path)

def copyfileordir(src, dest):
    if os.path.isdir(src):
        shutil.copytree(src, dest, True)
    else:
        shutil.copy2(src, dest)

def copyfile(src, dest, symlink=True):
    if not os.path.exists(src):
        # Some bad symlink in the src
        logger.warn('Cannot find file %s (bad symlink)', src)
        return
    if os.path.exists(dest):
        logger.debug('File %s already exists', dest)
        return
    if not os.path.exists(os.path.dirname(dest)):
        logger.info('Creating parent directories for %s' % os.path.dirname(dest))
        os.makedirs(os.path.dirname(dest))
    if not os.path.islink(src):
        srcpath = os.path.abspath(src)
    else:
        srcpath = os.readlink(src)
    if symlink and hasattr(os, 'symlink'):
        logger.info('Symlinking %s', dest)
        try:
            os.symlink(srcpath, dest)
        except (OSError, NotImplementedError):
            logger.info('Symlinking failed, copying to %s', dest)
            copyfileordir(src, dest)
    else:
        logger.info('Copying to %s', dest)
        copyfileordir(src, dest)

def writefile(dest, content, overwrite=True):
    if not os.path.exists(dest):
        logger.info('Writing %s', dest)
        f = open(dest, 'wb')
        f.write(content.encode('utf-8'))
        f.close()
        return
    else:
        f = open(dest, 'rb')
        c = f.read()
        f.close()
        if c != content:
            if not overwrite:
                logger.notify('File %s exists with different content; not overwriting', dest)
                return
            logger.notify('Overwriting %s with new content', dest)
            f = open(dest, 'wb')
            f.write(content.encode('utf-8'))
            f.close()
        else:
            logger.info('Content %s already in place', dest)

def rmtree(dir):
    if os.path.exists(dir):
        logger.notify('Deleting tree %s', dir)
        shutil.rmtree(dir)
    else:
        logger.info('Do not need to delete %s; already gone', dir)

def make_exe(fn):
    if hasattr(os, 'chmod'):
        oldmode = os.stat(fn).st_mode & 0xFFF # 0o7777
        newmode = (oldmode | 0x16D) & 0xFFF # 0o555, 0o7777
        os.chmod(fn, newmode)
        logger.info('Changed mode of %s to %s', fn, oct(newmode))

def _find_file(filename, dirs):
    for dir in dirs:
        if os.path.exists(join(dir, filename)):
            return join(dir, filename)
    return filename

def _install_req(py_executable, unzip=False, distribute=False,
                 search_dirs=None, never_download=False):

    if search_dirs is None:
        search_dirs = file_search_dirs()

    if not distribute:
        setup_fn = 'setuptools-0.6c11-py%s.egg' % sys.version[:3]
        project_name = 'setuptools'
        bootstrap_script = EZ_SETUP_PY
        source = None
    else:
        setup_fn = None
        source = 'distribute-0.6.24.tar.gz'
        project_name = 'distribute'
        bootstrap_script = DISTRIBUTE_SETUP_PY

    if setup_fn is not None:
        setup_fn = _find_file(setup_fn, search_dirs)

    if source is not None:
        source = _find_file(source, search_dirs)

    if is_jython and os._name == 'nt':
        # Jython's .bat sys.executable can't handle a command line
        # argument with newlines
        fd, ez_setup = tempfile.mkstemp('.py')
        os.write(fd, bootstrap_script)
        os.close(fd)
        cmd = [py_executable, ez_setup]
    else:
        cmd = [py_executable, '-c', bootstrap_script]
    if unzip:
        cmd.append('--always-unzip')
    env = {}
    remove_from_env = []
    if logger.stdout_level_matches(logger.DEBUG):
        cmd.append('-v')

    old_chdir = os.getcwd()
    if setup_fn is not None and os.path.exists(setup_fn):
        logger.info('Using existing %s egg: %s' % (project_name, setup_fn))
        cmd.append(setup_fn)
        if os.environ.get('PYTHONPATH'):
            env['PYTHONPATH'] = setup_fn + os.path.pathsep + os.environ['PYTHONPATH']
        else:
            env['PYTHONPATH'] = setup_fn
    else:
        # the source is found, let's chdir
        if source is not None and os.path.exists(source):
            logger.info('Using existing %s egg: %s' % (project_name, source))
            os.chdir(os.path.dirname(source))
            # in this case, we want to be sure that PYTHONPATH is unset (not
            # just empty, really unset), else CPython tries to import the
            # site.py that it's in virtualenv_support
            remove_from_env.append('PYTHONPATH')
        else:
            if never_download:
                logger.fatal("Can't find any local distributions of %s to install "
                             "and --never-download is set.  Either re-run virtualenv "
                             "without the --never-download option, or place a %s "
                             "distribution (%s) in one of these "
                             "locations: %r" % (project_name, project_name,
                                                setup_fn or source,
                                                search_dirs))
                sys.exit(1)

            logger.info('No %s egg found; downloading' % project_name)
        cmd.extend(['--always-copy', '-U', project_name])
    logger.start_progress('Installing %s...' % project_name)
    logger.indent += 2
    cwd = None
    if project_name == 'distribute':
        env['DONT_PATCH_SETUPTOOLS'] = 'true'

    def _filter_ez_setup(line):
        return filter_ez_setup(line, project_name)

    if not os.access(os.getcwd(), os.W_OK):
        cwd = tempfile.mkdtemp()
        if source is not None and os.path.exists(source):
            # the current working dir is hostile, let's copy the
            # tarball to a temp dir
            target = os.path.join(cwd, os.path.split(source)[-1])
            shutil.copy(source, target)
    try:
        call_subprocess(cmd, show_stdout=False,
                        filter_stdout=_filter_ez_setup,
                        extra_env=env,
                        remove_from_env=remove_from_env,
                        cwd=cwd)
    finally:
        logger.indent -= 2
        logger.end_progress()
        if os.getcwd() != old_chdir:
            os.chdir(old_chdir)
        if is_jython and os._name == 'nt':
            os.remove(ez_setup)

def file_search_dirs():
    here = os.path.dirname(os.path.abspath(__file__))
    dirs = ['.', here,
            join(here, 'virtualenv_support')]
    if os.path.splitext(os.path.dirname(__file__))[0] != 'virtualenv':
        # Probably some boot script; just in case virtualenv is installed...
        try:
            import virtualenv
        except ImportError:
            pass
        else:
            dirs.append(os.path.join(os.path.dirname(virtualenv.__file__), 'virtualenv_support'))
    return [d for d in dirs if os.path.isdir(d)]

def install_setuptools(py_executable, unzip=False,
                       search_dirs=None, never_download=False):
    _install_req(py_executable, unzip,
                 search_dirs=search_dirs, never_download=never_download)

def install_distribute(py_executable, unzip=False,
                       search_dirs=None, never_download=False):
    _install_req(py_executable, unzip, distribute=True,
                 search_dirs=search_dirs, never_download=never_download)

_pip_re = re.compile(r'^pip-.*(zip|tar.gz|tar.bz2|tgz|tbz)$', re.I)
def install_pip(py_executable, search_dirs=None, never_download=False):
    if search_dirs is None:
        search_dirs = file_search_dirs()

    filenames = []
    for dir in search_dirs:
        filenames.extend([join(dir, fn) for fn in os.listdir(dir)
                          if _pip_re.search(fn)])
    filenames = [(os.path.basename(filename).lower(), i, filename) for i, filename in enumerate(filenames)]
    filenames.sort()
    filenames = [filename for basename, i, filename in filenames]
    if not filenames:
        filename = 'pip'
    else:
        filename = filenames[-1]
    easy_install_script = 'easy_install'
    if sys.platform == 'win32':
        easy_install_script = 'easy_install-script.py'
    cmd = [join(os.path.dirname(py_executable), easy_install_script), filename]
    if sys.platform == 'win32':
        cmd.insert(0, py_executable)
    if filename == 'pip':
        if never_download:
            logger.fatal("Can't find any local distributions of pip to install "
                         "and --never-download is set.  Either re-run virtualenv "
                         "without the --never-download option, or place a pip "
                         "source distribution (zip/tar.gz/tar.bz2) in one of these "
                         "locations: %r" % search_dirs)
            sys.exit(1)
        logger.info('Installing pip from network...')
    else:
        logger.info('Installing existing %s distribution: %s' % (
                os.path.basename(filename), filename))
    logger.start_progress('Installing pip...')
    logger.indent += 2
    def _filter_setup(line):
        return filter_ez_setup(line, 'pip')
    try:
        call_subprocess(cmd, show_stdout=False,
                        filter_stdout=_filter_setup)
    finally:
        logger.indent -= 2
        logger.end_progress()

def filter_ez_setup(line, project_name='setuptools'):
    if not line.strip():
        return Logger.DEBUG
    if project_name == 'distribute':
        for prefix in ('Extracting', 'Now working', 'Installing', 'Before',
                       'Scanning', 'Setuptools', 'Egg', 'Already',
                       'running', 'writing', 'reading', 'installing',
                       'creating', 'copying', 'byte-compiling', 'removing',
                       'Processing'):
            if line.startswith(prefix):
                return Logger.DEBUG
        return Logger.DEBUG
    for prefix in ['Reading ', 'Best match', 'Processing setuptools',
                   'Copying setuptools', 'Adding setuptools',
                   'Installing ', 'Installed ']:
        if line.startswith(prefix):
            return Logger.DEBUG
    return Logger.INFO


class UpdatingDefaultsHelpFormatter(optparse.IndentedHelpFormatter):
    """
    Custom help formatter for use in ConfigOptionParser that updates
    the defaults before expanding them, allowing them to show up correctly
    in the help listing
    """
    def expand_default(self, option):
        if self.parser is not None:
            self.parser.update_defaults(self.parser.defaults)
        return optparse.IndentedHelpFormatter.expand_default(self, option)


class ConfigOptionParser(optparse.OptionParser):
    """
    Custom option parser which updates its defaults by by checking the
    configuration files and environmental variables
    """
    def __init__(self, *args, **kwargs):
        self.config = ConfigParser.RawConfigParser()
        self.files = self.get_config_files()
        self.config.read(self.files)
        optparse.OptionParser.__init__(self, *args, **kwargs)

    def get_config_files(self):
        config_file = os.environ.get('VIRTUALENV_CONFIG_FILE', False)
        if config_file and os.path.exists(config_file):
            return [config_file]
        return [default_config_file]

    def update_defaults(self, defaults):
        """
        Updates the given defaults with values from the config files and
        the environ. Does a little special handling for certain types of
        options (lists).
        """
        # Then go and look for the other sources of configuration:
        config = {}
        # 1. config files
        config.update(dict(self.get_config_section('virtualenv')))
        # 2. environmental variables
        config.update(dict(self.get_environ_vars()))
        # Then set the options with those values
        for key, val in config.items():
            key = key.replace('_', '-')
            if not key.startswith('--'):
                key = '--%s' % key  # only prefer long opts
            option = self.get_option(key)
            if option is not None:
                # ignore empty values
                if not val:
                    continue
                # handle multiline configs
                if option.action == 'append':
                    val = val.split()
                else:
                    option.nargs = 1
                if option.action in ('store_true', 'store_false', 'count'):
                    val = strtobool(val)
                try:
                    val = option.convert_value(key, val)
                except optparse.OptionValueError:
                    e = sys.exc_info()[1]
                    print("An error occured during configuration: %s" % e)
                    sys.exit(3)
                defaults[option.dest] = val
        return defaults

    def get_config_section(self, name):
        """
        Get a section of a configuration
        """
        if self.config.has_section(name):
            return self.config.items(name)
        return []

    def get_environ_vars(self, prefix='VIRTUALENV_'):
        """
        Returns a generator with all environmental vars with prefix VIRTUALENV
        """
        for key, val in os.environ.items():
            if key.startswith(prefix):
                yield (key.replace(prefix, '').lower(), val)

    def get_default_values(self):
        """
        Overridding to make updating the defaults after instantiation of
        the option parser possible, update_defaults() does the dirty work.
        """
        if not self.process_default_values:
            # Old, pre-Optik 1.5 behaviour.
            return optparse.Values(self.defaults)

        defaults = self.update_defaults(self.defaults.copy()) # ours
        for option in self._get_all_options():
            default = defaults.get(option.dest)
            if isinstance(default, basestring):
                opt_str = option.get_opt_string()
                defaults[option.dest] = option.check_value(opt_str, default)
        return optparse.Values(defaults)


def main():
    parser = ConfigOptionParser(
        version=virtualenv_version,
        usage="%prog [OPTIONS] DEST_DIR",
        formatter=UpdatingDefaultsHelpFormatter())

    parser.add_option(
        '-v', '--verbose',
        action='count',
        dest='verbose',
        default=0,
        help="Increase verbosity")

    parser.add_option(
        '-q', '--quiet',
        action='count',
        dest='quiet',
        default=0,
        help='Decrease verbosity')

    parser.add_option(
        '-p', '--python',
        dest='python',
        metavar='PYTHON_EXE',
        help='The Python interpreter to use, e.g., --python=python2.5 will use the python2.5 '
        'interpreter to create the new environment.  The default is the interpreter that '
        'virtualenv was installed with (%s)' % sys.executable)

    parser.add_option(
        '--clear',
        dest='clear',
        action='store_true',
        help="Clear out the non-root install and start from scratch")

    parser.add_option(
        '--no-site-packages',
        dest='no_site_packages',
        action='store_true',
        help="Don't give access to the global site-packages dir to the "
             "virtual environment")

    parser.add_option(
        '--system-site-packages',
        dest='system_site_packages',
        action='store_true',
        help="Give access to the global site-packages dir to the "
             "virtual environment")

    parser.add_option(
        '--unzip-setuptools',
        dest='unzip_setuptools',
        action='store_true',
        help="Unzip Setuptools or Distribute when installing it")

    parser.add_option(
        '--relocatable',
        dest='relocatable',
        action='store_true',
        help='Make an EXISTING virtualenv environment relocatable.  '
        'This fixes up scripts and makes all .pth files relative')

    parser.add_option(
        '--distribute',
        dest='use_distribute',
        action='store_true',
        help='Use Distribute instead of Setuptools. Set environ variable '
        'VIRTUALENV_DISTRIBUTE to make it the default ')

    default_search_dirs = file_search_dirs()
    parser.add_option(
        '--extra-search-dir',
        dest="search_dirs",
        action="append",
        default=default_search_dirs,
        help="Directory to look for setuptools/distribute/pip distributions in. "
        "You can add any number of additional --extra-search-dir paths.")

    parser.add_option(
        '--never-download',
        dest="never_download",
        action="store_true",
        help="Never download anything from the network.  Instead, virtualenv will fail "
        "if local distributions of setuptools/distribute/pip are not present.")

    parser.add_option(
        '--prompt=',
        dest='prompt',
        help='Provides an alternative prompt prefix for this environment')

    if 'extend_parser' in globals():
        extend_parser(parser)

    options, args = parser.parse_args()

    global logger

    if 'adjust_options' in globals():
        adjust_options(options, args)

    verbosity = options.verbose - options.quiet
    logger = Logger([(Logger.level_for_integer(2-verbosity), sys.stdout)])

    if options.python and not os.environ.get('VIRTUALENV_INTERPRETER_RUNNING'):
        env = os.environ.copy()
        interpreter = resolve_interpreter(options.python)
        if interpreter == sys.executable:
            logger.warn('Already using interpreter %s' % interpreter)
        else:
            logger.notify('Running virtualenv with interpreter %s' % interpreter)
            env['VIRTUALENV_INTERPRETER_RUNNING'] = 'true'
            file = __file__
            if file.endswith('.pyc'):
                file = file[:-1]
            popen = subprocess.Popen([interpreter, file] + sys.argv[1:], env=env)
            raise SystemExit(popen.wait())

    # Force --use-distribute on Python 3, since setuptools is not available.
    if majver > 2:
        options.use_distribute = True

    if os.environ.get('PYTHONDONTWRITEBYTECODE') and not options.use_distribute:
        print(
            "The PYTHONDONTWRITEBYTECODE environment variable is "
            "not compatible with setuptools. Either use --distribute "
            "or unset PYTHONDONTWRITEBYTECODE.")
        sys.exit(2)
    if not args:
        print('You must provide a DEST_DIR')
        parser.print_help()
        sys.exit(2)
    if len(args) > 1:
        print('There must be only one argument: DEST_DIR (you gave %s)' % (
            ' '.join(args)))
        parser.print_help()
        sys.exit(2)

    home_dir = args[0]

    if os.environ.get('WORKING_ENV'):
        logger.fatal('ERROR: you cannot run virtualenv while in a workingenv')
        logger.fatal('Please deactivate your workingenv, then re-run this script')
        sys.exit(3)

    if 'PYTHONHOME' in os.environ:
        logger.warn('PYTHONHOME is set.  You *must* activate the virtualenv before using it')
        del os.environ['PYTHONHOME']

    if options.relocatable:
        make_environment_relocatable(home_dir)
        return

    if options.no_site_packages:
        logger.warn('The --no-site-packages flag is deprecated; it is now '
                    'the default behavior.')

    create_environment(home_dir,
                       site_packages=options.system_site_packages,
                       clear=options.clear,
                       unzip_setuptools=options.unzip_setuptools,
                       use_distribute=options.use_distribute,
                       prompt=options.prompt,
                       search_dirs=options.search_dirs,
                       never_download=options.never_download)
    if 'after_install' in globals():
        after_install(options, home_dir)

def call_subprocess(cmd, show_stdout=True,
                    filter_stdout=None, cwd=None,
                    raise_on_returncode=True, extra_env=None,
                    remove_from_env=None):
    cmd_parts = []
    for part in cmd:
        if len(part) > 45:
            part = part[:20]+"..."+part[-20:]
        if ' ' in part or '\n' in part or '"' in part or "'" in part:
            part = '"%s"' % part.replace('"', '\\"')
        if hasattr(part, 'decode'):
            try:
                part = part.decode(sys.getdefaultencoding())
            except UnicodeDecodeError:
                part = part.decode(sys.getfilesystemencoding())
        cmd_parts.append(part)
    cmd_desc = ' '.join(cmd_parts)
    if show_stdout:
        stdout = None
    else:
        stdout = subprocess.PIPE
    logger.debug("Running command %s" % cmd_desc)
    if extra_env or remove_from_env:
        env = os.environ.copy()
        if extra_env:
            env.update(extra_env)
        if remove_from_env:
            for varname in remove_from_env:
                env.pop(varname, None)
    else:
        env = None
    try:
        proc = subprocess.Popen(
            cmd, stderr=subprocess.STDOUT, stdin=None, stdout=stdout,
            cwd=cwd, env=env)
    except Exception:
        e = sys.exc_info()[1]
        logger.fatal(
            "Error %s while executing command %s" % (e, cmd_desc))
        raise
    all_output = []
    if stdout is not None:
        stdout = proc.stdout
        encoding = sys.getdefaultencoding()
        fs_encoding = sys.getfilesystemencoding()
        while 1:
            line = stdout.readline()
            try:
                line = line.decode(encoding)
            except UnicodeDecodeError:
                line = line.decode(fs_encoding)
            if not line:
                break
            line = line.rstrip()
            all_output.append(line)
            if filter_stdout:
                level = filter_stdout(line)
                if isinstance(level, tuple):
                    level, line = level
                logger.log(level, line)
                if not logger.stdout_level_matches(level):
                    logger.show_progress()
            else:
                logger.info(line)
    else:
        proc.communicate()
    proc.wait()
    if proc.returncode:
        if raise_on_returncode:
            if all_output:
                logger.notify('Complete output from command %s:' % cmd_desc)
                logger.notify('\n'.join(all_output) + '\n----------------------------------------')
            raise OSError(
                "Command %s failed with error code %s"
                % (cmd_desc, proc.returncode))
        else:
            logger.warn(
                "Command %s had error code %s"
                % (cmd_desc, proc.returncode))


def create_environment(home_dir, site_packages=False, clear=False,
                       unzip_setuptools=False, use_distribute=False,
                       prompt=None, search_dirs=None, never_download=False):
    """
    Creates a new environment in ``home_dir``.

    If ``site_packages`` is true, then the global ``site-packages/``
    directory will be on the path.

    If ``clear`` is true (default False) then the environment will
    first be cleared.
    """
    home_dir, lib_dir, inc_dir, bin_dir = path_locations(home_dir)

    py_executable = os.path.abspath(install_python(
        home_dir, lib_dir, inc_dir, bin_dir,
        site_packages=site_packages, clear=clear))

    install_distutils(home_dir)

    # use_distribute also is True if VIRTUALENV_DISTRIBUTE env var is set
    # we also check VIRTUALENV_USE_DISTRIBUTE for backwards compatibility
    if use_distribute or os.environ.get('VIRTUALENV_USE_DISTRIBUTE'):
        install_distribute(py_executable, unzip=unzip_setuptools,
                           search_dirs=search_dirs, never_download=never_download)
    else:
        install_setuptools(py_executable, unzip=unzip_setuptools,
                           search_dirs=search_dirs, never_download=never_download)

    install_pip(py_executable, search_dirs=search_dirs, never_download=never_download)

    install_activate(home_dir, bin_dir, prompt)

def path_locations(home_dir):
    """Return the path locations for the environment (where libraries are,
    where scripts go, etc)"""
    # XXX: We'd use distutils.sysconfig.get_python_inc/lib but its
    # prefix arg is broken: http://bugs.python.org/issue3386
    if sys.platform == 'win32':
        # Windows has lots of problems with executables with spaces in
        # the name; this function will remove them (using the ~1
        # format):
        mkdir(home_dir)
        if ' ' in home_dir:
            try:
                import win32api
            except ImportError:
                print('Error: the path "%s" has a space in it' % home_dir)
                print('To handle these kinds of paths, the win32api module must be installed:')
                print('  http://sourceforge.net/projects/pywin32/')
                sys.exit(3)
            home_dir = win32api.GetShortPathName(home_dir)
        lib_dir = join(home_dir, 'Lib')
        inc_dir = join(home_dir, 'Include')
        bin_dir = join(home_dir, 'Scripts')
    elif is_jython:
        lib_dir = join(home_dir, 'Lib')
        inc_dir = join(home_dir, 'Include')
        bin_dir = join(home_dir, 'bin')
    elif is_pypy:
        lib_dir = home_dir
        inc_dir = join(home_dir, 'include')
        bin_dir = join(home_dir, 'bin')
    else:
        lib_dir = join(home_dir, 'lib', py_version)
        inc_dir = join(home_dir, 'include', py_version + abiflags)
        bin_dir = join(home_dir, 'bin')
    return home_dir, lib_dir, inc_dir, bin_dir


def change_prefix(filename, dst_prefix):
    prefixes = [sys.prefix]

    if sys.platform == "darwin":
        prefixes.extend((
            os.path.join("/Library/Python", sys.version[:3], "site-packages"),
            os.path.join(sys.prefix, "Extras", "lib", "python"),
            os.path.join("~", "Library", "Python", sys.version[:3], "site-packages")))

    if hasattr(sys, 'real_prefix'):
        prefixes.append(sys.real_prefix)
    prefixes = list(map(os.path.abspath, prefixes))
    filename = os.path.abspath(filename)
    for src_prefix in prefixes:
        if filename.startswith(src_prefix):
            _, relpath = filename.split(src_prefix, 1)
            assert relpath[0] == os.sep
            relpath = relpath[1:]
            return join(dst_prefix, relpath)
    assert False, "Filename %s does not start with any of these prefixes: %s" % \
        (filename, prefixes)

def copy_required_modules(dst_prefix):
    import imp
    for modname in REQUIRED_MODULES:
        if modname in sys.builtin_module_names:
            logger.info("Ignoring built-in bootstrap module: %s" % modname)
            continue
        try:
            f, filename, _ = imp.find_module(modname)
        except ImportError:
            logger.info("Cannot import bootstrap module: %s" % modname)
        else:
            if f is not None:
                f.close()
            dst_filename = change_prefix(filename, dst_prefix)
            copyfile(filename, dst_filename)
            if filename.endswith('.pyc'):
                pyfile = filename[:-1]
                if os.path.exists(pyfile):
                    copyfile(pyfile, dst_filename[:-1])


def install_python(home_dir, lib_dir, inc_dir, bin_dir, site_packages, clear):
    """Install just the base environment, no distutils patches etc"""
    if sys.executable.startswith(bin_dir):
        print('Please use the *system* python to run this script')
        return

    if clear:
        rmtree(lib_dir)
        ## FIXME: why not delete it?
        ## Maybe it should delete everything with #!/path/to/venv/python in it
        logger.notify('Not deleting %s', bin_dir)

    if hasattr(sys, 'real_prefix'):
        logger.notify('Using real prefix %r' % sys.real_prefix)
        prefix = sys.real_prefix
    else:
        prefix = sys.prefix
    mkdir(lib_dir)
    fix_lib64(lib_dir)
    fix_local_scheme(home_dir)
    stdlib_dirs = [os.path.dirname(os.__file__)]
    if sys.platform == 'win32':
        stdlib_dirs.append(join(os.path.dirname(stdlib_dirs[0]), 'DLLs'))
    elif sys.platform == 'darwin':
        stdlib_dirs.append(join(stdlib_dirs[0], 'site-packages'))
    if hasattr(os, 'symlink'):
        logger.info('Symlinking Python bootstrap modules')
    else:
        logger.info('Copying Python bootstrap modules')
    logger.indent += 2
    try:
        # copy required files...
        for stdlib_dir in stdlib_dirs:
            if not os.path.isdir(stdlib_dir):
                continue
            for fn in os.listdir(stdlib_dir):
                bn = os.path.splitext(fn)[0]
                if fn != 'site-packages' and bn in REQUIRED_FILES:
                    copyfile(join(stdlib_dir, fn), join(lib_dir, fn))
        # ...and modules
        copy_required_modules(home_dir)
    finally:
        logger.indent -= 2
    mkdir(join(lib_dir, 'site-packages'))
    import site
    site_filename = site.__file__
    if site_filename.endswith('.pyc'):
        site_filename = site_filename[:-1]
    elif site_filename.endswith('$py.class'):
        site_filename = site_filename.replace('$py.class', '.py')
    site_filename_dst = change_prefix(site_filename, home_dir)
    site_dir = os.path.dirname(site_filename_dst)
    writefile(site_filename_dst, SITE_PY)
    writefile(join(site_dir, 'orig-prefix.txt'), prefix)
    site_packages_filename = join(site_dir, 'no-global-site-packages.txt')
    if not site_packages:
        writefile(site_packages_filename, '')
    else:
        if os.path.exists(site_packages_filename):
            logger.info('Deleting %s' % site_packages_filename)
            os.unlink(site_packages_filename)

    if is_pypy or is_win:
        stdinc_dir = join(prefix, 'include')
    else:
        stdinc_dir = join(prefix, 'include', py_version + abiflags)
    if os.path.exists(stdinc_dir):
        copyfile(stdinc_dir, inc_dir)
    else:
        logger.debug('No include dir %s' % stdinc_dir)

    # pypy never uses exec_prefix, just ignore it
    if sys.exec_prefix != prefix and not is_pypy:
        if sys.platform == 'win32':
            exec_dir = join(sys.exec_prefix, 'lib')
        elif is_jython:
            exec_dir = join(sys.exec_prefix, 'Lib')
        else:
            exec_dir = join(sys.exec_prefix, 'lib', py_version)
        for fn in os.listdir(exec_dir):
            copyfile(join(exec_dir, fn), join(lib_dir, fn))

    if is_jython:
        # Jython has either jython-dev.jar and javalib/ dir, or just
        # jython.jar
        for name in 'jython-dev.jar', 'javalib', 'jython.jar':
            src = join(prefix, name)
            if os.path.exists(src):
                copyfile(src, join(home_dir, name))
        # XXX: registry should always exist after Jython 2.5rc1
        src = join(prefix, 'registry')
        if os.path.exists(src):
            copyfile(src, join(home_dir, 'registry'), symlink=False)
        copyfile(join(prefix, 'cachedir'), join(home_dir, 'cachedir'),
                 symlink=False)

    mkdir(bin_dir)
    py_executable = join(bin_dir, os.path.basename(sys.executable))
    if 'Python.framework' in prefix:
        if re.search(r'/Python(?:-32|-64)*$', py_executable):
            # The name of the python executable is not quite what
            # we want, rename it.
            py_executable = os.path.join(
                    os.path.dirname(py_executable), 'python')

    logger.notify('New %s executable in %s', expected_exe, py_executable)
    if sys.executable != py_executable:
        ## FIXME: could I just hard link?
        executable = sys.executable
        if sys.platform == 'cygwin' and os.path.exists(executable + '.exe'):
            # Cygwin misreports sys.executable sometimes
            executable += '.exe'
            py_executable += '.exe'
            logger.info('Executable actually exists in %s' % executable)
        shutil.copyfile(executable, py_executable)
        make_exe(py_executable)
        if sys.platform == 'win32' or sys.platform == 'cygwin':
            pythonw = os.path.join(os.path.dirname(sys.executable), 'pythonw.exe')
            if os.path.exists(pythonw):
                logger.info('Also created pythonw.exe')
                shutil.copyfile(pythonw, os.path.join(os.path.dirname(py_executable), 'pythonw.exe'))
        if is_pypy:
            # make a symlink python --> pypy-c
            python_executable = os.path.join(os.path.dirname(py_executable), 'python')
            logger.info('Also created executable %s' % python_executable)
            copyfile(py_executable, python_executable)

    if os.path.splitext(os.path.basename(py_executable))[0] != expected_exe:
        secondary_exe = os.path.join(os.path.dirname(py_executable),
                                     expected_exe)
        py_executable_ext = os.path.splitext(py_executable)[1]
        if py_executable_ext == '.exe':
            # python2.4 gives an extension of '.4' :P
            secondary_exe += py_executable_ext
        if os.path.exists(secondary_exe):
            logger.warn('Not overwriting existing %s script %s (you must use %s)'
                        % (expected_exe, secondary_exe, py_executable))
        else:
            logger.notify('Also creating executable in %s' % secondary_exe)
            shutil.copyfile(sys.executable, secondary_exe)
            make_exe(secondary_exe)

    if 'Python.framework' in prefix:
        logger.debug('MacOSX Python framework detected')

        # Make sure we use the the embedded interpreter inside
        # the framework, even if sys.executable points to
        # the stub executable in ${sys.prefix}/bin
        # See http://groups.google.com/group/python-virtualenv/
        #                              browse_thread/thread/17cab2f85da75951
        original_python = os.path.join(
            prefix, 'Resources/Python.app/Contents/MacOS/Python')
        shutil.copy(original_python, py_executable)

        # Copy the framework's dylib into the virtual
        # environment
        virtual_lib = os.path.join(home_dir, '.Python')

        if os.path.exists(virtual_lib):
            os.unlink(virtual_lib)
        copyfile(
            os.path.join(prefix, 'Python'),
            virtual_lib)

        # And then change the install_name of the copied python executable
        try:
            call_subprocess(
                ["install_name_tool", "-change",
                 os.path.join(prefix, 'Python'),
                 '@executable_path/../.Python',
                 py_executable])
        except:
            logger.fatal(
                "Could not call install_name_tool -- you must have Apple's development tools installed")
            raise

        # Some tools depend on pythonX.Y being present
        py_executable_version = '%s.%s' % (
            sys.version_info[0], sys.version_info[1])
        if not py_executable.endswith(py_executable_version):
            # symlinking pythonX.Y > python
            pth = py_executable + '%s.%s' % (
                    sys.version_info[0], sys.version_info[1])
            if os.path.exists(pth):
                os.unlink(pth)
            os.symlink('python', pth)
        else:
            # reverse symlinking python -> pythonX.Y (with --python)
            pth = join(bin_dir, 'python')
            if os.path.exists(pth):
                os.unlink(pth)
            os.symlink(os.path.basename(py_executable), pth)

    if sys.platform == 'win32' and ' ' in py_executable:
        # There's a bug with subprocess on Windows when using a first
        # argument that has a space in it.  Instead we have to quote
        # the value:
        py_executable = '"%s"' % py_executable
    cmd = [py_executable, '-c', """
import sys
prefix = sys.prefix
if sys.version_info[0] == 3:
    prefix = prefix.encode('utf8')
if hasattr(sys.stdout, 'detach'):
    sys.stdout = sys.stdout.detach()
elif hasattr(sys.stdout, 'buffer'):
    sys.stdout = sys.stdout.buffer
sys.stdout.write(prefix)
"""]
    logger.info('Testing executable with %s %s "%s"' % tuple(cmd))
    try:
        proc = subprocess.Popen(cmd,
                            stdout=subprocess.PIPE)
        proc_stdout, proc_stderr = proc.communicate()
    except OSError:
        e = sys.exc_info()[1]
        if e.errno == errno.EACCES:
            logger.fatal('ERROR: The executable %s could not be run: %s' % (py_executable, e))
            sys.exit(100)
        else:
          raise e

    proc_stdout = proc_stdout.strip().decode("utf-8")
    proc_stdout = os.path.normcase(os.path.abspath(proc_stdout))
    norm_home_dir = os.path.normcase(os.path.abspath(home_dir))
    if hasattr(norm_home_dir, 'decode'):
        norm_home_dir = norm_home_dir.decode(sys.getfilesystemencoding())
    if proc_stdout != norm_home_dir:
        logger.fatal(
            'ERROR: The executable %s is not functioning' % py_executable)
        logger.fatal(
            'ERROR: It thinks sys.prefix is %r (should be %r)'
            % (proc_stdout, norm_home_dir))
        logger.fatal(
            'ERROR: virtualenv is not compatible with this system or executable')
        if sys.platform == 'win32':
            logger.fatal(
                'Note: some Windows users have reported this error when they installed Python for "Only this user".  The problem may be resolvable if you install Python "For all users".  (See https://bugs.launchpad.net/virtualenv/+bug/352844)')
        sys.exit(100)
    else:
        logger.info('Got sys.prefix result: %r' % proc_stdout)

    pydistutils = os.path.expanduser('~/.pydistutils.cfg')
    if os.path.exists(pydistutils):
        logger.notify('Please make sure you remove any previous custom paths from '
                      'your %s file.' % pydistutils)
    ## FIXME: really this should be calculated earlier
    return py_executable

def install_activate(home_dir, bin_dir, prompt=None):
    if sys.platform == 'win32' or is_jython and os._name == 'nt':
        files = {'activate.bat': ACTIVATE_BAT,
                 'deactivate.bat': DEACTIVATE_BAT}
        if os.environ.get('OS') == 'Windows_NT' and os.environ.get('OSTYPE') == 'cygwin':
            files['activate'] = ACTIVATE_SH
    else:
        files = {'activate': ACTIVATE_SH}

        # suppling activate.fish in addition to, not instead of, the
        # bash script support.
        files['activate.fish'] = ACTIVATE_FISH

        # same for csh/tcsh support...
        files['activate.csh'] = ACTIVATE_CSH



    files['activate_this.py'] = ACTIVATE_THIS
    home_dir = os.path.abspath(home_dir)
    if hasattr(home_dir, 'decode'):
        home_dir = home_dir.decode(sys.getfilesystemencoding())
    vname = os.path.basename(home_dir)
    for name, content in files.items():
        content = content.replace('__VIRTUAL_PROMPT__', prompt or '')
        content = content.replace('__VIRTUAL_WINPROMPT__', prompt or '(%s)' % vname)
        content = content.replace('__VIRTUAL_ENV__', home_dir)
        content = content.replace('__VIRTUAL_NAME__', vname)
        content = content.replace('__BIN_NAME__', os.path.basename(bin_dir))
        writefile(os.path.join(bin_dir, name), content)

def install_distutils(home_dir):
    distutils_path = change_prefix(distutils.__path__[0], home_dir)
    mkdir(distutils_path)
    ## FIXME: maybe this prefix setting should only be put in place if
    ## there's a local distutils.cfg with a prefix setting?
    home_dir = os.path.abspath(home_dir)
    ## FIXME: this is breaking things, removing for now:
    #distutils_cfg = DISTUTILS_CFG + "\n[install]\nprefix=%s\n" % home_dir
    writefile(os.path.join(distutils_path, '__init__.py'), DISTUTILS_INIT)
    writefile(os.path.join(distutils_path, 'distutils.cfg'), DISTUTILS_CFG, overwrite=False)

def fix_local_scheme(home_dir):
    """
    Platforms that use the "posix_local" install scheme (like Ubuntu with
    Python 2.7) need to be given an additional "local" location, sigh.
    """
    try:
        import sysconfig
    except ImportError:
        pass
    else:
        if sysconfig._get_default_scheme() == 'posix_local':
            local_path = os.path.join(home_dir, 'local')
            if not os.path.exists(local_path):
                os.symlink(os.path.abspath(home_dir), local_path)

def fix_lib64(lib_dir):
    """
    Some platforms (particularly Gentoo on x64) put things in lib64/pythonX.Y
    instead of lib/pythonX.Y.  If this is such a platform we'll just create a
    symlink so lib64 points to lib
    """
    if [p for p in distutils.sysconfig.get_config_vars().values()
        if isinstance(p, basestring) and 'lib64' in p]:
        logger.debug('This system uses lib64; symlinking lib64 to lib')
        assert os.path.basename(lib_dir) == 'python%s' % sys.version[:3], (
            "Unexpected python lib dir: %r" % lib_dir)
        lib_parent = os.path.dirname(lib_dir)
        assert os.path.basename(lib_parent) == 'lib', (
            "Unexpected parent dir: %r" % lib_parent)
        copyfile(lib_parent, os.path.join(os.path.dirname(lib_parent), 'lib64'))

def resolve_interpreter(exe):
    """
    If the executable given isn't an absolute path, search $PATH for the interpreter
    """
    if os.path.abspath(exe) != exe:
        paths = os.environ.get('PATH', '').split(os.pathsep)
        for path in paths:
            if os.path.exists(os.path.join(path, exe)):
                exe = os.path.join(path, exe)
                break
    if not os.path.exists(exe):
        logger.fatal('The executable %s (from --python=%s) does not exist' % (exe, exe))
        raise SystemExit(3)
    if not is_executable(exe):
        logger.fatal('The executable %s (from --python=%s) is not executable' % (exe, exe))
        raise SystemExit(3)
    return exe

def is_executable(exe):
    """Checks a file is executable"""
    return os.access(exe, os.X_OK)

############################################################
## Relocating the environment:

def make_environment_relocatable(home_dir):
    """
    Makes the already-existing environment use relative paths, and takes out
    the #!-based environment selection in scripts.
    """
    home_dir, lib_dir, inc_dir, bin_dir = path_locations(home_dir)
    activate_this = os.path.join(bin_dir, 'activate_this.py')
    if not os.path.exists(activate_this):
        logger.fatal(
            'The environment doesn\'t have a file %s -- please re-run virtualenv '
            'on this environment to update it' % activate_this)
    fixup_scripts(home_dir)
    fixup_pth_and_egg_link(home_dir)
    ## FIXME: need to fix up distutils.cfg

OK_ABS_SCRIPTS = ['python', 'python%s' % sys.version[:3],
                  'activate', 'activate.bat', 'activate_this.py']

def fixup_scripts(home_dir):
    # This is what we expect at the top of scripts:
    shebang = '#!%s/bin/python' % os.path.normcase(os.path.abspath(home_dir))
    # This is what we'll put:
    new_shebang = '#!/usr/bin/env python%s' % sys.version[:3]
    activate = "import os; activate_this=os.path.join(os.path.dirname(__file__), 'activate_this.py'); execfile(activate_this, dict(__file__=activate_this)); del os, activate_this"
    if sys.platform == 'win32':
        bin_suffix = 'Scripts'
    else:
        bin_suffix = 'bin'
    bin_dir = os.path.join(home_dir, bin_suffix)
    home_dir, lib_dir, inc_dir, bin_dir = path_locations(home_dir)
    for filename in os.listdir(bin_dir):
        filename = os.path.join(bin_dir, filename)
        if not os.path.isfile(filename):
            # ignore subdirs, e.g. .svn ones.
            continue
        f = open(filename, 'rb')
        lines = f.readlines()
        f.close()
        if not lines:
            logger.warn('Script %s is an empty file' % filename)
            continue
        if not lines[0].strip().startswith(shebang):
            if os.path.basename(filename) in OK_ABS_SCRIPTS:
                logger.debug('Cannot make script %s relative' % filename)
            elif lines[0].strip() == new_shebang:
                logger.info('Script %s has already been made relative' % filename)
            else:
                logger.warn('Script %s cannot be made relative (it\'s not a normal script that starts with %s)'
                            % (filename, shebang))
            continue
        logger.notify('Making script %s relative' % filename)
        lines = [new_shebang+'\n', activate+'\n'] + lines[1:]
        f = open(filename, 'wb')
        f.writelines(lines)
        f.close()

def fixup_pth_and_egg_link(home_dir, sys_path=None):
    """Makes .pth and .egg-link files use relative paths"""
    home_dir = os.path.normcase(os.path.abspath(home_dir))
    if sys_path is None:
        sys_path = sys.path
    for path in sys_path:
        if not path:
            path = '.'
        if not os.path.isdir(path):
            continue
        path = os.path.normcase(os.path.abspath(path))
        if not path.startswith(home_dir):
            logger.debug('Skipping system (non-environment) directory %s' % path)
            continue
        for filename in os.listdir(path):
            filename = os.path.join(path, filename)
            if filename.endswith('.pth'):
                if not os.access(filename, os.W_OK):
                    logger.warn('Cannot write .pth file %s, skipping' % filename)
                else:
                    fixup_pth_file(filename)
            if filename.endswith('.egg-link'):
                if not os.access(filename, os.W_OK):
                    logger.warn('Cannot write .egg-link file %s, skipping' % filename)
                else:
                    fixup_egg_link(filename)

def fixup_pth_file(filename):
    lines = []
    prev_lines = []
    f = open(filename)
    prev_lines = f.readlines()
    f.close()
    for line in prev_lines:
        line = line.strip()
        if (not line or line.startswith('#') or line.startswith('import ')
            or os.path.abspath(line) != line):
            lines.append(line)
        else:
            new_value = make_relative_path(filename, line)
            if line != new_value:
                logger.debug('Rewriting path %s as %s (in %s)' % (line, new_value, filename))
            lines.append(new_value)
    if lines == prev_lines:
        logger.info('No changes to .pth file %s' % filename)
        return
    logger.notify('Making paths in .pth file %s relative' % filename)
    f = open(filename, 'w')
    f.write('\n'.join(lines) + '\n')
    f.close()

def fixup_egg_link(filename):
    f = open(filename)
    link = f.read().strip()
    f.close()
    if os.path.abspath(link) != link:
        logger.debug('Link in %s already relative' % filename)
        return
    new_link = make_relative_path(filename, link)
    logger.notify('Rewriting link %s in %s as %s' % (link, filename, new_link))
    f = open(filename, 'w')
    f.write(new_link)
    f.close()

def make_relative_path(source, dest, dest_is_directory=True):
    """
    Make a filename relative, where the filename is dest, and it is
    being referred to from the filename source.

        >>> make_relative_path('/usr/share/something/a-file.pth',
        ...                    '/usr/share/another-place/src/Directory')
        '../another-place/src/Directory'
        >>> make_relative_path('/usr/share/something/a-file.pth',
        ...                    '/home/user/src/Directory')
        '../../../home/user/src/Directory'
        >>> make_relative_path('/usr/share/a-file.pth', '/usr/share/')
        './'
    """
    source = os.path.dirname(source)
    if not dest_is_directory:
        dest_filename = os.path.basename(dest)
        dest = os.path.dirname(dest)
    dest = os.path.normpath(os.path.abspath(dest))
    source = os.path.normpath(os.path.abspath(source))
    dest_parts = dest.strip(os.path.sep).split(os.path.sep)
    source_parts = source.strip(os.path.sep).split(os.path.sep)
    while dest_parts and source_parts and dest_parts[0] == source_parts[0]:
        dest_parts.pop(0)
        source_parts.pop(0)
    full_parts = ['..']*len(source_parts) + dest_parts
    if not dest_is_directory:
        full_parts.append(dest_filename)
    if not full_parts:
        # Special case for the current directory (otherwise it'd be '')
        return './'
    return os.path.sep.join(full_parts)



############################################################
## Bootstrap script creation:

def create_bootstrap_script(extra_text, python_version=''):
    """
    Creates a bootstrap script, which is like this script but with
    extend_parser, adjust_options, and after_install hooks.

    This returns a string that (written to disk of course) can be used
    as a bootstrap script with your own customizations.  The script
    will be the standard virtualenv.py script, with your extra text
    added (your extra text should be Python code).

    If you include these functions, they will be called:

    ``extend_parser(optparse_parser)``:
        You can add or remove options from the parser here.

    ``adjust_options(options, args)``:
        You can change options here, or change the args (if you accept
        different kinds of arguments, be sure you modify ``args`` so it is
        only ``[DEST_DIR]``).

    ``after_install(options, home_dir)``:

        After everything is installed, this function is called.  This
        is probably the function you are most likely to use.  An
        example would be::

            def after_install(options, home_dir):
                subprocess.call([join(home_dir, 'bin', 'easy_install'),
                                 'MyPackage'])
                subprocess.call([join(home_dir, 'bin', 'my-package-script'),
                                 'setup', home_dir])

        This example immediately installs a package, and runs a setup
        script from that package.

    If you provide something like ``python_version='2.4'`` then the
    script will start with ``#!/usr/bin/env python2.4`` instead of
    ``#!/usr/bin/env python``.  You can use this when the script must
    be run with a particular Python version.
    """
    filename = __file__
    if filename.endswith('.pyc'):
        filename = filename[:-1]
    f = open(filename, 'rb')
    content = f.read()
    f.close()
    py_exe = 'python%s' % python_version
    content = (('#!/usr/bin/env %s\n' % py_exe)
               + '## WARNING: This file is generated\n'
               + content)
    return content.replace('##EXT' 'END##', extra_text)

##EXTEND##

def convert(s):
    b = base64.b64decode(s.encode('ascii'))
    return zlib.decompress(b).decode('utf-8')

##file site.py
SITE_PY = convert("""
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
""")

##file ez_setup.py
EZ_SETUP_PY = convert("""
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
BDaonX65d/fwEjNqlDjLVIvM9X+XVxF7
""")

##file distribute_setup.py
DISTRIBUTE_SETUP_PY = convert("""
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
""")

##file activate.sh
ACTIVATE_SH = convert("""
eJytVU1v4jAQPW9+xTT0ANVS1GsrDlRFAqmFqmG72m0rY5IJsRRslDiktNr/vuMQ8tFQpNU2B4I9
H36eeW/SglkgYvBFiLBKYg0LhCRGD1KhA7BjlUQuwkLIHne12HCNNpz5kVrBgsfBmdWCrUrA5VIq
DVEiQWjwRISuDreW5eE+CtodeLeAnhZEGKMGFXqAciMiJVcoNWx4JPgixDjzEj48QVeCfcqmtzfs
cfww+zG4ZfeD2ciGF7gCHaDMPM1jtvuHXAsPfF2rSGeOxV4iDY5GUGb3xVEYv2aj6WQ0vRseAlMY
G5DKsAawwnQUXt2LQOYlzZoYByqhonqoqfxZf4BLD97i4DukgXADCPgGgdOLTK5arYxZB1xnrc9T
EQFcHoZEAa1gSQioo/TPV5FZrDlxJA+NzwF+Ek1UonOzFnKZp6k5mgLBqSkuuAGXS4whJb5xz/xs
wXCHjiVerAk5eh9Kfz1wqOldtVv9dkbscfjgjKeTA8XPrtaNauX5rInOxaHuOReNtpFjo1/OxdFG
5eY9hJ3L3jqcPJbATggXAemDLZX0MNZRYjSDH7C1wMHQh73DyYfTu8a0F9v+6D8W6XNnF1GEIXW/
JrSKPOtnW1YFat9mrLJkzLbyIlTvYzV0RGXcaTBfVLx7jF2PJ2wyuBsydpm7VSVa4C4Zb6pFO2TR
huypCEPwuQjNftUrNl6GsYZzuFrrLdC9iJjQ3omAPBbcI2lsU77tUD43kw1NPZhTrnZWzuQKLomx
Rd4OXM1ByExVVkmoTwfBJ7Lt10Iq1Kgo23Bmd8Ib1KrGbsbO4Pp2yO4fpnf3s6MnZiwuiJuls1/L
Pu4yUCvhpA+vZaJvWWDTr0yFYYyVnHMqCEq+QniuYX225xmnzRENjbXACF3wkCYNVZ1mBwxoR9Iw
WAo3/36oSOTfgjwEEQKt15e9Xpqm52+oaXxszmnE9GLl65RH2OMmS6+u5acKxDmlPgj2eT5/gQOX
LLK0j1y0Uwbmn438VZkVpqlfNKa/YET/53j+99G8H8tUhr9ZSXs2
""")

##file activate.fish
ACTIVATE_FISH = convert("""
eJydVm1v4jgQ/s6vmA1wBxUE7X2stJVYlVWR2lK13d6d9laRk0yIr8HmbIe0++tvnIQQB9pbXT5A
Ys/LM55nZtyHx5RrSHiGsMm1gRAh1xhDwU0Kng8hFzMWGb5jBv2E69SDs0TJDdj3MxilxmzPZzP7
pVPMMl+q9bjXh1eZQ8SEkAZULoAbiLnCyGSvvV6SC7IoBcS4Nw0wjcFbvJDcjiuTswzFDpiIQaHJ
lQAjQUi1YRmUboC2uZJig8J4PaCnT5IaDcgsbm/CjinOwgx1KcUTMEhhTgV4g2B1fRk8Le8fv86v
g7v545UHpZB9rKnp+gXsMhxLunIIpwVQxP/l9c/Hq9Xt1epm4R27bva6AJqN92G4YhbMG2i+LB+u
grv71c3dY7B6WtzfLy9bePbp0taDTXSwJQJszUnnp0y57mvpPcrF7ZODyhswtd59+/jdgw+fwBNS
xLSscksUPIDqwwNmCez3PpxGeyBYg6HE0YdcWBxcKczYzuVJi5Wu915vn5oWePCCoPUZBN5B7IgV
MCi54ZDLG7TUZ0HweXkb3M5vFmSpFm/gthhBx0UrveoPpv9AJ9unIbQYdUoe21bKg2q48sPFGVwu
H+afrxd1qvclaNlRFyh1EQ2sSccEuNAGWQwysfVpz1tPajUqbqJUnEcIJkWo6OXDaodK8ZiLdbmM
L1wb+9H0D+pcyPSrX5u5kgWSygRYXCnJUi/KKcuU4cqsAyTKZBiissLc7NFwizvjxtieKBVCIdWz
fzilzPaYyljZN0cGN1v7NnaIPNCGmVy3GKuJaQ6iVjE1Qfm+36hglErwmnAD8hu0dDy4uICBA8ZV
pQr/q/+O0KFW2kjelu9Dgb9SDBsWV4F4x5CswgS0zBVlk5tDMP5bVtUGpslbm81Lu2sdKq7uNMGh
MVQ4fy9xhogC1lS5guhISa0DlBWv0O8odT6/LP+4WZzDV6FzIkEqC0uolGZSZoMnlpxplmD2euaT
O4hkTpPnbztDccey0bhjDaBIqaWQa0uwEtQEwtyU56i4fq54F9IE3ORR6mKriODM4XOYZwaVYLYz
7SPbKkz4i7VkB6/Ot1upDE3znNqYKpM8raa0Bx8vfvntJ32UENsM4aI6gJL+jJwhxhh3jVIDOcpi
m0r2hmEtS8XXXNBk71QCDXTBNhhPiHX2LtHkrVIlhoEshH/EZgdq53Eirqs5iFKMnkOmqZTtr3Xq
djvPTWZT4S3NT5aVLgurMPUWI07BRVYqkQrmtCKohNY8qu9EdACoT6ki0a66XxVF4f9AQ3W38yO5
mWmZmIIpnDFrbXakvKWeZhLwhvrbUH8fahhqD0YUcBDJjEBMQwiznE4y5QbHrbhHBOnUAYzb2tVN
jJa65e+eE2Ya30E2GurxUP8ssA6e/wOnvo3V78d3vTcvMB3n7l3iX1JXWqk=
""")

##file activate.csh
ACTIVATE_CSH = convert("""
eJx9U11vmzAUffevOCVRu+UB9pws29Kl0iq1aVWllaZlcgxciiViItsQdb9+xiQp+dh4QOB7Pu49
XHqY59IgkwVhVRmLmFAZSrGRNkdgykonhFiqSCRW1sJSmJg8wCDT5QrucRCyHn6WFRKhVGmhKwVp
kUpNiS3emup3TY6XIn7DVNQyJUwlrgthJD6n/iCNv72uhCzCpFx9CRkThRQGKe08cWXJ9db/yh/u
pvzl9mn+PLnjj5P5D1yM8QmXlzBkSdXwZ0H/BBc0mEo5FE5qI2jKhclHOOvy9HD/OO/6YO1mX9vx
sY0H/tPIV0dtqel0V7iZvWyNg8XFcBA0ToEqVeqOdNUEQFvN41SumAv32VtJrakQNSmLWmgp4oJM
yDoBHgoydtoEAs47r5wHHnUal5vbJ8oOI+9wI86vb2d8Nrm/4Xy4RZ8R85E4uTZPB5EZPnTaaAGu
E59J8BE2J8XgrkbLeXMlVoQxznEYFYY8uFFdxsKQRx90Giwx9vSueHP1YNaUSFG4vTaErNSYuBOF
lXiVyXa9Sy3JdClEyK1dD6Nos9mEf8iKlOpmqSNTZnYjNEWiUYn2pKNB3ttcLJ3HmYYXy6Un76f7
r8rRsC1TpTJj7f19m5sUf/V3Ir+x/yjtLu8KjLX/CmN/AcVGUUo=
""")

##file activate.bat
ACTIVATE_BAT = convert("""
eJyFUkEKgzAQvAfyhz0YaL9QEWpRqlSjWGspFPZQTevFHOr/adQaU1GaUzI7Mzu7ZF89XhKkEJS8
qxaKMMsvboQ+LxxE44VICSW1gEa2UFaibqoS0iyJ0xw2lIA6nX5AHCu1jpRsv5KRjknkac9VLVug
sX9mtzxIeJDE/mg4OGp47qoLo3NHX2jsMB3AiDht5hryAUOEifoTdCXbSh7V0My2NMq/Xbh5MEjU
ZT63gpgNT9lKOJ/CtHsvT99re3pX303kydn4HeyOeAg5cjf2EW1D6HOPkg9NGKhu
""")

##file deactivate.bat
DEACTIVATE_BAT = convert("""
eJxzSE3OyFfIT0vj4spMU0hJTcvMS01RiPf3cYkP8wwKCXX0iQ8I8vcNCFHQ4FIAguLUEgWIgK0q
FlWqXJpcICVYpGzx2BAZ4uHv5+Hv6wq1BWINXBTdKriEKkI1DhW2QAfhttcxxANiFZCBbglQSJUL
i2dASrm4rFz9XLgAwJNbyQ==
""")

##file distutils-init.py
DISTUTILS_INIT = convert("""
eJytV92L4zYQf/dfMU0ottuse7RvC6FQrg8Lxz2Ugz4si9HacqKuIxlJ2ST313dG8odkO9d7aGBB
luZLv/nNjFacOqUtKJMIvzK3cXlhWgp5MDBsqK5SNYftsBAGpLLA4F1oe2Ytl+9wUvW55TswCi4c
KibhbFDSglXQCFmDPXIwtm7FawLRbwtPzg2T9gf4gupKv4GS0N262w7V0NvpbCy8cvTo3eAus6C5
ETU3ICQZX1hFTw/dzR6V/AW1RCN4/XAtbsVXqIXmlVX6liS4lOzEYY9QFB2zx6LfoSNjz1a0pqT9
QOIfJWQ2E888NEVZNqLlZZnvIB0NpHkimlFdKn2iRRY7yGG/CCJb6Iz280d34SFXBS2yEYPNF0Q7
yM7oCjpWvbEDQmnhRwOs6zjThpKE8HogwRAgraqYFZgGZvzmzVh+mgz9vskT3hruwyjdFcqyENJw
bbMPO5jdzonxK68QKT7B57CMRRG5shRSWDTX3dI8LzRndZbnSWL1zfvriUmK4TcGWSnZiEPCrxXv
bM+sP7VW2is2WgWXCO3sAu3Rzysz3FiNCA8WPyM4gb1JAAmCiyTZbhFjWx3h9SzauuRXC9MFoVbc
yNTCm1QXOOIfIn/g1kGMhDUBN72hI5XCBQtIXQw8UEEdma6Jaz4vJIJ51Orc15hzzmu6TdFp3ogr
Aof0c98tsw1SiaiWotHffk3XYCkqdToxWRfTFXqgpg2khcLluOHMVC0zZhLKIomesfSreUNNgbXi
Ky9VRzwzkBneNoGQyyvGjbsFQqOZvpWIjqH281lJ/jireFgR3cPzSyTGWzQpDNIU+03Fs4XKLkhp
/n0uFnuF6VphB44b3uWRneSbBoMSioqE8oeF0JY+qTvYfEK+bPLYdoR4McfYQ7wMZj39q0kfP8q+
FfsymO0GzNlPh644Jje06ulqHpOEQqdJUfoidI2O4CWx4qOglLye6RrFQirpCRXvhoRqXH3sYdVJ
AItvc+VUsLO2v2hVAWrNIfVGtkG351cUMNncbh/WdowtSPtCdkzYFv6mwYc9o2Jt68ud6wectBr8
hYAulPSlgzH44YbV3ikjrulEaNJxt+/H3wZ7bXSXje/YY4tfVVrVmUstaDwwOBLMg6iduDB0lMVC
UyzYx7Ab4kjCqdViEJmDcdk/SKbgsjYXgfMznUWcrtS4z4fmJ/XOM1LPk/iIpqass5XwNbdnLb1Y
8h3ERXSWZI6rZJxKs1LBqVH65w0Oy4ra0CBYxEeuOMbDmV5GI6E0Ha/wgVTtkX0+OXvqsD02CKLf
XHbeft85D7tTCMYy2Njp4DJP7gWJr6paVWXZ1+/6YXLv/iE0M90FktiI7yFJD9e7SOLhEkkaMTUO
azq9i2woBNR0/0eoF1HFMf0H8ChxH/jgcB34GZIz3Qn4/vid+VEamQrOVqAPTrOfmD4MPdVh09tb
8dLLjvh/61lEP4yW5vJaH4vHcevG8agXvzPGoOhhXNncpTr99PTHx6e/UvffFLaxUSjuSeP286Dw
gtEMcW1xKr/he4/6IQ6FUXP+0gkioHY5iwC9Eyx3HKO7af0zPPe+XyLn7fAY78k4aiR387bCr5XT
5C4rFgwLGfMvJuAMew==
""")

##file distutils.cfg
DISTUTILS_CFG = convert("""
eJxNj00KwkAMhfc9xYNuxe4Ft57AjYiUtDO1wXSmNJnK3N5pdSEEAu8nH6lxHVlRhtDHMPATA4uH
xJ4EFmGbvfJiicSHFRzUSISMY6hq3GLCRLnIvSTnEefN0FIjw5tF0Hkk9Q5dRunBsVoyFi24aaLg
9FDOlL0FPGluf4QjcInLlxd6f6rqkgPu/5nHLg0cXCscXoozRrP51DRT3j9QNl99AP53T2Q=
""")

##file activate_this.py
ACTIVATE_THIS = convert("""
eJyNUlGL2zAMfvevEBlHEujSsXsL9GGDvW1jD3sZpQQ3Ua7aJXawnbT595Ocpe0dO5ghseVP+vRJ
VpIkn2cYPZknwAvWLXWYhRP5Sk4baKgOWRWNqtpdgTyH2Y5wpq5Tug406YAgKEzkwqg7NBPwR86a
Hk0olPopaK0NHJHzYQPnE5rI0o8+yBUwiBfyQcT8mMPJGiAT0A0O+b8BY4MKJ7zPcSSzHaKrSpJE
qeDmUgGvVbPCS41DgO+6xy/OWbfAThMn/OQ9ukDWRCSLiKzk1yrLjWapq6NnvHUoHXQ4bYPdrsVX
4lQMc/q6ZW975nmSK+oH6wL42a9H65U6aha342Mh0UVDzrD87C1bH73s16R5zsStkBZDp0NrXQ+7
HaRnMo8f06UBnljKoOtn/YT+LtdvSyaT/BtIv9KR60nF9f3qmuYKO4//T9ItJMsjPfgUHqKwCZ3n
xu/Lx8M/UvCLTxW7VULHxB1PRRbrYfvWNY5S8it008jOjcleaMqVBDnUXcWULV2YK9JEQ92OfC96
1Tv4ZicZZZ7GpuEpZbbeQ7DxquVx5hdqoyFSSmXwfC90f1Dc7hjFs/tK99I0fpkI8zSLy4tSy+sI
3vMWehjQNJmE5VePlZbL61nzX3S93ZcfDqznnkb9AZ3GWJU=
""")

if __name__ == '__main__':
    main()

## TODO:
## Copy python.exe.manifest
## Monkeypatch distutils.sysconfig

########NEW FILE########
__FILENAME__ = test_examples
# Imports
import pyutilib.th as unittest
import glob
import os
from os.path import dirname, abspath, basename
import sys
import re

currdir = dirname(abspath(__file__))+os.sep
datadir = currdir

compilerre = re.compile("^(?P<path>[^:]+)(?P<rest>:.*)$")
dirre      = re.compile("^([^%s]*/)*" % re.escape(os.sep))
xmlre      = re.compile("\"(?P<path>[^\"]*/[^\"]*)\"")
datere     = re.compile("date=\"[^\"]*\"")
versionre  = re.compile("version=\"[^\"]*\"")
timestampre = re.compile("timestamp=\"[^\"]*\"")
failure    = re.compile("^(?P<prefix>.+)file=\"(?P<path>[^\"]+)\"(?P<suffix>.*)$")

def filter(line):
    # for xml, remove prefixes from everything that looks like a 
    # file path inside ""
    line = xmlre.sub(
            lambda match: '"'+re.sub("^[^/]+/", "", match.group(1))+'"',
            line
            )
    # Remove date info
    line = datere.sub( lambda match: 'date=""', line)
    # Remove version info
    line = versionre.sub( lambda match: 'version=""', line)
    # Remove timestamp info
    line = timestampre.sub( lambda match: 'timestamp=""', line)

    if 'Running' in line:
        return False
    if "IGNORE" in line:
        return True
    pathmatch = compilerre.match(line) # see if we can remove the basedir
    failmatch = failure.match(line) # see if we can remove the basedir
    #print "HERE", pathmatch, failmatch
    if failmatch:
        parts = failmatch.groupdict()
        #print "X", parts
        line = "%s file=\"%s\" %s" % (parts['prefix'], dirre.sub("", parts['path']), parts['suffix'])
    elif pathmatch:
        parts = pathmatch.groupdict()
        #print "Y", parts
        line = dirre.sub("", parts['path']) + parts['rest']
    return line

# Declare an empty TestCase class
class Test(unittest.TestCase): pass

if not sys.platform.startswith('win'):
    # Find all *.sh files, and use them to define baseline tests
    for file in glob.glob(datadir+'*.sh'):
        bname = basename(file)
        name=bname.split('.')[0]
        if os.path.exists(datadir+name+'.txt'):
            Test.add_baseline_test(cwd=datadir, cmd=file, baseline=datadir+name+'.txt', name=name, filter=filter)

# Execute the tests
if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = include_anchors
import re
import sys
import os.path
import os


pat1a = re.compile('include::([a-zA-Z0-9_\.\-/\/]+\/)\.([^\_]+)\_[a-zA-Z0-9]*\.py\[\]')
pat1b = re.compile('include::([a-zA-Z0-9_\.\-/\/]+\/)\.([^\_]+)\_[a-zA-Z0-9]*\.sh\[\]')
pat1c = re.compile('include::([a-zA-Z0-9_\.\-/\/]+\/)\.([^\_]+)\_[a-zA-Z0-9]*\.h\[\]')
pat1d = re.compile('include::([a-zA-Z0-9_\.\-/\/]+\/)\.([^\_]+)\_[a-zA-Z0-9]*\.cpp\[\]')
pat2 = re.compile('([^@]+)@([a-zA-Z0-9]+):')
pat3 = re.compile('([^@]+)@:([a-zA-Z0-9]+)')

processed = set()

def process(dir, root, suffix):
    #print "PROCESS ",root, suffix
    bname = "%s%s" % (dir, root)
    global processed
    if bname in processed:
        return
    #
    anchors = {}
    anchors[''] = open('%s.%s_.%s' % (dir, root, suffix), 'w')
    INPUT = open('%s%s.%s' % (dir, root, suffix), 'r')
    for line in INPUT:
        m2 = pat2.match(line)
        m3 = pat3.match(line)
        if m2:
            anchor = m2.group(2)
            anchors[anchor] = open('%s.%s_%s.%s' % (dir, root, anchor, suffix), 'w')
        elif m3:
            anchor = m3.group(2)
            anchors[anchor].close()
            del anchors[anchor]
        else:
            for anchor in anchors:
                os.write(anchors[anchor].fileno(), line)
    INPUT.close()
    for anchor in anchors:
        if anchor != '':
            print "ERROR: anchor '%s' did not terminate" % anchor
        anchors[anchor].close()
    #
    processed.add(bname)


for file in sys.argv[1:]:
    print "Processing file '%s' ..." % file
    INPUT = open(file, 'r')
    for line in INPUT:
        suffix = None
        m = pat1a.match(line)
        if m:
            suffix = 'py'
        #
        if suffix is None:
            m = pat1b.match(line)
            if m:
                suffix = 'sh'
        #
        if suffix is None:
            m = pat1c.match(line)
            if m:
                suffix = 'h'
        #
        if suffix is None:
            m = pat1d.match(line)
            if m:
                suffix = 'cpp'
        #
        if not suffix is None:
            #print "HERE", line, suffix
            fname = m.group(1)+m.group(2)+'.'+suffix
            if not os.path.exists(fname):
                print line
                print "ERROR: file '%s' does not exist!" % fname
                sys.exit(1)
            process(m.group(1), m.group(2), suffix)
    INPUT.close()


########NEW FILE########
__FILENAME__ = test_gcovr
#!/usr/bin/env python
import os
import os.path
import re
import sys
import subprocess
import traceback
import pyutilib.th as unittest

basedir = os.path.split(os.path.abspath(__file__))[0]
starting_dir = os.getcwd()

class GcovrTxt(unittest.TestCase):
    def __init__(self, *args, **kwds):
        unittest.TestCase.__init__(self, *args, **kwds)

GcovrTxt = unittest.category('smoke')(GcovrTxt)


class GcovrXml(unittest.TestCase):
    def __init__(self, *args, **kwds):
        unittest.TestCase.__init__(self, *args, **kwds)
        self.xml_re = re.compile('((timestamp)|(version))="[^"]*"')

    def compare_xml(self):
        F = open("coverage.xml")
        testData = self.xml_re.sub('\\1=""',F.read()).replace("\r","")
        F.close()
        F = open('coverage.xml', 'w')
        F.write(testData)
        F.close()
        F = open("reference/coverage.xml")
        refData = self.xml_re.sub('\\1=""',F.read()).replace("\r","")
        F.close()
        F = open('reference/coverage.xml', 'w')
        F.write(refData)
        F.close()
        #self.assertSequenceEqual(testData.split('\n'), refData.split('\n'))
        self.assertMatchesXmlBaseline('coverage.xml', os.path.join('reference','coverage.xml'), tolerance=1e-4)

GcovrXml = unittest.category('smoke')(GcovrXml)


class GcovrHtml(unittest.TestCase):
    def __init__(self, *args, **kwds):
        unittest.TestCase.__init__(self, *args, **kwds)
        self.xml_re = re.compile('((timestamp)|(version))="[^"]*"')

    def compare_html(self):
        F = open("coverage.html")
        testData = self.xml_re.sub('\\1=""',F.read()).replace("\r","")
        F.close()
        F = open('coverage.html', 'w')
        F.write(testData)
        F.close()
        F = open("reference/coverage.html")
        refData = self.xml_re.sub('\\1=""',F.read()).replace("\r","")
        F.close()
        F = open('reference/coverage.html', 'w')
        F.write(refData)
        F.close()
        #self.assertSequenceEqual(testData.split('\n'), refData.split('\n'))
        self.assertMatchesXmlBaseline('coverage.html', os.path.join('reference','coverage.html'), tolerance=1e-4)

GcovrHtml = unittest.category('smoke')(GcovrHtml)


def run(cmd):
    try:
        proc = subprocess.Popen( cmd,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT,
                                 env=os.environ )
        print("STDOUT - START")
        sys.stdout.write("%s"%proc.communicate()[0])
        print("STDOUT - END")
        return not proc.returncode
    except Exception:
        e = sys.exc_info()[1]
        sys.stdout.write("Caught unexpected exception in test driver: %s\n%s"
                         % ( str(e), traceback.format_exc() ))
        raise
    

    

@unittest.nottest
def gcovr_test_txt(self, name):
    os.chdir(os.path.join(basedir,name))
    run(["make","clean"]) or self.fail("Clean failed")
    run(["make"]) or self.fail("Make failed")
    run(["make","txt"]) or self.fail("Execution failed")
    self.assertFileEqualsBaseline("coverage.txt", "reference/coverage.txt")
    run(["make","clean"]) or self.fail("Clean failed")
    os.chdir(basedir)

@unittest.nottest
def gcovr_test_xml(self, name):
    os.chdir(os.path.join(basedir,name))
    run(["make","clean"]) or self.fail("Clean failed")
    run(["make"]) or self.fail("Make failed")
    run(["make","xml"]) or self.fail("Execution failed")
    self.compare_xml()
    run(["make","clean"]) or self.fail("Clean failed")
    os.chdir(basedir)

@unittest.nottest
def gcovr_test_html(self, name):
    os.chdir(os.path.join(basedir,name))
    run(["make"]) or self.fail("Make failed")
    run(["make","html"]) or self.fail("Execution failed")
    self.compare_html()
    run(["make","clean"]) or self.fail("Clean failed")
    os.chdir(basedir)

skip_dirs = [ '.', '..', '.svn' ]

for f in os.listdir(basedir):
    if os.path.isdir(os.path.join(basedir,f)) and f not in skip_dirs:
        if 'pycache' in f:
            continue
        GcovrTxt.add_fn_test(fn=gcovr_test_txt, name=f)
        GcovrXml.add_fn_test(fn=gcovr_test_xml, name=f)
        #GcovrHtml.add_fn_test(fn=gcovr_test_html, name=f)
	
if __name__ == "__main__":
    unittest.main()

########NEW FILE########
