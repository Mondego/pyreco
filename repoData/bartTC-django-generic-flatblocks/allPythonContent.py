__FILENAME__ = admin
from django.contrib import admin
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django_generic_flatblocks.models import GenericFlatblock

class GenericFlatblockAdmin(admin.ModelAdmin):

    list_display = (
        'related_object_changelink',
        'slug'
    )

    list_display_links = ('slug',)

    def related_object_changelink(self, obj):
        return '<a href="%s">%s - %s</a>' % (
            self.generate_related_object_admin_link(obj.content_object),
            obj.slug,
            obj.content_object.__unicode__(),
        )
    related_object_changelink.allow_tags = True
    related_object_changelink.short_description = _('change related object')

    def generate_related_object_admin_link(self, related_object):
        return '../../%s/%s/%s/' % (
            related_object._meta.app_label,
            related_object._meta.module_name,
            related_object.pk
        )

    def change_view(self, request, object_id, extra_context=None):
        """
        Haven't figured out how to edit the related object as an inline.
        This template adds a link to the change view of the related
        object..
        """
        related_object = self.model.objects.get(pk=object_id).content_object
        c = {
            'admin_url': self.generate_related_object_admin_link(related_object),
            'related_object': related_object,
            'related_app_label': related_object._meta.app_label,
            'related_module_name': related_object._meta.module_name,
        }
        c.update(extra_context or {})
        self.change_form_template = 'admin/django_generic_flatblocks/change_form_forward.html'
        return super(GenericFlatblockAdmin, self).change_view(request, object_id, extra_context=c)

admin.site.register(GenericFlatblock, GenericFlatblockAdmin)

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from django_generic_flatblocks.contrib.gblocks.models import *

admin.site.register(Title)
admin.site.register(Text)
admin.site.register(Image)
admin.site.register(TitleAndText)
admin.site.register(TitleTextAndImage)

########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.utils.translation import ugettext_lazy as _

class Title(models.Model):
    title = models.CharField(_('title'), max_length=255, blank=True)

    def __unicode__(self):
        return "(TitleBlock) %s" % self.title

class Text(models.Model):
    text = models.TextField(_('text'), blank=True)

    def __unicode__(self):
        return "(TextBlock) %s..." % self.text[:20]

class Image(models.Model):
    image = models.ImageField(_('image'), upload_to='gblocks/', blank=True)

    def __unicode__(self):
        return "(ImageBlock) %s" % self.image

class TitleAndText(models.Model):
    title = models.CharField(_('title'), max_length=255, blank=True)
    text = models.TextField(_('text'), blank=True)

    def __unicode__(self):
        return "(TitleAndTextBlock) %s" % self.title

class TitleTextAndImage(models.Model):
    title = models.CharField(_('title'), max_length=255, blank=True)
    text = models.TextField(_('text'), blank=True)
    image = models.ImageField(_('image'), upload_to='gblocks/', blank=True)

    def __unicode__(self):
        return "(TitleTextAndImageBlock) %s" % self.title

########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic

class GenericFlatblock(models.Model):
    slug = models.SlugField(_('slug'), max_length=255, unique=True)
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = generic.GenericForeignKey('content_type', 'object_id')

    def __unicode__(self):
        return self.slug

########NEW FILE########
__FILENAME__ = generic_flatblocks
from django.template import Library, Node
from django.template import TemplateSyntaxError, TemplateDoesNotExist, Variable
from django.template.loader import select_template
from django.conf import settings
from django.db.models.loading import get_model
from django.template.defaultfilters import slugify
from django_generic_flatblocks.models import GenericFlatblock

register = Library()

