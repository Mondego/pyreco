__FILENAME__ = base
import time
import logging

from django.core.cache import cache
from django.conf import settings

from cacheback import tasks

logging.basicConfig()
logger = logging.getLogger('cacheback')

MEMCACHE_MAX_EXPIRATION = 2592000


class Job(object):
    """
    A cached read job.

    This is the core class for the package which is intended to be subclassed
    to allow the caching behaviour to be customised.
    """
    # All items are stored in memcache as a tuple (expiry, data).  We don't use
    # the TTL functionality within memcache but implement on own.  If the
    # expiry value is None, this indicates that there is already a job created
    # for refreshing this item.

    #: Default cache lifetime is 5 minutes.  After this time, the result will
    #: be considered stale and requests will trigger a job to refresh it.
    lifetime = 600

    #: Timeout period during which no new Celery tasks will be created for a
    #: single cache item.  This time should cover the normal time required to
    #: refresh the cache.
    refresh_timeout = 60

    #: Time to store items in the cache.  After this time, we will get a cache
    #: miss which can lead to synchronous refreshes if you have
    #: fetch_on_miss=True.
    cache_ttl = MEMCACHE_MAX_EXPIRATION

    #: Whether to perform a synchronous refresh when a result is missing from
    #: the cache.  Default behaviour is to do a synchronous fetch when the cache is empty.
    #: Stale results are generally ok, but not no results.
    fetch_on_miss = True

    #: Whether to perform a synchronous refresh when a result is in the cache
    #: but stale from. Default behaviour is never to do a synchronous fetch but
    #: there will be times when an item is _too_ stale to be returned.
    fetch_on_stale_threshold = None

    #: Overrides options for `refresh_cache.apply_async` (e.g. `queue`).
    task_options = {}

    # --------
    # MAIN API
    # --------

    def get(self, *raw_args, **raw_kwargs):
        """
        Return the data for this function (using the cache if possible).

        This method is not intended to be overidden
        """
        # We pass args and kwargs through a filter to allow them to be
        # converted into values that can be pickled.
        args = self.prepare_args(*raw_args)
        kwargs = self.prepare_kwargs(**raw_kwargs)

        # Build the cache key and attempt to fetch the cached item
        key = self.key(*args, **kwargs)
        item = cache.get(key)

        if item is None:
            # Cache MISS - we can either:
            # a) fetch the data immediately, blocking execution until
            #    the fetch has finished, or
            # b) trigger an async refresh and return an empty result
            if self.should_missing_item_be_fetched_synchronously(*args, **kwargs):
                logger.debug(("Job %s with key '%s' - cache MISS - running "
                              "synchronous refresh"),
                             self.class_path, key)
                return self.refresh(*args, **kwargs)
            else:
                logger.debug(("Job %s with key '%s' - cache MISS - triggering "
                              "async refresh and returning empty result"),
                             self.class_path, key)
                # To avoid cache hammering (ie lots of identical Celery tasks
                # to refresh the same cache item), we reset the cache with an
                # empty result which will be returned until the cache is
                # refreshed.
                empty = self.empty()
                self.cache_set(key, self.timeout(*args, **kwargs), empty)
                self.async_refresh(*args, **kwargs)
                return empty

        expiry, data = item
        delta = time.time() - expiry
        if delta > 0:
            # Cache HIT but STALE expiry - we can either:
            # a) fetch the data immediately, blocking execution until
            #    the fetch has finished, or
            # b) trigger a refresh but allow the stale result to be
            #    returned this time.  This is normally acceptable.
            if self.should_stale_item_be_fetched_synchronously(
                    delta, *args, **kwargs):
                logger.debug(
                    ("Job %s with key '%s' - STALE cache hit - running "
                    "synchronous refresh"),
                    self.class_path, key)
                return self.refresh(*args, **kwargs)
            else:
                logger.debug(
                    ("Job %s with key '%s' - STALE cache hit - triggering "
                    "async refresh and returning stale result"),
                    self.class_path, key)
                # We replace the item in the cache with a 'timeout' expiry - this
                # prevents cache hammering but guards against a 'limbo' situation
                # where the refresh task fails for some reason.
                timeout = self.timeout(*args, **kwargs)
                self.cache_set(key, timeout, data)
                self.async_refresh(*args, **kwargs)
        else:
            logger.debug("Job %s with key '%s' - cache HIT", self.class_path, key)
        return data

    def invalidate(self, *raw_args, **raw_kwargs):
        """
        Mark a cached item invalid and trigger an asynchronous
        job to refresh the cache
        """
        args = self.prepare_args(*raw_args)
        kwargs = self.prepare_kwargs(**raw_kwargs)
        key = self.key(*args, **kwargs)
        item = cache.get(key)
        if item is not None:
            expiry, data = item
            self.cache_set(key, self.timeout(*args, **kwargs), data)
            self.async_refresh(*args, **kwargs)

    def delete(self, *raw_args, **raw_kwargs):
        """
        Remove an item from the cache
        """
        args = self.prepare_args(*raw_args)
        kwargs = self.prepare_kwargs(**raw_kwargs)
        key = self.key(*args, **kwargs)
        item = cache.get(key)
        if item is not None:
            cache.delete(key)

    # --------------
    # HELPER METHODS
    # --------------

    def prepare_args(self, *args):
        return args

    def prepare_kwargs(self, **kwargs):
        return kwargs

    def cache_set(self, key, expiry, data):
        """
        Add a result to the cache

        :key: Cache key to use
        :expiry: The expiry timestamp after which the result is stale
        :data: The data to cache
        """
        cache.set(key, (expiry, data), self.cache_ttl)

        if getattr(settings, 'CACHEBACK_VERIFY_CACHE_WRITE', True):
            # We verify that the item was cached correctly.  This is to avoid a
            # Memcache problem where some values aren't cached correctly
            # without warning.
            __, cached_data = cache.get(key, (None, None))
            if data is not None and cached_data is None:
                raise RuntimeError(
                    "Unable to save data of type %s to cache" % (
                        type(data)))

    def refresh(self, *args, **kwargs):
        """
        Fetch the result SYNCHRONOUSLY and populate the cache
        """
        result = self.fetch(*args, **kwargs)
        self.cache_set(self.key(*args, **kwargs),
                       self.expiry(*args, **kwargs),
                       result)
        return result

    def async_refresh(self, *args, **kwargs):
        """
        Trigger an asynchronous job to refresh the cache
        """
        # We trigger the task with the class path to import as well as the
        # (a) args and kwargs for instantiating the class
        # (b) args and kwargs for calling the 'refresh' method
        try:
            tasks.refresh_cache.apply_async(
                kwargs=dict(
                    klass_str=self.class_path,
                    obj_args=self.get_constructor_args(),
                    obj_kwargs=self.get_constructor_kwargs(),
                    call_args=args,
                    call_kwargs=kwargs
                ),
                **self.task_options
            )
        except Exception, e:
            # Handle exceptions from talking to RabbitMQ - eg connection
            # refused.  When this happens, we try to run the task
            # synchronously.
            logger.error("Unable to trigger task asynchronously - failing "
                         "over to synchronous refresh")
            logger.exception(e)
            try:
                return self.refresh(*args, **kwargs)
            except Exception, e:
                # Something went wrong while running the task
                logger.error("Unable to refresh data synchronously: %s", e)
                logger.exception(e)
            else:
                logger.debug("Failover synchronous refresh completed successfully")

    def get_constructor_args(self):
        return ()

    def get_constructor_kwargs(self):
        """
        Return the kwargs that need to be passed to __init__ when
        reconstructing this class.
        """
        return {}

    @property
    def class_path(self):
        return '%s.%s' % (self.__module__, self.__class__.__name__)

    # Override these methods

    def empty(self):
        """
        Return the appropriate value for a cache MISS (and when we defer the
        repopulation of the cache)
        """
        return None

    def expiry(self, *args, **kwargs):
        """
        Return the expiry timestamp for this item.
        """
        return time.time() + self.lifetime

    def timeout(self, *args, **kwargs):
        """
        Return the refresh timeout for this item
        """
        return time.time() + self.refresh_timeout

    def should_missing_item_be_fetched_synchronously(self, *args, **kwargs):
        """
        Return whether to refresh an item synchronously when it is missing from
        the cache
        """
        return self.fetch_on_miss

    def should_item_be_fetched_synchronously(self, *args, **kwargs):
        import warnings
        warnings.warn(
            "The method 'should_item_be_fetched_synchronously' is deprecated "
            "and will be removed in 0.5.  Use "
            "'should_missing_item_be_fetched_synchronously' instead.",
            DeprecationWarning)
        return self.should_missing_item_be_fetched_synchronously(
            *args, **kwargs)

    def should_stale_item_be_fetched_synchronously(self, delta, *args, **kwargs):
        """
        Return whether to refresh an item synchronously when it is found in the
        cache but stale
        """
        if self.fetch_on_stale_threshold is None:
            return False
        return delta > (self.fetch_on_stale_threshold - self.lifetime)

    def key(self, *args, **kwargs):
        """
        Return the cache key to use.

        If you're passing anything but primitive types to the ``get`` method,
        it's likely that you'll need to override this method.
        """
        if not args and not kwargs:
            return self.class_path
        try:
            if args and not kwargs:
                return "%s:%s" % (self.class_path, hash(args))
            # The line might break if your passed values are un-hashable.  If
            # it does, you need to override this method and implement your own
            # key algorithm.
            return "%s:%s:%s:%s" % (self.class_path,
                                    hash(args),
                                    hash(tuple(kwargs.keys())),
                                    hash(tuple(kwargs.values())))
        except TypeError:
            raise RuntimeError(
                "Unable to generate cache key due to unhashable"
                "args or kwargs - you need to implement your own"
                "key generation method to avoid this problem")

    def fetch(self, *args, **kwargs):
        """
        Return the data for this job - this is where the expensive work should
        be done.
        """
        raise NotImplementedError()

