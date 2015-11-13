__FILENAME__ = some_module
from structlog import get_logger

logger = get_logger()


def some_function():
    # later then:
    logger.error('user did something', something='shot_in_foot')
    # gives you:
    # event='user did something 'request_id='ffcdc44f-b952-4b5f-95e6-0f1f3a9ee5fd' something='shot_in_foot'


########NEW FILE########
__FILENAME__ = webapp
import uuid

import flask
import structlog

from .some_module import some_function


logger = structlog.get_logger()
app = flask.Flask(__name__)


@app.route('/login', methods=['POST', 'GET'])
def some_route():
    log = logger.new(
        request_id=str(uuid.uuid4()),
    )
    # do something
    # ...
    log.info('user logged in', user='test-user')
    # gives you:
    # event='user logged in' request_id='ffcdc44f-b952-4b5f-95e6-0f1f3a9ee5fd' user='test-user'
    # ...
    some_function()
    # ...

if __name__ == "__main__":
    structlog.configure(
        processors=[
            structlog.processors.KeyValueRenderer(
                key_order=['event', 'request_id'],
            ),
        ],
        context_class=structlog.threadlocal.wrap_dict(dict),
        logger_factory=structlog.stdlib.LoggerFactory(),
    )
    app.run()

########NEW FILE########
__FILENAME__ = imaginary_web
from structlog import get_logger

log = get_logger()


def view(request):
    user_agent = request.get('HTTP_USER_AGENT', 'UNKNOWN')
    peer_ip = request.client_addr
    if something:
        log.msg('something', user_agent=user_agent, peer_ip=peer_ip)
        return 'something'
    elif something_else:
        log.msg('something_else', user_agent=user_agent, peer_ip=peer_ip)
        return 'something_else'
    else:
        log.msg('else', user_agent=user_agent, peer_ip=peer_ip)
        return 'else'

########NEW FILE########
__FILENAME__ = imaginary_web_better
from structlog import get_logger

logger = get_logger()


def view(request):
    log = logger.bind(
        user_agent=request.get('HTTP_USER_AGENT', 'UNKNOWN'),
        peer_ip=request.client_addr,
    )
    foo = request.get('foo')
    if foo:
        log = log.bind(foo=foo)
    if something:
        log.msg('something')
        return 'something'
    elif something_else:
        log.msg('something_else')
        return 'something_else'
    else:
        log.msg('else')
        return 'else'

########NEW FILE########
__FILENAME__ = conditional_dropper
from structlog import DropEvent


class ConditionalDropper(object):
    def __init__(self, peer_to_ignore):
        self._peer_to_ignore = peer_to_ignore

    def __call__(self, logger, method_name, event_dict):
        """
        >>> cd = ConditionalDropper('127.0.0.1')
        >>> cd(None, None, {'event': 'foo', 'peer': '10.0.0.1'})
        {'peer': '10.0.0.1', 'event': 'foo'}
        >>> cd(None, None, {'event': 'foo', 'peer': '127.0.0.1'})
        Traceback (most recent call last):
        ...
        DropEvent
        """
        if event_dict.get('peer') == self._peer_to_ignore:
            raise DropEvent
        else:
            return event_dict

########NEW FILE########
__FILENAME__ = dropper
from structlog import DropEvent


def dropper(logger, method_name, event_dict):
    raise DropEvent

########NEW FILE########
__FILENAME__ = timestamper
import calendar
import time


def timestamper(logger, log_method, event_dict):
    event_dict['timestamp'] = calendar.timegm(time.gmtime())
    return event_dict

########NEW FILE########
__FILENAME__ = twisted_echo
import sys
import uuid

import structlog
import twisted

from twisted.internet import protocol, reactor

logger = structlog.getLogger()


class Counter(object):
    i = 0

    def inc(self):
        self.i += 1

    def __repr__(self):
        return str(self.i)


class Echo(protocol.Protocol):
    def connectionMade(self):
        self._counter = Counter()
        self._log = logger.new(
            connection_id=str(uuid.uuid4()),
            peer=self.transport.getPeer().host,
            count=self._counter,
        )

    def dataReceived(self, data):
        self._counter.inc()
        log = self._log.bind(data=data)
        self.transport.write(data)
        log.msg('echoed data!')


if __name__ == "__main__":
    structlog.configure(
        processors=[structlog.twisted.EventAdapter()],
        logger_factory=structlog.twisted.LoggerFactory(),
    )
    twisted.python.log.startLogging(sys.stderr)
    reactor.listenTCP(1234, protocol.Factory.forProtocol(Echo))
    reactor.run()

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# structlog documentation build configuration file, created by
# sphinx-quickstart on Sun Aug 18 13:21:52 2013.
#
# This file is execfile()d with the current directory set to its containing dir
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import codecs
import os
import re

try:
    import sphinx_rtd_theme
except ImportError:
    sphinx_rtd_theme = None


here = os.path.abspath(os.path.dirname(__file__))


def read(*parts):
    return codecs.open(os.path.join(here, *parts), 'r').read()


def find_version(*file_paths):
    version_file = read(*file_paths)
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]",
                              version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")


# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))

# -- General configuration ----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = [
    'releases',
    'sphinx.ext.autodoc',
    'sphinx.ext.doctest',
    'sphinx.ext.viewcode',
]

# 'releases' (changelog) settings
releases_issue_uri = "https://github.com/hynek/structlog/issues/%s"
releases_release_uri = "https://github.com/hynek/structlog/tree/%s"

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'structlog'
copyright = u'2013, Hynek Schlawack'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = find_version('..', 'structlog', '__init__.py')
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

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = [
    '_build',
]

# The reST default role (used for this markup: `text`) to use for all
# documents.
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


# -- Options for HTML output --------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
if sphinx_rtd_theme:
    html_theme = "sphinx_rtd_theme"
    html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]
