__FILENAME__ = bench_disabled_introspection
"""Tests with frame introspection disabled"""
from logbook import Logger, NullHandler, Flags


log = Logger('Test logger')


class DummyHandler(NullHandler):
    blackhole = False


def run():
    with Flags(introspection=False):
        with DummyHandler() as handler:
            for x in xrange(500):
                log.warning('this is not handled')

########NEW FILE########
__FILENAME__ = bench_disabled_logger
"""Tests with the whole logger disabled"""
from logbook import Logger


log = Logger('Test logger')
log.disabled = True


def run():
    for x in xrange(500):
        log.warning('this is not handled')

########NEW FILE########
__FILENAME__ = bench_enabled_introspection
"""Tests with stack frame introspection enabled"""
from logbook import Logger, NullHandler, Flags


log = Logger('Test logger')


class DummyHandler(NullHandler):
    blackhole = False


def run():
    with Flags(introspection=True):
        with DummyHandler() as handler:
            for x in xrange(500):
                log.warning('this is not handled')

########NEW FILE########
__FILENAME__ = bench_file_handler
"""Benchmarks the file handler"""
from logbook import Logger, FileHandler
from tempfile import NamedTemporaryFile


log = Logger('Test logger')


def run():
    f = NamedTemporaryFile()
    with FileHandler(f.name) as handler:
        for x in xrange(500):
            log.warning('this is handled')

########NEW FILE########
__FILENAME__ = bench_file_handler_unicode
"""Benchmarks the file handler with unicode"""
from logbook import Logger, FileHandler
from tempfile import NamedTemporaryFile


log = Logger('Test logger')


def run():
    f = NamedTemporaryFile()
    with FileHandler(f.name) as handler:
        for x in xrange(500):
            log.warning(u'this is handled \x6f')

########NEW FILE########
__FILENAME__ = bench_logger_creation
"""Test with no handler active"""
from logbook import Logger


def run():
    for x in xrange(500):
        Logger('Test')

########NEW FILE########
__FILENAME__ = bench_logger_level_low
"""Benchmarks too low logger levels"""
from logbook import Logger, StreamHandler, ERROR
from cStringIO import StringIO


log = Logger('Test logger')
log.level = ERROR


def run():
    out = StringIO()
    with StreamHandler(out):
        for x in xrange(500):
            log.warning('this is not handled')

########NEW FILE########
__FILENAME__ = bench_logging_file_handler
"""Tests logging file handler in comparison"""
from logging import getLogger, FileHandler
from tempfile import NamedTemporaryFile


log = getLogger('Testlogger')


def run():
    f = NamedTemporaryFile()
    handler = FileHandler(f.name)
    log.addHandler(handler)
    for x in xrange(500):
        log.warning('this is handled')

########NEW FILE########
__FILENAME__ = bench_logging_file_handler_unicode
"""Tests logging file handler in comparison"""
from logging import getLogger, FileHandler
from tempfile import NamedTemporaryFile


log = getLogger('Testlogger')


def run():
    f = NamedTemporaryFile()
    handler = FileHandler(f.name)
    log.addHandler(handler)
    for x in xrange(500):
        log.warning(u'this is handled \x6f')

########NEW FILE########
__FILENAME__ = bench_logging_logger_creation
"""Test with no handler active"""
from logging import getLogger


root_logger = getLogger()


def run():
    for x in xrange(500):
        getLogger('Test')
        del root_logger.manager.loggerDict['Test']

########NEW FILE########
__FILENAME__ = bench_logging_logger_level_low
"""Tests with a logging handler becoming a noop for comparison"""
from logging import getLogger, StreamHandler, ERROR
from cStringIO import StringIO


log = getLogger('Testlogger')
log.setLevel(ERROR)


def run():
    out = StringIO()
    handler = StreamHandler(out)
    log.addHandler(handler)
    for x in xrange(500):
        log.warning('this is not handled')

########NEW FILE########
__FILENAME__ = bench_logging_noop
"""Tests with a logging handler becoming a noop for comparison"""
from logging import getLogger, StreamHandler, ERROR
from cStringIO import StringIO


log = getLogger('Testlogger')


def run():
    out = StringIO()
    handler = StreamHandler(out)
    handler.setLevel(ERROR)
    log.addHandler(handler)
    for x in xrange(500):
        log.warning('this is not handled')

########NEW FILE########
__FILENAME__ = bench_logging_noop_filter
"""Tests with a filter disabling a handler for comparsion in logging"""
from logging import getLogger, StreamHandler, Filter
from cStringIO import StringIO


log = getLogger('Testlogger')


class DisableFilter(Filter):
    def filter(self, record):
        return False


def run():
    out = StringIO()
    handler = StreamHandler(out)
    handler.addFilter(DisableFilter())
    log.addHandler(handler)
    for x in xrange(500):
        log.warning('this is not handled')

########NEW FILE########
__FILENAME__ = bench_logging_stream_handler
"""Tests the stream handler in logging"""
from logging import Logger, StreamHandler
from cStringIO import StringIO


log = Logger('Test logger')


def run():
    out = StringIO()
    log.addHandler(StreamHandler(out))
    for x in xrange(500):
        log.warning('this is not handled')
    assert out.getvalue().count('\n') == 500

########NEW FILE########
__FILENAME__ = bench_noop
"""Test with no handler active"""
from logbook import Logger, StreamHandler, NullHandler, ERROR
from cStringIO import StringIO


log = Logger('Test logger')


def run():
    out = StringIO()
    with NullHandler():
        with StreamHandler(out, level=ERROR) as handler:
            for x in xrange(500):
                log.warning('this is not handled')
    assert not out.getvalue()

########NEW FILE########
__FILENAME__ = bench_noop_filter
from logbook import Logger, StreamHandler, NullHandler
from cStringIO import StringIO


log = Logger('Test logger')


def run():
    out = StringIO()
    with NullHandler():
        with StreamHandler(out, filter=lambda r, h: False) as handler:
            for x in xrange(500):
                log.warning('this is not handled')
    assert not out.getvalue()

########NEW FILE########
__FILENAME__ = bench_noop_filter_on_handler
"""Like the filter test, but with the should_handle implemented"""
from logbook import Logger, StreamHandler, NullHandler
from cStringIO import StringIO


log = Logger('Test logger')


class CustomStreamHandler(StreamHandler):
    def should_handle(self, record):
        return False


def run():
    out = StringIO()
    with NullHandler():
        with CustomStreamHandler(out) as handler:
            for x in xrange(500):
                log.warning('this is not handled')
    assert not out.getvalue()

########NEW FILE########
__FILENAME__ = bench_redirect_from_logging
"""Tests redirects from logging to logbook"""
from logging import getLogger
from logbook import StreamHandler
from logbook.compat import redirect_logging
from cStringIO import StringIO


redirect_logging()
log = getLogger('Test logger')


def run():
    out = StringIO()
    with StreamHandler(out):
        for x in xrange(500):
            log.warning('this is not handled')
    assert out.getvalue().count('\n') == 500

########NEW FILE########
__FILENAME__ = bench_redirect_to_logging
"""Tests redirects from logging to logbook"""
from logging import getLogger, StreamHandler
from logbook.compat import LoggingHandler
from cStringIO import StringIO


log = getLogger('Test logger')


def run():
    out = StringIO()
    log.addHandler(StreamHandler(out))
    with LoggingHandler():
        for x in xrange(500):
            log.warning('this is not handled')
    assert out.getvalue().count('\n') == 500

########NEW FILE########
__FILENAME__ = bench_stack_manipulation
"""Tests basic stack manipulation performance"""
from logbook import Handler, NullHandler, StreamHandler, FileHandler, \
     ERROR, WARNING
from tempfile import NamedTemporaryFile
from cStringIO import StringIO


def run():
    f = NamedTemporaryFile()
    out = StringIO()
    with NullHandler():
        with StreamHandler(out, level=WARNING):
            with FileHandler(f.name, level=ERROR):
                for x in xrange(100):
                    list(Handler.stack_manager.iter_context_objects())

########NEW FILE########
__FILENAME__ = bench_stream_handler
"""Tests the stream handler"""
from logbook import Logger, StreamHandler
from cStringIO import StringIO


log = Logger('Test logger')


def run():
    out = StringIO()
    with StreamHandler(out) as handler:
        for x in xrange(500):
            log.warning('this is not handled')
    assert out.getvalue().count('\n') == 500

########NEW FILE########
__FILENAME__ = bench_test_handler
"""Tests the test handler"""
from logbook import Logger, TestHandler


log = Logger('Test logger')


def run():
    with TestHandler() as handler:
        for x in xrange(500):
            log.warning('this is not handled')

########NEW FILE########
__FILENAME__ = run
#!/usr/bin/env python
"""
    Runs the benchmarks
"""
import sys
import os
import re
from subprocess import Popen

try:
    from pkg_resources import get_distribution
    version = get_distribution('Logbook').version
except Exception:
    version = 'unknown version'


_filename_re = re.compile(r'^bench_(.*?)\.py$')
bench_directory = os.path.abspath(os.path.dirname(__file__))


def list_benchmarks():
    result = []
    for name in os.listdir(bench_directory):
        match = _filename_re.match(name)
        if match is not None:
            result.append(match.group(1))
    result.sort(key=lambda x: (x.startswith('logging_'), x.lower()))
    return result


def run_bench(name):
    sys.stdout.write('%-32s' % name)
    sys.stdout.flush()
    Popen([sys.executable, '-mtimeit', '-s',
           'from bench_%s import run' % name,
           'run()']).wait()


def main():
    print '=' * 80
    print 'Running benchmark with Logbook %s' % version
    print '-' * 80
    os.chdir(bench_directory)
    for bench in list_benchmarks():
        run_bench(bench)
    print '-' * 80


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Logbook documentation build configuration file, created by
# sphinx-quickstart on Fri Jul 23 16:54:49 2010.
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
sys.path.extend((os.path.abspath('.'), os.path.abspath('..')))

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
project = u'Logbook'
copyright = u'2010, Armin Ronacher, Georg Brandl'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.7.1-dev'
# The full version, including alpha/beta/rc tags.
release = '0.7.1-dev'

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
html_theme = 'sheet'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
html_theme_options = {
    'nosidebar': True,
}

# Add any paths that contain custom themes here, relative to this directory.
html_theme_path = ['.']

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
html_title = "Logbook"

# A shorter title for the navigation bar.  Default is the same as html_title.
html_short_title = "Logbook " + release

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
#html_static_path = ['_static']

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

html_add_permalinks = False

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# If nonempty, this is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = ''

# Output file base name for HTML help builder.
htmlhelp_basename = 'Logbookdoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'Logbook.tex', u'Logbook Documentation',
   u'Armin Ronacher, Georg Brandl', 'manual'),
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
    ('index', 'logbook', u'Logbook Documentation',
     [u'Armin Ronacher, Georg Brandl'], 1)
]

intersphinx_mapping = {
    'http://docs.python.org': None
}

########NEW FILE########
__FILENAME__ = base
# -*- coding: utf-8 -*-
"""
    logbook.base
    ~~~~~~~~~~~~

    Base implementation for logbook.

    :copyright: (c) 2010 by Armin Ronacher, Georg Brandl.
    :license: BSD, see LICENSE for more details.
"""
import os
import sys
try:
    import thread
except ImportError:
    # for python 3.1,3.2
    import _thread as thread
import threading
import traceback
from itertools import chain
from weakref import ref as weakref
from datetime import datetime

from logbook.helpers import to_safe_json, parse_iso8601, cached_property, \
     PY2, u, string_types, iteritems, integer_types
try:
    from logbook._speedups import group_reflected_property, \
         ContextStackManager, StackedObject
except ImportError:
    from logbook._fallback import group_reflected_property, \
         ContextStackManager, StackedObject

_datetime_factory = datetime.utcnow
def set_datetime_format(datetime_format):
    """
    Set the format for the datetime objects created, which are then
    made available as the :py:attr:`LogRecord.time` attribute of
    :py:class:`LogRecord` instances.

    :param datetime_format: Indicates how to generate datetime objects.  Possible values are:

         "utc"
             :py:attr:`LogRecord.time` will be a datetime in UTC time zone (but not time zone aware)
         "local"
             :py:attr:`LogRecord.time` will be a datetime in local time zone (but not time zone aware)

    This function defaults to creating datetime objects in UTC time,
    using `datetime.utcnow()
    <http://docs.python.org/3/library/datetime.html#datetime.datetime.utcnow>`_,
    so that logbook logs all times in UTC time by default.  This is
    recommended in case you have multiple software modules or
    instances running in different servers in different time zones, as
    it makes it simple and less error prone to correlate logging
    across the different servers.

    On the other hand if all your software modules are running in the
    same time zone and you have to correlate logging with third party
    modules already logging in local time, it can be more convenient
    to have logbook logging to local time instead of UTC.  Local time
    logging can be enabled like this::

       import logbook
       from datetime import datetime
       logbook.set_datetime_format("local")

    """
    global _datetime_factory
    if datetime_format == "utc":
        _datetime_factory = datetime.utcnow
    elif datetime_format == "local":
        _datetime_factory = datetime.now
    else:
        raise ValueError("Invalid value %r.  Valid values are 'utc' and 'local'." % (datetime_format,))

# make sure to sync these up with _speedups.pyx
CRITICAL = 6
ERROR = 5
WARNING = 4
NOTICE = 3
INFO = 2
DEBUG = 1
NOTSET = 0

_level_names = {
    CRITICAL:   'CRITICAL',
    ERROR:      'ERROR',
    WARNING:    'WARNING',
    NOTICE:     'NOTICE',
    INFO:       'INFO',
    DEBUG:      'DEBUG',
    NOTSET:     'NOTSET'
}
_reverse_level_names = dict((v, k) for (k, v) in iteritems(_level_names))
_missing = object()


# on python 3 we can savely assume that frame filenames will be in
# unicode, on Python 2 we have to apply a trick.
if PY2:
    def _convert_frame_filename(fn):
        if isinstance(fn, unicode):
            fn = fn.decode(sys.getfilesystemencoding() or 'utf-8',
                           'replace')
        return fn
else:
    def _convert_frame_filename(fn):
        return fn


def level_name_property():
    """Returns a property that reflects the level as name from
    the internal level attribute.
    """

    def _get_level_name(self):
        return get_level_name(self.level)

    def _set_level_name(self, level):
        self.level = lookup_level(level)
    return property(_get_level_name, _set_level_name,
                    doc='The level as unicode string')


def lookup_level(level):
    """Return the integer representation of a logging level."""
    if isinstance(level, integer_types):
        return level
    try:
        return _reverse_level_names[level]
    except KeyError:
        raise LookupError('unknown level name %s' % level)


def get_level_name(level):
    """Return the textual representation of logging level 'level'."""
    try:
        return _level_names[level]
    except KeyError:
        raise LookupError('unknown level')


class ExtraDict(dict):
    """A dictionary which returns ``u''`` on missing keys."""

    if sys.version_info[:2] < (2, 5):
        def __getitem__(self, key):
            try:
                return dict.__getitem__(self, key)
            except KeyError:
                return u('')
    else:
        def __missing__(self, key):
            return u('')

    def copy(self):
        return self.__class__(self)

    def __repr__(self):
        return '%s(%s)' % (
            self.__class__.__name__,
            dict.__repr__(self)
        )


class _ExceptionCatcher(object):
    """Helper for exception caught blocks."""

    def __init__(self, logger, args, kwargs):
        self.logger = logger
        self.args = args
        self.kwargs = kwargs

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        if exc_type is not None:
            kwargs = self.kwargs.copy()
            kwargs['exc_info'] = (exc_type, exc_value, tb)
            self.logger.exception(*self.args, **kwargs)
        return True


class ContextObject(StackedObject):
    """An object that can be bound to a context.  It is managed by the
    :class:`ContextStackManager`"""

    #: subclasses have to instanciate a :class:`ContextStackManager`
    #: object on this attribute which is then shared for all the
    #: subclasses of it.
    stack_manager = None

    def push_thread(self):
        """Pushes the context object to the thread stack."""
        self.stack_manager.push_thread(self)

    def pop_thread(self):
        """Pops the context object from the stack."""
        popped = self.stack_manager.pop_thread()
        assert popped is self, 'popped unexpected object'

    def push_application(self):
        """Pushes the context object to the application stack."""
        self.stack_manager.push_application(self)

    def pop_application(self):
        """Pops the context object from the stack."""
        popped = self.stack_manager.pop_application()
        assert popped is self, 'popped unexpected object'


class NestedSetup(StackedObject):
    """A nested setup can be used to configure multiple handlers
    and processors at once.
    """

    def __init__(self, objects=None):
        self.objects = list(objects or ())

    def push_application(self):
        for obj in self.objects:
            obj.push_application()

    def pop_application(self):
        for obj in reversed(self.objects):
            obj.pop_application()

    def push_thread(self):
        for obj in self.objects:
            obj.push_thread()

    def pop_thread(self):
        for obj in reversed(self.objects):
            obj.pop_thread()


class Processor(ContextObject):
    """Can be pushed to a stack to inject additional information into
    a log record as necessary::

        def inject_ip(record):
            record.extra['ip'] = '127.0.0.1'

        with Processor(inject_ip):
            ...
    """

    stack_manager = ContextStackManager()

    def __init__(self, callback=None):
        #: the callback that was passed to the constructor
        self.callback = callback

    def process(self, record):
        """Called with the log record that should be overridden.  The default
        implementation calls :attr:`callback` if it is not `None`.
        """
        if self.callback is not None:
            self.callback(record)


class _InheritedType(object):
    __slots__ = ()

    def __repr__(self):
        return 'Inherit'

    def __reduce__(self):
        return 'Inherit'
Inherit = _InheritedType()


class Flags(ContextObject):
    """Allows flags to be pushed on a flag stack.  Currently two flags
    are available:

    `errors`
        Can be set to override the current error behaviour.  This value is
        used when logging calls fail.  The default behaviour is spitting
        out the stacktrace to stderr but this can be overridden:

        =================== ==========================================
        ``'silent'``        fail silently
        ``'raise'``         raise a catchable exception
        ``'print'``         print the stacktrace to stderr (default)
        =================== ==========================================

    `introspection`
        Can be used to disable frame introspection.  This can give a
        speedup on production systems if you are using a JIT compiled
        Python interpreter such as pypy.  The default is `True`.

        Note that the default setup of some of the handler (mail for
        instance) includes frame dependent information which will
        not be available when introspection is disabled.

    Example usage::

        with Flags(errors='silent'):
            ...
    """
    stack_manager = ContextStackManager()

    def __init__(self, **flags):
        self.__dict__.update(flags)

    @staticmethod
    def get_flag(flag, default=None):
        """Looks up the current value of a specific flag."""
        for flags in Flags.stack_manager.iter_context_objects():
            val = getattr(flags, flag, Inherit)
            if val is not Inherit:
                return val
        return default


def _create_log_record(cls, dict):
    """Extra function for reduce because on Python 3 unbound methods
    can no longer be pickled.
    """
    return cls.from_dict(dict)


class LogRecord(object):
    """A LogRecord instance represents an event being logged.

    LogRecord instances are created every time something is logged. They
    contain all the information pertinent to the event being logged. The
    main information passed in is in msg and args
    """
    _pullable_information = frozenset((
        'func_name', 'module', 'filename', 'lineno', 'process_name', 'thread',
        'thread_name', 'formatted_exception', 'message', 'exception_name',
        'exception_message'
    ))
    _noned_on_close = frozenset(('exc_info', 'frame', 'calling_frame'))

    #: can be overriden by a handler to not close the record.  This could
    #: lead to memory leaks so it should be used carefully.
    keep_open = False

    #: the time of the log record creation as :class:`datetime.datetime`
    #: object.  This information is unavailable until the record was
    #: heavy initialized.
    time = None

    #: a flag that is `True` if the log record is heavy initialized which
    #: is not the case by default.
    heavy_initialized = False

    #: a flag that is `True` when heavy initialization is no longer possible
    late = False

    #: a flag that is `True` when all the information was pulled from the
    #: information that becomes unavailable on close.
    information_pulled = False

    def __init__(self, channel, level, msg, args=None, kwargs=None,
                 exc_info=None, extra=None, frame=None, dispatcher=None):
        #: the name of the logger that created it or any other textual
        #: channel description.  This is a descriptive name and can be
        #: used for filtering.
        self.channel = channel
        #: The message of the log record as new-style format string.
        self.msg = msg
        #: the positional arguments for the format string.
        self.args = args or ()
        #: the keyword arguments for the format string.
        self.kwargs = kwargs or {}
        #: the level of the log record as integer.
        self.level = level
        #: optional exception information.  If set, this is a tuple in the
        #: form ``(exc_type, exc_value, tb)`` as returned by
        #: :func:`sys.exc_info`.
        #: This parameter can also be ``True``, which would cause the exception info tuple
        #: to be fetched for you.
        self.exc_info = exc_info
        #: optional extra information as dictionary.  This is the place
        #: where custom log processors can attach custom context sensitive
        #: data.
        self.extra = ExtraDict(extra or ())
        #: If available, optionally the interpreter frame that pulled the
        #: heavy init.  This usually points to somewhere in the dispatcher.
        #: Might not be available for all calls and is removed when the log
        #: record is closed.
        self.frame = frame
        #: the PID of the current process
        self.process = None
        if dispatcher is not None:
            dispatcher = weakref(dispatcher)
        self._dispatcher = dispatcher

    def heavy_init(self):
        """Does the heavy initialization that could be expensive.  This must
        not be called from a higher stack level than when the log record was
        created and the later the initialization happens, the more off the
        date information will be for example.

        This is internally used by the record dispatching system and usually
        something not to worry about.
        """
        if self.heavy_initialized:
            return
        assert not self.late, 'heavy init is no longer possible'
        self.heavy_initialized = True
        self.process = os.getpid()
        self.time = _datetime_factory()
        if self.frame is None and Flags.get_flag('introspection', True):
            self.frame = sys._getframe(1)
        if self.exc_info is True:
            self.exc_info = sys.exc_info()

    def pull_information(self):
        """A helper function that pulls all frame-related information into
        the object so that this information is available after the log
        record was closed.
        """
        if self.information_pulled:
            return
        # due to how cached_property is implemented, the attribute access
        # has the side effect of caching the attribute on the instance of
        # the class.
        for key in self._pullable_information:
            getattr(self, key)
        self.information_pulled = True

    def close(self):
        """Closes the log record.  This will set the frame and calling
        frame to `None` and frame-related information will no longer be
        available unless it was pulled in first (:meth:`pull_information`).
        This makes a log record safe for pickling and will clean up
        memory that might be still referenced by the frames.
        """
        for key in self._noned_on_close:
            setattr(self, key, None)
        self.late = True

    def __reduce_ex__(self, protocol):
        return _create_log_record, (type(self), self.to_dict())

    def to_dict(self, json_safe=False):
        """Exports the log record into a dictionary without the information
        that cannot be safely serialized like interpreter frames and
        tracebacks.
        """
        self.pull_information()
        rv = {}
        for key, value in iteritems(self.__dict__):
            if key[:1] != '_' and key not in self._noned_on_close:
                rv[key] = value
        # the extra dict is exported as regular dict
        rv['extra'] = dict(rv['extra'])
        if json_safe:
            return to_safe_json(rv)
        return rv

    @classmethod
    def from_dict(cls, d):
        """Creates a log record from an exported dictionary.  This also
        supports JSON exported dictionaries.
        """
        rv = object.__new__(cls)
        rv.update_from_dict(d)
        return rv

    def update_from_dict(self, d):
        """Like the :meth:`from_dict` classmethod, but will update the
        instance in place.  Helpful for constructors.
        """
        self.__dict__.update(d)
        for key in self._noned_on_close:
            setattr(self, key, None)
        self._information_pulled = True
        self._channel = None
        if isinstance(self.time, string_types):
            self.time = parse_iso8601(self.time)
        self.extra = ExtraDict(self.extra)
        return self

    @cached_property
    def message(self):
        """The formatted message."""
        if not (self.args or self.kwargs):
            return self.msg
        try:
            try:
                return self.msg.format(*self.args, **self.kwargs)
            except UnicodeDecodeError:
                # Assume an unicode message but mixed-up args
                msg = self.msg.encode('utf-8', 'replace')
                return msg.format(*self.args, **self.kwargs)
            except (UnicodeEncodeError, AttributeError):
                # we catch AttributeError since if msg is bytes, it won't have the 'format' method
                if sys.exc_info()[0] is AttributeError and (PY2 or not isinstance(self.msg, bytes)):
                    # this is not the case we thought it is...
                    raise
                # Assume encoded message with unicode args.
                # The assumption of utf8 as input encoding is just a guess,
                # but this codepath is unlikely (if the message is a constant
                # string in the caller's source file)
                msg = self.msg.decode('utf-8', 'replace')
                return msg.format(*self.args, **self.kwargs)

        except Exception:
            # this obviously will not give a proper error message if the
            # information was not pulled and the log record no longer has
            # access to the frame.  But there is not much we can do about
            # that.
            e = sys.exc_info()[1]
            errormsg = ('Could not format message with provided '
                       'arguments: {err}\n  msg={msg!r}\n  '
                       'args={args!r} \n  kwargs={kwargs!r}.\n'
                       'Happened in file {file}, line {lineno}').format(
                err=e, msg=self.msg, args=self.args,
                kwargs=self.kwargs, file=self.filename,
                lineno=self.lineno
            )
            if PY2:
                errormsg = errormsg.encode('utf-8')
            raise TypeError(errormsg)

    level_name = level_name_property()

    @cached_property
    def calling_frame(self):
        """The frame in which the record has been created.  This only
        exists for as long the log record is not closed.
        """
        frm = self.frame
        globs = globals()
        while frm is not None and frm.f_globals is globs:
            frm = frm.f_back
        return frm

    @cached_property
    def func_name(self):
        """The name of the function that triggered the log call if
        available.  Requires a frame or that :meth:`pull_information`
        was called before.
        """
        cf = self.calling_frame
        if cf is not None:
            return cf.f_code.co_name

    @cached_property
    def module(self):
        """The name of the module that triggered the log call if
        available.  Requires a frame or that :meth:`pull_information`
        was called before.
        """
        cf = self.calling_frame
        if cf is not None:
            return cf.f_globals.get('__name__')

    @cached_property
    def filename(self):
        """The filename of the module in which the record has been created.
        Requires a frame or that :meth:`pull_information` was called before.
        """
        cf = self.calling_frame
        if cf is not None:
            fn = cf.f_code.co_filename
            if fn[:1] == '<' and fn[-1:] == '>':
                return fn
            return _convert_frame_filename(os.path.abspath(fn))

    @cached_property
    def lineno(self):
        """The line number of the file in which the record has been created.
        Requires a frame or that :meth:`pull_information` was called before.
        """
        cf = self.calling_frame
        if cf is not None:
            return cf.f_lineno

    @cached_property
    def thread(self):
        """The ident of the thread.  This is evaluated late and means that
        if the log record is passed to another thread, :meth:`pull_information`
        was called in the old thread.
        """
        return thread.get_ident()

    @cached_property
    def thread_name(self):
        """The name of the thread.  This is evaluated late and means that
        if the log record is passed to another thread, :meth:`pull_information`
        was called in the old thread.
        """
        return threading.currentThread().getName()

    @cached_property
    def process_name(self):
        """The name of the process in which the record has been created."""
        # Errors may occur if multiprocessing has not finished loading
        # yet - e.g. if a custom import hook causes third-party code
        # to run when multiprocessing calls import. See issue 8200
        # for an example
        mp = sys.modules.get('multiprocessing')
        if mp is not None:  # pragma: no cover
            try:
                return mp.current_process().name
            except Exception:
                pass

    @cached_property
    def formatted_exception(self):
        """The formatted exception which caused this record to be created
        in case there was any.
        """
        if self.exc_info is not None:
            rv = ''.join(traceback.format_exception(*self.exc_info))
            if PY2:
                rv = rv.decode('utf-8', 'replace')
            return rv.rstrip()

    @cached_property
    def exception_name(self):
        """The name of the exception."""
        if self.exc_info is not None:
            cls = self.exc_info[0]
            return u(cls.__module__ + '.' + cls.__name__)

    @property
    def exception_shortname(self):
        """An abbreviated exception name (no import path)"""
        return self.exception_name.rsplit('.')[-1]

    @cached_property
    def exception_message(self):
        """The message of the exception."""
        if self.exc_info is not None:
            val = self.exc_info[1]
            try:
                if PY2:
                    return unicode(val)
                else:
                    return str(val)
            except UnicodeError:
                return str(val).decode('utf-8', 'replace')

    @property
    def dispatcher(self):
        """The dispatcher that created the log record.  Might not exist because
        a log record does not have to be created from a logger or other
        dispatcher to be handled by logbook.  If this is set, it will point to
        an object that implements the :class:`~logbook.base.RecordDispatcher`
        interface.
        """
        if self._dispatcher is not None:
            return self._dispatcher()


