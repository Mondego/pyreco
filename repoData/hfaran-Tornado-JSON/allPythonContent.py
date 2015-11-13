__FILENAME__ = api
from tornado import gen

from tornado_json.requesthandlers import APIHandler
from tornado_json import schema


class HelloWorldHandler(APIHandler):

    # Decorate any HTTP methods with the `schema.validate` decorator
    #   to validate input to it and output from it as per the
    #   the schema ``input_schema`` and ``output_schema`` arguments passed.
    # Simply use `return` rather than `self.write` to write back
    #   your output.
    @schema.validate(
        output_schema={"type": "string"},
        output_example="Hello world!"
    )
    def get(self):
        """Shouts hello to the world!"""
        return "Hello world!"


class AsyncHelloWorld(APIHandler):

    def hello(self, callback=None):
        callback("Hello (asynchronous) world!")

    @schema.validate(
        output_schema={"type": "string"},
        output_example="Hello (asynchronous) world!"
    )
    @gen.coroutine
    def get(self):
        """Shouts hello to the world (asynchronously)!"""
        # Asynchronously yield a result from a method
        res = yield gen.Task(self.hello)

        # When using the `schema.validate` decorator asynchronously,
        #   we can return the output desired by raising
        #   `tornado.gen.Return(value)` which returns a
        #   Future that the decorator will yield.
        # In Python 3.3, using `raise Return(value)` is no longer
        #   necessary and can be replaced with simply `return value`.
        #   For details, see:
        # http://www.tornadoweb.org/en/branch3.2/gen.html#tornado.gen.Return

        # return res  # Python 3.3
        raise gen.Return(res)  # Python 2.7


class PostIt(APIHandler):

    @schema.validate(
        input_schema={
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "body": {"type": "string"},
                "index": {"type": "number"},
            }
        },
        input_example={
            "title": "Very Important Post-It Note",
            "body": "Equally important message",
            "index": 0
        },
        output_schema={
            "type": "object",
            "properties": {
                "message": {"type": "string"}
            }
        },
        output_example={
            "message": "Very Important Post-It Note was posted."
        },
    )
    def post(self):
        """
        POST the required parameters to post a Post-It note

        * `title`: Title of the note
        * `body`: Body of the note
        * `index`: An easy index with which to find the note
        """
        # `schema.validate` will JSON-decode `self.request.body` for us
        #   and set self.body as the result, so we can use that here
        return {
            "message": "{} was posted.".format(self.body["title"])
        }


class Greeting(APIHandler):

    # When you include extra arguments in the signature of an HTTP
    #   method, Tornado-JSON will generate a route that matches the extra
    #   arguments; here, you can GET /api/greeting/John/Smith and you will
    #   get a response back that says, "Greetings, John Smith!"
    # You can match the regex equivalent of `\w+`.
    @schema.validate(
        output_schema={"type": "string"},
        output_example="Greetings, Named Person!"
    )
    def get(self, fname, lname):
        """Greets you."""
        return "Greetings, {} {}!".format(fname, lname)


class FreeWilledHandler(APIHandler):

    # And of course, you aren't forced to use schema validation;
    #   if you want your handlers to do something more custom,
    #   they definitely can.
    def get(self):
        # If you don't know where `self.success` comes from, it is defined
        #   in the `JSendMixin` mixin in tornado_json.jsend. `APIHandler`
        #   inherits from this and thus gets the methods.
        self.success("I don't need no stinkin' schema validation.")
        # If you're feeling really bold, you could even skip JSend
        #   altogether and do the following EVIL thing:
        # self.write("I'm writing back a string that isn't JSON! Take that!")

########NEW FILE########
__FILENAME__ = helloworld
#!/usr/bin/env python2.7

# ---- The following so demo can be run without having to install package ----#
import sys
sys.path.append("../../")
# ---- Can be removed if Tornado-JSON is installed ----#

import json
import tornado.ioloop
from tornado_json.routes import get_routes
from tornado_json.application import Application


def main():
    # Pass the web app's package the get_routes and it will generate
    #   routes based on the submodule names and ending with lowercase
    #   request handler name (with 'handler' removed from the end of the
    #   name if it is the name).
    # [("/api/helloworld", helloworld.api.HelloWorldHandler)]
    import helloworld
    routes = get_routes(helloworld)
    print("Routes\n======\n\n" + json.dumps(
        [(url, repr(rh)) for url, rh in routes],
        indent=2)
    )
    # Create the application by passing routes and any settings
    application = Application(routes=routes, settings={})

    # Start the application on port 8888
    application.listen(8888)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = app
#!/usr/bin/env python2.7

# ---- The following so demo can be run without having to install package ----#
import sys
sys.path.append("../../")
# ---- Can be removed if Tornado-JSON is installed ----#

