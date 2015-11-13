__FILENAME__ = ddt
import inspect
import json
import os
import re
from functools import wraps

__version__ = '0.8.0'

# These attributes will not conflict with any real python attribute
# They are added to the decorated test method and processed later
# by the `ddt` class decorator.

DATA_ATTR = '%values'      # store the data the test must run with
FILE_ATTR = '%file_path'   # store the path to JSON file
UNPACK_ATTR = '%unpack'    # remember that we have to unpack values


def unpack(func):
    """
    Method decorator to add unpack feature.

    """
    setattr(func, UNPACK_ATTR, True)
    return func


def data(*values):
    """
    Method decorator to add to your test methods.

    Should be added to methods of instances of ``unittest.TestCase``.

    """
    def wrapper(func):
        setattr(func, DATA_ATTR, values)
        return func
    return wrapper


def file_data(value):
    """
    Method decorator to add to your test methods.

    Should be added to methods of instances of ``unittest.TestCase``.

    ``value`` should be a path relative to the directory of the file
    containing the decorated ``unittest.TestCase``. The file
    should contain JSON encoded data, that can either be a list or a
    dict.

    In case of a list, each value in the list will correspond to one
    test case, and the value will be concatenated to the test method
    name.

    In case of a dict, keys will be used as suffixes to the name of the
    test case, and values will be fed as test data.

    """
    def wrapper(func):
        setattr(func, FILE_ATTR, value)
        return func
    return wrapper


def mk_test_name(name, value, index=0):
    """
    Generate a new name for a test case.

    It will take the original test name and append an ordinal index and a
    string representation of the value, and convert the result into a valid
    python identifier by replacing extraneous characters with ``_``.

    """
    try:
        value = str(value)
    except UnicodeEncodeError:
        # fallback for python2
        value = value.encode('ascii', 'backslashreplace')
    test_name = "{0}_{1}_{2}".format(name, index + 1, value)
    return re.sub('\W|^(?=\d)', '_', test_name)


def ddt(cls):
    """
    Class decorator for subclasses of ``unittest.TestCase``.

    Apply this decorator to the test case class, and then
    decorate test methods with ``@data``.

    For each method decorated with ``@data``, this will effectively create as
    many methods as data items are passed as parameters to ``@data``.

    The names of the test methods follow the pattern
    ``original_test_name_{ordinal}_{data}``. ``ordinal`` is the position of the
    data argument, starting with 1.

    For data we use a string representation of the data value converted into a
    valid python identifier.  If ``data.__name__`` exists, we use that instead.

    For each method decorated with ``@file_data('test_data.json')``, the
    decorator will try to load the test_data.json file located relative
    to the python file containing the method that is decorated. It will,
    for each ``test_name`` key create as many methods in the list of values
    from the ``data`` key.

    """
    def feed_data(func, new_name, *args, **kwargs):
        """
        This internal method decorator feeds the test data item to the test.

        """
        @wraps(func)
        def wrapper(self):
            return func(self, *args, **kwargs)
        wrapper.__name__ = new_name
        return wrapper

    def add_test(test_name, func, *args, **kwargs):
        """
        Add a test case to this class.

        The test will be based on an existing function but will give it a new
        name.

        """
        setattr(cls, test_name, feed_data(func, test_name, *args, **kwargs))

    def process_file_data(name, func, file_attr):
        """
        Process the parameter in the `file_data` decorator.

        """
        cls_path = os.path.abspath(inspect.getsourcefile(cls))
        data_file_path = os.path.join(os.path.dirname(cls_path), file_attr)

        def _raise_ve(*args):
            raise ValueError("%s does not exist" % file_attr)

        if os.path.exists(data_file_path) is False:
            test_name = mk_test_name(name, "error")
            add_test(test_name, _raise_ve, None)
        else:
            data = json.loads(open(data_file_path).read())
            for i, elem in enumerate(data):
                if isinstance(data, dict):
                    key, value = elem, data[elem]
                    test_name = mk_test_name(name, key, i)
                elif isinstance(data, list):
                    value = elem
                    test_name = mk_test_name(name, value, i)
                add_test(test_name, func, value)

    for name, func in list(cls.__dict__.items()):
        if hasattr(func, DATA_ATTR):
            for i, v in enumerate(getattr(func, DATA_ATTR)):
                test_name = mk_test_name(name, getattr(v, "__name__", v), i)
                if hasattr(func, UNPACK_ATTR):
                    if isinstance(v, tuple) or isinstance(v, list):
                        add_test(test_name, func, *v)
                    else:
                        # unpack dictionary
                        add_test(test_name, func, **v)
                else:
                    add_test(test_name, func, v)
            delattr(cls, name)
        elif hasattr(func, FILE_ATTR):
            file_attr = getattr(func, FILE_ATTR)
            process_file_data(name, func, file_attr)
            delattr(cls, name)
    return cls

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# DDT documentation build configuration file, created by
# sphinx-quickstart on Tue Feb 21 23:00:01 2012.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

