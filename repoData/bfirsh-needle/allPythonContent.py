__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Needle documentation build configuration file, created by
# sphinx-quickstart on Tue Apr  5 19:53:10 2011.
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
#sys.path.insert(0, os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.txt'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Needle'
copyright = u'2011, Ben Firshman'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.1a1'
# The full version, including alpha/beta/rc tags.
release = '0.1a1'

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
html_theme = 'nature'

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
htmlhelp_basename = 'Needledoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'Needle.tex', u'Needle Documentation',
   u'Ben Firshman', 'manual'),
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

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'needle', u'Needle Documentation',
     [u'Ben Firshman'], 1)
]

########NEW FILE########
__FILENAME__ = cases
# encoding: utf-8
from __future__ import absolute_import
from __future__ import print_function

from warnings import warn
from contextlib import contextmanager
import os
import sys

if sys.version_info > (2, 7):
    from unittest import TestCase
else:
    from unittest2 import TestCase

if sys.version_info >= (3, 0):
    basestring = str


from PIL import Image

from needle.engines.pil_engine import ImageDiff
from needle.driver import (NeedleFirefox, NeedleChrome, NeedleIe, NeedleOpera,
                           NeedleSafari, NeedlePhantomJS, NeedleWebElement)


def _object_filename(obj):
    return os.path.abspath(sys.modules[type(obj).__module__].__file__)


def import_from_string(path):
    """
    Utility function to dynamically load a class specified by a string,
    e.g. 'path.to.my.Class'.
    """
    module_name, klass = path.rsplit('.', 1)
    module = __import__(module_name, fromlist=[klass])
    return getattr(module, klass)