########NEW FILE########
__FILENAME__ = decorators
from functools import wraps

from django.utils.decorators import available_attrs

from cacheback.function import FunctionJob


def cacheback(lifetime=None, fetch_on_miss=None, job_class=None,
              task_options=None):
    """
    Decorate function to cache its return value.

    :lifetime: How long to cache items for
    :fetch_on_miss: Whether to perform a synchronous fetch when no cached
                    result is found
    :job_class: The class to use for running the cache refresh job.  Defaults
                using the FunctionJob.
    """
    if job_class is None:
        job_class = FunctionJob
    job = job_class(lifetime=lifetime, fetch_on_miss=fetch_on_miss,
                    task_options=task_options)

    def _wrapper(fn):
        # using available_attrs to work around http://bugs.python.org/issue3445
        @wraps(fn, assigned=available_attrs(fn))
        def __wrapper(*args, **kwargs):
            return job.get(fn, *args, **kwargs)
        # Assign reference to unwrapped function so that we can access it
        # later without descending into infinite regress.
        __wrapper.fn = fn
        # Assign reference to job so we can use the full Job API
        __wrapper.job = job
        return __wrapper

    return _wrapper

########NEW FILE########
__FILENAME__ = function
from django.utils import importlib

from cacheback.base import Job


class FunctionJob(Job):
    """
    Job for executing a function and caching the result
    """

    def __init__(self, lifetime=None, fetch_on_miss=None, task_options=None):
        if lifetime is not None:
            self.lifetime = int(lifetime)
        if fetch_on_miss is not None:
            self.fetch_on_miss = fetch_on_miss
        if task_options is not None:
            self.task_options = task_options

    def prepare_args(self, fn, *args):
        # Convert function into "module:name" form so that is can be pickled and
        # then re-imported.
        return ("%s:%s" % (fn.__module__, fn.__name__),) + args

    def fetch(self, fn_string, *args, **kwargs):
        # Import function from string representation
        module_path, fn_name = fn_string.split(":")
        module = importlib.import_module(module_path)
        fn = getattr(module, fn_name)
        # Look for 'fn' attribute which is used by the decorator
        if hasattr(fn, 'fn'):
            fn = fn.fn
        return fn(*args, **kwargs)

    def get_constructor_kwargs(self):
        """
        Return the kwargs that need to be passed to __init__ when reconstructing
        this class.
        """
        # We don't need to pass fetch_on_miss as it isn't used by the refresh
        # method.
        return {'lifetime': self.lifetime}