else:
    html_theme = "default"

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
# html_theme_path = ['_themes']

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
htmlhelp_basename = 'structlogdoc'


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
  ('index', 'structlog.tex', u'structlog Documentation',
   u'Author', 'manual'),
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
    ('index', 'structlog', u'structlog Documentation',
     [u'Author'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'structlog', u'structlog Documentation',
   u'Author', 'structlog', 'One line description of project.',
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
epub_title = u'structlog'
epub_author = u'Author'
epub_publisher = u'Author'
epub_copyright = u'2013, Author'

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

linkcheck_ignore = [
    # fake links
    r'https://github.com/hynek/structlog/issues/0',
    # 404s for unknown reasons
    r'http://graylog2.org.*',
    # Times out way too often
    r'http://www.rabbitmq.com',
    # throws a 406 for unknown reasons
    r'http://www.elasticsearch.org',
]

# Twisted's trac tends to be slow
linkcheck_timeout = 300

########NEW FILE########
__FILENAME__ = processors
# Copyright 2013 Hynek Schlawack
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Processors useful regardless of the logging framework.
"""

from __future__ import absolute_import, division, print_function

import calendar
import datetime
import json
import operator
import sys
import time

from structlog._compat import unicode_type
from structlog._frames import (
    _find_first_app_frame_and_name,
    _format_exception,
    _format_stack,
)


class KeyValueRenderer(object):
    """
    Render `event_dict` as a list of ``Key=repr(Value)`` pairs.

    :param bool sort_keys: Whether to sort keys when formatting.
    :param list key_order: List of keys that should be rendered in this exact
        order.  Missing keys will be rendered as `None`, extra keys depending
        on *sort_keys* and the dict class.


    >>> from structlog.processors import KeyValueRenderer
    >>> KeyValueRenderer(sort_keys=True)(None, None, {'a': 42, 'b': [1, 2, 3]})
    'a=42 b=[1, 2, 3]'
    >>> KeyValueRenderer(key_order=['b', 'a'])(None, None,
    ...                                       {'a': 42, 'b': [1, 2, 3]})
    'b=[1, 2, 3] a=42'

    .. versionadded:: 0.2.0
        `key_order`
    """
    def __init__(self, sort_keys=False, key_order=None):
        # Use an optimized version for each case.
        if key_order and sort_keys:
            def ordered_items(event_dict):
                items = []
                for key in key_order:
                    value = event_dict.pop(key, None)
                    items.append((key, value))
                items += sorted(event_dict.items())
                return items
        elif key_order:
            def ordered_items(event_dict):
                items = []
                for key in key_order:
                    value = event_dict.pop(key, None)
                    items.append((key, value))
                items += event_dict.items()
                return items
        elif sort_keys:
            def ordered_items(event_dict):
                return sorted(event_dict.items())
        else:
            ordered_items = operator.methodcaller('items')

        self._ordered_items = ordered_items

    def __call__(self, _, __, event_dict):
        return ' '.join(k + '=' + repr(v)
                        for k, v in self._ordered_items(event_dict))


class UnicodeEncoder(object):
    """
    Encode unicode values in `event_dict`.

    :param str encoding: Encoding to encode to (default: ``'utf-8'``.
    :param str errors: How to cope with encoding errors (default
        ``'backslashreplace'``).

    Useful for :class:`KeyValueRenderer` if you don't want to see u-prefixes:

    >>> from structlog.processors import KeyValueRenderer, UnicodeEncoder
    >>> KeyValueRenderer()(None, None, {'foo': u'bar'})
    "foo=u'bar'"
    >>> KeyValueRenderer()(None, None,
    ...                    UnicodeEncoder()(None, None, {'foo': u'bar'}))
    "foo='bar'"

    or :class:`JSONRenderer` and :class:`structlog.twisted.JSONRenderer` to
    make sure user-supplied strings don't break the renderer.

    Just put it in the processor chain before the renderer.
    """
    def __init__(self, encoding='utf-8', errors='backslashreplace'):
        self._encoding = encoding
        self._errors = errors

    def __call__(self, logger, name, event_dict):
        for key, value in event_dict.items():
            if isinstance(value, unicode_type):
                event_dict[key] = value.encode(self._encoding, self._errors)
        return event_dict


class JSONRenderer(object):
    """
    Render the `event_dict` using `json.dumps(event_dict, **json_kw)`.

    :param json_kw: Are passed unmodified to `json.dumps()`.

    >>> from structlog.processors import JSONRenderer
    >>> JSONRenderer(sort_keys=True)(None, None, {'a': 42, 'b': [1, 2, 3]})
    '{"a": 42, "b": [1, 2, 3]}'

    Bound objects are attempted to be serialize using a ``__structlog__``
    method.  If none is defined, ``repr()`` is used:

    >>> class C1(object):
    ...     def __structlog__(self):
    ...         return ['C1!']
    ...     def __repr__(self):
    ...         return '__structlog__ took precedence'
    >>> class C2(object):
    ...     def __repr__(self):
    ...         return 'No __structlog__, so this is used.'
    >>> from structlog.processors import JSONRenderer
    >>> JSONRenderer(sort_keys=True)(None, None, {'c1': C1(), 'c2': C2()})
    '{"c1": ["C1!"], "c2": "No __structlog__, so this is used."}'

    Please note that additionally to strings, you can also return any type
    the standard library JSON module knows about -- like in this example
    a list.

    .. versionchanged:: 0.2.0
        Added support for ``__structlog__`` serialization method.
    """
    def __init__(self, **dumps_kw):
        self._dumps_kw = dumps_kw

    def __call__(self, logger, name, event_dict):
        return json.dumps(event_dict, cls=_JSONFallbackEncoder,
                          **self._dumps_kw)


class _JSONFallbackEncoder(json.JSONEncoder):
    """
    Serialize custom datatypes and pass the rest to __structlog__ & repr().
    """
    def default(self, obj):
        """
        Serialize obj with repr(obj) as fallback.
        """
        # circular imports :(
        from structlog.threadlocal import _ThreadLocalDictWrapper
        if isinstance(obj, _ThreadLocalDictWrapper):
            return obj._dict
        else:
            try:
                return obj.__structlog__()
            except AttributeError:
                return repr(obj)


def format_exc_info(logger, name, event_dict):
    """
    Replace an `exc_info` field by an `exception` string field:

    If *event_dict* contains the key ``exc_info``, there are two possible
    behaviors:

    - If the value is a tuple, render it into the key ``exception``.
    - If the value true but no tuple, obtain exc_info ourselves and render
      that.

    If there is no ``exc_info`` key, the *event_dict* is not touched.
    This behavior is analogue to the one of the stdlib's logging.

    >>> from structlog.processors import format_exc_info
    >>> try:
    ...     raise ValueError
    ... except ValueError:
    ...     format_exc_info(None, None, {'exc_info': True})# doctest: +ELLIPSIS
    {'exception': 'Traceback (most recent call last):...
    """
    exc_info = event_dict.pop('exc_info', None)
    if exc_info:
        if not isinstance(exc_info, tuple):
            exc_info = sys.exc_info()
        event_dict['exception'] = _format_exception(exc_info)
    return event_dict


class TimeStamper(object):
    """
    Add a timestamp to `event_dict`.

    .. note::
        You probably want to let OS tools take care of timestamping.  See also
        :doc:`logging-best-practices`.

    :param str format: strftime format string, or ``"iso"`` for `ISO 8601
        <http://en.wikipedia.org/wiki/ISO_8601>`_, or `None` for a `UNIX
        timestamp <http://en.wikipedia.org/wiki/Unix_time>`_.
    :param bool utc: Whether timestamp should be in UTC or local time.

    >>> from structlog.processors import TimeStamper
    >>> TimeStamper()(None, None, {})  # doctest: +SKIP
    {'timestamp': 1378994017}
    >>> TimeStamper(fmt='iso')(None, None, {})  # doctest: +SKIP
    {'timestamp': '2013-09-12T13:54:26.996778Z'}
    >>> TimeStamper(fmt='%Y')(None, None, {})  # doctest: +SKIP
    {'timestamp': '2013'}
    """
    def __new__(cls, fmt=None, utc=True):
        if fmt is None and not utc:
            raise ValueError('UNIX timestamps are always UTC.')

        now_method = getattr(datetime.datetime, 'utcnow' if utc else 'now')
        if fmt is None:
            def stamper(self, _, __, event_dict):
                event_dict['timestamp'] = calendar.timegm(time.gmtime())
                return event_dict
        elif fmt.upper() == 'ISO':
            if utc:
                def stamper(self, _, __, event_dict):
                    event_dict['timestamp'] = now_method().isoformat() + 'Z'
                    return event_dict
            else:
                def stamper(self, _, __, event_dict):
                    event_dict['timestamp'] = now_method().isoformat()
                    return event_dict
        else:
            def stamper(self, _, __, event_dict):
                event_dict['timestamp'] = now_method().strftime(fmt)
                return event_dict

        return type('TimeStamper', (object,), {'__call__': stamper})()


class ExceptionPrettyPrinter(object):
    """
    Pretty print exceptions and remove them from the `event_dict`.

    :param file file: Target file for output (default: `sys.stdout`).

    This processor is mostly for development and testing so you can read
    exceptions properly formatted.

    It behaves like :func:`format_exc_info` except it removes the exception
    data from the event dictionary after printing it.

    It's tolerant to having `format_exc_info` in front of itself in the
    processor chain but doesn't require it.  In other words, it handles both
    `exception` as well as `exc_info` keys.

    .. versionadded:: 0.4.0
    """
    def __init__(self, file=None):
        if file is not None:
            self._file = file
        else:
            self._file = sys.stdout

    def __call__(self, logger, name, event_dict):
        exc = event_dict.pop('exception', None)
        if exc is None:
            exc_info = event_dict.pop('exc_info', None)
            if exc_info:
                if not isinstance(exc_info, tuple):
                    exc_info = sys.exc_info()
                exc = _format_exception(exc_info)
        if exc:
            print(exc, file=self._file)
        return event_dict


class StackInfoRenderer(object):
    """
    Add stack information with key `stack` if `stack_info` is true.

    Useful when you want to attach a stack dump to a log entry without
    involving an exception.

    It works analogously to the `stack_info` argument of the Python 3 standard
    library logging but works on both 2 and 3.

    .. versionadded:: 0.4.0
    """
    def __call__(self, logger, name, event_dict):
        if event_dict.pop('stack_info', None):
            event_dict['stack'] = _format_stack(
                _find_first_app_frame_and_name()[0]
            )
        return event_dict

########NEW FILE########
__FILENAME__ = stdlib
# Copyright 2013 Hynek Schlawack
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Processors and helpers specific to the `logging module
<http://docs.python.org/2/library/logging.html>`_ from the `Python standard
library <http://docs.python.org/>`_.
"""

from __future__ import absolute_import, division, print_function

import logging

from structlog._base import BoundLoggerBase
from structlog._exc import DropEvent
from structlog._compat import PY3
from structlog._frames import _format_stack, _find_first_app_frame_and_name


class _FixedFindCallerLogger(logging.Logger):
    """
    Change the behavior of findCaller to cope with structlog's extra frames.
    """
    def findCaller(self, stack_info=False):
        """
        Finds the first caller frame outside of structlog so that the caller
        info is populated for wrapping stdlib.
        This logger gets set as the default one when using LoggerFactory.
        """
        f, name = _find_first_app_frame_and_name(['logging'])
        if PY3:  # pragma: nocover
            if stack_info:
                sinfo = _format_stack(f)
            else:
                sinfo = None
            return f.f_code.co_filename, f.f_lineno, f.f_code.co_name, sinfo
        else:
            return f.f_code.co_filename, f.f_lineno, f.f_code.co_name


class BoundLogger(BoundLoggerBase):
    """
    Python Standard Library version of :class:`structlog.BoundLogger`.
    Works exactly like the generic one except that it takes advantage of
    knowing the logging methods in advance.

    Use it like::

        configure(
            wrapper_class=structlog.stdlib.BoundLogger,
        )

    """
    def debug(self, event=None, **kw):
        """
        Process event and call ``Logger.debug()`` with the result.
        """
        return self._proxy_to_logger('debug', event, **kw)

    def info(self, event=None, **kw):
        """
        Process event and call ``Logger.info()`` with the result.
        """
        return self._proxy_to_logger('info', event, **kw)

    def warning(self, event=None, **kw):
        """
        Process event and call ``Logger.warning()`` with the result.
        """
        return self._proxy_to_logger('warning', event, **kw)

    warn = warning

    def error(self, event=None, **kw):
        """
        Process event and call ``Logger.error()`` with the result.
        """
        return self._proxy_to_logger('error', event, **kw)

    def critical(self, event=None, **kw):
        """
        Process event and call ``Logger.critical()`` with the result.
        """
        return self._proxy_to_logger('critical', event, **kw)


class LoggerFactory(object):
    """
    Build a standard library logger when an *instance* is called.

    Sets a custom logger using `logging.setLogggerClass` so variables in
    log format are expanded properly.

    >>> from structlog import configure
    >>> from structlog.stdlib import LoggerFactory
    >>> configure(logger_factory=LoggerFactory())

    :param ignore_frame_names: When guessing the name of a logger, skip frames
        whose names *start* with one of these.  For example, in pyramid
        applications you'll want to set it to
        ``['venusian', 'pyramid.config']``.
    :type ignore_frame_names: `list` of `str`
    """
    def __init__(self, ignore_frame_names=None):
        self._ignore = ignore_frame_names
        logging.setLoggerClass(_FixedFindCallerLogger)

    def __call__(self, *args):
        """
        Deduce the caller's module name and create a stdlib logger.

        If an optional argument is passed, it will be used as the logger name
        instead of guesswork.  This optional argument would be passed from the
        :func:`structlog.get_logger` call.  For example
        ``struclog.get_logger('foo')`` would cause this method to be called
        with ``'foo'`` as its first positional argument.

        :rtype: `logging.Logger`

        .. versionchanged:: 0.4.0
            Added support for optional positional arguments.  Using the first
            one for naming the constructed logger.
        """
        if args:
            return logging.getLogger(args[0])

        # We skip all frames that originate from within structlog or one of the
        # configured names.
        _, name = _find_first_app_frame_and_name(self._ignore)
        return logging.getLogger(name)


# Adapted from the stdlib

CRITICAL = 50
FATAL = CRITICAL
ERROR = 40
WARNING = 30
WARN = WARNING
INFO = 20
DEBUG = 10
NOTSET = 0

_nameToLevel = {
    'critical': CRITICAL,
    'error': ERROR,
    'warn': WARNING,
    'warning': WARNING,
    'info': INFO,
    'debug': DEBUG,
    'notset': NOTSET,
}


def filter_by_level(logger, name, event_dict):
    """
    Check whether logging is configured to accept messages from this log level.

    Should be the first processor if stdlib's filtering by level is used so
    possibly expensive processors like exception formatters are avoided in the
    first place.

    >>> import logging
    >>> from structlog.stdlib import filter_by_level
    >>> logging.basicConfig(level=logging.WARN)
    >>> logger = logging.getLogger()
    >>> filter_by_level(logger, 'warn', {})
    {}
    >>> filter_by_level(logger, 'debug', {})
    Traceback (most recent call last):
    ...
    DropEvent
    """
    if logger.isEnabledFor(_nameToLevel[name]):
        return event_dict
    else:
        raise DropEvent

########NEW FILE########
__FILENAME__ = threadlocal
# Copyright 2013 Hynek Schlawack
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Primitives to keep context global but thread (and greenlet) local.
"""

from __future__ import absolute_import, division, print_function

import contextlib
import uuid

from structlog._config import BoundLoggerLazyProxy

try:
    from greenlet import getcurrent
except ImportError:  # pragma: nocover
    from threading import local as ThreadLocal
else:
    class ThreadLocal(object):  # pragma: nocover
        """
        threading.local() replacement for greenlets.
        """
        def __init__(self):
            self.__dict__["_prefix"] = str(id(self))

        def __getattr__(self, name):
            return getattr(getcurrent(), self._prefix + name)

        def __setattr__(self, name, val):
            setattr(getcurrent(), self._prefix + name, val)

        def __delattr__(self, name):
            delattr(getcurrent(), self._prefix + name)


def wrap_dict(dict_class):
    """
    Wrap a dict-like class and return the resulting class.

    The wrapped class and used to keep global in the current thread.

    :param type dict_class: Class used for keeping context.

    :rtype: `type`
    """
    Wrapped = type('WrappedDict-' + str(uuid.uuid4()),
                   (_ThreadLocalDictWrapper,), {})
    Wrapped._tl = ThreadLocal()
    Wrapped._dict_class = dict_class
    return Wrapped


def as_immutable(logger):
    """
    Extract the context from a thread local logger into an immutable logger.

    :param BoundLogger logger: A logger with *possibly* thread local state.
    :rtype: :class:`~structlog.BoundLogger` with an immutable context.
    """
    if isinstance(logger, BoundLoggerLazyProxy):
        logger = logger.bind()

    try:
        ctx = logger._context._tl.dict_.__class__(logger._context._dict)
        bl = logger.__class__(
            logger._logger,
            processors=logger._processors,
            context={},
        )
        bl._context = ctx
        return bl
    except AttributeError:
        return logger


@contextlib.contextmanager
def tmp_bind(logger, **tmp_values):
    """
    Bind *tmp_values* to *logger* & memorize current state. Rewind afterwards.

    >>> from structlog import wrap_logger, PrintLogger
    >>> from structlog.threadlocal import tmp_bind, wrap_dict
    >>> logger = wrap_logger(PrintLogger(),  context_class=wrap_dict(dict))
    >>> with tmp_bind(logger, x=5) as tmp_logger:
    ...     logger = logger.bind(y=3)
    ...     tmp_logger.msg('event')
    y=3 x=5 event='event'
    >>> logger.msg('event')
    event='event'
    """
    saved = as_immutable(logger)._context
    yield logger.bind(**tmp_values)
    logger._context.clear()
    logger._context.update(saved)


class _ThreadLocalDictWrapper(object):
    """
    Wrap a dict-like class and keep the state *global* but *thread-local*.

    Attempts to re-initialize only updates the wrapped dictionary.

    Useful for short-lived threaded applications like requests in web app.

    Use :func:`wrap` to instantiate and use
    :func:`structlog._loggers.BoundLogger.new` to clear the context.
    """
    def __init__(self, *args, **kw):
        """
        We cheat.  A context dict gets never recreated.
        """
        if args and isinstance(args[0], self.__class__):
            # our state is global, no need to look at args[0] if it's of our
            # class
            self._dict.update(**kw)
        else:
            self._dict.update(*args, **kw)

    @property
    def _dict(self):
        """
        Return or create and return the current context.
        """
        try:
            return self.__class__._tl.dict_
        except AttributeError:
            self.__class__._tl.dict_ = self.__class__._dict_class()
            return self.__class__._tl.dict_

    def __repr__(self):
        return '<{0}({1!r})>'.format(self.__class__.__name__, self._dict)

    def __eq__(self, other):
        # Same class == same dictionary
        return self.__class__ == other.__class__

    def __ne__(self, other):
        return not self.__eq__(other)

    # Proxy methods necessary for structlog.
    # Dunder methods don't trigger __getattr__ so we need to proxy by hand.
    def __iter__(self):
        return self._dict.__iter__()

    def __setitem__(self, key, value):
        self._dict[key] = value

    def __delitem__(self, key):
        self._dict.__delitem__(key)

    def __len__(self):
        return self._dict.__len__()

    def __getattr__(self, name):
        method = getattr(self._dict, name)
        return method

########NEW FILE########
__FILENAME__ = twisted
# Copyright 2013 Hynek Schlawack
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Processors and tools specific to the `Twisted <http://twistedmatrix.com/>`_
networking engine.

See also :doc:`structlog's Twisted support <twisted>`.
"""

from __future__ import absolute_import, division, print_function

import json
import sys

from twisted.python.failure import Failure
from twisted.python import log
from twisted.python.log import ILogObserver, textFromEventDict
from zope.interface import implementer

from structlog._base import BoundLoggerBase
from structlog._compat import PY2, string_types
from structlog._utils import until_not_interrupted
from structlog.processors import (
    KeyValueRenderer,
    # can't import processors module without risking circular imports
    JSONRenderer as GenericJSONRenderer
)


class BoundLogger(BoundLoggerBase):
    """
    Twisted-specific version of :class:`structlog.BoundLogger`.

    Works exactly like the generic one except that it takes advantage of
    knowing the logging methods in advance.

    Use it like::

        configure(
            wrapper_class=structlog.twisted.BoundLogger,
        )

    """
    def msg(self, event=None, **kw):
        """
        Process event and call ``log.msg()`` with the result.
        """
        return self._proxy_to_logger('msg', event, **kw)

    def err(self, event=None, **kw):
        """
        Process event and call ``log.err()`` with the result.
        """
        return self._proxy_to_logger('err', event, **kw)


class LoggerFactory(object):
    """
    Build a Twisted logger when an *instance* is called.

    >>> from structlog import configure
    >>> from structlog.twisted import LoggerFactory
    >>> configure(logger_factory=LoggerFactory())
    """
    def __call__(self, *args):
        """
        Positional arguments are silently ignored.

        :rvalue: A new Twisted logger.

        .. versionchanged:: 0.4.0
            Added support for optional positional arguments.
        """
        return log


_FAIL_TYPES = (BaseException, Failure)


def _extractStuffAndWhy(eventDict):
    """
    Removes all possible *_why*s and *_stuff*s, analyzes exc_info and returns
    a tuple of `(_stuff, _why, eventDict)`.

    **Modifies** *eventDict*!
    """
    _stuff = eventDict.pop('_stuff', None)
    _why = eventDict.pop('_why', None)
    event = eventDict.pop('event', None)
    if (
        isinstance(_stuff, _FAIL_TYPES) and
        isinstance(event, _FAIL_TYPES)
    ):
        raise ValueError('Both _stuff and event contain an Exception/Failure.')
    # `log.err('event', _why='alsoEvent')` is ambiguous.
    if _why and isinstance(event, string_types):
        raise ValueError('Both `_why` and `event` supplied.')
    # Two failures are ambiguous too.
    if not isinstance(_stuff, _FAIL_TYPES) and isinstance(event, _FAIL_TYPES):
        _why = _why or 'error'
        _stuff = event
    if isinstance(event, string_types):
        _why = event
    if not _stuff and sys.exc_info() != (None, None, None):
        _stuff = Failure()
    # Either we used the error ourselves or the user supplied one for
    # formatting.  Avoid log.err() to dump another traceback into the log.
    if isinstance(_stuff, BaseException):
        _stuff = Failure(_stuff)
    if PY2:
        sys.exc_clear()
    return _stuff, _why, eventDict


class JSONRenderer(GenericJSONRenderer):
    """
    Behaves like :class:`structlog.processors.JSONRenderer` except that it
    formats tracebacks and failures itself if called with `err()`.

    .. note::

        This ultimately means that the messages get logged out using `msg()`,
        and *not* `err()` which renders failures in separate lines.

        Therefore it will break your tests that contain assertions using
        `flushLoggedErrors <http://twistedmatrix.com/documents/
        current/api/twisted.trial.unittest.SynchronousTestCase.html
        #flushLoggedErrors>`_.

    *Not* an adapter like :class:`EventAdapter` but a real formatter.  Nor does
    it require to be adapted using it.

    Use together with a :class:`JSONLogObserverWrapper`-wrapped Twisted logger
    like :func:`plainJSONStdOutLogger` for pure-JSON logs.
    """
    def __call__(self, logger, name, eventDict):
        _stuff, _why, eventDict = _extractStuffAndWhy(eventDict)
        if name == 'err':
            eventDict['event'] = _why
            if isinstance(_stuff, Failure):
                eventDict['exception'] = _stuff.getTraceback(detail='verbose')
                _stuff.cleanFailure()
        else:
            eventDict['event'] = _why
        return ((GenericJSONRenderer.__call__(self, logger, name, eventDict),),
                {'_structlog': True})


@implementer(ILogObserver)
class PlainFileLogObserver(object):
    """
    Write only the the plain message without timestamps or anything else.

    Great to just print JSON to stdout where you catch it with something like
    runit.

    :param file file: File to print to.


    .. versionadded:: 0.2.0
    """
    def __init__(self, file):
        self._write = file.write
        self._flush = file.flush

    def __call__(self, eventDict):
        until_not_interrupted(self._write, textFromEventDict(eventDict) + '\n')
        until_not_interrupted(self._flush)


@implementer(ILogObserver)
class JSONLogObserverWrapper(object):
    """
    Wrap a log *observer* and render non-:class:`JSONRenderer` entries to JSON.

    :param ILogObserver observer: Twisted log observer to wrap.  For example
        :class:`PlainFileObserver` or Twisted's stock `FileLogObserver
        <http://twistedmatrix.com/documents/current/api/twisted.python.log.
        FileLogObserver.html>`_

    .. versionadded:: 0.2.0
    """
    def __init__(self, observer):
        self._observer = observer

    def __call__(self, eventDict):
        if '_structlog' not in eventDict:
            eventDict['message'] = (json.dumps({
                'event': textFromEventDict(eventDict),
                'system': eventDict.get('system'),
            }),)
            eventDict['_structlog'] = True
        return self._observer(eventDict)


def plainJSONStdOutLogger():
    """
    Return a logger that writes only the message to stdout.

    Transforms non-:class:`~structlog.twisted.JSONRenderer` messages to JSON.

    Ideal for JSONifying log entries from Twisted plugins and libraries that
    are outside of your control::

        $ twistd -n --logger structlog.twisted.plainJSONStdOutLogger web
        {"event": "Log opened.", "system": "-"}
        {"event": "twistd 13.1.0 (python 2.7.3) starting up.", "system": "-"}
        {"event": "reactor class: twisted...EPollReactor.", "system": "-"}
        {"event": "Site starting on 8080", "system": "-"}
        {"event": "Starting factory <twisted.web.server.Site ...>", ...}
        ...

    Composes :class:`PlainFileLogObserver` and :class:`JSONLogObserverWrapper`
    to a usable logger.

    .. versionadded:: 0.2.0
    """
    return JSONLogObserverWrapper(PlainFileLogObserver(sys.stdout))


class EventAdapter(object):
    """
    Adapt an ``event_dict`` to Twisted logging system.

    Particularly, make a wrapped `twisted.python.log.err
    <http://twistedmatrix.com/documents/current/
    api/twisted.python.log.html#err>`_ behave as expected.

    :param callable dictRenderer: Renderer that is used for the actual
        log message.  Please note that structlog comes with a dedicated
        :class:`JSONRenderer`.

    **Must** be the last processor in the chain and requires a `dictRenderer`
    for the actual formatting as an constructor argument in order to be able to
    fully support the original behaviors of ``log.msg()`` and ``log.err()``.
    """
    def __init__(self, dictRenderer=None):
        """
        :param dictRenderer: A processor used to format the log message.
        """
        self._dictRenderer = dictRenderer or KeyValueRenderer()

    def __call__(self, logger, name, eventDict):
        if name == 'err':
            # This aspires to handle the following cases correctly:
            #   - log.err(failure, _why='event', **kw)
            #   - log.err('event', **kw)
            #   - log.err(_stuff=failure, _why='event', **kw)
            _stuff, _why, eventDict = _extractStuffAndWhy(eventDict)
            eventDict['event'] = _why
            return ((), {
                '_stuff': _stuff,
                '_why': self._dictRenderer(logger, name, eventDict),
            })
        else:
            return self._dictRenderer(logger, name, eventDict)

########NEW FILE########
__FILENAME__ = _base
# Copyright 2013 Hynek Schlawack
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Logger wrapper and helper class.
"""

from __future__ import absolute_import, division, print_function

from structlog._compat import string_types
from structlog._exc import DropEvent


class BoundLoggerBase(object):
    """
    Immutable context carrier.

    Doesn't do any actual logging; examples for useful subclasses are:

        - the generic :class:`BoundLogger` that can wrap anything,
        - :class:`structlog.twisted.BoundLogger`,
        - and :class:`structlog.stdlib.BoundLogger`.

    See also :doc:`custom-wrappers`.
    """
    _logger = None
    """
    Wrapped logger.

    .. note::

        Despite underscore available **read-only** to custom wrapper classes.

        See also :doc:`custom-wrappers`.
    """

    def __init__(self, logger, processors, context):
        self._logger = logger
        self._processors = processors
        self._context = context

    def __repr__(self):
        return '<{0}(context={1!r}, processors={2!r})>'.format(
            self.__class__.__name__,
            self._context,
            self._processors,
        )

    def __eq__(self, other):
        try:
            if self._context == other._context:
                return True
            else:
                return False
        except AttributeError:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def bind(self, **new_values):
        """
        Return a new logger with *new_values* added to the existing ones.

        :rtype: `self.__class__`
        """
        return self.__class__(
            self._logger,
            self._processors,
            self._context.__class__(self._context, **new_values)
        )

    def unbind(self, *keys):
        """
        Return a new logger with *keys* removed from the context.

        :raises KeyError: If the key is not part of the context.

        :rtype: `self.__class__`
        """
        bl = self.bind()
        for key in keys:
            del bl._context[key]
        return bl

    def new(self, **new_values):
        """
        Clear context and binds *initial_values* using :func:`bind`.

        Only necessary with dict implementations that keep global state like
        those wrapped by :func:`structlog.threadlocal.wrap_dict` when threads
        are re-used.

        :rtype: `self.__class__`
        """
        self._context.clear()
        return self.bind(**new_values)

    # Helper methods for sub-classing concrete BoundLoggers.

    def _process_event(self, method_name, event, event_kw):
        """
        Combines creates an `event_dict` and runs the chain.

        Call it to combine your *event* and *context* into an event_dict and
        process using the processor chain.

        :param str method_name: The name of the logger method.  Is passed into
            the processors.
        :param event: The event -- usually the first positional argument to a
            logger.
        :param event_kw: Additional event keywords.  For example if someone
            calls ``log.msg('foo', bar=42)``, *event* would to be ``'foo'``
            and *event_kw* ``{'bar': 42}``.
        :raises: :class:`structlog.DropEvent` if log entry should be dropped.
        :raises: :class:`ValueError` if the final processor doesn't return a
            string, tuple, or a dict.
        :rtype: `tuple` of `(*args, **kw)`

        .. note::

            Despite underscore available to custom wrapper classes.

            See also :doc:`custom-wrappers`.

        .. versionchanged:: 0.5.0
            Allow final processor to return a `dict`.
        """
        event_dict = self._context.copy()
        event_dict.update(**event_kw)
        if event:
            event_dict['event'] = event
        for proc in self._processors:
            event_dict = proc(self._logger, method_name, event_dict)
        if isinstance(event_dict, string_types):
            return (event_dict,), {}
        elif isinstance(event_dict, tuple):
            # In this case we assume that the last processor returned a tuple
            # of ``(args, kwargs)`` and pass it right through.
            return event_dict
        elif isinstance(event_dict, dict):
            return (), event_dict
        else:
            raise ValueError(
                "Last processor didn't return an approriate value.  Allowed "
                "return values are a dict, a tuple of (args, kwargs), or a "
                "string."
            )

    def _proxy_to_logger(self, method_name, event=None, **event_kw):
        """
        Run processor chain on event & call *method_name* on wrapped logger.

        DRY convenience method that runs :func:`_process_event`, takes care of
        handling :exc:`structlog.DropEvent`, and finally calls *method_name* on
        :attr:`_logger` with the result.

        :param str method_name: The name of the method that's going to get
            called.  Technically it should be identical to the method the
            user called because it also get passed into processors.
        :param event: The event -- usually the first positional argument to a
            logger.
        :param event_kw: Additional event keywords.  For example if someone
            calls ``log.msg('foo', bar=42)``, *event* would to be ``'foo'``
            and *event_kw* ``{'bar': 42}``.

        .. note::

            Despite underscore available to custom wrapper classes.

            See also :doc:`custom-wrappers`.
        """
        try:
            args, kw = self._process_event(method_name, event, event_kw)
            return getattr(self._logger, method_name)(*args, **kw)
        except DropEvent:
            return

########NEW FILE########
__FILENAME__ = _compat
# Copyright 2013 Hynek Schlawack
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Python 2 + 3 compatibility utilities.

Derived from MIT-licensed https://bitbucket.org/gutworth/six/ which is
Copyright 2010-2013 by Benjamin Peterson.
"""

from __future__ import absolute_import, division, print_function

import abc
import sys
import types

PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3


try:
    from cStringIO import StringIO
except ImportError:
    from io import StringIO  # flake8: noqa

if sys.version_info[:2] == (2, 6):
    try:
        from ordereddict import OrderedDict
    except ImportError:
        class OrderedDict(object):
            def __init__(self, *args, **kw):
                raise NotImplementedError(
                    'The ordereddict package is needed on Python 2.6. '
                    'See <http://www.structlog.org/en/latest/'
                    'installation.html>.'
                )
else:
    from collections import OrderedDict

if PY3:
    string_types = str,
    integer_types = int,
    class_types = type,
    text_type = str
    binary_type = bytes
    unicode_type = str
    u = lambda s: s
else:
    string_types = basestring,
    integer_types = (int, long)
    class_types = (type, types.ClassType)
    text_type = unicode
    binary_type = str
    unicode_type = unicode
    u = lambda s: unicode(s, "unicode_escape")

def with_metaclass(meta, *bases):
    """
    Create a base class with a metaclass.
    """
    return meta("NewBase", bases, {})

########NEW FILE########
__FILENAME__ = _config
# Copyright 2013 Hynek Schlawack
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
Global state department.  Don't reload this module or everything breaks.
"""

from __future__ import absolute_import, division, print_function

import warnings

from structlog._compat import OrderedDict
from structlog._generic import BoundLogger
from structlog._loggers import (
    PrintLoggerFactory,
)
from structlog.processors import (
    KeyValueRenderer,
    StackInfoRenderer,
    format_exc_info,
)

_BUILTIN_DEFAULT_PROCESSORS = [
    StackInfoRenderer(),
    format_exc_info,
    KeyValueRenderer()
]
_BUILTIN_DEFAULT_CONTEXT_CLASS = OrderedDict
_BUILTIN_DEFAULT_WRAPPER_CLASS = BoundLogger
_BUILTIN_DEFAULT_LOGGER_FACTORY = PrintLoggerFactory()
_BUILTIN_CACHE_LOGGER_ON_FIRST_USE = False


class _Configuration(object):
    """
    Global defaults.
    """
    is_configured = False
    default_processors = _BUILTIN_DEFAULT_PROCESSORS[:]
    default_context_class = _BUILTIN_DEFAULT_CONTEXT_CLASS
    default_wrapper_class = _BUILTIN_DEFAULT_WRAPPER_CLASS
    logger_factory = _BUILTIN_DEFAULT_LOGGER_FACTORY
    cache_logger_on_first_use = _BUILTIN_CACHE_LOGGER_ON_FIRST_USE


_CONFIG = _Configuration()
"""
Global defaults used when arguments to :func:`wrap_logger` are omitted.
"""


def get_logger(*args, **initial_values):
    """
    Convenience function that returns a logger according to configuration.

    >>> from structlog import get_logger
    >>> log = get_logger(y=23)
    >>> log.msg('hello', x=42)
    y=23 x=42 event='hello'

    :param args: *Optional* positional arguments that are passed unmodified to
        the logger factory.  Therefore it depends on the factory what they
        mean.
    :param initial_values: Values that are used to pre-populate your contexts.

    :rtype: A proxy that creates a correctly configured bound logger when
        necessary.

    See :ref:`configuration` for details.

    If you prefer CamelCase, there's an alias for your reading pleasure:
    :func:`structlog.getLogger`.

    .. versionadded:: 0.4.0
        `args`
    """
    return wrap_logger(None, logger_factory_args=args, **initial_values)


getLogger = get_logger
"""
CamelCase alias for :func:`structlog.get_logger`.

This function is supposed to be in every source file -- we don't want it to
stick out like a sore thumb in frameworks like Twisted or Zope.
"""


def wrap_logger(logger, processors=None, wrapper_class=None,
                context_class=None, cache_logger_on_first_use=None,
                logger_factory_args=None, **initial_values):
    """
    Create a new bound logger for an arbitrary `logger`.

    Default values for *processors*, *wrapper_class*, and *context_class* can
    be set using :func:`configure`.

    If you set an attribute here, :func:`configure` calls have *no* effect for
    the *respective* attribute.

    In other words: selective overwriting of the defaults while keeping some
    *is* possible.

    :param initial_values: Values that are used to pre-populate your contexts.
    :param tuple logger_factory_args: Values that are passed unmodified as
        ``*logger_factory_args`` to the logger factory if not `None`.

    :rtype: A proxy that creates a correctly configured bound logger when
        necessary.

    See :func:`configure` for the meaning of the rest of the arguments.

    .. versionadded:: 0.4.0
        `logger_factory_args`
    """
    return BoundLoggerLazyProxy(
        logger,
        wrapper_class=wrapper_class,
        processors=processors,
        context_class=context_class,
        cache_logger_on_first_use=cache_logger_on_first_use,
        initial_values=initial_values,
        logger_factory_args=logger_factory_args,
    )


def configure(processors=None, wrapper_class=None, context_class=None,
              logger_factory=None, cache_logger_on_first_use=None):
    """
    Configures the **global** defaults.

    They are used if :func:`wrap_logger` has been called without arguments.

    Also sets the global class attribute :attr:`is_configured` to `True` on
    first call.  Can be called several times, keeping an argument at `None`
    leaves is unchanged from the current setting.

    Use :func:`reset_defaults` to undo your changes.

    :param list processors: List of processors.
    :param type wrapper_class: Class to use for wrapping loggers instead of
        :class:`structlog.BoundLogger`.  See :doc:`standard-library`,
        :doc:`twisted`, and :doc:`custom-wrappers`.
    :param type context_class: Class to be used for internal context keeping.
    :param callable logger_factory: Factory to be called to create a new
        logger that shall be wrapped.
    :param bool cache_logger_on_first_use: `wrap_logger` doesn't return an
        actual wrapped logger but a proxy that assembles one when it's first
        used.  If this option is set to `True`, this assembled logger is
        cached.  See :doc:`performance`.

    .. versionadded:: 0.3.0
        `cache_logger_on_first_use`
    """
    _CONFIG.is_configured = True
    if processors is not None:
        _CONFIG.default_processors = processors
    if wrapper_class:
        _CONFIG.default_wrapper_class = wrapper_class
    if context_class:
        _CONFIG.default_context_class = context_class
    if logger_factory:
        _CONFIG.logger_factory = logger_factory
    if cache_logger_on_first_use is not None:
        _CONFIG.cache_logger_on_first_use = cache_logger_on_first_use


def configure_once(*args, **kw):
    """
    Configures iff structlog isn't configured yet.

    It does *not* matter whether is was configured using :func:`configure`
    or :func:`configure_once` before.

    Raises a RuntimeWarning if repeated configuration is attempted.
    """
    if not _CONFIG.is_configured:
        configure(*args, **kw)
    else:
        warnings.warn('Repeated configuration attempted.', RuntimeWarning)


def reset_defaults():
    """
    Resets global default values to builtins.

    That means [:class:`~structlog.processors.StackInfoRenderer`,
    :func:`~structlog.processors.format_exc_info`,
    :class:`~structlog.processors.KeyValueRenderer`] for *processors*,
    :class:`~structlog.BoundLogger` for *wrapper_class*, ``OrderedDict`` for
    *context_class*, :class:`~structlog.PrintLoggerFactory` for
    *logger_factory*, and `False` for *cache_logger_on_first_use*.

    Also sets the global class attribute :attr:`is_configured` to `False`.
    """
    _CONFIG.is_configured = False
    _CONFIG.default_processors = _BUILTIN_DEFAULT_PROCESSORS[:]
    _CONFIG.default_wrapper_class = _BUILTIN_DEFAULT_WRAPPER_CLASS
    _CONFIG.default_context_class = _BUILTIN_DEFAULT_CONTEXT_CLASS
    _CONFIG.logger_factory = _BUILTIN_DEFAULT_LOGGER_FACTORY
    _CONFIG.cache_logger_on_first_use = _BUILTIN_CACHE_LOGGER_ON_FIRST_USE


class BoundLoggerLazyProxy(object):
    """
    Instantiates a BoundLogger on first usage.

    Takes both configuration and instantiation parameters into account.

    The only points where a BoundLogger changes state are bind(), unbind(), and
    new() and that return the actual BoundLogger.

    If and only if configuration says so, that actual BoundLogger is cached on
    first usage.

    .. versionchanged:: 0.4.0
        Added support for `logger_factory_args`.
    """
    def __init__(self, logger, wrapper_class=None, processors=None,
                 context_class=None, cache_logger_on_first_use=None,
                 initial_values=None, logger_factory_args=None):
        self._logger = logger
        self._wrapper_class = wrapper_class
        self._processors = processors
        self._context_class = context_class
        self._cache_logger_on_first_use = cache_logger_on_first_use
        self._initial_values = initial_values or {}
        self._logger_factory_args = logger_factory_args or ()

    def __repr__(self):
        return (
            '<BoundLoggerLazyProxy(logger={0._logger!r}, wrapper_class='
            '{0._wrapper_class!r}, processors={0._processors!r}, '
            'context_class={0._context_class!r}, '
            'initial_values={0._initial_values!r}, '
            'logger_factory_args={0._logger_factory_args!r})>'.format(self)
        )

    def bind(self, **new_values):
        """
        Assemble a new BoundLogger from arguments and configuration.
        """
        if self._context_class:
            ctx = self._context_class(self._initial_values)
        else:
            ctx = _CONFIG.default_context_class(self._initial_values)
        cls = self._wrapper_class or _CONFIG.default_wrapper_class
        if not self._logger:
            self._logger = _CONFIG.logger_factory(*self._logger_factory_args)
        logger = cls(
            self._logger,
            processors=self._processors or _CONFIG.default_processors,
            context=ctx,
        )

        def finalized_bind(**new_values):
            """
            Use cached assembled logger to bind potentially new values.
            """
            if new_values:
                return logger.bind(**new_values)
            else:
                return logger

        if (
            self._cache_logger_on_first_use is True or
            (self._cache_logger_on_first_use is None
             and _CONFIG.cache_logger_on_first_use is True)
        ):
            self.bind = finalized_bind
        return finalized_bind(**new_values)

    def unbind(self, *keys):
        """
        Same as bind, except unbind *keys* first.

        In our case that could be only initial values.
        """
        return self.bind().unbind(*keys)

    def new(self, **new_values):
        """
        Clear context, then bind.
        """
        if self._context_class:
            self._context_class().clear()
        else:
            _CONFIG.default_context_class().clear()
        bl = self.bind(**new_values)
        return bl

    def __getattr__(self, name):
        """
        If a logging method if called on a lazy proxy, we have to create an
        ephemeral BoundLogger first.
        """
        bl = self.bind()
        return getattr(bl, name)

########NEW FILE########
__FILENAME__ = _exc
# Copyright 2013 Hynek Schlawack
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Exceptions factored out to avoid import loops.
"""


class DropEvent(BaseException):
    """
    If raised by an processor, the event gets silently dropped.

    Derives from BaseException because it's technically not an error.
    """

########NEW FILE########
__FILENAME__ = _frames
# Copyright 2013 Hynek Schlawack
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

import sys
import traceback

from structlog._compat import StringIO


def _format_exception(exc_info):
    """
    Prettyprint an `exc_info` tuple.

    Shamelessly stolen from stdlib's logging module.
    """
    sio = StringIO()
    traceback.print_exception(exc_info[0], exc_info[1], exc_info[2], None, sio)
    s = sio.getvalue()
    sio.close()
    if s[-1:] == "\n":
        s = s[:-1]
    return s


def _find_first_app_frame_and_name(additional_ignores=None):
    """
    Remove all intra-structlog calls and return the relevant app frame.

    :param additional_ignores: Additional names with which the first frame must
        not start.
    :type additional_ignores: `list` of `str` or `None`

    :rtype: tuple of (frame, name)
    """
    ignores = ['structlog'] + (additional_ignores or [])
    f = sys._getframe()
    name = f.f_globals['__name__']
    while any(name.startswith(i) for i in ignores):
        f = f.f_back
        name = f.f_globals['__name__']
    return f, name


def _format_stack(frame):
    """
    Pretty-print the stack of `frame` like logging would.
    """
    sio = StringIO()
    sio.write('Stack (most recent call last):\n')
    traceback.print_stack(frame, file=sio)
    sinfo = sio.getvalue()
    if sinfo[-1] == '\n':
        sinfo = sinfo[:-1]
    sio.close()
    return sinfo

########NEW FILE########
__FILENAME__ = _generic
# Copyright 2013 Hynek Schlawack
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Generic bound logger that can wrap anything.
"""

from __future__ import absolute_import, division, print_function

from functools import partial

from structlog._base import BoundLoggerBase


class BoundLogger(BoundLoggerBase):
    """
    A generic BoundLogger that can wrap anything.

    Every unknown method will be passed to the wrapped logger.  If that's too
    much magic for you, try :class:`structlog.twisted.BoundLogger` or
    `:class:`structlog.twisted.BoundLogger` which also take advantage of
    knowing the wrapped class which generally results in better performance.

    Not intended to be instantiated by yourself.  See
    :func:`~structlog.wrap_logger` and :func:`~structlog.get_logger`.
    """
    def __getattr__(self, method_name):
        """
        If not done so yet, wrap the desired logger method & cache the result.
        """
        wrapped = partial(self._proxy_to_logger, method_name)
        setattr(self, method_name, wrapped)
        return wrapped

########NEW FILE########
__FILENAME__ = _loggers
# Copyright 2013 Hynek Schlawack
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Logger wrapper and helper class.
"""

from __future__ import absolute_import, division, print_function

import sys

from structlog._utils import until_not_interrupted


class PrintLoggerFactory(object):
    """
    Produces :class:`PrintLogger`\ s.

    To be used with :func:`structlog.configure`\ 's `logger_factory`.

    :param file file: File to print to. (default: stdout)

    Positional arguments are silently ignored.

    .. versionadded:: 0.4.0
    """
    def __init__(self, file=None):
        self._file = file

    def __call__(self, *args):
        return PrintLogger(self._file)


class PrintLogger(object):
    """
    Prints events into a file.

    :param file file: File to print to. (default: stdout)

    >>> from structlog import PrintLogger
    >>> PrintLogger().msg('hello')
    hello

    Useful if you just capture your stdout with tools like `runit
    <http://smarden.org/runit/>`_ or if you `forward your stderr to syslog
    <https://hynek.me/articles/taking-some-pain-out-of-python-logging/>`_.

    Also very useful for testing and examples since logging is sometimes
    finicky in doctests.
    """
    def __init__(self, file=None):
        self._file = file or sys.stdout
        self._write = self._file.write
        self._flush = self._file.flush

    def __repr__(self):
        return '<PrintLogger(file={0!r})>'.format(self._file)

    def msg(self, message):
        """
        Print *message*.
        """
        until_not_interrupted(self._write, message + '\n')
        until_not_interrupted(self._flush)

    err = debug = info = warning = error = critical = log = msg


class ReturnLoggerFactory(object):
    """
    Produces and caches :class:`ReturnLogger`\ s.

    To be used with :func:`structlog.configure`\ 's `logger_factory`.

    Positional arguments are silently ignored.

    .. versionadded:: 0.4.0
    """
    def __init__(self):
        self._logger = ReturnLogger()

    def __call__(self, *args):
        return self._logger


class ReturnLogger(object):
    """
    Returns the string that it's called with.

    >>> from structlog import ReturnLogger
    >>> ReturnLogger().msg('hello')
    'hello'
    >>> ReturnLogger().msg('hello', when='again')
    (('hello',), {'when': 'again'})

    Useful for unit tests.

    .. versionchanged:: 0.3.0
        Allow for arbitrary arguments and keyword arguments to be passed in.
    """
    def msg(self, *args, **kw):
        """
        Return tuple of ``args, kw`` or just ``args[0]`` if only one arg passed
        """
        # Slightly convoluted for backwards compatibility.
        if len(args) == 1 and not kw:
            return args[0]
        else:
            return args, kw

    err = debug = info = warning = error = critical = log = msg

########NEW FILE########
__FILENAME__ = _utils
# Copyright 2013 Hynek Schlawack
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Generic utilities.
"""

from __future__ import absolute_import, division, print_function

import errno


def until_not_interrupted(f, *args, **kw):
    """
    Retry until *f* succeeds or an exception that isn't caused by EINTR occurs.

    :param callable f: A callable like a function.
    :param *args: Positional arguments for *f*.
    :param **kw: Keyword arguments for *f*.
    """
    while True:
        try:
            return f(*args, **kw)
        except (IOError, OSError) as e:
            if e.args[0] == errno.EINTR:
                continue
            raise

########NEW FILE########
__FILENAME__ = additional_frame
# Copyright 2013 Hynek Schlawack
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Helper function for testing the deduction of stdlib logger names.

Since the logger factories are called from within structlog._config, they have
to skip a frame.  Calling them here emulates that.
"""

from __future__ import absolute_import, division, print_function


def additional_frame(callable):
    return callable()

########NEW FILE########
__FILENAME__ = test_base
# Copyright 2013 Hynek Schlawack
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

import pytest

from pretend import raiser, stub

from structlog._base import BoundLoggerBase
from structlog._config import _CONFIG
from structlog._exc import DropEvent
from structlog._loggers import ReturnLogger
from structlog.processors import KeyValueRenderer


def build_bl(logger=None, processors=None, context=None):
    """
    Convenience function to build BoundLoggerBases with sane defaults.
    """
    return BoundLoggerBase(
        logger or ReturnLogger(),
        processors or _CONFIG.default_processors,
        context if context is not None else _CONFIG.default_context_class(),
    )


class TestBinding(object):
    def test_repr(self):
        l = build_bl(processors=[1, 2, 3], context={})
        assert '<BoundLoggerBase(context={}, processors=[1, 2, 3])>' == repr(l)

    def test_binds_independently(self):
        """
        Ensure BoundLogger is immutable by default.
        """
        b = build_bl(processors=[KeyValueRenderer(sort_keys=True)])
        b = b.bind(x=42, y=23)
        b1 = b.bind(foo='bar')
        b2 = b.bind(foo='qux')
        assert b._context != b1._context != b2._context

    def test_new_clears_state(self):
        b = build_bl()
        b = b.bind(x=42)
        assert 42 == b._context['x']
        b = b.bind()
        assert 42 == b._context['x']
        b = b.new()
        assert 'x' not in b._context

    def test_comparison(self):
        b = build_bl()
        assert b == b.bind()
        assert b is not b.bind()
        assert b != b.bind(x=5)
        assert b != 'test'

    def test_bind_keeps_class(self):
        class Wrapper(BoundLoggerBase):
            pass
        b = Wrapper(None, [], {})
        assert isinstance(b.bind(), Wrapper)

    def test_new_keeps_class(self):
        class Wrapper(BoundLoggerBase):
            pass
        b = Wrapper(None, [], {})
        assert isinstance(b.new(), Wrapper)

    def test_unbind(self):
        b = build_bl().bind(x=42, y=23).unbind('x', 'y')
        assert {} == b._context


class TestProcessing(object):
    def test_copies_context_before_processing(self):
        """
        BoundLoggerBase._process_event() gets called before relaying events
        to wrapped loggers.
        """
        def chk(_, __, event_dict):
            assert b._context is not event_dict
            return ''

        b = build_bl(processors=[chk])
        assert (('',), {}) == b._process_event('', 'event', {})
        assert 'event' not in b._context

    def test_chain_does_not_swallow_all_exceptions(self):
        b = build_bl(processors=[raiser(ValueError)])
        with pytest.raises(ValueError):
            b._process_event('', 'boom', {})

    def test_last_processor_returns_string(self):
        """
        If the final processor returns a string, ``(the_string,), {}`` is
        returned.
        """
        logger = stub(msg=lambda *args, **kw: (args, kw))
        b = build_bl(logger, processors=[lambda *_: 'foo'])
        assert (
            (('foo',), {})
            == b._process_event('', 'foo', {})
        )

    def test_last_processor_returns_tuple(self):
        """
        If the final processor returns a tuple, it is just passed through.
        """
        logger = stub(msg=lambda *args, **kw: (args, kw))
        b = build_bl(logger, processors=[lambda *_: (('foo',),
                                                     {'key': 'value'})])
        assert (
            (('foo',), {'key': 'value'})
            == b._process_event('', 'foo', {})
        )

    def test_last_processor_returns_dict(self):
        """
        If the final processor returns a dict, ``(), the_dict`` is returnend.
        """
        logger = stub(msg=lambda *args, **kw: (args, kw))
        b = build_bl(logger, processors=[lambda *_: {'event': 'foo'}])
        assert (
            ((), {'event': 'foo'})
            == b._process_event('', 'foo', {})
        )

    def test_last_processor_returns_unknown_value(self):
        """
        If the final processor returns something unexpected, raise ValueError
        with a helpful error message.
        """
        logger = stub(msg=lambda *args, **kw: (args, kw))
        b = build_bl(logger, processors=[lambda *_: object()])
        with pytest.raises(ValueError) as exc:
            b._process_event('', 'foo', {})

        assert (
            exc.value.args[0].startswith("Last processor didn't return")
        )


class TestProxying(object):
    def test_processor_raising_DropEvent_silently_aborts_chain(self, capsys):
        b = build_bl(processors=[raiser(DropEvent), raiser(ValueError)])
        b._proxy_to_logger('', None, x=5)
        assert (('', '') == capsys.readouterr())

########NEW FILE########
__FILENAME__ = test_config
# Copyright 2013 Hynek Schlawack
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

import warnings

import pytest

from pretend import call_recorder, call, stub

from structlog._base import BoundLoggerBase
from structlog._compat import PY3
from structlog._config import (
    BoundLoggerLazyProxy,
    _CONFIG,
    _BUILTIN_DEFAULT_CONTEXT_CLASS,
    _BUILTIN_DEFAULT_PROCESSORS,
    _BUILTIN_DEFAULT_LOGGER_FACTORY,
    _BUILTIN_DEFAULT_WRAPPER_CLASS,
    configure,
    configure_once,
    get_logger,
    reset_defaults,
    wrap_logger,
)


@pytest.fixture
def proxy():
    """
    Returns a BoundLoggerLazyProxy constructed w/o paramaters & None as logger.
    """
    return BoundLoggerLazyProxy(None)


class Wrapper(BoundLoggerBase):
    """
    Custom wrapper class for testing.
    """


class TestConfigure(object):
    def teardown_method(self, method):
        reset_defaults()

    def test_configure_all(self, proxy):
        x = stub()
        configure(processors=[x], context_class=dict)
        b = proxy.bind()
        assert [x] == b._processors
        assert dict is b._context.__class__

    def test_reset(self, proxy):
        x = stub()
        configure(processors=[x], context_class=dict, wrapper_class=Wrapper)
        reset_defaults()
        b = proxy.bind()
        assert [x] != b._processors
        assert _BUILTIN_DEFAULT_PROCESSORS == b._processors
        assert isinstance(b, _BUILTIN_DEFAULT_WRAPPER_CLASS)
        assert _BUILTIN_DEFAULT_CONTEXT_CLASS == b._context.__class__
        assert _BUILTIN_DEFAULT_LOGGER_FACTORY is _CONFIG.logger_factory

    def test_just_processors(self, proxy):
        x = stub()
        configure(processors=[x])
        b = proxy.bind()
        assert [x] == b._processors
        assert _BUILTIN_DEFAULT_PROCESSORS != b._processors
        assert _BUILTIN_DEFAULT_CONTEXT_CLASS == b._context.__class__

    def test_just_context_class(self, proxy):
        configure(context_class=dict)
        b = proxy.bind()
        assert dict is b._context.__class__
        assert _BUILTIN_DEFAULT_PROCESSORS == b._processors

    def test_configure_sets_is_configured(self):
        assert False is _CONFIG.is_configured
        configure()
        assert True is _CONFIG.is_configured

    def test_rest_resets_is_configured(self):
        configure()
        reset_defaults()
        assert False is _CONFIG.is_configured

    def test_configures_logger_factory(self):
        def f():
            pass

        configure(logger_factory=f)
        assert f is _CONFIG.logger_factory


class TestBoundLoggerLazyProxy(object):
    def teardown_method(self, method):
        reset_defaults()

    def test_repr(self):
        p = BoundLoggerLazyProxy(
            None, processors=[1, 2, 3], context_class=dict,
            initial_values={'foo': 42}, logger_factory_args=(4, 5),
        )
        assert (
            "<BoundLoggerLazyProxy(logger=None, wrapper_class=None, "
            "processors=[1, 2, 3], "
            "context_class=<%s 'dict'>, "
            "initial_values={'foo': 42}, "
            "logger_factory_args=(4, 5))>"
            % ('class' if PY3 else 'type',)
        ) == repr(p)

    def test_returns_bound_logger_on_bind(self, proxy):
        assert isinstance(proxy.bind(), BoundLoggerBase)

    def test_returns_bound_logger_on_new(self, proxy):
        assert isinstance(proxy.new(), BoundLoggerBase)

    def test_prefers_args_over_config(self):
        p = BoundLoggerLazyProxy(None, processors=[1, 2, 3],
                                 context_class=dict)
        b = p.bind()
        assert isinstance(b._context, dict)
        assert [1, 2, 3] == b._processors

        class Class(object):
            def __init__(self, *args, **kw):
                pass

            def update(self, *args, **kw):
                pass
        configure(processors=[4, 5, 6], context_class=Class)
        b = p.bind()
        assert not isinstance(b._context, Class)
        assert [1, 2, 3] == b._processors

    def test_falls_back_to_config(self, proxy):
        b = proxy.bind()
        assert isinstance(b._context, _CONFIG.default_context_class)
        assert _CONFIG.default_processors == b._processors

    def test_bind_honors_initial_values(self):
        p = BoundLoggerLazyProxy(None, initial_values={'a': 1, 'b': 2})
        b = p.bind()
        assert {'a': 1, 'b': 2} == b._context
        b = p.bind(c=3)
        assert {'a': 1, 'b': 2, 'c': 3} == b._context

    def test_bind_binds_new_values(self, proxy):
        b = proxy.bind(c=3)
        assert {'c': 3} == b._context

    def test_unbind_unbinds_from_initial_values(self):
        p = BoundLoggerLazyProxy(None, initial_values={'a': 1, 'b': 2})
        b = p.unbind('a')
        assert {'b': 2} == b._context

    def test_honors_wrapper_class(self):
        p = BoundLoggerLazyProxy(None, wrapper_class=Wrapper)
        b = p.bind()
        assert isinstance(b, Wrapper)

    def test_honors_wrapper_from_config(self, proxy):
        configure(wrapper_class=Wrapper)
        b = proxy.bind()
        assert isinstance(b, Wrapper)

    def test_new_binds_only_initial_values_impolicit_ctx_class(self, proxy):
        proxy = BoundLoggerLazyProxy(None, initial_values={'a': 1, 'b': 2})
        b = proxy.new(foo=42)
        assert {'a': 1, 'b': 2, 'foo': 42} == b._context

    def test_new_binds_only_initial_values_explicit_ctx_class(self, proxy):
        proxy = BoundLoggerLazyProxy(None,
                                     initial_values={'a': 1, 'b': 2},
                                     context_class=dict)
        b = proxy.new(foo=42)
        assert {'a': 1, 'b': 2, 'foo': 42} == b._context

    def test_rebinds_bind_method(self, proxy):
        """
        To save time, be rebind the bind method once the logger has been
        cached.
        """
        configure(cache_logger_on_first_use=True)
        bind = proxy.bind
        proxy.bind()
        assert bind != proxy.bind

    def test_does_not_cache_by_default(self, proxy):
        """
        Proxy's bind method doesn't change by default.
        """
        bind = proxy.bind
        proxy.bind()
        assert bind == proxy.bind

    def test_argument_takes_precedence_over_configuration(self):
        configure(cache_logger_on_first_use=True)
        proxy = BoundLoggerLazyProxy(None, cache_logger_on_first_use=False)
        bind = proxy.bind
        proxy.bind()
        assert bind == proxy.bind

    def test_argument_takes_precedence_over_configuration2(self):
        configure(cache_logger_on_first_use=False)
        proxy = BoundLoggerLazyProxy(None, cache_logger_on_first_use=True)
        bind = proxy.bind
        proxy.bind()
        assert bind != proxy.bind


class TestFunctions(object):
    def teardown_method(self, method):
        reset_defaults()

    def test_wrap_passes_args(self):
        logger = object()
        p = wrap_logger(logger, processors=[1, 2, 3], context_class=dict)
        assert logger is p._logger
        assert [1, 2, 3] == p._processors
        assert dict is p._context_class

    def test_wrap_returns_proxy(self):
        assert isinstance(wrap_logger(None), BoundLoggerLazyProxy)

    def test_configure_once_issues_warning_on_repeated_call(self):
        with warnings.catch_warnings(record=True) as warns:
            configure_once()
        assert 0 == len(warns)
        with warnings.catch_warnings(record=True) as warns:
            configure_once()
        assert 1 == len(warns)
        assert RuntimeWarning == warns[0].category
        assert 'Repeated configuration attempted.' == warns[0].message.args[0]

    def test_get_logger_configures_according_to_config(self):
        b = get_logger().bind()
        assert isinstance(b._logger,
                          _BUILTIN_DEFAULT_LOGGER_FACTORY().__class__)
        assert _BUILTIN_DEFAULT_PROCESSORS == b._processors
        assert isinstance(b, _BUILTIN_DEFAULT_WRAPPER_CLASS)
        assert _BUILTIN_DEFAULT_CONTEXT_CLASS == b._context.__class__

    def test_get_logger_passes_positional_arguments_to_logger_factory(self):
        """
        Ensure `get_logger` passes optional positional arguments through to
        the logger factory.
        """
        factory = call_recorder(lambda *args: object())
        configure(logger_factory=factory)
        get_logger('test').bind(x=42)
        assert [call('test')] == factory.calls

########NEW FILE########
__FILENAME__ = test_frames
# Copyright 2013 Hynek Schlawack
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

import sys

import pytest

from pretend import stub

import structlog._frames

from structlog._frames import (
    _find_first_app_frame_and_name,
    _format_exception,
    _format_stack,
)


class TestFindFirstAppFrameAndName(object):
    def test_ignores_structlog_by_default(self, monkeypatch):
        """
        No matter what you pass in, structlog frames get always ignored.
        """
        f1 = stub(f_globals={'__name__': 'test'}, f_back=None)
        f2 = stub(f_globals={'__name__': 'structlog.blubb'}, f_back=f1)
        monkeypatch.setattr(structlog._frames.sys, '_getframe', lambda: f2)
        f, n = _find_first_app_frame_and_name()
        monkeypatch.undo()
        assert ((f1, 'test') == f, n)

    def test_ignoring_of_additional_frame_names_works(self, monkeypatch):
        """
        Additional names are properly ignored too.
        """
        f1 = stub(f_globals={'__name__': 'test'}, f_back=None)
        f2 = stub(f_globals={'__name__': 'ignored.bar'}, f_back=f1)
        f3 = stub(f_globals={'__name__': 'structlog.blubb'}, f_back=f2)
        monkeypatch.setattr(structlog._frames.sys, '_getframe', lambda: f3)
        f, n = _find_first_app_frame_and_name()
        monkeypatch.undo()
        assert ((f1, 'test') == f, n)


@pytest.fixture
def exc_info():
    """
    Fake a valid exc_info.
    """
    try:
        raise ValueError
    except ValueError:
        return sys.exc_info()


class TestFormatException(object):
    def test_returns_str(self, exc_info):
        assert isinstance(_format_exception(exc_info), str)

    def test_formats(self, exc_info):
        assert _format_exception(exc_info).startswith(
            'Traceback (most recent call last):\n'
        )


class TestFormatStack(object):
    def test_returns_str(self):
        assert isinstance(_format_stack(sys._getframe()), str)

    def test_formats(self):
        assert _format_stack(sys._getframe()).startswith(
            'Stack (most recent call last):\n'
        )

########NEW FILE########
__FILENAME__ = test_generic
# Copyright 2013 Hynek Schlawack
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

from structlog._config import _CONFIG
from structlog._generic import BoundLogger
from structlog._loggers import ReturnLogger


class TestLogger(object):
    def log(self, msg):
        return 'log', msg

    def gol(self, msg):
        return 'gol', msg


class TestGenericBoundLogger(object):
    def test_caches(self):
        """
        __getattr__() gets called only once per logger method.
        """
        b = BoundLogger(
            ReturnLogger(),
            _CONFIG.default_processors,
            _CONFIG.default_context_class(),
        )
        assert 'msg' not in b.__dict__
        b.msg('foo')
        assert 'msg' in b.__dict__

    def test_proxies_anything(self):
        """
        Anything that isn't part of BoundLoggerBase gets proxied to the correct
        wrapped logger methods.
        """
        b = BoundLogger(
            ReturnLogger(),
            _CONFIG.default_processors,
            _CONFIG.default_context_class(),
        )
        assert 'log', 'foo' == b.log('foo')
        assert 'gol', 'bar' == b.gol('bar')

########NEW FILE########
__FILENAME__ = test_loggers
# Copyright 2013 Hynek Schlawack
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

import sys

from structlog._loggers import (
    PrintLogger,
    PrintLoggerFactory,
    ReturnLogger,
    ReturnLoggerFactory,
)


def test_return_logger():
    obj = ['hello']
    assert obj is ReturnLogger().msg(obj)


class TestPrintLogger(object):
    def test_prints_to_stdout_by_default(self, capsys):
        PrintLogger().msg('hello')
        out, err = capsys.readouterr()
        assert 'hello\n' == out
        assert '' == err

    def test_prints_to_correct_file(self, tmpdir, capsys):
        f = tmpdir.join('test.log')
        fo = f.open('w')
        PrintLogger(fo).msg('hello')
        out, err = capsys.readouterr()
        assert '' == out == err
        fo.close()
        assert 'hello\n' == f.read()

    def test_repr(self):
        assert repr(PrintLogger()).startswith(
            "<PrintLogger(file="
        )


class TestPrintLoggerFactory(object):
    def test_does_not_cache(self):
        """
        Due to doctest weirdness, we must not re-use PrintLoggers.
        """
        f = PrintLoggerFactory()
        assert f() is not f()

    def test_passes_file(self):
        """
        If a file is passed to the factory, it get passed on to the logger.
        """
        l = PrintLoggerFactory(sys.stderr)()
        assert sys.stderr is l._file

    def test_ignores_args(self):
        """
        PrintLogger doesn't take positional arguments.  If any are passed to
        the factory, they are not passed to the logger.
        """
        PrintLoggerFactory()(1, 2, 3)


class TestReturnLoggerFactory(object):
    def test_builds_returnloggers(self):
        f = ReturnLoggerFactory()
        assert isinstance(f(), ReturnLogger)

    def test_caches(self):
        """
        There's no need to have several loggers so we return the same one on
        each call.
        """
        f = ReturnLoggerFactory()
        assert f() is f()

    def test_ignores_args(self):
        """
        ReturnLogger doesn't take positional arguments.  If any are passed to
        the factory, they are not passed to the logger.
        """
        ReturnLoggerFactory()(1, 2, 3)

########NEW FILE########
__FILENAME__ = test_processors
# Copyright 2013 Hynek Schlawack
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

import datetime
import json
import sys

import pytest

from freezegun import freeze_time

import structlog

from structlog._compat import u, StringIO
from structlog.processors import (
    ExceptionPrettyPrinter,
    JSONRenderer,
    KeyValueRenderer,
    StackInfoRenderer,
    TimeStamper,
    UnicodeEncoder,
    _JSONFallbackEncoder,
    format_exc_info,
)
from structlog.threadlocal import wrap_dict


@pytest.fixture
def sio():
    return StringIO()


@pytest.fixture
def event_dict():
    class A(object):
        def __repr__(self):
            return '<A(\o/)>'

    return {'a': A(), 'b': [3, 4], 'x': 7, 'y': 'test', 'z': (1, 2)}


class TestKeyValueRenderer(object):
    def test_sort_keys(self, event_dict):
        assert (
            r"a=<A(\o/)> b=[3, 4] x=7 y='test' z=(1, 2)" ==
            KeyValueRenderer(sort_keys=True)(None, None, event_dict)
        )

    def test_order_complete(self, event_dict):
        assert (
            r"y='test' b=[3, 4] a=<A(\o/)> z=(1, 2) x=7" ==
            KeyValueRenderer(key_order=['y', 'b', 'a', 'z', 'x'])
            (None, None, event_dict)
        )

    def test_order_missing(self, event_dict):
        """
        Missing keys get rendered as None.
        """
        assert (
            r"c=None y='test' b=[3, 4] a=<A(\o/)> z=(1, 2) x=7" ==
            KeyValueRenderer(key_order=['c', 'y', 'b', 'a', 'z', 'x'])
            (None, None, event_dict)
        )

    def test_order_extra(self, event_dict):
        """
        Extra keys get sorted if sort_keys=True.
        """
        event_dict['B'] = 'B'
        event_dict['A'] = 'A'
        assert (
            r"c=None y='test' b=[3, 4] a=<A(\o/)> z=(1, 2) x=7 A='A' B='B'" ==
            KeyValueRenderer(key_order=['c', 'y', 'b', 'a', 'z', 'x'],
                             sort_keys=True)
            (None, None, event_dict)
        )

    def test_random_order(self, event_dict):
        rv = KeyValueRenderer()(None, None, event_dict)
        assert isinstance(rv, str)


class TestJSONRenderer(object):
    def test_renders_json(self, event_dict):
        assert (
            r'{"a": "<A(\\o/)>", "b": [3, 4], "x": 7, "y": "test", "z": '
            r'[1, 2]}'
            == JSONRenderer(sort_keys=True)(None, None, event_dict)
        )

    def test_FallbackEncoder_handles_ThreadLocalDictWrapped_dicts(self):
        s = json.dumps(wrap_dict(dict)({'a': 42}),
                       cls=_JSONFallbackEncoder)
        assert '{"a": 42}' == s

    def test_FallbackEncoder_falls_back(self):
        s = json.dumps({'date': datetime.date(1980, 3, 25)},
                       cls=_JSONFallbackEncoder,)

        assert '{"date": "datetime.date(1980, 3, 25)"}' == s


class TestTimeStamper(object):
    def test_disallowsNonUTCUNIXTimestamps(self):
        with pytest.raises(ValueError) as e:
            TimeStamper(utc=False)
        assert 'UNIX timestamps are always UTC.' == e.value.args[0]

    def test_insertsUTCUNIXTimestampByDefault(self):
        ts = TimeStamper()
        d = ts(None, None, {})
        # freezegun doesn't work with time.gmtime :(
        assert isinstance(d['timestamp'], int)

    @freeze_time('1980-03-25 16:00:00')
    def test_local(self):
        ts = TimeStamper(fmt='iso', utc=False)
        d = ts(None, None, {})
        assert '1980-03-25T16:00:00' == d['timestamp']

    @freeze_time('1980-03-25 16:00:00')
    def test_formats(self):
        ts = TimeStamper(fmt='%Y')
        d = ts(None, None, {})
        assert '1980' == d['timestamp']

    @freeze_time('1980-03-25 16:00:00')
    def test_adds_Z_to_iso(self):
        ts = TimeStamper(fmt='iso', utc=True)
        d = ts(None, None, {})
        assert '1980-03-25T16:00:00Z' == d['timestamp']


class TestFormatExcInfo(object):
    def test_formats_tuple(self, monkeypatch):
        monkeypatch.setattr(structlog.processors,
                            '_format_exception',
                            lambda exc_info: exc_info)
        d = format_exc_info(None, None, {'exc_info': (None, None, 42)})
        assert {'exception': (None, None, 42)} == d

    def test_gets_exc_info_on_bool(self):
        # monkeypatching sys.exc_info makes currently py.test return 1 on
        # success.
        try:
            raise ValueError('test')
        except ValueError:
            d = format_exc_info(None, None, {'exc_info': True})
        assert 'exc_info' not in d
        assert 'raise ValueError(\'test\')\nValueError: test' in d['exception']


class TestUnicodeEncoder(object):
    def test_encodes(self):
        ue = UnicodeEncoder()
        assert {'foo': b'b\xc3\xa4r'} == ue(None, None, {'foo': u('b\xe4r')})

    def test_passes_arguments(self):
        ue = UnicodeEncoder('latin1', 'xmlcharrefreplace')
        assert {'foo': b'&#8211;'} == ue(None, None, {'foo': u('\u2013')})


class TestExceptionPrettyPrinter(object):
    def test_stdout_by_default(self):
        """
        If no file is supplied, use stdout.
        """
        epp = ExceptionPrettyPrinter()
        assert sys.stdout is epp._file

    def test_prints_exception(self, sio):
        """
        If there's an `exception` key in the event_dict, just print it out.
        This happens if `format_exc_info` was run before us in the chain.
        """
        epp = ExceptionPrettyPrinter(file=sio)
        try:
            raise ValueError
        except ValueError:
            ed = format_exc_info(None, None, {'exc_info': True})
        epp(None, None, ed)

        out = sio.getvalue()
        assert 'test_prints_exception' in out
        assert 'raise ValueError' in out

    def test_removes_exception_after_printing(self, sio):
        """
        After pretty printing `exception` is removed from the event_dict.
        """
        epp = ExceptionPrettyPrinter(sio)
        try:
            raise ValueError
        except ValueError:
            ed = format_exc_info(None, None, {'exc_info': True})
        assert 'exception' in ed
        new_ed = epp(None, None, ed)
        assert 'exception' not in new_ed

    def test_handles_exc_info(self, sio):
        """
        If `exc_info` is passed in, it behaves like `format_exc_info`.
        """
        epp = ExceptionPrettyPrinter(sio)
        try:
            raise ValueError
        except ValueError:
            epp(None, None, {'exc_info': True})

        out = sio.getvalue()
        assert 'test_handles_exc_info' in out
        assert 'raise ValueError' in out

    def test_removes_exc_info_after_printing(self, sio):
        """
        After pretty printing `exception` is removed from the event_dict.
        """
        epp = ExceptionPrettyPrinter(sio)
        try:
            raise ValueError
        except ValueError:
            ed = epp(None, None, {'exc_info': True})
        assert 'exc_info' not in ed

    def test_nop_if_no_exception(self, sio):
        """
        If there is no exception, don't print anything.
        """
        epp = ExceptionPrettyPrinter(sio)
        epp(None, None, {})
        assert '' == sio.getvalue()


@pytest.fixture
def sir():
    return StackInfoRenderer()


class TestStackInfoRenderer(object):
    def test_removes_stack_info(self, sir):
        """
        The `stack_info` key is removed from `event_dict`.
        """
        ed = sir(None, None, {'stack_info': True})
        assert 'stack_info' not in ed

    def test_adds_stack_if_asked(self, sir):
        """
        If `stack_info` is true, `stack` is added.
        """
        ed = sir(None, None, {'stack_info': True})
        assert 'stack' in ed

    def test_renders_correct_stack(self, sir):
        ed = sir(None, None, {'stack_info': True})
        assert "ed = sir(None, None, {'stack_info': True})" in ed['stack']

########NEW FILE########
__FILENAME__ = test_stdlib
# Copyright 2013 Hynek Schlawack
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

import os

import logging

import pytest
from pretend import call_recorder

from structlog._exc import DropEvent
from structlog._loggers import ReturnLogger
from structlog.stdlib import (
    BoundLogger,
    CRITICAL,
    LoggerFactory,
    WARN,
    filter_by_level,
    _FixedFindCallerLogger,
)
from structlog._compat import PY2

from .additional_frame import additional_frame


def build_bl(logger=None, processors=None, context=None):
    """
    Convenience function to build BoundLogger with sane defaults.
    """
    return BoundLogger(
        logger or ReturnLogger(),
        processors,
        {}
    )


class TestLoggerFactory(object):
    def setup_method(self, method):
        """
        The stdlib logger factory modifies global state to fix caller
        identification.
        """
        self.original_logger = logging.getLoggerClass()

    def teardown_method(self, method):
        logging.setLoggerClass(self.original_logger)

    def test_deduces_correct_name(self):
        """
        The factory isn't called directly but from structlog._config so
        deducing has to be slightly smarter.
        """
        assert 'tests.additional_frame' == (
            additional_frame(LoggerFactory()).name
        )
        assert 'tests.test_stdlib' == LoggerFactory()().name

    def test_ignores_frames(self):
        """
        The name guesser walks up the frames until it reaches a frame whose
        name is not from structlog or one of the configurable other names.
        """
        assert '__main__' == additional_frame(LoggerFactory(
            ignore_frame_names=['tests.', '_pytest.'])
        ).name

    def test_deduces_correct_caller(self):
        logger = _FixedFindCallerLogger('test')
        file_name, line_number, func_name = logger.findCaller()[:3]
        assert file_name == os.path.realpath(__file__)
        assert func_name == 'test_deduces_correct_caller'

    @pytest.mark.skipif(PY2, reason="Py3-only")
    def test_stack_info(self):
        logger = _FixedFindCallerLogger('test')
        testing, is_, fun, stack_info = logger.findCaller(stack_info=True)
        assert 'testing, is_, fun' in stack_info

    @pytest.mark.skipif(PY2, reason="Py3-only")
    def test_no_stack_info_by_default(self):
        logger = _FixedFindCallerLogger('test')
        testing, is_, fun, stack_info = logger.findCaller()
        assert None is stack_info

    def test_find_caller(self, monkeypatch):
        logger = LoggerFactory()()
        log_handle = call_recorder(lambda x: None)
        monkeypatch.setattr(logger, 'handle', log_handle)
        logger.error('Test')
        log_record = log_handle.calls[0].args[0]
        assert log_record.funcName == 'test_find_caller'
        assert log_record.name == __name__
        assert log_record.filename == os.path.basename(__file__)

    def test_sets_correct_logger(self):
        assert logging.getLoggerClass() is logging.Logger
        LoggerFactory()
        assert logging.getLoggerClass() is _FixedFindCallerLogger

    def test_positional_argument_avoids_guessing(self):
        """
        If a positional argument is passed to the factory, it's used as the
        name instead of guessing.
        """
        l = LoggerFactory()('foo')
        assert 'foo' == l.name


class TestFilterByLevel(object):
    def test_filters_lower_levels(self):
        logger = logging.Logger(__name__)
        logger.setLevel(CRITICAL)
        with pytest.raises(DropEvent):
            filter_by_level(logger, 'warn', {})

    def test_passes_higher_levels(self):
        logger = logging.Logger(__name__)
        logger.setLevel(WARN)
        event_dict = {'event': 'test'}
        assert event_dict is filter_by_level(logger, 'warn', event_dict)
        assert event_dict is filter_by_level(logger, 'error', event_dict)


class TestBoundLogger(object):
    @pytest.mark.parametrize(('method_name'), [
        'debug', 'info', 'warning', 'error', 'critical',
    ])
    def test_proxies_to_correct_method(self, method_name):
        def return_method_name(_, method_name, __):
            return method_name
        bl = BoundLogger(ReturnLogger(), [return_method_name], {})
        assert method_name == getattr(bl, method_name)('event')

########NEW FILE########
__FILENAME__ = test_threadlocal
# Copyright 2013 Hynek Schlawack
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import threading

import pytest

from structlog._base import BoundLoggerBase
from structlog._config import wrap_logger
from structlog._compat import OrderedDict
from structlog._loggers import ReturnLogger
from structlog.threadlocal import as_immutable, wrap_dict, tmp_bind


@pytest.fixture
def D():
    """
    Returns a dict wrapped in _ThreadLocalDictWrapper.
    """
    return wrap_dict(dict)


@pytest.fixture
def log():
    return wrap_logger(logger(), context_class=wrap_dict(OrderedDict))


@pytest.fixture
def logger():
    """
    Returns a simple logger stub with a *msg* method that takes one argument
    which gets returned.
    """
    return ReturnLogger()


class TestTmpBind(object):
    def test_yields_a_new_bound_loggger_if_called_on_lazy_proxy(self, log):
        with tmp_bind(log, x=42) as tmp_log:
            assert "x=42 event='bar'" == tmp_log.msg('bar')
        assert "event='bar'" == log.msg('bar')

    def test_bind(self, log):
        log = log.bind(y=23)
        with tmp_bind(log, x=42, y='foo') as tmp_log:
            assert (
                {'y': 'foo', 'x': 42}
                == tmp_log._context._dict == log._context._dict
            )
        assert {'y': 23} == log._context._dict
        assert "y=23 event='foo'" == log.msg('foo')


class TestAsImmutable(object):
    def test_does_not_affect_global(self, log):
        log = log.new(x=42)
        il = as_immutable(log)
        assert isinstance(il._context, dict)
        il = il.bind(y=23)
        assert {'x': 42, 'y': 23} == il._context
        assert {'x': 42} == log._context._dict

    def test_converts_proxy(self, log):
        il = as_immutable(log)
        assert isinstance(il._context, dict)
        assert isinstance(il, BoundLoggerBase)

    def test_works_with_immutable(self, log):
        il = as_immutable(log)
        assert isinstance(il._context, dict)
        assert isinstance(as_immutable(il), BoundLoggerBase)


class TestThreadLocalDict(object):
    def test_wrap_returns_distinct_classes(self):
        D1 = wrap_dict(dict)
        D2 = wrap_dict(dict)
        assert D1 != D2
        assert D1 is not D2
        D1.x = 42
        D2.x = 23
        assert D1.x != D2.x

    def test_is_thread_local(self, D):
        class TestThread(threading.Thread):
            def __init__(self, d):
                self._d = d
                threading.Thread.__init__(self)

            def run(self):
                assert 'x' not in self._d._dict
                self._d['x'] = 23
        d = wrap_dict(dict)()
        d['x'] = 42
        t = TestThread(d)
        t.start()
        t.join()
        assert 42 == d._dict['x']

    def test_context_is_global_to_thread(self, D):
        d1 = D({'a': 42})
        d2 = D({'b': 23})
        d3 = D()
        assert {'a': 42, 'b': 23} == d1._dict == d2._dict == d3._dict
        assert d1 == d2 == d3
        D_ = wrap_dict(dict)
        d_ = D_({'a': 42, 'b': 23})
        assert d1 != d_

    def test_init_with_itself_works(self, D):
        d = D({'a': 42})
        assert {'a': 42, 'b': 23} == D(d, b=23)._dict

    def test_iter_works(self, D):
        d = D({'a': 42})
        assert ['a'] == list(iter(d))

    def test_non_dunder_proxy_works(self, D):
        d = D({'a': 42})
        assert 1 == len(d)
        d.clear()
        assert 0 == len(d)

    def test_repr(self, D):
        r = repr(D({'a': 42}))
        assert r.startswith('<WrappedDict-')
        assert r.endswith("({'a': 42})>")

    def test_is_greenlet_local(self, D):
        greenlet = pytest.importorskip("greenlet")
        d = wrap_dict(dict)()
        d['x'] = 42

        def run():
            assert 'x' not in d._dict
            d['x'] = 23

        greenlet.greenlet(run).switch()
        assert 42 == d._dict["x"]

    def test_delattr(self, D):
        d = D()
        d['x'] = 42
        assert 42 == d._dict["x"]
        del d.__class__._tl.dict_

    def test_del(self, D):
        d = D()
        d['x'] = 13
        del d['x']
        assert 'x' not in d._dict

########NEW FILE########
__FILENAME__ = test_twisted
# Copyright 2013 Hynek Schlawack
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

import pytest
pytest.importorskip('twisted')

import json

from pretend import call_recorder
from twisted.python.failure import Failure, NoCurrentExceptionError
from twisted.python.log import ILogObserver

from structlog._config import _CONFIG
from structlog._compat import OrderedDict, StringIO
from structlog._loggers import ReturnLogger
from structlog.twisted import (
    BoundLogger,
    EventAdapter,
    JSONRenderer,
    JSONLogObserverWrapper,
    LoggerFactory,
    PlainFileLogObserver,
    _extractStuffAndWhy,
    plainJSONStdOutLogger,
)


def test_LoggerFactory():
    from twisted.python import log
    assert log is LoggerFactory()()


def _render_repr(_, __, event_dict):
    return repr(event_dict)


def build_bl(logger=None, processors=None, context=None):
    """
    Convenience function to build BoundLoggerses with sane defaults.
    """
    return BoundLogger(
        logger or ReturnLogger(),
        processors or _CONFIG.default_processors,
        context if context is not None else _CONFIG.default_context_class(),
    )


class TestBoundLogger(object):
    def test_msg(self):
        bl = build_bl()
        assert "foo=42 event='event'" == bl.msg('event', foo=42)

    def test_errVanilla(self):
        bl = build_bl()
        assert "foo=42 event='event'" == bl.err('event', foo=42)

    def test_errWithFailure(self):
        bl = build_bl(processors=[EventAdapter()])
        try:
            raise ValueError
        except ValueError:
            # Use str() for comparison to avoid tricky
            # deep-compares of Failures.
            assert (
                str(((), {'_stuff': Failure(ValueError()),
                          '_why': "foo=42 event='event'"}))
                == str(bl.err('event', foo=42))
            )


class TestExtractStuffAndWhy(object):
    def test_extractFailsOnTwoFailures(self):
        with pytest.raises(ValueError) as e:
            _extractStuffAndWhy({'_stuff': Failure(ValueError),
                                 'event': Failure(TypeError)})
        assert (
            'Both _stuff and event contain an Exception/Failure.'
            == e.value.args[0]
        )

    def test_failsOnConflictingEventAnd_why(self):
        with pytest.raises(ValueError) as e:
            _extractStuffAndWhy({'_why': 'foo', 'event': 'bar'})
        assert (
            'Both `_why` and `event` supplied.'
            == e.value.args[0]
        )

    def test_handlesFailures(self):
        assert (
            Failure(ValueError()), 'foo', {}
            == _extractStuffAndWhy({'_why': 'foo',
                                    '_stuff': Failure(ValueError())})
        )
        assert (
            Failure(ValueError()), 'error', {}
            == _extractStuffAndWhy({'_stuff': Failure(ValueError())})
        )

    def test_handlesMissingFailure(self):
        assert (
            (None, 'foo', {})
            == _extractStuffAndWhy({'event': 'foo'})
        )

    def test_recognizesErrorsAndCleansThem(self):
        """
        If no error is supplied, the environment is checked for one.  If one is
        found, it's used and cleared afterwards so log.err doesn't add it as
        well.
        """
        try:
            raise ValueError
        except ValueError:
            f = Failure()
            _stuff, _why, ed = _extractStuffAndWhy({'event': 'foo'})
            assert _stuff.value is f.value
            with pytest.raises(NoCurrentExceptionError):
                Failure()


class TestEventAdapter(object):
    """
    Some tests here are redundant because they predate _extractStuffAndWhy.
    """
    def test_EventAdapterFormatsLog(self):
        la = EventAdapter(_render_repr)
        assert "{'foo': 'bar'}" == la(None, 'msg', {'foo': 'bar'})

    def test_transforms_whyIntoEvent(self):
        """
        log.err(_stuff=exc, _why='foo') makes the output 'event="foo"'
        """
        la = EventAdapter(_render_repr)
        error = ValueError('test')
        rv = la(None, 'err', {
            '_stuff': error,
            '_why': 'foo',
            'event': None,
        })
        assert () == rv[0]
        assert isinstance(rv[1]['_stuff'], Failure)
        assert error == rv[1]['_stuff'].value
        assert "{'event': 'foo'}" == rv[1]['_why']

    def test_worksUsualCase(self):
        """
        log.err(exc, _why='foo') makes the output 'event="foo"'
        """
        la = EventAdapter(_render_repr)
        error = ValueError('test')
        rv = la(None, 'err', {'event': error, '_why': 'foo'})
        assert () == rv[0]
        assert isinstance(rv[1]['_stuff'], Failure)
        assert error == rv[1]['_stuff'].value
        assert "{'event': 'foo'}" == rv[1]['_why']

    def test_allKeywords(self):
        """
        log.err(_stuff=exc, _why='event')
        """
        la = EventAdapter(_render_repr)
        error = ValueError('test')
        rv = la(None, 'err', {'_stuff': error, '_why': 'foo'})
        assert () == rv[0]
        assert isinstance(rv[1]['_stuff'], Failure)
        assert error == rv[1]['_stuff'].value
        assert "{'event': 'foo'}" == rv[1]['_why']

    def test_noFailure(self):
        """
        log.err('event')
        """
        la = EventAdapter(_render_repr)
        assert ((), {
            '_stuff': None,
            '_why': "{'event': 'someEvent'}",
        }) == la(None, 'err', {
            'event': 'someEvent'
        })

    def test_noFailureWithKeyword(self):
        """
        log.err(_why='event')
        """
        la = EventAdapter(_render_repr)
        assert ((), {
            '_stuff': None,
            '_why': "{'event': 'someEvent'}",
        }) == la(None, 'err', {
            '_why': 'someEvent'
        })

    def test_catchesConflictingEventAnd_why(self):
        la = EventAdapter(_render_repr)
        with pytest.raises(ValueError) as e:
            la(None, 'err', {
                'event': 'someEvent',
                '_why': 'someReason',
            })
        assert 'Both `_why` and `event` supplied.' == e.value.args[0]


@pytest.fixture
def jr():
    """
    A plain Twisted JSONRenderer.
    """
    return JSONRenderer()


class TestJSONRenderer(object):
    def test_dumpsKWsAreHandedThrough(self, jr):
        """
        JSONRenderer allows for setting arguments that are passed to
        json.dumps().  Make sure they are passed.
        """
        d = OrderedDict(x='foo')
        d.update(a='bar')
        jr_sorted = JSONRenderer(sort_keys=True)
        assert jr_sorted(None, 'err', d) != jr(None, 'err', d)

    def test_handlesMissingFailure(self, jr):
        assert '{"event": "foo"}' == jr(None, 'err', {'event': 'foo'})[0][0]
        assert '{"event": "foo"}' == jr(None, 'err', {'_why': 'foo'})[0][0]

    def test_msgWorksToo(self, jr):
        assert '{"event": "foo"}' == jr(None, 'msg', {'_why': 'foo'})[0][0]

    def test_handlesFailure(self, jr):
        rv = jr(None, 'err', {'event': Failure(ValueError())})[0][0]
        assert 'Failure: exceptions.ValueError' in rv
        assert '"event": "error"' in rv

    def test_setsStructLogField(self, jr):
        """
        Formatted entries are marked so they can be identified without guessing
        for example in JSONLogObserverWrapper.
        """
        assert {'_structlog': True} == jr(None, 'msg', {'_why': 'foo'})[1]


class TestPlainFileLogObserver(object):
    def test_isLogObserver(self):
        assert ILogObserver.providedBy(PlainFileLogObserver(StringIO()))

    def test_writesOnlyMessageWithLF(self):
        sio = StringIO()
        PlainFileLogObserver(sio)({'system': 'some system',
                                   'message': ('hello',)})
        assert 'hello\n' == sio.getvalue()


class TestJSONObserverWrapper(object):
    def test_IsAnObserver(self):
        assert ILogObserver.implementedBy(JSONLogObserverWrapper)

    def test_callsWrappedObserver(self):
        """
        The wrapper always runs the wrapped observer in the end.
        """
        o = call_recorder(lambda *a, **kw: None)
        JSONLogObserverWrapper(o)({'message': ('hello',)})
        assert 1 == len(o.calls)

    def test_jsonifiesPlainLogEntries(self):
        """
        Entries that aren't formatted by JSONRenderer are rendered as JSON
        now.
        """
        o = call_recorder(lambda *a, **kw: None)
        JSONLogObserverWrapper(o)({'message': ('hello',), 'system': '-'})
        msg = json.loads(o.calls[0].args[0]['message'][0])
        assert msg == {'event': 'hello', 'system': '-'}

    def test_leavesStructLogAlone(self):
        """
        Entries that are formatted by JSONRenderer are left alone.
        """
        d = {'message': ('hello',), '_structlog': True}

        def verify(eventDict):
            assert d == eventDict

        JSONLogObserverWrapper(verify)(d)


class TestPlainJSONStdOutLogger(object):
    def test_isLogObserver(self):
        assert ILogObserver.providedBy(plainJSONStdOutLogger())

########NEW FILE########
__FILENAME__ = test_utils
# Copyright 2013 Hynek Schlawack
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

import errno

import pytest

from pretend import raiser

from structlog._utils import until_not_interrupted


class TestUntilNotInterrupted(object):
    def test_passes_arguments_and_returns_return_value(self):
        def returner(*args, **kw):
            return args, kw
        assert ((42,), {'x': 23}) == until_not_interrupted(returner, 42, x=23)

    def test_leaves_unrelated_exceptions_through(self):
        exc = IOError
        with pytest.raises(exc):
            until_not_interrupted(raiser(exc('not EINTR')))

    def test_retries_on_EINTR(self):
        calls = [0]

        def raise_on_first_three():
            if calls[0] < 3:
                calls[0] += 1
                raise IOError(errno.EINTR)

        until_not_interrupted(raise_on_first_three)

        assert 3 == calls[0]

########NEW FILE########
