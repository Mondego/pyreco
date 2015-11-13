__FILENAME__ = abstract
# coding: utf-8
"""
    brownie.abstract
    ~~~~~~~~~~~~~~~~

    Utilities to deal with abstract base classes.

    .. versionadded:: 0.2

    :copyright: 2010-2011 by Daniel Neuhäuser
    :license: BSD, see LICENSE.rst for details
"""
try:
    from abc import ABCMeta
except ImportError:
    class ABCMeta(type):
        """Dummy :class:`abc.ABCMeta` implementation which does nothing."""

        def register(self, subclass):
            pass


class VirtualSubclassMeta(type):
    """
    A metaclass which allows you to easily define abstract super classes,
    simply inherit from this metaclass and set the
    :attr:`virtual_superclasses` attribute to an iterable:

        >>> from brownie.abstract import ABCMeta, VirtualSubclassMeta
        >>>
        >>> class VirtualBaseClass(object):
        ...     __metaclass__ = ABCMeta
        >>>
        >>> class VirtualSubclass(object):
        ...     __metaclass__ = VirtualSubclassMeta
        ...
        ...     virtual_superclasses = (VirtualBaseClass, )
        >>>
        >>> issubclass(VirtualSubclass, VirtualBaseClass)
        True
    """
    def __init__(self, name, bases, attributes):
        type.__init__(self, name, bases, attributes)
        self._register_superclasses(attributes.get('virtual_superclasses', ()))

    def _register_superclasses(self, superclasses):
        for cls in superclasses:
            if isinstance(cls, ABCMeta):
                cls.register(self)
            if hasattr(cls, 'virtual_superclasses'):
                self._register_superclasses(cls.virtual_superclasses)


class AbstractClassMeta(ABCMeta, VirtualSubclassMeta):
    """
    A metaclass for abstract base classes which are also virtual subclasses.

    Simply set :attr:`virtual_subclasses` to an iterable of classes your class
    is supposed to virtually inherit from:

    >>> from brownie.abstract import ABCMeta, AbstractClassMeta, \\
    ...                              VirtualSubclassMeta
    >>> class Foo(object):
    ...     __metaclass__ = ABCMeta
    >>>
    >>> class Bar(object):
    ...     __metaclass__ = AbstractClassMeta
    ...
    ...     virtual_superclasses = (Foo, )
    >>>
    >>> class Baz(object):
    ...     __metaclass__ = VirtualSubclassMeta
    ...
    ...     virtual_superclasses = (Bar, )
    >>>
    >>> issubclass(Baz, Foo)
    True
    >>> issubclass(Baz, Bar)
    True

    .. note::
        All classes could use :class:`AbstractClassMeta` as `__metaclass__`
        and the result would be the same, the usage here is just to demonstrate
        the specific problem which is solved.
    """


__all__ = ['ABCMeta', 'VirtualSubclassMeta', 'AbstractClassMeta']

########NEW FILE########
__FILENAME__ = caching
# coding: utf-8
"""
    brownie.caching
    ~~~~~~~~~~~~~~~

    Caching utilities.

    :copyright: 2010-2011 by Daniel Neuhäuser
    :license: BSD, see LICENSE.rst for details
"""
from functools import wraps

from brownie.datastructures import OrderedDict, Counter, missing


class cached_property(object):
    """
    Property which caches the result of the given `getter`.

    :param doc: Optional docstring which is used instead of the `getter`\s
                docstring.
    """
    def __init__(self, getter, doc=None):
        self.getter = getter
        self.__module__ = getter.__module__
        self.__name__ = getter.__name__
        self.__doc__ = doc or getter.__doc__

    def __get__(self, obj, type=None):
        if obj is None:
            return self
        value = obj.__dict__[self.__name__] = self.getter(obj)
        return value


class CacheBase(object):
    """
    Base class for all caches, which is supposed to be used as a mixin.
    """
    @classmethod
    def decorate(cls, maxsize=float('inf')):
        """
        Returns a decorator which can be used to create functions whose
        results are cached.

        In order to clear the cache of the decorated function call `.clear()`
        on it.

        ::

            @CacheBase.decorate(maxsize=1024) # items stored in the cache
            def foo(a, b):
                return a + b # imagine a very expensive operation here
        """
        def decorator(function, _maxsize=maxsize):
            cache = cls(maxsize=maxsize)
            @wraps(function)
            def wrapper(*args, **kwargs):
                key = args
                if kwargs:
                    key += tuple(sorted(kwargs.iteritems()))
                try:
                    result = cache[key]
                except KeyError:
                    result = function(*args, **kwargs)
                    cache[key] = result
                return result
            wrapper.clear = cache.clear
            return wrapper
        return decorator


class LRUCache(OrderedDict, CacheBase):
    """
    :class:`~brownie.datastructures.OrderedDict` based cache which removes the
    least recently used item once `maxsize` is reached.

    .. note:: The order of the dict is changed each time you access the dict.
    """
    def __init__(self, mapping=(), maxsize=float('inf')):
        OrderedDict.__init__(self, mapping)
        self.maxsize = maxsize

    def __getitem__(self, key):
        self.move_to_end(key)
        return OrderedDict.__getitem__(self, key)

    def __setitem__(self, key, value):
        if len(self) >= self.maxsize:
            self.popitem(last=False)
        OrderedDict.__setitem__(self, key, value)

    def __repr__(self):
        return '%s(%s, %f)' % (
            self.__class__.__name__, dict.__repr__(self), self.maxsize
        )


class LFUCache(dict, CacheBase):
    """
    :class:`dict` based cache which removes the least frequently used item once
    `maxsize` is reached.
    """
    def __init__(self, mapping=(), maxsize=float('inf')):
        dict.__init__(self, mapping)
        self.maxsize = maxsize
        self.usage_counter = Counter()

    def __getitem__(self, key):
        value = dict.__getitem__(self, key)
        self.usage_counter[key] += 1
        return value

    def __setitem__(self, key, value):
        dict.__setitem__(self, key, value)
        for key, _ in self.usage_counter.most_common(len(self) - self.maxsize):
            del self[key]

    def __delitem__(self, key):
        dict.__delitem__(self, key)
        del self.usage_counter[key]

    def pop(self, key, default=missing):
        try:
            value = self[key]
            del self[key]
            return value
        except KeyError:
            if default is missing:
                raise
            return default

    def setdefault(self, key, default=None):
        if key not in self:
            self[key] = default
        return self[key]

    def popitem(self):
        item = dict.__popitem__(self)
        del self.usage_counter[item[0]]
        return item

    def __repr__(self):
        return '%s(%s, %f)' % (
            self.__class__.__name__, dict.__repr__(self), self.maxsize
        )


#: A memoization decorator, which uses a simple dictionary of infinite size as
#: cache::
#:
#:     @memoize
#:     def foo(a, b):
#:         return a + b
#:
#: .. versionadded:: 0.5
memoize = lambda func: type(
    '_MemoizeCache', (dict, CacheBase), {}
).decorate()(func)


__all__ = ['cached_property', 'LRUCache', 'LFUCache', 'memoize']

########NEW FILE########
__FILENAME__ = context
# coding: utf-8
"""
    brownie.context
    ~~~~~~~~~~~~~~~

    Utilities to deal with context managers.

    .. versionadded:: 0.6

    :copyright: 2010-2011 by Daniel Neuhäuser
    :license: BSD, see LICENSE.rst for details
"""
from __future__ import with_statement
import thread
import threading
from operator import itemgetter
from itertools import count

from brownie.caching import LFUCache


def _make_stack_methods(name, lockname, stackname):
    def push(self, obj):
        """
        Pushes the given object onto the %s stack.
        """
        with getattr(self, lockname):
            self._add_object(getattr(self, stackname), obj)
            self._cache.clear()

    def pop(self):
        """
        Pops and returns an object from the %s stack.
        """
        with getattr(self, lockname):
            stack = self._get_objects(getattr(self, stackname))
            if stack is None:
                raise RuntimeError('no objects on stack')
            self._cache.clear()
            return stack.pop()[1]

    push.__name__ = 'push_' + name
    push.__doc__ = push.__doc__ % name
    pop.__name__ = 'pop_' + name
    pop.__doc__ = pop.__doc__ % name
    return push, pop


class ContextStackManagerBase(object):
    """
    Helper which manages context dependant stacks.

    A common API pattern is using context managers to change options; those
    options are internally stored on a stack.

    However larger applications have multiple execution contexts such as
    processes, threads and/or coroutines/greenthreads and such an API becomes
    a problem as each modification of the stack becomes visible to every
    execution context.

    This helper allows you to make stack operations local to the current
    execution context, ensuring that the stack remains the same in other
    contexts unless you want it to change there.

    As applications tend to have very different requirements and use different
    contexts each is implemented in a separate mixin, this way it easily
    possible to create a `ContextStackManager` for your needs.

    Assuming your application uses threads and eventlet for greenthreads you
    would create a `ContextStackManager` like this::

        class ContextStackManager(
                ContextStackManagerEventletMixin,
                ContextStackManagerThreadMixin,
                ContextStackManagerBase
            ):
            pass

    Greenthreads are executed in a thread, whereas threads are executed in
    the application thread (handled by the base class) this is why
    `ContextStackManager` inherits from these classes exactly in this order.

    Currently available mixins are:

    - :class:`ContextStackManagerThreadMixin`
    - :class:`ContextStackManagerEventletMixin`
    """
    def __init__(self, _object_cache_maxsize=256):
        self._application_stack = []
        self._cache = LFUCache(maxsize=_object_cache_maxsize)
        self._contexts = []
        self._stackop = count().next

    def _get_ident(self):
        return ()

    def _make_item(self, obj):
        return self._stackop(), obj

    def _get_objects(self, context):
        return getattr(context, 'objects', None)

    def _add_object(self, context, obj):
        item = self._make_item(obj)
        objects = self._get_objects(context)
        if objects is None:
            context.objects = [item]
        else:
            objects.append(item)

    def iter_current_stack(self):
        """
        Returns an iterator over the items in the 'current' stack, ordered
        from top to bottom.
        """
        ident = self._get_ident()
        objects = self._cache.get(ident)
        if objects is None:
            objects = self._application_stack[:]
            for context in self._contexts:
                objects.extend(getattr(context, 'objects', ()))
            objects.reverse()
            self._cache[ident] = objects = map(itemgetter(1), objects)
        return iter(objects)

    def push_application(self, obj):
        """
        Pushes the given object onto the application stack.
        """
        self._application_stack.append(self._make_item(obj))
        self._cache.clear()

    def pop_application(self):
        """
        Pops and returns an object from the application stack.
        """
        if not self._application_stack:
            raise RuntimeError('no objects on application stack')
        self._cache.clear()
        return self._application_stack.pop()[1]


class ContextStackManagerThreadMixin(object):
    """
    A :class:`ContextStackManagerBase` mixin providing thread context support.
    """
    def __init__(self, *args, **kwargs):
        super(ContextStackManagerThreadMixin, self).__init__(*args, **kwargs)
        self._thread_context = threading.local()
        self._contexts.append(self._thread_context)
        self._thread_lock = threading.Lock()

    def _get_ident(self):
        return super(
            ContextStackManagerThreadMixin,
            self
        )._get_ident() + (thread.get_ident(), )

    push_thread, pop_thread = _make_stack_methods(
        'thread', '_thread_lock', '_thread_context'
    )


class ContextStackManagerEventletMixin(object):
    """
    A :class:`ContextStackManagerBase` mixin providing coroutine/greenthread
    context support using eventlet_.

    .. _eventlet: http://eventlet.net
    """
    def __init__(self, *args, **kwargs):
        super(ContextStackManagerEventletMixin, self).__init__(*args, **kwargs)
        try:
            from eventlet.corolocal import local
            from eventlet.semaphore import BoundedSemaphore
        except ImportError:
            raise RuntimeError(
                'the eventlet library is required for %s' %
                self.__class__.__name__
            )
        self._coroutine_context = local()
        self._contexts.append(self._coroutine_context)
        self._coroutine_lock = BoundedSemaphore()

    def _get_ident(self):
        from eventlet.corolocal import get_ident
        return super(
            ContextStackManagerEventletMixin,
            self
        )._get_ident() + (get_ident(), )

    push_coroutine, pop_coroutine = _make_stack_methods(
        'coroutine', '_coroutine_lock', '_coroutine_context'
    )


__all__ = [
    'ContextStackManagerBase', 'ContextStackManagerThreadMixin',
    'ContextStackManagerEventletMixin'
]

########NEW FILE########
__FILENAME__ = iterators
# coding: utf-8
"""
    brownie.datastructures.iterators
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    :copyright: 2010-2011 by Daniel Neuhäuser
    :license: BSD, see LICENSE.rst for details
"""
from collections import deque


class PeekableIterator(object):
    """
    An iterator which allows peeking.

    .. versionadded:: 0.6
    """
    def __init__(self, iterable):
        self.iterator = iter(iterable)
        self.remaining = deque()

    def next(self):
        if self.remaining:
            return self.remaining.popleft()
        return self.iterator.next()

    def peek(self, n=1):
        """
        Returns the next `n` items without consuming the iterator, if the
        iterator has less than `n` items these are returned.

        Raises :exc:`ValueError` if `n` is lower than 1.
        """
        if n < 1:
            raise ValueError('n should be greater than 0')
        items = list(self.remaining)[:n]
        while len(items) < n:
            try:
                item = self.iterator.next()
            except StopIteration:
                break
            items.append(item)
            self.remaining.append(item)
        return items

    def __iter__(self):
        return self

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.iterator)


__all__ = ['PeekableIterator']

########NEW FILE########
__FILENAME__ = mappings
# coding: utf-8
"""
    brownie.datastructures.mappings
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    :copyright: 2010-2011 by Daniel Neuhäuser
    :license: BSD, see LICENSE.rst for details
"""
from heapq import nlargest
from operator import itemgetter
from itertools import izip, repeat, ifilter

from brownie.itools import chain, unique, starmap
from brownie.abstract import AbstractClassMeta
from brownie.datastructures import missing


def iter_multi_items(mapping):
    """
    Iterates over the items of the given `mapping`.

    If a key has multiple values a ``(key, value)`` item is yielded for each::

        >>> for key, value in iter_multi_items({1: [2, 3]}):
        ...     print key, value
        1 2
        1 3
        >>> for key, value in iter_multi_items(MultiDict({1: [2, 3]})):
        ...     print key, value
        1 2
        1 3
    """
    if isinstance(mapping, MultiDict):
        for item in mapping.iteritems(multi=False):
            yield item
    elif isinstance(mapping, dict):
        for key, value in mapping.iteritems():
            if isinstance(value, (tuple, list)):
                for value in value:
                    yield key, value
            else:
                yield key, value
    else:
        for item in mapping:
            yield item


@classmethod
def raise_immutable(cls, *args, **kwargs):
    raise TypeError('%r objects are immutable' % cls.__name__)


class ImmutableDictMixin(object):
    @classmethod
    def fromkeys(cls, keys, value=None):
        return cls(zip(keys, repeat(value)))

    __setitem__ = __delitem__ = setdefault = update = pop = popitem = clear = \
        raise_immutable

    def __repr__(self):
        content = dict.__repr__(self) if self else ''
        return '%s(%s)' % (self.__class__.__name__, content)


class ImmutableDict(ImmutableDictMixin, dict):
    """
    An immutable :class:`dict`.

    .. versionadded:: 0.5
       :class:`ImmutableDict` is now hashable, given the content is.
    """
    __metaclass__ = AbstractClassMeta

    def __hash__(self):
        return hash(tuple(self.items()))


class CombinedDictMixin(object):
    @classmethod
    def fromkeys(cls, keys, value=None):
        raise TypeError('cannot create %r instances with .fromkeys()' %
            cls.__class__.__name__
        )

    def __init__(self, dicts=None):
        #: The list of combined dictionaries.
        self.dicts = [] if dicts is None else list(dicts)

    def __getitem__(self, key):
        for d in self.dicts:
            if key in d:
                return d[key]
        raise KeyError(key)

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def __iter__(self):
        return unique(chain.from_iterable(d.iterkeys() for d in self.dicts))

    iterkeys = __iter__

    def itervalues(self):
        for key in self:
            yield self[key]

    def iteritems(self):
        for key in self:
            yield key, self[key]

    def keys(self):
        return list(self.iterkeys())

    def values(self):
        return list(self.itervalues())

    def items(self):
        return list(self.iteritems())

    def __len__(self):
        return len(self.keys())

    def __contains__(self, key):
        return any(key in d for d in self.dicts)

    has_key = __contains__

    def __repr__(self):
        content = repr(self.dicts) if self.dicts else ''
        return '%s(%s)' % (self.__class__.__name__, content)


class CombinedDict(CombinedDictMixin, ImmutableDictMixin, dict):
    """
    An immutable :class:`dict` which combines the given `dicts` into one.

    You can use this class to combine dicts of any type, however different
    interfaces as provided by e.g. :class:`MultiDict` or :class:`Counter` are
    not supported, the same goes for additional keyword arguments.

    .. versionadded:: 0.2

    .. versionadded:: 0.5
       :class:`CombinedDict` is now hashable, given the content is.
    """
    __metaclass__ = AbstractClassMeta
    virtual_superclasses = (ImmutableDict, )

    def __hash__(self):
        return hash(tuple(self.dicts))


class MultiDictMixin(object):
    def __init__(self, *args, **kwargs):
        if len(args) > 1:
            raise TypeError(
                'expected at most 1 argument, got %d' % len(args)
            )
        arg = []
        if args:
            mapping = args[0]
            if isinstance(mapping, self.__class__):
                arg = ((k, l[:]) for k, l in mapping.iterlists())
            elif hasattr(mapping, 'iteritems'):
                for key, value in mapping.iteritems():
                    if isinstance(value, (tuple, list)):
                        value = list(value)
                    else:
                        value = [value]
                    arg.append((key, value))
            else:
                keys = []
                tmp = {}
                for key, value in mapping or ():
                    tmp.setdefault(key, []).append(value)
                    keys.append(key)
                arg = ((key, tmp[key]) for key in unique(keys))
        kws = {}
        for key, value in kwargs.iteritems():
            if isinstance(value, (tuple, list)):
                value = list(value)
            else:
                value = [value]
            kws[key] = value
        super(MultiDictMixin, self).__init__(arg, **kws)

    def __getitem__(self, key):
        """
        Returns the first value associated with the given `key`. If no value
        is found a :exc:`KeyError` is raised.
        """
        return super(MultiDictMixin, self).__getitem__(key)[0]

    def __setitem__(self, key, value):
        """
        Sets the values associated with the given `key` to ``[value]``.
        """
        super(MultiDictMixin, self).__setitem__(key, [value])

    def get(self, key, default=None):
        """
        Returns the first value associated with the given `key`, if there are
        none the `default` is returned.
        """
        try:
            return self[key]
        except KeyError:
            return default

    def add(self, key, value):
        """
        Adds the `value` for the given `key`.
        """
        super(MultiDictMixin, self).setdefault(key, []).append(value)

    def getlist(self, key):
        """
        Returns the :class:`list` of values for the given `key`. If there are
        none an empty :class:`list` is returned.
        """
        try:
            return super(MultiDictMixin, self).__getitem__(key)
        except KeyError:
            return []

    def setlist(self, key, values):
        """
        Sets the values associated with the given `key` to the given `values`.
        """
        super(MultiDictMixin, self).__setitem__(key, list(values))

    def setdefault(self, key, default=None):
        """
        Returns the value for the `key` if it is in the dict, otherwise returns
        `default` and sets that value for the `key`.
        """
        if key not in self:
            MultiDictMixin.__setitem__(self, key, default)
        else:
            default = MultiDictMixin.__getitem__(self, key)
        return default

    def setlistdefault(self, key, default_list=None):
        """
        Like :meth:`setdefault` but sets multiple values and returns the list
        associated with the `key`.
        """
        if key not in self:
            default_list = list(default_list or (None, ))
            MultiDictMixin.setlist(self, key, default_list)
        else:
            default_list = MultiDictMixin.getlist(self, key)
        return default_list

    def iteritems(self, multi=False):
        """Like :meth:`items` but returns an iterator."""
        for key, values in super(MultiDictMixin, self).iteritems():
            if multi:
                for value in values:
                    yield key, value
            else:
                yield key, values[0]

    def items(self, multi=False):
        """
        Returns a :class:`list` of ``(key, value)`` pairs.

        :param multi:
            If ``True`` the returned :class:`list` will contain a pair for
            every value associated with a key.
        """
        return list(self.iteritems(multi))

    def itervalues(self):
        """Like :meth:`values` but returns an iterator."""
        for values in super(MultiDictMixin, self).itervalues():
            yield values[0]

    def values(self):
        """
        Returns a :class:`list` with the first value of every key.
        """
        return list(self.itervalues())

    def iterlists(self):
        """Like :meth:`lists` but returns an iterator."""
        for key, values in super(MultiDictMixin, self).iteritems():
            yield key, list(values)

    def lists(self):
        """
        Returns a :class:`list` of ``(key, values)`` pairs, where `values` is
        the list of values associated with the `key`.
        """
        return list(self.iterlists())

    def iterlistvalues(self):
        """Like :meth:`listvalues` but returns an iterator."""
        return super(MultiDictMixin, self).itervalues()

    def listvalues(self):
        """
        Returns a :class:`list` of all values.
        """
        return list(self.iterlistvalues())

    def pop(self, key, default=missing):
        """
        Returns the first value associated with the given `key` and removes
        the item.
        """
        value = super(MultiDictMixin, self).pop(key, default)
        if value is missing:
            raise KeyError(key)
        elif value is default:
            return default
        return value[0]

    def popitem(self, *args, **kwargs):
        """
        Returns a key and the first associated value. The item is removed.
        """
        key, values = super(MultiDictMixin, self).popitem(*args, **kwargs)
        return key, values[0]

    def poplist(self, key):
        """
        Returns the :class:`list` of values associated with the given `key`,
        if the `key` does not exist in the :class:`MultiDict` an empty list is
        returned.
        """
        return super(MultiDictMixin, self).pop(key, [])

    def popitemlist(self):
        """Like :meth:`popitem` but returns all associated values."""
        return super(MultiDictMixin, self).popitem()

    def update(self, *args, **kwargs):
        """
        Extends the dict using the given mapping and/or keyword arguments.
        """
        if len(args) > 1:
            raise TypeError(
                'expected at most 1 argument, got %d' % len(args)
            )
        mappings = [args[0] if args else [], kwargs.iteritems()]
        for mapping in mappings:
            for key, value in iter_multi_items(mapping):
                MultiDictMixin.add(self, key, value)


class MultiDict(MultiDictMixin, dict):
    """
    A :class:`MultiDict` is a dictionary customized to deal with multiple
    values for the same key.

    Internally the values for each key are stored as a :class:`list`, but the
    standard :class:`dict` methods will only return the first value of those
    :class:`list`\s. If you want to gain access to every value associated with
    a key, you have to use the :class:`list` methods, specific to a
    :class:`MultiDict`.
    """
    __metaclass__ = AbstractClassMeta

    def __repr__(self):
        content = dict.__repr__(self) if self else ''
        return '%s(%s)' % (self.__class__.__name__, content)


class ImmutableMultiDictMixin(ImmutableDictMixin, MultiDictMixin):
    def add(self, key, value):
        raise_immutable(self)

    def setlist(self, key, values):
        raise_immutable(self)

    def setlistdefault(self, key, default_list=None):
        raise_immutable(self)

    def poplist(self, key):
        raise_immutable(self)

    def popitemlist(self):
        raise_immutable(self)


class ImmutableMultiDict(ImmutableMultiDictMixin, dict):
    """
    An immutable :class:`MultiDict`.

    .. versionadded:: 0.5
       :class:`ImmutableMultiDict` is now hashable, given the content is.
    """
    __metaclass__ = AbstractClassMeta

    virtual_superclasses = (MultiDict, ImmutableDict)

    def __hash__(self):
        return hash(tuple((key, tuple(value)) for key, value in self.lists()))


class CombinedMultiDict(CombinedDictMixin, ImmutableMultiDictMixin, dict):
    """
    An :class:`ImmutableMultiDict` which combines the given `dicts` into one.

    .. versionadded:: 0.2
    """
    __metaclass__ = AbstractClassMeta

    virtual_superclasses = (ImmutableMultiDict, )

    def getlist(self, key):
        return sum((d.getlist(key) for d in self.dicts), [])

    def iterlists(self):
        result = OrderedDict()
        for d in self.dicts:
            for key, values in d.iterlists():
                result.setdefault(key, []).extend(values)
        return result.iteritems()

    def iterlistvalues(self):
        for key in self:
            yield self.getlist(key)

    def iteritems(self, multi=False):
        for key in self:
            if multi:
                yield key, self.getlist(key)
            else:
                yield key, self[key]

    def items(self, multi=False):
        return list(self.iteritems(multi))


class _Link(object):
    __slots__ = 'key', 'prev', 'next'

    def __init__(self, key=None, prev=None, next=None):
        self.key = key
        self.prev = prev
        self.next = next

    def __getstate__(self):
        return self.key, self.prev, self.next

    def __setstate__(self, state):
        self.key, self.prev, self.next = state


