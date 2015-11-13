__FILENAME__ = base
# -*- coding: utf-8; fill-column: 76 -*-
"""Signals and events.

A small implementation of signals, inspired by a snippet of Django signal
API client code seen in a blog post.  Signals are first-class objects and
each manages its own receivers and message emission.

The :func:`signal` function provides singleton behavior for named signals.

"""
from warnings import warn
from weakref import WeakValueDictionary

from blinker._utilities import (
    WeakTypes,
    contextmanager,
    defaultdict,
    hashable_identity,
    lazy_property,
    reference,
    symbol,
    )


ANY = symbol('ANY')
ANY.__doc__ = 'Token for "any sender".'
ANY_ID = 0


class Signal(object):
    """A notification emitter."""

    #: An :obj:`ANY` convenience synonym, allows ``Signal.ANY``
    #: without an additional import.
    ANY = ANY

    @lazy_property
    def receiver_connected(self):
        """Emitted after each :meth:`connect`.

        The signal sender is the signal instance, and the :meth:`connect`
        arguments are passed through: *receiver*, *sender*, and *weak*.

        .. versionadded:: 1.2

        """
        return Signal(doc="Emitted after a receiver connects.")

    @lazy_property
    def receiver_disconnected(self):
        """Emitted after :meth:`disconnect`.

        The sender is the signal instance, and the :meth:`disconnect` arguments
        are passed through: *receiver* and *sender*.

        Note, this signal is emitted **only** when :meth:`disconnect` is
        called explicitly.

        The disconnect signal can not be emitted by an automatic disconnect
        (due to a weakly referenced receiver or sender going out of scope),
        as the receiver and/or sender instances are no longer available for
        use at the time this signal would be emitted.

        An alternative approach is available by subscribing to
        :attr:`receiver_connected` and setting up a custom weakref cleanup
        callback on weak receivers and senders.

        .. versionadded:: 1.2

        """
        return Signal(doc="Emitted after a receiver disconnects.")

    def __init__(self, doc=None):
        """
        :param doc: optional.  If provided, will be assigned to the signal's
          __doc__ attribute.

        """
        if doc:
            self.__doc__ = doc
        #: A mapping of connected receivers.
        #:
        #: The values of this mapping are not meaningful outside of the
        #: internal :class:`Signal` implementation, however the boolean value
        #: of the mapping is useful as an extremely efficient check to see if
        #: any receivers are connected to the signal.
        self.receivers = {}
        self._by_receiver = defaultdict(set)
        self._by_sender = defaultdict(set)
        self._weak_senders = {}

    def connect(self, receiver, sender=ANY, weak=True):
        """Connect *receiver* to signal events sent by *sender*.

        :param receiver: A callable.  Will be invoked by :meth:`send` with
          `sender=` as a single positional argument and any \*\*kwargs that
          were provided to a call to :meth:`send`.

        :param sender: Any object or :obj:`ANY`, defaults to ``ANY``.
          Restricts notifications delivered to *receiver* to only those
          :meth:`send` emissions sent by *sender*.  If ``ANY``, the receiver
          will always be notified.  A *receiver* may be connected to
          multiple *sender* values on the same Signal through multiple calls
          to :meth:`connect`.

        :param weak: If true, the Signal will hold a weakref to *receiver*
          and automatically disconnect when *receiver* goes out of scope or
          is garbage collected.  Defaults to True.

        """
        receiver_id = hashable_identity(receiver)
        if weak:
            receiver_ref = reference(receiver, self._cleanup_receiver)
            receiver_ref.receiver_id = receiver_id
        else:
            receiver_ref = receiver
        if sender is ANY:
            sender_id = ANY_ID
        else:
            sender_id = hashable_identity(sender)

        self.receivers.setdefault(receiver_id, receiver_ref)
        self._by_sender[sender_id].add(receiver_id)
        self._by_receiver[receiver_id].add(sender_id)
        del receiver_ref

        if sender is not ANY and sender_id not in self._weak_senders:
            # wire together a cleanup for weakref-able senders
            try:
                sender_ref = reference(sender, self._cleanup_sender)
                sender_ref.sender_id = sender_id
            except TypeError:
                pass
            else:
                self._weak_senders.setdefault(sender_id, sender_ref)
                del sender_ref

        # broadcast this connection.  if receivers raise, disconnect.
        if ('receiver_connected' in self.__dict__ and
            self.receiver_connected.receivers):
            try:
                self.receiver_connected.send(self,
                                             receiver=receiver,
                                             sender=sender,
                                             weak=weak)
            except:
                self.disconnect(receiver, sender)
                raise
        if receiver_connected.receivers and self is not receiver_connected:
            try:
                receiver_connected.send(self,
                                        receiver_arg=receiver,
                                        sender_arg=sender,
                                        weak_arg=weak)
            except:
                self.disconnect(receiver, sender)
                raise
        return receiver

    def connect_via(self, sender, weak=False):
        """Connect the decorated function as a receiver for *sender*.

        :param sender: Any object or :obj:`ANY`.  The decorated function
          will only receive :meth:`send` emissions sent by *sender*.  If
          ``ANY``, the receiver will always be notified.  A function may be
          decorated multiple times with differing *sender* values.

        :param weak: If true, the Signal will hold a weakref to the
          decorated function and automatically disconnect when *receiver*
          goes out of scope or is garbage collected.  Unlike
          :meth:`connect`, this defaults to False.

        The decorated function will be invoked by :meth:`send` with
          `sender=` as a single positional argument and any \*\*kwargs that
          were provided to the call to :meth:`send`.


        .. versionadded:: 1.1

        """
        def decorator(fn):
            self.connect(fn, sender, weak)
            return fn
        return decorator

    @contextmanager
    def connected_to(self, receiver, sender=ANY):
        """Execute a block with the signal temporarily connected to *receiver*.

        :param receiver: a receiver callable
        :param sender: optional, a sender to filter on

        This is a context manager for use in the ``with`` statement.  It can
        be useful in unit tests.  *receiver* is connected to the signal for
        the duration of the ``with`` block, and will be disconnected
        automatically when exiting the block:

        .. testsetup::

          from __future__ import with_statement
          from blinker import Signal
          on_ready = Signal()
          receiver = lambda sender: None

        .. testcode::

          with on_ready.connected_to(receiver):
             # do stuff
             on_ready.send(123)

        .. versionadded:: 1.1

        """
        self.connect(receiver, sender=sender, weak=False)
        try:
            yield None
        except:
            self.disconnect(receiver)
            raise
        else:
            self.disconnect(receiver)

    def temporarily_connected_to(self, receiver, sender=ANY):
        """An alias for :meth:`connected_to`.

        :param receiver: a receiver callable
        :param sender: optional, a sender to filter on

        .. versionadded:: 0.9

        .. versionchanged:: 1.1
          Renamed to :meth:`connected_to`.  ``temporarily_connected_to``
          was deprecated in 1.2 and removed in a subsequent version.

        """
        warn("temporarily_connected_to is deprecated; "
             "use connected_to instead.",
             DeprecationWarning)
        return self.connected_to(receiver, sender)

    def send(self, *sender, **kwargs):
        """Emit this signal on behalf of *sender*, passing on \*\*kwargs.

        Returns a list of 2-tuples, pairing receivers with their return
        value. The ordering of receiver notification is undefined.

        :param \*sender: Any object or ``None``.  If omitted, synonymous
          with ``None``.  Only accepts one positional argument.

        :param \*\*kwargs: Data to be sent to receivers.

        """
        # Using '*sender' rather than 'sender=None' allows 'sender' to be
        # used as a keyword argument- i.e. it's an invisible name in the
        # function signature.
        if len(sender) == 0:
            sender = None
        elif len(sender) > 1:
            raise TypeError('send() accepts only one positional argument, '
                            '%s given' % len(sender))
        else:
            sender = sender[0]
        if not self.receivers:
            return []
        else:
            return [(receiver, receiver(sender, **kwargs))
                    for receiver in self.receivers_for(sender)]

    def has_receivers_for(self, sender):
        """True if there is probably a receiver for *sender*.

        Performs an optimistic check only.  Does not guarantee that all
        weakly referenced receivers are still alive.  See
        :meth:`receivers_for` for a stronger search.

        """
        if not self.receivers:
            return False
        if self._by_sender[ANY_ID]:
            return True
        if sender is ANY:
            return False
        return hashable_identity(sender) in self._by_sender

    def receivers_for(self, sender):
        """Iterate all live receivers listening for *sender*."""
        # TODO: test receivers_for(ANY)
        if self.receivers:
            sender_id = hashable_identity(sender)
            if sender_id in self._by_sender:
                ids = (self._by_sender[ANY_ID] |
                       self._by_sender[sender_id])
            else:
                ids = self._by_sender[ANY_ID].copy()
            for receiver_id in ids:
                receiver = self.receivers.get(receiver_id)
                if receiver is None:
                    continue
                if isinstance(receiver, WeakTypes):
                    strong = receiver()
                    if strong is None:
                        self._disconnect(receiver_id, ANY_ID)
                        continue
                    receiver = strong
                yield receiver

    def disconnect(self, receiver, sender=ANY):
        """Disconnect *receiver* from this signal's events.

        :param receiver: a previously :meth:`connected<connect>` callable

        :param sender: a specific sender to disconnect from, or :obj:`ANY`
          to disconnect from all senders.  Defaults to ``ANY``.

        """
        if sender is ANY:
            sender_id = ANY_ID
        else:
            sender_id = hashable_identity(sender)
        receiver_id = hashable_identity(receiver)
        self._disconnect(receiver_id, sender_id)

        if ('receiver_disconnected' in self.__dict__ and
            self.receiver_disconnected.receivers):
            self.receiver_disconnected.send(self,
                                            receiver=receiver,
                                            sender=sender)

    def _disconnect(self, receiver_id, sender_id):
        if sender_id == ANY_ID:
            if self._by_receiver.pop(receiver_id, False):
                for bucket in self._by_sender.values():
                    bucket.discard(receiver_id)
            self.receivers.pop(receiver_id, None)
        else:
            self._by_sender[sender_id].discard(receiver_id)

    def _cleanup_receiver(self, receiver_ref):
        """Disconnect a receiver from all senders."""
        self._disconnect(receiver_ref.receiver_id, ANY_ID)

    def _cleanup_sender(self, sender_ref):
        """Disconnect all receivers from a sender."""
        sender_id = sender_ref.sender_id
        assert sender_id != ANY_ID
        self._weak_senders.pop(sender_id, None)
        for receiver_id in self._by_sender.pop(sender_id, ()):
            self._by_receiver[receiver_id].discard(sender_id)

    def _clear_state(self):
        """Throw away all signal state.  Useful for unit tests."""
        self._weak_senders.clear()
        self.receivers.clear()
        self._by_sender.clear()
        self._by_receiver.clear()


