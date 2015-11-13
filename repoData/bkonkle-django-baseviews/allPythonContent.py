__FILENAME__ = models
# This is a dummy file to convince Django that baseviews is a real app

########NEW FILE########
__FILENAME__ = tests
import unittest
from django.conf import settings
from django.test import TestCase, Client
from django.utils import simplejson
from baseviews.views import BasicView


@unittest.skipIf(not settings.ROOT_URLCONF == 'test_project.urls',
                 'These tests will only work with the test project.')
class BaseviewTests(TestCase):

    def test_basic_view(self):
        response = self.client.get('/lol/')

        self.assertEqual(response.content, 'I can haz cheezburger\n')

        self.assertTrue('verb' in response.context)
        self.assertEqual(response.context['verb'], 'haz')

        self.assertTrue('noun' in response.context)
        self.assertEqual(response.context['noun'], 'cheezburger')

        self.assertEqual(response.template.name, 'home.html')

        self.assertEqual(response['Content-Type'],
                         settings.DEFAULT_CONTENT_TYPE)

    def test_ajax_view(self):
        response = self.client.get('/ajax/')

        # This should fail because it's not an Ajax request
        self.assertEqual(response.status_code, 404)

        response = self.client.get('/ajax/',
                                   HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(simplejson.loads(response.content)['armed'],
                         '...with Ajax!')

    def test_form_view(self):
        from test_project.views import KittehForm

        response = self.client.get('/kitteh/')
        self.assertEqual(response.content, str(KittehForm()))

        response = self.client.post('/kitteh/',
                                    {'caption': "No, you can't haz a pony."})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response._headers['location'][1],
                         'http://testserver/pewpewpew/')

    def test_multi_form_view(self):
        from test_project.views import KittehForm, GoggieForm

        response = self.client.get('/monorail/')
        self.assertEqual(response.content,
                         ' '.join([str(KittehForm()), str(GoggieForm())]))
        
        response = self.client.post('/monorail/',
                                    {'caption': "Not yours.",
                                     'bark': 'Woof!'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response._headers['location'][1],
                         'http://testserver/derailed/')

########NEW FILE########
__FILENAME__ = views
from django.conf import settings
from django.core.cache import cache
from django.core.serializers.json import DjangoJSONEncoder
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.utils import simplejson
from django.shortcuts import render_to_response
from django.template import RequestContext


class BasicView(object):
    cache_key = None # Leave as none to disable context caching
    cache_time = 60*5 # 5 minutes
    content_type = settings.DEFAULT_CONTENT_TYPE

    def __new__(cls, request, *args, **kwargs):
        instance = object.__new__(cls)
        if isinstance(instance, cls):
            instance.__init__(request, *args, **kwargs)
        return instance()

    def __init__(self, request, *args, **kwargs):
        self.request = request
        self.args = args
        self.kwargs = kwargs

    def __call__(self):
        """Handle the request processing workflow."""
        return self.render()

    def get_cache_key(self):
        """Provide an opportunity to dynamically generate the cache key."""
        return self.cache_key

    def get_context(self):
        """
        Retrieve the cached context from the cache if it exists. Otherwise,
        generate it and cache it.
        """
        cache_key = self.get_cache_key()
        if cache_key is None:
            context_dict = self.cached_context()
        else:
            context_dict = cache.get(cache_key)
            if context_dict is None:
                context_dict = self.cached_context()
                cache.set(cache_key, context_dict, self.cache_time)
        context_dict.update(self.uncached_context())
        return context_dict

    def cached_context(self):
        """Provide the context that can be cached."""
        return {}

    def uncached_context(self):
        """Provide the context that should not be cached."""
        return {}

    def get_template(self):
        """
        Provide an opportunity for to dynamically generate the template name.
        """
        return self.template

    def render(self):
        """Take the context and render it using the template."""
        return render_to_response(self.get_template(), self.get_context(),
                                  RequestContext(self.request),
                                  mimetype=self.content_type)


class AjaxView(BasicView):
    """Returns a response containing the context serialized to Json"""
    content_type = 'application/json'

    def __call__(self):
        if not self.request.is_ajax():
            raise Http404
        return super(AjaxView, self).__call__()

    def render(self):
        json_data = simplejson.dumps(self.get_context(),
                                     cls=DjangoJSONEncoder)
        return HttpResponse(json_data, content_type=self.content_type)


class FormView(BasicView):

    def __init__(self, request, *args, **kwargs):
        super(FormView, self).__init__(request, *args, **kwargs)
        self.data = getattr(self.request, 'POST', None)
        self.files = getattr(self.request, 'FILES', None)
        self.form_options = {}
        self.form = self.get_form()

    def __call__(self):
        if self.request.method == 'POST':
            response = self.process_form()
            # If a response was returned by the process_form method, then
            # return that response instead of the standard response.
            if response:
                return response

        return self.render()

    def uncached_context(self):
        """Add the form to the uncached context."""
        context = super(FormView, self).uncached_context()
        context.update({'form': self.form})
        return context

    def get_form(self):
        """
        Get the default form for the view, bound with data if provided.
        """
        if self.data:
            self.form_options.update({'data': self.data})
        if self.files:
            self.form_options.update({'files': self.files})
        return self.form_class(**self.form_options)

    def process_form(self):
        """
        The method to process POST requests. Return an HttpResponse when you
        need to circumvent normal view processing, such as redirecting to a
        success url.
        """
        if self.form.is_valid():
            self.form.save()
            return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        """Get the url to redirect to upon successful form submission."""
        return self.success_url


class MultiFormView(FormView):

    def __init__(self, request, *args, **kwargs):
        self.forms = {}
        super(MultiFormView, self).__init__(request, *args, **kwargs)

    def get_form(self):
        """
        Set self.forms to a dict of form_class keys to form instances, and
        return None for the value of self.form.
        """
        for form_name, form_class in self.form_classes.items():
            if not self.form_options.get(form_name):
                self.form_options[form_name] = {}
            if self.data:
                self.form_options[form_name].update({'data': self.data})
            if self.files:
                self.form_options[form_name].update({'files': self.files})
            self.forms[form_name] = \
                form_class(**self.form_options[form_name])
        return None

    def process_form(self):
        for form_name in self.form_classes.keys():
            if not self.forms[form_name].is_valid():
                # Return none so that the normal view processing will
                # continue, allowing the user to correct errors.
                return None

        # If all forms are valid, save them and redirect.
        for form_name in self.form_classes.keys():
            self.forms[form_name].save()
        return HttpResponseRedirect(self.get_success_url())

    def uncached_context(self):
        context = super(MultiFormView, self).uncached_context()
        for form_name in self.form_classes.keys():
            context.update({form_name: self.forms[form_name]})
        return context

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# django-baseviews documentation build configuration file, created by
# sphinx-quickstart on Mon Sep 20 23:11:20 2010.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

DOCS_BASE = os.path.dirname(__file__)
sys.path.insert(0, os.path.abspath(os.path.join(DOCS_BASE, '..')))

import baseviews

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))

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
project = u'django-baseviews'
copyright = u'2010, Brandon Konkle'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = baseviews.get_version(short=True)
# The full version, including alpha/beta/rc tags.
release = baseviews.__version__

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
htmlhelp_basename = 'django-baseviewsdoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'django-baseviews.tex', u'django-baseviews Documentation',
   u'Brandon Konkle', 'manual'),
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
    ('index', 'django-baseviews', u'django-baseviews Documentation',
     [u'Brandon Konkle'], 1)
]

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
from django.core.management import execute_manager
try:
    import settings # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
    sys.exit(1)

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = settings
# Django settings for example_project project.
import os, sys
BASE = os.path.dirname(__file__)
sys.path.insert(0, os.path.abspath(os.path.join(BASE, '..')))

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'dev.db',                      # Or path to database file if using sqlite3.
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
TIME_ZONE = 'America/Chicago'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = ''

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'f*4-eku(m4w6-nor)2g!ra%jljga&^sio(au2#mar5kycx4y74'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
)