class LoggerMixin(object):
    """This mixin class defines and implements the "usual" logger
    interface (i.e. the descriptive logging functions).

    Classes using this mixin have to implement a :meth:`!handle` method which
    takes a :class:`~logbook.LogRecord` and passes it along.
    """

    #: The name of the minimium logging level required for records to be
    #: created.
    level_name = level_name_property()

    def debug(self, *args, **kwargs):
        """Logs a :class:`~logbook.LogRecord` with the level set
        to :data:`~logbook.DEBUG`.
        """
        if not self.disabled and DEBUG >= self.level:
            self._log(DEBUG, args, kwargs)

    def info(self, *args, **kwargs):
        """Logs a :class:`~logbook.LogRecord` with the level set
        to :data:`~logbook.INFO`.
        """
        if not self.disabled and INFO >= self.level:
            self._log(INFO, args, kwargs)

    def warn(self, *args, **kwargs):
        """Logs a :class:`~logbook.LogRecord` with the level set
        to :data:`~logbook.WARNING`.  This function has an alias
        named :meth:`warning`.
        """
        if not self.disabled and WARNING >= self.level:
            self._log(WARNING, args, kwargs)

    def warning(self, *args, **kwargs):
        """Alias for :meth:`warn`."""
        return self.warn(*args, **kwargs)

    def notice(self, *args, **kwargs):
        """Logs a :class:`~logbook.LogRecord` with the level set
        to :data:`~logbook.NOTICE`.
        """
        if not self.disabled and NOTICE >= self.level:
            self._log(NOTICE, args, kwargs)

    def error(self, *args, **kwargs):
        """Logs a :class:`~logbook.LogRecord` with the level set
        to :data:`~logbook.ERROR`.
        """
        if not self.disabled and ERROR >= self.level:
            self._log(ERROR, args, kwargs)

    def exception(self, *args, **kwargs):
        """Works exactly like :meth:`error` just that the message
        is optional and exception information is recorded.
        """
        if self.disabled or ERROR < self.level:
            return
        if not args:
            args = ('Uncaught exception occurred',)
        if 'exc_info' not in kwargs:
            exc_info = sys.exc_info()
            assert exc_info[0] is not None, 'no exception occurred'
            kwargs.setdefault('exc_info', sys.exc_info())
        return self.error(*args, **kwargs)

    def critical(self, *args, **kwargs):
        """Logs a :class:`~logbook.LogRecord` with the level set
        to :data:`~logbook.CRITICAL`.
        """
        if not self.disabled and CRITICAL >= self.level:
            self._log(CRITICAL, args, kwargs)

    def log(self, level, *args, **kwargs):
        """Logs a :class:`~logbook.LogRecord` with the level set
        to the `level` parameter.  Because custom levels are not
        supported by logbook, this method is mainly used to avoid
        the use of reflection (e.g.: :func:`getattr`) for programmatic
        logging.
        """
        level = lookup_level(level)
        if level >= self.level:
            self._log(level, args, kwargs)

    def catch_exceptions(self, *args, **kwargs):
        """A context manager that catches exceptions and calls
        :meth:`exception` for exceptions caught that way.  Example:

        .. code-block:: python

            with logger.catch_exceptions():
                execute_code_that_might_fail()
        """
        if not args:
            args = ('Uncaught exception occurred',)
        return _ExceptionCatcher(self, args, kwargs)

    def _log(self, level, args, kwargs):
        exc_info = kwargs.pop('exc_info', None)
        extra = kwargs.pop('extra', None)
        self.make_record_and_handle(level, args[0], args[1:], kwargs,
                                    exc_info, extra)


class RecordDispatcher(object):
    """A record dispatcher is the internal base class that implements
    the logic used by the :class:`~logbook.Logger`.
    """

    #: If this is set to `True` the dispatcher information will be suppressed
    #: for log records emitted from this logger.
    suppress_dispatcher = False

    def __init__(self, name=None, level=NOTSET):
        #: the name of the record dispatcher
        self.name = name
        #: list of handlers specific for this record dispatcher
        self.handlers = []
        #: optionally the name of the group this logger belongs to
        self.group = None
        #: the level of the record dispatcher as integer
        self.level = level

    disabled = group_reflected_property('disabled', False)
    level = group_reflected_property('level', NOTSET, fallback=NOTSET)

    def handle(self, record):
        """Call the handlers for the specified record.  This is
        invoked automatically when a record should be handled.
        The default implementation checks if the dispatcher is disabled
        and if the record level is greater than the level of the
        record dispatcher.  In that case it will call the handlers
        (:meth:`call_handlers`).
        """
        if not self.disabled and record.level >= self.level:
            self.call_handlers(record)

    def make_record_and_handle(self, level, msg, args, kwargs, exc_info,
                               extra):
        """Creates a record from some given arguments and heads it
        over to the handling system.
        """
        # The channel information can be useful for some use cases which is
        # why we keep it on there.  The log record however internally will
        # only store a weak reference to the channel, so it might disappear
        # from one instruction to the other.  It will also disappear when
        # a log record is transmitted to another process etc.
        channel = None
        if not self.suppress_dispatcher:
            channel = self

        record = LogRecord(self.name, level, msg, args, kwargs, exc_info,
                           extra, None, channel)

        # after handling the log record is closed which will remove some
        # referenes that would require a GC run on cpython.  This includes
        # the current stack frame, exception information.  However there are
        # some use cases in keeping the records open for a little longer.
        # For example the test handler keeps log records open until the
        # test handler is closed to allow assertions based on stack frames
        # and exception information.
        try:
            self.handle(record)
        finally:
            record.late = True
            if not record.keep_open:
                record.close()

    def call_handlers(self, record):
        """Pass a record to all relevant handlers in the following
        order:

        -   per-dispatcher handlers are handled first
        -   afterwards all the current context handlers in the
            order they were pushed

        Before the first handler is invoked, the record is processed
        (:meth:`process_record`).
        """
        # for performance reasons records are only heavy initialized
        # and processed if at least one of the handlers has a higher
        # level than the record and that handler is not a black hole.
        record_initialized = False

        # Both logger attached handlers as well as context specific
        # handlers are handled one after another.  The latter also
        # include global handlers.
        for handler in chain(self.handlers,
                             Handler.stack_manager.iter_context_objects()):
            # skip records that this handler is not interested in based
            # on the record and handler level or in case this method was
            # overridden on some custom logic.
            if not handler.should_handle(record):
                continue

            # a filter can still veto the handling of the record.  This
            # however is already operating on an initialized and processed
            # record.  The impact is that filters are slower than the
            # handler's should_handle function in case there is no default
            # handler that would handle the record (delayed init).
            if handler.filter is not None \
               and not handler.filter(record, handler):
                continue

            # if this is a blackhole handler, don't even try to
            # do further processing, stop right away.  Technically
            # speaking this is not 100% correct because if the handler
            # is bubbling we shouldn't apply this logic, but then we
            # won't enter this branch anyways.  The result is that a
            # bubbling blackhole handler will never have this shortcut
            # applied and do the heavy init at one point.  This is fine
            # however because a bubbling blackhole handler is not very
            # useful in general.
            if handler.blackhole:
                break

            # we are about to handle the record.  If it was not yet
            # processed by context-specific record processors we
            # have to do that now and remeber that we processed
            # the record already.
            if not record_initialized:
                record.heavy_init()
                self.process_record(record)
                record_initialized = True

            # handle the record.  If the record was handled and
            # the record is not bubbling we can abort now.
            if handler.handle(record) and not handler.bubble:
                break

    def process_record(self, record):
        """Processes the record with all context specific processors.  This
        can be overriden to also inject additional information as necessary
        that can be provided by this record dispatcher.
        """
        if self.group is not None:
            self.group.process_record(record)
        for processor in Processor.stack_manager.iter_context_objects():
            processor.process(record)


class Logger(RecordDispatcher, LoggerMixin):
    """Instances of the Logger class represent a single logging channel.
    A "logging channel" indicates an area of an application. Exactly
    how an "area" is defined is up to the application developer.

    Names used by logbook should be descriptive and are intended for user
    display, not for filtering.  Filtering should happen based on the
    context information instead.

    A logger internally is a subclass of a
    :class:`~logbook.base.RecordDispatcher` that implements the actual
    logic.  If you want to implement a custom logger class, have a look
    at the interface of that class as well.
    """


class LoggerGroup(object):
    """A LoggerGroup represents a group of loggers.  It cannot emit log
    messages on its own but it can be used to set the disabled flag and
    log level of all loggers in the group.

    Furthermore the :meth:`process_record` method of the group is called
    by any logger in the group which by default calls into the
    :attr:`processor` callback function.
    """

    def __init__(self, loggers=None, level=NOTSET, processor=None):
        #: a list of all loggers on the logger group.  Use the
        #: :meth:`add_logger` and :meth:`remove_logger` methods to add
        #: or remove loggers from this list.
        self.loggers = []
        if loggers is not None:
            for logger in loggers:
                self.add_logger(logger)

        #: the level of the group.  This is reflected to the loggers
        #: in the group unless they overrode the setting.
        self.level = lookup_level(level)
        #: the disabled flag for all loggers in the group, unless
        #: the loggers overrode the setting.
        self.disabled = False
        #: an optional callback function that is executed to process
        #: the log records of all loggers in the group.
        self.processor = processor

    def add_logger(self, logger):
        """Adds a logger to this group."""
        assert logger.group is None, 'Logger already belongs to a group'
        logger.group = self
        self.loggers.append(logger)

    def remove_logger(self, logger):
        """Removes a logger from the group."""
        self.loggers.remove(logger)
        logger.group = None

    def process_record(self, record):
        """Like :meth:`Logger.process_record` but for all loggers in
        the group.  By default this calls into the :attr:`processor`
        function is it's not `None`.
        """
        if self.processor is not None:
            self.processor(record)


_default_dispatcher = RecordDispatcher()


def dispatch_record(record):
    """Passes a record on to the handlers on the stack.  This is useful when
    log records are created programmatically and already have all the
    information attached and should be dispatched independent of a logger.
    """
    _default_dispatcher.call_handlers(record)


# at that point we are save to import handler
from logbook.handlers import Handler

########NEW FILE########
__FILENAME__ = compat
# -*- coding: utf-8 -*-
"""
    logbook.compat
    ~~~~~~~~~~~~~~

    Backwards compatibility with stdlib's logging package and the
    warnings module.

    :copyright: (c) 2010 by Armin Ronacher, Georg Brandl.
    :license: BSD, see LICENSE for more details.
"""
import sys
import logging
import warnings
import logbook
from datetime import date, datetime

from logbook.helpers import u, string_types, iteritems

_epoch_ord = date(1970, 1, 1).toordinal()


def redirect_logging(set_root_logger_level=True):
    """Permanently redirects logging to the stdlib.  This also
    removes all otherwise registered handlers on root logger of
    the logging system but leaves the other loggers untouched.

    :param set_root_logger_level: controls of the default level of the legacy root logger is changed
       so that all legacy log messages get redirected to Logbook
    """
    del logging.root.handlers[:]
    logging.root.addHandler(RedirectLoggingHandler())
    if set_root_logger_level:
        logging.root.setLevel(logging.DEBUG)


class redirected_logging(object):
    """Temporarily redirects logging for all threads and reverts
    it later to the old handlers.  Mainly used by the internal
    unittests::

        from logbook.compat import redirected_logging
        with redirected_logging():
            ...
    """
    def __init__(self, set_root_logger_level=True):
        self.old_handlers = logging.root.handlers[:]
        self.old_level = logging.root.level
        self.set_root_logger_level = set_root_logger_level

    def start(self):
        redirect_logging(self.set_root_logger_level)

    def end(self, etype=None, evalue=None, tb=None):
        logging.root.handlers[:] = self.old_handlers
        logging.root.setLevel(self.old_level)

    __enter__ = start
    __exit__ = end


class RedirectLoggingHandler(logging.Handler):
    """A handler for the stdlib's logging system that redirects
    transparently to logbook.  This is used by the
    :func:`redirect_logging` and :func:`redirected_logging`
    functions.

    If you want to customize the redirecting you can subclass it.
    """

    def __init__(self):
        logging.Handler.__init__(self)

    def convert_level(self, level):
        """Converts a logging level into a logbook level."""
        if level >= logging.CRITICAL:
            return logbook.CRITICAL
        if level >= logging.ERROR:
            return logbook.ERROR
        if level >= logging.WARNING:
            return logbook.WARNING
        if level >= logging.INFO:
            return logbook.INFO
        return logbook.DEBUG

    def find_extra(self, old_record):
        """Tries to find custom data from the old logging record.  The
        return value is a dictionary that is merged with the log record
        extra dictionaries.
        """
        rv = vars(old_record).copy()
        for key in ('name', 'msg', 'args', 'levelname', 'levelno',
                    'pathname', 'filename', 'module', 'exc_info',
                    'exc_text', 'lineno', 'funcName', 'created',
                    'msecs', 'relativeCreated', 'thread', 'threadName',
                    'processName', 'process'):
            rv.pop(key, None)
        return rv

    def find_caller(self, old_record):
        """Tries to find the caller that issued the call."""
        frm = sys._getframe(2)
        while frm is not None:
            if frm.f_globals is globals() or \
               frm.f_globals is logbook.base.__dict__ or \
               frm.f_globals is logging.__dict__:
                frm = frm.f_back
            else:
                return frm

    def convert_time(self, timestamp):
        """Converts the UNIX timestamp of the old record into a
        datetime object as used by logbook.
        """
        return datetime.utcfromtimestamp(timestamp)

    def convert_record(self, old_record):
        """Converts an old logging record into a logbook log record."""
        record = logbook.LogRecord(old_record.name,
                                   self.convert_level(old_record.levelno),
                                   old_record.getMessage(),
                                   None, None, old_record.exc_info,
                                   self.find_extra(old_record),
                                   self.find_caller(old_record))
        record.time = self.convert_time(old_record.created)
        return record

    def emit(self, record):
        logbook.dispatch_record(self.convert_record(record))


class LoggingHandler(logbook.Handler):
    """Does the opposite of the :class:`RedirectLoggingHandler`, it sends
    messages from logbook to logging.  Because of that, it's a very bad
    idea to configure both.

    This handler is for logbook and will pass stuff over to a logger
    from the standard library.

    Example usage::

        from logbook.compat import LoggingHandler, warn
        with LoggingHandler():
            warn('This goes to logging')
    """

    def __init__(self, logger=None, level=logbook.NOTSET, filter=None,
                 bubble=False):
        logbook.Handler.__init__(self, level, filter, bubble)
        if logger is None:
            logger = logging.getLogger()
        elif isinstance(logger, string_types):
            logger = logging.getLogger(logger)
        self.logger = logger

    def get_logger(self, record):
        """Returns the logger to use for this record.  This implementation
        always return :attr:`logger`.
        """
        return self.logger

    def convert_level(self, level):
        """Converts a logbook level into a logging level."""
        if level >= logbook.CRITICAL:
            return logging.CRITICAL
        if level >= logbook.ERROR:
            return logging.ERROR
        if level >= logbook.WARNING:
            return logging.WARNING
        if level >= logbook.INFO:
            return logging.INFO
        return logging.DEBUG

    def convert_time(self, dt):
        """Converts a datetime object into a timestamp."""
        year, month, day, hour, minute, second = dt.utctimetuple()[:6]
        days = date(year, month, 1).toordinal() - _epoch_ord + day - 1
        hours = days * 24 + hour
        minutes = hours * 60 + minute
        seconds = minutes * 60 + second
        return seconds

    def convert_record(self, old_record):
        """Converts a record from logbook to logging."""
        if sys.version_info >= (2, 5):
            # make sure 2to3 does not screw this up
            optional_kwargs = {'func': getattr(old_record, 'func_name')}
        else:
            optional_kwargs = {}
        record = logging.LogRecord(old_record.channel,
                                   self.convert_level(old_record.level),
                                   old_record.filename,
                                   old_record.lineno,
                                   old_record.message,
                                   (), old_record.exc_info,
                                   **optional_kwargs)
        for key, value in iteritems(old_record.extra):
            record.__dict__.setdefault(key, value)
        record.created = self.convert_time(old_record.time)
        return record

    def emit(self, record):
        self.get_logger(record).handle(self.convert_record(record))


def redirect_warnings():
    """Like :func:`redirected_warnings` but will redirect all warnings
    to the shutdown of the interpreter:

    .. code-block:: python

        from logbook.compat import redirect_warnings
        redirect_warnings()
    """
    redirected_warnings().__enter__()


class redirected_warnings(object):
    """A context manager that copies and restores the warnings filter upon
    exiting the context, and logs warnings using the logbook system.

    The :attr:`~logbook.LogRecord.channel` attribute of the log record will be
    the import name of the warning.

    Example usage:

    .. code-block:: python

        from logbook.compat import redirected_warnings
        from warnings import warn

        with redirected_warnings():
            warn(DeprecationWarning('logging should be deprecated'))
    """

    def __init__(self):
        self._entered = False

    def message_to_unicode(self, message):
        try:
            return u(str(message))
        except UnicodeError:
            return str(message).decode('utf-8', 'replace')

    def make_record(self, message, exception, filename, lineno):
        category = exception.__name__
        if exception.__module__ not in ('exceptions', 'builtins'):
            category = exception.__module__ + '.' + category
        rv = logbook.LogRecord(category, logbook.WARNING, message)
        # we don't know the caller, but we get that information from the
        # warning system.  Just attach them.
        rv.filename = filename
        rv.lineno = lineno
        return rv

    def start(self):
        if self._entered:  # pragma: no cover
            raise RuntimeError("Cannot enter %r twice" % self)
        self._entered = True
        self._filters = warnings.filters
        warnings.filters = self._filters[:]
        self._showwarning = warnings.showwarning

        def showwarning(message, category, filename, lineno,
                        file=None, line=None):
            message = self.message_to_unicode(message)
            record = self.make_record(message, category, filename, lineno)
            logbook.dispatch_record(record)
        warnings.showwarning = showwarning

    def end(self, etype=None, evalue=None, tb=None):
        if not self._entered:  # pragma: no cover
            raise RuntimeError("Cannot exit %r without entering first" % self)
        warnings.filters = self._filters
        warnings.showwarning = self._showwarning

    __enter__ = start
    __exit__ = end

########NEW FILE########
__FILENAME__ = handlers
# -*- coding: utf-8 -*-
"""
    logbook.handlers
    ~~~~~~~~~~~~~~~~

    The handler interface and builtin handlers.

    :copyright: (c) 2010 by Armin Ronacher, Georg Brandl.
    :license: BSD, see LICENSE for more details.
"""
import os
import re
import sys
import stat
import errno
import socket
try:
    from hashlib import sha1
except ImportError:
    from sha import new as sha1
import threading
import traceback
from datetime import datetime, timedelta
from threading import Lock
from collections import deque

from logbook.base import CRITICAL, ERROR, WARNING, NOTICE, INFO, DEBUG, \
     NOTSET, level_name_property, _missing, lookup_level, \
     Flags, ContextObject, ContextStackManager
from logbook.helpers import rename, b, _is_text_stream, is_unicode, PY2, \
    zip, xrange, string_types, integer_types, reraise, u


DEFAULT_FORMAT_STRING = (
    u('[{record.time:%Y-%m-%d %H:%M}] ') +
    u('{record.level_name}: {record.channel}: {record.message}')
)
SYSLOG_FORMAT_STRING = u('{record.channel}: {record.message}')
NTLOG_FORMAT_STRING = u('''\
Message Level: {record.level_name}
Location: {record.filename}:{record.lineno}
Module: {record.module}
Function: {record.func_name}
Exact Time: {record.time:%Y-%m-%d %H:%M:%S}

Event provided Message:

{record.message}
''')
TEST_FORMAT_STRING = \
u('[{record.level_name}] {record.channel}: {record.message}')
MAIL_FORMAT_STRING = u('''\
Subject: {handler.subject}

Message type:       {record.level_name}
Location:           {record.filename}:{record.lineno}
Module:             {record.module}
Function:           {record.func_name}
Time:               {record.time:%Y-%m-%d %H:%M:%S}

Message:

{record.message}
''')
MAIL_RELATED_FORMAT_STRING = u('''\
Message type:       {record.level_name}
Location:           {record.filename}:{record.lineno}
Module:             {record.module}
Function:           {record.func_name}
{record.message}
''')

SYSLOG_PORT = 514

REGTYPE = type(re.compile("I'm a regular expression!"))

def create_syshandler(application_name, level=NOTSET):
    """Creates the handler the operating system provides.  On Unix systems
    this creates a :class:`SyslogHandler`, on Windows sytems it will
    create a :class:`NTEventLogHandler`.
    """
    if os.name == 'nt':
        return NTEventLogHandler(application_name, level=level)
    return SyslogHandler(application_name, level=level)


class _HandlerType(type):
    """The metaclass of handlers injects a destructor if the class has an
    overridden close method.  This makes it possible that the default
    handler class as well as all subclasses that don't need cleanup to be
    collected with less overhead.
    """

    def __new__(cls, name, bases, d):
        # aha, that thing has a custom close method.  We will need a magic
        # __del__ for it to be called on cleanup.
        if bases != (ContextObject,) and 'close' in d and '__del__' not in d \
           and not any(hasattr(x, '__del__') for x in bases):
            def _magic_del(self):
                try:
                    self.close()
                except Exception:
                    # del is also invoked when init fails, so we better just
                    # ignore any exception that might be raised here
                    pass
            d['__del__'] = _magic_del
        return type.__new__(cls, name, bases, d)


class Handler(ContextObject):
    """Handler instances dispatch logging events to specific destinations.

    The base handler class. Acts as a placeholder which defines the Handler
    interface. Handlers can optionally use Formatter instances to format
    records as desired. By default, no formatter is specified; in this case,
    the 'raw' message as determined by record.message is logged.

    To bind a handler you can use the :meth:`push_application` and
    :meth:`push_thread` methods.  This will push the handler on a stack of
    handlers.  To undo this, use the :meth:`pop_application` and
    :meth:`pop_thread` methods::

        handler = MyHandler()
        handler.push_application()
        # all here goes to that handler
        handler.pop_application()

    By default messages sent to that handler will not go to a handler on
    an outer level on the stack, if handled.  This can be changed by
    setting bubbling to `True`.  This setup for example would not have
    any effect::

        handler = NullHandler(bubble=True)
        handler.push_application()

    Whereas this setup disables all logging for the application::

        handler = NullHandler()
        handler.push_application()

    There are also context managers to setup the handler for the duration
    of a `with`-block::

        with handler.applicationbound():
            ...

        with handler.threadbound():
            ...

    Because `threadbound` is a common operation, it is aliased to a with
    on the handler itself::

        with handler:
            ...
    """
    __metaclass__ = _HandlerType

    stack_manager = ContextStackManager()

    #: a flag for this handler that can be set to `True` for handlers that
    #: are consuming log records but are not actually displaying it.  This
    #: flag is set for the :class:`NullHandler` for instance.
    blackhole = False

    def __init__(self, level=NOTSET, filter=None, bubble=False):
        #: the level for the handler.  Defaults to `NOTSET` which
        #: consumes all entries.
        self.level = lookup_level(level)
        #: the formatter to be used on records.  This is a function
        #: that is passed a log record as first argument and the
        #: handler as second and returns something formatted
        #: (usually a unicode string)
        self.formatter = None
        #: the filter to be used with this handler
        self.filter = filter
        #: the bubble flag of this handler
        self.bubble = bubble

    level_name = level_name_property()

    def format(self, record):
        """Formats a record with the given formatter.  If no formatter
        is set, the record message is returned.  Generally speaking the
        return value is most likely a unicode string, but nothing in
        the handler interface requires a formatter to return a unicode
        string.

        The combination of a handler and formatter might have the
        formatter return an XML element tree for example.
        """
        if self.formatter is None:
            return record.message
        return self.formatter(record, self)

    def should_handle(self, record):
        """Returns `True` if this handler wants to handle the record.  The
        default implementation checks the level.
        """
        return record.level >= self.level

    def handle(self, record):
        """Emits the record and falls back.  It tries to :meth:`emit` the
        record and if that fails, it will call into :meth:`handle_error` with
        the record and traceback.  This function itself will always emit
        when called, even if the logger level is higher than the record's
        level.

        If this method returns `False` it signals to the calling function that
        no recording took place in which case it will automatically bubble.
        This should not be used to signal error situations.  The default
        implementation always returns `True`.
        """
        try:
            self.emit(record)
        except Exception:
            self.handle_error(record, sys.exc_info())
        return True

    def emit(self, record):
        """Emit the specified logging record.  This should take the
        record and deliver it to whereever the handler sends formatted
        log records.
        """

    def emit_batch(self, records, reason):
        """Some handlers may internally queue up records and want to forward
        them at once to another handler.  For example the
        :class:`~logbook.FingersCrossedHandler` internally buffers
        records until a level threshold is reached in which case the buffer
        is sent to this method and not :meth:`emit` for each record.

        The default behaviour is to call :meth:`emit` for each record in
        the buffer, but handlers can use this to optimize log handling.  For
        instance the mail handler will try to batch up items into one mail
        and not to emit mails for each record in the buffer.

        Note that unlike :meth:`emit` there is no wrapper method like
        :meth:`handle` that does error handling.  The reason is that this
        is intended to be used by other handlers which are already protected
        against internal breakage.

        `reason` is a string that specifies the rason why :meth:`emit_batch`
        was called, and not :meth:`emit`.  The following are valid values:

        ``'buffer'``
            Records were buffered for performance reasons or because the
            records were sent to another process and buffering was the only
            possible way.  For most handlers this should be equivalent to
            calling :meth:`emit` for each record.

        ``'escalation'``
            Escalation means that records were buffered in case the threshold
            was exceeded.  In this case, the last record in the iterable is the
            record that triggered the call.

        ``'group'``
            All the records in the iterable belong to the same logical
            component and happened in the same process.  For example there was
            a long running computation and the handler is invoked with a bunch
            of records that happened there.  This is similar to the escalation
            reason, just that the first one is the significant one, not the
            last.

        If a subclass overrides this and does not want to handle a specific
        reason it must call into the superclass because more reasons might
        appear in future releases.

        Example implementation::

            def emit_batch(self, records, reason):
                if reason not in ('escalation', 'group'):
                    Handler.emit_batch(self, records, reason)
                ...
        """
        for record in records:
            self.emit(record)

    def close(self):
        """Tidy up any resources used by the handler.  This is automatically
        called by the destructor of the class as well, but explicit calls are
        encouraged.  Make sure that multiple calls to close are possible.
        """

    def handle_error(self, record, exc_info):
        """Handle errors which occur during an emit() call.  The behaviour of
        this function depends on the current `errors` setting.

        Check :class:`Flags` for more information.
        """
        try:
            behaviour = Flags.get_flag('errors', 'print')
            if behaviour == 'raise':
                reraise(exc_info[0], exc_info[1], exc_info[2])
            elif behaviour == 'print':
                traceback.print_exception(*(exc_info + (None, sys.stderr)))
                sys.stderr.write('Logged from file %s, line %s\n' % (
                                 record.filename, record.lineno))
        except IOError:
            pass


class NullHandler(Handler):
    """A handler that does nothing, meant to be inserted in a handler chain
    with ``bubble=False`` to stop further processing.
    """
    blackhole = True