receiver_connected = Signal("""\
Sent by a :class:`Signal` after a receiver connects.

:argument: the Signal that was connected to
:keyword receiver_arg: the connected receiver
:keyword sender_arg: the sender to connect to
:keyword weak_arg: true if the connection to receiver_arg is a weak reference

.. deprecated:: 1.2

As of 1.2, individual signals have their own private
:attr:`~Signal.receiver_connected` and
:attr:`~Signal.receiver_disconnected` signals with a slightly simplified
call signature.  This global signal is planned to be removed in 1.6.

""")


class NamedSignal(Signal):
    """A named generic notification emitter."""

    def __init__(self, name, doc=None):
        Signal.__init__(self, doc)

        #: The name of this signal.
        self.name = name

    def __repr__(self):
        base = Signal.__repr__(self)
        return "%s; %r>" % (base[:-1], self.name)


class Namespace(dict):
    """A mapping of signal names to signals."""

    def signal(self, name, doc=None):
        """Return the :class:`NamedSignal` *name*, creating it if required.

        Repeated calls to this function will return the same signal object.

        """
        try:
            return self[name]
        except KeyError:
            return self.setdefault(name, NamedSignal(name, doc))


class WeakNamespace(WeakValueDictionary):
    """A weak mapping of signal names to signals.

    Automatically cleans up unused Signals when the last reference goes out
    of scope.  This namespace implementation exists for a measure of legacy
    compatibility with Blinker <= 1.2, and may be dropped in the future.

    """

    def signal(self, name, doc=None):
        """Return the :class:`NamedSignal` *name*, creating it if required.

        Repeated calls to this function will return the same signal object.

        """
        try:
            return self[name]
        except KeyError:
            return self.setdefault(name, NamedSignal(name, doc))


