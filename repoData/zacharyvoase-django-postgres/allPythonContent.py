__FILENAME__ = bitstrings
from contextlib import closing

from bitstring import Bits
from django.db import models
from django.db.backends.postgresql_psycopg2.base import DatabaseWrapper as PGDatabaseWrapper
from django.db.backends.signals import connection_created
from psycopg2 import extensions as ext


__all__ = ['Bits', 'BitStringField', 'BitStringExpression']


def adapt_bits(bits):
    """psycopg2 adapter function for ``bitstring.Bits``.

    Encode SQL parameters from ``bitstring.Bits`` instances to SQL strings.
    """
    if bits.length % 4 == 0:
        return ext.AsIs("X'%s'" % (bits.hex,))
    return ext.AsIs("B'%s'" % (bits.bin,))
ext.register_adapter(Bits, adapt_bits)


def cast_bits(value, cur):
    """psycopg2 caster for bit strings.

    Turns query results from the database into ``bitstring.Bits`` instances.
    """
    if value is None:
        return None
    return Bits(bin=value)


def register_bitstring_types(connection):
    """Register the BIT and VARBIT casters on the provided connection.

    This ensures that BIT and VARBIT instances returned from the database will
    be represented in Python as ``bitstring.Bits`` instances.
    """
    with closing(connection.cursor()) as cur:
        cur.execute("SELECT NULL::BIT")
        bit_oid = cur.description[0].type_code
        cur.execute("SELECT NULL::VARBIT")
        varbit_oid = cur.description[0].type_code
    bit_caster = ext.new_type((bit_oid, varbit_oid), 'BIT', cast_bits)
    ext.register_type(bit_caster, connection)


def register_types_on_connection_creation(connection, sender, *args, **kwargs):
    if not issubclass(sender, PGDatabaseWrapper):
        return
    register_bitstring_types(connection.connection)
connection_created.connect(register_types_on_connection_creation)


class BitStringField(models.Field):

    """A Postgres bit string."""

    def __init__(self, *args, **kwargs):
        self.max_length = kwargs.setdefault('max_length', 1)
        self.varying = kwargs.pop('varying', False)

        if 'default' in kwargs:
            default = kwargs.pop('default')
        elif kwargs.get('null', False):
            default = None
        elif self.max_length is not None and not self.varying:
            default = '0' * self.max_length
        else:
            default = '0'
        kwargs['default'] = self.to_python(default)

        super(BitStringField, self).__init__(*args, **kwargs)

    def db_type(self, connection):
        if self.varying:
            if self.max_length is not None:
                return 'VARBIT(%d)' % (self.max_length,)
            return 'VARBIT'
        elif self.max_length is not None:
            return 'BIT(%d)' % (self.max_length,)
        return 'BIT'

    def to_python(self, value):
        if value is None or isinstance(value, Bits):
            return value
        elif isinstance(value, basestring):
            if value.startswith('0x'):
                return Bits(hex=value)
            return Bits(bin=value)
        raise TypeError("Cannot coerce into bit string: %r" % (value,))

    def get_prep_value(self, value):
        return self.to_python(value)

    def get_prep_lookup(self, lookup_type, value):
        if lookup_type == 'exact':
            return self.get_prep_value(value)
        elif lookup_type == 'in':
            return map(self.get_prep_value, value)
        raise TypeError("Lookup type %r not supported on bit strings" % lookup_type)

    def get_default(self):
        default = super(BitStringField, self).get_default()
        return self.to_python(default)


class BitStringExpression(models.expressions.F):

    ADD = '||'  # The Postgres concatenation operator.
    XOR = '#'
    LSHIFT = '<<'
    RSHIFT = '>>'
    NOT = '~'

    def __init__(self, field, *args, **kwargs):
        super(BitStringExpression, self).__init__(field, *args, **kwargs)
        self.lookup = field

    def __and__(self, other):
        return self.bitand(other)

    def __or__(self, other):
        return self.bitor(other)

    def __xor__(self, other):
        return self._combine(other, self.XOR, False)

    def __rxor__(self, other):
        return self._combine(other, self.XOR, True)

    def __lshift__(self, other):
        return self._combine(other, self.LSHIFT, False)

    def __rshift__(self, other):
        return self._combine(other, self.RSHIFT, False)

    def _unary(self, operator):
        # This is a total hack, but you need to combine a raw empty space with
        # the current node, in reverse order, with the connector being the
        # unary operator you want to apply.
        return self._combine(ext.AsIs(''), operator, True)

    def __invert__(self):
        return self._unary(self.NOT)