class GenericFlatblockNode(Node):
    def __init__(self, slug, modelname=None, template_path=None,
                 variable_name=None, store_in_object=None):
        self.slug = slug
        self.modelname = modelname
        self.template_path = template_path
        self.variable_name = variable_name
        self.store_in_object = store_in_object

    def generate_slug(self, slug, context):
        """
        Generates a slug out of a comma-separated string. Automatically resolves
        variables in it. Examples::

        "website","title" -> website_title
        "website",LANGUAGE_CODE -> website_en
        """
        # If the user passed a integer as slug, use it as a primary key in
        # self.get_content_object()
        if not ',' in slug and isinstance(self.resolve(slug, context), int):
            return self.resolve(slug, context)
        return slugify('_'.join([str(self.resolve(i, context)) for i in slug.split(',')]))

    def generate_admin_link(self, related_object, context):
        """
        Generates a link to contrib.admin change view. In Django 1.1 this
        will work automatically using urlresolvers.
        """
        app_label = related_object._meta.app_label
        module_name = related_object._meta.module_name
        # Check if user has change permissions
        if context['request'].user.is_authenticated() and \
           context['request'].user.has_perm('%s.change' % module_name):
            admin_url_prefix = getattr(settings, 'ADMIN_URL_PREFIX', '/admin/')
            return '%s%s/%s/%s/' % (admin_url_prefix, app_label, module_name, related_object.pk)
        else:
            return None

    def get_content_object(self, related_model, slug):

        # If the user passed a Integer as a slug, assume that we should fetch
        # this specific object
        if isinstance(slug, int):
            try:
                related_object = related_model._default_manager.get(pk=slug)
                return None, related_object
            except related_model.DoesNotExist:
                if settings.TEMPLATE_DEBUG:
                    raise
                related_object = related_model()
                return None, related_object

        # Otherwise, try to generate a new, related object
        try:
            generic_object = GenericFlatblock._default_manager.get(slug=slug)
            related_object = generic_object.content_object
            if related_object is None:
                # The related object must have been deleted. Let's start over.
                generic_object.delete()
                raise GenericFlatblock.DoesNotExist
        except GenericFlatblock.DoesNotExist:
            related_object = related_model._default_manager.create()
            generic_object = GenericFlatblock._default_manager.create(slug=slug, content_object=related_object)
        return generic_object, related_object

    def resolve(self, var, context):
        """Resolves a variable out of context if it's not in quotes"""
        if var[0] in ('"', "'") and var[-1] == var[0]:
            return var[1:-1]
        else:
            return Variable(var).resolve(context)

    def resolve_model_for_label(self, modelname, context):
        """resolves a model for a applabel.modelname string"""
        applabel, modellabel = self.resolve(modelname, context).split(".")
        related_model = get_model(applabel, modellabel)
        return related_model

    def render(self, context):

        slug = self.generate_slug(self.slug, context)
        related_model = self.resolve_model_for_label(self.modelname, context)

        # Get the generic and related object
        generic_object, related_object = self.get_content_object(related_model, slug)
        admin_url = self.generate_admin_link(related_object, context)

        # if "into" is provided, store the related object into this variable
        if self.store_in_object:
            into_var = self.resolve(self.store_in_object, context)
            context[into_var] = related_object
            context["%s_generic_object" % into_var] = generic_object
            context["%s_admin_url" % into_var] = admin_url
            return ''

        # Add the model instances to the current context
        context['generic_object'] = generic_object
        context['object'] = related_object
        context['admin_url'] = admin_url

        # Resolve the template(s)
        template_paths = []
        if self.template_path:
            template_paths.append(self.resolve(self.template_path, context))
        template_paths.append('%s/%s/flatblock.html' % \
            tuple(self.resolve(self.modelname, context).lower().split(".")))

        try:
            t = select_template(template_paths)
        except:
            if settings.TEMPLATE_DEBUG:
                raise
            return ''
        content = t.render(context)

        # Set content as variable inside context, if variable_name is given
        if self.variable_name:
            context[self.resolve(self.variable_name, context)] = content
            return ''
        return content

def do_genericflatblock(parser, token):
    """
    {% gblock "slug" for "appname.modelname" %}
    {% gblock "slug" for "appname.modelname" into "slug_object" %}
    {% gblock "slug" for "appname.modelname" with "templatename.html" %}
    {% gblock "slug" for "appname.modelname" with "templatename.html" as "variable" %}
    """

    def next_bit_for(bits, key, if_none=None):
        try:
            return bits[bits.index(key)+1]
        except ValueError:
            return if_none

    bits = token.contents.split()
    args = {
        'slug': next_bit_for(bits, 'gblock'),
        'modelname': next_bit_for(bits, 'for'),
        'template_path': next_bit_for(bits, 'with'),
        'variable_name': next_bit_for(bits, 'as'),
        'store_in_object': next_bit_for(bits, 'into'),
    }
    return GenericFlatblockNode(**args)

register.tag('gblock', do_genericflatblock)

########NEW FILE########
__FILENAME__ = settings
from os.path import join, dirname

TEST_DIR = dirname(__file__)

DATABASE_ENGINE = 'sqlite3'
DATABASE_NAME = ':memory:'
TEST_DATABASE_NAME = ":memory:"

SITE_ID = 1

ROOT_URLCONF = ''

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.core.context_processors.auth',
    'django.core.context_processors.debug',
    'django.core.context_processors.i18n',
    'django.core.context_processors.media',
#    'django.core.context_processors.request',
)

TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.admin',
    'django_generic_flatblocks',
    'django_generic_flatblocks.tests',
    'django_generic_flatblocks.contrib.gblocks',
)

TEMPLATE_DIRS = (
    join(TEST_DIR, 'templates'),
)

TEST_RUNNER = 'django-test-coverage.runner.run_tests'
########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# django-generic-flatblocks documentation build configuration file, created by
# sphinx-quickstart on Thu Jun  4 20:21:28 2009.
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
#sys.path.append(os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = []

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'django-generic-flatblocks'
copyright = u'2010, Martin Mahner'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = ''
# The full version, including alpha/beta/rc tags.
release = ''

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of documents that shouldn't be included in the build.
#unused_docs = []