class WrapperHandler(Handler):
    """A class that can wrap another handler and redirect all calls to the
    wrapped handler::

        handler = WrapperHandler(other_handler)

    Subclasses should override the :attr:`_direct_attrs` attribute as
    necessary.
    """

    #: a set of direct attributes that are not forwarded to the inner
    #: handler.  This has to be extended as necessary.
    _direct_attrs = frozenset(['handler'])

    def __init__(self, handler):
        self.handler = handler

    def __getattr__(self, name):
        return getattr(self.handler, name)

    def __setattr__(self, name, value):
        if name in self._direct_attrs:
            return Handler.__setattr__(self, name, value)
        setattr(self.handler, name, value)


class StringFormatter(object):
    """Many handlers format the log entries to text format.  This is done
    by a callable that is passed a log record and returns an unicode
    string.  The default formatter for this is implemented as a class so
    that it becomes possible to hook into every aspect of the formatting
    process.
    """

    def __init__(self, format_string):
        self.format_string = format_string

    def _get_format_string(self):
        return self._format_string

    def _set_format_string(self, value):
        self._format_string = value
        self._formatter = value

    format_string = property(_get_format_string, _set_format_string)
    del _get_format_string, _set_format_string

    def format_record(self, record, handler):
        try:
            return self._formatter.format(record=record, handler=handler)
        except UnicodeEncodeError:
            # self._formatter is a str, but some of the record items
            # are unicode
            fmt = self._formatter.decode('ascii', 'replace')
            return fmt.format(record=record, handler=handler)
        except UnicodeDecodeError:
            # self._formatter is unicode, but some of the record items
            # are non-ascii str
            fmt = self._formatter.encode('ascii', 'replace')
            return fmt.format(record=record, handler=handler)

    def format_exception(self, record):
        return record.formatted_exception

    def __call__(self, record, handler):
        line = self.format_record(record, handler)
        exc = self.format_exception(record)
        if exc:
            line += u('\n') + exc
        return line


class StringFormatterHandlerMixin(object):
    """A mixin for handlers that provides a default integration for the
    :class:`~logbook.StringFormatter` class.  This is used for all handlers
    by default that log text to a destination.
    """

    #: a class attribute for the default format string to use if the
    #: constructor was invoked with `None`.
    default_format_string = DEFAULT_FORMAT_STRING

    #: the class to be used for string formatting
    formatter_class = StringFormatter

    def __init__(self, format_string):
        if format_string is None:
            format_string = self.default_format_string

        #: the currently attached format string as new-style format
        #: string.
        self.format_string = format_string

    def _get_format_string(self):
        if isinstance(self.formatter, StringFormatter):
            return self.formatter.format_string

    def _set_format_string(self, value):
        if value is None:
            self.formatter = None
        else:
            self.formatter = self.formatter_class(value)

    format_string = property(_get_format_string, _set_format_string)
    del _get_format_string, _set_format_string


class HashingHandlerMixin(object):
    """Mixin class for handlers that are hashing records."""

    def hash_record_raw(self, record):
        """Returns a hashlib object with the hash of the record."""
        hash = sha1()
        hash.update(('%d\x00' % record.level).encode('ascii'))
        hash.update((record.channel or u('')).encode('utf-8') + b('\x00'))
        hash.update(record.filename.encode('utf-8') + b('\x00'))
        hash.update(b(str(record.lineno)))
        return hash

    def hash_record(self, record):
        """Returns a hash for a record to keep it apart from other records.
        This is used for the `record_limit` feature.  By default
        The level, channel, filename and location are hashed.

        Calls into :meth:`hash_record_raw`.
        """
        return self.hash_record_raw(record).hexdigest()

_NUMBER_TYPES = integer_types + (float,)

class LimitingHandlerMixin(HashingHandlerMixin):
    """Mixin class for handlers that want to limit emitting records.

    In the default setting it delivers all log records but it can be set up
    to not send more than n mails for the same record each hour to not
    overload an inbox and the network in case a message is triggered multiple
    times a minute.  The following example limits it to 60 mails an hour::

        from datetime import timedelta
        handler = MailHandler(record_limit=1,
                              record_delta=timedelta(minutes=1))
    """

    def __init__(self, record_limit, record_delta):
        self.record_limit = record_limit
        self._limit_lock = Lock()
        self._record_limits = {}
        if record_delta is None:
            record_delta = timedelta(seconds=60)
        elif isinstance(record_delta, _NUMBER_TYPES):
            record_delta = timedelta(seconds=record_delta)
        self.record_delta = record_delta

    def check_delivery(self, record):
        """Helper function to check if data should be delivered by this
        handler.  It returns a tuple in the form ``(suppression_count,
        allow)``.  The first one is the number of items that were not delivered
        so far, the second is a boolean flag if a delivery should happen now.
        """
        if self.record_limit is None:
            return 0, True
        hash = self.hash_record(record)
        self._limit_lock.acquire()
        try:
            allow_delivery = None
            suppression_count = old_count = 0
            first_count = now = datetime.utcnow()

            if hash in self._record_limits:
                last_count, suppression_count = self._record_limits[hash]
                if last_count + self.record_delta < now:
                    allow_delivery = True
                else:
                    first_count = last_count
                    old_count = suppression_count

            if not suppression_count and \
               len(self._record_limits) >= self.max_record_cache:
                cache_items = self._record_limits.items()
                cache_items.sort()
                del cache_items[:int(self._record_limits) \
                    * self.record_cache_prune]
                self._record_limits = dict(cache_items)

            self._record_limits[hash] = (first_count, old_count + 1)

            if allow_delivery is None:
                allow_delivery = old_count < self.record_limit
            return suppression_count, allow_delivery
        finally:
            self._limit_lock.release()


class StreamHandler(Handler, StringFormatterHandlerMixin):
    """a handler class which writes logging records, appropriately formatted,
    to a stream. note that this class does not close the stream, as sys.stdout
    or sys.stderr may be used.

    If a stream handler is used in a `with` statement directly it will
    :meth:`close` on exit to support this pattern::

        with StreamHandler(my_stream):
            pass

    .. admonition:: Notes on the encoding

       On Python 3, the encoding parameter is only used if a stream was
       passed that was opened in binary mode.
    """

    def __init__(self, stream, level=NOTSET, format_string=None,
                 encoding=None, filter=None, bubble=False):
        Handler.__init__(self, level, filter, bubble)
        StringFormatterHandlerMixin.__init__(self, format_string)
        self.encoding = encoding
        self.lock = threading.Lock()
        if stream is not _missing:
            self.stream = stream

    def __enter__(self):
        return Handler.__enter__(self)

    def __exit__(self, exc_type, exc_value, tb):
        self.close()
        return Handler.__exit__(self, exc_type, exc_value, tb)

    def close(self):
        """The default stream handler implementation is not to close
        the wrapped stream but to flush it.
        """
        self.flush()

    def flush(self):
        """Flushes the inner stream."""
        if self.stream is not None and hasattr(self.stream, 'flush'):
            self.stream.flush()

    def format_and_encode(self, record):
        """Formats the record and encodes it to the stream encoding."""
        stream = self.stream
        rv = self.format(record) + '\n'
        if (PY2 and is_unicode(rv)) or \
                not (PY2 or is_unicode(rv) or _is_text_stream(stream)):
            enc = self.encoding
            if enc is None:
                enc = getattr(stream, 'encoding', None) or 'utf-8'
            rv = rv.encode(enc, 'replace')
        return rv

    def write(self, item):
        """Writes a bytestring to the stream."""
        self.stream.write(item)

    def emit(self, record):
        self.lock.acquire()
        try:
            self.write(self.format_and_encode(record))
            self.flush()
        finally:
            self.lock.release()


class FileHandler(StreamHandler):
    """A handler that does the task of opening and closing files for you.
    By default the file is opened right away, but you can also `delay`
    the open to the point where the first message is written.

    This is useful when the handler is used with a
    :class:`~logbook.FingersCrossedHandler` or something similar.
    """

    def __init__(self, filename, mode='a', encoding=None, level=NOTSET,
                 format_string=None, delay=False, filter=None, bubble=False):
        if encoding is None:
            encoding = 'utf-8'
        StreamHandler.__init__(self, None, level, format_string,
                               encoding, filter, bubble)
        self._filename = filename
        self._mode = mode
        if delay:
            self.stream = None
        else:
            self._open()

    def _open(self, mode=None):
        if mode is None:
            mode = self._mode
        self.stream = open(self._filename, mode)

    def write(self, item):
        if self.stream is None:
            self._open()
        if not PY2 and isinstance(item, bytes):
            self.stream.buffer.write(item)
        else:
            self.stream.write(item)

    def close(self):
        if self.stream is not None:
            self.flush()
            self.stream.close()
            self.stream = None

    def format_and_encode(self, record):
        # encodes based on the stream settings, so the stream has to be
        # open at the time this function is called.
        if self.stream is None:
            self._open()
        return StreamHandler.format_and_encode(self, record)

    def emit(self, record):
        if self.stream is None:
            self._open()
        StreamHandler.emit(self, record)


class MonitoringFileHandler(FileHandler):
    """A file handler that will check if the file was moved while it was
    open.  This might happen on POSIX systems if an application like
    logrotate moves the logfile over.

    Because of different IO concepts on Windows, this handler will not
    work on a windows system.
    """

    def __init__(self, filename, mode='a', encoding='utf-8', level=NOTSET,
                 format_string=None, delay=False, filter=None, bubble=False):
        FileHandler.__init__(self, filename, mode, encoding, level,
                             format_string, delay, filter, bubble)
        if os.name == 'nt':
            raise RuntimeError('MonitoringFileHandler '
                               'does not support Windows')
        self._query_fd()

    def _query_fd(self):
        if self.stream is None:
            self._last_stat = None, None
        else:
            try:
                st = os.stat(self._filename)
            except OSError:
                e = sys.exc_info()[1]
                if e.errno != 2:
                    raise
                self._last_stat = None, None
            else:
                self._last_stat = st[stat.ST_DEV], st[stat.ST_INO]

    def emit(self, record):
        last_stat = self._last_stat
        self._query_fd()
        if last_stat != self._last_stat:
            self.close()
        FileHandler.emit(self, record)
        self._query_fd()


class StderrHandler(StreamHandler):
    """A handler that writes to what is currently at stderr.  At the first
    glace this appears to just be a :class:`StreamHandler` with the stream
    set to :data:`sys.stderr` but there is a difference: if the handler is
    created globally and :data:`sys.stderr` changes later, this handler will
    point to the current `stderr`, whereas a stream handler would still
    point to the old one.
    """

    def __init__(self, level=NOTSET, format_string=None, filter=None,
                 bubble=False):
        StreamHandler.__init__(self, _missing, level, format_string,
                               None, filter, bubble)

    @property
    def stream(self):
        return sys.stderr


class RotatingFileHandlerBase(FileHandler):
    """Baseclass for rotating file handlers.

    .. versionchanged:: 0.3
       This class was deprecated because the interface is not flexible
       enough to implement proper file rotations.  The former builtin
       subclasses no longer use this baseclass.
    """

    def __init__(self, *args, **kwargs):
        from warnings import warn
        warn(DeprecationWarning('This class is deprecated'))
        FileHandler.__init__(self, *args, **kwargs)

    def emit(self, record):
        self.lock.acquire()
        try:
            msg = self.format_and_encode(record)
            if self.should_rollover(record, msg):
                self.perform_rollover()
            self.write(msg)
            self.flush()
        finally:
            self.lock.release()

    def should_rollover(self, record, formatted_record):
        """Called with the log record and the return value of the
        :meth:`format_and_encode` method.  The method has then to
        return `True` if a rollover should happen or `False`
        otherwise.

        .. versionchanged:: 0.3
           Previously this method was called with the number of bytes
           returned by :meth:`format_and_encode`
        """
        return False

    def perform_rollover(self):
        """Called if :meth:`should_rollover` returns `True` and has
        to perform the actual rollover.
        """


class RotatingFileHandler(FileHandler):
    """This handler rotates based on file size.  Once the maximum size
    is reached it will reopen the file and start with an empty file
    again.  The old file is moved into a backup copy (named like the
    file, but with a ``.backupnumber`` appended to the file.  So if
    you are logging to ``mail`` the first backup copy is called
    ``mail.1``.)

    The default number of backups is 5.  Unlike a similar logger from
    the logging package, the backup count is mandatory because just
    reopening the file is dangerous as it deletes the log without
    asking on rollover.
    """

    def __init__(self, filename, mode='a', encoding='utf-8', level=NOTSET,
                 format_string=None, delay=False, max_size=1024 * 1024,
                 backup_count=5, filter=None, bubble=False):
        FileHandler.__init__(self, filename, mode, encoding, level,
                             format_string, delay, filter, bubble)
        self.max_size = max_size
        self.backup_count = backup_count
        assert backup_count > 0, 'at least one backup file has to be ' \
                                 'specified'

    def should_rollover(self, record, bytes):
        self.stream.seek(0, 2)
        return self.stream.tell() + bytes >= self.max_size

    def perform_rollover(self):
        self.stream.close()
        for x in xrange(self.backup_count - 1, 0, -1):
            src = '%s.%d' % (self._filename, x)
            dst = '%s.%d' % (self._filename, x + 1)
            try:
                rename(src, dst)
            except OSError:
                e = sys.exc_info()[1]
                if e.errno != errno.ENOENT:
                    raise
        rename(self._filename, self._filename + '.1')
        self._open('w')

    def emit(self, record):
        self.lock.acquire()
        try:
            msg = self.format_and_encode(record)
            if self.should_rollover(record, len(msg)):
                self.perform_rollover()
            self.write(msg)
            self.flush()
        finally:
            self.lock.release()


class TimedRotatingFileHandler(FileHandler):
    """This handler rotates based on dates.  It will name the file
    after the filename you specify and the `date_format` pattern.

    So for example if you configure your handler like this::

        handler = TimedRotatingFileHandler('/var/log/foo.log',
                                           date_format='%Y-%m-%d')

    The filenames for the logfiles will look like this::

        /var/log/foo-2010-01-10.log
        /var/log/foo-2010-01-11.log
        ...

    By default it will keep all these files around, if you want to limit
    them, you can specify a `backup_count`.
    """

    def __init__(self, filename, mode='a', encoding='utf-8', level=NOTSET,
                 format_string=None, date_format='%Y-%m-%d',
                 backup_count=0, filter=None, bubble=False):
        FileHandler.__init__(self, filename, mode, encoding, level,
                             format_string, True, filter, bubble)
        self.date_format = date_format
        self.backup_count = backup_count
        self._fn_parts = os.path.splitext(os.path.abspath(filename))
        self._filename = None

    def _get_timed_filename(self, datetime):
        return datetime.strftime('-' + self.date_format) \
                       .join(self._fn_parts)

    def should_rollover(self, record):
        fn = self._get_timed_filename(record.time)
        rv = self._filename is not None and self._filename != fn
        # remember the current filename.  In case rv is True, the rollover
        # performing function will already have the new filename
        self._filename = fn
        return rv

    def files_to_delete(self):
        """Returns a list with the files that have to be deleted when
        a rollover occours.
        """
        directory = os.path.dirname(self._filename)
        files = []
        for filename in os.listdir(directory):
            filename = os.path.join(directory, filename)
            if filename.startswith(self._fn_parts[0] + '-') and \
               filename.endswith(self._fn_parts[1]):
                files.append((os.path.getmtime(filename), filename))
        files.sort()
        return files[:-self.backup_count + 1]

    def perform_rollover(self):
        self.stream.close()
        if self.backup_count > 0:
            for time, filename in self.files_to_delete():
                os.remove(filename)
        self._open('w')

    def emit(self, record):
        self.lock.acquire()
        try:
            if self.should_rollover(record):
                self.perform_rollover()
            self.write(self.format_and_encode(record))
            self.flush()
        finally:
            self.lock.release()


class TestHandler(Handler, StringFormatterHandlerMixin):
    """Like a stream handler but keeps the values in memory.  This
    logger provides some ways to test for the records in memory.

    Example usage::

        def my_test():
            with logbook.TestHandler() as handler:
                logger.warn('A warning')
                assert logger.has_warning('A warning')
                ...
    """
    default_format_string = TEST_FORMAT_STRING

    def __init__(self, level=NOTSET, format_string=None, filter=None,
                 bubble=False):
        Handler.__init__(self, level, filter, bubble)
        StringFormatterHandlerMixin.__init__(self, format_string)
        #: captures the :class:`LogRecord`\s as instances
        self.records = []
        self._formatted_records = []
        self._formatted_record_cache = []

    def close(self):
        """Close all records down when the handler is closed."""
        for record in self.records:
            record.close()

    def emit(self, record):
        # keep records open because we will want to examine them after the
        # call to the emit function.  If we don't do that, the traceback
        # attribute and other things will already be removed.
        record.keep_open = True
        self.records.append(record)

    @property
    def formatted_records(self):
        """Captures the formatted log records as unicode strings."""
        if len(self._formatted_record_cache) != len(self.records) or \
           any(r1 != r2 for r1, r2 in
               zip(self.records, self._formatted_record_cache)):
            self._formatted_records = [self.format(r) for r in self.records]
            self._formatted_record_cache = list(self.records)
        return self._formatted_records

    @property
    def has_criticals(self):
        """`True` if any :data:`CRITICAL` records were found."""
        return any(r.level == CRITICAL for r in self.records)

    @property
    def has_errors(self):
        """`True` if any :data:`ERROR` records were found."""
        return any(r.level == ERROR for r in self.records)

    @property
    def has_warnings(self):
        """`True` if any :data:`WARNING` records were found."""
        return any(r.level == WARNING for r in self.records)

    @property
    def has_notices(self):
        """`True` if any :data:`NOTICE` records were found."""
        return any(r.level == NOTICE for r in self.records)

    @property
    def has_infos(self):
        """`True` if any :data:`INFO` records were found."""
        return any(r.level == INFO for r in self.records)

    @property
    def has_debugs(self):
        """`True` if any :data:`DEBUG` records were found."""
        return any(r.level == DEBUG for r in self.records)

    def has_critical(self, *args, **kwargs):
        """`True` if a specific :data:`CRITICAL` log record exists.

        See :ref:`probe-log-records` for more information.
        """
        kwargs['level'] = CRITICAL
        return self._test_for(*args, **kwargs)

    def has_error(self, *args, **kwargs):
        """`True` if a specific :data:`ERROR` log record exists.

        See :ref:`probe-log-records` for more information.
        """
        kwargs['level'] = ERROR
        return self._test_for(*args, **kwargs)

    def has_warning(self, *args, **kwargs):
        """`True` if a specific :data:`WARNING` log record exists.

        See :ref:`probe-log-records` for more information.
        """
        kwargs['level'] = WARNING
        return self._test_for(*args, **kwargs)

    def has_notice(self, *args, **kwargs):
        """`True` if a specific :data:`NOTICE` log record exists.

        See :ref:`probe-log-records` for more information.
        """
        kwargs['level'] = NOTICE
        return self._test_for(*args, **kwargs)

    def has_info(self, *args, **kwargs):
        """`True` if a specific :data:`INFO` log record exists.

        See :ref:`probe-log-records` for more information.
        """
        kwargs['level'] = INFO
        return self._test_for(*args, **kwargs)

    def has_debug(self, *args, **kwargs):
        """`True` if a specific :data:`DEBUG` log record exists.

        See :ref:`probe-log-records` for more information.
        """
        kwargs['level'] = DEBUG
        return self._test_for(*args, **kwargs)

    def _test_for(self, message=None, channel=None, level=None):
        def _match(needle, haystack):
            "Matches both compiled regular expressions and strings"
            if isinstance(needle, REGTYPE) and needle.search(haystack):
                return True
            if needle == haystack:
                return True
            return False
        for record in self.records:
            if level is not None and record.level != level:
                continue
            if channel is not None and record.channel != channel:
                continue
            if message is not None and not _match(message, record.message):
                continue
            return True
        return False


class MailHandler(Handler, StringFormatterHandlerMixin,
                  LimitingHandlerMixin):
    """A handler that sends error mails.  The format string used by this
    handler are the contents of the mail plus the headers.  This is handy
    if you want to use a custom subject or ``X-`` header::

        handler = MailHandler(format_string='''\
        Subject: {record.level_name} on My Application

        {record.message}
        {record.extra[a_custom_injected_record]}
        ''')

    This handler will always emit text-only mails for maximum portability and
    best performance.

    In the default setting it delivers all log records but it can be set up
    to not send more than n mails for the same record each hour to not
    overload an inbox and the network in case a message is triggered multiple
    times a minute.  The following example limits it to 60 mails an hour::

        from datetime import timedelta
        handler = MailHandler(record_limit=1,
                              record_delta=timedelta(minutes=1))

    The default timedelta is 60 seconds (one minute).

    The mail handler is sending mails in a blocking manner.  If you are not
    using some centralized system for logging these messages (with the help
    of ZeroMQ or others) and the logging system slows you down you can
    wrap the handler in a :class:`logbook.queues.ThreadedWrapperHandler`
    that will then send the mails in a background thread.

    .. versionchanged:: 0.3
       The handler supports the batching system now.
    """
    default_format_string = MAIL_FORMAT_STRING
    default_related_format_string = MAIL_RELATED_FORMAT_STRING
    default_subject = u('Server Error in Application')

    #: the maximum number of record hashes in the cache for the limiting
    #: feature.  Afterwards, record_cache_prune percent of the oldest
    #: entries are removed
    max_record_cache = 512

    #: the number of items to prune on a cache overflow in percent.
    record_cache_prune = 0.333

    def __init__(self, from_addr, recipients, subject=None,
                 server_addr=None, credentials=None, secure=None,
                 record_limit=None, record_delta=None, level=NOTSET,
                 format_string=None, related_format_string=None,
                 filter=None, bubble=False):
        Handler.__init__(self, level, filter, bubble)
        StringFormatterHandlerMixin.__init__(self, format_string)
        LimitingHandlerMixin.__init__(self, record_limit, record_delta)
        self.from_addr = from_addr
        self.recipients = recipients
        if subject is None:
            subject = self.default_subject
        self.subject = subject
        self.server_addr = server_addr
        self.credentials = credentials
        self.secure = secure
        if related_format_string is None:
            related_format_string = self.default_related_format_string
        self.related_format_string = related_format_string

    def _get_related_format_string(self):
        if isinstance(self.related_formatter, StringFormatter):
            return self.related_formatter.format_string
    def _set_related_format_string(self, value):
        if value is None:
            self.related_formatter = None
        else:
            self.related_formatter = self.formatter_class(value)
    related_format_string = property(_get_related_format_string,
                                    _set_related_format_string)
    del _get_related_format_string, _set_related_format_string

    def get_recipients(self, record):
        """Returns the recipients for a record.  By default the
        :attr:`recipients` attribute is returned for all records.
        """
        return self.recipients

    def message_from_record(self, record, suppressed):
        """Creates a new message for a record as email message object
        (:class:`email.message.Message`).  `suppressed` is the number
        of mails not sent if the `record_limit` feature is active.
        """
        from email.message import Message
        from email.header import Header
        msg = Message()
        msg.set_charset('utf-8')
        lineiter = iter(self.format(record).splitlines())
        for line in lineiter:
            if not line:
                break
            h, v = line.split(':', 1)
            # We could probably just encode everything. For the moment encode
            # only what really needed to avoid breaking a couple of tests.
            try:
                v.encode('ascii')
            except UnicodeEncodeError:
                msg[h.strip()] = Header(v.strip(), 'utf-8')
            else:
                msg[h.strip()] = v.strip()

        msg.replace_header('Content-Transfer-Encoding', '8bit')

        body = '\r\n'.join(lineiter)
        if suppressed:
            body += '\r\n\r\nThis message occurred additional %d ' \
                    'time(s) and was suppressed' % suppressed

        # inconsistency in Python 2.5
        # other versions correctly return msg.get_payload() as str
        if sys.version_info < (2, 6) and isinstance(body, unicode):
            body = body.encode('utf-8')

        msg.set_payload(body, 'UTF-8')
        return msg

    def format_related_record(self, record):
        """Used for format the records that led up to another record or
        records that are related into strings.  Used by the batch formatter.
        """
        return self.related_formatter(record, self)

    def generate_mail(self, record, suppressed=0):
        """Generates the final email (:class:`email.message.Message`)
        with headers and date.  `suppressed` is the number of mails
        that were not send if the `record_limit` feature is active.
        """
        from email.utils import formatdate
        msg = self.message_from_record(record, suppressed)
        msg['From'] = self.from_addr
        msg['Date'] = formatdate()
        return msg

    def collapse_mails(self, mail, related, reason):
        """When escaling or grouped mails are """
        if not related:
            return mail
        if reason == 'group':
            title = 'Other log records in the same group'
        else:
            title = 'Log records that led up to this one'
        mail.set_payload('%s\r\n\r\n\r\n%s:\r\n\r\n%s' % (
            mail.get_payload(),
            title,
            '\r\n\r\n'.join(body.rstrip() for body in related)
        ))
        return mail

    def get_connection(self):
        """Returns an SMTP connection.  By default it reconnects for
        each sent mail.
        """
        from smtplib import SMTP, SMTP_PORT, SMTP_SSL_PORT
        if self.server_addr is None:
            host = '127.0.0.1'
            port = self.secure and SMTP_SSL_PORT or SMTP_PORT
        else:
            host, port = self.server_addr
        con = SMTP()
        con.connect(host, port)
        if self.credentials is not None:
            if self.secure is not None:
                con.ehlo()
                con.starttls(*self.secure)
                con.ehlo()
            con.login(*self.credentials)
        return con

    def close_connection(self, con):
        """Closes the connection that was returned by
        :meth:`get_connection`.
        """
        try:
            if con is not None:
                con.quit()
        except Exception:
            pass

    def deliver(self, msg, recipients):
        """Delivers the given message to a list of recpients."""
        con = self.get_connection()
        try:
            con.sendmail(self.from_addr, recipients, msg.as_string())
        finally:
            self.close_connection(con)

    def emit(self, record):
        suppressed = 0
        if self.record_limit is not None:
            suppressed, allow_delivery = self.check_delivery(record)
            if not allow_delivery:
                return
        self.deliver(self.generate_mail(record, suppressed),
                     self.get_recipients(record))

    def emit_batch(self, records, reason):
        if reason not in ('escalation', 'group'):
            return MailHandler.emit_batch(self, records, reason)
        records = list(records)
        if not records:
            return

        trigger = records.pop(reason == 'escalation' and -1 or 0)
        suppressed = 0
        if self.record_limit is not None:
            suppressed, allow_delivery = self.check_delivery(trigger)
            if not allow_delivery:
                return

        trigger_mail = self.generate_mail(trigger, suppressed)
        related = [self.format_related_record(record)
                   for record in records]

        self.deliver(self.collapse_mails(trigger_mail, related, reason),
                     self.get_recipients(trigger))


class GMailHandler(MailHandler):
    """
    A customized mail handler class for sending emails via GMail (or Google Apps mail)::

       handler = GMailHandler("my_user@gmail.com", "mypassword", ["to_user@some_mail.com"], ...) # other arguments same as MailHandler

    .. versionadded:: 0.6.0
    """

    def __init__(self, account_id, password, recipients, **kw):
        super(GMailHandler, self).__init__(
            account_id, recipients, secure=(), server_addr=("smtp.gmail.com", 587),
            credentials=(account_id, password), **kw)


