__FILENAME__ = bootstrap
##############################################################################
#
# Copyright (c) 2006 Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Bootstrap a buildout-based project

Simply run this script in a directory containing a buildout.cfg.
The script accepts buildout command-line options, so you can
use the -c option to specify an alternate configuration file.
"""

import os
import shutil
import sys
import tempfile

from optparse import OptionParser

tmpeggs = tempfile.mkdtemp()

usage = '''\
[DESIRED PYTHON FOR BUILDOUT] bootstrap.py [options]

Bootstraps a buildout-based project.

Simply run this script in a directory containing a buildout.cfg, using the
Python that you want bin/buildout to use.

Note that by using --find-links to point to local resources, you can keep 
this script from going over the network.
'''

parser = OptionParser(usage=usage)
parser.add_option("-v", "--version", help="use a specific zc.buildout version")

parser.add_option("-t", "--accept-buildout-test-releases",
                  dest='accept_buildout_test_releases',
                  action="store_true", default=False,
                  help=("Normally, if you do not specify a --version, the "
                        "bootstrap script and buildout gets the newest "
                        "*final* versions of zc.buildout and its recipes and "
                        "extensions for you.  If you use this flag, "
                        "bootstrap and buildout will get the newest releases "
                        "even if they are alphas or betas."))
parser.add_option("-c", "--config-file",
                  help=("Specify the path to the buildout configuration "
                        "file to be used."))
parser.add_option("-f", "--find-links",
                  help=("Specify a URL to search for buildout releases"))


options, args = parser.parse_args()

######################################################################
# load/install setuptools

to_reload = False
try:
    import pkg_resources
    import setuptools
except ImportError:
    ez = {}

    try:
        from urllib.request import urlopen
    except ImportError:
        from urllib2 import urlopen

    # XXX use a more permanent ez_setup.py URL when available.
    exec(urlopen('https://bitbucket.org/pypa/setuptools/raw/0.7.2/ez_setup.py'
                ).read(), ez)
    setup_args = dict(to_dir=tmpeggs, download_delay=0)
    ez['use_setuptools'](**setup_args)

    if to_reload:
        reload(pkg_resources)
    import pkg_resources
    # This does not (always?) update the default working set.  We will
    # do it.
    for path in sys.path:
        if path not in pkg_resources.working_set.entries:
            pkg_resources.working_set.add_entry(path)

######################################################################
# Install buildout

ws = pkg_resources.working_set

cmd = [sys.executable, '-c',
       'from setuptools.command.easy_install import main; main()',
       '-mZqNxd', tmpeggs]

find_links = os.environ.get(
    'bootstrap-testing-find-links',
    options.find_links or
    ('http://downloads.buildout.org/'
     if options.accept_buildout_test_releases else None)
    )
if find_links:
    cmd.extend(['-f', find_links])

setuptools_path = ws.find(
    pkg_resources.Requirement.parse('setuptools')).location

requirement = 'zc.buildout'
version = options.version
if version is None and not options.accept_buildout_test_releases:
    # Figure out the most recent final version of zc.buildout.
    import setuptools.package_index
    _final_parts = '*final-', '*final'

    def _final_version(parsed_version):
        for part in parsed_version:
            if (part[:1] == '*') and (part not in _final_parts):
                return False
        return True
    index = setuptools.package_index.PackageIndex(
        search_path=[setuptools_path])
    if find_links:
        index.add_find_links((find_links,))
    req = pkg_resources.Requirement.parse(requirement)
    if index.obtain(req) is not None:
        best = []
        bestv = None
        for dist in index[req.project_name]:
            distv = dist.parsed_version
            if _final_version(distv):
                if bestv is None or distv > bestv:
                    best = [dist]
                    bestv = distv
                elif distv == bestv:
                    best.append(dist)
        if best:
            best.sort()
            version = best[-1].version
if version:
    requirement = '=='.join((requirement, version))
cmd.append(requirement)

import subprocess
if subprocess.call(cmd, env=dict(os.environ, PYTHONPATH=setuptools_path)) != 0:
    raise Exception(
        "Failed to execute command:\n%s",
        repr(cmd)[1:-1])

######################################################################
# Import and run buildout

ws.add_entry(tmpeggs)
ws.require(requirement)
import zc.buildout.buildout

if not [a for a in args if '=' not in a]:
    args.append('bootstrap')

# if -c was provided, we push it back into args for buildout' main function
if options.config_file is not None:
    args[0:0] = ['-c', options.config_file]

zc.buildout.buildout.main(args)
shutil.rmtree(tmpeggs)

########NEW FILE########
__FILENAME__ = settings
"""Settings for Zinnia Demo"""
import os

gettext = lambda s: s

DEBUG = True
TEMPLATE_DEBUG = DEBUG

DATABASES = {'default':
             {'ENGINE': 'django.db.backends.sqlite3',
              'NAME': os.path.join(os.path.dirname(__file__), 'demo.db')}
             }

TIME_ZONE = 'Europe/Paris'

STATIC_URL = '/static/'

MEDIA_URL = '/media/'

SECRET_KEY = 'jo-1rzm(%sf)3#n+fb7h955yu$3(pt63abhi12_t7e^^5q8dyw'

USE_TZ = True
USE_I18N = True
USE_L10N = True

SITE_ID = 1

LANGUAGE_CODE = 'en'

LANGUAGES = (
    ('en', gettext('English')),
    ('fr', gettext('French')),
    ('de', gettext('German')),
    ('es', gettext('Spanish')),
    ('it', gettext('Italian')),
    ('nl', gettext('Dutch')),
    ('sl', gettext('Slovenian')),
    ('bg', gettext('Bulgarian')),
    ('hu', gettext('Hungarian')),
    ('cs', gettext('Czech')),
    ('sk', gettext('Slovak')),
    ('lt', gettext('Lithuanian')),
    ('ru', gettext('Russian')),
    ('pl', gettext('Polish')),
    ('eu', gettext('Basque')),
    ('he', gettext('Hebrew')),
    ('ca', gettext('Catalan')),
    ('tr', gettext('Turkish')),
    ('sv', gettext('Swedish')),
    ('hr_HR', gettext('Croatian')),
    ('pt_BR', gettext('Brazilian Portuguese')),
    ('fa_IR', gettext('Persian')),
    ('fi_FI', gettext('Finnish')),
    ('zh_CN', gettext('Simplified Chinese')),
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.admindocs.middleware.XViewMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

ROOT_URLCONF = 'demo.urls'

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.i18n',
    'django.core.context_processors.request',
    'django.contrib.messages.context_processors.messages',
    'zinnia.context_processors.version',
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.sitemaps',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.sites',
    'django.contrib.admin',
    'django.contrib.admindocs',
    'django.contrib.staticfiles',
    'django_comments',
    'django_xmlrpc',
    'mptt',
    'south',
    'tagging',
    'zinnia'
)

from zinnia.xmlrpc import ZINNIA_XMLRPC_METHODS
XMLRPC_METHODS = ZINNIA_XMLRPC_METHODS

########NEW FILE########
__FILENAME__ = urls
"""Urls for the demo of Zinnia"""
from django.conf import settings
from django.contrib import admin
from django.conf.urls import url
from django.conf.urls import include
from django.conf.urls import patterns
from django.views.generic.base import RedirectView

from zinnia.sitemaps import TagSitemap
from zinnia.sitemaps import EntrySitemap
from zinnia.sitemaps import CategorySitemap
from zinnia.sitemaps import AuthorSitemap

admin.autodiscover()

urlpatterns = patterns(
    '',
    url(r'^$', RedirectView.as_view(url='/blog/')),
    url(r'^blog/', include('zinnia.urls', namespace='zinnia')),
    url(r'^comments/', include('django_comments.urls')),
    url(r'^xmlrpc/$', 'django_xmlrpc.views.handle_xmlrpc'),
    url(r'^i18n/', include('django.conf.urls.i18n')),
    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
    url(r'^admin/', include(admin.site.urls)),
)

sitemaps = {
    'tags': TagSitemap,
    'blog': EntrySitemap,
    'authors': AuthorSitemap,
    'categories': CategorySitemap
}

urlpatterns += patterns(
    'django.contrib.sitemaps.views',
    url(r'^sitemap.xml$', 'index',
        {'sitemaps': sitemaps}),
    url(r'^sitemap-(?P<section>.+)\.xml$', 'sitemap',
        {'sitemaps': sitemaps}),
)

urlpatterns += patterns(
    '',
    url(r'^400/$', 'django.views.defaults.bad_request'),
    url(r'^403/$', 'django.views.defaults.permission_denied'),
    url(r'^404/$', 'django.views.defaults.page_not_found'),
    url(r'^500/$', 'django.views.defaults.server_error'),
)

if settings.DEBUG:
    urlpatterns += patterns(
        '',
        url(r'^media/(?P<path>.*)$', 'django.views.static.serve',
            {'document_root': settings.MEDIA_ROOT})
    )

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# django-blog-zinnia documentation build configuration file, created by
# sphinx-quickstart on Thu Oct 21 17:44:20 2010.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.
import os
import sys
import re
from datetime import date

HERE = os.path.abspath(os.path.dirname(__file__))

sys.path.append(HERE)
sys.path.append(os.path.join(HERE, '..'))
os.environ['DJANGO_SETTINGS_MODULE'] = 'extensions.settings'

from django.core.management import call_command
call_command('syncdb', verbosity=0, interactive=False)

import zinnia

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc',
              'sphinx.ext.intersphinx',
              'extensions.zinnia_docs']

intersphinx_mapping = {
    'django': ('http://readthedocs.org/docs/django/en/latest/', None),
    }

# Add any paths that contain templates here, relative to this directory.
#templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = 'Django Blog Zinnia'
copyright = '%s, %s' % (date.today().year, zinnia.__author__)

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#

# The full version, including alpha/beta/rc tags.
release = zinnia.__version__

# The short X.Y version.
version = re.match(r'\d+\.\d+(?:\.\d+)?', release).group()

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
exclude_patterns = ['build']

# The reST default role (used for this markup: `text`) to use for all documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
add_function_parentheses = True

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

# For using default theme on RTFD
html_style = 'default.css'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
text_color = '#33333'
link_color = '#0066AA'
box_color = '#e9e9f3'
background_color = '#FFF'
text_font = "Arial, Helvetica, sans-serif"

html_theme_options = {
    'footerbgcolor': background_color,
    'footertextcolor': text_color,
    'sidebarbgcolor': background_color,
    'sidebartextcolor': text_color,
    'sidebarlinkcolor': link_color,
    'relbarbgcolor': background_color,
    'relbartextcolor': text_color,
    'relbarlinkcolor': link_color,
    'bgcolor': background_color,
    'textcolor': text_color,
    'linkcolor': link_color,
    'visitedlinkcolor': link_color,
    'headbgcolor': box_color,
    'headtextcolor': link_color,
    'headlinkcolor': link_color,
    'codebgcolor': box_color,
    'bodyfont': text_font,
    'headfont': text_font,
    'sidebarwidth': 210,
}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
html_logo = 'logo.png'

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
html_favicon = 'favicon.ico'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['static']

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
htmlhelp_basename = 'django-blog-zinniadoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'django-blog-zinnia.tex', 'django-blog-zinnia Documentation',
   'Fantomas42', 'manual'),
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
    ('index', 'django-blog-zinnia', 'django-blog-zinnia Documentation',
     ['Fantomas42'], 1)
]

########NEW FILE########
__FILENAME__ = settings
"""Settings for Zinnia documentation"""
from zinnia.xmlrpc import ZINNIA_XMLRPC_METHODS

DATABASES = {'default': {'NAME': ':memory:',
                         'ENGINE': 'django.db.backends.sqlite3'}}

SITE_ID = 1

STATIC_URL = '/static/'

SECRET_KEY = 'secret-key'
AKISMET_SECRET_API_KEY = 'AKISMET_API_KEY'
TYPEPAD_SECRET_API_KEY = 'TYPEPAD_API_KEY'
BITLY_LOGIN = 'BITLY_LOGIN'
BITLY_API_KEY = 'BITLY_API_KEY'
MOLLOM_PUBLIC_KEY = 'MOLLOM_PUBLIC_KEY'
MOLLOM_PRIVATE_KEY = 'MOLLOM_PRIVATE_KEY'

INSTALLED_APPS = [
    'django.contrib.sites',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.admin',
    'django.contrib.auth',
    'django_comments',
    'django_xmlrpc',
    'mptt', 'tagging', 'zinnia']

########NEW FILE########
__FILENAME__ = zinnia_docs
"""
Extensions for the Sphinx documation of Zinnia

Inspired, stealed and needed for
cross linking the django documentation.
"""
import inspect

from django.db import models
from django.utils.html import strip_tags
from django.utils.encoding import force_unicode


def skip_model_member(app, what, name, obj, skip, options):
    # These fields always fails !
    if name in ('tags', 'image'):
        return True
    return skip


def process_model_docstring(app, what, name, obj, options, lines):
    if inspect.isclass(obj) and issubclass(obj, models.Model):
        for field in obj._meta.fields:
            # Decode and strip any html out of the field's help text
            help_text = strip_tags(force_unicode(field.help_text))
            # Decode and capitalize the verbose name, for use if there isn't
            # any help text
            verbose_name = force_unicode(field.verbose_name).capitalize()

            if help_text:
                lines.append(':param %s: %s' % (field.attname, help_text))
            else:
                lines.append(':param %s: %s' % (field.attname, verbose_name))
            # Add the field's type to the docstring
            lines.append(':type %s: %s' % (field.attname,
                                           type(field).__name__))
    # Return the extended docstring
    return lines


def setup(app):
    app.add_crossref_type(
        directivename = 'setting',
        rolename      = 'setting',
        indextemplate = 'pair: %s; setting',
    )
    app.add_crossref_type(
        directivename = 'templatetag',
        rolename      = 'ttag',
        indextemplate = 'pair: %s; template tag'
    )
    app.add_crossref_type(
        directivename = 'templatefilter',
        rolename      = 'tfilter',
        indextemplate = 'pair: %s; template filter'
    )
    app.connect('autodoc-process-docstring',
                process_model_docstring)
    app.connect('autodoc-skip-member',
                skip_model_member)

########NEW FILE########
__FILENAME__ = category
"""CategoryAdmin for Zinnia"""
from django.contrib import admin
from django.core.urlresolvers import NoReverseMatch
from django.utils.translation import ugettext_lazy as _

from zinnia.admin.forms import CategoryAdminForm


class CategoryAdmin(admin.ModelAdmin):
    """
    Admin for Category model.
    """
    form = CategoryAdminForm
    fields = ('title', 'parent', 'description', 'slug')
    list_display = ('title', 'slug', 'get_tree_path', 'description')
    prepopulated_fields = {'slug': ('title', )}
    search_fields = ('title', 'description')
    list_filter = ('parent',)

    def __init__(self, model, admin_site):
        self.form.admin_site = admin_site
        super(CategoryAdmin, self).__init__(model, admin_site)

    def get_tree_path(self, category):
        """
        Return the category's tree path in HTML.
        """
        try:
            return '<a href="%s" target="blank">/%s/</a>' % \
                   (category.get_absolute_url(), category.tree_path)
        except NoReverseMatch:
            return '/%s/' % category.tree_path
    get_tree_path.allow_tags = True
    get_tree_path.short_description = _('tree path')

########NEW FILE########
__FILENAME__ = entry
"""EntryAdmin for Zinnia"""
from django.forms import Media
from django.contrib import admin
from django.db.models import Q
from django.conf.urls import url
from django.conf.urls import patterns
from django.utils import timezone
from django.utils.text import Truncator
from django.utils.html import strip_tags
from django.core.urlresolvers import reverse
from django.core.urlresolvers import NoReverseMatch
from django.views.decorators.csrf import csrf_exempt
from django.utils.translation import get_language
from django.template.response import TemplateResponse
from django.utils.translation import ungettext_lazy
from django.utils.translation import ugettext_lazy as _
from django.contrib.staticfiles.storage import staticfiles_storage

from zinnia import settings
from zinnia.managers import HIDDEN
from zinnia.managers import PUBLISHED
from zinnia.settings import PROTOCOL
from zinnia.models.author import Author
from zinnia.ping import DirectoryPinger
from zinnia.admin.forms import EntryAdminForm
from zinnia.admin.filters import AuthorListFilter
from zinnia.admin.filters import CategoryListFilter


class EntryAdmin(admin.ModelAdmin):
    """
    Admin for Entry model.
    """
    form = EntryAdminForm
    date_hierarchy = 'creation_date'
    fieldsets = (
        (_('Content'), {
            'fields': (('title', 'status'), 'content', 'image')}),
        (_('Publication'), {
            'fields': (('start_publication', 'end_publication'),
                       'creation_date', 'sites'),
            'classes': ('collapse', 'collapse-closed')}),
        (_('Discussions'), {
            'fields': ('comment_enabled', 'pingback_enabled',
                       'trackback_enabled'),
            'classes': ('collapse', 'collapse-closed')}),
        (_('Privacy'), {
            'fields': ('login_required', 'password'),
            'classes': ('collapse', 'collapse-closed')}),
        (_('Templates'), {
            'fields': ('content_template', 'detail_template'),
            'classes': ('collapse', 'collapse-closed')}),
        (_('Metadatas'), {
            'fields': ('featured', 'excerpt', 'authors', 'related'),
            'classes': ('collapse', 'collapse-closed')}),
        (None, {'fields': ('categories', 'tags', 'slug')}))
    list_filter = (CategoryListFilter, AuthorListFilter, 'status', 'featured',
                   'login_required', 'comment_enabled', 'pingback_enabled',
                   'trackback_enabled', 'creation_date', 'start_publication',
                   'end_publication', 'sites')
    list_display = ('get_title', 'get_authors', 'get_categories',
                    'get_tags', 'get_sites', 'get_is_visible', 'featured',
                    'get_short_url', 'creation_date')
    radio_fields = {'content_template': admin.VERTICAL,
                    'detail_template': admin.VERTICAL}
    filter_horizontal = ('categories', 'authors', 'related')
    prepopulated_fields = {'slug': ('title', )}
    search_fields = ('title', 'excerpt', 'content', 'tags')
    actions = ['make_mine', 'make_published', 'make_hidden',
               'close_comments', 'close_pingbacks', 'close_trackbacks',
               'ping_directories', 'put_on_top',
               'mark_featured', 'unmark_featured']
    actions_on_top = True
    actions_on_bottom = True

    def __init__(self, model, admin_site):
        self.form.admin_site = admin_site
        super(EntryAdmin, self).__init__(model, admin_site)

    # Custom Display
    def get_title(self, entry):
        """
        Return the title with word count and number of comments.
        """
        title = _('%(title)s (%(word_count)i words)') % \
            {'title': entry.title, 'word_count': entry.word_count}
        reaction_count = int(entry.comment_count +
                             entry.pingback_count +
                             entry.trackback_count)
        if reaction_count:
            return ungettext_lazy(
                '%(title)s (%(reactions)i reaction)',
                '%(title)s (%(reactions)i reactions)', reaction_count) % \
                {'title': title,
                 'reactions': reaction_count}
        return title
    get_title.short_description = _('title')

    def get_authors(self, entry):
        """
        Return the authors in HTML.
        """
        try:
            authors = ['<a href="%s" target="blank">%s</a>' %
                       (author.get_absolute_url(),
                        getattr(author, author.USERNAME_FIELD))
                       for author in entry.authors.all()]
        except NoReverseMatch:
            authors = [getattr(author, author.USERNAME_FIELD)
                       for author in entry.authors.all()]
        return ', '.join(authors)
    get_authors.allow_tags = True
    get_authors.short_description = _('author(s)')

    def get_categories(self, entry):
        """
        Return the categories linked in HTML.
        """
        try:
            categories = ['<a href="%s" target="blank">%s</a>' %
                          (category.get_absolute_url(), category.title)
                          for category in entry.categories.all()]
        except NoReverseMatch:
            categories = [category.title for category in
                          entry.categories.all()]
        return ', '.join(categories)
    get_categories.allow_tags = True
    get_categories.short_description = _('category(s)')

    def get_tags(self, entry):
        """
        Return the tags linked in HTML.
        """
        try:
            return ', '.join(['<a href="%s" target="blank">%s</a>' %
                              (reverse('zinnia:tag_detail', args=[tag]), tag)
                              for tag in entry.tags_list])
        except NoReverseMatch:
            return entry.tags
    get_tags.allow_tags = True
    get_tags.short_description = _('tag(s)')

    def get_sites(self, entry):
        """
        Return the sites linked in HTML.
        """
        try:
            index_url = reverse('zinnia:entry_archive_index')
        except NoReverseMatch:
            index_url = ''
        return ', '.join(
            ['<a href="%s://%s%s" target="blank">%s</a>' %
             (PROTOCOL, site.domain, index_url, site.name)
             for site in entry.sites.all()])
    get_sites.allow_tags = True
    get_sites.short_description = _('site(s)')

    def get_short_url(self, entry):
        """
        Return the short url in HTML.
        """
        try:
            short_url = entry.short_url
        except NoReverseMatch:
            short_url = entry.get_absolute_url()
        return '<a href="%(url)s" target="blank">%(url)s</a>' % \
               {'url': short_url}
    get_short_url.allow_tags = True
    get_short_url.short_description = _('short url')

    def get_is_visible(self, entry):
        """
        Admin wrapper for entry.is_visible.
        """
        return entry.is_visible
    get_is_visible.boolean = True
    get_is_visible.short_description = _('is visible')

    # Custom Methods
    def save_model(self, request, entry, form, change):
        """
        Save the authors, update time, make an excerpt.
        """
        if not entry.excerpt and entry.status == PUBLISHED:
            entry.excerpt = Truncator(strip_tags(entry.content)).words(50)

        if entry.pk and not request.user.has_perm('zinnia.can_change_author'):
            form.cleaned_data['authors'] = entry.authors.all()

        if not entry.pk and not form.cleaned_data.get('authors'):
            form.cleaned_data['authors'] = Author.objects.filter(
                pk=request.user.pk)

        entry.last_update = timezone.now()
        entry.save()

    def get_queryset(self, request):
        """
        Make special filtering by user's permissions.
        """
        if not request.user.has_perm('zinnia.can_view_all'):
            queryset = request.user.entries.all()
        else:
            queryset = super(EntryAdmin, self).get_queryset(request)
        return queryset.prefetch_related('categories', 'authors', 'sites')

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        """
        Filter the disposable authors.
        """
        if db_field.name == 'authors':
            if request.user.has_perm('zinnia.can_change_author'):
                kwargs['queryset'] = Author.objects.filter(
                    Q(is_staff=True) | Q(entries__isnull=False)
                    ).distinct()
            else:
                kwargs['queryset'] = Author.objects.filter(pk=request.user.pk)

        return super(EntryAdmin, self).formfield_for_manytomany(
            db_field, request, **kwargs)

    def get_readonly_fields(self, request, obj=None):
        """
        Return readonly fields by user's permissions.
        """
        readonly_fields = super(EntryAdmin, self).get_readonly_fields(
            request, obj)
        if not request.user.has_perm('zinnia.can_change_status'):
            readonly_fields = list(readonly_fields)
            readonly_fields.append('status')
        return readonly_fields

    def get_actions(self, request):
        """
        Define actions by user's permissions.
        """
        actions = super(EntryAdmin, self).get_actions(request)
        if not actions:
            return actions
        if (not request.user.has_perm('zinnia.can_change_author') or
                not request.user.has_perm('zinnia.can_view_all')):
            del actions['make_mine']
        if not request.user.has_perm('zinnia.can_change_status'):
            del actions['make_hidden']
            del actions['make_published']
        if not settings.PING_DIRECTORIES:
            del actions['ping_directories']

        return actions

    # Custom Actions
    def make_mine(self, request, queryset):
        """
        Set the entries to the current user.
        """
        for entry in queryset:
            if request.user not in entry.authors.all():
                entry.authors.add(request.user)
        self.message_user(
            request, _('The selected entries now belong to you.'))
    make_mine.short_description = _('Set the entries to the user')

    def make_published(self, request, queryset):
        """
        Set entries selected as published.
        """
        queryset.update(status=PUBLISHED)
        self.ping_directories(request, queryset, messages=False)
        self.message_user(
            request, _('The selected entries are now marked as published.'))
    make_published.short_description = _('Set entries selected as published')

    def make_hidden(self, request, queryset):
        """
        Set entries selected as hidden.
        """
        queryset.update(status=HIDDEN)
        self.message_user(
            request, _('The selected entries are now marked as hidden.'))
    make_hidden.short_description = _('Set entries selected as hidden')

    def close_comments(self, request, queryset):
        """
        Close the comments for selected entries.
        """
        queryset.update(comment_enabled=False)
        self.message_user(
            request, _('Comments are now closed for selected entries.'))
    close_comments.short_description = _('Close the comments for '
                                         'selected entries')

    def close_pingbacks(self, request, queryset):
        """
        Close the pingbacks for selected entries.
        """
        queryset.update(pingback_enabled=False)
        self.message_user(
            request, _('Pingbacks are now closed for selected entries.'))
    close_pingbacks.short_description = _(
        'Close the pingbacks for selected entries')

    def close_trackbacks(self, request, queryset):
        """
        Close the trackbacks for selected entries.
        """
        queryset.update(trackback_enabled=False)
        self.message_user(
            request, _('Trackbacks are now closed for selected entries.'))
    close_trackbacks.short_description = _(
        'Close the trackbacks for selected entries')

    def put_on_top(self, request, queryset):
        """
        Put the selected entries on top at the current date.
        """
        queryset.update(creation_date=timezone.now())
        self.ping_directories(request, queryset, messages=False)
        self.message_user(request, _(
            'The selected entries are now set at the current date.'))
    put_on_top.short_description = _(
        'Put the selected entries on top at the current date')

    def mark_featured(self, request, queryset):
        """
        Mark selected as featured post.
        """
        queryset.update(featured=True)
        self.message_user(
            request, _('Selected entries are now marked as featured.'))
    mark_featured.short_description = _('Mark selected entries as featured')

    def unmark_featured(self, request, queryset):
        """
        Un-Mark selected featured posts.
        """
        queryset.update(featured=False)
        self.message_user(
            request, _('Selected entries are no longer marked as featured.'))
    unmark_featured.short_description = _(
        'Unmark selected entries as featured')

    def ping_directories(self, request, queryset, messages=True):
        """
        Ping web directories for selected entries.
        """
        for directory in settings.PING_DIRECTORIES:
            pinger = DirectoryPinger(directory, queryset)
            pinger.join()
            if messages:
                success = 0
                for result in pinger.results:
                    if not result.get('flerror', True):
                        success += 1
                    else:
                        self.message_user(request,
                                          '%s : %s' % (directory,
                                                       result['message']))
                if success:
                    self.message_user(
                        request,
                        _('%(directory)s directory succesfully '
                          'pinged %(success)d entries.') %
                        {'directory': directory, 'success': success})
    ping_directories.short_description = _(
        'Ping Directories for selected entries')

    def get_urls(self):
        """
        Overload the admin's urls for WYSIWYG and tag auto-completion.
        """
        entry_admin_urls = super(EntryAdmin, self).get_urls()
        urls = patterns(
            '',
            url(r'^autocomplete_tags/$',
                self.admin_site.admin_view(self.autocomplete_tags),
                name='zinnia_entry_autocomplete_tags'),
            url(r'^wymeditor/$',
                self.admin_site.admin_view(self.wymeditor),
                name='zinnia_entry_wymeditor'),
            url(r'^markitup/$',
                self.admin_site.admin_view(self.markitup),
                name='zinnia_entry_markitup'),
            url(r'^markitup/preview/$',
                self.admin_site.admin_view(self.content_preview),
                name='zinnia_entry_markitup_preview'),)
        return urls + entry_admin_urls

    def autocomplete_tags(self, request):
        """
        View for tag auto-completion.
        """
        return TemplateResponse(
            request, 'admin/zinnia/entry/autocomplete_tags.js',
            content_type='application/javascript')

    def wymeditor(self, request):
        """
        View for serving the config of WYMEditor.
        """
        return TemplateResponse(
            request, 'admin/zinnia/entry/wymeditor.js',
            {'lang': get_language().split('-')[0]},
            content_type='application/javascript')

    def markitup(self, request):
        """
        View for serving the config of MarkItUp.
        """
        return TemplateResponse(
            request, 'admin/zinnia/entry/markitup.js',
            content_type='application/javascript')

    @csrf_exempt
    def content_preview(self, request):
        """
        Admin view to preview Entry.content in HTML,
        useful when using markups to write entries.
        """
        data = request.POST.get('data', '')
        entry = self.model(content=data)
        return TemplateResponse(
            request, 'admin/zinnia/entry/preview.html',
            {'preview': entry.html_content})

    def _media(self):
        """
        The medias needed to enhance the admin page.
        """
        def static_url(url):
            return staticfiles_storage.url('zinnia/%s' % url)

        media = super(EntryAdmin, self).media + Media(
            css={'all': (
                static_url('css/jquery.autocomplete.css'),)},
            js=(static_url('js/jquery.js'),
                static_url('js/jquery.bgiframe.js'),
                static_url('js/jquery.autocomplete.js'),
                reverse('admin:zinnia_entry_autocomplete_tags')))

        if settings.WYSIWYG == 'wymeditor':
            media += Media(
                js=(static_url('js/wymeditor/jquery.wymeditor.pack.js'),
                    static_url('js/wymeditor/plugins/hovertools/'
                               'jquery.wymeditor.hovertools.js'),
                    reverse('admin:zinnia_entry_wymeditor')))
        elif settings.WYSIWYG == 'tinymce':
            from tinymce.widgets import TinyMCE
            media += TinyMCE().media + Media(
                js=(reverse('tinymce-js', args=('admin/zinnia/entry',)),))
        elif settings.WYSIWYG == 'markitup':
            media += Media(
                js=(static_url('js/markitup/jquery.markitup.js'),
                    static_url('js/markitup/sets/%s/set.js' % (
                        settings.MARKUP_LANGUAGE)),
                    reverse('admin:zinnia_entry_markitup')),
                css={'all': (
                    static_url('js/markitup/skins/django/style.css'),
                    static_url('js/markitup/sets/%s/style.css' % (
                        settings.MARKUP_LANGUAGE)))})
        return media
    media = property(_media)

########NEW FILE########
__FILENAME__ = fields
"""Fields for Zinnia admin"""
from django import forms
from django.utils.encoding import smart_text


class MPTTModelChoiceIterator(forms.models.ModelChoiceIterator):
    """
    MPTT version of ModelChoiceIterator.
    """

    def choice(self, obj):
        """
        Overloads the choice method to add the position
        of the object in the tree for future sorting.
        """
        tree_id = getattr(obj, self.queryset.model._mptt_meta.tree_id_attr, 0)
        left = getattr(obj, self.queryset.model._mptt_meta.left_attr, 0)
        return super(MPTTModelChoiceIterator,
                     self).choice(obj) + ((tree_id, left),)


class MPTTModelMultipleChoiceField(forms.ModelMultipleChoiceField):
    """
    MPTT version of ModelMultipleChoiceField.
    """

    def __init__(self, level_indicator='|--', *args, **kwargs):
        self.level_indicator = level_indicator
        super(MPTTModelMultipleChoiceField, self).__init__(*args, **kwargs)

    def label_from_instance(self, obj):
        """
        Create labels which represent the tree level of each node
        when generating option labels.
        """
        label = smart_text(obj)
        prefix = self.level_indicator * getattr(obj, obj._mptt_meta.level_attr)
        if prefix:
            return '%s %s' % (prefix, label)
        return label

    def _get_choices(self):
        """
        Override the _get_choices method to use MPTTModelChoiceIterator.
        """
        return MPTTModelChoiceIterator(self)

    choices = property(_get_choices, forms.ChoiceField._set_choices)

########NEW FILE########
__FILENAME__ = filters
"""Filters for Zinnia admin"""
from django.db.models import Count
from django.utils.encoding import smart_text
from django.contrib.admin import SimpleListFilter
from django.utils.translation import ungettext_lazy
from django.utils.translation import ugettext_lazy as _

from zinnia.models.author import Author
from zinnia.models.category import Category


class RelatedPublishedFilter(SimpleListFilter):
    """
    Base filter for related objects to published entries.
    """
    model = None
    lookup_key = None

    def lookups(self, request, model_admin):
        """
        Return published objects with the number of entries.
        """
        active_objects = self.model.published.all().annotate(
            count_entries_published=Count('entries')).order_by(
            '-count_entries_published', '-pk')
        for active_object in active_objects:
            yield (
                str(active_object.pk), ungettext_lazy(
                    '%(item)s (%(count)i entry)',
                    '%(item)s (%(count)i entries)',
                    active_object.count_entries_published) % {
                    'item': smart_text(active_object),
                    'count': active_object.count_entries_published})

    def queryset(self, request, queryset):
        """
        Return the object's entries if a value is set.
        """
        if self.value():
            params = {self.lookup_key: self.value()}
            return queryset.filter(**params)


class AuthorListFilter(RelatedPublishedFilter):
    """
    List filter for EntryAdmin with published authors only.
    """
    model = Author
    lookup_key = 'authors__id'
    title = _('published authors')
    parameter_name = 'author'


class CategoryListFilter(RelatedPublishedFilter):
    """
    List filter for EntryAdmin about categories
    with published entries.
    """
    model = Category
    lookup_key = 'categories__id'
    title = _('published categories')
    parameter_name = 'category'

########NEW FILE########
__FILENAME__ = forms
"""Forms for Zinnia admin"""
from django import forms
from django.db.models import ManyToOneRel
from django.db.models import ManyToManyRel
from django.contrib.sites.models import Site
from django.utils.translation import ugettext_lazy as _
from django.contrib.admin.widgets import RelatedFieldWidgetWrapper

from mptt.forms import TreeNodeChoiceField

from zinnia.models.entry import Entry
from zinnia.models.category import Category
from zinnia.admin.widgets import MPTTFilteredSelectMultiple
from zinnia.admin.fields import MPTTModelMultipleChoiceField


class CategoryAdminForm(forms.ModelForm):
    """
    Form for Category's Admin.
    """
    parent = TreeNodeChoiceField(
        label=_('Parent category'),
        level_indicator='|--', required=False,
        empty_label=_('No parent category'),
        queryset=Category.objects.all())

    def __init__(self, *args, **kwargs):
        super(CategoryAdminForm, self).__init__(*args, **kwargs)
        rel = ManyToOneRel(Category._meta.get_field('tree_id'),
                           Category, 'id')
        self.fields['parent'].widget = RelatedFieldWidgetWrapper(
            self.fields['parent'].widget, rel, self.admin_site)

    def clean_parent(self):
        """
        Check if category parent is not selfish.
        """
        data = self.cleaned_data['parent']
        if data == self.instance:
            raise forms.ValidationError(
                _('A category cannot be parent of itself.'))
        return data

    class Meta:
        """
        CategoryAdminForm's Meta.
        """
        model = Category
        fields = forms.ALL_FIELDS


class EntryAdminForm(forms.ModelForm):
    """
    Form for Entry's Admin.
    """
    categories = MPTTModelMultipleChoiceField(
        label=_('Categories'), required=False,
        queryset=Category.objects.all(),
        widget=MPTTFilteredSelectMultiple(_('categories'), False,
                                          attrs={'rows': '10'}))

    def __init__(self, *args, **kwargs):
        super(EntryAdminForm, self).__init__(*args, **kwargs)
        rel = ManyToManyRel(Category, 'id')
        self.fields['categories'].widget = RelatedFieldWidgetWrapper(
            self.fields['categories'].widget, rel, self.admin_site)
        self.fields['sites'].initial = [Site.objects.get_current()]

    class Meta:
        """
        EntryAdminForm's Meta.
        """
        model = Entry
        fields = forms.ALL_FIELDS

########NEW FILE########
__FILENAME__ = widgets
"""Widgets for Zinnia admin"""
from itertools import chain

from django.utils import six
from django.utils.html import escape
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.encoding import force_text
from django.contrib.admin import widgets
from django.contrib.staticfiles.storage import staticfiles_storage


class MPTTFilteredSelectMultiple(widgets.FilteredSelectMultiple):
    """
    MPTT version of FilteredSelectMultiple.
    """

    def render_option(self, selected_choices, option_value,
                      option_label, sort_fields):
        """
        Overrides the render_option method to handle
        the sort_fields argument.
        """
        option_value = force_text(option_value)
        option_label = escape(force_text(option_label))

        if option_value in selected_choices:
            selected_html = mark_safe(' selected="selected"')
        else:
            selected_html = ''
        return format_html(
            six.text_type('<option value="{1}"{2} data-tree-id="{3}"'
                          ' data-left-value="{4}">{0}</option>'),
            option_label, option_value, selected_html,
            sort_fields[0], sort_fields[1])

    def render_options(self, choices, selected_choices):
        """
        This is copy'n'pasted from django.forms.widgets Select(Widget)
        change to the for loop and render_option so they will unpack
        and use our extra tuple of mptt sort fields (if you pass in
        some default choices for this field, make sure they have the
        extra tuple too!).
        """
        selected_choices = set(force_text(v) for v in selected_choices)
        output = []
        for option_value, option_label, sort_fields in chain(
                self.choices, choices):
            output.append(self.render_option(
                selected_choices, option_value,
                option_label, sort_fields))
        return '\n'.join(output)

    class Media:
        """
        MPTTFilteredSelectMultiple's Media.
        """
        js = (staticfiles_storage.url('admin/js/core.js'),
              staticfiles_storage.url('zinnia/js/mptt_m2m_selectbox.js'),
              staticfiles_storage.url('admin/js/SelectFilter2.js'))

########NEW FILE########
__FILENAME__ = breadcrumbs
"""Breadcrumb module for Zinnia"""
import re
from functools import wraps
from datetime import datetime

from django.utils.dateformat import format
from django.utils.timezone import is_aware
from django.utils.timezone import localtime
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _


class Crumb(object):
    """
    Part of the breadcrumbs.
    """
    def __init__(self, name, url=None):
        self.name = name
        self.url = url


def year_crumb(creation_date):
    """
    Crumb for a year.
    """
    year = creation_date.strftime('%Y')
    return Crumb(year, reverse('zinnia:entry_archive_year',
                               args=[year]))


def month_crumb(creation_date):
    """
    Crumb for a month.
    """
    year = creation_date.strftime('%Y')
    month = creation_date.strftime('%m')
    month_text = format(creation_date, 'F').capitalize()
    return Crumb(month_text, reverse('zinnia:entry_archive_month',
                                     args=[year, month]))


def day_crumb(creation_date):
    """
    Crumb for a day.
    """
    year = creation_date.strftime('%Y')
    month = creation_date.strftime('%m')
    day = creation_date.strftime('%d')
    return Crumb(day, reverse('zinnia:entry_archive_day',
                              args=[year, month, day]))


def entry_breadcrumbs(entry):
    """
    Breadcrumbs for an Entry.
    """
    creation_date = entry.creation_date
    if is_aware(creation_date):
        creation_date = localtime(creation_date)
    return [year_crumb(creation_date),
            month_crumb(creation_date),
            day_crumb(creation_date),
            Crumb(entry.title)]


ZINNIA_ROOT_URL = lambda: reverse('zinnia:entry_archive_index')

MODEL_BREADCRUMBS = {'Tag': lambda x: [Crumb(_('Tags'),
                                             reverse('zinnia:tag_list')),
                                       Crumb(x.name)],
                     'Author': lambda x: [Crumb(_('Authors'),
                                                reverse('zinnia:author_list')),
                                          Crumb(x.__str__())],
                     'Category': lambda x: [Crumb(
                         _('Categories'), reverse('zinnia:category_list'))] +
                     [Crumb(anc.__str__(), anc.get_absolute_url())
                      for anc in x.get_ancestors()] + [Crumb(x.title)],
                     'Entry': entry_breadcrumbs}

ARCHIVE_REGEXP = re.compile(
    r'.*(?P<year>\d{4})/(?P<month>\d{2})?/(?P<day>\d{2})?.*')

ARCHIVE_WEEK_REGEXP = re.compile(
    r'.*(?P<year>\d{4})/week/(?P<week>\d+)?.*')

PAGE_REGEXP = re.compile(r'page/(?P<page>\d+).*$')


def handle_page_crumb(func):
    """
    Decorator for handling the current page in the breadcrumbs.
    """
    @wraps(func)
    def wrapper(path, model, page, root_name):
        path = PAGE_REGEXP.sub('', path)
        breadcrumbs = func(path, model, root_name)
        if page:
            if page.number > 1:
                breadcrumbs[-1].url = path
                page_crumb = Crumb(_('Page %s') % page.number)
                breadcrumbs.append(page_crumb)
        return breadcrumbs
    return wrapper


@handle_page_crumb
def retrieve_breadcrumbs(path, model_instance, root_name=''):
    """
    Build a semi-hardcoded breadcrumbs
    based of the model's url handled by Zinnia.
    """
    breadcrumbs = []

    if root_name:
        breadcrumbs.append(Crumb(root_name, ZINNIA_ROOT_URL()))

    if model_instance is not None:
        key = model_instance.__class__.__name__
        if key in MODEL_BREADCRUMBS:
            breadcrumbs.extend(MODEL_BREADCRUMBS[key](model_instance))
            return breadcrumbs

    date_match = ARCHIVE_WEEK_REGEXP.match(path)
    if date_match:
        year, week = date_match.groups()
        year_date = datetime(int(year), 1, 1)
        date_breadcrumbs = [year_crumb(year_date),
                            Crumb(_('Week %s') % week)]
        breadcrumbs.extend(date_breadcrumbs)
        return breadcrumbs

    date_match = ARCHIVE_REGEXP.match(path)
    if date_match:
        date_dict = date_match.groupdict()
        path_date = datetime(
            int(date_dict['year']),
            date_dict.get('month') is not None and
            int(date_dict.get('month')) or 1,
            date_dict.get('day') is not None and
            int(date_dict.get('day')) or 1)

        date_breadcrumbs = [year_crumb(path_date)]
        if date_dict['month']:
            date_breadcrumbs.append(month_crumb(path_date))
        if date_dict['day']:
            date_breadcrumbs.append(day_crumb(path_date))
        breadcrumbs.extend(date_breadcrumbs)
        breadcrumbs[-1].url = None
        return breadcrumbs

    url_components = [comp for comp in
                      path.replace(ZINNIA_ROOT_URL(), '', 1).split('/')
                      if comp]
    if len(url_components):
        breadcrumbs.append(Crumb(_(url_components[-1].capitalize())))

    return breadcrumbs

########NEW FILE########
__FILENAME__ = calendar
"""Calendar module for Zinnia"""
from __future__ import absolute_import

from datetime import date
from calendar import HTMLCalendar

from django.utils.dates import MONTHS
from django.utils.dates import WEEKDAYS_ABBR
from django.utils.formats import get_format
from django.utils.formats import date_format
from django.core.urlresolvers import reverse

from zinnia.models.entry import Entry

AMERICAN_TO_EUROPEAN_WEEK_DAYS = [6, 0, 1, 2, 3, 4, 5]


class Calendar(HTMLCalendar):
    """
    Extension of the HTMLCalendar.
    """

    def __init__(self):
        """
        Retrieve and convert the localized first week day
        at initialization.
        """
        HTMLCalendar.__init__(self, AMERICAN_TO_EUROPEAN_WEEK_DAYS[
            get_format('FIRST_DAY_OF_WEEK')])

    def formatday(self, day, weekday):
        """
        Return a day as a table cell with a link
        if entries are published this day.
        """
        if day and day in self.day_entries:
            day_date = date(self.current_year, self.current_month, day)
            archive_day_url = reverse('zinnia:entry_archive_day',
                                      args=[day_date.strftime('%Y'),
                                            day_date.strftime('%m'),
                                            day_date.strftime('%d')])
            return '<td class="%s entry"><a href="%s" '\
                   'class="archives">%d</a></td>' % (
                       self.cssclasses[weekday], archive_day_url, day)

        return super(Calendar, self).formatday(day, weekday)

    def formatweekday(self, day):
        """
        Return a weekday name translated as a table header.
        """
        return '<th class="%s">%s</th>' % (self.cssclasses[day],
                                           WEEKDAYS_ABBR[day].title())

    def formatweekheader(self):
        """
        Return a header for a week as a table row.
        """
        return '<thead>%s</thead>' % super(Calendar, self).formatweekheader()

    def formatfooter(self, previous_month, next_month):
        """
        Return a footer for a previous and next month.
        """
        footer = '<tfoot><tr>' \
                 '<td colspan="3" class="prev">%s</td>' \
                 '<td class="pad">&nbsp;</td>' \
                 '<td colspan="3" class="next">%s</td>' \
                 '</tr></tfoot>'
        if previous_month:
            previous_content = '<a href="%s" class="previous-month">%s</a>' % (
                reverse('zinnia:entry_archive_month', args=[
                    previous_month.strftime('%Y'),
                    previous_month.strftime('%m')]),
                date_format(previous_month, 'YEAR_MONTH_FORMAT'))
        else:
            previous_content = '&nbsp;'

        if next_month:
            next_content = '<a href="%s" class="next-month">%s</a>' % (
                reverse('zinnia:entry_archive_month', args=[
                    next_month.strftime('%Y'),
                    next_month.strftime('%m')]),
                date_format(next_month, 'YEAR_MONTH_FORMAT'))
        else:
            next_content = '&nbsp;'

        return footer % (previous_content, next_content)

    def formatmonthname(self, theyear, themonth, withyear=True):
        """Return a month name translated as a table row."""
        monthname = '%s %s' % (MONTHS[themonth].title(), theyear)
        return '<caption>%s</caption>' % monthname

    def formatmonth(self, theyear, themonth, withyear=True,
                    previous_month=None, next_month=None):
        """
        Return a formatted month as a table
        with new attributes computed for formatting a day,
        and thead/tfooter.
        """
        self.current_year = theyear
        self.current_month = themonth
        self.day_entries = [date.day
                            for date in Entry.published.filter(
                                creation_date__year=theyear,
                                creation_date__month=themonth
                                ).datetimes('creation_date', 'day')]
        v = []
        a = v.append
        a('<table class="%s">' % (
            self.day_entries and 'entries-calendar' or 'no-entries-calendar'))
        a('\n')
        a(self.formatmonthname(theyear, themonth, withyear=withyear))
        a('\n')
        a(self.formatweekheader())
        a('\n')
        a(self.formatfooter(previous_month, next_month))
        a('\n<tbody>\n')
        for week in self.monthdays2calendar(theyear, themonth):
            a(self.formatweek(week))
            a('\n')
        a('</tbody>\n</table>')
        a('\n')
        return ''.join(v)

########NEW FILE########
__FILENAME__ = comparison
"""Comparison tools for Zinnia"""
from django.utils import six

from math import sqrt

from zinnia.settings import F_MIN
from zinnia.settings import F_MAX


def pearson_score(list1, list2):
    """
    Compute the Pearson' score between 2 lists of vectors.
    """
    sum1 = sum(list1)
    sum2 = sum(list2)
    sum_sq1 = sum([pow(l, 2) for l in list1])
    sum_sq2 = sum([pow(l, 2) for l in list2])

    prod_sum = sum([list1[i] * list2[i] for i in range(len(list1))])

    num = prod_sum - (sum1 * sum2 / len(list1))
    den = sqrt((sum_sq1 - pow(sum1, 2.0) / len(list1)) *
               (sum_sq2 - pow(sum2, 2.0) / len(list2)))

    if den == 0.0:
        return 1.0

    return num / den


class ClusteredModel(object):
    """
    Wrapper around Model class
    building a dataset of instances.
    """

    def __init__(self, queryset, fields=['id']):
        self.fields = fields
        self.queryset = queryset

    def dataset(self):
        """
        Generate a dataset based on the queryset
        and the specified fields.
        """
        dataset = {}
        for item in self.queryset.filter():
            dataset[item] = ' '.join([six.text_type(getattr(item, field))
                                      for field in self.fields])
        return dataset


class VectorBuilder(object):
    """
    Build a list of vectors based on datasets.
    """

    def __init__(self, queryset, fields):
        self.key = ''
        self.columns = []
        self.dataset = {}
        self.clustered_model = ClusteredModel(queryset, fields)
        self.build_dataset()

    def build_dataset(self):
        """
        Generate the whole dataset.
        """
        data = {}
        words_total = {}

        model_data = self.clustered_model.dataset()
        for instance, words in model_data.items():
            words_item_total = {}
            for word in words.split():
                words_total.setdefault(word, 0)
                words_item_total.setdefault(word, 0)
                words_total[word] += 1
                words_item_total[word] += 1
            data[instance] = words_item_total

        top_words = []
        for word, count in words_total.items():
            frequency = float(count) / len(data)
            if frequency > F_MIN and frequency < F_MAX:
                top_words.append(word)

        self.dataset = {}
        self.columns = top_words
        for instance in data.keys():
            self.dataset[instance] = [data[instance].get(word, 0)
                                      for word in top_words]
        self.key = self.generate_key()

    def generate_key(self):
        """
        Generate key for this list of vectors.
        """
        return self.clustered_model.queryset.count()

    def flush(self):
        """
        Flush the dataset.
        """
        if self.key != self.generate_key():
            self.build_dataset()

    def __call__(self):
        self.flush()
        return self.columns, self.dataset

########NEW FILE########
__FILENAME__ = context_processors
"""Context Processors for Zinnia"""
from zinnia import __version__


def version(request):
    """
    Add version of Zinnia to the context.
    """
    return {'ZINNIA_VERSION': __version__}

########NEW FILE########
__FILENAME__ = feeds
"""Feeds for Zinnia"""
import os
from mimetypes import guess_type
try:
    from urllib.parse import urljoin
except ImportError:  # Python 2
    from urlparse import urljoin

from django.contrib.sites.models import Site
from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404
from django.utils.feedgenerator import Atom1Feed
from django.utils.translation import ugettext as _
from django.contrib.syndication.views import Feed
from django.template.defaultfilters import slugify
from django.core.urlresolvers import NoReverseMatch
from django.core.files.storage import default_storage
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.contenttypes.models import ContentType

from bs4 import BeautifulSoup

import django_comments as comments

from tagging.models import Tag
from tagging.models import TaggedItem

from zinnia.models.entry import Entry
from zinnia.models.author import Author
from zinnia.settings import PROTOCOL
from zinnia.settings import COPYRIGHT
from zinnia.settings import FEEDS_FORMAT
from zinnia.settings import FEEDS_MAX_ITEMS
from zinnia.views.categories import get_category_or_404
from zinnia.templatetags.zinnia_tags import get_gravatar


class ZinniaFeed(Feed):
    """
    Base Feed class for the Zinnia application,
    enriched for a more convenient usage.
    """
    feed_copyright = COPYRIGHT
    _site = None

    def __init__(self):
        if FEEDS_FORMAT == 'atom':
            self.feed_type = Atom1Feed
            self.subtitle = getattr(self, 'description', None)

    def title(self, obj=None):
        """
        Title of the feed prefixed with the site name.
        """
        return '%s - %s' % (self.site.name, self.get_title(obj))

    def get_title(self, obj):
        raise NotImplementedError

    @property
    def site(self):
        """
        Acquire the current site used.
        """
        if self._site is None:
            self._site = Site.objects.get_current()
        return self._site

    @property
    def site_url(self):
        """
        Return the URL of the current site.
        """
        return '%s://%s' % (PROTOCOL, self.site.domain)


class EntryFeed(ZinniaFeed):
    """
    Base Entry Feed.
    """
    title_template = 'feeds/entry_title.html'
    description_template = 'feeds/entry_description.html'

    def item_pubdate(self, item):
        """
        Publication date of an entry.
        """
        return item.creation_date

    def item_categories(self, item):
        """
        Entry's categories.
        """
        return [category.title for category in item.categories.all()]

    def item_author_name(self, item):
        """
        Return the first author of an entry.
        """
        if item.authors.count():
            self.item_author = item.authors.all()[0]
            return self.item_author.__str__()

    def item_author_email(self, item):
        """
        Return the first author's email.
        Should not be called if self.item_author_name has returned None.
        """
        return self.item_author.email

    def item_author_link(self, item):
        """
        Return the author's URL.
        Should not be called if self.item_author_name has returned None.
        """
        try:
            author_url = self.item_author.get_absolute_url()
            return self.site_url + author_url
        except NoReverseMatch:
            return self.site_url

    def item_enclosure_url(self, item):
        """
        Return an image for enclosure.
        """
        if item.image:
            url = item.image.url
        else:
            img = BeautifulSoup(item.html_content).find('img')
            url = img.get('src') if img else None
        self.cached_enclosure_url = url
        return urljoin(self.site_url, url) if url else None

    def item_enclosure_length(self, item):
        """
        Try to obtain the size of the enclosure
        if the enclosure is present on the FS,
        otherwise returns an hardcoded value.
        """
        if item.image:
            try:
                return str(default_storage.size(item.image.path))
            except (os.error, NotImplementedError):
                pass
        return '100000'

    def item_enclosure_mime_type(self, item):
        """
        Guess the enclosure's mimetype.
        """
        mimetype, encoding = guess_type(self.cached_enclosure_url)
        if mimetype:
            return mimetype
        return 'image/jpeg'


class LatestEntries(EntryFeed):
    """
    Feed for the latest entries.
    """

    def link(self):
        """
        URL of latest entries.
        """
        return reverse('zinnia:entry_archive_index')

    def items(self):
        """
        Items are published entries.
        """
        return Entry.published.all()[:FEEDS_MAX_ITEMS]

    def get_title(self, obj):
        """
        Title of the feed
        """
        return _('Latest entries')

    def description(self):
        """
        Description of the feed.
        """
        return _('The latest entries for the site %s') % self.site.name


class CategoryEntries(EntryFeed):
    """
    Feed filtered by a category.
    """

    def get_object(self, request, path):
        """
        Retrieve the category by his path.
        """
        return get_category_or_404(path)

    def items(self, obj):
        """
        Items are the published entries of the category.
        """
        return obj.entries_published()[:FEEDS_MAX_ITEMS]

    def link(self, obj):
        """
        URL of the category.
        """
        return obj.get_absolute_url()

    def get_title(self, obj):
        """
        Title of the feed.
        """
        return _('Entries for the category %s') % obj.title

    def description(self, obj):
        """
        Description of the feed.
        """
        return _('The latest entries for the category %s') % obj.title


class AuthorEntries(EntryFeed):
    """
    Feed filtered by an author.
    """

    def get_object(self, request, username):
        """
        Retrieve the author by his username.
        """
        return get_object_or_404(Author, **{Author.USERNAME_FIELD: username})

    def items(self, obj):
        """
        Items are the published entries of the author.
        """
        return obj.entries_published()[:FEEDS_MAX_ITEMS]

    def link(self, obj):
        """
        URL of the author.
        """
        return obj.get_absolute_url()

    def get_title(self, obj):
        """
        Title of the feed.
        """
        return _('Entries for author %s') % obj.__str__()

    def description(self, obj):
        """
        Description of the feed.
        """
        return _('The latest entries by %s') % obj.__str__()


class TagEntries(EntryFeed):
    """
    Feed filtered by a tag.
    """

    def get_object(self, request, tag):
        """
        Retrieve the tag by his name.
        """
        return get_object_or_404(Tag, name=tag)

    def items(self, obj):
        """
        Items are the published entries of the tag.
        """
        return TaggedItem.objects.get_by_model(
            Entry.published.all(), obj)[:FEEDS_MAX_ITEMS]

    def link(self, obj):
        """
        URL of the tag.
        """
        return reverse('zinnia:tag_detail', args=[obj.name])

    def get_title(self, obj):
        """
        Title of the feed.
        """
        return _('Entries for the tag %s') % obj.name

    def description(self, obj):
        """
        Description of the feed.
        """
        return _('The latest entries for the tag %s') % obj.name


class SearchEntries(EntryFeed):
    """
    Feed filtered by a search pattern.
    """

    def get_object(self, request):
        """
        The GET parameter 'pattern' is the object.
        """
        pattern = request.GET.get('pattern', '')
        if len(pattern) < 3:
            raise ObjectDoesNotExist
        return pattern

    def items(self, obj):
        """
        Items are the published entries founds.
        """
        return Entry.published.search(obj)[:FEEDS_MAX_ITEMS]

    def link(self, obj):
        """
        URL of the search request.
        """
        return '%s?pattern=%s' % (reverse('zinnia:entry_search'), obj)

    def get_title(self, obj):
        """
        Title of the feed.
        """
        return _("Results of the search for '%s'") % obj

    def description(self, obj):
        """
        Description of the feed.
        """
        return _("The entries containing the pattern '%s'") % obj


class DiscussionFeed(ZinniaFeed):
    """
    Base class for discussion Feed.
    """
    title_template = 'feeds/discussion_title.html'
    description_template = 'feeds/discussion_description.html'

    def item_pubdate(self, item):
        """
        Publication date of a discussion.
        """
        return item.submit_date

    def item_link(self, item):
        """
        URL of the discussion item.
        """
        return item.get_absolute_url()

    def item_author_name(self, item):
        """
        Author of the discussion item.
        """
        return item.name

    def item_author_email(self, item):
        """
        Author's email of the discussion item.
        """
        return item.email

    def item_author_link(self, item):
        """
        Author's URL of the discussion.
        """
        return item.url


class LatestDiscussions(DiscussionFeed):
    """
    Feed for the latest discussions.
    """

    def items(self):
        """
        Items are the discussions on the entries.
        """
        content_type = ContentType.objects.get_for_model(Entry)
        return comments.get_model().objects.filter(
            content_type=content_type, is_public=True).order_by(
            '-submit_date')[:FEEDS_MAX_ITEMS]

    def link(self):
        """
        URL of latest discussions.
        """
        return reverse('zinnia:entry_archive_index')

    def get_title(self, obj):
        """
        Title of the feed.
        """
        return _('Latest discussions')

    def description(self):
        """
        Description of the feed.
        """
        return _('The latest discussions for the site %s') % self.site.name


class EntryDiscussions(DiscussionFeed):
    """
    Feed for discussions on an entry.
    """

    def get_object(self, request, year, month, day, slug):
        """
        Retrieve the discussions by entry's slug.
        """
        return get_object_or_404(Entry, slug=slug,
                                 creation_date__year=year,
                                 creation_date__month=month,
                                 creation_date__day=day)

    def items(self, obj):
        """
        Items are the discussions on the entry.
        """
        return obj.discussions[:FEEDS_MAX_ITEMS]

    def link(self, obj):
        """
        URL of the entry.
        """
        return obj.get_absolute_url()

    def get_title(self, obj):
        """
        Title of the feed.
        """
        return _('Discussions on %s') % obj.title

    def description(self, obj):
        """
        Description of the feed.
        """
        return _('The latest discussions for the entry %s') % obj.title


class EntryComments(EntryDiscussions):
    """
    Feed for comments on an entry.
    """
    title_template = 'feeds/comment_title.html'
    description_template = 'feeds/comment_description.html'

    def items(self, obj):
        """
        Items are the comments on the entry.
        """
        return obj.comments[:FEEDS_MAX_ITEMS]

    def item_link(self, item):
        """
        URL of the comment.
        """
        return item.get_absolute_url('#comment-%(id)s-by-'
                                     ) + slugify(item.user_name)

    def get_title(self, obj):
        """
        Title of the feed.
        """
        return _('Comments on %s') % obj.title

    def description(self, obj):
        """
        Description of the feed.
        """
        return _('The latest comments for the entry %s') % obj.title

    def item_enclosure_url(self, item):
        """
        Return a gravatar image for enclosure.
        """
        return get_gravatar(item.email)

    def item_enclosure_length(self, item):
        """
        Hardcoded enclosure length.
        """
        return '100000'

    def item_enclosure_mime_type(self, item):
        """
        Hardcoded enclosure mimetype.
        """
        return 'image/jpeg'


class EntryPingbacks(EntryDiscussions):
    """
    Feed for pingbacks on an entry.
    """
    title_template = 'feeds/pingback_title.html'
    description_template = 'feeds/pingback_description.html'

    def items(self, obj):
        """
        Items are the pingbacks on the entry.
        """
        return obj.pingbacks[:FEEDS_MAX_ITEMS]

    def item_link(self, item):
        """
        URL of the pingback.
        """
        return item.get_absolute_url('#pingback-%(id)s')

    def get_title(self, obj):
        """
        Title of the feed.
        """
        return _('Pingbacks on %s') % obj.title

    def description(self, obj):
        """
        Description of the feed.
        """
        return _('The latest pingbacks for the entry %s') % obj.title


class EntryTrackbacks(EntryDiscussions):
    """
    Feed for trackbacks on an entry.
    """
    title_template = 'feeds/trackback_title.html'
    description_template = 'feeds/trackback_description.html'

    def items(self, obj):
        """
        Items are the trackbacks on the entry.
        """
        return obj.trackbacks[:FEEDS_MAX_ITEMS]

    def item_link(self, item):
        """
        URL of the trackback.
        """
        return item.get_absolute_url('#trackback-%(id)s')

    def get_title(self, obj):
        """
        Title of the feed.
        """
        return _('Trackbacks on %s') % obj.title

    def description(self, obj):
        """
        Description of the feed.
        """
        return _('The latest trackbacks for the entry %s') % obj.title

########NEW FILE########
__FILENAME__ = flags
"""Comment flags for Zinnia"""
from django.contrib.auth import get_user_model
from django.utils.functional import memoize

from zinnia.settings import COMMENT_FLAG_USER_ID

PINGBACK = 'pingback'
TRACKBACK = 'trackback'
FLAGGER_USERNAME = 'Zinnia-Flagger'

user_flagger_ = {}


def _get_user_flagger():
    User = get_user_model()
    try:
        user = User.objects.get(pk=COMMENT_FLAG_USER_ID)
    except User.DoesNotExist:
        try:
            user = User.objects.get(**{User.USERNAME_FIELD: FLAGGER_USERNAME})
        except User.DoesNotExist:
            user = User.objects.create_user(FLAGGER_USERNAME)
    return user

get_user_flagger = memoize(_get_user_flagger, user_flagger_, 0)

########NEW FILE########
__FILENAME__ = blogger2zinnia
"""Blogger to Zinnia command module
Based on Elijah Rutschman's code"""
import sys
from getpass import getpass
from datetime import datetime
from optparse import make_option

from django.conf import settings
from django.utils import timezone
from django.utils.text import Truncator
from django.utils.html import strip_tags
from django.utils.six.moves import input
from django.utils.encoding import smart_str
from django.utils.encoding import smart_unicode
from django.contrib.sites.models import Site
from django.template.defaultfilters import slugify
from django.core.management.base import CommandError
from django.core.management.base import NoArgsCommand
from django.contrib.contenttypes.models import ContentType

from django_comments import get_model as get_comment_model

from zinnia import __version__
from zinnia.models.entry import Entry
from zinnia.models.author import Author
from zinnia.models.category import Category
from zinnia.managers import DRAFT, PUBLISHED
from zinnia.signals import disconnect_entry_signals
from zinnia.signals import disconnect_discussion_signals

gdata_service = None
Comment = get_comment_model()


class Command(NoArgsCommand):
    """
    Command object for importing a Blogger blog
    into Zinnia via Google's gdata API.
    """
    help = 'Import a Blogger blog into Zinnia.'

    option_list = NoArgsCommand.option_list + (
        make_option('--blogger-username', dest='blogger_username', default='',
                    help='The username to login to Blogger with'),
        make_option('--category-title', dest='category_title', default='',
                    help='The Zinnia category to import Blogger posts to'),
        make_option('--blogger-blog-id', dest='blogger_blog_id', default='',
                    help='The id of the Blogger blog to import'),
        make_option('--blogger-limit', dest='blogger_limit', default=25,
                    help='Specify a limit for posts to be imported'),
        make_option('--author', dest='author', default='',
                    help='All imported entries belong to specified author'),
        make_option('--noautoexcerpt', action='store_false',
                    dest='auto_excerpt', default=True,
                    help='Do NOT generate an excerpt.'))

    SITE = Site.objects.get_current()

    def __init__(self):
        """
        Init the Command and add custom styles.
        """
        super(Command, self).__init__()
        self.style.TITLE = self.style.SQL_FIELD
        self.style.STEP = self.style.SQL_COLTYPE
        self.style.ITEM = self.style.HTTP_INFO
        disconnect_entry_signals()
        disconnect_discussion_signals()

    def write_out(self, message, verbosity_level=1):
        """
        Convenient method for outputing.
        """
        if self.verbosity and self.verbosity >= verbosity_level:
            sys.stdout.write(smart_str(message))
            sys.stdout.flush()

    def handle_noargs(self, **options):
        global gdata_service
        try:
            from gdata import service
            gdata_service = service
        except ImportError:
            raise CommandError('You need to install the gdata '
                               'module to run this command.')

        self.verbosity = int(options.get('verbosity', 1))
        self.blogger_username = options.get('blogger_username')
        self.blogger_blog_id = options.get('blogger_blog_id')
        self.blogger_limit = int(options.get('blogger_limit'))
        self.category_title = options.get('category_title')
        self.auto_excerpt = options.get('auto-excerpt', True)

        self.write_out(self.style.TITLE(
            'Starting migration from Blogger to Zinnia %s\n' % __version__))

        if not self.blogger_username:
            self.blogger_username = input('Blogger username: ')
            if not self.blogger_username:
                raise CommandError('Invalid Blogger username')

        self.blogger_password = getpass('Blogger password: ')
        try:
            self.blogger_manager = BloggerManager(self.blogger_username,
                                                  self.blogger_password)
        except gdata_service.BadAuthentication:
            raise CommandError('Incorrect Blogger username or password')

        default_author = options.get('author')
        if default_author:
            try:
                self.default_author = Author.objects.get(
                    **{Author.USERNAME_FIELD: self.default_author})
            except Author.DoesNotExist:
                raise CommandError(
                    'Invalid Zinnia username for default author "%s"' %
                    default_author)
        else:
            self.default_author = Author.objects.all()[0]

        if not self.blogger_blog_id:
            self.select_blog_id()

        if not self.category_title:
            self.category_title = input(
                'Category title for imported entries: ')
            if not self.category_title:
                raise CommandError('Invalid category title')

        self.import_posts()

    def select_blog_id(self):
        self.write_out(self.style.STEP('- Requesting your weblogs\n'))
        blogs_list = [blog for blog in self.blogger_manager.get_blogs()]
        while True:
            i = 0
            blogs = {}
            for blog in blogs_list:
                i += 1
                blogs[i] = blog
                self.write_out('%s. %s (%s)' % (i, blog.title.text,
                                                get_blog_id(blog)))
            try:
                blog_index = int(input('\nSelect a blog to import: '))
                blog = blogs[blog_index]
                break
            except (ValueError, KeyError):
                self.write_out(self.style.ERROR(
                    'Please enter a valid blog number\n'))

        self.blogger_blog_id = get_blog_id(blog)

    def get_category(self):
        category, created = Category.objects.get_or_create(
            title=self.category_title,
            slug=slugify(self.category_title)[:255])

        if created:
            category.save()

        return category

    def import_posts(self):
        category = self.get_category()
        self.write_out(self.style.STEP('- Importing entries\n'))
        for post in self.blogger_manager.get_posts(self.blogger_blog_id,
                                                   self.blogger_limit):
            creation_date = convert_blogger_timestamp(post.published.text)
            status = DRAFT if is_draft(post) else PUBLISHED
            title = post.title.text or ''
            content = post.content.text or ''
            excerpt = self.auto_excerpt and Truncator(
                strip_tags(smart_unicode(content))).words(50) or ''
            slug = slugify(post.title.text or get_post_id(post))[:255]
            try:
                entry = Entry.objects.get(creation_date=creation_date,
                                          slug=slug)
                output = self.style.NOTICE('> Skipped %s (already migrated)\n'
                                           % entry)
            except Entry.DoesNotExist:
                entry = Entry(status=status, title=title, content=content,
                              creation_date=creation_date, slug=slug,
                              excerpt=excerpt)
                entry.tags = ','.join([slugify(cat.term) for
                                       cat in post.category])
                entry.last_update = convert_blogger_timestamp(
                    post.updated.text)
                entry.save()
                entry.sites.add(self.SITE)
                entry.categories.add(category)
                entry.authors.add(self.default_author)
                try:
                    self.import_comments(entry, post)
                except gdata_service.RequestError:
                    # comments not available for this post
                    pass
                entry.comment_count = entry.comments.count()
                entry.save(force_update=True)
                output = self.style.ITEM('> Migrated %s + %s comments\n'
                                         % (entry.title, entry.comment_count))

            self.write_out(output)

    def import_comments(self, entry, post):
        blog_id = self.blogger_blog_id
        post_id = get_post_id(post)
        comments = self.blogger_manager.get_comments(blog_id, post_id)
        entry_content_type = ContentType.objects.get_for_model(Entry)

        for comment in comments:
            submit_date = convert_blogger_timestamp(comment.published.text)
            content = comment.content.text

            author = comment.author[0]
            if author:
                user_name = author.name.text if author.name else ''
                user_email = author.email.text if author.email else ''
                user_url = author.uri.text if author.uri else ''

            else:
                user_name = ''
                user_email = ''
                user_url = ''

            com, created = Comment.objects.get_or_create(
                content_type=entry_content_type,
                object_pk=entry.pk,
                comment=content,
                submit_date=submit_date,
                site=self.SITE,
                user_name=user_name,
                user_email=user_email,
                user_url=user_url)

            if created:
                com.save()


def convert_blogger_timestamp(timestamp):
    # parse 2010-12-19T15:37:00.003
    date_string = timestamp[:-6]
    dt = datetime.strptime(date_string, '%Y-%m-%dT%H:%M:%S.%f')
    if settings.USE_TZ:
        dt = timezone.make_aware(dt, timezone.utc)
    return dt


def is_draft(post):
    if post.control:
        if post.control.draft:
            if post.control.draft.text == 'yes':
                return True
    return False


def get_blog_id(blog):
    return blog.GetSelfLink().href.split('/')[-1]


def get_post_id(post):
    return post.GetSelfLink().href.split('/')[-1]


class BloggerManager(object):

    def __init__(self, username, password):
        self.service = gdata_service.GDataService(username, password)
        self.service.server = 'www.blogger.com'
        self.service.service = 'blogger'
        self.service.ProgrammaticLogin()

    def get_blogs(self):
        feed = self.service.Get('/feeds/default/blogs')
        for blog in feed.entry:
            yield blog

    def get_posts(self, blog_id, limit):
        feed = self.service.Get('/feeds/%s/posts/default/?max-results=%d' %
                                (blog_id, limit))
        for post in feed.entry:
            yield post

    def get_comments(self, blog_id, post_id):
        feed = self.service.Get('/feeds/%s/%s/comments/default' %
                                (blog_id, post_id))
        for comment in feed.entry:
            yield comment

########NEW FILE########
__FILENAME__ = count_discussions
"""Management command for re-counting the discussions on Entry"""
import sys

from django.utils.encoding import smart_str
from django.core.management.base import NoArgsCommand

from zinnia.models.entry import Entry


class Command(NoArgsCommand):
    """
    Command for re-counting the discussions on entries
    in case of problems.
    """
    help = 'Refresh all the discussion counts on entries'

    def write_out(self, message, verbosity_level=1):
        """
        Convenient method for outputing.
        """
        if self.verbosity and self.verbosity >= verbosity_level:
            sys.stdout.write(smart_str(message))
            sys.stdout.flush()

    def handle_noargs(self, **options):
        self.verbosity = int(options.get('verbosity', 1))
        for entry in Entry.objects.all():
            self.write_out('Processing %s\n' % entry.title)
            changed = False
            comment_count = entry.comments.count()
            pingback_count = entry.pingbacks.count()
            trackback_count = entry.trackbacks.count()

            if entry.comment_count != comment_count:
                changed = True
                self.write_out('- %s comments found, %s before\n' % (
                    comment_count, entry.comment_count))
                entry.comment_count = comment_count

            if entry.pingback_count != pingback_count:
                changed = True
                self.write_out('- %s pingbacks found, %s before\n' % (
                    pingback_count, entry.pingback_count))
                entry.pingback_count = pingback_count

            if entry.trackback_count != trackback_count:
                changed = True
                self.write_out('- %s trackbacks found, %s before\n' % (
                    trackback_count, entry.trackback_count))
                entry.trackback_count = trackback_count

            if changed:
                self.write_out('- Updating...\n')
                entry.save()

########NEW FILE########
__FILENAME__ = feed2zinnia
"""Feed to Zinnia command module"""
import os
import sys
from datetime import datetime
from optparse import make_option
try:
    from urllib.request import urlopen
except ImportError:  # Python 2
    from urllib2 import urlopen

from django.conf import settings
from django.utils import timezone
from django.core.files import File
from django.utils.text import Truncator
from django.utils.html import strip_tags
from django.db.utils import IntegrityError
from django.utils.encoding import smart_str
from django.contrib.sites.models import Site
from django.template.defaultfilters import slugify
from django.core.management.base import CommandError
from django.core.management.base import LabelCommand
from django.core.files.temp import NamedTemporaryFile

from zinnia import __version__
from zinnia.models.entry import Entry
from zinnia.models.author import Author
from zinnia.models.category import Category
from zinnia.managers import PUBLISHED
from zinnia.signals import disconnect_entry_signals
from zinnia.signals import disconnect_discussion_signals


class Command(LabelCommand):
    """
    Command object for importing a RSS or Atom
    feed into Zinnia.
    """
    help = 'Import a RSS or Atom feed into Zinnia.'
    label = 'feed url'
    args = 'url'

    option_list = LabelCommand.option_list + (
        make_option('--no-auto-excerpt', action='store_false',
                    dest='auto-excerpt', default=True,
                    help='Do NOT generate an excerpt if not present.'),
        make_option('--no-enclosure', action='store_false',
                    dest='image-enclosure', default=True,
                    help='Do NOT save image enclosure if present.'),
        make_option('--no-tags', action='store_false',
                    dest='tags', default=True,
                    help='Do NOT store categories as tags'),
        make_option('--author', dest='author', default='',
                    help='All imported entries belong to specified author'))
    SITE = Site.objects.get_current()

    def __init__(self):
        """
        Init the Command and add custom styles.
        """
        super(Command, self).__init__()
        self.style.TITLE = self.style.SQL_FIELD
        self.style.STEP = self.style.SQL_COLTYPE
        self.style.ITEM = self.style.HTTP_INFO
        disconnect_entry_signals()
        disconnect_discussion_signals()

    def write_out(self, message, verbosity_level=1):
        """
        Convenient method for outputing.
        """
        if self.verbosity and self.verbosity >= verbosity_level:
            sys.stdout.write(smart_str(message))
            sys.stdout.flush()

    def handle_label(self, url, **options):
        try:
            import feedparser
        except ImportError:
            raise CommandError('You need to install the feedparser '
                               'module to run this command.')

        self.tags = options.get('tags', True)
        self.default_author = options.get('author')
        self.verbosity = int(options.get('verbosity', 1))
        self.auto_excerpt = options.get('auto-excerpt', True)
        self.image_enclosure = options.get('image-enclosure', True)
        if self.default_author:
            try:
                self.default_author = Author.objects.get(
                    **{Author.USERNAME_FIELD: self.default_author})
            except Author.DoesNotExist:
                raise CommandError('Invalid username for default author')

        self.write_out(self.style.TITLE(
            'Starting importation of %s to Zinnia %s:\n' % (url, __version__)))

        feed = feedparser.parse(url)
        self.import_entries(feed.entries)

    def import_entries(self, feed_entries):
        """
        Import entries.
        """
        for feed_entry in feed_entries:
            self.write_out('> %s... ' % feed_entry.title)
            if feed_entry.get('published_parsed'):
                creation_date = datetime(*feed_entry.published_parsed[:6])
                if settings.USE_TZ:
                    creation_date = timezone.make_aware(
                        creation_date, timezone.utc)
            else:
                creation_date = timezone.now()
            slug = slugify(feed_entry.title)[:255]

            if Entry.objects.filter(creation_date__year=creation_date.year,
                                    creation_date__month=creation_date.month,
                                    creation_date__day=creation_date.day,
                                    slug=slug):
                self.write_out(self.style.NOTICE(
                    'SKIPPED (already imported)\n'))
                continue

            categories = self.import_categories(feed_entry)
            entry_dict = {'title': feed_entry.title[:255],
                          'content': feed_entry.description,
                          'excerpt': strip_tags(feed_entry.get('summary')),
                          'status': PUBLISHED,
                          'creation_date': creation_date,
                          'start_publication': creation_date,
                          'last_update': timezone.now(),
                          'slug': slug}

            if not entry_dict['excerpt'] and self.auto_excerpt:
                entry_dict['excerpt'] = Truncator(
                    strip_tags(feed_entry.description)).words(50)

            if self.tags:
                entry_dict['tags'] = self.import_tags(categories)

            entry = Entry(**entry_dict)
            entry.save()
            entry.categories.add(*categories)
            entry.sites.add(self.SITE)

            if self.image_enclosure:
                for enclosure in feed_entry.enclosures:
                    if ('image' in enclosure.get('type') and
                            enclosure.get('href')):
                        img_tmp = NamedTemporaryFile(delete=True)
                        img_tmp.write(urlopen(enclosure['href']).read())
                        img_tmp.flush()
                        entry.image.save(os.path.basename(enclosure['href']),
                                         File(img_tmp))
                        break

            if self.default_author:
                entry.authors.add(self.default_author)
            elif feed_entry.get('author_detail'):
                try:
                    author = Author.objects.create_user(
                        slugify(feed_entry.author_detail.get('name')),
                        feed_entry.author_detail.get('email', ''))
                except IntegrityError:
                    author = Author.objects.get(**{
                        Author.USERNAME_FIELD:
                        slugify(feed_entry.author_detail.get('name'))})
                entry.authors.add(author)

            self.write_out(self.style.ITEM('OK\n'))

    def import_categories(self, feed_entry):
        categories = []
        for cat in feed_entry.get('tags', ''):
            category, created = Category.objects.get_or_create(
                slug=slugify(cat.term), defaults={'title': cat.term})
            categories.append(category)
        return categories

    def import_tags(self, categories):
        tags = []
        for cat in categories:
            if len(cat.title.split()) > 1:
                tags.append('"%s"' % slugify(cat.title).replace('-', ' '))
            else:
                tags.append(slugify(cat.title).replace('-', ' '))
        return ', '.join(tags)

########NEW FILE########
__FILENAME__ = spam_cleanup
"""Spam cleanup command module for Zinnia"""
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import NoArgsCommand

import django_comments as comments

from zinnia.models.entry import Entry


class Command(NoArgsCommand):
    """
    Command object for removing comments
    marked as non-public and removed.
    """
    help = "Delete the entries's comments marked as non-public and removed."

    def handle_noargs(self, **options):
        verbosity = int(options.get('verbosity', 1))

        content_type = ContentType.objects.get_for_model(Entry)
        spams = comments.get_model().objects.filter(
            is_public=False, is_removed=True,
            content_type=content_type)
        spams_count = spams.count()
        spams.delete()

        if verbosity:
            print('%i spam comments deleted.' % spams_count)

########NEW FILE########
__FILENAME__ = wp2zinnia
"""WordPress to Zinnia command module"""
import os
import sys
import pytz

from datetime import datetime
from optparse import make_option
from xml.etree import ElementTree as ET
try:
    from urllib.request import urlopen
except ImportError:  # Python 2
    from urllib2 import urlopen

from django.conf import settings
from django.utils import timezone
from django.core.files import File
from django.utils.text import Truncator
from django.utils.html import strip_tags
from django.utils.six.moves import input
from django.db.utils import IntegrityError
from django.utils.encoding import smart_str
from django.contrib.sites.models import Site
from django.template.defaultfilters import slugify
from django.core.management.base import CommandError
from django.core.management.base import LabelCommand
from django.core.files.temp import NamedTemporaryFile

import django_comments as comments

from tagging.models import Tag

from zinnia import __version__
from zinnia.models.entry import Entry
from zinnia.models.author import Author
from zinnia.models.category import Category
from zinnia.flags import get_user_flagger
from zinnia.flags import PINGBACK, TRACKBACK
from zinnia.managers import DRAFT, HIDDEN, PUBLISHED
from zinnia.signals import disconnect_entry_signals
from zinnia.signals import disconnect_discussion_signals

WP_NS = 'http://wordpress.org/export/%s/'


class Command(LabelCommand):
    """
    Command object for importing a WordPress blog
    into Zinnia via a WordPress eXtended RSS (WXR) file.
    """
    help = 'Import a Wordpress blog into Zinnia.'
    label = 'WXR file'
    args = 'wordpress.xml'

    option_list = LabelCommand.option_list + (
        make_option('--noautoexcerpt', action='store_false',
                    dest='auto_excerpt', default=True,
                    help='Do NOT generate an excerpt if not present.'),
        make_option('--author', dest='author', default='',
                    help='All imported entries belong to specified author'))

    SITE = Site.objects.get_current()
    REVERSE_STATUS = {'pending': DRAFT,
                      'draft': DRAFT,
                      'auto-draft': DRAFT,
                      'inherit': DRAFT,
                      'publish': PUBLISHED,
                      'future': PUBLISHED,
                      'trash': HIDDEN,
                      'private': PUBLISHED}

    def __init__(self):
        """
        Init the Command and add custom styles.
        """
        super(Command, self).__init__()
        self.style.TITLE = self.style.SQL_FIELD
        self.style.STEP = self.style.SQL_COLTYPE
        self.style.ITEM = self.style.HTTP_INFO
        disconnect_entry_signals()
        disconnect_discussion_signals()

    def write_out(self, message, verbosity_level=1):
        """
        Convenient method for outputing.
        """
        if self.verbosity and self.verbosity >= verbosity_level:
            sys.stdout.write(smart_str(message))
            sys.stdout.flush()

    def handle_label(self, wxr_file, **options):
        global WP_NS
        self.verbosity = int(options.get('verbosity', 1))
        self.auto_excerpt = options.get('auto_excerpt', True)
        self.default_author = options.get('author')
        if self.default_author:
            try:
                self.default_author = Author.objects.get(
                    **{Author.USERNAME_FIELD: self.default_author})
            except Author.DoesNotExist:
                raise CommandError('Invalid username for default author')

        self.write_out(self.style.TITLE(
            'Starting migration from Wordpress to Zinnia %s:\n' % __version__))

        tree = ET.parse(wxr_file)
        WP_NS = WP_NS % self.guess_wxr_version(tree)

        self.authors = self.import_authors(tree)

        self.categories = self.import_categories(
            tree.findall('channel/{%s}category' % WP_NS))

        self.import_tags(tree.findall('channel/{%s}tag' % WP_NS))

        self.import_entries(tree.findall('channel/item'))

    def guess_wxr_version(self, tree):
        """
        We will try to guess the wxr version used
        to complete the wordpress xml namespace name.
        """
        for v in ('1.2', '1.1', '1.0'):
            try:
                tree.find('channel/{%s}wxr_version' % (WP_NS % v)).text
                return v
            except AttributeError:
                pass
        raise CommandError('Cannot resolve the wordpress namespace')

    def import_authors(self, tree):
        """
        Retrieve all the authors used in posts
        and convert it to new or existing author and
        return the conversion.
        """
        self.write_out(self.style.STEP('- Importing authors\n'))

        post_authors = set()
        for item in tree.findall('channel/item'):
            post_type = item.find('{%s}post_type' % WP_NS).text
            if post_type == 'post':
                post_authors.add(item.find(
                    '{http://purl.org/dc/elements/1.1/}creator').text)

        self.write_out('> %i authors found.\n' % len(post_authors))

        authors = {}
        for post_author in post_authors:
            if self.default_author:
                authors[post_author] = self.default_author
            else:
                authors[post_author] = self.migrate_author(
                    post_author.replace(' ', '-'))
        return authors

    def migrate_author(self, author_name):
        """
        Handle actions for migrating the authors.
        """
        action_text = "The author '%s' needs to be migrated to an user:\n"\
                      "1. Use an existing user ?\n"\
                      "2. Create a new user ?\n"\
                      "Please select a choice: " % self.style.ITEM(author_name)
        while 42:
            selection = input(smart_str(action_text))
            if selection and selection in '12':
                break
        if selection == '1':
            users = Author.objects.all()
            if users.count() == 1:
                username = users[0].get_username()
                preselected_user = username
                usernames = [username]
                usernames_display = ['[%s]' % username]
            else:
                usernames = []
                usernames_display = []
                preselected_user = None
                for user in users:
                    username = user.get_username()
                    if username == author_name:
                        usernames_display.append('[%s]' % username)
                        preselected_user = username
                    else:
                        usernames_display.append(username)
                    usernames.append(username)
            while 42:
                user_text = "1. Select your user, by typing " \
                            "one of theses usernames:\n"\
                            "%s or 'back'\n"\
                            "Please select a choice: " % \
                            ', '.join(usernames_display)
                user_selected = input(user_text)
                if user_selected in usernames:
                    break
                if user_selected == '' and preselected_user:
                    user_selected = preselected_user
                    break
                if user_selected.strip() == 'back':
                    return self.migrate_author(author_name)
            return users.get(**{users[0].USERNAME_FIELD: user_selected})
        else:
            create_text = "2. Please type the email of " \
                          "the '%s' user or 'back': " % author_name
            author_mail = input(create_text)
            if author_mail.strip() == 'back':
                return self.migrate_author(author_name)
            try:
                return Author.objects.create_user(author_name, author_mail)
            except IntegrityError:
                return Author.objects.get(
                    **{Author.USERNAME_FIELD: author_name})

    def import_categories(self, category_nodes):
        """
        Import all the categories from 'wp:category' nodes,
        because categories in 'item' nodes are not necessarily
        all the categories and returning it in a dict for
        database optimizations.
        """
        self.write_out(self.style.STEP('- Importing categories\n'))

        categories = {}
        for category_node in category_nodes:
            title = category_node.find('{%s}cat_name' % WP_NS).text[:255]
            slug = category_node.find(
                '{%s}category_nicename' % WP_NS).text[:255]
            try:
                parent = category_node.find(
                    '{%s}category_parent' % WP_NS).text[:255]
            except TypeError:
                parent = None
            self.write_out('> %s... ' % title)
            category, created = Category.objects.get_or_create(
                slug=slug, defaults={'title': title,
                                     'parent': categories.get(parent)})
            categories[title] = category
            self.write_out(self.style.ITEM('OK\n'))
        return categories

    def import_tags(self, tag_nodes):
        """
        Import all the tags form 'wp:tag' nodes,
        because tags in 'item' nodes are not necessarily
        all the tags, then use only the nicename, because it's like
        a slug and the true tag name may be not valid for url usage.
        """
        self.write_out(self.style.STEP('- Importing tags\n'))
        for tag_node in tag_nodes:
            tag_name = tag_node.find(
                '{%s}tag_slug' % WP_NS).text[:50]
            self.write_out('> %s... ' % tag_name)
            Tag.objects.get_or_create(name=tag_name)
            self.write_out(self.style.ITEM('OK\n'))

    def get_entry_tags(self, categories):
        """
        Return a list of entry's tags,
        by using the nicename for url compatibility.
        """
        tags = []
        for category in categories:
            domain = category.attrib.get('domain', 'category')
            if 'tag' in domain and category.attrib.get('nicename'):
                tags.append(category.attrib.get('nicename'))
        return tags

    def get_entry_categories(self, category_nodes):
        """
        Return a list of entry's categories
        based on imported categories.
        """
        categories = []
        for category_node in category_nodes:
            domain = category_node.attrib.get('domain')
            if domain == 'category':
                categories.append(self.categories[category_node.text])
        return categories

    def import_entry(self, title, content, item_node):
        """
        Importing an entry but some data are missing like
        related entries, start_publication and end_publication.
        start_publication and creation_date will use the same value,
        wich is always in Wordpress $post->post_date.
        """
        creation_date = datetime.strptime(
            item_node.find('{%s}post_date_gmt' % WP_NS).text,
            '%Y-%m-%d %H:%M:%S')
        if settings.USE_TZ:
            creation_date = timezone.make_aware(
                creation_date, pytz.timezone('GMT'))

        excerpt = strip_tags(item_node.find(
            '{%sexcerpt/}encoded' % WP_NS).text or '')
        if not excerpt:
            if self.auto_excerpt:
                excerpt = Truncator(strip_tags(content)).words(50)
            else:
                excerpt = ''

        # Prefer use this function than
        # item_node.find('{%s}post_name' % WP_NS).text
        # Because slug can be not well formated
        slug = slugify(title)[:255] or 'post-%s' % item_node.find(
            '{%s}post_id' % WP_NS).text

        entry_dict = {
            'title': title,
            'content': content,
            'excerpt': excerpt,
            'tags': ', '.join(self.get_entry_tags(item_node.findall(
                'category'))),
            'status': self.REVERSE_STATUS[item_node.find(
                '{%s}status' % WP_NS).text],
            'comment_enabled': item_node.find(
                '{%s}comment_status' % WP_NS).text == 'open',
            'pingback_enabled': item_node.find(
                '{%s}ping_status' % WP_NS).text == 'open',
            'featured': item_node.find('{%s}is_sticky' % WP_NS).text == '1',
            'password': item_node.find('{%s}post_password' % WP_NS).text or '',
            'login_required': item_node.find(
                '{%s}status' % WP_NS).text == 'private',
            'last_update': timezone.now()}
        entry_dict['trackback_enabled'] = entry_dict['pingback_enabled']

        entry, created = Entry.objects.get_or_create(
            slug=slug, creation_date=creation_date,
            defaults=entry_dict)
        if created:
            entry.categories.add(*self.get_entry_categories(
                item_node.findall('category')))
            entry.authors.add(self.authors[item_node.find(
                '{http://purl.org/dc/elements/1.1/}creator').text])
            entry.sites.add(self.SITE)

        return entry, created

    def find_image_id(self, metadatas):
        for meta in metadatas:
            if meta.find('{%s}meta_key' % WP_NS).text == '_thumbnail_id':
                return meta.find('{%s}meta_value' % WP_NS).text

    def import_entries(self, items):
        """
        Loops over items and find entry to import,
        an entry need to have 'post_type' set to 'post' and
        have content.
        """
        self.write_out(self.style.STEP('- Importing entries\n'))

        for item_node in items:
            title = (item_node.find('title').text or '')[:255]
            post_type = item_node.find('{%s}post_type' % WP_NS).text
            content = item_node.find(
                '{http://purl.org/rss/1.0/modules/content/}encoded').text

            if post_type == 'post' and content and title:
                self.write_out('> %s... ' % title)
                entry, created = self.import_entry(title, content, item_node)
                if created:
                    self.write_out(self.style.ITEM('OK\n'))
                    image_id = self.find_image_id(
                        item_node.findall('{%s}postmeta' % WP_NS))
                    if image_id:
                        self.import_image(entry, items, image_id)
                    self.import_comments(entry, item_node.findall(
                        '{%s}comment' % WP_NS))
                else:
                    self.write_out(self.style.NOTICE(
                        'SKIPPED (already imported)\n'))
            else:
                self.write_out('> %s... ' % title, 2)
                self.write_out(self.style.NOTICE('SKIPPED (not a post)\n'), 2)

    def import_image(self, entry, items, image_id):
        for item in items:
            post_type = item.find('{%s}post_type' % WP_NS).text
            if (post_type == 'attachment' and
                    item.find('{%s}post_id' % WP_NS).text == image_id):
                title = 'Attachment %s' % item.find('title').text
                self.write_out(' > %s... ' % title)
                image_url = item.find('{%s}attachment_url' % WP_NS).text
                img_tmp = NamedTemporaryFile(delete=True)
                img_tmp.write(urlopen(image_url).read())
                img_tmp.flush()
                entry.image.save(os.path.basename(image_url),
                                 File(img_tmp))
                self.write_out(self.style.ITEM('OK\n'))

    def import_comments(self, entry, comment_nodes):
        """
        Loops over comments nodes and import then
        in django_comments.
        """
        for comment_node in comment_nodes:
            is_pingback = comment_node.find(
                '{%s}comment_type' % WP_NS).text == PINGBACK
            is_trackback = comment_node.find(
                '{%s}comment_type' % WP_NS).text == TRACKBACK

            title = 'Comment #%s' % (comment_node.find(
                '{%s}comment_id' % WP_NS).text)
            self.write_out(' > %s... ' % title)

            content = comment_node.find(
                '{%s}comment_content' % WP_NS).text
            if not content:
                self.write_out(self.style.NOTICE('SKIPPED (unfilled)\n'))
                return

            submit_date = datetime.strptime(
                comment_node.find('{%s}comment_date_gmt' % WP_NS).text,
                '%Y-%m-%d %H:%M:%S')
            if settings.USE_TZ:
                submit_date = timezone.make_aware(submit_date,
                                                  pytz.timezone('GMT'))

            approvation = comment_node.find(
                '{%s}comment_approved' % WP_NS).text
            is_public = True
            is_removed = False
            if approvation != '1':
                is_removed = True
            if approvation == 'spam':
                is_public = False

            comment_dict = {
                'content_object': entry,
                'site': self.SITE,
                'user_name': comment_node.find(
                    '{%s}comment_author' % WP_NS).text[:50],
                'user_email': comment_node.find(
                    '{%s}comment_author_email' % WP_NS).text or '',
                'user_url': comment_node.find(
                    '{%s}comment_author_url' % WP_NS).text or '',
                'comment': content,
                'submit_date': submit_date,
                'ip_address': comment_node.find(
                    '{%s}comment_author_IP' % WP_NS).text or None,
                'is_public': is_public,
                'is_removed': is_removed, }
            comment = comments.get_model()(**comment_dict)
            comment.save()
            if is_pingback:
                comment.flags.create(
                    user=get_user_flagger(), flag=PINGBACK)
            if is_trackback:
                comment.flags.create(
                    user=get_user_flagger(), flag=TRACKBACK)

            self.write_out(self.style.ITEM('OK\n'))
        entry.comment_count = entry.comments.count()
        entry.pingback_count = entry.pingbacks.count()
        entry.trackback_count = entry.trackbacks.count()
        entry.save(force_update=True)

########NEW FILE########
__FILENAME__ = zinnia2wp
"""Zinnia to WordPress command module"""
from django.conf import settings
from django.utils.encoding import smart_str
from django.contrib.sites.models import Site
from django.template.loader import render_to_string
from django.core.management.base import NoArgsCommand

from tagging.models import Tag

from zinnia import __version__
from zinnia.settings import PROTOCOL
from zinnia.models.entry import Entry
from zinnia.models.category import Category


class Command(NoArgsCommand):
    """Command object for exporting a Zinnia blog
    into WordPress via a WordPress eXtended RSS (WXR) file."""
    help = 'Export Zinnia to WXR file.'

    def handle_noargs(self, **options):
        site = Site.objects.get_current()
        blog_context = {'entries': Entry.objects.all(),
                        'categories': Category.objects.all(),
                        'tags': Tag.objects.usage_for_model(Entry),
                        'version': __version__,
                        'language': settings.LANGUAGE_CODE,
                        'site': site,
                        'site_url': '%s://%s' % (PROTOCOL, site.domain)}
        export = render_to_string('zinnia/wxr.xml', blog_context)
        print(smart_str(export))

########NEW FILE########
__FILENAME__ = managers
"""Managers of Zinnia"""
from django.db import models
from django.utils import timezone
from django.contrib.sites.models import Site

DRAFT = 0
HIDDEN = 1
PUBLISHED = 2


def tags_published():
    """
    Return the published tags.
    """
    from tagging.models import Tag
    from zinnia.models.entry import Entry
    tags_entry_published = Tag.objects.usage_for_queryset(
        Entry.published.all())
    # Need to do that until the issue #44 of django-tagging is fixed
    return Tag.objects.filter(name__in=[t.name for t in tags_entry_published])


def entries_published(queryset):
    """
    Return only the entries published.
    """
    now = timezone.now()
    return queryset.filter(
        models.Q(start_publication__lte=now) |
        models.Q(start_publication=None),
        models.Q(end_publication__gt=now) |
        models.Q(end_publication=None),
        status=PUBLISHED, sites=Site.objects.get_current())


class EntryPublishedManager(models.Manager):
    """
    Manager to retrieve published entries.
    """

    def get_queryset(self):
        """
        Return published entries.
        """
        return entries_published(
            super(EntryPublishedManager, self).get_queryset())

    def on_site(self):
        """
        Return entries published on current site.
        """
        return super(EntryPublishedManager, self).get_queryset().filter(
            sites=Site.objects.get_current())

    def search(self, pattern):
        """
        Top level search method on entries.
        """
        try:
            return self.advanced_search(pattern)
        except:
            return self.basic_search(pattern)

    def advanced_search(self, pattern):
        """
        Advanced search on entries.
        """
        from zinnia.search import advanced_search
        return advanced_search(pattern)

    def basic_search(self, pattern):
        """
        Basic search on entries.
        """
        lookup = None
        for pattern in pattern.split():
            query_part = models.Q(content__icontains=pattern) | \
                models.Q(excerpt__icontains=pattern) | \
                models.Q(title__icontains=pattern)
            if lookup is None:
                lookup = query_part
            else:
                lookup |= query_part

        return self.get_queryset().filter(lookup)


class EntryRelatedPublishedManager(models.Manager):
    """
    Manager to retrieve objects associated with published entries.
    """

    def get_queryset(self):
        """
        Return a queryset containing published entries.
        """
        now = timezone.now()
        return super(
            EntryRelatedPublishedManager, self).get_queryset().filter(
            models.Q(entries__start_publication__lte=now) |
            models.Q(entries__start_publication=None),
            models.Q(entries__end_publication__gt=now) |
            models.Q(entries__end_publication=None),
            entries__status=PUBLISHED,
            entries__sites=Site.objects.get_current()
            ).distinct()

########NEW FILE########
__FILENAME__ = markups
"""
Set of" markup" function to transform plain text into HTML for Zinnia.
Code originally provided by django.contrib.markups
"""
import warnings

from django.utils.encoding import force_text
from django.utils.encoding import force_bytes

from zinnia.settings import MARKDOWN_EXTENSIONS
from zinnia.settings import RESTRUCTUREDTEXT_SETTINGS


def textile(value):
    """
    Textile processing.
    """
    try:
        import textile
    except ImportError:
        warnings.warn("The Python textile library isn't installed.",
                      RuntimeWarning)
        return value

    return textile.textile(force_bytes(value),
                           encoding='utf-8', output='utf-8')


def markdown(value, extensions=MARKDOWN_EXTENSIONS):
    """
    Markdown processing with optionally using various extensions
    that python-markdown supports.
    """
    try:
        import markdown
    except ImportError:
        warnings.warn("The Python markdown library isn't installed.",
                      RuntimeWarning)
        return value

    extensions = [e for e in extensions.split(',') if e]
    return markdown.markdown(force_text(value),
                             extensions, safe_mode=False)


def restructuredtext(value, settings=RESTRUCTUREDTEXT_SETTINGS):
    """
    RestructuredText processing with optionnally custom settings.
    """
    try:
        from docutils.core import publish_parts
    except ImportError:
        warnings.warn("The Python docutils library isn't installed.",
                      RuntimeWarning)
        return value

    parts = publish_parts(source=force_bytes(value),
                          writer_name='html4css1',
                          settings_overrides=settings)
    return force_text(parts['fragment'])

########NEW FILE########
__FILENAME__ = 0001_initial
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

from zinnia.migrations import user_name
from zinnia.migrations import user_table
from zinnia.migrations import user_orm_label
from zinnia.migrations import user_model_label


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Adding model 'Category'
        db.create_table('zinnia_category', (
            ('slug', self.gf('django.db.models.fields.SlugField')(max_length=50, db_index=True)),
            ('description', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=50)),
        ))
        db.send_create_signal('zinnia', ['Category'])

        # Adding model 'Entry'
        db.create_table('zinnia_entry', (
            ('status', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('last_update', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('comment_enabled', self.gf('django.db.models.fields.BooleanField')(default=True, blank=True)),
            ('tags', self.gf('tagging.fields.TagField')()),
            ('image', self.gf('django.db.models.fields.files.ImageField')(max_length=100, blank=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('excerpt', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('slug', self.gf('django.db.models.fields.SlugField')(max_length=50, db_index=True)),
            ('content', self.gf('django.db.models.fields.TextField')()),
            ('end_publication', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime(2042, 3, 15, 0, 0))),
            ('start_publication', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('creation_date', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
        ))
        db.send_create_signal('zinnia', ['Entry'])

        # Adding M2M table for field sites on 'Entry'
        db.create_table('zinnia_entry_sites', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('entry', models.ForeignKey(orm['zinnia.entry'], null=False)),
            ('site', models.ForeignKey(orm['sites.site'], null=False))
        ))
        db.create_unique('zinnia_entry_sites', ['entry_id', 'site_id'])

        # Adding M2M table for field related on 'Entry'
        db.create_table('zinnia_entry_related', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('from_entry', models.ForeignKey(orm['zinnia.entry'], null=False)),
            ('to_entry', models.ForeignKey(orm['zinnia.entry'], null=False))
        ))
        db.create_unique('zinnia_entry_related', ['from_entry_id', 'to_entry_id'])

        # Adding M2M table for field categories on 'Entry'
        db.create_table('zinnia_entry_categories', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('entry', models.ForeignKey(orm['zinnia.entry'], null=False)),
            ('category', models.ForeignKey(orm['zinnia.category'], null=False))
        ))
        db.create_unique('zinnia_entry_categories', ['entry_id', 'category_id'])

        # Adding M2M table for field authors on 'Entry'
        db.create_table('zinnia_entry_authors', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('entry', models.ForeignKey(orm['zinnia.entry'], null=False)),
            ('user', models.ForeignKey(orm[user_orm_label], null=False))
        ))
        db.create_unique('zinnia_entry_authors', ['entry_id', 'user_id'])

    def backwards(self, orm):

        # Deleting model 'Category'
        db.delete_table('zinnia_category')

        # Deleting model 'Entry'
        db.delete_table('zinnia_entry')

        # Removing M2M table for field sites on 'Entry'
        db.delete_table('zinnia_entry_sites')

        # Removing M2M table for field related on 'Entry'
        db.delete_table('zinnia_entry_related')

        # Removing M2M table for field categories on 'Entry'
        db.delete_table('zinnia_entry_categories')

        # Removing M2M table for field authors on 'Entry'
        db.delete_table('zinnia_entry_authors')

    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        user_model_label: {
            'Meta': {'object_name': user_name, 'db_table': "'%s'" % user_table},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'sites.site': {
            'Meta': {'object_name': 'Site', 'db_table': "'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'zinnia.category': {
            'Meta': {'object_name': 'Category'},
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'zinnia.entry': {
            'Meta': {'object_name': 'Entry'},
            'authors': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['%s']" % user_orm_label, 'blank': 'True'}),
            'categories': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['zinnia.Category']"}),
            'comment_enabled': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'content': ('django.db.models.fields.TextField', [], {}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'end_publication': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2042, 3, 15, 0, 0)'}),
            'excerpt': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'blank': 'True'}),
            'last_update': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'related': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'related_rel_+'", 'null': 'True', 'to': "orm['zinnia.Entry']"}),
            'sites': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['sites.Site']"}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'}),
            'start_publication': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'status': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'tags': ('tagging.fields.TagField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['zinnia']

########NEW FILE########
__FILENAME__ = 0002_auto__add_field_entry_pingback_enabled
from south.db import db
from south.v2 import SchemaMigration

from zinnia.migrations import user_name
from zinnia.migrations import user_table
from zinnia.migrations import user_orm_label
from zinnia.migrations import user_model_label


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Adding field 'Entry.pingback_enabled'
        db.add_column('zinnia_entry', 'pingback_enabled', self.gf('django.db.models.fields.BooleanField')(default=True, blank=True))

    def backwards(self, orm):

        # Deleting field 'Entry.pingback_enabled'
        db.delete_column('zinnia_entry', 'pingback_enabled')

    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        user_model_label: {
            'Meta': {'object_name': user_name, 'db_table': "'%s'" % user_table},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'sites.site': {
            'Meta': {'object_name': 'Site', 'db_table': "'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'zinnia.category': {
            'Meta': {'object_name': 'Category'},
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'zinnia.entry': {
            'Meta': {'object_name': 'Entry'},
            'authors': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['%s']" % user_orm_label, 'symmetrical': 'False', 'blank': 'True'}),
            'categories': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['zinnia.Category']", 'symmetrical': 'False'}),
            'comment_enabled': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'content': ('django.db.models.fields.TextField', [], {}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'end_publication': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2042, 3, 15, 0, 0)'}),
            'excerpt': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'blank': 'True'}),
            'last_update': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'pingback_enabled': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'related': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'related_rel_+'", 'null': 'True', 'to': "orm['zinnia.Entry']"}),
            'sites': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['sites.Site']", 'symmetrical': 'False'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'}),
            'start_publication': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'status': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'tags': ('tagging.fields.TagField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['zinnia']

########NEW FILE########
__FILENAME__ = 0003_auto__chg_field_category_title__chg_field_category_slug__add_unique_ca
from south.db import db
from south.v2 import SchemaMigration

from zinnia.migrations import user_name
from zinnia.migrations import user_table
from zinnia.migrations import user_orm_label
from zinnia.migrations import user_model_label


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'Category.title'
        db.alter_column('zinnia_category', 'title', self.gf('django.db.models.fields.CharField')(max_length=255))

        # Changing field 'Category.slug'
        db.alter_column('zinnia_category', 'slug', self.gf('django.db.models.fields.SlugField')(unique=True, max_length=255))

        # Adding unique constraint on 'Category', fields ['slug']
        db.create_unique('zinnia_category', ['slug'])

        # Changing field 'Entry.title'
        db.alter_column('zinnia_entry', 'title', self.gf('django.db.models.fields.CharField')(max_length=255))

        # Changing field 'Entry.slug'
        db.alter_column('zinnia_entry', 'slug', self.gf('django.db.models.fields.SlugField')(max_length=255))

    def backwards(self, orm):

        # Changing field 'Category.title'
        db.alter_column('zinnia_category', 'title', self.gf('django.db.models.fields.CharField')(max_length=50))

        # Changing field 'Category.slug'
        db.alter_column('zinnia_category', 'slug', self.gf('django.db.models.fields.SlugField')(max_length=50))

        # Removing unique constraint on 'Category', fields ['slug']
        db.delete_unique('zinnia_category', ['slug'])

        # Changing field 'Entry.title'
        db.alter_column('zinnia_entry', 'title', self.gf('django.db.models.fields.CharField')(max_length=100))

        # Changing field 'Entry.slug'
        db.alter_column('zinnia_entry', 'slug', self.gf('django.db.models.fields.SlugField')(max_length=50))

    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        user_model_label: {
            'Meta': {'object_name': user_name, 'db_table': "'%s'" % user_table},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'sites.site': {
            'Meta': {'object_name': 'Site', 'db_table': "'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'zinnia.category': {
            'Meta': {'object_name': 'Category'},
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '255', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'zinnia.entry': {
            'Meta': {'object_name': 'Entry'},
            'authors': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['%s']" % user_orm_label, 'symmetrical': 'False', 'blank': 'True'}),
            'categories': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['zinnia.Category']", 'symmetrical': 'False'}),
            'comment_enabled': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'content': ('django.db.models.fields.TextField', [], {}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'end_publication': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2042, 3, 15, 0, 0)'}),
            'excerpt': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'blank': 'True'}),
            'last_update': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'pingback_enabled': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'related': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'related_rel_+'", 'null': 'True', 'to': "orm['zinnia.Entry']"}),
            'sites': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['sites.Site']", 'symmetrical': 'False'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '255', 'db_index': 'True'}),
            'start_publication': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'status': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'tags': ('tagging.fields.TagField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        }
    }

    complete_apps = ['zinnia']

########NEW FILE########
__FILENAME__ = 0004_mptt_categories
from south.db import db
from south.v2 import SchemaMigration

from zinnia.migrations import user_name
from zinnia.migrations import user_table
from zinnia.migrations import user_orm_label
from zinnia.migrations import user_model_label


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Adding field 'Category.parent'
        db.add_column('zinnia_category', 'parent', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='children', null=True, to=orm['zinnia.Category']), keep_default=False)

        # Adding field 'Category.lft'
        db.add_column('zinnia_category', 'lft', self.gf('django.db.models.fields.PositiveIntegerField')(default=0, db_index=True), keep_default=False)

        # Adding field 'Category.rght'
        db.add_column('zinnia_category', 'rght', self.gf('django.db.models.fields.PositiveIntegerField')(default=0, db_index=True), keep_default=False)

        # Adding field 'Category.tree_id'
        db.add_column('zinnia_category', 'tree_id', self.gf('django.db.models.fields.PositiveIntegerField')(default=0, db_index=True), keep_default=False)

        # Adding field 'Category.level'
        db.add_column('zinnia_category', 'level', self.gf('django.db.models.fields.PositiveIntegerField')(default=0, db_index=True), keep_default=False)

    def backwards(self, orm):

        # Deleting field 'Category.parent'
        db.delete_column('zinnia_category', 'parent_id')

        # Deleting field 'Category.lft'
        db.delete_column('zinnia_category', 'lft')

        # Deleting field 'Category.rght'
        db.delete_column('zinnia_category', 'rght')

        # Deleting field 'Category.tree_id'
        db.delete_column('zinnia_category', 'tree_id')

        # Deleting field 'Category.level'
        db.delete_column('zinnia_category', 'level')

    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        user_model_label: {
            'Meta': {'object_name': user_name, 'db_table': "'%s'" % user_table},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'sites.site': {
            'Meta': {'object_name': 'Site', 'db_table': "'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'zinnia.category': {
            'Meta': {'object_name': 'Category'},
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['zinnia.Category']"}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '255', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        },
        'zinnia.entry': {
            'Meta': {'object_name': 'Entry'},
            'authors': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['%s']" % user_orm_label, 'symmetrical': 'False', 'blank': 'True'}),
            'categories': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['zinnia.Category']", 'symmetrical': 'False'}),
            'comment_enabled': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'content': ('django.db.models.fields.TextField', [], {}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'end_publication': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2042, 3, 15, 0, 0)'}),
            'excerpt': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'blank': 'True'}),
            'last_update': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'pingback_enabled': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'related': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'related_rel_+'", 'null': 'True', 'to': "orm['zinnia.Entry']"}),
            'sites': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['sites.Site']", 'symmetrical': 'False'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '255', 'db_index': 'True'}),
            'start_publication': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'status': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'tags': ('tagging.fields.TagField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        }
    }

    complete_apps = ['zinnia']

########NEW FILE########
__FILENAME__ = 0005_entry_protection
from south.db import db
from south.v2 import SchemaMigration

from zinnia.migrations import user_name
from zinnia.migrations import user_table
from zinnia.migrations import user_orm_label
from zinnia.migrations import user_model_label


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Adding field 'Entry.login_required'
        db.add_column('zinnia_entry', 'login_required', self.gf('django.db.models.fields.BooleanField')(default=False, blank=True), keep_default=False)

        # Adding field 'Entry.password'
        db.add_column('zinnia_entry', 'password', self.gf('django.db.models.fields.CharField')(default='', max_length=50, blank=True), keep_default=False)

    def backwards(self, orm):

        # Deleting field 'Entry.login_required'
        db.delete_column('zinnia_entry', 'login_required')

        # Deleting field 'Entry.password'
        db.delete_column('zinnia_entry', 'password')

    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        user_model_label: {
            'Meta': {'object_name': user_name, 'db_table': "'%s'" % user_table},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'sites.site': {
            'Meta': {'object_name': 'Site', 'db_table': "'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'zinnia.category': {
            'Meta': {'object_name': 'Category'},
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['zinnia.Category']"}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '255', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        },
        'zinnia.entry': {
            'Meta': {'object_name': 'Entry'},
            'authors': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['%s']" % user_orm_label, 'symmetrical': 'False', 'blank': 'True'}),
            'categories': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['zinnia.Category']", 'symmetrical': 'False'}),
            'comment_enabled': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'content': ('django.db.models.fields.TextField', [], {}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'end_publication': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2042, 3, 15, 0, 0)'}),
            'excerpt': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'blank': 'True'}),
            'last_update': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'login_required': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'pingback_enabled': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'related': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'related_rel_+'", 'null': 'True', 'to': "orm['zinnia.Entry']"}),
            'sites': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['sites.Site']", 'symmetrical': 'False'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '255', 'db_index': 'True'}),
            'start_publication': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'status': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'tags': ('tagging.fields.TagField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        }
    }

    complete_apps = ['zinnia']

########NEW FILE########
__FILENAME__ = 0006_entry_template
from south.db import db
from south.v2 import SchemaMigration

from zinnia.migrations import user_name
from zinnia.migrations import user_table
from zinnia.migrations import user_orm_label
from zinnia.migrations import user_model_label


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Adding field 'Entry.template'
        db.add_column('zinnia_entry', 'template', self.gf('django.db.models.fields.CharField')(default='zinnia/entry_detail.html', max_length=250), keep_default=False)

    def backwards(self, orm):

        # Deleting field 'Entry.template'
        db.delete_column('zinnia_entry', 'template')

    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        user_model_label: {
            'Meta': {'object_name': user_name, 'db_table': "'%s'" % user_table},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'sites.site': {
            'Meta': {'object_name': 'Site', 'db_table': "'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'zinnia.category': {
            'Meta': {'object_name': 'Category'},
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['zinnia.Category']"}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '255', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        },
        'zinnia.entry': {
            'Meta': {'object_name': 'Entry'},
            'authors': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['%s']" % user_orm_label, 'symmetrical': 'False', 'blank': 'True'}),
            'categories': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['zinnia.Category']", 'symmetrical': 'False'}),
            'comment_enabled': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'content': ('django.db.models.fields.TextField', [], {}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'end_publication': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2042, 3, 15, 0, 0)'}),
            'excerpt': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'blank': 'True'}),
            'last_update': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'login_required': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'pingback_enabled': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'related': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'related_rel_+'", 'null': 'True', 'to': "orm['zinnia.Entry']"}),
            'sites': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['sites.Site']", 'symmetrical': 'False'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '255', 'db_index': 'True'}),
            'start_publication': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'status': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'tags': ('tagging.fields.TagField', [], {}),
            'template': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        }
    }

    complete_apps = ['zinnia']

########NEW FILE########
__FILENAME__ = 0007_entry_featured
from south.db import db
from south.v2 import SchemaMigration

from zinnia.migrations import user_name
from zinnia.migrations import user_table
from zinnia.migrations import user_orm_label
from zinnia.migrations import user_model_label


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Adding field 'Entry.featured'
        db.add_column('zinnia_entry', 'featured', self.gf('django.db.models.fields.BooleanField')(default=False), keep_default=False)

    def backwards(self, orm):

        # Deleting field 'Entry.featured'
        db.delete_column('zinnia_entry', 'featured')

    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        user_model_label: {
            'Meta': {'object_name': user_name, 'db_table': "'%s'" % user_table},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'sites.site': {
            'Meta': {'ordering': "('domain',)", 'object_name': 'Site', 'db_table': "'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'zinnia.category': {
            'Meta': {'ordering': "['title']", 'object_name': 'Category'},
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['zinnia.Category']"}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '255', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        },
        'zinnia.entry': {
            'Meta': {'ordering': "['-creation_date']", 'object_name': 'Entry'},
            'authors': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['%s']" % user_orm_label, 'symmetrical': 'False', 'blank': 'True'}),
            'categories': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['zinnia.Category']", 'null': 'True', 'blank': 'True'}),
            'comment_enabled': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'content': ('django.db.models.fields.TextField', [], {}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'end_publication': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2042, 3, 15, 0, 0)'}),
            'excerpt': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'blank': 'True'}),
            'last_update': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'login_required': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'pingback_enabled': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'related': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'related_rel_+'", 'null': 'True', 'to': "orm['zinnia.Entry']"}),
            'sites': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['sites.Site']", 'symmetrical': 'False'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '255', 'db_index': 'True'}),
            'start_publication': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'status': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'tags': ('tagging.fields.TagField', [], {}),
            'template': ('django.db.models.fields.CharField', [], {'default': "'zinnia/entry_detail.html'", 'max_length': '250'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        }
    }

    complete_apps = ['zinnia']

########NEW FILE########
__FILENAME__ = 0008_add_status_permission
from django.db import connection
from django.db.transaction import set_autocommit

from south.v2 import DataMigration

from zinnia.migrations import user_name
from zinnia.migrations import user_table
from zinnia.migrations import user_orm_label
from zinnia.migrations import user_model_label


class Migration(DataMigration):

    def forwards(self, orm):
        """Create the new permission for changing status"""
        if connection.vendor == 'sqlite':
            set_autocommit(True)
        ct, created = orm['contenttypes.ContentType'].objects.get_or_create(
            model='entry', app_label='zinnia')
        perm, created = orm['auth.permission'].objects.get_or_create(
            content_type=ct, codename='can_change_status',
            defaults={'name': 'Can change status'})

    def backwards(self, orm):
        """Delete the new permission for changing status"""
        ct = orm['contenttypes.ContentType'].objects.get(
            model='entry', app_label='zinnia')
        perm = orm['auth.permission'].objects.get(
            content_type=ct, codename='can_change_status')
        perm.delete()

    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.message': {
            'Meta': {'object_name': 'Message'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'_message_set'", 'to': "orm['%s']" % user_orm_label})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        user_model_label: {
            'Meta': {'object_name': user_name, 'db_table': "'%s'" % user_table},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'sites.site': {
            'Meta': {'ordering': "('domain',)", 'object_name': 'Site', 'db_table': "'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'zinnia.category': {
            'Meta': {'ordering': "['title']", 'object_name': 'Category'},
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['zinnia.Category']"}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '255', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        },
        'zinnia.entry': {
            'Meta': {'ordering': "['-creation_date']", 'object_name': 'Entry'},
            'authors': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'entries'", 'blank': 'True', 'to': "orm['%s']" % user_orm_label}),
            'categories': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'entries'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['zinnia.Category']"}),
            'comment_enabled': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'content': ('django.db.models.fields.TextField', [], {}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'end_publication': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2042, 3, 15, 0, 0)'}),
            'excerpt': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'blank': 'True'}),
            'last_update': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'login_required': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'pingback_enabled': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'related': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'related_rel_+'", 'null': 'True', 'to': "orm['zinnia.Entry']"}),
            'sites': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'entries'", 'symmetrical': 'False', 'to': "orm['sites.Site']"}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '255', 'db_index': 'True'}),
            'start_publication': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'status': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'tags': ('tagging.fields.TagField', [], {}),
            'template': ('django.db.models.fields.CharField', [], {'default': "'zinnia/entry_detail.html'", 'max_length': '250'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        }
    }

    complete_apps = ['contenttypes', 'auth', 'zinnia']

########NEW FILE########
__FILENAME__ = 0009_change_mptt_field
from south.db import db
from south.v2 import SchemaMigration

from zinnia.migrations import user_name
from zinnia.migrations import user_table
from zinnia.migrations import user_orm_label
from zinnia.migrations import user_model_label


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Changing field 'Category.parent'
        db.alter_column('zinnia_category', 'parent_id', self.gf('mptt.fields.TreeForeignKey')(null=True, to=orm['zinnia.Category']))

    def backwards(self, orm):
        # Changing field 'Category.parent'
        db.alter_column('zinnia_category', 'parent_id', self.gf('django.db.models.fields.related.ForeignKey')(null=True, to=orm['zinnia.Category']))

    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        user_model_label: {
            'Meta': {'object_name': user_name, 'db_table': "'%s'" % user_table},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 5, 11, 10, 16, 27, 936575)'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 5, 11, 10, 16, 27, 936424)'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'sites.site': {
            'Meta': {'ordering': "('domain',)", 'object_name': 'Site', 'db_table': "'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'zinnia.category': {
            'Meta': {'ordering': "['title']", 'object_name': 'Category'},
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'parent': ('mptt.fields.TreeForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['zinnia.Category']"}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '255', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        },
        'zinnia.entry': {
            'Meta': {'ordering': "['-creation_date']", 'object_name': 'Entry'},
            'authors': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'entries'", 'blank': 'True', 'to': "orm['%s']" % user_orm_label}),
            'categories': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'entries'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['zinnia.Category']"}),
            'comment_enabled': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'content': ('django.db.models.fields.TextField', [], {}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'end_publication': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2042, 3, 15, 0, 0)'}),
            'excerpt': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'blank': 'True'}),
            'last_update': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'login_required': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'pingback_enabled': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'related': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'related_rel_+'", 'null': 'True', 'to': "orm['zinnia.Entry']"}),
            'sites': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'entries'", 'symmetrical': 'False', 'to': "orm['sites.Site']"}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '255', 'db_index': 'True'}),
            'start_publication': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'status': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'tags': ('tagging.fields.TagField', [], {}),
            'template': ('django.db.models.fields.CharField', [], {'default': "'entry_detail.html'", 'max_length': '250'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        }
    }

    complete_apps = ['zinnia']

########NEW FILE########
__FILENAME__ = 0010_publication_dates_unrequired
from south.db import db
from south.v2 import SchemaMigration

from zinnia.migrations import user_name
from zinnia.migrations import user_table
from zinnia.migrations import user_orm_label
from zinnia.migrations import user_model_label


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Changing field 'Entry.end_publication'
        db.alter_column('zinnia_entry', 'end_publication', self.gf('django.db.models.fields.DateTimeField')(null=True))

        # Changing field 'Entry.start_publication'
        db.alter_column('zinnia_entry', 'start_publication', self.gf('django.db.models.fields.DateTimeField')(null=True))

    def backwards(self, orm):
        # Changing field 'Entry.end_publication'
        db.alter_column('zinnia_entry', 'end_publication', self.gf('django.db.models.fields.DateTimeField')())

        # Changing field 'Entry.start_publication'
        db.alter_column('zinnia_entry', 'start_publication', self.gf('django.db.models.fields.DateTimeField')())

    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        user_model_label: {
            'Meta': {'object_name': user_name, 'db_table': "'%s'" % user_table},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 5, 11, 10, 22, 25, 800658)'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 5, 11, 10, 22, 25, 800492)'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'sites.site': {
            'Meta': {'ordering': "('domain',)", 'object_name': 'Site', 'db_table': "'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'zinnia.category': {
            'Meta': {'ordering': "['title']", 'object_name': 'Category'},
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'parent': ('mptt.fields.TreeForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['zinnia.Category']"}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '255', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        },
        'zinnia.entry': {
            'Meta': {'ordering': "['-creation_date']", 'object_name': 'Entry'},
            'authors': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'entries'", 'blank': 'True', 'to': "orm['%s']" % user_orm_label}),
            'categories': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'entries'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['zinnia.Category']"}),
            'comment_enabled': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'content': ('django.db.models.fields.TextField', [], {}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'end_publication': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'excerpt': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'blank': 'True'}),
            'last_update': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'login_required': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'pingback_enabled': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'related': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'related_rel_+'", 'null': 'True', 'to': "orm['zinnia.Entry']"}),
            'sites': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'entries'", 'symmetrical': 'False', 'to': "orm['sites.Site']"}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '255', 'db_index': 'True'}),
            'start_publication': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'status': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'tags': ('tagging.fields.TagField', [], {}),
            'template': ('django.db.models.fields.CharField', [], {'default': "'entry_detail.html'", 'max_length': '250'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        }
    }

    complete_apps = ['zinnia']

########NEW FILE########
__FILENAME__ = 0011_author_proxy
from south.db import db
from south.v2 import SchemaMigration

from zinnia.migrations import user_name
from zinnia.migrations import user_table
from zinnia.migrations import user_orm_label
from zinnia.migrations import user_model_label


class Migration(SchemaMigration):

    def forwards(self, orm):
        db.delete_unique('zinnia_entry_authors', ['entry_id', 'user_id'])
        db.rename_column('zinnia_entry_authors', 'user_id', 'author_id')
        db.create_unique('zinnia_entry_authors', ['entry_id', 'author_id'])

    def backwards(self, orm):
        db.delete_unique('zinnia_entry_authors', ['entry_id', 'author_id'])
        db.rename_column('zinnia_entry_authors', 'author_id', 'user_id')
        db.create_unique('zinnia_entry_authors', ['entry_id', 'user_id'])

    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        user_model_label: {
            'Meta': {'object_name': user_name, 'db_table': "'%s'" % user_table},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'sites.site': {
            'Meta': {'ordering': "('domain',)", 'object_name': 'Site', 'db_table': "'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'zinnia.category': {
            'Meta': {'ordering': "['title']", 'object_name': 'Category'},
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'parent': ('mptt.fields.TreeForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['zinnia.Category']"}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '255'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        },
        'zinnia.entry': {
            'Meta': {'ordering': "['-creation_date']", 'object_name': 'Entry'},
            'authors': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'entries'", 'blank': 'True', 'to': "orm['%s']" % user_orm_label}),
            'categories': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'entries'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['zinnia.Category']"}),
            'comment_enabled': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'content': ('django.db.models.fields.TextField', [], {}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'end_publication': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'excerpt': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'blank': 'True'}),
            'last_update': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'login_required': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'pingback_enabled': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'related': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'related_rel_+'", 'null': 'True', 'to': "orm['zinnia.Entry']"}),
            'sites': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'entries'", 'symmetrical': 'False', 'to': "orm['sites.Site']"}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '255'}),
            'start_publication': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'status': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'tags': ('tagging.fields.TagField', [], {}),
            'template': ('django.db.models.fields.CharField', [], {'default': "'entry_detail.html'", 'max_length': '250'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        }
    }

    complete_apps = ['zinnia']

########NEW FILE########
__FILENAME__ = 0012_discussion_count
from south.db import db
from south.v2 import SchemaMigration

from zinnia.migrations import user_name
from zinnia.migrations import user_table
from zinnia.migrations import user_orm_label
from zinnia.migrations import user_model_label


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Entry.comment_count'
        db.add_column('zinnia_entry', 'comment_count',
                      self.gf('django.db.models.fields.IntegerField')(default=0),
                      keep_default=False)

        # Adding field 'Entry.pingback_count'
        db.add_column('zinnia_entry', 'pingback_count',
                      self.gf('django.db.models.fields.IntegerField')(default=0),
                      keep_default=False)

        # Adding field 'Entry.trackback_count'
        db.add_column('zinnia_entry', 'trackback_count',
                      self.gf('django.db.models.fields.IntegerField')(default=0),
                      keep_default=False)

    def backwards(self, orm):
        # Deleting field 'Entry.comment_count'
        db.delete_column('zinnia_entry', 'comment_count')

        # Deleting field 'Entry.pingback_count'
        db.delete_column('zinnia_entry', 'pingback_count')

        # Deleting field 'Entry.trackback_count'
        db.delete_column('zinnia_entry', 'trackback_count')

    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        user_model_label: {
            'Meta': {'object_name': user_name, 'db_table': "'%s'" % user_table},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'sites.site': {
            'Meta': {'ordering': "('domain',)", 'object_name': 'Site', 'db_table': "'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'zinnia.category': {
            'Meta': {'ordering': "['title']", 'object_name': 'Category'},
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'parent': ('mptt.fields.TreeForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['zinnia.Category']"}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '255'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        },
        'zinnia.entry': {
            'Meta': {'ordering': "['-creation_date']", 'object_name': 'Entry'},
            'authors': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'entries'", 'blank': 'True', 'to': "orm['%s']" % user_orm_label}),
            'categories': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'entries'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['zinnia.Category']"}),
            'comment_count': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'comment_enabled': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'content': ('django.db.models.fields.TextField', [], {}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'end_publication': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'excerpt': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'blank': 'True'}),
            'last_update': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'login_required': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'pingback_count': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'pingback_enabled': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'related': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'related_rel_+'", 'null': 'True', 'to': "orm['zinnia.Entry']"}),
            'sites': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'entries'", 'symmetrical': 'False', 'to': "orm['sites.Site']"}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '255'}),
            'start_publication': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'status': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'tags': ('tagging.fields.TagField', [], {}),
            'template': ('django.db.models.fields.CharField', [], {'default': "'entry_detail.html'", 'max_length': '250'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'trackback_count': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        }
    }

    complete_apps = ['zinnia']

########NEW FILE########
__FILENAME__ = 0013_compute_discussion_count
from south.v2 import DataMigration

from django.db.models import Q

from django_comments.models import CommentFlag

from zinnia.flags import PINGBACK
from zinnia.flags import TRACKBACK
from zinnia.migrations import user_name
from zinnia.migrations import user_table
from zinnia.migrations import user_orm_label
from zinnia.migrations import user_model_label


class Migration(DataMigration):

    def forwards(self, orm):
        entry_content_type = orm['contenttypes.ContentType'].objects.get(
            app_label='zinnia', model='entry')
        for entry in orm['zinnia.Entry'].objects.all():
            discussion_qs = orm['comments.Comment'].objects.filter(
                content_type=entry_content_type, object_pk=entry.pk,
                is_public=True, is_removed=False)
            entry.comment_count = discussion_qs.filter(
                Q(flags=None) |
                Q(flags__flag=CommentFlag.MODERATOR_APPROVAL)).count()
            entry.trackback_count = discussion_qs.filter(
                flags__flag=TRACKBACK).count()
            entry.pingback_count = discussion_qs.filter(
                flags__flag=PINGBACK).count()
            entry.save()

    def backwards(self, orm):
        orm.Entry.objects.all().update(comment_count=0,
                                       pingback_count=0,
                                       trackback_count=0)

    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        user_model_label: {
            'Meta': {'object_name': user_name, 'db_table': "'%s'" % user_table},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'comments.comment': {
            'Meta': {'ordering': "('submit_date',)", 'object_name': 'Comment', 'db_table': "'django_comments'"},
            'comment': ('django.db.models.fields.TextField', [], {'max_length': '3000'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'content_type_set_for_comment'", 'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ip_address': ('django.db.models.fields.IPAddressField', [], {'max_length': '15', 'null': 'True', 'blank': 'True'}),
            'is_public': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_removed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'object_pk': ('django.db.models.fields.TextField', [], {}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sites.Site']"}),
            'submit_date': ('django.db.models.fields.DateTimeField', [], {'default': 'None'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'comment_comments'", 'null': 'True', 'to': "orm['%s']" % user_orm_label}),
            'user_email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'user_name': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'user_url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'})
        },
        'comments.commentflag': {
            'Meta': {'unique_together': "[('user', 'comment', 'flag')]", 'object_name': 'CommentFlag', 'db_table': "'django_comment_flags'"},
            'comment': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'flags'", 'to': "orm['comments.Comment']"}),
            'flag': ('django.db.models.fields.CharField', [], {'max_length': '30', 'db_index': 'True'}),
            'flag_date': ('django.db.models.fields.DateTimeField', [], {'default': 'None'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'comment_flags'", 'to': "orm['%s']" % user_orm_label})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'sites.site': {
            'Meta': {'ordering': "('domain',)", 'object_name': 'Site', 'db_table': "'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'zinnia.category': {
            'Meta': {'ordering': "['title']", 'object_name': 'Category'},
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'parent': ('mptt.fields.TreeForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['zinnia.Category']"}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '255'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        },
        'zinnia.entry': {
            'Meta': {'ordering': "['-creation_date']", 'object_name': 'Entry'},
            'authors': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'entries'", 'blank': 'True', 'to': "orm['%s']" % user_orm_label}),
            'categories': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'entries'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['zinnia.Category']"}),
            'comment_count': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'comment_enabled': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'content': ('django.db.models.fields.TextField', [], {}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'end_publication': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'excerpt': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'blank': 'True'}),
            'last_update': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'login_required': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'pingback_count': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'pingback_enabled': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'related': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'related_rel_+'", 'null': 'True', 'to': "orm['zinnia.Entry']"}),
            'sites': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'entries'", 'symmetrical': 'False', 'to': "orm['sites.Site']"}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '255'}),
            'start_publication': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'status': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'tags': ('tagging.fields.TagField', [], {}),
            'template': ('django.db.models.fields.CharField', [], {'default': "'entry_detail.html'", 'max_length': '250'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'trackback_count': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        }
    }

    complete_apps = ['comments', 'zinnia']
    symmetrical = True

########NEW FILE########
__FILENAME__ = 0014_trackback_enabled
from south.db import db
from south.v2 import SchemaMigration

from zinnia.migrations import user_name
from zinnia.migrations import user_table
from zinnia.migrations import user_orm_label
from zinnia.migrations import user_model_label


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Entry.trackback_enabled'
        db.add_column('zinnia_entry', 'trackback_enabled',
                      self.gf('django.db.models.fields.BooleanField')(default=True),
                      keep_default=False)

    def backwards(self, orm):
        # Deleting field 'Entry.trackback_enabled'
        db.delete_column('zinnia_entry', 'trackback_enabled')

    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        user_model_label: {
            'Meta': {'object_name': user_name, 'db_table': "'%s'" % user_table},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'sites.site': {
            'Meta': {'ordering': "('domain',)", 'object_name': 'Site', 'db_table': "'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'zinnia.category': {
            'Meta': {'ordering': "['title']", 'object_name': 'Category'},
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'parent': ('mptt.fields.TreeForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['zinnia.Category']"}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '255'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        },
        'zinnia.entry': {
            'Meta': {'ordering': "['-creation_date']", 'object_name': 'Entry'},
            'authors': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'entries'", 'blank': 'True', 'to': "orm['%s']" % user_orm_label}),
            'categories': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'entries'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['zinnia.Category']"}),
            'comment_count': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'comment_enabled': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'content': ('django.db.models.fields.TextField', [], {}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'end_publication': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'excerpt': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'blank': 'True'}),
            'last_update': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'login_required': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'pingback_count': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'pingback_enabled': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'related': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'related_rel_+'", 'null': 'True', 'to': "orm['zinnia.Entry']"}),
            'sites': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'entries'", 'symmetrical': 'False', 'to': "orm['sites.Site']"}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '255'}),
            'start_publication': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'status': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'tags': ('tagging.fields.TagField', [], {}),
            'template': ('django.db.models.fields.CharField', [], {'default': "'entry_detail.html'", 'max_length': '250'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'trackback_count': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'trackback_enabled': ('django.db.models.fields.BooleanField', [], {'default': 'True'})
        }
    }

    complete_apps = ['zinnia']

########NEW FILE########
__FILENAME__ = 0015_rename_template
from south.db import db
from south.v2 import SchemaMigration

from zinnia.migrations import user_name
from zinnia.migrations import user_table
from zinnia.migrations import user_orm_label
from zinnia.migrations import user_model_label


class Migration(SchemaMigration):

    def forwards(self, orm):
        db.rename_column('zinnia_entry', 'template', 'detail_template')

    def backwards(self, orm):
        db.rename_column('zinnia_entry', 'detail_template', 'template')

    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        user_model_label: {
            'Meta': {'object_name': user_name, 'db_table': "'%s'" % user_table},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'sites.site': {
            'Meta': {'ordering': "('domain',)", 'object_name': 'Site', 'db_table': "'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'zinnia.category': {
            'Meta': {'ordering': "['title']", 'object_name': 'Category'},
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'parent': ('mptt.fields.TreeForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['zinnia.Category']"}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '255'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        },
        'zinnia.entry': {
            'Meta': {'ordering': "['-creation_date']", 'object_name': 'Entry'},
            'authors': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'entries'", 'blank': 'True', 'to': "orm['%s']" % user_orm_label}),
            'categories': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'entries'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['zinnia.Category']"}),
            'comment_count': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'comment_enabled': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'content': ('django.db.models.fields.TextField', [], {}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'detail_template': ('django.db.models.fields.CharField', [], {'default': "'entry_detail.html'", 'max_length': '250'}),
            'end_publication': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'excerpt': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'blank': 'True'}),
            'last_update': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'login_required': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'pingback_count': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'pingback_enabled': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'related': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'related_rel_+'", 'null': 'True', 'to': "orm['zinnia.Entry']"}),
            'sites': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'entries'", 'symmetrical': 'False', 'to': "orm['sites.Site']"}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '255'}),
            'start_publication': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'status': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'tags': ('tagging.fields.TagField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'trackback_count': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'trackback_enabled': ('django.db.models.fields.BooleanField', [], {'default': 'True'})
        }
    }

    complete_apps = ['zinnia']

########NEW FILE########
__FILENAME__ = 0016_entry_content_template
from south.db import db
from south.v2 import SchemaMigration

from zinnia.migrations import user_name
from zinnia.migrations import user_table
from zinnia.migrations import user_orm_label
from zinnia.migrations import user_model_label


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Entry.content_template'
        db.add_column('zinnia_entry', 'content_template',
                      self.gf('django.db.models.fields.CharField')(default='zinnia/_entry_detail.html', max_length=250),
                      keep_default=False)

    def backwards(self, orm):
        # Deleting field 'Entry.content_template'
        db.delete_column('zinnia_entry', 'content_template')

    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        user_model_label: {
            'Meta': {'object_name': user_name, 'db_table': "'%s'" % user_table},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'sites.site': {
            'Meta': {'ordering': "('domain',)", 'object_name': 'Site', 'db_table': "'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'zinnia.category': {
            'Meta': {'ordering': "['title']", 'object_name': 'Category'},
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'parent': ('mptt.fields.TreeForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['zinnia.Category']"}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '255'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        },
        'zinnia.entry': {
            'Meta': {'ordering': "['-creation_date']", 'object_name': 'Entry'},
            'authors': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'entries'", 'blank': 'True', 'to': "orm['%s']" % user_orm_label}),
            'categories': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'entries'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['zinnia.Category']"}),
            'comment_count': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'comment_enabled': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'content': ('django.db.models.fields.TextField', [], {}),
            'content_template': ('django.db.models.fields.CharField', [], {'default': "'zinnia/_entry_detail.html'", 'max_length': '250'}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'detail_template': ('django.db.models.fields.CharField', [], {'default': "'entry_detail.html'", 'max_length': '250'}),
            'end_publication': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'excerpt': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'blank': 'True'}),
            'last_update': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'login_required': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'pingback_count': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'pingback_enabled': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'related': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'related_rel_+'", 'null': 'True', 'to': "orm['zinnia.Entry']"}),
            'sites': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'entries'", 'symmetrical': 'False', 'to': "orm['sites.Site']"}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '255'}),
            'start_publication': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'status': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'tags': ('tagging.fields.TagField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'trackback_count': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'trackback_enabled': ('django.db.models.fields.BooleanField', [], {'default': 'True'})
        }
    }

    complete_apps = ['zinnia']

########NEW FILE########
__FILENAME__ = 0017_index_together
from south.db import db
from south.v2 import SchemaMigration

from zinnia.migrations import user_name
from zinnia.migrations import user_table
from zinnia.migrations import user_orm_label
from zinnia.migrations import user_model_label


class Migration(SchemaMigration):

    def forwards(self, orm):
        db.create_index('zinnia_entry', ['slug', 'creation_date'])

    def backwards(self, orm):
        db.delete_index('zinnia_entry', ['slug', 'creation_date'])

    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        user_model_label: {
            'Meta': {'object_name': user_name, 'db_table': "'%s'" % user_table},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'sites.site': {
            'Meta': {'ordering': "('domain',)", 'object_name': 'Site', 'db_table': "'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'zinnia.category': {
            'Meta': {'ordering': "['title']", 'object_name': 'Category'},
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'parent': ('mptt.fields.TreeForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['zinnia.Category']"}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '255'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        },
        'zinnia.entry': {
            'Meta': {'ordering': "['-creation_date']", 'object_name': 'Entry', 'index_together': "[['slug', 'creation_date']]"},
            'Meta': {'ordering': "['-creation_date']", 'object_name': 'Entry'},
            'authors': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'entries'", 'blank': 'True', 'to': "orm['%s']" % user_orm_label}),
            'categories': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'entries'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['zinnia.Category']"}),
            'comment_count': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'comment_enabled': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'content': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'content_template': ('django.db.models.fields.CharField', [], {'default': "'zinnia/_entry_detail.html'", 'max_length': '250'}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'detail_template': ('django.db.models.fields.CharField', [], {'default': "'entry_detail.html'", 'max_length': '250'}),
            'end_publication': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'excerpt': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'blank': 'True'}),
            'last_update': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'login_required': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'pingback_count': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'pingback_enabled': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'related': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'related_rel_+'", 'null': 'True', 'to': "orm['zinnia.Entry']"}),
            'sites': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'entries'", 'symmetrical': 'False', 'to': "orm['sites.Site']"}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '255'}),
            'start_publication': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'status': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'tags': ('tagging.fields.TagField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'trackback_count': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'trackback_enabled': ('django.db.models.fields.BooleanField', [], {'default': 'True'})
        }
    }

    complete_apps = ['zinnia']

########NEW FILE########
__FILENAME__ = 0018_more_indexes
from south.db import db
from south.v2 import SchemaMigration

from zinnia.migrations import user_name
from zinnia.migrations import user_table
from zinnia.migrations import user_orm_label
from zinnia.migrations import user_model_label


class Migration(SchemaMigration):

    def forwards(self, orm):
        db.create_index('zinnia_entry', ['status'])
        db.create_index('zinnia_entry', ['start_publication'])
        db.create_index('zinnia_entry', ['creation_date'])
        db.create_index('zinnia_entry', ['end_publication'])
        db.create_index('zinnia_entry', [
            'status', 'creation_date',
            'start_publication', 'end_publication'])

    def backwards(self, orm):
        db.delete_index('zinnia_entry', [
            'status', 'creation_date',
            'start_publication', 'end_publication'])
        db.delete_index('zinnia_entry', ['end_publication'])
        db.delete_index('zinnia_entry', ['creation_date'])
        db.delete_index('zinnia_entry', ['start_publication'])
        db.delete_index('zinnia_entry', ['status'])


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        user_model_label: {
            'Meta': {'object_name': user_name, 'db_table': "'%s'" % user_table},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'user_set'", 'blank': 'True', 'to': "orm['auth.Group']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'user_set'", 'blank': 'True', 'to': "orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'sites.site': {
            'Meta': {'ordering': "('domain',)", 'object_name': 'Site', 'db_table': "'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'zinnia.category': {
            'Meta': {'ordering': "['title']", 'object_name': 'Category'},
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'parent': ('mptt.fields.TreeForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['zinnia.Category']"}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '255'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        },
        'zinnia.entry': {
            'Meta': {'ordering': "['-creation_date']", 'object_name': 'Entry', 'index_together': "[['slug', 'creation_date'], ['status', 'creation_date', 'start_publication', 'end_publication']]"},
            'authors': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'entries'", 'blank': 'True', 'to': "orm['%s']" % user_orm_label}),
            'categories': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'entries'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['zinnia.Category']"}),
            'comment_count': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'comment_enabled': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'content': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'content_template': ('django.db.models.fields.CharField', [], {'default': "'zinnia/_entry_detail.html'", 'max_length': '250'}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'detail_template': ('django.db.models.fields.CharField', [], {'default': "'entry_detail.html'", 'max_length': '250'}),
            'end_publication': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'excerpt': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'blank': 'True'}),
            'last_update': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'login_required': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'pingback_count': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'pingback_enabled': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'related': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'related_rel_+'", 'null': 'True', 'to': "orm['zinnia.Entry']"}),
            'sites': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'entries'", 'symmetrical': 'False', 'to': "orm['sites.Site']"}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '255'}),
            'start_publication': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'status': ('django.db.models.fields.IntegerField', [], {'default': '0', 'db_index': 'True'}),
            'tags': ('tagging.fields.TagField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'trackback_count': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'trackback_enabled': ('django.db.models.fields.BooleanField', [], {'default': 'True'})
        }
    }

    complete_apps = ['zinnia']

########NEW FILE########
__FILENAME__ = author
"""Author model for Zinnia"""
from django.db import models
from django.contrib.auth import get_user_model
from django.utils.encoding import python_2_unicode_compatible

from zinnia.managers import entries_published
from zinnia.managers import EntryRelatedPublishedManager


class AuthorPublishedManager(models.Model):
    """
    Proxy model manager to avoid overriding of
    the default User's manager and issue #307.
    """
    published = EntryRelatedPublishedManager()

    class Meta:
        abstract = True


@python_2_unicode_compatible
class Author(get_user_model(),
             AuthorPublishedManager):
    """
    Proxy model around :class:`django.contrib.auth.models.get_user_model`.
    """

    def entries_published(self):
        """
        Returns author's published entries.
        """
        return entries_published(self.entries)

    @models.permalink
    def get_absolute_url(self):
        """
        Builds and returns the author's URL based on his username.
        """
        return ('zinnia:author_detail', [self.get_username()])

    def __str__(self):
        """
        If the user has a full name, use it instead of the username.
        """
        return self.get_full_name() or self.get_username()

    class Meta:
        """
        Author's meta informations.
        """
        app_label = 'zinnia'
        proxy = True

########NEW FILE########
__FILENAME__ = category
"""Category model for Zinnia"""
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import python_2_unicode_compatible

from mptt.models import MPTTModel
from mptt.models import TreeForeignKey
from mptt.managers import TreeManager

from zinnia.managers import entries_published
from zinnia.managers import EntryRelatedPublishedManager


@python_2_unicode_compatible
class Category(MPTTModel):
    """
    Simple model for categorizing entries.
    """

    title = models.CharField(
        _('title'), max_length=255)

    slug = models.SlugField(
        _('slug'), unique=True, max_length=255,
        help_text=_("Used to build the category's URL."))

    description = models.TextField(
        _('description'), blank=True)

    parent = TreeForeignKey(
        'self',
        related_name='children',
        null=True, blank=True,
        verbose_name=_('parent category'))

    objects = TreeManager()
    published = EntryRelatedPublishedManager()

    def entries_published(self):
        """
        Returns category's published entries.
        """
        return entries_published(self.entries)

    @property
    def tree_path(self):
        """
        Returns category's tree path
        by concatening the slug of his ancestors.
        """
        if self.parent_id:
            return '/'.join(
                [ancestor.slug for ancestor in self.get_ancestors()] +
                [self.slug])
        return self.slug

    @models.permalink
    def get_absolute_url(self):
        """
        Builds and returns the category's URL
        based on his tree path.
        """
        return ('zinnia:category_detail', (self.tree_path,))

    def __str__(self):
        return self.title

    class Meta:
        """
        Category's meta informations.
        """
        app_label = 'zinnia'
        ordering = ['title']
        verbose_name = _('category')
        verbose_name_plural = _('categories')

    class MPTTMeta:
        """
        Category MPTT's meta informations.
        """
        order_insertion_by = ['title']

########NEW FILE########
__FILENAME__ = entry
"""Entry model for Zinnia"""
from zinnia.settings import ENTRY_BASE_MODEL
from zinnia.models_bases import load_model_class


class Entry(load_model_class(ENTRY_BASE_MODEL)):
    """
    The final Entry model based on inheritence.
    """

########NEW FILE########
__FILENAME__ = entry
"""Base entry models for Zinnia"""
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.html import strip_tags
from django.utils.html import linebreaks
from django.contrib.sites.models import Site
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import python_2_unicode_compatible

import django_comments as comments
from django_comments.models import CommentFlag

from tagging.fields import TagField
from tagging.utils import parse_tag_input

from zinnia.markups import textile
from zinnia.markups import markdown
from zinnia.markups import restructuredtext
from zinnia.preview import HTMLPreview
from zinnia.flags import PINGBACK, TRACKBACK
from zinnia.settings import UPLOAD_TO
from zinnia.settings import MARKUP_LANGUAGE
from zinnia.settings import ENTRY_DETAIL_TEMPLATES
from zinnia.settings import ENTRY_CONTENT_TEMPLATES
from zinnia.settings import AUTO_CLOSE_COMMENTS_AFTER
from zinnia.settings import AUTO_CLOSE_PINGBACKS_AFTER
from zinnia.settings import AUTO_CLOSE_TRACKBACKS_AFTER
from zinnia.managers import entries_published
from zinnia.managers import EntryPublishedManager
from zinnia.managers import DRAFT, HIDDEN, PUBLISHED
from zinnia.url_shortener import get_url_shortener


@python_2_unicode_compatible
class CoreEntry(models.Model):
    """
    Abstract core entry model class providing
    the fields and methods required for publishing
    content over time.
    """
    STATUS_CHOICES = ((DRAFT, _('draft')),
                      (HIDDEN, _('hidden')),
                      (PUBLISHED, _('published')))

    title = models.CharField(
        _('title'), max_length=255)

    slug = models.SlugField(
        _('slug'), max_length=255,
        unique_for_date='creation_date',
        help_text=_("Used to build the entry's URL."))

    status = models.IntegerField(
        _('status'), db_index=True,
        choices=STATUS_CHOICES, default=DRAFT)

    start_publication = models.DateTimeField(
        _('start publication'),
        db_index=True, blank=True, null=True,
        help_text=_('Start date of publication.'))

    end_publication = models.DateTimeField(
        _('end publication'),
        db_index=True, blank=True, null=True,
        help_text=_('End date of publication.'))

    sites = models.ManyToManyField(
        Site,
        related_name='entries',
        verbose_name=_('sites'),
        help_text=_('Sites where the entry will be published.'))

    creation_date = models.DateTimeField(
        _('creation date'),
        db_index=True, default=timezone.now,
        help_text=_("Used to build the entry's URL."))

    last_update = models.DateTimeField(
        _('last update'), default=timezone.now)

    objects = models.Manager()
    published = EntryPublishedManager()

    @property
    def is_actual(self):
        """
        Checks if an entry is within his publication period.
        """
        now = timezone.now()
        if self.start_publication and now < self.start_publication:
            return False

        if self.end_publication and now >= self.end_publication:
            return False
        return True

    @property
    def is_visible(self):
        """
        Checks if an entry is visible and published.
        """
        return self.is_actual and self.status == PUBLISHED

    @property
    def previous_entry(self):
        """
        Returns the previous published entry if exists.
        """
        return self.previous_next_entries[0]

    @property
    def next_entry(self):
        """
        Returns the next published entry if exists.
        """
        return self.previous_next_entries[1]

    @property
    def previous_next_entries(self):
        """
        Returns and caches a tuple containing the next
        and previous published entries.
        Only available if the entry instance is published.
        """
        previous_next = getattr(self, 'previous_next', None)

        if previous_next is None:
            if not self.is_visible:
                previous_next = (None, None)
                setattr(self, 'previous_next', previous_next)
                return previous_next

            entries = list(self.__class__.published.all())
            index = entries.index(self)
            try:
                previous = entries[index + 1]
            except IndexError:
                previous = None

            if index:
                next = entries[index - 1]
            else:
                next = None
            previous_next = (previous, next)
            setattr(self, 'previous_next', previous_next)
        return previous_next

    @property
    def short_url(self):
        """
        Returns the entry's short url.
        """
        return get_url_shortener()(self)

    @models.permalink
    def get_absolute_url(self):
        """
        Builds and returns the entry's URL based on
        the slug and the creation date.
        """
        creation_date = self.creation_date
        if timezone.is_aware(creation_date):
            creation_date = timezone.localtime(creation_date)
        return ('zinnia:entry_detail', (), {
            'year': creation_date.strftime('%Y'),
            'month': creation_date.strftime('%m'),
            'day': creation_date.strftime('%d'),
            'slug': self.slug})

    def __str__(self):
        return '%s: %s' % (self.title, self.get_status_display())

    class Meta:
        """
        CoreEntry's meta informations.
        """
        abstract = True
        app_label = 'zinnia'
        ordering = ['-creation_date']
        get_latest_by = 'creation_date'
        verbose_name = _('entry')
        verbose_name_plural = _('entries')
        index_together = [['slug', 'creation_date'],
                          ['status', 'creation_date',
                           'start_publication', 'end_publication']]
        permissions = (('can_view_all', 'Can view all entries'),
                       ('can_change_status', 'Can change status'),
                       ('can_change_author', 'Can change author(s)'), )


class ContentEntry(models.Model):
    """
    Abstract content model class providing field
    and methods to write content inside an entry.
    """
    content = models.TextField(_('content'), blank=True)

    @property
    def html_content(self):
        """
        Returns the "content" field formatted in HTML.
        """
        if '</p>' in self.content:
            return self.content
        elif MARKUP_LANGUAGE == 'markdown':
            return markdown(self.content)
        elif MARKUP_LANGUAGE == 'textile':
            return textile(self.content)
        elif MARKUP_LANGUAGE == 'restructuredtext':
            return restructuredtext(self.content)
        return linebreaks(self.content)

    @property
    def html_preview(self):
        """
        Returns a preview of the "content" field formmated in HTML.
        """
        return HTMLPreview(self.html_content)

    @property
    def word_count(self):
        """
        Counts the number of words used in the content.
        """
        return len(strip_tags(self.html_content).split())

    class Meta:
        abstract = True


class DiscussionsEntry(models.Model):
    """
    Abstract discussion model class providing
    the fields and methods to manage the discussions
    (comments, pingbacks, trackbacks).
    """
    comment_enabled = models.BooleanField(
        _('comments enabled'), default=True,
        help_text=_('Allows comments if checked.'))
    pingback_enabled = models.BooleanField(
        _('pingbacks enabled'), default=True,
        help_text=_('Allows pingbacks if checked.'))
    trackback_enabled = models.BooleanField(
        _('trackbacks enabled'), default=True,
        help_text=_('Allows trackbacks if checked.'))

    comment_count = models.IntegerField(
        _('comment count'), default=0)
    pingback_count = models.IntegerField(
        _('pingback count'), default=0)
    trackback_count = models.IntegerField(
        _('trackback count'), default=0)

    @property
    def discussions(self):
        """
        Returns a queryset of the published discussions.
        """
        return comments.get_model().objects.for_model(
            self).filter(is_public=True, is_removed=False)

    @property
    def comments(self):
        """
        Returns a queryset of the published comments.
        """
        return self.discussions.filter(Q(flags=None) | Q(
            flags__flag=CommentFlag.MODERATOR_APPROVAL))

    @property
    def pingbacks(self):
        """
        Returns a queryset of the published pingbacks.
        """
        return self.discussions.filter(flags__flag=PINGBACK)

    @property
    def trackbacks(self):
        """
        Return a queryset of the published trackbacks.
        """
        return self.discussions.filter(flags__flag=TRACKBACK)

    def discussion_is_still_open(self, discussion_type, auto_close_after):
        """
        Checks if a type of discussion is still open
        are a certain number of days.
        """
        discussion_enabled = getattr(self, discussion_type)
        if (discussion_enabled and isinstance(auto_close_after, int)
                and auto_close_after >= 0):
            return (timezone.now() - (
                self.start_publication or self.creation_date)).days < \
                auto_close_after
        return discussion_enabled

    @property
    def comments_are_open(self):
        """
        Checks if the comments are open with the
        AUTO_CLOSE_COMMENTS_AFTER setting.
        """
        return self.discussion_is_still_open(
            'comment_enabled', AUTO_CLOSE_COMMENTS_AFTER)

    @property
    def pingbacks_are_open(self):
        """
        Checks if the pingbacks are open with the
        AUTO_CLOSE_PINGBACKS_AFTER setting.
        """
        return self.discussion_is_still_open(
            'pingback_enabled', AUTO_CLOSE_PINGBACKS_AFTER)

    @property
    def trackbacks_are_open(self):
        """
        Checks if the trackbacks are open with the
        AUTO_CLOSE_TRACKBACKS_AFTER setting.
        """
        return self.discussion_is_still_open(
            'trackback_enabled', AUTO_CLOSE_TRACKBACKS_AFTER)

    class Meta:
        abstract = True


class RelatedEntry(models.Model):
    """
    Abstract model class for making manual relations
    between the differents entries.
    """
    related = models.ManyToManyField(
        'self',
        blank=True, null=True,
        verbose_name=_('related entries'))

    @property
    def related_published(self):
        """
        Returns only related entries published.
        """
        return entries_published(self.related)

    class Meta:
        abstract = True


class ExcerptEntry(models.Model):
    """
    Abstract model class to add an excerpt to the entries.
    """
    excerpt = models.TextField(
        _('excerpt'), blank=True,
        help_text=_('Used for search and SEO.'))

    class Meta:
        abstract = True


class ImageEntry(models.Model):
    """
    Abstract model class to add an image to the entries.
    """
    image = models.ImageField(
        _('image'), blank=True, upload_to=UPLOAD_TO,
        help_text=_('Used for illustration.'))

    class Meta:
        abstract = True


class FeaturedEntry(models.Model):
    """
    Abstract model class to mark entries as featured.
    """
    featured = models.BooleanField(
        _('featured'), default=False)

    class Meta:
        abstract = True


class AuthorsEntry(models.Model):
    """
    Abstract model class to add relationship
    between the entries and their authors.
    """
    authors = models.ManyToManyField(
        'zinnia.Author',
        related_name='entries',
        blank=True, null=False,
        verbose_name=_('authors'))

    class Meta:
        abstract = True


class CategoriesEntry(models.Model):
    """
    Abstract model class to categorize the entries.
    """
    categories = models.ManyToManyField(
        'zinnia.Category',
        related_name='entries',
        blank=True, null=True,
        verbose_name=_('categories'))

    class Meta:
        abstract = True


class TagsEntry(models.Model):
    """
    Abstract lodel class to add tags to the entries.
    """
    tags = TagField(_('tags'))

    @property
    def tags_list(self):
        """
        Return iterable list of tags.
        """
        return parse_tag_input(self.tags)

    class Meta:
        abstract = True


class LoginRequiredEntry(models.Model):
    """
    Abstract model class to restrcit the display
    of the entry on authenticated users.
    """
    login_required = models.BooleanField(
        _('login required'), default=False,
        help_text=_('Only authenticated users can view the entry.'))

    class Meta:
        abstract = True


class PasswordRequiredEntry(models.Model):
    """
    Abstract model class to restrict the display
    of the entry to users knowing the password.
    """
    password = models.CharField(
        _('password'), max_length=50, blank=True,
        help_text=_('Protects the entry with a password.'))

    class Meta:
        abstract = True


class ContentTemplateEntry(models.Model):
    """
    Abstract model class to display entry's content
    with a custom template.
    """
    content_template = models.CharField(
        _('content template'), max_length=250,
        default='zinnia/_entry_detail.html',
        choices=[('zinnia/_entry_detail.html', _('Default template'))] +
        ENTRY_CONTENT_TEMPLATES,
        help_text=_("Template used to display the entry's content."))

    class Meta:
        abstract = True


class DetailTemplateEntry(models.Model):
    """
    Abstract model class to display entries with a
    custom template if needed on the detail page.
    """
    detail_template = models.CharField(
        _('detail template'), max_length=250,
        default='entry_detail.html',
        choices=[('entry_detail.html', _('Default template'))] +
        ENTRY_DETAIL_TEMPLATES,
        help_text=_("Template used to display the entry's detail page."))

    class Meta:
        abstract = True


class AbstractEntry(
        CoreEntry,
        ContentEntry,
        DiscussionsEntry,
        RelatedEntry,
        ExcerptEntry,
        ImageEntry,
        FeaturedEntry,
        AuthorsEntry,
        CategoriesEntry,
        TagsEntry,
        LoginRequiredEntry,
        PasswordRequiredEntry,
        ContentTemplateEntry,
        DetailTemplateEntry):
    """
    Final abstract entry model class assembling
    all the abstract entry model classes into a single one.

    In this manner we can override some fields without
    reimplemting all the AbstractEntry.
    """

    class Meta(CoreEntry.Meta):
        abstract = True

########NEW FILE########
__FILENAME__ = moderator
"""Moderator of Zinnia comments"""
from django.conf import settings
from django.template import Context
from django.template import loader
from django.core.mail import send_mail
from django.core.mail import EmailMessage
from django.contrib.sites.models import Site
from django.utils.translation import activate
from django.utils.translation import get_language
from django.utils.translation import ugettext_lazy as _

from django_comments.moderation import CommentModerator

from zinnia.settings import PROTOCOL
from zinnia.settings import MAIL_COMMENT_REPLY
from zinnia.settings import MAIL_COMMENT_AUTHORS
from zinnia.settings import AUTO_MODERATE_COMMENTS
from zinnia.settings import AUTO_CLOSE_COMMENTS_AFTER
from zinnia.settings import MAIL_COMMENT_NOTIFICATION_RECIPIENTS
from zinnia.settings import SPAM_CHECKER_BACKENDS
from zinnia.spam_checker import check_is_spam


class EntryCommentModerator(CommentModerator):
    """
    Moderate the comments on entries.
    """
    email_reply = MAIL_COMMENT_REPLY
    email_authors = MAIL_COMMENT_AUTHORS
    enable_field = 'comment_enabled'
    auto_close_field = 'start_publication'
    close_after = AUTO_CLOSE_COMMENTS_AFTER
    spam_checker_backends = SPAM_CHECKER_BACKENDS
    auto_moderate_comments = AUTO_MODERATE_COMMENTS
    mail_comment_notification_recipients = MAIL_COMMENT_NOTIFICATION_RECIPIENTS

    def email(self, comment, content_object, request):
        """
        Send email notifications needed.
        """
        if comment.is_public:
            current_language = get_language()
            try:
                activate(settings.LANGUAGE_CODE)
                if self.mail_comment_notification_recipients:
                    self.do_email_notification(comment, content_object,
                                               request)
                if self.email_authors:
                    self.do_email_authors(comment, content_object,
                                          request)
                if self.email_reply:
                    self.do_email_reply(comment, content_object, request)
            finally:
                activate(current_language)

    def do_email_notification(self, comment, content_object, request):
        """
        Send email notification of a new comment to site staff.
        """
        site = Site.objects.get_current()
        template = loader.get_template(
            'comments/comment_notification_email.txt')
        context = Context({'comment': comment, 'site': site,
                           'protocol': PROTOCOL,
                           'content_object': content_object})
        subject = _('[%(site)s] New comment posted on "%(title)s"') % \
            {'site': site.name, 'title': content_object.title}
        message = template.render(context)
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL,
                  self.mail_comment_notification_recipients,
                  fail_silently=not settings.DEBUG)

    def do_email_authors(self, comment, content_object, request):
        """
        Send email notification of a new comment to the authors of the entry.
        """
        exclude_list = self.mail_comment_notification_recipients + ['']
        recipient_list = set(
            [author.email for author in content_object.authors.all()]) - \
            set(exclude_list)
        if recipient_list:
            site = Site.objects.get_current()
            template = loader.get_template(
                'comments/comment_authors_email.txt')
            context = Context({'comment': comment, 'site': site,
                               'protocol': PROTOCOL,
                               'content_object': content_object})
            subject = _('[%(site)s] New comment posted on "%(title)s"') % \
                {'site': site.name, 'title': content_object.title}
            message = template.render(context)
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL,
                      recipient_list, fail_silently=not settings.DEBUG)

    def do_email_reply(self, comment, content_object, request):
        """
        Send email notification of a new comment to the authors of
        the previous comments.
        """
        exclude_list = self.mail_comment_notification_recipients + \
            [author.email for author in content_object.authors.all()] + \
            [comment.email]
        recipient_list = set(
            [other_comment.email for other_comment in content_object.comments
             if other_comment.email]) - set(exclude_list)
        if recipient_list:
            site = Site.objects.get_current()
            template = loader.get_template('comments/comment_reply_email.txt')
            context = Context({'comment': comment, 'site': site,
                               'protocol': PROTOCOL,
                               'content_object': content_object})
            subject = _('[%(site)s] New comment posted on "%(title)s"') % \
                {'site': site.name, 'title': content_object.title}
            message = template.render(context)
            mail = EmailMessage(subject, message,
                                settings.DEFAULT_FROM_EMAIL,
                                bcc=recipient_list)
            mail.send(fail_silently=not settings.DEBUG)

    def moderate(self, comment, content_object, request):
        """
        Determine if a new comment should be marked as non-public
        and await approval.
        Return ``True`` to put the comment into the moderator queue,
        or ``False`` to allow it to be showed up immediately.
        """
        if self.auto_moderate_comments:
            return True

        if check_is_spam(comment, content_object, request,
                         self.spam_checker_backends):
            return True

        return False

########NEW FILE########
__FILENAME__ = ping
"""Pings utilities for Zinnia"""
import socket
import threading
from logging import getLogger
try:
    from urllib.request import urlopen
    from urllib.parse import urlsplit
    from xmlrpc.client import Error
    from xmlrpc.client import ServerProxy
except ImportError:  # Python 2
    from urllib2 import urlopen
    from urlparse import urlsplit
    from xmlrpclib import Error
    from xmlrpclib import ServerProxy

from bs4 import BeautifulSoup

from django.contrib.sites.models import Site
from django.core.urlresolvers import reverse

from zinnia.flags import PINGBACK
from zinnia.settings import PROTOCOL


class URLRessources(object):
    """
    Object defining the ressources of the Website.
    """

    def __init__(self):
        self.current_site = Site.objects.get_current()
        self.site_url = '%s://%s' % (PROTOCOL, self.current_site.domain)
        self.blog_url = '%s%s' % (self.site_url,
                                  reverse('zinnia:entry_archive_index'))
        self.blog_feed = '%s%s' % (self.site_url,
                                   reverse('zinnia:entry_latest_feed'))


class DirectoryPinger(threading.Thread):
    """
    Threaded web directory pinger.
    """

    def __init__(self, server_name, entries, timeout=10, start_now=True):
        self.results = []
        self.timeout = timeout
        self.entries = entries
        self.server_name = server_name
        self.server = ServerProxy(self.server_name)
        self.ressources = URLRessources()

        threading.Thread.__init__(self)
        if start_now:
            self.start()

    def run(self):
        """
        Ping entries to a directory in a thread.
        """
        logger = getLogger('zinnia.ping.directory')
        socket.setdefaulttimeout(self.timeout)
        for entry in self.entries:
            reply = self.ping_entry(entry)
            self.results.append(reply)
            logger.info('%s : %s' % (self.server_name, reply['message']))
        socket.setdefaulttimeout(None)

    def ping_entry(self, entry):
        """
        Ping an entry to a directory.
        """
        entry_url = '%s%s' % (self.ressources.site_url,
                              entry.get_absolute_url())
        categories = '|'.join([c.title for c in entry.categories.all()])

        try:
            reply = self.server.weblogUpdates.extendedPing(
                self.ressources.current_site.name,
                self.ressources.blog_url, entry_url,
                self.ressources.blog_feed, categories)
        except Exception:
            try:
                reply = self.server.weblogUpdates.ping(
                    self.ressources.current_site.name,
                    self.ressources.blog_url, entry_url,
                    categories)
            except Exception:
                reply = {'message': '%s is an invalid directory.' %
                         self.server_name,
                         'flerror': True}
        return reply


class ExternalUrlsPinger(threading.Thread):
    """
    Threaded external URLs pinger.
    """

    def __init__(self, entry, timeout=10, start_now=True):
        self.results = []
        self.entry = entry
        self.timeout = timeout
        self.ressources = URLRessources()
        self.entry_url = '%s%s' % (self.ressources.site_url,
                                   self.entry.get_absolute_url())

        threading.Thread.__init__(self)
        if start_now:
            self.start()

    def run(self):
        """
        Ping external URLs in a Thread.
        """
        logger = getLogger('zinnia.ping.external_urls')
        socket.setdefaulttimeout(self.timeout)

        external_urls = self.find_external_urls(self.entry)
        external_urls_pingable = self.find_pingback_urls(external_urls)

        for url, server_name in external_urls_pingable.items():
            reply = self.pingback_url(server_name, url)
            self.results.append(reply)
            logger.info('%s : %s' % (url, reply))

        socket.setdefaulttimeout(None)

    def is_external_url(self, url, site_url):
        """
        Check if the URL is an external URL.
        """
        url_splitted = urlsplit(url)
        if not url_splitted.netloc:
            return False
        return url_splitted.netloc != urlsplit(site_url).netloc

    def find_external_urls(self, entry):
        """
        Find external URLs in an entry.
        """
        soup = BeautifulSoup(entry.html_content)
        external_urls = [a['href'] for a in soup.find_all('a')
                         if self.is_external_url(
                             a['href'], self.ressources.site_url)]
        return external_urls

    def find_pingback_href(self, content):
        """
        Try to find LINK markups to pingback URL.
        """
        soup = BeautifulSoup(content)
        for link in soup.find_all('link'):
            dict_attr = dict(link.attrs)
            if 'rel' in dict_attr and 'href' in dict_attr:
                for rel_type in dict_attr['rel']:
                    if rel_type.lower() == PINGBACK:
                        return dict_attr.get('href')

    def find_pingback_urls(self, urls):
        """
        Find the pingback URL for each URLs.
        """
        pingback_urls = {}

        for url in urls:
            try:
                page = urlopen(url)
                headers = page.info()

                if 'text/' not in headers.get('Content-Type', '').lower():
                    continue

                server_url = headers.get('X-Pingback')
                if not server_url:
                    server_url = self.find_pingback_href(page.read())

                if server_url:
                    server_url_splitted = urlsplit(server_url)
                    if not server_url_splitted.netloc:
                        url_splitted = urlsplit(url)
                        server_url = '%s://%s%s' % (url_splitted.scheme,
                                                    url_splitted.netloc,
                                                    server_url)
                    pingback_urls[url] = server_url
            except IOError:
                pass
        return pingback_urls

    def pingback_url(self, server_name, target_url):
        """
        Do a pingback call for the target URL.
        """
        try:
            server = ServerProxy(server_name)
            reply = server.pingback.ping(self.entry_url, target_url)
        except (Error, socket.error):
            reply = '%s cannot be pinged.' % target_url
        return reply

########NEW FILE########
__FILENAME__ = preview
"""Preview for Zinnia"""
from __future__ import division

from django.utils import six
from django.utils.text import Truncator
from django.utils.html import strip_tags
from django.utils.functional import cached_property
from django.utils.encoding import python_2_unicode_compatible

from bs4 import BeautifulSoup

from zinnia.settings import PREVIEW_SPLITTERS
from zinnia.settings import PREVIEW_MAX_WORDS
from zinnia.settings import PREVIEW_MORE_STRING


@python_2_unicode_compatible
class HTMLPreview(object):
    """
    Build an HTML preview of an HTML content.
    """

    def __init__(self, content,
                 splitters=PREVIEW_SPLITTERS,
                 max_words=PREVIEW_MAX_WORDS,
                 more_string=PREVIEW_MORE_STRING):
        self._preview = None

        self.content = content
        self.splitters = splitters
        self.max_words = max_words
        self.more_string = more_string

    @property
    def preview(self):
        """
        The preview is a cached property.
        """
        if self._preview is None:
            self._preview = self.build_preview()
        return self._preview

    @property
    def has_more(self):
        """
        Boolean telling if the preview has hidden content.
        """
        return self.preview != self.content

    def __str__(self):
        """
        Method used to render the preview in templates.
        """
        return six.text_type(self.preview)

    def build_preview(self):
        """
        Build the preview by:
        - Checking if a split marker is present in the content
          Then split the content with the marker to build the preview.
        - Splitting the content to a fixed number of words.
        """
        for splitter in self.splitters:
            if splitter in self.content:
                return self.split(splitter)
        return self.truncate()

    def truncate(self):
        """
        Truncate the content with the Truncator object.
        """
        return Truncator(self.content).words(
            self.max_words, self.more_string, html=True)

    def split(self, splitter):
        """
        Split the HTML content with a marker
        without breaking closing markups.
        """
        soup = BeautifulSoup(self.content.split(splitter)[0],
                             'html.parser')
        last_string = soup.find_all(text=True)[-1]
        last_string.replace_with(last_string.string + self.more_string)
        return soup

    @cached_property
    def total_words(self):
        """
        Return the total of words contained in the content.
        """
        return len(strip_tags(self.content).split())

    @cached_property
    def displayed_words(self):
        """
        Return the number of words displayed in the preview.
        """
        return (len(strip_tags(self.preview).split()) -
                len(self.more_string.split()))

    @cached_property
    def remaining_words(self):
        """
        Return the number of words remaining after the preview.
        """
        return self.total_words - self.displayed_words

    @cached_property
    def displayed_percent(self):
        """
        Return the percentage of the content displayed in the preview.
        """
        return (self.displayed_words / self.total_words) * 100

    @cached_property
    def remaining_percent(self):
        """
        Return the percentage of the content remaining after the preview.
        """
        return (self.remaining_words / self.total_words) * 100

########NEW FILE########
__FILENAME__ = search
"""Search module with complex query parsing for Zinnia"""
from django.utils import six

from pyparsing import Word
from pyparsing import alphas
from pyparsing import WordEnd
from pyparsing import Combine
from pyparsing import opAssoc
from pyparsing import Optional
from pyparsing import OneOrMore
from pyparsing import StringEnd
from pyparsing import printables
from pyparsing import quotedString
from pyparsing import removeQuotes
from pyparsing import ParseResults
from pyparsing import CaselessLiteral
from pyparsing import operatorPrecedence

from django.db.models import Q

from zinnia.models.entry import Entry
from zinnia.models.author import Author
from zinnia.settings import STOP_WORDS


def createQ(token):
    """
    Creates the Q() object.
    """
    meta = getattr(token, 'meta', None)
    query = getattr(token, 'query', '')
    wildcards = None

    if isinstance(query, six.string_types):  # Unicode -> Quoted string
        search = query
    else:  # List -> No quoted string (possible wildcards)
        if len(query) == 1:
            search = query[0]
        elif len(query) == 3:
            wildcards = 'BOTH'
            search = query[1]
        elif len(query) == 2:
            if query[0] == '*':
                wildcards = 'START'
                search = query[1]
            else:
                wildcards = 'END'
                search = query[0]

    # Ignore connective words (of, a, an...) and STOP_WORDS
    if (len(search) < 3 and not search.isdigit()) or search in STOP_WORDS:
        return Q()

    if not meta:
        return Q(content__icontains=search) | \
            Q(excerpt__icontains=search) | \
            Q(title__icontains=search)

    if meta == 'category':
        if wildcards == 'BOTH':
            return Q(categories__title__icontains=search) | \
                Q(categories__slug__icontains=search)
        elif wildcards == 'START':
            return Q(categories__title__iendswith=search) | \
                Q(categories__slug__iendswith=search)
        elif wildcards == 'END':
            return Q(categories__title__istartswith=search) | \
                Q(categories__slug__istartswith=search)
        else:
            return Q(categories__title__iexact=search) | \
                Q(categories__slug__iexact=search)
    elif meta == 'author':
        if wildcards == 'BOTH':
            return Q(**{'authors__%s__icontains' % Author.USERNAME_FIELD:
                        search})
        elif wildcards == 'START':
            return Q(**{'authors__%s__iendswith' % Author.USERNAME_FIELD:
                        search})
        elif wildcards == 'END':
            return Q(**{'authors__%s__istartswith' % Author.USERNAME_FIELD:
                        search})
        else:
            return Q(**{'authors__%s__iexact' % Author.USERNAME_FIELD:
                        search})
    elif meta == 'tag':  # TODO: tags ignore wildcards
        return Q(tags__icontains=search)


def unionQ(token):
    """
    Appends all the Q() objects.
    """
    query = Q()
    operation = 'and'
    negation = False

    for t in token:
        if type(t) is ParseResults:  # See tokens recursively
            query &= unionQ(t)
        else:
            if t in ('or', 'and'):  # Set the new op and go to next token
                operation = t
            elif t == '-':  # Next tokens needs to be negated
                negation = True
            else:  # Append to query the token
                if negation:
                    t = ~t
                if operation == 'or':
                    query |= t
                else:
                    query &= t
    return query


NO_BRTS = printables.replace('(', '').replace(')', '')
SINGLE = Word(NO_BRTS.replace('*', ''))
WILDCARDS = Optional('*') + SINGLE + Optional('*') + WordEnd(wordChars=NO_BRTS)
QUOTED = quotedString.setParseAction(removeQuotes)

OPER_AND = CaselessLiteral('and')
OPER_OR = CaselessLiteral('or')
OPER_NOT = '-'

TERM = Combine(Optional(Word(alphas).setResultsName('meta') + ':') +
               (QUOTED.setResultsName('query') |
                WILDCARDS.setResultsName('query')))
TERM.setParseAction(createQ)

EXPRESSION = operatorPrecedence(TERM, [
    (OPER_NOT, 1, opAssoc.RIGHT),
    (OPER_OR, 2, opAssoc.LEFT),
    (Optional(OPER_AND, default='and'), 2, opAssoc.LEFT)])
EXPRESSION.setParseAction(unionQ)

QUERY = OneOrMore(EXPRESSION) + StringEnd()
QUERY.setParseAction(unionQ)


def advanced_search(pattern):
    """
    Parse the grammar of a pattern and build a queryset with it.
    """
    query_parsed = QUERY.parseString(pattern)
    return Entry.published.filter(query_parsed[0]).distinct()

########NEW FILE########
__FILENAME__ = settings
"""Settings of Zinnia"""
from django.conf import settings

PING_DIRECTORIES = getattr(settings, 'ZINNIA_PING_DIRECTORIES',
                           ('http://django-blog-zinnia.com/xmlrpc/',))
SAVE_PING_DIRECTORIES = getattr(settings, 'ZINNIA_SAVE_PING_DIRECTORIES',
                                bool(PING_DIRECTORIES))
SAVE_PING_EXTERNAL_URLS = getattr(settings, 'ZINNIA_PING_EXTERNAL_URLS', True)

TRANSLATED_URLS = getattr(settings, 'ZINNIA_TRANSLATED_URLS', False)

COPYRIGHT = getattr(settings, 'ZINNIA_COPYRIGHT', 'Zinnia')

PAGINATION = getattr(settings, 'ZINNIA_PAGINATION', 10)
ALLOW_EMPTY = getattr(settings, 'ZINNIA_ALLOW_EMPTY', True)
ALLOW_FUTURE = getattr(settings, 'ZINNIA_ALLOW_FUTURE', True)

ENTRY_BASE_MODEL = getattr(settings, 'ZINNIA_ENTRY_BASE_MODEL',
                           'zinnia.models_bases.entry.AbstractEntry')

ENTRY_DETAIL_TEMPLATES = getattr(
    settings, 'ZINNIA_ENTRY_DETAIL_TEMPLATES', [])
ENTRY_CONTENT_TEMPLATES = getattr(
    settings, 'ZINNIA_ENTRY_CONTENT_TEMPLATES', [])

MARKUP_LANGUAGE = getattr(settings, 'ZINNIA_MARKUP_LANGUAGE', 'html')

MARKDOWN_EXTENSIONS = getattr(settings, 'ZINNIA_MARKDOWN_EXTENSIONS', '')

RESTRUCTUREDTEXT_SETTINGS = getattr(
    settings, 'ZINNIA_RESTRUCTUREDTEXT_SETTINGS', {})

PREVIEW_SPLITTERS = getattr(settings, 'ZINNIA_PREVIEW_SPLITTERS',
                            ['<!-- more -->', '<!--more-->'])

PREVIEW_MAX_WORDS = getattr(settings, 'ZINNIA_PREVIEW_MAX_WORDS', 55)

PREVIEW_MORE_STRING = getattr(settings, 'ZINNIA_PREVIEW_MORE_STRING', ' ...')

WYSIWYG_MARKUP_MAPPING = {
    'textile': 'markitup',
    'markdown': 'markitup',
    'restructuredtext': 'markitup',
    'html': 'tinymce' in settings.INSTALLED_APPS and 'tinymce' or 'wymeditor'}

WYSIWYG = getattr(settings, 'ZINNIA_WYSIWYG',
                  WYSIWYG_MARKUP_MAPPING.get(MARKUP_LANGUAGE))

AUTO_CLOSE_PINGBACKS_AFTER = getattr(
    settings, 'ZINNIA_AUTO_CLOSE_PINGBACKS_AFTER', None)

AUTO_CLOSE_TRACKBACKS_AFTER = getattr(
    settings, 'ZINNIA_AUTO_CLOSE_TRACKBACKS_AFTER', None)

AUTO_CLOSE_COMMENTS_AFTER = getattr(
    settings, 'ZINNIA_AUTO_CLOSE_COMMENTS_AFTER', None)

AUTO_MODERATE_COMMENTS = getattr(settings, 'ZINNIA_AUTO_MODERATE_COMMENTS',
                                 False)

MAIL_COMMENT_REPLY = getattr(settings, 'ZINNIA_MAIL_COMMENT_REPLY', False)

MAIL_COMMENT_AUTHORS = getattr(settings, 'ZINNIA_MAIL_COMMENT_AUTHORS', True)

MAIL_COMMENT_NOTIFICATION_RECIPIENTS = getattr(
    settings, 'ZINNIA_MAIL_COMMENT_NOTIFICATION_RECIPIENTS',
    [manager_tuple[1] for manager_tuple in settings.MANAGERS])

COMMENT_MIN_WORDS = getattr(settings, 'ZINNIA_COMMENT_MIN_WORDS', 4)

COMMENT_FLAG_USER_ID = getattr(settings, 'ZINNIA_COMMENT_FLAG_USER_ID', 1)

UPLOAD_TO = getattr(settings, 'ZINNIA_UPLOAD_TO', 'uploads/zinnia')

PROTOCOL = getattr(settings, 'ZINNIA_PROTOCOL', 'http')

FEEDS_FORMAT = getattr(settings, 'ZINNIA_FEEDS_FORMAT', 'rss')
FEEDS_MAX_ITEMS = getattr(settings, 'ZINNIA_FEEDS_MAX_ITEMS', 15)

PINGBACK_CONTENT_LENGTH = getattr(settings,
                                  'ZINNIA_PINGBACK_CONTENT_LENGTH', 300)

F_MIN = getattr(settings, 'ZINNIA_F_MIN', 0.1)
F_MAX = getattr(settings, 'ZINNIA_F_MAX', 1.0)

SPAM_CHECKER_BACKENDS = getattr(settings, 'ZINNIA_SPAM_CHECKER_BACKENDS',
                                ())

URL_SHORTENER_BACKEND = getattr(settings, 'ZINNIA_URL_SHORTENER_BACKEND',
                                'zinnia.url_shortener.backends.default')

STOP_WORDS = getattr(settings, 'ZINNIA_STOP_WORDS',
                     ('able', 'about', 'across', 'after', 'all', 'almost',
                      'also', 'among', 'and', 'any', 'are', 'because', 'been',
                      'but', 'can', 'cannot', 'could', 'dear', 'did', 'does',
                      'either', 'else', 'ever', 'every', 'for', 'from', 'get',
                      'got', 'had', 'has', 'have', 'her', 'hers', 'him', 'his',
                      'how', 'however', 'into', 'its', 'just', 'least', 'let',
                      'like', 'likely', 'may', 'might', 'most', 'must',
                      'neither', 'nor', 'not', 'off', 'often', 'only', 'other',
                      'our', 'own', 'rather', 'said', 'say', 'says', 'she',
                      'should', 'since', 'some', 'than', 'that', 'the',
                      'their', 'them', 'then', 'there', 'these', 'they',
                      'this', 'tis', 'too', 'twas', 'wants', 'was', 'were',
                      'what', 'when', 'where', 'which', 'while', 'who', 'whom',
                      'why', 'will', 'with', 'would', 'yet', 'you', 'your'))

########NEW FILE########
__FILENAME__ = signals
"""Signal handlers of Zinnia"""
import inspect
from functools import wraps

from django.db.models import F
from django.dispatch import Signal
from django.db.models.signals import post_save
from django.db.models.signals import pre_delete

import django_comments as comments
from django_comments.signals import comment_was_posted
from django_comments.signals import comment_was_flagged

from zinnia import settings
from zinnia.models.entry import Entry

comment_model = comments.get_model()
ENTRY_PS_PING_DIRECTORIES = 'zinnia.entry.post_save.ping_directories'
ENTRY_PS_PING_EXTERNAL_URLS = 'zinnia.entry.post_save.ping_external_urls'
COMMENT_PS_COUNT_DISCUSSIONS = 'zinnia.comment.post_save.count_discussions'
COMMENT_PD_COUNT_DISCUSSIONS = 'zinnia.comment.pre_delete.count_discussions'
COMMENT_WF_COUNT_DISCUSSIONS = 'zinnia.comment.was_flagged.count_discussions'
COMMENT_WP_COUNT_COMMENTS = 'zinnia.comment.was_posted.count_comments'
PINGBACK_WP_COUNT_PINGBACKS = 'zinnia.pingback.was_flagged.count_pingbacks'
TRACKBACK_WP_COUNT_TRACKBACKS = 'zinnia.trackback.was_flagged.count_trackbacks'

pingback_was_posted = Signal(providing_args=['pingback', 'entry'])
trackback_was_posted = Signal(providing_args=['trackback', 'entry'])


def disable_for_loaddata(signal_handler):
    """
    Decorator for disabling signals sent by 'post_save'
    on loaddata command.
    http://code.djangoproject.com/ticket/8399
    """
    @wraps(signal_handler)
    def wrapper(*args, **kwargs):
        for fr in inspect.stack():
            if inspect.getmodulename(fr[1]) == 'loaddata':
                return  # pragma: no cover
        signal_handler(*args, **kwargs)

    return wrapper


@disable_for_loaddata
def ping_directories_handler(sender, **kwargs):
    """
    Ping directories when an entry is saved.
    """
    entry = kwargs['instance']

    if entry.is_visible and settings.SAVE_PING_DIRECTORIES:
        from zinnia.ping import DirectoryPinger

        for directory in settings.PING_DIRECTORIES:
            DirectoryPinger(directory, [entry])


@disable_for_loaddata
def ping_external_urls_handler(sender, **kwargs):
    """
    Ping externals URLS when an entry is saved.
    """
    entry = kwargs['instance']

    if entry.is_visible and settings.SAVE_PING_EXTERNAL_URLS:
        from zinnia.ping import ExternalUrlsPinger

        ExternalUrlsPinger(entry)


def count_discussions_handler(sender, **kwargs):
    """
    Update the count of each type of discussion on an entry.
    """
    if kwargs.get('instance') and kwargs.get('created'):
        # The signal is emitted by the comment creation,
        # so we do nothing, comment_was_posted is used instead.
        return

    comment = 'comment' in kwargs and kwargs['comment'] or kwargs['instance']
    entry = comment.content_object

    if isinstance(entry, Entry):
        entry.comment_count = entry.comments.count()
        entry.pingback_count = entry.pingbacks.count()
        entry.trackback_count = entry.trackbacks.count()
        entry.save(update_fields=[
            'comment_count', 'pingback_count', 'trackback_count'])


def count_comments_handler(sender, **kwargs):
    """
    Update Entry.comment_count when a public comment was posted.
    """
    comment = kwargs['comment']
    if comment.is_public:
        entry = comment.content_object
        if isinstance(entry, Entry):
            entry.comment_count = F('comment_count') + 1
            entry.save(update_fields=['comment_count'])


def count_pingbacks_handler(sender, **kwargs):
    """
    Update Entry.pingback_count when a pingback was posted.
    """
    entry = kwargs['entry']
    entry.pingback_count = F('pingback_count') + 1
    entry.save(update_fields=['pingback_count'])


def count_trackbacks_handler(sender, **kwargs):
    """
    Update Entry.trackback_count when a trackback was posted.
    """
    entry = kwargs['entry']
    entry.trackback_count = F('trackback_count') + 1
    entry.save(update_fields=['trackback_count'])


def connect_entry_signals():
    """
    Connect all the signals on Entry model.
    """
    post_save.connect(
        ping_directories_handler, sender=Entry,
        dispatch_uid=ENTRY_PS_PING_DIRECTORIES)
    post_save.connect(
        ping_external_urls_handler, sender=Entry,
        dispatch_uid=ENTRY_PS_PING_EXTERNAL_URLS)


def disconnect_entry_signals():
    """
    Disconnect all the signals on Entry model.
    """
    post_save.disconnect(
        sender=Entry,
        dispatch_uid=ENTRY_PS_PING_DIRECTORIES)
    post_save.disconnect(
        sender=Entry,
        dispatch_uid=ENTRY_PS_PING_EXTERNAL_URLS)


def connect_discussion_signals():
    """
    Connect all the signals on the Comment model to
    maintains a valid discussion count on each entries
    when an action is done with the comments.
    """
    post_save.connect(
        count_discussions_handler, sender=comment_model,
        dispatch_uid=COMMENT_PS_COUNT_DISCUSSIONS)
    pre_delete.connect(
        count_discussions_handler, sender=comment_model,
        dispatch_uid=COMMENT_PD_COUNT_DISCUSSIONS)
    comment_was_flagged.connect(
        count_discussions_handler, sender=comment_model,
        dispatch_uid=COMMENT_WF_COUNT_DISCUSSIONS)
    comment_was_posted.connect(
        count_comments_handler, sender=comment_model,
        dispatch_uid=COMMENT_WP_COUNT_COMMENTS)
    pingback_was_posted.connect(
        count_pingbacks_handler, sender=comment_model,
        dispatch_uid=PINGBACK_WP_COUNT_PINGBACKS)
    trackback_was_posted.connect(
        count_trackbacks_handler, sender=comment_model,
        dispatch_uid=TRACKBACK_WP_COUNT_TRACKBACKS)


def disconnect_discussion_signals():
    """
    Disconnect all the signals on Comment model
    provided by Zinnia.
    """
    post_save.disconnect(
        sender=comment_model,
        dispatch_uid=COMMENT_PS_COUNT_DISCUSSIONS)
    pre_delete.disconnect(
        sender=comment_model,
        dispatch_uid=COMMENT_PD_COUNT_DISCUSSIONS)
    comment_was_flagged.disconnect(
        sender=comment_model,
        dispatch_uid=COMMENT_WF_COUNT_DISCUSSIONS)
    comment_was_posted.disconnect(
        sender=comment_model,
        dispatch_uid=COMMENT_WP_COUNT_COMMENTS)
    pingback_was_posted.disconnect(
        sender=comment_model,
        dispatch_uid=PINGBACK_WP_COUNT_PINGBACKS)
    trackback_was_posted.disconnect(
        sender=comment_model,
        dispatch_uid=TRACKBACK_WP_COUNT_TRACKBACKS)

########NEW FILE########
__FILENAME__ = sitemaps
"""Sitemaps for Zinnia"""
from django.db.models import Max
from django.db.models import Count
from django.contrib.sitemaps import Sitemap
from django.core.urlresolvers import reverse

from tagging.models import Tag
from tagging.models import TaggedItem

from zinnia.models.entry import Entry
from zinnia.models.author import Author
from zinnia.models.category import Category
from zinnia.settings import PROTOCOL


class ZinniaSitemap(Sitemap):
    """
    Base Sitemap class for Zinnia.
    """
    protocol = PROTOCOL


class EntrySitemap(ZinniaSitemap):
    """
    Sitemap for entries.
    """
    priority = 0.5
    changefreq = 'weekly'

    def items(self):
        """
        Return published entries.
        """
        return Entry.published.all()

    def lastmod(self, obj):
        """
        Return last modification of an entry.
        """
        return obj.last_update


class EntryRelatedSitemap(ZinniaSitemap):
    """
    Sitemap for models related to Entries.
    """
    model = None
    changefreq = 'monthly'

    def items(self):
        """
        Get a queryset, cache infos for standardized access to them later
        then compute the maximum of entries to define the priority
        of each items.
        """
        queryset = self.get_queryset()
        self.cache_infos(queryset)
        self.set_max_entries()
        return queryset

    def get_queryset(self):
        """
        Build a queryset of items with published entries and annotated
        with the number of entries and the latest modification date.
        """
        return self.model.published.annotate(
            count_entries_published=Count('entries')).annotate(
            last_update=Max('entries__last_update')).order_by(
            '-count_entries_published', '-last_update', '-pk')

    def cache_infos(self, queryset):
        """
        Cache infos like the number of entries published and
        the last modification date for standardized access later.
        """
        self.cache = {}
        for item in queryset:
            self.cache[item.pk] = (item.count_entries_published,
                                   item.last_update)

    def set_max_entries(self):
        """
        Define the maximum of entries for computing the priority
        of each items later.
        """
        if self.cache:
            self.max_entries = float(max([i[0] for i in self.cache.values()]))

    def lastmod(self, item):
        """
        The last modification date is defined
        by the latest entries last update in the cache.
        """
        return self.cache[item.pk][1]

    def priority(self, item):
        """
        The priority of the item depends of the number of entries published
        in the cache divided by the maximum of entries.
        """
        return '%.1f' % max(self.cache[item.pk][0] / self.max_entries, 0.1)


class CategorySitemap(EntryRelatedSitemap):
    """
    Sitemap for categories.
    """
    model = Category


class AuthorSitemap(EntryRelatedSitemap):
    """
    Sitemap for authors.
    """
    model = Author


class TagSitemap(EntryRelatedSitemap):
    """
    Sitemap for tags.
    """

    def get_queryset(self):
        """
        Return the published Tags with option counts.
        """
        self.entries_qs = Entry.published.all()
        return Tag.objects.usage_for_queryset(
            self.entries_qs, counts=True)

    def cache_infos(self, queryset):
        """
        Cache the number of entries published and the last
        modification date under each tag.
        """
        self.cache = {}
        for item in queryset:
            # If the sitemap is too slow, don't hesitate to do this :
            #   self.cache[item.pk] = (item.count, None)
            self.cache[item.pk] = (
                item.count, TaggedItem.objects.get_by_model(
                    self.entries_qs, item)[0].last_update)

    def location(self, item):
        """
        Return URL of the tag.
        """
        return reverse('zinnia:tag_detail', args=[item.name])

########NEW FILE########
__FILENAME__ = all_is_spam
"""All is spam, spam checker backend for Zinnia"""


def backend(comment, content_object, request):
    """
    Backend for setting all comments to spam.
    """
    return True

########NEW FILE########
__FILENAME__ = long_enough
"""Long enough spam checker backend for Zinnia"""
from zinnia.settings import COMMENT_MIN_WORDS


def backend(comment, content_object, request):
    """
    Backend checking if the comment posted is long enough to be public.
    Generally a comments with few words is useless.
    The will avoid comments like this:

    - First !
    - I don't like.
    - Check http://spam-ads.com/
    """
    return len(comment.comment.split()) < COMMENT_MIN_WORDS

########NEW FILE########
__FILENAME__ = zinnia_tags
"""Template tags and filters for Zinnia"""
import re
from hashlib import md5
from datetime import date
try:
    from urllib.parse import urlencode
except ImportError:  # Python 2
    from urllib import urlencode

from django.db.models import Q
from django.db.models import Count
from django.conf import settings
from django.utils import timezone
from django.template import Library
from django.utils.encoding import smart_text
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _
from django.utils.html import conditional_escape
from django.template.defaultfilters import stringfilter
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType

from django_comments.models import CommentFlag
from django_comments import get_model as get_comment_model

from tagging.models import Tag
from tagging.utils import calculate_cloud

from zinnia.models.entry import Entry
from zinnia.models.author import Author
from zinnia.models.category import Category
from zinnia.managers import DRAFT
from zinnia.managers import tags_published
from zinnia.flags import PINGBACK, TRACKBACK
from zinnia.settings import PROTOCOL
from zinnia.comparison import VectorBuilder
from zinnia.comparison import pearson_score
from zinnia.calendar import Calendar
from zinnia.breadcrumbs import retrieve_breadcrumbs

register = Library()

VECTORS = None
VECTORS_FACTORY = lambda: VectorBuilder(Entry.published.all(),
                                        ['title', 'excerpt', 'content'])
CACHE_ENTRIES_RELATED = {}

WIDONT_REGEXP = re.compile(
    r'\s+(\S+\s*)$')
DOUBLE_SPACE_PUNCTUATION_WIDONT_REGEXP = re.compile(
    r'\s+([-+*/%=;:!?]+&nbsp;\S+\s*)$')
END_PUNCTUATION_WIDONT_REGEXP = re.compile(
    r'\s+([?!]+\s*)$')


@register.inclusion_tag('zinnia/tags/dummy.html', takes_context=True)
def get_categories(context, template='zinnia/tags/categories.html'):
    """
    Return the published categories.
    """
    return {'template': template,
            'categories': Category.published.all().annotate(
                count_entries_published=Count('entries')),
            'context_category': context.get('category')}


@register.inclusion_tag('zinnia/tags/dummy.html', takes_context=True)
def get_categories_tree(context, template='zinnia/tags/categories_tree.html'):
    """
    Return the categories as a tree.
    """
    return {'template': template,
            'categories': Category.objects.all(),
            'context_category': context.get('category')}


@register.inclusion_tag('zinnia/tags/dummy.html', takes_context=True)
def get_authors(context, template='zinnia/tags/authors.html'):
    """
    Return the published authors.
    """
    return {'template': template,
            'authors': Author.published.all().annotate(
                count_entries_published=Count('entries')),
            'context_author': context.get('author')}


@register.inclusion_tag('zinnia/tags/dummy.html')
def get_recent_entries(number=5, template='zinnia/tags/entries_recent.html'):
    """
    Return the most recent entries.
    """
    return {'template': template,
            'entries': Entry.published.all()[:number]}


@register.inclusion_tag('zinnia/tags/dummy.html')
def get_featured_entries(number=5,
                         template='zinnia/tags/entries_featured.html'):
    """
    Return the featured entries.
    """
    return {'template': template,
            'entries': Entry.published.filter(featured=True)[:number]}


@register.inclusion_tag('zinnia/tags/dummy.html')
def get_draft_entries(number=5,
                      template='zinnia/tags/entries_draft.html'):
    """
    Return the latest draft entries.
    """
    return {'template': template,
            'entries': Entry.objects.filter(status=DRAFT)[:number]}


@register.inclusion_tag('zinnia/tags/dummy.html')
def get_random_entries(number=5, template='zinnia/tags/entries_random.html'):
    """
    Return random entries.
    """
    return {'template': template,
            'entries': Entry.published.order_by('?')[:number]}


@register.inclusion_tag('zinnia/tags/dummy.html')
def get_popular_entries(number=5, template='zinnia/tags/entries_popular.html'):
    """
    Return popular entries.
    """
    return {'template': template,
            'entries': Entry.published.filter(
                comment_count__gt=0).order_by(
                '-comment_count', '-creation_date')[:number]}


@register.inclusion_tag('zinnia/tags/dummy.html', takes_context=True)
def get_similar_entries(context, number=5,
                        template='zinnia/tags/entries_similar.html',
                        flush=False):
    """
    Return similar entries.
    """
    global VECTORS
    global CACHE_ENTRIES_RELATED

    if VECTORS is None or flush:
        VECTORS = VECTORS_FACTORY()
        CACHE_ENTRIES_RELATED = {}

    def compute_related(object_id, dataset):
        """
        Compute related entries to an entry with a dataset.
        """
        object_vector = None
        for entry, e_vector in dataset.items():
            if entry.pk == object_id:
                object_vector = e_vector

        if not object_vector:
            return []

        entry_related = {}
        for entry, e_vector in dataset.items():
            if entry.pk != object_id:
                score = pearson_score(object_vector, e_vector)
                if score:
                    entry_related[entry] = score

        related = sorted(entry_related.items(),
                         key=lambda k_v: (k_v[1], k_v[0]))
        return [rel[0] for rel in related]

    object_id = context['object'].pk
    columns, dataset = VECTORS()
    key = '%s-%s' % (object_id, VECTORS.key)
    if key not in CACHE_ENTRIES_RELATED.keys():
        CACHE_ENTRIES_RELATED[key] = compute_related(object_id, dataset)

    entries = CACHE_ENTRIES_RELATED[key][:number]
    return {'template': template,
            'entries': entries}


@register.inclusion_tag('zinnia/tags/dummy.html')
def get_archives_entries(template='zinnia/tags/entries_archives.html'):
    """
    Return archives entries.
    """
    return {'template': template,
            'archives': Entry.published.datetimes(
                'creation_date', 'month', order='DESC')}


@register.inclusion_tag('zinnia/tags/dummy.html')
def get_archives_entries_tree(
        template='zinnia/tags/entries_archives_tree.html'):
    """
    Return archives entries as a tree.
    """
    return {'template': template,
            'archives': Entry.published.datetimes(
                'creation_date', 'day', order='ASC')}


@register.inclusion_tag('zinnia/tags/dummy.html', takes_context=True)
def get_calendar_entries(context, year=None, month=None,
                         template='zinnia/tags/entries_calendar.html'):
    """
    Return an HTML calendar of entries.
    """
    if not (year and month):
        month_day = context.get('month') or context.get('day')
        creation_date = getattr(context.get('object'), 'creation_date', None)
        if month_day:
            current_month = month_day
        elif creation_date:
            if settings.USE_TZ:
                creation_date = timezone.localtime(creation_date)
            current_month = creation_date.date().replace(day=1)
        else:
            today = timezone.now()
            if settings.USE_TZ:
                today = timezone.localtime(today)
            current_month = today.date().replace(day=1)
    else:
        current_month = date(year, month, 1)

    dates = list(map(
        lambda x: settings.USE_TZ and timezone.localtime(x).date() or x.date(),
        Entry.published.datetimes('creation_date', 'month')))

    if current_month not in dates:
        dates.append(current_month)
        dates.sort()
    index = dates.index(current_month)

    previous_month = index > 0 and dates[index - 1] or None
    next_month = index != len(dates) - 1 and dates[index + 1] or None
    calendar = Calendar()

    return {'template': template,
            'next_month': next_month,
            'previous_month': previous_month,
            'calendar': calendar.formatmonth(
                current_month.year,
                current_month.month,
                previous_month=previous_month,
                next_month=next_month)}


@register.inclusion_tag('zinnia/tags/dummy.html')
def get_recent_comments(number=5, template='zinnia/tags/comments_recent.html'):
    """
    Return the most recent comments.
    """
    # Using map(smart_text... fix bug related to issue #8554
    entry_published_pks = map(smart_text,
                              Entry.published.values_list('id', flat=True))
    content_type = ContentType.objects.get_for_model(Entry)

    comments = get_comment_model().objects.filter(
        Q(flags=None) | Q(flags__flag=CommentFlag.MODERATOR_APPROVAL),
        content_type=content_type, object_pk__in=entry_published_pks,
        is_public=True).order_by('-pk')[:number]

    comments = comments.prefetch_related('content_object')

    return {'template': template,
            'comments': comments}


@register.inclusion_tag('zinnia/tags/dummy.html')
def get_recent_linkbacks(number=5,
                         template='zinnia/tags/linkbacks_recent.html'):
    """
    Return the most recent linkbacks.
    """
    entry_published_pks = map(smart_text,
                              Entry.published.values_list('id', flat=True))
    content_type = ContentType.objects.get_for_model(Entry)

    linkbacks = get_comment_model().objects.filter(
        content_type=content_type,
        object_pk__in=entry_published_pks,
        flags__flag__in=[PINGBACK, TRACKBACK],
        is_public=True).order_by('-pk')[:number]

    linkbacks = linkbacks.prefetch_related('content_object')

    return {'template': template,
            'linkbacks': linkbacks}


@register.inclusion_tag('zinnia/tags/dummy.html', takes_context=True)
def zinnia_pagination(context, page, begin_pages=1, end_pages=1,
                      before_pages=2, after_pages=2,
                      template='zinnia/tags/pagination.html'):
    """
    Return a Digg-like pagination,
    by splitting long list of page into 3 blocks of pages.
    """
    GET_string = ''
    for key, value in context['request'].GET.items():
        if key != 'page':
            GET_string += '&%s=%s' % (key, value)

    begin = list(page.paginator.page_range[:begin_pages])
    end = list(page.paginator.page_range[-end_pages:])
    middle = list(page.paginator.page_range[
        max(page.number - before_pages - 1, 0):page.number + after_pages])

    if set(begin) & set(middle):  # [1, 2, 3], [2, 3, 4], [...]
        begin = sorted(set(begin + middle))  # [1, 2, 3, 4]
        middle = []
    elif begin[-1] + 1 == middle[0]:  # [1, 2, 3], [4, 5, 6], [...]
        begin += middle  # [1, 2, 3, 4, 5, 6]
        middle = []
    elif middle[-1] + 1 == end[0]:  # [...], [15, 16, 17], [18, 19, 20]
        end = middle + end  # [15, 16, 17, 18, 19, 20]
        middle = []
    elif set(middle) & set(end):  # [...], [17, 18, 19], [18, 19, 20]
        end = sorted(set(middle + end))  # [17, 18, 19, 20]
        middle = []

    if set(begin) & set(end):  # [1, 2, 3], [...], [2, 3, 4]
        begin = sorted(set(begin + end))  # [1, 2, 3, 4]
        middle, end = [], []
    elif begin[-1] + 1 == end[0]:  # [1, 2, 3], [...], [4, 5, 6]
        begin += end  # [1, 2, 3, 4, 5, 6]
        middle, end = [], []

    return {'template': template,
            'page': page,
            'begin': begin,
            'middle': middle,
            'end': end,
            'GET_string': GET_string}


@register.inclusion_tag('zinnia/tags/dummy.html', takes_context=True)
def zinnia_breadcrumbs(context, root_name=_('Blog'),
                       template='zinnia/tags/breadcrumbs.html',):
    """
    Return a breadcrumb for the application.
    """
    path = context['request'].path
    context_object = context.get('object') or context.get('category') or \
        context.get('tag') or context.get('author')
    context_page = context.get('page_obj')
    breadcrumbs = retrieve_breadcrumbs(path, context_object,
                                       context_page, root_name)

    return {'template': template,
            'breadcrumbs': breadcrumbs}


@register.simple_tag
def get_gravatar(email, size=80, rating='g', default=None,
                 protocol=PROTOCOL):
    """
    Return url for a Gravatar.
    """
    GRAVATAR_PROTOCOLS = {'http': 'http://www',
                          'https': 'https://secure'}
    url = '%s.gravatar.com/avatar/%s' % (
        GRAVATAR_PROTOCOLS[protocol],
        md5(email.strip().lower().encode('utf-8')).hexdigest())
    options = {'s': size, 'r': rating}
    if default:
        options['d'] = default

    url = '%s?%s' % (url, urlencode(options))
    return url.replace('&', '&amp;')


@register.assignment_tag
def get_tags():
    """
    Return the published tags.
    """
    return Tag.objects.usage_for_queryset(
        Entry.published.all())


@register.inclusion_tag('zinnia/tags/dummy.html', takes_context=True)
def get_tag_cloud(context, steps=6, min_count=None,
                  template='zinnia/tags/tag_cloud.html'):
    """
    Return a cloud of published tags.
    """
    tags = Tag.objects.usage_for_queryset(
        Entry.published.all(), counts=True,
        min_count=min_count)
    return {'template': template,
            'tags': calculate_cloud(tags, steps),
            'context_tag': context.get('tag')}


@register.filter(needs_autoescape=True)
@stringfilter
def widont(value, autoescape=None):
    """
    Add an HTML non-breaking space between the final
    two words of the string to avoid "widowed" words.
    """
    esc = autoescape and conditional_escape or (lambda x: x)

    def replace(matchobj):
        return '&nbsp;%s' % matchobj.group(1)

    value = END_PUNCTUATION_WIDONT_REGEXP.sub(replace, esc(smart_text(value)))
    value = WIDONT_REGEXP.sub(replace, value)
    value = DOUBLE_SPACE_PUNCTUATION_WIDONT_REGEXP.sub(replace, value)

    return mark_safe(value)


@register.filter
def week_number(date):
    """
    Return the Python week number of a date.
    The django \|date:"W" returns incompatible value
    with the view implementation.
    """
    week_number = date.strftime('%W')
    if int(week_number) < 10:
        week_number = week_number[-1]
    return week_number


@register.filter
def comment_admin_urlname(action):
    """
    Return the admin URLs for the comment app used.
    """
    comment = get_comment_model()
    return 'admin:%s_%s_%s' % (
        comment._meta.app_label, comment._meta.model_name,
        action)


@register.filter
def user_admin_urlname(action):
    """
    Return the admin URLs for the user app used.
    """
    user = get_user_model()
    return 'admin:%s_%s_%s' % (
        user._meta.app_label, user._meta.model_name,
        action)


@register.inclusion_tag('zinnia/tags/dummy.html')
def zinnia_statistics(template='zinnia/tags/statistics.html'):
    """
    Return statistics on the content of Zinnia.
    """
    content_type = ContentType.objects.get_for_model(Entry)
    discussions = get_comment_model().objects.filter(
        content_type=content_type)

    entries = Entry.published
    categories = Category.objects
    tags = tags_published()
    authors = Author.published
    replies = discussions.filter(
        flags=None, is_public=True)
    pingbacks = discussions.filter(
        flags__flag=PINGBACK, is_public=True)
    trackbacks = discussions.filter(
        flags__flag=TRACKBACK, is_public=True)
    rejects = discussions.filter(is_public=False)

    entries_count = entries.count()
    replies_count = replies.count()
    pingbacks_count = pingbacks.count()
    trackbacks_count = trackbacks.count()

    if entries_count:
        first_entry = entries.order_by('creation_date')[0]
        last_entry = entries.latest()
        months_count = (last_entry.creation_date -
                        first_entry.creation_date).days / 31.0
        entries_per_month = entries_count / (months_count or 1.0)

        comments_per_entry = float(replies_count) / entries_count
        linkbacks_per_entry = float(pingbacks_count + trackbacks_count) / \
            entries_count

        total_words_entry = 0
        for e in entries.all():
            total_words_entry += e.word_count
        words_per_entry = float(total_words_entry) / entries_count

        words_per_comment = 0.0
        if replies_count:
            total_words_comment = 0
            for c in replies.all():
                total_words_comment += len(c.comment.split())
            words_per_comment = float(total_words_comment) / replies_count
    else:
        words_per_entry = words_per_comment = entries_per_month = \
            comments_per_entry = linkbacks_per_entry = 0.0

    return {'template': template,
            'entries': entries_count,
            'categories': categories.count(),
            'tags': tags.count(),
            'authors': authors.count(),
            'comments': replies_count,
            'pingbacks': pingbacks_count,
            'trackbacks': trackbacks_count,
            'rejects': rejects.count(),
            'words_per_entry': words_per_entry,
            'words_per_comment': words_per_comment,
            'entries_per_month': entries_per_month,
            'comments_per_entry': comments_per_entry,
            'linkbacks_per_entry': linkbacks_per_entry}

########NEW FILE########
__FILENAME__ = custom_spam_checker
"""Custom spam checker backend for testing Zinnia"""
from django.core.exceptions import ImproperlyConfigured

raise ImproperlyConfigured('This backend only exists for testing')


def backend(entry):
    """Custom spam checker backend for testing Zinnia"""
    return False

########NEW FILE########
__FILENAME__ = custom_url_shortener
"""Custom url shortener backend for testing Zinnia"""
from django.core.exceptions import ImproperlyConfigured

raise ImproperlyConfigured('This backend only exists for testing')


def backend(entry):
    """Custom url shortener backend for testing Zinnia"""
    return ''

########NEW FILE########
__FILENAME__ = mysql
"""Settings for testing zinnia on MySQL"""
from zinnia.tests.implementations.settings import *  # noqa

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'zinnia',
        'USER': 'root',
        'HOST': 'localhost'
    }
}

########NEW FILE########
__FILENAME__ = postgres
"""Settings for testing zinnia on Postgres"""
from zinnia.tests.implementations.settings import *  # noqa

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'zinnia',
        'USER': 'postgres',
        'HOST': 'localhost'
    }
}

########NEW FILE########
__FILENAME__ = settings
"""Settings for testing zinnia"""
import os
from zinnia.xmlrpc import ZINNIA_XMLRPC_METHODS

SITE_ID = 1

USE_TZ = True

STATIC_URL = '/static/'

SECRET_KEY = 'secret-key'

ROOT_URLCONF = 'zinnia.tests.implementions.urls.default'

LOCALE_PATHS = [os.path.join(os.path.dirname(__file__), 'locale')]

PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.SHA1PasswordHasher'
]

MIDDLEWARE_CLASSES = [
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
]

TEMPLATE_CONTEXT_PROCESSORS = [
    'django.core.context_processors.request',
    'zinnia.context_processors.version'
]

TEMPLATE_LOADERS = [
    ['django.template.loaders.cached.Loader', [
        'django.template.loaders.filesystem.Loader',
        'django.template.loaders.app_directories.Loader']
     ]
]

INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.staticfiles',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.admin',
    'django.contrib.auth',
    'django_comments',
    'django_xmlrpc',
    'mptt',
    'tagging',
    'south',
    'zinnia'
]

ZINNIA_PAGINATION = 3

XMLRPC_METHODS = ZINNIA_XMLRPC_METHODS

########NEW FILE########
__FILENAME__ = sqlite
"""Settings for testing zinnia on SQLite"""
from zinnia.tests.implementations.settings import *  # noqa

DATABASES = {
    'default': {
        'NAME': 'zinnia.db',
        'ENGINE': 'django.db.backends.sqlite3'
    }
}

########NEW FILE########
__FILENAME__ = custom_detail_views
"""Test urls for the zinnia project"""
from django.conf.urls import url
from django.conf.urls import patterns

from zinnia.views.tags import TagDetail
from zinnia.views.authors import AuthorDetail
from zinnia.views.categories import CategoryDetail
from zinnia.tests.implementations.urls.default import (
    urlpatterns as test_urlpatterns)


class CustomModelDetailMixin(object):
    """Mixin for changing the template_name
    and overriding the context"""
    template_name = 'zinnia/entry_custom_list.html'

    def get_context_data(self, **kwargs):
        context = super(CustomModelDetailMixin,
                        self).get_context_data(**kwargs)
        context.update({'extra': 'context'})
        return context


class CustomTagDetail(CustomModelDetailMixin, TagDetail):
    pass


class CustomAuthorDetail(CustomModelDetailMixin, AuthorDetail):
    pass


class CustomCategoryDetail(CustomModelDetailMixin, CategoryDetail):
    pass


urlpatterns = patterns(
    '',
    url(r'^authors/(?P<username>[.+-@\w]+)/$',
        CustomAuthorDetail.as_view(),
        name='zinnia_author_detail'),
    url(r'^authors/(?P<username>[.+-@\w]+)/page/(?P<page>\d+)/$',
        CustomAuthorDetail.as_view(),
        name='zinnia_author_detail_paginated'),
    url(r'^categories/(?P<path>[-\/\w]+)/page/(?P<page>\d+)/$',
        CustomCategoryDetail.as_view(),
        name='zinnia_category_detail_paginated'),
    url(r'^categories/(?P<path>[-\/\w]+)/$',
        CustomCategoryDetail.as_view(),
        name='zinnia_category_detail'),
    url(r'^tags/(?P<tag>[^/]+(?u))/$',
        CustomTagDetail.as_view(),
        name='zinnia_tag_detail'),
    url(r'^tags/(?P<tag>[^/]+(?u))/page/(?P<page>\d+)/$',
        CustomTagDetail.as_view(),
        name='zinnia_tag_detail_paginated'),
) + test_urlpatterns

########NEW FILE########
__FILENAME__ = default
"""Test urls for the zinnia project"""
from django.contrib import admin
from django.conf.urls import url
from django.conf.urls import include
from django.conf.urls import patterns

from zinnia.views.channels import EntryChannel

admin.autodiscover()

handler500 = 'django.views.defaults.server_error'
handler404 = 'django.views.defaults.page_not_found'

urlpatterns = patterns(
    '',
    url(r'^', include('zinnia.urls', namespace='zinnia')),
    url(r'^channel-test/$', EntryChannel.as_view(query='test')),
    url(r'^comments/', include('django_comments.urls')),
    url(r'^xmlrpc/$', 'django_xmlrpc.views.handle_xmlrpc'),
    url(r'^admin/', include(admin.site.urls)),
)

########NEW FILE########
__FILENAME__ = poor
"""Poor test urls for the zinnia project"""
from django.contrib import admin
from django.conf.urls import url
from django.conf.urls import include
from django.conf.urls import patterns

admin.autodiscover()

urlpatterns = patterns(
    '',
    url(r'^', include('zinnia.urls.entries', namespace='zinnia')),
    url(r'^admin/', include(admin.site.urls)),
)

########NEW FILE########
__FILENAME__ = test_admin
"""Test cases for Zinnia's admin"""
from django.test import TestCase
from django.test import RequestFactory
from django.utils import timezone
from django.contrib.sites.models import Site
from django.utils.translation import activate
from django.utils.translation import deactivate
from django.contrib.admin.sites import AdminSite
from django.test.utils import restore_template_loaders
from django.test.utils import setup_test_template_loader
from django.contrib.auth.tests.utils import skipIfCustomUser

from zinnia import settings
from zinnia.managers import PUBLISHED
from zinnia.models.entry import Entry
from zinnia.models.author import Author
from zinnia.models.category import Category
from zinnia.tests.utils import datetime
from zinnia.admin.entry import EntryAdmin
from zinnia.admin.category import CategoryAdmin
from zinnia.signals import disconnect_entry_signals
from zinnia.url_shortener.backends.default import base36


class BaseAdminTestCase(TestCase):
    rich_urls = 'zinnia.tests.implementations.urls.default'
    poor_urls = 'zinnia.tests.implementations.urls.poor'
    urls = rich_urls
    model_class = None
    admin_class = None

    def setUp(self):
        disconnect_entry_signals()
        activate('en')
        self.site = AdminSite()
        self.admin = self.admin_class(
            self.model_class, self.site)

    def tearDown(self):
        """
        Be sure to restore the good urls to use
        if a test fail before restoring the urls.
        """
        self.urls = self.rich_urls
        self._urlconf_setup()
        deactivate()
        try:
            restore_template_loaders()
        except AttributeError:
            pass

    def check_with_rich_and_poor_urls(self, func, args,
                                      result_rich, result_poor):
        self.assertEqual(func(*args), result_rich)
        self.urls = self.poor_urls
        self._urlconf_setup()
        self.assertEqual(func(*args), result_poor)
        self.urls = self.rich_urls
        self._urlconf_setup()


class TestMessageBackend(object):
    """Message backend for testing"""
    def __init__(self, *ka, **kw):
        self.messages = []

    def add(self, *ka, **kw):
        self.messages.append((ka, kw))


@skipIfCustomUser
class EntryAdminTestCase(BaseAdminTestCase):
    """Test case for Entry Admin"""
    model_class = Entry
    admin_class = EntryAdmin

    def setUp(self):
        super(EntryAdminTestCase, self).setUp()
        params = {'title': 'My title',
                  'content': 'My content',
                  'slug': 'my-title'}
        self.entry = Entry.objects.create(**params)
        self.request_factory = RequestFactory()
        self.request = self.request_factory.get('/')

    def test_get_title(self):
        self.assertEqual(self.admin.get_title(self.entry),
                         'My title (2 words)')
        self.entry.comment_count = 1
        self.entry.save()
        self.entry = Entry.objects.get(pk=self.entry.pk)
        self.assertEqual(self.admin.get_title(self.entry),
                         'My title (2 words) (1 reaction)')
        self.entry.pingback_count = 1
        self.entry.save()
        self.entry = Entry.objects.get(pk=self.entry.pk)
        self.assertEqual(self.admin.get_title(self.entry),
                         'My title (2 words) (2 reactions)')

    def test_get_authors(self):
        self.check_with_rich_and_poor_urls(
            self.admin.get_authors, (self.entry,),
            '', '')
        author_1 = Author.objects.create_user(
            'author-1', 'author1@example.com')
        author_2 = Author.objects.create_user(
            'author-2', 'author2@example.com')
        self.entry.authors.add(author_1)
        self.check_with_rich_and_poor_urls(
            self.admin.get_authors, (self.entry,),
            '<a href="/authors/author-1/" target="blank">author-1</a>',
            'author-1')
        self.entry.authors.add(author_2)
        self.check_with_rich_and_poor_urls(
            self.admin.get_authors, (self.entry,),
            '<a href="/authors/author-1/" target="blank">author-1</a>, '
            '<a href="/authors/author-2/" target="blank">author-2</a>',
            'author-1, author-2',)

    def test_get_catgories(self):
        self.check_with_rich_and_poor_urls(
            self.admin.get_categories, (self.entry,),
            '', '')
        category_1 = Category.objects.create(title='Category 1',
                                             slug='category-1')
        category_2 = Category.objects.create(title='Category 2',
                                             slug='category-2')
        self.entry.categories.add(category_1)
        self.check_with_rich_and_poor_urls(
            self.admin.get_categories, (self.entry,),
            '<a href="/categories/category-1/" target="blank">Category 1</a>',
            'Category 1')
        self.entry.categories.add(category_2)
        self.check_with_rich_and_poor_urls(
            self.admin.get_categories, (self.entry,),
            '<a href="/categories/category-1/" target="blank">Category 1</a>, '
            '<a href="/categories/category-2/" target="blank">Category 2</a>',
            'Category 1, Category 2')

    def test_get_tags(self):
        self.check_with_rich_and_poor_urls(
            self.admin.get_tags, (self.entry,),
            '', '')
        self.entry.tags = 'zinnia'
        self.check_with_rich_and_poor_urls(
            self.admin.get_tags, (self.entry,),
            '<a href="/tags/zinnia/" target="blank">zinnia</a>',
            'zinnia')
        self.entry.tags = 'zinnia, test'
        self.check_with_rich_and_poor_urls(
            self.admin.get_tags, (self.entry,),
            '<a href="/tags/test/" target="blank">test</a>, '
            '<a href="/tags/zinnia/" target="blank">zinnia</a>',
            'zinnia, test')  # Yes, this is not the same order...

    def test_get_sites(self):
        self.assertEqual(self.admin.get_sites(self.entry), '')
        self.entry.sites.add(Site.objects.get_current())
        self.check_with_rich_and_poor_urls(
            self.admin.get_sites, (self.entry,),
            '<a href="http://example.com/" target="blank">example.com</a>',
            '<a href="http://example.com" target="blank">example.com</a>')

    def test_get_short_url(self):
        self.check_with_rich_and_poor_urls(
            self.admin.get_short_url, (self.entry,),
            '<a href="http://example.com/%(hash)s/" target="blank">'
            'http://example.com/%(hash)s/</a>' % {
                'hash': base36(self.entry.pk)},
            '<a href="%(url)s" target="blank">%(url)s</a>' % {
                'url': self.entry.get_absolute_url()})

    def test_get_is_visible(self):
        self.assertEqual(self.admin.get_is_visible(self.entry),
                         self.entry.is_visible)

    def test_save_model(self):
        user = Author.objects.create_user(
            'user', 'user@exemple.com')
        self.request.user = user
        form = EntryAdmin.form({'title': 'title'})
        form.is_valid()
        self.entry.status = PUBLISHED
        self.admin.save_model(self.request, self.entry,
                              form, False)
        self.assertEqual(len(form.cleaned_data['authors']), 0)
        self.assertEqual(self.entry.excerpt, self.entry.content)
        self.admin.save_model(self.request, Entry(),
                              form, False)
        self.assertEqual(len(form.cleaned_data['authors']), 1)

    def test_queryset(self):
        user = Author.objects.create_user(
            'user', 'user@exemple.com')
        self.entry.authors.add(user)
        root = Author.objects.create_superuser(
            'root', 'root@exemple.com', 'toor')
        params = {'title': 'My root title',
                  'content': 'My root content',
                  'slug': 'my-root-titile'}
        root_entry = Entry.objects.create(**params)
        root_entry.authors.add(root)
        self.request.user = user
        self.assertEqual(len(self.admin.get_queryset(self.request)), 1)
        self.request.user = root
        self.assertEqual(len(self.admin.get_queryset(self.request)), 2)

    def test_formfield_for_manytomany(self):
        staff = Author.objects.create_user(
            'staff', 'staff@exemple.com')
        author = Author.objects.create_user(
            'author', 'author@exemple.com')
        root = Author.objects.create_superuser(
            'root', 'root@exemple.com', 'toor')
        self.request.user = staff
        field = self.admin.formfield_for_manytomany(
            Entry.authors.field, self.request)
        self.assertEqual(field.queryset.count(), 1)
        self.request.user = root
        field = self.admin.formfield_for_manytomany(
            Entry.authors.field, self.request)
        self.assertEqual(field.queryset.count(), 1)
        staff.is_staff = True
        staff.save()
        field = self.admin.formfield_for_manytomany(
            Entry.authors.field, self.request)
        self.assertEqual(field.queryset.count(), 2)
        self.entry.authors.add(author)
        field = self.admin.formfield_for_manytomany(
            Entry.authors.field, self.request)
        self.assertEqual(field.queryset.count(), 3)

    def test_get_readonly_fields(self):
        user = Author.objects.create_user(
            'user', 'user@exemple.com')
        root = Author.objects.create_superuser(
            'root', 'root@exemple.com', 'toor')
        self.request.user = user
        self.assertEqual(self.admin.get_readonly_fields(self.request),
                         ['status'])
        self.request.user = root
        self.assertEqual(self.admin.get_readonly_fields(self.request),
                         ())

    def test_get_actions(self):
        original_ping_directories = settings.PING_DIRECTORIES
        user = Author.objects.create_user(
            'user', 'user@exemple.com')
        root = Author.objects.create_superuser(
            'root', 'root@exemple.com', 'toor')
        self.request.user = user
        settings.PING_DIRECTORIES = True
        self.assertEqual(
            list(self.admin.get_actions(self.request).keys()),
            ['delete_selected',
             'close_comments',
             'close_pingbacks',
             'close_trackbacks',
             'ping_directories',
             'put_on_top',
             'mark_featured',
             'unmark_featured'])
        settings.PING_DIRECTORIES = False
        self.assertEqual(
            list(self.admin.get_actions(self.request).keys()),
            ['delete_selected',
             'close_comments',
             'close_pingbacks',
             'close_trackbacks',
             'put_on_top',
             'mark_featured',
             'unmark_featured'])
        self.request.user = root
        self.assertEqual(
            list(self.admin.get_actions(self.request).keys()),
            ['delete_selected',
             'make_mine',
             'make_published',
             'make_hidden',
             'close_comments',
             'close_pingbacks',
             'close_trackbacks',
             'put_on_top',
             'mark_featured',
             'unmark_featured'])
        settings.PING_DIRECTORIES = original_ping_directories

    def test_get_actions_in_popup_mode_issue_291(self):
        user = Author.objects.create_user(
            'user', 'user@exemple.com')
        request = self.request_factory.get('/?_popup=1')
        request.user = user
        self.assertEqual(
            list(self.admin.get_actions(request).keys()),
            [])

    def test_make_mine(self):
        user = Author.objects.create_user(
            'user', 'user@exemple.com')
        self.request.user = user
        self.request._messages = TestMessageBackend()
        self.assertEqual(user.entries.count(), 0)
        self.admin.make_mine(self.request, Entry.objects.all())
        self.assertEqual(user.entries.count(), 1)
        self.assertEqual(len(self.request._messages.messages), 1)

    def test_make_published(self):
        original_ping_directories = settings.PING_DIRECTORIES
        settings.PING_DIRECTORIES = []
        self.request._messages = TestMessageBackend()
        self.entry.sites.add(Site.objects.get_current())
        self.assertEqual(Entry.published.count(), 0)
        self.admin.make_published(self.request, Entry.objects.all())
        self.assertEqual(Entry.published.count(), 1)
        self.assertEqual(len(self.request._messages.messages), 1)
        settings.PING_DIRECTORIES = original_ping_directories

    def test_make_hidden(self):
        self.request._messages = TestMessageBackend()
        self.entry.status = PUBLISHED
        self.entry.save()
        self.entry.sites.add(Site.objects.get_current())
        self.assertEqual(Entry.published.count(), 1)
        self.admin.make_hidden(self.request, Entry.objects.all())
        self.assertEqual(Entry.published.count(), 0)
        self.assertEqual(len(self.request._messages.messages), 1)

    def test_close_comments(self):
        self.request._messages = TestMessageBackend()
        self.assertEqual(Entry.objects.filter(
            comment_enabled=True).count(), 1)
        self.admin.close_comments(self.request, Entry.objects.all())
        self.assertEqual(Entry.objects.filter(
            comment_enabled=True).count(), 0)
        self.assertEqual(len(self.request._messages.messages), 1)

    def test_close_pingbacks(self):
        self.request._messages = TestMessageBackend()
        self.assertEqual(Entry.objects.filter(
            pingback_enabled=True).count(), 1)
        self.admin.close_pingbacks(self.request, Entry.objects.all())
        self.assertEqual(Entry.objects.filter(
            pingback_enabled=True).count(), 0)
        self.assertEqual(len(self.request._messages.messages), 1)

    def test_close_trackbacks(self):
        self.request._messages = TestMessageBackend()
        self.assertEqual(Entry.objects.filter(
            trackback_enabled=True).count(), 1)
        self.admin.close_trackbacks(self.request, Entry.objects.all())
        self.assertEqual(Entry.objects.filter(
            trackback_enabled=True).count(), 0)
        self.assertEqual(len(self.request._messages.messages), 1)

    def test_put_on_top(self):
        original_ping_directories = settings.PING_DIRECTORIES
        settings.PING_DIRECTORIES = []
        self.request._messages = TestMessageBackend()
        self.entry.creation_date = datetime(2011, 1, 1, 12, 0)
        self.admin.put_on_top(self.request, Entry.objects.all())
        self.assertEqual(
            Entry.objects.get(pk=self.entry.pk).creation_date.date(),
            timezone.now().date())
        self.assertEqual(len(self.request._messages.messages), 1)
        settings.PING_DIRECTORIES = original_ping_directories

    def test_mark_unmark_featured(self):
        self.request._messages = TestMessageBackend()
        self.assertEqual(Entry.objects.filter(
            featured=True).count(), 0)
        self.admin.mark_featured(self.request, Entry.objects.all())
        self.assertEqual(Entry.objects.filter(featured=True).count(), 1)
        self.assertEqual(len(self.request._messages.messages), 1)
        self.admin.unmark_featured(self.request, Entry.objects.all())
        self.assertEqual(Entry.objects.filter(featured=True).count(), 0)
        self.assertEqual(len(self.request._messages.messages), 2)

    def test_autocomplete_tags(self):
        template_to_use = 'admin/zinnia/entry/autocomplete_tags.js'
        setup_test_template_loader({template_to_use: ''})
        response = self.admin.autocomplete_tags(self.request)
        self.assertTemplateUsed(response, template_to_use)
        self.assertEqual(response['Content-Type'], 'application/javascript')

    def test_wymeditor(self):
        template_to_use = 'admin/zinnia/entry/wymeditor.js'
        setup_test_template_loader({template_to_use: ''})
        response = self.admin.wymeditor(self.request)
        self.assertTemplateUsed(response, template_to_use)
        self.assertEqual(len(response.context_data['lang']), 2)
        self.assertEqual(response['Content-Type'], 'application/javascript')

    def test_markitup(self):
        template_to_use = 'admin/zinnia/entry/markitup.js'
        setup_test_template_loader({template_to_use: ''})
        response = self.admin.markitup(self.request)
        self.assertTemplateUsed(response, template_to_use)
        self.assertEqual(response['Content-Type'], 'application/javascript')

    def test_content_preview(self):
        template_to_use = 'admin/zinnia/entry/preview.html'
        setup_test_template_loader({template_to_use: ''})
        response = self.admin.content_preview(self.request)
        self.assertTemplateUsed(response, template_to_use)
        self.assertEqual(response.context_data['preview'], '<p></p>')
        self.assertEqual(response['Content-Type'], 'text/html; charset=utf-8')


class CategoryAdminTestCase(BaseAdminTestCase):
    """Test cases for Category Admin"""
    model_class = Category
    admin_class = CategoryAdmin

    def test_get_tree_path(self):
        category = Category.objects.create(title='Category', slug='cat')

        self.check_with_rich_and_poor_urls(
            self.admin.get_tree_path, (category,),
            '<a href="/categories/cat/" target="blank">/cat/</a>',
            '/cat/')

########NEW FILE########
__FILENAME__ = test_admin_fields
"""Test cases for Zinnia's admin fields"""
from django.test import TestCase
from django.utils.encoding import smart_text

from zinnia.models import Category
from zinnia.admin.fields import MPTTModelChoiceIterator
from zinnia.admin.fields import MPTTModelMultipleChoiceField


class MPTTModelChoiceIteratorTestCase(TestCase):

    def test_choice(self):
        category_1 = Category.objects.create(
            title='Category 1', slug='cat-1')
        category_2 = Category.objects.create(
            title='Category 2', slug='cat-2',
            parent=category_1)

        class FakeField(object):
            queryset = Category.objects.all()

            def prepare_value(self, value):
                return value.pk

            def label_from_instance(self, obj):
                return smart_text(obj)

        field = FakeField()
        iterator = MPTTModelChoiceIterator(field)

        self.assertEqual(iterator.choice(category_1),
                         (category_1.pk, 'Category 1', (1, 1)))
        self.assertEqual(iterator.choice(category_2),
                         (category_2.pk, 'Category 2', (1, 2)))


class MPTTModelMultipleChoiceFieldTestCase(TestCase):

    def setUp(self):
        self.category_1 = Category.objects.create(
            title='Category 1', slug='cat-1')
        self.category_2 = Category.objects.create(
            title='Category 2', slug='cat-2',
            parent=self.category_1)

    def test_label_from_instance(self):
        queryset = Category.objects.all()

        field = MPTTModelMultipleChoiceField(
            queryset=queryset)
        self.assertEqual(field.label_from_instance(self.category_1),
                         'Category 1')
        self.assertEqual(field.label_from_instance(self.category_2),
                         '|-- Category 2')
        field = MPTTModelMultipleChoiceField(
            level_indicator='-->', queryset=queryset)
        self.assertEqual(field.label_from_instance(self.category_2),
                         '--> Category 2')

    def test_get_choices(self):
        queryset = Category.objects.all()

        field = MPTTModelMultipleChoiceField(
            queryset=queryset)
        self.assertEqual(list(field.choices),
                         [(self.category_1.pk, 'Category 1', (1, 1)),
                          (self.category_2.pk, '|-- Category 2', (1, 2))])

        field = MPTTModelMultipleChoiceField(
            level_indicator='-->', queryset=queryset)
        self.assertEqual(list(field.choices),
                         [(self.category_1.pk, 'Category 1', (1, 1)),
                          (self.category_2.pk, '--> Category 2', (1, 2))])

########NEW FILE########
__FILENAME__ = test_admin_filters
"""Test cases for Zinnia's admin filters"""
from django.test import TestCase
from django.test import RequestFactory
from django.contrib.admin import site
from django.contrib.admin import ModelAdmin
from django.contrib.sites.models import Site
from django.utils.translation import activate
from django.utils.translation import deactivate
from django.contrib.admin.views.main import ChangeList
from django.contrib.auth.tests.utils import skipIfCustomUser

from zinnia.models.entry import Entry
from zinnia.models.author import Author
from zinnia.models.category import Category
from zinnia.managers import PUBLISHED
from zinnia.admin.filters import AuthorListFilter
from zinnia.admin.filters import CategoryListFilter
from zinnia.signals import disconnect_entry_signals


class MiniEntryAuthorAdmin(ModelAdmin):
    list_filter = [AuthorListFilter]


class MiniEntryCategoryAdmin(ModelAdmin):
    list_filter = [CategoryListFilter]


class BaseListFilterTestCase(TestCase):
    """Base TestCase for testing Filters"""
    urls = 'zinnia.tests.implementations.urls.default'

    def setUp(self):
        disconnect_entry_signals()
        activate('en')
        self.request_factory = RequestFactory()
        self.site = Site.objects.get_current()

        params = {'title': 'My entry 1',
                  'content': 'My content 1',
                  'status': PUBLISHED,
                  'slug': 'my-entry-1'}
        self.entry_1 = Entry.objects.create(**params)
        self.entry_1.sites.add(self.site)

        params = {'title': 'My entry 2',
                  'content': 'My content 2',
                  'status': PUBLISHED,
                  'slug': 'my-entry-2'}
        self.entry_2 = Entry.objects.create(**params)
        self.entry_2.sites.add(self.site)

        params = {'title': 'My entry draft',
                  'content': 'My content draft',
                  'slug': 'my-entry-draft'}
        self.entry_draft = Entry.objects.create(**params)
        self.entry_draft.sites.add(self.site)

    def tearDown(self):
        deactivate()

    def get_changelist(self, request, model, modeladmin):
        return ChangeList(
            request, model, modeladmin.list_display,
            modeladmin.list_display_links, modeladmin.list_filter,
            modeladmin.date_hierarchy, modeladmin.search_fields,
            modeladmin.list_select_related, modeladmin.list_per_page,
            modeladmin.list_max_show_all, modeladmin.list_editable, modeladmin)


@skipIfCustomUser
class AuthorListFilterTestCase(BaseListFilterTestCase):
    """Test case for AuthorListFilter"""

    def setUp(self):
        super(AuthorListFilterTestCase, self).setUp()
        self.authors = [
            Author.objects.create_user(username='webmaster',
                                       email='webmaster@example.com'),
            Author.objects.create_user(username='contributor',
                                       email='contributor@example.com'),
            Author.objects.create_user(username='reader',
                                       email='reader@example.com')]
        self.entry_1.authors.add(self.authors[0])
        self.entry_2.authors.add(*self.authors[:-1])
        self.entry_draft.authors.add(*self.authors)

    def test_filter(self):
        modeladmin = MiniEntryAuthorAdmin(Entry, site)

        request = self.request_factory.get('/')
        changelist = self.get_changelist(request, Entry, modeladmin)
        queryset = changelist.get_queryset(request)
        self.assertEqual(queryset.count(), 3)

        request = self.request_factory.get('/', {'author': self.authors[1].pk})
        changelist = self.get_changelist(request, Entry, modeladmin)
        queryset = changelist.get_queryset(request)
        self.assertEqual(queryset.count(), 2)

        with self.assertNumQueries(1):
            filterspec = changelist.get_filters(request)[0][0]
            self.assertEqual(filterspec.title, 'published authors')
            self.assertEqual(filterspec.used_parameters,
                             {'author': str(self.authors[1].pk)})
            self.assertEqual(filterspec.lookup_choices,
                             [(str(self.authors[0].pk),
                               'webmaster (2 entries)'),
                              (str(self.authors[1].pk),
                               'contributor (1 entry)')])


class CategoryListFilterTestCase(BaseListFilterTestCase):
    """Test case for CategoryListFilter"""

    def setUp(self):
        super(CategoryListFilterTestCase, self).setUp()
        self.categories = [
            Category.objects.create(title='Category 1',
                                    slug='cat-1'),
            Category.objects.create(title='Category 2',
                                    slug='cat-2'),
            Category.objects.create(title='Category 3',
                                    slug='cat-3')]

        self.entry_1.categories.add(self.categories[0])
        self.entry_2.categories.add(*self.categories[:-1])
        self.entry_draft.categories.add(*self.categories)

    def test_filter(self):
        modeladmin = MiniEntryCategoryAdmin(Entry, site)

        request = self.request_factory.get('/')
        changelist = self.get_changelist(request, Entry, modeladmin)
        queryset = changelist.get_queryset(request)
        self.assertEqual(queryset.count(), 3)

        request = self.request_factory.get('/', {'category':
                                                 str(self.categories[1].pk)})
        changelist = self.get_changelist(request, Entry, modeladmin)
        queryset = changelist.get_queryset(request)
        self.assertEqual(queryset.count(), 2)

        with self.assertNumQueries(1):
            filterspec = changelist.get_filters(request)[0][0]
            self.assertEqual(filterspec.title, 'published categories')
            self.assertEqual(filterspec.used_parameters,
                             {'category': str(self.categories[1].pk)})
            self.assertEqual(filterspec.lookup_choices,
                             [(str(self.categories[0].pk),
                               'Category 1 (2 entries)'),
                              (str(self.categories[1].pk),
                               'Category 2 (1 entry)')])

########NEW FILE########
__FILENAME__ = test_admin_forms
"""Test cases for Zinnia's admin forms"""
from django.test import TestCase
from django.contrib.admin.widgets import RelatedFieldWidgetWrapper

from zinnia.models import Category
from zinnia.admin.forms import EntryAdminForm
from zinnia.admin.forms import CategoryAdminForm


class EntryAdminFormTestCase(TestCase):

    def test_categories_has_related_widget(self):
        form = EntryAdminForm()
        self.assertTrue(
            isinstance(form.fields['categories'].widget,
                       RelatedFieldWidgetWrapper))

    def test_initial_sites(self):
        form = EntryAdminForm()
        self.assertEqual(
            len(form.fields['sites'].initial), 1)


class CategoryAdminFormTestCase(TestCase):

    def test_parent_has_related_widget(self):
        form = CategoryAdminForm()
        self.assertTrue(
            isinstance(form.fields['parent'].widget,
                       RelatedFieldWidgetWrapper))

    def test_clean_parent(self):
        category = Category.objects.create(
            title='Category 1', slug='cat-1')
        datas = {'parent': category.pk,
                 'title': category.title,
                 'slug': category.slug}
        form = CategoryAdminForm(datas, instance=category)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors['parent']), 1)

        subcategory = Category.objects.create(
            title='Category 2', slug='cat-2')
        self.assertEqual(subcategory.parent, None)

        datas = {'parent': category.pk,
                 'title': subcategory.title,
                 'slug': subcategory.slug}
        form = CategoryAdminForm(datas, instance=subcategory)
        self.assertTrue(form.is_valid())

########NEW FILE########
__FILENAME__ = test_admin_widgets
# coding=utf-8
"""Test cases for Zinnia's admin widgets"""
from django.test import TestCase
from django.utils.encoding import smart_text

from zinnia.admin.widgets import MPTTFilteredSelectMultiple


class MPTTFilteredSelectMultipleTestCase(TestCase):

    def test_render_option(self):
        widget = MPTTFilteredSelectMultiple('test', False)

        option = widget.render_option([], 1, 'Test', (4, 5))

        self.assertEqual(
            option,
            '<option value="1" data-tree-id="4"'
            ' data-left-value="5">Test</option>')

        option = widget.render_option(['0', '1', '2'], 1, 'Test', (4, 5))

        self.assertEqual(
            option,
            '<option value="1" selected="selected" data-tree-id="4"'
            ' data-left-value="5">Test</option>')

    def test_render_option_non_ascii_issue_317(self):
        widget = MPTTFilteredSelectMultiple('test', False)

        option = widget.render_option([], 1, 'тест', (1, 1))

        self.assertEqual(
            option,
            smart_text('<option value="1" data-tree-id="1"'
                       ' data-left-value="1">тест</option>'))

    def test_render_options(self):
        widget = MPTTFilteredSelectMultiple('test', False)
        self.assertEqual(widget.render_options([], []), '')

        options = widget.render_options([
            (1, 'Category 1', (1, 1)),
            (2, '|-- Category 2', (1, 2))], [])

        self.assertEqual(
            options,
            '<option value="1" data-tree-id="1" data-left-value="1">'
            'Category 1</option>\n<option value="2" data-tree-id="1" '
            'data-left-value="2">|-- Category 2</option>')

        options = widget.render_options([
            (1, 'Category 1', (1, 1)),
            (2, '|-- Category 2', (1, 2))], [2])

        self.assertEqual(
            options,
            '<option value="1" data-tree-id="1" data-left-value="1">'
            'Category 1</option>\n<option value="2" selected="selected" '
            'data-tree-id="1" data-left-value="2">|-- Category 2</option>')

########NEW FILE########
__FILENAME__ = test_author
"""Test cases for Zinnia's Author"""
from django.test import TestCase
from django.contrib.sites.models import Site
from django.contrib.auth.tests.utils import skipIfCustomUser
from django.contrib.auth import get_user_model

from zinnia.models.entry import Entry
from zinnia.models.author import Author
from zinnia.managers import PUBLISHED
from zinnia.signals import disconnect_entry_signals


@skipIfCustomUser
class AuthorTestCase(TestCase):

    def setUp(self):
        disconnect_entry_signals()
        self.site = Site.objects.get_current()
        self.author = Author.objects.create_user(
            'webmaster', 'webmaster@example.com')
        params = {'title': 'My entry',
                  'content': 'My content',
                  'tags': 'zinnia, test',
                  'slug': 'my-entry'}

        self.entry = Entry.objects.create(**params)
        self.entry.authors.add(self.author)
        self.entry.sites.add(self.site)

    def test_entries_published(self):
        self.assertEqual(self.author.entries_published().count(), 0)
        self.entry.status = PUBLISHED
        self.entry.save()
        self.assertEqual(self.author.entries_published().count(), 1)

    def test_str(self):
        self.assertEqual(self.author.__str__(),
                         'webmaster')
        self.author.first_name = 'John'
        self.assertEqual(self.author.__str__(),
                         'John')
        self.author.last_name = 'Doe'
        self.assertEqual(self.author.__str__(),
                         'John Doe')

    def test_manager_pollution(self):
        """
        https://github.com/Fantomas42/django-blog-zinnia/pull/307
        """
        self.assertNotEqual(get_user_model().objects.model,
                            Author)

########NEW FILE########
__FILENAME__ = test_category
"""Test cases for Zinnia's Category"""
from django.test import TestCase
from django.contrib.sites.models import Site

from zinnia.models.entry import Entry
from zinnia.models.category import Category
from zinnia.managers import PUBLISHED
from zinnia.signals import disconnect_entry_signals


class CategoryTestCase(TestCase):

    def setUp(self):
        disconnect_entry_signals()
        self.site = Site.objects.get_current()
        self.categories = [Category.objects.create(title='Category 1',
                                                   slug='category-1'),
                           Category.objects.create(title='Category 2',
                                                   slug='category-2')]
        params = {'title': 'My entry',
                  'content': 'My content',
                  'tags': 'zinnia, test',
                  'slug': 'my-entry'}

        self.entry = Entry.objects.create(**params)
        self.entry.categories.add(*self.categories)
        self.entry.sites.add(self.site)

    def test_entries_published(self):
        category = self.categories[0]
        self.assertEqual(category.entries_published().count(), 0)
        self.entry.status = PUBLISHED
        self.entry.save()
        self.assertEqual(category.entries_published().count(), 1)

        params = {'title': 'My second entry',
                  'content': 'My second content',
                  'tags': 'zinnia, test',
                  'status': PUBLISHED,
                  'slug': 'my-second-entry'}

        new_entry = Entry.objects.create(**params)
        new_entry.sites.add(self.site)
        new_entry.categories.add(self.categories[0])

        self.assertEqual(self.categories[0].entries_published().count(), 2)
        self.assertEqual(self.categories[1].entries_published().count(), 1)

    def test_entries_tree_path(self):
        self.categories.extend([Category.objects.create(title='Category 3',
                                                        slug='category-3'),
                                Category.objects.create(title='Category 4',
                                                        slug='category-4')])
        with self.assertNumQueries(0):
            self.assertEqual(self.categories[0].tree_path, 'category-1')
            self.assertEqual(self.categories[1].tree_path, 'category-2')

        self.categories[1].parent = self.categories[0]
        self.categories[1].save()
        self.categories[1].parent = self.categories[0]
        self.categories[1].save()
        self.categories[2].parent = self.categories[1]
        self.categories[2].save()
        self.categories[3].parent = self.categories[2]
        self.categories[3].save()

        category = Category.objects.get(slug='category-2')
        with self.assertNumQueries(1):
            self.assertEqual(category.tree_path, 'category-1/category-2')

        category = Category.objects.get(slug='category-4')
        with self.assertNumQueries(1):
            self.assertEqual(category.tree_path,
                             'category-1/category-2/category-3/category-4')

########NEW FILE########
__FILENAME__ = test_comparison
"""Test cases for Zinnia's comparison"""
from django.test import TestCase

from zinnia.models.entry import Entry
from zinnia.comparison import pearson_score
from zinnia.comparison import VectorBuilder
from zinnia.comparison import ClusteredModel
from zinnia.signals import disconnect_entry_signals


class ComparisonTestCase(TestCase):
    """Test cases for comparison tools"""

    def setUp(self):
        disconnect_entry_signals()

    def test_pearson_score(self):
        self.assertEqual(pearson_score([42], [42]), 1.0)
        self.assertEqual(pearson_score([0, 1, 2], [0, 1, 2]), 1.0)
        self.assertEqual(pearson_score([0, 1, 3], [0, 1, 2]),
                         0.9819805060619656)
        self.assertEqual(pearson_score([0, 1, 2], [0, 1, 3]),
                         0.9819805060619656)

    def test_clustered_model(self):
        params = {'title': 'My entry 1', 'content': 'My content 1',
                  'tags': 'zinnia, test', 'slug': 'my-entry-1'}
        entry_1 = Entry.objects.create(**params)
        params = {'title': 'My entry 2', 'content': 'My content 2',
                  'tags': 'zinnia, test', 'slug': 'my-entry-2'}
        entry_2 = Entry.objects.create(**params)
        cm = ClusteredModel(Entry.objects.all())
        self.assertEqual(list(cm.dataset().values()),
                         [str(entry_1.pk), str(entry_2.pk)])
        cm = ClusteredModel(Entry.objects.all(),
                            ['title', 'excerpt', 'content'])
        self.assertEqual(list(cm.dataset().values()),
                         ['My entry 1  My content 1',
                          'My entry 2  My content 2'])

    def test_vector_builder(self):
        vectors = VectorBuilder(Entry.objects.all(),
                                ['title', 'excerpt', 'content'])
        params = {'title': 'My entry 1', 'content':
                  'This is my first content',
                  'tags': 'zinnia, test', 'slug': 'my-entry-1'}
        Entry.objects.create(**params)
        params = {'title': 'My entry 2', 'content':
                  'My second entry',
                  'tags': 'zinnia, test', 'slug': 'my-entry-2'}
        Entry.objects.create(**params)
        columns, dataset = vectors()
        self.assertEqual(sorted(columns), sorted(
            ['content', 'This', 'my', 'is', '1',
             'second', '2', 'first']))
        self.assertEqual(sorted([sorted(row) for row in dataset.values()]),
                         sorted([sorted([1, 1, 1, 1, 1, 0, 0, 1]),
                                 sorted([0, 0, 0, 0, 0, 1, 1, 0])]))

########NEW FILE########
__FILENAME__ = test_entry
"""Test cases for Zinnia's Entry"""
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from django.utils.unittest import skipUnless
from django.contrib.sites.models import Site
from django.core.urlresolvers import reverse
from django.utils.translation import activate
from django.utils.translation import deactivate
from django.test.utils import override_settings
from django.contrib.auth.tests.utils import skipIfCustomUser

import django_comments as comments
from django_comments.models import CommentFlag

from zinnia.managers import PUBLISHED
from zinnia.models_bases import entry
from zinnia.models.entry import Entry
from zinnia.models.author import Author
from zinnia.flags import PINGBACK, TRACKBACK
from zinnia.tests.utils import datetime
from zinnia.tests.utils import is_lib_available
from zinnia import url_shortener as shortener_settings
from zinnia.signals import disconnect_entry_signals
from zinnia.signals import disconnect_discussion_signals
from zinnia.url_shortener.backends.default import base36


class EntryTestCase(TestCase):

    def setUp(self):
        disconnect_entry_signals()
        disconnect_discussion_signals()
        params = {'title': 'My entry',
                  'content': 'My content',
                  'slug': 'my-entry'}
        self.entry = Entry.objects.create(**params)

    @skipIfCustomUser
    def test_discussions(self):
        site = Site.objects.get_current()
        self.assertEqual(self.entry.discussions.count(), 0)
        self.assertEqual(self.entry.comments.count(), 0)
        self.assertEqual(self.entry.pingbacks.count(), 0)
        self.assertEqual(self.entry.trackbacks.count(), 0)

        comments.get_model().objects.create(
            comment='My Comment 1',
            content_object=self.entry,
            submit_date=timezone.now(),
            site=site)
        self.assertEqual(self.entry.discussions.count(), 1)
        self.assertEqual(self.entry.comments.count(), 1)
        self.assertEqual(self.entry.pingbacks.count(), 0)
        self.assertEqual(self.entry.trackbacks.count(), 0)

        comments.get_model().objects.create(
            comment='My Comment 2',
            content_object=self.entry,
            submit_date=timezone.now(),
            site=site, is_public=False)
        self.assertEqual(self.entry.discussions.count(), 1)
        self.assertEqual(self.entry.comments.count(), 1)
        self.assertEqual(self.entry.pingbacks.count(), 0)
        self.assertEqual(self.entry.trackbacks.count(), 0)

        author = Author.objects.create_user(username='webmaster',
                                            email='webmaster@example.com')

        comment = comments.get_model().objects.create(
            comment='My Comment 3',
            content_object=self.entry,
            submit_date=timezone.now(),
            site=Site.objects.create(domain='http://toto.com',
                                     name='Toto.com'))
        comment.flags.create(user=author, flag=CommentFlag.MODERATOR_APPROVAL)
        self.assertEqual(self.entry.discussions.count(), 2)
        self.assertEqual(self.entry.comments.count(), 2)
        self.assertEqual(self.entry.pingbacks.count(), 0)
        self.assertEqual(self.entry.trackbacks.count(), 0)

        comment = comments.get_model().objects.create(
            comment='My Pingback 1',
            content_object=self.entry,
            submit_date=timezone.now(),
            site=site)
        comment.flags.create(user=author, flag=PINGBACK)
        self.assertEqual(self.entry.discussions.count(), 3)
        self.assertEqual(self.entry.comments.count(), 2)
        self.assertEqual(self.entry.pingbacks.count(), 1)
        self.assertEqual(self.entry.trackbacks.count(), 0)

        comment = comments.get_model().objects.create(
            comment='My Trackback 1',
            content_object=self.entry,
            submit_date=timezone.now(),
            site=site)
        comment.flags.create(user=author, flag=TRACKBACK)
        self.assertEqual(self.entry.discussions.count(), 4)
        self.assertEqual(self.entry.comments.count(), 2)
        self.assertEqual(self.entry.pingbacks.count(), 1)
        self.assertEqual(self.entry.trackbacks.count(), 1)

    def test_str(self):
        activate('en')
        self.assertEqual(str(self.entry), 'My entry: draft')
        deactivate()

    def test_word_count(self):
        self.assertEqual(self.entry.word_count, 2)

    def test_comments_are_open(self):
        original_auto_close = entry.AUTO_CLOSE_COMMENTS_AFTER
        entry.AUTO_CLOSE_COMMENTS_AFTER = None
        self.assertEqual(self.entry.comments_are_open, True)
        entry.AUTO_CLOSE_COMMENTS_AFTER = -1
        self.assertEqual(self.entry.comments_are_open, True)
        entry.AUTO_CLOSE_COMMENTS_AFTER = 0
        self.assertEqual(self.entry.comments_are_open, False)
        entry.AUTO_CLOSE_COMMENTS_AFTER = 5
        self.assertEqual(self.entry.comments_are_open, True)
        self.entry.start_publication = timezone.now() - timedelta(days=7)
        self.entry.save()
        self.assertEqual(self.entry.comments_are_open, False)
        entry.AUTO_CLOSE_COMMENTS_AFTER = original_auto_close

    def test_pingbacks_are_open(self):
        original_auto_close = entry.AUTO_CLOSE_PINGBACKS_AFTER
        entry.AUTO_CLOSE_PINGBACKS_AFTER = None
        self.assertEqual(self.entry.pingbacks_are_open, True)
        entry.AUTO_CLOSE_PINGBACKS_AFTER = -1
        self.assertEqual(self.entry.pingbacks_are_open, True)
        entry.AUTO_CLOSE_PINGBACKS_AFTER = 0
        self.assertEqual(self.entry.pingbacks_are_open, False)
        entry.AUTO_CLOSE_PINGBACKS_AFTER = 5
        self.assertEqual(self.entry.pingbacks_are_open, True)
        self.entry.start_publication = timezone.now() - timedelta(days=7)
        self.entry.save()
        self.assertEqual(self.entry.pingbacks_are_open, False)
        entry.AUTO_CLOSE_PINGBACKS_AFTER = original_auto_close

    def test_trackbacks_are_open(self):
        original_auto_close = entry.AUTO_CLOSE_TRACKBACKS_AFTER
        entry.AUTO_CLOSE_TRACKBACKS_AFTER = None
        self.assertEqual(self.entry.trackbacks_are_open, True)
        entry.AUTO_CLOSE_TRACKBACKS_AFTER = -1
        self.assertEqual(self.entry.trackbacks_are_open, True)
        entry.AUTO_CLOSE_TRACKBACKS_AFTER = 0
        self.assertEqual(self.entry.trackbacks_are_open, False)
        entry.AUTO_CLOSE_TRACKBACKS_AFTER = 5
        self.assertEqual(self.entry.trackbacks_are_open, True)
        self.entry.start_publication = timezone.now() - timedelta(days=7)
        self.entry.save()
        self.assertEqual(self.entry.trackbacks_are_open, False)
        entry.AUTO_CLOSE_TRACKBACKS_AFTER = original_auto_close

    def test_is_actual(self):
        self.assertTrue(self.entry.is_actual)
        self.entry.start_publication = datetime(2020, 3, 15)
        self.assertFalse(self.entry.is_actual)
        self.entry.start_publication = timezone.now()
        self.assertTrue(self.entry.is_actual)
        self.entry.end_publication = datetime(2000, 3, 15)
        self.assertFalse(self.entry.is_actual)

    def test_is_visible(self):
        self.assertFalse(self.entry.is_visible)
        self.entry.status = PUBLISHED
        self.assertTrue(self.entry.is_visible)
        self.entry.start_publication = datetime(2020, 3, 15)
        self.assertFalse(self.entry.is_visible)

    def test_short_url(self):
        original_shortener = shortener_settings.URL_SHORTENER_BACKEND
        shortener_settings.URL_SHORTENER_BACKEND = 'zinnia.url_shortener.'\
                                                   'backends.default'
        self.assertEqual(self.entry.short_url,
                         'http://example.com' +
                         reverse('zinnia:entry_shortlink',
                                 args=[base36(self.entry.pk)]))
        shortener_settings.URL_SHORTENER_BACKEND = original_shortener

    def test_previous_entry(self):
        site = Site.objects.get_current()
        with self.assertNumQueries(0):
            # entry.previous_entry does not works until entry
            # is published, so no query should be performed
            self.assertFalse(self.entry.previous_entry)
        self.entry.status = PUBLISHED
        self.entry.save()
        self.entry.sites.add(site)
        del self.entry.previous_next  # Invalidate the cached property
        with self.assertNumQueries(1):
            self.assertFalse(self.entry.previous_entry)
            # Reload to check the cache
            self.assertFalse(self.entry.previous_entry)
        params = {'title': 'My second entry',
                  'content': 'My second content',
                  'slug': 'my-second-entry',
                  'creation_date': datetime(2000, 1, 1),
                  'status': PUBLISHED}
        self.second_entry = Entry.objects.create(**params)
        self.second_entry.sites.add(site)
        del self.entry.previous_next  # Invalidate the cached property
        with self.assertNumQueries(1):
            self.assertEqual(self.entry.previous_entry, self.second_entry)
            # Reload to check the cache
            self.assertEqual(self.entry.previous_entry, self.second_entry)
        params = {'title': 'My third entry',
                  'content': 'My third content',
                  'slug': 'my-third-entry',
                  'creation_date': datetime(2001, 1, 1),
                  'status': PUBLISHED}
        self.third_entry = Entry.objects.create(**params)
        self.third_entry.sites.add(site)
        del self.entry.previous_next  # Invalidate the cached property
        self.assertEqual(self.entry.previous_entry, self.third_entry)
        self.assertEqual(self.third_entry.previous_entry, self.second_entry)
        self.assertFalse(self.second_entry.previous_entry)

    def test_next_entry(self):
        site = Site.objects.get_current()
        with self.assertNumQueries(0):
            # entry.next_entry does not works until entry
            # is published, so no query should be performed
            self.assertFalse(self.entry.previous_entry)
        self.entry.status = PUBLISHED
        self.entry.save()
        self.entry.sites.add(site)
        del self.entry.previous_next  # Invalidate the cached property
        with self.assertNumQueries(1):
            self.assertFalse(self.entry.next_entry)
            # Reload to check the cache
            self.assertFalse(self.entry.next_entry)
        params = {'title': 'My second entry',
                  'content': 'My second content',
                  'slug': 'my-second-entry',
                  'creation_date': datetime(2100, 1, 1),
                  'status': PUBLISHED}
        self.second_entry = Entry.objects.create(**params)
        self.second_entry.sites.add(site)
        del self.entry.previous_next  # Invalidate the cached property
        with self.assertNumQueries(1):
            self.assertEqual(self.entry.next_entry, self.second_entry)
            # Reload to check the cache
            self.assertEqual(self.entry.next_entry, self.second_entry)
        params = {'title': 'My third entry',
                  'content': 'My third content',
                  'slug': 'my-third-entry',
                  'creation_date': datetime(2050, 1, 1),
                  'status': PUBLISHED}
        self.third_entry = Entry.objects.create(**params)
        self.third_entry.sites.add(site)
        del self.entry.previous_next  # Invalidate the cached property
        self.assertEqual(self.entry.next_entry, self.third_entry)
        self.assertEqual(self.third_entry.next_entry, self.second_entry)
        self.assertFalse(self.second_entry.next_entry)

    def test_previous_next_entry_in_one_query(self):
        site = Site.objects.get_current()
        self.entry.status = PUBLISHED
        self.entry.save()
        self.entry.sites.add(site)
        with self.assertNumQueries(1):
            self.assertFalse(self.entry.previous_entry)
            self.assertFalse(self.entry.next_entry)
            # Reload to check the cache
            self.assertFalse(self.entry.previous_entry)
            self.assertFalse(self.entry.next_entry)
        params = {'title': 'My second entry',
                  'content': 'My second content',
                  'slug': 'my-second-entry',
                  'creation_date': datetime(2001, 1, 1),
                  'status': PUBLISHED}
        self.second_entry = Entry.objects.create(**params)
        self.second_entry.sites.add(site)
        params = {'title': 'My third entry',
                  'content': 'My third content',
                  'slug': 'my-third-entry',
                  'creation_date': datetime(2050, 1, 1),
                  'status': PUBLISHED}
        self.third_entry = Entry.objects.create(**params)
        self.third_entry.sites.add(site)
        del self.entry.previous_next  # Invalidate the cached property
        with self.assertNumQueries(1):
            self.assertEqual(self.entry.previous_entry, self.second_entry)
            self.assertEqual(self.entry.next_entry, self.third_entry)
            # Reload to check the cache
            self.assertEqual(self.entry.previous_entry, self.second_entry)
            self.assertEqual(self.entry.next_entry, self.third_entry)

    def test_related_published(self):
        site = Site.objects.get_current()
        self.assertFalse(self.entry.related_published)
        params = {'title': 'My second entry',
                  'content': 'My second content',
                  'slug': 'my-second-entry',
                  'status': PUBLISHED}
        self.second_entry = Entry.objects.create(**params)
        self.second_entry.related.add(self.entry)
        self.assertEqual(len(self.entry.related_published), 0)

        self.second_entry.sites.add(site)
        self.assertEqual(len(self.entry.related_published), 1)
        self.assertEqual(len(self.second_entry.related_published), 0)

        self.entry.status = PUBLISHED
        self.entry.save()
        self.entry.sites.add(site)
        self.assertEqual(len(self.entry.related_published), 1)
        self.assertEqual(len(self.second_entry.related_published), 1)

    def test_tags_list(self):
        self.assertEqual(self.entry.tags_list, [])
        self.entry.tags = 'tag-1, tag-2'
        self.assertEqual(self.entry.tags_list, ['tag-1', 'tag-2'])


class EntryHtmlContentTestCase(TestCase):

    def setUp(self):
        params = {'title': 'My entry',
                  'content': 'My content',
                  'slug': 'my-entry'}
        self.entry = Entry(**params)
        self.original_rendering = entry.MARKUP_LANGUAGE

    def tearDown(self):
        entry.MARKUP_LANGUAGE = self.original_rendering

    def test_html_content_default(self):
        entry.MARKUP_LANGUAGE = None
        self.assertEqual(self.entry.html_content, '<p>My content</p>')

        self.entry.content = 'Hello world !\n' \
                             ' this is my content'
        self.assertEqual(self.entry.html_content,
                         '<p>Hello world !<br /> this is my content</p>')

    @skipUnless(is_lib_available('textile'), 'Textile is not available')
    def test_html_content_textitle(self):
        entry.MARKUP_LANGUAGE = 'textile'
        self.entry.content = 'Hello world !\n\n' \
                             'this is my content :\n\n' \
                             '* Item 1\n* Item 2'
        html_content = self.entry.html_content
        self.assertEqual(html_content,
                         '\t<p>Hello world !</p>\n\n\t'
                         '<p>this is my content :</p>\n\n\t'
                         '<ul>\n\t\t<li>Item 1</li>\n\t\t'
                         '<li>Item 2</li>\n\t</ul>')

    @skipUnless(is_lib_available('markdown'), 'Markdown is not available')
    def test_html_content_markdown(self):
        entry.MARKUP_LANGUAGE = 'markdown'
        self.entry.content = 'Hello world !\n\n' \
                             'this is my content :\n\n' \
                             '* Item 1\n* Item 2'
        html_content = self.entry.html_content
        self.assertEqual(html_content,
                         '<p>Hello world !</p>\n'
                         '<p>this is my content :</p>'
                         '\n<ul>\n<li>Item 1</li>\n'
                         '<li>Item 2</li>\n</ul>')

    @skipUnless(is_lib_available('docutils'), 'Docutils is not available')
    def test_html_content_restructuredtext(self):
        entry.MARKUP_LANGUAGE = 'restructuredtext'
        self.entry.content = 'Hello world !\n\n' \
                             'this is my content :\n\n' \
                             '* Item 1\n* Item 2'
        html_content = self.entry.html_content
        self.assertEqual(html_content,
                         '<p>Hello world !</p>\n'
                         '<p>this is my content :</p>'
                         '\n<ul class="simple">\n<li>Item 1</li>\n'
                         '<li>Item 2</li>\n</ul>\n')

    def test_html_preview(self):
        entry.MARKUP_LANGUAGE = None
        preview = self.entry.html_preview
        self.assertEqual(str(preview), '<p>My content</p>')
        self.assertEqual(preview.has_more, False)


class EntryAbsoluteUrlTestCase(TestCase):

    def check_get_absolute_url(self, creation_date, url_expected):
        params = {'title': 'My entry',
                  'content': 'My content',
                  'slug': 'my-entry',
                  'creation_date': creation_date}
        entry = Entry.objects.create(**params)
        self.assertTrue(url_expected in entry.get_absolute_url())

    @override_settings(USE_TZ=False)
    def test_get_absolute_url_no_timezone(self):
        self.check_get_absolute_url(datetime(2013, 1, 1, 12, 0),
                                    '/2013/01/01/my-entry/')
        self.check_get_absolute_url(datetime(2013, 1, 1, 23, 0),
                                    '/2013/01/01/my-entry/')

    @override_settings(USE_TZ=True, TIME_ZONE='Europe/Paris')
    def test_get_absolute_url_with_timezone(self):
        self.check_get_absolute_url(datetime(2013, 1, 1, 12, 0),
                                    '/2013/01/01/my-entry/')
        self.check_get_absolute_url(datetime(2013, 1, 1, 23, 0),
                                    '/2013/01/02/my-entry/')

########NEW FILE########
__FILENAME__ = test_feeds
"""Test cases for Zinnia's feeds"""
try:
    from urllib.parse import urljoin
except ImportError:  # Python 2
    from urlparse import urljoin

from django.test import TestCase
from django.utils import timezone
from django.contrib.sites.models import Site
from django.utils.translation import activate
from django.utils.translation import deactivate
from django.test.utils import override_settings
from django.core.files.base import ContentFile
from django.utils.feedgenerator import Atom1Feed
from django.utils.feedgenerator import DefaultFeed
from django.core.exceptions import ObjectDoesNotExist
from django.core.files.storage import default_storage
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.tests.utils import skipIfCustomUser

import django_comments as comments

from tagging.models import Tag

from zinnia.managers import HIDDEN
from zinnia.managers import PUBLISHED
from zinnia.models.entry import Entry
from zinnia.models.author import Author
from zinnia.tests.utils import datetime
from zinnia.tests.utils import urlEqual
from zinnia.models.category import Category
from zinnia.flags import PINGBACK, TRACKBACK
from zinnia import feeds
from zinnia.feeds import EntryFeed
from zinnia.feeds import ZinniaFeed
from zinnia.feeds import LatestEntries
from zinnia.feeds import CategoryEntries
from zinnia.feeds import AuthorEntries
from zinnia.feeds import TagEntries
from zinnia.feeds import SearchEntries
from zinnia.feeds import EntryDiscussions
from zinnia.feeds import EntryComments
from zinnia.feeds import EntryPingbacks
from zinnia.feeds import EntryTrackbacks
from zinnia.feeds import LatestDiscussions
from zinnia.signals import disconnect_entry_signals
from zinnia.signals import disconnect_discussion_signals


@skipIfCustomUser
class FeedsTestCase(TestCase):
    """Test cases for the Feed classes provided"""
    urls = 'zinnia.tests.implementations.urls.default'

    def setUp(self):
        disconnect_entry_signals()
        disconnect_discussion_signals()
        activate('en')
        self.site = Site.objects.get_current()
        self.author = Author.objects.create(username='admin',
                                            first_name='Root',
                                            last_name='Bloody',
                                            email='admin@example.com')
        self.category = Category.objects.create(title='Tests', slug='tests')
        self.entry_ct_id = ContentType.objects.get_for_model(Entry).pk

    def tearDown(self):
        deactivate()

    def create_published_entry(self):
        params = {'title': 'My test entry',
                  'content': 'My test content with image '
                  '<img src="/image.jpg" />',
                  'slug': 'my-test-entry',
                  'tags': 'tests',
                  'creation_date': datetime(2010, 1, 1, 12),
                  'status': PUBLISHED}
        entry = Entry.objects.create(**params)
        entry.sites.add(self.site)
        entry.categories.add(self.category)
        entry.authors.add(self.author)
        return entry

    def create_discussions(self, entry):
        comment = comments.get_model().objects.create(
            comment='My Comment',
            user=self.author,
            user_name='admin',
            content_object=entry,
            site=self.site,
            submit_date=timezone.now())
        pingback = comments.get_model().objects.create(
            comment='My Pingback',
            user=self.author,
            content_object=entry,
            site=self.site,
            submit_date=timezone.now())
        pingback.flags.create(user=self.author, flag=PINGBACK)
        trackback = comments.get_model().objects.create(
            comment='My Trackback',
            user=self.author,
            content_object=entry,
            site=self.site,
            submit_date=timezone.now())
        trackback.flags.create(user=self.author, flag=TRACKBACK)
        return [comment, pingback, trackback]

    def test_entry_feed(self):
        entry = self.create_published_entry()
        feed = EntryFeed()
        self.assertEqual(feed.item_pubdate(entry), entry.creation_date)
        self.assertEqual(feed.item_categories(entry), [self.category.title])
        self.assertEqual(feed.item_author_name(entry),
                         self.author.__str__())
        self.assertEqual(feed.item_author_email(entry), self.author.email)
        self.assertEqual(
            feed.item_author_link(entry),
            'http://example.com/authors/%s/' % self.author.username)
        # Test a NoReverseMatch for item_author_link
        self.author.username = '[]'
        self.author.save()
        feed.item_author_name(entry)
        self.assertEqual(feed.item_author_link(entry), 'http://example.com')

    def test_entry_feed_enclosure(self):
        entry = self.create_published_entry()
        feed = EntryFeed()
        self.assertEqual(
            feed.item_enclosure_url(entry), 'http://example.com/image.jpg')
        self.assertEqual(feed.item_enclosure_length(entry), '100000')
        self.assertEqual(feed.item_enclosure_mime_type(entry), 'image/jpeg')
        entry.content = 'My test content with image <img src="image.jpg" />'
        entry.save()
        self.assertEqual(
            feed.item_enclosure_url(entry), 'http://example.com/image.jpg')
        self.assertEqual(feed.item_enclosure_length(entry), '100000')
        self.assertEqual(feed.item_enclosure_mime_type(entry), 'image/jpeg')
        entry.content = 'My test content with image ' \
                        '<img src="http://test.com/image.jpg" />'
        entry.save()
        self.assertEqual(
            feed.item_enclosure_url(entry), 'http://test.com/image.jpg')
        self.assertEqual(feed.item_enclosure_length(entry), '100000')
        self.assertEqual(feed.item_enclosure_mime_type(entry), 'image/jpeg')
        path = default_storage.save('enclosure.png', ContentFile('Content'))
        entry.image = path
        entry.save()
        self.assertEqual(feed.item_enclosure_url(entry),
                         urljoin('http://example.com', entry.image.url))
        self.assertEqual(feed.item_enclosure_length(entry), '7')
        self.assertEqual(feed.item_enclosure_mime_type(entry), 'image/png')
        default_storage.delete(path)
        entry.image = 'invalid_image_without_extension'
        entry.save()
        self.assertEqual(feed.item_enclosure_url(entry),
                         urljoin('http://example.com', entry.image.url))
        self.assertEqual(feed.item_enclosure_length(entry), '100000')
        self.assertEqual(feed.item_enclosure_mime_type(entry), 'image/jpeg')

    def test_entry_feed_enclosure_issue_134(self):
        entry = self.create_published_entry()
        feed = EntryFeed()
        entry.content = 'My test content with image <img xsrc="image.jpg" />'
        entry.save()
        self.assertEqual(
            feed.item_enclosure_url(entry), None)

    def test_latest_entries(self):
        self.create_published_entry()
        feed = LatestEntries()
        self.assertEqual(feed.link(), '/')
        self.assertEqual(len(feed.items()), 1)
        self.assertEqual(feed.get_title(None), 'Latest entries')
        self.assertEqual(
            feed.description(),
            'The latest entries for the site example.com')

    def test_category_entries(self):
        self.create_published_entry()
        feed = CategoryEntries()
        self.assertEqual(feed.get_object('request', '/tests/'), self.category)
        self.assertEqual(len(feed.items(self.category)), 1)
        self.assertEqual(feed.link(self.category), '/categories/tests/')
        self.assertEqual(
            feed.get_title(self.category),
            'Entries for the category %s' % self.category.title)
        self.assertEqual(
            feed.description(self.category),
            'The latest entries for the category %s' % self.category.title)

    def test_author_entries(self):
        self.create_published_entry()
        feed = AuthorEntries()
        self.assertEqual(feed.get_object('request', 'admin'), self.author)
        self.assertEqual(len(feed.items(self.author)), 1)
        self.assertEqual(feed.link(self.author), '/authors/admin/')
        self.assertEqual(feed.get_title(self.author),
                         'Entries for author %s' %
                         self.author.__str__())
        self.assertEqual(feed.description(self.author),
                         'The latest entries by %s' %
                         self.author.__str__())

    def test_tag_entries(self):
        self.create_published_entry()
        feed = TagEntries()
        tag = Tag(name='tests')
        self.assertEqual(feed.get_object('request', 'tests').name, 'tests')
        self.assertEqual(len(feed.items('tests')), 1)
        self.assertEqual(feed.link(tag), '/tags/tests/')
        self.assertEqual(feed.get_title(tag),
                         'Entries for the tag %s' % tag.name)
        self.assertEqual(feed.description(tag),
                         'The latest entries for the tag %s' % tag.name)

    def test_search_entries(self):
        class FakeRequest:
            def __init__(self, val):
                self.GET = {'pattern': val}
        self.create_published_entry()
        feed = SearchEntries()
        self.assertRaises(ObjectDoesNotExist,
                          feed.get_object, FakeRequest('te'))
        self.assertEqual(feed.get_object(FakeRequest('test')), 'test')
        self.assertEqual(len(feed.items('test')), 1)
        self.assertEqual(feed.link('test'), '/search/?pattern=test')
        self.assertEqual(feed.get_title('test'),
                         "Results of the search for '%s'" % 'test')
        self.assertEqual(
            feed.description('test'),
            "The entries containing the pattern '%s'" % 'test')

    def test_latest_discussions(self):
        entry = self.create_published_entry()
        self.create_discussions(entry)
        feed = LatestDiscussions()
        self.assertEqual(feed.link(), '/')
        self.assertEqual(len(feed.items()), 3)
        self.assertEqual(feed.get_title(None), 'Latest discussions')
        self.assertEqual(
            feed.description(),
            'The latest discussions for the site example.com')

    def test_entry_discussions(self):
        entry = self.create_published_entry()
        comments = self.create_discussions(entry)
        feed = EntryDiscussions()
        self.assertEqual(feed.get_object(
            'request', 2010, 1, 1, entry.slug), entry)
        self.assertEqual(feed.link(entry), '/2010/01/01/my-test-entry/')
        self.assertEqual(len(feed.items(entry)), 3)
        self.assertEqual(feed.item_pubdate(comments[0]),
                         comments[0].submit_date)
        self.assertEqual(feed.item_link(comments[0]),
                         '/comments/cr/%i/%i/#c%i' %
                         (self.entry_ct_id, entry.pk, comments[0].pk))
        self.assertEqual(feed.item_author_name(comments[0]),
                         self.author.__str__())
        self.assertEqual(feed.item_author_email(comments[0]),
                         'admin@example.com')
        self.assertEqual(feed.item_author_link(comments[0]), '')
        self.assertEqual(feed.get_title(entry),
                         'Discussions on %s' % entry.title)
        self.assertEqual(
            feed.description(entry),
            'The latest discussions for the entry %s' % entry.title)

    def test_feed_for_hidden_entry_issue_277(self):
        entry = self.create_published_entry()
        entry.status = HIDDEN
        entry.save()
        feed = EntryDiscussions()
        self.assertEqual(feed.get_object(
            'request', 2010, 1, 1, entry.slug), entry)

    @override_settings(USE_TZ=False)
    def test_feed_discussions_no_timezone_issue_277(self):
        entry = self.create_published_entry()
        entry.creation_date = datetime(2014, 1, 1, 23)
        entry.save()
        feed = EntryDiscussions()
        self.assertEqual(feed.get_object(
            'request', 2014, 1, 1, entry.slug), entry)

    @override_settings(USE_TZ=True, TIME_ZONE='Europe/Paris')
    def test_feed_discussions_with_timezone_issue_277(self):
        entry = self.create_published_entry()
        entry.creation_date = datetime(2014, 1, 1, 23)
        entry.save()
        feed = EntryDiscussions()
        self.assertEqual(feed.get_object(
            'request', 2014, 1, 2, entry.slug), entry)

    def test_entry_comments(self):
        entry = self.create_published_entry()
        comments = self.create_discussions(entry)
        feed = EntryComments()
        self.assertEqual(list(feed.items(entry)), [comments[0]])
        self.assertEqual(feed.item_link(comments[0]),
                         '/comments/cr/%i/%i/#comment-%i-by-admin' %
                         (self.entry_ct_id, entry.pk, comments[0].pk))
        self.assertEqual(feed.get_title(entry),
                         'Comments on %s' % entry.title)
        self.assertEqual(
            feed.description(entry),
            'The latest comments for the entry %s' % entry.title)
        self.assertTrue(urlEqual(
            feed.item_enclosure_url(comments[0]),
            'http://www.gravatar.com/avatar/e64c7d89f26b'
            'd1972efa854d13d7dd61?s=80&amp;r=g'))
        self.assertEqual(feed.item_enclosure_length(entry), '100000')
        self.assertEqual(feed.item_enclosure_mime_type(entry), 'image/jpeg')

    def test_entry_pingbacks(self):
        entry = self.create_published_entry()
        comments = self.create_discussions(entry)
        feed = EntryPingbacks()
        self.assertEqual(list(feed.items(entry)), [comments[1]])
        self.assertEqual(feed.item_link(comments[1]),
                         '/comments/cr/%i/%i/#pingback-%i' %
                         (self.entry_ct_id, entry.pk, comments[1].pk))
        self.assertEqual(feed.get_title(entry),
                         'Pingbacks on %s' % entry.title)
        self.assertEqual(
            feed.description(entry),
            'The latest pingbacks for the entry %s' % entry.title)

    def test_entry_trackbacks(self):
        entry = self.create_published_entry()
        comments = self.create_discussions(entry)
        feed = EntryTrackbacks()
        self.assertEqual(list(feed.items(entry)), [comments[2]])
        self.assertEqual(feed.item_link(comments[2]),
                         '/comments/cr/%i/%i/#trackback-%i' %
                         (self.entry_ct_id, entry.pk, comments[2].pk))
        self.assertEqual(feed.get_title(entry),
                         'Trackbacks on %s' % entry.title)
        self.assertEqual(
            feed.description(entry),
            'The latest trackbacks for the entry %s' % entry.title)

    def test_entry_feed_no_authors(self):
        entry = self.create_published_entry()
        entry.authors.clear()
        feed = EntryFeed()
        self.assertEqual(feed.item_author_name(entry), None)

    def test_entry_feed_rss_or_atom(self):
        original_feeds_format = feeds.FEEDS_FORMAT
        feeds.FEEDS_FORMAT = ''
        feed = LatestEntries()
        self.assertEqual(feed.feed_type, DefaultFeed)
        feeds.FEEDS_FORMAT = 'atom'
        feed = LatestEntries()
        self.assertEqual(feed.feed_type, Atom1Feed)
        self.assertEqual(feed.subtitle, feed.description)
        feeds.FEEDS_FORMAT = original_feeds_format

    def test_title_with_sitename_implementation(self):
        feed = ZinniaFeed()
        self.assertRaises(NotImplementedError, feed.title)
        feed = LatestEntries()
        self.assertEqual(feed.title(), 'example.com - Latest entries')

    def test_discussion_feed_with_same_slugs(self):
        """
        https://github.com/Fantomas42/django-blog-zinnia/issues/104

        OK, Here I will reproduce the original case: getting a discussion
        type feed, with a same slug.

        The correction of this case, will need some changes in the
        get_object method.
        """
        entry = self.create_published_entry()

        feed = EntryDiscussions()
        self.assertEqual(feed.get_object(
            'request', 2010, 1, 1, entry.slug), entry)

        params = {'title': 'My test entry, part II',
                  'content': 'My content ',
                  'slug': 'my-test-entry',
                  'tags': 'tests',
                  'creation_date': datetime(2010, 2, 1, 12),
                  'status': PUBLISHED}
        entry_same_slug = Entry.objects.create(**params)
        entry_same_slug.sites.add(self.site)
        entry_same_slug.authors.add(self.author)

        self.assertEqual(feed.get_object(
            'request', 2010, 2, 1, entry_same_slug.slug), entry_same_slug)

########NEW FILE########
__FILENAME__ = test_flags
"""Test cases for Zinnia's flags"""
from django.test import TestCase
from django.contrib.auth.tests.utils import skipIfCustomUser

from zinnia import flags
from zinnia.flags import user_flagger_
from zinnia.flags import get_user_flagger


@skipIfCustomUser
class FlagsTestCase(TestCase):
    """Test cases for zinnia.flags"""

    def setUp(self):
        self.clear_user_flagger_cache()

    def clear_user_flagger_cache(self):
        try:
            del user_flagger_[()]
        except KeyError:
            pass

    def test_get_user_flagger_cache(self):
        get_user_flagger()
        with self.assertNumQueries(0):
            get_user_flagger()

    def test_get_user_flagger_does_not_exist(self):
        original_user_id = flags.COMMENT_FLAG_USER_ID
        flags.COMMENT_FLAG_USER_ID = 4242
        flagger = get_user_flagger()
        self.assertEqual(flagger.username, 'Zinnia-Flagger')
        flags.COMMENT_FLAG_USER_ID = original_user_id

    def test_get_user_flagged_does_not_exist_twice_issue_245(self):
        original_user_id = flags.COMMENT_FLAG_USER_ID
        flags.COMMENT_FLAG_USER_ID = None
        flagger = get_user_flagger()
        self.assertEqual(flagger.username, 'Zinnia-Flagger')
        self.clear_user_flagger_cache()
        flagger = get_user_flagger()
        self.assertEqual(flagger.username, 'Zinnia-Flagger')
        flags.COMMENT_FLAG_USER_ID = original_user_id

########NEW FILE########
__FILENAME__ = test_long_enough
"""Test cases for Zinnia's long_enought spam checker"""
from django.test import TestCase
from django.utils import timezone
from django.contrib.sites.models import Site
from django.contrib.auth.tests.utils import skipIfCustomUser

import django_comments as comments

from zinnia.models.entry import Entry
from zinnia.models.author import Author
from zinnia.managers import PUBLISHED
from zinnia.spam_checker.backends.long_enough import backend
from zinnia.signals import disconnect_entry_signals
from zinnia.signals import disconnect_discussion_signals


@skipIfCustomUser
class LongEnoughTestCase(TestCase):
    """Test cases for zinnia.spam_checker.long_enough"""

    def setUp(self):
        disconnect_entry_signals()
        disconnect_discussion_signals()
        self.site = Site.objects.get_current()
        self.author = Author.objects.create(username='admin',
                                            email='admin@example.com')

        params = {'title': 'My test entry',
                  'content': 'My test entry',
                  'slug': 'my-test-entry',
                  'status': PUBLISHED}
        self.entry = Entry.objects.create(**params)
        self.entry.sites.add(self.site)
        self.entry.authors.add(self.author)

    def test_long_enough(self):
        comment = comments.get_model().objects.create(
            comment='My Comment', user=self.author, is_public=True,
            content_object=self.entry, site=self.site,
            submit_date=timezone.now())
        self.assertEqual(backend(comment, self.entry, {}), True)

        comment.comment = 'Hello I just wanted to thank for great article'
        comment.save()
        self.assertEqual(backend(comment, self.entry, {}), False)

########NEW FILE########
__FILENAME__ = test_managers
"""Test cases for Zinnia's managers"""
from django.test import TestCase
from django.contrib.sites.models import Site
from django.contrib.auth.tests.utils import skipIfCustomUser

from tagging.models import Tag

from zinnia.models.entry import Entry
from zinnia.models.author import Author
from zinnia.models.category import Category
from zinnia.tests.utils import datetime
from zinnia.managers import PUBLISHED
from zinnia.managers import tags_published
from zinnia.managers import entries_published
from zinnia.signals import disconnect_entry_signals


@skipIfCustomUser
class ManagersTestCase(TestCase):

    def setUp(self):
        disconnect_entry_signals()
        self.sites = [
            Site.objects.get_current(),
            Site.objects.create(domain='http://domain.com',
                                name='Domain.com')]
        self.authors = [
            Author.objects.create_user(username='webmaster',
                                       email='webmaster@example.com'),
            Author.objects.create_user(username='contributor',
                                       email='contributor@example.com')]
        self.categories = [
            Category.objects.create(title='Category 1',
                                    slug='category-1'),
            Category.objects.create(title='Category 2',
                                    slug='category-2')]

        params = {'title': 'My entry 1', 'content': 'My content 1',
                  'tags': 'zinnia, test', 'slug': 'my-entry-1',
                  'status': PUBLISHED}
        self.entry_1 = Entry.objects.create(**params)
        self.entry_1.authors.add(self.authors[0])
        self.entry_1.categories.add(*self.categories)
        self.entry_1.sites.add(*self.sites)

        params = {'title': 'My entry 2', 'content': 'My content 2',
                  'tags': 'zinnia, test', 'slug': 'my-entry-2'}
        self.entry_2 = Entry.objects.create(**params)
        self.entry_2.authors.add(*self.authors)
        self.entry_2.categories.add(self.categories[0])
        self.entry_2.sites.add(self.sites[0])

    def test_tags_published(self):
        self.assertEqual(tags_published().count(), Tag.objects.count())
        Tag.objects.create(name='out')
        self.assertNotEqual(tags_published().count(), Tag.objects.count())

    def test_author_published_manager_get_query_set(self):
        self.assertEqual(Author.published.count(), 1)
        self.entry_2.status = PUBLISHED
        self.entry_2.save()
        self.assertEqual(Author.published.count(), 2)
        self.entry_2.sites.remove(self.sites[0])
        self.entry_2.sites.add(self.sites[1])
        self.assertEqual(Author.published.count(), 1)

    def test_category_published_manager_get_query_set(self):
        category = Category.objects.create(
            title='Third Category', slug='third-category')
        self.assertEqual(Category.published.count(), 2)
        self.entry_2.categories.add(category)
        self.entry_2.status = PUBLISHED
        self.entry_2.save()
        self.assertEqual(Category.published.count(), 3)

    def test_entries_published(self):
        self.assertEqual(entries_published(Entry.objects.all()).count(), 1)
        self.entry_2.status = PUBLISHED
        self.entry_2.save()
        self.assertEqual(entries_published(Entry.objects.all()).count(), 2)
        self.entry_1.sites.clear()
        self.assertEqual(entries_published(Entry.objects.all()).count(), 1)
        self.entry_1.sites.add(*self.sites)
        self.entry_1.start_publication = datetime(2020, 1, 1)
        self.entry_1.save()
        self.assertEqual(entries_published(Entry.objects.all()).count(), 1)
        self.entry_1.start_publication = datetime(2000, 1, 1)
        self.entry_1.save()
        self.assertEqual(entries_published(Entry.objects.all()).count(), 2)
        self.entry_1.end_publication = datetime(2000, 1, 1)
        self.entry_1.save()
        self.assertEqual(entries_published(Entry.objects.all()).count(), 1)
        self.entry_1.end_publication = datetime(2020, 1, 1)
        self.entry_1.save()
        self.assertEqual(entries_published(Entry.objects.all()).count(), 2)

    def test_entry_published_manager_get_query_set(self):
        self.assertEqual(Entry.published.count(), 1)
        self.entry_2.status = PUBLISHED
        self.entry_2.save()
        self.assertEqual(Entry.published.count(), 2)
        self.entry_1.sites.clear()
        self.assertEqual(Entry.published.count(), 1)
        self.entry_1.sites.add(*self.sites)
        self.entry_1.start_publication = datetime(2020, 1, 1)
        self.entry_1.save()
        self.assertEqual(Entry.published.count(), 1)
        self.entry_1.start_publication = datetime(2000, 1, 1)
        self.entry_1.save()
        self.assertEqual(Entry.published.count(), 2)
        self.entry_1.end_publication = datetime(2000, 1, 1)
        self.entry_1.save()
        self.assertEqual(Entry.published.count(), 1)
        self.entry_1.end_publication = datetime(2020, 1, 1)
        self.entry_1.save()
        self.assertEqual(Entry.published.count(), 2)

    def test_entry_published_manager_on_site(self):
        self.assertEqual(Entry.published.on_site().count(), 2)
        self.entry_2.sites.clear()
        self.entry_2.sites.add(self.sites[1])
        self.assertEqual(Entry.published.on_site().count(), 1)
        self.entry_1.sites.clear()
        self.assertEqual(Entry.published.on_site().count(), 0)

    def test_entry_published_manager_basic_search(self):
        self.assertEqual(Entry.published.basic_search('My ').count(), 1)
        self.entry_2.status = PUBLISHED
        self.entry_2.save()
        self.assertEqual(Entry.published.basic_search('My ').count(), 2)
        self.assertEqual(Entry.published.basic_search('1').count(), 1)
        self.assertEqual(Entry.published.basic_search('content 1').count(), 2)

    def test_entry_published_manager_advanced_search(self):
        category = Category.objects.create(
            title='SimpleCategory', slug='simple')
        self.entry_2.categories.add(category)
        self.entry_2.tags = self.entry_2.tags + ', custom'
        self.entry_2.status = PUBLISHED
        self.entry_2.save()
        self.assertEqual(
            Entry.published.advanced_search('content').count(), 2)
        search = Entry.published.advanced_search('content 1')
        self.assertEqual(search.count(), 1)
        self.assertEqual(search.all()[0], self.entry_1)
        self.assertEqual(
            Entry.published.advanced_search('content 1 or 2').count(), 2)
        self.assertEqual(
            Entry.published.advanced_search('content 1 and 2').count(), 0)
        self.assertEqual(
            Entry.published.advanced_search('content 1 2').count(), 0)
        self.assertEqual(
            Entry.published.advanced_search('"My content" 1 or 2').count(), 2)
        self.assertEqual(
            Entry.published.advanced_search('-"My content" 2').count(), 0)
        search = Entry.published.advanced_search('content -1')
        self.assertEqual(search.count(), 1)
        self.assertEqual(search.all()[0], self.entry_2)
        self.assertEqual(Entry.published.advanced_search(
            'content category:SimpleCategory').count(), 1)
        self.assertEqual(Entry.published.advanced_search(
            'content category:simple').count(), 1)
        self.assertEqual(Entry.published.advanced_search(
            'content category:"Category 1"').count(), 2)
        self.assertEqual(Entry.published.advanced_search(
            'content category:"category-1"').count(), 2)
        self.assertEqual(Entry.published.advanced_search(
            'content category:"category-2"').count(), 1)
        self.assertEqual(Entry.published.advanced_search(
            'content tag:zinnia').count(), 2)
        self.assertEqual(Entry.published.advanced_search(
            'content tag:custom').count(), 1)
        self.assertEqual(Entry.published.advanced_search(
            'content author:webmaster').count(), 2)
        self.assertEqual(Entry.published.advanced_search(
            'content author:contributor').count(), 1)
        self.assertEqual(Entry.published.advanced_search(
            'content author:webmaster tag:zinnia').count(), 2)
        self.assertEqual(Entry.published.advanced_search(
            'content author:webmaster tag:custom').count(), 1)
        self.assertEqual(Entry.published.advanced_search(
            'content 1 or 2 author:webmaster').count(), 2)
        self.assertEqual(Entry.published.advanced_search(
            'content 1 or 2 author:webmaster').count(), 2)
        self.assertEqual(Entry.published.advanced_search(
            '(author:webmaster content) my').count(), 2)
        self.assertEqual(Entry.published.advanced_search(
            '(author:webmaster) or (author:contributor)').count(), 2)
        self.assertEqual(Entry.published.advanced_search(
            '(author:webmaster) (author:contributor)').count(), 0)
        self.assertEqual(Entry.published.advanced_search(
            '(author:webmaster content) 1').count(), 1)
        self.assertEqual(Entry.published.advanced_search(
            '(author:webmaster content) or 2').count(), 2)
        self.assertEqual(Entry.published.advanced_search(
            '(author:contributor content) or 1').count(), 2)
        self.assertEqual(Entry.published.advanced_search(
            '(author:contributor content) or 2').count(), 1)
        self.assertEqual(Entry.published.advanced_search(
            '(author:webmaster or ("hello world")) and 2').count(), 1)

        # Complex queries
        self.assertEqual(Entry.published.advanced_search(
            '(author:admin and "content 1") or author:webmaster').count(), 2)
        self.assertEqual(Entry.published.advanced_search(
            'author:admin and ("content 1" or author:webmaster)').count(), 0)
        self.assertEqual(Entry.published.advanced_search(
            'author:admin and "content 1" or author:webmaster').count(), 0)
        self.assertEqual(Entry.published.advanced_search(
            '-(author:webmaster and "content 1")').count(), 1)
        self.assertEqual(Entry.published.advanced_search(
            '-(-author:webmaster and "content 1")').count(), 2)
        self.assertEqual(Entry.published.advanced_search(
            'category:"category -1" or author:"web master"').count(), 0)
        self.assertEqual(Entry.published.advanced_search(
            'category:"category-1" or author:"webmaster"').count(), 2)

        # Wildcards
        self.assertEqual(Entry.published.advanced_search(
            'author:webm*').count(), 2)
        self.assertEqual(Entry.published.advanced_search(
            'author:*bmas*').count(), 2)
        self.assertEqual(Entry.published.advanced_search(
            'author:*master').count(), 2)
        self.assertEqual(Entry.published.advanced_search(
            'author:*master category:*ory-2').count(), 1)
        self.assertEqual(Entry.published.advanced_search(
            'author:*master or category:cate*').count(), 2)
        self.assertEqual(Entry.published.advanced_search(
            'category:*ate*').count(), 2)
        self.assertEqual(Entry.published.advanced_search(
            'author:"webmast*"').count(), 0)
        self.assertEqual(Entry.published.advanced_search(
            'tag:"zinnia*"').count(), 0)
        self.assertEqual(Entry.published.advanced_search(
            'tag:*inni*').count(), 2)

    def test_entry_published_manager_advanced_search_with_punctuation(self):
        self.entry_2.content = 'How are you today ? Fine thank you ! OK.'
        self.entry_2.status = PUBLISHED
        self.entry_2.save()
        self.assertEqual(Entry.published.advanced_search(
            'today ?').count(), 1)
        self.assertEqual(Entry.published.advanced_search(
            'today or ! or .').count(), 1)
        self.assertEqual(Entry.published.advanced_search(
            '"you today ?"').count(), 1)

    def test_entry_published_manager_search(self):
        self.entry_2.content = self.entry_2.content + ' * '
        self.entry_2.status = PUBLISHED
        self.entry_2.save()
        # Be sure that basic_search does not return
        # the same results of advanced_search
        self.assertNotEqual(
            Entry.published.basic_search('content 1').count(),
            Entry.published.advanced_search('content 1').count())
        # Now check the fallback with the '*' pattern
        # which will fails advanced search
        self.assertEqual(Entry.published.search('*').count(), 1)

########NEW FILE########
__FILENAME__ = test_markups
"""Test cases for Zinnia's markups"""
import sys
try:
    import builtins
except ImportError:  # Python 2
    import __builtin__ as builtins
import warnings

from django.test import TestCase
from django.utils.unittest import skipUnless

from zinnia.markups import textile
from zinnia.markups import markdown
from zinnia.markups import restructuredtext
from zinnia.tests.utils import is_lib_available


class MarkupsTestCase(TestCase):
    text = 'Hello *World* !'

    @skipUnless(is_lib_available('textile'), 'Textile is not available')
    def test_textile(self):
        self.assertEqual(textile(self.text).strip(),
                         '<p>Hello <strong>World</strong> !</p>')

    @skipUnless(is_lib_available('markdown'), 'Markdown is not available')
    def test_markdown(self):
        self.assertEqual(markdown(self.text).strip(),
                         '<p>Hello <em>World</em> !</p>')

    @skipUnless(is_lib_available('markdown'), 'Markdown is not available')
    def test_markdown_extensions(self):
        text = '[TOC]\n\n# Header 1\n\n## Header 2'
        self.assertEqual(markdown(text).strip(),
                         '<p>[TOC]</p>\n<h1>Header 1</h1>'
                         '\n<h2>Header 2</h2>')
        self.assertEqual(markdown(text, extensions='toc').strip(),
                         '<div class="toc">\n<ul>\n<li><a href="#header-1">'
                         'Header 1</a><ul>\n<li><a href="#header-2">'
                         'Header 2</a></li>\n</ul>\n</li>\n</ul>\n</div>'
                         '\n<h1 id="header-1">Header 1</h1>\n'
                         '<h2 id="header-2">Header 2</h2>')

    @skipUnless(is_lib_available('docutils'), 'Docutils is not available')
    def test_restructuredtext(self):
        self.assertEqual(restructuredtext(self.text).strip(),
                         '<p>Hello <em>World</em> !</p>')

    @skipUnless(is_lib_available('docutils'), 'Docutils is not available')
    def test_restructuredtext_settings_override(self):
        text = 'My email is toto@example.com'
        self.assertEqual(restructuredtext(text).strip(),
                         '<p>My email is <a class="reference external" '
                         'href="mailto:toto&#64;example.com">'
                         'toto&#64;example.com</a></p>')
        self.assertEqual(
            restructuredtext(text, {'cloak_email_addresses': True}).strip(),
            '<p>My email is <a class="reference external" '
            'href="mailto:toto&#37;&#52;&#48;example&#46;com">'
            'toto<span>&#64;</span>example<span>&#46;</span>com</a></p>')


@skipUnless(sys.version_info >= (2, 7, 0),
            'Cannot run these tests under Python 2.7')
class MarkupFailImportTestCase(TestCase):
    exclude_list = ['textile', 'markdown', 'docutils']

    def setUp(self):
        self.original_import = builtins.__import__
        builtins.__import__ = self.import_hook

    def tearDown(self):
        builtins.__import__ = self.original_import

    def import_hook(self, name, *args, **kwargs):
        if name in self.exclude_list:
            raise ImportError('%s module has been disabled' % name)
        else:
            self.original_import(name, *args, **kwargs)

    def test_textile(self):
        with warnings.catch_warnings(record=True) as w:
            result = textile('My *text*')
        self.tearDown()
        self.assertEqual(result, 'My *text*')
        self.assertTrue(issubclass(w[-1].category, RuntimeWarning))
        self.assertEqual(
            str(w[-1].message),
            "The Python textile library isn't installed.")

    def test_markdown(self):
        with warnings.catch_warnings(record=True) as w:
            result = markdown('My *text*')
        self.tearDown()
        self.assertEqual(result, 'My *text*')
        self.assertTrue(issubclass(w[-1].category, RuntimeWarning))
        self.assertEqual(
            str(w[-1].message),
            "The Python markdown library isn't installed.")

    def test_restructuredtext(self):
        with warnings.catch_warnings(record=True) as w:
            result = restructuredtext('My *text*')
        self.tearDown()
        self.assertEqual(result, 'My *text*')
        self.assertTrue(issubclass(w[-1].category, RuntimeWarning))
        self.assertEqual(
            str(w[-1].message),
            "The Python docutils library isn't installed.")

########NEW FILE########
__FILENAME__ = test_metaweblog
"""Test cases for Zinnia's MetaWeblog API"""
try:
    from xmlrpc.client import Binary
    from xmlrpc.client import Fault
    from xmlrpc.client import ServerProxy
except ImportError:  # Python 2
    from xmlrpclib import Binary
    from xmlrpclib import Fault
    from xmlrpclib import ServerProxy
from tempfile import TemporaryFile

from django.test import TestCase
from django.contrib.sites.models import Site
from django.core.files.storage import default_storage
from django.contrib.auth.tests.utils import skipIfCustomUser

from tagging.models import Tag

from zinnia.models.entry import Entry
from zinnia.models.author import Author
from zinnia.models.category import Category
from zinnia.managers import DRAFT
from zinnia.managers import PUBLISHED
from zinnia.settings import UPLOAD_TO
from zinnia.tests.utils import datetime
from zinnia.xmlrpc.metaweblog import authenticate
from zinnia.xmlrpc.metaweblog import post_structure
from zinnia.tests.utils import TestTransport
from zinnia.signals import disconnect_entry_signals


@skipIfCustomUser
class MetaWeblogTestCase(TestCase):
    """Test cases for MetaWeblog"""
    urls = 'zinnia.tests.implementations.urls.default'

    def setUp(self):
        disconnect_entry_signals()
        # Create data
        self.webmaster = Author.objects.create_superuser(
            username='webmaster',
            email='webmaster@example.com',
            password='password')
        self.contributor = Author.objects.create_user(
            username='contributor',
            email='contributor@example.com',
            password='password')
        self.site = Site.objects.get_current()
        self.categories = [
            Category.objects.create(title='Category 1',
                                    slug='category-1'),
            Category.objects.create(title='Category 2',
                                    slug='category-2')]
        params = {'title': 'My entry 1', 'content': 'My content 1',
                  'tags': 'zinnia, test', 'slug': 'my-entry-1',
                  'creation_date': datetime(2010, 1, 1, 12),
                  'status': PUBLISHED}
        self.entry_1 = Entry.objects.create(**params)
        self.entry_1.authors.add(self.webmaster)
        self.entry_1.categories.add(*self.categories)
        self.entry_1.sites.add(self.site)

        params = {'title': 'My entry 2', 'content': 'My content 2',
                  'creation_date': datetime(2010, 3, 15),
                  'tags': 'zinnia, test', 'slug': 'my-entry-2'}
        self.entry_2 = Entry.objects.create(**params)
        self.entry_2.authors.add(self.webmaster)
        self.entry_2.categories.add(self.categories[0])
        self.entry_2.sites.add(self.site)
        # Instanciating the server proxy
        self.server = ServerProxy('http://localhost:8000/xmlrpc/',
                                  transport=TestTransport())

    def test_authenticate(self):
        self.assertRaises(Fault, authenticate, 'badcontributor', 'badpassword')
        self.assertRaises(Fault, authenticate, 'contributor', 'badpassword')
        self.assertRaises(Fault, authenticate, 'contributor', 'password')
        self.contributor.is_staff = True
        self.contributor.save()
        self.assertEqual(authenticate('contributor', 'password'),
                         self.contributor)
        self.assertRaises(Fault, authenticate, 'contributor',
                          'password', 'zinnia.change_entry')
        self.assertEqual(authenticate('webmaster', 'password'),
                         self.webmaster)
        self.assertEqual(authenticate('webmaster', 'password',
                                      'zinnia.change_entry'),
                         self.webmaster)

    def test_get_users_blogs(self):
        self.assertRaises(Fault, self.server.blogger.getUsersBlogs,
                          'apikey', 'contributor', 'password')
        self.assertEqual(
            self.server.blogger.getUsersBlogs(
                'apikey', 'webmaster', 'password'),
            [{'url': 'http://example.com/',
              'blogid': 1,
              'blogName': 'example.com'}])

    def test_get_user_info(self):
        self.assertRaises(Fault, self.server.blogger.getUserInfo,
                          'apikey', 'contributor', 'password')
        self.webmaster.first_name = 'John'
        self.webmaster.save()
        self.assertEqual(self.server.blogger.getUserInfo(
            'apikey', 'webmaster', 'password'),
            {'firstname': 'John', 'lastname': '',
             'url': 'http://example.com/authors/webmaster/',
             'userid': self.webmaster.pk,
             'nickname': 'webmaster',
             'email': 'webmaster@example.com'})

        self.webmaster.last_name = 'Doe'
        self.webmaster.save()
        self.assertEqual(self.server.blogger.getUserInfo(
            'apikey', 'webmaster', 'password'),
            {'firstname': 'John', 'lastname': 'Doe',
             'url': 'http://example.com/authors/webmaster/',
             'userid': self.webmaster.pk,
             'nickname': 'webmaster',
             'email': 'webmaster@example.com'})

    def test_get_authors(self):
        self.assertRaises(Fault, self.server.wp.getAuthors,
                          'apikey', 'contributor', 'password')
        self.assertEqual(
            self.server.wp.getAuthors(
                'apikey', 'webmaster', 'password'),
            [{'user_login': 'webmaster',
              'user_id': self.webmaster.pk,
              'user_email': 'webmaster@example.com',
              'display_name': 'webmaster'}])

    def test_get_tags(self):
        self.assertRaises(Fault, self.server.wp.getTags,
                          1, 'contributor', 'password')
        self.assertEqual(
            self.server.wp.getTags('apikey', 'webmaster', 'password'),
            [{'count': 1,
              'html_url': 'http://example.com/tags/test/',
              'name': 'test',
              'rss_url': 'http://example.com/feeds/tags/test/',
              'slug': 'test',
              'tag_id': Tag.objects.get(name='test').pk},
             {'count': 1,
              'html_url': 'http://example.com/tags/zinnia/',
              'name': 'zinnia',
              'rss_url': 'http://example.com/feeds/tags/zinnia/',
              'slug': 'zinnia',
              'tag_id': Tag.objects.get(name='zinnia').pk}])

    def test_get_categories(self):
        self.assertRaises(Fault, self.server.metaWeblog.getCategories,
                          1, 'contributor', 'password')
        self.assertEqual(
            self.server.metaWeblog.getCategories('apikey',
                                                 'webmaster', 'password'),
            [{'rssUrl': 'http://example.com/feeds/categories/category-1/',
              'description': 'Category 1',
              'htmlUrl': 'http://example.com/categories/category-1/',
              'categoryId': self.categories[0].pk, 'parentId': 0,
              'categoryName': 'Category 1',
              'categoryDescription': ''},
             {'rssUrl': 'http://example.com/feeds/categories/category-2/',
              'description': 'Category 2',
              'htmlUrl': 'http://example.com/categories/category-2/',
              'categoryId': self.categories[1].pk, 'parentId': 0,
              'categoryName': 'Category 2',
              'categoryDescription': ''}])
        self.categories[1].parent = self.categories[0]
        self.categories[1].description = 'category 2 description'
        self.categories[1].save()
        self.assertEqual(
            self.server.metaWeblog.getCategories('apikey',
                                                 'webmaster', 'password'),
            [{'rssUrl': 'http://example.com/feeds/categories/category-1/',
              'description': 'Category 1',
              'htmlUrl': 'http://example.com/categories/category-1/',
              'categoryId': self.categories[0].pk, 'parentId': 0,
              'categoryName': 'Category 1',
              'categoryDescription': ''},
             {'rssUrl':
              'http://example.com/feeds/categories/category-1/category-2/',
              'description': 'Category 2',
              'htmlUrl':
              'http://example.com/categories/category-1/category-2/',
              'categoryId': self.categories[1].pk,
              'parentId': self.categories[0].pk,
              'categoryName': 'Category 2',
              'categoryDescription': 'category 2 description'}])

    def test_new_category(self):
        category_struct = {'name': 'Category 3', 'slug': 'category-3',
                           'description': 'Category 3 description',
                           'parent_id': self.categories[0].pk}
        self.assertRaises(Fault, self.server.wp.newCategory,
                          1, 'contributor', 'password', category_struct)
        self.assertEqual(Category.objects.count(), 2)
        new_category_id = self.server.wp.newCategory(
            1, 'webmaster', 'password', category_struct)
        self.assertEqual(Category.objects.count(), 3)
        category = Category.objects.get(pk=new_category_id)
        self.assertEqual(category.title, 'Category 3')
        self.assertEqual(category.description, 'Category 3 description')
        self.assertEqual(category.slug, 'category-3')
        self.assertEqual(category.parent, self.categories[0])

    def test_get_recent_posts(self):
        self.assertRaises(Fault, self.server.metaWeblog.getRecentPosts,
                          1, 'contributor', 'password', 10)
        self.assertEqual(len(self.server.metaWeblog.getRecentPosts(
            1, 'webmaster', 'password', 10)), 2)

    def test_delete_post(self):
        self.assertRaises(Fault, self.server.blogger.deletePost,
                          'apikey', 1, 'contributor', 'password', 'publish')
        self.assertEqual(Entry.objects.count(), 2)
        self.assertTrue(
            self.server.blogger.deletePost(
                'apikey', self.entry_1.pk, 'webmaster', 'password', 'publish'))
        self.assertEqual(Entry.objects.count(), 1)

    def test_get_post(self):
        self.assertRaises(Fault, self.server.metaWeblog.getPost,
                          1, 'contributor', 'password')
        post = self.server.metaWeblog.getPost(
            self.entry_1.pk, 'webmaster', 'password')
        self.assertEqual(post['title'], self.entry_1.title)
        self.assertEqual(post['description'], '<p>My content 1</p>')
        self.assertEqual(post['categories'], ['Category 1', 'Category 2'])
        self.assertTrue('2010-01-01T12:00:00' in post['dateCreated'].value)
        self.assertEqual(post['link'],
                         'http://example.com/2010/01/01/my-entry-1/')
        self.assertEqual(post['permaLink'],
                         'http://example.com/2010/01/01/my-entry-1/')
        self.assertEqual(post['postid'], self.entry_1.pk)
        self.assertEqual(post['userid'], 'webmaster')
        self.assertEqual(post['mt_excerpt'], '')
        self.assertEqual(post['mt_allow_comments'], 1)
        self.assertEqual(post['mt_allow_pings'], 1)
        self.assertEqual(post['mt_keywords'], self.entry_1.tags)
        self.assertEqual(post['wp_author'], 'webmaster')
        self.assertEqual(post['wp_author_id'], self.webmaster.pk)
        self.assertEqual(post['wp_author_display_name'], 'webmaster')
        self.assertEqual(post['wp_password'], '')
        self.assertEqual(post['wp_slug'], self.entry_1.slug)

    def test_new_post(self):
        post = post_structure(self.entry_2, self.site)
        self.assertRaises(Fault, self.server.metaWeblog.newPost,
                          1, 'contributor', 'password', post, 1)
        self.assertEqual(Entry.objects.count(), 2)
        self.assertEqual(Entry.published.count(), 1)
        self.server.metaWeblog.newPost(
            1, 'webmaster', 'password', post, 1)
        self.assertEqual(Entry.objects.count(), 3)
        self.assertEqual(Entry.published.count(), 2)
        del post['dateCreated']
        post['wp_author_id'] = self.contributor.pk
        self.server.metaWeblog.newPost(
            1, 'webmaster', 'password', post, 0)
        self.assertEqual(Entry.objects.count(), 4)
        self.assertEqual(Entry.published.count(), 2)

    def test_edit_post(self):
        post = post_structure(self.entry_2, self.site)
        self.assertRaises(Fault, self.server.metaWeblog.editPost,
                          1, 'contributor', 'password', post, 1)
        new_post_id = self.server.metaWeblog.newPost(
            1, 'webmaster', 'password', post, 0)

        entry = Entry.objects.get(pk=new_post_id)
        self.assertEqual(entry.title, self.entry_2.title)
        self.assertEqual(entry.content, self.entry_2.html_content)
        self.assertEqual(entry.excerpt, self.entry_2.excerpt)
        self.assertEqual(entry.slug, self.entry_2.slug)
        self.assertEqual(entry.status, DRAFT)
        self.assertEqual(entry.password, self.entry_2.password)
        self.assertEqual(entry.comment_enabled, True)
        self.assertEqual(entry.pingback_enabled, True)
        self.assertEqual(entry.categories.count(), 1)
        self.assertEqual(entry.authors.count(), 1)
        self.assertEqual(entry.authors.all()[0], self.webmaster)
        self.assertEqual(entry.creation_date, self.entry_2.creation_date)

        entry.title = 'Title edited'
        entry.creation_date = datetime(2000, 1, 1)
        post = post_structure(entry, self.site)
        post['categories'] = ''
        post['description'] = 'Content edited'
        post['mt_excerpt'] = 'Content edited'
        post['wp_slug'] = 'slug-edited'
        post['wp_password'] = 'password'
        post['mt_allow_comments'] = 2
        post['mt_allow_pings'] = 0

        response = self.server.metaWeblog.editPost(
            new_post_id, 'webmaster', 'password', post, 1)
        self.assertEqual(response, True)
        entry = Entry.objects.get(pk=new_post_id)
        self.assertEqual(entry.title, post['title'])
        self.assertEqual(entry.content, post['description'])
        self.assertEqual(entry.excerpt, post['mt_excerpt'])
        self.assertEqual(entry.slug, 'slug-edited')
        self.assertEqual(entry.status, PUBLISHED)
        self.assertEqual(entry.password, 'password')
        self.assertEqual(entry.comment_enabled, False)
        self.assertEqual(entry.pingback_enabled, False)
        self.assertEqual(entry.categories.count(), 0)
        self.assertEqual(entry.creation_date, datetime(2000, 1, 1))

        del post['dateCreated']
        post['wp_author_id'] = self.contributor.pk

        response = self.server.metaWeblog.editPost(
            new_post_id, 'webmaster', 'password', post, 1)
        entry = Entry.objects.get(pk=new_post_id)
        self.assertEqual(entry.authors.count(), 1)
        self.assertEqual(entry.authors.all()[0], self.contributor)
        self.assertEqual(entry.creation_date, datetime(2000, 1, 1))

    def test_new_media_object(self):
        file_ = TemporaryFile()
        file_.write('My test content'.encode('utf-8'))
        file_.seek(0)
        media = {'name': 'zinnia_test_file.txt',
                 'type': 'text/plain',
                 'bits': Binary(file_.read())}
        file_.close()

        self.assertRaises(Fault, self.server.metaWeblog.newMediaObject,
                          1, 'contributor', 'password', media)
        new_media = self.server.metaWeblog.newMediaObject(
            1, 'webmaster', 'password', media)
        self.assertTrue('/zinnia_test_file' in new_media['url'])
        default_storage.delete('/'.join([
            UPLOAD_TO, new_media['url'].split('/')[-1]]))

########NEW FILE########
__FILENAME__ = test_mixins
"""Test cases for Zinnia's mixins"""
from datetime import date

from django.test import TestCase
from django.contrib.sites.models import Site
from django.core.exceptions import ImproperlyConfigured
from django.contrib.auth.tests.utils import skipIfCustomUser

from zinnia.models.entry import Entry
from zinnia.models.author import Author
from zinnia.models.category import Category
from zinnia.managers import PUBLISHED
from zinnia.tests.utils import datetime
from zinnia.signals import disconnect_entry_signals
from zinnia.views.mixins.archives import PreviousNextPublishedMixin
from zinnia.views.mixins.callable_queryset import CallableQuerysetMixin
from zinnia.views.mixins.prefetch_related import PrefetchRelatedMixin
from zinnia.views.mixins.prefetch_related import PrefetchCategoriesAuthorsMixin
from zinnia.views.mixins.templates import EntryQuerysetTemplateResponseMixin
from zinnia.views.mixins.templates import EntryArchiveTemplateResponseMixin
from zinnia.views.mixins.templates import \
    EntryQuerysetArchiveTemplateResponseMixin


class MixinTestCase(TestCase):
    """Test cases for zinnia.views.mixins"""

    def setUp(self):
        disconnect_entry_signals()

    def test_callable_queryset_mixin(self):
        instance = CallableQuerysetMixin()
        self.assertRaises(ImproperlyConfigured,
                          instance.get_queryset)

        def qs():
            return []

        instance.queryset = qs
        self.assertEqual(instance.get_queryset(),
                         [])

    def test_entry_queryset_template_response_mixin(self):
        instance = EntryQuerysetTemplateResponseMixin()
        self.assertRaises(ImproperlyConfigured,
                          instance.get_model_type)
        self.assertRaises(ImproperlyConfigured,
                          instance.get_model_name)
        instance.model_type = 'model'
        instance.model_name = 'name'
        self.assertEqual(instance.get_model_type(),
                         'model')
        self.assertEqual(instance.get_model_name(),
                         'name')
        self.assertEqual(instance.get_template_names(),
                         ['zinnia/model/name/entry_list.html',
                          'zinnia/model/name_entry_list.html',
                          'zinnia/model/entry_list.html',
                          'zinnia/entry_list.html'])
        instance.template_name = 'zinnia/entry_search.html'
        self.assertEqual(instance.get_template_names(),
                         ['zinnia/entry_search.html',
                          'zinnia/model/name/entry_list.html',
                          'zinnia/model/name_entry_list.html',
                          'zinnia/model/entry_list.html',
                          'zinnia/entry_list.html'])

    def test_entry_queryset_archive_template_response_mixin(self):
        get_year = lambda: 2012
        get_week = lambda: 16
        get_month = lambda: '04'
        get_day = lambda: 21
        instance = EntryQuerysetArchiveTemplateResponseMixin()
        self.assertEqual(
            instance.get_template_names(),
            ['zinnia/archives/entry_archive.html',
             'zinnia/entry_archive.html',
             'entry_archive.html'])
        instance.get_year = get_year
        self.assertEqual(
            instance.get_template_names(),
            ['zinnia/archives/2012/entry_archive.html',
             'zinnia/archives/entry_archive.html',
             'zinnia/entry_archive.html',
             'entry_archive.html'])
        instance.get_week = get_week
        self.assertEqual(
            instance.get_template_names(),
            ['zinnia/archives/2012/week/16/entry_archive.html',
             'zinnia/archives/week/16/entry_archive.html',
             'zinnia/archives/2012/entry_archive.html',
             'zinnia/archives/entry_archive.html',
             'zinnia/entry_archive.html',
             'entry_archive.html'])
        instance.get_month = get_month
        self.assertEqual(
            instance.get_template_names(),
            ['zinnia/archives/2012/month/04/entry_archive.html',
             'zinnia/archives/month/04/entry_archive.html',
             'zinnia/archives/2012/week/16/entry_archive.html',
             'zinnia/archives/week/16/entry_archive.html',
             'zinnia/archives/2012/entry_archive.html',
             'zinnia/archives/entry_archive.html',
             'zinnia/entry_archive.html',
             'entry_archive.html'])
        instance.get_day = get_day
        self.assertEqual(
            instance.get_template_names(),
            ['zinnia/archives/2012/04/21/entry_archive.html',
             'zinnia/archives/month/04/day/21/entry_archive.html',
             'zinnia/archives/2012/day/21/entry_archive.html',
             'zinnia/archives/day/21/entry_archive.html',
             'zinnia/archives/2012/month/04/entry_archive.html',
             'zinnia/archives/month/04/entry_archive.html',
             'zinnia/archives/2012/week/16/entry_archive.html',
             'zinnia/archives/week/16/entry_archive.html',
             'zinnia/archives/2012/entry_archive.html',
             'zinnia/archives/entry_archive.html',
             'zinnia/entry_archive.html',
             'entry_archive.html'])

        instance.template_name = 'zinnia/entry_search.html'
        self.assertEqual(
            instance.get_template_names(),
            ['zinnia/entry_search.html',
             'zinnia/archives/2012/04/21/entry_archive.html',
             'zinnia/archives/month/04/day/21/entry_archive.html',
             'zinnia/archives/2012/day/21/entry_archive.html',
             'zinnia/archives/day/21/entry_archive.html',
             'zinnia/archives/2012/month/04/entry_archive.html',
             'zinnia/archives/month/04/entry_archive.html',
             'zinnia/archives/2012/week/16/entry_archive.html',
             'zinnia/archives/week/16/entry_archive.html',
             'zinnia/archives/2012/entry_archive.html',
             'zinnia/archives/entry_archive.html',
             'zinnia/entry_archive.html',
             'entry_archive.html'])

    def test_entry_archive_template_response_mixin(self):
        class FakeEntry(object):
            detail_template = 'entry_detail.html'
            slug = 'my-fake-entry'

        get_year = lambda: 2012
        get_month = lambda: '04'
        get_day = lambda: 21

        instance = EntryArchiveTemplateResponseMixin()
        instance.get_year = get_year
        instance.get_month = get_month
        instance.get_day = get_day
        instance.object = FakeEntry()
        self.assertEqual(
            instance.get_template_names(),
            ['zinnia/archives/2012/04/21/my-fake-entry_entry_detail.html',
             'zinnia/archives/month/04/day/21/my-fake-entry_entry_detail.html',
             'zinnia/archives/2012/day/21/my-fake-entry_entry_detail.html',
             'zinnia/archives/day/21/my-fake-entry_entry_detail.html',
             'zinnia/archives/2012/04/21/my-fake-entry.html',
             'zinnia/archives/month/04/day/21/my-fake-entry.html',
             'zinnia/archives/2012/day/21/my-fake-entry.html',
             'zinnia/archives/day/21/my-fake-entry.html',
             'zinnia/archives/2012/04/21/entry_detail.html',
             'zinnia/archives/month/04/day/21/entry_detail.html',
             'zinnia/archives/2012/day/21/entry_detail.html',
             'zinnia/archives/day/21/entry_detail.html',
             'zinnia/archives/2012/month/04/my-fake-entry_entry_detail.html',
             'zinnia/archives/month/04/my-fake-entry_entry_detail.html',
             'zinnia/archives/2012/month/04/my-fake-entry.html',
             'zinnia/archives/month/04/my-fake-entry.html',
             'zinnia/archives/2012/month/04/entry_detail.html',
             'zinnia/archives/month/04/entry_detail.html',
             'zinnia/archives/2012/my-fake-entry_entry_detail.html',
             'zinnia/archives/2012/my-fake-entry.html',
             'zinnia/archives/2012/entry_detail.html',
             'zinnia/archives/my-fake-entry_entry_detail.html',
             'zinnia/my-fake-entry_entry_detail.html',
             'my-fake-entry_entry_detail.html',
             'zinnia/archives/my-fake-entry.html',
             'zinnia/my-fake-entry.html',
             'my-fake-entry.html',
             'zinnia/archives/entry_detail.html',
             'zinnia/entry_detail.html',
             'entry_detail.html'])

        instance.object.detail_template = 'custom.html'
        self.assertEqual(
            instance.get_template_names(),
            ['zinnia/archives/2012/04/21/my-fake-entry_custom.html',
             'zinnia/archives/month/04/day/21/my-fake-entry_custom.html',
             'zinnia/archives/2012/day/21/my-fake-entry_custom.html',
             'zinnia/archives/day/21/my-fake-entry_custom.html',
             'zinnia/archives/2012/04/21/my-fake-entry.html',
             'zinnia/archives/month/04/day/21/my-fake-entry.html',
             'zinnia/archives/2012/day/21/my-fake-entry.html',
             'zinnia/archives/day/21/my-fake-entry.html',
             'zinnia/archives/2012/04/21/custom.html',
             'zinnia/archives/month/04/day/21/custom.html',
             'zinnia/archives/2012/day/21/custom.html',
             'zinnia/archives/day/21/custom.html',
             'zinnia/archives/2012/month/04/my-fake-entry_custom.html',
             'zinnia/archives/month/04/my-fake-entry_custom.html',
             'zinnia/archives/2012/month/04/my-fake-entry.html',
             'zinnia/archives/month/04/my-fake-entry.html',
             'zinnia/archives/2012/month/04/custom.html',
             'zinnia/archives/month/04/custom.html',
             'zinnia/archives/2012/my-fake-entry_custom.html',
             'zinnia/archives/2012/my-fake-entry.html',
             'zinnia/archives/2012/custom.html',
             'zinnia/archives/my-fake-entry_custom.html',
             'zinnia/my-fake-entry_custom.html',
             'my-fake-entry_custom.html',
             'zinnia/archives/my-fake-entry.html',
             'zinnia/my-fake-entry.html',
             'my-fake-entry.html',
             'zinnia/archives/custom.html',
             'zinnia/custom.html',
             'custom.html'])

    def test_previous_next_published_mixin(self):
        site = Site.objects.get_current()

        params = {'title': 'Entry 1', 'content': 'Entry 1',
                  'slug': 'entry-1', 'status': PUBLISHED,
                  'creation_date': datetime(2012, 1, 1, 12)}
        entry_1 = Entry.objects.create(**params)
        entry_1.sites.add(site)

        params = {'title': 'Entry 2', 'content': 'Entry 2',
                  'slug': 'entry-2', 'status': PUBLISHED,
                  'creation_date': datetime(2012, 3, 15, 12)}
        entry_2 = Entry.objects.create(**params)
        entry_2.sites.add(site)

        params = {'title': 'Entry 3', 'content': 'Entry 3',
                  'slug': 'entry-3', 'status': PUBLISHED,
                  'creation_date': datetime(2013, 6, 2, 12)}
        entry_3 = Entry.objects.create(**params)
        entry_3.sites.add(site)

        class EntryPreviousNextPublished(PreviousNextPublishedMixin):
            def get_queryset(self):
                return Entry.published.all()

        test_date = datetime(2009, 12, 1)
        epnp = EntryPreviousNextPublished()
        self.assertEqual(epnp.get_previous_year(test_date), None)
        self.assertEqual(epnp.get_previous_week(test_date), None)
        self.assertEqual(epnp.get_previous_month(test_date), None)
        self.assertEqual(epnp.get_previous_day(test_date), None)
        self.assertEqual(epnp.get_next_year(test_date), date(2012, 1, 1))
        self.assertEqual(epnp.get_next_week(test_date), date(2011, 12, 26))
        self.assertEqual(epnp.get_next_month(test_date), date(2012, 1, 1))
        self.assertEqual(epnp.get_next_day(test_date), date(2012, 1, 1))

        test_date = datetime(2012, 1, 1)
        epnp = EntryPreviousNextPublished()
        self.assertEqual(epnp.get_previous_year(test_date), None)
        self.assertEqual(epnp.get_previous_week(test_date), None)
        self.assertEqual(epnp.get_previous_month(test_date), None)
        self.assertEqual(epnp.get_previous_day(test_date), None)
        self.assertEqual(epnp.get_next_year(test_date), date(2013, 1, 1))
        self.assertEqual(epnp.get_next_week(test_date), date(2012, 3, 12))
        self.assertEqual(epnp.get_next_month(test_date), date(2012, 3, 1))
        self.assertEqual(epnp.get_next_day(test_date), date(2012, 3, 15))

        test_date = datetime(2012, 3, 15)
        epnp = EntryPreviousNextPublished()
        self.assertEqual(epnp.get_previous_year(test_date), None)
        self.assertEqual(epnp.get_previous_week(test_date), date(2011, 12, 26))
        self.assertEqual(epnp.get_previous_month(test_date), date(2012, 1, 1))
        self.assertEqual(epnp.get_previous_day(test_date), date(2012, 1, 1))
        self.assertEqual(epnp.get_next_year(test_date), date(2013, 1, 1))
        self.assertEqual(epnp.get_next_week(test_date), date(2013, 5, 27))
        self.assertEqual(epnp.get_next_month(test_date), date(2013, 6, 1))
        self.assertEqual(epnp.get_next_day(test_date), date(2013, 6, 2))

        test_date = datetime(2013, 6, 2)
        epnp = EntryPreviousNextPublished()
        self.assertEqual(epnp.get_previous_year(test_date), date(2012, 1, 1))
        self.assertEqual(epnp.get_previous_week(test_date), date(2012, 3, 12))
        self.assertEqual(epnp.get_previous_month(test_date), date(2012, 3, 1))
        self.assertEqual(epnp.get_previous_day(test_date), date(2012, 3, 15))
        self.assertEqual(epnp.get_next_year(test_date), None)
        self.assertEqual(epnp.get_next_week(test_date), None)
        self.assertEqual(epnp.get_next_month(test_date), None)
        self.assertEqual(epnp.get_next_day(test_date), None)

        test_date = datetime(2014, 5, 1)
        epnp = EntryPreviousNextPublished()
        self.assertEqual(epnp.get_previous_year(test_date), date(2013, 1, 1))
        self.assertEqual(epnp.get_previous_week(test_date), date(2013, 5, 27))
        self.assertEqual(epnp.get_previous_month(test_date), date(2013, 6, 1))
        self.assertEqual(epnp.get_previous_day(test_date), date(2013, 6, 2))
        self.assertEqual(epnp.get_next_year(test_date), None)
        self.assertEqual(epnp.get_next_week(test_date), None)
        self.assertEqual(epnp.get_next_month(test_date), None)
        self.assertEqual(epnp.get_next_day(test_date), None)

    def test_prefetch_related_mixin(self):
        instance = PrefetchRelatedMixin()
        self.assertRaises(ImproperlyConfigured,
                          instance.get_queryset)
        instance.relation_names = 'string'
        self.assertRaises(ImproperlyConfigured,
                          instance.get_queryset)

    @skipIfCustomUser
    def test_prefetch_categories_authors_mixin(self):
        author = Author.objects.create_user(username='author',
                                            email='author@example.com')
        category = Category.objects.create(title='Category',
                                           slug='category')
        for i in range(3):
            params = {'title': 'My entry',
                      'content': 'My content',
                      'slug': 'my-entry-%s' % i}
            entry = Entry.objects.create(**params)
            entry.authors.add(author)
            entry.categories.add(category)

        class View(object):
            def get_queryset(self):
                return Entry.objects.all()

        class ViewCategoriesAuthorsPrefetched(
                PrefetchCategoriesAuthorsMixin, View):
            pass

        with self.assertNumQueries(7):
            for entry in View().get_queryset():
                entry.authors.count()
                entry.categories.count()

        with self.assertNumQueries(3):
            for entry in ViewCategoriesAuthorsPrefetched().get_queryset():
                entry.authors.count()
                entry.categories.count()

########NEW FILE########
__FILENAME__ = test_models_bases
"""Test cases for zinnia.models_bases"""
from django.test import TestCase
from django.core.exceptions import ImproperlyConfigured

from zinnia.models_bases import load_model_class
from zinnia.models_bases.entry import AbstractEntry


class LoadModelClassTestCase(TestCase):

    def test_load_model_class(self):
        self.assertEqual(
            load_model_class('zinnia.models_bases.entry.AbstractEntry'),
            AbstractEntry)
        self.assertRaises(ImproperlyConfigured,
                          load_model_class, 'invalid.path.models.Toto')

########NEW FILE########
__FILENAME__ = test_moderator
"""Test cases for Zinnia's moderator"""
from django.core import mail
from django.test import TestCase
from django.utils import timezone
from django.contrib.sites.models import Site
from django.core.urlresolvers import reverse
from django.test.utils import restore_template_loaders
from django.test.utils import setup_test_template_loader
from django.contrib.auth.tests.utils import skipIfCustomUser

import django_comments as comments
from django_comments.forms import CommentForm
from django_comments.moderation import moderator as moderator_stack

from zinnia.models.entry import Entry
from zinnia.models.author import Author
from zinnia.managers import PUBLISHED
from zinnia.moderator import EntryCommentModerator
from zinnia.signals import connect_discussion_signals
from zinnia.signals import disconnect_discussion_signals
from zinnia.signals import disconnect_entry_signals


@skipIfCustomUser
class CommentModeratorTestCase(TestCase):
    """Test cases for the moderator"""

    def setUp(self):
        disconnect_entry_signals()
        disconnect_discussion_signals()
        setup_test_template_loader(
            {'comments/comment_authors_email.txt': '',
             'comments/comment_notification_email.txt': '',
             'comments/comment_reply_email.txt': ''})

        self.site = Site.objects.get_current()
        self.author = Author.objects.create(username='admin',
                                            email='admin@example.com')
        params = {'title': 'My test entry',
                  'content': 'My test entry',
                  'slug': 'my-test-entry',
                  'status': PUBLISHED}
        self.entry = Entry.objects.create(**params)
        self.entry.sites.add(self.site)
        self.entry.authors.add(self.author)

    def tearDown(self):
        restore_template_loaders()

    def test_email(self):
        comment = comments.get_model().objects.create(
            comment='My Comment', user=self.author, is_public=True,
            content_object=self.entry, submit_date=timezone.now(),
            site=self.site)
        self.assertEqual(len(mail.outbox), 0)
        moderator = EntryCommentModerator(Entry)
        moderator.email_reply = False
        moderator.email_authors = False
        moderator.mail_comment_notification_recipients = []
        moderator.email(comment, self.entry, 'request')
        self.assertEqual(len(mail.outbox), 0)
        moderator.email_reply = True
        moderator.email_authors = True
        moderator.mail_comment_notification_recipients = ['admin@example.com']
        moderator.email(comment, self.entry, 'request')
        self.assertEqual(len(mail.outbox), 1)

    def test_do_email_notification(self):
        comment = comments.get_model().objects.create(
            comment='My Comment', user=self.author, is_public=True,
            content_object=self.entry, submit_date=timezone.now(),
            site=self.site)
        self.assertEqual(len(mail.outbox), 0)
        moderator = EntryCommentModerator(Entry)
        moderator.mail_comment_notification_recipients = ['admin@example.com']
        moderator.do_email_notification(comment, self.entry, 'request')
        self.assertEqual(len(mail.outbox), 1)

    def test_do_email_authors(self):
        comment = comments.get_model().objects.create(
            comment='My Comment', user=self.author, is_public=True,
            content_object=self.entry, submit_date=timezone.now(),
            site=self.site)
        self.assertEqual(len(mail.outbox), 0)
        moderator = EntryCommentModerator(Entry)
        moderator.email_authors = True
        moderator.mail_comment_notification_recipients = [
            'admin@example.com', 'webmaster@example.com']
        moderator.do_email_authors(comment, self.entry, 'request')
        self.assertEqual(len(mail.outbox), 0)
        moderator.mail_comment_notification_recipients = []
        moderator.do_email_authors(comment, self.entry, 'request')
        self.assertEqual(len(mail.outbox), 1)

    def test_do_email_authors_without_email(self):
        """
        https://github.com/Fantomas42/django-blog-zinnia/issues/145
        """
        comment = comments.get_model().objects.create(
            comment='My Comment', user=self.author, is_public=True,
            content_object=self.entry, submit_date=timezone.now(),
            site=self.site)
        self.assertEqual(len(mail.outbox), 0)
        moderator = EntryCommentModerator(Entry)
        moderator.email_authors = True
        moderator.mail_comment_notification_recipients = []
        contributor = Author.objects.create(username='contributor',
                                            email='contrib@example.com')
        self.entry.authors.add(contributor)
        moderator.do_email_authors(comment, self.entry, 'request')
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(
            set(mail.outbox[0].to),
            set(['admin@example.com', 'contrib@example.com']))
        mail.outbox = []
        contributor.email = ''
        contributor.save()
        moderator.do_email_authors(comment, self.entry, 'request')
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['admin@example.com'])

    def test_do_email_reply(self):
        comment = comments.get_model().objects.create(
            comment='My Comment 1', user=self.author, is_public=True,
            content_object=self.entry, submit_date=timezone.now(),
            site=self.site)
        moderator = EntryCommentModerator(Entry)
        moderator.email_notification_reply = True
        moderator.mail_comment_notification_recipients = [
            'admin@example.com', 'webmaster@example.com']
        moderator.do_email_reply(comment, self.entry, 'request')
        self.assertEqual(len(mail.outbox), 0)

        comment = comments.get_model().objects.create(
            comment='My Comment 2', user_email='user_1@example.com',
            content_object=self.entry, is_public=True,
            submit_date=timezone.now(), site=self.site)
        moderator.do_email_reply(comment, self.entry, 'request')
        self.assertEqual(len(mail.outbox), 0)

        comment = comments.get_model().objects.create(
            comment='My Comment 3', user_email='user_2@example.com',
            content_object=self.entry, is_public=True,
            submit_date=timezone.now(), site=self.site)
        moderator.do_email_reply(comment, self.entry, 'request')
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].bcc, ['user_1@example.com'])

        comment = comments.get_model().objects.create(
            comment='My Comment 4', user=self.author, is_public=True,
            content_object=self.entry, submit_date=timezone.now(),
            site=self.site)
        moderator.do_email_reply(comment, self.entry, 'request')
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(
            set(mail.outbox[1].bcc),
            set(['user_1@example.com', 'user_2@example.com']))

    def test_moderate(self):
        comment = comments.get_model().objects.create(
            comment='My Comment', user=self.author, is_public=True,
            content_object=self.entry, submit_date=timezone.now(),
            site=self.site)
        moderator = EntryCommentModerator(Entry)
        moderator.auto_moderate_comments = True
        moderator.spam_checker_backends = ()
        self.assertTrue(moderator.moderate(comment, self.entry, 'request'))
        moderator.auto_moderate_comments = False
        self.assertFalse(moderator.moderate(comment, self.entry, 'request'))
        moderator.spam_checker_backends = (
            'zinnia.spam_checker.backends.all_is_spam',)
        self.assertTrue(moderator.moderate(comment, self.entry, 'request'))

    def test_moderate_comment_on_entry_without_author(self):
        self.entry.authors.clear()
        comment = comments.get_model().objects.create(
            comment='My Comment', user=self.author, is_public=True,
            content_object=self.entry, submit_date=timezone.now(),
            site=self.site)
        moderator = EntryCommentModerator(Entry)
        moderator.auto_moderate_comments = False
        moderator.spam_checker_backends = (
            'zinnia.spam_checker.backends.all_is_spam',)
        self.assertTrue(moderator.moderate(comment, self.entry, 'request'))

    def test_integrity_error_on_duplicate_spam_comments(self):
        class AllIsSpamModerator(EntryCommentModerator):
            spam_checker_backends = [
                'zinnia.spam_checker.backends.all_is_spam']

        moderator_stack.unregister(Entry)
        moderator_stack.register(Entry, AllIsSpamModerator)

        datas = {'name': 'Jim Bob',
                 'email': 'jim.bob@example.com',
                 'url': '',
                 'comment': 'This is my comment'}

        f = CommentForm(self.entry)
        datas.update(f.initial)
        url = reverse('comments-post-comment')
        self.assertEqual(self.entry.comment_count, 0)
        connect_discussion_signals()
        self.client.post(url, datas)
        self.client.post(url, datas)
        disconnect_discussion_signals()
        self.assertEqual(comments.get_model().objects.count(), 1)
        entry_reloaded = Entry.objects.get(pk=self.entry.pk)
        self.assertEqual(entry_reloaded.comment_count, 0)

    def test_comment_count_denormalization(self):
        class AllIsSpamModerator(EntryCommentModerator):
            spam_checker_backends = [
                'zinnia.spam_checker.backends.all_is_spam']

        class NoMailNoSpamModerator(EntryCommentModerator):
            def email(self, *ka, **kw):
                pass

            def moderate(self, *ka, **kw):
                return False

        datas = {'name': 'Jim Bob',
                 'email': 'jim.bob@example.com',
                 'url': '',
                 'comment': 'This is my comment'}

        f = CommentForm(self.entry)
        datas.update(f.initial)
        url = reverse('comments-post-comment')

        moderator_stack.unregister(Entry)
        moderator_stack.register(Entry, AllIsSpamModerator)

        self.assertEqual(self.entry.comment_count, 0)
        connect_discussion_signals()
        self.client.post(url, datas)
        entry_reloaded = Entry.objects.get(pk=self.entry.pk)
        self.assertEqual(entry_reloaded.comment_count, 0)

        moderator_stack.unregister(Entry)
        moderator_stack.register(Entry, NoMailNoSpamModerator)

        datas['comment'] = 'This a published comment'
        self.client.post(url, datas)
        disconnect_discussion_signals()
        entry_reloaded = Entry.objects.get(pk=self.entry.pk)
        self.assertEqual(entry_reloaded.comment_count, 1)

########NEW FILE########
__FILENAME__ = test_ping
"""Test cases for Zinnia's ping"""
try:
    from io import StringIO
    from urllib.error import URLError
    from urllib.response import addinfourl
except ImportError:  # Python 2
    from urllib import addinfourl
    from urllib2 import URLError
    from cStringIO import StringIO

from django.test import TestCase

from zinnia.models.entry import Entry
from zinnia.ping import URLRessources
from zinnia.ping import DirectoryPinger
from zinnia.ping import ExternalUrlsPinger
from zinnia.signals import disconnect_entry_signals


class NoThreadMixin(object):
    def start(self):
        self.run()


class NoThreadDirectoryPinger(NoThreadMixin, DirectoryPinger):
    pass


class NoThreadExternalUrlsPinger(NoThreadMixin, ExternalUrlsPinger):
    pass


class DirectoryPingerTestCase(TestCase):
    """Test cases for DirectoryPinger"""

    def setUp(self):
        disconnect_entry_signals()
        params = {'title': 'My entry',
                  'content': 'My content',
                  'tags': 'zinnia, test',
                  'slug': 'my-entry'}
        self.entry = Entry.objects.create(**params)

    def test_ping_entry(self):
        pinger = NoThreadDirectoryPinger('http://localhost', [self.entry],
                                         start_now=False)
        self.assertEqual(
            pinger.ping_entry(self.entry),
            {'message': 'http://localhost is an invalid directory.',
             'flerror': True})
        self.assertEqual(pinger.results, [])

    def test_run(self):
        pinger = NoThreadDirectoryPinger('http://localhost', [self.entry])
        self.assertEqual(
            pinger.results,
            [{'flerror': True,
              'message': 'http://localhost is an invalid directory.'}])


class ExternalUrlsPingerTestCase(TestCase):
    """Test cases for ExternalUrlsPinger"""

    def setUp(self):
        disconnect_entry_signals()
        params = {'title': 'My entry',
                  'content': 'My content',
                  'tags': 'zinnia, test',
                  'slug': 'my-entry'}
        self.entry = Entry.objects.create(**params)

    def test_is_external_url(self):
        r = URLRessources()
        pinger = ExternalUrlsPinger(self.entry, start_now=False)
        self.assertEqual(pinger.is_external_url(
            'http://example.com/', 'http://google.com/'), True)
        self.assertEqual(pinger.is_external_url(
            'http://example.com/toto/', 'http://google.com/titi/'), True)
        self.assertEqual(pinger.is_external_url(
            'http://example.com/blog/', 'http://example.com/page/'), False)
        self.assertEqual(pinger.is_external_url(
            '%s/blog/' % r.site_url, r.site_url), False)
        self.assertEqual(pinger.is_external_url(
            'http://google.com/', r.site_url), True)
        self.assertEqual(pinger.is_external_url(
            '/blog/', r.site_url), False)

    def test_find_external_urls(self):
        r = URLRessources()
        pinger = ExternalUrlsPinger(self.entry, start_now=False)
        external_urls = pinger.find_external_urls(self.entry)
        self.assertEqual(external_urls, [])
        self.entry.content = """
        <p>This is a <a href="http://fantomas.willbreak.it/">link</a>
        to a site.</p>
        <p>This is a <a href="%s/blog/">link</a> within my site.</p>
        <p>This is a <a href="/blog/">relative link</a> within my site.</p>
        """ % r.site_url
        self.entry.save()
        external_urls = pinger.find_external_urls(self.entry)
        self.assertEqual(external_urls, ['http://fantomas.willbreak.it/'])

    def test_find_pingback_href(self):
        pinger = ExternalUrlsPinger(self.entry, start_now=False)
        result = pinger.find_pingback_href('')
        self.assertEqual(result, None)
        result = pinger.find_pingback_href("""
        <html><head><link rel="pingback" href="/xmlrpc/" /></head>
        <body></body></html>
        """)
        self.assertEqual(result, '/xmlrpc/')
        result = pinger.find_pingback_href("""
        <html><head><LINK hrEF="/xmlrpc/" REL="PingBack" /></head>
        <body></body></html>
        """)
        self.assertEqual(result, '/xmlrpc/')
        result = pinger.find_pingback_href("""
        <html><head><LINK REL="PingBack" /></head><body></body></html>
        """)
        self.assertEqual(result, None)

    def fake_urlopen(self, url):
        """Fake urlopen using test client"""
        if 'example' in url:
            response = StringIO('')
            return addinfourl(response, {'X-Pingback': '/xmlrpc.php',
                                         'Content-Type': 'text/html'}, url)
        elif 'localhost' in url:
            response = StringIO(
                '<link rel="pingback" href="/xmlrpc/">')
            return addinfourl(response, {'Content-Type': 'text/xhtml'}, url)
        elif 'google' in url:
            response = StringIO('PNG CONTENT')
            return addinfourl(response, {'content-type': 'image/png'}, url)
        elif 'error' in url:
            raise URLError('Invalid ressource')

    def test_pingback_url(self):
        pinger = ExternalUrlsPinger(self.entry, start_now=False)
        self.assertEqual(
            pinger.pingback_url('http://localhost',
                                'http://error.com'),
            'http://error.com cannot be pinged.')

    def test_find_pingback_urls(self):
        # Set up a stub around urlopen
        import zinnia.ping
        self.original_urlopen = zinnia.ping.urlopen
        zinnia.ping.urlopen = self.fake_urlopen
        pinger = ExternalUrlsPinger(self.entry, start_now=False)

        urls = ['http://localhost/', 'http://example.com/', 'http://error',
                'http://www.google.co.uk/images/nav_logo72.png']
        self.assertEqual(
            pinger.find_pingback_urls(urls),
            {'http://localhost/': 'http://localhost/xmlrpc/',
             'http://example.com/': 'http://example.com/xmlrpc.php'})
        # Remove stub
        zinnia.ping.urlopen = self.original_urlopen

    def test_run(self):
        import zinnia.ping
        self.original_urlopen = zinnia.ping.urlopen
        zinnia.ping.urlopen = self.fake_urlopen
        self.entry.content = """
        <a href="http://localhost/">Localhost</a>
        <a href="http://example.com/">Example</a>
        <a href="http://error">Error</a>
        <a href="http://www.google.co.uk/images/nav_logo72.png">Img</a>
        """
        pinger = NoThreadExternalUrlsPinger(self.entry)
        self.assertEqual(pinger.results, [
            'http://localhost/ cannot be pinged.'])
        zinnia.ping.urlopen = self.original_urlopen

########NEW FILE########
__FILENAME__ = test_pingback
"""Test cases for Zinnia's PingBack API"""
try:
    from urllib.error import HTTPError
    from urllib.parse import urlsplit
    from xmlrpc.client import ServerProxy
except ImportError:  # Python 2
    from urllib2 import HTTPError
    from urlparse import urlsplit
    from xmlrpclib import ServerProxy

from django.utils import six
from django.utils import timezone
from django.test import TestCase
from django.contrib.sites.models import Site
from django.test.utils import restore_template_loaders
from django.test.utils import setup_test_template_loader
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.tests.utils import skipIfCustomUser

import django_comments as comments

from bs4 import BeautifulSoup

from zinnia.models.entry import Entry
from zinnia.models.author import Author
from zinnia.models.category import Category
from zinnia.flags import PINGBACK
from zinnia.flags import user_flagger_
from zinnia.managers import PUBLISHED
from zinnia.tests.utils import datetime
from zinnia.tests.utils import TestTransport
from zinnia.xmlrpc.pingback import generate_pingback_content
from zinnia import url_shortener as shortener_settings
from zinnia.signals import connect_discussion_signals
from zinnia.signals import disconnect_entry_signals
from zinnia.signals import disconnect_discussion_signals


@skipIfCustomUser
class PingBackTestCase(TestCase):
    """Test cases for pingbacks"""
    urls = 'zinnia.tests.implementations.urls.default'

    def fake_urlopen(self, url):
        """Fake urlopen using client if domain
        correspond to current_site else HTTPError"""
        scheme, netloc, path, query, fragment = urlsplit(url)
        if not netloc:
            raise
        if self.site.domain == netloc:
            response = six.BytesIO(self.client.get(url).content)
            return response
        raise HTTPError(url, 404, 'unavailable url', {}, None)

    def setUp(self):
        disconnect_entry_signals()
        disconnect_discussion_signals()
        # Clean the memoization of user flagger to avoid error on MySQL
        try:
            del user_flagger_[()]
        except KeyError:
            pass
        # Use default URL shortener backend, to avoid networks errors
        self.original_shortener = shortener_settings.URL_SHORTENER_BACKEND
        shortener_settings.URL_SHORTENER_BACKEND = 'zinnia.url_shortener.'\
                                                   'backends.default'
        # Set up a stub around urlopen
        import zinnia.xmlrpc.pingback
        self.original_urlopen = zinnia.xmlrpc.pingback.urlopen
        zinnia.xmlrpc.pingback.urlopen = self.fake_urlopen
        # Set a short template for entry_detail to avoid rendering errors
        setup_test_template_loader(
            {'zinnia/entry_detail.html':
             '<html><head><title>{{ object.title }}</title></head>'
             '<body>{{ object.html_content|safe }}</body></html>',
             '404.html': '404'})
        # Preparing site
        self.site = Site.objects.get_current()
        # Creating tests entries
        self.author = Author.objects.create_user(username='webmaster',
                                                 email='webmaster@example.com')
        self.category = Category.objects.create(title='test', slug='test')
        params = {'title': 'My first entry',
                  'content': 'My first content',
                  'slug': 'my-first-entry',
                  'creation_date': datetime(2010, 1, 1, 12),
                  'status': PUBLISHED}
        self.first_entry = Entry.objects.create(**params)
        self.first_entry.sites.add(self.site)
        self.first_entry.categories.add(self.category)
        self.first_entry.authors.add(self.author)

        params = {'title': 'My second entry',
                  'content': 'My second content with link '
                  'to <a href="http://%s%s">first entry</a>'
                  ' and other links : %s %s.' % (
                      self.site.domain,
                      self.first_entry.get_absolute_url(),
                      'http://example.com/error-404/',
                      'http://external/'),
                  'slug': 'my-second-entry',
                  'creation_date': datetime(2010, 1, 1, 12),
                  'status': PUBLISHED}
        self.second_entry = Entry.objects.create(**params)
        self.second_entry.sites.add(self.site)
        self.second_entry.categories.add(self.category)
        self.second_entry.authors.add(self.author)
        # Instanciating the server proxy
        self.server = ServerProxy('http://example.com/xmlrpc/',
                                  transport=TestTransport())

    def tearDown(self):
        import zinnia.xmlrpc.pingback
        zinnia.xmlrpc.pingback.urlopen = self.original_urlopen
        shortener_settings.URL_SHORTENER_BACKEND = self.original_shortener
        restore_template_loaders()

    def test_generate_pingback_content(self):
        soup = BeautifulSoup(self.second_entry.content)
        target = 'http://%s%s' % (self.site.domain,
                                  self.first_entry.get_absolute_url())

        self.assertEqual(
            generate_pingback_content(soup, target, 1000),
            'My second content with link to first entry and other links : '
            'http://example.com/error-404/ http://external/.')
        self.assertEqual(
            generate_pingback_content(soup, target, 50),
            '...ond content with link to first entry and other lin...')

        soup = BeautifulSoup('<a href="%s">test link</a>' % target)
        self.assertEqual(
            generate_pingback_content(soup, target, 6), 'test l...')

        soup = BeautifulSoup('test <a href="%s">link</a>' % target)
        self.assertEqual(
            generate_pingback_content(soup, target, 8), '...est link')
        self.assertEqual(
            generate_pingback_content(soup, target, 9), 'test link')

    def test_pingback_ping(self):
        target = 'http://%s%s' % (
            self.site.domain, self.first_entry.get_absolute_url())
        source = 'http://%s%s' % (
            self.site.domain, self.second_entry.get_absolute_url())

        # Error code 0 : A generic fault code
        response = self.server.pingback.ping('toto', 'titi')
        self.assertEqual(response, 0)
        response = self.server.pingback.ping('http://%s/' % self.site.domain,
                                             'http://%s/' % self.site.domain)
        self.assertEqual(response, 0)

        # Error code 16 : The source URI does not exist.
        response = self.server.pingback.ping('http://external/', target)
        self.assertEqual(response, 16)

        # Error code 17 : The source URI does not contain a link to
        # the target URI and so cannot be used as a source.
        response = self.server.pingback.ping(source, 'toto')
        self.assertEqual(response, 17)

        # Error code 32 : The target URI does not exist.
        response = self.server.pingback.ping(
            source, 'http://example.com/error-404/')
        self.assertEqual(response, 32)
        response = self.server.pingback.ping(source, 'http://external/')
        self.assertEqual(response, 32)

        # Error code 33 : The target URI cannot be used as a target.
        response = self.server.pingback.ping(source, 'http://example.com/')
        self.assertEqual(response, 33)
        self.first_entry.pingback_enabled = False
        self.first_entry.save()
        response = self.server.pingback.ping(source, target)
        self.assertEqual(response, 33)

        # Validate pingback
        self.assertEqual(self.first_entry.pingback_count, 0)
        self.first_entry.pingback_enabled = True
        self.first_entry.save()
        connect_discussion_signals()
        response = self.server.pingback.ping(source, target)
        disconnect_discussion_signals()
        self.assertEqual(
            response,
            'Pingback from %s to %s registered.' % (source, target))
        first_entry_reloaded = Entry.objects.get(pk=self.first_entry.pk)
        self.assertEqual(first_entry_reloaded.pingback_count, 1)
        self.assertTrue(self.second_entry.title in
                        self.first_entry.pingbacks[0].user_name)

        # Error code 48 : The pingback has already been registered.
        response = self.server.pingback.ping(source, target)
        self.assertEqual(response, 48)

    def test_pingback_ping_on_entry_without_author(self):
        target = 'http://%s%s' % (
            self.site.domain, self.first_entry.get_absolute_url())
        source = 'http://%s%s' % (
            self.site.domain, self.second_entry.get_absolute_url())
        self.first_entry.pingback_enabled = True
        self.first_entry.save()
        self.first_entry.authors.clear()
        connect_discussion_signals()
        response = self.server.pingback.ping(source, target)
        disconnect_discussion_signals()
        self.assertEqual(
            response,
            'Pingback from %s to %s registered.' % (source, target))
        first_entry_reloaded = Entry.objects.get(pk=self.first_entry.pk)
        self.assertEqual(first_entry_reloaded.pingback_count, 1)
        self.assertTrue(self.second_entry.title in
                        self.first_entry.pingbacks[0].user_name)

    def test_pingback_extensions_get_pingbacks(self):
        target = 'http://%s%s' % (
            self.site.domain, self.first_entry.get_absolute_url())
        source = 'http://%s%s' % (
            self.site.domain, self.second_entry.get_absolute_url())

        response = self.server.pingback.ping(source, target)
        self.assertEqual(
            response, 'Pingback from %s to %s registered.' % (source, target))

        response = self.server.pingback.extensions.getPingbacks(
            'http://external/')
        self.assertEqual(response, 32)

        response = self.server.pingback.extensions.getPingbacks(
            'http://example.com/error-404/')
        self.assertEqual(response, 32)

        response = self.server.pingback.extensions.getPingbacks(
            'http://example.com/2010/')
        self.assertEqual(response, 33)

        response = self.server.pingback.extensions.getPingbacks(source)
        self.assertEqual(response, [])

        response = self.server.pingback.extensions.getPingbacks(target)
        self.assertEqual(response, [
            'http://example.com/2010/01/01/my-second-entry/'])

        comment = comments.get_model().objects.create(
            content_type=ContentType.objects.get_for_model(Entry),
            object_pk=self.first_entry.pk,
            site=self.site, submit_date=timezone.now(),
            comment='Test pingback',
            user_url='http://external/blog/1/',
            user_name='Test pingback')
        comment.flags.create(user=self.author, flag=PINGBACK)

        response = self.server.pingback.extensions.getPingbacks(target)
        self.assertEqual(response, [
            'http://example.com/2010/01/01/my-second-entry/',
            'http://external/blog/1/'])

########NEW FILE########
__FILENAME__ = test_preview
# coding=utf-8
"""Test cases for Zinnia's preview"""
from django.test import TestCase

from zinnia.preview import HTMLPreview


class HTMLPreviewTestCase(TestCase):

    def test_splitters(self):
        text = '<p>Hello World</p><!-- more --><p>Hello dude</p>'
        preview = HTMLPreview(text, splitters=['<!--more-->'],
                              max_words=1000, more_string=' ...')
        self.assertEqual(str(preview), text)
        preview = HTMLPreview(text, splitters=['<!--more-->',
                                               '<!-- more -->'],
                              max_words=1000, more_string=' ...')
        self.assertEqual(str(preview), '<p>Hello World ...</p>')

    def test_truncate(self):
        text = '<p>Hello World</p><p>Hello dude</p>'
        preview = HTMLPreview(text, splitters=[],
                              max_words=2, more_string=' ...')
        self.assertEqual(str(preview), '<p>Hello World ...</p>')

    def test_has_more(self):
        text = '<p>Hello World</p><p>Hello dude</p>'
        preview = HTMLPreview(text, splitters=[],
                              max_words=2, more_string=' ...')
        self.assertEqual(preview.has_more, True)
        preview = HTMLPreview(text, splitters=[],
                              max_words=4, more_string=' ...')
        self.assertEqual(preview.has_more, False)

    def test_has_more_with_long_more_text(self):
        text = '<p>Hello the World</p>'
        preview = HTMLPreview(text, splitters=[],
                              max_words=2, more_string=' .........')
        self.assertEqual(str(preview), '<p>Hello the .........</p>')
        self.assertEqual(preview.has_more, True)

    def test_str_non_ascii_issue_314(self):
        text = '<p>тест non ascii</p>'
        preview = HTMLPreview(text, splitters=[],
                              max_words=2, more_string=' ...')
        self.assertEqual(str(preview), '<p>тест non ...</p>')

    def test_metrics(self):
        text = '<p>Hello World</p> <p>Hello dude</p>'
        preview = HTMLPreview(text, splitters=[],
                              max_words=2, more_string=' ...')
        self.assertEqual(preview.total_words, 4)
        self.assertEqual(preview.displayed_words, 2)
        self.assertEqual(preview.remaining_words, 2)
        self.assertEqual(preview.displayed_percent, 50.0)
        self.assertEqual(preview.remaining_percent, 50.0)

########NEW FILE########
__FILENAME__ = test_signals
"""Test cases for Zinnia's signals"""
from django.test import TestCase

from zinnia.models.entry import Entry
from zinnia.managers import DRAFT
from zinnia.managers import PUBLISHED
from zinnia.signals import disable_for_loaddata
from zinnia.signals import ping_directories_handler
from zinnia.signals import ping_external_urls_handler
from zinnia.signals import disconnect_entry_signals
from zinnia.signals import disconnect_discussion_signals


class SignalsTestCase(TestCase):
    """Test cases for signals"""

    def setUp(self):
        disconnect_entry_signals()
        disconnect_discussion_signals()

    def test_disable_for_loaddata(self):
        self.top = 0

        @disable_for_loaddata
        def make_top():
            self.top += 1

        def call():
            return make_top()

        call()
        self.assertEqual(self.top, 1)
        # Okay the command is executed

    def test_ping_directories_handler(self):
        # Set up a stub around DirectoryPinger
        self.top = 0

        def fake_pinger(*ka, **kw):
            self.top += 1

        import zinnia.ping
        from zinnia import settings
        self.original_pinger = zinnia.ping.DirectoryPinger
        zinnia.ping.DirectoryPinger = fake_pinger

        params = {'title': 'My entry',
                  'content': 'My content',
                  'status': PUBLISHED,
                  'slug': 'my-entry'}
        entry = Entry.objects.create(**params)
        self.assertEqual(entry.is_visible, True)
        settings.PING_DIRECTORIES = ()
        ping_directories_handler('sender', **{'instance': entry})
        self.assertEqual(self.top, 0)
        settings.PING_DIRECTORIES = ('toto',)
        settings.SAVE_PING_DIRECTORIES = True
        ping_directories_handler('sender', **{'instance': entry})
        self.assertEqual(self.top, 1)
        entry.status = DRAFT
        ping_directories_handler('sender', **{'instance': entry})
        self.assertEqual(self.top, 1)

        # Remove stub
        zinnia.ping.DirectoryPinger = self.original_pinger

    def test_ping_external_urls_handler(self):
        # Set up a stub around ExternalUrlsPinger
        self.top = 0

        def fake_pinger(*ka, **kw):
            self.top += 1

        import zinnia.ping
        from zinnia import settings
        self.original_pinger = zinnia.ping.ExternalUrlsPinger
        zinnia.ping.ExternalUrlsPinger = fake_pinger

        params = {'title': 'My entry',
                  'content': 'My content',
                  'status': PUBLISHED,
                  'slug': 'my-entry'}
        entry = Entry.objects.create(**params)
        self.assertEqual(entry.is_visible, True)
        settings.SAVE_PING_EXTERNAL_URLS = False
        ping_external_urls_handler('sender', **{'instance': entry})
        self.assertEqual(self.top, 0)
        settings.SAVE_PING_EXTERNAL_URLS = True
        ping_external_urls_handler('sender', **{'instance': entry})
        self.assertEqual(self.top, 1)
        entry.status = 0
        ping_external_urls_handler('sender', **{'instance': entry})
        self.assertEqual(self.top, 1)

        # Remove stub
        zinnia.ping.ExternalUrlsPinger = self.original_pinger

########NEW FILE########
__FILENAME__ = test_sitemaps
"""Test cases for Zinnia's sitemaps"""
from django.test import TestCase
from django.contrib.sites.models import Site
from django.contrib.auth.tests.utils import skipIfCustomUser

from zinnia.managers import PUBLISHED
from zinnia.models.entry import Entry
from zinnia.models.author import Author
from zinnia.models.category import Category
from zinnia.sitemaps import EntrySitemap
from zinnia.sitemaps import CategorySitemap
from zinnia.sitemaps import AuthorSitemap
from zinnia.sitemaps import TagSitemap
from zinnia.signals import disconnect_entry_signals


@skipIfCustomUser
class SitemapsTestCase(TestCase):
    """Test cases for Sitemaps classes provided"""
    urls = 'zinnia.tests.implementations.urls.default'

    def setUp(self):
        disconnect_entry_signals()
        self.site = Site.objects.get_current()
        self.authors = [
            Author.objects.create(username='admin', email='admin@example.com'),
            Author.objects.create(username='user', email='user@example.com')]
        self.categories = [
            Category.objects.create(title='Category 1', slug='cat-1'),
            Category.objects.create(title='Category 2', slug='cat-2')]
        params = {'title': 'My entry 1', 'content': 'My content 1',
                  'tags': 'zinnia, test', 'slug': 'my-entry-1',
                  'status': PUBLISHED}
        self.entry_1 = Entry.objects.create(**params)
        self.entry_1.authors.add(*self.authors)
        self.entry_1.categories.add(*self.categories)
        self.entry_1.sites.add(self.site)

        params = {'title': 'My entry 2', 'content': 'My content 2',
                  'tags': 'zinnia', 'slug': 'my-entry-2',
                  'status': PUBLISHED}
        self.entry_2 = Entry.objects.create(**params)
        self.entry_2.authors.add(self.authors[0])
        self.entry_2.categories.add(self.categories[0])
        self.entry_2.sites.add(self.site)

        params = {'title': 'My entry draft', 'content': 'My content draft',
                  'tags': 'zinnia, tag', 'slug': 'my-entry-draft'}
        self.entry_draft = Entry.objects.create(**params)
        self.entry_draft.authors.add(self.authors[0])
        self.entry_draft.categories.add(self.categories[0])
        self.entry_draft.sites.add(self.site)

    def test_entry_sitemap(self):
        sitemap = EntrySitemap()
        with self.assertNumQueries(1):
            items = sitemap.items()
            self.assertEqual(len(items), 2)
        self.assertEqual(
            sitemap.lastmod(items[0]).replace(microsecond=0),
            self.entry_2.last_update.replace(microsecond=0))

    def test_category_sitemap(self):
        sitemap = CategorySitemap()
        with self.assertNumQueries(1):
            items = sitemap.items()
            self.assertEqual(len(items), 2)
        self.assertEqual(
            sitemap.lastmod(items[0]).replace(microsecond=0),
            self.entry_2.last_update.replace(microsecond=0))
        self.assertEqual(
            sitemap.lastmod(items[1]).replace(microsecond=0),
            self.entry_1.last_update.replace(microsecond=0))
        self.assertEqual(sitemap.priority(items[0]), '1.0')
        self.assertEqual(sitemap.priority(items[1]), '0.5')

    def test_author_sitemap(self):
        sitemap = AuthorSitemap()
        with self.assertNumQueries(1):
            items = sitemap.items()
            self.assertEqual(len(items), 2)
        self.assertEqual(
            sitemap.lastmod(items[0]).replace(microsecond=0),
            self.entry_2.last_update.replace(microsecond=0))
        self.assertEqual(
            sitemap.lastmod(items[1]).replace(microsecond=0),
            self.entry_1.last_update.replace(microsecond=0))
        self.assertEqual(sitemap.priority(items[0]), '1.0')
        self.assertEqual(sitemap.priority(items[1]), '0.5')

    def test_tag_sitemap(self):
        sitemap = TagSitemap()
        with self.assertNumQueries(3):
            items = sitemap.items()
            self.assertEqual(len(items), 2)
        self.assertEqual(
            sitemap.lastmod(items[1]).replace(microsecond=0),
            self.entry_2.last_update.replace(microsecond=0))
        self.assertEqual(
            sitemap.lastmod(items[0]).replace(microsecond=0),
            self.entry_1.last_update.replace(microsecond=0))
        self.assertEqual(sitemap.priority(items[1]), '1.0')
        self.assertEqual(sitemap.priority(items[0]), '0.5')
        self.assertEqual(sitemap.location(items[1]), '/tags/zinnia/')
        self.assertEqual(sitemap.location(items[0]), '/tags/test/')

    def test_empty_sitemap_issue_188(self):
        Entry.objects.all().delete()
        entry_sitemap = EntrySitemap()
        category_sitemap = CategorySitemap()
        author_sitemap = AuthorSitemap()
        tag_sitemap = TagSitemap()
        self.assertEqual(len(entry_sitemap.items()), 0)
        self.assertEqual(len(category_sitemap.items()), 0)
        self.assertEqual(len(author_sitemap.items()), 0)
        self.assertEqual(len(tag_sitemap.items()), 0)

########NEW FILE########
__FILENAME__ = test_spam_checker
"""Test cases for Zinnia's spam_checker"""
import warnings

from django.test import TestCase

from zinnia.spam_checker import get_spam_checker
from zinnia.spam_checker.backends.all_is_spam import backend


class SpamCheckerTestCase(TestCase):
    """Test cases for zinnia.spam_checker"""

    def test_get_spam_checker(self):
        with warnings.catch_warnings(record=True) as w:
            self.assertEqual(get_spam_checker('mymodule.myclass'), None)
            self.assertTrue(issubclass(w[-1].category, RuntimeWarning))
            self.assertEqual(
                str(w[-1].message),
                'mymodule.myclass backend cannot be imported')

        with warnings.catch_warnings(record=True) as w:
            self.assertEqual(
                get_spam_checker(
                    'zinnia.tests.implementations.custom_spam_checker'), None)
            self.assertTrue(issubclass(w[-1].category, RuntimeWarning))
            self.assertEqual(
                str(w[-1].message),
                'This backend only exists for testing')

        self.assertEqual(
            get_spam_checker('zinnia.spam_checker.backends.all_is_spam'),
            backend)

########NEW FILE########
__FILENAME__ = test_templatetags
"""Test cases for Zinnia's templatetags"""
from datetime import date

from django.test import TestCase
from django.utils import timezone
from django.template import Context
from django.template import Template
from django.template import TemplateSyntaxError
from django.core.paginator import Paginator
from django.core.urlresolvers import reverse
from django.contrib.sites.models import Site
from django.test.utils import override_settings
from django.contrib.auth.tests.utils import skipIfCustomUser

import django_comments as comments
from django_comments.models import CommentFlag

from tagging.models import Tag

from zinnia.models.entry import Entry
from zinnia.models.author import Author
from zinnia.models.category import Category
from zinnia.managers import DRAFT
from zinnia.managers import PUBLISHED
from zinnia.flags import PINGBACK, TRACKBACK
from zinnia.tests.utils import datetime
from zinnia.tests.utils import urlEqual
from zinnia.signals import disconnect_entry_signals
from zinnia.signals import disconnect_discussion_signals
from zinnia.templatetags.zinnia_tags import widont
from zinnia.templatetags.zinnia_tags import week_number
from zinnia.templatetags.zinnia_tags import get_authors
from zinnia.templatetags.zinnia_tags import get_gravatar
from zinnia.templatetags.zinnia_tags import get_tag_cloud
from zinnia.templatetags.zinnia_tags import get_categories
from zinnia.templatetags.zinnia_tags import get_categories_tree
from zinnia.templatetags.zinnia_tags import zinnia_pagination
from zinnia.templatetags.zinnia_tags import zinnia_statistics
from zinnia.templatetags.zinnia_tags import get_draft_entries
from zinnia.templatetags.zinnia_tags import get_recent_entries
from zinnia.templatetags.zinnia_tags import get_random_entries
from zinnia.templatetags.zinnia_tags import zinnia_breadcrumbs
from zinnia.templatetags.zinnia_tags import get_popular_entries
from zinnia.templatetags.zinnia_tags import get_similar_entries
from zinnia.templatetags.zinnia_tags import get_recent_comments
from zinnia.templatetags.zinnia_tags import get_recent_linkbacks
from zinnia.templatetags.zinnia_tags import get_featured_entries
from zinnia.templatetags.zinnia_tags import get_calendar_entries
from zinnia.templatetags.zinnia_tags import get_archives_entries
from zinnia.templatetags.zinnia_tags import get_archives_entries_tree
from zinnia.templatetags.zinnia_tags import user_admin_urlname
from zinnia.templatetags.zinnia_tags import comment_admin_urlname


class TemplateTagsTestCase(TestCase):
    """Test cases for Template tags"""

    def setUp(self):
        disconnect_entry_signals()
        disconnect_discussion_signals()
        params = {'title': 'My entry',
                  'content': 'My content',
                  'tags': 'zinnia, test',
                  'creation_date': datetime(2010, 1, 1, 12),
                  'slug': 'my-entry'}
        self.entry = Entry.objects.create(**params)
        self.site = Site.objects.get_current()

    def publish_entry(self):
        self.entry.status = PUBLISHED
        self.entry.featured = True
        self.entry.sites.add(self.site)
        self.entry.save()

    def make_local(self, date_time):
        """
        Convert aware datetime to local datetime.
        """
        if timezone.is_aware(date_time):
            return timezone.localtime(date_time)
        return date_time

    def test_get_categories(self):
        source_context = Context()
        with self.assertNumQueries(0):
            context = get_categories(source_context)
        self.assertEqual(len(context['categories']), 0)
        self.assertEqual(context['template'], 'zinnia/tags/categories.html')
        self.assertEqual(context['context_category'], None)
        category = Category.objects.create(title='Category 1',
                                           slug='category-1')
        self.entry.categories.add(category)
        self.publish_entry()
        source_context = Context({'category': category})
        with self.assertNumQueries(0):
            context = get_categories(source_context, 'custom_template.html')
        self.assertEqual(len(context['categories']), 1)
        self.assertEqual(context['categories'][0].count_entries_published, 1)
        self.assertEqual(context['template'], 'custom_template.html')
        self.assertEqual(context['context_category'], category)

    def test_get_categories_tree(self):
        source_context = Context()
        with self.assertNumQueries(0):
            context = get_categories_tree(source_context)
        self.assertEqual(len(context['categories']), 0)
        self.assertEqual(context['template'],
                         'zinnia/tags/categories_tree.html')
        self.assertEqual(context['context_category'], None)

        category = Category.objects.create(title='Category 1',
                                           slug='category-1')
        source_context = Context({'category': category})
        with self.assertNumQueries(0):
            context = get_categories_tree(
                source_context, 'custom_template.html')
        self.assertEqual(len(context['categories']), 1)
        self.assertEqual(context['template'], 'custom_template.html')
        self.assertEqual(context['context_category'], category)

    @skipIfCustomUser
    def test_get_authors(self):
        source_context = Context()
        with self.assertNumQueries(0):
            context = get_authors(source_context)
        self.assertEqual(len(context['authors']), 0)
        self.assertEqual(context['template'], 'zinnia/tags/authors.html')
        self.assertEqual(context['context_author'], None)
        author = Author.objects.create_user(username='webmaster',
                                            email='webmaster@example.com')
        self.entry.authors.add(author)
        self.publish_entry()
        source_context = Context({'author': author})
        with self.assertNumQueries(0):
            context = get_authors(source_context, 'custom_template.html')
        self.assertEqual(len(context['authors']), 1)
        self.assertEqual(context['authors'][0].count_entries_published, 1)
        self.assertEqual(context['template'], 'custom_template.html')
        self.assertEqual(context['context_author'], author)

    def test_get_recent_entries(self):
        with self.assertNumQueries(0):
            context = get_recent_entries()
        self.assertEqual(len(context['entries']), 0)
        self.assertEqual(context['template'],
                         'zinnia/tags/entries_recent.html')

        self.publish_entry()
        with self.assertNumQueries(0):
            context = get_recent_entries(3, 'custom_template.html')
        self.assertEqual(len(context['entries']), 1)
        self.assertEqual(context['template'], 'custom_template.html')
        with self.assertNumQueries(0):
            context = get_recent_entries(0)
        self.assertEqual(len(context['entries']), 0)

    def test_get_featured_entries(self):
        with self.assertNumQueries(0):
            context = get_featured_entries()
        self.assertEqual(len(context['entries']), 0)
        self.assertEqual(context['template'],
                         'zinnia/tags/entries_featured.html')

        self.publish_entry()
        with self.assertNumQueries(0):
            context = get_featured_entries(3, 'custom_template.html')
        self.assertEqual(len(context['entries']), 1)
        self.assertEqual(context['template'], 'custom_template.html')
        with self.assertNumQueries(0):
            context = get_featured_entries(0)
        self.assertEqual(len(context['entries']), 0)

    def test_draft_entries(self):
        with self.assertNumQueries(0):
            context = get_draft_entries()
        self.assertEqual(len(context['entries']), 1)
        self.assertEqual(context['template'],
                         'zinnia/tags/entries_draft.html')

        self.publish_entry()
        with self.assertNumQueries(0):
            context = get_draft_entries(3, 'custom_template.html')
        self.assertEqual(len(context['entries']), 0)
        self.assertEqual(context['template'], 'custom_template.html')
        with self.assertNumQueries(0):
            context = get_draft_entries(0)
        self.assertEqual(len(context['entries']), 0)

    def test_get_random_entries(self):
        with self.assertNumQueries(0):
            context = get_random_entries()
        self.assertEqual(len(context['entries']), 0)
        self.assertEqual(context['template'],
                         'zinnia/tags/entries_random.html')

        self.publish_entry()
        with self.assertNumQueries(0):
            context = get_random_entries(3, 'custom_template.html')
        self.assertEqual(len(context['entries']), 1)
        self.assertEqual(context['template'], 'custom_template.html')
        with self.assertNumQueries(0):
            context = get_random_entries(0)
        self.assertEqual(len(context['entries']), 0)

    def test_get_popular_entries(self):
        with self.assertNumQueries(0):
            context = get_popular_entries()
        self.assertEqual(len(context['entries']), 0)
        self.assertEqual(context['template'],
                         'zinnia/tags/entries_popular.html')

        self.publish_entry()
        with self.assertNumQueries(0):
            context = get_popular_entries(3, 'custom_template.html')
        self.assertEqual(len(context['entries']), 0)
        self.assertEqual(context['template'], 'custom_template.html')

        params = {'title': 'My second entry',
                  'content': 'My second content',
                  'tags': 'zinnia, test',
                  'status': PUBLISHED,
                  'comment_count': 2,
                  'slug': 'my-second-entry'}
        second_entry = Entry.objects.create(**params)
        second_entry.sites.add(self.site)
        self.entry.comment_count = 1
        self.entry.save()
        with self.assertNumQueries(0):
            context = get_popular_entries(3)
        self.assertEqual(list(context['entries']), [second_entry, self.entry])

        self.entry.comment_count = 2
        self.entry.save()
        with self.assertNumQueries(0):
            context = get_popular_entries(3)
        self.assertEqual(list(context['entries']), [second_entry, self.entry])

        self.entry.comment_count = 3
        self.entry.save()
        with self.assertNumQueries(0):
            context = get_popular_entries(3)
        self.assertEqual(list(context['entries']), [self.entry, second_entry])

        self.entry.status = DRAFT
        self.entry.save()
        with self.assertNumQueries(0):
            context = get_popular_entries(3)
        self.assertEqual(list(context['entries']), [second_entry])

    def test_get_similar_entries(self):
        self.publish_entry()
        source_context = Context({'object': self.entry})
        with self.assertNumQueries(3):
            context = get_similar_entries(source_context)
        self.assertEqual(len(context['entries']), 0)
        self.assertEqual(context['template'],
                         'zinnia/tags/entries_similar.html')

        params = {'title': 'My second entry',
                  'content': 'This is the second content of my tests.',
                  'tags': 'zinnia, test',
                  'status': PUBLISHED,
                  'slug': 'my-second-entry'}
        second_entry = Entry.objects.create(**params)
        second_entry.sites.add(self.site)

        source_context = Context({'object': second_entry})
        with self.assertNumQueries(3):
            context = get_similar_entries(source_context, 3,
                                          'custom_template.html',
                                          flush=True)
        self.assertEqual(len(context['entries']), 1)
        self.assertEqual(context['template'], 'custom_template.html')

    def test_get_archives_entries(self):
        with self.assertNumQueries(0):
            context = get_archives_entries()
        self.assertEqual(len(context['archives']), 0)
        self.assertEqual(context['template'],
                         'zinnia/tags/entries_archives.html')

        self.publish_entry()
        params = {'title': 'My second entry',
                  'content': 'My second content',
                  'tags': 'zinnia, test',
                  'status': PUBLISHED,
                  'creation_date': datetime(2009, 1, 1),
                  'slug': 'my-second-entry'}
        second_entry = Entry.objects.create(**params)
        second_entry.sites.add(self.site)

        with self.assertNumQueries(0):
            context = get_archives_entries('custom_template.html')
        self.assertEqual(len(context['archives']), 2)

        self.assertEqual(
            context['archives'][0],
            self.make_local(self.entry.creation_date).replace(day=1, hour=0))
        self.assertEqual(
            context['archives'][1],
            self.make_local(second_entry.creation_date).replace(day=1, hour=0))
        self.assertEqual(context['template'], 'custom_template.html')

    def test_get_archives_tree(self):
        with self.assertNumQueries(0):
            context = get_archives_entries_tree()
        self.assertEqual(len(context['archives']), 0)
        self.assertEqual(context['template'],
                         'zinnia/tags/entries_archives_tree.html')

        self.publish_entry()
        params = {'title': 'My second entry',
                  'content': 'My second content',
                  'tags': 'zinnia, test',
                  'status': PUBLISHED,
                  'creation_date': datetime(2009, 1, 10),
                  'slug': 'my-second-entry'}
        second_entry = Entry.objects.create(**params)
        second_entry.sites.add(self.site)

        with self.assertNumQueries(0):
            context = get_archives_entries_tree('custom_template.html')
        self.assertEqual(len(context['archives']), 2)
        self.assertEqual(
            context['archives'][0],
            self.make_local(
                second_entry.creation_date).replace(hour=0))
        self.assertEqual(
            context['archives'][1],
            self.make_local(
                self.entry.creation_date).replace(hour=0))
        self.assertEqual(context['template'], 'custom_template.html')

    def test_get_calendar_entries_no_params(self):
        source_context = Context()
        with self.assertNumQueries(2):
            context = get_calendar_entries(source_context)
        self.assertEqual(context['previous_month'], None)
        self.assertEqual(context['next_month'], None)
        self.assertEqual(context['template'],
                         'zinnia/tags/entries_calendar.html')

        self.publish_entry()
        with self.assertNumQueries(2):
            context = get_calendar_entries(source_context)
        self.assertEqual(
            context['previous_month'],
            self.make_local(self.entry.creation_date).date().replace(day=1))
        self.assertEqual(context['next_month'], None)

    def test_get_calendar_entries_incomplete_year_month(self):
        self.publish_entry()
        source_context = Context()
        with self.assertNumQueries(2):
            context = get_calendar_entries(source_context, year=2009)
        self.assertEqual(
            context['previous_month'],
            self.make_local(self.entry.creation_date).date().replace(day=1))
        self.assertEqual(context['next_month'], None)

        with self.assertNumQueries(2):
            context = get_calendar_entries(source_context, month=1)
        self.assertEqual(
            context['previous_month'],
            self.make_local(self.entry.creation_date).date().replace(day=1))
        self.assertEqual(context['next_month'], None)

    def test_get_calendar_entries_full_params(self):
        self.publish_entry()
        source_context = Context()
        with self.assertNumQueries(2):
            context = get_calendar_entries(source_context, 2009, 1,
                                           template='custom_template.html')
        self.assertEqual(context['previous_month'], None)
        self.assertEqual(
            context['next_month'],
            self.make_local(self.entry.creation_date).date().replace(day=1))
        self.assertEqual(context['template'], 'custom_template.html')

    def test_get_calendar_entries_no_prev_next(self):
        self.publish_entry()
        source_context = Context()
        with self.assertNumQueries(2):
            context = get_calendar_entries(source_context, 2010, 1)
        self.assertEqual(context['previous_month'], None)
        self.assertEqual(context['next_month'], None)

    def test_get_calendar_entries_month_context(self):
        self.publish_entry()
        source_context = Context({'month': date(2009, 1, 1)})
        with self.assertNumQueries(2):
            context = get_calendar_entries(source_context)
        self.assertEqual(context['previous_month'], None)
        self.assertEqual(
            context['next_month'],
            self.make_local(self.entry.creation_date).date().replace(day=1))

    def test_get_calendar_entries_day_context(self):
        self.publish_entry()
        source_context = Context({'month': date(2009, 1, 15)})
        with self.assertNumQueries(2):
            context = get_calendar_entries(source_context)
        self.assertEqual(context['previous_month'], None)
        self.assertEqual(
            context['next_month'],
            self.make_local(self.entry.creation_date).date().replace(day=1))

    def test_get_calendar_entries_object_context(self):
        self.publish_entry()
        source_context = Context({'object': object()})
        with self.assertNumQueries(2):
            context = get_calendar_entries(source_context)
        self.assertEqual(
            context['previous_month'],
            self.make_local(self.entry.creation_date).date().replace(day=1))
        self.assertEqual(context['next_month'], None)

        params = {'title': 'My second entry',
                  'content': 'My second content',
                  'tags': 'zinnia, test',
                  'status': PUBLISHED,
                  'creation_date': datetime(2008, 1, 15),
                  'slug': 'my-second-entry'}
        second_entry = Entry.objects.create(**params)
        second_entry.sites.add(self.site)

        source_context = Context({'object': self.entry})
        with self.assertNumQueries(2):
            context = get_calendar_entries(source_context)
        self.assertEqual(
            context['previous_month'],
            self.make_local(second_entry.creation_date).date().replace(day=1))
        self.assertEqual(context['next_month'], None)

        source_context = Context({'object': second_entry})
        with self.assertNumQueries(2):
            context = get_calendar_entries(source_context)
        self.assertEqual(context['previous_month'], None)
        self.assertEqual(
            context['next_month'],
            self.make_local(self.entry.creation_date).date().replace(day=1))

    @skipIfCustomUser
    def test_get_recent_comments(self):
        with self.assertNumQueries(1):
            context = get_recent_comments()
        self.assertEqual(len(context['comments']), 0)
        self.assertEqual(context['template'],
                         'zinnia/tags/comments_recent.html')

        comment_1 = comments.get_model().objects.create(
            comment='My Comment 1', site=self.site,
            content_object=self.entry, submit_date=timezone.now())
        with self.assertNumQueries(1):
            context = get_recent_comments(3, 'custom_template.html')
        self.assertEqual(len(context['comments']), 0)
        self.assertEqual(context['template'], 'custom_template.html')

        self.publish_entry()
        with self.assertNumQueries(3):
            context = get_recent_comments()
            self.assertEqual(len(context['comments']), 1)
            self.assertEqual(context['comments'][0].content_object,
                             self.entry)

        author = Author.objects.create_user(username='webmaster',
                                            email='webmaster@example.com')
        comment_2 = comments.get_model().objects.create(
            comment='My Comment 2', site=self.site,
            content_object=self.entry, submit_date=timezone.now())
        comment_2.flags.create(user=author,
                               flag=CommentFlag.MODERATOR_APPROVAL)
        with self.assertNumQueries(3):
            context = get_recent_comments()
            self.assertEqual(list(context['comments']),
                             [comment_2, comment_1])
            self.assertEqual(context['comments'][0].content_object,
                             self.entry)
            self.assertEqual(context['comments'][1].content_object,
                             self.entry)

    @skipIfCustomUser
    def test_get_recent_linkbacks(self):
        user = Author.objects.create_user(username='webmaster',
                                          email='webmaster@example.com')
        with self.assertNumQueries(1):
            context = get_recent_linkbacks()
        self.assertEqual(len(context['linkbacks']), 0)
        self.assertEqual(context['template'],
                         'zinnia/tags/linkbacks_recent.html')

        linkback_1 = comments.get_model().objects.create(
            comment='My Linkback 1', site=self.site,
            content_object=self.entry, submit_date=timezone.now())
        linkback_1.flags.create(user=user, flag=PINGBACK)
        with self.assertNumQueries(1):
            context = get_recent_linkbacks(3, 'custom_template.html')
        self.assertEqual(len(context['linkbacks']), 0)
        self.assertEqual(context['template'], 'custom_template.html')

        self.publish_entry()
        with self.assertNumQueries(3):
            context = get_recent_linkbacks()
            self.assertEqual(len(context['linkbacks']), 1)
            self.assertEqual(context['linkbacks'][0].content_object,
                             self.entry)

        linkback_2 = comments.get_model().objects.create(
            comment='My Linkback 2', site=self.site,
            content_object=self.entry, submit_date=timezone.now())
        linkback_2.flags.create(user=user, flag=TRACKBACK)
        with self.assertNumQueries(3):
            context = get_recent_linkbacks()
            self.assertEqual(list(context['linkbacks']),
                             [linkback_2, linkback_1])
            self.assertEqual(context['linkbacks'][0].content_object,
                             self.entry)
            self.assertEqual(context['linkbacks'][1].content_object,
                             self.entry)

    def test_zinnia_pagination(self):
        class FakeRequest(object):
            def __init__(self, get_dict):
                self.GET = get_dict

        source_context = Context({'request': FakeRequest(
            {'page': '1', 'key': 'val'})})
        paginator = Paginator(range(200), 10)

        with self.assertNumQueries(0):
            context = zinnia_pagination(
                source_context, paginator.page(1),
                begin_pages=3, end_pages=3,
                before_pages=2, after_pages=2)
        self.assertEqual(context['page'].number, 1)
        self.assertEqual(list(context['begin']), [1, 2, 3])
        self.assertEqual(list(context['middle']), [])
        self.assertEqual(list(context['end']), [18, 19, 20])
        self.assertEqual(context['GET_string'], '&key=val')
        self.assertEqual(context['template'], 'zinnia/tags/pagination.html')

        source_context = Context({'request': FakeRequest({})})
        with self.assertNumQueries(0):
            context = zinnia_pagination(
                source_context, paginator.page(2),
                begin_pages=3, end_pages=3,
                before_pages=2, after_pages=2)
        self.assertEqual(context['page'].number, 2)
        self.assertEqual(list(context['begin']), [1, 2, 3, 4])
        self.assertEqual(list(context['middle']), [])
        self.assertEqual(list(context['end']), [18, 19, 20])
        self.assertEqual(context['GET_string'], '')

        with self.assertNumQueries(0):
            context = zinnia_pagination(
                source_context, paginator.page(3),
                begin_pages=3, end_pages=3,
                before_pages=2, after_pages=2)
        self.assertEqual(list(context['begin']), [1, 2, 3, 4, 5])
        self.assertEqual(list(context['middle']), [])
        self.assertEqual(list(context['end']), [18, 19, 20])

        with self.assertNumQueries(0):
            context = zinnia_pagination(
                source_context, paginator.page(6),
                begin_pages=3, end_pages=3,
                before_pages=2, after_pages=2)
        self.assertEqual(list(context['begin']), [1, 2, 3, 4, 5, 6, 7, 8])
        self.assertEqual(list(context['middle']), [])
        self.assertEqual(list(context['end']), [18, 19, 20])

        with self.assertNumQueries(0):
            context = zinnia_pagination(
                source_context, paginator.page(11),
                begin_pages=3, end_pages=3,
                before_pages=2, after_pages=2)
        self.assertEqual(list(context['begin']), [1, 2, 3])
        self.assertEqual(list(context['middle']), [9, 10, 11, 12, 13])
        self.assertEqual(list(context['end']), [18, 19, 20])

        with self.assertNumQueries(0):
            context = zinnia_pagination(
                source_context, paginator.page(15),
                begin_pages=3, end_pages=3,
                before_pages=2, after_pages=2)
        self.assertEqual(list(context['begin']), [1, 2, 3])
        self.assertEqual(list(context['middle']), [])
        self.assertEqual(list(context['end']),
                         [13, 14, 15, 16, 17, 18, 19, 20])

        with self.assertNumQueries(0):
            context = zinnia_pagination(
                source_context, paginator.page(18),
                begin_pages=3, end_pages=3,
                before_pages=2, after_pages=2)
        self.assertEqual(list(context['begin']), [1, 2, 3])
        self.assertEqual(list(context['middle']), [])
        self.assertEqual(list(context['end']), [16, 17, 18, 19, 20])

        with self.assertNumQueries(0):
            context = zinnia_pagination(
                source_context, paginator.page(19),
                begin_pages=3, end_pages=3,
                before_pages=2, after_pages=2)
        self.assertEqual(list(context['begin']), [1, 2, 3])
        self.assertEqual(list(context['middle']), [])
        self.assertEqual(list(context['end']), [17, 18, 19, 20])

        with self.assertNumQueries(0):
            context = zinnia_pagination(
                source_context, paginator.page(20),
                begin_pages=3, end_pages=3,
                before_pages=2, after_pages=2)
        self.assertEqual(list(context['begin']), [1, 2, 3])
        self.assertEqual(list(context['middle']), [])
        self.assertEqual(list(context['end']), [18, 19, 20])

        with self.assertNumQueries(0):
            context = zinnia_pagination(
                source_context, paginator.page(10),
                begin_pages=1, end_pages=3,
                before_pages=4, after_pages=3,
                template='custom_template.html')
        self.assertEqual(list(context['begin']), [1])
        self.assertEqual(list(context['middle']), [6, 7, 8, 9, 10, 11, 12, 13])
        self.assertEqual(list(context['end']), [18, 19, 20])
        self.assertEqual(context['template'], 'custom_template.html')

        paginator = Paginator(range(50), 10)
        with self.assertNumQueries(0):
            context = zinnia_pagination(
                source_context, paginator.page(1),
                begin_pages=3, end_pages=3,
                before_pages=2, after_pages=2)
        self.assertEqual(list(context['begin']), [1, 2, 3, 4, 5])
        self.assertEqual(list(context['middle']), [])
        self.assertEqual(list(context['end']), [])

        paginator = Paginator(range(60), 10)
        with self.assertNumQueries(0):
            context = zinnia_pagination(
                source_context, paginator.page(1),
                begin_pages=3, end_pages=3,
                before_pages=2, after_pages=2)
        self.assertEqual(list(context['begin']), [1, 2, 3, 4, 5, 6])
        self.assertEqual(list(context['middle']), [])
        self.assertEqual(list(context['end']), [])

        paginator = Paginator(range(70), 10)
        with self.assertNumQueries(0):
            context = zinnia_pagination(
                source_context, paginator.page(1),
                begin_pages=3, end_pages=3,
                before_pages=2, after_pages=2)
        self.assertEqual(list(context['begin']), [1, 2, 3])
        self.assertEqual(list(context['middle']), [])
        self.assertEqual(list(context['end']), [5, 6, 7])

    def test_zinnia_pagination_on_my_website(self):
        """
        Reproduce the issue encountred on my website,
        versus the expected result.
        """
        class FakeRequest(object):
            def __init__(self, get_dict={}):
                self.GET = get_dict

        source_context = Context({'request': FakeRequest()})
        paginator = Paginator(range(40), 10)

        with self.assertNumQueries(0):
            for i in range(1, 5):
                context = zinnia_pagination(
                    source_context, paginator.page(i),
                    begin_pages=1, end_pages=1,
                    before_pages=2, after_pages=2)
                self.assertEqual(context['page'].number, i)
                self.assertEqual(list(context['begin']), [1, 2, 3, 4])
                self.assertEqual(list(context['middle']), [])
                self.assertEqual(list(context['end']), [])

    @skipIfCustomUser
    def test_zinnia_breadcrumbs(self):
        class FakeRequest(object):
            def __init__(self, path):
                self.path = path

        class FakePage(object):
            def __init__(self, number):
                self.number = number

        def check_only_last_have_no_url(crumb_list):
            size = len(crumb_list) - 1
            for i, crumb in enumerate(crumb_list):
                if i != size:
                    self.assertNotEqual(crumb.url, None)
                else:
                    self.assertEqual(crumb.url, None)

        source_context = Context({'request': FakeRequest('/')})
        with self.assertNumQueries(0):
            context = zinnia_breadcrumbs(source_context)
        self.assertEqual(len(context['breadcrumbs']), 1)
        self.assertEqual(context['breadcrumbs'][0].name, 'Blog')
        self.assertEqual(context['breadcrumbs'][0].url,
                         reverse('zinnia:entry_archive_index'))
        self.assertEqual(context['template'], 'zinnia/tags/breadcrumbs.html')

        with self.assertNumQueries(0):
            context = zinnia_breadcrumbs(source_context,
                                         'Weblog', 'custom_template.html')
        self.assertEqual(len(context['breadcrumbs']), 1)
        self.assertEqual(context['breadcrumbs'][0].name, 'Weblog')
        self.assertEqual(context['template'], 'custom_template.html')

        source_context = Context(
            {'request': FakeRequest(self.entry.get_absolute_url()),
             'object': self.entry})
        with self.assertNumQueries(0):
            context = zinnia_breadcrumbs(source_context)
        self.assertEqual(len(context['breadcrumbs']), 5)
        check_only_last_have_no_url(context['breadcrumbs'])

        cat_1 = Category.objects.create(title='Category 1', slug='category-1')
        source_context = Context(
            {'request': FakeRequest(cat_1.get_absolute_url()),
             'object': cat_1})
        with self.assertNumQueries(0):
            context = zinnia_breadcrumbs(source_context)
        self.assertEqual(len(context['breadcrumbs']), 3)
        check_only_last_have_no_url(context['breadcrumbs'])
        cat_2 = Category.objects.create(title='Category 2', slug='category-2',
                                        parent=cat_1)
        source_context = Context(
            {'request': FakeRequest(cat_2.get_absolute_url()),
             'object': cat_2})
        with self.assertNumQueries(1):
            context = zinnia_breadcrumbs(source_context)
        self.assertEqual(len(context['breadcrumbs']), 4)
        check_only_last_have_no_url(context['breadcrumbs'])

        tag = Tag.objects.get(name='test')
        source_context = Context(
            {'request': FakeRequest(reverse('zinnia:tag_detail',
                                            args=['test'])),
             'object': tag})
        with self.assertNumQueries(0):
            context = zinnia_breadcrumbs(source_context)
        self.assertEqual(len(context['breadcrumbs']), 3)
        check_only_last_have_no_url(context['breadcrumbs'])

        author = Author.objects.create_user(username='webmaster',
                                            email='webmaster@example.com')
        source_context = Context(
            {'request': FakeRequest(author.get_absolute_url()),
             'object': author})
        with self.assertNumQueries(0):
            context = zinnia_breadcrumbs(source_context)
        self.assertEqual(len(context['breadcrumbs']), 3)
        check_only_last_have_no_url(context['breadcrumbs'])

        source_context = Context(
            {'request': FakeRequest(reverse(
                'zinnia:entry_archive_year', args=[2011]))})
        with self.assertNumQueries(0):
            context = zinnia_breadcrumbs(source_context)
        self.assertEqual(len(context['breadcrumbs']), 2)
        check_only_last_have_no_url(context['breadcrumbs'])

        source_context = Context({'request': FakeRequest(reverse(
            'zinnia:entry_archive_month', args=[2011, '03']))})
        with self.assertNumQueries(0):
            context = zinnia_breadcrumbs(source_context)
        self.assertEqual(len(context['breadcrumbs']), 3)
        check_only_last_have_no_url(context['breadcrumbs'])

        source_context = Context({'request': FakeRequest(reverse(
            'zinnia:entry_archive_week', args=[2011, 15]))})
        with self.assertNumQueries(0):
            context = zinnia_breadcrumbs(source_context)
        self.assertEqual(len(context['breadcrumbs']), 3)
        check_only_last_have_no_url(context['breadcrumbs'])

        source_context = Context({'request': FakeRequest(reverse(
            'zinnia:entry_archive_day', args=[2011, '03', 15]))})
        with self.assertNumQueries(0):
            context = zinnia_breadcrumbs(source_context)
        self.assertEqual(len(context['breadcrumbs']), 4)
        check_only_last_have_no_url(context['breadcrumbs'])

        source_context = Context({'request': FakeRequest('%s?page=2' % reverse(
            'zinnia:entry_archive_day', args=[2011, '03', 15])),
            'page_obj': FakePage(2)})
        with self.assertNumQueries(0):
            context = zinnia_breadcrumbs(source_context)
        self.assertEqual(len(context['breadcrumbs']), 5)
        check_only_last_have_no_url(context['breadcrumbs'])

        source_context = Context({'request': FakeRequest(reverse(
            'zinnia:entry_archive_day_paginated', args=[2011, '03', 15, 2])),
            'page_obj': FakePage(2)})
        with self.assertNumQueries(0):
            context = zinnia_breadcrumbs(source_context)
        self.assertEqual(len(context['breadcrumbs']), 5)
        check_only_last_have_no_url(context['breadcrumbs'])
        # More tests can be done here, for testing path and objects in context

    def test_get_gravatar(self):
        self.assertTrue(urlEqual(
            get_gravatar('webmaster@example.com'),
            'http://www.gravatar.com/avatar/86d4fd4a22de452'
            'a9228298731a0b592?s=80&amp;r=g'))
        self.assertTrue(urlEqual(
            get_gravatar('  WEBMASTER@example.com  ', 15, 'x', '404'),
            'http://www.gravatar.com/avatar/86d4fd4a22de452'
            'a9228298731a0b592?s=15&amp;r=x&amp;d=404'))
        self.assertTrue(urlEqual(
            get_gravatar('  WEBMASTER@example.com  ', 15, 'x', '404', 'https'),
            'https://secure.gravatar.com/avatar/86d4fd4a22de452'
            'a9228298731a0b592?s=15&amp;r=x&amp;d=404'))

    def test_get_tags(self):
        Tag.objects.create(name='tag')
        t = Template("""
        {% load zinnia_tags %}
        {% get_tags as entry_tags %}
        {{ entry_tags|join:", " }}
        """)
        with self.assertNumQueries(1):
            html = t.render(Context())
        self.assertEqual(html.strip(), '')
        self.publish_entry()
        html = t.render(Context())
        self.assertEqual(html.strip(), 'test, zinnia')

        template_error_as = """
        {% load zinnia_tags %}
        {% get_tags a_s entry_tags %}"""
        self.assertRaises(TemplateSyntaxError, Template, template_error_as)

        template_error_args = """
        {% load zinnia_tags %}
        {% get_tags as entry tags %}"""
        self.assertRaises(TemplateSyntaxError, Template, template_error_args)

    def test_get_tag_cloud(self):
        source_context = Context()
        with self.assertNumQueries(1):
            context = get_tag_cloud(source_context)
        self.assertEqual(len(context['tags']), 0)
        self.assertEqual(context['template'], 'zinnia/tags/tag_cloud.html')
        self.assertEqual(context['context_tag'], None)
        self.publish_entry()
        tag = Tag.objects.get(name='test')
        source_context = Context({'tag': tag})
        with self.assertNumQueries(1):
            context = get_tag_cloud(source_context, 6, 1,
                                    'custom_template.html')
        self.assertEqual(len(context['tags']), 2)
        self.assertEqual(context['template'], 'custom_template.html')
        self.assertEqual(context['context_tag'], tag)

    def test_widont(self):
        self.assertEqual(
            widont('Word'), 'Word')
        self.assertEqual(
            widont('A complete string'),
            'A complete&nbsp;string')
        self.assertEqual(
            widont('A complete\tstring'),
            'A complete&nbsp;string')
        self.assertEqual(
            widont('A  complete  string'),
            'A  complete&nbsp;string')
        self.assertEqual(
            widont('A complete string with trailing spaces  '),
            'A complete string with trailing&nbsp;spaces  ')
        self.assertEqual(
            widont('A complete string with <markup>', autoescape=False),
            'A complete string with&nbsp;<markup>')
        self.assertEqual(
            widont('A complete string with <markup>', autoescape=True),
            'A complete string with&nbsp;&lt;markup&gt;')

    def test_widont_pre_punctuation(self):
        """
        In some languages like French, applying the widont filter
        before a punctuation sign preceded by a space, leads to
        ugly visual results, instead of a better visual results.
        """
        self.assertEqual(
            widont('Releases : django-blog-zinnia'),
            'Releases&nbsp;:&nbsp;django-blog-zinnia')
        self.assertEqual(
            widont('Releases ; django-blog-zinnia'),
            'Releases&nbsp;;&nbsp;django-blog-zinnia')
        self.assertEqual(
            widont('Releases ! django-blog-zinnia'),
            'Releases&nbsp;!&nbsp;django-blog-zinnia')
        self.assertEqual(
            widont('Releases ? django-blog-zinnia'),
            'Releases&nbsp;?&nbsp;django-blog-zinnia')
        self.assertEqual(
            widont('Releases - django-blog-zinnia'),
            'Releases&nbsp;-&nbsp;django-blog-zinnia')
        self.assertEqual(
            widont('Releases + django-blog-zinnia'),
            'Releases&nbsp;+&nbsp;django-blog-zinnia')
        self.assertEqual(
            widont('Releases * django-blog-zinnia'),
            'Releases&nbsp;*&nbsp;django-blog-zinnia')
        self.assertEqual(
            widont('Releases / django-blog-zinnia'),
            'Releases&nbsp;/&nbsp;django-blog-zinnia')
        self.assertEqual(
            widont('Releases % django-blog-zinnia'),
            'Releases&nbsp;%&nbsp;django-blog-zinnia')
        self.assertEqual(
            widont('Releases = django-blog-zinnia'),
            'Releases&nbsp;=&nbsp;django-blog-zinnia')
        self.assertEqual(
            widont('Releases   :   django-blog-zinnia  '),
            'Releases&nbsp;:&nbsp;django-blog-zinnia  ')
        self.assertEqual(
            widont('Releases :: django-blog-zinnia'),
            'Releases&nbsp;::&nbsp;django-blog-zinnia')
        self.assertEqual(
            widont('Releases :z django-blog-zinnia'),
            'Releases :z&nbsp;django-blog-zinnia')

    def test_widont_post_punctuation(self):
        """
        Sometimes applying the widont filter on just a punctuation sign,
        leads to ugly visual results, instead of better visual results.
        """
        self.assertEqual(
            widont('Move !'),
            'Move&nbsp;!')
        self.assertEqual(
            widont('Move it   !  '),
            'Move&nbsp;it&nbsp;!  ')
        self.assertEqual(
            widont('Move it ?'),
            'Move&nbsp;it&nbsp;?')
        self.assertEqual(
            widont('I like to move : it !'),
            'I like to move&nbsp;:&nbsp;it&nbsp;!')
        self.assertEqual(
            widont('I like to : move it !'),
            'I like to : move&nbsp;it&nbsp;!')

    def test_week_number(self):
        self.assertEqual(week_number(datetime(2013, 1, 1)), '0')
        self.assertEqual(week_number(datetime(2013, 12, 21)), '50')

    def test_comment_admin_urlname(self):
        comment_admin_url = comment_admin_urlname('action')
        self.assertTrue(comment_admin_url.startswith('admin:'))
        self.assertTrue(comment_admin_url.endswith('_action'))

    @skipIfCustomUser
    def test_user_admin_urlname(self):
        user_admin_url = user_admin_urlname('action')
        self.assertEqual(user_admin_url, 'admin:auth_user_action')

    @skipIfCustomUser
    def test_zinnia_statistics(self):
        with self.assertNumQueries(8):
            context = zinnia_statistics()
        self.assertEqual(context['template'], 'zinnia/tags/statistics.html')
        self.assertEqual(context['entries'], 0)
        self.assertEqual(context['categories'], 0)
        self.assertEqual(context['tags'], 0)
        self.assertEqual(context['authors'], 0)
        self.assertEqual(context['comments'], 0)
        self.assertEqual(context['pingbacks'], 0)
        self.assertEqual(context['trackbacks'], 0)
        self.assertEqual(context['rejects'], 0)
        self.assertEqual(context['words_per_entry'], 0)
        self.assertEqual(context['words_per_comment'], 0)
        self.assertEqual(context['entries_per_month'], 0)
        self.assertEqual(context['comments_per_entry'], 0)
        self.assertEqual(context['linkbacks_per_entry'], 0)

        Category.objects.create(title='Category 1', slug='category-1')
        author = Author.objects.create_user(username='webmaster',
                                            email='webmaster@example.com')
        comments.get_model().objects.create(
            comment='My Comment 1', site=self.site,
            content_object=self.entry,
            submit_date=timezone.now())
        self.entry.authors.add(author)
        self.publish_entry()

        with self.assertNumQueries(13):
            context = zinnia_statistics('custom_template.html')
        self.assertEqual(context['template'], 'custom_template.html')
        self.assertEqual(context['entries'], 1)
        self.assertEqual(context['categories'], 1)
        self.assertEqual(context['tags'], 2)
        self.assertEqual(context['authors'], 1)
        self.assertEqual(context['comments'], 1)
        self.assertEqual(context['pingbacks'], 0)
        self.assertEqual(context['trackbacks'], 0)
        self.assertEqual(context['rejects'], 0)
        self.assertEqual(context['words_per_entry'], 2)
        self.assertEqual(context['words_per_comment'], 3)
        self.assertEqual(context['entries_per_month'], 1)
        self.assertEqual(context['comments_per_entry'], 1)
        self.assertEqual(context['linkbacks_per_entry'], 0)


class TemplateTagsTimezoneTestCase(TestCase):

    def create_published_entry_at(self, creation_date):
        params = {'title': 'My entry',
                  'content': 'My content',
                  'slug': 'my-entry',
                  'status': PUBLISHED,
                  'creation_date': creation_date}
        entry = Entry.objects.create(**params)
        entry.sites.add(Site.objects.get_current())
        return entry

    @override_settings(USE_TZ=False)
    def test_calendar_entries_no_timezone(self):
        template = Template('{% load zinnia_tags %}'
                            '{% get_calendar_entries 2014 1 %}')
        self.create_published_entry_at(datetime(2014, 1, 1, 12, 0))
        self.create_published_entry_at(datetime(2014, 1, 1, 23, 0))
        self.create_published_entry_at(datetime(2012, 12, 31, 23, 0))
        self.create_published_entry_at(datetime(2014, 1, 31, 23, 0))
        output = template.render(Context())
        self.assertTrue('/2014/01/01/' in output)
        self.assertTrue('/2014/01/02/' not in output)
        self.assertTrue('/2012/12/' in output)
        self.assertTrue('/2014/02/' not in output)

    @override_settings(USE_TZ=True, TIME_ZONE='Europe/Paris')
    def test_calendar_entries_with_timezone(self):
        template = Template('{% load zinnia_tags %}'
                            '{% get_calendar_entries 2014 1 %}')
        self.create_published_entry_at(datetime(2014, 1, 1, 12, 0))
        self.create_published_entry_at(datetime(2014, 1, 1, 23, 0))
        self.create_published_entry_at(datetime(2012, 12, 31, 23, 0))
        self.create_published_entry_at(datetime(2014, 1, 31, 23, 0))
        output = template.render(Context())
        self.assertTrue('/2014/01/01/' in output)
        self.assertTrue('/2014/01/02/' in output)
        self.assertTrue('/2013/01/' in output)
        self.assertTrue('/2014/02/' in output)

    @override_settings(USE_TZ=False)
    def test_archives_entries_no_timezone(self):
        template = Template('{% load zinnia_tags %}'
                            '{% get_archives_entries %}')
        self.create_published_entry_at(datetime(2014, 1, 1, 12, 0))
        self.create_published_entry_at(datetime(2014, 1, 31, 23, 0))
        output = template.render(Context())
        self.assertTrue('/2014/01/' in output)
        self.assertTrue('/2014/02/' not in output)

    @override_settings(USE_TZ=True, TIME_ZONE='Europe/Paris')
    def test_archives_entries_with_timezone(self):
        template = Template('{% load zinnia_tags %}'
                            '{% get_archives_entries %}')
        self.create_published_entry_at(datetime(2014, 1, 1, 12, 0))
        self.create_published_entry_at(datetime(2014, 1, 31, 23, 0))
        output = template.render(Context())
        self.assertTrue('/2014/01/' in output)
        self.assertTrue('/2014/02/' in output)

    @override_settings(USE_TZ=False)
    def test_archives_entries_tree_no_timezone(self):
        template = Template('{% load zinnia_tags %}'
                            '{% get_archives_entries_tree %}')
        self.create_published_entry_at(datetime(2014, 1, 1, 12, 0))
        self.create_published_entry_at(datetime(2014, 1, 31, 23, 0))
        output = template.render(Context())
        self.assertTrue('/2014/01/01/' in output)
        self.assertTrue('/2014/02/01/' not in output)

    @override_settings(USE_TZ=True, TIME_ZONE='Europe/Paris')
    def test_archives_entries_tree_with_timezone(self):
        template = Template('{% load zinnia_tags %}'
                            '{% get_archives_entries_tree %}')
        self.create_published_entry_at(datetime(2014, 1, 1, 12, 0))
        self.create_published_entry_at(datetime(2014, 1, 31, 23, 0))
        output = template.render(Context())
        self.assertTrue('/2014/01/01/' in output)
        self.assertTrue('/2014/02/01/' in output)

########NEW FILE########
__FILENAME__ = test_translated_urls
"""Test cases for Zinnia's translated URLs"""
from django.test import TestCase
from django.utils.translation import activate
from django.utils.translation import deactivate

from zinnia.urls import i18n_url


class TranslatedURLsTestCase(TestCase):
    """Test cases for translated URLs"""

    def test_translated_urls(self):
        deactivate()
        self.assertEqual(
            i18n_url(r'^authors/'), r'^authors/')
        activate('fr')
        self.assertEqual(
            i18n_url(r'^authors/', True), r'^auteurs/')
        self.assertEqual(
            i18n_url(r'^authors/', False), r'^authors/')

########NEW FILE########
__FILENAME__ = test_url_shortener
"""Test cases for Zinnia's url_shortener"""
import warnings

from django.test import TestCase

from zinnia.url_shortener import get_url_shortener
from zinnia import url_shortener as us_settings
from zinnia.url_shortener.backends import default


class URLShortenerTestCase(TestCase):
    """Test cases for zinnia.url_shortener"""

    def setUp(self):
        self.original_backend = us_settings.URL_SHORTENER_BACKEND

    def tearDown(self):
        us_settings.URL_SHORTENER_BACKEND = self.original_backend

    def test_get_url_shortener(self):
        us_settings.URL_SHORTENER_BACKEND = 'mymodule.myclass'
        with warnings.catch_warnings(record=True) as w:
            self.assertEqual(get_url_shortener(), default.backend)
            self.assertTrue(issubclass(w[-1].category, RuntimeWarning))
            self.assertEqual(
                str(w[-1].message),
                'mymodule.myclass backend cannot be imported')

        us_settings.URL_SHORTENER_BACKEND = ('zinnia.tests.implementations.'
                                             'custom_url_shortener')
        with warnings.catch_warnings(record=True) as w:
            self.assertEqual(get_url_shortener(), default.backend)
            self.assertTrue(issubclass(w[-1].category, RuntimeWarning))
            self.assertEqual(
                str(w[-1].message),
                'This backend only exists for testing')

        us_settings.URL_SHORTENER_BACKEND = 'zinnia.url_shortener'\
                                            '.backends.default'
        self.assertEqual(get_url_shortener(), default.backend)


class FakeEntry(object):
    """Fake entry with only 'pk' as attribute"""
    def __init__(self, pk):
        self.pk = pk


class UrlShortenerDefaultBackendTestCase(TestCase):
    """Tests cases for the default url shortener backend"""
    urls = 'zinnia.tests.implementations.urls.default'

    def test_backend(self):
        original_protocol = default.PROTOCOL
        default.PROTOCOL = 'http'
        entry = FakeEntry(1)
        self.assertEquals(default.backend(entry),
                          'http://example.com/1/')
        default.PROTOCOL = 'https'
        entry = FakeEntry(100)
        self.assertEquals(default.backend(entry),
                          'https://example.com/2S/')
        default.PROTOCOL = original_protocol

    def test_base36(self):
        self.assertEquals(default.base36(1), '1')
        self.assertEquals(default.base36(100), '2S')
        self.assertEquals(default.base36(46656), '1000')

########NEW FILE########
__FILENAME__ = test_views
# coding=utf-8
"""Test cases for Zinnia's views"""
from datetime import date

from django.test import TestCase
from django.utils import timezone
from django.contrib.sites.models import Site
from django.test.utils import override_settings
from django.test.utils import restore_template_loaders
from django.test.utils import setup_test_template_loader
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.signals import user_logged_in
from django.contrib.auth.models import update_last_login
from django.contrib.auth.tests.utils import skipIfCustomUser

import django_comments as comments

from zinnia.models.entry import Entry
from zinnia.models.author import Author
from zinnia.models.category import Category
from zinnia.views import quick_entry
from zinnia.managers import DRAFT
from zinnia.managers import PUBLISHED
from zinnia.settings import PAGINATION
from zinnia.tests.utils import datetime
from zinnia.tests.utils import urlEqual
from zinnia.flags import user_flagger_
from zinnia.flags import get_user_flagger
from zinnia.signals import connect_discussion_signals
from zinnia.signals import disconnect_entry_signals
from zinnia.signals import disconnect_discussion_signals
from zinnia.url_shortener.backends.default import base36


@skipIfCustomUser
@override_settings(
    TEMPLATE_CONTEXT_PROCESSORS=(
        'django.core.context_processors.request',
    ))
class ViewsBaseCase(TestCase):
    """
    Setup and utility function base case.
    """

    def setUp(self):
        disconnect_entry_signals()
        disconnect_discussion_signals()
        self.site = Site.objects.get_current()
        self.author = Author.objects.create_user(username='admin',
                                                 email='admin@example.com',
                                                 password='password')
        self.category = Category.objects.create(title='Tests', slug='tests')
        params = {'title': 'Test 1',
                  'content': 'First test entry published',
                  'slug': 'test-1',
                  'tags': 'tests',
                  'creation_date': datetime(2010, 1, 1, 23, 00),
                  'status': PUBLISHED}
        entry = Entry.objects.create(**params)
        entry.sites.add(self.site)
        entry.categories.add(self.category)
        entry.authors.add(self.author)
        self.first_entry = entry

        params = {'title': 'Test 2',
                  'content': 'Second test entry published',
                  'slug': 'test-2',
                  'tags': 'tests',
                  'creation_date': datetime(2010, 5, 31, 23, 00),
                  'status': PUBLISHED}
        entry = Entry.objects.create(**params)
        entry.sites.add(self.site)
        entry.categories.add(self.category)
        entry.authors.add(self.author)
        self.second_entry = entry

    def tearDown(self):
        """Always try to restore the initial template loaders
        even if the test_template_loader has not been enabled,
        to avoid cascading errors if a test fails"""
        try:
            restore_template_loaders()
        except AttributeError:
            pass

    def inhibit_templates(self, *template_names):
        """
        Set templates with no content to bypass the rendering time.
        """
        setup_test_template_loader(
            dict(map(lambda x: (x, ''), template_names)))

    def create_published_entry(self):
        params = {'title': 'My test entry',
                  'content': 'My test content',
                  'slug': 'my-test-entry',
                  'tags': 'tests',
                  'creation_date': datetime(2010, 1, 1, 23, 0),
                  'status': PUBLISHED}
        entry = Entry.objects.create(**params)
        entry.sites.add(self.site)
        entry.categories.add(self.category)
        entry.authors.add(self.author)
        return entry

    def check_publishing_context(self, url, first_expected,
                                 second_expected=None,
                                 friendly_context=None,
                                 queries=None):
        """Test the numbers of entries in context of an url."""
        if queries is not None:
            with self.assertNumQueries(queries):
                response = self.client.get(url)
        else:
            response = self.client.get(url)
        self.assertEqual(len(response.context['object_list']),
                         first_expected)
        if second_expected:
            self.create_published_entry()
            response = self.client.get(url)
            self.assertEqual(len(response.context['object_list']),
                             second_expected)
        if friendly_context:
            self.assertEqual(
                response.context['object_list'],
                response.context[friendly_context])
        return response

    def check_capabilities(self, url, mimetype, queries=0):
        """Test simple views for the Weblog capabilities"""
        with self.assertNumQueries(queries):
            response = self.client.get(url)
        self.assertEqual(response['Content-Type'], mimetype)
        self.assertTrue('protocol' in response.context)


class ViewsTestCase(ViewsBaseCase):
    """
    Test cases for generic views used in the application,
    for reproducing and correcting issue :
    http://github.com/Fantomas42/django-blog-zinnia/issues#issue/3
    """
    urls = 'zinnia.tests.implementations.urls.default'

    @override_settings(USE_TZ=False)
    def test_zinnia_entry_archive_index_no_timezone(self):
        template_name_today = 'zinnia/archives/%s/entry_archive.html' % \
                              date.today().strftime('%Y/%m/%d')
        self.inhibit_templates(template_name_today)
        response = self.check_publishing_context(
            '/', 2, 3, 'entry_list', 2)
        self.assertTemplateUsed(response, template_name_today)

    @override_settings(USE_TZ=True, TIME_ZONE='Europe/Paris')
    def test_zinnia_entry_archive_index_with_timezone(self):
        template_name_today = 'zinnia/archives/%s/entry_archive.html' % \
                              timezone.localtime(timezone.now()
                                                 ).strftime('%Y/%m/%d')
        self.inhibit_templates(template_name_today)
        response = self.check_publishing_context(
            '/', 2, 3, 'entry_list', 2)
        self.assertTemplateUsed(response, template_name_today)

    @override_settings(USE_TZ=False)
    def test_zinnia_entry_archive_year_no_timezone(self):
        self.inhibit_templates(
            'zinnia/archives/2010/entry_archive_year.html',
            'zinnia/entry_archive_year.html')
        response = self.check_publishing_context(
            '/2010/', 2, 3, 'entry_list', 3)
        self.assertTemplateUsed(
            response, 'zinnia/archives/2010/entry_archive_year.html')
        self.assertEqual(response.context['previous_year'], None)
        self.assertEqual(response.context['next_year'], None)
        response = self.client.get('/2011/')
        self.assertEqual(response.context['previous_year'], date(2010, 1, 1))
        self.assertEqual(response.context['next_year'], None)

    @override_settings(USE_TZ=True, TIME_ZONE='Europe/Paris')
    def test_zinnia_entry_archive_year_with_timezone(self):
        self.inhibit_templates(
            'zinnia/archives/2010/entry_archive_year.html',
            'zinnia/entry_archive_year.html')
        response = self.check_publishing_context(
            '/2010/', 2, 3, 'entry_list', 3)
        self.assertTemplateUsed(
            response, 'zinnia/archives/2010/entry_archive_year.html')
        self.assertEqual(response.context['previous_year'], None)
        self.assertEqual(response.context['next_year'], None)
        response = self.client.get('/2011/')
        self.assertEqual(response.context['previous_year'], date(2010, 1, 1))
        self.assertEqual(response.context['next_year'], None)

    @override_settings(USE_TZ=False)
    def test_zinnia_entry_archive_week_no_timezone(self):
        self.inhibit_templates(
            'zinnia/archives/2010/week/00/entry_archive_week.html',
            'zinnia/entry_archive_week.html')
        response = self.check_publishing_context(
            '/2010/week/00/', 1, 2, 'entry_list', 3)
        self.assertTemplateUsed(
            response, 'zinnia/archives/2010/week/00/entry_archive_week.html')
        # All days in a new year preceding the first Monday
        # are considered to be in week 0.
        self.assertEqual(response.context['week'], date(2009, 12, 28))
        self.assertEqual(response.context['week_end_day'], date(2010, 1, 3))
        self.assertEqual(response.context['previous_week'], None)
        self.assertEqual(response.context['next_week'], date(2010, 5, 31))
        self.assertEqual(list(response.context['date_list']),
                         [datetime(2010, 1, 1)])
        response = self.client.get('/2011/week/01/')
        self.assertEqual(response.context['week'], date(2011, 1, 3))
        self.assertEqual(response.context['week_end_day'], date(2011, 1, 9))
        self.assertEqual(response.context['previous_week'], date(2010, 5, 31))
        self.assertEqual(response.context['next_week'], None)
        self.assertEqual(list(response.context['date_list']), [])

    @override_settings(USE_TZ=True, TIME_ZONE='Europe/Paris')
    def test_zinnia_entry_archive_week_with_timezone(self):
        self.inhibit_templates(
            'zinnia/archives/2010/week/00/entry_archive_week.html',
            'zinnia/entry_archive_week.html')
        response = self.check_publishing_context(
            '/2010/week/00/', 1, 2, 'entry_list', 3)
        self.assertTemplateUsed(
            response, 'zinnia/archives/2010/week/00/entry_archive_week.html')
        # All days in a new year preceding the first Monday
        # are considered to be in week 0.
        self.assertEqual(response.context['week'], date(2009, 12, 28))
        self.assertEqual(response.context['week_end_day'], date(2010, 1, 3))
        self.assertEqual(response.context['previous_week'], None)
        self.assertEqual(response.context['next_week'], date(2010, 5, 31))
        self.assertEqual(response.context['date_list'][0].date(),
                         datetime(2010, 1, 2).date())
        response = self.client.get('/2011/week/01/')
        self.assertEqual(response.context['week'], date(2011, 1, 3))
        self.assertEqual(response.context['week_end_day'], date(2011, 1, 9))
        self.assertEqual(response.context['previous_week'], date(2010, 5, 31))
        self.assertEqual(response.context['next_week'], None)
        self.assertEqual(list(response.context['date_list']), [])

    @override_settings(USE_TZ=False)
    def test_zinnia_entry_archive_month_no_timezone(self):
        self.inhibit_templates(
            'zinnia/archives/2010/month/01/entry_archive_month.html',
            'zinnia/entry_archive_month.html')
        response = self.check_publishing_context(
            '/2010/01/', 1, 2, 'entry_list', 3)
        self.assertTemplateUsed(
            response, 'zinnia/archives/2010/month/01/entry_archive_month.html')
        self.assertEqual(response.context['previous_month'], None)
        self.assertEqual(response.context['next_month'], date(2010, 5, 1))
        self.assertEqual(list(response.context['date_list']),
                         [datetime(2010, 1, 1)])
        response = self.client.get('/2010/05/')
        self.assertEqual(response.context['previous_month'], date(2010, 1, 1))
        self.assertEqual(response.context['next_month'], None)
        self.assertEqual(list(response.context['date_list']),
                         [datetime(2010, 5, 31)])

    @override_settings(USE_TZ=True, TIME_ZONE='Europe/Paris')
    def test_zinnia_entry_archive_month_with_timezone(self):
        self.inhibit_templates(
            'zinnia/archives/2010/month/01/entry_archive_month.html',
            'zinnia/entry_archive_month.html')
        response = self.check_publishing_context(
            '/2010/01/', 1, 2, 'entry_list', 3)
        self.assertTemplateUsed(
            response, 'zinnia/archives/2010/month/01/entry_archive_month.html')
        self.assertEqual(response.context['previous_month'], None)
        self.assertEqual(response.context['next_month'], date(2010, 6, 1))
        self.assertEqual(response.context['date_list'][0].date(),
                         datetime(2010, 1, 2).date())
        response = self.client.get('/2010/06/')
        self.assertEqual(response.context['previous_month'], date(2010, 1, 1))
        self.assertEqual(response.context['next_month'], None)
        self.assertEqual(response.context['date_list'][0].date(),
                         datetime(2010, 6, 1).date())

    @override_settings(USE_TZ=False)
    def test_zinnia_entry_archive_day_no_timezone(self):
        self.inhibit_templates(
            'zinnia/archives/2010/01/01/entry_archive_day.html',
            'zinnia/entry_archive_day.html')
        response = self.check_publishing_context(
            '/2010/01/01/', 1, 2, 'entry_list', 2)
        self.assertTemplateUsed(
            response, 'zinnia/archives/2010/01/01/entry_archive_day.html')
        self.assertEqual(response.context['previous_month'], None)
        self.assertEqual(response.context['next_month'], date(2010, 5, 1))
        self.assertEqual(response.context['previous_day'], None)
        self.assertEqual(response.context['next_day'], date(2010, 5, 31))
        response = self.client.get('/2010/05/31/')
        self.assertEqual(response.context['previous_month'], date(2010, 1, 1))
        self.assertEqual(response.context['next_month'], None)
        self.assertEqual(response.context['previous_day'], date(2010, 1, 1))
        self.assertEqual(response.context['next_day'], None)

    @override_settings(USE_TZ=True, TIME_ZONE='Europe/Paris')
    def test_zinnia_entry_archive_day_with_timezone(self):
        self.inhibit_templates(
            'zinnia/archives/2010/01/02/entry_archive_day.html',
            'zinnia/entry_archive_day.html')
        response = self.check_publishing_context(
            '/2010/01/02/', 1, 2, 'entry_list', 2)
        self.assertTemplateUsed(
            response, 'zinnia/archives/2010/01/02/entry_archive_day.html')
        self.assertEqual(response.context['previous_month'], None)
        self.assertEqual(response.context['next_month'], date(2010, 6, 1))
        self.assertEqual(response.context['previous_day'], None)
        self.assertEqual(response.context['next_day'], date(2010, 6, 1))
        response = self.client.get('/2010/06/01/')
        self.assertEqual(response.context['previous_month'], date(2010, 1, 1))
        self.assertEqual(response.context['next_month'], None)
        self.assertEqual(response.context['previous_day'], date(2010, 1, 2))
        self.assertEqual(response.context['next_day'], None)

    @override_settings(USE_TZ=False)
    def test_zinnia_entry_archive_today_no_timezone(self):
        self.inhibit_templates('zinnia/entry_archive_today.html')
        with self.assertNumQueries(2):
            response = self.client.get('/today/')
        self.assertTemplateUsed(response, 'zinnia/entry_archive_today.html')
        self.assertEqual(response.context['day'].date(), date.today())
        self.assertEqual(response.context['previous_month'], date(2010, 5, 1))
        self.assertEqual(response.context['next_month'], None)
        self.assertEqual(response.context['previous_day'], date(2010, 5, 31))
        self.assertEqual(response.context['next_day'], None)

    @override_settings(USE_TZ=True, TIME_ZONE='Europe/Paris')
    def test_zinnia_entry_archive_today_with_timezone(self):
        self.inhibit_templates('zinnia/entry_archive_today.html')
        with self.assertNumQueries(2):
            response = self.client.get('/today/')
        self.assertTemplateUsed(response, 'zinnia/entry_archive_today.html')
        self.assertEqual(response.context['day'].date(), timezone.localtime(
            timezone.now()).date())
        self.assertEqual(response.context['previous_month'], date(2010, 6, 1))
        self.assertEqual(response.context['next_month'], None)
        self.assertEqual(response.context['previous_day'], date(2010, 6, 1))
        self.assertEqual(response.context['next_day'], None)

    def test_zinnia_entry_shortlink(self):
        with self.assertNumQueries(1):
            response = self.client.get('/%s/' % base36(self.first_entry.pk))
        self.assertEqual(response.status_code, 301)
        self.assertEqual(
            response['Location'],
            'http://testserver%s' % self.first_entry.get_absolute_url())

    def test_zinnia_entry_detail(self):
        self.inhibit_templates('zinnia/_entry_detail.html', '404.html')
        entry = self.create_published_entry()
        entry.sites.clear()
        response = self.client.get(entry.get_absolute_url())
        self.assertEqual(response.status_code, 404)
        entry.detail_template = '_entry_detail.html'
        entry.save()
        entry.sites.add(Site.objects.get_current())
        with self.assertNumQueries(1):
            response = self.client.get(entry.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'zinnia/_entry_detail.html')

    def test_zinnia_entry_detail_login(self):
        self.inhibit_templates('zinnia/entry_detail.html',
                               'zinnia/login.html')
        entry = self.create_published_entry()
        entry.login_required = True
        entry.save()
        with self.assertNumQueries(1):
            response = self.client.get(entry.get_absolute_url())
        self.assertTemplateUsed(response, 'zinnia/login.html')
        response = self.client.post(entry.get_absolute_url(),
                                    {'username': 'admin',
                                     'password': 'password'})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'zinnia/entry_detail.html')

    def test_zinnia_entry_detail_password(self):
        self.inhibit_templates('zinnia/entry_detail.html',
                               'zinnia/password.html')
        entry = self.create_published_entry()
        entry.password = 'password'
        entry.save()
        with self.assertNumQueries(1):
            response = self.client.get(entry.get_absolute_url())
        self.assertTemplateUsed(response, 'zinnia/password.html')
        self.assertEqual(response.context['error'], False)
        with self.assertNumQueries(1):
            response = self.client.post(entry.get_absolute_url(),
                                        {'entry_password': 'bad_password'})
        self.assertTemplateUsed(response, 'zinnia/password.html')
        self.assertEqual(response.context['error'], True)
        with self.assertNumQueries(7):
            response = self.client.post(entry.get_absolute_url(),
                                        {'entry_password': 'password'})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'zinnia/entry_detail.html')

    def test_zinnia_entry_detail_login_password(self):
        user_logged_in.disconnect(update_last_login)
        self.inhibit_templates('zinnia/entry_detail.html',
                               'zinnia/login.html',
                               'zinnia/password.html')
        entry = self.create_published_entry()
        entry.password = 'password'
        entry.login_required = True
        entry.save()
        with self.assertNumQueries(1):
            response = self.client.get(entry.get_absolute_url())
        self.assertTemplateUsed(response, 'zinnia/login.html')
        with self.assertNumQueries(12):
            response = self.client.post(entry.get_absolute_url(),
                                        {'username': 'admin',
                                         'password': 'password'})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'zinnia/password.html')
        self.assertEqual(response.context['error'], False)
        with self.assertNumQueries(7):
            response = self.client.post(entry.get_absolute_url(),
                                        {'entry_password': 'password'})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'zinnia/entry_detail.html')
        user_logged_in.connect(update_last_login)

    def test_zinnia_entry_detail_preview(self):
        self.inhibit_templates('zinnia/entry_detail.html', '404.html')
        self.first_entry.status = DRAFT
        self.first_entry.save()
        url = self.first_entry.get_absolute_url()
        with self.assertNumQueries(2):
            response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
        Author.objects.create_superuser(
            'root', 'root@example.com', 'password')
        self.client.login(username='root', password='password')
        with self.assertNumQueries(3):
            response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.client.login(username='admin', password='password')
        with self.assertNumQueries(6):
            response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_zinnia_entry_channel(self):
        self.inhibit_templates('zinnia/entry_list.html')
        self.check_publishing_context(
            '/channel-test/', 2, 3, 'entry_list', 1)

    def test_zinnia_category_list(self):
        self.inhibit_templates('zinnia/category_list.html')
        self.check_publishing_context(
            '/categories/', 1,
            friendly_context='category_list',
            queries=0)
        self.first_entry.categories.add(Category.objects.create(
            title='New category', slug='new-category'))
        self.check_publishing_context('/categories/', 2)

    def test_zinnia_category_detail(self):
        self.inhibit_templates('zinnia/category/tests/entry_list.html')
        response = self.check_publishing_context(
            '/categories/tests/', 2, 3, 'entry_list', 2)
        self.assertTemplateUsed(
            response, 'zinnia/category/tests/entry_list.html')
        self.assertEqual(response.context['category'].slug, 'tests')

    def test_zinnia_category_detail_paginated(self):
        """Test case reproducing issue #42 on category
        detail view paginated"""
        self.inhibit_templates('zinnia/entry_list.html')
        for i in range(PAGINATION):
            params = {'title': 'My entry %i' % i,
                      'content': 'My content %i' % i,
                      'slug': 'my-entry-%i' % i,
                      'creation_date': datetime(2010, 1, 1),
                      'status': PUBLISHED}
            entry = Entry.objects.create(**params)
            entry.sites.add(self.site)
            entry.categories.add(self.category)
        response = self.client.get('/categories/tests/')
        self.assertEqual(len(response.context['object_list']), PAGINATION)
        response = self.client.get('/categories/tests/?page=2')
        self.assertEqual(len(response.context['object_list']), 2)
        response = self.client.get('/categories/tests/page/2/')
        self.assertEqual(len(response.context['object_list']), 2)
        self.assertEqual(response.context['category'].slug, 'tests')

    def test_zinnia_author_list(self):
        self.inhibit_templates('zinnia/author_list.html')
        self.check_publishing_context(
            '/authors/', 1,
            friendly_context='author_list',
            queries=0)
        user = Author.objects.create(username='new-user',
                                     email='new_user@example.com')
        self.check_publishing_context('/authors/', 1)
        self.first_entry.authors.add(user)
        self.check_publishing_context('/authors/', 2)

    def test_zinnia_author_detail(self):
        self.inhibit_templates('zinnia/author/admin/entry_list.html')
        response = self.check_publishing_context(
            '/authors/admin/', 2, 3, 'entry_list', 2)
        self.assertTemplateUsed(
            response, 'zinnia/author/admin/entry_list.html')
        self.assertEqual(response.context['author'].username, 'admin')

    def test_zinnia_author_detail_paginated(self):
        """Test case reproducing issue #207 on author
        detail view paginated"""
        self.inhibit_templates('zinnia/entry_list.html')
        for i in range(PAGINATION):
            params = {'title': 'My entry %i' % i,
                      'content': 'My content %i' % i,
                      'slug': 'my-entry-%i' % i,
                      'creation_date': datetime(2010, 1, 1),
                      'status': PUBLISHED}
            entry = Entry.objects.create(**params)
            entry.sites.add(self.site)
            entry.authors.add(self.author)
        response = self.client.get('/authors/admin/')
        self.assertEqual(len(response.context['object_list']), PAGINATION)
        response = self.client.get('/authors/admin/?page=2')
        self.assertEqual(len(response.context['object_list']), 2)
        response = self.client.get('/authors/admin/page/2/')
        self.assertEqual(len(response.context['object_list']), 2)
        self.assertEqual(response.context['author'].username, 'admin')

    def test_zinnia_tag_list(self):
        self.inhibit_templates('zinnia/tag_list.html')
        self.check_publishing_context(
            '/tags/', 1,
            friendly_context='tag_list',
            queries=1)
        self.first_entry.tags = 'tests, tag'
        self.first_entry.save()
        self.check_publishing_context('/tags/', 2)

    def test_zinnia_tag_detail(self):
        self.inhibit_templates('zinnia/tag/tests/entry_list.html', '404.html')
        response = self.check_publishing_context(
            '/tags/tests/', 2, 3, 'entry_list', 2)
        self.assertTemplateUsed(
            response, 'zinnia/tag/tests/entry_list.html')
        self.assertEqual(response.context['tag'].name, 'tests')
        response = self.client.get('/tags/404/')
        self.assertEqual(response.status_code, 404)

    def test_zinnia_tag_detail_paginated(self):
        self.inhibit_templates('zinnia/entry_list.html')
        for i in range(PAGINATION):
            params = {'title': 'My entry %i' % i,
                      'content': 'My content %i' % i,
                      'slug': 'my-entry-%i' % i,
                      'tags': 'tests',
                      'creation_date': datetime(2010, 1, 1),
                      'status': PUBLISHED}
            entry = Entry.objects.create(**params)
            entry.sites.add(self.site)
        response = self.client.get('/tags/tests/')
        self.assertEqual(len(response.context['object_list']), PAGINATION)
        response = self.client.get('/tags/tests/?page=2')
        self.assertEqual(len(response.context['object_list']), 2)
        response = self.client.get('/tags/tests/page/2/')
        self.assertEqual(len(response.context['object_list']), 2)
        self.assertEqual(response.context['tag'].name, 'tests')

    def test_zinnia_entry_search(self):
        self.inhibit_templates('zinnia/entry_search.html')
        self.check_publishing_context(
            '/search/?pattern=test', 2, 3, 'entry_list', 1)
        response = self.client.get('/search/?pattern=ab')
        self.assertEqual(len(response.context['object_list']), 0)
        self.assertEqual(response.context['error'],
                         _('The pattern is too short'))
        response = self.client.get('/search/')
        self.assertEqual(len(response.context['object_list']), 0)
        self.assertEqual(response.context['error'],
                         _('No pattern to search found'))

    def test_zinnia_entry_random(self):
        self.inhibit_templates('zinnia/entry_detail.html')
        response = self.client.get('/random/', follow=True)
        self.assertTrue(response.redirect_chain[0][0].startswith(
            'http://testserver/2010/'))
        self.assertEqual(response.redirect_chain[0][1], 302)

    def test_zinnia_sitemap(self):
        self.inhibit_templates('zinnia/sitemap.html')
        with self.assertNumQueries(0):
            response = self.client.get('/sitemap/')
        self.assertEqual(len(response.context['entries']), 2)
        self.assertEqual(len(response.context['categories']), 1)
        entry = self.create_published_entry()
        entry.categories.add(Category.objects.create(title='New category',
                                                     slug='new-category'))
        response = self.client.get('/sitemap/')
        self.assertEqual(len(response.context['entries']), 3)
        self.assertEqual(len(response.context['categories']), 2)

    def test_zinnia_trackback(self):
        # Clean the memoization of user flagger to avoid error on MySQL
        try:
            del user_flagger_[()]
        except KeyError:
            pass
        self.inhibit_templates('zinnia/entry_trackback.xml', '404.html')
        response = self.client.post('/trackback/404/')
        trackback_url = '/trackback/%s/' % self.first_entry.pk
        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.client.post(trackback_url).status_code, 301)
        self.first_entry.trackback_enabled = False
        self.first_entry.save()
        self.assertEqual(self.first_entry.trackback_count, 0)
        response = self.client.post(trackback_url,
                                    {'url': 'http://example.com'})
        self.assertEqual(response['Content-Type'], 'text/xml')
        self.assertEqual(response.context['error'],
                         'Trackback is not enabled for Test 1')
        self.first_entry.trackback_enabled = True
        self.first_entry.save()
        connect_discussion_signals()
        get_user_flagger()  # Memoize user flagger for stable query number
        if comments.get_comment_app_name() == comments.DEFAULT_COMMENTS_APP:
            # If we are using the default comment app,
            # we can count the database queries executed.
            with self.assertNumQueries(8):
                response = self.client.post(trackback_url,
                                            {'url': 'http://example.com'})
        else:
            response = self.client.post(trackback_url,
                                        {'url': 'http://example.com'})
        self.assertEqual(response['Content-Type'], 'text/xml')
        self.assertEqual('error' in response.context, False)
        disconnect_discussion_signals()
        entry = Entry.objects.get(pk=self.first_entry.pk)
        self.assertEqual(entry.trackback_count, 1)
        response = self.client.post(trackback_url,
                                    {'url': 'http://example.com'})
        self.assertEqual(response.context['error'],
                         'Trackback is already registered')

    def test_zinnia_trackback_on_entry_without_author(self):
        # Clean the memoization of user flagger to avoid error on MySQL
        try:
            del user_flagger_[()]
        except KeyError:
            pass
        self.inhibit_templates('zinnia/entry_trackback.xml')
        self.first_entry.authors.clear()
        response = self.client.post('/trackback/%s/' % self.first_entry.pk,
                                    {'url': 'http://example.com'})
        self.assertEqual(response['Content-Type'], 'text/xml')
        self.assertEqual('error' in response.context, False)

    def test_capabilities(self):
        self.inhibit_templates(
            'zinnia/humans.txt',
            'zinnia/rsd.xml',
            'zinnia/wlwmanifest.xml',
            'zinnia/opensearch.xml')
        self.check_capabilities('/humans.txt', 'text/plain', 0)
        self.check_capabilities('/rsd.xml', 'application/rsd+xml', 0)
        self.check_capabilities('/wlwmanifest.xml',
                                'application/wlwmanifest+xml', 0)
        self.check_capabilities('/opensearch.xml',
                                'application/opensearchdescription+xml', 0)

    def test_comment_success(self):
        self.inhibit_templates('comments/zinnia/entry/posted.html',
                               'zinnia/entry_list.html')
        with self.assertNumQueries(0):
            response = self.client.get('/comments/success/')
        self.assertTemplateUsed(response, 'comments/zinnia/entry/posted.html')
        self.assertEqual(response.context['comment'], None)

        with self.assertNumQueries(1):
            response = self.client.get('/comments/success/?c=404')
        self.assertEqual(response.context['comment'], None)

        comment = comments.get_model().objects.create(
            submit_date=timezone.now(),
            comment='My Comment 1', content_object=self.category,
            site=self.site, is_public=False)
        success_url = '/comments/success/?c=%s' % comment.pk
        with self.assertNumQueries(1):
            response = self.client.get(success_url)
        self.assertEqual(response.context['comment'], comment)
        comment.is_public = True
        comment.save()
        with self.assertNumQueries(5):
            response = self.client.get(success_url, follow=True)
        self.assertEqual(
            response.redirect_chain[1],
            ('http://example.com/categories/tests/', 302))

    def test_comment_success_invalid_pk_issue_292(self):
        self.inhibit_templates('comments/zinnia/entry/posted.html')
        with self.assertNumQueries(0):
            response = self.client.get('/comments/success/?c=file.php')
        self.assertTemplateUsed(response, 'comments/zinnia/entry/posted.html')
        self.assertEqual(response.context['comment'], None)

    def test_quick_entry(self):
        Author.objects.create_superuser(
            'root', 'root@example.com', 'password')
        response = self.client.get('/quick-entry/')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response['Location'],
            'http://testserver/accounts/login/?next=/quick-entry/')
        self.client.login(username='admin', password='password')
        response = self.client.get('/quick-entry/')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response['Location'],
            'http://testserver/accounts/login/?next=/quick-entry/')
        self.client.logout()
        self.client.login(username='root', password='password')
        response = self.client.get('/quick-entry/')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response['Location'],
            'http://testserver/admin/zinnia/entry/add/')
        response = self.client.post('/quick-entry/', {'content': 'test'})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(urlEqual(
            response['Location'],
            'http://testserver/admin/zinnia/entry/add/'
            '?tags=&title=&sites=1&content='
            '%3Cp%3Etest%3C%2Fp%3E&authors=2&slug='))
        response = self.client.post('/quick-entry/',
                                    {'title': 'test', 'tags': 'test',
                                     'content': 'Test content',
                                     'save_draft': ''})
        entry = Entry.objects.get(title='test')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response['Location'],
            'http://testserver%s' % entry.get_absolute_url())
        self.assertEqual(entry.status, DRAFT)
        self.assertEqual(entry.title, 'test')
        self.assertEqual(entry.tags, 'test')
        self.assertEqual(entry.content, '<p>Test content</p>')

    def test_quick_entry_non_ascii_title_issue_153(self):
        Author.objects.create_superuser(
            'root', 'root@example.com', 'password')
        self.client.login(username='root', password='password')
        response = self.client.post('/quick-entry/',
                                    {'title': 'тест', 'tags': 'test-2',
                                     'content': 'Test content',
                                     'save_draft': ''})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(urlEqual(
            response['Location'],
            'http://testserver/admin/zinnia/entry/add/'
            '?tags=test-2&title=%D1%82%D0%B5%D1%81%D1%82'
            '&sites=1&content=%3Cp%3ETest+content%3C%2Fp%3E'
            '&authors=2&slug='))

    def test_quick_entry_markup_language_issue_270(self):
        original_markup_language = quick_entry.MARKUP_LANGUAGE
        quick_entry.MARKUP_LANGUAGE = 'restructuredtext'
        Author.objects.create_superuser(
            'root', 'root@example.com', 'password')
        self.client.login(username='root', password='password')
        response = self.client.post('/quick-entry/',
                                    {'title': 'Test markup',
                                     'tags': 'test, markup',
                                     'content': 'Hello *World* !',
                                     'save_draft': ''})
        entry = Entry.objects.get(title='Test markup')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response['Location'],
            'http://testserver%s' % entry.get_absolute_url())
        self.assertEquals(
            entry.content,
            'Hello *World* !')
        quick_entry.MARKUP_LANGUAGE = original_markup_language


class CustomDetailViewsTestCase(ViewsBaseCase):
    """
    Tests with an alternate urls.py that modifies how author_detail,
    tags_detail and categories_detail views to be called with a custom
    template_name keyword argument and an extra_context.
    """
    urls = 'zinnia.tests.implementations.urls.custom_detail_views'

    def setUp(self):
        """We don't need to generate the full template
        to make the tests working"""
        super(CustomDetailViewsTestCase, self).setUp()
        self.inhibit_templates('zinnia/entry_custom_list.html')

    def test_custom_category_detail(self):
        response = self.check_publishing_context('/categories/tests/', 2, 3)
        self.assertTemplateUsed(response, 'zinnia/entry_custom_list.html')
        self.assertEqual(response.context['category'].slug, 'tests')
        self.assertEqual(response.context['extra'], 'context')

    def test_custom_author_detail(self):
        response = self.check_publishing_context('/authors/admin/', 2, 3)
        self.assertTemplateUsed(response, 'zinnia/entry_custom_list.html')
        self.assertEqual(response.context['author'].username, 'admin')
        self.assertEqual(response.context['extra'], 'context')

    def test_custom_tag_detail(self):
        response = self.check_publishing_context('/tags/tests/', 2, 3)
        self.assertTemplateUsed(response, 'zinnia/entry_custom_list.html')
        self.assertEqual(response.context['tag'].name, 'tests')
        self.assertEqual(response.context['extra'], 'context')

########NEW FILE########
__FILENAME__ = utils
"""Utils for Zinnia's tests"""
try:
    from urllib.parse import parse_qs
    from urllib.parse import urlparse
    from xmlrpc.client import Transport
except ImportError:  # Python 2
    from urlparse import parse_qs
    from urlparse import urlparse
    from xmlrpclib import Transport
from datetime import datetime as original_datetime

from django.utils import six
from django.conf import settings
from django.utils import timezone
from django.test.client import Client


class TestTransport(Transport):
    """
    Handles connections to XML-RPC server through Django test client.
    """

    def __init__(self, *args, **kwargs):
        Transport.__init__(self, *args, **kwargs)
        self.client = Client()

    def request(self, host, handler, request_body, verbose=0):
        self.verbose = verbose
        response = self.client.post(handler,
                                    request_body,
                                    content_type="text/xml")
        res = six.BytesIO(response.content)
        setattr(res, 'getheader', lambda *args: '')  # For Python >= 2.7
        res.seek(0)
        return self.parse_response(res)


def omniscient_datetime(*args):
    """
    Generating a datetime aware or naive depending of USE_TZ.
    """
    d = original_datetime(*args)
    if settings.USE_TZ:
        d = timezone.make_aware(d, timezone.utc)
    return d

datetime = omniscient_datetime


def is_lib_available(library):
    """
    Check if a Python library is available.
    """
    try:
        __import__(library)
        return True
    except ImportError:
        return False


def urlEqual(url_1, url_2):
    """
    Compare two URLs with query string where
    ordering does not matter.
    """
    parse_result_1 = urlparse(url_1)
    parse_result_2 = urlparse(url_2)

    return (parse_result_1[:4] == parse_result_2[:4] and
            parse_qs(parse_result_1[5]) == parse_qs(parse_result_2[5]))

########NEW FILE########
__FILENAME__ = archives
"""Urls for the Zinnia archives"""
from django.conf.urls import url
from django.conf.urls import patterns

from zinnia.urls import _
from zinnia.views.archives import EntryDay
from zinnia.views.archives import EntryWeek
from zinnia.views.archives import EntryYear
from zinnia.views.archives import EntryMonth
from zinnia.views.archives import EntryToday
from zinnia.views.archives import EntryIndex


index_patterns = [
    url(r'^$',
        EntryIndex.as_view(),
        name='entry_archive_index'),
    url(_(r'^page/(?P<page>\d+)/$'),
        EntryIndex.as_view(),
        name='entry_archive_index_paginated')
]

year_patterns = [
    url(r'^(?P<year>\d{4})/$',
        EntryYear.as_view(),
        name='entry_archive_year'),
    url(_(r'^(?P<year>\d{4})/page/(?P<page>\d+)/$'),
        EntryYear.as_view(),
        name='entry_archive_year_paginated'),
]

week_patterns = [
    url(_(r'^(?P<year>\d{4})/week/(?P<week>\d+)/$'),
        EntryWeek.as_view(),
        name='entry_archive_week'),
    url(_(r'^(?P<year>\d{4})/week/(?P<week>\d+)/page/(?P<page>\d+)/$'),
        EntryWeek.as_view(),
        name='entry_archive_week_paginated'),
]

month_patterns = [
    url(r'^(?P<year>\d{4})/(?P<month>\d{2})/$',
        EntryMonth.as_view(),
        name='entry_archive_month'),
    url(_(r'^(?P<year>\d{4})/(?P<month>\d{2})/page/(?P<page>\d+)/$'),
        EntryMonth.as_view(),
        name='entry_archive_month_paginated'),
]

day_patterns = [
    url(r'^(?P<year>\d{4})/(?P<month>\d{2})/(?P<day>\d{2})/$',
        EntryDay.as_view(),
        name='entry_archive_day'),
    url(_(r'^(?P<year>\d{4})/(?P<month>\d{2})/'
          '(?P<day>\d{2})/page/(?P<page>\d+)/$'),
        EntryDay.as_view(),
        name='entry_archive_day_paginated'),
]

today_patterns = [
    url(_(r'^today/$'),
        EntryToday.as_view(),
        name='entry_archive_today'),
    url(_(r'^today/page/(?P<page>\d+)/$'),
        EntryToday.as_view(),
        name='entry_archive_today_paginated'),
]

archive_patterns = (index_patterns + year_patterns +
                    week_patterns + month_patterns +
                    day_patterns + today_patterns)

urlpatterns = patterns(
    '', *archive_patterns
)

########NEW FILE########
__FILENAME__ = authors
"""Urls for the Zinnia authors"""
from django.conf.urls import url
from django.conf.urls import patterns

from zinnia.urls import _
from zinnia.views.authors import AuthorList
from zinnia.views.authors import AuthorDetail


urlpatterns = patterns(
    '',
    url(r'^$',
        AuthorList.as_view(),
        name='author_list'),
    url(_(r'^(?P<username>[.+-@\w]+)/page/(?P<page>\d+)/$'),
        AuthorDetail.as_view(),
        name='author_detail_paginated'),
    url(r'^(?P<username>[.+-@\w]+)/$',
        AuthorDetail.as_view(),
        name='author_detail'),
)

########NEW FILE########
__FILENAME__ = capabilities
"""Urls for the zinnia capabilities"""
from django.conf.urls import url
from django.conf.urls import patterns

from zinnia.views.capabilities import RsdXml
from zinnia.views.capabilities import HumansTxt
from zinnia.views.capabilities import OpenSearchXml
from zinnia.views.capabilities import WLWManifestXml


urlpatterns = patterns(
    '',
    url(r'^rsd.xml$', RsdXml.as_view(),
        name='rsd'),
    url(r'^humans.txt$', HumansTxt.as_view(),
        name='humans'),
    url(r'^opensearch.xml$', OpenSearchXml.as_view(),
        name='opensearch'),
    url(r'^wlwmanifest.xml$', WLWManifestXml.as_view(),
        name='wlwmanifest')
)

########NEW FILE########
__FILENAME__ = categories
"""Urls for the Zinnia categories"""
from django.conf.urls import url
from django.conf.urls import patterns

from zinnia.urls import _
from zinnia.views.categories import CategoryList
from zinnia.views.categories import CategoryDetail


urlpatterns = patterns(
    '',
    url(r'^$',
        CategoryList.as_view(),
        name='category_list'),
    url(_(r'^(?P<path>[-\/\w]+)/page/(?P<page>\d+)/$'),
        CategoryDetail.as_view(),
        name='category_detail_paginated'),
    url(r'^(?P<path>[-\/\w]+)/$',
        CategoryDetail.as_view(),
        name='category_detail'),
)

########NEW FILE########
__FILENAME__ = comments
"""Urls for the Zinnia comments"""
from django.conf.urls import url
from django.conf.urls import patterns

from zinnia.urls import _
from zinnia.views.comments import CommentSuccess


urlpatterns = patterns(
    '',
    url(_(r'^success/$'),
        CommentSuccess.as_view(),
        name='comment_success')
)

########NEW FILE########
__FILENAME__ = entries
"""Urls for the Zinnia entries"""
from django.conf.urls import url
from django.conf.urls import patterns

from zinnia.views.entries import EntryDetail


urlpatterns = patterns(
    '',
    url(r'^(?P<year>\d{4})/(?P<month>\d{2})/(?P<day>\d{2})/(?P<slug>[-\w]+)/$',
        EntryDetail.as_view(),
        name='entry_detail'),
)

########NEW FILE########
__FILENAME__ = feeds
"""Urls for the Zinnia feeds"""
from django.conf.urls import url
from django.conf.urls import patterns

from zinnia.urls import _
from zinnia.feeds import LatestEntries
from zinnia.feeds import TagEntries
from zinnia.feeds import AuthorEntries
from zinnia.feeds import CategoryEntries
from zinnia.feeds import SearchEntries
from zinnia.feeds import EntryComments
from zinnia.feeds import EntryPingbacks
from zinnia.feeds import EntryTrackbacks
from zinnia.feeds import EntryDiscussions
from zinnia.feeds import LatestDiscussions


urlpatterns = patterns(
    '',
    url(r'^$',
        LatestEntries(),
        name='entry_latest_feed'),
    url(_(r'^discussions/$'),
        LatestDiscussions(),
        name='discussion_latest_feed'),
    url(_(r'^search/$'),
        SearchEntries(),
        name='entry_search_feed'),
    url(_(r'^tags/(?P<tag>[^/]+(?u))/$'),
        TagEntries(),
        name='tag_feed'),
    url(_(r'^authors/(?P<username>[.+-@\w]+)/$'),
        AuthorEntries(),
        name='author_feed'),
    url(_(r'^categories/(?P<path>[-\/\w]+)/$'),
        CategoryEntries(),
        name='category_feed'),
    url(_(r'^discussions/(?P<year>\d{4})/(?P<month>\d{2})/'
          '(?P<day>\d{2})/(?P<slug>[-\w]+)/$'),
        EntryDiscussions(),
        name='entry_discussion_feed'),
    url(_(r'^comments/(?P<year>\d{4})/(?P<month>\d{2})/'
          '(?P<day>\d{2})/(?P<slug>[-\w]+)/$'),
        EntryComments(),
        name='entry_comment_feed'),
    url(_(r'^pingbacks/(?P<year>\d{4})/(?P<month>\d{2})/'
        '(?P<day>\d{2})/(?P<slug>[-\w]+)/$'),
        EntryPingbacks(),
        name='entry_pingback_feed'),
    url(_(r'^trackbacks/(?P<year>\d{4})/(?P<month>\d{2})/'
        '(?P<day>\d{2})/(?P<slug>[-\w]+)/$'),
        EntryTrackbacks(),
        name='entry_trackback_feed'),
)

########NEW FILE########
__FILENAME__ = quick_entry
"""Url for the Zinnia quick entry view"""
from django.conf.urls import url
from django.conf.urls import patterns

from zinnia.urls import _
from zinnia.views.quick_entry import QuickEntry


urlpatterns = patterns(
    '',
    url(_(r'^quick-entry/$'),
        QuickEntry.as_view(),
        name='entry_quick_post')
)

########NEW FILE########
__FILENAME__ = random
"""Urls for Zinnia random entries"""
from django.conf.urls import url
from django.conf.urls import patterns

from zinnia.views.random import EntryRandom


urlpatterns = patterns(
    '',
    url(r'^$',
        EntryRandom.as_view(),
        name='entry_random'),
)

########NEW FILE########
__FILENAME__ = search
"""Urls for the Zinnia search"""
from django.conf.urls import url
from django.conf.urls import patterns

from zinnia.views.search import EntrySearch


urlpatterns = patterns(
    '',
    url(r'^$', EntrySearch.as_view(),
        name='entry_search'),
)

########NEW FILE########
__FILENAME__ = shortlink
"""Urls for the Zinnia entries short link"""
from django.conf.urls import url
from django.conf.urls import patterns

from zinnia.views.shortlink import EntryShortLink


urlpatterns = patterns(
    '',
    url(r'^(?P<token>[\dA-Z]+)/$',
        EntryShortLink.as_view(),
        name='entry_shortlink'),
)

########NEW FILE########
__FILENAME__ = sitemap
"""Urls for the Zinnia sitemap"""
from django.conf.urls import url
from django.conf.urls import patterns

from zinnia.views.sitemap import Sitemap


urlpatterns = patterns(
    '',
    url(r'^$', Sitemap.as_view(),
        name='sitemap'),
)

########NEW FILE########
__FILENAME__ = tags
"""Urls for the Zinnia tags"""
from django.conf.urls import url
from django.conf.urls import patterns

from zinnia.urls import _
from zinnia.views.tags import TagList
from zinnia.views.tags import TagDetail


urlpatterns = patterns(
    '',
    url(r'^$',
        TagList.as_view(),
        name='tag_list'),
    url(r'^(?P<tag>[^/]+(?u))/$',
        TagDetail.as_view(),
        name='tag_detail'),
    url(_(r'^(?P<tag>[^/]+(?u))/page/(?P<page>\d+)/$'),
        TagDetail.as_view(),
        name='tag_detail_paginated'),
)

########NEW FILE########
__FILENAME__ = trackback
"""Urls for the Zinnia trackback"""
from django.conf.urls import url
from django.conf.urls import patterns

from zinnia.views.trackback import EntryTrackback


urlpatterns = patterns(
    '',
    url(r'^(?P<pk>\d+)/$',
        EntryTrackback.as_view(),
        name='entry_trackback'),
)

########NEW FILE########
__FILENAME__ = default
"""Default URL shortener backend for Zinnia"""
import string

from django.contrib.sites.models import Site
from django.core.urlresolvers import reverse

from zinnia.settings import PROTOCOL

BASE36_ALPHABET = string.digits + string.ascii_uppercase


def base36(value):
    """
    Encode int to base 36.
    """
    result = ''
    while value:
        value, i = divmod(value, 36)
        result = BASE36_ALPHABET[i] + result
    return result


def backend(entry):
    """
    Default URL shortener backend for Zinnia.
    """
    return '%s://%s%s' % (
        PROTOCOL, Site.objects.get_current().domain,
        reverse('zinnia:entry_shortlink', args=[base36(entry.pk)]))

########NEW FILE########
__FILENAME__ = archives
"""Views for Zinnia archives"""
import datetime

from django.utils import timezone
from django.views.generic.dates import BaseArchiveIndexView
from django.views.generic.dates import BaseYearArchiveView
from django.views.generic.dates import BaseMonthArchiveView
from django.views.generic.dates import BaseWeekArchiveView
from django.views.generic.dates import BaseDayArchiveView
from django.views.generic.dates import BaseTodayArchiveView

from zinnia.models.entry import Entry
from zinnia.views.mixins.archives import ArchiveMixin
from zinnia.views.mixins.archives import PreviousNextPublishedMixin
from zinnia.views.mixins.callable_queryset import CallableQuerysetMixin
from zinnia.views.mixins.prefetch_related import PrefetchCategoriesAuthorsMixin
from zinnia.views.mixins.templates import \
    EntryQuerysetArchiveTemplateResponseMixin
from zinnia.views.mixins.templates import \
    EntryQuerysetArchiveTodayTemplateResponseMixin


class EntryArchiveMixin(ArchiveMixin,
                        PreviousNextPublishedMixin,
                        PrefetchCategoriesAuthorsMixin,
                        CallableQuerysetMixin,
                        EntryQuerysetArchiveTemplateResponseMixin):
    """
    Mixin combinating:

    - ArchiveMixin configuration centralizing conf for archive views.
    - PrefetchCategoriesAuthorsMixin to prefetch related objects.
    - PreviousNextPublishedMixin for returning published archives.
    - CallableQueryMixin to force the update of the queryset.
    - EntryQuerysetArchiveTemplateResponseMixin to provide a
      custom templates for archives.
    """
    queryset = Entry.published.all


class EntryIndex(EntryArchiveMixin,
                 EntryQuerysetArchiveTodayTemplateResponseMixin,
                 BaseArchiveIndexView):
    """
    View returning the archive index.
    """
    context_object_name = 'entry_list'


class EntryYear(EntryArchiveMixin, BaseYearArchiveView):
    """
    View returning the archives for a year.
    """
    make_object_list = True
    template_name_suffix = '_archive_year'


class EntryMonth(EntryArchiveMixin, BaseMonthArchiveView):
    """
    View returning the archives for a month.
    """
    template_name_suffix = '_archive_month'


class EntryWeek(EntryArchiveMixin, BaseWeekArchiveView):
    """
    View returning the archive for a week.
    """
    template_name_suffix = '_archive_week'

    def get_dated_items(self):
        """
        Override get_dated_items to add a useful 'week_end_day'
        variable in the extra context of the view.
        """
        self.date_list, self.object_list, extra_context = super(
            EntryWeek, self).get_dated_items()
        self.date_list = self.get_date_list(self.object_list, 'day')
        extra_context['week_end_day'] = extra_context[
            'week'] + datetime.timedelta(days=6)
        return self.date_list, self.object_list, extra_context


class EntryDay(EntryArchiveMixin, BaseDayArchiveView):
    """
    View returning the archive for a day.
    """
    template_name_suffix = '_archive_day'


class EntryToday(EntryArchiveMixin, BaseTodayArchiveView):
    """
    View returning the archive for the current day.
    """
    template_name_suffix = '_archive_today'

    def get_dated_items(self):
        """
        Return (date_list, items, extra_context) for this request.
        And defines self.year/month/day for
        EntryQuerysetArchiveTemplateResponseMixin.
        """
        today = timezone.now()
        if timezone.is_aware(today):
            today = timezone.localtime(today)
        self.year, self.month, self.day = today.date().isoformat().split('-')
        return self._get_dated_items(today)

########NEW FILE########
__FILENAME__ = authors
"""Views for Zinnia authors"""
from django.db.models import Count
from django.shortcuts import get_object_or_404
from django.views.generic.list import ListView
from django.views.generic.list import BaseListView

from zinnia.settings import PAGINATION
from zinnia.models.author import Author
from zinnia.views.mixins.templates import EntryQuerysetTemplateResponseMixin
from zinnia.views.mixins.prefetch_related import PrefetchCategoriesAuthorsMixin


class AuthorList(ListView):
    """
    View returning a list of all published authors.
    """

    def get_queryset(self):
        """
        Return a queryset of published authors,
        with a count of their entries published.
        """
        return Author.published.all().annotate(
            count_entries_published=Count('entries'))


class BaseAuthorDetail(object):
    """
    Mixin providing the behavior of the author detail view,
    by returning in the context the current author and a
    queryset containing the entries written by author.
    """

    def get_queryset(self):
        """
        Retrieve the author by his username and
        build a queryset of his published entries.
        """
        self.author = get_object_or_404(
            Author, **{Author.USERNAME_FIELD: self.kwargs['username']})
        return self.author.entries_published()

    def get_context_data(self, **kwargs):
        """
        Add the current author in context.
        """
        context = super(BaseAuthorDetail, self).get_context_data(**kwargs)
        context['author'] = self.author
        return context


class AuthorDetail(EntryQuerysetTemplateResponseMixin,
                   PrefetchCategoriesAuthorsMixin,
                   BaseAuthorDetail,
                   BaseListView):
    """
    Detailed view for an Author combinating these mixins:

    - EntryQuerysetTemplateResponseMixin to provide custom templates
      for the author display page.
    - PrefetchCategoriesAuthorsMixin to prefetch related Categories
      and Authors to belonging the entry list.
    - BaseAuthorDetail to provide the behavior of the view.
    - BaseListView to implement the ListView.
    """
    model_type = 'author'
    paginate_by = PAGINATION

    def get_model_name(self):
        """
        The model name is the author's username.
        """
        return self.author.get_username()

########NEW FILE########
__FILENAME__ = capabilities
"""Views for Zinnia capabilities"""
from django.contrib.sites.models import Site
from django.views.generic.base import TemplateView

from zinnia.settings import PROTOCOL
from zinnia.settings import COPYRIGHT
from zinnia.settings import FEEDS_FORMAT


class CapabilityView(TemplateView):
    """
    Base view for the weblog capabilities.
    """

    def get_context_data(self, **kwargs):
        """
        Populate the context of the template
        with technical informations for building urls.
        """
        context = super(CapabilityView, self).get_context_data(**kwargs)
        context.update({'protocol': PROTOCOL,
                        'copyright': COPYRIGHT,
                        'feeds_format': FEEDS_FORMAT,
                        'site': Site.objects.get_current()})
        return context


class HumansTxt(CapabilityView):
    """
    http://humanstxt.org/
    """
    content_type = 'text/plain'
    template_name = 'zinnia/humans.txt'


class RsdXml(CapabilityView):
    """
    http://en.wikipedia.org/wiki/Really_Simple_Discovery
    """
    content_type = 'application/rsd+xml'
    template_name = 'zinnia/rsd.xml'


class WLWManifestXml(CapabilityView):
    """
    http://msdn.microsoft.com/en-us/library/bb463260.aspx
    """
    content_type = 'application/wlwmanifest+xml'
    template_name = 'zinnia/wlwmanifest.xml'


class OpenSearchXml(CapabilityView):
    """
    http://www.opensearch.org/
    """
    content_type = 'application/opensearchdescription+xml'
    template_name = 'zinnia/opensearch.xml'

########NEW FILE########
__FILENAME__ = categories
"""Views for Zinnia categories"""
from django.shortcuts import get_object_or_404
from django.views.generic.list import ListView
from django.views.generic.list import BaseListView

from zinnia.models.category import Category
from zinnia.settings import PAGINATION
from zinnia.views.mixins.templates import EntryQuerysetTemplateResponseMixin
from zinnia.views.mixins.prefetch_related import PrefetchCategoriesAuthorsMixin


def get_category_or_404(path):
    """
    Retrieve a Category instance by a path.
    """
    path_bits = [p for p in path.split('/') if p]
    return get_object_or_404(Category, slug=path_bits[-1])


class CategoryList(ListView):
    """
    View returning a list of all the categories.
    """
    queryset = Category.objects.all()


class BaseCategoryDetail(object):
    """
    Mixin providing the behavior of the category detail view,
    by returning in the context the current category and a
    queryset containing the entries published under it.
    """

    def get_queryset(self):
        """
        Retrieve the category by his path and
        build a queryset of her published entries.
        """
        self.category = get_category_or_404(self.kwargs['path'])
        return self.category.entries_published()

    def get_context_data(self, **kwargs):
        """
        Add the current category in context.
        """
        context = super(BaseCategoryDetail, self).get_context_data(**kwargs)
        context['category'] = self.category
        return context


class CategoryDetail(EntryQuerysetTemplateResponseMixin,
                     PrefetchCategoriesAuthorsMixin,
                     BaseCategoryDetail,
                     BaseListView):
    """
    Detailed view for a Category combinating these mixins:

    - EntryQuerysetTemplateResponseMixin to provide custom templates
      for the category display page.
    - PrefetchCategoriesAuthorsMixin to prefetch related Categories
      and Authors to belonging the entry list.
    - BaseCategoryDetail to provide the behavior of the view.
    - BaseListView to implement the ListView.
    """
    model_type = 'category'
    paginate_by = PAGINATION

    def get_model_name(self):
        """
        The model name is the category's slug.
        """
        return self.category.slug

########NEW FILE########
__FILENAME__ = channels
"""Views for Zinnia channels"""
from django.views.generic.list import ListView

from zinnia.models.entry import Entry
from zinnia.settings import PAGINATION
from zinnia.views.mixins.prefetch_related import PrefetchCategoriesAuthorsMixin


class BaseEntryChannel(object):
    """
    Mixin for displaying a custom selection of entries
    based on a search query, useful to build SEO/SMO pages
    aggregating entries on a thematic or for building a
    custom homepage.
    """
    query = ''

    def get_queryset(self):
        """
        Override the get_queryset method to build
        the queryset with entry matching query.
        """
        return Entry.published.search(self.query)

    def get_context_data(self, **kwargs):
        """
        Add query in context.
        """
        context = super(BaseEntryChannel, self).get_context_data(**kwargs)
        context.update({'query': self.query})
        return context


class EntryChannel(PrefetchCategoriesAuthorsMixin,
                   BaseEntryChannel,
                   ListView):
    """
    Channel view for entries combinating these mixins:

    - PrefetchCategoriesAuthorsMixin to prefetch related Categories
      and Authors to belonging the entry list.
    - BaseEntryChannel to provide the behavior of the view.
    - ListView to implement the ListView and template name resolution.
    """
    paginate_by = PAGINATION

########NEW FILE########
__FILENAME__ = comments
"""Views for Zinnia comments"""
from django.template.defaultfilters import slugify
from django.http import HttpResponsePermanentRedirect
from django.core.exceptions import ObjectDoesNotExist
from django.views.generic.base import View
from django.views.generic.base import TemplateResponseMixin

import django_comments as comments


class CommentSuccess(TemplateResponseMixin, View):
    """
    View for handing the publication of a Comment on an Entry.
    Do a redirection if the comment is visible,
    else render a confirmation template.
    """
    template_name = 'comments/zinnia/entry/posted.html'

    def get_context_data(self, **kwargs):
        return {'comment': self.comment}

    def get(self, request, *args, **kwargs):
        self.comment = None

        if 'c' in request.GET:
            try:
                self.comment = comments.get_model().objects.get(
                    pk=request.GET['c'])
            except (ObjectDoesNotExist, ValueError):
                pass
        if self.comment and self.comment.is_public:
            return HttpResponsePermanentRedirect(
                self.comment.get_absolute_url(
                    '#comment-%(id)s-by-') + slugify(self.comment.user_name))

        context = self.get_context_data(**kwargs)
        return self.render_to_response(context)

########NEW FILE########
__FILENAME__ = entries
"""Views for Zinnia entries"""
from django.views.generic.dates import BaseDateDetailView

from zinnia.models.entry import Entry
from zinnia.views.mixins.archives import ArchiveMixin
from zinnia.views.mixins.entry_preview import EntryPreviewMixin
from zinnia.views.mixins.entry_protection import EntryProtectionMixin
from zinnia.views.mixins.callable_queryset import CallableQuerysetMixin
from zinnia.views.mixins.templates import EntryArchiveTemplateResponseMixin


class EntryDateDetail(ArchiveMixin,
                      EntryArchiveTemplateResponseMixin,
                      CallableQuerysetMixin,
                      BaseDateDetailView):
    """
    Mixin combinating:

    - ArchiveMixin configuration centralizing conf for archive views
    - EntryArchiveTemplateResponseMixin to provide a
      custom templates depending on the date
    - BaseDateDetailView to retrieve the entry with date and slug
    - CallableQueryMixin to defer the execution of the *queryset*
      property when imported
    """
    queryset = Entry.published.on_site


class EntryDetail(EntryPreviewMixin,
                  EntryProtectionMixin,
                  EntryDateDetail):
    """
    Detailled archive view for an Entry with password
    and login protections and restricted preview.
    """

########NEW FILE########
__FILENAME__ = archives
"""Mixins for Zinnia archive views"""
from datetime import datetime
from datetime import timedelta

from zinnia.settings import PAGINATION
from zinnia.settings import ALLOW_EMPTY
from zinnia.settings import ALLOW_FUTURE


class ArchiveMixin(object):
    """
    Mixin centralizing the configuration of the archives views.
    """
    paginate_by = PAGINATION
    allow_empty = ALLOW_EMPTY
    allow_future = ALLOW_FUTURE
    date_field = 'creation_date'
    month_format = '%m'
    week_format = '%W'


class PreviousNextPublishedMixin(object):
    """
    Mixin for correcting the previous/next
    context variable to return dates with published datas.
    """

    def get_previous_next_published(self, date):
        """
        Returns a dict of the next and previous date periods
        with published entries.
        """
        previous_next = getattr(self, 'previous_next', None)

        if previous_next is None:
            date_year = datetime(date.year, 1, 1)
            date_month = datetime(date.year, date.month, 1)
            date_day = datetime(date.year, date.month, date.day)
            date_next_week = date_day + timedelta(weeks=1)
            previous_next = {'year': [None, None],
                             'week': [None, None],
                             'month': [None, None],
                             'day':  [None, None]}
            dates = self.get_queryset().datetimes(
                'creation_date', 'day', order='ASC')
            for d in dates:
                d_year = datetime(d.year, 1, 1)
                d_month = datetime(d.year, d.month, 1)
                d_day = datetime(d.year, d.month, d.day)
                if d_year < date_year:
                    previous_next['year'][0] = d_year.date()
                elif d_year > date_year and not previous_next['year'][1]:
                    previous_next['year'][1] = d_year.date()
                if d_month < date_month:
                    previous_next['month'][0] = d_month.date()
                elif d_month > date_month and not previous_next['month'][1]:
                    previous_next['month'][1] = d_month.date()
                if d_day < date_day:
                    previous_next['day'][0] = d_day.date()
                    previous_next['week'][0] = d_day.date() - timedelta(
                        days=d_day.weekday())
                elif d_day > date_day and not previous_next['day'][1]:
                    previous_next['day'][1] = d_day.date()
                if d_day > date_next_week and not previous_next['week'][1]:
                    previous_next['week'][1] = d_day.date() - timedelta(
                        days=d_day.weekday())

            setattr(self, 'previous_next', previous_next)
        return previous_next

    def get_next_year(self, date):
        """
        Get the next year with published entries.
        """
        return self.get_previous_next_published(date)['year'][1]

    def get_previous_year(self, date):
        """
        Get the previous year with published entries.
        """
        return self.get_previous_next_published(date)['year'][0]

    def get_next_week(self, date):
        """
        Get the next week with published entries.
        """
        return self.get_previous_next_published(date)['week'][1]

    def get_previous_week(self, date):
        """
        Get the previous wek with published entries.
        """
        return self.get_previous_next_published(date)['week'][0]

    def get_next_month(self, date):
        """
        Get the next month with published entries.
        """
        return self.get_previous_next_published(date)['month'][1]

    def get_previous_month(self, date):
        """
        Get the previous month with published entries.
        """
        return self.get_previous_next_published(date)['month'][0]

    def get_next_day(self, date):
        """
        Get the next day with published entries.
        """
        return self.get_previous_next_published(date)['day'][1]

    def get_previous_day(self, date):
        """
        Get the previous day with published entries.
        """
        return self.get_previous_next_published(date)['day'][0]

########NEW FILE########
__FILENAME__ = callable_queryset
"""Callable Queryset mixins for Zinnia views"""
from django.core.exceptions import ImproperlyConfigured


class CallableQuerysetMixin(object):
    """
    Mixin for handling a callable queryset,
    which will force the update of the queryset.
    Related to issue http://code.djangoproject.com/ticket/8378
    """
    queryset = None

    def get_queryset(self):
        """
        Check that the queryset is defined and call it.
        """
        if self.queryset is None:
            raise ImproperlyConfigured(
                "'%s' must define 'queryset'" % self.__class__.__name__)
        return self.queryset()

########NEW FILE########
__FILENAME__ = entry_preview
"""Preview mixins for Zinnia views"""
from django.http import Http404
from django.utils.translation import ugettext as _

from zinnia.managers import PUBLISHED


class EntryPreviewMixin(object):
    """
    Mixin implementing the preview of Entries.
    """

    def get_object(self, queryset=None):
        """
        If the status of the entry is not PUBLISHED,
        a preview is requested, so we check if the user
        has the 'zinnia.can_view_all' permission or if
        it's an author of the entry.
        """
        obj = super(EntryPreviewMixin, self).get_object(queryset)
        if obj.status == PUBLISHED:
            return obj
        if (self.request.user.has_perm('zinnia.can_view_all') or
                self.request.user.pk in [
                author.pk for author in obj.authors.all()]):
            return obj
        raise Http404(_('No entry found matching the query'))

########NEW FILE########
__FILENAME__ = entry_protection
"""Protection mixins for Zinnia views"""
from django.contrib.auth.views import login


class LoginMixin(object):
    """
    Mixin implemeting a login view
    configurated for Zinnia.
    """

    def login(self):
        """
        Return the login view.
        """
        return login(self.request, 'zinnia/login.html')


class PasswordMixin(object):
    """
    Mixin implementing a password view
    configurated for Zinnia.
    """
    error = False

    def password(self):
        """
        Return the password view.
        """
        return self.response_class(request=self.request,
                                   template='zinnia/password.html',
                                   context={'error': self.error})


class EntryProtectionMixin(LoginMixin, PasswordMixin):
    """
    Mixin returning a login view if the current
    entry need authentication and password view
    if the entry is protected by a password.
    """
    session_key = 'zinnia_entry_%s_password'

    def get(self, request, *args, **kwargs):
        """
        Do the login and password protection.
        """
        response = super(EntryProtectionMixin, self).get(
            request, *args, **kwargs)
        if self.object.login_required and not request.user.is_authenticated():
            return self.login()
        if (self.object.password and self.object.password !=
                self.request.session.get(self.session_key % self.object.pk)):
            return self.password()
        return response

    def post(self, request, *args, **kwargs):
        """
        Do the login and password protection.
        """
        self.object = self.get_object()
        self.login()
        if self.object.password:
            entry_password = self.request.POST.get('entry_password')
            if entry_password:
                if entry_password == self.object.password:
                    self.request.session[self.session_key %
                                         self.object.pk] = self.object.password
                    return self.get(request, *args, **kwargs)
                else:
                    self.error = True
            return self.password()
        return self.get(request, *args, **kwargs)

########NEW FILE########
__FILENAME__ = prefetch_related
"""Mixins for enabling prefetching in views returning list of entries"""
from django.core.exceptions import ImproperlyConfigured


class PrefetchRelatedMixin(object):
    """
    Mixin allow you to provides list of relation names
    to be prefetching when the queryset is build.
    """
    relation_names = None

    def get_queryset(self):
        """
        Check if relation_names is correctly set and
        do a prefetch related on the queryset with it.
        """
        if self.relation_names is None:
            raise ImproperlyConfigured(
                "'%s' must define 'relation_names'" %
                self.__class__.__name__)
        if not isinstance(self.relation_names, (tuple, list)):
            raise ImproperlyConfigured(
                "%s's relation_names property must be a tuple or list." %
                self.__class__.__name__)
        return super(PrefetchRelatedMixin, self
                     ).get_queryset().prefetch_related(*self.relation_names)


class PrefetchCategoriesAuthorsMixin(PrefetchRelatedMixin):
    """
    Mixin for prefetching categories and authors related
    to the entries in the queryset.
    """
    relation_names = ('categories', 'authors')

########NEW FILE########
__FILENAME__ = templates
"""Template mixins for Zinnia views"""
from django.utils import timezone
from django.core.exceptions import ImproperlyConfigured
from django.views.generic.base import TemplateResponseMixin


class EntryQuerysetTemplateResponseMixin(TemplateResponseMixin):
    """
    Return a custom template name for views returning
    a queryset of Entry filtered by another model.
    """
    model_type = None
    model_name = None

    def get_model_type(self):
        """
        Return the model type for templates.
        """
        if self.model_type is None:
            raise ImproperlyConfigured(
                "%s requires either a definition of "
                "'model_type' or an implementation of 'get_model_type()'" %
                self.__class__.__name__)
        return self.model_type

    def get_model_name(self):
        """
        Return the model name for templates.
        """
        if self.model_name is None:
            raise ImproperlyConfigured(
                "%s requires either a definition of "
                "'model_name' or an implementation of 'get_model_name()'" %
                self.__class__.__name__)
        return self.model_name

    def get_template_names(self):
        """
        Return a list of template names to be used for the view.
        """
        model_type = self.get_model_type()
        model_name = self.get_model_name()

        templates = [
            'zinnia/%s/%s/entry_list.html' % (model_type, model_name),
            'zinnia/%s/%s_entry_list.html' % (model_type, model_name),
            'zinnia/%s/entry_list.html' % model_type,
            'zinnia/entry_list.html']

        if self.template_name is not None:
            templates.insert(0, self.template_name)

        return templates


class EntryQuerysetArchiveTemplateResponseMixin(TemplateResponseMixin):
    """
    Return a custom template name for the archive views based
    on the type of the archives and the value of the date.
    """
    template_name_suffix = '_archive'

    def get_archive_part_value(self, part):
        """
        Method for accessing to the value of
        self.get_year(), self.get_month(), etc methods
        if they exists.
        """
        try:
            return getattr(self, 'get_%s' % part)()
        except AttributeError:
            return None

    def get_default_base_template_names(self):
        """
        Return a list of default base templates used
        to build the full list of templates.
        """
        return ['entry%s.html' % self.template_name_suffix]

    def get_template_names(self):
        """
        Return a list of template names to be used for the view.
        """
        year = self.get_archive_part_value('year')
        week = self.get_archive_part_value('week')
        month = self.get_archive_part_value('month')
        day = self.get_archive_part_value('day')

        templates = []
        path = 'zinnia/archives'
        template_names = self.get_default_base_template_names()
        for template_name in template_names:
            templates.extend([template_name,
                              'zinnia/%s' % template_name,
                              '%s/%s' % (path, template_name)])
        if year:
            for template_name in template_names:
                templates.append(
                    '%s/%s/%s' % (path, year, template_name))
        if week:
            for template_name in template_names:
                templates.extend([
                    '%s/week/%s/%s' % (path, week, template_name),
                    '%s/%s/week/%s/%s' % (path, year, week, template_name)])
        if month:
            for template_name in template_names:
                templates.extend([
                    '%s/month/%s/%s' % (path, month, template_name),
                    '%s/%s/month/%s/%s' % (path, year, month, template_name)])
        if day:
            for template_name in template_names:
                templates.extend([
                    '%s/day/%s/%s' % (path, day, template_name),
                    '%s/%s/day/%s/%s' % (path, year, day, template_name),
                    '%s/month/%s/day/%s/%s' % (path, month, day,
                                               template_name),
                    '%s/%s/%s/%s/%s' % (path, year, month, day,
                                        template_name)])

        if self.template_name is not None:
            templates.append(self.template_name)

        templates.reverse()
        return templates


class EntryArchiveTemplateResponseMixin(
        EntryQuerysetArchiveTemplateResponseMixin):
    """
    Same as EntryQuerysetArchivetemplateResponseMixin
    but use the template defined in the Entry instance
    as the base template name.
    """

    def get_default_base_template_names(self):
        """
        Return the Entry.template value.
        """
        return [self.object.detail_template,
                '%s.html' % self.object.slug,
                '%s_%s' % (self.object.slug, self.object.detail_template)]


class EntryQuerysetArchiveTodayTemplateResponseMixin(
        EntryQuerysetArchiveTemplateResponseMixin):
    """
    Same as EntryQuerysetArchivetemplateResponseMixin
    but use the current date of the day when getting
    archive part values.
    """
    today = None

    def get_archive_part_value(self, part):
        """Return archive part for today"""
        parts_dict = {'year': '%Y',
                      'month': self.month_format,
                      'week': self.week_format,
                      'day': '%d'}
        if self.today is None:
            today = timezone.now()
            if timezone.is_aware(today):
                today = timezone.localtime(today)
            self.today = today
        return self.today.strftime(parts_dict[part])

########NEW FILE########
__FILENAME__ = quick_entry
"""Views for Zinnia quick entry"""
try:
    from urllib.parse import urlencode
except:  # Python 2
    from urllib import urlencode

from django import forms
from django.shortcuts import redirect
from django.utils.html import linebreaks
from django.views.generic.base import View
from django.utils.encoding import smart_str
from django.core.urlresolvers import reverse
from django.contrib.sites.models import Site
from django.template.defaultfilters import slugify
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import permission_required
from django.utils import timezone

from zinnia.models.entry import Entry
from zinnia.managers import DRAFT
from zinnia.managers import PUBLISHED
from zinnia.settings import MARKUP_LANGUAGE


class QuickEntryForm(forms.ModelForm):
    """
    Form for posting an entry quickly.
    """

    class Meta:
        model = Entry
        exclude = ('comment_count',
                   'pingback_count',
                   'trackback_count')


class QuickEntry(View):
    """
    View handling the quick post of a short Entry.
    """

    @method_decorator(permission_required('zinnia.add_entry'))
    def dispatch(self, *args, **kwargs):
        """
        Decorate the view dispatcher with permission_required.
        """
        return super(QuickEntry, self).dispatch(*args, **kwargs)

    def get(self, request, *args, **kwargs):
        """
        GET only do a redirection to the admin for adding and entry.
        """
        return redirect('admin:zinnia_entry_add')

    def post(self, request, *args, **kwargs):
        """
        Handle the datas for posting a quick entry,
        and redirect to the admin in case of error or
        to the entry's page in case of success.
        """
        data = {
            'title': request.POST.get('title'),
            'slug': slugify(request.POST.get('title')),
            'status': DRAFT if 'save_draft' in request.POST else PUBLISHED,
            'sites': [Site.objects.get_current().pk],
            'authors': [request.user.pk],
            'content_template': 'zinnia/_entry_detail.html',
            'detail_template': 'entry_detail.html',
            'creation_date': timezone.now(),
            'last_update': timezone.now(),
            'content': request.POST.get('content'),
            'tags': request.POST.get('tags')}
        form = QuickEntryForm(data)
        if form.is_valid():
            form.instance.content = self.htmlize(form.cleaned_data['content'])
            entry = form.save()
            return redirect(entry)

        data = {'title': smart_str(request.POST.get('title', '')),
                'content': smart_str(self.htmlize(
                    request.POST.get('content', ''))),
                'tags': smart_str(request.POST.get('tags', '')),
                'slug': slugify(request.POST.get('title', '')),
                'authors': request.user.pk,
                'sites': Site.objects.get_current().pk}
        return redirect('%s?%s' % (reverse('admin:zinnia_entry_add'),
                                   urlencode(data)))

    def htmlize(self, content):
        """
        Convert to HTML the content if the MARKUP_LANGUAGE
        is set to HTML to optimize the rendering and avoid
        ugly effect in WYMEditor.
        """
        if MARKUP_LANGUAGE == 'html':
            return linebreaks(content)
        return content

########NEW FILE########
__FILENAME__ = random
"""Views for Zinnia random entry"""
from django.views.generic.base import RedirectView

from zinnia.models.entry import Entry


class EntryRandom(RedirectView):
    """
    View for handling a random entry
    simply do a redirection after the random selection.
    """
    permanent = False

    def get_redirect_url(self, **kwargs):
        """
        Get entry corresponding to 'pk' and
        return the get_absolute_url of the entry.
        """
        entry = Entry.published.all().order_by('?')[0]
        return entry.get_absolute_url()

########NEW FILE########
__FILENAME__ = search
"""Views for Zinnia entries search"""
from django.views.generic.list import ListView
from django.utils.translation import ugettext as _

from zinnia.models.entry import Entry
from zinnia.settings import PAGINATION
from zinnia.views.mixins.prefetch_related import PrefetchCategoriesAuthorsMixin


class BaseEntrySearch(object):
    """
    Mixin providing the behavior of the entry search view,
    by returning in the context the pattern searched, the
    error if something wrong has happened and finally the
    the queryset of published entries matching the pattern.
    """
    pattern = ''
    error = None

    def get_queryset(self):
        """
        Overridde the get_queryset method to
        do some validations and build the search queryset.
        """
        entries = Entry.published.none()

        if self.request.GET:
            self.pattern = self.request.GET.get('pattern', '')
            if len(self.pattern) < 3:
                self.error = _('The pattern is too short')
            else:
                entries = Entry.published.search(self.pattern)
        else:
            self.error = _('No pattern to search found')
        return entries

    def get_context_data(self, **kwargs):
        """
        Add error and pattern in context.
        """
        context = super(BaseEntrySearch, self).get_context_data(**kwargs)
        context.update({'error': self.error, 'pattern': self.pattern})
        return context


class EntrySearch(PrefetchCategoriesAuthorsMixin,
                  BaseEntrySearch,
                  ListView):
    """
    Search view for entries combinating these mixins:

    - PrefetchCategoriesAuthorsMixin to prefetch related Categories
      and Authors to belonging the entry list.
    - BaseEntrySearch to provide the behavior of the view.
    - ListView to implement the ListView and template name resolution.
    """
    paginate_by = PAGINATION
    template_name_suffix = '_search'

########NEW FILE########
__FILENAME__ = shortlink
"""Views for Zinnia shortlink"""
from django.shortcuts import get_object_or_404
from django.views.generic.base import RedirectView

from zinnia.models.entry import Entry


class EntryShortLink(RedirectView):
    """
    View for handling the shortlink of an Entry,
    simply do a redirection.
    """

    def get_redirect_url(self, **kwargs):
        """
        Get entry corresponding to 'pk' encoded in base36
        in the 'token' variable and return the get_absolute_url
        of the entry.
        """
        entry = get_object_or_404(Entry, pk=int(kwargs['token'], 36))
        return entry.get_absolute_url()

########NEW FILE########
__FILENAME__ = sitemap
"""Views for Zinnia sitemap"""
from django.views.generic import TemplateView

from zinnia.models.entry import Entry
from zinnia.models.category import Category


class Sitemap(TemplateView):
    """
    Sitemap view of the Weblog.
    """
    template_name = 'zinnia/sitemap.html'

    def get_context_data(self, **kwargs):
        """
        Populate the context of the template
        with all published entries and all the categories.
        """
        context = super(Sitemap, self).get_context_data(**kwargs)
        context.update({'entries': Entry.published.all(),
                        'categories': Category.objects.all()})
        return context

########NEW FILE########
__FILENAME__ = tags
"""Views for Zinnia tags"""
from django.http import Http404
from django.views.generic.list import ListView
from django.views.generic.list import BaseListView
from django.template.defaultfilters import slugify
from django.utils.translation import ugettext as _

from tagging.utils import get_tag
from tagging.models import Tag
from tagging.models import TaggedItem

from zinnia.models.entry import Entry
from zinnia.settings import PAGINATION
from zinnia.views.mixins.templates import EntryQuerysetTemplateResponseMixin
from zinnia.views.mixins.prefetch_related import PrefetchCategoriesAuthorsMixin


class TagList(ListView):
    """
    View return a list of all published tags.
    """
    template_name = 'zinnia/tag_list.html'
    context_object_name = 'tag_list'

    def get_queryset(self):
        """
        Return a queryset of published tags,
        with a count of their entries published.
        """
        return Tag.objects.usage_for_queryset(
            Entry.published.all(), counts=True)


class BaseTagDetail(object):
    """
    Mixin providing the behavior of the tag detail view,
    by returning in the context the current tag and a
    queryset containing the entries published with the tag.
    """

    def get_queryset(self):
        """
        Retrieve the tag by his name and
        build a queryset of his published entries.
        """
        self.tag = get_tag(self.kwargs['tag'])
        if self.tag is None:
            raise Http404(_('No Tag found matching "%s".') %
                          self.kwargs['tag'])
        return TaggedItem.objects.get_by_model(
            Entry.published.all(), self.tag)

    def get_context_data(self, **kwargs):
        """
        Add the current tag in context.
        """
        context = super(BaseTagDetail, self).get_context_data(**kwargs)
        context['tag'] = self.tag
        return context


class TagDetail(EntryQuerysetTemplateResponseMixin,
                PrefetchCategoriesAuthorsMixin,
                BaseTagDetail,
                BaseListView):
    """
    Detailed view for a Tag combinating these mixins:

    - EntryQuerysetTemplateResponseMixin to provide custom templates
      for the tag display page.
    - PrefetchCategoriesAuthorsMixin to prefetch related Categories
      and Authors to belonging the entry list.
    - BaseTagDetail to provide the behavior of the view.
    - BaseListView to implement the ListView.
    """
    model_type = 'tag'
    paginate_by = PAGINATION

    def get_model_name(self):
        """
        The model name is the tag slugified.
        """
        return slugify(self.tag)

########NEW FILE########
__FILENAME__ = trackback
"""Views for Zinnia trackback"""
from django.utils import timezone
from django.contrib.sites.models import Site
from django.shortcuts import get_object_or_404
from django.views.generic.base import TemplateView
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.http import HttpResponsePermanentRedirect
from django.contrib.contenttypes.models import ContentType

import django_comments as comments

from zinnia.models.entry import Entry
from zinnia.flags import TRACKBACK
from zinnia.flags import get_user_flagger
from zinnia.signals import trackback_was_posted


class EntryTrackback(TemplateView):
    """
    View for handling trackbacks on the entries.
    """
    content_type = 'text/xml'
    template_name = 'zinnia/entry_trackback.xml'

    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        """
        Decorate the view dispatcher with csrf_exempt.
        """
        return super(EntryTrackback, self).dispatch(*args, **kwargs)

    def get_object(self):
        """
        Retrieve the Entry trackbacked.
        """
        return get_object_or_404(Entry.published, pk=self.kwargs['pk'])

    def get(self, request, *args, **kwargs):
        """
        GET only do a permanent redirection to the Entry.
        """
        entry = self.get_object()
        return HttpResponsePermanentRedirect(entry.get_absolute_url())

    def post(self, request, *args, **kwargs):
        """
        Check if an URL is provided and if trackbacks
        are enabled on the Entry.
        If so the URL is registered one time as a trackback.
        """
        url = request.POST.get('url')

        if not url:
            return self.get(request, *args, **kwargs)

        entry = self.get_object()
        site = Site.objects.get_current()

        if not entry.trackbacks_are_open:
            return self.render_to_response(
                {'error': 'Trackback is not enabled for %s' % entry.title})

        title = request.POST.get('title') or url
        excerpt = request.POST.get('excerpt') or title
        blog_name = request.POST.get('blog_name') or title
        ip_address = request.META.get('REMOTE_ADDR', None)

        trackback, created = comments.get_model().objects.get_or_create(
            content_type=ContentType.objects.get_for_model(Entry),
            object_pk=entry.pk, site=site, user_url=url,
            user_name=blog_name, ip_address=ip_address,
            defaults={'comment': excerpt,
                      'submit_date': timezone.now()})
        if created:
            trackback.flags.create(user=get_user_flagger(), flag=TRACKBACK)
            trackback_was_posted.send(trackback.__class__,
                                      trackback=trackback,
                                      entry=entry)
        else:
            return self.render_to_response(
                {'error': 'Trackback is already registered'})
        return self.render_to_response({})

########NEW FILE########
__FILENAME__ = metaweblog
"""XML-RPC methods of Zinnia metaWeblog API"""
import os
from datetime import datetime
try:
    from xmlrpc.client import Fault
    from xmlrpc.client import DateTime
except ImportError:  # Python 2
    from xmlrpclib import Fault
    from xmlrpclib import DateTime

from django.utils import six
from django.conf import settings
from django.utils import timezone
from django.contrib.sites.models import Site
from django.core.urlresolvers import reverse
from django.utils.translation import gettext as _
from django.utils.text import Truncator
from django.utils.html import strip_tags
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.template.defaultfilters import slugify

from tagging.models import Tag

from django_xmlrpc.decorators import xmlrpc_func

from zinnia.models.entry import Entry
from zinnia.models.author import Author
from zinnia.models.category import Category
from zinnia.settings import PROTOCOL
from zinnia.settings import UPLOAD_TO
from zinnia.managers import DRAFT, PUBLISHED


# http://docs.nucleuscms.org/blog/12#errorcodes
LOGIN_ERROR = 801
PERMISSION_DENIED = 803


def authenticate(username, password, permission=None):
    """
    Authenticate staff_user with permission.
    """
    try:
        author = Author.objects.get(
            **{'%s__exact' % Author.USERNAME_FIELD: username})
    except Author.DoesNotExist:
        raise Fault(LOGIN_ERROR, _('Username is incorrect.'))
    if not author.check_password(password):
        raise Fault(LOGIN_ERROR, _('Password is invalid.'))
    if not author.is_staff or not author.is_active:
        raise Fault(PERMISSION_DENIED, _('User account unavailable.'))
    if permission:
        if not author.has_perm(permission):
            raise Fault(PERMISSION_DENIED, _('User cannot %s.') % permission)
    return author


def blog_structure(site):
    """
    A blog structure.
    """
    return {'blogid': settings.SITE_ID,
            'blogName': site.name,
            'url': '%s://%s%s' % (
                PROTOCOL, site.domain,
                reverse('zinnia:entry_archive_index'))}


def user_structure(user, site):
    """
    An user structure.
    """
    full_name = user.get_full_name().split()
    first_name = full_name[0]
    try:
        last_name = full_name[1]
    except IndexError:
        last_name = ''
    return {'userid': user.pk,
            'email': user.email,
            'nickname': user.get_username(),
            'lastname': last_name,
            'firstname': first_name,
            'url': '%s://%s%s' % (
                PROTOCOL, site.domain,
                user.get_absolute_url())}


def author_structure(user):
    """
    An author structure.
    """
    return {'user_id': user.pk,
            'user_login': user.get_username(),
            'display_name': user.__str__(),
            'user_email': user.email}


def category_structure(category, site):
    """
    A category structure.
    """
    return {'description': category.title,
            'htmlUrl': '%s://%s%s' % (
                PROTOCOL, site.domain,
                category.get_absolute_url()),
            'rssUrl': '%s://%s%s' % (
                PROTOCOL, site.domain,
                reverse('zinnia:category_feed', args=[category.tree_path])),
            # Useful Wordpress Extensions
            'categoryId': category.pk,
            'parentId': category.parent and category.parent.pk or 0,
            'categoryDescription': category.description,
            'categoryName': category.title}


def tag_structure(tag, site):
    """
    A tag structure.
    """
    return {'tag_id': tag.pk,
            'name': tag.name,
            'count': tag.count,
            'slug': tag.name,
            'html_url': '%s://%s%s' % (
                PROTOCOL, site.domain,
                reverse('zinnia:tag_detail', args=[tag.name])),
            'rss_url': '%s://%s%s' % (
                PROTOCOL, site.domain,
                reverse('zinnia:tag_feed', args=[tag.name]))
            }


def post_structure(entry, site):
    """
    A post structure with extensions.
    """
    author = entry.authors.all()[0]
    return {'title': entry.title,
            'description': six.text_type(entry.html_content),
            'link': '%s://%s%s' % (PROTOCOL, site.domain,
                                   entry.get_absolute_url()),
            # Basic Extensions
            'permaLink': '%s://%s%s' % (PROTOCOL, site.domain,
                                        entry.get_absolute_url()),
            'categories': [cat.title for cat in entry.categories.all()],
            'dateCreated': DateTime(entry.creation_date.isoformat()),
            'postid': entry.pk,
            'userid': author.get_username(),
            # Useful Movable Type Extensions
            'mt_excerpt': entry.excerpt,
            'mt_allow_comments': int(entry.comment_enabled),
            'mt_allow_pings': (int(entry.pingback_enabled) or
                               int(entry.trackback_enabled)),
            'mt_keywords': entry.tags,
            # Useful Wordpress Extensions
            'wp_author': author.get_username(),
            'wp_author_id': author.pk,
            'wp_author_display_name': author.__str__(),
            'wp_password': entry.password,
            'wp_slug': entry.slug,
            'sticky': entry.featured}


@xmlrpc_func(returns='struct[]', args=['string', 'string', 'string'])
def get_users_blogs(apikey, username, password):
    """
    blogger.getUsersBlogs(api_key, username, password)
    => blog structure[]
    """
    authenticate(username, password)
    site = Site.objects.get_current()
    return [blog_structure(site)]


@xmlrpc_func(returns='struct', args=['string', 'string', 'string'])
def get_user_info(apikey, username, password):
    """
    blogger.getUserInfo(api_key, username, password)
    => user structure
    """
    user = authenticate(username, password)
    site = Site.objects.get_current()
    return user_structure(user, site)


@xmlrpc_func(returns='struct[]', args=['string', 'string', 'string'])
def get_authors(apikey, username, password):
    """
    wp.getAuthors(api_key, username, password)
    => author structure[]
    """
    authenticate(username, password)
    return [author_structure(author)
            for author in Author.objects.filter(is_staff=True)]


@xmlrpc_func(returns='boolean', args=['string', 'string',
                                      'string', 'string', 'string'])
def delete_post(apikey, post_id, username, password, publish):
    """
    blogger.deletePost(api_key, post_id, username, password, 'publish')
    => boolean
    """
    user = authenticate(username, password, 'zinnia.delete_entry')
    entry = Entry.objects.get(id=post_id, authors=user)
    entry.delete()
    return True


@xmlrpc_func(returns='struct', args=['string', 'string', 'string'])
def get_post(post_id, username, password):
    """
    metaWeblog.getPost(post_id, username, password)
    => post structure
    """
    user = authenticate(username, password)
    site = Site.objects.get_current()
    return post_structure(Entry.objects.get(id=post_id, authors=user), site)


@xmlrpc_func(returns='struct[]',
             args=['string', 'string', 'string', 'integer'])
def get_recent_posts(blog_id, username, password, number):
    """
    metaWeblog.getRecentPosts(blog_id, username, password, number)
    => post structure[]
    """
    user = authenticate(username, password)
    site = Site.objects.get_current()
    return [post_structure(entry, site)
            for entry in Entry.objects.filter(authors=user)[:number]]


@xmlrpc_func(returns='struct[]', args=['string', 'string', 'string'])
def get_tags(blog_id, username, password):
    """
    wp.getTags(blog_id, username, password)
    => tag structure[]
    """
    authenticate(username, password)
    site = Site.objects.get_current()
    return [tag_structure(tag, site)
            for tag in Tag.objects.usage_for_queryset(
                Entry.published.all(), counts=True)]


@xmlrpc_func(returns='struct[]', args=['string', 'string', 'string'])
def get_categories(blog_id, username, password):
    """
    metaWeblog.getCategories(blog_id, username, password)
    => category structure[]
    """
    authenticate(username, password)
    site = Site.objects.get_current()
    return [category_structure(category, site)
            for category in Category.objects.all()]


@xmlrpc_func(returns='string', args=['string', 'string', 'string', 'struct'])
def new_category(blog_id, username, password, category_struct):
    """
    wp.newCategory(blog_id, username, password, category)
    => category_id
    """
    authenticate(username, password, 'zinnia.add_category')
    category_dict = {'title': category_struct['name'],
                     'description': category_struct['description'],
                     'slug': category_struct['slug']}
    if int(category_struct['parent_id']):
        category_dict['parent'] = Category.objects.get(
            pk=category_struct['parent_id'])
    category = Category.objects.create(**category_dict)

    return category.pk


@xmlrpc_func(returns='string', args=['string', 'string', 'string',
                                     'struct', 'boolean'])
def new_post(blog_id, username, password, post, publish):
    """
    metaWeblog.newPost(blog_id, username, password, post, publish)
    => post_id
    """
    user = authenticate(username, password, 'zinnia.add_entry')
    if post.get('dateCreated'):
        creation_date = datetime.strptime(
            post['dateCreated'].value[:18], '%Y-%m-%dT%H:%M:%S')
        if settings.USE_TZ:
            creation_date = timezone.make_aware(
                creation_date, timezone.utc)
    else:
        creation_date = timezone.now()

    entry_dict = {'title': post['title'],
                  'content': post['description'],
                  'excerpt': post.get('mt_excerpt', Truncator(
                      strip_tags(post['description'])).words(50)),
                  'creation_date': creation_date,
                  'last_update': creation_date,
                  'comment_enabled': post.get('mt_allow_comments', 1) == 1,
                  'pingback_enabled': post.get('mt_allow_pings', 1) == 1,
                  'trackback_enabled': post.get('mt_allow_pings', 1) == 1,
                  'featured': post.get('sticky', 0) == 1,
                  'tags': 'mt_keywords' in post and post['mt_keywords'] or '',
                  'slug': 'wp_slug' in post and post['wp_slug'] or slugify(
                      post['title']),
                  'password': post.get('wp_password', '')}
    if user.has_perm('zinnia.can_change_status'):
        entry_dict['status'] = publish and PUBLISHED or DRAFT

    entry = Entry.objects.create(**entry_dict)

    author = user
    if 'wp_author_id' in post and user.has_perm('zinnia.can_change_author'):
        if int(post['wp_author_id']) != user.pk:
            author = Author.objects.get(pk=post['wp_author_id'])
    entry.authors.add(author)

    entry.sites.add(Site.objects.get_current())
    if 'categories' in post:
        entry.categories.add(*[
            Category.objects.get_or_create(
                title=cat, slug=slugify(cat))[0]
            for cat in post['categories']])

    return entry.pk


@xmlrpc_func(returns='boolean', args=['string', 'string', 'string',
                                      'struct', 'boolean'])
def edit_post(post_id, username, password, post, publish):
    """
    metaWeblog.editPost(post_id, username, password, post, publish)
    => boolean
    """
    user = authenticate(username, password, 'zinnia.change_entry')
    entry = Entry.objects.get(id=post_id, authors=user)
    if post.get('dateCreated'):
        creation_date = datetime.strptime(
            post['dateCreated'].value[:18], '%Y-%m-%dT%H:%M:%S')
        if settings.USE_TZ:
            creation_date = timezone.make_aware(
                creation_date, timezone.utc)
    else:
        creation_date = entry.creation_date

    entry.title = post['title']
    entry.content = post['description']
    entry.excerpt = post.get('mt_excerpt', Truncator(
        strip_tags(post['description'])).words(50))
    entry.creation_date = creation_date
    entry.last_update = timezone.now()
    entry.comment_enabled = post.get('mt_allow_comments', 1) == 1
    entry.pingback_enabled = post.get('mt_allow_pings', 1) == 1
    entry.trackback_enabled = post.get('mt_allow_pings', 1) == 1
    entry.featured = post.get('sticky', 0) == 1
    entry.tags = 'mt_keywords' in post and post['mt_keywords'] or ''
    entry.slug = 'wp_slug' in post and post['wp_slug'] or slugify(
        post['title'])
    if user.has_perm('zinnia.can_change_status'):
        entry.status = publish and PUBLISHED or DRAFT
    entry.password = post.get('wp_password', '')
    entry.save()

    if 'wp_author_id' in post and user.has_perm('zinnia.can_change_author'):
        if int(post['wp_author_id']) != user.pk:
            author = Author.objects.get(pk=post['wp_author_id'])
            entry.authors.clear()
            entry.authors.add(author)

    if 'categories' in post:
        entry.categories.clear()
        entry.categories.add(*[
            Category.objects.get_or_create(
                title=cat, slug=slugify(cat))[0]
            for cat in post['categories']])
    return True


@xmlrpc_func(returns='struct', args=['string', 'string', 'string', 'struct'])
def new_media_object(blog_id, username, password, media):
    """
    metaWeblog.newMediaObject(blog_id, username, password, media)
    => media structure
    """
    authenticate(username, password)
    path = default_storage.save(os.path.join(UPLOAD_TO, media['name']),
                                ContentFile(media['bits'].data))
    return {'url': default_storage.url(path)}

########NEW FILE########
__FILENAME__ = pingback
"""XML-RPC methods of Zinnia Pingback"""
try:
    from urllib.error import URLError
    from urllib.error import HTTPError
    from urllib.request import urlopen
    from urllib.parse import urlsplit
except ImportError:  # Python 2
    from urllib2 import urlopen
    from urllib2 import URLError
    from urllib2 import HTTPError
    from urlparse import urlsplit

from django.utils import six
from django.utils import timezone
from django.utils.html import strip_tags
from django.contrib.sites.models import Site
from django.core.urlresolvers import resolve
from django.core.urlresolvers import Resolver404
from django.utils.translation import ugettext as _
from django.contrib.contenttypes.models import ContentType

import django_comments as comments

from django_xmlrpc.decorators import xmlrpc_func

from bs4 import BeautifulSoup

from zinnia.models.entry import Entry
from zinnia.flags import PINGBACK
from zinnia.flags import get_user_flagger
from zinnia.signals import pingback_was_posted
from zinnia.settings import PINGBACK_CONTENT_LENGTH

UNDEFINED_ERROR = 0
SOURCE_DOES_NOT_EXIST = 16
SOURCE_DOES_NOT_LINK = 17
TARGET_DOES_NOT_EXIST = 32
TARGET_IS_NOT_PINGABLE = 33
PINGBACK_ALREADY_REGISTERED = 48


def generate_pingback_content(soup, target, max_length, trunc_char='...'):
    """
    Generate a description text for the pingback.
    """
    link = soup.find('a', href=target)

    content = strip_tags(six.text_type(link.findParent()))
    index = content.index(link.string)

    if len(content) > max_length:
        middle = max_length // 2
        start = index - middle
        end = index + middle

        if start <= 0:
            end -= start
            extract = content[0:end]
        else:
            extract = '%s%s' % (trunc_char, content[start:end])

        if end < len(content):
            extract += trunc_char
        return extract

    return content


@xmlrpc_func(returns='string', args=['string', 'string'])
def pingback_ping(source, target):
    """
    pingback.ping(sourceURI, targetURI) => 'Pingback message'

    Notifies the server that a link has been added to sourceURI,
    pointing to targetURI.

    See: http://hixie.ch/specs/pingback/pingback-1.0
    """
    try:
        if source == target:
            return UNDEFINED_ERROR

        site = Site.objects.get_current()
        try:
            document = ''.join(map(
                lambda byte_line: byte_line.decode('utf-8'),
                urlopen(source).readlines()))
        except (HTTPError, URLError):
            return SOURCE_DOES_NOT_EXIST

        if target not in document:
            return SOURCE_DOES_NOT_LINK

        scheme, netloc, path, query, fragment = urlsplit(target)
        if netloc != site.domain:
            return TARGET_DOES_NOT_EXIST

        try:
            view, args, kwargs = resolve(path)
        except Resolver404:
            return TARGET_DOES_NOT_EXIST

        try:
            entry = Entry.published.get(
                slug=kwargs['slug'],
                creation_date__year=kwargs['year'],
                creation_date__month=kwargs['month'],
                creation_date__day=kwargs['day'])
            if not entry.pingbacks_are_open:
                return TARGET_IS_NOT_PINGABLE
        except (KeyError, Entry.DoesNotExist):
            return TARGET_IS_NOT_PINGABLE

        soup = BeautifulSoup(document)
        title = six.text_type(soup.find('title'))
        title = title and strip_tags(title) or _('No title')
        description = generate_pingback_content(soup, target,
                                                PINGBACK_CONTENT_LENGTH)

        pingback, created = comments.get_model().objects.get_or_create(
            content_type=ContentType.objects.get_for_model(Entry),
            object_pk=entry.pk, user_url=source, site=site,
            defaults={'comment': description, 'user_name': title,
                      'submit_date': timezone.now()})
        if created:
            pingback.flags.create(user=get_user_flagger(), flag=PINGBACK)
            pingback_was_posted.send(pingback.__class__,
                                     pingback=pingback,
                                     entry=entry)
            return 'Pingback from %s to %s registered.' % (source, target)
        return PINGBACK_ALREADY_REGISTERED
    except:
        return UNDEFINED_ERROR


@xmlrpc_func(returns='string[]', args=['string'])
def pingback_extensions_get_pingbacks(target):
    """
    pingback.extensions.getPingbacks(url) => '[url, url, ...]'

    Returns an array of URLs that link to the specified url.

    See: http://www.aquarionics.com/misc/archives/blogite/0198.html
    """
    site = Site.objects.get_current()

    scheme, netloc, path, query, fragment = urlsplit(target)
    if netloc != site.domain:
        return TARGET_DOES_NOT_EXIST

    try:
        view, args, kwargs = resolve(path)
    except Resolver404:
        return TARGET_DOES_NOT_EXIST

    try:
        entry = Entry.published.get(
            slug=kwargs['slug'],
            creation_date__year=kwargs['year'],
            creation_date__month=kwargs['month'],
            creation_date__day=kwargs['day'])
    except (KeyError, Entry.DoesNotExist):
        return TARGET_IS_NOT_PINGABLE

    return [pingback.user_url for pingback in entry.pingbacks]

########NEW FILE########
