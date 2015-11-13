__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# pyramid_xmlrpc documentation build configuration file
#
# This file is execfile()d with the current directory set to its containing
# dir.
#
# The contents of this file are pickled, so don't put values in the
# namespace that aren't pickleable (module imports are okay, they're
# removed automatically).
#
# All configuration values have a default value; values that are commented
# out serve to show the default value.

import sys, os, datetime

# If your extensions are in another directory, add it here. If the directory
# is relative to the documentation root, use os.path.abspath to make it
# absolute, like shown here.
parent = os.path.dirname(os.path.dirname(__file__))
sys.path.append(os.path.abspath(parent))
wd = os.getcwd()
os.chdir(parent)
os.system('%s setup.py test -q' % sys.executable)
os.chdir(wd)

for item in os.listdir(parent):
    if item.endswith('.egg'):
        sys.path.append(os.path.join(parent, item))

import pkginfo

# General configuration
# ---------------------

pkg_info = pkginfo.Develop(os.path.join(os.path.dirname(__file__),'..'))

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.intersphinx',
    ]

# Looks for bfg's objects
intersphinx_mapping = {'http://docs.pylonsproject.org/projects/pyramid/dev': None}

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

# General substitutions.
project = 'pyramid_rpc'
copyright = '%s, Ben Bangert <ben@groovie.org>' % datetime.datetime.now().year

# The default replacements for |version| and |release|, also used in various
# other places throughout the built documents.
#
# The short X.Y version.
version = release = pkg_info.version
# The full version, including alpha/beta/rc tags.

# There are two options for replacing |today|: either, you set today to
# some non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
today_fmt = '%B %d, %Y'

# List of documents that shouldn't be included in the build.
#unused_docs = []

# List of directories, relative to source directories, that shouldn't be
# searched for source files.
#exclude_dirs = []

# The reST default role (used for this markup: `text`) to use for all
# documents.
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
#pygments_style = 'sphinx'


# Options for HTML output
# -----------------------

# Add and use Pylons theme
sys.path.append(os.path.abspath('_themes'))
html_theme_path = ['_themes']
html_theme = 'pyramid'

# The style sheet to use for HTML and HTML Help pages. A file of that name
# must exist either in Sphinx' static/ path, or in one of the custom paths
# given in html_static_path.
#html_style = 'repoze.css'

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as
# html_title.
#html_short_title = None

# The name of an image file (within the static path) to place at the top of
# the sidebar.
# html_logo = '.static/logo_hi.gif'

# The name of an image file (within the static path) to use as favicon of
# the docs.  This file should be a Windows icon file (.ico) being 16x16 or
# 32x32 pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets)
# here, relative to this directory. They are copied after the builtin
# static files, so a file named "default.css" will overwrite the builtin
# "default.css".
html_static_path = ['.static']

# If not '', a 'Last updated on:' timestamp is inserted at every page
# bottom, using the given strftime format.
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

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, the reST sources are included in the HTML build as
# _sources/<name>.
#html_copy_source = True

# If true, an OpenSearch description file will be output, and all pages
# will contain a <link> tag referring to it.  The value of this option must
# be the base URL from which the finished HTML is served.
#html_use_opensearch = ''

# If nonempty, this is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = ''

# Output file base name for HTML help builder.
htmlhelp_basename = 'rpcdoc'


# Options for LaTeX output
# ------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title,
#  author, document class [howto/manual]).
latex_documents = [
  ('index', 'rpc.tex', 'pyramid_rpc Documentation',
   'Pylons Project Developers', 'manual'),
]

# The name of an image file (relative to this directory) to place at the
# top of the title page.
latex_logo = '.static/logo_hi.gif'

# For "manual" documents, if this is true, then toplevel headings are
# parts, not chapters.
#latex_use_parts = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_use_modindex = True

########NEW FILE########
__FILENAME__ = css_selector_steps
import time

from lettuce import step
from lettuce import world

from lettuce_webdriver.util import assert_true
from lettuce_webdriver.util import assert_false

from selenium.common.exceptions import WebDriverException

import logging
log = logging.getLogger(__name__)

def wait_for_elem(browser, sel, timeout=15):
    start = time.time()
    elems = []
    while time.time() - start < timeout:
        elems = find_elements_by_jquery(browser, sel)
        if elems:
            return elems
        time.sleep(0.2)
    return elems


def load_script(browser, url):
    """Ensure that JavaScript at a given URL is available to the browser."""
    if browser.current_url.startswith('file:'):
        url = 'https:' + url
    browser.execute_script("""
    var script_tag = document.createElement("script");
    script_tag.setAttribute("type", "text/javascript");
    script_tag.setAttribute("src", arguments[0]);
    document.getElementsByTagName("head")[0].appendChild(script_tag);
    """, url)


def find_elements_by_jquery(browser, selector):
    """Find HTML elements using jQuery-style selectors.
    
    Ensures that jQuery is available to the browser; if it gets a
    WebDriverException that looks like jQuery is not available, it attempts to
    include it and reexecute the script."""
    try:
        return browser.execute_script("""return ($ || jQuery)(arguments[0]).get();""", selector)
    except WebDriverException as e:
        if e.msg.startswith(u'$ is not defined'):
            load_script(browser, "//ajax.googleapis.com/ajax/libs/jquery/1.10.2/jquery.min.js")
            return browser.execute_script("""return ($ || jQuery)(arguments[0]).get();""", selector)
        else:
            raise


def find_element_by_jquery(step, browser, selector):
    """Find a single HTML element using jQuery-style selectors."""
    elements = find_elements_by_jquery(browser, selector)
    assert_true(step, len(elements) > 0)
    return elements[0]


def find_parents_by_jquery(browser, selector):
    """Find HTML elements' parents using jQuery-style selectors.
    
    In addition to reliably including jQuery, this also finds the pa"""
    try:
        return browser.execute_script("""return ($ || jQuery)(arguments[0]).parent().get();""", selector)
    except WebDriverException as e:
        if e.msg.startswith(u'$ is not defined'):
            load_script(browser, "//ajax.googleapis.com/ajax/libs/jquery/1.10.2/jquery.min.js")
            return browser.execute_script("""return ($ || jQuery)(arguments[0]).parent().get();""", selector)
        else:
            raise


@step(r'There should be an element matching \$\("(.*?)"\)$')
def check_element_by_selector(step, selector):
    elems = find_elements_by_jquery(world.browser, selector)
    assert_true(step, elems)


@step(r'There should be an element matching \$\("(.*?)"\) within (\d+) seconds?$')
def wait_for_element_by_selector(step, selector, seconds):
    elems = wait_for_elem(world.browser, selector, int(seconds))
    assert_true(step, elems)


