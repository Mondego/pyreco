__FILENAME__ = basecommand
import os
import sys
import re
from optparse import OptionParser
from pythonbrew import commands

command_dict = {}

class Command(object):
    name = None
    usage = None
    summary = ""
    
    def __init__(self):
        self.parser = OptionParser(usage=self.usage,
                                   prog='%s %s' % ("pythonbrew", self.name))
        command_dict[self.name] = self
        
    def run(self, args):
        options, args = self.parser.parse_args(args)
        self.run_command(options, args)

def load_command(name):
    full_name = 'pythonbrew.commands.%s' % name
    if full_name in sys.modules:
        return
    try:
        __import__(full_name)
    except ImportError:
        pass

def load_all_commands():
    for name in command_names():
        load_command(name)

def command_names():
    return [path[:-3] for path in os.listdir(commands.__path__[0]) if not re.match("(__init__\.py$|.*\.pyc$)", path)]

########NEW FILE########
__FILENAME__ = baseparser
from optparse import OptionParser
from pythonbrew.define import VERSION

parser = OptionParser(usage="%prog COMMAND [OPTIONS]",
                      prog="pythonbrew",
                      version=VERSION,
                      add_help_option=False)
parser.add_option(
    '-h', '--help',
    dest='help',
    action='store_true',
    help='Show help')
parser.disable_interspersed_args()

########NEW FILE########
__FILENAME__ = buildout
import os
import sys
import subprocess
from pythonbrew.basecommand import Command
from pythonbrew.define import PATH_PYTHONS, BOOTSTRAP_DLSITE
from pythonbrew.util import Package, get_using_python_pkgname, Link, is_installed
from pythonbrew.log import logger
from pythonbrew.downloader import Downloader

class BuildoutCommand(Command):
    name = "buildout"
    usage = "%prog"
    summary = "Runs the buildout with specified or current using python"
    
    def __init__(self):
        super(BuildoutCommand, self).__init__()
        self.parser.add_option(
            "-p", "--python",
            dest="python",
            default=None,
            help="Use the specified version of python.",
            metavar='VERSION'
        )
    
    def run_command(self, options, args):
        if options.python:
            pkgname = Package(options.python).name
        else:
            pkgname = get_using_python_pkgname()
        if not is_installed(pkgname):
            logger.error('`%s` is not installed.' % pkgname)
            sys.exit(1)
        logger.info('Using %s' % pkgname)
        
        # build a path
        python = os.path.join(PATH_PYTHONS, pkgname, 'bin', 'python')
        
        # Download bootstrap.py
        download_url = BOOTSTRAP_DLSITE
        filename = Link(download_url).filename
        bootstrap = os.path.join(os.getcwd(), filename) # fetching into current directory
        try:
            d = Downloader()
            d.download(filename, download_url, bootstrap)
        except:
            e = sys.exc_info()[1]
            logger.error("%s" % (e))
            sys.exit(1)

        # call bootstrap.py
        if subprocess.call([python, bootstrap, '-d']):
            logger.error('Failed to bootstrap.')
            sys.exit(1)

        # call buildout
        subprocess.call(['./bin/buildout'])

BuildoutCommand()

########NEW FILE########
__FILENAME__ = cleanup
import os
from pythonbrew.basecommand import Command
from pythonbrew.define import PATH_BUILD, PATH_DISTS
from pythonbrew.util import rm_r

class CleanupCommand(Command):
    name = "cleanup"
    usage = "%prog"
    summary = "Remove stale source folders and archives"
    
    def run_command(self, options, args):
        self._cleanup(PATH_BUILD)
        self._cleanup(PATH_DISTS)
        
    def _cleanup(self, root):
        for dir in os.listdir(root):
            rm_r(os.path.join(root, dir))

CleanupCommand()

########NEW FILE########
__FILENAME__ = help
from pythonbrew.basecommand import Command, command_dict
from pythonbrew.baseparser import parser
from pythonbrew.log import logger

class HelpCommand(Command):
    name = "help"
    usage = "%prog [COMMAND]"
    summary = "Show available commands"
    
    def run_command(self, options, args):
        if args:
            command = args[0]
            if command not in command_dict:
                parser.error("Unknown command: `%s`" % command)
                return
            command = command_dict[command]
            command.parser.print_help()
            return
        parser.print_help()
        logger.log("\nCommands available:")
        commands = [command_dict[key] for key in sorted(command_dict.keys())]
        for command in commands:
            logger.log("  %s: %s" % (command.name, command.summary))
        logger.log("\nFurther Instructions:")
        logger.log("  https://github.com/utahta/pythonbrew")

HelpCommand()

########NEW FILE########
__FILENAME__ = install
import sys
from pythonbrew.basecommand import Command
from pythonbrew.installer.pythoninstaller import PythonInstaller,\
    PythonInstallerMacOSX
from pythonbrew.util import is_macosx

class InstallCommand(Command):
    name = "install"
    usage = "%prog [OPTIONS] VERSION"
    summary = "Build and install the given version of python"
    
    def __init__(self):
        super(InstallCommand, self).__init__()
        self.parser.add_option(
            "-f", "--force",
            dest="force",
            action="store_true",
            default=False,
            help="Force installation of python."
        )
        self.parser.add_option(
            "-t", "--test",
            dest="test",
            action="store_true",
            default=False,
            help="Running `make test`."
        )
        self.parser.add_option(
            "-v", "--verbose",
            dest="verbose",
            action="store_true",
            default=False,
            help="Display log information on the console."
        )
        self.parser.add_option(
            "-C", "--configure",
            dest="configure",
            default="",
            metavar="CONFIGURE_OPTIONS",
            help="Options passed directly to configure."
        )
        self.parser.add_option(
            "--no-setuptools",
            dest="no_setuptools",
            action="store_true",
            default=False,
            help="Skip installation of setuptools."
        )
        self.parser.add_option(
            "--as",
            dest="alias",
            default=None,
            help="Install a python under an alias."
        )
        self.parser.add_option(
            '-j', "--jobs",
            dest="jobs",
            type='int',
            default=0,
            help="Enable parallel make."
        )
        self.parser.add_option(
            "--framework",
            dest="framework",
            action="store_true",
            default=False,
            help="Build (MacOSX|Darwin) framework."
        )
        self.parser.add_option(
            "--universal",
            dest="universal",
            action="store_true",
            default=False,
            help="Build for both 32 & 64 bit Intel."
        )
        self.parser.add_option(
            "--static",
            dest="static",
            action="store_true",
            default=False,
            help="Build static libraries."
        )

    def run_command(self, options, args):
        if not args:
            self.parser.print_help()
            sys.exit(1)
        # installing python
        for arg in args:
            try:
                if is_macosx():
                    p = PythonInstallerMacOSX(arg, options)
                else:
                    p = PythonInstaller(arg, options)
                p.install()
            except:
                continue

InstallCommand()

########NEW FILE########
__FILENAME__ = list
import os
import re
from pythonbrew.basecommand import Command
from pythonbrew.define import PYTHON_VERSION_URL, LATEST_VERSIONS_OF_PYTHON,\
    PATH_PYTHONS
from pythonbrew.util import Package, get_using_python_pkgname
from pythonbrew.log import logger

class ListCommand(Command):
    name = "list"
    usage = "%prog [VERSION]"
    summary = "List the installed all pythons"
    
    def __init__(self):
        super(ListCommand, self).__init__()
        self.parser.add_option(
            '-a', '--all-versions',
            dest='all_versions',
            action='store_true',
            default=False,
            help='Show the all python versions.'
        )
        self.parser.add_option(
            '-k', '--known',
            dest='known',
            action='store_true',
            default=False,
            help='List the available latest python versions.'
        )
    
    def run_command(self, options, args):
        if options.known:
            self.available_install(options, args)
        else:
            self.installed(options, args)
    
    def installed(self, options, args):
        logger.log("# pythonbrew pythons")
        cur = get_using_python_pkgname()
        for d in sorted(os.listdir(PATH_PYTHONS)):
            if cur and cur == d:
                logger.log('  %s (*)' % d)
            else:
                logger.log('  %s' % d)
    
    def available_install(self, options, args):
        logger.log('# Pythons')
        if args:
            pkg = Package(args[0])
            _re = re.compile(r"%s" % pkg.name)
            pkgs = []
            for pkgname in self._get_packages_name(options):
                if _re.match(pkgname):
                    pkgs.append(pkgname)
            if pkgs:
                for pkgname in pkgs:
                    logger.log("%s" % pkgname)
            else:
                logger.error("`%s` was not found." % pkg.name)
        else:
            for pkgname in self._get_packages_name(options):
                logger.log("%s" % pkgname)
    
    def _get_packages_name(self, options):
        return ["Python-%s" % version for version in sorted(PYTHON_VERSION_URL.keys()) 
                if(options.all_versions or (not options.all_versions and version in LATEST_VERSIONS_OF_PYTHON))]

ListCommand()

########NEW FILE########
__FILENAME__ = off
from pythonbrew.basecommand import Command
from pythonbrew.util import off

class OffCommand(Command):
    name = "off"
    usage = "%prog"
    summary = "Disable pythonbrew"
    
    def run_command(self, options, args):
        off()

OffCommand()

########NEW FILE########
__FILENAME__ = py
import os
import sys
import subprocess
from pythonbrew.basecommand import Command
from pythonbrew.define import PATH_PYTHONS
from pythonbrew.util import Package
from pythonbrew.log import logger

