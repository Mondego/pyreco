__FILENAME__ = decorators
from functools import wraps


def csp_exempt(f):
    @wraps(f)
    def _wrapped(*a, **kw):
        r = f(*a, **kw)
        r._csp_exempt = True
        return r
    return _wrapped


def csp_update(**kwargs):
    update = dict((k.lower().replace('_', '-'), v) for k, v in kwargs.items())

    def decorator(f):
        @wraps(f)
        def _wrapped(*a, **kw):
            r = f(*a, **kw)
            r._csp_update = update
            return r
        return _wrapped
    return decorator


def csp_replace(**kwargs):
    replace = dict((k.lower().replace('_', '-'), v) for k, v in kwargs.items())

    def decorator(f):
        @wraps(f)
        def _wrapped(*a, **kw):
            r = f(*a, **kw)
            r._csp_replace = replace
            return r
        return _wrapped
    return decorator


def csp(**kwargs):
    config = dict((k.lower().replace('_', '-'), v) for k, v in kwargs.items())

    def decorator(f):
        @wraps(f)
        def _wrapped(*a, **kw):
            r = f(*a, **kw)
            r._csp_config = config
            return r
        return _wrapped
    return decorator

########NEW FILE########
__FILENAME__ = middleware
from django.conf import settings
from django.utils.six.moves import http_client

from csp.utils import build_policy


class CSPMiddleware(object):
    """
    Implements the Content-Security-Policy response header, which
    conforming user-agents can use to restrict the permitted sources
    of various content.

    See http://www.w3.org/TR/CSP/

    """

    def process_response(self, request, response):
        if getattr(response, '_csp_exempt', False):
            return response

        # Check for ignored path prefix.
        prefixes = getattr(settings, 'CSP_EXCLUDE_URL_PREFIXES', ('/admin',))
        if request.path_info.startswith(prefixes):
            return response

        # Check for debug view
        status_code = response.status_code
        if status_code == http_client.INTERNAL_SERVER_ERROR and settings.DEBUG:
            return response

        header = 'Content-Security-Policy'
        if getattr(settings, 'CSP_REPORT_ONLY', False):
            header += '-Report-Only'

        if header in response:
            # Don't overwrite existing headers.
            return response

        config = getattr(response, '_csp_config', None)
        update = getattr(response, '_csp_update', None)
        replace = getattr(response, '_csp_replace', None)
        response[header] = build_policy(config=config, update=update,
                                        replace=replace)
        return response

########NEW FILE########
__FILENAME__ = models
# This file intentionally left blank.

########NEW FILE########
__FILENAME__ = test_decorators
from django.http import HttpResponse
from django.test import RequestFactory, TestCase
from django.test.utils import override_settings

from nose.tools import eq_

from csp.decorators import csp, csp_replace, csp_update, csp_exempt


REQUEST = RequestFactory().get('/')


class DecoratorTests(TestCase):
    def test_csp_exempt(self):
        @csp_exempt
        def view(request):
            return HttpResponse()
        response = view(REQUEST)
        assert response._csp_exempt

    @override_settings(CSP_IMG_SRC=['foo.com'])
    def test_csp_update(self):
        @csp_update(IMG_SRC='bar.com')
        def view(request):
            return HttpResponse()
        response = view(REQUEST)
        eq_(response._csp_update, {'img-src': 'bar.com'})

    @override_settings(CSP_IMG_SRC=['foo.com'])
    def test_csp_replace(self):
        @csp_replace(IMG_SRC='bar.com')
        def view(request):
            return HttpResponse()
        response = view(REQUEST)
        eq_(response._csp_replace, {'img-src': 'bar.com'})

    def test_csp(self):
        @csp(IMG_SRC='foo.com', FONT_SRC='bar.com')
        def view(request):
            return HttpResponse()
        response = view(REQUEST)
        eq_(response._csp_config,
            {'img-src': 'foo.com', 'font-src': 'bar.com'})

########NEW FILE########
__FILENAME__ = test_middleware
from django.http import HttpResponse, HttpResponseServerError
from django.test import RequestFactory, TestCase
from django.test.utils import override_settings

from nose.tools import eq_

from csp.middleware import CSPMiddleware


HEADER = 'Content-Security-Policy'
mw = CSPMiddleware()
rf = RequestFactory()