########NEW FILE########
__FILENAME__ = queryset
from cacheback.base import Job


class QuerySetJob(Job):
    """
    Helper class for wrapping ORM reads
    """

    def __init__(self, model, lifetime=None, fetch_on_miss=None):
        """
        :model: The model class to use
        """
        self.model = model
        if lifetime is not None:
            self.lifetime = lifetime
        if fetch_on_miss is not None:
            self.fetch_on_miss = fetch_on_miss

    def key(self, *args, **kwargs):
        return "%s-%s" % (
            self.model.__name__,
            super(QuerySetJob, self).key(*args, **kwargs)
        )

    def get_constructor_kwargs(self):
        return {'model': self.model,
                'lifetime': self.lifetime}


class QuerySetGetJob(QuerySetJob):
    """
    For ORM reads that use the ``get`` method.
    """
    def fetch(self, *args, **kwargs):
        return self.model.objects.get(**kwargs)


class QuerySetFilterJob(QuerySetJob):
    """
    For ORM reads that use the ``filter`` method.
    """
    def fetch(self, *args, **kwargs):
        return self.model.objects.filter(**kwargs)

########NEW FILE########
__FILENAME__ = tasks
import time

from celery.task import task
from celery.utils.log import get_task_logger
from django.utils import importlib


logger = get_task_logger(__name__)