class PyCommand(Command):
    name = "py"
    usage = "%prog PYTHON_FILE"
    summary = "Runs a named python file against specified and/or all pythons"
    
    def __init__(self):
        super(PyCommand, self).__init__()
        self.parser.add_option(
            "-p", "--python",
            dest="pythons",
            action="append",
            default=[],
            help="Use the specified python version.",
            metavar='VERSION'
        )
        self.parser.add_option(
            "-v", "--verbose",
            dest="verbose",
            action="store_true",
            default=False,
            help="Show the running python version."
        )
        self.parser.disable_interspersed_args()
    
    def run_command(self, options, args):
        if not args:
            self.parser.print_help()
            sys.exit(1)
        pythons = self._get_pythons(options.pythons)
        for d in pythons:
            if options.verbose:
                logger.info('`%s` running...' % d)
            path = os.path.join(PATH_PYTHONS, d, 'bin', args[0])
            if os.path.isfile(path) and os.access(path, os.X_OK):
                subprocess.call([path] + args[1:])
            else:
                path = os.path.join(PATH_PYTHONS, d, 'bin', 'python')
                if os.path.isfile(path) and os.access(path, os.X_OK):
                    subprocess.call([path] + args)
                else:
                    logger.error('%s: No such file or directory.' % path)
    
    def _get_pythons(self, _pythons):
        pythons = [Package(p).name for p in _pythons]
        return [d for d in sorted(os.listdir(PATH_PYTHONS))
                if not pythons or d in pythons]

PyCommand()

########NEW FILE########
__FILENAME__ = switch
import os
import sys
from pythonbrew.basecommand import Command
from pythonbrew.define import PATH_PYTHONS
from pythonbrew.util import Package, set_current_path, is_installed
from pythonbrew.log import logger

class SwitchCommand(Command):
    name = "switch"
    usage = "%prog VERSION"
    summary = "Permanently use the specified python as default"

    def run_command(self, options, args):
        if not args:
            self.parser.print_help()
            sys.exit(1)

        pkg = Package(args[0])
        pkgname = pkg.name
        if not is_installed(pkgname):
            logger.error("`%s` is not installed." % pkgname)
            sys.exit(1)
        pkgbin = os.path.join(PATH_PYTHONS,pkgname,'bin')
        pkglib = os.path.join(PATH_PYTHONS,pkgname,'lib')

        set_current_path(pkgbin, pkglib)

        logger.info("Switched to %s" % pkgname)

SwitchCommand()

########NEW FILE########
__FILENAME__ = symlink
import os
import sys
from pythonbrew.basecommand import Command
from pythonbrew.define import PATH_PYTHONS, PATH_BIN, PATH_VENVS
from pythonbrew.util import Package, symlink, unlink, get_using_python_pkgname,\
    is_installed
from pythonbrew.log import logger

class SymlinkCommand(Command):
    name = "symlink"
    usage = "%prog [OPTIONS] [SCRIPT]"
    summary = "Create/Remove a symbolic link on your $PATH"
    
    def __init__(self):
        super(SymlinkCommand, self).__init__()
        self.parser.add_option(
            "-p", "--python",
            dest="pythons",
            action="append",
            default=[],
            help="Use the specified python version.",
            metavar='VERSION'
        )
        self.parser.add_option(
            "-r", "--remove",
            dest="remove",
            action="store_true",
            default=False,
            help="Remove the all symbolic link."
        )
        self.parser.add_option(
            "-d", "--default",
            dest="default",
            default=None,
            help="Use as default the specified python version."
        )
        self.parser.add_option(
            "-v", "--venv",
            dest="venv",
            default=None,
            help="Use the virtual environment python."
        )
    
    def run_command(self, options, args):
        if options.default:
            # create only one instance as default of an application.
            pythons = self._get_pythons([options.default])
            for pkgname in pythons:
                if args:
                    bin = args[0]
                    self._symlink(bin, bin, pkgname)
                else:
                    self._symlink('python', 'py', pkgname)
        elif options.venv:
            if options.pythons:
                pkgname = Package(options.pythons[0]).name
            else:
                pkgname = get_using_python_pkgname()
            if not is_installed(pkgname):
                logger.error('`%s` is not installed.')
                sys.exit(1)
            
            venv_pkgdir = os.path.join(PATH_VENVS, pkgname)
            venv_dir = os.path.join(venv_pkgdir, options.venv)
            if not os.path.isdir(venv_dir):
                logger.error("`%s` environment was not found in %s." % (options.venv, venv_pkgdir))
                sys.exit(1)
            pkg = Package(pkgname)
            if args:
                bin = args[0]
                dstbin = '%s%s-%s' % (bin, pkg.version, options.venv)
                self._symlink(bin, dstbin, pkgname)
            else:
                dstbin = 'py%s-%s' % (pkg.version, options.venv)
                self._symlink('python', dstbin, pkgname)
        else:
            pythons = self._get_pythons(options.pythons)
            for pkgname in pythons:
                if options.remove:
                    # remove symlinks
                    for bin in os.listdir(PATH_BIN):
                        path = os.path.join(PATH_BIN, bin)
                        if os.path.islink(path):
                            unlink(path)
                else:
                    # create symlinks
                    if args:
                        bin = args[0]
                        self._symlink_version_suffix(bin, bin, pkgname)
                    else:
                        self._symlink_version_suffix('python', 'py', pkgname)
                    
    def _symlink_version_suffix(self, srcbin, dstbin, pkgname):
        """Create a symlink. add version suffix.
        """
        version = Package(pkgname).version
        dstbin = '%s%s' % (dstbin, version)
        self._symlink(srcbin, dstbin, pkgname)
    
    def _symlink(self, srcbin, dstbin, pkgname):
        """Create a symlink.
        """
        src = os.path.join(PATH_PYTHONS, pkgname, 'bin', srcbin)
        dst = os.path.join(PATH_BIN, dstbin)
        if os.path.isfile(src):
            symlink(src, dst)
        else:
            logger.error("%s was not found in your path." % src)
    
    def _get_pythons(self, _pythons):
        """Get the installed python versions list.
        """
        pythons = [Package(p).name for p in _pythons]
        return [d for d in sorted(os.listdir(PATH_PYTHONS)) 
                if not pythons or d in pythons]

SymlinkCommand()

########NEW FILE########
__FILENAME__ = uninstall
import os
from pythonbrew.basecommand import Command
from pythonbrew.define import PATH_PYTHONS, PATH_BIN, PATH_VENVS
from pythonbrew.util import off, rm_r, Package, get_using_python_pkgname, unlink,\
    is_installed
from pythonbrew.log import logger

class UninstallCommand(Command):
    name = "uninstall"
    usage = "%prog VERSION"
    summary = "Uninstall the given version of python"
    
    def run_command(self, options, args):
        if args:
            # Uninstall pythons
            for arg in args:
                pkg = Package(arg)
                pkgname = pkg.name
                pkgpath = os.path.join(PATH_PYTHONS, pkgname)
                venvpath = os.path.join(PATH_VENVS, pkgname)
                if not is_installed(pkgname):
                    logger.error("`%s` is not installed." % pkgname)
                    continue
                if get_using_python_pkgname() == pkgname:
                    off()
                for d in os.listdir(PATH_BIN):
                    # remove symlink
                    path = os.path.join(PATH_BIN, d)
                    if os.path.islink(path):
                        basename = os.path.basename(os.path.realpath(path))
                        tgtpath = os.path.join(pkgpath, 'bin', basename)
                        if os.path.isfile(tgtpath) and os.path.samefile(path, tgtpath):
                            unlink(path)
                rm_r(pkgpath)
                rm_r(venvpath)
        else:
            self.parser.print_help()

UninstallCommand()

########NEW FILE########
__FILENAME__ = update
import os
import sys
from pythonbrew.basecommand import Command
from pythonbrew.define import PATH_DISTS, VERSION, ROOT,\
    PATH_BUILD, PYTHONBREW_UPDATE_URL_CONFIG, PATH_ETC_CONFIG
from pythonbrew.log import logger
from pythonbrew.downloader import Downloader, get_pythonbrew_update_url,\
    get_stable_version, get_headerinfo_from_url
from pythonbrew.util import rm_r, extract_downloadfile, Link, is_gzip, Subprocess, Version

class UpdateCommand(Command):
    name = "update"
    usage = "%prog"
    summary = "Update the pythonbrew to the latest version"
    
    def __init__(self):
        super(UpdateCommand, self).__init__()
        self.parser.add_option(
            '--master',
            dest='master',
            action='store_true',
            default=False,
            help='Update the pythonbrew to the `master` branch on github.'
        )
        self.parser.add_option(
            '--config',
            dest='config',
            action='store_true',
            default=False,
            help='Update config.cfg.'
        )
        self.parser.add_option(
            '-f', '--force',
            dest='force',
            action='store_true',
            default=False,
            help='Force update the pythonbrew.'
        )
    
    def run_command(self, options, args):
        if options.config:
            self._update_config(options, args)
        else:
            self._update_pythonbrew(options, args)
    
    def _update_config(self, options, args):
        # config.cfg update
        # TODO: Automatically create for config.cfg
        download_url = PYTHONBREW_UPDATE_URL_CONFIG
        if not download_url:
            logger.error("Invalid download url in config.cfg. `%s`" % download_url)
            sys.exit(1)
        distname = Link(PYTHONBREW_UPDATE_URL_CONFIG).filename
        download_file = PATH_ETC_CONFIG
        try:
            d = Downloader()
            d.download(distname, download_url, download_file)
        except:
            logger.error("Failed to download. `%s`" % download_url)
            sys.exit(1)
        logger.log("The config.cfg has been updated.")
    
    def _update_pythonbrew(self, options, args):
        if options.master:
            version = 'master'
        else:
            version = get_stable_version()
            # check for version
            if not options.force and Version(version) <= VERSION:
                logger.info("You are already running the installed latest version of pythonbrew.")
                return
        
        download_url = get_pythonbrew_update_url(version)
        if not download_url:
            logger.error("`pythonbrew-%s` was not found in pypi." % version)
            sys.exit(1)
        headinfo = get_headerinfo_from_url(download_url)
        content_type = headinfo['content-type']
        if not options.master:
            if not is_gzip(content_type, Link(download_url).filename):
                logger.error("content type should be gzip. content-type:`%s`" % content_type)
                sys.exit(1)
        
        filename = "pythonbrew-%s" % version
        distname = "%s.tgz" % filename
        download_file = os.path.join(PATH_DISTS, distname)
        try:
            d = Downloader()
            d.download(distname, download_url, download_file)
        except:
            logger.error("Failed to download. `%s`" % download_url)
            sys.exit(1)
        
        extract_dir = os.path.join(PATH_BUILD, filename)
        rm_r(extract_dir)
        if not extract_downloadfile(content_type, download_file, extract_dir):
            sys.exit(1)
        
        try:
            logger.info("Installing %s into %s" % (extract_dir, ROOT))
            s = Subprocess()
            s.check_call([sys.executable, os.path.join(extract_dir,'pythonbrew_install.py'), '--upgrade'])
        except:
            logger.error("Failed to update pythonbrew.")
            sys.exit(1)
        logger.info("The pythonbrew has been updated.")

