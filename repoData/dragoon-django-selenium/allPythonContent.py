__FILENAME__ = jenkins_runner
from django.dispatch import receiver
from django_jenkins.runner import CITestSuiteRunner
from django_jenkins.signals import build_suite
from django_selenium.selenium_runner import SeleniumTestRunner

class JenkinsTestRunner(CITestSuiteRunner, SeleniumTestRunner):
    def __init__(self, **kwargs):
        super(JenkinsTestRunner, self).__init__(**kwargs)
        self.selenium = True

    def build_suite(self, test_labels, extra_tests=None, **kwargs):
        # args and kwargs saved in instance to use in the signal below
        self.test_labels = test_labels
        self.build_suite_kwargs = kwargs
        suite = CITestSuiteRunner.build_suite(self, test_labels, extra_tests, **kwargs)
        return suite

    def run_tests(self, test_labels, extra_tests=None, **kwargs):
        results = super(JenkinsTestRunner, self).run_tests(test_labels, extra_tests, **kwargs)
        return results


@receiver(build_suite)
def add_selenium_tests(sender, suite, **kwargs):
    ''' Add the selenium test under Jenkins environment '''
    sel_suite = sender._get_seltests(sender.test_labels, **sender.build_suite_kwargs)
    suite.addTest(sel_suite)


########NEW FILE########
__FILENAME__ = livetestcases
from django.test import LiveServerTestCase

from django_selenium.testcases import MyDriver
from django_selenium import settings


class SeleniumLiveTestCase(LiveServerTestCase):
    """Selenium TestCase for django 1.4 with custom MyDriver"""

    @classmethod
    def setUpClass(cls):
        cls.driver = MyDriver()
        super(SeleniumLiveTestCase, cls).setUpClass()

    def setUp(self):
        self.driver.live_server_url = self.live_server_url

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()
        super(SeleniumLiveTestCase, cls).tearDownClass()

########NEW FILE########
__FILENAME__ = test_selenium
from optparse import make_option
import sys

from django.conf import settings
from django.core.management.commands import test
from django.test.utils import get_runner

from django_selenium import settings as selenium_settings


class Command(test.Command):
    # TODO: update when django 1.4 is out, it will have custom options available
    option_list = test.Command.option_list + (
        make_option('--selenium', action='store_true', dest='selenium', default=False,
            help='Run selenium tests during test execution\n'
                 '(requires access to 4444 and $SELENIUM_TESTSERVER_PORT ports, java and running X server'),
        make_option('--selenium-only', action='store_true', dest='selenium_only', default=False,
            help='Run only selenium tests (implies --selenium)')
    )

    def handle(self, *test_labels, **options):

        verbosity = int(options.get('verbosity', 1))
        interactive = options.get('interactive', True)
        failfast = options.get('failfast', False)
        selenium = options.get('selenium', False)
        selenium_only = options.get('selenium_only', False)
        if selenium_only:
            selenium = True

        TestRunner = get_runner(settings)
        test_runner = TestRunner(verbosity=verbosity, interactive=interactive, failfast=failfast,
                                 selenium=selenium, selenium_only=selenium_only)
        failures = test_runner.run_tests(test_labels)
        if failures:
            sys.exit(bool(failures))

########NEW FILE########
__FILENAME__ = selenium_runner
import os
import socket
import subprocess
import time
import signal
import unittest

from django_selenium import settings
from django.test.testcases import TestCase
from django_selenium.selenium_server import get_test_server

try:
    from django.test.simple import reorder_suite
except ImportError:
    from django.test.runner import reorder_suite

try:
    from django.test.simple import DjangoTestSuiteRunner
except ImportError:
    msg = """

    django-selenium requires django 1.2+.
    """
    raise ImportError(msg)

SELTEST_MODULE = 'seltests'

def wait_until_connectable(port, timeout=120):
    """Blocks until the specified port is connectable."""

    def is_connectable(port):
        """Tries to connect to the specified port."""
        try:
            socket_ = socket.create_connection(("127.0.0.1", port), 1)
            socket_.close()
            return True
        except socket.error:
            return False

    count = 0
    while not is_connectable(port):
        if count >= timeout:
            return False
        count += 5
        time.sleep(5)
    return True