ROOT_URLCONF = 'test_project.urls'

TEMPLATE_DIRS = (
    os.path.join(BASE, 'templates'),
)

INSTALLED_APPS = (
    'baseviews',
)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

urlpatterns = patterns('test_project.views',
    url(r'^lol/$', 'LolHome'),
    url(r'^ajax/$', 'StrongerThanDirt'),
    url(r'^kitteh/$', 'KittehView'),
    url(r'^monorail/$', 'MonorailCatTicketsView'),
)

########NEW FILE########
__FILENAME__ = views
from django import forms
from baseviews.views import BasicView, AjaxView, FormView, MultiFormView


class LolHome(BasicView):
    template = 'home.html'
    
    def get_context(self):
        return {'verb': 'haz', 'noun': 'cheezburger'}


class StrongerThanDirt(AjaxView):

    def get_context(self):
        return {'armed': '...with Ajax!'}


class KittehForm(forms.Form):
    caption = forms.CharField()

    def save(self):
        pass


class KittehView(FormView):
    template = 'kitteh.html'
    form_class = KittehForm
    success_url = '/pewpewpew/'


class GoggieForm(forms.Form):
    bark = forms.CharField()

    def save(self):
        pass


class MonorailCatTicketsView(MultiFormView):
    template = 'monorail.html'
    form_classes = {'kitteh_form': KittehForm,
                    'goggie_form': GoggieForm}
    success_url = '/derailed/'

########NEW FILE########
