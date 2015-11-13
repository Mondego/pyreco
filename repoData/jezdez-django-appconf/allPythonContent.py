__FILENAME__ = base
from django.core.exceptions import ImproperlyConfigured
import sys
import six
from .utils import import_attribute


class AppConfOptions(object):

    def __init__(self, meta, prefix=None):
        self.prefix = prefix
        self.holder_path = getattr(meta, 'holder', 'django.conf.settings')
        self.holder = import_attribute(self.holder_path)
        self.proxy = getattr(meta, 'proxy', False)
        self.required = getattr(meta, 'required', [])
        self.configured_data = {}

    def prefixed_name(self, name):
        if name.startswith(self.prefix.upper()):
            return name
        return "%s_%s" % (self.prefix.upper(), name.upper())

    def contribute_to_class(self, cls, name):
        cls._meta = self
        self.names = {}
        self.defaults = {}


class AppConfMetaClass(type):

    def __new__(cls, name, bases, attrs):
        super_new = super(AppConfMetaClass, cls).__new__
        parents = [b for b in bases if isinstance(b, AppConfMetaClass)]
        if not parents:
            return super_new(cls, name, bases, attrs)

        # Create the class.
        module = attrs.pop('__module__')
        new_class = super_new(cls, name, bases, {'__module__': module})
        attr_meta = attrs.pop('Meta', None)
        if attr_meta:
            meta = attr_meta
        else:
            attr_meta = type('Meta', (object,), {})
            meta = getattr(new_class, 'Meta', None)

        prefix = getattr(meta, 'prefix', getattr(meta, 'app_label', None))
        if prefix is None:
            # Figure out the prefix by looking one level up.
            # For 'django.contrib.sites.models', this would be 'sites'.
            model_module = sys.modules[new_class.__module__]
            prefix = model_module.__name__.split('.')[-2]

        new_class.add_to_class('_meta', AppConfOptions(meta, prefix))
        new_class.add_to_class('Meta', attr_meta)

        for parent in parents[::-1]:
            if hasattr(parent, '_meta'):
                new_class._meta.names.update(parent._meta.names)
                new_class._meta.defaults.update(parent._meta.defaults)
                new_class._meta.configured_data.update(
                    parent._meta.configured_data)

        for name in filter(str.isupper, list(attrs.keys())):
            prefixed_name = new_class._meta.prefixed_name(name)
            new_class._meta.names[name] = prefixed_name
            new_class._meta.defaults[prefixed_name] = attrs.pop(name)

        # Add all attributes to the class.
        for name, value in attrs.items():
            new_class.add_to_class(name, value)

        new_class._configure()
        for name, value in six.iteritems(new_class._meta.configured_data):
            prefixed_name = new_class._meta.prefixed_name(name)
            setattr(new_class._meta.holder, prefixed_name, value)
            new_class.add_to_class(name, value)

        # Confirm presence of required settings.
        for name in new_class._meta.required:
            prefixed_name = new_class._meta.prefixed_name(name)
            if not hasattr(new_class._meta.holder, prefixed_name):
                raise ImproperlyConfigured('The required setting %s is'
                                           ' missing.' % prefixed_name)

        return new_class

    def add_to_class(cls, name, value):
        if hasattr(value, 'contribute_to_class'):
            value.contribute_to_class(cls, name)
        else:
            setattr(cls, name, value)

    def _configure(cls):
        # the ad-hoc settings class instance used to configure each value
        obj = cls()
        for name, prefixed_name in six.iteritems(obj._meta.names):
            default_value = obj._meta.defaults.get(prefixed_name)
            value = getattr(obj._meta.holder, prefixed_name, default_value)
            callback = getattr(obj, "configure_%s" % name.lower(), None)
            if callable(callback):
                value = callback(value)
            cls._meta.configured_data[name] = value
        cls._meta.configured_data = obj.configure()


class AppConf(six.with_metaclass(AppConfMetaClass)):
    """
    An app setting object to be used for handling app setting defaults
    gracefully and providing a nice API for them.
    """

    def __init__(self, **kwargs):
        for name, value in six.iteritems(kwargs):
            setattr(self, name, value)

    def __dir__(self):
        return sorted(list(set(self._meta.names.keys())))

    # For instance access..
    @property
    def configured_data(self):
        return self._meta.configured_data

    # For Python < 2.6:
    @property
    def __members__(self):
        return self.__dir__()

    def __getattr__(self, name):
        if self._meta.proxy:
            return getattr(self._meta.holder, name)
        raise AttributeError("%s not found. Use '%s' instead." %
                             (name, self._meta.holder_path))

    def __setattr__(self, name, value):
        if name == name.upper():
            setattr(self._meta.holder,
                    self._meta.prefixed_name(name), value)
        object.__setattr__(self, name, value)

    def configure(self):
        """
        Hook for doing any extra configuration, returning a dictionary
        containing the configured data.

        """
        return self.configured_data

########NEW FILE########
__FILENAME__ = models
from appconf import AppConf


class CustomHolder(object):
    HOLDER_VALUE = True