@task()
def refresh_cache(klass_str, obj_args, obj_kwargs, call_args, call_kwargs):
    """
    Re-populate cache using the given job class.

    The job class is instantiated with the passed constructor args and the
    refresh method is called with the passed call args.  That is::

        data = klass(*obj_args, **obj_kwargs).refresh(
            *call_args, **call_kwargs)

    :klass_str: String repr of class (eg 'apps.twitter.jobs:FetchTweetsJob')
    :obj_args: Constructor args
    :obj_kwargs: Constructor kwargs
    :call_args: Refresh args
    :call_kwargs: Refresh kwargs
    """
    klass = _get_job_class(klass_str)
    if klass is None:
        logger.error("Unable to construct %s with args %r and kwargs %r",
                     klass_str, obj_args, obj_kwargs)
        return

    logger.info("Using %s with constructor args %r and kwargs %r",
                klass_str, obj_args, obj_kwargs)
    logger.info("Calling refresh with args %r and kwargs %r", call_args,
                call_kwargs)
    start = time.time()
    try:
        klass(*obj_args, **obj_kwargs).refresh(
            *call_args, **call_kwargs)
    except Exception, e:
        logger.error("Error running job: '%s'", e)
        logger.exception(e)
    else:
        duration = time.time() - start
        logger.info("Refreshed cache in %.6f seconds", duration)


def _get_job_class(klass_str):
    """
    Return the job class
    """
    mod_name, klass_name = klass_str.rsplit('.', 1)
    try:
        mod = importlib.import_module(mod_name)
    except ImportError, e:
        logger.error("Error importing job module %s: '%s'", mod_name, e)
        return
    try:
        klass = getattr(mod, klass_name)
    except AttributeError:
        logger.error("Module '%s' does not define a '%s' class", mod_name,
                     klass_name)
        return
    return klass

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# django-async-cache documentation build configuration file, created by
# sphinx-quickstart on Mon Jul 30 21:40:46 2012.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os
code_dir = os.path.realpath(
    os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(code_dir)

from django.conf import settings
if not settings.configured:
    settings.configure(
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                }
            },
    )

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
project = u'django-async-cache'
copyright = u'2012, David Winterbottom'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
import cacheback
version = cacheback.__version__
# The full version, including alpha/beta/rc tags.
release = cacheback.__version__

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
htmlhelp_basename = 'django-async-cachedoc'


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
  ('index', 'django-async-cache.tex', u'django-async-cache Documentation',
   u'David Winterbottom', 'manual'),
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
    ('index', 'django-async-cache', u'django-async-cache Documentation',
     [u'David Winterbottom'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'django-async-cache', u'django-async-cache Documentation',
   u'David Winterbottom', 'django-async-cache', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

########NEW FILE########
__FILENAME__ = runtests
#!/usr/bin/env python
import sys
from optparse import OptionParser

from django.conf import settings

if not settings.configured:
    settings.configure(
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
            }
        },
        CACHES={
            'default': {
                'BACKEND':
                'django.core.cache.backends.locmem.LocMemCache',
                'LOCATION': 'unique-snowflake'
            }
        },
        INSTALLED_APPS=[
            'django.contrib.auth',
            'django.contrib.admin',
            'django.contrib.contenttypes',
            'django.contrib.sessions',
            'django.contrib.sites',
            'django.contrib.flatpages',
            'cacheback',
            'djcelery',
            'tests.dummyapp',
            ],
        BROKER_URL = 'django://',
        CELERY_ALWAYS_EAGER=True,
        NOSE_ARGS=['-s', '--with-spec'],
    )
    import djcelery
    djcelery.setup_loader()