@step(r'There should be exactly (\d+) elements matching \$\("(.*?)"\)$')
def count_elements_exactly_by_selector(step, number, selector):
    elems = find_elements_by_jquery(world.browser, selector)
    assert_true(step, len(elems) == int(number))


@step(r'I fill in \$\("(.*?)"\) with "(.*?)"$')
def fill_in_by_selector(step, selector, value):
    elem = find_element_by_jquery(step, world.browser, selector)
    elem.clear()
    elem.send_keys(value)


@step(r'I submit \$\("(.*?)"\)')
def submit_by_selector(step, selector):
    elem = find_element_by_jquery(step, world.browser, selector)
    elem.submit()


@step(r'I check \$\("(.*?)"\)$')
def check_by_selector(step, selector):
    elem = find_element_by_jquery(step, world.browser, selector)
    if not elem.is_selected():
        elem.click()


@step(r'I click \$\("(.*?)"\)$')
def click_by_selector(step, selector):
    # No need for separate button press step with selector style.
    elem = find_element_by_jquery(step, world.browser, selector)
    elem.click()


@step(r'I follow the link \$\("(.*?)"\)$')
def click_by_selector(step, selector):
    elem = find_element_by_jquery(step, world.browser, selector)
    href = elem.get_attribute('href')
    world.browser.get(href)


@step(r'\$\("(.*?)"\) should be selected$')
def click_by_selector(step, selector):
    # No need for separate button press step with selector style.
    elem = find_element_by_jquery(step, world.browser, selector)
    assert_true(step, elem.is_selected())


@step(r'I select \$\("(.*?)"\)$')
def select_by_selector(step, selector):
    option = find_element_by_jquery(step, world.browser, selector)
    selectors = find_parents_by_jquery(world.browser, selector)
    assert_true(step, len(selectors) > 0)
    selector = selectors[0]
    selector.click()
    time.sleep(0.3)
    option.click()
    assert_true(step, option.is_selected())

@step(r'There should not be an element matching \$\("(.*?)"\)$')
def check_element_by_selector(step, selector):
    elems = find_elements_by_jquery(world.browser, selector)
    assert_false(step, elems)

__all__ = [
    'wait_for_element_by_selector',
    'fill_in_by_selector',
    'check_by_selector',
    'click_by_selector',
    'check_element_by_selector',
]

########NEW FILE########
__FILENAME__ = django
"""
Django-specific extensions
"""

import socket
import urlparse

from lettuce import step
from lettuce.django import server

# make sure the steps are loaded
import lettuce_webdriver.webdriver  # pylint:disable=unused-import


def site_url(url):
    """
    Determine the server URL.
    """
    base_url = 'http://%s' % socket.gethostname()

    if server.port is not 80:
        base_url += ':%d' % server.port

    return urlparse.urljoin(base_url, url)


@step(r'I visit site page "([^"]*)"')
def visit_page(self, page):
    """
    Visit the specific page of the site.
    """

    self.given('I visit "%s"' % site_url(page))

########NEW FILE########
__FILENAME__ = parallel_bin
import os
import sys
import optparse

import lettuce
from .parallel_runner import ParallelRunner


def main(args=sys.argv[1:]):
    base_path = os.path.join(os.path.dirname(os.curdir), 'features')
    parser = optparse.OptionParser(
        usage="%prog or type %prog -h (--help) for help",
        version=lettuce.version)

    parser.add_option("-v", "--verbosity",
                      dest="verbosity",
                      default=4,
                      help='The verbosity level')

    parser.add_option('-p', '--parallelization',
                      dest='parallelization',
                      default=5,
                      type="int",
                      help='How many parallel processes to use')

    parser.add_option("-s", "--scenarios",
                      dest="scenarios",
                      default=None,
                      help='Comma separated list of scenarios to run')

    parser.add_option("-t", "--tag",
                      dest="tags",
                      default=None,
                      action='append',
                      help='Tells lettuce to run the specified tags only; '
                      'can be used multiple times to define more tags'
                      '(prefixing tags with "-" will exclude them and '
                      'prefixing with "~" will match approximate words)')

    parser.add_option("-r", "--random",
                      dest="random",
                      action="store_true",
                      default=False,
                      help="Run scenarios in a more random order to avoid interference")

    parser.add_option("--with-xunit",
                      dest="enable_xunit",
                      action="store_true",
                      default=False,
                      help='Output JUnit XML test results to a file')

    parser.add_option("--xunit-file",
                      dest="xunit_file",
                      default=None,
                      type="string",
                      help='Write JUnit XML to this file. Defaults to '
                      'lettucetests.xml')

    parser.add_option("--failfast",
                      dest="failfast",
                      default=False,
                      action="store_true",
                      help='Stop running in the first failure')

    parser.add_option("--pdb",
                      dest="auto_pdb",
                      default=False,
                      action="store_true",
                      help='Launches an interactive debugger upon error')

    options, args = parser.parse_args(args)
    if args:
        base_path = [os.path.abspath(arg) for arg in args]

    try:
        options.verbosity = int(options.verbosity)
    except ValueError:
        pass

    tags = None
    if options.tags:
        tags = [tag.strip('@') for tag in options.tags]

    runner = ParallelRunner(
        base_path,
        parallelization=options.parallelization,
        scenarios=options.scenarios,
        verbosity=options.verbosity,
        random=options.random,
        enable_xunit=options.enable_xunit,
        xunit_filename=options.xunit_file,
        failfast=options.failfast,
        auto_pdb=options.auto_pdb,
        tags=tags,
    )

    result = runner.run()
    failed = result is None or result.steps != result.steps_passed
    sys.exit(int(failed))

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = parallel_runner
from lettuce.core import Feature, TotalResult

from lettuce.terrain import after
from lettuce.terrain import before
from lettuce.terrain import world

from lettuce.decorators import step
from lettuce.registry import call_hook
from lettuce.registry import STEP_REGISTRY
from lettuce.registry import CALLBACK_REGISTRY
from lettuce.exceptions import StepLoadingError
from lettuce.plugins import (
    xunit_output,
    autopdb
)
from lettuce import fs
from lettuce import exceptions

from multiprocessing import Pool
from cStringIO import StringIO
from itertools import chain
import os.path
import sys
import traceback
import copy

from importlib import import_module

try:
    from colorama import init as ms_windows_workaround
    ms_windows_workaround()
except ImportError:
    pass

try:
    terrain = fs.FileSystem._import("terrain")
    reload(terrain)
except Exception, e:
    if not "No module named terrain" in str(e):
        string = 'Lettuce has tried to load the conventional environment ' \
            'module "terrain"\nbut it has errors, check its contents and ' \
            'try to run lettuce again.\n\nOriginal traceback below:\n\n'

        sys.stderr.write(string)
        sys.stderr.write(exceptions.traceback.format_exc(e))
        raise SystemExit(1)