class NeedleTestCase(TestCase):
    """
    A `unittest2 <http://www.voidspace.org.uk/python/articles/unittest2.shtml>`_
    test case which provides tools for testing CSS with Selenium.
    """

    driver = None

    capture = False  # Deprecated
    save_baseline = False

    viewport_width = 1024
    viewport_height = 768

    engine_class = 'needle.engines.pil_engine.Engine'

    @classmethod
    def setUpClass(cls):
        if os.environ.get('NEEDLE_CAPTURE'):
            cls.capture = True
        if os.environ.get('NEEDLE_SAVE_BASELINE'):
            cls.save_baseline = True

        # Instantiate the diff engine
        klass = import_from_string(cls.engine_class)
        cls.engine = klass()

        cls.driver = cls.get_web_driver()
        cls.driver.set_window_position(0, 0)
        cls.set_viewport_size(cls.viewport_width, cls.viewport_height)
        super(NeedleTestCase, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()
        super(NeedleTestCase, cls).tearDownClass()

    @classmethod
    def get_web_driver(cls):
        """
        Returns the WebDriver instance to be used. Defaults to `NeedleFirefox()`.
        Override this method if you'd like to control the logic for choosing
        the proper WebDriver instance.
        """
        browser_name = os.environ.get('NEEDLE_BROWSER')
        browser_map = {
            'firefox': NeedleFirefox,
            'chrome': NeedleChrome,
            'ie': NeedleIe,
            'opera': NeedleOpera,
            'safari': NeedleSafari,
            'phantomjs': NeedlePhantomJS,
        }
        browser_class = browser_map.get(browser_name, NeedleFirefox)
        return browser_class()

    def __init__(self, *args, **kwargs):
        super(NeedleTestCase, self).__init__(*args, **kwargs)
        # TODO: should output directory be timestamped?
        self.output_directory = os.environ.get('NEEDLE_OUTPUT_DIR', os.path.realpath(os.path.join(os.getcwd(), 'screenshots')))
        # TODO: Should baseline be a top-level peer to output_directory?
        self.baseline_directory = os.environ.get('NEEDLE_BASELINE_DIR', os.path.realpath(os.path.join(os.getcwd(), 'screenshots', 'baseline')))

        for i in (self.baseline_directory, self.output_directory):
            if not os.path.exists(i):
                print('Creating %s' % i, file=sys.stderr)
                os.makedirs(i)

    @classmethod
    def set_viewport_size(cls, width, height):
        cls.driver.set_window_size(width, height)

        # Measure the difference between the actual document width and the
        # desired viewport width so we can account for scrollbars:
        measured = cls.driver.execute_script("return {width: document.body.clientWidth, height: document.body.clientHeight};")
        delta = width - measured['width']

        cls.driver.set_window_size(width + delta, height)

    def assertScreenshot(self, element_or_selector, file, threshold=0):
        """assert-style variant of compareScreenshot context manager

        compareScreenshot() can be considerably more efficient for recording baselines by avoiding the need
        to load pages before checking whether we're actually going to save them. This function allows you
        to continue using normal unittest-style assertions if you don't need the efficiency benefits
        """

        with self.compareScreenshot(element_or_selector, file, threshold=threshold):
            pass

    @contextmanager
    def compareScreenshot(self, element_or_selector, file, threshold=0):
        """
        Assert that a screenshot of an element is the same as a screenshot on disk,
        within a given threshold.

        :param element_or_selector:
            Either a CSS selector as a string or a
            :py:class:`~needle.driver.NeedleWebElement` object that represents
            the element to capture.
        :param file:
            If a string, then assumed to be the filename for the screenshot,
            which will be appended with ``.png``. Otherwise assumed to be
            a file object for the baseline image.
        :param threshold:
            The threshold for triggering a test failure.
        """

        yield  # To allow using this method as a context manager

        if not isinstance(element_or_selector, NeedleWebElement):
            element = self.driver.find_element_by_css_selector(element_or_selector)
        else:
            element = element_or_selector

        if not isinstance(file, basestring):
            # Comparing in-memory files instead of on-disk files
            baseline_image = Image.open(file).convert('RGB')
            fresh_screenshot = element.get_screenshot()
            diff = ImageDiff(fresh_screenshot, baseline_image)
            distance = abs(diff.get_distance())
            if distance > threshold:
                raise AssertionError("The new screenshot did not match "
                                     "the baseline (by a distance of %.2f)"
                                     % distance)
        else:
            baseline_file = os.path.join(self.baseline_directory, '%s.png' % file)
            output_file = os.path.join(self.output_directory, '%s.png' % file)

            # Determine whether we should save the baseline image
            save_baseline = False
            if self.save_baseline:
                save_baseline = True
            elif self.capture:
                warn("The 'NeedleTestCase.capture' attribute and '--with-save-baseline' nose option "
                     "are deprecated since version 0.2.0. Use 'save_baseline' and '--with-save-baseline' "
                     "instead. See the changelog for more information.",
                     PendingDeprecationWarning)
                if os.path.exists(baseline_file):
                    self.skipTest('Not capturing %s, its baseline image already exists. If you '
                                  'want to capture this element again, delete %s'
                                  % (file, baseline_file))
                else:
                    save_baseline = True

            if save_baseline:
                # Save the baseline screenshot and bail out
                element.get_screenshot().save(baseline_file)
                return
            else:
                if not os.path.exists(baseline_file):
                    raise IOError('The baseline screenshot %s does not exist. '
                                  'You might want to re-run this test in baseline-saving mode.'
                                  % baseline_file)

                # Save the new screenshot
                element.get_screenshot().save(output_file)

                self.engine.assertSameFiles(output_file, baseline_file, threshold)

########NEW FILE########
__FILENAME__ = driver
# encoding: utf-8
from __future__ import absolute_import

import base64
import os
import sys

if sys.version_info >= (3, 0):
    from urllib.parse import quote
    from io import BytesIO as IOClass
else:
    from urllib import quote
    try:
        from cStringIO import StringIO as IOClass
    except ImportError:
        from StringIO import StringIO as IOClass


from PIL import Image


from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.firefox.webdriver import WebDriver as Firefox
from selenium.webdriver.chrome.webdriver import WebDriver as Chrome
from selenium.webdriver.ie.webdriver import WebDriver as Ie
from selenium.webdriver.opera.webdriver import WebDriver as Opera
from selenium.webdriver.safari.webdriver import WebDriver as Safari
from selenium.webdriver.phantomjs.webdriver import WebDriver as PhantomJS
from selenium.webdriver.remote.webdriver import WebDriver as Remote


class NeedleWebElement(WebElement):
    """
    An element on a page that Selenium has opened.

    It is a Selenium :py:class:`~selenium.webdriver.remote.webelement.WebElement`
    object with some extra methods for testing CSS.
    """
    def get_dimensions(self):
        """
        Returns a dictionary containing, in pixels, the element's ``width`` and
        ``height``, and it's ``left`` and ``top`` position relative to the document.
        """
        self._parent.load_jquery()
        return self._parent.execute_script("""
            var e = $(arguments[0]);
            var offset = e.offset();
            var dimensions = {
                'width': e.outerWidth(),
                'height': e.outerHeight(),
                'left': Math.floor(offset.left),
                'top': Math.floor(offset.top)
            };
            return dimensions;
        """, self)

    def get_screenshot(self):
        """
        Returns a screenshot of this element as a PIL image.
        """
        d = self.get_dimensions()
        return self._parent.get_screenshot_as_image().crop((
            d['left'],
            d['top'],
            d['left'] + d['width'],
            d['top'] + d['height'],
        ))


class NeedleWebDriverMixin(object):
    """
    Selenium WebDriver mixin with some extra methods for testing CSS.
    """
    def load_html(self, html):
        """
        Similar to :py:meth:`get`, but instead of passing a URL to load in the
        browser, the HTML for the page is provided.
        """
        self.get('data:text/html,' + quote(html))

    def get_screenshot_as_image(self):
        """
        Returns a screenshot of the current page as an RGB
        `PIL image <http://www.pythonware.com/library/pil/handbook/image.htm>`_.
        """
        fh = IOClass(base64.b64decode(self.get_screenshot_as_base64().encode('ascii')))
        return Image.open(fh).convert('RGB')

    def load_jquery(self):
        """
        Loads jQuery onto the current page so calls to
        :py:meth:`execute_script` have access to it.
        """
        if (self.execute_script('return typeof(jQuery)') == 'undefined'):
            self.execute_script(open(
                os.path.join(self._get_js_path(), 'jquery-1.11.0.min.js')
            ).read() + '\nreturn "";')

    def _get_js_path(self):
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'js')

    def create_web_element(self, *args, **kwargs):
        return NeedleWebElement(self, *args, **kwargs)