class SeleniumTestRunner(DjangoTestSuiteRunner):
    """
    Test runner with Selenium support
    """

    def __init__(self, **kwargs):
        super(SeleniumTestRunner, self).__init__(**kwargs)
        self.selenium = kwargs.get('selenium')
        self.selenium_only = kwargs.get('selenium_only')

        self.test_server = None
        self.selenium_server = None

    def _is_start_selenium_server(self):
        return bool((settings.SELENIUM_DRIVER == 'Remote') and settings.SELENIUM_PATH)

    def build_suite(self, test_labels, *args, **kwargs):
        suite = unittest.TestSuite()

        if not self.selenium_only:
            suite = super(SeleniumTestRunner, self).build_suite(test_labels, *args, **kwargs)

        if self.selenium:
            # Hack to exclude doctests from selenium-only, they are already present
            from django.db.models import get_app
            if test_labels:
                for label in test_labels:
                    if not '.' in label:
                        app = get_app(label)
                        setattr(app, 'suite', unittest.TestSuite)


            sel_suite = self._get_seltests(test_labels, *args, **kwargs)
            suite.addTest(sel_suite)

        return reorder_suite(suite, (TestCase,))

    def _get_seltests(self, *args, **kwargs):
        # Add tests from seltests.py modules
        import django.test.simple
        orig_test_module = django.test.simple.TEST_MODULE
        django.test.simple.TEST_MODULE = SELTEST_MODULE
        try:
            sel_suite = DjangoTestSuiteRunner.build_suite(self, *args, **kwargs)
        finally:
             django.test.simple.TEST_MODULE = orig_test_module

        return sel_suite


    def _start_selenium(self):
        if self.selenium:

            # Set display variable
            os.environ['DISPLAY'] = settings.SELENIUM_DISPLAY
            # Start test server
            self.test_server = get_test_server()
            if self._is_start_selenium_server():
                # Start selenium server
                self.selenium_server = subprocess.Popen(('java -jar %s' % settings.SELENIUM_PATH).split())

                # Waiting for server to be ready
                if not wait_until_connectable(4444):
                    self.selenium_server.kill()
                    self.test_server.stop()
                    assert False, "selenium server does not respond"

    def _stop_selenium(self):
        if self.selenium:
            # Stop selenium server
            if self._is_start_selenium_server():
                selenium_server = self.selenium_server
                selenium_server.send_signal(signal.SIGINT)
                if selenium_server.poll() is None:
                    selenium_server.kill()
                    selenium_server.wait()
            # Stop test server
            if self.test_server:
                self.test_server.stop()

    def run_tests(self, test_labels, extra_tests=None, **kwargs):
        self._start_selenium()
        try:
            results = super(SeleniumTestRunner, self).run_tests(test_labels, extra_tests, **kwargs)
        finally:
            self._stop_selenium()

        return results

########NEW FILE########
__FILENAME__ = selenium_server
import socket
from django.core.servers import basehttp
from django.core.handlers.wsgi import WSGIHandler
from django.contrib.staticfiles.handlers import StaticFilesHandler

import threading
from django_selenium import settings

try:
    from django.core.servers.basehttp import WSGIServerException \
                                             as wsgi_exec_error
except ImportError:
    import socket
    wsgi_exec_error = socket.error                                            

class StoppableWSGIServer(basehttp.WSGIServer):
    """WSGIServer with short timeout"""

    def server_bind(self):
        """Sets timeout to 1 second."""
        basehttp.WSGIServer.server_bind(self)
        self.socket.settimeout(1)

    def get_request(self):
        """Checks for timeout when getting request."""
        try:
            sock, address = self.socket.accept()
            sock.settimeout(None)
            return (sock, address)
        except socket.timeout:
            raise