class ParallelRunner(object):
    """Parallel lettuce test runner. Runs each feature in a separate process,
    up to a fixed number in parallel.

    Takes a base path as parameter (string), so that it can look for
    features and step definitions on there.
    """
    def __init__(self, base_path, parallelization=5, scenarios=None,
                 verbosity=0, random=False, enable_xunit=False,
                 xunit_filename=None, tags=None, failfast=False,
                 auto_pdb=False):
        """ lettuce.Runner will try to find a terrain.py file and
        import it from within `base_path`
        """

        self.tags = tags
        self.explicit_features = []

        if isinstance(base_path, list):
            self.explicit_features = base_path
            base_path = os.path.dirname(base_path[0])

        sys.path.insert(0, base_path)
        self.loader = fs.FeatureLoader(base_path)
        self.verbosity = verbosity
        self.scenarios = scenarios and map(int, scenarios.split(",")) or None
        self.failfast = failfast
        if auto_pdb:
            autopdb.enable(self)

        sys.path.remove(base_path)

        if verbosity is 0:
            output = 'non_verbose'
        elif verbosity is 1:
            output = 'dots'
        elif verbosity is 2:
            output = 'scenario_names'
        elif verbosity is 3:
            output = 'shell_output'
        else:
            output = 'colored_shell_output'

        self.random = random

        if enable_xunit:
            xunit_output.enable(filename=xunit_filename)

        self._output = output

        self.parallelization = parallelization

    @property
    def output(self):
        module = import_module('.' + self._output, 'lettuce.plugins')
        reload(module)
        return module

    def run(self):
        """ Find and load step definitions, and them find and load
        features under `base_path` specified on constructor
        """
        try:
            self.loader.find_and_load_step_definitions()
        except StepLoadingError, e:
            print "Error loading step definitions:\n", e
            return

        results = []
        if self.explicit_features:
            features_files = self.explicit_features
        else:
            features_files = self.loader.find_feature_files()
        if self.random:
            random.shuffle(features_files)

        if not features_files:
            self.output.print_no_features_found(self.loader.base_dir)
            return

        processes = Pool(processes=self.parallelization)
        test_results_it = processes.imap_unordered(
            worker_process, [(self, filename) for filename in features_files]
        )
        
        all_total = ParallelTotalResult()
        for result in test_results_it:
            all_total += result['total']
            sys.stdout.write(result['stdout'])
            sys.stderr.write(result['stderr'])

        return all_total

def worker_process(args):
    self, filename = args
    sys.stdout = StringIO()
    sys.stderr = StringIO()

    failed = False
    results = []
    try:
        self.output
        call_hook('before', 'all')
        feature = Feature.from_file(filename)
        results.append(
            feature.run(self.scenarios,
                        tags=self.tags,
                        random=self.random,
                        failfast=self.failfast))

    except exceptions.LettuceSyntaxError, e:
        sys.stderr.write(e.msg)
        failed = True
    except:
        if not self.failfast:
            e = sys.exc_info()[1]
            print "Died with %s" % str(e)
            traceback.print_exc()
        else:
            print
            print ("Lettuce aborted running any more tests "
                   "because was called with the `--failfast` option")

        failed = True

    finally:
        total = TotalResult(results)
        call_hook('after', 'all', total)
    
    return {
        'stdout': sys.stdout.getvalue(),
        'stderr': sys.stderr.getvalue(),
        'failed': failed,
        'total': ParallelTotalResult(total),
    }

class ParallelTotalResult(object):
    def __init__(self, total=None):
        self.steps_passed = 0
        self.steps_failed = 0
        self.steps_skipped = 0
        self.steps_undefined = 0
        self.steps = 0
        scenario_results = []
        if total:
            feature_results = total.feature_results
            self.features_ran = len(feature_results)
            self.features_passed = len([result for result in feature_results if result.passed])
            for feature_result in feature_results:
                for scenario_result in feature_result.scenario_results:
                    self.steps_passed += len(scenario_result.steps_passed)
                    self.steps_failed += len(scenario_result.steps_failed)
                    self.steps_skipped += len(scenario_result.steps_skipped)
                    self.steps_undefined += len(scenario_result.steps_undefined)
                    self.steps += scenario_result.total_steps
                    scenario_results.append(scenario_result)
            self.scenarios_ran = len(scenario_results)
            self.scenarios_passed = len([result for result in scenario_results if result.passed])
        else:
            self.features_ran = 0
            self.features_passed = 0
            self.scenarios_ran = 0
            self.scenarios_passed = 0

    def _filter_proposed_definitions(self):
        raise NotImplementedError()

    @property
    def proposed_definitions(self):
        raise NotImplementedError()
    
    def __add__(self, other):
        new_ptr = copy.copy(self)
        for attr in new_ptr.__dict__:
            if isinstance(getattr(new_ptr, attr), int):
                setattr(new_ptr, attr,
                        getattr(new_ptr, attr) + getattr(other, attr))
        return new_ptr


########NEW FILE########
__FILENAME__ = screenshot
"""Steps and utility functions for taking screenshots."""

import uuid

from lettuce import (
    after,
    step,
    world,
)
import os.path
import json

def set_save_directory(base, source):
    """Sets the root save directory for saving screenshots.
    
    Screenshots will be saved in subdirectories under this directory by
    browser window size. """
    root = os.path.join(base, source)
    if not os.path.isdir(root):
        os.makedirs(root)

    world.screenshot_root = root


def resolution_path(world):
    window_size = world.browser.get_window_size()
    return os.path.join(
        world.screenshot_root,
        '{}x{}'.format(window_size['width'], window_size['height']),
    )


@step(r'I capture a screenshot$')
def capture_screenshot(step):
    feature = step.scenario.feature
    step.shot_name = '{}.png'.format(uuid.uuid4())
    if getattr(feature, 'dir_path', None) is None:
        feature.dir_path = resolution_path(world)
    if not os.path.isdir(feature.dir_path):
        os.makedirs(feature.dir_path)
    filename = os.path.join(
        feature.dir_path,
        step.shot_name,
    )
    world.browser.get_screenshot_as_file(filename)


@step(r'I capture a screenshot after (\d+) seconds?$')
def capture_screenshot_delay(step, delay):
    time.sleep(delay)
    capture_screenshot()