class NeedleRemote(NeedleWebDriverMixin, Remote):
    """
    The same as Selenium's remote WebDriver, but with NeedleWebDriverMixin's
    functionality.
    """

class NeedlePhantomJS(NeedleWebDriverMixin, PhantomJS):
    """
    The same as Selenium's PhantomJS WebDriver, but with NeedleWebDriverMixin's
    functionality.
    """

class NeedleFirefox(NeedleWebDriverMixin, Firefox):
    """
    The same as Selenium's Firefox WebDriver, but with NeedleWebDriverMixin's
    functionality.
    """

class NeedleChrome(NeedleWebDriverMixin, Chrome):
    """
    The same as Selenium's Chrome WebDriver, but with NeedleWebDriverMixin's
    functionality.
    """

class NeedleIe(NeedleWebDriverMixin, Ie):
    """
    The same as Selenium's Internet Explorer WebDriver, but with
    NeedleWebDriverMixin's functionality.
    """

class NeedleOpera(NeedleWebDriverMixin, Opera):
    """
    The same as Selenium's Opera WebDriver, but with NeedleWebDriverMixin's
    functionality.
    """

class NeedleSafari(NeedleWebDriverMixin, Safari):
    """
    The same as Selenium's Safari WebDriver, but with NeedleWebDriverMixin's
    functionality.
    """

########NEW FILE########
__FILENAME__ = base
class EngineBase(object):
    """
    Base class for diff engines.
    """

    def assertSameFiles(self, output_file, baseline_file, threshold):
        raise NotImplementedError
########NEW FILE########
__FILENAME__ = perceptualdiff_engine
import subprocess
import os

from PIL import Image

from needle.engines.base import EngineBase


class Engine(EngineBase):

    perceptualdiff_path = 'perceptualdiff'
    perceptualdiff_output_png = True

    def assertSameFiles(self, output_file, baseline_file, threshold):
        # Calculate threshold value as a pixel number instead of percentage.
        width, height = Image.open(open(output_file)).size
        threshold = int(width * height * threshold)

        diff_ppm = output_file.replace(".png", ".diff.ppm")
        cmd = "%s -threshold %d -output %s %s %s" % (
            self.perceptualdiff_path, threshold, diff_ppm, baseline_file, output_file)
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        perceptualdiff_stdout, _ = process.communicate()

        if process.returncode == 0:
            # No differences found
            return
        else:
            if os.path.exists(diff_ppm):
                if self.perceptualdiff_output_png:
                    # Convert the .ppm output to .png
                    diff_png = diff_ppm.replace("diff.ppm", "diff.png")
                    Image.open(diff_ppm).save(diff_png)
                    os.remove(diff_ppm)
                    diff_file_msg = ' (See %s)' % diff_png
                else:
                    diff_file_msg = ' (See %s)' % diff_ppm
            else:
                diff_file_msg = ''
            raise AssertionError("The new screenshot '%s' did not match "
                                 "the baseline '%s'%s:\n%s"
                                 % (output_file, baseline_file, diff_file_msg, perceptualdiff_stdout))