########NEW FILE########
__FILENAME__ = citext
from django.db.models import fields


class CaseInsensitiveTextField(fields.TextField):

    def db_type(self, connection):
        return "citext"

########NEW FILE########
__FILENAME__ = sync_pgviews
from optparse import make_option
import logging

from django.core.management.base import NoArgsCommand
from django.db import models

from django_postgres.view import create_views


log = logging.getLogger('django_postgres.sync_pgviews')


class Command(NoArgsCommand):
    help = """Create/update Postgres views for all installed apps."""
    option_list = NoArgsCommand.option_list + (
        make_option('--no-update',
                    action='store_false',
                    dest='update',
                    default=True,
                    help="""Don't update existing views, only create new ones."""),
        make_option('--force',
                    action='store_true',
                    dest='force',
                    default=False,
                    help="""Force replacement of pre-existing views where
                    breaking changes have been made to the schema."""),
    )

    def handle_noargs(self, force, update, **options):
        for module in models.get_apps():
            log.info("Creating views for %s", module.__name__)
            try:
                for status, view_cls, python_name in create_views(module, update=update, force=force):
                    if status == 'CREATED':
                        msg = "created"
                    elif status == 'UPDATED':
                        msg = "updated"
                    elif status == 'EXISTS':
                        msg = "already exists, skipping"
                    elif status == 'FORCED':
                        msg = "forced overwrite of existing schema"
                    elif status == 'FORCE_REQUIRED':
                        msg = "exists with incompatible schema, --force required to update"
                    log.info("%(python_name)s (%(view_name)s): %(msg)s" % {
                        'python_name': python_name,
                        'view_name': view_cls._meta.db_table,
                        'msg': msg})
            except Exception, exc:
                if not hasattr(exc, 'view_cls'):
                    raise
                log.exception("Error creating view %s (%r)",
                              exc.python_name,
                              exc.view_cls._meta.db_table)

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
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import operator
import sys
import types

__author__ = "Benjamin Peterson <benjamin@python.org>"
__version__ = "1.3.0"


# True if we are running on Python 3.
PY3 = sys.version_info[0] == 3

if PY3:
    string_types = str,
    integer_types = int,
    class_types = type,
    text_type = str
    binary_type = bytes

    MAXSIZE = sys.maxsize
else:
    string_types = basestring,
    integer_types = (int, long)
    class_types = (type, types.ClassType)
    text_type = unicode
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
    MovedAttribute("input", "__builtin__", "builtins", "raw_input", "input"),
    MovedAttribute("map", "itertools", "builtins", "imap", "map"),
    MovedAttribute("range", "__builtin__", "builtins", "xrange", "range"),
    MovedAttribute("reload_module", "__builtin__", "imp", "reload"),
    MovedAttribute("reduce", "__builtin__", "functools"),
    MovedAttribute("StringIO", "StringIO", "io"),
    MovedAttribute("xrange", "__builtin__", "builtins", "xrange", "range"),
    MovedAttribute("zip", "itertools", "builtins", "izip", "zip"),

    MovedModule("builtins", "__builtin__"),
    MovedModule("configparser", "ConfigParser"),
    MovedModule("copyreg", "copy_reg"),
    MovedModule("http_cookiejar", "cookielib", "http.cookiejar"),
    MovedModule("http_cookies", "Cookie", "http.cookies"),
    MovedModule("html_entities", "htmlentitydefs", "html.entities"),
    MovedModule("html_parser", "HTMLParser", "html.parser"),
    MovedModule("http_client", "httplib", "http.client"),
    MovedModule("email_mime_multipart", "email.MIMEMultipart", "email.mime.multipart"),
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
    MovedModule("tkinter_scrolledtext", "ScrolledText", "tkinter.scrolledtext"),
    MovedModule("tkinter_simpledialog", "SimpleDialog", "tkinter.simpledialog"),
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
    MovedModule("tkinter_tksimpledialog", "tkSimpleDialog",
                "tkinter.simpledialog"),
    MovedModule("urllib_robotparser", "robotparser", "urllib.robotparser"),
    MovedModule("winreg", "_winreg"),
]
for attr in _moved_attributes:
    setattr(_MovedItems, attr.name, attr)