@after.each_feature
def record_run_feature_report(feature):
    if getattr(feature, 'dir_path', None) is None:
        return
    feature_name_json = '{}.json'.format(os.path.splitext(
        os.path.basename(feature.described_at.file)
    )[0])
    report = {}
    for scenario in feature.scenarios:
        scenario_report = []
        for step in scenario.steps:
            shot_name = getattr(step, 'shot_name', None)
            if shot_name is not None:
                scenario_report.append(shot_name)
        if scenario_report:
            report[scenario.name] = scenario_report

    if report:
        with open(os.path.join(feature.dir_path, feature_name_json), 'w') as f:
            json.dump(report, f)

########NEW FILE########
__FILENAME__ = test_css_selector_steps
import os
import unittest

from lettuce import world
from lettuce.core import Feature

from lettuce_webdriver.tests import html_pages

PAGES = {}
for filename in os.listdir(html_pages):
    name = filename.split('.html')[0]
    PAGES[name] = 'file://%s' % os.path.join(html_pages, filename)


FEATURES = [
    """
    Feature: Wait and match CSS
        Scenario: Everything fires up
            When I go to "%(page)s"
            Then There should be an element matching $("textarea[name='bio']") within 1 second
    """ % {'page': PAGES['basic_page']},

    """
    Feature: CSS-based formstuff
        Scenario: Everything fires up
            When I go to "%(page)s"
            Then I fill in $("input[name='user']") with "A test string"
            And I check $("input[value='Bike']")
    """ % {'page': PAGES['basic_page']},    
]

class TestUtil(unittest.TestCase):
    def setUp(self):
        # Go to an empty page
        world.browser.get('')

    def test_features(self):
        import lettuce_webdriver.webdriver
        import lettuce_webdriver.css_selector_steps
        for feature_string in FEATURES:
            f = Feature.from_string(feature_string)
            feature_result = f.run(failfast=True)
            scenario_result = feature_result.scenario_results[0]
            self.assertFalse(scenario_result.steps_failed)
            self.assertFalse(scenario_result.steps_skipped)
            self.assertFalse(scenario_result.steps_undefined)

########NEW FILE########
__FILENAME__ = test_util
import os
import unittest

from lettuce import world
from lettuce.core import Step
from lettuce_webdriver.tests import html_pages

def setUp():
    file_path = 'file://%s' % os.path.join(html_pages, 'basic_page.html')
    world.browser.get(file_path)

class TestUtil(unittest.TestCase):
    def test_find_by_id(self):
        from lettuce_webdriver.util import find_field_by_id
        assert find_field_by_id(world.browser, 'password', 'pass')

    def test_find_by_name(self):
        from lettuce_webdriver.util import find_field_by_name
        assert find_field_by_name(world.browser, 'submit', 'submit')
        assert find_field_by_name(world.browser, 'select', 'car_choice')
        assert find_field_by_name(world.browser, 'textarea', 'bio')

    def test_find_by_label(self):
        from lettuce_webdriver.util import find_field_by_label
        assert find_field_by_label(world.browser, 'text', 'Username:')
    
    def test_no_label(self):
        from lettuce_webdriver.util import find_field_by_label
        assert find_field_by_label(world.browser, 'text', 'NoSuchLabel') is False
    
    def test_find_field(self):
        from lettuce_webdriver.util import find_field
        assert find_field(world.browser, 'text', 'username')
        assert find_field(world.browser, 'text', 'Username:')
        assert find_field(world.browser, 'text', 'user')

    def test_find_button(self):
        from lettuce_webdriver.util import find_button
        assert find_button(world.browser, 'submit')
        assert find_button(world.browser, 'Submit!')
        assert find_button(world.browser, 'submit_tentative')
        assert find_button(world.browser, 'Submit as tentative')
    
    def test_wait_for_content(self):
        from lettuce_webdriver.webdriver import wait_for_content
        step = Step("foobar", [])
        self.assertRaises(AssertionError, wait_for_content, step, world.browser, 'text not on the page', timeout=0)
    

########NEW FILE########
__FILENAME__ = test_webdriver
import os
import unittest
from functools import wraps

from lettuce import world
from lettuce.core import Feature

from lettuce_webdriver.tests import html_pages

PAGES = {}
for filename in os.listdir(html_pages):
    name = filename.split('.html')[0]
    PAGES[name] = 'file://%s' % os.path.join(html_pages, filename)


def feature(passed=None, failed=0, skipped=0):
    """
    Decorate a test method to test the feature contained in its docstring.

    Apply the context returned by the method to the feature.

    For example:
        @feature(passed=3)
        def test_some_feature(self):
            '''
            Feature: This name is returned
                Scenario: ...
                    When I {variable}
            '''

            return dict(variable=something)
    """

    assert passed is not None

    def outer(func):
        @wraps(func)
        def inner(self):
            import lettuce_webdriver.webdriver

            v = func(self)
            f = Feature.from_string(func.__doc__.format(**v))
            feature_result = f.run()
            scenario_result = feature_result.scenario_results[0]

            try:
                self.assertEquals(len(scenario_result.steps_passed), passed)
                self.assertEquals(len(scenario_result.steps_failed), failed)
                self.assertEquals(len(scenario_result.steps_skipped), skipped)
            except AssertionError:
                print "Failed", scenario_result.steps_failed
                if scenario_result.steps_failed:
                    print scenario_result.steps_failed[-1].why.traceback
                print "Skipped", scenario_result.steps_skipped
                print world.browser.page_source

                raise

        return inner

    return outer