# Specific for readthedocs.org
on_rtd = os.environ.get('READTHEDOCS', None) == 'True'

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))
docs_root = os.path.dirname(__file__)
sys.path.insert(0, os.path.split(docs_root)[0])

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc']
if not on_rtd:
    extensions.append('sphinxcontrib.programoutput')

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'DDT'
copyright = u'2012, Carles Barrobés'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.

from ddt import __version__
# The short X.Y version.
version = __version__
# The full version, including alpha/beta/rc tags.
release = __version__

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
if on_rtd:
    html_theme = 'default'
else:
    html_theme = 'sphinxdoc'

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
htmlhelp_basename = 'DDTdoc'


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
  ('index', 'DDT.tex', u'DDT Documentation',
   u'Carles Barrobés', 'manual'),
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
    ('index', 'ddt', u'DDT Documentation',
     [u'Carles Barrobés'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'DDT', u'DDT Documentation',
   u'Carles Barrobés', 'DDT', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

########NEW FILE########
__FILENAME__ = mycode
"""
Some simple functions that we will use in our tests.
"""


def larger_than_two(value):
    return value > 2


def has_three_elements(value):
    return len(value) == 3


def is_a_greeting(value):
    return value in ['Hello', 'Goodbye']

########NEW FILE########
__FILENAME__ = test_example
import unittest
from ddt import ddt, data, file_data, unpack
from test.mycode import larger_than_two, has_three_elements, is_a_greeting


class mylist(list):
    pass


def annotated(a, b):
    r = mylist([a, b])
    setattr(r, "__name__", "test_%d_greater_than_%d" % (a, b))
    return r


@ddt
class FooTestCase(unittest.TestCase):
    def test_undecorated(self):
        self.assertTrue(larger_than_two(24))

    @data(3, 4, 12, 23)
    def test_larger_than_two(self, value):
        self.assertTrue(larger_than_two(value))

    @data(1, -3, 2, 0)
    def test_not_larger_than_two(self, value):
        self.assertFalse(larger_than_two(value))

    @data(annotated(2, 1), annotated(10, 5))
    def test_greater(self, value):
        a, b = value
        self.assertGreater(a, b)

    @file_data('test_data_dict.json')
    def test_file_data_dict(self, value):
        self.assertTrue(has_three_elements(value))

    @file_data('test_data_list.json')
    def test_file_data_list(self, value):
        self.assertTrue(is_a_greeting(value))

    @data((3, 2), (4, 3), (5, 3))
    @unpack
    def test_tuples_extracted_into_arguments(self, first_value, second_value):
        self.assertTrue(first_value > second_value)

    @data([3, 2], [4, 3], [5, 3])
    @unpack
    def test_list_extracted_into_arguments(self, first_value, second_value):
        self.assertTrue(first_value > second_value)

    @unpack
    @data({'first': 1, 'second': 3, 'third': 2},
          {'first': 4, 'second': 6, 'third': 5})
    def test_dicts_extracted_into_kwargs(self, first, second, third):
        self.assertTrue(first < third < second)

    @data(u'ascii', u'non-ascii-\N{SNOWMAN}')
    def test_unicode(self, value):
        self.assertIn(value, (u'ascii', u'non-ascii-\N{SNOWMAN}'))

########NEW FILE########
__FILENAME__ = test_functional
import os
import json

import six

from ddt import ddt, data, file_data
from nose.tools import assert_equal, assert_is_not_none, assert_raises


@ddt
class Dummy(object):
    """
    Dummy class to test the data decorator on
    """

    @data(1, 2, 3, 4)
    def test_something(self, value):
        return value


@ddt
class DummyInvalidIdentifier():
    """
    Dummy class to test the data decorator receiving values invalid characters
    indentifiers
    """

    @data('32v2 g #Gmw845h$W b53wi.')
    def test_data_with_invalid_identifier(self, value):
        return value


@ddt
class FileDataDummy(object):
    """
    Dummy class to test the file_data decorator on
    """

    @file_data("test_data_dict.json")
    def test_something_again(self, value):
        return value


@ddt
class FileDataMissingDummy(object):
    """
    Dummy class to test the file_data decorator on when
    JSON file is missing
    """

    @file_data("test_data_dict_missing.json")
    def test_something_again(self, value):
        return value


def test_data_decorator():
    """
    Test the ``data`` method decorator
    """

    def hello():
        pass

    pre_size = len(hello.__dict__)
    keys = set(hello.__dict__.keys())
    data_hello = data(1, 2)(hello)
    dh_keys = set(data_hello.__dict__.keys())
    post_size = len(data_hello.__dict__)

    assert_equal(post_size, pre_size + 1)
    extra_attrs = dh_keys - keys
    assert_equal(len(extra_attrs), 1)
    extra_attr = extra_attrs.pop()
    assert_equal(getattr(data_hello, extra_attr), (1, 2))


def test_file_data_decorator_with_dict():
    """
    Test the ``file_data`` method decorator
    """

    def hello():
        pass

    pre_size = len(hello.__dict__)
    keys = set(hello.__dict__.keys())
    data_hello = data("test_data_dict.json")(hello)

    dh_keys = set(data_hello.__dict__.keys())
    post_size = len(data_hello.__dict__)

    assert_equal(post_size, pre_size + 1)
    extra_attrs = dh_keys - keys
    assert_equal(len(extra_attrs), 1)
    extra_attr = extra_attrs.pop()
    assert_equal(getattr(data_hello, extra_attr), ("test_data_dict.json",))


is_test = lambda x: x.startswith('test_')


def test_ddt():
    """
    Test the ``ddt`` class decorator
    """
    tests = len(list(filter(is_test, Dummy.__dict__)))
    assert_equal(tests, 4)


def test_file_data_test_creation():
    """
    Test that the ``file_data`` decorator creates two tests
    """

    tests = len(list(filter(is_test, FileDataDummy.__dict__)))
    assert_equal(tests, 2)


def test_file_data_test_names_dict():
    """
    Test that ``file_data`` creates tests with the correct name

    Name is the the function name plus the key in the JSON data,
    when it is parsed as a dictionary.
    """

    tests = set(filter(is_test, FileDataDummy.__dict__))

    tests_dir = os.path.dirname(__file__)
    test_data_path = os.path.join(tests_dir, 'test_data_dict.json')
    test_data = json.loads(open(test_data_path).read())
    created_tests = set([
        "test_something_again_{0}_{1}".format(index + 1, name)
        for index, name in enumerate(test_data.keys())
    ])

    assert_equal(tests, created_tests)


def test_feed_data_data():
    """
    Test that data is fed to the decorated tests
    """
    tests = filter(is_test, Dummy.__dict__)

    values = []
    obj = Dummy()
    for test in tests:
        method = getattr(obj, test)
        values.append(method())

    assert_equal(set(values), set([1, 2, 3, 4]))


def test_feed_data_file_data():
    """
    Test that data is fed to the decorated tests from a file
    """
    tests = filter(is_test, FileDataDummy.__dict__)

    values = []
    obj = FileDataDummy()
    for test in tests:
        method = getattr(obj, test)
        values.extend(method())

    assert_equal(set(values), set([10, 12, 15, 15, 12, 50]))


def test_feed_data_file_data_missing_json():
    """
    Test that a ValueError is raised
    """
    tests = filter(is_test, FileDataMissingDummy.__dict__)

    obj = FileDataMissingDummy()
    for test in tests:
        method = getattr(obj, test)
        assert_raises(ValueError, method)


def test_ddt_data_name_attribute():
    """
    Test the ``__name__`` attribute handling of ``data`` items with ``ddt``
    """

    def hello():
        pass

    class myint(int):
        pass

    class mytest(object):
        pass

    d1 = myint(1)
    d1.__name__ = 'data1'

    d2 = myint(2)

    data_hello = data(d1, d2)(hello)
    setattr(mytest, 'test_hello', data_hello)

    ddt_mytest = ddt(mytest)
    assert_is_not_none(getattr(ddt_mytest, 'test_hello_1_data1'))
    assert_is_not_none(getattr(ddt_mytest, 'test_hello_2_2'))


def test_ddt_data_unicode():
    """
    Test that unicode strings are converted to function names correctly
    """

    def hello():
        pass

    # We test unicode support separately for python 2 and 3

    if six.PY2:

        @ddt
        class mytest(object):
            @data(u'ascii', u'non-ascii-\N{SNOWMAN}', {u'\N{SNOWMAN}': 'data'})
            def test_hello(self, val):
                pass

        assert_is_not_none(getattr(mytest, 'test_hello_1_ascii'))
        assert_is_not_none(getattr(mytest, 'test_hello_2_non_ascii__u2603'))
        assert_is_not_none(getattr(mytest, 'test_hello_3__u__u2603____data__'))

    elif six.PY3:

        @ddt
        class mytest(object):
            @data('ascii', 'non-ascii-\N{SNOWMAN}', {'\N{SNOWMAN}': 'data'})
            def test_hello(self, val):
                pass

        assert_is_not_none(getattr(mytest, 'test_hello_1_ascii'))
        assert_is_not_none(getattr(mytest, 'test_hello_2_non_ascii__'))
        assert_is_not_none(getattr(mytest, 'test_hello_3________data__'))


def test_feed_data_with_invalid_identifier():
    """
    Test that data is fed to the decorated tests
    """
    tests = list(filter(is_test, DummyInvalidIdentifier.__dict__))
    assert_equal(len(tests), 1)

    obj = DummyInvalidIdentifier()
    method = getattr(obj, tests[0])
    assert_equal(
        method.__name__,
        'test_data_with_invalid_identifier_1_32v2_g__Gmw845h_W_b53wi_'
    )
    assert_equal(method(), '32v2 g #Gmw845h$W b53wi.')

########NEW FILE########
