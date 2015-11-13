__FILENAME__ = build_dist
#!/usr/bin/env python

import os, sys, shutil, subprocess, argparse

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(THIS_DIR, "dist")
sys.path.append(os.path.join(THIS_DIR, "src", "Selenium2Library"))
sys.path.append(os.path.join(THIS_DIR, "doc"))
sys.path.append(os.path.join(THIS_DIR, "demo"))

def main():
    parser = argparse.ArgumentParser(description="Builds a Se2Lib distribution")
    parser.add_argument('py_26_path', action='store', help='Python 2.6 executbale file path')
    parser.add_argument('py_27_path', action='store', help='Python 2.7 executbale file path')
    parser.add_argument('--release', action='store_true')
    parser.add_argument('--winonly', action='store_true')
    args = parser.parse_args()
    
    if args.winonly:
        run_builds(args)
        return
    
    clear_dist_folder()
    run_register(args)
    run_builds(args)
    run_demo_packaging()
    run_doc_gen()

def clear_dist_folder():
    if os.path.exists(DIST_DIR):
        shutil.rmtree(DIST_DIR)
    os.mkdir(DIST_DIR)

def run_doc_gen():
    import generate
    print
    generate.main()

def run_register(args):
    if args.release:
        _run_setup(args.py_27_path, "register", [], False)

def run_builds(args):
    print
    if not args.winonly:
        _run_setup(args.py_27_path, "sdist", [ "--formats=gztar,zip" ], args.release)
        _run_setup(args.py_26_path, "bdist_egg", [], args.release)
        _run_setup(args.py_27_path, "bdist_egg", [], args.release)
    if os.name == 'nt':
        _run_setup(args.py_27_path, "bdist_wininst", [ "--plat-name=win32" ], args.release)
        _run_setup(args.py_27_path, "bdist_wininst", [ "--plat-name=win-amd64" ], args.release)
    else:
        print    
        print("Windows binary installers cannot be built on this platform!")    

def run_demo_packaging():
    import package
    print
    package.main()

def _run_setup(py_path, type, params, upload):
    setup_args = [py_path, os.path.join(THIS_DIR, "setup.py")]
    #setup_args.append("--quiet")
    setup_args.append(type)
    setup_args.extend(params)
    if upload:
        setup_args.append("upload")
        
    print
    print("Running: %s" % ' '.join(setup_args))
    returncode = subprocess.call(setup_args)
    if returncode != 0:
        print("Error running setup.py")
        sys.exit(1)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = server
#!/usr/bin/env python

#  Copyright 2008-2011 Nokia Siemens Networks Oyj
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

"""Simple HTTP server requiring only Python and no other preconditions.

Server is started by running this script with argument 'start' and
optional port number (default port 7272). Server root is the same
directory where this script is situated. Server can be stopped either
using Ctrl-C or running this script with argument 'stop' and same port
number as when starting it.
"""

import os
import sys
import httplib
import BaseHTTPServer
import SimpleHTTPServer


DEFAULT_PORT = 7272
DEFAULT_HOST = 'localhost'


class StoppableHttpServer(BaseHTTPServer.HTTPServer):

    def serve_forever(self):
        self.stop = False
        while not self.stop:
            try:
                self.handle_request()
            except KeyboardInterrupt:
                break


class StoppableHttpRequestHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):

    def do_QUIT(self):
        self.send_response(200)
        self.end_headers()
        self.server.stop = True

    def do_POST(self):
        # We could also process paremeters here using something like below.
        # length = self.headers['Content-Length']
        # print self.rfile.read(int(length))
        self.do_GET()


def start_server(host=DEFAULT_HOST, port=DEFAULT_PORT):
    print "Demo application starting on port %s" % port
    root  = os.path.dirname(os.path.abspath(__file__))
    os.chdir(root)
    server = StoppableHttpServer((host, int(port)), StoppableHttpRequestHandler)
    server.serve_forever()

def stop_server(host=DEFAULT_HOST, port=DEFAULT_PORT):
    print "Demo application on port %s stopping" % port
    conn = httplib.HTTPConnection("%s:%s" % (host, port))
    conn.request("QUIT", "/")
    conn.getresponse()

def print_help():
    print __doc__


if __name__ == '__main__':
    try:
        {'start': start_server,
         'stop': stop_server,
         'help': print_help}[sys.argv[1]](*sys.argv[2:])
    except (IndexError, KeyError, TypeError):
        print 'Usage: %s start|stop|help [port]' % os.path.basename(sys.argv[0])

########NEW FILE########
__FILENAME__ = package
#!/usr/bin/env python

import os, sys
from time import localtime
from zipfile import ZipFile, ZIP_DEFLATED

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
execfile(os.path.join(THIS_DIR, '..', 'src', 'Selenium2Library', 'version.py'))

FILES = {
    '': ['rundemo.py'],
    'login_tests': ['valid_login.txt', 'invalid_login.txt', 'resource.txt'],
    'demoapp': ['server.py'],
    'demoapp/html': ['index.html', 'welcome.html', 'error.html', 'demo.css']
}

def main():
    cwd = os.getcwd()
    try:
        os.chdir(THIS_DIR)
        name = 'robotframework-selenium2library-%s-demo' % VERSION
        zipname = '%s.zip' % name
        if os.path.exists(zipname):
            os.remove(zipname)
        zipfile = ZipFile(zipname, 'w', ZIP_DEFLATED)
        for dirname in FILES:
            for filename in FILES[dirname]:
                path = os.path.join('.', dirname.replace('/', os.sep), filename)
                print 'Adding:  ', os.path.normpath(path)
                zipfile.write(path, os.path.join(name, path))
        zipfile.close()
        target_path = os.path.join('..', 'dist', zipname)
        if os.path.exists(target_path):
            os.remove(target_path)
        os.rename(zipname, target_path)
        print 'Created: ', os.path.abspath(target_path)
    finally:
        os.chdir(cwd)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = rundemo
#! /usr/bin/env python

"""Runner Script for Robot Framework SeleniumLibrary Demo

Tests are run by giving a path to the tests to be executed as an argument to
this script. Possible Robot Framework options are given before the path.

Examples:
  rundemo.py login_tests                        # Run all tests in a directory
  rundemo.py login_tests/valid_login.text       # Run tests in a specific file
  rundemo.py --variable BROWSER:IE login_tests  # Override variable
  rundemo.py -v BROWSER:IE -v DELAY:0.25 login_tests

By default tests are executed with Firefox browser, but this can be changed
by overriding the `BROWSER` variable as illustrated above. Similarly it is
possible to slow down the test execution by overriding the `DELAY` variable
with a non-zero value.

When tests are run, the demo application is started and stopped automatically. 
It is also possible to start and stop the application separately
by using `demoapp` options. This allows running tests with the
normal `pybot` start-up script, as well as investigating the demo application.

Running the demo requires that Robot Framework, Selenium2Library, Python, and
Java to be installed.
"""

import os
import sys
from tempfile import TemporaryFile
from subprocess import Popen, call, STDOUT

try:
    import Selenium2Library
except ImportError, e:
    print 'Importing Selenium2Library module failed (%s).' % e
    print 'Please make sure you have Selenium2Library properly installed.'
    print 'See INSTALL.rst for troubleshooting information.'
    sys.exit(1)


ROOT = os.path.dirname(os.path.abspath(__file__))
DEMOAPP = os.path.join(ROOT, 'demoapp', 'server.py')


def run_tests(args):
    start_demo_application()
    call(['pybot'] + args, shell=(os.sep == '\\'))
    stop_demo_application()

def start_demo_application():
    Popen(['python', DEMOAPP, 'start'], stdout=TemporaryFile(), stderr=STDOUT)

def stop_demo_application():
    call(['python', DEMOAPP, 'stop'], stdout=TemporaryFile(), stderr=STDOUT)

def print_help():
    print __doc__

def print_usage():
    print 'Usage: rundemo.py [options] datasource'
    print '   or: rundemo.py demoapp start|stop'
    print '   or: rundemo.py help'


if __name__ == '__main__':
    action = {'demoapp-start': start_demo_application,
              'demoapp-stop': stop_demo_application,
              'help': print_help,
              '': print_usage}.get('-'.join(sys.argv[1:]))
    if action:
        action()
    else:
        run_tests(sys.argv[1:])

########NEW FILE########
__FILENAME__ = buildhtml
#!/usr/bin/env python

# $Id: buildhtml.py 7037 2011-05-19 08:56:27Z milde $
# Author: David Goodger <goodger@python.org>
# Copyright: This module has been placed in the public domain.

"""
Generates .html from all the .txt files in a directory.

Ordinary .txt files are understood to be standalone reStructuredText.
Files named ``pep-*.txt`` are interpreted as reStructuredText PEPs.
"""
# Once PySource is here, build .html from .py as well.

__docformat__ = 'reStructuredText'


try:
    import locale
    locale.setlocale(locale.LC_ALL, '')
except:
    pass

import sys
import os
import os.path
import copy
from fnmatch import fnmatch
import docutils
from docutils import ApplicationError
from docutils import core, frontend, utils
from docutils.error_reporting import ErrorOutput, ErrorString
from docutils.parsers import rst
from docutils.readers import standalone, pep
from docutils.writers import html4css1, pep_html


usage = '%prog [options] [<directory> ...]'
description = ('Generates .html from all the reStructuredText .txt files '
               '(including PEPs) in each <directory> '
               '(default is the current directory).')


class SettingsSpec(docutils.SettingsSpec):

    """
    Runtime settings & command-line options for the front end.
    """

    # Can't be included in OptionParser below because we don't want to
    # override the base class.
    settings_spec = (
        'Build-HTML Options',
        None,
        (('Recursively scan subdirectories for files to process.  This is '
          'the default.',
          ['--recurse'],
          {'action': 'store_true', 'default': 1,
           'validator': frontend.validate_boolean}),
         ('Do not scan subdirectories for files to process.',
          ['--local'], {'dest': 'recurse', 'action': 'store_false'}),
         ('BROKEN Do not process files in <directory>.  This option may be used '
          'more than once to specify multiple directories.',
          ['--prune'],
          {'metavar': '<directory>', 'action': 'append',
           'validator': frontend.validate_colon_separated_string_list}),
         ('BROKEN Recursively ignore files or directories matching any of the given '
          'wildcard (shell globbing) patterns (separated by colons).  '
          'Default: ".svn:CVS"',
          ['--ignore'],
          {'metavar': '<patterns>', 'action': 'append',
           'default': ['.svn', 'CVS'],
           'validator': frontend.validate_colon_separated_string_list}),
         ('Work silently (no progress messages).  Independent of "--quiet".',
          ['--silent'],
          {'action': 'store_true', 'validator': frontend.validate_boolean}),
         ('Do not process files, show files that would be processed.',
          ['--dry-run'],
          {'action': 'store_true', 'validator': frontend.validate_boolean}),))

    relative_path_settings = ('prune',)
    config_section = 'buildhtml application'
    config_section_dependencies = ('applications',)


class OptionParser(frontend.OptionParser):

    """
    Command-line option processing for the ``buildhtml.py`` front end.
    """

    def check_values(self, values, args):
        frontend.OptionParser.check_values(self, values, args)
        values._source = None
        return values

    def check_args(self, args):
        source = destination = None
        if args:
            self.values._directories = args
        else:
            self.values._directories = [os.getcwd()]
        return source, destination


class Struct:

    """Stores data attributes for dotted-attribute access."""

    def __init__(self, **keywordargs):
        self.__dict__.update(keywordargs)


class Builder:

    def __init__(self):
        self.publishers = {
            '': Struct(components=(pep.Reader, rst.Parser, pep_html.Writer,
                                   SettingsSpec)),
            '.txt': Struct(components=(rst.Parser, standalone.Reader,
                                       html4css1.Writer, SettingsSpec),
                           reader_name='standalone',
                           writer_name='html'),
            'PEPs': Struct(components=(rst.Parser, pep.Reader,
                                       pep_html.Writer, SettingsSpec),
                           reader_name='pep',
                           writer_name='pep_html')}
        """Publisher-specific settings.  Key '' is for the front-end script
        itself.  ``self.publishers[''].components`` must contain a superset of
        all components used by individual publishers."""

        self.setup_publishers()

    def setup_publishers(self):
        """
        Manage configurations for individual publishers.

        Each publisher (combination of parser, reader, and writer) may have
        its own configuration defaults, which must be kept separate from those
        of the other publishers.  Setting defaults are combined with the
        config file settings and command-line options by
        `self.get_settings()`.
        """
        for name, publisher in self.publishers.items():
            option_parser = OptionParser(
                components=publisher.components, read_config_files=1,
                usage=usage, description=description)
            publisher.option_parser = option_parser
            publisher.setting_defaults = option_parser.get_default_values()
            frontend.make_paths_absolute(publisher.setting_defaults.__dict__,
                                         option_parser.relative_path_settings)
            publisher.config_settings = (
                option_parser.get_standard_config_settings())
        self.settings_spec = self.publishers[''].option_parser.parse_args(
            values=frontend.Values())   # no defaults; just the cmdline opts
        self.initial_settings = self.get_settings('')

    def get_settings(self, publisher_name, directory=None):
        """
        Return a settings object, from multiple sources.

        Copy the setting defaults, overlay the startup config file settings,
        then the local config file settings, then the command-line options.
        Assumes the current directory has been set.
        """
        publisher = self.publishers[publisher_name]
        settings = frontend.Values(publisher.setting_defaults.__dict__)
        settings.update(publisher.config_settings, publisher.option_parser)
        if directory:
            local_config = publisher.option_parser.get_config_file_settings(
                os.path.join(directory, 'docutils.conf'))
            frontend.make_paths_absolute(
                local_config, publisher.option_parser.relative_path_settings,
                directory)
            settings.update(local_config, publisher.option_parser)
        settings.update(self.settings_spec.__dict__, publisher.option_parser)
        return settings

    def run(self, directory=None, recurse=1):
        recurse = recurse and self.initial_settings.recurse
        if directory:
            self.directories = [directory]
        elif self.settings_spec._directories:
            self.directories = self.settings_spec._directories
        else:
            self.directories = [os.getcwd()]
        for directory in self.directories:
            for root, dirs, files in os.walk(directory):
                # os.walk by default this recurses down the tree,
                # influence by modifying dirs.
                if not recurse:
                    del dirs[:]
                self.visit(root, files)

    def visit(self, directory, names):
        # BUG prune and ignore do not work 
        settings = self.get_settings('', directory)
        errout = ErrorOutput(encoding=settings.error_encoding)
        if settings.prune and (os.path.abspath(directory) in settings.prune):
            print >>errout, ('/// ...Skipping directory (pruned): %s' %
                              directory)
            sys.stderr.flush()
            names[:] = []
            return
        if not self.initial_settings.silent:
            print >>errout, '/// Processing directory: %s' % directory
            sys.stderr.flush()
        # settings.ignore grows many duplicate entries as we recurse
        # if we add patterns in config files or on the command line.
        for pattern in utils.uniq(settings.ignore):
            for i in range(len(names) - 1, -1, -1):
                if fnmatch(names[i], pattern):
                    # Modify in place!
                    del names[i]
        prune = 0
        for name in names:
            if name.endswith('.txt'):
                prune = self.process_txt(directory, name)
                if prune:
                    break

    def process_txt(self, directory, name):
        if name.startswith('pep-'):
            publisher = 'PEPs'
        else:
            publisher = '.txt'
        settings = self.get_settings(publisher, directory)
        errout = ErrorOutput(encoding=settings.error_encoding)
        pub_struct = self.publishers[publisher]
        if settings.prune and (directory in settings.prune):
            return 1
        settings._source = os.path.normpath(os.path.join(directory, name))
        settings._destination = settings._source[:-4]+'.html'
        if not self.initial_settings.silent:
            print >>errout, '    ::: Processing: %s' % name
            sys.stderr.flush()
        try:
            if not settings.dry_run:
                core.publish_file(source_path=settings._source,
                              destination_path=settings._destination,
                              reader_name=pub_struct.reader_name,
                              parser_name='restructuredtext',
                              writer_name=pub_struct.writer_name,
                              settings=settings)
        except ApplicationError, error:
            print >>errout, '        %s' % ErrorString(error)


if __name__ == "__main__":
    Builder().run()

########NEW FILE########
__FILENAME__ = generate
#!/usr/bin/env python
from os.path import join, dirname
try:
    from robot.libdoc import libdoc
except:
    def main():
        print """Robot Framework 2.7 or later required for generating documentation"""
else:
    def main():
        libdoc(join(dirname(__file__),'..','src','Selenium2Library'), join(dirname(__file__),'Selenium2Library.html'))


if __name__ == '__main__':
    main()
########NEW FILE########
__FILENAME__ = generate_readmes
#!/usr/bin/env python

import os, shutil
from buildhtml import Builder

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.join(THIS_DIR, "..")
SRC_DIR = os.path.join(ROOT_DIR, "src")
LIB_DIR = os.path.join(SRC_DIR, "Selenium2Library")

README_FILES = [
    "README.rst",
    "INSTALL.rst",
    "BUILD.rst",
    "CHANGES.rst"
]

def main():
    try:
        import docutils
    except:
        print "Readme files will not be built into HTML, docutils not installed"
        return
    for readme_relative_path in README_FILES:
        (readme_dir, readme_name) = _parse_readme_path(readme_relative_path)
        readme_txt_name = _make_txt_file(readme_dir, readme_name)
        Builder().process_txt(readme_dir, readme_txt_name)
        _cleanup_txt_file(readme_dir, readme_txt_name)

        readme_html_name = os.path.splitext(readme_name)[0] + '.html'
        readme_html_path = os.path.join(readme_dir, readme_html_name)
        target_readme_html_name =  os.path.splitext(readme_relative_path.replace('/', '-'))[0] + '.html'
        target_readme_html_path = os.path.join(THIS_DIR, target_readme_html_name)

        if os.path.exists(target_readme_html_path):
            os.remove(target_readme_html_path)
        os.rename(readme_html_path, target_readme_html_path)

        print "    ::: Saved: %s" % target_readme_html_name

def _parse_readme_path(readme_relative_path):
    readme_abs_path = os.path.join(ROOT_DIR, readme_relative_path.replace('/', os.sep))
    readme_path_parts = os.path.split(readme_abs_path)
    readme_dir = readme_path_parts[0]
    readme_name = readme_path_parts[1]
    return (readme_dir, readme_name)

def _make_txt_file(readme_dir, readme_name):
    readme_txt_name  = os.path.splitext(readme_name)[0] + '.txt'
    _cleanup_txt_file(readme_dir, readme_txt_name)
    shutil.copyfile(
        os.path.join(readme_dir, readme_name), 
        os.path.join(readme_dir, readme_txt_name))
    return readme_txt_name

def _cleanup_txt_file(readme_dir, readme_txt_name):
    readme_txt_abs_path = os.path.join(readme_dir, readme_txt_name)
    if os.path.exists(readme_txt_abs_path):
        os.remove(readme_txt_abs_path)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = keywordgroup
import sys
import inspect
try:
    from decorator import decorator
except SyntaxError: # decorator module requires Python/Jython 2.4+
    decorator = None
if sys.platform == 'cli':
    decorator = None # decorator module doesn't work with IronPython 2.6

def _run_on_failure_decorator(method, *args, **kwargs):
    try:
        return method(*args, **kwargs)
    except Exception, err:
        self = args[0]
        if hasattr(self, '_run_on_failure'):
            self._run_on_failure()
        raise

class KeywordGroupMetaClass(type):
    def __new__(cls, clsname, bases, dict):
        if decorator:
            for name, method in dict.items():
                if not name.startswith('_') and inspect.isroutine(method):
                    dict[name] = decorator(_run_on_failure_decorator, method)
        return type.__new__(cls, clsname, bases, dict)

class KeywordGroup(object):
    __metaclass__ = KeywordGroupMetaClass

########NEW FILE########
__FILENAME__ = _browsermanagement
import os
import robot
from robot.errors import DataError
from selenium import webdriver
from Selenium2Library import webdrivermonkeypatches
from Selenium2Library.utils import BrowserCache
from Selenium2Library.locators import WindowManager
from keywordgroup import KeywordGroup

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FIREFOX_PROFILE_DIR = os.path.join(ROOT_DIR, 'resources', 'firefoxprofile')
BROWSER_NAMES = {'ff': "_make_ff",
                 'firefox': "_make_ff",
                 'ie': "_make_ie",
                 'internetexplorer': "_make_ie",
                 'googlechrome': "_make_chrome",
                 'gc': "_make_chrome",
                 'chrome': "_make_chrome",
                 'opera' : "_make_opera",
                 'phantomjs' : "_make_phantomjs",
                 'htmlunit' : "_make_htmlunit",
                 'htmlunitwithjs' : "_make_htmlunitwithjs",
                 'android': "_make_android",
                 'iphone': "_make_iphone",
                 'safari': "_make_safari"
                }