UpdateCommand()

########NEW FILE########
__FILENAME__ = use
import os
import sys
from pythonbrew.basecommand import Command
from pythonbrew.define import PATH_PYTHONS, PATH_HOME_ETC_TEMP
from pythonbrew.util import Package
from pythonbrew.log import logger

class UseCommand(Command):
    name = "use"
    usage = "%prog VERSION"
    summary = "Use the specified python in current shell"

    def run_command(self, options, args):
        if not args:
            self.parser.print_help()
            sys.exit(1)

        pkg = Package(args[0])
        pkgname = pkg.name
        pkgdir = os.path.join(PATH_PYTHONS, pkgname)
        if not os.path.isdir(pkgdir):
            logger.error("`%s` is not installed." % pkgname)
            sys.exit(1)
        pkgbin = os.path.join(pkgdir,'bin')
        pkglib = os.path.join(pkgdir,'lib')

        self._set_temp(pkgbin, pkglib)

        logger.info("Using `%s`" % pkgname)

    def _set_temp(self, bin_path, lib_path):
        fp = open(PATH_HOME_ETC_TEMP, 'w')
        fp.write('deactivate &> /dev/null\nPATH_PYTHONBREW_TEMP="%s"\nPATH_PYTHONBREW_TEMP_LIB="%s"\n' % (bin_path, lib_path))
        fp.close()

UseCommand()

########NEW FILE########
__FILENAME__ = venv
import os
import sys
from pythonbrew.basecommand import Command
from pythonbrew.define import PATH_PYTHONS, PATH_VENVS, PATH_HOME_ETC_VENV,\
    PATH_ETC, VIRTUALENV_DLSITE, PATH_DISTS, VIRTUALENV_CLONE_DLSITE
from pythonbrew.util import Package, \
    is_installed, get_installed_pythons_pkgname, get_using_python_pkgname,\
    untar_file, Subprocess, rm_r
from pythonbrew.log import logger
from pythonbrew.downloader import Downloader

class VenvCommand(Command):
    name = "venv"
    usage = "%prog [create|use|delete|list|clone|rename|print_activate] [project]"
    summary = "Create isolated python environments"

    def __init__(self):
        super(VenvCommand, self).__init__()
        self.parser.add_option(
            "-p", "--python",
            dest="python",
            default=None,
            help="Use the specified version of python.",
            metavar='VERSION'
        )
        self.parser.add_option(
            "-g", "--system-site-packages",
            dest="system_site_packages",
            action='store_true',
            default=False,
            help="Give access to the global site-packages dir to the virtual environment.",
        )
        self._venv_dir = os.path.join(PATH_ETC, 'virtualenv')
        self._venv = os.path.join(self._venv_dir, 'virtualenv.py')
        self._venv_clone_dir = os.path.join(PATH_ETC, 'virtualenv-clone')
        self._venv_clone = os.path.join(self._venv_clone_dir, 'clonevirtualenv.py')
        self._clear()

    def run_command(self, options, args):
        if not args:
            self.parser.print_help()
            sys.exit(1)
        cmd = args[0]
        if not cmd in ('init', 'create', 'delete', 'use', 'list', 'clone', 'rename', 'print_activate'):
            self.parser.print_help()
            sys.exit(1)

        # initialize?
        if cmd == 'init':
            self.run_command_init()
            return

        # target python interpreter
        if options.python:
            pkgname = Package(options.python).name
            if not is_installed(pkgname):
                logger.error('%s is not installed.' % pkgname)
                sys.exit(1)
        else:
            pkgname = get_using_python_pkgname()

        self._pkgname = pkgname
        if self._pkgname:
            self._target_py = os.path.join(PATH_PYTHONS, pkgname, 'bin', 'python')
            self._workon_home = os.path.join(PATH_VENVS, pkgname)
            self._py = os.path.join(PATH_PYTHONS, pkgname, 'bin', 'python')

        # is already installed virtualenv?
        if not os.path.exists(self._venv) or not os.path.exists(self._venv_clone):
            self.run_command_init()

        # Create a shell script
        self.__getattribute__('run_command_%s' % cmd)(options, args)

    def run_command_init(self):
        if os.path.exists(self._venv):
            logger.info('Remove virtualenv. (%s)' % self._venv_dir)
            rm_r(self._venv_dir)
        if os.path.exists(self._venv_clone):
            logger.info('Remove virtualenv-clone. (%s)' % self._venv_clone_dir)
            rm_r(self._venv_clone_dir)
        if not os.access(PATH_DISTS, os.W_OK):
            logger.error("Can not initialize venv command: Permission denied.")
            sys.exit(1)
        d = Downloader()
        download_file = os.path.join(PATH_DISTS, 'virtualenv.tar.gz')
        d.download('virtualenv.tar.gz', VIRTUALENV_DLSITE, download_file)
        logger.info('Extracting virtualenv into %s' % self._venv_dir)
        untar_file(download_file, self._venv_dir)
        download_file = os.path.join(PATH_DISTS, 'virtualenv-clone.tar.gz')
        d.download('virtualenv-clone.tar.gz', VIRTUALENV_CLONE_DLSITE, download_file)
        logger.info('Extracting virtualenv-clone into %s' % self._venv_clone_dir)
        untar_file(download_file, self._venv_clone_dir)

    def run_command_create(self, options, args):
        if not os.access(PATH_VENVS, os.W_OK):
            logger.error("Can not create a virtual environment in %s.\nPermission denied." % PATH_VENVS)
            sys.exit(1)
        if not self._pkgname:
            logger.error("Unknown python version: ( 'pythonbrew venv create <project> -p VERSION' )")
            sys.exit(1)

        virtualenv_options = []
        if options.system_site_packages:
            virtualenv_options.append('--system-site-packages')

        for arg in args[1:]:
            target_dir = os.path.join(self._workon_home, arg)
            logger.info("Creating `%s` environment into %s" % (arg, self._workon_home))
            # make command
            cmd = [self._py, self._venv, '-p', self._target_py]
            cmd.extend(virtualenv_options)
            cmd.append(target_dir)
            # create environment
            s = Subprocess(verbose=True)
            s.call(cmd)

    def run_command_delete(self, options, args):
        if not self._pkgname:
            logger.error("Unknown python version: ( 'pythonbrew venv delete <project> -p VERSION' )")
            sys.exit(1)

        for arg in args[1:]:
            target_dir = os.path.join(self._workon_home, arg)
            if not os.path.isdir(target_dir):
                logger.error('%s does not exist.' % target_dir)
            else:
                if not os.access(target_dir, os.W_OK):
                    logger.error("Can not delete %s.\nPermission denied." % target_dir)
                    continue
                logger.info('Deleting `%s` environment in %s' % (arg, self._workon_home))
                # make command
                rm_r(target_dir)

    def run_command_use(self, options, args):
        if len(args) < 2:
            logger.error("Unrecognized command line argument: ( 'pythonbrew venv use <project>' )")
            sys.exit(1)

        workon_home = None
        activate = None
        if self._pkgname:
            workon_home = self._workon_home
            activate = os.path.join(workon_home, args[1], 'bin', 'activate')
        else:
            for pkgname in get_installed_pythons_pkgname():
                workon_home = os.path.join(PATH_VENVS, pkgname)
                if os.path.isdir(workon_home):
                    if len([d for d in os.listdir(workon_home) if d == args[1]]) > 0:
                        activate = os.path.join(workon_home, args[1], 'bin', 'activate')
                        break
        if not activate or not os.path.exists(activate):
            logger.error('`%s` environment does not exist. Try `pythonbrew venv create %s`.' % (args[1], args[1]))
            sys.exit(1)

        self._write("""\
echo '# Using `%(arg)s` environment (found in %(workon_home)s)'
echo '# To leave an environment, simply run `deactivate`'
source '%(activate)s'
""" % {'arg': args[1], 'workon_home': workon_home, 'activate': activate})

    def run_command_list(self, options, args):
        if options.python:
            pkgname = Package(options.python).name
            workon_home = os.path.join(PATH_VENVS, pkgname)
            if pkgname == self._pkgname:
                logger.log("%s (*)" % pkgname)
            else:
                logger.log("%s" % pkgname)
            if os.path.isdir(workon_home):
                for d in sorted(os.listdir(workon_home)):
                    if os.path.isdir(os.path.join(workon_home, d)):
                        logger.log("  %s" % d)
        else:
            for pkgname in get_installed_pythons_pkgname():
                workon_home = os.path.join(PATH_VENVS, pkgname)
                if os.path.isdir(workon_home):
                    dirs = os.listdir(workon_home)
                    if len(dirs) > 0:
                        if pkgname == self._pkgname:
                            logger.log("%s (*)" % pkgname)
                        else:
                            logger.log("%s" % pkgname)
                        for d in sorted(dirs):
                            if os.path.isdir(os.path.join(workon_home, d)):
                                logger.log("  %s" % d)

    def run_command_clone(self, options, args):
        if len(args) < 3:
            logger.error("Unrecognized command line argument: ( 'pythonbrew venv clone <source> <target>' )")
            sys.exit(1)
        if not os.access(PATH_VENVS, os.W_OK):
            logger.error("Can not clone a virtual environment in %s.\nPermission denied." % PATH_VENVS)
            sys.exit(1)
        if not self._pkgname:
            logger.error("Unknown python version: ( 'pythonbrew venv clone <source> <target> -p VERSION' )")
            sys.exit(1)

        source, target = args[1], args[2]
        source_dir = os.path.join(self._workon_home, source)
        target_dir = os.path.join(self._workon_home, target)

        if not os.path.isdir(source_dir):
            logger.error('%s does not exist.' % source_dir)
            sys.exit(1)

        if os.path.isdir(target_dir):
            logger.error('Can not overwrite %s.' % target_dir)
            sys.exit(1)

        logger.info("Cloning `%s` environment into `%s` on %s" % (source, target, self._workon_home))

        # Copies source to target
        cmd = [self._py, self._venv_clone, source_dir, target_dir]
        s = Subprocess()
        s.call(cmd)

    def run_command_rename(self, options, args):
        if len(args) < 3:
            logger.error("Unrecognized command line argument: ( 'pythonbrew venv rename <source> <target>' )")
            sys.exit(1)
        if not os.access(PATH_VENVS, os.W_OK):
            logger.error("Can not rename a virtual environment in %s.\nPermission denied." % PATH_VENVS)
            sys.exit(1)
        if not self._pkgname:
            logger.error("Unknown python version: ( 'pythonbrew venv rename <source> <target> -p VERSION' )")
            sys.exit(1)

        logger.info("Rename `%s` environment to `%s` on %s" % (args[1], args[2], self._workon_home))

        source, target = args[1], args[2]
        self.run_command_clone(options, ['clone', source, target])
        self.run_command_delete(options, ['delete', source])

    def run_command_print_activate(self, options, args):
        if len(args) < 2:
            logger.error("Unrecognized command line argument: ( 'pythonbrew venv print_activate <project>' )")
            sys.exit(1)
        if not self._pkgname:
            logger.error("Unknown python version: ( 'pythonbrew venv print_activate <project> -p VERSION' )")
            sys.exit(1)

        activate = os.path.join(self._workon_home, args[1], 'bin', 'activate')
        if not os.path.exists(activate):
            logger.error('`%s` environment already does not exist. Try `pythonbrew venv create %s`.' % (args[1], args[1]))
            sys.exit(1)

        logger.log(activate)

    def _clear(self):
        self._write("")

    def _write(self, src):
        fp = open(PATH_HOME_ETC_VENV, 'w')
        fp.write(src)
        fp.close()

