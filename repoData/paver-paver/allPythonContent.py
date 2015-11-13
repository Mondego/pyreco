__FILENAME__ = bootstrap
#!/usr/bin/env python
## WARNING: This file is generated
#!/usr/bin/env python
"""Create a "virtual" Python installation
"""

# If you change the version here, change it in setup.py
# and docs/conf.py as well.
__version__ = "1.8.2"  # following best practices
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
        if files and os.path.exists(files[0]):
            return files[0]
    return filename

def _install_req(py_executable, unzip=False, distribute=False,
                 search_dirs=None, never_download=False):

    if search_dirs is None:
        search_dirs = file_search_dirs()

    if not distribute:
        setup_fn = 'setuptools-*-py%s.egg' % sys.version[:3]
        project_name = 'setuptools'
        bootstrap_script = EZ_SETUP_PY
        source = None
    else:
        setup_fn = None
        source = 'distribute-*.tar.gz'
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
    remove_from_env = ['__PYVENV_LAUNCHER__']
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

    if use_distribute:
        install_distribute(py_executable, unzip=unzip_setuptools,
                           search_dirs=search_dirs, never_download=never_download)
    else:
        install_setuptools(py_executable, unzip=unzip_setuptools,
                           search_dirs=search_dirs, never_download=never_download)

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
    prefixes = list(map(os.path.expanduser, prefixes))
    prefixes = list(map(os.path.abspath, prefixes))
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
                dst_filename = change_prefix(filename, dst_prefix)
                copyfile(filename, dst_filename)
                if filename.endswith('.pyc'):
                    pyfile = filename[:-1]
                    if os.path.exists(pyfile):
                        copyfile(pyfile, dst_filename[:-1])
    finally:
        sys.path = _prev_sys_path

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
        if is_cygwin and os.path.exists(executable + '.exe'):
            # Cygwin misreports sys.executable sometimes
            executable += '.exe'
            py_executable += '.exe'
            logger.info('Executable actually exists in %s' % executable)
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
        assert os.path.basename(lib_parent) == 'lib', (
            "Unexpected parent dir: %r" % lib_parent)
        os.symlink(os.path.join('.', os.path.basename(lib_parent)),
                   os.path.join(os.path.dirname(lib_parent), 'lib64'))

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

    If you provide something like ``python_version='2.4'`` then the
    script will start with ``#!/usr/bin/env python2.4`` instead of
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

def adjust_options(options, args):
    args[:] = ['virtualenv']


def after_install(options, home_dir):
    if sys.platform == 'win32':
        bin_dir = join(home_dir, 'Scripts')
    else:
        bin_dir = join(home_dir, 'bin')
    subprocess.call([join(bin_dir, 'easy_install'), 'nose'])
    subprocess.call([join(bin_dir, 'easy_install'), 'Sphinx>=0.6b1'])
    subprocess.call([join(bin_dir, 'easy_install'), 'docutils'])
    subprocess.call([join(bin_dir, 'easy_install'), 'virtualenv'])
    subprocess.call([join(bin_dir, 'python'), '-c', 'import sys; sys.path.append("."); import paver.command; paver.command.main()', 'develop'])

def convert(s):
    b = base64.b64decode(s.encode('ascii'))
    return zlib.decompress(b).decode('utf-8')

##file site.py
SITE_PY = convert("""
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
YAowyJmdag/AGoXg/wBaZusT
""")

##file ez_setup.py
EZ_SETUP_PY = convert("""
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
BDaonX65d/fwEjNqlDjLVIvM9X+XVxF7
""")