signal = Namespace().signal

########NEW FILE########
__FILENAME__ = _saferef
# extracted from Louie, http://pylouie.org/
# updated for Python 3
#
# Copyright (c) 2006 Patrick K. O'Brien, Mike C. Fletcher,
#                    Matthew R. Scott
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#
#     * Redistributions in binary form must reproduce the above
#       copyright notice, this list of conditions and the following
#       disclaimer in the documentation and/or other materials provided
#       with the distribution.
#
#     * Neither the name of the <ORGANIZATION> nor the names of its
#       contributors may be used to endorse or promote products derived
#       from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
"""Refactored 'safe reference from dispatcher.py"""

import operator
import sys
import traceback
import weakref


try:
    callable
except NameError:
    def callable(object):
        return hasattr(object, '__call__')


if sys.version_info < (3,):
    get_self = operator.attrgetter('im_self')
    get_func = operator.attrgetter('im_func')
else:
    get_self = operator.attrgetter('__self__')
    get_func = operator.attrgetter('__func__')


def safe_ref(target, on_delete=None):
    """Return a *safe* weak reference to a callable target.

    - ``target``: The object to be weakly referenced, if it's a bound
      method reference, will create a BoundMethodWeakref, otherwise
      creates a simple weakref.

    - ``on_delete``: If provided, will have a hard reference stored to
      the callable to be called after the safe reference goes out of
      scope with the reference object, (either a weakref or a
      BoundMethodWeakref) as argument.
    """
    try:
        im_self = get_self(target)
    except AttributeError:
        if callable(on_delete):
            return weakref.ref(target, on_delete)
        else:
            return weakref.ref(target)
    else:
        if im_self is not None:
            # Turn a bound method into a BoundMethodWeakref instance.
            # Keep track of these instances for lookup by disconnect().
            assert hasattr(target, 'im_func') or hasattr(target, '__func__'), (
                "safe_ref target %r has im_self, but no im_func, "
                "don't know how to create reference" % target)
            reference = BoundMethodWeakref(target=target, on_delete=on_delete)
            return reference