class _BrowserManagementKeywords(KeywordGroup):

    def __init__(self):
        self._cache = BrowserCache()
        self._window_manager = WindowManager()
        self._speed_in_secs = float(0)
        self._timeout_in_secs = float(5)
        self._implicit_wait_in_secs = float(0)

    # Public, open and close

    def close_all_browsers(self):
        """Closes all open browsers and resets the browser cache.

        After this keyword new indexes returned from `Open Browser` keyword
        are reset to 1.

        This keyword should be used in test or suite teardown to make sure
        all browsers are closed.
        """
        self._debug('Closing all browsers')
        self._cache.close_all()

    def close_browser(self):
        """Closes the current browser."""
        if self._cache.current:
            self._debug('Closing browser with session id %s'
                        % self._cache.current.session_id)
            self._cache.close()

    def open_browser(self, url, browser='firefox', alias=None,remote_url=False,
                desired_capabilities=None,ff_profile_dir=None):
        """Opens a new browser instance to given URL.

        Returns the index of this browser instance which can be used later to
        switch back to it. Index starts from 1 and is reset back to it when
        `Close All Browsers` keyword is used. See `Switch Browser` for
        example.

        Optional alias is an alias for the browser instance and it can be used
        for switching between browsers (just as index can be used). See `Switch
        Browser` for more details.

        Possible values for `browser` are as follows:

        | firefox          | FireFox   |
        | ff               | FireFox   |
        | internetexplorer | Internet Explorer |
        | ie               | Internet Explorer |
        | googlechrome     | Google Chrome |
        | gc               | Google Chrome |
        | chrome           | Google Chrome |
        | opera            | Opera         |
        | phantomjs        | PhantomJS     |
        | htmlunit         | HTMLUnit      |
        | htmlunitwithjs   | HTMLUnit with Javascipt support |
        | android          | Android       |
        | iphone           | Iphone        |
        | safari           | Safari        |


        Note, that you will encounter strange behavior, if you open
        multiple Internet Explorer browser instances. That is also why
        `Switch Browser` only works with one IE browser at most.
        For more information see:
        http://selenium-grid.seleniumhq.org/faq.html#i_get_some_strange_errors_when_i_run_multiple_internet_explorer_instances_on_the_same_machine

        Optional 'remote_url' is the url for a remote selenium server for example
        http://127.0.0.1/wd/hub.  If you specify a value for remote you can
        also specify 'desired_capabilities' which is a string in the form
        key1:val1,key2:val2 that will be used to specify desired_capabilities
        to the remote server. This is useful for doing things like specify a
        proxy server for internet explorer or for specify browser and os if your
        using saucelabs.com. 'desired_capabilities' can also be a dictonary
        (created with 'Create Dictionary') to allow for more complex configurations.

        Optional 'ff_profile_dir' is the path to the firefox profile dir if you
        wish to overwrite the default.
        """
        if remote_url:
            self._info("Opening browser '%s' to base url '%s' through remote server at '%s'"
                    % (browser, url, remote_url))
        else:
            self._info("Opening browser '%s' to base url '%s'" % (browser, url))
        browser_name = browser
        browser = self._make_browser(browser_name,desired_capabilities,ff_profile_dir,remote_url)
        try:
            browser.get(url)
        except:  
            self._cache.register(browser, alias)
            self._debug("Opened browser with session id %s but failed to open url '%s'"
                        % (browser.session_id, url))
            raise
        self._debug('Opened browser with session id %s'
                    % browser.session_id)
        return self._cache.register(browser, alias)

    def create_webdriver(self, driver_name, alias=None, kwargs={}, **init_kwargs):
        """Creates an instance of a WebDriver.

        Like `Open Browser`, but allows passing arguments to a WebDriver's
        __init__. _Open Browser_ is preferred over _Create Webdriver_ when
        feasible.

        Returns the index of this browser instance which can be used later to
        switch back to it. Index starts from 1 and is reset back to it when
        `Close All Browsers` keyword is used. See `Switch Browser` for
        example.

        `driver_name` must be the exact name of a WebDriver in
        _selenium.webdriver_ to use. WebDriver names include: Firefox, Chrome,
        Ie, Opera, Safari, PhantomJS, and Remote.

        Use keyword arguments to specify the arguments you want to pass to
        the WebDriver's __init__. The values of the arguments are not
        processed in any way before being passed on. For Robot Framework
        < 2.8, which does not support keyword arguments, create a keyword
        dictionary and pass it in as argument `kwargs`. See the
        [http://selenium.googlecode.com/git/docs/api/py/api.html|Selenium API Documentation]
        for information about argument names and appropriate argument values.

        Examples:
        | # use proxy for Firefox     |              |                                           |                         |
        | ${proxy}=                   | Evaluate     | sys.modules['selenium.webdriver'].Proxy() | sys, selenium.webdriver |
        | ${proxy.http_proxy}=        | Set Variable | localhost:8888                            |                         |
        | Create Webdriver            | Firefox      | proxy=${proxy}                            |                         |
        | # use a proxy for PhantomJS |              |                                           |                         |
        | ${service args}=            | Create List  | --proxy=192.168.132.104:8888              |                         |
        | Create Webdriver            | PhantomJS    | service_args=${service args}              |                         |
        
        Example for Robot Framework < 2.8:
        | # debug IE driver |                   |                  |       |          |                       |
        | ${kwargs}=        | Create Dictionary | log_level        | DEBUG | log_file | %{HOMEPATH}${/}ie.log |
        | Create Webdriver  | Ie                | kwargs=${kwargs} |       |          |                       |
        """
        if not isinstance(kwargs, dict):
            raise RuntimeError("kwargs must be a dictionary.")
        for arg_name in kwargs:
            if arg_name in init_kwargs:
                raise RuntimeError("Got multiple values for argument '%s'." % arg_name)
            init_kwargs[arg_name] = kwargs[arg_name]
        driver_name = driver_name.strip()
        try:
            creation_func = getattr(webdriver, driver_name)
        except AttributeError:
            raise RuntimeError("'%s' is not a valid WebDriver name" % driver_name)
        self._info("Creating an instance of the %s WebDriver" % driver_name)
        driver = creation_func(**init_kwargs)
        self._debug("Created %s WebDriver instance with session id %s" % (driver_name, driver.session_id))
        return self._cache.register(driver, alias)

    def switch_browser(self, index_or_alias):
        """Switches between active browsers using index or alias.

        Index is returned from `Open Browser` and alias can be given to it.

        Example:
        | Open Browser        | http://google.com | ff       |
        | Location Should Be  | http://google.com |          |
        | Open Browser        | http://yahoo.com  | ie       | 2nd conn |
        | Location Should Be  | http://yahoo.com  |          |
        | Switch Browser      | 1                 | # index  |
        | Page Should Contain | I'm feeling lucky |          |
        | Switch Browser      | 2nd conn          | # alias  |
        | Page Should Contain | More Yahoo!       |          |
        | Close All Browsers  |                   |          |

        Above example expects that there was no other open browsers when
        opening the first one because it used index '1' when switching to it
        later. If you aren't sure about that you can store the index into
        a variable as below.

        | ${id} =            | Open Browser  | http://google.com | *firefox |
        | # Do something ... |
        | Switch Browser     | ${id}         |                   |          |
        """
        try:
            self._cache.switch(index_or_alias)
            self._debug('Switched to browser with Selenium session id %s'
                         % self._cache.current.session_id)
        except (RuntimeError, DataError):  # RF 2.6 uses RE, earlier DE
            raise RuntimeError("No browser with index or alias '%s' found."
                               % index_or_alias)

    # Public, window management

    def close_window(self):
        """Closes currently opened pop-up window."""
        self._current_browser().close()

    def get_window_identifiers(self):
        """Returns and logs id attributes of all windows known to the browser."""
        return self._log_list(self._window_manager.get_window_ids(self._current_browser()))

    def get_window_names(self):
        """Returns and logs names of all windows known to the browser."""
        values = self._window_manager.get_window_names(self._current_browser())

        # for backward compatibility, since Selenium 1 would always
        # return this constant value for the main window
        if len(values) and values[0] == 'undefined':
            values[0] = 'selenium_main_app_window'

        return self._log_list(values)

    def get_window_titles(self):
        """Returns and logs titles of all windows known to the browser."""
        return self._log_list(self._window_manager.get_window_titles(self._current_browser()))

    def maximize_browser_window(self):
        """Maximizes current browser window."""
        self._current_browser().maximize_window()

    def get_window_size(self):
        """Returns current window size as `width` then `height`.

        Example:
        | ${width} | ${height}= | Get Window Size |
        """
        size = self._current_browser().get_window_size()
        return size['width'], size['height']

    def set_window_size(self, width, height):
        """Sets the `width` and `height` of the current window to the specified values.

        Example:
        | Set Window Size | ${800} | ${600}       |
        | ${width} | ${height}= | Get Window Size |
        | Should Be Equal | ${width}  | ${800}    |
        | Should Be Equal | ${height} | ${600}    |
        """
        return self._current_browser().set_window_size(width, height)

    def select_frame(self, locator):
        """Sets frame identified by `locator` as current frame.

        Key attributes for frames are `id` and `name.` See `introduction` for
        details about locating elements.
        """
        self._info("Selecting frame '%s'." % locator)
        element = self._element_find(locator, True, True)
        self._current_browser().switch_to_frame(element)

    def select_window(self, locator=None):
        """Selects the window found with `locator` as the context of actions.

        If the window is found, all subsequent commands use that window, until
        this keyword is used again. If the window is not found, this keyword fails.
        
        By default, when a locator value is provided,
        it is matched against the title of the window and the
        javascript name of the window. If multiple windows with
        same identifier are found, the first one is selected.

        Special locator `main` (default) can be used to select the main window.

        It is also possible to specify the approach Selenium2Library should take
        to find a window by specifying a locator strategy:

        | *Strategy* | *Example*                               | *Description*                        |
        | title      | Select Window `|` title=My Document     | Matches by window title              |
        | name       | Select Window `|` name=${name}          | Matches by window javascript name    |
        | url        | Select Window `|` url=http://google.com | Matches by window's current URL      |

        Example:
        | Click Link | popup_link | # opens new window |
        | Select Window | popupName |
        | Title Should Be | Popup Title |
        | Select Window |  | | # Chooses the main window again |
        """
        self._window_manager.select(self._current_browser(), locator)

    def unselect_frame(self):
        """Sets the top frame as the current frame."""
        self._current_browser().switch_to_default_content()

    # Public, browser/current page properties

    def get_location(self):
        """Returns the current location."""
        return self._current_browser().get_current_url()

    def get_source(self):
        """Returns the entire html source of the current page or frame."""
        return self._current_browser().get_page_source()

    def get_title(self):
        """Returns title of current page."""
        return self._current_browser().get_title()

    def location_should_be(self, url):
        """Verifies that current URL is exactly `url`."""
        actual = self.get_location()
        if  actual != url:
            raise AssertionError("Location should have been '%s' but was '%s'"
                                 % (url, actual))
        self._info("Current location is '%s'." % url)

    def location_should_contain(self, expected):
        """Verifies that current URL contains `expected`."""
        actual = self.get_location()
        if not expected in actual:
            raise AssertionError("Location should have contained '%s' "
                                 "but it was '%s'." % (expected, actual))
        self._info("Current location contains '%s'." % expected)

    def log_location(self):
        """Logs and returns the current location."""
        url = self.get_location()
        self._info(url)
        return url

    def log_source(self, loglevel='INFO'):
        """Logs and returns the entire html source of the current page or frame.

        The `loglevel` argument defines the used log level. Valid log levels are
        `WARN`, `INFO` (default), `DEBUG`, `TRACE` and `NONE` (no logging).
        """
        source = self.get_source()
        self._log(source, loglevel.upper())
        return source

    def log_title(self):
        """Logs and returns the title of current page."""
        title = self.get_title()
        self._info(title)
        return title

    def title_should_be(self, title):
        """Verifies that current page title equals `title`."""
        actual = self.get_title()
        if actual != title:
            raise AssertionError("Title should have been '%s' but was '%s'"
                                  % (title, actual))
        self._info("Page title is '%s'." % title)

    # Public, navigation

    def go_back(self):
        """Simulates the user clicking the "back" button on their browser."""
        self._current_browser().back()

    def go_to(self, url):
        """Navigates the active browser instance to the provided URL."""
        self._info("Opening url '%s'" % url)
        self._current_browser().get(url)

    def reload_page(self):
        """Simulates user reloading page."""
        self._current_browser().refresh()

    # Public, execution properties

    def get_selenium_speed(self):
        """Gets the delay in seconds that is waited after each Selenium command.

        See `Set Selenium Speed` for an explanation."""
        return robot.utils.secs_to_timestr(self._speed_in_secs)

    def get_selenium_timeout(self):
        """Gets the timeout in seconds that is used by various keywords.

        See `Set Selenium Timeout` for an explanation."""
        return robot.utils.secs_to_timestr(self._timeout_in_secs)

    def get_selenium_implicit_wait(self):
        """Gets the wait in seconds that is waited by Selenium.

        See `Set Selenium Implicit Wait` for an explanation."""
        return robot.utils.secs_to_timestr(self._implicit_wait_in_secs)

    def set_selenium_speed(self, seconds):
        """Sets the delay in seconds that is waited after each Selenium command.

        This is useful mainly in slowing down the test execution to be able to
        view the execution. `seconds` may be given in Robot Framework time
        format. Returns the previous speed value.

        Example:
        | Set Selenium Speed | .5 seconds |
        """
        old_speed = self.get_selenium_speed()
        self._speed_in_secs = robot.utils.timestr_to_secs(seconds)
        for browser in self._cache.browsers:
            browser.set_speed(self._speed_in_secs)
        return old_speed

    def set_selenium_timeout(self, seconds):
        """Sets the timeout in seconds used by various keywords.

        There are several `Wait ...` keywords that take timeout as an
        argument. All of these timeout arguments are optional. The timeout
        used by all of them can be set globally using this keyword.
        See `introduction` for more information about timeouts.

        The previous timeout value is returned by this keyword and can
        be used to set the old value back later. The default timeout
        is 5 seconds, but it can be altered in `importing`.

        Example:
        | ${orig timeout} = | Set Selenium Timeout | 15 seconds |
        | Open page that loads slowly |
        | Set Selenium Timeout | ${orig timeout} |
        """
        old_timeout = self.get_selenium_timeout()
        self._timeout_in_secs = robot.utils.timestr_to_secs(seconds)
        for browser in self._cache.get_open_browsers():
            browser.set_script_timeout(self._timeout_in_secs)
        return old_timeout

    def set_selenium_implicit_wait(self, seconds):
        """Sets Selenium 2's default implicit wait in seconds and
        sets the implicit wait for all open browsers.

        From selenium 2 function 'Sets a sticky timeout to implicitly 
            wait for an element to be found, or a command to complete.
            This method only needs to be called one time per session.'

        Example:
        | ${orig wait} = | Set Selenium Implicit Wait | 10 seconds |
        | Perform AJAX call that is slow |
        | Set Selenium Implicit Wait | ${orig wait} | 
        """
        old_wait = self.get_selenium_implicit_wait()
        self._implicit_wait_in_secs = robot.utils.timestr_to_secs(seconds)
        for browser in self._cache.get_open_browsers():
            browser.implicitly_wait(self._implicit_wait_in_secs)
        return old_wait
    

    def set_browser_implicit_wait(self, seconds):
        """Sets current browser's implicit wait in seconds.

        From selenium 2 function 'Sets a sticky timeout to implicitly 
            wait for an element to be found, or a command to complete.
            This method only needs to be called one time per session.'

        Example:
        | Set Browser Implicit Wait | 10 seconds |

        See also `Set Selenium Implicit Wait`.
        """
        implicit_wait_in_secs = robot.utils.timestr_to_secs(seconds)
        self._current_browser().implicitly_wait(implicit_wait_in_secs)

    # Private

    def _current_browser(self):
        if not self._cache.current:
            raise RuntimeError('No browser is open')
        return self._cache.current

    def _get_browser_creation_function(self, browser_name):
        func_name = BROWSER_NAMES.get(browser_name.lower().replace(' ', ''))
        return getattr(self, func_name) if func_name else None

    def _make_browser(self, browser_name, desired_capabilities=None,
                      profile_dir=None, remote=None):
        creation_func = self._get_browser_creation_function(browser_name)

        if not creation_func:
            raise ValueError(browser_name + " is not a supported browser.")

        browser = creation_func(remote, desired_capabilities, profile_dir)
        browser.set_speed(self._speed_in_secs)
        browser.set_script_timeout(self._timeout_in_secs)
        browser.implicitly_wait(self._implicit_wait_in_secs)

        return browser


    def _make_ff(self , remote , desired_capabilites , profile_dir):
        
        if not profile_dir: profile_dir = FIREFOX_PROFILE_DIR
        profile = webdriver.FirefoxProfile(profile_dir)
        if remote:
            browser = self._create_remote_web_driver(webdriver.DesiredCapabilities.FIREFOX  , 
                        remote , desired_capabilites , profile)
        else:
            browser = webdriver.Firefox(firefox_profile=profile)
        return browser
    
    def _make_ie(self , remote , desired_capabilities , profile_dir):
        return self._generic_make_browser(webdriver.Ie, 
                webdriver.DesiredCapabilities.INTERNETEXPLORER, remote, desired_capabilities)

    def _make_chrome(self , remote , desired_capabilities , profile_dir):
        return self._generic_make_browser(webdriver.Chrome, 
                webdriver.DesiredCapabilities.CHROME, remote, desired_capabilities)

    def _make_opera(self , remote , desired_capabilities , profile_dir):
        return self._generic_make_browser(webdriver.Opera, 
                webdriver.DesiredCapabilities.OPERA, remote, desired_capabilities)

    def _make_phantomjs(self , remote , desired_capabilities , profile_dir):
        return self._generic_make_browser(webdriver.PhantomJS, 
                webdriver.DesiredCapabilities.PHANTOMJS, remote, desired_capabilities)

    def _make_htmlunit(self , remote , desired_capabilities , profile_dir):
        return self._generic_make_browser(webdriver.Remote, 
                webdriver.DesiredCapabilities.HTMLUNIT, remote, desired_capabilities)

    def _make_htmlunitwithjs(self , remote , desired_capabilities , profile_dir):
        return self._generic_make_browser(webdriver.Remote, 
                webdriver.DesiredCapabilities.HTMLUNITWITHJS, remote, desired_capabilities)

    def _make_android(self , remote , desired_capabilities , profile_dir):
        return self._generic_make_browser(webdriver.Remote,
                webdriver.DesiredCapabilities.ANDROID, remote, desired_capabilities)

    def _make_iphone(self , remote , desired_capabilities , profile_dir):
        return self._generic_make_browser(webdriver.Remote,
                webdriver.DesiredCapabilities.IPHONE, remote, desired_capabilities)

    def _make_safari(self , remote , desired_capabilities , profile_dir):
        return self._generic_make_browser(webdriver.Safari,
                webdriver.DesiredCapabilities.SAFARI, remote, desired_capabilities)

    def _generic_make_browser(self, webdriver_type , desired_cap_type, remote_url, desired_caps):
        '''most of the make browser functions just call this function which creates the 
        appropriate web-driver'''
        if not remote_url: 
            browser = webdriver_type()
        else:
            browser = self._create_remote_web_driver(desired_cap_type,remote_url , desired_caps)
        return browser

    def _create_remote_web_driver(self , capabilities_type , remote_url , desired_capabilities=None , profile=None):
        '''parses the string based desired_capabilities if neccessary and
        creates the associated remote web driver'''

        desired_capabilities_object = capabilities_type.copy()

        if type(desired_capabilities) in (str, unicode):
            desired_capabilities = self._parse_capabilities_string(desired_capabilities)

        desired_capabilities_object.update(desired_capabilities or {})

        return webdriver.Remote(desired_capabilities=desired_capabilities_object,
                command_executor=str(remote_url), browser_profile=profile)

    def _parse_capabilities_string(self, capabilities_string):
        '''parses the string based desired_capabilities which should be in the form
        key1:val1,key2:val2
        '''
        desired_capabilities = {}

        if not capabilities_string:
            return desired_capabilities

        for cap in capabilities_string.split(","):
            (key, value) = cap.split(":", 1)
            desired_capabilities[key.strip()] = value.strip()

        return desired_capabilities
    

########NEW FILE########
__FILENAME__ = _cookie
from keywordgroup import KeywordGroup

class _CookieKeywords(KeywordGroup):

    def delete_all_cookies(self):
        """Deletes all cookies."""
        self._current_browser().delete_all_cookies()

    def delete_cookie(self, name):
        """Deletes cookie matching `name`.

        If the cookie is not found, nothing happens.
        """
        self._current_browser().delete_cookie(name)

    def get_cookies(self):
        """Returns all cookies of the current page."""
        pairs = []
        for cookie in self._current_browser().get_cookies():
            pairs.append(cookie['name'] + "=" + cookie['value'])
        return '; '.join(pairs)

    def get_cookie_value(self, name):
        """Returns value of cookie found with `name`.

        If no cookie is found with `name`, this keyword fails.
        """
        cookie = self._current_browser().get_cookie(name)
        if cookie is not None:
            return cookie['value']
        raise ValueError("Cookie with name %s not found." % name)

    def add_cookie(self,name, value, path=None, domain=None, secure=None,
            expiry=None):
        """Adds a cookie to your current session.
        "name" and "value" are required, "path", "domain" and "secure" are
        optional"""
        new_cookie = {'name'    : name,
                      'value'   : value}
        if path: new_cookie['path'] = path
        if domain: new_cookie['domain'] = domain
        #secure should be True or False so check explicitly for None
        if not secure is None: new_cookie['secure'] = secure

        self._current_browser().add_cookie(new_cookie)

########NEW FILE########
__FILENAME__ = _element
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from Selenium2Library import utils
from Selenium2Library.locators import ElementFinder
from keywordgroup import KeywordGroup