class MiddlewareTests(TestCase):
    def test_add_header(self):
        request = rf.get('/')
        response = HttpResponse()
        mw.process_response(request, response)
        assert HEADER in response

    def test_exempt(self):
        request = rf.get('/')
        response = HttpResponse()
        response._csp_exempt = True
        mw.process_response(request, response)
        assert HEADER not in response

    def text_exclude(self):
        request = rf.get('/admin/foo')
        response = HttpResponse()
        mw.process_response(request, response)
        assert HEADER not in response

    @override_settings(CSP_REPORT_ONLY=True)
    def test_report_only(self):
        request = rf.get('/')
        response = HttpResponse()
        mw.process_response(request, response)
        assert HEADER not in response
        assert HEADER + '-Report-Only' in response

    def test_dont_replace(self):
        request = rf.get('/')
        response = HttpResponse()
        response[HEADER] = 'default-src example.com'
        mw.process_response(request, response)
        eq_(response[HEADER], 'default-src example.com')

    def test_use_config(self):
        request = rf.get('/')
        response = HttpResponse()
        response._csp_config = {'default-src': ['example.com']}
        mw.process_response(request, response)
        eq_(response[HEADER], 'default-src example.com')

    def test_use_update(self):
        request = rf.get('/')
        response = HttpResponse()
        response._csp_update = {'default-src': ['example.com']}
        mw.process_response(request, response)
        eq_(response[HEADER], "default-src 'self' example.com")

    @override_settings(CSP_IMG_SRC=['foo.com'])
    def test_use_replace(self):
        request = rf.get('/')
        response = HttpResponse()
        response._csp_replace = {'img-src': ['bar.com']}
        mw.process_response(request, response)
        eq_(response[HEADER], "default-src 'self'; img-src bar.com")

    @override_settings(DEBUG=True)
    def test_debug_exempt(self):
        request = rf.get('/')
        response = HttpResponseServerError()
        mw.process_response(request, response)
        assert HEADER not in response

########NEW FILE########
__FILENAME__ = test_utils
from django.test import TestCase
from django.test.utils import override_settings

from nose.tools import eq_

from csp.utils import build_policy


def policy_eq(a, b, msg='%r != %r'):
    parts_a = sorted(a.split('; '))
    parts_b = sorted(b.split('; '))
    assert parts_a == parts_b, msg % (a, b)


class UtilsTests(TestCase):
    def test_empty_policy(self):
        policy = build_policy()
        eq_("default-src 'self'", policy)

    @override_settings(CSP_DEFAULT_SRC=['example.com', 'example2.com'])
    def test_default_src(self):
        policy = build_policy()
        eq_('default-src example.com example2.com', policy)

    @override_settings(CSP_SCRIPT_SRC=['example.com'])
    def test_script_src(self):
        policy = build_policy()
        policy_eq("default-src 'self'; script-src example.com", policy)

    @override_settings(CSP_OBJECT_SRC=['example.com'])
    def test_object_src(self):
        policy = build_policy()
        policy_eq("default-src 'self'; object-src example.com", policy)

    @override_settings(CSP_STYLE_SRC=['example.com'])
    def test_style_src(self):
        policy = build_policy()
        policy_eq("default-src 'self'; style-src example.com", policy)

    @override_settings(CSP_IMG_SRC=['example.com'])
    def test_img_src(self):
        policy = build_policy()
        policy_eq("default-src 'self'; img-src example.com", policy)

    @override_settings(CSP_MEDIA_SRC=['example.com'])
    def test_media_src(self):
        policy = build_policy()
        policy_eq("default-src 'self'; media-src example.com", policy)

    @override_settings(CSP_FRAME_SRC=['example.com'])
    def test_frame_src(self):
        policy = build_policy()
        policy_eq("default-src 'self'; frame-src example.com", policy)

    @override_settings(CSP_FONT_SRC=['example.com'])
    def test_font_src(self):
        policy = build_policy()
        policy_eq("default-src 'self'; font-src example.com", policy)

    @override_settings(CSP_CONNECT_SRC=['example.com'])
    def test_connect_src(self):
        policy = build_policy()
        policy_eq("default-src 'self'; connect-src example.com", policy)

    @override_settings(CSP_SANDBOX=['allow-scripts'])
    def test_sandbox(self):
        policy = build_policy()
        policy_eq("default-src 'self'; sandbox allow-scripts", policy)

    @override_settings(CSP_SANDBOX=[])
    def test_sandbox_empty(self):
        policy = build_policy()
        policy_eq("default-src 'self'; sandbox ", policy)

    @override_settings(CSP_REPORT_URI='/foo')
    def test_report_uri(self):
        policy = build_policy()
        policy_eq("default-src 'self'; report-uri /foo", policy)

    @override_settings(CSP_IMG_SRC=['example.com'])
    def test_update_img(self):
        policy = build_policy(update={'img-src': 'example2.com'})
        policy_eq("default-src 'self'; img-src example.com example2.com",
                  policy)

    def test_update_missing_setting(self):
        """update should work even if the setting is not defined."""
        policy = build_policy(update={'img-src': 'example.com'})
        policy_eq("default-src 'self'; img-src example.com", policy)

    @override_settings(CSP_IMG_SRC=['example.com'])
    def test_replace_img(self):
        policy = build_policy(replace={'img-src': 'example2.com'})
        policy_eq("default-src 'self'; img-src example2.com", policy)

    def test_replace_missing_setting(self):
        """replace should work even if the setting is not defined."""
        policy = build_policy(replace={'img-src': 'example.com'})
        policy_eq("default-src 'self'; img-src example.com", policy)

    def test_config(self):
        policy = build_policy(
            config={'default-src': ["'none'"], 'img-src': ["'self'"]})
        policy_eq("default-src 'none'; img-src 'self'", policy)

    @override_settings(CSP_IMG_SRC=('example.com',))
    def test_update_string(self):
        """
        GitHub issue #40 - given project settings as a tuple, and
        an update/replace with a string, concatenate correctly.
        """
        policy = build_policy(update={'img-src': 'example2.com'})
        policy_eq("default-src 'self'; img-src example.com example2.com",
                  policy)

    @override_settings(CSP_IMG_SRC=('example.com',))
    def test_replace_string(self):
        """
        Demonstrate that GitHub issue #40 doesn't affect replacements
        """
        policy = build_policy(replace={'img-src': 'example2.com'})
        policy_eq("default-src 'self'; img-src example2.com",
                  policy)

