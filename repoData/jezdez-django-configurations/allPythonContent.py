__FILENAME__ = base
import warnings

from django.utils import six
from django.conf import global_settings
from django.core.exceptions import ImproperlyConfigured

from .utils import uppercase_attributes
from .values import Value, setup_value

__all__ = ['Configuration']


install_failure = ("django-configurations settings importer wasn't "
                   "correctly installed. Please use one of the starter "
                   "functions to install it as mentioned in the docs: "
                   "http://django-configurations.readthedocs.org/")


class ConfigurationBase(type):

    def __new__(cls, name, bases, attrs):
        # also check for "Configuration" here to handle the Settings class
        # below remove it when we deprecate the Settings class
        if (bases not in ((object,), ()) and
                bases[0].__name__ not in ('NewBase', 'Configuration')):
            # if this is actually a subclass in a settings module
            # we better check if the importer was correctly installed
            from . import importer
            if not importer.installed:
                raise ImproperlyConfigured(install_failure)
        settings_vars = uppercase_attributes(global_settings)
        parents = [base for base in bases if isinstance(base,
                                                        ConfigurationBase)]
        if parents:
            for base in bases[::-1]:
                settings_vars.update(uppercase_attributes(base))
        attrs = dict(settings_vars, **attrs)
        return super(ConfigurationBase, cls).__new__(cls, name, bases, attrs)

    def __repr__(self):
        return "<Configuration '{0}.{1}'>".format(self.__module__,
                                                  self.__name__)


class Configuration(six.with_metaclass(ConfigurationBase)):
    """
    The base configuration class to inherit from.

    ::

        class Develop(Configuration):
            EXTRA_AWESOME = True

            @property
            def SOMETHING(self):
                return completely.different()

            def OTHER(self):
                if whatever:
                    return (1, 2, 3)
                return (4, 5, 6)

    The module this configuration class is located in will
    automatically get the class and instance level attributes
    with upper characters if the ``DJANGO_CONFIGURATION`` is set
    to the name of the class.

    """
    @classmethod
    def pre_setup(cls):
        pass

    @classmethod
    def post_setup(cls):
        pass

    @classmethod
    def setup(cls):
        for name, value in uppercase_attributes(cls).items():
            if isinstance(value, Value):
                setup_value(cls, name, value)


class Settings(Configuration):

    @classmethod
    def pre_setup(cls):
        # make sure to remove the handling of the Settings class above when deprecating
        warnings.warn("configurations.Settings was renamed to "
                      "settings.Configuration and will be "
                      "removed in 1.0", PendingDeprecationWarning)

########NEW FILE########
__FILENAME__ = decorators
def pristinemethod(func):
    """
    A decorator for handling pristine settings like callables.

    Use it like this::

        from configurations import Configuration, pristinemethod

        class Develop(Configuration):

            @pristinemethod
            def USER_CHECK(user):
                return user.check_perms()

            GROUP_CHECK = pristinemethod(lambda user: user.has_group_access())

    """
    func.pristine = True
    return staticmethod(func)

########NEW FILE########
__FILENAME__ = fastcgi
from . import importer

importer.install()

from django.core.servers.fastcgi import runfastcgi  # noqa

########NEW FILE########
__FILENAME__ = importer
import imp
import logging
import os
import sys
from optparse import make_option

from django.core.exceptions import ImproperlyConfigured
from django.core.management import LaxOptionParser
from django.conf import ENVIRONMENT_VARIABLE as SETTINGS_ENVIRONMENT_VARIABLE

from .utils import uppercase_attributes, reraise
from .values import Value, setup_value

installed = False

CONFIGURATION_ENVIRONMENT_VARIABLE = 'DJANGO_CONFIGURATION'


configuration_options = (
    make_option('--configuration',
                help='The name of the configuration class to load, e.g. '
                     '"Development". If this isn\'t provided, the '
                     'DJANGO_CONFIGURATION environment variable will '
                     'be used.'),)


def install(check_options=False):
    global installed
    if not installed:
        from django.core.management import base

        # add the configuration option to all management commands
        base.BaseCommand.option_list += configuration_options

        importer = ConfigurationImporter(check_options=check_options)
        sys.meta_path.insert(0, importer)
        installed = True


class ConfigurationImporter(object):
    modvar = SETTINGS_ENVIRONMENT_VARIABLE
    namevar = CONFIGURATION_ENVIRONMENT_VARIABLE
    error_msg = ("Configuration cannot be imported, "
                 "environment variable {0} is undefined.")

    def __init__(self, check_options=False):
        self.argv = sys.argv[:]
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler()
        self.logger.addHandler(handler)
        if check_options:
            self.check_options()
        self.validate()
        if check_options:
            self.announce()

    def __repr__(self):
        return "<ConfigurationImporter for '{0}.{1}'>".format(self.module,
                                                              self.name)

    @property
    def module(self):
        return os.environ.get(self.modvar)

    @property
    def name(self):
        return os.environ.get(self.namevar)

    def check_options(self):
        parser = LaxOptionParser(option_list=configuration_options,
                                 add_help_option=False)
        try:
            options, args = parser.parse_args(self.argv)
            if options.configuration:
                os.environ[self.namevar] = options.configuration
        except:
            pass  # Ignore any option errors at this point.

    def validate(self):
        if self.name is None:
            raise ImproperlyConfigured(self.error_msg.format(self.namevar))
        if self.module is None:
            raise ImproperlyConfigured(self.error_msg.format(self.modvar))

    def announce(self):
        if len(self.argv) > 1:
            from . import __version__
            from django.utils.termcolors import colorize
            # Django >= 1.7 supports hiding the colorization in the shell
            try:
                from django.core.management.color import no_style
            except ImportError:
                no_style = None

            if no_style is not None and '--no-color' in self.argv:
                stylize = no_style()
            else:
                stylize = lambda text: colorize(text, fg='green')

            if (self.argv[1] == 'runserver' and
                    os.environ.get('RUN_MAIN') == 'true'):

                message = ("django-configurations version {0}, using "
                           "configuration '{1}'".format(__version__,
                                                        self.name))
                self.logger.debug(stylize(message))

    def find_module(self, fullname, path=None):
        if fullname is not None and fullname == self.module:
            module = fullname.rsplit('.', 1)[-1]
            return ConfigurationLoader(self.name,
                                       imp.find_module(module, path))
        return None