class _ElementKeywords(KeywordGroup):

    def __init__(self):
        self._element_finder = ElementFinder()

    # Public, element lookups

    def current_frame_contains(self, text, loglevel='INFO'):
        """Verifies that current frame contains `text`.

        See `Page Should Contain ` for explanation about `loglevel` argument.
        """
        if not self._is_text_present(text):
            self.log_source(loglevel)
            raise AssertionError("Page should have contained text '%s' "
                                 "but did not" % text)
        self._info("Current page contains text '%s'." % text)


    def current_frame_should_not_contain(self, text, loglevel='INFO'):
        """Verifies that current frame contains `text`.

        See `Page Should Contain ` for explanation about `loglevel` argument.
        """
        if self._is_text_present(text):
            self.log_source(loglevel)
            raise AssertionError("Page should not have contained text '%s' "
                                 "but it did" % text)
        self._info("Current page should not contain text '%s'." % text)

    def element_should_contain(self, locator, expected, message=''):
        """Verifies element identified by `locator` contains text `expected`.

        If you wish to assert an exact (not a substring) match on the text
        of the element, use `Element Text Should Be`.

        `message` can be used to override the default error message.

        Key attributes for arbitrary elements are `id` and `name`. See
        `introduction` for details about locating elements.
        """
        self._info("Verifying element '%s' contains text '%s'."
                    % (locator, expected))
        actual = self._get_text(locator)
        if not expected in actual:
            if not message:
                message = "Element '%s' should have contained text '%s' but "\
                          "its text was '%s'." % (locator, expected, actual)
            raise AssertionError(message)

    def frame_should_contain(self, locator, text, loglevel='INFO'):
        """Verifies frame identified by `locator` contains `text`.

        See `Page Should Contain ` for explanation about `loglevel` argument.

        Key attributes for frames are `id` and `name.` See `introduction` for
        details about locating elements.
        """
        if not self._frame_contains(locator, text):
            self.log_source(loglevel)
            raise AssertionError("Page should have contained text '%s' "
                                 "but did not" % text)
        self._info("Current page contains text '%s'." % text)

    def page_should_contain(self, text, loglevel='INFO'):
        """Verifies that current page contains `text`.

        If this keyword fails, it automatically logs the page source
        using the log level specified with the optional `loglevel` argument.
        Giving `NONE` as level disables logging.
        """
        if not self._page_contains(text):
            self.log_source(loglevel)
            raise AssertionError("Page should have contained text '%s' "
                                 "but did not" % text)
        self._info("Current page contains text '%s'." % text)

    def page_should_contain_element(self, locator, message='', loglevel='INFO'):
        """Verifies element identified by `locator` is found on the current page.

        `message` can be used to override default error message.

        See `Page Should Contain` for explanation about `loglevel` argument.

        Key attributes for arbitrary elements are `id` and `name`. See
        `introduction` for details about locating elements.
        """
        self._page_should_contain_element(locator, None, message, loglevel)

    def page_should_not_contain(self, text, loglevel='INFO'):
        """Verifies the current page does not contain `text`.

        See `Page Should Contain ` for explanation about `loglevel` argument.
        """
        if self._page_contains(text):
            self.log_source(loglevel)
            raise AssertionError("Page should not have contained text '%s'" % text)
        self._info("Current page does not contain text '%s'." % text)

    def page_should_not_contain_element(self, locator, message='', loglevel='INFO'):
        """Verifies element identified by `locator` is not found on the current page.

        `message` can be used to override the default error message.

        See `Page Should Contain ` for explanation about `loglevel` argument.

        Key attributes for arbitrary elements are `id` and `name`. See
        `introduction` for details about locating elements.
        """
        self._page_should_not_contain_element(locator, None, message, loglevel)

    # Public, attributes

    def assign_id_to_element(self, locator, id):
        """Assigns a temporary identifier to element specified by `locator`.

        This is mainly useful if the locator is complicated/slow XPath expression.
        Identifier expires when the page is reloaded.

        Example:
        | Assign ID to Element | xpath=//div[@id="first_div"] | my id |
        | Page Should Contain Element | my id |
        """
        self._info("Assigning temporary id '%s' to element '%s'" % (id, locator))
        element = self._element_find(locator, True, True)
        self._current_browser().execute_script("arguments[0].id = '%s';" % id, element)

    def element_should_be_disabled(self, locator):
        """Verifies that element identified with `locator` is disabled.

        Key attributes for arbitrary elements are `id` and `name`. See
        `introduction` for details about locating elements.
        """
        if self._is_enabled(locator):
            raise AssertionError("Element '%s' is enabled." % (locator))

    def element_should_be_enabled(self, locator):
        """Verifies that element identified with `locator` is enabled.

        Key attributes for arbitrary elements are `id` and `name`. See
        `introduction` for details about locating elements.
        """
        if not self._is_enabled(locator):
            raise AssertionError("Element '%s' is disabled." % (locator))

    def element_should_be_visible(self, locator, message=''):
        """Verifies that the element identified by `locator` is visible.

        Herein, visible means that the element is logically visible, not optically
        visible in the current browser viewport. For example, an element that carries
        display:none is not logically visible, so using this keyword on that element
        would fail.

        `message` can be used to override the default error message.

        Key attributes for arbitrary elements are `id` and `name`. See
        `introduction` for details about locating elements.
        """
        self._info("Verifying element '%s' is visible." % locator)
        visible = self._is_visible(locator)
        if not visible:
            if not message:
                message = "The element '%s' should be visible, but it "\
                          "is not." % locator
            raise AssertionError(message)

    def element_should_not_be_visible(self, locator, message=''):
        """Verifies that the element identified by `locator` is NOT visible.

        This is the opposite of `Element Should Be Visible`.

        `message` can be used to override the default error message.

        Key attributes for arbitrary elements are `id` and `name`. See
        `introduction` for details about locating elements.
        """
        self._info("Verifying element '%s' is not visible." % locator)
        visible = self._is_visible(locator)
        if visible:
            if not message:
                message = "The element '%s' should not be visible, "\
                          "but it is." % locator
            raise AssertionError(message)

    def element_text_should_be(self, locator, expected, message=''):
        """Verifies element identified by `locator` exactly contains text `expected`.

        In contrast to `Element Should Contain`, this keyword does not try
        a substring match but an exact match on the element identified by `locator`.

        `message` can be used to override the default error message.

        Key attributes for arbitrary elements are `id` and `name`. See
        `introduction` for details about locating elements.
        """
        self._info("Verifying element '%s' contains exactly text '%s'."
                    % (locator, expected))
        element = self._element_find(locator, True, True)
        actual = element.text
        if expected != actual:
            if not message:
                message = "The text of element '%s' should have been '%s' but "\
                          "in fact it was '%s'." % (locator, expected, actual)
            raise AssertionError(message)

    def get_element_attribute(self, attribute_locator):
        """Return value of element attribute.

        `attribute_locator` consists of element locator followed by an @ sign
        and attribute name, for example "element_id@class".
        """
        locator, attribute_name = self._parse_attribute_locator(attribute_locator)
        element = self._element_find(locator, True, False)
        if element is None:
            raise ValueError("Element '%s' not found." % (locator))
        return element.get_attribute(attribute_name)

    def get_horizontal_position(self, locator):
        """Returns horizontal position of element identified by `locator`.

        The position is returned in pixels off the left side of the page,
        as an integer. Fails if a matching element is not found.

        See also `Get Vertical Position`.
        """
        element = self._element_find(locator, True, False)
        if element is None:
            raise AssertionError("Could not determine position for '%s'" % (locator))
        return element.location['x']

    def get_value(self, locator):
        """Returns the value attribute of element identified by `locator`.

        See `introduction` for details about locating elements.
        """
        return self._get_value(locator)

    def get_text(self, locator):
        """Returns the text value of element identified by `locator`.

        See `introduction` for details about locating elements.
        """
        return self._get_text(locator)

    def get_vertical_position(self, locator):
        """Returns vertical position of element identified by `locator`.

        The position is returned in pixels off the top of the page,
        as an integer. Fails if a matching element is not found.

        See also `Get Horizontal Position`.
        """
        element = self._element_find(locator, True, False)
        if element is None:
            raise AssertionError("Could not determine position for '%s'" % (locator))
        return element.location['y']

    # Public, mouse input/events

    def click_element(self, locator):
        """Click element identified by `locator`.

        Key attributes for arbitrary elements are `id` and `name`. See
        `introduction` for details about locating elements.
        """
        self._info("Clicking element '%s'." % locator)
        self._element_find(locator, True, True).click()

    def click_element_at_coordinates(self, locator, xoffset, yoffset):
        """Click element identified by `locator` at x/y coordinates of the element.
        Cursor is moved and the center of the element and x/y coordinates are
        calculted from that point.

        Key attributes for arbitrary elements are `id` and `name`. See
        `introduction` for details about locating elements.
        """
        self._info("Click clicking element '%s' in coordinates '%s', '%s'." % (locator, xoffset, yoffset))
        element = self._element_find(locator, True, True)
        #self._element_find(locator, True, True).click()
        #ActionChains(self._current_browser()).move_to_element_with_offset(element, xoffset, yoffset).click().perform()
        ActionChains(self._current_browser()).move_to_element(element).move_by_offset(xoffset, yoffset).click().perform()

    def double_click_element(self, locator):
        """Double click element identified by `locator`.

        Key attributes for arbitrary elements are `id` and `name`. See
        `introduction` for details about locating elements.
        """
        self._info("Double clicking element '%s'." % locator)
        element = self._element_find(locator, True, True)
        ActionChains(self._current_browser()).double_click(element).perform()

    def focus(self, locator):
        """Sets focus to element identified by `locator`."""
        element = self._element_find(locator, True, True)
        self._current_browser().execute_script("arguments[0].focus();", element)

    def drag_and_drop(self, source, target):
        """Drags element identified with `source` which is a locator.

        Element can be moved on top of another element with `target`
        argument.

        `target` is a locator of the element where the dragged object is
        dropped.

        Examples:
        | Drag And Drop | elem1 | elem2 | # Move elem1 over elem2. |
        """
        src_elem = self._element_find(source,True,True)
        trg_elem =  self._element_find(target,True,True)
        ActionChains(self._current_browser()).drag_and_drop(src_elem, trg_elem).perform()


    def drag_and_drop_by_offset(self, source, xoffset, yoffset):
        """Drags element identified with `source` which is a locator.

        Element will be moved by xoffset and yoffset.  each of which is a
        negative or positive number specify the offset.

        Examples:
        | Drag And Drop | myElem | 50 | -35 | # Move myElem 50px right and 35px down. |
        """
        src_elem = self._element_find(source, True, True)
        ActionChains(self._current_browser()).drag_and_drop_by_offset(src_elem, xoffset, yoffset).perform()

    def mouse_down(self, locator):
        """Simulates pressing the left mouse button on the element specified by `locator`.

        The element is pressed without releasing the mouse button.

        Key attributes for arbitrary elements are `id` and `name`. See
        `introduction` for details about locating elements.

        See also the more specific keywords `Mouse Down On Image` and
        `Mouse Down On Link`.
        """
        self._info("Simulating Mouse Down on element '%s'" % locator)
        element = self._element_find(locator, True, False)
        if element is None:
            raise AssertionError("ERROR: Element %s not found." % (locator))
        ActionChains(self._current_browser()).click_and_hold(element).perform()

    def mouse_out(self, locator):
        """Simulates moving mouse away from the element specified by `locator`.

        Key attributes for arbitrary elements are `id` and `name`. See
        `introduction` for details about locating elements.
        """
        self._info("Simulating Mouse Out on element '%s'" % locator)
        element = self._element_find(locator, True, False)
        if element is None:
            raise AssertionError("ERROR: Element %s not found." % (locator))
        size = element.size
        offsetx = (size['width'] / 2) + 1
        offsety = (size['height'] / 2) + 1
        ActionChains(self._current_browser()).move_to_element(element).move_by_offset(offsetx, offsety).perform()

    def mouse_over(self, locator):
        """Simulates hovering mouse over the element specified by `locator`.

        Key attributes for arbitrary elements are `id` and `name`. See
        `introduction` for details about locating elements.
        """
        self._info("Simulating Mouse Over on element '%s'" % locator)
        element = self._element_find(locator, True, False)
        if element is None:
            raise AssertionError("ERROR: Element %s not found." % (locator))
        ActionChains(self._current_browser()).move_to_element(element).perform()

    def mouse_up(self, locator):
        """Simulates releasing the left mouse button on the element specified by `locator`.

        Key attributes for arbitrary elements are `id` and `name`. See
        `introduction` for details about locating elements.
        """
        self._info("Simulating Mouse Up on element '%s'" % locator)
        element = self._element_find(locator, True, False)
        if element is None:
            raise AssertionError("ERROR: Element %s not found." % (locator))
        ActionChains(self._current_browser()).release(element).perform()

    def open_context_menu(self, locator):
        """Opens context menu on element identified by `locator`."""
        element = self._element_find(locator, True, True)
        ActionChains(self._current_browser()).context_click(element).perform()

    def simulate(self, locator, event):
        """Simulates `event` on element identified by `locator`.

        This keyword is useful if element has OnEvent handler that needs to be
        explicitly invoked.

        See `introduction` for details about locating elements.
        """
        element = self._element_find(locator, True, True)
        script = """
element = arguments[0];
eventName = arguments[1];
if (document.createEventObject) { // IE
    return element.fireEvent('on' + eventName, document.createEventObject());
}
var evt = document.createEvent("HTMLEvents");
evt.initEvent(eventName, true, true);
return !element.dispatchEvent(evt);
        """
        self._current_browser().execute_script(script, element, event)

    def press_key(self, locator, key):
        """Simulates user pressing key on element identified by `locator`.

        `key` is either a single character, or a numerical ASCII code of the key
        lead by '\\'.

        Examples:
        | Press Key | text_field   | q |
        | Press Key | login_button | \\13 | # ASCII code for enter key |
        """
        if key.startswith('\\') and len(key) > 1:
            key = self._map_ascii_key_code_to_key(int(key[1:]))
        #if len(key) > 1:
        #    raise ValueError("Key value '%s' is invalid.", key)
        element = self._element_find(locator, True, True)
        #select it
        element.send_keys(key)

    # Public, links

    def click_link(self, locator):
        """Clicks a link identified by locator.

        Key attributes for links are `id`, `name`, `href` and link text. See
        `introduction` for details about locating elements.
        """
        self._info("Clicking link '%s'." % locator)
        link = self._element_find(locator, True, True, tag='a')
        link.click()

    def get_all_links(self):
        """Returns a list containing ids of all links found in current page.

        If a link has no id, an empty string will be in the list instead.
        """
        links = []
        for anchor in self._element_find("tag=a", False, False, 'a'):
            links.append(anchor.get_attribute('id'))
        return links

    def mouse_down_on_link(self, locator):
        """Simulates a mouse down event on a link.

        Key attributes for links are `id`, `name`, `href` and link text. See
        `introduction` for details about locating elements.
        """
        element = self._element_find(locator, True, True, 'link')
        ActionChains(self._current_browser()).click_and_hold(element).perform()

    def page_should_contain_link(self, locator, message='', loglevel='INFO'):
        """Verifies link identified by `locator` is found from current page.

        See `Page Should Contain Element` for explanation about `message` and
        `loglevel` arguments.

        Key attributes for links are `id`, `name`, `href` and link text. See
        `introduction` for details about locating elements.
        """
        self._page_should_contain_element(locator, 'link', message, loglevel)

    def page_should_not_contain_link(self, locator, message='', loglevel='INFO'):
        """Verifies image identified by `locator` is not found from current page.

        See `Page Should Contain Element` for explanation about `message` and
        `loglevel` arguments.

        Key attributes for images are `id`, `src` and `alt`. See
        `introduction` for details about locating elements.
        """
        self._page_should_not_contain_element(locator, 'link', message, loglevel)

    # Public, images

    def click_image(self, locator):
        """Clicks an image found by `locator`.

        Key attributes for images are `id`, `src` and `alt`. See
        `introduction` for details about locating elements.
        """
        self._info("Clicking image '%s'." % locator)
        element = self._element_find(locator, True, False, 'image')
        if element is None:
            # A form may have an image as it's submit trigger.
            element = self._element_find(locator, True, True, 'input')
        element.click()

    def mouse_down_on_image(self, locator):
        """Simulates a mouse down event on an image.

        Key attributes for images are `id`, `src` and `alt`. See
        `introduction` for details about locating elements.
        """
        element = self._element_find(locator, True, True, 'image')
        ActionChains(self._current_browser()).click_and_hold(element).perform()

    def page_should_contain_image(self, locator, message='', loglevel='INFO'):
        """Verifies image identified by `locator` is found from current page.

        See `Page Should Contain Element` for explanation about `message` and
        `loglevel` arguments.

        Key attributes for images are `id`, `src` and `alt`. See
        `introduction` for details about locating elements.
        """
        self._page_should_contain_element(locator, 'image', message, loglevel)

    def page_should_not_contain_image(self, locator, message='', loglevel='INFO'):
        """Verifies image identified by `locator` is found from current page.

        See `Page Should Contain Element` for explanation about `message` and
        `loglevel` arguments.

        Key attributes for images are `id`, `src` and `alt`. See
        `introduction` for details about locating elements.
        """
        self._page_should_not_contain_element(locator, 'image', message, loglevel)

    # Public, xpath

    def get_matching_xpath_count(self, xpath):
        """Returns number of elements matching `xpath`

        If you wish to assert the number of matching elements, use
        `Xpath Should Match X Times`.
        """
        count = len(self._element_find("xpath=" + xpath, False, False))
        return str(count)

    def xpath_should_match_x_times(self, xpath, expected_xpath_count, message='', loglevel='INFO'):
        """Verifies that the page contains the given number of elements located by the given `xpath`.

        See `Page Should Contain Element` for explanation about `message` and
        `loglevel` arguments.
        """
        actual_xpath_count = len(self._element_find("xpath=" + xpath, False, False))
        if int(actual_xpath_count) != int(expected_xpath_count):
            if not message:
                message = "Xpath %s should have matched %s times but matched %s times"\
                            %(xpath, expected_xpath_count, actual_xpath_count)
            self.log_source(loglevel)
            raise AssertionError(message)
        self._info("Current page contains %s elements matching '%s'."
                   % (actual_xpath_count, xpath))

    # Private

    def _element_find(self, locator, first_only, required, tag=None):
        browser = self._current_browser()
        elements = self._element_finder.find(browser, locator, tag)
        if required and len(elements) == 0:
            raise ValueError("Element locator '" + locator + "' did not match any elements.")
        if first_only:
            if len(elements) == 0: return None
            return elements[0]
        return elements

    def _frame_contains(self, locator, text):
        browser = self._current_browser()
        element = self._element_find(locator, True, True)
        browser.switch_to_frame(element)
        self._info("Searching for text from frame '%s'." % locator)
        found = self._is_text_present(text)
        browser.switch_to_default_content()
        return found

    def _get_text(self, locator):
        element = self._element_find(locator, True, True)
        if element is not None:
            return element.text
        return None

    def _get_value(self, locator, tag=None):
        element = self._element_find(locator, True, False, tag=tag)
        return element.get_attribute('value') if element is not None else None

    def _is_enabled(self, locator):
        element = self._element_find(locator, True, True)
        if not self._is_form_element(element):
            raise AssertionError("ERROR: Element %s is not an input." % (locator))
        if not element.is_enabled():
            return False
        read_only = element.get_attribute('readonly')
        if read_only == 'readonly' or read_only == 'true':
            return False
        return True

    def _is_text_present(self, text):
        locator = "xpath=//*[contains(., %s)]" % utils.escape_xpath_value(text);
        return self._is_element_present(locator)

    def _is_visible(self, locator):
        element = self._element_find(locator, True, False)
        if element is not None:
            return element.is_displayed()
        return None

    def _map_ascii_key_code_to_key(self, key_code):
        map = {
            0: Keys.NULL,
            8: Keys.BACK_SPACE,
            9: Keys.TAB,
            10: Keys.RETURN,
            13: Keys.ENTER,
            24: Keys.CANCEL,
            27: Keys.ESCAPE,
            32: Keys.SPACE,
            42: Keys.MULTIPLY,
            43: Keys.ADD,
            44: Keys.SEPARATOR,
            45: Keys.SUBTRACT,
            56: Keys.DECIMAL,
            57: Keys.DIVIDE,
            59: Keys.SEMICOLON,
            61: Keys.EQUALS,
            127: Keys.DELETE
        }
        key = map.get(key_code)
        if key is None:
            key = chr(key_code)
        return key

    def _parse_attribute_locator(self, attribute_locator):
        parts = attribute_locator.rpartition('@')
        if len(parts[0]) == 0:
            raise ValueError("Attribute locator '%s' does not contain an element locator." % (attribute_locator))
        if len(parts[2]) == 0:
            raise ValueError("Attribute locator '%s' does not contain an attribute name." % (attribute_locator))
        return (parts[0], parts[2])

    def _is_element_present(self, locator, tag=None):
        return (self._element_find(locator, True, False, tag=tag) != None)

    def _page_contains(self, text):
        browser = self._current_browser()
        browser.switch_to_default_content()

        if self._is_text_present(text):
            return True

        subframes = self._element_find("xpath=//frame|//iframe", False, False)
        self._debug('Current frame has %d subframes' % len(subframes))
        for frame in subframes:
            browser.switch_to_frame(frame)
            found_text = self._is_text_present(text)
            browser.switch_to_default_content()
            if found_text:
                return True

        return False

    def _page_should_contain_element(self, locator, tag, message, loglevel):
        element_name = tag if tag is not None else 'element'
        if not self._is_element_present(locator, tag):
            if not message:
                message = "Page should have contained %s '%s' but did not"\
                           % (element_name, locator)
            self.log_source(loglevel)
            raise AssertionError(message)
        self._info("Current page contains %s '%s'." % (element_name, locator))

    def _page_should_not_contain_element(self, locator, tag, message, loglevel):
        element_name = tag if tag is not None else 'element'
        if self._is_element_present(locator, tag):
            if not message:
                message = "Page should not have contained %s '%s'"\
                           % (element_name, locator)
            self.log_source(loglevel)
            raise AssertionError(message)
        self._info("Current page does not contain %s '%s'."
                   % (element_name, locator))


########NEW FILE########
__FILENAME__ = _formelement
import os
from keywordgroup import KeywordGroup

class _FormElementKeywords(KeywordGroup):

    # Public, form

    def submit_form(self, locator=None):
        """Submits a form identified by `locator`.

        If `locator` is empty, first form in the page will be submitted.
        Key attributes for forms are `id` and `name`. See `introduction` for
        details about locating elements.
        """
        self._info("Submitting form '%s'." % locator)
        if not locator:
            locator = 'xpath=//form'
        element = self._element_find(locator, True, True, 'form')
        element.submit()

    # Public, checkboxes

    def checkbox_should_be_selected(self, locator):
        """Verifies checkbox identified by `locator` is selected/checked.

        Key attributes for checkboxes are `id` and `name`. See `introduction`
        for details about locating elements.
        """
        self._info("Verifying checkbox '%s' is selected." % locator)
        element = self._get_checkbox(locator)
        if not element.is_selected():
            raise AssertionError("Checkbox '%s' should have been selected "
                                 "but was not" % locator)

    def checkbox_should_not_be_selected(self, locator):
        """Verifies checkbox identified by `locator` is not selected/checked.

        Key attributes for checkboxes are `id` and `name`. See `introduction`
        for details about locating elements.
        """
        self._info("Verifying checkbox '%s' is not selected." % locator)
        element = self._get_checkbox(locator)
        if element.is_selected():
            raise AssertionError("Checkbox '%s' should not have been selected"
                                  % locator)

    def page_should_contain_checkbox(self, locator, message='', loglevel='INFO'):
        """Verifies checkbox identified by `locator` is found from current page.

        See `Page Should Contain Element` for explanation about `message` and
        `loglevel` arguments.

        Key attributes for checkboxes are `id` and `name`. See `introduction`
        for details about locating elements.
        """
        self._page_should_contain_element(locator, 'checkbox', message, loglevel)

    def page_should_not_contain_checkbox(self, locator, message='', loglevel='INFO'):
        """Verifies checkbox identified by `locator` is not found from current page.

        See `Page Should Contain Element` for explanation about `message` and
        `loglevel` arguments.

        Key attributes for checkboxes are `id` and `name`. See `introduction`
        for details about locating elements.
        """
        self._page_should_not_contain_element(locator, 'checkbox', message, loglevel)

    def select_checkbox(self, locator):
        """Selects checkbox identified by `locator`.

        Does nothing if checkbox is already selected. Key attributes for
        checkboxes are `id` and `name`. See `introduction` for details about
        locating elements.
        """
        self._info("Selecting checkbox '%s'." % locator)
        element = self._get_checkbox(locator)
        if not element.is_selected():
            element.click()

    def unselect_checkbox(self, locator):
        """Removes selection of checkbox identified by `locator`.

        Does nothing if the checkbox is not checked. Key attributes for
        checkboxes are `id` and `name`. See `introduction` for details about
        locating elements.
        """
        self._info("Unselecting checkbox '%s'." % locator)
        element = self._get_checkbox(locator)
        if element.is_selected():
            element.click()

    # Public, radio buttons

    def page_should_contain_radio_button(self, locator, message='', loglevel='INFO'):
        """Verifies radio button identified by `locator` is found from current page.

        See `Page Should Contain Element` for explanation about `message` and
        `loglevel` arguments.

        Key attributes for radio buttons are `id`, `name` and `value`. See
        `introduction` for details about locating elements.
        """
        self._page_should_contain_element(locator, 'radio button', message, loglevel)

    def page_should_not_contain_radio_button(self, locator, message='', loglevel='INFO'):
        """Verifies radio button identified by `locator` is not found from current page.

        See `Page Should Contain Element` for explanation about `message` and
        `loglevel` arguments.

        Key attributes for radio buttons are `id`, `name` and `value`. See
        `introduction` for details about locating elements.
        """
        self._page_should_not_contain_element(locator, 'radio button', message, loglevel)

    def radio_button_should_be_set_to(self, group_name, value):
        """Verifies radio button group identified by `group_name` has its selection set to `value`.

        See `Select Radio Button` for information about how radio buttons are
        located.
        """
        self._info("Verifying radio button '%s' has selection '%s'." \
                   % (group_name, value))
        elements = self._get_radio_buttons(group_name)
        actual_value = self._get_value_from_radio_buttons(elements)
        if actual_value is None or actual_value != value:
            raise AssertionError("Selection of radio button '%s' should have "
                                 "been '%s' but was '%s'"
                                  % (group_name, value, actual_value))

    def radio_button_should_not_be_selected(self, group_name):
        """Verifies radio button group identified by `group_name` has no selection.

        See `Select Radio Button` for information about how radio buttons are
        located.
        """
        self._info("Verifying radio button '%s' has no selection." % group_name)
        elements = self._get_radio_buttons(group_name)
        actual_value = self._get_value_from_radio_buttons(elements)
        if actual_value is not None:
            raise AssertionError("Radio button group '%s' should not have had "
                                 "selection, but '%s' was selected"
                                  % (group_name, actual_value))

    def select_radio_button(self, group_name, value):
        """Sets selection of radio button group identified by `group_name` to `value`.

        The radio button to be selected is located by two arguments:
        - `group_name` is used as the name of the radio input
        - `value` is used for the value attribute or for the id attribute

        The XPath used to locate the correct radio button then looks like this:
        //input[@type='radio' and @name='group_name' and (@value='value' or @id='value')]

        Examples:
        | Select Radio Button | size | XL | # Matches HTML like <input type="radio" name="size" value="XL">XL</input> |
        | Select Radio Button | size | sizeXL | # Matches HTML like <input type="radio" name="size" value="XL" id="sizeXL">XL</input> |
        """
        self._info("Selecting '%s' from radio button '%s'." % (value, group_name))
        element = self._get_radio_button_with_value(group_name, value)
        if not element.is_selected():
            element.click()

    # Public, text fields

    def choose_file(self, locator, file_path):
        """Inputs the `file_path` into file input field found by `identifier`.

        This keyword is most often used to input files into upload forms.
        The file specified with `file_path` must be available on the same host 
        where the Selenium Server is running.

        Example:
        | Choose File | my_upload_field | /home/user/files/trades.csv |
        """
        if not os.path.isfile(file_path):
            self._info("File '%s' does not exist on the local file system"
                        % file_path)
        self._element_find(locator, True, True).send_keys(file_path)

    def input_password(self, locator, text):
        """Types the given password into text field identified by `locator`.

        Difference between this keyword and `Input Text` is that this keyword
        does not log the given password. See `introduction` for details about
        locating elements.
        """
        self._info("Typing password into text field '%s'" % locator)
        self._input_text_into_text_field(locator, text)

    def input_text(self, locator, text):
        """Types the given `text` into text field identified by `locator`.

        See `introduction` for details about locating elements.
        """
        self._info("Typing text '%s' into text field '%s'" % (text, locator))
        self._input_text_into_text_field(locator, text)

    def page_should_contain_textfield(self, locator, message='', loglevel='INFO'):
        """Verifies text field identified by `locator` is found from current page.

        See `Page Should Contain Element` for explanation about `message` and
        `loglevel` arguments.

        Key attributes for text fields are `id` and `name`. See `introduction`
        for details about locating elements.
        """
        self._page_should_contain_element(locator, 'text field', message, loglevel)

    def page_should_not_contain_textfield(self, locator, message='', loglevel='INFO'):
        """Verifies text field identified by `locator` is not found from current page.

        See `Page Should Contain Element` for explanation about `message` and
        `loglevel` arguments.

        Key attributes for text fields are `id` and `name`. See `introduction`
        for details about locating elements.
        """
        self._page_should_not_contain_element(locator, 'text field', message, loglevel)

    def textfield_should_contain(self, locator, expected, message=''):
        """Verifies text field identified by `locator` contains text `expected`.

        `message` can be used to override default error message.

        Key attributes for text fields are `id` and `name`. See `introduction`
        for details about locating elements.
        """
        actual = self._get_value(locator, 'text field')
        if not expected in actual:
            if not message:
                message = "Text field '%s' should have contained text '%s' "\
                          "but it contained '%s'" % (locator, expected, actual)
            raise AssertionError(message)
        self._info("Text field '%s' contains text '%s'." % (locator, expected))

    def textfield_value_should_be(self, locator, expected, message=''):
        """Verifies the value in text field identified by `locator` is exactly `expected`.

        `message` can be used to override default error message.

        Key attributes for text fields are `id` and `name`. See `introduction`
        for details about locating elements.
        """
        element = self._element_find(locator, True, False, 'text field')
        if element is None: element = self._element_find(locator, True, False, 'file upload')
        actual = element.get_attribute('value') if element is not None else None
        if actual != expected:
            if not message:
                message = "Value of text field '%s' should have been '%s' "\
                          "but was '%s'" % (locator, expected, actual)
            raise AssertionError(message)
        self._info("Content of text field '%s' is '%s'." % (locator, expected))

    def textarea_should_contain(self, locator, expected, message=''):
        """Verifies text area identified by `locator` contains text `expected`.

        `message` can be used to override default error message.

        Key attributes for text areas are `id` and `name`. See `introduction`
        for details about locating elements.
        """
        actual = self._get_value(locator, 'text area')
        if actual is not None:
            if not expected in actual:
                if not message:
                    message = "Text field '%s' should have contained text '%s' "\
                              "but it contained '%s'" % (locator, expected, actual)
                raise AssertionError(message)
        else:
            raise ValueError("Element locator '" + locator + "' did not match any elements.")
        self._info("Text area '%s' contains text '%s'." % (locator, expected))
        
    def textarea_value_should_be(self, locator, expected, message=''):
        """Verifies the value in text area identified by `locator` is exactly `expected`.

        `message` can be used to override default error message.

        Key attributes for text areas are `id` and `name`. See `introduction`
        for details about locating elements.
        """
        actual = self._get_value(locator, 'text area')
        if actual is not None:
            if expected!=actual:
                if not message:
                    message = "Text field '%s' should have contained text '%s' "\
                              "but it contained '%s'" % (locator, expected, actual)
                raise AssertionError(message)
        else:
            raise ValueError("Element locator '" + locator + "' did not match any elements.")
        self._info("Content of text area '%s' is '%s'." % (locator, expected))
        
    # Public, buttons

    def click_button(self, locator):
        """Clicks a button identified by `locator`.

        Key attributes for buttons are `id`, `name` and `value`. See
        `introduction` for details about locating elements.
        """
        self._info("Clicking button '%s'." % locator)
        element = self._element_find(locator, True, False, 'input')
        if element is None:
            element = self._element_find(locator, True, True, 'button')
        element.click()

    def page_should_contain_button(self, locator, message='', loglevel='INFO'):
        """Verifies button identified by `locator` is found from current page.

        This keyword searches for buttons created with either `input` or `button` tag.

        See `Page Should Contain Element` for explanation about `message` and
        `loglevel` arguments.

        Key attributes for buttons are `id`, `name` and `value`. See
        `introduction` for details about locating elements.
        """
        try:
            self._page_should_contain_element(locator, 'input', message, loglevel)
        except AssertionError:
            self._page_should_contain_element(locator, 'button', message, loglevel)

    def page_should_not_contain_button(self, locator, message='', loglevel='INFO'):
        """Verifies button identified by `locator` is not found from current page.

        This keyword searches for buttons created with either `input` or `button` tag.

        See `Page Should Contain Element` for explanation about `message` and
        `loglevel` arguments.

        Key attributes for buttons are `id`, `name` and `value`. See
        `introduction` for details about locating elements.
        """
        self._page_should_not_contain_element(locator, 'button', message, loglevel)
        self._page_should_not_contain_element(locator, 'input', message, loglevel)

    # Private

    def _get_checkbox(self, locator):
        return self._element_find(locator, True, True, tag='input')

    def _get_radio_buttons(self, group_name):
        xpath = "xpath=//input[@type='radio' and @name='%s']" % group_name
        self._debug('Radio group locator: ' + xpath)
        return self._element_find(xpath, False, True)

    def _get_radio_button_with_value(self, group_name, value):
        xpath = "xpath=//input[@type='radio' and @name='%s' and (@value='%s' or @id='%s')]" \
                 % (group_name, value, value)
        self._debug('Radio group locator: ' + xpath)
        return self._element_find(xpath, True, True)

    def _get_value_from_radio_buttons(self, elements):
        for element in elements:
            if element.is_selected():
                return element.get_attribute('value')
        return None

    def _input_text_into_text_field(self, locator, text):
        element = self._element_find(locator, True, True)
        element.clear()
        element.send_keys(text)

    def _is_form_element(self, element):
        if element is None:
            return False
        tag = element.tag_name.lower()
        return tag == 'input' or tag == 'select' or tag == 'textarea' or tag == 'button' or tag == 'option'