del attr

moves = sys.modules[__name__ + ".moves"] = _MovedItems("moves")


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
    if sys.version_info[1] <= 1:
        def int2byte(i):
            return bytes((i,))
    else:
        # This is about 2x faster than the implementation above on 3.2+
        int2byte = operator.methodcaller("to_bytes", 1, "big")
    indexbytes = operator.getitem
    iterbytes = iter
    import io
    StringIO = io.StringIO
    BytesIO = io.BytesIO
else:
    def b(s):
        return s
    def u(s):
        return unicode(s, "unicode_escape")
    int2byte = chr
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
            if not isinstance(data, basestring):
                data = str(data)
            fp.write(data)
        want_unicode = False
        sep = kwargs.pop("sep", None)
        if sep is not None:
            if isinstance(sep, unicode):
                want_unicode = True
            elif not isinstance(sep, str):
                raise TypeError("sep must be None or a string")
        end = kwargs.pop("end", None)
        if end is not None:
            if isinstance(end, unicode):
                want_unicode = True
            elif not isinstance(end, str):
                raise TypeError("end must be None or a string")
        if kwargs:
            raise TypeError("invalid keyword arguments to print()")
        if not want_unicode:
            for arg in args:
                if isinstance(arg, unicode):
                    want_unicode = True
                    break
        if want_unicode:
            newline = unicode("\n")
            space = unicode(" ")
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

########NEW FILE########
__FILENAME__ = view
"""Helpers to access Postgres views from the Django ORM."""

import collections
import copy
import logging
import re

from django.db import connection, transaction
from django.db import models
import psycopg2

from . import six


FIELD_SPEC_REGEX = (r'^([A-Za-z_][A-Za-z0-9_]*)\.'
                    r'([A-Za-z_][A-Za-z0-9_]*)\.'
                    r'(\*|(?:[A-Za-z_][A-Za-z0-9_]*))$')
FIELD_SPEC_RE = re.compile(FIELD_SPEC_REGEX)

log = logging.getLogger('django_postgres.view')


def hasfield(model_cls, field_name):
    """Like `hasattr()`, but for model fields.

        >>> from django.contrib.auth.models import User
        >>> hasfield(User, 'password')
        True
        >>> hasfield(User, 'foobarbaz')
        False
    """
    try:
        model_cls._meta.get_field_by_name(field_name)
        return True
    except models.FieldDoesNotExist:
        return False


# Projections of models fields onto views which have been deferred due to
# model import and loading dependencies.
# Format: (app_label, model_name): {view_cls: [field_name, ...]}
_DEFERRED_PROJECTIONS = collections.defaultdict(
    lambda: collections.defaultdict(list))
def realize_deferred_projections(sender, *args, **kwargs):
    """Project any fields which were deferred pending model preparation."""
    app_label = sender._meta.app_label
    model_name = sender.__name__.lower()
    pending = _DEFERRED_PROJECTIONS.pop((app_label, model_name), {})
    for view_cls, field_names in six.iteritems(pending):
        field_instances = get_fields_by_name(sender, *field_names)
        for name, field in six.iteritems(field_instances):
            # Only assign the field if the view does not already have an
            # attribute or explicitly-defined field with that name.
            if hasattr(view_cls, name) or hasfield(view_cls, name):
                continue
            copy.copy(field).contribute_to_class(view_cls, name)
models.signals.class_prepared.connect(realize_deferred_projections)