from django_nose import NoseTestSuiteRunner


def run_tests(*test_args):
    if not test_args:
        test_args = ['tests']

    test_runner = NoseTestSuiteRunner(verbosity=1)
    num_failures = test_runner.run_tests(test_args)
    if num_failures > 0:
        sys.exit(num_failures)


if __name__ == '__main__':
    parser = OptionParser()
    (options, args) = parser.parse_args()
    run_tests(*args)

########NEW FILE########
__FILENAME__ = jobs
from cacheback.base import Job

from dummyapp import models


class VanillaJob(Job):
    fetch_on_miss = False
    refresh_timeout = 5

    def fetch(self):
        import time
        time.sleep(10)
        return models.DummyModel.objects.all()


class KeyedJob(Job):
    lifetime = 5
    fetch_on_stale_threshold = 10

    def key(self, name):
        return name

    def fetch(self, name):
        return models.DummyModel.objects.filter(name=name)

########NEW FILE########
__FILENAME__ = models
from django.db import models


class DummyModel(models.Model):
    name = models.CharField(max_length=100)
    date_created = models.DateTimeField(auto_now_add=True)

    def __unicode__(self):
        return self.name
########NEW FILE########
__FILENAME__ = views
from django.shortcuts import render

from cacheback.queryset import QuerySetFilterJob
from cacheback.function import FunctionJob
from cacheback.decorators import cacheback

from dummyapp import jobs
from dummyapp import models


def fetch():
    return models.DummyModel.objects.filter(name__contains='1')


def fetch_with_arg(q):
    return models.DummyModel.objects.filter(name__contains=q)


@cacheback(5)
def decorated(q):
    return models.DummyModel.objects.filter(name__contains=q)


def index(request):
    if 'name' in request.GET:
        name = request.GET['name']
        if 'qs' in request.GET:
            items = QuerySetFilterJob(models.DummyModel, 10, False).get(
                name=name)
        else:
            items = jobs.KeyedJob().get(name=request.GET['name'])
    elif 'function' in request.GET:
        job = FunctionJob()
        job.fetch_on_miss = False
        if 'q' in request.GET:
            items = job.get(fetch_with_arg, request.GET['q'])
        else:
            items = job.get(fetch)
    elif 'decorator' in request.GET:
        items = decorated('3')
    else:
        items = jobs.VanillaJob().get()
    return render(request, 'index.html', {'items': items})

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = models
from django.db import models


class DummyModel(models.Model):
    name = models.CharField(max_length=100)
    date_created = models.DateTimeField(auto_now_add=True)
########NEW FILE########
__FILENAME__ = settings
DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': '/vagrant/sandbox/db.sqlite3',                      # Or path to database file if using sqlite3.
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
SECRET_KEY = 'a5my98-t4si@aoegk1tm4!3w3&amp;vmsehkpez+5xp@b0kvk42t#b'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'debug_toolbar.middleware.DebugToolbarMiddleware',
)

ROOT_URLCONF = 'urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'wsgi.application'

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
    'dummyapp',
    'cacheback',
    'debug_toolbar',
    'djcelery',
)

INTERNAL_IPS = ('10.0.2.2',)

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
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
        'cacheback': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    }
}

# CACHEBACK SETTINGS

import djcelery
djcelery.setup_loader()
BROKER_URL = 'amqp://cb_rabbit_user:somepasswordhere@localhost/'

# This doesn't seem to work.  If you stop rabbit and attempt to connect, it
# takes 60 seconds even though this value is correctly passed to the socked.
BROKER_CONNECTION_TIMEOUT = 5

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': '127.0.0.1:11211',
    }
}

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url