########NEW FILE########
__FILENAME__ = pil_engine
import sys
from itertools import chain
import math

if sys.version_info >= (3, 0):
    izip = zip
else:
    from itertools import izip

from PIL import Image

from needle.engines.base import EngineBase


class Engine(EngineBase):

    def assertSameFiles(self, output_file, baseline_file, threshold):
        output_image = Image.open(output_file).convert('RGB')
        baseline_image = Image.open(baseline_file).convert('RGB')
        diff = ImageDiff(output_image, baseline_image)
        distance = abs(diff.get_distance())
        if distance > threshold:
            raise AssertionError("The new screenshot '%s' did not match "
                                 "the baseline '%s' (by a distance of %.2f)"
                                 % (output_file, baseline_file, distance))


class ImageDiff(object):
    """
    Utility class for performing image comparisons using PIL.
    """

    def __init__(self, image_a, image_b):
        assert image_a.size == image_b.size
        assert image_a.getbands() == image_b.getbands()

        self.image_a = image_a
        self.image_b = image_b

    def get_nrmsd(self):
        """
        Returns the normalised root mean squared deviation of the two images.
        """
        a_values = chain(*self.image_a.getdata())
        b_values = chain(*self.image_b.getdata())
        rmsd = 0
        for a, b in izip(a_values, b_values):
            rmsd += (a - b) ** 2
        rmsd = math.sqrt(float(rmsd) / (
            self.image_a.size[0] * self.image_a.size[1] * len(self.image_a.getbands())
        ))
        return rmsd / 255

    def get_distance(self):
        """
        Returns the distance between the two images in pixels.
        """
        a_values = chain(*self.image_a.getdata())
        b_values = chain(*self.image_b.getdata())
        band_len = len(self.image_a.getbands())
        distance = 0
        for a, b in izip(a_values, b_values):
            distance += abs(float(a) / band_len - float(b) / band_len) / 255
        return distance
########NEW FILE########
__FILENAME__ = plugin
from nose.plugins import Plugin

class NeedleCapturePlugin(Plugin):
    """
    A nose plugin which causes all calls to
    ``NeedleTestCase.assertScreenshot`` to save a baseline screenshot to disk,
    unless the baseline file already exists.
    """
    name = 'needle-capture'

    def wantClass(self, cls):
        # Only gather classes which are a needle test case
        return hasattr(cls, 'assertScreenshot')

    def wantFunction(self, f):
        return False

    def beforeTest(self, test):
        if hasattr(test, 'test'):
            test.test.capture = True



class SaveBaselinePlugin(Plugin):
    """
    A nose plugin which causes all calls to ``NeedleTestCase.assertScreenshot``
    to save the baseline screenshot to disk.
    """
    name = 'save-baseline'

    def add_options(self, parser, env=None):
        super(SaveBaselinePlugin, self).add_options(parser, env)

    def wantClass(self, cls):
        # Only gather classes which are a needle test case
        return hasattr(cls, 'assertScreenshot')

    def wantFunction(self, f):
        return False

    def beforeTest(self, test):
        if hasattr(test, 'test'):
            test.test.save_baseline = True
########NEW FILE########
__FILENAME__ = red_box
from needle.cases import NeedleTestCase
from tests import ImageTestCaseMixin

class RedBoxTestCase(ImageTestCaseMixin, NeedleTestCase):
    def test_red_box(self):
        self.driver.load_html("""
            <style type="text/css">
                #test {
                    position: absolute;
                    left: 50px;
                    top: 100px;
                    width: 100px;
                    height: 100px;
                    background-color: red;
                }
            </style>
            <div id="test"></div>
        """)
        self.assertScreenshot(self.driver.find_element_by_id('test'), 'red_box')
########NEW FILE########
__FILENAME__ = test_case
from __future__ import with_statement
from needle.cases import NeedleTestCase
from PIL import Image
from . import ImageTestCaseMixin