class BoundMethodWeakref(object):
    """'Safe' and reusable weak references to instance methods.

    BoundMethodWeakref objects provide a mechanism for referencing a
    bound method without requiring that the method object itself
    (which is normally a transient object) is kept alive.  Instead,
    the BoundMethodWeakref object keeps weak references to both the
    object and the function which together define the instance method.

    Attributes:

    - ``key``: The identity key for the reference, calculated by the
      class's calculate_key method applied to the target instance method.

    - ``deletion_methods``: Sequence of callable objects taking single
      argument, a reference to this object which will be called when
      *either* the target object or target function is garbage
      collected (i.e. when this object becomes invalid).  These are
      specified as the on_delete parameters of safe_ref calls.

    - ``weak_self``: Weak reference to the target object.

    - ``weak_func``: Weak reference to the target function.

    Class Attributes:

    - ``_all_instances``: Class attribute pointing to all live
      BoundMethodWeakref objects indexed by the class's
      calculate_key(target) method applied to the target objects.
      This weak value dictionary is used to short-circuit creation so
      that multiple references to the same (object, function) pair
      produce the same BoundMethodWeakref instance.
    """

    _all_instances = weakref.WeakValueDictionary()

    def __new__(cls, target, on_delete=None, *arguments, **named):
        """Create new instance or return current instance.

        Basically this method of construction allows us to
        short-circuit creation of references to already- referenced
        instance methods.  The key corresponding to the target is
        calculated, and if there is already an existing reference,
        that is returned, with its deletion_methods attribute updated.
        Otherwise the new instance is created and registered in the
        table of already-referenced methods.
        """
        key = cls.calculate_key(target)
        current = cls._all_instances.get(key)
        if current is not None:
            current.deletion_methods.append(on_delete)
            return current
        else:
            base = super(BoundMethodWeakref, cls).__new__(cls)
            cls._all_instances[key] = base
            base.__init__(target, on_delete, *arguments, **named)
            return base

    def __init__(self, target, on_delete=None):
        """Return a weak-reference-like instance for a bound method.

        - ``target``: The instance-method target for the weak reference,
          must have im_self and im_func attributes and be
          reconstructable via the following, which is true of built-in
          instance methods::

            target.im_func.__get__( target.im_self )

        - ``on_delete``: Optional callback which will be called when
          this weak reference ceases to be valid (i.e. either the
          object or the function is garbage collected).  Should take a
          single argument, which will be passed a pointer to this
          object.
        """
        def remove(weak, self=self):
            """Set self.isDead to True when method or instance is destroyed."""
            methods = self.deletion_methods[:]
            del self.deletion_methods[:]
            try:
                del self.__class__._all_instances[self.key]
            except KeyError:
                pass
            for function in methods:
                try:
                    if callable(function):
                        function(self)
                except Exception:
                    try:
                        traceback.print_exc()
                    except AttributeError:
                        e = sys.exc_info()[1]
                        print ('Exception during saferef %s '
                               'cleanup function %s: %s' % (self, function, e))
        self.deletion_methods = [on_delete]
        self.key = self.calculate_key(target)
        im_self = get_self(target)
        im_func = get_func(target)
        self.weak_self = weakref.ref(im_self, remove)
        self.weak_func = weakref.ref(im_func, remove)
        self.self_name = str(im_self)
        self.func_name = str(im_func.__name__)

    def calculate_key(cls, target):
        """Calculate the reference key for this reference.

        Currently this is a two-tuple of the id()'s of the target
        object and the target function respectively.
        """
        return (id(get_self(target)), id(get_func(target)))
    calculate_key = classmethod(calculate_key)

    def __str__(self):
        """Give a friendly representation of the object."""
        return "%s(%s.%s)" % (
            self.__class__.__name__,
            self.self_name,
            self.func_name,
            )

    __repr__ = __str__

    def __nonzero__(self):
        """Whether we are still a valid reference."""
        return self() is not None

    def __cmp__(self, other):
        """Compare with another reference."""
        if not isinstance(other, self.__class__):
            return cmp(self.__class__, type(other))
        return cmp(self.key, other.key)

    def __call__(self):
        """Return a strong reference to the bound method.

        If the target cannot be retrieved, then will return None,
        otherwise returns a bound instance method for our object and
        function.

        Note: You may call this method any number of times, as it does
        not invalidate the reference.
        """
        target = self.weak_self()
        if target is not None:
            function = self.weak_func()
            if function is not None:
                return function.__get__(target)
        return None

########NEW FILE########
__FILENAME__ = _utilities
from weakref import ref

from blinker._saferef import BoundMethodWeakref


try:
    callable
except NameError:
    def callable(object):
        return hasattr(object, '__call__')


try:
    from collections import defaultdict
