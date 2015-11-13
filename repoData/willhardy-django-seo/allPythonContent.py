__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Django SEO documentation build configuration file
#
# This file is execfile()d with the current directory set to its containing dir.
#
# The contents of this file are pickled, so don't put values in the namespace
# that aren't pickleable (module imports are okay, they're removed automatically).
#
# All configuration values have a default value; values that are commented out
# serve to show the default value.

import sys, os

# If your extensions are in another directory, add it here. If the directory
# is relative to the documentation root, use os.path.abspath to make it
# absolute, like shown here.
#sys.path.append(os.path.abspath('some/directory'))

# General configuration
# ---------------------

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.doctest']

# Add any paths that contain templates here, relative to this directory.
#templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.txt'

# The master toctree document.
master_doc = 'contents'

# General substitutions.
project = 'Django SEO'
copyright = '2010, Will Hardy'

# The default replacements for |version| and |release|, also used in various
# other places throughout the built documents.
#
# The short X.Y version.
version = '1.0'
# The full version, including alpha/beta/rc tags.
release = '1.0'

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
today_fmt = '%B %d, %Y'

# List of documents that shouldn't be included in the build.
#unused_docs = []

# List of directories, relative to source directories, that shouldn't be searched
# for source files.
#exclude_dirs = []

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


# Options for HTML output
# -----------------------

# The style sheet to use for HTML and HTML Help pages. A file of that name
# must exist either in Sphinx' static/ path, or in one of the custom paths
# given in html_static_path.
html_style = 'default.css'

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (within the static path) to place at the top of
# the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
#html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
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

# If true, the reST sources are included in the HTML build as _sources/<name>.
#html_copy_source = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# If nonempty, this is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = ''

# Output file base name for HTML help builder.
htmlhelp_basename = 'DjangoSEO'