urlpatterns = patterns('',
    url(r'^$', 'dummyapp.views.index', name='index'),
)

########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for sandbox project.

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

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")

# This application object is used by any WSGI server configured to use this
# file. This includes Django's development server, if the WSGI_APPLICATION
# setting points here.
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

# Apply WSGI middleware here.
# from helloworld.wsgi import HelloWorldApplication
# application = HelloWorldApplication(application)

########NEW FILE########
__FILENAME__ = async_tests
import time

from django.core.cache import cache
from django.test import TestCase
from django.test.utils import override_settings
import mock

from cacheback.base import Job


class StaleSyncJob(Job):
    # Cache items for 5 seconds.
    # -> trigger an async refresh if item is 5 < x < 10 seconds old
    # -> trigger a sync refresh if item is x > 10 seconds old
    lifetime = 5
    fetch_on_stale_threshold = 10

    def __init__(self):
        self.called_async = False

    def fetch(self):
        return 'testing'

    def async_refresh(self, *args, **kwargs):
        self.called_async = True
        super(StaleSyncJob, self).async_refresh(*args, **kwargs)


@override_settings(CELERY_ALWAYS_EAGER=False)
class TestJobWithStaleSyncRefreshAttributeSet(TestCase):

    def setUp(self):
        self.job = StaleSyncJob()
        # Populate cache
        self.cache_time = time.time()
        self.job.refresh()

    def tearDown(self):
        cache.clear()

    def test_hits_cache_within_cache_lifetime(self):
        self.assertEqual('testing', self.job.get())
        self.assertFalse(self.job.called_async)

    def test_triggers_async_refresh_after_lifetime_but_before_stale_threshold(self):
        with mock.patch('time.time') as mocktime:
            mocktime.return_value = self.cache_time + 7
            self.assertEqual('testing', self.job.get())
            self.assertTrue(self.job.called_async)

    def test_triggers_sync_refresh_after_stale_threshold(self):
        with mock.patch('time.time') as mocktime:
            mocktime.return_value = self.cache_time + 12
            self.assertEqual('testing', self.job.get())
            self.assertFalse(self.job.called_async)

########NEW FILE########
__FILENAME__ = decorator_tests
from django.test import TestCase

from cacheback.function import FunctionJob


def fetch():
    return 1, 2, 3


def fetch_with_args(*args):
    return args


class TestDecorator(TestCase):

    def setUp(self):
        self.job = FunctionJob(fetch_on_miss=False)

    def test_wrapping_argless_function(self):
        self.assertIsNone(self.job.get(fetch))
        self.assertEqual((1, 2, 3), self.job.get(fetch))

    def test_wrapping_function(self):
        self.assertIsNone(self.job.get(fetch_with_args, 'testing'))
        self.assertEqual(('testing',),
                         self.job.get(fetch_with_args, 'testing'))


class TestUsingConstructorArgs(TestCase):

    def test_passing_lifetime(self):
        job = FunctionJob(300)
        self.assertEqual(300, job.lifetime)

########NEW FILE########
__FILENAME__ = models
from django.db import models


class DummyModel(models.Model):
    name = models.CharField(max_length=100)
    date_created = models.DateTimeField(auto_now_add=True)
########NEW FILE########
__FILENAME__ = job_tests
from django.test import TestCase
from django.test.utils import override_settings
from django.core.cache import cache
from django.core.cache.backends.dummy import DummyCache

import cacheback.base
from cacheback.base import Job


class NoArgsJob(Job):
    def fetch(self):
        return 1, 2, 3


class TestDefaultJobCalledWithNoArgs(TestCase):

    def setUp(self):
        self.job = NoArgsJob()

    def tearDown(self):
        cache.clear()

    def test_returns_result_on_first_call(self):
        self.assertEqual((1, 2, 3), self.job.get())


class NoArgsUseEmptyJob(NoArgsJob):
    fetch_on_miss = False


class TestJobWithFetchOnMissCalledWithNoArgs(TestCase):
    """Test job with fetch_on_miss=False called with no args"""

    def setUp(self):
        self.job = NoArgsUseEmptyJob()

    def tearDown(self):
        cache.clear()

    def test_returns_none_on_first_call(self):
        self.assertIsNone(self.job.get())

    def test_returns_result_on_second_call(self):
        self.assertIsNone(self.job.get())
        self.assertEqual((1, 2, 3), self.job.get())


