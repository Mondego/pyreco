__FILENAME__ = models
# only for unittest

########NEW FILE########
__FILENAME__ = wysiwyg
from django import template
from django.conf import settings
from django.template.loader import render_to_string

try:
    from urlparse import urljoin
except ImportError:
    from urllib.parse import urljoin

register = template.Library()

def get_settings():
    """Utility function to retrieve settings.py values with defaults"""
    flavor = getattr(settings, "DJANGO_WYSIWYG_FLAVOR", "yui")

    return {
        "DJANGO_WYSIWYG_MEDIA_URL": getattr(settings, "DJANGO_WYSIWYG_MEDIA_URL", urljoin(settings.STATIC_URL, flavor) + '/'),
        "DJANGO_WYSIWYG_FLAVOR":    flavor,
    }


@register.simple_tag
def wysiwyg_setup(protocol="http"):
    """
    Create the <style> and <script> tags needed to initialize the rich text editor.

    Create a local django_wysiwyg/includes.html template if you don't want to use Yahoo's CDN
    """

    ctx = {
        "protocol": protocol,
    }
    ctx.update(get_settings())

    return render_to_string(
        "django_wysiwyg/%s/includes.html" % ctx['DJANGO_WYSIWYG_FLAVOR'],
        ctx
    )


@register.simple_tag
def wysiwyg_editor(field_id, editor_name=None, config=None):
    """
    Turn the textarea #field_id into a rich editor. If you do not specify the
    JavaScript name of the editor, it will be derived from the field_id.

    If you don't specify the editor_name then you'll have a JavaScript object
    named "<field_id>_editor" in the global namespace. We give you control of
    this in case you have a complex JS ctxironment.
    """

    if not editor_name:
        editor_name = "%s_editor" % field_id

    ctx = {
        'field_id':     field_id,
        'editor_name':  editor_name,
        'config': config
    }
    ctx.update(get_settings())

    return render_to_string(
        "django_wysiwyg/%s/editor_instance.html" % ctx['DJANGO_WYSIWYG_FLAVOR'],
        ctx
    )


@register.simple_tag
def wysiwyg_static_url(appname, prefix, default_path):
    """
    Automatically use an prefix if a given application is installed.
    For example, if django-ckeditor is installed, use it's STATIC_URL/ckeditor folder to find the CKEditor distribution.
    When the application does not available, fallback to the default path.

    This is a function for the internal templates of *django-wysiwyg*.
    """
    if appname in settings.INSTALLED_APPS:
        return urljoin(settings.STATIC_URL, prefix)
    else:
        return default_path

########NEW FILE########
__FILENAME__ = utils
"""
Utilities for cleaning HTML code.
"""

def clean_html(*args, **kwargs):
    raise ImportError("clean_html requires html5lib or pytidylib")

def sanitize_html(*args, **kwargs):
    raise ImportError("sanitize_html requires html5lib")

def clean_html5lib(input):
    """
    Takes an HTML fragment and processes it using html5lib to ensure that the HTML is well-formed.

    >>> clean_html5lib("<p>Foo<b>bar</b></p>")
    u'<p>Foo<b>bar</b></p>'
    >>> clean_html5lib("<p>Foo<b>bar</b><i>Ooops!</p>")
    u'<p>Foo<b>bar</b><i>Ooops!</i></p>'
    >>> clean_html5lib('<p>Foo<b>bar</b>& oops<a href="#foo&bar">This is a <>link</a></p>')
    u'<p>Foo<b>bar</b>&amp; oops<a href=#foo&amp;bar>This is a &lt;&gt;link</a></p>'
    """
    from html5lib import treebuilders, treewalkers, serializer, sanitizer

    p = html5lib.HTMLParser(tree=treebuilders.getTreeBuilder("dom"))
    dom_tree = p.parseFragment(input)
    walker = treewalkers.getTreeWalker("dom")
    stream = walker(dom_tree)

    s = serializer.htmlserializer.HTMLSerializer(omit_optional_tags=False)
    return "".join(s.serialize(stream))

def sanitize_html5lib(input):
    """
    Removes any unwanted HTML tags and attributes, using html5lib.

    >>> sanitize_html5lib("foobar<p>adf<i></p>abc</i>")
    u'foobar<p>adf<i></i></p><i>abc</i>'
    >>> sanitize_html5lib('foobar<p style="color:red; remove:me; background-image: url(http://example.com/test.php?query_string=bad);">adf<script>alert("Uhoh!")</script><i></p>abc</i>')
    u'foobar<p style="color: red;">adf&lt;script&gt;alert("Uhoh!")&lt;/script&gt;<i></i></p><i>abc</i>'
    """
    from html5lib import treebuilders, treewalkers, serializer, sanitizer

    p = html5lib.HTMLParser(tokenizer=sanitizer.HTMLSanitizer, tree=treebuilders.getTreeBuilder("dom"))
    dom_tree = p.parseFragment(input)
    walker = treewalkers.getTreeWalker("dom")
    stream = walker(dom_tree)

    s = serializer.htmlserializer.HTMLSerializer(omit_optional_tags=False)
    return "".join(s.serialize(stream))

def clean_pytidylib(input):
    (cleaned_html, warnings) = tidylib.tidy_document(input)
    return cleaned_html