class NeedleTestCaseTest(ImageTestCaseMixin, NeedleTestCase):
    def create_div(self):
        self.driver.load_html("""
            <style type="text/css">
                #test {
                    position: absolute;
                    left: 50px;
                    top: 100px;
                    width: 100px;
                    height: 100px;
                    background-color: black;
                }
            </style>
            <div id="test"></div>
        """)

    def test_assertScreenshot(self):
        self.create_div()
        self.assertScreenshot(
            self.driver.find_element_by_id('test'), 
            self.save_image_to_fh(self.get_black_image())
        )

    def test_assertScreenshot_with_css_selector(self):
        self.create_div()
        self.assertScreenshot('#test', self.save_image_to_fh(self.get_black_image()))

    def test_assertScreenshot_fails(self):
        self.create_div()
        im = self.get_black_image()
        # Create one red pixel
        im.putpixel((0, 0), (255, 0, 0))
        with self.assertRaises(AssertionError):
            # Default threshold for error is 0
            self.assertScreenshot(
                self.driver.find_element_by_id('test'), 
                self.save_image_to_fh(im)
            )

    def test_assertScreenshot_does_not_fail_with_threshold(self):
        self.create_div()
        im = self.get_black_image()
        # Create one red pixel
        im.putpixel((0, 0), (255, 0, 0))
        self.assertScreenshot(
            self.driver.find_element_by_id('test'), 
            self.save_image_to_fh(im),
            threshold=1
        )

    def test_assertScreenshot_fails_with_threshold(self):
        self.create_div()
        im = self.get_black_image()
        # Create two white pixels
        im.putpixel((0, 0), (255, 255, 255))
        im.putpixel((1, 0), (255, 255, 255))
        with self.assertRaises(AssertionError):
            self.assertScreenshot(
                self.driver.find_element_by_id('test'), 
                self.save_image_to_fh(im),
                threshold=1
            )



########NEW FILE########
__FILENAME__ = test_diff
import math
import sys

if sys.version_info > (2, 7):
    from unittest import TestCase
else:
    from unittest2 import TestCase

from needle.engines.pil_engine import ImageDiff
from . import ImageTestCaseMixin

class TestImageDiff(ImageTestCaseMixin, TestCase):
    def test_nrmsd_all_channels(self):
        diff = ImageDiff(self.get_white_image(), self.get_black_image())
        self.assertEqual(diff.get_nrmsd(), 1)

    def test_nrmsd_one_channel(self):
        diff = ImageDiff(self.get_image((255, 0, 0)), self.get_black_image())
        self.assertEqual(diff.get_nrmsd(), math.sqrt(1.0 / 3))

    def test_nrmsd_half_filled(self):
        diff = ImageDiff(self.get_black_image(), self.get_half_filled_image())
        self.assertEqual(diff.get_nrmsd(), math.sqrt(0.5))

    def test_distance_all_channels(self):
        diff = ImageDiff(self.get_white_image(), self.get_black_image())
        self.assertAlmostEqual(diff.get_distance(), 100 * 100, delta=0.001)

    def test_distance_one_channel(self):
        diff = ImageDiff(self.get_image((255, 0, 0)), self.get_black_image())
        self.assertAlmostEqual(diff.get_distance(), 10000.0 / 3, delta=0.001)

    def test_distance_half_filled(self):
        diff = ImageDiff(self.get_black_image(), self.get_half_filled_image())
        self.assertAlmostEqual(diff.get_distance(), 10000.0 / 2, delta=0.001)




########NEW FILE########
__FILENAME__ = test_driver
from needle.cases import NeedleTestCase

class TestWebDriver(NeedleTestCase):
    def test_load_html(self):
        self.driver.load_html('<div id="test">foo</div>')
        e = self.driver.find_element_by_id('test')
        self.assertEqual(e.text, 'foo')

    def test_load_html_works_with_large_pages(self):
        div = '<div>' + 'a' * 1000 + '</div>'
        html = ''.join(div for _ in range(500)) + '<div id="test">hello</div>'
        self.driver.load_html(html)
        self.assertEqual(
            self.driver.execute_script(
                'return document.getElementsByTagName("div").length'
            ),
            501
        )
        e = self.driver.find_element_by_id('test')
        self.assertEqual(e.text, 'hello')

    def test_load_jquery(self):
        self.driver.load_html('<div></div>')
        self.driver.load_jquery()
        self.assertTrue(self.driver.execute_script("""
            return jQuery !== undefined;
        """))