custom_holder = CustomHolder()


class TestConf(AppConf):

    SIMPLE_VALUE = True

    CONFIGURED_VALUE = 'wrong'

    def configure_configured_value(self, value):
        return 'correct'

    def configure(self):
        self.configured_data['CONFIGURE_METHOD_VALUE'] = True
        return self.configured_data


class PrefixConf(TestConf):

    class Meta:
        prefix = 'prefix'


class YetAnotherPrefixConf(PrefixConf):

    SIMPLE_VALUE = False

    class Meta:
        prefix = 'yetanother_prefix'


class SeparateConf(AppConf):

    SEPARATE_VALUE = True

    class Meta(PrefixConf.Meta):
        pass


class SubclassConf(TestConf):

    def configure(self):
        self.configured_data['CONFIGURE_METHOD_VALUE2'] = False
        return self.configured_data


class ProxyConf(TestConf):

    class Meta:
        proxy = True


class CustomHolderConf(AppConf):

    SIMPLE_VALUE = True

    class Meta:
        # instead of django.conf.settings
        holder = 'appconf.tests.models.custom_holder'
        prefix = 'custom_holder'

########NEW FILE########
__FILENAME__ = settings
SIMPLE_VALUE = True

CONFIGURED_VALUE = 'wrong'

########NEW FILE########
__FILENAME__ = tests
from __future__ import absolute_import
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase

from appconf.tests.models import (AppConf, TestConf, PrefixConf,
                                  YetAnotherPrefixConf, SeparateConf,
                                  ProxyConf, CustomHolderConf, custom_holder)


class TestConfTests(TestCase):

    def test_basic(self):
        self.assertEqual(TestConf._meta.prefix, 'tests')

    def test_simple(self):
        self.assertTrue(hasattr(settings, 'TESTS_SIMPLE_VALUE'))
        self.assertEqual(settings.TESTS_SIMPLE_VALUE, True)

    def test_configured(self):
        self.assertTrue(hasattr(settings, 'TESTS_CONFIGURED_VALUE'))
        self.assertEqual(settings.TESTS_CONFIGURED_VALUE, 'correct')

    def test_configure_method(self):
        self.assertTrue(hasattr(settings, 'TESTS_CONFIGURE_METHOD_VALUE'))
        self.assertEqual(settings.TESTS_CONFIGURE_METHOD_VALUE, True)

    def test_init_kwargs(self):
        custom_conf = TestConf(CUSTOM_VALUE='custom')
        self.assertEqual(custom_conf.CUSTOM_VALUE, 'custom')
        self.assertEqual(settings.TESTS_CUSTOM_VALUE, 'custom')
        self.assertRaises(AttributeError,
                          lambda: custom_conf.TESTS_CUSTOM_VALUE)
        custom_conf.CUSTOM_VALUE_SETATTR = 'custom'
        self.assertEqual(settings.TESTS_CUSTOM_VALUE_SETATTR, 'custom')
        custom_conf.custom_value_lowercase = 'custom'
        self.assertRaises(AttributeError,
                          lambda: settings.custom_value_lowercase)

    def test_init_kwargs_with_prefix(self):
        custom_conf = TestConf(TESTS_CUSTOM_VALUE2='custom2')
        self.assertEqual(custom_conf.TESTS_CUSTOM_VALUE2, 'custom2')
        self.assertEqual(settings.TESTS_CUSTOM_VALUE2, 'custom2')

    def test_proxy(self):
        custom_conf = ProxyConf(CUSTOM_VALUE3='custom3')
        self.assertEqual(custom_conf.CUSTOM_VALUE3, 'custom3')
        self.assertEqual(settings.TESTS_CUSTOM_VALUE3, 'custom3')
        self.assertEqual(custom_conf.TESTS_CUSTOM_VALUE3, 'custom3')
        self.assertTrue('appconf.tests' in custom_conf.INSTALLED_APPS)

    def test_dir_members(self):
        custom_conf = TestConf()
        self.assertTrue('TESTS_SIMPLE_VALUE' in dir(settings))
        if hasattr(settings, '__members__'):  # django 1.5 removed __members__
            self.assertTrue('TESTS_SIMPLE_VALUE' in settings.__members__)
        self.assertTrue('SIMPLE_VALUE' in dir(custom_conf))
        self.assertTrue('SIMPLE_VALUE' in custom_conf.__members__)
        self.assertFalse('TESTS_SIMPLE_VALUE' in dir(custom_conf))
        self.assertFalse('TESTS_SIMPLE_VALUE' in custom_conf.__members__)

    def test_custom_holder(self):
        CustomHolderConf()
        self.assertTrue(hasattr(custom_holder, 'CUSTOM_HOLDER_SIMPLE_VALUE'))
        self.assertEqual(custom_holder.CUSTOM_HOLDER_SIMPLE_VALUE, True)

    def test_subclass_configured_data(self):
        self.assertTrue('TESTS_CONFIGURE_METHOD_VALUE2' in dir(settings))
        self.assertEqual(settings.TESTS_CONFIGURE_METHOD_VALUE2, False)