# This module contains essentially the same boilerplate
#   as the corresponding one in the helloworld example;
#   refer to that for details.

import json
import tornado.ioloop
from tornado_json.routes import get_routes
from tornado_json.application import Application


def main():
    import cars
    routes = get_routes(cars)
    print("Routes\n======\n\n" + json.dumps(
        [(url, repr(rh)) for url, rh in routes],
        indent=2)
    )
    application = Application(routes=routes, settings={})

    application.listen(8888)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# tornado_json documentation build configuration file, created by
# sphinx-quickstart on Thu Dec 19 00:44:46 2013.
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
sys.path.insert(0, os.path.abspath('../'))
import tornado_json

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.viewcode']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Tornado-JSON'
copyright = u'2014, Hamza Faran'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = tornado_json.__version__
# The full version, including alpha/beta/rc tags.
release = tornado_json.__version__

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

# on_rtd is whether we are on readthedocs.org, this line of code grabbed from docs.readthedocs.org
on_rtd = os.environ.get('READTHEDOCS', None) == 'True'

if not on_rtd:  # only import and set the theme if we're building docs locally
    import sphinx_rtd_theme
    html_theme = "sphinx_rtd_theme"

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
    html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]

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
htmlhelp_basename = 'tornado_jsondoc'


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
  ('index', 'tornado_json.tex', u'tornado\\_json Documentation',
   u'Author', 'manual'),
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
    ('index', 'tornado_json', u'tornado_json Documentation',
     [u'Author'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'tornado_json', u'tornado_json Documentation',
   u'Author', 'tornado_json', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'


# -- Options for Epub output ---------------------------------------------------

# Bibliographic Dublin Core info.
epub_title = u'Tornado-JSON'
epub_author = u'Hamza Faran'
epub_publisher = u'Hamza Faran'
epub_copyright = u'2014, Hamza Faran'

# The language of the text. It defaults to the language option
# or en if the language is not set.
#epub_language = ''

# The scheme of the identifier. Typical schemes are ISBN or URL.
#epub_scheme = ''

# The unique identifier of the text. This can be a ISBN number
# or the project homepage.
#epub_identifier = ''

# A unique identification for the text.
#epub_uid = ''

# A tuple containing the cover image and cover page html template filenames.
#epub_cover = ()

# HTML files that should be inserted before the pages created by sphinx.
# The format is a list of tuples containing the path and title.
#epub_pre_files = []

# HTML files shat should be inserted after the pages created by sphinx.
# The format is a list of tuples containing the path and title.
#epub_post_files = []

# A list of files that should not be packed into the epub file.
#epub_exclude_files = []

# The depth of the table of contents in toc.ncx.
#epub_tocdepth = 3

# Allow duplicate toc entries.
#epub_tocdup = True

########NEW FILE########
__FILENAME__ = func_test
import sys
import json
from tornado.testing import AsyncHTTPTestCase

try:
    sys.path.append('.')
    from tornado_json import routes
    from tornado_json import schema
    from tornado_json import application
    from tornado_json import requesthandlers
    sys.path.append('demos/helloworld')
    import helloworld
except ImportError as e:
    print("Please run `py.test` from the root project directory")
    exit(1)


def jd(obj):
    return json.dumps(obj)


def jl(s):
    return json.loads(s.decode("utf-8"))


class DummyView(requesthandlers.ViewHandler):

    """Dummy ViewHandler for coverage"""

    def delete(self):
        # Reference db_conn to test for AttributeError
        self.db_conn


class DBTestHandler(requesthandlers.APIHandler):

    """APIHandler for testing db_conn"""

    def get(self):
        # Set application.db_conn to test if db_conn BaseHandler
        #   property works
        self.application.db_conn = {"data": "Nothing to see here."}
        self.success(self.db_conn.get("data"))


class ExplodingHandler(requesthandlers.APIHandler):

    @schema.validate(**{
        "input_schema": None,
        "output_schema": {
            "type": "number",
        }
    })
    def get(self):
        """This handler is used for testing purposes and is explosive."""
        return "I am not the handler you are looking for."

    @schema.validate(**{
        "input_schema": {
            "type": "number",
        },
        "output_schema": {
            "type": "number",
        }
    })
    def post(self):
        """This handler is used for testing purposes and is explosive."""
        return "Fission mailed."


class APIFunctionalTest(AsyncHTTPTestCase):

    def get_app(self):
        rts = routes.get_routes(helloworld)
        rts += [
            ("/api/explodinghandler", ExplodingHandler),
            ("/views/someview", DummyView),
            ("/api/dbtest", DBTestHandler)
        ]
        return application.Application(
            routes=rts,
            settings={"debug": True},
            db_conn=None
        )

    def test_synchronous_handler(self):
        r = self.fetch(
            "/api/helloworld"
        )
        self.assertEqual(r.code, 200)
        self.assertEqual(
            jl(r.body)["data"],
            "Hello world!"
        )

    def test_asynchronous_handler(self):
        r = self.fetch(
            "/api/asynchelloworld"
        )
        self.assertEqual(r.code, 200)
        self.assertEqual(
            jl(r.body)["data"],
            "Hello (asynchronous) world!"
        )

    def test_post_request(self):
        r = self.fetch(
            "/api/postit",
            method="POST",
            body=jd({
                "title": "Very Important Post-It Note",
                "body": "Equally important message",
                "index": 0
            })
        )
        self.assertEqual(r.code, 200)
        self.assertEqual(
            jl(r.body)["data"]["message"],
            "Very Important Post-It Note was posted."
        )

    def test_url_pattern_route(self):
        r = self.fetch(
            "/api/greeting/John/Smith"
        )
        self.assertEqual(r.code, 200)
        self.assertEqual(
            jl(r.body)["data"],
            "Greetings, John Smith!"
        )

    def test_write_error(self):
        # Test malformed output
        r = self.fetch(
            "/api/explodinghandler"
        )
        self.assertEqual(r.code, 500)
        self.assertEqual(
            jl(r.body)["status"],
            "error"
        )
        # Test malformed input
        r = self.fetch(
            "/api/explodinghandler",
            method="POST",
            body='"Yup", "this is going to end badly."]'
        )
        self.assertEqual(r.code, 400)
        self.assertEqual(
            jl(r.body)["status"],
            "fail"
        )

    def test_view_db_conn(self):
        r = self.fetch(
            "/views/someview",
            method="DELETE"
        )
        self.assertEqual(r.code, 500)
        self.assertTrue(
            "No database connection was provided." in r.body.decode("UTF-8")
        )

    def test_db_conn(self):
        r = self.fetch(
            "/api/dbtest",
            method="GET"
        )
        self.assertEqual(r.code, 200)
        print(r.body)
        self.assertEqual(
            jl(r.body)["status"],
            "success"
        )
        self.assertTrue(
            "Nothing to see here." in jl(r.body)["data"]
        )

########NEW FILE########
__FILENAME__ = test_tornado_json
import sys
import pytest

try:
    sys.path.append('.')
    from tornado_json import routes
    from tornado_json import schema
    from tornado_json import exceptions
    from tornado_json import jsend
    sys.path.append('demos/helloworld')
    sys.path.append('demos/rest_api')
    import helloworld
    import cars
except ImportError as e:
    print("Please run `py.test` from the root project directory")
    exit(1)


class SuccessException(Exception):

    """Great success!"""


class MockRequestHandler(object):

    class Request(object):
        body = "{\"I am a\": \"JSON object\"}"

    request = Request()

    def fail(message):
        raise exceptions.APIError(message)

    def success(self, message):
        raise SuccessException


class TestTornadoJSONBase(object):

    """Base class for all tornado_json test classes"""


class TestRoutes(TestTornadoJSONBase):

    """Tests the routes module"""

    def test_get_routes(self):
        """Tests routes.get_routes"""
        assert sorted(routes.get_routes(
            helloworld)) == sorted([
            ("/api/helloworld/?", helloworld.api.HelloWorldHandler),
            ("/api/asynchelloworld/?", helloworld.api.AsyncHelloWorld),
            ("/api/postit/?", helloworld.api.PostIt),
            ("/api/greeting/(?P<fname>[a-zA-Z0-9_]+)/"
             "(?P<lname>[a-zA-Z0-9_]+)/?$",
             helloworld.api.Greeting),
            ("/api/freewilled/?", helloworld.api.FreeWilledHandler)
        ])
        assert sorted(routes.get_routes(
            cars)) == sorted([
            ("/api/cars/?", cars.api.MakeListHandler),
            ("/api/cars/(?P<make>[a-zA-Z0-9_]+)/(?P<model>[a-zA-Z0-9_]+)/?$",
             cars.api.ModelHandler),
            ("/api/cars/(?P<make>[a-zA-Z0-9_]+)/(?P<model>[a-zA-Z0-9_]+)/"
             "(?P<year>[a-zA-Z0-9_]+)/?$", cars.api.YearHandler),
            ("/api/cars/(?P<make>[a-zA-Z0-9_]+)/?$", cars.api.MakeHandler),
        ])

    def test_gen_submodule_names(self):
        """Tests routes.gen_submodule_names"""
        assert list(routes.gen_submodule_names(helloworld)
                    ) == ['helloworld.api']

    def test_get_module_routes(self):
        """Tests routes.get_module_routes"""
        assert sorted(routes.get_module_routes(
            "cars.api")) == sorted([
            ("/api/cars/?", cars.api.MakeListHandler),
            ("/api/cars/(?P<make>[a-zA-Z0-9_]+)/(?P<model>[a-zA-Z0-9_]+)/?$",
             cars.api.ModelHandler),
            ("/api/cars/(?P<make>[a-zA-Z0-9_]+)/(?P<model>[a-zA-Z0-9_]+)/"
             "(?P<year>[a-zA-Z0-9_]+)/?$", cars.api.YearHandler),
            ("/api/cars/(?P<make>[a-zA-Z0-9_]+)/?$", cars.api.MakeHandler),
        ])


class TestUtils(TestTornadoJSONBase):

    """Tests the utils module"""

    def test_api_assert(self):
        """Test exceptions.api_assert"""
        with pytest.raises(exceptions.APIError):
            exceptions.api_assert(False, 400)

        exceptions.api_assert(True, 400)

    class TerribleHandler(MockRequestHandler):

        """This 'handler' is used in test_validate"""

        @schema.validate(output_schema={"type": "number"})
        def get(self):
            return "I am not the handler you are looking for."

        @schema.validate(output_schema={"type": "number"},
                         input_schema={"type": "number"})
        def post(self):
            return "Fission mailed."

    class ReasonableHandler(MockRequestHandler):

        """This 'handler' is used in test_validate"""

        @schema.validate(output_schema={"type": "number"})
        def get(self, fname, lname):
            return "I am the handler you are looking for, {} {}".format(
                fname, lname)

        @schema.validate(
            input_schema={
                "type": "object",
                "properties": {
                    "I am a": {"type": "string"},
                },
                "required": ["I am a"],
            },
            output_schema={
                "type": "string",
            }
        )
        def post(self):
            # Test that self.body is available as expected
            assert self.body == {"I am a": "JSON object"}
            return "Mail received."

    # DONE: Test validate functionally instead; pytest.raises does
    #   not seem to be catching errors being thrown after change
    #   to async compatible code.
    # The following test left here as antiquity.
    # def test_validate(self):
    #     """Tests the schema.validate decorator"""
    #     th = self.TerribleHandler()
    #     rh = self.ReasonableHandler()

    # Expect a TypeError to be raised because of invalid output
    #     with pytest.raises(TypeError):
    #         th.get("Duke", "Flywalker")

    # Expect a validation error because of invalid input
    #     with pytest.raises(ValidationError):
    #         th.post()

    # Both of these should succeed as the body matches the schema
    #     with pytest.raises(SuccessException):
    #         rh.get("J", "S")
    #     with pytest.raises(SuccessException):
    #         rh.post()


class TestJSendMixin(TestTornadoJSONBase):

    """Tests the JSendMixin module"""

    class MockJSendMixinRH(jsend.JSendMixin):

        """Mock handler for testing JSendMixin"""
        _buffer = None

        def write(self, data):
            self._buffer = data

    @classmethod
    @pytest.fixture(scope="class", autouse=True)
    def setup(cls):
        """Create mock handler instance"""
        cls.jsend_rh = cls.MockJSendMixinRH()

    def test_success(self):
        """Tests JSendMixin.success"""
        data = "Huzzah!"
        self.jsend_rh.success(data)
        assert self.jsend_rh._buffer == {'status': 'success', 'data': data}

    def test_fail(self):
        """Tests JSendMixin.fail"""
        data = "Aww!"
        self.jsend_rh.fail(data)
        assert self.jsend_rh._buffer == {'status': 'fail', 'data': data}

    def test_error(self):
        """Tests JSendMixin.error"""
        message = "Drats!"
        data = "I am the plural form of datum."
        code = 9001
        self.jsend_rh.error(message=message, data=data, code=code)
        assert self.jsend_rh._buffer == {
            'status': 'error', 'message': message, 'data': data, 'code': code}

########NEW FILE########
__FILENAME__ = api_doc_gen
import json
import inspect
from jsonschema import validate, ValidationError

from tornado_json.utils import is_method
from tornado_json.constants import HTTP_METHODS
from tornado_json.requesthandlers import APIHandler


def _validate_example(rh, method, example_type):
    """Validates example against schema

    :returns: Formatted example if example exists and validates, otherwise None
    :raises ValidationError: If example does not validate against the schema
    """
    example = getattr(method, example_type + "_example")
    schema = getattr(method, example_type + "_schema")

    if example is None:
        return None

    try:
        validate(example, schema)
    except ValidationError as e:
        raise ValidationError(
            "{}_example for {}.{} could not be validated.\n{}".format(
                example_type, rh.__name__, method.__name__, str(e)
            )
        )

    return json.dumps(example, indent=4)


def _get_rh_methods(rh):
    """Yield all HTTP methods in ``rh`` that are decorated
    with schema.validate"""
    for k, v in vars(rh).items():
        if all([
            k in HTTP_METHODS,
            is_method(v),
            hasattr(v, "input_schema")
        ]):
            yield (k, v)


def api_doc_gen(routes):
    """
    Generates GitHub Markdown formatted API documentation using
    provided schemas in RequestHandler methods and their docstrings.

    :type  routes: [(url, RequestHandler), ...]
    :param routes: List of routes (this is ideally all possible routes of the
        app)
    """
    documentation = []
    # Iterate over routes sorted by url
    for url, rh in sorted(routes, key=lambda a: a[0]):
        # Content-type is hard-coded but ideally should be retrieved;
        #  the hard part is, we don't know what it is without initializing
        #  an instance, so just leave as-is for now

        # BEGIN ROUTE_DOC #
        route_doc = """
# {0}

    Content-Type: application/json

{1}
""".format(
            # Escape markdown literals
            "".join(
                ['\\' + c if c in list("\\`*_{}[]()<>#+-.!:|") else c
                 for c in url]),
            "\n\n".join(
                [
"""## {0}
**Input Schema**
```json
{1}
```
{4}
**Output Schema**
```json
{2}
```
{5}

**Notes**

{3}

""".format(
            method_name.upper(),
            json.dumps(method.input_schema, indent=4),
            json.dumps(method.output_schema, indent=4),
            inspect.getdoc(method),
"""
**Input Example**
```json
{}
```
""".format(_validate_example(rh, method, "input")) if _validate_example(
            rh, method, "input") else "",
"""
**Output Example**
```json
{}
```
""".format(_validate_example(rh, method, "output")) if _validate_example(
            rh, method, "output") else "",
        ) for method_name, method in _get_rh_methods(rh)
                ]
            )
        )
        # END ROUTE_DOC #

        if issubclass(rh, APIHandler):
            documentation.append(route_doc)

    # Documentation is written to the root folder
    with open("API_Documentation.md", "w+") as f:
        f.write(
            "**This documentation is automatically generated.**\n\n" +
            "**Output schemas only represent `data` and not the full output; "
            "see output examples and the JSend specification.**\n" +
            "\n<br>\n<br>\n".join(documentation)
        )

########NEW FILE########
__FILENAME__ = application
import tornado.web

from tornado_json.api_doc_gen import api_doc_gen


class Application(tornado.web.Application):

    """Entry-point for the app

    - Generate API documentation using provided routes
    - Initialize the application

    :type  routes: [(url, RequestHandler), ...]
    :param routes: List of routes for the app
    :type  settings: dict
    :param settings: Settings for the app
    :param  db_conn: Database connection
    """

    def __init__(self, routes, settings, db_conn=None):
        # Generate API Documentation
        api_doc_gen(routes)

        # Unless gzip was specifically set to False in settings, enable it
        if "gzip" not in list(settings.keys()):
            settings["gzip"] = True

        tornado.web.Application.__init__(
            self,
            routes,
            **settings
        )

        self.db_conn = db_conn

########NEW FILE########
__FILENAME__ = constants
HTTP_METHODS = ["get", "put", "post", "patch", "delete", "head", "options"]

########NEW FILE########
__FILENAME__ = exceptions
from tornado.web import HTTPError


class APIError(HTTPError):

    """Equivalent to ``RequestHandler.HTTPError`` except for in name"""


def api_assert(condition, *args, **kwargs):
    """Assertion to fail with if not ``condition``

    Asserts that ``condition`` is ``True``, else raises an ``APIError``
    with the provided ``args`` and ``kwargs``

    :type  condition: bool
    """
    if not condition:
        raise APIError(*args, **kwargs)

########NEW FILE########
__FILENAME__ = jsend
"""Forked from: http://tornadogists.org/6612013/"""


class JSendMixin(object):

    """http://labs.omniti.com/labs/jsend

    JSend is a specification that lays down some rules for how JSON
    responses from web servers should be formatted.

    JSend focuses on application-level (as opposed to protocol- or
    transport-level) messaging which makes it ideal for use in
    REST-style applications and APIs.
    """

    def success(self, data):
        """When an API call is successful, the JSend object is used as a simple
        envelope for the results, using the data key.

        :type  data: A JSON-serializable object
        :param data: Acts as the wrapper for any data returned by the API
            call. If the call returns no data, data should be set to null.
        """
        self.write({'status': 'success', 'data': data})

    def fail(self, data):
        """There was a problem with the data submitted, or some pre-condition
        of the API call wasn't satisfied.

        :type  data: A JSON-serializable object
        :param data: Provides the wrapper for the details of why the request
            failed. If the reasons for failure correspond to POST values,
            the response object's keys SHOULD correspond to those POST values.
        """
        self.write({'status': 'fail', 'data': data})

    def error(self, message, data=None, code=None):
        """An error occurred in processing the request, i.e. an exception was
        thrown.

        :type  data: A JSON-serializable object
        :param data: A generic container for any other information about the
            error, i.e. the conditions that caused the error,
            stack traces, etc.
        :type  message: A JSON-serializable object
        :param message: A meaningful, end-user-readable (or at the least
            log-worthy) message, explaining what went wrong
        :type  code: int
        :param code: A numeric code corresponding to the error, if applicable
        """
        result = {'status': 'error', 'message': message}
        if data:
            result['data'] = data
        if code:
            result['code'] = code
        self.write(result)

########NEW FILE########
__FILENAME__ = requesthandlers
import logging

from tornado.web import RequestHandler
from jsonschema import ValidationError

from tornado_json.jsend import JSendMixin
from tornado_json.exceptions import APIError


class BaseHandler(RequestHandler):

    """BaseHandler for all other RequestHandlers"""

    __url_names__ = ["__self__"]
    __urls__ = []

    @property
    def db_conn(self):
        """Returns database connection abstraction

        If no database connection is available, raises an AttributeError
        """
        db_conn = self.application.db_conn
        if not db_conn:
            raise AttributeError("No database connection was provided.")
        return db_conn


class ViewHandler(BaseHandler):

    """Handler for views"""

    def initialize(self):
        """
        - Set Content-type for HTML
        """
        self.set_header("Content-Type", "text/html")


class APIHandler(BaseHandler, JSendMixin):

    """RequestHandler for API calls

    - Sets header as ``application/json``
    - Provides custom write_error that writes error back as JSON \
    rather than as the standard HTML template
    """

    def initialize(self):
        """
        - Set Content-type for JSON
        """
        self.set_header("Content-Type", "application/json")

    def write_error(self, status_code, **kwargs):
        """Override of RequestHandler.write_error

        Calls ``error()`` or ``fail()`` from JSendMixin depending on which
        exception was raised with provided reason and status code.

        :type  status_code: int
        :param status_code: HTTP status code
        """
        def get_exc_message(exception):
            return exception.log_message if \
                hasattr(exception, "log_message") else str(exception)

        self.clear()
        self.set_status(status_code)

        # Any APIError exceptions raised will result in a JSend fail written
        # back with the log_message as data. Hence, log_message should NEVER
        # expose internals. Since log_message is proprietary to HTTPError
        # class exceptions, all exceptions without it will return their
        # __str__ representation.
        # All other exceptions result in a JSend error being written back,
        # with log_message only written if debug mode is enabled
        exception = kwargs["exc_info"][1]
        if any(isinstance(exception, c) for c in [APIError, ValidationError]):
            # ValidationError is always due to a malformed request
            if isinstance(exception, ValidationError):
                self.set_status(400)
            self.fail(get_exc_message(exception))
        else:
            self.error(
                message=self._reason,
                data=get_exc_message(exception) if self.settings.get("debug")
                else None,
                code=status_code
            )

########NEW FILE########
__FILENAME__ = routes
import pyclbr
import pkgutil
import importlib
import inspect
from itertools import chain
from functools import reduce


from tornado_json.constants import HTTP_METHODS
from tornado_json.utils import extract_method, is_method, is_handler_subclass


def get_routes(package):
    """
    This will walk ``package`` and generates routes from any and all
    ``APIHandler`` and ``ViewHandler`` subclasses it finds. If you need to
    customize or remove any routes, you can do so to the list of
    returned routes that this generates.

    :type  package: package
    :param package: The package containing RequestHandlers to generate
        routes from
    :returns: List of routes for all submodules of ``package``
    :rtype: [(url, RequestHandler), ... ]
    """
    return list(chain(*[get_module_routes(modname) for modname in
                        gen_submodule_names(package)]))


def gen_submodule_names(package):
    """Walk package and yield names of all submodules

    :type  package: package
    :param package: The package to get submodule names of
    :returns: Iterator that yields names of all submodules of ``package``
    :rtype: Iterator that yields ``str``
    """
    for importer, modname, ispkg in pkgutil.walk_packages(
        path=package.__path__,
        prefix=package.__name__ + '.',
            onerror=lambda x: None):
        yield modname


def get_module_routes(module_name, custom_routes=None, exclusions=None):
    """Create and return routes for module_name

    Routes are (url, RequestHandler) tuples

    :returns: list of routes for ``module_name`` with respect to ``exclusions``
        and ``custom_routes``. Returned routes are with URLs formatted such
        that they are forward-slash-separated by module/class level
        and end with the lowercase name of the RequestHandler (it will also
        remove 'handler' from the end of the name of the handler).
        For example, a requesthandler with the name
        ``helloworld.api.HelloWorldHandler`` would be assigned the url
        ``/api/helloworld``.
        Additionally, if a method has extra arguments aside from ``self`` in
        its signature, routes with URL patterns will be generated to
        match ``r"(?P<{}>[a-zA-Z0-9_]+)".format(argname)`` for each
        argument. The aforementioned regex will match ONLY values
        with alphanumeric+underscore characters.
    :rtype: [(url, RequestHandler), ... ]
    :type  module_name: str
    :param module_name: Name of the module to get routes for
    :type  custom_routes: [(str, RequestHandler), ... ]
    :param custom_routes: List of routes that have custom URLs and therefore
        should be automagically generated
    :type  exclusions: [str, str, ...]
    :param exclusions: List of RequestHandler names that routes should not be
        generated for
    """
    def has_method(module, cls_name, method_name):
        return all([
            method_name in vars(getattr(module, cls_name)),
            is_method(reduce(getattr, [module, cls_name, method_name]))
        ])

    def yield_args(module, cls_name, method_name):
        """Get signature of ``module.cls_name.method_name``

        Confession: This function doesn't actually ``yield`` the arguments,
            just returns a list. Trust me, it's better that way.

        :returns: List of arg names from method_name except ``self``
        :rtype: list
        """
        # method = getattr(getattr(module, cls_name), method_name)
        wrapped_method = reduce(getattr, [module, cls_name, method_name])
        method = extract_method(wrapped_method)
        return [a for a in inspect.getargspec(method).args if a not in ["self"]]

    def generate_auto_route(module, module_name, cls_name, method_name, url_name):
        """Generate URL for auto_route

        :rtype: str
        :returns: Constructed URL based on given arguments
        """
        def get_handler_name():
            """Get handler identifier for URL

            For the special case where ``url_name`` is
            ``__self__``, the handler is named a lowercase
            value of its own name with 'handler' removed
            from the ending if give; otherwise, we
            simply use the provided ``url_name``
            """
            if url_name == "__self__":
                if cls_name.lower().endswith('handler'):
                    return cls_name.lower().replace('handler', '', 1)
                return cls_name.lower()
            else:
                return url_name

        def get_arg_route():
            """Get remainder of URL determined by method argspec

            :returns: Remainder of URL which matches `\w+` regex
                with groups named by the method's argument spec.
                If there are no arguments given, returns ``""``.
            :rtype: str
            """
            if yield_args(module, cls_name, method_name):
                return "/{}/?$".format("/".join(
                    ["(?P<{}>[a-zA-Z0-9_]+)".format(argname) for argname
                     in yield_args(module, cls_name, method_name)]
                ))
            return r"/?"

        return "/{}/{}{}".format(
            "/".join(module_name.split(".")[1:]),
            get_handler_name(),
            get_arg_route()
        )

    if not custom_routes:
        custom_routes = []
    if not exclusions:
        exclusions = []

    # Import module so we can get its request handlers
    module = importlib.import_module(module_name)

    # Generate list of RequestHandler names in custom_routes
    custom_routes_s = [c.__name__ for r, c in custom_routes]

    # rhs is a dict of {classname: pyclbr.Class} key, value pairs
    rhs = pyclbr.readmodule(module_name)

    # You better believe this is a list comprehension
    auto_routes = list(chain(*[
        list(set(chain(*[
            # Generate a route for each "name" specified in the
            #   __url_names__ attribute of the handler
            [
                # URL, requesthandler tuple
                (
                    generate_auto_route(
                        module, module_name, cls_name, method_name, url_name
                    ),
                    getattr(module, cls_name)
                ) for url_name in getattr(module, cls_name).__url_names__
                # Add routes for each custom URL specified in the
                #   __urls__ attribute of the handler
            ] + [
                (
                    url,
                    getattr(module, cls_name)
                ) for url in getattr(module, cls_name).__urls__
            ]
            # We create a route for each HTTP method in the handler
            #   so that we catch all possible routes if different
            #   HTTP methods have different argspecs and are expecting
            #   to catch different routes. Any duplicate routes
            #   are removed from the set() comparison.
            for method_name in HTTP_METHODS if has_method(
                module, cls_name, method_name)
        ])))
        # foreach classname, pyclbr.Class in rhs
        for cls_name, cls in rhs.items()
        # Only add the pair to auto_routes if:
        #    * the superclass is in the list of supers we want
        #    * the requesthandler isn't already paired in custom_routes
        #    * the requesthandler isn't manually excluded
        if is_handler_subclass(cls)
        and cls_name not in (custom_routes_s + exclusions)
    ]))

    routes = auto_routes + custom_routes
    return routes

########NEW FILE########
__FILENAME__ = schema
import json
import jsonschema

from functools import wraps
from tornado import gen
from tornado.concurrent import Future

from tornado_json.utils import container


def validate(input_schema=None, output_schema=None,
             input_example=None, output_example=None):
    @container
    def _validate(rh_method):
        """Decorator for RequestHandler schema validation

        This decorator:

            - Validates request body against input schema of the method
            - Calls the ``rh_method`` and gets output from it
            - Validates output against output schema of the method
            - Calls ``JSendMixin.success`` to write the validated output

        :type  rh_method: function
        :param rh_method: The RequestHandler method to be decorated
        :returns: The decorated method
        :raises ValidationError: If input is invalid as per the schema
            or malformed
        :raises TypeError: If the output is invalid as per the schema
            or malformed
        """
        @wraps(rh_method)
        @gen.coroutine
        def _wrapper(self, *args, **kwargs):
            # In case the specified input_schema is ``None``, we
            #   don't json.loads the input, but just set it to ``None``
            #   instead.
            if input_schema is not None:
                # Attempt to json.loads the input
                try:
                    # TODO: Assuming UTF-8 encoding for all requests,
                    #   find a nice way of determining this from charset
                    #   in headers if provided
                    encoding = "UTF-8"
                    input_ = json.loads(self.request.body.decode(encoding))
                except ValueError as e:
                    raise jsonschema.ValidationError(
                        "Input is malformed; could not decode JSON object."
                    )
                # Validate the received input
                jsonschema.validate(
                    input_,
                    input_schema
                )
            else:
                input_ = None

            # A json.loads'd version of self.request["body"] is now available
            #   as self.body
            setattr(self, "body", input_)
            # Call the requesthandler method
            output = rh_method(self, *args, **kwargs)
            # If the rh_method returned a Future a la `raise Return(value)`
            #   we grab the output.
            if isinstance(output, Future):
                output = yield output

            if output_schema is not None:
                # We wrap output in an object before validating in case
                #  output is a string (and ergo not a validatable JSON object)
                try:
                    jsonschema.validate(
                        {"result": output},
                        {
                            "type": "object",
                            "properties": {
                                "result": output_schema
                            },
                            "required": ["result"]
                        }
                    )
                except jsonschema.ValidationError as e:
                    # We essentially re-raise this as a TypeError because
                    #  we don't want this error data passed back to the client
                    #  because it's a fault on our end. The client should
                    #  only see a 500 - Internal Server Error.
                    raise TypeError(str(e))

            # If no ValidationError has been raised up until here, we write
            #  back output
            self.success(output)

        setattr(_wrapper, "input_schema", input_schema)
        setattr(_wrapper, "output_schema", output_schema)
        setattr(_wrapper, "input_example", input_example)
        setattr(_wrapper, "output_example", output_example)

        return _wrapper
    return _validate

########NEW FILE########
__FILENAME__ = utils
import types
import pyclbr

from functools import wraps


def container(dec):
    """Meta-decorator (for decorating decorators)

    Keeps around original decorated function as a property ``orig_func``

    :param dec: Decorator to decorate
    :type  dec: function
    :returns: Decorated decorator
    """
    # Credits: http://stackoverflow.com/a/1167248/1798683
    @wraps(dec)
    def meta_decorator(f):
        decorator = dec(f)
        decorator.orig_func = f
        return decorator
    return meta_decorator


def extract_method(wrapped_method):
    """Gets original method if wrapped_method was decorated

    :rtype: any([types.FunctionType, types.MethodType])
    """
    # If method was decorated with validate, the original method
    #   is available as orig_func thanks to our container decorator
    return wrapped_method.orig_func if \
        hasattr(wrapped_method, "orig_func") else wrapped_method


def is_method(method):
    method = extract_method(method)
    # Can be either a method or a function
    return type(method) in [types.MethodType, types.FunctionType]


def is_handler_subclass(cls, classnames=("ViewHandler", "APIHandler")):
    """Determines if ``cls`` is indeed a subclass of ``classnames``

    This function should only be used with ``cls`` from ``pyclbr.readmodule``
    """
    if isinstance(cls, pyclbr.Class):
        return is_handler_subclass(cls.super)
    elif isinstance(cls, list):
        return any(is_handler_subclass(s) for s in cls)
    elif isinstance(cls, str):
        return cls in classnames
    else:
        raise TypeError(
            "Unexpected pyclbr.Class.super type `{}` for class `{}`".format(
                type(cls),
                cls
            )
        )

########NEW FILE########
