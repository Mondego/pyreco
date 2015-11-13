__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# pg8000 documentation build configuration file, created by
# sphinx-quickstart on Mon Sep 15 09:38:48 2008.
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
extensions = []

# Add any paths that contain templates here, relative to this directory.
templates_path = ['.templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

# General substitutions.
project = 'pg8000'
copyright = '2008, Mathieu Fenniak'

# The default replacements for |version| and |release|, also used in various
# other places throughout the built documents.
#
# The short X.Y version.
version = '1.9'
# The full version, including alpha/beta/rc tags.
release = '1.9.9'

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
html_static_path = ['.static']

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
htmlhelp_basename = 'pg8000doc'


# Options for LaTeX output
# ------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, document class [howto/manual]).
latex_documents = [
  ('index', 'pg8000.tex', 'pg8000 Documentation',
   'Mathieu Fenniak', 'manual'),
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
__FILENAME__ = core
# Copyright (c) 2007-2009, Mathieu Fenniak
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
# * Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.
# * Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
# * The name of the author may not be used to endorse or promote products
# derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

__author__ = "Mathieu Fenniak"

import datetime
from datetime import timedelta
from pg8000 import (
    Interval, min_int2, max_int2, min_int4, max_int4, min_int8, max_int8,
    Bytea)
from pg8000.errors import (
    NotSupportedError, ProgrammingError, InternalError, IntegrityError,
    OperationalError, DatabaseError, InterfaceError, Error,
    CopyQueryOrTableRequiredError, CursorClosedError, QueryParameterParseError,
    ArrayContentNotHomogenousError, ArrayContentEmptyError,
    ArrayDimensionsNotConsistentError, ArrayContentNotSupportedError, Warning,
    CopyQueryWithoutStreamError)
from warnings import warn
import socket
import threading
from struct import pack
from hashlib import md5
from decimal import Decimal
import pg8000
import pg8000.util
from pg8000 import (
    i_unpack, ii_unpack, iii_unpack, h_pack, d_unpack, q_unpack, d_pack,
    f_unpack, q_pack, i_pack, h_unpack, dii_unpack, qii_unpack, ci_unpack,
    bh_unpack, ihihih_unpack, cccc_unpack, ii_pack, iii_pack, dii_pack,
    qii_pack)
from collections import deque, defaultdict
from itertools import count, islice
from pg8000.six.moves import map
from pg8000.six import (
    b, Iterator, PY2, integer_types, next, PRE_26, text_type, u, IS_JYTHON)
from sys import exc_info
from uuid import UUID
from copy import deepcopy
from calendar import timegm

ZERO = timedelta(0)


class UTC(datetime.tzinfo):

    def utcoffset(self, dt):
        return ZERO

    def tzname(self, dt):
        return "UTC"

    def dst(self, dt):
        return ZERO

utc = UTC()

if PRE_26:
    bytearray = list


FC_TEXT = 0
FC_BINARY = 1


def convert_paramstyle(style, query):
    # I don't see any way to avoid scanning the query string char by char,
    # so we might as well take that careful approach and create a
    # state-based scanner.  We'll use int variables for the state.
    #  0 -- outside quoted string
    #  1 -- inside single-quote string '...'
    #  2 -- inside quoted identifier   "..."
    #  3 -- inside escaped single-quote string, E'...'
    #  4 -- inside parameter name eg. :name
    OUTSIDE = 0
    INSIDE_SQ = 1
    INSIDE_QI = 2
    INSIDE_ES = 3
    INSIDE_PN = 4

    in_quote_escape = False
    in_param_escape = False
    placeholders = []
    output_query = []
    param_idx = map(lambda x: "$" + str(x), count(1))
    state = OUTSIDE
    prev_c = None
    for i, c in enumerate(query):
        if i + 1 < len(query):
            next_c = query[i + 1]
        else:
            next_c = None

        if state == OUTSIDE:
            if c == "'":
                output_query.append(c)
                if prev_c == 'E':
                    state = INSIDE_ES
                else:
                    state = INSIDE_SQ
            elif c == '"':
                output_query.append(c)
                state = INSIDE_QI
            elif style == "qmark" and c == "?":
                output_query.append(next(param_idx))
            elif style == "numeric" and c == ":":
                output_query.append("$")
            elif style == "named" and c == ":":
                state = INSIDE_PN
                placeholders.append('')
            elif style == "pyformat" and c == '%' and next_c == "(":
                state = INSIDE_PN
                placeholders.append('')
            elif style in ("format", "pyformat") and c == "%":
                style = "format"
                if in_param_escape:
                    in_param_escape = False
                    output_query.append(c)
                else:
                    if next_c == "%":
                        in_param_escape = True
                    elif next_c == "s":
                        state = INSIDE_PN
                        output_query.append(next(param_idx))
                    else:
                        raise QueryParameterParseError(
                            "Only %s and %% are supported")
            else:
                output_query.append(c)

        elif state == INSIDE_SQ:
            if c == "'":
                output_query.append(c)
                if in_quote_escape:
                    in_quote_escape = False
                else:
                    if next_c == "'":
                        in_quote_escape = True
                    else:
                        state = OUTSIDE
            elif style in ("pyformat", "format") and c == "%":
                # hm... we're only going to support an escaped percent sign
                if in_param_escape:
                    in_param_escape = False
                    output_query.append(c)
                else:
                    if next_c == "%":
                        in_param_escape = True
                    else:
                        raise QueryParameterParseError(
                            "'%" + next_c + "' not supported in quoted string")
            else:
                output_query.append(c)

        elif state == INSIDE_QI:
            if c == '"':
                state = OUTSIDE
                output_query.append(c)
            elif style in ("pyformat", "format") and c == "%":
                # hm... we're only going to support an escaped percent sign
                if in_param_escape:
                    in_param_escape = False
                    output_query.append(c)
                else:
                    if next_c == "%":
                        in_param_escape = True
                    else:
                        raise QueryParameterParseError(
                            "'%" + next_c + "' not supported in quoted string")
            else:
                output_query.append(c)

        elif state == INSIDE_ES:
            if c == "'" and prev_c != "\\":
                # check for escaped single-quote
                output_query.append(c)
                state = OUTSIDE
            elif style in ("pyformat", "format") and c == "%":
                # hm... we're only going to support an escaped percent sign
                if in_param_escape:
                    in_param_escape = False
                    output_query.append(c)
                else:
                    if next_c == "%":
                        in_param_escape = True
                    else:
                        raise QueryParameterParseError(
                            "'%" + next_c + "' not supported in quoted string")
            else:
                output_query.append(c)

        elif state == INSIDE_PN:
            if style == 'named':
                placeholders[-1] += c
                if next_c is None or (not next_c.isalnum() and next_c != '_'):
                    state = OUTSIDE
                    try:
                        pidx = placeholders.index(placeholders[-1], 0, -1)
                        output_query.append("$" + str(pidx + 1))
                        del placeholders[-1]
                    except ValueError:
                        output_query.append("$" + str(len(placeholders)))
            elif style == 'pyformat':
                if prev_c == ')' and c == "s":
                    state = OUTSIDE
                    try:
                        pidx = placeholders.index(placeholders[-1], 0, -1)
                        output_query.append("$" + str(pidx + 1))
                        del placeholders[-1]
                    except ValueError:
                        output_query.append("$" + str(len(placeholders)))
                elif c in "()":
                    pass
                else:
                    placeholders[-1] += c
            elif style == 'format':
                state = OUTSIDE

        prev_c = c

    if style in ('numeric', 'qmark', 'format'):
        def make_args(vals):
            return vals
    else:
        def make_args(vals):
            return tuple(vals[p] for p in placeholders)

    return ''.join(output_query), make_args


def require_open_cursor(fn):
    def _fn(self, *args, **kwargs):
        if self._c is None:
            raise CursorClosedError()
        return fn(self, *args, **kwargs)
    return _fn


EPOCH = datetime.datetime(2000, 1, 1)
EPOCH_TZ = EPOCH.replace(tzinfo=utc)
EPOCH_SECONDS = timegm(EPOCH.timetuple())
utcfromtimestamp = datetime.datetime.utcfromtimestamp

INFINITY_MICROSECONDS = 2 ** 63 - 1
MINUS_INFINITY_MICROSECONDS = -1 * INFINITY_MICROSECONDS - 1


# data is 64-bit integer representing microseconds since 2000-01-01
def timestamp_recv_integer(data, offset, length):
    micros = q_unpack(data, offset)[0]
    try:
        return EPOCH + timedelta(microseconds=micros)
    except OverflowError:
        if micros == INFINITY_MICROSECONDS:
            return datetime.datetime.max
        elif micros == MINUS_INFINITY_MICROSECONDS:
            return datetime.datetime.min
        else:
            raise exc_info()[1]


# data is double-precision float representing seconds since 2000-01-01
def timestamp_recv_float(data, offset, length):
    return utcfromtimestamp(EPOCH_SECONDS + d_unpack(data, offset)[0])


# data is 64-bit integer representing microseconds since 2000-01-01
def timestamp_send_integer(v):
    if v == datetime.datetime.max:
        micros = INFINITY_MICROSECONDS
    elif v == datetime.datetime.min:
        micros = MINUS_INFINITY_MICROSECONDS
    else:
        micros = int(
            (timegm(v.timetuple()) - EPOCH_SECONDS) * 1e6) + v.microsecond
    return q_pack(micros)


# data is double-precision float representing seconds since 2000-01-01
def timestamp_send_float(v):
    return d_pack(timegm(v.timetuple) + v.microsecond / 1e6 - EPOCH_SECONDS)


def timestamptz_send_integer(v):
    # timestamps should be sent as UTC.  If they have zone info,
    # convert them.
    return timestamp_send_integer(v.astimezone(utc).replace(tzinfo=None))


def timestamptz_send_float(v):
    # timestamps should be sent as UTC.  If they have zone info,
    # convert them.
    return timestamp_send_float(v.astimezone(utc).replace(tzinfo=None))

DATETIME_MAX_TZ = datetime.datetime.max.replace(tzinfo=utc)
DATETIME_MIN_TZ = datetime.datetime.min.replace(tzinfo=utc)


# return a timezone-aware datetime instance if we're reading from a
# "timestamp with timezone" type.  The timezone returned will always be
# UTC, but providing that additional information can permit conversion
# to local.
def timestamptz_recv_integer(data, offset, length):
    micros = q_unpack(data, offset)[0]
    try:
        return EPOCH_TZ + timedelta(microseconds=micros)
    except OverflowError:
        if micros == INFINITY_MICROSECONDS:
            return DATETIME_MAX_TZ
        elif micros == MINUS_INFINITY_MICROSECONDS:
            return DATETIME_MIN_TZ
        else:
            raise exc_info()[1]


def timestamptz_recv_float(data, offset, length):
    return timestamp_recv_float(data, offset, length).replace(tzinfo=utc)


def interval_send_integer(v):
    microseconds = v.microseconds
    try:
        microseconds += int(v.seconds * 1e6)
    except AttributeError:
        pass

    try:
        months = v.months
    except AttributeError:
        months = 0

    return qii_pack(microseconds, v.days, months)


def interval_send_float(v):
    seconds = v.microseconds / 1000.0 / 1000.0
    try:
        seconds += v.seconds
    except AttributeError:
        pass

    try:
        months = v.months
    except AttributeError:
        months = 0

    return dii_pack(seconds, v.days, months)


def interval_recv_integer(data, offset, length):
    microseconds, days, months = qii_unpack(data, offset)
    if months == 0:
        seconds, micros = divmod(microseconds, 1e6)
        return datetime.timedelta(days, seconds, micros)
    else:
        return Interval(microseconds, days, months)


def interval_recv_float(data, offset, length):
    seconds, days, months = dii_unpack(data, offset)
    if months == 0:
        secs, microseconds = divmod(seconds, 1e6)
        return datetime.timedelta(days, secs, microseconds)
    else:
        return Interval(int(seconds * 1000 * 1000), days, months)


def int8_recv(data, offset, length):
    return q_unpack(data, offset)[0]


def int2_recv(data, offset, length):
    return h_unpack(data, offset)[0]


def int4_recv(data, offset, length):
    return i_unpack(data, offset)[0]


def float4_recv(data, offset, length):
    return f_unpack(data, offset)[0]


def float8_recv(data, offset, length):
    return d_unpack(data, offset)[0]


def bytea_send(v):
    return v

# bytea
if PY2:
    def bytea_recv(data, offset, length):
        return Bytea(data[offset:offset + length])
else:
    def bytea_recv(data, offset, length):
        return data[offset:offset + length]


def uuid_send(v):
    return v.bytes


def uuid_recv(data, offset, length):
    return UUID(bytes=data[offset:offset+length])


TRUE = b("\x01")
FALSE = b("\x00")


def bool_send(v):
    return TRUE if v else FALSE


NULL = i_pack(-1)

NULL_BYTE = b('\x00')


def null_send(v):
    return NULL


def int_in(data, offset, length):
    return int(data[offset: offset + length])


##
# The class of object returned by the {@link #ConnectionWrapper.cursor cursor
# method}.
# The Cursor class allows multiple queries to be performed concurrently with a
# single PostgreSQL connection.  The Cursor object is implemented internally by
# using a {@link PreparedStatement PreparedStatement} object, so if you plan to
# use a statement multiple times, you might as well create a PreparedStatement
# and save a small amount of reparsing time.
# <p>
# As of v1.01, instances of this class are thread-safe.  See {@link
# PreparedStatement PreparedStatement} for more information.
# <p>
# Stability: Added in v1.00, stability guaranteed for v1.xx.
#
# @param connection     An instance of {@link Connection Connection}.
class Cursor(Iterator):
    def __init__(self, connection):
        self._c = connection
        self._stmt = None
        self.arraysize = 1
        self._row_count = -1

    def require_stmt(func):
        def retval(self, *args, **kwargs):
            if self._stmt is None:
                raise ProgrammingError("attempting to use unexecuted cursor")
            return func(self, *args, **kwargs)
        return retval

    ##
    # This read-only attribute returns a reference to the connection object on
    # which the cursor was created.
    # <p>
    # Stability: Part of a DBAPI 2.0 extension.  A warning "DB-API extension
    # cursor.connection used" will be fired.
    @property
    def connection(self):
        warn("DB-API extension cursor.connection used", stacklevel=3)
        return self._c

    ##
    # This read-only attribute specifies the number of rows that the last
    # .execute*() produced (for DQL statements like 'select') or affected (for
    # DML statements like 'update' or 'insert').
    # <p>
    # The attribute is -1 in case no .execute*() has been performed on the
    # cursor or the rowcount of the last operation is cannot be determined by
    # the interface.
    # <p>
    # Stability: Part of the DBAPI 2.0 specification.
    @property
    def rowcount(self):
        return self._row_count

    ##
    # This read-only attribute is a sequence of 7-item sequences.  Each value
    # contains information describing one result column.  The 7 items returned
    # for each column are (name, type_code, display_size, internal_size,
    # precision, scale, null_ok).  Only the first two values are provided by
    # this interface implementation.
    # <p>
    # Stability: Part of the DBAPI 2.0 specification.
    description = property(lambda self: self._getDescription())

    @require_open_cursor
    def _getDescription(self):
        if self._stmt is None:
            return None
        row_desc = self._stmt.get_row_description()
        if len(row_desc) == 0:
            return None
        columns = []
        for col in row_desc:
            columns.append(
                (col["name"], col["type_oid"], None, None, None, None, None))
        return columns

    ##
    # Executes a database operation.  Parameters may be provided as a sequence
    # or mapping and will be bound to variables in the operation.
    # <p>
    # Stability: Part of the DBAPI 2.0 specification.
    def execute(self, operation, args=None, stream=None):
        if args is None:
            args = tuple()

        self._row_count = -1
        if not self._c.use_cache:
            self._c.statement_cache.clear()

        try:
            self._c.begin()
        except AttributeError:
            if self._c is None:
                raise InterfaceError("Cursor closed")
            else:
                raise exc_info()[1]

        self._stmt = self._get_ps(operation, args)
        self._stmt.execute(args, stream=stream)
        self._row_count = self._stmt.row_count

    ##
    # Prepare a database operation and then execute it against all parameter
    # sequences or mappings provided.
    # <p>
    # Stability: Part of the DBAPI 2.0 specification.
    def executemany(self, operation, param_sets):
        self._row_count = -1

        try:
            self._c.begin()
        except AttributeError:
            if self._c is None:
                raise InterfaceError("Cursor closed")
            else:
                raise exc_info()[1]

        if not self._c.use_cache:
            self._c.statement_cache.clear()

        for parameters in param_sets:
            self._stmt = self._get_ps(operation, parameters)
            self._stmt.execute(parameters)
            if self._stmt.row_count == -1:
                self._row_count = -1
            elif self._row_count == -1:
                self._row_count = self._stmt.row_count
            else:
                self._row_count += self._stmt.row_count

    def copy_from(self, fileobj, table=None, sep='\t', null=None, query=None):
        if query is None:
            if table is None:
                raise CopyQueryOrTableRequiredError()
            query = "COPY %s FROM stdout DELIMITER '%s'" % (table, sep)
            if null is not None:
                query += " NULL '%s'" % (null,)
        self.copy_execute(fileobj, query)

    def copy_to(self, fileobj, table=None, sep='\t', null=None, query=None):
        if query is None:
            if table is None:
                raise CopyQueryOrTableRequiredError()
            query = "COPY %s TO stdout DELIMITER '%s'" % (table, sep)
            if null is not None:
                query += " NULL '%s'" % (null,)
        self.copy_execute(fileobj, query)

    def _get_ps(self, operation, vals):
        if pg8000.paramstyle in ('numeric', 'qmark', 'format'):
            args = vals
        else:
            args = tuple(vals[k] for k in sorted(vals.keys()))

        key = tuple(oid for oid, x, y in self._c.make_params(args)), operation

        try:
            return self._c.statement_cache[key]
        except KeyError:
            ps = PreparedStatement(self._c, operation, vals)
            self._c.statement_cache[key] = ps
            return ps

    @require_open_cursor
    def copy_execute(self, fileobj, query):
        self.execute(query, stream=fileobj)

    ##
    # Fetch the next row of a query result set, returning a single sequence, or
    # None when no more data is available.
    # <p>
    # Stability: Part of the DBAPI 2.0 specification.
    def fetchone(self):
        try:
            return next(self._stmt)
        except StopIteration:
            return None
        except TypeError:
            raise ProgrammingError("attempting to use unexecuted cursor")
        except AttributeError:
            raise ProgrammingError("attempting to use unexecuted cursor")

    ##
    # Fetch the next set of rows of a query result, returning a sequence of
    # sequences.  An empty sequence is returned when no more rows are
    # available.
    # <p>
    # Stability: Part of the DBAPI 2.0 specification.
    # @param size   The number of rows to fetch when called.  If not provided,
    #               the arraysize property value is used instead.
    if IS_JYTHON:
        def fetchmany(self, num=None):
            if self._stmt is None:
                raise ProgrammingError("attempting to use unexecuted cursor")
            else:
                try:
                    return tuple(
                        islice(self, self.arraysize if num is None else num))
                except TypeError:
                    raise ProgrammingError(
                        "attempting to use unexecuted cursor")
    else:
        def fetchmany(self, num=None):
            try:
                return tuple(
                    islice(self, self.arraysize if num is None else num))
            except TypeError:
                raise ProgrammingError("attempting to use unexecuted cursor")

    ##
    # Fetch all remaining rows of a query result, returning them as a sequence
    # of sequences.
    # <p>
    # Stability: Part of the DBAPI 2.0 specification.
    if IS_JYTHON:
        def fetchall(self):
            if self._stmt is None:
                raise ProgrammingError("attempting to use unexecuted cursor")
            else:
                return tuple(self)
    else:
        def fetchall(self):
            try:
                return tuple(self)
            except TypeError:
                raise ProgrammingError("attempting to use unexecuted cursor")

    ##
    # Close the cursor.
    # <p>
    # Stability: Part of the DBAPI 2.0 specification.
    @require_open_cursor
    def close(self):
        if self._stmt is not None and not self._c.use_cache:
            self._stmt.close()
            self._stmt = None
        self._c = None

    def __iter__(self):
        return self._stmt

    def setinputsizes(self, sizes):
        pass

    def setoutputsize(self, size, column=None):
        pass


# Message codes
NOTICE_RESPONSE = b("N")
AUTHENTICATION_REQUEST = b("R")
PARAMETER_STATUS = b("S")
BACKEND_KEY_DATA = b("K")
READY_FOR_QUERY = b("Z")
ROW_DESCRIPTION = b("T")
ERROR_RESPONSE = b("E")
DATA_ROW = b("D")
COMMAND_COMPLETE = b("C")
PARSE_COMPLETE = b("1")
BIND_COMPLETE = b("2")
CLOSE_COMPLETE = b("3")
PORTAL_SUSPENDED = b("s")
NO_DATA = b("n")
PARAMETER_DESCRIPTION = b("t")
NOTIFICATION_RESPONSE = b("A")
COPY_DONE = b("c")
COPY_DATA = b("d")
COPY_IN_RESPONSE = b("G")
COPY_OUT_RESPONSE = b("H")

BIND = b("B")
PARSE = b("P")
EXECUTE = b("E")
FLUSH = b('H')
SYNC = b('S')
PASSWORD = b('p')
DESCRIBE = b('D')
TERMINATE = b('X')
CLOSE = b('C')

FLUSH_MSG = FLUSH + i_pack(4)
SYNC_MSG = SYNC + i_pack(4)
TERMINATE_MSG = TERMINATE + i_pack(4)
COPY_DONE_MSG = COPY_DONE + i_pack(4)

# DESCRIBE constants
STATEMENT = b('S')
PORTAL = b('P')

# ErrorResponse codes
RESPONSE_SEVERITY = b("S")  # always present
RESPONSE_CODE = b("C")  # always present
RESPONSE_MSG = b("M")  # always present
RESPONSE_DETAIL = b("D")
RESPONSE_HINT = b("H")
RESPONSE_POSITION = b("P")
RESPONSE__POSITION = b("p")
RESPONSE__QUERY = b("q")
RESPONSE_WHERE = b("W")
RESPONSE_FILE = b("F")
RESPONSE_LINE = b("L")
RESPONSE_ROUTINE = b("R")

IDLE = b("I")
IDLE_IN_TRANSACTION = b("T")
IDLE_IN_FAILED_TRANSACTION = b("E")


# Byte1('N') - Identifier
# Int32 - Message length
# Any number of these, followed by a zero byte:
#   Byte1 - code identifying the field type (see responseKeys)
#   String - field value
def data_into_dict(data):
    return dict((s[0:1], s[1:]) for s in data.split(NULL_BYTE))

arr_trans = dict(zip(map(ord, u("[] 'u")), list(u('{}')) + [None] * 3))


##
# This class represents a connection to a PostgreSQL database.
# <p>
# The database connection is derived from the {@link #Cursor Cursor} class,
# which provides a default cursor for running queries.  It also provides
# transaction control via the 'commit', and 'rollback' methods.
# <p>
# As of v1.01, instances of this class are thread-safe.  See {@link
# PreparedStatement PreparedStatement} for more information.
# <p>
# Stability: Added in v1.00, stability guaranteed for v1.xx.
#
# @param user   The username to connect to the PostgreSQL server with.  This
# parameter is required.
#
# @keyparam host   The hostname of the PostgreSQL server to connect with.
# Providing this parameter is necessary for TCP/IP connections.  One of either
# host, or unix_sock, must be provided.
#
# @keyparam unix_sock   The path to the UNIX socket to access the database
# through, for example, '/tmp/.s.PGSQL.5432'.  One of either unix_sock or host
# must be provided.  The port parameter will have no affect if unix_sock is
# provided.
#
# @keyparam port   The TCP/IP port of the PostgreSQL server instance.  This
# parameter defaults to 5432, the registered and common port of PostgreSQL
# TCP/IP servers.
#
# @keyparam database   The name of the database instance to connect with.  This
# parameter is optional, if omitted the PostgreSQL server will assume the
# database name is the same as the username.
#
# @keyparam password   The user password to connect to the server with.  This
# parameter is optional.  If omitted, and the database server requests password
# based authentication, the connection will fail.  On the other hand, if this
# parameter is provided and the database does not request password
# authentication, then the password will not be used.
#
# @keyparam socket_timeout  Socket connect timeout measured in seconds.
# Defaults to 60 seconds.
#
# @keyparam ssl     Use SSL encryption for TCP/IP socket.  Defaults to False.

##
# The class of object returned by the {@link #connect connect method}.
class Connection(object):
    # DBAPI Extension: supply exceptions as attributes on the connection
    Warning = property(lambda self: self._getError(Warning))
    Error = property(lambda self: self._getError(Error))
    InterfaceError = property(lambda self: self._getError(InterfaceError))
    DatabaseError = property(lambda self: self._getError(DatabaseError))
    OperationalError = property(lambda self: self._getError(OperationalError))
    IntegrityError = property(lambda self: self._getError(IntegrityError))
    InternalError = property(lambda self: self._getError(InternalError))
    ProgrammingError = property(lambda self: self._getError(ProgrammingError))
    NotSupportedError = property(
        lambda self: self._getError(NotSupportedError))

    def _getError(self, error):
        warn(
            "DB-API extension connection.%s used" %
            error.__name__, stacklevel=3)
        return error

    def __init__(
            self, user, host, unix_sock, port, database, password,
            socket_timeout, ssl, use_cache):
        self._client_encoding = "ascii"
        self._commands_with_count = (
            b("INSERT"), b("DELETE"), b("UPDATE"), b("MOVE"),
            b("FETCH"), b("COPY"), b("SELECT"))
        self._sock_lock = threading.Lock()
        self.user = user
        self.password = password
        self.autocommit = False

        self.statement_cache = {}

        self.statement_number_lock = threading.Lock()
        self.statement_number = 0

        self.portal_number_lock = threading.Lock()
        self.portal_number = 0
        self.use_cache = use_cache

        try:
            if unix_sock is None and host is not None:
                self._usock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            elif unix_sock is not None:
                if not hasattr(socket, "AF_UNIX"):
                    raise InterfaceError(
                        "attempt to connect to unix socket on unsupported "
                        "platform")
                self._usock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            else:
                raise ProgrammingError(
                    "one of host or unix_sock must be provided")
            if unix_sock is None and host is not None:
                self._usock.connect((host, port))
            elif unix_sock is not None:
                self._usock.connect(unix_sock)

            if ssl:
                try:
                    self._sock_lock.acquire()
                    import ssl as sslmodule
                    # Int32(8) - Message length, including self.
                    # Int32(80877103) - The SSL request code.
                    self._usock.sendall(ii_pack(8, 80877103))
                    resp = self._usock.recv(1)
                    if resp == b('S'):
                        self._usock = sslmodule.wrap_socket(self._usock)
                    else:
                        raise InterfaceError("Server refuses SSL")
                except ImportError:
                    raise InterfaceError(
                        "SSL required but ssl module not available in "
                        "this python installation")
                finally:
                    self._sock_lock.release()

            # settimeout causes ssl failure, on windows.  Python bug 1462352.
            self._usock.settimeout(socket_timeout)
            self._sock = self._usock.makefile(mode="rwb")
        except socket.error:
            self._usock.close()
            raise InterfaceError("communication error", exc_info()[1])
        self._flush = self._sock.flush
        self._read = self._sock.read

        if PRE_26:
            self._write = self._sock.writelines
        else:
            self._write = self._sock.write
        self._backend_key_data = None

        ##
        # An event handler that is fired when the database server issues a
        # notice.
        # The value of this property is a util.MulticastDelegate. A callback
        # can be added by using connection.NotificationReceived += SomeMethod.
        # The method will be called with a single argument, an object that has
        # properties: severity, code, msg, and possibly others (detail, hint,
        # position, where, file, line, and routine). Callbacks can be removed
        # with the -= operator.
        # <p>
        # Stability: Added in v1.03, stability guaranteed for v1.xx.
        self.NoticeReceived = pg8000.util.MulticastDelegate()

        ##
        # An event handler that is fired when a runtime configuration option is
        # changed on the server.  The value of this property is a
        # util.MulticastDelegate.  A callback can be added by using
        # connection.NotificationReceived += SomeMethod. Callbacks can be
        # removed with the -= operator. The method will be called with a single
        # argument, an object that has properties "key" and "value".
        # <p>
        # Stability: Added in v1.03, stability guaranteed for v1.xx.
        self.ParameterStatusReceived = pg8000.util.MulticastDelegate()

        ##
        # An event handler that is fired when NOTIFY occurs for a notification
        # that has been LISTEN'd for.  The value of this property is a
        # util.MulticastDelegate.  A callback can be added by using
        # connection.NotificationReceived += SomeMethod. The method will be
        # called with a single argument, an object that has properties:
        # backend_pid, condition, and additional_info. Callbacks can be
        # removed with the -= operator.
        # <p>
        # Stability: Added in v1.03, stability guaranteed for v1.xx.
        self.NotificationReceived = pg8000.util.MulticastDelegate()

        self.ParameterStatusReceived += self.handle_PARAMETER_STATUS

        def text_out(v):
            return v.encode(self._client_encoding)

        def time_out(v):
            return v.isoformat().encode(self._client_encoding)

        def date_out(v):
            if v == datetime.date.max:
                return 'infinity'.encode(self._client_encoding)
            elif v == datetime.date.min:
                return '-infinity'.encode(self._client_encoding)
            else:
                return v.isoformat().encode(self._client_encoding)

        def unknown_out(v):
            return str(v).encode(self._client_encoding)

        trans_tab = dict(zip(map(ord, u('{}')), u('[]')))
        glbls = {'Decimal': Decimal}

        def array_in(data, idx, length):
            arr = []
            prev_c = None
            for c in data[idx:idx+length].decode(
                    self._client_encoding).translate(
                    trans_tab).replace(u('NULL'), u('None')):
                if c not in ('[', ']', ',', 'N') and prev_c in ('[', ','):
                    arr.extend("Decimal('")
                elif c in (']', ',') and prev_c not in ('[', ']', ',', 'e'):
                    arr.extend("')")

                arr.append(c)
                prev_c = c
            return eval(''.join(arr), glbls)

        def array_recv(data, idx, length):
            final_idx = idx + length
            dim, hasnull, typeoid = iii_unpack(data, idx)
            idx += 12

            # get type conversion method for typeoid
            conversion = self.pg_types[typeoid][1]

            # Read dimension info
            dim_lengths = []
            for i in range(dim):
                dim_lengths.append(ii_unpack(data, idx)[0])
                idx += 8

            # Read all array values
            values = []
            while idx < final_idx:
                element_len, = i_unpack(data, idx)
                idx += 4
                if element_len == -1:
                    values.append(None)
                else:
                    values.append(conversion(data, idx, element_len))
                    idx += element_len

            # at this point, {{1,2,3},{4,5,6}}::int[][] looks like
            # [1,2,3,4,5,6]. go through the dimensions and fix up the array
            # contents to match expected dimensions
            for length in reversed(dim_lengths[1:]):
                values = list(map(list, zip(*[iter(values)] * length)))
            return values

        def vector_in(data, idx, length):
            return eval('[' + data[idx:idx+length].decode(
                self._client_encoding).replace(' ', ',') + ']')

        if PY2:
            def text_in(data, offset, length):
                return unicode(  # noqa
                    data[offset: offset + length], self._client_encoding)

            def bool_recv(d, o, l):
                return d[o] == "\x01"

        else:
            def text_in(data, offset, length):
                return str(
                    data[offset: offset + length], self._client_encoding)

            def bool_recv(data, offset, length):
                return data[offset] == 1

        def time_in(data, offset, length):
            hour = int(data[offset:offset + 2])
            minute = int(data[offset + 3:offset + 5])
            sec = Decimal(
                data[offset + 6:offset + length].decode(self._client_encoding))
            return datetime.time(
                hour, minute, int(sec), int((sec - int(sec)) * 1000000))

        def date_in(data, offset, length):
            year_str = data[offset:offset + 4].decode(self._client_encoding)
            if year_str == 'infi':
                return datetime.date.max
            elif year_str == '-inf':
                return datetime.date.min
            else:
                return datetime.date(
                    int(year_str), int(data[offset + 5:offset + 7]),
                    int(data[offset + 8:offset + 10]))

        def numeric_in(data, offset, length):
            return Decimal(
                data[offset: offset + length].decode(self._client_encoding))

        def numeric_out(d):
            return str(d).encode(self._client_encoding)

        self.pg_types = defaultdict(
            lambda: (FC_TEXT, text_in), {
                16: (FC_BINARY, bool_recv),  # boolean
                17: (FC_BINARY, bytea_recv),  # bytea
                19: (FC_BINARY, text_in),  # name type
                20: (FC_BINARY, int8_recv),  # int8
                21: (FC_BINARY, int2_recv),  # int2
                22: (FC_TEXT, vector_in),  # int2vector
                23: (FC_BINARY, int4_recv),  # int4
                25: (FC_TEXT, text_in),  # TEXT type
                26: (FC_TEXT, int_in),  # oid
                28: (FC_TEXT, int_in),  # xid
                700: (FC_BINARY, float4_recv),  # float4
                701: (FC_BINARY, float8_recv),  # float8
                705: (FC_BINARY, text_in),  # unknown
                829: (FC_TEXT, text_in),  # MACADDR type
                1000: (FC_BINARY, array_recv),  # BOOL[]
                1003: (FC_BINARY, array_recv),  # NAME[]
                1005: (FC_BINARY, array_recv),  # INT2[]
                1007: (FC_BINARY, array_recv),  # INT4[]
                1009: (FC_BINARY, array_recv),  # TEXT[]
                1014: (FC_BINARY, array_recv),  # CHAR[]
                1015: (FC_BINARY, array_recv),  # VARCHAR[]
                1016: (FC_BINARY, array_recv),  # INT8[]
                1021: (FC_BINARY, array_recv),  # FLOAT4[]
                1022: (FC_BINARY, array_recv),  # FLOAT8[]
                1042: (FC_TEXT, text_in),  # CHAR type
                1043: (FC_TEXT, text_in),  # VARCHAR type
                1082: (FC_TEXT, date_in),  # date
                1083: (FC_TEXT, time_in),
                1114: (FC_BINARY, timestamp_recv_float),  # timestamp w/ tz
                1184: (FC_BINARY, timestamptz_recv_float),
                1186: (FC_BINARY, interval_recv_integer),
                1231: (FC_TEXT, array_in),  # NUMERIC[]
                1263: (FC_BINARY, array_recv),  # cstring[]
                1700: (FC_TEXT, numeric_in),  # NUMERIC
                2275: (FC_TEXT, text_in),  # cstring
                2950: (FC_BINARY, uuid_recv),  # uuid
            })

        self.py_types = {
            type(None): (-1, FC_BINARY, null_send),  # null
            bool: (16, FC_BINARY, bool_send),
            int: (705, FC_TEXT, unknown_out),
            float: (701, FC_BINARY, d_pack),  # float8
            str: (705, FC_TEXT, text_out),  # unknown
            datetime.date: (1082, FC_TEXT, date_out),  # date
            datetime.time: (1083, FC_TEXT, time_out),  # time
            1114: (1114, FC_BINARY, timestamp_send_integer),  # timestamp
            # timestamp w/ tz
            1184: (1184, FC_BINARY, timestamptz_send_integer),
            datetime.timedelta: (1186, FC_BINARY, interval_send_integer),
            Interval: (1186, FC_BINARY, interval_send_integer),
            Decimal: (1700, FC_TEXT, numeric_out),  # Decimal
            UUID: (2950, FC_BINARY, uuid_send),  # uuid
        }

        self.inspect_funcs = {
            datetime.datetime: self.inspect_datetime,
            list: self.array_inspect}

        if PY2:
            self.py_types[pg8000.Bytea] = (17, FC_BINARY, bytea_send)  # bytea
            self.py_types[text_type] = (705, FC_BINARY, text_out)  # unknown

            self.py_types[long] = (705, FC_TEXT, unknown_out)  # noqa
        else:
            self.py_types[bytes] = (17, FC_BINARY, bytea_send)  # bytea

        try:
            from ipaddress import (
                ip_address, IPv4Address, IPv6Address, ip_network, IPv4Network,
                IPv6Network)

            def inet_out(v):
                return str(v).encode(self._client_encoding)

            def inet_in(data, offset, length):
                inet_str = data[offset: offset + length].decode(
                    self._client_encoding)
                if '/' in inet_str:
                    return ip_network(inet_str, False)
                else:
                    return ip_address(inet_str)

            self.py_types[IPv4Address] = (869, FC_TEXT, inet_out)  # inet
            self.py_types[IPv6Address] = (869, FC_TEXT, inet_out)  # inet
            self.py_types[IPv4Network] = (869, FC_TEXT, inet_out)  # inet
            self.py_types[IPv6Network] = (869, FC_TEXT, inet_out)  # inet
            self.pg_types[869] = (FC_TEXT, inet_in)  # inet
        except ImportError:
            pass

        self.message_types = {
            NOTICE_RESPONSE: self.handle_NOTICE_RESPONSE,
            AUTHENTICATION_REQUEST: self.handle_AUTHENTICATION_REQUEST,
            PARAMETER_STATUS: self.handle_PARAMETER_STATUS,
            BACKEND_KEY_DATA: self.handle_BACKEND_KEY_DATA,
            READY_FOR_QUERY: self.handle_READY_FOR_QUERY,
            ROW_DESCRIPTION: self.handle_ROW_DESCRIPTION,
            ERROR_RESPONSE: self.handle_ERROR_RESPONSE,
            DATA_ROW: self.handle_DATA_ROW,
            COMMAND_COMPLETE: self.handle_COMMAND_COMPLETE,
            PARSE_COMPLETE: self.handle_PARSE_COMPLETE,
            BIND_COMPLETE: self.handle_BIND_COMPLETE,
            CLOSE_COMPLETE: self.handle_CLOSE_COMPLETE,
            PORTAL_SUSPENDED: self.handle_PORTAL_SUSPENDED,
            NO_DATA: self.handle_NO_DATA,
            PARAMETER_DESCRIPTION: self.handle_PARAMETER_DESCRIPTION,
            NOTIFICATION_RESPONSE: self.handle_NOTIFICATION_RESPONSE,
            COPY_DONE: self.handle_COPY_DONE,
            COPY_DATA: self.handle_COPY_DATA,
            COPY_IN_RESPONSE: self.handle_COPY_IN_RESPONSE,
            COPY_OUT_RESPONSE: self.handle_COPY_OUT_RESPONSE}

        # Int32 - Message length, including self.
        # Int32(196608) - Protocol version number.  Version 3.0.
        # Any number of key/value pairs, terminated by a zero byte:
        #   String - A parameter name (user, database, or options)
        #   String - Parameter value
        protocol = 196608
        val = bytearray(i_pack(protocol) + b("user\x00"))
        val.extend(user.encode("ascii") + NULL_BYTE)
        if database is not None:
            val.extend(
                b("database\x00") + database.encode("ascii") + NULL_BYTE)
        val.append(0)
        self._write(i_pack(len(val) + 4))
        self._write(val)
        self._flush()

        try:
            try:
                self._sock_lock.acquire()
                self.handle_messages()
            finally:
                self._sock_lock.release()
        except:
            self.close()
            raise exc_info()[1]

        self._begin = PreparedStatement(self, "BEGIN TRANSACTION", ())
        self._commit = PreparedStatement(self, "COMMIT TRANSACTION", ())
        self._rollback = PreparedStatement(self, "ROLLBACK TRANSACTION", ())
        self.in_transaction = False
        self.notifies = []
        self.notifies_lock = threading.Lock()

    def handle_ERROR_RESPONSE(self, data, ps):
        msg_dict = data_into_dict(data)
        if msg_dict[RESPONSE_CODE] == "28000":
            raise InterfaceError("md5 password authentication failed")
        else:
            raise ProgrammingError(
                msg_dict[RESPONSE_SEVERITY], msg_dict[RESPONSE_CODE],
                msg_dict[RESPONSE_MSG])

    def handle_CLOSE_COMPLETE(self, data, ps):
        pass

    def handle_PARSE_COMPLETE(self, data, ps):
        # Byte1('1') - Identifier.
        # Int32(4) - Message length, including self.
        pass

    def handle_BIND_COMPLETE(self, data, ps):
        pass

    def handle_PORTAL_SUSPENDED(self, data, ps):
        ps.portal_suspended = True

    def handle_PARAMETER_DESCRIPTION(self, data, ps):
        # Well, we don't really care -- we're going to send whatever we
        # want and let the database deal with it.  But thanks anyways!

        # count = h_unpack(data)[0]
        # type_oids = unpack_from("!" + "i" * count, data, 2)
        pass

    def handle_COPY_DONE(self, data, ps):
        self._copy_done = True

    def handle_COPY_OUT_RESPONSE(self, data, ps):
        # Int8(1) - 0 textual, 1 binary
        # Int16(2) - Number of columns
        # Int16(N) - Format codes for each column (0 text, 1 binary)

        is_binary, num_cols = bh_unpack(data)
        # column_formats = unpack_from('!' + 'h' * num_cols, data, 3)
        if ps.stream is None:
            raise CopyQueryWithoutStreamError()

    def handle_COPY_DATA(self, data, ps):
        ps.stream.write(data)

    def handle_COPY_IN_RESPONSE(self, data, ps):
        # Int16(2) - Number of columns
        # Int16(N) - Format codes for each column (0 text, 1 binary)
        is_binary, num_cols = bh_unpack(data)
        # column_formats = unpack_from('!' + 'h' * num_cols, data, 3)
        assert self._sock_lock.locked()
        if ps.stream is None:
            raise CopyQueryWithoutStreamError()

        if PY2:
            while True:
                data = ps.stream.read(8192)
                if not data:
                    break
                self._write(COPY_DATA + i_pack(len(data) + 4))
                self._write(data)
                self._flush()
        else:
            bffr = bytearray(8192)
            while True:
                bytes_read = ps.stream.readinto(bffr)
                if bytes_read == 0:
                    break
                self._write(COPY_DATA + i_pack(bytes_read + 4))
                self._write(bffr[:bytes_read])
                self._flush()

        # Send CopyDone
        # Byte1('c') - Identifier.
        # Int32(4) - Message length, including self.
        self._write(COPY_DONE_MSG)
        self._write(SYNC_MSG)
        self._flush()

    def handle_NOTIFICATION_RESPONSE(self, data, ps):
        self.NotificationReceived(data)
        ##
        # A message sent if this connection receives a NOTIFY that it was
        # LISTENing for.
        # <p>
        # Stability: Added in pg8000 v1.03.  When limited to accessing
        # properties from a notification event dispatch, stability is
        # guaranteed for v1.xx.
        backend_pid = i_unpack(data)[0]
        idx = 4
        null = data.find(NULL_BYTE, idx) - idx
        condition = data[idx:idx + null].decode("ascii")
        idx += null + 1
        null = data.find(NULL_BYTE, idx) - idx
        # additional_info = data[idx:idx + null]

        # psycopg2 compatible notification interface
        try:
            self.notifies_lock.acquire()
            self.notifies.append((backend_pid, condition))
        finally:
            self.notifies_lock.release()

    ##
    # Creates a {@link #CursorWrapper CursorWrapper} object bound to this
    # connection.
    # <p>
    # Stability: Part of the DBAPI 2.0 specification.
    def cursor(self):
        return Cursor(self)

    ##
    # Commits the current database transaction.
    # <p>
    # Stability: Part of the DBAPI 2.0 specification.
    def commit(self):
        # There's a threading bug here.  If a query is sent after the
        # commit, but before the begin, it will be executed immediately
        # without a surrounding transaction.  Like all threading bugs -- it
        # sounds unlikely, until it happens every time in one
        # application...  however, to fix this, we need to lock the
        # database connection entirely, so that no cursors can execute
        # statements on other threads.  Support for that type of lock will
        # be done later.
        self._commit.execute(())

    ##
    # Rolls back the current database transaction.
    # <p>
    # Stability: Part of the DBAPI 2.0 specification.
    def rollback(self):
        # see bug description in commit.
        self._rollback.execute(())

    ##
    # Closes the database connection.
    # <p>
    # Stability: Part of the DBAPI 2.0 specification.
    def close(self):
        try:
            self._sock_lock.acquire()
            # Byte1('X') - Identifies the message as a terminate message.
            # Int32(4) - Message length, including self.
            self._write(TERMINATE_MSG)
            self._flush()
            self._sock.close()
            self._usock.close()
            self._sock = None
        except AttributeError:
            raise pg8000.InterfaceError("Connection is closed.")
        except ValueError:
            raise pg8000.InterfaceError("Connection is closed.")
        finally:
            self._sock_lock.release()

    ##
    # Begins a new transaction.
    # <p>
    # Stability: Added in v1.00, stability guaranteed for v1.xx.
    def begin(self):
        if not self.in_transaction and not self.autocommit:
            self._begin.execute(())

    def handle_AUTHENTICATION_REQUEST(self, data, ps):
        assert self._sock_lock.locked()
        # Int32 -   An authentication code that represents different
        #           authentication messages:
        #               0 = AuthenticationOk
        #               5 = MD5 pwd
        #               2 = Kerberos v5 (not supported by pg8000)
        #               3 = Cleartext pwd (not supported by pg8000)
        #               4 = crypt() pwd (not supported by pg8000)
        #               6 = SCM credential (not supported by pg8000)
        #               7 = GSSAPI (not supported by pg8000)
        #               8 = GSSAPI data (not supported by pg8000)
        #               9 = SSPI (not supported by pg8000)
        # Some authentication messages have additional data following the
        # authentication code.  That data is documented in the appropriate
        # class.
        auth_code = i_unpack(data)[0]
        if auth_code == 0:
            pass
        elif auth_code == 5:
            ##
            # A message representing the backend requesting an MD5 hashed
            # password response.  The response will be sent as
            # md5(md5(pwd + login) + salt).

            # Additional message data:
            #  Byte4 - Hash salt.
            salt = b("").join(cccc_unpack(data, 4))
            if self.password is None:
                raise InterfaceError(
                    "server requesting MD5 password authentication, but no "
                    "password was provided")
            pwd = b("md5") + md5(
                md5(
                    self.password.encode("ascii") +
                    self.user.encode("ascii")).hexdigest().encode("ascii") +
                salt).hexdigest().encode("ascii")
            # Byte1('p') - Identifies the message as a password message.
            # Int32 - Message length including self.
            # String - The password.  Password may be encrypted.
            self._send_message(PASSWORD, pwd + NULL_BYTE)
            self._flush()

        elif auth_code in (2, 3, 4, 6, 7, 8, 9):
            raise NotSupportedError(
                "authentication method " + auth_code + " not supported")
        else:
            raise InternalError(
                "Authentication method " + auth_code + " not recognized")

    def handle_READY_FOR_QUERY(self, data, ps):
        # Byte1 -   Status indicator.
        self.in_transaction = data != IDLE

    def handle_BACKEND_KEY_DATA(self, data, ps):
        self._backend_key_data = data

    def inspect_datetime(self, value):
        if value.tzinfo is None:
            return self.py_types[1114]  # timestamp
        else:
            return self.py_types[1184]  # send as timestamptz

    def make_params(self, values):
        params = []
        for value in values:
            typ = type(value)
            try:
                params.append(self.py_types[typ])
            except KeyError:
                try:
                    params.append(self.inspect_funcs[typ](value))
                except KeyError:
                    raise NotSupportedError(
                        "type " + str(exc_info()[1]) +
                        "not mapped to pg type")
        return params

    def handle_ROW_DESCRIPTION(self, data, ps):
        count = h_unpack(data)[0]
        idx = 2
        for i in range(count):
            field = {'name': data[idx:data.find(NULL_BYTE, idx)]}
            idx += len(field['name']) + 1
            field.update(
                dict(zip((
                    "table_oid", "column_attrnum", "type_oid",
                    "type_size", "type_modifier", "format"),
                    ihihih_unpack(data, idx))))
            idx += 18
            ps.row_desc.append(field)
            try:
                field['pg8000_fc'], field['func'] = self.pg_types[
                    field['type_oid']]
            except KeyError:
                raise NotSupportedError(
                    "type oid " + exc_info()[1] + " not supported")

    def parse(self, ps, statement):
        try:
            self._sock_lock.acquire()
            # Byte1('P') - Identifies the message as a Parse command.
            # Int32 -   Message length, including self.
            # String -  Prepared statement name. An empty string selects the
            #           unnamed prepared statement.
            # String -  The query string.
            # Int16 -   Number of parameter data types specified (can be zero).
            # For each parameter:
            #   Int32 - The OID of the parameter data type.
            val = bytearray(ps.statement_name_bin)
            val.extend(statement.encode(self._client_encoding) + NULL_BYTE)
            val.extend(h_pack(len(ps.params)))
            for oid, fc, send_func in ps.params:
                # Parse message doesn't seem to handle the -1 type_oid for NULL
                # values that other messages handle.  So we'll provide type_oid
                # 705, the PG "unknown" type.
                val.extend(i_pack(705 if oid == -1 else oid))

            # Byte1('D') - Identifies the message as a describe command.
            # Int32 - Message length, including self.
            # Byte1 - 'S' for prepared statement, 'P' for portal.
            # String - The name of the item to describe.
            self._send_message(PARSE, val)
            self._send_message(DESCRIBE, STATEMENT + ps.statement_name_bin)
            self._write(SYNC_MSG)
            self._flush()
            self.handle_messages(ps)
        finally:
            self._sock_lock.release()

    def bind(self, ps, values):
        try:
            self._sock_lock.acquire()

            # Byte1('B') - Identifies the Bind command.
            # Int32 - Message length, including self.
            # String - Name of the destination portal.
            # String - Name of the source prepared statement.
            # Int16 - Number of parameter format codes.
            # For each parameter format code:
            #   Int16 - The parameter format code.
            # Int16 - Number of parameter values.
            # For each parameter value:
            #   Int32 - The length of the parameter value, in bytes, not
            #           including this length.  -1 indicates a NULL parameter
            #           value, in which no value bytes follow.
            #   Byte[n] - Value of the parameter.
            # Int16 - The number of result-column format codes.
            # For each result-column format code:
            #   Int16 - The format code.
            retval = bytearray(ps.portal_name_bin + ps.bind_1)
            for value, send_func in zip(values, ps.param_funcs):
                if value is None:
                    val = NULL
                else:
                    val = send_func(value)
                    retval.extend(i_pack(len(val)))
                retval.extend(val)
            retval.extend(ps.bind_2)

            self._send_message(BIND, retval)
            self.send_EXECUTE(ps)
            self._write(SYNC_MSG)
            self._flush()
            self.handle_messages(ps)
        except AttributeError:
            raise pg8000.InterfaceError("Connection is closed.")
        finally:
            self._sock_lock.release()

    def _send_message(self, code, data):
        try:
            self._write(code)
            self._write(i_pack(len(data) + 4))
            self._write(data)
            self._write(FLUSH_MSG)
        except ValueError:
            if str(exc_info()[1]) == "write to closed file":
                raise pg8000.InterfaceError("Connection is closed.")
            else:
                raise exc_info()[1]
        except AttributeError:
            raise pg8000.InterfaceError("Connection is closed.")

    def send_EXECUTE(self, ps):
        # Byte1('E') - Identifies the message as an execute message.
        # Int32 -   Message length, including self.
        # String -  The name of the portal to execute.
        # Int32 -   Maximum number of rows to return, if portal
        #           contains a query # that returns rows.
        #           0 = no limit.
        ps.cmd = None
        ps.portal_suspended = False
        self._send_message(
            EXECUTE, ps.portal_name_bin + ps.row_cache_size_bin)

    def handle_NO_DATA(self, msg, ps):
        pass

    def handle_COMMAND_COMPLETE(self, data, ps):
        ps.cmd = {}
        data = data[:-1]
        values = data.split(b(" "))
        if values[0] in self._commands_with_count:
            ps.cmd['command'] = values[0]
            row_count = int(values[-1])
            if ps.row_count == -1:
                ps.row_count = row_count
            else:
                ps.row_count += row_count
            if values[0] == b("INSERT"):
                ps.cmd['oid'] = int(values[1])
        else:
            ps.cmd['command'] = data

    def handle_DATA_ROW(self, data, ps):
        data_idx = 2
        row = []
        for func in ps.input_funcs:
            vlen = i_unpack(data, data_idx)[0]
            data_idx += 4
            if vlen == -1:
                row.append(None)
            else:
                row.append(func(data, data_idx, vlen))
                data_idx += vlen
        ps._cached_rows.append(row)

    def handle_messages(self, ps=None):
        message_code = None
        error = None

        while message_code != READY_FOR_QUERY:
            message_code, data_len = ci_unpack(self._read(5))
            try:
                self.message_types[message_code](self._read(data_len - 4), ps)
            except KeyError:
                raise InternalError(
                    "Unrecognised message code " + message_code)
            except pg8000.errors.Error:
                e = exc_info()[1]
                if ps is None:
                    raise e
                else:
                    error = e
        if error is not None:
            raise error

    # Byte1('C') - Identifies the message as a close command.
    # Int32 - Message length, including self.
    # Byte1 - 'S' for prepared statement, 'P' for portal.
    # String - The name of the item to close.
    def close_statement(self, ps):
        try:
            self._sock_lock.acquire()
            self._send_message(CLOSE, STATEMENT + ps.statement_name_bin)
            self._write(SYNC_MSG)
            self._flush()
            self.handle_messages(ps)
        finally:
            self._sock_lock.release()

    def handle_NOTICE_RESPONSE(self, data, ps):
        resp = data_into_dict(data)
        self.NoticeReceived(resp)

    def handle_PARAMETER_STATUS(self, data, ps):
        pos = data.find(NULL_BYTE)
        key, value = data[:pos], data[pos + 1:-1]
        if key == b("client_encoding"):
            encoding = value.decode("ascii").lower()
            self._client_encoding = pg_to_py_encodings.get(encoding, encoding)

        elif key == b("integer_datetimes"):
            if value == b('on'):

                self.py_types[1114] = (1114, FC_BINARY, timestamp_send_integer)
                self.pg_types[1114] = (FC_BINARY, timestamp_recv_integer)

                self.py_types[1184] = (
                    1184, FC_BINARY, timestamptz_send_integer)
                self.pg_types[1184] = (FC_BINARY, timestamptz_recv_integer)

                self.py_types[Interval] = (
                    1186, FC_BINARY, interval_send_integer)
                self.py_types[datetime.timedelta] = (
                    1186, FC_BINARY, interval_send_integer)
                self.pg_types[1186] = (FC_BINARY, interval_recv_integer)
            else:
                self.py_types[1114] = (1114, FC_BINARY, timestamp_send_float)
                self.pg_types[1114] = (FC_BINARY, timestamp_recv_float)
                self.py_types[1184] = (1184, FC_BINARY, timestamptz_send_float)
                self.pg_types[1184] = (FC_BINARY, timestamptz_recv_float)

                self.py_types[Interval] = (
                    1186, FC_BINARY, interval_send_float)
                self.py_types[datetime.timedelta] = (
                    1186, FC_BINARY, interval_send_float)
                self.pg_types[1186] = (FC_BINARY, interval_recv_float)

        elif key == b("server_version"):
            self._server_version = value.decode("ascii")
            if self._server_version.startswith("8"):
                self._commands_with_count = (
                    b("INSERT"), b("DELETE"), b("UPDATE"), b("MOVE"),
                    b("FETCH"), b("COPY"))

    def array_inspect(self, value):
        # Check if array has any values.  If not, we can't determine the proper
        # array typeoid.
        first_element = array_find_first_element(value)
        if first_element is None:
            raise ArrayContentEmptyError("array has no values")

        # supported array output
        typ = type(first_element)

        if issubclass(typ, integer_types):
            # special int array support -- send as smallest possible array type
            typ = integer_types
            int2_ok, int4_ok, int8_ok = True, True, True
            for v in array_flatten(value):
                if v is None:
                    continue
                if min_int2 < v < max_int2:
                    continue
                int2_ok = False
                if min_int4 < v < max_int4:
                    continue
                int4_ok = False
                if min_int8 < v < max_int8:
                    continue
                int8_ok = False
            if int2_ok:
                array_typeoid = 1005  # INT2[]
                oid, fc, send_func = (21, FC_BINARY, h_pack)
            elif int4_ok:
                array_typeoid = 1007  # INT4[]
                oid, fc, send_func = (23, FC_BINARY, i_pack)
            elif int8_ok:
                array_typeoid = 1016  # INT8[]
                oid, fc, send_func = (20, FC_BINARY, q_pack)
            else:
                raise ArrayContentNotSupportedError(
                    "numeric not supported as array contents")
        elif typ is str:
            oid, fc, send_func = (25, FC_BINARY, self.py_types[str][2])
            array_typeoid = pg_array_types[oid]
        else:
            try:
                oid, fc, send_func = self.make_params((first_element,))[0]
                array_typeoid = pg_array_types[oid]
            except KeyError:
                raise ArrayContentNotSupportedError(
                    "type " + str(typ) + " not supported as array contents")
            except NotSupportedError:
                raise ArrayContentNotSupportedError(
                    "type " + str(typ) + " not supported as array contents")

        if fc == FC_BINARY:
            def send_array(arr):
                # check for homogenous array
                for a, i, v in walk_array(arr):
                    if not isinstance(v, (typ, type(None))):
                        raise ArrayContentNotHomogenousError(
                            "not all array elements are of type " + str(typ))

                # check that all array dimensions are consistent
                array_check_dimensions(arr)

                has_null = array_has_null(arr)
                dim_lengths = array_dim_lengths(arr)
                data = bytearray(iii_pack(len(dim_lengths), has_null, oid))
                for i in dim_lengths:
                    data.extend(ii_pack(i, 1))
                for v in array_flatten(arr):
                    if v is None:
                        data += i_pack(-1)
                    else:
                        inner_data = send_func(v)
                        data += i_pack(len(inner_data))
                        data += inner_data
                return data
        else:
            def send_array(arr):
                for a, i, v in walk_array(arr):
                    if not isinstance(v, (typ, type(None))):
                        raise ArrayContentNotHomogenousError(
                            "not all array elements are of type " + str(typ))
                array_check_dimensions(arr)
                ar = deepcopy(arr)
                for a, i, v in walk_array(ar):
                    if v is None:
                        a[i] = 'NULL'
                    else:
                        a[i] = send_func(v).decode('ascii')

                return u(str(ar)).translate(arr_trans).encode('ascii')
        return (array_typeoid, fc, send_array)


# pg element typeoid -> pg array typeoid
pg_array_types = {
    701: 1022,
    16: 1000,
    25: 1009,      # TEXT[]
    1700: 1231,  # NUMERIC[]
}


# PostgreSQL encodings:
#   http://www.postgresql.org/docs/8.3/interactive/multibyte.html
# Python encodings:
#   http://www.python.org/doc/2.4/lib/standard-encodings.html
#
# Commented out encodings don't require a name change between PostgreSQL and
# Python.  If the py side is None, then the encoding isn't supported.
pg_to_py_encodings = {
    # Not supported:
    "mule_internal": None,
    "euc_tw": None,

    # Name fine as-is:
    # "euc_jp",
    # "euc_jis_2004",
    # "euc_kr",
    # "gb18030",
    # "gbk",
    # "johab",
    # "sjis",
    # "shift_jis_2004",
    # "uhc",
    # "utf8",

    # Different name:
    "euc_cn": "gb2312",
    "iso_8859_5": "is8859_5",
    "iso_8859_6": "is8859_6",
    "iso_8859_7": "is8859_7",
    "iso_8859_8": "is8859_8",
    "koi8": "koi8_r",
    "latin1": "iso8859-1",
    "latin2": "iso8859_2",
    "latin3": "iso8859_3",
    "latin4": "iso8859_4",
    "latin5": "iso8859_9",
    "latin6": "iso8859_10",
    "latin7": "iso8859_13",
    "latin8": "iso8859_14",
    "latin9": "iso8859_15",
    "sql_ascii": "ascii",
    "win866": "cp886",
    "win874": "cp874",
    "win1250": "cp1250",
    "win1251": "cp1251",
    "win1252": "cp1252",
    "win1253": "cp1253",
    "win1254": "cp1254",
    "win1255": "cp1255",
    "win1256": "cp1256",
    "win1257": "cp1257",
    "win1258": "cp1258",
    "unicode": "utf-8",  # Needed for Amazon Redshift
}


def walk_array(arr):
    for i, v in enumerate(arr):
        if isinstance(v, list):
            for a, i2, v2 in walk_array(v):
                yield a, i2, v2
        else:
            yield arr, i, v


def array_find_first_element(arr):
    for v in array_flatten(arr):
        if v is not None:
            return v
    return None


def array_flatten(arr):
    for v in arr:
        if isinstance(v, list):
            for v2 in array_flatten(v):
                yield v2
        else:
            yield v


def array_check_dimensions(arr):
    v0 = arr[0]
    if isinstance(v0, list):
        req_len = len(v0)
        req_inner_lengths = array_check_dimensions(v0)
        for v in arr:
            inner_lengths = array_check_dimensions(v)
            if len(v) != req_len or inner_lengths != req_inner_lengths:
                raise ArrayDimensionsNotConsistentError(
                    "array dimensions not consistent")
        retval = [req_len]
        retval.extend(req_inner_lengths)
        return retval
    else:
        # make sure nothing else at this level is a list
        for v in arr:
            if isinstance(v, list):
                raise ArrayDimensionsNotConsistentError(
                    "array dimensions not consistent")
        return []


def array_has_null(arr):
    for v in array_flatten(arr):
        if v is None:
            return True
    return False


def array_dim_lengths(arr):
    v0 = arr[0]
    if isinstance(v0, list):
        retval = [len(v0)]
        retval.extend(array_dim_lengths(v0))
    else:
        return [len(arr)]
    return retval


##
# This class represents a prepared statement.  A prepared statement is
# pre-parsed on the server, which reduces the need to parse the query every
# time it is run.  The statement can have parameters in the form of $1, $2, $3,
# etc.  When parameters are used, the types of the parameters need to be
# specified when creating the prepared statement.
# <p>
# As of v1.01, instances of this class are thread-safe.  This means that a
# single PreparedStatement can be accessed by multiple threads without the
# internal consistency of the statement being altered.  However, the
# responsibility is on the client application to ensure that one thread reading
# from a statement isn't affected by another thread starting a new query with
# the same statement.
# <p>
# Stability: Added in v1.00, stability guaranteed for v1.xx.
#
# @param connection     An instance of {@link Connection Connection}.
#
# @param statement      The SQL statement to be represented, often containing
# parameters in the form of $1, $2, $3, etc.
#
# @param types          Python type objects for each parameter in the SQL
# statement.  For example, int, float, str.
class PreparedStatement(Iterator):

    ##
    # Determines the number of rows to read from the database server at once.
    # Reading more rows increases performance at the cost of memory.  The
    # default value is 100 rows.  The affect of this parameter is transparent.
    # That is, the library reads more rows when the cache is empty
    # automatically.
    # <p>
    # Stability: Added in v1.00, stability guaranteed for v1.xx.  It is
    # possible that implementation changes in the future could cause this
    # parameter to be ignored.
    row_cache_size = 100

    def __init__(self, connection, query, values):

        # Stability: Added in v1.03, stability guaranteed for v1.xx.
        self.row_count = -1

        self.c = connection
        self.portal_name = None
        self.row_cache_size_bin = i_pack(PreparedStatement.row_cache_size)

        try:
            self.c.statement_number_lock.acquire()
            self.statement_name = "pg8000_statement_" + \
                str(self.c.statement_number)
            self.c.statement_number += 1
        finally:
            self.c.statement_number_lock.release()

        self.statement_name_bin = self.statement_name.encode('ascii') + \
            NULL_BYTE
        self._cached_rows = deque()
        self.statement, self.make_args = convert_paramstyle(
            pg8000.paramstyle, query)
        self.params = self.c.make_params(self.make_args(values))
        param_fcs = tuple(x[1] for x in self.params)
        self.param_funcs = tuple(x[2] for x in self.params)
        self.row_desc = []
        self.c.parse(self, self.statement)
        self._lock = threading.RLock()
        self.cmd = None

        # We've got row_desc that allows us to identify what we're
        # going to get back from this statement.
        output_fc = tuple(
            self.c.pg_types[f['type_oid']][0] for f in self.row_desc)

        self.input_funcs = tuple(f['func'] for f in self.row_desc)
        # Byte1('B') - Identifies the Bind command.
        # Int32 - Message length, including self.
        # String - Name of the destination portal.
        # String - Name of the source prepared statement.
        # Int16 - Number of parameter format codes.
        # For each parameter format code:
        #   Int16 - The parameter format code.
        # Int16 - Number of parameter values.
        # For each parameter value:
        #   Int32 - The length of the parameter value, in bytes, not
        #           including this length.  -1 indicates a NULL parameter
        #           value, in which no value bytes follow.
        #   Byte[n] - Value of the parameter.
        # Int16 - The number of result-column format codes.
        # For each result-column format code:
        #   Int16 - The format code.
        self.bind_1 = self.statement_name_bin + h_pack(len(self.params)) + \
            pack("!" + "h" * len(param_fcs), *param_fcs) + \
            h_pack(len(self.params))

        self.bind_2 = h_pack(len(output_fc)) + \
            pack("!" + "h" * len(output_fc), *output_fc)

    def close(self):
        if self.statement_name != "":  # don't close unnamed statement
            self.c.close_statement(self)
        if self.portal_name is not None:
            self.portal_name = None

    def get_row_description(self):
        return self.row_desc

    ##
    # Run the SQL prepared statement with the given parameters.
    # <p>
    # Stability: Added in v1.00, stability guaranteed for v1.xx.
    def execute(self, values, stream=None):
        try:
            self._lock.acquire()
            # cleanup last execute
            self._cached_rows.clear()
            self.row_count = -1
            self.portal_suspended = False
            try:
                self.c.portal_number_lock.acquire()
                self.portal_name = "pg8000_portal_" + str(self.c.portal_number)
                self.c.portal_number += 1
            finally:
                self.c.portal_number_lock.release()
            self.portal_name_bin = self.portal_name.encode('ascii') + NULL_BYTE
            self.cmd = None
            self.stream = stream
            self.c.bind(self, self.make_args(values))
        finally:
            self._lock.release()

    def __next__(self):
        try:
            self._lock.acquire()
            return self._cached_rows.popleft()
        except IndexError:
            if self.portal_suspended:
                try:
                    self.c._sock_lock.acquire()
                    self.c.send_EXECUTE(self)
                    self.c._write(SYNC_MSG)
                    self.c._flush()
                    self.c.handle_messages(self)
                finally:
                    self.c._sock_lock.release()

            try:
                return self._cached_rows.popleft()
            except IndexError:
                if len(self.row_desc) == 0:
                    raise ProgrammingError("no result set")
                raise StopIteration()
        finally:
            self._lock.release()

########NEW FILE########
__FILENAME__ = errors
# vim: sw=4:expandtab:foldmethod=marker
#
# Copyright (c) 2007-2009, Mathieu Fenniak
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
# * Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.
# * Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
# * The name of the author may not be used to endorse or promote products
# derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

__author__ = "Mathieu Fenniak"


class Warning(Exception):
    pass


class Error(Exception):
    pass


class InterfaceError(Error):
    pass


class ConnectionClosedError(InterfaceError):
    def __init__(self):
        InterfaceError.__init__(self, "connection is closed")


class CursorClosedError(InterfaceError):
    def __init__(self):
        InterfaceError.__init__(self, "cursor is closed")


class DatabaseError(Error):
    pass


class DataError(DatabaseError):
    pass


class OperationalError(DatabaseError):
    pass


class IntegrityError(DatabaseError):
    pass


class InternalError(DatabaseError):
    pass


class ProgrammingError(DatabaseError):
    pass


class NotSupportedError(DatabaseError):
    pass


##
# An exception that is thrown when an internal error occurs trying to
# decode binary array data from the server.
class ArrayDataParseError(InternalError):
    pass


##
# Thrown when attempting to transmit an array of unsupported data types.
class ArrayContentNotSupportedError(NotSupportedError):
    pass


##
# Thrown when attempting to send an array that doesn't contain all the same
# type of objects (eg. some floats, some ints).
class ArrayContentNotHomogenousError(ProgrammingError):
    pass


##
# Attempted to pass an empty array in, but it's not possible to determine the
# data type for an empty array.
class ArrayContentEmptyError(ProgrammingError):
    pass


##
# Attempted to use a multidimensional array with inconsistent array sizes.
class ArrayDimensionsNotConsistentError(ProgrammingError):
    pass


# A cursor's copy_to or copy_from argument was not provided a table or query
# to operate on.
class CopyQueryOrTableRequiredError(ProgrammingError):
    pass


# Raised if a COPY query is executed without using copy_to or copy_from
# functions to provide a data stream.
class CopyQueryWithoutStreamError(ProgrammingError):
    pass


# When query parameters don't match up with query args.
class QueryParameterIndexError(ProgrammingError):
    pass


# Some sort of parse error occured during query parameterization.
class QueryParameterParseError(ProgrammingError):
    pass

########NEW FILE########
__FILENAME__ = six
"""Utilities for writing code that runs on Python 2 and 3"""

# Copyright (c) 2010-2013 Benjamin Peterson
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from __future__ import absolute_import
import operator
import sys
import types

__author__ = "Benjamin Peterson <benjamin@python.org>"
__version__ = "1.4.1"


# Useful for very coarse version differentiation.
PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3

PRE_26 = PY2 and sys.version_info[1] < 6

IS_JYTHON = sys.platform.lower().count('java') > 0


if PY3:
    string_types = str,
    integer_types = int,
    class_types = type,
    text_type = str
    binary_type = bytes

    MAXSIZE = sys.maxsize
else:
    string_types = basestring,  # noqa
    integer_types = (int, long)  # noqa
    class_types = (type, types.ClassType)
    text_type = unicode  # noqa
    binary_type = str

    if sys.platform.startswith("java"):
        # Jython always uses 32 bits.
        MAXSIZE = int((1 << 31) - 1)
    else:
        # It's possible to have sizeof(long) != sizeof(Py_ssize_t).
        class X(object):
            def __len__(self):
                return 1 << 31
        try:
            len(X())
        except OverflowError:
            # 32-bit
            MAXSIZE = int((1 << 31) - 1)
        else:
            # 64-bit
            MAXSIZE = int((1 << 63) - 1)
        del X


def _add_doc(func, doc):
    """Add documentation to a function."""
    func.__doc__ = doc


def _import_module(name):
    """Import module, returning the module after the last dot."""
    __import__(name)
    return sys.modules[name]


class _LazyDescr(object):

    def __init__(self, name):
        self.name = name

    def __get__(self, obj, tp):
        result = self._resolve()
        setattr(obj, self.name, result)
        # This is a bit ugly, but it avoids running this again.
        delattr(tp, self.name)
        return result


class MovedModule(_LazyDescr):

    def __init__(self, name, old, new=None):
        super(MovedModule, self).__init__(name)
        if PY3:
            if new is None:
                new = name
            self.mod = new
        else:
            self.mod = old

    def _resolve(self):
        return _import_module(self.mod)


class MovedAttribute(_LazyDescr):

    def __init__(self, name, old_mod, new_mod, old_attr=None, new_attr=None):
        super(MovedAttribute, self).__init__(name)
        if PY3:
            if new_mod is None:
                new_mod = name
            self.mod = new_mod
            if new_attr is None:
                if old_attr is None:
                    new_attr = name
                else:
                    new_attr = old_attr
            self.attr = new_attr
        else:
            self.mod = old_mod
            if old_attr is None:
                old_attr = name
            self.attr = old_attr

    def _resolve(self):
        module = _import_module(self.mod)
        return getattr(module, self.attr)


class _MovedItems(types.ModuleType):
    """Lazy loading of moved objects"""


_moved_attributes = [
    MovedAttribute("cStringIO", "cStringIO", "io", "StringIO"),
    MovedAttribute("filter", "itertools", "builtins", "ifilter", "filter"),
    MovedAttribute(
        "filterfalse", "itertools", "itertools", "ifilterfalse",
        "filterfalse"),
    MovedAttribute("input", "__builtin__", "builtins", "raw_input", "input"),
    MovedAttribute("map", "itertools", "builtins", "imap", "map"),
    MovedAttribute("range", "__builtin__", "builtins", "xrange", "range"),
    MovedAttribute("reload_module", "__builtin__", "imp", "reload"),
    MovedAttribute("reduce", "__builtin__", "functools"),
    MovedAttribute("StringIO", "StringIO", "io"),
    MovedAttribute("UserString", "UserString", "collections"),
    MovedAttribute("xrange", "__builtin__", "builtins", "xrange", "range"),
    MovedAttribute("zip", "itertools", "builtins", "izip", "zip"),
    MovedAttribute(
        "zip_longest", "itertools", "itertools", "izip_longest",
        "zip_longest"),
    MovedModule("builtins", "__builtin__"),
    MovedModule("configparser", "ConfigParser"),
    MovedModule("copyreg", "copy_reg"),
    MovedModule("http_cookiejar", "cookielib", "http.cookiejar"),
    MovedModule("http_cookies", "Cookie", "http.cookies"),
    MovedModule("html_entities", "htmlentitydefs", "html.entities"),
    MovedModule("html_parser", "HTMLParser", "html.parser"),
    MovedModule("http_client", "httplib", "http.client"),
    MovedModule(
        "email_mime_multipart", "email.MIMEMultipart", "email.mime.multipart"),
    MovedModule("email_mime_text", "email.MIMEText", "email.mime.text"),
    MovedModule("email_mime_base", "email.MIMEBase", "email.mime.base"),
    MovedModule("BaseHTTPServer", "BaseHTTPServer", "http.server"),
    MovedModule("CGIHTTPServer", "CGIHTTPServer", "http.server"),
    MovedModule("SimpleHTTPServer", "SimpleHTTPServer", "http.server"),
    MovedModule("cPickle", "cPickle", "pickle"),
    MovedModule("queue", "Queue"),
    MovedModule("reprlib", "repr"),
    MovedModule("socketserver", "SocketServer"),
    MovedModule("tkinter", "Tkinter"),
    MovedModule("tkinter_dialog", "Dialog", "tkinter.dialog"),
    MovedModule("tkinter_filedialog", "FileDialog", "tkinter.filedialog"),
    MovedModule(
        "tkinter_scrolledtext", "ScrolledText", "tkinter.scrolledtext"),
    MovedModule(
        "tkinter_simpledialog", "SimpleDialog", "tkinter.simpledialog"),
    MovedModule("tkinter_tix", "Tix", "tkinter.tix"),
    MovedModule("tkinter_constants", "Tkconstants", "tkinter.constants"),
    MovedModule("tkinter_dnd", "Tkdnd", "tkinter.dnd"),
    MovedModule("tkinter_colorchooser", "tkColorChooser",
                "tkinter.colorchooser"),
    MovedModule("tkinter_commondialog", "tkCommonDialog",
                "tkinter.commondialog"),
    MovedModule("tkinter_tkfiledialog", "tkFileDialog", "tkinter.filedialog"),
    MovedModule("tkinter_font", "tkFont", "tkinter.font"),
    MovedModule("tkinter_messagebox", "tkMessageBox", "tkinter.messagebox"),
    MovedModule(
        "tkinter_tksimpledialog", "tkSimpleDialog", "tkinter.simpledialog"),
    MovedModule(
        "urllib_parse", __name__ + ".moves.urllib_parse", "urllib.parse"),
    MovedModule(
        "urllib_error", __name__ + ".moves.urllib_error", "urllib.error"),
    MovedModule(
        "urllib", __name__ + ".moves.urllib", __name__ + ".moves.urllib"),
    MovedModule("urllib_robotparser", "robotparser", "urllib.robotparser"),
    MovedModule("winreg", "_winreg"),
]
for attr in _moved_attributes:
    setattr(_MovedItems, attr.name, attr)
del attr

moves = sys.modules[__name__ + ".moves"] = _MovedItems(__name__ + ".moves")


class Module_six_moves_urllib_parse(types.ModuleType):
    """Lazy loading of moved objects in six.moves.urllib_parse"""


_urllib_parse_moved_attributes = [
    MovedAttribute("ParseResult", "urlparse", "urllib.parse"),
    MovedAttribute("parse_qs", "urlparse", "urllib.parse"),
    MovedAttribute("parse_qsl", "urlparse", "urllib.parse"),
    MovedAttribute("urldefrag", "urlparse", "urllib.parse"),
    MovedAttribute("urljoin", "urlparse", "urllib.parse"),
    MovedAttribute("urlparse", "urlparse", "urllib.parse"),
    MovedAttribute("urlsplit", "urlparse", "urllib.parse"),
    MovedAttribute("urlunparse", "urlparse", "urllib.parse"),
    MovedAttribute("urlunsplit", "urlparse", "urllib.parse"),
    MovedAttribute("quote", "urllib", "urllib.parse"),
    MovedAttribute("quote_plus", "urllib", "urllib.parse"),
    MovedAttribute("unquote", "urllib", "urllib.parse"),
    MovedAttribute("unquote_plus", "urllib", "urllib.parse"),
    MovedAttribute("urlencode", "urllib", "urllib.parse"),
]
for attr in _urllib_parse_moved_attributes:
    setattr(Module_six_moves_urllib_parse, attr.name, attr)
del attr

sys.modules[__name__ + ".moves.urllib_parse"] = Module_six_moves_urllib_parse(
    __name__ + ".moves.urllib_parse")
sys.modules[__name__ + ".moves.urllib.parse"] = Module_six_moves_urllib_parse(
    __name__ + ".moves.urllib.parse")


class Module_six_moves_urllib_error(types.ModuleType):
    """Lazy loading of moved objects in six.moves.urllib_error"""


_urllib_error_moved_attributes = [
    MovedAttribute("URLError", "urllib2", "urllib.error"),
    MovedAttribute("HTTPError", "urllib2", "urllib.error"),
    MovedAttribute("ContentTooShortError", "urllib", "urllib.error"),
]
for attr in _urllib_error_moved_attributes:
    setattr(Module_six_moves_urllib_error, attr.name, attr)
del attr

sys.modules[__name__ + ".moves.urllib_error"] = Module_six_moves_urllib_error(
    __name__ + ".moves.urllib_error")
sys.modules[__name__ + ".moves.urllib.error"] = Module_six_moves_urllib_error(
    __name__ + ".moves.urllib.error")


class Module_six_moves_urllib_request(types.ModuleType):
    """Lazy loading of moved objects in six.moves.urllib_request"""


_urllib_request_moved_attributes = [
    MovedAttribute("urlopen", "urllib2", "urllib.request"),
    MovedAttribute("install_opener", "urllib2", "urllib.request"),
    MovedAttribute("build_opener", "urllib2", "urllib.request"),
    MovedAttribute("pathname2url", "urllib", "urllib.request"),
    MovedAttribute("url2pathname", "urllib", "urllib.request"),
    MovedAttribute("getproxies", "urllib", "urllib.request"),
    MovedAttribute("Request", "urllib2", "urllib.request"),
    MovedAttribute("OpenerDirector", "urllib2", "urllib.request"),
    MovedAttribute("HTTPDefaultErrorHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPRedirectHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPCookieProcessor", "urllib2", "urllib.request"),
    MovedAttribute("ProxyHandler", "urllib2", "urllib.request"),
    MovedAttribute("BaseHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPPasswordMgr", "urllib2", "urllib.request"),
    MovedAttribute(
        "HTTPPasswordMgrWithDefaultRealm", "urllib2", "urllib.request"),
    MovedAttribute("AbstractBasicAuthHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPBasicAuthHandler", "urllib2", "urllib.request"),
    MovedAttribute("ProxyBasicAuthHandler", "urllib2", "urllib.request"),
    MovedAttribute("AbstractDigestAuthHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPDigestAuthHandler", "urllib2", "urllib.request"),
    MovedAttribute("ProxyDigestAuthHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPSHandler", "urllib2", "urllib.request"),
    MovedAttribute("FileHandler", "urllib2", "urllib.request"),
    MovedAttribute("FTPHandler", "urllib2", "urllib.request"),
    MovedAttribute("CacheFTPHandler", "urllib2", "urllib.request"),
    MovedAttribute("UnknownHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPErrorProcessor", "urllib2", "urllib.request"),
    MovedAttribute("urlretrieve", "urllib", "urllib.request"),
    MovedAttribute("urlcleanup", "urllib", "urllib.request"),
    MovedAttribute("URLopener", "urllib", "urllib.request"),
    MovedAttribute("FancyURLopener", "urllib", "urllib.request"),
]
for attr in _urllib_request_moved_attributes:
    setattr(Module_six_moves_urllib_request, attr.name, attr)
del attr

sys.modules[__name__ + ".moves.urllib_request"] = \
    Module_six_moves_urllib_request(__name__ + ".moves.urllib_request")
sys.modules[__name__ + ".moves.urllib.request"] = \
    Module_six_moves_urllib_request(__name__ + ".moves.urllib.request")


class Module_six_moves_urllib_response(types.ModuleType):
    """Lazy loading of moved objects in six.moves.urllib_response"""


_urllib_response_moved_attributes = [
    MovedAttribute("addbase", "urllib", "urllib.response"),
    MovedAttribute("addclosehook", "urllib", "urllib.response"),
    MovedAttribute("addinfo", "urllib", "urllib.response"),
    MovedAttribute("addinfourl", "urllib", "urllib.response"),
]
for attr in _urllib_response_moved_attributes:
    setattr(Module_six_moves_urllib_response, attr.name, attr)
del attr

sys.modules[__name__ + ".moves.urllib_response"] = \
    Module_six_moves_urllib_response(__name__ + ".moves.urllib_response")
sys.modules[__name__ + ".moves.urllib.response"] = \
    Module_six_moves_urllib_response(__name__ + ".moves.urllib.response")


class Module_six_moves_urllib_robotparser(types.ModuleType):
    """Lazy loading of moved objects in six.moves.urllib_robotparser"""


_urllib_robotparser_moved_attributes = [
    MovedAttribute("RobotFileParser", "robotparser", "urllib.robotparser"),
]
for attr in _urllib_robotparser_moved_attributes:
    setattr(Module_six_moves_urllib_robotparser, attr.name, attr)
del attr

sys.modules[__name__ + ".moves.urllib_robotparser"] = \
    Module_six_moves_urllib_robotparser(__name__ + ".moves.urllib_robotparser")
sys.modules[__name__ + ".moves.urllib.robotparser"] = \
    Module_six_moves_urllib_robotparser(
        __name__ + ".moves.urllib.robotparser")


class Module_six_moves_urllib(types.ModuleType):
    """Create a six.moves.urllib namespace that resembles the Python 3
    namespace"""
    parse = sys.modules[__name__ + ".moves.urllib_parse"]
    error = sys.modules[__name__ + ".moves.urllib_error"]
    request = sys.modules[__name__ + ".moves.urllib_request"]
    response = sys.modules[__name__ + ".moves.urllib_response"]
    robotparser = sys.modules[__name__ + ".moves.urllib_robotparser"]


sys.modules[__name__ + ".moves.urllib"] = Module_six_moves_urllib(
    __name__ + ".moves.urllib")


def add_move(move):
    """Add an item to six.moves."""
    setattr(_MovedItems, move.name, move)


def remove_move(name):
    """Remove item from six.moves."""
    try:
        delattr(_MovedItems, name)
    except AttributeError:
        try:
            del moves.__dict__[name]
        except KeyError:
            raise AttributeError("no such move, %r" % (name,))


if PY3:
    _meth_func = "__func__"
    _meth_self = "__self__"

    _func_closure = "__closure__"
    _func_code = "__code__"
    _func_defaults = "__defaults__"
    _func_globals = "__globals__"

    _iterkeys = "keys"
    _itervalues = "values"
    _iteritems = "items"
    _iterlists = "lists"
else:
    _meth_func = "im_func"
    _meth_self = "im_self"

    _func_closure = "func_closure"
    _func_code = "func_code"
    _func_defaults = "func_defaults"
    _func_globals = "func_globals"

    _iterkeys = "iterkeys"
    _itervalues = "itervalues"
    _iteritems = "iteritems"
    _iterlists = "iterlists"


try:
    advance_iterator = next
except NameError:
    def advance_iterator(it):
        return it.next()
next = advance_iterator


try:
    callable = callable
except NameError:
    def callable(obj):
        return any("__call__" in klass.__dict__ for klass in type(obj).__mro__)


if PY3:
    def get_unbound_function(unbound):
        return unbound

    create_bound_method = types.MethodType

    Iterator = object
else:
    def get_unbound_function(unbound):
        return unbound.im_func

    def create_bound_method(func, obj):
        return types.MethodType(func, obj, obj.__class__)

    class Iterator(object):

        def next(self):
            return type(self).__next__(self)

    callable = callable
_add_doc(get_unbound_function,
         """Get the function out of a possibly unbound function""")


get_method_function = operator.attrgetter(_meth_func)
get_method_self = operator.attrgetter(_meth_self)
get_function_closure = operator.attrgetter(_func_closure)
get_function_code = operator.attrgetter(_func_code)
get_function_defaults = operator.attrgetter(_func_defaults)
get_function_globals = operator.attrgetter(_func_globals)


def iterkeys(d, **kw):
    """Return an iterator over the keys of a dictionary."""
    return iter(getattr(d, _iterkeys)(**kw))


def itervalues(d, **kw):
    """Return an iterator over the values of a dictionary."""
    return iter(getattr(d, _itervalues)(**kw))


def iteritems(d, **kw):
    """Return an iterator over the (key, value) pairs of a dictionary."""
    return iter(getattr(d, _iteritems)(**kw))


def iterlists(d, **kw):
    """Return an iterator over the (key, [values]) pairs of a dictionary."""
    return iter(getattr(d, _iterlists)(**kw))


if PY3:
    def b(s):
        return s.encode("latin-1")

    def u(s):
        return s
    unichr = chr
    if sys.version_info[1] <= 1:
        def int2byte(i):
            return bytes((i,))
    else:
        # This is about 2x faster than the implementation above on 3.2+
        int2byte = operator.methodcaller("to_bytes", 1, "big")
    byte2int = operator.itemgetter(0)
    indexbytes = operator.getitem
    iterbytes = iter
    import io
    StringIO = io.StringIO
    BytesIO = io.BytesIO
else:
    def b(s):
        return s

    def u(s):
        return unicode(s, "unicode_escape")  # noqa
    unichr = unichr
    int2byte = chr

    def byte2int(bs):
        return ord(bs[0])

    def indexbytes(buf, i):
        return ord(buf[i])

    def iterbytes(buf):
        return (ord(byte) for byte in buf)
    import StringIO
    StringIO = BytesIO = StringIO.StringIO
_add_doc(b, """Byte literal""")
_add_doc(u, """Text literal""")


if PY3:
    import builtins
    exec_ = getattr(builtins, "exec")

    def reraise(tp, value, tb=None):
        if value.__traceback__ is not tb:
            raise value.with_traceback(tb)
        raise value

    print_ = getattr(builtins, "print")
    del builtins

else:
    def exec_(_code_, _globs_=None, _locs_=None):
        """Execute code in a namespace."""
        if _globs_ is None:
            frame = sys._getframe(1)
            _globs_ = frame.f_globals
            if _locs_ is None:
                _locs_ = frame.f_locals
            del frame
        elif _locs_ is None:
            _locs_ = _globs_
        exec("""exec _code_ in _globs_, _locs_""")

    exec_("""def reraise(tp, value, tb=None):
    raise tp, value, tb
""")

    def print_(*args, **kwargs):
        """The new-style print function."""
        fp = kwargs.pop("file", sys.stdout)
        if fp is None:
            return

        def write(data):
            if not isinstance(data, basestring):  # noqa
                data = str(data)
            fp.write(data)
        want_unicode = False
        sep = kwargs.pop("sep", None)
        if sep is not None:
            if isinstance(sep, unicode):  # noqa
                want_unicode = True
            elif not isinstance(sep, str):
                raise TypeError("sep must be None or a string")
        end = kwargs.pop("end", None)
        if end is not None:
            if isinstance(end, unicode):  # noqa
                want_unicode = True
            elif not isinstance(end, str):
                raise TypeError("end must be None or a string")
        if kwargs:
            raise TypeError("invalid keyword arguments to print()")
        if not want_unicode:
            for arg in args:
                if isinstance(arg, unicode):  # noqa
                    want_unicode = True
                    break
        if want_unicode:
            newline = unicode("\n")  # noqa
            space = unicode(" ")  # noqa
        else:
            newline = "\n"
            space = " "
        if sep is None:
            sep = space
        if end is None:
            end = newline
        for i, arg in enumerate(args):
            if i:
                write(sep)
            write(arg)
        write(end)

_add_doc(reraise, """Reraise an exception.""")


def with_metaclass(meta, *bases):
    """Create a base class with a metaclass."""
    return meta("NewBase", bases, {})


def add_metaclass(metaclass):
    """Class decorator for creating a class with a metaclass."""
    def wrapper(cls):
        orig_vars = cls.__dict__.copy()
        orig_vars.pop('__dict__', None)
        orig_vars.pop('__weakref__', None)
        for slots_var in orig_vars.get('__slots__', ()):
            orig_vars.pop(slots_var)
        return metaclass(cls.__name__, cls.__bases__, orig_vars)
    return wrapper

########NEW FILE########
__FILENAME__ = connection_settings
import os


db_stewart_connect = {
    "host": "127.0.0.1",
    "user": "pg8000-test",
    "database": "pg8000-test",
    "password": "pg8000-test",
    "socket_timeout": 5,
    "ssl": False}

db_local_connect = {
    "unix_sock": "/tmp/.s.PGSQL.5432",
    "user": "mfenniak"}

db_local_win_connect = {
    "host": "localhost",
    "user": "mfenniak",
    "password": "password",
    "database": "mfenniak"}

db_oracledev2_connect = {
    "host": "oracledev2",
    "user": "mfenniak",
    "password": "password",
    "database": "mfenniak"}

db_connect = eval(os.environ["PG8000_TEST"])

try:
    from testconfig import config
    try:
        db_connect['use_cache'] = config['use_cache'] == 'true'
    except KeyError:
        pass
except:
    # This means we're using Python 2.5 which is a special case.
    pass

########NEW FILE########
__FILENAME__ = dbapi20
#!/usr/bin/env python
''' Python DB API 2.0 driver compliance unit test suite.

    This software is Public Domain and may be used without restrictions.

 "Now we have booze and barflies entering the discussion, plus rumours of
  DBAs on drugs... and I won't tell you what flashes through my mind each
  time I read the subject line with 'Anal Compliance' in it.  All around
  this is turning out to be a thoroughly unwholesome unit test."

    -- Ian Bicking
'''

__rcs_id__ = '$Id: dbapi20.py,v 1.10 2003/10/09 03:14:14 zenzen Exp $'
__version__ = '$Revision: 1.10 $'[11:-2]
__author__ = 'Stuart Bishop <zen@shangri-la.dropbear.id.au>'

import unittest
import time
import warnings
from pg8000.six import b

# $Log: dbapi20.py,v $
# Revision 1.10  2003/10/09 03:14:14  zenzen
# Add test for DB API 2.0 optional extension, where database exceptions
# are exposed as attributes on the Connection object.
#
# Revision 1.9  2003/08/13 01:16:36  zenzen
# Minor tweak from Stefan Fleiter
#
# Revision 1.8  2003/04/10 00:13:25  zenzen
# Changes, as per suggestions by M.-A. Lemburg
# - Add a table prefix, to ensure namespace collisions can always be avoided
#
# Revision 1.7  2003/02/26 23:33:37  zenzen
# Break out DDL into helper functions, as per request by David Rushby
#
# Revision 1.6  2003/02/21 03:04:33  zenzen
# Stuff from Henrik Ekelund:
#     added test_None
#     added test_nextset & hooks
#
# Revision 1.5  2003/02/17 22:08:43  zenzen
# Implement suggestions and code from Henrik Eklund - test that
# cursor.arraysize defaults to 1 & generic cursor.callproc test added
#
# Revision 1.4  2003/02/15 00:16:33  zenzen
# Changes, as per suggestions and bug reports by M.-A. Lemburg,
# Matthew T. Kromer, Federico Di Gregorio and Daniel Dittmar
# - Class renamed
# - Now a subclass of TestCase, to avoid requiring the driver stub
#   to use multiple inheritance
# - Reversed the polarity of buggy test in test_description
# - Test exception heirarchy correctly
# - self.populate is now self._populate(), so if a driver stub
#   overrides self.ddl1 this change propogates
# - VARCHAR columns now have a width, which will hopefully make the
#   DDL even more portible (this will be reversed if it causes more problems)
# - cursor.rowcount being checked after various execute and fetchXXX methods
# - Check for fetchall and fetchmany returning empty lists after results
#   are exhausted (already checking for empty lists if select retrieved
#   nothing
# - Fix bugs in test_setoutputsize_basic and test_setinputsizes
#


class DatabaseAPI20Test(unittest.TestCase):
    ''' Test a database self.driver for DB API 2.0 compatibility.
        This implementation tests Gadfly, but the TestCase
        is structured so that other self.drivers can subclass this
        test case to ensure compiliance with the DB-API. It is
        expected that this TestCase may be expanded in the future
        if ambiguities or edge conditions are discovered.

        The 'Optional Extensions' are not yet being tested.

        self.drivers should subclass this test, overriding setUp, tearDown,
        self.driver, connect_args and connect_kw_args. Class specification
        should be as follows:

        import dbapi20
        class mytest(dbapi20.DatabaseAPI20Test):
           [...]

        Don't 'import DatabaseAPI20Test from dbapi20', or you will
        confuse the unit tester - just 'import dbapi20'.
    '''

    # The self.driver module. This should be the module where the 'connect'
    # method is to be found
    driver = None
    connect_args = ()  # List of arguments to pass to connect
    connect_kw_args = {}  # Keyword arguments for connect
    table_prefix = 'dbapi20test_'  # If you need to specify a prefix for tables

    ddl1 = 'create table %sbooze (name varchar(20))' % table_prefix
    ddl2 = 'create table %sbarflys (name varchar(20))' % table_prefix
    xddl1 = 'drop table %sbooze' % table_prefix
    xddl2 = 'drop table %sbarflys' % table_prefix

    # Name of stored procedure to convert
    # string->lowercase
    lowerfunc = 'lower'

    # Some drivers may need to override these helpers, for example adding
    # a 'commit' after the execute.
    def executeDDL1(self, cursor):
        cursor.execute(self.ddl1)

    def executeDDL2(self, cursor):
        cursor.execute(self.ddl2)

    def setUp(self):
        ''' self.drivers should override this method to perform required setup
            if any is necessary, such as creating the database.
        '''
        pass

    def tearDown(self):
        ''' self.drivers should override this method to perform required
            cleanup if any is necessary, such as deleting the test database.
            The default drops the tables that may be created.
        '''
        con = self._connect()
        try:
            cur = con.cursor()
            for ddl in (self.xddl1, self.xddl2):
                try:
                    cur.execute(ddl)
                    con.commit()
                except self.driver.Error:
                    # Assume table didn't exist. Other tests will check if
                    # execute is busted.
                    pass
        finally:
            con.close()

    def _connect(self):
        try:
            return self.driver.connect(
                *self.connect_args, **self.connect_kw_args)
        except AttributeError:
            self.fail("No connect method found in self.driver module")

    def test_connect(self):
        con = self._connect()
        con.close()

    def test_apilevel(self):
        try:
            # Must exist
            apilevel = self.driver.apilevel
            # Must equal 2.0
            self.assertEqual(apilevel, '2.0')
        except AttributeError:
            self.fail("Driver doesn't define apilevel")

    def test_threadsafety(self):
        try:
            # Must exist
            threadsafety = self.driver.threadsafety
            # Must be a valid value
            self.assertEqual(threadsafety in (0, 1, 2, 3), True)
        except AttributeError:
            self.fail("Driver doesn't define threadsafety")

    def test_paramstyle(self):
        try:
            # Must exist
            paramstyle = self.driver.paramstyle
            # Must be a valid value
            self.assertEqual(
                paramstyle in (
                    'qmark', 'numeric', 'named', 'format', 'pyformat'), True)
        except AttributeError:
            self.fail("Driver doesn't define paramstyle")

    def test_Exceptions(self):
        # Make sure required exceptions exist, and are in the
        # defined heirarchy.
        self.assertEqual(issubclass(self.driver.Warning, Exception), True)
        self.assertEqual(issubclass(self.driver.Error, Exception), True)
        self.assertEqual(
            issubclass(self.driver.InterfaceError, self.driver.Error), True)
        self.assertEqual(
            issubclass(self.driver.DatabaseError, self.driver.Error), True)
        self.assertEqual(
            issubclass(self.driver.OperationalError, self.driver.Error), True)
        self.assertEqual(
            issubclass(self.driver.IntegrityError, self.driver.Error), True)
        self.assertEqual(
            issubclass(self.driver.InternalError, self.driver.Error), True)
        self.assertEqual(
            issubclass(self.driver.ProgrammingError, self.driver.Error), True)
        self.assertEqual(
            issubclass(self.driver.NotSupportedError, self.driver.Error), True)

    def test_ExceptionsAsConnectionAttributes(self):
        # OPTIONAL EXTENSION
        # Test for the optional DB API 2.0 extension, where the exceptions
        # are exposed as attributes on the Connection object
        # I figure this optional extension will be implemented by any
        # driver author who is using this test suite, so it is enabled
        # by default.
        warnings.simplefilter("ignore")
        con = self._connect()
        drv = self.driver
        self.assertEqual(con.Warning is drv.Warning, True)
        self.assertEqual(con.Error is drv.Error, True)
        self.assertEqual(con.InterfaceError is drv.InterfaceError, True)
        self.assertEqual(con.DatabaseError is drv.DatabaseError, True)
        self.assertEqual(con.OperationalError is drv.OperationalError, True)
        self.assertEqual(con.IntegrityError is drv.IntegrityError, True)
        self.assertEqual(con.InternalError is drv.InternalError, True)
        self.assertEqual(con.ProgrammingError is drv.ProgrammingError, True)
        self.assertEqual(con.NotSupportedError is drv.NotSupportedError, True)
        warnings.resetwarnings()
        con.close()

    def test_commit(self):
        con = self._connect()
        try:
            # Commit must work, even if it doesn't do anything
            con.commit()
        finally:
            con.close()

    def test_rollback(self):
        con = self._connect()
        # If rollback is defined, it should either work or throw
        # the documented exception
        if hasattr(con, 'rollback'):
            try:
                con.rollback()
            except self.driver.NotSupportedError:
                pass
        con.close()

    def test_cursor(self):
        con = self._connect()
        try:
            con.cursor()
        finally:
            con.close()

    def test_cursor_isolation(self):
        con = self._connect()
        try:
            # Make sure cursors created from the same connection have
            # the documented transaction isolation level
            cur1 = con.cursor()
            cur2 = con.cursor()
            self.executeDDL1(cur1)
            cur1.execute(
                "insert into %sbooze values ('Victoria Bitter')" % (
                    self.table_prefix))
            cur2.execute("select name from %sbooze" % self.table_prefix)
            booze = cur2.fetchall()
            self.assertEqual(len(booze), 1)
            self.assertEqual(len(booze[0]), 1)
            self.assertEqual(booze[0][0], 'Victoria Bitter')
        finally:
            con.close()

    def test_description(self):
        con = self._connect()
        try:
            cur = con.cursor()
            self.executeDDL1(cur)
            self.assertEqual(
                cur.description, None,
                'cursor.description should be none after executing a '
                'statement that can return no rows (such as DDL)')
            cur.execute('select name from %sbooze' % self.table_prefix)
            self.assertEqual(
                len(cur.description), 1,
                'cursor.description describes too many columns')
            self.assertEqual(
                len(cur.description[0]), 7,
                'cursor.description[x] tuples must have 7 elements')
            self.assertEqual(
                cur.description[0][0].lower(), b('name'),
                'cursor.description[x][0] must return column name')
            self.assertEqual(
                cur.description[0][1], self.driver.STRING,
                'cursor.description[x][1] must return column type. Got %r'
                % cur.description[0][1])

            # Make sure self.description gets reset
            self.executeDDL2(cur)
            self.assertEqual(
                cur.description, None,
                'cursor.description not being set to None when executing '
                'no-result statements (eg. DDL)')
        finally:
            con.close()

    def test_rowcount(self):
        con = self._connect()
        try:
            cur = con.cursor()
            self.executeDDL1(cur)
            self.assertEqual(
                cur.rowcount, -1,
                'cursor.rowcount should be -1 after executing no-result '
                'statements')
            cur.execute(
                "insert into %sbooze values ('Victoria Bitter')" % (
                    self.table_prefix))
            self.assertEqual(
                cur.rowcount in (-1, 1), True,
                'cursor.rowcount should == number or rows inserted, or '
                'set to -1 after executing an insert statement')
            cur.execute("select name from %sbooze" % self.table_prefix)
            self.assertEqual(
                cur.rowcount in (-1, 1), True,
                'cursor.rowcount should == number of rows returned, or '
                'set to -1 after executing a select statement')
            self.executeDDL2(cur)
            self.assertEqual(
                cur.rowcount, -1,
                'cursor.rowcount not being reset to -1 after executing '
                'no-result statements')
        finally:
            con.close()

    lower_func = 'lower'

    def test_callproc(self):
        con = self._connect()
        try:
            cur = con.cursor()
            if self.lower_func and hasattr(cur, 'callproc'):
                r = cur.callproc(self.lower_func, ('FOO',))
                self.assertEqual(len(r), 1)
                self.assertEqual(r[0], 'FOO')
                r = cur.fetchall()
                self.assertEqual(len(r), 1, 'callproc produced no result set')
                self.assertEqual(
                    len(r[0]), 1, 'callproc produced invalid result set')
                self.assertEqual(
                    r[0][0], 'foo', 'callproc produced invalid results')
        finally:
            con.close()

    def test_close(self):
        con = self._connect()
        try:
            cur = con.cursor()
        finally:
            con.close()

        # cursor.execute should raise an Error if called after connection
        # closed
        self.assertRaises(self.driver.Error, self.executeDDL1, cur)

        # connection.commit should raise an Error if called after connection'
        # closed.'
        self.assertRaises(self.driver.Error, con.commit)

        # connection.close should raise an Error if called more than once
        self.assertRaises(self.driver.Error, con.close)

    def test_execute(self):
        con = self._connect()
        try:
            cur = con.cursor()
            self._paraminsert(cur)
        finally:
            con.close()

    def _paraminsert(self, cur):
        self.executeDDL1(cur)
        cur.execute("insert into %sbooze values ('Victoria Bitter')" % (
            self.table_prefix))
        self.assertEqual(cur.rowcount in (-1, 1), True)

        if self.driver.paramstyle == 'qmark':
            cur.execute(
                'insert into %sbooze values (?)' % self.table_prefix,
                ("Cooper's",))
        elif self.driver.paramstyle == 'numeric':
            cur.execute(
                'insert into %sbooze values (:1)' % self.table_prefix,
                ("Cooper's",))
        elif self.driver.paramstyle == 'named':
            cur.execute(
                'insert into %sbooze values (:beer)' % self.table_prefix,
                {'beer': "Cooper's"})
        elif self.driver.paramstyle == 'format':
            cur.execute(
                'insert into %sbooze values (%%s)' % self.table_prefix,
                ("Cooper's",))
        elif self.driver.paramstyle == 'pyformat':
            cur.execute(
                'insert into %sbooze values (%%(beer)s)' % self.table_prefix,
                {'beer': "Cooper's"})
        else:
            self.fail('Invalid paramstyle')
        self.assertEqual(cur.rowcount in (-1, 1), True)

        cur.execute('select name from %sbooze' % self.table_prefix)
        res = cur.fetchall()
        self.assertEqual(
            len(res), 2, 'cursor.fetchall returned too few rows')
        beers = [res[0][0], res[1][0]]
        beers.sort()
        self.assertEqual(
            beers[0], "Cooper's",
            'cursor.fetchall retrieved incorrect data, or data inserted '
            'incorrectly')
        self.assertEqual(
            beers[1], "Victoria Bitter",
            'cursor.fetchall retrieved incorrect data, or data inserted '
            'incorrectly')

    def test_executemany(self):
        con = self._connect()
        try:
            cur = con.cursor()
            self.executeDDL1(cur)
            largs = [("Cooper's",), ("Boag's",)]
            margs = [{'beer': "Cooper's"}, {'beer': "Boag's"}]
            if self.driver.paramstyle == 'qmark':
                cur.executemany(
                    'insert into %sbooze values (?)' % self.table_prefix,
                    largs
                    )
            elif self.driver.paramstyle == 'numeric':
                cur.executemany(
                    'insert into %sbooze values (:1)' % self.table_prefix,
                    largs
                    )
            elif self.driver.paramstyle == 'named':
                cur.executemany(
                    'insert into %sbooze values (:beer)' % self.table_prefix,
                    margs
                    )
            elif self.driver.paramstyle == 'format':
                cur.executemany(
                    'insert into %sbooze values (%%s)' % self.table_prefix,
                    largs
                    )
            elif self.driver.paramstyle == 'pyformat':
                cur.executemany(
                    'insert into %sbooze values (%%(beer)s)' % (
                        self.table_prefix), margs)
            else:
                self.fail('Unknown paramstyle')
            self.assertEqual(
                cur.rowcount in (-1, 2), True,
                'insert using cursor.executemany set cursor.rowcount to '
                'incorrect value %r' % cur.rowcount)
            cur.execute('select name from %sbooze' % self.table_prefix)
            res = cur.fetchall()
            self.assertEqual(
                len(res), 2,
                'cursor.fetchall retrieved incorrect number of rows')
            beers = [res[0][0], res[1][0]]
            beers.sort()
            self.assertEqual(beers[0], "Boag's", 'incorrect data retrieved')
            self.assertEqual(beers[1], "Cooper's", 'incorrect data retrieved')
        finally:
            con.close()

    def test_fetchone(self):
        con = self._connect()
        try:
            cur = con.cursor()

            # cursor.fetchone should raise an Error if called before
            # executing a select-type query
            self.assertRaises(self.driver.Error, cur.fetchone)

            # cursor.fetchone should raise an Error if called after
            # executing a query that cannnot return rows
            self.executeDDL1(cur)
            self.assertRaises(self.driver.Error, cur.fetchone)

            cur.execute('select name from %sbooze' % self.table_prefix)
            self.assertEqual(
                cur.fetchone(), None,
                'cursor.fetchone should return None if a query retrieves '
                'no rows')
            self.assertEqual(cur.rowcount in (-1, 0), True)

            # cursor.fetchone should raise an Error if called after
            # executing a query that cannnot return rows
            cur.execute(
                "insert into %sbooze values ('Victoria Bitter')" % (
                    self.table_prefix))
            self.assertRaises(self.driver.Error, cur.fetchone)

            cur.execute('select name from %sbooze' % self.table_prefix)
            r = cur.fetchone()
            self.assertEqual(
                len(r), 1,
                'cursor.fetchone should have retrieved a single row')
            self.assertEqual(
                r[0], 'Victoria Bitter',
                'cursor.fetchone retrieved incorrect data')
            self.assertEqual(
                cur.fetchone(), None,
                'cursor.fetchone should return None if no more rows available')
            self.assertEqual(cur.rowcount in (-1, 1), True)
        finally:
            con.close()

    samples = [
        'Carlton Cold',
        'Carlton Draft',
        'Mountain Goat',
        'Redback',
        'Victoria Bitter',
        'XXXX'
        ]

    def _populate(self):
        ''' Return a list of sql commands to setup the DB for the fetch
            tests.
        '''
        populate = [
            "insert into %sbooze values ('%s')" % (self.table_prefix, s)
            for s in self.samples]
        return populate

    def test_fetchmany(self):
        con = self._connect()
        try:
            cur = con.cursor()

            # cursor.fetchmany should raise an Error if called without
            # issuing a query
            self.assertRaises(self.driver.Error, cur.fetchmany, 4)

            self.executeDDL1(cur)
            for sql in self._populate():
                cur.execute(sql)

            cur.execute('select name from %sbooze' % self.table_prefix)
            r = cur.fetchmany()
            self.assertEqual(
                len(r), 1,
                'cursor.fetchmany retrieved incorrect number of rows, '
                'default of arraysize is one.')
            cur.arraysize = 10
            r = cur.fetchmany(3)  # Should get 3 rows
            self.assertEqual(
                len(r), 3,
                'cursor.fetchmany retrieved incorrect number of rows')
            r = cur.fetchmany(4)  # Should get 2 more
            self.assertEqual(
                len(r), 2,
                'cursor.fetchmany retrieved incorrect number of rows')
            r = cur.fetchmany(4)  # Should be an empty sequence
            self.assertEqual(
                len(r), 0,
                'cursor.fetchmany should return an empty sequence after '
                'results are exhausted')
            self.assertEqual(cur.rowcount in (-1, 6), True)

            # Same as above, using cursor.arraysize
            cur.arraysize = 4
            cur.execute('select name from %sbooze' % self.table_prefix)
            r = cur.fetchmany()  # Should get 4 rows
            self.assertEqual(
                len(r), 4,
                'cursor.arraysize not being honoured by fetchmany')
            r = cur.fetchmany()  # Should get 2 more
            self.assertEqual(len(r), 2)
            r = cur.fetchmany()  # Should be an empty sequence
            self.assertEqual(len(r), 0)
            self.assertEqual(cur.rowcount in (-1, 6), True)

            cur.arraysize = 6
            cur.execute('select name from %sbooze' % self.table_prefix)
            rows = cur.fetchmany()  # Should get all rows
            self.assertEqual(cur.rowcount in (-1, 6), True)
            self.assertEqual(len(rows), 6)
            self.assertEqual(len(rows), 6)
            rows = [row[0] for row in rows]
            rows.sort()

            # Make sure we get the right data back out
            for i in range(0, 6):
                self.assertEqual(
                    rows[i], self.samples[i],
                    'incorrect data retrieved by cursor.fetchmany')

            rows = cur.fetchmany()  # Should return an empty list
            self.assertEqual(
                len(rows), 0,
                'cursor.fetchmany should return an empty sequence if '
                'called after the whole result set has been fetched')
            self.assertEqual(cur.rowcount in (-1, 6), True)

            self.executeDDL2(cur)
            cur.execute('select name from %sbarflys' % self.table_prefix)
            r = cur.fetchmany()  # Should get empty sequence
            self.assertEqual(
                len(r), 0,
                'cursor.fetchmany should return an empty sequence if '
                'query retrieved no rows')
            self.assertEqual(cur.rowcount in (-1, 0), True)

        finally:
            con.close()

    def test_fetchall(self):
        con = self._connect()
        try:
            cur = con.cursor()
            # cursor.fetchall should raise an Error if called
            # without executing a query that may return rows (such
            # as a select)
            self.assertRaises(self.driver.Error, cur.fetchall)

            self.executeDDL1(cur)
            for sql in self._populate():
                cur.execute(sql)

            # cursor.fetchall should raise an Error if called
            # after executing a a statement that cannot return rows
            self.assertRaises(self.driver.Error, cur.fetchall)

            cur.execute('select name from %sbooze' % self.table_prefix)
            rows = cur.fetchall()
            self.assertEqual(cur.rowcount in (-1, len(self.samples)), True)
            self.assertEqual(
                len(rows), len(self.samples),
                'cursor.fetchall did not retrieve all rows')
            rows = [r[0] for r in rows]
            rows.sort()
            for i in range(0, len(self.samples)):
                self.assertEqual(
                    rows[i], self.samples[i],
                    'cursor.fetchall retrieved incorrect rows')
            rows = cur.fetchall()
            self.assertEqual(
                len(rows), 0,
                'cursor.fetchall should return an empty list if called '
                'after the whole result set has been fetched')
            self.assertEqual(cur.rowcount in (-1, len(self.samples)), True)

            self.executeDDL2(cur)
            cur.execute('select name from %sbarflys' % self.table_prefix)
            rows = cur.fetchall()
            self.assertEqual(cur.rowcount in (-1, 0), True)
            self.assertEqual(
                len(rows), 0,
                'cursor.fetchall should return an empty list if '
                'a select query returns no rows')

        finally:
            con.close()

    def test_mixedfetch(self):
        con = self._connect()
        try:
            cur = con.cursor()
            self.executeDDL1(cur)
            for sql in self._populate():
                cur.execute(sql)

            cur.execute('select name from %sbooze' % self.table_prefix)
            rows1 = cur.fetchone()
            rows23 = cur.fetchmany(2)
            rows4 = cur.fetchone()
            rows56 = cur.fetchall()
            self.assertEqual(cur.rowcount in (-1, 6), True)
            self.assertEqual(
                len(rows23), 2, 'fetchmany returned incorrect number of rows')
            self.assertEqual(
                len(rows56), 2, 'fetchall returned incorrect number of rows')

            rows = [rows1[0]]
            rows.extend([rows23[0][0], rows23[1][0]])
            rows.append(rows4[0])
            rows.extend([rows56[0][0], rows56[1][0]])
            rows.sort()
            for i in range(0, len(self.samples)):
                self.assertEqual(
                    rows[i], self.samples[i],
                    'incorrect data retrieved or inserted')
        finally:
            con.close()

    def help_nextset_setUp(self, cur):
        ''' Should create a procedure called deleteme
            that returns two result sets, first the
            number of rows in booze then "name from booze"
        '''
        raise NotImplementedError('Helper not implemented')

    def help_nextset_tearDown(self, cur):
        'If cleaning up is needed after nextSetTest'
        raise NotImplementedError('Helper not implemented')

    def test_nextset(self):
        con = self._connect()
        try:
            cur = con.cursor()
            if not hasattr(cur, 'nextset'):
                return

            try:
                self.executeDDL1(cur)
                sql = self._populate()
                for sql in self._populate():
                    cur.execute(sql)

                self.help_nextset_setUp(cur)

                cur.callproc('deleteme')
                numberofrows = cur.fetchone()
                assert numberofrows[0] == len(self.samples)
                assert cur.nextset()
                names = cur.fetchall()
                assert len(names) == len(self.samples)
                s = cur.nextset()
                assert s is None, 'No more return sets, should return None'
            finally:
                self.help_nextset_tearDown(cur)

        finally:
            con.close()

    '''
    def test_nextset(self):
        raise NotImplementedError('Drivers need to override this test')
    '''

    def test_arraysize(self):
        # Not much here - rest of the tests for this are in test_fetchmany
        con = self._connect()
        try:
            cur = con.cursor()
            self.assertEqual(
                hasattr(cur, 'arraysize'), True,
                'cursor.arraysize must be defined')
        finally:
            con.close()

    def test_setinputsizes(self):
        con = self._connect()
        try:
            cur = con.cursor()
            cur.setinputsizes((25,))
            self._paraminsert(cur)  # Make sure cursor still works
        finally:
            con.close()

    def test_setoutputsize_basic(self):
        # Basic test is to make sure setoutputsize doesn't blow up
        con = self._connect()
        try:
            cur = con.cursor()
            cur.setoutputsize(1000)
            cur.setoutputsize(2000, 0)
            self._paraminsert(cur)  # Make sure the cursor still works
        finally:
            con.close()

    def test_setoutputsize(self):
        # Real test for setoutputsize is driver dependant
        raise NotImplementedError('Driver need to override this test')

    def test_None(self):
        con = self._connect()
        try:
            cur = con.cursor()
            self.executeDDL1(cur)
            cur.execute(
                'insert into %sbooze values (NULL)' % self.table_prefix)
            cur.execute('select name from %sbooze' % self.table_prefix)
            r = cur.fetchall()
            self.assertEqual(len(r), 1)
            self.assertEqual(len(r[0]), 1)
            self.assertEqual(r[0][0], None, 'NULL value not returned as None')
        finally:
            con.close()

    def test_Date(self):
        self.driver.Date(2002, 12, 25)
        self.driver.DateFromTicks(
            time.mktime((2002, 12, 25, 0, 0, 0, 0, 0, 0)))
        # Can we assume this? API doesn't specify, but it seems implied
        # self.assertEqual(str(d1),str(d2))

    def test_Time(self):
        self.driver.Time(13, 45, 30)
        self.driver.TimeFromTicks(
            time.mktime((2001, 1, 1, 13, 45, 30, 0, 0, 0)))
        # Can we assume this? API doesn't specify, but it seems implied
        # self.assertEqual(str(t1),str(t2))

    def test_Timestamp(self):
        self.driver.Timestamp(2002, 12, 25, 13, 45, 30)
        self.driver.TimestampFromTicks(
            time.mktime((2002, 12, 25, 13, 45, 30, 0, 0, 0)))
        # Can we assume this? API doesn't specify, but it seems implied
        # self.assertEqual(str(t1),str(t2))

    def test_Binary(self):
        self.driver.Binary(b('Something'))
        self.driver.Binary(b(''))

    def test_STRING(self):
        self.assertEqual(
            hasattr(self.driver, 'STRING'), True,
            'module.STRING must be defined')

    def test_BINARY(self):
        self.assertEqual(
            hasattr(self.driver, 'BINARY'), True,
            'module.BINARY must be defined.')

    def test_NUMBER(self):
        self.assertTrue(
            hasattr(self.driver, 'NUMBER'), 'module.NUMBER must be defined.')

    def test_DATETIME(self):
        self.assertEqual(
            hasattr(self.driver, 'DATETIME'), True,
            'module.DATETIME must be defined.')

    def test_ROWID(self):
        self.assertEqual(
            hasattr(self.driver, 'ROWID'), True,
            'module.ROWID must be defined.')

########NEW FILE########
__FILENAME__ = performance
import pg8000
from pg8000.tests.connection_settings import db_connect
import time
import warnings
from contextlib import closing
from decimal import Decimal


whole_begin_time = time.time()

tests = (
        ("cast(id / 100 as int2)", 'int2'),
        ("cast(id as int4)", 'int4'),
        ("cast(id * 100 as int8)", 'int8'),
        ("(id %% 2) = 0", 'bool'),
        ("N'Static text string'", 'txt'),
        ("cast(id / 100 as float4)", 'float4'),
        ("cast(id / 100 as float8)", 'float8'),
        ("cast(id / 100 as numeric)", 'numeric'),
        ("timestamp '2001-09-28' + id * interval '1 second'", 'timestamp'),
)

with warnings.catch_warnings(), closing(pg8000.connect(**db_connect)) as db:
    for txt, name in tests:
        query = """SELECT {0} AS column1, {0} AS column2, {0} AS column3,
            {0} AS column4, {0} AS column5, {0} AS column6, {0} AS column7
            FROM (SELECT generate_series(1, 10000) AS id) AS tbl""".format(txt)
        cursor = db.cursor()
        print("Beginning %s test..." % name)
        for i in range(1, 5):
            begin_time = time.time()
            cursor.execute(query)
            for row in cursor:
                pass
            end_time = time.time()
            print("Attempt %s - %s seconds." % (i, end_time - begin_time))
    db.commit()
    cursor = db.cursor()
    cursor.execute(
        "CREATE TEMPORARY TABLE t1 (f1 serial primary key, "
        "f2 bigint not null, f3 varchar(50) null, f4 bool)")
    db.commit()
    params = [(Decimal('7.4009'), 'season of mists...', True)] * 1000
    print("Beginning executemany test...")
    for i in range(1, 5):
        begin_time = time.time()
        cursor.executemany(
            "insert into t1 (f2, f3, f4) values (%s, %s, %s)", params)
        db.commit()
        end_time = time.time()
        print("Attempt {0} took {1} seconds.".format(i, end_time - begin_time))

    print("Beginning reuse statements test...")
    begin_time = time.time()
    for i in range(2000):
        cursor.execute("select count(*) from t1")
        cursor.fetchall()
    print("Took {0} seconds.".format(time.time() - begin_time))

print("Whole time - %s seconds." % (time.time() - whole_begin_time))

########NEW FILE########
__FILENAME__ = connection_settings
import os


db_stewart_connect = {
    "host": "127.0.0.1",
    "user": "pg8000-test",
    "database": "pg8000-test",
    "password": "pg8000-test",
    "socket_timeout": 5,
    "ssl": False}

db_local_connect = {
    "unix_sock": "/tmp/.s.PGSQL.5432",
    "user": "mfenniak"}

db_local_win_connect = {
    "host": "localhost",
    "user": "mfenniak",
    "password": "password",
    "database": "mfenniak"}

db_oracledev2_connect = {
    "host": "oracledev2",
    "user": "mfenniak",
    "password": "password",
    "database": "mfenniak"}

db_connect = eval(os.environ["PG8000_TEST"])
try:
    from testconfig import config
    try:
        db_connect['use_cache'] = config['use_cache'] == 'true'
    except KeyError:
        pass
except:
    # This means we're using Python 2.5 which is a special case.
    pass

########NEW FILE########
__FILENAME__ = dbapi20
#!/usr/bin/env python
''' Python DB API 2.0 driver compliance unit test suite.

    This software is Public Domain and may be used without restrictions.

 "Now we have booze and barflies entering the discussion, plus rumours of
  DBAs on drugs... and I won't tell you what flashes through my mind each
  time I read the subject line with 'Anal Compliance' in it.  All around
  this is turning out to be a thoroughly unwholesome unit test."

    -- Ian Bicking
'''

__rcs_id__ = '$Id: dbapi20.py,v 1.10 2003/10/09 03:14:14 zenzen Exp $'
__version__ = '$Revision: 1.10 $'[11:-2]
__author__ = 'Stuart Bishop <zen@shangri-la.dropbear.id.au>'

import unittest
import time
import warnings
from pg8000.six import b

# $Log: dbapi20.py,v $
# Revision 1.10  2003/10/09 03:14:14  zenzen
# Add test for DB API 2.0 optional extension, where database exceptions
# are exposed as attributes on the Connection object.
#
# Revision 1.9  2003/08/13 01:16:36  zenzen
# Minor tweak from Stefan Fleiter
#
# Revision 1.8  2003/04/10 00:13:25  zenzen
# Changes, as per suggestions by M.-A. Lemburg
# - Add a table prefix, to ensure namespace collisions can always be avoided
#
# Revision 1.7  2003/02/26 23:33:37  zenzen
# Break out DDL into helper functions, as per request by David Rushby
#
# Revision 1.6  2003/02/21 03:04:33  zenzen
# Stuff from Henrik Ekelund:
#     added test_None
#     added test_nextset & hooks
#
# Revision 1.5  2003/02/17 22:08:43  zenzen
# Implement suggestions and code from Henrik Eklund - test that
# cursor.arraysize defaults to 1 & generic cursor.callproc test added
#
# Revision 1.4  2003/02/15 00:16:33  zenzen
# Changes, as per suggestions and bug reports by M.-A. Lemburg,
# Matthew T. Kromer, Federico Di Gregorio and Daniel Dittmar
# - Class renamed
# - Now a subclass of TestCase, to avoid requiring the driver stub
#   to use multiple inheritance
# - Reversed the polarity of buggy test in test_description
# - Test exception heirarchy correctly
# - self.populate is now self._populate(), so if a driver stub
#   overrides self.ddl1 this change propogates
# - VARCHAR columns now have a width, which will hopefully make the
#   DDL even more portible (this will be reversed if it causes more problems)
# - cursor.rowcount being checked after various execute and fetchXXX methods
# - Check for fetchall and fetchmany returning empty lists after results
#   are exhausted (already checking for empty lists if select retrieved
#   nothing
# - Fix bugs in test_setoutputsize_basic and test_setinputsizes
#


class DatabaseAPI20Test(unittest.TestCase):
    ''' Test a database self.driver for DB API 2.0 compatibility.
        This implementation tests Gadfly, but the TestCase
        is structured so that other self.drivers can subclass this
        test case to ensure compiliance with the DB-API. It is
        expected that this TestCase may be expanded in the future
        if ambiguities or edge conditions are discovered.

        The 'Optional Extensions' are not yet being tested.

        self.drivers should subclass this test, overriding setUp, tearDown,
        self.driver, connect_args and connect_kw_args. Class specification
        should be as follows:

        import dbapi20
        class mytest(dbapi20.DatabaseAPI20Test):
           [...]

        Don't 'import DatabaseAPI20Test from dbapi20', or you will
        confuse the unit tester - just 'import dbapi20'.
    '''

    # The self.driver module. This should be the module where the 'connect'
    # method is to be found
    driver = None
    connect_args = ()  # List of arguments to pass to connect
    connect_kw_args = {}  # Keyword arguments for connect
    table_prefix = 'dbapi20test_'  # If you need to specify a prefix for tables

    ddl1 = 'create table %sbooze (name varchar(20))' % table_prefix
    ddl2 = 'create table %sbarflys (name varchar(20))' % table_prefix
    xddl1 = 'drop table %sbooze' % table_prefix
    xddl2 = 'drop table %sbarflys' % table_prefix

    # Name of stored procedure to convert
    # string->lowercase
    lowerfunc = 'lower'

    # Some drivers may need to override these helpers, for example adding
    # a 'commit' after the execute.
    def executeDDL1(self, cursor):
        cursor.execute(self.ddl1)

    def executeDDL2(self, cursor):
        cursor.execute(self.ddl2)

    def setUp(self):
        ''' self.drivers should override this method to perform required setup
            if any is necessary, such as creating the database.
        '''
        pass

    def tearDown(self):
        ''' self.drivers should override this method to perform required
            cleanup if any is necessary, such as deleting the test database.
            The default drops the tables that may be created.
        '''
        con = self._connect()
        try:
            cur = con.cursor()
            for ddl in (self.xddl1, self.xddl2):
                try:
                    cur.execute(ddl)
                    con.commit()
                except self.driver.Error:
                    # Assume table didn't exist. Other tests will check if
                    # execute is busted.
                    pass
        finally:
            con.close()

    def _connect(self):
        try:
            return self.driver.connect(
                *self.connect_args, **self.connect_kw_args)
        except AttributeError:
            self.fail("No connect method found in self.driver module")

    def test_connect(self):
        con = self._connect()
        con.close()

    def test_apilevel(self):
        try:
            # Must exist
            apilevel = self.driver.apilevel
            # Must equal 2.0
            self.assertEqual(apilevel, '2.0')
        except AttributeError:
            self.fail("Driver doesn't define apilevel")

    def test_threadsafety(self):
        try:
            # Must exist
            threadsafety = self.driver.threadsafety
            # Must be a valid value
            self.assertEqual(threadsafety in (0, 1, 2, 3), True)
        except AttributeError:
            self.fail("Driver doesn't define threadsafety")

    def test_paramstyle(self):
        try:
            # Must exist
            paramstyle = self.driver.paramstyle
            # Must be a valid value
            self.assertEqual(
                paramstyle in (
                    'qmark', 'numeric', 'named', 'format', 'pyformat'), True)
        except AttributeError:
            self.fail("Driver doesn't define paramstyle")

    def test_Exceptions(self):
        # Make sure required exceptions exist, and are in the
        # defined heirarchy.
        self.assertEqual(issubclass(self.driver.Warning, Exception), True)
        self.assertEqual(issubclass(self.driver.Error, Exception), True)
        self.assertEqual(
            issubclass(self.driver.InterfaceError, self.driver.Error), True)
        self.assertEqual(
            issubclass(self.driver.DatabaseError, self.driver.Error), True)
        self.assertEqual(
            issubclass(self.driver.OperationalError, self.driver.Error), True)
        self.assertEqual(
            issubclass(self.driver.IntegrityError, self.driver.Error), True)
        self.assertEqual(
            issubclass(self.driver.InternalError, self.driver.Error), True)
        self.assertEqual(
            issubclass(self.driver.ProgrammingError, self.driver.Error), True)
        self.assertEqual(
            issubclass(self.driver.NotSupportedError, self.driver.Error), True)

    def test_ExceptionsAsConnectionAttributes(self):
        # OPTIONAL EXTENSION
        # Test for the optional DB API 2.0 extension, where the exceptions
        # are exposed as attributes on the Connection object
        # I figure this optional extension will be implemented by any
        # driver author who is using this test suite, so it is enabled
        # by default.
        warnings.simplefilter("ignore")
        con = self._connect()
        drv = self.driver
        self.assertEqual(con.Warning is drv.Warning, True)
        self.assertEqual(con.Error is drv.Error, True)
        self.assertEqual(con.InterfaceError is drv.InterfaceError, True)
        self.assertEqual(con.DatabaseError is drv.DatabaseError, True)
        self.assertEqual(con.OperationalError is drv.OperationalError, True)
        self.assertEqual(con.IntegrityError is drv.IntegrityError, True)
        self.assertEqual(con.InternalError is drv.InternalError, True)
        self.assertEqual(con.ProgrammingError is drv.ProgrammingError, True)
        self.assertEqual(con.NotSupportedError is drv.NotSupportedError, True)
        warnings.resetwarnings()
        con.close()

    def test_commit(self):
        con = self._connect()
        try:
            # Commit must work, even if it doesn't do anything
            con.commit()
        finally:
            con.close()

    def test_rollback(self):
        con = self._connect()
        # If rollback is defined, it should either work or throw
        # the documented exception
        if hasattr(con, 'rollback'):
            try:
                con.rollback()
            except self.driver.NotSupportedError:
                pass
        con.close()

    def test_cursor(self):
        con = self._connect()
        try:
            con.cursor()
        finally:
            con.close()

    def test_cursor_isolation(self):
        con = self._connect()
        try:
            # Make sure cursors created from the same connection have
            # the documented transaction isolation level
            cur1 = con.cursor()
            cur2 = con.cursor()
            self.executeDDL1(cur1)
            cur1.execute(
                "insert into %sbooze values ('Victoria Bitter')" % (
                    self.table_prefix))
            cur2.execute("select name from %sbooze" % self.table_prefix)
            booze = cur2.fetchall()
            self.assertEqual(len(booze), 1)
            self.assertEqual(len(booze[0]), 1)
            self.assertEqual(booze[0][0], 'Victoria Bitter')
        finally:
            con.close()

    def test_description(self):
        con = self._connect()
        try:
            cur = con.cursor()
            self.executeDDL1(cur)
            self.assertEqual(
                cur.description, None,
                'cursor.description should be none after executing a '
                'statement that can return no rows (such as DDL)')
            cur.execute('select name from %sbooze' % self.table_prefix)
            self.assertEqual(
                len(cur.description), 1,
                'cursor.description describes too many columns')
            self.assertEqual(
                len(cur.description[0]), 7,
                'cursor.description[x] tuples must have 7 elements')
            self.assertEqual(
                cur.description[0][0].lower(), b('name'),
                'cursor.description[x][0] must return column name')
            self.assertEqual(
                cur.description[0][1], self.driver.STRING,
                'cursor.description[x][1] must return column type. Got %r'
                % cur.description[0][1])

            # Make sure self.description gets reset
            self.executeDDL2(cur)
            self.assertEqual(
                cur.description, None,
                'cursor.description not being set to None when executing '
                'no-result statements (eg. DDL)')
        finally:
            con.close()

    def test_rowcount(self):
        con = self._connect()
        try:
            cur = con.cursor()
            self.executeDDL1(cur)
            self.assertEqual(
                cur.rowcount, -1,
                'cursor.rowcount should be -1 after executing no-result '
                'statements')
            cur.execute(
                "insert into %sbooze values ('Victoria Bitter')" % (
                    self.table_prefix))
            self.assertEqual(
                cur.rowcount in (-1, 1), True,
                'cursor.rowcount should == number or rows inserted, or '
                'set to -1 after executing an insert statement')
            cur.execute("select name from %sbooze" % self.table_prefix)
            self.assertEqual(
                cur.rowcount in (-1, 1), True,
                'cursor.rowcount should == number of rows returned, or '
                'set to -1 after executing a select statement')
            self.executeDDL2(cur)
            self.assertEqual(
                cur.rowcount, -1,
                'cursor.rowcount not being reset to -1 after executing '
                'no-result statements')
        finally:
            con.close()

    lower_func = 'lower'

    def test_callproc(self):
        con = self._connect()
        try:
            cur = con.cursor()
            if self.lower_func and hasattr(cur, 'callproc'):
                r = cur.callproc(self.lower_func, ('FOO',))
                self.assertEqual(len(r), 1)
                self.assertEqual(r[0], 'FOO')
                r = cur.fetchall()
                self.assertEqual(len(r), 1, 'callproc produced no result set')
                self.assertEqual(
                    len(r[0]), 1, 'callproc produced invalid result set')
                self.assertEqual(
                    r[0][0], 'foo', 'callproc produced invalid results')
        finally:
            con.close()

    def test_close(self):
        con = self._connect()
        try:
            cur = con.cursor()
        finally:
            con.close()

        # cursor.execute should raise an Error if called after connection
        # closed
        self.assertRaises(self.driver.Error, self.executeDDL1, cur)

        # connection.commit should raise an Error if called after connection'
        # closed.'
        self.assertRaises(self.driver.Error, con.commit)

        # connection.close should raise an Error if called more than once
        self.assertRaises(self.driver.Error, con.close)

    def test_execute(self):
        con = self._connect()
        try:
            cur = con.cursor()
            self._paraminsert(cur)
        finally:
            con.close()

    def _paraminsert(self, cur):
        self.executeDDL1(cur)
        cur.execute("insert into %sbooze values ('Victoria Bitter')" % (
            self.table_prefix))
        self.assertEqual(cur.rowcount in (-1, 1), True)

        if self.driver.paramstyle == 'qmark':
            cur.execute(
                'insert into %sbooze values (?)' % self.table_prefix,
                ("Cooper's",))
        elif self.driver.paramstyle == 'numeric':
            cur.execute(
                'insert into %sbooze values (:1)' % self.table_prefix,
                ("Cooper's",))
        elif self.driver.paramstyle == 'named':
            cur.execute(
                'insert into %sbooze values (:beer)' % self.table_prefix,
                {'beer': "Cooper's"})
        elif self.driver.paramstyle == 'format':
            cur.execute(
                'insert into %sbooze values (%%s)' % self.table_prefix,
                ("Cooper's",))
        elif self.driver.paramstyle == 'pyformat':
            cur.execute(
                'insert into %sbooze values (%%(beer)s)' % self.table_prefix,
                {'beer': "Cooper's"})
        else:
            self.fail('Invalid paramstyle')
        self.assertEqual(cur.rowcount in (-1, 1), True)

        cur.execute('select name from %sbooze' % self.table_prefix)
        res = cur.fetchall()
        self.assertEqual(
            len(res), 2, 'cursor.fetchall returned too few rows')
        beers = [res[0][0], res[1][0]]
        beers.sort()
        self.assertEqual(
            beers[0], "Cooper's",
            'cursor.fetchall retrieved incorrect data, or data inserted '
            'incorrectly')
        self.assertEqual(
            beers[1], "Victoria Bitter",
            'cursor.fetchall retrieved incorrect data, or data inserted '
            'incorrectly')

    def test_executemany(self):
        con = self._connect()
        try:
            cur = con.cursor()
            self.executeDDL1(cur)
            largs = [("Cooper's",), ("Boag's",)]
            margs = [{'beer': "Cooper's"}, {'beer': "Boag's"}]
            if self.driver.paramstyle == 'qmark':
                cur.executemany(
                    'insert into %sbooze values (?)' % self.table_prefix,
                    largs
                    )
            elif self.driver.paramstyle == 'numeric':
                cur.executemany(
                    'insert into %sbooze values (:1)' % self.table_prefix,
                    largs
                    )
            elif self.driver.paramstyle == 'named':
                cur.executemany(
                    'insert into %sbooze values (:beer)' % self.table_prefix,
                    margs
                    )
            elif self.driver.paramstyle == 'format':
                cur.executemany(
                    'insert into %sbooze values (%%s)' % self.table_prefix,
                    largs
                    )
            elif self.driver.paramstyle == 'pyformat':
                cur.executemany(
                    'insert into %sbooze values (%%(beer)s)' % (
                        self.table_prefix), margs)
            else:
                self.fail('Unknown paramstyle')
            self.assertEqual(
                cur.rowcount in (-1, 2), True,
                'insert using cursor.executemany set cursor.rowcount to '
                'incorrect value %r' % cur.rowcount)
            cur.execute('select name from %sbooze' % self.table_prefix)
            res = cur.fetchall()
            self.assertEqual(
                len(res), 2,
                'cursor.fetchall retrieved incorrect number of rows')
            beers = [res[0][0], res[1][0]]
            beers.sort()
            self.assertEqual(beers[0], "Boag's", 'incorrect data retrieved')
            self.assertEqual(beers[1], "Cooper's", 'incorrect data retrieved')
        finally:
            con.close()

    def test_fetchone(self):
        con = self._connect()
        try:
            cur = con.cursor()

            # cursor.fetchone should raise an Error if called before
            # executing a select-type query
            self.assertRaises(self.driver.Error, cur.fetchone)

            # cursor.fetchone should raise an Error if called after
            # executing a query that cannnot return rows
            self.executeDDL1(cur)
            self.assertRaises(self.driver.Error, cur.fetchone)

            cur.execute('select name from %sbooze' % self.table_prefix)
            self.assertEqual(
                cur.fetchone(), None,
                'cursor.fetchone should return None if a query retrieves '
                'no rows')
            self.assertEqual(cur.rowcount in (-1, 0), True)

            # cursor.fetchone should raise an Error if called after
            # executing a query that cannnot return rows
            cur.execute(
                "insert into %sbooze values ('Victoria Bitter')" % (
                    self.table_prefix))
            self.assertRaises(self.driver.Error, cur.fetchone)

            cur.execute('select name from %sbooze' % self.table_prefix)
            r = cur.fetchone()
            self.assertEqual(
                len(r), 1,
                'cursor.fetchone should have retrieved a single row')
            self.assertEqual(
                r[0], 'Victoria Bitter',
                'cursor.fetchone retrieved incorrect data')
            self.assertEqual(
                cur.fetchone(), None,
                'cursor.fetchone should return None if no more rows available')
            self.assertEqual(cur.rowcount in (-1, 1), True)
        finally:
            con.close()

    samples = [
        'Carlton Cold',
        'Carlton Draft',
        'Mountain Goat',
        'Redback',
        'Victoria Bitter',
        'XXXX'
        ]

    def _populate(self):
        ''' Return a list of sql commands to setup the DB for the fetch
            tests.
        '''
        populate = [
            "insert into %sbooze values ('%s')" % (self.table_prefix, s)
            for s in self.samples]
        return populate

    def test_fetchmany(self):
        con = self._connect()
        try:
            cur = con.cursor()

            # cursor.fetchmany should raise an Error if called without
            # issuing a query
            self.assertRaises(self.driver.Error, cur.fetchmany, 4)

            self.executeDDL1(cur)
            for sql in self._populate():
                cur.execute(sql)

            cur.execute('select name from %sbooze' % self.table_prefix)
            r = cur.fetchmany()
            self.assertEqual(
                len(r), 1,
                'cursor.fetchmany retrieved incorrect number of rows, '
                'default of arraysize is one.')
            cur.arraysize = 10
            r = cur.fetchmany(3)  # Should get 3 rows
            self.assertEqual(
                len(r), 3,
                'cursor.fetchmany retrieved incorrect number of rows')
            r = cur.fetchmany(4)  # Should get 2 more
            self.assertEqual(
                len(r), 2,
                'cursor.fetchmany retrieved incorrect number of rows')
            r = cur.fetchmany(4)  # Should be an empty sequence
            self.assertEqual(
                len(r), 0,
                'cursor.fetchmany should return an empty sequence after '
                'results are exhausted')
            self.assertEqual(cur.rowcount in (-1, 6), True)

            # Same as above, using cursor.arraysize
            cur.arraysize = 4
            cur.execute('select name from %sbooze' % self.table_prefix)
            r = cur.fetchmany()  # Should get 4 rows
            self.assertEqual(
                len(r), 4,
                'cursor.arraysize not being honoured by fetchmany')
            r = cur.fetchmany()  # Should get 2 more
            self.assertEqual(len(r), 2)
            r = cur.fetchmany()  # Should be an empty sequence
            self.assertEqual(len(r), 0)
            self.assertEqual(cur.rowcount in (-1, 6), True)

            cur.arraysize = 6
            cur.execute('select name from %sbooze' % self.table_prefix)
            rows = cur.fetchmany()  # Should get all rows
            self.assertEqual(cur.rowcount in (-1, 6), True)
            self.assertEqual(len(rows), 6)
            self.assertEqual(len(rows), 6)
            rows = [row[0] for row in rows]
            rows.sort()

            # Make sure we get the right data back out
            for i in range(0, 6):
                self.assertEqual(
                    rows[i], self.samples[i],
                    'incorrect data retrieved by cursor.fetchmany')

            rows = cur.fetchmany()  # Should return an empty list
            self.assertEqual(
                len(rows), 0,
                'cursor.fetchmany should return an empty sequence if '
                'called after the whole result set has been fetched')
            self.assertEqual(cur.rowcount in (-1, 6), True)

            self.executeDDL2(cur)
            cur.execute('select name from %sbarflys' % self.table_prefix)
            r = cur.fetchmany()  # Should get empty sequence
            self.assertEqual(
                len(r), 0,
                'cursor.fetchmany should return an empty sequence if '
                'query retrieved no rows')
            self.assertEqual(cur.rowcount in (-1, 0), True)

        finally:
            con.close()

    def test_fetchall(self):
        con = self._connect()
        try:
            cur = con.cursor()
            # cursor.fetchall should raise an Error if called
            # without executing a query that may return rows (such
            # as a select)
            self.assertRaises(self.driver.Error, cur.fetchall)

            self.executeDDL1(cur)
            for sql in self._populate():
                cur.execute(sql)

            # cursor.fetchall should raise an Error if called
            # after executing a a statement that cannot return rows
            self.assertRaises(self.driver.Error, cur.fetchall)

            cur.execute('select name from %sbooze' % self.table_prefix)
            rows = cur.fetchall()
            self.assertEqual(cur.rowcount in (-1, len(self.samples)), True)
            self.assertEqual(
                len(rows), len(self.samples),
                'cursor.fetchall did not retrieve all rows')
            rows = [r[0] for r in rows]
            rows.sort()
            for i in range(0, len(self.samples)):
                self.assertEqual(
                    rows[i], self.samples[i],
                    'cursor.fetchall retrieved incorrect rows')
            rows = cur.fetchall()
            self.assertEqual(
                len(rows), 0,
                'cursor.fetchall should return an empty list if called '
                'after the whole result set has been fetched')
            self.assertEqual(cur.rowcount in (-1, len(self.samples)), True)

            self.executeDDL2(cur)
            cur.execute('select name from %sbarflys' % self.table_prefix)
            rows = cur.fetchall()
            self.assertEqual(cur.rowcount in (-1, 0), True)
            self.assertEqual(
                len(rows), 0,
                'cursor.fetchall should return an empty list if '
                'a select query returns no rows')

        finally:
            con.close()

    def test_mixedfetch(self):
        con = self._connect()
        try:
            cur = con.cursor()
            self.executeDDL1(cur)
            for sql in self._populate():
                cur.execute(sql)

            cur.execute('select name from %sbooze' % self.table_prefix)
            rows1 = cur.fetchone()
            rows23 = cur.fetchmany(2)
            rows4 = cur.fetchone()
            rows56 = cur.fetchall()
            self.assertEqual(cur.rowcount in (-1, 6), True)
            self.assertEqual(
                len(rows23), 2, 'fetchmany returned incorrect number of rows')
            self.assertEqual(
                len(rows56), 2, 'fetchall returned incorrect number of rows')

            rows = [rows1[0]]
            rows.extend([rows23[0][0], rows23[1][0]])
            rows.append(rows4[0])
            rows.extend([rows56[0][0], rows56[1][0]])
            rows.sort()
            for i in range(0, len(self.samples)):
                self.assertEqual(
                    rows[i], self.samples[i],
                    'incorrect data retrieved or inserted')
        finally:
            con.close()

    def help_nextset_setUp(self, cur):
        ''' Should create a procedure called deleteme
            that returns two result sets, first the
            number of rows in booze then "name from booze"
        '''
        raise NotImplementedError('Helper not implemented')

    def help_nextset_tearDown(self, cur):
        'If cleaning up is needed after nextSetTest'
        raise NotImplementedError('Helper not implemented')

    def test_nextset(self):
        con = self._connect()
        try:
            cur = con.cursor()
            if not hasattr(cur, 'nextset'):
                return

            try:
                self.executeDDL1(cur)
                sql = self._populate()
                for sql in self._populate():
                    cur.execute(sql)

                self.help_nextset_setUp(cur)

                cur.callproc('deleteme')
                numberofrows = cur.fetchone()
                assert numberofrows[0] == len(self.samples)
                assert cur.nextset()
                names = cur.fetchall()
                assert len(names) == len(self.samples)
                s = cur.nextset()
                assert s is None, 'No more return sets, should return None'
            finally:
                self.help_nextset_tearDown(cur)

        finally:
            con.close()

    '''
    def test_nextset(self):
        raise NotImplementedError('Drivers need to override this test')
    '''

    def test_arraysize(self):
        # Not much here - rest of the tests for this are in test_fetchmany
        con = self._connect()
        try:
            cur = con.cursor()
            self.assertEqual(
                hasattr(cur, 'arraysize'), True,
                'cursor.arraysize must be defined')
        finally:
            con.close()

    def test_setinputsizes(self):
        con = self._connect()
        try:
            cur = con.cursor()
            cur.setinputsizes((25,))
            self._paraminsert(cur)  # Make sure cursor still works
        finally:
            con.close()

    def test_setoutputsize_basic(self):
        # Basic test is to make sure setoutputsize doesn't blow up
        con = self._connect()
        try:
            cur = con.cursor()
            cur.setoutputsize(1000)
            cur.setoutputsize(2000, 0)
            self._paraminsert(cur)  # Make sure the cursor still works
        finally:
            con.close()

    def test_setoutputsize(self):
        # Real test for setoutputsize is driver dependant
        raise NotImplementedError('Driver need to override this test')

    def test_None(self):
        con = self._connect()
        try:
            cur = con.cursor()
            self.executeDDL1(cur)
            cur.execute(
                'insert into %sbooze values (NULL)' % self.table_prefix)
            cur.execute('select name from %sbooze' % self.table_prefix)
            r = cur.fetchall()
            self.assertEqual(len(r), 1)
            self.assertEqual(len(r[0]), 1)
            self.assertEqual(r[0][0], None, 'NULL value not returned as None')
        finally:
            con.close()

    def test_Date(self):
        self.driver.Date(2002, 12, 25)
        self.driver.DateFromTicks(
            time.mktime((2002, 12, 25, 0, 0, 0, 0, 0, 0)))
        # Can we assume this? API doesn't specify, but it seems implied
        # self.assertEqual(str(d1),str(d2))

    def test_Time(self):
        self.driver.Time(13, 45, 30)
        self.driver.TimeFromTicks(
            time.mktime((2001, 1, 1, 13, 45, 30, 0, 0, 0)))
        # Can we assume this? API doesn't specify, but it seems implied
        # self.assertEqual(str(t1),str(t2))

    def test_Timestamp(self):
        self.driver.Timestamp(2002, 12, 25, 13, 45, 30)
        self.driver.TimestampFromTicks(
            time.mktime((2002, 12, 25, 13, 45, 30, 0, 0, 0)))
        # Can we assume this? API doesn't specify, but it seems implied
        # self.assertEqual(str(t1),str(t2))

    def test_Binary(self):
        self.driver.Binary(b('Something'))
        self.driver.Binary(b(''))

    def test_STRING(self):
        self.assertEqual(
            hasattr(self.driver, 'STRING'), True,
            'module.STRING must be defined')

    def test_BINARY(self):
        self.assertEqual(
            hasattr(self.driver, 'BINARY'), True,
            'module.BINARY must be defined.')

    def test_NUMBER(self):
        self.assertTrue(
            hasattr(self.driver, 'NUMBER'), 'module.NUMBER must be defined.')

    def test_DATETIME(self):
        self.assertEqual(
            hasattr(self.driver, 'DATETIME'), True,
            'module.DATETIME must be defined.')

    def test_ROWID(self):
        self.assertEqual(
            hasattr(self.driver, 'ROWID'), True,
            'module.ROWID must be defined.')

########NEW FILE########
__FILENAME__ = performance
from pg8000 import DBAPI
from .connection_settings import db_connect
import time
import warnings
from contextlib import closing
from decimal import Decimal


tests = (
        ("(id / 100)::int2", 'int2'),
        ("id::int4", 'int4'),
        ("(id * 100)::int8", 'int8'),
        ("(id %% 2) = 0", 'bool'),
        ("N'Static text string'", 'txt'),
        ("id / 100::float4", 'float4'),
        ("id / 100::float8", 'float8'),
        ("id / 100::numeric", 'numeric'),
)

with warnings.catch_warnings(), closing(DBAPI.connect(**db_connect)) as db:
    warnings.simplefilter("ignore")

    for txt, name in tests:
        query = """SELECT {0} AS column1, {0} AS column2, {0} AS column3,
            {0} AS column4, {0} AS column5, {0} AS column6, {0} AS column7
            FROM (SELECT generate_series(1, 10000) AS id) AS tbl""".format(txt)
        cursor = db.cursor()
        print("Beginning %s test..." % name)
        for i in range(1, 5):
            begin_time = time.time()
            cursor.execute(query)
            for row in cursor:
                pass
            end_time = time.time()
            print("Attempt %s - %s seconds." % (i, end_time - begin_time))
    db.commit()

    cursor = db.cursor()
    cursor.execute(
        "CREATE TEMPORARY TABLE t1 (f1 serial primary key, "
        "f2 bigint not null, f3 varchar(50) null, f4 bool)")
    db.commit()
    params = [(Decimal('7.4009'), 'season of mists...', True)] * 1000
    print("Beginning executemany test...")
    for i in range(1, 5):
        begin_time = time.time()
        cursor.executemany(
            "insert into t1 (f2, f3, f4) values (%s, %s, %s)", params)
        db.commit()
        end_time = time.time()
        print("Attempt {0} took {1} seconds.".format(i, end_time - begin_time))

########NEW FILE########
__FILENAME__ = test_connection
import unittest
from pg8000 import dbapi
from .connection_settings import db_connect
from pg8000.six import PY2, PRE_26


# Tests related to connecting to a database.
class Tests(unittest.TestCase):
    def testSocketMissing(self):
        self.assertRaises(
            dbapi.InterfaceError, dbapi.connect,
            unix_sock="/file-does-not-exist", user="doesn't-matter")

    def testDatabaseMissing(self):
        data = db_connect.copy()
        data["database"] = "missing-db"
        self.assertRaises(dbapi.ProgrammingError, dbapi.connect, **data)

    def testNotify(self):

        try:
            db = dbapi.connect(**db_connect)
            self.assertEqual(db.notifies, [])
            cursor = db.cursor()
            cursor.execute("LISTEN test")
            cursor.execute("NOTIFY test")
            db.commit()

            cursor.execute("VALUES (1, 2), (3, 4), (5, 6)")
            self.assertEqual(len(db.notifies), 1)
            self.assertEqual(db.notifies[0][1], "test")
        finally:
            cursor.close()
            db.close()

    # This requires a line in pg_hba.conf that requires md5 for the database
    # pg8000_md5

    def testMd5(self):
        data = db_connect.copy()
        data["database"] = "pg8000_md5"

        # Should only raise an exception saying db doesn't exist
        if PY2:
            self.assertRaises(
                dbapi.ProgrammingError, dbapi.connect, **data)
        else:
            self.assertRaisesRegex(
                dbapi.ProgrammingError, '3D000', dbapi.connect, **data)

    def testSsl(self):
        data = db_connect.copy()
        data["ssl"] = True
        if PRE_26:
            self.assertRaises(dbapi.InterfaceError, dbapi.connect, **data)
        else:
            db = dbapi.connect(**data)
            db.close()

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_copy
import unittest
from pg8000 import dbapi
from .connection_settings import db_connect
from pg8000.six import b, BytesIO
from sys import exc_info


class Tests(unittest.TestCase):
    def setUp(self):
        self.db = dbapi.connect(**db_connect)
        try:
            cursor = self.db.cursor()
            try:
                cursor = self.db.cursor()
                cursor.execute("DROP TABLE t1")
            except dbapi.DatabaseError:
                e = exc_info()[1]
                # the only acceptable error is:
                self.assertEqual(
                    e.args[1], b('42P01'),  # table does not exist
                    "incorrect error for drop table")
                self.db.rollback()
            cursor.execute(
                "CREATE TEMPORARY TABLE t1 (f1 int primary key, "
                "f2 int not null, f3 varchar(50) null)")
        finally:
            cursor.close()

    def tearDown(self):
        self.db.close()

    def testCopyToWithTable(self):
        try:
            cursor = self.db.cursor()
            cursor.execute(
                "INSERT INTO t1 (f1, f2, f3) VALUES (%s, %s, %s)", (1, 1, 1))
            cursor.execute(
                "INSERT INTO t1 (f1, f2, f3) VALUES (%s, %s, %s)", (2, 2, 2))
            cursor.execute(
                "INSERT INTO t1 (f1, f2, f3) VALUES (%s, %s, %s)", (3, 3, 3))

            stream = BytesIO()
            cursor.copy_to(stream, "t1")
            self.assertEqual(
                stream.getvalue(), b("1\t1\t1\n2\t2\t2\n3\t3\t3\n"))
            self.assertEqual(cursor.rowcount, 3)
            self.db.commit()
        finally:
            cursor.close()

    def testCopyToWithQuery(self):
        try:
            cursor = self.db.cursor()
            stream = BytesIO()
            cursor.copy_to(
                stream, query="COPY (SELECT 1 as One, 2 as Two) TO STDOUT "
                "WITH DELIMITER 'X' CSV HEADER QUOTE AS 'Y' FORCE QUOTE Two")
            self.assertEqual(stream.getvalue(), b('oneXtwo\n1XY2Y\n'))
            self.assertEqual(cursor.rowcount, 1)
            self.db.rollback()
        finally:
            cursor.close()

    def testCopyFromWithTable(self):
        try:
            cursor = self.db.cursor()
            stream = BytesIO(b("1\t1\t1\n2\t2\t2\n3\t3\t3\n"))
            cursor.copy_from(stream, "t1")
            self.assertEqual(cursor.rowcount, 3)

            cursor.execute("SELECT * FROM t1 ORDER BY f1")
            retval = cursor.fetchall()
            self.assertEqual(retval, ([1, 1, '1'], [2, 2, '2'], [3, 3, '3']))
            self.db.rollback()
        finally:
            cursor.close()

    def testCopyFromWithQuery(self):
        try:
            cursor = self.db.cursor()
            stream = BytesIO(b("f1Xf2\n1XY1Y\n"))
            cursor.copy_from(
                stream, query="COPY t1 (f1, f2) FROM STDIN WITH DELIMITER "
                "'X' CSV HEADER QUOTE AS 'Y' FORCE NOT NULL f1")
            self.assertEqual(cursor.rowcount, 1)

            cursor.execute("SELECT * FROM t1 ORDER BY f1")
            retval = cursor.fetchall()
            self.assertEqual(retval, ([1, 1, None],))
            self.db.commit()
        finally:
            cursor.close()

    def testCopyWithoutTableOrQuery(self):
        try:
            cursor = self.db.cursor()
            stream = BytesIO()
            self.assertRaises(
                dbapi.CopyQueryOrTableRequiredError, cursor.copy_from, stream)
            self.assertRaises(
                dbapi.CopyQueryOrTableRequiredError, cursor.copy_to, stream)
            self.db.rollback()
        finally:
            cursor.close()


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_dbapi
import unittest
import os
import time
import pg8000
import datetime
from .connection_settings import db_connect
from sys import exc_info
from pg8000.six import b, IS_JYTHON

dbapi = pg8000.DBAPI


# DBAPI compatible interface tests
class Tests(unittest.TestCase):
    def setUp(self):
        self.db = dbapi.connect(**db_connect)
        # Jython 2.5.3 doesn't have a time.tzset() so skip
        if not IS_JYTHON:
            os.environ['TZ'] = "UTC"
            time.tzset()

        try:
            c = self.db.cursor()
            try:
                c = self.db.cursor()
                c.execute("DROP TABLE t1")
            except pg8000.DatabaseError:
                e = exc_info()[1]
                # the only acceptable error is:
                self.assertEqual(e.args[1], b('42P01'))  # table does not exist
                self.db.rollback()
            c.execute(
                "CREATE TEMPORARY TABLE t1 "
                "(f1 int primary key, f2 int not null, f3 varchar(50) null)")
            c.execute(
                "INSERT INTO t1 (f1, f2, f3) VALUES (%s, %s, %s)",
                (1, 1, None))
            c.execute(
                "INSERT INTO t1 (f1, f2, f3) VALUES (%s, %s, %s)",
                (2, 10, None))
            c.execute(
                "INSERT INTO t1 (f1, f2, f3) VALUES (%s, %s, %s)",
                (3, 100, None))
            c.execute(
                "INSERT INTO t1 (f1, f2, f3) VALUES (%s, %s, %s)",
                (4, 1000, None))
            c.execute(
                "INSERT INTO t1 (f1, f2, f3) VALUES (%s, %s, %s)",
                (5, 10000, None))
            self.db.commit()
        finally:
            c.close()

    def tearDown(self):
        self.db.close()

    def testParallelQueries(self):
        try:
            c1 = self.db.cursor()
            c2 = self.db.cursor()

            c1.execute("SELECT f1, f2, f3 FROM t1")
            while 1:
                row = c1.fetchone()
                if row is None:
                    break
                f1, f2, f3 = row
                c2.execute("SELECT f1, f2, f3 FROM t1 WHERE f1 > %s", (f1,))
                while 1:
                    row = c2.fetchone()
                    if row is None:
                        break
                    f1, f2, f3 = row
        finally:
            c1.close()
            c2.close()

        self.db.rollback()

    def testQmark(self):
        orig_paramstyle = dbapi.paramstyle
        try:
            dbapi.paramstyle = "qmark"
            c1 = self.db.cursor()
            c1.execute("SELECT f1, f2, f3 FROM t1 WHERE f1 > ?", (3,))
            while 1:
                row = c1.fetchone()
                if row is None:
                    break
                f1, f2, f3 = row
            self.db.rollback()
        finally:
            dbapi.paramstyle = orig_paramstyle
            c1.close()

    def testNumeric(self):
        orig_paramstyle = dbapi.paramstyle
        try:
            dbapi.paramstyle = "numeric"
            c1 = self.db.cursor()
            c1.execute("SELECT f1, f2, f3 FROM t1 WHERE f1 > :1", (3,))
            while 1:
                row = c1.fetchone()
                if row is None:
                    break
                f1, f2, f3 = row
            self.db.rollback()
        finally:
            dbapi.paramstyle = orig_paramstyle
            c1.close()

    def testNamed(self):
        orig_paramstyle = dbapi.paramstyle
        try:
            dbapi.paramstyle = "named"
            c1 = self.db.cursor()
            c1.execute(
                "SELECT f1, f2, f3 FROM t1 WHERE f1 > :f1", {"f1": 3})
            while 1:
                row = c1.fetchone()
                if row is None:
                    break
                f1, f2, f3 = row
            self.db.rollback()
        finally:
            dbapi.paramstyle = orig_paramstyle
            c1.close()

    def testFormat(self):
        orig_paramstyle = dbapi.paramstyle
        try:
            dbapi.paramstyle = "format"
            c1 = self.db.cursor()
            c1.execute("SELECT f1, f2, f3 FROM t1 WHERE f1 > %s", (3,))
            while 1:
                row = c1.fetchone()
                if row is None:
                    break
                f1, f2, f3 = row
            self.db.commit()
        finally:
            dbapi.paramstyle = orig_paramstyle
            c1.close()

    def testPyformat(self):
        orig_paramstyle = dbapi.paramstyle
        try:
            dbapi.paramstyle = "pyformat"
            c1 = self.db.cursor()
            c1.execute(
                "SELECT f1, f2, f3 FROM t1 WHERE f1 > %(f1)s", {"f1": 3})
            while 1:
                row = c1.fetchone()
                if row is None:
                    break
                f1, f2, f3 = row
            self.db.commit()
        finally:
            dbapi.paramstyle = orig_paramstyle
            c1.close()

    def testArraysize(self):
        try:
            c1 = self.db.cursor()
            c1.arraysize = 3
            c1.execute("SELECT * FROM t1")
            retval = c1.fetchmany()
            self.assertEqual(len(retval), c1.arraysize)
        finally:
            c1.close()
        self.db.commit()

    def testDate(self):
        val = dbapi.Date(2001, 2, 3)
        self.assertEqual(val, datetime.date(2001, 2, 3))

    def testTime(self):
        val = dbapi.Time(4, 5, 6)
        self.assertEqual(val, datetime.time(4, 5, 6))

    def testTimestamp(self):
        val = dbapi.Timestamp(2001, 2, 3, 4, 5, 6)
        self.assertEqual(val, datetime.datetime(2001, 2, 3, 4, 5, 6))

    def testDateFromTicks(self):
        if IS_JYTHON:
            return

        val = dbapi.DateFromTicks(1173804319)
        self.assertEqual(val, datetime.date(2007, 3, 13))

    def testTimeFromTicks(self):
        if IS_JYTHON:
            return

        val = dbapi.TimeFromTicks(1173804319)
        self.assertEqual(val, datetime.time(16, 45, 19))

    def testTimestampFromTicks(self):
        if IS_JYTHON:
            return

        val = dbapi.TimestampFromTicks(1173804319)
        self.assertEqual(val, datetime.datetime(2007, 3, 13, 16, 45, 19))

    def testBinary(self):
        v = dbapi.Binary(b("\x00\x01\x02\x03\x02\x01\x00"))
        self.assertEqual(v, b("\x00\x01\x02\x03\x02\x01\x00"))
        self.assertTrue(isinstance(v, dbapi.BINARY))

    def testRowCount(self):
        # In PostgreSQL 8.4 we don't know the row count for a select
        if not self.db._server_version.startswith("8.4"):
            try:
                c1 = self.db.cursor()
                c1.execute("SELECT * FROM t1")
                self.assertEqual(5, c1.rowcount)

                c1.execute("UPDATE t1 SET f3 = %s WHERE f2 > 101", ("Hello!",))
                self.assertEqual(2, c1.rowcount)

                c1.execute("DELETE FROM t1")
                self.assertEqual(5, c1.rowcount)
            finally:
                c1.close()
            self.db.commit()

    def testFetchMany(self):
        try:
            cursor = self.db.cursor()
            cursor.arraysize = 2
            cursor.execute("SELECT * FROM t1")
            self.assertEqual(2, len(cursor.fetchmany()))
            self.assertEqual(2, len(cursor.fetchmany()))
            self.assertEqual(1, len(cursor.fetchmany()))
            self.assertEqual(0, len(cursor.fetchmany()))
        finally:
            cursor.close()
        self.db.commit()

    def testIterator(self):
        from warnings import filterwarnings
        filterwarnings("ignore", "DB-API extension cursor.next()")
        filterwarnings("ignore", "DB-API extension cursor.__iter__()")

        try:
            cursor = self.db.cursor()
            cursor.execute("SELECT * FROM t1 ORDER BY f1")
            f1 = 0
            for row in cursor:
                next_f1 = row[0]
                assert next_f1 > f1
                f1 = next_f1
        except:
            cursor.close()

        self.db.commit()

    # Vacuum can't be run inside a transaction, so we need to turn
    # autocommit on.
    def testVacuum(self):
        self.db.autocommit = True
        try:
            cursor = self.db.cursor()
            cursor.execute("vacuum")
        finally:
            cursor.close()

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_error_recovery
import unittest
from pg8000 import DBAPI
from .connection_settings import db_connect
import warnings
from pg8000.errors import DatabaseError
import datetime
from sys import exc_info
from pg8000.six import b


class TestException(Exception):
    pass


class Tests(unittest.TestCase):
    def setUp(self):
        self.db = DBAPI.connect(**db_connect)

    def tearDown(self):
        self.db.close()

    def raiseException(self, value):
        raise TestException("oh noes!")

    def testPyValueFail(self):
        # Ensure that if types.py_value throws an exception, the original
        # exception is raised (TestException), and the connection is
        # still usable after the error.
        orig = self.db.py_types[datetime.time]
        self.db.py_types[datetime.time] = (
            orig[0], orig[1], self.raiseException)

        try:
            c = self.db.cursor()
            try:
                try:
                    c.execute("SELECT %s as f1", (datetime.time(10, 30),))
                    c.fetchall()
                    # shouldn't get here, exception should be thrown
                    self.fail()
                except TestException:
                    # should be TestException type, this is OK!
                    self.db.rollback()
            finally:
                self.db.py_types[datetime.time] = orig

            # ensure that the connection is still usable for a new query
            c.execute("VALUES ('hw3'::text)")
            self.assertEqual(c.fetchone()[0], "hw3")
        finally:
            c.close()

    def testNoDataErrorRecovery(self):
        for i in range(1, 4):
            try:
                try:
                    cursor = self.db.cursor()
                    cursor.execute("DROP TABLE t1")
                finally:
                    cursor.close()
            except DatabaseError:
                e = exc_info()[1]
                # the only acceptable error is:
                self.assertEqual(e.args[1], b('42P01'))  # table does not exist
                self.db.rollback()

    def testClosedConnection(self):
        warnings.simplefilter("ignore")
        my_db = DBAPI.connect(**db_connect)
        cursor = my_db.cursor()
        my_db.close()
        self.assertRaises(
            self.db.InterfaceError, cursor.execute, "VALUES ('hw1'::text)")
        warnings.resetwarnings()

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_paramstyle
import unittest
import pg8000


# Tests of the convert_paramstyle function.
class Tests(unittest.TestCase):
    def testQmark(self):
        new_query, make_args = pg8000.core.convert_paramstyle(
            "qmark", "SELECT ?, ?, \"field_?\" FROM t "
            "WHERE a='say ''what?''' AND b=? AND c=E'?\\'test\\'?'")
        self.assertEqual(
            new_query, "SELECT $1, $2, \"field_?\" FROM t WHERE "
            "a='say ''what?''' AND b=$3 AND c=E'?\\'test\\'?'")
        self.assertEqual(make_args((1, 2, 3)), (1, 2, 3))

    def testQmark2(self):
        new_query, make_args = pg8000.core.convert_paramstyle(
            "qmark", "SELECT ?, ?, * FROM t WHERE a=? AND b='are you ''sure?'")
        self.assertEqual(
            new_query,
            "SELECT $1, $2, * FROM t WHERE a=$3 AND b='are you ''sure?'")
        self.assertEqual(make_args((1, 2, 3)), (1, 2, 3))

    def testNumeric(self):
        new_query, make_args = pg8000.core.convert_paramstyle(
            "numeric", "SELECT :2, :1, * FROM t WHERE a=:3")
        self.assertEqual(new_query, "SELECT $2, $1, * FROM t WHERE a=$3")
        self.assertEqual(make_args((1, 2, 3)), (1, 2, 3))

    def testNamed(self):
        new_query, make_args = pg8000.core.convert_paramstyle(
            "named", "SELECT :f_2, :f1 FROM t WHERE a=:f_2")
        self.assertEqual(new_query, "SELECT $1, $2 FROM t WHERE a=$1")
        self.assertEqual(make_args({"f_2": 1, "f1": 2}), (1, 2))

    def testFormat(self):
        new_query, make_args = pg8000.core.convert_paramstyle(
            "format", "SELECT %s, %s, \"f1_%%\", E'txt_%%' "
            "FROM t WHERE a=%s AND b='75%%'")
        self.assertEqual(
            new_query,
            "SELECT $1, $2, \"f1_%\", E'txt_%' FROM t WHERE a=$3 AND b='75%'")
        self.assertEqual(make_args((1, 2, 3)), (1, 2, 3))

    def testPyformat(self):
        new_query, make_args = pg8000.core.convert_paramstyle(
            "pyformat", "SELECT %(f2)s, %(f1)s, \"f1_%%\", E'txt_%%' "
            "FROM t WHERE a=%(f2)s AND b='75%%'")
        self.assertEqual(
            new_query,
            "SELECT $1, $2, \"f1_%\", E'txt_%' FROM t WHERE a=$1 AND b='75%'")
        self.assertEqual(make_args({"f2": 1, "f1": 2, "f3": 3}), (1, 2))

        # pyformat should support %s and an array, too:
        new_query, make_args = pg8000.core.convert_paramstyle(
            "pyformat", "SELECT %s, %s, \"f1_%%\", E'txt_%%' "
            "FROM t WHERE a=%s AND b='75%%'")
        self.assertEqual(
            new_query,
            "SELECT $1, $2, \"f1_%\", E'txt_%' FROM t WHERE a=$3 AND b='75%'")
        self.assertEqual(make_args((1, 2, 3)), (1, 2, 3))

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_pg8000_dbapi20
#!/usr/bin/env python
from . import dbapi20
import unittest
import pg8000
from .connection_settings import db_connect


class Tests(dbapi20.DatabaseAPI20Test):
    driver = pg8000.DBAPI
    connect_args = ()
    connect_kw_args = db_connect

    lower_func = 'lower'  # For stored procedure test

    def test_nextset(self):
        pass

    def test_setoutputsize(self):
        pass

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_query
import unittest
import threading
from pg8000 import dbapi
from .connection_settings import db_connect
from pg8000.six import u, b
from sys import exc_info


from warnings import filterwarnings


# Tests relating to the basic operation of the database driver, driven by the
# pg8000 custom interface.
class Tests(unittest.TestCase):
    def setUp(self):
        self.db = dbapi.connect(**db_connect)
        filterwarnings("ignore", "DB-API extension cursor.next()")
        filterwarnings("ignore", "DB-API extension cursor.__iter__()")
        self.db.paramstyle = 'format'
        try:
            cursor = self.db.cursor()
            try:
                cursor.execute("DROP TABLE t1")
            except dbapi.DatabaseError:
                e = exc_info()[1]
                # the only acceptable error is:
                self.assertEqual(e.args[1], b('42P01'))  # table does not exist
                self.db.rollback()
            cursor.execute(
                "CREATE TEMPORARY TABLE t1 (f1 int primary key, "
                "f2 bigint not null, f3 varchar(50) null)")
        finally:
            cursor.close()

        self.db.commit()

    def tearDown(self):
        self.db.close()

    def testDatabaseError(self):
        try:
            cursor = self.db.cursor()
            self.assertRaises(
                dbapi.ProgrammingError, cursor.execute,
                "INSERT INTO t99 VALUES (1, 2, 3)")
        finally:
            cursor.close()

        self.db.rollback()

    def testParallelQueries(self):
        try:
            cursor = self.db.cursor()
            cursor.execute(
                "INSERT INTO t1 (f1, f2, f3) VALUES (%s, %s, %s)",
                (1, 1, None))
            cursor.execute(
                "INSERT INTO t1 (f1, f2, f3) VALUES (%s, %s, %s)",
                (2, 10, None))
            cursor.execute(
                "INSERT INTO t1 (f1, f2, f3) VALUES (%s, %s, %s)",
                (3, 100, None))
            cursor.execute(
                "INSERT INTO t1 (f1, f2, f3) VALUES (%s, %s, %s)",
                (4, 1000, None))
            cursor.execute(
                "INSERT INTO t1 (f1, f2, f3) VALUES (%s, %s, %s)",
                (5, 10000, None))
            try:
                c1 = self.db.cursor()
                c2 = self.db.cursor()
                c1.execute("SELECT f1, f2, f3 FROM t1")
                for row in c1:
                    f1, f2, f3 = row
                    c2.execute(
                        "SELECT f1, f2, f3 FROM t1 WHERE f1 > %s", (f1,))
                    for row in c2:
                        f1, f2, f3 = row
            finally:
                c1.close()
                c2.close()
        finally:
            cursor.close()
        self.db.rollback()

    def testInsertReturning(self):
        try:
            cursor = self.db.cursor()
            cursor.execute("CREATE TABLE t2 (id serial, data text)")

            # Test INSERT ... RETURNING with one row...
            cursor.execute(
                "INSERT INTO t2 (data) VALUES (%s) RETURNING id",
                ("test1",))
            row_id = cursor.fetchone()[0]
            cursor.execute("SELECT data FROM t2 WHERE id = %s", (row_id,))
            self.assertEqual("test1", cursor.fetchone()[0])

            # In PostgreSQL 8.4 we don't know the row count for a select
            if not self.db._server_version.startswith("8.4"):
                self.assertEqual(cursor.rowcount, 1)

            # Test with multiple rows...
            cursor.execute(
                "INSERT INTO t2 (data) VALUES (%s), (%s), (%s) "
                "RETURNING id", ("test2", "test3", "test4"))

            # In PostgreSQL 8.4 we don't know the row count for a select
            if not self.db._server_version.startswith("8.4"):
                self.assertEqual(cursor.rowcount, 3)

            ids = tuple([x[0] for x in cursor])
            self.assertEqual(len(ids), 3)
        finally:
            cursor.close()
            self.db.rollback()

    def testMultithreadedCursor(self):
        try:
            cursor = self.db.cursor()
            # Note: Multithreading with a cursor is not highly recommended due
            # to low performance.

            def test(left, right):
                for i in range(left, right):
                    cursor.execute(
                        "INSERT INTO t1 (f1, f2, f3) VALUES (%s, %s, %s)",
                        (i, id(threading.currentThread()), None))
            t1 = threading.Thread(target=test, args=(1, 25))
            t2 = threading.Thread(target=test, args=(25, 50))
            t3 = threading.Thread(target=test, args=(50, 75))
            t1.start()
            t2.start()
            t3.start()
            t1.join()
            t2.join()
            t3.join()
        finally:
            cursor.close()
            self.db.rollback()

    def testRowCount(self):
        # In PostgreSQL 8.4 we don't know the row count for a select
        if not self.db._server_version.startswith("8.4"):
            try:
                cursor = self.db.cursor()
                expected_count = 57
                cursor.executemany(
                    "INSERT INTO t1 (f1, f2, f3) VALUES (%s, %s, %s)",
                    tuple((i, i, None) for i in range(expected_count)))
                self.db.commit()

                cursor.execute("SELECT * FROM t1")

                # Check row_count without doing any reading first...
                self.assertEqual(expected_count, cursor.rowcount)

                # Check rowcount after reading some rows, make sure it still
                # works...
                for i in range(expected_count // 2):
                    cursor.fetchone()
                self.assertEqual(expected_count, cursor.rowcount)
            finally:
                cursor.close()
                self.db.commit()

            try:
                cursor = self.db.cursor()
                # Restart the cursor, read a few rows, and then check rowcount
                # again...
                cursor = self.db.cursor()
                cursor.execute("SELECT * FROM t1")
                for i in range(expected_count // 3):
                    cursor.fetchone()
                self.assertEqual(expected_count, cursor.rowcount)
                self.db.rollback()

                # Should be -1 for a command with no results
                cursor.execute("DROP TABLE t1")
                self.assertEqual(-1, cursor.rowcount)
            finally:
                cursor.close()
                self.db.commit()

    def testRowCountUpdate(self):
        try:
            cursor = self.db.cursor()
            cursor.execute(
                "INSERT INTO t1 (f1, f2, f3) VALUES (%s, %s, %s)",
                (1, 1, None))
            cursor.execute(
                "INSERT INTO t1 (f1, f2, f3) VALUES (%s, %s, %s)",
                (2, 10, None))
            cursor.execute(
                "INSERT INTO t1 (f1, f2, f3) VALUES (%s, %s, %s)",
                (3, 100, None))
            cursor.execute(
                "INSERT INTO t1 (f1, f2, f3) VALUES (%s, %s, %s)",
                (4, 1000, None))
            cursor.execute(
                "INSERT INTO t1 (f1, f2, f3) VALUES (%s, %s, %s)",
                (5, 10000, None))
            cursor.execute("UPDATE t1 SET f3 = %s WHERE f2 > 101", ("Hello!",))
            self.assertEqual(cursor.rowcount, 2)
        finally:
            cursor.close()
            self.db.commit()

    def testIntOid(self):
        try:
            cursor = self.db.cursor()
            # https://bugs.launchpad.net/pg8000/+bug/230796
            cursor.execute(
                "SELECT typname FROM pg_type WHERE oid = %s", (100,))
        finally:
            cursor.close()
            self.db.rollback()

    def testUnicodeQuery(self):
        try:
            cursor = self.db.cursor()
            cursor.execute(
                u(
                    "CREATE TEMPORARY TABLE \u043c\u0435\u0441\u0442\u043e "
                    "(\u0438\u043c\u044f VARCHAR(50), "
                    "\u0430\u0434\u0440\u0435\u0441 VARCHAR(250))"))
        finally:
            cursor.close()
            self.db.commit()


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_typeconversion
import unittest
from pg8000 import errors, types, dbapi
import datetime
import decimal
import struct
from .connection_settings import db_connect
from pg8000.six import b, IS_JYTHON
import uuid


if not IS_JYTHON:
    import pytz


# Type conversion tests
class Tests(unittest.TestCase):
    def setUp(self):
        self.db = dbapi.connect(**db_connect)
        self.cursor = self.db.cursor()

    def tearDown(self):
        self.cursor.close()
        self.cursor = None
        self.db.close()

    def testTimeRoundtrip(self):
        self.cursor.execute("SELECT %s as f1", (datetime.time(4, 5, 6),))
        retval = self.cursor.fetchall()
        self.assertEqual(retval[0][0], datetime.time(4, 5, 6))

    def testDateRoundtrip(self):
        self.cursor.execute("SELECT %s as f1", (datetime.date(2001, 2, 3),))
        retval = self.cursor.fetchall()
        self.assertEqual(retval[0][0], datetime.date(2001, 2, 3))

    def testBoolRoundtrip(self):
        self.cursor.execute("SELECT %s as f1", (True,))
        retval = self.cursor.fetchall()
        self.assertEqual(retval[0][0], True)

    def testNullRoundtrip(self):
        # We can't just "SELECT %s" and set None as the parameter, since it has
        # no type.  That would result in a PG error, "could not determine data
        # type of parameter %s".  So we create a temporary table, insert null
        # values, and read them back.
        self.cursor.execute(
            "CREATE TEMPORARY TABLE TestNullWrite "
            "(f1 int4, f2 timestamp, f3 varchar)")
        self.cursor.execute(
            "INSERT INTO TestNullWrite VALUES (%s, %s, %s)",
            (None, None, None,))
        self.cursor.execute("SELECT * FROM TestNullWrite")
        retval = self.cursor.fetchone()
        self.assertEqual(retval, [None, None, None])

    def testNullSelectFailure(self):
        # See comment in TestNullRoundtrip.  This test is here to ensure that
        # this behaviour is documented and doesn't mysteriously change.
        self.assertRaises(
            errors.ProgrammingError, self.cursor.execute,
            "SELECT %s as f1", (None,))
        self.db.rollback()

    def testDecimalRoundtrip(self):
        values = "1.1", "-1.1", "10000", "20000", "-1000000000.123456789"
        for v in values:
            self.cursor.execute("SELECT %s as f1", (decimal.Decimal(v),))
            retval = self.cursor.fetchall()
            self.assertEqual(retval[0][0], decimal.Decimal(v))

    def testFloatRoundtrip(self):
        # This test ensures that the binary float value doesn't change in a
        # roundtrip to the server.  That could happen if the value was
        # converted to text and got rounded by a decimal place somewhere.
        val = 1.756e-12
        bin_orig = struct.pack("!d", val)
        self.cursor.execute("SELECT %s as f1", (val,))
        retval = self.cursor.fetchall()
        bin_new = struct.pack("!d", retval[0][0])
        self.assertEqual(bin_new, bin_orig)

    def testStrRoundtrip(self):
        v = "hello world"
        self.cursor.execute(
            "create temporary table test_str (f character varying(255))")
        self.cursor.execute("INSERT INTO test_str VALUES (%s)", (v,))
        self.cursor.execute("SELECT * from test_str")
        retval = self.cursor.fetchall()
        self.assertEqual(retval[0][0], v)

    def testUnicodeRoundtrip(self):
        self.cursor.execute(
            "SELECT cast(%s as varchar) as f1", ("hello \u0173 world",))
        retval = self.cursor.fetchall()
        self.assertEqual(retval[0][0], "hello \u0173 world")

    def testLongRoundtrip(self):
        self.cursor.execute(
            "SELECT cast(%s as bigint) as f1", (50000000000000,))
        retval = self.cursor.fetchall()
        self.assertEqual(retval[0][0], 50000000000000)

    def testIntRoundtrip(self):
        int2 = 21
        int4 = 23
        int8 = 20

        test_values = [
            (0, int2, 'smallint'),
            (-32767, int2, 'smallint'),
            (-32768, int4, 'integer'),
            (+32767, int2, 'smallint'),
            (+32768, int4, 'integer'),
            (-2147483647, int4, 'integer'),
            (-2147483648, int8, 'bigint'),
            (+2147483647, int4, 'integer'),
            (+2147483648, int8, 'bigint'),
            (-9223372036854775807, int8, 'bigint'),
            (+9223372036854775807, int8, 'bigint'), ]

        for value, typoid, tp in test_values:
            self.cursor.execute(
                "SELECT cast(%s as " + tp + ") as f1", (value,))
            retval = self.cursor.fetchall()
            self.assertEqual(retval[0][0], value)
            column_name, column_typeoid = self.cursor.description[0][0:2]
            self.assertEqual(column_typeoid, typoid, "type should be INT2[]")

    def testByteaRoundtrip(self):
        self.cursor.execute(
            "SELECT %s as f1",
            (dbapi.Binary(b("\x00\x01\x02\x03\x02\x01\x00")),))
        retval = self.cursor.fetchall()
        self.assertEqual(retval[0][0], b("\x00\x01\x02\x03\x02\x01\x00"))

    def testTimestampRoundtrip(self):
        v = datetime.datetime(2001, 2, 3, 4, 5, 6, 170000)
        self.cursor.execute("SELECT %s as f1", (v,))
        retval = self.cursor.fetchall()
        self.assertEqual(retval[0][0], v)

    def testIntervalRoundtrip(self):
        v = types.Interval(microseconds=123456789, days=2, months=24)
        self.cursor.execute("SELECT %s as f1", (v,))
        retval = self.cursor.fetchall()
        self.assertEqual(retval[0][0], v)

    def testEnumRoundtrip(self):
        try:
            self.cursor.execute(
                "create type lepton as enum ('electron', 'muon', 'tau')")
        except errors.ProgrammingError:
            self.db.rollback()

        v = 'muon'
        self.cursor.execute("SELECT cast(%s as lepton) as f1", (v,))
        retval = self.cursor.fetchall()
        self.assertEqual(retval[0][0], v)
        self.cursor.execute(
            "CREATE TEMPORARY TABLE testenum "
            "(f1 lepton)")
        self.cursor.execute("INSERT INTO testenum VALUES (%s)", ('electron',))
        self.cursor.execute("drop table testenum")
        self.cursor.execute("drop type lepton")
        self.db.commit()

    def testXmlRoundtrip(self):
        v = '<genome>gatccgagtac</genome>'
        self.cursor.execute("select xmlparse(content %s) as f1", (v,))
        retval = self.cursor.fetchall()
        self.assertEqual(retval[0][0], v)

    def testUuidRoundtrip(self):
        v = uuid.UUID('911460f2-1f43-fea2-3e2c-e01fd5b5069d')
        self.cursor.execute("select %s as f1", (v,))
        retval = self.cursor.fetchall()
        self.assertEqual(retval[0][0], v)

    def testTimestampTzOut(self):
        self.cursor.execute(
            "SELECT '2001-02-03 04:05:06.17 America/Edmonton'"
            "::timestamp with time zone")
        retval = self.cursor.fetchall()
        dt = retval[0][0]
        self.assertEqual(dt.tzinfo is not None, True, "no tzinfo returned")
        self.assertEqual(
            dt.astimezone(types.utc),
            datetime.datetime(2001, 2, 3, 11, 5, 6, 170000, types.utc),
            "retrieved value match failed")

    def testTimestampTzRoundtrip(self):
        if not IS_JYTHON:
            mst = pytz.timezone("America/Edmonton")
            v1 = mst.localize(datetime.datetime(2001, 2, 3, 4, 5, 6, 170000))
            self.cursor.execute("SELECT %s as f1", (v1,))
            retval = self.cursor.fetchall()
            v2 = retval[0][0]
            self.assertNotEqual(v2.tzinfo, None)
            self.assertEqual(v1, v2)

    def testTimestampMismatch(self):
        if not IS_JYTHON:
            mst = pytz.timezone("America/Edmonton")
            self.cursor.execute("SET SESSION TIME ZONE 'America/Edmonton'")
            try:
                self.cursor.execute(
                    "CREATE TEMPORARY TABLE TestTz "
                    "(f1 timestamp with time zone, "
                    "f2 timestamp without time zone)")
                self.cursor.execute(
                    "INSERT INTO TestTz (f1, f2) VALUES (%s, %s)", (
                        # insert timestamp into timestamptz field (v1)
                        datetime.datetime(2001, 2, 3, 4, 5, 6, 170000),
                        # insert timestamptz into timestamp field (v2)
                        mst.localize(datetime.datetime(
                            2001, 2, 3, 4, 5, 6, 170000))))
                self.cursor.execute("SELECT f1, f2 FROM TestTz")
                retval = self.cursor.fetchall()

                # when inserting a timestamp into a timestamptz field,
                # postgresql assumes that it is in local time. So the value
                # that comes out will be the server's local time interpretation
                # of v1. We've set the server's TZ to MST, the time should
                # be...
                f1 = retval[0][0]
                self.assertEqual(
                    f1, datetime.datetime(
                        2001, 2, 3, 11, 5, 6, 170000, pytz.utc))

                # inserting the timestamptz into a timestamp field, pg8000
                # converts the value into UTC, and then the PG server converts
                # it into local time for insertion into the field. When we
                # query for it, we get the same time back, like the tz was
                # dropped.
                f2 = retval[0][1]
                self.assertEqual(
                    f2, datetime.datetime(2001, 2, 3, 4, 5, 6, 170000))
            finally:
                self.cursor.execute("SET SESSION TIME ZONE DEFAULT")

    def testNameOut(self):
        # select a field that is of "name" type:
        self.cursor.execute("SELECT usename FROM pg_user")
        self.cursor.fetchall()
        # It is sufficient that no errors were encountered.

    def testOidOut(self):
        self.cursor.execute("SELECT oid FROM pg_type")
        self.cursor.fetchall()
        # It is sufficient that no errors were encountered.

    def testBooleanOut(self):
        self.cursor.execute("SELECT cast('t' as bool)")
        retval = self.cursor.fetchall()
        self.assertTrue(retval[0][0])

    def testNumericOut(self):
        for num in ('5000', '50.34'):
            self.cursor.execute("SELECT " + num + "::numeric")
            retval = self.cursor.fetchall()
            self.assertEqual(str(retval[0][0]), num)

    def testInt2Out(self):
        self.cursor.execute("SELECT 5000::smallint")
        retval = self.cursor.fetchall()
        self.assertEqual(retval[0][0], 5000)

    def testInt4Out(self):
        self.cursor.execute("SELECT 5000::integer")
        retval = self.cursor.fetchall()
        self.assertEqual(retval[0][0], 5000)

    def testInt8Out(self):
        self.cursor.execute("SELECT 50000000000000::bigint")
        retval = self.cursor.fetchall()
        self.assertEqual(retval[0][0], 50000000000000)

    def testFloat4Out(self):
        self.cursor.execute("SELECT 1.1::real")
        retval = self.cursor.fetchall()
        self.assertEqual(retval[0][0], 1.1000000238418579)

    def testFloat8Out(self):
        self.cursor.execute("SELECT 1.1::double precision")
        retval = self.cursor.fetchall()
        self.assertEqual(retval[0][0], 1.1000000000000001)

    def testVarcharOut(self):
        self.cursor.execute("SELECT 'hello'::varchar(20)")
        retval = self.cursor.fetchall()
        self.assertEqual(retval[0][0], "hello")

    def testCharOut(self):
        self.cursor.execute("SELECT 'hello'::char(20)")
        retval = self.cursor.fetchall()
        self.assertEqual(retval[0][0], "hello               ")

    def testTextOut(self):
        self.cursor.execute("SELECT 'hello'::text")
        retval = self.cursor.fetchall()
        self.assertEqual(retval[0][0], "hello")

    def testIntervalOut(self):
        self.cursor.execute(
            "SELECT '1 month 16 days 12 hours 32 minutes 64 seconds'"
            "::interval")
        retval = self.cursor.fetchall()
        expected_value = types.Interval(
            microseconds=(12 * 60 * 60 * 1000 * 1000) +
            (32 * 60 * 1000 * 1000) + (64 * 1000 * 1000),
            days=16, months=1)
        self.assertEqual(retval[0][0], expected_value)

    def testTimestampOut(self):
        self.cursor.execute("SELECT '2001-02-03 04:05:06.17'::timestamp")
        retval = self.cursor.fetchall()
        self.assertEqual(
            retval[0][0], datetime.datetime(2001, 2, 3, 4, 5, 6, 170000))

    # confirms that pg8000's binary output methods have the same output for
    # a data type as the PG server
    def testBinaryOutputMethods(self):
        methods = (
            ("float8send", 22.2),
            ("timestamp_send", datetime.datetime(2001, 2, 3, 4, 5, 6, 789)),
            ("byteasend", dbapi.Binary(b("\x01\x02"))),
            ("interval_send", types.Interval(1234567, 123, 123)),)
        for method_out, value in methods:
            self.cursor.execute("SELECT %s(%%s) as f1" % method_out, (value,))
            retval = self.cursor.fetchall()
            self.assertEqual(
                retval[0][0], self.db.make_params((value,))[0][2](value))

    def testInt4ArrayOut(self):
        self.cursor.execute(
            "SELECT '{1,2,3,4}'::INT[] AS f1, "
            "'{{1,2,3},{4,5,6}}'::INT[][] AS f2, "
            "'{{{1,2},{3,4}},{{NULL,6},{7,8}}}'::INT[][][] AS f3")
        f1, f2, f3 = self.cursor.fetchone()
        self.assertEqual(f1, [1, 2, 3, 4])
        self.assertEqual(f2, [[1, 2, 3], [4, 5, 6]])
        self.assertEqual(f3, [[[1, 2], [3, 4]], [[None, 6], [7, 8]]])

    def testInt2ArrayOut(self):
        self.cursor.execute(
            "SELECT '{1,2,3,4}'::INT2[] AS f1, "
            "'{{1,2,3},{4,5,6}}'::INT2[][] AS f2, "
            "'{{{1,2},{3,4}},{{NULL,6},{7,8}}}'::INT2[][][] AS f3")
        f1, f2, f3 = self.cursor.fetchone()
        self.assertEqual(f1, [1, 2, 3, 4])
        self.assertEqual(f2, [[1, 2, 3], [4, 5, 6]])
        self.assertEqual(f3, [[[1, 2], [3, 4]], [[None, 6], [7, 8]]])

    def testInt8ArrayOut(self):
        self.cursor.execute(
            "SELECT '{1,2,3,4}'::INT8[] AS f1, "
            "'{{1,2,3},{4,5,6}}'::INT8[][] AS f2, "
            "'{{{1,2},{3,4}},{{NULL,6},{7,8}}}'::INT8[][][] AS f3")
        f1, f2, f3 = self.cursor.fetchone()
        self.assertEqual(f1, [1, 2, 3, 4])
        self.assertEqual(f2, [[1, 2, 3], [4, 5, 6]])
        self.assertEqual(f3, [[[1, 2], [3, 4]], [[None, 6], [7, 8]]])

    def testBoolArrayOut(self):
        self.cursor.execute(
            "SELECT '{TRUE,FALSE,FALSE,TRUE}'::BOOL[] AS f1, "
            "'{{TRUE,FALSE,TRUE},{FALSE,TRUE,FALSE}}'::BOOL[][] AS f2, "
            "'{{{TRUE,FALSE},{FALSE,TRUE}},{{NULL,TRUE},{FALSE,FALSE}}}'"
            "::BOOL[][][] AS f3")
        f1, f2, f3 = self.cursor.fetchone()
        self.assertEqual(f1, [True, False, False, True])
        self.assertEqual(f2, [[True, False, True], [False, True, False]])
        self.assertEqual(
            f3,
            [[[True, False], [False, True]], [[None, True], [False, False]]])

    def testFloat4ArrayOut(self):
        self.cursor.execute(
            "SELECT '{1,2,3,4}'::FLOAT4[] AS f1, "
            "'{{1,2,3},{4,5,6}}'::FLOAT4[][] AS f2, "
            "'{{{1,2},{3,4}},{{NULL,6},{7,8}}}'::FLOAT4[][][] AS f3")
        f1, f2, f3 = self.cursor.fetchone()
        self.assertEqual(f1, [1, 2, 3, 4])
        self.assertEqual(f2, [[1, 2, 3], [4, 5, 6]])
        self.assertEqual(f3, [[[1, 2], [3, 4]], [[None, 6], [7, 8]]])

    def testFloat8ArrayOut(self):
        self.cursor.execute(
            "SELECT '{1,2,3,4}'::FLOAT8[] AS f1, "
            "'{{1,2,3},{4,5,6}}'::FLOAT8[][] AS f2, "
            "'{{{1,2},{3,4}},{{NULL,6},{7,8}}}'::FLOAT8[][][] AS f3")
        f1, f2, f3 = self.cursor.fetchone()
        self.assertEqual(f1, [1, 2, 3, 4])
        self.assertEqual(f2, [[1, 2, 3], [4, 5, 6]])
        self.assertEqual(f3, [[[1, 2], [3, 4]], [[None, 6], [7, 8]]])

    def testIntArrayRoundtrip(self):
        # send small int array, should be sent as INT2[]
        self.cursor.execute("SELECT %s as f1", ([1, 2, 3],))
        retval = self.cursor.fetchall()
        self.assertEqual(retval[0][0], [1, 2, 3])
        column_name, column_typeoid = self.cursor.description[0][0:2]
        self.assertEqual(column_typeoid, 1005, "type should be INT2[]")

        # test multi-dimensional array, should be sent as INT2[]
        self.cursor.execute("SELECT %s as f1", ([[1, 2], [3, 4]],))
        retval = self.cursor.fetchall()
        self.assertEqual(retval[0][0], [[1, 2], [3, 4]])

        column_name, column_typeoid = self.cursor.description[0][0:2]
        self.assertEqual(column_typeoid, 1005, "type should be INT2[]")

        # a larger value should kick it up to INT4[]...
        self.cursor.execute("SELECT %s as f1 -- integer[]", ([70000, 2, 3],))
        retval = self.cursor.fetchall()
        self.assertEqual(retval[0][0], [70000, 2, 3])
        column_name, column_typeoid = self.cursor.description[0][0:2]
        self.assertEqual(column_typeoid, 1007, "type should be INT4[]")

        # a much larger value should kick it up to INT8[]...
        self.cursor.execute(
            "SELECT %s as f1 -- bigint[]", ([7000000000, 2, 3],))
        retval = self.cursor.fetchall()
        self.assertEqual(
            retval[0][0], [7000000000, 2, 3],
            "retrieved value match failed")
        column_name, column_typeoid = self.cursor.description[0][0:2]
        self.assertEqual(column_typeoid, 1016, "type should be INT8[]")

    def testIntArrayWithNullRoundtrip(self):
        self.cursor.execute("SELECT %s as f1", ([1, None, 3],))
        retval = self.cursor.fetchall()
        self.assertEqual(retval[0][0], [1, None, 3])

    def testFloatArrayRoundtrip(self):
        self.cursor.execute("SELECT %s as f1", ([1.1, 2.2, 3.3],))
        retval = self.cursor.fetchall()
        self.assertEqual(retval[0][0], [1.1, 2.2, 3.3])

    def testBoolArrayRoundtrip(self):
        self.cursor.execute("SELECT %s as f1", ([True, False, None],))
        retval = self.cursor.fetchall()
        self.assertEqual(retval[0][0], [True, False, None])

    def testStringArrayOut(self):
        self.cursor.execute("SELECT '{a,b,c}'::TEXT[] AS f1")
        self.assertEqual(self.cursor.fetchone()[0], ["a", "b", "c"])
        self.cursor.execute("SELECT '{a,b,c}'::CHAR[] AS f1")
        self.assertEqual(self.cursor.fetchone()[0], ["a", "b", "c"])
        self.cursor.execute("SELECT '{a,b,c}'::VARCHAR[] AS f1")
        self.assertEqual(self.cursor.fetchone()[0], ["a", "b", "c"])
        self.cursor.execute("SELECT '{a,b,c}'::CSTRING[] AS f1")
        self.assertEqual(self.cursor.fetchone()[0], ["a", "b", "c"])
        self.cursor.execute("SELECT '{a,b,c}'::NAME[] AS f1")
        self.assertEqual(self.cursor.fetchone()[0], ["a", "b", "c"])
        self.cursor.execute("SELECT '{}'::text[];")
        self.assertEqual(self.cursor.fetchone()[0], [])

    def testNumericArrayOut(self):
        self.cursor.execute("SELECT '{1.1,2.2,3.3}'::numeric[] AS f1")
        self.assertEqual(
            self.cursor.fetchone()[0], [
                decimal.Decimal("1.1"), decimal.Decimal("2.2"),
                decimal.Decimal("3.3")])

    def testNumericArrayRoundtrip(self):
        v = [decimal.Decimal("1.1"), None, decimal.Decimal("3.3")]
        self.cursor.execute("SELECT %s as f1", (v,))
        retval = self.cursor.fetchall()
        self.assertEqual(retval[0][0], v)

    def testStringArrayRoundtrip(self):
        self.cursor.execute("SELECT %s as f1", (["Hello!", "World!", None],))
        retval = self.cursor.fetchall()
        self.assertEqual(retval[0][0], ["Hello!", "World!", None])

        self.cursor.execute("SELECT %s as f1", (["Hello!", "World!", None],))
        retval = self.cursor.fetchall()
        self.assertEqual(retval[0][0], ["Hello!", "World!", None])

    def testArrayHasValue(self):
        self.assertRaises(
            errors.ArrayContentEmptyError,
            self.db.array_inspect, [[None], [None], [None]])
        self.db.rollback()

    def testArrayContentNotSupported(self):
        class Kajigger(object):
            pass
        self.assertRaises(
            errors.ArrayContentNotSupportedError,
            self.db.array_inspect, [[Kajigger()], [None], [None]])
        self.db.rollback()

    def testArrayDimensions(self):
        for arr in (
                [1, [2]], [[1], [2], [3, 4]],
                [[[1]], [[2]], [[3, 4]]],
                [[[1]], [[2]], [[3, 4]]],
                [[[[1]]], [[[2]]], [[[3, 4]]]],
                [[1, 2, 3], [4, [5], 6]]):

            arr_send = self.db.array_inspect(arr)[2]
            self.assertRaises(
                errors.ArrayDimensionsNotConsistentError, arr_send, arr)
            self.db.rollback()

    def testArrayHomogenous(self):
        arr = [[[1]], [[2]], [[3.1]]]
        arr_send = self.db.array_inspect(arr)[2]
        self.assertRaises(
            errors.ArrayContentNotHomogenousError, arr_send, arr)
        self.db.rollback()

    def testArrayInspect(self):
        self.db.array_inspect([1, 2, 3])
        self.db.array_inspect([[1], [2], [3]])
        self.db.array_inspect([[[1]], [[2]], [[3]]])

    def testMacaddr(self):
        self.cursor.execute("SELECT macaddr '08002b:010203'")
        retval = self.cursor.fetchall()
        self.assertEqual(retval[0][0], "08:00:2b:01:02:03")

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_typeobjects
import unittest
from pg8000.types import Interval


# Type conversion tests
class Tests(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def testIntervalConstructor(self):
        i = Interval(days=1)
        self.assertEqual(i.months, 0)
        self.assertEqual(i.days, 1)
        self.assertEqual(i.microseconds, 0)

    def intervalRangeTest(self, parameter, in_range, out_of_range):
        for v in out_of_range:
            try:
                Interval(**{parameter: v})
                self.fail("expected OverflowError")
            except OverflowError:
                pass
        for v in in_range:
            Interval(**{parameter: v})

    def testIntervalDaysRange(self):
        out_of_range_days = (-2147483648, +2147483648,)
        in_range_days = (-2147483647, +2147483647,)
        self.intervalRangeTest("days", in_range_days, out_of_range_days)

    def testIntervalMonthsRange(self):
        out_of_range_months = (-2147483648, +2147483648,)
        in_range_months = (-2147483647, +2147483647,)
        self.intervalRangeTest("months", in_range_months, out_of_range_months)

    def testIntervalMicrosecondsRange(self):
        out_of_range_microseconds = (
            -9223372036854775808, +9223372036854775808,)
        in_range_microseconds = (
            -9223372036854775807, +9223372036854775807,)
        self.intervalRangeTest(
            "microseconds", in_range_microseconds, out_of_range_microseconds)

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_connection
import unittest
import pg8000
from pg8000.tests.connection_settings import db_connect
from pg8000.six import PY2, PRE_26


# Tests related to connecting to a database.
class Tests(unittest.TestCase):
    def testSocketMissing(self):
        conn_params = {
            'unix_sock': "/file-does-not-exist",
            'user': "doesn't-matter"}
        if 'use_cache' in db_connect:
            conn_params['use_cache'] = db_connect['use_cache']
        self.assertRaises(pg8000.InterfaceError, pg8000.connect, **conn_params)

    def testDatabaseMissing(self):
        data = db_connect.copy()
        data["database"] = "missing-db"
        self.assertRaises(pg8000.ProgrammingError, pg8000.connect, **data)

    def testNotify(self):

        try:
            db = pg8000.connect(**db_connect)
            self.assertEqual(db.notifies, [])
            cursor = db.cursor()
            cursor.execute("LISTEN test")
            cursor.execute("NOTIFY test")
            db.commit()

            cursor.execute("VALUES (1, 2), (3, 4), (5, 6)")
            self.assertEqual(len(db.notifies), 1)
            self.assertEqual(db.notifies[0][1], "test")
        finally:
            cursor.close()
            db.close()

    # This requires a line in pg_hba.conf that requires md5 for the database
    # pg8000_md5

    def testMd5(self):
        data = db_connect.copy()
        data["database"] = "pg8000_md5"

        # Should only raise an exception saying db doesn't exist
        if PY2:
            self.assertRaises(
                pg8000.ProgrammingError, pg8000.connect, **data)
        else:
            self.assertRaisesRegex(
                pg8000.ProgrammingError, '3D000', pg8000.connect, **data)

    def testSsl(self):
        data = db_connect.copy()
        data["ssl"] = True
        if PRE_26:
            self.assertRaises(pg8000.InterfaceError, pg8000.connect, **data)
        else:
            db = pg8000.connect(**data)
            db.close()

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_copy
import unittest
import pg8000
from .connection_settings import db_connect
from pg8000.six import b, BytesIO
from sys import exc_info


class Tests(unittest.TestCase):
    def setUp(self):
        self.db = pg8000.connect(**db_connect)
        try:
            cursor = self.db.cursor()
            try:
                cursor = self.db.cursor()
                cursor.execute("DROP TABLE t1")
            except pg8000.DatabaseError:
                e = exc_info()[1]
                # the only acceptable error is:
                self.assertEqual(
                    e.args[1], b('42P01'),  # table does not exist
                    "incorrect error for drop table")
                self.db.rollback()
            cursor.execute(
                "CREATE TEMPORARY TABLE t1 (f1 int primary key, "
                "f2 int not null, f3 varchar(50) null)")
        finally:
            cursor.close()

    def tearDown(self):
        self.db.close()

    def testCopyToWithTable(self):
        try:
            cursor = self.db.cursor()
            cursor.execute(
                "INSERT INTO t1 (f1, f2, f3) VALUES (%s, %s, %s)", (1, 1, 1))
            cursor.execute(
                "INSERT INTO t1 (f1, f2, f3) VALUES (%s, %s, %s)", (2, 2, 2))
            cursor.execute(
                "INSERT INTO t1 (f1, f2, f3) VALUES (%s, %s, %s)", (3, 3, 3))

            stream = BytesIO()
            cursor.copy_to(stream, "t1")
            self.assertEqual(
                stream.getvalue(), b("1\t1\t1\n2\t2\t2\n3\t3\t3\n"))
            self.assertEqual(cursor.rowcount, 3)
            self.db.commit()
        finally:
            cursor.close()

    def testCopyToWithQuery(self):
        try:
            cursor = self.db.cursor()
            stream = BytesIO()
            cursor.copy_to(
                stream, query="COPY (SELECT 1 as One, 2 as Two) TO STDOUT "
                "WITH DELIMITER 'X' CSV HEADER QUOTE AS 'Y' FORCE QUOTE Two")
            self.assertEqual(stream.getvalue(), b('oneXtwo\n1XY2Y\n'))
            self.assertEqual(cursor.rowcount, 1)
            self.db.rollback()
        finally:
            cursor.close()

    def testCopyFromWithTable(self):
        try:
            cursor = self.db.cursor()
            stream = BytesIO(b("1\t1\t1\n2\t2\t2\n3\t3\t3\n"))
            cursor.copy_from(stream, "t1")
            self.assertEqual(cursor.rowcount, 3)

            cursor.execute("SELECT * FROM t1 ORDER BY f1")
            retval = cursor.fetchall()
            self.assertEqual(retval, ([1, 1, '1'], [2, 2, '2'], [3, 3, '3']))
            self.db.rollback()
        finally:
            cursor.close()

    def testCopyFromWithQuery(self):
        try:
            cursor = self.db.cursor()
            stream = BytesIO(b("f1Xf2\n1XY1Y\n"))
            cursor.copy_from(
                stream, query="COPY t1 (f1, f2) FROM STDIN WITH DELIMITER "
                "'X' CSV HEADER QUOTE AS 'Y' FORCE NOT NULL f1")
            self.assertEqual(cursor.rowcount, 1)

            cursor.execute("SELECT * FROM t1 ORDER BY f1")
            retval = cursor.fetchall()
            self.assertEqual(retval, ([1, 1, None],))
            self.db.commit()
        finally:
            cursor.close()

    def testCopyWithoutTableOrQuery(self):
        try:
            cursor = self.db.cursor()
            stream = BytesIO()
            self.assertRaises(
                pg8000.CopyQueryOrTableRequiredError, cursor.copy_from, stream)
            self.assertRaises(
                pg8000.CopyQueryOrTableRequiredError, cursor.copy_to, stream)
            self.db.rollback()
        finally:
            cursor.close()


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_dbapi
import unittest
import os
import time
import pg8000
import datetime
from .connection_settings import db_connect
from sys import exc_info
from pg8000.six import b, IS_JYTHON


# DBAPI compatible interface tests
class Tests(unittest.TestCase):
    def setUp(self):
        self.db = pg8000.connect(**db_connect)
        # Jython 2.5.3 doesn't have a time.tzset() so skip
        if not IS_JYTHON:
            os.environ['TZ'] = "UTC"
            time.tzset()

        try:
            c = self.db.cursor()
            try:
                c = self.db.cursor()
                c.execute("DROP TABLE t1")
            except pg8000.DatabaseError:
                e = exc_info()[1]
                # the only acceptable error is:
                self.assertEqual(e.args[1], b('42P01'))  # table does not exist
                self.db.rollback()
            c.execute(
                "CREATE TEMPORARY TABLE t1 "
                "(f1 int primary key, f2 int not null, f3 varchar(50) null)")
            c.execute(
                "INSERT INTO t1 (f1, f2, f3) VALUES (%s, %s, %s)",
                (1, 1, None))
            c.execute(
                "INSERT INTO t1 (f1, f2, f3) VALUES (%s, %s, %s)",
                (2, 10, None))
            c.execute(
                "INSERT INTO t1 (f1, f2, f3) VALUES (%s, %s, %s)",
                (3, 100, None))
            c.execute(
                "INSERT INTO t1 (f1, f2, f3) VALUES (%s, %s, %s)",
                (4, 1000, None))
            c.execute(
                "INSERT INTO t1 (f1, f2, f3) VALUES (%s, %s, %s)",
                (5, 10000, None))
            self.db.commit()
        finally:
            c.close()

    def tearDown(self):
        self.db.close()

    def testParallelQueries(self):
        try:
            c1 = self.db.cursor()
            c2 = self.db.cursor()

            c1.execute("SELECT f1, f2, f3 FROM t1")
            while 1:
                row = c1.fetchone()
                if row is None:
                    break
                f1, f2, f3 = row
                c2.execute("SELECT f1, f2, f3 FROM t1 WHERE f1 > %s", (f1,))
                while 1:
                    row = c2.fetchone()
                    if row is None:
                        break
                    f1, f2, f3 = row
        finally:
            c1.close()
            c2.close()

        self.db.rollback()

    def testQmark(self):
        orig_paramstyle = pg8000.paramstyle
        try:
            pg8000.paramstyle = "qmark"
            c1 = self.db.cursor()
            c1.execute("SELECT f1, f2, f3 FROM t1 WHERE f1 > ?", (3,))
            while 1:
                row = c1.fetchone()
                if row is None:
                    break
                f1, f2, f3 = row
            self.db.rollback()
        finally:
            pg8000.paramstyle = orig_paramstyle
            c1.close()

    def testNumeric(self):
        orig_paramstyle = pg8000.paramstyle
        try:
            pg8000.paramstyle = "numeric"
            c1 = self.db.cursor()
            c1.execute("SELECT f1, f2, f3 FROM t1 WHERE f1 > :1", (3,))
            while 1:
                row = c1.fetchone()
                if row is None:
                    break
                f1, f2, f3 = row
            self.db.rollback()
        finally:
            pg8000.paramstyle = orig_paramstyle
            c1.close()

    def testNamed(self):
        orig_paramstyle = pg8000.paramstyle
        try:
            pg8000.paramstyle = "named"
            c1 = self.db.cursor()
            c1.execute(
                "SELECT f1, f2, f3 FROM t1 WHERE f1 > :f1", {"f1": 3})
            while 1:
                row = c1.fetchone()
                if row is None:
                    break
                f1, f2, f3 = row
            self.db.rollback()
        finally:
            pg8000.paramstyle = orig_paramstyle
            c1.close()

    def testFormat(self):
        orig_paramstyle = pg8000.paramstyle
        try:
            pg8000.paramstyle = "format"
            c1 = self.db.cursor()
            c1.execute("SELECT f1, f2, f3 FROM t1 WHERE f1 > %s", (3,))
            while 1:
                row = c1.fetchone()
                if row is None:
                    break
                f1, f2, f3 = row
            self.db.commit()
        finally:
            pg8000.paramstyle = orig_paramstyle
            c1.close()

    def testPyformat(self):
        orig_paramstyle = pg8000.paramstyle
        try:
            pg8000.paramstyle = "pyformat"
            c1 = self.db.cursor()
            c1.execute(
                "SELECT f1, f2, f3 FROM t1 WHERE f1 > %(f1)s", {"f1": 3})
            while 1:
                row = c1.fetchone()
                if row is None:
                    break
                f1, f2, f3 = row
            self.db.commit()
        finally:
            pg8000.paramstyle = orig_paramstyle
            c1.close()

    def testArraysize(self):
        try:
            c1 = self.db.cursor()
            c1.arraysize = 3
            c1.execute("SELECT * FROM t1")
            retval = c1.fetchmany()
            self.assertEqual(len(retval), c1.arraysize)
        finally:
            c1.close()
        self.db.commit()

    def testDate(self):
        val = pg8000.Date(2001, 2, 3)
        self.assertEqual(val, datetime.date(2001, 2, 3))

    def testTime(self):
        val = pg8000.Time(4, 5, 6)
        self.assertEqual(val, datetime.time(4, 5, 6))

    def testTimestamp(self):
        val = pg8000.Timestamp(2001, 2, 3, 4, 5, 6)
        self.assertEqual(val, datetime.datetime(2001, 2, 3, 4, 5, 6))

    def testDateFromTicks(self):
        if IS_JYTHON:
            return

        val = pg8000.DateFromTicks(1173804319)
        self.assertEqual(val, datetime.date(2007, 3, 13))

    def testTimeFromTicks(self):
        if IS_JYTHON:
            return

        val = pg8000.TimeFromTicks(1173804319)
        self.assertEqual(val, datetime.time(16, 45, 19))

    def testTimestampFromTicks(self):
        if IS_JYTHON:
            return

        val = pg8000.TimestampFromTicks(1173804319)
        self.assertEqual(val, datetime.datetime(2007, 3, 13, 16, 45, 19))

    def testBinary(self):
        v = pg8000.Binary(b("\x00\x01\x02\x03\x02\x01\x00"))
        self.assertEqual(v, b("\x00\x01\x02\x03\x02\x01\x00"))
        self.assertTrue(isinstance(v, pg8000.BINARY))

    def testRowCount(self):
        try:
            c1 = self.db.cursor()
            c1.execute("SELECT * FROM t1")

            # In PostgreSQL 8.4 we don't know the row count for a select
            if not self.db._server_version.startswith("8.4"):
                self.assertEqual(5, c1.rowcount)

            c1.execute("UPDATE t1 SET f3 = %s WHERE f2 > 101", ("Hello!",))
            self.assertEqual(2, c1.rowcount)

            c1.execute("DELETE FROM t1")
            self.assertEqual(5, c1.rowcount)
        finally:
            c1.close()
        self.db.commit()

    def testFetchMany(self):
        try:
            cursor = self.db.cursor()
            cursor.arraysize = 2
            cursor.execute("SELECT * FROM t1")
            self.assertEqual(2, len(cursor.fetchmany()))
            self.assertEqual(2, len(cursor.fetchmany()))
            self.assertEqual(1, len(cursor.fetchmany()))
            self.assertEqual(0, len(cursor.fetchmany()))
        finally:
            cursor.close()
        self.db.commit()

    def testIterator(self):
        from warnings import filterwarnings
        filterwarnings("ignore", "DB-API extension cursor.next()")
        filterwarnings("ignore", "DB-API extension cursor.__iter__()")

        try:
            cursor = self.db.cursor()
            cursor.execute("SELECT * FROM t1 ORDER BY f1")
            f1 = 0
            for row in cursor:
                next_f1 = row[0]
                assert next_f1 > f1
                f1 = next_f1
        except:
            cursor.close()

        self.db.commit()

    # Vacuum can't be run inside a transaction, so we need to turn
    # autocommit on.
    def testVacuum(self):
        self.db.autocommit = True
        try:
            cursor = self.db.cursor()
            cursor.execute("vacuum")
        finally:
            cursor.close()

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_error_recovery
import unittest
import pg8000
from .connection_settings import db_connect
import warnings
import datetime
from sys import exc_info
from pg8000.six import b


class TestException(Exception):
    pass


class Tests(unittest.TestCase):
    def setUp(self):
        self.db = pg8000.connect(**db_connect)

    def tearDown(self):
        self.db.close()

    def raiseException(self, value):
        raise TestException("oh noes!")

    def testPyValueFail(self):
        # Ensure that if types.py_value throws an exception, the original
        # exception is raised (TestException), and the connection is
        # still usable after the error.
        orig = self.db.py_types[datetime.time]
        self.db.py_types[datetime.time] = (
            orig[0], orig[1], self.raiseException)

        try:
            c = self.db.cursor()
            try:
                try:
                    c.execute("SELECT %s as f1", (datetime.time(10, 30),))
                    c.fetchall()
                    # shouldn't get here, exception should be thrown
                    self.fail()
                except TestException:
                    # should be TestException type, this is OK!
                    self.db.rollback()
            finally:
                self.db.py_types[datetime.time] = orig

            # ensure that the connection is still usable for a new query
            c.execute("VALUES ('hw3'::text)")
            self.assertEqual(c.fetchone()[0], "hw3")
        finally:
            c.close()

    def testNoDataErrorRecovery(self):
        for i in range(1, 4):
            try:
                try:
                    cursor = self.db.cursor()
                    cursor.execute("DROP TABLE t1")
                finally:
                    cursor.close()
            except pg8000.DatabaseError:
                e = exc_info()[1]
                # the only acceptable error is:
                self.assertEqual(e.args[1], b('42P01'))  # table does not exist
                self.db.rollback()

    def testClosedConnection(self):
        warnings.simplefilter("ignore")
        my_db = pg8000.connect(**db_connect)
        cursor = my_db.cursor()
        my_db.close()
        self.assertRaises(
            self.db.InterfaceError, cursor.execute, "VALUES ('hw1'::text)")
        warnings.resetwarnings()

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_paramstyle
import unittest
import pg8000


# Tests of the convert_paramstyle function.
class Tests(unittest.TestCase):
    def testQmark(self):
        new_query, make_args = pg8000.core.convert_paramstyle(
            "qmark", "SELECT ?, ?, \"field_?\" FROM t "
            "WHERE a='say ''what?''' AND b=? AND c=E'?\\'test\\'?'")
        self.assertEqual(
            new_query, "SELECT $1, $2, \"field_?\" FROM t WHERE "
            "a='say ''what?''' AND b=$3 AND c=E'?\\'test\\'?'")
        self.assertEqual(make_args((1, 2, 3)), (1, 2, 3))

    def testQmark2(self):
        new_query, make_args = pg8000.core.convert_paramstyle(
            "qmark", "SELECT ?, ?, * FROM t WHERE a=? AND b='are you ''sure?'")
        self.assertEqual(
            new_query,
            "SELECT $1, $2, * FROM t WHERE a=$3 AND b='are you ''sure?'")
        self.assertEqual(make_args((1, 2, 3)), (1, 2, 3))

    def testNumeric(self):
        new_query, make_args = pg8000.core.convert_paramstyle(
            "numeric", "SELECT :2, :1, * FROM t WHERE a=:3")
        self.assertEqual(new_query, "SELECT $2, $1, * FROM t WHERE a=$3")
        self.assertEqual(make_args((1, 2, 3)), (1, 2, 3))

    def testNamed(self):
        new_query, make_args = pg8000.core.convert_paramstyle(
            "named", "SELECT :f_2, :f1 FROM t WHERE a=:f_2")
        self.assertEqual(new_query, "SELECT $1, $2 FROM t WHERE a=$1")
        self.assertEqual(make_args({"f_2": 1, "f1": 2}), (1, 2))

    def testFormat(self):
        new_query, make_args = pg8000.core.convert_paramstyle(
            "format", "SELECT %s, %s, \"f1_%%\", E'txt_%%' "
            "FROM t WHERE a=%s AND b='75%%'")
        self.assertEqual(
            new_query,
            "SELECT $1, $2, \"f1_%\", E'txt_%' FROM t WHERE a=$3 AND b='75%'")
        self.assertEqual(make_args((1, 2, 3)), (1, 2, 3))

    def testPyformat(self):
        new_query, make_args = pg8000.core.convert_paramstyle(
            "pyformat", "SELECT %(f2)s, %(f1)s, \"f1_%%\", E'txt_%%' "
            "FROM t WHERE a=%(f2)s AND b='75%%'")
        self.assertEqual(
            new_query,
            "SELECT $1, $2, \"f1_%\", E'txt_%' FROM t WHERE a=$1 AND b='75%'")
        self.assertEqual(make_args({"f2": 1, "f1": 2, "f3": 3}), (1, 2))

        # pyformat should support %s and an array, too:
        new_query, make_args = pg8000.core.convert_paramstyle(
            "pyformat", "SELECT %s, %s, \"f1_%%\", E'txt_%%' "
            "FROM t WHERE a=%s AND b='75%%'")
        self.assertEqual(
            new_query,
            "SELECT $1, $2, \"f1_%\", E'txt_%' FROM t WHERE a=$3 AND b='75%'")
        self.assertEqual(make_args((1, 2, 3)), (1, 2, 3))

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_pg8000_dbapi20
#!/usr/bin/env python
from . import dbapi20
import unittest
import pg8000
from .connection_settings import db_connect


class Tests(dbapi20.DatabaseAPI20Test):
    driver = pg8000.DBAPI
    connect_args = ()
    connect_kw_args = db_connect

    lower_func = 'lower'  # For stored procedure test

    def test_nextset(self):
        pass

    def test_setoutputsize(self):
        pass

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_query
import unittest
import threading
import pg8000
from .connection_settings import db_connect
from pg8000.six import u, b
from sys import exc_info
import datetime


from warnings import filterwarnings


# Tests relating to the basic operation of the database driver, driven by the
# pg8000 custom interface.
class Tests(unittest.TestCase):
    def setUp(self):
        self.db = pg8000.connect(**db_connect)
        filterwarnings("ignore", "DB-API extension cursor.next()")
        filterwarnings("ignore", "DB-API extension cursor.__iter__()")
        self.db.paramstyle = 'format'
        try:
            cursor = self.db.cursor()
            try:
                cursor.execute("DROP TABLE t1")
            except pg8000.DatabaseError:
                e = exc_info()[1]
                # the only acceptable error is:
                self.assertEqual(e.args[1], b('42P01'))  # table does not exist
                self.db.rollback()
            cursor.execute(
                "CREATE TEMPORARY TABLE t1 (f1 int primary key, "
                "f2 bigint not null, f3 varchar(50) null)")
        finally:
            cursor.close()

        self.db.commit()

    def tearDown(self):
        self.db.close()

    def testDatabaseError(self):
        try:
            cursor = self.db.cursor()
            self.assertRaises(
                pg8000.ProgrammingError, cursor.execute,
                "INSERT INTO t99 VALUES (1, 2, 3)")
        finally:
            cursor.close()

        self.db.rollback()

    def testParallelQueries(self):
        try:
            cursor = self.db.cursor()
            cursor.execute(
                "INSERT INTO t1 (f1, f2, f3) VALUES (%s, %s, %s)",
                (1, 1, None))
            cursor.execute(
                "INSERT INTO t1 (f1, f2, f3) VALUES (%s, %s, %s)",
                (2, 10, None))
            cursor.execute(
                "INSERT INTO t1 (f1, f2, f3) VALUES (%s, %s, %s)",
                (3, 100, None))
            cursor.execute(
                "INSERT INTO t1 (f1, f2, f3) VALUES (%s, %s, %s)",
                (4, 1000, None))
            cursor.execute(
                "INSERT INTO t1 (f1, f2, f3) VALUES (%s, %s, %s)",
                (5, 10000, None))
            try:
                c1 = self.db.cursor()
                c2 = self.db.cursor()
                c1.execute("SELECT f1, f2, f3 FROM t1")
                for row in c1:
                    f1, f2, f3 = row
                    c2.execute(
                        "SELECT f1, f2, f3 FROM t1 WHERE f1 > %s", (f1,))
                    for row in c2:
                        f1, f2, f3 = row
            finally:
                c1.close()
                c2.close()
        finally:
            cursor.close()
        self.db.rollback()

    def testInsertReturning(self):
        try:
            cursor = self.db.cursor()
            cursor.execute("CREATE TABLE t2 (id serial, data text)")

            # Test INSERT ... RETURNING with one row...
            cursor.execute(
                "INSERT INTO t2 (data) VALUES (%s) RETURNING id",
                ("test1",))
            row_id = cursor.fetchone()[0]
            cursor.execute("SELECT data FROM t2 WHERE id = %s", (row_id,))
            self.assertEqual("test1", cursor.fetchone()[0])

            # In PostgreSQL 8.4 we don't know the row count for a select
            if not self.db._server_version.startswith("8.4"):
                self.assertEqual(cursor.rowcount, 1)

            # Test with multiple rows...
            cursor.execute(
                "INSERT INTO t2 (data) VALUES (%s), (%s), (%s) "
                "RETURNING id", ("test2", "test3", "test4"))
            self.assertEqual(cursor.rowcount, 3)
            ids = tuple([x[0] for x in cursor])
            self.assertEqual(len(ids), 3)
        finally:
            cursor.close()
            self.db.rollback()

    def testMultithreadedCursor(self):
        try:
            cursor = self.db.cursor()
            # Note: Multithreading with a cursor is not highly recommended due
            # to low performance.

            def test(left, right):
                for i in range(left, right):
                    cursor.execute(
                        "INSERT INTO t1 (f1, f2, f3) VALUES (%s, %s, %s)",
                        (i, id(threading.currentThread()), None))
            t1 = threading.Thread(target=test, args=(1, 25))
            t2 = threading.Thread(target=test, args=(25, 50))
            t3 = threading.Thread(target=test, args=(50, 75))
            t1.start()
            t2.start()
            t3.start()
            t1.join()
            t2.join()
            t3.join()
        finally:
            cursor.close()
            self.db.rollback()

    def testRowCount(self):
        # In PostgreSQL 8.4 we don't know the row count for a select
        if not self.db._server_version.startswith("8.4"):
            try:
                cursor = self.db.cursor()
                expected_count = 57
                cursor.executemany(
                    "INSERT INTO t1 (f1, f2, f3) VALUES (%s, %s, %s)",
                    tuple((i, i, None) for i in range(expected_count)))
                self.db.commit()

                cursor.execute("SELECT * FROM t1")

                # Check row_count without doing any reading first...
                self.assertEqual(expected_count, cursor.rowcount)

                # Check rowcount after reading some rows, make sure it still
                # works...
                for i in range(expected_count // 2):
                    cursor.fetchone()
                self.assertEqual(expected_count, cursor.rowcount)
            finally:
                cursor.close()
                self.db.commit()

            try:
                cursor = self.db.cursor()
                # Restart the cursor, read a few rows, and then check rowcount
                # again...
                cursor = self.db.cursor()
                cursor.execute("SELECT * FROM t1")
                for i in range(expected_count // 3):
                    cursor.fetchone()
                self.assertEqual(expected_count, cursor.rowcount)
                self.db.rollback()

                # Should be -1 for a command with no results
                cursor.execute("DROP TABLE t1")
                self.assertEqual(-1, cursor.rowcount)
            finally:
                cursor.close()
                self.db.commit()

    def testRowCountUpdate(self):
        try:
            cursor = self.db.cursor()
            cursor.execute(
                "INSERT INTO t1 (f1, f2, f3) VALUES (%s, %s, %s)",
                (1, 1, None))
            cursor.execute(
                "INSERT INTO t1 (f1, f2, f3) VALUES (%s, %s, %s)",
                (2, 10, None))
            cursor.execute(
                "INSERT INTO t1 (f1, f2, f3) VALUES (%s, %s, %s)",
                (3, 100, None))
            cursor.execute(
                "INSERT INTO t1 (f1, f2, f3) VALUES (%s, %s, %s)",
                (4, 1000, None))
            cursor.execute(
                "INSERT INTO t1 (f1, f2, f3) VALUES (%s, %s, %s)",
                (5, 10000, None))
            cursor.execute("UPDATE t1 SET f3 = %s WHERE f2 > 101", ("Hello!",))
            self.assertEqual(cursor.rowcount, 2)
        finally:
            cursor.close()
            self.db.commit()

    def testIntOid(self):
        try:
            cursor = self.db.cursor()
            # https://bugs.launchpad.net/pg8000/+bug/230796
            cursor.execute(
                "SELECT typname FROM pg_type WHERE oid = %s", (100,))
        finally:
            cursor.close()
            self.db.rollback()

    def testUnicodeQuery(self):
        try:
            cursor = self.db.cursor()
            cursor.execute(
                u(
                    "CREATE TEMPORARY TABLE \u043c\u0435\u0441\u0442\u043e "
                    "(\u0438\u043c\u044f VARCHAR(50), "
                    "\u0430\u0434\u0440\u0435\u0441 VARCHAR(250))"))
        finally:
            cursor.close()
            self.db.commit()

    def testExecutemany(self):
        try:
            cursor = self.db.cursor()
            cursor.executemany(
                "INSERT INTO t1 (f1, f2, f3) VALUES (%s, %s, %s)",
                ((1, 1, 'Avast ye!'), (2, 1, None)))

            cursor.executemany(
                "select %s",
                (
                    (datetime.datetime(2014, 5, 7, tzinfo=pg8000.core.utc), ),
                    (datetime.datetime(2014, 5, 7),)))
        finally:
            cursor.close()
            self.db.commit()

    # Check that autocommit stays off
    # We keep track of whether we're in a transaction or not by using the
    # READY_FOR_QUERY message.
    def testTransactions(self):
        try:
            cursor = self.db.cursor()
            cursor.execute("commit")
            cursor.execute(
                "INSERT INTO t1 (f1, f2, f3) VALUES (%s, %s, %s)",
                (1, 1, "Zombie"))
            cursor.execute("rollback")
            cursor.execute("select * from t1")
            self.assertEqual(cursor.rowcount, 0)
        finally:
            cursor.close()
            self.db.commit()

    def testIn(self):
        try:
            cursor = self.db.cursor()
            cursor.execute(
                "SELECT typname FROM pg_type WHERE oid = any(%s)", ([16, 23],))
            ret = cursor.fetchall()
            self.assertEqual(ret[0][0], 'bool')
        finally:
            cursor.close()

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_typeconversion
import unittest
import pg8000
import datetime
import decimal
import struct
from .connection_settings import db_connect
from pg8000.six import b, IS_JYTHON, text_type
import uuid
import os
import time


if not IS_JYTHON:
    import pytz


# Type conversion tests
class Tests(unittest.TestCase):
    def setUp(self):
        self.db = pg8000.connect(**db_connect)
        self.cursor = self.db.cursor()

    def tearDown(self):
        self.cursor.close()
        self.cursor = None
        self.db.close()

    def testTimeRoundtrip(self):
        self.cursor.execute("SELECT %s as f1", (datetime.time(4, 5, 6),))
        retval = self.cursor.fetchall()
        self.assertEqual(retval[0][0], datetime.time(4, 5, 6))

    def testDateRoundtrip(self):
        self.cursor.execute("SELECT %s as f1", (datetime.date(2001, 2, 3),))
        retval = self.cursor.fetchall()
        self.assertEqual(retval[0][0], datetime.date(2001, 2, 3))

    def testBoolRoundtrip(self):
        self.cursor.execute("SELECT %s as f1", (True,))
        retval = self.cursor.fetchall()
        self.assertEqual(retval[0][0], True)

    def testNullRoundtrip(self):
        # We can't just "SELECT %s" and set None as the parameter, since it has
        # no type.  That would result in a PG error, "could not determine data
        # type of parameter %s".  So we create a temporary table, insert null
        # values, and read them back.
        self.cursor.execute(
            "CREATE TEMPORARY TABLE TestNullWrite "
            "(f1 int4, f2 timestamp, f3 varchar)")
        self.cursor.execute(
            "INSERT INTO TestNullWrite VALUES (%s, %s, %s)",
            (None, None, None,))
        self.cursor.execute("SELECT * FROM TestNullWrite")
        retval = self.cursor.fetchone()
        self.assertEqual(retval, [None, None, None])

    def testNullSelectFailure(self):
        # See comment in TestNullRoundtrip.  This test is here to ensure that
        # this behaviour is documented and doesn't mysteriously change.
        self.assertRaises(
            pg8000.ProgrammingError, self.cursor.execute,
            "SELECT %s as f1", (None,))
        self.db.rollback()

    def testDecimalRoundtrip(self):
        values = (
            "1.1", "-1.1", "10000", "20000", "-1000000000.123456789", "1.0",
            "12.44")
        for v in values:
            self.cursor.execute("SELECT %s as f1", (decimal.Decimal(v),))
            retval = self.cursor.fetchall()
            self.assertEqual(str(retval[0][0]), v)

    def testFloatRoundtrip(self):
        # This test ensures that the binary float value doesn't change in a
        # roundtrip to the server.  That could happen if the value was
        # converted to text and got rounded by a decimal place somewhere.
        val = 1.756e-12
        bin_orig = struct.pack("!d", val)
        self.cursor.execute("SELECT %s as f1", (val,))
        retval = self.cursor.fetchall()
        bin_new = struct.pack("!d", retval[0][0])
        self.assertEqual(bin_new, bin_orig)

    def testStrRoundtrip(self):
        v = "hello world"
        self.cursor.execute(
            "create temporary table test_str (f character varying(255))")
        self.cursor.execute("INSERT INTO test_str VALUES (%s)", (v,))
        self.cursor.execute("SELECT * from test_str")
        retval = self.cursor.fetchall()
        self.assertEqual(retval[0][0], v)

    def testUnicodeRoundtrip(self):
        self.cursor.execute(
            "SELECT cast(%s as varchar) as f1", ("hello \u0173 world",))
        retval = self.cursor.fetchall()
        self.assertEqual(retval[0][0], "hello \u0173 world")

        v = text_type("hello \u0173 world")
        self.cursor.execute("SELECT cast(%s as varchar) as f1", (v,))
        retval = self.cursor.fetchall()
        self.assertEqual(retval[0][0], v)

    def testLongRoundtrip(self):
        self.cursor.execute(
            "SELECT cast(%s as bigint)", (50000000000000,))
        retval = self.cursor.fetchall()
        self.assertEqual(retval[0][0], 50000000000000)

    def testIntExecuteMany(self):
        self.cursor.executemany("SELECT cast(%s as integer)", ((1,), (40000,)))
        self.cursor.fetchall()

        v = ([None], [4])
        self.cursor.execute(
            "create temporary table test_int (f integer)")
        self.cursor.executemany("INSERT INTO test_int VALUES (%s)", v)
        self.cursor.execute("SELECT * from test_int")
        retval = self.cursor.fetchall()
        self.assertEqual(retval, v)

    def testIntRoundtrip(self):
        int2 = 21
        int4 = 23
        int8 = 20

        test_values = [
            (0, int2, 'smallint'),
            (-32767, int2, 'smallint'),
            (-32768, int4, 'integer'),
            (+32767, int2, 'smallint'),
            (+32768, int4, 'integer'),
            (-2147483647, int4, 'integer'),
            (-2147483648, int8, 'bigint'),
            (+2147483647, int4, 'integer'),
            (+2147483648, int8, 'bigint'),
            (-9223372036854775807, int8, 'bigint'),
            (+9223372036854775807, int8, 'bigint'), ]

        for value, typoid, tp in test_values:
            self.cursor.execute("SELECT cast(%s as " + tp + ")", (value,))
            retval = self.cursor.fetchall()
            self.assertEqual(retval[0][0], value)
            column_name, column_typeoid = self.cursor.description[0][0:2]
            self.assertEqual(column_typeoid, typoid)

    def testByteaRoundtrip(self):
        self.cursor.execute(
            "SELECT %s as f1",
            (pg8000.Binary(b("\x00\x01\x02\x03\x02\x01\x00")),))
        retval = self.cursor.fetchall()
        self.assertEqual(retval[0][0], b("\x00\x01\x02\x03\x02\x01\x00"))

    def testTimestampRoundtrip(self):
        v = datetime.datetime(2001, 2, 3, 4, 5, 6, 170000)
        self.cursor.execute("SELECT %s as f1", (v,))
        retval = self.cursor.fetchall()
        self.assertEqual(retval[0][0], v)

        # Test that time zone doesn't affect it
        # Jython 2.5.3 doesn't have a time.tzset() so skip
        if not IS_JYTHON:
            orig_tz = os.environ['TZ']
            os.environ['TZ'] = "America/Edmonton"
            time.tzset()

            self.cursor.execute("SELECT %s as f1", (v,))
            retval = self.cursor.fetchall()
            self.assertEqual(retval[0][0], v)

            os.environ['TZ'] = orig_tz
            time.tzset()

    def testIntervalRoundtrip(self):
        v = pg8000.Interval(microseconds=123456789, days=2, months=24)
        self.cursor.execute("SELECT %s as f1", (v,))
        retval = self.cursor.fetchall()
        self.assertEqual(retval[0][0], v)

        v = datetime.timedelta(seconds=30)
        self.cursor.execute("SELECT %s as f1", (v,))
        retval = self.cursor.fetchall()
        self.assertEqual(retval[0][0], v)

    def testEnumRoundtrip(self):
        try:
            self.cursor.execute(
                "create type lepton as enum ('electron', 'muon', 'tau')")
        except pg8000.ProgrammingError:
            self.db.rollback()

        v = 'muon'
        self.cursor.execute("SELECT cast(%s as lepton) as f1", (v,))
        retval = self.cursor.fetchall()
        self.assertEqual(retval[0][0], v)
        self.cursor.execute(
            "CREATE TEMPORARY TABLE testenum "
            "(f1 lepton)")
        self.cursor.execute("INSERT INTO testenum VALUES (%s)", ('electron',))
        self.cursor.execute("drop table testenum")
        self.cursor.execute("drop type lepton")
        self.db.commit()

    def testXmlRoundtrip(self):
        v = '<genome>gatccgagtac</genome>'
        self.cursor.execute("select xmlparse(content %s) as f1", (v,))
        retval = self.cursor.fetchall()
        self.assertEqual(retval[0][0], v)

    def testUuidRoundtrip(self):
        v = uuid.UUID('911460f2-1f43-fea2-3e2c-e01fd5b5069d')
        self.cursor.execute("select %s as f1", (v,))
        retval = self.cursor.fetchall()
        self.assertEqual(retval[0][0], v)

    def testInetRoundtrip(self):
        try:
            import ipaddress

            v = ipaddress.ip_network('192.168.0.0/28')
            self.cursor.execute("select %s as f1", (v,))
            retval = self.cursor.fetchall()
            self.assertEqual(retval[0][0], v)

            v = ipaddress.ip_address('192.168.0.1')
            self.cursor.execute("select %s as f1", (v,))
            retval = self.cursor.fetchall()
            self.assertEqual(retval[0][0], v)

        except ImportError:
            for v in ('192.168.100.128/25', '192.168.0.1'):
                self.cursor.execute(
                    "select cast(cast(%s as varchar) as inet) as f1", (v,))
                retval = self.cursor.fetchall()
                self.assertEqual(retval[0][0], v)

    def testXidRoundtrip(self):
        v = 86722
        self.cursor.execute(
            "select cast(cast(%s as varchar) as xid) as f1", (v,))
        retval = self.cursor.fetchall()
        self.assertEqual(retval[0][0], v)

        # Should complete without an exception
        self.cursor.execute(
            "select * from pg_locks where transactionid = %s", (97712,))
        retval = self.cursor.fetchall()

    def testInt2VectorIn(self):
        self.cursor.execute("select cast('1 2' as int2vector) as f1")
        retval = self.cursor.fetchall()
        self.assertEqual(retval[0][0], [1, 2])

        # Should complete without an exception
        self.cursor.execute("select indkey from pg_index")
        retval = self.cursor.fetchall()

    def testTimestampTzOut(self):
        self.cursor.execute(
            "SELECT '2001-02-03 04:05:06.17 America/Edmonton'"
            "::timestamp with time zone")
        retval = self.cursor.fetchall()
        dt = retval[0][0]
        self.assertEqual(dt.tzinfo is not None, True, "no tzinfo returned")
        self.assertEqual(
            dt.astimezone(pg8000.utc),
            datetime.datetime(2001, 2, 3, 11, 5, 6, 170000, pg8000.utc),
            "retrieved value match failed")

    def testTimestampTzRoundtrip(self):
        if not IS_JYTHON:
            mst = pytz.timezone("America/Edmonton")
            v1 = mst.localize(datetime.datetime(2001, 2, 3, 4, 5, 6, 170000))
            self.cursor.execute("SELECT %s as f1", (v1,))
            retval = self.cursor.fetchall()
            v2 = retval[0][0]
            self.assertNotEqual(v2.tzinfo, None)
            self.assertEqual(v1, v2)

    def testTimestampMismatch(self):
        if not IS_JYTHON:
            mst = pytz.timezone("America/Edmonton")
            self.cursor.execute("SET SESSION TIME ZONE 'America/Edmonton'")
            try:
                self.cursor.execute(
                    "CREATE TEMPORARY TABLE TestTz "
                    "(f1 timestamp with time zone, "
                    "f2 timestamp without time zone)")
                self.cursor.execute(
                    "INSERT INTO TestTz (f1, f2) VALUES (%s, %s)", (
                        # insert timestamp into timestamptz field (v1)
                        datetime.datetime(2001, 2, 3, 4, 5, 6, 170000),
                        # insert timestamptz into timestamp field (v2)
                        mst.localize(datetime.datetime(
                            2001, 2, 3, 4, 5, 6, 170000))))
                self.cursor.execute("SELECT f1, f2 FROM TestTz")
                retval = self.cursor.fetchall()

                # when inserting a timestamp into a timestamptz field,
                # postgresql assumes that it is in local time. So the value
                # that comes out will be the server's local time interpretation
                # of v1. We've set the server's TZ to MST, the time should
                # be...
                f1 = retval[0][0]
                self.assertEqual(
                    f1, datetime.datetime(
                        2001, 2, 3, 11, 5, 6, 170000, pytz.utc))

                # inserting the timestamptz into a timestamp field, pg8000
                # converts the value into UTC, and then the PG server converts
                # it into local time for insertion into the field. When we
                # query for it, we get the same time back, like the tz was
                # dropped.
                f2 = retval[0][1]
                self.assertEqual(
                    f2, datetime.datetime(2001, 2, 3, 4, 5, 6, 170000))
            finally:
                self.cursor.execute("SET SESSION TIME ZONE DEFAULT")

    def testNameOut(self):
        # select a field that is of "name" type:
        self.cursor.execute("SELECT usename FROM pg_user")
        self.cursor.fetchall()
        # It is sufficient that no errors were encountered.

    def testOidOut(self):
        self.cursor.execute("SELECT oid FROM pg_type")
        self.cursor.fetchall()
        # It is sufficient that no errors were encountered.

    def testBooleanOut(self):
        self.cursor.execute("SELECT cast('t' as bool)")
        retval = self.cursor.fetchall()
        self.assertTrue(retval[0][0])

    def testNumericOut(self):
        for num in ('5000', '50.34'):
            self.cursor.execute("SELECT " + num + "::numeric")
            retval = self.cursor.fetchall()
            self.assertEqual(str(retval[0][0]), num)

    def testInt2Out(self):
        self.cursor.execute("SELECT 5000::smallint")
        retval = self.cursor.fetchall()
        self.assertEqual(retval[0][0], 5000)

    def testInt4Out(self):
        self.cursor.execute("SELECT 5000::integer")
        retval = self.cursor.fetchall()
        self.assertEqual(retval[0][0], 5000)

    def testInt8Out(self):
        self.cursor.execute("SELECT 50000000000000::bigint")
        retval = self.cursor.fetchall()
        self.assertEqual(retval[0][0], 50000000000000)

    def testFloat4Out(self):
        self.cursor.execute("SELECT 1.1::real")
        retval = self.cursor.fetchall()
        self.assertEqual(retval[0][0], 1.1000000238418579)

    def testFloat8Out(self):
        self.cursor.execute("SELECT 1.1::double precision")
        retval = self.cursor.fetchall()
        self.assertEqual(retval[0][0], 1.1000000000000001)

    def testVarcharOut(self):
        self.cursor.execute("SELECT 'hello'::varchar(20)")
        retval = self.cursor.fetchall()
        self.assertEqual(retval[0][0], "hello")

    def testCharOut(self):
        self.cursor.execute("SELECT 'hello'::char(20)")
        retval = self.cursor.fetchall()
        self.assertEqual(retval[0][0], "hello               ")

    def testTextOut(self):
        self.cursor.execute("SELECT 'hello'::text")
        retval = self.cursor.fetchall()
        self.assertEqual(retval[0][0], "hello")

    def testIntervalOut(self):
        self.cursor.execute(
            "SELECT '1 month 16 days 12 hours 32 minutes 64 seconds'"
            "::interval")
        retval = self.cursor.fetchall()
        expected_value = pg8000.Interval(
            microseconds=(12 * 60 * 60 * 1000 * 1000) +
            (32 * 60 * 1000 * 1000) + (64 * 1000 * 1000),
            days=16, months=1)
        self.assertEqual(retval[0][0], expected_value)

        self.cursor.execute("select interval '30 seconds'")
        retval = self.cursor.fetchall()
        expected_value = datetime.timedelta(seconds=30)
        self.assertEqual(retval[0][0], expected_value)

        self.cursor.execute("select interval '12 days 30 seconds'")
        retval = self.cursor.fetchall()
        expected_value = datetime.timedelta(days=12, seconds=30)
        self.assertEqual(retval[0][0], expected_value)

    def testTimestampOut(self):
        self.cursor.execute("SELECT '2001-02-03 04:05:06.17'::timestamp")
        retval = self.cursor.fetchall()
        self.assertEqual(
            retval[0][0], datetime.datetime(2001, 2, 3, 4, 5, 6, 170000))

    # confirms that pg8000's binary output methods have the same output for
    # a data type as the PG server
    def testBinaryOutputMethods(self):
        methods = (
            ("float8send", 22.2),
            ("timestamp_send", datetime.datetime(2001, 2, 3, 4, 5, 6, 789)),
            ("byteasend", pg8000.Binary(b("\x01\x02"))),
            ("interval_send", pg8000.Interval(1234567, 123, 123)),)
        for method_out, value in methods:
            self.cursor.execute("SELECT %s(%%s) as f1" % method_out, (value,))
            retval = self.cursor.fetchall()
            self.assertEqual(
                retval[0][0], self.db.make_params((value,))[0][2](value))

    def testInt4ArrayOut(self):
        self.cursor.execute(
            "SELECT '{1,2,3,4}'::INT[] AS f1, "
            "'{{1,2,3},{4,5,6}}'::INT[][] AS f2, "
            "'{{{1,2},{3,4}},{{NULL,6},{7,8}}}'::INT[][][] AS f3")
        f1, f2, f3 = self.cursor.fetchone()
        self.assertEqual(f1, [1, 2, 3, 4])
        self.assertEqual(f2, [[1, 2, 3], [4, 5, 6]])
        self.assertEqual(f3, [[[1, 2], [3, 4]], [[None, 6], [7, 8]]])

    def testInt2ArrayOut(self):
        self.cursor.execute(
            "SELECT '{1,2,3,4}'::INT2[] AS f1, "
            "'{{1,2,3},{4,5,6}}'::INT2[][] AS f2, "
            "'{{{1,2},{3,4}},{{NULL,6},{7,8}}}'::INT2[][][] AS f3")
        f1, f2, f3 = self.cursor.fetchone()
        self.assertEqual(f1, [1, 2, 3, 4])
        self.assertEqual(f2, [[1, 2, 3], [4, 5, 6]])
        self.assertEqual(f3, [[[1, 2], [3, 4]], [[None, 6], [7, 8]]])

    def testInt8ArrayOut(self):
        self.cursor.execute(
            "SELECT '{1,2,3,4}'::INT8[] AS f1, "
            "'{{1,2,3},{4,5,6}}'::INT8[][] AS f2, "
            "'{{{1,2},{3,4}},{{NULL,6},{7,8}}}'::INT8[][][] AS f3")
        f1, f2, f3 = self.cursor.fetchone()
        self.assertEqual(f1, [1, 2, 3, 4])
        self.assertEqual(f2, [[1, 2, 3], [4, 5, 6]])
        self.assertEqual(f3, [[[1, 2], [3, 4]], [[None, 6], [7, 8]]])

    def testBoolArrayOut(self):
        self.cursor.execute(
            "SELECT '{TRUE,FALSE,FALSE,TRUE}'::BOOL[] AS f1, "
            "'{{TRUE,FALSE,TRUE},{FALSE,TRUE,FALSE}}'::BOOL[][] AS f2, "
            "'{{{TRUE,FALSE},{FALSE,TRUE}},{{NULL,TRUE},{FALSE,FALSE}}}'"
            "::BOOL[][][] AS f3")
        f1, f2, f3 = self.cursor.fetchone()
        self.assertEqual(f1, [True, False, False, True])
        self.assertEqual(f2, [[True, False, True], [False, True, False]])
        self.assertEqual(
            f3,
            [[[True, False], [False, True]], [[None, True], [False, False]]])

    def testFloat4ArrayOut(self):
        self.cursor.execute(
            "SELECT '{1,2,3,4}'::FLOAT4[] AS f1, "
            "'{{1,2,3},{4,5,6}}'::FLOAT4[][] AS f2, "
            "'{{{1,2},{3,4}},{{NULL,6},{7,8}}}'::FLOAT4[][][] AS f3")
        f1, f2, f3 = self.cursor.fetchone()
        self.assertEqual(f1, [1, 2, 3, 4])
        self.assertEqual(f2, [[1, 2, 3], [4, 5, 6]])
        self.assertEqual(f3, [[[1, 2], [3, 4]], [[None, 6], [7, 8]]])

    def testFloat8ArrayOut(self):
        self.cursor.execute(
            "SELECT '{1,2,3,4}'::FLOAT8[] AS f1, "
            "'{{1,2,3},{4,5,6}}'::FLOAT8[][] AS f2, "
            "'{{{1,2},{3,4}},{{NULL,6},{7,8}}}'::FLOAT8[][][] AS f3")
        f1, f2, f3 = self.cursor.fetchone()
        self.assertEqual(f1, [1, 2, 3, 4])
        self.assertEqual(f2, [[1, 2, 3], [4, 5, 6]])
        self.assertEqual(f3, [[[1, 2], [3, 4]], [[None, 6], [7, 8]]])

    def testIntArrayRoundtrip(self):
        # send small int array, should be sent as INT2[]
        self.cursor.execute("SELECT %s as f1", ([1, 2, 3],))
        retval = self.cursor.fetchall()
        self.assertEqual(retval[0][0], [1, 2, 3])
        column_name, column_typeoid = self.cursor.description[0][0:2]
        self.assertEqual(column_typeoid, 1005, "type should be INT2[]")

        # test multi-dimensional array, should be sent as INT2[]
        self.cursor.execute("SELECT %s as f1", ([[1, 2], [3, 4]],))
        retval = self.cursor.fetchall()
        self.assertEqual(retval[0][0], [[1, 2], [3, 4]])

        column_name, column_typeoid = self.cursor.description[0][0:2]
        self.assertEqual(column_typeoid, 1005, "type should be INT2[]")

        # a larger value should kick it up to INT4[]...
        self.cursor.execute("SELECT %s as f1 -- integer[]", ([70000, 2, 3],))
        retval = self.cursor.fetchall()
        self.assertEqual(retval[0][0], [70000, 2, 3])
        column_name, column_typeoid = self.cursor.description[0][0:2]
        self.assertEqual(column_typeoid, 1007, "type should be INT4[]")

        # a much larger value should kick it up to INT8[]...
        self.cursor.execute(
            "SELECT %s as f1 -- bigint[]", ([7000000000, 2, 3],))
        retval = self.cursor.fetchall()
        self.assertEqual(
            retval[0][0], [7000000000, 2, 3],
            "retrieved value match failed")
        column_name, column_typeoid = self.cursor.description[0][0:2]
        self.assertEqual(column_typeoid, 1016, "type should be INT8[]")

    def testIntArrayWithNullRoundtrip(self):
        self.cursor.execute("SELECT %s as f1", ([1, None, 3],))
        retval = self.cursor.fetchall()
        self.assertEqual(retval[0][0], [1, None, 3])

    def testFloatArrayRoundtrip(self):
        self.cursor.execute("SELECT %s as f1", ([1.1, 2.2, 3.3],))
        retval = self.cursor.fetchall()
        self.assertEqual(retval[0][0], [1.1, 2.2, 3.3])

    def testBoolArrayRoundtrip(self):
        self.cursor.execute("SELECT %s as f1", ([True, False, None],))
        retval = self.cursor.fetchall()
        self.assertEqual(retval[0][0], [True, False, None])

    def testStringArrayOut(self):
        self.cursor.execute("SELECT '{a,b,c}'::TEXT[] AS f1")
        self.assertEqual(self.cursor.fetchone()[0], ["a", "b", "c"])
        self.cursor.execute("SELECT '{a,b,c}'::CHAR[] AS f1")
        self.assertEqual(self.cursor.fetchone()[0], ["a", "b", "c"])
        self.cursor.execute("SELECT '{a,b,c}'::VARCHAR[] AS f1")
        self.assertEqual(self.cursor.fetchone()[0], ["a", "b", "c"])
        self.cursor.execute("SELECT '{a,b,c}'::CSTRING[] AS f1")
        self.assertEqual(self.cursor.fetchone()[0], ["a", "b", "c"])
        self.cursor.execute("SELECT '{a,b,c}'::NAME[] AS f1")
        self.assertEqual(self.cursor.fetchone()[0], ["a", "b", "c"])
        self.cursor.execute("SELECT '{}'::text[];")
        self.assertEqual(self.cursor.fetchone()[0], [])

    def testNumericArrayOut(self):
        self.cursor.execute("SELECT '{1.1,2.2,3.3}'::numeric[] AS f1")
        self.assertEqual(
            self.cursor.fetchone()[0], [
                decimal.Decimal("1.1"), decimal.Decimal("2.2"),
                decimal.Decimal("3.3")])

    def testNumericArrayRoundtrip(self):
        v = [decimal.Decimal("1.1"), None, decimal.Decimal("3.3")]
        self.cursor.execute("SELECT %s as f1", (v,))
        retval = self.cursor.fetchall()
        self.assertEqual(retval[0][0], v)

    def testStringArrayRoundtrip(self):
        self.cursor.execute("SELECT %s as f1", (["Hello!", "World!", None],))
        retval = self.cursor.fetchall()
        self.assertEqual(retval[0][0], ["Hello!", "World!", None])

        self.cursor.execute("SELECT %s as f1", (["Hello!", "World!", None],))
        retval = self.cursor.fetchall()
        self.assertEqual(retval[0][0], ["Hello!", "World!", None])

    def testArrayHasValue(self):
        self.assertRaises(
            pg8000.ArrayContentEmptyError,
            self.db.array_inspect, [[None], [None], [None]])
        self.db.rollback()

    def testArrayContentNotSupported(self):
        class Kajigger(object):
            pass
        self.assertRaises(
            pg8000.ArrayContentNotSupportedError,
            self.db.array_inspect, [[Kajigger()], [None], [None]])
        self.db.rollback()

    def testArrayDimensions(self):
        for arr in (
                [1, [2]], [[1], [2], [3, 4]],
                [[[1]], [[2]], [[3, 4]]],
                [[[1]], [[2]], [[3, 4]]],
                [[[[1]]], [[[2]]], [[[3, 4]]]],
                [[1, 2, 3], [4, [5], 6]]):

            arr_send = self.db.array_inspect(arr)[2]
            self.assertRaises(
                pg8000.ArrayDimensionsNotConsistentError, arr_send, arr)
            self.db.rollback()

    def testArrayHomogenous(self):
        arr = [[[1]], [[2]], [[3.1]]]
        arr_send = self.db.array_inspect(arr)[2]
        self.assertRaises(
            pg8000.ArrayContentNotHomogenousError, arr_send, arr)
        self.db.rollback()

    def testArrayInspect(self):
        self.db.array_inspect([1, 2, 3])
        self.db.array_inspect([[1], [2], [3]])
        self.db.array_inspect([[[1]], [[2]], [[3]]])

    def testMacaddr(self):
        self.cursor.execute("SELECT macaddr '08002b:010203'")
        retval = self.cursor.fetchall()
        self.assertEqual(retval[0][0], "08:00:2b:01:02:03")

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_typeobjects
import unittest
from pg8000 import Interval


# Type conversion tests
class Tests(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def testIntervalConstructor(self):
        i = Interval(days=1)
        self.assertEqual(i.months, 0)
        self.assertEqual(i.days, 1)
        self.assertEqual(i.microseconds, 0)

    def intervalRangeTest(self, parameter, in_range, out_of_range):
        for v in out_of_range:
            try:
                Interval(**{parameter: v})
                self.fail("expected OverflowError")
            except OverflowError:
                pass
        for v in in_range:
            Interval(**{parameter: v})

    def testIntervalDaysRange(self):
        out_of_range_days = (-2147483648, +2147483648,)
        in_range_days = (-2147483647, +2147483647,)
        self.intervalRangeTest("days", in_range_days, out_of_range_days)

    def testIntervalMonthsRange(self):
        out_of_range_months = (-2147483648, +2147483648,)
        in_range_months = (-2147483647, +2147483647,)
        self.intervalRangeTest("months", in_range_months, out_of_range_months)

    def testIntervalMicrosecondsRange(self):
        out_of_range_microseconds = (
            -9223372036854775808, +9223372036854775808,)
        in_range_microseconds = (
            -9223372036854775807, +9223372036854775807,)
        self.intervalRangeTest(
            "microseconds", in_range_microseconds, out_of_range_microseconds)

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = types
# vim: sw=4:expandtab:foldmethod=marker
#
# Copyright (c) 2007-2009, Mathieu Fenniak
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
# * Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.
# * Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
# * The name of the author may not be used to endorse or promote products
# derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

__author__ = "Mathieu Fenniak"

from pg8000 import Interval, Bytea, utc

__all__ = [Interval, Bytea, utc]

########NEW FILE########
__FILENAME__ = util


class MulticastDelegate(object):
    def __init__(self):
        self.delegates = []

    def __iadd__(self, delegate):
        self.add(delegate)
        return self

    def add(self, delegate):
        self.delegates.append(delegate)

    def __isub__(self, delegate):
        self.delegates.remove(delegate)
        return self

    def __call__(self, *args, **kwargs):
        for d in self.delegates:
            d(*args, **kwargs)

########NEW FILE########
__FILENAME__ = run_25
import nose

nose.run()

########NEW FILE########
__FILENAME__ = run_25_cache
import nose
import os
import sys

params = eval(os.environ['PG8000_TEST'])
params['use_cache'] = True
os.environ['PG8000_TEST'] = str(params)

nose.run()

########NEW FILE########