VenvCommand()

########NEW FILE########
__FILENAME__ = version
from pythonbrew.basecommand import Command
from pythonbrew.define import VERSION
from pythonbrew.log import logger

class VersionCommand(Command):
    name = "version"
    usage = "%prog"
    summary = "Show version"
    
    def run_command(self, options, args):
        logger.log(VERSION)

VersionCommand()

########NEW FILE########
__FILENAME__ = curl
import sys
import re
import subprocess
from subprocess import Popen, PIPE
from pythonbrew.log import logger
from pythonbrew.util import to_str
from pythonbrew.exceptions import CurlFetchException

class Curl(object):
    def __init__(self):
        returncode = subprocess.call("command -v curl > /dev/null", shell=True)
        if returncode:
            logger.log("pythonbrew required curl. curl was not found in your path.")
            sys.exit(1)
    
    def read(self, url):
        p = Popen('curl -skL "%s"' % url, stdout=PIPE, shell=True)
        p.wait()
        if p.returncode:
            raise Exception('Failed to read.')
        return p.stdout.read()
    
    def readheader(self, url):
        p = Popen('curl --head -skL "%s"' % url, stdout=PIPE, shell=True)
        p.wait()
        if p.returncode:
            raise Exception('Failed to readheader.')
        respinfo = {}
        for line in p.stdout:
            line = to_str(line.strip())
            if re.match('^HTTP.*? 200 OK$', line):
                break
        for line in p.stdout:
            line = to_str(line.strip()).split(":", 1)
            if len(line) == 2:
                respinfo[line[0].strip().lower()] = line[1].strip()
        return respinfo
    
    def fetch(self, url, filename):
        p = Popen('curl -# -kL "%s" -o "%s"' % (url, filename), shell=True)
        p.wait()
        if p.returncode:
            raise CurlFetchException('Failed to fetch.')

########NEW FILE########
__FILENAME__ = define
import os
import re
try:
    import ConfigParser
except:
    import configparser as ConfigParser

# pythonbrew version
VERSION = "1.3.4"

# pythonbrew installer root path
INSTALLER_ROOT = os.path.dirname(os.path.abspath(__file__))

# Root
# pythonbrew root path
ROOT = os.environ.get("PYTHONBREW_ROOT")
if not ROOT:
    ROOT = os.path.join(os.environ["HOME"],".pythonbrew")

# directories
PATH_PYTHONS = os.path.join(ROOT,"pythons")
PATH_BUILD = os.path.join(ROOT,"build")
PATH_DISTS = os.path.join(ROOT,"dists")
PATH_ETC = os.path.join(ROOT,"etc")
PATH_BIN = os.path.join(ROOT,"bin")
PATH_LOG = os.path.join(ROOT,"log")
PATH_VENVS = os.path.join(ROOT, "venvs")
PATH_SCRIPTS = os.path.join(ROOT,"scripts")
PATH_SCRIPTS_PYTHONBREW = os.path.join(PATH_SCRIPTS,"pythonbrew")
PATH_SCRIPTS_PYTHONBREW_COMMANDS = os.path.join(PATH_SCRIPTS_PYTHONBREW,"commands")
PATH_SCRIPTS_PYTHONBREW_INSTALLER = os.path.join(PATH_SCRIPTS_PYTHONBREW,"installer")
PATH_PATCHES = os.path.join(ROOT,"patches")
PATH_PATCHES_ALL = os.path.join(PATH_PATCHES,"all")
PATH_PATCHES_MACOSX = os.path.join(PATH_PATCHES,"macosx")
PATH_PATCHES_MACOSX_PYTHON27 = os.path.join(PATH_PATCHES_MACOSX,"python27")
PATH_PATCHES_MACOSX_PYTHON26 = os.path.join(PATH_PATCHES_MACOSX,"python26")
PATH_PATCHES_MACOSX_PYTHON25 = os.path.join(PATH_PATCHES_MACOSX,"python25")
PATH_PATCHES_MACOSX_PYTHON24 = os.path.join(PATH_PATCHES_MACOSX,"python24")

# files
PATH_BIN_PYTHONBREW = os.path.join(PATH_BIN,'pythonbrew')
PATH_ETC_CONFIG = os.path.join(PATH_ETC,'config.cfg')

# Home
# pythonbrew home path
PATH_HOME = os.environ.get('PYTHONBREW_HOME')
if not PATH_HOME:
    PATH_HOME = os.path.join(os.environ["HOME"],".pythonbrew")

# directories
PATH_HOME_ETC = os.path.join(PATH_HOME, 'etc')

# files
PATH_HOME_ETC_VENV = os.path.join(PATH_HOME_ETC, 'venv.run')
PATH_HOME_ETC_CURRENT = os.path.join(PATH_HOME_ETC,'current')
PATH_HOME_ETC_TEMP = os.path.join(PATH_HOME_ETC,'temp')

# read config.cfg
config = ConfigParser.SafeConfigParser()
config.read([PATH_ETC_CONFIG, os.path.join(INSTALLER_ROOT,'etc','config.cfg')])
def _get_or_default(section, option, default=''):
    try:
        return config.get(section, option)
    except:
        return default

# setuptools download
DISTRIBUTE_SETUP_DLSITE = _get_or_default('distribute', 'url')

# buildout bootstrap download
BOOTSTRAP_DLSITE = _get_or_default('bootstrap', 'url')

# virtualenv download
VIRTUALENV_DLSITE = _get_or_default('virtualenv', 'url')
VIRTUALENV_CLONE_DLSITE = _get_or_default('virtualenv-clone', 'url')

# pythonbrew download
PYTHONBREW_UPDATE_URL_MASTER = _get_or_default('pythonbrew', 'master')
PYTHONBREW_UPDATE_URL_DEVELOP = _get_or_default('pythonbrew', 'develop')
PYTHONBREW_UPDATE_URL_PYPI = _get_or_default('pythonbrew', 'pypi')
PYTHONBREW_UPDATE_URL_CONFIG = _get_or_default('pythonbrew', 'config')

# stable version text
PYTHONBREW_STABLE_VERSION_URL = _get_or_default('pythonbrew', 'stable-version')

# python download
LATEST_VERSIONS_OF_PYTHON = []
PYTHON_VERSION_URL = {}
PYTHON_VERSION_URL["1.5.2"] = _get_or_default('Python-1.5.2', 'url')
PYTHON_VERSION_URL["1.6.1"] = _get_or_default('Python-1.6.1', 'url')
for section in sorted(config.sections()):
    m = re.search("^Python-(.*)$", section)
    if m:
        version = m.group(1)
        PYTHON_VERSION_URL[version] = config.get(section, 'url')
        if config.has_option(section, 'latest') and config.getboolean(section, 'latest'):
            LATEST_VERSIONS_OF_PYTHON.append(version)

########NEW FILE########
__FILENAME__ = downloader
from pythonbrew.define import PYTHON_VERSION_URL, PYTHONBREW_STABLE_VERSION_URL, \
    PYTHONBREW_UPDATE_URL_PYPI, PYTHONBREW_UPDATE_URL_MASTER,\
    PYTHONBREW_UPDATE_URL_DEVELOP
from pythonbrew.log import logger
from pythonbrew.curl import Curl
from pythonbrew.util import to_str

def get_headerinfo_from_url(url):
    c = Curl()
    return c.readheader(url)

def get_stable_version():
    c = Curl()
    return to_str(c.read(PYTHONBREW_STABLE_VERSION_URL).strip())

class Downloader(object):
    def download(self, msg, url, path):
        logger.info("Downloading %s as %s" % (msg, path))
        c = Curl()
        c.fetch(url, path)

