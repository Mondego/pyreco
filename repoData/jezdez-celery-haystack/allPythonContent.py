__FILENAME__ = conf
from django.conf import settings  # noqa
from django.core.exceptions import ImproperlyConfigured
from haystack import constants, __version__ as haystack_version
from appconf import AppConf


class CeleryHaystack(AppConf):
    #: The default alias to
    DEFAULT_ALIAS = None
    #: The delay (in seconds) after which a failed index is retried
    RETRY_DELAY = 5 * 60
    #: The number of retries that are done
    MAX_RETRIES = 1
    #: The default Celery task class
    DEFAULT_TASK = 'celery_haystack.tasks.CeleryHaystackSignalHandler'
    #: Whether the task should be handled transaction safe
    TRANSACTION_SAFE = True

    #: The batch size used by the CeleryHaystackUpdateIndex task
    COMMAND_BATCH_SIZE = None
    #: The max age of items used by the CeleryHaystackUpdateIndex task
    COMMAND_AGE = None
    #: Wehther to remove items from the index that aren't in the DB anymore
    COMMAND_REMOVE = False
    #: The number of multiprocessing workers used by the CeleryHaystackUpdateIndex task
    COMMAND_WORKERS = 0
    #: The names of apps to run update_index for
    COMMAND_APPS = []
    #: The verbosity level of the update_index call
    COMMAND_VERBOSITY = 1

    def configure_default_alias(self, value):
        return value or getattr(constants, 'DEFAULT_ALIAS', None)

    def configure(self):
        data = {}
        for name, value in self.configured_data.items():
            if name in ('RETRY_DELAY', 'MAX_RETRIES',
                        'COMMAND_WORKERS', 'COMMAND_VERBOSITY'):
                value = int(value)
            data[name] = value
        return data


signal_processor = getattr(settings, 'HAYSTACK_SIGNAL_PROCESSOR', None)


if haystack_version[0] >= 2 and signal_processor is None:
    raise ImproperlyConfigured("When using celery-haystack with Haystack 2.X "
                               "the HAYSTACK_SIGNAL_PROCESSOR setting must be "
                               "set. Use 'celery_haystack.signals."
                               "CelerySignalProcessor' as default.")

########NEW FILE########
__FILENAME__ = indexes
from django.db.models import signals

from haystack import indexes

from .utils import enqueue_task


class CelerySearchIndex(indexes.SearchIndex):
    """
    A ``SearchIndex`` subclass that enqueues updates/deletes for later
    processing using Celery.
    """
    # We override the built-in _setup_* methods to connect the enqueuing
    # operation.
    def _setup_save(self, model):
        signals.post_save.connect(self.enqueue_save,
                                  sender=model,
                                  dispatch_uid=CelerySearchIndex)

    def _setup_delete(self, model):
        signals.post_delete.connect(self.enqueue_delete,
                                    sender=model,
                                    dispatch_uid=CelerySearchIndex)

    def _teardown_save(self, model):
        signals.post_save.disconnect(self.enqueue_save,
                                     sender=model,
                                     dispatch_uid=CelerySearchIndex)

    def _teardown_delete(self, model):
        signals.post_delete.disconnect(self.enqueue_delete,
                                       sender=model,
                                       dispatch_uid=CelerySearchIndex)

    def enqueue_save(self, instance, **kwargs):
        if not getattr(instance, 'skip_indexing', False):
            return self.enqueue('update', instance)

    def enqueue_delete(self, instance, **kwargs):
        if not getattr(instance, 'skip_indexing', False):
            return self.enqueue('delete', instance)

    def enqueue(self, action, instance):
        """
        Shoves a message about how to update the index into the queue.

        This is a standardized string, resembling something like::

            ``notes.note.23``
            # ...or...
            ``weblog.entry.8``
        """
        return enqueue_task(action, instance)

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = signals
from django.db.models import signals

from haystack.signals import BaseSignalProcessor
from haystack.exceptions import NotHandled

from .utils import enqueue_task
from .indexes import CelerySearchIndex