class OrderedDict(dict):
    """
    A :class:`dict` which remembers insertion order.

    Big-O times for every operation are equal to the ones :class:`dict` has
    however this comes at the cost of higher memory usage.

    This dictionary is only equal to another dictionary of this type if the
    items on both dictionaries were inserted in the same order.
    """
    @classmethod
    def fromkeys(cls, iterable, value=None):
        """
        Returns a :class:`OrderedDict` with keys from the given `iterable`
        and `value` as value for each item.
        """
        return cls(izip(iterable, repeat(value)))

    def __init__(self, *args, **kwargs):
        if len(args) > 1:
            raise TypeError(
                'expected at most 1 argument, got %d' % len(args)
            )
        self._root = _Link()
        self._root.prev = self._root.next = self._root
        self._map = {}
        OrderedDict.update(self, *args, **kwargs)

    def __setitem__(self, key, value):
        """
        Sets the item with the given `key` to the given `value`.
        """
        if key not in self:
            last = self._root.prev
            link = _Link(key, last, self._root)
            last.next = self._root.prev = self._map[key] = link
        dict.__setitem__(self, key, value)

    def __delitem__(self, key):
        """
        Deletes the item with the given `key`.
        """
        dict.__delitem__(self, key)
        link = self._map.pop(key)
        prev, next = link.prev, link.next
        prev.next, next.prev = link.next, link.prev

    def setdefault(self, key, default=None):
        """
        Returns the value of the item with the given `key`, if not existant
        sets creates an item with the `default` value.
        """
        if key not in self:
            OrderedDict.__setitem__(self, key, default)
        return OrderedDict.__getitem__(self, key)

    def pop(self, key, default=missing):
        """
        Deletes the item with the given `key` and returns the value. If the
        item does not exist a :exc:`KeyError` is raised unless `default` is
        given.
        """
        try:
            value = dict.__getitem__(self, key)
            del self[key]
            return value
        except KeyError:
            if default is missing:
                raise
            return default

    def popitem(self, last=True):
        """
        Pops the last or first item from the dict depending on `last`.
        """
        if not self:
            raise KeyError('dict is empty')
        key = (reversed(self) if last else iter(self)).next()
        return key, OrderedDict.pop(self, key)

    def move_to_end(self, key, last=True):
        """
        Moves the item with the given `key` to the end of the dictionary if
        `last` is ``True`` otherwise to the beginning.

        Raises :exc:`KeyError` if no item with the given `key` exists.

        .. versionadded:: 0.4
        """
        if key not in self:
            raise KeyError(key)
        link = self._map[key]
        prev, next = link.prev, link.next
        prev.next, next.prev = next, prev
        if last:
            replacing = self._root.prev
            replacing.next = self._root.prev = link
            link.prev, link.next = replacing, self._root
        else:
            replacing = self._root.next
            self._root.next = replacing.prev = link
            link.prev, link.next = self._root, replacing

    def update(self, *args, **kwargs):
        """
        Updates the dictionary with a mapping and/or from keyword arguments.
        """
        if len(args) > 1:
            raise TypeError(
                'expected at most 1 argument, got %d' % len(args)
            )
        mappings = []
        if args:
            if hasattr(args[0], 'iteritems'):
                mappings.append(args[0].iteritems())
            else:
                mappings.append(args[0])
        mappings.append(kwargs.iteritems())
        for mapping in mappings:
            for key, value in mapping:
                OrderedDict.__setitem__(self, key, value)

    def clear(self):
        """
        Clears the contents of the dict.
        """
        self._root = _Link()
        self._root.prev = self._root.next = self._root
        self._map.clear()
        dict.clear(self)

    def __eq__(self, other):
        """
        Returns ``True`` if this dict is equal to the `other` one. If the
        other one is a :class:`OrderedDict` as well they are only considered
        equal if the insertion order is identical.
        """
        if isinstance(other, self.__class__):
            return all(
                i1 == i2 for i1, i2 in izip(self.iteritems(), other.iteritems())
            )
        return dict.__eq__(self, other)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __iter__(self):
        curr = self._root.next
        while curr is not self._root:
            yield curr.key
            curr = curr.next

    def __reversed__(self):
        curr = self._root.prev
        while curr is not self._root:
            yield curr.key
            curr = curr.prev

    def iterkeys(self):
        """
        Returns an iterator over the keys of all items in insertion order.
        """
        return OrderedDict.__iter__(self)

    def itervalues(self):
        """
        Returns an iterator over the values of all items in insertion order.
        """
        return (dict.__getitem__(self, k) for k in OrderedDict.__iter__(self))

    def iteritems(self):
        """
        Returns an iterator over all the items in insertion order.
        """
        return izip(OrderedDict.iterkeys(self), OrderedDict.itervalues(self))

    def keys(self):
        """
        Returns a :class:`list` over the keys of all items in insertion order.
        """
        return list(OrderedDict.iterkeys(self))

    def values(self):
        """
        Returns a :class:`list` over the values of all items in insertion order.
        """
        return list(OrderedDict.itervalues(self))

    def items(self):
        """
        Returns a :class:`list` over the items in insertion order.
        """
        return zip(OrderedDict.keys(self), OrderedDict.values(self))

    def __repr__(self):
        content = repr(self.items()) if self else ''
        return '%s(%s)' % (self.__class__.__name__, content)


class ImmutableOrderedDict(ImmutableDictMixin, OrderedDict):
    """
    An immutable :class:`OrderedDict`.

    .. versionadded:: 0.2

    .. versionadded:: 0.5
       :class:`ImmutableOrderedDict` is now hashable, given the content is.
    """
    __metaclass__ = AbstractClassMeta

    virtual_superclasses = (ImmutableDict, )

    move_to_end = raise_immutable

    def __hash__(self):
        return hash(tuple(self.iteritems()))

    __repr__ = OrderedDict.__repr__


class OrderedMultiDict(MultiDictMixin, OrderedDict):
    """An ordered :class:`MultiDict`."""
    __metaclass__ = AbstractClassMeta

    virtual_superclasses = (MultiDict, )


class ImmutableOrderedMultiDict(ImmutableMultiDictMixin, ImmutableOrderedDict):
    """An immutable :class:`OrderedMultiDict`."""
    __metaclass__ = AbstractClassMeta

    virtual_superclasses = (ImmutableMultiDict, OrderedMultiDict)

    def __repr__(self):
        content = repr(self.items()) if self else ''
        return '%s(%s)' % (self.__class__.__name__, content)


class FixedDict(dict):
    """
    A :class:`dict` whose items can only be created or deleted not changed.

    If you attempt to change an item a :exc:`KeyError` is raised.

    .. versionadded:: 0.5
    """
    def __setitem__(self, key, value):
        if key in self:
            raise KeyError('already set')
        dict.__setitem__(self, key, value)

    def update(self, *args, **kwargs):
        if len(args) > 1:
            raise TypeError(
                'expected at most 1 argument, got %d' % len(args)
            )
        mappings = []
        if args:
            if hasattr(args[0], 'iteritems'):
                mappings.append(args[0].iteritems())
            else:
                mappings.append(args[0])
        mappings.append(kwargs.iteritems())
        for mapping in mappings:
            for key, value in mapping:
                FixedDict.__setitem__(self, key, value)

    def __repr__(self):
        return '%s(%s)' % (
            self.__class__.__name__,
            dict.__repr__(self) if self else ''
        )