except:
    class defaultdict(dict):

        def __init__(self, default_factory=None, *a, **kw):
            if (default_factory is not None and
                not hasattr(default_factory, '__call__')):
                raise TypeError('first argument must be callable')
            dict.__init__(self, *a, **kw)
            self.default_factory = default_factory

        def __getitem__(self, key):
            try:
                return dict.__getitem__(self, key)
            except KeyError:
                return self.__missing__(key)

        def __missing__(self, key):
            if self.default_factory is None:
                raise KeyError(key)
            self[key] = value = self.default_factory()
            return value

        def __reduce__(self):
            if self.default_factory is None:
                args = tuple()
            else:
                args = self.default_factory,
            return type(self), args, None, None, self.items()

        def copy(self):
            return self.__copy__()

        def __copy__(self):
            return type(self)(self.default_factory, self)

        def __deepcopy__(self, memo):
            import copy
            return type(self)(self.default_factory,
                              copy.deepcopy(self.items()))

        def __repr__(self):
            return 'defaultdict(%s, %s)' % (self.default_factory,
                                            dict.__repr__(self))


try:
    from contextlib import contextmanager
except ImportError:
    def contextmanager(fn):
        def oops(*args, **kw):
            raise RuntimeError("Python 2.5 or above is required to use "
                               "context managers.")
        oops.__name__ = fn.__name__
        return oops

class _symbol(object):

    def __init__(self, name):
        """Construct a new named symbol."""
        self.__name__ = self.name = name

    def __reduce__(self):
        return symbol, (self.name,)

    def __repr__(self):
        return self.name
_symbol.__name__ = 'symbol'


class symbol(object):
    """A constant symbol.

    >>> symbol('foo') is symbol('foo')
    True
    >>> symbol('foo')
    foo

    A slight refinement of the MAGICCOOKIE=object() pattern.  The primary
    advantage of symbol() is its repr().  They are also singletons.

    Repeated calls of symbol('name') will all return the same instance.

    """
    symbols = {}

    def __new__(cls, name):
        try:
            return cls.symbols[name]
        except KeyError:
            return cls.symbols.setdefault(name, _symbol(name))


try:
    text = (str, unicode)
except NameError:
    text = str


def hashable_identity(obj):
    if hasattr(obj, '__func__'):
        return (id(obj.__func__), id(obj.__self__))
    elif hasattr(obj, 'im_func'):
        return (id(obj.im_func), id(obj.im_self))
    elif isinstance(obj, text):
        return obj
    else:
        return id(obj)


WeakTypes = (ref, BoundMethodWeakref)


class annotatable_weakref(ref):
    """A weakref.ref that supports custom instance attributes."""


def reference(object, callback=None, **annotations):
    """Return an annotated weak ref."""
    if callable(object):
        weak = callable_reference(object, callback)
    else:
        weak = annotatable_weakref(object, callback)
    for key, value in annotations.items():
        setattr(weak, key, value)
    return weak


def callable_reference(object, callback=None):
    """Return an annotated weak ref, supporting bound instance methods."""
    if hasattr(object, 'im_self') and object.im_self is not None:
        return BoundMethodWeakref(target=object, on_delete=callback)
    elif hasattr(object, '__self__') and object.__self__ is not None:
        return BoundMethodWeakref(target=object, on_delete=callback)
    return annotatable_weakref(object, callback)


class lazy_property(object):
    """A @property that is only evaluated once."""

    def __init__(self, deferred):
        self._deferred = deferred
        self.__doc__ = deferred.__doc__

    def __get__(self, obj, cls):
        if obj is None:
            return self
        value = self._deferred(obj)
        setattr(obj, self._deferred.__name__, value)
        return value

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Blinker documentation build configuration file, created by
# sphinx-quickstart on Mon Feb 15 10:54:13 2010.
#
# This file is execfile()d with the current directory set to its containing
# dir.

import os
from os import path
import sys

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.

sys.path.append(os.path.abspath('../../'))

# -- General configuration -----------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc',
              'sphinx.ext.doctest',
              'sphinx.ext.coverage']

html_theme_path = ['.']

try:
   import dbuilder
except ImportError:
   pass
else:
   extensions.append('dbuilder')
   html_theme_path.append(path.join(dbuilder.__path__[0], 'theme'))

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Blinker'
copyright = u'2010, Jason Kirtland'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = 'tip'
# The full version, including alpha/beta/rc tags.
release = 'tip'

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
exclude_trees = []

autoclass_content = "both"
autodoc_member_order = "groupwise"
import sphinx.ext.autodoc
sphinx.ext.autodoc.AttributeDocumenter.member_order = 25
sphinx.ext.autodoc.InstanceAttributeDocumenter.member_order = 26


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

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# If nonempty, this is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = ''

# Output file base name for HTML help builder.
htmlhelp_basename = 'Blinkerdoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'Blinker.tex', u'Blinker Documentation',
   u'Jason Kirtland', 'manual'),
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
__FILENAME__ = test_context
from __future__ import with_statement

from blinker import Signal


def test_temp_connection():
    sig = Signal()

    canary = []
    receiver = lambda sender: canary.append(sender)

    sig.send(1)
    with sig.connected_to(receiver):
        sig.send(2)
    sig.send(3)

    assert canary == [2]
    assert not sig.receivers


def test_temp_connection_for_sender():
    sig = Signal()

    canary = []
    receiver = lambda sender: canary.append(sender)

    with sig.connected_to(receiver, sender=2):
        sig.send(1)
        sig.send(2)

    assert canary == [2]
    assert not sig.receivers