def get_pythonbrew_update_url(version):
    if version == "master":
        return PYTHONBREW_UPDATE_URL_MASTER
    elif version == 'develop':
        return PYTHONBREW_UPDATE_URL_DEVELOP
    else:
        return PYTHONBREW_UPDATE_URL_PYPI % (version)

def get_python_version_url(version):
    return PYTHON_VERSION_URL.get(version)

########NEW FILE########
__FILENAME__ = exceptions

class BuildingException(Exception):
    """General exception during building"""

class ShellCommandException(Exception):
    """General exception during shell command"""

class UnknownVersionException(Exception):
    """General exception during installing"""
class AlreadyInstalledException(Exception):
    """General exception during installing"""
class NotSupportedVersionException(Exception):
    """General exception during installing"""
    
class CurlFetchException(Exception):
    """Exception curl during fetching"""

########NEW FILE########
__FILENAME__ = pythonbrewinstaller
import os
import sys
import glob
import shutil
from pythonbrew.util import makedirs, rm_r
from pythonbrew.define import PATH_BUILD, PATH_BIN, PATH_DISTS, PATH_PYTHONS,\
    PATH_ETC, PATH_SCRIPTS, PATH_SCRIPTS_PYTHONBREW,\
    PATH_SCRIPTS_PYTHONBREW_COMMANDS, PATH_BIN_PYTHONBREW,\
    PATH_LOG, PATH_PATCHES, PATH_ETC_CONFIG,\
    PATH_SCRIPTS_PYTHONBREW_INSTALLER, PATH_VENVS, PATH_HOME_ETC, ROOT
import stat
import time

class PythonbrewInstaller(object):
    """pythonbrew installer:
    """
    
    @staticmethod
    def install(installer_root):
        # create directories
        makedirs(PATH_PYTHONS)
        makedirs(PATH_BUILD)
        makedirs(PATH_DISTS)
        makedirs(PATH_ETC)
        makedirs(PATH_BIN)
        makedirs(PATH_LOG)
        makedirs(PATH_VENVS)
        makedirs(PATH_HOME_ETC)
        
        # create script directories
        rm_r(PATH_SCRIPTS)
        makedirs(PATH_SCRIPTS)
        makedirs(PATH_SCRIPTS_PYTHONBREW)
        makedirs(PATH_SCRIPTS_PYTHONBREW_COMMANDS)
        makedirs(PATH_SCRIPTS_PYTHONBREW_INSTALLER)
        
        # copy all .py files
        for path in glob.glob(os.path.join(installer_root,"*.py")):
            shutil.copy(path, PATH_SCRIPTS_PYTHONBREW)
        for path in glob.glob(os.path.join(installer_root,"commands","*.py")):
            shutil.copy(path, PATH_SCRIPTS_PYTHONBREW_COMMANDS)
        for path in glob.glob(os.path.join(installer_root,"installer","*.py")):
            shutil.copy(path, PATH_SCRIPTS_PYTHONBREW_INSTALLER)
        
        # create patches direcotry
        rm_r(PATH_PATCHES)
        shutil.copytree(os.path.join(installer_root,"patches"), PATH_PATCHES)
        
        # create a main file
        fp = open("%s/pythonbrew_main.py" % PATH_SCRIPTS, "w")
        fp.write("""import pythonbrew
if __name__ == "__main__":
    pythonbrew.main()
""")
        fp.close()
        
        # create entry point file
        fp = open(PATH_BIN_PYTHONBREW, "w")
        fp.write("""#!/usr/bin/env bash
%s "%s/pythonbrew_main.py" "$@"
""" % (sys.executable, PATH_SCRIPTS))
        fp.close()
        # mode 0755
        os.chmod(PATH_BIN_PYTHONBREW, stat.S_IRUSR|stat.S_IWUSR|stat.S_IXUSR|stat.S_IRGRP|stat.S_IXGRP|stat.S_IROTH|stat.S_IXOTH)
        
        # create a bashrc for pythonbrew
        shutil.copy(os.path.join(installer_root,'etc','bashrc'), os.path.join(PATH_ETC,'bashrc'))
        
        # copy config.cfg
        shutil.copy(os.path.join(installer_root,'etc','config.cfg'), PATH_ETC_CONFIG)
    
    @staticmethod
    def systemwide_install():
        profile = """\
#begin-pythonbrew
if [ -n "${BASH_VERSION:-}" -o -n "${ZSH_VERSION:-}" ] ; then
    export PYTHONBREW_ROOT=%(root)s
    source "${PYTHONBREW_ROOT}/etc/bashrc"
fi
#end-pythonbrew
""" % {'root': ROOT}
        
        if os.path.isdir('/etc/profile.d'):
            fp = open('/etc/profile.d/pythonbrew.sh', 'w')
            fp.write(profile)
            fp.close()
        elif os.path.isfile('/etc/profile'):
            # create backup
            shutil.copy('/etc/profile', '/tmp/profile.pythonbrew.%s' % int(time.time()))
            
            output = []
            is_copy = True
            fp = open('/etc/profile', 'r')
            for line in fp:
                if line.startswith('#begin-pythonbrew'):
                    is_copy = False
                    continue
                elif line.startswith('#end-pythonbrew'):
                    is_copy = True
                    continue
                if is_copy:
                    output.append(line)
            fp.close()
            output.append(profile)
            
            fp = open('/etc/profile', 'w')
            fp.write(''.join(output))
            fp.close()
        

########NEW FILE########
__FILENAME__ = pythoninstaller
import os
import sys
import shutil
import mimetypes
import re
from pythonbrew.util import makedirs, symlink, Package, is_url, Link,\
    unlink, is_html, Subprocess, rm_r,\
    is_python25, is_python24, is_python26, is_python27,\
    extract_downloadfile, is_archive_file, path_to_fileurl, is_file,\
    fileurl_to_path, is_python30, is_python31, is_python32,\
    get_macosx_deployment_target, Version
from pythonbrew.define import PATH_BUILD, PATH_DISTS, PATH_PYTHONS,\
    ROOT, PATH_LOG, DISTRIBUTE_SETUP_DLSITE,\
    PATH_PATCHES_MACOSX_PYTHON25, PATH_PATCHES_MACOSX_PYTHON24,\
    PATH_PATCHES_MACOSX_PYTHON26, PATH_PATCHES_MACOSX_PYTHON27, PATH_PATCHES_ALL
from pythonbrew.downloader import get_python_version_url, Downloader,\
    get_headerinfo_from_url
from pythonbrew.log import logger
from pythonbrew.exceptions import UnknownVersionException,\
    NotSupportedVersionException