class SyslogHandler(Handler, StringFormatterHandlerMixin):
    """A handler class which sends formatted logging records to a
    syslog server.  By default it will send to it via unix socket.
    """
    default_format_string = SYSLOG_FORMAT_STRING

    # priorities
    LOG_EMERG     = 0       #  system is unusable
    LOG_ALERT     = 1       #  action must be taken immediately
    LOG_CRIT      = 2       #  critical conditions
    LOG_ERR       = 3       #  error conditions
    LOG_WARNING   = 4       #  warning conditions
    LOG_NOTICE    = 5       #  normal but significant condition
    LOG_INFO      = 6       #  informational
    LOG_DEBUG     = 7       #  debug-level messages

    # facility codes
    LOG_KERN      = 0       #  kernel messages
    LOG_USER      = 1       #  random user-level messages
    LOG_MAIL      = 2       #  mail system
    LOG_DAEMON    = 3       #  system daemons
    LOG_AUTH      = 4       #  security/authorization messages
    LOG_SYSLOG    = 5       #  messages generated internally by syslogd
    LOG_LPR       = 6       #  line printer subsystem
    LOG_NEWS      = 7       #  network news subsystem
    LOG_UUCP      = 8       #  UUCP subsystem
    LOG_CRON      = 9       #  clock daemon
    LOG_AUTHPRIV  = 10      #  security/authorization messages (private)
    LOG_FTP       = 11      #  FTP daemon

    # other codes through 15 reserved for system use
    LOG_LOCAL0    = 16      #  reserved for local use
    LOG_LOCAL1    = 17      #  reserved for local use
    LOG_LOCAL2    = 18      #  reserved for local use
    LOG_LOCAL3    = 19      #  reserved for local use
    LOG_LOCAL4    = 20      #  reserved for local use
    LOG_LOCAL5    = 21      #  reserved for local use
    LOG_LOCAL6    = 22      #  reserved for local use
    LOG_LOCAL7    = 23      #  reserved for local use

    facility_names = {
        'auth':     LOG_AUTH,
        'authpriv': LOG_AUTHPRIV,
        'cron':     LOG_CRON,
        'daemon':   LOG_DAEMON,
        'ftp':      LOG_FTP,
        'kern':     LOG_KERN,
        'lpr':      LOG_LPR,
        'mail':     LOG_MAIL,
        'news':     LOG_NEWS,
        'syslog':   LOG_SYSLOG,
        'user':     LOG_USER,
        'uucp':     LOG_UUCP,
        'local0':   LOG_LOCAL0,
        'local1':   LOG_LOCAL1,
        'local2':   LOG_LOCAL2,
        'local3':   LOG_LOCAL3,
        'local4':   LOG_LOCAL4,
        'local5':   LOG_LOCAL5,
        'local6':   LOG_LOCAL6,
        'local7':   LOG_LOCAL7,
    }

    level_priority_map = {
        DEBUG:      LOG_DEBUG,
        INFO:       LOG_INFO,
        NOTICE:     LOG_NOTICE,
        WARNING:    LOG_WARNING,
        ERROR:      LOG_ERR,
        CRITICAL:   LOG_CRIT
    }

    def __init__(self, application_name=None, address=None,
                 facility='user', socktype=socket.SOCK_DGRAM,
                 level=NOTSET, format_string=None, filter=None,
                 bubble=False):
        Handler.__init__(self, level, filter, bubble)
        StringFormatterHandlerMixin.__init__(self, format_string)
        self.application_name = application_name

        if address is None:
            if sys.platform == 'darwin':
                address = '/var/run/syslog'
            else:
                address = '/dev/log'

        self.address = address
        self.facility = facility
        self.socktype = socktype

        if isinstance(address, string_types):
            self._connect_unixsocket()
        else:
            self._connect_netsocket()

    def _connect_unixsocket(self):
        self.unixsocket = True
        self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        try:
            self.socket.connect(self.address)
        except socket.error:
            self.socket.close()
            self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.socket.connect(self.address)

    def _connect_netsocket(self):
        self.unixsocket = False
        self.socket = socket.socket(socket.AF_INET, self.socktype)
        if self.socktype == socket.SOCK_STREAM:
            self.socket.connect(self.address)
            self.address = self.socket.getsockname()

    def encode_priority(self, record):
        facility = self.facility_names[self.facility]
        priority = self.level_priority_map.get(record.level,
                                               self.LOG_WARNING)
        return (facility << 3) | priority

    def emit(self, record):
        prefix = u('')
        if self.application_name is not None:
            prefix = self.application_name + u(':')
        self.send_to_socket((u('<%d>%s%s\x00') % (
            self.encode_priority(record),
            prefix,
            self.format(record)
        )).encode('utf-8'))

    def send_to_socket(self, data):
        if self.unixsocket:
            try:
                self.socket.send(data)
            except socket.error:
                self._connect_unixsocket()
                self.socket.send(data)
        elif self.socktype == socket.SOCK_DGRAM:
            # the flags are no longer optional on Python 3
            self.socket.sendto(data, 0, self.address)
        else:
            self.socket.sendall(data)

    def close(self):
        self.socket.close()


class NTEventLogHandler(Handler, StringFormatterHandlerMixin):
    """A handler that sends to the NT event log system."""
    dllname = None
    default_format_string = NTLOG_FORMAT_STRING

    def __init__(self, application_name, log_type='Application',
                 level=NOTSET, format_string=None, filter=None,
                 bubble=False):
        Handler.__init__(self, level, filter, bubble)
        StringFormatterHandlerMixin.__init__(self, format_string)

        if os.name != 'nt':
            raise RuntimeError('NTLogEventLogHandler requires a Windows '
                               'operating system.')

        try:
            import win32evtlogutil
            import win32evtlog
        except ImportError:
            raise RuntimeError('The pywin32 library is required '
                               'for the NTEventLogHandler.')

        self.application_name = application_name
        self._welu = win32evtlogutil
        dllname = self.dllname
        if not dllname:
            dllname = os.path.join(os.path.dirname(self._welu.__file__),
                                   '../win32service.pyd')
        self.log_type = log_type
        self._welu.AddSourceToRegistry(self.application_name, dllname,
                                       log_type)

        self._default_type = win32evtlog.EVENTLOG_INFORMATION_TYPE
        self._type_map = {
            DEBUG:      win32evtlog.EVENTLOG_INFORMATION_TYPE,
            INFO:       win32evtlog.EVENTLOG_INFORMATION_TYPE,
            NOTICE:     win32evtlog.EVENTLOG_INFORMATION_TYPE,
            WARNING:    win32evtlog.EVENTLOG_WARNING_TYPE,
            ERROR:      win32evtlog.EVENTLOG_ERROR_TYPE,
            CRITICAL:   win32evtlog.EVENTLOG_ERROR_TYPE
        }

    def unregister_logger(self):
        """Removes the application binding from the registry.  If you call
        this, the log viewer will no longer be able to provide any
        information about the message.
        """
        self._welu.RemoveSourceFromRegistry(self.application_name,
                                            self.log_type)

    def get_event_type(self, record):
        return self._type_map.get(record.level, self._default_type)

    def get_event_category(self, record):
        return 0

    def get_message_id(self, record):
        return 1

    def emit(self, record):
        id = self.get_message_id(record)
        cat = self.get_event_category(record)
        type = self.get_event_type(record)
        self._welu.ReportEvent(self.application_name, id, cat, type,
                               [self.format(record)])


class FingersCrossedHandler(Handler):
    """This handler wraps another handler and will log everything in
    memory until a certain level (`action_level`, defaults to `ERROR`)
    is exceeded.  When that happens the fingers crossed handler will
    activate forever and log all buffered records as well as records
    yet to come into another handled which was passed to the constructor.

    Alternatively it's also possible to pass a factory function to the
    constructor instead of a handler.  That factory is then called with
    the triggering log entry and the finger crossed handler to create
    a handler which is then cached.

    The idea of this handler is to enable debugging of live systems.  For
    example it might happen that code works perfectly fine 99% of the time,
    but then some exception happens.  But the error that caused the
    exception alone might not be the interesting bit, the interesting
    information were the warnings that lead to the error.

    Here a setup that enables this for a web application::

        from logbook import FileHandler
        from logbook import FingersCrossedHandler

        def issue_logging():
            def factory(record, handler):
                return FileHandler('/var/log/app/issue-%s.log' % record.time)
            return FingersCrossedHandler(factory)

        def application(environ, start_response):
            with issue_logging():
                return the_actual_wsgi_application(environ, start_response)

    Whenever an error occours, a new file in ``/var/log/app`` is created
    with all the logging calls that lead up to the error up to the point
    where the `with` block is exited.

    Please keep in mind that the :class:`~logbook.FingersCrossedHandler`
    handler is a one-time handler.  Once triggered, it will not reset.  Because
    of that you will have to re-create it whenever you bind it.  In this case
    the handler is created when it's bound to the thread.

    Due to how the handler is implemented, the filter, bubble and level
    flags of the wrapped handler are ignored.

    .. versionchanged:: 0.3

    The default behaviour is to buffer up records and then invoke another
    handler when a severity theshold was reached with the buffer emitting.
    This now enables this logger to be properly used with the
    :class:`~logbook.MailHandler`.  You will now only get one mail for
    each bfufered record.  However once the threshold was reached you would
    still get a mail for each record which is why the `reset` flag was added.

    When set to `True`, the handler will instantly reset to the untriggered
    state and start buffering again::

        handler = FingersCrossedHandler(MailHandler(...),
                                        buffer_size=10,
                                        reset=True)

    .. versionadded:: 0.3
       The `reset` flag was added.
    """

    #: the reason to be used for the batch emit.  The default is
    #: ``'escalation'``.
    #:
    #: .. versionadded:: 0.3
    batch_emit_reason = 'escalation'

    def __init__(self, handler, action_level=ERROR, buffer_size=0,
                 pull_information=True, reset=False, filter=None,
                 bubble=False):
        Handler.__init__(self, NOTSET, filter, bubble)
        self.lock = Lock()
        self._level = action_level
        if isinstance(handler, Handler):
            self._handler = handler
            self._handler_factory = None
        else:
            self._handler = None
            self._handler_factory = handler
        #: the buffered records of the handler.  Once the action is triggered
        #: (:attr:`triggered`) this list will be None.  This attribute can
        #: be helpful for the handler factory function to select a proper
        #: filename (for example time of first log record)
        self.buffered_records = deque()
        #: the maximum number of entries in the buffer.  If this is exhausted
        #: the oldest entries will be discarded to make place for new ones
        self.buffer_size = buffer_size
        self._buffer_full = False
        self._pull_information = pull_information
        self._action_triggered = False
        self._reset = reset

    def close(self):
        if self._handler is not None:
            self._handler.close()

    def enqueue(self, record):
        if self._pull_information:
            record.pull_information()
        if self._action_triggered:
            self._handler.emit(record)
        else:
            self.buffered_records.append(record)
            if self._buffer_full:
                self.buffered_records.popleft()
            elif self.buffer_size and \
                 len(self.buffered_records) >= self.buffer_size:
                self._buffer_full = True
            return record.level >= self._level
        return False

    def rollover(self, record):
        if self._handler is None:
            self._handler = self._handler_factory(record, self)
        self._handler.emit_batch(iter(self.buffered_records), 'escalation')
        self.buffered_records.clear()
        self._action_triggered = not self._reset

    @property
    def triggered(self):
        """This attribute is `True` when the action was triggered.  From
        this point onwards the finger crossed handler transparently
        forwards all log records to the inner handler.  If the handler resets
        itself this will always be `False`.
        """
        return self._action_triggered

    def emit(self, record):
        self.lock.acquire()
        try:
            if self.enqueue(record):
                self.rollover(record)
        finally:
            self.lock.release()


class GroupHandler(WrapperHandler):
    """A handler that buffers all messages until it is popped again and then
    forwards all messages to another handler.  This is useful if you for
    example have an application that does computations and only a result
    mail is required.  A group handler makes sure that only one mail is sent
    and not multiple.  Some other handles might support this as well, though
    currently none of the builtins do.

    Example::

        with GroupHandler(MailHandler(...)):
            # everything here ends up in the mail

    The :class:`GroupHandler` is implemented as a :class:`WrapperHandler`
    thus forwarding all attributes of the wrapper handler.

    Notice that this handler really only emit the records when the handler
    is popped from the stack.

    .. versionadded:: 0.3
    """
    _direct_attrs = frozenset(['handler', 'pull_information',
                               'buffered_records'])

    def __init__(self, handler, pull_information=True):
        WrapperHandler.__init__(self, handler)
        self.pull_information = pull_information
        self.buffered_records = []

    def rollover(self):
        self.handler.emit_batch(self.buffered_records, 'group')
        self.buffered_records = []

    def pop_application(self):
        Handler.pop_application(self)
        self.rollover()

    def pop_thread(self):
        Handler.pop_thread(self)
        self.rollover()

    def emit(self, record):
        if self.pull_information:
            record.pull_information()
        self.buffered_records.append(record)

########NEW FILE########
__FILENAME__ = helpers
# -*- coding: utf-8 -*-
"""
    logbook.helpers
    ~~~~~~~~~~~~~~~

    Various helper functions

    :copyright: (c) 2010 by Armin Ronacher, Georg Brandl.
    :license: BSD, see LICENSE for more details.
"""
import os
import re
import sys
import errno
import time
import random
from datetime import datetime, timedelta

PY2 = sys.version_info[0] == 2

if PY2:
    import __builtin__ as _builtins
else:
    import builtins as _builtins

try:
    import json
except ImportError:
    import simplejson as json

if PY2:
    from cStringIO import StringIO
    iteritems = dict.iteritems
    from itertools import izip as zip
    xrange = _builtins.xrange
else:
    from io import StringIO
    zip = _builtins.zip
    xrange = range
    iteritems = dict.items

_IDENTITY = lambda obj: obj

if PY2:
    def u(s):
        return unicode(s, "unicode_escape")
else:
    u = _IDENTITY

if PY2:
    integer_types = (int, long)
    string_types = (basestring,)
else:
    integer_types = (int,)
    string_types = (str,)

if PY2:
    import httplib as http_client
else:
    from http import client as http_client

if PY2:
    #Yucky, but apparently that's the only way to do this
    exec("""
def reraise(tp, value, tb=None):
    raise tp, value, tb
""", locals(), globals())
else:
    def reraise(tp, value, tb=None):
        if value.__traceback__ is not tb:
            raise value.with_traceback(tb)
        raise value


# this regexp also matches incompatible dates like 20070101 because
# some libraries (like the python xmlrpclib modules) use this
_iso8601_re = re.compile(
    # date
    r'(\d{4})(?:-?(\d{2})(?:-?(\d{2}))?)?'
    # time
    r'(?:T(\d{2}):(\d{2})(?::(\d{2}(?:\.\d+)?))?(Z|[+-]\d{2}:\d{2})?)?$'
)
_missing = object()
if PY2:
    def b(x): return x
    def _is_text_stream(x): return True
else:
    import io
    def b(x): return x.encode('ascii')
    def _is_text_stream(stream): return isinstance(stream, io.TextIOBase)


can_rename_open_file = False
if os.name == 'nt': # pragma: no cover
    _rename = lambda src, dst: False
    _rename_atomic = lambda src, dst: False

    try:
        import ctypes

        _MOVEFILE_REPLACE_EXISTING = 0x1
        _MOVEFILE_WRITE_THROUGH = 0x8
        _MoveFileEx = ctypes.windll.kernel32.MoveFileExW

        def _rename(src, dst):
            if PY2:
                if not isinstance(src, unicode):
                    src = unicode(src, sys.getfilesystemencoding())
                if not isinstance(dst, unicode):
                    dst = unicode(dst, sys.getfilesystemencoding())
            if _rename_atomic(src, dst):
                return True
            retry = 0
            rv = False
            while not rv and retry < 100:
                rv = _MoveFileEx(src, dst, _MOVEFILE_REPLACE_EXISTING |
                                           _MOVEFILE_WRITE_THROUGH)
                if not rv:
                    time.sleep(0.001)
                    retry += 1
            return rv

        # new in Vista and Windows Server 2008
        _CreateTransaction = ctypes.windll.ktmw32.CreateTransaction
        _CommitTransaction = ctypes.windll.ktmw32.CommitTransaction
        _MoveFileTransacted = ctypes.windll.kernel32.MoveFileTransactedW
        _CloseHandle = ctypes.windll.kernel32.CloseHandle
        can_rename_open_file = True

        def _rename_atomic(src, dst):
            ta = _CreateTransaction(None, 0, 0, 0, 0, 1000, 'Logbook rename')
            if ta == -1:
                return False
            try:
                retry = 0
                rv = False
                while not rv and retry < 100:
                    rv = _MoveFileTransacted(src, dst, None, None,
                                             _MOVEFILE_REPLACE_EXISTING |
                                             _MOVEFILE_WRITE_THROUGH, ta)
                    if rv:
                        rv = _CommitTransaction(ta)
                        break
                    else:
                        time.sleep(0.001)
                        retry += 1
                return rv
            finally:
                _CloseHandle(ta)
    except Exception:
        pass

    def rename(src, dst):
        # Try atomic or pseudo-atomic rename
        if _rename(src, dst):
            return
        # Fall back to "move away and replace"
        try:
            os.rename(src, dst)
        except OSError:
            e = sys.exc_info()[1]
            if e.errno != errno.EEXIST:
                raise
            old = "%s-%08x" % (dst, random.randint(0, sys.maxint))
            os.rename(dst, old)
            os.rename(src, dst)
            try:
                os.unlink(old)
            except Exception:
                pass
else:
    rename = os.rename
    can_rename_open_file = True

_JSON_SIMPLE_TYPES = (bool, float) + integer_types + string_types

def to_safe_json(data):
    """Makes a data structure safe for JSON silently discarding invalid
    objects from nested structures.  This also converts dates.
    """
    def _convert(obj):
        if obj is None:
            return None
        elif PY2 and isinstance(obj, str):
            return obj.decode('utf-8', 'replace')
        elif isinstance(obj, _JSON_SIMPLE_TYPES):
            return obj
        elif isinstance(obj, datetime):
            return format_iso8601(obj)
        elif isinstance(obj, list):
            return [_convert(x) for x in obj]
        elif isinstance(obj, tuple):
            return tuple(_convert(x) for x in obj)
        elif isinstance(obj, dict):
            rv = {}
            for key, value in iteritems(obj):
                if not isinstance(key, string_types):
                    key = str(key)
                if not is_unicode(key):
                    key = u(key)
                rv[key] = _convert(value)
            return rv
    return _convert(data)


def format_iso8601(d=None):
    """Returns a date in iso8601 format."""
    if d is None:
        d = datetime.utcnow()
    rv = d.strftime('%Y-%m-%dT%H:%M:%S')
    if d.microsecond:
        rv += '.' + str(d.microsecond)
    return rv + 'Z'


def parse_iso8601(value):
    """Parse an iso8601 date into a datetime object.  The timezone is
    normalized to UTC.
    """
    m = _iso8601_re.match(value)
    if m is None:
        raise ValueError('not a valid iso8601 date value')

    groups = m.groups()
    args = []
    for group in groups[:-2]:
        if group is not None:
            group = int(group)
        args.append(group)
    seconds = groups[-2]
    if seconds is not None:
        if '.' in seconds:
            sec, usec = seconds.split('.')
            args.append(int(sec))
            args.append(int(usec.ljust(6, '0')))
        else:
            args.append(int(seconds))

    rv = datetime(*args)
    tz = groups[-1]
    if tz and tz != 'Z':
        args = [int(x) for x in tz[1:].split(':')]
        delta = timedelta(hours=args[0], minutes=args[1])
        if tz[0] == '+':
            rv -= delta
        else:
            rv += delta

    return rv


def get_application_name():
    if not sys.argv or not sys.argv[0]:
        return 'Python'
    return os.path.basename(sys.argv[0]).title()


class cached_property(object):
    """A property that is lazily calculated and then cached."""

    def __init__(self, func, name=None, doc=None):
        self.__name__ = name or func.__name__
        self.__module__ = func.__module__
        self.__doc__ = doc or func.__doc__
        self.func = func

    def __get__(self, obj, type=None):
        if obj is None:
            return self
        value = obj.__dict__.get(self.__name__, _missing)
        if value is _missing:
            value = self.func(obj)
            obj.__dict__[self.__name__] = value
        return value

def get_iterator_next_method(it):
    return lambda: next(it)

# python 2 support functions and aliases
def is_unicode(x):
    if PY2:
        return isinstance(x, unicode)
    return isinstance(x, str)

########NEW FILE########
__FILENAME__ = more
# -*- coding: utf-8 -*-
"""
    logbook.more
    ~~~~~~~~~~~~

    Fancy stuff for logbook.

    :copyright: (c) 2010 by Armin Ronacher, Georg Brandl.
    :license: BSD, see LICENSE for more details.
"""
import re
import os
from collections import defaultdict
from cgi import parse_qsl

from logbook.base import RecordDispatcher, dispatch_record, NOTSET, ERROR, NOTICE
from logbook.handlers import Handler, StringFormatter, \
     StringFormatterHandlerMixin, StderrHandler
from logbook._termcolors import colorize
from logbook.helpers import PY2, string_types, iteritems, u

from logbook.ticketing import TicketingHandler as DatabaseHandler
from logbook.ticketing import BackendBase

if PY2:
    from urllib import urlencode
else:
    from urllib.parse import urlencode

_ws_re = re.compile(r'(\s+)(?u)')
TWITTER_FORMAT_STRING = \
u('[{record.channel}] {record.level_name}: {record.message}')
TWITTER_ACCESS_TOKEN_URL = 'https://twitter.com/oauth/access_token'
NEW_TWEET_URL = 'https://api.twitter.com/1/statuses/update.json'


class CouchDBBackend(BackendBase):
    """Implements a backend that writes into a CouchDB database.
    """
    def setup_backend(self):
        from couchdb import Server

        uri = self.options.pop('uri', u(''))
        couch = Server(uri)
        db_name = self.options.pop('db')
        self.database = couch[db_name]

    def record_ticket(self, record, data, hash, app_id):
        """Records a log record as ticket.
        """
        db = self.database

        ticket = record.to_dict()
        ticket["time"] = ticket["time"].isoformat() + "Z"
        ticket_id, _ = db.save(ticket)

        db.save(ticket)


class TwitterFormatter(StringFormatter):
    """Works like the standard string formatter and is used by the
    :class:`TwitterHandler` unless changed.
    """
    max_length = 140

    def format_exception(self, record):
        return u('%s: %s') % (record.exception_shortname,
                              record.exception_message)

    def __call__(self, record, handler):
        formatted = StringFormatter.__call__(self, record, handler)
        rv = []
        length = 0
        for piece in _ws_re.split(formatted):
            length += len(piece)
            if length > self.max_length:
                if length - len(piece) < self.max_length:
                    rv.append(u('…'))
                break
            rv.append(piece)
        return u('').join(rv)


class TaggingLogger(RecordDispatcher):
    """A logger that attaches a tag to each record.  This is an alternative
    record dispatcher that does not use levels but tags to keep log
    records apart.  It is constructed with a descriptive name and at least
    one tag.  The tags are up for you to define::

        logger = TaggingLogger('My Logger', ['info', 'warning'])

    For each tag defined that way, a method appears on the logger with
    that name::

        logger.info('This is a info message')

    To dispatch to different handlers based on tags you can use the
    :class:`TaggingHandler`.

    The tags themselves are stored as list named ``'tags'`` in the
    :attr:`~logbook.LogRecord.extra` dictionary.
    """

    def __init__(self, name=None, tags=None):
        RecordDispatcher.__init__(self, name)
        # create a method for each tag named
        list(setattr(self, tag, lambda msg, *args, **kwargs:
            self.log(tag, msg, *args, **kwargs)) for tag in (tags or ()))

    def log(self, tags, msg, *args, **kwargs):
        if isinstance(tags, string_types):
            tags = [tags]
        exc_info = kwargs.pop('exc_info', None)
        extra = kwargs.pop('extra', {})
        extra['tags'] = list(tags)
        return self.make_record_and_handle(NOTSET, msg, args, kwargs,
                                           exc_info, extra)


class TaggingHandler(Handler):
    """A handler that logs for tags and dispatches based on those.

    Example::

        import logbook
        from logbook.more import TaggingHandler

        handler = TaggingHandler(dict(
            info=OneHandler(),
            warning=AnotherHandler()
        ))
    """

    def __init__(self, handlers, filter=None, bubble=False):
        Handler.__init__(self, NOTSET, filter, bubble)
        assert isinstance(handlers, dict)
        self._handlers = dict(
            (tag, isinstance(handler, Handler) and [handler] or handler)
            for (tag, handler) in iteritems(handlers))

    def emit(self, record):
        for tag in record.extra.get('tags', ()):
            for handler in self._handlers.get(tag, ()):
                handler.handle(record)


class TwitterHandler(Handler, StringFormatterHandlerMixin):
    """A handler that logs to twitter.  Requires that you sign up an
    application on twitter and request xauth support.  Furthermore the
    oauth2 library has to be installed.

    If you don't want to register your own application and request xauth
    credentials, there are a couple of leaked consumer key and secret
    pairs from application explicitly whitelisted at Twitter
    (`leaked secrets <http://bit.ly/leaked-secrets>`_).
    """
    default_format_string = TWITTER_FORMAT_STRING
    formatter_class = TwitterFormatter

    def __init__(self, consumer_key, consumer_secret, username,
                 password, level=NOTSET, format_string=None, filter=None,
                 bubble=False):
        Handler.__init__(self, level, filter, bubble)
        StringFormatterHandlerMixin.__init__(self, format_string)
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.username = username
        self.password = password

        try:
            import oauth2
        except ImportError:
            raise RuntimeError('The python-oauth2 library is required for '
                               'the TwitterHandler.')

        self._oauth = oauth2
        self._oauth_token = None
        self._oauth_token_secret = None
        self._consumer = oauth2.Consumer(consumer_key,
                                         consumer_secret)
        self._client = oauth2.Client(self._consumer)

    def get_oauth_token(self):
        """Returns the oauth access token."""
        if self._oauth_token is None:
            resp, content = self._client.request(
                TWITTER_ACCESS_TOKEN_URL + '?', 'POST',
                body=urlencode({
                    'x_auth_username':  self.username.encode('utf-8'),
                    'x_auth_password':  self.password.encode('utf-8'),
                    'x_auth_mode':      'client_auth'
                }),
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )
            if resp['status'] != '200':
                raise RuntimeError('unable to login to Twitter')
            data = dict(parse_qsl(content))
            self._oauth_token = data['oauth_token']
            self._oauth_token_secret = data['oauth_token_secret']
        return self._oauth.Token(self._oauth_token,
                                 self._oauth_token_secret)

    def make_client(self):
        """Creates a new oauth client auth a new access token."""
        return self._oauth.Client(self._consumer, self.get_oauth_token())

    def tweet(self, status):
        """Tweets a given status.  Status must not exceed 140 chars."""
        client = self.make_client()
        resp, content = client.request(NEW_TWEET_URL, 'POST',
            body=urlencode({'status': status.encode('utf-8')}),
            headers={'Content-Type': 'application/x-www-form-urlencoded'})
        return resp['status'] == '200'

    def emit(self, record):
        self.tweet(self.format(record))


class JinjaFormatter(object):
    """A formatter object that makes it easy to format using a Jinja 2
    template instead of a format string.
    """

    def __init__(self, template):
        try:
            from jinja2 import Template
        except ImportError:
            raise RuntimeError('The jinja2 library is required for '
                               'the JinjaFormatter.')
        self.template = Template(template)

    def __call__(self, record, handler):
        return self.template.render(record=record, handler=handler)


class ExternalApplicationHandler(Handler):
    """This handler invokes an external application to send parts of
    the log record to.  The constructor takes a list of arguments that
    are passed to another application where each of the arguments is a
    format string, and optionally a format string for data that is
    passed to stdin.

    For example it can be used to invoke the ``say`` command on OS X::

        from logbook.more import ExternalApplicationHandler
        say_handler = ExternalApplicationHandler(['say', '{record.message}'])

    Note that the above example is blocking until ``say`` finished, so it's
    recommended to combine this handler with the
    :class:`logbook.ThreadedWrapperHandler` to move the execution into
    a background thread.

    .. versionadded:: 0.3
    """

    def __init__(self, arguments, stdin_format=None,
                 encoding='utf-8', level=NOTSET, filter=None,
                 bubble=False):
        Handler.__init__(self, level, filter, bubble)
        self.encoding = encoding
        self._arguments = list(arguments)
        if stdin_format is not None:
            stdin_format = stdin_format
        self._stdin_format = stdin_format
        import subprocess
        self._subprocess = subprocess

    def emit(self, record):
        args = [arg.format(record=record).encode(self.encoding)
                for arg in self._arguments]
        if self._stdin_format is not None:
            stdin_data = self._stdin_format.format(record=record) \
                                           .encode(self.encoding)
            stdin = self._subprocess.PIPE
        else:
            stdin = None
        c = self._subprocess.Popen(args, stdin=stdin)
        if stdin is not None:
            c.communicate(stdin_data)
        c.wait()