########NEW FILE########
__FILENAME__ = _javascript
import os
from selenium.common.exceptions import WebDriverException
from keywordgroup import KeywordGroup

class _JavaScriptKeywords(KeywordGroup):

    def __init__(self):
        self._cancel_on_next_confirmation = False

    # Public

    def alert_should_be_present(self, text=''):
        """Verifies an alert is present and dismisses it.

        If `text` is a non-empty string, then it is also verified that the
        message of the alert equals to `text`.

        Will fail if no alert is present. Note that following keywords
        will fail unless the alert is dismissed by this
        keyword or another like `Get Alert Message`.
        """
        alert_text = self.get_alert_message()
        if text and alert_text != text:
            raise AssertionError("Alert text should have been '%s' but was '%s'"
                                  % (text, alert_text))

    def choose_cancel_on_next_confirmation(self):
        """Cancel will be selected the next time `Confirm Action` is used."""
        self._cancel_on_next_confirmation = True

    def choose_ok_on_next_confirmation(self):
        """Undo the effect of using keywords `Choose Cancel On Next Confirmation`. Note
        that Selenium's overridden window.confirm() function will normally automatically
        return true, as if the user had manually clicked OK, so you shouldn't
        need to use this command unless for some reason you need to change
        your mind prior to the next confirmation. After any confirmation, Selenium will resume using the
        default behavior for future confirmations, automatically returning 
        true (OK) unless/until you explicitly use `Choose Cancel On Next Confirmation` for each
        confirmation.
        
        Note that every time a confirmation comes up, you must
        consume it by using a keywords such as `Get Alert Message`, or else
        the following selenium operations will fail.
        """
        self._cancel_on_next_confirmation = False

    def confirm_action(self):
        """Dismisses currently shown confirmation dialog and returns it's message.

        By default, this keyword chooses 'OK' option from the dialog. If
        'Cancel' needs to be chosen, keyword `Choose Cancel On Next
        Confirmation` must be called before the action that causes the
        confirmation dialog to be shown.

        Examples:
        | Click Button | Send | # Shows a confirmation dialog |
        | ${message}= | Confirm Action | # Chooses Ok |
        | Should Be Equal | ${message} | Are your sure? |
        |                |    |              |
        | Choose Cancel On Next Confirmation | | |
        | Click Button | Send | # Shows a confirmation dialog |
        | Confirm Action |    | # Chooses Cancel |
        """
        text = self._close_alert(not self._cancel_on_next_confirmation)
        self._cancel_on_next_confirmation = False
        return text

    def execute_javascript(self, *code):
        """Executes the given JavaScript code.

        `code` may contain multiple lines of code but must contain a 
        return statement (with the value to be returned) at the end.

        `code` may be divided into multiple cells in the test data. In that
        case, the parts are catenated together without adding spaces.

        If `code` is an absolute path to an existing file, the JavaScript
        to execute will be read from that file. Forward slashes work as
        a path separator on all operating systems.

        Note that, by default, the code will be executed in the context of the
        Selenium object itself, so `this` will refer to the Selenium object.
        Use `window` to refer to the window of your application, e.g.
        `window.document.getElementById('foo')`.

        Example:
        | Execute JavaScript | window.my_js_function('arg1', 'arg2') |
        | Execute JavaScript | ${CURDIR}/js_to_execute.js |
        """
        js = self._get_javascript_to_execute(''.join(code))
        self._info("Executing JavaScript:\n%s" % js)
        return self._current_browser().execute_script(js)

    def execute_async_javascript(self, *code):
        """Executes asynchronous JavaScript code.

        `code` may contain multiple lines of code but must contain a 
        return statement (with the value to be returned) at the end.

        `code` may be divided into multiple cells in the test data. In that
        case, the parts are catenated together without adding spaces.

        If `code` is an absolute path to an existing file, the JavaScript
        to execute will be read from that file. Forward slashes work as
        a path separator on all operating systems.

        Note that, by default, the code will be executed in the context of the
        Selenium object itself, so `this` will refer to the Selenium object.
        Use `window` to refer to the window of your application, e.g.
        `window.document.getElementById('foo')`.

        Example:
        | Execute Async JavaScript | window.my_js_function('arg1', 'arg2') |
        | Execute Async JavaScript | ${CURDIR}/js_to_execute.js |
        """
        js = self._get_javascript_to_execute(''.join(code))
        self._info("Executing Asynchronous JavaScript:\n%s" % js)
        return self._current_browser().execute_async_script(js)

    def get_alert_message(self):
        """Returns the text of current JavaScript alert.

        This keyword will fail if no alert is present. Note that
        following keywords will fail unless the alert is
        dismissed by this keyword or another like `Get Alert Message`.
        """
        return self._close_alert()

    # Private

    def _close_alert(self, confirm=False):
        alert = None
        try:
            alert = self._current_browser().switch_to_alert()
            text = ' '.join(alert.text.splitlines()) # collapse new lines chars
            if not confirm: alert.dismiss()
            else: alert.accept()
            return text
        except WebDriverException:
            raise RuntimeError('There were no alerts')

    def _get_javascript_to_execute(self, code):
        codepath = code.replace('/', os.sep)
        if not (os.path.isabs(codepath) and os.path.isfile(codepath)):
            return code
        self._html('Reading JavaScript from file <a href="file://%s">%s</a>.'
                   % (codepath.replace(os.sep, '/'), codepath))
        codefile = open(codepath)
        try:
            return codefile.read().strip()
        finally:
            codefile.close()
########NEW FILE########
__FILENAME__ = _logging
import os
import sys
from robot.variables import GLOBAL_VARIABLES
from robot.api import logger
from keywordgroup import KeywordGroup

class _LoggingKeywords(KeywordGroup):

    # Private

    def _debug(self, message):
        logger.debug(message)

    def _get_log_dir(self):
        logfile = GLOBAL_VARIABLES['${LOG FILE}']
        if logfile != 'NONE':
            return os.path.dirname(logfile)
        return GLOBAL_VARIABLES['${OUTPUTDIR}']

    def _html(self, message):
        logger.info(message, True, False)

    def _info(self, message):
        logger.info(message)

    def _log(self, message, level='INFO'):
        level = level.upper()
        if (level == 'INFO'): self._info(message)
        elif (level == 'DEBUG'): self._debug(message)
        elif (level == 'WARN'): self._warn(message)
        elif (level == 'HTML'): self._html(message)

    def _log_list(self, items, what='item'):
        msg = ['Altogether %d %s%s.' % (len(items), what, ['s',''][len(items)==1])]
        for index, item in enumerate(items):
            msg.append('%d: %s' % (index+1, item))
        self._info('\n'.join(msg))
        return items

    def _warn(self, message):
        logger.warn(message)
########NEW FILE########
__FILENAME__ = _runonfailure
from robot.libraries import BuiltIn
from keywordgroup import KeywordGroup

BUILTIN = BuiltIn.BuiltIn()

class _RunOnFailureKeywords(KeywordGroup):

    def __init__(self):
        self._run_on_failure_keyword = None
        self._running_on_failure_routine = False

    # Public

    def register_keyword_to_run_on_failure(self, keyword):
        """Sets the keyword to execute when a Selenium2Library keyword fails.

        `keyword_name` is the name of a keyword (from any available
        libraries) that  will be executed if a Selenium2Library keyword fails.
        It is not possible to use a keyword that requires arguments.
        Using the value "Nothing" will disable this feature altogether.

        The initial keyword to use is set in `importing`, and the
        keyword that is used by default is `Capture Page Screenshot`.
        Taking a screenshot when something failed is a very useful
        feature, but notice that it can slow down the execution.

        This keyword returns the name of the previously registered
        failure keyword. It can be used to restore the original
        value later.

        Example:
        | Register Keyword To Run On Failure  | Log Source | # Run `Log Source` on failure. |
        | ${previous kw}= | Register Keyword To Run On Failure  | Nothing    | # Disables run-on-failure functionality and stores the previous kw name in a variable. |
        | Register Keyword To Run On Failure  | ${previous kw} | # Restore to the previous keyword. |

        This run-on-failure functionality only works when running tests on Python/Jython 2.4
        or newer and it does not work on IronPython at all.
        """
        old_keyword = self._run_on_failure_keyword
        old_keyword_text = old_keyword if old_keyword is not None else "No keyword"

        new_keyword = keyword if keyword.strip().lower() != "nothing" else None
        new_keyword_text = new_keyword if new_keyword is not None else "No keyword"

        self._run_on_failure_keyword = new_keyword
        self._info('%s will be run on failure.' % new_keyword_text)

        return old_keyword_text
    
    # Private

    def _run_on_failure(self):
        if self._run_on_failure_keyword is None:
            return
        if self._running_on_failure_routine:
            return
        self._running_on_failure_routine = True
        try:
            BUILTIN.run_keyword(self._run_on_failure_keyword)
        except Exception, err:
            self._run_on_failure_error(err)
        finally:
            self._running_on_failure_routine = False

    def _run_on_failure_error(self, err):
        err = "Keyword '%s' could not be run on failure: %s" % (self._run_on_failure_keyword, err)
        if hasattr(self, '_warn'):
            self._warn(err)
            return
        raise Exception(err)

########NEW FILE########
__FILENAME__ = _screenshot
import os
import robot
from keywordgroup import KeywordGroup

class _ScreenshotKeywords(KeywordGroup):

    def __init__(self):
        self._screenshot_index = 0

    # Public

    def capture_page_screenshot(self, filename=None):
        """Takes a screenshot of the current page and embeds it into the log.

        `filename` argument specifies the name of the file to write the
        screenshot into. If no `filename` is given, the screenshot is saved into file
        `selenium-screenshot-<counter>.png` under the directory where
        the Robot Framework log file is written into. The `filename` is
        also considered relative to the same directory, if it is not
        given in absolute format.

        `css` can be used to modify how the screenshot is taken. By default
        the bakground color is changed to avoid possible problems with
        background leaking when the page layout is somehow broken.
        """
        path, link = self._get_screenshot_paths(filename)

        if hasattr(self._current_browser(), 'get_screenshot_as_file'):
          self._current_browser().get_screenshot_as_file(path)
        else:
          self._current_browser().save_screenshot(path)

        # Image is shown on its own row and thus prev row is closed on purpose
        self._html('</td></tr><tr><td colspan="3"><a href="%s">'
                   '<img src="%s" width="800px"></a>' % (link, link))

    # Private

    def _get_screenshot_paths(self, filename):
        if not filename:
            self._screenshot_index += 1
            filename = 'selenium-screenshot-%d.png' % self._screenshot_index
        else:
            filename = filename.replace('/', os.sep)
        logdir = self._get_log_dir()
        path = os.path.join(logdir, filename)
        link = robot.utils.get_link_path(path, logdir)
        return path, link

########NEW FILE########
__FILENAME__ = _selectelement
from selenium.webdriver.support.ui import Select
from keywordgroup import KeywordGroup

class _SelectElementKeywords(KeywordGroup):

    # Public

    def get_list_items(self, locator):
        """Returns the values in the select list identified by `locator`.

        Select list keywords work on both lists and combo boxes. Key attributes for
        select lists are `id` and `name`. See `introduction` for details about
        locating elements.
        """
        select, options = self._get_select_list_options(locator)
        return self._get_labels_for_options(options)

    def get_selected_list_label(self, locator):
        """Returns the visible label of the selected element from the select list identified by `locator`.

        Select list keywords work on both lists and combo boxes. Key attributes for
        select lists are `id` and `name`. See `introduction` for details about
        locating elements.
        """
        select = self._get_select_list(locator)
        return select.first_selected_option.text

    def get_selected_list_labels(self, locator):
        """Returns the visible labels of selected elements (as a list) from the select list identified by `locator`.

        Fails if there is no selection.

        Select list keywords work on both lists and combo boxes. Key attributes for
        select lists are `id` and `name`. See `introduction` for details about
        locating elements.
        """
        select, options = self._get_select_list_options_selected(locator)
        if len(options) == 0:
            raise ValueError("Select list with locator '%s' does not have any selected values")
        return self._get_labels_for_options(options)

    def get_selected_list_value(self, locator):
        """Returns the value of the selected element from the select list identified by `locator`.

        Return value is read from `value` attribute of the selected element.

        Select list keywords work on both lists and combo boxes. Key attributes for
        select lists are `id` and `name`. See `introduction` for details about
        locating elements.
        """
        select = self._get_select_list(locator)
        return select.first_selected_option.get_attribute('value')

    def get_selected_list_values(self, locator):
        """Returns the values of selected elements (as a list) from the select list identified by `locator`.

        Fails if there is no selection.

        Select list keywords work on both lists and combo boxes. Key attributes for
        select lists are `id` and `name`. See `introduction` for details about
        locating elements.
        """
        select, options = self._get_select_list_options_selected(locator)
        if len(options) == 0:
            raise ValueError("Select list with locator '%s' does not have any selected values")
        return self._get_values_for_options(options)

    def list_selection_should_be(self, locator, *items):
        """Verifies the selection of select list identified by `locator` is exactly `*items`.

        If you want to test that no option is selected, simply give no `items`.

        Select list keywords work on both lists and combo boxes. Key attributes for
        select lists are `id` and `name`. See `introduction` for details about
        locating elements.
        """
        items_str = items and "option(s) [ %s ]" % " | ".join(items) or "no options"
        self._info("Verifying list '%s' has %s selected." % (locator, items_str))
        items = list(items)
        self.page_should_contain_list(locator)
        select, options = self._get_select_list_options_selected(locator)
        if not items and len(options) == 0:
            return
        selected_values = self._get_values_for_options(options)
        selected_labels = self._get_labels_for_options(options)
        err = "List '%s' should have had selection [ %s ] but it was [ %s ]" \
            % (locator, ' | '.join(items), ' | '.join(selected_labels))
        for item in items:
            if item not in selected_values + selected_labels:
                raise AssertionError(err)
        for selected_value, selected_label in zip(selected_values, selected_labels):
            if selected_value not in items and selected_label not in items:
                raise AssertionError(err)

    def list_should_have_no_selections(self, locator):
        """Verifies select list identified by `locator` has no selections.

        Select list keywords work on both lists and combo boxes. Key attributes for
        select lists are `id` and `name`. See `introduction` for details about
        locating elements.
        """
        self._info("Verifying list '%s' has no selection." % locator)
        select, options = self._get_select_list_options_selected(locator)
        if options:
            selected_labels = self._get_labels_for_options(options)
            items_str = " | ".join(selected_labels)
            raise AssertionError("List '%s' should have had no selection "
                                 "(selection was [ %s ])" % (locator, items_str))

    def page_should_contain_list(self, locator, message='', loglevel='INFO'):
        """Verifies select list identified by `locator` is found from current page.

        See `Page Should Contain Element` for explanation about `message` and
        `loglevel` arguments.

        Key attributes for lists are `id` and `name`. See `introduction` for
        details about locating elements.
        """
        self._page_should_contain_element(locator, 'list', message, loglevel)

    def page_should_not_contain_list(self, locator, message='', loglevel='INFO'):
        """Verifies select list identified by `locator` is not found from current page.

        See `Page Should Contain Element` for explanation about `message` and
        `loglevel` arguments.

        Key attributes for lists are `id` and `name`. See `introduction` for
        details about locating elements.
        """
        self._page_should_not_contain_element(locator, 'list', message, loglevel)

    def select_all_from_list(self, locator):
        """Selects all values from multi-select list identified by `id`.

        Key attributes for lists are `id` and `name`. See `introduction` for
        details about locating elements.
        """
        self._info("Selecting all options from list '%s'." % locator)

        select = self._get_select_list(locator)
        if not select.is_multiple:
            raise RuntimeError("Keyword 'Select all from list' works only for multiselect lists.")

        for i in range(len(select.options)):
            select.select_by_index(i)

    def select_from_list(self, locator, *items):
        """Selects `*items` from list identified by `locator`

        If more than one value is given for a single-selection list, the last
        value will be selected. If the target list is a multi-selection list,
        and `*items` is an empty list, all values of the list will be selected.

        *items try to select by value then by label.

        It's faster to use 'by index/value/label' functions.

        An exception is raised for a single-selection list if the last
        value does not exist in the list and a warning for all other non-
        existing items. For a multi-selection list, an exception is raised
        for any and all non-existing values.

        Select list keywords work on both lists and combo boxes. Key attributes for
        select lists are `id` and `name`. See `introduction` for details about
        locating elements.
        """
        non_existing_items = []

        items_str = items and "option(s) '%s'" % ", ".join(items) or "all options"
        self._info("Selecting %s from list '%s'." % (items_str, locator))

        select = self._get_select_list(locator)

        if not items:
            for i in range(len(select.options)):
                select.select_by_index(i)
            return

        for item in items:
            try:
                select.select_by_value(item)
            except:
                try:
                    select.select_by_visible_text(item)
                except:
                    non_existing_items = non_existing_items + [item]
                    continue

        if any(non_existing_items):
            if select.is_multiple:
                raise ValueError("Options '%s' not in list '%s'." % (", ".join(non_existing_items), locator))
            else:
                if any (non_existing_items[:-1]):
                    items_str = non_existing_items[:-1] and "Option(s) '%s'" % ", ".join(non_existing_items[:-1])
                    self._warn("%s not found within list '%s'." % (items_str, locator))
                if items and items[-1] in non_existing_items:
                    raise ValueError("Option '%s' not in list '%s'." % (items[-1], locator))

    def select_from_list_by_index(self, locator, *indexes):
        """Selects `*indexes` from list identified by `locator`

        Select list keywords work on both lists and combo boxes. Key attributes for
        select lists are `id` and `name`. See `introduction` for details about
        locating elements.
        """
        if not indexes:
            raise ValueError("No index given.")
        items_str = "index(es) '%s'" % ", ".join(indexes)
        self._info("Selecting %s from list '%s'." % (items_str, locator))

        select = self._get_select_list(locator)
        for index in indexes:
            select.select_by_index(int(index))

    def select_from_list_by_value(self, locator, *values):
        """Selects `*values` from list identified by `locator`

        Select list keywords work on both lists and combo boxes. Key attributes for
        select lists are `id` and `name`. See `introduction` for details about
        locating elements.
        """
        if not values:
            raise ValueError("No value given.")
        items_str = "value(s) '%s'" % ", ".join(values)
        self._info("Selecting %s from list '%s'." % (items_str, locator))

        select = self._get_select_list(locator)
        for value in values:
            select.select_by_value(value)

    def select_from_list_by_label(self, locator, *labels):
        """Selects `*labels` from list identified by `locator`

        Select list keywords work on both lists and combo boxes. Key attributes for
        select lists are `id` and `name`. See `introduction` for details about
        locating elements.
        """
        if not labels:
            raise ValueError("No value given.")
        items_str = "label(s) '%s'" % ", ".join(labels)
        self._info("Selecting %s from list '%s'." % (items_str, locator))

        select = self._get_select_list(locator)
        for label in labels:
            select.select_by_visible_text(label)

    def unselect_from_list(self, locator, *items):
        """Unselects given values from select list identified by locator.

        As a special case, giving empty list as `*items` will remove all
        selections.

        *items try to unselect by value AND by label.

        It's faster to use 'by index/value/label' functions.

        Select list keywords work on both lists and combo boxes. Key attributes for
        select lists are `id` and `name`. See `introduction` for details about
        locating elements.
        """
        items_str = items and "option(s) '%s'" % ", ".join(items) or "all options"
        self._info("Unselecting %s from list '%s'." % (items_str, locator))

        select = self._get_select_list(locator)
        if not select.is_multiple:
            raise RuntimeError("Keyword 'Unselect from list' works only for multiselect lists.")

        if not items:
            select.deselect_all()
            return

        select, options = self._get_select_list_options(select)
        for item in items:
            select.deselect_by_value(item)
            select.deselect_by_visible_text(item)

    def unselect_from_list_by_index(self, locator, *indexes):
        """Unselects `*indexes` from list identified by `locator`

        Select list keywords work on both lists and combo boxes. Key attributes for
        select lists are `id` and `name`. See `introduction` for details about
        locating elements.
        """
        if not indexes:
            raise ValueError("No index given.")

        items_str = "index(es) '%s'" % ", ".join(indexes)
        self._info("Unselecting %s from list '%s'." % (items_str, locator))

        select = self._get_select_list(locator)
        if not select.is_multiple:
            raise RuntimeError("Keyword 'Unselect from list' works only for multiselect lists.")

        for index in indexes:
            select.deselect_by_index(int(index))

    def unselect_from_list_by_value(self, locator, *values):
        """Unselects `*values` from list identified by `locator`

        Select list keywords work on both lists and combo boxes. Key attributes for
        select lists are `id` and `name`. See `introduction` for details about
        locating elements.
        """
        if not values:
            raise ValueError("No value given.")
        items_str = "value(s) '%s'" % ", ".join(values)
        self._info("Unselecting %s from list '%s'." % (items_str, locator))

        select = self._get_select_list(locator)
        if not select.is_multiple:
            raise RuntimeError("Keyword 'Unselect from list' works only for multiselect lists.")

        for value in values:
            select.deselect_by_value(value)

    def unselect_from_list_by_label(self, locator, *labels):
        """Unselects `*labels` from list identified by `locator`

        Select list keywords work on both lists and combo boxes. Key attributes for
        select lists are `id` and `name`. See `introduction` for details about
        locating elements.
        """
        if not labels:
            raise ValueError("No value given.")
        items_str = "label(s) '%s'" % ", ".join(labels)
        self._info("Unselecting %s from list '%s'." % (items_str, locator))

        select = self._get_select_list(locator)
        if not select.is_multiple:
            raise RuntimeError("Keyword 'Unselect from list' works only for multiselect lists.")

        for label in labels:
            select.deselect_by_visible_text(label)

    # Private

    def _get_labels_for_options(self, options):
        labels = []
        for option in options:
            labels.append(option.text)
        return labels

    def _get_select_list(self, locator):
        el = self._element_find(locator, True, True, 'select')
        return Select(el)

    def _get_select_list_options(self, select_list_or_locator):
        if isinstance(select_list_or_locator, Select):
            select = select_list_or_locator
        else:
            select = self._get_select_list(select_list_or_locator)
        return select, select.options

    def _get_select_list_options_selected(self, locator):
        select = self._get_select_list(locator)
        # TODO: Handle possible exception thrown by all_selected_options
        return select, select.all_selected_options

    def _get_values_for_options(self, options):
        values = []
        for option in options:
             values.append(option.get_attribute('value'))
        return values

    def _is_multiselect_list(self, select):
        multiple_value = select.get_attribute('multiple')
        if multiple_value is not None and (multiple_value == 'true' or multiple_value == 'multiple'):
            return True
        return False

    def _unselect_all_options_from_multi_select_list(self, select):
        self._current_browser().execute_script("arguments[0].selectedIndex = -1;", select)

    def _unselect_option_from_multi_select_list(self, select, options, index):
        if options[index].is_selected():
            options[index].click()

########NEW FILE########
__FILENAME__ = _tableelement
import os
import sys
from robot.variables import GLOBAL_VARIABLES
from robot.api import logger
from Selenium2Library.locators import TableElementFinder
from keywordgroup import KeywordGroup