class PythonInstaller(object):
    """Python installer
    """

    def __init__(self, arg, options):
        if is_archive_file(arg):
            name = path_to_fileurl(arg)
        elif os.path.isdir(arg):
            name = path_to_fileurl(arg)
        else:
            name = arg

        if is_url(name):
            self.download_url = name
            filename = Link(self.download_url).filename
            pkg = Package(filename, options.alias)
        else:
            pkg = Package(name, options.alias)
            self.download_url = get_python_version_url(pkg.version)
            if not self.download_url:
                logger.error("Unknown python version: `%s`" % pkg.name)
                raise UnknownVersionException
            filename = Link(self.download_url).filename
        self.pkg = pkg
        self.install_dir = os.path.join(PATH_PYTHONS, pkg.name)
        self.build_dir = os.path.join(PATH_BUILD, pkg.name)
        self.download_file = os.path.join(PATH_DISTS, filename)

        self.options = options
        self.logfile = os.path.join(PATH_LOG, 'build.log')
        self.patches = []

        if Version(self.pkg.version) >= '3.1':
            self.configure_options = ['--with-computed-gotos']
        else:
            self.configure_options = []

    def install(self):
        # cleanup
        if os.path.isdir(self.build_dir):
            shutil.rmtree(self.build_dir)

        # get content type.
        if is_file(self.download_url):
            path = fileurl_to_path(self.download_url)
            self.content_type = mimetypes.guess_type(path)[0]
        else:
            headerinfo = get_headerinfo_from_url(self.download_url)
            self.content_type = headerinfo['content-type']
        if is_html(self.content_type):
            # note: maybe got 404 or 503 http status code.
            logger.error("Invalid content-type: `%s`" % self.content_type)
            return

        if os.path.isdir(self.install_dir):
            logger.info("You are already installed `%s`" % self.pkg.name)
            return

        self.download_and_extract()
        logger.info("\nThis could take a while. You can run the following command on another shell to track the status:")
        logger.info("  tail -f \"%s\"\n" % self.logfile)
        self.patch()
        logger.info("Installing %s into %s" % (self.pkg.name, self.install_dir))
        try:
            self.configure()
            self.make()
            self.make_install()
        except:
            rm_r(self.install_dir)
            logger.error("Failed to install %s. See %s to see why." % (self.pkg.name, self.logfile))
            sys.exit(1)
        self.symlink()
        self.install_setuptools()
        logger.info("\nInstalled %(pkgname)s successfully. Run the following command to switch to %(pkgname)s."
                    % {"pkgname":self.pkg.name})
        logger.info("  pythonbrew switch %s" % self.pkg.alias)

    def download_and_extract(self):
        if is_file(self.download_url):
            path = fileurl_to_path(self.download_url)
            if os.path.isdir(path):
                logger.info('Copying %s into %s' % (path, self.build_dir))
                shutil.copytree(path, self.build_dir)
                return
        if os.path.isfile(self.download_file):
            logger.info("Use the previously fetched %s" % (self.download_file))
        else:
            base_url = Link(self.download_url).base_url
            try:
                dl = Downloader()
                dl.download(base_url, self.download_url, self.download_file)
            except:
                unlink(self.download_file)
                logger.error("Failed to download.\n%s" % (sys.exc_info()[1]))
                sys.exit(1)
        # extracting
        if not extract_downloadfile(self.content_type, self.download_file, self.build_dir):
            sys.exit(1)

    def patch(self):
        version = Version(self.pkg.version)
        # for ubuntu 11.04(Natty)
        if is_python24(version):
            patch_dir = os.path.join(PATH_PATCHES_ALL, "python24")
            self._add_patches_to_list(patch_dir, ['patch-setup.py.diff'])
        elif is_python25(version):
            patch_dir = os.path.join(PATH_PATCHES_ALL, "python25")
            self._add_patches_to_list(patch_dir, ['patch-setup.py.diff'])
        elif is_python26(version):
            if version < '2.6.6':
                patch_dir = os.path.join(PATH_PATCHES_ALL, "python26")
                if version < '2.6.3':
                    self._add_patches_to_list(patch_dir, ['patch-Makefile.pre.in-for-2.6.2-and-earlier.diff'])
                self._add_patches_to_list(patch_dir, ['patch-setup.py-for-2.6.5-and-earlier.diff'])
                self._add_patches_to_list(patch_dir, ['patch-_ssl.c-for-ubuntu-oneiric-and-later.diff'])
            else:
                patch_dir = os.path.join(PATH_PATCHES_ALL, "common")
                self._add_patches_to_list(patch_dir, ['patch-setup.py.diff'])
        elif is_python27(version):
            if version < '2.7.2':
                patch_dir = os.path.join(PATH_PATCHES_ALL, "common")
                self._add_patches_to_list(patch_dir, ['patch-setup.py.diff'])
            if version == '2.7.3':
                patch_dir = os.path.join(PATH_PATCHES_ALL, "python27")
                self._add_patches_to_list(patch_dir, ['patch-Modules-_sqlite-connection.c.diff'])
            if version == '2.7.4':
                patch_dir = os.path.join(PATH_PATCHES_ALL, "python27")
                self._add_patches_to_list(patch_dir, ['patch-Modules-_sqlite-for-2.7.4.diff'])
        elif is_python30(version):
            patch_dir = os.path.join(PATH_PATCHES_ALL, "python30")
            self._add_patches_to_list(patch_dir, ['patch-setup.py.diff'])
        elif is_python31(version):
            if version < '3.1.4':
                patch_dir = os.path.join(PATH_PATCHES_ALL, "common")
                self._add_patches_to_list(patch_dir, ['patch-setup.py.diff'])
        elif is_python32(version):
            if version == '3.2':
                patch_dir = os.path.join(PATH_PATCHES_ALL, "python32")
                self._add_patches_to_list(patch_dir, ['patch-setup.py.diff'])
        self._do_patch()

    def _do_patch(self):
        try:
            s = Subprocess(log=self.logfile, cwd=self.build_dir, verbose=self.options.verbose)
            if self.patches:
                logger.info("Patching %s" % self.pkg.name)
                for patch in self.patches:
                    if type(patch) is dict:
                        for (ed, source) in patch.items():
                            s.shell('ed - "%s" < "%s"' % (source, ed))
                    else:
                        s.shell('patch -p0 < "%s"' % patch)
        except:
            logger.error("Failed to patch `%s`.\n%s" % (self.build_dir, sys.exc_info()[1]))
            sys.exit(1)

    def _add_patches_to_list(self, patch_dir, patch_files):
        for patch in patch_files:
            if type(patch) is dict:
                tmp = patch
                patch = {}
                for key in tmp.keys():
                    patch[os.path.join(patch_dir, key)] = tmp[key]
                self.patches.append(patch)
            else:
                self.patches.append(os.path.join(patch_dir, patch))

    def configure(self):
        s = Subprocess(log=self.logfile, cwd=self.build_dir, verbose=self.options.verbose)
        cmd = './configure --prefix="%s" %s %s' % (self.install_dir, self.options.configure, ' '.join(self.configure_options))
        if self.options.verbose:
            logger.log(cmd)
        s.check_call(cmd)

    def make(self):
        jobs = self.options.jobs
        make = ((jobs > 0 and 'make -j%s' % jobs) or 'make')
        s = Subprocess(log=self.logfile, cwd=self.build_dir, verbose=self.options.verbose)
        s.check_call(make)
        if self.options.test:
            if self.options.force:
                # note: ignore tests failure error.
                s.call("make test")
            else:
                s.check_call("make test")

    def make_install(self):
        version = Version(self.pkg.version)
        if version == "1.5.2" or version == "1.6.1":
            makedirs(self.install_dir)
        s = Subprocess(log=self.logfile, cwd=self.build_dir, verbose=self.options.verbose)
        s.check_call("make install")

    def symlink(self):
        install_dir = os.path.realpath(self.install_dir)
        if self.options.framework:
            # create symlink bin -> /path/to/Frameworks/Python.framework/Versions/?.?/bin
            bin_dir = os.path.join(install_dir, 'bin')
            if os.path.exists(bin_dir):
                rm_r(bin_dir)
            m = re.match(r'\d\.\d', self.pkg.version)
            if m:
                version = m.group(0)
            symlink(os.path.join(install_dir,'Frameworks','Python.framework','Versions',version,'bin'),
                    os.path.join(bin_dir))

        path_python = os.path.join(install_dir,'bin','python')
        if not os.path.isfile(path_python):
            src = None
            for d in os.listdir(os.path.join(install_dir,'bin')):
                if re.match(r'^python\d\.\d$', d):
                    src = d
                    break
            if src:
                path_src = os.path.join(install_dir,'bin',src)
                symlink(path_src, path_python)

    def install_setuptools(self):
        options = self.options
        pkgname = self.pkg.name
        if options.no_setuptools:
            logger.log("Skip installation of setuptools.")
            return
        download_url = DISTRIBUTE_SETUP_DLSITE
        filename = Link(download_url).filename
        download_file = os.path.join(PATH_DISTS, filename)

        dl = Downloader()
        dl.download(filename, download_url, download_file)

        install_dir = os.path.join(PATH_PYTHONS, pkgname)
        path_python = os.path.join(install_dir,"bin","python")
        try:
            s = Subprocess(log=self.logfile, cwd=PATH_DISTS, verbose=self.options.verbose)
            logger.info("Installing distribute into %s" % install_dir)
            s.check_call([path_python, filename])
            # installing pip
            easy_install = os.path.join(install_dir, 'bin', 'easy_install')
            if os.path.isfile(easy_install):
                logger.info("Installing pip into %s" % install_dir)
                s.check_call([easy_install, 'pip'])
        except:
            logger.error("Failed to install setuptools. See %s/log/build.log to see why." % (ROOT))
            logger.log("Skip installation of setuptools.")

class PythonInstallerMacOSX(PythonInstaller):
    """Python installer for MacOSX
    """
    def __init__(self, arg, options):
        super(PythonInstallerMacOSX, self).__init__(arg, options)

        # check for version
        version = Version(self.pkg.version)
        if version < '2.6' and (version != '2.4.6' and version < '2.5.5'):
            logger.error("`%s` is not supported on MacOSX Snow Leopard" % self.pkg.name)
            raise NotSupportedVersionException
        # set configure options
        target = get_macosx_deployment_target()
        if target:
            self.configure_options.append('MACOSX_DEPLOYMENT_TARGET=%s' % target)

        # set build options
        if options.framework and options.static:
            logger.error("Can't specify both framework and static.")
            raise Exception
        if options.framework:
            self.configure_options.append('--enable-framework=%s' % os.path.join(self.install_dir, 'Frameworks'))
        elif not options.static:
            self.configure_options.append('--enable-shared')
        if options.universal:
            self.configure_options.append('--enable-universalsdk=/')
            self.configure_options.append('--with-universal-archs=intel')

        # note: skip `make test` to avoid hanging test_threading.
        if is_python25(version) or is_python24(version):
            self.options.test = False

    def patch(self):
        # note: want an interface to the source patching functionality. like a patchperl.
        version = Version(self.pkg.version)
        if is_python24(version):
            patch_dir = PATH_PATCHES_MACOSX_PYTHON24
            self._add_patches_to_list(patch_dir, ['patch-configure', 'patch-Makefile.pre.in',
                                                  'patch-Lib-cgi.py.diff', 'patch-Lib-site.py.diff',
                                                  'patch-setup.py.diff', 'patch-Include-pyport.h',
                                                  'patch-Mac-OSX-Makefile.in', 'patch-Mac-OSX-IDLE-Makefile.in',
                                                  'patch-Mac-OSX-PythonLauncher-Makefile.in', 'patch-configure-badcflags.diff',
                                                  'patch-configure-arch_only.diff', 'patch-macosmodule.diff',
                                                  'patch-mactoolboxglue.diff', 'patch-pymactoolbox.diff',
                                                  'patch-gestaltmodule.c.diff'])
        elif is_python25(version):
            patch_dir = PATH_PATCHES_MACOSX_PYTHON25
            self._add_patches_to_list(patch_dir, ['patch-Makefile.pre.in.diff',
                                                  'patch-Lib-cgi.py.diff',
                                                  'patch-Lib-distutils-dist.py.diff',
                                                  'patch-setup.py.diff',
                                                  'patch-configure-badcflags.diff',
                                                  'patch-configure-arch_only.diff',
                                                  'patch-configure-no-posix-c-source.diff',
                                                  'patch-64bit.diff',
                                                  'patch-pyconfig.h.in.diff',
                                                  'patch-gestaltmodule.c.diff',
                                                  {'_localemodule.c.ed': 'Modules/_localemodule.c'},
                                                  {'locale.py.ed': 'Lib/locale.py'}])
        elif is_python26(version):
            patch_dir = PATH_PATCHES_MACOSX_PYTHON26
            self._add_patches_to_list(patch_dir, ['patch-Lib-cgi.py.diff',
                                                  'patch-Lib-distutils-dist.py.diff',
                                                  'patch-Mac-IDLE-Makefile.in.diff',
                                                  'patch-Mac-Makefile.in.diff',
                                                  'patch-Mac-PythonLauncher-Makefile.in.diff',
                                                  'patch-Mac-Tools-Doc-setup.py.diff',
                                                  'patch-setup.py-db46.diff',
                                                  'patch-Lib-ctypes-macholib-dyld.py.diff',
                                                  'patch-setup_no_tkinter.py.diff',
                                                  {'_localemodule.c.ed': 'Modules/_localemodule.c'},
                                                  {'locale.py.ed': 'Lib/locale.py'}])
        elif is_python27(version):
            patch_dir = PATH_PATCHES_MACOSX_PYTHON27
            self._add_patches_to_list(patch_dir, ['patch-Modules-posixmodule.diff'])

        self._do_patch()