class ConfigurationLoader(object):

    def __init__(self, name, location):
        self.name = name
        self.location = location

    def load_module(self, fullname):
        if fullname in sys.modules:
            mod = sys.modules[fullname]  # pragma: no cover
        else:
            mod = imp.load_module(fullname, *self.location)
        cls_path = '{0}.{1}'.format(mod.__name__, self.name)

        try:
            cls = getattr(mod, self.name)
        except AttributeError as err:  # pragma: no cover
            reraise(err, "Couldn't find configuration '{0}' "
                         "in module '{1}'".format(self.name,
                                                  mod.__package__))
        try:
            cls.pre_setup()
            cls.setup()
            obj = cls()
            attributes = uppercase_attributes(obj).items()
            for name, value in attributes:
                if callable(value) and not getattr(value, 'pristine', False):
                    value = value()
                    # in case a method returns a Value instance we have
                    # to do the same as the Configuration.setup method
                    if isinstance(value, Value):
                        setup_value(mod, name, value)
                        continue
                setattr(mod, name, value)

            setattr(mod, 'CONFIGURATION', '{0}.{1}'.format(fullname,
                                                           self.name))
            cls.post_setup()

        except Exception as err:
            reraise(err, "Couldn't setup configuration '{0}'".format(cls_path))

        return mod

########NEW FILE########
__FILENAME__ = management
from . import importer

importer.install(check_options=True)

from django.core.management import execute_from_command_line  # noqa

########NEW FILE########
__FILENAME__ = utils
import sys

from django.core.exceptions import ImproperlyConfigured
from django.utils import six
from django.utils.importlib import import_module


def isuppercase(name):
    return name == name.upper() and not name.startswith('_')


def uppercase_attributes(obj):
    return dict((name, getattr(obj, name))
                for name in filter(isuppercase, dir(obj)))


def import_by_path(dotted_path, error_prefix=''):
    """
    Import a dotted module path and return the attribute/class designated by
    the last name in the path. Raise ImproperlyConfigured if something goes
    wrong.

    Backported from Django 1.6.
    """
    try:
        module_path, class_name = dotted_path.rsplit('.', 1)
    except ValueError:
        raise ImproperlyConfigured("{0}{1} doesn't look like "
                                   "a module path".format(error_prefix,
                                                          dotted_path))
    try:
        module = import_module(module_path)
    except ImportError as err:
        msg = '{0}Error importing module {1}: "{2}"'.format(error_prefix,
                                                            module_path,
                                                            err)
        six.reraise(ImproperlyConfigured, ImproperlyConfigured(msg),
                    sys.exc_info()[2])
    try:
        attr = getattr(module, class_name)
    except AttributeError:
        raise ImproperlyConfigured('{0}Module "{1}" does not define a '
                                   '"{2}" attribute/class'.format(error_prefix,
                                                                  module_path,
                                                                  class_name))
    return attr


def reraise(exc, prefix=None, suffix=None):
    args = exc.args
    if not args:
        args = ('',)
    if prefix is None:
        prefix = ''
    elif not prefix.endswith((':', ': ')):
        prefix = prefix + ': '
    if suffix is None:
        suffix = ''
    elif not (suffix.startswith('(') and suffix.endswith(')')):
        suffix = '(' + suffix + ')'
    exc.args = ('{0} {1} {2}'.format(prefix, exc.args[0], suffix),) + args[1:]
    raise

########NEW FILE########
__FILENAME__ = values
import ast
import copy
import decimal
import os
import sys

from django.core import validators
from django.core.exceptions import ValidationError, ImproperlyConfigured
from django.utils import six

from .utils import import_by_path


def setup_value(target, name, value):
    actual_value = value.setup(name)
    # overwriting the original Value class with the result
    setattr(target, name, actual_value)
    if value.multiple:
        for multiple_name, multiple_value in actual_value.items():
            setattr(target, multiple_name, multiple_value)


class Value(object):
    """
    A single settings value that is able to interpret env variables
    and implements a simple validation scheme.
    """
    multiple = False

    def __init__(self, default=None, environ=True, environ_name=None,
                 environ_prefix='DJANGO', *args, **kwargs):
        if isinstance(default, Value):
            self.default = copy.copy(default.default)
        else:
            self.default = default
        self.environ = environ
        if environ_prefix and environ_prefix.endswith('_'):
            environ_prefix = environ_prefix[:-1]
        self.environ_prefix = environ_prefix
        self.environ_name = environ_name

    def __repr__(self):
        return "<Value default: {0}>".format(self.default)

    def setup(self, name):
        value = self.default
        if self.environ:
            if self.environ_name is None:
                environ_name = name.upper()
            else:
                environ_name = self.environ_name
            if self.environ_prefix:
                full_environ_name = '{0}_{1}'.format(self.environ_prefix,
                                                     environ_name)
            else:
                full_environ_name = environ_name
            if full_environ_name in os.environ:
                value = self.to_python(os.environ[full_environ_name])
        return value

    def to_python(self, value):
        """
        Convert the given value of a environment variable into an
        appropriate Python representation of the value.
        This should be overriden when subclassing.
        """
        return value


class MultipleMixin(object):
    multiple = True


class BooleanValue(Value):
    true_values = ('yes', 'y', 'true', '1')
    false_values = ('no', 'n', 'false', '0', '')

    def __init__(self, *args, **kwargs):
        super(BooleanValue, self).__init__(*args, **kwargs)
        if self.default not in (True, False):
            raise ValueError('Default value {0!r} is not a '
                             'boolean value'.format(self.default))

    def to_python(self, value):
        normalized_value = value.strip().lower()
        if normalized_value in self.true_values:
            return True
        elif normalized_value in self.false_values:
            return False
        else:
            raise ValueError('Cannot interpret '
                             'boolean value {0!r}'.format(value))


class CastingMixin(object):
    exception = (TypeError, ValueError)
    message = 'Cannot interpret value {0!r}'

    def __init__(self, *args, **kwargs):
        super(CastingMixin, self).__init__(*args, **kwargs)
        if isinstance(self.caster, six.string_types):
            self._caster = import_by_path(self.caster)
        elif callable(self.caster):
            self._caster = self.caster
        else:
            error = 'Cannot use caster of {0} ({1!r})'.format(self,
                                                              self.caster)
            raise ValueError(error)

    def to_python(self, value):
        try:
            return self._caster(value)
        except self.exception:
            raise ValueError(self.message.format(value))