##file distribute_setup.py
DISTRIBUTE_SETUP_PY = convert("""
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
9g==
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
eJx9U11v2jAUffevOA2o3ZBG9gxjGx2VVqmlVUUrTWMyTnLTWEocZDsg+uvnOEDDx5aHKLn3fFyf
3HQwy6RBKnNCURmLiFAZSrCWNkNgykrHhEiqUMRWroSlfmyyAL1UlwXcY6/POvhVVoiFUqWFrhSk
RSI1xTbf1N0fmhwvQbTBRKxkQphIXOfCSHxJfCGJvr8WQub9uCy+9hkTuRQGCe08cWXJzdb9xh/u
Jvzl9mn2PL7jj+PZT1yM8BmXlzBkSa3ga0H3BBfUmEo5FE56Q2jKhMmGOOvy9HD/OGv7YOnOvrSj
YxsP/KeR7w6bVj3prnEzfdkaB/OLQS+onQJVqsSVdFUHQFvNk1Ra1eUmKeMr5tJ+9t5Sa8ppJZTF
SmgpopxMn7W4hw6MnU6FgPPWK+eBR53m54LwEbPDb9Dihpxf3075dHx/w/lgiz4j5jNyck3ADiJT
fGiN0QDcJD6k4CNsRorBXbWW8+ZKFIQRznEY5YY8uFZdRMKQRx9MGiww8vS2eH11YJYUS5G7RTeE
tNQYu4pCIV5lvN33UksybQoRMmuXgzBcr9f9N7IioVW95aEpU7sWmkJRq4R70tFB3secL5zHmYHn
i4Un70/3X5WjwzZMlciUNff39a5T/N3difzB/qM0y71r7H5Wv4DubrNS4VPRvDPW/FmM/QUd8WEa
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

##file activate.ps1
ACTIVATE_PS = convert("""
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
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
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# The Old Way documentation build configuration file, created by
# sphinx-quickstart on Sun May  4 14:02:06 2008.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# The contents of this file are pickled, so don't put values in the namespace
# that aren't pickleable (module imports are okay, they're removed automatically).
#
# All configuration values have a default value; values that are commented out
# serve to show the default value.

import sys, os

# If your extensions are in another directory, add it here. If the directory
# is relative to the documentation root, use os.path.abspath to make it
# absolute, like shown here.
#sys.path.append(os.path.abspath('some/directory'))

# General configuration
# ---------------------

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
#extensions = []

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

# General substitutions.
project = 'The New Way'
copyright = '2008, Kevin Dangoor'

# The default replacements for |version| and |release|, also used in various
# other places throughout the built documents.
#
# The short X.Y version.
version = '1.0'
# The full version, including alpha/beta/rc tags.
release = '1.0'

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
today_fmt = '%B %d, %Y'

# List of documents that shouldn't be included in the build.
#unused_docs = []

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'


# Options for HTML output
# -----------------------

# The style sheet to use for HTML and HTML Help pages. A file of that name
# must exist either in Sphinx' static/ path, or in one of the custom paths
# given in html_static_path.
html_style = 'default.css'

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# The name of an image file (within the static path) to place at the top of
# the sidebar.
#html_logo = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_use_modindex = True

# If true, the reST sources are included in the HTML build as _sources/<name>.
#html_copy_source = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.
#html_use_opensearch = False

# Output file base name for HTML help builder.
htmlhelp_basename = 'The New Waydoc'


# Options for LaTeX output
# ------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, document class [howto/manual]).
latex_documents = [
  ('index', 'The New Way.tex', 'The New Way Documentation', 'Kevin Dangoor', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_use_modindex = True

########NEW FILE########
__FILENAME__ = test_thecode
from newway.thecode import *

def test_the_function():
    output = powerful_function_and_new_too()
    assert output == 2, "Doh! Got %s instead" % (output)
    
########NEW FILE########
__FILENAME__ = thecode
"""This is our powerful, code-filled, new-fangled module."""

# [[[section code]]]
def powerful_function_and_new_too():
    """This is powerful stuff, and it's new."""
    return 2*1
# [[[endsection]]]

########NEW FILE########
__FILENAME__ = pavement
# [[[section imports]]]
from paver.easy import *
import paver.doctools
from paver.setuputils import setup
# [[[endsection]]]

# [[[section setup]]]
setup(
    name="TheNewWay",
    packages=['newway'],
    version="1.0",
    url="http://www.blueskyonmars.com/",
    author="Kevin Dangoor",
    author_email="dangoor@gmail.com"
)
# [[[endsection]]]

# [[[section sphinx]]]
options(
    sphinx=Bunch(
        builddir="_build"
    )
)
# [[[endsection]]]

# [[[section deployoptions]]]
options(
    deploy = Bunch(
        htmldir = path('newway/docs'),
        hosts = ['host1.hostymost.com', 'host2.hostymost.com'],
        hostpath = 'sites/newway'
    )
)
# [[[endsection]]]

# [[[section minilib]]]
options(
    minilib = Bunch(
        extra_files=["doctools"],
        versioned_name=False
    )
)
# [[[endsection]]]

# [[[section sdist]]]
@task
@needs('generate_setup', 'minilib', 'setuptools.command.sdist')
def sdist():
    """Overrides sdist to make sure that our setup.py is generated."""
    pass
# [[[endsection]]]

# [[[section html]]]
@task
@needs('paver.doctools.html')
def html(options):
    """Build the docs and put them into our package."""
    destdir = path('newway/docs')
    destdir.rmtree()
    # [[[section builtdocs]]]
    builtdocs = path("docs") / options.builddir / "html"
    # [[[endsection]]]
    builtdocs.move(destdir)
# [[[endsection]]]    

# [[[section deploy]]]
@task
@cmdopts([
    ('username=', 'u', 'Username to use when logging in to the servers')
])
def deploy(options):
    """Deploy the HTML to the server."""
    for host in options.hosts:
        sh("rsync -avz -e ssh %s/ %s@%s:%s/" % (options.htmldir,
            options.username, host, options.hostpath))
# [[[endsection]]]

# the pass that follows is to work around a weird bug. It looks like
# you can't compile a Python module that ends in a comment.
pass

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# The Old Way documentation build configuration file, created by
# sphinx-quickstart on Sun May  4 14:02:06 2008.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# The contents of this file are pickled, so don't put values in the namespace
# that aren't pickleable (module imports are okay, they're removed automatically).
#
# All configuration values have a default value; values that are commented out
# serve to show the default value.

import sys, os

# If your extensions are in another directory, add it here. If the directory
# is relative to the documentation root, use os.path.abspath to make it
# absolute, like shown here.
#sys.path.append(os.path.abspath('some/directory'))

# General configuration
# ---------------------

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
#extensions = []

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

# General substitutions.
project = 'The Old Way'
copyright = '2008, Kevin Dangoor'

# The default replacements for |version| and |release|, also used in various
# other places throughout the built documents.
#
# The short X.Y version.
version = '1.0'
# The full version, including alpha/beta/rc tags.
release = '1.0'

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
today_fmt = '%B %d, %Y'

# List of documents that shouldn't be included in the build.
#unused_docs = []

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'


# Options for HTML output
# -----------------------

# The style sheet to use for HTML and HTML Help pages. A file of that name
# must exist either in Sphinx' static/ path, or in one of the custom paths
# given in html_static_path.
html_style = 'default.css'

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# The name of an image file (within the static path) to place at the top of
# the sidebar.
#html_logo = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_use_modindex = True

# If true, the reST sources are included in the HTML build as _sources/<name>.
#html_copy_source = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.
#html_use_opensearch = False

# Output file base name for HTML help builder.
htmlhelp_basename = 'The Old Waydoc'


# Options for LaTeX output
# ------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, document class [howto/manual]).
latex_documents = [
  ('index', 'The Old Way.tex', 'The Old Way Documentation', 'Kevin Dangoor', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_use_modindex = True

########NEW FILE########
__FILENAME__ = test_thecode
from oldway.thecode import *

def test_the_function():
    output = powerful_function_but_still_old()
    assert output == 2, "Doh! Got %s instead" % (output)
    
########NEW FILE########
__FILENAME__ = thecode
def powerful_function_but_still_old():
    """This is powerful stuff, but it's still the old way of
    doing things."""
    return 1+1
    
########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Paver documentation build configuration file, created by
# sphinx-quickstart on Fri Apr 11 08:20:18 2008.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# The contents of this file are pickled, so don't put values in the namespace
# that aren't pickleable (module imports are okay, they're removed automatically).
#
# All configuration values have a default value; values that are commented out
# serve to show the default value.

import sys

from sphinx.ext import autodoc


# If your extensions are in another directory, add it here.
#sys.path.append()

# Add our autodoc extension

class TaskDocumenter(autodoc.FunctionDocumenter):
    objtype = "task"
    directivetype = "function"
    
    @classmethod
    def can_document_member(cls, member, membername, isattr, parent):
        from paver.tasks import Task
        return isinstance(member, Task)
        
    def import_object(self):
        super(TaskDocumenter, self).import_object()
        obj = self.object
        self.object = obj.func
        return True
    
autodoc.add_documenter(TaskDocumenter)

# General configuration
# ---------------------

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

# General substitutions.
project = 'Paver'
copyright = '2008, SitePen, Inc.'

# The default replacements for |version| and |release|, also used in various
# other places throughout the built documents.
#
# The short X.Y version.
version = '1.2'
# The full version, including alpha/beta/rc tags.
release = '1.2.2'
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
today_fmt = '%B %d, %Y'

# List of documents that shouldn't be included in the build.
#unused_docs = []

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'


# Options for HTML output
# -----------------------

# The style sheet to use for HTML and HTML Help pages. A file of that name
# must exist either in Sphinx' static/ path, or in one of the custom paths
# given in html_static_path.
html_style = 'default.css'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Content template for the index page.
#html_index = ''

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_use_modindex = True

# If true, the reST sources are included in the HTML build as _sources/<name>.
#html_copy_source = True

# Output file base name for HTML help builder.
htmlhelp_basename = 'Paverdoc'


# Options for LaTeX output
# ------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, document class [howto/manual]).
latex_documents = [('index', 'paver.tex', 'Paver Manual', 'Kevin Dangoor',
                    'manual', False)]

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_use_modindex = True

########NEW FILE########
__FILENAME__ = pavement
from paver.easy import *

from paver.release import setup_meta

import paver.doctools
import paver.virtual
import paver.misctasks
from paver.setuputils import setup

options = environment.options

setup(**setup_meta)

options(
    minilib=Bunch(
        extra_files=['doctools', 'virtual'],
        versioned_name=False,
    ),
    sphinx=Bunch(
        builddir="build",
        sourcedir="source"
    ),
    virtualenv=Bunch(
        packages_to_install=["nose", "Sphinx>=0.6b1", "docutils", "virtualenv"],
        install_paver=False,
        script_name='bootstrap.py',
        paver_command_line=None,
        dest_dir="virtualenv"
    ),
    cog=Bunch(
        includedir="docs/samples",
        beginspec="<==",
        endspec="==>",
        endoutput="<==end==>"
    ),
    deploy=Bunch(
        deploydir="blueskyonmars.com/projects/paver"
    )
)

# not only does paver bootstrap itself, but it should work even with just 
# distutils
if paver.setuputils.has_setuptools:
    old_sdist = "setuptools.command.sdist"
    options.setup.update(dict(
        install_requires=[],
        test_suite='nose.collector',
        zip_safe=False,
        entry_points="""
[console_scripts]
paver = paver.tasks:main
"""
    ))
else:
    old_sdist = "distutils.command.sdist"
    options.setup.scripts = ['distutils_scripts/paver']

options.setup.package_data=paver.setuputils.find_package_data("paver", package="paver",
                                                only_in_packages=False)

if paver.doctools.has_sphinx:
    @task
    @needs('cog', 'paver.doctools.html')
    def html():
        """Build Paver's documentation and install it into paver/docs"""
        builtdocs = path("docs") / options.sphinx.builddir / "html"
        destdir = path("paver") / "docs"
        destdir.rmtree_p()
        builtdocs.move(destdir)
    
    @task
    @needs('html', "minilib", "generate_setup", old_sdist)
    def sdist():
        """Builds the documentation and the tarball."""
        pass

if paver.virtual.has_virtualenv:
    @task
    def bootstrap():
        """Build a virtualenv bootstrap for developing paver."""
        # we have to pull some private api shenanigans that normal people don't
        # because we're bootstrapping paver itself.
        paver.virtual._create_bootstrap(options.script_name,
                              options.packages_to_install,
                              options.paver_command_line,
                              options.install_paver,
                              more_text="""    subprocess.call([join("""
                              """bin_dir, 'python'), '-c', """
                              """'import sys; sys.path.append("."); """
                              """import paver.command; paver.command.main()', """
                              """'develop'])""",
                              dest_dir=options.virtualenv.dest_dir)
    
@task
def clean():
    """Cleans up this paver directory. Removes the virtualenv traces and
    the build directory."""
    path("build").rmtree_p()
    path("bin").rmtree_p()
    path("lib").rmtree_p()
    path(".Python").remove_p()
    
@task
@needs("uncog")
@consume_args
def commit(args):
    """Removes the generated code from the docs and then commits to bzr."""
    sh("git commit " + ' '.join(args))

@task
@cmdopts([
    ("branch=", "b", "Branch from which to publish"),
    ("docs-branch=", "d", "Docs branch to commit/push to"),
    ("git-repo=", "g", "Github repository to use"),
    ("deploy-key=", "k", "Deploy key to use"),
])
def publish_docs(options):
    """Publish current docs/site do paver.github.com"""

    # we are going to mess around with files, so do it in temporary place
    import os
    from subprocess import check_call, CalledProcessError
    from tempfile import mkdtemp, mkstemp

    current_repo = path(os.curdir).abspath()
    branch = getattr(options, 'branch', 'master')
    docs_branch = getattr(options, 'docs_branch', 'gh-pages')
    repo = getattr(options, 'git_repo', 'git@github.com:paver/paver.git')

    try:
        safe_clone = path(mkdtemp(prefix='paver-clone-'))
        docs_repo = path(mkdtemp(prefix='paver-docs-'))
        fd, git = mkstemp(prefix='tmp-git-ssh-')

        # TODO: I strongly believe there have to be better way to provide custom
        # identity file for git, but cannot find one...so, workaround
        f = os.fdopen(fd, 'w')
        f.writelines(["#!/bin/sh", os.linesep, "ssh%s $*" % (" -i "+options.deploy_key if getattr(options, "deploy_key", None) else "")])
        f.close()

        os.chmod(git, int('777', 8))

        safe_clone.chdir()

        sh('git init')

        check_call(['git', 'remote', 'add', '-t', branch, '-f', 'origin', 'file://'+str(current_repo)], env={"GIT_SSH" : git})

        check_call(['git', 'checkout', branch], env={"GIT_SSH" : git})

        check_call(['python', os.path.join(str(current_repo), "distutils_scripts", "paver"), 'html'], env={
            'PYTHONPATH' : os.path.join(str(current_repo))
        })


        docs_repo.chdir()

        sh('git init')

        check_call(['git', 'remote', 'add', '-t', docs_branch, '-f', 'origin', repo], env={"GIT_SSH" : git})
        check_call(['git', 'checkout', docs_branch], env={"GIT_SSH" : git})

        check_call(['rsync', '-av', os.path.join(str(safe_clone), 'paver', 'docs')+'/', str(docs_repo)])

        sh('git add *')

        #TODO: '...from revision abc'
        try:
            check_call(['git', 'commit', '-a', '-m', "Commit auto-generated documentation"])
        except CalledProcessError:
            # usually 'working directory clean'
            pass
        else:
            check_call(['git', 'push', 'origin', '%s:%s' % (docs_branch, docs_branch)], env={"GIT_SSH" : git})


    finally:
        safe_clone.rmtree_p()
        docs_repo.rmtree_p()
        os.remove(git)


@task
def release():
    """ Release new version of Paver """

    # To avoid dirty workdirs and various artifacts, offload complete environment
    # to temporary directory located outside of current worktree

    import os
    from subprocess import check_call, CalledProcessError
    from tempfile import mkdtemp, mkstemp

    release_clone = path(mkdtemp(prefix='paver-release-'))
    current_repo = path(os.curdir).abspath()
    branch = getattr(options, 'branch', 'master')

    # clone current branch to temporary directory
    try:
        release_clone.chdir()
        sh('git init')
        check_call(['git', 'remote', 'add', '-t', branch, '-f', 'origin', 'file://'+str(current_repo)])
        check_call(['git', 'checkout', '-b', branch, "origin/%s" % branch])

        # install release requirements to be sure we are generating everything properly
        sh('pip install -r release-requirements.txt')


        # build documentation
        sh('paver html')

        # create source directory
        sh('paver sdist')

        # create source directory and upload it to PyPI
        sh('paver sdist upload')

        # also upload sphinx documentation
        sh('paver upload_sphinx --upload-dir=paver/docs')

    finally:
        release_clone.rmtree_p()

@task
@consume_args
def bump(args):
    import paver.version
    version = map(int, paver.version.VERSION.split('.')[0:3])

    if len(args) > 0 and args[0] == 'major':
        version[1] += 1
    else:
        version[2] += 1

    version = map(str, version)

    module_content = "VERSION='%s'\n" % '.'.join(version)

    # bump version in paver
    with open(path('paver/version.py'), 'w') as f:
        f.write(module_content)

    # bump version in sphinx
    conf = []
    with open(path('docs/source/conf.py'), 'r') as f:
        for line in f.readlines():
            if line.startswith('version = '):
                line = "version = '%s'\n" % '.'.join(version[0:2])
            elif line.startswith('release = '):
                line = "release = '%s'\n" % '.'.join(version[0:3])

            conf.append(line)

    with open(path('docs/source/conf.py'), 'w') as f:
        f.writelines(conf)

########NEW FILE########
__FILENAME__ = bzr
"""Convenience functions for working with bzr.

This module does not include any tasks, only functions."""

import sys

if sys.version_info[0] == 3:
    raise ImportError("Bazaar-NG is not available for Python 3")

from paver.options import Bunch
from bzrlib.builtins import cmd_branch, cmd_checkout, cmd_update, cmd_pull, cmd_version_info
from StringIO import StringIO

__all__ = ["checkout", "update", "branch", "pull", "info"]

def do_bzr_cmd(cmd_class, output=True, **kwarg):
    if output:
        import bzrlib.ui
        from bzrlib.ui.text import TextUIFactory
        bzrlib.ui.ui_factory = TextUIFactory()
    cmd = cmd_class()
    if output:
        cmd._setup_outf()
    else:
        cmd.outf = StringIO()
    cmd.run(**kwarg)

    return cmd.outf

def checkout(url, dest, revision=None):
    """Checkout from the URL to the destination."""
    do_bzr_cmd(cmd_checkout, branch_location=url, to_location=dest, revision=revision)

def update(path='.'):
    """Update the given path."""
    do_bzr_cmd(cmd_update, dir=path)

def branch(url, dest, revision=None):
    """Branch from the given URL to the destination."""
    do_bzr_cmd(cmd_branch, from_location=url, to_location=dest, revision=revision)

def pull(url, revision=None):
    """Pull from the given URL at the optional revision."""
    do_bzr_cmd(cmd_pull, location=url, revision=revision)

def info(location=None):
    """Retrieve the info at location."""
    data = Bunch()
    sio = do_bzr_cmd(cmd_version_info, False, location=location)
    sio.seek(0)

    for line in sio.readlines():
        if not ":" in line:
            continue
        key, value = line.split(":", 1)
        key = key.lower().replace(" ", "_").replace("-", "_")
        data[key] = value.strip()
    return data

########NEW FILE########
__FILENAME__ = command
"""Paver's command-line driver"""

import warnings

warnings.warn("paver.command is deprecated. Please re-run the generate_setup task.",
    stacklevel=2)
import paver.tasks

def main():
    paver.tasks.main()

########NEW FILE########
__FILENAME__ = defaults
"""The namespace for the pavement to run in, also imports default tasks."""

import warnings

warnings.warn("""paver.defaults is deprecated. Import from paver.easy instead.
Note that you will need to add additional declarations for exactly
equivalent behavior. Specifically:

from paver.easy import *
import paver.misctasks
from paver import setuputils

setuputils.install_distutils_tasks()
""", DeprecationWarning, 2)

from paver.easy import *
from paver.misctasks import *
from paver import setuputils

setuputils.install_distutils_tasks()

########NEW FILE########
__FILENAME__ = path2
#
# Copyright (c) 2010 Mikhail Gusarov
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#

""" path.py - An object representing a path to a file or directory.

Original author:
 Jason Orendorff <jason.orendorff\x40gmail\x2ecom>

Contributors:
 Mikhail Gusarov <dottedmag@dottedmag.net>
 Marc Abramowitz <marc@marc-abramowitz.com>

Example:

from path import path
d = path('/home/guido/bin')
for f in d.files('*.py'):
    f.chmod(0755)

This module requires Python 2.3 or later.
"""

from __future__ import generators

import __builtin__

import sys
import warnings
import os
import fnmatch
import glob
import shutil
import codecs
import hashlib
import errno

__version__ = '2.4'
__all__ = ['path']

PRE_PY3 = sys.version_info[0] < 3

# Platform-specific support for path.owner
if os.name == 'nt':
    try:
        import win32security
    except ImportError:
        win32security = None
else:
    try:
        import pwd
    except ImportError:
        pwd = None

# Pre-2.3 support.  Are unicode filenames supported?
_base = str
_getcwd = os.getcwd
try:
    if os.path.supports_unicode_filenames:
        _base = unicode
        _getcwd = os.getcwdu
except AttributeError:
    pass

# Pre-2.3 workaround for basestring.
try:
    basestring
except NameError:
    basestring = (str, unicode)

# Universal newline support
_textmode = 'U'
if hasattr(__builtin__, 'file') and not hasattr(file, 'newlines'):
    _textmode = 'r'

class TreeWalkWarning(Warning):
    pass

class path(_base):
    """ Represents a filesystem path.

    For documentation on individual methods, consult their
    counterparts in os.path.
    """

    # --- Special Python methods.

    def __repr__(self):
        return 'path(%s)' % _base.__repr__(self)

    # Adding a path and a string yields a path.
    def __add__(self, more):
        try:
            resultStr = _base.__add__(self, more)
        except TypeError:  # Python bug
            resultStr = NotImplemented

        # On python 2, unicode result breaks os.path.join
        # if we are inheriting from str
        # see https://github.com/paver/paver/issues/78
        if isinstance(resultStr, unicode) and not os.path.supports_unicode_filenames:
            resultStr = resultStr.encode('utf-8')

        if resultStr is NotImplemented:
            return resultStr
        return self.__class__(resultStr)

    def __radd__(self, other):
        if isinstance(other, basestring):
            return self.__class__(other.__add__(self))
        else:
            return NotImplemented

    # The / operator joins paths.
    def __div__(self, rel):
        """ fp.__div__(rel) == fp / rel == fp.joinpath(rel)

        Join two path components, adding a separator character if
        needed.
        """
        return self.__class__(os.path.join(self, rel))

    # Make the / operator work even when true division is enabled.
    __truediv__ = __div__

    def __enter__(self):
        self._old_dir = self.getcwd()
        os.chdir(self)

    def __exit__(self, *_):
        os.chdir(self._old_dir)

    def getcwd(cls):
        """ Return the current working directory as a path object. """
        return cls(_getcwd())
    getcwd = classmethod(getcwd)

    #
    # --- Operations on path strings.

    def abspath(self):       return self.__class__(os.path.abspath(self))
    def normcase(self):      return self.__class__(os.path.normcase(self))
    def normpath(self):      return self.__class__(os.path.normpath(self))
    def realpath(self):      return self.__class__(os.path.realpath(self))
    def expanduser(self):    return self.__class__(os.path.expanduser(self))
    def expandvars(self):    return self.__class__(os.path.expandvars(self))
    def dirname(self):       return self.__class__(os.path.dirname(self))
    def basename(self):      return self.__class__(os.path.basename(self))

    def expand(self):
        """ Clean up a filename by calling expandvars(),
        expanduser(), and normpath() on it.

        This is commonly everything needed to clean up a filename
        read from a configuration file, for example.
        """
        return self.expandvars().expanduser().normpath()

    def _get_namebase(self):
        base, ext = os.path.splitext(self.name)
        return base

    def _get_ext(self):
        f, ext = os.path.splitext(_base(self))
        return ext

    def _get_drive(self):
        drive, r = os.path.splitdrive(self)
        return self.__class__(drive)

    parent = property(
        dirname, None, None,
        """ This path's parent directory, as a new path object.

        For example, path('/usr/local/lib/libpython.so').parent == path('/usr/local/lib')
        """)

    name = property(
        basename, None, None,
        """ The name of this file or directory without the full path.

        For example, path('/usr/local/lib/libpython.so').name == 'libpython.so'
        """)

    namebase = property(
        _get_namebase, None, None,
        """ The same as path.name, but with one file extension stripped off.

        For example, path('/home/guido/python.tar.gz').name     == 'python.tar.gz',
        but          path('/home/guido/python.tar.gz').namebase == 'python.tar'
        """)

    ext = property(
        _get_ext, None, None,
        """ The file extension, for example '.py'. """)

    drive = property(
        _get_drive, None, None,
        """ The drive specifier, for example 'C:'.
        This is always empty on systems that don't use drive specifiers.
        """)

    def splitpath(self):
        """ p.splitpath() -> Return (p.parent, p.name). """
        parent, child = os.path.split(self)
        return self.__class__(parent), child

    def splitdrive(self):
        """ p.splitdrive() -> Return (p.drive, <the rest of p>).

        Split the drive specifier from this path.  If there is
        no drive specifier, p.drive is empty, so the return value
        is simply (path(''), p).  This is always the case on Unix.
        """
        drive, rel = os.path.splitdrive(self)
        return self.__class__(drive), rel

    def splitext(self):
        """ p.splitext() -> Return (p.stripext(), p.ext).

        Split the filename extension from this path and return
        the two parts.  Either part may be empty.

        The extension is everything from '.' to the end of the
        last path segment.  This has the property that if
        (a, b) == p.splitext(), then a + b == p.
        """
        filename, ext = os.path.splitext(self)
        return self.__class__(filename), ext

    def stripext(self):
        """ p.stripext() -> Remove one file extension from the path.

        For example, path('/home/guido/python.tar.gz').stripext()
        returns path('/home/guido/python.tar').
        """
        return self.splitext()[0]

    if hasattr(os.path, 'splitunc'):
        def splitunc(self):
            unc, rest = os.path.splitunc(self)
            return self.__class__(unc), rest

        def _get_uncshare(self):
            unc, r = os.path.splitunc(self)
            return self.__class__(unc)

        uncshare = property(
            _get_uncshare, None, None,
            """ The UNC mount point for this path.
            This is empty for paths on local drives. """)

    def joinpath(self, *args):
        """ Join two or more path components, adding a separator
        character (os.sep) if needed.  Returns a new path
        object.
        """
        return self.__class__(os.path.join(self, *args))

    def splitall(self):
        r""" Return a list of the path components in this path.

        The first item in the list will be a path.  Its value will be
        either os.curdir, os.pardir, empty, or the root directory of
        this path (for example, '/' or 'C:\\').  The other items in
        the list will be strings.

        path.path.joinpath(*result) will yield the original path.
        """
        parts = []
        loc = self
        while loc != os.curdir and loc != os.pardir:
            prev = loc
            loc, child = prev.splitpath()
            if loc == prev:
                break
            parts.append(child)
        parts.append(loc)
        parts.reverse()
        return parts

    def relpath(self):
        """ Return this path as a relative path,
        based from the current working directory.
        """
        cwd = self.__class__(os.getcwd())
        return cwd.relpathto(self)

    def relpathto(self, dest):
        """ Return a relative path from self to dest.

        If there is no relative path from self to dest, for example if
        they reside on different drives in Windows, then this returns
        dest.abspath().
        """
        origin = self.abspath()
        dest = self.__class__(dest).abspath()

        orig_list = origin.normcase().splitall()
        # Don't normcase dest!  We want to preserve the case.
        dest_list = dest.splitall()

        if orig_list[0] != os.path.normcase(dest_list[0]):
            # Can't get here from there.
            return dest

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
            relpath = os.curdir
        else:
            relpath = os.path.join(*segments)
        return self.__class__(relpath)

    # --- Listing, searching, walking, and matching

    def listdir(self, pattern=None):
        """ D.listdir() -> List of items in this directory.

        Use D.files() or D.dirs() instead if you want a listing
        of just files or just subdirectories.

        The elements of the list are path objects.

        With the optional 'pattern' argument, this only lists
        items whose names match the given pattern.
        """
        names = os.listdir(self)
        if pattern is not None:
            names = fnmatch.filter(names, pattern)
        return [self / child for child in names]

    def dirs(self, pattern=None):
        """ D.dirs() -> List of this directory's subdirectories.

        The elements of the list are path objects.
        This does not walk recursively into subdirectories
        (but see path.walkdirs).

        With the optional 'pattern' argument, this only lists
        directories whose names match the given pattern.  For
        example, d.dirs('build-*').
        """
        return [p for p in self.listdir(pattern) if p.isdir()]

    def files(self, pattern=None):
        """ D.files() -> List of the files in this directory.

        The elements of the list are path objects.
        This does not walk into subdirectories (see path.walkfiles).

        With the optional 'pattern' argument, this only lists files
        whose names match the given pattern.  For example,
        d.files('*.pyc').
        """

        return [p for p in self.listdir(pattern) if p.isfile()]

    def walk(self, pattern=None, errors='strict'):
        """ D.walk() -> iterator over files and subdirs, recursively.

        The iterator yields path objects naming each child item of
        this directory and its descendants.  This requires that
        D.isdir().

        This performs a depth-first traversal of the directory tree.
        Each directory is returned just before all its children.

        The errors= keyword argument controls behavior when an
        error occurs.  The default is 'strict', which causes an
        exception.  The other allowed values are 'warn', which
        reports the error via warnings.warn(), and 'ignore'.
        """
        if errors not in ('strict', 'warn', 'ignore'):
            raise ValueError("invalid errors parameter")

        try:
            childList = self.listdir()
        except Exception:
            if errors == 'ignore':
                return
            elif errors == 'warn':
                warnings.warn(
                    "Unable to list directory '%s': %s"
                    % (self, sys.exc_info()[1]),
                    TreeWalkWarning)
                return
            else:
                raise

        for child in childList:
            if pattern is None or child.fnmatch(pattern):
                yield child
            try:
                isdir = child.isdir()
            except Exception:
                if errors == 'ignore':
                    isdir = False
                elif errors == 'warn':
                    warnings.warn(
                        "Unable to access '%s': %s"
                        % (child, sys.exc_info()[1]),
                        TreeWalkWarning)
                    isdir = False
                else:
                    raise

            if isdir:
                for item in child.walk(pattern, errors):
                    yield item

    def walkdirs(self, pattern=None, errors='strict'):
        """ D.walkdirs() -> iterator over subdirs, recursively.

        With the optional 'pattern' argument, this yields only
        directories whose names match the given pattern.  For
        example, mydir.walkdirs('*test') yields only directories
        with names ending in 'test'.

        The errors= keyword argument controls behavior when an
        error occurs.  The default is 'strict', which causes an
        exception.  The other allowed values are 'warn', which
        reports the error via warnings.warn(), and 'ignore'.
        """
        if errors not in ('strict', 'warn', 'ignore'):
            raise ValueError("invalid errors parameter")

        try:
            dirs = self.dirs()
        except Exception:
            if errors == 'ignore':
                return
            elif errors == 'warn':
                warnings.warn(
                    "Unable to list directory '%s': %s"
                    % (self, sys.exc_info()[1]),
                    TreeWalkWarning)
                return
            else:
                raise

        for child in dirs:
            if pattern is None or child.fnmatch(pattern):
                yield child
            for subsubdir in child.walkdirs(pattern, errors):
                yield subsubdir

    def walkfiles(self, pattern=None, errors='strict'):
        """ D.walkfiles() -> iterator over files in D, recursively.

        The optional argument, pattern, limits the results to files
        with names that match the pattern.  For example,
        mydir.walkfiles('*.tmp') yields only files with the .tmp
        extension.
        """
        if errors not in ('strict', 'warn', 'ignore'):
            raise ValueError("invalid errors parameter")

        try:
            childList = self.listdir()
        except Exception:
            if errors == 'ignore':
                return
            elif errors == 'warn':
                warnings.warn(
                    "Unable to list directory '%s': %s"
                    % (self, sys.exc_info()[1]),
                    TreeWalkWarning)
                return
            else:
                raise

        for child in childList:
            try:
                isfile = child.isfile()
                isdir = not isfile and child.isdir()
            except:
                if errors == 'ignore':
                    continue
                elif errors == 'warn':
                    warnings.warn(
                        "Unable to access '%s': %s"
                        % (self, sys.exc_info()[1]),
                        TreeWalkWarning)
                    continue
                else:
                    raise

            if isfile:
                if pattern is None or child.fnmatch(pattern):
                    yield child
            elif isdir:
                for f in child.walkfiles(pattern, errors):
                    yield f

    def fnmatch(self, pattern):
        """ Return True if self.name matches the given pattern.

        pattern - A filename pattern with wildcards,
            for example '*.py'.
        """
        return fnmatch.fnmatch(self.name, pattern)

    def glob(self, pattern):
        """ Return a list of path objects that match the pattern.

        pattern - a path relative to this directory, with wildcards.

        For example, path('/users').glob('*/bin/*') returns a list
        of all the files users have in their bin directories.
        """
        cls = self.__class__
        return [cls(s) for s in glob.glob(_base(self / pattern))]

    #
    # --- Reading or writing an entire file at once.

    def open(self, mode='r'):
        """ Open this file.  Return a file object. """
        return open(self, mode)

    def bytes(self):
        """ Open this file, read all bytes, return them as a string. """
        f = self.open('rb')
        try:
            return f.read()
        finally:
            f.close()

    def write_bytes(self, bytes, append=False):
        """ Open this file and write the given bytes to it.

        Default behavior is to overwrite any existing file.
        Call p.write_bytes(bytes, append=True) to append instead.
        """
        if append:
            mode = 'ab'
        else:
            mode = 'wb'
        f = self.open(mode)
        try:
            f.write(bytes)
        finally:
            f.close()

    def text(self, encoding=None, errors='strict'):
        r""" Open this file, read it in, return the content as a string.

        This uses 'U' mode in Python 2.3 and later, so '\r\n' and '\r'
        are automatically translated to '\n'.

        Optional arguments:

        encoding - The Unicode encoding (or character set) of
            the file.  If present, the content of the file is
            decoded and returned as a unicode object; otherwise
            it is returned as an 8-bit str.
        errors - How to handle Unicode errors; see help(str.decode)
            for the options.  Default is 'strict'.
        """
        if encoding is None:
            # 8-bit
            f = self.open(_textmode)
            try:
                return f.read()
            finally:
                f.close()
        else:
            # Unicode
            f = codecs.open(self, 'r', encoding, errors)
            # (Note - Can't use 'U' mode here, since codecs.open
            # doesn't support 'U' mode, even in Python 2.3.)
            try:
                t = f.read()
            finally:
                f.close()
            return (t.replace(u'\r\n', u'\n')
                     .replace(u'\r\x85', u'\n')
                     .replace(u'\r', u'\n')
                     .replace(u'\x85', u'\n')
                     .replace(u'\u2028', u'\n'))

    def write_text(self, text, encoding=None, errors='strict', linesep=os.linesep, append=False):
        r""" Write the given text to this file.

        The default behavior is to overwrite any existing file;
        to append instead, use the 'append=True' keyword argument.

        There are two differences between path.write_text() and
        path.write_bytes(): newline handling and Unicode handling.
        See below.

        Parameters:

          - text - str/unicode - The text to be written.

          - encoding - str - The Unicode encoding that will be used.
            This is ignored if 'text' isn't a Unicode string.

          - errors - str - How to handle Unicode encoding errors.
            Default is 'strict'.  See help(unicode.encode) for the
            options.  This is ignored if 'text' isn't a Unicode
            string.

          - linesep - keyword argument - str/unicode - The sequence of
            characters to be used to mark end-of-line.  The default is
            os.linesep.  You can also specify None; this means to
            leave all newlines as they are in 'text'.

          - append - keyword argument - bool - Specifies what to do if
            the file already exists (True: append to the end of it;
            False: overwrite it.)  The default is False.


        --- Newline handling.

        write_text() converts all standard end-of-line sequences
        ('\n', '\r', and '\r\n') to your platform's default end-of-line
        sequence (see os.linesep; on Windows, for example, the
        end-of-line marker is '\r\n').

        If you don't like your platform's default, you can override it
        using the 'linesep=' keyword argument.  If you specifically want
        write_text() to preserve the newlines as-is, use 'linesep=None'.

        This applies to Unicode text the same as to 8-bit text, except
        there are three additional standard Unicode end-of-line sequences:
        u'\x85', u'\r\x85', and u'\u2028'.

        (This is slightly different from when you open a file for
        writing with fopen(filename, "w") in C or open(filename, 'w')
        in Python.)


        --- Unicode

        If 'text' isn't Unicode, then apart from newline handling, the
        bytes are written verbatim to the file.  The 'encoding' and
        'errors' arguments are not used and must be omitted.

        If 'text' is Unicode, it is first converted to bytes using the
        specified 'encoding' (or the default encoding if 'encoding'
        isn't specified).  The 'errors' argument applies only to this
        conversion.

        """
        if isinstance(text, unicode):
            if linesep is not None:
                # Convert all standard end-of-line sequences to
                # ordinary newline characters.
                text = (text.replace(u'\r\n', u'\n')
                            .replace(u'\r\x85', u'\n')
                            .replace(u'\r', u'\n')
                            .replace(u'\x85', u'\n')
                            .replace(u'\u2028', u'\n'))
                text = text.replace(u'\n', linesep)
            if encoding is None:
                encoding = sys.getdefaultencoding()
            bytes = text.encode(encoding, errors)
        else:
            # It is an error to specify an encoding if 'text' is
            # an 8-bit string.
            assert encoding is None

            if linesep is not None:
                text = (text.replace('\r\n', '\n')
                            .replace('\r', '\n'))
                bytes = text.replace('\n', linesep)

        self.write_bytes(bytes, append)

    def lines(self, encoding=None, errors='strict', retain=True):
        r""" Open this file, read all lines, return them in a list.

        Optional arguments:
            encoding - The Unicode encoding (or character set) of
                the file.  The default is None, meaning the content
                of the file is read as 8-bit characters and returned
                as a list of (non-Unicode) str objects.
            errors - How to handle Unicode errors; see help(str.decode)
                for the options.  Default is 'strict'
            retain - If true, retain newline characters; but all newline
                character combinations ('\r', '\n', '\r\n') are
                translated to '\n'.  If false, newline characters are
                stripped off.  Default is True.

        This uses 'U' mode in Python 2.3 and later.
        """
        if encoding is None and retain:
            f = self.open(_textmode)
            try:
                return f.readlines()
            finally:
                f.close()
        else:
            return self.text(encoding, errors).splitlines(retain)

    def write_lines(self, lines, encoding=None, errors='strict',
                    linesep=os.linesep, append=False):
        r""" Write the given lines of text to this file.

        By default this overwrites any existing file at this path.

        This puts a platform-specific newline sequence on every line.
        See 'linesep' below.

        lines - A list of strings.

        encoding - A Unicode encoding to use.  This applies only if
            'lines' contains any Unicode strings.

        errors - How to handle errors in Unicode encoding.  This
            also applies only to Unicode strings.

        linesep - The desired line-ending.  This line-ending is
            applied to every line.  If a line already has any
            standard line ending ('\r', '\n', '\r\n', u'\x85',
            u'\r\x85', u'\u2028'), that will be stripped off and
            this will be used instead.  The default is os.linesep,
            which is platform-dependent ('\r\n' on Windows, '\n' on
            Unix, etc.)  Specify None to write the lines as-is,
            like file.writelines().

        Use the keyword argument append=True to append lines to the
        file.  The default is to overwrite the file.  Warning:
        When you use this with Unicode data, if the encoding of the
        existing data in the file is different from the encoding
        you specify with the encoding= parameter, the result is
        mixed-encoding data, which can really confuse someone trying
        to read the file later.
        """
        if append:
            mode = 'ab'
        else:
            mode = 'wb'
        f = self.open(mode)
        try:
            for line in lines:
                isUnicode = isinstance(line, unicode)
                if linesep is not None:
                    # Strip off any existing line-end and add the
                    # specified linesep string.
                    if isUnicode:
                        if line[-2:] in (u'\r\n', u'\x0d\x85'):
                            line = line[:-2]
                        elif line[-1:] in (u'\r', u'\n',
                                           u'\x85', u'\u2028'):
                            line = line[:-1]
                    else:
                        if line[-2:] == '\r\n':
                            line = line[:-2]
                        elif line[-1:] in ('\r', '\n'):
                            line = line[:-1]
                    line += linesep
                if isUnicode:
                    if encoding is None:
                        encoding = sys.getdefaultencoding()
                    line = line.encode(encoding, errors)
                f.write(line)
        finally:
            f.close()

    def read_md5(self):
        """ Calculate the md5 hash for this file.

        This reads through the entire file.
        """
        return self.read_hash('md5')

    def _hash(self, hash_name):
        f = self.open('rb')
        try:
            m = hashlib.new(hash_name)
            while True:
                d = f.read(8192)
                if not d:
                    break
                m.update(d)
            return m
        finally:
            f.close()

    def read_hash(self, hash_name):
        """ Calculate given hash for this file.

        List of supported hashes can be obtained from hashlib package. This
        reads the entire file.
        """
        return self._hash(hash_name).digest()

    def read_hexhash(self, hash_name):
        """ Calculate given hash for this file, returning hexdigest.

        List of supported hashes can be obtained from hashlib package. This
        reads the entire file.
        """
        return self._hash(hash_name).hexdigest()

    # --- Methods for querying the filesystem.
    # N.B. On some platforms, the os.path functions may be implemented in C
    # (e.g. isdir on Windows, Python 3.2.2), and compiled functions don't get
    # bound. Playing it safe and wrapping them all in method calls.

    def isabs(self): return os.path.isabs(self)
    def exists(self): return os.path.exists(self)
    def isdir(self): return os.path.isdir(self)
    def isfile(self): return os.path.isfile(self)
    def islink(self): return os.path.islink(self)
    def ismount(self): return os.path.ismount(self)

    if hasattr(os.path, 'samefile'):
        def samefile(self, otherfile): return os.path.samefile(self, otherfile)

    def getatime(self): return os.path.getatime(self)
    atime = property(
        getatime, None, None,
        """ Last access time of the file. """)

    def getmtime(self): return os.path.getmtime(self)
    mtime = property(
        getmtime, None, None,
        """ Last-modified time of the file. """)

    if hasattr(os.path, 'getctime'):
        def getctime(self): return os.path.getctime(self)
        ctime = property(
            getctime, None, None,
            """ Creation time of the file. """)

    def getsize(self): return os.path.getsize(self)
    size = property(
        getsize, None, None,
        """ Size of the file, in bytes. """)

    if hasattr(os, 'access'):
        def access(self, mode):
            """ Return true if current user has access to this path.

            mode - One of the constants os.F_OK, os.R_OK, os.W_OK, os.X_OK
            """
            return os.access(self, mode)

    def stat(self):
        """ Perform a stat() system call on this path. """
        return os.stat(self)

    def lstat(self):
        """ Like path.stat(), but do not follow symbolic links. """
        return os.lstat(self)

    def get_owner(self):
        r""" Return the name of the owner of this file or directory.

        This follows symbolic links.

        On Windows, this returns a name of the form ur'DOMAIN\User Name'.
        On Windows, a group can own a file or directory.
        """
        if os.name == 'nt':
            if win32security is None:
                raise Exception("path.owner requires win32all to be installed")
            desc = win32security.GetFileSecurity(
                self, win32security.OWNER_SECURITY_INFORMATION)
            sid = desc.GetSecurityDescriptorOwner()
            account, domain, typecode = win32security.LookupAccountSid(None, sid)
            return domain + u'\\' + account
        else:
            if pwd is None:
                raise NotImplementedError("path.owner is not implemented on this platform.")
            st = self.stat()
            return pwd.getpwuid(st.st_uid).pw_name

    owner = property(
        get_owner, None, None,
        """ Name of the owner of this file or directory. """)

    if hasattr(os, 'statvfs'):
        def statvfs(self):
            """ Perform a statvfs() system call on this path. """
            return os.statvfs(self)

    if hasattr(os, 'pathconf'):
        def pathconf(self, name):
            return os.pathconf(self, name)

    #
    # --- Modifying operations on files and directories

    def utime(self, times):
        """ Set the access and modified times of this file. """
        os.utime(self, times)

    def chmod(self, mode):
        os.chmod(self, mode)

    if hasattr(os, 'chown'):
        def chown(self, uid, gid):
            os.chown(self, uid, gid)

    def rename(self, new):
        os.rename(self, new)

    def renames(self, new):
        os.renames(self, new)

    #
    # --- Create/delete operations on directories

    def mkdir(self, mode=0777):
        if not self.exists():
            os.mkdir(self, mode)

    def mkdir_p(self, mode=0777):
        try:
            self.mkdir(mode)
        except OSError, e:
            if e.errno != errno.EEXIST:
                raise

    def makedirs(self, mode=0777):
        if not self.exists():
            os.makedirs(self, mode)

    def makedirs_p(self, mode=0777):
        try:
            self.makedirs(mode)
        except OSError, e:
            if e.errno != errno.EEXIST:
                raise

    def rmdir(self):
        if self.exists():
            os.rmdir(self)

    def rmdir_p(self):
        try:
            self.rmdir()
        except OSError, e:
            if e.errno != errno.ENOTEMPTY and e.errno != errno.EEXIST:
                raise

    def removedirs(self):
        if self.exists():
            os.removedirs(self)

    def removedirs_p(self):
        try:
            self.removedirs()
        except OSError, e:
            if e.errno != errno.ENOTEMPTY and e.errno != errno.EEXIST:
                raise

    # --- Modifying operations on files

    def touch(self):
        """ Set the access/modified times of this file to the current time.
        Create the file if it does not exist.
        """
        fd = os.open(self, os.O_WRONLY | os.O_CREAT, 0666)
        os.close(fd)
        os.utime(self, None)

    def remove(self):
        if self.exists():
            os.remove(self)

    def remove_p(self):
        try:
            self.unlink()
        except OSError, e:
            if e.errno != errno.ENOENT:
                raise

    def unlink(self):
        if self.exists():
            os.unlink(self)

    def unlink_p(self):
        self.remove_p()

    # --- Links

    if hasattr(os, 'link'):
        def link(self, newpath):
            """ Create a hard link at 'newpath', pointing to this file. """
            os.link(self, newpath)

    if hasattr(os, 'symlink'):
        def symlink(self, newlink):
            """ Create a symbolic link at 'newlink', pointing here. """
            os.symlink(self, newlink)

    if hasattr(os, 'readlink'):
        def readlink(self):
            """ Return the path to which this symbolic link points.

            The result may be an absolute or a relative path.
            """
            return self.__class__(os.readlink(self))

        def readlinkabs(self):
            """ Return the path to which this symbolic link points.

            The result is always an absolute path.
            """
            p = self.readlink()
            if p.isabs():
                return p
            else:
                return (self.parent / p).abspath()

    #
    # --- High-level functions from shutil

    copyfile = shutil.copyfile
    copymode = shutil.copymode
    copystat = shutil.copystat
    copy = shutil.copy
    copy2 = shutil.copy2
    copytree = shutil.copytree
    if hasattr(shutil, 'move'):
        move = shutil.move

    def rmtree(self, *args, **kw):
        if self.exists():
            shutil.rmtree(self, *args, **kw)

    def rmtree_p(self):
        try:
            self.rmtree()
        except OSError, e:
            if e.errno != errno.ENOENT:
                raise

    #
    # --- Special stuff from os

    if hasattr(os, 'chroot'):
        def chroot(self):
            os.chroot(self)

    if hasattr(os, 'startfile'):
        def startfile(self):
            os.startfile(self)

########NEW FILE########
__FILENAME__ = path3
#
# Copyright (c) 2010 Mikhail Gusarov
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#

""" path.py - An object representing a path to a file or directory.

Original author:
 Jason Orendorff <jason.orendorff\x40gmail\x2ecom>

Contributors:
 Mikhail Gusarov <dottedmag@dottedmag.net>
 Marc Abramowitz <marc@marc-abramowitz.com>

Example:

from path import path
d = path('/home/guido/bin')
for f in d.files('*.py'):
    f.chmod(0755)

This module requires Python 2.3 or later.
"""



import sys
import warnings
import os
import fnmatch
import glob
import shutil
import codecs
import hashlib
import errno

__version__ = '2.4'
__all__ = ['path']

# Platform-specific support for path.owner
if os.name == 'nt':
    try:
        import win32security
    except ImportError:
        win32security = None
else:
    try:
        import pwd
    except ImportError:
        pwd = None

# Pre-2.3 support.  Are unicode filenames supported?
_base = str
_getcwd = os.getcwd
try:
    if os.path.supports_unicode_filenames:
        _base = str
        _getcwd = os.getcwd
except AttributeError:
    pass

# Pre-2.3 workaround for basestring.
try:
    str
except NameError:
    str = (str, str)

# Universal newline support
_textmode = 'U'
if hasattr(__builtins__, 'file') and not hasattr(file, 'newlines'):
    _textmode = 'r'

class TreeWalkWarning(Warning):
    pass

class path(_base):
    """ Represents a filesystem path.

    For documentation on individual methods, consult their
    counterparts in os.path.
    """

    # --- Special Python methods.

    def __repr__(self):
        return 'path(%s)' % _base.__repr__(self)

    # Adding a path and a string yields a path.
    def __add__(self, more):
        try:
            resultStr = _base.__add__(self, more)
        except TypeError:  # Python bug
            resultStr = NotImplemented
        if resultStr is NotImplemented:
            return resultStr
        return self.__class__(resultStr)

    def __radd__(self, other):
        if isinstance(other, str):
            return self.__class__(other.__add__(self))
        else:
            return NotImplemented

    # The / operator joins paths.
    def __div__(self, rel):
        """ fp.__div__(rel) == fp / rel == fp.joinpath(rel)

        Join two path components, adding a separator character if
        needed.
        """
        return self.__class__(os.path.join(self, rel))

    # Make the / operator work even when true division is enabled.
    __truediv__ = __div__

    def __enter__(self):
        self._old_dir = self.getcwd()
        os.chdir(self)

    def __exit__(self, *_):
        os.chdir(self._old_dir)

    def getcwd(cls):
        """ Return the current working directory as a path object. """
        return cls(_getcwd())
    getcwd = classmethod(getcwd)

    #
    # --- Operations on path strings.

    def abspath(self):       return self.__class__(os.path.abspath(self))
    def normcase(self):      return self.__class__(os.path.normcase(self))
    def normpath(self):      return self.__class__(os.path.normpath(self))
    def realpath(self):      return self.__class__(os.path.realpath(self))
    def expanduser(self):    return self.__class__(os.path.expanduser(self))
    def expandvars(self):    return self.__class__(os.path.expandvars(self))
    def dirname(self):       return self.__class__(os.path.dirname(self))
    def basename(self):      return self.__class__(os.path.basename(self))

    def expand(self):
        """ Clean up a filename by calling expandvars(),
        expanduser(), and normpath() on it.

        This is commonly everything needed to clean up a filename
        read from a configuration file, for example.
        """
        return self.expandvars().expanduser().normpath()

    def _get_namebase(self):
        base, ext = os.path.splitext(self.name)
        return base

    def _get_ext(self):
        f, ext = os.path.splitext(_base(self))
        return ext

    def _get_drive(self):
        drive, r = os.path.splitdrive(self)
        return self.__class__(drive)

    parent = property(
        dirname, None, None,
        """ This path's parent directory, as a new path object.

        For example, path('/usr/local/lib/libpython.so').parent == path('/usr/local/lib')
        """)

    name = property(
        basename, None, None,
        """ The name of this file or directory without the full path.

        For example, path('/usr/local/lib/libpython.so').name == 'libpython.so'
        """)

    namebase = property(
        _get_namebase, None, None,
        """ The same as path.name, but with one file extension stripped off.

        For example, path('/home/guido/python.tar.gz').name     == 'python.tar.gz',
        but          path('/home/guido/python.tar.gz').namebase == 'python.tar'
        """)

    ext = property(
        _get_ext, None, None,
        """ The file extension, for example '.py'. """)

    drive = property(
        _get_drive, None, None,
        """ The drive specifier, for example 'C:'.
        This is always empty on systems that don't use drive specifiers.
        """)

    def splitpath(self):
        """ p.splitpath() -> Return (p.parent, p.name). """
        parent, child = os.path.split(self)
        return self.__class__(parent), child

    def splitdrive(self):
        """ p.splitdrive() -> Return (p.drive, <the rest of p>).

        Split the drive specifier from this path.  If there is
        no drive specifier, p.drive is empty, so the return value
        is simply (path(''), p).  This is always the case on Unix.
        """
        drive, rel = os.path.splitdrive(self)
        return self.__class__(drive), rel

    def splitext(self):
        """ p.splitext() -> Return (p.stripext(), p.ext).

        Split the filename extension from this path and return
        the two parts.  Either part may be empty.

        The extension is everything from '.' to the end of the
        last path segment.  This has the property that if
        (a, b) == p.splitext(), then a + b == p.
        """
        filename, ext = os.path.splitext(self)
        return self.__class__(filename), ext

    def stripext(self):
        """ p.stripext() -> Remove one file extension from the path.

        For example, path('/home/guido/python.tar.gz').stripext()
        returns path('/home/guido/python.tar').
        """
        return self.splitext()[0]

    if hasattr(os.path, 'splitunc'):
        def splitunc(self):
            unc, rest = os.path.splitunc(self)
            return self.__class__(unc), rest

        def _get_uncshare(self):
            unc, r = os.path.splitunc(self)
            return self.__class__(unc)

        uncshare = property(
            _get_uncshare, None, None,
            """ The UNC mount point for this path.
            This is empty for paths on local drives. """)

    def joinpath(self, *args):
        """ Join two or more path components, adding a separator
        character (os.sep) if needed.  Returns a new path
        object.
        """
        return self.__class__(os.path.join(self, *args))

    def splitall(self):
        r""" Return a list of the path components in this path.

        The first item in the list will be a path.  Its value will be
        either os.curdir, os.pardir, empty, or the root directory of
        this path (for example, '/' or 'C:\\').  The other items in
        the list will be strings.

        path.path.joinpath(*result) will yield the original path.
        """
        parts = []
        loc = self
        while loc != os.curdir and loc != os.pardir:
            prev = loc
            loc, child = prev.splitpath()
            if loc == prev:
                break
            parts.append(child)
        parts.append(loc)
        parts.reverse()
        return parts

    def relpath(self):
        """ Return this path as a relative path,
        based from the current working directory.
        """
        cwd = self.__class__(os.getcwd())
        return cwd.relpathto(self)

    def relpathto(self, dest):
        """ Return a relative path from self to dest.

        If there is no relative path from self to dest, for example if
        they reside on different drives in Windows, then this returns
        dest.abspath().
        """
        origin = self.abspath()
        dest = self.__class__(dest).abspath()

        orig_list = origin.normcase().splitall()
        # Don't normcase dest!  We want to preserve the case.
        dest_list = dest.splitall()

        if orig_list[0] != os.path.normcase(dest_list[0]):
            # Can't get here from there.
            return dest

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
            relpath = os.curdir
        else:
            relpath = os.path.join(*segments)
        return self.__class__(relpath)

    # --- Listing, searching, walking, and matching

    def listdir(self, pattern=None):
        """ D.listdir() -> List of items in this directory.

        Use D.files() or D.dirs() instead if you want a listing
        of just files or just subdirectories.

        The elements of the list are path objects.

        With the optional 'pattern' argument, this only lists
        items whose names match the given pattern.
        """
        names = os.listdir(self)
        if pattern is not None:
            names = fnmatch.filter(names, pattern)
        return [self / child for child in names]

    def dirs(self, pattern=None):
        """ D.dirs() -> List of this directory's subdirectories.

        The elements of the list are path objects.
        This does not walk recursively into subdirectories
        (but see path.walkdirs).

        With the optional 'pattern' argument, this only lists
        directories whose names match the given pattern.  For
        example, d.dirs('build-*').
        """
        return [p for p in self.listdir(pattern) if p.isdir()]

    def files(self, pattern=None):
        """ D.files() -> List of the files in this directory.

        The elements of the list are path objects.
        This does not walk into subdirectories (see path.walkfiles).

        With the optional 'pattern' argument, this only lists files
        whose names match the given pattern.  For example,
        d.files('*.pyc').
        """

        return [p for p in self.listdir(pattern) if p.isfile()]

    def walk(self, pattern=None, errors='strict'):
        """ D.walk() -> iterator over files and subdirs, recursively.

        The iterator yields path objects naming each child item of
        this directory and its descendants.  This requires that
        D.isdir().

        This performs a depth-first traversal of the directory tree.
        Each directory is returned just before all its children.

        The errors= keyword argument controls behavior when an
        error occurs.  The default is 'strict', which causes an
        exception.  The other allowed values are 'warn', which
        reports the error via warnings.warn(), and 'ignore'.
        """
        if errors not in ('strict', 'warn', 'ignore'):
            raise ValueError("invalid errors parameter")

        try:
            childList = self.listdir()
        except Exception:
            if errors == 'ignore':
                return
            elif errors == 'warn':
                warnings.warn(
                    "Unable to list directory '%s': %s"
                    % (self, sys.exc_info()[1]),
                    TreeWalkWarning)
                return
            else:
                raise

        for child in childList:
            if pattern is None or child.fnmatch(pattern):
                yield child
            try:
                isdir = child.isdir()
            except Exception:
                if errors == 'ignore':
                    isdir = False
                elif errors == 'warn':
                    warnings.warn(
                        "Unable to access '%s': %s"
                        % (child, sys.exc_info()[1]),
                        TreeWalkWarning)
                    isdir = False
                else:
                    raise

            if isdir:
                for item in child.walk(pattern, errors):
                    yield item

    def walkdirs(self, pattern=None, errors='strict'):
        """ D.walkdirs() -> iterator over subdirs, recursively.

        With the optional 'pattern' argument, this yields only
        directories whose names match the given pattern.  For
        example, mydir.walkdirs('*test') yields only directories
        with names ending in 'test'.

        The errors= keyword argument controls behavior when an
        error occurs.  The default is 'strict', which causes an
        exception.  The other allowed values are 'warn', which
        reports the error via warnings.warn(), and 'ignore'.
        """
        if errors not in ('strict', 'warn', 'ignore'):
            raise ValueError("invalid errors parameter")

        try:
            dirs = self.dirs()
        except Exception:
            if errors == 'ignore':
                return
            elif errors == 'warn':
                warnings.warn(
                    "Unable to list directory '%s': %s"
                    % (self, sys.exc_info()[1]),
                    TreeWalkWarning)
                return
            else:
                raise

        for child in dirs:
            if pattern is None or child.fnmatch(pattern):
                yield child
            for subsubdir in child.walkdirs(pattern, errors):
                yield subsubdir

    def walkfiles(self, pattern=None, errors='strict'):
        """ D.walkfiles() -> iterator over files in D, recursively.

        The optional argument, pattern, limits the results to files
        with names that match the pattern.  For example,
        mydir.walkfiles('*.tmp') yields only files with the .tmp
        extension.
        """
        if errors not in ('strict', 'warn', 'ignore'):
            raise ValueError("invalid errors parameter")

        try:
            childList = self.listdir()
        except Exception:
            if errors == 'ignore':
                return
            elif errors == 'warn':
                warnings.warn(
                    "Unable to list directory '%s': %s"
                    % (self, sys.exc_info()[1]),
                    TreeWalkWarning)
                return
            else:
                raise

        for child in childList:
            try:
                isfile = child.isfile()
                isdir = not isfile and child.isdir()
            except:
                if errors == 'ignore':
                    continue
                elif errors == 'warn':
                    warnings.warn(
                        "Unable to access '%s': %s"
                        % (self, sys.exc_info()[1]),
                        TreeWalkWarning)
                    continue
                else:
                    raise

            if isfile:
                if pattern is None or child.fnmatch(pattern):
                    yield child
            elif isdir:
                for f in child.walkfiles(pattern, errors):
                    yield f

    def fnmatch(self, pattern):
        """ Return True if self.name matches the given pattern.

        pattern - A filename pattern with wildcards,
            for example '*.py'.
        """
        return fnmatch.fnmatch(self.name, pattern)

    def glob(self, pattern):
        """ Return a list of path objects that match the pattern.

        pattern - a path relative to this directory, with wildcards.

        For example, path('/users').glob('*/bin/*') returns a list
        of all the files users have in their bin directories.
        """
        cls = self.__class__
        return [cls(s) for s in glob.glob(_base(self / pattern))]

    #
    # --- Reading or writing an entire file at once.

    def open(self, mode='r'):
        """ Open this file.  Return a file object. """
        return open(self, mode)

    def bytes(self):
        """ Open this file, read all bytes, return them as a string. """
        f = self.open('rb')
        try:
            return f.read()
        finally:
            f.close()

    def write_bytes(self, bytes, append=False):
        """ Open this file and write the given bytes to it.

        Default behavior is to overwrite any existing file.
        Call p.write_bytes(bytes, append=True) to append instead.
        """
        if append:
            mode = 'ab'
        else:
            mode = 'wb'
        f = self.open(mode)
        try:
            f.write(bytes)
        finally:
            f.close()

    def text(self, encoding=None, errors='strict'):
        r""" Open this file, read it in, return the content as a string.

        This uses 'U' mode in Python 2.3 and later, so '\r\n' and '\r'
        are automatically translated to '\n'.

        Optional arguments:

        encoding - The Unicode encoding (or character set) of
            the file.  If present, the content of the file is
            decoded and returned as a unicode object; otherwise
            it is returned as an 8-bit str.
        errors - How to handle Unicode errors; see help(str.decode)
            for the options.  Default is 'strict'.
        """
        if encoding is None:
            # 8-bit
            f = self.open(_textmode)
            try:
                return f.read()
            finally:
                f.close()
        else:
            # Unicode
            f = codecs.open(self, 'r', encoding, errors)
            # (Note - Can't use 'U' mode here, since codecs.open
            # doesn't support 'U' mode, even in Python 2.3.)
            try:
                t = f.read()
            finally:
                f.close()
            return (t.replace('\r\n', '\n')
                     .replace('\r\x85', '\n')
                     .replace('\r', '\n')
                     .replace('\x85', '\n')
                     .replace('\u2028', '\n'))

    def write_text(self, text, encoding=None, errors='strict', linesep=os.linesep, append=False):
        r""" Write the given text to this file.

        The default behavior is to overwrite any existing file;
        to append instead, use the 'append=True' keyword argument.

        There are two differences between path.write_text() and
        path.write_bytes(): newline handling and Unicode handling.
        See below.

        Parameters:

          - text - str/unicode - The text to be written.

          - encoding - str - The Unicode encoding that will be used.
            This is ignored if 'text' isn't a Unicode string.

          - errors - str - How to handle Unicode encoding errors.
            Default is 'strict'.  See help(unicode.encode) for the
            options.  This is ignored if 'text' isn't a Unicode
            string.

          - linesep - keyword argument - str/unicode - The sequence of
            characters to be used to mark end-of-line.  The default is
            os.linesep.  You can also specify None; this means to
            leave all newlines as they are in 'text'.

          - append - keyword argument - bool - Specifies what to do if
            the file already exists (True: append to the end of it;
            False: overwrite it.)  The default is False.


        --- Newline handling.

        write_text() converts all standard end-of-line sequences
        ('\n', '\r', and '\r\n') to your platform's default end-of-line
        sequence (see os.linesep; on Windows, for example, the
        end-of-line marker is '\r\n').

        If you don't like your platform's default, you can override it
        using the 'linesep=' keyword argument.  If you specifically want
        write_text() to preserve the newlines as-is, use 'linesep=None'.

        This applies to Unicode text the same as to 8-bit text, except
        there are three additional standard Unicode end-of-line sequences:
        u'\x85', u'\r\x85', and u'\u2028'.

        (This is slightly different from when you open a file for
        writing with fopen(filename, "w") in C or open(filename, 'w')
        in Python.)


        --- Unicode

        If 'text' isn't Unicode, then apart from newline handling, the
        bytes are written verbatim to the file.  The 'encoding' and
        'errors' arguments are not used and must be omitted.

        If 'text' is Unicode, it is first converted to bytes using the
        specified 'encoding' (or the default encoding if 'encoding'
        isn't specified).  The 'errors' argument applies only to this
        conversion.

        """
        if isinstance(text, str):
            if linesep is not None:
                # Convert all standard end-of-line sequences to
                # ordinary newline characters.
                text = (text.replace('\r\n', '\n')
                            .replace('\r\x85', '\n')
                            .replace('\r', '\n')
                            .replace('\x85', '\n')
                            .replace('\u2028', '\n'))
                text = text.replace('\n', linesep)
            if encoding is None:
                encoding = sys.getdefaultencoding()
            bytes = text.encode(encoding, errors)
        else:
            # It is an error to specify an encoding if 'text' is
            # an 8-bit string.
            assert encoding is None

            if linesep is not None:
                text = (text.replace('\r\n', '\n')
                            .replace('\r', '\n'))
                bytes = text.replace('\n', linesep)

        self.write_bytes(bytes, append)

    def lines(self, encoding=None, errors='strict', retain=True):
        r""" Open this file, read all lines, return them in a list.

        Optional arguments:
            encoding - The Unicode encoding (or character set) of
                the file.  The default is None, meaning the content
                of the file is read as 8-bit characters and returned
                as a list of (non-Unicode) str objects.
            errors - How to handle Unicode errors; see help(str.decode)
                for the options.  Default is 'strict'
            retain - If true, retain newline characters; but all newline
                character combinations ('\r', '\n', '\r\n') are
                translated to '\n'.  If false, newline characters are
                stripped off.  Default is True.

        This uses 'U' mode in Python 2.3 and later.
        """
        if encoding is None and retain:
            f = self.open(_textmode)
            try:
                return f.readlines()
            finally:
                f.close()
        else:
            return self.text(encoding, errors).splitlines(retain)

    def write_lines(self, lines, encoding=None, errors='strict',
                    linesep=os.linesep, append=False):
        r""" Write the given lines of text to this file.

        By default this overwrites any existing file at this path.

        This puts a platform-specific newline sequence on every line.
        See 'linesep' below.

        lines - A list of strings.

        encoding - A Unicode encoding to use.  This applies only if
            'lines' contains any Unicode strings.

        errors - How to handle errors in Unicode encoding.  This
            also applies only to Unicode strings.

        linesep - The desired line-ending.  This line-ending is
            applied to every line.  If a line already has any
            standard line ending ('\r', '\n', '\r\n', u'\x85',
            u'\r\x85', u'\u2028'), that will be stripped off and
            this will be used instead.  The default is os.linesep,
            which is platform-dependent ('\r\n' on Windows, '\n' on
            Unix, etc.)  Specify None to write the lines as-is,
            like file.writelines().

        Use the keyword argument append=True to append lines to the
        file.  The default is to overwrite the file.  Warning:
        When you use this with Unicode data, if the encoding of the
        existing data in the file is different from the encoding
        you specify with the encoding= parameter, the result is
        mixed-encoding data, which can really confuse someone trying
        to read the file later.
        """
        if append:
            mode = 'ab'
        else:
            mode = 'wb'
        f = self.open(mode)
        try:
            for line in lines:
                isUnicode = isinstance(line, str)
                if linesep is not None:
                    # Strip off any existing line-end and add the
                    # specified linesep string.
                    if isUnicode:
                        if line[-2:] in ('\r\n', '\x0d\x85'):
                            line = line[:-2]
                        elif line[-1:] in ('\r', '\n',
                                           '\x85', '\u2028'):
                            line = line[:-1]
                    else:
                        if line[-2:] == '\r\n':
                            line = line[:-2]
                        elif line[-1:] in ('\r', '\n'):
                            line = line[:-1]
                    line += linesep
                if isUnicode:
                    if encoding is None:
                        encoding = sys.getdefaultencoding()
                    line = line.encode(encoding, errors)
                f.write(line)
        finally:
            f.close()

    def read_md5(self):
        """ Calculate the md5 hash for this file.

        This reads through the entire file.
        """
        return self.read_hash('md5')

    def _hash(self, hash_name):
        f = self.open('rb')
        try:
            m = hashlib.new(hash_name)
            while True:
                d = f.read(8192)
                if not d:
                    break
                m.update(d)
            return m
        finally:
            f.close()

    def read_hash(self, hash_name):
        """ Calculate given hash for this file.

        List of supported hashes can be obtained from hashlib package. This
        reads the entire file.
        """
        return self._hash(hash_name).digest()

    def read_hexhash(self, hash_name):
        """ Calculate given hash for this file, returning hexdigest.

        List of supported hashes can be obtained from hashlib package. This
        reads the entire file.
        """
        return self._hash(hash_name).hexdigest()

    # --- Methods for querying the filesystem.
    # N.B. On some platforms, the os.path functions may be implemented in C
    # (e.g. isdir on Windows, Python 3.2.2), and compiled functions don't get
    # bound. Playing it safe and wrapping them all in method calls.

    def isabs(self): return os.path.isabs(self)
    def exists(self): return os.path.exists(self)
    def isdir(self): return os.path.isdir(self)
    def isfile(self): return os.path.isfile(self)
    def islink(self): return os.path.islink(self)
    def ismount(self): return os.path.ismount(self)

    if hasattr(os.path, 'samefile'):
        def samefile(self, otherfile): return os.path.samefile(self, otherfile)

    def getatime(self): return os.path.getatime(self)
    atime = property(
        getatime, None, None,
        """ Last access time of the file. """)

    def getmtime(self): return os.path.getmtime(self)
    mtime = property(
        getmtime, None, None,
        """ Last-modified time of the file. """)

    if hasattr(os.path, 'getctime'):
        def getctime(self): return os.path.getctime(self)
        ctime = property(
            getctime, None, None,
            """ Creation time of the file. """)

    def getsize(self): return os.path.getsize(self)
    size = property(
        getsize, None, None,
        """ Size of the file, in bytes. """)

    if hasattr(os, 'access'):
        def access(self, mode):
            """ Return true if current user has access to this path.

            mode - One of the constants os.F_OK, os.R_OK, os.W_OK, os.X_OK
            """
            return os.access(self, mode)

    def stat(self):
        """ Perform a stat() system call on this path. """
        return os.stat(self)

    def lstat(self):
        """ Like path.stat(), but do not follow symbolic links. """
        return os.lstat(self)

    def get_owner(self):
        r""" Return the name of the owner of this file or directory.

        This follows symbolic links.

        On Windows, this returns a name of the form ur'DOMAIN\User Name'.
        On Windows, a group can own a file or directory.
        """
        if os.name == 'nt':
            if win32security is None:
                raise Exception("path.owner requires win32all to be installed")
            desc = win32security.GetFileSecurity(
                self, win32security.OWNER_SECURITY_INFORMATION)
            sid = desc.GetSecurityDescriptorOwner()
            account, domain, typecode = win32security.LookupAccountSid(None, sid)
            return domain + '\\' + account
        else:
            if pwd is None:
                raise NotImplementedError("path.owner is not implemented on this platform.")
            st = self.stat()
            return pwd.getpwuid(st.st_uid).pw_name

    owner = property(
        get_owner, None, None,
        """ Name of the owner of this file or directory. """)

    if hasattr(os, 'statvfs'):
        def statvfs(self):
            """ Perform a statvfs() system call on this path. """
            return os.statvfs(self)

    if hasattr(os, 'pathconf'):
        def pathconf(self, name):
            return os.pathconf(self, name)

    #
    # --- Modifying operations on files and directories

    def utime(self, times):
        """ Set the access and modified times of this file. """
        os.utime(self, times)

    def chmod(self, mode):
        os.chmod(self, mode)

    if hasattr(os, 'chown'):
        def chown(self, uid, gid):
            os.chown(self, uid, gid)

    def rename(self, new):
        os.rename(self, new)

    def renames(self, new):
        os.renames(self, new)

    #
    # --- Create/delete operations on directories

    def mkdir(self, mode=0o777):
        if not self.exists():
            os.mkdir(self, mode)

    def mkdir_p(self, mode=0o777):
        try:
            self.mkdir(mode)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

    def makedirs(self, mode=0o777):
        if not self.exists():
            os.makedirs(self, mode)

    def makedirs_p(self, mode=0o777):
        try:
            self.makedirs(mode)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

    def rmdir(self):
        if self.exists():
            os.rmdir(self)

    def rmdir_p(self):
        try:
            self.rmdir()
        except OSError as e:
            if e.errno != errno.ENOTEMPTY and e.errno != errno.EEXIST:
                raise

    def removedirs(self):
        if self.exists():
            os.removedirs(self)

    def removedirs_p(self):
        try:
            self.removedirs()
        except OSError as e:
            if e.errno != errno.ENOTEMPTY and e.errno != errno.EEXIST:
                raise

    # --- Modifying operations on files

    def touch(self):
        """ Set the access/modified times of this file to the current time.
        Create the file if it does not exist.
        """
        fd = os.open(self, os.O_WRONLY | os.O_CREAT, 0o666)
        os.close(fd)
        os.utime(self, None)

    def remove(self):
        if self.exists():
            os.remove(self)

    def remove_p(self):
        try:
            self.unlink()
        except OSError as e:
            if e.errno != errno.ENOENT:
                raise

    def unlink(self):
        if not self.exists():
            os.unlink(self)

    def unlink_p(self):
        self.remove_p()

    # --- Links

    if hasattr(os, 'link'):
        def link(self, newpath):
            """ Create a hard link at 'newpath', pointing to this file. """
            os.link(self, newpath)

    if hasattr(os, 'symlink'):
        def symlink(self, newlink):
            """ Create a symbolic link at 'newlink', pointing here. """
            os.symlink(self, newlink)

    if hasattr(os, 'readlink'):
        def readlink(self):
            """ Return the path to which this symbolic link points.

            The result may be an absolute or a relative path.
            """
            return self.__class__(os.readlink(self))

        def readlinkabs(self):
            """ Return the path to which this symbolic link points.

            The result is always an absolute path.
            """
            p = self.readlink()
            if p.isabs():
                return p
            else:
                return (self.parent / p).abspath()

    #
    # --- High-level functions from shutil

    copyfile = shutil.copyfile
    copymode = shutil.copymode
    copystat = shutil.copystat
    copy = shutil.copy
    copy2 = shutil.copy2
    copytree = shutil.copytree
    if hasattr(shutil, 'move'):
        move = shutil.move

    def rmtree(self, *args, **kw):
        if self.exists():
            shutil.rmtree(self, *args, **kw)

    def rmtree_p(self):
        try:
            self.rmtree()
        except OSError as e:
            if e.errno != errno.ENOENT:
                raise

    #
    # --- Special stuff from os

    if hasattr(os, 'chroot'):
        def chroot(self):
            os.chroot(self)

    if hasattr(os, 'startfile'):
        def startfile(self):
            os.startfile(self)

########NEW FILE########
__FILENAME__ = six
"""Utilities for writing code that runs on Python 2 and 3"""

import operator
import sys
import types

__author__ = "Benjamin Peterson <benjamin@python.org>"
__version__ = "1.2.0"


# True if we are running on Python 3.
PY3 = sys.version_info[0] == 3

if PY3:
    string_types = str,
    integer_types = int,
    class_types = type,
    text_type = str
    binary_type = bytes

    MAXSIZE = sys.maxsize
else:
    string_types = basestring,
    integer_types = (int, long)
    class_types = (type, types.ClassType)
    text_type = unicode
    binary_type = str

    if sys.platform.startswith("java"):
        # Jython always uses 32 bits.
        MAXSIZE = int((1 << 31) - 1)
    else:
        # It's possible to have sizeof(long) != sizeof(Py_ssize_t).
        class X(object):
            def __len__(self):
                return 1 << 31
        try:
            len(X())
        except OverflowError:
            # 32-bit
            MAXSIZE = int((1 << 31) - 1)
        else:
            # 64-bit
            MAXSIZE = int((1 << 63) - 1)
            del X


def _add_doc(func, doc):
    """Add documentation to a function."""
    func.__doc__ = doc


def _import_module(name):
    """Import module, returning the module after the last dot."""
    __import__(name)
    return sys.modules[name]


class _LazyDescr(object):

    def __init__(self, name):
        self.name = name

    def __get__(self, obj, tp):
        result = self._resolve()
        setattr(obj, self.name, result)
        # This is a bit ugly, but it avoids running this again.
        delattr(tp, self.name)
        return result


class MovedModule(_LazyDescr):

    def __init__(self, name, old, new=None):
        super(MovedModule, self).__init__(name)
        if PY3:
            if new is None:
                new = name
            self.mod = new
        else:
            self.mod = old

    def _resolve(self):
        return _import_module(self.mod)


class MovedAttribute(_LazyDescr):

    def __init__(self, name, old_mod, new_mod, old_attr=None, new_attr=None):
        super(MovedAttribute, self).__init__(name)
        if PY3:
            if new_mod is None:
                new_mod = name
            self.mod = new_mod
            if new_attr is None:
                if old_attr is None:
                    new_attr = name
                else:
                    new_attr = old_attr
            self.attr = new_attr
        else:
            self.mod = old_mod
            if old_attr is None:
                old_attr = name
            self.attr = old_attr

    def _resolve(self):
        module = _import_module(self.mod)
        return getattr(module, self.attr)



class _MovedItems(types.ModuleType):
    """Lazy loading of moved objects"""


_moved_attributes = [
    MovedAttribute("cStringIO", "cStringIO", "io", "StringIO"),
    MovedAttribute("filter", "itertools", "builtins", "ifilter", "filter"),
    MovedAttribute("input", "__builtin__", "builtins", "raw_input", "input"),
    MovedAttribute("map", "itertools", "builtins", "imap", "map"),
    MovedAttribute("reload_module", "__builtin__", "imp", "reload"),
    MovedAttribute("reduce", "__builtin__", "functools"),
    MovedAttribute("StringIO", "StringIO", "io"),
    MovedAttribute("xrange", "__builtin__", "builtins", "xrange", "range"),
    MovedAttribute("zip", "itertools", "builtins", "izip", "zip"),

    MovedModule("builtins", "__builtin__"),
    MovedModule("configparser", "ConfigParser"),
    MovedModule("copyreg", "copy_reg"),
    MovedModule("http_cookiejar", "cookielib", "http.cookiejar"),
    MovedModule("http_cookies", "Cookie", "http.cookies"),
    MovedModule("html_entities", "htmlentitydefs", "html.entities"),
    MovedModule("html_parser", "HTMLParser", "html.parser"),
    MovedModule("http_client", "httplib", "http.client"),
    MovedModule("BaseHTTPServer", "BaseHTTPServer", "http.server"),
    MovedModule("CGIHTTPServer", "CGIHTTPServer", "http.server"),
    MovedModule("SimpleHTTPServer", "SimpleHTTPServer", "http.server"),
    MovedModule("cPickle", "cPickle", "pickle"),
    MovedModule("queue", "Queue"),
    MovedModule("reprlib", "repr"),
    MovedModule("socketserver", "SocketServer"),
    MovedModule("tkinter", "Tkinter"),
    MovedModule("tkinter_dialog", "Dialog", "tkinter.dialog"),
    MovedModule("tkinter_filedialog", "FileDialog", "tkinter.filedialog"),
    MovedModule("tkinter_scrolledtext", "ScrolledText", "tkinter.scrolledtext"),
    MovedModule("tkinter_simpledialog", "SimpleDialog", "tkinter.simpledialog"),
    MovedModule("tkinter_tix", "Tix", "tkinter.tix"),
    MovedModule("tkinter_constants", "Tkconstants", "tkinter.constants"),
    MovedModule("tkinter_dnd", "Tkdnd", "tkinter.dnd"),
    MovedModule("tkinter_colorchooser", "tkColorChooser",
                "tkinter.colorchooser"),
    MovedModule("tkinter_commondialog", "tkCommonDialog",
                "tkinter.commondialog"),
    MovedModule("tkinter_tkfiledialog", "tkFileDialog", "tkinter.filedialog"),
    MovedModule("tkinter_font", "tkFont", "tkinter.font"),
    MovedModule("tkinter_messagebox", "tkMessageBox", "tkinter.messagebox"),
    MovedModule("tkinter_tksimpledialog", "tkSimpleDialog",
                "tkinter.simpledialog"),
    MovedModule("urllib_robotparser", "robotparser", "urllib.robotparser"),
    MovedModule("winreg", "_winreg"),
]
for attr in _moved_attributes:
    setattr(_MovedItems, attr.name, attr)
del attr

moves = sys.modules["six.moves"] = _MovedItems("moves")


def add_move(move):
    """Add an item to six.moves."""
    setattr(_MovedItems, move.name, move)


def remove_move(name):
    """Remove item from six.moves."""
    try:
        delattr(_MovedItems, name)
    except AttributeError:
        try:
            del moves.__dict__[name]
        except KeyError:
            raise AttributeError("no such move, %r" % (name,))


if PY3:
    _meth_func = "__func__"
    _meth_self = "__self__"

    _func_code = "__code__"
    _func_defaults = "__defaults__"

    _iterkeys = "keys"
    _itervalues = "values"
    _iteritems = "items"
else:
    _meth_func = "im_func"
    _meth_self = "im_self"

    _func_code = "func_code"
    _func_defaults = "func_defaults"

    _iterkeys = "iterkeys"
    _itervalues = "itervalues"
    _iteritems = "iteritems"


try:
    advance_iterator = next
except NameError:
    def advance_iterator(it):
        return it.next()
next = advance_iterator


if PY3:
    def get_unbound_function(unbound):
        return unbound

    Iterator = object

    def callable(obj):
        return any("__call__" in klass.__dict__ for klass in type(obj).__mro__)
else:
    def get_unbound_function(unbound):
        return unbound.im_func

    class Iterator(object):

        def next(self):
            return type(self).__next__(self)

    callable = callable
_add_doc(get_unbound_function,
         """Get the function out of a possibly unbound function""")


get_method_function = operator.attrgetter(_meth_func)
get_method_self = operator.attrgetter(_meth_self)
get_function_code = operator.attrgetter(_func_code)
get_function_defaults = operator.attrgetter(_func_defaults)


def iterkeys(d):
    """Return an iterator over the keys of a dictionary."""
    return iter(getattr(d, _iterkeys)())

def itervalues(d):
    """Return an iterator over the values of a dictionary."""
    return iter(getattr(d, _itervalues)())

def iteritems(d):
    """Return an iterator over the (key, value) pairs of a dictionary."""
    return iter(getattr(d, _iteritems)())


if PY3:
    def b(s):
        return s.encode("latin-1")
    def u(s):
        return s
    if sys.version_info[1] <= 1:
        def int2byte(i):
            return bytes((i,))
    else:
        # This is about 2x faster than the implementation above on 3.2+
        int2byte = operator.methodcaller("to_bytes", 1, "big")
    import io
    StringIO = io.StringIO
    BytesIO = io.BytesIO
else:
    def b(s):
        return s
    def u(s):
        return unicode(s, "unicode_escape")
    int2byte = chr
    import StringIO
    StringIO = BytesIO = StringIO.StringIO
_add_doc(b, """Byte literal""")
_add_doc(u, """Text literal""")


if PY3:
    import builtins
    exec_ = getattr(builtins, "exec")


    def reraise(tp, value, tb=None):
        if value.__traceback__ is not tb:
            raise value.with_traceback(tb)
        raise value


    print_ = getattr(builtins, "print")
    del builtins

else:
    def exec_(code, globs=None, locs=None):
        """Execute code in a namespace."""
        if globs is None:
            frame = sys._getframe(1)
            globs = frame.f_globals
            if locs is None:
                locs = frame.f_locals
            del frame
        elif locs is None:
            locs = globs
        exec("""exec code in globs, locs""")


    exec_("""def reraise(tp, value, tb=None):
    raise tp, value, tb
""")


    def print_(*args, **kwargs):
        """The new-style print function."""
        fp = kwargs.pop("file", sys.stdout)
        if fp is None:
            return
        def write(data):
            if not isinstance(data, basestring):
                data = str(data)
            fp.write(data)
        want_unicode = False
        sep = kwargs.pop("sep", None)
        if sep is not None:
            if isinstance(sep, unicode):
                want_unicode = True
            elif not isinstance(sep, str):
                raise TypeError("sep must be None or a string")
        end = kwargs.pop("end", None)
        if end is not None:
            if isinstance(end, unicode):
                want_unicode = True
            elif not isinstance(end, str):
                raise TypeError("end must be None or a string")
        if kwargs:
            raise TypeError("invalid keyword arguments to print()")
        if not want_unicode:
            for arg in args:
                if isinstance(arg, unicode):
                    want_unicode = True
                    break
        if want_unicode:
            newline = unicode("\n")
            space = unicode(" ")
        else:
            newline = "\n"
            space = " "
        if sep is None:
            sep = space
        if end is None:
            end = newline
        for i, arg in enumerate(args):
            if i:
                write(sep)
            write(arg)
        write(end)

_add_doc(reraise, """Reraise an exception.""")


def with_metaclass(meta, base=object):
    """Create a base class with a metaclass."""
    return meta("NewBase", (base,), {})

########NEW FILE########
__FILENAME__ = doctools
"""Tasks and utility functions and classes for working with project
documentation."""

from __future__ import with_statement
import re

from paver.easy import *

try:
    import sphinx
    import sphinx.apidoc
    has_sphinx = True
except ImportError:
    has_sphinx = False

try:
    import cogapp
    has_cog = True
except ImportError:
    has_cog = False

def _get_paths():
    """look up the options that determine where all of the files are."""
    opts = options
    docroot = path(opts.get('docroot', 'docs'))
    if not docroot.exists():
        raise BuildFailure("Sphinx documentation root (%s) does not exist."
                           % docroot)
    builddir = docroot / opts.get("builddir", ".build")
    builddir.mkdir_p()
    srcdir = docroot / opts.get("sourcedir", "")
    if not srcdir.exists():
        raise BuildFailure("Sphinx source file dir (%s) does not exist" 
                            % srcdir)
    apidir = None
    if opts.get("apidir", "api"):
        apidir = srcdir / opts.get("apidir", "api")
        apidir.mkdir_p()
    htmldir = builddir / "html"
    htmldir.mkdir_p()
    doctrees = builddir / "doctrees"
    doctrees.mkdir_p()
    return Bunch(locals())

@task
def html():
    """Build HTML documentation using Sphinx. This uses the following
    options in a "sphinx" section of the options.

    docroot
      the root under which Sphinx will be working. Default: docs
    builddir
      directory under the docroot where the resulting files are put.
      default: .build
    sourcedir
      directory under the docroot for the source files
      default: (empty string)
    apidir
      directory under the sourcedir for the auto-generated API docs (empty = don't create them)
      default: api
    """
    if not has_sphinx:
        raise BuildFailure('install sphinx to build html docs')
    options.order('sphinx', add_rest=True)
    paths = _get_paths()

    # First, auto-gen additional sources
    if paths.apidir:
        sphinxopts = ['', '-f', '-o', paths.apidir] + options.setup.packages
        dry("sphinx-apidoc %s" % (" ".join(sphinxopts),), sphinx.apidoc.main, sphinxopts)

    # Then generate HTML tree
    sphinxopts = ['', '-b', 'html', '-d', paths.doctrees, 
        paths.srcdir, paths.htmldir]
    dry("sphinx-build %s" % (" ".join(sphinxopts),), sphinx.main, sphinxopts)

@task
def doc_clean():
    """Clean (delete) the built docs. Specifically, this deletes the
    build directory under the docroot. See the html task for the
    options list."""
    options.order('sphinx', add_rest=True)
    paths = _get_paths()
    paths.builddir.rmtree_p()
    paths.builddir.mkdir_p()
    if paths.apidir and paths.apidir != paths.srcdir:
        paths.apidir.rmtree_p()
        paths.apidir.mkdir_p()

_sectionmarker = re.compile(r'\[\[\[section\s+(.+)\]\]\]')
_endmarker = re.compile(r'\[\[\[endsection\s*.*\]\]\]')

class SectionedFile(object):
    """Loads a file into memory and keeps track of all of the
    sections found in the file. Sections are started with a
    line that looks like this::
    
      [[[section SECTIONNAME]]]
    
    Anything else can appear on the line outside of the brackets
    (so if you're in a source code file, you can put the section marker
    in a comment). The entire lines containing the section markers are
    not included when you request the text from the file.
    
    An end of section marker looks like this::
    
      [[[endsection]]]
      
    Sections can be nested. If you do nest sections, you will use
    dotted notation to refer to the inner sections. For example,
    a "dessert" section within an "order" section would be referred
    to as "order.dessert".
    
    The SectionedFile provides dictionary-style access to the
    sections. If you have a SectionedFile named 'sf',
    sf[sectionname] will give you back a string of that section
    of the file, including any inner sections. There won't
    be any section markers in that string.
    
    You can get the text of the whole file via the ``all`` property
    (for example, ``sf.all``).
    
    Section names must be unique across the file, but inner section
    names are kept track of by the full dotted name. So you can
    have a "dessert" section that is contained within two different
    outer sections.
    
    Ending a section without starting one or ending the file without
    ending a section will yield BuildFailures.
    """
    
    def __init__(self, filename=None, from_string=None):
        """Initialize this SectionedFile object from a file or string.
        If ``from_string`` is provided, that is the text that will
        be used and a filename is optional. If a filename is provided
        it will be used in error messages.
        """
        self.filename = filename
        self.contents = []
        self.sections = {}
        if from_string is not None:
            from paver.deps.six import StringIO
            self._read_file(StringIO(from_string))
        else:
            with open(filename) as f:
                self._read_file(f)
        
    def _read_file(self, f):
        """Do the work of reading the file."""
        contents = self.contents
        sections = self.sections
        real_lineno = 1
        output_lineno = 0
        
        stack = []
        line = f.readline()
        while line:
            m = _sectionmarker.search(line)
            if m:
                section = m.group(1)
                debug("Section %s found at %s (%s)", section, real_lineno, 
                      output_lineno)
                stack.append(section)
                sectionname = ".".join(stack)
                if sectionname in sections:
                    raise BuildFailure("""section '%s' redefined
(in file '%s', first section at line %s, second at line %s)""" %
                                        (sectionname, self.filename,
                                         sections[sectionname][0],
                                         real_lineno))
                sections[".".join(stack)] = [real_lineno, output_lineno]
            elif _endmarker.search(line):
                sectionname = ".".join(stack)
                try:
                    section = stack.pop()
                except IndexError:
                    raise BuildFailure("""End section marker with no starting marker
(in file '%s', at line %s)""" % (self.filename, real_lineno))
                debug("Section %s end at %s (%s)", section, real_lineno, 
                      output_lineno)
                sections[sectionname].append(output_lineno)
            else:
                contents.append(line)
                output_lineno += 1
            line = f.readline()
            real_lineno += 1
        if stack:
            section = ".".join(stack)
            raise BuildFailure("""No end marker for section '%s'
(in file '%s', starts at line %s)""" % (section, self.filename, 
                                        sections[section][0]))
    
    def __getitem__(self, key):
        """Look up a section, and return the text of the section."""
        try:
            pos = self.sections[key]
        except KeyError:
            raise BuildFailure("No section '%s' in file '%s'" %
                               (key, self.filename))
        return "".join(self.contents[pos[1]:pos[2]])
    
    def __len__(self):
        """Number of sections available in the file."""
        return len(self.sections)
    
    def keys(self):
        return self.sections.keys()
    
    @property
    def all(self):
        """Property to get access to the whole file."""
        return "".join(self.contents)

_default_include_marker = dict(
    py="# "
)

class Includer(object):
    """Looks up SectionedFiles relative to the basedir.
    
    When called with a filename and an optional section, the Includer
    will:
    
    1. look up that file relative to the basedir in a cache
    2. load it as a SectionedFile if it's not in the cache
    3. return the whole file if section is None
    4. return just the section desired if a section is requested
    
    If a cog object is provided at initialization, the text will be
    output (via cog's out) rather than returned as
    a string.
    
    You can pass in include_markers which is a dictionary that maps
    file extensions to the single line comment character for that
    file type. If there is an include marker available, then
    output like:
    
    # section 'sectionname' from 'file.py'
    
    There are some default include markers. If you don't pass
    in anything, no include markers will be displayed. If you
    pass in an empty dictionary, the default ones will
    be displayed.
    """
    def __init__(self, basedir, cog=None, include_markers=None):
        self.include_markers = {}
        if include_markers is not None:
            self.include_markers.update(_default_include_marker)
        if include_markers:
            self.include_markers.update(include_markers)
        self.basedir = path(basedir)
        self.cog = cog
        self.files = {}
    
    def __call__(self, fn, section=None):
        f = self.files.get(fn)
        if f is None:
            f = SectionedFile(self.basedir / fn)
            self.files[fn] = f
        ext = path(fn).ext.replace(".", "")
        marker = self.include_markers.get(ext)
        if section is None:
            if marker:
                value = marker + "file '" + fn + "'\n" + f.all
            else:
                value = f.all
        else:
            if marker:
                value = marker + "section '" + section + "' in file '" + fn \
                      + "'\n" + f[section]
            else:
                value = f[section]
        if self.cog:
            self.cog.cogmodule.out(value)
        else:
            return value

def _cogsh(cog):
    """The sh command used within cog. Runs the command (unless it's a dry run)
    and inserts the output into the cog output if insert_output is True."""
    def shfunc(command, insert_output=True):
        output = sh(command, capture=insert_output)
        if insert_output:
            cog.cogmodule.out(output)
    return shfunc

def _runcog(options, uncog=False):
    """Common function for the cog and runcog tasks."""
    if not has_cog:
        raise BuildFailure('install Cog to build html docs')

    options.order('cog', 'sphinx', add_rest=True)
    c = cogapp.Cog()
    if uncog:
        c.options.bNoGenerate = True
    c.options.bReplace = True
    c.options.bDeleteCode = options.get("delete_code", False)
    includedir = options.get('includedir', None)
    if includedir:
        include = Includer(includedir, cog=c, 
                           include_markers=options.get("include_markers"))
        # load cog's namespace with our convenience functions.
        c.options.defines['include'] = include
        c.options.defines['sh'] = _cogsh(c)
    
    c.options.defines.update(options.get("defines", {}))

    c.sBeginSpec = options.get('beginspec', '[[[cog')
    c.sEndSpec = options.get('endspec', ']]]')
    c.sEndOutput = options.get('endoutput', '[[[end]]]')
    
    basedir = options.get('basedir', None)
    if basedir is None:
        basedir = path(options.get('docroot', "docs")) / options.get('sourcedir', "")
    basedir = path(basedir)
        
    pattern = options.get("pattern", "*.rst")
    if pattern:
        files = basedir.walkfiles(pattern)
    else:
        files = basedir.walkfiles()
    for f in files:
        dry("cog %s" % f, c.processOneFile, f)
    

@task
def cog(options):
    """Runs the cog code generator against the files matching your 
    specification. By default, cog will run against any .rst files
    in your Sphinx document root. Full documentation for Cog is
    here:
    
    http://nedbatchelder.com/code/cog/
    
    In a nutshell, you put blocks in your file that look like
    this:
    
    [[[cog cog.outl("Hi there!")
    ]]]
    [[[end]]]
    
    Cog will replace the space between ]]] and [[[end]]] with
    the generated output. In this case, Hi there!
    
    Here are the options available for the cog task. These are
    looked up in the 'cog' options section by default. The
    'sphinx' option set is also searched.
    
    basedir
        directory to look in for files to cog. If not set,
        'docroot' is looked up.
    pattern
        file glob to look for under basedir. By default, ``*.rst``
    includedir
        If you have external files to include in your
        documentation, setting includedir to the root
        of those files will put a paver.doctools.Includer 
        in your Cog namespace as 'include'. This lets you
        easily include files and sections of files. Here's
        an example usage::

            [[[cog include('filename_under_includedir.py', 'mysection')]]]
            [[[end]]]
    defines
        Dictionary of objects added to your Cog namespace.
        (can supersede 'include' and 'sh' defined by includedir.)
    beginspec
        String used at the beginning of the code generation block.
        Default: [[[cog
    endspec
        String used at the end of the code generation block.
        Default; ]]]
    endoutput
        String used at the end of the generated output
        Default: [[[end]]]
    delete_code
        Remove the generator code. Note that this will mean that the
        files that get changed cannot be changed again since the code
        will be gone. Default: False
    include_markers
        Dictionary mapping file extensions to the single line
        comment marker for that file. There are some defaults.
        For example, 'py' maps to '# '. If there is a known
        include marker for a given file, then a comment
        will be displayed along the lines of:
        
        # section 'SECTIONNAME' in file 'foo.py'
        
        If this option is not set, these lines will not
        be displayed at all. If this option is set to an
        empty dictionary, the default include markers
        will be displayed. You can also pass in your own
        extension -> include marker settings.
    """
    _runcog(options)
    
@task
def uncog(options):
    """Remove the Cog generated code from files. Often, you will want to
    do this before committing code under source control, because you
    don't generally want generated code in your version control system.
    
    This takes the same options as the cog task. Look there for
    more information.
    """
    _runcog(options, True)

########NEW FILE########
__FILENAME__ = easy
from paver import tasks
#needed for paver.easy.* import
from paver.options import Bunch

def dry(message, func, *args, **kw):
    """Wraps a function that performs a destructive operation, so that
    nothing will happen when a dry run is requested.

    Runs func with the given arguments and keyword arguments. If this
    is a dry run, print the message rather than running the function."""
    if message is not None:
        info(message)
    if tasks.environment.dry_run:
        return
    return func(*args, **kw)

def error(message, *args):
    """Displays an error message to the user."""
    tasks.environment.error(message, *args)

def info(message, *args):
    """Displays a message to the user. If the quiet option is specified, the
    message will not be displayed."""
    tasks.environment.info(message, *args)

def debug(message, *args):
    """Displays a message to the user, but only if the verbose flag is
    set."""
    tasks.environment.debug(message, *args)

class _SimpleProxy(object):
    __initialized = False
    def __init__(self, rootobj, name):
        self.__rootobj = rootobj
        self.__name = name
        self.__initialized = True
    
    def __get_object(self):
        return getattr(self.__rootobj, self.__name)
        
    def __getattr__(self, attr):
        return getattr(self.__get_object(), attr)
    
    def __setattr__(self, attr, value):
        if self.__initialized:
            setattr(self.__get_object(), attr, value)
        else:
            super(_SimpleProxy, self).__setattr__(attr, value)
            
    def __call__(self, *args, **kw):
        return self.__get_object()(*args, **kw)
    
    def __str__(self):
        return str(self.__get_object())
    
    def __repr__(self):
        return repr(self.__get_object())

environment = _SimpleProxy(tasks, "environment")
options = _SimpleProxy(environment, "options")
call_task = _SimpleProxy(environment, "call_task")

call_pavement = tasks.call_pavement
task = tasks.task
needs = tasks.needs
might_call = tasks.might_call
cmdopts = tasks.cmdopts
consume_args = tasks.consume_args
consume_nargs = tasks.consume_nargs
no_auto = tasks.no_auto
no_help = tasks.no_help
BuildFailure = tasks.BuildFailure
PavementError = tasks.PavementError

# these are down here to avoid circular dependencies. Ideally, nothing would
# be using paver.easy other than pavements.
from paver.path import path, pushd
from paver.shell import sh

import paver.misctasks

########NEW FILE########
__FILENAME__ = git
"""Convenience functions for working with git.

This module does not include any tasks, only functions.

At this point, these functions do not use any kind of library. They require
the git binary on the path."""

from paver.easy import sh
import os, re

def _format_path(provided_path):
    return provided_path or os.getcwd()

def _split_remote_branch_name(provided_name):
    return provided_name.split("/")[1]

def clone(url, dest_folder):
    sh("git clone %(url)s %(path)s" % dict(url=url, path=dest_folder) )

def pull(destination, remote="origin", branch="master"):
    """Perform a git pull. Destination must be absolute path.
    """
    sh("cd %(destination)s; git pull %(remote)s %(branch)s" % dict(
        destination=destination, remote=remote, branch=branch) )

def branch_list(path="", remote_branches_only=False, __override__=None):
    """
    Lists git branches for the repository specified (or CWD).
    If remote_branches_only is specified will list branches that exist
    on the remote. These branches may, or may not, have corresponding remote
    tracking branches.
    
    Returns a Python tuple. The first item in the tuple will be the current
    branch, and the other item will be a list of branches for the repository.
    
    Optional parameter path: the path to the git repo. Else uses os.getcwd()
    """

    remote_branches = ""
    if remote_branches_only:
        remote_branches = "-r"
    
    if __override__ == None:
        git_output = sh(  "cd %(repo_path)s; git branch %(remote)s" % dict(
            repo_path = _format_path(path), remote = remote_branches ), capture=True  )
    else:
        git_output = __override__
    
    if git_output == None:
        return None, [] # should only hit this condition in testing...
    
    current_branch = ""
    branches = []
    found_a_match = False
    regex = re.compile(r"(\*?)\W*(.+)")
    
    for line in git_output.split("\n"):
        match_obj = regex.match(line)
        if match_obj:
            found_a_match = True
            if match_obj.group(1):
                current_branch = match_obj.group(2).strip()
            if match_obj.group(2).strip():
                branches.append( match_obj.group(2).strip() )
        
    if found_a_match is False:
        raise "git branch did not return output expected. Returned %s" % git_output
    
    return current_branch, branches

def branch_checkout(branch_name, path=""):
    """Checkout a git branch.
    
    Take the branch name to checkout, and optional path parameter
    (the path to the git repo. Else uses os.getcwd())
    """
    
    sh( "cd %(repo_path)s; git checkout %(branch_name)s" % dict(
        repo_path = _format_path(path),
        branch_name=branch_name) )
     
def branch_track_remote(remote_branch_name, local_branch_name=None, path=""):
    local_branch_name = ( local_branch_name or _split_remote_branch_name(remote_branch_name) )
    
    sh( "cd %(repo_path)s; git checkout -b %(branch_name)s --track %(remote_branch_name)s" % dict(
        repo_path = _format_path(path),
        branch_name=local_branch_name,
        remote_branch_name=remote_branch_name) )
    

########NEW FILE########
__FILENAME__ = misctasks
"""Miscellaneous tasks that don't fit into one of the other groupings."""
import pkgutil
import zipfile
import paver.deps.six as six
from os.path import join, dirname, exists, abspath
from paver.easy import dry, task
from paver.tasks import VERSION, cmdopts

_docsdir = join(dirname(__file__), "docs")
if exists(_docsdir):
    @task
    def paverdocs():
        """Open your web browser and display Paver's documentation."""
        import webbrowser
        webbrowser.open("file://%s"  % join(abspath(_docsdir), 'index.html') )
        
@task
@cmdopts([('versioned_name', '', 'Determine if minilib uses version in its name')],
            share_with=['generate_setup'])
def minilib(options):
    """Create a Paver mini library that contains enough for a simple
    pavement.py to be installed using a generated setup.py. This
    is a good temporary measure until more people have deployed paver.
    The output file is 'paver-minilib.zip' in the current directory.

    Options:

    versioned_name
        if set to True, paver version will be added into minilib's filename
        (ie paver-minilib-1.1.0.zip)
        purpose is to avoid import error while using different versions of minilib
        with easy_install
        (default False)
    
    extra_files
        list of other paver modules to include (don't include the .py
        extension). By default, the following modules are included:
        defaults, path, release, setuputils, misctasks, options,
        tasks, easy
    """
    filelist = ['__init__', 'defaults', 'release', 'path', 'version',
                'setuputils', "misctasks", "options", "tasks", "easy",
                'shell', 'deps/__init__', 'deps/path2', 'deps/path3',
                'deps/six']
    filelist.extend(options.get('extra_files', []))

    output_version = ""
    if 'versioned_name' in options:
        output_version = "-%s" % VERSION

    output_file = 'paver-minilib%s.zip' % output_version

    def generate_zip():
        # Write the mini library to a buffer.
        buf = six.BytesIO()
        destfile = zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED)
        for filename in filelist:
            destfile.writestr("paver/%s.py" % filename,
                pkgutil.get_data('paver', "%s.py" % filename))
        destfile.close()

        # Write the buffer to disk.
        f = open(output_file, "wb")
        f.write(buf.getvalue())
        f.close()
    dry("Generate %s" % output_file, generate_zip)

@task
@cmdopts([('versioned_name', '', 'Determine if setup refers to minilib with version in its name')],
            share_with=['minilib'])
def generate_setup(options):
    """Generates a setup.py file that uses paver behind the scenes. This 
    setup.py file will look in the directory that the user is running it
    in for a paver-minilib.zip and will add that to sys.path if available.
    Otherwise, it will just assume that paver is available."""
    if 'versioned_name' in options:
        minilib_name = "paver-minilib-%s.zip" % VERSION
        is_versioned_msg = ', referring versioned minilib: %s' % minilib_name
    else:
        is_versioned_msg = ""
        minilib_name = 'paver-minilib.zip'

    def write_setup():
        setup = open("setup.py", "w")
        setup.write("""try:
    import paver.tasks
except ImportError:
    from os.path import exists
    if exists("%(minilib_name)s"):
        import sys
        sys.path.insert(0, "%(minilib_name)s")
    import paver.tasks

paver.tasks.main()
""" % {'minilib_name': minilib_name})
        setup.close()

    dry("Write setup.py%s" % is_versioned_msg, write_setup)

########NEW FILE########
__FILENAME__ = options
class OptionsError(Exception):
    pass

class Bunch(dict):
    """A dictionary that provides attribute-style access."""

    def __repr__(self):
        keys = list(self.keys())
        keys.sort()
        args = ', '.join(['%s=%r' % (key, self[key]) for key in keys])
        return '%s(%s)' % (self.__class__.__name__, args)
    
    def __getitem__(self, key):
        item = dict.__getitem__(self, key)
        if callable(item):
            return item()
        return item

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)

    __setattr__ = dict.__setitem__

    def __delattr__(self, name):
        try:
            del self[name]
        except KeyError:
            raise AttributeError(name)

class Namespace(Bunch):
    """A Bunch that will search dictionaries contained within to find a value.
    The search order is set via the order() method. See the order method for
    more information about search order.
    """
    def __init__(self, d=None, **kw):
        self._sections = []
        self._ordering = None
        self.update(d, **kw)
    
    def order(self, *keys, **kw):
        """Set the search order for this namespace. The arguments
        should be the list of keys in the order you wish to search,
        or a dictionary/Bunch that you want to search.
        Keys that are left out will not be searched. If you pass in
        no arguments, then the default ordering will be used. (The default
        is to search the global space first, then in the order in
        which the sections were created.)
        
        If you pass in a key name that is not a section, that
        key will be silently removed from the list.
        
        Keyword arguments are:
        
        add_rest=False
            put the sections you list at the front of the search
            and add the remaining sections to the end
        """
        if not keys:
            self._ordering = None
            return
        
        order = []
        for item in keys:
            if isinstance(item, dict) or item in self._sections:
                order.append(item)
        
        if kw.get('add_rest'):
            # this is not efficient. do we care? probably not.
            for item in self._sections:
                if item not in order:
                    order.append(item)
        self._ordering = order
        
    def clear(self):
        self._ordering = None
        self._sections = []
        super(Namespace, self).clear()
    
    def setdotted(self, key, value):
        """Sets a namespace key, value pair where the key
        can use dotted notation to set sub-values. For example,
        the key "foo.bar" will set the "bar" value in the "foo"
        Bunch in this Namespace. If foo does not exist, it is created
        as a Bunch. If foo is a value, an OptionsError will be
        raised."""
        segments = key.split(".")
        obj = self
        segment = segments.pop(0)
        while segments:
            if segment not in obj:
                obj[segment] = Bunch()
            obj = obj[segment]
            if not isinstance(obj, dict):
                raise OptionsError("In setting option '%s', %s was already a value"
                                   % (key, segment))
            segment = segments.pop(0)
        obj[segment] = value
    
    def __setitem__(self, key, value):
        if isinstance(value, dict):
            self._sections.insert(0, key)
        super(Namespace, self).__setitem__(key, value)
    
    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default
    
    def __getitem__(self, key):
        order = self._ordering
        if order is None:
            order = self._sections
        try:
            return super(Namespace, self).__getitem__(key)
        except KeyError:
            pass
        for section in order:
            if isinstance(section, dict):
                try:
                    return section[key]
                except KeyError:
                    pass
            else:
                try:
                    return self[section][key]
                except KeyError:
                    pass
        raise KeyError("Key %s not found in namespace" % key)
    
    def __setattr__(self, key, value):
        if key.startswith("_"):
            object.__setattr__(self, key, value)
        else:
            self[key] = value
    
    def __delitem__(self, key):
        try:
            index = self._sections.index(key)
            del self._sections[index]
        except ValueError:
            pass
        super(Namespace, self).__delitem__(key)
    
    def update(self, d=None, **kw):
        """Update the namespace. This is less efficient than the standard 
        dict.update but is necessary to keep track of the sections that we'll be
        searching."""
        items = []
        if d:
            # look up keys even though we call items
            # because that's what the dict.update
            # doc says
            if hasattr(d, 'keys'):
                items.extend(list(d.items()))
            else:
                items.extend(list(d))
        items.extend(list(kw.items()))
        for key, value in items:
            self[key] = value
    
    __call__ = update
    
    def setdefault(self, key, default):
        if not key in self:
            self[key] = default
            return default
        return self[key]

########NEW FILE########
__FILENAME__ = path
"""
Wrapper around path.py to add dry run support and other paver integration.
"""
from __future__ import with_statement

import functools
import os
from contextlib import contextmanager
import sys

if sys.version_info[0] == 3:
    from paver.deps.path3 import path as _orig_path
else:
    from paver.deps.path2 import path as _orig_path

from paver import tasks

__all__ = ['path', 'pushd']


@contextmanager
def pushd(dir):
    '''A context manager (Python 2.5+ only) for stepping into a
    directory and automatically coming back to the previous one.
    The original directory is returned. Usage is like this::

        from __future__ import with_statement
        # the above line is only needed for Python 2.5

        from paver.easy import *

        @task
        def my_task():
            with pushd('new/directory') as old_dir:
                ...do stuff...
    '''
    old_dir = os.getcwd()
    tasks.environment.info('cd %s' % dir)
    os.chdir(dir)
    try:
        yield old_dir
        tasks.environment.info('cd %s' % old_dir)
    finally:
        os.chdir(old_dir)

class path(_orig_path):
    def chdir(self):
        # compatability with the ancient path.py that had a .chdir() method
        self.__enter__()

# This is used to prevent implementation details of dry'd functions from
# printing redundant information.
# In particular, foo_p methods usually call the foo method internally and
# we don't want to print that information twice.
# We can say that the former implies the latter and call it a day.
_silence_nested_calls = False

def _make_wrapper(name, func):
    from paver.easy import dry

    @functools.wraps(func)
    def wrapper(*args, **kwds):
        global _silence_nested_calls
        msg = None
        if not _silence_nested_calls:
            msg = name + ' ' + ' '.join(map(repr, args))
        try:
            _silence_nested_calls = True
            return dry(msg, func, *args, **kwds)
        finally:
            _silence_nested_calls = False
    return wrapper

_METHOD_BLACKLIST = [
    'rename', 'renames', 'mkdir', 'mkdir_p', 'makedirs', 'makedirs_p',
    'rmdir', 'rmdir_p', 'removedirs', 'removedirs_p', 'touch',
    'remove', 'remove_p', 'unlink', 'unlink_p', 'link', 'symlink',
    'copyfile', 'copymode', 'copystat', 'copy', 'copy2', 'copytree',
    'move', 'rmtree', 'rmtree_p',
    # added atop of original dry run support
    'chown', 'chmod', 'utime', 'write_bytes', 'write_lines', 'write_text'
]


for name in _METHOD_BLACKLIST:
    if not hasattr(_orig_path, name):
        continue
    wrapper = _make_wrapper(name, getattr(_orig_path, name))
    setattr(path, name, wrapper)

########NEW FILE########
__FILENAME__ = path25
# backward compatibility
# Print deprecation warning in next release
from paver.path import *


########NEW FILE########
__FILENAME__ = release
"""Release metadata for Paver."""

from paver.options import Bunch
from paver.tasks import VERSION

setup_meta=Bunch(
    name='Paver',
    version=VERSION,
    description='Easy build, distribution and deployment scripting',
    long_description="""Paver is a Python-based build/distribution/deployment scripting tool along the
lines of Make or Rake. What makes Paver unique is its integration with 
commonly used Python libraries. Common tasks that were easy before remain 
easy. More importantly, dealing with *your* applications specific needs and 
requirements is also easy.""",
    author='Kevin Dangoor',
    author_email='dangoor+paver@gmail.com',
    maintainer='Lukas Linhart',
    maintainer_email='bugs@almad.net',
    url='http://github.com/paver/paver',
    packages=['paver', 'paver.deps'],
    tests_require=['nose', 'virtualenv', 'mock', 'cogapp'],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.5",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.2",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: Implementation :: CPython",
        "Environment :: Console",
        "Topic :: Documentation",
        "Topic :: Utilities",
        "Topic :: Software Development :: Build Tools",
    ])

########NEW FILE########
__FILENAME__ = runtime
"""Helper functions and data structures used by pavements."""

import warnings

warnings.warn("Import from paver.easy instead of paver.runtime",
              DeprecationWarning, 2)

from paver.easy import *

__all__ = ["Bunch", "task", "Task", "needs", "dry", "error",
           "info", "debug", "call_task", "require_keys", "sh", "options",
           "BuildFailure", "PavementError", "path", 'cmdopts', "consume_args"]


def call_task(task_name, options=None):
    """DEPRECATED. Just call the task instead.
    
    Calls the desired task, including any tasks upon which that task
    depends. options is an optional dictionary that will be added
    to the option lookup search order.
    
    You can always call a task directly by calling the function directly.
    But, if you do so the dependencies aren't called. call_task ensures
    that these are called.
    
    Note that call_task will only call the task `once` during a given
    build as long as the options remain the same. If the options are
    changed, the task will be called again."""
    warnings.warn("Just call the function instead of using call_task",
                  DeprecationWarning, 2)
    task = environment.get_task(task_name)
    task()

def require_keys(keys):
    """GONE. There is no equivalent in Paver 1.0. Calling this
    will raise an exception.
    
    A set of dotted-notation keys that must be present in the
    options for this task to be relevant.
    
    """
    raise PavementError("require_keys is no longer available.")


class PaverImportError(ImportError):
    pass

########NEW FILE########
__FILENAME__ = shell
from paver.easy import error, dry, BuildFailure

import subprocess
import shlex
import sys

try:
    _shlex_quote = shlex.quote
except AttributeError:
    # Backport from Python 3.x. This suite is accordingly under the PSF
    # License rather than the BSD license used for the rest of the code.
    import re
    _find_unsafe = re.compile(r'[^\w@%+=:,./-]').search

    def _shlex_quote(s):
        """Return a shell-escaped version of the string *s*."""
        if not s:
            return "''"
        if _find_unsafe(s) is None:
            return s

        # use single quotes, and put single quotes into double quotes
        # the string $'b is then quoted as '$'"'"'b'
        return "'" + s.replace("'", "'\"'\"'") + "'"


def sh(command, capture=False, ignore_error=False, cwd=None):
    """Runs an external command. If capture is True, the output of the
    command will be captured and returned as a string.  If the command
    has a non-zero return code raise a BuildFailure. You can pass
    ignore_error=True to allow non-zero return codes to be allowed to
    pass silently, silently into the night.  If you pass cwd='some/path'
    paver will chdir to 'some/path' before exectuting the command.

    If the dry_run option is True, the command will not
    actually be run."""
    if isinstance(command, (list, tuple)):
        command = ' '.join([_shlex_quote(c) for c in command])

    def runpipe():
        kwargs = {'shell': True, 'cwd': cwd}
        if capture:
            kwargs['stderr'] = subprocess.STDOUT
            kwargs['stdout'] = subprocess.PIPE
        p = subprocess.Popen(command, **kwargs)
        p_stdout = p.communicate()[0]
        if p_stdout is not None:
            if sys.version_info[0] == 2 and sys.version_info[1] < 7:
                p_stdout = p_stdout.decode(sys.getdefaultencoding())
            else:
                p_stdout = p_stdout.decode(sys.getdefaultencoding(), 'ignore')
        if p.returncode and not ignore_error:
            if capture and p_stdout is not None:
                error(p_stdout)
            raise BuildFailure("Subprocess return code: %d" % p.returncode)

        if capture:
            return p_stdout

    return dry(command, runpipe)

########NEW FILE########
__FILENAME__ = ssh
"""Functions for accessing remote hosts.

At present, these are implemented by calling ssh's command line programs.
"""

from paver.easy import sh

def scp(source, dest):
    """Copy the source file to the destination."""
    sh(["scp", source, dest])

########NEW FILE########
__FILENAME__ = svn
"""Convenience functions for working with svn.

This module does not include any tasks, only functions.

At this point, these functions do not use any kind of library. They require
the svn binary on the path."""

from paver.easy import sh, Bunch, path

def _format_revision(revision):
    if revision:
        revision = "-r %s " % (revision)
    return revision
    
def checkout(url, dest, revision=""):
    """Checks out the specified URL to the given destination."""
    revision = _format_revision(revision)
    sh("svn co %s%s %s" % (revision, url, dest))

def update(path="", revision=""):
    """Run an svn update on the given path."""
    revision = _format_revision(revision)
    command = "svn up %s" % revision
    if path:
        command += path
    sh(command)

def checkup(url, dest, revision=""):
    """Does a checkout or update, depending on whether the destination
    exists and is up to date (if a revision is passed in). Returns
    true if a checkout or update was performed. False otherwise."""
    dest = path(dest)
    if not dest.exists():
        checkout(url, dest, revision)
        return True
    else:
        vinfo = info(dest)
        if not vinfo or vinfo.revision != revision:
            update(dest, revision)
            return True
        return False

def export(url, dest, revision=""):
    """Exports the specified URL to the given destination."""
    revision = _format_revision(revision)
    cmd = 'svn export %s%s %s' % (revision, url, dest)
    sh(cmd)

def info(path=""):
    """Retrieves the svn info for the path and returns a dictionary of 
    the values. Names are normalized to lower case with spaces converted
    to underscores."""
    output = sh("svn info %s" % path, capture=True)
    if not output:
        return Bunch()
    lines = output.splitlines()
    data = Bunch()
    for line in lines:
        colon = line.find(":")
        if colon == -1:
            continue
        key = line[:colon].lower().replace(" ", "_")
        value = line[colon+2:]
        data[key] = value
    return data

########NEW FILE########
__FILENAME__ = tasks
from __future__ import with_statement
import sys
import os
import copy
import optparse
import re
import types
import inspect
import itertools
import operator
import traceback

from os.path import *

import paver.deps.six as six
from paver.deps.six import print_
from paver.version import VERSION

# using six.moves is complicated because we include it and it's thus not at
# the top level
if six.PY3:
    xrange = range

class PavementError(Exception):
    """Exception that represents a problem in the pavement.py file
    rather than the process of running a build."""
    pass

class BuildFailure(Exception):
    """Represents a problem with some part of the build's execution."""
    pass


class Environment(object):
    _task_in_progress = None
    _task_output = None
    _all_tasks = None
    _dry_run = False
    verbose = False
    interactive = False
    quiet = False
    _file = "pavement.py"

    def __init__(self, pavement=None):
        self.pavement = pavement
        self.task_finders = []
        try:
            # for the time being, at least, tasks.py can be used on its
            # own!
            from paver import options
            self.options = options.Namespace()
            self.options.dry_run = False
            self.options.pavement_file = self.pavement_file
        except ImportError:
            pass

    def info(self, message, *args):
        self._log(2, message, args)

    def debug(self, message, *args):
        self._log(1, message, args)

    def error(self, message, *args):
        self._log(3, message, args)

    def _log(self, level, message, args):
        # This conditional fixes an issue which arises if the message contains
        # formatting directives but no args are provided.
        if args:
            output = message % args
        else:
            output = message

        if self._task_output is not None:
            self._task_output.append(output)
        if level > 2 or (level > 1 and not self.quiet) or \
            self.verbose:
            self._print(output)

    def _print(self, output):
        print_(output)
        sys.stdout.flush()

    def _exit(self, code):
        sys.exit(1)

    def _set_dry_run(self, dr):
        self._dry_run = dr
        try:
            self.options.dry_run = dr
        except AttributeError:
            pass

    def _get_dry_run(self):
        return self._dry_run

    dry_run = property(_get_dry_run, _set_dry_run)

    def _set_pavement_file(self, pavement_file):
        self._file = pavement_file
        try:
            self.options.pavement_file = pavement_file
        except AttributeError:
            pass

    def _get_pavement_file(self):
        return self._file

    pavement_file = property(_get_pavement_file, _set_pavement_file)

    file = property(fset=_set_pavement_file)

    def get_task(self, taskname):

        task = getattr(self.pavement, taskname, None)

        # delegate to task finders next
        if not task:
            for finder in self.task_finders:
                task = finder.get_task(taskname)
                if task:
                    break

        # try to look up by full name
        if not task:
            task = _import_task(taskname)

        # if there's nothing by full name, look up by
        # short name
        if not task:
            all_tasks = self.get_tasks()
            matches = [t for t in all_tasks
                        if t.shortname == taskname]
            if len(matches) > 1:
                matched_names = [t.name for t in matches]
                raise BuildFailure("Ambiguous task name %s (%s)" %
                                    (taskname, matched_names))
            elif matches:
                task = matches[0]
        return task

    def call_task(self, task_name, args=None, options=None):
        task = self.get_task(task_name)
        if hasattr(task, 'paver_constraint'):
            task.paver_constraint()
        if options:
            for option in options:
                task._set_value_to_task(task_name, option, None, options[option])

        if args and task.consume_args > 0:
            args = _consume_nargs(task, args)
        elif args and (task.consume_args == 0):
            raise BuildFailure("Task %s is not decorated with @consume_(n)args,"
                                "but has been called with them")
        task()

    def _run_task(self, task_name, needs, func):
        (funcargs, varargs, varkw, defaults) = inspect.getargspec(func)
        kw = dict()
        for i in xrange(0, len(funcargs)):
            arg = funcargs[i]
            if arg == 'env':
                kw['env'] = self
            # Keyword arguments do now need to be in the environment
            elif (defaults is not None and
                  (i - (len(funcargs) - len(defaults))) >= 0):
                pass
            else:
                try:
                    kw[arg] = getattr(self, arg)
                except AttributeError:
                    raise PavementError("Task %s requires an argument (%s) that is "
                        "not present in the environment" % (task_name, arg))

        if not self._task_in_progress:
            self._task_in_progress = task_name
            self._task_output = []
            running_top_level = True
        else:
            running_top_level = False
        def do_task():
            self.info("---> " + task_name)
            for req in needs:
                task = self.get_task(req)
                if not task:
                    raise PavementError("Requirement %s for task %s not found" %
                        (req, task_name))
                if not isinstance(task, Task):
                    raise PavementError("Requirement %s for task %s is not a Task"
                        % (req, task_name))
                if not task.called:
                    task()
            return func(**kw)
        if running_top_level:
            try:
                return do_task()
            except Exception:
                e = sys.exc_info()[1]
                self._print("""

Captured Task Output:
---------------------
""")
                self._print("\n".join(map(str, self._task_output)))
                if isinstance(e, BuildFailure):
                    self._print("\nBuild failed running %s: %s" %
                                (self._task_in_progress, e))
                else:
                    self._print(traceback.format_exc())
            self._task_in_progress = None
            self._task_output = None
            self._exit(1)
        else:
            return do_task()

    def get_tasks(self):
        if self._all_tasks:
            return self._all_tasks
        result = set()
        modules = set()
        def scan_module(module):
            modules.add(module)
            for name in dir(module):
                item = getattr(module, name, None)
                if isinstance(item, Task):
                    result.add(item)
                if isinstance(item, types.ModuleType) and item not in modules:
                    scan_module(item)
        scan_module(self.pavement)
        for finder in self.task_finders:
            result.update(finder.get_tasks())
        self._all_tasks = result
        return result

environment_stack = []
environment = Environment()

def _consume_nargs(task, args):
    """Set up args in environment function of number of args task consumes.
    """
    if task.consume_args > 0:
        if (args is None) or (task.consume_args != float('inf') and \
                              (len(args) < task.consume_args)):
            args_consumed = ""
            if task.consume_args == float('inf'):
                args_consumed = "all arguments"
            else:
                args_consumed = "exactly %i argument" % task.consume_args
                args_consumed += "s" if (task.consume_args > 1) else ""

            args_passed = "none" if args is None \
                                 else "got only %i" % len(args)

            raise BuildFailure("%s consumes %s, %s" %  \
                                (task.name, args_consumed, args_passed))

        _args = args if task.consume_args == float('inf') \
                     else args[:task.consume_args]
        try:
            environment.options.args = _args
        except AttributeError:
            pass
        environment.args = _args

        return [] if task.consume_args == float('inf') \
                  else args[task.consume_args:]

def _import_task(taskname):
    """Looks up a dotted task name and imports the module as necessary
    to get at the task."""
    parts = taskname.split('.')
    if len(parts) < 2:
        return None
    func_name = parts[-1]
    full_mod_name = ".".join(parts[:-1])
    mod_name = parts[-2]
    try:
        module = __import__(full_mod_name, globals(), locals(), [mod_name])
    except ImportError:
        return None
    return getattr(module, func_name, None)

class Task(object):
    called = False
    consume_args = 0
    no_auto = False

    __doc__ = ""

    def __init__(self, func):

        super(Task, self).__init__()

        self.func = func
        self.needs = []
        self.might_call = []
        self.__name__ = func.__name__
        self.shortname = func.__name__
        self.name = "%s.%s" % (func.__module__, func.__name__)
        self.option_names = set()
        self.user_options = []
        self.negative_opt = {}
        self.share_options_with = []
        self._parser = None
        self.use_virtualenv = None
        self.virtualenv_dir = None

        try:
            self.__doc__ = func.__doc__
        except AttributeError:
            pass

    def __call__(self, *args, **kw):
        if self.use_virtualenv and self.virtualenv_dir:
            #TODO: Environment recovery?
            activate_this = join(self.virtualenv_dir, "bin", "activate_this.py")
            with open(activate_this) as f:
                s = f.read()
            code = compile(s, activate_this, 'exec')
            exec(code, dict(__file__=activate_this))
        retval = environment._run_task(self.name, self.needs, self.func)
        self.called = True
        return retval

    def __repr__(self):
        return "Task: " + self.__name__

    def _make_option_from_tuple(self, option):
        # option is (longname, short, desc)
        longname = option[0]
        if longname and longname.endswith('='):
            action = "store"
            longname = longname[:-1]
        else:
            action = "store_true"

        destination = longname.replace('-', '_')

        opts = []

        if option[1]:
            opts.append('-' + option[1])

        if longname:
            opts.append('--' + longname)

        return optparse.make_option(*opts,
            **dict(action=action, dest=destination, help=option[2]))

    @property
    def parser(self):

        if getattr(self, '_parser', None):
            return self._parser

        self._parser = parser = optparse.OptionParser(add_help_option=False,
            usage="%%prog %s [options]" % self.name)

        parser.disable_interspersed_args()
        parser.add_option('-h', '--help', action="store_true",
                        help="display this help information")

        needs_tasks = [(environment.get_task(task), task) for task in self.needs_closure]

        # backward compatibility: tasks that inherit from Task and override constructor
        if getattr(self, "might_call", None):
            needs_tasks.extend((environment.get_task(task), task) for task in self.might_call)

        shared_tasks = {}
        parser.mirrored_options = {}
        parser.options_to_hide_from_help = []

        for task, task_name in itertools.chain([(self, self.name)], needs_tasks):
            if not task:
                raise PavementError("Task %s needed by %s does not exist"
                    % (task_name, self))

            for option in task.user_options:
                add_options = True
                try:
                    if not isinstance(option, optparse.Option):
                        option = self._make_option_from_tuple(option)

                    environment.debug("Task %s: adding option %s" %
                                     (self.name, str(option)))

                    try:
                        longname = option._long_opts[0]
                    except IndexError:
                        longname = None

                    try:
                        shortname = option._short_opts[0]
                    except IndexError:
                        shortname = None

                    # XXX: this probably needs refactored to handle commands with multiple
                    # long or short options
                    task_share_options_with = task.share_options_with or []
                    task_shares = [environment.get_task(t).name for t in task_share_options_with if environment.get_task(t)]

                    if self.share_options_with or task_shares:
                        options = (shortname, longname)

                        # either I am sharing with dependent task
                        # ...or it can share with me
                        if (
                                options in shared_tasks and (shared_tasks[options] or self.share_options_with)
                            ) \
                            or \
                            (
                                self.name in [environment.get_task(t).name for t in task_share_options_with if environment.get_task(t)]
                            ):
                            environment.debug("Task %s: NOT adding option %s," \
                                "already present; setting up mirror" %
                                             (self.name, option))

                            if option.dest not in parser.mirrored_options:
                                parser.mirrored_options[option.dest] = []
                            parser.mirrored_options[option.dest].append(task_name)
                            add_options = False

                        if options not in shared_tasks:
                            shared_tasks[options] = set()

                        if task_share_options_with:
                            shared_tasks[options] |= set(task_share_options_with)

                    if add_options:
                        try:
                            parser.add_option(option)
                        except optparse.OptionConflictError:
                            raise PavementError("""In setting command options for %r,
    option %s for %r is already in use
    by another task in the dependency chain.""" % (self, option, task))
                        # add just names; longname now contains --initial-dashes
                        self.option_names.add((task.shortname, longname[2:], option.dest))

                        if getattr(task, 'no_help', False):
                            if shortname:
                                parser.options_to_hide_from_help.append(shortname)
                            elif longname:
                                parser.options_to_hide_from_help.append(longname)
                except IndexError:
                    raise PavementError("Invalid option format provided for %r: %s"
                                        % (self, option))

        return parser

    def display_help(self, parser=None):
        if not parser:
            parser = self.parser

        for opt_str in parser.options_to_hide_from_help:
            try:
                parser.remove_option(opt_str)
            except ValueError:
                environment.error("Option %s added for hiding, but it's not in parser...?" % opt_str)

        name = self.name
        print_("\n%s" % name)
        print_("-" * len(name))
        parser.print_help()
        print_()
        print_(self.__doc__)
        print_()

    def _set_value_to_task(self, task_name, option_name, dist_option_name, value):
        import paver.options
        try:
            optholder = environment.options[task_name]
        except KeyError:
            optholder = paver.options.Bunch()
            environment.options[task_name] = optholder

        if value is not None:
            if dist_option_name in getattr(self, "negative_opt"):
                optholder[self.negative_opt[dist_option_name].replace('-', '_')] = False
            else:
                optholder[option_name] = value

    def parse_args(self, args):
        import paver.options
        environment.debug("Task %s: Parsing args %s" % (self.name, args))
        environment.options.setdefault(self.shortname, paver.options.Bunch())
        parser = self.parser
        options, args = parser.parse_args(args)

        if options.help:
            self.display_help(parser)
            sys.exit(0)

        for task_name, option_name, option_dest in self.option_names:
            if option_name != option_dest:
                dist_option_name = copy.copy(option_name)
                option_name = option_dest
            else:
                dist_option_name = option_name
            option_name = option_name.replace('-', '_')

            value = getattr(options, option_name, getattr(options, option_dest))

            self._set_value_to_task(task_name, option_name, dist_option_name, value)

            if option_name in parser.mirrored_options:
                for task_name in parser.mirrored_options[option_name]:
                    self._set_value_to_task(task_name, option_name, dist_option_name, value)

        return args

    @property
    def description(self):
        if self.__doc__:
            return re.split("\.\s+", self.__doc__, maxsplit=1)[0].strip()
        else:
            return ""

    @property
    def needs_closure(self):
        stack = [] + self.needs
        rv = []
        while stack:
            top = stack.pop()
            if top not in rv:
                rv.append(top)
                needs = []
                if environment.get_task(top):
                    deptask = environment.get_task(top)

                    if not isinstance(deptask, Task):
                        raise BuildFailure("Dependency %s is not a Task (only tasks allowed in @needs)" % deptask)

                    needs = deptask.needs

                for t in needs:
                    stack.append(t)

        return rv

def task(func):
    """Specifies that this function is a task.

    Note that this decorator does not actually replace the function object.
    It just keeps track of the task and sets an is_task flag on the
    function object."""
    if isinstance(func, Task):
        return func
    task = Task(func)
    return task

def needs(*args):
    """Specifies tasks upon which this task depends.

    req can be a string or a list of strings with the names
    of the tasks. You can call this decorator multiple times
    and the various requirements are added on. You can also
    call with the requirements as a list of arguments.

    The requirements are called in the order presented in the
    list."""
    def entangle(func):
        req = args
        func = task(func)
        needs_list = func.needs
        if len(req) == 1:
            req = req[0]
        if isinstance(req, six.string_types):
            needs_list.append(req)
        elif isinstance(req, (list, tuple)):
            needs_list.extend(req)
        else:
            raise PavementError("'needs' decorator requires a list or string "
                                "but got %s" % req)
        return func
    return entangle

def cmdopts(options, share_with=None):
    """Sets the command line options that can be set for this task.
    This uses the same format as the distutils command line option
    parser. It's a list of tuples, each with three elements:
    long option name, short option, description.

    If the long option name ends with '=', that means that the
    option takes a value. Otherwise the option is just boolean.
    All of the options will be stored in the options dict with
    the name of the task. Each value that gets stored in that
    dict will be stored with a key that is based on the long option
    name (the only difference is that - is replaced by _).

    """
    def entangle(func):
        func = task(func)
        func.user_options = options
        func.share_options_with = share_with
        return func
    return entangle

def might_call(*args):
    """

    """
    def entangle(func):
        req = args
        func = task(func)
        might_call = func.might_call
        if len(req) == 1:
            req = req[0]
        if isinstance(req, six.string_types):
            might_call.append(req)
        elif isinstance(req, (list, tuple)):
            might_call.extend(req)
        else:
            raise PavementError("'might_call' decorator requires a list or string "
                                "but got %s" % req)
        return func
    return entangle


def consume_nargs(nb_args=None):
    """All specified command line arguments that appear after this task on the
    command line will be placed in options.args.
    By default, if :data:`nb_args` is not specified, all arguments will
    be consumed.

    :param nb_args:     number of arguments the decorated function consumes
    :type nb_args:      ``int``

    """
    def consume_args_wrapper(func):
        func = task(func)
        func.consume_args = nb_args if nb_args is not None else float('inf')
        return func

    return consume_args_wrapper

def consume_args(func):
    """Any command line arguments that appear after this task on the
    command line will be placed in options.args."""
    return consume_nargs()(func)

def no_auto(func):
    """Specify that this task does not depend on the auto task,
    and don't run the auto task just for this one."""
    func = task(func)
    func.no_auto = True
    return func

def no_help(func):
    """Do not show this task in paver help."""
    func = task(func)
    func.no_help = True
    return func

def _preparse(args):
    task = None
    taskname = None
    while args:
        arg = args.pop(0)
        if '=' in arg:
            key, value = arg.split("=")
            try:
                environment.options.setdotted(key, value)
            except AttributeError:
                raise BuildFailure("""This appears to be a standalone Paver
tasks.py, so the build environment does not support options. The command
line (%s) attempts to set an option.""" % (args))
        elif arg.startswith('-'):
            args.insert(0, arg)
            break
        else:
            taskname = arg
            task = environment.get_task(taskname)
            if task is None:
                raise BuildFailure("Unknown task: %s" % taskname)
            break
    return task, taskname, args

def _parse_global_options(args):
    # this is where global options should be dealt with
    parser = optparse.OptionParser(usage=
        """Usage: %prog [global options] taskname [task options] """
        """[taskname [taskoptions]]""", version="Paver %s" % (VERSION),
        add_help_option=False)

    environment.help_function = parser.print_help

    parser.add_option('-n', '--dry-run', action='store_true',
                    help="don't actually do anything")
    parser.add_option('-v', "--verbose", action="store_true",
                    help="display all logging output")
    parser.add_option('-q', '--quiet', action="store_true",
                    help="display only errors")
    parser.add_option("-i", "--interactive", action="store_true",
                    help="enable prompting")
    parser.add_option("-f", "--file", metavar="FILE",
                    help="read tasks from FILE [%default]")
    parser.add_option('-h', "--help", action="store_true",
                    help="display this help information")
    parser.add_option("--propagate-traceback", action="store_true",
                    help="propagate traceback, do not hide it under BuildFailure"
                        "(for debugging)")
    parser.add_option('-x', '--command-packages', action="store",
                    help="list of packages that provide distutils commands")
    parser.set_defaults(file=environment.pavement_file)

    parser.disable_interspersed_args()
    options, args = parser.parse_args(args)
    if options.help:
        args.insert(0, "help")
    for key, value in vars(options).items():
        setattr(environment, key, value)

    return args

def _parse_command_line(args):
    task, taskname, args = _preparse(args)

    if not task:
        args = _parse_global_options(args)
        if not args:
            return None, []

        taskname = args.pop(0)
        task = environment.get_task(taskname)

        if not task:
            raise BuildFailure("Unknown task: %s" % taskname)

    if not isinstance(task, Task):
        raise BuildFailure("%s is not a Task" % taskname)

    if task.consume_args > 0:
        args = _consume_nargs(task, args)
    else:
        args = task.parse_args(args)

    return task, args

def _cmp_task_names(a, b):
    a = a.name
    b = b.name
    a_in_pavement = a.startswith("pavement.")
    b_in_pavement = b.startswith("pavement.")
    if a_in_pavement and not b_in_pavement:
        return 1
    if b_in_pavement and not a_in_pavement:
        return -1
    # trick taken from python3porting.org
    return (a > b) - (b < a)

if six.PY3:
    import functools
    _task_names_key = functools.cmp_to_key(_cmp_task_names)

def _group_by_module(items):
    def key(item):
        dotpos = item.name.rfind('.')
        return item.name[:dotpos]

    maxlen = max(len(item.shortname) for item in items)
    groups = itertools.groupby(sorted(items, key=operator.attrgetter('name')), key=key)
    return maxlen, groups

@task
@no_auto
@consume_args
def help(args, help_function):
    """This help display."""
    if args:
        task_name = args[0]
        task = environment.get_task(task_name)
        if not task:
            print_("Task not found: %s" % (task_name))
            return

        task.display_help()
        return

    help_function()

    task_list = environment.get_tasks()
    if six.PY3:
        task_list = sorted(task_list, key=_task_names_key)
    else:
        task_list = sorted(task_list, cmp=_cmp_task_names)
    maxlen, task_list = _group_by_module(task_list)
    fmt = "  %-" + str(maxlen) + "s - %s"
    for group_name, group in task_list:
        print_("\nTasks from %s:" % (group_name))
        for task in group:
            if not getattr(task, "no_help", False):
                print_(fmt % (task.shortname, task.description))

def _process_commands(args, auto_pending=False):
    first_loop = True
    while True:
        task, args = _parse_command_line(args)
        if auto_pending:
            if task and not task.no_auto:
                environment.call_task('auto')
                auto_pending=False
        if task is None:
            if first_loop:
                task = environment.get_task('default')
                if not task:
                    break
            else:
                break
        task()
        first_loop = False

def call_pavement(new_pavement, args):
    if isinstance(args, six.string_types):
        args = args.split()
    global environment
    environment_stack.append(environment)
    environment = Environment()
    cwd = os.getcwd()
    dirname, basename = split(new_pavement)
    environment.pavement_file = basename
    try:
        if dirname:
            os.chdir(dirname)
        _launch_pavement(args)
    finally:
        os.chdir(cwd)
    environment = environment_stack.pop()

def _launch_pavement(args):
    mod = types.ModuleType("pavement")
    environment.pavement = mod

    if not exists(environment.pavement_file):
        environment.pavement_file = None
        six.exec_("from paver.easy import *\n", mod.__dict__)
        _process_commands(args)
        return

    mod.__file__ = environment.pavement_file
    try:
        pf = open(environment.pavement_file)
        try:
            source = pf.read()
        finally:
            pf.close()
        exec(compile(source, environment.pavement_file, 'exec'), mod.__dict__)
        auto_task = getattr(mod, 'auto', None)
        auto_pending = isinstance(auto_task, Task)

        from paver.misctasks import generate_setup, minilib
        resident_tasks = {
            'help': help,
            'generate_setup': generate_setup,
            'minilib': minilib,
            }
        mod.__dict__.update(resident_tasks)

        _process_commands(args, auto_pending=auto_pending)
    except PavementError:
        e = sys.exc_info()[1]
        # this is hacky, but it is needed if problem would occur within
        # argument parsing, which is actually quite common
        if getattr(environment.options, "propagate_traceback", False) \
            or '--propagate-traceback' in args:
            raise
        print_("\n\n*** Problem with pavement:\n%s\n%s\n\n" % (
                    abspath(environment.pavement_file), e))

def main(args=None):
    global environment
    if args is None:
        args = sys.argv[1:]
    environment = Environment()

    # need to parse args to recover pavement-file to read before executing
    try:
        args = _parse_global_options(args)
        _launch_pavement(args)
    except BuildFailure:
        e = sys.exc_info()[1]
        environment.error("Build failed: %s", e)
        sys.exit(1)

########NEW FILE########
__FILENAME__ = t1
#[[[section first]]]
print "Hi!"
#[[[endsection]]]

print "More"

########NEW FILE########
__FILENAME__ = t2
#[[[section second]]]
import sys

#[[[section inner]]]
print sys.path
#[[[endsection]]]
#[[[endsection]]]

########NEW FILE########
__FILENAME__ = other_pavement
from paver.easy import *

from paver.tests import test_tasks

options(foo=1)

@task
def t1(options):
    test_tasks.OP_T1_CALLED = options.foo

########NEW FILE########
__FILENAME__ = test_doctools
from __future__ import with_statement
import sys

from nose.plugins.skip import SkipTest
from paver.deps.six import print_

from paver.easy import *
from paver import doctools, tasks, options

def _no25():
    if sys.version_info[:2] == (2, 5):
        raise SkipTest('No cog integration in Python 2.5')


def test_sections_from_file():
    simpletext = """# [[[section foo]]]
#Foo!
# [[[endsection]]]
"""
    f = doctools.SectionedFile(from_string=simpletext)
    assert len(f) == 1, "Sections found: %s" % f
    assert f['foo'] == "#Foo!\n", "Foo section contained: '%s'" % f['foo']

def display(msg, *args):
    print_(msg % args)

doctools.debug = display

def test_nested_sections():
    myfile = """
[[[section bar]]]
    Hi there.
    [[[section baz]]]
    Yo.
    [[[endsection]]]
[[[endsection]]]
"""
    f = doctools.SectionedFile(from_string=myfile)
    assert len(f) == 2
    assert f['bar'] == """    Hi there.
    Yo.
""", "Bar was: '%s'" % (f['bar'])
    assert f['bar.baz'] == """    Yo.
"""

def test_section_doesnt_end():
    myfile = """
[[[section bar]]]
Yo.
"""
    try:
        f = doctools.SectionedFile(from_string=myfile)
        assert False, "Expected a BuildFailure"
    except BuildFailure:
        e = sys.exc_info()[1]
        assert str(e) == """No end marker for section 'bar'
(in file 'None', starts at line 2)""", "error was: %s" % (str(e))

def test_section_already_defined():
    myfile = """
[[[section foo]]]
First one.
[[[endsection]]]

[[[section foo]]]
Second one.
[[[endsection]]]
"""
    try:
        f = doctools.SectionedFile(from_string=myfile)
        assert False, "Expected a BuildFailure"
    except BuildFailure:
        e = sys.exc_info()[1]
        assert str(e) == """section 'foo' redefined
(in file 'None', first section at line 2, second at line 6)""", \
        "error was: %s" % (str(e))
        

def test_endmarker_without_start():
    myfile = """
[[[section foo]]]
This is a good section.
[[[endsection]]]

[[[endsection]]]
"""
    try:
        f = doctools.SectionedFile(from_string=myfile)
        assert False, "Expected a BuildFailure"
    except BuildFailure:
        e = sys.exc_info()[1]
        assert str(e) == """End section marker with no starting marker
(in file 'None', at line 6)""", \
        "error was: %s" % (str(e))

def test_whole_file():
    myfile = """
[[[section bar]]]
    Hi there.
    [[[section baz]]]
    Yo.
    [[[endsection]]]
[[[endsection]]]
"""
    f = doctools.SectionedFile(from_string=myfile)
    assert f.all == """
    Hi there.
    Yo.
""", "All was: %s" % (f.all)
    
def test_bad_section():
    f = doctools.SectionedFile(from_string="")
    try:
        f['foo']
        assert False, "Should have a BuildFailure"
    except BuildFailure:
        e = sys.exc_info()[1]
        assert str(e) == "No section 'foo' in file 'None'", \
               "Error: '%s'" % (str(e))
    
def test_include_lookup():
    basedir = path(__file__).dirname() / "data"
    include = doctools.Includer(basedir, include_markers={})
    everything = include("t1.py")
    assert everything == """# file 't1.py'
print "Hi!"

print "More"
""", "Everything was: '%s'" % (everything)
    first = include("t1.py", "first")
    assert first == """# section 'first' in file 't1.py'
print "Hi!"
""", "First was '%s'" % (first)
    second = include("t2.py", "second.inner")
    assert second == """# section 'second.inner' in file 't2.py'
print sys.path
""", "Second was '%s'" % (second)
    
def test_cogging():
    if not paver.doctools.has_cog:
        raise SkipTest("Cog must be installed for this test")
    _no25()
    env = tasks.Environment(doctools)
    tasks.environment = env
    opt = env.options
    opt.cog = options.Bunch()
    basedir = path(__file__).dirname()
    opt.cog.basedir = basedir
    opt.cog.pattern = "*.rst"
    opt.cog.includedir = basedir / "data"
    env.options = opt
    doctools.cog()
    textfile = basedir / "data/textfile.rst"
    with open(textfile) as f:
        data = f.read()
    print_(data)
    assert "print sys.path" in data
    doctools.uncog()
    with open(textfile) as f:
        data = f.read()
    assert "print sys.path" not in data
    
def test_cogging_with_markers_removed():
    if not paver.doctools.has_cog:
        raise SkipTest("Cog must be installed for this test")
    _no25()
    env = tasks.Environment(doctools)
    tasks.environment = env
    opt = env.options
    opt.cog = Bunch()
    basedir = path(__file__).dirname()
    opt.cog.basedir = basedir
    opt.cog.pattern = "*.rst"
    opt.cog.includedir = basedir / "data"
    opt.cog.delete_code = True
    env.options = opt
    textfile = basedir / "data/textfile.rst"
    with open(textfile) as f:
        original_data = f.read()
    try:
        doctools.cog()
        with open(textfile) as f:
            data = f.read()
        print_(data)
        assert "[[[cog" not in data
    finally:
        with open(textfile, "w") as f:
            f.write(original_data)


########NEW FILE########
__FILENAME__ = test_git
from mock import patch
from paver import git

import os

@patch('paver.git.sh')
def test_simple_clone(sh):
    git.clone("git://foo/foo.git", "bar")
    assert sh.called
    assert sh.call_args[0][0] == "git clone git://foo/foo.git bar"

@patch('paver.git.sh')
def test_simple_pull(sh):
    git.pull("repo_path", "origin_remote", "master_branch")
    assert sh.called
    assert sh.call_args[0][0] == "cd repo_path; git pull origin_remote master_branch"

@patch('paver.git.sh')
def test_simple_branch_checkout(sh):
    git.branch_checkout("my_branch", path="repo_path")
    assert sh.called
    assert sh.call_args[0][0] == "cd repo_path; git checkout my_branch"
    
@patch('paver.git.sh')
def test_branch_chekout_cwd(sh):
    """it should get the CWD and assume that is the repo"""
    
    git.branch_checkout("my_branch")
    assert sh.called
    assert sh.call_args[0][0] == "cd %(current_path)s; git checkout my_branch" % dict(
        current_path=os.getcwd()
    )
    
@patch('paver.git.sh')
def test_branch_list_correctly_parses_git_output(sh):
    output = git.branch_list(path="repo_path", __override__="""
* git_support
  master
  virtualenv_in_folder
    """)
    
    assert output == ("git_support", ["git_support", "master", "virtualenv_in_folder"])
    
@patch('paver.git.sh')
def test_branch_list_correctly_parses_remote_branch_output(sh):
    output = git.branch_list(path="repo_path", 
        remote_branches_only = True,
        __override__="""
    github/gh-pages
    github/git_support
    github/master""")
    
    assert output == ('',
        ["github/gh-pages", "github/git_support", "github/master"])

@patch('paver.git.sh')
def test_branch_track_remote(sh):
    git.branch_track_remote("origin/alpha_two", path="repo_path")
    
    assert sh.called
    assert sh.call_args[0][0] == "cd %(current_path)s; git checkout -b alpha_two --track origin/alpha_two" % dict(
        current_path="repo_path"
    )
     

########NEW FILE########
__FILENAME__ = test_options
from paver import options, tasks

def test_basic_namespace_as_dictionary():
    ns = options.Namespace(foo=1, bar=2)
    assert ns.foo == 1
    assert ns['bar'] == 2
    ns.bar = 3
    assert ns['bar'] == 3
    ns.new = 4
    assert ns.new == 4

def test_default_namespace_searching():
    ns = options.Namespace()
    ns.val = 0
    ns.foo = options.Bunch(foo=1, bar=2, baz=3, blorg=6)
    ns.bar = options.Bunch(foo=4, baz=5, bop=7, val=8)
    assert ns.val == 0, "Top namespace has priority"
    assert ns.foo == options.Bunch(foo=1, bar=2, baz=3, blorg=6)
    assert ns.foo.foo == 1
    assert ns.bar.foo == 4
    assert ns.baz == 5
    assert ns.blorg == 6
    
    try:
        ns['does not exist']
        assert False, "expected key error for missing item"
    except KeyError:
        pass
    
    del ns['val']
    
    assert ns.val == 8, "Now getting val from inner dict"
    
    del ns.bar.val
    
    try:
        a = ns['val']
        assert False, "expected exception for deleted item %s" % (ns)
    except KeyError:
        pass
    
    del ns.foo
    assert ns._sections == ['bar']

def test_clear():
    ns = options.Namespace(foo=options.Bunch(bar=1))
    ns.order('foo')
    ns.clear()
    assert len(ns) == 0
    assert len(ns._sections) == 0
    assert ns._ordering == None

def test_search_order_is_adjustable():
    ns = options.Namespace(
        bar=options.Bunch(val=1, blorg=4)
    )
    ns.baz=options.Bunch(val=2, bop=5)
    ns.foo=options.Bunch(val=3, bam=6)

    assert ns.blorg == 4
    assert ns.val == 3
    
    ns.order('baz')
    assert ns.val == 2
    assert ns.bop == 5
    try:
        ns.bam
        assert False, "expected attribute error for item not in search"
    except AttributeError:
        pass
    
    ns.order('bar', 'baz')
    assert ns.val == 1
    assert ns.blorg == 4
    assert ns.bop == 5
    
    ns.order('baz', add_rest=True)
    assert ns.val == 2
    assert ns.bam == 6

def test_update():
    ns = options.Namespace()
    ns.update(foo=options.Bunch(val=2))
    assert ns._sections == ['foo'], str(ns._sections)
    ns.update([('bar', options.Bunch(val=2))])
    assert ns._sections == ['bar', 'foo'], str(ns._sections)
    ns.update(dict(baz=options.Bunch(val=3)))
    assert ns._sections == ['baz', 'bar', 'foo'], str(ns._sections)
    ns(hi='there')
    assert ns.hi == 'there'
    
def test_setdefault():
    ns = options.Namespace()
    ns.setdefault('foo', options.Bunch())
    assert ns._sections == ['foo'], ns._sections
    
def test_callables_in_bunch():
    b = options.Bunch(foo = lambda: "hi")
    assert b.foo == "hi", "foo was: %s" % b.foo
    
def test_setdotted_values():
    ns = options.Namespace()
    ns.foo = options.Bunch()
    ns.setdotted("foo.bar", "baz")
    assert ns.foo.bar == "baz"
    ns.setdotted("bligger.bar", "flilling")
    assert ns.bligger.bar == "flilling"
    ns.val = 10
    try:
        ns.setdotted("val.yo", 42)
        assert False, "Expected exception when a value is found instead of bunch"
    except options.OptionsError:
        pass
    
def test_add_dict_to_order():
    ns = options.Namespace()
    ns.foo = options.Bunch(val="yo")
    ns.bar = options.Bunch(val="there")
    assert ns.val == "there"
    ns.order('foo')
    assert ns.val == "yo"
    ns.order(dict(val="new"), add_rest=True)
    assert ns.val == "new", "Got %s" % (ns.val)

########NEW FILE########
__FILENAME__ = test_path
# -*- coding: utf-8 -*-
import paver.path

import sys
import os.path

def test_join_on_unicode_path():
    # This is why we should drop 2.5 asap :]
    # b'' strings are not supported in 2.5, while u'' string are not supported in 3.2
    # -- even syntactically, so if will not help you here
    if sys.version_info[0] < 3:
        expected = 'something/\xc3\xb6'
        unicode_o = '\xc3\xb6'.decode('utf-8')

        # path.py on py2 is inheriting from str instead of unicode under this
        # circumstances, therefore we have to expect string
        if os.path.supports_unicode_filenames:
            expected.decode('utf-8')

    else:
        expected = 'something/ö'
        unicode_o = 'ö'

    assert expected == os.path.join(paver.path.path('something'), unicode_o)




########NEW FILE########
__FILENAME__ = test_shell
import sys
from paver.deps.six import b
from mock import patch, Mock
from paver import easy
from subprocess import PIPE, STDOUT

@patch('subprocess.Popen')
def test_sh_raises_BuildFailure(popen):
    popen.return_value.returncode = 1
    popen.return_value.communicate.return_value = [b('some stderr')]

    try:
        easy.sh('foo')
    except easy.BuildFailure:
        e = sys.exc_info()[1]
        args = e.args
        assert args == ('Subprocess return code: 1', )
    else:
        assert False, 'Failed to raise BuildFailure'

    assert popen.called
    assert popen.call_args[0][0] == 'foo'
    assert popen.call_args[1]['shell'] == True
    assert 'stdout' not in popen.call_args[1]

@patch('paver.shell.error')
@patch('subprocess.Popen')
def test_sh_with_capture_raises_BuildFailure(popen, error):
    popen.return_value.returncode = 1
    popen.return_value.communicate.return_value = [b('some stderr')]
    try:
        easy.sh('foo', capture=True)
    except easy.BuildFailure:
        e = sys.exc_info()[1]
        args = e.args
        assert args == ('Subprocess return code: 1', )
    else:
        assert False, 'Failed to raise BuildFailure'

    assert popen.called
    assert popen.call_args[0][0] == 'foo'
    assert popen.call_args[1]['shell'] == True
    assert popen.call_args[1]['stdout'] == PIPE
    assert popen.call_args[1]['stderr'] == STDOUT

    assert error.called
    assert error.call_args == (('some stderr', ), {})

@patch('subprocess.Popen')
def test_sh_ignores_error(popen):
    popen.return_value.communicate.return_value = [b('some stderr')]
    popen.return_value.returncode = 1
    easy.sh('foo', ignore_error=True)

    assert popen.called
    assert popen.call_args[0][0] == 'foo'
    assert popen.call_args[1]['shell'] == True
    assert 'stdout' not in popen.call_args[1]

@patch('subprocess.Popen')
def test_sh_ignores_error_with_capture(popen):
    popen.return_value.returncode = 1
    popen.return_value.communicate.return_value = [b('some stderr')]
    easy.sh('foo', capture=True, ignore_error=True)

    assert popen.called
    assert popen.call_args[0][0] == 'foo'
    assert popen.call_args[1]['shell'] == True
    assert popen.call_args[1]['stdout'] == PIPE
    assert popen.call_args[1]['stderr'] == STDOUT

@patch('subprocess.Popen')
def test_sh_with_multi_command(popen):
    popen.return_value.returncode = 0

    easy.sh(['foo', ' bar', 'fi"zz'])

    assert popen.called
    assert popen.call_args[0][0] == "foo ' bar' 'fi\"zz'"
    assert popen.call_args[1]['shell'] == True

########NEW FILE########
__FILENAME__ = test_svn
from mock import patch
from paver import svn

@patch('paver.svn.sh')
def test_simple_checkout(sh):
    svn.checkout("http://foo", "bar")
    assert sh.called
    assert sh.call_args[0][0] == "svn co http://foo bar"

@patch('paver.svn.sh')
def test_checkout_with_revision(sh):
    svn.checkout("http://foober", "baz", revision="1212")
    assert sh.called
    assert sh.call_args[0][0] == "svn co -r 1212 http://foober baz", sh.call_args[0][0]

@patch('paver.svn.sh')
def test_simple_update(sh):
    svn.update("bar")
    assert sh.called
    assert sh.call_args[0][0] == "svn up bar"
    sh.reset()
    svn.update()
    assert sh.called
    assert sh.call_args[0][0] == "svn up "

@patch('paver.svn.sh')
def test_update_with_revision(sh):
    svn.update(revision="1234")
    assert sh.called
    assert sh.call_args[0][0] == "svn up -r 1234 "

@patch('paver.svn.sh')
def test_simple_export(sh):
    svn.export("http://foo", "bar")
    assert sh.called
    assert sh.call_args[0][0] == "svn export http://foo bar"

@patch('paver.svn.sh')
def test_export_with_revision(sh):
    svn.export("http://foo", "bar", revision="1234")
    assert sh.called
    assert sh.call_args[0][0] == "svn export -r 1234 http://foo bar"

@patch('paver.svn.sh')
def test_svn_info(sh):
    sh.return_value="""Path: dojotoolkit/dojo
URL: http://svn.dojotoolkit.org/src/dojo/trunk
Repository Root: http://svn.dojotoolkit.org/src
Repository UUID: 560b804f-0ae3-0310-86f3-f6aa0a117693
Revision: 13301
Node Kind: directory
Schedule: normal
Last Changed Author: jaredj
Last Changed Rev: 13299
Last Changed Date: 2008-04-10 11:44:52 -0400 (Thu, 10 Apr 2008)
"""
    output = svn.info()
    assert sh.called
    assert output.path == "dojotoolkit/dojo"
    assert output.url == "http://svn.dojotoolkit.org/src/dojo/trunk"
    assert output.last_changed_date == "2008-04-10 11:44:52 -0400 (Thu, 10 Apr 2008)"
    

########NEW FILE########
__FILENAME__ = test_tasks
from __future__ import with_statement
import os
from pprint import pprint

from paver.deps.six import print_

from paver import setuputils, misctasks, tasks, options

from paver.tests.utils import _set_environment, FakeExitException

OP_T1_CALLED = 0
subpavement = os.path.join(os.path.dirname(__file__), "other_pavement.py")

def test_basic_dependencies():
    @tasks.task
    def t1():
        pass
    
    t1.called = False
    t1.t2_was_called = False
    
    @tasks.task
    @tasks.needs('t1')
    def t2():
        assert t1.called
        t1.t2_was_called = True
    
    _set_environment(t1 = t1, t2=t2)
    
    assert hasattr(tasks.environment.pavement, 't1')
    t2()
    assert t1.t2_was_called

@tasks.task
def global_t1():
    pass

def test_longname_resolution_in_dependencies():
    global_t1.called = False
    global_t1.t2_was_called = False
    
    @tasks.task
    @tasks.needs('paver.tests.test_tasks.global_t1')
    def t2():
        assert global_t1.called
        global_t1.t2_was_called = True
    
    _set_environment(t2=t2)
    t2()
    assert global_t1.t2_was_called
    
def test_chained_dependencies():
    called = [False, False, False, False]
    
    @tasks.task
    def t1():
        assert called == [False, False, False, False]
        called[0] = True
    
    @tasks.task
    @tasks.needs('t1')
    def t2():
        assert called == [True, False, False, False]
        called[1] = True
    
    @tasks.task
    def t3():
        assert called == [True, True, False, False]
        called[2] = True
    
    @tasks.task
    @tasks.needs('t2', 't3')
    def t4():
        assert called == [True, True, True, False]
        called[3] = True
    
    _set_environment(t1=t1,t2=t2,t3=t3,t4=t4)
    t4()
    assert called == [True, True, True, True], "Called was: %s" % (called)

def test_backwards_compatible_needs():
    @tasks.task
    def t():
        pass
    
    @tasks.task
    @tasks.needs(['t'])
    def t2():
        pass
    
    @tasks.task
    @tasks.needs('t')
    def t3():
        pass
    
    env = _set_environment(t=t, t2=t2, t3=t3)
    t3()
    assert t.called
    t.called = False
    
    t2()
    assert t.called

def test_tasks_dont_repeat():
    called = [0, 0, 0, 0]
    
    @tasks.task
    def t1():
        assert called == [0, 0, 0, 0]
        called[0] += 1
    
    @tasks.task
    @tasks.needs('t1')
    def t2():
        assert called == [1, 0, 0, 0]
        called[1] += 1
    
    @tasks.task
    @tasks.needs('t1')
    def t3():
        assert called == [1, 1, 0, 0]
        called[2] += 1
    
    @tasks.task
    @tasks.needs('t2', 't3')
    def t4():
        assert called == [1, 1, 1, 0]
        called[3] += 1
    
    _set_environment(t1=t1,t2=t2,t3=t3,t4=t4)
    t4()
    assert called == [1, 1, 1, 1]

def test_basic_command_line():
    @tasks.task
    def t1():
        pass
        
    _set_environment(t1=t1)
    try:
        tr, args = tasks._parse_command_line(['foo'])
        print_(tr)
        assert False, "Expected BuildFailure exception for unknown task"
    except tasks.BuildFailure:
        pass
    
    task, args = tasks._parse_command_line(['t1'])
    assert task == t1
    
    task, args = tasks._parse_command_line(['t1', 't2'])
    assert task == t1
    assert args == ['t2']
    
def test_list_tasks():
    from paver import doctools
    
    @tasks.task
    def t1():
        pass
        
    _set_environment(t1=t1, doctools=doctools)
    task_list = tasks.environment.get_tasks()
    assert t1 in task_list
    assert doctools.html in task_list
    
def test_environment_insertion():
    @tasks.task
    def t1(env):
        pass
    
    _set_environment(t1=t1)
    t1()
    assert t1.called

def test_add_options_to_environment():
    @tasks.task
    def t1(options):
        assert options.foo == 1
        
    @tasks.task
    def t2(options, env):
        assert options.foo == 1
        assert env.options == options
        
    environment = _set_environment(t1=t1, t2=t2)
    environment.options.foo = 1
    
    t1()
    t2()
    assert t1.called
    assert t2.called
    
def test_shortname_access():
    environment = _set_environment(tasks=tasks)
    task = environment.get_task("help")
    assert task is not None


def test_longname_access():
    environment = _set_environment(tasks=tasks)
    task = environment.get_task("paver.tasks.help")
    assert task is not None

    task = environment.get_task("nosuchmodule.nosuchtask")
    assert task is None

    task = environment.get_task("paver.tasks.nosuchtask")
    assert task is None


def test_task_command_line_options():
    @tasks.task
    @tasks.cmdopts([('foo=', 'f', 'Foobeedoobee!')])
    def t1(options):
        assert options.foo == "1"
        assert options.t1.foo == "1"
    
    environment = _set_environment(t1=t1)
    tasks._process_commands(['t1', '--foo', '1'])
    assert t1.called
    
def test_setting_of_options_with_equals():
    @tasks.task
    def t1(options):
        assert options.foo == '1'
        assert not hasattr(options, 'bar')
    
    @tasks.task
    def t2(options):
        assert options.foo == '1'
        assert options.bar == '2'
    
    environment = _set_environment(t1=t1, t2=t2)
    tasks._process_commands(['foo=1', 't1', 'bar=2', 't2'])
    assert t1.called
    assert t2.called
    
def test_options_inherited_via_needs():
    @tasks.task
    @tasks.cmdopts([('foo=', 'f', "Foo!")])
    def t1(options):
        assert options.t1.foo == "1"
    
    @tasks.task
    @tasks.needs('t1')
    @tasks.cmdopts([('bar=', 'b', "Bar!")])
    def t2(options):
        assert options.t2.bar == '2'
        
    environment = _set_environment(t1=t1, t2=t2)
    tasks._process_commands("t2 --foo 1 -b 2".split())
    assert t1.called
    assert t2.called

def test_options_inherited_via_needs_even_from_grandparents():
    @tasks.task
    @tasks.cmdopts([('foo=', 'f', "Foo!")])
    def t1(options):
        assert options.t1.foo == "1"
    
    @tasks.task
    @tasks.needs('t1')
    @tasks.cmdopts([('bar=', 'b', "Bar!")])
    def t2(options):
        assert options.t2.bar == '2'

    @tasks.task
    @tasks.needs('t2')
    @tasks.cmdopts([('spam=', 's', "Spam!")])
    def t3(options):
        assert options.t3.spam == '3'
        
    environment = _set_environment(t1=t1, t2=t2, t3=t3)
    tasks._process_commands("t3 --foo 1 -b 2 -s 3".split())
    assert t1.called
    assert t2.called
    assert t3.called
    
def test_options_shouldnt_overlap():
    @tasks.task
    @tasks.cmdopts([('foo=', 'f', "Foo!")])
    def t1(options):
        assert False
    
    @tasks.task
    @tasks.needs('t1')
    @tasks.cmdopts([('force=', 'f', "Force!")])
    def t2(options):
        assert False
        
    environment = _set_environment(t1=t1, t2=t2)
    try:
        tasks._process_commands("t2 -f 1".split())
        assert False, "should have gotten a PavementError"
    except tasks.PavementError:
        pass

def test_options_shouldnt_overlap_when_bad_task_specified():
    @tasks.task
    @tasks.cmdopts([('foo=', 'f', "Foo!")])
    def t1(options):
        assert False
    
    @tasks.task
    @tasks.needs('t1')
    @tasks.cmdopts([('force=', 'f', "Force!")], share_with=['nonexisting_task'])
    def t2(options):
        assert False
        
    environment = _set_environment(t1=t1, t2=t2)
    try:
        tasks._process_commands("t2 -f 1".split())
        assert False, "should have gotten a PavementError"
    except tasks.PavementError:
        pass

def test_options_may_overlap_if_explicitly_allowed():
    @tasks.task
    @tasks.cmdopts([('foo=', 'f', "Foo!")])
    def t1(options):
        assert options.t1.foo == "1"
    
    @tasks.task
    @tasks.needs('t1')
    @tasks.cmdopts([('foo=', 'f', "Foo!")], share_with=['t1'])
    def t2(options):
        assert options.t2.foo == "1"
        
    environment = _set_environment(t1=t1, t2=t2)

    tasks._process_commands("t2 -f 1".split())

    assert t1.called
    assert t2.called

def test_exactly_same_parameters_must_be_specified_in_order_to_allow_sharing():
    @tasks.task
    @tasks.cmdopts([('foo=', 'f', "Foo!")])
    def t1(options):
        assert False
    
    @tasks.task
    @tasks.needs('t1')
    @tasks.cmdopts([('force=', 'f', "Force!")], share_with=['t1'])
    def t2(options):
        assert False
        
    environment = _set_environment(t1=t1, t2=t2)
    try:
        tasks._process_commands("t2 -f 1".split())
        assert False, "should have gotten a PavementError"
    except tasks.PavementError:
        pass

def test_dest_parameter_should_map_opt_to_property():
    from optparse import make_option as opt

    @tasks.task
    @tasks.cmdopts([opt('-f', '--force', dest='force')])
    def t1(options):
        assert options.force == '1'

    @tasks.task
    @tasks.cmdopts([opt('-f', '--force', dest='foo_force')])
    def t2(options):
        assert options.foo_force == '1'

    environment = _set_environment(t1=t1, t2=t2)
    tasks._process_commands("t1 -f 1".split())
    tasks._process_commands("t2 -f 1".split())
    assert t1.called
    assert t2.called

def test_dotted_options():
    environment = _set_environment()
    tasks._process_commands(['this.is.cool=1'])
    assert environment.options.this['is'].cool == '1'

def test_dry_run():
    environment = _set_environment()
    tasks._process_commands(['-n'])
    assert environment.dry_run

def test_consume_args():
    @tasks.task
    @tasks.consume_args
    def t1(options):
        assert options.args == ["1", "t2", "3"]

    @tasks.task
    def t2(options):
        assert False, "Should not have run t2 because of consume_args"

    env = _set_environment(t1=t1, t2=t2)
    tasks._process_commands("t1 1 t2 3".split())
    assert t1.called

    @tasks.task
    @tasks.consume_args
    def t3(options):
        assert options.args[0] == '-v'
        assert options.args[1] == '1'

    env = _set_environment(t3=t3)
    tasks._process_commands("t3 -v 1".split())
    assert t3.called

def test_consume_nargs():
    # consume all args on first task
    @tasks.task
    @tasks.consume_nargs()
    def t11(options):
        assert options.args == ["1", "t12", "3"]

    @tasks.task
    def t12(options):
        assert False, ("Should not have run t12 because of previous "
                       "consume_nargs()")

    env = _set_environment(t11=t11, t12=t12)
    tasks._process_commands("t11 1 t12 3".split())
    assert t11.called

    # consume some args (specified numbers) on first and second task
    @tasks.task
    @tasks.consume_nargs(2)
    def t21(options):
        assert options.args == ["1", "2"]

    @tasks.task
    @tasks.consume_nargs(3)
    def t22(options):
        assert options.args == ["3", "4", "5"]

    env = _set_environment(t21=t21, t22=t22)
    tasks._process_commands("t21 1 2 t22 3 4 5".split())
    assert t21.called
    assert t22.called

    # not enougth args consumable on called task, and other task not called
    env = _set_environment(t21=t21, t12=t12)
    try:
        tr, args = tasks._parse_command_line("t21 t12".split())
        print_(tr)
        assert False, "Expected BuildFailure exception for not enougth args"
    except tasks.BuildFailure:
        pass

    # too much args passed, and unconsumed args are not tasks
    tr, args = tasks._parse_command_line("t21 1 2 3 4 5".split())
    assert args == ["3", "4", "5"]

    # consume some args (specified numbers) on first and all other on second task
    @tasks.task
    @tasks.consume_nargs(2)
    def t31(options):
        assert options.args == ["1", "2"]

    @tasks.task
    @tasks.consume_nargs()
    def t32(options):
        assert options.args == ["3", "4", "t33", "5"]

    @tasks.task
    @tasks.consume_nargs()
    def t33(options):
        assert False, ("Should not have run t33 because of previous "
                       "consume_nargs()")

    env = _set_environment(t31=t31, t32=t32, t33=t33)
    tasks._process_commands("t31 1 2 t32 3 4 t33 5".split())
    assert t31.called
    assert t32.called

def test_optional_args_in_tasks():
    @tasks.task
    def t1(options, optarg=None):
        assert optarg is None

    @tasks.task
    def t2(options, optarg1='foo', optarg2='bar'):
        assert optarg1 == 'foo'
        assert optarg2 == 'bar'

    env = _set_environment(t1=t1, t2=t2)
    tasks._process_commands(['t1', 't2'])
    assert t1.called
    assert t2.called
    
def test_debug_logging():
    @tasks.task
    def t1(debug):
        debug("Hi %s", "there")
        
    env = _set_environment(t1=t1, patch_print=True)
    tasks._process_commands(['-v', 't1'])
    assert env.patch_captured[-1] == "Hi there"
    env.patch_captured = []
    
    tasks._process_commands(['t1'])
    assert env.patch_captured[-1] != "Hi there"

def test_base_logging():
    @tasks.task
    def t1(info):
        info("Hi %s", "you")
    
    env = _set_environment(t1=t1, patch_print=True)
    tasks._process_commands(['t1'])
    assert env.patch_captured[-1] == 'Hi you'
    env.patch_captured = []
    
    tasks._process_commands(['-q', 't1'])
    assert not env.patch_captured
    
def test_error_show_up_no_matter_what():
    @tasks.task
    def t1(error):
        error("Hi %s", "error")
    
    env = _set_environment(t1=t1, patch_print=True)
    tasks._process_commands(['t1'])
    assert env.patch_captured[-1] == "Hi error"
    env.patch_captured = []
    
    tasks._process_commands(['-q', 't1'])
    assert env.patch_captured[-1] == "Hi error"
    
def test_all_messages_for_a_task_are_captured():
    @tasks.task
    def t1(debug, error):
        debug("This is debug msg")
        error("This is error msg")
        raise tasks.BuildFailure("Yo, problem, yo")
    
    env = _set_environment(t1=t1, patch_print=True)
    try:
        tasks._process_commands(['t1'])
    except FakeExitException:
        assert "This is debug msg" in "\n".join(env.patch_captured)
        assert env.exit_code == 1

def test_messages_with_formatting_and_no_args_still_work():
    @tasks.task
    def t1(error):
        error("This is a %s message")

    env = _set_environment(t1=t1, patch_print=True)
    tasks._process_commands(['t1'])
    assert env.patch_captured[-1] == "This is a %s message"
    env.patch_captured = []

    tasks._process_commands(['-q', 't1'])
    assert env.patch_captured[-1] == "This is a %s message"
    
def test_alternate_pavement_option():
    env = _set_environment()
    tasks._parse_global_options([])
    assert env.pavement_file == 'pavement.py'

    env = _set_environment()
    tasks._parse_global_options(['--file=foo.py'])
    set_pavement = env.pavement_file
    assert set_pavement == 'foo.py'

    env = _set_environment()
    tasks._parse_global_options(['-f', 'foo.py'])
    set_pavement = env.pavement_file
    assert set_pavement == 'foo.py'


def test_captured_output_shows_up_on_exception():
    @tasks.task
    def t1(debug, error):
        debug("Dividing by zero!")
        1/0
    
    env = _set_environment(t1=t1, patch_print=True, patch_exit=1)
    try:
        tasks._process_commands(['t1'])
        assert False and "Expecting FakeExitException"
    except FakeExitException:
        assert "Dividing by zero!" in "\n".join(env.patch_captured)
        assert env.exit_code == 1
    
def test_calling_subpavement():
    @tasks.task
    def private_t1(options):
        options.foo = 2
        tasks.call_pavement(subpavement, "t1")
        # our options should not be mangled
        assert options.foo == 2
    
    env = _set_environment(private_t1=private_t1)
    tasks._process_commands(['private_t1'])
    # the value should be set by the other pavement, which runs
    # in the same process
    assert OP_T1_CALLED == 1

class MyTaskFinder(object):
    def get_task(self, name):
        if name == "foo":
            return self.foo
        return None
        
    def get_tasks(self):
        return set([self.foo])
    
    @tasks.task
    def foo(self):
        self.foo_called = True
    
def test_task_finders():
    env = _set_environment()
    mtf = MyTaskFinder()
    env.task_finders.append(mtf)
    t = env.get_task("foo")
    assert t == mtf.foo
    all_tasks = env.get_tasks()
    assert mtf.foo in all_tasks
    
def test_calling_a_function_rather_than_task():
    def foo():
        pass
        
    env = _set_environment(foo=foo)
    try:
        tasks._process_commands(['foo'])
        assert False, "Expected a BuildFailure when calling something that is not a task."
    except tasks.BuildFailure:
        pass

def test_depending_on_a_function_rather_than_task():
    def bar():
        pass

    @tasks.task
    @tasks.needs('bar')
    def foo():
        pass

    env = _set_environment(foo=foo, bar=bar)
    try:
        tasks._process_commands(['foo'])
        assert False, "Expected a BuildFailure when depending on something that is not a task."
    except tasks.BuildFailure:
        pass

def test_description_retrieval_trial():
    @tasks.task
    def t1():
        """ Task it is """
    
    assert t1.description == "Task it is"

def test_description_empty_without_docstring():
    @tasks.task
    def t1():
        pass
    
    assert t1.description == ""

def test_description_retrieval_first_sentence():
    @tasks.task
    def t1():
        """ Task it is. Not with another sentence. """
    
    assert t1.description == "Task it is"

def test_description_retrieval_first_sentence_even_with_version_numbers():
    @tasks.task
    def t1():
        """ Task it is, installs Django 1.0. Not with another sentence. """
    
    assert t1.description == "Task it is, installs Django 1.0"

def test_auto_task_is_not_run_with_noauto():
    @tasks.no_auto
    @tasks.task
    def t1():
        pass

    @tasks.task
    def auto():
        pass

    _set_environment(auto=auto, t1=t1)
    tasks._process_commands(['t1'], auto_pending=True)
    
    assert t1.called
    assert not auto.called, "t1 is decorated with no_auto, it should not be called"

def test_auto_task_is_run_when_present():
    @tasks.task
    def t1():
        pass

    @tasks.task
    def auto():
        pass

    _set_environment(auto=auto, t1=t1)
    tasks._process_commands(['t1'], auto_pending=True)

    assert t1.called
    assert auto.called

def test_task_can_be_called_repeatedly():
    @tasks.consume_args
    @tasks.task
    def t1(options, info):
        info(options.args[0])

    env = _set_environment(t1=t1, patch_print=True)
    
    tasks._process_commands(['t1', 'spam'])
    tasks._process_commands(['t1', 'eggs'])

    assert 'eggs' == env.patch_captured[~0]
    assert 'spam' == env.patch_captured[~2]


def test_options_passed_to_task():
    from optparse import make_option

    @tasks.task
    @tasks.cmdopts([
        make_option("-f", "--foo", help="foo")
    ])
    def t1(options):
        assert options.foo == "1"
        assert options.t1.foo == "1"

    environment = _set_environment(t1=t1)
    tasks._process_commands(['t1', '--foo', '1'])
    assert t1.called

# We could mock stdout/err, but seriously -- to integration test for this one
# once integration test suite is merged into master

#def test_hiding_from_help():
#    @tasks.task
#    @tasks.no_help
#    def hidden_task(options):
#        pass
#
#    environment = _set_environment(hidden_task=hidden_task, help=tasks.help)
#    args = tasks._parse_global_options(['-h'])
#    output = tasks._process_commands(args)
#
#    assert 'hidden_task' not in output

def test_calling_task_with_option_arguments():
    @tasks.task
    @tasks.cmdopts([('foo=', 'f', "Foo!")])
    def t1(options):
        assert options.foo == 'true story'

    env = _set_environment(t1=t1)

    env.call_task('t1', options={
        'foo' : 'true story'
    })

def test_calling_task_with_arguments_do_not_overwrite_it_for_other_tasks():
    @tasks.task
    @tasks.cmdopts([('foo=', 'f', "Foo!")])
    def t3(options):
        assert options.foo == 'cool story'

    @tasks.task
    @tasks.cmdopts([('foo=', 'f', "Foo!")])
    def t2(options):
        assert options.foo == 'true'


    @tasks.task
    @tasks.needs('t2')
    def t1(options):
        env.call_task('t3', options={
            'foo' : 'cool story'
        })

    env = _set_environment(t1=t1, t2=t2, t3=t3)

    tasks._process_commands(['t1', '--foo', 'true'])


def test_options_might_be_provided_if_task_might_be_called():

    @tasks.task
    @tasks.cmdopts([('foo=', 'f', "Foo!")])
    def t1(options):
        assert options.foo == "YOUHAVEBEENFOOD"

    @tasks.task
    @tasks.might_call('t1')
    def t2(options):
        pass

    environment = _set_environment(t1=t1, t2=t2)
    tasks._process_commands("t2 -f YOUHAVEBEENFOOD".split())

def test_calling_task_with_arguments():
    @tasks.task
    @tasks.consume_args
    def t2(args):
        assert args[0] == 'SOPA'


    @tasks.task
    def t1(options):
        env.call_task('t2', args=['SOPA'])

    env = _set_environment(t1=t1, t2=t2)

    tasks._process_commands(['t1'])

def test_calling_nonconsuming_task_with_arguments():
    @tasks.task
    def t2():
        pass

    @tasks.task
    def t1():
        env.call_task('t2')

    env = _set_environment(t1=t1, t2=t2)

    try:
        env.call_task('t1', args=['fail'])
    except tasks.BuildFailure:
        pass
    else:
        assert False, ("Task without @consume_args canot be called with them "
                      "(BuildFailure should be raised)")

def test_options_may_overlap_between_multiple_tasks_even_when_specified_in_reverse_order():
    @tasks.task
    @tasks.cmdopts([('foo=', 'f', "Foo!")], share_with=['t2', 't3'])
    def t1(options):
        assert options.t1.foo == "1"

    @tasks.task
    @tasks.needs('t1')
    @tasks.cmdopts([('foo=', 'f', "Foo!")])
    def t2(options):
        assert options.t2.foo == "1"

    @tasks.task
    @tasks.needs('t1')
    @tasks.cmdopts([('foo=', 'f', "Foo!")])
    def t3(options):
        assert options.t3.foo == "1"

    environment = _set_environment(t1=t1, t2=t2, t3=t3)

    tasks._process_commands("t2 -f 1".split())

    assert t1.called
    assert t2.called

    tasks._process_commands("t3 -f 1".split())

    assert t1.called
    assert t3.called


def test_options_might_be_shared_both_way():
    @tasks.task
    @tasks.cmdopts([('foo=', 'f', "Foo!")], share_with=['t2'])
    def t1(options):
        assert options.t1.foo == "1"

    @tasks.task
    @tasks.needs('t1')
    @tasks.cmdopts([('foo=', 'f', "Foo!")], share_with=['t1'])
    def t2(options):
        assert options.t2.foo == "1"

    environment = _set_environment(t1=t1, t2=t2)

    tasks._process_commands("t2 -f 1".split())

    assert t1.called
    assert t2.called

########NEW FILE########
__FILENAME__ = utils
import types
import paver.deps.six as six

from paver import setuputils, tasks

class FakeModule(object):
    def __init__(self, **kw):
        for name, value in kw.items():
            setattr(self, name, value)

def patched_print(self, output):
    self.patch_captured.append(output)

class FakeExitException(Exception):
    """ Fake out tasks.Environment._exit to avoid interupting tests """

def patched_exit(self, code):
    self.exit_code = 1
    raise FakeExitException(code)


def _set_environment(patch_print=False, **kw):
    pavement = FakeModule(**kw)
    env = tasks.Environment(pavement)
    tasks.environment = env
    if six.PY3:
        method_args = (env,)
    else:
        method_args = (env, tasks.Environment)
    env._exit = types.MethodType(patched_exit, *method_args)
    if patch_print:
        env._print = types.MethodType(patched_print, *method_args)
        env.patch_captured = []
    return env


########NEW FILE########
__FILENAME__ = version
VERSION='1.2.2'

########NEW FILE########
__FILENAME__ = virtual
"""Tasks for managing virtualenv environments."""
from paver.easy import task, options, dry, debug
from paver.release import setup_meta

try:
    import virtualenv as venv
except ImportError:
    has_virtualenv = False
else:
    has_virtualenv = True

_pip_then_easy_install_tmpl = """
    try:
        subprocess.call(
            [join(%(bin_dir_var)s, 'pip'), 'install']
            + %(cmd_options)r
            + %%(packages)r
        )
    except OSError:
        subprocess.call(
            [join(%(bin_dir_var)s, 'easy_install')]
            + %(cmd_options)r
            + %%(packages)r
        )
"""
_easy_install_tmpl = """
    subprocess.call(
        [join(%(bin_dir_var)s, 'easy_install')]
        + %(cmd_options)r
        + %%(packages)r
    )
"""
def _create_bootstrap(script_name, packages_to_install, paver_command_line,
                      install_paver=True, more_text="", dest_dir='.',
                      no_site_packages=None, system_site_packages=None,
                      unzip_setuptools=False, distribute=None, index_url=None,
                      no_index=False, find_links=None, prefer_easy_install=False):
    # configure package installation template
    install_cmd_options = []
    if index_url:
        install_cmd_options.extend(['--index-url', index_url])
    if no_index:
        install_cmd_options.extend(['--no-index'])
    if find_links:
        for link in find_links:
            install_cmd_options.extend(
                ['--find-links', link])
    install_cmd_tmpl = (_easy_install_tmpl if prefer_easy_install
                        else _pip_then_easy_install_tmpl)
    confd_install_cmd_tmpl = (install_cmd_tmpl %
        {'bin_dir_var': 'bin_dir', 'cmd_options': install_cmd_options})
    # make copy to local scope to add paver to packages to install
    packages_to_install = packages_to_install[:]
    if install_paver:
        packages_to_install.insert(0, 'paver==%s' % setup_meta['version'])
    install_cmd = confd_install_cmd_tmpl % {'packages': packages_to_install}

    options = ""
    # if deprecated 'no_site_packages' was specified and 'system_site_packages'
    # wasn't, set it from that value
    if system_site_packages is None and no_site_packages is not None:
        system_site_packages = not no_site_packages
    if system_site_packages is not None:
        options += ("    options.system_site_packages = %s\n" %
                    bool(system_site_packages))
    if unzip_setuptools:
        options += "    options.unzip_setuptools = True\n"
    if distribute is not None:
        options += "    options.use_distribute = %s\n" % bool(distribute)
    options += "\n"

    extra_text = """def adjust_options(options, args):
    args[:] = ['%s']
%s
def after_install(options, home_dir):
    if sys.platform == 'win32':
        bin_dir = join(home_dir, 'Scripts')
    else:
        bin_dir = join(home_dir, 'bin')
%s""" % (dest_dir, options, install_cmd)
    if paver_command_line:
        command_list = list(paver_command_line.split())
        extra_text += "    subprocess.call([join(bin_dir, 'paver'),%s)" % repr(command_list)[1:]

    extra_text += more_text
    bootstrap_contents = venv.create_bootstrap_script(extra_text)
    fn = script_name

    debug("Bootstrap script extra text: " + extra_text)
    def write_script():
        open(fn, "w").write(bootstrap_contents)
    dry("Write bootstrap script %s" % fn, write_script)


def _boostrap_constraint():
    try:
        import virtualenv as venv
    except ImportError:
        from paver.runtime import PaverImportError
        raise PaverImportError("`virtualenv` is needed to use paver's virtualenv tasks")


@task
def bootstrap():
    """Creates a virtualenv bootstrap script.
    The script will create a bootstrap script that populates a
    virtualenv in the current directory. The environment will
    have paver, the packages of your choosing and will run
    the paver command of your choice.

    This task looks in the virtualenv options for:

    script_name
        name of the generated script
    packages_to_install
        packages to install with pip/easy_install. The version of paver that
        you are using is included automatically. This should be a list of
        strings.
    paver_command_line
        run this paver command line after installation (just the command
        line arguments, not the paver command itself).
    dest_dir
        the destination directory for the virtual environment (defaults to
        '.')
    no_site_packages
        don't give access to the global site-packages dir to the virtual
        environment (default; deprecated)
    system_site_packages
        give access to the global site-packages dir to the virtual
        environment
    unzip_setuptools
        unzip Setuptools when installing it (defaults to False)
    distribute
        use Distribute instead of Setuptools. Set environment variable
        VIRTUALENV_DISTRIBUTE to make it the default.
    index_url
        base URL of Python Package Index
    no_index
        ignore package index (only looking at find_links URL(s) instead)
    find_links
        additional URL(s) to search for packages. This should be a list of
        strings.
    prefer_easy_install
        prefer easy_install to pip for package installation if both are
        installed (defaults to False)
    """
    vopts = options.virtualenv
    _create_bootstrap(vopts.get("script_name", "bootstrap.py"),
                      vopts.get("packages_to_install", []),
                      vopts.get("paver_command_line", None),
                      dest_dir=vopts.get("dest_dir", '.'),
                      no_site_packages=vopts.get("no_site_packages", None),
                      system_site_packages=vopts.get("system_site_packages",
                                                     None),
                      unzip_setuptools=vopts.get("unzip_setuptools", False),
                      distribute=vopts.get("distribute", None),
                      index_url=vopts.get("index_url", None),
                      no_index=vopts.get("no_index", False),
                      find_links=vopts.get("find_links", []),
                      prefer_easy_install=vopts.get("prefer_easy_install",
                                                    False))
bootstrap.paver_constraint = _boostrap_constraint

def virtualenv(dir):
    """Run decorated task in specified virtual environment."""
    def inner(func):
        func = task(func)
        func.use_virtualenv = True
        func.virtualenv_dir = dir
        return func
    return inner

########NEW FILE########
__FILENAME__ = test_virtualenv
from __future__ import with_statement
from unittest2 import TestCase

from os import chdir, getcwd, pardir, environ
from os.path import join, dirname, exists
from shutil import rmtree, copyfile
from subprocess import check_call, PIPE
import sys
from tempfile import mkdtemp

class TestVirtualenvTaskSpecification(TestCase):

    def setUp(self):
        super(TestVirtualenvTaskSpecification, self).setUp()

        if 'TRAVIS_PYTHON_VERSION' in environ and environ['TRAVIS_PYTHON_VERSION'] in ('jython', 'pypy'):
            from nose import SkipTest
            raise SkipTest("%s virtual tests not yet supported" % environ['TRAVIS_PYTHON_VERSION'])

        self.basedir = mkdtemp(prefix="test_paver_venv")
        self.oldcwd = getcwd()

    def _prepare_virtualenv(self):
        """
        Prepare paver virtual environment in self.basedir.
        Use distribution's bootstrap to do so.
        """
        copyfile(join(dirname(__file__), pardir, "bootstrap.py"), join(self.basedir, "bootstrap.py"))
        check_call([sys.executable, join(self.basedir, "bootstrap.py")], stdout=PIPE, stderr=PIPE, cwd=self.basedir)

    def test_running_task_in_specified_virtualenv(self):
        self._prepare_virtualenv()
        if sys.platform == 'win32':
            site_packages = join(self.basedir, 'virtualenv', 'Lib', 'site-packages')
        else:
            site_packages = join(self.basedir, 'virtualenv', 'lib', 'python%s' % sys.version[:3], 'site-packages')

        # just create the file
        with open(join(site_packages,  "some_venv_module.py"), "w"):
            pass

        subpavement = """
from paver import tasks
from paver.virtual import virtualenv

@tasks.task
@virtualenv(dir="%s")
def t1():
    import some_venv_module
""" % join(self.basedir, "virtualenv")

        pavement_dir = mkdtemp(prefix="unrelated_pavement_module_")

        try:
            with open(join(pavement_dir, "pavement.py"), "w") as f:
                f.write(subpavement)

            chdir(pavement_dir)

            paver_bin = join(dirname(__file__), pardir, 'distutils_scripts', 'paver')
            # FIXME: Will this work on windows?
            if 'VIRTUAL_ENV' in environ and exists(join(environ['VIRTUAL_ENV'], "bin", "python")):
                python_bin = join(environ['VIRTUAL_ENV'], "bin", "python")
            else:
                python_bin = "python"
            check_call([python_bin, paver_bin, "t1"],
                env={
                    'PYTHONPATH' : join(dirname(__file__), pardir),
                    'PATH': environ['PATH']
                })

        finally:
            rmtree(pavement_dir)


    def tearDown(self):
        chdir(self.oldcwd)
        rmtree(self.basedir)

        super(TestVirtualenvTaskSpecification, self).tearDown()

########NEW FILE########