class CelerySignalProcessor(BaseSignalProcessor):

    def setup(self):
        signals.post_save.connect(self.enqueue_save)
        signals.post_delete.connect(self.enqueue_delete)

    def teardown(self):
        signals.post_save.disconnect(self.enqueue_save)
        signals.post_delete.disconnect(self.enqueue_delete)

    def enqueue_save(self, sender, instance, **kwargs):
        return self.enqueue('update', instance, sender, **kwargs)

    def enqueue_delete(self, sender, instance, **kwargs):
        return self.enqueue('delete', instance, sender, **kwargs)

    def enqueue(self, action, instance, sender, **kwargs):
        """
        Given an individual model instance, determine if a backend
        handles the model, check if the index is Celery-enabled and
        enqueue task.
        """
        using_backends = self.connection_router.for_write(instance=instance)

        for using in using_backends:
            try:
                connection = self.connections[using]
                index = connection.get_unified_index().get_index(sender)
            except NotHandled:
                continue  # Check next backend

            if isinstance(index, CelerySearchIndex):
                if action == 'update' and not index.should_update(instance):
                    continue
                enqueue_task(action, instance)
                return  # Only enqueue instance once

########NEW FILE########
__FILENAME__ = tasks
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.db.models.loading import get_model

from .conf import settings

try:
    from haystack import connections, connection_router
    from haystack.exceptions import NotHandled as IndexNotFoundException
    legacy = False
except ImportError:
    try:
        from haystack import site
        from haystack.exceptions import NotRegistered as IndexNotFoundException  # noqa
        legacy = True
    except ImportError as e:
        raise ImproperlyConfigured("Haystack couldn't be imported: %s" % e)

if settings.CELERY_HAYSTACK_TRANSACTION_SAFE and not getattr(settings, 'CELERY_ALWAYS_EAGER', False):
    from djcelery_transactions import PostTransactionTask as Task
else:
    from celery.task import Task  # noqa


class CeleryHaystackSignalHandler(Task):
    using = settings.CELERY_HAYSTACK_DEFAULT_ALIAS
    max_retries = settings.CELERY_HAYSTACK_MAX_RETRIES
    default_retry_delay = settings.CELERY_HAYSTACK_RETRY_DELAY

    def split_identifier(self, identifier, **kwargs):
        """
        Break down the identifier representing the instance.

        Converts 'notes.note.23' into ('notes.note', 23).
        """
        bits = identifier.split('.')

        if len(bits) < 2:
            logger = self.get_logger(**kwargs)
            logger.error("Unable to parse object "
                         "identifer '%s'. Moving on..." % identifier)
            return (None, None)

        pk = bits[-1]
        # In case Django ever handles full paths...
        object_path = '.'.join(bits[:-1])
        return (object_path, pk)

    def get_model_class(self, object_path, **kwargs):
        """
        Fetch the model's class in a standarized way.
        """
        bits = object_path.split('.')
        app_name = '.'.join(bits[:-1])
        classname = bits[-1]
        model_class = get_model(app_name, classname)

        if model_class is None:
            raise ImproperlyConfigured("Could not load model '%s'." %
                                       object_path)
        return model_class

    def get_instance(self, model_class, pk, **kwargs):
        """
        Fetch the instance in a standarized way.
        """
        logger = self.get_logger(**kwargs)
        instance = None
        try:
            instance = model_class._default_manager.get(pk=int(pk))
        except model_class.DoesNotExist:
            logger.error("Couldn't load %s.%s.%s. Somehow it went missing?" %
                         (model_class._meta.app_label.lower(),
                          model_class._meta.object_name.lower(), pk))
        except model_class.MultipleObjectsReturned:
            logger.error("More than one object with pk %s. Oops?" % pk)
        return instance

    def get_indexes(self, model_class, **kwargs):
        """
        Fetch the model's registered ``SearchIndex`` in a standarized way.
        """
        try:
            if legacy:
                index_holder = site
                yield index_holder.get_index(model_class)
            else:
                using_backends = connection_router.for_write(**{'models': [model_class]})
                for using in using_backends:
                    index_holder = connections[using].get_unified_index()
                    yield index_holder.get_index(model_class)
        except IndexNotFoundException:
            raise ImproperlyConfigured("Couldn't find a SearchIndex for %s." %
                                       model_class)

    def get_handler_options(self, **kwargs):
        options = {}
        if legacy:
            options['using'] = self.using
        return options

    def run(self, action, identifier, **kwargs):
        """
        Trigger the actual index handler depending on the
        given action ('update' or 'delete').
        """
        logger = self.get_logger(**kwargs)

        # First get the object path and pk (e.g. ('notes.note', 23))
        object_path, pk = self.split_identifier(identifier, **kwargs)
        if object_path is None or pk is None:
            msg = "Couldn't handle object with identifier %s" % identifier
            logger.error(msg)
            raise ValueError(msg)

        # Then get the model class for the object path
        model_class = self.get_model_class(object_path, **kwargs)
        for current_index in self.get_indexes(model_class, **kwargs):
            current_index_name = ".".join([current_index.__class__.__module__,
                                           current_index.__class__.__name__])

            if action == 'delete':
                # If the object is gone, we'll use just the identifier
                # against the index.
                try:
                    handler_options = self.get_handler_options(**kwargs)
                    current_index.remove_object(identifier, **handler_options)
                except Exception as exc:
                    logger.exception(exc)
                    self.retry(exc=exc)
                else:
                    msg = ("Deleted '%s' (with %s)" %
                           (identifier, current_index_name))
                    logger.debug(msg)
                    return msg
            elif action == 'update':
                # and the instance of the model class with the pk
                instance = self.get_instance(model_class, pk, **kwargs)
                if instance is None:
                    logger.debug("Failed updating '%s' (with %s)" %
                                 (identifier, current_index_name))
                    raise ValueError("Couldn't load object '%s'" % identifier)

                # Call the appropriate handler of the current index and
                # handle exception if neccessary
                try:
                    handler_options = self.get_handler_options(**kwargs)
                    current_index.update_object(instance, **handler_options)
                except Exception as exc:
                    logger.exception(exc)
                    self.retry(exc=exc)
                else:
                    msg = ("Updated '%s' (with %s)" %
                           (identifier, current_index_name))
                    logger.debug(msg)
                    return msg
            else:
                logger.error("Unrecognized action '%s'. Moving on..." % action)
                raise ValueError("Unrecognized action %s" % action)