class TestServerThread(threading.Thread):
    """Thread for running a http server."""

    def __init__(self, address, port):
        self.address = address
        self.port = port
        self._start_event = threading.Event()
        self._stop_event = threading.Event()
        self._activate_event = threading.Event()
        self._ready_event = threading.Event()
        self._error = None
        super(TestServerThread, self).__init__()

    def run(self):
        try:
            handler = StaticFilesHandler(WSGIHandler())
            def test_app(environ, start_response):
                if environ['REQUEST_METHOD'] == 'HEAD':
                    start_response('200 OK', [])
                    return ''
                if environ['PATH_INFO'] == '/favicon.ico':
                    start_response('404 Not Found', [])
                    return ''
                return handler(environ, start_response)
            server_address = (self.address, self.port)
            httpd = StoppableWSGIServer(server_address, basehttp.WSGIRequestHandler)
            httpd.set_app(test_app)
            self._start_event.set()
        except wsgi_exec_error, e:
            self.error = e
            self._start_event.set()
            return
        self._activate_event.set()
        # Loop until we get a stop event.
        while not self._stop_event.is_set():
            if self._activate_event.wait(5):
                httpd.handle_request()
            self._ready_event.set()

    def stop(self, timeout=None):
        """Stop the thread and wait for it to finish."""
        self._stop_event.set()
        self.join(timeout)

    def activate(self):
        """Activate the server and wait until it changes the status."""
        self._activate_event.set()
        self._ready_event.clear()
        if not self._ready_event.wait(settings.SELENIUM_TEST_SERVER_TIMEOUT):
            raise Exception('Test server hung. Timed out after %i seconds' % settings.SELENIUM_TEST_SERVER_TIMEOUT)

    def deactivate(self):
        """Deactivate the server and wait until it finishes processing requests."""
        self._activate_event.clear()
        self._ready_event.clear()
        if not self._ready_event.wait(settings.SELENIUM_TEST_SERVER_TIMEOUT):
            raise Exception('Test server hung. Timed out after %i seconds' % settings.SELENIUM_TEST_SERVER_TIMEOUT)


def get_test_server():
    """ TestServer lazy initialization with singleton"""

    #TODO: make this lazy initialization thread-safe
    if '__instance' not in globals():
        server_thread = TestServerThread(settings.SELENIUM_TESTSERVER_HOST, settings.SELENIUM_TESTSERVER_PORT)
        server_thread.start()
        server_thread._start_event.wait()
        if server_thread._error:
            raise server_thread._error
        globals()['__instance'] = server_thread

    return globals()['__instance']

########NEW FILE########
__FILENAME__ = settings
from django.conf import settings

# Specify the selenium test runner
SELENIUM_TEST_RUNNER = getattr(settings, 'SELENIUM_TEST_RUNNER',
                             'django_selenium.selenium_runner.SeleniumTestRunner')

SELENIUM_TIMEOUT = getattr(settings, 'SELENIUM_TIMEOUT', 120)
SELENIUM_DRIVER_TIMEOUT = getattr(settings, 'SELENIUM_DRIVER_TIMEOUT', 10)
# Specify max waiting time for server to finish processing request and deactivates
SELENIUM_TEST_SERVER_TIMEOUT = getattr(settings, 'SELENIUM_TEST_SERVER_TIMEOUT', 300)

#------------------ LOCAL ----------------------------------
SELENIUM_TESTSERVER_HOST = getattr(settings, 'SELENIUM_TESTSERVER_HOST', 'localhost')
SELENIUM_TESTSERVER_PORT = getattr(settings, 'SELENIUM_TESTSERVER_PORT', 8011)
SELENIUM_HOST = getattr(settings, 'SELENIUM_HOST', None)
SELENIUM_PORT = getattr(settings, 'SELENIUM_PORT', 4444)

SELENIUM_DISPLAY = getattr(settings, 'SELENIUM_DISPLAY', ':0')
# Set the drivers that you want to run your tests against
SELENIUM_DRIVER = getattr(settings, 'SELENIUM_DRIVER', 'Firefox')
#------------------------------------------------------------