def test_temp_connection_failure():
    sig = Signal()

    canary = []
    receiver = lambda sender: canary.append(sender)

    class Failure(Exception):
        pass

    try:
        sig.send(1)
        with sig.connected_to(receiver):
            sig.send(2)
            raise Failure
        sig.send(3)
    except Failure:
        pass
    else:
        raise AssertionError("Context manager did not propagate.")

    assert canary == [2]
    assert not sig.receivers

########NEW FILE########
__FILENAME__ = test_saferef
# extracted from Louie, http://pylouie.org/
# updated for Python 3
#
# Copyright (c) 2006 Patrick K. O'Brien, Mike C. Fletcher,
#                    Matthew R. Scott
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#
#     * Redistributions in binary form must reproduce the above
#       copyright notice, this list of conditions and the following
#       disclaimer in the documentation and/or other materials provided
#       with the distribution.
#
#     * Neither the name of the <ORGANIZATION> nor the names of its
#       contributors may be used to endorse or promote products derived
#       from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
import unittest

from blinker._saferef import safe_ref


class _Sample1(object):
    def x(self):
        pass


def _sample2(obj):
    pass


class _Sample3(object):
    def __call__(self, obj):
        pass


class TestSaferef(unittest.TestCase):

    # XXX: The original tests had a test for closure, and it had an
    # off-by-one problem, perhaps due to scope issues.  It has been
    # removed from this test suite.

    def setUp(self):
        ts = []
        ss = []
        for x in range(100):
            t = _Sample1()
            ts.append(t)
            s = safe_ref(t.x, self._closure)
            ss.append(s)
        ts.append(_sample2)
        ss.append(safe_ref(_sample2, self._closure))
        for x in range(30):
            t = _Sample3()
            ts.append(t)
            s = safe_ref(t, self._closure)
            ss.append(s)
        self.ts = ts
        self.ss = ss
        self.closure_count = 0

    def tearDown(self):
        if hasattr(self, 'ts'):
            del self.ts
        if hasattr(self, 'ss'):
            del self.ss

    def test_In(self):
        """Test the `in` operator for safe references (cmp)"""
        for t in self.ts[:50]:
            assert safe_ref(t.x) in self.ss

    def test_Valid(self):
        """Test that the references are valid (return instance methods)"""
        for s in self.ss:
            assert s()

    def test_ShortCircuit(self):
        """Test that creation short-circuits to reuse existing references"""
        sd = {}
        for s in self.ss:
            sd[s] = 1
        for t in self.ts:
            if hasattr(t, 'x'):
                assert safe_ref(t.x) in sd
            else:
                assert safe_ref(t) in sd

    def test_Representation(self):
        """Test that the reference object's representation works

        XXX Doesn't currently check the results, just that no error
            is raised
        """
        repr(self.ss[-1])

    def _closure(self, ref):
        """Dumb utility mechanism to increment deletion counter"""
        self.closure_count += 1

########NEW FILE########
__FILENAME__ = test_signals
import gc
import sys
import time

import blinker

from nose.tools import assert_raises


jython = sys.platform.startswith('java')
pypy = hasattr(sys, 'pypy_version_info')


def collect_acyclic_refs():
    # cpython releases these immediately without a collection
    if jython or pypy:
        gc.collect()
    if jython:
        time.sleep(0.1)


class Sentinel(list):
    """A signal receipt accumulator."""

    def make_receiver(self, key):
        """Return a generic signal receiver function logging as *key*

        When connected to a signal, appends (key, sender, kw) to the Sentinel.

        """
        def receiver(*sentby, **kw):
            self.append((key, sentby[0], kw))
        receiver.func_name = 'receiver_%s' % key
        return receiver


def test_meta_connect():
    sentinel = []
    def meta_received(sender, **kw):
        sentinel.append(dict(kw, sender=sender))

    assert not blinker.receiver_connected.receivers
    blinker.receiver_connected.connect(meta_received)
    assert not sentinel

    def receiver(sender, **kw):
        pass
    sig = blinker.Signal()
    sig.connect(receiver)

    assert sentinel == [dict(sender=sig,
                             receiver_arg=receiver,
                             sender_arg=blinker.ANY,
                             weak_arg=True)]

    blinker.receiver_connected._clear_state()


def _test_signal_signals(sender):
    sentinel = Sentinel()
    sig = blinker.Signal()

    connected = sentinel.make_receiver('receiver_connected')
    disconnected = sentinel.make_receiver('receiver_disconnected')
    receiver1 = sentinel.make_receiver('receiver1')
    receiver2 = sentinel.make_receiver('receiver2')

    assert not sig.receiver_connected.receivers
    assert not sig.receiver_disconnected.receivers
    sig.receiver_connected.connect(connected)
    sig.receiver_disconnected.connect(disconnected)

    assert sig.receiver_connected.receivers
    assert not sentinel

    for receiver, weak in [(receiver1, True), (receiver2, False)]:
        sig.connect(receiver, sender=sender, weak=weak)

        expected = ('receiver_connected',
                    sig,
                    dict(receiver=receiver, sender=sender, weak=weak))

        assert sentinel[-1] == expected

    # disconnect from explicit sender
    sig.disconnect(receiver1, sender=sender)

    expected = ('receiver_disconnected',
                sig,
                dict(receiver=receiver1, sender=sender))
    assert sentinel[-1] == expected

    # disconnect from ANY and all senders (implicit disconnect signature)
    sig.disconnect(receiver2)
    assert sentinel[-1] == ('receiver_disconnected',
                            sig,
                            dict(receiver=receiver2, sender=blinker.ANY))