# Options for LaTeX output
# ------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, document class [howto/manual]).
latex_documents = [
  ('index', 'DjangoSEO.tex', 'Django SEO Documentation',
   'Will Hardy', 'manual'),
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
import os
import sys

# Setup the path (could have been PYTHONPATH)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path = [PROJECT_ROOT] + sys.path

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
# Django settings for regressiontests project.
import django

# Let testing know what version we're using
print "Using Django version: %s" % django.get_version()

# Use the new messages?
_MESSAGES_FRAMEWORK = (django.VERSION[:2] >= (1,2))

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'test.db',                      # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

# Old-school fallback (Django <= 1.1)
DATABASE_ENGINE = 'django.db.backends.sqlite3'
DATABASE_NAME = 'test.db'

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'Europe/Berlin'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-au'

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
SECRET_KEY = '+ljg9bcz6t7^9y8ppcxxg5#(%f1p#yj9ot%+e*n5n3y9kg=brm'

if django.VERSION < (1,2):
    TEMPLATE_LOADERS = ( 'django.template.loaders.app_directories.load_template_source',)
else:
    TEMPLATE_LOADERS = ( 'django.template.loaders.app_directories.Loader',)

MIDDLEWARE_CLASSES = [
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    #'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
]
if _MESSAGES_FRAMEWORK:
    MIDDLEWARE_CLASSES.append('django.contrib.messages.middleware.MessageMiddleware')

ROOT_URLCONF = 'regressiontests.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

if django.VERSION < (1,2):
    TEMPLATE_CONTEXT_PROCESSORS = ["django.core.context_processors.auth"]
else:
    TEMPLATE_CONTEXT_PROCESSORS = ["django.contrib.auth.context_processors.auth"]

TEMPLATE_CONTEXT_PROCESSORS += [
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    'django.core.context_processors.request',
    ]
if _MESSAGES_FRAMEWORK:
    TEMPLATE_CONTEXT_PROCESSORS.append("django.contrib.messages.context_processors.messages")

INSTALLED_APPS = [
    'django.contrib.sites',
    'django.contrib.redirects',
    'rollyourown.seo',
    'userapp',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.admin',
    'django.contrib.flatpages',
]
if _MESSAGES_FRAMEWORK:
    INSTALLED_APPS.append('django.contrib.messages')

CACHE_BACKEND = 'dummy://'
# Enable when testing cache
#CACHE_BACKEND = "locmem://?timeout=30&max_entries=400"

# If south is available, add it
try:
    import south
    INSTALLED_APPS.append('south')
except ImportError:
    pass

SEO_MODELS = ('userapp',)

COVERAGE_MODULES = ('rollyourown.seo', 'userapp', 'flatpages.FlatPage')

try:
    from settings_local import *
except ImportError:
    pass

########NEW FILE########
__FILENAME__ = test-coverage
#!/usr/bin/env python

"""
Run Django Tests with full test coverage

This starts coverage early enough to get all of the model loading &
other startup code. It also allows you to change the output location
from $PROJECT_ROOT/coverage by setting the $TEST_COVERAGE_OUTPUT_DIR
environmental variable.

This is a customised version of the django coverage tool by acdha,
downloaded from http://gist.github.com/288810

Modified by Will Hardy (will@hardysoftware.de) June 2010.
"""

import logging
import os
import sys
from coverage import coverage

def main():
    PROJECT_ROOT = os.path.realpath(os.path.join(os.path.dirname(__file__), ".."))
    output_dir = os.environ.get("TEST_COVERAGE_OUTPUT_DIR", os.path.join(PROJECT_ROOT, "coverage"))
    if 'DJANGO_SETTINGS_MODULE' not in os.environ:
        import settings as sett
        os.environ["DJANGO_SETTINGS_MODULE"] = sett.__name__

    print >>sys.stderr, "Test coverage output will be stored in %s" % output_dir

    if not os.path.exists(output_dir):
        os.mkdir(output_dir)

    logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s', filename=os.path.join(output_dir, "tests.log"))

    from django.conf import settings

    # Start code coverage before anything else if necessary
    use_coverage = hasattr(settings, 'COVERAGE_MODULES') and len(settings.COVERAGE_MODULES)
    if use_coverage:
        if len(sys.argv) > 1 and sys.argv[1] == "--branch":
            sys.argv.pop(1)
            cov = coverage(branch=True) # Enable super experimental branch support
        else:
            cov = coverage()
        cov.use_cache(0) # Do not cache any of the coverage.py stuff
        cov.exclude('^\s*$') # Exclude empty lines
        cov.exclude('^\s*#.*$') # Exclude comment blocks
        cov.exclude('^\s*(import|from)\s') # Exclude import statements
        cov.start()

    from django.conf import settings
    from django.db.models import get_app, get_apps


    # NOTE: Normally we'd use ``django.core.management.commands.test`` here but
    # we want to have South's intelligence for applying database migrations or
    # syncing everything directly (based on ``settings.SOUTH_TESTS_MIGRATE``).
    # South's test Command is a subclass of the standard Django test Command so
    # it's otherwise identical:
    try:
        from south.management.commands import test
    except ImportError:
        from django.core.management.commands import test

    # Suppress debugging displays, etc. to test as real users will see it:
    settings.DEBUG = False
    settings.TEMPLATE_DEBUG = False
    # This avoids things being cached when we attempt to regenerate them.
    settings.CACHE_BACKEND = 'dummy:///'

    # According to http://docs.djangoproject.com/en/1.0/topics/cache/#order-of-middleware-classes
    # this should not be ahead of UpdateCacheMiddleware but to avoid this unresolved Django bug
    # http://code.djangoproject.com/ticket/5176 we have to place SessionMiddleware first to avoid
    # failures:
    mc = list(settings.MIDDLEWARE_CLASSES)
    try:
        mc.remove('django.middleware.cache.FetchFromCacheMiddleware')
        mc.remove('django.middleware.cache.UpdateCacheMiddleware')
    except ValueError:
        pass

    settings.MIDDLEWARE_CLASSES = tuple(mc)

    # If the user provided modules on the command-line we'll only test the
    # listed modules. Otherwise we'll build a list of installed applications
    # which we wrote and pretend the user entered that on the command-line
    # instead.

    test_labels = [ i for i in sys.argv[1:] if not i[0] == "-"]
    if not test_labels:
        test_labels = []

        site_name = settings.SETTINGS_MODULE.split(".")[0]

        for app in get_apps():
            pkg = app.__package__ or app.__name__.replace(".models", "")
            if pkg in settings.COVERAGE_MODULES:
                test_labels.append(pkg)
            else:
                print >>sys.stderr, "Skipping tests for %s" % pkg

        test_labels.sort()

        print >>sys.stderr, "Automatically generated test labels for %s: %s" % (site_name, ", ".join(test_labels))

        sys.argv.extend(test_labels)

    settings.DEBUG = False
    settings.TEMPLATE_DEBUG = False

    command = test.Command()

    rc = 0
    sys.argv.insert(1, "test")
    try:
        command.run_from_argv(sys.argv)
    except SystemExit, e:
        rc = e.code

    # Stop code coverage after tests have completed
    if use_coverage:
        cov.stop()

    coverage_modules = filter(None, [
        sys.modules[k] for k in sys.modules if any(
            l for l in [ l.split(".")[0] for l in test_labels]
                # Avoid issues with an empty models.py causing __package__ == None
                if k.startswith(get_app(l).__package__ or get_app(l).__name__.replace(".models", ""))
        )
    ])

    if use_coverage:
        # Print code metrics header
        print ''
        print '-------------------------------------------------------------------------'
        print ' Unit Test Code Coverage Results'
        print '-------------------------------------------------------------------------'
    
        # Report code coverage metrics
        cov.report(coverage_modules)

        cov.html_report(coverage_modules, directory=output_dir)
        cov.xml_report(coverage_modules, outfile=os.path.join(output_dir, "coverage.xml"))

        # Print code metrics footer
        print '-------------------------------------------------------------------------'

        if rc != 0:
            print >>sys.stderr, "Coverage report is not be accurate due to non-zero exit status: %d" % rc

        sys.exit(rc)


if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

from django.contrib import admin
from userapp.admin import alternative_site

urlpatterns = patterns('',
    (r'^admin/', include(admin.site.urls)),
    (r'^alt-admin/', include(alternative_site.urls)),
    (r'^', include('userapp.urls')),
)

########NEW FILE########
__FILENAME__ = admin
#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from rollyourown.seo.admin import register_seo_admin, get_inline
from django.contrib import admin
from userapp.seo import Coverage, WithSites, WithSEOModels

register_seo_admin(admin.site, Coverage)
register_seo_admin(admin.site, WithSites)

from userapp.models import Product, Page, Category, Tag, NoPath

class WithMetadataAdmin(admin.ModelAdmin):
    inlines = [get_inline(Coverage), get_inline(WithSites)]

admin.site.register(Product, admin.ModelAdmin)
admin.site.register(Page, admin.ModelAdmin)
admin.site.register(Tag, WithMetadataAdmin)
admin.site.register(NoPath, WithMetadataAdmin)


# Register alternative site here to avoid double import
alternative_site = admin.AdminSite()
from rollyourown.seo.admin import auto_register_inlines
#from userapp.models import Tag, Page, Product
#from userapp.seo import Coverage, WithSites, WithSEOModels
alternative_site.register(Tag)
auto_register_inlines(alternative_site, Coverage)
alternative_site.register(Page)
auto_register_inlines(alternative_site, WithSites)
auto_register_inlines(alternative_site, WithSEOModels)
alternative_site.register(Product)


########NEW FILE########
__FILENAME__ = models
from django.db import models

class Page(models.Model):
    title = models.CharField(max_length=255, default="", blank=True)
    type = models.CharField(max_length=50, default="", blank=True)
    content = models.TextField(default="", blank=True)

    @models.permalink
    def get_absolute_url(self):
        return ('userapp_page_detail', [self.type], {})

    def __unicode__(self):
        return self.title or self.content


class Product(models.Model):
    meta_description = models.TextField(default="")
    meta_keywords    = models.CharField(max_length=255, default="")
    meta_title       = models.CharField(max_length=255, default="")

    @models.permalink
    def get_absolute_url(self):
        return ('userapp_product_detail', [self.id], {})

    def __unicode__(self):
        return self.meta_title


class Category(models.Model):
    name = models.CharField(max_length=255, default="M Category Name")
    page_title = models.CharField(max_length=255, default="M Category Page Title")

    @models.permalink
    def get_absolute_url(self):
        return ('userapp_my_view', ["abc"], {})


class NoPath(models.Model):
    pass


class Tag(models.Model):
    name = models.CharField(max_length=255, default="")

    @models.permalink
    def get_absolute_url(self):
        return ('userapp_tag', [self.name], {})

    def __unicode__(self):
        return self.name


########NEW FILE########
__FILENAME__ = seo
from rollyourown import seo
from django.db import models
from django.contrib.sites.models import Site

def get_site_name(metadata, **kwargs):
    return "example.com"

def get_model_instance_content(metadata, model_instance=None, **kwargs):
    if model_instance:
        return u'model instance content: %s' % model_instance.content
    return 'no model instance'

class Coverage(seo.Metadata):
    """ A SEO metadata definition, which should cover all configurable options.
    """
    def get_populate_from1(self, metadata, **kwargs):
        return "wxy"

    def get_populate_from2(self, metadata, **kwargs):
        return "xyz"
    get_populate_from2.short_description = "Always xyz"

    title        = seo.Tag(populate_from=seo.Literal("example.com"), head=True)
    heading      = seo.Tag(max_length=68, name="hs:tag", verbose_name="tag two", head=True)

    keywords     = seo.KeywordTag()
    description  = seo.MetaTag(max_length=155, name="hs:metatag", verbose_name="metatag two")

    raw1         = seo.Raw()
    raw2         = seo.Raw(head=True, verbose_name="raw two", valid_tags=("meta", "title"))

    help_text1   = seo.Tag(help_text="Some help text 1.")
    help_text2   = seo.Tag(populate_from="def")
    help_text3   = seo.Tag(populate_from=get_populate_from1, help_text="Some help text 3.")
    help_text4   = seo.Tag(populate_from=get_populate_from2)
    help_text5   = seo.Tag(populate_from="heading")
    help_text6   = seo.Tag(populate_from="heading", help_text="Some help text 6.")

    populate_from1     = seo.Tag(populate_from="get_populate_from1")
    populate_from2     = seo.Tag(populate_from="heading")
    populate_from3     = seo.Tag(populate_from=seo.Literal("efg"))
    populate_from4     = seo.Tag(populate_from="ghi")
    populate_from5     = seo.Tag(populate_from="ghi", editable=False)
    populate_from6     = seo.Tag(populate_from="keywords")
    populate_from7     = seo.Tag(populate_from=get_model_instance_content)

    field1       = seo.Tag(field=models.TextField)

    class Meta:
        verbose_name = "Basic Metadatum"
        verbose_name_plural = "Basic Metadata"
        use_sites = False
        groups = { 
            'advanced': ('raw1', 'raw2' ),
            'help_text': ( 'help_text1', 'help_text2', 'help_text3', 'help_text4', )
        }
        seo_models = ('userapp', )
        seo_views = ('userapp', )

    class HelpText:
        help_text2 = "Updated help text2."


class WithSites(seo.Metadata):
    title        = seo.Tag()

    class Meta:
        use_sites = True

class WithI18n(seo.Metadata):
    title        = seo.Tag()

    class Meta:
        use_i18n = True

class WithRedirect(seo.Metadata):
    title        = seo.Tag()

    class Meta:
        use_redirect = True

class WithRedirectSites(seo.Metadata):
    title        = seo.Tag()

    class Meta:
        use_sites = True
        use_redirect = True

class WithCache(seo.Metadata):
    title    = seo.Tag(head=True, populate_from=seo.Literal("1234"))
    subtitle = seo.Tag(head=True)

    class Meta:
        use_cache = True

class WithCacheSites(seo.Metadata):
    title    = seo.Tag(head=True, populate_from=seo.Literal("1234"))
    subtitle = seo.Tag(head=True)

    class Meta:
        use_cache = True
        use_sites = True

class WithCacheI18n(seo.Metadata):
    title    = seo.Tag(head=True, populate_from=seo.Literal("1234"))
    subtitle = seo.Tag(head=True)

    class Meta:
        use_cache = True
        use_i18n = True

class WithBackends(seo.Metadata):
    title    = seo.Tag()

    class Meta:
        backends = ('view', 'path')

class WithSEOModels(seo.Metadata):
    title = seo.Tag()

    class Meta:
        seo_models = ('userapp', )

########NEW FILE########
__FILENAME__ = tests
#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Test suite for SEO framework.

    It is divided into 7 sections:

    * Data selection (Unit tests)
    * Value resolution (Unit tests)
    * Formatting (Unit tests)
    * Definition (System tests)
    * Meta options (System tests)
    * Templates (System tests)
    * Random (series of various uncategorised tests)


    TESTS TO WRITE: 
    To check functionality actually works:
        - south compatibility (changing a definition)

    For better coverage:
        - valid_tags given as a string
        - Meta.seo_models = appname.modelname (ie with a dot)
        + if "head" is True, tag is automatically included in the head, if "false" then no
        + if "name" is included, that is the name of the given tag, otherwise, the field name is used
        + if verbose_name is used, pass on to field (through field_kwargs)
        + if the field argument given, that Django field type is used (NB default field argument incompatibility?)
        + if editable is set to False, no Django model field is created. The value is always from populate_from
        + if choices is given it is passed onto the field, (expanded if just a list of strings)
        + groups: these elements are grouped together in the admin and can be output together in the template
        + use_sites: add a 'site' field to each model. Non-matching sites are removed, null is allowed, meaning all sites match.
        + sites conflicting sites, when two entries exist for different sites, the explicit (local) one wins. (Even better: both are used, in the appropriate order)
        + models: list of models and/or apps which are available for model instance metadata
        - verbose_name(_plural): this is passed onto Django

"""
import StringIO

from django.core.urlresolvers import reverse
from django.test import TestCase
try:
    from django.test import TransactionTestCase
except ImportError:
    TransactionTestCase = TestCase
from django.test.client import FakePayload
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.contrib.redirects.models import Redirect
from django.contrib.auth.models import User
from django.conf import settings
from django.db import IntegrityError, transaction
from django.core.handlers.wsgi import WSGIRequest
from django.template import Template, RequestContext, TemplateSyntaxError
from django.core.cache import cache
from django.utils.hashcompat import md5_constructor
from django.utils.encoding import iri_to_uri
from django.core.management import call_command

from rollyourown.seo import get_metadata as seo_get_metadata
from rollyourown.seo.base import registry
from userapp.models import Page, Product, Category, NoPath, Tag
from userapp.seo import Coverage, WithSites, WithI18n, WithRedirect, WithRedirectSites, WithCache, WithCacheSites, WithCacheI18n, WithBackends


def get_metadata(path):
    return seo_get_metadata(path, name="Coverage")


class DataSelection(TestCase):
    """ Data selection (unit tests). Test how metadata objects are discovered.
    """

    def setUp(self):
        # Model instance metadata
        self.product = Product.objects.create()
        self.product_content_type = ContentType.objects.get_for_model(Product)
        # NB if signals aren't working, the following will fail.
        self.product_metadata = Coverage._meta.get_model('modelinstance').objects.get(_content_type=self.product_content_type, _object_id=self.product.id)
        self.product_metadata.title="ModelInstance title"
        self.product_metadata.keywords="ModelInstance keywords"
        self.product_metadata.save()

        self.page = Page.objects.create(title=u"Page Title", type="abc")
        self.page_content_type = ContentType.objects.get_for_model(Page)
        self.page_metadata = Coverage._meta.get_model('modelinstance').objects.get(_content_type=self.page_content_type, _object_id=self.page.id)
        self.page_metadata.title="Page title"
        self.page_metadata.keywords="Page keywords"
        self.page_metadata.save()

        # Model metadata
        self.model_metadata = Coverage._meta.get_model('model').objects.create(_content_type=self.product_content_type, title="Model title", keywords="Model keywords")

        # Path metadata
        self.path_metadata = Coverage._meta.get_model('path').objects.create(_path="/path/", title="Path title", keywords="Path keywords")

        # View metadata
        self.view_metadata = Coverage._meta.get_model('view').objects.create(_view="userapp_my_view", title="View title", keywords="View keywords")

    def test_path(self):
        """ Checks that a direct path listing is always found first. """
        path = self.product.get_absolute_url()
        self.assertNotEqual(get_metadata(path).title.value, 'Path title')
        self.assertEqual(get_metadata(path).title.value, 'ModelInstance title')
        self.path_metadata._path = path
        self.path_metadata.save()
        self.assertEqual(get_metadata(path).title.value, 'Path title')

    def test_model_instance(self):
        # With no matching instances, the default should be used
        page = Page(title="Title", type="newpage")
        path = page.get_absolute_url()
        self.assertEqual(get_metadata(path).title.value, "example.com")

        # Check that a new metadata instance is created
        old_count = Coverage._meta.get_model('modelinstance').objects.all().count()
        page.save()
        new_count = Coverage._meta.get_model('modelinstance').objects.all().count()
        self.assertEqual(new_count, old_count+1)

        # Check that the correct data is loaded
        assert 'New Page title' not in unicode(get_metadata(path).title)
        Coverage._meta.get_model('modelinstance').objects.filter(_content_type=self.page_content_type, _object_id=page.id).update(title="New Page title")
        self.assertEqual(get_metadata(path).title.value, 'New Page title')

    def test_model(self):
        path = self.product.get_absolute_url()

        # Model metadata only works if there is no instance metadata
        self.assertEqual(get_metadata(path).title.value, 'ModelInstance title')
        self.assertEqual(get_metadata(path).keywords.value, 'ModelInstance keywords')

        # Remove the instance metadata
        self.product_metadata.keywords = ''
        self.product_metadata.save()

        self.assertEqual(get_metadata(path).keywords.value, 'Model keywords')

    def test_view(self):
        path = '/my/view/text/'
        path_metadata = Coverage._meta.get_model('path').objects.create(_path=path, title="Path title")
        self.assertEqual(get_metadata(path).title.value, 'Path title')
        path_metadata.delete()
        self.assertEqual(get_metadata(path).title.value, 'View title')

    def test_sites(self):
        """ Tests the django.contrib.sites support.
            A separate metadata definition is used, WithSites, which has turned on sites support.
        """
        path = "/abc/"
        site = Site.objects.get_current()
        path_metadata = WithSites._meta.get_model('path').objects.create(_site=site, title="Site Path title", _path=path)
        self.assertEqual(seo_get_metadata(path, name="WithSites").title.value, 'Site Path title')
        # Metadata with site=null should work
        path_metadata._site_id = None
        path_metadata.save()
        self.assertEqual(seo_get_metadata(path, name="WithSites").title.value, 'Site Path title')
        # Metadata with an explicitly wrong site should not work
        path_metadata._site_id = site.id + 1
        path_metadata.save()
        self.assertEqual(seo_get_metadata(path, name="WithSites").title.value, None)

    def test_i18n(self):
        """ Tests the i18n support, allowing a language to be associated with metadata entries.
        """
        path = "/abc/"
        language = 'de'
        path_metadata = WithI18n._meta.get_model('path').objects.create(_language='de', title="German Path title", _path=path)
        self.assertEqual(seo_get_metadata(path, name="WithI18n", language="de").title.value, 'German Path title')
        # Metadata with an explicitly wrong site should not work
        path_metadata._language = "en"
        path_metadata.save()
        self.assertEqual(seo_get_metadata(path, name="WithI18n", language="de").title.value, None)

#    # FUTURE feature
#
#    def test_redirect(self):
#        """ Tests django.contrib.redirect support, automatically adding redirects for new paths.
#        """
#        old_path = "/abc/"
#        new_path = "/new-path/"
#
#        # Check that the redirect doesn't already exist
#        self.assertEqual(Redirect.objects.filter(old_path=old_path, new_path=new_path).count(), 0)
#
#        path_metadata = WithRedirect._meta.get_model('path').objects.create(title="A Path title", _path=old_path)
#        self.assertEqual(seo_get_metadata(old_path, name="WithRedirect").title.value, 'A Path title')
#
#        # Rename the path
#        path_metadata._path = new_path
#        path_metadata.save()
#        self.assertEqual(seo_get_metadata(old_path, name="WithRedirect").title.value, None)
#        self.assertEqual(seo_get_metadata(new_path, name="WithRedirect").title.value, 'A Path title')
#
#        # Check that a redirect was created
#        self.assertEqual(Redirect.objects.filter(old_path=old_path, new_path=new_path).count(), 1)
#
#    def test_redirect_with_sites(self):
#        """ Tests django.contrib.redirect support, automatically adding redirects for new paths.
#        """
#        old_path = "/abc/"
#        new_path = "/new-path/"
#        site = Site.objects.get_current()
#
#        # Check that the redirect doesn't already exist
#        self.assertEqual(Redirect.objects.filter(old_path=old_path, new_path=new_path, site=site).count(), 0)
#
#        path_metadata = WithRedirectSites._meta.get_model('path').objects.create(title="A Path title", _path=old_path, _site=site)
#        self.assertEqual(seo_get_metadata(old_path, name="WithRedirectSites").title.value, 'A Path title')
#
#        # Rename the path
#        path_metadata._path = new_path
#        path_metadata.save()
#        self.assertEqual(seo_get_metadata(old_path, name="WithRedirectSites").title.value, None)
#        self.assertEqual(seo_get_metadata(new_path, name="WithRedirectSites").title.value, 'A Path title')
#
#        # Check that a redirect was created
#        self.assertEqual(Redirect.objects.filter(old_path=old_path, new_path=new_path, site=site).count(), 1)

    def test_missing_value(self):
        """ Checks that nothing breaks when no value could be found. 
            The value should be None, the output blank (if that is appropriate for the field).
        """
        path = "/abc/"
        self.assertEqual(seo_get_metadata(path, name="WithSites").title.value, None)
        self.assertEqual(unicode(seo_get_metadata(path, name="WithSites").title), "")

    def test_path_conflict(self):
        """ Check the crazy scenario where an existing metadata object has the same path. """
        old_path = self.product_metadata._path
        self.product_metadata._path = '/products/2/'
        self.product_metadata.save()
        self.assertEqual(self.product_metadata._object_id, self.product.pk)

        # Create a new product that will take the same path
        new_product = Product.objects.create()
        Coverage._meta.get_model('modelinstance').objects.filter(_content_type=self.product_content_type, _object_id=new_product.id).update(title="New Title")

        # This test will not work if we have the id wrong
        if new_product.id != 2:
            raise Exception("Test Error: the product ID is not as expected, this test cannot work.")

        # Check that the existing path was corrected
        product_metadata = Coverage._meta.get_model('modelinstance').objects.get(id=self.product_metadata.id)
        self.assertEqual(old_path, product_metadata._path)

        # Check the new data is available under the correct path
        metadata = get_metadata(path="/products/2/")
        self.assertEqual(metadata.title.value, u"New Title")

    def test_useful_error_messages(self):
        """ Tests that the system gracefully handles a developer error 
            (eg exception in get_absolute_url).
        """
        from django.core.urlresolvers import NoReverseMatch
        try:
            self.page.type = "a type with spaces!" # this causes get_absolute_url() to fail
            self.page.save()
            self.fail("No exception raised on developer error.")
        except NoReverseMatch:
            pass

    def test_missing_meta(self):
        """ Check that no exceptions are raised when the metadata object is missing. """
        try:
            self.page_metadata.delete()
            self.page.title = "A New Page Title"
            self.page.save()
            Coverage._meta.get_model('modelinstance').objects.get(_content_type=self.page_content_type, _object_id=self.page.id).delete()
            self.page.type = "a-new-type"
            self.page.save()
            Coverage._meta.get_model('modelinstance').objects.get(_content_type=self.page_content_type, _object_id=self.page.id).delete()
            self.page.delete()
        except Exception, e:
            self.fail("Exception raised inappropriately: %r" % e)

    def test_path_change(self):
        """ Check the ability to change the path of metadata. """
        self.page.type = "new-type"
        self.page.save()
        metadata_1 = Coverage._meta.get_model('modelinstance').objects.get(_path=self.page.get_absolute_url())
        metadata_2 = Coverage._meta.get_model('modelinstance').objects.get(_content_type=self.page_content_type, _object_id=self.page.id)
        self.assertEqual(metadata_1.id, metadata_2.id)

        self.assertEqual(get_metadata(path=self.page.get_absolute_url()).title.value, 'Page title')

    def test_delete_object(self):
        """ Tests that an object can be deleted, and the metadata is deleted with it. """
        num_metadata = Coverage._meta.get_model('modelinstance').objects.all().count()
        old_path = self.page.get_absolute_url()
        self.page.delete()
        self.assertEqual(Coverage._meta.get_model('modelinstance').objects.all().count(), num_metadata - 1)
        self.assertEqual(Coverage._meta.get_model('modelinstance').objects.filter(_path=old_path).count(), 0)

    def test_group(self):
        """ Checks that groups can be accessed directly. """
        path = self.path_metadata._path
        self.path_metadata.raw1 = "<title>Raw 1</title>"
        self.path_metadata.raw2 = "<title>Raw 1</title>"
        self.path_metadata.help_text1 = "Help Text 1"
        self.path_metadata.help_text3 = "Help Text 3"
        self.path_metadata.help_text4 = "Help Text 4"
        self.path_metadata.save()

        self.assertEqual(get_metadata(path).advanced, u'<title>Raw 1</title>\n<title>Raw 1</title>')
        self.assertEqual(get_metadata(path).help_text, u'''<help_text1>Help Text 1</help_text1>

<help_text3>Help Text 3</help_text3>
<help_text4>Help Text 4</help_text4>''')

    def test_wrong_name(self):
        """ Missing attribute should raise an AttributeError. """
        path = self.path_metadata._path
        metadata = get_metadata(path)
        try:
            metadata.this_does_not_exist
        except AttributeError:
            pass
        else:
            self.fail("AttributeError should be raised on missing FormattedMetadata attribute.")

class ValueResolution(TestCase):
    """ Value resolution (unit tests).
    """
    def setUp(self):
        InstanceMetadata = Coverage._meta.get_model('modelinstance')
        ModelMetadata = Coverage._meta.get_model('model')
        ViewMetadata = Coverage._meta.get_model('view')

        self.page1 = Page.objects.create(title=u"MD Page One Title", type=u"page-one-type", content=u"Page one content.")
        self.page2 = Page.objects.create(type=u"page-two-type", content=u"Page two content.")

        self.page_content_type = ContentType.objects.get_for_model(Page)

        self.metadata1 = InstanceMetadata.objects.get(_content_type=self.page_content_type, _object_id=self.page1.id)
        self.metadata1.keywords = "MD Keywords"
        self.metadata1.save()
        self.metadata2 = InstanceMetadata.objects.get(_content_type=self.page_content_type, _object_id=self.page2.id)

        self.model_metadata = ModelMetadata(_content_type=self.page_content_type)
        self.model_metadata.title = u"MMD { Title"
        self.model_metadata.keywords = u"MMD Keywords, {{ page.type }}, more keywords"
        self.model_metadata.description = u"MMD Description for {{ page }} and {{ page }}"
        self.model_metadata.save()

        self.context1 = get_metadata(path=self.page1.get_absolute_url())
        self.context2 = get_metadata(path=self.page2.get_absolute_url())

        self.view_metadata = ViewMetadata.objects.create(_view="userapp_my_view")
        self.view_metadata.title = "MD {{ text }} Title"
        self.view_metadata.keywords = "MD {{ text }} Keywords"
        self.view_metadata.description = "MD {{ text }} Description"
        self.view_metadata.save()

    def test_direct_data(self):
        """ Check data is used directly when it is given. """
        self.assertEqual(self.context1.keywords.value, u'MD Keywords')

    def test_populate_from_literal(self):
        # Explicit literal
        self.assertEqual(self.context1.populate_from3.value, u'efg')
        # Implicit literal is not evaluated (None)
        self.assertEqual(self.context1.populate_from4.value, None)
        self.assertEqual(self.context1.populate_from5.value, None)

    def test_populate_from_callable(self):
        # Callable given as a string
        self.assertEqual(self.context1.populate_from1.value, u'wxy')
        # Callable given as callable (method)
        self.assertEqual(self.context1.populate_from7.value, u'model instance content: Page one content.')

    def test_populate_from_field(self):
        # Data direct from another field
        self.assertEqual(self.context1.populate_from6.value, u'MD Keywords')
        # Data direct from another field's populate_from
        self.assertEqual(self.context1.populate_from2.value, None)

    def test_fallback_order(self):
        path = self.page1.get_absolute_url()
        # Collect instances from all four metadata model for the same path
        # Each will have a title (ie field with populate_from) and a heading (ie field without populate_from)
        path_md = Coverage._meta.get_model('path').objects.create(_path=path, title='path title', heading="path heading")
        modelinstance_md = self.metadata1
        model_md = self.model_metadata
        view_md = Coverage._meta.get_model('view').objects.create(_view='userapp_page_detail', title='view title', heading="view heading")
        # Correct some values
        modelinstance_md.title = "model instance title"
        modelinstance_md.heading = "model instance heading"
        modelinstance_md.save()
        model_md.title = "model title"
        model_md.heading = "model heading"
        model_md.save()
        # A convenience function for future checks
        def check_values(title, heading, heading2):
            self.assertEqual(get_metadata(path=path).title.value, title)
            self.assertEqual(get_metadata(path=path).heading.value, heading)
            self.assertEqual(get_metadata(path=path).populate_from2.value, heading2)

        # Path is always found first
        check_values("path title", "path heading", "path heading")

        # populate_from is from the path model first
        path_md.title = ""
        path_md.save()
        check_values("example.com", "path heading", "path heading")

        # a field without populate_from just needs to be blank to fallback (heading)
        # a field with populate_from needs to be deleted (title) or have populate_from resolve to blank (populate_from2)
        path_md.heading = ""
        path_md.save()
        check_values("example.com", "model instance heading", "model instance heading")

        path_md.delete()
        check_values("model instance title", "model instance heading", "model instance heading")
        
        modelinstance_md.title = ""
        modelinstance_md.heading = ""
        modelinstance_md.save()
        check_values("example.com", "model heading", "model heading")

        modelinstance_md.delete()
        model_md.delete()
        check_values("view title", "view heading", "view heading")

        # Nothing matches, no metadata shown # TODO: Should populate_from be tried?
        view_md.delete()
        check_values("example.com", None, None)

    def test_fallback_order2(self):
        """ Checks a conflict between populate_from and model metadata. """
        path = self.page1.get_absolute_url()
        modelinstance_md = self.metadata1
        model_md = self.model_metadata

        self.assertEqual(get_metadata(path=path).populate_from3.value, "efg")
        model_md.populate_from3 = "not efg"
        model_md.save()
        self.assertEqual(get_metadata(path=path).populate_from3.value, "not efg")

    def test_model_variable_substitution(self):
        """ Simple check to see if model variable substitution is happening """
        self.assertEqual(self.context2.keywords.value, u'MMD Keywords, page-two-type, more keywords')
        self.assertEqual(self.context1.description.value, u'MMD Description for MD Page One Title and MD Page One Title')
        self.assertEqual(self.context2.description.value, u'MMD Description for Page two content. and Page two content.')

    def test_view_variable_substitution(self):
        """ Simple check to see if view variable substitution is happening """
        response = self.client.get(reverse('userapp_my_view', args=["abc123"]))
        self.assertContains(response, u'<title>MD abc123 Title</title>')
        self.assertContains(response, u'<meta name="keywords" content="MD abc123 Keywords" />')
        self.assertContains(response, u'<meta name="hs:metatag" content="MD abc123 Description" />')

    def test_not_request_context(self):
        """ Tests the view metadata on a view that is not a request context. """
        self.view_metadata._view = "userapp_my_other_view"
        self.view_metadata.save()
        try:
            response = self.client.get(reverse('userapp_my_other_view', args=["abc123"]))
            self.fail("No error raised when RequestContext not used.")
        except TemplateSyntaxError:
            pass


class Formatting(TestCase):
    """ Formatting (unit tests)
    """
    def setUp(self):
        self.path_metadata = Coverage._meta.get_model('path')(
                _path        = "/",
                title       = "The <strong>Title</strong>",
                heading     = "The <em>Heading</em>",
                keywords    = 'Some, keywords", with\n other, chars\'',
                description = "A \n description with \" interesting\' chars.",
                raw1        = '<meta name="author" content="seo" /><hr /> ' 
                              'No text outside tags please.',
                raw2        = '<meta name="author" content="seo" />'
                              '<script>make_chaos();</script>')
        self.path_metadata.save()

        self.metadata = get_metadata(path="/")
    
    def test_html(self):
        """ Tests html generation is performed correctly.
        """
        exp = """<title>The <strong>Title</strong></title>
<hs:tag>The <em>Heading</em></hs:tag>
<meta name="keywords" content="Some, keywords&quot;, with,  other, chars&#39;" />
<meta name="hs:metatag" content="A   description with &quot; interesting&#39; chars." />
<meta name="author" content="seo" />
<meta name="author" content="seo" />"""
        assert unicode(self.metadata).strip() == exp.strip(), "Incorrect html:\n" + unicode(self.metadata) + "\n\n" + unicode(exp)

    def test_description(self):
        """ Tests the tag2 is cleaned correctly. """
        exp = "A   description with &quot; interesting&#39; chars."
        self.assertEqual(self.metadata.description.value, exp)
        exp = '<meta name="hs:metatag" content="%s" />' % exp
        self.assertEqual(unicode(self.metadata.description), exp)

    def test_keywords(self):
        """ Tests keywords are cleaned correctly. """
        exp = "Some, keywords&quot;, with,  other, chars&#39;"
        self.assertEqual(self.metadata.keywords.value, exp)
        exp = '<meta name="keywords" content="%s" />' % exp
        self.assertEqual(unicode(self.metadata.keywords), exp)

    def test_inline_tags(self):
        """ Tests the title is cleaned correctly. """
        exp = 'The <strong>Title</strong>'
        self.assertEqual(self.metadata.title.value, exp)
        exp = '<title>%s</title>' % exp
        self.assertEqual(unicode(self.metadata.title), exp)

    def test_inline_tags2(self):
        """ Tests the title is cleaned correctly. """
        self.path_metadata.title = "The <strong id=\"mytitle\">Title</strong>"
        self.path_metadata.save()
        metadata = get_metadata(self.path_metadata._path)
        exp = 'The <strong id=\"mytitle\">Title</strong>'
        self.assertEqual(metadata.title.value, exp)
        exp = '<title>%s</title>' % exp
        self.assertEqual(unicode(metadata.title), exp)

    def test_inline_tags3(self):
        """ Tests the title is cleaned correctly. """
        self.path_metadata.title = "The < strong >Title</ strong >"
        self.path_metadata.save()
        metadata = get_metadata(self.path_metadata._path)
        exp = 'The < strong >Title</ strong >'
        self.assertEqual(metadata.title.value, exp)
        exp = '<title>%s</title>' % exp
        self.assertEqual(unicode(metadata.title), exp)

    def test_inline_tags4(self):
        """ Tests the title is cleaned correctly. """
        self.path_metadata.title = "The <strong class=\"with&quot;inside\">Title</strong>"
        self.path_metadata.save()
        metadata = get_metadata(self.path_metadata._path)
        exp = 'The <strong class="with&quot;inside">Title</strong>'
        self.assertEqual(metadata.title.value, exp)
        exp = '<title>%s</title>' % exp
        self.assertEqual(unicode(metadata.title), exp)

    def test_inline_tags5(self):
        """ Tests the title is cleaned correctly. """
        self.path_metadata.title = "The Title <!-- with a comment -->"
        self.path_metadata.save()
        metadata = get_metadata(self.path_metadata._path)
        exp = 'The Title <!-- with a comment -->'
        self.assertEqual(metadata.title.value, exp)
        exp = '<title>%s</title>' % exp
        self.assertEqual(unicode(metadata.title), exp)

    def test_forbidden_tags(self):
        """ Tests the title is cleaned correctly. """
        self.path_metadata.title = "The <div>Title</div>"
        self.path_metadata.save()
        metadata = get_metadata(self.path_metadata._path)
        exp = 'The &lt;div&gt;Title&lt;/div&gt;'
        self.assertEqual(metadata.title.value, exp)
        exp = '<title>%s</title>' % exp
        self.assertEqual(unicode(metadata.title), exp)

    def test_raw1(self):
        """ Tests that raw fields in head are cleaned correctly. 
        """
        exp = '<meta name="author" content="seo" />'
        self.assertEqual(self.metadata.raw1.value, exp)
        self.assertEqual(unicode(self.metadata.raw1), exp)

    def test_raw2(self):
        """ Tests that raw fields in head are cleaned correctly. 
        """
        exp = '<meta name="author" content="seo" />'
        self.assertEqual(self.metadata.raw2.value, exp)
        self.assertEqual(unicode(self.metadata.raw2), exp)

    def test_raw3(self):
        """ Checks that raw fields aren't cleaned too enthusiastically  """
        self.path_metadata.raw1 = '<title>Raw title 1</title>'
        self.path_metadata.raw2 = '<title>Raw title 2</title>'
        self.path_metadata.save()
        metadata = get_metadata(path="/")

        exp = '<title>Raw title 1</title>'
        self.assertEqual(metadata.raw1.value, exp)
        self.assertEqual(unicode(metadata.raw1), exp)
        exp = '<title>Raw title 2</title>'
        self.assertEqual(metadata.raw2.value, exp)
        self.assertEqual(unicode(metadata.raw2), exp)


class Definition(TransactionTestCase):
    """ Definition (System tests)
        + if "head" is True, tag is automatically included in the head
        + if "name" is included, that is the name of the given tag, otherwise, the field name is used
        + if verbose_name is used, pass on to field (through field_kwargs)
        + if the field argument given, that Django field type is used
        + if editable is set to False, no Django model field is created. The value is always from populate_from
        + if choices is given it is passed onto the field, (expanded if just a list of strings)
    """

    def test_backends(self):
        self.assertEqual(Coverage._meta.models.keys(), ['path', 'modelinstance', 'model', 'view'])
        self.assertEqual(WithBackends._meta.models.keys(), ['view', 'path'])

    def test_help_text_direct(self):
        self.assert_help_text('help_text1', "Some help text 1.")

    def test_help_text_class(self):
        self.assert_help_text('help_text2', "Updated help text2.")

    def test_help_text_field(self):
        self.assert_help_text('help_text6', "Some help text 6.")
        self.assert_help_text('help_text5', "If empty, tag two will be used.")

    def test_help_text_callable(self):
        self.assert_help_text('help_text3', "Some help text 3.")
        self.assert_help_text('help_text4', "If empty, Always xyz")

    def test_help_text_literal(self):
        self.assert_help_text('populate_from3', "If empty, \"efg\" will be used.")

    def assert_help_text(self, name, text):
        self.assertEqual(Coverage._meta.get_model('path')._meta.get_field(name).help_text, text)
        self.assertEqual(Coverage._meta.get_model('modelinstance')._meta.get_field(name).help_text, text)
        self.assertEqual(Coverage._meta.get_model('model')._meta.get_field(name).help_text, text)
        self.assertEqual(Coverage._meta.get_model('view')._meta.get_field(name).help_text, text)

    def test_uniqueness(self):
        # Check a path for uniqueness
        Coverage._meta.get_model('path').objects.create(_path="/unique/")
        try:
            Coverage._meta.get_model('path').objects.create(_path="/unique/")
            self.fail("Exception not raised when duplicate path created")
        except IntegrityError:
            transaction.rollback()

        # Check that uniqueness handles sites correctly
        current_site = Site.objects.get_current()
        another_site = Site.objects.create(id=current_site.id+1)
        WithSites._meta.get_model('path').objects.create(_site=current_site, _path="/unique/")
        pmd = WithSites._meta.get_model('path').objects.create(_site=another_site, _path="/unique/")
        try:
            WithSites._meta.get_model('path').objects.create(_site=current_site, _path="/unique/")
            self.fail("Exception not raised when duplicate path/site combination created")
        except IntegrityError:
            transaction.rollback()


class MetaOptions(TestCase):
    """ Meta options (System tests)
        + groups: these elements are grouped together in the admin and can be output together in the template
        + use_sites: add a 'site' field to each model. Non-matching sites are removed, null is allowed, meaning all sites match.
        + use_i18n:
        + use_redirect:
        + use_cache:
        + seo_models: list of models and/or apps which are available for model instance metadata
        + seo_views: list of models and/or apps which are available for model instance metadata
        - verbose_name(_plural): this is passed onto Django
        + HelpText: Help text can be applied in bulk by using a special class, like 'Meta'
    """

    def test_use_cache(self):
        """ Checks that cache is being used when use_cache is set.
            Will only work if cache backend is not dummy.
        """
        if 'dummy' not in settings.CACHE_BACKEND:
            path = '/'
            hexpath = md5_constructor(iri_to_uri(path)).hexdigest() 

            #unicode(seo_get_metadata(path, name="Coverage"))
            unicode(seo_get_metadata(path, name="WithCache"))

            self.assertEqual(cache.get('rollyourown.seo.Coverage.%s.title' % hexpath), None)
            self.assertEqual(cache.get('rollyourown.seo.WithCache.%s.title' % hexpath), "1234")
            self.assertEqual(cache.get('rollyourown.seo.WithCache.%s.subtitle' % hexpath), "")

    def test_use_cache_site(self):
        """ Checks that the cache plays nicely with sites.
        """
        if 'dummy' not in settings.CACHE_BACKEND:
            path = '/'
            site = Site.objects.get_current()
            hexpath = md5_constructor(iri_to_uri(site.domain+path)).hexdigest()

            #unicode(seo_get_metadata(path, name="Coverage"))
            unicode(seo_get_metadata(path, name="WithCacheSites", site=site))

            self.assertEqual(cache.get('rollyourown.seo.Coverage.%s.title' % hexpath), None)
            self.assertEqual(cache.get('rollyourown.seo.WithCacheSites.%s.title' % hexpath), "1234")
            self.assertEqual(cache.get('rollyourown.seo.WithCacheSites.%s.subtitle' % hexpath), "")

    def test_use_cache_i18n(self):
        """ Checks that the cache plays nicely with i18n. 
        """
        if 'dummy' not in settings.CACHE_BACKEND:
            path = '/'
            hexpath = md5_constructor(iri_to_uri(path)).hexdigest()

            #unicode(seo_get_metadata(path, name="Coverage"))
            unicode(seo_get_metadata(path, name="WithCacheI18n", language='de'))

            self.assertEqual(cache.get('rollyourown.seo.Coverage.%s.de.title' % hexpath), None)
            self.assertEqual(cache.get('rollyourown.seo.WithCacheI18n.%s.en.title' % hexpath), None)
            self.assertEqual(cache.get('rollyourown.seo.WithCacheI18n.%s.de.title' % hexpath), "1234")
            self.assertEqual(cache.get('rollyourown.seo.WithCacheI18n.%s.de.subtitle' % hexpath), "")


class Templates(TestCase):
    """ Templates (System tests)

        To write:
        - {% get_metadata ClassName on site in language for path as var %} All at once!
    """
    def setUp(self):
        self.path = "/abc/"
        Coverage._meta.get_model('path').objects.create(_path=self.path, title="A Title", description="A Description", raw1="Some raw text")
        self.metadata = get_metadata(path=self.path)
        self.context = {}

    def test_basic(self):
        self.deregister_alternatives()
        self.compilesTo("{% get_metadata %}", unicode(self.metadata))
        self.compilesTo("{% get_metadata as var %}{{ var }}", unicode(self.metadata))

    def test_for_path(self):
        self.deregister_alternatives()
        path = self.path
        self.path = "/another-path/"
        other_path = "/a-third-path/"
        # Where the path does not find a metadata object, defaults should be returned
        self.compilesTo("{%% get_metadata for \"%s\" %%}" % other_path, "<title>example.com</title>")
        self.compilesTo("{%% get_metadata for \"%s\" as var %%}{{ var }}" % other_path, "<title>example.com</title>")

        self.compilesTo("{%% get_metadata for \"%s\" %%}" % path, unicode(self.metadata))
        self.compilesTo("{%% get_metadata for \"%s\" as var %%}{{ var }}" % path, unicode(self.metadata))

    def test_for_obj(self):
        self.deregister_alternatives()
        path = self.path
        self.path = "/another-path/"
        # Where the path does not find a metadata object, defaults should be returned
        self.context = {'obj': {'get_absolute_url': lambda: "/a-third-path/"}}
        self.compilesTo("{% get_metadata for obj %}", "<title>example.com</title>")
        self.compilesTo("{% get_metadata for obj as var %}{{ var }}", "<title>example.com</title>")

        self.context = {'obj': {'get_absolute_url': lambda: path}}
        self.compilesTo("{% get_metadata for obj %}", unicode(self.metadata))
        self.compilesTo("{% get_metadata for obj as var %}{{ var }}", unicode(self.metadata))

    def test_for_obj_no_metadata(self):
        """ Checks that defaults are used when no metadata object (previously) exists. 
            The relevant path is also removed so that the object's link to the database is used.
        """
        self.deregister_alternatives()

        # Remove all metadata
        Metadata = Coverage._meta.get_model('modelinstance')

        # Create a page with metadata (with a path that get_metadata won't find)
        page = Page.objects.create(title=u"Page Title", type="nometadata", content="no meta data")
        content_type = ContentType.objects.get_for_model(Page)
        Metadata.objects.filter(_content_type=content_type, _object_id=page.pk).update(title="Page Title", _path="/different/")
        
        expected_output = '<title>Page Title</title>'

        # Check the output of the template is correct when the metadata exists
        self.context = {'obj': page}
        self.compilesTo("{% get_metadata for obj %}", expected_output)
        self.compilesTo("{% get_metadata for obj as var %}{{ var }}", expected_output)
        self.compilesTo("{% get_metadata for obj as var %}{{ var.populate_from7 }}", 
                '<populate_from7>model instance content: no meta data</populate_from7>')

        # Check the output is correct when there is no metadata
        Metadata.objects.filter(_content_type=content_type, _object_id=page.pk).delete()
        self.compilesTo("{% get_metadata for obj %}", "<title>example.com</title>")
        self.compilesTo("{% get_metadata for obj as var %}{{ var }}", "<title>example.com</title>")
        self.compilesTo("{% get_metadata for obj as var %}{{ var.populate_from7 }}", 
                '<populate_from7>model instance content: no meta data</populate_from7>')

    def test_for_obj_no_path(self):
        InstanceMetadata = Coverage._meta.get_model('modelinstance')
        self.deregister_alternatives()

        # NoPath objects can exist without a matching metadata instance
        obj1 = NoPath.objects.create()
        obj2 = NoPath.objects.create()
        content_type = ContentType.objects.get_for_model(NoPath)
        obj_metadata = InstanceMetadata.objects.create(_content_type=content_type, _object_id=obj2.id, title="Correct Title")

        self.context = {'obj': obj2}
        expected_metadata = '<title>Correct Title</title>'
        self.compilesTo("{% get_metadata for obj %}", expected_metadata)
        self.compilesTo("{% get_metadata for obj as var %}{{ var }}", expected_metadata)

        # Where the object does not link to a metadata object, defaults should be returned
        self.context = {'obj': obj1}
        self.compilesTo("{% get_metadata for obj %}", "<title>example.com</title>")
        self.compilesTo("{% get_metadata for obj as var %}{{ var }}", "<title>example.com</title>")

    def test_wrong_class_name(self):
        self.compilesTo("{% get_metadata WithSites %}", "")
        self.compilesTo("{% get_metadata WithSites as var %}{{ var }}", "")

    def test_bad_class_name(self):
        try:
            self.compilesTo("{% get_metadata ThisDoesNotExist %}", "This should have raised an exception")
        except TemplateSyntaxError:
            pass
        try:
            self.compilesTo("{% get_metadata ThisDoesNotExist as var %}{{ var }}", "This should have raised an exception")
        except TemplateSyntaxError:
            pass

    def test_missing_class_name_when_required(self):
        try:
            self.compilesTo("{% get_metadata %}", "This should have raised an exception")
        except TemplateSyntaxError:
            pass

    def test_bad_class_name_when_only_one(self):
        self.deregister_alternatives()
        try:
            self.compilesTo("{% get_metadata ThisDoesNotExist %}", "This should have raised an exception")
        except TemplateSyntaxError:
            pass

    def test_class_name(self):
        self.compilesTo("{% get_metadata Coverage %}", unicode(self.metadata))
        self.compilesTo("{% get_metadata Coverage as var %}{{ var }}", unicode(self.metadata))
        path = self.path
        self.context = {'obj': {'get_absolute_url': lambda: path}}
        self.path = "/another-path/"
        self.compilesTo("{%% get_metadata Coverage for \"%s\" %%}" % path, unicode(self.metadata))
        self.compilesTo("{%% get_metadata Coverage for \"%s\" as var %%}{{ var }}"% path, unicode(self.metadata))
        self.compilesTo("{% get_metadata Coverage for obj %}", unicode(self.metadata))
        self.compilesTo("{% get_metadata Coverage for obj as var %}{{ var }}", unicode(self.metadata))

    def test_variable_group(self):
        self.deregister_alternatives()
        self.compilesTo("{% get_metadata as var %}{{ var.advanced }}", unicode(self.metadata.raw1))

    def test_variable_field(self):
        self.deregister_alternatives()
        self.compilesTo("{% get_metadata as var %}{{ var.raw1 }}", unicode(self.metadata.raw1))

    def test_variable_field_value(self):
        self.deregister_alternatives()
        self.compilesTo("{% get_metadata as var %}{{ var.raw1.value }}", "Some raw text")

    def test_variable_field_name(self):
        self.deregister_alternatives()
        self.compilesTo("{% get_metadata as var %}{{ var.raw1.field.name }}", "raw1")

    def test_language(self):
        WithI18n._meta.get_model('path').objects.create(_path=self.path, title="A Title", _language="de")
        metadata = seo_get_metadata(path=self.path, name="WithSites", language="de")
        self.compilesTo('{% get_metadata WithI18n in "de" %}', unicode(metadata))
        self.compilesTo('{% get_metadata WithI18n in "en" %}', "")

    def test_site(self):
        new_site = Site.objects.create(domain="new-example.com", name="New example")
        WithSites._meta.get_model('path').objects.create(_path=self.path, title="A Title", _site=new_site)
        metadata = seo_get_metadata(path=self.path, name="WithSites", site=new_site)
        self.compilesTo('{% get_metadata WithI18n on "new-example.com" %}', unicode(metadata))
        self.compilesTo('{% get_metadata WithI18n in "example.com" %}', "")

    def compilesTo(self, input, expected_output):
        """ Asserts that the given template string compiles to the given output. 
        """
        input = '{% load seo %}' + input
        environ = { 
            'PATH_INFO': self.path, 
            'REQUEST_METHOD': 'GET',
            'wsgi.input': FakePayload(''),
            } 
        
        # Create a fake request for our purposes
        request = WSGIRequest(environ) 
        context= RequestContext(request)
        context.update(self.context)
        self.assertEqual(Template(input).render(context).strip(), expected_output.strip())

    def deregister_alternatives(self):
        """ Deregister any alternative metadata classes for the sake of testing. 
            This emulates the situation where there is only one metadata definition.
        """
        self._previous_registry = registry.items()
        for key in registry.keys():
            del registry[key]
        registry['Coverage'] = Coverage

    def tearDown(self):
        # Reregister any missing classes
        if hasattr(self, '_previous_registry'):
            for key, val in self._previous_registry:
                if key not in registry:
                    registry[key] = val


class Random(TestCase):
    """
        - Caching
            - metadata lookups are avoided by caching previous rendering for certain amount of time

    """

    def setUp(self):
        self.Metadata = Coverage._meta.get_model('modelinstance')

        self.page = Page.objects.create(type="abc")
        self.content_type = ContentType.objects.get_for_model(Page)
        self.model_metadata = self.Metadata.objects.get(_content_type=self.content_type,
                                                    _object_id=self.page.id)
        self.context = get_metadata(path=self.model_metadata._path)

    def test_default_fallback(self):
        """ Tests the ability to use the current Site name as a default 
            fallback. 
        """
        from django.contrib.sites.models import Site
        site = Site.objects.get_current()
        self.assertEqual(site.name, self.context.title.value)

    def test_missing_path(self):
        " Checks that a model with a missing path is gracefully ignored. "
        num_metadata = self.Metadata.objects.all().count()
        try:
            no_path = NoPath.objects.create()
        except Exception, e:
            self.fail("Exception inappropriately raised: %r" % e)
        new_num_metadata = self.Metadata.objects.all().count()
        self.assertEqual(num_metadata, new_num_metadata)

    def test_syncdb_populate(self):
        " Checks that syncdb populates the seo metadata. "
        Metadata = Coverage._meta.get_model('modelinstance')
        if not Metadata.objects.all():
            raise Exception("Test case requires instances for model instance metadata")

        self.remove_seo_tables()

        call_command('syncdb', verbosity=0)

        if not Metadata.objects.all():
            self.fail("No metadata objects created.")

    def remove_seo_tables(self):
        from django.core.management.sql import sql_delete
        from django.db import connection
        from django.core.management.color import no_style
        from rollyourown.seo import models as seo_models

        try:
            sql_list = sql_delete(seo_models, no_style(), connection) 
        except TypeError:
            sql_list = sql_delete(seo_models, no_style())
        cursor = connection.cursor()
        try:
            for sql in sql_list:
                cursor.execute(sql)
        except Exception, e:
            transaction.rollback_unless_managed()

    def test_management_populate(self):
        " Checks that populate_metadata command adds relevant metadata instances. "
        Metadata = Coverage._meta.get_model('modelinstance')
        self.page = Page.objects.create(type="def")

        # Check the number of existing metadata instances
        existing_metadata = Metadata.objects.count()
        if existing_metadata < 2:
            raise Exception("Test case requires at least 2 instances for model instance metadata")

        # Remove one metadata, populate_metadata will add it again
        Metadata.objects.all()[0].delete()

        call_command('populate_metadata')

        # Check that we at least have as many as previously
        full_metadata = Metadata.objects.count()
        if full_metadata < existing_metadata:
            self.fail("No metadata objects created.")


class Admin(TestCase):

    def setUp(self):
        # Create and login a superuser for the admin
        user = User(username="admin", is_staff=True, is_superuser=True)
        user.set_password("admin")
        user.save()
        self.client.login(username="admin", password="admin")

    def test_inline_smoke(self):
        """ Tests that no error is raised when viewing an inline in the admin. 
        """
        path = '/admin/userapp/page/add/'
        try:
            response = self.client.get(path)
        except Exception, e:
            self.fail(u"Exception raised at '%s': %s" % (path, e))
        self.assertEqual(response.status_code, 200)

    def test_inline_add(self):
        path = '/admin/userapp/tag/add/'
        data = {
            "name": "Test",
            "seo-coveragemodelinstance-_content_type-_object_id-0-title": "test",
            "seo-coveragemodelinstance-_content_type-_object_id-TOTAL_FORMS": "1",
            "seo-coveragemodelinstance-_content_type-_object_id-INITIAL_FORMS": "0",
            "seo-coveragemodelinstance-_content_type-_object_id-MAX_NUM_FORMS": "1",
            "seo-withsitesmodelinstance-_content_type-_object_id-TOTAL_FORMS": "1",
            "seo-withsitesmodelinstance-_content_type-_object_id-INITIAL_FORMS": "0",
            "seo-withsitesmodelinstance-_content_type-_object_id-MAX_NUM_FORMS": "1",
        }

        try:
            response = self.client.post(path, data, follow=True)
        except Exception, e:
            raise
            self.fail(u"Exception raised at '%s': %s" % (path, e))
        self.assertEqual(response.status_code, 200)

    def test_inline_nonadmin(self):
        """ Checks that a model that can be edited inline in the Admin automatically
            creates an instance when not using the Admin.
        """
        content_type = ContentType.objects.get_for_model(Tag)
        Metadata = Coverage._meta.get_model('modelinstance')

        tag = Tag(name="noinline")
        tag.save()
        try:
            Metadata.objects.get(_content_type=content_type, _object_id=tag.pk)
        except Metadata.DoesNotExist:
            self.fail("No metadata automatically created on .save()")

        # Try with create
        tag = Tag.objects.create(name="noinline2")
        try:
            Metadata.objects.get(_content_type=content_type, _object_id=tag.pk)
        except Metadata.DoesNotExist:
            self.fail("No metadata automatically created after using .create()")

    def test_autoinline(self):
        for model in ('tag', 'page', 'product'):
            path = '/alt-admin/userapp/%s/add/' % model
            try:
                response = self.client.get(path)
            except Exception, e:
                self.fail(u"Exception raised at '%s': %s" % (path, e))
            self.assertContains(response, "seo-coveragemodelinstance-_content_type", status_code=200)
            self.assertNotContains(response, "seo-withsitesmodelinstance-_content_type")
            self.assertContains(response, "seo-withseomodelsmodelinstance-_content_type", status_code=200)

    def test_inline_add(self):
        path = '/admin/seo/coveragemodel/add/'
        data = {
            "title": "Testing",
            "_content_type": u'3',
        }

        try:
            response = self.client.post(path, data, follow=True)
        except Exception, e:
            raise
            self.fail(u"Exception raised at '%s': %s" % (path, e))
        self.assertEqual(response.status_code, 200)

########NEW FILE########
__FILENAME__ = urls
#!/usr/bin/env python
# -*- coding: UTF-8 -*-
from django.conf.urls.defaults import *

urlpatterns = patterns('userapp.views', 
    url(r'^pages/([\w\d-]+)/', 'page_detail', name="userapp_page_detail"),
    url(r'^products/(\d+)/', 'product_detail', name="userapp_product_detail"),
    url(r'^tags/(.+)/', 'tag_detail', name="userapp_tag"),
    url(r'^my/view/(.+)/', 'my_view', name="userapp_my_view"),
    url(r'^my/other/view/(.+)/', 'my_other_view', name="userapp_my_other_view"),
    )

########NEW FILE########
__FILENAME__ = views
from django.shortcuts import get_object_or_404, render_to_response
from userapp.models import Page, Tag, Product
from django.template.context import RequestContext

def page_detail(request, page_type):
    page = get_object_or_404(Page, type=page_type)
    return render_to_response('object_detail.html', {'object': page})

def product_detail(request, product_id):
    page = get_object_or_404(Product, id=product_id)
    return render_to_response('object_detail.html', {'object': product})

def tag_detail(request, tag_name):
    tag = get_object_or_404(Tag, name=tag_name)
    return render_to_response('object_detail.html', {'object': tag})

def my_view(request, text):
    context = {'text': text}
    return render_to_response('my_view.html', context, context_instance=RequestContext(request))

def my_other_view(request, text):
    context = {'text': text}
    return render_to_response('my_view.html', context)

########NEW FILE########
__FILENAME__ = admin
# -*- coding: utf-8 -*-

from django import forms
from django.contrib import admin
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.utils.encoding import smart_unicode
from django.forms.models import fields_for_model
from django.utils.translation import ugettext_lazy as _
from django.utils.text import capfirst

from rollyourown.seo.utils import get_seo_content_types
from rollyourown.seo.systemviews import get_seo_views

# TODO Use groups as fieldsets

# Varients without sites support

class PathMetadataAdmin(admin.ModelAdmin):
    list_display = ('_path',)

class ModelInstanceMetadataAdmin(admin.ModelAdmin):
    list_display = ('_path', '_content_type', '_object_id')

class ModelMetadataAdmin(admin.ModelAdmin):
    list_display = ('_content_type',)

class ViewMetadataAdmin(admin.ModelAdmin):
    list_display = ('_view', )


# Varients with sites support

class SitePathMetadataAdmin(admin.ModelAdmin):
    list_display = ('_path', '_site')
    list_filter = ('_site',)

class SiteModelInstanceMetadataAdmin(admin.ModelAdmin):
    list_display = ('_path', '_content_type', '_object_id', '_site')
    list_filter = ('_site', '_content_type')

class SiteModelMetadataAdmin(admin.ModelAdmin):
    list_display = ('_content_type', '_site')
    list_filter = ('_site',)

class SiteViewMetadataAdmin(admin.ModelAdmin):
    list_display = ('_view', '_site')
    list_filter = ('_site',)


def register_seo_admin(admin_site, metadata_class):
    if metadata_class._meta.use_sites:
        path_admin = SitePathMetadataAdmin
        model_instance_admin = SiteModelInstanceMetadataAdmin
        model_admin = SiteModelMetadataAdmin
        view_admin = SiteViewMetadataAdmin
    else:
        path_admin = PathMetadataAdmin
        model_instance_admin = ModelInstanceMetadataAdmin
        model_admin = ModelMetadataAdmin
        view_admin = ViewMetadataAdmin

    class ModelAdmin(model_admin):
        form = get_model_form(metadata_class)

    class ViewAdmin(view_admin):
        form = get_view_form(metadata_class)

    class PathAdmin(path_admin):
        form = get_path_form(metadata_class)

    class ModelInstanceAdmin(model_instance_admin):
        pass

    _register_admin(admin_site, metadata_class._meta.get_model('path'), PathAdmin)
    _register_admin(admin_site, metadata_class._meta.get_model('modelinstance'), ModelInstanceAdmin)
    _register_admin(admin_site, metadata_class._meta.get_model('model'), ModelAdmin)
    _register_admin(admin_site, metadata_class._meta.get_model('view'), ViewAdmin)


def _register_admin(admin_site, model, admin_class):
    """ Register model in the admin, ignoring any previously registered models.
        Alternatively it could be used in the future to replace a previously 
        registered model.
    """
    try:
        admin_site.register(model, admin_class)
    except admin.sites.AlreadyRegistered:
        pass


class MetadataFormset(generic.BaseGenericInlineFormSet):
    def _construct_form(self, i, **kwargs):
        """ Override the method to change the form attribute empty_permitted """
        form = super(MetadataFormset, self)._construct_form(i, **kwargs)
        # Monkey patch the form to always force a save.
        # It's unfortunate, but necessary because we always want an instance
        # Affect on performance shouldn't be too great, because ther is only
        # ever one metadata attached
        form.empty_permitted = False
        form.has_changed = lambda: True

        # Set a marker on this object to prevent automatic metadata creation
        # This is seen by the post_save handler, which then skips this instance.
        if self.instance:
            self.instance.__seo_metadata_handled = True

        return form


def get_inline(metadata_class):
    attrs = {
        'max_num': 1, 
        'extra': 1, 
        'model': metadata_class._meta.get_model('modelinstance'), 
        'ct_field': "_content_type",
        'ct_fk_field': "_object_id",
        'formset': MetadataFormset,
        }
    return type('MetadataInline', (generic.GenericStackedInline,), attrs)


def get_model_form(metadata_class):
    model_class = metadata_class._meta.get_model('model')

    # Restrict content type choices to the models set in seo_models
    content_types = get_seo_content_types(metadata_class._meta.seo_models)
    content_type_choices = [(x._get_pk_val(), smart_unicode(x)) for x in ContentType.objects.filter(id__in=content_types)]

    # Get a list of fields, with _content_type at the start
    important_fields = ['_content_type'] + core_choice_fields(metadata_class)
    _fields = important_fields + fields_for_model(model_class, exclude=important_fields).keys()

    class ModelMetadataForm(forms.ModelForm):
        _content_type = forms.ChoiceField(label=capfirst(_("model")), choices=content_type_choices)

        class Meta:
            model = model_class
            fields = _fields

        def clean__content_type(self):
            value = self.cleaned_data['_content_type']
            try:
                return ContentType.objects.get(pk=int(value))
            except (ContentType.DoesNotExist, ValueError):
                raise forms.ValidationError("Invalid ContentType")

    return ModelMetadataForm


def get_path_form(metadata_class):
    model_class = metadata_class._meta.get_model('path')

    # Get a list of fields, with _view at the start
    important_fields = ['_path'] + core_choice_fields(metadata_class)
    _fields = important_fields + fields_for_model(model_class, exclude=important_fields).keys()

    class ModelMetadataForm(forms.ModelForm):
        class Meta:
            model = model_class
            fields = _fields

    return ModelMetadataForm


def get_view_form(metadata_class):
    model_class = metadata_class._meta.get_model('view')

    # Restrict content type choices to the models set in seo_models
    view_choices = [(key, " ".join(key.split("_"))) for key in get_seo_views(metadata_class)]
    view_choices.insert(0, ("", "---------"))

    # Get a list of fields, with _view at the start
    important_fields = ['_view'] + core_choice_fields(metadata_class)
    _fields = important_fields + fields_for_model(model_class, exclude=important_fields).keys()

    class ModelMetadataForm(forms.ModelForm):
        _view = forms.ChoiceField(label=capfirst(_("view")), choices=view_choices, required=False)

        class Meta:
            model = model_class
            fields = _fields

    return ModelMetadataForm


def core_choice_fields(metadata_class):
    """ If the 'optional' core fields (_site and _language) are required, 
        list them here. 
    """
    fields = []
    if metadata_class._meta.use_sites:
        fields.append('_site')
    if metadata_class._meta.use_i18n:
        fields.append('_language')
    return fields


def _monkey_inline(model, admin_class_instance, metadata_class, inline_class, admin_site):
    """ Monkey patch the inline onto the given admin_class instance. """
    if model in metadata_class._meta.seo_models:
        # *Not* adding to the class attribute "inlines", as this will affect
        # all instances from this class. Explicitly adding to instance attribute.
        admin_class_instance.__dict__['inlines'] = admin_class_instance.inlines + [inline_class]

        # Because we've missed the registration, we need to perform actions
        # that were done then (on admin class instantiation)
        inline_instance = inline_class(admin_class_instance.model, admin_site)
        admin_class_instance.inline_instances.append(inline_instance)

def _with_inline(func, admin_site, metadata_class, inline_class):
    """ Decorator for register function that adds an appropriate inline."""   

    def register(model_or_iterable, admin_class=None, **options):
        # Call the (bound) function we were given.
        # We have to assume it will be bound to admin_site
        func(model_or_iterable, admin_class, **options)
        _monkey_inline(model_or_iterable, admin_site._registry[model_or_iterable], metadata_class, inline_class, admin_site)

    return register

def auto_register_inlines(admin_site, metadata_class):
    """ This is a questionable function that automatically adds our metadata
        inline to all relevant models in the site. 
    """
    inline_class = get_inline(metadata_class)

    for model, admin_class_instance in admin_site._registry.items():
        _monkey_inline(model, admin_class_instance, metadata_class, inline_class, admin_site)

    # Monkey patch the register method to automatically add an inline for this site.
    # _with_inline() is a decorator that wraps the register function with the same injection code
    # used above (_monkey_inline).
    admin_site.register = _with_inline(admin_site.register, admin_site, metadata_class, inline_class)


########NEW FILE########
__FILENAME__ = backends
#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from django.utils.translation import ugettext_lazy as _
from django.conf import settings
from django.db import models
from django.contrib.sites.models import Site
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.template import Template, Context
from django.utils.datastructures import SortedDict

from rollyourown.seo.utils import resolve_to_name, NotSet, Literal

RESERVED_FIELD_NAMES = ('_metadata', '_path', '_content_type', '_object_id',
                        '_content_object', '_view', '_site', 'objects', 
                        '_resolve_value', '_set_context', 'id', 'pk' )

backend_registry = SortedDict()

class MetadataBaseModel(models.Model):

    class Meta:
        abstract = True

    def __init__(self, *args, **kwargs):
        super(MetadataBaseModel, self).__init__(*args, **kwargs)

        # Provide access to a class instance
        # TODO Rename to __metadata
        self._metadata = self.__class__._metadata()

    # TODO Rename to __resolve_value?
    def _resolve_value(self, name):
        """ Returns an appropriate value for the given name. """
        name = str(name)
        if name in self._metadata._meta.elements:
            element = self._metadata._meta.elements[name]

            # Look in instances for an explicit value
            if element.editable:
                value = getattr(self, name)
                if value:
                    return value

            # Otherwise, return an appropriate default value (populate_from)
            populate_from = element.populate_from
            if callable(populate_from):
                return populate_from(self, **self._populate_from_kwargs())
            elif isinstance(populate_from, Literal):
                return populate_from.value
            elif populate_from is not NotSet:
                return self._resolve_value(populate_from)

        # If this is not an element, look for an attribute on metadata
        try:
            value = getattr(self._metadata, name)
        except AttributeError:
            pass
        else:
            if callable(value):
                if getattr(value, 'im_self', None):
                    return value(self)
                else:
                    return value(self._metadata, self)
            return value

    def _populate_from_kwargs(self):
        return {}


class BaseManager(models.Manager):
    def on_current_site(self, site=None):
        if isinstance(site, Site):
            site_id = site.id
        elif site is not None:
            site_id = site and Site.objects.get(domain=site).id
        else:
            site_id = settings.SITE_ID
        # Exclude entries for other sites
        where = ['_site_id IS NULL OR _site_id=%s']
        return self.get_query_set().extra(where=where, params=[site_id])

    def for_site_and_language(self, site=None, language=None):
        queryset = self.on_current_site(site)
        if language:
            queryset = queryset.filter(_language=language)
        return queryset

# Following is part of an incomplete move to define backends, which will:
#   -  contain the business logic of backends to a short, succinct module
#   -  allow individual backends to be turned on and off
#   -  allow new backends to be added by end developers
#
# A Backend:
#   -  defines an abstract base class for storing the information required to associate metadata with its target (ie a view, a path, a model instance etc)
#   -  defines a method for retrieving an instance
#
# This is not particularly easy.
#   -  unique_together fields need to be defined in the same django model, as some django versions don't enforce the uniqueness when it spans subclasses
#   -  most backends use the path to find a matching instance. The model backend however ideally needs a content_type (found from a model instance backend, which used the path)
#   -  catering for all the possible options (use_sites, use_languages), needs to be done succiently, and at compile time
#
# This means that:
#   -  all fields that share uniqueness (backend fields, _site, _language) need to be defined in the same model
#   -  as backends should have full control over the model, therefore every backend needs to define the compulsory fields themselves (eg _site and _language).
#      There is no way to add future compulsory fields to all backends without editing each backend individually. 
#      This is probably going to have to be a limitataion we need to live with.

class MetadataBackend(object):
    name = None
    verbose_name = None
    unique_together = None

    class __metaclass__(type):
        def __new__(cls, name, bases, attrs):
            new_class = type.__new__(cls, name, bases, attrs)
            backend_registry[new_class.name] = new_class
            return new_class

    def get_unique_together(self, options):
        ut = []
        for ut_set in self.unique_together:
            ut_set = [a for a in ut_set]
            if options.use_sites:
                ut_set.append('_site')
            if options.use_i18n:
                ut_set.append('_language')
            ut.append(tuple(ut_set))
        return tuple(ut)

    def get_manager(self, options):
        _get_instances = self.get_instances

        class _Manager(BaseManager):
            def get_instances(self, path, site=None, language=None, context=None):
                queryset = self.for_site_and_language(site, language)
                return _get_instances(queryset, path, context)

            if not options.use_sites:
                def for_site_and_language(self, site=None, language=None):
                    queryset = self.get_query_set()
                    if language:
                        queryset = queryset.filter(_language=language)
                    return queryset
        return _Manager


    @staticmethod
    def validate(options):
        """ Validates the application of this backend to a given metadata 
        """


class PathBackend(MetadataBackend):
    name = "path"
    verbose_name = "Path"
    unique_together = (("_path",),)

    def get_instances(self, queryset, path, context):
        return queryset.filter(_path=path)

    def get_model(self, options):
        class PathMetadataBase(MetadataBaseModel):
            _path = models.CharField(_('path'), max_length=255, unique=not (options.use_sites or options.use_i18n))
            if options.use_sites:
                _site = models.ForeignKey(Site, null=True, blank=True, verbose_name=_("site"))
            if options.use_i18n:
                _language = models.CharField(_("language"), max_length=5, null=True, blank=True, db_index=True, choices=settings.LANGUAGES)
            objects = self.get_manager(options)()

            def __unicode__(self):
                return self._path

            def _populate_from_kwargs(self):
                return {'path': self._path}

            class Meta:
                abstract = True
                unique_together = self.get_unique_together(options)

        return PathMetadataBase


class ViewBackend(MetadataBackend):
    name = "view"
    verbose_name = "View"
    unique_together = (("_view",),)

    def get_instances(self, queryset, path, context):
        view_name = ""
        if path is not None:
            view_name = resolve_to_name(path)
        return queryset.filter(_view=view_name or "")

    def get_model(self, options):
        class ViewMetadataBase(MetadataBaseModel):
            _view = models.CharField(_('view'), max_length=255, unique=not (options.use_sites or options.use_i18n), default="", blank=True)
            if options.use_sites:
                _site = models.ForeignKey(Site, null=True, blank=True, verbose_name=_("site"))
            if options.use_i18n:
                _language = models.CharField(_("language"), max_length=5, null=True, blank=True, db_index=True, choices=settings.LANGUAGES)
            objects = self.get_manager(options)()

            def _process_context(self, context):
                """ Use the context when rendering any substitutions.  """
                if 'view_context' in context:
                    self.__context = context['view_context']

            def _populate_from_kwargs(self):
                return {'view_name': self._view}
        
            def _resolve_value(self, name):
                value = super(ViewMetadataBase, self)._resolve_value(name)
                try:
                    return _resolve(value, context=self.__context)
                except AttributeError:
                    return value

            def __unicode__(self):
                return self._view
    
            class Meta:
                abstract = True
                unique_together = self.get_unique_together(options)

        return ViewMetadataBase


class ModelInstanceBackend(MetadataBackend):
    name = "modelinstance"
    verbose_name = "Model Instance"
    unique_together = (("_path",), ("_content_type", "_object_id"))

    def get_instances(self, queryset, path, context):
        return queryset.filter(_path=path)

    def get_model(self, options):
        class ModelInstanceMetadataBase(MetadataBaseModel):
            _path = models.CharField(_('path'), max_length=255, editable=False, unique=not (options.use_sites or options.use_i18n))
            _content_type = models.ForeignKey(ContentType, editable=False)
            _object_id = models.PositiveIntegerField(editable=False)
            _content_object = generic.GenericForeignKey('_content_type', '_object_id')
            if options.use_sites:
                _site = models.ForeignKey(Site, null=True, blank=True, verbose_name=_("site"))
            if options.use_i18n:
                _language = models.CharField(_("language"), max_length=5, null=True, blank=True, db_index=True, choices=settings.LANGUAGES)
            objects = self.get_manager(options)()
        
            def __unicode__(self):
                return self._path

            class Meta:
                unique_together = self.get_unique_together(options)
                abstract = True

            def _process_context(self, context):
                context['content_type'] = self._content_type
                context['model_instance'] = self

            def _populate_from_kwargs(self):
                return {'model_instance': self._content_object}

            def save(self, *args, **kwargs):
                try:
                    path_func = self._content_object.get_absolute_url
                except AttributeError:
                    pass
                else:
                    self._path = path_func()
                super(ModelInstanceMetadataBase, self).save(*args, **kwargs)

        return ModelInstanceMetadataBase


class ModelBackend(MetadataBackend):
    name = "model"
    verbose_name = "Model"
    unique_together = (("_content_type",),)

    def get_instances(self, queryset, path, context):
        if context and 'content_type' in context:
            return queryset.filter(_content_type=context['content_type'])

    def get_model(self, options):
        class ModelMetadataBase(MetadataBaseModel):
            _content_type = models.ForeignKey(ContentType)
            if options.use_sites:
                _site = models.ForeignKey(Site, null=True, blank=True, verbose_name=_("site"))
            if options.use_i18n:
                _language = models.CharField(_("language"), max_length=5, null=True, blank=True, db_index=True, choices=settings.LANGUAGES)
            objects = self.get_manager(options)()

            def __unicode__(self):
                return unicode(self._content_type)

            def _process_context(self, context):
                """ Use the given model instance as context for rendering 
                    any substitutions. 
                """
                if 'model_instance' in context:
                    self.__instance = context['model_instance']

            def _populate_from_kwargs(self):
                return {'content_type': self._content_type}
        
            def _resolve_value(self, name):
                value = super(ModelMetadataBase, self)._resolve_value(name)
                try:
                    return _resolve(value, self.__instance._content_object)
                except AttributeError:
                    return value
        
            class Meta:
                abstract = True
                unique_together = self.get_unique_together(options)
        return ModelMetadataBase

    @staticmethod
    def validate(options):
        """ Validates the application of this backend to a given metadata 
        """
        try:
            if options.backends.index('modelinstance') > options.backends.index('model'):
                raise Exception("Metadata backend 'modelinstance' must come before 'model' backend")
        except ValueError:
            raise Exception("Metadata backend 'modelinstance' must be installed in order to use 'model' backend")



def _resolve(value, model_instance=None, context=None):
    """ Resolves any template references in the given value. 
    """

    if isinstance(value, basestring) and "{" in value:
        if context is None:
            context = Context()
        if model_instance is not None:
            context[model_instance._meta.module_name] = model_instance
        value = Template(value).render(context)
    return value


########NEW FILE########
__FILENAME__ = base
# -*- coding: utf-8 -*-

# TODO:
#    * Move/rename namespace polluting attributes
#    * Documentation
#    * Make backends optional: Meta.backends = (path, modelinstance/model, view)
import hashlib

from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils.datastructures import SortedDict
from django.utils.functional import curry
from django.contrib.sites.models import Site
from django.contrib.contenttypes.models import ContentType
from django.conf import settings
from django.utils.safestring import mark_safe
from django.core.cache import cache
from django.utils.encoding import iri_to_uri

from rollyourown.seo.utils import NotSet, Literal
from rollyourown.seo.options import Options
from rollyourown.seo.fields import MetadataField, Tag, MetaTag, KeywordTag, Raw
from rollyourown.seo.backends import backend_registry, RESERVED_FIELD_NAMES


registry = SortedDict()


class FormattedMetadata(object):
    """ Allows convenient access to selected metadata.
        Metadata for each field may be sourced from any one of the relevant instances passed.
    """

    def __init__(self, metadata, instances, path, site=None, language=None):
        self.__metadata = metadata
        if metadata._meta.use_cache:
            if metadata._meta.use_sites and site:
                hexpath = hashlib.md5(iri_to_uri(site.domain+path)).hexdigest() 
            else:
                hexpath = hashlib.md5(iri_to_uri(path)).hexdigest() 
            if metadata._meta.use_i18n:
                self.__cache_prefix = 'rollyourown.seo.%s.%s.%s' % (self.__metadata.__class__.__name__, hexpath, language)
            else:
                self.__cache_prefix = 'rollyourown.seo.%s.%s' % (self.__metadata.__class__.__name__, hexpath)
        else:
            self.__cache_prefix = None
        self.__instances_original = instances
        self.__instances_cache = []

    def __instances(self):
        """ Cache instances, allowing generators to be used and reused. 
            This fills a cache as the generator gets emptied, eventually
            reading exclusively from the cache.
        """
        for instance in self.__instances_cache:
            yield instance
        for instance in self.__instances_original:
            self.__instances_cache.append(instance)
            yield instance

    def _resolve_value(self, name):
        """ Returns an appropriate value for the given name. 
            This simply asks each of the instances for a value.
        """
        for instance in self.__instances():
            value = instance._resolve_value(name)
            if value:
                return value

        # Otherwise, return an appropriate default value (populate_from)
        # TODO: This is duplicated in meta_models. Move this to a common home.
        if name in self.__metadata._meta.elements:
            populate_from = self.__metadata._meta.elements[name].populate_from
            if callable(populate_from):
                return populate_from(None)
            elif isinstance(populate_from, Literal):
                return populate_from.value
            elif populate_from is not NotSet:
                return self._resolve_value(populate_from)

    def __getattr__(self, name):
        # If caching is enabled, work out a key
        if self.__cache_prefix:
            cache_key = '%s.%s' % (self.__cache_prefix, name)
            value = cache.get(cache_key)
        else:
            cache_key = None
            value = None

        # Look for a group called "name"
        if name in self.__metadata._meta.groups:
            if value is not None:
                return value or None
            value = '\n'.join(unicode(BoundMetadataField(self.__metadata._meta.elements[f], self._resolve_value(f))) for f in self.__metadata._meta.groups[name]).strip()

        # Look for an element called "name"
        elif name in self.__metadata._meta.elements:
            if value is not None:
                return BoundMetadataField(self.__metadata._meta.elements[name], value or None)
            value = self._resolve_value(name)
            if cache_key is not None:
                cache.set(cache_key, value or '')
            return BoundMetadataField(self.__metadata._meta.elements[name], value)
        else:
            raise AttributeError

        if cache_key is not None:
            cache.set(cache_key, value or '')

        return value or None

    def __unicode__(self):
        """ String version of this object is the html output of head elements. """
        if self.__cache_prefix is not None:
            value = cache.get(self.__cache_prefix)
        else:
            value = None

        if value is None:
            value = mark_safe(u'\n'.join(unicode(getattr(self, f)) for f,e in self.__metadata._meta.elements.items() if e.head))
            if self.__cache_prefix is not None:
                cache.set(self.__cache_prefix, value or '')

        return value


class BoundMetadataField(object):
    """ An object to help provide templates with access to a "bound" metadata field. """

    def __init__(self, field, value):
        self.field = field
        if value:
            self.value = field.clean(value)
        else:
            self.value = None

    def __unicode__(self):
        if self.value:
            return mark_safe(self.field.render(self.value))
        else:
            return u""

    def __str__(self):
        return self.__unicode__().encode("ascii", "ignore")


class MetadataBase(type):
    def __new__(cls, name, bases, attrs):
        # TODO: Think of a better test to avoid processing Metadata parent class
        if bases == (object,):
            return type.__new__(cls, name, bases, attrs)

        # Save options as a dict for now (we will be editing them)
        # TODO: Is this necessary, should we bother relaying Django Meta options?
        Meta = attrs.pop('Meta', {})
        if Meta:
            Meta = Meta.__dict__.copy()

        # Remove our options from Meta, so Django won't complain
        help_text = attrs.pop('HelpText', {})

        # TODO: Is this necessary
        if help_text:
            help_text = help_text.__dict__.copy()

        options = Options(Meta, help_text)

        # Collect and sort our elements
        elements = [(key, attrs.pop(key)) for key, obj in attrs.items() 
                                        if isinstance(obj, MetadataField)]
        elements.sort(lambda x, y: cmp(x[1].creation_counter, 
                                                y[1].creation_counter))
        elements = SortedDict(elements)

        # Validation:
        # TODO: Write a test framework for seo.Metadata validation
        # Check that no group names clash with element names
        for key,members in options.groups.items():
            assert key not in elements, "Group name '%s' clashes with field name" % key
            for member in members:
                assert member in elements, "Group member '%s' is not a valid field" % member

        # Check that the names of the elements are not going to clash with a model field
        for key in elements:
            assert key not in RESERVED_FIELD_NAMES, "Field name '%s' is not allowed" % key


        # Preprocessing complete, here is the new class
        new_class = type.__new__(cls, name, bases, attrs)

        options.metadata = new_class
        new_class._meta = options

        # Some useful attributes
        options._update_from_name(name)
        options._register_elements(elements)

        try:
            for backend_name in options.backends:
                new_class._meta._add_backend(backend_registry[backend_name])
            for backend_name in options.backends:
                backend_registry[backend_name].validate(options)
        except KeyError:
            raise Exception('Metadata backend "%s" is not installed.' % backend_name)

        #new_class._meta._add_backend(PathBackend)
        #new_class._meta._add_backend(ModelInstanceBackend)
        #new_class._meta._add_backend(ModelBackend)
        #new_class._meta._add_backend(ViewBackend)

        registry[name] = new_class

        return new_class


    # TODO: Move this function out of the way (subclasses will want to define their own attributes)
    def _get_formatted_data(cls, path, context=None, site=None, language=None):
        """ Return an object to conveniently access the appropriate values. """
        return FormattedMetadata(cls(), cls._get_instances(path, context, site, language), path, site, language)


    # TODO: Move this function out of the way (subclasses will want to define their own attributes)
    def _get_instances(cls, path, context=None, site=None, language=None):
        """ A sequence of instances to discover metadata. 
            Each instance from each backend is looked up when possible/necessary.
            This is a generator to eliminate unnecessary queries.
        """
        backend_context = {'view_context': context }

        for model in cls._meta.models.values():
            for instance in model.objects.get_instances(path, site, language, backend_context) or []:
                if hasattr(instance, '_process_context'):
                    instance._process_context(backend_context)
                yield instance


class Metadata(object):
    __metaclass__ = MetadataBase


def _get_metadata_model(name=None):
    # Find registered Metadata object
    if name is not None:
        try:
            return registry[name]
        except KeyError:
            if len(registry) == 1:
                valid_names = u'Try using the name "%s" or simply leaving it out altogether.'% registry.keys()[0]
            else:
                valid_names = u"Valid names are " + u", ".join(u'"%s"' % k for k in registry.keys())
            raise Exception(u"Metadata definition with name \"%s\" does not exist.\n%s" % (name, valid_names))
    else:
        assert len(registry) == 1, "You must have exactly one Metadata class, if using get_metadata() without a 'name' parameter."
        return registry.values()[0]


def get_metadata(path, name=None, context=None, site=None, language=None):
    metadata = _get_metadata_model(name)
    return metadata._get_formatted_data(path, context, site, language)


def get_linked_metadata(obj, name=None, context=None, site=None, language=None):
    """ Gets metadata linked from the given object. """
    # XXX Check that 'modelinstance' and 'model' metadata are installed in backends
    # I believe that get_model() would return None if not
    Metadata = _get_metadata_model(name)
    InstanceMetadata = Metadata._meta.get_model('modelinstance')
    ModelMetadata = Metadata._meta.get_model('model')
    content_type = ContentType.objects.get_for_model(obj)
    instances = []
    if InstanceMetadata is not None:
        try:
            instance_md = InstanceMetadata.objects.get(_content_type=content_type, _object_id=obj.pk)
        except InstanceMetadata.DoesNotExist:
            instance_md = InstanceMetadata(_content_object=obj)
        instances.append(instance_md)
    if ModelMetadata is not None:
        try:
            model_md = ModelMetadata.objects.get(_content_type=content_type)
        except ModelMetadata.DoesNotExist:
            model_md = ModelMetadata(_content_type=content_type)
        instances.append(model_md)    
    return FormattedMetadata(Metadata, instances, '', site, language)


def create_metadata_instance(metadata_class, instance):
    # If this instance is marked as handled, don't do anything
    # This typically means that the django admin will add metadata 
    # using eg an inline.
    if getattr(instance, '_MetadataFormset__seo_metadata_handled', False):
        return

    metadata = None
    content_type = ContentType.objects.get_for_model(instance)
    
    # If this object does not define a path, don't worry about automatic update
    try:
        path = instance.get_absolute_url()
    except AttributeError:
        return

    # Look for an existing object with this path
    language = getattr(instance, '_language', None)
    site = getattr(instance, '_site', None)
    for md in metadata_class.objects.get_instances(path, site, language):
        # If another object has the same path, remove the path.
        # It's harsh, but we need a unique path and will assume the other
        # link is outdated.
        if md._content_type != content_type or md._object_id != instance.pk:
            md._path = md._content_object.get_absolute_url()
            md.save()
            # Move on, this metadata instance isn't for us
            md = None
        else:
            # This is our instance!
            metadata = md
    
    # If the path-based search didn't work, look for (or create) an existing
    # instance linked to this object.
    if not metadata:
        metadata, md_created = metadata_class.objects.get_or_create(_content_type=content_type, _object_id=instance.pk)
        metadata._path = path
        metadata.save()


def populate_metadata(model, MetadataClass):
    """ For a given model and metadata class, ensure there is metadata for every instance. 
    """
    content_type = ContentType.objects.get_for_model(model)
    for instance in model.objects.all():
        create_metadata_instance(MetadataClass, instance)


def _update_callback(model_class, sender, instance, created, **kwargs):
    """ Callback to be attached to a post_save signal, updating the relevant
        metadata, or just creating an entry. 
    
        NB:
        It is theoretically possible that this code will lead to two instances
        with the same generic foreign key.  If you have non-overlapping URLs,
        then this shouldn't happen.
        I've held it to be more important to avoid double path entries.
    """
    create_metadata_instance(model_class, instance)


def _delete_callback(model_class, sender, instance,  **kwargs):
    content_type = ContentType.objects.get_for_model(instance)
    model_class.objects.filter(_content_type=content_type, _object_id=instance.pk).delete()


def register_signals():
    for metadata_class in registry.values():
        model_instance = metadata_class._meta.get_model('modelinstance')
        if model_instance is not None:
            update_callback = curry(_update_callback, model_class=model_instance)
            delete_callback = curry(_delete_callback, model_class=model_instance)

            ## Connect the models listed in settings to the update callback.
            for model in metadata_class._meta.seo_models:
                models.signals.post_save.connect(update_callback, sender=model, weak=False)
                models.signals.pre_delete.connect(delete_callback, sender=model, weak=False)



########NEW FILE########
__FILENAME__ = default
#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from rollyourown import seo
from django.conf import settings

class DefaultMetadata(seo.Metadata):
    """ A very basic default class for those who do not wish to write their own.
    """
    title       = seo.Tag(head=True, max_length=68)
    keywords    = seo.MetaTag()
    description = seo.MetaTag(max_length=155)
    heading     = seo.Tag(name="h1")

    class Meta:
        verbose_name = "Metadata"
        verbose_name_plural = "Metadata"
        use_sites = False
        # This default class is automatically created when SEO_MODELS is 
        # defined, so we'll take our model list from there.
        seo_models = getattr(settings, 'SEO_MODELS', [])

    class HelpText:
        title       = "This is the page title, that appears in the title bar."
        keywords    = "Comma-separated keywords for search engines."
        description = "A short description, displayed in search results."
        heading     = "This is the page heading, appearing in the &lt;h1&gt; tag."


########NEW FILE########
__FILENAME__ = fields
#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import re

from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils.html import conditional_escape

from rollyourown.seo.utils import escape_tags, NotSet, Literal


VALID_HEAD_TAGS = "head title base link meta script".split()
VALID_INLINE_TAGS = (
    "area img object map param "
    "a abbr acronym dfn em strong "
    "code samp kbd var "
    "b i big small tt " # would like to leave these out :-)
    "span br bdo cite del ins q sub sup"
    # NB: deliberately leaving out iframe and script
).split()


class MetadataField(object):
    creation_counter = 0

    def __init__(self, name, head, editable, populate_from, valid_tags, choices, help_text, verbose_name, field, field_kwargs):
        self.name = name
        self.head = head
        self.editable = editable
        self.populate_from = populate_from
        self.help_text = help_text
        self.field = field or models.CharField
        self.verbose_name = verbose_name
        if field_kwargs is None: field_kwargs = {}
        self.field_kwargs = field_kwargs

        if choices and isinstance(choices[0], basestring):
            choices = [(c, c) for c in choices]
        field_kwargs.setdefault('choices', choices)

        # If valid_tags is a string, tags are space separated words
        if isinstance(valid_tags, basestring):
            valid_tags = valid_tags.split()
        if valid_tags is not None:
            valid_tags = set(valid_tags)
        self.valid_tags = valid_tags


        # Track creation order for field ordering
        self.creation_counter = MetadataField.creation_counter
        MetadataField.creation_counter += 1

    def contribute_to_class(self, cls, name):
        if not self.name:
            self.name = name
        # Populate the hep text from populate_from if it's missing
        if not self.help_text and self.populate_from is not NotSet:
            if callable(self.populate_from) and hasattr(self.populate_from, 'short_description'):
                self.help_text = _('If empty, %s') % self.populate_from.short_description
            elif isinstance(self.populate_from, Literal):
                self.help_text = _('If empty, \"%s\" will be used.') % self.populate_from.value
            elif isinstance(self.populate_from, basestring) and self.populate_from in cls._meta.elements:
                field = cls._meta.elements[self.populate_from]
                self.help_text = _('If empty, %s will be used.') % field.verbose_name or field.name  
            elif isinstance(self.populate_from, basestring) and hasattr(cls, self.populate_from): 
                populate_from = getattr(cls, self.populate_from, None)
                if callable(populate_from) and hasattr(populate_from, 'short_description'):
                    self.help_text = _('If empty, %s') % populate_from.short_description
        self.validate()

    def validate(self):
        """ Discover certain illegal configurations """
        if not self.editable:
            assert self.populate_from is not NotSet, u"If field (%s) is not editable, you must set populate_from" % self.name

    def get_field(self):
        kwargs = self.field_kwargs
        if self.help_text:
            kwargs.setdefault('help_text', self.help_text)
        if self.verbose_name:
            kwargs.setdefault('verbose_name', self.help_text)
        return self.field(**kwargs)

    def clean(self, value):
        return value

    def render(self, value):
        raise NotImplementedError


class Tag(MetadataField):
    def __init__(self, name=None, head=False, escape_value=True,
                       editable=True, verbose_name=None, valid_tags=None, max_length=511,
                       choices=None, populate_from=NotSet, field=models.CharField, 
                       field_kwargs=None, help_text=None):

        self.escape_value = escape_value
        if field_kwargs is None: 
            field_kwargs = {}
        field_kwargs.setdefault('max_length', max_length)
        field_kwargs.setdefault('default', "")
        field_kwargs.setdefault('blank', True)
        super(Tag, self).__init__(name, head, editable, populate_from, valid_tags, choices, help_text, verbose_name, field, field_kwargs)

    def clean(self, value):
        value = escape_tags(value, self.valid_tags or VALID_INLINE_TAGS)

        return value.strip()

    def render(self, value):
        return u'<%s>%s</%s>' % (self.name, value, self.name)


VALID_META_NAME = re.compile(r"[A-z][A-z0-9_:.-]*$")

class MetaTag(MetadataField):
    def __init__(self, name=None, head=True, verbose_name=None, editable=True, 
                       populate_from=NotSet, valid_tags=None, max_length=511, choices=None, 
                       field=models.CharField, field_kwargs=None, help_text=None):
        if field_kwargs is None: 
            field_kwargs = {}
        field_kwargs.setdefault('max_length', max_length)
        field_kwargs.setdefault('default', "")
        field_kwargs.setdefault('blank', True)

        if name is not None:
            assert VALID_META_NAME.match(name) is not None, u"Invalid name for MetaTag: '%s'" % name

        super(MetaTag, self).__init__(name, head, editable, populate_from, valid_tags, choices, help_text, verbose_name, field, field_kwargs)

    def clean(self, value):
        value = escape_tags(value, self.valid_tags)

        # Replace newlines with spaces
        return value.replace("\n", " ").strip()

    def render(self, value):
        # TODO: HTML/XHTML?
        return u'<meta name="%s" content="%s" />' % (self.name, value)

class KeywordTag(MetaTag):
    def __init__(self, name=None, head=True, verbose_name=None, editable=True, 
                       populate_from=NotSet, valid_tags=None, max_length=511, choices=None,
                       field=models.CharField, field_kwargs=None, help_text=None):
        if name is None:
            name = "keywords"
        if valid_tags is None:
            valid_tags = []
        super(KeywordTag, self).__init__(name, head, verbose_name, editable, 
                        populate_from, valid_tags, max_length, choices, field, 
                        field_kwargs, help_text)

    def clean(self, value):
        value = escape_tags(value, self.valid_tags)

        # Remove double quote, replace newlines with commas
        return value.replace('"', '&#34;').replace("\n", ", ").strip()


# TODO: if max_length is given, use a CharField and pass it through
class Raw(MetadataField):
    def __init__(self, head=True, editable=True, populate_from=NotSet, 
                    verbose_name=None, valid_tags=None, choices=None, field=models.TextField,
                    field_kwargs=None, help_text=None):
        if field_kwargs is None: 
            field_kwargs = {}
        field_kwargs.setdefault('default', "")
        field_kwargs.setdefault('blank', True)
        super(Raw, self).__init__(None, head, editable, populate_from, valid_tags, choices, help_text, verbose_name, field, field_kwargs)

    def clean(self, value):
        # Find a suitable set of valid tags using self.head and self.valid_tags
        if self.head:
            valid_tags = set(VALID_HEAD_TAGS)
            if self.valid_tags is not None:
                valid_tags = valid_tags & self.valid_tags
        else:
            valid_tags = self.valid_tags

        value = escape_tags(value, valid_tags)

        if self.head:
            # Remove text before tags
            before_tags = re.compile("^([^<>]*)<")
            value = before_tags.sub('<', value)

            # Remove text after tags
            after_tags = re.compile(">([^<>]*)$")
            value = after_tags.sub('>', value)

        return value

    def render(self, value):
        return value



########NEW FILE########
__FILENAME__ = populate_metadata
#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from django.core.management.base import BaseCommand, CommandError
from rollyourown.seo.management import populate_all_metadata

class Command(BaseCommand):
    help = "Populate the database with metadata instances for all models listed in seo_models."

    def handle(self, *args, **options):
        if len(args) > 0:
            raise CommandError("This command currently takes no arguments")

        populate_all_metadata()


########NEW FILE########
__FILENAME__ = models
#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from django.conf import settings

# Look for Metadata subclasses in appname/seo.py files
for app in settings.INSTALLED_APPS:
    try:
        module_name = '%s.seo' % str(app)
        __import__(module_name)
    except ImportError:
        pass

# if SEO_MODELS is defined, create a default Metadata class
if hasattr(settings, 'SEO_MODELS'):
    __import__('rollyourown.seo.default')

from rollyourown.seo.base import register_signals
register_signals()

########NEW FILE########
__FILENAME__ = options
#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from django.db.models.options import get_verbose_name
from django.db import models
from django.utils.datastructures import SortedDict

class Options(object):
    def __init__(self, meta, help_text=None):
        self.use_sites = meta.pop('use_sites', False)
        self.use_i18n = meta.pop('use_i18n', False)
        self.use_redirect = meta.pop('use_redirect', False)
        self.use_cache = meta.pop('use_cache', False)
        self.groups = meta.pop('groups', {})
        self.seo_views = meta.pop('seo_views', [])
        self.verbose_name = meta.pop('verbose_name', None)
        self.verbose_name_plural = meta.pop('verbose_name_plural', None)
        self.backends = list(meta.pop('backends', ('path', 'modelinstance', 'model', 'view')))
        self._set_seo_models(meta.pop('seo_models', []))
        self.bulk_help_text = help_text
        self.original_meta = meta
        self.models = SortedDict()
        self.name = None
        self.elements = None
        self.metadata = None

    def get_model(self, name):
        try:
            return self.models[name]
        except KeyError:
            return None

    def _update_from_name(self, name):
        self.name = name
        self.verbose_name = self.verbose_name or get_verbose_name(name)
        self.verbose_name_plural = self.verbose_name_plural or self.verbose_name + 's'

    def _register_elements(self, elements):
        """ Takes elements from the metadata class and creates a base model for all backend models .
        """
        self.elements = elements

        for key, obj in elements.items():
            obj.contribute_to_class(self.metadata, key)

        # Create the common Django fields
        fields = {}
        for key, obj in elements.items():
            if obj.editable:
                field = obj.get_field()
                if not field.help_text:
                    if key in self.bulk_help_text:
                        field.help_text = self.bulk_help_text[key]
                fields[key] = field

        # 0. Abstract base model with common fields
        base_meta = type('Meta', (), self.original_meta)
        class BaseMeta(base_meta):
            abstract = True
            app_label = 'seo'
        fields['Meta'] = BaseMeta
        # Do we need this?
        fields['__module__'] = __name__ #attrs['__module__']
        self.MetadataBaseModel = type('%sBase' % self.name, (models.Model,), fields)

    def _add_backend(self, backend):
        """ Builds a subclass model for the given backend """
        md_type = backend.verbose_name
        base = backend().get_model(self)
        # TODO: Rename this field
        new_md_attrs = {'_metadata': self.metadata, '__module__': __name__ }

        new_md_meta = {}
        new_md_meta['verbose_name'] = '%s (%s)' % (self.verbose_name, md_type)
        new_md_meta['verbose_name_plural'] = '%s (%s)' % (self.verbose_name_plural, md_type)
        new_md_meta['unique_together'] = base._meta.unique_together
        new_md_attrs['Meta'] = type("Meta", (), new_md_meta)
        new_md_attrs['_metadata_type'] = backend.name
        model = type("%s%s"%(self.name,"".join(md_type.split())), (base, self.MetadataBaseModel), new_md_attrs.copy())
        self.models[backend.name] = model
        # This is a little dangerous, but because we set __module__ to __name__, the model needs tobe accessible here
        globals()[model.__name__] = model

    def _set_seo_models(self, value):
        """ Gets the actual models to be used. """
        seo_models = []
        for model_name in value:
            if "." in model_name:
                app_label, model_name = model_name.split(".", 1)
                model = models.get_model(app_label, model_name)
                if model:
                    seo_models.append(model)
            else:
                app = models.get_app(model_name)
                if app:
                    seo_models.extend(models.get_models(app))
    
        self.seo_models = seo_models



########NEW FILE########
__FILENAME__ = systemviews
#!/usr/bin/env python
# -*- coding: UTF-8 -*-

def get_seo_views(metadata_class):
    return get_view_names(metadata_class._meta.seo_views)

    ## The following is a previous attempt to dynamically get all urls
    ## This has a number of difficult spots, and is unnecessary when 
    ## seo_views is given
    #choices = SystemViews()
    #seo_views = get_view_names(metadata_class._meta.seo_views)
    #if seo_views:
    #    return filter(lambda c: c[0] in seo_views, choices)
    #else:
    #    return choices

from django.db.models.loading import get_app

def get_view_names(seo_views):
    output = []
    for name in seo_views:
        try:
            app = get_app(name)
        except:
            output.append(name)
        else:
            app_name = app.__name__.split(".")[:-1]
            app_name.append("urls")
            try:
                urls = __import__(".".join(app_name)).urls
            except (ImportError, AttributeError):
                output.append(name)
            else:
                for url in urls.urlpatterns:
                    if url.name:
                        output.append(url.name)
    return output

from rollyourown.seo.utils import LazyChoices
from django.utils.functional import lazy

class SystemViews(LazyChoices):
    def populate(self):
        """ Populate this list with all views that take no arguments.
        """
        from django.conf import settings
        from django.core import urlresolvers

        self.append(("", ""))
        urlconf = settings.ROOT_URLCONF
        resolver = urlresolvers.RegexURLResolver(r'^/', urlconf)
        # Collect base level views
        for key, value in resolver.reverse_dict.items():
            if isinstance(key, basestring):
                args = value[0][0][1]
                url = "/" + value[0][0][0]
                self.append((key, " ".join(key.split("_"))))
        # Collect namespaces (TODO: merge these two sections into one)
        for namespace, url in resolver.namespace_dict.items():
            for key, value in url[1].reverse_dict.items():
                if isinstance(key, basestring):
                    args = value[0][0][1]
                    full_key = '%s:%s' % (namespace, key)
                    self.append((full_key, "%s: %s" % (namespace, " ".join(key.split("_")))))
        self.sort()


from django import forms
class SystemViewChoiceField(forms.TypedChoiceField):
    def _get_choices(self):
        return self._choices
    def _set_choices(self, value):
        self._choices =  self.widget.choices = value
    choices = property(_get_choices, _set_choices)


from django.db.models.fields import BLANK_CHOICE_DASH
from django.db import models
from django.utils.text import capfirst
class SystemViewField(models.CharField):
    def __init__(self, restrict_to, *args, **kwargs):
        self.restrict_to = restrict_to
        kwargs.setdefault('max_length', 255)
        kwargs.setdefault('choices', SystemViews())
        super(SystemViewField, self).__init__(*args, **kwargs)

    def get_choices(self, include_blank=True, blank_choice=BLANK_CHOICE_DASH):
        return self.choices

    def formfield(self, **kwargs):
        defaults = {'required': not self.blank, 'label': capfirst(self.verbose_name), 'help_text': self.help_text}
        if self.has_default():
            if callable(self.default):
                defaults['initial'] = self.default
                defaults['show_hidden_initial'] = True
            else:
                defaults['initial'] = self.get_default()
        include_blank = self.blank or not (self.has_default() or 'initial' in kwargs)
        defaults['choices'] = self.get_choices(include_blank=include_blank)
        defaults['coerce'] = self.to_python
        if self.null:
            defaults['empty_value'] = None
        form_class = SystemViewChoiceField
        # Many of the subclass-specific formfield arguments (min_value,
        # max_value) don't apply for choice fields, so be sure to only pass
        # the values that TypedChoiceField will understand.
        for k in kwargs.keys():
            if k not in ('coerce', 'empty_value', 'choices', 'required',
                         'widget', 'label', 'initial', 'help_text',
                         'error_messages', 'show_hidden_initial'):
                del kwargs[k]
        defaults.update(kwargs)
        return form_class(**defaults)


# help south understand our models
try:
    from south.modelsinspector import add_introspection_rules
except ImportError:
    pass
else:
    add_introspection_rules([], ["^seo\.fields"])

########NEW FILE########
__FILENAME__ = seo
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from django import template
from rollyourown.seo import get_metadata, get_linked_metadata
from django.template import VariableDoesNotExist

register = template.Library()

class MetadataNode(template.Node):
    def __init__(self, metadata_name, variable_name, target, site, language):
        self.metadata_name = metadata_name
        self.variable_name = variable_name
        self.target = template.Variable(target or 'request.path')
        self.site = site and template.Variable(site) or None
        self.language = language and template.Variable(language) or None

    def render(self, context):
        try:
            target = self.target.resolve(context)
        except VariableDoesNotExist:
            msg = (u"{% get_metadata %} needs some path information.\n"
                        u"Please use RequestContext with the django.core.context_processors.request context processor.\n"
                        "Or provide a path or object explicitly, eg {% get_metadata for path %} or {% get_metadata for object %}")
            raise template.TemplateSyntaxError(msg)
        else:
            if callable(target):
                target = target()
            if isinstance(target, basestring):
                path = target
            elif hasattr(target, 'get_absolute_url'):
                path = target.get_absolute_url()
            elif hasattr(target, "__iter__") and 'get_absolute_url' in target:
                path = target['get_absolute_url']()
            else:
                path = None

        kwargs = {}

        # If a site is given, pass that on
        if self.site:
            kwargs['site'] = self.site.resolve(context)

        # If a language is given, pass that on
        if self.language:
            kwargs['language'] = self.language.resolve(context)

        metadata = None
        # If the target is a django model object
        if hasattr(target, 'pk'):
            metadata = get_linked_metadata(target, self.metadata_name, context, **kwargs)
        if not isinstance(path, basestring):
            path = None
        if not metadata:
            # Fetch the metadata
            try:
                metadata = get_metadata(path, self.metadata_name, context, **kwargs)
            except Exception, e:
                raise template.TemplateSyntaxError(e)

        # If a variable name is given, store the result there
        if self.variable_name is not None:
            context[self.variable_name] = metadata
            return ""
        else:
            return unicode(metadata)


def do_get_metadata(parser, token):
    """
    Retrieve an object which can produce (and format) metadata.

        {% get_metadata [for my_path] [in my_language] [on my_site] [as my_variable] %}

        or if you have multiple metadata classes:

        {% get_metadata MyClass [for my_path] [in my_language] [on my_site] [as my_variable] %}

    """
    bits = list(token.split_contents())
    tag_name = bits[0]
    bits = bits[1:]
    metadata_name = None
    args = { 'as': None, 'for': None, 'in': None, 'on': None }

    # If there are an even number of bits, 
    # a metadata name has been provided.
    if len(bits) % 2:
        metadata_name = bits[0]
        bits = bits[1:]

    # Each bits are in the form "key value key value ..."
    # Valid keys are given in the 'args' dict above.
    while len(bits):
        if len(bits) < 2 or bits[0] not in args:
            raise template.TemplateSyntaxError("expected format is '%r [as <variable_name>]'" % tag_name)
        key, value, bits = bits[0], bits[1], bits[2:]
        args[key] = value

    return MetadataNode(metadata_name, 
                variable_name = args['as'], 
                target = args['for'], 
                site = args['on'], 
                language = args['in'])


register.tag('get_metadata', do_get_metadata)


########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-

import logging
import re

from django.conf import settings
from django.db import models
from django.utils.functional import lazy
from django.utils.safestring import mark_safe
from django.utils.html import conditional_escape
from django.contrib.contenttypes.models import ContentType

class NotSet(object):
    " A singleton to identify unset values (where None would have meaning) "
    def __str__(self): return "NotSet"
    def __repr__(self): return self.__str__()
NotSet = NotSet()


class Literal(object):
    " Wrap literal values so that the system knows to treat them that way "
    def __init__(self, value):
        self.value = value


class LazyList(list):
    """ Generic python list which is populated when items are first accessed.
    """

    def populate(self):
        """ Populates the list.
            This method must be overridden by subclasses.
            It is called once, when items in the list are first accessed.
        """
        raise NotImplementedError

    # Ensure list is only populated once
    def __init__(self, populate_function=None):
        if populate_function is not None:
            # TODO: Test this functionality!
            self.populate = populate_function
        self._populated = False
    def _populate(self):
        """ Populate this list by calling populate(), but only once. """
        if not self._populated:
            logging.debug("Populating lazy list %d (%s)" % (id(self), self.__class__.__name__))
            try:
                self.populate()
                self._populated = True
            except Exception, e:
                logging.debug("Currently unable to populate lazy list: %s" % e)

    # Accessing methods that require a populated field
    def __len__(self):
        self._populate()
        return super(LazyList, self).__len__()
    def __getitem__(self, key):
        self._populate()
        return super(LazyList, self).__getitem__(key)
    def __setitem__(self, key, value):
        self._populate()
        return super(LazyList, self).__setitem__(key, value)
    def __delitem__(self, key):
        self._populate()
        return super(LazyList, self).__delitem__(key)
    def __iter__(self):
        self._populate()
        return super(LazyList, self).__iter__()
    def __contains__(self, item):
        self._populate()
        return super(LazyList, self).__contains__(item)


class LazyChoices(LazyList):
    """ Allows a choices list to be given to Django model fields which is
        populated after the models have been defined (ie on validation).
    """

    def __nonzero__(self):
        # Django tests for existence too early, meaning population is attempted
        # before the models have been imported. 
        # This may have some side effects if truth testing is supposed to
        # evaluate the list, but in the case of django choices, this is not
        # The case. This prevents __len__ from being called on truth tests.
        if not self._populated:
            return True
        else:
            return bool(len(self))


from django.core.urlresolvers import RegexURLResolver, RegexURLPattern, Resolver404, get_resolver

def _pattern_resolve_to_name(pattern, path):
    match = pattern.regex.search(path)
    if match:
        name = ""
        if pattern.name:
            name = pattern.name
        elif hasattr(pattern, '_callback_str'):
            name = pattern._callback_str
        else:
            name = "%s.%s" % (pattern.callback.__module__, pattern.callback.func_name)
        return name

def _resolver_resolve_to_name(resolver, path):
    tried = []
    match = resolver.regex.search(path)
    if match:
        new_path = path[match.end():]
        for pattern in resolver.url_patterns:
            try:
                if isinstance(pattern, RegexURLPattern):
                    name = _pattern_resolve_to_name(pattern, new_path)
                elif isinstance(pattern, RegexURLResolver):
                    name = _resolver_resolve_to_name(pattern, new_path)
            except Resolver404, e:
                tried.extend([(pattern.regex.pattern + '   ' + t) for t in e.args[0]['tried']])
            else:
                if name:
                    return name
                tried.append(pattern.regex.pattern)
        raise Resolver404, {'tried': tried, 'path': new_path}


def resolve_to_name(path, urlconf=None):
    try:
        return _resolver_resolve_to_name(get_resolver(urlconf), path)
    except Resolver404:
        return None


def _replace_quot(match):
    unescape = lambda v: v.replace('&quot;', '"').replace('&amp;', '&')
    return u'<%s%s>' % (unescape(match.group(1)), unescape(match.group(3)))


def escape_tags(value, valid_tags):
    """ Strips text from the given html string, leaving only tags.
        This functionality requires BeautifulSoup, nothing will be 
        done otherwise.

        This isn't perfect. Someone could put javascript in here:
              <a onClick="alert('hi');">test</a>

            So if you use valid_tags, you still need to trust your data entry.
            Or we could try:
              - only escape the non matching bits
              - use BeautifulSoup to understand the elements, escape everything else and remove potentially harmful attributes (onClick).
              - Remove this feature entirely. Half-escaping things securely is very difficult, developers should not be lured into a false sense of security.
    """
    # 1. escape everything
    value = conditional_escape(value)

    # 2. Reenable certain tags
    if valid_tags:
        # TODO: precompile somewhere once?
        tag_re = re.compile(r'&lt;(\s*/?\s*(%s))(.*?\s*)&gt;' % u'|'.join(re.escape(tag) for tag in valid_tags))
        value = tag_re.sub(_replace_quot, value)

    # Allow comments to be hidden
    value = value.replace("&lt;!--", "<!--").replace("--&gt;", "-->")
    
    return mark_safe(value)


def _get_seo_content_types(seo_models):
    """ Returns a list of content types from the models defined in settings (SEO_MODELS) """
    try:
        return [ ContentType.objects.get_for_model(m).id for m in seo_models ]
    except: # previously caught DatabaseError
        # Return an empty list if this is called too early
        return []
def get_seo_content_types(seo_models):
    return lazy(_get_seo_content_types, list)(seo_models)

########NEW FILE########