class TestUtil(unittest.TestCase):
    def setUp(self):
        # Go to an empty page
        world.browser.get('')

    @feature(passed=5)
    def test_I_should_see(self):
        """
Feature: I should see, I should not see
    Scenario: Everything fires up
        When I visit "{page}"
        Then I should see "Hello there!"
        And I should see a link to "Google" with the url "http://google.com/"
        And I should see a link with the url "http://google.com/"
        And I should not see "Bogeyman"
        """

        return dict(page=PAGES['basic_page'])

    @feature(passed=3)
    def test_I_see_a_link(self):
        """
Feature: I should see a link
    Scenario: Everything fires up
        When I go to "{page}"
        Then  I should see a link to "Google" with the url "http://google.com/"
        And I see "Hello there!"
        """

        return dict(page=PAGES['basic_page'])

    @feature(passed=3)
    def test_see_a_link_containing(self):
        """
Feature: I should see a link containing
    Scenario: Everything fires up
        When I go to "{page}"
        Then The browser's URL should contain "file://"
        And I should see a link that contains the text "Goo" and the url "http://google.com/"
        """

        return dict(page=PAGES['basic_page'])

    @feature(passed=6)
    def test_basic_page_linking(self):
        """
Feature: Basic page linking
    Scenario: Follow links
        Given I go to "{link_page}"
        And I see "Page o link"
        When I click "Next Page"
        Then I should be at "{link_dest_page}"
        And The browser's URL should be "{link_dest_page}"
        And The browser's URL should not contain "http://"
        """

        return {
            'link_page': PAGES['link_page'],
            'link_dest_page': PAGES['link_dest']
        }

    @feature(passed=4)
    def test_I_see_a_form(self):
        """
Feature: I should see a form
    Scenario: Everything fires up
        When I go to "{page}"
        Then I should see a form that goes to "basic_page.html"
        And the element with id of "somediv" contains "Hello"
        And the element with id of "somediv" does not contain "bye"
        """

        return dict(page=PAGES['basic_page'])

    @feature(passed=5)
    def test_I_fill_in_a_form(self):
        """
Feature: I fill in a form
    Scenario: Everything fires up
        Given I go to "{page}"
        And I fill in "bio" with "everything awesome"
        And I fill in "Password: " with "neat"
        When I press "Submit!"
        Then The browser's URL should contain "bio=everything"
        """

        return dict(page=PAGES['basic_page'])

    @feature(passed=4)
    def test_checkboxes_checked(self):
        """
Feature: Checkboxes checked
    Scenario: Everything fires up
        Given I go to "{page}"
        When I check "I have a bike"
        Then The "I have a bike" checkbox should be checked
        And The "I have a car" checkbox should not be checked
        """

        return dict(page=PAGES['basic_page'])

    @feature(passed=5)
    def test_checkboxes_unchecked(self):
        """
Feature: Checkboxes unchecked
    Scenario: Everything fires up
        Given I go to "{page}"
        And I check "I have a bike"
        And The "I have a bike" checkbox should be checked
        When I uncheck "I have a bike"
        Then The "I have a bike" checkbox should not be checked
        """

        return dict(page=PAGES['basic_page'])

    @feature(passed=6)
    def test_combo_boxes(self):
        """
Feature: Combo boxes
    Scenario: Everything fires up
        Given I go to "{page}"
        Then I should see option "Mercedes" in selector "car_choice"
        And I should see option "Volvo" in selector "car_choice"
        And I should not see option "Skoda" in selector "car_choice"
        When I select "Mercedes" from "car_choice"
        Then The "Mercedes" option from "car_choice" should be selected
        """

        return dict(page=PAGES['basic_page'])

    @feature(passed=1, failed=1)
    def test_combo_boxes_fail(self):
        """
Feature: Combo boxes fail
    Scenario: Everything fires up
        Given I go to "{page}"
        Then I should not see option "Mercedes" in selector "car_choice"
        """

        return dict(page=PAGES['basic_page'])

    @feature(passed=3)
    def test_multi_combo_boxes(self):
        '''
Feature: Multi-combo-boxes
    Scenario: Everything fires up
        Given I go to "{page}"
        When I select the following from "Favorite Colors:":
            """
            Blue
            Green
            """
        Then The following options from "Favorite Colors:" should be selected:
            """
            Blue
            Green
            """
        '''

        return dict(page=PAGES['basic_page'])

    @feature(passed=4)
    def test_radio_buttons(self):
        """
Feature: Radio buttons
    Scenario: Everything fires up
        When I go to "{page}"
        And I choose "Male"
        Then The "Male" option should be chosen
        And The "Female" option should not be chosen
        """

        return dict(page=PAGES['basic_page'])

    @feature(passed=4, failed=1, skipped=0)
    def test_hidden_text(self):
        """
Feature: Hidden text
    Scenario: Everything fires up
        When I go to "{page}"
        Then I should see an element with id of "bio_field"
        And I should see an element with id of "somediv" within 2 seconds
        And I should not see an element with id of "hidden_text"
        And I should see "Weeeee" within 1 second
        """

        return dict(page=PAGES['basic_page'])

    @feature(passed=2, failed=1, skipped=1)
    def test_hidden_text_2(self):
        """
Feature: Hidden text 2
    Scenario: Everything fires up
        When I go to "{page}"
        Then I should see "Hello there" within 1 second
        And I should see an element with id of "oops_field" within 1 second
        And I should not see an element with id of "hidden_text"
        """

        return dict(page=PAGES['basic_page'])

    @feature(passed=5)
    def test_alert_accept(self):
        """
Feature: test alert accept
    Scenario: alerts
        When I go to "{page}"
        Then I should see an alert with text "This is an alerting alert"
        When I accept the alert
        Then I should not see an alert
        And I should see "true"
        """

        return dict(page=PAGES['alert_page'])

    @feature(passed=5)
    def test_alert_dismiss(self):
        """
Feature: test alert accept
    Scenario: alerts
        When I go to "{page}"
        Then I should see an alert with text "This is an alerting alert"
        When I dismiss the alert
        Then I should not see an alert
        And I should see "false"
        """

        return dict(page=PAGES['alert_page'])

    @feature(passed=6)
    def test_tooltips(self):
        """
Feature: test tooltips
    Scenario: tooltips
        When I go to "{page}"
        Then I should see an element with tooltip "A tooltip"
        And I should not see an element with tooltip "Does not exist"
        And I should not see an element with tooltip "Hidden"
        When I click the element with tooltip "A tooltip"
        Then the browser's URL should contain "#anchor"
        """

        return dict(page=PAGES['tooltips'])

    @feature(passed=4)
    def test_labels(self):
        """
Feature: test labels
    Scenario: basic page
        When I go to "{page}"
        And I click on label "Favorite Colors:"
        Then element with id "fav_colors" should be focused
        And element with id "bio_field" should not be focused
        """

        return dict(page=PAGES['basic_page'])

    @feature(passed=2, failed=1)
    def test_labels_fail(self):
        """
Feature: test labels fail
    Scenario: basic page
        When I go to "{page}"
        And I click on label "Favorite Colors:"
        Then element with id "fav_colors" should not be focused
        """

        return dict(page=PAGES['basic_page'])

    @feature(passed=3)
    def test_input_values(self):
        """
Feature: assert value
    Scenario: basic page
        When I go to "{page}"
        And I fill in "username" with "Danni"
        Then input "username" has value "Danni"
        """

        return dict(page=PAGES['basic_page'])

    @feature(passed=2, failed=1)
    def test_input_values_fail(self):
        """
Feature: assert value
    Scenario: basic page
        When I go to "{page}"
        And I fill in "username" with "Danni"
        Then input "username" has value "Ricky"
        """

        return dict(page=PAGES['basic_page'])

    @feature(passed=2)
    def test_page_title(self):
        """
Feature: assert value
    Scenario: basic page
        When I go to "{page}"
        Then the page title should be "A Basic Page"
        """

        return dict(page=PAGES['basic_page'])

    @feature(passed=4)
    def test_submit_only(self):
        """
Feature: submit only form
    Scenario: basic page
        When I go to "{page}"
        And I submit the only form
        Then the browser's URL should contain "bio="
        And the browser's URL should contain "user="
        """

        return dict(page=PAGES['basic_page'])

    @feature(passed=4)
    def test_submit_action(self):
        """
Feature: submit only form
    Scenario: basic page
        When I go to "{page}"
        And I submit the form with action "basic_page.html"
        Then the browser's URL should contain "bio="
        And the browser's URL should contain "user="
        """

        return dict(page=PAGES['basic_page'])

    @feature(passed=4)
    def test_submit_id(self):
        """
Feature: submit only form
    Scenario: basic page
        When I go to "{page}"
        And I submit the form with id "the-form"
        Then the browser's URL should contain "bio="
        And the browser's URL should contain "user="
        """

        return dict(page=PAGES['basic_page'])