class ColorizingStreamHandlerMixin(object):
    """A mixin class that does colorizing.

    .. versionadded:: 0.3
    """

    def should_colorize(self, record):
        """Returns `True` if colorizing should be applied to this
        record.  The default implementation returns `True` if the
        stream is a tty and we are not executing on windows.
        """
        if os.name == 'nt':
            return False
        isatty = getattr(self.stream, 'isatty', None)
        return isatty and isatty()

    def get_color(self, record):
        """Returns the color for this record."""
        if record.level >= ERROR:
            return 'red'
        elif record.level >= NOTICE:
            return 'yellow'
        return 'lightgray'

    def format_and_encode(self, record):
        rv = super(ColorizingStreamHandlerMixin, self) \
                .format_and_encode(record)
        if self.should_colorize(record):
            color = self.get_color(record)
            if color:
                rv = colorize(color, rv)
        return rv


class ColorizedStderrHandler(ColorizingStreamHandlerMixin, StderrHandler):
    """A colorizing stream handler that writes to stderr.  It will only
    colorize if a terminal was detected.  Note that this handler does
    not colorize on Windows systems.

    .. versionadded:: 0.3
    """


# backwards compat.  Should go away in some future releases
from logbook.handlers import FingersCrossedHandler as \
     FingersCrossedHandlerBase
class FingersCrossedHandler(FingersCrossedHandlerBase):
    def __init__(self, *args, **kwargs):
        FingersCrossedHandlerBase.__init__(self, *args, **kwargs)
        from warnings import warn
        warn(PendingDeprecationWarning('fingers crossed handler changed '
            'location.  It\'s now a core component of Logbook.'))


class ExceptionHandler(Handler, StringFormatterHandlerMixin):
    """An exception handler which raises exceptions of the given `exc_type`.
    This is especially useful if you set a specific error `level` e.g. to treat
    warnings as exceptions::

        from logbook.more import ExceptionHandler

        class ApplicationWarning(Exception):
            pass

        exc_handler = ExceptionHandler(ApplicationWarning, level='WARNING')

    .. versionadded:: 0.3
    """
    def __init__(self, exc_type, level=NOTSET, format_string=None,
                 filter=None, bubble=False):
        Handler.__init__(self, level, filter, bubble)
        StringFormatterHandlerMixin.__init__(self, format_string)
        self.exc_type = exc_type

    def handle(self, record):
        if self.should_handle(record):
            raise self.exc_type(self.format(record))
        return False

class DedupHandler(Handler):
    """A handler that deduplicates log messages.

    It emits each unique log record once, along with the number of times it was emitted.
    Example:::

        with logbook.more.DedupHandler():
            logbook.error('foo')
            logbook.error('bar')
            logbook.error('foo')

    The expected output:::

       message repeated 2 times: foo
       message repeated 1 times: bar
    """
    def __init__(self, format_string='message repeated {count} times: {message}', *args, **kwargs):
        Handler.__init__(self, bubble=False, *args, **kwargs)
        self._format_string = format_string
        self.clear()
        
    def clear(self):
        self._message_to_count = defaultdict(int)
        self._unique_ordered_records = []

    def pop_application(self):
        Handler.pop_application(self)
        self.flush()

    def pop_thread(self):
        Handler.pop_thread(self)
        self.flush()

    def handle(self, record):
        if not record.message in self._message_to_count:
            self._unique_ordered_records.append(record)
        self._message_to_count[record.message] += 1
        return True

    def flush(self):
        for record in self._unique_ordered_records:
            record.message = self._format_string.format(message=record.message, count=self._message_to_count[record.message])
            # record.dispatcher is the logger who created the message, it's sometimes supressed (by logbook.info for example)
            dispatch = record.dispatcher.call_handlers if record.dispatcher is not None else dispatch_record
            dispatch(record)
        self.clear()


########NEW FILE########
__FILENAME__ = notifiers
# -*- coding: utf-8 -*-
"""
    logbook.notifiers
    ~~~~~~~~~~~~~~~~~

    System notify handlers for OSX and Linux.

    :copyright: (c) 2010 by Armin Ronacher, Christopher Grebs.
    :license: BSD, see LICENSE for more details.
"""
import os
import sys
import base64
from time import time

from logbook.base import NOTSET, ERROR, WARNING
from logbook.handlers import Handler, LimitingHandlerMixin
from logbook.helpers import get_application_name, PY2, http_client

if PY2:
    from urllib import urlencode
else:
    from urllib.parse import urlencode

def create_notification_handler(application_name=None, level=NOTSET, icon=None):
    """Creates a handler perfectly fit the current platform.  On Linux
    systems this creates a :class:`LibNotifyHandler`, on OS X systems it
    will create a :class:`GrowlHandler`.
    """
    if sys.platform == 'darwin':
        return GrowlHandler(application_name, level=level, icon=icon)
    return LibNotifyHandler(application_name, level=level, icon=icon)


class NotificationBaseHandler(Handler, LimitingHandlerMixin):
    """Baseclass for notification handlers."""

    def __init__(self, application_name=None, record_limit=None,
                 record_delta=None, level=NOTSET, filter=None, bubble=False):
        Handler.__init__(self, level, filter, bubble)
        LimitingHandlerMixin.__init__(self, record_limit, record_delta)
        if application_name is None:
            application_name = get_application_name()
        self.application_name = application_name

    def make_title(self, record):
        """Called to get the title from the record."""
        return u('%s: %s') % (record.channel, record.level_name.title())

    def make_text(self, record):
        """Called to get the text of the record."""
        return record.message


class GrowlHandler(NotificationBaseHandler):
    """A handler that dispatches to Growl.  Requires that either growl-py or
    py-Growl are installed.
    """

    def __init__(self, application_name=None, icon=None, host=None,
                 password=None, record_limit=None, record_delta=None,
                 level=NOTSET, filter=None, bubble=False):
        NotificationBaseHandler.__init__(self, application_name, record_limit,
                                         record_delta, level, filter, bubble)

        # growl is using the deprecated md5 module, but we really don't need
        # to see that deprecation warning
        from warnings import filterwarnings
        filterwarnings(module='Growl', category=DeprecationWarning,
                       action='ignore')

        try:
            import Growl
            self._growl = Growl
        except ImportError:
            raise RuntimeError('The growl module is not available.  You have '
                               'to install either growl-py or py-Growl to '
                               'use the GrowlHandler.')

        if icon is not None:
            if not os.path.isfile(icon):
                raise IOError('Filename to an icon expected.')
            icon = self._growl.Image.imageFromPath(icon)
        else:
            try:
                icon = self._growl.Image.imageWithIconForCurrentApplication()
            except TypeError:
                icon = None

        self._notifier = self._growl.GrowlNotifier(
            applicationName=self.application_name,
            applicationIcon=icon,
            notifications=['Notset', 'Debug', 'Info', 'Notice', 'Warning',
                           'Error', 'Critical'],
            hostname=host,
            password=password
        )
        self._notifier.register()

    def is_sticky(self, record):
        """Returns `True` if the sticky flag should be set for this record.
        The default implementation marks errors and criticals sticky.
        """
        return record.level >= ERROR

    def get_priority(self, record):
        """Returns the priority flag for Growl.  Errors and criticals are
        get highest priority (2), warnings get higher priority (1) and the
        rest gets 0.  Growl allows values between -2 and 2.
        """
        if record.level >= ERROR:
            return 2
        elif record.level == WARNING:
            return 1
        return 0

    def emit(self, record):
        if not self.check_delivery(record)[1]:
            return
        self._notifier.notify(record.level_name.title(),
                              self.make_title(record),
                              self.make_text(record),
                              sticky=self.is_sticky(record),
                              priority=self.get_priority(record))


class LibNotifyHandler(NotificationBaseHandler):
    """A handler that dispatches to libnotify.  Requires pynotify installed.
    If `no_init` is set to `True` the initialization of libnotify is skipped.
    """

    def __init__(self, application_name=None, icon=None, no_init=False,
                 record_limit=None, record_delta=None, level=NOTSET,
                 filter=None, bubble=False):
        NotificationBaseHandler.__init__(self, application_name, record_limit,
                                         record_delta, level, filter, bubble)

        try:
            import pynotify
            self._pynotify = pynotify
        except ImportError:
            raise RuntimeError('The pynotify library is required for '
                               'the LibNotifyHandler.')

        self.icon = icon
        if not no_init:
            pynotify.init(self.application_name)

    def set_notifier_icon(self, notifier, icon):
        """Used to attach an icon on a notifier object."""
        try:
            from gtk import gdk
        except ImportError:
            #TODO: raise a warning?
            raise RuntimeError('The gtk.gdk module is required to set an icon.')

        if icon is not None:
            if not isinstance(icon, gdk.Pixbuf):
                icon = gdk.pixbuf_new_from_file(icon)
            notifier.set_icon_from_pixbuf(icon)

    def get_expires(self, record):
        """Returns either EXPIRES_DEFAULT or EXPIRES_NEVER for this record.
        The default implementation marks errors and criticals as EXPIRES_NEVER.
        """
        pn = self._pynotify
        return pn.EXPIRES_NEVER if record.level >= ERROR else pn.EXPIRES_DEFAULT

    def get_urgency(self, record):
        """Returns the urgency flag for pynotify.  Errors and criticals are
        get highest urgency (CRITICAL), warnings get higher priority (NORMAL)
        and the rest gets LOW.
        """
        pn = self._pynotify
        if record.level >= ERROR:
            return pn.URGENCY_CRITICAL
        elif record.level == WARNING:
            return pn.URGENCY_NORMAL
        return pn.URGENCY_LOW

    def emit(self, record):
        if not self.check_delivery(record)[1]:
            return
        notifier = self._pynotify.Notification(self.make_title(record),
                                               self.make_text(record))
        notifier.set_urgency(self.get_urgency(record))
        notifier.set_timeout(self.get_expires(record))
        self.set_notifier_icon(notifier, self.icon)
        notifier.show()


class BoxcarHandler(NotificationBaseHandler):
    """Sends notifications to boxcar.io.  Can be forwarded to your iPhone or
    other compatible device.
    """
    api_url = 'https://boxcar.io/notifications/'

    def __init__(self, email, password, record_limit=None, record_delta=None,
                 level=NOTSET, filter=None, bubble=False):
        NotificationBaseHandler.__init__(self, None, record_limit, record_delta,
                                         level, filter, bubble)
        self.email = email
        self.password = password

    def get_screen_name(self, record):
        """Returns the value of the screen name field."""
        return record.level_name.title()

    def emit(self, record):
        if not self.check_delivery(record)[1]:
            return
        body = urlencode({
            'notification[from_screen_name]':
                self.get_screen_name(record).encode('utf-8'),
            'notification[message]':
                self.make_text(record).encode('utf-8'),
            'notification[from_remote_service_id]': str(int(time() * 100))
        })
        con = http_client.HTTPSConnection('boxcar.io')
        con.request('POST', '/notifications/', headers={
            'Authorization': 'Basic ' +
                base64.b64encode((u('%s:%s') %
                    (self.email, self.password)).encode('utf-8')).strip(),
        }, body=body)
        con.close()


class NotifoHandler(NotificationBaseHandler):
    """Sends notifications to notifo.com.  Can be forwarded to your Desktop,
    iPhone, or other compatible device.
    """

    def __init__(self, application_name=None, username=None, secret=None,
                 record_limit=None, record_delta=None, level=NOTSET, filter=None,
                 bubble=False, hide_level=False):
        try:
            import notifo
        except ImportError:
            raise RuntimeError(
                'The notifo module is not available.  You have '
                'to install notifo to use the NotifoHandler.'
            )
        NotificationBaseHandler.__init__(self, None, record_limit, record_delta,
                                         level, filter, bubble)
        self._notifo = notifo
        self.application_name = application_name
        self.username = username
        self.secret = secret
        self.hide_level = hide_level


    def emit(self, record):

        if self.hide_level:
            _level_name = None
        else:
            _level_name = self.level_name

        self._notifo.send_notification(self.username, self.secret, None,
                                       record.message, self.application_name,
                                       _level_name, None)

########NEW FILE########
__FILENAME__ = queues
# -*- coding: utf-8 -*-
"""
    logbook.queues
    ~~~~~~~~~~~~~~

    This module implements queue backends.

    :copyright: (c) 2010 by Armin Ronacher, Georg Brandl.
    :license: BSD, see LICENSE for more details.
"""
import json
import threading
from threading import Thread, Lock
import platform
from logbook.base import NOTSET, LogRecord, dispatch_record
from logbook.handlers import Handler, WrapperHandler
from logbook.helpers import PY2, u

if PY2:
    from Queue import Empty, Queue as ThreadQueue
else:
    from queue import Empty, Queue as ThreadQueue


class RedisHandler(Handler):
    """A handler that sends log messages to a Redis instance.

    It publishes each record as json dump. Requires redis module.

    To receive such records you need to have a running instance of Redis.

    Example setup::

        handler = RedisHandler('http://127.0.0.1', port='9200', key='redis')

    If your Redis instance is password protected, you can securely connect passing
    your password when creating a RedisHandler object.

    Example::

        handler = RedisHandler(password='your_redis_password')

    More info about the default buffer size: wp.me/p3tYJu-3b
    """
    def __init__(self, host='127.0.0.1', port=6379, key='redis', extra_fields={},
                flush_threshold=128, flush_time=1, level=NOTSET, filter=None,
                password=False, bubble=True, context=None):
        Handler.__init__(self, level, filter, bubble)
        try:
            import redis
            from redis import ResponseError
        except ImportError:
            raise RuntimeError('The redis library is required for '
                               'the RedisHandler')

        self.redis = redis.Redis(host=host, port=port, password=password, decode_responses=True)
        try:
            self.redis.ping()
        except ResponseError:
            raise ResponseError('The password provided is apparently incorrect')
        self.key = key
        self.extra_fields = extra_fields
        self.flush_threshold = flush_threshold
        self.queue = []
        self.lock = Lock()

        #Set up a thread that flushes the queue every specified seconds
        self._stop_event = threading.Event()
        self._flushing_t = threading.Thread(target=self._flush_task,
                                            args=(flush_time, self._stop_event))
        self._flushing_t.daemon = True
        self._flushing_t.start()


    def _flush_task(self, time, stop_event):
        """Calls the method _flush_buffer every certain time.
        """
        while not self._stop_event.isSet():
            with self.lock:
                self._flush_buffer()
            self._stop_event.wait(time)


    def _flush_buffer(self):
        """Flushes the messaging queue into Redis.

        All values are pushed at once for the same key.
        """
        if self.queue:
            self.redis.rpush(self.key, *self.queue)
        self.queue = []


    def disable_buffering(self):
        """Disables buffering.

        If called, every single message will be directly pushed to Redis.
        """
        self._stop_event.set()
        self.flush_threshold = 1


    def emit(self, record):
        """Emits a pair (key, value) to redis.

        The key is the one provided when creating the handler, or redis if none was
        provided. The value contains both the message and the hostname. Extra values
        are also appended to the message.
        """
        with self.lock:
            r = {"message": record.msg, "host": platform.node(), "level": record.level_name}
            r.update(self.extra_fields)
            r.update(record.kwargs)
            self.queue.append(json.dumps(r))
            if len(self.queue) == self.flush_threshold:
                self._flush_buffer()


    def close(self):
        self._flush_buffer()


class MessageQueueHandler(Handler):
    """A handler that acts as a message queue publisher, which publishes each
    record as json dump. Requires the kombu module.

    The queue will be filled with JSON exported log records.  To receive such
    log records from a queue you can use the :class:`MessageQueueSubscriber`.

    Example setup::

        handler = MessageQueueHandler('mongodb://localhost:27017/logging')
    """

    def __init__(self, uri=None, queue='logging', level=NOTSET,
                 filter=None, bubble=False, context=None):
        Handler.__init__(self, level, filter, bubble)
        try:
            import kombu
        except ImportError:
            raise RuntimeError('The kombu library is required for '
                               'the RabbitMQSubscriber.')
        if uri:
            connection = kombu.Connection(uri)

        self.queue = connection.SimpleQueue(queue)

    def export_record(self, record):
        """Exports the record into a dictionary ready for JSON dumping.
        """
        return record.to_dict(json_safe=True)

    def emit(self, record):
        self.queue.put(self.export_record(record))

    def close(self):
        self.queue.close()


RabbitMQHandler = MessageQueueHandler


class ZeroMQHandler(Handler):
    """A handler that acts as a ZeroMQ publisher, which publishes each record
    as json dump.  Requires the pyzmq library.

    The queue will be filled with JSON exported log records.  To receive such
    log records from a queue you can use the :class:`ZeroMQSubscriber`.

    If `multi` is set to `True`, the handler will use a `PUSH` socket to
    publish the records. This allows multiple handlers to use the same `uri`.
    The records can be received by using the :class:`ZeroMQSubscriber` with
    `multi` set to `True`.


    Example setup::

        handler = ZeroMQHandler('tcp://127.0.0.1:5000')
    """

    def __init__(self, uri=None, level=NOTSET, filter=None, bubble=False,
                 context=None, multi=False):
        Handler.__init__(self, level, filter, bubble)
        try:
            import zmq
        except ImportError:
            raise RuntimeError('The pyzmq library is required for '
                               'the ZeroMQHandler.')
        #: the zero mq context
        self.context = context or zmq.Context()

        if multi:
            #: the zero mq socket.
            self.socket = self.context.socket(zmq.PUSH)
            if uri is not None:
                self.socket.connect(uri)
        else:
            #: the zero mq socket.
            self.socket = self.context.socket(zmq.PUB)
            if uri is not None:
                self.socket.bind(uri)


    def export_record(self, record):
        """Exports the record into a dictionary ready for JSON dumping."""
        return record.to_dict(json_safe=True)

    def emit(self, record):
        self.socket.send(json.dumps(self.export_record(record)).encode("utf-8"))

    def close(self):
        self.socket.close()


class ThreadController(object):
    """A helper class used by queue subscribers to control the background
    thread.  This is usually created and started in one go by
    :meth:`~logbook.queues.ZeroMQSubscriber.dispatch_in_background` or
    a comparable function.
    """

    def __init__(self, subscriber, setup=None):
        self.setup = setup
        self.subscriber = subscriber
        self.running = False
        self._thread = None

    def start(self):
        """Starts the task thread."""
        self.running = True
        self._thread = Thread(target=self._target)
        self._thread.setDaemon(True)
        self._thread.start()

    def stop(self):
        """Stops the task thread."""
        if self.running:
            self.running = False
            self._thread.join()
            self._thread = None

    def _target(self):
        if self.setup is not None:
            self.setup.push_thread()
        try:
            while self.running:
                self.subscriber.dispatch_once(timeout=0.05)
        finally:
            if self.setup is not None:
                self.setup.pop_thread()


class SubscriberBase(object):
    """Baseclass for all subscribers."""

    def recv(self, timeout=None):
        """Receives a single record from the socket.  Timeout of 0 means nonblocking,
        `None` means blocking and otherwise it's a timeout in seconds after which
        the function just returns with `None`.

        Subclasses have to override this.
        """
        raise NotImplementedError()

    def dispatch_once(self, timeout=None):
        """Receives one record from the socket, loads it and dispatches it.  Returns
        `True` if something was dispatched or `False` if it timed out.
        """
        rv = self.recv(timeout)
        if rv is not None:
            dispatch_record(rv)
            return True
        return False

    def dispatch_forever(self):
        """Starts a loop that dispatches log records forever."""
        while 1:
            self.dispatch_once()

    def dispatch_in_background(self, setup=None):
        """Starts a new daemonized thread that dispatches in the background.
        An optional handler setup can be provided that pushed to the new
        thread (can be any :class:`logbook.base.StackedObject`).

        Returns a :class:`ThreadController` object for shutting down
        the background thread.  The background thread will already be
        running when this function returns.
        """
        controller = ThreadController(self, setup)
        controller.start()
        return controller


class MessageQueueSubscriber(SubscriberBase):
    """A helper that acts as a message queue subscriber and will dispatch
    received log records to the active handler setup. There are multiple ways
    to use this class.

    It can be used to receive log records from a queue::

        subscriber = MessageQueueSubscriber('mongodb://localhost:27017/logging')
        record = subscriber.recv()

    But it can also be used to receive and dispatch these in one go::

        with target_handler:
            subscriber = MessageQueueSubscriber('mongodb://localhost:27017/logging')
            subscriber.dispatch_forever()

    This will take all the log records from that queue and dispatch them
    over to `target_handler`.  If you want you can also do that in the
    background::

        subscriber = MessageQueueSubscriber('mongodb://localhost:27017/logging')
        controller = subscriber.dispatch_in_background(target_handler)

    The controller returned can be used to shut down the background
    thread::

        controller.stop()
    """
    def __init__(self, uri=None, queue='logging'):
        try:
            import kombu
        except ImportError:
            raise RuntimeError('The kombu library is required.')
        if uri:
            connection = kombu.Connection(uri)

        self.queue = connection.SimpleQueue(queue)

    def __del__(self):
        try:
            self.close()
        except AttributeError:
            # subscriber partially created
            pass

    def close(self):
        self.queue.close()

    def recv(self, timeout=None):
        """Receives a single record from the socket.  Timeout of 0 means nonblocking,
        `None` means blocking and otherwise it's a timeout in seconds after which
        the function just returns with `None`.
        """
        if timeout == 0:
            try:
                rv = self.queue.get(block=False)
            except Exception:
                return
        else:
            rv = self.queue.get(timeout=timeout)

        log_record = rv.payload
        rv.ack()

        return LogRecord.from_dict(log_record)


RabbitMQSubscriber = MessageQueueSubscriber


class ZeroMQSubscriber(SubscriberBase):
    """A helper that acts as ZeroMQ subscriber and will dispatch received
    log records to the active handler setup.  There are multiple ways to
    use this class.

    It can be used to receive log records from a queue::

        subscriber = ZeroMQSubscriber('tcp://127.0.0.1:5000')
        record = subscriber.recv()

    But it can also be used to receive and dispatch these in one go::

        with target_handler:
            subscriber = ZeroMQSubscriber('tcp://127.0.0.1:5000')
            subscriber.dispatch_forever()

    This will take all the log records from that queue and dispatch them
    over to `target_handler`.  If you want you can also do that in the
    background::

        subscriber = ZeroMQSubscriber('tcp://127.0.0.1:5000')
        controller = subscriber.dispatch_in_background(target_handler)

    The controller returned can be used to shut down the background
    thread::

        controller.stop()

    If `multi` is set to `True`, the subscriber will use a `PULL` socket
    and listen to records published by a `PUSH` socket (usually via a
    :class:`ZeroMQHandler` with `multi` set to `True`). This allows a
    single subscriber to dispatch multiple handlers.
    """

    def __init__(self, uri=None, context=None, multi=False):
        try:
            import zmq
        except ImportError:
            raise RuntimeError('The pyzmq library is required for '
                               'the ZeroMQSubscriber.')
        self._zmq = zmq

        #: the zero mq context
        self.context = context or zmq.Context()

        if multi:
            #: the zero mq socket.
            self.socket = self.context.socket(zmq.PULL)
            if uri is not None:
                self.socket.bind(uri)
        else:
            #: the zero mq socket.
            self.socket = self.context.socket(zmq.SUB)
            if uri is not None:
                self.socket.connect(uri)
            self.socket.setsockopt_unicode(zmq.SUBSCRIBE, u(''))

    def __del__(self):
        try:
            self.close()
        except AttributeError:
            # subscriber partially created
            pass

    def close(self):
        """Closes the zero mq socket."""
        self.socket.close()

    def recv(self, timeout=None):
        """Receives a single record from the socket.  Timeout of 0 means nonblocking,
        `None` means blocking and otherwise it's a timeout in seconds after which
        the function just returns with `None`.
        """
        if timeout is None:
            rv = self.socket.recv()
        elif not timeout:
            rv = self.socket.recv(self._zmq.NOBLOCK)
            if rv is None:
                return
        else:
            if not self._zmq.select([self.socket], [], [], timeout)[0]:
                return
            rv = self.socket.recv(self._zmq.NOBLOCK)
        if not PY2:
            rv = rv.decode("utf-8")
        return LogRecord.from_dict(json.loads(rv))


def _fix_261_mplog():
    """necessary for older python's to disable a broken monkeypatch
    in the logging module.  See multiprocessing/util.py for the
    hasattr() check.  At least in Python 2.6.1 the multiprocessing
    module is not imported by logging and as such the test in
    the util fails.
    """
    import logging
    import multiprocessing
    logging.multiprocessing = multiprocessing


class MultiProcessingHandler(Handler):
    """Implements a handler that dispatches over a queue to a different
    process.  It is connected to a subscriber with a
    :class:`multiprocessing.Queue`::

        from multiprocessing import Queue
        from logbook.queues import MultiProcessingHandler
        queue = Queue(-1)
        handler = MultiProcessingHandler(queue)

    """

    def __init__(self, queue, level=NOTSET, filter=None, bubble=False):
        Handler.__init__(self, level, filter, bubble)
        self.queue = queue
        _fix_261_mplog()

    def emit(self, record):
        self.queue.put_nowait(record.to_dict(json_safe=True))


class MultiProcessingSubscriber(SubscriberBase):
    """Receives log records from the given multiprocessing queue and
    dispatches them to the active handler setup.  Make sure to use the same
    queue for both handler and subscriber.  Idaelly the queue is set
    up with maximum size (``-1``)::

        from multiprocessing import Queue
        queue = Queue(-1)

    It can be used to receive log records from a queue::

        subscriber = MultiProcessingSubscriber(queue)
        record = subscriber.recv()

    But it can also be used to receive and dispatch these in one go::

        with target_handler:
            subscriber = MultiProcessingSubscriber(queue)
            subscriber.dispatch_forever()

    This will take all the log records from that queue and dispatch them
    over to `target_handler`.  If you want you can also do that in the
    background::

        subscriber = MultiProcessingSubscriber(queue)
        controller = subscriber.dispatch_in_background(target_handler)

    The controller returned can be used to shut down the background
    thread::

        controller.stop()

    If no queue is provided the subscriber will create one.  This one can the
    be used by handlers::

        subscriber = MultiProcessingSubscriber()
        handler = MultiProcessingHandler(subscriber.queue)
    """

    def __init__(self, queue=None):
        if queue is None:
            from multiprocessing import Queue
            queue = Queue(-1)
        self.queue = queue
        _fix_261_mplog()

    def recv(self, timeout=None):
        if timeout is None:
            rv = self.queue.get()
        else:
            try:
                rv = self.queue.get(block=False, timeout=timeout)
            except Empty:
                return None
        return LogRecord.from_dict(rv)


class ExecnetChannelHandler(Handler):
    """Implements a handler that dispatches over a execnet channel
    to a different process.
    """

    def __init__(self, channel, level=NOTSET, filter=None, bubble=False):
        Handler.__init__(self, level, filter, bubble)
        self.channel = channel

    def emit(self, record):
        self.channel.send(record.to_dict(json_safe=True))


class ExecnetChannelSubscriber(SubscriberBase):
    """subscribes to a execnet channel"""

    def __init__(self, channel):
        self.channel = channel

    def recv(self, timeout=None):
        try:
            rv = self.channel.receive(timeout=timeout)
        except self.channel.RemoteError:
            #XXX: handle
            return None
        except (self.channel.TimeoutError, EOFError):
            return None
        else:
            return LogRecord.from_dict(rv)


class TWHThreadController(object):
    """A very basic thread controller that pulls things in from a
    queue and sends it to a handler.  Both queue and handler are
    taken from the passed :class:`ThreadedWrapperHandler`.
    """
    _sentinel = object()

    def __init__(self, wrapper_handler):
        self.wrapper_handler = wrapper_handler
        self.running = False
        self._thread = None

    def start(self):
        """Starts the task thread."""
        self.running = True
        self._thread = Thread(target=self._target)
        self._thread.setDaemon(True)
        self._thread.start()

    def stop(self):
        """Stops the task thread."""
        if self.running:
            self.wrapper_handler.queue.put_nowait(self._sentinel)
            self._thread.join()
            self._thread = None

    def _target(self):
        while 1:
            record = self.wrapper_handler.queue.get()
            if record is self._sentinel:
                self.running = False
                break
            self.wrapper_handler.handler.handle(record)