def create_views(models_module, update=True, force=False):
    """Create the database views for a given models module."""
    for name, view_cls in six.iteritems(vars(models_module)):
        if not (isinstance(view_cls, type) and
                issubclass(view_cls, View) and
                hasattr(view_cls, 'sql')):
            continue

        try:
            created = create_view(connection, view_cls._meta.db_table,
                                  view_cls.sql, update=update, force=force)
        except Exception as exc:
            exc.view_cls = view_cls
            exc.python_name = models_module.__name__ + '.' + name
            raise
        else:
            yield created, view_cls, models_module.__name__ + '.' + name


def create_view(connection, view_name, view_query, update=True, force=False):
    """
    Create a named view on a connection.

    Returns True if a new view was created (or an existing one updated), or
    False if nothing was done.

    If ``update`` is True (default), attempt to update an existing view. If the
    existing view's schema is incompatible with the new definition, ``force``
    (default: False) controls whether or not to drop the old view and create
    the new one.
    """
    cursor_wrapper = connection.cursor()
    cursor = cursor_wrapper.cursor.cursor
    try:
        force_required = False
        # Determine if view already exists.
        cursor.execute('SELECT COUNT(*) FROM pg_catalog.pg_class WHERE relname = %s;',
                       [view_name])
        view_exists = cursor.fetchone()[0] > 0
        if view_exists and not update:
            return 'EXISTS'
        elif view_exists:
            # Detect schema conflict by copying the original view, attempting to
            # update this copy, and detecting errors.
            cursor.execute('CREATE TEMPORARY VIEW check_conflict AS SELECT * FROM {0};'.format(view_name))
            try:
                cursor.execute('CREATE OR REPLACE TEMPORARY VIEW check_conflict AS {0};'.format(view_query))
            except psycopg2.ProgrammingError:
                force_required = True
                cursor.connection.rollback()
            finally:
                cursor.execute('DROP VIEW IF EXISTS check_conflict;')

        if not force_required:
            cursor.execute('CREATE OR REPLACE VIEW {0} AS {1};'.format(view_name, view_query))
            ret = view_exists and 'UPDATED' or 'CREATED'
        elif force:
            cursor.execute('DROP VIEW {0};'.format(view_name))
            cursor.execute('CREATE VIEW {0} AS {1};'.format(view_name, view_query))
            ret = 'FORCED'
        else:
            ret = 'FORCE_REQUIRED'

        transaction.commit_unless_managed()
        return ret
    finally:
        cursor_wrapper.close()



def get_fields_by_name(model_cls, *field_names):
    """Return a dict of `models.Field` instances for named fields.

    Supports wildcard fetches using `'*'`.

        >>> get_fields_by_name(User, 'username', 'password')
        {'username': <django.db.models.fields.CharField: username>,
         'password': <django.db.models.fields.CharField: password>}

        >>> get_fields_by_name(User, '*')
        {'username': <django.db.models.fields.CharField: username>,
         ...,
         'date_joined': <django.db.models.fields.DateTimeField: date_joined>}
    """
    if '*' in field_names:
        return dict((field.name, field) for field in model_cls._meta.fields)
    return dict((field_name, model_cls._meta.get_field_by_name(field_name)[0])
                for field_name in field_names)