class TestWebElement(NeedleTestCase):
    def test_get_dimensions(self):
        self.driver.load_html("""
            <style type="text/css">
                #test {
                    position: absolute;
                    left: 50px;
                    top: 100px;
                    width: 150px;
                    height: 200px;
                }
            </style>
            <div id="test">Test</div>
        """)
        e = self.driver.find_element_by_id('test')
        self.assertEqual(e.get_dimensions(), {
            'left': 50,
            'top': 100,
            'width': 150,
            'height': 200,
        })

    def test_get_screenshot(self):
        self.driver.load_html("""
            <style type="text/css">
                #test {
                    position: absolute;
                    left: 50px;
                    top: 100px;
                    width: 150px;
                    height: 200px;
                    background-color: #FF0000;
                }
            </style>
            <div id="test"></div>
        """)
        e = self.driver.find_element_by_id('test')
        im = e.get_screenshot()
        self.assertEqual(im.size, (150, 200))
        for pixel in im.getdata():
            self.assertEqual(pixel, (255, 0, 0))

########NEW FILE########
__FILENAME__ = test_plugin
import sys
import os

from needle.plugin import NeedleCapturePlugin, SaveBaselinePlugin
from nose.plugins import PluginTester

if sys.version_info > (2, 7):
    from unittest import TestCase
else:
    from unittest2 import TestCase


baseline_filename = 'screenshots/baseline/red_box.png'
dummy_baseline_content = b'abcd'


class NeedleCaptureTest(PluginTester, TestCase):
    """
    Check that the baseline file gets saved when using the
    --with-needle-capture option.
    """
    activate = '--with-needle-capture'
    plugins = [NeedleCapturePlugin()]
    suitepath = 'tests/plugin_test_cases/red_box.py'

    def setUp(self):
        self.assertFalse(os.path.exists(baseline_filename))
        super(NeedleCaptureTest, self).setUp()

    def tearDown(self):
        os.remove(baseline_filename)

    def test_baseline_is_saved(self):
        self.assertTrue(os.path.exists(baseline_filename))
        self.assertTrue(self.nose.success)


class NeedleCaptureOverwriteTest(PluginTester, TestCase):
    """
    Check that an existing baseline file does NOT get overwritten, when using
    the --with-needle-capture option.
    """

    activate = '--with-needle-capture'
    plugins = [NeedleCapturePlugin()]
    suitepath = 'tests/plugin_test_cases/red_box.py'

    def setUp(self):
        self.assertFalse(os.path.exists(baseline_filename))

        # Create dummy baseline file
        baseline = open(baseline_filename, 'wb')
        baseline.write(dummy_baseline_content)
        baseline.close()

        super(NeedleCaptureOverwriteTest, self).setUp()

    def tearDown(self):
        os.remove(baseline_filename)

    def test_existing_baseline_not_overwritten(self):
        baseline = open(baseline_filename, 'rb')
        self.assertEqual(baseline.read(), dummy_baseline_content)
        self.assertTrue(self.nose.success)



class SaveBaselineTest(PluginTester, TestCase):
    """
    Check that the baseline file gets saved when using the
    --with-save-baseline option.
    """
    activate = '--with-save-baseline'
    plugins = [SaveBaselinePlugin()]
    suitepath = 'tests/plugin_test_cases/red_box.py'

    def setUp(self):
        self.assertFalse(os.path.exists(baseline_filename))
        super(SaveBaselineTest, self).setUp()

    def tearDown(self):
        os.remove(baseline_filename)

    def test_baseline_is_saved(self):
        self.assertTrue(os.path.exists(baseline_filename))
        self.assertTrue(self.nose.success)


class SaveBaselineOverwriteTest(PluginTester, TestCase):
    """
    Check that an existing baseline file DOES get overwritten, when using
    the --with-save-baseline option.
    """

    activate = '--with-save-baseline'
    plugins = [SaveBaselinePlugin()]
    suitepath = 'tests/plugin_test_cases/red_box.py'

    def setUp(self):
        self.assertFalse(os.path.exists(baseline_filename))

        # Create dummy baseline file
        baseline = open(baseline_filename, 'wb')
        baseline.write(dummy_baseline_content)
        baseline.close()

        super(SaveBaselineOverwriteTest, self).setUp()

    def tearDown(self):
        os.remove(baseline_filename)

    def test_existing_baseline_is_overwritten(self):
        baseline = open(baseline_filename, 'rb')
        self.assertNotEqual(baseline.read(), dummy_baseline_content)
        self.assertTrue(self.nose.success)
########NEW FILE########