class _TableElementKeywords(KeywordGroup):

    def __init__(self):
        self._table_element_finder = TableElementFinder()

    # Public

    def get_table_cell(self, table_locator, row, column, loglevel='INFO'):
        """Returns the content from a table cell.

        Row and column number start from 1. Header and footer rows are
        included in the count. This means that also cell content from
        header or footer rows can be obtained with this keyword. To
        understand how tables are identified, please take a look at
        the `introduction`.
        """
        row = int(row)
        row_index = row - 1
        column = int(column)
        column_index = column - 1
        table = self._table_element_finder.find(self._current_browser(), table_locator)
        if table is not None:
            rows = table.find_elements_by_xpath("./thead/tr")
            if row_index >= len(rows): rows.extend(table.find_elements_by_xpath("./tbody/tr"))
            if row_index >= len(rows): rows.extend(table.find_elements_by_xpath("./tfoot/tr"))
            if row_index < len(rows):
                columns = rows[row_index].find_elements_by_tag_name('th')
                if column_index >= len(columns): columns.extend(rows[row_index].find_elements_by_tag_name('td'))
                if column_index < len(columns):
                    return columns[column_index].text
        self.log_source(loglevel)
        raise AssertionError("Cell in table %s in row #%s and column #%s could not be found."
            % (table_locator, str(row), str(column)))

    def table_cell_should_contain(self, table_locator, row, column, expected, loglevel='INFO'):
        """Verifies that a certain cell in a table contains `expected`.

        Row and column number start from 1. This keyword passes if the
        specified cell contains the given content. If you want to test
        that the cell content matches exactly, or that it e.g. starts
        with some text, use `Get Table Cell` keyword in combination
        with built-in keywords such as `Should Be Equal` or `Should
        Start With`.

        To understand how tables are identified, please take a look at
        the `introduction`.
        """
        message = ("Cell in table '%s' in row #%s and column #%s "
                   "should have contained text '%s'."
                   % (table_locator, row, column, expected))
        try:
            content = self.get_table_cell(table_locator, row, column, loglevel='NONE')
        except AssertionError, err:
            self._info(err)
            self.log_source(loglevel)
            raise AssertionError(message)
        self._info("Cell contains %s." % (content))
        if expected not in content:
            self.log_source(loglevel)
            raise AssertionError(message)

    def table_column_should_contain(self, table_locator, col, expected, loglevel='INFO'):
        """Verifies that a specific column contains `expected`.

        The first leftmost column is column number 1. If the table
        contains cells that span multiple columns, those merged cells
        count as a single column. For example both tests below work,
        if in one row columns A and B are merged with colspan="2", and
        the logical third column contains "C".

        Example:
        | Table Column Should Contain | tableId | 3 | C |
        | Table Column Should Contain | tableId | 2 | C |

        To understand how tables are identified, please take a look at
        the `introduction`.

        See `Page Should Contain Element` for explanation about
        `loglevel` argument.
        """
        element = self._table_element_finder.find_by_col(self._current_browser(), table_locator, col, expected)
        if element is None:
            self.log_source(loglevel)
            raise AssertionError("Column #%s in table identified by '%s' "
                   "should have contained text '%s'."
                   % (col, table_locator, expected))

    def table_footer_should_contain(self, table_locator, expected, loglevel='INFO'):
        """Verifies that the table footer contains `expected`.

        With table footer can be described as any <td>-element that is
        child of a <tfoot>-element.  To understand how tables are
        identified, please take a look at the `introduction`.

        See `Page Should Contain Element` for explanation about
        `loglevel` argument.
        """
        element = self._table_element_finder.find_by_footer(self._current_browser(), table_locator, expected)
        if element is None:
            self.log_source(loglevel)
            raise AssertionError("Footer in table identified by '%s' should have contained "
                   "text '%s'." % (table_locator, expected))

    def table_header_should_contain(self, table_locator, expected, loglevel='INFO'):
        """Verifies that the table header, i.e. any <th>...</th> element, contains `expected`.

        To understand how tables are identified, please take a look at
        the `introduction`.

        See `Page Should Contain Element` for explanation about
        `loglevel` argument.
        """
        element = self._table_element_finder.find_by_header(self._current_browser(), table_locator, expected)
        if element is None:
            self.log_source(loglevel)
            raise AssertionError("Header in table identified by '%s' should have contained "
               "text '%s'." % (table_locator, expected))

    def table_row_should_contain(self, table_locator, row, expected, loglevel='INFO'):
        """Verifies that a specific table row contains `expected`.

        The uppermost row is row number 1. For tables that are
        structured with thead, tbody and tfoot, only the tbody section
        is searched. Please use `Table Header Should Contain` or
        `Table Footer Should Contain` for tests against the header or
        footer content.

        If the table contains cells that span multiple rows, a match
        only occurs for the uppermost row of those merged cells. To
        understand how tables are identified, please take a look at
        the `introduction`.

        See `Page Should Contain Element` for explanation about `loglevel` argument.
        """
        element = self._table_element_finder.find_by_row(self._current_browser(), table_locator, row, expected)
        if element is None:
            self.log_source(loglevel)
            raise AssertionError("Row #%s in table identified by '%s' should have contained "
                   "text '%s'." % (row, table_locator, expected))

    def table_should_contain(self, table_locator, expected, loglevel='INFO'):
        """Verifies that `expected` can be found somewhere in the table.

        To understand how tables are identified, please take a look at
        the `introduction`.

        See `Page Should Contain Element` for explanation about
        `loglevel` argument.
        """
        element = self._table_element_finder.find_by_content(self._current_browser(), table_locator, expected)
        if element is None:
            self.log_source(loglevel)
            raise AssertionError("Table identified by '%s' should have contained text '%s'." \
                % (table_locator, expected))
########NEW FILE########
__FILENAME__ = _waiting
import time
import robot
from keywordgroup import KeywordGroup

class _WaitingKeywords(KeywordGroup):

    # Public

    def wait_for_condition(self, condition, timeout=None, error=None):
        """Waits until the given `condition` is true or `timeout` expires.

        `code` may contain multiple lines of code but must contain a 
        return statement (with the value to be returned) at the end

        The `condition` can be arbitrary JavaScript expression but must contain a 
        return statement (with the value to be returned) at the end.
        See `Execute JavaScript` for information about accessing the
        actual contents of the window through JavaScript.

        `error` can be used to override the default error message.

        See `introduction` for more information about `timeout` and its
        default value.

        See also `Wait Until Page Contains`, `Wait Until Page Contains
        Element`, `Wait Until Element Is Visible` and BuiltIn keyword
        `Wait Until Keyword Succeeds`.
        """
        if not error:
            error = "Condition '%s' did not become true in <TIMEOUT>" % condition
        self._wait_until(timeout, error,
                         lambda: self._current_browser().execute_script(condition) == True)

    def wait_until_page_contains(self, text, timeout=None, error=None):
        """Waits until `text` appears on current page.

        Fails if `timeout` expires before the text appears. See
        `introduction` for more information about `timeout` and its
        default value.

        `error` can be used to override the default error message.

        See also `Wait Until Page Contains Element`, `Wait For Condition`,
        `Wait Until Element Is Visible` and BuiltIn keyword `Wait Until
        Keyword Succeeds`.
        """
        if not error:
            error = "Text '%s' did not appear in <TIMEOUT>" % text
        self._wait_until(timeout, error, self._is_text_present, text)

    def wait_until_page_contains_element(self, locator, timeout=None, error=None):
        """Waits until element specified with `locator` appears on current page.

        Fails if `timeout` expires before the element appears. See
        `introduction` for more information about `timeout` and its
        default value.

        `error` can be used to override the default error message.

        See also `Wait Until Page Contains`, `Wait For Condition`,
        `Wait Until Element Is Visible` and BuiltIn keyword `Wait Until
        Keyword Succeeds`.
        """
        if not error:
            error = "Element '%s' did not appear in <TIMEOUT>" % locator
        self._wait_until(timeout, error, self._is_element_present, locator)

    def wait_until_element_is_visible(self, locator, timeout=None, error=None):
        """Waits until element specified with `locator` is visible.

        Fails if `timeout` expires before the element is visible. See
        `introduction` for more information about `timeout` and its
        default value.

        `error` can be used to override the default error message.

        See also `Wait Until Page Contains`, `Wait Until Page Contains 
        Element`, `Wait For Condition` and BuiltIn keyword `Wait Until Keyword
        Succeeds`.
        """
        def check_visibility():
            visible = self._is_visible(locator)
            if visible:
                return
            elif visible is None:
                return error or "Element locator '%s' did not match any elements after %s" % (locator, self._format_timeout(timeout))
            else:
                return error or "Element '%s' was not visible in %s" % (locator, self._format_timeout(timeout))
        self._wait_until_no_error(timeout, check_visibility)

    # Private

    def _wait_until(self, timeout, error, function, *args):
        error = error.replace('<TIMEOUT>', self._format_timeout(timeout))
        def wait_func():
            return None if function(*args) else error
        self._wait_until_no_error(timeout, wait_func)

    def _wait_until_no_error(self, timeout, wait_func, *args):
        timeout = robot.utils.timestr_to_secs(timeout) if timeout is not None else self._timeout_in_secs
        maxtime = time.time() + timeout
        while True:
            timeout_error = wait_func(*args)
            if not timeout_error: return
            if time.time() > maxtime:
                raise AssertionError(timeout_error)
            time.sleep(0.2)

    def _format_timeout(self, timeout):
        timeout = robot.utils.timestr_to_secs(timeout) if timeout is not None else self._timeout_in_secs
        return robot.utils.secs_to_timestr(timeout)

########NEW FILE########
__FILENAME__ = elementfinder
from Selenium2Library import utils
from robot.api import logger

class ElementFinder(object):

    def __init__(self):
        self._strategies = {
            'identifier': self._find_by_identifier,
            'id': self._find_by_id,
            'name': self._find_by_name,
            'xpath': self._find_by_xpath,
            'dom': self._find_by_dom,
            'link': self._find_by_link_text,
            'css': self._find_by_css_selector,
            'jquery': self._find_by_sizzle_selector,
            'sizzle': self._find_by_sizzle_selector,
            'tag': self._find_by_tag_name,
            None: self._find_by_default
        }

    def find(self, browser, locator, tag=None):
        assert browser is not None
        assert locator is not None and len(locator) > 0

        (prefix, criteria) = self._parse_locator(locator)
        strategy = self._strategies.get(prefix)
        if strategy is None:
            raise ValueError("Element locator with prefix '" + prefix + "' is not supported")
        (tag, constraints) = self._get_tag_and_constraints(tag)
        return strategy(browser, criteria, tag, constraints)

    # Strategy routines, private

    def _find_by_identifier(self, browser, criteria, tag, constraints):
        elements = self._normalize_result(browser.find_elements_by_id(criteria))
        elements.extend(self._normalize_result(browser.find_elements_by_name(criteria)))
        return self._filter_elements(elements, tag, constraints)

    def _find_by_id(self, browser, criteria, tag, constraints):
        return self._filter_elements(
            browser.find_elements_by_id(criteria),
            tag, constraints)

    def _find_by_name(self, browser, criteria, tag, constraints):
        return self._filter_elements(
            browser.find_elements_by_name(criteria),
            tag, constraints)

    def _find_by_xpath(self, browser, criteria, tag, constraints):
        return self._filter_elements(
            browser.find_elements_by_xpath(criteria),
            tag, constraints)

    def _find_by_dom(self, browser, criteria, tag, constraints):
        result = browser.execute_script("return %s;" % criteria)
        if result is None:
            return []
        if not isinstance(result, list):
            result = [result]
        return self._filter_elements(result, tag, constraints)

    def _find_by_sizzle_selector(self, browser, criteria, tag, constraints):
        js = "return jQuery('%s').get();" % criteria.replace("'", "\\'")
        return self._filter_elements(
            browser.execute_script(js),
            tag, constraints)

    def _find_by_link_text(self, browser, criteria, tag, constraints):
        return self._filter_elements(
            browser.find_elements_by_link_text(criteria),
            tag, constraints)

    def _find_by_css_selector(self, browser, criteria, tag, constraints):
        return self._filter_elements(
            browser.find_elements_by_css_selector(criteria),
            tag, constraints)

    def _find_by_tag_name(self, browser, criteria, tag, constraints):
        return self._filter_elements(
            browser.find_elements_by_tag_name(criteria),
            tag, constraints)

    def _find_by_default(self, browser, criteria, tag, constraints):
        if criteria.startswith('//'):
            return self._find_by_xpath(browser, criteria, tag, constraints)
        return self._find_by_key_attrs(browser, criteria, tag, constraints)

    def _find_by_key_attrs(self, browser, criteria, tag, constraints):
        key_attrs = self._key_attrs.get(None)
        if tag is not None:
            key_attrs = self._key_attrs.get(tag, key_attrs)

        xpath_criteria = utils.escape_xpath_value(criteria)
        xpath_tag = tag if tag is not None else '*'
        xpath_constraints = ["@%s='%s'" % (name, constraints[name]) for name in constraints]
        xpath_searchers = ["%s=%s" % (attr, xpath_criteria) for attr in key_attrs]
        xpath_searchers.extend(
            self._get_attrs_with_url(key_attrs, criteria, browser))
        xpath = "//%s[%s(%s)]" % (
            xpath_tag,
            ' and '.join(xpath_constraints) + ' and ' if len(xpath_constraints) > 0 else '',
            ' or '.join(xpath_searchers))

        return self._normalize_result(browser.find_elements_by_xpath(xpath))

    # Private

    _key_attrs = {
        None: ['@id', '@name'],
        'a': ['@id', '@name', '@href', 'normalize-space(descendant-or-self::text())'],
        'img': ['@id', '@name', '@src', '@alt'],
        'input': ['@id', '@name', '@value', '@src'],
        'button': ['@id', '@name', '@value', 'normalize-space(descendant-or-self::text())']
    }

    def _get_tag_and_constraints(self, tag):
        if tag is None: return None, {}

        tag = tag.lower()
        constraints = {}
        if tag == 'link':
            tag = 'a'
        elif tag == 'image':
            tag = 'img'
        elif tag == 'list':
            tag = 'select'
        elif tag == 'radio button':
            tag = 'input'
            constraints['type'] = 'radio'
        elif tag == 'checkbox':
            tag = 'input'
            constraints['type'] = 'checkbox'
        elif tag == 'text field':
            tag = 'input'
            constraints['type'] = 'text'
        elif tag == 'file upload':
            tag = 'input'
            constraints['type'] = 'file'
        elif tag == 'text area':
            tag = 'textarea'
        return tag, constraints

    def _element_matches(self, element, tag, constraints):
        if not element.tag_name.lower() == tag:
            return False
        for name in constraints:
            if not element.get_attribute(name) == constraints[name]:
                return False
        return True

    def _filter_elements(self, elements, tag, constraints):
        elements = self._normalize_result(elements)
        if tag is None: return elements
        return filter(
            lambda element: self._element_matches(element, tag, constraints),
            elements)

    def _get_attrs_with_url(self, key_attrs, criteria, browser):
        attrs = []
        url = None
        xpath_url = None
        for attr in ['@src', '@href']:
            if attr in key_attrs:
                if url is None or xpath_url is None:
                    url = self._get_base_url(browser) + "/" + criteria
                    xpath_url = utils.escape_xpath_value(url)
                attrs.append("%s=%s" % (attr, xpath_url))
        return attrs

    def _get_base_url(self, browser):
        url = browser.get_current_url()
        if '/' in url:
            url = '/'.join(url.split('/')[:-1])
        return url

    def _parse_locator(self, locator):
        prefix = None
        criteria = locator
        if not locator.startswith('//'):
            locator_parts = locator.partition('=')
            if len(locator_parts[1]) > 0:
                prefix = locator_parts[0].strip().lower()
                criteria = locator_parts[2].strip()
        return (prefix, criteria)

    def _normalize_result(self, elements):
        if not isinstance(elements, list):
            logger.debug("WebDriver find returned %s" % elements)
            return []
        return elements

########NEW FILE########
__FILENAME__ = tableelementfinder
from selenium.common.exceptions import NoSuchElementException
from Selenium2Library import utils
from elementfinder import ElementFinder

class TableElementFinder(object):

    def __init__(self, element_finder=None):
        if not element_finder:
            element_finder = ElementFinder()
        self._element_finder = element_finder

        self._locator_suffixes = {
            ('css', 'default'): [''],
            ('css', 'content'): [''],
            ('css', 'header'): [' th'],
            ('css', 'footer'): [' tfoot td'],
            ('css', 'row'): [' tr:nth-child(%s)'],
            ('css', 'col'): [' tr td:nth-child(%s)', ' tr th:nth-child(%s)'],

            ('jquery', 'default'): [''],
            ('jquery', 'content'): [''],
            ('jquery', 'header'): [' th'],
            ('jquery', 'footer'): [' tfoot td'],
            ('jquery', 'row'): [' tr:nth-child(%s)'],
            ('jquery', 'col'): [' tr td:nth-child(%s)', ' tr th:nth-child(%s)'],

            ('sizzle', 'default'): [''],
            ('sizzle', 'content'): [''],
            ('sizzle', 'header'): [' th'],
            ('sizzle', 'footer'): [' tfoot td'],
            ('sizzle', 'row'): [' tr:nth-child(%s)'],
            ('sizzle', 'col'): [' tr td:nth-child(%s)', ' tr th:nth-child(%s)'],

            ('xpath', 'default'): [''],
            ('xpath', 'content'): ['//*'],
            ('xpath', 'header'): ['//th'],
            ('xpath', 'footer'): ['//tfoot//td'],
            ('xpath', 'row'): ['//tr[%s]//*'],
            ('xpath', 'col'): ['//tr//*[self::td or self::th][%s]']
        };

    def find(self, browser, table_locator):
        locators = self._parse_table_locator(table_locator, 'default')
        return self._search_in_locators(browser, locators, None)

    def find_by_content(self, browser, table_locator, content):
        locators = self._parse_table_locator(table_locator, 'content')
        return self._search_in_locators(browser, locators, content)

    def find_by_header(self, browser, table_locator, content):
        locators = self._parse_table_locator(table_locator, 'header')
        return self._search_in_locators(browser, locators, content)

    def find_by_footer(self, browser, table_locator, content):
        locators = self._parse_table_locator(table_locator, 'footer')
        return self._search_in_locators(browser, locators, content)

    def find_by_row(self, browser, table_locator, col, content):
        locators = self._parse_table_locator(table_locator, 'row')
        locators = [locator % str(col) for locator in locators]
        return self._search_in_locators(browser, locators, content)

    def find_by_col(self, browser, table_locator, col, content):
        locators = self._parse_table_locator(table_locator, 'col')
        locators = [locator % str(col) for locator in locators]
        return self._search_in_locators(browser, locators, content)

    def _parse_table_locator(self, table_locator, location_method):
        if table_locator.startswith('xpath='):
            table_locator_type = 'xpath'
        elif table_locator.startswith('jquery=') or table_locator.startswith('sizzle='):
            table_locator_type = 'sizzle'
        else:
            if not table_locator.startswith('css='):
                table_locator = "css=table#%s" % table_locator
            table_locator_type = 'css'

        locator_suffixes = self._locator_suffixes[(table_locator_type, location_method)]

        return map(
            lambda locator_suffix: table_locator + locator_suffix,
            locator_suffixes)

    def _search_in_locators(self, browser, locators, content):
        for locator in locators:
            elements = self._element_finder.find(browser, locator)
            for element in elements:
                if content is None: return element
                element_text = element.text
                if element_text and content in element_text:
                    return element
        return None

########NEW FILE########
__FILENAME__ = windowmanager
from types import *
from robot import utils
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.common.exceptions import NoSuchWindowException

class WindowManager(object):

    def __init__(self):
        self._strategies = {
            'title': self._select_by_title,
            'name': self._select_by_name,
            'url': self._select_by_url,
            None: self._select_by_default
        }

    def get_window_ids(self, browser):
        return [ window_info[1] for window_info in self._get_window_infos(browser) ]

    def get_window_names(self, browser):
        return [ window_info[2] for window_info in self._get_window_infos(browser) ]

    def get_window_titles(self, browser):
        return [ window_info[3] for window_info in self._get_window_infos(browser) ]

    def select(self, browser, locator):
        assert browser is not None

        (prefix, criteria) = self._parse_locator(locator)
        strategy = self._strategies.get(prefix)
        if strategy is None:
            raise ValueError("Window locator with prefix '" + prefix + "' is not supported")
        return strategy(browser, criteria)

    # Strategy routines, private

    def _select_by_title(self, browser, criteria):
        self._select_matching(
            browser,
            lambda window_info: window_info[3].strip().lower() == criteria.lower(),
            "Unable to locate window with title '" + criteria + "'")

    def _select_by_name(self, browser, criteria):
        self._select_matching(
            browser,
            lambda window_info: window_info[2].strip().lower() == criteria.lower(),
            "Unable to locate window with name '" + criteria + "'")

    def _select_by_url(self, browser, criteria):
        self._select_matching(
            browser,
            lambda window_info: window_info[4].strip().lower() == criteria.lower(),
            "Unable to locate window with URL '" + criteria + "'")

    def _select_by_default(self, browser, criteria):
        if criteria is None or len(criteria) == 0 or criteria.lower() == "null":
            browser.switch_to_window('')
            return

        try:
            self._select_by_name(browser, criteria)
            return
        except ValueError: pass

        try:
            self._select_by_title(browser, criteria)
            return
        except ValueError: pass

        raise ValueError("Unable to locate window with name or title '" + criteria + "'")

    # Private

    def _parse_locator(self, locator):
        prefix = None
        criteria = locator
        if locator is not None and len(locator) > 0:
            locator_parts = locator.partition('=')        
            if len(locator_parts[1]) > 0:
                prefix = locator_parts[0].strip().lower()
                criteria = locator_parts[2].strip()
        if prefix is None or prefix == 'name':
            if criteria is None or criteria.lower() == 'main':
                criteria = ''
        return (prefix, criteria)

    def _get_window_infos(self, browser):
        window_infos = []
        starting_handle = browser.get_current_window_handle()
        try:
            for handle in browser.get_window_handles():
                browser.switch_to_window(handle)
                window_infos.append(browser.get_current_window_info())
        finally:
            browser.switch_to_window(starting_handle)
        return window_infos

    def _select_matching(self, browser, matcher, error):
        starting_handle = browser.get_current_window_handle()
        for handle in browser.get_window_handles():
            browser.switch_to_window(handle)
            if matcher(browser.get_current_window_info()):
                return
        browser.switch_to_window(starting_handle)
        raise ValueError(error)

########NEW FILE########
__FILENAME__ = browsercache
from robot.utils import ConnectionCache

class BrowserCache(ConnectionCache):

    def __init__(self):
        ConnectionCache.__init__(self, no_current_msg='No current browser')
        self._closed = set()

    @property
    def browsers(self):
        return self._connections

    def get_open_browsers(self):
        open_browsers = []
        for browser in self._connections:
            if browser not in self._closed:
                open_browsers.append(browser)
        return open_browsers
    
    def close(self):
        if self.current:
            browser = self.current
            browser.quit()
            self.current = self._no_current
            self._closed.add(browser)

    def close_all(self):
        for browser in self._connections:
            if browser not in self._closed:
                browser.quit()
        self.empty_cache()
        return self.current

########NEW FILE########
__FILENAME__ = version
VERSION = '1.5.0'

########NEW FILE########
__FILENAME__ = webdrivermonkeypatches
import time
from robot import utils
from selenium.webdriver.remote.webdriver import WebDriver as RemoteWebDriver
from locators import WindowManager

class WebDriverMonkeyPatches:

    RemoteWebDriver._base_execute = RemoteWebDriver.execute

    def execute(self, driver_command, params=None):
        result = self._base_execute(driver_command, params)
        speed = self._get_speed()
        if speed > 0:
            time.sleep(speed)
        return result

    def get_current_url(self):
        return self.current_url

    def get_current_window_handle(self):
        return self.current_window_handle

    def get_current_window_info(self):
        atts = self.execute_script("return [ window.id, window.name, document.title, document.url ];")
        atts = [ att if att is not None and len(att) else 'undefined'
            for att in atts ]
        return (self.current_window_handle, atts[0], atts[1], atts[2], atts[3])

    def get_page_source(self):
        return self.page_source

    def get_title(self):
        return self.title

    def get_window_handles(self):
        return self.window_handles

    def current_window_is_main(self):
        return self.current_window_handle == self.window_handles[0];

    def set_speed(self, seconds):
        self._speed = seconds

    def _get_speed(self):
        if not hasattr(self, '_speed'):
            self._speed = float(0)
        return self._speed

    RemoteWebDriver.get_title = get_title
    RemoteWebDriver.get_current_url = get_current_url
    RemoteWebDriver.get_page_source = get_page_source
    RemoteWebDriver.get_current_window_handle = get_current_window_handle
    RemoteWebDriver.get_current_window_info = get_current_window_info
    RemoteWebDriver.get_window_handles = get_window_handles
    RemoteWebDriver.set_speed = set_speed
    RemoteWebDriver._get_speed = _get_speed
    RemoteWebDriver.execute = execute

########NEW FILE########
__FILENAME__ = variables
#encoding: utf-8
unic_text = u'ÄÖÅåöä €€ scandic toimii kivasti'

