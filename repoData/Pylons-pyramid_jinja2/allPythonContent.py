__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# pyramid_jinja2 documentation build configuration file
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

# If your extensions are in another directory, add it here. If the
# directory is relative to the documentation root, use os.path.abspath to
# make it absolute, like shown here.
#sys.path.append(os.path.abspath('some/directory'))

import sys
import os

# Add and use Pylons theme
if 'sphinx-build' in ' '.join(sys.argv): # protect against dumb importers
    from subprocess import call, Popen, PIPE

    p = Popen('which git', shell=True, stdout=PIPE)
    git = p.stdout.read().strip()
    cwd = os.getcwd()
    _themes = os.path.join(cwd, '_themes')

    if not os.path.isdir(_themes):
        call([git, 'clone', 'git://github.com/Pylons/pylons_sphinx_theme.git',
                '_themes'])
    else:
        os.chdir(_themes)
        call([git, 'checkout', 'master'])
        call([git, 'pull'])
        os.chdir(cwd)

    sys.path.append(os.path.abspath('_themes'))

    parent = os.path.dirname(os.path.dirname(__file__))
    sys.path.append(os.path.abspath(parent))
    wd = os.getcwd()
    #os.chdir(parent)
    #os.system('%s setup.py test -q' % sys.executable)
    os.chdir(wd)

    for item in os.listdir(parent):
        if item.endswith('.egg'):
            sys.path.append(os.path.join(parent, item))

# General configuration
# ---------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.intersphinx']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['.templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

# General substitutions.
project = 'pyramid_jinja2'
copyright = '2011, Agendaless Consulting <chrism@plope.com>'

# The default replacements for |version| and |release|, also used in various
# other places throughout the built documents.
#
# The short X.Y version.
import pkg_resources
version = pkg_resources.get_distribution(project).version
# The full version, including alpha/beta/rc tags.
release = version

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

exclude_patterns = ['_themes/README.rst',]

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


html_theme_options = {
    'github_url': 'https://github.com/Pylons/pyramid_jinja2'
}


# The style sheet to use for HTML and HTML Help pages. A file of that name
# must exist either in Sphinx' static/ path, or in one of the custom paths
# given in html_static_path.
# html_style = 'repoze.css'

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
#html_static_path = ['_static']

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
htmlhelp_basename = 'atemplatedoc'

# for cross referencing documentations
intersphinx_mapping = {
    'jinja2': ('http://jinja.pocoo.org/docs/', None),
    'pyramid': ('http://docs.pylonsproject.org/projects/pyramid/en/latest/', None),
}


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
  ('index', 'pyramid_jinja2.tex', 'pyramid_jinja2 Documentation',
   'Repoze Developers', 'manual'),
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
__FILENAME__ = compat
import sys
import types

# True if we are running on Python 3.
PY3 = sys.version_info[0] == 3

if PY3: # pragma: no cover
    string_types = str,
    integer_types = int,
    class_types = type,
    text_type = str
    binary_type = bytes
    long = int
else: # pragma: no cover
    string_types = basestring,
    integer_types = (int, long)
    class_types = (type, types.ClassType)
    text_type = unicode
    binary_type = str

# TODO check if errors is ever used

def text_(s, encoding='latin-1', errors='strict'): # pragma: no cover
    if isinstance(s, binary_type):
        return s.decode(encoding, errors)
    return s # pragma: no cover

def bytes_(s, encoding='latin-1', errors='strict'): # pragma: no cover
    if isinstance(s, text_type):
        return s.encode(encoding, errors)
    return s

if PY3: # pragma: no cover
    def reraise(exc_info):
        etype, exc, tb = exc_info
        if exc.__traceback__ is not tb:
            raise exc.with_traceback(tb)
        raise exc
else: # pragma: no cover
    exec("def reraise(exc): raise exc[0], exc[1], exc[2]")

if PY3: # pragma: no cover
    from io import StringIO
    from io import BytesIO
else: # pragma: no cover
    from StringIO import StringIO
    BytesIO = StringIO

########NEW FILE########
__FILENAME__ = tests
import unittest
import pyramid.testing


class DemoTests(unittest.TestCase):
    def test_root_view(self):
        from pyramid_jinja2.demo import root_view
        m = pyramid.testing.DummyRequest()
        root_view(m)
        self.assertEqual(m.locale_name, 'fr')

    def test_app(self):
        from pyramid_jinja2.demo import app
        webapp = app({})
        self.assertTrue(callable(webapp))

    def test_main(self):
        from pyramid_jinja2.demo import Mainer

        class MyMainer(Mainer):
            def serve_forever(self):
                self.serving = True

            def make_server(self, *args, **kwargs):
                return Mock(args=args,
                            kwargs=kwargs,
                            serve_forever=self.serve_forever)

        mainer = MyMainer()
        mainer.main()
        self.assertTrue(getattr(mainer, 'serving', False))