########NEW FILE########
__FILENAME__ = util
"""Utility functions that combine steps to locate elements"""

import socket
import urlparse

from selenium.common.exceptions import NoSuchElementException

from nose.tools import assert_true as nose_assert_true
from nose.tools import assert_false as nose_assert_false

# pylint:disable=missing-docstring,redefined-outer-name,redefined-builtin
# pylint:disable=invalid-name


class AssertContextManager():
    def __init__(self, step):
        self.step = step

    def __enter__(self):
        pass

    def __exit__(self, type, value, traceback):
        step = self.step
        if traceback:
            if isinstance(value, AssertionError):
                error = AssertionError(self.step.sentence)
            else:
                sentence = "%s, failed because: %s" % (step.sentence, value)
                error = AssertionError(sentence)
            raise error, None, traceback


def assert_true(step, exp):
    with AssertContextManager(step):
        nose_assert_true(exp)


def assert_false(step, exp, msg=None):
    with AssertContextManager(step):
        nose_assert_false(exp, msg)


def element_id_by_label(browser, label):
    """Return the id of a label's for attribute"""
    for_id = browser.find_elements_by_xpath(str('//label[contains(., "%s")]' %
                                                label))
    if not for_id:
        return False
    return for_id[0].get_attribute('for')


## Field helper functions to locate select, textarea, and the other
## types of input fields (text, checkbox, radio)
def field_xpath(field, attribute):
    if field in ['select', 'textarea']:
        return './/%s[@%s="%%s"]' % (field, attribute)
    elif field == 'button':
        if attribute == 'value':
            return './/%s[contains(., "%%s")]' % (field, )
        else:
            return './/%s[@%s="%%s"]' % (field, attribute)
    elif field == 'option':
        return './/%s[@%s="%%s"]' % (field, attribute)
    else:
        return './/input[@%s="%%s"][@type="%s"]' % (attribute, field)


def find_button(browser, value):
    return find_field_with_value(browser, 'submit', value) or \
        find_field_with_value(browser, 'reset', value) or \
        find_field_with_value(browser, 'button', value) or \
        find_field_with_value(browser, 'image', value)


def find_field_with_value(browser, field, value):
    return find_field_by_id(browser, field, value) or \
        find_field_by_name(browser, field, value) or \
        find_field_by_value(browser, field, value)


def find_option(browser, select_name, option_name):
    # First, locate the select
    select_box = find_field(browser, 'select', select_name)
    assert select_box

    # Now locate the option
    option_box = find_field(select_box, 'option', option_name)
    if not option_box:
        # Locate by contents
        option_box = select_box.find_element_by_xpath(str(
            './/option[contains(., "%s")]' % option_name))
    return option_box


def find_field(browser, field, value):
    """Locate an input field of a given value

    This first looks for the value as the id of the element, then
    the name of the element, then a label for the element.

    """
    return find_field_by_id(browser, field, value) or \
        find_field_by_name(browser, field, value) or \
        find_field_by_label(browser, field, value)


def find_field_by_id(browser, field, id):
    xpath = field_xpath(field, 'id')
    elems = browser.find_elements_by_xpath(str(xpath % id))
    return elems[0] if elems else False


def find_field_by_name(browser, field, name):
    xpath = field_xpath(field, 'name')
    elems = browser.find_elements_by_xpath(str(xpath % name))
    return elems[0] if elems else False


def find_field_by_value(browser, field, name):
    xpath = field_xpath(field, 'value')
    elems = browser.find_elements_by_xpath(str(xpath % name))
    return elems[0] if elems else False


def find_field_by_label(browser, field, label):
    """Locate the control input that has a label pointing to it

    This will first locate the label element that has a label of the given
    name. It then pulls the id out of the 'for' attribute, and uses it to
    locate the element by its id.

    """
    for_id = element_id_by_label(browser, label)
    if not for_id:
        return False
    return find_field_by_id(browser, field, for_id)


def option_in_select(browser, select_name, option):
    """
    Returns the Element specified by @option or None

    Looks at the real <select> not the select2 widget, since that doesn't
    create the DOM until we click on it.
    """

    select = find_field(browser, 'select', select_name)
    assert select

    try:
        return select.find_element_by_xpath(str(
            './/option[normalize-space(text()) = "%s"]' % option))
    except NoSuchElementException:
        return None

########NEW FILE########
__FILENAME__ = webdriver
"""Webdriver support for lettuce"""
import time

from lettuce import step, world

from lettuce_webdriver.util import (assert_true,
                                    assert_false,
                                    AssertContextManager,
                                    find_button,
                                    find_field,
                                    find_option,
                                    option_in_select)

from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.alert import Alert
from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    NoAlertPresentException,
    WebDriverException)

from nose.tools import assert_equals

# pylint:disable=missing-docstring,redefined-outer-name

from css_selector_steps import *


def contains_content(browser, content):
    # Search for an element that contains the whole of the text we're looking
    #  for in it or its subelements, but whose children do NOT contain that
    #  text - otherwise matches <body> or <html> or other similarly useless
    #  things.
    for elem in browser.find_elements_by_xpath(str(
            '//*[contains(normalize-space(.),"{content}") '
            'and not(./*[contains(normalize-space(.),"{content}")])]'
            .format(content=content))):

        try:
            if elem.is_displayed():
                return True
        except StaleElementReferenceException:
            pass

    return False


def wait_for_elem(browser, xpath, timeout=15):
    start = time.time()
    elems = []
    while time.time() - start < timeout:
        elems = browser.find_elements_by_xpath(str(xpath))
        if elems:
            return elems
        time.sleep(0.2)
    return elems


def wait_for_content(step, browser, content, timeout=15):
    start = time.time()
    while time.time() - start < timeout:
        if contains_content(world.browser, content):
            return
        time.sleep(0.2)
    assert_true(step, contains_content(world.browser, content))


## URLS
@step('I visit "(.*?)"$')
def visit(step, url):
    with AssertContextManager(step):
        world.browser.get(url)


