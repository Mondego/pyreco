__FILENAME__ = cleanup

import os

from pythonz.commands import Command
from pythonz.define import PATH_BUILD, PATH_DISTS
from pythonz.util import rm_r


class CleanupCommand(Command):
    name = "cleanup"
    usage = "%prog"
    summary = "Remove stale source folders and archives"

    def __init__(self):
        super(CleanupCommand, self).__init__()
        self.parser.add_option(
            '-a', '--all',
            dest='clean_all',
            action='store_true',
            default=False,
            help='Clean all, including the build directory. Note that debug symbols will be gone too!'
        )

    def run_command(self, options, args):
        if options.clean_all:
            self._cleanup(PATH_BUILD)
        self._cleanup(PATH_DISTS)

    def _cleanup(self, root):
        for dir in os.listdir(root):
            rm_r(os.path.join(root, dir))

CleanupCommand()


########NEW FILE########
__FILENAME__ = help

from pythonz.commands import Command, command_map
from pythonz.log import logger


class HelpCommand(Command):
    name = "help"
    usage = "%prog [COMMAND]"
    summary = "Show available commands"

    def run_command(self, options, args):
        if args:
            command = args[0]
            if command not in command_map:
                self.parser.error("Unknown command: `%s`" % command)
                return
            command = command_map[command]
            command.parser.print_help()
            return
        self.parser.print_help()
        logger.log("\nCommands available:")
        commands = [command_map[key] for key in sorted(command_map.keys())]
        for command in commands:
            logger.log("  %s: %s" % (command.name, command.summary))
        logger.log("\nFurther Instructions:")
        logger.log("  https://github.com/saghul/pythonz")

HelpCommand()


########NEW FILE########
__FILENAME__ = install

import sys

from pythonz.commands import Command
from pythonz.installer.pythoninstaller import PythonInstaller