try:
    import html5lib
    clean_html,  sanitize_html = clean_html5lib, sanitize_html5lib
except ImportError:
    try:
        import tidylib
        clean_html = clean_pytidylib
    except ImportError:
        pass

if __name__ == "__main__":
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# django-wysiwyg documentation build configuration file, created by
# sphinx-quickstart on Wed Apr  6 10:47:56 2011.
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
extensions = []

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'django-wysiwyg'
copyright = u'2011, Daniel Greenfeld, Chris Adams, and contributors'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.5.1'
# The full version, including alpha/beta/rc tags.
release = '0.5.1'

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
htmlhelp_basename = 'django-wysiwygdoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'django-wysiwyg.tex', u'django-wysiwyg Documentation',
   u'Daniel Greenfeld, Chris Adams, and contributors', 'manual'),
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
    ('index', 'django-wysiwyg', u'django-wysiwyg Documentation',
     [u'Daniel Greenfeld, Chris Adams, and contributors'], 1)
]

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin

from .models import Playground, FancyPlayground


class CartWheelAdmin(admin.ModelAdmin):
    change_form_template = 'fun/admin/playground/change_form.html'


class FancyCartWheelAdmin(admin.ModelAdmin):
    change_form_template = 'fun/admin/fancyplayground/change_form.html'


admin.site.register(Playground, CartWheelAdmin)
admin.site.register(FancyPlayground, FancyCartWheelAdmin)

########NEW FILE########
__FILENAME__ = models
from django.db import models


class Playground(models.Model):
    body = models.TextField()


class FancyPlayground(models.Model):
    title = models.CharField(max_length=100)
    body = models.TextField()

########NEW FILE########
__FILENAME__ = tests

########NEW FILE########
__FILENAME__ = views

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python

import sys
import os

sys.path.append(os.path.realpath(os.path.join(os.path.dirname(__file__), "..")))

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
# Django settings for test_project project.
from __future__ import print_function
import os
import sys

PROJECT_ROOT = os.path.dirname(__file__)

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASE_ENGINE = 'sqlite3'
DATABASE_NAME = os.path.join(PROJECT_ROOT, 'dev.db')
DATABASE_USER = ''
DATABASE_PASSWORD = ''
DATABASE_HOST = ''
DATABASE_PORT = ''

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
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

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = os.path.join(PROJECT_ROOT, 'media')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = '/media/'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/admin_media/' # Set this so our files can use /media/

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'v!y*k!pa947m205&g*ih*a20651l=-gagc_$ntdjt9$_g85c=!'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = ('django.template.loaders.filesystem.Loader',
                    'django.template.loaders.app_directories.Loader')

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    "django.middleware.csrf.CsrfViewMiddleware",
    'django.contrib.auth.middleware.AuthenticationMiddleware',

)

ROOT_URLCONF = 'test_project.urls'

TEMPLATE_DIRS = (os.path.join(PROJECT_ROOT, "templates"), )

INSTALLED_APPS = (
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.sites",
    "django.contrib.messages",
    "test_project.fun",
    'django_wysiwyg'
)

DJANGO_WYSIWYG_FLAVOR = 'yui'       # Default
# DJANGO_WYSIWYG_FLAVOR = 'ckeditor'  # Requires you to also place the ckeditor files here:
# NOTE: If you are using DJANGO 1.3, you will want to follow the docs and use
# STATIC_URL instead of MEDIA_URL here.
# DJANGO_WYSIWYG_MEDIA_URL = "%s/ckeditor" % MEDIA_URL


# Support newer Django versions:
import django
if django.VERSION >= (1,3):
    STATIC_ROOT = os.path.join(PROJECT_ROOT, 'static')
    STATIC_URL = '/static/'

    ADMIN_MEDIA_PREFIX = '/static/admin/'

    INSTALLED_APPS += (
        "django.contrib.staticfiles",
    )

    DATABASES = {
        'default': {
            'ENGINE':   'django.db.backends.' + DATABASE_ENGINE,
            'NAME':     DATABASE_NAME,
            'USER':     DATABASE_USER,
            'PASSWORD': DATABASE_PASSWORD,
            'HOST':     DATABASE_HOST,
            'PORT':     DATABASE_PORT,
        },
    }


# Auto configure resources for editor flavors:
if 'tinymce' in DJANGO_WYSIWYG_FLAVOR:
    print("NOTE: Adding 'tinymce' to INSTALLED_APPS")
    INSTALLED_APPS += (
        'tinymce',
    )
elif 'ckeditor' in DJANGO_WYSIWYG_FLAVOR:
    print("NOTE: Adding 'ckeditor' to INSTALLED_APPS")
    INSTALLED_APPS += (
        'ckeditor',
    )
    CKEDITOR_UPLOAD_PATH = MEDIA_ROOT


########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from django.conf import settings

from django.contrib import admin
admin.autodiscover()

from views import basic_test

urlpatterns = patterns('',
    (r'^media/(?P<path>.*)$', 'django.views.static.serve',
            { 'document_root': settings.MEDIA_ROOT }
        ),
    ('^$', basic_test),
    url(r"^admin/", include(admin.site.urls)),    
)

########NEW FILE########
__FILENAME__ = views
from django.shortcuts import render_to_response

def basic_test(request):
    return render_to_response("basic_test.html")

########NEW FILE########