class PrefixConfTests(TestCase):

    def test_prefix(self):
        self.assertEqual(PrefixConf._meta.prefix, 'prefix')

    def test_simple(self):
        self.assertTrue(hasattr(settings, 'PREFIX_SIMPLE_VALUE'))
        self.assertEqual(settings.PREFIX_SIMPLE_VALUE, True)

    def test_configured(self):
        self.assertTrue(hasattr(settings, 'PREFIX_CONFIGURED_VALUE'))
        self.assertEqual(settings.PREFIX_CONFIGURED_VALUE, 'correct')

    def test_configure_method(self):
        self.assertTrue(hasattr(settings, 'PREFIX_CONFIGURE_METHOD_VALUE'))
        self.assertEqual(settings.PREFIX_CONFIGURE_METHOD_VALUE, True)


class YetAnotherPrefixConfTests(TestCase):

    def test_prefix(self):
        self.assertEqual(YetAnotherPrefixConf._meta.prefix,
                         'yetanother_prefix')

    def test_simple(self):
        self.assertTrue(hasattr(settings,
                                'YETANOTHER_PREFIX_SIMPLE_VALUE'))
        self.assertEqual(settings.YETANOTHER_PREFIX_SIMPLE_VALUE, False)

    def test_configured(self):
        self.assertTrue(hasattr(settings,
                                'YETANOTHER_PREFIX_CONFIGURED_VALUE'))
        self.assertEqual(settings.YETANOTHER_PREFIX_CONFIGURED_VALUE,
                         'correct')

    def test_configure_method(self):
        self.assertTrue(hasattr(settings,
                                'YETANOTHER_PREFIX_CONFIGURE_METHOD_VALUE'))
        self.assertEqual(settings.YETANOTHER_PREFIX_CONFIGURE_METHOD_VALUE,
                         True)


class SeparateConfTests(TestCase):

    def test_prefix(self):
        self.assertEqual(SeparateConf._meta.prefix, 'prefix')

    def test_simple(self):
        self.assertTrue(hasattr(settings, 'PREFIX_SEPARATE_VALUE'))
        self.assertEqual(settings.PREFIX_SEPARATE_VALUE, True)


class RequiredSettingsTests(TestCase):

    def create_invalid_conf(self):
        class RequirementConf(AppConf):
            class Meta:
                required = ['NOT_PRESENT']

    def test_value_is_defined(self):
        class RequirementConf(AppConf):
            class Meta:
                holder = 'appconf.tests.models.custom_holder'
                prefix = 'holder'
                required = ['VALUE']

    def test_default_is_defined(self):
        class RequirementConf(AppConf):
            SIMPLE_VALUE = True

            class Meta:
                required = ['SIMPLE_VALUE']

    def test_missing(self):
        self.assertRaises(ImproperlyConfigured, self.create_invalid_conf)

########NEW FILE########
__FILENAME__ = test_settings
import django

SITE_ID = 1

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.sites',
    'django.contrib.auth',
    'django.contrib.admin',
    'appconf.tests',
]

if django.VERSION[:2] < (1, 6):
    TEST_RUNNER = 'discover_runner.DiscoverRunner'

SECRET_KEY = 'local'

########NEW FILE########
__FILENAME__ = utils
import sys


def import_attribute(import_path, exception_handler=None):
    from django.utils.importlib import import_module
    module_name, object_name = import_path.rsplit('.', 1)
    try:
        module = import_module(module_name)
    except:  # pragma: no cover
        if callable(exception_handler):
            exctype, excvalue, tb = sys.exc_info()
            return exception_handler(import_path, exctype, excvalue, tb)
        else:
            raise
    try:
        return getattr(module, object_name)
    except:  # pragma: no cover
        if callable(exception_handler):
            exctype, excvalue, tb = sys.exc_info()
            return exception_handler(import_path, exctype, excvalue, tb)
        else:
            raise

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# django-appconf documentation build configuration file, created by
# sphinx-quickstart on Thu Aug 25 14:26:22 2011.
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
sys.path.insert(0, os.path.abspath('..'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.intersphinx', 'sphinx.ext.coverage']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'django-appconf'
copyright = u'2011-2013, Jannis Leidel and individual contributors'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
try:
    from appconf import __version__
    # The short X.Y version.
    version = '.'.join(__version__.split('.')[:2])
    # The full version, including alpha/beta/rc tags.
    release = __version__
except ImportError:
    version = release = 'dev'

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
htmlhelp_basename = 'django-appconfdoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'django-appconf.tex', u'django-appconf Documentation',
   u'Jannis Leidel and individual contributors', 'manual'),
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
    ('index', 'django-appconf', u'django-appconf Documentation',
     [u'Jannis Leidel and individual contributors'], 1)
]


# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {
    'python': ('http://python.readthedocs.org/en/v2.7.2/', None),
    'django': ('http://django.readthedocs.org/en/latest/', None),
    'celery': ('http://celery.readthedocs.org/en/latest/', None),
}

########NEW FILE########