class IntegerValue(CastingMixin, Value):
    caster = int


class FloatValue(CastingMixin, Value):
    caster = float


class DecimalValue(CastingMixin, Value):
    caster = decimal.Decimal
    exception = decimal.InvalidOperation


class ListValue(Value):
    converter = None
    message = 'Cannot interpret list item {0!r} in list {1!r}'

    def __init__(self, *args, **kwargs):
        self.separator = kwargs.pop('separator', ',')
        converter = kwargs.pop('converter', None)
        if converter is not None:
            self.converter = converter
        super(ListValue, self).__init__(*args, **kwargs)
        # make sure the default is a list
        if self.default is None:
            self.default = []
        # initial conversion
        if self.converter is not None:
            self.default = [self.converter(value) for value in self.default]

    def to_python(self, value):
        split_value = [v.strip() for v in value.strip().split(self.separator)]
        # removing empty items
        value_list = filter(None, split_value)
        if self.converter is None:
            return list(value_list)

        converted_values = []
        for list_value in value_list:
            try:
                converted_values.append(self.converter(list_value))
            except (TypeError, ValueError):
                raise ValueError(self.message.format(list_value, value))
        return converted_values


class BackendsValue(ListValue):

    def converter(self, value):
        try:
            import_by_path(value)
        except ImproperlyConfigured as err:
            six.reraise(ValueError, ValueError(err), sys.exc_info()[2])
        return value


class TupleValue(ListValue):
    message = 'Cannot interpret tuple item {0!r} in tuple {1!r}'

    def __init__(self, *args, **kwargs):
        super(TupleValue, self).__init__(*args, **kwargs)
        if self.default is None:
            self.default = ()
        else:
            self.default = tuple(self.default)

    def to_python(self, value):
        return tuple(super(TupleValue, self).to_python(value))


class SetValue(ListValue):
    message = 'Cannot interpret set item {0!r} in set {1!r}'

    def __init__(self, *args, **kwargs):
        super(SetValue, self).__init__(*args, **kwargs)
        if self.default is None:
            self.default = set()
        else:
            self.default = set(self.default)

    def to_python(self, value):
        return set(super(SetValue, self).to_python(value))


class DictValue(Value):
    message = 'Cannot interpret dict value {0!r}'

    def __init__(self, *args, **kwargs):
        super(DictValue, self).__init__(*args, **kwargs)
        if self.default is None:
            self.default = {}
        else:
            self.default = dict(self.default)

    def to_python(self, value):
        value = super(DictValue, self).to_python(value)
        if not value:
            return {}
        try:
            evaled_value = ast.literal_eval(value)
        except ValueError:
            raise ValueError(self.message.format(value))
        if not isinstance(evaled_value, dict):
            raise ValueError(self.message.format(value))
        return evaled_value


class ValidationMixin(object):

    def __init__(self, *args, **kwargs):
        super(ValidationMixin, self).__init__(*args, **kwargs)
        if isinstance(self.validator, six.string_types):
            self._validator = import_by_path(self.validator)
        elif callable(self.validator):
            self._validator = self.validator
        else:
            raise ValueError('Cannot use validator of '
                             '{0} ({1!r})'.format(self, self.validator))
        self.to_python(self.default)

    def to_python(self, value):
        try:
            self._validator(value)
        except ValidationError:
            raise ValueError(self.message.format(value))
        else:
            return value


class EmailValue(ValidationMixin, Value):
    message = 'Cannot interpret email value {0!r}'
    validator = 'django.core.validators.validate_email'


class URLValue(ValidationMixin, Value):
    message = 'Cannot interpret URL value {0!r}'
    validator = validators.URLValidator()


class IPValue(ValidationMixin, Value):
    message = 'Cannot interpret IP value {0!r}'
    validator = 'django.core.validators.validate_ipv46_address'


class RegexValue(ValidationMixin, Value):
    message = "Regex doesn't match value {0!r}"

    def __init__(self, *args, **kwargs):
        regex = kwargs.pop('regex', None)
        self.validator = validators.RegexValidator(regex=regex)
        super(RegexValue, self).__init__(*args, **kwargs)


class PathValue(Value):
    def __init__(self, *args, **kwargs):
        self.check_exists = kwargs.pop('check_exists', True)
        super(PathValue, self).__init__(*args, **kwargs)

    def setup(self, name):
        value = super(PathValue, self).setup(name)
        value = os.path.expanduser(value)
        if self.check_exists and not os.path.exists(value):
            raise ValueError('Path {0!r} does  not exist.'.format(value))
        return os.path.abspath(value)


class SecretValue(Value):

    def __init__(self, *args, **kwargs):
        kwargs['environ'] = True
        super(SecretValue, self).__init__(*args, **kwargs)
        if self.default is not None:
            raise ValueError('Secret values are only allowed to '
                             'be set as environment variables')

    def setup(self, name):
        value = super(SecretValue, self).setup(name)
        if not value:
            raise ValueError('Secret value {0!r} is not set'.format(name))
        return value


class EmailURLValue(CastingMixin, MultipleMixin, Value):
    caster = 'dj_email_url.parse'
    message = 'Cannot interpret email URL value {0!r}'

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('environ', True)
        kwargs.setdefault('environ_prefix', None)
        kwargs.setdefault('environ_name', 'EMAIL_URL')
        super(EmailURLValue, self).__init__(*args, **kwargs)
        if self.default is None:
            self.default = {}
        else:
            self.default = self.to_python(self.default)


class DictBackendMixin(Value):
    default_alias = 'default'

    def __init__(self, *args, **kwargs):
        self.alias = kwargs.pop('alias', self.default_alias)
        kwargs.setdefault('environ', True)
        kwargs.setdefault('environ_prefix', None)
        kwargs.setdefault('environ_name', self.environ_name)
        super(DictBackendMixin, self).__init__(*args, **kwargs)
        if self.default is None:
            self.default = {}
        else:
            self.default = self.to_python(self.default)

    def to_python(self, value):
        value = super(DictBackendMixin, self).to_python(value)
        return {self.alias: value}