class View(models.Model):

    """Helper for exposing Postgres views as Django models."""

    class ViewMeta(models.base.ModelBase):

        def __new__(metacls, name, bases, attrs):
            projection = attrs.pop('projection', [])
            deferred_projections = []
            for field_name in projection:
                if isinstance(field_name, models.Field):
                    attrs[field_name.name] = copy.copy(field_name)
                elif isinstance(field_name, basestring):
                    match = FIELD_SPEC_RE.match(field_name)
                    if not match:
                        raise TypeError("Unrecognized field specifier: %r" %
                                        field_name)
                    deferred_projections.append(match.groups())
                else:
                    raise TypeError("Unrecognized field specifier: %r" %
                                    field_name)
            view_cls = models.base.ModelBase.__new__(metacls, name, bases,
                                                     attrs)
            for app_label, model_name, field_name in deferred_projections:
                model_spec = (app_label, model_name.lower())
                _DEFERRED_PROJECTIONS[model_spec][view_cls].append(field_name)
                # If the model has already been loaded, run
                # `realize_deferred_projections()` on it.
                model_cls = models.get_model(app_label, model_name,
                                             seed_cache=False)
                if model_cls is not None:
                    realize_deferred_projections(model_cls)
            return view_cls

    __metaclass__ = ViewMeta

    class Meta:
        abstract = True
        managed = False

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# django-postgres documentation build configuration file, created by
# sphinx-quickstart on Sun Aug 19 05:34:54 2012.
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
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.viewcode']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'django-postgres'
copyright = u'Public Domain'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.0.1'
# The full version, including alpha/beta/rc tags.
release = '0.0.1'

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
html_show_copyright = False

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'django_postgresdoc'


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
  ('index', 'django-postgres.tex', u'django\\-postgres Documentation',
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
    ('index', 'django-postgres', u'django-postgres Documentation',
     [u'Author'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'django-postgres', u'django-postgres Documentation',
   u'Author', 'django-postgres', 'One line description of project.',
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
epub_title = u'django-postgres'
epub_author = u'Author'
epub_publisher = u'Author'
epub_copyright = u'2012, Author'

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

########NEW FILE########
__FILENAME__ = models
from django.db import models

# Create your models here.

########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase


class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.assertEqual(1 + 1, 2)

########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
__FILENAME__ = models
from django.db import models
import django_postgres


class BloomFilter(models.Model):
    name = models.CharField(max_length=100)
    bitmap = django_postgres.BitStringField(max_length=8)


class VarBitmap(models.Model):
    name = models.CharField(max_length=100)
    bitmap = django_postgres.BitStringField(max_length=8, varying=True)


class NullBitmap(models.Model):
    name = models.CharField(max_length=100)
    bitmap = django_postgres.BitStringField(max_length=8, null=True)

########NEW FILE########
__FILENAME__ = tests
from django.test import TestCase
from django_postgres import Bits, B

import models


class SimpleTest(TestCase):

    def test_can_create_bitstrings(self):
        bloom = models.BloomFilter.objects.create(name='foo')
        # Default bit string is all zeros.
        assert bloom.bitmap.bin == ('0' * 8)

    def test_null_bitmap_defaults_to_None(self):
        bloom = models.NullBitmap.objects.create(name='foo')
        assert bloom.bitmap is None

    def test_can_change_bitstrings(self):
        bloom = models.BloomFilter.objects.create(name='foo')
        bloom.bitmap = Bits(bin='01011010')
        bloom.save()

        refetch = models.BloomFilter.objects.get(id=bloom.id)
        assert refetch.bitmap.bin == '01011010'

    def test_can_set_null_bitmap_to_None(self):
        bloom = models.NullBitmap.objects.create(name='foo',
                                                 bitmap=Bits(bin='01010101'))
        assert bloom.bitmap is not None
        bloom.bitmap = None
        bloom.save()
        bloom = models.NullBitmap.objects.get(id=bloom.id)
        assert bloom.bitmap is None

    def test_can_search_for_equal_bitstrings(self):
        models.BloomFilter.objects.create(name='foo', bitmap='01011010')

        results = models.BloomFilter.objects.filter(bitmap='01011010')
        assert results.count() == 1
        assert results[0].name == 'foo'


class VarBitTest(TestCase):

    def test_can_create_varying_length_bitstrings(self):
        bloom = models.VarBitmap.objects.create(name='foo')
        # Default varbit string is one zero.
        assert bloom.bitmap.bin == '0'

    def test_can_change_varbit_length(self):
        bloom = models.VarBitmap.objects.create(name='foo',
                                                bitmap=Bits(bin='01010'))
        assert len(bloom.bitmap.bin) == 5
        bloom.bitmap = Bits(bin='0101010')
        bloom.save()
        bloom = models.VarBitmap.objects.get(id=bloom.id)
        assert len(bloom.bitmap.bin) == 7


class BitStringExpressionUpdateTest(TestCase):

    def check_update(self, initial, expression, result):
        models.BloomFilter.objects.create(name='foo', bitmap=initial)
        models.BloomFilter.objects.create(name='bar')

        models.BloomFilter.objects \
                .filter(name='foo') \
                .update(bitmap=expression)

        assert models.BloomFilter.objects.get(name='foo').bitmap.bin == result
        assert models.BloomFilter.objects.get(name='bar').bitmap.bin == '00000000'

    def test_or(self):
        self.check_update('00000000',
                          B('bitmap') | Bits('0b10100101'),
                          '10100101')

    def test_and(self):
        self.check_update('10100101',
                          B('bitmap') & Bits('0b11000011'),
                          '10000001')

    def test_xor(self):
        self.check_update('10100101',
                          B('bitmap') ^ Bits('0b11000011'),
                          '01100110')

    def test_not(self):
        self.check_update('10100101',
                          ~B('bitmap'),
                          '01011010')

    def test_lshift(self):
        self.check_update('10100101',
                          B('bitmap') << 3,
                          '00101000')

    def test_rshift(self):
        self.check_update('10100101',
                          B('bitmap') >> 3,
                          '00010100')

########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
__FILENAME__ = settings
import commands

DEBUG = True
TEMPLATE_DEBUG = DEBUG

def git_name_and_email():
    name = commands.getoutput('git config user.name')
    email = commands.getoutput('git config user.email')
    return name, email

ADMINS = (git_name_and_email(),)
MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2', # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'django_postgres',                      # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '127.0.0.1',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
TIME_ZONE = 'Atlantic/Reykjavik'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = False

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = False

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
SECRET_KEY = 'g34i6_w+#in7d6_ficl42kbw!d*axa0qroei8yp#n__he22&amp;+g'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
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
    'django_nose',
    'django_postgres',
    'viewtest',
    'arraytest',
    'bitstringtest',
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
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
        'django_postgres': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True,
        }
    }
}

TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'

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
__FILENAME__ = models
import django.contrib.auth.models as auth_models

import django_postgres


class Superusers(django_postgres.View):
    projection = ['auth.User.*']
    sql = """SELECT * FROM auth_user WHERE is_superuser = TRUE;"""


class SimpleUser(django_postgres.View):
    projection = ['auth.User.username', 'auth.User.password']
    # The row_number() window function is needed so that Django sees some kind
    # of 'id' field. We could also grab the one from `auth.User`, but this
    # seemed like more fun :)
    sql = """
    SELECT
        username,
        password,
        row_number() OVER () AS id
    FROM auth_user;"""


class Staffness(django_postgres.View):
    projection = ['auth.User.username', 'auth.User.is_staff']
    sql = str(auth_models.User.objects.only('username', 'is_staff').query)

########NEW FILE########
__FILENAME__ = tests
from contextlib import closing

from django.contrib import auth
from django.core.management import call_command
from django.db import connection
from django.test import TestCase

import models


class ViewTestCase(TestCase):

    def setUp(self):
        call_command('sync_pgviews', *[], **{})

    def test_views_have_been_created(self):
        with closing(connection.cursor()) as cur:
            cur.execute('''SELECT COUNT(*) FROM pg_views
                        WHERE viewname LIKE 'viewtest_%';''')

            count, = cur.fetchone()
            self.assertEqual(count, 3)

    def test_wildcard_projection_gets_all_fields_from_projected_model(self):
        foo_user = auth.models.User.objects.create(
            username='foo', is_superuser=True)
        foo_user.set_password('blah')
        foo_user.save()

        foo_superuser = models.Superusers.objects.get(username='foo')

        self.assertEqual(foo_user.id, foo_superuser.id)
        self.assertEqual(foo_user.password, foo_superuser.password)

    def test_limited_projection_only_gets_selected_fields_from_projected_model(self):
        foo_user = auth.models.User.objects.create(
            username='foo', is_superuser=True)
        foo_user.set_password('blah')
        foo_user.save()

        foo_simple = models.SimpleUser.objects.get(username='foo')
        self.assertEqual(foo_simple.username, foo_user.username)
        self.assertEqual(foo_simple.password, foo_user.password)
        self.assertFalse(hasattr(foo_simple, 'date_joined'))

    def test_queryset_based_view_works_similarly_to_raw_sql(self):
        auth.models.User.objects.create(
            username='foo', is_staff=True)

        self.assertTrue(
            models.Staffness.objects.filter(username='foo').exists())

########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