class ThreadedWrapperHandler(WrapperHandler):
    """This handled uses a single background thread to dispatch log records
    to a specific other handler using an internal queue.  The idea is that if
    you are using a handler that requires some time to hand off the log records
    (such as the mail handler) and would block your request, you can let
    Logbook do that in a background thread.

    The threaded wrapper handler will automatically adopt the methods and
    properties of the wrapped handler.  All the values will be reflected:

    >>> twh = ThreadedWrapperHandler(TestHandler())
    >>> from logbook import WARNING
    >>> twh.level_name = 'WARNING'
    >>> twh.handler.level_name
    'WARNING'
    """
    _direct_attrs = frozenset(['handler', 'queue', 'controller'])

    def __init__(self, handler):
        WrapperHandler.__init__(self, handler)
        self.queue = ThreadQueue(-1)
        self.controller = TWHThreadController(self)
        self.controller.start()

    def close(self):
        self.controller.stop()
        self.handler.close()

    def emit(self, record):
        self.queue.put_nowait(record)


class GroupMember(ThreadController):
    def __init__(self, subscriber, queue):
        ThreadController.__init__(self, subscriber, None)
        self.queue = queue

    def _target(self):
        if self.setup is not None:
            self.setup.push_thread()
        try:
            while self.running:
                record = self.subscriber.recv()
                if record:
                    try:
                        self.queue.put(record, timeout=0.05)
                    except Queue.Full:
                        pass
        finally:
            if self.setup is not None:
                self.setup.pop_thread()


class SubscriberGroup(SubscriberBase):
    """This is a subscriber which represents a group of subscribers.

    This is helpful if you are writing a server-like application which has
    "slaves". This way a user is easily able to view every log record which
    happened somewhere in the entire system without having to check every
    single slave::

        subscribers = SubscriberGroup([
            MultiProcessingSubscriber(queue),
            ZeroMQSubscriber('tcp://127.0.0.1:5000')
        ])
        with target_handler:
            subscribers.dispatch_forever()
    """
    def __init__(self, subscribers=None, queue_limit=10):
        self.members = []
        self.queue = ThreadQueue(queue_limit)
        for subscriber in subscribers or []:
            self.add(subscriber)

    def add(self, subscriber):
        """Adds the given `subscriber` to the group."""
        member = GroupMember(subscriber, self.queue)
        member.start()
        self.members.append(member)

    def recv(self, timeout=None):
        try:
            return self.queue.get(timeout=timeout)
        except Empty:
            return

    def stop(self):
        """Stops the group from internally recieving any more messages, once the
        internal queue is exhausted :meth:`recv` will always return `None`.
        """
        for member in self.members:
            self.member.stop()

########NEW FILE########
__FILENAME__ = ticketing
# -*- coding: utf-8 -*-
"""
    logbook.ticketing
    ~~~~~~~~~~~~~~~~~

    Implements long handlers that write to remote data stores and assign
    each logging message a ticket id.

    :copyright: (c) 2010 by Armin Ronacher, Georg Brandl.
    :license: BSD, see LICENSE for more details.
"""
from time import time
import json
from logbook.base import NOTSET, level_name_property, LogRecord
from logbook.handlers import Handler, HashingHandlerMixin
from logbook.helpers import cached_property, b, PY2, u

class Ticket(object):
    """Represents a ticket from the database."""

    level_name = level_name_property()

    def __init__(self, db, row):
        self.db = db
        self.__dict__.update(row)

    @cached_property
    def last_occurrence(self):
        """The last occurrence."""
        rv = self.get_occurrences(limit=1)
        if rv:
            return rv[0]

    def get_occurrences(self, order_by='-time', limit=50, offset=0):
        """Returns the occurrences for this ticket."""
        return self.db.get_occurrences(self.ticket_id, order_by, limit, offset)

    def solve(self):
        """Marks this ticket as solved."""
        self.db.solve_ticket(self.ticket_id)
        self.solved = True

    def delete(self):
        """Deletes the ticket from the database."""
        self.db.delete_ticket(self.ticket_id)

    # Silence DeprecationWarning
    __hash__ = None

    def __eq__(self, other):
        equal = True
        for key in self.__dict__.keys():
            if getattr(self, key) != getattr(other, key):
                equal = False
                break
        return equal

    def __ne__(self, other):
        return not self.__eq__(other)


class Occurrence(LogRecord):
    """Represents an occurrence of a ticket."""

    def __init__(self, db, row):
        self.update_from_dict(json.loads(row['data']))
        self.db = db
        self.time = row['time']
        self.ticket_id = row['ticket_id']
        self.occurrence_id = row['occurrence_id']


class BackendBase(object):
    """Provides an abstract interface to various databases."""

    def __init__(self, **options):
        self.options = options
        self.setup_backend()

    def setup_backend(self):
        """Setup the database backend."""
        raise NotImplementedError()

    def record_ticket(self, record, data, hash, app_id):
        """Records a log record as ticket."""
        raise NotImplementedError()

    def count_tickets(self):
        """Returns the number of tickets."""
        raise NotImplementedError()

    def get_tickets(self, order_by='-last_occurrence_time', limit=50, offset=0):
        """Selects tickets from the database."""
        raise NotImplementedError()

    def solve_ticket(self, ticket_id):
        """Marks a ticket as solved."""
        raise NotImplementedError()

    def delete_ticket(self, ticket_id):
        """Deletes a ticket from the database."""
        raise NotImplementedError()

    def get_ticket(self, ticket_id):
        """Return a single ticket with all occurrences."""
        raise NotImplementedError()

    def get_occurrences(self, ticket, order_by='-time', limit=50, offset=0):
        """Selects occurrences from the database for a ticket."""
        raise NotImplementedError()


class SQLAlchemyBackend(BackendBase):
    """Implements a backend that is writing into a database SQLAlchemy can
    interface.

    This backend takes some additional options:

    `table_prefix`
        an optional table prefix for all tables created by
        the logbook ticketing handler.

    `metadata`
        an optional SQLAlchemy metadata object for the table creation.

    `autocreate_tables`
        can be set to `False` to disable the automatic
        creation of the logbook tables.

    """

    def setup_backend(self):
        from sqlalchemy import create_engine, MetaData
        engine_or_uri = self.options.pop('uri', None)
        metadata = self.options.pop('metadata', None)
        table_prefix = self.options.pop('table_prefix', 'logbook_')

        if hasattr(engine_or_uri, 'execute'):
            self.engine = engine_or_uri
        else:
            self.engine = create_engine(engine_or_uri, convert_unicode=True)
        if metadata is None:
            metadata = MetaData()
        self.table_prefix = table_prefix
        self.metadata = metadata
        self.create_tables()
        if self.options.get('autocreate_tables', True):
            self.metadata.create_all(bind=self.engine)

    def create_tables(self):
        """Creates the tables required for the handler on the class and
        metadata.
        """
        import sqlalchemy as db
        def table(name, *args, **kwargs):
            return db.Table(self.table_prefix + name, self.metadata,
                            *args, **kwargs)
        self.tickets = table('tickets',
            db.Column('ticket_id', db.Integer, primary_key=True),
            db.Column('record_hash', db.String(40), unique=True),
            db.Column('level', db.Integer),
            db.Column('channel', db.String(120)),
            db.Column('location', db.String(512)),
            db.Column('module', db.String(256)),
            db.Column('last_occurrence_time', db.DateTime),
            db.Column('occurrence_count', db.Integer),
            db.Column('solved', db.Boolean),
            db.Column('app_id', db.String(80))
        )
        self.occurrences = table('occurrences',
            db.Column('occurrence_id', db.Integer, primary_key=True),
            db.Column('ticket_id', db.Integer,
                      db.ForeignKey(self.table_prefix + 'tickets.ticket_id')),
            db.Column('time', db.DateTime),
            db.Column('data', db.Text),
            db.Column('app_id', db.String(80))
        )

    def _order(self, q, table, order_by):
        if order_by[0] == '-':
            return q.order_by(table.c[order_by[1:]].desc())
        return q.order_by(table.c[order_by])

    def record_ticket(self, record, data, hash, app_id):
        """Records a log record as ticket."""
        cnx = self.engine.connect()
        trans = cnx.begin()
        try:
            q = self.tickets.select(self.tickets.c.record_hash == hash)
            row = cnx.execute(q).fetchone()
            if row is None:
                row = cnx.execute(self.tickets.insert().values(
                    record_hash=hash,
                    level=record.level,
                    channel=record.channel or u(''),
                    location=u('%s:%d') % (record.filename, record.lineno),
                    module=record.module or u('<unknown>'),
                    occurrence_count=0,
                    solved=False,
                    app_id=app_id
                ))
                ticket_id = row.inserted_primary_key[0]
            else:
                ticket_id = row['ticket_id']
            cnx.execute(self.occurrences.insert()
                .values(ticket_id=ticket_id,
                        time=record.time,
                        app_id=app_id,
                        data=json.dumps(data)))
            cnx.execute(self.tickets.update()
                .where(self.tickets.c.ticket_id == ticket_id)
                .values(occurrence_count=self.tickets.c.occurrence_count + 1,
                        last_occurrence_time=record.time,
                        solved=False))
            trans.commit()
        except Exception:
            trans.rollback()
            raise
        cnx.close()

    def count_tickets(self):
        """Returns the number of tickets."""
        return self.engine.execute(self.tickets.count()).fetchone()[0]

    def get_tickets(self, order_by='-last_occurrence_time', limit=50, offset=0):
        """Selects tickets from the database."""
        return [Ticket(self, row) for row in self.engine.execute(
            self._order(self.tickets.select(), self.tickets, order_by)
            .limit(limit).offset(offset)).fetchall()]

    def solve_ticket(self, ticket_id):
        """Marks a ticket as solved."""
        self.engine.execute(self.tickets.update()
            .where(self.tickets.c.ticket_id == ticket_id)
            .values(solved=True))

    def delete_ticket(self, ticket_id):
        """Deletes a ticket from the database."""
        self.engine.execute(self.occurrences.delete()
            .where(self.occurrences.c.ticket_id == ticket_id))
        self.engine.execute(self.tickets.delete()
            .where(self.tickets.c.ticket_id == ticket_id))

    def get_ticket(self, ticket_id):
        """Return a single ticket with all occurrences."""
        row = self.engine.execute(self.tickets.select().where(
            self.tickets.c.ticket_id == ticket_id)).fetchone()
        if row is not None:
            return Ticket(self, row)

    def get_occurrences(self, ticket, order_by='-time', limit=50, offset=0):
        """Selects occurrences from the database for a ticket."""
        return [Occurrence(self, row) for row in
                self.engine.execute(self._order(self.occurrences.select()
                    .where(self.occurrences.c.ticket_id == ticket),
                    self.occurrences, order_by)
                .limit(limit).offset(offset)).fetchall()]


class MongoDBBackend(BackendBase):
    """Implements a backend that writes into a MongoDB database."""

    class _FixedTicketClass(Ticket):
        @property
        def ticket_id(self):
            return self._id

    class _FixedOccurrenceClass(Occurrence):
        def __init__(self, db, row):
            self.update_from_dict(json.loads(row['data']))
            self.db = db
            self.time = row['time']
            self.ticket_id = row['ticket_id']
            self.occurrence_id = row['_id']

    #TODO: Update connection setup once PYTHON-160 is solved.
    def setup_backend(self):
        import pymongo
        from pymongo import ASCENDING, DESCENDING
        from pymongo.connection import Connection

        try:
                from pymongo.uri_parser import parse_uri
        except ImportError:
                from pymongo.connection import _parse_uri as parse_uri

        from pymongo.errors import AutoReconnect

        _connection = None
        uri = self.options.pop('uri', u(''))
        _connection_attempts = 0

        parsed_uri = parse_uri(uri, Connection.PORT)

        if type(parsed_uri) is tuple:
                # pymongo < 2.0
                database = parsed_uri[1]
        else:
                # pymongo >= 2.0
                database = parsed_uri['database']

        # Handle auto reconnect signals properly
        while _connection_attempts < 5:
            try:
                if _connection is None:
                    _connection = Connection(uri)
                database = _connection[database]
                break
            except AutoReconnect:
                _connection_attempts += 1
                time.sleep(0.1)

        self.database = database

        # setup correct indexes
        database.tickets.ensure_index([('record_hash', ASCENDING)], unique=True)
        database.tickets.ensure_index([('solved', ASCENDING), ('level', ASCENDING)])
        database.occurrences.ensure_index([('time', DESCENDING)])

    def _order(self, q, order_by):
        from pymongo import ASCENDING, DESCENDING
        col = '%s' % (order_by[0] == '-' and order_by[1:] or order_by)
        if order_by[0] == '-':
            return q.sort(col, DESCENDING)
        return q.sort(col, ASCENDING)

    def _oid(self, ticket_id):
        from pymongo.objectid import ObjectId
        return ObjectId(ticket_id)

    def record_ticket(self, record, data, hash, app_id):
        """Records a log record as ticket."""
        db = self.database
        ticket = db.tickets.find_one({'record_hash': hash})
        if not ticket:
            doc = {
                'record_hash':      hash,
                'level':            record.level,
                'channel':          record.channel or u(''),
                'location':         u('%s:%d') % (record.filename, record.lineno),
                'module':           record.module or u('<unknown>'),
                'occurrence_count': 0,
                'solved':           False,
                'app_id':           app_id,
            }
            ticket_id = db.tickets.insert(doc)
        else:
            ticket_id = ticket['_id']

        db.tickets.update({'_id': ticket_id}, {
            '$inc': {
                'occurrence_count':     1
            },
            '$set': {
                'last_occurrence_time': record.time,
                'solved':               False
            }
        })
        # We store occurrences in a seperate collection so that
        # we can make it a capped collection optionally.
        db.occurrences.insert({
            'ticket_id':    self._oid(ticket_id),
            'app_id':       app_id,
            'time':         record.time,
            'data':         json.dumps(data),
        })

    def count_tickets(self):
        """Returns the number of tickets."""
        return self.database.tickets.count()

    def get_tickets(self, order_by='-last_occurrence_time', limit=50, offset=0):
        """Selects tickets from the database."""
        query = self._order(self.database.tickets.find(), order_by) \
                    .limit(limit).skip(offset)
        return [self._FixedTicketClass(self, obj) for obj in query]

    def solve_ticket(self, ticket_id):
        """Marks a ticket as solved."""
        self.database.tickets.update({'_id': self._oid(ticket_id)},
                                     {'solved': True})

    def delete_ticket(self, ticket_id):
        """Deletes a ticket from the database."""
        self.database.occurrences.remove({'ticket_id': self._oid(ticket_id)})
        self.database.tickets.remove({'_id': self._oid(ticket_id)})

    def get_ticket(self, ticket_id):
        """Return a single ticket with all occurrences."""
        ticket = self.database.tickets.find_one({'_id': self._oid(ticket_id)})
        if ticket:
            return Ticket(self, ticket)

    def get_occurrences(self, ticket, order_by='-time', limit=50, offset=0):
        """Selects occurrences from the database for a ticket."""
        collection = self.database.occurrences
        occurrences = self._order(collection.find(
            {'ticket_id': self._oid(ticket)}
        ), order_by).limit(limit).skip(offset)
        return [self._FixedOccurrenceClass(self, obj) for obj in occurrences]


class TicketingBaseHandler(Handler, HashingHandlerMixin):
    """Baseclass for ticketing handlers.  This can be used to interface
    ticketing systems that do not necessarily provide an interface that
    would be compatible with the :class:`BackendBase` interface.
    """

    def __init__(self, hash_salt, level=NOTSET, filter=None, bubble=False):
        Handler.__init__(self, level, filter, bubble)
        self.hash_salt = hash_salt

    def hash_record_raw(self, record):
        """Returns the unique hash of a record."""
        hash = HashingHandlerMixin.hash_record_raw(self, record)
        if self.hash_salt is not None:
            hash_salt = self.hash_salt
            if not PY2 or isinstance(hash_salt, unicode):
                hash_salt = hash_salt.encode('utf-8')
            hash.update(b('\x00') + hash_salt)
        return hash


class TicketingHandler(TicketingBaseHandler):
    """A handler that writes log records into a remote database.  This
    database can be connected to from different dispatchers which makes
    this a nice setup for web applications::

        from logbook.ticketing import TicketingHandler
        handler = TicketingHandler('sqlite:////tmp/myapp-logs.db')

    :param uri: a backend specific string or object to decide where to log to.
    :param app_id: a string with an optional ID for an application.  Can be
                   used to keep multiple application setups apart when logging
                   into the same database.
    :param hash_salt: an optional salt (binary string) for the hashes.
    :param backend: A backend class that implements the proper database handling.
                    Backends available are: :class:`SQLAlchemyBackend`,
                    :class:`MongoDBBackend`.
    """

    #: The default backend that is being used when no backend is specified.
    #: Unless overriden by a subclass this will be the
    #: :class:`SQLAlchemyBackend`.
    default_backend = SQLAlchemyBackend

    def __init__(self, uri, app_id='generic', level=NOTSET,
                 filter=None, bubble=False, hash_salt=None, backend=None,
                 **db_options):
        if hash_salt is None:
            hash_salt = u('apphash-') + app_id
        TicketingBaseHandler.__init__(self, hash_salt, level, filter, bubble)
        if backend is None:
            backend = self.default_backend
        db_options['uri'] = uri
        self.set_backend(backend, **db_options)
        self.app_id = app_id

    def set_backend(self, cls, **options):
        self.db = cls(**options)

    def process_record(self, record, hash):
        """Subclasses can override this to tamper with the data dict that
        is sent to the database as JSON.
        """
        return record.to_dict(json_safe=True)

    def record_ticket(self, record, data, hash):
        """Record either a new ticket or a new occurrence for a
        ticket based on the hash.
        """
        self.db.record_ticket(record, data, hash, self.app_id)

    def emit(self, record):
        """Emits a single record and writes it to the database."""
        hash = self.hash_record(record)
        data = self.process_record(record, hash)
        self.record_ticket(record, data, hash)

########NEW FILE########
__FILENAME__ = _fallback
# -*- coding: utf-8 -*-
"""
    logbook._fallback
    ~~~~~~~~~~~~~~~~~

    Fallback implementations in case speedups is not around.

    :copyright: (c) 2010 by Armin Ronacher, Georg Brandl.
    :license: BSD, see LICENSE for more details.
"""
import threading
from itertools import count
try:
    from thread import get_ident as current_thread
except ImportError:
    from _thread import get_ident as current_thread
from logbook.helpers import get_iterator_next_method

_missing = object()
_MAX_CONTEXT_OBJECT_CACHE = 256

def group_reflected_property(name, default, fallback=_missing):
    """Returns a property for a given name that falls back to the
    value of the group if set.  If there is no such group, the
    provided default is used.
    """
    def _get(self):
        rv = getattr(self, '_' + name, _missing)
        if rv is not _missing and rv != fallback:
            return rv
        if self.group is None:
            return default
        return getattr(self.group, name)
    def _set(self, value):
        setattr(self, '_' + name, value)
    def _del(self):
        delattr(self, '_' + name)
    return property(_get, _set, _del)


class _StackBound(object):

    def __init__(self, obj, push, pop):
        self.__obj = obj
        self.__push = push
        self.__pop = pop

    def __enter__(self):
        self.__push()
        return self.__obj

    def __exit__(self, exc_type, exc_value, tb):
        self.__pop()


class StackedObject(object):
    """Baseclass for all objects that provide stack manipulation
    operations.
    """

    def push_thread(self):
        """Pushes the stacked object to the thread stack."""
        raise NotImplementedError()

    def pop_thread(self):
        """Pops the stacked object from the thread stack."""
        raise NotImplementedError()

    def push_application(self):
        """Pushes the stacked object to the application stack."""
        raise NotImplementedError()

    def pop_application(self):
        """Pops the stacked object from the application stack."""
        raise NotImplementedError()

    def __enter__(self):
        self.push_thread()
        return self

    def __exit__(self, exc_type, exc_value, tb):
        self.pop_thread()

    def threadbound(self, _cls=_StackBound):
        """Can be used in combination with the `with` statement to
        execute code while the object is bound to the thread.
        """
        return _cls(self, self.push_thread, self.pop_thread)

    def applicationbound(self, _cls=_StackBound):
        """Can be used in combination with the `with` statement to
        execute code while the object is bound to the application.
        """
        return _cls(self, self.push_application, self.pop_application)


class ContextStackManager(object):
    """Helper class for context objects that manages a stack of
    objects.
    """

    def __init__(self):
        self._global = []
        self._context_lock = threading.Lock()
        self._context = threading.local()
        self._cache = {}
        self._stackop = get_iterator_next_method(count())

    def iter_context_objects(self):
        """Returns an iterator over all objects for the combined
        application and context cache.
        """
        tid = current_thread()
        objects = self._cache.get(tid)
        if objects is None:
            if len(self._cache) > _MAX_CONTEXT_OBJECT_CACHE:
                self._cache.clear()
            objects = self._global[:]
            objects.extend(getattr(self._context, 'stack', ()))
            objects.sort(reverse=True)
            objects = [x[1] for x in objects]
            self._cache[tid] = objects
        return iter(objects)

    def push_thread(self, obj):
        self._context_lock.acquire()
        try:
            self._cache.pop(current_thread(), None)
            item = (self._stackop(), obj)
            stack = getattr(self._context, 'stack', None)
            if stack is None:
                self._context.stack = [item]
            else:
                stack.append(item)
        finally:
            self._context_lock.release()

    def pop_thread(self):
        self._context_lock.acquire()
        try:
            self._cache.pop(current_thread(), None)
            stack = getattr(self._context, 'stack', None)
            assert stack, 'no objects on stack'
            return stack.pop()[1]
        finally:
            self._context_lock.release()

    def push_application(self, obj):
        self._global.append((self._stackop(), obj))
        self._cache.clear()

    def pop_application(self):
        assert self._global, 'no objects on application stack'
        popped = self._global.pop()[1]
        self._cache.clear()
        return popped

########NEW FILE########
__FILENAME__ = _termcolors
# -*- coding: utf-8 -*-
"""
    logbook._termcolors
    ~~~~~~~~~~~~~~~~~~~

    Provides terminal color mappings.

    :copyright: (c) 2010 by Armin Ronacher, Georg Brandl.
    :license: BSD, see LICENSE for more details.
"""

esc = "\x1b["

codes = {}
codes[""]          = ""
codes["reset"]     = esc + "39;49;00m"

dark_colors  = ["black", "darkred", "darkgreen", "brown", "darkblue",
                "purple", "teal", "lightgray"]
light_colors = ["darkgray", "red", "green", "yellow", "blue",
                "fuchsia", "turquoise", "white"]

x = 30
for d, l in zip(dark_colors, light_colors):
    codes[d] = esc + "%im" % x
    codes[l] = esc + "%i;01m" % x
    x += 1

del d, l, x

codes["darkteal"]   = codes["turquoise"]
codes["darkyellow"] = codes["brown"]
codes["fuscia"]     = codes["fuchsia"]


def _str_to_type(obj, strtype):
    """Helper for ansiformat and colorize"""
    if isinstance(obj, type(strtype)):
        return obj
    return obj.encode('ascii')


def colorize(color_key, text):
    """Returns an ANSI formatted text with the given color."""
    return _str_to_type(codes[color_key], text) + text + \
           _str_to_type(codes["reset"], text)

########NEW FILE########
__FILENAME__ = make-release
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    make-release
    ~~~~~~~~~~~~

    Helper script that performs a release.  Does pretty much everything
    automatically for us.

    :copyright: (c) 2011 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""
import sys
import os
import re
import argparse
from datetime import datetime, date
from subprocess import Popen, PIPE

_date_clean_re = re.compile(r'(\d+)(st|nd|rd|th)')


def parse_changelog():
    with open('CHANGES') as f:
        lineiter = iter(f)
        for line in lineiter:
            match = re.search('^Version\s+(.*)', line.strip())
            if match is None:
                continue
            length = len(match.group(1))
            version = match.group(1).strip()
            if lineiter.next().count('-') != len(match.group(0)):
                continue
            while 1:
                change_info = lineiter.next().strip()
                if change_info:
                    break

            match = re.search(r'released on (\w+\s+\d+\w+\s+\d+)'
                              r'(?:, codename (.*))?(?i)', change_info)
            if match is None:
                continue

            datestr, codename = match.groups()
            return version, parse_date(datestr), codename


def bump_version(version):
    try:
        parts = map(int, version.split('.'))
    except ValueError:
        fail('Current version is not numeric')
    parts[-1] += 1
    return '.'.join(map(str, parts))


def parse_date(string):
    string = _date_clean_re.sub(r'\1', string)
    return datetime.strptime(string, '%B %d %Y')


def set_filename_version(filename, version_number, pattern):
    changed = []
    def inject_version(match):
        before, old, after = match.groups()
        changed.append(True)
        return before + version_number + after
    with open(filename) as f:
        contents = re.sub(r"^(\s*%s\s*=\s*')(.+?)(')(?sm)" % pattern,
                          inject_version, f.read())

    if not changed:
        fail('Could not find %s in %s', pattern, filename)

    with open(filename, 'w') as f:
        f.write(contents)


def set_init_version(version):
    info('Setting __init__.py version to %s', version)
    set_filename_version('logbook/__init__.py', version, '__version__')


def set_setup_version(version):
    info('Setting setup.py version to %s', version)
    set_filename_version('setup.py', version, 'version')

def set_doc_version(version):
    info('Setting docs/conf.py version to %s', version)
    set_filename_version('docs/conf.py', version, 'version')
    set_filename_version('docs/conf.py', version, 'release')


def build_and_upload():
    Popen([sys.executable, 'setup.py', 'release', 'sdist', 'upload']).wait()


def fail(message, *args):
    print >> sys.stderr, 'Error:', message % args
    sys.exit(1)


def info(message, *args):
    print >> sys.stderr, message % args


def get_git_tags():
    return set(Popen(['git', 'tag'], stdout=PIPE).communicate()[0].splitlines())


def git_is_clean():
    return Popen(['git', 'diff', '--quiet']).wait() == 0


def make_git_commit(message, *args):
    message = message % args
    Popen(['git', 'commit', '-am', message]).wait()


def make_git_tag(tag):
    info('Tagging "%s"', tag)
    Popen(['git', 'tag', tag]).wait()


parser = argparse.ArgumentParser("%prog [options]")
parser.add_argument("--no-upload", dest="upload", action="store_false", default=True)

def main():
    args = parser.parse_args()

    os.chdir(os.path.join(os.path.dirname(__file__), '..'))

    rv = parse_changelog()
    if rv is None:
        fail('Could not parse changelog')

    version, release_date, codename = rv
    dev_version = bump_version(version) + '-dev'

    info('Releasing %s (codename %s, release date %s)',
         version, codename, release_date.strftime('%d/%m/%Y'))
    tags = get_git_tags()

    if version in tags:
        fail('Version "%s" is already tagged', version)
    if release_date.date() != date.today():
        fail('Release date is not today (%s != %s)' % (release_date.date(), date.today()))

    if not git_is_clean():
        fail('You have uncommitted changes in git')

    set_init_version(version)
    set_setup_version(version)
    set_doc_version(version)
    make_git_commit('Bump version number to %s', version)
    make_git_tag(version)
    if args.upload:
        build_and_upload()
    set_init_version(dev_version)
    set_setup_version(dev_version)
    set_doc_version(dev_version)
    make_git_commit('Bump version number to %s', dev_version)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = travis_build
#! /usr/bin/python
from __future__ import print_function
import ast
import os
import subprocess
import sys

_PYPY = hasattr(sys, "pypy_version_info")

if __name__ == '__main__':
    use_cython = ast.literal_eval(os.environ["USE_CYTHON"])
    if use_cython and _PYPY:
        print("PyPy+Cython configuration skipped")
    else:
        sys.exit(
            subprocess.call("make cybuild test" if use_cython else "make test", shell=True)
        )