class SingleArgJob(Job):

    def fetch(self, name):
        return name.upper()


class AnotherSingleArgJob(Job):

    def fetch(self, name):
        return '%s!' % name.upper()


class TestSingleArgJob(TestCase):

    def setUp(self):
        self.job = SingleArgJob()

    def tearDown(self):
        cache.clear()

    def test_returns_correct_result(self):
        self.assertEqual('ALAN', self.job.get('alan'))
        self.assertEqual('BARRY', self.job.get('barry'))

    def test_jobs_with_duplicate_args_dont_clash_on_cache_key(self):
        another_job = AnotherSingleArgJob()
        self.assertEqual('ALAN', self.job.get('alan'))
        self.assertEqual('ALAN!', another_job.get('alan'))


class IntegerJob(Job):

    def fetch(self, obj):
        return 1


class TestNonIterableCacheItem(TestCase):

    def setUp(self):
        self.job = IntegerJob()
        self.job.fetch_on_miss = False

    def tearDown(self):
        cache.clear()

    def test_returns_correct_result(self):
        self.assertIsNone(self.job.get(None))
        self.assertEqual(1, self.job.get(None))


class TestDummyCache(TestCase):

    def setUp(self):
        # Monkey-patch in the dummy cache
        self.cache = cache
        cacheback.base.cache = DummyCache('unique-snowflake', {})
        self.job = SingleArgJob()

    def tearDown(self):
        cacheback.base.cache  = self.cache

    @override_settings(CACHEBACK_VERIFY_CACHE_WRITE=False)
    def test_dummy_cache_does_not_raise_error(self):
        self.assertEqual('ALAN', self.job.get('alan'))
        self.assertEqual('BARRY', self.job.get('barry'))

########NEW FILE########
__FILENAME__ = queryset_tests
from django.test import TestCase
from django.core.cache import cache

from cacheback.base import Job
from cacheback.queryset import QuerySetFilterJob, QuerySetGetJob
from tests.dummyapp import models


class ManualQuerySetJob(Job):

    def fetch(self, name):
        return models.DummyModel.objects.filter(name=name)


class TestManualQuerySetJob(TestCase):

    def setUp(self):
        self.job = ManualQuerySetJob()
        models.DummyModel.objects.create(name="Alan")
        models.DummyModel.objects.create(name="Barry")

    def tearDown(self):
        models.DummyModel.objects.all().delete()
        cache.clear()

    def test_returns_result_on_first_call(self):
        results = self.job.get('Alan')
        self.assertEqual(1, len(results))

    def test_makes_only_one_database_query(self):
        with self.assertNumQueries(1):
            for _ in xrange(10):
                self.job.get('Alan')


class TestFilterQuerySetJob(TestCase):

    def setUp(self):
        self.job = QuerySetFilterJob(models.DummyModel)
        models.DummyModel.objects.create(name="Alan")
        models.DummyModel.objects.create(name="Barry")

    def tearDown(self):
        models.DummyModel.objects.all().delete()
        cache.clear()

    def test_returns_result_on_first_call(self):
        results = self.job.get(name='Alan')
        self.assertEqual(1, len(results))


class TestGetQuerySetJob(TestCase):

    def setUp(self):
        self.job = QuerySetGetJob(models.DummyModel)
        models.DummyModel.objects.create(name="Alan")
        models.DummyModel.objects.create(name="Barry")

    def tearDown(self):
        models.DummyModel.objects.all().delete()
        cache.clear()

    def test_returns_result_on_first_call(self):
        result = self.job.get(name='Alan')
        self.assertEqual('Alan', result.name)


class EchoJob(Job):
    def fetch(self, *args, **kwargs):
        return (args, kwargs)


class TestEdgeCases(TestCase):

    def setUp(self):
        self.job = EchoJob()

    def tearDown(self):
        cache.clear()

    def test_unhashable_arg_raises_exception(self):
        with self.assertRaises(RuntimeError):
            self.job.get({})

    def test_unhashable_kwarg_raises_exception(self):
        with self.assertRaises(RuntimeError):
            self.job.get(name={})

########NEW FILE########