########NEW FILE########
__FILENAME__ = env
import os
import sys

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
UNIT_TEST_DIR = os.path.join(ROOT_DIR, "unit")
ACCEPTANCE_TEST_DIR = os.path.join(ROOT_DIR, "acceptance")
LIB_DIR = os.path.join(ROOT_DIR, "lib")
RESOURCES_DIR = os.path.join(ROOT_DIR, "resources")
RESULTS_DIR = os.path.join(ROOT_DIR, "results")
HTTP_SERVER_FILE = os.path.join(RESOURCES_DIR, 'testserver', 'testserver.py')
SRC_DIR = os.path.join(ROOT_DIR, "..", "src")

sys.path.insert(0, SRC_DIR)
sys.path.append(LIB_DIR)
sys.path.append(UNIT_TEST_DIR)

########NEW FILE########
__FILENAME__ = inorder
#!/usr/bin/env python3
# coding: utf-8

from mockito import verify as verify_main

__author__ = "Serhiy Oplakanets <serhiy@oplakanets.com>"
__copyright__ = "Copyright 2008-2010, Mockito Contributors"
__license__ = "MIT"
__maintainer__ = "Mockito Maintainers"
__email__ = "mockito-python@googlegroups.com"

def verify(object, *args, **kwargs):
  kwargs['inorder'] = True
  return verify_main(object, *args, **kwargs)


########NEW FILE########
__FILENAME__ = invocation
#!/usr/bin/env python
# coding: utf-8

import matchers

__copyright__ = "Copyright 2008-2010, Mockito Contributors"
__license__ = "MIT"
__maintainer__ = "Mockito Maintainers"
__email__ = "mockito-python@googlegroups.com"

class InvocationError(AssertionError):
    pass

class Invocation(object):
  def __init__(self, mock, method_name):
    self.method_name = method_name
    self.mock = mock
    self.verified = False
    self.verified_inorder = False
    self.params = ()
    self.named_params = {}
    self.answers = []
    self.strict = mock.strict
    
  def _remember_params(self, params, named_params):
    self.params = params
    self.named_params = named_params
    
  def __repr__(self):
    return self.method_name + "(" + ", ".join([repr(p) for p in self.params]) + ")"

  def answer_first(self):
    return self.answers[0].answer()
  
class MatchingInvocation(Invocation):
  @staticmethod
  def compare(p1, p2):
    if isinstance(p1, matchers.Matcher):
      if not p1.matches(p2): return False
    elif p1 != p2: return False
    return True

  def matches(self, invocation):
    if self.method_name != invocation.method_name:
      return False
    if len(self.params) != len(invocation.params):
      return False
    if len(self.named_params) != len(invocation.named_params):
      return False
    if self.named_params.keys() != invocation.named_params.keys():
      return False

    for x, p1 in enumerate(self.params):
      if not self.compare(p1, invocation.params[x]):
          return False
      
    for x, p1 in self.named_params.iteritems():
      if not self.compare(p1, invocation.named_params[x]):
          return False
      
    return True
  
class RememberedInvocation(Invocation):
  def __call__(self, *params, **named_params):
    self._remember_params(params, named_params)
    self.mock.remember(self)
    
    for matching_invocation in self.mock.stubbed_invocations:
      if matching_invocation.matches(self):
        return matching_invocation.answer_first()

    return None
  
class RememberedProxyInvocation(Invocation):
  '''Remeber params and proxy to method of original object.
  
  Calls method on original object and returns it's return value.
  '''
  def __call__(self, *params, **named_params):
    self._remember_params(params, named_params)
    self.mock.remember(self)
    obj = self.mock.original_object
    try:
      method = getattr(obj, self.method_name)
    except AttributeError:
      raise AttributeError("You tried to call method '%s' which '%s' instance does not have." % (self.method_name, obj.__class__.__name__))
    return method(*params, **named_params)

class VerifiableInvocation(MatchingInvocation):
  def __call__(self, *params, **named_params):
    self._remember_params(params, named_params)
    matched_invocations = []
    for invocation in self.mock.invocations:
      if self.matches(invocation):
        matched_invocations.append(invocation)

    verification = self.mock.pull_verification()
    verification.verify(self, len(matched_invocations))
    
    for invocation in matched_invocations:
      invocation.verified = True
  
class StubbedInvocation(MatchingInvocation):
  def __init__(self, *params):
    super(StubbedInvocation, self).__init__(*params)  
    if self.mock.strict:
      self.ensure_mocked_object_has_method(self.method_name)
        
  def ensure_mocked_object_has_method(self, method_name):  
    if not self.mock.has_method(method_name):
      raise InvocationError("You tried to stub a method '%s' the object (%s) doesn't have." 
                            % (method_name, self.mock.mocked_obj))
    
        
  def __call__(self, *params, **named_params):
    self._remember_params(params, named_params)
    return AnswerSelector(self)
  
  def stub_with(self, answer):
    self.answers.append(answer)
    self.mock.stub(self.method_name)
    self.mock.finish_stubbing(self)
    
class AnswerSelector(object):
  def __init__(self, invocation):
    self.invocation = invocation
    self.answer = None
  
  def thenReturn(self, *return_values):
    for return_value in return_values:
      self.__then(Return(return_value))
    return self
    
  def thenRaise(self, *exceptions):
    for exception in exceptions:
      self.__then(Raise(exception))
    return self

  def __then(self, answer):
    if not self.answer:
      self.answer = CompositeAnswer(answer)
      self.invocation.stub_with(self.answer)
    else:
      self.answer.add(answer)
      
    return self      

class CompositeAnswer(object):
  def __init__(self, answer):
    self.answers = [answer]
    
  def add(self, answer):
    self.answers.insert(0, answer)
    
  def answer(self):
    if len(self.answers) > 1:
      a = self.answers.pop()
    else:
      a = self.answers[0]
      
    return a.answer()

class Raise(object):
  def __init__(self, exception):
    self.exception = exception
    
  def answer(self):
    raise self.exception
  
class Return(object):
  def __init__(self, return_value):
    self.return_value = return_value
    
  def answer(self):
    return self.return_value

########NEW FILE########
__FILENAME__ = matchers
#!/usr/bin/env python
# coding: utf-8

'''Matchers for stubbing and verifications.

Common matchers for use in stubbing and verifications.
'''

__copyright__ = "Copyright 2008-2010, Mockito Contributors"
__license__ = "MIT"
__maintainer__ = "Mockito Maintainers"
__email__ = "mockito-python@googlegroups.com"

__all__ = ['any', 'contains', 'times']

class Matcher:
  def matches(self, arg):
    pass
  
class Any(Matcher):     
  def __init__(self, wanted_type=None):
    self.wanted_type = wanted_type
    
  def matches(self, arg):     
    if self.wanted_type:
      return isinstance(arg, self.wanted_type)
    else:
      return True
  
  def __repr__(self):
    return "<Any: %s>" % self.wanted_type  

class Contains(Matcher):
  def __init__(self, sub):
    self.sub = sub
      
  def matches(self, arg):
    if not hasattr(arg, 'find'):
      return  
    return self.sub and len(self.sub) > 0 and arg.find(self.sub) > -1

  def __repr__(self):
    return "<Contains: '%s'>" % self.sub  
  
      
def any(wanted_type=None):
  """Matches any() argument OR any(SomeClass) argument
     Examples:
       when(mock).foo(any()).thenReturn(1)
       verify(mock).foo(any(int))
  """
  return Any(wanted_type)     
        
def contains(sub):
  return Contains(sub)

def times(count):
  return count

########NEW FILE########
__FILENAME__ = mocking
#!/usr/bin/env python
# coding: utf-8

import inspect
import invocation
from mock_registry import mock_registry
import warnings

__copyright__ = "Copyright 2008-2010, Mockito Contributors"
__license__ = "MIT"
__maintainer__ = "Mockito Maintainers"
__email__ = "mockito-python@googlegroups.com"

__all__ = ['mock', 'Mock']

class _Dummy(object): pass

class TestDouble(object): pass

class mock(TestDouble):
  def __init__(self, mocked_obj=None, strict=True):
    self.invocations = []
    self.stubbed_invocations = []
    self.original_methods = []
    self.stubbing = None
    self.verification = None
    if mocked_obj is None:
        mocked_obj = _Dummy()
        strict = False
    self.mocked_obj = mocked_obj
    self.strict = strict
    self.stubbing_real_object = False
    
    mock_registry.register(self)
  
  def __getattr__(self, method_name):
    if self.stubbing is not None:
      return invocation.StubbedInvocation(self, method_name)
    
    if self.verification is not None:
      return invocation.VerifiableInvocation(self, method_name)
      
    return invocation.RememberedInvocation(self, method_name)
  
  def remember(self, invocation):
    self.invocations.insert(0, invocation)
  
  def finish_stubbing(self, stubbed_invocation):
    self.stubbed_invocations.insert(0, stubbed_invocation)
    self.stubbing = None
    
  def expect_stubbing(self):
    self.stubbing = True
    
  def pull_verification(self):
    v = self.verification
    self.verification = None
    return v

  def has_method(self, method_name):
    return hasattr(self.mocked_obj, method_name)
    
  def get_method(self, method_name):
    return self.mocked_obj.__dict__.get(method_name)

  def set_method(self, method_name, new_method):
    setattr(self.mocked_obj, method_name, new_method)
    
  def replace_method(self, method_name, original_method):
    
    def new_mocked_method(*args, **kwargs): 
      # we throw away the first argument, if it's either self or cls  
      if inspect.isclass(self.mocked_obj) and not isinstance(original_method, staticmethod): 
          args = args[1:]
      call = self.__getattr__(method_name) # that is: invocation.RememberedInvocation(self, method_name)
      return call(*args, **kwargs)
      
    if isinstance(original_method, staticmethod):
      new_mocked_method = staticmethod(new_mocked_method)  
    elif isinstance(original_method, classmethod): 
      new_mocked_method = classmethod(new_mocked_method)  
    
    self.set_method(method_name, new_mocked_method)
    
  def stub(self, method_name):
    original_method = self.get_method(method_name)
    original = (method_name, original_method)
    self.original_methods.append(original)

    # If we're trying to stub real object(not a generated mock), then we should patch object to use our mock method.
    # TODO: Polymorphism was invented long time ago. Refactor this.
    if self.stubbing_real_object:
      self.replace_method(method_name, original_method)

  def unstub(self):  
    while self.original_methods:  
      method_name, original_method = self.original_methods.pop()      
      self.set_method(method_name, original_method)
       
def Mock(*args, **kwargs):
  '''A ``mock``() alias.
  
  Alias for compatibility. To be removed in version 1.0.
  '''
  warnings.warn("\n`Mock()` is deprecated, please use `mock()` (lower 'm') instead.", DeprecationWarning)
  return mock(*args, **kwargs)

########NEW FILE########
__FILENAME__ = mockito
#!/usr/bin/env python
# coding: utf-8

import verification
from mocking import mock, TestDouble
from mock_registry import mock_registry
from verification import VerificationError

__copyright__ = "Copyright 2008-2010, Mockito Contributors"
__license__ = "MIT"
__maintainer__ = "Mockito Maintainers"
__email__ = "mockito-python@googlegroups.com"

class ArgumentError(Exception):
  pass

def _multiple_arguments_in_use(*args):
  return len(filter(lambda x: x, args)) > 1    

def _invalid_argument(value):
  return (value is not None and value < 1) or value == 0

def _invalid_between(between):
  if between is not None:
    start, end = between
    if start > end or start < 0:
      return True
  return False

def verify(obj, times=1, atleast=None, atmost=None, between=None, inorder=False):
  if times < 0:
    raise ArgumentError("""'times' argument has invalid value. 
                           It should be at least 0. You wanted to set it to: %i""" % times)
  if _multiple_arguments_in_use(atleast, atmost, between):
    raise ArgumentError("""Sure you know what you are doing?
                           You can set only one of the arguments: 'atleast', 'atmost' or 'between'.""")
  if _invalid_argument(atleast):
    raise ArgumentError("""'atleast' argument has invalid value.
                           It should be at least 1.  You wanted to set it to: %i""" % atleast)
  if _invalid_argument(atmost):
    raise ArgumentError("""'atmost' argument has invalid value.
                           It should be at least 1.  You wanted to set it to: %i""" % atmost)
  if _invalid_between(between):
    raise ArgumentError("""'between' argument has invalid value.
                           It should consist of positive values with second number not greater than first
                           e.g. [1, 4] or [0, 3] or [2, 2]
                           You wanted to set it to: %s""" % between)

  if isinstance(obj, TestDouble):
    mocked_object = obj
  else:
    mocked_object = mock_registry.mock_for(obj)
               
  if atleast:
    mocked_object.verification = verification.AtLeast(atleast)
  elif atmost:
    mocked_object.verification = verification.AtMost(atmost)
  elif between:
    mocked_object.verification = verification.Between(*between)
  else:
    mocked_object.verification = verification.Times(times)
    
  if inorder:
    mocked_object.verification = verification.InOrder(mocked_object.verification)
    
  return mocked_object

def when(obj, strict=True):
  if isinstance(obj, mock):
    theMock = obj
  else:    
    theMock = mock_registry.mock_for(obj)
    if theMock is None:
      theMock = mock(obj, strict=strict)
      # If we call when on something that is not TestDouble that means we're trying to stub real object,
      # (class, module etc.). Not to be confused with generating stubs from real classes.
      theMock.stubbing_real_object = True

  theMock.expect_stubbing()
  return theMock

def unstub():
  """Unstubs all stubbed methods and functions"""
  mock_registry.unstub_all()

def verifyNoMoreInteractions(*mocks):
  for mock in mocks:
    for i in mock.invocations:
      if not i.verified:
        raise VerificationError("\nUnwanted interaction: " + str(i))
      
def verifyZeroInteractions(*mocks):
  verifyNoMoreInteractions(*mocks)

########NEW FILE########
__FILENAME__ = mock_registry
class MockRegistry:
  """Registers mock()s, ensures that we only have one mock() per mocked_obj, and
  iterates over them to unstub each stubbed method. """
  
  def __init__(self):
    self.mocks = {}
    
  def register(self, mock):
    self.mocks[mock.mocked_obj] = mock
        
  def mock_for(self, cls):
    return self.mocks.get(cls, None)
  
  def unstub_all(self):
    for mock in self.mocks.itervalues():    
      mock.unstub()
    self.mocks.clear()  

mock_registry = MockRegistry()
########NEW FILE########
__FILENAME__ = spying
#!/usr/bin/env python
# coding: utf-8

'''Spying on real objects.'''

from invocation import RememberedProxyInvocation, VerifiableInvocation
from mocking import TestDouble

__author__ = "Serhiy Oplakanets <serhiy@oplakanets.com>"
__copyright__ = "Copyright 2009-2010, Mockito Contributors"
__license__ = "MIT"
__maintainer__ = "Mockito Maintainers"
__email__ = "mockito-python@googlegroups.com"

__all__ = ['spy']

def spy(original_object):
  return Spy(original_object)

class Spy(TestDouble):
  strict = True # spies always have to check if method exists
  
  def __init__(self, original_object):
    self.original_object = original_object
    self.invocations = []
    self.verification = None
    
  def __getattr__(self, name):        
    if self.verification:
      return VerifiableInvocation(self, name)
    else:
      return RememberedProxyInvocation(self, name)
  
  def remember(self, invocation):
    self.invocations.insert(0, invocation)
    
  def pull_verification(self):
    v = self.verification
    self.verification = None
    return v
    
########NEW FILE########
__FILENAME__ = verification
#!/usr/bin/env python
# coding: utf-8

__copyright__ = "Copyright 2008-2010, Mockito Contributors"
__license__ = "MIT"
__maintainer__ = "Mockito Maintainers"
__email__ = "mockito-python@googlegroups.com"

__all__ = ['never', 'VerificationError']

class VerificationError(AssertionError):
  '''Indicates error during verification of invocations.
  
  Raised if verification fails. Error message contains the cause.
  '''
  pass

class AtLeast(object):
  def __init__(self, wanted_count):
    self.wanted_count = wanted_count
    
  def verify(self, invocation, actual_count):
    if actual_count < self.wanted_count: 
      raise VerificationError("\nWanted at least: %i, actual times: %i" % (self.wanted_count, actual_count))
    
class AtMost(object):
  def __init__(self, wanted_count):
    self.wanted_count = wanted_count
    
  def verify(self, invocation, actual_count):
    if actual_count > self.wanted_count: 
      raise VerificationError("\nWanted at most: %i, actual times: %i" % (self.wanted_count, actual_count))

class Between(object):
  def __init__(self, wanted_from, wanted_to):
    self.wanted_from = wanted_from
    self.wanted_to = wanted_to
    
  def verify(self, invocation, actual_count):
    if actual_count < self.wanted_from or actual_count > self.wanted_to: 
      raise VerificationError("\nWanted between: [%i, %i], actual times: %i" % (self.wanted_from, self.wanted_to, actual_count))
    
class Times(object):
  def __init__(self, wanted_count):
    self.wanted_count = wanted_count
    
  def verify(self, invocation, actual_count):
    if actual_count == self.wanted_count:
        return  
    if actual_count == 0:
      raise VerificationError("\nWanted but not invoked: %s" % (invocation))
    else:
      if self.wanted_count == 0:
        raise VerificationError("\nUnwanted invocation of %s, times: %i" % (invocation, actual_count))
      else:
        raise VerificationError("\nWanted times: %i, actual times: %i" % (self.wanted_count, actual_count))
    
class InOrder(object):
  ''' 
  Verifies invocations in order.
  
  Verifies if invocation was in expected order, and if yes -- degrades to original Verifier (AtLeast, Times, Between, ...).
  '''
  
  def __init__(self, original_verification):
    '''    
    @param original_verification: Original verifiaction to degrade to if order of invocation was ok.
    '''
    self.original_verification = original_verification
    
  def verify(self, wanted_invocation, count):
    for invocation in reversed(wanted_invocation.mock.invocations):
      if not invocation.verified_inorder:
        if not wanted_invocation.matches(invocation):
          raise VerificationError("\nWanted %s to be invoked, got %s instead" % (wanted_invocation, invocation))
        invocation.verified_inorder = True
        break
    # proceed with original verification
    self.original_verification.verify(wanted_invocation, count)
    
never = 0

########NEW FILE########
__FILENAME__ = statuschecker
#!/usr/bin/env python

#  Copyright 2008-2012 Nokia Siemens Networks Oyj
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

"""Robot Framework Test Status Checker

Usage:  statuschecker.py infile [outfile]

This tool processes Robot Framework output XML files and checks that test case
statuses and messages are as expected. Main use case is post-processing output
files got when testing Robot Framework test libraries using Robot Framework
itself.

If output file is not given, the input file is considered to be also output
file and it is edited in place.

By default all test cases are expected to 'PASS' and have no message. Changing
the expected status to 'FAIL' is done by having word 'FAIL' (in uppercase)
somewhere in the test case documentation. Expected error message must then be
given after 'FAIL'. Error message can also be specified as a regular
expression by prefixing it with string 'REGEXP:'. Testing only the beginning
of the message is possible with 'STARTS:' prefix.

This tool also allows testing the created log messages. They are specified
using a syntax 'LOG x.y:z LEVEL Actual message', which is described in detail
detail in the tool documentation.
"""

import re

from robot.result import ExecutionResult


def process_output(inpath, outpath=None):
    result = ExecutionResult(inpath)
    _process_suite(result.suite)
    result.save(outpath)
    return result.return_code

def _process_suite(suite):
    for subsuite in suite.suites:
        _process_suite(subsuite)
    for test in suite.tests:
        _process_test(test)

def _process_test(test):
    exp = _Expected(test.doc)
    _check_status(test, exp)
    if test.status == 'PASS':
        _check_logs(test, exp)

def _check_status(test, exp):
    if exp.status != test.status:
        test.status = 'FAIL'
        if exp.status == 'PASS':
            test.message = ("Test was expected to PASS but it FAILED. "
                            "Error message:\n") + test.message
        else:
            test.message = ("Test was expected to FAIL but it PASSED. "
                            "Expected message:\n") + exp.message
    elif not _message_matches(test.message, exp.message):
        test.status = 'FAIL'
        test.message = ("Wrong error message.\n\nExpected:\n%s\n\nActual:\n%s\n"
                        % (exp.message, test.message))
    elif test.status == 'FAIL':
        test.status = 'PASS'
        test.message = 'Original test failed as expected.'

def _message_matches(actual, expected):
    if actual == expected:
        return True
    if expected.startswith('REGEXP:'):
        pattern = '^%s$' % expected.replace('REGEXP:', '', 1).strip()
        if re.match(pattern, actual, re.DOTALL):
            return True
    if expected.startswith('STARTS:'):
        start = expected.replace('STARTS:', '', 1).strip()
        if actual.startswith(start):
            return True
    return False

def _check_logs(test, exp):
    for kw_indices, msg_index, level, message in exp.logs:
        try:
            kw = test.keywords[kw_indices[0]]
            for index in kw_indices[1:]:
                kw = kw.keywords[index]
        except IndexError:
            indices = '.'.join(str(i+1) for i in kw_indices)
            test.status = 'FAIL'
            test.message = ("Test '%s' does not have keyword with index '%s'"
                            % (test.name, indices))
            return
        if len(kw.messages) <= msg_index:
            if message != 'NONE':
                test.status = 'FAIL'
                test.message = ("Keyword '%s' should have had at least %d "
                                "messages" % (kw.name, msg_index+1))
        else:
            if _check_log_level(level, test, kw, msg_index):
                _check_log_message(message, test, kw, msg_index)

def _check_log_level(expected, test, kw, index):
    actual = kw.messages[index].level
    if actual == expected:
        return True
    test.status = 'FAIL'
    test.message = ("Wrong level for message %d of keyword '%s'.\n\n"
                    "Expected: %s\nActual: %s.\n%s"
                    % (index+1, kw.name, expected,
                       actual, kw.messages[index].message))
    return False

def _check_log_message(expected, test, kw, index):
    actual = kw.messages[index].message.strip()
    if _message_matches(actual, expected):
        return True
    test.status = 'FAIL'
    test.message = ("Wrong content for message %d of keyword '%s'.\n\n"
                    "Expected:\n%s\n\nActual:\n%s"
                    % (index+1, kw.name, expected, actual))
    return False


class _Expected:

    def __init__(self, doc):
        self.status, self.message = self._get_status_and_message(doc)
        self.logs = self._get_logs(doc)

    def _get_status_and_message(self, doc):
        if 'FAIL' in doc:
            return 'FAIL', doc.split('FAIL', 1)[1].split('LOG', 1)[0].strip()
        return 'PASS', ''

    def _get_logs(self, doc):
        logs = []
        for item in doc.split('LOG')[1:]:
            index_str, msg_str = item.strip().split(' ', 1)
            kw_indices, msg_index = self._get_indices(index_str)
            level, message = self._get_log_message(msg_str)
            logs.append((kw_indices, msg_index, level, message))
        return logs

    def _get_indices(self, index_str):
        try:
            kw_indices, msg_index = index_str.split(':')
        except ValueError:
            kw_indices, msg_index = index_str, '1'
        kw_indices = [int(index) - 1 for index in kw_indices.split('.')]
        return kw_indices, int(msg_index) - 1

    def _get_log_message(self, msg_str):
        try:
            level, message = msg_str.split(' ', 1)
            if level not in ['TRACE', 'DEBUG', 'INFO', 'WARN', 'FAIL']:
                raise ValueError
        except ValueError:
            level, message = 'INFO', msg_str
        return level, message


if __name__=='__main__':
    import sys
    import os

    if not 2 <= len(sys.argv) <= 3 or '--help' in sys.argv:
        print __doc__
        sys.exit(1)
    infile = sys.argv[1]
    outfile = sys.argv[2] if len(sys.argv) == 3 else None
    print  "Checking %s" % os.path.abspath(infile)
    rc = process_output(infile, outfile)
    if outfile:
        print "Output: %s" % os.path.abspath(outfile)
    if rc > 255:
        rc = 255
    sys.exit(rc)

########NEW FILE########
__FILENAME__ = testserver
# http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/336012

import SimpleHTTPServer
import BaseHTTPServer
import httplib
import os


class StoppableHttpRequestHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
    """http request handler with QUIT stopping the server"""

    def do_QUIT(self):
        """send 200 OK response, and set server.stop to True"""
        self.send_response(200)
        self.end_headers()
        self.server.stop = True
        
    def do_POST(self):
        # We could also process paremeters here using something like below.
        # length = self.headers['Content-Length']
        # print self.rfile.read(int(length))
        self.do_GET()

    def send_head(self):
        # This is ripped directly from SimpleHTTPRequestHandler,
        # only the cookie part is added.
        """Common code for GET and HEAD commands.

        This sends the response code and MIME headers.

        Return value is either a file object (which has to be copied
        to the outputfile by the caller unless the command was HEAD,
        and must be closed by the caller under all circumstances), or
        None, in which case the caller has nothing further to do.

        """
        path = self.translate_path(self.path)
        f = None
        if os.path.isdir(path):
            if not self.path.endswith('/'):
                # redirect browser - doing basically what apache does
                self.send_response(301)
                self.send_header("Location", self.path + "/")
                self.end_headers()
                return None
            for index in "index.html", "index.htm":
                index = os.path.join(path, index)
                if os.path.exists(index):
                    path = index
                    break
            else:
                return self.list_directory(path)
        ctype = self.guess_type(path)
        if ctype.startswith('text/'):
            mode = 'r'
        else:
            mode = 'rb'
        try:
            f = open(path, mode)
        except IOError:
            self.send_error(404, "File not found")
            return None
        self.send_response(200)
        self.send_header("Content-type", ctype)
        fs = os.fstat(f.fileno())
        self.send_header("Content-Length", str(fs[6]))
        self.send_header("Last-Modified", self.date_time_string(fs.st_mtime))
        self.send_header("Set-Cookie", "test=seleniumlibrary;")
        self.send_header("Set-Cookie", "another=value;")
        self.end_headers()
        return f