class DatabaseURLValue(DictBackendMixin, CastingMixin, Value):
    caster = 'dj_database_url.parse'
    message = 'Cannot interpret database URL value {0!r}'
    environ_name = 'DATABASE_URL'


class CacheURLValue(DictBackendMixin, CastingMixin, Value):
    caster = 'django_cache_url.parse'
    message = 'Cannot interpret cache URL value {0!r}'
    environ_name = 'CACHE_URL'


class SearchURLValue(DictBackendMixin, CastingMixin, Value):
    caster = 'dj_search_url.parse'
    message = 'Cannot interpret Search URL value {0!r}'
    environ_name = 'SEARCH_URL'

########NEW FILE########
__FILENAME__ = wsgi
from . import importer

importer.install()

try:
    from django.core.wsgi import get_wsgi_application
except ImportError:  # pragma: no cover
    from django.core.handlers.wsgi import WSGIHandler

    def get_wsgi_application():  # noqa
        return WSGIHandler()

# this is just for the crazy ones
application = get_wsgi_application()

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# django-configurations documentation build configuration file, created by
# sphinx-quickstart on Sat Jul 21 15:03:23 2012.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys
import os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), os.pardir))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.intersphinx', 'sphinx.ext.viewcode']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'django-configurations'
copyright = u'2012-2014, Jannis Leidel and other contributors'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
try:
    from configurations import __version__
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
htmlhelp_basename = 'django-configurationsdoc'


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
  ('index', 'django-configurations.tex', u'django-configurations Documentation',
   u'Jannis Leidel', 'manual'),
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
    ('index', 'django-configurations', u'django-configurations Documentation',
     [u'Jannis Leidel'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'django-configurations', u'django-configurations Documentation',
   u'Jannis Leidel', 'django-configurations', 'One line description of project.',
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
epub_title = u'django-configurations'
epub_author = u'Jannis Leidel'
epub_publisher = u'Jannis Leidel'
epub_copyright = u'2012, Jannis Leidel'

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


# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {
    'python': ('http://docs.python.org/2.7', None),
    'sphinx': ('http://sphinx.pocoo.org/', None),
    'django': ('http://docs.djangoproject.com/en/dev/',
               'http://docs.djangoproject.com/en/dev/_objects/'),
}

add_function_parentheses = add_module_names = False

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tests.settings.main')
    os.environ.setdefault('DJANGO_CONFIGURATION', 'Test')

    from configurations.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = base
from configurations import Configuration


def test_callback(request):
    return {}


class Base(Configuration):
    pass

########NEW FILE########
__FILENAME__ = main
import os
import uuid
import django

from configurations import Configuration, pristinemethod


class Test(Configuration):
    DEBUG = True

    SITE_ID = 1

    SECRET_KEY = str(uuid.uuid4())

    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': os.path.join(os.path.dirname(__file__), 'test.db'),
        }
    }

    INSTALLED_APPS = [
        'django.contrib.sessions',
        'django.contrib.contenttypes',
        'django.contrib.sites',
        'django.contrib.auth',
        'django.contrib.admin',
        'tests',
    ]

    ROOT_URLCONF = 'tests.urls'

    if django.VERSION[:2] < (1, 6):
        TEST_RUNNER = 'discover_runner.DiscoverRunner'

    def TEMPLATE_CONTEXT_PROCESSORS(self):
        return Configuration.TEMPLATE_CONTEXT_PROCESSORS + (
            'tests.settings.base.test_callback',
        )

    ATTRIBUTE_SETTING = True

    _PRIVATE_SETTING = 'ryan'

    @property
    def PROPERTY_SETTING(self):
        return 1

    def METHOD_SETTING(self):
        return 2

    LAMBDA_SETTING = lambda self: 3

    PRISTINE_LAMBDA_SETTING = pristinemethod(lambda: 4)

    @pristinemethod
    def PRISTINE_FUNCTION_SETTING():
        return 5

    @classmethod
    def pre_setup(cls):
        cls.PRE_SETUP_TEST_SETTING = 6

    @classmethod
    def post_setup(cls):
        cls.POST_SETUP_TEST_SETTING = 7

########NEW FILE########
__FILENAME__ = mixin_inheritance
from configurations import Configuration


class Mixin1(object):

    @property
    def TEMPLATE_CONTEXT_PROCESSORS(self):
        return super(Mixin1, self).TEMPLATE_CONTEXT_PROCESSORS + (
            'some_app.context_processors.processor1',)


class Mixin2(object):

    @property
    def TEMPLATE_CONTEXT_PROCESSORS(self):
        return super(Mixin2, self).TEMPLATE_CONTEXT_PROCESSORS + (
            'some_app.context_processors.processor2',)


class Inheritance(Mixin2, Mixin1, Configuration):

    @property
    def TEMPLATE_CONTEXT_PROCESSORS(self):
        return super(Inheritance, self).TEMPLATE_CONTEXT_PROCESSORS + (
            'some_app.context_processors.processorbase',)

########NEW FILE########
__FILENAME__ = multiple_inheritance
from .main import Test


class Inheritance(Test):

    def TEMPLATE_CONTEXT_PROCESSORS(self):
        return super(Inheritance, self).TEMPLATE_CONTEXT_PROCESSORS() + (
            'tests.settings.base.test_callback',)

########NEW FILE########
__FILENAME__ = single_inheritance
from .base import Base


class Inheritance(Base):

    def TEMPLATE_CONTEXT_PROCESSORS(self):
        return super(Inheritance, self).TEMPLATE_CONTEXT_PROCESSORS + (
            'tests.settings.base.test_callback',)

########NEW FILE########
__FILENAME__ = test_inheritance
import os

from django.conf import global_settings
from django.test import TestCase

from mock import patch