########NEW FILE########
__FILENAME__ = test_logbook
# -*- coding: utf-8 -*-
from .utils import (
    LogbookTestCase,
    activate_via_push_pop,
    activate_via_with_statement,
    capturing_stderr_context,
    get_total_delta_seconds,
    make_fake_mail_handler,
    missing,
    require_module,
    require_py3,
)
from contextlib import closing, contextmanager
from datetime import datetime, timedelta
from random import randrange
import logbook
from logbook.helpers import StringIO, xrange, iteritems, zip, u
import os
import pickle
import re
import shutil
import socket
import sys
import tempfile
import time
import json
try:
    from thread import get_ident
except ImportError:
    from _thread import get_ident
import base64

__file_without_pyc__ = __file__
if __file_without_pyc__.endswith(".pyc"):
    __file_without_pyc__ = __file_without_pyc__[:-1]

LETTERS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"

class _BasicAPITestCase(LogbookTestCase):
    def test_basic_logging(self):
        with self.thread_activation_strategy(logbook.TestHandler()) as handler:
            self.log.warn('This is a warning.  Nice hah?')

        self.assert_(handler.has_warning('This is a warning.  Nice hah?'))
        self.assertEqual(handler.formatted_records, [
            '[WARNING] testlogger: This is a warning.  Nice hah?'
        ])

    def test_extradict(self):
        with self.thread_activation_strategy(logbook.TestHandler()) as handler:
            self.log.warn('Test warning')
        record = handler.records[0]
        record.extra['existing'] = 'foo'
        self.assertEqual(record.extra['nonexisting'], '')
        self.assertEqual(record.extra['existing'], 'foo')
        self.assertEqual(repr(record.extra),
                         'ExtraDict({\'existing\': \'foo\'})')

    def test_custom_logger(self):
        client_ip = '127.0.0.1'

        class CustomLogger(logbook.Logger):
            def process_record(self, record):
                record.extra['ip'] = client_ip

        custom_log = CustomLogger('awesome logger')
        fmt = '[{record.level_name}] {record.channel}: ' \
              '{record.message} [{record.extra[ip]}]'
        handler = logbook.TestHandler(format_string=fmt)
        self.assertEqual(handler.format_string, fmt)

        with self.thread_activation_strategy(handler):
            custom_log.warn('Too many sounds')
            self.log.warn('"Music" playing')

        self.assertEqual(handler.formatted_records, [
            '[WARNING] awesome logger: Too many sounds [127.0.0.1]',
            '[WARNING] testlogger: "Music" playing []'
        ])

    def test_handler_exception(self):
        class ErroringHandler(logbook.TestHandler):
            def emit(self, record):
                raise RuntimeError('something bad happened')

        with capturing_stderr_context() as stderr:
            with self.thread_activation_strategy(ErroringHandler()) as handler:
                self.log.warn('I warn you.')
        self.assert_('something bad happened' in stderr.getvalue())
        self.assert_('I warn you' not in stderr.getvalue())

    def test_formatting_exception(self):
        def make_record():
            return logbook.LogRecord('Test Logger', logbook.WARNING,
                                     'Hello {foo:invalid}',
                                     kwargs={'foo': 42},
                                     frame=sys._getframe())
        record = make_record()
        with self.assertRaises(TypeError) as caught:
            record.message

        errormsg = str(caught.exception)
        self.assertRegexpMatches(errormsg,
                "Could not format message with provided arguments: Invalid (?:format specifier)|(?:conversion specification)|(?:format spec)")
        self.assertIn("msg='Hello {foo:invalid}'", errormsg)
        self.assertIn('args=()', errormsg)
        self.assertIn("kwargs={'foo': 42}", errormsg)
        self.assertRegexpMatches(
            errormsg,
            r'Happened in file .*%s, line \d+' % __file_without_pyc__)

    def test_exception_catching(self):
        logger = logbook.Logger('Test')
        with self.thread_activation_strategy(logbook.TestHandler()) as handler:
            self.assertFalse(handler.has_error())
            try:
                1 / 0
            except Exception:
                logger.exception()
            try:
                1 / 0
            except Exception:
                logger.exception('Awesome')
            self.assert_(handler.has_error('Uncaught exception occurred'))
            self.assert_(handler.has_error('Awesome'))
        self.assertIsNotNone(handler.records[0].exc_info)
        self.assertIn('1 / 0', handler.records[0].formatted_exception)

    def test_exception_catching_with_unicode(self):
        """ See https://github.com/mitsuhiko/logbook/issues/104
        """
        try:
            raise Exception(u('\u202a test \u202c'))
        except:
            r = logbook.LogRecord('channel', 'DEBUG', 'test', exc_info=sys.exc_info())
        r.exception_message

    def test_exc_info_tuple(self):
        self._test_exc_info(as_tuple=True)

    def test_exc_info_true(self):
        self._test_exc_info(as_tuple=False)

    def _test_exc_info(self, as_tuple):
        logger = logbook.Logger("Test")
        with self.thread_activation_strategy(logbook.TestHandler()) as handler:
            try:
                1 / 0
            except Exception:
                exc_info = sys.exc_info()
                logger.info("Exception caught", exc_info=exc_info if as_tuple else True)
        self.assertIsNotNone(handler.records[0].exc_info)
        self.assertEquals(handler.records[0].exc_info, exc_info)

    def test_exporting(self):
        with self.thread_activation_strategy(logbook.TestHandler()) as handler:
            try:
                1 / 0
            except Exception:
                self.log.exception()
            record = handler.records[0]

        exported = record.to_dict()
        record.close()
        imported = logbook.LogRecord.from_dict(exported)
        for key, value in iteritems(record.__dict__):
            if key[0] == '_':
                continue
            self.assertEqual(value, getattr(imported, key))

    def test_pickle(self):
        with self.thread_activation_strategy(logbook.TestHandler()) as handler:
            try:
                1 / 0
            except Exception:
                self.log.exception()
            record = handler.records[0]
        record.pull_information()
        record.close()

        for p in xrange(pickle.HIGHEST_PROTOCOL):
            exported = pickle.dumps(record, p)
            imported = pickle.loads(exported)
            for key, value in iteritems(record.__dict__):
                if key[0] == '_':
                    continue
                imported_value = getattr(imported, key)
                if isinstance(value, ZeroDivisionError):
                    # in Python 3.2, ZeroDivisionError(x) != ZeroDivisionError(x)
                    self.assert_(type(value) is type(imported_value))
                    self.assertEqual(value.args, imported_value.args)
                else:
                    self.assertEqual(value, imported_value)

    def test_timedate_format(self):
        """
        tests the logbook.set_datetime_format() function
        """
        FORMAT_STRING = '{record.time:%H:%M:%S} {record.message}'
        handler = logbook.TestHandler(format_string=FORMAT_STRING)
        handler.push_thread()
        logbook.set_datetime_format('utc')
        try:
            self.log.warn('This is a warning.')
            time_utc = handler.records[0].time
            logbook.set_datetime_format('local')
            self.log.warn('This is a warning.')
            time_local = handler.records[1].time
        finally:
            handler.pop_thread()
            # put back the default time factory
            logbook.set_datetime_format('utc')

        # get the expected difference between local and utc time
        t1 = datetime.now()
        t2 = datetime.utcnow()

        tz_minutes_diff = get_total_delta_seconds(t1 - t2)/60.0

        if abs(tz_minutes_diff) < 1:
            self.skipTest("Cannot test utc/localtime differences if they vary by less than one minute...")

        # get the difference between LogRecord local and utc times
        logbook_minutes_diff = get_total_delta_seconds(time_local - time_utc)/60.0
        self.assertGreater(abs(logbook_minutes_diff), 1, "Localtime does not differ from UTC by more than 1 minute (Local: %s, UTC: %s)" % (time_local, time_utc))

        ratio = logbook_minutes_diff / tz_minutes_diff

        self.assertGreater(ratio, 0.99)
        self.assertLess(ratio, 1.01)

class BasicAPITestCase_Regular(_BasicAPITestCase):
    def setUp(self):
        super(BasicAPITestCase_Regular, self).setUp()
        self.thread_activation_strategy = activate_via_with_statement

class BasicAPITestCase_Contextmgr(_BasicAPITestCase):
    def setUp(self):
        super(BasicAPITestCase_Contextmgr, self).setUp()
        self.thread_activation_strategy = activate_via_push_pop

class _HandlerTestCase(LogbookTestCase):
    def setUp(self):
        super(_HandlerTestCase, self).setUp()
        self.dirname = tempfile.mkdtemp()
        self.filename = os.path.join(self.dirname, 'log.tmp')

    def tearDown(self):
        shutil.rmtree(self.dirname)
        super(_HandlerTestCase, self).tearDown()

    def test_file_handler(self):
        handler = logbook.FileHandler(self.filename,
            format_string='{record.level_name}:{record.channel}:'
            '{record.message}',)
        with self.thread_activation_strategy(handler):
            self.log.warn('warning message')
        handler.close()
        with open(self.filename) as f:
            self.assertEqual(f.readline(),
                             'WARNING:testlogger:warning message\n')

    def test_file_handler_unicode(self):
        with capturing_stderr_context() as captured:
            with self.thread_activation_strategy(logbook.FileHandler(self.filename)) as h:
                self.log.info(u('\u0431'))
        self.assertFalse(captured.getvalue())

    def test_file_handler_delay(self):
        handler = logbook.FileHandler(self.filename,
            format_string='{record.level_name}:{record.channel}:'
            '{record.message}', delay=True)
        self.assertFalse(os.path.isfile(self.filename))
        with self.thread_activation_strategy(handler):
            self.log.warn('warning message')
        handler.close()

        with open(self.filename) as f:
            self.assertEqual(f.readline(),
                             'WARNING:testlogger:warning message\n')

    def test_monitoring_file_handler(self):
        if os.name == "nt":
            self.skipTest("unsupported on windows due to different IO (also unneeded)")
        handler = logbook.MonitoringFileHandler(self.filename,
            format_string='{record.level_name}:{record.channel}:'
            '{record.message}', delay=True)
        with self.thread_activation_strategy(handler):
            self.log.warn('warning message')
            os.rename(self.filename, self.filename + '.old')
            self.log.warn('another warning message')
        handler.close()
        with open(self.filename) as f:
            self.assertEqual(f.read().strip(),
                             'WARNING:testlogger:another warning message')

    def test_custom_formatter(self):
        def custom_format(record, handler):
            return record.level_name + ':' + record.message
        handler = logbook.FileHandler(self.filename)
        with self.thread_activation_strategy(handler):
            handler.formatter = custom_format
            self.log.warn('Custom formatters are awesome')

        with open(self.filename) as f:
            self.assertEqual(f.readline(),
                             'WARNING:Custom formatters are awesome\n')

    def test_rotating_file_handler(self):
        basename = os.path.join(self.dirname, 'rot.log')
        handler = logbook.RotatingFileHandler(basename, max_size=2048,
                                              backup_count=3,
                                              )
        handler.format_string = '{record.message}'
        with self.thread_activation_strategy(handler):
            for c, x in zip(LETTERS, xrange(32)):
                self.log.warn(c * 256)
        files = [x for x in os.listdir(self.dirname)
                 if x.startswith('rot.log')]
        files.sort()

        self.assertEqual(files, ['rot.log', 'rot.log.1', 'rot.log.2',
                                 'rot.log.3'])
        with open(basename) as f:
            self.assertEqual(f.readline().rstrip(), 'C' * 256)
            self.assertEqual(f.readline().rstrip(), 'D' * 256)
            self.assertEqual(f.readline().rstrip(), 'E' * 256)
            self.assertEqual(f.readline().rstrip(), 'F' * 256)

    def test_timed_rotating_file_handler(self):
        basename = os.path.join(self.dirname, 'trot.log')
        handler = logbook.TimedRotatingFileHandler(basename, backup_count=3)
        handler.format_string = '[{record.time:%H:%M}] {record.message}'

        def fake_record(message, year, month, day, hour=0,
                        minute=0, second=0):
            lr = logbook.LogRecord('Test Logger', logbook.WARNING,
                                   message)
            lr.time = datetime(year, month, day, hour, minute, second)
            return lr

        with self.thread_activation_strategy(handler):
            for x in xrange(10):
                handler.handle(fake_record('First One', 2010, 1, 5, x + 1))
            for x in xrange(20):
                handler.handle(fake_record('Second One', 2010, 1, 6, x + 1))
            for x in xrange(10):
                handler.handle(fake_record('Third One', 2010, 1, 7, x + 1))
            for x in xrange(20):
                handler.handle(fake_record('Last One', 2010, 1, 8, x + 1))

        files = sorted(
            x for x in os.listdir(self.dirname) if x.startswith('trot')
        )
        self.assertEqual(files, ['trot-2010-01-06.log', 'trot-2010-01-07.log',
                                 'trot-2010-01-08.log'])
        with open(os.path.join(self.dirname, 'trot-2010-01-08.log')) as f:
            self.assertEqual(f.readline().rstrip(), '[01:00] Last One')
            self.assertEqual(f.readline().rstrip(), '[02:00] Last One')
        with open(os.path.join(self.dirname, 'trot-2010-01-07.log')) as f:
            self.assertEqual(f.readline().rstrip(), '[01:00] Third One')
            self.assertEqual(f.readline().rstrip(), '[02:00] Third One')

    def test_mail_handler(self):
        subject = u('\xf8nicode')
        handler = make_fake_mail_handler(subject=subject)
        with capturing_stderr_context() as fallback:
            with self.thread_activation_strategy(handler):
                self.log.warn('This is not mailed')
                try:
                    1 / 0
                except Exception:
                    self.log.exception(u('Viva la Espa\xf1a'))

            if not handler.mails:
                # if sending the mail failed, the reason should be on stderr
                self.fail(fallback.getvalue())

            self.assertEqual(len(handler.mails), 1)
            sender, receivers, mail = handler.mails[0]
            mail = mail.replace("\r", "")
            self.assertEqual(sender, handler.from_addr)
            self.assert_('=?utf-8?q?=C3=B8nicode?=' in mail)
            header, data = mail.split("\n\n", 1)
            if "Content-Transfer-Encoding: base64" in header:
                data = base64.b64decode(data).decode("utf-8")
            self.assertRegexpMatches(data, 'Message type:\s+ERROR')
            self.assertRegexpMatches(data, 'Location:.*%s' % __file_without_pyc__)
            self.assertRegexpMatches(data, 'Module:\s+%s' % __name__)
            self.assertRegexpMatches(data, 'Function:\s+test_mail_handler')
            body = u('Viva la Espa\xf1a')
            if sys.version_info < (3, 0):
                body = body.encode('utf-8')
            self.assertIn(body, data)
            self.assertIn('\nTraceback (most', data)
            self.assertIn('1 / 0', data)
            self.assertIn('This is not mailed', fallback.getvalue())

    def test_mail_handler_record_limits(self):
        suppression_test = re.compile('This message occurred additional \d+ '
                                      'time\(s\) and was suppressed').search
        handler = make_fake_mail_handler(record_limit=1,
                                         record_delta=timedelta(seconds=0.5))
        with self.thread_activation_strategy(handler):
            later = datetime.utcnow() + timedelta(seconds=1.1)
            while datetime.utcnow() < later:
                self.log.error('Over and over...')

            # first mail that is always delivered + 0.5 seconds * 2
            # and 0.1 seconds of room for rounding errors makes 3 mails
            self.assertEqual(len(handler.mails), 3)

            # first mail is always delivered
            self.assert_(not suppression_test(handler.mails[0][2]))

            # the next two have a supression count
            self.assert_(suppression_test(handler.mails[1][2]))
            self.assert_(suppression_test(handler.mails[2][2]))

    def test_mail_handler_batching(self):
        mail_handler = make_fake_mail_handler()
        handler = logbook.FingersCrossedHandler(mail_handler, reset=True)
        with self.thread_activation_strategy(handler):
            self.log.warn('Testing')
            self.log.debug('Even more')
            self.log.error('And this triggers it')
            self.log.info('Aha')
            self.log.error('And this triggers it again!')

        self.assertEqual(len(mail_handler.mails), 2)
        mail = mail_handler.mails[0][2]

        pieces = mail.split('Log records that led up to this one:')
        self.assertEqual(len(pieces), 2)
        body, rest = pieces
        rest = rest.replace("\r", "")

        self.assertRegexpMatches(body, 'Message type:\s+ERROR')
        self.assertRegexpMatches(body, 'Module:\s+%s' % __name__)
        self.assertRegexpMatches(body, 'Function:\s+test_mail_handler_batching')

        related = rest.strip().split('\n\n')
        self.assertEqual(len(related), 2)
        self.assertRegexpMatches(related[0], 'Message type:\s+WARNING')
        self.assertRegexpMatches(related[1], 'Message type:\s+DEBUG')

        self.assertIn('And this triggers it again', mail_handler.mails[1][2])

    def test_group_handler_mail_combo(self):
        mail_handler = make_fake_mail_handler(level=logbook.DEBUG)
        handler = logbook.GroupHandler(mail_handler)
        with self.thread_activation_strategy(handler):
            self.log.error('The other way round')
            self.log.warn('Testing')
            self.log.debug('Even more')
            self.assertEqual(mail_handler.mails, [])

        self.assertEqual(len(mail_handler.mails), 1)
        mail = mail_handler.mails[0][2]

        pieces = mail.split('Other log records in the same group:')
        self.assertEqual(len(pieces), 2)
        body, rest = pieces
        rest = rest.replace("\r", "")

        self.assertRegexpMatches(body, 'Message type:\s+ERROR')
        self.assertRegexpMatches(body, 'Module:\s+'+__name__)
        self.assertRegexpMatches(body, 'Function:\s+test_group_handler_mail_combo')

        related = rest.strip().split('\n\n')
        self.assertEqual(len(related), 2)
        self.assertRegexpMatches(related[0], 'Message type:\s+WARNING')
        self.assertRegexpMatches(related[1], 'Message type:\s+DEBUG')

    def test_syslog_handler(self):
        to_test = [
            (socket.AF_INET, ('127.0.0.1', 0)),
        ]
        if hasattr(socket, 'AF_UNIX'):
            to_test.append((socket.AF_UNIX, self.filename))
        for sock_family, address in to_test:
            with closing(socket.socket(sock_family, socket.SOCK_DGRAM)) as inc:
                inc.bind(address)
                inc.settimeout(1)
                for app_name in [None, 'Testing']:
                    handler = logbook.SyslogHandler(app_name, inc.getsockname())
                    with self.thread_activation_strategy(handler):
                        self.log.warn('Syslog is weird')
                    try:
                        rv = inc.recvfrom(1024)[0]
                    except socket.error:
                        self.fail('got timeout on socket')
                    self.assertEqual(rv, (
                        u('<12>%stestlogger: Syslog is weird\x00') %
                        (app_name and app_name + u(':') or u(''))).encode('utf-8'))

    def test_handler_processors(self):
        handler = make_fake_mail_handler(format_string='''\
Subject: Application Error for {record.extra[path]} [{record.extra[method]}]

Message type:       {record.level_name}
Location:           {record.filename}:{record.lineno}
Module:             {record.module}
Function:           {record.func_name}
Time:               {record.time:%Y-%m-%d %H:%M:%S}
Remote IP:          {record.extra[ip]}
Request:            {record.extra[path]} [{record.extra[method]}]

Message:

{record.message}
''')

        class Request(object):
            remote_addr = '127.0.0.1'
            method = 'GET'
            path = '/index.html'

        def handle_request(request):
            def inject_extra(record):
                record.extra['ip'] = request.remote_addr
                record.extra['method'] = request.method
                record.extra['path'] = request.path

            processor = logbook.Processor(inject_extra)
            with self.thread_activation_strategy(processor):
                handler.push_thread()
                try:
                    try:
                        1 / 0
                    except Exception:
                        self.log.exception('Exception happened during request')
                finally:
                    handler.pop_thread()

        handle_request(Request())
        self.assertEqual(len(handler.mails), 1)
        mail = handler.mails[0][2]
        self.assertIn('Subject: Application Error '
                     'for /index.html [GET]', mail)
        self.assertIn('1 / 0', mail)

    def test_regex_matching(self):
        test_handler = logbook.TestHandler()
        with self.thread_activation_strategy(test_handler):
            self.log.warn('Hello World!')
            self.assert_(test_handler.has_warning(re.compile('^Hello')))
            self.assert_(not test_handler.has_warning(re.compile('world$')))
            self.assert_(not test_handler.has_warning('^Hello World'))

    def test_custom_handling_test(self):
        class MyTestHandler(logbook.TestHandler):
            def handle(self, record):
                if record.extra.get('flag') != 'testing':
                    return False
                return logbook.TestHandler.handle(self, record)

        class MyLogger(logbook.Logger):
            def process_record(self, record):
                logbook.Logger.process_record(self, record)
                record.extra['flag'] = 'testing'
        log = MyLogger()
        handler = MyTestHandler()
        with capturing_stderr_context() as captured:
            with self.thread_activation_strategy(handler):
                log.warn('From my logger')
                self.log.warn('From another logger')
            self.assert_(handler.has_warning('From my logger'))
            self.assertIn('From another logger', captured.getvalue())

    def test_custom_handling_tester(self):
        flag = True

        class MyTestHandler(logbook.TestHandler):
            def should_handle(self, record):
                return flag
        null_handler = logbook.NullHandler()
        with self.thread_activation_strategy(null_handler):
            test_handler = MyTestHandler()
            with self.thread_activation_strategy(test_handler):
                self.log.warn('1')
                flag = False
                self.log.warn('2')
                self.assert_(test_handler.has_warning('1'))
                self.assert_(not test_handler.has_warning('2'))

    def test_null_handler(self):
        with capturing_stderr_context() as captured:
            with self.thread_activation_strategy(logbook.NullHandler()) as null_handler:
                with self.thread_activation_strategy(logbook.TestHandler(level='ERROR')) as handler:
                    self.log.error('An error')
                    self.log.warn('A warning')
            self.assertEqual(captured.getvalue(), '')
            self.assertFalse(handler.has_warning('A warning'))
            self.assert_(handler.has_error('An error'))

    def test_test_handler_cache(self):
        with self.thread_activation_strategy(logbook.TestHandler()) as handler:
            self.log.warn('First line')
            self.assertEqual(len(handler.formatted_records),1)
            cache = handler.formatted_records # store cache, to make sure it is identifiable
            self.assertEqual(len(handler.formatted_records),1)
            self.assert_(cache is handler.formatted_records) # Make sure cache is not invalidated without changes to record
            self.log.warn('Second line invalidates cache')
        self.assertEqual(len(handler.formatted_records),2)
        self.assertFalse(cache is handler.formatted_records) # Make sure cache is invalidated when records change

    def test_blackhole_setting(self):
        null_handler = logbook.NullHandler()
        heavy_init = logbook.LogRecord.heavy_init
        with self.thread_activation_strategy(null_handler):
            def new_heavy_init(self):
                raise RuntimeError('should not be triggered')
            logbook.LogRecord.heavy_init = new_heavy_init
            try:
                with self.thread_activation_strategy(null_handler):
                    logbook.warn('Awesome')
            finally:
                logbook.LogRecord.heavy_init = heavy_init

        null_handler.bubble = True
        with capturing_stderr_context() as captured:
            logbook.warning('Not a blockhole')
            self.assertNotEqual(captured.getvalue(), '')

    def test_calling_frame(self):
        handler = logbook.TestHandler()
        with self.thread_activation_strategy(handler):
            logbook.warn('test')
        self.assertEqual(handler.records[0].calling_frame, sys._getframe())

    def test_nested_setups(self):
        with capturing_stderr_context() as captured:
            logger = logbook.Logger('App')
            test_handler = logbook.TestHandler(level='WARNING')
            mail_handler = make_fake_mail_handler(bubble=True)

            handlers = logbook.NestedSetup([
                logbook.NullHandler(),
                test_handler,
                mail_handler
            ])

            with self.thread_activation_strategy(handlers):
                logger.warn('This is a warning')
                logger.error('This is also a mail')
                try:
                    1 / 0
                except Exception:
                    logger.exception()
            logger.warn('And here we go straight back to stderr')

            self.assert_(test_handler.has_warning('This is a warning'))
            self.assert_(test_handler.has_error('This is also a mail'))
            self.assertEqual(len(mail_handler.mails), 2)
            self.assertIn('This is also a mail', mail_handler.mails[0][2])
            self.assertIn('1 / 0',mail_handler.mails[1][2])
            self.assertIn('And here we go straight back to stderr',
                         captured.getvalue())

            with self.thread_activation_strategy(handlers):
                logger.warn('threadbound warning')

            handlers.push_application()
            try:
                logger.warn('applicationbound warning')
            finally:
                handlers.pop_application()

    def test_dispatcher(self):
        logger = logbook.Logger('App')
        with self.thread_activation_strategy(logbook.TestHandler()) as test_handler:
            logger.warn('Logbook is too awesome for stdlib')
            self.assertEqual(test_handler.records[0].dispatcher, logger)

    def test_filtering(self):
        logger1 = logbook.Logger('Logger1')
        logger2 = logbook.Logger('Logger2')
        handler = logbook.TestHandler()
        outer_handler = logbook.TestHandler()

        def only_1(record, handler):
            return record.dispatcher is logger1
        handler.filter = only_1

        with self.thread_activation_strategy(outer_handler):
            with self.thread_activation_strategy(handler):
                logger1.warn('foo')
                logger2.warn('bar')

        self.assert_(handler.has_warning('foo', channel='Logger1'))
        self.assertFalse(handler.has_warning('bar', channel='Logger2'))
        self.assertFalse(outer_handler.has_warning('foo', channel='Logger1'))
        self.assert_(outer_handler.has_warning('bar', channel='Logger2'))

    def test_null_handler_filtering(self):
        logger1 = logbook.Logger("1")
        logger2 = logbook.Logger("2")
        outer = logbook.TestHandler()
        inner = logbook.NullHandler()

        inner.filter = lambda record, handler: record.dispatcher is logger1

        with self.thread_activation_strategy(outer):
            with self.thread_activation_strategy(inner):
                logger1.warn("1")
                logger2.warn("2")

        self.assertTrue(outer.has_warning("2", channel="2"))
        self.assertFalse(outer.has_warning("1", channel="1"))

    def test_different_context_pushing(self):
        h1 = logbook.TestHandler(level=logbook.DEBUG)
        h2 = logbook.TestHandler(level=logbook.INFO)
        h3 = logbook.TestHandler(level=logbook.WARNING)
        logger = logbook.Logger('Testing')

        with self.thread_activation_strategy(h1):
            with self.thread_activation_strategy(h2):
                with self.thread_activation_strategy(h3):
                    logger.warn('Wuuu')
                    logger.info('still awesome')
                    logger.debug('puzzled')

        self.assert_(h1.has_debug('puzzled'))
        self.assert_(h2.has_info('still awesome'))
        self.assert_(h3.has_warning('Wuuu'))
        for handler in h1, h2, h3:
            self.assertEquals(len(handler.records), 1)

    def test_global_functions(self):
        with self.thread_activation_strategy(logbook.TestHandler()) as handler:
            logbook.debug('a debug message')
            logbook.info('an info message')
            logbook.warn('warning part 1')
            logbook.warning('warning part 2')
            logbook.notice('notice')
            logbook.error('an error')
            logbook.critical('pretty critical')
            logbook.log(logbook.CRITICAL, 'critical too')

        self.assert_(handler.has_debug('a debug message'))
        self.assert_(handler.has_info('an info message'))
        self.assert_(handler.has_warning('warning part 1'))
        self.assert_(handler.has_warning('warning part 2'))
        self.assert_(handler.has_notice('notice'))
        self.assert_(handler.has_error('an error'))
        self.assert_(handler.has_critical('pretty critical'))
        self.assert_(handler.has_critical('critical too'))
        self.assertEqual(handler.records[0].channel, 'Generic')
        self.assertIsNone(handler.records[0].dispatcher)

    def test_fingerscrossed(self):
        handler = logbook.FingersCrossedHandler(logbook.default_handler,
                                                logbook.WARNING)

        # if no warning occurs, the infos are not logged
        with self.thread_activation_strategy(handler):
            with capturing_stderr_context() as captured:
                self.log.info('some info')
            self.assertEqual(captured.getvalue(), '')
            self.assert_(not handler.triggered)

        # but if it does, all log messages are output
        with self.thread_activation_strategy(handler):
            with capturing_stderr_context() as captured:
                self.log.info('some info')
                self.log.warning('something happened')
                self.log.info('something else happened')
            logs = captured.getvalue()
            self.assert_('some info' in logs)
            self.assert_('something happened' in logs)
            self.assert_('something else happened' in logs)
            self.assert_(handler.triggered)

    def test_fingerscrossed_factory(self):
        handlers = []

        def handler_factory(record, fch):
            handler = logbook.TestHandler()
            handlers.append(handler)
            return handler

        def make_fch():
            return logbook.FingersCrossedHandler(handler_factory,
                                                 logbook.WARNING)

        fch = make_fch()
        with self.thread_activation_strategy(fch):
            self.log.info('some info')
            self.assertEqual(len(handlers), 0)
            self.log.warning('a warning')
            self.assertEqual(len(handlers), 1)
            self.log.error('an error')
            self.assertEqual(len(handlers), 1)
            self.assert_(handlers[0].has_infos)
            self.assert_(handlers[0].has_warnings)
            self.assert_(handlers[0].has_errors)
            self.assert_(not handlers[0].has_notices)
            self.assert_(not handlers[0].has_criticals)
            self.assert_(not handlers[0].has_debugs)

        fch = make_fch()
        with self.thread_activation_strategy(fch):
            self.log.info('some info')
            self.log.warning('a warning')
            self.assertEqual(len(handlers), 2)

    def test_fingerscrossed_buffer_size(self):
        logger = logbook.Logger('Test')
        test_handler = logbook.TestHandler()
        handler = logbook.FingersCrossedHandler(test_handler, buffer_size=3)

        with self.thread_activation_strategy(handler):
            logger.info('Never gonna give you up')
            logger.warn('Aha!')
            logger.warn('Moar!')
            logger.error('Pure hate!')

        self.assertEqual(test_handler.formatted_records, [
            '[WARNING] Test: Aha!',
            '[WARNING] Test: Moar!',
            '[ERROR] Test: Pure hate!'
        ])