class StoppableHttpServer(BaseHTTPServer.HTTPServer):
    """http server that reacts to self.stop flag"""

    def serve_forever(self):
        """Handle one request at a time until stopped."""
        self.stop = False
        while not self.stop:
            self.handle_request()

def stop_server(port=7000):
    """send QUIT request to http server running on localhost:<port>"""
    conn = httplib.HTTPConnection("localhost:%d" % port)
    conn.request("QUIT", "/")
    conn.getresponse()

def start_server(port=7000):
    import os
    os.chdir(os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), '..'))
    server = StoppableHttpServer(('', port), StoppableHttpRequestHandler)
    server.serve_forever()
    
    
if __name__ == '__main__':
    import sys
    if len(sys.argv) != 2 or sys.argv[1] not in [ 'start', 'stop' ]:
        print 'usage: %s start|stop' % sys.argv[0]
        sys.exit(1)
    if sys.argv[1] == 'start':
        start_server()
    else:
        stop_server()



########NEW FILE########
__FILENAME__ = run_tests
#!/usr/bin/env python

import env
import os
import sys
from subprocess import Popen, call
from tempfile import TemporaryFile

from run_unit_tests import run_unit_tests

ROBOT_ARGS = [
    '--doc', 'SeleniumSPacceptanceSPtestsSPwithSP%(browser)s',
    '--outputdir', '%(outdir)s',
    '--variable', 'browser:%(browser)s',
    '--escape', 'space:SP',
    '--report', 'none',
    '--log', 'none',
    #'--suite', 'Acceptance.Keywords.Textfields',
    '--loglevel', 'DEBUG',
    '--pythonpath', '%(pythonpath)s',
]
REBOT_ARGS = [
    '--outputdir', '%(outdir)s',
    '--name', '%(browser)sSPAcceptanceSPTests',
    '--escape', 'space:SP',
    '--critical', 'regression',
    '--noncritical', 'inprogress',
]
ARG_VALUES = {'outdir': env.RESULTS_DIR, 'pythonpath': env.SRC_DIR}

def acceptance_tests(interpreter, browser, args):
    ARG_VALUES['browser'] = browser.replace('*', '')
    start_http_server()
    runner = {'python': 'pybot', 'jython': 'jybot', 'ipy': 'ipybot'}[interpreter]
    if os.sep == '\\':
        runner += '.bat'
    execute_tests(runner, args)
    stop_http_server()
    return process_output(args)

def start_http_server():
    server_output = TemporaryFile()
    Popen(['python', env.HTTP_SERVER_FILE ,'start'],
          stdout=server_output, stderr=server_output)

def execute_tests(runner, args):
    if not os.path.exists(env.RESULTS_DIR):
        os.mkdir(env.RESULTS_DIR)
    command = [runner] + [arg % ARG_VALUES for arg in ROBOT_ARGS] + args + [env.ACCEPTANCE_TEST_DIR]
    print ''
    print 'Starting test execution with command:\n' + ' '.join(command)
    syslog = os.path.join(env.RESULTS_DIR, 'syslog.txt')
    call(command, shell=os.sep=='\\', env=dict(os.environ, ROBOT_SYSLOG_FILE=syslog))

def stop_http_server():
    call(['python', env.HTTP_SERVER_FILE, 'stop'])

def process_output(args):
    print
    if _has_robot_27():
        call(['python', os.path.join(env.RESOURCES_DIR, 'statuschecker.py'),
             os.path.join(env.RESULTS_DIR, 'output.xml')])
    rebot = 'rebot' if os.sep == '/' else 'rebot.bat'
    rebot_cmd = [rebot] + [ arg % ARG_VALUES for arg in REBOT_ARGS ] + args + \
                [os.path.join(ARG_VALUES['outdir'], 'output.xml') ]
    rc = call(rebot_cmd, env=os.environ)
    if rc == 0:
        print 'All critical tests passed'
    else:
        print '%d critical test%s failed' % (rc, 's' if rc != 1 else '')
    return rc

def _has_robot_27():
    try:
        from robot.result import ExecutionResult
    except:
        return False
    return True

def _exit(rc):
    sys.exit(rc)

def _help():
    print 'Usage:  python run_tests.py python|jython browser [options]'
    print
    print 'See README.txt for details.'
    return 255

def _run_unit_tests():
    print 'Running unit tests'
    failures = run_unit_tests()
    if failures != 0:
        print '\n%d unit tests failed - not running acceptance tests!' % failures
    else:
        print 'All unit tests passed'
    return failures


if __name__ ==  '__main__':
    if not len(sys.argv) > 2:
        _exit(_help())
    unit_failures = _run_unit_tests()
    if unit_failures:
        _exit(unit_failures)
    interpreter = sys.argv[1]
    browser = sys.argv[2].lower()
    args = sys.argv[3:]
    if browser != 'unit':
        _exit(acceptance_tests(interpreter, browser, args))

########NEW FILE########
__FILENAME__ = run_unit_tests
import env
import os, sys
import unittest
from Selenium2Library import utils

def run_unit_tests(modules_to_run=[]):
    (test_module_names, test_modules) = utils.import_modules_under(
        env.UNIT_TEST_DIR, include_root_package_name = False, pattern="test*.py")

    bad_modules_to_run = [module_to_run for module_to_run in modules_to_run
        if module_to_run not in test_module_names]
    if bad_modules_to_run:
        print "Specified test module%s not exist: %s" % (
            ' does' if len(bad_modules_to_run) == 1 else 's do',
            ', '.join(bad_modules_to_run))
        return -1

    tests = [unittest.defaultTestLoader.loadTestsFromModule(test_module) 
        for test_module in test_modules]

    runner = unittest.TextTestRunner()
    result = runner.run(unittest.TestSuite(tests))
    rc = len(result.failures) + len(result.errors)
    if rc > 255: rc = 255
    return rc

if __name__ == '__main__':
    sys.exit(run_unit_tests(sys.argv[1:]))


########NEW FILE########
__FILENAME__ = test_browsermanagement
import unittest
from Selenium2Library.keywords._browsermanagement import _BrowserManagementKeywords
from selenium import webdriver
from mockito import *

class BrowserManagementTests(unittest.TestCase): 

    
    def test_create_firefox_browser(self):
        test_browsers = ((webdriver.Firefox, "ff"), (webdriver.Firefox, "firEfOx"))

        for test_browser in test_browsers:
            self.verify_browser(*test_browser)
    
    def mock_createProfile(self, profile_directory=None):
        self.ff_profile_dir = profile_directory
        return self.old_profile_init(profile_directory)

    def test_create_ie_browser(self):
        test_browsers = ((webdriver.Ie, "ie"), (webdriver.Ie, "Internet Explorer"))

        for test_browser in test_browsers:
            self.verify_browser(*test_browser)

    def test_create_chrome_browser(self):
        test_browsers = ((webdriver.Chrome, "gOOglEchrOmE"),(webdriver.Chrome,"gc"),
                          (webdriver.Chrome, "chrome"))

        for test_browser in test_browsers:
            self.verify_browser(*test_browser)

    def test_create_opera_browser(self):
        self.verify_browser(webdriver.Opera, "OPERA")

    def test_create_phantomjs_browser(self):
        self.verify_browser(webdriver.PhantomJS, "PHANTOMJS")

    def test_create_remote_browser(self):
        self.verify_browser(webdriver.Remote, "chrome", remote="http://127.0.0.1/wd/hub")

    def test_create_htmlunit_browser(self):
        self.verify_browser(webdriver.Remote, "htmlunit")

    def test_create_htmlunitwihtjs_browser(self):
        self.verify_browser(webdriver.Remote, "htmlunitwithjs")

    def test_parse_capabilities_string(self):
        bm = _BrowserManagementKeywords()
        expected_caps = "key1:val1,key2:val2"
        capabilities = bm._parse_capabilities_string(expected_caps)
        self.assertTrue("val1", capabilities["key1"])
        self.assertTrue("val2", capabilities["key2"])
        self.assertTrue(2, len(capabilities))

    def test_parse_complex_capabilities_string(self):
        bm = _BrowserManagementKeywords()
        expected_caps = "proxyType:manual,httpProxy:IP:port"
        capabilities = bm._parse_capabilities_string(expected_caps)
        self.assertTrue("manual", capabilities["proxyType"])
        self.assertTrue("IP:port", capabilities["httpProxy"])
        self.assertTrue(2, len(capabilities))

    def test_create_remote_browser_with_desired_prefs(self):
        expected_caps = {"key1":"val1","key2":"val2"}
        self.verify_browser(webdriver.Remote, "chrome", remote="http://127.0.0.1/wd/hub",
            desired_capabilities=expected_caps)

    def test_create_remote_browser_with_string_desired_prefs(self):
        expected_caps = "key1:val1,key2:val2"
        self.verify_browser(webdriver.Remote, "chrome", remote="http://127.0.0.1/wd/hub",
            desired_capabilities=expected_caps)

    def test_capabilities_attribute_not_modified(self):
        expected_caps = {"some_cap":"42"}
        self.verify_browser(webdriver.Remote, "chrome", remote="http://127.0.0.1/wd/hub",
            desired_capabilities=expected_caps)
        self.assertFalse("some_cap" in webdriver.DesiredCapabilities.CHROME)

    def test_set_selenium_timeout_only_affects_open_browsers(self):
        bm = _BrowserManagementKeywords()
        first_browser, second_browser = mock(), mock()
        bm._cache.register(first_browser)
        bm._cache.close()
        verify(first_browser).quit()
        bm._cache.register(second_browser)
        bm.set_selenium_timeout("10 seconds")
        verify(second_browser).set_script_timeout(10.0)
        bm._cache.close_all()
        verify(second_browser).quit()
        bm.set_selenium_timeout("20 seconds")
        verifyNoMoreInteractions(first_browser)
        verifyNoMoreInteractions(second_browser)

    def test_bad_browser_name(self):
        bm = _BrowserManagementKeywords()
        try:
            bm._make_browser("fireox")
            self.fail("Exception not raised")
        except ValueError, e:
            self.assertEquals("fireox is not a supported browser.", e.message)

    def test_create_webdriver(self):
        bm = _BrowserManagementWithLoggingStubs()
        capt_data = {}
        class FakeWebDriver(mock):
            def __init__(self, some_arg=None):
                mock.__init__(self)
                capt_data['some_arg'] = some_arg
                capt_data['webdriver'] = self
        webdriver.FakeWebDriver = FakeWebDriver
        try:
            index = bm.create_webdriver('FakeWebDriver', 'fake', some_arg=1)
            self.assertEquals(capt_data['some_arg'], 1)
            self.assertEquals(capt_data['webdriver'], bm._current_browser())
            self.assertEquals(capt_data['webdriver'], bm._cache.get_connection(index))
            self.assertEquals(capt_data['webdriver'], bm._cache.get_connection('fake'))
            capt_data.clear()
            my_kwargs = {'some_arg':2}
            bm.create_webdriver('FakeWebDriver', kwargs=my_kwargs)
            self.assertEquals(capt_data['some_arg'], 2)
        finally:
            del webdriver.FakeWebDriver

    def verify_browser(self , webdriver_type , browser_name, **kw):
        #todo try lambda *x: was_called = true
        bm = _BrowserManagementKeywords()
        old_init = webdriver_type.__init__
        webdriver_type.__init__ = self.mock_init
        
        try:
            self.was_called = False
            bm._make_browser(browser_name, **kw)
        except AttributeError:
            pass #kinda dangerous but I'm too lazy to mock out all the set_timeout calls
        finally:
            webdriver_type.__init__ = old_init
            self.assertTrue(self.was_called)
            
    def mock_init(self, *args, **kw):
        self.was_called = True


class _BrowserManagementWithLoggingStubs(_BrowserManagementKeywords):

    def __init__(self):
        _BrowserManagementKeywords.__init__(self)
        def mock_logging_method(self, *args, **kwargs):
            pass
        for name in ['_info', '_debug', '_warn', '_log', '_html']:
            setattr(self, name, mock_logging_method)

########NEW FILE########
__FILENAME__ = test_elementfinder
import unittest
import os
from Selenium2Library.locators import ElementFinder
from mockito import *

class ElementFinderTests(unittest.TestCase):

    def test_find_with_invalid_prefix(self):
        finder = ElementFinder()
        browser = mock()
        try:
            self.assertRaises(ValueError, finder.find, browser, "something=test1")
        except ValueError as e:
            self.assertEqual(e.message, "Element locator with prefix 'something' is not supported")

    def test_find_with_null_browser(self):
        finder = ElementFinder()
        self.assertRaises(AssertionError,
            finder.find, None, "id=test1")

    def test_find_with_null_locator(self):
        finder = ElementFinder()
        browser = mock()
        self.assertRaises(AssertionError,
            finder.find, browser, None)

    def test_find_with_empty_locator(self):
        finder = ElementFinder()
        browser = mock()
        self.assertRaises(AssertionError,
            finder.find, browser, "")

    def test_find_with_no_tag(self):
        finder = ElementFinder()
        browser = mock()
        finder.find(browser, "test1")
        verify(browser).find_elements_by_xpath("//*[(@id='test1' or @name='test1')]")

    def test_find_with_tag(self):
        finder = ElementFinder()
        browser = mock()
        finder.find(browser, "test1", tag='div')
        verify(browser).find_elements_by_xpath("//div[(@id='test1' or @name='test1')]")

    def test_find_with_locator_with_apos(self):
        finder = ElementFinder()
        browser = mock()
        finder.find(browser, "test '1'")
        verify(browser).find_elements_by_xpath("//*[(@id=\"test '1'\" or @name=\"test '1'\")]")

    def test_find_with_locator_with_quote(self):
        finder = ElementFinder()
        browser = mock()
        finder.find(browser, "test \"1\"")
        verify(browser).find_elements_by_xpath("//*[(@id='test \"1\"' or @name='test \"1\"')]")

    def test_find_with_locator_with_quote_and_apos(self):
        finder = ElementFinder()
        browser = mock()
        finder.find(browser, "test \"1\" and '2'")
        verify(browser).find_elements_by_xpath(
            "//*[(@id=concat('test \"1\" and ', \"'\", '2', \"'\", '') or @name=concat('test \"1\" and ', \"'\", '2', \"'\", ''))]")

    def test_find_with_a(self):
        finder = ElementFinder()
        browser = mock()
        when(browser).get_current_url().thenReturn("http://localhost/mypage.html")
        finder.find(browser, "test1", tag='a')
        verify(browser).find_elements_by_xpath(
            "//a[(@id='test1' or @name='test1' or @href='test1' or normalize-space(descendant-or-self::text())='test1' or @href='http://localhost/test1')]")

    def test_find_with_link_synonym(self):
        finder = ElementFinder()
        browser = mock()
        when(browser).get_current_url().thenReturn("http://localhost/mypage.html")
        finder.find(browser, "test1", tag='link')
        verify(browser).find_elements_by_xpath(
            "//a[(@id='test1' or @name='test1' or @href='test1' or normalize-space(descendant-or-self::text())='test1' or @href='http://localhost/test1')]")

    def test_find_with_img(self):
        finder = ElementFinder()
        browser = mock()
        when(browser).get_current_url().thenReturn("http://localhost/mypage.html")
        finder.find(browser, "test1", tag='img')
        verify(browser).find_elements_by_xpath(
            "//img[(@id='test1' or @name='test1' or @src='test1' or @alt='test1' or @src='http://localhost/test1')]")

    def test_find_with_image_synonym(self):
        finder = ElementFinder()
        browser = mock()
        when(browser).get_current_url().thenReturn("http://localhost/mypage.html")
        finder.find(browser, "test1", tag='image')
        verify(browser).find_elements_by_xpath(
            "//img[(@id='test1' or @name='test1' or @src='test1' or @alt='test1' or @src='http://localhost/test1')]")

    def test_find_with_input(self):
        finder = ElementFinder()
        browser = mock()
        when(browser).get_current_url().thenReturn("http://localhost/mypage.html")
        finder.find(browser, "test1", tag='input')
        verify(browser).find_elements_by_xpath(
            "//input[(@id='test1' or @name='test1' or @value='test1' or @src='test1' or @src='http://localhost/test1')]")

    def test_find_with_radio_button_synonym(self):
        finder = ElementFinder()
        browser = mock()
        when(browser).get_current_url().thenReturn("http://localhost/mypage.html")
        finder.find(browser, "test1", tag='radio button')
        verify(browser).find_elements_by_xpath(
            "//input[@type='radio' and (@id='test1' or @name='test1' or @value='test1' or @src='test1' or @src='http://localhost/test1')]")

    def test_find_with_checkbox_synonym(self):
        finder = ElementFinder()
        browser = mock()
        when(browser).get_current_url().thenReturn("http://localhost/mypage.html")
        finder.find(browser, "test1", tag='checkbox')
        verify(browser).find_elements_by_xpath(
            "//input[@type='checkbox' and (@id='test1' or @name='test1' or @value='test1' or @src='test1' or @src='http://localhost/test1')]")

    def test_find_with_file_upload_synonym(self):
        finder = ElementFinder()
        browser = mock()
        when(browser).get_current_url().thenReturn("http://localhost/mypage.html")
        finder.find(browser, "test1", tag='file upload')
        verify(browser).find_elements_by_xpath(
            "//input[@type='file' and (@id='test1' or @name='test1' or @value='test1' or @src='test1' or @src='http://localhost/test1')]")

    def test_find_with_text_field_synonym(self):
        finder = ElementFinder()
        browser = mock()
        when(browser).get_current_url().thenReturn("http://localhost/mypage.html")
        finder.find(browser, "test1", tag='text field')
        verify(browser).find_elements_by_xpath(
            "//input[@type='text' and (@id='test1' or @name='test1' or @value='test1' or @src='test1' or @src='http://localhost/test1')]")

    def test_find_with_button(self):
        finder = ElementFinder()
        browser = mock()
        finder.find(browser, "test1", tag='button')
        verify(browser).find_elements_by_xpath(
            "//button[(@id='test1' or @name='test1' or @value='test1' or normalize-space(descendant-or-self::text())='test1')]")

    def test_find_with_select(self):
        finder = ElementFinder()
        browser = mock()
        finder.find(browser, "test1", tag='select')
        verify(browser).find_elements_by_xpath(
            "//select[(@id='test1' or @name='test1')]")

    def test_find_with_list_synonym(self):
        finder = ElementFinder()
        browser = mock()
        finder.find(browser, "test1", tag='list')
        verify(browser).find_elements_by_xpath(
            "//select[(@id='test1' or @name='test1')]")

    def test_find_with_implicit_xpath(self):
        finder = ElementFinder()
        browser = mock()

        elements = self._make_mock_elements('div', 'a', 'span', 'a')
        when(browser).find_elements_by_xpath("//*[(@test='1')]").thenReturn(elements)

        result = finder.find(browser, "//*[(@test='1')]")
        self.assertEqual(result, elements)
        result = finder.find(browser, "//*[(@test='1')]", tag='a')
        self.assertEqual(result, [elements[1], elements[3]])

    def test_find_by_identifier(self):
        finder = ElementFinder()
        browser = mock()

        id_elements = self._make_mock_elements('div', 'a')
        name_elements = self._make_mock_elements('span', 'a')
        when(browser).find_elements_by_id("test1").thenReturn(list(id_elements)).thenReturn(list(id_elements))
        when(browser).find_elements_by_name("test1").thenReturn(list(name_elements)).thenReturn(list(name_elements))

        all_elements = list(id_elements)
        all_elements.extend(name_elements)

        result = finder.find(browser, "identifier=test1")
        self.assertEqual(result, all_elements)
        result = finder.find(browser, "identifier=test1", tag='a')
        self.assertEqual(result, [id_elements[1], name_elements[1]])

    def test_find_by_id(self):
        finder = ElementFinder()
        browser = mock()

        elements = self._make_mock_elements('div', 'a', 'span', 'a')
        when(browser).find_elements_by_id("test1").thenReturn(elements)

        result = finder.find(browser, "id=test1")
        self.assertEqual(result, elements)
        result = finder.find(browser, "id=test1", tag='a')
        self.assertEqual(result, [elements[1], elements[3]])

    def test_find_by_name(self):
        finder = ElementFinder()
        browser = mock()

        elements = self._make_mock_elements('div', 'a', 'span', 'a')
        when(browser).find_elements_by_name("test1").thenReturn(elements)

        result = finder.find(browser, "name=test1")
        self.assertEqual(result, elements)
        result = finder.find(browser, "name=test1", tag='a')
        self.assertEqual(result, [elements[1], elements[3]])

    def test_find_by_xpath(self):
        finder = ElementFinder()
        browser = mock()

        elements = self._make_mock_elements('div', 'a', 'span', 'a')
        when(browser).find_elements_by_xpath("//*[(@test='1')]").thenReturn(elements)

        result = finder.find(browser, "xpath=//*[(@test='1')]")
        self.assertEqual(result, elements)
        result = finder.find(browser, "xpath=//*[(@test='1')]", tag='a')
        self.assertEqual(result, [elements[1], elements[3]])

    def test_find_by_dom(self):
        finder = ElementFinder()
        browser = mock()

        elements = self._make_mock_elements('div', 'a', 'span', 'a')
        when(browser).execute_script("return document.getElementsByTagName('a');").thenReturn(
            [elements[1], elements[3]])

        result = finder.find(browser, "dom=document.getElementsByTagName('a')")
        self.assertEqual(result, [elements[1], elements[3]])

    def test_find_by_link_text(self):
        finder = ElementFinder()
        browser = mock()

        elements = self._make_mock_elements('div', 'a', 'span', 'a')
        when(browser).find_elements_by_link_text("my link").thenReturn(elements)

        result = finder.find(browser, "link=my link")
        self.assertEqual(result, elements)
        result = finder.find(browser, "link=my link", tag='a')
        self.assertEqual(result, [elements[1], elements[3]])

    def test_find_by_css_selector(self):
        finder = ElementFinder()
        browser = mock()

        elements = self._make_mock_elements('div', 'a', 'span', 'a')
        when(browser).find_elements_by_css_selector("#test1").thenReturn(elements)

        result = finder.find(browser, "css=#test1")
        self.assertEqual(result, elements)
        result = finder.find(browser, "css=#test1", tag='a')
        self.assertEqual(result, [elements[1], elements[3]])

    def test_find_by_tag_name(self):
        finder = ElementFinder()
        browser = mock()

        elements = self._make_mock_elements('div', 'a', 'span', 'a')
        when(browser).find_elements_by_tag_name("div").thenReturn(elements)

        result = finder.find(browser, "tag=div")
        self.assertEqual(result, elements)
        result = finder.find(browser, "tag=div", tag='a')
        self.assertEqual(result, [elements[1], elements[3]])

    def test_find_with_sloppy_prefix(self):
        finder = ElementFinder()
        browser = mock()

        elements = self._make_mock_elements('div', 'a', 'span', 'a')
        when(browser).find_elements_by_id("test1").thenReturn(elements)

        result = finder.find(browser, "ID=test1")
        self.assertEqual(result, elements)
        result = finder.find(browser, "iD=test1")
        self.assertEqual(result, elements)
        result = finder.find(browser, "id=test1")
        self.assertEqual(result, elements)
        result = finder.find(browser, "  id =test1")
        self.assertEqual(result, elements)

    def test_find_with_sloppy_criteria(self):
        finder = ElementFinder()
        browser = mock()

        elements = self._make_mock_elements('div', 'a', 'span', 'a')
        when(browser).find_elements_by_id("test1").thenReturn(elements)

        result = finder.find(browser, "id= test1  ")
        self.assertEqual(result, elements)

    def test_find_by_id_with_synonym_and_constraints(self):
        finder = ElementFinder()
        browser = mock()

        elements = self._make_mock_elements('div', 'input', 'span', 'input', 'a', 'input', 'div', 'input')
        elements[1].set_attribute('type', 'radio')
        elements[3].set_attribute('type', 'checkbox')
        elements[5].set_attribute('type', 'text')
        elements[7].set_attribute('type', 'file')
        when(browser).find_elements_by_id("test1").thenReturn(elements)

        result = finder.find(browser, "id=test1")
        self.assertEqual(result, elements)
        result = finder.find(browser, "id=test1", tag='input')
        self.assertEqual(result, [elements[1], elements[3], elements[5], elements[7]])
        result = finder.find(browser, "id=test1", tag='radio button')
        self.assertEqual(result, [elements[1]])
        result = finder.find(browser, "id=test1", tag='checkbox')
        self.assertEqual(result, [elements[3]])
        result = finder.find(browser, "id=test1", tag='text field')
        self.assertEqual(result, [elements[5]])
        result = finder.find(browser, "id=test1", tag='file upload')
        self.assertEqual(result, [elements[7]])

    def test_find_returns_bad_values(self):
        finder = ElementFinder()
        browser = mock()
        # selenium.webdriver.ie.webdriver.WebDriver sometimes returns these
        for bad_value in (None, {'': None}):
            for func_name in ('find_elements_by_id', 'find_elements_by_name',
                              'find_elements_by_xpath', 'find_elements_by_link_text',
                              'find_elements_by_css_selector', 'find_elements_by_tag_name'):
                when_find_func = getattr(when(browser), func_name)
                when_find_func(any()).thenReturn(bad_value)
            for locator in ("identifier=it", "id=it", "name=it", "xpath=//div",
                            "link=it", "css=div.it", "tag=div", "default"):
                result = finder.find(browser, locator)
                self.assertEqual(result, [])
                result = finder.find(browser, locator, tag='div')
                self.assertEqual(result, [])

    def _make_mock_elements(self, *tags):
        elements = []
        for tag in tags:
            element = self._make_mock_element(tag)
            elements.append(element)
        return elements

    def _make_mock_element(self, tag):
        element = mock()
        element.tag_name = tag
        element.attributes = {}

        def set_attribute(name, value):
            element.attributes[name] = value
        element.set_attribute = set_attribute

        def get_attribute(name):
            return element.attributes[name]
        element.get_attribute = get_attribute

        return element