class InheritanceTests(TestCase):

    @patch.dict(os.environ, clear=True,
                DJANGO_CONFIGURATION='Inheritance',
                DJANGO_SETTINGS_MODULE='tests.settings.single_inheritance')
    def test_inherited(self):
        from tests.settings import single_inheritance
        self.assertEqual(single_inheritance.TEMPLATE_CONTEXT_PROCESSORS,
                         global_settings.TEMPLATE_CONTEXT_PROCESSORS + (
                             'tests.settings.base.test_callback',
                         ))

    @patch.dict(os.environ, clear=True,
                DJANGO_CONFIGURATION='Inheritance',
                DJANGO_SETTINGS_MODULE='tests.settings.multiple_inheritance')
    def test_inherited2(self):
        from tests.settings import multiple_inheritance
        self.assertEqual(multiple_inheritance.TEMPLATE_CONTEXT_PROCESSORS,
                         global_settings.TEMPLATE_CONTEXT_PROCESSORS + (
                             'tests.settings.base.test_callback',
                             'tests.settings.base.test_callback',
                         ))

    @patch.dict(os.environ, clear=True,
                DJANGO_CONFIGURATION='Inheritance',
                DJANGO_SETTINGS_MODULE='tests.settings.mixin_inheritance')
    def test_inherited3(self):
        from tests.settings import mixin_inheritance
        self.assertEqual(mixin_inheritance.TEMPLATE_CONTEXT_PROCESSORS,
                         global_settings.TEMPLATE_CONTEXT_PROCESSORS + (
                             'some_app.context_processors.processor1',
                             'some_app.context_processors.processor2',
                             'some_app.context_processors.processorbase',
                         ))

########NEW FILE########
__FILENAME__ = test_main
import os
import sys

from django.conf import global_settings
from django.test import TestCase
from django.core.exceptions import ImproperlyConfigured

from mock import patch

from configurations.importer import ConfigurationImporter


class MainTests(TestCase):

    def test_simple(self):
        from tests.settings import main
        self.assertEqual(main.ATTRIBUTE_SETTING, True)
        self.assertEqual(main.PROPERTY_SETTING, 1)
        self.assertEqual(main.METHOD_SETTING, 2)
        self.assertEqual(main.LAMBDA_SETTING, 3)
        self.assertNotEqual(main.PRISTINE_LAMBDA_SETTING, 4)
        self.assertTrue(lambda: callable(main.PRISTINE_LAMBDA_SETTING))
        self.assertNotEqual(main.PRISTINE_FUNCTION_SETTING, 5)
        self.assertTrue(lambda: callable(main.PRISTINE_FUNCTION_SETTING))
        self.assertEqual(main.TEMPLATE_CONTEXT_PROCESSORS,
                         global_settings.TEMPLATE_CONTEXT_PROCESSORS + (
                             'tests.settings.base.test_callback',
                         ))
        self.assertEqual(main.PRE_SETUP_TEST_SETTING, 6)
        self.assertRaises(AttributeError, lambda: main.POST_SETUP_TEST_SETTING)
        self.assertEqual(main.Test.POST_SETUP_TEST_SETTING, 7)

    def test_global_arrival(self):
        from django.conf import settings
        self.assertEqual(settings.PROPERTY_SETTING, 1)
        self.assertRaises(AttributeError, lambda: settings._PRIVATE_SETTING)
        self.assertNotEqual(settings.PRISTINE_LAMBDA_SETTING, 4)
        self.assertTrue(lambda: callable(settings.PRISTINE_LAMBDA_SETTING))
        self.assertNotEqual(settings.PRISTINE_FUNCTION_SETTING, 5)
        self.assertTrue(lambda: callable(settings.PRISTINE_FUNCTION_SETTING))
        self.assertEqual(settings.PRE_SETUP_TEST_SETTING, 6)

    @patch.dict(os.environ, clear=True, DJANGO_CONFIGURATION='Test')
    def test_empty_module_var(self):
        self.assertRaises(ImproperlyConfigured, ConfigurationImporter)

    @patch.dict(os.environ, clear=True,
                DJANGO_SETTINGS_MODULE='tests.settings.main')
    def test_empty_class_var(self):
        self.assertRaises(ImproperlyConfigured, ConfigurationImporter)

    def test_global_settings(self):
        from configurations.base import Configuration
        self.assertIn('dictConfig', Configuration.LOGGING_CONFIG)
        self.assertEqual(repr(Configuration),
                         "<Configuration 'configurations.base.Configuration'>")

    def test_repr(self):
        from tests.settings.main import Test
        self.assertEqual(repr(Test),
                         "<Configuration 'tests.settings.main.Test'>")

    @patch.dict(os.environ, clear=True,
                DJANGO_SETTINGS_MODULE='tests.settings.main',
                DJANGO_CONFIGURATION='Test')
    def test_initialization(self):
        importer = ConfigurationImporter()
        self.assertEqual(importer.module, 'tests.settings.main')
        self.assertEqual(importer.name, 'Test')
        self.assertEqual(repr(importer),
                         "<ConfigurationImporter for 'tests.settings.main.Test'>")

    @patch.dict(os.environ, clear=True,
                DJANGO_SETTINGS_MODULE='tests.settings.inheritance',
                DJANGO_CONFIGURATION='Inheritance')
    def test_initialization_inheritance(self):
        importer = ConfigurationImporter()
        self.assertEqual(importer.module,
                         'tests.settings.inheritance')
        self.assertEqual(importer.name, 'Inheritance')

    @patch.dict(os.environ, clear=True,
                DJANGO_SETTINGS_MODULE='tests.settings.main',
                DJANGO_CONFIGURATION='NonExisting')
    @patch.object(sys, 'argv', ['python', 'manage.py', 'test',
                                '--settings=tests.settings.main',
                                '--configuration=Test'])
    def test_configuration_option(self):
        importer = ConfigurationImporter(check_options=False)
        self.assertEqual(importer.module, 'tests.settings.main')
        self.assertEqual(importer.name, 'NonExisting')
        importer = ConfigurationImporter(check_options=True)
        self.assertEqual(importer.module, 'tests.settings.main')
        self.assertEqual(importer.name, 'Test')

########NEW FILE########
__FILENAME__ = test_values
import decimal
import os
from contextlib import contextmanager

from django.test import TestCase
from django.core.exceptions import ImproperlyConfigured

from mock import patch

from configurations.values import (Value, BooleanValue, IntegerValue,
                                   FloatValue, DecimalValue, ListValue,
                                   TupleValue, SetValue, DictValue,
                                   URLValue, EmailValue, IPValue,
                                   RegexValue, PathValue, SecretValue,
                                   DatabaseURLValue, EmailURLValue,
                                   CacheURLValue, BackendsValue,
                                   CastingMixin, SearchURLValue)


@contextmanager
def env(**kwargs):
    with patch.dict(os.environ, clear=True, **kwargs):
        yield


class FailingCasterValue(CastingMixin, Value):
    caster = 'non.existing.caster'