@step('I go to "(.*?)"$')
def goto(step, url):
    step.given('I visit "%s"' % url)


## Links
@step('I click "(.*?)"$')
def click(step, name):
    with AssertContextManager(step):
        elem = world.browser.find_element_by_link_text(name)
        elem.click()


@step('I should see a link with the url "(.*?)"$')
def should_see_link(step, link_url):
    assert_true(step, world.browser.
                find_element_by_xpath(str('//a[@href="%s"]' % link_url)))


@step('I should see a link to "(.*?)" with the url "(.*?)"$')
def should_see_link_text(step, link_text, link_url):
    assert_true(step,
                world.browser.find_element_by_xpath(str(
                    '//a[@href="%s"][./text()="%s"]' %
                    (link_url, link_text))))


@step('I should see a link that contains the text "(.*?)" '
      'and the url "(.*?)"$')
def should_include_link_text(step, link_text, link_url):
    return world.browser.find_element_by_xpath(str(
        '//a[@href="%s"][contains(., %s)]' %
        (link_url, link_text)))


## General
@step('The element with id of "(.*?)" contains "(.*?)"$')
def element_contains(step, element_id, value):
    return world.browser.find_element_by_xpath(str(
        'id("{id}")[contains(text(), "{value}")]'.format(
            id=element_id, value=value)))


@step('The element with id of "(.*?)" does not contain "(.*?)"$')
def element_not_contains(step, element_id, value):
    elem = world.browser.find_elements_by_xpath(str(
        'id("{id}")[contains(text(), "{value}")]'.format(
            id=element_id, value=value)))
    assert_false(step, elem)


@step(r'I should see an element with id of "(.*?)" within (\d+) seconds?$')
def should_see_id_in_seconds(step, element_id, timeout):
    elem = wait_for_elem(world.browser, 'id("%s")' % element_id,
                         int(timeout))
    assert_true(step, elem)
    elem = elem[0]
    assert_true(step, elem.is_displayed())


@step('I should see an element with id of "(.*?)"$')
def should_see_id(step, element_id):
    elem = world.browser.find_element_by_xpath(str('id("%s")' % element_id))
    assert_true(step, elem.is_displayed())


@step('I should not see an element with id of "(.*?)"$')
def should_not_see_id(step, element_id):
    try:
        elem = world.browser.find_element_by_xpath(str('id("%s")' %
                                                   element_id))
        assert_true(step, not elem.is_displayed())
    except NoSuchElementException:
        pass


@step(r'I should see "([^"]+)" within (\d+) seconds?$')
def should_see_in_seconds(step, text, timeout):
    wait_for_content(step, world.browser, text, int(timeout))


@step('I should see "([^"]+)"$')
def should_see(step, text):
    assert_true(step, contains_content(world.browser, text))


@step('I see "([^"]+)"$')
def see(step, text):
    assert_true(step, contains_content(world.browser, text))


@step('I should not see "([^"]+)"$')
def should_not_see(step, text):
    assert_true(step, not contains_content(world.browser, text))


@step('I should be at "(.*?)"$')
def url_should_be(step, url):
    assert_true(step, url == world.browser.current_url)


## Browser
@step('The browser\'s URL should be "(.*?)"$')
def browser_url_should_be(step, url):
    assert_true(step, url == world.browser.current_url)


@step('The browser\'s URL should contain "(.*?)"$')
def url_should_contain(step, url):
    assert_true(step, url in world.browser.current_url)


@step('The browser\'s URL should not contain "(.*?)"$')
def url_should_not_contain(step, url):
    assert_true(step, url not in world.browser.current_url)


## Forms
@step('I should see a form that goes to "(.*?)"$')
def see_form(step, url):
    return world.browser.find_element_by_xpath(str('//form[@action="%s"]' %
                                                   url))


@step('I fill in "(.*?)" with "(.*?)"$')
def fill_in_textfield(step, field_name, value):
    with AssertContextManager(step):
        text_field = find_field(world.browser, 'text', field_name) or \
            find_field(world.browser, 'textarea', field_name) or \
            find_field(world.browser, 'password', field_name) or \
            find_field(world.browser, 'datetime', field_name) or \
            find_field(world.browser, 'datetime-local', field_name) or \
            find_field(world.browser, 'date', field_name) or \
            find_field(world.browser, 'month', field_name) or \
            find_field(world.browser, 'time', field_name) or \
            find_field(world.browser, 'week', field_name) or \
            find_field(world.browser, 'number', field_name) or \
            find_field(world.browser, 'range', field_name) or \
            find_field(world.browser, 'email', field_name) or \
            find_field(world.browser, 'url', field_name) or \
            find_field(world.browser, 'search', field_name) or \
            find_field(world.browser, 'tel', field_name) or \
            find_field(world.browser, 'color', field_name)
        assert_false(step, text_field is False,
                     'Can not find a field named "%s"' % field_name)
        text_field.clear()
        text_field.send_keys(value)


@step('I press "(.*?)"$')
def press_button(step, value):
    with AssertContextManager(step):
        button = find_button(world.browser, value)
        button.click()


@step('I click on label "([^"]*)"')
def click_on_label(step, label):
    """
    Click on a label
    """

    with AssertContextManager(step):
        elem = world.browser.find_element_by_xpath(str(
            '//label[normalize-space(text()) = "%s"]' % label))
        elem.click()


@step(r'Element with id "([^"]*)" should be focused')
def element_focused(step, id):
    """
    Check if the element is focused
    """

    elem = world.browser.find_element_by_xpath(str('id("{id}")'.format(id=id)))
    focused = world.browser.switch_to_active_element()

    assert_true(step, elem == focused)


@step(r'Element with id "([^"]*)" should not be focused')
def element_not_focused(step, id):
    """
    Check if the element is not focused
    """

    elem = world.browser.find_element_by_xpath(str('id("{id}")'.format(id=id)))
    focused = world.browser.switch_to_active_element()

    assert_false(step, elem == focused)


@step(r'Input "([^"]*)" (?:has|should have) value "([^"]*)"')
def input_has_value(step, field_name, value):
    """
    Check that the form input element has given value.
    """
    with AssertContextManager(step):
        text_field = find_field(world.browser, 'text', field_name) or \
            find_field(world.browser, 'textarea', field_name) or \
            find_field(world.browser, 'password', field_name)
        assert_false(step, text_field is False,
                     'Can not find a field named "%s"' % field_name)
        assert_equals(text_field.get_attribute('value'), value)


@step(r'I submit the only form')
def submit_the_only_form(step):
    """
    Look for a form on the page and submit it.
    """
    form = world.browser.find_element_by_xpath(str('//form'))
    form.submit()


