__FILENAME__ = bowerrc
import sublime
import sublime_plugin
import json
import os


class BowerrcCommand(sublime_plugin.WindowCommand):
    def run(self):
        try:
            path = os.path.join(self.window.folders()[0], '.bowerrc')

            if not os.path.exists(path):
                rc = json.dumps({'directory': 'components'}, indent=2)

                f = open(path, 'w+')
                f.write(rc)

            self.window.open_file(path)
        except IndexError:
            sublime.error_message('Oh Dear! I need a directory for file .bowerrc.')
########NEW FILE########
__FILENAME__ = discover
import sublime_plugin


class DiscoverPackageCommand(sublime_plugin.WindowCommand):
    def run(self):
        self.window.run_command('open_url', {'url': 'http://sindresorhus.com/bower-components/'})
########NEW FILE########
__FILENAME__ = download_package
import sublime
import sublime_plugin

try:
    # ST3
    from ..utils.download import Download

except ImportError:
    # ST2
    from bower.utils.download import Download


class DownloadPackageCommand(sublime_plugin.TextCommand):
    result = None
    pkg_name = None

    def run(self, edit, pkg_name, cwd):
        self.edit = edit
        self.pkg_name = pkg_name
        self.cwd = cwd

        threads = []
        thread = Download(pkg_name, cwd)
        threads.append(thread)
        thread.start()
        self.handle_threads(edit, threads)

    def handle_threads(self, edit, threads, offset=0, i=0, dir=1):
        status = None
        next_threads = []
        for thread in threads:
            status = thread.result
            if thread.is_alive():
                next_threads.append(thread)
                continue
            if thread.result is False:
                continue

        threads = next_threads

        if len(threads):
            # This animates a little activity indicator in the status area
            before = i % 8
            after = (7) - before

            if not after:
                dir = -1
            if not before:
                dir = 1

            i += dir
            sublime.status_message(('Downloading %s [%s=%s]') % (self.pkg_name, ' ' * before, ' ' * after))

            sublime.set_timeout(lambda: self.handle_threads(edit, threads, offset, i, dir), 100)
            return

        if status:
            sublime.status_message(('Bower: installed %s') % self.pkg_name)

########NEW FILE########
__FILENAME__ = install
import sublime_plugin
try:
    # ST3
    from ..utils.api import API
except ImportError:
    # ST2
    from bower.utils.api import API


class InstallCommand(sublime_plugin.WindowCommand):
    def run(self, *args, **kwargs):
        self.list_packages()

    def list_packages(self):
        self.fileList = []
        packages = API().get('packages')
        packages.reverse()

        for package in packages:
            self.fileList.append([package['name'], package['url']])
        self.window.show_quick_panel(self.fileList, self.get_file)

    def get_file(self, index):
        if (index > -1):
            if not self.window.views():
                self.window.new_file()

            name = self.fileList[index][0]
            cwd = self.window.folders()[0]
            self.window.run_command("download_package", {"pkg_name": name, "cwd": cwd})

########NEW FILE########
__FILENAME__ = non_clean_exit_error
class NonCleanExitError(Exception):
    def __init__(self, returncode):
        self.returncode = returncode

    def __str__(self):
        return repr(self.returncode)

########NEW FILE########
__FILENAME__ = api
import json
import gzip
import sublime

try:
    # ST3
    import urllib.request as req
except ImportError:
    # ST2
    import urllib2 as req

try:
    # ST3
    from io import StringIO
except ImportError:
    # ST2
    from StringIO import StringIO


class API():
    def get(self, endpoint, *args):
        host = "http://bower.herokuapp.com/"
        request = req.Request(host + endpoint)

        try:
            response = req.urlopen(request)
        except urllib.error.HTTPError:
            sublime.error_message('Unable to connect to ' + host + endpoint + ". Check your internet connection.")

        responseText = response.read().decode('utf-8', 'replace')

        try:
            return json.loads(responseText)
        except:
            sublime.error_message('Oh Snap! It looks like theres an error with the Bower API.')
########NEW FILE########
__FILENAME__ = cli
import sublime
import os
import subprocess

try:
    # ST3
    from ..exceptions.non_clean_exit_error import NonCleanExitError
except ImportError:
    # ST2
    from bower.exceptions.non_clean_exit_error import NonCleanExitError

if os.name == 'nt':
    LOCAL_PATH = ';' + os.getenv('APPDATA') + '\\npm'
    BINARY_NAME = 'bower.cmd'
else:
    LOCAL_PATH = ':/usr/local/bin:/usr/local/sbin:/usr/local/share/npm/bin'
    BINARY_NAME = 'bower'

os.environ['PATH'] += LOCAL_PATH


class CLI():
    def find_binary(self):
        for dir in os.environ['PATH'].split(os.pathsep):
            path = os.path.join(dir, BINARY_NAME)
            if os.path.exists(path):
                return path
        sublime.error_message(BINARY_NAME + ' could not be found in your $PATH. Check the installation guidelines - https://github.com/benschwarz/sublime-bower#installation')

    def execute(self, command, cwd):
        binary = self.find_binary()
        command.insert(0, binary)

        cflags = 0

        if os.name == 'nt':
            cflags = 0x08000000  # Avoid opening of a cmd on Windows

        proc = subprocess.Popen(command, cwd=cwd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, creationflags=cflags)

        output = proc.stdout.read()
        returncode = proc.wait()
        if returncode != 0:
            error = NonCleanExitError(returncode)
            error.output = output
            raise error
        return output

########NEW FILE########
__FILENAME__ = download
from threading import Thread

try:
    # ST3
    from ..utils.cli import CLI
except ImportError:
    # ST2
    from bower.utils.cli import CLI


class Download(Thread):
    def __init__(self, pkg_name, cwd):
        self.pkg_name = pkg_name
        self.txt = None
        self.cwd = cwd

        # Defaults
        self.result = None
        Thread.__init__(self)

    def run(self):
        self.install_package()

    def install_package(self):
        command = ['install', self.pkg_name, '--save']
        CLI().execute(command, cwd=self.cwd)

########NEW FILE########
__FILENAME__ = Bower
import sublime
import sublime_plugin

#Internal
try:
    # ST3
    from .bower.commands.discover import DiscoverPackageCommand
    from .bower.commands.install import InstallCommand
    from .bower.commands.download_package import DownloadPackageCommand
    from .bower.commands.bowerrc import BowerrcCommand
except (ImportError, ValueError):
    # ST2
    from bower.commands.discover import DiscoverPackageCommand
    from bower.commands.install import InstallCommand
    from bower.commands.download_package import DownloadPackageCommand
    from bower.commands.bowerrc import BowerrcCommand

########NEW FILE########