class ValueTests(TestCase):

    def test_value(self):
        value = Value('default', environ=False)
        self.assertEqual(value.setup('TEST'), 'default')
        with env(DJANGO_TEST='override'):
            self.assertEqual(value.setup('TEST'), 'default')

    @patch.dict(os.environ, clear=True, DJANGO_TEST='override')
    def test_env_var(self):
        value = Value('default')
        self.assertEqual(value.setup('TEST'), 'override')
        self.assertNotEqual(value.setup('TEST'), value.default)
        self.assertEqual(value.to_python(os.environ['DJANGO_TEST']),
                         value.setup('TEST'))

    def test_value_reuse(self):
        value1 = Value('default')
        value2 = Value(value1)
        self.assertEqual(value1.setup('TEST1'), 'default')
        self.assertEqual(value2.setup('TEST2'), 'default')
        with env(DJANGO_TEST1='override1', DJANGO_TEST2='override2'):
            self.assertEqual(value1.setup('TEST1'), 'override1')
            self.assertEqual(value2.setup('TEST2'), 'override2')

    def test_env_var_prefix(self):
        with patch.dict(os.environ, clear=True, ACME_TEST='override'):
            value = Value('default', environ_prefix='ACME')
            self.assertEqual(value.setup('TEST'), 'override')

        with patch.dict(os.environ, clear=True, TEST='override'):
            value = Value('default', environ_prefix='')
            self.assertEqual(value.setup('TEST'), 'override')

    def test_boolean_values_true(self):
        value = BooleanValue(False)
        for truthy in value.true_values:
            with env(DJANGO_TEST=truthy):
                self.assertTrue(value.setup('TEST'))

    def test_boolean_values_faulty(self):
        self.assertRaises(ValueError, BooleanValue, 'false')

    def test_boolean_values_false(self):
        value = BooleanValue(True)
        for falsy in value.false_values:
            with env(DJANGO_TEST=falsy):
                self.assertFalse(value.setup('TEST'))

    def test_boolean_values_nonboolean(self):
        value = BooleanValue(True)
        with env(DJANGO_TEST='nonboolean'):
            self.assertRaises(ValueError, value.setup, 'TEST')

    def test_integer_values(self):
        value = IntegerValue(1)
        with env(DJANGO_TEST='2'):
            self.assertEqual(value.setup('TEST'), 2)
        with env(DJANGO_TEST='noninteger'):
            self.assertRaises(ValueError, value.setup, 'TEST')

    def test_float_values(self):
        value = FloatValue(1.0)
        with env(DJANGO_TEST='2.0'):
            self.assertEqual(value.setup('TEST'), 2.0)
        with env(DJANGO_TEST='noninteger'):
            self.assertRaises(ValueError, value.setup, 'TEST')

    def test_decimal_values(self):
        value = DecimalValue(decimal.Decimal(1))
        with env(DJANGO_TEST='2'):
            self.assertEqual(value.setup('TEST'), decimal.Decimal(2))
        with env(DJANGO_TEST='nondecimal'):
            self.assertRaises(ValueError, value.setup, 'TEST')

    def test_failing_caster(self):
        self.assertRaises(ImproperlyConfigured, FailingCasterValue)

    def test_list_values_default(self):
        value = ListValue()
        with env(DJANGO_TEST='2,2'):
            self.assertEqual(value.setup('TEST'), ['2', '2'])
        with env(DJANGO_TEST='2, 2 ,'):
            self.assertEqual(value.setup('TEST'), ['2', '2'])
        with env(DJANGO_TEST=''):
            self.assertEqual(value.setup('TEST'), [])

    def test_list_values_separator(self):
        value = ListValue(separator=':')
        with env(DJANGO_TEST='/usr/bin:/usr/sbin:/usr/local/bin'):
            self.assertEqual(value.setup('TEST'),
                             ['/usr/bin', '/usr/sbin', '/usr/local/bin'])

    def test_List_values_converter(self):
        value = ListValue(converter=int)
        with env(DJANGO_TEST='2,2'):
            self.assertEqual(value.setup('TEST'), [2, 2])

        value = ListValue(converter=float)
        with env(DJANGO_TEST='2,2'):
            self.assertEqual(value.setup('TEST'), [2.0, 2.0])

    def test_list_values_custom_converter(self):
        value = ListValue(converter=lambda x: x * 2)
        with env(DJANGO_TEST='2,2'):
            self.assertEqual(value.setup('TEST'), ['22', '22'])

    def test_list_values_converter_exception(self):
        value = ListValue(converter=int)
        with env(DJANGO_TEST='2,b'):
            self.assertRaises(ValueError, value.setup, 'TEST')

    def test_tuple_values_default(self):
        value = TupleValue()
        with env(DJANGO_TEST='2,2'):
            self.assertEqual(value.setup('TEST'), ('2', '2'))
        with env(DJANGO_TEST='2, 2 ,'):
            self.assertEqual(value.setup('TEST'), ('2', '2'))
        with env(DJANGO_TEST=''):
            self.assertEqual(value.setup('TEST'), ())

    def test_set_values_default(self):
        value = SetValue()
        with env(DJANGO_TEST='2,2'):
            self.assertEqual(value.setup('TEST'), set(['2', '2']))
        with env(DJANGO_TEST='2, 2 ,'):
            self.assertEqual(value.setup('TEST'), set(['2', '2']))
        with env(DJANGO_TEST=''):
            self.assertEqual(value.setup('TEST'), set())

    def test_dict_values_default(self):
        value = DictValue()
        with env(DJANGO_TEST='{2: 2}'):
            self.assertEqual(value.setup('TEST'), {2: 2})
        expected = {2: 2, '3': '3', '4': [1, 2, 3]}
        with env(DJANGO_TEST="{2: 2, '3': '3', '4': [1, 2, 3]}"):
            self.assertEqual(value.setup('TEST'), expected)
        with env(DJANGO_TEST="""{
                    2: 2,
                    '3': '3',
                    '4': [1, 2, 3],
                }"""):
            self.assertEqual(value.setup('TEST'), expected)
        with env(DJANGO_TEST=''):
            self.assertEqual(value.setup('TEST'), {})
        with env(DJANGO_TEST='spam'):
            self.assertRaises(ValueError, value.setup, 'TEST')

    def test_email_values(self):
        value = EmailValue('spam@eg.gs')
        with env(DJANGO_TEST='spam@sp.am'):
            self.assertEqual(value.setup('TEST'), 'spam@sp.am')
        with env(DJANGO_TEST='spam'):
            self.assertRaises(ValueError, value.setup, 'TEST')

    def test_url_values(self):
        value = URLValue('http://eggs.spam')
        with env(DJANGO_TEST='http://spam.eggs'):
            self.assertEqual(value.setup('TEST'), 'http://spam.eggs')
        with env(DJANGO_TEST='httb://spam.eggs'):
            self.assertRaises(ValueError, value.setup, 'TEST')

    def test_ip_values(self):
        value = IPValue('0.0.0.0')
        with env(DJANGO_TEST='127.0.0.1'):
            self.assertEqual(value.setup('TEST'), '127.0.0.1')
        with env(DJANGO_TEST='::1'):
            self.assertEqual(value.setup('TEST'), '::1')
        with env(DJANGO_TEST='spam.eggs'):
            self.assertRaises(ValueError, value.setup, 'TEST')

    def test_regex_values(self):
        value = RegexValue('000--000', regex=r'\d+--\d+')
        with env(DJANGO_TEST='123--456'):
            self.assertEqual(value.setup('TEST'), '123--456')
        with env(DJANGO_TEST='123456'):
            self.assertRaises(ValueError, value.setup, 'TEST')

    def test_path_values_with_check(self):
        value = PathValue()
        with env(DJANGO_TEST='/'):
            self.assertEqual(value.setup('TEST'), '/')
        with env(DJANGO_TEST='~/'):
            self.assertEqual(value.setup('TEST'), os.path.expanduser('~'))
        with env(DJANGO_TEST='/does/not/exist'):
            self.assertRaises(ValueError, value.setup, 'TEST')

    def test_path_values_no_check(self):
        value = PathValue(check_exists=False)
        with env(DJANGO_TEST='/'):
            self.assertEqual(value.setup('TEST'), '/')
        with env(DJANGO_TEST='~/spam/eggs'):
            self.assertEqual(value.setup('TEST'),
                             os.path.join(os.path.expanduser('~'),
                                          'spam', 'eggs'))
        with env(DJANGO_TEST='/does/not/exist'):
            self.assertEqual(value.setup('TEST'), '/does/not/exist')

    def test_secret_value(self):
        self.assertRaises(ValueError, SecretValue, 'default')

        value = SecretValue()
        self.assertRaises(ValueError, value.setup, 'TEST')
        with env(DJANGO_SECRET_KEY='123'):
            self.assertEqual(value.setup('SECRET_KEY'), '123')

        value = SecretValue(environ_name='FACEBOOK_API_SECRET',
                            environ_prefix=None)
        self.assertRaises(ValueError, value.setup, 'TEST')
        with env(FACEBOOK_API_SECRET='123'):
            self.assertEqual(value.setup('TEST'), '123')

    def test_database_url_value(self):
        value = DatabaseURLValue()
        self.assertEqual(value.default, {})
        with env(DATABASE_URL='sqlite://'):
            self.assertEqual(value.setup('DATABASE_URL'), {
                'default': {
                    'ENGINE': 'django.db.backends.sqlite3',
                    'HOST': '',
                    'NAME': ':memory:',
                    'PASSWORD': '',
                    'PORT': '',
                    'USER': '',
                }})

    def test_email_url_value(self):
        value = EmailURLValue()
        self.assertEqual(value.default, {})
        with env(EMAIL_URL='smtps://user@domain.com:password@smtp.example.com:587'):
            self.assertEqual(value.setup('EMAIL_URL'), {
                'EMAIL_BACKEND': 'django.core.mail.backends.smtp.EmailBackend',
                'EMAIL_FILE_PATH': '',
                'EMAIL_HOST': 'smtp.example.com',
                'EMAIL_HOST_PASSWORD': 'password',
                'EMAIL_HOST_USER': 'user@domain.com',
                'EMAIL_PORT': 587,
                'EMAIL_USE_TLS': True})
        with env(EMAIL_URL='console://'):
            self.assertEqual(value.setup('EMAIL_URL'), {
                'EMAIL_BACKEND': 'django.core.mail.backends.console.EmailBackend',
                'EMAIL_FILE_PATH': '',
                'EMAIL_HOST': None,
                'EMAIL_HOST_PASSWORD': None,
                'EMAIL_HOST_USER': None,
                'EMAIL_PORT': None,
                'EMAIL_USE_TLS': False})
        with env(EMAIL_URL='smtps://user@domain.com:password@smtp.example.com:wrong'):
            self.assertRaises(ValueError, value.setup, 'TEST')

    def test_cache_url_value(self):
        cache_setting = {
            'default': {
                'BACKEND': 'redis_cache.cache.RedisCache',
                'KEY_PREFIX': '',
                'LOCATION': 'host:port:1'
            }
        }
        cache_url = 'redis://user@host:port/1'
        value = CacheURLValue(cache_url)
        self.assertEqual(value.default, cache_setting)
        value = CacheURLValue()
        self.assertEqual(value.default, {})
        with env(CACHE_URL='redis://user@host:port/1'):
            self.assertEqual(value.setup('CACHE_URL'), cache_setting)
        with env(CACHE_URL='wrong://user@host:port/1'):
            self.assertRaises(KeyError, value.setup, 'TEST')

    def test_search_url_value(self):
        value = SearchURLValue()
        self.assertEqual(value.default, {})
        with env(SEARCH_URL='elasticsearch://127.0.0.1:9200/index'):
            self.assertEqual(value.setup('SEARCH_URL'), {
                'default': {
                    'ENGINE': 'haystack.backends.elasticsearch_backend.ElasticsearchSearchEngine',
                    'URL': 'http://127.0.0.1:9200',
                    'INDEX_NAME': 'index',
                }})

    def test_backend_list_value(self):
        backends = ['django.middleware.common.CommonMiddleware']
        value = BackendsValue(backends)
        self.assertEqual(value.setup('TEST'), backends)

        backends = ['non.existing.Backend']
        self.assertRaises(ValueError, BackendsValue, backends)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import include, patterns

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    (r'^admin/', include(admin.site.urls)),
)

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'test_project.settings')
    os.environ.setdefault('DJANGO_CONFIGURATION', 'Debug')

    from configurations.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = settings