def test_signal_signals_any_sender():
    _test_signal_signals(blinker.ANY)


def test_signal_signals_strong_sender():
    _test_signal_signals("squiznart")


def test_signal_weak_receiver_vanishes():
    # non-edge-case path for weak receivers is exercised in the ANY sender
    # test above.
    sentinel = Sentinel()
    sig = blinker.Signal()

    connected = sentinel.make_receiver('receiver_connected')
    disconnected = sentinel.make_receiver('receiver_disconnected')
    receiver1 = sentinel.make_receiver('receiver1')
    receiver2 = sentinel.make_receiver('receiver2')

    sig.receiver_connected.connect(connected)
    sig.receiver_disconnected.connect(disconnected)

    # explicit disconnect on a weak does emit the signal
    sig.connect(receiver1, weak=True)
    sig.disconnect(receiver1)

    assert len(sentinel) == 2
    assert sentinel[-1][2]['receiver'] is receiver1

    del sentinel[:]
    sig.connect(receiver2, weak=True)
    assert len(sentinel) == 1

    del sentinel[:]  # holds a ref to receiver2
    del receiver2
    collect_acyclic_refs()

    # no disconnect signal is fired
    assert len(sentinel) == 0

    # and everything really is disconnected
    sig.send('abc')
    assert len(sentinel) == 0


def test_signal_signals_weak_sender():
    sentinel = Sentinel()
    sig = blinker.Signal()

    connected = sentinel.make_receiver('receiver_connected')
    disconnected = sentinel.make_receiver('receiver_disconnected')
    receiver1 = sentinel.make_receiver('receiver1')
    receiver2 = sentinel.make_receiver('receiver2')

    class Sender(object):
        """A weakref-able object."""

    sig.receiver_connected.connect(connected)
    sig.receiver_disconnected.connect(disconnected)

    sender1 = Sender()
    sig.connect(receiver1, sender=sender1, weak=False)
    # regular disconnect of weak-able sender works fine
    sig.disconnect(receiver1, sender=sender1)

    assert len(sentinel) == 2

    del sentinel[:]
    sender2 = Sender()
    sig.connect(receiver2, sender=sender2, weak=False)

    # force sender2 to go out of scope
    del sender2
    collect_acyclic_refs()

    # no disconnect signal is fired
    assert len(sentinel) == 1

    # and everything really is disconnected
    sig.send('abc')
    assert len(sentinel) == 1


def test_meta_connect_failure():
    def meta_received(sender, **kw):
        raise TypeError('boom')

    assert not blinker.receiver_connected.receivers
    blinker.receiver_connected.connect(meta_received)

    def receiver(sender, **kw):
        pass
    sig = blinker.Signal()

    assert_raises(TypeError, sig.connect, receiver)
    assert not sig.receivers
    assert not sig._by_receiver
    assert sig._by_sender == {blinker.base.ANY_ID: set()}

    blinker.receiver_connected._clear_state()


def test_weak_namespace():
    ns = blinker.WeakNamespace()
    assert not ns
    s1 = ns.signal('abc')
    assert s1 is ns.signal('abc')
    assert s1 is not ns.signal('def')
    assert 'abc' in ns
    collect_acyclic_refs()

    # weak by default, already out of scope
    assert 'def' not in ns
    del s1
    collect_acyclic_refs()

    assert 'abc' not in ns


def test_namespace():
    ns = blinker.Namespace()
    assert not ns
    s1 = ns.signal('abc')
    assert s1 is ns.signal('abc')
    assert s1 is not ns.signal('def')
    assert 'abc' in ns

    del s1
    collect_acyclic_refs()

    assert 'def' in ns
    assert 'abc' in ns


def test_weak_receiver():
    sentinel = []
    def received(sender, **kw):
        sentinel.append(kw)

    sig = blinker.Signal()

    # XXX: weirdly, under jython an explicit weak=True causes this test
    #      to fail, leaking a strong ref to the receiver somewhere.
    #      http://bugs.jython.org/issue1586
    if jython:
        sig.connect(received)  # weak=True by default.
    else:
        sig.connect(received, weak=True)

    del received
    collect_acyclic_refs()

    assert not sentinel
    sig.send()
    assert not sentinel
    assert not sig.receivers
    values_are_empty_sets_(sig._by_receiver)
    values_are_empty_sets_(sig._by_sender)