########NEW FILE########
__FILENAME__ = log
import sys

class Color(object):
    DEBUG = '\033[35m'
    INFO = '\033[32m'
    ERROR = '\033[31m'
    ENDC = '\033[0m'
    
    @classmethod
    def _deco(cls, msg, color):
        return '%s%s%s' % (color, msg, cls.ENDC)
    
    @classmethod
    def debug(cls, msg):
        return cls._deco(msg, cls.DEBUG)
    @classmethod
    def info(cls, msg):
        return cls._deco(msg, cls.INFO)
    @classmethod
    def error(cls, msg):
        return cls._deco(msg, cls.ERROR)

class Logger(object):    
    def debug(self, msg):
        self._stdout(Color.debug("DEBUG: %s\n" % msg))
    
    def log(self, msg):
        self._stdout("%s\n" % (msg))
    
    def info(self, msg):
        self._stdout(Color.info('%s\n' % msg))
        
    def error(self, msg):
        self._stderr(Color.error("ERROR: %s\n" % msg))
        
    def _stdout(self, msg):
        sys.stdout.write(msg)
        sys.stdout.flush()
    def _stderr(self, msg):
        sys.stderr.write(msg)
        sys.stderr.flush()

logger = Logger()

########NEW FILE########
__FILENAME__ = util
import os
import sys
import errno
import shutil
import re
import posixpath
import tarfile
import platform
import urllib
import subprocess
import shlex
import select
from pythonbrew.define import PATH_BIN, PATH_HOME_ETC_CURRENT, PATH_PYTHONS, PATH_VENVS
from pythonbrew.exceptions import ShellCommandException
from pythonbrew.log import logger

def size_format(b):
    kb = 1000
    mb = kb*kb
    b = float(b)
    if b >= mb:
        return "%.1fMb" % (b/mb)
    if b >= kb:
        return "%.1fKb" % (b/kb)
    return "%.0fbytes" % (b)

def is_url(name):
    if ':' not in name:
        return False
    scheme = name.split(':', 1)[0].lower()
    return scheme in ['http', 'https', 'file', 'ftp']

def is_file(name):
    if ':' not in name:
        return False
    scheme = name.split(':', 1)[0].lower()
    return scheme == 'file'

def splitext(name):
    base, ext = os.path.splitext(name)
    if base.lower().endswith('.tar'):
        ext = base[-4:] + ext
        base = base[:-4]
    return base, ext

def is_archive_file(name):
    ext = splitext(name)[1].lower()
    archives = ('.zip', '.tar.gz', '.tar.bz2', '.tgz', '.tar')
    if ext in archives:
        return True
    return False

def is_html(content_type):
    if content_type and content_type.startswith('text/html'):
        return True
    return False

def is_gzip(content_type, filename):
    if(content_type == 'application/x-gzip'
       or splitext(filename)[1].lower() in ('.tar', '.tar.gz', '.tgz')):
        return True
    if os.path.exists(filename) and tarfile.is_tarfile(filename):
        return True
    return False

def is_macosx():
    mac_ver = platform.mac_ver()[0]
    return mac_ver >= '10.6'

def get_macosx_deployment_target():
    m = re.search('^([0-9]+\.[0-9]+)', platform.mac_ver()[0])
    if m:
        return m.group(1)
    return None

def _py_version_cmp(v, v1, v2):
    if is_str(v):
        v = Version(v)
    return v >= v1 and v < v2

def is_python24(version):
    return _py_version_cmp(version, '2.4', '2.5')

def is_python25(version):
    return _py_version_cmp(version, '2.5', '2.6')

def is_python26(version):
    return _py_version_cmp(version, '2.6', '2.7')

def is_python27(version):
    return _py_version_cmp(version, '2.7', '2.8')

def is_python30(version):
    return _py_version_cmp(version, '3.0', '3.1')

def is_python31(version):
    return _py_version_cmp(version, '3.1', '3.2')

def is_python32(version):
    return _py_version_cmp(version, '3.2', '3.3')

def makedirs(path):
    if not os.path.exists(path):
        os.makedirs(path)

def symlink(src, dst):
    try:
        os.symlink(src, dst)
    except:
        pass

def unlink(path):
    try:
        os.unlink(path)
    except OSError:
        e = sys.exc_info()[1]
        if errno.ENOENT != e.errno:
            raise

def rm_r(path):
    """like rm -r command."""
    if os.path.isdir(path):
        shutil.rmtree(path)
    elif os.path.isfile(path):
        unlink(path)

def off():
    set_current_path(PATH_BIN, '')

def split_leading_dir(path):
    path = str(path)
    path = path.lstrip('/').lstrip('\\')
    if '/' in path and (('\\' in path and path.find('/') < path.find('\\'))
                        or '\\' not in path):
        return path.split('/', 1)
    elif '\\' in path:
        return path.split('\\', 1)
    else:
        return path, ''

def has_leading_dir(paths):
    """Returns true if all the paths have the same leading path name
    (i.e., everything is in one subdirectory in an archive)"""
    common_prefix = None
    for path in paths:
        prefix, rest = split_leading_dir(path)
        if not prefix:
            return False
        elif common_prefix is None:
            common_prefix = prefix
        elif prefix != common_prefix:
            return False
    return True

def untar_file(filename, location):
    if not os.path.exists(location):
        os.makedirs(location)
    if filename.lower().endswith('.gz') or filename.lower().endswith('.tgz'):
        mode = 'r:gz'
    elif filename.lower().endswith('.bz2') or filename.lower().endswith('.tbz'):
        mode = 'r:bz2'
    elif filename.lower().endswith('.tar'):
        mode = 'r'
    else:
        logger.error('Cannot determine compression type for file %s' % filename)
        mode = 'r:*'
    tar = tarfile.open(filename, mode)
    try:
        # note: python<=2.5 doesnt seem to know about pax headers, filter them
        leading = has_leading_dir([
            member.name for member in tar.getmembers()
            if member.name != 'pax_global_header'
        ])
        for member in tar.getmembers():
            fn = member.name
            if fn == 'pax_global_header':
                continue
            if leading:
                fn = split_leading_dir(fn)[1]
            path = os.path.join(location, fn)
            if member.isdir():
                if not os.path.exists(path):
                    os.makedirs(path)
            else:
                try:
                    fp = tar.extractfile(member)
                except (KeyError, AttributeError):
                    e = sys.exc_info()[1]
                    # Some corrupt tar files seem to produce this
                    # (specifically bad symlinks)
                    logger.error('In the tar file %s the member %s is invalid: %s'
                                  % (filename, member.name, e))
                    continue
                if not os.path.exists(os.path.dirname(path)):
                    os.makedirs(os.path.dirname(path))
                destfp = open(path, 'wb')
                try:
                    shutil.copyfileobj(fp, destfp)
                finally:
                    destfp.close()
                fp.close()
                # note: configure ...etc
                os.chmod(path, member.mode)
                # note: the file timestamps should be such that asdl_c.py is not invoked.
                os.utime(path, (member.mtime, member.mtime))
    finally:
        tar.close()

def extract_downloadfile(content_type, download_file, target_dir):
    logger.info("Extracting %s into %s" % (os.path.basename(download_file), target_dir))
    if is_gzip(content_type, download_file):
        untar_file(download_file, target_dir)
    else:
        logger.error("Cannot determine archive format of %s" % download_file)
        return False
    return True

def get_command_path(command):
    p = subprocess.Popen('command -v %s' % command, stdout=subprocess.PIPE, shell=True)
    return to_str(p.communicate()[0].strip())

def get_using_python_path():
    return get_command_path('python')

def get_using_python_pkgname():
    """return: Python-<VERSION> or None"""
    path = get_using_python_path()

    # extract PYTHON NAME FROM PATH
    if path.startswith(PATH_PYTHONS):
        path = path.replace(PATH_PYTHONS,'').strip(os.sep)
        pkgname, rest = path.split(os.sep,1)
        return pkgname

    if path.startswith(PATH_VENVS):
        path = path.replace(PATH_VENVS,'').strip(os.sep)
        pkgname, rest = path.split(os.sep,1)
        return pkgname

    return None

def get_installed_pythons_pkgname():
    """Get the installed python versions list."""
    return [d for d in sorted(os.listdir(PATH_PYTHONS))]

def is_installed(name):
    pkgname = Package(name).name
    pkgdir = os.path.join(PATH_PYTHONS, pkgname)
    if not os.path.isdir(pkgdir):
        return False
    return True

def set_current_path(path_bin, path_lib):
    fp = open(PATH_HOME_ETC_CURRENT, 'w')
    fp.write('deactivate &> /dev/null\nPATH_PYTHONBREW_CURRENT="%s"\nPATH_PYTHONBREW_CURRENT_LIB="%s"\n' % (path_bin, path_lib))
    fp.close()

def path_to_fileurl(path):
    path = os.path.normcase(os.path.abspath(path))
    url = urllib.quote(path)
    url = url.replace(os.path.sep, '/')
    url = url.lstrip('/')
    return 'file:///' + url

def fileurl_to_path(url):
    assert url.startswith('file:'), ('Illegal scheme:%s' % url)
    url = '/' + url[len('file:'):].lstrip('/')
    return urllib.unquote(url)

def to_str(val):
    try:
        # python3
        if type(val) is bytes:
            return val.decode()
    except:
        if type(val) is unicode:
            return val.encode("utf-8")
    return val

def is_str(val):
    try:
        # python2
        return isinstance(val, basestring)
    except:
        # python3
        return isinstance(val, str)
    return False

