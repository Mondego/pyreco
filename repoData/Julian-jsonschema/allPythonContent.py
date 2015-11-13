__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# This file is execfile()d with the current directory set to its containing dir.

from textwrap import dedent
import sys, os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
ext_paths = [os.path.abspath(os.path.pardir), os.path.dirname(__file__)]
sys.path = ext_paths + sys.path

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.coverage',
    'sphinx.ext.doctest',
    'sphinx.ext.intersphinx',
    'sphinx.ext.viewcode',
    'jsonschema_role',
]

cache_path = "_cache"

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'jsonschema'
copyright = u'2013, Julian Berman'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# version: The short X.Y version
# release: The full version, including alpha/beta/rc tags.
from jsonschema import __version__ as release
version = release.partition("-")[0]

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build', "_cache", "_static", "_templates"]

# The reST default role (used for this markup: `text`) to use for all documents.
#default_role = None

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []

doctest_global_setup = dedent("""
    from __future__ import print_function
    from jsonschema import *
""")

intersphinx_mapping = {"python": ("http://docs.python.org/2.7", None)}


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'pyramid'

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
# html_static_path = ['_static']

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
htmlhelp_basename = 'jsonschemadoc'


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
  ('index', 'jsonschema.tex', u'jsonschema Documentation',
   u'Julian Berman', 'manual'),
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
    ('index', 'jsonschema', u'jsonschema Documentation',
     [u'Julian Berman'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'jsonschema', u'jsonschema Documentation',
   u'Julian Berman', 'jsonschema', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

# -- Read the Docs -------------------------------------------------------------

# Ooo pretty.
RTD_NEW_THEME = True

########NEW FILE########
__FILENAME__ = jsonschema_role
from datetime import datetime
from docutils import nodes
import errno
import os

try:
    import urllib2 as urllib
except ImportError:
    import urllib.request as urllib

from lxml import html


VALIDATION_SPEC = "http://json-schema.org/latest/json-schema-validation.html"


def setup(app):
    """
    Install the plugin.

    :argument sphinx.application.Sphinx app: the Sphinx application context

    """

    app.add_config_value("cache_path", "_cache", "")

    try:
        os.makedirs(app.config.cache_path)
    except OSError as error:
        if error.errno != errno.EEXIST:
            raise

    path = os.path.join(app.config.cache_path, "spec.html")
    spec = fetch_or_load(path)
    app.add_role("validator", docutils_sucks(spec))


def fetch_or_load(spec_path):
    """
    Fetch a new specification or use the cache if it's current.

    :argument cache_path: the path to a cached specification

    """

    headers = {}

    try:
        modified = datetime.utcfromtimestamp(os.path.getmtime(spec_path))
        date = modified.strftime("%a, %d %b %Y %I:%M:%S UTC")
        headers["If-Modified-Since"] = date
    except OSError as error:
        if error.errno != errno.ENOENT:
            raise

    request = urllib.Request(VALIDATION_SPEC, headers=headers)
    response = urllib.urlopen(request)

    if response.code == 200:
        with open(spec_path, "w+b") as spec:
            spec.writelines(response)
            spec.seek(0)
            return html.parse(spec)

    with open(spec_path) as spec:
        return html.parse(spec)


def docutils_sucks(spec):
    """
    Yeah.

    It doesn't allow using a class because it does stupid stuff like try to set
    attributes on the callable object rather than just keeping a dict.

    """

    base_url = VALIDATION_SPEC
    ref_url = "http://json-schema.org/latest/json-schema-core.html#anchor25"
    schema_url = "http://json-schema.org/latest/json-schema-core.html#anchor22"

    def validator(name, raw_text, text, lineno, inliner):
        """
        Link to the JSON Schema documentation for a validator.

        :argument str name: the name of the role in the document
        :argument str raw_source: the raw text (role with argument)
        :argument str text: the argument given to the role
        :argument int lineno: the line number
        :argument docutils.parsers.rst.states.Inliner inliner: the inliner

        :returns: 2-tuple of nodes to insert into the document and an iterable
            of system messages, both possibly empty

        """

        if text == "$ref":
            return [nodes.reference(raw_text, text, refuri=ref_url)], []
        elif text == "$schema":
            return [nodes.reference(raw_text, text, refuri=schema_url)], []

        xpath = "//h3[re:match(text(), '(^|\W)\"?{0}\"?($|\W,)', 'i')]"
        header = spec.xpath(
            xpath.format(text),
            namespaces={"re": "http://exslt.org/regular-expressions"},
        )

        if len(header) == 0:
            inliner.reporter.warning(
                "Didn't find a target for {0}".format(text),
            )
            uri = base_url
        else:
            if len(header) > 1:
                inliner.reporter.info(
                    "Found multiple targets for {0}".format(text),
                )
            uri = base_url + "#" + header[0].getprevious().attrib["name"]

        reference = nodes.reference(raw_text, text, refuri=uri)
        return [reference], []

    return validator

########NEW FILE########
__FILENAME__ = cli
from __future__ import absolute_import
import argparse
import json
import sys

from jsonschema._reflect import namedAny
from jsonschema.validators import validator_for


def _namedAnyWithDefault(name):
    if "." not in name:
        name = "jsonschema." + name
    return namedAny(name)


def _json_file(path):
    with open(path) as file:
        return json.load(file)


parser = argparse.ArgumentParser(
    description="JSON Schema Validation CLI",
)
parser.add_argument(
    "-i", "--instance",
    action="append",
    dest="instances",
    type=_json_file,
    help="a path to a JSON instance to validate "
         "(may be specified multiple times)",
)
parser.add_argument(
    "-F", "--error-format",
    default="{error.instance}: {error.message}\n",
    help="the format to use for each error output message, specified in "
         "a form suitable for passing to str.format, which will be called "
         "with 'error' for each error",
)
parser.add_argument(
    "-V", "--validator",
    type=_namedAnyWithDefault,
    help="the fully qualified object name of a validator to use, or, for "
          "validators that are registered with jsonschema, simply the name "
          "of the class.",
)
parser.add_argument(
    "schema",
    help="the JSON Schema to validate with",
    type=_json_file,
)


def parse_args(args):
    arguments = vars(parser.parse_args(args=args or ["--help"]))
    if arguments["validator"] is None:
        arguments["validator"] = validator_for(arguments["schema"])
    return arguments


def main(args=sys.argv[1:]):
    sys.exit(run(arguments=parse_args(args=args)))


def run(arguments, stdout=sys.stdout, stderr=sys.stderr):
    error_format = arguments["error_format"]
    validator = arguments["validator"](schema=arguments["schema"])
    errored = False
    for instance in arguments["instances"] or ():
        for error in validator.iter_errors(instance):
            stderr.write(error_format.format(error=error))
            errored = True
    return errored

########NEW FILE########
__FILENAME__ = compat
from __future__ import unicode_literals
import sys
import operator

try:
    from collections import MutableMapping, Sequence  # noqa
except ImportError:
    from collections.abc import MutableMapping, Sequence  # noqa

PY3 = sys.version_info[0] >= 3

if PY3:
    zip = zip
    from io import StringIO
    from urllib.parse import (
        unquote, urljoin, urlunsplit, SplitResult, urlsplit as _urlsplit
    )
    from urllib.request import urlopen
    str_types = str,
    int_types = int,
    iteritems = operator.methodcaller("items")
else:
    from itertools import izip as zip  # noqa
    from StringIO import StringIO
    from urlparse import (
        urljoin, urlunsplit, SplitResult, urlsplit as _urlsplit # noqa
    )
    from urllib import unquote  # noqa
    from urllib2 import urlopen  # noqa
    str_types = basestring
    int_types = int, long
    iteritems = operator.methodcaller("iteritems")


# On python < 3.3 fragments are not handled properly with unknown schemes
def urlsplit(url):
    scheme, netloc, path, query, fragment = _urlsplit(url)
    if "#" in path:
        path, fragment = path.split("#", 1)
    return SplitResult(scheme, netloc, path, query, fragment)


def urldefrag(url):
    if "#" in url:
        s, n, p, q, frag = urlsplit(url)
        defrag = urlunsplit((s, n, p, q, ''))
    else:
        defrag = url
        frag = ''
    return defrag, frag


# flake8: noqa

########NEW FILE########
__FILENAME__ = exceptions
from collections import defaultdict, deque
import itertools
import pprint
import textwrap

from jsonschema import _utils
from jsonschema.compat import PY3, iteritems


WEAK_MATCHES = frozenset(["anyOf", "oneOf"])
STRONG_MATCHES = frozenset()

_unset = _utils.Unset()


class _Error(Exception):
    def __init__(
        self,
        message,
        validator=_unset,
        path=(),
        cause=None,
        context=(),
        validator_value=_unset,
        instance=_unset,
        schema=_unset,
        schema_path=(),
        parent=None,
    ):
        self.message = message
        self.path = self.relative_path = deque(path)
        self.schema_path = self.relative_schema_path = deque(schema_path)
        self.context = list(context)
        self.cause = self.__cause__ = cause
        self.validator = validator
        self.validator_value = validator_value
        self.instance = instance
        self.schema = schema
        self.parent = parent

        for error in context:
            error.parent = self

    def __repr__(self):
        return "<%s: %r>" % (self.__class__.__name__, self.message)

    def __str__(self):
        return unicode(self).encode("utf-8")

    def __unicode__(self):
        essential_for_verbose = (
            self.validator, self.validator_value, self.instance, self.schema,
        )
        if any(m is _unset for m in essential_for_verbose):
            return self.message

        pschema = pprint.pformat(self.schema, width=72)
        pinstance = pprint.pformat(self.instance, width=72)
        return self.message + textwrap.dedent("""

            Failed validating %r in schema%s:
            %s

            On instance%s:
            %s
            """.rstrip()
        ) % (
            self.validator,
            _utils.format_as_index(list(self.relative_schema_path)[:-1]),
            _utils.indent(pschema),
            _utils.format_as_index(self.relative_path),
            _utils.indent(pinstance),
        )

    if PY3:
        __str__ = __unicode__

    @classmethod
    def create_from(cls, other):
        return cls(**other._contents())

    @property
    def absolute_path(self):
        parent = self.parent
        if parent is None:
            return self.relative_path

        path = deque(self.relative_path)
        path.extendleft(parent.absolute_path)
        return path

    @property
    def absolute_schema_path(self):
        parent = self.parent
        if parent is None:
            return self.relative_schema_path

        path = deque(self.relative_schema_path)
        path.extendleft(parent.absolute_schema_path)
        return path

    def _set(self, **kwargs):
        for k, v in iteritems(kwargs):
            if getattr(self, k) is _unset:
                setattr(self, k, v)

    def _contents(self):
        attrs = (
            "message", "cause", "context", "validator", "validator_value",
            "path", "schema_path", "instance", "schema", "parent",
        )
        return dict((attr, getattr(self, attr)) for attr in attrs)


class ValidationError(_Error):
    pass


class SchemaError(_Error):
    pass


class RefResolutionError(Exception):
    pass


class UnknownType(Exception):
    def __init__(self, type, instance, schema):
        self.type = type
        self.instance = instance
        self.schema = schema

    def __str__(self):
        return unicode(self).encode("utf-8")

    def __unicode__(self):
        pschema = pprint.pformat(self.schema, width=72)
        pinstance = pprint.pformat(self.instance, width=72)
        return textwrap.dedent("""
            Unknown type %r for validator with schema:
            %s

            While checking instance:
            %s
            """.rstrip()
        ) % (self.type, _utils.indent(pschema), _utils.indent(pinstance))

    if PY3:
        __str__ = __unicode__



class FormatError(Exception):
    def __init__(self, message, cause=None):
        super(FormatError, self).__init__(message, cause)
        self.message = message
        self.cause = self.__cause__ = cause

    def __str__(self):
        return self.message.encode("utf-8")

    def __unicode__(self):
        return self.message

    if PY3:
        __str__ = __unicode__


class ErrorTree(object):
    """
    ErrorTrees make it easier to check which validations failed.

    """

    _instance = _unset

    def __init__(self, errors=()):
        self.errors = {}
        self._contents = defaultdict(self.__class__)

        for error in errors:
            container = self
            for element in error.path:
                container = container[element]
            container.errors[error.validator] = error

            self._instance = error.instance

    def __contains__(self, index):
        """
        Check whether ``instance[index]`` has any errors.

        """

        return index in self._contents

    def __getitem__(self, index):
        """
        Retrieve the child tree one level down at the given ``index``.

        If the index is not in the instance that this tree corresponds to and
        is not known by this tree, whatever error would be raised by
        ``instance.__getitem__`` will be propagated (usually this is some
        subclass of :class:`LookupError`.

        """

        if self._instance is not _unset and index not in self:
            self._instance[index]
        return self._contents[index]

    def __setitem__(self, index, value):
        self._contents[index] = value

    def __iter__(self):
        """
        Iterate (non-recursively) over the indices in the instance with errors.

        """

        return iter(self._contents)

    def __len__(self):
        """
        Same as :attr:`total_errors`.

        """

        return self.total_errors

    def __repr__(self):
        return "<%s (%s total errors)>" % (self.__class__.__name__, len(self))

    @property
    def total_errors(self):
        """
        The total number of errors in the entire tree, including children.

        """

        child_errors = sum(len(tree) for _, tree in iteritems(self._contents))
        return len(self.errors) + child_errors


def by_relevance(weak=WEAK_MATCHES, strong=STRONG_MATCHES):
    def relevance(error):
        validator = error.validator
        return -len(error.path), validator not in weak, validator in strong
    return relevance


relevance = by_relevance()


def best_match(errors, key=relevance):
    errors = iter(errors)
    best = next(errors, None)
    if best is None:
        return
    best = max(itertools.chain([best], errors), key=key)

    while best.context:
        best = min(best.context, key=key)
    return best

########NEW FILE########
__FILENAME__ = compat
import sys


if sys.version_info[:2] < (2, 7):  # pragma: no cover
    import unittest2 as unittest
else:
    import unittest

try:
    from unittest import mock
except ImportError:
    import mock


# flake8: noqa

########NEW FILE########
__FILENAME__ = test_cli
from jsonschema import Draft4Validator, ValidationError, cli
from jsonschema.compat import StringIO
from jsonschema.tests.compat import mock, unittest


def fake_validator(*errors):
    errors = list(reversed(errors))

    class FakeValidator(object):
        def __init__(self, *args, **kwargs):
            pass

        def iter_errors(self, instance):
            if errors:
                return errors.pop()
            return []
    return FakeValidator


class TestParser(unittest.TestCase):

    FakeValidator = fake_validator()

    def setUp(self):
        self.open = mock.mock_open(read_data='{}')
        patch = mock.patch.object(cli, "open", self.open, create=True)
        patch.start()
        self.addCleanup(patch.stop)

    def test_find_validator_by_fully_qualified_object_name(self):
        arguments = cli.parse_args(
            [
                "--validator",
                "jsonschema.tests.test_cli.TestParser.FakeValidator",
                "--instance", "foo.json",
                "schema.json",
            ]
        )
        self.assertIs(arguments["validator"], self.FakeValidator)

    def test_find_validator_in_jsonschema(self):
        arguments = cli.parse_args(
            [
                "--validator", "Draft4Validator",
                "--instance", "foo.json",
                "schema.json",
            ]
        )
        self.assertIs(arguments["validator"], Draft4Validator)


class TestCLI(unittest.TestCase):
    def test_successful_validation(self):
        stdout, stderr = StringIO(), StringIO()
        exit_code = cli.run(
            {
                "validator" : fake_validator(),
                "schema" : {},
                "instances" : [1],
                "error_format" : "{error.message}",
            },
            stdout=stdout,
            stderr=stderr,
        )
        self.assertFalse(stdout.getvalue())
        self.assertFalse(stderr.getvalue())
        self.assertEqual(exit_code, 0)

    def test_unsuccessful_validation(self):
        error = ValidationError("I am an error!", instance=1)
        stdout, stderr = StringIO(), StringIO()
        exit_code = cli.run(
            {
                "validator" : fake_validator([error]),
                "schema" : {},
                "instances" : [1],
                "error_format" : "{error.instance} - {error.message}",
            },
            stdout=stdout,
            stderr=stderr,
        )
        self.assertFalse(stdout.getvalue())
        self.assertEqual(stderr.getvalue(), "1 - I am an error!")
        self.assertEqual(exit_code, 1)

    def test_unsuccessful_validation_multiple_instances(self):
        first_errors = [
            ValidationError("9", instance=1),
            ValidationError("8", instance=1),
        ]
        second_errors = [ValidationError("7", instance=2)]
        stdout, stderr = StringIO(), StringIO()
        exit_code = cli.run(
            {
                "validator" : fake_validator(first_errors, second_errors),
                "schema" : {},
                "instances" : [1, 2],
                "error_format" : "{error.instance} - {error.message}\t",
            },
            stdout=stdout,
            stderr=stderr,
        )
        self.assertFalse(stdout.getvalue())
        self.assertEqual(stderr.getvalue(), "1 - 9\t1 - 8\t2 - 7\t")
        self.assertEqual(exit_code, 1)

########NEW FILE########
__FILENAME__ = test_exceptions
import textwrap

from jsonschema import Draft4Validator, exceptions
from jsonschema.compat import PY3
from jsonschema.tests.compat import mock, unittest


class TestBestMatch(unittest.TestCase):
    def best_match(self, errors):
        errors = list(errors)
        best = exceptions.best_match(errors)
        reversed_best = exceptions.best_match(reversed(errors))
        self.assertEqual(
            best,
            reversed_best,
            msg="Didn't return a consistent best match!\n"
                "Got: {0}\n\nThen: {1}".format(best, reversed_best),
        )
        return best

    def test_shallower_errors_are_better_matches(self):
        validator = Draft4Validator(
            {
                "properties" : {
                    "foo" : {
                        "minProperties" : 2,
                        "properties" : {"bar" : {"type" : "object"}},
                    }
                }
            }
        )
        best = self.best_match(validator.iter_errors({"foo" : {"bar" : []}}))
        self.assertEqual(best.validator, "minProperties")

    def test_oneOf_and_anyOf_are_weak_matches(self):
        """
        A property you *must* match is probably better than one you have to
        match a part of.

        """

        validator = Draft4Validator(
            {
                "minProperties" : 2,
                "anyOf" : [{"type" : "string"}, {"type" : "number"}],
                "oneOf" : [{"type" : "string"}, {"type" : "number"}],
            }
        )
        best = self.best_match(validator.iter_errors({}))
        self.assertEqual(best.validator, "minProperties")

    def test_if_the_most_relevant_error_is_anyOf_it_is_traversed(self):
        """
        If the most relevant error is an anyOf, then we traverse its context
        and select the otherwise *least* relevant error, since in this case
        that means the most specific, deep, error inside the instance.

        I.e. since only one of the schemas must match, we look for the most
        relevant one.

        """

        validator = Draft4Validator(
            {
                "properties" : {
                    "foo" : {
                        "anyOf" : [
                            {"type" : "string"},
                            {"properties" : {"bar" : {"type" : "array"}}},
                        ],
                    },
                },
            },
        )
        best = self.best_match(validator.iter_errors({"foo" : {"bar" : 12}}))
        self.assertEqual(best.validator_value, "array")

    def test_if_the_most_relevant_error_is_oneOf_it_is_traversed(self):
        """
        If the most relevant error is an oneOf, then we traverse its context
        and select the otherwise *least* relevant error, since in this case
        that means the most specific, deep, error inside the instance.

        I.e. since only one of the schemas must match, we look for the most
        relevant one.

        """

        validator = Draft4Validator(
            {
                "properties" : {
                    "foo" : {
                        "oneOf" : [
                            {"type" : "string"},
                            {"properties" : {"bar" : {"type" : "array"}}},
                        ],
                    },
                },
            },
        )
        best = self.best_match(validator.iter_errors({"foo" : {"bar" : 12}}))
        self.assertEqual(best.validator_value, "array")

    def test_if_the_most_relevant_error_is_allOf_it_is_traversed(self):
        """
        Now, if the error is allOf, we traverse but select the *most* relevant
        error from the context, because all schemas here must match anyways.

        """

        validator = Draft4Validator(
            {
                "properties" : {
                    "foo" : {
                        "allOf" : [
                            {"type" : "string"},
                            {"properties" : {"bar" : {"type" : "array"}}},
                        ],
                    },
                },
            },
        )
        best = self.best_match(validator.iter_errors({"foo" : {"bar" : 12}}))
        self.assertEqual(best.validator_value, "string")

    def test_nested_context_for_oneOf(self):
        validator = Draft4Validator(
            {
                "properties" : {
                    "foo" : {
                        "oneOf" : [
                            {"type" : "string"},
                            {
                                "oneOf" : [
                                    {"type" : "string"},
                                    {
                                        "properties" : {
                                            "bar" : {"type" : "array"}
                                        },
                                    },
                                ],
                            },
                        ],
                    },
                },
            },
        )
        best = self.best_match(validator.iter_errors({"foo" : {"bar" : 12}}))
        self.assertEqual(best.validator_value, "array")

    def test_one_error(self):
        validator = Draft4Validator({"minProperties" : 2})
        error, = validator.iter_errors({})
        self.assertEqual(
            exceptions.best_match(validator.iter_errors({})).validator,
            "minProperties",
        )

    def test_no_errors(self):
        validator = Draft4Validator({})
        self.assertIsNone(exceptions.best_match(validator.iter_errors({})))


class TestByRelevance(unittest.TestCase):
    def test_short_paths_are_better_matches(self):
        shallow = exceptions.ValidationError("Oh no!", path=["baz"])
        deep = exceptions.ValidationError("Oh yes!", path=["foo", "bar"])
        match = max([shallow, deep], key=exceptions.relevance)
        self.assertIs(match, shallow)

        match = max([deep, shallow], key=exceptions.relevance)
        self.assertIs(match, shallow)

    def test_global_errors_are_even_better_matches(self):
        shallow = exceptions.ValidationError("Oh no!", path=[])
        deep = exceptions.ValidationError("Oh yes!", path=["foo"])

        errors = sorted([shallow, deep], key=exceptions.relevance)
        self.assertEqual(
            [list(error.path) for error in errors],
            [["foo"], []],
        )

        errors = sorted([deep, shallow], key=exceptions.relevance)
        self.assertEqual(
            [list(error.path) for error in errors],
            [["foo"], []],
        )

    def test_weak_validators_are_lower_priority(self):
        weak = exceptions.ValidationError("Oh no!", path=[], validator="a")
        normal = exceptions.ValidationError("Oh yes!", path=[], validator="b")

        best_match = exceptions.by_relevance(weak="a")

        match = max([weak, normal], key=best_match)
        self.assertIs(match, normal)

        match = max([normal, weak], key=best_match)
        self.assertIs(match, normal)

    def test_strong_validators_are_higher_priority(self):
        weak = exceptions.ValidationError("Oh no!", path=[], validator="a")
        normal = exceptions.ValidationError("Oh yes!", path=[], validator="b")
        strong = exceptions.ValidationError("Oh fine!", path=[], validator="c")

        best_match = exceptions.by_relevance(weak="a", strong="c")

        match = max([weak, normal, strong], key=best_match)
        self.assertIs(match, strong)

        match = max([strong, normal, weak], key=best_match)
        self.assertIs(match, strong)


class TestErrorTree(unittest.TestCase):
    def test_it_knows_how_many_total_errors_it_contains(self):
        errors = [mock.MagicMock() for _ in range(8)]
        tree = exceptions.ErrorTree(errors)
        self.assertEqual(tree.total_errors, 8)

    def test_it_contains_an_item_if_the_item_had_an_error(self):
        errors = [exceptions.ValidationError("a message", path=["bar"])]
        tree = exceptions.ErrorTree(errors)
        self.assertIn("bar", tree)

    def test_it_does_not_contain_an_item_if_the_item_had_no_error(self):
        errors = [exceptions.ValidationError("a message", path=["bar"])]
        tree = exceptions.ErrorTree(errors)
        self.assertNotIn("foo", tree)

    def test_validators_that_failed_appear_in_errors_dict(self):
        error = exceptions.ValidationError("a message", validator="foo")
        tree = exceptions.ErrorTree([error])
        self.assertEqual(tree.errors, {"foo" : error})

    def test_it_creates_a_child_tree_for_each_nested_path(self):
        errors = [
            exceptions.ValidationError("a bar message", path=["bar"]),
            exceptions.ValidationError("a bar -> 0 message", path=["bar", 0]),
        ]
        tree = exceptions.ErrorTree(errors)
        self.assertIn(0, tree["bar"])
        self.assertNotIn(1, tree["bar"])

    def test_children_have_their_errors_dicts_built(self):
        e1, e2 = (
            exceptions.ValidationError("1", validator="foo", path=["bar", 0]),
            exceptions.ValidationError("2", validator="quux", path=["bar", 0]),
        )
        tree = exceptions.ErrorTree([e1, e2])
        self.assertEqual(tree["bar"][0].errors, {"foo" : e1, "quux" : e2})

    def test_it_does_not_contain_subtrees_that_are_not_in_the_instance(self):
        error = exceptions.ValidationError("123", validator="foo", instance=[])
        tree = exceptions.ErrorTree([error])

        with self.assertRaises(IndexError):
            tree[0]

    def test_if_its_in_the_tree_anyhow_it_does_not_raise_an_error(self):
        """
        If a validator is dumb (like :validator:`required` in draft 3) and
        refers to a path that isn't in the instance, the tree still properly
        returns a subtree for that path.

        """

        error = exceptions.ValidationError(
            "a message", validator="foo", instance={}, path=["foo"],
        )
        tree = exceptions.ErrorTree([error])
        self.assertIsInstance(tree["foo"], exceptions.ErrorTree)


class TestErrorReprStr(unittest.TestCase):
    def make_error(self, **kwargs):
        defaults = dict(
            message=u"hello",
            validator=u"type",
            validator_value=u"string",
            instance=5,
            schema={u"type": u"string"},
        )
        defaults.update(kwargs)
        return exceptions.ValidationError(**defaults)

    def assertShows(self, expected, **kwargs):
        if PY3:
            expected = expected.replace("u'", "'")
        expected = textwrap.dedent(expected).rstrip("\n")

        error = self.make_error(**kwargs)
        message_line, _, rest = str(error).partition("\n")
        self.assertEqual(message_line, error.message)
        self.assertEqual(rest, expected)

    def test_repr(self):
        self.assertEqual(
            repr(exceptions.ValidationError(message="Hello!")),
            "<ValidationError: %r>" % "Hello!",
        )

    def test_unset_error(self):
        error = exceptions.ValidationError("message")
        self.assertEqual(str(error), "message")

        kwargs = {
            "validator": "type",
            "validator_value": "string",
            "instance": 5,
            "schema": {"type": "string"}
        }
        # Just the message should show if any of the attributes are unset
        for attr in kwargs:
            k = dict(kwargs)
            del k[attr]
            error = exceptions.ValidationError("message", **k)
            self.assertEqual(str(error), "message")

    def test_empty_paths(self):
        self.assertShows(
            """
            Failed validating u'type' in schema:
                {u'type': u'string'}

            On instance:
                5
            """,
            path=[],
            schema_path=[],
        )

    def test_one_item_paths(self):
        self.assertShows(
            """
            Failed validating u'type' in schema:
                {u'type': u'string'}

            On instance[0]:
                5
            """,
            path=[0],
            schema_path=["items"],
        )

    def test_multiple_item_paths(self):
        self.assertShows(
            """
            Failed validating u'type' in schema[u'items'][0]:
                {u'type': u'string'}

            On instance[0][u'a']:
                5
            """,
            path=[0, u"a"],
            schema_path=[u"items", 0, 1],
        )

    def test_uses_pprint(self):
        with mock.patch("pprint.pformat") as pformat:
            str(self.make_error())
            self.assertEqual(pformat.call_count, 2)  # schema + instance

    def test_str_works_with_instances_having_overriden_eq_operator(self):
        """
        Check for https://github.com/Julian/jsonschema/issues/164 which
        rendered exceptions unusable when a `ValidationError` involved
        instances with an `__eq__` method that returned truthy values.

        """

        instance = mock.MagicMock()
        error = exceptions.ValidationError(
            "a message",
            validator="foo",
            instance=instance,
            validator_value="some",
            schema="schema",
        )
        str(error)
        self.assertFalse(instance.__eq__.called)

########NEW FILE########
__FILENAME__ = test_format
"""
Tests for the parts of jsonschema related to the :validator:`format` property.

"""

from jsonschema.tests.compat import mock, unittest

from jsonschema import FormatError, ValidationError, FormatChecker
from jsonschema.validators import Draft4Validator


class TestFormatChecker(unittest.TestCase):
    def setUp(self):
        self.fn = mock.Mock()

    def test_it_can_validate_no_formats(self):
        checker = FormatChecker(formats=())
        self.assertFalse(checker.checkers)

    def test_it_raises_a_key_error_for_unknown_formats(self):
        with self.assertRaises(KeyError):
            FormatChecker(formats=["o noes"])

    def test_it_can_register_cls_checkers(self):
        with mock.patch.dict(FormatChecker.checkers, clear=True):
            FormatChecker.cls_checks("new")(self.fn)
            self.assertEqual(FormatChecker.checkers, {"new" : (self.fn, ())})

    def test_it_can_register_checkers(self):
        checker = FormatChecker()
        checker.checks("new")(self.fn)
        self.assertEqual(
            checker.checkers,
            dict(FormatChecker.checkers, new=(self.fn, ()))
        )

    def test_it_catches_registered_errors(self):
        checker = FormatChecker()
        cause = self.fn.side_effect = ValueError()

        checker.checks("foo", raises=ValueError)(self.fn)

        with self.assertRaises(FormatError) as cm:
            checker.check("bar", "foo")

        self.assertIs(cm.exception.cause, cause)
        self.assertIs(cm.exception.__cause__, cause)

        # Unregistered errors should not be caught
        self.fn.side_effect = AttributeError
        with self.assertRaises(AttributeError):
            checker.check("bar", "foo")

    def test_format_error_causes_become_validation_error_causes(self):
        checker = FormatChecker()
        checker.checks("foo", raises=ValueError)(self.fn)
        cause = self.fn.side_effect = ValueError()
        validator = Draft4Validator({"format" : "foo"}, format_checker=checker)

        with self.assertRaises(ValidationError) as cm:
            validator.validate("bar")

        self.assertIs(cm.exception.__cause__, cause)

########NEW FILE########
__FILENAME__ = test_jsonschema_test_suite
"""
Test runner for the JSON Schema official test suite

Tests comprehensive correctness of each draft's validator.

See https://github.com/json-schema/JSON-Schema-Test-Suite for details.

"""

from contextlib import closing
from decimal import Decimal
import glob
import json
import io
import itertools
import os
import re
import subprocess
import sys

try:
    from sys import pypy_version_info
except ImportError:
    pypy_version_info = None

from jsonschema import (
    FormatError, SchemaError, ValidationError, Draft3Validator,
    Draft4Validator, FormatChecker, draft3_format_checker,
    draft4_format_checker, validate,
)
from jsonschema.compat import PY3
from jsonschema.tests.compat import mock, unittest
import jsonschema


REPO_ROOT = os.path.join(os.path.dirname(jsonschema.__file__), os.path.pardir)
SUITE = os.getenv("JSON_SCHEMA_TEST_SUITE", os.path.join(REPO_ROOT, "json"))

if not os.path.isdir(SUITE):
    raise ValueError(
        "Can't find the JSON-Schema-Test-Suite directory. Set the "
        "'JSON_SCHEMA_TEST_SUITE' environment variable or run the tests from "
        "alongside a checkout of the suite."
    )

TESTS_DIR = os.path.join(SUITE, "tests")
JSONSCHEMA_SUITE = os.path.join(SUITE, "bin", "jsonschema_suite")

remotes_stdout = subprocess.Popen(
    ["python", JSONSCHEMA_SUITE, "remotes"], stdout=subprocess.PIPE,
).stdout

with closing(remotes_stdout):
    if PY3:
        remotes_stdout = io.TextIOWrapper(remotes_stdout)
    REMOTES = json.load(remotes_stdout)


def make_case(schema, data, valid, name):
    if valid:
        def test_case(self):
            kwargs = getattr(self, "validator_kwargs", {})
            validate(data, schema, cls=self.validator_class, **kwargs)
    else:
        def test_case(self):
            kwargs = getattr(self, "validator_kwargs", {})
            with self.assertRaises(ValidationError):
                validate(data, schema, cls=self.validator_class, **kwargs)

    if not PY3:
        name = name.encode("utf-8")
    test_case.__name__ = name

    return test_case


def maybe_skip(skip, test_case, case, test):
    if skip is not None:
        reason = skip(case, test)
        if reason is not None:
            test_case = unittest.skip(reason)(test_case)
    return test_case


def load_json_cases(tests_glob, ignore_glob="", basedir=TESTS_DIR, skip=None):
    if ignore_glob:
        ignore_glob = os.path.join(basedir, ignore_glob)

    def add_test_methods(test_class):
        ignored = set(glob.iglob(ignore_glob))

        for filename in glob.iglob(os.path.join(basedir, tests_glob)):
            if filename in ignored:
                continue

            validating, _ = os.path.splitext(os.path.basename(filename))
            id = itertools.count(1)

            with open(filename) as test_file:
                for case in json.load(test_file):
                    for test in case["tests"]:
                        name = "test_%s_%s_%s" % (
                            validating,
                            next(id),
                            re.sub(r"[\W ]+", "_", test["description"]),
                        )
                        assert not hasattr(test_class, name), name

                        test_case = make_case(
                            data=test["data"],
                            schema=case["schema"],
                            valid=test["valid"],
                            name=name,
                        )
                        test_case = maybe_skip(skip, test_case, case, test)
                        setattr(test_class, name, test_case)

        return test_class
    return add_test_methods


class TypesMixin(object):
    @unittest.skipIf(PY3, "In Python 3 json.load always produces unicode")
    def test_string_a_bytestring_is_a_string(self):
        self.validator_class({"type" : "string"}).validate(b"foo")


class DecimalMixin(object):
    def test_it_can_validate_with_decimals(self):
        schema = {"type" : "number"}
        validator = self.validator_class(
            schema, types={"number" : (int, float, Decimal)}
        )

        for valid in [1, 1.1, Decimal(1) / Decimal(8)]:
            validator.validate(valid)

        for invalid in ["foo", {}, [], True, None]:
            with self.assertRaises(ValidationError):
                validator.validate(invalid)


def missing_format(checker):
    def missing_format(case, test):
        format = case["schema"].get("format")
        if format not in checker.checkers:
            return "Format checker {0!r} not found.".format(format)
        elif (
            format == "date-time" and
            pypy_version_info is not None and
            pypy_version_info[:2] <= (1, 9)
        ):
            # datetime.datetime is overzealous about typechecking in <=1.9
            return "datetime.datetime is broken on this version of PyPy."
    return missing_format


class FormatMixin(object):
    def test_it_returns_true_for_formats_it_does_not_know_about(self):
        validator = self.validator_class(
            {"format" : "carrot"}, format_checker=FormatChecker(),
        )
        validator.validate("bugs")

    def test_it_does_not_validate_formats_by_default(self):
        validator = self.validator_class({})
        self.assertIsNone(validator.format_checker)

    def test_it_validates_formats_if_a_checker_is_provided(self):
        checker = mock.Mock(spec=FormatChecker)
        validator = self.validator_class(
            {"format" : "foo"}, format_checker=checker,
        )

        validator.validate("bar")

        checker.check.assert_called_once_with("bar", "foo")

        cause = ValueError()
        checker.check.side_effect = FormatError('aoeu', cause=cause)

        with self.assertRaises(ValidationError) as cm:
            validator.validate("bar")
        # Make sure original cause is attached
        self.assertIs(cm.exception.cause, cause)

    def test_it_validates_formats_of_any_type(self):
        checker = mock.Mock(spec=FormatChecker)
        validator = self.validator_class(
            {"format" : "foo"}, format_checker=checker,
        )

        validator.validate([1, 2, 3])

        checker.check.assert_called_once_with([1, 2, 3], "foo")

        cause = ValueError()
        checker.check.side_effect = FormatError('aoeu', cause=cause)

        with self.assertRaises(ValidationError) as cm:
            validator.validate([1, 2, 3])
        # Make sure original cause is attached
        self.assertIs(cm.exception.cause, cause)


if sys.maxunicode == 2 ** 16 - 1:          # This is a narrow build.
    def narrow_unicode_build(case, test):
        if "supplementary Unicode" in test["description"]:
            return "Not running surrogate Unicode case, this Python is narrow."
else:
    def narrow_unicode_build(case, test):  # This isn't, skip nothing.
        return


@load_json_cases(
    "draft3/*.json",
    skip=narrow_unicode_build,
    ignore_glob="draft3/refRemote.json",
)
@load_json_cases(
    "draft3/optional/format.json", skip=missing_format(draft3_format_checker)
)
@load_json_cases("draft3/optional/bignum.json")
@load_json_cases("draft3/optional/zeroTerminatedFloats.json")
class TestDraft3(unittest.TestCase, TypesMixin, DecimalMixin, FormatMixin):
    validator_class = Draft3Validator
    validator_kwargs = {"format_checker" : draft3_format_checker}

    def test_any_type_is_valid_for_type_any(self):
        validator = self.validator_class({"type" : "any"})
        validator.validate(mock.Mock())

    # TODO: we're in need of more meta schema tests
    def test_invalid_properties(self):
        with self.assertRaises(SchemaError):
            validate({}, {"properties": {"test": True}},
                     cls=self.validator_class)

    def test_minItems_invalid_string(self):
        with self.assertRaises(SchemaError):
            # needs to be an integer
            validate([1], {"minItems" : "1"}, cls=self.validator_class)


@load_json_cases(
    "draft4/*.json",
    skip=narrow_unicode_build,
    ignore_glob="draft4/refRemote.json",
)
@load_json_cases(
    "draft4/optional/format.json", skip=missing_format(draft4_format_checker)
)
@load_json_cases("draft4/optional/bignum.json")
@load_json_cases("draft4/optional/zeroTerminatedFloats.json")
class TestDraft4(unittest.TestCase, TypesMixin, DecimalMixin, FormatMixin):
    validator_class = Draft4Validator
    validator_kwargs = {"format_checker" : draft4_format_checker}

    # TODO: we're in need of more meta schema tests
    def test_invalid_properties(self):
        with self.assertRaises(SchemaError):
            validate({}, {"properties": {"test": True}},
                     cls=self.validator_class)

    def test_minItems_invalid_string(self):
        with self.assertRaises(SchemaError):
            # needs to be an integer
            validate([1], {"minItems" : "1"}, cls=self.validator_class)


class RemoteRefResolutionMixin(object):
    def setUp(self):
        patch = mock.patch("jsonschema.validators.requests")
        requests = patch.start()
        requests.get.side_effect = self.resolve
        self.addCleanup(patch.stop)

    def resolve(self, reference):
        _, _, reference = reference.partition("http://localhost:1234/")
        return mock.Mock(**{"json.return_value" : REMOTES.get(reference)})


@load_json_cases("draft3/refRemote.json")
class Draft3RemoteResolution(RemoteRefResolutionMixin, unittest.TestCase):
    validator_class = Draft3Validator


@load_json_cases("draft4/refRemote.json")
class Draft4RemoteResolution(RemoteRefResolutionMixin, unittest.TestCase):
    validator_class = Draft4Validator

########NEW FILE########
__FILENAME__ = test_validators
from collections import deque
from contextlib import contextmanager
import json

from jsonschema import FormatChecker, ValidationError
from jsonschema.tests.compat import mock, unittest
from jsonschema.validators import (
    RefResolutionError, UnknownType, Draft3Validator,
    Draft4Validator, RefResolver, create, extend, validator_for, validate,
)


class TestCreateAndExtend(unittest.TestCase):
    def setUp(self):
        self.meta_schema = {u"properties" : {u"smelly" : {}}}
        self.smelly = mock.MagicMock()
        self.validators = {u"smelly" : self.smelly}
        self.types = {u"dict" : dict}
        self.Validator = create(
            meta_schema=self.meta_schema,
            validators=self.validators,
            default_types=self.types,
        )

        self.validator_value = 12
        self.schema = {u"smelly" : self.validator_value}
        self.validator = self.Validator(self.schema)

    def test_attrs(self):
        self.assertEqual(self.Validator.VALIDATORS, self.validators)
        self.assertEqual(self.Validator.META_SCHEMA, self.meta_schema)
        self.assertEqual(self.Validator.DEFAULT_TYPES, self.types)

    def test_init(self):
        self.assertEqual(self.validator.schema, self.schema)

    def test_iter_errors(self):
        instance = "hello"

        self.smelly.return_value = []
        self.assertEqual(list(self.validator.iter_errors(instance)), [])

        error = mock.Mock()
        self.smelly.return_value = [error]
        self.assertEqual(list(self.validator.iter_errors(instance)), [error])

        self.smelly.assert_called_with(
            self.validator, self.validator_value, instance, self.schema,
        )

    def test_if_a_version_is_provided_it_is_registered(self):
        with mock.patch("jsonschema.validators.validates") as validates:
            validates.side_effect = lambda version : lambda cls : cls
            Validator = create(meta_schema={u"id" : ""}, version="my version")
        validates.assert_called_once_with("my version")
        self.assertEqual(Validator.__name__, "MyVersionValidator")

    def test_if_a_version_is_not_provided_it_is_not_registered(self):
        with mock.patch("jsonschema.validators.validates") as validates:
            create(meta_schema={u"id" : "id"})
        self.assertFalse(validates.called)

    def test_extend(self):
        validators = dict(self.Validator.VALIDATORS)
        new = mock.Mock()

        Extended = extend(self.Validator, validators={u"a new one" : new})

        validators.update([(u"a new one", new)])
        self.assertEqual(Extended.VALIDATORS, validators)
        self.assertNotIn(u"a new one", self.Validator.VALIDATORS)

        self.assertEqual(Extended.META_SCHEMA, self.Validator.META_SCHEMA)
        self.assertEqual(Extended.DEFAULT_TYPES, self.Validator.DEFAULT_TYPES)


class TestIterErrors(unittest.TestCase):
    def setUp(self):
        self.validator = Draft3Validator({})

    def test_iter_errors(self):
        instance = [1, 2]
        schema = {
            u"disallow" : u"array",
            u"enum" : [["a", "b", "c"], ["d", "e", "f"]],
            u"minItems" : 3
        }

        got = (e.message for e in self.validator.iter_errors(instance, schema))
        expected = [
            "%r is disallowed for [1, 2]" % (schema["disallow"],),
            "[1, 2] is too short",
            "[1, 2] is not one of %r" % (schema["enum"],),
        ]
        self.assertEqual(sorted(got), sorted(expected))

    def test_iter_errors_multiple_failures_one_validator(self):
        instance = {"foo" : 2, "bar" : [1], "baz" : 15, "quux" : "spam"}
        schema = {
            u"properties" : {
                "foo" : {u"type" : "string"},
                "bar" : {u"minItems" : 2},
                "baz" : {u"maximum" : 10, u"enum" : [2, 4, 6, 8]},
            }
        }

        errors = list(self.validator.iter_errors(instance, schema))
        self.assertEqual(len(errors), 4)


class TestValidationErrorMessages(unittest.TestCase):
    def message_for(self, instance, schema, *args, **kwargs):
        kwargs.setdefault("cls", Draft3Validator)
        with self.assertRaises(ValidationError) as e:
            validate(instance, schema, *args, **kwargs)
        return e.exception.message

    def test_single_type_failure(self):
        message = self.message_for(instance=1, schema={u"type" : u"string"})
        self.assertEqual(message, "1 is not of type %r" % u"string")

    def test_single_type_list_failure(self):
        message = self.message_for(instance=1, schema={u"type" : [u"string"]})
        self.assertEqual(message, "1 is not of type %r" % u"string")

    def test_multiple_type_failure(self):
        types = u"string", u"object"
        message = self.message_for(instance=1, schema={u"type" : list(types)})
        self.assertEqual(message, "1 is not of type %r, %r" % types)

    def test_object_without_title_type_failure(self):
        type = {u"type" : [{u"minimum" : 3}]}
        message = self.message_for(instance=1, schema={u"type" : [type]})
        self.assertEqual(message, "1 is not of type %r" % (type,))

    def test_object_with_name_type_failure(self):
        name = "Foo"
        schema = {u"type" : [{u"name" : name, u"minimum" : 3}]}
        message = self.message_for(instance=1, schema=schema)
        self.assertEqual(message, "1 is not of type %r" % (name,))

    def test_minimum(self):
        message = self.message_for(instance=1, schema={"minimum" : 2})
        self.assertEqual(message, "1 is less than the minimum of 2")

    def test_maximum(self):
        message = self.message_for(instance=1, schema={"maximum" : 0})
        self.assertEqual(message, "1 is greater than the maximum of 0")

    def test_dependencies_failure_has_single_element_not_list(self):
        depend, on = "bar", "foo"
        schema = {u"dependencies" : {depend : on}}
        message = self.message_for({"bar" : 2}, schema)
        self.assertEqual(message, "%r is a dependency of %r" % (on, depend))

    def test_additionalItems_single_failure(self):
        message = self.message_for(
            [2], {u"items" : [], u"additionalItems" : False},
        )
        self.assertIn("(2 was unexpected)", message)

    def test_additionalItems_multiple_failures(self):
        message = self.message_for(
            [1, 2, 3], {u"items" : [], u"additionalItems" : False}
        )
        self.assertIn("(1, 2, 3 were unexpected)", message)

    def test_additionalProperties_single_failure(self):
        additional = "foo"
        schema = {u"additionalProperties" : False}
        message = self.message_for({additional : 2}, schema)
        self.assertIn("(%r was unexpected)" % (additional,), message)

    def test_additionalProperties_multiple_failures(self):
        schema = {u"additionalProperties" : False}
        message = self.message_for(dict.fromkeys(["foo", "bar"]), schema)

        self.assertIn(repr("foo"), message)
        self.assertIn(repr("bar"), message)
        self.assertIn("were unexpected)", message)

    def test_invalid_format_default_message(self):
        checker = FormatChecker(formats=())
        check_fn = mock.Mock(return_value=False)
        checker.checks(u"thing")(check_fn)

        schema = {u"format" : u"thing"}
        message = self.message_for("bla", schema, format_checker=checker)

        self.assertIn(repr("bla"), message)
        self.assertIn(repr("thing"), message)
        self.assertIn("is not a", message)


class TestValidationErrorDetails(unittest.TestCase):
    # TODO: These really need unit tests for each individual validator, rather
    #       than just these higher level tests.
    def test_anyOf(self):
        instance = 5
        schema = {
            "anyOf": [
                {"minimum": 20},
                {"type": "string"}
            ]
        }

        validator = Draft4Validator(schema)
        errors = list(validator.iter_errors(instance))
        self.assertEqual(len(errors), 1)
        e = errors[0]

        self.assertEqual(e.validator, "anyOf")
        self.assertEqual(e.validator_value, schema["anyOf"])
        self.assertEqual(e.instance, instance)
        self.assertEqual(e.schema, schema)
        self.assertIsNone(e.parent)

        self.assertEqual(e.path, deque([]))
        self.assertEqual(e.relative_path, deque([]))
        self.assertEqual(e.absolute_path, deque([]))

        self.assertEqual(e.schema_path, deque(["anyOf"]))
        self.assertEqual(e.relative_schema_path, deque(["anyOf"]))
        self.assertEqual(e.absolute_schema_path, deque(["anyOf"]))

        self.assertEqual(len(e.context), 2)

        e1, e2 = sorted_errors(e.context)

        self.assertEqual(e1.validator, "minimum")
        self.assertEqual(e1.validator_value, schema["anyOf"][0]["minimum"])
        self.assertEqual(e1.instance, instance)
        self.assertEqual(e1.schema, schema["anyOf"][0])
        self.assertIs(e1.parent, e)

        self.assertEqual(e1.path, deque([]))
        self.assertEqual(e1.absolute_path, deque([]))
        self.assertEqual(e1.relative_path, deque([]))

        self.assertEqual(e1.schema_path, deque([0, "minimum"]))
        self.assertEqual(e1.relative_schema_path, deque([0, "minimum"]))
        self.assertEqual(
            e1.absolute_schema_path, deque(["anyOf", 0, "minimum"]),
        )

        self.assertFalse(e1.context)

        self.assertEqual(e2.validator, "type")
        self.assertEqual(e2.validator_value, schema["anyOf"][1]["type"])
        self.assertEqual(e2.instance, instance)
        self.assertEqual(e2.schema, schema["anyOf"][1])
        self.assertIs(e2.parent, e)

        self.assertEqual(e2.path, deque([]))
        self.assertEqual(e2.relative_path, deque([]))
        self.assertEqual(e2.absolute_path, deque([]))

        self.assertEqual(e2.schema_path, deque([1, "type"]))
        self.assertEqual(e2.relative_schema_path, deque([1, "type"]))
        self.assertEqual(e2.absolute_schema_path, deque(["anyOf", 1, "type"]))

        self.assertEqual(len(e2.context), 0)

    def test_type(self):
        instance = {"foo": 1}
        schema = {
            "type": [
                {"type": "integer"},
                {
                    "type": "object",
                    "properties": {
                        "foo": {"enum": [2]}
                    }
                }
            ]
        }

        validator = Draft3Validator(schema)
        errors = list(validator.iter_errors(instance))
        self.assertEqual(len(errors), 1)
        e = errors[0]

        self.assertEqual(e.validator, "type")
        self.assertEqual(e.validator_value, schema["type"])
        self.assertEqual(e.instance, instance)
        self.assertEqual(e.schema, schema)
        self.assertIsNone(e.parent)

        self.assertEqual(e.path, deque([]))
        self.assertEqual(e.relative_path, deque([]))
        self.assertEqual(e.absolute_path, deque([]))

        self.assertEqual(e.schema_path, deque(["type"]))
        self.assertEqual(e.relative_schema_path, deque(["type"]))
        self.assertEqual(e.absolute_schema_path, deque(["type"]))

        self.assertEqual(len(e.context), 2)

        e1, e2 = sorted_errors(e.context)

        self.assertEqual(e1.validator, "type")
        self.assertEqual(e1.validator_value, schema["type"][0]["type"])
        self.assertEqual(e1.instance, instance)
        self.assertEqual(e1.schema, schema["type"][0])
        self.assertIs(e1.parent, e)

        self.assertEqual(e1.path, deque([]))
        self.assertEqual(e1.relative_path, deque([]))
        self.assertEqual(e1.absolute_path, deque([]))

        self.assertEqual(e1.schema_path, deque([0, "type"]))
        self.assertEqual(e1.relative_schema_path, deque([0, "type"]))
        self.assertEqual(e1.absolute_schema_path, deque(["type", 0, "type"]))

        self.assertFalse(e1.context)

        self.assertEqual(e2.validator, "enum")
        self.assertEqual(e2.validator_value, [2])
        self.assertEqual(e2.instance, 1)
        self.assertEqual(e2.schema, {u"enum" : [2]})
        self.assertIs(e2.parent, e)

        self.assertEqual(e2.path, deque(["foo"]))
        self.assertEqual(e2.relative_path, deque(["foo"]))
        self.assertEqual(e2.absolute_path, deque(["foo"]))

        self.assertEqual(
            e2.schema_path, deque([1, "properties", "foo", "enum"]),
        )
        self.assertEqual(
            e2.relative_schema_path, deque([1, "properties", "foo", "enum"]),
        )
        self.assertEqual(
            e2.absolute_schema_path,
            deque(["type", 1, "properties", "foo", "enum"]),
        )

        self.assertFalse(e2.context)

    def test_single_nesting(self):
        instance = {"foo" : 2, "bar" : [1], "baz" : 15, "quux" : "spam"}
        schema = {
            "properties" : {
                "foo" : {"type" : "string"},
                "bar" : {"minItems" : 2},
                "baz" : {"maximum" : 10, "enum" : [2, 4, 6, 8]},
            }
        }

        validator = Draft3Validator(schema)
        errors = validator.iter_errors(instance)
        e1, e2, e3, e4 = sorted_errors(errors)

        self.assertEqual(e1.path, deque(["bar"]))
        self.assertEqual(e2.path, deque(["baz"]))
        self.assertEqual(e3.path, deque(["baz"]))
        self.assertEqual(e4.path, deque(["foo"]))

        self.assertEqual(e1.relative_path, deque(["bar"]))
        self.assertEqual(e2.relative_path, deque(["baz"]))
        self.assertEqual(e3.relative_path, deque(["baz"]))
        self.assertEqual(e4.relative_path, deque(["foo"]))

        self.assertEqual(e1.absolute_path, deque(["bar"]))
        self.assertEqual(e2.absolute_path, deque(["baz"]))
        self.assertEqual(e3.absolute_path, deque(["baz"]))
        self.assertEqual(e4.absolute_path, deque(["foo"]))

        self.assertEqual(e1.validator, "minItems")
        self.assertEqual(e2.validator, "enum")
        self.assertEqual(e3.validator, "maximum")
        self.assertEqual(e4.validator, "type")

    def test_multiple_nesting(self):
        instance = [1, {"foo" : 2, "bar" : {"baz" : [1]}}, "quux"]
        schema = {
            "type" : "string",
            "items" : {
                "type" : ["string", "object"],
                "properties" : {
                    "foo" : {"enum" : [1, 3]},
                    "bar" : {
                        "type" : "array",
                        "properties" : {
                            "bar" : {"required" : True},
                            "baz" : {"minItems" : 2},
                        }
                    }
                }
            }
        }

        validator = Draft3Validator(schema)
        errors = validator.iter_errors(instance)
        e1, e2, e3, e4, e5, e6 = sorted_errors(errors)

        self.assertEqual(e1.path, deque([]))
        self.assertEqual(e2.path, deque([0]))
        self.assertEqual(e3.path, deque([1, "bar"]))
        self.assertEqual(e4.path, deque([1, "bar", "bar"]))
        self.assertEqual(e5.path, deque([1, "bar", "baz"]))
        self.assertEqual(e6.path, deque([1, "foo"]))

        self.assertEqual(e1.schema_path, deque(["type"]))
        self.assertEqual(e2.schema_path, deque(["items", "type"]))
        self.assertEqual(
            list(e3.schema_path), ["items", "properties", "bar", "type"],
        )
        self.assertEqual(
            list(e4.schema_path),
            ["items", "properties", "bar", "properties", "bar", "required"],
        )
        self.assertEqual(
            list(e5.schema_path),
            ["items", "properties", "bar", "properties", "baz", "minItems"]
        )
        self.assertEqual(
            list(e6.schema_path), ["items", "properties", "foo", "enum"],
        )

        self.assertEqual(e1.validator, "type")
        self.assertEqual(e2.validator, "type")
        self.assertEqual(e3.validator, "type")
        self.assertEqual(e4.validator, "required")
        self.assertEqual(e5.validator, "minItems")
        self.assertEqual(e6.validator, "enum")

    def test_additionalProperties(self):
        instance = {"bar": "bar", "foo": 2}
        schema = {
            "additionalProperties" : {"type": "integer", "minimum": 5}
        }

        validator = Draft3Validator(schema)
        errors = validator.iter_errors(instance)
        e1, e2 = sorted_errors(errors)

        self.assertEqual(e1.path, deque(["bar"]))
        self.assertEqual(e2.path, deque(["foo"]))

        self.assertEqual(e1.validator, "type")
        self.assertEqual(e2.validator, "minimum")

    def test_patternProperties(self):
        instance = {"bar": 1, "foo": 2}
        schema = {
            "patternProperties" : {
                "bar": {"type": "string"},
                "foo": {"minimum": 5}
            }
        }

        validator = Draft3Validator(schema)
        errors = validator.iter_errors(instance)
        e1, e2 = sorted_errors(errors)

        self.assertEqual(e1.path, deque(["bar"]))
        self.assertEqual(e2.path, deque(["foo"]))

        self.assertEqual(e1.validator, "type")
        self.assertEqual(e2.validator, "minimum")

    def test_additionalItems(self):
        instance = ["foo", 1]
        schema = {
            "items": [],
            "additionalItems" : {"type": "integer", "minimum": 5}
        }

        validator = Draft3Validator(schema)
        errors = validator.iter_errors(instance)
        e1, e2 = sorted_errors(errors)

        self.assertEqual(e1.path, deque([0]))
        self.assertEqual(e2.path, deque([1]))

        self.assertEqual(e1.validator, "type")
        self.assertEqual(e2.validator, "minimum")

    def test_additionalItems_with_items(self):
        instance = ["foo", "bar", 1]
        schema = {
            "items": [{}],
            "additionalItems" : {"type": "integer", "minimum": 5}
        }

        validator = Draft3Validator(schema)
        errors = validator.iter_errors(instance)
        e1, e2 = sorted_errors(errors)

        self.assertEqual(e1.path, deque([1]))
        self.assertEqual(e2.path, deque([2]))

        self.assertEqual(e1.validator, "type")
        self.assertEqual(e2.validator, "minimum")


class ValidatorTestMixin(object):
    def setUp(self):
        self.instance = mock.Mock()
        self.schema = {}
        self.resolver = mock.Mock()
        self.validator = self.validator_class(self.schema)

    def test_valid_instances_are_valid(self):
        errors = iter([])

        with mock.patch.object(
            self.validator, "iter_errors", return_value=errors,
        ):
            self.assertTrue(
                self.validator.is_valid(self.instance, self.schema)
            )

    def test_invalid_instances_are_not_valid(self):
        errors = iter([mock.Mock()])

        with mock.patch.object(
            self.validator, "iter_errors", return_value=errors,
        ):
            self.assertFalse(
                self.validator.is_valid(self.instance, self.schema)
            )

    def test_non_existent_properties_are_ignored(self):
        instance, my_property, my_value = mock.Mock(), mock.Mock(), mock.Mock()
        validate(instance=instance, schema={my_property : my_value})

    def test_it_creates_a_ref_resolver_if_not_provided(self):
        self.assertIsInstance(self.validator.resolver, RefResolver)

    def test_it_delegates_to_a_ref_resolver(self):
        resolver = RefResolver("", {})
        schema = {"$ref" : mock.Mock()}

        @contextmanager
        def resolving():
            yield {"type": "integer"}

        with mock.patch.object(resolver, "resolving") as resolve:
            resolve.return_value = resolving()
            with self.assertRaises(ValidationError):
                self.validator_class(schema, resolver=resolver).validate(None)

        resolve.assert_called_once_with(schema["$ref"])

    def test_is_type_is_true_for_valid_type(self):
        self.assertTrue(self.validator.is_type("foo", "string"))

    def test_is_type_is_false_for_invalid_type(self):
        self.assertFalse(self.validator.is_type("foo", "array"))

    def test_is_type_evades_bool_inheriting_from_int(self):
        self.assertFalse(self.validator.is_type(True, "integer"))
        self.assertFalse(self.validator.is_type(True, "number"))

    def test_is_type_raises_exception_for_unknown_type(self):
        with self.assertRaises(UnknownType):
            self.validator.is_type("foo", object())


class TestDraft3Validator(ValidatorTestMixin, unittest.TestCase):
    validator_class = Draft3Validator

    def test_is_type_is_true_for_any_type(self):
        self.assertTrue(self.validator.is_valid(mock.Mock(), {"type": "any"}))

    def test_is_type_does_not_evade_bool_if_it_is_being_tested(self):
        self.assertTrue(self.validator.is_type(True, "boolean"))
        self.assertTrue(self.validator.is_valid(True, {"type": "any"}))

    def test_non_string_custom_types(self):
        schema = {'type': [None]}
        cls = self.validator_class(schema, types={None: type(None)})
        cls.validate(None, schema)


class TestDraft4Validator(ValidatorTestMixin, unittest.TestCase):
    validator_class = Draft4Validator


class TestBuiltinFormats(unittest.TestCase):
    """
    The built-in (specification-defined) formats do not raise type errors.

    If an instance or value is not a string, it should be ignored.

    """


for format in FormatChecker.checkers:
    def test(self, format=format):
        v = Draft4Validator({"format": format}, format_checker=FormatChecker())
        v.validate(123)

    name = "test_{0}_ignores_non_strings".format(format)
    test.__name__ = name
    setattr(TestBuiltinFormats, name, test)
    del test  # Ugh py.test. Stop discovering top level tests.


class TestValidatorFor(unittest.TestCase):
    def test_draft_3(self):
        schema = {"$schema" : "http://json-schema.org/draft-03/schema"}
        self.assertIs(validator_for(schema), Draft3Validator)

        schema = {"$schema" : "http://json-schema.org/draft-03/schema#"}
        self.assertIs(validator_for(schema), Draft3Validator)

    def test_draft_4(self):
        schema = {"$schema" : "http://json-schema.org/draft-04/schema"}
        self.assertIs(validator_for(schema), Draft4Validator)

        schema = {"$schema" : "http://json-schema.org/draft-04/schema#"}
        self.assertIs(validator_for(schema), Draft4Validator)

    def test_custom_validator(self):
        Validator = create(meta_schema={"id" : "meta schema id"}, version="12")
        schema = {"$schema" : "meta schema id"}
        self.assertIs(validator_for(schema), Validator)

    def test_validator_for_jsonschema_default(self):
        self.assertIs(validator_for({}), Draft4Validator)

    def test_validator_for_custom_default(self):
        self.assertIs(validator_for({}, default=None), None)


class TestValidate(unittest.TestCase):
    def test_draft3_validator_is_chosen(self):
        schema = {"$schema" : "http://json-schema.org/draft-03/schema#"}
        with mock.patch.object(Draft3Validator, "check_schema") as chk_schema:
            validate({}, schema)
            chk_schema.assert_called_once_with(schema)
        # Make sure it works without the empty fragment
        schema = {"$schema" : "http://json-schema.org/draft-03/schema"}
        with mock.patch.object(Draft3Validator, "check_schema") as chk_schema:
            validate({}, schema)
            chk_schema.assert_called_once_with(schema)

    def test_draft4_validator_is_chosen(self):
        schema = {"$schema" : "http://json-schema.org/draft-04/schema#"}
        with mock.patch.object(Draft4Validator, "check_schema") as chk_schema:
            validate({}, schema)
            chk_schema.assert_called_once_with(schema)

    def test_draft4_validator_is_the_default(self):
        with mock.patch.object(Draft4Validator, "check_schema") as chk_schema:
            validate({}, {})
            chk_schema.assert_called_once_with({})


class TestRefResolver(unittest.TestCase):

    base_uri = ""
    stored_uri = "foo://stored"
    stored_schema = {"stored" : "schema"}

    def setUp(self):
        self.referrer = {}
        self.store = {self.stored_uri : self.stored_schema}
        self.resolver = RefResolver(self.base_uri, self.referrer, self.store)

    def test_it_does_not_retrieve_schema_urls_from_the_network(self):
        ref = Draft3Validator.META_SCHEMA["id"]
        with mock.patch.object(self.resolver, "resolve_remote") as remote:
            with self.resolver.resolving(ref) as resolved:
                self.assertEqual(resolved, Draft3Validator.META_SCHEMA)
        self.assertFalse(remote.called)

    def test_it_resolves_local_refs(self):
        ref = "#/properties/foo"
        self.referrer["properties"] = {"foo" : object()}
        with self.resolver.resolving(ref) as resolved:
            self.assertEqual(resolved, self.referrer["properties"]["foo"])

    def test_it_resolves_local_refs_with_id(self):
        schema = {"id": "foo://bar/schema#", "a": {"foo": "bar"}}
        resolver = RefResolver.from_schema(schema)
        with resolver.resolving("#/a") as resolved:
            self.assertEqual(resolved, schema["a"])
        with resolver.resolving("foo://bar/schema#/a") as resolved:
            self.assertEqual(resolved, schema["a"])

    def test_it_retrieves_stored_refs(self):
        with self.resolver.resolving(self.stored_uri) as resolved:
            self.assertIs(resolved, self.stored_schema)

        self.resolver.store["cached_ref"] = {"foo" : 12}
        with self.resolver.resolving("cached_ref#/foo") as resolved:
            self.assertEqual(resolved, 12)

    def test_it_retrieves_unstored_refs_via_requests(self):
        ref = "http://bar#baz"
        schema = {"baz" : 12}

        with mock.patch("jsonschema.validators.requests") as requests:
            requests.get.return_value.json.return_value = schema
            with self.resolver.resolving(ref) as resolved:
                self.assertEqual(resolved, 12)
        requests.get.assert_called_once_with("http://bar")

    def test_it_retrieves_unstored_refs_via_urlopen(self):
        ref = "http://bar#baz"
        schema = {"baz" : 12}

        with mock.patch("jsonschema.validators.requests", None):
            with mock.patch("jsonschema.validators.urlopen") as urlopen:
                urlopen.return_value.read.return_value = (
                    json.dumps(schema).encode("utf8"))
                with self.resolver.resolving(ref) as resolved:
                    self.assertEqual(resolved, 12)
        urlopen.assert_called_once_with("http://bar")

    def test_it_can_construct_a_base_uri_from_a_schema(self):
        schema = {"id" : "foo"}
        resolver = RefResolver.from_schema(schema)
        self.assertEqual(resolver.base_uri, "foo")
        with resolver.resolving("") as resolved:
            self.assertEqual(resolved, schema)
        with resolver.resolving("#") as resolved:
            self.assertEqual(resolved, schema)
        with resolver.resolving("foo") as resolved:
            self.assertEqual(resolved, schema)
        with resolver.resolving("foo#") as resolved:
            self.assertEqual(resolved, schema)

    def test_it_can_construct_a_base_uri_from_a_schema_without_id(self):
        schema = {}
        resolver = RefResolver.from_schema(schema)
        self.assertEqual(resolver.base_uri, "")
        with resolver.resolving("") as resolved:
            self.assertEqual(resolved, schema)
        with resolver.resolving("#") as resolved:
            self.assertEqual(resolved, schema)

    def test_custom_uri_scheme_handlers(self):
        schema = {"foo": "bar"}
        ref = "foo://bar"
        foo_handler = mock.Mock(return_value=schema)
        resolver = RefResolver("", {}, handlers={"foo": foo_handler})
        with resolver.resolving(ref) as resolved:
            self.assertEqual(resolved, schema)
        foo_handler.assert_called_once_with(ref)

    def test_cache_remote_on(self):
        ref = "foo://bar"
        foo_handler = mock.Mock()
        resolver = RefResolver(
            "", {}, cache_remote=True, handlers={"foo" : foo_handler},
        )
        with resolver.resolving(ref):
            pass
        with resolver.resolving(ref):
            pass
        foo_handler.assert_called_once_with(ref)

    def test_cache_remote_off(self):
        ref = "foo://bar"
        foo_handler = mock.Mock()
        resolver = RefResolver(
            "", {}, cache_remote=False, handlers={"foo" : foo_handler},
        )
        with resolver.resolving(ref):
            pass
        with resolver.resolving(ref):
            pass
        self.assertEqual(foo_handler.call_count, 2)

    def test_if_you_give_it_junk_you_get_a_resolution_error(self):
        ref = "foo://bar"
        foo_handler = mock.Mock(side_effect=ValueError("Oh no! What's this?"))
        resolver = RefResolver("", {}, handlers={"foo" : foo_handler})
        with self.assertRaises(RefResolutionError) as err:
            with resolver.resolving(ref):
                pass
        self.assertEqual(str(err.exception), "Oh no! What's this?")


def sorted_errors(errors):
    def key(error):
        return (
            [str(e) for e in error.path],
            [str(e) for e in error.schema_path]
        )
    return sorted(errors, key=key)

########NEW FILE########
__FILENAME__ = validators
from __future__ import division

import contextlib
import json
import numbers

try:
    import requests
except ImportError:
    requests = None

from jsonschema import _utils, _validators
from jsonschema.compat import (
    Sequence, urljoin, urlsplit, urldefrag, unquote, urlopen,
    str_types, int_types, iteritems,
)
from jsonschema.exceptions import ErrorTree  # Backwards compatibility  # noqa
from jsonschema.exceptions import RefResolutionError, SchemaError, UnknownType


_unset = _utils.Unset()

validators = {}
meta_schemas = _utils.URIDict()


def validates(version):
    """
    Register the decorated validator for a ``version`` of the specification.

    Registered validators and their meta schemas will be considered when
    parsing ``$schema`` properties' URIs.

    :argument str version: an identifier to use as the version's name
    :returns: a class decorator to decorate the validator with the version

    """

    def _validates(cls):
        validators[version] = cls
        if u"id" in cls.META_SCHEMA:
            meta_schemas[cls.META_SCHEMA[u"id"]] = cls
        return cls
    return _validates


def create(meta_schema, validators=(), version=None, default_types=None):  # noqa
    if default_types is None:
        default_types = {
            u"array" : list, u"boolean" : bool, u"integer" : int_types,
            u"null" : type(None), u"number" : numbers.Number, u"object" : dict,
            u"string" : str_types,
        }

    class Validator(object):
        VALIDATORS = dict(validators)
        META_SCHEMA = dict(meta_schema)
        DEFAULT_TYPES = dict(default_types)

        def __init__(
            self, schema, types=(), resolver=None, format_checker=None,
        ):
            self._types = dict(self.DEFAULT_TYPES)
            self._types.update(types)

            if resolver is None:
                resolver = RefResolver.from_schema(schema)

            self.resolver = resolver
            self.format_checker = format_checker
            self.schema = schema

        @classmethod
        def check_schema(cls, schema):
            for error in cls(cls.META_SCHEMA).iter_errors(schema):
                raise SchemaError.create_from(error)

        def iter_errors(self, instance, _schema=None):
            if _schema is None:
                _schema = self.schema

            with self.resolver.in_scope(_schema.get(u"id", u"")):
                ref = _schema.get(u"$ref")
                if ref is not None:
                    validators = [(u"$ref", ref)]
                else:
                    validators = iteritems(_schema)

                for k, v in validators:
                    validator = self.VALIDATORS.get(k)
                    if validator is None:
                        continue

                    errors = validator(self, v, instance, _schema) or ()
                    for error in errors:
                        # set details if not already set by the called fn
                        error._set(
                            validator=k,
                            validator_value=v,
                            instance=instance,
                            schema=_schema,
                        )
                        if k != u"$ref":
                            error.schema_path.appendleft(k)
                        yield error

        def descend(self, instance, schema, path=None, schema_path=None):
            for error in self.iter_errors(instance, schema):
                if path is not None:
                    error.path.appendleft(path)
                if schema_path is not None:
                    error.schema_path.appendleft(schema_path)
                yield error

        def validate(self, *args, **kwargs):
            for error in self.iter_errors(*args, **kwargs):
                raise error

        def is_type(self, instance, type):
            if type not in self._types:
                raise UnknownType(type, instance, self.schema)
            pytypes = self._types[type]

            # bool inherits from int, so ensure bools aren't reported as ints
            if isinstance(instance, bool):
                pytypes = _utils.flatten(pytypes)
                is_number = any(
                    issubclass(pytype, numbers.Number) for pytype in pytypes
                )
                if is_number and bool not in pytypes:
                    return False
            return isinstance(instance, pytypes)

        def is_valid(self, instance, _schema=None):
            error = next(self.iter_errors(instance, _schema), None)
            return error is None

    if version is not None:
        Validator = validates(version)(Validator)
        Validator.__name__ = version.title().replace(" ", "") + "Validator"

    return Validator


def extend(validator, validators, version=None):
    all_validators = dict(validator.VALIDATORS)
    all_validators.update(validators)
    return create(
        meta_schema=validator.META_SCHEMA,
        validators=all_validators,
        version=version,
        default_types=validator.DEFAULT_TYPES,
    )


Draft3Validator = create(
    meta_schema=_utils.load_schema("draft3"),
    validators={
        u"$ref" : _validators.ref,
        u"additionalItems" : _validators.additionalItems,
        u"additionalProperties" : _validators.additionalProperties,
        u"dependencies" : _validators.dependencies,
        u"disallow" : _validators.disallow_draft3,
        u"divisibleBy" : _validators.multipleOf,
        u"enum" : _validators.enum,
        u"extends" : _validators.extends_draft3,
        u"format" : _validators.format,
        u"items" : _validators.items,
        u"maxItems" : _validators.maxItems,
        u"maxLength" : _validators.maxLength,
        u"maximum" : _validators.maximum,
        u"minItems" : _validators.minItems,
        u"minLength" : _validators.minLength,
        u"minimum" : _validators.minimum,
        u"multipleOf" : _validators.multipleOf,
        u"pattern" : _validators.pattern,
        u"patternProperties" : _validators.patternProperties,
        u"properties" : _validators.properties_draft3,
        u"type" : _validators.type_draft3,
        u"uniqueItems" : _validators.uniqueItems,
    },
    version="draft3",
)

Draft4Validator = create(
    meta_schema=_utils.load_schema("draft4"),
    validators={
        u"$ref" : _validators.ref,
        u"additionalItems" : _validators.additionalItems,
        u"additionalProperties" : _validators.additionalProperties,
        u"allOf" : _validators.allOf_draft4,
        u"anyOf" : _validators.anyOf_draft4,
        u"dependencies" : _validators.dependencies,
        u"enum" : _validators.enum,
        u"format" : _validators.format,
        u"items" : _validators.items,
        u"maxItems" : _validators.maxItems,
        u"maxLength" : _validators.maxLength,
        u"maxProperties" : _validators.maxProperties_draft4,
        u"maximum" : _validators.maximum,
        u"minItems" : _validators.minItems,
        u"minLength" : _validators.minLength,
        u"minProperties" : _validators.minProperties_draft4,
        u"minimum" : _validators.minimum,
        u"multipleOf" : _validators.multipleOf,
        u"not" : _validators.not_draft4,
        u"oneOf" : _validators.oneOf_draft4,
        u"pattern" : _validators.pattern,
        u"patternProperties" : _validators.patternProperties,
        u"properties" : _validators.properties_draft4,
        u"required" : _validators.required_draft4,
        u"type" : _validators.type_draft4,
        u"uniqueItems" : _validators.uniqueItems,
    },
    version="draft4",
)


class RefResolver(object):
    """
    Resolve JSON References.

    :argument str base_uri: URI of the referring document
    :argument referrer: the actual referring document
    :argument dict store: a mapping from URIs to documents to cache
    :argument bool cache_remote: whether remote refs should be cached after
        first resolution
    :argument dict handlers: a mapping from URI schemes to functions that
        should be used to retrieve them

    """

    def __init__(
        self, base_uri, referrer, store=(), cache_remote=True, handlers=(),
    ):
        self.base_uri = base_uri
        self.resolution_scope = base_uri
        # This attribute is not used, it is for backwards compatibility
        self.referrer = referrer
        self.cache_remote = cache_remote
        self.handlers = dict(handlers)

        self.store = _utils.URIDict(
            (id, validator.META_SCHEMA)
            for id, validator in iteritems(meta_schemas)
        )
        self.store.update(store)
        self.store[base_uri] = referrer

    @classmethod
    def from_schema(cls, schema, *args, **kwargs):
        """
        Construct a resolver from a JSON schema object.

        :argument schema schema: the referring schema
        :rtype: :class:`RefResolver`

        """

        return cls(schema.get(u"id", u""), schema, *args, **kwargs)

    @contextlib.contextmanager
    def in_scope(self, scope):
        old_scope = self.resolution_scope
        self.resolution_scope = urljoin(old_scope, scope)
        try:
            yield
        finally:
            self.resolution_scope = old_scope

    @contextlib.contextmanager
    def resolving(self, ref):
        """
        Context manager which resolves a JSON ``ref`` and enters the
        resolution scope of this ref.

        :argument str ref: reference to resolve

        """

        full_uri = urljoin(self.resolution_scope, ref)
        uri, fragment = urldefrag(full_uri)
        if not uri:
            uri = self.base_uri

        if uri in self.store:
            document = self.store[uri]
        else:
            try:
                document = self.resolve_remote(uri)
            except Exception as exc:
                raise RefResolutionError(exc)

        old_base_uri, self.base_uri = self.base_uri, uri
        try:
            with self.in_scope(uri):
                yield self.resolve_fragment(document, fragment)
        finally:
            self.base_uri = old_base_uri

    def resolve_fragment(self, document, fragment):
        """
        Resolve a ``fragment`` within the referenced ``document``.

        :argument document: the referrant document
        :argument str fragment: a URI fragment to resolve within it

        """

        fragment = fragment.lstrip(u"/")
        parts = unquote(fragment).split(u"/") if fragment else []

        for part in parts:
            part = part.replace(u"~1", u"/").replace(u"~0", u"~")

            if isinstance(document, Sequence):
                # Array indexes should be turned into integers
                try:
                    part = int(part)
                except ValueError:
                    pass
            try:
                document = document[part]
            except (TypeError, LookupError):
                raise RefResolutionError(
                    "Unresolvable JSON pointer: %r" % fragment
                )

        return document

    def resolve_remote(self, uri):
        """
        Resolve a remote ``uri``.

        Does not check the store first, but stores the retrieved document in
        the store if :attr:`RefResolver.cache_remote` is True.

        .. note::

            If the requests_ library is present, ``jsonschema`` will use it to
            request the remote ``uri``, so that the correct encoding is
            detected and used.

            If it isn't, or if the scheme of the ``uri`` is not ``http`` or
            ``https``, UTF-8 is assumed.

        :argument str uri: the URI to resolve
        :returns: the retrieved document

        .. _requests: http://pypi.python.org/pypi/requests/

        """

        scheme = urlsplit(uri).scheme

        if scheme in self.handlers:
            result = self.handlers[scheme](uri)
        elif (
            scheme in [u"http", u"https"] and
            requests and
            getattr(requests.Response, "json", None) is not None
        ):
            # Requests has support for detecting the correct encoding of
            # json over http
            if callable(requests.Response.json):
                result = requests.get(uri).json()
            else:
                result = requests.get(uri).json
        else:
            # Otherwise, pass off to urllib and assume utf-8
            result = json.loads(urlopen(uri).read().decode("utf-8"))

        if self.cache_remote:
            self.store[uri] = result
        return result


def validator_for(schema, default=_unset):
    if default is _unset:
        default = Draft4Validator
    return meta_schemas.get(schema.get(u"$schema", u""), default)


def validate(instance, schema, cls=None, *args, **kwargs):
    """
    Validate an instance under the given schema.

        >>> validate([2, 3, 4], {"maxItems" : 2})
        Traceback (most recent call last):
            ...
        ValidationError: [2, 3, 4] is too long

    :func:`validate` will first verify that the provided schema is itself
    valid, since not doing so can lead to less obvious error messages and fail
    in less obvious or consistent ways. If you know you have a valid schema
    already or don't care, you might prefer using the
    :meth:`~IValidator.validate` method directly on a specific validator
    (e.g. :meth:`Draft4Validator.validate`).


    :argument instance: the instance to validate
    :argument schema: the schema to validate with
    :argument cls: an :class:`IValidator` class that will be used to validate
                   the instance.

    If the ``cls`` argument is not provided, two things will happen in
    accordance with the specification. First, if the schema has a
    :validator:`$schema` property containing a known meta-schema [#]_ then the
    proper validator will be used.  The specification recommends that all
    schemas contain :validator:`$schema` properties for this reason. If no
    :validator:`$schema` property is found, the default validator class is
    :class:`Draft4Validator`.

    Any other provided positional and keyword arguments will be passed on when
    instantiating the ``cls``.

    :raises:
        :exc:`ValidationError` if the instance is invalid

        :exc:`SchemaError` if the schema itself is invalid

    .. rubric:: Footnotes
    .. [#] known by a validator registered with :func:`validates`
    """
    if cls is None:
        cls = validator_for(schema)
    cls.check_schema(schema)
    cls(schema, *args, **kwargs).validate(instance)

########NEW FILE########
__FILENAME__ = _format
import datetime
import re
import socket

from jsonschema.compat import str_types
from jsonschema.exceptions import FormatError


class FormatChecker(object):
    """
    A ``format`` property checker.

    JSON Schema does not mandate that the ``format`` property actually do any
    validation. If validation is desired however, instances of this class can
    be hooked into validators to enable format validation.

    :class:`FormatChecker` objects always return ``True`` when asked about
    formats that they do not know how to validate.

    To check a custom format using a function that takes an instance and
    returns a ``bool``, use the :meth:`FormatChecker.checks` or
    :meth:`FormatChecker.cls_checks` decorators.

    :argument iterable formats: the known formats to validate. This argument
                                can be used to limit which formats will be used
                                during validation.

    """

    checkers = {}

    def __init__(self, formats=None):
        if formats is None:
            self.checkers = self.checkers.copy()
        else:
            self.checkers = dict((k, self.checkers[k]) for k in formats)

    def checks(self, format, raises=()):
        """
        Register a decorated function as validating a new format.

        :argument str format: the format that the decorated function will check
        :argument Exception raises: the exception(s) raised by the decorated
            function when an invalid instance is found. The exception object
            will be accessible as the :attr:`ValidationError.cause` attribute
            of the resulting validation error.

        """

        def _checks(func):
            self.checkers[format] = (func, raises)
            return func
        return _checks

    cls_checks = classmethod(checks)

    def check(self, instance, format):
        """
        Check whether the instance conforms to the given format.

        :argument instance: the instance to check
        :type: any primitive type (str, number, bool)
        :argument str format: the format that instance should conform to
        :raises: :exc:`FormatError` if instance does not conform to format

        """

        if format not in self.checkers:
            return

        func, raises = self.checkers[format]
        result, cause = None, None
        try:
            result = func(instance)
        except raises as e:
            cause = e
        if not result:
            raise FormatError(
                "%r is not a %r" % (instance, format), cause=cause,
            )

    def conforms(self, instance, format):
        """
        Check whether the instance conforms to the given format.

        :argument instance: the instance to check
        :type: any primitive type (str, number, bool)
        :argument str format: the format that instance should conform to
        :rtype: bool

        """

        try:
            self.check(instance, format)
        except FormatError:
            return False
        else:
            return True


_draft_checkers = {"draft3": [], "draft4": []}


def _checks_drafts(both=None, draft3=None, draft4=None, raises=()):
    draft3 = draft3 or both
    draft4 = draft4 or both

    def wrap(func):
        if draft3:
            _draft_checkers["draft3"].append(draft3)
            func = FormatChecker.cls_checks(draft3, raises)(func)
        if draft4:
            _draft_checkers["draft4"].append(draft4)
            func = FormatChecker.cls_checks(draft4, raises)(func)
        return func
    return wrap


@_checks_drafts("email")
def is_email(instance):
    if not isinstance(instance, str_types):
        return True
    return "@" in instance


_ipv4_re = re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")

@_checks_drafts(draft3="ip-address", draft4="ipv4")
def is_ipv4(instance):
    if not isinstance(instance, str_types):
        return True
    if not _ipv4_re.match(instance):
        return False
    return all(0 <= int(component) <= 255 for component in instance.split("."))


if hasattr(socket, "inet_pton"):
    @_checks_drafts("ipv6", raises=socket.error)
    def is_ipv6(instance):
        if not isinstance(instance, str_types):
            return True
        return socket.inet_pton(socket.AF_INET6, instance)


_host_name_re = re.compile(r"^[A-Za-z0-9][A-Za-z0-9\.\-]{1,255}$")

@_checks_drafts(draft3="host-name", draft4="hostname")
def is_host_name(instance):
    if not isinstance(instance, str_types):
        return True
    if not _host_name_re.match(instance):
        return False
    components = instance.split(".")
    for component in components:
        if len(component) > 63:
            return False
    return True


try:
    import rfc3987
except ImportError:
    pass
else:
    @_checks_drafts("uri", raises=ValueError)
    def is_uri(instance):
        if not isinstance(instance, str_types):
            return True
        return rfc3987.parse(instance, rule="URI")


try:
    import strict_rfc3339
except ImportError:
    try:
        import isodate
    except ImportError:
        pass
    else:
        @_checks_drafts("date-time", raises=(ValueError, isodate.ISO8601Error))
        def is_date(instance):
            if not isinstance(instance, str_types):
                return True
            return isodate.parse_datetime(instance)
else:
        @_checks_drafts("date-time")
        def is_date(instance):
            if not isinstance(instance, str_types):
                return True
            return strict_rfc3339.validate_rfc3339(instance)


@_checks_drafts("regex", raises=re.error)
def is_regex(instance):
    if not isinstance(instance, str_types):
        return True
    return re.compile(instance)


@_checks_drafts(draft3="date", raises=ValueError)
def is_date(instance):
    if not isinstance(instance, str_types):
        return True
    return datetime.datetime.strptime(instance, "%Y-%m-%d")


@_checks_drafts(draft3="time", raises=ValueError)
def is_time(instance):
    if not isinstance(instance, str_types):
        return True
    return datetime.datetime.strptime(instance, "%H:%M:%S")


try:
    import webcolors
except ImportError:
    pass
else:
    def is_css_color_code(instance):
        return webcolors.normalize_hex(instance)


    @_checks_drafts(draft3="color", raises=(ValueError, TypeError))
    def is_css21_color(instance):
        if (
            not isinstance(instance, str_types) or
            instance.lower() in webcolors.css21_names_to_hex
        ):
            return True
        return is_css_color_code(instance)


    def is_css3_color(instance):
        if instance.lower() in webcolors.css3_names_to_hex:
            return True
        return is_css_color_code(instance)


draft3_format_checker = FormatChecker(_draft_checkers["draft3"])
draft4_format_checker = FormatChecker(_draft_checkers["draft4"])

########NEW FILE########
__FILENAME__ = _reflect
# -*- test-case-name: twisted.test.test_reflect -*-
# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.

"""
Standardized versions of various cool and/or strange things that you can do
with Python's reflection capabilities.
"""

import sys

from jsonschema.compat import PY3


class _NoModuleFound(Exception):
    """
    No module was found because none exists.
    """



class InvalidName(ValueError):
    """
    The given name is not a dot-separated list of Python objects.
    """



class ModuleNotFound(InvalidName):
    """
    The module associated with the given name doesn't exist and it can't be
    imported.
    """



class ObjectNotFound(InvalidName):
    """
    The object associated with the given name doesn't exist and it can't be
    imported.
    """



if PY3:
    def reraise(exception, traceback):
        raise exception.with_traceback(traceback)
else:
    exec("""def reraise(exception, traceback):
        raise exception.__class__, exception, traceback""")

reraise.__doc__ = """
Re-raise an exception, with an optional traceback, in a way that is compatible
with both Python 2 and Python 3.

Note that on Python 3, re-raised exceptions will be mutated, with their
C{__traceback__} attribute being set.

@param exception: The exception instance.
@param traceback: The traceback to use, or C{None} indicating a new traceback.
"""


def _importAndCheckStack(importName):
    """
    Import the given name as a module, then walk the stack to determine whether
    the failure was the module not existing, or some code in the module (for
    example a dependent import) failing.  This can be helpful to determine
    whether any actual application code was run.  For example, to distiguish
    administrative error (entering the wrong module name), from programmer
    error (writing buggy code in a module that fails to import).

    @param importName: The name of the module to import.
    @type importName: C{str}
    @raise Exception: if something bad happens.  This can be any type of
        exception, since nobody knows what loading some arbitrary code might
        do.
    @raise _NoModuleFound: if no module was found.
    """
    try:
        return __import__(importName)
    except ImportError:
        excType, excValue, excTraceback = sys.exc_info()
        while excTraceback:
            execName = excTraceback.tb_frame.f_globals["__name__"]
            # in Python 2 execName is None when an ImportError is encountered,
            # where in Python 3 execName is equal to the importName.
            if execName is None or execName == importName:
                reraise(excValue, excTraceback)
            excTraceback = excTraceback.tb_next
        raise _NoModuleFound()



def namedAny(name):
    """
    Retrieve a Python object by its fully qualified name from the global Python
    module namespace.  The first part of the name, that describes a module,
    will be discovered and imported.  Each subsequent part of the name is
    treated as the name of an attribute of the object specified by all of the
    name which came before it.  For example, the fully-qualified name of this
    object is 'twisted.python.reflect.namedAny'.

    @type name: L{str}
    @param name: The name of the object to return.

    @raise InvalidName: If the name is an empty string, starts or ends with
        a '.', or is otherwise syntactically incorrect.

    @raise ModuleNotFound: If the name is syntactically correct but the
        module it specifies cannot be imported because it does not appear to
        exist.

    @raise ObjectNotFound: If the name is syntactically correct, includes at
        least one '.', but the module it specifies cannot be imported because
        it does not appear to exist.

    @raise AttributeError: If an attribute of an object along the way cannot be
        accessed, or a module along the way is not found.

    @return: the Python object identified by 'name'.
    """
    if not name:
        raise InvalidName('Empty module name')

    names = name.split('.')

    # if the name starts or ends with a '.' or contains '..', the __import__
    # will raise an 'Empty module name' error. This will provide a better error
    # message.
    if '' in names:
        raise InvalidName(
            "name must be a string giving a '.'-separated list of Python "
            "identifiers, not %r" % (name,))

    topLevelPackage = None
    moduleNames = names[:]
    while not topLevelPackage:
        if moduleNames:
            trialname = '.'.join(moduleNames)
            try:
                topLevelPackage = _importAndCheckStack(trialname)
            except _NoModuleFound:
                moduleNames.pop()
        else:
            if len(names) == 1:
                raise ModuleNotFound("No module named %r" % (name,))
            else:
                raise ObjectNotFound('%r does not name an object' % (name,))

    obj = topLevelPackage
    for n in names[1:]:
        obj = getattr(obj, n)

    return obj

########NEW FILE########
__FILENAME__ = _utils
import itertools
import json
import pkgutil
import re

from jsonschema.compat import str_types, MutableMapping, urlsplit


class URIDict(MutableMapping):
    """
    Dictionary which uses normalized URIs as keys.

    """

    def normalize(self, uri):
        return urlsplit(uri).geturl()

    def __init__(self, *args, **kwargs):
        self.store = dict()
        self.store.update(*args, **kwargs)

    def __getitem__(self, uri):
        return self.store[self.normalize(uri)]

    def __setitem__(self, uri, value):
        self.store[self.normalize(uri)] = value

    def __delitem__(self, uri):
        del self.store[self.normalize(uri)]

    def __iter__(self):
        return iter(self.store)

    def __len__(self):
        return len(self.store)

    def __repr__(self):
        return repr(self.store)


class Unset(object):
    """
    An as-of-yet unset attribute or unprovided default parameter.

    """

    def __repr__(self):
        return "<unset>"


def load_schema(name):
    """
    Load a schema from ./schemas/``name``.json and return it.

    """

    data = pkgutil.get_data(__package__, "schemas/{0}.json".format(name))
    return json.loads(data.decode("utf-8"))


def indent(string, times=1):
    """
    A dumb version of :func:`textwrap.indent` from Python 3.3.

    """

    return "\n".join(" " * (4 * times) + line for line in string.splitlines())


def format_as_index(indices):
    """
    Construct a single string containing indexing operations for the indices.

    For example, [1, 2, "foo"] -> [1][2]["foo"]

    :type indices: sequence

    """

    if not indices:
        return ""
    return "[%s]" % "][".join(repr(index) for index in indices)


def find_additional_properties(instance, schema):
    """
    Return the set of additional properties for the given ``instance``.

    Weeds out properties that should have been validated by ``properties`` and
    / or ``patternProperties``.

    Assumes ``instance`` is dict-like already.

    """

    properties = schema.get("properties", {})
    patterns = "|".join(schema.get("patternProperties", {}))
    for property in instance:
        if property not in properties:
            if patterns and re.search(patterns, property):
                continue
            yield property


def extras_msg(extras):
    """
    Create an error message for extra items or properties.

    """

    if len(extras) == 1:
        verb = "was"
    else:
        verb = "were"
    return ", ".join(repr(extra) for extra in extras), verb


def types_msg(instance, types):
    """
    Create an error message for a failure to match the given types.

    If the ``instance`` is an object and contains a ``name`` property, it will
    be considered to be a description of that object and used as its type.

    Otherwise the message is simply the reprs of the given ``types``.

    """

    reprs = []
    for type in types:
        try:
            reprs.append(repr(type["name"]))
        except Exception:
            reprs.append(repr(type))
    return "%r is not of type %s" % (instance, ", ".join(reprs))


def flatten(suitable_for_isinstance):
    """
    isinstance() can accept a bunch of really annoying different types:
        * a single type
        * a tuple of types
        * an arbitrary nested tree of tuples

    Return a flattened tuple of the given argument.

    """

    types = set()

    if not isinstance(suitable_for_isinstance, tuple):
        suitable_for_isinstance = (suitable_for_isinstance,)
    for thing in suitable_for_isinstance:
        if isinstance(thing, tuple):
            types.update(flatten(thing))
        else:
            types.add(thing)
    return tuple(types)


def ensure_list(thing):
    """
    Wrap ``thing`` in a list if it's a single str.

    Otherwise, return it unchanged.

    """

    if isinstance(thing, str_types):
        return [thing]
    return thing


def unbool(element, true=object(), false=object()):
    """
    A hack to make True and 1 and False and 0 unique for ``uniq``.

    """

    if element is True:
        return true
    elif element is False:
        return false
    return element


def uniq(container):
    """
    Check if all of a container's elements are unique.

    Successively tries first to rely that the elements are hashable, then
    falls back on them being sortable, and finally falls back on brute
    force.

    """

    try:
        return len(set(unbool(i) for i in container)) == len(container)
    except TypeError:
        try:
            sort = sorted(unbool(i) for i in container)
            sliced = itertools.islice(sort, 1, None)
            for i, j in zip(sort, sliced):
                if i == j:
                    return False
        except (NotImplementedError, TypeError):
            seen = []
            for e in container:
                e = unbool(e)
                if e in seen:
                    return False
                seen.append(e)
    return True

########NEW FILE########
__FILENAME__ = _validators
import re

from jsonschema import _utils
from jsonschema.exceptions import FormatError, ValidationError
from jsonschema.compat import iteritems


FLOAT_TOLERANCE = 10 ** -15


def patternProperties(validator, patternProperties, instance, schema):
    if not validator.is_type(instance, "object"):
        return

    for pattern, subschema in iteritems(patternProperties):
        for k, v in iteritems(instance):
            if re.search(pattern, k):
                for error in validator.descend(
                    v, subschema, path=k, schema_path=pattern,
                ):
                    yield error


def additionalProperties(validator, aP, instance, schema):
    if not validator.is_type(instance, "object"):
        return

    extras = set(_utils.find_additional_properties(instance, schema))

    if validator.is_type(aP, "object"):
        for extra in extras:
            for error in validator.descend(instance[extra], aP, path=extra):
                yield error
    elif not aP and extras:
        error = "Additional properties are not allowed (%s %s unexpected)"
        yield ValidationError(error % _utils.extras_msg(extras))


def items(validator, items, instance, schema):
    if not validator.is_type(instance, "array"):
        return

    if validator.is_type(items, "object"):
        for index, item in enumerate(instance):
            for error in validator.descend(item, items, path=index):
                yield error
    else:
        for (index, item), subschema in zip(enumerate(instance), items):
            for error in validator.descend(
                item, subschema, path=index, schema_path=index,
            ):
                yield error


def additionalItems(validator, aI, instance, schema):
    if (
        not validator.is_type(instance, "array") or
        validator.is_type(schema.get("items", {}), "object")
    ):
        return

    len_items = len(schema.get("items", []))
    if validator.is_type(aI, "object"):
        for index, item in enumerate(instance[len_items:], start=len_items):
            for error in validator.descend(item, aI, path=index):
                yield error
    elif not aI and len(instance) > len(schema.get("items", [])):
        error = "Additional items are not allowed (%s %s unexpected)"
        yield ValidationError(
            error %
            _utils.extras_msg(instance[len(schema.get("items", [])):])
        )


def minimum(validator, minimum, instance, schema):
    if not validator.is_type(instance, "number"):
        return

    if schema.get("exclusiveMinimum", False):
        failed = float(instance) <= minimum
        cmp = "less than or equal to"
    else:
        failed = float(instance) < minimum
        cmp = "less than"

    if failed:
        yield ValidationError(
            "%r is %s the minimum of %r" % (instance, cmp, minimum)
        )


def maximum(validator, maximum, instance, schema):
    if not validator.is_type(instance, "number"):
        return

    if schema.get("exclusiveMaximum", False):
        failed = float(instance) >= maximum
        cmp = "greater than or equal to"
    else:
        failed = float(instance) > maximum
        cmp = "greater than"

    if failed:
        yield ValidationError(
            "%r is %s the maximum of %r" % (instance, cmp, maximum)
        )


def multipleOf(validator, dB, instance, schema):
    if not validator.is_type(instance, "number"):
        return

    if isinstance(dB, float):
        mod = instance % dB
        failed = (mod > FLOAT_TOLERANCE) and (dB - mod) > FLOAT_TOLERANCE
    else:
        failed = instance % dB

    if failed:
        yield ValidationError("%r is not a multiple of %r" % (instance, dB))


def minItems(validator, mI, instance, schema):
    if validator.is_type(instance, "array") and len(instance) < mI:
        yield ValidationError("%r is too short" % (instance,))


def maxItems(validator, mI, instance, schema):
    if validator.is_type(instance, "array") and len(instance) > mI:
        yield ValidationError("%r is too long" % (instance,))


def uniqueItems(validator, uI, instance, schema):
    if (
        uI and
        validator.is_type(instance, "array") and
        not _utils.uniq(instance)
    ):
        yield ValidationError("%r has non-unique elements" % instance)


def pattern(validator, patrn, instance, schema):
    if (
        validator.is_type(instance, "string") and
        not re.search(patrn, instance)
    ):
        yield ValidationError("%r does not match %r" % (instance, patrn))


def format(validator, format, instance, schema):
    if validator.format_checker is not None:
        try:
            validator.format_checker.check(instance, format)
        except FormatError as error:
            yield ValidationError(error.message, cause=error.cause)


def minLength(validator, mL, instance, schema):
    if validator.is_type(instance, "string") and len(instance) < mL:
        yield ValidationError("%r is too short" % (instance,))


def maxLength(validator, mL, instance, schema):
    if validator.is_type(instance, "string") and len(instance) > mL:
        yield ValidationError("%r is too long" % (instance,))


def dependencies(validator, dependencies, instance, schema):
    if not validator.is_type(instance, "object"):
        return

    for property, dependency in iteritems(dependencies):
        if property not in instance:
            continue

        if validator.is_type(dependency, "object"):
            for error in validator.descend(
                instance, dependency, schema_path=property,
            ):
                yield error
        else:
            dependencies = _utils.ensure_list(dependency)
            for dependency in dependencies:
                if dependency not in instance:
                    yield ValidationError(
                        "%r is a dependency of %r" % (dependency, property)
                    )


def enum(validator, enums, instance, schema):
    if instance not in enums:
        yield ValidationError("%r is not one of %r" % (instance, enums))


def ref(validator, ref, instance, schema):
    with validator.resolver.resolving(ref) as resolved:
        for error in validator.descend(instance, resolved):
            yield error


def type_draft3(validator, types, instance, schema):
    types = _utils.ensure_list(types)

    all_errors = []
    for index, type in enumerate(types):
        if type == "any":
            return
        if validator.is_type(type, "object"):
            errors = list(validator.descend(instance, type, schema_path=index))
            if not errors:
                return
            all_errors.extend(errors)
        else:
            if validator.is_type(instance, type):
                return
    else:
        yield ValidationError(
            _utils.types_msg(instance, types), context=all_errors,
        )


def properties_draft3(validator, properties, instance, schema):
    if not validator.is_type(instance, "object"):
        return

    for property, subschema in iteritems(properties):
        if property in instance:
            for error in validator.descend(
                instance[property],
                subschema,
                path=property,
                schema_path=property,
            ):
                yield error
        elif subschema.get("required", False):
            error = ValidationError("%r is a required property" % property)
            error._set(
                validator="required",
                validator_value=subschema["required"],
                instance=instance,
                schema=schema,
            )
            error.path.appendleft(property)
            error.schema_path.extend([property, "required"])
            yield error


def disallow_draft3(validator, disallow, instance, schema):
    for disallowed in _utils.ensure_list(disallow):
        if validator.is_valid(instance, {"type" : [disallowed]}):
            yield ValidationError(
                "%r is disallowed for %r" % (disallowed, instance)
            )


def extends_draft3(validator, extends, instance, schema):
    if validator.is_type(extends, "object"):
        for error in validator.descend(instance, extends):
            yield error
        return
    for index, subschema in enumerate(extends):
        for error in validator.descend(instance, subschema, schema_path=index):
            yield error


def type_draft4(validator, types, instance, schema):
    types = _utils.ensure_list(types)

    if not any(validator.is_type(instance, type) for type in types):
        yield ValidationError(_utils.types_msg(instance, types))


def properties_draft4(validator, properties, instance, schema):
    if not validator.is_type(instance, "object"):
        return

    for property, subschema in iteritems(properties):
        if property in instance:
            for error in validator.descend(
                instance[property],
                subschema,
                path=property,
                schema_path=property,
            ):
                yield error


def required_draft4(validator, required, instance, schema):
    if not validator.is_type(instance, "object"):
        return
    for property in required:
        if property not in instance:
            yield ValidationError("%r is a required property" % property)


def minProperties_draft4(validator, mP, instance, schema):
    if validator.is_type(instance, "object") and len(instance) < mP:
        yield ValidationError(
            "%r does not have enough properties" % (instance,)
        )


def maxProperties_draft4(validator, mP, instance, schema):
    if not validator.is_type(instance, "object"):
        return
    if validator.is_type(instance, "object") and len(instance) > mP:
        yield ValidationError("%r has too many properties" % (instance,))


def allOf_draft4(validator, allOf, instance, schema):
    for index, subschema in enumerate(allOf):
        for error in validator.descend(instance, subschema, schema_path=index):
            yield error


def oneOf_draft4(validator, oneOf, instance, schema):
    subschemas = enumerate(oneOf)
    all_errors = []
    for index, subschema in subschemas:
        errs = list(validator.descend(instance, subschema, schema_path=index))
        if not errs:
            first_valid = subschema
            break
        all_errors.extend(errs)
    else:
        yield ValidationError(
            "%r is not valid under any of the given schemas" % (instance,),
            context=all_errors,
        )

    more_valid = [s for i, s in subschemas if validator.is_valid(instance, s)]
    if more_valid:
        more_valid.append(first_valid)
        reprs = ", ".join(repr(schema) for schema in more_valid)
        yield ValidationError(
            "%r is valid under each of %s" % (instance, reprs)
        )


def anyOf_draft4(validator, anyOf, instance, schema):
    all_errors = []
    for index, subschema in enumerate(anyOf):
        errs = list(validator.descend(instance, subschema, schema_path=index))
        if not errs:
            break
        all_errors.extend(errs)
    else:
        yield ValidationError(
            "%r is not valid under any of the given schemas" % (instance,),
            context=all_errors,
        )


def not_draft4(validator, not_schema, instance, schema):
    if validator.is_valid(instance, not_schema):
        yield ValidationError(
            "%r is not allowed for %r" % (not_schema, instance)
        )

########NEW FILE########
__FILENAME__ = __main__
from jsonschema.cli import main
main()

########NEW FILE########