class CeleryHaystackUpdateIndex(Task):
    """
    A celery task class to be used to call the update_index management
    command from Celery.
    """
    def run(self, apps=None, **kwargs):
        logger = self.get_logger(**kwargs)
        defaults = {
            'batchsize': settings.CELERY_HAYSTACK_COMMAND_BATCH_SIZE,
            'age': settings.CELERY_HAYSTACK_COMMAND_AGE,
            'remove': settings.CELERY_HAYSTACK_COMMAND_REMOVE,
            'using': settings.CELERY_HAYSTACK_DEFAULT_ALIAS,
            'workers': settings.CELERY_HAYSTACK_COMMAND_WORKERS,
            'verbosity': settings.CELERY_HAYSTACK_COMMAND_VERBOSITY,
        }
        defaults.update(kwargs)
        if apps is None:
            apps = settings.CELERY_HAYSTACK_COMMAND_APPS
        # Run the update_index management command
        logger.info("Starting update index")
        call_command('update_index', *apps, **defaults)
        logger.info("Finishing update index")

########NEW FILE########
__FILENAME__ = models
from django.db import models


class Note(models.Model):
    content = models.TextField()

    def __unicode__(self):
        return self.content

########NEW FILE########
__FILENAME__ = search_indexes
from haystack import indexes, __version__ as haystack_version

from .models import Note
from ..indexes import CelerySearchIndex

if haystack_version[:2] < (2, 0):
    from haystack import site

    class Indexable(object):
        pass
    indexes.Indexable = Indexable
else:
    site = None  # noqa


# Simplest possible subclass that could work.
class NoteIndex(CelerySearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, model_attr='content')

    def get_model(self):
        return Note

if site:
    site.register(Note, NoteIndex)

########NEW FILE########
__FILENAME__ = search_sites
import haystack

haystack.autodiscover()

########NEW FILE########
__FILENAME__ = tests
from django.core.management import call_command
from django.test import TestCase

from haystack.query import SearchQuerySet

from .models import Note