from configurations import Configuration, values


class Base(Configuration):
    # Django settings for test_project project.

    DEBUG = values.BooleanValue(True, environ=True)
    TEMPLATE_DEBUG = DEBUG

    ADMINS = (
        # ('Your Name', 'your_email@example.com'),
    )

    EMAIL_URL = values.EmailURLValue('console://', environ=True)

    MANAGERS = ADMINS

    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',  # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
            'NAME': '',                      # Or path to database file if using sqlite3.
            'USER': '',                      # Not used with sqlite3.
            'PASSWORD': '',                  # Not used with sqlite3.
            'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
            'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
        }
    }

    # Hosts/domain names that are valid for this site; required if DEBUG is False
    # See https://docs.djangoproject.com/en/1.4/ref/settings/#allowed-hosts
    ALLOWED_HOSTS = []

    # Local time zone for this installation. Choices can be found here:
    # http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
    # although not all choices may be available on all operating systems.
    # In a Windows environment this must be set to your system time zone.
    TIME_ZONE = 'America/Chicago'

    # Language code for this installation. All choices can be found here:
    # http://www.i18nguy.com/unicode/language-identifiers.html
    LANGUAGE_CODE = 'en-us'

    SITE_ID = 1

    # If you set this to False, Django will make some optimizations so as not
    # to load the internationalization machinery.
    USE_I18N = True

    # If you set this to False, Django will not format dates, numbers and
    # calendars according to the current locale.
    USE_L10N = True

    # If you set this to False, Django will not use timezone-aware datetimes.
    USE_TZ = True

    # Absolute filesystem path to the directory that will hold user-uploaded files.
    # Example: "/home/media/media.lawrence.com/media/"
    MEDIA_ROOT = ''

    # URL that handles the media served from MEDIA_ROOT. Make sure to use a
    # trailing slash.
    # Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
    MEDIA_URL = ''

    # Absolute path to the directory static files should be collected to.
    # Don't put anything in this directory yourself; store your static files
    # in apps' "static/" subdirectories and in STATICFILES_DIRS.
    # Example: "/home/media/media.lawrence.com/static/"
    STATIC_ROOT = ''

    # URL prefix for static files.
    # Example: "http://media.lawrence.com/static/"
    STATIC_URL = '/static/'

    # Additional locations of static files
    STATICFILES_DIRS = (
        # Put strings here, like "/home/html/static" or "C:/www/django/static".
        # Always use forward slashes, even on Windows.
        # Don't forget to use absolute paths, not relative paths.
    )

    # List of finder classes that know how to find static files in
    # various locations.
    STATICFILES_FINDERS = (
        'django.contrib.staticfiles.finders.FileSystemFinder',
        'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    #    'django.contrib.staticfiles.finders.DefaultStorageFinder',
    )

    # Make this unique, and don't share it with anybody.
    SECRET_KEY = '-9i$j8kcp48(y-v0hiwgycp5jb*_)sy4(swd@#m(j1m*4vfn4w'

    # List of callables that know how to import templates from various sources.
    TEMPLATE_LOADERS = (
        'django.template.loaders.filesystem.Loader',
        'django.template.loaders.app_directories.Loader',
    )

    MIDDLEWARE_CLASSES = (
        'django.middleware.common.CommonMiddleware',
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.middleware.csrf.CsrfViewMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
        'django.contrib.messages.middleware.MessageMiddleware',
        # Uncomment the next line for simple clickjacking protection:
        # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
    )

    ROOT_URLCONF = 'test_project.urls'

    # Python dotted path to the WSGI application used by Django's runserver.
    WSGI_APPLICATION = 'test_project.wsgi.application'

    TEMPLATE_DIRS = (
        # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
        # Always use forward slashes, even on Windows.
        # Don't forget to use absolute paths, not relative paths.
    )

    INSTALLED_APPS = (
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.sessions',
        'django.contrib.sites',
        'django.contrib.messages',
        'django.contrib.staticfiles',
        # Uncomment the next line to enable the admin:
        # 'django.contrib.admin',
        # Uncomment the next line to enable admin documentation:
        # 'django.contrib.admindocs',
        'configurations',
    )

    # A sample logging configuration. The only tangible logging
    # performed by this configuration is to send an email to
    # the site admins on every HTTP 500 error when DEBUG=False.
    # See http://docs.djangoproject.com/en/dev/topics/logging for
    # more details on how to customize your logging configuration.
    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'filters': {
            'require_debug_false': {
                '()': 'django.utils.log.RequireDebugFalse'
            }
        },
        'handlers': {
            'mail_admins': {
                'level': 'ERROR',
                'filters': ['require_debug_false'],
                'class': 'django.utils.log.AdminEmailHandler'
            }
        },
        'loggers': {
            'django.request': {
                'handlers': ['mail_admins'],
                'level': 'ERROR',
                'propagate': True,
            },
        }
    }

    INSTALLED_APPS = (
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.sessions',
        'django.contrib.sites',
        'django.contrib.messages',
        'django.contrib.staticfiles',
        # Uncomment the next line to enable the admin:
        # 'django.contrib.admin',
        # Uncomment the next line to enable admin documentation:
        # 'django.contrib.admindocs',
        'configurations',
    )


class Debug(Base):
    YEAH = True


class Other(Base):
    YEAH = False

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'test_project.views.home', name='home'),
    # url(r'^test_project/', include('test_project.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # url(r'^admin/', include(admin.site.urls)),
)

########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for test_project project.

This module contains the WSGI application used by Django's development server
and any production WSGI deployments. It should expose a module-level variable
named ``application``. Django's ``runserver`` and ``runfcgi`` commands discover
this application via the ``WSGI_APPLICATION`` setting.

Usually you will have the standard Django WSGI application here, but it also
might make sense to replace the whole Django WSGI application with a custom one
that later delegates to the Django one. For example, you could introduce WSGI
middleware here, or combine a Django application with an application of another
framework.

"""
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "test_project.settings")

# This application object is used by any WSGI server configured to use this
# file. This includes Django's development server, if the WSGI_APPLICATION
# setting points here.
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

# Apply WSGI middleware here.
# from helloworld.wsgi import HelloWorldApplication
# application = HelloWorldApplication(application)

########NEW FILE########