class InstallCommand(Command):
    name = "install"
    usage = "%prog [OPTIONS] VERSION"
    summary = "Build and install the given version of python"
    
    def __init__(self):
        super(InstallCommand, self).__init__()
        self.parser.add_option(
            "-t", "--type",
            dest="type",
            default="cpython",
            help="Type of Python version: cpython, stackless, pypy or jython."
        )
        self.parser.add_option(
            "-f", "--force",
            dest="force",
            action="store_true",
            default=False,
            help="Force installation of python even if tests fail."
        )
        self.parser.add_option(
            "--run-tests",
            dest="run_tests",
            action="store_true",
            default=False,
            help="Run `make test` after compiling."
        )
        self.parser.add_option(
            "--url",
            dest="url",
            default=None,
            help="URL used to download the specified python version."
        )
        self.parser.add_option(
            "--file",
            dest="file",
            default=None,
            help="File pinting to the python version to be installed."
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
        for arg in args:
            try:
                p = PythonInstaller.get_installer(arg, options)
                p.install()
            except Exception:
                import traceback
                traceback.print_exc()
                continue

InstallCommand()


########NEW FILE########
__FILENAME__ = list

import os

from pythonz.commands import Command
from pythonz.define import PATH_PYTHONS
from pythonz.installer.pythoninstaller import CPythonInstaller, StacklessInstaller, PyPyInstaller, JythonInstaller
from pythonz.log import logger


class ListCommand(Command):
    name = "list"
    usage = "%prog [options]"
    summary = "List the installed python versions"

    def __init__(self):
        super(ListCommand, self).__init__()
        self.parser.add_option(
            '-a', '--all-versions',
            dest='all_versions',
            action='store_true',
            default=False,
            help='Show the all available python versions.'
        )
        self.parser.add_option(
            '-p', '--path',
            dest='path',
            action='store_true',
            default=False,
            help='Show the path for all Python installations.'
        )

    def run_command(self, options, args):
        if options.all_versions:
            self.all()
        else:
            self.installed(path=options.path)

    def installed(self, path):
        logger.log("# Installed Python versions")
        for d in sorted(os.listdir(PATH_PYTHONS)):
            if path:
                logger.log('  %-16s %s/%s' % (d, PATH_PYTHONS, d))
            else:
                logger.log('  %s' % d)

    def all(self):
        logger.log('# Available Python versions')
        for type, installer in zip(['cpython', 'stackless', 'pypy', 'jython'], [CPythonInstaller, StacklessInstaller, PyPyInstaller, JythonInstaller]):
            logger.log('  # %s:' % type)
            for version in installer.supported_versions:
                logger.log('     %s' % version)

ListCommand()


########NEW FILE########
__FILENAME__ = uninstall

import os

from pythonz.commands import Command
from pythonz.define import PATH_PYTHONS
from pythonz.util import rm_r, Package, is_installed
from pythonz.log import logger


class UninstallCommand(Command):
    name = "uninstall"
    usage = "%prog [options] VERSION"
    summary = "Uninstall the given version of python"

    def __init__(self):
        super(UninstallCommand, self).__init__()
        self.parser.add_option(
            "-t", "--type",
            dest="type",
            default="cpython",
            help="Type of Python version: cpython, stackless, pypy or jython."
        )

    def run_command(self, options, args):
        if args:
            # Uninstall pythons
            for arg in args:
                pkg = Package(arg, options.type)
                pkgname = pkg.name
                if not is_installed(pkg):
                    logger.error("`%s` is not installed." % pkgname)
                    continue
                rm_r(os.path.join(PATH_PYTHONS, pkgname))
        else:
            self.parser.print_help()

UninstallCommand()


########NEW FILE########
__FILENAME__ = update

import os
import sys

from pythonz.commands import Command
from pythonz.define import PATH_DISTS, ROOT, PATH_BUILD, PYTHONZ_UPDATE_URL, PYTHONZ_DEV_UPDATE_URL
from pythonz.downloader import Downloader, DownloadError
from pythonz.log import logger
from pythonz.util import rm_r, extract_downloadfile, Link, unlink, Subprocess


class UpdateCommand(Command):
    name = "update"
    usage = "%prog"
    summary = "Update pythonz to the latest version"

    def __init__(self):
        super(UpdateCommand, self).__init__()
        self.parser.add_option(
            "--dev",
            dest="dev",
            action="store_true",
            default=False,
            help="Use the development branch."
        )

    def run_command(self, options, args):
        if options.dev:
            download_url = PYTHONZ_DEV_UPDATE_URL
        else:
            download_url = PYTHONZ_UPDATE_URL
        headinfo = Downloader.read_head_info(download_url)
        content_type = headinfo['content-type']
        filename = "pythonz-latest"
        distname = "%s.tgz" % filename
        download_file = os.path.join(PATH_DISTS, distname)
        # Remove old tarball
        unlink(download_file)
        logger.info("Downloading %s as %s" % (distname, download_file))
        try:
            Downloader.fetch(download_url, download_file)
        except DownloadError:
            unlink(download_file)
            logger.error("Failed to download. `%s`" % download_url)
            sys.exit(1)
        except:
            unlink(download_file)
            raise

        extract_dir = os.path.join(PATH_BUILD, filename)
        rm_r(extract_dir)
        if not extract_downloadfile(content_type, download_file, extract_dir):
            sys.exit(1)

        try:
            logger.info("Installing %s into %s" % (extract_dir, ROOT))
            s = Subprocess()
            s.check_call([sys.executable, os.path.join(extract_dir,'pythonz_install.py'), '--upgrade'])
        except:
            logger.error("Failed to update pythonz.")
            sys.exit(1)
        logger.info("pythonz has been updated.")

UpdateCommand()


########NEW FILE########
__FILENAME__ = version

from pythonz.commands import Command
from pythonz.log import logger
from pythonz.version import __version__


class VersionCommand(Command):
    name = "version"
    usage = "%prog"
    summary = "Show version"

    def run_command(self, options, args):
        logger.log(__version__)

VersionCommand()


########NEW FILE########
__FILENAME__ = define

import os

# pythonz installer root path
INSTALLER_ROOT = os.path.dirname(os.path.abspath(__file__))

# Root
# pythonz root path
ROOT = os.environ.get('PYTHONZ_ROOT') or os.path.join(os.environ['HOME'], '.pythonz')

# directories
PATH_PYTHONS = os.path.join(ROOT, 'pythons')
PATH_BUILD = os.path.join(ROOT, 'build')
PATH_DISTS = os.path.join(ROOT, 'dists')
PATH_ETC = os.path.join(ROOT, 'etc')
PATH_BASH_COMPLETION = os.path.join(PATH_ETC, 'bash_completion.d')
PATH_BIN = os.path.join(ROOT, 'bin')
PATH_LOG = os.path.join(ROOT, 'log')
PATH_SCRIPTS = os.path.join(ROOT, 'scripts')
PATH_SCRIPTS_PYTHONZ = os.path.join(PATH_SCRIPTS, 'pythonz')
PATH_SCRIPTS_PYTHONZ_COMMANDS = os.path.join(PATH_SCRIPTS_PYTHONZ, 'commands')
PATH_SCRIPTS_PYTHONZ_INSTALLER = os.path.join(PATH_SCRIPTS_PYTHONZ, 'installer')
PATH_PATCHES = os.path.join(ROOT, 'patches')
PATH_PATCHES_ALL = os.path.join(PATH_PATCHES, 'all')
PATH_PATCHES_OSX = os.path.join(PATH_PATCHES, 'osx')

# files
PATH_BIN_PYTHONZ = os.path.join(PATH_BIN, 'pythonz')

# Home
# pythonz home path
PATH_HOME = os.environ.get('PYTHONZ_HOME') or os.path.join(os.environ['HOME'], '.pythonz')

# directories
PATH_HOME_ETC = os.path.join(PATH_HOME, 'etc')

# pythonz download
PYTHONZ_UPDATE_URL = 'https://github.com/saghul/pythonz/archive/master.tar.gz'
PYTHONZ_DEV_UPDATE_URL = 'https://github.com/saghul/pythonz/archive/dev.tar.gz'


########NEW FILE########
__FILENAME__ = downloader

import sys

from pythonz.util import PY3K

if PY3K:
    from urllib.request import Request, urlopen, urlretrieve
else:
    from urllib import urlretrieve
    from urllib2 import urlopen, Request


class ProgressBar(object):
    def __init__(self, out=sys.stdout):
        self._term_width = 79
        self._out = out

    def update_line(self, current):
        num_bar = int(current / 100.0 * (self._term_width - 5))
        bars = '#' * num_bar
        spaces = ' ' * (self._term_width - 5 - num_bar)
        percentage = '%3d' % int(current) + '%\r'
        result = bars + spaces + ' ' + percentage
        if not PY3K:
            # Python 2.x
            return result.decode("utf-8")
        return result

    def reporthook(self, blocknum, bs, size):
        current = (blocknum * bs * 100) / size
        if current > 100:
            current = 100
        self._out.write(self.update_line(current))
        self._out.flush()

    def finish(self):
        self._out.write(self.update_line(100))
        self._out.flush()


class HEADRequest(Request):
    def get_method(self):
        return "HEAD"


class DownloadError(Exception):
    """Exception during download"""


class Downloader(object):

    @classmethod
    def read(cls, url):
        try:
            r = urlopen(url)
        except IOError:
            raise DownloadError('Failed to fetch %s' % url)
        else:
            return r.read()

    @classmethod
    def read_head_info(cls, url):
        try:
            req = HEADRequest(url)
            res = urlopen(req)
        except IOError:
            raise DownloadError('Failed to fetch %s' % url)
        else:
            if res.code != 200:
                raise DownloadError('Failed to fetch %s' % url)
            return res.info()

    @classmethod
    def fetch(cls, url, filename):
        b = ProgressBar()
        try:
            urlretrieve(url, filename, b.reporthook)
            sys.stdout.write('\n')
        except IOError:
            sys.stdout.write('\n')
            raise DownloadError('Failed to fetch %s from %s' % (filename, url))

########NEW FILE########
__FILENAME__ = pythoninstaller

import ctypes
import os
import sys
import shutil
import mimetypes
import multiprocessing
import re
import subprocess

from pythonz.util import symlink, makedirs, Package, is_url, Link,\
    unlink, is_html, Subprocess, rm_r, is_python26, is_python27,\
    extract_downloadfile, is_archive_file, path_to_fileurl, is_file,\
    fileurl_to_path, is_python30, is_python31, is_python32,\
    get_macosx_deployment_target, Version, is_python25, is_python24, is_python33
from pythonz.define import PATH_BUILD, PATH_DISTS, PATH_PYTHONS, PATH_LOG, \
    PATH_PATCHES_ALL, PATH_PATCHES_OSX
from pythonz.downloader import Downloader, DownloadError
from pythonz.log import logger


class PythonInstaller(object):
    @staticmethod
    def get_installer(version, options):
        type = options.type.lower()
        if type == 'cpython':
            return CPythonInstaller(version, options)
        elif type == 'stackless':
            return StacklessInstaller(version, options)
        elif type == 'pypy':
            return PyPyInstaller(version, options)
        elif type == 'jython':
            return JythonInstaller(version, options)
        raise RuntimeError('invalid type specified: %s' % type)


class Installer(object):
    supported_versions = []

    def __init__(self, version, options):
        # create directories
        makedirs(PATH_BUILD)
        makedirs(PATH_DISTS)
        makedirs(PATH_LOG)

        if options.file is not None:
            if not (is_archive_file(options.file) and os.path.isfile(options.file)):
                logger.error('invalid file specified: %s' % options.file)
                raise RuntimeError
            self.download_url = path_to_fileurl(options.file)
        elif options.url is not None:
            if not is_url(options.url):
                logger.error('invalid URL specified: %s' % options.url)
                raise RuntimeError
            self.download_url = options.url
        else:
            if version not in self.supported_versions:
                logger.warning("Unsupported Python version: `%s`, trying with the following URL anyway: %s" % (version, self.get_version_url(version)))
            self.download_url = self.get_version_url(version)
        self.pkg = Package(version, options.type)
        self.install_dir = os.path.join(PATH_PYTHONS, self.pkg.name)
        self.build_dir = os.path.join(PATH_BUILD, self.pkg.name)
        filename = Link(self.download_url).filename
        self.download_file = os.path.join(PATH_DISTS, filename)

        self.options = options
        self.logfile = os.path.join(PATH_LOG, 'build.log')
        self.patches = []
        self.configure_options = []

    @classmethod
    def get_version_url(cls, version):
        raise NotImplementedError

    def download(self):
        if os.path.isfile(self.download_file):
            logger.info("Use the previously fetched %s" % (self.download_file))
        else:
            base_url = Link(self.download_url).base_url
            logger.info("Downloading %s as %s" % (base_url, self.download_file))
            try:
                Downloader.fetch(self.download_url, self.download_file)
            except DownloadError:
                unlink(self.download_file)
                logger.error("Failed to download.\n%s" % (sys.exc_info()[1]))
                sys.exit(1)
            except:
                unlink(self.download_file)
                raise

    def install(self):
        raise NotImplementedError


class CPythonInstaller(Installer):
    version_re = re.compile(r'(\d\.\d(\.\d)?)(.*)')
    supported_versions = ['2.4', '2.4.1', '2.4.2', '2.4.3', '2.4.4', '2.4.5', '2.4.6',
                          '2.5', '2.5.1', '2.5.2', '2.5.3', '2.5.4', '2.5.5', '2.5.6',
                          '2.6', '2.6.1', '2.6.2', '2.6.3', '2.6.4', '2.6.5', '2.6.6', '2.6.7', '2.6.8', '2.6.9',
                          '2.7', '2.7.1', '2.7.2', '2.7.3', '2.7.4', '2.7.5', '2.7.6',
                          '3.0', '3.0.1',
                          '3.1', '3.1.1', '3.1.2', '3.1.3', '3.1.4', '3.1.5',
                          '3.2', '3.2.1', '3.2.2', '3.2.3', '3.2.4', '3.2.5',
                          '3.3.0', '3.3.1', '3.3.2', '3.3.3', '3.3.4', '3.3.5',
                          '3.4.0', '3.4.1']

    def __init__(self, version, options):
        super(CPythonInstaller, self).__init__(version, options)

        if Version(self.pkg.version) >= '3.1':
            self.configure_options.append('--with-computed-gotos')

        if sys.platform == "darwin":
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

    @classmethod
    def get_version_url(cls, version):
        if version not in cls.supported_versions:
            # Unsupported alpha, beta or rc versions
            match = cls.version_re.match(version)
            if match is not None:
                groups = match.groups()
                base_version = groups[0]
                version = groups[0] + groups[2]
                return 'http://www.python.org/ftp/python/%(base_version)s/Python-%(version)s.tgz' % {'base_version': base_version, 'version': version}
        return 'http://www.python.org/ftp/python/%(version)s/Python-%(version)s.tgz' % {'version': version}

    def _apply_patches(self):
        try:
            s = Subprocess(log=self.logfile, cwd=self.build_dir, verbose=self.options.verbose)
            for patch in self.patches:
                if type(patch) is dict:
                    for ed, source in patch.items():
                        s.shell('ed - %s < %s' % (source, ed))
                else:
                    s.shell("patch -p0 < %s" % patch)
        except:
            logger.error("Failed to patch `%s`.\n%s" % (self.build_dir, sys.exc_info()[1]))
            sys.exit(1)

    def _append_patch(self, patch_dir, patch_files):
        for patch in patch_files:
            if type(patch) is dict:
                tmp = patch
                patch = {}
                for key in tmp.keys():
                    patch[os.path.join(patch_dir, key)] = tmp[key]
                self.patches.append(patch)
            else:
                self.patches.append(os.path.join(patch_dir, patch))

    def install(self):
        # cleanup
        if os.path.isdir(self.build_dir):
            shutil.rmtree(self.build_dir)

        # get content type.
        if is_file(self.download_url):
            path = fileurl_to_path(self.download_url)
            self.content_type = mimetypes.guess_type(path)[0]
        else:
            headerinfo = Downloader.read_head_info(self.download_url)
            self.content_type = headerinfo['content-type']
        if is_html(self.content_type):
            # note: maybe got 404 or 503 http status code.
            logger.error("Invalid content-type: `%s`" % self.content_type)
            return

        if os.path.isdir(self.install_dir):
            logger.info("You have already installed `%s`" % self.pkg.name)
            return

        self.download_and_extract()
        logger.info("\nThis could take a while. You can run the following command on another shell to track the status:")
        logger.info("  tail -f %s\n" % self.logfile)
        logger.info("Installing %s into %s" % (self.pkg.name, self.install_dir))
        try:
            self.patch()
            self.configure()
            self.make()
            self.make_install()
        except Exception:
            import traceback
            traceback.print_exc()
            rm_r(self.install_dir)
            logger.error("Failed to install %s. Check %s to see why." % (self.pkg.name, self.logfile))
            sys.exit(1)
        self.symlink()
        logger.info("\nInstalled %(pkgname)s successfully." % {"pkgname": self.pkg.name})

    def download_and_extract(self):
        self.download()
        if not extract_downloadfile(self.content_type, self.download_file, self.build_dir):
            sys.exit(1)

    def _patch(self):
        version = Version(self.pkg.version)
        common_patch_dir = os.path.join(PATH_PATCHES_ALL, "common")
        if is_python24(version):
            patch_dir = os.path.join(PATH_PATCHES_ALL, "python24")
            self._append_patch(patch_dir, ['patch-setup.py.diff'])
        elif is_python25(version):
            patch_dir = os.path.join(PATH_PATCHES_ALL, "python25")
            self._append_patch(patch_dir, ['patch-setup.py.diff', 'patch-svnversion.patch'])
        elif is_python26(version):
            self._append_patch(common_patch_dir, ['patch-setup.py.diff'])
            patch_dir = os.path.join(PATH_PATCHES_ALL, "python26")
            if version < '2.6.5':
                self._append_patch(patch_dir, ['patch-nosslv2-1.diff'])
            elif version < '2.6.6':
                self._append_patch(patch_dir, ['patch-nosslv2-2.diff'])
            elif version < '2.6.9':
                self._append_patch(patch_dir, ['patch-nosslv2-3.diff'])
        elif is_python27(version):
            if version < '2.7.2':
                self._append_patch(common_patch_dir, ['patch-setup.py.diff'])
        elif is_python30(version):
            patch_dir = os.path.join(PATH_PATCHES_ALL, "python30")
            self._append_patch(patch_dir, ['patch-setup.py.diff',
                                           'patch-nosslv2.diff'])
        elif is_python31(version):
            if version < '3.1.4':
                self._append_patch(common_patch_dir, ['patch-setup.py.diff'])
        elif is_python32(version):
            if version == '3.2':
                patch_dir = os.path.join(PATH_PATCHES_ALL, "python32")
                self._append_patch(patch_dir, ['patch-setup.py.diff'])

    def _patch_osx(self):
        version = Version(self.pkg.version)
        if is_python24(version):
            PATH_PATCHES_OSX_PYTHON24 = os.path.join(PATH_PATCHES_OSX, "python24")
            if version == '2.4':
                self._append_patch(PATH_PATCHES_OSX_PYTHON24, ['patch240-configure',
                                                               'patch240-setup.py.diff',
                                                               'patch240-Mac-OSX-Makefile.in',
                                                               'patch240-gestaltmodule.c.diff',
                                                               'patch240-sysconfig.py.diff'])
            elif version < '2.4.4':
                self._append_patch(PATH_PATCHES_OSX_PYTHON24, ['patch241-configure',
                                                               'patch240-setup.py.diff',
                                                               'patch240-Mac-OSX-Makefile.in',
                                                               'patch240-gestaltmodule.c.diff'])
            else:
                self._append_patch(PATH_PATCHES_OSX_PYTHON24, ['patch244-configure',
                                                               'patch244-setup.py.diff',
                                                               'patch244-Mac-OSX-Makefile.in',
                                                               'patch244-gestaltmodule.c.diff'])
            self._append_patch(PATH_PATCHES_OSX_PYTHON24, [
                                                  'patch-Makefile.pre.in',
                                                  'patch-Lib-cgi.py.diff',
                                                  'patch-Lib-site.py.diff',
                                                  'patch-Include-pyport.h',
                                                  'patch-configure-badcflags.diff',
                                                  'patch-macosmodule.diff',
                                                  'patch-mactoolboxglue.diff',
                                                  'patch-pymactoolbox.diff'])
        elif is_python25(version):
            PATH_PATCHES_OSX_PYTHON25 = os.path.join(PATH_PATCHES_OSX, "python25")
            if version == '2.5':
                self._append_patch(PATH_PATCHES_OSX_PYTHON25, ['patch250-setup.py.diff'])
            elif version == '2.5.1':
                self._append_patch(PATH_PATCHES_OSX_PYTHON25, ['patch251-setup.py.diff'])
            else:
                self._append_patch(PATH_PATCHES_OSX_PYTHON25, ['patch252-setup.py.diff'])
            self._append_patch(PATH_PATCHES_OSX_PYTHON25, [
                                                  'patch-Makefile.pre.in.diff',
                                                  'patch-Lib-cgi.py.diff',
                                                  'patch-Lib-distutils-dist.py.diff',
                                                  'patch-configure-badcflags.diff',
                                                  'patch-configure-arch_only.diff',
                                                  'patch-64bit.diff',
                                                  'patch-pyconfig.h.in.diff',
                                                  'patch-gestaltmodule.c.diff',
                                                  {'_localemodule.c.ed': 'Modules/_localemodule.c'},
                                                  {'locale.py.ed': 'Lib/locale.py'}])
        elif is_python26(version):
            PATH_PATCHES_OSX_PYTHON26 = os.path.join(PATH_PATCHES_OSX, "python26")
            self._append_patch(PATH_PATCHES_OSX_PYTHON26, [
                                                  'patch-Lib-cgi.py.diff',
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
            if version < '2.6.9':
                patch_dir = os.path.join(PATH_PATCHES_ALL, "python26")
                self._append_patch(patch_dir, ['patch-nosslv2-3.diff'])
        elif is_python27(version):
            PATH_PATCHES_OSX_PYTHON27 = os.path.join(PATH_PATCHES_OSX, "python27")
            if version < '2.7.4':
                self._append_patch(PATH_PATCHES_OSX_PYTHON27, ['patch-Modules-posixmodule.diff'])
            elif version == '2.7.6':
                self._append_patch(PATH_PATCHES_OSX_PYTHON27, ['python-276-dtrace.diff'])
        elif is_python33(version):
            PATH_PATCHES_OSX_PYTHON33 = os.path.join(PATH_PATCHES_OSX, "python33")
            if version == '3.3.4':
                self._append_patch(PATH_PATCHES_OSX_PYTHON33, ['python-334-dtrace.diff'])

    def patch(self):
        if sys.platform == "darwin":
            self._patch_osx()
        else:
            self._patch()
        self._apply_patches()

    def configure(self):
        s = Subprocess(log=self.logfile, cwd=self.build_dir, verbose=self.options.verbose)
        cmd = "./configure --prefix=%s %s %s" % (self.install_dir, self.options.configure, ' '.join(self.configure_options))
        if self.options.verbose:
            logger.log(cmd)
        s.check_call(cmd)

    def make(self):
        try:
            jobs = multiprocessing.cpu_count()
        except NotImplementedError:
            make = 'make'
        else:
            make = 'make -j%s' % jobs
        s = Subprocess(log=self.logfile, cwd=self.build_dir, verbose=self.options.verbose)
        s.check_call(make)
        if self.options.run_tests:
            if self.options.force:
                # note: ignore tests failure error.
                s.call("make test")
            else:
                s.check_call("make test")

    def make_install(self):
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
                symlink(os.path.join(install_dir, 'Frameworks', 'Python.framework', 'Versions', version, 'bin'), os.path.join(bin_dir))


class StacklessInstaller(CPythonInstaller):
    supported_versions = ['2.6.5',
                          '2.7.2',
                          '3.1.3',
                          '3.2.2', '3.2.5',
                          '3.3.5']

    @classmethod
    def get_version_url(cls, version):
        return 'http://www.stackless.com/binaries/stackless-%(version)s-export.tar.bz2' % {'version': version.replace('.', '')}


class PyPyInstaller(Installer):
    supported_versions = ['1.8',
                          '1.9',
                          '2.0', '2.0.1', '2.0.2',
                          '2.1',
                          '2.2', '2.2.1',
                          '2.3']

    @classmethod
    def get_version_url(cls, version):
        if sys.platform == 'darwin':
            return 'https://bitbucket.org/pypy/pypy/downloads/pypy-%(version)s-osx64.tar.bz2' % {'version': version}
        else:
            # Linux
            logger.warning("Linux binaries are dynamically linked, as is usual, and thus might not be usable due to the sad story of linux binary compatibility, check the PyPy website for more information")
            arch = {4: '', 8: '64'}[ctypes.sizeof(ctypes.c_size_t)]
            return 'https://bitbucket.org/pypy/pypy/downloads/pypy-%(version)s-linux%(arch)s.tar.bz2' % {'arch': arch, 'version': version}

    def install(self):
        # cleanup
        if os.path.isdir(self.build_dir):
            shutil.rmtree(self.build_dir)

        # get content type.
        if is_file(self.download_url):
            path = fileurl_to_path(self.download_url)
            self.content_type = mimetypes.guess_type(path)[0]
        else:
            headerinfo = Downloader.read_head_info(self.download_url)
            self.content_type = headerinfo['content-type']
        if is_html(self.content_type):
            # note: maybe got 404 or 503 http status code.
            logger.error("Invalid content-type: `%s`" % self.content_type)
            return

        if os.path.isdir(self.install_dir):
            logger.info("You have already installed `%s`" % self.pkg.name)
            return

        self.download_and_extract()
        logger.info("\nThis could take a while. You can run the following command on another shell to track the status:")
        logger.info("  tail -f %s\n" % self.logfile)
        logger.info("Installing %s into %s" % (self.pkg.name, self.install_dir))
        shutil.copytree(self.build_dir, self.install_dir)
        logger.info("\nInstalled %(pkgname)s successfully." % {"pkgname": self.pkg.name})

    def download_and_extract(self):
        self.download()
        if not extract_downloadfile(self.content_type, self.download_file, self.build_dir):
            sys.exit(1)


class JythonInstaller(Installer):
    supported_versions = ['2.5.0', '2.5.1', '2.5.2', '2.5.3']

    def __init__(self, version, options):
        super(JythonInstaller, self).__init__(version, options)
        filename = 'jython-installer-%s.jar' % version
        self.download_file = os.path.join(PATH_DISTS, filename)

    @classmethod
    def get_version_url(cls, version):
        if version in ('2.5.0', '2.5.1', '2.5.2'):
            return 'https://downloads.sourceforge.net/project/jython/jython/%(version)s/jython_installer-%(version)s.jar' % {'version': version}
        else:
            return 'http://search.maven.org/remotecontent?filepath=org/python/jython-installer/%(version)s/jython-installer-%(version)s.jar' % {'version': version}

    def install(self):
        # check if java is installed
        r = subprocess.call("command -v java > /dev/null", shell=True)
        if r != 0:
            logger.error("Jython requires Java to be installed, but the 'java' command was not found in the path.")
            return

        # cleanup
        if os.path.isdir(self.build_dir):
            shutil.rmtree(self.build_dir)

        # get content type.
        if is_file(self.download_url):
            path = fileurl_to_path(self.download_url)
            self.content_type = mimetypes.guess_type(path)[0]
        else:
            try:
                headerinfo = Downloader.read_head_info(self.download_url)
            except DownloadError:
                self.content_type = None
            else:
                self.content_type = headerinfo['content-type']
        if is_html(self.content_type):
            # note: maybe got 404 or 503 http status code.
            logger.error("Invalid content-type: `%s`" % self.content_type)
            return

        if os.path.isdir(self.install_dir):
            logger.info("You have already installed `%s`" % self.pkg.name)
            return

        self.download()
        logger.info("\nThis could take a while. You can run the following command on another shell to track the status:")
        logger.info("  tail -f %s\n" % self.logfile)
        logger.info("Installing %s into %s" % (self.pkg.name, self.install_dir))
        cmd = 'java -jar %s -s -d %s' % (self.download_file, self.install_dir)
        s = Subprocess(log=self.logfile, verbose=self.options.verbose)
        s.check_call(cmd)
        logger.info("\nInstalled %(pkgname)s successfully." % {"pkgname": self.pkg.name})


########NEW FILE########
__FILENAME__ = pythonzinstaller

import os
import sys
import glob
import shutil
import stat
import time

from pythonz.util import makedirs, rm_r
from pythonz.define import PATH_BUILD, PATH_BIN, PATH_DISTS, PATH_PYTHONS,\
    PATH_ETC, PATH_SCRIPTS, PATH_SCRIPTS_PYTHONZ,\
    PATH_SCRIPTS_PYTHONZ_COMMANDS, PATH_BIN_PYTHONZ,\
    PATH_LOG, PATH_PATCHES,\
    PATH_SCRIPTS_PYTHONZ_INSTALLER, PATH_HOME_ETC, ROOT,\
    PATH_BASH_COMPLETION


class PythonzInstaller(object):
    """pythonz installer:
    """

    @staticmethod
    def install(installer_root):
        # create directories
        makedirs(PATH_PYTHONS)
        makedirs(PATH_BUILD)
        makedirs(PATH_DISTS)
        makedirs(PATH_ETC)
        makedirs(PATH_BASH_COMPLETION)
        makedirs(PATH_BIN)
        makedirs(PATH_LOG)
        makedirs(PATH_HOME_ETC)

        # create script directories
        rm_r(PATH_SCRIPTS)
        makedirs(PATH_SCRIPTS)
        makedirs(PATH_SCRIPTS_PYTHONZ)
        makedirs(PATH_SCRIPTS_PYTHONZ_COMMANDS)
        makedirs(PATH_SCRIPTS_PYTHONZ_INSTALLER)

        # copy all .py files
        for path in glob.glob(os.path.join(installer_root,"*.py")):
            shutil.copy(path, PATH_SCRIPTS_PYTHONZ)
        for path in glob.glob(os.path.join(installer_root,"commands","*.py")):
            shutil.copy(path, PATH_SCRIPTS_PYTHONZ_COMMANDS)
        for path in glob.glob(os.path.join(installer_root,"installer","*.py")):
            shutil.copy(path, PATH_SCRIPTS_PYTHONZ_INSTALLER)

        # create patches direcotry
        rm_r(PATH_PATCHES)
        shutil.copytree(os.path.join(installer_root,"patches"), PATH_PATCHES)

        # create a main file
        with open("%s/pythonz_main.py" % PATH_SCRIPTS, "w") as f:
            f.write("""import pythonz
if __name__ == "__main__":
    pythonz.main()
""")

        # create entry point file
        with open(PATH_BIN_PYTHONZ, "w") as f:
            f.write("""#!/usr/bin/env bash
python %s/pythonz_main.py "$@"
""" % PATH_SCRIPTS)

        # mode 0755
        os.chmod(PATH_BIN_PYTHONZ, stat.S_IRUSR|stat.S_IWUSR|stat.S_IXUSR|stat.S_IRGRP|stat.S_IXGRP|stat.S_IROTH|stat.S_IXOTH)

        # create a bashrc for pythonz
        shutil.copy(os.path.join(installer_root,'etc','bashrc'), os.path.join(PATH_ETC,'bashrc'))

        # create a fish file for pythonz
        shutil.copy(os.path.join(installer_root, 'etc', 'pythonz.fish'), os.path.join(PATH_ETC, 'pythonz.fish'))

        #copy all *.sh files to bash_completion.d directory
        for path in glob.glob(os.path.join(installer_root,"etc","bash_completion.d","*.sh")):
            shutil.copy( path, PATH_BASH_COMPLETION )
    @staticmethod
    def systemwide_install():
        profile = """\
#begin-pythonz
if [ -n "${BASH_VERSION:-}" -o -n "${ZSH_VERSION:-}" ] ; then
    export PYTHONZ_ROOT=%(root)s
    source "${PYTHONZ_ROOT}/etc/bashrc"
fi
#end-pythonz
""" % {'root': ROOT}

        if os.path.isdir('/etc/profile.d'):
            with open('/etc/profile.d/pythonz.sh', 'w') as f:
                f.write(profile)
        elif os.path.isfile('/etc/profile'):
            # create backup
            shutil.copy('/etc/profile', '/tmp/profile.pythonz.%s' % int(time.time()))

            output = []
            is_copy = True
            with open('/etc/profile', 'r') as f:
                for line in f:
                    if line.startswith('#begin-pythonz'):
                        is_copy = False
                        continue
                    elif line.startswith('#end-pythonz'):
                        is_copy = True
                        continue
                    if is_copy:
                        output.append(line)
            output.append(profile)

            with open('/etc/profile', 'w') as f:
                f.write(''.join(output))


########NEW FILE########
__FILENAME__ = log

import sys

class Color(object):
    DEBUG = '\033[35m'
    INFO = '\033[32m'
    WARNING = '\033[31m'
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
    def warning(cls, msg):
        return cls._deco(msg, cls.WARNING)

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

    def warning(self, msg):
        self._stderr(Color.warning("WARNING: %s\n" % msg))

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
import subprocess
import shlex
import select

PY3K = sys.version_info >= (3,)
if not PY3K:
    from urllib import quote as urlquote, unquote as urlunquote
    from urllib2 import urlparse
else:
    from urllib.parse import urlparse, quote as urlquote, unquote as urlunquote

from pythonz.define import PATH_PYTHONS
from pythonz.log import logger


def is_url(name):
    try:
        result = urlparse.urlparse(name)
    except Exception:
        return False
    else:
        return result.scheme in ('http', 'https', 'file', 'ftp')

def is_file(name):
    try:
        result = urlparse.urlparse(name)
    except Exception:
        return False
    else:
        return result.scheme == 'file'

def splitext(name):
    base, ext = os.path.splitext(name)
    if base.lower().endswith('.tar'):
        ext = base[-4:] + ext
        base = base[:-4]
    return base, ext

def is_archive_file(name):
    ext = splitext(name)[1].lower()
    return ext in ('.zip', '.tar.gz', '.tar.bz2', '.tgz', '.tar')

def is_html(content_type):
    return content_type and content_type.startswith('text/html')

def is_gzip(content_type, filename):
    return (content_type == 'application/x-gzip' or tarfile.is_tarfile(filename) or splitext(filename)[1].lower() in ('.tar', '.tar.gz', '.tgz'))

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

def is_python33(version):
    return _py_version_cmp(version, '3.3', '3.4')

def makedirs(path):
    if not os.path.exists(path):
        os.makedirs(path)

def symlink(src, dst):
    try:
        os.symlink(src, dst)
    except OSError:
        pass

def unlink(path):
    try:
        os.unlink(path)
    except OSError as e:
        if e.errno != errno.ENOENT:
            raise

def rm_r(path):
    """like rm -r command."""
    if os.path.isdir(path):
        shutil.rmtree(path)
    elif os.path.isfile(path):
        unlink(path)

def split_leading_dir(path):
    path = str(path)
    path = path.lstrip('/').lstrip('\\')
    if '/' in path and (('\\' in path and path.find('/') < path.find('\\')) or '\\' not in path):
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

def is_installed(pkg):
    return os.path.isdir(os.path.join(PATH_PYTHONS, pkg.name))

def path_to_fileurl(path):
    path = os.path.normcase(os.path.abspath(path))
    url = urlquote(path)
    url = url.replace(os.path.sep, '/')
    url = url.lstrip('/')
    return 'file:///' + url

def fileurl_to_path(url):
    assert url.startswith('file:'), ('Illegal scheme:%s' % url)
    url = '/' + url[len('file:'):].lstrip('/')
    return urlunquote(url)

def to_str(val):
    if not PY3K:
        # python2
        if isinstance(val, unicode):
            return val.encode("utf-8")
        return val
    if isinstance(val, bytes):
        return val.decode("utf-8")
    return val

def is_str(val):
    if not PY3K:
        # python2
        return isinstance(val, basestring)
    # python3
    return isinstance(val, str)

def is_sequence(val):
    if is_str(val):
        return False
    return (hasattr(val, "__getitem__") or hasattr(val, "__iter__"))


#-----------------------------
# class
#-----------------------------
class ShellCommandException(Exception):
    """General exception during shell command"""

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
            cmd = ''.join(cmd)
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
            while any(select.select([p.stdout], [], [])):
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
    def __init__(self, version, type):
        type = type.lower()
        if type == 'cpython':
            tag = 'CPython'
        elif type == 'stackless':
            tag = 'Stackless'
        elif type == 'pypy':
            tag = 'PyPy'
        elif type == 'jython':
            tag = 'Jython'
        else:
            raise ValueError('invalid type: %s' % type)
        self.type = type
        self.tag = tag
        self.version = version

    @property
    def name(self):
        return '%s-%s' % (self.tag, self.version)

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
__FILENAME__ = version

__version__ = '1.3.0'


########NEW FILE########
__FILENAME__ = __main__
"""For development purposes, support invocation of pythonz with python -m."""

import pythonz
pythonz.main()

########NEW FILE########
__FILENAME__ = pythonz_install

from optparse import OptionParser
from pythonz.installer import install_pythonz, upgrade_pythonz, systemwide_pythonz

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
    opt, arg = parser.parse_args()
    if opt.systemwide:
        systemwide_pythonz()
    elif opt.upgrade:
        upgrade_pythonz()
    else:
        install_pythonz()


########NEW FILE########
__FILENAME__ = tasks

import invoke

# Based on https://github.com/pyca/cryptography/blob/master/tasks.py


@invoke.task
def release(version):
    invoke.run("git tag -a pythonz-{0} -m \"pythonz {0} release\"".format(version))
    invoke.run("git push --tags")


########NEW FILE########
__FILENAME__ = test_suite

import os
import shutil


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

PYTHONZ_ROOT = '/tmp/pythonz.test'
TESTPY_VERSION = (
    ('cpython', ['2.6.8', '2.7.3', '3.3.0']),
    ('stackless', ['2.7.2', '3.2.2']),
    ('pypy', ['1.9']),
    ('jython', ['2.5.3']),
)


def _cleanall():
    if os.path.isdir(PYTHONZ_ROOT):
        shutil.rmtree(PYTHONZ_ROOT)


def _install_pythonz():
    from pythonz.installer import install_pythonz
    install_pythonz()


def setup():
    os.environ['PYTHONZ_ROOT'] = PYTHONZ_ROOT
    _cleanall()
    _install_pythonz()


def teardown():
    _cleanall()


class Options(object):
    """A mock options object."""

    def __init__(self, opts):
        vars(self).update(opts)


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------

def test_01_update():
    from pythonz.commands.update import UpdateCommand
    c = UpdateCommand()
    c.run_command(None, None)


def test_02_help():
    from pythonz.commands.help import HelpCommand
    c = HelpCommand()
    c.run_command(None, None)


def test_03_install():
    from pythonz.commands.install import InstallCommand
    for t, versions in TESTPY_VERSION:
        o = Options({'type': t, 'force':True, 'run_tests':False, 'url': None,
                     'file': None, 'verbose':False, 'configure': "",
                     'framework':False, 'universal':False, 'static':False})
        c = InstallCommand()
        c.run_command(o, [versions.pop()]) # pythonz install 2.5.5
        if versions:
            c.run_command(o, versions) # pythonz install 2.6.6 2.7.3 3.2


def test_04_list():
    from pythonz.commands.list import ListCommand
    c = ListCommand()
    c.run_command(Options({'all_versions': False}), None)


def test_05_uninstall():
    from pythonz.commands.uninstall import UninstallCommand
    for py_type, py_versions in TESTPY_VERSION:
        c = UninstallCommand()
        for py_version in py_versions:
            c.run_command(Options({'type': py_type}), [py_version])


def test_06_cleanup():
    from pythonz.commands.cleanup import CleanupCommand
    c = CleanupCommand()
    c.run_command(Options({'clean_all': False}), None)
    c.run_command(Options({'clean_all': True}), None)


########NEW FILE########