class QueuedSearchIndexTestCase(TestCase):

    def assertSearchResultLength(self, count):
        self.assertEqual(count, len(SearchQuerySet()))

    def assertSearchResultContains(self, pk, text):
        results = SearchQuerySet().filter(id='tests.note.%s' % pk)
        self.assertTrue(results)
        self.assertTrue(text in results[0].text)

    def setUp(self):
        # Nuke the index.
        call_command('clear_index', interactive=False, verbosity=0)

        # Throw away all Notes
        Note.objects.all().delete()

    def test_update(self):
        self.assertSearchResultLength(0)
        note1 = Note.objects.create(content='Because everyone loves tests.')
        self.assertSearchResultLength(1)
        self.assertSearchResultContains(note1.pk, 'loves')

        note2 = Note.objects.create(content='More test data.')
        self.assertSearchResultLength(2)
        self.assertSearchResultContains(note2.pk, 'More')

        note3 = Note.objects.create(content='The test data. All done.')
        self.assertSearchResultLength(3)
        self.assertSearchResultContains(note3.pk, 'All done')

        note3.content = 'Final test note FOR REAL'
        note3.save()
        self.assertSearchResultLength(3)
        self.assertSearchResultContains(note3.pk, 'FOR REAL')

    def test_delete(self):
        note1 = Note.objects.create(content='Because everyone loves tests.')
        note2 = Note.objects.create(content='More test data.')
        note3 = Note.objects.create(content='The test data. All done.')
        self.assertSearchResultLength(3)
        note1.delete()
        self.assertSearchResultLength(2)
        note2.delete()
        self.assertSearchResultLength(1)
        note3.delete()
        self.assertSearchResultLength(0)

    def test_complex(self):
        note1 = Note.objects.create(content='Because everyone loves test.')
        self.assertSearchResultLength(1)

        Note.objects.create(content='More test data.')
        self.assertSearchResultLength(2)
        note1.delete()
        self.assertSearchResultLength(1)

        note3 = Note.objects.create(content='The test data. All done.')
        self.assertSearchResultLength(2)

        note3.title = 'Final test note FOR REAL'
        note3.save()
        self.assertSearchResultLength(2)

        note3.delete()
        self.assertSearchResultLength(1)

########NEW FILE########
__FILENAME__ = test_settings
import os

DEBUG = True

TEST_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), 'tests'))

INSTALLED_APPS = [
    'haystack',
    'djcelery',
    'celery_haystack',
    'celery_haystack.tests',
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

SECRET_KEY = 'really-not-secret'

BROKER_TRANSPORT = "memory"
CELERY_ALWAYS_EAGER = True
CELERY_IGNORE_RESULT = True
CELERYD_LOG_LEVEL = "DEBUG"
CELERY_DEFAULT_QUEUE = "celery-haystack"

TEST_RUNNER = 'discover_runner.DiscoverRunner'

if os.environ.get('HAYSTACK') == 'v1':
    HAYSTACK_SITECONF = 'celery_haystack.tests.search_sites'
    HAYSTACK_SEARCH_ENGINE = 'whoosh'
    HAYSTACK_WHOOSH_PATH = os.path.join(TEST_ROOT, 'whoosh_index')

elif os.environ.get('HAYSTACK') == 'v2':
    HAYSTACK_CONNECTIONS = {
        'default': {
            'ENGINE': 'haystack.backends.whoosh_backend.WhooshEngine',
            'PATH': os.path.join(TEST_ROOT, 'whoosh_index'),
        }
    }
    HAYSTACK_SIGNAL_PROCESSOR = 'celery_haystack.signals.CelerySignalProcessor'

########NEW FILE########
__FILENAME__ = utils
from django.core.exceptions import ImproperlyConfigured
from django.utils.importlib import import_module

from haystack.utils import get_identifier

from .conf import settings


def get_update_task(task_path=None):
    import_path = task_path or settings.CELERY_HAYSTACK_DEFAULT_TASK
    module, attr = import_path.rsplit('.', 1)
    try:
        mod = import_module(module)
    except ImportError as e:
        raise ImproperlyConfigured('Error importing module %s: "%s"' %
                                   (module, e))
    try:
        Task = getattr(mod, attr)
    except AttributeError:
        raise ImproperlyConfigured('Module "%s" does not define a "%s" '
                                   'class.' % (module, attr))
    return Task


def enqueue_task(action, instance):
    """
    Common utility for enqueing a task for the given action and
    model instance.
    """
    identifier = get_identifier(instance)
    get_update_task().delay(action, identifier)

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# celery-haystack documentation build configuration file, created by
# sphinx-quickstart on Sat Sep 17 14:02:10 2011.
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
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.intersphinx']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'celery-haystack'
copyright = u'2011-2013, Jannis Leidel and contributors'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
try:
    from celery_haystack import __version__
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
htmlhelp_basename = 'celery-haystackdoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'celery-haystack.tex', u'celery-haystack Documentation',
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
    ('index', 'celery-haystack', u'celery-haystack Documentation',
     [u'Jannis Leidel'], 1)
]


# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {
    'python': ('http://docs.python.org/2.7', None),
    'sphinx': ('http://sphinx.pocoo.org/', None),
    'django': ('http://django.readthedocs.org/en/latest/', None),
}

########NEW FILE########