# List of directories, relative to source directory, that shouldn't be searched
# for source files.
exclude_trees = ['_build']

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

# The theme to use for HTML and HTML Help pages.  Major themes that come with
# Sphinx are currently 'default' and 'sphinxdoc'.
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
#html_use_modindex = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# If nonempty, this is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = ''

# Output file base name for HTML help builder.
htmlhelp_basename = 'django-generic-flatblocksdoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'django-generic-flatblocks.tex', u'django-generic-flatblocks Documentation',
   u'Martin Mahner', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_use_modindex = True

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os, sys

sys.path.insert(0, "../")

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
import os

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
PROJECT_NAME = os.path.split(PROJECT_ROOT)[-1]

# ==============================================================================
# debug settings
# ==============================================================================

DEBUG = True
TEMPLATE_DEBUG = DEBUG
INTERNAL_IPS = ()
if DEBUG:
    TEMPLATE_STRING_IF_INVALID = ''

# ==============================================================================
# cache settings
# ==============================================================================

CACHE_BACKEND = 'locmem://'
CACHE_MIDDLEWARE_KEY_PREFIX = '%s_' % PROJECT_NAME
CACHE_MIDDLEWARE_SECONDS = 600

# ==============================================================================
# email and error-notify settings
# ==============================================================================

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DEFAULT_FROM_EMAIL = 'from-mail@example.com'
SERVER_EMAIL = 'error-notify@example.com'

EMAIL_SUBJECT_PREFIX = '[%s] ' % PROJECT_NAME
EMAIL_HOST = 'localhost'
EMAIL_PORT = 25
EMAIL_HOST_USER = ''
EMAIL_HOST_PASSWORD = ''
EMAIL_USE_TLS = False

# ==============================================================================
# auth settings
# ==============================================================================

LOGIN_URL = '/accounts/login/'
LOGOUT_URL = '/accounts/logout/'
LOGIN_REDIRECT_URL = '/'

# ==============================================================================
# database settings
# ==============================================================================

DATABASE_ENGINE = 'sqlite3'
DATABASE_NAME = os.path.join(PROJECT_ROOT, 'dev.db')
DATABASE_USER = ''
DATABASE_PASSWORD = ''
DATABASE_HOST = ''
DATABASE_PORT = ''

# ==============================================================================
# i18n and url settings
# ==============================================================================

TIME_ZONE = 'Europe/Berlin'
LANGUAGE_CODE = 'de'
LANGUAGES = (('en', 'English'),
             ('de', 'German'))
USE_I18N = True

SITE_ID = 1

MEDIA_ROOT = os.path.join(PROJECT_ROOT, 'site_media')
MEDIA_URL = '/media/'
ADMIN_MEDIA_PREFIX = '/django_admin_media/'

ROOT_URLCONF = '%s.urls' % PROJECT_NAME

# ==============================================================================
# application and middleware settings
# ==============================================================================

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.admin',
    'django.contrib.humanize',
    'django.contrib.webdesign',
    'django_generic_flatblocks',
    'django_generic_flatblocks.contrib.gblocks',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.middleware.http.ConditionalGetMiddleware',
#    'django.middleware.gzip.GZipMiddleware',
    'django.middleware.common.CommonMiddleware',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.core.context_processors.auth',
    'django.core.context_processors.debug',
    'django.core.context_processors.i18n',
    'django.core.context_processors.media',
    'django.core.context_processors.request',
)

TEMPLATE_DIRS = (
    os.path.join(PROJECT_ROOT, 'templates'),
)

TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
#    'django.template.loaders.eggs.load_template_source',
)

# ==============================================================================
# the secret key
# ==============================================================================

try:
    SECRET_KEY
except NameError:
    SECRET_FILE = os.path.join(PROJECT_ROOT, 'secret.txt')
    try:
        SECRET_KEY = open(SECRET_FILE).read().strip()
    except IOError:
        try:
            from random import choice
            SECRET_KEY = ''.join([choice('abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)') for i in range(50)])
            secret = file(SECRET_FILE, 'w')
            secret.write(SECRET_KEY)
            secret.close()
        except IOError:
            Exception('Please create a %s file with random characters to generate your secret key!' % SECRET_FILE)

# ==============================================================================
# third party
# ==============================================================================

# ..third party app settings here

# ==============================================================================
# host specific settings
# ==============================================================================

try:
    from local_settings import *
except ImportError:
    pass

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from django.contrib import admin
from django.views.generic.simple import direct_to_template

admin.autodiscover()

urlpatterns = patterns('',
    url(r'^$', direct_to_template, {'template': 'example.html'}),
    (r'^admin/doc/', include('django.contrib.admindocs.urls')),
    (r'^admin/(.*)', admin.site.root),
)

########NEW FILE########