########NEW FILE########
__FILENAME__ = test_tableelementfinder
import unittest
from Selenium2Library.locators import TableElementFinder
from mockito import *

class ElementFinderTests(unittest.TestCase):

    def test_find_with_implicit_css_locator(self):
        finder = TableElementFinder()
        browser = mock()
        when(browser).find_elements_by_css_selector("table#test1").thenReturn([])
        
        finder.find(browser, "test1")

        verify(browser).find_elements_by_css_selector("table#test1")

    def test_find_with_css_selector(self):
        finder = TableElementFinder()
        browser = mock()
        elements = self._make_mock_elements('table', 'table', 'table')
        when(browser).find_elements_by_css_selector("table#test1").thenReturn(elements)
        
        self.assertEqual(
            finder.find(browser, "css=table#test1"),
            elements[0])

        verify(browser).find_elements_by_css_selector("table#test1")

    def test_find_with_xpath_selector(self):
        finder = TableElementFinder()
        browser = mock()
        elements = self._make_mock_elements('table', 'table', 'table')
        when(browser).find_elements_by_xpath("//table[@id='test1']").thenReturn(elements)
        
        self.assertEqual(
            finder.find(browser, "xpath=//table[@id='test1']"),
            elements[0])

        verify(browser).find_elements_by_xpath("//table[@id='test1']")

    def test_find_with_content_constraint(self):
        finder = TableElementFinder()
        browser = mock()
        elements = self._make_mock_elements('td', 'td', 'td')
        elements[1].text = 'hi'
        when(browser).find_elements_by_css_selector("table#test1").thenReturn(elements)
        
        self.assertEqual(
            finder.find_by_content(browser, "test1", 'hi'),
            elements[1])

        verify(browser).find_elements_by_css_selector("table#test1")

    def test_find_with_null_content_constraint(self):
        finder = TableElementFinder()
        browser = mock()
        elements = self._make_mock_elements('td', 'td', 'td')
        elements[1].text = 'hi'
        when(browser).find_elements_by_css_selector("table#test1").thenReturn(elements)
        
        self.assertEqual(
            finder.find_by_content(browser, "test1", None),
            elements[0])

        verify(browser).find_elements_by_css_selector("table#test1")

    def test_find_by_content_with_css_locator(self):
        finder = TableElementFinder()
        browser = mock()
        when(browser).find_elements_by_css_selector("table#test1").thenReturn([])
        
        finder.find_by_content(browser, "css=table#test1", 'hi')

        verify(browser).find_elements_by_css_selector("table#test1")

    def test_find_by_content_with_xpath_locator(self):
        finder = TableElementFinder()
        browser = mock()
        when(browser).find_elements_by_xpath("//table[@id='test1']//*").thenReturn([])
        
        finder.find_by_content(browser, "xpath=//table[@id='test1']", 'hi')

        verify(browser).find_elements_by_xpath("//table[@id='test1']//*")

    def test_find_by_header_with_css_locator(self):
        finder = TableElementFinder()
        browser = mock()
        when(browser).find_elements_by_css_selector("table#test1 th").thenReturn([])
        
        finder.find_by_header(browser, "css=table#test1", 'hi')

        verify(browser).find_elements_by_css_selector("table#test1 th")

    def test_find_by_header_with_xpath_locator(self):
        finder = TableElementFinder()
        browser = mock()
        when(browser).find_elements_by_xpath("//table[@id='test1']//th").thenReturn([])
        
        finder.find_by_header(browser, "xpath=//table[@id='test1']", 'hi')

        verify(browser).find_elements_by_xpath("//table[@id='test1']//th")

    def test_find_by_footer_with_css_locator(self):
        finder = TableElementFinder()
        browser = mock()
        when(browser).find_elements_by_css_selector("table#test1 tfoot td").thenReturn([])
        
        finder.find_by_footer(browser, "css=table#test1", 'hi')

        verify(browser).find_elements_by_css_selector("table#test1 tfoot td")

    def test_find_by_footer_with_xpath_locator(self):
        finder = TableElementFinder()
        browser = mock()
        when(browser).find_elements_by_xpath("//table[@id='test1']//tfoot//td").thenReturn([])
        
        finder.find_by_footer(browser, "xpath=//table[@id='test1']", 'hi')

        verify(browser).find_elements_by_xpath("//table[@id='test1']//tfoot//td")

    def test_find_by_row_with_css_locator(self):
        finder = TableElementFinder()
        browser = mock()
        when(browser).find_elements_by_css_selector("table#test1 tr:nth-child(2)").thenReturn([])
        
        finder.find_by_row(browser, "css=table#test1", 2, 'hi')

        verify(browser).find_elements_by_css_selector("table#test1 tr:nth-child(2)")

    def test_find_by_row_with_xpath_locator(self):
        finder = TableElementFinder()
        browser = mock()
        when(browser).find_elements_by_xpath("//table[@id='test1']//tr[2]//*").thenReturn([])
        
        finder.find_by_row(browser, "xpath=//table[@id='test1']", 2, 'hi')

        verify(browser).find_elements_by_xpath("//table[@id='test1']//tr[2]//*")

    def test_find_by_col_with_css_locator(self):
        finder = TableElementFinder()
        browser = mock()
        when(browser).find_elements_by_css_selector("table#test1 tr td:nth-child(2)").thenReturn([])
        when(browser).find_elements_by_css_selector("table#test1 tr th:nth-child(2)").thenReturn([])
        
        finder.find_by_col(browser, "css=table#test1", 2, 'hi')

        verify(browser).find_elements_by_css_selector("table#test1 tr td:nth-child(2)")
        verify(browser).find_elements_by_css_selector("table#test1 tr th:nth-child(2)")

    def test_find_by_col_with_xpath_locator(self):
        finder = TableElementFinder()
        browser = mock()
        when(browser).find_elements_by_xpath("//table[@id='test1']//tr//*[self::td or self::th][2]").thenReturn([])
        
        finder.find_by_col(browser, "xpath=//table[@id='test1']", 2, 'hi')

        verify(browser).find_elements_by_xpath("//table[@id='test1']//tr//*[self::td or self::th][2]")

    def _make_mock_elements(self, *tags):
        elements = []
        for tag in tags:
            element = self._make_mock_element(tag)
            elements.append(element)
        return elements

    def _make_mock_element(self, tag):
        element = mock()
        element.tag_name = tag
        element.attributes = {}
        element.text = None

        def set_attribute(name, value):
            element.attributes[name] = value
        element.set_attribute = set_attribute

        def get_attribute(name):
            return element.attributes[name]
        element.get_attribute = get_attribute

        return element

########NEW FILE########
__FILENAME__ = test_windowmanager
import unittest
import os
from Selenium2Library.locators import WindowManager
from mockito import *
import uuid
from selenium.common.exceptions import NoSuchWindowException

class WindowManagerTests(unittest.TestCase):

    def test_select_with_invalid_prefix(self):
        manager = WindowManager()
        browser = mock()
        try:
            self.assertRaises(ValueError, manager.select, browser, "something=test1")
        except ValueError as e:
            self.assertEqual(e.message, "Window locator with prefix 'something' is not supported")

    def test_select_with_null_browser(self):
        manager = WindowManager()
        self.assertRaises(AssertionError,
            manager.select, None, "name=test1")

    def test_select_by_title(self):
        manager = WindowManager()
        browser = self._make_mock_browser(
            { 'name': 'win1', 'title': "Title 1", 'url': 'http://localhost/page1.html' },
            { 'name': 'win2', 'title': "Title 2", 'url': 'http://localhost/page2.html' },
            { 'name': 'win3', 'title': "Title 3", 'url': 'http://localhost/page3.html' })

        manager.select(browser, "title=Title 2")
        self.assertEqual(browser.current_window.name, 'win2')

    def test_select_by_title_sloppy_match(self):
        manager = WindowManager()
        browser = self._make_mock_browser(
            { 'name': 'win1', 'title': "Title 1", 'url': 'http://localhost/page1.html' },
            { 'name': 'win2', 'title': "Title 2", 'url': 'http://localhost/page2.html' },
            { 'name': 'win3', 'title': "Title 3", 'url': 'http://localhost/page3.html' })

        manager.select(browser, "title= tItLe 2  ")
        self.assertEqual(browser.current_window.name, 'win2')

    def test_select_by_title_with_multiple_matches(self):
        manager = WindowManager()
        browser = self._make_mock_browser(
            { 'name': 'win1', 'title': "Title 1", 'url': 'http://localhost/page1.html' },
            { 'name': 'win2a', 'title': "Title 2", 'url': 'http://localhost/page2a.html' },
            { 'name': 'win2b', 'title': "Title 2", 'url': 'http://localhost/page2b.html' })

        manager.select(browser, "title=Title 2")
        self.assertEqual(browser.current_window.name, 'win2a')

    def test_select_by_title_no_match(self):
        manager = WindowManager()
        browser = self._make_mock_browser(
            { 'name': 'win1', 'title': "Title 1", 'url': 'http://localhost/page1.html' },
            { 'name': 'win2', 'title': "Title 2", 'url': 'http://localhost/page2.html' },
            { 'name': 'win3', 'title': "Title 3", 'url': 'http://localhost/page3.html' })

        try:
            self.assertRaises(ValueError, manager.select, browser, "title=Title -1")
        except ValueError as e:
            self.assertEqual(e.message, "Unable to locate window with title 'Title -1'")

    def test_select_by_name(self):
        manager = WindowManager()
        browser = self._make_mock_browser(
            { 'name': 'win1', 'title': "Title 1", 'url': 'http://localhost/page1.html' },
            { 'name': 'win2', 'title': "Title 2", 'url': 'http://localhost/page2.html' },
            { 'name': 'win3', 'title': "Title 3", 'url': 'http://localhost/page3.html' })

        manager.select(browser, "name=win2")
        self.assertEqual(browser.current_window.name, 'win2')

    def test_select_by_name_sloppy_match(self):
        manager = WindowManager()
        browser = self._make_mock_browser(
            { 'name': 'win1', 'title': "Title 1", 'url': 'http://localhost/page1.html' },
            { 'name': 'win2', 'title': "Title 2", 'url': 'http://localhost/page2.html' },
            { 'name': 'win3', 'title': "Title 3", 'url': 'http://localhost/page3.html' })

        manager.select(browser, "name= win2  ")
        self.assertEqual(browser.current_window.name, 'win2')

    def test_select_by_name_with_bad_case(self):
        manager = WindowManager()
        browser = self._make_mock_browser(
            { 'name': 'win1', 'title': "Title 1", 'url': 'http://localhost/page1.html' },
            { 'name': 'win2', 'title': "Title 2", 'url': 'http://localhost/page2.html' },
            { 'name': 'win3', 'title': "Title 3", 'url': 'http://localhost/page3.html' })

        manager.select(browser, "name=Win2")
        self.assertEqual(browser.current_window.name, 'win2')

    def test_select_by_name_no_match(self):
        manager = WindowManager()
        browser = self._make_mock_browser(
            { 'name': 'win1', 'title': "Title 1", 'url': 'http://localhost/page1.html' },
            { 'name': 'win2', 'title': "Title 2", 'url': 'http://localhost/page2.html' },
            { 'name': 'win3', 'title': "Title 3", 'url': 'http://localhost/page3.html' })

        try:
            self.assertRaises(ValueError, manager.select, browser, "name=win-1")
        except ValueError as e:
            self.assertEqual(e.message, "Unable to locate window with name 'win-1'")

    def test_select_by_url(self):
        manager = WindowManager()
        browser = self._make_mock_browser(
            { 'name': 'win1', 'title': "Title 1", 'url': 'http://localhost/page1.html' },
            { 'name': 'win2', 'title': "Title 2", 'url': 'http://localhost/page2.html' },
            { 'name': 'win3', 'title': "Title 3", 'url': 'http://localhost/page3.html' })

        manager.select(browser, "url=http://localhost/page2.html")
        self.assertEqual(browser.current_window.name, 'win2')

    def test_select_by_url_sloppy_match(self):
        manager = WindowManager()
        browser = self._make_mock_browser(
            { 'name': 'win1', 'title': "Title 1", 'url': 'http://localhost/page1.html' },
            { 'name': 'win2', 'title': "Title 2", 'url': 'http://localhost/page2.html' },
            { 'name': 'win3', 'title': "Title 3", 'url': 'http://localhost/page3.html' })

        manager.select(browser, "url=   http://LOCALHOST/page2.html  ")
        self.assertEqual(browser.current_window.name, 'win2')

    def test_select_by_url_with_multiple_matches(self):
        manager = WindowManager()
        browser = self._make_mock_browser(
            { 'name': 'win1', 'title': "Title 1", 'url': 'http://localhost/page1.html' },
            { 'name': 'win2a', 'title': "Title 2a", 'url': 'http://localhost/page2.html' },
            { 'name': 'win2b', 'title': "Title 2b", 'url': 'http://localhost/page2.html' })

        manager.select(browser, "url=http://localhost/page2.html")
        self.assertEqual(browser.current_window.name, 'win2a')

    def test_select_by_url_no_match(self):
        manager = WindowManager()
        browser = self._make_mock_browser(
            { 'name': 'win1', 'title': "Title 1", 'url': 'http://localhost/page1.html' },
            { 'name': 'win2', 'title': "Title 2", 'url': 'http://localhost/page2.html' },
            { 'name': 'win3', 'title': "Title 3", 'url': 'http://localhost/page3.html' })

        try:
            self.assertRaises(ValueError, manager.select, browser, "url=http://localhost/page-1.html")
        except ValueError as e:
            self.assertEqual(e.message, "Unable to locate window with URL 'http://localhost/page-1.html'")

    def test_select_with_null_locator(self):
        manager = WindowManager()
        browser = self._make_mock_browser(
            { 'name': 'win1', 'title': "Title 1", 'url': 'http://localhost/page1.html' },
            { 'name': 'win2', 'title': "Title 2", 'url': 'http://localhost/page2.html' },
            { 'name': 'win3', 'title': "Title 3", 'url': 'http://localhost/page3.html' })

        manager.select(browser, "name=win2")
        self.assertEqual(browser.current_window.name, 'win2')
        manager.select(browser, None)
        self.assertEqual(browser.current_window.name, 'win1')

    def test_select_with_null_string_locator(self):
        manager = WindowManager()
        browser = self._make_mock_browser(
            { 'name': 'win1', 'title': "Title 1", 'url': 'http://localhost/page1.html' },
            { 'name': 'win2', 'title': "Title 2", 'url': 'http://localhost/page2.html' },
            { 'name': 'win3', 'title': "Title 3", 'url': 'http://localhost/page3.html' })

        manager.select(browser, "name=win2")
        self.assertEqual(browser.current_window.name, 'win2')
        manager.select(browser, "null")
        self.assertEqual(browser.current_window.name, 'win1')

    def test_select_with_empty_locator(self):
        manager = WindowManager()
        browser = self._make_mock_browser(
            { 'name': 'win1', 'title': "Title 1", 'url': 'http://localhost/page1.html' },
            { 'name': 'win2', 'title': "Title 2", 'url': 'http://localhost/page2.html' },
            { 'name': 'win3', 'title': "Title 3", 'url': 'http://localhost/page3.html' })

        manager.select(browser, "name=win2")
        self.assertEqual(browser.current_window.name, 'win2')
        manager.select(browser, "")
        self.assertEqual(browser.current_window.name, 'win1')

    def test_select_with_main_constant_locator(self):
        manager = WindowManager()
        browser = self._make_mock_browser(
            { 'name': 'win1', 'title': "Title 1", 'url': 'http://localhost/page1.html' },
            { 'name': 'win2', 'title': "Title 2", 'url': 'http://localhost/page2.html' },
            { 'name': 'win3', 'title': "Title 3", 'url': 'http://localhost/page3.html' })

        manager.select(browser, "name=win2")
        self.assertEqual(browser.current_window.name, 'win2')
        manager.select(browser, "main")
        self.assertEqual(browser.current_window.name, 'win1')

    def test_select_by_default_with_name(self):
        manager = WindowManager()
        browser = self._make_mock_browser(
            { 'name': 'win1', 'title': "Title 1", 'url': 'http://localhost/page1.html' },
            { 'name': 'win2', 'title': "Title 2", 'url': 'http://localhost/page2.html' },
            { 'name': 'win3', 'title': "Title 3", 'url': 'http://localhost/page3.html' })

        manager.select(browser, "win2")
        self.assertEqual(browser.current_window.name, 'win2')

    def test_select_by_default_with_title(self):
        manager = WindowManager()
        browser = self._make_mock_browser(
            { 'name': 'win1', 'title': "Title 1", 'url': 'http://localhost/page1.html' },
            { 'name': 'win2', 'title': "Title 2", 'url': 'http://localhost/page2.html' },
            { 'name': 'win3', 'title': "Title 3", 'url': 'http://localhost/page3.html' })

        manager.select(browser, "Title 2")
        self.assertEqual(browser.current_window.name, 'win2')

    def test_select_by_default_no_match(self):
        manager = WindowManager()
        browser = self._make_mock_browser(
            { 'name': 'win1', 'title': "Title 1", 'url': 'http://localhost/page1.html' },
            { 'name': 'win2', 'title': "Title 2", 'url': 'http://localhost/page2.html' },
            { 'name': 'win3', 'title': "Title 3", 'url': 'http://localhost/page3.html' })

        try:
            self.assertRaises(ValueError, manager.select, browser, "win-1")
        except ValueError as e:
            self.assertEqual(context.exception.message, "Unable to locate window with name or title 'win-1'")

    def test_select_with_sloppy_prefix(self):
        manager = WindowManager()
        browser = self._make_mock_browser(
            { 'name': 'win1', 'title': "Title 1", 'url': 'http://localhost/page1.html' },
            { 'name': 'win2', 'title': "Title 2", 'url': 'http://localhost/page2.html' },
            { 'name': 'win3', 'title': "Title 3", 'url': 'http://localhost/page3.html' })

        manager.select(browser, "name=win2")
        self.assertEqual(browser.current_window.name, 'win2')
        manager.select(browser, "nAmE=win2")
        self.assertEqual(browser.current_window.name, 'win2')
        manager.select(browser, " name  =win2")
        self.assertEqual(browser.current_window.name, 'win2')

    def test_get_window_ids(self):
        manager = WindowManager()
        browser = self._make_mock_browser(
            { 'id': 'win1', 'name': 'win1', 'title': "Title 1", 'url': 'http://localhost/page1.html' },
            { 'id': 'win2', 'name': 'win2', 'title': "Title 2", 'url': 'http://localhost/page2.html' },
            { 'name': 'win3', 'title': "Title 3", 'url': 'http://localhost/page3.html' })

        self.assertEqual(
            manager.get_window_ids(browser),
            [ 'win1', 'win2', 'undefined' ])

    def test_get_window_names(self):
        manager = WindowManager()
        browser = self._make_mock_browser(
            { 'name': 'win1', 'title': "Title 1", 'url': 'http://localhost/page1.html' },
            { 'name': 'win2', 'title': "Title 2", 'url': 'http://localhost/page2.html' },
            { 'name': 'win3', 'title': "Title 3", 'url': 'http://localhost/page3.html' })

        self.assertEqual(
            manager.get_window_names(browser),
            [ 'win1', 'win2', 'win3' ])

    def test_get_window_titles(self):
        manager = WindowManager()
        browser = self._make_mock_browser(
            { 'name': 'win1', 'title': "Title 1", 'url': 'http://localhost/page1.html' },
            { 'name': 'win2', 'title': "Title 2", 'url': 'http://localhost/page2.html' },
            { 'name': 'win3', 'title': "Title 3", 'url': 'http://localhost/page3.html' })

        self.assertEqual(
            manager.get_window_titles(browser),
            [ 'Title 1', 'Title 2', 'Title 3' ])

    def _make_mock_browser(self, *window_specs):
        browser = mock()

        windows = []
        window_handles = []
        first_window = None
        for window_spec in window_specs:
            window = mock()
            window.handle = uuid.uuid4().hex
            window.id = window_spec.get('id')
            if window.id is None:
                window.id = 'undefined'
            window.name = window_spec['name']
            window.title = window_spec['title']
            window.url = window_spec['url']

            windows.append(window)
            window_handles.append(window.handle)

            if first_window is None:
                first_window = window

        def switch_to_window(handle_or_name):
            if handle_or_name == '':
                browser.current_window = first_window
                return
            for window in windows:
                if window.handle == handle_or_name or window.name == handle_or_name:
                    browser.current_window = window
                    return
            raise NoSuchWindowException(u'Unable to locate window "' + handle_or_name + '"')

        browser.current_window = first_window
        browser.get_current_window_handle = lambda: browser.current_window.handle
        browser.get_title = lambda: browser.current_window.title
        browser.get_current_url = lambda: browser.current_window.url
        browser.get_window_handles = lambda: window_handles
        browser.switch_to_window = switch_to_window
        browser.get_current_window_info = lambda: (
            browser.current_window.handle, browser.current_window.id, browser.current_window.name,
            browser.current_window.title, browser.current_window.url)

        return browser

########NEW FILE########
__FILENAME__ = test_browsercache
import unittest
import os
from Selenium2Library.utils import BrowserCache
from mockito import *

class BrowserCacheTests(unittest.TestCase): 

    def test_no_current_message(self):
        cache = BrowserCache()
        try:
            self.assertRaises(RuntimeError, cache.current.anyMember())
        except RuntimeError as e:
            self.assertEqual(e.message, "No current browser")

    def test_browsers_property(self):
        cache = BrowserCache()

        browser1 = mock()
        browser2 = mock()
        browser3 = mock()

        cache.register(browser1)
        cache.register(browser2)
        cache.register(browser3)

        self.assertEqual(len(cache.browsers), 3)
        self.assertEqual(cache.browsers[0], browser1)
        self.assertEqual(cache.browsers[1], browser2)
        self.assertEqual(cache.browsers[2], browser3)

    def test_get_open_browsers(self):
        cache = BrowserCache()

        browser1 = mock()
        browser2 = mock()
        browser3 = mock()

        cache.register(browser1)
        cache.register(browser2)
        cache.register(browser3)

        browsers = cache.get_open_browsers()
        self.assertEqual(len(browsers), 3)
        self.assertEqual(browsers[0], browser1)
        self.assertEqual(browsers[1], browser2)
        self.assertEqual(browsers[2], browser3)

        cache.close()
        browsers = cache.get_open_browsers()
        self.assertEqual(len(browsers), 2)
        self.assertEqual(browsers[0], browser1)
        self.assertEqual(browsers[1], browser2)

    def test_close(self):
        cache = BrowserCache()
        browser = mock()
        cache.register(browser)

        verify(browser, times=0).quit() # sanity check
        cache.close()
        verify(browser, times=1).quit()

    def test_close_only_called_once(self):
        cache = BrowserCache()

        browser1 = mock()
        browser2 = mock()
        browser3 = mock()

        cache.register(browser1)
        cache.register(browser2)
        cache.register(browser3)

        cache.close()
        verify(browser3, times=1).quit()

        cache.close_all()
        verify(browser1, times=1).quit()
        verify(browser2, times=1).quit()
        verify(browser3, times=1).quit()

########NEW FILE########
__FILENAME__ = test_package
import unittest
from Selenium2Library import utils

class UtilsPackageTests(unittest.TestCase):

    def test_escape_xpath_value_with_apos(self):
        self.assertEqual(
            utils.escape_xpath_value("test '1'"),
            "\"test '1'\"")

    def test_escape_xpath_value_with_quote(self):
        self.assertEqual(
            utils.escape_xpath_value("test \"1\""),
            "'test \"1\"'")

    def test_escape_xpath_value_with_quote_and_apos(self):
        self.assertEqual(
            utils.escape_xpath_value("test \"1\" and '2'"),
            "concat('test \"1\" and ', \"'\", '2', \"'\", '')")

########NEW FILE########