########NEW FILE########
__FILENAME__ = utils
from django.conf import settings


def from_settings():
    return {
        'default-src': getattr(settings, 'CSP_DEFAULT_SRC', ["'self'"]),
        'script-src': getattr(settings, 'CSP_SCRIPT_SRC', None),
        'object-src': getattr(settings, 'CSP_OBJECT_SRC', None),
        'style-src': getattr(settings, 'CSP_STYLE_SRC', None),
        'img-src': getattr(settings, 'CSP_IMG_SRC', None),
        'media-src': getattr(settings, 'CSP_MEDIA_SRC', None),
        'frame-src': getattr(settings, 'CSP_FRAME_SRC', None),
        'font-src': getattr(settings, 'CSP_FONT_SRC', None),
        'connect-src': getattr(settings, 'CSP_CONNECT_SRC', None),
        'sandbox': getattr(settings, 'CSP_SANDBOX', None),
        'report-uri': getattr(settings, 'CSP_REPORT_URI', None),
    }


def build_policy(config=None, update=None, replace=None):
    """Builds the policy as a string from the settings."""

    if config is None:
        config = from_settings()

    # Update rules from settings.
    if update is not None:
        for k, v in update.items():
            if not isinstance(v, (list, tuple)):
                v = (v,)
            if config[k] is not None:
                config[k] += v
            else:
                config[k] = v

    # Replace rules from settings.
    if replace is not None:
        for k, v in replace.items():
            if v is not None and not isinstance(v, (list, tuple)):
                v = [v]
            config[k] = v

    report_uri = config.pop('report-uri', None)
    policy = ['%s %s' % (k, ' '.join(v)) for k, v in
              config.items() if v is not None]
    if report_uri:
        policy.append('report-uri %s' % report_uri)
    return '; '.join(policy)

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Django-CSP documentation build configuration file, created by
# sphinx-quickstart on Wed Oct 31 13:02:27 2012.
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
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Django-CSP'
copyright = u'2013 Mozilla Foundation'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '2.0'
# The full version, including alpha/beta/rc tags.
release = '2.0'

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
htmlhelp_basename = 'Django-CSPdoc'


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
  ('index', 'Django-CSP.tex', u'Django-CSP Documentation',
   u'James Socol, Mozilla', 'manual'),
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
    ('index', 'django-csp', u'Django-CSP Documentation',
     [u'James Socol, Mozilla'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'Django-CSP', u'Django-CSP Documentation',
   u'James Socol, Mozilla', 'Django-CSP', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

########NEW FILE########
__FILENAME__ = test_settings
DEBUG = True
TEMPLATE_DEBUG = True

CSP_REPORT_ONLY = False

SITE_ID = 1

DATABASES = {
    'default': {
        'NAME': 'test.db',
        'ENGINE': 'django.db.backends.sqlite3',
    }
}

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'csp',
)

SECRET_KEY = 'csp-test-key'

########NEW FILE########