class Counter(dict):
    """
    :class:`dict` subclass for counting hashable objects. Elements are stored
    as keys with the values being their respective counts.

    :param countable: An iterable of elements to be counted or a
                      :class:`dict`\-like object mapping elements to their
                      respective counts.

    This object supports several operations returning a new :class:`Counter`
    object from the common elements of `c1` and `c2`, in any case the new
    counter will not contain negative counts.

    +-------------+-----------------------------------------------------+
    | Operation   | Result contains...                                  |
    +=============+=====================================================+
    | ``c1 + c2`` | sums of common element counts.                      |
    +-------------+-----------------------------------------------------+
    | ``c1 - c2`` | difference of common element counts.                |
    +-------------+-----------------------------------------------------+
    | ``c1 | c2`` | maximum of common element counts.                   |
    +-------------+-----------------------------------------------------+
    | ``c1 & c2`` | minimum of common element counts.                   |
    +-------------+-----------------------------------------------------+

    Furthermore it is possible to multiply the counter with an :class:`int` as
    scalar.

    Accessing a non-existing element will always result in an element
    count of 0, accordingly :meth:`get` uses 0 and :meth:`setdefault` uses 1 as
    default value.
    """
    def __init__(self, countable=None, **kwargs):
        self.update(countable, **kwargs)

    def __missing__(self, key):
        return 0

    def get(self, key, default=0):
        return dict.get(self, key, default)

    def setdefault(self, key, default=1):
        return dict.setdefault(self, key, default)

    def most_common(self, n=None):
        """
        Returns a list of all items sorted from the most common to the least.

        :param n: If given only the items of the `n`\-most common elements are
                  returned.

        >>> from brownie.datastructures import Counter
        >>> Counter('Hello, World!').most_common(2)
        [('l', 3), ('o', 2)]
        """
        if n is None:
            return sorted(self.iteritems(), key=itemgetter(1), reverse=True)
        return nlargest(n, self.iteritems(), key=itemgetter(1))

    def elements(self):
        """
        Iterator over the elements in the counter, repeating as many times as
        counted.

        >>> from brownie.datastructures import Counter
        >>> sorted(Counter('abcabc').elements())
        ['a', 'a', 'b', 'b', 'c', 'c']
        """
        return chain(*starmap(repeat, self.iteritems()))

    def update(self, countable=None, **kwargs):
        """
        Updates the counter from the given `countable` and `kwargs`.
        """
        countable = countable or []
        if hasattr(countable, 'iteritems'):
            mappings = [countable.iteritems()]
        else:
            mappings = [izip(countable, repeat(1))]
        mappings.append(kwargs.iteritems())
        for mapping in mappings:
            for element, count in mapping:
                self[element] = self.get(element) + count

    def __add__(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented
        result = Counter()
        for element in set(self) | set(other):
            newcount = self[element] + other[element]
            if newcount > 0:
                result[element] = newcount
        return result

    def __sub__(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented
        result = Counter()
        for element in set(self) | set(other):
            newcount = self[element] - other[element]
            if newcount > 0:
                result[element] = newcount

    def __mul__(self, other):
        if not isinstance(other, int):
            return NotImplemented
        result = Counter()
        for element in self:
            newcount = self[element] * other
            if newcount > 0:
                result[element] = newcount
        return result

    def __or__(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented
        result = Counter()
        for element in set(self) | set(other):
            newcount = max(self[element], other[element])
            if newcount > 0:
                result[element] = newcount
        return result

    def __and__(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented
        result = Counter()
        if len(self) < len(other):
            self, other = other, self
        for element in ifilter(self.__contains__, other):
            newcount = min(self[element], other[element])
            if newcount > 0:
                result[element] = newcount
        return result


########NEW FILE########
__FILENAME__ = queues
# coding: utf-8
"""
    brownie.datastructures.queues
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    :copyright 2010-2011 by Daniel Neuhäuser
    :license: BSD, see LICENSE.rst for details
"""
import Queue as queue


class SetQueue(queue.Queue):
    """Thread-safe implementation of an ordered set queue, which coalesces
    duplicate items into a single item if the older occurrence has not yet been
    read and maintains the order of items in the queue.

    Ordered set queues are useful when implementing data structures like
    event buses or event queues where duplicate events need to be coalesced
    into a single event. An example use case is the inotify API in the Linux
    kernel which shares the same behaviour.

    Queued items must be immutable and hashable so that they can be used as
    dictionary keys or added to sets. Items must have only read-only properties
    and must implement the :meth:`__hash__`, :meth:`__eq__`, and :meth:`__ne__`
    methods to be hashable.

    An example item class implementation follows::

        class QueuedItem(object):
            def __init__(self, a, b):
                self._a = a
                self._b = b

            @property
            def a(self):
                return self._a

            @property
            def b(self):
                return self._b

            def _key(self):
                return (self._a, self._b)

            def __eq__(self, item):
                return self._key() == item._key()

            def __ne__(self, item):
                return self._key() != item._key()

            def __hash__(self):
                return hash(self._key())

    .. NOTE::
        This ordered set queue leverages locking already present in the
        :class:`queue.Queue` class redefining only internal primitives. The
        order of items is maintained because the internal queue is not replaced.
        An internal set is used merely to check for the existence of an item in
        the queue.

    .. versionadded:: 0.3

    :author: Gora Khargosh <gora.khargosh@gmail.com>
    :author: Lukáš Lalinský <lalinsky@gmail.com>
    """
    def _init(self, maxsize):
        queue.Queue._init(self, maxsize)
        self._set_of_items = set()

    def _put(self, item):
        if item not in self._set_of_items:
            queue.Queue._put(self, item)
            self._set_of_items.add(item)

    def _get(self):
        item = queue.Queue._get(self)
        self._set_of_items.remove(item)
        return item


__all__ = ['SetQueue']

########NEW FILE########
__FILENAME__ = sequences
# coding: utf-8
"""
    brownie.datastructures.sequences
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    :copyright: 2010-2011 by Daniel Neuhäuser
    :license: BSD, see LICENSE.rst for details
"""
import textwrap
from keyword import iskeyword
from functools import wraps
from itertools import count

from brownie.itools import chain


class LazyList(object):
    """
    Implements a lazy list which computes items based on the given `iterable`.

    This allows you to create :class:`list`\-like objects of unlimited size.
    However although most operations don't exhaust the internal iterator
    completely some of them do, so if the given iterable is of unlimited size
    making such an operation will eventually cause a :exc:`MemoryError`.

    Cost in terms of laziness of supported operators, this does not include
    supported operators without any cost:

    +-----------------+-------------------------------------------------------+
    | Operation       | Result                                                |
    +=================+=======================================================+
    | ``list[i]``     | This exhausts the `list` up until the given index.    |
    +-----------------+                                                       |
    | ``list[i] = x`` |                                                       |
    +-----------------+                                                       |
    | ``del list[i]`` |                                                       |
    +-----------------+-------------------------------------------------------+
    | ``len(list)``   | Exhausts the internal iterator.                       |
    +-----------------+-------------------------------------------------------+
    | ``x in list``   | Exhausts the `list` up until `x` or until the `list`  |
    |                 | is exhausted.                                         |
    +-----------------+-------------------------------------------------------+
    | ``l1 == l2``    | Exhausts both lists.                                  |
    +-----------------+-------------------------------------------------------+
    | ``l1 != l2``    | Exhausts both lists.                                  |
    +-----------------+-------------------------------------------------------+
    | ``bool(list)``  | Exhausts the `list` up to the first item.             |
    +-----------------+-------------------------------------------------------+
    | ``l1 < l2``     | Exhausts the list up to the first item which shows    |
    |                 | the result. In the worst case this exhausts both      |
    +-----------------+ lists.                                                |
    | ``l1 > l2``     |                                                       |
    +-----------------+-------------------------------------------------------+
    | ``l1 + l2``     | Creates a new :class:`LazyList` without exhausting    |
    |                 | `l1` or `l2`.                                         |
    +-----------------+-------------------------------------------------------+
    | ``list * n``    | Exhausts the `list`.                                  |
    +-----------------+                                                       |
    | ``list *= n``   |                                                       |
    +-----------------+-------------------------------------------------------+


    .. versionadded:: 0.5
       It is now possible to pickle :class:`LazyList`\s, however this will
       exhaust the list.
    """
    @classmethod
    def factory(cls, callable):
        """
        Returns a wrapper for a given callable which takes the return value
        of the wrapped callable and converts it into a :class:`LazyList`.
        """
        @wraps(callable)
        def wrap(*args, **kwargs):
            return cls(callable(*args, **kwargs))
        return wrap

    def exhausting(func):
        @wraps(func)
        def wrap(self, *args, **kwargs):
            self._exhaust()
            return func(self, *args, **kwargs)
        return wrap

    def __init__(self, iterable):
        if isinstance(iterable, (list, tuple, basestring)):
            #: ``True`` if the internal iterator is exhausted.
            self.exhausted = True
            self._collected_data = list(iterable)
        else:
            self._iterator = iter(iterable)
            self.exhausted = False
            self._collected_data = []

    def _exhaust(self, i=None):
        if self.exhausted:
            return
        elif i is None or i < 0:
            index_range = count(self.known_length)
        elif isinstance(i, slice):
            start, stop = i.start, i.stop
            if start < 0 or stop < 0:
                index_range = count(self.known_length)
            else:
                index_range = xrange(self.known_length, stop)
        else:
            index_range = xrange(self.known_length, i + 1)
        for i in index_range:
            try:
                self._collected_data.append(self._iterator.next())
            except StopIteration:
                self.exhausted = True
                break

    @property
    def known_length(self):
        """
        The number of items which have been taken from the internal iterator.
        """
        return len(self._collected_data)

    def append(self, object):
        """
        Appends the given `object` to the list.
        """
        self.extend([object])

    def extend(self, objects):
        """
        Extends the list with the given `objects`.
        """
        if self.exhausted:
            self._collected_data.extend(objects)
        else:
            self._iterator = chain(self._iterator, objects)

    def insert(self, index, object):
        """
        Inserts the given `object` at the given `index`.

        This method exhausts the internal iterator up until the given `index`.
        """
        self._exhaust(index)
        self._collected_data.insert(index, object)

    def pop(self, index=None):
        """
        Removes and returns the item at the given `index`, if no `index` is
        given the last item is used.

        This method exhausts the internal iterator up until the given `index`.
        """
        self._exhaust(index)
        if index is None:
            return self._collected_data.pop()
        return self._collected_data.pop(index)

    def remove(self, object):
        """
        Looks for the given `object` in the list and removes the first
        occurrence.

        If the item is not found a :exc:`ValueError` is raised.

        This method exhausts the internal iterator up until the first
        occurrence of the given `object` or entirely if it is not found.
        """
        while True:
            try:
                self._collected_data.remove(object)
                return
            except ValueError:
                if self.exhausted:
                    raise
                else:
                    self._exhaust(self.known_length)

    @exhausting
    def reverse(self):
        """
        Reverses the list.

        This method exhausts the internal iterator.
        """
        self._collected_data.reverse()

    @exhausting
    def sort(self, cmp=None, key=None, reverse=False):
        """
        Sorts the list using the given `cmp` or `key` function and reverses it
        if `reverse` is ``True``.

        This method exhausts the internal iterator.
        """
        self._collected_data.sort(cmp=cmp, key=key, reverse=reverse)

    @exhausting
    def count(self, object):
        """
        Counts the occurrences of the given `object` in the list.

        This method exhausts the internal iterator.
        """
        return self._collected_data.count(object)

    def index(self, object):
        """
        Returns first index of the `object` in list

        This method exhausts the internal iterator up until the given `object`.
        """
        for i, obj in enumerate(self):
            if obj == object:
                return i
        raise ValueError('%s not in LazyList' % object)

    def __getitem__(self, i):
        """
        Returns the object or objects at the given index.

        This method exhausts the internal iterator up until the given index.
        """
        self._exhaust(i)
        return self._collected_data[i]

    def __setitem__(self, i, obj):
        """
        Sets the given object or objects at the given index.

        This method exhausts the internal iterator up until the given index.
        """
        self._exhaust(i)
        self._collected_data[i] = obj

    def __delitem__(self, i):
        """
        Removes the item or items at the given index.

        This method exhausts the internal iterator up until the given index.
        """
        self._exhaust(i)
        del self._collected_data[i]

    @exhausting
    def __len__(self):
        """
        Returns the length of the list.

        This method exhausts the internal iterator.
        """
        return self.known_length

    def __contains__(self, other):
        for item in self:
            if item == other:
                return True
        return False

    @exhausting
    def __eq__(self, other):
        """
        Returns ``True`` if the list is equal to the given `other` list, which
        may be another :class:`LazyList`, a :class:`list` or a subclass of
        either.

        This method exhausts the internal iterator.
        """
        if isinstance(other, (self.__class__, list)):
            return self._collected_data == other
        return False

    def __ne__(self, other):
        """
        Returns ``True`` if the list is unequal to the given `other` list, which
        may be another :class:`LazyList`, a :class:`list` or a subclass of
        either.

        This method exhausts the internal iterator.
        """
        return not self.__eq__(other)

    __hash__ = None

    def __nonzero__(self):
        """
        Returns ``True`` if the list is not empty.

        This method takes one item from the internal iterator.
        """
        self._exhaust(0)
        return bool(self._collected_data)

    def __lt__(self, other):
        """
        This method returns ``True`` if this list is "lower than" the given
        `other` list. This is the case if...

        - this list is empty and the other is not.
        - the first nth item in this list which is unequal to the
          corresponding item in the other list, is lower than the corresponding
          item.

        If this and the other list is empty this method will return ``False``.
        """
        if isinstance(other, (self.__class__, list)):
            other = list(other)
        return list(self) < other


    def __gt__(self, other):
        """
        This method returns ``True`` if this list is "greater than" the given
        `other` list. This is the case if...

        - this list is not empty and the other is
        - the first nth item in this list which is unequal to the
          corresponding item in the other list, is greater than the
          corresponding item.

        If this and the other list is empty this method will return ``False``.
        """
        if isinstance(other, (self.__class__, list)):
            other = list(other)
        return list(self) > other

    def __add__(self, other):
        if isinstance(other, (list, self.__class__)):
            return self.__class__(chain(self, other))
        raise TypeError("can't concatenate with non-list: {0}".format(other))

    def __iadd__(self, other):
        self.extend(other)
        return self

    def __mul__(self, other):
        if isinstance(other, int):
            self._exhaust()
            return self.__class__(self._collected_data * other)
        raise TypeError("can't multiply sequence by non-int: {0}".format(other))

    def __imul__(self, other):
        if isinstance(other, int):
            self._exhaust()
            self._collected_data *= other
            return self
        else:
            raise TypeError(
                "can't multiply sequence by non-int: {0}".format(other)
            )

    @exhausting
    def __getstate__(self):
        return self._collected_data

    def __setstate__(self, state):
        self.exhausted = True
        self._collected_data = state

    def __repr__(self):
        """
        Returns the representation string of the list, if the list exhausted
        this looks like the representation of any other list, otherwise the
        "lazy" part is represented by "...", like "[1, 2, 3, ...]".
        """
        if self.exhausted:
            return repr(self._collected_data)
        elif not self._collected_data:
            return '[...]'
        return '[%s, ...]' % ', '.join(
            repr(obj) for obj in self._collected_data
        )

    del exhausting


class CombinedSequence(object):
    """
    A sequence combining other sequences.

    .. versionadded:: 0.5
    """
    def __init__(self, sequences):
        self.sequences = list(sequences)

    def at_index(self, index):
        """
        Returns the sequence and the 'sequence local' index::

            >>> foo = [1, 2, 3]
            >>> bar = [4, 5, 6]
            >>> cs = CombinedSequence([foo, bar])
            >>> cs[3]
            4
            >>> cs.at_index(3)
            ([4, 5, 6], 0)
        """
        seen = 0
        if index >= 0:
            for sequence in self.sequences:
                if seen <= index < seen + len(sequence):
                    return sequence, index - seen
                seen += len(sequence)
        else:
            for sequence in reversed(self.sequences):
                if seen >= index > seen - len(sequence):
                    return sequence, index - seen
                seen -= len(sequence)
        raise IndexError(index)

    def __getitem__(self, index):
        if isinstance(index, slice):
            return list(iter(self))[index]
        sequence, index = self.at_index(index)
        return sequence[index]

    def __len__(self):
        return sum(map(len, self.sequences))

    def __iter__(self):
        return chain.from_iterable(self.sequences)

    def __reversed__(self):
        return chain.from_iterable(reversed(map(reversed, self.sequences)))

    def __eq__(self, other):
        if isinstance(other, list):
            return list(self) == other
        elif isinstance(other, self.__class__):
            return self.sequences == other.sequences
        return False

    def __ne__(self, other):
        return not self == other

    __hash__ = None

    def __mul__(self, times):
        if not isinstance(times, int):
            return NotImplemented
        return list(self) * times

    def __rmul__(self, times):
        if not isinstance(times, int):
            return NotImplemented
        return times * list(self)

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.sequences)


class CombinedList(CombinedSequence):
    """
    A list combining other lists.

    .. versionadded:: 0.5
    """
    def count(self, item):
        """
        Returns the number of occurrences of the given `item`.
        """
        return sum(sequence.count(item) for sequence in self.sequences)

    def index(self, item, start=None, stop=None):
        """
        Returns the index of the first occurence of the given `item` between
        `start` and `stop`.
        """
        start = 0 if start is None else start
        for index, it in enumerate(self[start:stop]):
            if item == it:
                return index + start
        raise ValueError('%r not in list' % item)

    def __setitem__(self, index, item):
        if isinstance(index, slice):
            start = 0 if index.start is None else index.start
            stop = len(self) if index.stop is None else index.stop
            step = 1 if index.step is None else index.step
            for index, item in zip(range(start, stop, step), item):
                self[index] = item
        else:
            list, index = self.at_index(index)
            list[index] = item

    def __delitem__(self, index):
        if isinstance(index, slice):
            start = 0 if index.start is None else index.start
            stop = len(self) if index.stop is None else index.stop
            step = 1 if index.step is None else index.step
            for list, index in map(self.at_index, range(start, stop, step)):
                del list[index]
        else:
            list, index = self.at_index(index)
            del list[index]

    def append(self, item):
        """
        Appends the given `item` to the end of the list.
        """
        self.sequences[-1].append(item)

    def extend(self, items):
        """
        Extends the list by appending from the given iterable.
        """
        self.sequences[-1].extend(items)

    def insert(self, index, item):
        """
        Inserts the given `item` before the item at the given `index`.
        """
        list, index = self.at_index(index)
        list.insert(index, item)

    def pop(self, index=-1):
        """
        Removes and returns the item at the given `index`.

        An :exc:`IndexError` is raised if the index is out of range.
        """
        list, index = self.at_index(index)
        return list.pop(index)

    def remove(self, item):
        """
        Removes the first occurence of the given `item` from the list.
        """
        for sequence in self.sequences:
            try:
                return sequence.remove(item)
            except ValueError:
                # we may find a value in the next sequence
                pass
        raise ValueError('%r not in list' % item)

    def _set_values(self, values):
        lengths = map(len, self.sequences)
        previous_length = 0
        for length in lengths:
            stop = previous_length + length
            self[previous_length:stop] = values[previous_length:stop]
            previous_length += length

    def reverse(self):
        """
        Reverses the list in-place::

            >>> a = [1, 2, 3]
            >>> b = [4, 5, 6]
            >>> l = CombinedList([a, b])
            >>> l.reverse()
            >>> a
            [6, 5, 4]
        """
        self._set_values(self[::-1])

    def sort(self, cmp=None, key=None, reverse=False):
        """
        Sorts the list in-place, see :meth:`list.sort`.
        """
        self._set_values(sorted(self, cmp, key, reverse))


def namedtuple(typename, field_names, verbose=False, rename=False, doc=None):
    """
    Returns a :class:`tuple` subclass named `typename` with a limited number
    of possible items who are accessible under their field name respectively.

    Due to the implementation `typename` as well as all `field_names` have to
    be valid python identifiers also the names used in `field_names` may not
    repeat themselves.

    You can solve the latter issue for `field_names` by passing ``rename=True``,
    any given name which is either a keyword or a repetition is then replaced
    with `_n` where `n` is an integer increasing with every rename starting by
    1.

    :func:`namedtuple` creates the code for the subclass and executes it
    internally you can view that code by passing ``verbose==True``, which will
    print the code.

    Unlike :class:`tuple` a named tuple provides several methods as helpers:

    .. class:: SomeNamedTuple(foo, bar)

       .. classmethod:: _make(iterable)

          Returns a :class:`SomeNamedTuple` populated with the items from the
          given `iterable`.

       .. method:: _asdict()

          Returns a :class:`dict` mapping the field names to their values.

       .. method:: _replace(**kwargs)

          Returns a :class:`SomeNamedTuple` values replaced with the given
          ones::

              >>> t = SomeNamedTuple(1, 2)
              >>> t._replace(bar=3)
              SomeNamedTuple(foo=1, bar=3)
              # doctest: DEACTIVATE

    .. note::
       :func:`namedtuple` is compatible with :func:`collections.namedtuple`.

    .. versionadded:: 0.5
    """
    def name_generator():
        for i in count(1):
            yield '_%d' % i
    make_name = name_generator().next

    if iskeyword(typename):
        raise ValueError('the given typename is a keyword: %s' % typename)
    if isinstance(field_names, basestring):
        field_names = field_names.replace(',', ' ').split()
    real_field_names = []
    seen_names = set()
    for name in field_names:
        if iskeyword(name):
            if rename:
                name = make_name()
            else:
                raise ValueError('a given field name is a keyword: %s' % name)
        elif name in seen_names:
            if rename:
                name = make_name()
            else:
                raise ValueError('a field name has been repeated: %s' % name)
        real_field_names.append(name)
        seen_names.add(name)

    code = textwrap.dedent("""
        from operator import itemgetter

        class %(typename)s(tuple):
            '''%(docstring)s'''

            _fields = %(fields)s

            @classmethod
            def _make(cls, iterable):
                result = tuple.__new__(cls, iterable)
                if len(result) > %(field_count)d:
                    raise TypeError(
                        'expected %(field_count)d arguments, got %%d' %% len(result)
                    )
                return result

            def __new__(cls, %(fieldnames)s):
                return tuple.__new__(cls, (%(fieldnames)s))

            def _asdict(self):
                return dict(zip(self._fields, self))

            def _replace(self, **kwargs):
                result = self._make(map(kwargs.pop, %(fields)s, self))
                if kwargs:
                    raise ValueError(
                        'got unexpected arguments: %%r' %% kwargs.keys()
                    )
                return result

            def __getnewargs__(self):
                return tuple(self)

            def __repr__(self):
                return '%(typename)s(%(reprtext)s)' %% self
    """) % {
        'typename': typename,
        'fields': repr(tuple(real_field_names)),
        'fieldnames': ', '.join(real_field_names),
        'field_count': len(real_field_names),
        'reprtext': ', '.join(name + '=%r' for name in real_field_names),
        'docstring': doc or typename + '(%s)' % ', '.join(real_field_names)
    }

    for i, name in enumerate(real_field_names):
        code += '    %s = property(itemgetter(%d))\n' % (name, i)

    if verbose:
        print code

    namespace = {}
    # there should never occur an exception here but if one does I'd rather
    # have the source to see what is going on
    try:
        exec code in namespace
    except SyntaxError, e: # pragma: no cover
        raise SyntaxError(e.args[0] + ':\n' + code)
    result = namespace[typename]

    return result


__all__ = ['LazyList', 'CombinedSequence', 'CombinedList', 'namedtuple']

########NEW FILE########
__FILENAME__ = sets
# coding: utf-8
"""
    brownie.datastructures.sets
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~

    :copyright: 2010-2011 by Daniel Neuhäuser
    :license: BSD, see LICENSE.rst for details
"""
from functools import wraps

from brownie.itools import chain
from brownie.datastructures.mappings import OrderedDict


class OrderedSet(object):
    """
    A :class:`set` which remembers insertion order.

    .. versionadded:: 0.2
    """
    def requires_set(func):
        @wraps(func)
        def wrapper(self, other):
            if isinstance(other, (self.__class__, set, frozenset)):
                return func(self, other)
            return NotImplemented
        return wrapper

    def __init__(self, iterable=None):
        self._orderedmap = OrderedDict.fromkeys(iterable or ())

    def __len__(self):
        return len(self._orderedmap)

    def __contains__(self, element):
        return element in self._orderedmap

    def add(self, element):
        self._orderedmap[element] = None

    def remove(self, element):
        del self._orderedmap[element]

    def discard(self, element):
        self._orderedmap.pop(element, None)

    def pop(self, last=True):
        """
        Returns the last element if `last` is ``True``, the first otherwise.
        """
        if not self:
            raise KeyError('set is empty')
        element = self._orderedmap.popitem(last=last)[0]
        return element

    def clear(self):
        self._orderedmap.clear()

    def update(self, *others):
        for other in others:
            for element in other:
                self._orderedmap[element] = None

    def copy(self):
        return self.__class__(self)

    @requires_set
    def __ior__(self, other):
        self.update(other)
        return self

    def issubset(self, other):
        return all(element in other for element in self)

    @requires_set
    def __le__(self, other):
        return self.issubset(other)

    @requires_set
    def __lt__(self, other):
        return self.issubset(other) and self != other

    def issuperset(self, other):
        return all(element in self for element in other)

    @requires_set
    def __ge__(self, other):
        return self.issuperset(other)

    @requires_set
    def __gt__(self, other):
        return self.issuperset(other) and self != other

    def union(self, *others):
        return self.__class__(chain.from_iterable((self, ) + others))

    @requires_set
    def __or__(self, other):
        return self.union(other)

    def intersection(self, *others):
        def intersect(a, b):
            result = self.__class__()
            smallest = min([a, b], key=len)
            for element in max([a, b], key=len):
                if element in smallest:
                    result.add(element)
            return result
        return reduce(intersect, others, self)

    @requires_set
    def __and__(self, other):
        return self.intersection(other)

    @requires_set
    def __iand__(self, other):
        intersection = self.intersection(other)
        self.clear()
        self.update(intersection)
        return self

    def difference(self, *others):
        return self.__class__(
            key for key in self if not any(key in s for s in others)
        )

    @requires_set
    def __sub__(self, other):
        return self.difference(other)

    @requires_set
    def __isub__(self, other):
        diff = self.difference(other)
        self.clear()
        self.update(diff)
        return self

    def symmetric_difference(self, other):
        other = self.__class__(other)
        return self.__class__(chain(self - other, other - self))

    @requires_set
    def __xor__(self, other):
        return self.symmetric_difference(other)

    @requires_set
    def __ixor__(self, other):
        diff = self.symmetric_difference(other)
        self.clear()
        self.update(diff)
        return self

    def __iter__(self):
        return iter(self._orderedmap)

    def __reversed__(self):
        return reversed(self._orderedmap)

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return len(self) == len(other) and list(self) == list(other)
        return set(self) == other

    def __ne__(self, other):
        return not self.__eq__(other)

    __hash__ = None

    def __repr__(self):
        content = repr(list(self)) if self else ''
        return '%s(%s)' % (self.__class__.__name__, content)

    del requires_set


__all__ = ['OrderedSet']

########NEW FILE########
__FILENAME__ = functional
# coding: utf-8
"""
    brownie.functional
    ~~~~~~~~~~~~~~~~~~

    Implements functions known from functional programming languages and other
    things which are useful when dealing with functions.

    :copyright: 2010-2011 by Daniel Neuhäuser
    :license: BSD, see LICENSE.rst for details
"""
from inspect import getargspec
from functools import wraps

from brownie.itools import izip_longest, unique
from brownie.datastructures import namedtuple, FixedDict


def compose(*functions):
    """
    Returns a function which acts as a composition of several `functions`. If
    one function is given it is returned if no function is given a
    :exc:`TypeError` is raised.

    >>> from brownie.functional import compose
    >>> compose(lambda x: x + 1, lambda x: x * 2)(1)
    3

    .. note:: Each function (except the last one) has to take the result of the
              last function as argument.
    """
    if not functions:
        raise TypeError('expected at least 1 argument, got 0')
    elif len(functions) == 1:
        return functions[0]
    return reduce(lambda f, g: lambda *a, **kws: f(g(*a, **kws)), functions)


def flip(function):
    """
    Returns a function which behaves like `function` but gets the given
    positional arguments reversed; keyword arguments are passed through.

    >>> from brownie.functional import flip
    >>> def f(a, b): return a
    >>> f(1, 2)
    1
    >>> flip(f)(1, 2)
    2
    """
    @wraps(function)
    def wrap(*args, **kwargs):
        return function(*reversed(args), **kwargs)
    return wrap


class Signature(namedtuple('SignatureBase', [
            'positionals', 'kwparams', 'varargs', 'varkwargs'
        ])):
    """
    A named tuple representing a function signature.

    :param positionals:
       A list of required positional parameters.

    :param kwparams:
       A list containing the keyword arguments, each as a tuple containing the
       name and default value, in order of their appearance in the function
       definition.

    :param varargs:
       The name used for arbitrary positional arguments or `None`.

    :param varkwargs:
       The name used for arbitary keyword arguments or `None`.

    .. warning::
       The size of :class:`Signature` tuples may change in the future to
       accommodate additional information like annotations. Therefore you
       should not rely on it.

    .. versionadded:: 0.5
    """
    @classmethod
    def from_function(cls, func):
        """
        Constructs a :class:`Signature` from the given function or method.
        """
        func = getattr(func, 'im_func', func)
        params, varargs, varkwargs, defaults = getargspec(func)
        defaults = [] if defaults is None else defaults
        return cls(
            params[
                :0 if len(defaults) == len(params)
                else -len(defaults) or len(params)
            ],
            zip(params[-len(defaults):], defaults),
            varargs,
            varkwargs
        )

    def bind_arguments(self, args=(), kwargs=None):
        """
        Returns a dictionary with the names of the parameters as keys with
        their arguments as values.

        Raises a :exc:`ValueError` if there are too many `args` and/or `kwargs`
        that are missing or repeated.
        """
        kwargs = {} if kwargs is None else kwargs

        required = set(self.positionals)
        overwritable = set(name for name, default in self.kwparams)
        settable = required | overwritable

        positional_count = len(self.positionals)
        kwparam_count = len(self.kwparams)

        result = dict(self.kwparams, **dict(zip(self.positionals, args)))

        remaining = args[positional_count:]
        for (param, _), arg in zip(self.kwparams, remaining):
            result[param] = arg
            overwritable.discard(param)
        if len(remaining) > kwparam_count:
            if self.varargs is None:
                raise ValueError(
                    'expected at most %d positional arguments, got %d' % (
                        positional_count + kwparam_count,
                        len(args)
                    )
                )
            else:
                result[self.varargs] = tuple(remaining[kwparam_count:])

        remaining = {}
        unexpected = []
        for key, value in kwargs.iteritems():
            if key in result and key not in overwritable:
                raise ValueError("got multiple values for '%s'" % key)
            elif key in settable:
                result[key] = value
            elif self.varkwargs:
                result_kwargs = result.setdefault(self.varkwargs, {})
                result_kwargs[key] = value
            else:
                unexpected.append(key)
        if len(unexpected) == 1:
            raise ValueError(
                "got unexpected keyword argument '%s'" % unexpected[0]
            )
        elif len(unexpected) == 2:
            raise ValueError(
                "got unexpected keyword arguments '%s' and '%s'" % tuple(unexpected)
            )
        elif unexpected:
            raise ValueError("got unexpected keyword arguments %s and '%s'" % (
                ', '.join("'%s'" % arg for arg in unexpected[:-1]), unexpected[-1]
            ))

        if set(result) < set(self.positionals):
            missing = set(result) ^ set(self.positionals)
            if len(missing) == 1:
                raise ValueError("'%s' is missing" % missing.pop())
            elif len(missing) == 2:
                raise ValueError("'%s' and '%s' are missing" % tuple(missing))
            else:
                missing = tuple(missing)
                raise ValueError("%s and '%s' are missing" % (
                    ', '.join("'%s'" % name for name in missing[:-1]), missing[-1]
                ))
        if self.varargs:
            result.setdefault(self.varargs, ())
        if self.varkwargs:
            result.setdefault(self.varkwargs, {})
        return result


class curried(object):
    """
    :class:`curried` is a decorator providing currying for callable objects.

    Each call to the curried callable returns a new curried object unless it
    is called with every argument required for a 'successful' call to the
    function::

        >>> foo = curried(lambda a, b, c: a + b * c)
        >>> foo(1, 2, 3)
        6
        >>> bar = foo(c=2)
        >>> bar(2, 3)
        8
        >>> baz = bar(3)
        >>> baz(3)
        9

    By the way if the function takes arbitrary positional and/or keyword
    arguments this will work as expected.

    .. versionadded:: 0.5
    """
    def __init__(self, function):
        self.function = function

        self.signature = Signature.from_function(function)
        self.params = self.signature.positionals + [
            name for name, default in self.signature.kwparams
        ]
        self.args = {}
        self.changeable_args = set(
            name for name, default in self.signature.kwparams
        )

    @property
    def remaining_params(self):
        return unique(self.params, set(self.args) - self.changeable_args)

    def _updated(self, args):
        result = object.__new__(self.__class__)
        result.__dict__.update(self.__dict__)
        result.args = args
        return result

    def __call__(self, *args, **kwargs):
        collected_args = self.args.copy()
        for remaining, arg in izip_longest(self.remaining_params, args):
            if remaining is None:
                if self.signature.varargs is None:
                    raise TypeError('unexpected positional argument: %r' % arg)
                collected_args.setdefault(self.signature.varargs, []).append(arg)
            elif arg is None:
                break
            else:
                collected_args[remaining] = arg
                self.changeable_args.discard(remaining)
        for key, value in kwargs.iteritems():
            if key in self.params:
                if key in collected_args:
                    raise TypeError("'%s' has been repeated: %r" % (key, value))
                self.changeable_args.discard(key)
                collected_args[key] = value
            else:
                if self.signature.varkwargs is None:
                    raise TypeError(
                        '%s is an unexpected keyword argument: %r' % (
                            key, value
                        )
                    )
                else:
                    collected_args.setdefault(
                        self.signature.varkwargs,
                        FixedDict()
                    )[key] = value
        if set(self.signature.positionals) <= set(collected_args):
            func_kwargs = dict(self.signature.kwparams)
            func_kwargs = FixedDict(self.signature.kwparams, **collected_args)
            func_kwargs.update(func_kwargs.pop(self.signature.varkwargs, {}))
            args = map(func_kwargs.pop, self.params)
            args += func_kwargs.pop(self.signature.varargs, [])
            return self.function(*args, **func_kwargs)
        return self._updated(collected_args)


def fmap(obj, functions):
    """
    Returns a generator yielding `function(obj)` for each function in
    `functions`.

    `functions` may contain iterables of functions instead of functions which
    will be composed and called with `obj`.

    .. versionadded:: 0.6
    """
    for function in functions:
        try:
            iter(function)
        except TypeError:
            yield function(obj)
        else:
            yield compose(*function)(obj)


__all__ = ['compose', 'flip', 'Signature', 'curried', 'fmap']

########NEW FILE########
__FILENAME__ = importing
# coding: utf-8
"""
    brownie.importing
    ~~~~~~~~~~~~~~~~~

    .. versionadded:: 0.2

    :copyright: 2010-2011 by Daniel Neuhäuser
    :license: BSD, see LICENSE.rst for details
"""
import re

_identifier_re = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')


def _raise_identifier(identifier):
    if _identifier_re.match(identifier) is None:
        raise ValueError('invalid identifier: %s' % identifier)


def import_string(name):
    """
    Imports and returns an object given its `name` as a string.

    As an addition to the normal way import paths are specified you can use
    a colon to delimit the object you want to import.

    If the given name is invalid a :exc:`ValueError` is raised, if the module
    cannot be imported an :exc:`ImportError`.

    Beware of the fact that in order to import a module it is executed and
    therefore any exception could be raised, especially when dealing with
    third party code e.g. if you implement a plugin system.
    """
    if ':' in name:
        module, obj = name.split(':', 1)
    elif '.' in name:
        module, obj = name.rsplit('.', 1)
    else:
        _raise_identifier(name)
        return __import__(name)
    for identifier in module.split('.') + [obj]:
        _raise_identifier(identifier)
    return getattr(
        __import__(module, globals=None, locals=None, fromlist=[obj]),
        obj
    )


__all__ = ['import_string']

########NEW FILE########
__FILENAME__ = itools
# coding: utf-8
"""
    brownie.itools
    ~~~~~~~~~~~~~~

    Implements :mod:`itertools` functions for earlier version of Python.

    :copyright: 2010-2011 by Daniel Neuhäuser
    :license: BSD, PSF see LICENSE.rst for details
"""
from itertools import repeat, izip


class chain(object):
    """
    An iterator which yields elements from the given `iterables` until each
    iterable is exhausted.

    .. versionadded:: 0.2
    """
    @classmethod
    def from_iterable(cls, iterable):
        """
        Alternative constructor which takes an `iterable` yielding iterators,
        this can be used to chain an infinite number of iterators.
        """
        rv = object.__new__(cls)
        rv._init(iterable)
        return rv

    def __init__(self, *iterables):
        self._init(iterables)

    def _init(self, iterables):
        self.iterables = iter(iterables)
        self.current_iterable = iter([])

    def __iter__(self):
        return self

    def next(self):
        try:
            return self.current_iterable.next()
        except StopIteration:
            self.current_iterable = iter(self.iterables.next())
            return self.current_iterable.next()


def izip_longest(*iterables, **kwargs):
    """
    Make an iterator that aggregates elements from each of the iterables. If
    the iterables are of uneven length, missing values are filled-in with
    `fillvalue`. Iteration continues until the longest iterable is exhausted.

    If one of the iterables is potentially infinite, then the
    :func:`izip_longest` function should be wrapped with something that limits
    the number of calls (for example :func:`itertools.islice` or
    :func:`itertools.takewhile`.) If not specified, `fillvalue` defaults to
    ``None``.

    .. note:: Software and documentation for this function are taken from
              CPython, :ref:`license details <psf-license>`.
    """
    fillvalue = kwargs.get('fillvalue')
    def sentinel(counter=([fillvalue] * (len(iterables) - 1)).pop):
        yield counter()
    fillers = repeat(fillvalue)
    iters = [chain(it, sentinel(), fillers) for it in iterables]
    try:
        for tup in izip(*iters):
            yield tup
    except IndexError:
        pass


def permutations(iterable, r=None):
    """
    Return successive `r` length permutations of elements in the `iterable`.

    If `r` is not specified or is ``None``, then `r` defaults to the length of
    the `iterable` and all possible full-length permutations are generated.

    Permutations are emitted in lexicographic sort order. So, if the input
    `iterable` is sorted, the permutation tuples will be produced in sorted
    order.

    Elements are treated as unique based on their position, not on their
    value. So if the input elements are unique, there will be no repeating
    value in each permutation.

    The number of items returned is ``n! / (n - r)!`` when ``0 <= r <= n`` or
    zero when `r > n`.

    .. note:: Software and documentation for this function are taken from
              CPython, :ref:`license details <psf-license>`.
    """
    pool = tuple(iterable)
    n = len(pool)
    r = n if r is None else r
    for indices in product(range(n), repeat=r):
        if len(set(indices)) == r:
            yield tuple(pool[i] for i in indices)


def product(*iterables, **kwargs):
    """
    Cartesian product of input iterables.

    Equivalent to nested for-loops in a generator expression. For example,
    ``product(A, B)`` returns the same as ``((x, y) for x in A for y in B)``.

    The nested loops cycle like an odometer with the rightmost element
    advancing on every iteration. The pattern creates a lexicographic ordering
    so that if the input's iterables are sorted, the product tuples are emitted
    in sorted order.

    To compute the product of an iterable with itself, specify the number of
    repetitions with the optional `repeat` keyword argument. For example,
    ``product(A, repeat=4)`` means the same as ``product(A, A, A, A)``.

    .. note:: Software and documentation for this function are taken from
              CPython, :ref:`license details <psf-license>`.
    """
    pools = map(tuple, iterables) * kwargs.get('repeat', 1)
    result = [[]]
    for pool in pools:
        result = [x + [y] for x in result for y in pool]
    for prod in result:
        yield tuple(prod)


def starmap(function, iterable):
    """
    Make an iterator that computes the function using arguments obtained from
    the iterable. Used instead of :func:`itertools.imap` when an argument
    parameters are already grouped in tuples from a single iterable (the data
    has been "pre-zipped"). The difference between :func:`itertools.imap` and
    :func:`starmap` parallels the distinction between ``function(a, b)`` and
    ``function(*c)``.

    .. note:: Software and documentation for this function are taken from
              CPython, :ref:`license details <psf-license>`.
    """
    for args in iterable:
        yield function(*args)


def combinations_with_replacement(iterable, r):
    """
    Return `r` length sub-sequences of elements from the `iterable` allowing
    individual elements to be replaced more than once.

    Combinations are emitted in lexicographic sort order. So, if the input
    `iterable` is sorted, the combinations tuples will be produced in sorted
    order.

    Elements are treated as unique based on their position, not on their value.
    So if the input elements are unique, the generated combinations will also
    be unique.

    The number of items returned is ``(n + r - 1)! / r! / (n - 1)!`` when
    ``n > 0``.

    .. note:: Software and documentation for this function are taken from
              CPython, :ref:`license details <psf-license>`.
    """
    pool = tuple(iterable)
    n = len(pool)
    for indices in product(xrange(n), repeat=r):
        if sorted(indices) == list(indices):
            yield tuple(pool[i] for i in indices)


def compress(data, selectors):
    """
    Make an iterator that filters elements from the `data` returning only
    those that have a corresponding element in `selectors` that evaluates to
    ``True``. Stops when either the `data` or `selectors` iterables have been
    exhausted.

    .. note:: Software and documentation for this function are taken from
              CPython, :ref:`license details <psf-license>`.
    """
    return (d for d, s in izip(data, selectors) if s)


def count(start=0, step=1):
    """
    Make an iterator that returns evenly spaced values starting with `start`.
    Often used as an argument to :func:`imap` to generate consecutive data
    points. Also, used with :func:`izip` to add sequence numbers.

    When counting with floating point numbers, better accuracy can sometimes
    be achieved by substituting multiplicative code such as:
    ``(start + step * i for i in count())``.

    .. note:: Software and documentation for this function are taken from
              CPython, :ref:`license details <psf-license>`.
    """
    n = start
    while True:
        yield n
        n += step


def grouped(n, iterable, fillvalue=None):
    """
    Groups the items in the given `iterable` to tuples of size `n`. In order
    for groups to always be of the size `n` the `fillvalue` is used for
    padding.
    """
    return izip_longest(fillvalue=fillvalue, *([iter(iterable)] * n))


def unique(iterable, seen=None):
    """
    Yields items from the given `iterable` of (hashable) items, once seen an
    item is not yielded again.

    :param seen:
       An iterable specifying already 'seen' items which will be excluded
       from the result.

       .. versionadded:: 0.5

    .. versionchanged:: 0.5
       Items don't have to be hashable any more.
    """
    seen = set() if seen is None else set(seen)
    seen_unhashable = []
    for item in iterable:
        try:
            if item not in seen:
                seen.add(item)
                yield item
        except TypeError:
            if item not in seen_unhashable:
                seen_unhashable.append(item)
                yield item


def flatten(iterable, ignore=(basestring, )):
    """
    Flattens a nested `iterable`.

    :param ignore:
        Types of iterable objects which should be yielded as-is.

    .. versionadded:: 0.5
    """
    stack = [iter(iterable)]
    while stack:
        try:
            item = stack[-1].next()
            if isinstance(item, ignore):
                yield item
            elif isinstance(item, basestring) and len(item) == 1:
                yield item
            else:
                try:
                    stack.append(iter(item))
                except TypeError:
                    yield item
        except StopIteration:
            stack.pop()


__all__ = [
    'chain', 'izip_longest', 'permutations', 'product', 'starmap',
    'combinations_with_replacement', 'compress', 'count', 'grouped', 'unique',
    'flatten'
]

########NEW FILE########
__FILENAME__ = parallel
# coding: utf-8
"""
    brownie.parallel
    ~~~~~~~~~~~~~~~~

    Implements useful parallelization stuff.

    :copyright: 2010-2011 by Daniel Neuhaeuser
    :license: BSD, see LICENSE.rst for details
"""
from __future__ import with_statement
import os
import sys
from threading import Condition, Lock

try:
    from multiprocessing import _get_cpu_count

    def get_cpu_count(default=None):
        try:
            return _get_cpu_count()
        except NotImplementedError:
            if default is None:
                raise
            return default

except ImportError:
    def get_cpu_count(default=None):
        if sys.platform == 'win32':
            try:
                return int(os.environ['NUMBER_OF_PROCESSORS'])
            except (ValueError, KeyError):
                # value could be anything or not existing
                pass
        if sys.platform in ('bsd', 'darwin'):
            try:
                return int(os.popen('sysctl -n hw.ncpu').read())
            except ValueError:
                # don't trust the outside world
                pass
        try:
            cpu_count = os.sysconf('SC_NPROCESSORS_ONLN')
            if cpu_count >= 1:
                return cpu_count
        except (AttributeError, ValueError):
            # availability is restricted to unix
            pass
        if default is not None:
            return default
        raise NotImplementedError()

get_cpu_count.__doc__ = """
Returns the number of available processors on this machine.

If default is ``None`` and the number cannot be determined a
:exc:`NotImplementedError` is raised.
"""


class TimeoutError(Exception):
    """Exception raised in case of timeouts."""


class AsyncResult(object):
    """
    Helper object for providing asynchronous results.

    :param callback:
        Callback which is called if the result is a success.

    :param errback:
        Errback which is called if the result is an exception.
    """
    def __init__(self, callback=None, errback=None):
        self.callback = callback
        self.errback = errback

        self.condition = Condition(Lock())
        #: ``True`` if a result is available.
        self.ready = False

    def wait(self, timeout=None):
        """
        Blocks until the result is available or the given `timeout` has been
        reached.
        """
        with self.condition:
            if not self.ready:
                self.condition.wait(timeout)

    def get(self, timeout=None):
        """
        Returns the result or raises the exception which has been set, if
        the result is not available this method is blocking.

        If `timeout` is given this method raises a :exc:`TimeoutError`
        if the result is not available soon enough.
        """
        self.wait(timeout)
        if not self.ready:
            raise TimeoutError(timeout)
        if self.success:
            return self.value
        else:
            raise self.value

    def set(self, obj, success=True):
        """
        Sets the given `obj` as result, set `success` to ``False`` if `obj`
        is an exception.
        """
        self.value = obj
        self.success = success
        if self.callback and success:
            self.callback(obj)
        if self.errback and not success:
            self.errback(obj)
        with self.condition:
            self.ready = True
            self.condition.notify()

    def __repr__(self):
        parts = []
        if self.callback is not None:
            parts.append(('callback', self.callback))
        if self.errback is not None:
            parts.append(('errback', self.errback))
        return '%s(%s)' % (
            self.__class__.__name__,
            ', '.join('%s=%r' % part for part in parts)
        )


__all__ = ['get_cpu_count', 'TimeoutError', 'AsyncResult']

########NEW FILE########
__FILENAME__ = proxies
# coding: utf-8
"""
    brownie.proxies
    ~~~~~~~~~~~~~~~

    :copyright: 2010-2011 by Daniel Neuhäuser
    :license: BSD, see LICENSE for details
"""
import textwrap

from brownie.datastructures import missing


SIMPLE_CONVERSION_METHODS = {
    '__str__':     str,
    '__unicode__': unicode,
    '__complex__': complex,
    '__int__':     int,
    '__long__':    long,
    '__float__':   float,
    '__oct__':     oct,
    '__hex__':     hex,
    '__nonzero__': bool
}


CONVERSION_METHODS = set(SIMPLE_CONVERSION_METHODS) | frozenset([
    '__index__',   # slicing, operator.index()
    '__coerce__',  # mixed-mode numeric arithmetic
])


COMPARISON_METHODS = {
    '__lt__': '<',
    '__le__': '<=',
    '__eq__': '==',
    '__ne__': '!=',
    '__gt__': '>',
    '__ge__': '>='
}


DESCRIPTOR_METHODS = frozenset([
    '__get__',
    '__set__',
    '__delete__',
])


REGULAR_BINARY_ARITHMETIC_METHODS = frozenset([
    '__add__',
    '__sub__',
    '__mul__',
    '__div__',
    '__truediv__',
    '__floordiv__',
    '__mod__',
    '__divmod__',
    '__pow__',
    '__lshift__',
    '__rshift__',
    '__and__',
    '__xor__',
    '__or__',
])


REVERSED_ARITHMETIC_METHODS = frozenset([
    '__radd__',
    '__rsub__',
    '__rmul__',
    '__rdiv__',
    '__rtruediv__',
    '__rfloordiv__',
    '__rmod__',
    '__rdivmod__',
    '__rpow__',
    '__rlshift__',
    '__rrshift__',
    '__rand__',
    '__rxor__',
    '__ror__',
])


AUGMENTED_ASSIGNMENT_METHODS = frozenset([
    '__iadd__',
    '__isub__',
    '__imul__',
    '__idiv__',
    '__itruediv__'
    '__ifloordiv__',
    '__imod__',
    '__ipow__',
    '__ipow__',
    '__ilshift__',
    '__rlshift__',
    '__iand__',
    '__ixor__',
    '__ior__',
])


BINARY_ARITHMETHIC_METHODS = (
    REGULAR_BINARY_ARITHMETIC_METHODS |
    REVERSED_ARITHMETIC_METHODS |
    AUGMENTED_ASSIGNMENT_METHODS
)


UNARY_ARITHMETHIC_METHODS = frozenset([
    '__neg__',   # -
    '__pos__',   # +
    '__abs__',   # abs()
    '__invert__' # ~
])

SIMPLE_CONTAINER_METHODS = {
    '__len__': len,
    '__iter__': iter,
    '__reversed__': reversed
}


CONTAINER_METHODS = frozenset(SIMPLE_CONTAINER_METHODS) | frozenset([
    '__getitem__',  # ...[]
    '__setitem__',  # ...[] = ...
    '__delitem__',  # del ...[]
    '__contains__'  # ... in ...
])


SLICING_METHODS = frozenset([
    '__getslice__',
    '__setslice__',
    '__delslice__',
])


TYPECHECK_METHODS = frozenset([
    '__instancecheck__', # isinstance()
    '__issubclass__',    # issubclass()
])


CONTEXT_MANAGER_METHODS = frozenset([
    '__enter__',
    '__exit__'
])


UNGROUPABLE_METHODS = frozenset([
    # special comparison
    '__cmp__', # cmp()

    # hashability, required if ==/!= are implemented
    '__hash__', # hash()

    '__call__', # ...()
])


#: All special methods with exception of :meth:`__new__` and :meth:`__init__`.
SPECIAL_METHODS = (
    CONVERSION_METHODS |
    set(COMPARISON_METHODS) |
    DESCRIPTOR_METHODS |
    BINARY_ARITHMETHIC_METHODS |
    UNARY_ARITHMETHIC_METHODS |
    CONTAINER_METHODS |
    SLICING_METHODS |
    TYPECHECK_METHODS |
    CONTEXT_MANAGER_METHODS |
    UNGROUPABLE_METHODS
)


SIMPLE_METHODS = {}
SIMPLE_METHODS.update(SIMPLE_CONVERSION_METHODS)
SIMPLE_METHODS.update(SIMPLE_CONTAINER_METHODS)


class ProxyMeta(type):
    def _set_private(self, name, obj):
        setattr(self, '_ProxyBase__' + name, obj)

    def method(self, handler):
        self._set_private('method_handler', handler)

    def getattr(self, handler):
        self._set_private('getattr_handler', handler)

    def setattr(self, handler):
        self._set_private('setattr_handler', handler)

    def repr(self, repr_handler):
        self._set_private('repr_handler', repr_handler)


class ProxyBase(object):
    def __init__(self, proxied):
        self.__proxied = proxied

    def __force(self, proxied):
        return self.__proxied

    def __method_handler(self, proxied, name, get_result, *args, **kwargs):
        return missing

    def __getattr_handler(self, proxied, name):
        return getattr(proxied, name)

    def __setattr_handler(self, proxied, name, obj):
        return setattr(proxied, name, obj)

    def __repr_handler(self, proxied):
        return repr(proxied)

    def __dir__(self):
        return dir(self.__proxied)

    def __getattribute__(self, name):
        if name.startswith('_ProxyBase__'):
            return object.__getattribute__(self, name)
        return self.__getattr_handler(self.__proxied, name)

    def __setattr__(self, name, obj):
        if name.startswith('_ProxyBase__'):
            return object.__setattr__(self, name, obj)
        return self.__setattr_handler(self.__proxied, name, obj)

    def __repr__(self):
        return self.__repr_handler(self.__proxied)

    # the special methods we implemented so far (for special cases)
    implemented = set()

    def __contains__(self, other):
        def get_result(proxied, other):
            return other in proxied
        result = self.__method_handler(self.__proxied, '__contains__',
                                       get_result, other)
        if result is missing:
            return get_result(self.__proxied, other)
        return result
    implemented.add('__contains__')

    def __getslice__(self, i, j):
        def get_result(proxied, i, j):
            return proxied[i:j]
        result = self.__method_handler(self.__proxied, '__getslice__',
                                       get_result, i, j)
        if result is missing:
            return get_result(self.__proxied, i, j)
        return result
    implemented.add('__getslice__')

    def __setslice__(self, i, j, value):
        def get_result(proxied, i, j, value):
            proxied[i:j] = value
        result = self.__method_handler(
            self.__proxied, '__setslice__', get_result, i, j, value
        )
        if result is missing:
            return get_result(self.__proxied, i, j, value)
        return result
    implemented.add('__setslice__')

    def __delslice__(self, i, j):
        def get_result(proxied, i, j):
            del proxied[i:j]
        result = self.__method_handler(
            self.__proxied, '__delslice__', get_result, i, j
        )
        if result is missing:
            return get_result(self.__proxied, i, j)
        return result
    implemented.add('__delslice__')

    # simple methods such as __complex__ are not necessarily defined like
    # other special methods, especially for built-in types by using the
    # built-in functions we achieve the desired behaviour.
    method_template = textwrap.dedent("""
        def %(name)s(self):
            def get_result(proxied):
                return %(func)s(proxied)
            result = self._ProxyBase__method_handler(
                self._ProxyBase__proxied, '%(name)s', get_result
            )
            if result is missing:
                return get_result(self._ProxyBase__proxied)
            return result
    """)
    for method, function in SIMPLE_METHODS.items():
        exec(method_template % dict(name=method, func=function.__name__))
    implemented.update(SIMPLE_METHODS)
    del function

    # we need to special case comparison methods due to the fact that
    # if we implement __lt__ and call it on the proxied object it might fail
    # because the proxied object implements __cmp__ instead.
    method_template = textwrap.dedent("""
        def %(name)s(self, other):
            def get_result(proxied, other):
                return proxied %(operator)s other
            result = self._ProxyBase__method_handler(
                self._ProxyBase__proxied, '%(name)s', get_result, other
            )
            if result is missing:
                return get_result(self._ProxyBase__proxied, other)
            return result
    """)

    for method, operator in COMPARISON_METHODS.items():
        exec(method_template % dict(name=method, operator=operator))
    implemented.update(COMPARISON_METHODS)
    del operator

    method_template = textwrap.dedent("""
        def %(name)s(self, *args, **kwargs):
            def get_result(proxied, *args, **kwargs):
                other = args[0]
                if type(self) is type(other):
                    other = other._ProxyBase__force(other._ProxyBase__proxied)
                return proxied.%(name)s(
                    *((other, ) + args[1:]), **kwargs
                )

            result = self._ProxyBase__method_handler(
                self._ProxyBase__proxied,
                '%(name)s',
                get_result,
                *args,
                **kwargs
            )
            if result is missing:
                return get_result(self._ProxyBase__proxied, *args, **kwargs)
            return result
    """)
    for method in BINARY_ARITHMETHIC_METHODS:
        exec(method_template % dict(name=method))
    implemented.update(BINARY_ARITHMETHIC_METHODS)

    method_template = textwrap.dedent("""
        def %(name)s(self, *args, **kwargs):
            def get_result(proxied, *args, **kwargs):
                return proxied.%(name)s(*args, **kwargs)
            result = self._ProxyBase__method_handler(
                self._ProxyBase__proxied, '%(name)s', get_result, *args, **kwargs
            )
            if result is missing:
                return get_result(self._ProxyBase__proxied, *args, **kwargs)
            return result
    """)
    for method in SPECIAL_METHODS - implemented:
        method = method_template % dict(name=method)
        exec(method)
    del method_template, method, implemented


def as_proxy(cls):
    '''
    Class decorator which returns a proxy based on the handlers defined in the
    given class defined as methods::

        @as_proxy
        class MyProxy(object):
            """
            This is an example proxy, every method defined is optional.
            """
            def method(self, proxied, name, get_result, *args, **kwargs):
                """
                Gets called when a special method is called on the proxy

                :param proxied:
                    The object wrapped by the proxy.

                :param name:
                    The name of the called method.

                :param get_result:
                    A function which takes `proxied`, `*args` and `**kwargs`
                    as arguments and returns the appropriate result for the
                    called method.

                :param \*args:
                    The positional arguments passed to the method.

                :param \*\*kwargs:
                    The keyword arguments passed to the method.
                """
                return missing

            def getattr(self, proxied, name):
                """
                Gets called when a 'regular' attribute is accessed.

                :param name:
                    The name of the attribute.
                """
                return getattr(proxied, name)

            def setattr(self, proxied, name, obj):
                """
                Gets called when a 'regular' attribute is set.

                :param obj:
                    The object which is set as attribute.
                """
                setattr(proxied, name, obj)

            def force(self, proxied):
                """
                Returns a 'real' version of `proxied`. This is required when
                `proxied` is something abstract like a function which returns
                an object like which the proxy is supposed to behave.

                Internally this is used when a binary operator is used with the
                proxy on the left side. Built-in types complain if we call the
                special method with the proxy given on the right side of the
                operator, therefore the proxy on the right side is 'forced'.
                """
                return proxied

            def repr(self, proxied):
                """
                Gets called for the representation of the proxy.
                """
                return repr(proxied)

        foo = MyProxy(1)
    '''
    attributes = {
        '__module__': cls.__module__,
        '__doc__': cls.__doc__
    }

    handler_name_mapping = {
        'method': '_ProxyBase__method_handler',
        'getattr': '_ProxyBase__getattr_handler',
        'setattr': '_ProxyBase__setattr_handler',
        'force': '_ProxyBase__force',
        'repr': '_ProxyBase__repr_handler'
    }

    for name, internal_name in handler_name_mapping.iteritems():
        handler = getattr(cls, name, None)
        if handler is not None:
            attributes[internal_name] = handler.im_func

    return ProxyMeta(cls.__name__, (ProxyBase, ), attributes)


def get_wrapped(proxy):
    """
    Returns the item wrapped by a given `proxy` whereas `proxy` is an instance
    of a class as returned by :func:`as_proxy`.
    """
    return proxy._ProxyBase__proxied


class LazyProxy(object):
    """
    Takes a callable and calls it every time this proxy is accessed to get an
    object which is then wrapped by this proxy::

        >>> from datetime import datetime

        >>> now = LazyProxy(datetime.utcnow)
        >>> now.second != now.second
        True
    """
    def method(self, proxied, name, get_result, *args, **kwargs):
        return get_result(proxied(), *args, **kwargs)

    def getattr(self, proxied, name):
        return getattr(proxied(), name)

    def setattr(self, proxied, name, attr):
        setattr(proxied(), name, attr)

    def force(self, proxied):
        return proxied()

    def repr(self, proxied):
        return '%s(%r)' % (type(self).__name__, proxied)


LazyProxy = as_proxy(LazyProxy)


__all__ = ['as_proxy', 'get_wrapped', 'LazyProxy']

########NEW FILE########
__FILENAME__ = progress
# coding: utf-8
"""
    brownie.terminal.progress
    ~~~~~~~~~~~~~~~~~~~~~~~~~

    A widget-based progress bar implementation.


    .. versionadded:: 0.6

    :copyright: 2010-2011 by Daniel Neuhäuser
    :license: BSD, see LICENSE.rst for details
"""
from __future__ import division
import re
import math
from functools import wraps
from datetime import datetime

from brownie.caching import LFUCache
from brownie.datastructures import ImmutableDict


#: Binary prefixes, largest first.
BINARY_PREFIXES = [
    (u'Yi', 2 ** 80), # yobi
    (u'Zi', 2 ** 70), # zebi
    (u'Ei', 2 ** 60), # exbi
    (u'Pi', 2 ** 50), # pebi
    (u'Ti', 2 ** 40), # tebi
    (u'Gi', 2 ** 30), # gibi
    (u'Mi', 2 ** 20), # mebi
    (u'Ki', 2 ** 10)  # kibi
]

#: Positive SI prefixes, largest first.
SI_PREFIXES = [
    (u'Y', 10 ** 24), # yotta
    (u'Z', 10 ** 21), # zetta
    (u'E', 10 ** 18), # exa
    (u'P', 10 ** 15), # peta
    (u'T', 10 ** 12), # tera
    (u'G', 10 ** 9),  # giga
    (u'M', 10 ** 6),  # mega
    (u'k', 10 ** 3)   # kilo
]


_progressbar_re = re.compile(ur"""
    (?<!\$)\$([a-zA-Z]+) # identifier
    (:                   # initial widget value

        (?: # grouping to avoid : to be treated as part of
            # the left or operand

            "( # quoted string
                (?:
                    [^"]|    # any character except " or ...
                    (?<=\\)" # ... " preceded by a backslash
                )*
            )"|

            ([a-zA-Z]+) # identifiers can be used instead of strings
        )
    )?|
    (\$\$) # escaped $
""", re.VERBOSE)


def count_digits(n):
    if n == 0:
        return 1
    return int(math.log10(abs(n)) + (2 if n < 0 else 1))


def bytes_to_readable_format(bytes, binary=True):
    prefixes = BINARY_PREFIXES if binary else SI_PREFIXES
    for prefix, size in prefixes:
        if bytes >= size:
            result = bytes / size
            return result, prefix + 'B'
    return bytes, 'B'


def bytes_to_string(bytes, binary=True):
    """
    Provides a nice readable string representation for `bytes`.

    :param binary:
        If ``True`` uses binary prefixes otherwise SI prefixes are used.
    """
    result, prefix = bytes_to_readable_format(bytes, binary=binary)
    if isinstance(result, int) or getattr(result, 'is_integer', lambda: False)():
        return '%i%s' % (result, prefix)
    return '%.02f%s' % (result, prefix)


@LFUCache.decorate(maxsize=64)
def parse_progressbar(string):
    """
    Parses a string representing a progress bar.
    """
    def add_text(text):
        if not rv or rv[-1][0] != 'text':
            rv.append(['text', text])
        else:
            rv[-1][1] += text
    rv = []
    remaining = string
    while remaining:
        match = _progressbar_re.match(remaining)
        if match is None:
            add_text(remaining[0])
            remaining = remaining[1:]
        elif match.group(5):
            add_text(u'$')
            remaining = remaining[match.end():]
        else:
            if match.group(3) is None:
                value = match.group(4)
            else:
                value = match.group(3).decode('string-escape')
            rv.append([match.group(1), value])
            remaining = remaining[match.end():]
    return rv


class Widget(object):
    """
    Represents a part of a progress bar.
    """
    #: The priority of the widget defines in which order they are updated. The
    #: default priority is 0.
    #:
    #: This is important as the first widget being updated has the entire
    #: line available.
    priority = 0

    #: Should be ``True`` if this widget depends on
    #: :attr:`ProgressBar.maxsteps` being set to something other than ``None``.
    requires_fixed_size = False

    @property
    def provides_size_hint(self):
        return self.size_hint.im_func is not Widget.size_hint.im_func

    def size_hint(self, progressbar):
        """
        Should return the required size or ``None`` if it cannot be given.
        """
        return None

    def init(self, progressbar, remaining_width, **kwargs):
        """
        Called when the progress bar is initialized.

        Should return the output of the widget as string.
        """
        raise NotImplementedError('%s.init' % self.__class__.__name__)

    def update(self, progressbar, remaining_width, **kwargs):
        """
        Called when the progress bar is updated, not necessarily with each
        step.

        Should return the output of the widget as string.
        """
        raise NotImplementedError('%s.update' % self.__class__.__name__)

    def finish(self, progressbar, remaining_width, **kwargs):
        """
        Called when the progress bar is finished, not necessarily after
        maxsteps has been reached, per default this calls :meth:`update`.

        Should return the output of the widget as string.
        """
        return self.update(progressbar, remaining_width, **kwargs)

    def __repr__(self):
        return '%s()' % self.__class__.__name__


class TextWidget(Widget):
    """
    Represents static text in a progress bar.
    """
    def __init__(self, text):
        self.text = text

    def size_hint(self, progressbar):
        return len(self.text)

    def update(self, progressbar, remaining_width, **kwargs):
        return self.text

    init = update

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.text)


class HintWidget(Widget):
    """
    Represents a 'hint', changing text passed with each update, in a progress
    bar.

    Requires that :meth:`ProgressBar.next` is called with a `hint` keyword
    argument.

    This widget has a priority of 1.
    """
    priority = 1

    def __init__(self, initial_hint=u''):
        self.initial_hint = initial_hint

    def init(self, progressbar, remaining_width, **kwargs):
        return self.initial_hint

    def update(self, progressbar, remaining_width, **kwargs):
        try:
            return kwargs.get('hint', u'')
        except KeyError:
            raise TypeError("expected 'hint' as a keyword argument")

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.initial_hint)


class PercentageWidget(Widget):
    """
    Represents a string showing the progress as percentage.
    """
    requires_fixed_size = True

    def calculate_percentage(self, progressbar):
        return 100 / progressbar.maxsteps * progressbar.step

    def size_hint(self, progressbar):
        return count_digits(self.calculate_percentage(progressbar)) + 1

    def init(self, progressbar, remaining_width, **kwargs):
        return '0%'

    def update(self, progressbar, remaining_width, **kwargs):
        return '%i%%' % self.calculate_percentage(progressbar)

    def finish(self, progressbar, remaining_width, **kwargs):
        return '100%'


class BarWidget(Widget):
    """
    A simple bar which moves with each update not corresponding with the
    progress being made.

    The bar is enclosed in brackets, progress is visualized by tree hashes
    `###` moving forwards or backwards with each update; the rest of the bar is
    filled with dots `.`.
    """
    def __init__(self):
        self.position = 0
        self.going_forward = True

    def make_bar(self, width):
        parts = ['.'] * (width - 2)
        parts[self.position:self.position+3] = '###'
        return '[%s]' % ''.join(parts)

    def init(self, progressbar, remaining_width, **kwargs):
        return self.make_bar(remaining_width)

    def update(self, progressbar, remaining_width, **kwargs):
        width = remaining_width - 2
        if (self.position + 3) > width:
            self.position = width - 4
            self.going_forward = False
        elif self.going_forward:
            self.position += 1
            if self.position + 3 == width:
                self.going_forward = False
        else:
            self.position -= 1
            if self.position == 0:
                self.going_forward = True
        return self.make_bar(remaining_width)


class PercentageBarWidget(Widget):
    """
    A simple bar which shows the progress in terms of a bar being filled
    corresponding to the percentage of progress.

    The bar is enclosed in brackets, progress is visualized with hashes `#`
    the remaining part uses dots `.`.
    """
    requires_fixed_size = True

    def init(self, progressbar, remaining_width, **kwargs):
        return '[%s]' % ('.' * (remaining_width - 2))

    def update(self, progressbar, remaining_width, **kwargs):
        percentage = 100 / progressbar.maxsteps * progressbar.step
        marked_width = int(percentage * (remaining_width - 2) / 100)
        return '[%s]' % ('#' * marked_width).ljust(remaining_width - 2, '.')

    def finish(self, progressbar, remaining_width, **kwargs):
        return '[%s]' % ('#' * (remaining_width - 2))


class StepWidget(Widget):
    """
    Shows at which step we are currently at and how many are remaining as
    `step of steps`.

    :param unit:
        If each step represents something other than a simple task e.g. a byte
        when doing file transactions, you can specify a unit which is used.

    Supported units:

    - `'bytes'` - binary prefix only, SI might be added in the future
    """
    requires_fixed_size = True
    units = ImmutableDict({
        'bytes': bytes_to_string,
        None: unicode
    })

    def __init__(self, unit=None):
        if unit not in self.units:
            raise ValueError('unknown unit: %s' % unit)
        self.unit = unit

    def get_values(self, progressbar):
        convert = self.units[self.unit]
        return convert(progressbar.step), convert(progressbar.maxsteps)

    def size_hint(self, progressbar):
        step, maxsteps = self.get_values(progressbar)
        return len(step) + len(maxsteps) + 4 # ' of '

    def init(self, progressbar, remaining_width, **kwargs):
        return u'%s of %s' % self.get_values(progressbar)

    update = init


class TimeWidget(Widget):
    """
    Shows the elapsed time in hours, minutes and seconds as
    ``$hours:$minutes:$seconds``.

    This widget has a priority of 2.
    """
    priority = 2

    def init(self, progressbar, remaining_width, **kwargs):
        self.start_time = datetime.now()
        return '00:00:00'

    def update(self, progressbar, remaining_width, **kwargs):
        seconds = (datetime.now() - self.start_time).seconds
        minutes = 0
        hours = 0

        minute = 60
        hour = minute * 60

        if seconds > hour:
            hours, seconds = divmod(seconds, hour)
        if seconds > minute:
            minutes, seconds = divmod(seconds, minute)

        return '%02i:%02i:%02i' % (hours, minutes, seconds)


class DataTransferSpeedWidget(Widget):
    """
    Shows the data transfer speed in bytes per second using SI prefixes.

    This widget has a priority of 2.
    """
    priority = 2

    def init(self, progressbar, remaining_width, **kwargs):
        self.begin_timing = datetime.now()
        self.last_step = 0
        return '0kb/s'

    def update(self, progressbar, remaining_width, **kwargs):
        end_timing = datetime.now()
        # .seconds is an integer so our calculations result in 0 if each update
        # takes less than a second, therefore we have to calculate the exact
        # time in seconds
        elapsed = (end_timing - self.begin_timing).microseconds * 10 ** -6
        step = progressbar.step - self.last_step
        if elapsed == 0:
            result = '%.02f%s/s' % bytes_to_readable_format(0, binary=False)
        else:
            result = '%.02f%s/s' % bytes_to_readable_format(
                step / elapsed,
                binary=False
            )
        self.begin_timing = end_timing
        self.last_step = progressbar.step
        return result


class ProgressBar(object):
    """
    A progress bar which acts as a container for various widgets which may be
    part of a progress bar.

    Initializing and finishing can be done by using the progress bar as a
    context manager instead of calling :meth:`init` and :meth:`finish`.

    :param widgets:
        An iterable of widgets which should be used.

    :param writer:
        A :class:`~brownie.terminal.TerminalWriter` which is used by the
        progress bar.

    :param maxsteps:
        The number of steps, not necessarily updates, which are to be made.
    """
    @classmethod
    def from_string(cls, string, writer, maxsteps=None, widgets=None):
        """
        Returns a :class:`ProgressBar` from a string.

        The string is used as a progressbar, ``$[a-zA-Z]+`` is substituted with
        a widget as defined by `widgets`.

        ``$`` can be escaped with another ``$`` e.g. ``$$foo`` will not be
        substituted.

        Initial values as required for the :class:`HintWidget` are given like
        this ``$hint:initial``, if the initial value is supposed to contain a
        space you have to use a quoted string ``$hint:"foo bar"``; quoted can
        be escaped using a backslash.

        If you want to provide your own widgets or overwrite existing ones
        pass a dictionary mapping the desired names to the widget classes to
        this method using the `widgets` keyword argument. The default widgets
        are:

        +--------------+----------------------------------+-------------------+
        | Name         | Class                            | Requires maxsteps |
        +==============+==================================+===================+
        | `text`       | :class:`TextWidget`              | No                |
        +--------------+----------------------------------+-------------------+
        | `hint`       | :class:`HintWidget`              | No                |
        +--------------+----------------------------------+-------------------+
        | `percentage` | :class:`Percentage`              | Yes               |
        +--------------+----------------------------------+-------------------+
        | `bar`        | :class:`BarWidget`               | No                |
        +--------------+----------------------------------+-------------------+
        | `sizedbar`   | :class:`PercentageBarWidget`     | Yes               |
        +--------------+----------------------------------+-------------------+
        | `step`       | :class:`StepWidget`              | Yes               |
        +--------------+----------------------------------+-------------------+
        | `time`       | :class:`TimeWidget`              | No                |
        +--------------+----------------------------------+-------------------+
        | `speed`      | :class:`DataTransferSpeedWidget` | No                |
        +--------------+----------------------------------+-------------------+
        """
        default_widgets = {
            'text': TextWidget,
            'hint': HintWidget,
            'percentage': PercentageWidget,
            'bar': BarWidget,
            'sizedbar': PercentageBarWidget,
            'step': StepWidget,
            'time': TimeWidget,
            'speed': DataTransferSpeedWidget
        }
        widgets = dict(default_widgets.copy(), **(widgets or {}))
        rv = []
        for name, initial in parse_progressbar(string):
            if name not in widgets:
                raise ValueError('widget not found: %s' % name)
            if initial:
                widget = widgets[name](initial)
            else:
                widget = widgets[name]()
            rv.append(widget)
        return cls(rv, writer, maxsteps=maxsteps)

    def __init__(self, widgets, writer, maxsteps=None):
        widgets = list(widgets)
        if maxsteps is None:
            for widget in widgets:
                if widget.requires_fixed_size:
                    raise ValueError(
                        '%r requires maxsteps to be given' % widget
                    )

        self.widgets = widgets
        self.writer = writer
        self.maxsteps = maxsteps
        self.step = 0

    def get_step(self):
        return self._step

    def set_step(self, new_step):
        if self.maxsteps is None or new_step <= self.maxsteps:
            self._step = new_step
        else:
            raise ValueError('step cannot be larger than maxsteps')

    step = property(get_step, set_step)
    del get_step, set_step

    def __iter__(self):
        return self

    def get_widgets_by_priority(self):
        """
        Returns an iterable of tuples consisting of the position of the widget
        and the widget itself ordered by each widgets priority.
        """
        return sorted(
            enumerate(self.widgets),
            key=lambda x: x[1].priority,
            reverse=True
        )

    def get_usable_width(self):
        """
        Returns the width usable by all widgets which don't provide a size
        hint.
        """
        return self.writer.get_usable_width() - sum(
            widget.size_hint(self) for widget in self.widgets
            if widget.provides_size_hint
        )

    def write(self, string, update=True):
        if update:
            self.writer.write('\r', escape=False, flush=False)
        self.writer.begin_line()
        self.writer.write(string)

    def make_writer(updating=True, finishing=False):
        def decorate(func):
            @wraps(func)
            def wrapper(self, **kwargs):
                if finishing and self.step == self.maxsteps:
                    return
                if updating and not finishing:
                    self.step += kwargs.get('step', 1)
                parts = []
                remaining_width = self.get_usable_width()
                for i, widget in self.get_widgets_by_priority():
                    part = func(self, widget, remaining_width, **kwargs)
                    if not widget.provides_size_hint:
                        remaining_width -= len(part)
                    parts.append((i, part))
                parts.sort()
                self.write(''.join(part for _, part in parts), update=updating)
                if finishing:
                    self.writer.newline()
            return wrapper
        return decorate

    @make_writer(updating=False)
    def init(self, widget, remaining_width, **kwargs):
        """
        Writes the initial progress bar to the terminal.
        """
        return widget.init(self, remaining_width, **kwargs)

    @make_writer()
    def next(self, widget, remaining_width, step=1, **kwargs):
        """
        Writes an updated version of the progress bar to the terminal.

        If the update corresponds to multiple steps, pass the number of steps
        which have been made as an argument. If `step` is larger than
        `maxsteps` a :exc:`ValueError` is raised.
        """
        return widget.update(self, remaining_width, **kwargs)

    @make_writer(finishing=True)
    def finish(self, widget, remaining_width, **kwargs):
        """
        Writes the finished version of the progress bar to the terminal.

        This method may be called even if `maxsteps` has not been reached or
        has not been defined.
        """
        return widget.finish(self, remaining_width, **kwargs)

    del make_writer

    def __enter__(self):
        self.init()
        return self

    def __exit__(self, etype, evalue, traceback):
        if etype is None:
            self.finish()

    def __repr__(self):
        return '%s(%r, %r, maxsteps=%r)' % (
            self.__class__.__name__, self.widgets, self.writer, self.maxsteps
        )


__all__ = [
    'ProgressBar', 'TextWidget', 'HintWidget', 'PercentageWidget', 'BarWidget',
    'PercentageBarWidget', 'StepWidget', 'TimeWidget', 'DataTransferSpeedWidget'
]

########NEW FILE########
__FILENAME__ = __main__
# coding: utf-8
"""
    brownie.terminal
    ~~~~~~~~~~~~~~~~

    :copyright: 2010-2011 by Daniel Neuhäuser
    :license: BSD, see LICENSE.rst for details
"""
import sys

from brownie.terminal import TerminalWriter, _colour_names, ATTRIBUTES

writer = TerminalWriter(sys.stdout)
for name in _colour_names:
    with writer.line():
        writer.write(name, text_colour=name)

    with writer.line():
        writer.write(name, background_colour=name)

for name in ATTRIBUTES:
    if name == 'reset':
        continue
    writer.writeline(name, **{name: True})

with writer.line():
    with writer.options(underline=True):
        writer.write('underline')
        with writer.options(background_colour='red'):
            writer.write('background')
            writer.write('text', text_colour='green')
            writer.write('background')
        writer.write('underline')

########NEW FILE########
__FILENAME__ = abstract
# coding: utf-8
"""
    brownie.tests.abstract
    ~~~~~~~~~~~~~~~~~~~~~~

    Tests for mod:`brownie.abstract`.

    :copyright: 2010-2011 by Daniel Neuhäuser
    :license: BSD, see LICENSE.rst for details
"""
import sys

from attest import Tests, TestBase, test_if, test, Assert

from brownie.itools import product
from brownie.abstract import VirtualSubclassMeta, ABCMeta, AbstractClassMeta


GE_PYTHON_26 = sys.version_info >= (2, 6)


tests = Tests()

@tests.test_if(GE_PYTHON_26)
def test_virtual_subclass_meta():
    from abc import ABCMeta

    class Foo(object):
        __metaclass__ = ABCMeta


    class Bar(object):
        __metaclass__ = ABCMeta


    class Simple(object):
        __metaclass__ = VirtualSubclassMeta
        virtual_superclasses = [Foo, Bar]

    class InheritingSimple(Simple):
        pass

    for a, b in product([Simple, InheritingSimple], [Foo, Bar]):
        Assert.issubclass(a, b)
        Assert.isinstance(a(), b)

    Assert.issubclass(InheritingSimple, Simple)
    Assert.isinstance(InheritingSimple(), Simple)

    class Spam(object):
        __metaclass__ = ABCMeta

    class Eggs(object):
        __metaclass__ = ABCMeta

    class SimpleMonty(object):
        __metaclass__ = VirtualSubclassMeta
        virtual_superclasses = [Spam, Eggs]

    class MultiInheritance(Simple, SimpleMonty):
        pass

    class MultiVirtualInheritance(object):
        __metaclass__ = VirtualSubclassMeta
        virtual_superclasses = [Simple, SimpleMonty]

    for virtual_super_cls in [Foo, Bar, Simple, Spam, Eggs, SimpleMonty]:
        Assert.issubclass(MultiInheritance, virtual_super_cls)
        Assert.isinstance(MultiInheritance(), virtual_super_cls)


class TestABCMeta(TestBase):
    @test_if(GE_PYTHON_26)
    def type_checks_work(self):
        class Foo(object):
            __metaclass__ = ABCMeta

        class Bar(object):
            pass

        Foo.register(Bar)

        Assert.issubclass(Bar, Foo)
        Assert.isinstance(Bar(), Foo)

    @test
    def api_works_cleanly(self):
        class Foo(object):
            __metaclass__ = ABCMeta

        class Bar(object):
            pass

        Foo.register(Bar)

tests.register(TestABCMeta)


@tests.test_if(GE_PYTHON_26)
def test_abstract_class_meta():
    class Foo(object):
        __metaclass__ = ABCMeta

    class Bar(object):
        __metaclass__ = AbstractClassMeta

        virtual_superclasses = [Foo]

    class Baz(object):
        __metaclass__ = VirtualSubclassMeta

        virtual_superclasses = [Bar]

    Assert.issubclass(Baz, Foo)
    Assert.issubclass(Baz, Bar)

########NEW FILE########
__FILENAME__ = caching
# coding: utf-8
"""
    brownie.tests.caching
    ~~~~~~~~~~~~~~~~~~~~~

    Tests for :mod:`brownie.caching`.

    :copyright: 2010-2011 by Daniel Neuhäuser
    :license: BSD, see LICENSE.rst for details
"""
import time

from attest import Tests, Assert, TestBase, test

from brownie.caching import cached_property, LRUCache, LFUCache, memoize


tests = Tests()


@tests.test
def test_cached_property():
    class Foo(object):
        def __init__(self):
            self.counter = 0

        @cached_property
        def spam(self):
            self.counter += 1
            return self.counter

    Assert(Foo.spam).is_(Foo.spam)

    foo = Foo()
    Assert(foo.spam) == 1
    Assert(foo.spam) == 1


class TestLRUCache(TestBase):
    @test
    def decorate(self):
        @LRUCache.decorate(2)
        def foo(*args, **kwargs):
            time.sleep(.1)
            return args, kwargs

        tests = [
            (('foo', 'bar'), {}),
            (('foo', 'bar'), {'spam': 'eggs'}),
            ((1, 2), {})
        ]
        times = []

        for test in tests:
            args, kwargs = test
            old = time.time()
            Assert(foo(*args, **kwargs)) == test
            new = time.time()
            uncached_time = new - old

            old = time.time()
            Assert(foo(*args, **kwargs)) == test
            new = time.time()
            cached_time = new - old
            Assert(cached_time) < uncached_time
            times.append((uncached_time, cached_time))
        old = time.time()
        foo(*tests[0][0], **tests[0][1])
        new = time.time()
        Assert(new - old) > times[0][1]

    @test
    def basics(self):
        cache = LRUCache(maxsize=2)
        cache[1] = 2
        cache[3] = 4
        cache[5] = 6
        Assert(cache.items()) == [(3, 4), (5, 6)]

    @test
    def repr(self):
        cache = LRUCache()
        Assert(repr(cache)) == 'LRUCache({}, inf)'

tests.register(TestLRUCache)


class TestLFUCache(TestBase):
    @test
    def basics(self):
        cache = LFUCache(maxsize=2)
        cache[1] = 2
        cache[3] = 4
        cache[3]
        cache[5] = 6
        Assert(cache.items()) == [(1, 2), (5, 6)]

    @test
    def repr(self):
        cache = LFUCache()
        Assert(repr(cache)) == 'LFUCache({}, inf)'

tests.register(TestLFUCache)


@tests.test
def test_memoize():
    @memoize
    def foo(a, b):
        return a + b
    Assert(foo(1, 1)) == 2
    Assert(foo(1, 1)) == 2
    Assert(foo(1, 2)) == 3

########NEW FILE########
__FILENAME__ = context
# coding: utf-8
"""
    brownie.tests.context
    ~~~~~~~~~~~~~~~~~~~~~

    Tests for :mod:`brownie.context`.

    :copyright: 2010-2011 by Daniel Neuhäuser
    :license: BSD, see LICENSE.rst for details
"""
from __future__ import with_statement
import time
from Queue import Queue
from threading import Thread, Event

from attest import Tests, TestBase, Assert, test, test_if

try:
    import eventlet
except ImportError:
    eventlet = None

from brownie.context import (
    ContextStackManagerBase, ContextStackManagerThreadMixin,
    ContextStackManagerEventletMixin
)


class TestContextStackManagerBase(TestBase):
    @test
    def application_context(self):
        csm = ContextStackManagerBase()
        csm.push_application('foo')
        Assert(list(csm.iter_current_stack())) == ['foo']
        csm.push_application('bar')
        Assert(list(csm.iter_current_stack())) == ['bar', 'foo']
        Assert(csm.pop_application()) == 'bar'
        Assert(csm.pop_application()) == 'foo'

        with Assert.raises(RuntimeError):
            csm.pop_application()

    @test_if(eventlet)
    def context_inheritance(self):
        class FooContextManager(
                ContextStackManagerEventletMixin,
                ContextStackManagerThreadMixin,
                ContextStackManagerBase
            ):
            pass
        csm = FooContextManager()
        csm.push_application('foo')

        def foo(csm, queue):
            csm.push_thread('bar')
            queue.put(list(csm.iter_current_stack()))
            eventlet.spawn(bar, csm, queue).wait()
            queue.put(list(csm.iter_current_stack()))

        def bar(csm, queue):
            csm.push_coroutine('baz')
            queue.put(list(csm.iter_current_stack()))

        queue = Queue()
        thread = Thread(target=foo, args=(csm, queue))
        thread.start()
        Assert(queue.get()) == ['bar', 'foo']
        Assert(queue.get()) == ['baz', 'bar', 'foo']
        Assert(queue.get()) == ['bar', 'foo']
        Assert(list(csm.iter_current_stack())) == ['foo']


class ThreadContextStackManager(
        ContextStackManagerThreadMixin,
        ContextStackManagerBase
    ):
    pass


class TestContextStackManagerThreadMixin(TestBase):
    @test
    def inherits_application_stack(self):
        csm = ThreadContextStackManager()
        csm.push_application('foo')

        def foo(csm, queue):
            queue.put(list(csm.iter_current_stack()))
            csm.push_thread('bar')
            queue.put(list(csm.iter_current_stack()))

        queue = Queue()
        thread = Thread(target=foo, args=(csm, queue))
        thread.start()
        thread.join()
        Assert(queue.get()) == ['foo']
        Assert(queue.get()) == ['bar', 'foo']
        Assert(list(csm.iter_current_stack())) == ['foo']

    @test
    def multiple_thread_contexts(self):
        csm = ThreadContextStackManager()

        def make_func(name):
            def func(csm, queue, event):
                csm.push_thread(name)
                queue.put(list(csm.iter_current_stack()))
                event.wait()
            func.__name__ = name
            return func

        foo_queue = Queue()
        bar_queue = Queue()
        foo_event = Event()
        bar_event = Event()
        foo_thread = Thread(
            target=make_func('foo'), args=(csm, foo_queue, foo_event)
        )
        bar_thread = Thread(
            target=make_func('bar'), args=(csm, bar_queue, bar_event)
        )
        foo_thread.start()
        # during that time foo should have pushed an object on
        # the thread local stack
        time.sleep(1)
        bar_thread.start()
        foo_event.set()
        bar_event.set()
        Assert(foo_queue.get()) == ['foo']
        Assert(bar_queue.get()) == ['bar']
        Assert(list(csm.iter_current_stack())) == []

    @test
    def basics(self):
        csm = ThreadContextStackManager()
        with Assert.raises(RuntimeError):
            csm.pop_thread()
        csm.push_thread('foo')
        Assert(list(csm.iter_current_stack())) == ['foo']
        csm.push_thread('bar')
        Assert(list(csm.iter_current_stack())) == ['bar', 'foo']
        Assert(csm.pop_thread()) == 'bar'
        Assert(list(csm.iter_current_stack())) == ['foo']


class EventletContextStackManager(
        ContextStackManagerEventletMixin,
        ContextStackManagerBase
    ):
    pass


class TestContextStackManagerEventletMixin(TestBase):
    if eventlet:
        @test
        def inherits_application_stack(self):
            csm = EventletContextStackManager()
            csm.push_application('foo')

            def foo(csm, queue):
                queue.put(list(csm.iter_current_stack()))
                csm.push_coroutine('bar')
                queue.put(list(csm.iter_current_stack()))

            queue = eventlet.Queue()
            greenthread = eventlet.spawn(foo, csm, queue)
            greenthread.wait()
            Assert(queue.get()) == ['foo']
            Assert(queue.get()) == ['bar', 'foo']

        @test
        def multiple_greenthread_contexts(self):
            csm = EventletContextStackManager()

            def make_func(name):
                def func(csm, queue):
                    csm.push_coroutine(name)
                    queue.put(list(csm.iter_current_stack()))
                func.__name__ = name
                return func

            foo_queue = eventlet.Queue()
            bar_queue = eventlet.Queue()
            foo = eventlet.spawn(make_func('foo'), csm, foo_queue)
            bar = eventlet.spawn(make_func('bar'), csm, bar_queue)
            foo.wait()
            bar.wait()
            Assert(foo_queue.get()) == ['foo']
            Assert(bar_queue.get()) == ['bar']

        @test
        def basics(self):
            csm = EventletContextStackManager()
            with Assert.raises(RuntimeError):
                csm.pop_coroutine()
            csm.push_coroutine('foo')
            Assert(list(csm.iter_current_stack())) == ['foo']
            csm.push_coroutine('bar')
            Assert(list(csm.iter_current_stack())) == ['bar', 'foo']
            Assert(csm.pop_coroutine()) == 'bar'
            Assert(list(csm.iter_current_stack())) == ['foo']
    else:
        @test
        def init(self):
            with Assert.raises(RuntimeError):
                EventletContextStackManager()


tests = Tests([
    TestContextStackManagerBase, TestContextStackManagerThreadMixin,
    TestContextStackManagerEventletMixin
])

########NEW FILE########
__FILENAME__ = iterators
# coding: utf-8
"""
    brownie.tests.datastructures.iterators
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Tests for :mod:`brownie.datastructures.iterators`.

    :copyright: 2010-2011 by Daniel Neuhäuser
    :license: BSD, see LICENSE.rst for details
"""
from __future__ import with_statement

from attest import Tests, TestBase, test, Assert

from brownie.datastructures import PeekableIterator


class TestPeekableIterator(TestBase):
    @test
    def iter(self):
        original = range(10)
        iterator = PeekableIterator(original)
        for item, expected in zip(original, iterator):
            Assert(item) == expected

    @test
    def iter_returns_self(self):
        iterator = PeekableIterator(range(10))
        Assert(iter(iterator)).is_(iterator)

    @test
    def peek(self):
        iterator = PeekableIterator(range(10))
        with Assert.raises(ValueError):
            iterator.peek(0)
        with Assert.raises(ValueError):
            iterator.peek(-1)

        Assert(iterator.peek(11)) == range(10)

        Assert(iterator.peek(10)) == range(10)
        for item, expected in zip(iterator, range(10)):
            Assert(item) == expected

        iterator = PeekableIterator(range(10))
        Assert(iterator.peek()) == iterator.peek()
        Assert(iterator.peek()) == [0]

        Assert(iterator.peek(10)) == range(10)
        Assert(iterator.peek(5)) == range(5)

    @test
    def repr(self):
        original = iter(xrange(10))
        iterator = PeekableIterator(original)
        Assert(repr(iterator)) == 'PeekableIterator(%r)' % iter(original)


tests = Tests([TestPeekableIterator])

########NEW FILE########
__FILENAME__ = mappings
# coding: utf-8
"""
    brownie.tests.datastructures.mappings
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Tests for :mod:`brownie.datastructures.mappings`.

    :copyright: 2010-2011 by Daniel Neuhäuser
    :license: BSD, see LICENSE.rst for details
"""
from __future__ import with_statement
import sys
import pickle

from attest import Tests, TestBase, test, test_if, Assert

from brownie.datastructures import (
    ImmutableDict,
    CombinedDict,
    MultiDict,
    ImmutableMultiDict,
    CombinedMultiDict,
    OrderedDict,
    OrderedMultiDict,
    ImmutableOrderedDict,
    ImmutableOrderedMultiDict,
    FixedDict,
    Counter
)


GE_PYTHON_26 = sys.version_info >= (2, 6)


class DictTestMixin(object):
    dict_class = None

    @test
    def fromkeys(self):
        d = self.dict_class.fromkeys([1, 2])
        Assert(d[1]) == None
        Assert(d[2]) == None
        d = self.dict_class.fromkeys([1, 2], 'foo')
        Assert(d[1]) == 'foo'
        Assert(d[2]) == 'foo'

        Assert(d.__class__).is_(self.dict_class)

    @test
    def init(self):
        data = [(1, 2), (3, 4)]
        with Assert.raises(TypeError):
            self.dict_class(*data)
        for mapping_type in [lambda x: x, self.dict_class]:
            d = self.dict_class(mapping_type(data))
            Assert(d[1]) == 2
            Assert(d[3]) == 4
        d = self.dict_class(foo='bar', spam='eggs')
        Assert(d['foo']) == 'bar'
        Assert(d['spam']) == 'eggs'
        d = self.dict_class([('foo', 'bar'), ('spam', 'eggs')], foo='baz')
        Assert(d['foo']) == 'baz'
        Assert(d['spam']) == 'eggs'

    @test
    def copy(self):
        d = self.dict_class()
        Assert(d.copy()).is_not(d)

    @test
    def setitem(self):
        d = self.dict_class()
        d[1] = 2
        Assert(d[1]) == 2
        d[1] = 3
        Assert(d[1]) == 3

    @test
    def getitem(self):
        d = self.dict_class([(1, 2), (3, 4)])
        Assert(d[1]) == 2
        Assert(d[3]) == 4

    @test
    def delitem(self):
        d = self.dict_class()
        d[1] = 2
        Assert(d[1]) == 2
        del d[1]
        with Assert.raises(KeyError):
            del d[1]

    @test
    def get(self):
        d = self.dict_class()
        Assert(d.get(1)) == None
        Assert(d.get(1, 2)) == 2
        d = self.dict_class({1: 2})
        Assert(d.get(1)) == 2
        Assert(d.get(1, 3)) == 2

    @test
    def setdefault(self):
        d = self.dict_class()
        Assert(d.setdefault(1)) == None
        Assert(d[1]) == None
        Assert(d.setdefault(1, 2)) == None
        Assert(d.setdefault(3, 4)) == 4
        Assert(d[3]) == 4

    @test
    def pop(self):
        d = self.dict_class()
        d[1] = 2
        Assert(d.pop(1)) == 2
        with Assert.raises(KeyError):
            d.pop(1)
        Assert(d.pop(1, 2)) == 2

    @test
    def popitem(self):
        d = self.dict_class([(1, 2), (3, 4)])
        items = iter(d.items())
        while d:
            Assert(d.popitem()) == items.next()

    @test
    def clear(self):
        d = self.dict_class([(1, 2), (3, 4)])
        assert d
        d.clear()
        assert not d

    @test
    def item_accessor_equality(self):
        d = self.dict_class([(1, 2), (3, 4)])
        Assert(list(d)) == d.keys()
        Assert(list(d.iterkeys())) == d.keys()
        Assert(list(d.itervalues())) == d.values()
        Assert(list(d.iteritems())) == d.items()
        for key, value, item in zip(d.keys(), d.values(), d.items()):
            Assert((key, value)) == item
            Assert(d[key]) == value

    @test
    def update(self):
        d = self.dict_class()
        with Assert.raises(TypeError):
            d.update((1, 2), (3, 4))

        for mapping in ([(1, 2), (3, 4)], self.dict_class([(1, 2), (3, 4)])):
            d.update(mapping)
            Assert(d[1]) == 2
            Assert(d[3]) == 4

        d = self.dict_class()
        d.update([('foo', 'bar'), ('spam', 'eggs')], foo='baz')
        Assert(d['foo']) == 'baz'
        Assert(d['spam']) == 'eggs'

    @test
    def repr(self):
        d = self.dict_class()
        Assert(repr(d)) == '%s()' % d.__class__.__name__
        original = {1: 2}
        d = self.dict_class(original)
        Assert(repr(d)) == '%s(%s)' % (d.__class__.__name__, repr(original))

    @test
    def test_custom_new(self):
        class D(self.dict_class):
            def __new__(cls, *args, **kwargs):
                return 42
        Assert(D.fromkeys([])) == 42

    @test
    def picklability(self):
        d = self.dict_class([(1, 2), (3, 4)])
        pickled = pickle.loads(pickle.dumps(d))
        Assert(pickled == d)
        Assert(pickled.__class__).is_(d.__class__)


class ImmutableDictTestMixin(DictTestMixin):
    @test
    def setitem(self):
        for d in (self.dict_class(), self.dict_class({1: 2})):
            with Assert.raises(TypeError):
                d[1] = 2

    @test
    def delitem(self):
        for d in (self.dict_class(), self.dict_class({1: 2})):
            with Assert.raises(TypeError):
                del d[1]

    @test
    def setdefault(self):
        for d in (self.dict_class(), self.dict_class({1: 2})):
            with Assert.raises(TypeError):
                d.setdefault(1)
            with Assert.raises(TypeError):
                d.setdefault(1, 3)

    @test
    def pop(self):
        d = self.dict_class()
        with Assert.raises(TypeError):
            d.pop(1)
        with Assert.raises(TypeError):
            d.pop(1, 2)
        d = self.dict_class({1: 2})
        with Assert.raises(TypeError):
            d.pop(1)

    @test
    def popitem(self):
        d = self.dict_class()
        with Assert.raises(TypeError):
            d.popitem()

    @test
    def update(self):
        d = self.dict_class()
        with Assert.raises(TypeError):
            d.update([])
        with Assert.raises(TypeError):
            d.update(foo='bar')

    @test
    def clear(self):
        d = self.dict_class()
        with Assert.raises(TypeError):
            d.clear()


class TestImmutableDict(TestBase, ImmutableDictTestMixin):
    dict_class = ImmutableDict

    @test_if(GE_PYTHON_26)
    def type_checking(self):
        Assert.isinstance(self.dict_class(), dict)

    @test
    def hashability(self):
        a = self.dict_class([(1, 2), (3, 4)])
        b = self.dict_class(a)
        Assert(hash(a)) == hash(b)
        Assert(hash(a)) != hash(ImmutableDict([(1, 2), (5, 6)]))
        with Assert.raises(TypeError):
            hash(ImmutableDict({1: []}))


class CombinedDictTestMixin(object):
    # .fromkeys() doesn't work here, so we don't need that test
    test_custom_new = None

    @test
    def fromkeys(self):
        with Assert.raises(TypeError):
            self.dict_class.fromkeys(['foo', 'bar'])

    @test
    def init(self):
        with Assert.raises(TypeError):
            self.dict_class(foo='bar')
        self.dict_class([{}, {}])

    @test
    def getitem(self):
        d = self.dict_class([{1: 2, 3: 4}, {1: 4, 3: 2}])
        Assert(d[1]) == 2
        Assert(d[3]) == 4

    @test
    def get(self):
        d = self.dict_class()
        Assert(d.get(1)) == None
        Assert(d.get(1, 2)) == 2

        d = self.dict_class([{1: 2}, {1: 3}])
        Assert(d.get(1)) == 2
        Assert(d.get(1, 4)) == 2

    @test
    def item_accessor_equality(self):
        d = self.dict_class([{1: 2}, {1: 3}, {2: 4}])
        Assert(d.keys()) == [1, 2]
        Assert(d.values()) == [2, 4]
        Assert(d.items()) == [(1, 2), (2, 4)]
        Assert(list(d)) == list(d.iterkeys()) == d.keys()
        Assert(list(d.itervalues())) == d.values()
        Assert(list(d.iteritems())) == d.items()

    @test
    def repr(self):
        Assert(repr(self.dict_class())) == '%s()' % self.dict_class.__name__
        d = self.dict_class([{}, {1: 2}])
        Assert(repr(d)) == '%s([{}, {1: 2}])' % self.dict_class.__name__


class TestCombinedDict(TestBase, CombinedDictTestMixin, ImmutableDictTestMixin):
    dict_class = CombinedDict

    @test_if(GE_PYTHON_26)
    def type_checking(self):
        d = self.dict_class()
        Assert.isinstance(d, ImmutableDict)
        Assert.isinstance(d, dict)

    @test
    def hashability(self):
        a = CombinedDict([ImmutableDict({1: 2}), ImmutableDict({3: 4})])
        Assert(hash(a)) == hash(CombinedDict(a.dicts))
        Assert(hash(a)) != hash(CombinedDict(reversed(a.dicts)))
        with Assert.raises(TypeError):
            hash(CombinedDict([{}]))


class MultiDictTestMixin(object):
    dict_class = None

    @test
    def init_with_lists(self):
        d = self.dict_class({'foo': ['bar'], 'spam': ['eggs']})
        Assert(d['foo']) == 'bar'
        Assert(d['spam']) == 'eggs'

    @test
    def add(self):
        d = self.dict_class()
        d.add('foo', 'bar')
        d.add('foo', 'spam')
        Assert(d['foo']) == 'bar'
        Assert(d.getlist('foo')) == ['bar', 'spam']

    @test
    def getlist(self):
        d = self.dict_class()
        Assert(d.getlist('foo')) == []
        d = self.dict_class({'foo': 'bar'})
        Assert(d.getlist('foo')) == ['bar']
        d = self.dict_class({'foo': ['bar', 'spam']})
        Assert(d.getlist('foo')) == ['bar', 'spam']

    @test
    def setlist(self):
        d = self.dict_class()
        d.setlist('foo', ['bar', 'spam'])
        Assert(d['foo']) == 'bar'
        Assert(d.getlist('foo')) == ['bar', 'spam']

    @test
    def setlistdefault(self):
        d = self.dict_class()
        Assert(d.setlistdefault('foo')) == [None]
        Assert(d['foo']).is_(None)
        Assert(d.setlistdefault('foo', ['bar'])) == [None]
        Assert(d['foo']).is_(None)
        Assert(d.setlistdefault('spam', ['eggs'])) == ['eggs']
        Assert(d['spam']) == 'eggs'

    @test
    def multi_items(self):
        d = self.dict_class({
            'foo': ['bar'],
            'spam': ['eggs', 'monty']
        })
        Assert(len(d.items())) == 2
        Assert(len(d.items(multi=True))) == 3
        Assert(d.items(multi=True)) == list(d.iteritems(multi=True))
        keys = [pair[0] for pair in d.items(multi=True)]
        Assert(set(keys)) == set(['foo', 'spam'])
        values = [pair[1] for pair in d.items(multi=True)]
        Assert(set(values)) == set(['bar', 'eggs', 'monty'])

    @test
    def lists(self):
        d = self.dict_class({
            'foo': ['bar', 'baz'],
            'spam': ['eggs', 'monty']
        })
        Assert(d.lists()) == list(d.iterlists())
        ('foo', ['bar', 'baz']) in Assert(d.lists())
        ('spam', ['eggs', 'monty']) in Assert(d.lists())

    @test
    def update(self):
        d = self.dict_class()
        with Assert.raises(TypeError):
            d.update((1, 2), (3, 4))
        d.update({'foo': 'bar'})
        Assert(d['foo']) == 'bar'
        d.update([('foo', 'spam')])
        Assert(d['foo']) == 'bar'
        Assert(d.getlist('foo')) == ['bar', 'spam']

    @test
    def poplist(self):
        d = self.dict_class({'foo': 'bar', 'spam': ['eggs', 'monty']})
        Assert(d.poplist('foo')) == ['bar']
        Assert(d.poplist('spam')) == ['eggs', 'monty']
        Assert(d.poplist('foo')) == []

    @test
    def popitemlist(self):
        d = self.dict_class({'foo': 'bar'})
        Assert(d.popitemlist()) == ('foo', ['bar'])
        with Assert.raises(KeyError):
            d.popitemlist()
        d = self.dict_class({'foo': ['bar', 'baz']})
        Assert(d.popitemlist()) == ('foo', ['bar', 'baz'])
        with Assert.raises(KeyError):
            d.popitemlist()

    @test
    def repr(self):
        d = self.dict_class()
        Assert(repr(d)) == '%s()' % d.__class__.__name__
        original = {1: [2, 3]}
        d = self.dict_class(original)
        Assert(repr(d)) == '%s(%s)' % (d.__class__.__name__, repr(original))


class TestMultiDict(TestBase, MultiDictTestMixin, DictTestMixin):
    dict_class = MultiDict

    @test_if(GE_PYTHON_26)
    def type_checking(self):
        Assert.isinstance(self.dict_class(), dict)


class ImmutableMultiDictTestMixin(MultiDictTestMixin):
    @test
    def add(self):
        d = self.dict_class()
        with Assert.raises(TypeError):
            d.add(1, 2)

    @test
    def setlist(self):
        d = self.dict_class()
        with Assert.raises(TypeError):
            d.setlist(1, [2, 3])

    @test
    def setlistdefault(self):
        d = self.dict_class()
        with Assert.raises(TypeError):
            d.setlistdefault(1)
        with Assert.raises(TypeError):
            d.setlistdefault(1, [2, 3])

    @test
    def poplist(self):
        for d in (self.dict_class(), self.dict_class({1: [2, 3]})):
            with Assert.raises(TypeError):
                d.poplist(1)

    @test
    def popitemlist(self):
        for d in (self.dict_class(), self.dict_class({1: [2, 3]})):
            with Assert.raises(TypeError):
                d.popitemlist()

    @test
    def update(self):
        d = self.dict_class()
        with Assert.raises(TypeError):
            d.update({1: 2})
        with Assert.raises(TypeError):
            d.update(foo='bar')


class TestImmutableMultiDict(TestBase, ImmutableMultiDictTestMixin,
                             ImmutableDictTestMixin):
    dict_class = ImmutableMultiDict

    @test_if(GE_PYTHON_26)
    def type_checking(self):
        d = self.dict_class()
        types = [dict, ImmutableDict, MultiDict]
        for type in types:
            Assert.isinstance(d, type), type

    @test
    def hashability(self):
        d = self.dict_class({1: [2, 3]})
        Assert(hash(d)) == hash(self.dict_class(d))
        with Assert.raises(TypeError):
            hash(self.dict_class({1: [[]]}))


class TestCombinedMultiDict(TestBase, CombinedDictTestMixin,
                            ImmutableMultiDictTestMixin,
                            ImmutableDictTestMixin):
    dict_class = CombinedMultiDict

    # we don't need this special kind of initalization
    init_with_lists = None

    @test
    def getlist(self):
        d = self.dict_class()
        Assert(d.getlist(1)) == []
        d = self.dict_class([MultiDict({1: 2}), MultiDict({1: 3})])
        Assert(d.getlist(1)) == [2, 3]

    @test
    def lists(self):
        d = self.dict_class([
            MultiDict({'foo': ['bar', 'baz']}),
            MultiDict({'foo': ['spam', 'eggs']})
        ])
        Assert(list(d.iterlists())) == d.lists()
        Assert(d.lists()) == [('foo', ['bar', 'baz', 'spam', 'eggs'])]

    @test
    def listvalues(self):
        d = self.dict_class([
            MultiDict({'foo': ['bar', 'baz']}),
            MultiDict({'foo': ['spam', 'eggs']})
        ])
        Assert(list(d.iterlistvalues())) == d.listvalues()
        Assert(d.listvalues()) == [['bar', 'baz', 'spam', 'eggs']]

    @test
    def multi_items(self):
        d = self.dict_class([
            MultiDict({'foo': ['bar', 'baz']}),
            MultiDict({'foo': ['spam', 'eggs']})
        ])
        Assert(list(d.iteritems(multi=True))) == d.items(multi=True)
        Assert(d.items(multi=True)) == [
            ('foo', ['bar', 'baz', 'spam', 'eggs'])
        ]

    @test
    def item_accessor_equality(self):
        CombinedDictTestMixin.item_accessor_equality(self)
        d = self.dict_class([
            MultiDict({'foo': ['bar', 'baz']}),
            MultiDict({'foo': ['spam', 'eggs']})
        ])
        Assert(d.values()) == [d['foo']]
        Assert(d.lists()) == [(key, d.getlist(key)) for key in d]
        Assert(d.items()) == [(k, vs[0]) for k, vs in d.lists()]

    @test_if(GE_PYTHON_26)
    def type_checking(self):
        types = [dict, ImmutableDict, MultiDict, ImmutableMultiDict]
        d = self.dict_class()
        for type in types:
            Assert.isinstance(d, type), type


class OrderedDictTestMixin(object):
    dict_class = None

    @test
    def fromkeys_is_ordered(self):
        d = self.dict_class.fromkeys([1, 2])
        Assert(d.items()) == [(1, None), (2, None)]

        d = self.dict_class.fromkeys([1, 2], 'foo')
        Assert(d.items()) == [(1, 'foo'), (2, 'foo')]

    @test
    def init_keeps_ordering(self):
        Assert(self.dict_class([(1, 2), (3, 4)]).items()) == [(1, 2), (3, 4)]

    @test
    def setitem_order(self):
        d = self.dict_class()
        d[1] = 2
        d[3] = 4
        Assert(d.items()) == [(1, 2), (3, 4)]

    @test
    def setdefault_order(self):
        d = self.dict_class()
        d.setdefault(1)
        d.setdefault(3, 4)
        Assert(d.items()) == [(1, None), (3, 4)]

    @test
    def pop_does_not_keep_ordering(self):
        d = self.dict_class([(1, 2), (3, 4)])
        d.pop(3)
        d[5] = 6
        d[3] = 4
        modified = self.dict_class([(1, 2), (5, 6), (3, 4)])
        Assert(d) == modified

    @test
    def popitem(self):
        d = self.dict_class([(1, 2), (3, 4), (5, 6)])
        Assert(d.popitem()) == (5, 6)
        Assert(d.popitem(last=False)) == (1, 2)

    @test
    def move_to_end(self):
        d = self.dict_class([(1, 2), (3, 4), (5, 6)])
        d.move_to_end(1)
        Assert(d.items()) == [(3, 4), (5, 6), (1, 2)]
        d.move_to_end(5, last=False)
        Assert(d.items()) == [(5, 6), (3, 4), (1, 2)]

    @test
    def update_order(self):
        d = self.dict_class()
        d.update([(1, 2), (3, 4)])
        items = Assert(d.items())
        items == [(1, 2), (3, 4)]

    @test
    def clear_does_not_keep_ordering(self):
        d = self.dict_class([(1, 2), (3, 4)])
        d.clear()
        d.update([(3, 4), (1, 2)])
        Assert(d.items()) == [(3, 4), (1, 2)]

    @test
    def repr(self):
        d = self.dict_class()
        Assert(repr(d)) == '%s()' % d.__class__.__name__
        original = [(1, 2), (3, 4)]
        d = self.dict_class(original)
        Assert(repr(d)) == '%s(%s)' % (d.__class__.__name__, repr(original))


class TestOrderedDict(TestBase, OrderedDictTestMixin, DictTestMixin):
    dict_class = OrderedDict

    @test_if(GE_PYTHON_26)
    def type_checking(self):
        d = self.dict_class()
        Assert.isinstance(d, dict)


class ImmutableOrderedDictTextMixin(OrderedDictTestMixin):
    update_order = setitem_order = setdefault_order = \
        pop_does_not_keep_ordering = clear_does_not_keep_ordering = None

    @test
    def popitem(self):
        d = self.dict_class()
        with Assert.raises(TypeError):
            d.popitem()
        d = self.dict_class([(1, 2)])
        with Assert.raises(TypeError):
            d.popitem()

    @test
    def move_to_end(self):
        d = self.dict_class([(1, 2), (3, 4)])
        with Assert.raises(TypeError):
            d.move_to_end(1)


class TestImmutableOrderedDict(TestBase, ImmutableOrderedDictTextMixin,
                               ImmutableDictTestMixin):
    dict_class = ImmutableOrderedDict


    @test_if(GE_PYTHON_26)
    def type_checking(self):
        d = self.dict_class()
        Assert.isinstance(d, OrderedDict)
        Assert.isinstance(d, ImmutableDict)
        Assert.isinstance(d, dict)

    @test
    def hashability(self):
        d = self.dict_class([(1, 2), (3, 4)])
        Assert(hash(d)) == hash(self.dict_class(d))
        Assert(hash(d)) != hash(self.dict_class(reversed(d.items())))
        with Assert.raises(TypeError):
            hash(self.dict_class(foo=[]))


class TestOrderedMultiDict(TestBase, OrderedDictTestMixin, MultiDictTestMixin,
                           DictTestMixin):
    dict_class = OrderedMultiDict

    @test_if(GE_PYTHON_26)
    def type_checking(self):
        d = self.dict_class()
        types = [dict, MultiDict, OrderedDict]
        for type in types:
            Assert.isinstance(d, type), type


class TestImmutableOrderedMultiDict(TestBase, ImmutableOrderedDictTextMixin,
                                    ImmutableMultiDictTestMixin,
                                    ImmutableDictTestMixin):
    dict_class = ImmutableOrderedMultiDict

    @test_if(GE_PYTHON_26)
    def type_checking(self):
        d = self.dict_class()
        types = [dict, ImmutableDict, MultiDict, ImmutableMultiDict,
                 OrderedDict]
        for type in types:
            Assert.isinstance(d, type), type


class TestFixedDict(TestBase, DictTestMixin):
    dict_class = FixedDict

    @test
    def setitem(self):
        d = self.dict_class()
        d[1] = 2
        Assert(d[1]) == 2
        with Assert.raises(KeyError):
            d[1] = 3

    @test
    def update(self):
        d = self.dict_class()
        d.update({1: 2})
        Assert(d[1]) == 2
        with Assert.raises(KeyError):
            d.update({1: 3})


class TestCounter(TestBase):
    @test
    def missing(self):
        c = Counter()
        Assert(c['a']) == 0

    @test
    def get(self):
        c = Counter('a')
        Assert(c.get('a')) == 1
        Assert(c.get('b')) == 0

    @test
    def setdefault(self):
        c = Counter('a')
        Assert(c.setdefault('a', 2)) == 1
        Assert(c['a']) == 1
        Assert(c.setdefault('b')) == 1
        Assert(c['b']) == 1

    @test
    def most_common(self):
        c = Counter('aababc')
        result = [('a', 3), ('b', 2), ('c', 1)]
        Assert(c.most_common()) == result
        Assert(c.most_common(2)) == result[:-1]
        Assert(c.most_common(1)) == result[:-2]
        Assert(c.most_common(0)) == []

    @test
    def elements(self):
        c = Counter('aababc')
        for element in c:
            Assert(list(c.elements()).count(element)) == c[element]

    @test
    def update(self):
        c = Counter()
        c.update('aababc')
        Assert(c) == Counter('aababc')
        c.update({'b': 1})
        Assert(c['b']) == 3
        c.update(c=2)
        Assert(c['c']) == 3

    @test
    def add(self):
        c = Counter('aababc')
        new = c + c
        Assert(new['a']) == 6
        Assert(new['b']) == 4
        Assert(new['c']) == 2

    @test
    def mul(self):
        c = Counter('abc')
        Assert(c * 2) == c + c

    @test
    def sub(self):
        c = Counter('aababc')
        assert not c - c

    @test
    def or_and(self):
        c1 = Counter('abc')
        new = c1 | c1 * 2
        Assert(new.values()) == [2] * 3
        new = c1 & c1 * 2
        Assert(new.values()) == [1] * 3


tests = Tests([
    TestImmutableDict, TestCombinedDict, TestMultiDict, TestImmutableMultiDict,
    TestCombinedMultiDict, TestOrderedDict, TestOrderedMultiDict,
    TestImmutableOrderedDict, TestImmutableOrderedMultiDict, TestFixedDict,
    TestCounter
])

########NEW FILE########
__FILENAME__ = queues
# coding: utf-8
"""
    brownie.tests.datastructures.queues
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Tests for :mod:`brownie.datastructures.queues`.

    :copyright: 2010-2011 by Daniel Neuhäuser
    :license: BSD, see LICENSE.rst for details
"""
from __future__ import with_statement
from threading import Thread

from attest import Tests, TestBase, test, Assert

from brownie.datastructures import SetQueue


class TestSetQueue(TestBase):
    @test
    def ordering_behaviour(self):
        class QueuedItem(object):
            def __init__(self, a, b):
                self.a, self.b = a, b

            @property
            def _key(self):
                return self.a, self.b

            def __eq__(self, other):
                return self._key == other._key

            def __ne__(self, other):
                return self._key != other._key

            def __hash__(self):
                return hash(self._key)

        foo = QueuedItem('foo', 'bar')
        bar = QueuedItem('foo', 'bar')
        item_list = [
            foo,
            foo,
            foo,
            foo,
            bar,
            bar,
            foo,
            foo,
            foo,
            bar,
            bar,
            bar,
            foo,
            foo,
            foo,
            foo,
            bar,
            bar
        ]
        item_set = set(item_list)
        queue = SetQueue()
        for item in item_list:
            queue.put(item)

        def item_consumer(tasks):
            item_list = []
            while True:
                try:
                    item = tasks.get(timeout=0.2)
                    item_list.append(item)
                    tasks.task_done()
                except queue.Empty:
                    break

            Assert(len(item_list)) == 2
            Assert(set(item_list)) == item_set
            Assert(item_list[0]) == foo
            Assert(item_list[1]) == bar

        consumer = Thread(target=item_consumer, args=(queue, ))
        consumer.start()
        consumer.join()


tests = Tests([TestSetQueue])

########NEW FILE########
__FILENAME__ = sequences
# coding: utf-8
"""
    brownie.tests.datastructures.sequences
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Tests for :mod:`brownie.datastructures.sequences`.

    :copyright: 2010-2011 by Daniel Neuhäuser
    :license: BSD, see LICENSE.rst for details
"""
from __future__ import with_statement
import sys
import pickle
import random
from StringIO import StringIO
from itertools import repeat
from contextlib import contextmanager

from attest import Tests, TestBase, test, Assert

from brownie.datastructures import (LazyList, CombinedSequence, CombinedList,
                                    namedtuple)


@contextmanager
def capture_output():
    stdout, stderr = sys.stdout, sys.stderr
    sys.stdout, sys.stdout = StringIO(), StringIO()
    try:
        yield sys.stdout, sys.stderr
    finally:
        sys.stdout, sys.stderr = stdout, stderr


class TestLazyList(TestBase):
    def _genrange(self, *args):
        """xrange() implementation which doesn't have like a sequence."""
        if len(args) == 1:
            start = 0
            stop = args[0]
            step = 1
        elif len(args) == 2:
            start, stop = args
            step = 1
        elif len(args) == 3:
            start, stop, step = args
        else:
            raise ValueError()
        i = start
        while i < stop:
            yield i
            i += step

    @test
    def _test_genrange(self):
        tests = [
            (10, ),
            (10, 20),
            (10, 20, 2)
        ]
        for test in tests:
            Assert(list(self._genrange(*test))) == range(*test)

    @test
    def factory(self):
        foo = LazyList.factory(xrange)
        Assert(foo(10).__class__).is_(LazyList)
        Assert(foo(10)) == range(10)

    @test
    def exhausted(self):
        l = LazyList(range(10))
        Assert(l.exhausted) == True
        l = LazyList(self._genrange(10))
        Assert(l.exhausted) == False
        l[-1]
        Assert(l.exhausted) == True

    @test
    def iteration(self):
        for l in [range(10), self._genrange(10)]:
            l = LazyList(l)
            result = []
            for item in l:
                result.append(item)
            Assert(result) == range(10)

    @test
    def append(self):
        data = self._genrange(10)
        l = LazyList(data)
        l.append(10)
        Assert(l.exhausted) == False
        Assert(l) == range(11)

    @test
    def extend(self):
        data = self._genrange(10)
        l = LazyList(data)
        l.extend(range(10, 20))
        Assert(l.exhausted) == False
        Assert(l) == range(10) + range(10, 20)

    @test
    def insert(self):
        data = self._genrange(10)
        l = LazyList(data)
        l.insert(5, 'foobar')
        Assert(l[5]) == 'foobar'
        Assert(l.exhausted) == False
        l.insert(-3, 'spam')
        Assert(l[-4]) == 'spam'

    @test
    def pop(self):
        data = xrange(10)
        l = LazyList(data)
        Assert(l.pop()) == 9
        Assert(l.pop(0)) == 0

    @test
    def remove(self):
        data = range(10)
        l = LazyList(self._genrange(10))
        data.remove(2)
        l.remove(2)
        Assert(l.exhausted) == False
        Assert(l) == data

        with Assert.raises(ValueError):
            l.remove('foo')

    @test
    def reverse(self):
        data = range(10)
        l = LazyList(reversed(data))
        l.reverse()
        Assert(l) == data

    @test
    def sort(self):
        data = range(10)
        random.choice(data)
        l = LazyList(data)
        l.sort()
        data.sort()
        Assert(l) == data

    @test
    def count(self):
        l = LazyList(['a', 'b', 'c', 'a'])
        tests = [('a', 2), ('b', 1), ('c', 1)]
        for test, result in tests:
            Assert(l.count(test)) == result

    @test
    def index(self):
        l = LazyList(self._genrange(10))
        Assert(l.index(5)) == 5
        with Assert.raises(ValueError):
            l.index('foo')

    @test
    def getitem(self):
        data = range(10)
        l = LazyList(data)
        for a, b in zip(data, l):
            Assert(a) == b
        l = LazyList(self._genrange(10))
        l[5]
        Assert(l.exhausted) == False
        l = LazyList(self._genrange(10))
        Assert(l[-1]) == 9

    @test
    def getslice(self):
        data = range(10)
        l = LazyList(self._genrange(10))
        Assert(data[3:6]) == l[3:6]
        Assert(l.exhausted) == False

        l = LazyList(self._genrange(10))
        Assert(data[:-1]) == l[:-1]

    @test
    def setitem(self):
        data = ['foo', 'bar', 'baz']
        l = LazyList(iter(data))
        l[0] = 'spam'
        Assert(l.exhausted) == False
        Assert(l[0]) == 'spam'
        Assert(l) != data

    @test
    def setslice(self):
        data = range(10)
        replacement = ['foo', 'bar', 'baz']
        l = LazyList(self._genrange(10))
        l[3:6] = replacement
        data[3:6] = replacement
        Assert(l.exhausted) == False
        Assert(l) == data

    @test
    def delitem(self):
        data = range(10)
        l = LazyList(data[:])
        del data[0]
        del l[0]
        Assert(l) == data
        l = LazyList(self._genrange(10))
        del l[2]
        Assert(l.exhausted) == False

    @test
    def delslice(self):
        data = range(10)
        l = LazyList(self._genrange(10))
        del data[3:6]
        del l[3:6]
        Assert(l.exhausted) == False
        Assert(l) == data

    @test
    def len(self):
        Assert(len(LazyList(range(10)))) == 10

        l = LazyList([])
        Assert(len(l)) == 0

        l.append(1)
        Assert(len(l)) == 1

        l.extend([2, 3])
        Assert(len(l)) == 3

        l.pop()
        Assert(len(l)) == 2

        del l[1]
        Assert(len(l)) == 1

    @test
    def contains(self):
        l = LazyList(self._genrange(10))
        Assert(5).in_(l)
        Assert('foo').not_in(l)

        class Foo(object):
            def __eq__(self, other):
                raise ValueError()
        l = LazyList([Foo()])
        with Assert.raises(ValueError):
            Assert(1).not_in(l)

    @test
    def equals(self):
        Assert(LazyList(range(10))) == range(10)
        Assert(LazyList(range(10))) == LazyList(range(10))

        Assert(LazyList(range(10)) != range(10)) == False
        Assert(LazyList(range(10)) != range(10)) == False

        Assert(LazyList(range(10)) == range(20)) == False
        Assert(LazyList(range(10)) == LazyList(range(20))) == False

        Assert(LazyList(range(10))) != range(20)
        Assert(LazyList(range(10))) != range(20)

        l = LazyList(self._genrange(10))
        Assert(l == range(20)) == False

    @test
    def boolean(self):
        Assert(bool(LazyList([]))) == False
        Assert(bool(LazyList([1]))) == True

    @test
    def lower_greater_than(self):
        Assert(LazyList([]) < LazyList([])) == False
        Assert(LazyList([]) > LazyList([])) == False

        tests = [
            ([], [1]),
            ([1], [2]),
            ([1, 2], [2, 1]),
            ([2, 1], [2, 2])
        ]
        for a, b in tests:
            Assert(LazyList(a) < LazyList(b)) == True
            Assert(LazyList(a) > LazyList(b)) == False

            Assert(LazyList(b) < LazyList(a)) == False
            Assert(LazyList(b) > LazyList(a)) == True

        a = LazyList(iter([1, 2, 3]))
        b = LazyList(iter([1, 3, 3]))

        Assert(a) < b
        Assert(b) > a

        Assert(LazyList([1, 2])) < [1, 2, 3]
        Assert(LazyList([1, 2, 3])) > [1, 2]

    @test
    def add(self):
        Assert(LazyList([1, 2]) + [3, 4]) == LazyList([1, 2, 3, 4])
        Assert(LazyList([1, 2]) + LazyList([3, 4])) == LazyList([1, 2, 3, 4])

    @test
    def inplace_add(self):
        old = l = LazyList([1, 2])
        l += [3, 4]
        l += (5, 6)
        Assert(l) == LazyList([1, 2, 3, 4, 5, 6])
        Assert(l).is_(old)

    @test
    def multiply(self):
        a = LazyList(self._genrange(10))
        b = range(10)
        Assert(a * 5) == b * 5

    @test
    def inplace_multiply(self):
        old = a = LazyList(self._genrange(10))
        b = range(10)
        a *= 5
        b *= 5
        Assert(a) == b
        Assert(a).is_(old)

    @test
    def repr(self):
        Assert(repr(LazyList([]))) == '[]'
        data = range(10)
        l = LazyList(self._genrange(10))
        Assert(repr(l)) == '[...]'
        l[1]
        Assert(repr(l)) == '[0, 1, ...]'
        l[-1]
        Assert(repr(l)) == repr(data)

    @test
    def picklability(self):
        l = LazyList(self._genrange(10))
        pickled = pickle.loads(pickle.dumps(l))
        Assert(pickled) == l
        Assert(pickled.__class__) == l.__class__


class CombinedSequenceTestMixin(object):
    sequence_cls = None

    @test
    def at_index(self):
        foo = [1, 2, 3]
        bar = [4, 5, 6]
        s = self.sequence_cls([foo, bar])

        for iterator in xrange(len(s) - 1), xrange(0, -len(s), -1):
            for i in iterator:
                list, index = s.at_index(i)
                if 0 <= i <= 2 or -6 <= i <= -3:
                    Assert(list).is_(foo)
                    Assert(foo[index]) == s[i]
                else:
                    Assert(list).is_(bar)
                    Assert(bar[index]) == s[i]

    @test
    def getitem(self):
        s = self.sequence_cls([[0, 1, 2], [3, 4, 5]])
        for a, b, item in zip(xrange(len(s) - 1), xrange(-len(s)), range(6)):
            Assert(s[a]) == s[b] == item

    @test
    def getslice(self):
        s = self.sequence_cls([[0, 1, 2], [3, 4, 5]])
        Assert(s[:]) == range(6)
        Assert(s[:3]) == s[:-3] == [0, 1, 2]
        Assert(s[3:]) == s[-3:] == [3, 4, 5]
        Assert(s[2:]) == [2, 3, 4, 5]
        Assert(s[-2:]) == [4, 5]

    @test
    def len(self):
        tests = [
            ([], 0),
            ([[]], 0),
            ([[], []], 0),
            ([[1, 2], [3, 4]], 4)
        ]
        for args, result in tests:
            Assert(len(self.sequence_cls(args))) == result

    @test
    def iteration(self):
        s = self.sequence_cls([[0, 1, 2], [3, 4, 5]])
        for expected, item in zip(range(6), s):
            Assert(expected) == item
        for expected, item in zip(range(5, 0, -1), reversed(s)):
            Assert(expected) == item

    @test
    def equality(self):
        s = self.sequence_cls([[0, 1, 2], [3, 4, 5]])
        Assert(s) == self.sequence_cls(s.sequences)
        Assert(s) != self.sequence_cls([[]])

    @test
    def picklability(self):
        s = self.sequence_cls([[0, 1, 2], [3, 4, 5]])
        pickled = pickle.loads(pickle.dumps(s))
        Assert(pickled) == s
        Assert(pickled.__class__).is_(self.sequence_cls)

    @test
    def multiplication(self):
        s = self.sequence_cls([[0, 1, 2], [3, 4, 5]])
        Assert(s * 2) == 2 * s == [0, 1, 2, 3, 4, 5] * 2
        with Assert.raises(TypeError):
            s * []


class TestCombinedSequence(TestBase, CombinedSequenceTestMixin):
    sequence_cls = CombinedSequence


class TestCombinedList(TestBase, CombinedSequenceTestMixin):
    sequence_cls = CombinedList

    @test
    def count(self):
        s = self.sequence_cls([[1, 1, 2], [3, 1, 4]])
        Assert(s.count(1)) == 3
        Assert(s.count(2)) == s.count(3) == s.count(4) == 1

    @test
    def index(self):
        s = self.sequence_cls([[1, 1, 2], [3, 1, 4]])
        Assert(s.index(1)) == 0
        Assert(s.index(1, 1)) == 1
        Assert(s.index(1, 2)) == 4
        with Assert.raises(ValueError):
            s.index(1, 2, 3)

    @test
    def setitem(self):
        foo, bar = [0, 1, 2], [3, 4, 5]
        s = self.sequence_cls([foo, bar])
        s[0] = 'foo'
        Assert(s[0]) == foo[0] == 'foo'

    @test
    def setslice(self):
        foo, bar = [0, 1, 2], [3, 4, 5]
        s = self.sequence_cls([foo, bar])
        s[:3] = 'abc'
        Assert(s) == ['a', 'b', 'c', 3, 4, 5]
        Assert(foo) == ['a', 'b', 'c']
        s[::2] = repeat(None)
        Assert(s) == [None, 'b', None, 3, None, 5]

    @test
    def delitem(self):
        foo, bar = [0, 1, 2], [3, 4, 5]
        s = self.sequence_cls([foo, bar])
        del s[0]
        Assert(s) == [1, 2, 3, 4, 5]
        Assert(foo) == [1, 2]

    @test
    def delslice(self):
        foo, bar = [0, 1, 2], [3, 4, 5]
        s = self.sequence_cls([foo, bar])
        del s[2:4]
        Assert(s) == [0, 1, 4, 5]
        Assert(foo) == [0, 1]
        Assert(bar) == [4, 5]

    @test
    def append(self):
        foo, bar = [0, 1, 2], [3, 4, 5]
        s = self.sequence_cls([foo, bar])
        s.append(6)
        Assert(s[-1]) == bar[-1] == 6

    @test
    def extend(self):
        foo, bar = [0, 1, 2], [3, 4, 5]
        s = self.sequence_cls([foo, bar])
        s.extend([6, 7])
        Assert(s[-2:]) == bar[-2:] == [6, 7]

    @test
    def insert(self):
        foo, bar = [0, 1, 2], [3, 4, 5]
        s = self.sequence_cls([foo, bar])
        s.insert(1, 6)
        Assert(s[:4]) == foo == [0, 6, 1, 2]
        Assert(bar) == [3, 4, 5]

    @test
    def pop(self):
        s = self.sequence_cls([])
        with Assert.raises(IndexError):
            s.pop()
        s = self.sequence_cls([[0, 1, 2]])
        with Assert.raises(IndexError):
            s.pop(3)
        Assert(s.pop()) == 2
        Assert(s.pop(0)) == 0

    @test
    def remove(self):
        s = self.sequence_cls([])
        with Assert.raises(ValueError):
            s.remove(1)
        s = self.sequence_cls([[1, 1]])
        s.remove(1)
        Assert(s) == [1]
        s = self.sequence_cls([[1, 2], [1, 2]])
        s.remove(1)
        Assert(s) == [2, 1, 2]
        s = self.sequence_cls([[2], [1, 2]])
        s.remove(1)
        Assert(s) == [2, 2]

    @test
    def reverse(self):
        foo, bar = [1, 2, 3], [4, 5, 6]
        s = self.sequence_cls([foo, bar])
        s.reverse()
        Assert(s) == [6, 5, 4, 3, 2, 1]
        Assert(foo) == [6, 5, 4]
        Assert(bar) == [3, 2, 1]

    @test
    def sort(self):
        foo, bar = [3, 1, 2], [4, 6, 5]
        s = self.sequence_cls([foo, bar])
        s.sort()
        Assert(s) == [1, 2, 3, 4, 5, 6]
        Assert(foo) == [1, 2, 3]
        Assert(bar) == [4, 5, 6]


class TestNamedTuple(TestBase):
    @test
    def docstring(self):
        nt = namedtuple('foo', 'foo bar')
        Assert(nt.__doc__) == 'foo(foo, bar)'

        nt = namedtuple('foo', 'foo bar', doc='hello user')
        Assert(nt.__doc__) == 'hello user'

    @test
    def string_field_names(self):
        nt = namedtuple('foo', 'foo bar')
        Assert(nt._fields) == ('foo', 'bar')
        nt = namedtuple('foo', 'foo,bar')
        Assert(nt._fields) == ('foo', 'bar')

    @test
    def typename(self):
        nt = namedtuple('foo', [])
        Assert(nt.__name__) == 'foo'
        with Assert.raises(ValueError):
            namedtuple('def', [])

    @test
    def fieldnames(self):
        with Assert.raises(ValueError):
            nt = namedtuple('foo', ['foo', 'bar', 'def'])

        with Assert.raises(ValueError):
            nt = namedtuple('foo', ['foo', 'bar', 'foo'])

        nt = namedtuple('foo', ['spam', 'eggs'])
        Assert(nt._fields) == ('spam', 'eggs')

        nt = namedtuple('foo', ['foo', 'bar', 'def'], rename=True)
        Assert(nt._fields) == ('foo', 'bar', '_1')
        Assert(nt(1, 2, 3)._1) == 3

        nt = namedtuple('foo', ['foo', 'bar', 'foo'], rename=True)
        Assert(nt._fields) == ('foo', 'bar', '_1')
        Assert(nt(1, 2, 3)._1) == 3

    @test
    def renaming(self):
        nt = namedtuple('foo', ['foo', 'foo', 'foo'], rename=True)
        t = nt(1, 2, 3)
        Assert(t.foo) == 1
        Assert(t._1) == 2
        Assert(t._2) == 3

    @test
    def repr(self):
        nt = namedtuple('foo', ['spam', 'eggs'])
        Assert(nt(1, 2)) == (1, 2)
        Assert(repr(nt(1, 2))) == 'foo(spam=1, eggs=2)'

    @test
    def _make(self):
        nt = namedtuple('foo', ['spam', 'eggs'])
        Assert(nt._make((1, 2))) == (1, 2)
        with Assert.raises(TypeError):
            nt._make((1, 2, 3))

    @test
    def _asdict(self):
        nt = namedtuple('foo', ['spam', 'eggs'])
        Assert(nt(1, 2)._asdict()) == {'spam': 1, 'eggs': 2}

    @test
    def _replace(self):
        nt = namedtuple('foo', ['spam', 'eggs'])
        t = nt(1, 2)
        Assert(t._replace(spam=3)) == (3, 2)
        Assert(t._replace(eggs=4)) == (1, 4)
        with Assert.raises(ValueError):
            t._replace(foo=1)

    @test
    def verbose(self):
        with capture_output() as (stdout, stderr):
            namedtuple('foo', 'spam eggs', verbose=True)
        assert not stderr.getvalue()
        namespace = {}
        exec stdout.getvalue() in namespace
        Assert('foo').in_(namespace)
        Assert(namespace['foo'].__name__) == 'foo'
        Assert(namespace['foo']._fields) == ('spam', 'eggs')


tests = Tests([TestLazyList, TestCombinedSequence, TestCombinedList, TestNamedTuple])

########NEW FILE########
__FILENAME__ = sets
# coding: utf-8
"""
    brownie.tests.datastructures.sets
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Tests for :mod:`brownie.datastructures.sets`.

    :copyright: 2010-2011 by Daniel Neuhäuser
    :license: BSD, see LICENSE.rst for details
"""
from __future__ import with_statement

from attest import Tests, TestBase, test, Assert

from brownie.datastructures import OrderedSet


class TestOrderedSet(TestBase):
    @test
    def length(self):
        Assert(len(OrderedSet([1, 2, 3]))) == 3

    @test
    def contains(self):
        s = OrderedSet([1, 2, 3])
        for element in s:
            Assert(element).in_(s)
        Assert(4).not_in(s)

    @test
    def add(self):
        s = OrderedSet()
        s.add(1)
        Assert(1).in_(s)

    @test
    def remove(self):
        s = OrderedSet()
        with Assert.raises(KeyError):
            s.remove(1)
        s.add(1)
        s.remove(1)

    @test
    def discard(self):
        s = OrderedSet()
        s.discard(1)
        s.add(1)
        s.discard(1)
        Assert(1).not_in(s)

    @test
    def pop(self):
        s = OrderedSet()
        with Assert.raises(KeyError):
            s.pop()
        s = OrderedSet([1, 2, 3])
        Assert(s.pop()) == 3
        Assert(s.pop(last=False)) == 1

    @test
    def clear(self):
        s = OrderedSet([1, 2, 3])
        s.clear()
        assert not s

    @test
    def update(self):
        s = OrderedSet()
        s.update('abc')
        Assert(s) == OrderedSet('abc')

    @test
    def copy(self):
        s = OrderedSet('abc')
        Assert(s.copy()) == s
        Assert(s.copy()).is_not(s)

    @test
    def inplace_update(self):
        old = s = OrderedSet()
        with Assert.raises(TypeError):
            s |= 'abc'
        s |= OrderedSet('abc')
        Assert(s) == OrderedSet('abc')
        Assert(s).is_(old)

    @test
    def issub_super_set(self):
        a = OrderedSet('abc')
        b = OrderedSet('abcdef')

        a.issubset(a)
        a.issuperset(a)
        a.issubset(a)
        a.issuperset(a)

        assert a <= a
        assert a >= a

        assert a <= b
        assert b >= a

        assert not (a < a)
        assert not (a > a)

        assert a < b
        assert not (a > b)

    @test
    def union(self):
        a = OrderedSet('abc')
        b = OrderedSet('def')
        Assert(a.union('def', 'ghi')) == OrderedSet('abcdefghi')
        Assert(a | b) == OrderedSet('abcdef')
        with Assert.raises(TypeError):
            a | 'abc'

    @test
    def intersection(self):
        a = OrderedSet('abc')
        Assert(a.intersection('ab', 'a')) == OrderedSet('a')
        Assert(a & OrderedSet('ab')) == OrderedSet('ab')
        with Assert.raises(TypeError):
            a & 'ab'

    @test
    def intersection_update(self):
        old = s = OrderedSet('abc')
        with Assert.raises(TypeError):
            s &= 'ab'
        s &= OrderedSet('ab')
        Assert(s) == OrderedSet('ab')
        Assert(s).is_(old)

    @test
    def difference(self):
        a = OrderedSet('abc')
        Assert(a.difference('abc')) == OrderedSet()
        Assert(a.difference('a', 'b', 'c')) == OrderedSet()
        Assert(a - OrderedSet('ab')) == OrderedSet('c')
        with Assert.raises(TypeError):
            a - 'abc'

    @test
    def difference_update(self):
        s = OrderedSet('abcd')
        s -= s
        Assert(s) == OrderedSet()

        old = s = OrderedSet('abcd')
        s -= OrderedSet('abc')
        with Assert.raises(TypeError):
            s -= 'abc'
        Assert(s) == OrderedSet('d')
        Assert(s).is_(old)

    @test
    def symmetric_difference(self):
        for a, b in [('abc', 'def'), ('def', 'abc')]:
            OrderedSet(a).symmetric_difference(b) == OrderedSet(a + b)
            OrderedSet(a) ^ OrderedSet(b) == OrderedSet(a + b)

            OrderedSet(a).symmetric_difference(a + b) == OrderedSet(b)
            OrderedSet(a) ^ OrderedSet(a + b) == OrderedSet(b)

        with Assert.raises(TypeError):
            OrderedSet('abc') ^ 'def'

    @test
    def symmetric_difference_update(self):
        old = s = OrderedSet('abc')
        s ^= OrderedSet('def')
        Assert(s) == OrderedSet('abcdef')
        Assert(s).is_(old)
        with Assert.raises(TypeError):
            s ^= 'ghi'

    @test
    def iteration(self):
        s = OrderedSet([1, 2, 3])
        Assert(list(s)) == [1, 2, 3]
        Assert(list(reversed(s))) == [3, 2, 1]

    @test
    def equality(self):
        a = OrderedSet([1, 2, 3])
        b = OrderedSet([3, 2, 1])
        Assert(a) == a
        Assert(a) == set(b)
        Assert(b) == b
        Assert(b) == set(a)
        Assert(a) != b

    @test
    def hashability(self):
        with Assert.raises(TypeError):
            hash(OrderedSet())

    @test
    def repr(self):
        Assert(repr(OrderedSet())) == 'OrderedSet()'
        s = OrderedSet([1, 2, 3])
        Assert(repr(s)) == 'OrderedSet([1, 2, 3])'


tests = Tests([TestOrderedSet])

########NEW FILE########
__FILENAME__ = signature
# coding: utf-8
"""
    brownie.tests.functional.signature
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Tests for :class:`brownie.functional.Signature`.

    :copyright: 2010-2011 by Daniel Neuhäuser
    :license: BSD, see LICENSE.rst for details
"""
from __future__ import with_statement
import re

from attest import Tests, Assert, TestBase, test

from brownie.functional import Signature


class TestFromFunction(TestBase):
    @test
    def positionals(self):
        func = lambda a, b, c: None
        Assert(Signature.from_function(func)) == (['a', 'b', 'c'], [], None, None)

    @test
    def keyword_arguments(self):
        func = lambda a=1, b=2, c=3: None
        Assert(Signature.from_function(func)) == (
            [], [('a', 1), ('b', 2), ('c', 3)], None, None
        )

    @test
    def mixed_positionals_keyword_arguments(self):
        func = lambda a, b, c=3: None
        Assert(Signature.from_function(func)) == (
            ['a', 'b'], [('c', 3)], None, None
        )
        func = lambda a, b, c=3, d=4: None
        Assert(Signature.from_function(func)) == (
            ['a', 'b'], [('c', 3), ('d', 4)], None, None
        )

    @test
    def arbitary_positionals(self):
        foo = lambda *foo: None
        bar = lambda *bar: None
        for func, name in [(foo, 'foo'), (bar, 'bar')]:
            Assert(Signature.from_function(func)) == ([], [], name, None)

    @test
    def arbitary_keyword_arguments(self):
        spam = lambda **spam: None
        eggs = lambda **eggs: None
        for func, name in [(spam, 'spam'), (eggs, 'eggs')]:
            Assert(Signature.from_function(func)) == ([], [], None, name)


class TestBindArguments(TestBase):
    @test
    def arguments_no_args(self):
        sig = Signature.from_function(lambda: None)

        Assert(sig.bind_arguments()) == {}

        with Assert.raises(ValueError) as exc:
            sig.bind_arguments((1, ), {})
        Assert(exc.args[0]) == 'expected at most 0 positional arguments, got 1'

        tests = [
            ({'a': 1}, "got unexpected keyword argument '.'"),
            ({'a': 1, 'b': 2}, "got unexpected keyword arguments '.' and '.'"),
            (
                {'a': 1, 'b': 2, 'c': 3},
                "got unexpected keyword arguments '.', '.' and '.'"
            )
        ]

        for kwargs, message in tests:
            with Assert.raises(ValueError) as exc:
                sig.bind_arguments(kwargs=kwargs)
            err_msg = exc.args[0].obj
            assert re.match(message, err_msg) is not None
            for name in kwargs:
                assert name in err_msg

    @test
    def arguments_only_positionals(self):
        sig = Signature.from_function(lambda a, b, c: None)

        Assert(sig.bind_arguments((1, 2, 3))) == dict(a=1, b=2, c=3)
        Assert(sig.bind_arguments((1, 2), {'c': 3})) == dict(a=1, b=2, c=3)

        tests = [
            ([('a', 1), ('b', 2)], "'.' is missing"),
            ([('a', 1)], "'.' and '.' are missing"),
            ([], "'.', '.' and '.' are missing")
        ]
        all_names = set('abc')
        for args, message in tests:
            names, values = [], []
            for name, value in args:
                names.append(name)
                values.append(value)

            with Assert.raises(ValueError) as exc_args:
                sig.bind_arguments(values)

            with Assert.raises(ValueError) as exc_kwargs:
                sig.bind_arguments(kwargs=dict(args))

            for exc in [exc_args, exc_kwargs]:
                err_msg = exc.args[0].obj
                assert re.match(message, err_msg) is not None
                for name in all_names.difference(names):
                    assert name in err_msg

        with Assert.raises(ValueError) as exc:
            sig.bind_arguments((1, 2, 3), {'c': 4})
        Assert(exc.args[0]) == "got multiple values for 'c'"

    @test
    def arguments_only_keyword_arguments(self):
        sig = Signature.from_function(lambda a=1, b=2, c=3: None)

        Assert(sig.bind_arguments()) == dict(a=1, b=2, c=3)
        Assert(sig.bind_arguments(('a', ))) == dict(a='a', b=2, c=3)
        Assert(sig.bind_arguments((), {'a': 'a'})) == dict(a='a', b=2, c=3)

    @test
    def arguments_arbitary_positionals(self):
        sig = Signature.from_function(lambda *args: None)

        Assert(sig.bind_arguments()) == {'args': ()}
        Assert(sig.bind_arguments((1, 2, 3))) == {'args': (1, 2, 3)}

    @test
    def arguments_mixed_positionals(self):
        sig = Signature.from_function(lambda a, b, *args: None)

        Assert(sig.bind_arguments((1, 2))) == dict(a=1, b=2, args=())
        Assert(sig.bind_arguments((1, 2, 3))) == dict(a=1, b=2, args=(3, ))
        with Assert.raises(ValueError):
            Assert(sig.bind_arguments())

    @test
    def arguments_arbitary_keyword_arguments(self):
        sig = Signature.from_function(lambda **kwargs: None)

        Assert(sig.bind_arguments()) == {'kwargs': {}}
        Assert(sig.bind_arguments((), {'a': 1})) == {'kwargs': {'a': 1}}

    @test
    def arguments_mixed_keyword_arguments(self):
        sig = Signature.from_function(lambda a=1, b=2, **kwargs: None)

        Assert(sig.bind_arguments()) == dict(a=1, b=2, kwargs={})
        Assert(sig.bind_arguments((3, 4))) == dict(a=3, b=4, kwargs={})
        Assert(sig.bind_arguments((), {'c': 3})) == dict(
            a=1,
            b=2,
            kwargs=dict(c=3)
        )

    @test
    def arguments_mixed_positional_arbitary_keyword_arguments(self):
        sig = Signature.from_function(lambda a, b, **kwargs: None)

        Assert(sig.bind_arguments((1, 2))) == dict(a=1, b=2, kwargs={})
        Assert(sig.bind_arguments((1, 2), {'c': 3})) == dict(
            a=1,
            b=2,
            kwargs=dict(c=3)
        )
        Assert(sig.bind_arguments((), dict(a=1, b=2))) == dict(
            a=1,
            b=2,
            kwargs={}
        )
        with Assert.raises(ValueError):
            sig.bind_arguments()
        with Assert.raises(ValueError):
            sig.bind_arguments((1, 2), {'a': 3})

    @test
    def arguments_mixed_keyword_arguments_arbitary_positionals(self):
        sig = Signature.from_function(lambda a=1, b=2, *args: None)

        Assert(sig.bind_arguments()) == dict(a=1, b=2, args=())
        Assert(sig.bind_arguments((3, 4))) == dict(a=3, b=4, args=())
        Assert(sig.bind_arguments((3, 4, 5))) == dict(a=3, b=4, args=(5, ))
        Assert(sig.bind_arguments((), {'a': 3, 'b': 4})) == dict(
            a=3, b=4, args=()
        )
        with Assert.raises(ValueError):
            sig.bind_arguments((3, ), {'a': 4})


tests = Tests([TestFromFunction, TestBindArguments])

########NEW FILE########
__FILENAME__ = importing
# coding: utf-8
"""
    brownie.tests.importing
    ~~~~~~~~~~~~~~~~~~~~~~~

    Tests for :mod:`brownie.importing`.

    :copyright: 2010-2011 by Daniel Neuhäuser
    :license: BSD, see LICENSE.rst for details
"""
from __future__ import with_statement
from attest import Tests, TestBase, Assert, test

from brownie.importing import import_string


class TestImportString(TestBase):
    @test
    def by_name(self):
        import __main__
        module = import_string('__main__')
        Assert(module).is_(__main__)

    @test
    def by_path(self):
        import brownie.itools
        module = import_string('brownie.itools')
        Assert(module).is_(brownie.itools)

    @test
    def import_object(self):
        from brownie.itools import chain
        func = import_string('brownie.itools.chain')
        Assert(func).is_(chain)

    @test
    def colon_notation(self):
        import brownie.itools
        module = import_string('brownie:itools')
        Assert(module).is_(brownie.itools)

        func = import_string('brownie.itools:chain')
        Assert(func).is_(brownie.itools.chain)

    @test
    def invalid_name(self):
        cases = [
            ('brownie:itools.chain', 'itools.chain'),
            ('brownie-itools:chain', 'brownie-itools')
        ]
        for test, invalid_identifier in cases:
            with Assert.raises(ValueError) as exc:
                import_string(test)
            Assert(invalid_identifier).in_(exc.args[0])

    @test
    def import_non_existing_module(self):
        with Assert.raises(ImportError):
            import_string('foobar')


tests = Tests([TestImportString])

########NEW FILE########
__FILENAME__ = itools
# coding: utf-8
"""
    brownie.tests.itools
    ~~~~~~~~~~~~~~~~~~~~

    Tests for :mod:`brownie.itools`.

    :copyright: 2010-2011 by Daniel Neuhäuser
    :license: BSD, see LICENSE.rst for details
"""
from attest import Tests, Assert

from brownie.itools import (
    izip_longest,
    product,
    compress,
    count,
    permutations,
    combinations_with_replacement,
    starmap,
    grouped,
    unique,
    chain,
    flatten
)


tests = Tests()


@tests.test
def test_chain():
    Assert(list(chain([1, 2], [3, 4]))) == [1, 2, 3, 4]
    Assert(list(chain.from_iterable([[1, 2], [3, 4]]))) == [1, 2, 3, 4]


@tests.test
def test_izip_longest():
    tests = [
        (((['a', 'b'], ['c', 'd']), {}), [('a', 'c'), ('b', 'd')]),
        (((['a'], ['c', 'd']), {}), [('a', 'c'), (None, 'd')]),
        (((['a'], ['c', 'd']), {'fillvalue': 1}), [('a', 'c'), (1, 'd')])
    ]
    for test, result in tests:
        args, kwargs = test
        Assert(list(izip_longest(*args, **kwargs))) == result


@tests.test
def test_permutations():
    tests = [
        ((('abc', )), ['abc', 'acb', 'bac', 'bca', 'cab', 'cba']),
        ((('abc', 1)), ['a', 'b', 'c']),
        ((('abc', 2)), ['ab', 'ac', 'ba', 'bc', 'ca', 'cb']),
        ((('abc', 4)), [])
    ]
    for test, result in tests:
        result = map(tuple, result)
        Assert(list(permutations(*test))) == result


@tests.test
def test_product():
    tests = [
        ((('ABCD', 'xy'), {}), ['Ax', 'Ay', 'Bx', 'By', 'Cx', 'Cy', 'Dx', 'Dy']),
        ((('01', ), {'repeat': 3}), [
            '000', '001', '010', '011', '100', '101', '110', '111'
        ])
    ]
    for test, result in tests:
        args, kwargs = test
        result = map(tuple, result)
        Assert(list(product(*args, **kwargs))) == result


@tests.test
def test_starmap():
    add = lambda a, b: a + b
    Assert(list(starmap(add, [(1, 2), (3, 4)]))) == [3, 7]


@tests.test
def test_combinations_with_replacement():
    tests = [
        (('ABC', 2), ['AA', 'AB', 'AC', 'BB', 'BC', 'CC']),
        (('ABC', 1), ['A', 'B', 'C']),
        (('ABC', 3), [
            'AAA', 'AAB', 'AAC', 'ABB', 'ABC', 'ACC', 'BBB', 'BBC', 'BCC', 'CCC'
        ])
    ]
    for test, result in tests:
        result = map(tuple, result)
        Assert(list(combinations_with_replacement(*test))) == result


@tests.test
def test_compress():
    tests = [
        (('ABCDEF', []), []),
        (('ABCDEF', [0, 0, 0, 0, 0, 0]), []),
        (('ABCDEF', [1, 0, 1, 0, 1, 0]), ['A', 'C', 'E']),
        (('ABCDEF', [0, 1, 0, 1, 0, 1]), ['B', 'D', 'F']),
        (('ABCDEF', [1, 1, 1, 1, 1, 1]), ['A', 'B', 'C', 'D', 'E', 'F'])
    ]
    for test, result in tests:
        Assert(list(compress(*test))) == result


@tests.test
def test_count():
    tests = [
        ((), [0, 1, 2, 3, 4]),
        ((1, ), [1, 2, 3, 4, 5]),
        ((0, 2), [0, 2, 4, 6, 8])
    ]
    for test, result in tests:
        c = count(*test)
        Assert([c.next() for _ in result]) == result


@tests.test
def test_grouped():
    tests = [
        ((0, 'abc'), []),
        ((2, 'abc'), [('a', 'b'), ('c', None)]),
        ((2, 'abc', 1), [('a', 'b'), ('c', 1)])
    ]
    for test, result in tests:
        Assert(list(grouped(*test))) == result


@tests.test
def test_unique():
    tests = [
        ('aabbcc', 'abc'),
        ('aa', 'a'),
        (([1, 2], [1, 2], [3, 4], 5, 5, 5), ([1, 2], [3, 4], 5))
    ]
    for test, result in tests:
        Assert(list(unique(test))) == list(result)

    Assert(list(unique('aaabbbbccc', seen='ab'))) == ['c']


@tests.test
def test_flatten():
    tests = [
        (([1, 2, 3], ), [1, 2, 3]),
        (([1, [2, 3]], ), [1, 2, 3]),
        (([1, [2, [3]]], ), [1, 2, 3]),
        (([1, [2, [3], 4], 5, 6], ), [1, 2, 3, 4, 5, 6]),
        ((['foo', 'bar'], ), ['foo', 'bar']),
        ((['ab', 'cd'], ()), ['a', 'b', 'c', 'd'])
    ]
    for args, result in tests:
        Assert(list(flatten(*args))) == result

########NEW FILE########
__FILENAME__ = parallel
# coding: utf-8
"""
    brownie.tests.parallel
    ~~~~~~~~~~~~~~~~~~~~~~

    Tests for :mod:`brownie.parallel`.

    :copyright: 2010-2011 by Daniel Neuhäuser
    :license: BSD, see LICENSE.rst for details
"""
from __future__ import with_statement
import time
from threading import Thread

from attest import Tests, Assert, TestBase, test

from brownie.parallel import get_cpu_count, AsyncResult, TimeoutError


tests = Tests()


@tests.test
def test_get_cpu_count():
    try:
        Assert(get_cpu_count()) > 0
        Assert(get_cpu_count()) == get_cpu_count()
    except NotImplementedError:
        # make sure default is returned if the number of processes cannot be
        # determined
        Assert(get_cpu_count(2)) == 2


class TestAsyncResult(TestBase):
    @test
    def wait(self):
        aresult = AsyncResult()

        def setter(aresult):
            time.sleep(1)
            aresult.set('foo')
        t = Thread(target=setter, args=(aresult, ))
        t.start()
        with Assert.not_raising(TimeoutError):
            aresult.wait(2)

    @test
    def get(self):
        aresult = AsyncResult()

        with Assert.raises(TimeoutError):
            aresult.get(0.1)

        def setter(aresult):
            time.sleep(1)
            aresult.set('foo')
        t = Thread(target=setter, args=(aresult, ))
        t.start()
        with Assert.not_raising(TimeoutError):
            Assert(aresult.get(2)) == 'foo'

        aresult.set('foo')
        Assert(aresult.get()) == 'foo'

        aresult = AsyncResult()
        aresult.set(ValueError(), success=False)
        with Assert.raises(ValueError):
            aresult.get()

    @test
    def callback_errback(self):
        testruns = (['callback', True], ['errback', False])
        for kwarg, success in testruns:
            l = []
            callback = lambda obj, l=l: l.append(obj)
            aresult = AsyncResult(**{kwarg: callback})
            assert not aresult.ready
            aresult.set('foo', success=success)
            Assert(len(l)) == 1
            Assert(l[0]) == 'foo'

    @test
    def repr(self):
        aresult = AsyncResult()
        Assert(repr(aresult)) == 'AsyncResult()'

        aresult = AsyncResult(callback=1)
        Assert(repr(aresult)) == 'AsyncResult(callback=1)'

        aresult = AsyncResult(errback=1)
        Assert(repr(aresult)) == 'AsyncResult(errback=1)'

        aresult = AsyncResult(callback=1, errback=2)
        Assert(repr(aresult)) == 'AsyncResult(callback=1, errback=2)'

tests.register(TestAsyncResult)

########NEW FILE########
__FILENAME__ = proxies
# coding: utf-8
"""
    brownie.tests.proxies
    ~~~~~~~~~~~~~~~~~~~~~

    :copyright: 2010-2011 by Daniel Neuhäuser
    :license: BSD, see LICENSE.rst for details
"""
import sys

from attest import Tests, TestBase, test, test_if, Assert

from brownie.proxies import as_proxy, get_wrapped, LazyProxy
from brownie.datastructures import missing


GE_PYTHON_26 = sys.version_info >= (2, 6)


tests = Tests()


class TestAsProxy(TestBase):
    @test
    def default_repr(self):
        proxy_cls = as_proxy(type('FooProxy', (object, ), {}))
        Assert(repr(proxy_cls(1))) == '1'

    @test
    def setting_repr(self):
        class FooProxy(object):
            def repr(self, proxied):
                return 'FooProxy(%s)' % repr(proxied)
        FooProxy = as_proxy(FooProxy)

        p = FooProxy(1)
        Assert(repr(p)) == 'FooProxy(1)'

    @test
    def default_attribute_handling(self):
        proxy_cls = as_proxy(type('FooProxy', (object, ), {}))

        class Foo(object):
            a = 1

        proxy = proxy_cls(Foo())
        Assert(proxy.a) == 1
        proxy.a = 2
        Assert(proxy.a) == 2

    @test
    def attribute_handling(self):
        getattr_access = []
        setattr_access = []

        class FooProxy(object):
            def getattr(self, proxied, name):
                getattr_access.append(name)
                return getattr(proxied, name)

            def setattr(self, proxied, name, obj):
                setattr_access.append((name, obj))
                return setattr(proxied, name, obj)

        FooProxy = as_proxy(FooProxy)

        class Foo(object):
            a = 1

        proxy = FooProxy(Foo())
        Assert(proxy.a) == 1
        proxy.a = 2
        Assert(getattr_access) == ['a']
        Assert(setattr_access) == [('a', 2)]

    @test
    def default_special_method_handling(self):
        proxy_cls = as_proxy(type('FooProxy', (object, ), {}))
        proxy = proxy_cls(1)
        Assert(proxy + 1) == 2

    @test
    def special_method_handling(self):
        def simple_method_handler(
                    self, proxied, name, get_result, *args, **kwargs
                ):
            method_calls.append((name, args, kwargs))
            return missing

        def advanced_method_handler(
                    self, proxied, name, get_result, *args, **kwargs
                ):
            method_calls.append((name, args, kwargs))
            return get_result(proxied, *args, **kwargs)

        for handler in [simple_method_handler, advanced_method_handler]:
            class FooProxy(object):
                method = handler
            FooProxy = as_proxy(FooProxy)
            method_calls = []

            proxy = FooProxy(1)
            Assert(proxy + 1) == 2
            Assert(proxy - 1) == 0
            Assert(proxy * 1) == 1
            Assert(proxy / 1) == 1
            Assert(proxy < 1) == False
            Assert(method_calls) == [
                ('__add__', (1, ), {}),
                ('__sub__', (1, ), {}),
                ('__mul__', (1, ), {}),
                ('__div__', (1, ), {}),
                ('__lt__', (1, ), {})
            ]

    @test
    def proper_wrapping(self):
        class FooProxy(object):
            """A little bit of documentation."""
        proxy_cls = as_proxy(FooProxy)
        Assert(proxy_cls.__name__) == FooProxy.__name__
        Assert(proxy_cls.__module__) == FooProxy.__module__
        Assert(proxy_cls.__doc__) == FooProxy.__doc__

    @test
    def forcing(self):
        func = lambda: 1

        class FooProxy(object):
            def method(self, proxied, name, get_result, *args, **kwargs):
                return get_result(proxied(), *args, **kwargs)

            def force(self, proxied):
                return proxied()
        FooProxy = as_proxy(FooProxy)

        proxy = FooProxy(func)
        Assert(proxy + proxy) == 2

        a = FooProxy(lambda: 1)
        b = FooProxy(lambda: 2)
        Assert(a - b) == -1
        Assert(b - a) == 1

    @test
    def getattr_not_called_on_method(self):
        getattr_access = []
        method_access = []

        class FooProxy(object):
            def method(self, proxied, name, get_result, *args, **kwargs):
                method_access.append(name)
                return get_result(proxied, *args, **kwargs)

            def getattr(self, proxied, name):
                getattr_access.append(name)
                return getattr(proxied, name)
        FooProxy = as_proxy(FooProxy)

        class Foo(object):
            spam = 1

            def __add__(self, other):
                return None

        p = FooProxy(Foo())
        p.spam
        p + p
        Assert(method_access) == ['__add__']
        Assert(getattr_access) == ['spam']

    @test
    def nonzero_via_len(self):
        class Foo(object):
            def __len__(self):
                return 0

        class Bar(object):
            def __len__(self):
                return 1

        proxy_cls = as_proxy(type('FooProxy', (object, ), {}))
        assert not proxy_cls(Foo())
        assert proxy_cls(Bar())

    @test
    def getitem_based_iteration(self):
        class Foo(object):
            def __getitem__(self, key):
                if key >= 3:
                    raise IndexError(key)
                return key
        proxy_cls = as_proxy(type('FooProxy', (object, ), {}))
        proxy = proxy_cls(Foo())
        Assert(list(proxy)) == [0, 1, 2]

    @test
    def reversed(self):
        class Foo(object):
            def __getitem__(self, key):
                if key >= 3:
                    raise IndexError(key)
                return key

            def __len__(self):
                return 3

        class Bar(object):
            def __reversed__(self):
                yield 2
                yield 1
                yield 0

        proxy_cls = as_proxy(type('FooProxy', (object, ), {}))
        Assert(list(reversed(proxy_cls(Foo())))) == [2, 1, 0]
        Assert(list(reversed(proxy_cls(Bar())))) == [2, 1, 0]

    @test
    def contains(self):
        class Foo(object):
            def __getitem__(self, key):
                if key >= 3:
                    raise IndexError(key)
                return key

        class Bar(object):
            def __iter__(self):
                yield 0
                yield 1
                yield 2

        class Baz(object):
            def __contains__(self, other):
                return other in (0, 1, 2)

        proxy_cls = as_proxy(type('FooProxy', (object, ), {}))
        for cls in (Foo, Bar, Baz):
            for i in xrange(3):
                assert i in proxy_cls(cls())

    @test
    def getslice(self):
        class Foo(object):
            def __getitem__(self, key):
                return [0, 1, 2][key]

            def __len__(self):
                return 3

        class Bar(object):
            def __getslice__(self, i, j):
                return [0, 1, 2][i:j]

            def __len__(self):
                return 3

        proxy_cls = as_proxy(type('FooProxy', (object, ), {}))
        a = proxy_cls(Foo())
        b = proxy_cls(Bar())
        Assert(a[:]) == b[:] == [0, 1, 2]
        Assert(a[1:]) == b[1:] == [1, 2]
        Assert(a[1:-1]) == b[1:-1] == [2]
        Assert(a[:-1]) == b[:-1] == [0, 1]

    @test
    def setslice(self):
        class Foo(object):
            def __init__(self):
                self.sequence = [0, 1, 2]

            def __eq__(self, other):
                if isinstance(other, list):
                    return self.sequence == other
                return self.sequence == other.sequence

            def __ne__(self, other):
                return self.sequence != other.sequence

            __hash__ = None

            def __len__(self):
                return len(self.sequence)

            def __repr__(self):
                return repr(self.sequence)

        class Bar(Foo):
            def __setitem__(self, key, value):
                self.sequence[key] = value

        class Baz(Foo):
            def __setslice__(self, i, j, value):
                self.sequence[i:j] = value

        proxy_cls = as_proxy(type('FooProxy', (object, ), {}))
        make_proxies = lambda: (proxy_cls(Bar()), proxy_cls(Baz()))

        a, b = make_proxies()
        a[:] = b[:] = 'abc'
        Assert(a) == b == ['a', 'b', 'c']

        a, b = make_proxies()
        a[1:] = b[1:] = 'bc'
        Assert(a) == b == [0, 'b', 'c']

        a, b = make_proxies()
        a[1:-1] = b[1:-1] = ['b']
        Assert(a) == b == [0, 'b', 2]

        a, b = make_proxies()
        a[:-1] = b[:-1] = ['a', 'b']
        Assert(a) == b == ['a', 'b', 2]

    @test
    def delslice(self):
        class Foo(object):
            def __init__(self):
                self.sequence = [0, 1, 2]

            def __eq__(self, other):
                if isinstance(other, list):
                    return self.sequence == other
                return self.sequence == other.sequence

            def __ne__(self, other):
                return self.sequence != other.sequence

            __hash__ = None

            def __len__(self):
                return len(self.sequence)

            def __repr__(self):
                return repr(self.sequence)

        class Bar(Foo):
            def __delitem__(self, key):
                del self.sequence[key]

        class Baz(Foo):
            def __delslice__(self, i, j):
                del self.sequence[i:j]

        proxy_cls = as_proxy(type('FooProxy', (object, ), {}))
        make_proxies = lambda: (proxy_cls(Bar()), proxy_cls(Baz()))

        a, b = make_proxies()
        del a[:]
        del b[:]
        Assert(a) == b == []

        a, b = make_proxies()
        del a[1:]
        del b[1:]
        Assert(a) == b == [0]

        a, b = make_proxies()
        del a[1:-1]
        del b[1:-1]
        Assert(a) == b == [0, 2]

        a, b = make_proxies()
        del a[:-1]
        del b[:-1]
        Assert(a) == b == [2]

    @test_if(GE_PYTHON_26)
    def dir(self):
        class Foo(object):
            bar = None

            def spam(self):
                pass

            def eggs(self):
                pass

        proxy_cls = as_proxy(type('FooProxy', (object, ), {}))
        Assert(dir(Foo)) == dir(proxy_cls(Foo))


tests.register(TestAsProxy)


@tests.test
def test_get_wrapped():
    proxy_cls = as_proxy(type('FooProxy', (object, ), {}))
    wrapped = 1
    Assert(get_wrapped(proxy_cls(wrapped))).is_(wrapped)


class TestLazyProxy(TestBase):
    @test
    def special(self):
        p = LazyProxy(lambda: 1)
        Assert(p + p) == 2
        Assert(p + 1) == 2
        Assert(1 + p) == 2

    @test
    def getattr(self):
        p = LazyProxy(int)
        Assert(p).imag = 0.0

    @test
    def setattr(self):
        class Foo(object): pass
        foo = Foo()
        p = LazyProxy(lambda: foo)
        p.a = 1
        Assert(p.a) == 1
        Assert(foo.a) == 1

    @test
    def repr(self):
        p = LazyProxy(int)
        Assert(repr(p)) == 'LazyProxy(%r)' % int

    @test
    def contains(self):
        p = LazyProxy(lambda: "abc")
        assert "b" in p

    @test
    def getslice(self):
        p = LazyProxy(lambda: "abc")
        assert p[1:2] == "b"


tests.register(TestLazyProxy)

########NEW FILE########
__FILENAME__ = progress
# coding: utf-8
"""
    brownie.tests.terminal.progress
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Tests for :mod:`brownie.terminal.progress`.

    :copyright: 2010-2011 by Daniel Neuhäuser
    :license: BSD, see LICENSE.rst for details
"""
from __future__ import with_statement
import time
from StringIO import StringIO

from brownie.terminal import TerminalWriter
from brownie.terminal.progress import (
    ProgressBar, Widget, TextWidget, HintWidget, PercentageWidget, BarWidget,
    PercentageBarWidget, parse_progressbar, StepWidget, bytes_to_string,
    count_digits, TimeWidget, DataTransferSpeedWidget
)

from attest import Tests, TestBase, test, Assert


tests = Tests([])


@tests.test
def test_count_digits():
    Assert(count_digits(10)) == 2
    Assert(count_digits(0)) == 1
    Assert(count_digits(-10)) == 3


@tests.test
def test_bytes_to_string():
    Assert(bytes_to_string(1000)) == '1000B'
    si = bytes_to_string(1000, binary=False)
    Assert('kB').in_(si)
    Assert('1').in_(si)


@tests.test
def test_parse_progressbar():
    tests = [
        ('foobar', [['text', 'foobar']]),
        ('$foo bar', [['foo', None], ['text', ' bar']]),
        ('$foo $$bar', [['foo', None], ['text', ' $bar']]),
        ('$foo:spam bar', [['foo', 'spam'], ['text', ' bar']]),
        ('$foo:""', [['foo', '']]),
        ('$foo:"spam eggs" bar', [['foo', 'spam eggs'], ['text', ' bar']]),
        ('$foo:"spam\\" eggs" bar', [['foo', 'spam\" eggs'], ['text', ' bar']])
    ]
    for test, result in tests:
        Assert(parse_progressbar(test)) == result


class TestWidget(TestBase):
    @test
    def size_hint(self):
        writer = TerminalWriter(StringIO())
        progressbar = ProgressBar([], writer)
        widget = Widget()
        assert not widget.provides_size_hint
        Assert(widget.size_hint(progressbar)).is_(None)

    @test
    def init(self):
        writer = TerminalWriter(StringIO())
        progressbar = ProgressBar([], writer)
        widget = Widget()
        with Assert.raises(NotImplementedError) as exc:
            widget.init(progressbar, writer.get_width())
        Assert(exc.args[0]) == 'Widget.init'

    @test
    def update(self):
        writer = TerminalWriter(StringIO())
        progressbar = ProgressBar([], writer)
        widget = Widget()
        with Assert.raises(NotImplementedError) as exc:
            widget.update(progressbar, writer.get_width())
        Assert(exc.args[0]) == 'Widget.update'

    @test
    def finish(self):
        class MyWidget(Widget):
            update_called = False

            def update(self, writer, remaining_width, **kwargs):
                self.update_called = True

        writer = TerminalWriter(StringIO())
        progressbar = ProgressBar([], writer)
        widget = MyWidget()
        widget.finish(progressbar, writer.get_width())
        assert widget.update_called

    @test
    def repr(self):
        widget = Widget()
        Assert(repr(widget)) == 'Widget()'

tests.register(TestWidget)


@tests.test
def test_text_widget():
    writer = TerminalWriter(StringIO())
    progressbar = ProgressBar([], writer)
    widget = TextWidget('foobar')
    assert widget.provides_size_hint
    Assert(widget.size_hint(progressbar)) == len('foobar')
    Assert(widget.init(progressbar, writer.get_width())) == 'foobar'
    Assert(widget.update(progressbar, writer.get_width())) == 'foobar'
    Assert(widget.finish(progressbar, writer.get_width())) == 'foobar'

    Assert(repr(widget)) == "TextWidget('foobar')"


@tests.test
def test_hint_widget():
    writer = TerminalWriter(StringIO())
    progressbar = ProgressBar([], writer)
    widget = HintWidget('foo')
    assert not widget.provides_size_hint
    Assert(widget.init(progressbar, writer.get_width())) == 'foo'
    Assert(widget.update(progressbar, writer.get_width(), hint='bar')) == 'bar'
    Assert(widget.update(progressbar, writer.get_width(), hint='baz')) == 'baz'
    Assert(widget.finish(progressbar, writer.get_width(), hint='spam')) == 'spam'

    Assert(repr(widget)) == "HintWidget('foo')"

    widget.finish(progressbar, writer.get_width()) == u''


class TestPercentageWidget(TestBase):
    @test
    def size_hint(self):
        writer = TerminalWriter(StringIO())
        progressbar = ProgressBar([], writer, maxsteps=20)
        widget = PercentageWidget()
        assert widget.provides_size_hint
        Assert(widget.size_hint(progressbar)) == 2
        progressbar.step = 1
        Assert(widget.size_hint(progressbar)) == 2
        progressbar.step = 2
        Assert(widget.size_hint(progressbar)) == 3
        progressbar.step = 20
        Assert(widget.size_hint(progressbar)) == 4

    @test
    def init(self):
        writer = TerminalWriter(StringIO())
        progressbar = ProgressBar([], writer, maxsteps=100)
        widget = PercentageWidget()
        Assert(widget.init(progressbar, writer.get_width())) == '0%'

    @test
    def update(self):
        writer = TerminalWriter(StringIO())
        progressbar = ProgressBar([], writer, maxsteps=20)
        widget = PercentageWidget()
        widget.init(progressbar, writer.get_width())
        for i in xrange(5, 96, 5):
            progressbar.step += 1
            result = widget.update(progressbar, writer.get_width())
            Assert(result) == '%i%%' % i

    @test
    def finish(self):
        writer = TerminalWriter(StringIO())
        progressbar = ProgressBar([], writer, maxsteps=100)
        widget = PercentageWidget()
        widget.init(progressbar, writer.get_width())
        Assert(widget.finish(progressbar, writer.get_width())) == '100%'

    @test
    def repr(self):
        widget = PercentageWidget()
        Assert(repr(widget)) == 'PercentageWidget()'

tests.register(TestPercentageWidget)


class TestBarWidget(TestBase):
    @test
    def init(self):
        writer = TerminalWriter(StringIO())
        progressbar = ProgressBar([], writer)

        widget = BarWidget()
        Assert(widget.init(progressbar, 8)) == '[###...]'

    @test
    def update(self):
        writer = TerminalWriter(StringIO())
        progressbar = ProgressBar([], writer)
        states = [
            '[.###..]',
            '[..###.]',
            '[...###]',
            '[..###.]',
            '[.###..]',
            '[###...]',
            '[.###..]'
        ]

        widget = BarWidget()
        for state in states:
            Assert(widget.update(progressbar, 8)) == state

        widget = BarWidget()
        widget.position = 10
        Assert(widget.update(progressbar, 8)) == '[..###.]'
        Assert(widget.update(progressbar, 8)) == '[.###..]'

tests.register(TestBarWidget)


class TestPercentageBarWidget(TestBase):
    @test
    def init(self):
        writer = TerminalWriter(StringIO())
        progressbar = ProgressBar([], writer, maxsteps=10)
        widget = PercentageBarWidget()
        Assert(widget.init(progressbar, 12)) == '[..........]'

    @test
    def update(self):
        writer = TerminalWriter(StringIO())
        progressbar = ProgressBar([], writer, maxsteps=10)
        widget = PercentageBarWidget()
        states = [
            '[%s]' % (x + '.' * (10 - len(x))) for x in (
                '#' * i for i in xrange(1, 11)
            )
        ]
        for state in states:
            progressbar.step += 1
            Assert(widget.update(progressbar, 12)) == state

    @test
    def finish(self):
        writer = TerminalWriter(StringIO())
        progressbar = ProgressBar([], writer, maxsteps=10)
        widget = PercentageBarWidget()
        Assert(widget.finish(progressbar, 12)) == '[##########]'

tests.register(TestPercentageBarWidget)


class TestStepWidget(TestBase):
    @test
    def init(self):
        writer = TerminalWriter(StringIO())
        progressbar = ProgressBar([], writer, maxsteps=20)
        widget = StepWidget()
        Assert(widget.init(progressbar, writer.get_width())) == '0 of 20'
        Assert(widget.size_hint(progressbar)) == 7

        with Assert.raises(ValueError):
            StepWidget('foo')

        with Assert.not_raising(ValueError):
            StepWidget('bytes')

    @test
    def update(self):
        writer = TerminalWriter(StringIO())
        progressbar = ProgressBar([], writer, maxsteps=20)
        widget = StepWidget()
        widget.init(progressbar, writer.get_width())
        for i in xrange(1, 21):
            progressbar.step += 1
            result = widget.update(progressbar, writer.get_width())
            Assert(len(result)) == widget.size_hint(progressbar)
            Assert(result) == '%i of 20' % i

    @test
    def finish(self):
        writer = TerminalWriter(StringIO())
        progressbar = ProgressBar([], writer, maxsteps=20)
        widget = StepWidget()
        progressbar.step = progressbar.maxsteps
        Assert(widget.finish(progressbar, writer.get_width())) == '20 of 20'

    @test
    def units(self):
        class FooStepWidget(StepWidget):
            units = {'foo': lambda x: str(x) + 'spam'}

        writer = TerminalWriter(StringIO())
        progressbar = ProgressBar([], writer, maxsteps=20)
        widget = FooStepWidget('foo')
        Assert(widget.init(progressbar, 100)) == '0spam of 20spam'
        progressbar.step +=1
        Assert(widget.init(progressbar, 100)) == '1spam of 20spam'
        progressbar.step = progressbar.maxsteps
        Assert(widget.finish(progressbar, 100)) == '20spam of 20spam'

tests.register(TestStepWidget)


class TestTimeWidget(TestBase):
    @test
    def init(self):
        writer = TerminalWriter(StringIO())
        progressbar = ProgressBar([], writer)
        widget = TimeWidget()
        Assert(widget.init(progressbar, 100)) == '00:00:00'

    @test
    def update(self):
        writer = TerminalWriter(StringIO())
        progressbar = ProgressBar([], writer)
        widget = TimeWidget()
        widget.init(progressbar, 100)
        time.sleep(1)
        Assert(widget.update(progressbar, 100)) == '00:00:01'

tests.register(TestTimeWidget)


class TestDataTransferSpeedWidget(TestBase):
    @test
    def init(self):
        writer = TerminalWriter(StringIO())
        progressbar = ProgressBar([], writer)
        widget = DataTransferSpeedWidget()
        Assert(widget.init(progressbar, 100)) == '0kb/s'

    @test
    def update(self):
        writer = TerminalWriter(StringIO())
        progressbar = ProgressBar([], writer)
        widget = DataTransferSpeedWidget()
        widget.init(progressbar, 100)
        time.sleep(1)
        progressbar.step += 50
        speed = float(widget.update(progressbar, 100)[:-4])
        Assert(speed) > 45.0
        Assert(speed) < 55.0
        time.sleep(2)
        progressbar.step += 50
        speed = float(widget.update(progressbar, 100)[:-4])
        Assert(speed) > 20.0
        Assert(speed) < 30.0

tests.register(TestDataTransferSpeedWidget)


class TestProgressBar(TestBase):
    @test
    def from_string(self):
        stream = StringIO()
        writer = TerminalWriter(stream)
        with Assert.raises(ValueError) as exc:
            ProgressBar.from_string('$foo', writer)
        Assert(exc.args[0]) == 'widget not found: foo'

        progressbar = ProgressBar.from_string(
            'hello $hint:world $percentage', writer, maxsteps=10
        )
        progressbar.init()
        progressbar.finish(hint='me')
        Assert(stream.getvalue()) == 'hello world 0%\rhello me 100%\n'

    @test
    def init(self):
        writer = TerminalWriter(StringIO())
        sized_widgets = PercentageWidget, PercentageBarWidget
        for sized in sized_widgets:
            with Assert.raises(ValueError):
                ProgressBar([sized()], writer)

    @test
    def step(self):
        writer = TerminalWriter(StringIO())
        progressbar = ProgressBar([], writer)
        Assert(progressbar.step) == 0
        progressbar.step = 100
        Assert(progressbar.step) == 100

        progressbar = ProgressBar([], writer, maxsteps=100)
        Assert(progressbar.step) == 0
        progressbar.step = 100
        Assert(progressbar.step) == 100
        with Assert.raises(ValueError):
            progressbar.step = 200

    @test
    def iter(self):
        writer = TerminalWriter(StringIO())
        progressbar = ProgressBar([], writer)
        Assert(iter(progressbar)).is_(progressbar)

    @test
    def get_widgets_by_priority(self):
        class ComparableWidget(Widget):
            def __eq__(self, other):
                return self.__class__ is other.__class__

            def __ne__(self, other):
                return not self.__eq__(other)

            __hash__ = None

        class FooWidget(ComparableWidget):
            priority = 1

        class BarWidget(ComparableWidget):
            priority = 2

        class BazWidget(ComparableWidget):
            priority = 3

        widgets = [BarWidget(), FooWidget(), BazWidget()]

        writer = TerminalWriter(StringIO())
        progressbar = ProgressBar(widgets, writer)
        Assert(progressbar.get_widgets_by_priority()) == [
            (2, BazWidget()), (0, BarWidget()), (1, FooWidget())
        ]

    @test
    def get_usable_width(self):
        writer = TerminalWriter(StringIO())
        progressbar = ProgressBar([TextWidget('foobar')], writer)
        Assert(progressbar.get_usable_width()) == writer.get_usable_width() - 6

    @test
    def write(self):
        stream = StringIO()
        writer = TerminalWriter(stream, prefix='spam')
        writer.indent()
        progressbar = ProgressBar([], writer)
        progressbar.write('foo', update=False)
        Assert(stream.getvalue()) == 'spam    foo'
        progressbar.write('bar')
        Assert(stream.getvalue()) == 'spam    foo\rspam    bar'

    @test
    def contextmanager_behaviour(self):
        class MyProgressBar(ProgressBar):
            init_called = False
            finish_called = False

            def init(self):
                self.init_called = True

            def finish(self):
                self.finish_called = True

        writer = TerminalWriter(StringIO())
        progressbar = MyProgressBar([], writer)
        with progressbar as foo:
            pass
        Assert(foo).is_(progressbar)
        assert progressbar.init_called
        assert progressbar.finish_called

    @test
    def repr(self):
        writer = TerminalWriter(StringIO())
        progressbar = ProgressBar([], writer)
        Assert(repr(progressbar)) == 'ProgressBar([], %r, maxsteps=None)' % writer

        progressbar = ProgressBar([], writer, maxsteps=100)
        Assert(repr(progressbar)) == 'ProgressBar([], %r, maxsteps=100)' % writer

tests.register(TestProgressBar)

########NEW FILE########
__FILENAME__ = text
# coding: utf-8
"""
    brownie.tests.text
    ~~~~~~~~~~~~~~~~~~

    Tests for :mod:`brownie.tests`.

    :copyright: 2010-2011 by Daniel Neuhäuser
    :license: BSD, see LICENSE.rst for details
"""
try:
    import translitcodec
except ImportError:
    translitcodec = None
from attest import Tests, Assert

from brownie.text import transliterate


tests = Tests()


@tests.test
def test_transliterate():
    Assert(transliterate(u'äöü', 'one')) == u'aou'

    tests = zip(
        [
            (u'©', 'long'),
            (u'©', 'short'),
            (u'☺', 'one'),
        ],
        [u''] * 3 if translitcodec is None else [u'(c)', u'c', u'?']
    )
    for args, result in tests:
        Assert(transliterate(*args)) == result

########NEW FILE########
__FILENAME__ = text
# coding: utf-8
"""
    brownie.text
    ~~~~~~~~~~~~

    Utilities to deal with text.

    .. versionadded:: 0.6

    :copyright: 2010-2011 by Daniel Neuhäuser
    :license: BSD, see LICENSE.rst for details
"""
import unicodedata

try:
    import translitcodec
except ImportError: # pragma: no cover
    translitcodec = None


def transliterate(string, length='long'):
    """
    Returns a transliterated version of the given unicode `string`.

    By specifying `length` you can specify how many characters are used for a
    replacement:

    `long`
        Use as many characters as needed to make a natural replacement.

    `short`
        Use as few characters as possible to make a replacement.

    `one`
        Use only one character to make a replacement. If a character cannot
        be transliterated with a single character replace it with `'?'`.

    If available translitcodec_ is used, which provides more natural results.

    .. _translitcodec: http://pypi.python.org/pypi/translitcodec
    """
    if length not in ('long', 'short', 'one'):
        raise ValueError('unknown length: %r' % length)
    if translitcodec is None:
        return unicodedata.normalize('NFKD', string) \
            .encode('ascii', 'ignore') \
            .decode('ascii')
    else:
        if length == 'one':
            return string.encode('translit/one/ascii', 'replace').decode('ascii')
        return string.encode('translit/%s' % length)

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Brownie documentation build configuration file, created by
# sphinx-quickstart on Fri Dec  3 16:39:44 2010.
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
sys.path.insert(0, os.path.join(os.path.dirname(__file__), os.path.pardir))
sys.path.append(os.path.abspath('_themes/minimalism'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = [
    'sphinx.ext.autodoc', 'sphinx.ext.intersphinx', 'sphinx.ext.viewcode',
    'sphinx.ext.doctest', 'sphinxcontrib.ansi'
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Brownie'
copyright = u'2010-2011, Daniel Neuhäuser and others'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.5+'
# The full version, including alpha/beta/rc tags.
release = '0.5+'

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
# pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
if os.path.exists('_themes/minimalism'):
    html_theme = 'minimalism'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
html_theme_options = {
    'github_fork': 'DasIch/Brownie',
    'is_a_pocoo_project': True
}

# Add any paths that contain custom themes here, relative to this directory.
html_theme_path = ['_themes']

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
htmlhelp_basename = 'Browniedoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'Brownie.tex', u'Brownie Documentation',
   u'Daniel Neuhäuser', 'manual'),
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
    ('index', 'brownie', u'Brownie Documentation',
     [u'Daniel Neuhäuser'], 1)
]


# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {
    'http://docs.python.org/': None,
    'http://www.pocoo.org/': None
}

autodoc_member_order = 'bysource'

html_ansi_stylesheet = 'black-on-white.css'

########NEW FILE########
__FILENAME__ = runtests
# coding: utf-8
import sys

from attest import FancyReporter

from brownie.importing import import_string


def main(tests=sys.argv[1:]):
    prefix = 'brownie.tests.'
    if not tests:
        import_string(prefix + 'all').run(
            reporter=FancyReporter(style='native')
        )
    for tests in (import_string(prefix + test + '.tests') for test in tests):
        tests.run(reporter=FancyReporter(style='native'))


if __name__ == '__main__':
    main()

########NEW FILE########