class Mock(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

########NEW FILE########
__FILENAME__ = filters
from pyramid.url import resource_url, route_url, static_url
from pyramid.url import route_path, static_path
from pyramid.threadlocal import get_current_request
from jinja2 import contextfilter


__all__ = [
    'model_url_filter',
    'route_url_filter',
    'route_path_filter',
    'static_url_filter',
    'static_path_filter',
]


@contextfilter
def model_url_filter(ctx, model, *elements, **kw):
    """A filter from ``model`` to a string representing the absolute URL.
    This filter calls :py:func:`pyramid.url.resource_url`.
    """
    request = get_current_request()
    return resource_url(model, request, *elements, **kw)


@contextfilter
def route_url_filter(ctx, route_name, *elements, **kw):
    """A filter from ``route_name`` to a string representing the absolute URL.
    This filter calls :py:func:`pyramid.url.route_url`.
    """
    request = get_current_request()
    return route_url(route_name, request, *elements, **kw)


@contextfilter
def route_path_filter(ctx, route_name, *elements, **kw):
    """A filter from ``route_name`` to a string representing the relative URL.
    This filter calls :py:func:`pyramid.url.route_path`.
    """
    request = get_current_request()
    return route_path(route_name, request, *elements, **kw)


@contextfilter
def static_url_filter(ctx, path, **kw):
    """A filter from ``path`` to a string representing the absolute URL.
    This filter calls :py:func:`pyramid.url.static_url`.
    """
    request = get_current_request()
    return static_url(path, request, **kw)


@contextfilter
def static_path_filter(ctx, path, **kw):
    """A filter from ``path`` to a string representing the relative URL.
    This filter calls :py:func:`pyramid.url.static_path`.
    """
    request = get_current_request()
    return static_path(path, request, **kw)

########NEW FILE########
__FILENAME__ = i18n
from pyramid import i18n
from pyramid.threadlocal import get_current_request


class GetTextWrapper(object):

    def __init__(self, domain):
        self.domain = domain

    @property
    def localizer(self):
        return i18n.get_localizer(get_current_request())

    def gettext(self, message):
        return self.localizer.translate(message,
                                        domain=self.domain)

    def ngettext(self, singular, plural, n):
        return self.localizer.pluralize(singular, plural, n,
                                        domain=self.domain)

########NEW FILE########
__FILENAME__ = models
class MyModel(object):
    pass

root = MyModel()


def get_root(request):
    return root

########NEW FILE########
__FILENAME__ = settings
from jinja2 import (
    BytecodeCache,
    DebugUndefined,
    FileSystemBytecodeCache,
    StrictUndefined,
    Undefined,
)

from pyramid.asset import abspath_from_asset_spec
from pyramid.settings import asbool

from .compat import string_types
from .i18n import GetTextWrapper


_JINJA2_ENVIRONMENT_DEFAULTS = {
    'autoescape': True,
}


def splitlines(s):
    return filter(None, [x.strip() for x in s.splitlines()])


def parse_named_assetspecs(input, maybe_dotted):
    """
    Parse a dictionary of asset specs.
    Parses config values from .ini file and returns a dictionary with
    imported objects
    """
    # input must be a string or dict
    result = {}
    if isinstance(input, string_types):
        for f in splitlines(input):
            name, impl = f.split('=', 1)
            result[name.strip()] = maybe_dotted(impl.strip())
    else:
        for name, impl in input.items():
            result[name] = maybe_dotted(impl)
    return result


def parse_multiline(extensions):
    if isinstance(extensions, string_types):
        extensions = list(splitlines(extensions))
    return extensions


def parse_undefined(undefined):
    if undefined == 'strict':
        return StrictUndefined
    if undefined == 'debug':
        return DebugUndefined
    return Undefined


def parse_loader_options_from_settings(settings,
                                       prefix,
                                       maybe_dotted,
                                       package):
    """ Parse options for use with the SmartAssetSpecLoader."""
    package = package or '__main__'

    def sget(name, default=None):
        return settings.get(prefix + name, default)

    debug = sget('debug_templates', None)
    if debug is None:
        # bw-compat prior to checking debug_templates for specific prefix
        debug = settings.get('debug_templates', None)
    debug = asbool(debug)

    input_encoding = sget('input_encoding', 'utf-8')

    # get jinja2 directories
    directories = parse_multiline(sget('directories') or '')
    directories = [abspath_from_asset_spec(d, package) for d in directories]

    return dict(
        debug=debug,
        encoding=input_encoding,
        searchpath=directories,
    )


def parse_env_options_from_settings(settings,
                                    prefix,
                                    maybe_dotted,
                                    package,
                                    defaults=None,
                                    ):
    """ Parse options for use with the Jinja2 Environment."""
    def sget(name, default=None):
        return settings.get(prefix + name, default)

    if defaults is None:
        defaults = _JINJA2_ENVIRONMENT_DEFAULTS

    opts = {}

    reload_templates = sget('reload_templates')
    if reload_templates is None:
        reload_templates = settings.get('pyramid.reload_templates')
    opts['auto_reload'] = asbool(reload_templates)

    # set string settings
    for key_name in ('block_start_string', 'block_end_string',
                     'variable_start_string', 'variable_end_string',
                     'comment_start_string', 'comment_end_string',
                     'line_statement_prefix', 'line_comment_prefix',
                     'newline_sequence'):
        value = sget(key_name, defaults.get(key_name))
        if value is not None:
            opts[key_name] = value

    # boolean settings
    for key_name in ('autoescape', 'trim_blocks', 'optimized'):
        value = sget(key_name, defaults.get(key_name))
        if value is not None:
            opts[key_name] = asbool(value)

    # integer settings
    for key_name in ('cache_size',):
        value = sget(key_name, defaults.get(key_name))
        if value is not None:
            opts[key_name] = int(value)

    opts['undefined'] = parse_undefined(sget('undefined', ''))

    # get supplementary jinja2 settings
    domain = sget('i18n.domain', package and package.__name__ or 'messages')
    opts['gettext'] = GetTextWrapper(domain=domain)

    # get jinja2 extensions
    extensions = parse_multiline(sget('extensions', ''))
    if 'jinja2.ext.i18n' not in extensions:
        extensions.append('jinja2.ext.i18n')
    opts['extensions'] = extensions

    # get jinja2 bytecode caching settings and set up bytecaching
    bytecode_caching = sget('bytecode_caching', False)
    if isinstance(bytecode_caching, BytecodeCache):
        opts['bytecode_cache'] = bytecode_caching
    elif asbool(bytecode_caching):
        bytecode_caching_directory = sget('bytecode_caching_directory', None)
        opts['bytecode_cache'] = FileSystemBytecodeCache(
            bytecode_caching_directory)

    # should newstyle gettext calls be enabled?
    opts['newstyle'] = asbool(sget('newstyle', False))

    # add custom jinja2 filters
    opts['filters'] = parse_named_assetspecs(sget('filters', ''), maybe_dotted)

    # add custom jinja2 tests
    opts['tests'] = parse_named_assetspecs(sget('tests', ''), maybe_dotted)

    # add custom jinja2 functions
    opts['globals'] = parse_named_assetspecs(sget('globals', ''), maybe_dotted)

    return opts

########NEW FILE########
__FILENAME__ = base
from pyramid import testing


class Base(object):
    def setUp(self):
        self.request = testing.DummyRequest()
        self.config = testing.setUp(request=self.request)
        self.request.registry = self.config.registry
        import os
        here = os.path.abspath(os.path.dirname(__file__))
        self.templates_dir = os.path.join(here, 'templates')

    def tearDown(self):
        testing.tearDown()
        del self.config


class Mock(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

########NEW FILE########
__FILENAME__ = extensions
from jinja2 import nodes
from jinja2.ext import Extension

class TestExtension(Extension):
    tags = set(['test_ext'])
    def parse(self, parser): return nodes.Const("This is test extension")

########NEW FILE########
__FILENAME__ = test_ext
import unittest
from .base import Base


class TestExtensions(Base, unittest.TestCase):

    def test_custom_extension(self):
        from pyramid_jinja2 import create_environment_from_options
        from pyramid_jinja2.settings import parse_env_options_from_settings

        options = {
            'extensions': 'pyramid_jinja2.tests.extensions.TestExtension',
        }
        settings = parse_env_options_from_settings(options, '', None, None)
        env = create_environment_from_options(settings, {})
        ext = env.extensions[
            'pyramid_jinja2.tests.extensions.TestExtension']
        import pyramid_jinja2.tests.extensions
        self.assertEqual(ext.__class__,
                         pyramid_jinja2.tests.extensions.TestExtension)

    def test_i18n(self):
        from pyramid_jinja2 import create_environment_from_options
        from pyramid_jinja2.settings import parse_env_options_from_settings

        settings = parse_env_options_from_settings({}, '', None, None)
        env = create_environment_from_options(settings, {})

        self.assertTrue(hasattr(env, 'install_gettext_translations'))

        self.config.add_translation_dirs('pyramid_jinja2.tests:locale/')
        self.request.locale_name = 'en'
        template = env.get_template(
            'pyramid_jinja2.tests:templates/i18n.jinja2')
        self.assertEqual(template.render(),
                         'some untranslated text here\nyay it worked!')


class GetTextWrapperTests(unittest.TestCase):

    def test_it(self):
        from pyramid_jinja2.i18n import GetTextWrapper

        class MyGetTextWrapper(GetTextWrapper):
            class localizer:
                @staticmethod
                def translate(s, domain):
                    return s

                @staticmethod
                def pluralize(s1, s2, n, domain):
                    return s2

            def __init__(self):
                GetTextWrapper.__init__(self, 'messages')

        self.assertEqual(MyGetTextWrapper().gettext('foo'), 'foo')
        self.assertEqual(MyGetTextWrapper().ngettext('foo', 'foos', 3), 'foos')

########NEW FILE########
__FILENAME__ = test_filters
import unittest
from pyramid import testing

class DummyRoot(object):
    __name__ = __parent__ = None

class DummyModel(object):
    __name__ = 'dummy'
    __parent__ = DummyRoot()

class Base(object):
    def setUp(self):
        self.request = testing.DummyRequest()
        self.config = testing.setUp(request=self.request)
        self.request.registry = self.config.registry

        from pyramid_jinja2 import Environment
        self.environment = Environment()

        self._addFilters()

    def tearDown(self):
        testing.tearDown()

    def _addFilters(self): pass

    def _callFUT(self, context, tmpl):
        tmpl = self.environment.from_string(tmpl)
        return tmpl.render(**context)

class Test_model_url_filter(Base, unittest.TestCase):

    def _addFilters(self):
        from pyramid_jinja2.filters import model_url_filter
        self.environment.filters['model_url'] = model_url_filter

    def test_filter(self):
        model = DummyModel()
        rendered = self._callFUT({'model': model}, '{{model|model_url}}')
        self.assertEqual(rendered, 'http://example.com/dummy/')

    def test_filter_with_elements(self):
        model = DummyModel()
        rendered = self._callFUT({'model': model}, "{{model|model_url('edit')}}")
        self.assertEqual(rendered, 'http://example.com/dummy/edit')

class Test_route_url_filter(Base, unittest.TestCase):
    def _addFilters(self):
        from pyramid_jinja2.filters import route_url_filter
        self.environment.filters['route_url'] = route_url_filter

        self.config.add_route('dummy_route1', '/dummy/')
        self.config.add_route('dummy_route2', '/dummy/:name/')

    def test_filter(self):
        rendered = self._callFUT({}, "{{'dummy_route1' | route_url }}")
        self.assertEqual(rendered, 'http://example.com/dummy/')

    def test_filter_with_arguments(self):
        rendered = self._callFUT({}, "{{'dummy_route2' | route_url('x', name='test') }}")
        self.assertEqual(rendered, 'http://example.com/dummy/test/x')

class Test_route_path_filter(Base, unittest.TestCase):
    def _addFilters(self):
        from pyramid_jinja2.filters import route_path_filter
        self.environment.filters['route_path'] = route_path_filter

        self.config.add_route('dummy_route1', '/dummy/')
        self.config.add_route('dummy_route2', '/dummy/:name/')

    def test_filter(self):
        rendered = self._callFUT({}, "{{'dummy_route1' | route_path }}")
        self.assertEqual(rendered, '/dummy/')

    def test_filter_with_arguments(self):
        rendered = self._callFUT({}, "{{'dummy_route2' | route_path('x', name='test') }}")
        self.assertEqual(rendered, '/dummy/test/x')

class Test_static_url_filter(Base, unittest.TestCase):
    def _addFilters(self):
        from pyramid_jinja2.filters import static_url_filter
        self.environment.filters['static_url'] = static_url_filter

        self.config.add_static_view('myfiles', 'dummy1:static')
        self.config.add_static_view('otherfiles/{owner}', 'dummy2:files')

    def test_filter(self):
        rendered = self._callFUT({}, "{{'dummy1:static/the/quick/brown/fox.svg' | static_url }}")
        self.assertEqual(rendered, 'http://example.com/myfiles/the/quick/brown/fox.svg')

    def test_filter_with_arguments(self):
        rendered = self._callFUT({}, "{{'dummy2:files/report.txt' | static_url(owner='foo') }}")
        self.assertEqual(rendered, 'http://example.com/otherfiles/foo/report.txt')

class Test_static_path_filter(Base, unittest.TestCase):
    def _addFilters(self):
        from pyramid_jinja2.filters import static_path_filter
        self.environment.filters['static_path'] = static_path_filter

        self.config.add_static_view('myfiles', 'dummy1:static')
        self.config.add_static_view('otherfiles/{owner}', 'dummy2:files')

    def test_filter(self):
        rendered = self._callFUT({}, "{{'dummy1:static/the/quick/brown/fox.svg' | static_path }}")
        self.assertEqual(rendered, '/myfiles/the/quick/brown/fox.svg')

    def test_filter_with_arguments(self):
        rendered = self._callFUT({}, "{{'dummy2:files/report.txt' | static_path(owner='foo') }}")
        self.assertEqual(rendered, '/otherfiles/foo/report.txt')

class Test_filters_not_caching(Base, unittest.TestCase):
    def _addFilters(self):
        from pyramid_jinja2.filters import route_url_filter
        self.environment.filters['route_url'] = route_url_filter

        self.config.add_route('dummy_route1', '/dummy/')
        self.config.add_route('dummy_route2', '/dummy/:name/')

    def test_filter(self):
        self.request.application_url = 'http://example.com'
        self.request.host = 'example.com:80'
        rendered = self._callFUT({}, "{{'dummy_route1' | route_url }}")
        self.assertEqual(rendered, 'http://example.com/dummy/')

        self.request.application_url = 'http://sub.example.com'
        self.request.host = 'sub.example.com:80'
        rendered = self._callFUT({}, "{{'dummy_route1' | route_url }}")
        self.assertEqual(rendered, 'http://sub.example.com/dummy/')

    def test_filter_with_arguments(self):
        self.request.application_url = 'http://example.com'
        self.request.host = 'example.com:80'
        rendered = self._callFUT({}, "{{'dummy_route2' | route_url('x', name='test') }}")
        self.assertEqual(rendered, 'http://example.com/dummy/test/x')

        self.request.application_url = 'http://sub.example.com'
        self.request.host = 'sub.example.com:80'
        rendered = self._callFUT({}, "{{'dummy_route2' | route_url('x', name='test') }}")
        self.assertEqual(rendered, 'http://sub.example.com/dummy/test/x')



########NEW FILE########
__FILENAME__ = test_it
## come on python gimme some of that sweet, sweet -*- coding: utf-8 -*-

import unittest
from pyramid import testing

from pyramid_jinja2.compat import (
    text_type,
    text_,
    bytes_,
    StringIO,
)
from .base import Base, Mock


def dummy_filter(value): return 'hoge'


class Test_renderer_factory(Base, unittest.TestCase):

    def setUp(self):
        Base.setUp(self)
        import warnings
        self.warnings = warnings.catch_warnings()
        self.warnings.__enter__()
        warnings.simplefilter('ignore', DeprecationWarning)

    def tearDown(self):
        self.warnings.__exit__(None, None, None)
        Base.tearDown(self)

    def _callFUT(self, info):
        from pyramid_jinja2 import renderer_factory
        return renderer_factory(info)

    def test_no_directories(self):
        from jinja2.exceptions import TemplateNotFound
        info = DummyRendererInfo({
            'name': 'helloworld.jinja2',
            'package': None,
            'registry': self.config.registry,
            })
        renderer = self._callFUT(info)
        self.assertRaises(
            TemplateNotFound, lambda: renderer({}, {'system': 1}))

    def test_no_environment(self):
        from pyramid_jinja2 import IJinja2Environment
        self.config.registry.settings.update(
            {'jinja2.directories': self.templates_dir})
        info = DummyRendererInfo({
            'name': 'helloworld.jinja2',
            'package': None,
            'registry': self.config.registry,
            })
        renderer = self._callFUT(info)
        environ = self.config.registry.getUtility(IJinja2Environment)
        self.assertEqual(environ.loader.searchpath, [self.templates_dir])
        self.assertTrue(renderer.template_loader is not None)

    def test_composite_directories_path(self):
        from pyramid_jinja2 import IJinja2Environment
        twice = self.templates_dir + '\n' + self.templates_dir
        self.config.registry.settings['jinja2.directories'] = twice
        info = DummyRendererInfo({
            'name': 'helloworld.jinja2',
            'package': None,
            'registry': self.config.registry,
            })
        self._callFUT(info)
        environ = self.config.registry.getUtility(IJinja2Environment)
        self.assertEqual(environ.loader.searchpath, [self.templates_dir] * 2)

    def test_with_environ(self):
        from pyramid_jinja2 import IJinja2Environment
        environ = DummyEnviron()
        self.config.registry.registerUtility(environ, IJinja2Environment)
        info = DummyRendererInfo({
            'name': 'helloworld.jinja2',
            'package': None,
            'registry': self.config.registry,
            })
        renderer = self._callFUT(info)
        self.assertTrue(renderer.template_loader)

    def test_with_filters_object(self):
        from pyramid_jinja2 import IJinja2Environment

        self.config.registry.settings.update(
            {'jinja2.directories': self.templates_dir,
             'jinja2.filters': {'dummy': dummy_filter}})
        info = DummyRendererInfo({
            'name': 'helloworld.jinja2',
            'package': None,
            'registry': self.config.registry,
            })
        self._callFUT(info)
        environ = self.config.registry.getUtility(IJinja2Environment)
        self.assertEqual(environ.filters['dummy'], dummy_filter)

    def test_with_filters_string(self):
        from pyramid_jinja2 import IJinja2Environment

        m = 'pyramid_jinja2.tests.test_it'
        self.config.registry.settings.update(
            {'jinja2.directories': self.templates_dir,
             'jinja2.filters': 'dummy=%s:dummy_filter' % m})
        info = DummyRendererInfo({
            'name': 'helloworld.jinja2',
            'package': None,
            'registry': self.config.registry,
            })
        self._callFUT(info)
        environ = self.config.registry.getUtility(IJinja2Environment)
        self.assertEqual(environ.filters['dummy'], dummy_filter)


class TestJinja2TemplateRenderer(Base, unittest.TestCase):
    def _getTargetClass(self):
        from pyramid_jinja2 import Jinja2TemplateRenderer
        return Jinja2TemplateRenderer

    def _makeOne(self, *arg, **kw):
        klass = self._getTargetClass()
        return klass(*arg, **kw)

    def test_call(self):
        template = DummyTemplate()
        instance = self._makeOne(lambda: template)
        result = instance({}, {'system': 1})
        self.assertTrue(isinstance(result, text_type))
        self.assertEqual(result, 'result')

    def test_call_with_system_context(self):
        template = DummyTemplate()
        instance = self._makeOne(lambda: template)
        result = instance({}, {'context': 1})
        self.assertTrue(isinstance(result, text_type))
        self.assertEqual(result, 'result')

    def test_call_with_nondict_value(self):
        template = DummyTemplate()
        instance = self._makeOne(lambda: template)
        self.assertRaises(ValueError, instance, None, {'context': 1})


class SearchPathTests(object):
    def test_relative_tmpl_helloworld(self):
        from pyramid.renderers import render
        result = render('templates/helloworld.jinja2', {})
        self.assertEqual(result, text_('\nHello föö', 'utf-8'))

    def test_relative_tmpl_extends(self):
        from pyramid.renderers import render
        result = render('templates/extends.jinja2', {})
        self.assertEqual(result, text_('\nHello fööYo!', 'utf-8'))

    def test_relative_tmpl_extends_abs(self):
        from pyramid.renderers import render
        result = render('templates/extends_abs.jinja2', {'a': 1})
        self.assertEqual(result, text_('\nHello fööYo!', 'utf-8'))

    def test_asset_tmpl_helloworld(self):
        from pyramid.renderers import render
        result = render('pyramid_jinja2.tests:templates/helloworld.jinja2',
                        {'a': 1})
        self.assertEqual(result, text_('\nHello föö', 'utf-8'))

    def test_asset_tmpl_extends(self):
        from pyramid.renderers import render
        result = render('pyramid_jinja2.tests:templates/extends.jinja2',
                        {'a': 1})
        self.assertEqual(result, text_('\nHello fööYo!', 'utf-8'))

    def test_asset_tmpl_extends_abs(self):
        from pyramid.renderers import render
        result = render('pyramid_jinja2.tests:templates/extends_abs.jinja2',
                        {'a': 1})
        self.assertEqual(result, text_('\nHello fööYo!', 'utf-8'))

    def test_abs_tmpl_extends_missing(self):
        import os.path
        from jinja2 import TemplateNotFound
        from pyramid.renderers import render
        here = os.path.abspath(os.path.dirname(__file__))
        templates_dir = os.path.join(here, 'templates')
        self.assertRaises(
            TemplateNotFound,
            lambda: render(
                os.path.join(templates_dir, '/extends_missing.jinja2'), {}))


class TestIntegrationWithSearchPath(SearchPathTests, unittest.TestCase):
    def setUp(self):
        config = testing.setUp()
        config.add_settings({'jinja2.directories':
                             'pyramid_jinja2.tests:templates'})
        config.include('pyramid_jinja2')
        self.config = config

    def tearDown(self):
        testing.tearDown()

    def test_tmpl_helloworld(self):
        from pyramid.renderers import render
        result = render('helloworld.jinja2', {'a': 1})
        self.assertEqual(result, text_('\nHello föö', 'utf-8'))

    def test_tmpl_extends(self):
        from pyramid.renderers import render
        result = render('extends.jinja2', {'a': 1})
        self.assertEqual(result, text_('\nHello fööYo!', 'utf-8'))

    def test_tmpl_extends_abs(self):
        from pyramid.renderers import render
        result = render('extends_abs.jinja2', {'a': 1})
        self.assertEqual(result, text_('\nHello fööYo!', 'utf-8'))

    def test_relative_tmpl_extends_relbase(self):
        from pyramid.renderers import render
        # this should pass as it will fallback to the new search path
        # and find it from there
        self.config.add_jinja2_search_path('pyramid_jinja2.tests:')
        result = render('extends_relbase.jinja2', {'a': 1})
        self.assertEqual(result, text_('\nHello fööYo!', 'utf-8'))


class TestIntegrationDefaultSearchPath(SearchPathTests, unittest.TestCase):
    def setUp(self):
        config = testing.setUp()
        config.include('pyramid_jinja2')

    def tearDown(self):
        testing.tearDown()

    def test_relative_tmpl_extends_relbase(self):
        from jinja2 import TemplateNotFound
        from pyramid.renderers import render
        # this should fail because the relative lookup will search for
        # templates/templates/extends_relbase.jinja2
        try:
            render('templates/extends_relbase.jinja2', {'a': 1})
        except TemplateNotFound as ex:
            self.assertTrue(
                'templates/templates/helloworld.jinja2' in ex.message)
        else: # pragma: no cover
            raise AssertionError


class TestIntegrationReloading(unittest.TestCase):
    def setUp(self):
        config = testing.setUp()
        config.add_settings({
            'pyramid.reload_templates': 'true',
        })
        config.include('pyramid_jinja2')
        self.config = config

    def tearDown(self):
        testing.tearDown()

    def test_render_reload_templates(self):
        import os, tempfile, time
        from webtest import TestApp

        _, path = tempfile.mkstemp('.jinja2')
        try:
            with open(path, 'wb') as fp:
                fp.write(b'foo')

            self.config.add_view(lambda r: {}, renderer=path)
            app = TestApp(self.config.make_wsgi_app())

            result = app.get('/').body
            self.assertEqual(result, b'foo')

            time.sleep(1)  # need mtime to change and most systems
                           # have 1-second resolution
            with open(path, 'wb') as fp:
                fp.write(b'bar')

            result = app.get('/').body
            self.assertEqual(result, b'bar')
        finally:
            os.unlink(path)


class Test_filters_and_tests(Base, unittest.TestCase):

    def _set_up_environ(self):
        self.config.include('pyramid_jinja2')
        return self.config.get_jinja2_environment()

    def _assert_has_test(self, test_name, test_obj):
        environ = self._set_up_environ()
        self.assertTrue(test_name in environ.tests)
        self.assertEqual(environ.tests[test_name], test_obj)

    def _assert_has_filter(self, filter_name, filter_obj):
        environ = self._set_up_environ()
        self.assertTrue(filter_name in environ.filters)
        self.assertEqual(environ.filters[filter_name], filter_obj)

    def _assert_has_global(self, global_name, global_obj):
        environ = self._set_up_environ()
        self.assertTrue(global_name in environ.globals)
        self.assertEqual(environ.globals[global_name], global_obj)

    def test_set_single_filter(self):
        self.config.registry.settings['jinja2.filters'] = \
                'my_filter = pyramid_jinja2.tests.test_it.my_test_func'
        self._assert_has_filter('my_filter', my_test_func)

    def test_set_single_test(self):
        self.config.registry.settings['jinja2.tests'] = \
                'my_test = pyramid_jinja2.tests.test_it.my_test_func'
        self._assert_has_test('my_test', my_test_func)

    def test_set_single_global(self):
        self.config.registry.settings['jinja2.globals'] = \
                'my_test = pyramid_jinja2.tests.test_it.my_test_func'
        self._assert_has_global('my_test', my_test_func)

    def test_set_multi_filters(self):
        self.config.registry.settings['jinja2.filters'] = \
                'my_filter1 = pyramid_jinja2.tests.test_it.my_test_func\n' \
                'my_filter2 = pyramid_jinja2.tests.test_it.my_test_func\n' \
                'my_filter3 = pyramid_jinja2.tests.test_it.my_test_func'
        self._assert_has_filter('my_filter1', my_test_func)
        self._assert_has_filter('my_filter2', my_test_func)
        self._assert_has_filter('my_filter3', my_test_func)

    def test_set_multi_tests(self):
        self.config.registry.settings['jinja2.tests'] = \
                'my_test1 = pyramid_jinja2.tests.test_it.my_test_func\n' \
                'my_test2 = pyramid_jinja2.tests.test_it.my_test_func\n' \
                'my_test3 = pyramid_jinja2.tests.test_it.my_test_func'
        self._assert_has_test('my_test1', my_test_func)
        self._assert_has_test('my_test2', my_test_func)
        self._assert_has_test('my_test3', my_test_func)

    def test_set_multi_globals(self):
        self.config.registry.settings['jinja2.globals'] = \
                'my_global1 = pyramid_jinja2.tests.test_it.my_test_func\n' \
                'my_global2 = pyramid_jinja2.tests.test_it.my_test_func\n' \
                'my_global3 = pyramid_jinja2.tests.test_it.my_test_func'
        self._assert_has_global('my_global1', my_test_func)
        self._assert_has_global('my_global2', my_test_func)
        self._assert_has_global('my_global3', my_test_func)

    def test_filter_and_test_and_global_works_in_render(self):
        from pyramid.renderers import render
        config = testing.setUp()
        config.include('pyramid_jinja2')
        config.add_settings({
            'jinja2.directories': 'pyramid_jinja2.tests:templates',
            'jinja2.tests': 'my_test = pyramid_jinja2.tests.test_it.my_test_func',
            'jinja2.filters': 'my_filter = pyramid_jinja2.tests.test_it.my_test_func',
            'jinja2.globals': 'my_global = pyramid_jinja2.tests.test_it.my_test_func'
        })
        config.add_jinja2_renderer('.jinja2')
        result = render('tests_and_filters.jinja2', {})
        #my_test_func returs "True" - it will be render as True when usign
        # as filter and will pass in tests
        self.assertEqual(result, text_('True is not False True', 'utf-8'))
        testing.tearDown()


class Test_includeme(unittest.TestCase):
    def test_it(self):
        from pyramid.interfaces import IRendererFactory
        from pyramid_jinja2 import includeme
        from pyramid_jinja2 import Jinja2RendererFactory
        config = testing.setUp()
        config.registry.settings['jinja2.directories'] = '/foobar'
        includeme(config)
        utility = config.registry.getUtility(IRendererFactory, name='.jinja2')
        self.assertTrue(isinstance(utility, Jinja2RendererFactory))


class Test_add_jinja2_searchpath(unittest.TestCase):
    def test_it_relative_to_package(self):
        import pyramid_jinja2.tests
        from pyramid_jinja2 import includeme
        import os
        config = testing.setUp()
        # hack because pyramid pre 1.6 doesn't configure testing configurator
        # with the correct package name
        config.package = pyramid_jinja2.tests
        config.package_name = 'pyramid_jinja2.tests'
        config.add_settings({'jinja2.directories': 'foobar'})
        includeme(config)
        env = config.get_jinja2_environment()
        self.assertEqual(len(env.loader.searchpath), 2)
        self.assertEqual(
            [x.split(os.sep)[-3:] for x in env.loader.searchpath][0],
            ['pyramid_jinja2', 'tests', 'foobar'])
        self.assertEqual(
            [x.split(os.sep)[-2:] for x in env.loader.searchpath][1],
            ['pyramid_jinja2', 'tests'])

        config.add_jinja2_search_path('grrr')
        self.assertEqual(len(env.loader.searchpath), 3)
        self.assertEqual(
            [x.split(os.sep)[-3:] for x in env.loader.searchpath][0],
            ['pyramid_jinja2', 'tests', 'foobar'])
        self.assertEqual(
            [x.split(os.sep)[-2:] for x in env.loader.searchpath][1],
            ['pyramid_jinja2', 'tests'])
        self.assertEqual(
            [x.split(os.sep)[-3:] for x in env.loader.searchpath][2],
            ['pyramid_jinja2', 'tests', 'grrr'])


class Test_get_jinja2_environment(unittest.TestCase):
    def test_it(self):
        from pyramid_jinja2 import includeme, Environment
        config = testing.setUp()
        includeme(config)
        self.assertEqual(config.get_jinja2_environment().__class__,
                         Environment)


class Test_bytecode_caching(unittest.TestCase):
    def test_default(self):
        from pyramid_jinja2 import includeme
        config = testing.setUp()
        config.registry.settings = {}
        includeme(config)
        env = config.get_jinja2_environment()
        self.assertTrue(env.bytecode_cache is None)
        self.assertFalse(env.auto_reload)

    def test_default_bccache(self):
        from pyramid_jinja2 import includeme
        import jinja2.bccache
        config = testing.setUp()
        config.registry.settings = {'jinja2.bytecode_caching': 'true'}
        includeme(config)
        env = config.get_jinja2_environment()
        self.assertTrue(isinstance(env.bytecode_cache,
                                   jinja2.bccache.FileSystemBytecodeCache))
        self.assertTrue(env.bytecode_cache.directory)
        self.assertFalse(env.auto_reload)

    def test_directory(self):
        import tempfile
        from pyramid_jinja2 import includeme
        tmpdir = tempfile.mkdtemp()
        config = testing.setUp()
        config.registry.settings['jinja2.bytecode_caching'] = '1'
        config.registry.settings['jinja2.bytecode_caching_directory'] = tmpdir
        includeme(config)
        env = config.get_jinja2_environment()
        self.assertEqual(env.bytecode_cache.directory, tmpdir)
        # TODO: test tmpdir is deleted when interpreter exits

    def test_bccache_instance(self):
        from pyramid_jinja2 import includeme
        import jinja2.bccache
        mycache = jinja2.bccache.MemcachedBytecodeCache(DummyMemcachedClient())
        config = testing.setUp()
        config.registry.settings = {'jinja2.bytecode_caching': mycache}
        includeme(config)
        env = config.get_jinja2_environment()
        self.assertTrue(env.bytecode_cache is mycache)
        self.assertFalse(env.auto_reload)

    def test_pyramid_reload_templates(self):
        from pyramid_jinja2 import includeme
        config = testing.setUp()
        config.registry.settings = {}
        config.registry.settings['pyramid.reload_templates'] = 'true'
        includeme(config)
        env = config.get_jinja2_environment()
        self.assertTrue(env.auto_reload)


class TestSmartAssetSpecLoader(unittest.TestCase):

    def _makeOne(self, **kw):
        from pyramid_jinja2 import SmartAssetSpecLoader
        return SmartAssetSpecLoader(**kw)

    def test_list_templates(self):
        loader = self._makeOne()
        self.assertRaises(TypeError, loader.list_templates)

    def test_get_source_invalid_spec(self):
        from jinja2.exceptions import TemplateNotFound
        loader = self._makeOne()
        self.assertRaises(TemplateNotFound,
                          loader.get_source, None, 'asset:foobar.jinja2')

    def test_get_source_spec(self):
        loader = self._makeOne()
        asset = 'pyramid_jinja2.tests:templates/helloworld.jinja2'
        self.assertNotEqual(loader.get_source(None, asset), None)

    def test_get_source_legacy_spec(self):
        loader = self._makeOne()
        # make sure legacy prefixed asset spec based loading works
        asset = 'asset:pyramid_jinja2.tests:templates/helloworld.jinja2'
        self.assertNotEqual(loader.get_source(None, asset), None)

    def test_get_source_from_path(self):
        import os.path
        here = os.path.abspath(os.path.dirname(__file__))
        loader = self._makeOne(searchpath=[here])
        asset = 'templates/helloworld.jinja2'
        self.assertNotEqual(loader.get_source(None, asset), None)


class TestFileInfo(unittest.TestCase):

    def test_mtime(self):
        from pyramid_jinja2 import FileInfo
        from pyramid.asset import abspath_from_asset_spec

        filename = abspath_from_asset_spec('templates/helloworld.jinja2',
                                           'pyramid_jinja2.tests')

        fi = FileInfo(filename)
        assert '_mtime' not in fi.__dict__
        assert fi.mtime is not None
        assert fi.mtime == fi._mtime

    def test_uptodate(self):
        from pyramid_jinja2 import FileInfo
        fi = FileInfo('foobar')
        assert fi.uptodate() is False

    def test_notfound(self):
        from jinja2 import TemplateNotFound
        from pyramid_jinja2 import FileInfo
        fi = FileInfo('foobar')
        self.assertRaises(TemplateNotFound, lambda: fi._delay_init())

    def test_delay_init(self):
        from pyramid_jinja2 import FileInfo

        class MyFileInfo(FileInfo):
            filename = 'foo.jinja2'

            def __init__(self, data):
                self.data = data
                FileInfo.__init__(self, self.filename)

            def open_if_exists(self, fname):
                return StringIO(self.data)

            def getmtime(self, fname):
                return 1

        mi = MyFileInfo(text_('nothing good here, move along'))
        mi._delay_init()
        self.assertEqual(mi._contents, mi.data)


class TestJinja2SearchPathIntegration(unittest.TestCase):

    def test_it(self):
        from pyramid.config import Configurator
        from pyramid_jinja2 import includeme
        from webtest import TestApp
        import os

        here = os.path.abspath(os.path.dirname(__file__))
        templates_dir = os.path.join(here, 'templates')

        def myview(request):
            return {}

        config1 = Configurator(settings={
                'jinja2.directories': os.path.join(templates_dir, 'foo')})
        includeme(config1)
        config1.add_view(view=myview, renderer='mytemplate.jinja2')
        config2 = Configurator(settings={
                'jinja2.directories': os.path.join(templates_dir, 'bar')})
        includeme(config2)
        config2.add_view(view=myview, renderer='mytemplate.jinja2')
        self.assertNotEqual(config1.registry.settings,
                            config2.registry.settings)

        app1 = config1.make_wsgi_app()
        testapp = TestApp(app1)
        self.assertEqual(testapp.get('/').body, bytes_('foo'))

        app2 = config2.make_wsgi_app()
        testapp = TestApp(app2)
        self.assertEqual(testapp.get('/').body, bytes_('bar'))

    def test_it_relative(self):
        from pyramid.config import Configurator
        from pyramid_jinja2 import includeme
        from webtest import TestApp

        def myview(request):
            return {}

        config = Configurator(settings={'jinja2.directories': 'templates'})
        includeme(config)
        config.add_view(view=myview, name='baz1',
                        renderer='baz1/mytemplate.jinja2')
        config.add_view(view=myview, name='baz2',
                        renderer='baz2/mytemplate.jinja2')

        app1 = config.make_wsgi_app()
        testapp = TestApp(app1)
        self.assertEqual(testapp.get('/baz1').body, bytes_('baz1\nbaz1 body'))
        self.assertEqual(testapp.get('/baz2').body, bytes_('baz2\nbaz2 body'))


class TestPackageFinder(unittest.TestCase):

    def test_caller_package(self):
        from pyramid_jinja2 import _PackageFinder
        pf = _PackageFinder()

        class MockInspect(object):
            def __init__(self, items=()):
                self.items = items

            def stack(self):
                return self.items
        pf.inspect = MockInspect()
        self.assertEqual(pf.caller_package(), None)

        import xml
        pf.inspect.items = [(Mock(f_globals={'__name__': 'xml'}),)]


class TestNewstyle(unittest.TestCase):
    def test_it(self):
        from pyramid.config import Configurator
        from pyramid_jinja2 import includeme
        from webtest import TestApp
        import os

        here = os.path.abspath(os.path.dirname(__file__))
        templates_dir = os.path.join(here, 'templates')

        def myview(request):
            return {'what': 'eels'}

        config = Configurator(settings={
                'jinja2.directories': templates_dir,
                'jinja2.newstyle': True})
        includeme(config)
        config.add_view(view=myview, renderer='newstyle.jinja2')

        app = config.make_wsgi_app()
        testapp = TestApp(app)
        self.assertEqual(testapp.get('/').body.decode('utf-8'), text_('my hovercraft is full of eels!'))


class Test_add_jinja2_extension(Base, unittest.TestCase):

    def test_it(self):
        self.config.include('pyramid_jinja2')
        env_before = self.config.get_jinja2_environment()

        class MockExt(object):
            identifier = 'foobar'

            def __init__(self, x):
                self.x = x

        self.config.add_jinja2_extension(MockExt)

        env_after = self.config.get_jinja2_environment()
        self.assertTrue('foobar' in env_after.extensions)
        self.assertTrue(env_before is env_after)

    def test_alternate_renderer_extension(self):
        self.config.include('pyramid_jinja2')
        self.config.add_jinja2_renderer('.html')
        env_before = self.config.get_jinja2_environment('.html')

        class MockExt(object):
            identifier = 'foobar'

            def __init__(self, x):
                self.x = x

        self.config.add_jinja2_extension(MockExt, '.html')

        env_after = self.config.get_jinja2_environment('.html')
        default_env = self.config.get_jinja2_environment()

        self.assertTrue('foobar' in env_after.extensions)
        self.assertTrue('foobar' not in default_env.extensions)
        self.assertTrue(env_before is env_after)


def my_test_func(*args, **kwargs):
    """ Used as a fake filter/test function """
    return True

class DummyMemcachedClient(dict):
    """ A memcached client acceptable to jinja2.MemcachedBytecodeCache.
    """
    def set(self, key, value, timeout):
        self[key] = value               # pragma: no cover

class DummyEnviron(dict):
    def get_template(self, path):  # pragma: no cover
        return path

class DummyTemplate(object):
    def render(self, system):
        return b'result'.decode('utf-8')

class DummyRendererInfo(object):
    def __init__(self, kw):
        self.__dict__.update(kw)
        if 'registry' in self.__dict__:
            self.settings = self.registry.settings

########NEW FILE########
__FILENAME__ = test_settings
import os.path
import unittest


class Test_parse_named_assetspecs(unittest.TestCase):

    def _callFUT(self, *args, **kwargs):
        from pyramid_jinja2.settings import parse_named_assetspecs
        return parse_named_assetspecs(*args, **kwargs)

    def test_it_with_strings(self):
        from pyramid.path import DottedNameResolver
        import pyramid_jinja2
        import pyramid_jinja2.tests
        resolver = DottedNameResolver()
        result = self._callFUT(
            '''
            foo = pyramid_jinja2
            bar= pyramid_jinja2.tests
            ''',
            resolver.maybe_resolve,
        )
        self.assertEqual(result['foo'], pyramid_jinja2)
        self.assertEqual(result['bar'], pyramid_jinja2.tests)

    def test_it_with_dict(self):
        from pyramid.path import DottedNameResolver
        import pyramid_jinja2
        import pyramid_jinja2.tests
        resolver = DottedNameResolver()
        result = self._callFUT(
            {
                'foo': 'pyramid_jinja2',
                'bar': pyramid_jinja2.tests,
            },
            resolver.maybe_resolve,
        )
        self.assertEqual(result['foo'], pyramid_jinja2)
        self.assertEqual(result['bar'], pyramid_jinja2.tests)


class Test_parse_loader_options_from_settings(unittest.TestCase):

    def _callFUT(self, *args, **kwargs):
        from pyramid_jinja2.settings import parse_loader_options_from_settings
        return parse_loader_options_from_settings(*args, **kwargs)

    def test_defaults(self):
        options = self._callFUT({}, 'p.', None, None)
        self.assertEqual(options['debug'], False)
        self.assertEqual(options['encoding'], 'utf-8')
        self.assertEqual(len(options['searchpath']), 0)

    def test_options(self):
        options = self._callFUT(
            {
                'debug_templates': 'false',
                'p.debug_templates': 'true',
                'p.input_encoding': 'ascii',
                'p.directories': 'pyramid_jinja2.tests:templates',
            },
            'p.', None, None,
        )
        self.assertEqual(options['debug'], True)
        self.assertEqual(options['encoding'], 'ascii')
        self.assertEqual(len(options['searchpath']), 1)
        self.assertTrue(
            options['searchpath'][0].endswith(
                os.path.join('pyramid_jinja2', 'tests', 'templates')))

    def test_options_with_spec(self):
        options = self._callFUT(
            {'p.directories': 'pyramid_jinja2:'}, 'p.', None, None)
        self.assertEqual(len(options['searchpath']), 1)
        self.assertTrue(options['searchpath'][0].endswith('pyramid_jinja2'))

    def test_options_with_abspath(self):
        import os.path
        here = os.path.dirname(os.path.abspath(__file__))
        options = self._callFUT({'p.directories': here}, 'p.', None, None)
        self.assertEqual(len(options['searchpath']), 1)
        self.assertEqual(options['searchpath'][0], here)

    def test_options_with_relpath(self):
        import os
        import pyramid_jinja2
        options = self._callFUT(
            {'p.directories': 'foo'}, 'p.', None, pyramid_jinja2)
        self.assertEqual(len(options['searchpath']), 1)
        self.assertEqual(options['searchpath'][0].split(os.sep)[-2:],
                         ['pyramid_jinja2', 'foo'])

    def test_debug_fallback(self):
        options = self._callFUT(
            {
                'debug_templates': 'true',
            },
            'p.', None, None,
        )
        self.assertEqual(options['debug'], True)


class Test_parse_env_options_from_settings(unittest.TestCase):

    def _callFUT(self, settings, prefix=''):
        import pyramid_jinja2
        from pyramid.path import DottedNameResolver
        from pyramid_jinja2.settings import parse_env_options_from_settings
        resolver = DottedNameResolver()
        return parse_env_options_from_settings(
            settings, prefix, resolver.maybe_resolve, pyramid_jinja2,
        )

    def test_most_settings(self):
        settings = {
            'j2.block_start_string': '<<<',
            'j2.block_end_string': '>>>',
            'j2.variable_start_string': '<|<',
            'j2.variable_end_string': '>|>',
            'j2.comment_start_string': '<+<',
            'j2.comment_end_string': '>+>',
            'j2.line_statement_prefix': '>.>',
            'j2.line_comment_prefix': '^.^',
            'j2.trim_blocks': 'true',
            'j2.newline_sequence': '\r',
            'j2.optimized': 'true',
            'j2.autoescape': 'false',
            'j2.cache_size': '300',
        }
        opts = self._callFUT(settings, 'j2.')
        # test
        self.assertEqual(opts['block_start_string'], '<<<')
        self.assertEqual(opts['block_end_string'], '>>>')
        self.assertEqual(opts['variable_start_string'], '<|<')
        self.assertEqual(opts['variable_end_string'], '>|>')
        self.assertEqual(opts['comment_start_string'], '<+<')
        self.assertEqual(opts['comment_end_string'], '>+>')
        self.assertEqual(opts['line_statement_prefix'], '>.>')
        self.assertEqual(opts['line_comment_prefix'], '^.^')
        self.assertEqual(opts['trim_blocks'], True)
        self.assertEqual(opts['newline_sequence'], '\r')
        self.assertEqual(opts['optimized'], True)
        self.assertEqual(opts['autoescape'], False)
        self.assertEqual(opts['cache_size'], 300)
        self.assertEqual(opts['gettext'].domain, 'pyramid_jinja2')

    def test_strict_undefined(self):
        from jinja2 import StrictUndefined
        settings = {'j2.undefined': 'strict'}
        opts = self._callFUT(settings, 'j2.')
        self.assertEqual(opts['undefined'], StrictUndefined)

    def test_debug_undefined(self):
        from jinja2 import DebugUndefined
        settings = {'j2.undefined': 'debug'}
        opts = self._callFUT(settings, 'j2.')
        self.assertEqual(opts['undefined'], DebugUndefined)

    def test_default_undefined(self):
        from jinja2 import Undefined
        settings = {'j2.undefined': ''}
        opts = self._callFUT(settings, 'j2.')
        self.assertEqual(opts['undefined'], Undefined)

########NEW FILE########