def is_sequence(val):
    if is_str(val):
        return False
    return (hasattr(val, "__getitem__") or hasattr(val, "__iter__"))

def bltin_any(iter):
    try:
        return any(iter)
    except:
        # python2.4
        for it in iter:
            if it:
                return True
        return False

#-----------------------------
# class
#-----------------------------
class Subprocess(object):
    def __init__(self, log=None, cwd=None, verbose=False, debug=False):
        self._log = log
        self._cwd = cwd
        self._verbose = verbose
        self._debug = debug

    def chdir(self, cwd):
        self._cwd = cwd

    def shell(self, cmd):
        if self._debug:
            logger.log(cmd)
        if is_sequence(cmd):
            cmd = ' '.join(cmd)
        if self._log:
            if self._verbose:
                cmd = "(%s) 2>&1 | tee '%s'" % (cmd, self._log)
            else:
                cmd = "(%s) >> '%s' 2>&1" % (cmd, self._log)
        returncode = subprocess.call(cmd, shell=True, cwd=self._cwd)
        if returncode:
            raise ShellCommandException('%s: failed to `%s`' % (returncode, cmd))

    def call(self, cmd):
        if is_str(cmd):
            cmd = shlex.split(cmd)
        if self._debug:
            logger.log(cmd)

        fp = ((self._log and open(self._log, 'a')) or None)
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=self._cwd)
        while p.returncode is None:
            while bltin_any(select.select([p.stdout], [], [])):
                line = to_str(p.stdout.readline())
                if not line:
                    break
                if self._verbose:
                    logger.log(line.strip())
                if fp:
                    fp.write(line)
                    fp.flush()
            p.poll()
        if fp:
            fp.close()
        return p.returncode

    def check_call(self, cmd):
        returncode = self.call(cmd)
        if returncode:
            raise ShellCommandException('%s: failed to `%s`' % (returncode, cmd))

class Package(object):
    def __init__(self, name, alias=None):
        self.name = None
        self.version = None
        self.alias = None
        if is_archive_file(name):
            name = splitext(name)[0]
        m = re.search("^Python-(.*)$", name)
        if m:
            self.name = name
            self.version = self.alias = m.group(1)
        else:
            self.name = "Python-%s" % name
            self.version = self.alias = name
        if alias:
            self.name = 'Python-%s' % alias
            self.alias = alias

class Link(object):
    def __init__(self, url):
        self._url = url

    @property
    def filename(self):
        url = self._url
        url = url.split('#', 1)[0]
        url = url.split('?', 1)[0]
        url = url.rstrip('/')
        name = posixpath.basename(url)
        assert name, ('URL %r produced no filename' % url)
        return name

    @property
    def base_url(self):
        return posixpath.basename(self._url.split('#', 1)[0].split('?', 1)[0])

class Version(object):
    """version compare
    """
    def __init__(self, v):
        self._version = v
        self._p = self._parse_version(v)

    def __lt__(self, o):
        if is_str(o):
            o = self._parse_version(o)
        return self._p < o

    def __le__(self, o):
        if is_str(o):
            o = self._parse_version(o)
        return self._p <= o

    def __eq__(self, o):
        if is_str(o):
            o = self._parse_version(o)
        return self._p == o

    def __ne__(self, o):
        if is_str(o):
            o = self._parse_version(o)
        return self._p != o

    def __gt__(self, o):
        if is_str(o):
            o = self._parse_version(o)
        return self._p > o

    def __ge__(self, o):
        if is_str(o):
            o = self._parse_version(o)
        return self._p >= o

    def _parse_version(self, s):
        """see pkg_resouce.parse_version
        """
        component_re = re.compile(r'(\d+ | [a-z]+ | \.| -)', re.VERBOSE)
        replace = {'pre':'c', 'preview':'c','-':'final-','rc':'c','dev':'@'}.get

        def _parse_version_parts(s):
            for part in component_re.split(s):
                part = replace(part,part)
                if not part or part=='.':
                    continue
                if part[:1] in '0123456789':
                    yield part.zfill(8)    # pad for numeric comparison
                else:
                    yield '*'+part
            yield '*final'  # ensure that alpha/beta/candidate are before final

        parts = []
        for part in _parse_version_parts(s.lower()):
            if part.startswith('*'):
                if part<'*final':   # remove '-' before a prerelease tag
                    while parts and parts[-1]=='*final-': parts.pop()
                # remove trailing zeros from each series of numeric parts
                while parts and parts[-1]=='00000000':
                    parts.pop()
            parts.append(part)
        return tuple(parts)

    def __repr__(self):
        return self._version


########NEW FILE########
__FILENAME__ = pythonbrew_install
from pythonbrew.installer import install_pythonbrew, upgrade_pythonbrew, systemwide_pythonbrew
from optparse import OptionParser
if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option(
        '-U', '--upgrade',
        dest="upgrade",
        action="store_true",
        default=False,
        help="Upgrade."
    )
    parser.add_option(
        '--systemwide',
        dest="systemwide",
        action="store_true",
        default=False,
        help="systemwide install."
    )
    (opt, arg) = parser.parse_args()
    if opt.systemwide:
        systemwide_pythonbrew()
    elif opt.upgrade:
        upgrade_pythonbrew()
    else:
        install_pythonbrew()

########NEW FILE########
__FILENAME__ = test_suite
# coding=utf-8
#---------------------------------------------------------------------------
# Copyright 2011 utahta
#---------------------------------------------------------------------------
import os
import shutil

#---------------------------------------------------------------------------
# Settings
#---------------------------------------------------------------------------
PYTHONBREW_ROOT = '/tmp/pythonbrew.test'
TESTPY_VERSION = ['2.5.6', '2.6.6', '3.2']

def _cleanall():
    if os.path.isdir(PYTHONBREW_ROOT):
        shutil.rmtree(PYTHONBREW_ROOT)

def _install_pythonbrew():
    from pythonbrew.installer import install_pythonbrew
    install_pythonbrew()

def setup():
    os.environ['PYTHONBREW_ROOT'] = PYTHONBREW_ROOT
    _cleanall()
    _install_pythonbrew()

def teardown():
    _cleanall()

class Options(object):
    def __init__(self, opts):
        for (k,v) in opts.items():
            setattr(self, k, v)

#---------------------------------------------------------------------------
# Test
#---------------------------------------------------------------------------
def test_00_update():
    from pythonbrew.commands.update import UpdateCommand
    c = UpdateCommand()
    c.run_command(Options({'master':False, 'develop':False, 'config':False, 'force':False}), 
                  None)

def test_01_help():
    from pythonbrew.commands.help import HelpCommand
    c = HelpCommand()
    c.run_command(None, None)

def test_02_version():
    from pythonbrew.commands.version import VersionCommand
    c = VersionCommand()
    c.run_command(None, None)

def test_03_install():
    from pythonbrew.commands.install import InstallCommand
    py_version = TESTPY_VERSION.pop(0)
    o = Options({'force':True, 'test':False, 'verbose':False, 'configure':"",
                 'no_setuptools': False, 'alias':None, 'jobs':2, 
                 'framework':False, 'universal':False, 'static':False})
    c = InstallCommand()
    c.run_command(o, [py_version]) # pybrew install -f -j2 2.5.6
    c.run_command(o, TESTPY_VERSION) # pybrew install -f -j2 2.6.6 3.2

def test_04_switch():
    from pythonbrew.commands.switch import SwitchCommand
    for py_version in TESTPY_VERSION:
        c = SwitchCommand()
        c.run_command(None, [py_version])

def test_05_use():
    from pythonbrew.commands.use import UseCommand
    for py_version in TESTPY_VERSION:
        c = UseCommand()
        c.run_command(None, [py_version])

def test_06_off():
    from pythonbrew.commands.off import OffCommand
    c = OffCommand()
    c.run_command(None, None)

def test_07_list():
    from pythonbrew.commands.list import ListCommand
    c = ListCommand()
    c.run_command(Options({'all_versions':False, 'known':False}), 
                  None)

def test_08_py():
    from pythonbrew.commands.py import PyCommand
    TESTPY_FILE = os.path.join(PYTHONBREW_ROOT, 'etc', 'testfile.py')
    fp = open(TESTPY_FILE, 'w')
    fp.write("print('test')")
    fp.close()
    # Runs the python script
    c = PyCommand()
    c.run_command(Options({'pythons':[], 'verbose':False, 'bin':"python", 'options':""}), 
                  [TESTPY_FILE])

def test_09_buildout():
    from pythonbrew.commands.buildout import BuildoutCommand
    BUILDOUT_DIR = os.path.join(PYTHONBREW_ROOT, 'etc', 'buildout')
    BUILDOUT_CONF = os.path.join(BUILDOUT_DIR, 'buildout.cfg')
    if not os.path.isdir(BUILDOUT_DIR):
        os.makedirs(BUILDOUT_DIR)
    fp = open(BUILDOUT_CONF, 'w')
    fp.write("""[buildout]
parts = test
develop =

[test]
recipe = 
eggs =""")
    fp.close()
    # Runs the buildout
    os.chdir(BUILDOUT_DIR)
    c = BuildoutCommand()
    c.run_command(Options({'python':'2.6.6'}), [])

def test_10_venv():
    from pythonbrew.commands.venv import VenvCommand
    c = VenvCommand()
    o = Options({'python':'2.6.6', 'no_site_packages':False})
    c.run_command(o, ['init'])
    c.run_command(o, ['create', 'aaa'])
    c.run_command(o, ['list'])
    c.run_command(o, ['use', 'aaa'])
    c.run_command(o, ['delete', 'aaa'])

def test_11_uninstall():
    from pythonbrew.commands.uninstall import UninstallCommand
    for py_version in TESTPY_VERSION:
        c = UninstallCommand()
        c.run_command(None, [py_version])

def test_12_clean():
    from pythonbrew.commands.cleanup import CleanupCommand
    c = CleanupCommand()
    c.run_command(None, None)


########NEW FILE########