def test_strong_receiver():
    sentinel = []
    def received(sender):
        sentinel.append(sender)
    fn_id = id(received)

    sig = blinker.Signal()
    sig.connect(received, weak=False)

    del received
    collect_acyclic_refs()

    assert not sentinel
    sig.send()
    assert sentinel
    assert [id(fn) for fn in sig.receivers.values()] == [fn_id]


def test_instancemethod_receiver():
    sentinel = []

    class Receiver(object):
        def __init__(self, bucket):
            self.bucket = bucket
        def received(self, sender):
            self.bucket.append(sender)

    receiver = Receiver(sentinel)

    sig = blinker.Signal()
    sig.connect(receiver.received)

    assert not sentinel
    sig.send()
    assert sentinel
    del receiver
    collect_acyclic_refs()

    sig.send()
    assert len(sentinel) == 1


def test_filtered_receiver():
    sentinel = []
    def received(sender):
        sentinel.append(sender)

    sig = blinker.Signal()

    sig.connect(received, 123)

    assert not sentinel
    sig.send()
    assert not sentinel
    sig.send(123)
    assert sentinel == [123]
    sig.send()
    assert sentinel == [123]

    sig.disconnect(received, 123)
    sig.send(123)
    assert sentinel == [123]

    sig.connect(received, 123)
    sig.send(123)
    assert sentinel == [123, 123]

    sig.disconnect(received)
    sig.send(123)
    assert sentinel == [123, 123]


def test_filtered_receiver_weakref():
    sentinel = []
    def received(sender):
        sentinel.append(sender)

    class Object(object):
        pass
    obj = Object()

    sig = blinker.Signal()
    sig.connect(received, obj)

    assert not sentinel
    sig.send(obj)
    assert sentinel == [obj]
    del sentinel[:]
    del obj
    collect_acyclic_refs()

    # general index isn't cleaned up
    assert sig.receivers
    # but receiver/sender pairs are
    values_are_empty_sets_(sig._by_receiver)
    values_are_empty_sets_(sig._by_sender)


def test_decorated_receiver():
    sentinel = []

    class Object(object):
        pass
    obj = Object()

    sig = blinker.Signal()

    @sig.connect_via(obj)
    def receiver(sender, **kw):
        sentinel.append(kw)

    assert not sentinel
    sig.send()
    assert not sentinel
    sig.send(1)
    assert not sentinel
    sig.send(obj)
    assert sig.receivers

    del receiver
    collect_acyclic_refs()
    assert sig.receivers


def test_no_double_send():
    sentinel = []
    def received(sender):
        sentinel.append(sender)

    sig = blinker.Signal()

    sig.connect(received, 123)
    sig.connect(received)

    assert not sentinel
    sig.send()
    assert sentinel == [None]
    sig.send(123)
    assert sentinel == [None, 123]
    sig.send()
    assert sentinel == [None, 123, None]


def test_has_receivers():
    received = lambda sender: None

    sig = blinker.Signal()
    assert not sig.has_receivers_for(None)
    assert not sig.has_receivers_for(blinker.ANY)

    sig.connect(received, 'xyz')
    assert not sig.has_receivers_for(None)
    assert not sig.has_receivers_for(blinker.ANY)
    assert sig.has_receivers_for('xyz')

    class Object(object):
        pass
    o = Object()

    sig.connect(received, o)
    assert sig.has_receivers_for(o)

    del received
    collect_acyclic_refs()

    assert not sig.has_receivers_for('xyz')
    assert list(sig.receivers_for('xyz')) == []
    assert list(sig.receivers_for(o)) == []

    sig.connect(lambda sender: None, weak=False)
    assert sig.has_receivers_for('xyz')
    assert sig.has_receivers_for(o)
    assert sig.has_receivers_for(None)
    assert sig.has_receivers_for(blinker.ANY)
    assert sig.has_receivers_for('xyz')


def test_instance_doc():
    sig = blinker.Signal(doc='x')
    assert sig.__doc__ == 'x'

    sig = blinker.Signal('x')
    assert sig.__doc__ == 'x'


def test_named_blinker():
    sig = blinker.NamedSignal('squiznart')
    assert 'squiznart' in repr(sig)


def values_are_empty_sets_(dictionary):
    for val in dictionary.values():
        assert val == set()

if sys.version_info < (2, 5):
    def test_context_manager_warning():
        sig = blinker.Signal()
        receiver = lambda sender: None

        assert_raises(RuntimeError, sig.connected_to, receiver)

########NEW FILE########
__FILENAME__ = test_utilities
import pickle

from blinker._utilities import symbol


def test_symbols():
    foo = symbol('foo')
    assert foo.name == 'foo'
    assert foo is symbol('foo')

    bar = symbol('bar')
    assert foo is not bar
    assert foo != bar
    assert not foo == bar

    assert repr(foo) == 'foo'


def test_pickled_symbols():
    foo = symbol('foo')

    for protocol in 0, 1, 2:
        roundtrip = pickle.loads(pickle.dumps(foo))
        assert roundtrip is foo

########NEW FILE########