@step(r'I submit the form with id "([^"]*)"')
def submit_form_id(step, id):
    """
    Submit the form having given id.
    """
    form = world.browser.find_element_by_xpath(str('id("{id}")'.format(id=id)))
    form.submit()


@step(r'I submit the form with action "([^"]*)"')
def submit_form_action(step, url):
    """
    Submit the form having given action URL.
    """
    form = world.browser.find_element_by_xpath(str('//form[@action="%s"]' %
                                                   url))
    form.submit()


# Checkboxes
@step('I check "(.*?)"$')
def check_checkbox(step, value):
    with AssertContextManager(step):
        check_box = find_field(world.browser, 'checkbox', value)
        if not check_box.is_selected():
            check_box.click()


@step('I uncheck "(.*?)"$')
def uncheck_checkbox(step, value):
    with AssertContextManager(step):
        check_box = find_field(world.browser, 'checkbox', value)
        if check_box.is_selected():
            check_box.click()


@step('The "(.*?)" checkbox should be checked$')
def assert_checked_checkbox(step, value):
    check_box = find_field(world.browser, 'checkbox', value)
    assert_true(step, check_box.is_selected())


@step('The "(.*?)" checkbox should not be checked$')
def assert_not_checked_checkbox(step, value):
    check_box = find_field(world.browser, 'checkbox', value)
    assert_true(step, not check_box.is_selected())


# Selectors
@step('I select "(.*?)" from "(.*?)"$')
def select_single_item(step, option_name, select_name):
    with AssertContextManager(step):
        option_box = find_option(world.browser, select_name, option_name)
        option_box.click()


@step('I select the following from "([^"]*?)":?$')
def select_multi_items(step, select_name):
    with AssertContextManager(step):
        # Ensure only the options selected are actually selected
        option_names = step.multiline.split('\n')
        select_box = find_field(world.browser, 'select', select_name)

        select = Select(select_box)
        select.deselect_all()

        for option in option_names:
            try:
                select.select_by_value(option)
            except NoSuchElementException:
                select.select_by_visible_text(option)


@step('The "(.*?)" option from "(.*?)" should be selected$')
def assert_single_selected(step, option_name, select_name):
    option_box = find_option(world.browser, select_name, option_name)
    assert_true(step, option_box.is_selected())


@step('The following options from "([^"]*?)" should be selected:?$')
def assert_multi_selected(step, select_name):
    with AssertContextManager(step):
        # Ensure its not selected unless its one of our options
        option_names = step.multiline.split('\n')
        select_box = find_field(world.browser, 'select', select_name)
        option_elems = select_box.find_elements_by_xpath(str('./option'))
        for option in option_elems:
            if option.get_attribute('id') in option_names or \
               option.get_attribute('name') in option_names or \
               option.get_attribute('value') in option_names or \
               option.text in option_names:
                assert_true(step, option.is_selected())
            else:
                assert_true(step, not option.is_selected())


@step(r'I should see option "([^"]*)" in selector "([^"]*)"')
def select_contains(step, option, id_):
    assert_true(step, option_in_select(world.browser, id_, option) is not None)


@step(r'I should not see option "([^"]*)" in selector "([^"]*)"')
def select_does_not_contain(step, option, id_):
    assert_true(step, option_in_select(world.browser, id_, option) is None)


## Radios
@step('I choose "(.*?)"$')
def choose_radio(step, value):
    with AssertContextManager(step):
        box = find_field(world.browser, 'radio', value)
        box.click()


@step('The "(.*?)" option should be chosen$')
def assert_radio_selected(step, value):
    box = find_field(world.browser, 'radio', value)
    assert_true(step, box.is_selected())


@step('The "(.*?)" option should not be chosen$')
def assert_radio_not_selected(step, value):
    box = find_field(world.browser, 'radio', value)
    assert_true(step, not box.is_selected())


# Alerts
@step('I accept the alert')
def accept_alert(step):
    """
    Accept the alert
    """

    try:
        alert = Alert(world.browser)
        alert.accept()
    except WebDriverException:
        # PhantomJS is kinda poor
        pass


@step('I dismiss the alert')
def dismiss_alert(step):
    """
    Dismiss the alert
    """

    try:
        alert = Alert(world.browser)
        alert.dismiss()
    except WebDriverException:
        # PhantomJS is kinda poor
        pass


@step(r'I should see an alert with text "([^"]*)"')
def check_alert(step, text):
    """
    Check the alert text
    """

    try:
        alert = Alert(world.browser)
        assert_equals(alert.text, text)
    except WebDriverException:
        # PhantomJS is kinda poor
        pass


@step('I should not see an alert')
def check_no_alert(step):
    """
    Check there is no alert
    """

    try:
        alert = Alert(world.browser)
        raise AssertionError("Should not see an alert. Alert '%s' shown." %
                             alert.text)
    except NoAlertPresentException:
        pass


# Tooltips
@step(r'I should see an element with tooltip "([^"]*)"')
def see_tooltip(step, tooltip):
    """
    Press a button having a given tooltip.
    """
    elem = world.browser.find_elements_by_xpath(str(
        '//*[@title="%(tooltip)s" or @data-original-title="%(tooltip)s"]' %
        dict(tooltip=tooltip)))
    elem = [e for e in elem if e.is_displayed()]
    assert_true(step, elem)


@step(r'I should not see an element with tooltip "([^"]*)"')
def no_see_tooltip(step, tooltip):
    """
    Press a button having a given tooltip.
    """
    elem = world.browser.find_elements_by_xpath(str(
        '//*[@title="%(tooltip)s" or @data-original-title="%(tooltip)s"]' %
        dict(tooltip=tooltip)))
    elem = [e for e in elem if e.is_displayed()]
    assert_true(step, not elem)


@step(r'I (?:click|press) the element with tooltip "([^"]*)"')
def press_by_tooltip(step, tooltip):
    """
    Press a button having a given tooltip.
    """
    with AssertContextManager(step):
        for button in world.browser.find_elements_by_xpath(str(
            '//*[@title="%(tooltip)s" or @data-original-title="%(tooltip)s"]' %
                dict(tooltip=tooltip))):
            try:
                button.click()
                break
            except Exception:
                pass


@step(r'The page title should be "([^"]*)"')
def page_title(step, title):
    """
    Check that the page title matches the given one.
    """

    with AssertContextManager(step):
        assert_equals(world.browser.title, title)


@step(r'I switch to the frame with id "([^"]*)"')
def switch_to_frame(self, frame):
    elem = world.browser.find_element_by_id(frame)
    world.browser.switch_to_frame(elem)


@step(r'I switch back to the main view')
def switch_to_main(self):
    world.browser.switch_to_default_content()

########NEW FILE########