#----------------- REMOTE ------------------------------------
# YOU SHOULD SET THESE IN YOUR LOCAL SETTINGS FILE
# Path to selenium-server JAR,
# for example: "/home/dragoon/myproject/selenium-server/selenium-server.jar"
SELENIUM_PATH=getattr(settings, 'SELENIUM_PATH', None)
SELENIUM_CAPABILITY =  getattr(settings, 'SELENIUM_CAPABILITY', 'FIREFOX')
#SELENIUM_DRIVER = 'Remote'
#SELENIUM_HOST = getattr(settings, 'SELENIUM_HOST', 'selenium-hub.example.com')
#SELENIUM_TESTSERVER_HOST = getattr(settings, 'SELENIUM_TESTSERVER_HOST', '0.0.0.0')
#------------------------------------------------------------

########NEW FILE########
__FILENAME__ = testcases
from functools import wraps
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
import time
import os

from django.db import transaction
from django.core.urlresolvers import reverse
from django.test import TransactionTestCase
from django.utils.html import strip_tags

from django_selenium import settings, selenium_server


def wait(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        i = settings.SELENIUM_DRIVER_TIMEOUT
        if 'timeout' in kwargs:
            i = kwargs.pop('timeout')
        res = func(self, *args, **kwargs)
        while not res and i:
            time.sleep(1)
            res = func(self, *args, **kwargs)
            i -= 1
        return res
    return wrapper


class SeleniumElement(object):

    def __init__(self, elements, selector):
        """Keep selector for key errors"""
        self.elements = elements
        self.selector = selector

    def __getattribute__(self, name):
        """
        Pass ``__getattribute__`` directly to the first array element.
        """
        try:
            attr = object.__getattribute__(self, 'elements')[0].__getattribute__(name)
        except IndexError:
            raise NoElementException(u'No elements found for selector: {0}'\
                .format(object.__getattribute__(self, 'selector')))
        return attr

    def __getitem__(self, key):
        """Return item from the internal sequence, bypassing ``__getattribute__``"""
        return object.__getattribute__(self, 'elements')[key]


class NoElementException(Exception):
    pass


class MyDriver(object):
    def __init__(self):
        driver = getattr(webdriver, settings.SELENIUM_DRIVER, None)
        assert driver, "settings.SELENIUM_DRIVER contains non-existing driver"
        if driver is webdriver.Remote:
            if isinstance(settings.SELENIUM_CAPABILITY, dict):
                capability = settings.SELENIUM_CAPABILITY
            else:
                capability = getattr(webdriver.DesiredCapabilities, settings.SELENIUM_CAPABILITY, None)
                assert capability, 'settings.SELENIUM_CAPABILITY contains non-existing capability'
            self.driver = driver('http://%s:%d/wd/hub' % (settings.SELENIUM_HOST, settings.SELENIUM_PORT), capability)
        else:
            self.driver = driver()
        self.live_server_url = 'http://%s:%s' % (settings.SELENIUM_TESTSERVER_HOST , str(settings.SELENIUM_TESTSERVER_PORT))
        self.text = ''

    def __getattribute__(self, name):
        try:
            attr = object.__getattribute__(self, name)
        except AttributeError:
            attr = self.driver.__getattribute__(name)
        return attr

    def _wait_for_page_source(self):
        try:
            page_source = self.page_source
            time.sleep(1)
            while page_source != self.page_source:
                page_source = self.page_source
                time.sleep(1)
            self.update_text()
        except WebDriverException:
            pass

    def authorize(self, username, password):
        self.open_url(reverse('login'))
        self.type_in("#id_username", username)
        self.type_in("#id_password", password)
        self.click("#login-form [type='submit']")

    def update_text(self):
        """
        Update text content of the current page.
        Use in case you cannot find text that is actually present on the page.
        """
        self.text = strip_tags(unicode(self.page_source))

    def open_url(self, url):
        """Open the specified url and wait until page source is fully loaded."""
        self.get('%s%s' % (self.live_server_url, url))
        self._wait_for_page_source()

    def click(self, selector):
        """
        :param selector: CSS selector of the element to be clicked on.
        Performs click on the specified CSS selector.
        Also refreshes page text.
        """
        self.find(selector).click()
        self._wait_for_page_source()

    def click_and_wait(self, selector, newselector):
        """
        :param selector: CSS selector of the element to be clicked on.
        :param newselector: CSS selector of the new element to wait for.
        Calls click function and then waits for element presense on the updated page.
        """
        self.click(selector)
        return self.wait_element_present(newselector)

    def is_element_present(self, selector):
        """Check if one or more elements specified by CSS selector are present on the current page."""
        return len(self.find_elements_by_css_selector(selector)) > 0

    def is_text_present(self, text):
        """Check if specified text is present on the current page."""
        return text in self.text

    def get_alert_text(self):
        """
        Get text of the current alert and close it.
        :returns: alert text
        """
        alert = self.switch_to_alert()
        # Selenium can return either dict or text,
        # TODO: Need to investigate why
        try:
            text = alert.text['text']
        except TypeError:
            text = alert.text
        alert.dismiss()
        self.switch_to_default_content()
        self.update_text()
        return text

    def get_text(self, selector):
        return self.find(selector).text

    def drop_image(self, file_path, droparea_selector, append_to):
        """Drop image to the element specified by selector"""
        self.execute_script("file_input = window.$('<input/>').attr({id: 'file_input', type:'file'}).appendTo('" + append_to + "');")
        self.find('#file_input').send_keys(os.path.join(os.getcwd(), file_path))
        self.execute_script('fileList = Array();fileList.push(file_input.get(0).files[0]);')
        self.execute_script("e = $.Event('drop'); e.originalEvent = {dataTransfer : { files : fileList } }; $('" + droparea_selector + "').trigger(e);")
        self.execute_script("$('#file_input').remove()")

    @wait
    def wait_for_text(self, selector, text):
        return text in self.find(selector).text

    @wait
    def wait_for_visible(self, selector, visible=True):
        return self.find(selector).is_displayed() == visible

    @wait
    def wait_element_present(self, selector, present=True):
        return self.is_element_present(selector) == present

    def get_title(self):
        return self.title

    def get_value(self, selector):
        return self.find(selector).get_attribute('value')

    def find(self, cssselector):
        """
        :returns: element specified by a CSS selector ``cssselector``
        :rtype: SeleniumElement
        """
        return SeleniumElement(self.find_elements_by_css_selector(cssselector), cssselector)

    def select(self, selector, value):
        self.click(selector + (" option[value='%s']" % value))

    def type_in(self, selector, text):
        elem = self.find(selector)
        elem.clear()
        elem.send_keys(text)


class SeleniumTestCase(TransactionTestCase):

    def __getattribute__(self, name):
        try:
            attr = object.__getattribute__(self, name)
        except AttributeError:
            attr = object.__getattribute__(self, 'driver').__getattribute__(name)
        return attr

    def _fixture_setup(self):
        test_server = selenium_server.get_test_server()
        test_server.deactivate()
        transaction.commit_unless_managed()
        transaction.enter_transaction_management()
        transaction.managed(True)
        super(SeleniumTestCase, self)._fixture_setup()
        transaction.commit()
        transaction.leave_transaction_management()
        test_server.activate()

    def setUp(self):
        import socket
        socket.setdefaulttimeout(settings.SELENIUM_TIMEOUT)
        self.driver = MyDriver()

    def tearDown(self):
        self.driver.quit()

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# django-selenium documentation build configuration file, created by
# sphinx-quickstart on Thu Feb 21 14:51:52 2013.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
sys.path.insert(0, os.path.abspath('../django_selenium'))
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.coverage', 'sphinx.ext.ifconfig', 'sphinx.ext.viewcode']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'django-selenium'
copyright = u'2013, Roman Prokofyev & Contributors'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.9.5'
# The full version, including alpha/beta/rc tags.
release = '0.9.5'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build']

# The reST default role (used for this markup: `text`) to use for all documents.
#default_role = None

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

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'default'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'django-seleniumdoc'


# -- Options for LaTeX output --------------------------------------------------

latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
#'papersize': 'letterpaper',

# The font size ('10pt', '11pt' or '12pt').
#'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
#'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'django-selenium.tex', u'django-selenium Documentation',
   u'Roman Prokofyev', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'django-selenium', u'django-selenium Documentation',
     [u'Roman Prokofyev'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'django-selenium', u'django-selenium Documentation',
   u'Roman Prokofyev', 'django-selenium', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

########NEW FILE########
__FILENAME__ = forms
from django import forms


class SampleSearchForm(forms.Form):
    """Search form for test purposes"""
    query = forms.CharField(widget=forms.TextInput(attrs={'class': 'input-xlarge search-query',
                                                          'autocomplete': 'off'}))

########NEW FILE########
__FILENAME__ = test
from django_selenium.management.commands import test_selenium

class Command(test_selenium.Command):

    def handle(self, *test_labels, **options):
        super(Command, self).handle(*test_labels, **options)

########NEW FILE########
__FILENAME__ = models


########NEW FILE########
__FILENAME__ = tests
import unittest

from django.core.urlresolvers import reverse
from django_selenium.livetestcases import SeleniumLiveTestCase
from django_selenium.testcases import SeleniumElement, NoElementException


class SimpleUnitTests(unittest.TestCase):

    def test_multiple_elements(self):
        test_list = ['one string', 'another string']
        se = SeleniumElement(test_list, 'selector')
        self.assertEquals(se.replace('one', 'two'), 'two string')
        for i, elem in enumerate(se):
            self.assertEquals(elem, test_list[i])

    def test_no_element_exception(self):
        se = SeleniumElement([], 'selector')
        with self.assertRaises(NoElementException):
            se.replace('one', 'two')


class MyTestCase(SeleniumLiveTestCase):

    def test_home(self):
        self.driver.open_url(reverse('main'))
        self.assertEquals(self.driver.get_title(), 'Sample Test Page')
        self.driver.type_in('input#id_query', 'search something')
        self.driver.click('.form-search button[type="submit"]')

        self.assertEquals(self.driver.get_text('#success'), 'SUCCESS')

########NEW FILE########
__FILENAME__ = views
from django.views.generic import FormView
from core.forms import SampleSearchForm


class SampleSearchView(FormView):
    template_name = "home.html"
    form_class = SampleSearchForm

    def form_valid(self, form):
        """Show the results that will be used in tests"""
        return self.render_to_response(self.get_context_data(form=form, success='SUCCESS'))

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
from django.core.management import execute_manager
import imp
try:
    imp.find_module('settings') # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n" % __file__)
    sys.exit(1)

import settings

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = settings
# Django settings for django-selenium-testapp project.
import os

DEBUG = True
TEMPLATE_DEBUG = DEBUG

PROJECT_DIR = os.path.abspath(os.path.dirname(__file__))

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'django_selenium.db',           # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'Europe/Moscow'

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = ''

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = ''#os.path.join(PROJECT_DIR, 'staticfiles')

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# Additional locations of static files

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

STATICFILES_DIRS = (os.path.join(PROJECT_DIR, 'static'),)

# Make this unique, and don't share it with anybody.
SECRET_KEY = '_29sv-$^kyi&z0c#ddcs)8^etu+-hb@qlz9--wm!pfpj(6i%^u'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
)

ROOT_URLCONF = 'urls'

TEMPLATE_DIRS = (os.path.join(os.path.dirname(__file__), 'templates'),)
TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.debug',
    'django.core.context_processors.request',
    'django.core.context_processors.i18n',
    'django.core.context_processors.media',
    'django.core.context_processors.static',
)


INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.staticfiles',
    'core',
)
# ----------------- SELENIUM ----------------------
SELENIUM_DRIVER = 'Firefox'
SELENIUM_DISPLAY = ":99.0"

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url
from core.views import SampleSearchView


urlpatterns = patterns('',
   url(r'^$', SampleSearchView.as_view(), name='main'),
)

########NEW FILE########