class HandlerTestCase_Regular(_HandlerTestCase):
    def setUp(self):
        super(HandlerTestCase_Regular, self).setUp()
        self.thread_activation_strategy = activate_via_push_pop

class HandlerTestCase_Contextmgr(_HandlerTestCase):
    def setUp(self):
        super(HandlerTestCase_Contextmgr, self).setUp()
        self.thread_activation_strategy = activate_via_with_statement

class AttributeTestCase(LogbookTestCase):

    def test_level_properties(self):
        self.assertEqual(self.log.level, logbook.NOTSET)
        self.assertEqual(self.log.level_name, 'NOTSET')
        self.log.level_name = 'WARNING'
        self.assertEqual(self.log.level, logbook.WARNING)
        self.log.level = logbook.ERROR
        self.assertEqual(self.log.level_name, 'ERROR')

    def test_reflected_properties(self):
        group = logbook.LoggerGroup()
        group.add_logger(self.log)
        self.assertEqual(self.log.group, group)
        group.level = logbook.ERROR
        self.assertEqual(self.log.level, logbook.ERROR)
        self.assertEqual(self.log.level_name, 'ERROR')
        group.level = logbook.WARNING
        self.assertEqual(self.log.level, logbook.WARNING)
        self.assertEqual(self.log.level_name, 'WARNING')
        self.log.level = logbook.CRITICAL
        group.level = logbook.DEBUG
        self.assertEqual(self.log.level, logbook.CRITICAL)
        self.assertEqual(self.log.level_name, 'CRITICAL')
        group.remove_logger(self.log)
        self.assertEqual(self.log.group, None)

class LevelLookupTest(LogbookTestCase):
    def test_level_lookup_failures(self):
        with self.assertRaises(LookupError):
            logbook.get_level_name(37)
        with self.assertRaises(LookupError):
            logbook.lookup_level('FOO')

class FlagsTestCase(LogbookTestCase):
    def test_error_flag(self):
        with capturing_stderr_context() as captured:
            with logbook.Flags(errors='print'):
                with logbook.Flags(errors='silent'):
                    self.log.warn('Foo {42}', 'aha')
            self.assertEqual(captured.getvalue(), '')

            with logbook.Flags(errors='silent'):
                with logbook.Flags(errors='print'):
                    self.log.warn('Foo {42}', 'aha')
            self.assertNotEqual(captured.getvalue(), '')

            with self.assertRaises(Exception) as caught:
                with logbook.Flags(errors='raise'):
                    self.log.warn('Foo {42}', 'aha')
            self.assertIn('Could not format message with provided '
                          'arguments', str(caught.exception))

    def test_disable_introspection(self):
        with logbook.Flags(introspection=False):
            with logbook.TestHandler() as h:
                self.log.warn('Testing')
                self.assertIsNone(h.records[0].frame)
                self.assertIsNone(h.records[0].calling_frame)
                self.assertIsNone(h.records[0].module)

class LoggerGroupTestCase(LogbookTestCase):
    def test_groups(self):
        def inject_extra(record):
            record.extra['foo'] = 'bar'
        group = logbook.LoggerGroup(processor=inject_extra)
        group.level = logbook.ERROR
        group.add_logger(self.log)
        with logbook.TestHandler() as handler:
            self.log.warn('A warning')
            self.log.error('An error')
        self.assertFalse(handler.has_warning('A warning'))
        self.assertTrue(handler.has_error('An error'))
        self.assertEqual(handler.records[0].extra['foo'], 'bar')

class DefaultConfigurationTestCase(LogbookTestCase):

    def test_default_handlers(self):
        with capturing_stderr_context() as stream:
            self.log.warn('Aha!')
            captured = stream.getvalue()
        self.assertIn('WARNING: testlogger: Aha!', captured)

class LoggingCompatTestCase(LogbookTestCase):

    def test_basic_compat_with_level_setting(self):
        self._test_basic_compat(True)
    def test_basic_compat_without_level_setting(self):
        self._test_basic_compat(False)

    def _test_basic_compat(self, set_root_logger_level):
        import logging
        from logbook.compat import redirected_logging

        # mimic the default logging setting
        self.addCleanup(logging.root.setLevel, logging.root.level)
        logging.root.setLevel(logging.WARNING)

        name = 'test_logbook-%d' % randrange(1 << 32)
        logger = logging.getLogger(name)

        with logbook.TestHandler(bubble=True) as handler:
            with capturing_stderr_context() as captured:
                with redirected_logging(set_root_logger_level):
                    logger.debug('This is from the old system')
                    logger.info('This is from the old system')
                    logger.warn('This is from the old system')
                    logger.error('This is from the old system')
                    logger.critical('This is from the old system')
            self.assertIn(('WARNING: %s: This is from the old system' % name),
                          captured.getvalue())
        if set_root_logger_level:
            self.assertEquals(handler.records[0].level, logbook.DEBUG)
        else:
            self.assertEquals(handler.records[0].level, logbook.WARNING)

    def test_redirect_logbook(self):
        import logging
        from logbook.compat import LoggingHandler
        out = StringIO()
        logger = logging.getLogger()
        old_handlers = logger.handlers[:]
        handler = logging.StreamHandler(out)
        handler.setFormatter(logging.Formatter(
            '%(name)s:%(levelname)s:%(message)s'))
        logger.handlers[:] = [handler]
        try:
            with logbook.compat.LoggingHandler() as logging_handler:
                self.log.warn("This goes to logging")
                pieces = out.getvalue().strip().split(':')
                self.assertEqual(pieces, [
                    'testlogger',
                    'WARNING',
                    'This goes to logging'
                ])
        finally:
            logger.handlers[:] = old_handlers

class WarningsCompatTestCase(LogbookTestCase):

    def test_warning_redirections(self):
        from logbook.compat import redirected_warnings
        with logbook.TestHandler() as handler:
            redirector = redirected_warnings()
            redirector.start()
            try:
                from warnings import warn
                warn(RuntimeWarning('Testing'))
            finally:
                redirector.end()

        self.assertEqual(len(handler.records), 1)
        self.assertEqual('[WARNING] RuntimeWarning: Testing',
                         handler.formatted_records[0])
        self.assertIn(__file_without_pyc__, handler.records[0].filename)

class MoreTestCase(LogbookTestCase):

    @contextmanager
    def _get_temporary_file_context(self):
        fn = tempfile.mktemp()
        try:
            yield fn
        finally:
            try:
                os.remove(fn)
            except OSError:
                pass

    @require_module('jinja2')
    def test_jinja_formatter(self):
        from logbook.more import JinjaFormatter
        fmter = JinjaFormatter('{{ record.channel }}/{{ record.level_name }}')
        handler = logbook.TestHandler()
        handler.formatter = fmter
        with handler:
            self.log.info('info')
        self.assertIn('testlogger/INFO', handler.formatted_records)

    @missing('jinja2')
    def test_missing_jinja2(self):
        from logbook.more import JinjaFormatter
        # check the RuntimeError is raised
        with self.assertRaises(RuntimeError):
            JinjaFormatter('dummy')

    def test_colorizing_support(self):
        from logbook.more import ColorizedStderrHandler

        class TestColorizingHandler(ColorizedStderrHandler):
            def should_colorize(self, record):
                return True
            stream = StringIO()
        with TestColorizingHandler(format_string='{record.message}') as handler:
            self.log.error('An error')
            self.log.warn('A warning')
            self.log.debug('A debug message')
            lines = handler.stream.getvalue().rstrip('\n').splitlines()
            self.assertEqual(lines, [
                '\x1b[31;01mAn error',
                '\x1b[39;49;00m\x1b[33;01mA warning',
                '\x1b[39;49;00m\x1b[37mA debug message',
                '\x1b[39;49;00m'
            ])

    def test_tagged(self):
        from logbook.more import TaggingLogger, TaggingHandler
        stream = StringIO()
        second_handler = logbook.StreamHandler(stream)

        logger = TaggingLogger('name', ['cmd'])
        handler = TaggingHandler(dict(
            info=logbook.default_handler,
            cmd=second_handler,
            both=[logbook.default_handler, second_handler],
        ))
        handler.bubble = False

        with handler:
            with capturing_stderr_context() as captured:
                logger.log('info', 'info message')
                logger.log('both', 'all message')
                logger.cmd('cmd message')

        stderr = captured.getvalue()

        self.assertIn('info message', stderr)
        self.assertIn('all message', stderr)
        self.assertNotIn('cmd message', stderr)

        stringio = stream.getvalue()

        self.assertNotIn('info message', stringio)
        self.assertIn('all message', stringio)
        self.assertIn('cmd message', stringio)

    def test_external_application_handler(self):
        from logbook.more import ExternalApplicationHandler as Handler
        with self._get_temporary_file_context() as fn:
            handler = Handler([sys.executable, '-c', r'''if 1:
                f = open(%(tempfile)s, 'w')
                try:
                    f.write('{record.message}\n')
                finally:
                    f.close()
            ''' % {'tempfile': repr(fn)}])
            with handler:
                self.log.error('this is a really bad idea')
            with open(fn, 'r') as rf:
                contents = rf.read().strip()
            self.assertEqual(contents, 'this is a really bad idea')

    def test_external_application_handler_stdin(self):
        from logbook.more import ExternalApplicationHandler as Handler
        with self._get_temporary_file_context() as fn:
            handler = Handler([sys.executable, '-c', r'''if 1:
                import sys
                f = open(%(tempfile)s, 'w')
                try:
                    f.write(sys.stdin.read())
                finally:
                    f.close()
            ''' % {'tempfile': repr(fn)}], '{record.message}\n')
            with handler:
                self.log.error('this is a really bad idea')
            with open(fn, 'r') as rf:
                contents = rf.read().strip()
            self.assertEqual(contents, 'this is a really bad idea')

    def test_exception_handler(self):
        from logbook.more import ExceptionHandler

        with ExceptionHandler(ValueError) as exception_handler:
            with self.assertRaises(ValueError) as caught:
                self.log.info('here i am')
        self.assertIn('INFO: testlogger: here i am', caught.exception.args[0])

    def test_exception_handler_specific_level(self):
        from logbook.more import ExceptionHandler
        with logbook.TestHandler() as test_handler:
            with self.assertRaises(ValueError) as caught:
                with ExceptionHandler(ValueError, level='WARNING') as exception_handler:
                    self.log.info('this is irrelevant')
                    self.log.warn('here i am')
            self.assertIn('WARNING: testlogger: here i am', caught.exception.args[0])
        self.assertIn('this is irrelevant', test_handler.records[0].message)

    def test_dedup_handler(self):
        from logbook.more import DedupHandler
        with logbook.TestHandler() as test_handler:
            with DedupHandler():
                self.log.info('foo')
                self.log.info('bar')
                self.log.info('foo')
        self.assertEqual(2, len(test_handler.records))
        self.assertIn('message repeated 2 times: foo', test_handler.records[0].message)
        self.assertIn('message repeated 1 times: bar', test_handler.records[1].message)

class QueuesTestCase(LogbookTestCase):
    def _get_zeromq(self, multi=False):
        from logbook.queues import ZeroMQHandler, ZeroMQSubscriber

        # Get an unused port
        tempsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tempsock.bind(('127.0.0.1', 0))
        host, unused_port = tempsock.getsockname()
        tempsock.close()

        # Retrieve the ZeroMQ handler and subscriber
        uri = 'tcp://%s:%d' % (host, unused_port)
        if multi:
            handler = [ZeroMQHandler(uri, multi=True) for _ in range(3)]
        else:
            handler = ZeroMQHandler(uri)
        subscriber = ZeroMQSubscriber(uri, multi=multi)
        # Enough time to start
        time.sleep(0.1)
        return handler, subscriber

    @require_module('zmq')
    def test_zeromq_handler(self):
        tests = [
            u('Logging something'),
            u('Something with umlauts äöü'),
            u('Something else for good measure'),
        ]
        handler, subscriber = self._get_zeromq()
        for test in tests:
            with handler:
                self.log.warn(test)
                record = subscriber.recv()
                self.assertEqual(record.message, test)
                self.assertEqual(record.channel, self.log.name)

    @require_module('zmq')
    def test_multi_zeromq_handler(self):
        tests = [
            u('Logging something'),
            u('Something with umlauts äöü'),
            u('Something else for good measure'),
        ]
        handlers, subscriber = self._get_zeromq(multi=True)
        for handler in handlers:
            for test in tests:
                with handler:
                    self.log.warn(test)
                    record = subscriber.recv()
                    self.assertEqual(record.message, test)
                    self.assertEqual(record.channel, self.log.name)

    @require_module('zmq')
    def test_zeromq_background_thread(self):
        handler, subscriber = self._get_zeromq()
        test_handler = logbook.TestHandler()
        controller = subscriber.dispatch_in_background(test_handler)

        with handler:
            self.log.warn('This is a warning')
            self.log.error('This is an error')

        # stop the controller.  This will also stop the loop and join the
        # background process.  Before that we give it a fraction of a second
        # to get all results
        time.sleep(0.2)
        controller.stop()

        self.assertTrue(test_handler.has_warning('This is a warning'))
        self.assertTrue(test_handler.has_error('This is an error'))

    @missing('zmq')
    def test_missing_zeromq(self):
        from logbook.queues import ZeroMQHandler, ZeroMQSubscriber
        with self.assertRaises(RuntimeError):
            ZeroMQHandler('tcp://127.0.0.1:42000')
        with self.assertRaises(RuntimeError):
            ZeroMQSubscriber('tcp://127.0.0.1:42000')

    @require_module('multiprocessing')
    def test_multi_processing_handler(self):
        from multiprocessing import Process, Queue
        from logbook.queues import MultiProcessingHandler, \
             MultiProcessingSubscriber
        queue = Queue(-1)
        test_handler = logbook.TestHandler()
        subscriber = MultiProcessingSubscriber(queue)

        def send_back():
            handler = MultiProcessingHandler(queue)
            handler.push_thread()
            try:
                logbook.warn('Hello World')
            finally:
                handler.pop_thread()

        p = Process(target=send_back)
        p.start()
        p.join()

        with test_handler:
            subscriber.dispatch_once()
            self.assert_(test_handler.has_warning('Hello World'))

    def test_threaded_wrapper_handler(self):
        from logbook.queues import ThreadedWrapperHandler
        test_handler = logbook.TestHandler()
        with ThreadedWrapperHandler(test_handler) as handler:
            self.log.warn('Just testing')
            self.log.error('More testing')

        # give it some time to sync up
        handler.close()

        self.assertTrue(not handler.controller.running)
        self.assertTrue(test_handler.has_warning('Just testing'))
        self.assertTrue(test_handler.has_error('More testing'))

    @require_module('execnet')
    def test_execnet_handler(self):
        def run_on_remote(channel):
            import logbook
            from logbook.queues import ExecnetChannelHandler
            handler = ExecnetChannelHandler(channel)
            log = logbook.Logger("Execnet")
            handler.push_application()
            log.info('Execnet works')

        import execnet
        gw = execnet.makegateway()
        channel = gw.remote_exec(run_on_remote)
        from logbook.queues import ExecnetChannelSubscriber
        subscriber = ExecnetChannelSubscriber(channel)
        record = subscriber.recv()
        self.assertEqual(record.msg, 'Execnet works')
        gw.exit()

    @require_module('multiprocessing')
    def test_subscriber_group(self):
        from multiprocessing import Process, Queue
        from logbook.queues import MultiProcessingHandler, \
                                   MultiProcessingSubscriber, SubscriberGroup
        a_queue = Queue(-1)
        b_queue = Queue(-1)
        test_handler = logbook.TestHandler()
        subscriber = SubscriberGroup([
            MultiProcessingSubscriber(a_queue),
            MultiProcessingSubscriber(b_queue)
        ])

        def make_send_back(message, queue):
            def send_back():
                with MultiProcessingHandler(queue):
                    logbook.warn(message)
            return send_back

        for _ in range(10):
            p1 = Process(target=make_send_back('foo', a_queue))
            p2 = Process(target=make_send_back('bar', b_queue))
            p1.start()
            p2.start()
            p1.join()
            p2.join()
            messages = [subscriber.recv().message for i in (1, 2)]
            self.assertEqual(sorted(messages), ['bar', 'foo'])

    @require_module('redis')
    def test_redis_handler(self):
        import redis
        from logbook.queues import RedisHandler

        KEY = 'redis'
        FIELDS = ['message', 'host']
        r = redis.Redis(decode_responses=True)
        redis_handler = RedisHandler(level=logbook.INFO, bubble=True)
        #We don't want output for the tests, so we can wrap everything in a NullHandler
        null_handler = logbook.NullHandler()

        #Check default values
        with null_handler.applicationbound():
            with redis_handler:
                logbook.info(LETTERS)

        key, message = r.blpop(KEY)
        #Are all the fields in the record?
        [self.assertTrue(message.find(field)) for field in FIELDS]
        self.assertEqual(key, KEY)
        self.assertTrue(message.find(LETTERS))

        #Change the key of the handler and check on redis
        KEY = 'test_another_key'
        redis_handler.key = KEY

        with null_handler.applicationbound():
            with redis_handler:
                logbook.info(LETTERS)

        key, message = r.blpop(KEY)
        self.assertEqual(key, KEY)

        #Check that extra fields are added if specified when creating the handler
        FIELDS.append('type')
        extra_fields = {'type': 'test'}
        del(redis_handler)
        redis_handler = RedisHandler(key=KEY, level=logbook.INFO,
                                     extra_fields=extra_fields, bubble=True)

        with null_handler.applicationbound():
            with redis_handler:
                logbook.info(LETTERS)

        key, message = r.blpop(KEY)
        [self.assertTrue(message.find(field)) for field in FIELDS]
        self.assertTrue(message.find('test'))

        #And finally, check that fields are correctly added if appended to the
        #log message
        FIELDS.append('more_info')
        with null_handler.applicationbound():
            with redis_handler:
                logbook.info(LETTERS, more_info='This works')

        key, message = r.blpop(KEY)
        [self.assertTrue(message.find(field)) for field in FIELDS]
        self.assertTrue(message.find('This works'))


class TicketingTestCase(LogbookTestCase):

    @require_module('sqlalchemy')
    def test_basic_ticketing(self):
        from logbook.ticketing import TicketingHandler
        with TicketingHandler('sqlite:///') as handler:
            for x in xrange(5):
                self.log.warn('A warning')
                self.log.info('An error')
                if x < 2:
                    try:
                        1 / 0
                    except Exception:
                        self.log.exception()

        self.assertEqual(handler.db.count_tickets(), 3)
        tickets = handler.db.get_tickets()
        self.assertEqual(len(tickets), 3)
        self.assertEqual(tickets[0].level, logbook.INFO)
        self.assertEqual(tickets[1].level, logbook.WARNING)
        self.assertEqual(tickets[2].level, logbook.ERROR)
        self.assertEqual(tickets[0].occurrence_count, 5)
        self.assertEqual(tickets[1].occurrence_count, 5)
        self.assertEqual(tickets[2].occurrence_count, 2)
        self.assertEqual(tickets[0].last_occurrence.level, logbook.INFO)

        tickets[0].solve()
        self.assert_(tickets[0].solved)
        tickets[0].delete()

        ticket = handler.db.get_ticket(tickets[1].ticket_id)
        self.assertEqual(ticket, tickets[1])

        occurrences = handler.db.get_occurrences(tickets[2].ticket_id,
                                                 order_by='time')
        self.assertEqual(len(occurrences), 2)
        record = occurrences[0]
        self.assertIn(__file_without_pyc__, record.filename)
        # avoid 2to3 destroying our assertion
        self.assertEqual(getattr(record, 'func_name'), 'test_basic_ticketing')
        self.assertEqual(record.level, logbook.ERROR)
        self.assertEqual(record.thread, get_ident())
        self.assertEqual(record.process, os.getpid())
        self.assertEqual(record.channel, 'testlogger')
        self.assertIn('1 / 0', record.formatted_exception)

class HelperTestCase(LogbookTestCase):

    def test_jsonhelper(self):
        from logbook.helpers import to_safe_json

        class Bogus(object):
            def __str__(self):
                return 'bogus'

        rv = to_safe_json([
            None,
            'foo',
            u('jäger'),
            1,
            datetime(2000, 1, 1),
            {'jäger1': 1, u('jäger2'): 2, Bogus(): 3, 'invalid': object()},
            object()  # invalid
        ])
        self.assertEqual(
            rv, [None, u('foo'), u('jäger'), 1, '2000-01-01T00:00:00Z',
                 {u('jäger1'): 1, u('jäger2'): 2, u('bogus'): 3,
                  u('invalid'): None}, None])

    def test_datehelpers(self):
        from logbook.helpers import format_iso8601, parse_iso8601
        now = datetime.now()
        rv = format_iso8601()
        self.assertEqual(rv[:4], str(now.year))

        self.assertRaises(ValueError, parse_iso8601, 'foo')
        v = parse_iso8601('2000-01-01T00:00:00.12Z')
        self.assertEqual(v.microsecond, 120000)
        v = parse_iso8601('2000-01-01T12:00:00+01:00')
        self.assertEqual(v.hour, 11)
        v = parse_iso8601('2000-01-01T12:00:00-01:00')
        self.assertEqual(v.hour, 13)

class UnicodeTestCase(LogbookTestCase):
    # in Py3 we can just assume a more uniform unicode environment
    @require_py3
    def test_default_format_unicode(self):
        with capturing_stderr_context() as stream:
            self.log.warn('\u2603')
        self.assertIn('WARNING: testlogger: \u2603', stream.getvalue())

    @require_py3
    def test_default_format_encoded(self):
        with capturing_stderr_context() as stream:
            # it's a string but it's in the right encoding so don't barf
            self.log.warn('\u2603')
        self.assertIn('WARNING: testlogger: \u2603', stream.getvalue())

    @require_py3
    def test_default_format_bad_encoding(self):
        with capturing_stderr_context() as stream:
            # it's a string, is wrong, but just dump it in the logger,
            # don't try to decode/encode it
            self.log.warn('Русский'.encode('koi8-r'))
        self.assertIn("WARNING: testlogger: b'\\xf2\\xd5\\xd3\\xd3\\xcb\\xc9\\xca'", stream.getvalue())

    @require_py3
    def test_custom_unicode_format_unicode(self):
        format_string = ('[{record.level_name}] '
                         '{record.channel}: {record.message}')
        with capturing_stderr_context() as stream:
            with logbook.StderrHandler(format_string=format_string):
                self.log.warn("\u2603")
        self.assertIn('[WARNING] testlogger: \u2603', stream.getvalue())

    @require_py3
    def test_custom_string_format_unicode(self):
        format_string = ('[{record.level_name}] '
            '{record.channel}: {record.message}')
        with capturing_stderr_context() as stream:
            with logbook.StderrHandler(format_string=format_string):
                self.log.warn('\u2603')
        self.assertIn('[WARNING] testlogger: \u2603', stream.getvalue())

    @require_py3
    def test_unicode_message_encoded_params(self):
        with capturing_stderr_context() as stream:
            self.log.warn("\u2603 {0}", "\u2603".encode('utf8'))
        self.assertIn("WARNING: testlogger: \u2603 b'\\xe2\\x98\\x83'", stream.getvalue())

    @require_py3
    def test_encoded_message_unicode_params(self):
        with capturing_stderr_context() as stream:
            self.log.warn('\u2603 {0}'.encode('utf8'), '\u2603')
        self.assertIn('WARNING: testlogger: \u2603 \u2603', stream.getvalue())

########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-
"""
    test utils for logbook
    ~~~~~~~~~~~~~~~~~~~~~~

    :copyright: (c) 2010 by Armin Ronacher, Georg Brandl.
    :license: BSD, see LICENSE for more details.
"""
from contextlib import contextmanager
import platform
import sys

if platform.python_version() < "2.7":
    import unittest2 as unittest
else:
    import unittest
import logbook
from logbook.helpers import StringIO

_missing = object()


def get_total_delta_seconds(delta):
    """
    Replacement for datetime.timedelta.total_seconds() for Python 2.5, 2.6 and 3.1
    """
    return (delta.microseconds + (delta.seconds + delta.days * 24 * 3600) * 10**6) / 10**6


require_py3 = unittest.skipUnless(sys.version_info[0] == 3, "Requires Python 3")
def require_module(module_name):
    try:
        __import__(module_name)
    except ImportError:
        return unittest.skip("Requires the %r module" % (module_name,))
    return lambda func: func

class LogbookTestSuite(unittest.TestSuite):
    pass

class LogbookTestCase(unittest.TestCase):
    def setUp(self):
        self.log = logbook.Logger('testlogger')

# silence deprecation warning displayed on Py 3.2
LogbookTestCase.assert_ = LogbookTestCase.assertTrue

def make_fake_mail_handler(**kwargs):
    class FakeMailHandler(logbook.MailHandler):
        mails = []

        def get_connection(self):
            return self

        def close_connection(self, con):
            pass

        def sendmail(self, fromaddr, recipients, mail):
            self.mails.append((fromaddr, recipients, mail))

    kwargs.setdefault('level', logbook.ERROR)
    return FakeMailHandler('foo@example.com', ['bar@example.com'], **kwargs)


def missing(name):
    def decorate(f):
        def wrapper(*args, **kwargs):
            old = sys.modules.get(name, _missing)
            sys.modules[name] = None
            try:
                f(*args, **kwargs)
            finally:
                if old is _missing:
                    del sys.modules[name]
                else:
                    sys.modules[name] = old
        return wrapper
    return decorate

def activate_via_with_statement(handler):
    return handler

@contextmanager
def activate_via_push_pop(handler):
    handler.push_thread()
    try:
        yield handler
    finally:
        handler.pop_thread()

@contextmanager
def capturing_stderr_context():
    original = sys.stderr
    sys.stderr = StringIO()
    try:
        yield sys.stderr
    finally:
        sys.stderr = original

########NEW FILE########
__FILENAME__ = testwin32log
from logbook import NTEventLogHandler, Logger

logger = Logger('MyLogger')
handler = NTEventLogHandler('My Application')

with handler.applicationbound():
    logger.error('Testing')

########NEW FILE########
