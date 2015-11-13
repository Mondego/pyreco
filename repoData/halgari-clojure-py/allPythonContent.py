__FILENAME__ = amapentry
from clojure.lang.apersistentvector import APersistentVector
from clojure.lang.persistentvector import create as createVector
from clojure.lang.cljexceptions import IndexOutOfBoundsException


class AMapEntry(APersistentVector):
    """An APersistentVector of exactly two items.

    The items are used as the key/value pairs of a an IPersistentMap.

    This is a pseudo-abstract class and should not be directly
    instantiated. See: MapEntry"""
    def __getitem__(self, i):
        """Return the key or value if i is 0 or 1, respectively.

        Raise IndexOutOfBoundsException otherwise."""
        if i == 0:
            return self.getKey()
        elif i == 1:
            return self.getValue()
        else:
            raise IndexOutOfBoundsException()

    def asVector(self):
        """Return a PersistentVector.

        The vector will contain two objects, the key and value."""
        return createVector(self.getKey(), self.getValue())

    def assocN(self, i, val):
        """Return a PersistentVector with index i set to val.

        i -- int, 0 or 1
        val -- any object"""
        return self.asVector().assocN(i, val)

    def __len__(self):
        """Return 2"""
        return 2

    def __contains__(self, x):
        """Return True if x is 0 or 1, False otherwise."""
        if x == 0 or x == 1:
            return True
        return False

    def seq(self):
        """Return an ISeq on this MapEntry."""
        return self.asVector().seq()

    def cons(self, o):
        """Return a PersistentVector.

        o -- any object

        The returned vector will contain this AMapEntry's key and value with o
        appended."""
        return self.asVector().cons(o)

    def empty(self):
        """Return None."""
        return None

    def pop(self):
        """Return a PersistentVector with one item, this AMapEntry's key."""
        return createVector(self.getKey())

########NEW FILE########
__FILENAME__ = apersistentmap

import clojure.lang.rt as RT
from clojure.lang.aseq import ASeq
from clojure.lang.mapentry import MapEntry
from clojure.lang.iprintable import IPrintable
from clojure.lang.ipersistentmap import IPersistentMap
from clojure.lang.ipersistentset import IPersistentSet
from clojure.lang.ipersistentvector import IPersistentVector
from clojure.lang.cljexceptions import (ArityException,
                                        InvalidArgumentException)


class APersistentMap(IPersistentMap, IPrintable):
    def cons(self, o):
        if isinstance(o, MapEntry):
            return self.assoc(o.getKey(), o.getValue())
        if isinstance(o, IPersistentVector):
            if len(o) != 2:
                raise InvalidArgumentException("Vector arg to map conj must "
                                               "be a pair")
            return self.assoc(o[0], o[1])
        ret = self
        s = o.seq()
        while s is not None:
            e = s.first()
            ret = ret.assoc(e.getKey(), e.getValue())
            s = s.next()
        return ret

    def toDict(self):
        s = self.seq()
        d = {}
        while s is not None:
            d[s.first().getKey()] = s.first().getValue()
            s = s.next()
        return d

    def __eq__(self, other):
        if self is other:
            return True
        if isinstance(other, (IPersistentSet, IPersistentVector)):
            return False
        try:
            return (len(self) == len(other) and
                    all(s in other and other[s] == self[s] for s in self))
        except TypeError:
            return False

    def __ne__(self, other):
        return not self == other

    def __getitem__(self, item):
        return self.valAt(item)

    def __iter__(self):
        s = self.seq()
        while s is not None:
            if s.first() is None:
                pass
            yield s.first().getKey()
            s = s.next()

    # def __hash__(self):
    #     return mapHash(self)

    def __call__(self, *args, **kwargs):
        return apply(self.valAt, args)

    def __contains__(self, item):
        return self.containsKey(item)

    def writeAsString(self, writer):
        writer.write("{")
        s = self.seq()
        while s is not None:
            e = s.first()
            RT.protocols.writeAsString(e.getKey(), writer)
            writer.write(" ")
            RT.protocols.writeAsString(e.getValue(), writer)
            if s.next() is not None:
                writer.write(", ")
            s = s.next()
        writer.write("}")

    def writeAsReplString(self, writer):
        writer.write("{")
        s = self.seq()
        while s is not None:
            e = s.first()
            RT.protocols.writeAsReplString(e.getKey(), writer)
            writer.write(" ")
            RT.protocols.writeAsReplString(e.getValue(), writer)
            if s.next() is not None:
                writer.write(", ")
            s = s.next()
        writer.write("}")


def mapHash(m):
    return reduce(lambda h, v: h + (0 if v.getKey() is None
                                      else hash(v.getKey()))
                                 ^ (0 if v.getValue() is None
                                      else hash(v.getValue())),
                  m.interator(),
                  0)


class KeySeq(ASeq):
    def __init__(self, *args):
        if len(args) == 1:
            self._seq = args[0]
        elif len(args) == 2:
            self._meta = args[0]
            self._seq = args[1]
        else:
            raise ArityException()

    def first(self):
        return self._seq.first().getKey()

    def next(self):
        return createKeySeq(self._seq.next())

    def withMeta(self, meta):
        return KeySeq(meta, self._seq)

    def __iter__(self):
        s = self
        while s is not None:
            yield s.first()
            s = s.next()


def createKeySeq(s):
    if s is None:
        return None
    return KeySeq(s)


class ValueSeq(ASeq):
    def __init__(self, *args):
        if len(args) == 1:
            self._seq = args[0]
        elif len(args) == 2:
            self._meta = args[0]
            self._seq = args[1]
        else:
            raise ArityException()

    def first(self):
        return self._seq.first().getValue()

    def next(self):
        return createValueSeq(self._seq.next())

    def withMeta(self, meta):
        return ValueSeq(meta, self._seq)

    def __iter__(self):
        s = self
        while s is not None:
            yield s.first()
            s = s.next()


def createValueSeq(s):
    if s is None:
        return None
    return ValueSeq(s)

########NEW FILE########
__FILENAME__ = apersistentset
import cStringIO

import clojure.lang.rt as RT
from clojure.lang.ifn import IFn
from clojure.lang.iprintable import IPrintable
from clojure.lang.apersistentmap import createKeySeq
from clojure.lang.ipersistentset import IPersistentSet
from clojure.lang.cljexceptions import ArityException


class APersistentSet(IPersistentSet, IFn, IPrintable):
    """An unordered collection of objects.

    Ordered set implementation:
    http://code.activestate.com/recipes/576694/

    Duplicate items are not permitted."""
    def __init__(self, impl):
        """Instantiate an APersistentSet

        This should not be called directly. See: PersistentHashSet.

        impl -- a PersistentHashMap"""
        self.impl = impl
        self._hash = -1

    def __getitem__(self, item):
        """Return item if found in this set, else None.

        item -- any object"""
        return self.impl[item]

    def __contains__(self, item):
        """Return True if item is found in this set, else False"""
        return item in self.impl

    def __len__(self):
        """Return the number of items in this APersistentSet."""
        return len(self.impl)

    def seq(self):
        """Return a KeySeq containing the items in this set."""
        return createKeySeq(self.impl.seq())

    def __call__(self, *args):
        """Return the single item in args if found in this set, else None.

        args -- must be one object"""
        if len(args) != 1:
            raise ArityException()
        return self.impl[args[0]]

    def __eq__(self, other):
        """Return True if:

        * self is other
        * other is an IPersistentSet and
          * both sets contain the same items"""
        if self is other:
            return True

        if not isinstance(other, IPersistentSet):
            return False

        if len(self) != len(other):
            return False

        for s in self.impl:
            if s not in other or not other[s] == self[s]:
                return False
        return True

    def __ne__(self, other):
        "Return not self.__eq__(other)"
        return not self == other

    def __hash__(self):
        """Return the hash of this set.

        The hash is computed as the sum of the hash of all items. If the set
        is empty, the hash is 0."""
        if self._hash == -1:
            hsh = 0
            s = self.seq()
            while s is not None:
                e = s.first()
                hsh += hash(e)
                s = s.next()
            self._hash = hsh
        return self._hash

    def writeAsString(self, writer):
        """Write #{...} to writer.

        writer -- a write-able object

        Where ... is a single space delimited list of the objects in this
        set."""
        writer.write("#{")
        s = self.seq()
        while s is not None:
            RT.protocols.writeAsString(s.first(), writer)
            if s.next() is not None:
                writer.write(" ")
            s = s.next()
        writer.write("}")

    def writeAsReplString(self, writer):
        """Write #{...} to writer.

        writer -- a write-able object

        Where ... is a single space delimited list of the objects in this
        set. The string may be read by the clojure-py reader."""
        writer.write("#{")
        s = self.seq()
        while s is not None:
            RT.protocols.writeAsReplString(s.first(), writer)
            if s.next() is not None:
                writer.write(" ")
            s = s.next()
        writer.write("}")

    def __str__(self):
        """Return a string representation of this set.

        The set will be formatted as a Python set would be:

        set([contents])"""
        s = []
        sq = self.seq()
        while sq is not None:
            s.append(str(sq.first()))
            sq = sq.next()
        if not s:
            return "set()"
        else:
            return "set([" + ", ".join(s) + "])"

    def __repr__(self):
        """Return a string representation of this set.

        An APersistentSet has no Python readable representation. The
        *semantic* validity of the resulting set is unknown."""
        sio = cStringIO.StringIO()
        self.writeAsReplString(sio)
        return "<{0}.{1} object at 0x{2:x} {3}>".format(self.__module__,
                                                        type(self).__name__,
                                                        id(self),
                                                        sio.getvalue())

########NEW FILE########
__FILENAME__ = apersistentvector
import cStringIO

import clojure.lang.rt as RT
from clojure.lang.iobj import IObj
from clojure.lang.iprintable import IPrintable
from clojure.lang.indexableseq import IndexableSeq
from clojure.lang.ipersistentmap import IPersistentMap
from clojure.lang.ipersistentset import IPersistentSet
from clojure.lang.ipersistentvector import IPersistentVector
from clojure.lang.cljexceptions import ArityException
from clojure.lang.cljexceptions import IndexOutOfBoundsException


class APersistentVector(IPersistentVector, IPrintable):
    """Pseudo-Abstract class to define a persistent vector.

    For concrete classes see: PersistentVector, MapEntry, and SubVec."""
    def __iter__(self):
        """Return an iterator on this vector."""
        for x in range(len(self)):
            yield self.nth(x)

    def peek(self):
        """Return the last item in this vector or None if empty."""
        if len(self):
            return self.nth(len(self) - 1)
        return None

    def __getitem__(self, index):
        """Return the item at index.

        index -- integer"""
        return self.nth(index)

    def seq(self):
        """Return an IndexableSeq on this vector or None if empty."""
        if not len(self):
            return None
        return IndexableSeq(self, 0)

    def count(self):
        return len(self)

    def __eq__(self, other):
        """Equality test.

        other -- ISeq or something that implements the seq protocol

        ASeq.__eq__ is actually used."""
        return (self is other or
                (RT.isSeqable(other) and
                 not isinstance(other, (IPersistentSet, IPersistentMap)) and
                 self.seq() == RT.seq(other)))

    def __hash__(self):
        """Return the hash on this vector or 1 if the vector is empty.

        See: ASeq.hasheq()"""
        s = self.seq()
        if not s is None:
            return s.hasheq();
        else:
            return 1            # EmptyList.__hash__() => 1

    def __ne__(self, other):
        """Return not self.__eq__(other)"""
        return not self == other

    # Placing these print methods here will cover:
    # MapEntry, PersistentVector, and SubVec

    def writeAsString(self, writer):
        """Write [...] to writer.

        writer -- a write-able object

        Where ... is a single space delimited list of the objects in this
        vector."""
        writer.write("[")
        s = self.seq()
        while s is not None:
            RT.protocols.writeAsString(s.first(), writer)
            if s.next() is not None:
                writer.write(" ")
            s = s.next()
        writer.write("]")

    def writeAsReplString(self, writer):
        """Write [...] to writer.

        writer -- a write-able object

        Where ... is a single space delimited list of the objects in this
        vector. The string may be read by the clojure-py reader."""
        writer.write("[")
        s = self.seq()
        while s is not None:
            RT.protocols.writeAsReplString(s.first(), writer)
            if s.next() is not None:
                writer.write(" ")
            s = s.next()
        writer.write("]")

    def __str__(self):
        """Return a string representation of this vector.

        The vector will be formatted as a Python list.
        """
        s = []
        for x in self:
            s.append(str(x))
        return "[" + ", ".join(s) + "]"

    def __repr__(self):
        """Return a string representation of this vector.

        A persistent vector has no Python readable representation. The
        *semantic* validity of the resulting list is unknown."""
        sio = cStringIO.StringIO()
        self.writeAsReplString(sio)
        return "<{0}.{1} object at 0x{2:x} {3}>".format(self.__module__,
                                                        type(self).__name__,
                                                        id(self),
                                                        sio.getvalue())

# ======================================================================
# SubVec
# ======================================================================

class SubVec(APersistentVector):
    """A fixed *window* on an APersistentVector."""
    def __init__(self, meta, v, start, end):
        """Instantiate a SubVec.

        meta -- IPersistentMap, meta data to attach
        v -- IPersistentVector, parent
        start -- int, start index into v
        end -- int, end index into v"""
        self._meta = meta
        if isinstance(v, SubVec):
            start += v.start
            end += v.start
            v = v.v
        self.v = v
        self.start = start
        self.end = end

    def nth(self, i):
        """Return the i'th item.

        i -- integer >= 0

        May raise an IndexOutOfBoundsException"""
        if i < 0 or self.start + i >= self.end:
            raise IndexOutOfBoundsException()
        return self.v.nth(self.start + i)

    def assocN(self, i, val):
        """Return a PersistentVector or SubVec.

        i -- integer >= 0
        val -- any object

        If i is within bounds of this SubVec, return a SubVec that shares data
        with this vec but with the item at i set to val. If i is equal to the
        length of this SubVec, return a PersistentVector that shares data with
        this SubVec and has val appended. Else, raise
        IndexOutOfBoundsException.  The returned vector will have this
        vector's meta data attached."""
        if i < 0 or self.start + i > self.end:
            raise IndexOutOfBoundsException()
        elif self.start + i == self.end:
            return self.cons(val)
        return SubVec(self._meta,
                      self.v.assocN(self.start + i, val),
                      self.start,
                      self.end)

    def __len__(self):
        """Return the number of items in this SubVec."""
        return self.end - self.start

    def cons(self, o):
        """Return a new SubVec with this vec's contents and o appended."""
        return SubVec(self._meta,
                      self.v.assocN(self.end, o),
                      self.start,
                      self.end + 1)

    def empty(self):
        """Return an empty PersistentVector.

        The new vector will have this vec's meta data attached.'"""
        from clojure.lang.persistentvector import EMPTY as EMPTY_VECTOR
        return EMPTY_VECTOR.withMeta(self.meta())

    def pop(self):
        """Return a vector with all but the last item in this vector omitted.

        If this SubVec contains one item, return an empty Persistentvector.
        Else return a SubVector."""
        from clojure.lang.persistentvector import EMPTY as EMPTY_VECTOR
        if self.end - 1 == self.start:
            return EMPTY_VECTOR
        return SubVec(self._meta, self.v, self.start, self.end - 1)

    def withMeta(self, meta):
        """Return a new SubVec with meta attached.

        meta -- an IPersistentMap

        The new vec will have the same contents as this vector."""
        if self._meta == meta:
            return self
        return SubVec(self._meta, self.v, self.start, self.end)

    def meta(self):
        """Return this vector's meta data, which may be None."""
        return self._meta

########NEW FILE########
__FILENAME__ = aref
from clojure.lang.areference import AReference
from clojure.lang.iref import IRef
import clojure.lang.rt as RT
from clojure.lang.cljexceptions import IllegalStateException, ArityException
from clojure.lang.threadutil import synchronized
from clojure.lang.persistenthashmap import EMPTY


class ARef(AReference, IRef):
    def __init__(self, meta=None):
        AReference.__init__(self, meta)
        self.validator = None
        self.watches = EMPTY

    def validate(self, *args):
        if len(args) == 1:
            val = args[0]
            vf = self.validator
        elif len(args) == 2:
            vf = args[0]
            val = args[1]
        else:
            raise ArityException()

        if vf is not None \
           and not RT.booleanCast(vf(val)):
            raise IllegalStateException("Invalid reference state")

    def setValidator(self, fn):
        self.validate(fn, self.deref())
        self.validator = fn

    def getValidator(self):
        return getattr(self, "validator", None)

    def getWatches(self):
        return self.watches

    @synchronized
    def addWatch(self, key, fn):
        self.watches = self.watches.assoc(key, fn)
        return self

    @synchronized
    def removeWatch(self, key):
        self.watches = self.watches.without(key)
        return self

    def notifyWatches(self, oldval, newval):
        ws = self.watches
        if len(ws) > 0:
            for s in ws.seq().interate():
                e = s.first()
                fn = e.getValue()
                if fn is not None:
                    fn(e.getKey(), self, oldval, newval)

########NEW FILE########
__FILENAME__ = areference
from clojure.lang.ireference import IReference
from clojure.lang.cons import Cons
import clojure.lang.rt as RT
from clojure.lang.iprintable import IPrintable

class AReference(IReference, IPrintable):
    def __init__(self, meta = None):
        self._meta = meta
    def meta(self):
        return self._meta
    def alterMeta(self, fn, x, y):
        self._meta = fn(self._meta, x, y)
    def resetMeta(self, meta):
        self._meta = meta

    def writeAsString(self, writer):
        writer.write(repr(self))

    def writeAsReplString(self, writer):
        writer.write(repr(self))

########NEW FILE########
__FILENAME__ = aseq
import cStringIO

import clojure.lang.rt as RT
from clojure.lang.obj import Obj
from clojure.lang.iseq import ISeq
from clojure.lang.counted import Counted
from clojure.lang.ihasheq import IHashEq
from clojure.lang.iterable import Iterable
from clojure.lang.iprintable import IPrintable
from clojure.lang.sequential import Sequential
from clojure.lang.ipersistentmap import IPersistentMap
from clojure.lang.ipersistentset import IPersistentSet
from clojure.lang.cljexceptions import AbstractMethodCall


class ASeq(Obj, Sequential, ISeq, IHashEq, Iterable, IPrintable):
    def __eq__(self, other):
        if self is other:
            return True
        if not RT.isSeqable(other) or isinstance(other, IPersistentSet):
            return False
        se = RT.seq(other)
        # XXX: don't think this is used
        # if isinstance(se, RT.NotSeq):
        #     print other, type(other)
        #     return False
        ms = self.seq()
        while se is not None:
            if ms is None or not se.first() == ms.first():
                return False
            ms = ms.next()
            se = se.next()
        return ms is None

    def __ne__(self, other):
        """Return not self.__eq__(other)"""
        return not self == other

    # XXX: This is broken, it should raise IndexOutOfBoundsException.
    #      If the nth protocol is going to be used for clojure-py, this should
    #      act like (0, 1)[42] when called from the Python side.
    def __getitem__(self, idx):
        """Return the item at idx or None if idx >= length self."""
        s = self.seq()
        c = 0
        while s is not None:
            if c == idx:
                return s.first()
            c += 1
            s = s.next()
        return None

    def seq(self):
        """Return this sequence (self)."""
        return self

    # XXX: don't think this is used
    # def count(self):
    #     """Return the number of items in this sequence."""
    #     i = 1
    #     for s in self.interator():
    #         if isinstance(s, Counted):
    #             return i + s.count()
    #         i += 1
    #     return i

    def more(self):
        """Return an ISeq.

        If this sequence has one item in it, return an EmptyList, else return
        the tail of this sequence"""
        s = self.next()
        if s is None:
            from clojure.lang.persistentlist import EMPTY
            return EMPTY
        return s

    # def first(self):
    #     """Raise AbstractMethodCall."""
    #     raise AbstractMethodCall(self)

    def __iter__(self):
        """Return an iterator on this sequence."""
        s = self.seq()
        while s is not None:
            yield s.first()
            s = s.next()

    def hasheq(self):
        """Return the hash of this sequence."""
        ret = 1
        for s in self:
            ret = 31 * ret + hash(s)
        return ret

    def cons(self, other):
        """Return a Cons.

        other -- any object

        The Cons will have object as the head, and this sequence as the
        tail."""
        from clojure.lang.cons import Cons
        return Cons(other, self)

    def __str__(self):
        """Return a string representation of this sequence.

        The list will be formatted as a Python tuple.
        """
        s = []
        for x in self:
            s.append(str(x))
        return "(" + ", ".join(s) + ")"

    def __repr__(self):
        """Return a string representation of this sequence.

        An ASeq has no Python readable representation. The
        *semantic* validity of the resulting list is unknown."""
        sio = cStringIO.StringIO()
        self.writeAsReplString(sio)
        return "<{0}.{1} object at 0x{2:x} {3}>".format(self.__module__,
                                                        type(self).__name__,
                                                        id(self),
                                                        sio.getvalue())

    def writeAsString(self, writer):
        """Write (...) to writer.

        writer -- a write-able object

        Where ... is a single space delimited list of the objects in this
        sequence."""
        writer.write("(")
        s = self
        while s is not None:
            RT.protocols.writeAsString(s.first(), writer)
            if s.next() is not None:
                writer.write(" ")
            s = s.next()
        writer.write(")")

    def writeAsReplString(self, writer):
        """Write (...) to writer.

        writer -- a write-able object

        Where ... is a single space delimited list of the objects in this
        sequence. The string may be read by the clojure-py reader."""
        writer.write("(")
        s = self
        while s is not None:
            RT.protocols.writeAsReplString(s.first(), writer)
            if s.next() is not None:
                writer.write(" ")
            s = s.next()
        writer.write(")")

########NEW FILE########
__FILENAME__ = associative
from clojure.lang.cljexceptions import AbstractMethodCall
from clojure.lang.ilookup import ILookup
from clojure.lang.ipersistentcollection import IPersistentCollection


class Associative(ILookup, IPersistentCollection):
    def containsKey(self, key):
        raise AbstractMethodCall(self)

    def entryAt(self, key):
        raise AbstractMethodCall(self)

    def assoc(self, key, val):
        raise AbstractMethodCall(self)

########NEW FILE########
__FILENAME__ = atom
from aref import ARef
from cljexceptions import ArityException
from atomicreference import AtomicReference


class Atom(ARef):
    """A thread-safe mutable object."""
    def __init__(self, state, meta=None):
        """Instantiate an Atom to the given state.

        state -- any object
        meta -- meta data to attach"""
        super(Atom, self).__init__(meta)
        self._state = AtomicReference(state)
    def deref(self):
        """Return this Atom's current state."""
        return self._state.get()
    def swap(self, *args):
        """Change this Atom's current state.

        args must be one of:

        * IFn
        * IFn, object
        * IFn, object, object
        * IFn, object, object, ISeq

        An ArityException will be raised otherwise.

        Return the result of calling IFn with the current state of this Atom
        as its first argument and the remaining arguments to this method."""
        func = None

        if 0 < len(args) <= 3:
            ifn = args[0]
            args = args[1:]
            func = lambda v: ifn(v, *args)
        elif len(args) == 4:
            ifn = args[0]
            arg1, arg2, args = args[1:]
            func = lambda v: ifn(v, arg1, arg2, *args)
        else:
            raise ArityException("Atom.swap() expected 1 to 4 arguments,"
                                 " got: ({})".format(len(args)))

        while True:
            val = self.deref()
            newv = func(val)
            self.validate(newv)
            if self._state.compareAndSet(val, newv):
                self.notifyWatches(val, newv)
                return newv
    def compareAndSet(self, oldv, newv):
        """Set the state of this Atom to newv.

        oldv -- Any object. The expected current state of this Atom.
        newv -- any object

        If the current state of this Atom is oldv set it to newv. A
        validator, if one exists is called prior to setting. Any watches are
        notified after successfully setting.

        Return True if successful, False otherwise."""
        self.validate(newv)
        ret = self._state.compareAndSet(oldv, newv)
        if ret is not None:
            self.notifyWatches(oldv, newv)
        return ret
    def reset(self, newval):
        """Reset this Atom's state to newval.

        newval -- any object

        A validator, if one exists is called prior to resetting.
        Any watches are notified after resetting.

        Return newval"""
        oldval = self._state.get()
        self.validate(newval)
        self._state.set(newval)
        self.notifyWatches(oldval, newval)
        return newval

########NEW FILE########
__FILENAME__ = atomicreference
# FIXME -- not threadsafe

class AtomicReference(object):
    def __init__(self, val=None):
        self.val = val

    def get(self):
        return self.val

    def set(self, val):
        self.val = val

    def mutate(self, fn):
        self.val = fn(self.val)

    def compareAndSet(self, old, newval):
        self.val = newval
        return True

########NEW FILE########
__FILENAME__ = atransientmap
from clojure.lang.ifn import IFn
from clojure.lang.cljexceptions import AbstractMethodCall
from clojure.lang.itransientmap import ITransientMap
import clojure.lang.rt as RT
from clojure.lang.iprintable import IPrintable

class ATransientMap(IFn, ITransientMap, IPrintable):
    def ensureEditable(self):
        raise AbstractMethodCall(self)

    def doAssoc(self, key, val):
        raise AbstractMethodCall(self)

    def doWithout(self, key):
        raise AbstractMethodCall(self)

    def doValAt(self, key, notFound = None):
        raise AbstractMethodCall(self)

    def doCount(self):
        raise AbstractMethodCall(self)

    def doPersistent(self):
        raise AbstractMethodCall(self)

    def conj(self, val):
        self.ensureEditable()
        return RT.conjToAssoc(self, val)

    def __call__(self, *args):
        return apply(self.valAt, args)

    def without(self, key):
        self.ensureEditable()
        return self.doWithout()

    def valAt(self, key, notFound = None):
        self.ensureEditable()
        return self.doValAt(key, notFound)

    def assoc(self, key, value):
        self.ensureEditable()
        return self.doAssoc(key, value)

    def count(self):
        self.ensureEditable()
        return self.count()

    def persistent(self):
        self.ensureEditable()
        return self.persistent()

    def writeAsString(self, writer):
        writer.write(repr(self))

    def writeAsReplString(self, writer):
        writer.write(repr(self))

########NEW FILE########
__FILENAME__ = box
class Box(object):
    def __init__(self, val):
        self.val = val

########NEW FILE########
__FILENAME__ = cljexceptions
class AbstractMethodCall(Exception):
    def __init__(self, cls=None):
        if cls is not None:
            Exception.__init__(self, "in " + cls.__class__.__name__)
        else:
            Exception.__init__(self)


class ArityException(TypeError):
    pass


class CljException(Exception):
    pass


class IllegalStateException(CljException):
    pass


class InvalidArgumentException(CljException):
    pass


class IllegalAccessError(CljException):
    pass


class IndexOutOfBoundsException(CljException):
    pass


class UnsupportedOperationException(Exception):
    pass


class IllegalArgumentException(Exception):
    pass


class TransactionRetryException(Exception):
    pass
    
class ReaderException(Exception):
    def __init__(self, s=None, rdr=None):
        Exception.__init__(
            self,
            s + ("" if rdr is None else " at line " + str(rdr.lineCol()[0])))


class CompilerException(Exception):
    def __init__(self, reason, form):
        from lispreader import LINE_KEY
        msg = "Compiler exception {0}".format(reason)
        at = getattr(form, "meta", lambda: {LINE_KEY: None})()[LINE_KEY]
        if at:
            msg += " at {0}".format(at)
        Exception.__init__(self, msg)


class NoNamespaceException(ImportError):
    def __init__(self, lib, ns):
        msg = "Importing {0} did not create namespace {1}.".format(lib, ns)

########NEW FILE########
__FILENAME__ = cljkeyword
from clojure.lang.atomicreference import AtomicReference
from clojure.lang.iprintable import IPrintable
from clojure.lang.ifn import IFn
from clojure.lang.named import Named
from clojure.lang.persistenthashmap import EMPTY as EMPTY_MAP
from clojure.lang.symbol import Symbol


class Keyword(IFn, Named, IPrintable):
    interned = AtomicReference(EMPTY_MAP)

    def __new__(cls, *args):
        """Keyword constructor.
        
        Argument(s) will be passed to Symbol() first.  If the keyword was
        already interned, it will be returned.
        """
        sym = Symbol(*args).withMeta(None)
        if sym in Keyword.interned.get():
            return Keyword.interned.get()[sym]
        obj = super(Keyword, cls).__new__(cls)
        Keyword.interned.mutate(
            lambda old: old if sym in old else old.assoc(sym, obj))
        obj.sym = sym
        obj.hash = hash(sym) + 0x9e3779b9
        return obj

    def __hash__(self):
        return self.hash

    def __call__(self, obj, notFound=None):
        if obj is None:
            return None
        if self not in obj:
            return notFound
        return obj[self]

    def __repr__(self):
        return ":{0}".format(self.sym)

    def getNamespace(self):
        return self.sym.getNamespace()

    def getName(self):
        return self.sym.getName()

    def writeAsString(self, writer):
        writer.write(repr(self))

    def writeAsReplString(self, writer):
        writer.write(repr(self))


def find(*args):
    if len(args) == 1 and isinstance(args[0], Symbol):
        return Keyword.interned.val()[args[0]]()
    if len(args) == 2:
        return find(Symbol(*args))


LINE_KEY = Keyword("line")
TAG_KEY = Keyword("tag")
T = Keyword("T")

########NEW FILE########
__FILENAME__ = comparator
from clojure.lang.cljexceptions import AbstractMethodCall

class Comparator(object):
    def compare(self, a, b):
        raise AbstractMethodCall()

########NEW FILE########
__FILENAME__ = compiler
import __builtin__
import dis
import marshal
import pickle
import py_compile
import re
import sys
import time
import fractions

from clojure.lang.cons import Cons
from clojure.lang.cljexceptions import CompilerException, AbstractMethodCall
from clojure.lang.cljkeyword import Keyword
from clojure.lang.ipersistentvector import IPersistentVector
from clojure.lang.ipersistentmap import IPersistentMap
from clojure.lang.ipersistentset import IPersistentSet
from clojure.lang.ipersistentlist import IPersistentList
from clojure.lang.iseq import ISeq
from clojure.lang.lispreader import _AMP_, LINE_KEY, garg
from clojure.lang.namespace import Namespace, findNS, findItem, intern
from clojure.lang.persistentlist import PersistentList, EmptyList
from clojure.lang.persistentvector import PersistentVector
import clojure.lang.rt as RT
from clojure.lang.symbol import Symbol
from clojure.lang.var import Var, threadBindings
from clojure.util.byteplay import *
import clojure.util.byteplay as byteplay
import marshal
import types

_MACRO_ = Keyword("macro")
_NS_ = Symbol("*ns*")
version = (sys.version_info[0] * 10) + sys.version_info[1]

PTR_MODE_GLOBAL = "PTR_MODE_GLOBAL"
PTR_MODE_DEREF = "PTR_MODE_DEREF"

AUDIT_CONSTS = False

class MetaBytecode(object):
    pass


class GlobalPtr(MetaBytecode):
    def __init__(self, ns, name):
        self.ns = ns
        self.name = name

    def __repr__(self):
        return "GblPtr<%s/%s>" % (self.ns.__name__, self.name)

    def emit(self, comp, mode):
        module = self.ns
        val = getattr(module, self.name)

        if isinstance(val, Var):
            if not val.isDynamic():
                val = val.deref()
                return [(LOAD_CONST, val)]
            else:
                if mode is PTR_MODE_DEREF:
                    return [(LOAD_CONST, val),
                            (LOAD_ATTR, "deref"),
                            (CALL_FUNCTION, 0)]
                else:
                    raise CompilerException("Invalid deref mode", mode)

        return [(LOAD_CONST, module),
               (LOAD_ATTR, self.name)]


def expandMetas(bc, comp):
    code = []
    for x in bc:
        if AUDIT_CONSTS and isinstance(x, tuple):
            if x[0] == LOAD_CONST:
                try:
                    marshal.dumps(x[1])
                except:
                    print "Can't marshal", x[1], type(x[1])
                    raise

        if isinstance(x, MetaBytecode):
            code.extend(x.emit(comp, PTR_MODE_DEREF))
        else:
            code.append(x)
    return code


def emitJump(label):
    if version == 26:
        return [(JUMP_IF_FALSE, label),
                (POP_TOP, None)]
    else:
        return [(POP_JUMP_IF_FALSE, label)]


def emitLanding(label):
    if version == 26:
        return [(label, None),
                (POP_TOP, None)]
    else:
        return [(label, None)]


builtins = {}

def register_builtin(sym):
    """A decorator to register a new builtin macro.
    
    Takes the symbol that the macro represents as argument. If the argument is
    a string, it will be converted to a symbol.
    """
    def inner(func):
        builtins[Symbol(sym)] = func
        return func
    return inner


@register_builtin("in-ns")
def compileNS(comp, form):
    rest = form.next()
    if len(rest) != 1:
        raise CompilerException("in-ns only supports one item", rest)
    ns = rest.first()
    code = [(LOAD_CONST, comp),
            (LOAD_ATTR, "setNS")]
    if isinstance(ns, Symbol):
        code.append((LOAD_CONST, ns))
    else:
        code.extend(comp.compile(ns))
    code.append((CALL_FUNCTION, 1))
    set_NS_ = [(LOAD_CONST, comp),
               (LOAD_ATTR, "_NS_"),
               (LOAD_ATTR, "set"),
               (LOAD_CONST, comp),
               (LOAD_ATTR, "ns"),
               (CALL_FUNCTION, 1),
               (LOAD_CONST, comp),
               (LOAD_ATTR, "ns")]
    code.extend(set_NS_)
    return code


@register_builtin("def")
def compileDef(comp, form):
    if len(form) not in [2, 3]:
        raise CompilerException("Only 2 or 3 arguments allowed to def", form)
    sym = form.next().first()
    value = None
    if len(form) == 3:
        value = form.next().next().first()
    if sym.ns is None:
        ns = comp.getNS()
    else:                                        
        ns = sym.ns

    comp.pushName(RT.name(sym))
    code = []
    v = intern(comp.getNS(), sym)

    v.setDynamic(True)
    if len(form) == 3:
        code.append((LOAD_CONST, v))
        code.append((LOAD_ATTR, "bindRoot"))
        compiledValue = comp.compile(value)
        if isinstance(value, ISeq) \
           and value.first().getName() == 'fn' \
           and sym.meta() is not None:
            try:
                compiledValue[0][1].__doc__ = sym.meta()[Keyword('doc')]
            except AttributeError:
                pass
        code.extend(compiledValue)
        code.append((CALL_FUNCTION, 1))
    else:
        code.append((LOAD_CONST, v))
    v.setMeta(sym.meta())
    comp.popName()
    return code


def compileBytecode(comp, form):
    codename = form.first().name
    if not hasattr(byteplay, codename):
        raise CompilerException("bytecode {0} unknown".format(codename), form)
    bc = getattr(byteplay, codename)
    hasarg = bc in byteplay.hasarg
    form = form.next()
    arg = None
    if hasarg:
        arg = form.first()
        if not isinstance(arg, (int, str, unicode)) and bc is not LOAD_CONST:
            raise CompilerException(
                "first argument to {0} must be int, unicode, or str".
                format(codename), form)

        arg = evalForm(arg, comp.getNS())
        form = form.next()

    se = byteplay.getse(bc, arg)
    if form != None and se[0] != 0 and (se[0] != len(form) or se[1] > 1):
        raise CompilerException(
            "literal bytecode {0} not supported".format(codename), form)
    s = form
    code = []
    while s is not None:
        code.extend(comp.compile(s.first()))
        s = s.next()
    code.append((bc, arg))
    if se[1] == 0:
        code.append((LOAD_CONST, None))
    return code


@register_builtin("kwapply")
def compileKWApply(comp, form):
    if len(form) < 3:
        raise CompilerException("at least two arguments required to kwapply", form)

    form = form.next()
    fn = form.first()
    form = form.next()
    kws = form.first()
    args = form.next()
    code = []

    s = args
    code.extend(comp.compile(fn))
    while s is not None:
        code.extend(comp.compile(s.first()))
        s = s.next()
    code.extend(comp.compile(kws))
    code.append((LOAD_ATTR, "toDict"))
    code.append((CALL_FUNCTION, 0))
    code.append((CALL_FUNCTION_KW, 0 if args is None else len(args)))
    return code

@register_builtin("loop*")
def compileLoopStar(comp, form):
    if len(form) < 3:
        raise CompilerException("loop* takes at least two args", form)
    form = form.next()
    if not isinstance(form.first(), PersistentVector):
        raise CompilerException(
            "loop* takes a vector as it's first argument", form)
    bindings = RT.seq(form.first())
    args = []
    code = []
    if bindings and len(bindings) % 2:
        raise CompilerException("loop* takes a even number of bindings", form)
    while bindings:
        local, bindings = bindings.first(), bindings.next()
        body, bindings = bindings.first(), bindings.next()
        if not isinstance(local, Symbol) or local.ns is not None:
            raise CompilerException(
                "bindings must be non-namespaced symbols", form)
        code.extend(comp.compile(body))
        alias = RenamedLocal(Symbol("{0}_{1}".format(local, RT.nextID()))
                             if comp.getAlias(local)
                             else local)
        comp.pushAlias(local, alias)
        args.append(local)
        code.extend(alias.compileSet(comp))
    form = form.next()
    recurlabel = Label("recurLabel")
    recur = {"label": recurlabel,
             "args": [comp.getAlias(arg).compileSet(comp) for arg in args]}
    code.append((recurlabel, None))
    comp.pushRecur(recur)
    code.extend(compileImplcitDo(comp, form))
    comp.popRecur()
    comp.popAliases(args)
    return code


@register_builtin("let*")
def compileLetStar(comp, form):
    if len(form) < 2:
        raise CompilerException("let* takes at least two args", form)
    form = form.next()
    if not isinstance(form.first(), IPersistentVector):
        raise CompilerException(
            "let* takes a vector as it's first argument", form)
    bindings = RT.seq(form.first())
    args = []
    code = []
    if bindings and len(bindings) % 2:
        raise CompilerException("let* takes a even number of bindings", form)
    while bindings:
        local, bindings = bindings.first(), bindings.next()
        body, bindings = bindings.first(), bindings.next()
        if not isinstance(local, Symbol) or local.ns is not None:
            raise CompilerException(
                "bindings must be non-namespaced symbols", form)
        code.extend(comp.compile(body))
        alias = RenamedLocal(Symbol("{0}_{1}".format(local, RT.nextID()))
                             if comp.getAlias(local)
                             else local)
        comp.pushAlias(local, alias)
        args.append(local)
        code.extend(alias.compileSet(comp))
    form = form.next()
    code.extend(compileImplcitDo(comp, form))
    comp.popAliases(args)
    return code


@register_builtin(".")
def compileDot(comp, form):
    if len(form) != 3:
        raise CompilerException(". form must have two arguments", form)
    clss = form.next().first()
    member = form.next().next().first()

    if isinstance(member, Symbol):
        attr = member.name
        args = []
    elif isinstance(member, ISeq):
        if not isinstance(member.first(), Symbol):
            raise CompilerException("Member name must be symbol", form)
        attr = member.first().name
        args = []
        if len(member) > 1:
            f = member.next()
            while f is not None:
                args.append(comp.compile(f.first()))
                f = f.next()

    alias = comp.getAlias(clss)
    if alias:
        code = alias.compile(comp)
        code.append((LOAD_ATTR, attr))
    else:
        code = comp.compile(Symbol(clss, attr))

    for x in args:
        code.extend(x)
    code.append((CALL_FUNCTION, len(args)))
    return code


@register_builtin("quote")
def compileQuote(comp, form):
    if len(form) != 2:
        raise CompilerException("Quote must only have one argument", form)
    return [(LOAD_CONST, form.next().first())]


@register_builtin("py/if")
def compilePyIf(comp, form):
    if len(form) != 3 and len(form) != 4:
        raise CompilerException("if takes 2 or 3 args", form)
    cmp = comp.compile(form.next().first())
    body = comp.compile(form.next().next().first())
    if len(form) == 3:
        body2 = [(LOAD_CONST, None)]
    else:
        body2 = comp.compile(form.next().next().next().first())

    elseLabel = Label("IfElse")
    endlabel = Label("IfEnd")
    code = cmp
    code.extend(emitJump(elseLabel))
    code.extend(body)
    code.append((JUMP_ABSOLUTE, endlabel))
    code.extend(emitLanding(elseLabel))
    code.extend(body2)
    code.append((endlabel, None))
    return code


@register_builtin("if*")
def compileIfStar(comp, form):
    """
    Compiles the form (if* pred val else?).
    """
    if len(form) != 3 and len(form) != 4:
        raise CompilerException("if takes 2 or 3 args", form)
    cmp = comp.compile(form.next().first())
    body = comp.compile(form.next().next().first())
    if len(form) == 3:
        body2 = [(LOAD_CONST, None)]
    else:
        body2 = comp.compile(form.next().next().next().first())

    elseLabel = Label("IfElse")
    endlabel = Label("IfEnd")
    condition_name = garg(0).name
    code = cmp
    code.append((STORE_FAST, condition_name))
    code.append((LOAD_FAST, condition_name))
    code.append((LOAD_CONST, None))
    code.append((COMPARE_OP, 'is not'))
    code.extend(emitJump(elseLabel))
    code.append((LOAD_FAST, condition_name))
    code.append((LOAD_CONST, False))
    code.append((COMPARE_OP, 'is not'))
    # Use is not instead of != as bool is a subclass of int, and
    # therefore False == 0
    code.extend(emitJump(elseLabel))
    code.extend(body)
    code.append((JUMP_ABSOLUTE, endlabel))
    code.extend(emitLanding(elseLabel))
    code.extend(body2)
    code.append((endlabel, None))
    return code


def unpackArgs(form):
    locals = {}
    args = []
    lastisargs = False
    argsname = None
    for x in form:
        if x == _AMP_:
            lastisargs = True
            continue
        if lastisargs and argsname is not None:
            raise CompilerException(
                "variable length argument must be the last in the function",
                form)
        if lastisargs:
            argsname = x
        if not isinstance(x, Symbol) or x.ns is not None:
            raise CompilerException(
                "fn* arguments must be non namespaced symbols, got {0} instead".
                format(form), form)
        locals[x] = RT.list(x)
        args.append(x.name)
    return locals, args, lastisargs, argsname


@register_builtin("do")
def compileDo(comp, form):
    return compileImplcitDo(comp, form.next())


def compileFn(comp, name, form, orgform):
    locals, args, lastisargs, argsname = unpackArgs(form.first())

    for x in locals:
        comp.pushAlias(x, FnArgument(x))

    if orgform.meta() is not None:
        line = orgform.meta()[LINE_KEY]
    else:
        line = 0
    code = [(SetLineno,line if line is not None else 0)]
    if lastisargs:
        code.extend(cleanRest(argsname.name))

    recurlabel = Label("recurLabel")

    recur = {"label": recurlabel,
    "args": map(lambda x: comp.getAlias(Symbol(x)).compileSet(comp), args)}

    code.append((recurlabel, None))
    comp.pushRecur(recur)
    code.extend(compileImplcitDo(comp, form.next()))
    comp.popRecur()
    code.append((RETURN_VALUE,None))
    comp.popAliases(locals)

    clist = map(lambda x: RT.name(x.sym), comp.closureList())
    code = expandMetas(code, comp)
    c = Code(code, clist, args, lastisargs, False, True, str(Symbol(comp.getNS().__name__, name.name)), comp.filename, 0, None)
    if not clist:
        c = types.FunctionType(c.to_code(), comp.ns.__dict__, name.name)

    return [(LOAD_CONST, c)], c


def cleanRest(name):
    label = Label("isclean")
    code = []
    code.append((LOAD_GLOBAL, "len"))
    code.append((LOAD_FAST, name))
    code.append((CALL_FUNCTION, 1))
    code.append((LOAD_CONST, 0))
    code.append((COMPARE_OP, "=="))
    code.extend(emitJump(label))
    code.append((LOAD_CONST, None))
    code.append((STORE_FAST, name))
    if version == 26:
        code.append((LOAD_CONST, None))
    code.extend(emitLanding(label))
    return code


class MultiFn(object):
    def __init__(self, comp, form):
        form = RT.seq(form)
        if len(form) < 1:
            raise CompilerException("FN defs must have at least one arg", form)
        argv = form.first()
        if not isinstance(argv, PersistentVector):
            raise CompilerException("FN arg list must be a vector", form)
        body = form.next()

        self.locals, self.args, self.lastisargs, self.argsname = unpackArgs(argv)
        endLabel = Label("endLabel")
        argcode = [(LOAD_CONST, len),
            (LOAD_FAST, '__argsv__'),
            (CALL_FUNCTION, 1),
            (LOAD_CONST, len(self.args) - (1 if self.lastisargs else 0)),
            (COMPARE_OP, ">=" if self.lastisargs else "==")]
        argcode.extend(emitJump(endLabel))
        for x in range(len(self.args)):
            if self.lastisargs and x == len(self.args) - 1:
                offset = len(self.args) - 1
                argcode.extend([(LOAD_FAST, '__argsv__'),
                    (LOAD_CONST, offset),
                    (SLICE_1, None),
                    (STORE_FAST, self.argsname.name)])
                argcode.extend(cleanRest(self.argsname.name))
            else:
                argcode.extend([(LOAD_FAST, '__argsv__'),
                    (LOAD_CONST, x),
                    (BINARY_SUBSCR, None),
                    (STORE_FAST, self.args[x])])

        for x in self.locals:
            comp.pushAlias(x, FnArgument(x))

        recurlabel = Label("recurLabel")

        recur = {"label": recurlabel,
        "args": map(lambda x: comp.getAlias(Symbol(x)).compileSet(comp), self.args)}

        bodycode = [(recurlabel, None)]
        comp.pushRecur(recur)
        bodycode.extend(compileImplcitDo(comp, body))
        bodycode.append((RETURN_VALUE, None))
        bodycode.extend(emitLanding(endLabel))
        comp.popRecur()
        comp.popAliases(self.locals)

        self.argcode = argcode
        self.bodycode = bodycode


def compileMultiFn(comp, name, form):
    s = form
    argdefs = []

    while s is not None:
        argdefs.append(MultiFn(comp, s.first()))
        s = s.next()
    argdefs = sorted(argdefs, lambda x, y: len(x.args) < len(y.args))
    if len(filter(lambda x: x.lastisargs, argdefs)) > 1:
        raise CompilerException(
            "Only one function overload may have variable number of arguments",
            form)

    code = []
    if len(argdefs) == 1 and not argdefs[0].lastisargs:
        hasvararg = False
        argslist = argdefs[0].args
        code.extend(argdefs[0].bodycode)
    else:
        hasvararg = True
        argslist = ["__argsv__"]
        for x in argdefs:
            code.extend(x.argcode)
            code.extend(x.bodycode)

        code.append((LOAD_CONST, Exception))
        code.append((CALL_FUNCTION, 0))
        code.append((RAISE_VARARGS, 1))

    clist = map(lambda x: RT.name(x.sym), comp.closureList())
    code = expandMetas(code, comp)
    c = Code(code, clist, argslist, hasvararg, False, True, str(Symbol(comp.getNS().__name__, name.name)), comp.filename, 0, None)
    if not clist:
        c = types.FunctionType(c.to_code(), comp.ns.__dict__, name.name)
    return [(LOAD_CONST, c)], c


def compileImplcitDo(comp, form):
    code = []
    s = form
    while s is not None:
        code.extend(comp.compile(s.first()))
        s = s.next()
        if s is not None:
            code.append((POP_TOP, None))
    if not len(code):
        code.append((LOAD_CONST, None))
    return code


@register_builtin("fn*")
def compileFNStar(comp, form):
    haslocalcaptures = False
    aliases = []
    if len(comp.aliases) > 0: # we might have closures to deal with
        for x in comp.aliases:

            comp.pushAlias(x, Closure(x))
            aliases.append(x)
        haslocalcaptures = True

    orgform = form
    if len(form) < 2:
        raise CompilerException("2 or more arguments to fn* required", form)
    form = form.next()
    name = form.first()
    pushed = False

    if not isinstance(name, Symbol):
        name = comp.getNamesString() + "_auto_"
    else:
        comp.pushName(name.name)
        pushed = True
        form = form.next()

    name = Symbol(name)

    # This is fun stuff here. The idea is that we want closures to be able
    # to call themselves. But we can't get a pointer to a closure until after
    # it's created, which is when we actually run this code. So, we're going to
    # create a tmp local that is None at first, then pass that in as a possible
    # closure cell. Then after we create the closure with MAKE_CLOSURE we'll
    # populate this var with the correct value

    selfalias = Closure(name)
    comp.pushAlias(name, selfalias)

    # form = ([x] x)
    if isinstance(form.first(), IPersistentVector):
        code, ptr = compileFn(comp, name, form, orgform)
    # form = (([x] x))
    elif len(form) == 1:
        code, ptr = compileFn(comp, name, RT.list(*form.first()), orgform)
    # form = (([x] x) ([x y] x))
    else:
        code, ptr = compileMultiFn(comp, name, form)

    if pushed:
        comp.popName()

    clist = comp.closureList()
    fcode = []

    if haslocalcaptures:
        comp.popAliases(aliases)

    if clist:
        for x in clist:
            if x is not selfalias:   #we'll populate selfalias later
                fcode.extend(comp.getAlias(x.sym).compile(comp))  # Load our local version
                fcode.append((STORE_DEREF, RT.name(x.sym)))            # Store it in a Closure Cell
            fcode.append((LOAD_CLOSURE, RT.name(x.sym)))           # Push the cell on the stack
        fcode.append((BUILD_TUPLE, len(clist)))
        fcode.extend(code)
        fcode.append((MAKE_CLOSURE, 0))
        code = fcode

    if selfalias in clist:
        prefix = []
        prefix.append((LOAD_CONST, None))
        prefix.extend(selfalias.compileSet(comp))
        prefix.extend(code)
        code = prefix
        code.append((DUP_TOP, None))
        code.extend(selfalias.compileSet(comp))

    comp.popAlias(Symbol(name)) #closure
    return code


def compileVector(comp, form):
    code = []
    code.extend(comp.compile(Symbol("clojure.lang.rt", "vector")))
    for x in form:
        code.extend(comp.compile(x))
    code.append((CALL_FUNCTION, len(form)))
    return code


@register_builtin("recur")
def compileRecur(comp, form):
    s = form.next() or []
    code = []
    if len(s) > len(comp.recurPoint.first()["args"]):
        raise CompilerException("too many arguments to recur", form)
    for recur_val in s:
        code.extend(comp.compile(recur_val))
    sets = comp.recurPoint.first()["args"][:]
    sets.reverse()
    for x in sets:
        code.extend(x)
    code.append((JUMP_ABSOLUTE, comp.recurPoint.first()["label"]))
    return code


@register_builtin("is?")
def compileIs(comp, form):
    if len(form) != 3:
        raise CompilerException("is? requires 2 arguments", form)
    fst = form.next().first()
    itm = form.next().next().first()
    code = comp.compile(fst)
    code.extend(comp.compile(itm))
    code.append((COMPARE_OP, "is"))
    return code


def compileMap(comp, form):
    s = form.seq()
    c = 0
    code = []
    code.extend(comp.compile(Symbol("clojure.lang.rt", "map")))
    while s is not None:
        kvp = s.first()
        code.extend(comp.compile(kvp.getKey()))
        code.extend(comp.compile(kvp.getValue()))
        c += 2
        s = s.next()
    code.append([CALL_FUNCTION, c])
    return code


def compileKeyword(comp, kw):
    return [(LOAD_CONST, kw)]


def compileBool(comp, b):
    return [(LOAD_CONST, b)]


@register_builtin("throw")
def compileThrow(comp, form):
    if len(form) != 2:
        raise CompilerException("throw requires two arguments", form)
    code = comp.compile(form.next().first())
    code.append((RAISE_VARARGS, 1))
    return code


@register_builtin("applyTo")
def compileApply(comp, form):
    s = form.next()
    code = []
    while s is not None:
        code.extend(comp.compile(s.first()))

        s = s.next()
    code.append((LOAD_CONST, RT.seqToTuple))
    code.append((ROT_TWO, None))
    code.append((CALL_FUNCTION, 1))
    code.append((CALL_FUNCTION_VAR, 0))
    return code


def compileBuiltin(comp, form):
    if len(form) != 2:
        raise CompilerException("throw requires two arguments", form)
    name = str(form.next().first())
    return [(LOAD_CONST, getBuiltin(name))]


def getBuiltin(name):
    if hasattr(__builtin__, name):
        return getattr(__builtin__, name)
    raise CompilerException("Python builtin {0} not found".format(name), name)


@register_builtin("let-macro")
def compileLetMacro(comp, form):
    if len(form) < 3:
        raise CompilerException(
            "alias-properties takes at least two args", form)
    form = form.next()
    s = RT.seq(form.first())
    syms = []
    while s is not None:
        sym = s.first()
        syms.append(sym)
        s = s.next()
        if s is None:
            raise CompilerException(
                "let-macro takes a even number of bindings", form)
        macro = s.first()
        comp.pushAlias(sym, LocalMacro(sym, macro))
        s = s.next()
    body = form.next()
    code = compileImplcitDo(comp, body)
    comp.popAliases(syms)
    return code


@register_builtin("__compiler__")
def compileCompiler(comp, form):
    return [(LOAD_CONST, comp)]


@register_builtin("try")
def compileTry(comp, form):
    """
    Compiles the try macro.
    """
    assert form.first() == Symbol("try")
    form = form.next()

    if not form:
        # I don't like this, but (try) == nil
        return [(LOAD_CONST, None)]

    # Keep a list of compiled might-throw statements in
    # implicit-do try body
    body = comp.compile(form.first())
    form = form.next()

    if not form:
        # If there are no further body statements, or
        # catch/finally/else etc statements, just
        # compile the body
        return body

    catch = []
    els = None
    fin = None
    for subform in form:
        try:
            name = subform.first()
        except AttributeError:
            name = None
        if name in (Symbol("catch"), Symbol("except")):
            name = subform.first()
            if len(subform) != 4:
                raise CompilerException(
                    "try {0} blocks must be 4 items long".format(name), form)

            # Exception is second, val is third
            exception = subform.next().first()
            if not isinstance(exception, Symbol):
                raise CompilerException(
                    "exception passed to {0} block must be a symbol".
                    format(name), form)
            for ex, _, _ in catch:
                if ex == exception:
                    raise CompilerException(
                        "try cannot catch duplicate exceptions", form)

            var = subform.next().next().first()
            if not isinstance(var, Symbol):
                raise CompilerException(
                    "variable name for {0} block must be a symbol".
                    format(name), form)
            val = subform.next().next().next().first()
            catch.append((exception, var, val))
        elif name == Symbol("else"):
            if len(subform) != 2:
                raise CompilerException(
                    "try else blocks must be 2 items", form)
            elif els:
                raise CompilerException(
                    "try cannot have multiple els blocks", form)
            els = subform.next().first()
        elif name == Symbol("finally"):
            if len(subform) != 2:
                raise CompilerException(
                    "try finally blocks must be 2 items", form)
            elif fin:
                raise CompilerException(
                    "try cannot have multiple finally blocks", form)
            fin = subform.next().first()
        else:
            # Append to implicit do
            body.append((POP_TOP, None))
            body.extend(comp.compile(subform))

    if fin and not catch and not els:
        return compileTryFinally(body, comp.compile(fin))
    elif catch and not fin and not els:
        return compileTryCatch(comp, body, catch)
    elif not fin and not catch and els:
        raise CompilerException(
            "try does not accept else statements on their own", form)

    if fin and catch and not els:
        return compileTryCatchFinally(comp, body, catch,
                                      comp.compile(fin))

    if not fin and not catch and not els:
        # No other statements, return compiled body
        return body

def compileTryFinally(body, fin):
    """
    Compiles the try/finally form. Takes the body of the try statement, and the
    finally statement. They must be compiled bytecode (i.e. comp.compile(body)).
    """
    finallyLabel = Label("TryFinally")

    ret_val = "__ret_val_{0}".format(RT.nextID())

    code = [(SETUP_FINALLY, finallyLabel)]
    code.extend(body)
    code.append((STORE_FAST, ret_val))
    code.append((POP_BLOCK, None))
    code.append((LOAD_CONST, None))
    code.append((finallyLabel, None))
    code.extend(fin)
    code.extend([(POP_TOP, None),
                 (END_FINALLY, None),
                 (LOAD_FAST, ret_val)])
    return code


def compileTryCatch(comp, body, catches):
    """
    Compiles the try/catch/catch... form. Takes the body of the try statement,
    and a list of (exception, exception_var, except_body) tuples for each
    exception. The order of the list is important.
    """
    assert len(catches), "Calling compileTryCatch with empty catches list"

    catch_labels = [Label("TryCatch_{0}".format(ex)) for ex, _, _ in catches]
    endLabel = Label("TryCatchEnd")
    endFinallyLabel = Label("TryCatchEndFinally")
    firstExceptLabel = Label("TryFirstExcept")

    ret_val = "__ret_val_{0}".format(RT.nextID())

    code = [(SETUP_EXCEPT, firstExceptLabel)] # First catch label
    code.extend(body)
    code.append((STORE_FAST, ret_val)) # Because I give up with
    # keeping track of what's in the stack
    code.append((POP_BLOCK, None))
    code.append((JUMP_FORWARD, endLabel)) # if all went fine, goto end

    n = len(catches)
    for i, (exception, var, val) in enumerate(catches):

        comp.pushAlias(var, FnArgument(var)) # FnArgument will do

        last = i == n - 1

        # except Exception
        code.extend(emitLanding(catch_labels[i]))
        if i == 0:
            # first time only
            code.append((firstExceptLabel, None))
        code.append((DUP_TOP, None))
        code.extend(comp.compile(exception))
        code.append((COMPARE_OP, "exception match"))
        code.extend(emitJump(catch_labels[i + 1] if not last else
                             endFinallyLabel))

        # as e
        code.append((POP_TOP, None))
        code.append((STORE_FAST, var.name))
        code.append((POP_TOP, None))

        # body
        code.extend(comp.compile(val))
        code.append((STORE_FAST, ret_val))
        code.append((JUMP_FORWARD, endLabel))

        comp.popAlias(var)

    code.extend(emitLanding(endFinallyLabel))
    code.append((END_FINALLY, None))
    code.append((endLabel, None))
    code.append((LOAD_FAST, ret_val))

    return code

def compileTryCatchFinally(comp, body, catches, fin):
    """
    Compiles the try/catch/finally form.
    """
    assert len(catches), "Calling compileTryCatch with empty catches list"

    catch_labels = [Label("TryCatch_{0}".format(ex)) for ex, _, _ in catches]
    finallyLabel = Label("TryCatchFinally")
    notCaughtLabel = Label("TryCatchFinally2")
    firstExceptLabel = Label("TryFirstExcept")
    normalEndLabel = Label("NoExceptionLabel")

    ret_val = "__ret_val_{0}".format(RT.nextID())

    code = [
        (SETUP_FINALLY, finallyLabel),
        (SETUP_EXCEPT, firstExceptLabel)] # First catch label
    code.extend(body)
    code.append((STORE_FAST, ret_val)) # Because I give up with
    # keeping track of what's in the stack
    code.append((POP_BLOCK, None))
    code.append((JUMP_FORWARD, normalEndLabel))
    # if all went fine, goto finally

    n = len(catches)
    for i, (exception, var, val) in enumerate(catches):

        comp.pushAlias(var, FnArgument(var)) # FnArgument will do

        last = i == n - 1
        first = i == 0

        # except Exception
        code.extend(emitLanding(catch_labels[i]))
        if first:
            # After the emitLanding, so as to split the label
            code.append((firstExceptLabel, None))
        code.append((DUP_TOP, None))
        code.extend(comp.compile(exception))
        code.append((COMPARE_OP, "exception match"))
        code.extend(emitJump(catch_labels[i + 1] if not last
                             else notCaughtLabel))

        # as e
        code.append((POP_TOP, None))
        code.append((STORE_FAST, var.name))
        code.append((POP_TOP, None))

        # body
        code.extend(comp.compile(val))
        code.append((STORE_FAST, ret_val))
        code.append((JUMP_FORWARD, normalEndLabel))

        comp.popAlias(var)

    code.extend(emitLanding(notCaughtLabel))
    code.append((END_FINALLY, None))
    code.append((normalEndLabel, None))
    code.append((POP_BLOCK, None))
    code.append((LOAD_CONST, None))

    code.append((finallyLabel, None))
    code.extend(fin)
    code.append((POP_TOP, None))
    code.append((END_FINALLY, None))
    code.append((LOAD_FAST, ret_val))

    return code


"""
We should mention a few words about aliases. Aliases are created when the
user uses closures, fns, loop, let, or let-macro. For some forms like
let or loop, the alias just creates a new local variable in which to store the
data. In other cases, closures are created. To handle all these cases, we have
a base AAlias class which provides basic single-linked list abilites. This will
allow us to override what certain symbols resolve to.

For instance:

(fn bar [a b]
    (let [b (inc b)
          z 1]
        (let-macro [a (fn [fdecl& env& decl] 'z)]
            (let [o (fn [a] a)]
                 [a o b]))))

As each new local is created, it is pushed onto the stack, then only the
top most local is executed whenever a new local is resolved. This allows
the above example to resolve exactly as desired. lets will never stop on
top of eachother, let-macros can turn 'x into (.-x self), etc.
"""

class AAlias(object):
    """Base class for all aliases"""
    def __init__(self, rest = None):
        self.rest = rest
    def compile(self, comp):
        raise AbstractMethodCall(self)
    def compileSet(self, comp):
        raise AbstractMethodCall(self)
    def next(self):
        return self.rest


class FnArgument(AAlias):
    """An alias provided by the arguments to a fn*
       in the fragment (fn [a] a) a is a FnArgument"""
    def __init__(self, sym, rest = None):
        AAlias.__init__(self, rest)
        self.sym = sym
    def compile(self, comp):
        return [(LOAD_FAST, RT.name(self.sym))]
    def compileSet(self, comp):
        return [(STORE_FAST, RT.name(self.sym))]


class RenamedLocal(AAlias):
    """An alias created by a let, loop, etc."""
    def __init__(self, sym, rest = None):
        AAlias.__init__(self, rest)
        self.sym = sym
        self.newsym = Symbol(RT.name(sym) + str(RT.nextID()))
    def compile(self, comp):
        return [(LOAD_FAST, RT.name(self.newsym))]
    def compileSet(self, comp):
        return [(STORE_FAST, RT.name(self.newsym))]


class Closure(AAlias):
    """Represents a value that is contained in a closure"""
    def __init__(self, sym, rest = None):
        AAlias.__init__(self, rest)
        self.sym = sym
        self.isused = False  ## will be set to true whenever this is compiled
    def isUsed(self):
        return self.isused
    def compile(self, comp):
        self.isused = True
        return [(LOAD_DEREF, RT.name(self.sym))]
    def compileSet(self, comp):
        return [(STORE_DEREF, RT.name(self.sym))]


class LocalMacro(AAlias):
    """represents a value that represents a local macro"""
    def __init__(self, sym, macroform, rest = None):
        AAlias.__init__(self, rest)
        self.sym = sym
        self.macroform = macroform
    def compile(self, comp):
        code = comp.compile(self.macroform)
        return code


class SelfReference(AAlias):
    def __init__(self, var, rest = None):
        AAlias.__init__(self, rest)
        self.var = var
        self.isused = False
    def compile(self, comp):
        self.isused = True
        return [(LOAD_CONST, self.var),
                (LOAD_ATTR, "deref"),
                (CALL_FUNCTION, 0)]


class Name(object):
    """Slot for a name"""
    def __init__(self, name, rest=None):
        self.name = name
        self.isused = False
        self.rest = rest

    def __str__(self):
        v = []
        r = self
        while r is not None:
            v.append(r.name)
            r = r.rest
        v.reverse()
        s = "_".join(v)
        if self.isused:
            s = s + str(RT.nextID())
        return s


def evalForm(form, ns):
    comp = Compiler()
    code = comp.compile(form)
    code = expandMetas(code, comp)
    return comp.executeCode(code, ns)


def ismacro(macro):
    return (not isinstance(macro, type)
            and (hasattr(macro, "meta")
            and macro.meta()
            and macro.meta()[_MACRO_])
            or getattr(macro, "macro?", False))


def meta(form):
    return getattr(form, "meta", lambda: None)()


def macroexpand(form, comp, one=False):
    if isinstance(form.first(), Symbol):
        if form.first().ns == 'py' or form.first().ns == "py.bytecode":
            return form, False

        itm = findItem(comp.getNS(), form.first())
        dreffed = itm
        if isinstance(dreffed, Var):
            dreffed = itm.deref()

        # Handle macros here
        # TODO: Break this out into a seperate function
        if ismacro(itm) or ismacro(dreffed):
            macro = dreffed
            args = RT.seqToTuple(form.next())

            macroform = getattr(macro, "_macro-form", macro)

            mresult = macro(macroform, None, *args)

            if hasattr(mresult, "withMeta") and hasattr(form, "meta"):
                mresult = mresult.withMeta(form.meta())
            if not one:
                mresult = comp.compile(mresult)
            return mresult, True

    return form, False


class Compiler(object):
    def __init__(self):
        self.recurPoint = RT.list()
        self.names = None
        self.ns = clojure_core = Namespace("clojure.core")
        self.lastlineno = -1
        self.aliases = {}
        self.filename = "<unknown>"
        self._NS_ = findItem(clojure_core, _NS_)

    def setFile(self, filename):
        self.filename = filename

    def pushAlias(self, sym, alias):
        """ Pushes this alias onto the alias stack for the entry sym.
            if no entry is found, a new one is created """
        if sym in self.aliases:
            alias.rest = self.aliases[sym]
            self.aliases[sym] = alias
        else:
            self.aliases[sym] = alias

    def getAlias(self, sym):
        """ Retreives to top alias for this entry """
        if sym in self.aliases:
            return self.aliases[sym]
        return None

    def popAlias(self, sym):
        """ Removes the top alias for this entry. If the entry would be
            empty after this pop, the entry is deleted """
        if sym in self.aliases and self.aliases[sym].rest is None:
            del self.aliases[sym]
            return
        self.aliases[sym] = self.aliases[sym].rest
        return

    def popAliases(self, syms):
        for x in syms:
            self.popAlias(x)

    def pushRecur(self, label):
        """ Pushes a new recursion label. All recur calls will loop back to this point """
        self.recurPoint = RT.cons(label, self.recurPoint)
    def popRecur(self):
        """ Pops the top most recursion point """
        self.recurPoint = self.recurPoint.next()

    def pushName(self, name):
        if self.names is None:
            self.names = Name(name)
        else:
            self.names = Name(name, self.names)

    def popName(self):
        self.names = self.names.rest

    def getNamesString(self, markused=True):
        if self.names is None:
            return "fn_{0}".format(RT.nextID())
        s = str(self.names)
        if markused and self.names is not None:
            self.names.isused = True
        return s

    def compileMethodAccess(self, form):
        attrname = form.first().name[1:]
        if len(form) < 2:
            raise CompilerException(
                "Method access must have at least one argument", form)
        c = self.compile(form.next().first())
        c.append((LOAD_ATTR, attrname))
        s = form.next().next()
        while s is not None:
            c.extend(self.compile(s.first()))
            s = s.next()
        c.append((CALL_FUNCTION, (len(form) - 2)))
        return c

    def compilePropertyAccess(self, form):
        attrname = form.first().name[2:]
        if len(form) != 2:
            raise CompilerException(
                "Property access must have at only one argument", form)
        c = self.compile(form.next().first())
        c.append((LOAD_ATTR, attrname))
        return c

    def compileForm(self, form):
        if form.first() in builtins:
            return builtins[form.first()](self, form)
        form, ret = macroexpand(form, self)
        if ret:
            return form
        if isinstance(form.first(), Symbol):
            if form.first().ns == "py.bytecode":
                return compileBytecode(self, form)
            if form.first().name.startswith(".-"):
                return self.compilePropertyAccess(form)
            if form.first().name.startswith(".") and form.first().ns is None:
                return self.compileMethodAccess(form)
        c = self.compile(form.first())
        f = form.next()
        acount = 0
        while f is not None:
            c.extend(self.compile(f.first()))
            acount += 1
            f = f.next()
        c.append((CALL_FUNCTION, acount))

        return c

    def compileAccessList(self, sym):
        if sym.ns == 'py':
            return [(LOAD_CONST, getBuiltin(RT.name(sym)))]

        code = self.getAccessCode(sym)
        return code

    def getAccessCode(self, sym):
        if sym.ns is None or sym.ns == self.getNS().__name__:
            if self.getNS() is None:
                raise CompilerException("no namespace has been defined", None)
            if not hasattr(self.getNS(), RT.name(sym)):
                raise CompilerException(
                    "could not resolve '{0}', '{1}' not found in {2} reference {3}".
                    format(sym, RT.name(sym), self.getNS().__name__,
                           self.getNamesString(False)),
                    None)
            var = getattr(self.getNS(), RT.name(sym))
            return [GlobalPtr(self.getNS(), RT.name(sym))]

        if Symbol(sym.ns) in getattr(self.getNS(), "__aliases__", {}):
            sym = Symbol(self.getNS().__aliases__[Symbol(sym.ns)].__name__, RT.name(sym))

        splt = []
        if sym.ns is not None:
            module = findNS(sym.ns)
            if not hasattr(module, RT.name(sym)):
                raise CompilerException(
                    "{0} does not define {1}".format(module, RT.name(sym)),
                    None)
            return [GlobalPtr(module, RT.name(sym))]

        code = LOAD_ATTR if sym.ns else LOAD_GLOBAL
        #if not sym.ns and RT.name(sym).find(".") != -1 and RT.name(sym) != "..":
        raise CompilerException(
            "unqualified dotted forms not supported: {0}".format(sym), sym)

        if len(RT.name(sym).replace(".", "")):
            splt.extend((code, attr) for attr in RT.name(sym).split("."))
        else:
            splt.append((code, RT.name(sym)))
        return splt

    def compileSymbol(self, sym):
        """ Compiles the symbol. First the compiler tries to compile it
            as an alias, then as a global """
            
        if sym in self.aliases:
            return self.compileAlias(sym)

        return self.compileAccessList(sym)

    def compileAlias(self, sym):
        """ Compiles the given symbol as an alias."""
        alias = self.getAlias(sym)
        if alias is None:
            raise CompilerException("Unknown Local {0}".format(sym), None)
        return alias.compile(self)

    def closureList(self):
        closures = []
        for x in self.aliases:
            alias = self.aliases[x]
            if isinstance(alias, Closure) and alias.isUsed():
                closures.append(alias)
        return closures

    def compile(self, itm):
        try:
            c = []
            lineset = False
            if getattr(itm, "meta", lambda: None)() is not None:
                line = itm.meta()[LINE_KEY]
                if line is not None and line > self.lastlineno:
                    lineset = True
                    self.lastlineno = line
                    c.append([SetLineno, line])

            if isinstance(itm, Symbol):
                c.extend(self.compileSymbol(itm))
            elif isinstance(itm, PersistentList) or isinstance(itm, Cons):
                c.extend(self.compileForm(itm))
            elif itm is None:
                c.extend(self.compileNone(itm))
            elif type(itm) in [str, int, types.ClassType, type, Var]:
                c.extend([(LOAD_CONST, itm)])
            elif isinstance(itm, IPersistentVector):
                c.extend(compileVector(self, itm))
            elif isinstance(itm, IPersistentMap):
                c.extend(compileMap(self, itm))
            elif isinstance(itm, Keyword):
                c.extend(compileKeyword(self, itm))
            elif isinstance(itm, bool):
                c.extend(compileBool(self, itm))
            elif isinstance(itm, EmptyList):
                c.append((LOAD_CONST, itm))
            elif isinstance(itm, unicode):
                c.append((LOAD_CONST, itm))
            elif isinstance(itm, float):
                c.append((LOAD_CONST, itm))
            elif isinstance(itm, long):
                c.append((LOAD_CONST, itm))
            elif isinstance(itm, fractions.Fraction):
                c.append((LOAD_CONST, itm))
            elif isinstance(itm, IPersistentSet):
                c.append((LOAD_CONST, itm))
            elif isinstance(itm, type(re.compile(""))):
                c.append((LOAD_CONST, itm))
            else:
                raise CompilerException(
                    " don't know how to compile {0}".format(type(itm)), None)

            if len(c) < 2 and lineset:
                return []
            return c
        except:
            print "Compiling {0}".format(itm)
            raise

    def compileNone(self, itm):
        return [(LOAD_CONST, None)]

    def setNS(self, ns):
        self.ns = Namespace(ns)

    def getNS(self):
        return self.ns

    def executeCode(self, code, ns=None):
        ns = ns or self.getNS()
        if code == []:
            return None
        newcode = expandMetas(code, self)
        newcode.append((RETURN_VALUE, None))
        c = Code(newcode, [], [], False, False, False,
                 str(Symbol(ns.__name__, "<string>")), self.filename, 0, None)
        try:
            c = c.to_code()
        except:
            for x in newcode:
                print x
            raise

        # work on .cljs
        #from clojure.util.freeze import write, read
        #with open("foo.cljs", "wb") as fl:
        #    f = write(c, fl)

        with threadBindings({self._NS_: ns}):
            retval = eval(c, ns.__dict__)
        return retval

    def pushPropertyAlias(self, mappings):
        locals = {}
        for x in mappings:
            if x in self.aliasedProperties:
                self.aliasedProperties[x].append(mappings[x])
            else:
                self.aliasedProperties[x] = [mappings[x]]

    def popPropertyAlias(self, mappings):
        dellist = []
        for x in mappings:
            self.aliasedProperties[x].pop()
            if not len(self.aliasedProperties[x]):
                dellist.append(x)
        for x in dellist:
            del self.aliasedProperties[x]

    def standardImports(self):
        return [(LOAD_CONST, -1),
            (LOAD_CONST, None),
            (IMPORT_NAME, "clojure.standardimports"),
            (IMPORT_STAR, None)]

    def executeModule(self, code):
        code.append((RETURN_VALUE, None))
        c = Code(code, [], [], False, False, False,
                 str(Symbol(self.getNS().__name__, "<string>")), self.filename, 0, None)

        dis.dis(c)
        codeobject = c.to_code()

        with open('output.pyc', 'wb') as fc:
            fc.write(py_compile.MAGIC)
            py_compile.wr_long(fc, long(time.time()))
            marshal.dump(c, fc)

########NEW FILE########
__FILENAME__ = cons
import cStringIO

from clojure.lang.aseq import ASeq
from clojure.lang.cljexceptions import ArityException
from clojure.lang.persistentlist import EMPTY
import clojure.lang.rt as RT


class Cons(ASeq):
    def __init__(self, *args):
        """Instantiate a Cons.

        args must be one of:

        * object, ISeq
          head and tail, respectively

        * IPersistentMap, object, ISeq
          meta data, head and tail

        Else an ArityException will be raised."""
        if len(args) == 2:
            self._meta = None
            self._first = args[0]
            self._more = args[1]
        elif len(args) == 3:
            self._meta = args[0]
            self._first = args[1]
            self._more = args[2]
        else:
            raise ArityException()

    def first(self):
        """Return the first item in this cons."""
        return self._first

    def next(self):
        """Return an ISeq or None.

        If there is one item in the cons, return None, else return an ISeq on
        the items after the first."""
        return self.more().seq()

    def more(self):
        """Return an ISeq,

        If there is more than one item in the cons, return the items after
        the first, else return an empty PersistentList."""
        if self._more is None:
            return EMPTY
        return self._more

    def withMeta(self, meta):
        """Return a Cons with meta attached.

        meta -- IPersistentMap

        The returned cons will share the head and tail with this cons."""
        return Cons(meta, self._first, self._more)

    def __len__(self):
        """Return the number of items in this Cons."""
        c = 0
        while self is not None:
            c += 1
            self = self.next()
        return c

########NEW FILE########
__FILENAME__ = counted
from clojure.lang.cljexceptions import AbstractMethodCall

class Counted(object):
    def __len__(self):
        raise AbstractMethodCall(self)
########NEW FILE########
__FILENAME__ = fileseq
from clojure.lang.aseq import ASeq
from clojure.lang.cljexceptions import IllegalAccessError, ArityException, InvalidArgumentException

def isReader(rdr):
    return hasattr(rdr, "read") and hasattr(rdr, "tell")


class FileSeq(ASeq):
    def __init__(self, *args):
        if len(args) == 1:
            if not isReader(args[0]):
                raise InvalidArgumentException("must pass in a object with a read() method")
            FileSeq.__init__(self, args[0], 1, 1, args[0].read(1))
            return
        elif len(args) == 4:
            self.rdr, self.line, self.col, self.ccur = args
            self._next = None

    def first(self):
        return self.ccur

    def reuseNext(self, nxt):
        c = self.rdr.read(1)
        if c == "":
            return None

        newline = self.line + 1 if c == '\n' else self.line
        newcol = 1 if newline != self.line else self.col + 1

        nxt.rdr = self.rdr
        nxt.line = newline
        nxt.col = newcol
        nxt.ccur = c
        nxt._next = None
        return nxt

    def next(self):
        if self._next is not None:
            return self._next
        c = self.rdr.read(1)
        if c == "":
            return None

        newline = self.line + 1 if c == '\n' else self.line
        newcol = 1 if newline != self.line else self.col + 1

        # Nasty mutation here please don't use this
        # with threads
        self._next = FileSeq(self.rdr, newline, newcol, c)
        return self._next

    def lineCol(self):
        return [self.line, self.col]

    def tell(self):
        return self.rdr.tell()

    def atLineStart(self):
        return self.col == 1

    def atLineEnd(self):
        nxt = self.next()
        return True if nxt is None else nxt.atLineStart()

    def __eq__(self, other):
        if isinstance(other, str):
            return self.ccur == other
        if other is None:
            return False
        if self is other:
            return True
        if self.rdr is other.rdr and \
           self.tell() == other.tell():
            return True
        return False

    def __ne__(self, other):
        return not self == other


class MutatableFileSeq(ASeq):
    def __init__(self, fs):
        self.fs = fs
        self.old = None
        self.d = dir

    def first(self):
        return self.fs.first()

    def next(self):
        o = self.old
        self.old = self.fs
        if o is not None:
            ret = self.fs.reuseNext(o)
        else:
            ret = self.fs.next()
        self.fs = ret
        return ret

    def back(self):
        if self.old is None:
            raise InvalidArgumentException("Can only go back once")
        self.fs = self.old
        self.old = None

    def lineCol(self):
        return self.fs.lineCol() if self.fs is not None else [None, None]


class StringReader(object):
    def __init__(self, s):
        self.line = 1;
        self.col = 1
        self.idx = -1
        self.s = s
        self.lastline = -1
        self.lastcol = -1
        self.haslast = False

    def read(self):
        self.lastcol = self.col
        self.lastline = self.line
        self.haslast = True
        self.idx += 1
        if self.idx >= len(self.s):
            return ""

        cc = self.s[self.idx]
        if cc == '\n':
            self.line += 1;
            self.col = 1
        return cc

    def next(self):
        self.read()
        return self

    def first(self):
        return self.s[self.idx] if self.idx < len(self.s) else ""

    def lineCol(self):
        return [self.line, self.col]

    def back(self):
        if not self.haslast:
            raise IllegalAccessError()
        self.idx -= 1
        self.haslast = False
        self.line = self.lastline
        self.col = self.lastcol

########NEW FILE########
__FILENAME__ = globals
from clojure.lang.var import Var

currentCompiler = Var()
currentCompiler.setDynamic()


########NEW FILE########
__FILENAME__ = gmp
#
# Copyright (c) 2009 Noah Watkins <noah@noahdesu.com>
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following
# conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT  OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#

from ctypes import *
from ctypes.util import find_library

# find the GMP library
_libgmp_path = find_library('gmp')
if not _libgmp_path:
    raise EnvironmentError('Unable to find libgmp')
_libgmp = CDLL(_libgmp_path)

#
# GNU MP structures
#
#  - TODO: choose between different definitions of these structures based on
#  checking library/arch. For example, different library configuration options
#  and 32-bit/64-bit systems.
#
class c_mpz_struct(Structure):
    _fields_ = [
        ('_mp_alloc',   c_int),
        ('_mp_size',    c_int),
        ('_mp_d',       POINTER(c_ulonglong))]

class c_gmp_randstate_struct(Structure):
    _fields_ = [
        ('_mp_seed',    c_mpz_struct),
        ('_mp_alg',     c_int),
        ('_mp_algdata', c_voidp)]

class c_mpq_struct(Structure):
    _fields_ = [
        ('_mp_num',     c_mpz_struct),
        ('_mp_den',     c_mpz_struct)]

class c_mpf_struct(Structure):
    _fields_ = [
        ('_mp_prec',    c_int),
        ('_mp_size',    c_int),
        ('_mp_exp',     c_long),
        ('_mp_d',       POINTER(c_long))]

#------------------------------------------------------------------------------
# Function references into MP library
#------------------------------------------------------------------------------

# Gnu MP integer routines
_MPZ_init = _libgmp.__gmpz_init
_MPZ_clear = _libgmp.__gmpz_clear
_MPZ_add = _libgmp.__gmpz_add
_MPZ_sub = _libgmp.__gmpz_sub
_MPZ_mul = _libgmp.__gmpz_mul
_MPZ_div = _libgmp.__gmpz_tdiv_q
_MPZ_mod = _libgmp.__gmpz_mod
_MPZ_and = _libgmp.__gmpz_and
_MPZ_ior = _libgmp.__gmpz_ior
_MPZ_xor = _libgmp.__gmpz_xor
_MPZ_abs = _libgmp.__gmpz_abs
_MPZ_neg = _libgmp.__gmpz_neg
_MPZ_cmp = _libgmp.__gmpz_cmp
_MPZ_set_str = _libgmp.__gmpz_set_str
_MPZ_get_str = _libgmp.__gmpz_get_str
_MPZ_urandomb = _libgmp.__gmpz_urandomb
_MPZ_urandomm = _libgmp.__gmpz_urandomm
_MPZ_rrandomb = _libgmp.__gmpz_rrandomb

# Gnu MP floating point routines
_MPF_set_default_prec = _libgmp.__gmpf_set_default_prec
_MPF_init = _libgmp.__gmpf_init
_MPF_clear = _libgmp.__gmpf_clear
_MPF_add = _libgmp.__gmpf_add
_MPF_sub = _libgmp.__gmpf_sub
_MPF_mul = _libgmp.__gmpf_mul
_MPF_div = _libgmp.__gmpf_div
_MPF_abs = _libgmp.__gmpf_abs
_MPF_neg = _libgmp.__gmpf_neg
_MPF_cmp = _libgmp.__gmpf_cmp
_MPF_eq  = _libgmp.__gmpf_eq
_MPF_set_str = _libgmp.__gmpf_set_str
_MPF_get_str = _libgmp.__gmpf_get_str


# Gnu MP random generator routines
_GMP_randinit_default = _libgmp.__gmp_randinit_default
_GMP_randinit_mt = _libgmp.__gmp_randinit_mt
_GMP_randclear = _libgmp.__gmp_randclear
_GMP_randseed = _libgmp.__gmp_randseed
_GMP_urandomm = _libgmp.__gmpz_urandomm

# Gnu MP rational number routines
_MPQ_init = _libgmp.__gmpq_init
_MPQ_clear = _libgmp.__gmpq_clear
_MPQ_add = _libgmp.__gmpq_add
_MPQ_sub = _libgmp.__gmpq_sub
_MPQ_mul = _libgmp.__gmpq_mul
_MPQ_div = _libgmp.__gmpq_div
_MPQ_abs = _libgmp.__gmpq_abs
_MPQ_neg = _libgmp.__gmpq_neg
_MPQ_cmp = _libgmp.__gmpq_cmp
_MPQ_set_str = _libgmp.__gmpq_set_str
_MPQ_get_str = _libgmp.__gmpq_get_str

# Gnu MP random generator algorithms
RAND_ALGO_DEFAULT = _GMP_randinit_default
RAND_ALGO_MT = _GMP_randinit_mt

#------------------------------------------------------------------------------
# Wrappers around Gnu MP Integer, Rational, Random, Float
#------------------------------------------------------------------------------

class Integer(object):
    def __init__(self, init_value=0):
        self._mpz = c_mpz_struct()
        self._mpzp = byref(self._mpz)
        _MPZ_init(self)
        self.set(init_value)

    def __del__(self):
        _MPZ_clear(self)

    @property
    def _as_parameter_(self):
        return self._mpzp

    @staticmethod
    def from_param(arg):
        assert isinstance(arg, Integer)
        return arg

    def __apply_ret(self, func, ret, op1, op2):
        assert isinstance(ret, Integer)
        if not isinstance(op1, Integer):
            op1 = Integer(op1)
        if not isinstance(op2, Integer):
            op2 = Integer(op2)
        func(ret, op1, op2)
        return ret

    def __apply_ret_2_0(self, func, ret, op1):
        assert isinstance(ret, Integer)
        assert isinstance(op1, Integer)
        func(ret, op1)
        return ret

    def __apply_ret_2_1(self, func, op1, op2):
        if not isinstance(op1, Integer):
            op1 = Integer(op1)
        if not isinstance(op2, Integer):
            op2 = Integer(op2)
        return func(op1, op2)

    def set(self, value, radix = 10):
        if isinstance(value, Integer):
            _MPZ_set_str(self, value.__str__(), radix)
        elif isinstance(value, str):
            _MPZ_set_str(self, value, radix)
        else:
            try:
                _MPZ_set_str(self, str(int(value)), radix)
            except:
                raise TypeError, "non-int"

    def __str__(self):
        return _MPZ_get_str(None, 10, self)

    def __repr__(self):
        return self.__str__()

    def __lt__(self, other):
        return self.__apply_ret_2_1(_MPZ_cmp, self, other) < 0

    def __le__(self, other):
        return self.__lt__(other) or self.__eq__(other)

    def __eq__(self, other):
        return self.__apply_ret_2_1(_MPZ_cmp, self, other) == 0

    def __ne__(self, other):
        return not self.__eq__(other)

    def __gt__(self, other):
        return self.__apply_ret_2_1(_MPZ_cmp, self, other) > 0

    def __ge__(self, other):
        return self.__gt__(other) or self.__eq__(other)

    def __add__(self, other):
        return self.__apply_ret(_MPZ_add, Integer(), self, other)

    def __sub__(self, other):
        return self.__apply_ret(_MPZ_sub, Integer(), self, other)

    def __mul__(self, other):
        return self.__apply_ret(_MPZ_mul, Integer(), self, other)

    def __div__(self, other):
        return self.__apply_ret(_MPZ_div, Integer(), self, other)

    def __and__(self, other):
        return self.__apply_ret(_MPZ_and, Integer(), self, other)

    def __mod__(self, other):
        return self.__apply_ret(_MPZ_mod, Integer(), self, other)

    def __xor__(self, other):
        return self.__apply_ret(_MPZ_xor, Integer(), self, other)

    def __or__(self, other):
        return self.__apply_ret(_MPZ_ior, Integer(), self, other)

    def __iadd__(self, other):
        return self.__apply_ret(_MPZ_add, self, self, other)

    def __isub__(self, other):
        return self.__apply_ret(_MPZ_sub, self, self, other)

    def __imul__(self, other):
        return self.__apply_ret(_MPZ_mul, self, self, other)

    def __imod__(self, other):
        return self.__apply_ret(_MPZ_mod, self, self, other)

    def __iand__(self, other):
        return self.__apply_ret(_MPZ_and, self, self, other)

    def __ixor__(self, other):
        return self.__apply_ret(_MPZ_xor, self, self, other)

    def __ior__(self, other):
        return self.__apply_ret(_MPZ_ior, self, self, other)

    def __radd__(self, other):
        return self.__apply_ret(_MPZ_add, Integer(), other, self)

    def __rsub__(self, other):
        return self.__apply_ret(_MPZ_sub, Integer(), other, self)

    def __rmul__(self, other):
        return self.__apply_ret(_MPZ_mul, Integer(), other, self)

    def __rdiv__(self, other):
        return self.__apply_ret(_MPZ_div, Integer(), other, self)

    def __rmod__(self, other):
        return self.__apply_ret(_MPZ_mod, Integer(), other, self)

    def __abs__(self):
        return self.__apply_ret_2_0(_MPZ_abs, Integer(), self)

    def __neg__(self):
        return self.__apply_ret_2_0(_MPZ_neg, Integer(), self)

class Rational(object):
    def __init__(self):
        self._mpq = c_mpq_struct()
        self._mpqp = byref(self._mpq)
        _MPQ_init(self)

    def __del__(self):
        _MPQ_clear(self)

    @property
    def _as_parameter_(self):
        return self._mpqp

    @staticmethod
    def from_param(arg):
        assert isinstance(arg, Rational)
        return arg

    def __apply_ret(self, func, ret, op1, op2):
        assert isinstance(ret, Rational)
        if not isinstance(op1, Rational):
            op1 = Rational(op1)
        if not isinstance(op2, Rational):
            op2 = Rational(op2)
        func(ret, op1, op2)
        return ret

    def __apply_ret_2_0(self, func, ret, op1):
        assert isinstance(ret, Rational)
        assert isinstance(op1, Rational)
        func(ret, op1)
        return ret

    def __apply_ret_2_1(self, func, op1, op2):
        if not isinstance(op1, Rational):
            op1 = Rational(op1)
        if not isinstance(op2, Rational):
            op2 = Rational(op2)
        return func(op1, op2)

    def set(self, value):
        if isinstance(value, Rational):
            _MPQ_set_str(self, value.__str__(), 10)
        else:
            try:
                _MPQ_set_str(self, str(float(value)), 10)
            except Exception as e:
                raise TypeError, "non-rational"

    def __str__(self):
        return _MPQ_get_str(None, 10, self)

    def __repr__(self):
        return self.__str__()

    def __lt__(self, other):
        return self.__apply_ret_2_1(_MPQ_cmp, self, other) < 0

    def __le__(self, other):
        return self.__lt__(other) or self.__eq__(other)

    def __eq__(self, other):
        return self.__apply_ret_2_1(_MPQ_cmp, self, other) == 0

    def __ne__(self, other):
        return not self.__eq__(other)

    def __gt__(self, other):
        return self.__apply_ret_2_1(_MPQ_cmp, self, other) > 0


    def __ge__(self, other):
        return self.__gt__(other) or self.__eq__(other)

    def __add__(self, other):
        return self.__apply_ret(_MPQ_add, Rational(), self, other)

    def __sub__(self, other):
        return self.__apply_ret(_MPQ_sub, Rational(), self, other)

    def __mul__(self, other):
        return self.__apply_ret(_MPQ_mul, Rational(), self, other)

    def __iadd__(self, other):
        return self.__apply_ret(_MPQ_add, self, self, other)

    def __isub__(self, other):
        return self.__apply_ret(_MPQ_sub, self, self, other)

    def __imul__(self, other):
        return self.__apply_ret(_MPQ_mul, self, self, other)

    def __abs__(self):
        return self.__apply_ret_2_0(_MPQ_abs, Rational(), self)

    def __neg__(self):
        return self.__apply_ret_2_0(_MPQ_neg, Rational(), self)

class Float(object):
    def __init__(self, init_value=0.0, precision=None):
        self._mpf = c_mpf_struct()
        self._mpfp = byref(self._mpf)
        _MPF_init(self)
        self.set(init_value)

    def __del__(self):
        _MPF_clear(self)

    def set(self, value):
        if isinstance(value, Float):
            _MPF_set_str(self, value.__str__(), 10)
        elif isinstance(value, str):
            _MPF_set_str(self, value)
        else:
            try:
                _MPF_set_str(self, str(float(value)), 10)
            except Exception as e:
                raise TypeError, "non-float"

    def __apply_ret(self, func, ret, op1, op2):
        assert isinstance(ret, Float)
        if not isinstance(op1, Float):
            op1 = Float(op1)
        if not isinstance(op2, Float):
            op2 = Float(op2)
        func(ret, op1, op2)
        return ret

    def __apply_ret_2_0(self, func, ret, op1):
        assert isinstance(ret, Float)
        assert isinstance(op1, Float)
        func(ret, op1)
        return ret

    def __apply_ret_2_1(self, func, op1, op2):
        if not isinstance(op1, Float):
            op1 = Float(op2)
        if not isinstance(op2, Float):
            op2 = Float(op2)
        return func(op1, op2)

    #Extra apply_ret for 3 args with return - for _eq
    def __apply_ret_3_1(self, func, op1, op2, op3):
        if(not isinstance(op2, Float)):
            op2 = Float(op2)
        return func(op1, op2, op3)

    @property
    def _as_parameter_(self):
        return self._mpfp

    @staticmethod
    def from_param(arg):
        assert isinstance(arg, Float)
        return arg

    def __str__(self):
        exp = (c_byte*4)()
        exp = cast(exp, POINTER((c_int)))
        return _MPF_get_str(None, exp, 10, 10, self)

    def __repr__(self):
        return self.__str__()

    def __lt__(self, other):
        return self.__apply_ret_2_1(_MPF_cmp, self, other) < 0

    def __le__(self, other):
        return self.__lt__(other) or self.__eq__(other)

    def __eq__(self, other):
        return self.__apply_ret_3_1(_MPF_eq, self, other, c_int(32)) != 0

    def __ne__(self, other):
        return not self.__eq__(other)

    def __gt__(self, other):
        return self.__apply_ret_2_1(_MPF_cmp, self, other) > 0

    def __ge__(self, other):
        return self.__gt__(other) or self.__eq__(other)

    def __add__(self, other):
        return self.__apply_ret(_MPF_add, Float(), self, other)

    def __sub__(self, other):
        return self.__apply_ret(_MPF_sub, Float(), self, other)

    def __mul__(self, other):
        return self.__apply_ret(_MPF_mul, Float(), self, other)

    def __div__(self, other):
        return self.__apply_ret(_MPF_div, Float(), self, other)

    def __iadd__(self, other):
        return self.__apply_ret(_MPF_add, self, self, other)

    def __isub__(self, other):
        return self.__apply_ret(_MPF_sub, self, self, other)

    def __imul__(self, other):
        return self.__apply_ret(_MPF_mul, self, self, other)

    def __radd__(self, other):
        return self.__apply_ret(_MPF_add, Float(), other, self)

    def __rsub__(self, other):
        return self.__apply_ret(_MPF_sub, Float(), other, self)

    def __rmul__(self, other):
        return self.__apply_ret(_MPF_mul, Float(), other, self)

    def __rdiv__(self, other):
        return self.__apply_ret(_MPF_div, Float(), other, self)

    def __idiv__(self, other):
        return self.__apply_ret(_MPF_div, self, self, other)

    def __abs__(self):
        return self.__apply_ret_2_0(_MPF_abs, Float(), self)

    def __neg__(self):
        return self.__apply_ret_2_0(_MPF_neg, Float(), self)


class Random(object):
    def __init__(self, algo=RAND_ALGO_DEFAULT):
        self._gmp = c_gmp_randstate_struct()
        self._gmpp = byref(self._gmp)

        if algo in [RAND_ALGO_DEFAULT, RAND_ALGO_MT]:
            algo(self)
        else:
            raise Exception, "Algorithm not available"

    def __del__(self):
        _GMP_randclear(self)

    @property
    def _as_parameter_(self):
        return self._gmpp

    @staticmethod
    def from_param(arg):
        assert isinstance(arg, Random)
        return arg

    def __apply_ret(self, func, ret, op1, op2):
        func(ret, op1, op2)
        return ret

    def seed(self, s):
        if not isinstance(s, Integer):
            s = Integer(s)
        _GMP_randseed(self, s)

    def urandom(self, n):
        ret = Integer()
        if not isinstance(n, Integer):
            n = Integer(n)
        _GMP_urandomm(ret, self, n)
        return ret

#------------------------------------------------------------------------------
# Argument/return-type specs for Gnu MP routines
#------------------------------------------------------------------------------

# Gnu MP random generator routines
_GMP_randinit_default.argtypes = (Random,)
_GMP_randinit_mt.artypes = (Random,)
_GMP_randclear.argtypes = (Random,)
_GMP_randseed.argtypes = (Random, Integer)
_GMP_urandomm.argtypes = (Integer, Random, Integer)

# Gnu MP integer routines
_MPZ_init.argtypes = (Integer,)
_MPZ_clear.argtypes = (Integer,)
_MPZ_add.argtypes = (Integer, Integer, Integer)
_MPZ_sub.argtypes = (Integer, Integer, Integer)
_MPZ_mul.argtypes = (Integer, Integer, Integer)
_MPZ_mod.argtypes = (Integer, Integer, Integer)
_MPZ_and.argtypes = (Integer, Integer, Integer)
_MPZ_ior.argtypes = (Integer, Integer, Integer)
_MPZ_xor.argtypes = (Integer, Integer, Integer)
_MPZ_abs.argtypes = (Integer, Integer)
_MPZ_neg.argtypes = (Integer, Integer)
_MPZ_cmp.argtypes = (Integer, Integer)
_MPZ_set_str.argtypes = (Integer, c_char_p, c_int)
_MPZ_get_str.argtypes = (c_char_p, c_int, Integer,)
# non-default (int) return types
_MPZ_get_str.restype = c_char_p

# Gnu MP rational number routines
_MPQ_init.argtypes = (Rational,)
_MPQ_clear.argtypes = (Rational,)
_MPQ_add.argtypes = (Rational, Rational, Rational)
_MPQ_sub.argtypes = (Rational, Rational, Rational)
_MPQ_mul.argtypes = (Rational, Rational, Rational)
_MPQ_abs.argtypes = (Rational, Rational)
_MPQ_neg.argtypes = (Rational, Rational)
_MPQ_cmp.argtypes = (Rational, Rational)
_MPQ_set_str.argtypes = (Rational, c_char_p, c_int)
_MPQ_get_str.argtypes = (c_char_p, c_int, Rational,)
# non-default (int) return types
_MPQ_get_str.restype = c_char_p

# Gnu MP floating point routines
_MPF_set_default_prec.argtypes = (c_ulong,)
_MPF_init.argtypes = (Float,)
_MPF_clear.argtypes = (Float,)
_MPF_add.argtypes = (Float, Float, Float)
_MPF_sub.argtypes = (Float, Float, Float)
_MPF_mul.argtypes = (Float, Float, Float)
_MPF_abs.argtypes = (Float, Float)
_MPF_neg.argtypes = (Float, Float)
_MPF_cmp.argtypes = (Float, Float)
_MPF_eq.argtypes =  (Float, Float, c_int)
_MPF_set_str.argtypes = (Float, c_char_p, c_int)
_MPF_get_str.argtypes = (c_char_p, POINTER(c_int), c_int, c_int, Float)
# non-default (int) return types
_MPF_get_str.restype = c_char_p
########NEW FILE########
__FILENAME__ = ideref
from clojure.lang.cljexceptions import AbstractMethodCall

class IDeref(object):
    def deref(self):
        raise AbstractMethodCall(self)

########NEW FILE########
__FILENAME__ = ieditablecollection
from clojure.lang.cljexceptions import AbstractMethodCall

class IEditableCollection(object):
    def asTransient(self):
        raise AbstractMethodCall(self)

########NEW FILE########
__FILENAME__ = ifn
from clojure.lang.cljexceptions import AbstractMethodCall

class IFn(object):
    def __call__(self, *args):
        raise AbstractMethodCall(self)
########NEW FILE########
__FILENAME__ = ihasheq
from clojure.lang.cljexceptions import AbstractMethodCall

class IHashEq(object):
    def hasheq(self):
        raise AbstractMethodCall(self)
########NEW FILE########
__FILENAME__ = ilookup
from clojure.lang.cljexceptions import AbstractMethodCall

class ILookup(object):
    def valAt(self, key, notFound=None):
        raise AbstractMethodCall(self)

########NEW FILE########
__FILENAME__ = imeta
from clojure.lang.cljexceptions import AbstractMethodCall

class IMeta(object):
    def meta(self):
        raise AbstractMethodCall(self)
########NEW FILE########
__FILENAME__ = indexableseq
from clojure.lang.aseq import ASeq
from clojure.lang.counted import Counted


class IndexableSeq(ASeq, Counted):
    def __init__(self, array, i):
        self.array = array
        self.i = i

    def first(self):
        return self.array[self.i]

    def next(self):
        if self.i >= len(self.array) - 1:
            return None
        return IndexableSeq(self.array, self.i + 1)

    def __len__(self):
        return len(self.array) - self.i

    def __repr__(self):
        c = []
        for x in range(self.i, len(self.array)):
            c.append(str(self.array[x]))
        return "[" + " ".join(c) + "]"


def create(obj):
    if len(obj) == 0:
        return None
    return IndexableSeq(obj, 0)

########NEW FILE########
__FILENAME__ = indexed
from clojure.lang.cljexceptions import AbstractMethodCall
from clojure.lang.counted import Counted


class Indexed(Counted):
    def nth(self, i, notFound = None):
        raise AbstractMethodCall(self)

########NEW FILE########
__FILENAME__ = iobj
from clojure.lang.cljexceptions import AbstractMethodCall

class IObj(object):
    def withMeta(self, meta):
        raise AbstractMethodCall(self)

########NEW FILE########
__FILENAME__ = ipersistentcollection
from clojure.lang.cljexceptions import AbstractMethodCall
from clojure.lang.seqable import Seqable

class IPersistentCollection(Seqable):
    def count(self):
        raise AbstractMethodCall(self)

    def cons(self, o):
        raise AbstractMethodCall(self)

    def empty(self):
        raise AbstractMethodCall(self)


########NEW FILE########
__FILENAME__ = ipersistentlist
from clojure.lang.ipersistentstack import IPersistentStack
from clojure.lang.sequential import Sequential

class IPersistentList(Sequential, IPersistentStack):
    pass

########NEW FILE########
__FILENAME__ = ipersistentmap
from clojure.lang.cljexceptions import AbstractMethodCall
from clojure.lang.associative import Associative
from clojure.lang.iterable import Iterable
from clojure.lang.counted import Counted


class IPersistentMap(Iterable, Associative, Counted):
    def without(self, key):
        raise AbstractMethodCall(self)

########NEW FILE########
__FILENAME__ = ipersistentset
from clojure.lang.cljexceptions import AbstractMethodCall
from clojure.lang.ipersistentcollection import IPersistentCollection
from clojure.lang.counted import Counted

class IPersistentSet(IPersistentCollection, Counted):
    def disjoin(self, key):
        raise AbstractMethodCall(self)

    def __contains__(self, item):
        raise AbstractMethodCall(self)

    def __getitem__(self, item):
        return self.get(item)

########NEW FILE########
__FILENAME__ = ipersistentstack
from clojure.lang.cljexceptions import AbstractMethodCall
from clojure.lang.ipersistentcollection import IPersistentCollection

class IPersistentStack(IPersistentCollection):
    def peek(self):
        raise AbstractMethodCall(self)

    def pop(self):
        raise AbstractMethodCall(self)

########NEW FILE########
__FILENAME__ = ipersistentvector
from clojure.lang.associative import Associative
from clojure.lang.sequential import Sequential
from clojure.lang.ipersistentstack import IPersistentStack
from clojure.lang.reversible import Reversible
from clojure.lang.indexed import Indexed
from clojure.lang.cljexceptions import AbstractMethodCall


class IPersistentVector(Associative, Sequential, IPersistentStack, Reversible, Indexed):
    def __len__(self):
        raise AbstractMethodCall(self)

    def assocN(self, i, val):
        raise AbstractMethodCall(self)

    def cons(self, o):
        raise AbstractMethodCall(self)

########NEW FILE########
__FILENAME__ = iprintable
from clojure.lang.cljexceptions import AbstractMethodCall


class IPrintable(object):
    """Pseudo-Interface to define an object->string protocol.

    An object that subclasses IPrintable must implement theses two methods:

    * writeAsString
    * writeAsReplString

    The behavior of these methods is described in their doc strings but both
    of these methods should adhere to a few suggestions:

    * Don't flush the writer
    * Don't pretty-print to the writer
    * Don't write leading or trailing white space
      (including a trailing newline)"""

    def writeAsString(self, writer):
        """Write a user-friendly string to writer.

        writer -- a writable stream such as sys.stdout, StringIO, etc.

        This function mimics the Python __str__ method. If the printed
        representation is the same at the Python repl and at the clojure-py
        repl, this method could simply write str(self)."""
        raise AbstractMethodCall(self)

    def writeAsReplString(self, writer):
        """Write a string readable by the clojure-py reader to writer.

        writer -- a writable stream such as sys.stdout, StringIO, etc.

        This function mimics the Python __repl__ method. But, we're writing a
        clojure-py readable string, *not* a Python readable string. If the
        object is unreadable it must have the form:

        #<fully.qualified.Name object at 0xADDRESS foo>

        The last foo is optional and can be any string of printable
        characters.

        An example of this is the Python list. clojure-py has extended the
        IPrintable protocol to include these objectS.

        user=> sys/path
        #<__builtin__.list object at 0xdeadbeef>
        user=>"""
        raise AbstractMethodCall(self)

########NEW FILE########
__FILENAME__ = ireduce
from clojure.lang.cljexceptions import AbstractMethodCall

class IReduce(object):
    def reduce(self, *args):
        raise AbstractMethodCall(self)

########NEW FILE########
__FILENAME__ = iref
from clojure.lang.cljexceptions import AbstractMethodCall
from clojure.lang.ideref import IDeref

class IRef(IDeref):
    def setValidator(self, fn):
        raise AbstractMethodCall(self)

    def getValidator(self):
        raise AbstractMethodCall(self)

    def getWatches(self):
        raise AbstractMethodCall(self)

    def addWatch(self, key, fn):
        raise AbstractMethodCall(self)

    def removeWatch(self, key):
        raise AbstractMethodCall(self)

########NEW FILE########
__FILENAME__ = ireference
from clojure.lang.cljexceptions import AbstractMethodCall
from clojure.lang.imeta import IMeta

class IReference(IMeta):
    def alterMeta(self, fn, args):
        raise AbstractMethodCall(self)

    def resetMeta(self, meta):
        raise AbstractMethodCall(self);

########NEW FILE########
__FILENAME__ = iseq
from clojure.lang.cljexceptions import AbstractMethodCall
from clojure.lang.ipersistentcollection import IPersistentCollection

class ISeq(IPersistentCollection):
    def first(self):
        """Return the first item in the collection or None if it's empty."""
        raise AbstractMethodCall(self)

    def next(self):
        """Return the *tail* of the collection or None if () or (x)."""
        raise AbstractMethodCall(self)

    def more(self):
        """Return the *tail* of the collection or () if () or (x)."""
        raise AbstractMethodCall(self)

    def cons(self, o):
        """Add an item to the front of the collection."""
        raise AbstractMethodCall(self)

########NEW FILE########
__FILENAME__ = iterable
from clojure.lang.cljexceptions import AbstractMethodCall

class Iterable(object):
    def __iter__(self):
        raise AbstractMethodCall(self)

########NEW FILE########
__FILENAME__ = itransientassociative
from clojure.lang.cljexceptions import AbstractMethodCall
from clojure.lang.itransientcollection import ITransientCollection
from clojure.lang.ilookup import ILookup

class ITransientAssociative(ITransientCollection, ILookup):
    def assoc(self, key, val):
        raise AbstractMethodCall(self)

########NEW FILE########
__FILENAME__ = itransientcollection
from clojure.lang.cljexceptions import AbstractMethodCall

class ITransientCollection(object):
    def conj(self, val):
        raise AbstractMethodCall(self)

    def persistent(self):
        raise AbstractMethodCall(self)

########NEW FILE########
__FILENAME__ = itransientmap
from clojure.lang.cljexceptions import AbstractMethodCall
from clojure.lang.itransientassociative import ITransientAssociative
from clojure.lang.counted import Counted

class ITransientMap(ITransientAssociative, Counted):
    def assoc(self, key, value):
        raise AbstractMethodCall(self)

    def without(self, key):
        raise AbstractMethodCall(self)

    def persistent(self):
        raise AbstractMethodCall(self)

########NEW FILE########
__FILENAME__ = linenumberingtextreader
class PushbackTextReader():
    def __init__(self, reader):
        self.baseReader = reader
        self.unreadChar = 0
        self.hasUnread = False

########NEW FILE########
__FILENAME__ = lispreader
# -*- coding: utf-8 -*-

import fractions
import re
import string
import unicodedata

from clojure.lang.cljexceptions import ReaderException, IllegalStateException
from clojure.lang.cljkeyword import Keyword, TAG_KEY, T, LINE_KEY
from clojure.lang.fileseq import FileSeq, MutatableFileSeq, StringReader
from clojure.lang.globals import currentCompiler
from clojure.lang.ipersistentlist import IPersistentList
from clojure.lang.ipersistentvector import IPersistentVector
from clojure.lang.ipersistentmap import IPersistentMap
from clojure.lang.ipersistentset import IPersistentSet
from clojure.lang.ipersistentcollection import IPersistentCollection
from clojure.lang.iseq import ISeq
from clojure.lang.persistenthashmap import EMPTY as EMPTY_MAP
from clojure.lang.persistentvector import EMPTY as EMPTY_VECTOR
import clojure.lang.persistenthashset
from clojure.lang.persistenthashset import createWithCheck
import clojure.lang.rt as RT
from clojure.lang.symbol import Symbol
from clojure.lang.var import Var, threadBindings
import clojure.lang.namespace as namespace

_AMP_ = Symbol("&")
_FN_ = Symbol("fn")
_VAR_ = Symbol("var")
_APPLY_ = Symbol("apply")
_DEREF_ = Symbol("deref")
_HASHMAP_ = Symbol("clojure.core", "hashmap")
_CONCAT_ = Symbol("clojure.core", "concat")
_LIST_ = Symbol("clojure.core", "list")
_SEQ_ = Symbol("clojure.core", "seq")
_VECTOR_ = Symbol("clojure.core", "vector")
_QUOTE_ = Symbol("quote")
_SYNTAX_QUOTE_ = Symbol("`")
_UNQUOTE_ = Symbol("~")
_UNQUOTE_SPLICING_ = Symbol("~@")

ARG_ENV = Var(None).setDynamic()
GENSYM_ENV = Var(None).setDynamic()

symbolPat = re.compile("[:]?([\\D^/].*/)?([\\D^/][^/]*)")

intPat = re.compile(r"""
(?P<sign>[+-])?
  (:?
    # radix: 12rAA
    (?P<radix>(?P<base>[1-9]\d?)[rR](?P<value>[0-9a-zA-Z]+))    |
    # decima1: 0, 23, 234, 3453455
    (?P<decInt>0|[1-9]\d*)                                      |
    # octal: 0777
    0(?P<octInt>[0-7]+)                                         |
    # hex: 0xff
    0[xX](?P<hexInt>[0-9a-fA-F]+))
$                               # ensure the entire string matched
""", re.X)

# This floating point re has to be a bit more accurate than the original
# Clojure version because Clojure uses Double.parseDouble() to convert the
# string to a floating point value for return. If it can't convert it (for
# what ever reason), it throws.  Python float() is a lot more liberal. It's
# not a parser:
#
# >>> float("08") => 8.0
#
# I could just check for a decimal in matchNumber(), but is that the *only*
# case I need to check? I think it best to fully define a valid float in the
# re.
floatPat = re.compile(r"""
[+-]?
\d+
(\.\d*([eE][+-]?\d+)? |
 [eE][+-]?\d+)
$                               # ensure the entire string matched
""", re.X)

# Clojure allows what *should* be octal numbers as the numerator and
# denominator. But they are parsed as base 10 integers that allow leading
# zeros. In my opinion this isn't consistent behavior at all.
# The following re only allows base 10 integers.
ratioPat = re.compile("[-+]?(0|[1-9]\d*)/(0|[1-9]\d*)$")

# clojure-py constants
# for interpretToken()
INTERPRET_TOKENS = {"nil": None,
                    "true": True,
                    "false": False,
                    }

# for stringReader()
chrLiterals = {'t': '\t',
               'r': '\r',
               'n': '\n',
               'b': '\b',
               '\\': '\\',
               '"': '"',
               "f": '\f',
               }

# for regexReader()
# http://docs.python.org/reference/lexical_analysis.html
regexCharLiterals = {'\\': '\\',
                    "'": "\'",
                    '"': '"',
                    'a': '\a',
                    'b': '\b',
                    "f": '\f',
                    'n': '\n',
                    'r': '\r',
                    't': '\t',
                    'v': '\v',
                    }

# for characterReader()
namedChars = {"newline": "\n",
              "space": " ",
              "tab": "\t",
              "backspace": "\b",
              "formfeed": "\f",
              "return": "\r",
              }

whiteSpace = set(",\n\t\r\b\f ")
octalChars = set("01234567")
commentTerminators = set(['', '\n', '\r'])
# legal characters between the braces: "\N{...}" for readNamedUnicodeChar()
unicodeNameChars = set(string.letters + "- ")
hexChars = set("0123456789abcdefABCDEF")


def read1(rdr):
    rdr.next()
    if rdr is None:
        return ""
    return rdr.first()


def isMacro(c):
    return c in macros


def isTerminatingMacro(ch):
    return ch != "#" and ch != "\'" and isMacro(ch)


def readString(s):
    "Return the first object found in s"
    r = StringReader(s)
    return read(r, False, None, False)


def read(rdr, eofIsError, eofValue, isRecursive):
    """Read and return one object from rdr.

    rdr -- a read/unread-able object
    eofIsError -- if True, raise an exception when rdr is out of characters
                  if False, return eofValue instead
    eofValue --   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    isRecursive -- not currently used

    The basic sequence is as follows:
    1. consume white space
    2. check for eof
    3. check for a number (sans [+-])       <- Does this
    4. dispatch on macro characters         <- order matter?
    5. check for a number (with [+-])
    6. check for a symbol"""
    while True:
        ch = read1(rdr)

        while ch in whiteSpace:
            ch = read1(rdr)

        if ch == "":
            if eofIsError:
                raise ReaderException("EOF while reading", rdr)
            else:
                return eofValue

        if ch.isdigit():
            return readNumber(rdr, ch)

        m = getMacro(ch)
        if m is not None:
            ret = m(rdr, ch)
            if ret is rdr:
                continue
            return ret

        if ch in ["+", "-"]:
            ch2 = read1(rdr)
            if ch2.isdigit():
                rdr.back()
                n = readNumber(rdr, ch)
                return n
            rdr.back()

        token = readToken(rdr, ch)
        return interpretToken(token)


def unquoteReader(rdr, tilde):
    """Return one of:
    * (unquote-splicing next-object-read)
    * (unquote next-object-read)"""
    s = read1(rdr)
    if s == "":
        raise ReaderException("EOF reading unquote", rdr)
    if s == "@":
        o = read(rdr, True, None, True)
        return RT.list(_UNQUOTE_SPLICING_, o)
    else:
        rdr.back()
        o = read(rdr, True, None, True)
        return RT.list(_UNQUOTE_, o)


# replaces the overloaded readUnicodeChar()
# Not really cemented to the reader
def stringCodepointToUnicodeChar(token, offset, length, base):
    """Return a unicode character given a string that specifies a codepoint.

    token -- string to parse
    offset -- index into token where codepoint starts
    length -- maximum number of digits to read from offset
    base -- expected radix of the codepoint

    Return a unicode string of length one."""
    if len(token) != offset + length:
        raise UnicodeError("Invalid unicode character: \\{0}".format(token))
    try:
        return unichr(int(token[offset:], base))
    except:
        raise UnicodeError("Invalid unicode character: \\{0}".format(token))


def readUnicodeChar(rdr, initch, base, length, exact):
    """Read a string that specifies a Unicode codepoint.

    rdr -- read/unread-able object
    initch -- the first character of the codepoint string
    base -- expected radix of the codepoint
    length -- maximum number of characters in the codepoint
    exact -- if True, codepoint string must contain length characters
             if False, it must contain [1, length], inclusive

    May raise ReaderException. Return a unicode string of length one."""
    digits = []
    try:
        int(initch, base)
        digits.append(initch)
    except ValueError:
        raise ReaderException("Expected base {0} digit, got:"
                              " ({1})".format(base, initch or "EOF"), rdr)
    for i in range(2, length+1):
        ch = read1(rdr)
        if ch == "" or ch in whiteSpace or isMacro(ch):
            rdr.back()
            i -= 1
            break
        try:
            int(ch, base)
            digits.append(ch)
        except ValueError:
            if exact:
                raise ReaderException("Expected base {0} digit, got:"
                                      " ({1})".format(base, ch or "EOF"), rdr)
            else:
                rdr.back()
                break
    if i != length and exact:
        raise ReaderException("Invalid character length: ({0}), should be:"
                              " ({1})".format(i, length), rdr)
    return unichr(int("".join(digits), base))


def characterReader(rdr, backslash):
    """Read a single clojure-py formatted character from rdr.

    rdr -- read/unread-able object
    backslash -- ignored

    May raise ReaderException. Return a unicode string of lenght one."""
    ch = rdr.read()
    if ch == "":
        raise ReaderException("EOF while reading character", rdr)
    token = readToken(rdr, ch)  # .decode("utf-8")
    if len(token) == 1:
        return token
    elif token in namedChars:
        return namedChars[token]
    elif token.startswith("u"):
        try:
            ch = stringCodepointToUnicodeChar(token, 1, 4, 16)
        except UnicodeError as e:
            raise ReaderException(e.args[0], rdr)
        codepoint = ord(ch)
        if u"\ud800" <= ch <= u"\udfff":
            raise ReaderException("Invalid character constant in literal"
                                  " string: \\{0}".format(token), rdr)
        return ch
    elif token.startswith("o"):
        if len(token) > 4:
            raise ReaderException("Invalid octal escape sequence length in"
                                  " literal string. Three digits max:"
                                  " \\{0}".format(token), rdr)
        try:
            ch = stringCodepointToUnicodeChar(token, 1, len(token) - 1, 8)
        except UnicodeError as e:
            raise ReaderException(e.args[0], rdr)
        codepoint = ord(ch)
        if codepoint > 255:
            raise ReaderException("Octal escape sequence in literal string"
                                  " must be in range [0, 377], got:"
                                  " (\\o{0})".format(codepoint), rdr)
        return ch
    raise ReaderException("Unsupported character: \\" + token, rdr)


def stringReader(rdr, doublequote):
    """Read a double-quoted "foo" literal string from rdr.

    rdr -- a read/unread-able object
    doublequote -- ignored

    May raise ReaderException. Return a str or unicode object."""
    buf = []
    ch = read1(rdr)
    while True:
        if ch == "":
            raise ReaderException("EOF while reading string")
        if ch == '\\':
            ch = read1(rdr)
            if ch == "":
                raise ReaderException("EOF while reading string")
            elif ch in chrLiterals:
                ch = chrLiterals[ch]
            elif ch == "u":
                ch = read1(rdr)
                if not ch in hexChars:
                    raise ReaderException("Hexidecimal digit expected after"
                                          " \\u in literal string, got:"
                                          " ({0})".format(ch), rdr)
                ch = readUnicodeChar(rdr, ch, 16, 4, True)
            elif ch in octalChars:
                ch = readUnicodeChar(rdr, ch, 8, 3, False)
                if ord(ch) > 255:
                    raise ReaderException("Octal escape sequence in literal"
                                          " string must be in range [0, 377]"
                                          ", got: ({0})".format(ord(ch)),
                                          rdr)
            else:
                raise ReaderException("Unsupported escape character in"
                                      " literal string: \\{0}".format(ch), rdr)
        elif ch == '"':
            return "".join(buf)
        buf += ch
        ch = read1(rdr)


def readToken(rdr, initch):
    """Read and return the next valid token from rdr.

    rdr -- read/unread-able object
    initch -- first character of returned token

    Collect characters until the eof is reached, white space is read, or a
    terminating macro character is read."""
    sb = [initch]
    while True:
        ch = read1(rdr)
        if ch == "" or ch in whiteSpace or isTerminatingMacro(ch):
            rdr.back()
            break
        sb.append(ch)
    s = "".join(sb)
    return s


def interpretToken(s):
    """Return the value defined by the string s.

    This function exists as a pre-filter to matchSymbol(). If is is found in
    lispreader.INTERPRET_TOKENS, return that, else see if s is a valid Symbol
    and return that.

    Raise ReaderException if s is not a valid token."""
    if s in INTERPRET_TOKENS:
        return INTERPRET_TOKENS[s]
    ret = matchSymbol(s)
    if ret is None:
        raise ReaderException("Unknown symbol {0}".format(s))
    return ret


def readNumber(rdr, initch):
    """Return the next number read from rdr.

    rdr -- a read/unread-able object
    initch -- the first character of the number

    May raise ReaderException."""
    sb = [initch]
    while True:
        ch = read1(rdr)
        if ch == "" or ch in whiteSpace or isMacro(ch):
            rdr.back()
            break
        sb.append(ch)

    s = "".join(sb)
    try:
        n = matchNumber(s)
    except Exception as e:
        raise ReaderException(e.args[0], rdr)
    if n is None:
        raise ReaderException("Invalid number: " + s, rdr)
    return n


def matchNumber(s):
    """Find if the string s is a valid literal number.

    Return the numeric value of s if so, else return None."""
    mo = intPat.match(s)
    if mo:
        mogd = mo.groupdict()
        sign = mogd["sign"] or "+"
        # 12rAA
        if mogd["radix"]:
            return int(sign + mogd["value"], int(mogd["base"], 10))
        # 232
        elif mogd["decInt"]:
            return int(sign + mogd["decInt"])
        # 0777
        elif mogd["octInt"]:
            return int(sign + mogd["octInt"], 8)
        # 0xdeadbeef
        elif mogd["hexInt"]:
            return int(sign + mogd["hexInt"], 16)
    # 1e3, 0.3,
    mo = floatPat.match(s)
    if mo:
        return float(mo.group())
    # 1/2
    mo = ratioPat.match(s)
    if mo:
        return fractions.Fraction(mo.group())
    # no match
    return None


def getMacro(ch):
    """Return the function associated with the macro character ch"""
    return macros.get(ch)       # None if key not present


def commentReader(rdr, semicolon):
    """Read and discard characters until a newline or eof is reached.

    rdr -- read/unread-able object
    semicolon -- ignored

    Return rdr"""
    while True:
        ch = read1(rdr)
        if ch in commentTerminators:
            break
    return rdr


def discardReader(rdr, underscore):
    """Read and discard the next object from rdr.

    rdr -- read/unread-able object
    underscore -- ignored

    Return rdr."""
    read(rdr, True, None, True)
    return rdr


class wrappingReader(object):
    """Defines a callable object that reads the next object and returns:
    (sym next-object-read)
    Where sym is Symbol instance passed to __init__."""
    def __init__(self, sym):
        self.sym = sym

    def __call__(self, rdr, quote):
        o = read(rdr, True, None, True)
        return RT.list(self.sym, o)


def dispatchReader(rdr, hash):
    """Read and return the next object defined by the next dispatch character.

    rdr -- read/unread-able object
    hash -- ignored

    Read a character from rdr. Call its associated function in
    dispatchMacros. Return that value. May raise ReaderException."""
    ch = read1(rdr)
    if ch == "":
        raise ReaderException("EOF while reading character", rdr)
    if ch not in dispatchMacros:
        raise ReaderException("No dispatch macro for: ("+ ch + ")", rdr)
    return dispatchMacros[ch](rdr, ch)


def listReader(rdr, leftparen):
    """Read and return a possibly empty list () from rdr.

    rdr -- a read/unread-able object
    leftparen -- ignored"""
    startline = rdr.lineCol()[0]
    lst = readDelimitedList(')', rdr, True)
    lst = apply(RT.list, lst)
    return lst.withMeta(RT.map(LINE_KEY, startline))


def vectorReader(rdr, leftbracket):
    """Read and return a possibly empty vector [] from rdr.

    rdr -- a read/unread-able object
    leftbracket -- ignored"""
    startline = rdr.lineCol()[0]
    lst = readDelimitedList(']', rdr, True)
    lst = apply(RT.vector, lst)
    return lst

def mapReader(rdr, leftbrace):
    """Read and return a possibly empty map {} from rdr.

    rdr -- a read/unread-able object
    leftbrace -- ignored"""
    startline = rdr.lineCol()[0]
    lst = readDelimitedList('}', rdr, True)
    lst = apply(RT.map, lst)
    return lst


def setReader(rdr, leftbrace):
    """Read and return a possibly empty set #{} from rdr.

    rdr -- a read/unread-able object
    leftbrace -- ignored"""
    s = readDelimitedList("}", rdr, True)
    return createWithCheck(s)


def unmatchedClosingDelimiterReader(rdr, un):
    """Raise ReaderException.

    rdr -- read/unread-able object (used for exception message)
    un -- the stray delimiter

    This will be called if un has no matching opening delimiter in rdr."""
    raise ReaderException(
        "Unmatched Delimiter {0} at {1}".format(un, rdr.lineCol()))


def readDelimitedList(delim, rdr, isRecursive):
    """Read and collect objects until an unmatched delim is reached.

    delim -- the terminating delimiter
    rdr -- read/unread-able object
    isRecursive -- ignored

    May raise ReaderException. Return a Python list of those objects."""
    firstline = rdr.lineCol()[0]
    a = []

    while True:
        ch = read1(rdr)
        while ch in whiteSpace:
            ch = read1(rdr)
        if ch == "":
            raise ReaderException(
                "EOF while reading starting at line {0}".format(firstline))

        if ch == delim:
            break

        macrofn = getMacro(ch)
        if macrofn is not None:
            mret = macrofn(rdr, ch)
            if mret is not None and mret is not rdr:
                a.append(mret)
        else:
            rdr.back()
            o = read(rdr, True, None, isRecursive)
            a.append(o)

    return a


# This is the unicode name db Python uses:
# ftp://ftp.unicode.org/Public/5.2.0/ucd/UnicodeData.txt
def readNamedUnicodeChar(rdr):
    """Read \N{foo} syntax, starting at the {.

    rdr -- a read/unread-able object

    May raise ReaderException. Return the unicode character named by foo."""
    buf = []
    ch = read1(rdr)
    if ch != "{":
        raise ReaderException("Expected { in named unicode escape sequence,"
                              " got: ({0})".format(ch or "EOF"), rdr)
    while True:
        ch = read1(rdr)
        if ch == "":
            raise ReaderException("EOF while reading named unicode escape"
                                  " sequence", rdr)
        elif ch in unicodeNameChars:
            buf.append(ch)
            continue
        elif ch == '"':
            raise ReaderException("Missing } while reading named unicode"
                                  " escape sequence", rdr)
        elif ch == '}':
            break
        else:
            raise ReaderException("Illegal character in named unicode"
                                  " escape sequence: ({0})".format(ch), rdr)
    name = "".join(buf).strip()
    if len(name) == 0:
        raise ReaderException("Expected name between {} in named unicode "
                              "escape sequence", rdr)
    try:
        return unicodedata.lookup(name)
    except KeyError:
        raise ReaderException("Unknown unicode character name in escape"
                              " sequence: ({0})".format(name), rdr)


def rawRegexReader(rdr, r):
    r"""Read a regex pattern string ignoring most escape sequences.

    rdr -- a read/unread-able object
    r -- ignored

    The following two are the only valid escape sequences. But only if they
    are not preceded by an even number of backslashes. When \ are in pairs
    they've lost their abilty to escape the next character. Both backslashes
    *still* get put into the string.

      * \uXXXX
        \u03bb => λ
        \\u03bb => \ \ u 0 3 b b
        \\\u03bb => \ \ λ
      * \UXXXXXXXX
        same as above

    Everything else will result in two characters in the string:
    \n => \ n
    \r => \ r
    \t => \ t
    \" => \ "
    \xff => \ x f f
    \377 => \ 3 7 7
    \N{foo} \ N { f o o }

    May raise ReaderException. Return a Unicode string.
    """
    nSlashes = 0
    pat = []
    ch = read1(rdr)
    if ch == "":
        raise ReaderException("EOF expecting regex pattern", rdr)
    if ch != '"':
        raise ReaderException("Expected regex pattern after #r", rdr)
    ch = read1(rdr)
    while ch != '"':
        if ch == "":
            raise ReaderException("EOF while reading regex pattern", rdr)
        if ch == "\\":
            nSlashes += 1
            ch = read1(rdr)
            if ch == "":
                raise ReaderException("EOF while reading regex pattern", rdr)
            # \uXXXX
            elif ch == "u" and nSlashes % 2 != 0:
                ch = read1(rdr)
                if not ch in hexChars:
                    raise ReaderException("Hexidecimal digit expected"
                                          " after \\u in regex pattern,"
                                          " got: ({0})".format(ch or "EOF"),
                                          rdr)
                pat.append(readUnicodeChar(rdr, ch, 16, 4, True))
                nSlashes = 0
            # \uXXXXXXXX
            elif ch == "U" and nSlashes % 2 != 0:
                ch = read1(rdr)
                if not ch in hexChars:
                    raise ReaderException("Hexidecimal digit expected"
                                          " after \\U in regex pattern,"
                                          " got: ({0})".format(ch or "EOF"),
                                          rdr)
                pat.append(readUnicodeChar(rdr, ch, 16, 8, True))
                nSlashes = 0
            else:
                if ch == "\\":
                    nSlashes += 1
                pat.append("\\")
                pat.append(ch)
        else:
            pat.append(ch)
        ch = read1(rdr)
    try:
        return re.compile(u"".join(pat))
    except re.error as e:
        raise ReaderException("invalid regex pattern: {0}".format(e.args[0]),
                              rdr)


def regexReader(rdr, doublequote):
    """Read a possibly multi-line Python re pattern string.

    rdr -- read/unread-able object
    doubleQuote -- ignored
    raw -- if True, the string is to be treated as a Python r"string".

    May raise ReaderException. Return a Unicode string"""
    pat = []
    ch = read1(rdr)
    while ch != '"':
        if ch == "":
            raise ReaderException("EOF while reading regex pattern", rdr)
        if ch == "\\":
            ch = read1(rdr)
            if ch == "":
                raise ReaderException("EOF while reading regex pattern", rdr)
            # \, ', ", a, b, f, n, r, t, v
            elif ch in regexCharLiterals:
                ch = regexCharLiterals[ch]
            # \uXXXX
            elif ch == "u":
                ch = read1(rdr)
                if not ch in hexChars:
                    raise ReaderException("Hexidecimal digit expected after"
                                          " \\u in regex pattern, got:"
                                          " ({0})".format(ch or "EOF"), rdr)
                ch = readUnicodeChar(rdr, ch, 16, 4, True)
            # \uXXXXXXXX
            elif ch == "U":
                ch = read1(rdr)
                if not ch in hexChars:
                    raise ReaderException("Hexidecimal digit expected after"
                                          " \\U in regex pattern, got:"
                                          " ({0})".format(ch or "EOF"), rdr)
                ch = readUnicodeChar(rdr, ch, 16, 8, True)
            # \xXX
            elif ch == "x":
                ch = read1(rdr)
                if not ch in hexChars:
                    raise ReaderException("Hexidecimal digit expected after"
                                          " \\x in regex pattern, got:"
                                          " ({0})".format(ch or "EOF"), rdr)
                ch = readUnicodeChar(rdr, ch, 16, 2, True)
            #\O, \OO, or \OOO
            elif ch.isdigit():
                ch = readUnicodeChar(rdr, ch, 8, 3, False) # <= False
            #\N{named unicode character}
            elif ch == "N":
                ch = readNamedUnicodeChar(rdr)
            # Didnt recognize any escape sequence but ch got
            # reset to the char after \\ so...
            else:
                pat.append("\\")
        pat.append(ch)
        ch = read1(rdr)
    try:
        return re.compile(u"".join(pat))
    except re.error as e:
        raise ReaderException("invalid regex pattern: {0}".format(e.args[0]),
                              rdr)


def metaReader(rdr, caret):
    """Read two objects from rdr. Return second with first as meta data.

    rdr -- read/unread-able object
    caret -- ignored

    May raise ReaderException."""
    line = rdr.lineCol()[0]
    meta = read(rdr, True, None, True)
    if isinstance(meta, (str, Symbol)):
        meta = RT.map(TAG_KEY, meta)
    elif isinstance(meta, Keyword):
        meta = RT.map(meta, T)
    elif not isinstance(meta, IPersistentMap):
        raise ReaderException("Metadata must be Symbol,Keyword,String or Map",
                              rdr)
    o = read(rdr, True, None, True)
    if not hasattr(o, "withMeta"):
        # can't attach rdr to the exception here as it would point
        # to the *end* of the object just read'
        raise ReaderException("Cannot attach meta to a object without"
                              " .withMeta")
    return o.withMeta(meta)

def currentNSName():
    comp = currentCompiler.deref()
    if comp is None:
        raise IllegalStateException("No Compiler found in syntax quote!")
    ns = comp.getNS()
    if ns is None:
        raise IllegalStateException("No ns in reader")
    return ns.__name__

def matchSymbol(s):
    """Return a symbol or keyword.

    Return None if the string s does not define a legal symbol or keyword."""
    m = symbolPat.match(s)
    if m is not None:
        ns = m.group(1)
        name = m.group(2)

        if name.endswith(".") and not name.startswith("."):
            name = name[:-1]
        if ns is not None and (ns.endswith(":/") or name.endswith(":")\
            or s.find("::") != -1):
                return None
        ns = ns if ns is None else ns[:-1]
        
        if s.startswith("::"):
            return Keyword(currentNSName(), s[2:])


        iskeyword = s.startswith(':')
        if iskeyword:
            return Keyword(s[1:])
        else:
            return Symbol(ns, name)
    return None


def argReader(rdr, perc):
    """Read and intern an anonymous function argument (%, %1, %&, etc.).

    rdr -- read/unread-able object
    prec -- ignored

    May raise IllegalStateException, or ReaderException.
    """
    if ARG_ENV.deref() is None:
        return interpretToken(readToken(rdr, '%'))
    ch = read1(rdr)
    rdr.back()
    if ch == "" or ch in whiteSpace or isTerminatingMacro(ch):
        return registerArg(1)
    n = read(rdr, True, None, True)
    if isinstance(n, Symbol) and n == _AMP_:
        return registerArg(-1)
    if not isinstance(n, int):
        raise ReaderException("arg literal must be %, %& or %integer", rdr)
    return registerArg(n)


def varQuoteReader(rdr, singlequote):
    """Return the list (var next-object-read)

    rdr -- read/unread-able object
    singlequote -- ignored"""
    line = rdr.lineCol()[0]
    form = read(rdr, True, None, True)
    return RT.list(_VAR_, form).withMeta(RT.map(LINE_KEY, line))


def registerArg(arg):
    argsyms = ARG_ENV.deref()
    if argsyms is None:
        raise IllegalStateException("arg literal not in #()")
    ret = argsyms[arg]
    if ret is None:
        ret = garg(arg)
        ARG_ENV.set(argsyms.assoc(arg, ret))
    return ret


def fnReader(rdr, lparen):
    """Read an anonymous function #() from reader

    rdr -- a read/unread-able object
    lparen -- ignored

    Return an IPersistentList"""
    if ARG_ENV.deref() is not None:
        raise IllegalStateException("Nested #()s are not allowed")
    with threadBindings(RT.map(ARG_ENV, EMPTY_MAP)):
        rdr.back()
        form = read(rdr, True, None, True)
        drefed = ARG_ENV.deref()
        sargs = sorted(list(filter(lambda x: x != -1, drefed)))
        args = []
        if len(sargs):
            for x in range(1, int(str(sargs[-1])) + 1):
                if x in drefed:
                    args.append(drefed[x])
                else:
                    args.append(garg(x))
            retsym = drefed[-1]
            if retsym is not None:
                args.append(_AMP_)
                args.append(retsym)
        vargs = RT.vector(*args)
    return RT.list(_FN_, vargs, form)


def isUnquote(form):
    """Return True if form is (unquote ...)"""
    return isinstance(form, ISeq) and form.first() == _UNQUOTE_


def isUnquoteSplicing(form):
    """Return True if form is (unquote-splicing ...)"""
    return isinstance(form, ISeq) and form.first() == _UNQUOTE_SPLICING_


class SyntaxQuoteReader(object):
    def __call__(self, r, backquote):
        with threadBindings(RT.map(GENSYM_ENV, EMPTY_MAP)):
            self.rdr = r
            form = read(r, True, None, True)
            return self.syntaxQuote(form)

    def syntaxQuote(self, form):
        # compiler uses this module, so import it lazily
        from clojure.lang.compiler import builtins as compilerbuiltins

        if form in compilerbuiltins:
            ret = RT.list(_QUOTE_, form)
        elif isinstance(form, Symbol):
            sym = form
            if sym.ns is None and sym.name.endswith("#"):
                gmap = GENSYM_ENV.deref()
                if gmap == None:
                    raise ReaderException("Gensym literal not in syntax-quote, before", self.rdr)
                gs = gmap[sym]
                if gs is None:
                    gs = Symbol(None, "{0}__{1}__auto__".format(sym.name[:-1], RT.nextID()))
                    GENSYM_ENV.set(gmap.assoc(sym, gs))
                sym = gs
            elif sym.ns is None and sym.name.endswith("."):
                ret = sym
            elif sym.ns is None and sym.name.startswith("."):
                ret = sym
            elif sym.ns is not None:
                ret = sym

            else:
                comp = currentCompiler.deref()
                if comp is None:
                    raise IllegalStateException("No Compiler found in syntax quote!")
                ns = comp.getNS()
                if ns is None:
                    raise IllegalStateException("No ns in reader")
                
                item = namespace.findItem(ns, sym)
                if item is None:
                    sym = Symbol(ns.__name__, sym.name)
                else:
                    sym = Symbol(item.ns.__name__, sym.name)
            ret = RT.list(_QUOTE_, sym)
        else:
            if isUnquote(form):
                return form.next().first()
            elif isUnquoteSplicing(form):
                raise IllegalStateException("splice not in list")
            elif isinstance(form, IPersistentCollection):
                if isinstance(form, IPersistentMap):
                    keyvals = self.flattenMap(form)
                    ret = RT.list(_APPLY_, _HASHMAP_, RT.list(RT.cons(_CONCAT_, self.sqExpandList(keyvals.seq()))))
                elif isinstance(form, (IPersistentVector, IPersistentSet)):
                    ret = RT.list(_APPLY_, _VECTOR_, RT.list(_SEQ_, RT.cons(_CONCAT_, self.sqExpandList(form.seq()))))
                elif isinstance(form, (ISeq, IPersistentList)):
                    seq = form.seq()
                    if seq is None:
                        ret = RT.cons(_LIST_, None)
                    else:
                        ret = RT.list(_SEQ_, RT.cons(_CONCAT_, self.sqExpandList(seq)))
                else:
                    raise IllegalStateException("Unknown collection type")
            elif isinstance(form, (int, float, str, Keyword)):
                ret = form
            else:
                ret = RT.list(_QUOTE_, form)
        if getattr(form, "meta", lambda: None)() is not None:
            newMeta = form.meta().without(LINE_KEY)
            if len(newMeta) > 0:
                return RT.list(_WITH_META_, ret, self.syntaxQuote(form.meta()))#FIXME: _WITH_META_ undefined
        return ret

    def sqExpandList(self, seq):
        ret = EMPTY_VECTOR
        while seq is not None:
            item = seq.first()
            if isUnquote(item):
                ret = ret.cons(RT.list(_LIST_, item.next().first()))
            elif isUnquoteSplicing(item):
                ret = ret.cons(item.next().first())
            else:
                ret = ret.cons(RT.list(_LIST_, self.syntaxQuote(item)))
            seq = seq.next()
        return ret.seq()

    def flattenMap(self, m):
        keyvals = EMPTY_VECTOR
        s = m.seq()
        while s is not None:
            e = s.first()
            keyvals = keyvals.cons(e.getKey())
            keyvals = keyvals.cons(e.getValue())
            s = s.next()
        return keyvals


def garg(n):
    return Symbol("rest" if n == -1 else "p{0}__{1}#".format(n, RT.nextID()))


def derefNotImplemented(rdr, _):
    """Unconditionally raise ReaderException.

    The deref syntax @foo is not currently implemented. @foo will pass through
    silently as a symbol unless it's caught here, as it should be."""
    raise ReaderException("Deref syntax @foo not currently implemented.",
                          rdr)


def evalReaderNotImplemented(rdr, _):
    """Unconditionally raise ReaderException.

    The eval syntax #= not currently implemented and should be caught by the
    #reader. This message is more informative than the `no dispatch macro'
    message."""
    raise ReaderException("Eval syntax #= not currently implemented.",
                          rdr)


macros = {'\"': stringReader,
          "\'": wrappingReader(_QUOTE_),
          "(": listReader,
          ")": unmatchedClosingDelimiterReader,
          "[": vectorReader,
          "]": unmatchedClosingDelimiterReader,
          "{": mapReader,
          "}": unmatchedClosingDelimiterReader,
          ";": commentReader,
          "#": dispatchReader,
          "^": metaReader,
          "%": argReader,
          "`": SyntaxQuoteReader(),
          "~": unquoteReader,
          "\\": characterReader,
          "@": wrappingReader(_DEREF_)
          }

dispatchMacros = {"\"": regexReader,
                  "{": setReader,
                  "!": commentReader,
                  "_": discardReader,
                  "(": fnReader,
                  "'": varQuoteReader,
                  "^": metaReader,
                  # Use Python raw string syntax as #r"foo"
                  "r": rawRegexReader,
                  "=": evalReaderNotImplemented, # temporary?
                  }

########NEW FILE########
__FILENAME__ = lockingtransaction
from cljexceptions import IllegalStateException, TransactionRetryException
from clojure.lang.util import TVal
import clojure.lang.rt as RT
from clojure.util.shared_lock import shared_lock, unique_lock

from itertools import count
from threadutil import AtomicInteger
from threading import local as thread_local
from threading import Lock, Event, current_thread
from time import time

# How many times to retry a transaction before giving up
RETRY_LIMIT = 10000
# How long to wait to acquire a read or write lock for a ref
LOCK_WAIT_SECS = 0.1 #(100 ms)
# How long a transaction must be alive for before it is considered old enough to survive barging
BARGE_WAIT_SECS = 0.1 #(10 * 1000000ns)

spew_debug = False

# Possible status values
class TransactionState:
    Running, Committing, Retry, Killed, Committed = range(5)

loglock = Lock()
def log(msg):
    """
    Thread-safe logging, can't get logging module to spit out debug output
    when run w/ nosetests :-/
    """
    if spew_debug:
        with loglock:
            print("Thread: %s (%s): %s" % (current_thread().ident, id(current_thread()), msg))

class Info:
    def __init__(self, status, startPoint):
        self.status = AtomicInteger(status)
        self.startPoint = startPoint

        self.lock = Lock()

        # Faking java's CountdownLatch w/ a simple event---it's only from 1
        self.latch = Event()

    def running(self):
        status = self.status.get()
        return status in (TransactionState.Running, TransactionState.Committing)

class LockingTransaction():
    _transactions = thread_local()
    # Global ordering on all transactions---provides a mechanism for determing relativity of transactions
    #  to each other
    # Start the count at 1 since refs history starts at 0, and a ref created before the first transaction
    #  should be considered "before", and 0 < 0 is false.
    transactionCounter = count(1)

    def _resetData(self):
        self._info       = None
        self._startPoint = -1 # time since epoch (time.time())
        self._vals       = {}
        self._sets       = []
        self._commutes   = {}
        self._ensures    = []
        self._actions    = [] # Deferred agent actions

    def __init__(self):
        self._readPoint = -1 # global ordering on transactions (int)
        self._resetData()

    def _retry(self, debug_msg):
        """
        Raises a retry exception, with additional message for debugging
        """
        log(debug_msg)
        raise TransactionRetryException

    def _updateReadPoint(self, set_start_point):
        """
        Update the read point of this transaction to the next transaction counter id"""
        self._readPoint = self.transactionCounter.next()
        if set_start_point:
            self._startPoint = self._readPoint
            self._startTime = time()


    @classmethod
    def _getCommitPoint(cls):
        """
        Gets the next transaction counter id, but simply returns it for use instead of
        updating any internal fields.
        """
        return cls.transactionCounter.next()

    def _stop_transaction(self, status):
        """
        Stops this transaction, setting the final state to the desired state. Will decrement
        the countdown latch to notify other running transactions that this one has terminated
        """
        if self._info:
            with self._info.lock:
                self._info.status.set(status)
                self._info.latch.set()
            self._resetData()

    def _tryWriteLock(self, ref):
        """
        Attempts to get a write lock for the desired ref, but only waiting for LOCK_WAIT_SECS
        If acquiring the lock is not possible, throws a retry exception to force a retry for the
        current transaction
        """
        if not ref._lock.acquire(LOCK_WAIT_SECS):
            self._retry("RETRY - Failed to acquire write lock in _tryWriteLock. Owned by %s" % ref._tinfo.thread_id if ref._tinfo else None)

    def _releaseIfEnsured(self, ref):
        """
        Release the given ref from the set of ensured refs, if this ref is ensured
        """
        if ref in self._ensures:
            self._ensures.remove(ref)
            ref._lock.release_shared()

    def _barge(self, other_refinfo):
        """
        Attempts to barge another running transaction, described by that transactions's Info
        object.

        Barging is successful iff:

        1) This transaction is at least BARGE_WAIT_SECS old
        2) This transaction is older than the other transasction
        3) The other transaction is Running and an compareAndSet operation to Killed
            must be successful

        Returns if this barge was successful or not
        """
        # log("Trying to barge: %s %s < %s" % (time() - self._startPoint, self._startPoint, other_refinfo.startPoint))
        if(time() - self._startPoint > BARGE_WAIT_SECS and
            self._startPoint < other_refinfo.startPoint):
            if other_refinfo.status.compareAndSet(TransactionState.Running, TransactionState.Killed):
                # We barged them successfully, set their "latch" to 0 by setting it to true
                # log("BARGED THEM!")
                other_refinfo.latch.set()
                return True

        return False

    def _blockAndBail(self, other_refinfo):
        """
        This is a time-delayed retry of the current transaction. If we know there was a conflict on a ref
        with other_refinfo's transaction, we give it LOCK_WAIT_SECS to complete before retrying ourselves,
        to reduce contention and re-conflicting with the same transaction in the future.
        """
        self._stop_transaction(TransactionState.Retry)
        other_refinfo.latch.wait(LOCK_WAIT_SECS)

        self._retry("RETRY - Blocked and now bailing")

    def _takeOwnership(self, ref):
        """
        This associates the given ref with this transaction. It is called when a transaction modifies
        a reference in doSet(). It does the following:

        0) Releases any read locks (ensures) on the ref, as a alter/set after an ensure
            undoes the ensure operation
        1) Marks the reference as having been modified in this transaction
        2) Checks if the ref has a newer committed value than the transaction-try start point, and retries this
            transaction if so
        3) Checks if the ref is currently owned by another transaction (has a in-transaction-value in another transaction)
            If so, attempts to barge the other transaction. If it fails, forces a retry
        4) Otherwise, it associates the ref with this transaction by setting the ref's _info to this Info
        5) Returns the most recently committed value for this ref


        This method is called 'lock' in the Clojure/Java implementation
        """
        self._releaseIfEnsured(ref)

        # We might get a retry exception, unlock lock if we have locked it
        unlocked = True
        try:
            self._tryWriteLock(ref)
            unlocked = False

            if ref._tvals and ref._tvals.point > self._readPoint:
                # Newer committed value than when we started our transaction try
                self._retry("RETRY - Newer committed value when taking ownership")

            refinfo = ref._tinfo
            if refinfo and refinfo != self._info and refinfo.running():
                # This ref has an in-transaction-value in some *other* transaction
                if not self._barge(refinfo):
                    # We lost the barge attempt, so we retry
                    ref._lock.release()
                    unlocked = True
                    # log("BARGE FAILED other: %s (%s != %s ? %s (running? %s))" %
                            # (refinfo.thread_id, refinfo, self._info, refinfo != self._info, refinfo.running()))
                    return self._blockAndBail(refinfo)
            # We own this ref
            ref._tinfo = self._info
            return ref._tvals.val if ref._tvals else None
        finally:
            # If we locked the mutex but need to retry, unlock it on our way out
            if not unlocked:
                ref._lock.release()

    def getRef(self, ref):
        """
        Returns a value for the desired ref in this transaction. Ensures that a transaction is running, and
        returns *either* the latest in-transaction-value for this ref (is there is one), or the latest committed
        value that was committed before the start of this transaction.

        If there is no committed value for this ref before this transaction began, it records a fault for the ref,
        and triggers a retry
        """
        if not self._info or not self._info.running():
            self._retry("RETRY - Not running in getRef")

        # Return in-transaction-value if we have one
        if ref in self._vals:
            return self._vals[ref]

        # Might raise a retry exception
        with unique_lock(ref._lock):
            if not ref._tvals:
                raise IllegalStateException("Ref in transaction doRef is unbound! ", ref)

            historypoint = ref._tvals
            while True:
                # log("Checking: %s < %s" % (historypoint.point, self._readPoint))
                if historypoint.point < self._readPoint:
                    return historypoint.val

                # Get older history value, if we loop around to the front we're done
                historypoint = historypoint.prev
                if historypoint == ref._tvals:
                    break

        # Could not find an old-enough committed value, fault!
        ref._faults.getAndIncrement()
        self._retry("RETRY - Fault, no new-enough value!")

    def doSet(self, ref, val):
        """
        Sets the in-transaction-value of the desired ref to the given value
        """
        if not self._info or not self._info.running():
            self._retry("RETRY - Not running in doSet!")

        # Can't alter after a commute
        if ref in self._commutes:
            raise IllegalStateException("Can't set/alter a ref in a transaction after a commute!")

        if not ref in self._sets:
            self._sets.append(ref)
            self._takeOwnership(ref)

        self._vals[ref] = val
        return val

    def doCommute(self, ref, fn, args):
        """
        Sets the in-transaction-value of this ref to the given value, but does not require
        other transactions that also change this ref to retry. Commutes are re-computed at
        commit time and apply on top of any more recent changes.
        """
        if not self._info or not self._info.running():
            self._retry("RETRY - Not running in doCommute!")

        # If we don't have an in-transaction-value yet for this ref
        #  get the latest one
        if not ref in self._vals:
            with shared_lock(ref._lock):
                val = ref._tvals.val if ref._tvals else None

            self._vals[ref] = val

        # Add this commute function to the end of the list of commutes for this ref
        self._commutes.setdefault(ref, []).append([fn, args])
        # Save the value we get by applying the fn now to our in-transaction-list
        returnValue = fn(*RT.cons(self._vals[ref], args))
        self._vals[ref] = returnValue

        return returnValue

    def doEnsure(self, ref):
        """
        Ensuring a ref means that no other transactions can change this ref until this transaction is finished.
        """
        if not self._info or not self._info.running():
            self._retry("RETRY - Not running in doEnsure!")

        # If this ref is already ensured, no more work to do
        if ref in self._ensures:
            return

        # Ensures means we have a read lock (so no one else can write)
        ref._lock.acquire_shared()

        if ref._tvals and ref._tvals.point > self._readPoint:
            # Ref was committed since we started our transaction (since we got our world snapshot)
            # We bail out and retry since we've already 'lost' the ensuring
            ref._lock.release_shared()
            self._retry("RETRY - Ref already committed to in doEnsure")

        refinfo = ref._tinfo

        if refinfo and refinfo.running():
            # Someone's writing to it (has called _takeOwnership)
            # Let go of our reader lock, ensure means some transaction's already owned it
            ref.lock.release_shared()
            if refinfo != self._info:
                # Not our ref, ensure fails!
                self._blockAndBail(refinfo)
        else:
            self._ensures.append(ref)

    def run(self, fn):
        """Main STM entry point---run the desired 0-args function in a
        transaction, capturing all modifications that happen,
        atomically applying them during the commit step."""

        tx_committed = False

        for i in xrange(RETRY_LIMIT):
            if tx_committed: break

            self._updateReadPoint(i == 0)

            locks, notifications = [], []
            try:
                self._start_transaction()
                returnValue = fn()
                if self.attempt_commit(locks, notifications):
                    tx_committed = True

            except TransactionRetryException:
                pass # Retry after cleanup.
            finally:
                self.release_locks(locks)
                self.release_ensures()
                self._stop_transaction(TransactionState.Committed if tx_committed else TransactionState.Retry)
                self.send_notifications(tx_committed, notifications)

        if tx_committed:
            return returnValue
        else:
            raise CljException("Transaction failed after reaching retry limit :'(")

    def _start_transaction(self):
        # Set the info for this transaction try. We are now Running!
        # if self._info:
        #     log("Setting new INFO, but old: %s %s is running? %s" % (self._info, self._info.thread_id, self._info.running()))
        self._info = Info(TransactionState.Running, self._startPoint)
        self._info.thread_id = "%s (%s)" % (current_thread().ident, id(current_thread()))
        # log("new INFO: %s %s running? %s" % (self._info, self._info.thread_id, self._info.running()))

    def attempt_commit(self, locks, notifications):
        # This will either raise an exception or return True
        if self._info.status.compareAndSet(TransactionState.Running, TransactionState.Committing):
            self.handle_commutes(locks)
            self.acquire_write_locks(self._sets, locks)
            self.validate_changes(self._vals)
            notifications = self.commit_ref_sets()
            self._info.status.set(TransactionState.Committed)
            return True
        return False

    def handle_commutes(self, locks):
        for ref, funcpairs in self._commutes.items():
            # If this ref has been ref-set or alter'ed before the commute, no need to re-apply
            # since we can be sure that the commute happened on the latest value of the ref
            if ref in self._sets: continue

            wasEnsured = ref in self._ensures
            self._releaseIfEnsured(ref)

            # Try to get a write lock---if some other transaction is
            # committing to this ref right now, retry this transaction
            self._tryWriteLock(ref)
            locks.append(ref)
            if wasEnsured and ref._tvals and ref._tvals.point > self._readPoint:
                self._retry("RETRY - was ensured and has newer version while commiting")

            other_refinfo = ref._tinfo
            if other_refinfo and other_refinfo != self._info and other_refinfo.running():
                # Other transaction is currently running, and owns
                # this ref---meaning it set the ref's
                # in-transaction-value already, so we either barge
                # them or retry
                if not self._barge(other_refinfo):
                    self._retry("RETRY - conflicting commutes being commited and barge failed")

            # Ok, no conflicting ref-set or alters to this ref, we can
            # make the change Update the val with the latest
            # in-transaction-version
            val = ref._tvals.val if ref._tvals else None
            self._vals[ref] = val

            # Now apply each commute to the latest value
            for fn, args in funcpairs:
                self._vals[ref] = fn(*RT.cons(self._vals[ref], args))

    def acquire_write_locks(self, sets, locks):
        # Acquire a write lock for all refs that were assigned to.
        # We'll need to change all of their values If we can't,
        # another transaction is committing so we retry
        for ref in sets:
            self._tryWriteLock(ref)
            locks.append(ref)

    def validate_changes(self, vals):
        # Call validators on each ref about to be changed to make sure the change is allowed
        for ref, value in vals.items():
            ref.validate(value)

    def commit_ref_sets(self):
        notifications = []
        commitPoint = self._getCommitPoint()
        for ref in self._vals:
            oldValue      = ref._tvals.val if ref._tvals else None
            newVal        = self._vals[ref]
            historyLength = ref.historyCount()

            # Easy case: ref has no binding, so lets give it one
            if not ref._tvals:
                ref._tvals = TVal(newVal, commitPoint, self._startTime)

            # Add this new value to the tvals history chain. This happens if:
            #  1. historyCount is less than minHistory
            #  2. the ref's faults > 0 and the history chain is < maxHistory
            elif ref._faults.get() > 0 and historyLength < ref.maxHistory() or \
                   historyLength < ref.minHistory():
                ref._tvals = TVal(newVal, commitPoint, self._startTime, ref._tvals)
                ref._faults.set(0)
            # Otherwise, we recycle the oldest ref in the chain, and make it the newest
            else:
                ref._tvals       = ref._tvals.next
                ref._tvals.val   = newVal
                ref._tvals.point = commitPoint
                ref._tvals.msecs = self._startTime

            if len(ref.getWatches()) > 0:
              notifications.append([ref, oldValue, newVal])

        return notifications

    def release_locks(self, locks):
        locks.reverse()
        for ref in locks:
            ref._lock.release()

    def release_ensures(self):
        for ref in self._ensures:
            ref._lock.release_shared()
        self._ensures = []

    def send_notifications(self, tx_committed, notifications):
        try:
            if tx_committed:
                for ref, oldval, newval in notifications:
                    ref.notifyWatches(oldval, newval)
                for action in self._actions:
                    pass # TODO actions when agents are supported
        finally:
            self._actions = []

    ### External API
    @classmethod
    def get(cls):
        """
        Returns the per-thread singleton transaction
        """
        try:
            return cls.ensureGet()
        except IllegalStateException:
            return None

    @classmethod
    def ensureGet(cls):
        """
        Returns the per-thread singleton transaction, or raises
        an IllegalStateException if one is not running
        """
        try:
            transaction = cls._transactions.local
            if not transaction or not transaction._info:
                raise AttributeError
        except AttributeError:
            raise IllegalStateException("No transaction running.")
        return transaction

    @classmethod
    def runInTransaction(cls, fn):
        """
        Runs the desired function in this transaction
        """
        try:
            transaction = cls.ensureGet()
        except IllegalStateException:
            transaction = cls._transactions.local = LockingTransaction()

        if transaction._info:
            # Already running transaction... execute current transaction in it. No nested transactions in the same thread
            return apply(fn)

        return transaction.run(fn)

########NEW FILE########
__FILENAME__ = mapentry
from clojure.lang.amapentry import AMapEntry


class MapEntry(AMapEntry):
    """Concrete implementation of an AMapEntry.

    Contains the attributes _key and _value with associated getKey() and
    getValue() methods."""
    def __init__(self, key, value):
        """Instantiate a MapEntry.

        key -- any object       # ???: any hashable object
        value -- any object"""
        self._key = key
        self._value = value

    def getKey(self):
        """Return the key of this MapEntry."""
        return self._key

    def getValue(self):
        """Return the value of this MapEntry."""
        return self._value

########NEW FILE########
__FILENAME__ = multimethod
from clojure.lang.cljkeyword import Keyword

default = Keyword("default")

class MultiMethodException(Exception):
    def __init__(self, reason):
        Exception.__init__(self, reason)

class MultiMethod(object):
    def __init__(self, selector):
        self.selector = selector
        self.fns = {}
        self.default = None
        
    def addMethod(self, value, fn):
        if value in self.fns:
            raise MultiMethodException("Method already exists for value {0}".format(value))
        if value == default and self.default is not none:
            raise MultiMethodException("Method already exists for value {0}".format(value))

        if value == default:
            self.default = fn
        else:
            self.fns[value]
            
    def __call__(self, *args):
        dval = self.selector(*args)
        
        try:
            fn = self.fns[dval]
        except KeyError:
            if not self.default:
                return self.default(*args)
            raise MultiMethodException("No match for dispatch value {0}".format(value))
        
        return fn(*args)


########NEW FILE########
__FILENAME__ = named
from clojure.lang.cljexceptions import AbstractMethodCall


class Named(object):
    def getNamespace(self):
        raise AbstractMethodCall(self)

    def getName(self):
        raise AbstractMethodCall(self)

########NEW FILE########
__FILENAME__ = namespace
from clojure.lang.cljexceptions import (InvalidArgumentException,
                                        IllegalArgumentException)
from clojure.lang.symbol import Symbol
from clojure.lang.var import Var
import clojure.standardimports as stdimps
import sys
from types import ModuleType


class Namespace(ModuleType):
    def __new__(cls, name):
        """Returns a namespace with a given name, creating it if needed.

        Adds standard imports to a module without clojure.core.
        clojure.core is special-cased: being the first created module, some
        specific Vars must be added "by hand" (currently: *ns*,
        *command-line-args*).
        """
        if isinstance(name, Symbol):
            name = name.name
        if not sys.modules.get(name):
            mod = ModuleType.__new__(cls)
            ModuleType.__init__(mod, name)
            mod.__file__ = "<interactive namespace>"
            for i in dir(stdimps):
                if i.startswith("_"):
                    continue
                setattr(mod, i, getattr(stdimps, i))
            if mod.__name__ == "clojure.core":
                setattr(mod, "*ns*", Var(mod, "*ns*", mod).setDynamic())
                setattr(mod, "*command-line-args*",
                        Var(mod, "*command-line-args*", None).setDynamic())
            sys.modules[name] = mod
        return sys.modules[name]

    def __init__(self, name):
        """Bypasses ModuleType.__init__.
        """


def findNS(name, fromns=None):
    """Finds a namespace, possibly as an defined as an alias in another one.
    """
    symbol_name = Symbol(name)
    if symbol_name in getattr(fromns, "__aliases__", {}):
        return fromns.__aliases__[symbol_name]
    return sys.modules.get(str(name))

def remove(ns):
    """Removes a namespace from sys.modules.
    """
    name = findNS(ns).__name__
    if name == "clojure.core":
        raise IllegalArgumentException("Cannot remove clojure.core namespace")
    del sys.modules[name]


def intern(ns, sym):
    """Interns a non-ns-qualified Symbol in a namespace.
    """
    sym = Symbol(sym)
    if sym.ns is not None:
        raise InvalidArgumentException(
            "Can't intern namespace-qualified symbol")
    if not isinstance(ns, ModuleType):
        raise InvalidArgumentException
    v = getattr(ns, str(sym), None)
    if v is not None:
        if not isinstance(v, Var):
            raise Exception(
                "Can't redefine {0} as {1}: is not Var".format(v, sym))
        if ns.__name__ == v.ns.__name__:
            return v
    v = Var(ns, sym)
    setattr(ns, sym.name, v)
    return v


def findItem(ns, sym):
    """Resolves a Symbol, ns-qualified or not, in a namespace.

    None is returned if the Symbol cannot be resolved.
    """
    if sym.ns == ns.__name__:
        return getattr(ns, sym.name, None)
    if sym.ns is not None:
        mod = findNS(sym.ns, fromns=ns)
        return getattr(mod, sym.name, None)
    return getattr(ns, sym.name, None)


########NEW FILE########
__FILENAME__ = obj
from clojure.lang.iobj import IObj
from clojure.lang.cljexceptions import AbstractMethodCall


class Obj(IObj):
    """An object that may have meta data attached.

    _meta -- a PersistentHashMap
             This attribute may not exist if a map has not been assigned.

    This map does not change the identiy of the object. When two subclass
    instances are compared, their meta data should be disregarded."""
    def meta(self):
        """Return a PersistentHashMap or None if no meta data attached."""
        return getattr(self, "_meta", None)

    def withMeta(self, meta):
        """Attach meta data to a subclass instance.

        meta -- a PersistentHashMap

        Subclasses generally return a *new* instance of themselves with meta
        attached.

        This base raises AbstractMethodCall"""
        raise AbstractMethodCall(self)

########NEW FILE########
__FILENAME__ = persistentarraymap
from clojure.lang.cljexceptions import ArityException, InvalidArgumentException, IllegalAccessError
from clojure.lang.apersistentmap import APersistentMap
from clojure.lang.atransientmap import ATransientMap
from clojure.lang.ieditablecollection import IEditableCollection
from clojure.lang.mapentry import MapEntry
from clojure.lang.aseq import ASeq
from clojure.lang.counted import Counted
from threading import currentThread

HASHTABLE_THRESHOLD = 16

class PersistentArrayMap(APersistentMap, IEditableCollection):
    def __init__(self, *args):
        if len(args) == 0:
            self.array = []
            self._meta = None
        elif len(args) == 1:
            self.array = args[0]
            self._meta = None
        elif len(args) == 2:
            self._meta = args[0]
            self.array = args[1]
        else:
            raise ArityException()

    def withMeta(self, meta):
        return PersistentArrayMap(meta, self.array)

    def createHT(self, init):
        return PersistentArrayMap(self.meta(), init)

    def assoc(self, key, val):
        i = self.indexOf(key)
        if i >= 0: # already have the key
            if self.array[i + 1] == val:
                return self # no op
            newarray = self.array[:]
            newarray[i + 1] = val
        else:
            if len(self.array) > HASHTABLE_THRESHOLD:
                return self.createHT(self.array).assoc(key, val)
            newarray = self.array[:]
            newarray.append(key)
            newarray.append(val)

        return create(newarray)

    def without(self, key):
        i = self.indexOf(key)
        if i >= 0:
            newlen = len(self.array) - 2
            if not newlen:
                return self.empty()
            newarr = self.array[:i]
            newarr.extend(self.array[i+2:])
            return create(newarr)
        return self

    def empty(self):
        return EMPTY.withMeta(self.meta())

    def containsKey(self, key):
        return self.indexOf(key) >= 0

    def count(self):
        return len(self.array) / 2

    def indexOf(self, key):
        for x in range(len(self.array), 2):
            if self.array[x] == key:
                return x
        return -1

    def entryAt(self, key):
        i = self.indexOf(key)
        if i >= 0:
            return MapEntry(self.array[i], self.array[i+1])
        return None

    def valAt(self, key, notFound = None):
        i = self.indexOf(key)
        if i >= 0:
            return self.array[i + 1]
        return notFound

    def seq(self):
        return Seq(self.array, 0)

    def meta(self):
        return self._meta

    def interator(self):
        for x in range(0, len(self.array), 2):
            yield MapEntry(self.array[x], self.array[x + 1])

    def asTransient(self):
        return TransientArrayMap(self.array)

def create(*args):
    return PersistentArrayMap(None, args)

def createWithCheck(self, init):
    for i in range(0, len(init), 2):
        for j in range(i+2, len(init), 2):
            if init[i] == init[j]:
                raise InvalidArgumentException(
                    "Duplicate Key {0}".format(init[i]))
    return PersistentArrayMap(init)

class Seq(ASeq, Counted):
    def __init__(self, *args):
        if len(args) == 2:
            self._meta = None
            self.array = args[1]
            self.i = args[2]
        elif len(args) == 3:
            self._meta = args[0]
            self.array = args[1]
            self.i = args[2]
        else:
            raise ArityException()

    def first(self):
        return MapEntry(self.array[self.i], self.array[self.i + 1])

    def next(self):
        return Seq(self.array, self.i + 2)

    def count(self):
        return (len(self.array) - self.i) / 2

    def withMeta(self, meta):
        return Seq(meta, self.array, self.i)

class TransientArrayMap(ATransientMap):
    def __init__(self, array):
        self.owner = currentThread()
        self.array = array[:]

    def indexOf(self, key):
        for x in range(0, len(self.array), 2):
            if self.array[x] == key:
                return x
        return -1

    def doAssoc(self, key, val):
        i = self.indexOf(key)
        if i >= 0: # allready have the key
            if self.array[i + 1] == val:
                return self #no op
            self.array[i + 1] = val
        else:
            if len(self.array) > HASHTABLE_THRESHOLD:
                return create(self.array).asTransient().assoc(key, val)
            self.array.append(key)
            self.array.append(val)

        return self

    def doWithout(self, key):
        i = self.indexOf(key)
        if i >= 0:
            newlen = len(self.array) - 2
            if not newlen:
                self.array = []
                return self.empty()
            newarr = self.array[:i]
            newarr.extend(self.array[i+2:])
            self.array = newarr
        return self

    def doCount(self):
        return len(self.array) / 2

    def doPersistent(self):
        self.ensureEditable()
        self.owner = None
        return PersistentArrayMap(self.array)

    def doValAt(self, key, notFound = None):
        i = self.indexOf(key)
        if i >= 0:
            return self.array[i + 1]
        return notFound

    def ensureEditable(self):
        if self.owner is currentThread():
            return
        if self.owner is None:
            raise IllegalAccessError("Transient used by non-owner thread")
        raise IllegalAccessError("Transient used after persistent! call")

EMPTY = PersistentArrayMap()

########NEW FILE########
__FILENAME__ = persistenthashmap
from clojure.lang.apersistentmap import APersistentMap
from clojure.lang.cljexceptions import ArityException, AbstractMethodCall
from clojure.lang.ieditablecollection import IEditableCollection
from clojure.lang.iobj import IObj
from clojure.lang.aseq import ASeq
from clojure.lang.util import bitCount, arrayCopy
from clojure.lang.box import Box
from clojure.lang.atomicreference import AtomicReference
from clojure.lang.mapentry import MapEntry
from clojure.lang.cons import Cons

def mask(h, shift):
    return (h >> shift) & 0x01f

def cloneAndSet(array, i, a, j = None, b = None):
    clone = array[:]
    clone[i] = a
    if j:
        clone[j] = b
    return clone

def bitpos(hsh, shift):
    return 1 << mask(hsh, shift)

def createNode(*args):
    if len(args) == 7:
        edit, shift, key1, val1, key2hash, key2, val2 = args
    elif len(args) == 6:
        shift, key1, val1, key2hash, key2, val2 = args
        edit = AtomicReference()
    else:
        raise ArityException()

    if shift > 64:
        raise Exception("Shift max reached")

    key1hash = hash(key1)
    if key1hash == key2hash:
        return HashCollisionNode(None, key1hash, 2, [key1, val1, key2, val2])
    nbox = Box(None)
    nd1 =  EMPTY_BITMAP_NODE \
            .assocEd(edit, shift, key1hash, key1, val1, nbox)
    nd2 = nd1.assocEd(edit, shift, key2hash, key2, val2, nbox)
    return nd2

def removePair(array, i):
    newArray = array[:2*i]
    newArray.extend(array[2*(i + 1):])
    return newArray

class PersistentHashMap(APersistentMap, IEditableCollection, IObj):
    def __init__(self, *args):
        """Instantiate a PersistentHashMap

        args must be one of

        * int, INode, bool, object
        * IPersistentMap, int, INode bool object
        """
        if len(args) == 4:
            self._meta = None        # IPersistentMap
            self.count = args[0]     # int
            self.root = args[1]      # INode
            self.hasNull = args[2]   # bool
            self.noneValue = args[3] # object
        elif len(args) == 5:
            self._meta = args[0]
            self.count = args[1]
            self.root = args[2]
            self.hasNull = args[3]
            self.noneValue = args[4]
        else:
            raise ArityException()

    def withMeta(self, meta):
        if self._meta is meta:
            return self
        return PersistentHashMap(meta,
                                 self.count,
                                 self.root,
                                 self.hasNull,
                                 self.noneValue)

    def assoc(self, key, val):
        if key is None:
            if self.hasNull and val == self.noneValue:
                return self
            return PersistentHashMap(self._meta, self.count if self.hasNull else self.count + 1, self.root, True, val)
        addedLeaf = Box(None)
        newRoot = EMPTY_BITMAP_NODE if self.root is None else self.root
        newRoot = newRoot.assoc(0, hash(key), key, val, addedLeaf)

        if newRoot == self.root:
            return self

        return PersistentHashMap(self._meta, self.count if addedLeaf.val is None else self.count + 1, newRoot, self.hasNull, self.noneValue)

    def without(self, key):
        if key is None:
            return PersistentHashMap(self._meta, self.count - 1, self.root, False, None) if self.hasNull else self

        if self.root is None:
            return self
        newroot = self.root.without(0, hash(key), key)
        if newroot is self.root:
            return self

        return PersistentHashMap(self._meta, self.count - 1, newroot, self.hasNull, self.noneValue)

    def valAt(self, key, notFound = None):
        if key is None:
            return self.noneValue if self.hasNull else notFound
        return self.root.find(0, hash(key), key, notFound) if self.root is not None else notFound

    def entryAt(self, key, notFound = None):
        val = self.root.find(0, hash(key), key, notFound) if self.root is not None else notFound
        return MapEntry(key, val) if val is not None else None

    def seq(self):
        s =  self.root.nodeSeq() if self.root is not None else None
        return Cons(MapEntry(None, self.noneValue), s) if self.hasNull else s

    def __len__(self):
        return self.count

    def containsKey(self, key):
        if key is None:
            return self.hasNull
        if self.root is not None:
            return self.root.find(0, hash(key), key, NOT_FOUND) \
                is not NOT_FOUND
        else:
            return False
        
    def __repr__(self):
        s = []
        for x in self:
            s.append(repr(x))
            s.append(repr(self[x]))
        return "{" + " ".join(s) + "}"

def fromDict(d):
    m = EMPTY
    for v in d:
        m = m.assoc(v, d[v])
    return m


class INode(object):
    def assoc(self, shift,  hsh, key, val, addedLeaf):
        raise AbstractMethodCall(self)

    def without(self,  shift,  hsh, key):
        raise AbstractMethodCall(self)

    def find(self,  shift,  hsh, key, notFound = None):
        raise AbstractMethodCall(self)

    def nodeSeq(self):
        raise AbstractMethodCall(self)

    def assocEd(self, edit,  shift, hsh, key, val, addedLeaf):
        raise AbstractMethodCall(self)

    def withoutEd(self,  edit,  shift,  hsh,  key,  removedLeaf):
        raise AbstractMethodCall(self)

class ArrayNode(INode):
    def __init__(self, edit, count, array):
        self.edit = edit
        self.count = count
        self.array = array

    def assoc(self, shift,  hsh, key, val, addedLeaf):
        idx = mask(hsh, shift)
        node = self.array[idx]
        if node is None:
            bmn = EMPTY_BITMAP_NODE.assoc(shift + 5, hsh, key, val, addedLeaf)
            setto = cloneAndSet(self.array, idx, bmn)
            return ArrayNode(None, self.count + 1, setto)
        n = node.assoc(shift + 5, hsh, key, val, addedLeaf)
        if n == node:
            return self
        return ArrayNode(None, self.count, cloneAndSet(self.array, idx, n))

    def without(self,  shift,  hsh, key):
        idx = mask(hsh, shift)
        node = self.array[idx]
        if node is None:
            return self
        n = node.without(shift + 5, hsh, key)
        if n is None:
            return self
        if node is None:
            if self.count <= 8:
                return self.pack(None, idx)
            return ArrayNode(None, self.count - 1, cloneAndSet(self.array, idx, n))
        else:
            return ArrayNode(None, self.count, cloneAndSet(self.array, idx, n))

    def find(self, shift, hsh, key, notFound = None):
        idx = mask(hsh, shift)
        node = self.array[idx]
        if node is None:
            return notFound
        return node.find(shift + 5, hsh, key, notFound)

    def ensureEditable(self, edit):
        if self.edit == edit:
            return self
        return ArrayNode(edit, self.count, self.array[:])

    def editAndSet(self, edit, i, n):
        editable = self.ensureEditable(edit)
        editable.array[i] = n
        return editable

    def pack(self, edit, idx):
        newArray = [None] * (2 * (self.count - 1))
        j = 1
        bitmap = 0
        for i in range(0, idx):
            if self.array[i] is None:
                newArray[j] = self.array[i]
                bitmap |= 1 << i
                j += 2
        for i in range(idx + 1, len(self.array)):
            if self.array[i] is None:
                newArray[j] = self.array[i]
                bitmap != 1 << i
                j += 2
        return BitmapIndexedNode(edit, bitmap, newArray)

    def assocEd(self, edit,  shift, hsh, key, val, addedLeaf):
        idx = mask(hsh, shift)
        node = self.array[idx]
        if node is None:
            nnode = EMPTY_BITMAP_NODE.assocEd(edit, shift + 5, hsh, key, val, addedLeaf)
            editable = self.editAndSet(edit, idx, nnode)
            editable.count += 1
            return editable
        n = node.assoc(edit, shift + 5, hsh, key, val, addedLeaf)
        if n is node:
            return self
        return self.editAndSet(edit, idx, n)

    def withoutEd(self,  edit,  shift,  hsh,  key,  removedLeaf):
        idx = mask(hsh, shift)
        node = self.array[idx]
        if node is None:
            return self
        n = node.without(edit, shift + 5, hsh, key, removedLeaf)
        if n is node:
            return self
        if n is None:
            if self.count <= 8: #shrink
                return self.pack(edit, idx)
            editable = self.editAndSet(edit, idx, n)
            editable.count -= 1
            return editable
        return self.editAndSet(edit, idx, n)

    def nodeSeq(self):
        return createSeq(self.array)

class Seq(ASeq):
    def __init__(self, meta, nodes, i, s):
        self._meta = meta
        self.nodes = nodes
        self.i = i
        self.s = s

    def withMeta(self, meta):
        return createSeq(meta, self.nodes, self.i, self.s)

    def first(self):
        return self.s.first()

    def next(self):
        return createSeq(None, self.nodes, self.i, self.s.next())

def createSeq(*args):
    if len(args) == 1:
        return createSeq(None, args[0], 0, None)
    if len(args) != 4:
        raise ArityException()
    meta, nodes, i, s = args
    if s is not None:
        return Seq(meta, nodes, i, s)
    for j in range(i, len(nodes)):
        if nodes[j] is not None:
            ns = nodes[j].nodeSeq()
            if ns is not None:
                return Seq(meta, nodes, j + 1, ns)
    return None

class BitmapIndexedNode(INode):
    def __init__(self, edit, bitmap, array):
        self.edit = edit
        self.bitmap = bitmap
        self.array = array

    def nodeSeq(self):
        return createNodeSeq(self.array)

    def index(self, bit):
        return bitCount(self.bitmap & (bit - 1))

    def assoc(self, shift,  hsh, key, val, addedLeaf):
        bit = bitpos(hsh, shift)
        idx = self.index(bit)
        if self.bitmap & bit:
            keyOrNull = self.array[2*idx]
            valOrNode = self.array[2*idx+1]

            if keyOrNull is None:
                n = valOrNode.assoc(shift + 5, hsh, key, val, addedLeaf)
                if n is valOrNode:
                    return self
                return BitmapIndexedNode(None, self.bitmap, cloneAndSet(self.array, 2*idx+1, n))

            if key == keyOrNull:
                if val is valOrNode:
                    return self
                return BitmapIndexedNode(None, self.bitmap, cloneAndSet(self.array, 2*idx+1, val))

            addedLeaf.val = addedLeaf
            return BitmapIndexedNode(None, self.bitmap,
                                    cloneAndSet(self.array,
                                                2*idx, None,
                                                2*idx+1, createNode(None, shift + 5, keyOrNull, valOrNode, hsh, key, val)))
        else:
            n = bitCount(self.bitmap)
            if n >= 16:
                nodes = [None] * 32
                jdx = mask(hsh, shift)
                nodes[jdx] = EMPTY_BITMAP_NODE.assoc(shift + 5, hsh, key, val, addedLeaf)
                j = 0
                for i in range(0, 32):
                    if (self.bitmap >> i) & 1:
                        if self.array[j] is None:
                            nodes[i] = self.array[j+1]
                        else:
                            nodes[i] = EMPTY_BITMAP_NODE.assoc(shift + 5, hash(self.array[j]), self.array[j], self.array[j+1], addedLeaf)
                        j += 2
                return ArrayNode(None, n + 1, nodes)
            else:
                newArray = self.array[:2 * idx]
                newArray.append(key)
                newArray.append(val)
                newArray.extend(self.array[2*idx:])
                addedLeaf.val = addedLeaf
                return BitmapIndexedNode(None, self.bitmap | bit, newArray)

    def without(self, shift, hsh, key):
        bit = bitpos(hsh, shift)
        if not (self.bitmap & bit):
            return self
        idx = self.index(bit)
        keyOrNull = self.array[2*idx]

        valOrNode = self.array[2*idx+1]
        if keyOrNull is None:
            n =  valOrNode.without(shift + 5, hsh, key)
            if n is valOrNode:
                return self
            if n is not None:
                return BitmapIndexedNode(None, self.bitmap, cloneAndSet(self.array, 2*idx+1, n))
            if self.bitmap == bit:
                return None
            return BitmapIndexedNode(None, self.bitmap ^ bit, removePair(self.array, idx))
        if key == keyOrNull:
            return BitmapIndexedNode(None, self.bitmap ^ bit, removePair(self.array, idx))
        return self

    def find(self,  shift,  hsh, key, notFound = None):
        bit = bitpos(hsh, shift)
        if not (self.bitmap & bit):
            return notFound
        idx = self.index(bit)
        keyOrNull = self.array[2*idx]
        valOrNode = self.array[2*idx+1]
        if keyOrNull is None:
            return valOrNode.find(shift + 5, hsh, key, notFound)
        if key == keyOrNull:
            return valOrNode
        return notFound

    def ensureEditable(self, edit):
        if self.edit is edit:
            return self
        n = bitCount(self.bitmap)
        newArray = [None] * (2*(n+1) if n >= 0 else 4) # make room for next assoc
        arrayCopy(self.array, 0, newArray, 0, 2*n)
        return BitmapIndexedNode(self.edit, self.bitmap, newArray)

    def editAndSet(self, edit, i, a, j = None, b = None):
        editable = self.ensureEditable(edit)
        editable.array[i] = a
        if j is not None:
            editable.array[j] = b
        return editable

    def editAndRemovePair(self, edit, bit, i):
        if self.bitmap == bit:
            return None
        editable = self.ensureEditable(edit)
        editable.bitmap ^= bit
        arrayCopy(editable.array, 2*(i+1), editable.array, 2*i, len(editable.array) - 2*(i+1))
        editable.array[len(editable.array) - 2] = None
        editable.array[len(editable.array) - 1] = None
        return editable

    def assocEd(self, edit, shift, hsh, key, val, addedLeaf):
        bit = bitpos(hsh, shift)
        idx = self.index(bit)
        if self.bitmap & bit:
            keyOrNull = self.array[2*idx]
            valOrNode = self.array[2*idx+1]
            if keyOrNull is None:
                n = valOrNode.assoc(edit, shift + 5, hsh, key, val, addedLeaf)
                if n == valOrNode:
                    return self
                return self.editAndSet(edit, 2*idx+1, n)

            if key == keyOrNull:
                if val == valOrNode:
                    return self
                return self.editAndSet(edit, 2*idx+1, val)
            addedLeaf.val = addedLeaf
            return self.editAndSet(edit, 2*idx, None, 2*idx+1,
                                createNode(edit, shift + 5, keyOrNull, valOrNode, hsh, key, val))
        else:
            n = bitCount(self.bitmap)
            if n*2 < len(self.array):
                addedLeaf.val = addedLeaf
                editable = self.ensureEditable(edit)
                arrayCopy(editable.array, 2*idx, editable.array, 2*(idx+1), 2*(n-idx))
                editable.array[2*idx] = key
                editable.array[2*idx+1] = val
                editable.bitmap |= bit
                return editable
            if n >= 16:
                nodes = [None] * 32
                jdx = mask(hsh, shift)
                nodes[jdx] = EMPTY_BITMAP_NODE.assocEd(edit, shift + 5, hsh, key, val, addedLeaf)
                j = 0
                for i in range(32):
                    if (self.bitmap >> i) & 1:
                        if self.array[j] is None:
                            nodes[i] = self.array[j+1]
                        else:
                            nodes[i] = EMPTY_BITMAP_NODE.assocEd(edit,
                                                                 shift + 5,
                                                                 hash(self.array[j]),
                                                                 self.array[j],
                                                                 self.array[j+1],
                                                                 addedLeaf)
                        j += 2
                return ArrayNode(edit, n + 1, nodes)
            else:
                newArray = [None] * (2*(n+4))
                arrayCopy(self.array, 0, newArray, 0, 2*idx)
                newArray[2*idx] = key
                addedLeaf.val = addedLeaf
                newArray[2*idx+1] = val
                arrayCopy(self.array, 2*idx, newArray, 2*(idx+1), 2*(n-idx))
                editable = self.ensureEditable(edit)
                editable.array = newArray
                editable.bitmap |= bit
                return editable

    def withoutEd(self, edit, shift, hsh, key, removedLeaf):
        bit = bitpos(hsh, shift)
        if not (self.bitmap & bit):
            return self
        idx = self.index(bit)
        keyOrNull = self.array[2*idx]
        valOrNode = self.array[2*idx+1]
        if keyOrNull is None:
            n = valOrNode.without(edit, shift + 5, hsh, key, removedLeaf)
            if n is valOrNode:
                return self
            if n is not None:
                return self.editAndSet(edit, 2*idx+1, n)
            if self.bitmap == bit:
                return None
            return self.editAndRemovePair(edit, bit, idx)

        if key == keyOrNull:
            removedLeaf.val = removedLeaf
            return self.editAndRemovePair(self.edit, bit, idx)
        return self

class HashCollisionNode(INode):
    def __init__(self, edit, hsh, count, array):
        self.edit = edit
        self.hsh = hsh
        self.count = count
        self.array = array

    def assoc(self, shift,  hsh, key, val, addedLeaf):
        if hsh == self.hsh:
            idx = self.findIndex(key)
            if idx != -1:
                if self.array[idx + 1] == val:
                    return self
                return HashCollisionNode(None, hsh, self.count, cloneAndSet(self.array, idx + 1, val))
            newArray = [None] * (len(self.array) + 2)
            arrayCopy(self.array, 0, newArray, 0, len(self.array))
            newArray[len(self.array)] = key
            newArray[len(self.array) + 1] = val
            addedLeaf.val = addedLeaf
            return HashCollisionNode(self.edit, hsh, self.count + 1, newArray)

        # nest it in a bitmap node
        return BitmapIndexedNode(None, bitpos(self.hsh, shift), [None, self]) \
                                .assoc(shift, hsh, key, val, addedLeaf)

    def without(self,  shift,  hsh, key):
        idx = self.findIndex(key)
        if idx == -1:
            return self
        if self.count == 1:
            return None

        return HashCollisionNode(None, hash, self.count - 1, removePair(self.array, idx/2))

    def findIndex(self, key):
        for x in range(0, self.count * 2, 2):
            if self.array[x] == key:
                return x
        return -1

    def find(self,  shift,  hsh, key, notFound = None):
        idx = self.findIndex(key)
        if idx < 0:
            return notFound
        return self.array[idx + 1]

    def nodeSeq(self):
        return createNodeSeq(self.array)

    def ensureEditable(self, edit, i = None, array = None):
        if self.edit is edit:
            if i is not None:
                self.count = i
                self.array = array
            return self
        if i is None:
            array = self.array[:]
            array.extend([None] * 2)
            i = self.count
        return HashCollisionNode(edit, self.hsh, i, array)

    def editAndSet(self, edit, i, a, j = None, b = None):
        editable = self.ensureEditable(edit)
        editable.array[i] = a
        if j is not None:
            editable.array[j] = b
        return editable

    def assocEd(self, edit, shift, hsh, key, val, addedLeaf):
        if hsh == self.hsh:
            idx = self.findIndex(key)
            if idx != -1:
                if self.array[idx + 1] == val:
                    return self
                return self.editAndSet(edit, idx+1, val)

            if len(self.array) > 2 * self.count:
                addedLeaf.val = addedLeaf
                editable = self.editAndSet(edit, 2 * self.count, key, 2 * self.count+1, val)
                editable.count += 1
                return editable
            newArray = [None] * (len(self.array) + 2)
            arrayCopy(self.array, 0, newArray, 0, len(self.array))
            newArray[len(self.array)] = key
            newArray[len(self.array) + 1] = val
            addedLeaf.val = addedLeaf
            return self.ensureEditable(edit, self.count + 1, newArray)

        # nest it in a bitmap node
        return BitmapIndexedNode(edit, bitpos(self.hsh, shift), [None, self, None, None]) \
                                    .assocEd(edit, shift, hsh, key, val, addedLeaf)

    def withoutEd(self, edit, shift, hsh, key, removedLeaf):
        idx = self.findIndex(key)
        if idx == -1:
            return self
        removedLeaf.val = removedLeaf
        if self.count == 1:
            return None
        editable = self.ensureEditable(edit)
        editable.array[idx] = editable.array[2*self.count-2]
        editable.array[idx+1] = editable.array[2*self.count-1]
        editable.array[2*self.count-2] = editable.array[2*self.count-1] = None
        editable.count -= 1
        return editable

class NodeSeq(ASeq):
    def __init__(self, *args):
        if len(args) == 3:
            self.array, self.i, self.s = args
        elif len(args) == 4:
            self._meta, self.array, self.i, self.s = args
        else:
            raise ArityException()

    def withMeta(self, meta):
        return NodeSeq(meta, self.array, self.i, self.s)

    def first(self):
        if self.s is not None:
            return self.s.first()
        return MapEntry(self.array[self.i], self.array[self.i + 1])

    def next(self):
        if self.s is not None:
            return createNodeSeq(self.array, self.i, self.s.next())
        return createNodeSeq(self.array, self.i + 2, None)

def createNodeSeq(*args):
    if len(args) == 1:
        if len(args[0]) == 0:
            return None
        return createNodeSeq(args[0], 0, None)
    if len(args) != 3:
        raise ArityException()

    array, i, s = args
    if s is not None:
        return NodeSeq(None, array, i, s)

    for j in range(i, len(array), 2):
        if array[j] is not None:
            return NodeSeq(None, array, j, None)
        node = array[j+1]
        if node is not None:
            nodeSeq = node.nodeSeq()
            if nodeSeq is not None:
                return NodeSeq(None, array, j + 2, nodeSeq)

    return None

EMPTY = PersistentHashMap(0, None, False, None)
EMPTY_BITMAP_NODE = BitmapIndexedNode(-1, 0, [])
NOT_FOUND = AtomicReference()

########NEW FILE########
__FILENAME__ = persistenthashset
"""
March 25, 2012 -- Documented
"""

from clojure.lang.iobj import IObj
from clojure.lang.apersistentset import APersistentSet
from clojure.lang.persistenthashmap import EMPTY as EMPTY_MAP
from clojure.lang.cljexceptions import IllegalArgumentException


class PersistentHashSet(APersistentSet, IObj):
    def __init__(self, meta, impl):
        """Use create or createWithCheck to instantiate."""
        APersistentSet.__init__(self, impl)
        self._meta = meta

    def cons(self, o):
        """Return a new PersistentHashSet with o added.

        o -- any object

        The new set will have this set's meta data attached. If o is already
        in this set, return this set."""
        if o in self:
            return self
        return PersistentHashSet(self._meta, self.impl.assoc(o, o))

    def meta(self):
        """Return this PersistentHashSet's meta data'"""
        return self._meta

    def withMeta(self, meta):
        """Return a new PersistentHashSet.

        meta -- the meta data to attach to the returned set

        The set will share this set's content.'"""
        return PersistentHashSet(meta, self.impl)

    def empty(self):
        """Return an empty PersistentHashSet.

        The new set will have this set's meta data attached."""
        return EMPTY.withMeta(self.meta())

    def disjoin(self, key):
        """Return a new PersistentHashSet with key removed.

        key -- any object

        If the key is not in this set, return this set."""
        if key not in self:
            return self
        return PersistentHashSet(self._meta, self.impl.without(key))


def create(*args):
    """Return a new PersistentHashSet.

    create()
    An empty PersistentHashSet will be returned.

    create(iterable)
    The elements of the iterable will be added to the returned set. Any
    duplicates will be silently omitted.

    create(obj1, obj2, ..., objN)
    Add the objs, omitting duplicates."""
    if not len(args):
        return EMPTY
    if len(args) == 1 and hasattr(args[0], "__iter__"):
        m = EMPTY
        s = args[0]
        for x in s:
            m = m.cons(x)
        return m
    m = EMPTY
    for x in args:
        m = m.cons(x)
    return m


def createWithCheck(iterable):
    """Return a new PersistentHashSet containing the items in iterable.

    iterable -- any iterable sequence of objects

    Raise IllegalArgumentException if a duplicate is found in iterable."""
    ret = EMPTY
    for i, key in enumerate(iterable):
        ret = ret.cons(key)
        if len(ret) != i + 1:
            raise IllegalArgumentException("Duplicate key: {0}".format(key))
    return ret;


EMPTY = PersistentHashSet(None, EMPTY_MAP)

########NEW FILE########
__FILENAME__ = persistentlist
import clojure.lang.rt as RT
from clojure.lang.obj import Obj
from clojure.lang.iseq import ISeq
from clojure.lang.aseq import ASeq
from clojure.lang.ireduce import IReduce
from clojure.lang.counted import Counted
from clojure.lang.seqable import Seqable
from clojure.lang.sequential import Sequential
from clojure.lang.iprintable import IPrintable
from clojure.lang.ipersistentlist import IPersistentList
from clojure.lang.cljexceptions import ArityException, IllegalStateException


class PersistentList(ASeq, IPersistentList, IReduce, Counted):
    def __init__(self, *args):
        """Instantiate a PersistentList.

        Use persistentlist.create() to instantiate on an existing list.

        args must be 1 or 4 items:

        * object
          first and only item in the list

        * IPersistentMap, object, IPersistentList, int
          IPersistentMap -- the meta data
          object -- the first item to put in the list
          IPersistentList -- the tail of the list
          int -- the total number of items put into the list

          May raise ArityException."""
        if len(args) == 1:
            self._first = args[0]
            self._rest = None
            self._count = 1
        elif len(args) == 4:
            self._meta = args[0]
            self._first = args[1]
            self._rest = args[2]
            self._count = args[3]
        else:
            raise ArityException
        # ???: Why here and not in ASeq
        self._hash = -1

    def next(self):
        """Return an ISeq.

        The sequence will contain all but the first item in this list. If the
        list contains only one item, return None."""
        if self._count == 1:
            return None
        return self._rest

    def first(self):
        """Return the first item in this list."""
        return self._first

    def peek(self):
        """Return the first item in this list."""
        return self.first()

    def pop(self):
        """Return an IPersistentList

        If this list contains only one item, return an EmptyList with this
        list's meta data attached. Else return this list omitting the first
        item."""
        if self._rest is None:
            return EMPTY.withMeta(self._meta)
        return self._rest

    def __len__(self):
        """Return the number of items in this list."""
        return self._count

    def cons(self, o):
        """Return a new PersistentList.

        o -- any object

        The returned list will contain o as the first item and this list's
        items as the rest. Also, this list's meta data will be attached to the
        new list."""
        return PersistentList(self.meta(), o, self, self._count + 1)

    def empty(self):
        """Return an EmptyList with this list's meta data attached."""
        return EMPTY.withMeta(self.meta())

    def reduce(self, *args):
        """Reduce this list to a single value.

        args must be one of:

        * IFn
        * IFn, object

        If this list contains one item, return it. Else, apply the given
        binary function to the first two items in the list. The result of that
        becomes the first argument of the next application of the function
        with the third item as the second argument. This continues until this
        list is exhausted.

        If the second argument is supplied to reduce, it's treated as the
        first item in this list.

        Return the result of this reduction. May raise ArityException."""
        if len(args) == 1:
            ret = self.first()
        elif len(args) == 2:
            ret = args[0](args[1], self.first())
        else:
            raise ArityException()
        fn = args[0]
        s = self.next()
        while s is not None:
            ret = fn(ret, s.first())
            s = s.next()
        return ret

    def withMeta(self, meta):
        """Return a PersistentList.

        meta -- an IPersistentMap

        If meta is equal to this list's meta return this list else return a
        new PersistentList with this lists contents and meta attached."""
        if meta != self.meta():
            return PersistentList(meta, self._first, self._rest, self._count)
        return self

# ======================================================================
# Creation
# ======================================================================

# XXX: don't think this is required
# def create(lst):
#     """Return a PersistentList with the contents of lst.

#     lst -- any object that implements __len__ and __getitem__"""
#     ret = EMPTY
#     for x in range(len(lst) - 1, -1, -1):
#         # c = lst[x]
#         ret = ret.cons(lst[x])
#     return ret


def creator(*args):
    """Return a PersistentList.

    args -- zero or more objectS"""
    ret = EMPTY
    for x in range(len(args) - 1, -1, -1):
        ret = ret.cons(args[x])
    return ret

# ======================================================================
# EmptyList
# ======================================================================

class EmptyList(Obj, IPersistentList, ISeq, Counted, IPrintable):
    """A list of zero objects."""
    def __init__(self, meta=None):
        """This is a psuedo-singleton class, use persistentlist.EMPTY."""
        self._meta = meta

    def __hash__(self):
        """Return the integer 1"""
        return 1

    def __eq__(self, other):
        """Return True if:

        * other is an instance of Sequential, list, or tuple, and
        * other contains no items

        Else return False."""
        return isinstance(other, (Sequential, list, tuple)) \
            and RT.protocols.seq(other) == None

    def __ne__(self, other):
        """Return not self.__eq__(other).

        other -- any object
        """
        return not self == other

    def __iter__(self):
        """Return None"""
        return

    def withMeta(self, meta):
        """Return an EmptyList with meta attached.

        meta -- an IPersistentMap

        If meta is equal to this list's meta return this list else return a
        new EmptyList with meta attached."""
        if self._meta == meta:
            return self
        return EmptyList(meta)

    def first(self):
        """Return None"""
        return None

    def next(self):
        """Return None"""
        return None

    def more(self):
        """Return this PersistentList."""
        return self

    def cons(self, o):
        """Return a new PersistentList.

        o -- any object

        The returned list will contain o as the first item and this list's
        items as the rest. Also, this list's meta data will be attached to the
        new list."""
        return PersistentList(self.meta(), o, None, 1)

    def empty(self):
        """Return this PersistentList."""
        return self

    def peek(self):
        """Return None."""
        return None

    def pop(self):
        """Raise IllegalStateException."""
        raise IllegalStateException("Can't pop an empty list")

    def count(self):
        """Return 0."""
        return 0

    def seq(self):
        """Return None."""
        return None

    def writeAsString(self, writer):
        """See: EmptyList.__str__"""
        writer.write(str(self))

    def writeAsReplString(self, writer):
        """See: EmptyList.__repr__"""
        writer.write(repr(self))

    def __str__(self):
        """Return the string "()"."""
        return "()"

    def __repr__(self):
        """Return the Python readable string "()"."""
        return "()"

    def __len__(self):
        """Return 0."""
        return 0

# ======================================================================
# Pseudo-Singleton
# ======================================================================

EMPTY = EmptyList()

########NEW FILE########
__FILENAME__ = persistenttreemap
from clojure.lang.apersistentmap import APersistentMap
from clojure.lang.aseq import ASeq
from clojure.lang.box import Box
from clojure.lang.cljexceptions import (ArityException,
                                        AbstractMethodCall,
                                        IllegalArgumentException,
                                        UnsupportedOperationException)
from clojure.lang.comparator import Comparator
from clojure.lang.iobj import IObj
from clojure.lang.ipersistentmap import IPersistentMap
from clojure.lang.iseq import ISeq
from clojure.lang.reversible import Reversible
import clojure.lang.rt as RT


class PersistentTreeMap(APersistentMap, IObj, Reversible):
    def __init__(self, *args):
        if len(args) == 0:
            self._meta = None
            self.comp = RT.DefaultComparator()
            self.tree = None
            self._count = 0
        elif len(args) == 1:
            self._meta = None
            self.comp = args[0]
            self.tree = None
            self._count = 0
        elif len(args) == 2:
            self._meta = args[0]
            self.comp = args[1]
            self.tree = None
            self._count = 0
        elif len(args) == 4 and isinstance(args[0], IPersistentMap):
            self._meta = args[0]
            self.comp = args[1]
            self.tree = args[2]
            self._count = args[2]
        elif len(args) == 4 and isinstance(args[0], Comparator):
            self.comp = args[0]
            self.tree = args[1]
            self._count = args[2]
            self._meta = args[3]
        else:
            raise ArityException()

    def withMeta(self, meta):
        return PersistentTreeMap(meta, self.comp, self.tree, self._count)

    def containsKey(self, key):
        return self.entryAt(key) is not None

    def assocEx(self, key, val):
        found = Box(None)
        t = self.add(self.tree, key, val, found)
        if t is None:   # None == already contains key
            raise Util.runtimeException("Key already present")#FIXME: Util not defined anywhere?
        return PersistentTreeMap(self.comp, t.blacken(), self._count + 1, self.meta())

    def assoc(self, key, val):
        found = Box(None)
        t = self.add(self.tree, key, val, found)
        if t is None: # None == already contains key
            foundNode = found.val
            if foundNode.val() is val: # note only get same collection on identity of val, not equals()
                return self
            return PersistentTreeMap(self.comp, self.replace(self.tree, key, val), self._count, self.meta())
        return PersistentTreeMap(self.comp, t.blacken(), self._count + 1, self.meta())

    def without(self, key):
        found = Box(None)
        t = self.remove(self.tree, key, found)
        if t is None:
            if found.val is None: # None == doesn't contain key
                return self
            # empty
            return PersistentTreeMap(self.meta(), self.comp)
        return PersistentTreeMap(self.comp, t.blacken(), self._count - 1, self.meta())

    def seq(self, *args):
        if len(args) == 0:
            if self._count > 0:
                return createSeq(self.tree, True, self._count)
            return None
        elif len(args) == 1:
            ascending = args[0]
            if self._count > 0:
                return createSeq(self.tree, ascending, self._count)
            return None
        else:
            raise ArityException()

    def empty(self):
        return PersistentTreeMap(self.meta(), self.comp);	

    def rseq(self):
        if self._count > 0:
            return createSeq(self.tree, False, self._count)
        return None

    def comparator(self):
        return self.comp

    def seqFrom(self, key, ascending):
        if self._count > 0:
            stack = None
            t = self.tree
            while t is not None:
                c = self.doCompare(key, t.key())
                if c == 0:
                    stack = RT.cons(t, stack)
                    return Seq(stack, ascending)
                elif ascending:
                    if c < 0:
                        stack = RT.cons(t, stack)
                        t = t.left()
                    else:
                        t = t.right()
                else:
                    if c > 0:
                        stack = RT.cons(t, stack)
                        t = t.right()
                    else:
                        t = t.left()
            if stack is not None:
                return Seq(stack, ascending)
        return None

    def iterator(self):
        return NodeIterator(self.tree, True)

    def reverseIterator(self):
        return NodeIterator(self.tree, False)

    def keys(self, *args):
        if len(args) == 0:
            return self.keys(self.iterator())
        elif len(args) == 1:
            it = args[0]
            return KeyIterator(it)

    def vals(self, *args):
        if len(args) == 0:
            return self.vals(self.iterator())
        elif len(args) == 1:
            it = args[0]
            return ValIterator(it)

    def minKey(self):
        t = self.min()
        return t.key() if t is not None else None

    def min(self):
        t = self.tree
        if t is not None:
            while t.left() is not None:
                t = t.left()
        return t

    def maxKey(self):
        t = self.max()
        return t.key() if t is not None else None

    def max(self):
        t = self.tree
        if t is not None:
            while t.right() is not None:
                t = t.right()
        return t

    def depth(self, *args):
        if len(args) == 0:
            return self.depth(self.tree)
        if len(args) == 1:
            t = args[0]
            if t is None:
                return 0
            return 1 + max([self.depth(t.left()), self.depth(t.right())])

    def valAt(self, *args):
        if len(args) == 1:
            key = args[0]
            return self.valAt(key, None)
        elif len(args) == 2:
            key = args[0]
            notFound = args[1]
            n = self.entryAt(key)
            return n.val() if n is not None else notFound

    def capacity(self):
        return self._count
    count = capacity

    def entryAt(self, key):
        t = self.tree
        while t is not None:
            c = self.doCompare(key, t.key())
            if c == 0:
                return t
            elif c < 0:
                t = t.left()
            else:
                t = t.right()
        return t

    def doCompare(self, k1, k2):
        return self.comp.compare(k1, k2)

    def add(self, t, key, val, found):
        if t is None:
            if val is None:
                return Red(key)
            return RedVal(key, val)
        c = self.doCompare(key, t.key())
        if c == 0:
            found.val = t
            return None
        ins = self.add(t.left(), key, val, found) if c < 0 else self.add(t.right(), key, val, found)
        if ins is None: # found below
            return None
        if c < 0:
            return t.addLeft(ins)
        return t.addRight(ins)

    def remove(self, t, key, found):
        if t is None:
            return None; # not found indicator
        c = self.doCompare(key, t.key())
        if c == 0:
            found.val = t
            return self.append(t.left(), t.right())
        del_ = self.remove(t.left(), key, found) if c < 0 else self.remove(t.right(), key, found)
        if del_ is None and found.val is None: # not found below
            return None
        if c < 0:
            if isinstance(t.left(), Black):
                return self.balanceLeftDel(t.key(), t.val(), del_, t.right())
            else:
                return red(t.key(), t.val(), del_, t.right())
        if isinstance(t.right(), Black):
            return self.balanceRightDel(t.key(), t.val(), t.left(), del_)
        return red(t.key(), t.val(), t.left(), del_)

    def append(self, left, right):
        if left is None:
            return right
        elif right is None:
            return left
        elif isinstance(left, Red):
            if isinstance(right, Red):
                app = self.append(left.right(), right.left())
                if isinstance(app, Red):
                    return red(app.key(), app.val(),
                               red(left.key(), left.val(), left.left(), app.left()),
                               red(right.key(), right.val(), app.right(), right.right()))
                else:
                    return red(left.key(), left.val(), left.left(), red(right.key(), right.val(), app, right.right()))
            else:
                return red(left.key(), left.val(), left.left(), self.append(left.right(), right))
        elif isinstance(right, Red):
            return red(right.key(), right.val(), self.append(left, right.left()), right.right())
        else: # black/black
            app = self.append(left.right(), right.left())
            if isinstance(app, Red):
                return red(app.key(), app.val(),
                           black(left.key(), left.val(), left.left(), app.left()),
                           black(right.key(), right.val(), app.right(), right.right()))
            else:
                return self.balanceLeftDel(left.key(), left.val(), left.left(), black(right.key(), right.val(), app, right.right()))

    def balanceLeftDel(self, key, val, del_, right):
        if isinstance(del_, Red):
            return red(key, val, del_.blacken(), right)
        elif isinstance(right, Black):
            return self.rightBalance(key, val, del_, right.redden())
        elif isinstance(right, Red) and isinstance(right.left(), Black):
            return red(right.left().key(), right.left().val(),
                       black(key, val, del_, right.left().left()),
                       self.rightBalance(right.key(), right.val(), right.left().right(), right.right().redden()))
        else:
            raise UnsupportedOperationException("Invariant violation")

    def balanceRightDel(self, key, val, left, del_):
        if isinstance(del_, Red):
            return red(key, val, left, del_.blacken())
        elif isinstance(left, Black):
            return self.leftBalance(key, val, left.redden(), del_)
        elif isinstance(left, Red) and isinstance(left.right(), Black):
            return red(left.right().key(), left.right().val(),
                       self.leftBalance(left.key(), left.val(), left.left().redden(), left.right().left()),
                       black(key, val, left.right().right(), del_))
        else:
            raise UnsupportedOperationException("Invariant violation")

    def leftBalance(self, key, val, ins, right):
        if isinstance(ins, Red) and isinstance(ins.left(), Red):
            return red(ins.key(), ins.val(), ins.left().blacken(), black(key, val, ins.right(), right))
        elif isinstance(ins, Red) and isinstance(ins.right(), Red):
            return red(ins.right().key(), ins.right().val(),
                       black(ins.key(), ins.val(), ins.left(), ins.right().left()),
                       black(key, val, ins.right().right(), right))
        else:
            return black(key, val, ins, right)

    def rightBalance(self, key, val, left, ins):
        if isinstance(ins, Red) and isinstance(ins.right(), Red):
            return red(ins.key(), ins.val(), black(key, val, left, ins.left()), ins.right().blacken())
        elif isinstance(ins, Red) and isinstance(ins.left(), Red):
            return red(ins.left().key(), ins.left().val(),
                       black(key, val, left, ins.left().left()),
                       black(ins.key(), ins.val(), ins.left().right(), ins.right()))
        else:
            return black(key, val, left, ins)

    def replace(self, t, key, val):
        c = self.doCompare(key, t.key())
        return t.replace(t.key(),
                         val if c == 0 else t.val(),
                         self.replace(t.left(), key, val) if c < 0 else t.left(),
                         self.replace(t.right(), key, val) if c > 0 else t.right())

    def meta(self):
        return self._meta

EMPTY = PersistentTreeMap()


def create(self, *args):
    if len(args) == 1 and isinstance(args[0], Map):#FIXME: Map undefined
        other = args[0]
        ret = EMPTY
        for o in other.entrySet():
            ret = ret.assoc(o.getKey(), o.getValue())
        return ret
    elif len(args) == 1 and isinstance(args[0], ISeq):
        items = args[0]
        ret = EMPTY
        while items is not None:
            if items.next() is None:
                raise IllegalArgumentException("No value supplied for key: %s" % items.first())
            ret = ret.assoc(items.first(), RT.second(items))
            items = items.next().next()
        return ret
    elif len(args) == 2:
        comp = args[0]
        items = args[1]
        ret = PersistentTreeMap(comp)
        while items is not None:
            if items.next() is None:
                raise IllegalArgumentException("No value supplied for key: %s" % items.first())
            ret = ret.assoc(items.first(), RT.second(items))
            items = items.next().next()
        return ret

def entryKey(entry):
    return entry.key()

def red(key, val, left, right):
    if left is None and right is None:
        if val is None:
            return Red(key)
        return RedVal(key, val)
    if val is None:
        return RedBranch(key, left, right)
    return RedBranchVal(key, val, left, right)

def black(key, val, left, right):
    if left is None and right is None:
        if val is None:
            return Black(key)
        return BlackVal(key, val)
    if val is None:
        return BlackBranch(key, left, right)
    return BlackBranchVal(key, val, left, right)


class Node(object):
    def __init__(self, key):
        self._key = key

    def key(self):
        return self._key
    getKey = key

    def val(self):
        return None
    getValue = val

    def left(self):
        return None

    def right(self):
        return None

    def addLeft(self, ins):
        raise AbstractMethodCall()

    def addRight(self, ins):
        raise AbstractMethodCall()

    def removeLeft(self, del_):
        raise AbstractMethodCall()

    def removeRight(self, del_):
        raise AbstractMethodCall()

    def blacken(self):
        raise AbstractMethodCall()

    def redden(self):
        raise AbstractMethodCall()

    def balanceLeft(self, parent):
        return black(parent.key(), parent.val(), self, parent.right())

    def balanceRight(self, parent):
        return black(parent.key(), parent.val(), parent.left(), self)

    def replace(self, key, val, left, right):
        raise AbstractMethodCall()


class Black(Node):
    def addLeft(self, ins):
        return ins.balanceLeft(self)

    def addRight(self, ins):
        return ins.balanceRight(self)

    def removeLeft(self, del_):
        return self.balanceLeftDel(self.key(), self.val(), del_, self.right())

    def removeRight(self, del_):
        return self.balanceRightDel(self.key(), self.val(), self.left(), del_)

    def blacken(self):
        return self

    def redden(self):
        return Red(self.key)

    def replace(self, key, val, left, right):
        return black(key, val, left, right)


class BlackVal(Black):
    def __init__(self, key, val):
        super(BlackVal, self).__init__(key)
        self._val = val

    def val(self):
        return self._val

    def redden(self):
        return RedVal(self._key, self._val)


class BlackBranch(Black):
    def __init__(self, key, left, right):
        super(BlackBranch, self).__init__(key)
        self._left = left
        self._right = right

    def left(self):
        return self._left

    def right(self):
        return self._right

    def redden(self):
        return RedBranch(self._key, self._left, self._right)


class BlackBranchVal(BlackBranch):
    def __init__(self, key, val, left, right):
        super(BlackBranchVal, self).__init__(key, left, right)
        self._val = val

    def val(self):
        return self._val

    def redden(self):
        return RedBranchVal(self._key, self._val, self._left, self._right)


class Red(Node):
    def addLeft(self, ins):
        return red(self._key, self.val(), ins, self.right())

    def addRight(self, ins):
        return red(self._key, self.val(), self.left(), ins)

    def removeLeft(self, del_):
        return red(self._key, self.val(), del_, self.right())

    def removeRight(self, del_):
        return red(self._key, self.val(), self.left(), del_)

    def blacken(self):
        return Black(self._key)

    def redden(self):
        raise UnsupportedOperationException("Invariant violation")

    def replace(self, key, val, left, right):
        return red(key, val, left, right)


class RedVal(Red):
    def __init__(self, key, val):
        super(RedVal, self).__init__(key)
        self._val = val

    def val(self):
        return self._val

    def blacken(self):
        return BlackVal(self._key, self._val)


class RedBranch(Red):
    def __init__(self, key, left, right):
        super(RedBranch, self).__init__(key)
        self._left = left
        self._right = right

    def left(self):
        return self._left

    def right(self):
        return self._right

    def balanceLeft(self, parent):
        if isinstance(self._left, Red):
            return red(self._key, self.val(), self._left.blacken(), black(parent._key, parent.val(), self.right(), parent.right()))
        elif isinstance(self._right, Red):
            return red(self._right._key, self._right.val(), black(self._key, self.val(), self._left, self._right.left()),
                       black(parent._key, parent.val(), self._right.right(), parent.right()))
        else:
            return super(RedBranch, self).balanceLeft(parent)

    def balanceRight(self, parent):
        if isinstance(self._right, Red):
            return red(self._key, self.val(), black(parent._key, parent.val(), parent.left(), self._left), self._right.blacken())
        elif isinstance(self._left, Red):
            return red(self._left._key, self._left.val(), black(parent._key, parent.val(), parent.left(), self._left.left()),
                       black(self._key, self.val(), self._left.right(), self._right))
        else:
            return super(RedBranch, self).balanceRight(parent)

    def blacken(self):
        return BlackBranch(self._key, self._left, self._right)


class RedBranchVal(RedBranch):
    def __init__(self, key, val, left, right):
        super(RedBranchVal, self).__init__(key, left, right)
        self._val = val

    def val(self):
        return self._val

    def blacken(self):
        return BlackBranchVal(self._key, self._val, self._left, self._right)


class Seq(ASeq):
    def __init__(self, *args):
        if len(args) == 2:
            self.stack = args[0]
            self.asc = args[1]
            self.cnt = -1
        elif len(args) == 3:
            self.stack = args[0]
            self.asc = args[1]
            self.cnt = args[2]
        elif len(args) == 4:
            super(Seq, self).__init__(args[0])
            self.stack = args[1]
            self.asc = args[2]
            self.cnt = args[3]

    def first(self):
        return self.stack.first()

    def next(self):
        t = self.stack.first()
        nextstack = pushSeq(t.right() if self.asc else t.left(), self.stack.next(), self.asc)
        if nextstack is not None:
            return Seq(nextstack, self.asc, self.cnt - 1)
        return None

    def count(self):
        if self.cnt < 0:
            return super(Seq, self).count()
        return self.cnt

    def withMeta(self, meta):
        return Seq(meta, self.stack, self.asc, self.cnt)

def createSeq(t, asc, cnt):
    return Seq(pushSeq(t, None, asc), asc, cnt)

def pushSeq(t, stack, asc):
    while t is not None:
        stack = RT.cons(t, stack)
        t = t.left() if asc else t.right()
    return stack


class NodeIterator(object):
    def __init__(self, t, asc):
        self.asc = asc
        self.stack = []
        self.push(t)

    def push(self, t):
        while t is not None:
            self.stack.append(t)
            t = t.left() if self.asc else t.right()

    def hasNext(self):
        return not self.stack.isEmpty()

    def next(self):
        t = self.stack.pop()
        self.push(t.right() if self.asc else t.left())
        return t

    def remove(self):
        raise UnsupportedOperationException()


class KeyIterator(object):
    def __init__(self, it):
        self._it = it

    def hasNext(self):
        return self._it.hasNext()

    def next(self):
        return self._it.next().key()

    def remove(self):
        raise UnsupportedOperationException()


class ValIterator(object):
    def __init__(self, it):
        self._it = it

    def hasNext(self):
        return self._it.hasNext()

    def next(self):
        return self._it.next().val()

    def remove(self):
        raise UnsupportedOperationException()

########NEW FILE########
__FILENAME__ = persistentvector
import clojure.lang.rt as RT
from clojure.lang.atomicreference import AtomicReference
from clojure.lang.apersistentvector import APersistentVector
from clojure.lang.cljexceptions import (ArityException,
                                        IllegalStateException,
                                        IndexOutOfBoundsException)


# Acts sort-of-like supplied-p in Common Lisp.
# Allows one to ascertain if a parameter foo=None was actually given specified
# in the call.
_notSupplied = object()


class PersistentVector(APersistentVector):
    """An indexable array where each operation such as cons and assocN return
    a *new* PersistentVector. The two vectors share old state, but the new
    state is only present in the newly returned vector. This preserves the
    state of the old vector prior to the operation.

    _cnt -- integer, the total number of items in the vector
    _shift -- integer, the depth of the tree, a multiple of 5, >=0
    _root -- Node, the root tree node
    _tail -- list of size 0 to 32
    _meta -- IPersistentHashMap, meta data attached to the vector"""
    def __init__(self, *args):
        """Instantiate a PersistentVector

        args must be one of:

        * int, int, Node, list
        * IPersistentHashMap, int, int, Node, list

        Else an ArityException will be raised.
        """
        if len(args) == 4:
            cnt, shift, root, tail = args
            meta = None
        elif len(args) == 5:
            meta, cnt, shift, root, tail = args
        else:
            raise ArityException()
        self._meta = meta
        self._cnt = cnt
        self._shift = shift
        self._root = root
        self._tail = tail

    def __call__(self, i):
        """Return the item at i.

        i -- integer >= 0

        May raise IndexOutOfBoundsException."""
        return self.nth(i)

    def _arrayFor(self, i):
        """Return the _tail list or a Node._array list.

        i -- integer, vector index >= 0

        The list will be a sublist of this vector where the index of its first
        element is i - i % 32. May raise IndexOutOfBoundsException."""
        if 0 <= i < self._cnt:
            if i >= self._tailoff():
                return self._tail
            node = self._root
            for level in range(self._shift, 0, -5):
                node = node._array[(i >> level) & 0x01f]
            return node._array
        raise IndexOutOfBoundsException()

    def nth(self, i, notFound=_notSupplied):
        """Return the item at index i.

        If i is out of bounds and notFound is supplied, return notFound, else
        raise IndexOutOfBoundsException."""
        if 0 <= i < self._cnt:
            node = self._arrayFor(i)
            return node[i & 0x01f]
        elif notFound is _notSupplied:
            raise IndexOutOfBoundsException()
        else:
            return notFound

    def meta(self):
        """Return this vector's meta data as an IPersistentHashMap."""
        return self._meta

    def assocN(self, i, val):
        """Return a PersistentVector with the item at index i set to val.

        i -- integer >= 0
        val -- any object

        The returned vector will contain all the items in this vector except
        for the newly *changed* value. This function will *append* val if i is
        the length of this vector. If i is > the length, raise
        IndexOutOfBoundsException. The returned vector will have this vector's
        meta data attached."""
        if 0 <= i < self._cnt:
            if i >= self._tailoff():
                newTail = self._tail[:]
                newTail[i & 0x01f] = val

                return PersistentVector(self.meta(), self._cnt, self._shift,
                                        self._root, newTail)

            n = _doAssoc(self._shift, self._root, i, val)
            return PersistentVector(self.meta(), self._cnt, self._shift, n,
                                    self._tail)
        if i == self._cnt:
            return self.cons(val)

        raise IndexOutOfBoundsException()

    def assoc(self, i, val):
        return self.assocN(i, val)

    def __len__(self):
        """Return the number of items in this vector."""
        return self._cnt

    def withMeta(self, meta):
        """Return a PersistentVector.

        meta -- an IPersistentMap

        The returned vector will contain this vectors contents and have meta
        attached."""
        return PersistentVector(meta, self._cnt, self._shift, self._root,
                                self._tail)

    def _tailoff(self):
        """Return the beginning index of the tail.

        This will be a multiple of 32, >= 0."""
        if self._cnt < 32:
            return 0
        return ((self._cnt - 1) >> 5) << 5

    def cons(self, val):
        """Return a new PersistentVector.

        val -- any object

        The returned vector contains all the items in this vector with val
        *appended*. It will also have this vector's meta data attached."""
        # there's room in the _tail for var
        if self._cnt - self._tailoff() < 32:
            newTail = self._tail[:]
            newTail.append(val)
            return PersistentVector(self.meta(), self._cnt + 1, self._shift,
                                    self._root, newTail)
        # _tail is full, have to create a new Node
        tailnode = Node(self._root._edit, self._tail)
        newshift = self._shift
        # no room at this level for the Node, add a new level
        if (self._cnt >> 5) > (1 << self._shift):
            newroot = Node(self._root._edit)
            newroot._array[0] = self._root
            newroot._array[1] = _newPath(self._root._edit, self._shift,
                                         tailnode)
            newshift += 5
        # room at this level for the new Node
        else:
            newroot = self._pushTail(self._shift, self._root, tailnode)

        return PersistentVector(self.meta(), self._cnt + 1, newshift, newroot,
                                [val])

    def _pushTail(self, level, parent, tailnode):
        """Add tailnode to the tree at the given level.

        level -- what level to push to, a multiple of 5, >= 5
        parent -- Node, the old root
        tailnode -- Node to push containing a full _array of the last 32 items
                    in the vector.

        Return the new root Node."""
        # the index of the next empty _array @ the given level
        subidx = ((self._cnt - 1) >> level) & 0x01f
        ret = Node(parent._edit, parent._array[:])

        if level == 5:
            nodeToInsert = tailnode
        else:
            child = parent._array[subidx]
            nodeToInsert = (self._pushTail(level - 5, child, tailnode)
                            if child is not None
                            else _newPath(self._root._edit, level - 5,
                                          tailnode))
        ret._array[subidx] = nodeToInsert
        return ret

    def empty(self):
        """Return an empty PersistentVector.

        The returned vector will have this vector's meta data attached."""
        return EMPTY.withMeta(self.meta())

    def pop(self):
        """Return a new PersistentVector.

        The returned vector will contain all the items it this vector except
        the *last* item. It will have this vector's meta data attached.

        Will raise IllegalStateException if this vector is empty."""
        if not self._cnt:
            raise IllegalStateException("Can't pop empty vector")
        if self._cnt == 1:
            return EMPTY.withMeta(self.meta())
        # pop from the _tail, done
        if self._cnt - self._tailoff() > 1:
            newTail = self._tail[:]
            newTail.pop()
            return PersistentVector(self.meta(), self._cnt - 1, self._shift,
                                    self._root, newTail)
        # the last sublist, post-pop
        newtail = self._arrayFor(self._cnt - 2)
        # pop from the last Node, done
        newroot = self._popTail(self._shift, self._root)
        newshift = self._shift
        if newroot is None:
            newroot = EMPTY_NODE
        if self._shift > 5 and newroot._array[1] is None:
            newroot = newroot._array[0]
            newshift -= 5
        return PersistentVector(self.meta(), self._cnt - 1, newshift, newroot,
                                newtail)

    def _popTail(self, level, node):
        """Return a new root Node or None if the last value was popped.

        level -- integer, 0 or a multiple of 5
        node -- Node to pop from

        Recursively descend the tree, starting at node and remove the value at
        _cnt - 1."""
        subidx = ((self._cnt - 2) >> level) & 0x01f
        if level > 5:
            newchild = self._popTail(level - 5, node._array[subidx])
            if newchild is None and not subidx:
                return None
            else:
                ret = Node(self._root._edit, node._array[:])
                ret._array[subidx] = newchild
                return ret
        elif not subidx:
            return None
        else:
            ret = Node(self._root._edit, node._array[:])
            ret._array[subidx] = None
            return ret

# ======================================================================
# PersistentVector Helpers
# ======================================================================

def _newPath(edit, level, node):
    """Return a Node.

    edit -- currently unused (for Clojure's transient data structures)
    level -- integer, multiple of 5, >= 5, stop recurring when 0
    node -- Node, the new path will lead *to* this node

    Called by PersistentVector.cons() (and indirectly by
    PersistentVector._pushTail()) when the leaves in the tree are full (a new
    level is required)."""
    if not level:
        return node
    ret = Node(edit)
    ret._array[0] = _newPath(edit, level - 5, node)
    return ret


def _doAssoc(level, node, i, val):
    """Return a new root Node with the item at index i set to val.

    level -- integer, multiple of 5, >== 5, stop recurring when 0
    node -- Node, the old root
    i -- integer >= 0, index of item to set
    val -- any object, the item to place at i"""
    ret = Node(node._edit, node._array[:])
    if not level:
        ret._array[i & 0x01f] = val
    else:
        subidx = (i >> level) & 0x01f
        ret._array[subidx] = _doAssoc(level - 5, node._array[subidx], i, val)
    return ret

# ======================================================================
# PersistentVector Tree Node
# ======================================================================

class Node(object):
    """A tree node in a PersistentVector."""
    def __init__(self, edit, array=None):
        """Instantiate a Node.

        edit -- currently unused (for Clojure's transient data structures)
        array -- An optional list of size 32. It will be initialized to [None]
                 * 32 if not supplied."""
        self._edit = edit
        self._array = array if array is not None else [None] * 32

# ======================================================================
# PersistentVector Creation
# ======================================================================

def vec(seq):
    """Return a PersistentVector.

    seq -- ISeq

    If seq is an APersistentVector return seq. Else the returned vector will
    contain the items in seq."""
    if isinstance(seq, APersistentVector):
        return seq
    s = RT.seq(seq)
    v = EMPTY
    while s is not None:
        v = v.cons(RT.first(s))
        s = RT.next(s)
    return v


def create(*args):
    """Return a PersistentVector.

    args -- zero or more objects

    The returned vector will contain all objects found in args."""
    x = EMPTY
    for z in args:
        x = x.cons(z)
    return x

# ======================================================================
# Pseudo-Singletons
# ======================================================================

# currently unused (for Clojure's transient data structures)
NOEDIT = AtomicReference()
# A Node holding no children or vector values
EMPTY_NODE = Node(NOEDIT)
# A PersistentVector containing 0 items
EMPTY = PersistentVector(0, 5, EMPTY_NODE, [])

########NEW FILE########
__FILENAME__ = protocol
from clojure.lang.namespace import Namespace
import clojure.lang.rt as RT

class ProtocolException(Exception):
    pass
    # def __init__(self, msg):
    #     Exception__init__(msg)



def getFuncName(protocol, funcname):
    return str(protocol) + funcname
    
class ProtocolFn(object):
    """Defines a function that dispatches on the type of the first argument
    passed to __call__"""
    
    def __init__(self, fname):
        self.dispatchTable = {}
        self.name = intern(fname)
        self.attrname = intern("__proto__" + self.name)
        self.default = None
        
    def extend(self, tp, fn):
           
        try:
            setattr(tp, self.attrname, fn)
        except:
            self.dispatchTable[tp] = fn
            
    def extendForTypes(self, tps, fn):
        for tp in tps:
            self.extend(tp, fn)
            
    def setDefault(self, fn):
        self.default = fn
            
    def isExtendedBy(self, tp):
        if hasattr(tp, self.attrname) or tp in self.dispatchTable:
            return True
        return False
        
           
    def __call__(self, *args):
        x = type(args[0])
        if hasattr(x, self.attrname):
            return getattr(x, self.attrname)(*args)
        else:
            # The table needs to be checked before the fn is called.
            #
            # If the following is used:
            #
            # try:
            #     return self.dispatchTable[x](*args)
            # except
            #     if self.default:
            #         return self.default(*args)
            #     raise
            #
            # the dispatched fn may raise (even a KeyError). That exception
            # will get silently swallowed and the default fn will get called.
            # I believe the following will handle this, but it will also
            # affect performance.
            fn = self.dispatchTable.get(x)
            if fn:
                # let any fn exceptions propogate
                return fn(*args)
            else:
                # now try the default and raise a specific exception
                if self.default:
                    # let any default fn exceptions propogate
                    return self.default(*args)
                raise ProtocolException("{0} not extended to handle: {1}"
                                        .format(self.name, x))

            
    def __repr__(self):
        return "ProtocolFn<" + self.name + ">"
        
    
    
class Protocol(object):
    def __init__(self, ns, name, fns):
        """Defines a protocol in the given ns with the given name and functions"""
        self.ns = ns
        self.name = name
        self.fns = fns
        self.protofns = registerFns(ns, fns)
        self.__name__ = name
        self.implementors = set()
        
    def markImplementor(self, tp):
        if tp in self.implementors:
            return
            
        self.implementors.add(tp)
        
    def extendForType(self, tp, mp):
        """Extends this protocol for the given type and the given map of methods
           mp should be a map of methodnames: functions"""
       
        for x in mp:
            name =  RT.name(x.sym)
            if name not in self.protofns:
                raise ProtocolException("No Method found for name " + x)
            
            fn = self.protofns[name]
            fn.extend(tp, mp[x])

        self.markImplementor(tp)
                
    def isExtendedBy(self, tp):
        return tp in self.implementors
        
    def __repr__(self):
        return "Protocol<" + self.name + ">"
        
        
        
def registerFns(ns, fns):
    ns = Namespace(ns)
    protofns = {}
    for fn in fns:
        fname = ns.__name__ + fn
        if hasattr(ns, fn):
            proto = getattr(ns, fn)
        else:
            proto = ProtocolFn(fname)
            setattr(ns, fn, proto)
        proto.__name__ = fn
        protofns[fn] = proto
        
    return protofns
    
def extend(np, *args):
    for x in range(0, len(args), 2):
        tp = args[x]
        proto = getExactProtocol(tp)
        if not proto:
            raise ProtocolExeception("Expected protocol, got {0}".format(x))
        if x + 1 >= len(args):
            raise ProtocolExeception("Expected even number of forms to extend")
        
        proto.extendForType(np, args[x + 1])
        
                
        
        
def getExactProtocol(tp):
    if hasattr(tp, "__exactprotocol__") \
       and hasattr(tp, "__exactprotocolclass__") \
       and tp.__exactprotocolclass__ is tp:
           return tp.__exactprotocol__
    return None
        
def protocolFromType(ns, tp):
    """Considers the input type to be a prototype for a protocol. Useful for
    turning abstract classes into protocols"""
    fns = []    
    for x in dir(tp):
        if not x.startswith("_"):
            fns.append(x)
            

        
    thens = Namespace(ns)
    proto = Protocol(ns, tp.__name__, fns)
    
    tp.__exactprotocol__ = proto
    tp.__exactprotocolclass__ = tp
    
    if not hasattr(tp, "__protocols__"):
        tp.__protocols__ = []
    tp.__protocols__.append(proto)
    
    if not hasattr(thens, tp.__name__):
        setattr(thens, tp.__name__, proto)
    return proto
    
def extendForAllSubclasses(tp):
    if not hasattr(tp, "__protocols__"):
        return
    
    for proto in tp.__protocols__:
        _extendProtocolForAllSubclasses(proto, tp)
        
def _extendProtocolForAllSubclasses(proto, tp):
    extendProtocolForClass(proto, tp)
    
    for x in tp.__subclasses__():
        _extendProtocolForAllSubclasses(proto, x)
    

def extendForType(interface, tp):
    if not hasattr(interface, "__protocols__"):
        return
    
    for proto in interface.__protocols__:
        extendProtocolForClass(proto, tp)

def extendProtocolForClass(proto, tp):
    for fn in proto.protofns:
        
        pfn = proto.protofns[fn]
        if hasattr(tp, fn):
            try:
                pfn.extend(tp, getattr(tp, fn))
            except AttributeError as e:
                print "Can't extend, got {0}".format(pfn), type(pfn)
                raise
        
    proto.markImplementor(tp)


########NEW FILE########
__FILENAME__ = pytypes
"""pytypes.py

Saturday, March 24 2012
"""

import re                       # for compiled regex type
import sys                      # for file type
import types                    # for generators, etc.

pyObjectType = type(object())
pyRegexType = type(re.compile(""))
pyFuncType = type(lambda x : x)
pyListType = type([])
pySetType = type(set())
pyTupleType = type(())
pyDictType = type({})
pyStrType = type("")
pyUnicodeType = type(u"")
pyNoneType = type(None)
pyBoolType = type(True)
pyIntType = type(int())
pyLongType = type(long())
pyFloatType = type(float())
pyFileType = type(sys.stdin)
pyTypeType = type
pyTypeCode = types.CodeType
pyTypeGenerator = types.GeneratorType
pyClassType = types.ClassType
pyReversedType = reversed

# add more if needed

########NEW FILE########
__FILENAME__ = ref
from aref import ARef
from cljexceptions import IllegalStateException
from threadutil import AtomicInteger
from clojure.util.shared_lock import SharedLock
from clojure.lang.util import TVal
from lockingtransaction import LockingTransaction

import clojure.lang.rt as RT

from itertools import count
from time import time

# NOTE only thread-safe in cPython
refids = count()

class Ref(ARef):

    def __init__(self, state, meta=None):
        super(Ref, self).__init__(meta)
        self._id         = refids.next()
        self._faults     = AtomicInteger(0)
        self._tinfo      = None
        self._maxHistory = 10
        self._minHistory = 0
        # NOTE SharedLock is also re-entrant.
        self._lock       = SharedLock(None, False)
        self._tvals      = TVal(state, 0, time() * 1000)

    def _currentVal(self):
        """Returns the current value of the ref. Safe to be called
        from outside an active transaction"""
        self._lock.acquire_shared()
        try:
            if self._tvals:
                return self._tvals.val
            raise IllegalStateException("Accessing unbound ref in currentVal!")
        finally:
            self._lock.release_shared()

    def deref(self):
        """Returns either the in-transaction-value of this ref if
        there is an active transaction, or returns the last committed
        value of ref"""
        transaction = LockingTransaction.get()
        if transaction:
            return transaction.getRef(self)
        return self._currentVal()

    def refSet(self, state):
        """Sets the value of this ref to the desired state, regardless
        of the current value. Returns the newly set state"""
        return LockingTransaction.ensureGet().doSet(self, state)

    def alter(self, fn, args):
        "Alters the value of this ref, and returns the new state"
        current = LockingTransaction.ensureGet().getRef(self)
        return self.refSet(fn(*RT.cons(current, args)))

    def commute(self, fn, args):
        """Commutes the value of this ref, allowing for it to be
        updated by other transactions before the commuting function is
        called"""
        return LockingTransaction.ensureGet().doCommute(self, fn, args)

    def touch(self):
        """Ensures that this ref cannot be given a new
        in-transaction-value by any other transactions for the
        duration of this transaction"""
        LockingTransaction.ensureGet().doEnsure(self)

    def isBound(self):
        """Returns whether or not this reference has had at least one
        TVal in the history chain set"""
        try:
            self._lock.acquire_shared()
            return self._tvals != None
        finally:
            self._lock.release_shared()

    def trimHistory(self):
        "Shortens the tvals history chain to the newest-item only"
        try:
            self._lock.acquire()
            if self._tvals != None:
                self._tvals.next = self._tvals
                self._tvals.prev = self._tvals
        finally:
            self._lock.release()

    def _historyCount(self):
        "Internal history length counter. Read lock must be acquired"
        if self._tvals == None:
            return 0
        count = 1
        tval = self._tvals.next
        while tval != self._tvals:
            count += 1
            tval = tval.next
        return count

    def historyCount(self):
        """Return the length of the tvals history chain. Requires a
        traversal and a read lock"""
        try:
            self._lock.acquire_shared()
            return self._historyCount()
        finally:
            self._lock.release_shared()

    def minHistory(self):
        "Returns the minimum history length for this ref"
        return self._minHistory

    def setMinHistory(self, minHistory):
        "Sets the minimum history chain length for this reference"
        self._minHistory = minHistory

    def maxHistory(self):
        "Returns the maximum history length for this ref"
        return self._maxHistory

    def setMaxHistory(self, maxhistory):
        "Sets the maximum history chain length for this reference"
        self._maxHistory = maxHistory

########NEW FILE########
__FILENAME__ = reversible
from clojure.lang.cljexceptions import AbstractMethodCall


class Reversible(object):
    def rseq(self):
        raise AbstractMethodCall(self)

########NEW FILE########
__FILENAME__ = rt
import re
import sys

from clojure.lang.ipersistentvector import IPersistentVector
from clojure.lang.cljexceptions import InvalidArgumentException
from clojure.lang.comparator import Comparator
from clojure.lang.threadutil import AtomicInteger
from clojure.lang.iseq import ISeq
# I don't like * either, but this should be fine
from pytypes import *


mapInter = map
_list = list


def setMeta(f, meta):
    setattr(f, "meta", lambda: meta)
    return f


def cons(x, s):
    from clojure.lang.cons import Cons
    from clojure.lang.persistentlist import EMPTY as EMPTY_LIST
    if isinstance(s, ISeq):
        return Cons(x, s)
    if s is None:
        return EMPTY_LIST.cons(x)
    return Cons(x, seq(s))


def seqToTuple(s):
    if s is None:
        return ()
    if isinstance(s, tuple):
        return s
    if isinstance(s, IPersistentVector):
        return tuple(s)
    return tuple(s)


class NotSeq(object):
    pass


#def seq(obj):
#    from clojure.lang.indexableseq import IndexableSeq
#    from clojure.lang.symbol import Symbol
#    from clojure.lang.aseq import ASeq

#    if isinstance(obj, Symbol):
#        pass
#    if obj is None:
#        return None
#    if isinstance(obj, ASeq):
#        return obj
#    if isinstance(obj, (tuple, _list, str)):
#        if len(obj) == 0:
#            return None
#        return IndexableSeq(obj, 0)

#    if hasattr(obj, "seq"):
#        return obj.seq()
#    return NotSeq()


    
def first(obj):
    return protocols.first(seq(obj))
        
def next(obj):
    return protocols.next(seq(obj))
    
def isSeqable(obj):
    return protocols.seq.isExtendedBy(type(obj))

def applyTo(fn, args):
    return apply(fn, tuple(map(lambda x: x.first(), args)))


def booleanCast(obj):
    if isinstance(obj, bool):
        return obj
    return obj is None


def keys(obj):
    from clojure.lang.apersistentmap import createKeySeq
    return createKeySeq(obj)


def vals(obj):
    from clojure.lang.apersistentmap import createValueSeq
    return createValueSeq(obj)


def fulfillsHashSet(obj):
    if not hasattr(obj, "__getitem__"):
        return False
    if not hasattr(obj, "__iter__"):
        return False
    if not hasattr(obj, "__contains__"):
        return False
    return True


def fulfillsIndexable(obj):
    if not hasattr(obj, "__getitem__"):
        return False
    if not hasattr(obj, "__len__"):
        return False
    return True


def list(*args):
    from clojure.lang.persistentlist import EMPTY
    c = EMPTY
    for x in range(len(args) - 1, -1, -1):
        c = c.cons(args[x])
    return c


def vector(*args):
    from clojure.lang.persistentvector import EMPTY
    c = EMPTY
    for x in args:
        c = c.cons(x)
    return c


def map(*args):
    from clojure.lang.persistenthashmap import EMPTY
    if len(args) == 0:
        return EMPTY
    if len(args) == 1:
        if isinstance(args[0], dict):
            m = EMPTY
            for x in args[0]:
                if x in m:
                    raise InvalidArgumentException("Duplicate key")
                m = m.assoc(x, args[0][x])
            return m
        if fulfillsIndexable(args[0]):
            args = args[0]
    m = EMPTY
    for x in range(0, len(args), 2):
        key = args[x]
        value = args[x + 1]
        m = m.assoc(key, value)
    return m

def set(*args):
    from clojure.lang.persistenthashset import EMPTY
    if len(args) == 0:
        return EMPTY
    if len(args) == 1:
        if isinstance(args[0], dict):
            m = EMPTY
            for x in args[0]:
                if x in m:
                    raise InvalidArgumentException("Duplicate key")
                m.impl = m.impl.assoc(x, args[0][x])
            return m
        if fulfillsIndexable(args[0]):
            args = args[0]
    m = EMPTY
    for x in range(0, len(args), 2):
        key = args[x]
        value = args[x + 1]
        m.impl = m.impl.assoc(key, value)
    return m


# need id for print protocol
_id = AtomicInteger()


def nextID():
    return _id.getAndIncrement()


def subvec(v, start, end):
    from clojure.lang.persistentvector import EMPTY as EMPTY_VECTOR
    from clojure.lang.apersistentvector import SubVec
    if end < start or start < 0 or end > len(v):
        raise Exception("Index out of range")
    if start == end:
        return EMPTY_VECTOR
    return SubVec(None, v, start, end)


stringEscapeMap = {
    "\a" : "<???>",                  # XXX
    "\b" : "\\b",
    "\f" : "\\f",
    "\n" : "\\n",
    "\r" : "\\r",
    "\t" : "\\t",
    "\v" : "<???>",                  # XXX
    "\\" : "\\\\",
    '"' : '\\\"'
    }

def stringEscape(s):
    return "".join([stringEscapeMap.get(c, c) for c in s])


def _extendIPrintableForManuals():

    # Any added writeAsReplString handlers need
    # to write the unreadable syntax:
    # #<foo>
    # if lispreader cannot recognize it.

    # None
    protocols.writeAsString.extend(
        pyNoneType,
        lambda obj, writer: writer.write("nil"))
    protocols.writeAsReplString.extend(
        pyNoneType,
        lambda obj, writer: writer.write("nil"))
    # True, False
    protocols.writeAsString.extend(
        pyBoolType,
        lambda obj, writer: writer.write(obj and "true" or "false"))
    protocols.writeAsReplString.extend(
        pyBoolType,
        lambda obj, writer: writer.write(obj and "true" or "false"))
    # int, long
    protocols.writeAsString.extendForTypes(
        [pyIntType, pyLongType],
        lambda obj, writer: writer.write(str(obj)))
    protocols.writeAsReplString.extendForTypes(
        [pyIntType, pyLongType],
        lambda obj, writer: writer.write(str(obj)))
    # float separate to allow for possible precision state
    protocols.writeAsString.extend(
        pyFloatType,
        lambda obj, writer: writer.write(str(obj)))
    protocols.writeAsReplString.extend(
        pyFloatType,
        lambda obj, writer: writer.write(str(obj)))
    # str
    protocols.writeAsString.extend(
        pyStrType,
        lambda obj, writer: writer.write(obj))
    protocols.writeAsReplString.extend(
        pyStrType,
        # XXX: Will not correctly escape Python strings because clojure-py
        #      will currently only read Clojure-compliant literal strings.
        lambda obj, writer: writer.write('"{0}"'.format(stringEscape(obj))))
    # unicode
    protocols.writeAsString.extend(
        pyUnicodeType,
        lambda obj, writer: writer.write(obj.encode("utf-8")))
    protocols.writeAsReplString.extend(
        pyUnicodeType,
        lambda obj, writer: writer.write(u'"{0}"'.format(stringEscape(obj))
                                         .encode("utf-8")))
    # regex
    protocols.writeAsString.extend(
        pyRegexType,
        lambda obj, writer:   # not sure about this one
            writer.write(u'#"{0}"'.format(stringEscape(obj.pattern))
                         .encode("utf-8")))
    protocols.writeAsReplString.extend(
        pyRegexType,
        lambda obj, writer:
            writer.write(u'#"{0}"'.format(stringEscape(obj.pattern))
                         .encode("utf-8")))
    # tuple, list, dict, and set
    # This is the same as default below, but maybe these will be handled
    # specially at some point.
    protocols.writeAsString.extendForTypes(
        [pyTupleType, pyListType, pyDictType, pySetType],
        lambda obj, writer: writer.write(repr(obj)))
    protocols.writeAsReplString.extendForTypes(
        [pyTupleType, pyListType, pyDictType, pySetType],
        # possibly print a preview of the collection:
        # #<__builtin__.dict obj at 0xdeadbeef {'one': 1, 'two': 2 ... >
        lambda obj, writer:
            writer.write('#<{0}.{1} object at 0x{2:x}>'
                         .format(type(obj).__module__, type(obj).__name__,
                                 id(obj))))
    # type
    # #<fully.qualified.name> or fully.qualified.name ?
    protocols.writeAsString.extend(
        pyTypeType,
        lambda obj, writer:
            writer.write('#<{0}.{1}>'.format(obj.__module__, obj.__name__)))
    protocols.writeAsReplString.extend(
        pyTypeType,
        lambda obj, writer:
            writer.write('#<{0}.{1}>'.format(obj.__module__, obj.__name__)))
    # function
    # #<function name at 0x21d20c8>
    protocols.writeAsString.extend(
        pyFuncType,
        lambda obj, writer: writer.write('#{0}'.format(obj)))
    protocols.writeAsReplString.extend(
        pyFuncType,
        lambda obj, writer: writer.write('#{0!r}'.format(obj)))
    # default
    # This *should* allow pr and family to handle anything not specified
    # above.
    protocols.writeAsString.setDefault(
        # repr or str here?
        lambda obj, writer: writer.write(str(obj)))
    protocols.writeAsReplString.setDefault(
        lambda obj, writer:
            writer.write('#<{0}.{1} object at 0x{2:x}>'
                         .format(type(obj).__module__, type(obj).__name__,
                                 id(obj))))

# this is only for the current Python-coded repl
def printTo(obj, writer=sys.stdout):
    protocols.writeAsReplString(obj, writer)
    writer.write("\n")
    writer.flush()

def _extendSeqableForManuals():
    from clojure.lang.indexableseq import create as createIndexableSeq
    
    protocols.seq.extendForTypes(
        [pyTupleType, pyListType, pyStrType, pyUnicodeType],
        lambda obj: createIndexableSeq(obj))
    protocols.seq.extend(type(None), lambda x: None)
    
    #protocols.seq.setDefault(lambda x: NotSeq())

def _bootstrap_protocols():
    global protocols, seq
    from clojure.lang.iseq import ISeq as iseq
    from clojure.lang.iprintable import IPrintable
    from clojure.lang.named import Named
    from clojure.lang.protocol import protocolFromType, extendForAllSubclasses
    from clojure.lang.seqable import Seqable as seqable

    protocolFromType("clojure.protocols", IPrintable)
    extendForAllSubclasses(IPrintable)

    protocolFromType("clojure.protocols", seqable)
    extendForAllSubclasses(seqable)
    
    protocolFromType("clojure.protocols", iseq)
    extendForAllSubclasses(iseq)
    protocols = sys.modules["clojure.protocols"]
    seq = protocols.seq
    _extendSeqableForManuals()
    _extendIPrintableForManuals()
    
    protocolFromType("clojure.protocols", Named)
    extendForAllSubclasses(Named)
    global name, namespace
    
    name = protocols.getName
    namespace = protocols.getNamespace
    _extendNamedForManuals()
    
def _extendNamedForManuals():
	protocols.getName.extendForTypes([pyStrType, pyUnicodeType], lambda x: x)
	protocols.getName.extend(pyTypeType, lambda x: x.__name__)
	
	protocols.getNamespace.extend(pyTypeType, lambda x: x.__module__)

# init is being called each time a .clj is loaded
initialized = False
def init():
    global initialized
    if not initialized:
        _bootstrap_protocols()
        initialized = True


class DefaultComparator(Comparator):
    def compare(self, k1, k2):
        if k1 == k2:
            return 0
        elif k1 < k2:
            return -1
        else:
            return 1

########NEW FILE########
__FILENAME__ = seqable
from clojure.lang.cljexceptions import AbstractMethodCall


class Seqable(object):
    def seq(self):
        raise AbstractMethodCall(self)

########NEW FILE########
__FILENAME__ = sequential
class Sequential(object):
    pass

########NEW FILE########
__FILENAME__ = settable
from clojure.lang.cljexceptions import AbstractMethodCall


class Settable(object):
    def doSet(self, o):
        raise AbstractMethodCall(self)

    def doReset(self, o):
        raise AbstractMethodCall(self)

########NEW FILE########
__FILENAME__ = symbol
from clojure.lang.iprintable import IPrintable
from clojure.lang.iobj import IObj
from clojure.lang.cljexceptions import ArityException
from clojure.lang.named import Named


class Symbol(IObj, IPrintable, Named):
    def __init__(self, *args):
        """Symbol initializer.
        
        Valid calls:
        - Symbol(symbol) -- copy,
        - Symbol([[mapping,] str,], str) -- metadata, namespace, name.
        """
        if len(args) == 1:
            arg = args[0]
            if isinstance(arg, Symbol):
                self._meta, self.ns, self.name = arg._meta, arg.ns, arg.name
            else:
                self._meta = None
                idx = arg.rfind("/")
                if idx == -1 or arg == "/":
                    self.ns = None
                    self.name = arg
                else:
                    self.ns = arg[:idx]
                    self.name = arg[idx + 1:]
        elif len(args) == 2:
            self._meta = None
            self.ns, self.name = args
        elif len(args) == 3:
            self._meta, self.ns, self.name = args
        else:
            raise ArityException()

    def getNamespace(self):
        return self.ns

    def getName(self):
        return self.name

    def withMeta(self, meta):
        if meta is self.meta():
            return self
        return Symbol(meta, self.ns, self.name)

    def meta(self):
        return self._meta

    def __eq__(self, other):
        if self is other:
            return True
        if not isinstance(other, Symbol):
            return False
        return (self.ns == other.ns) and (self.name == other.name)

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return hash(self.name) ^ hash(self.ns)

    def writeAsString(self, writer):
        writer.write(repr(self))

    def writeAsReplString(self, writer):
        writer.write(repr(self))

    def __repr__(self):
        if self.ns is None:
            return self.name
        else:
            return self.ns + "/" + self.name

########NEW FILE########
__FILENAME__ = threadutil
from threading import Lock, local, currentThread

from clojure.util.shared_lock import SharedLock, shared_lock, unique_lock

def synchronized(f):
    """ Synchronization decorator. """
    lock = Lock()

    def synchronized_closure(*args, **kw):
        lock.acquire()
        try:
            return f(*args, **kw)
        finally:
            lock.release()
    return synchronized_closure


class ThreadLocal(local):
    def __init__(self):
        pass

    def get(self, defaultfn):
        if not hasattr(self, "value"):
            self.value = defaultfn()
        return self.value

    def set(self, value):
        self.value = value


class AtomicInteger(object):
    def __init__(self, v=0):
        self._v = v
        self._lock = SharedLock()

    def get(self):
        with shared_lock(self._lock): return self._v

    def set(self, v):
        with unique_lock(self._lock): self._v = v

    def getAndIncrement(self):
        with unique_lock(self._lock):
            self._v += 1
            return self._v

    def compareAndSet(self, expected, update):
        with unique_lock(self._lock):
            if self._v == expected:
                self._v = update
                return True
            else:
                return False

########NEW FILE########
__FILENAME__ = util
from clojure.lang.cljexceptions import (AbstractMethodCall,
                                        InvalidArgumentException)
from clojure.lang.mapentry import MapEntry
import clojure.lang.rt as RT

# Needed by both ref.py and lockingtransaction, so they can't depend on each other
class TVal:
    def __init__(self, val, point, msecs, prev = None):
        self.val = val
        self.point = point
        self.msecs = msecs

        # If we are passed prev, add ourselves to the end of the linked list
        if prev:
            self.prev = prev
            self.next = prev.next
            self.prev.next = self
            self.next.prev = self
        else:
            self.prev = self
            self.next = self

def hashCombine(hash, seed): # FIXME - unused argument?
    seed ^= seed + 0x9e3779b9 + (seed << 6) + (seed >> 2)
    return seed

def hasheq(o):
    raise AbstractMethodCall()

def conjToAssoc(self, o):
    if isinstance(o, MapEntry):
        return self.assoc(o.getKey(), o.getValue())
    if hasattr(o, "__getitem__") and hasattr(o, "__len__"):
        if len(o) != 2:
            raise InvalidArgumentException("Vector arg must be a pair")
        return self.assoc(o[0], o[1])

    s = RT.seq(o)
    map = self
    for s in s.interator():
        m = s.first()
        map = map.assoc(m.getKey(), m.getValue())
    return map


def bitCount(i):
    i -= ((i >> 1) & 0x55555555)
    i = (i & 0x33333333) + ((i >> 2) & 0x33333333)
    return (((i + (i >> 4)) & 0x0F0F0F0F) * 0x01010101) >> 24


def arrayCopy(src, srcPos, dest, destPos, length):
    dest[destPos:length] = src[srcPos:length]

########NEW FILE########
__FILENAME__ = var
import contextlib

from clojure.lang.aref import ARef
from clojure.lang.atomicreference import AtomicReference
from clojure.lang.cljexceptions import (ArityException,
                                        IllegalStateException)
from clojure.lang.cljkeyword import Keyword
from clojure.lang.ifn import IFn
from clojure.lang.iprintable import IPrintable
from clojure.lang.persistenthashmap import EMPTY
from clojure.lang.persistentarraymap import create
from clojure.lang.settable import Settable
from clojure.lang.symbol import Symbol
from clojure.lang.threadutil import ThreadLocal, currentThread

privateKey = Keyword("private")
macrokey = Keyword("macro")
STATIC_KEY = Keyword("static")
dvals = ThreadLocal()
privateMeta = create([privateKey, True])
UNKNOWN = Symbol("UNKNOWN")


class Var(ARef, Settable, IFn, IPrintable):
    def __init__(self, *args):
        """Var initializer

        Valid calls:
        - Var(namespace, symbol, root)
        - Var(namespace, symbol) -- unbound Var
        - Var(root) -- anonymous Var
        - Var() -- anonymous, unbound Var
        """
        self.ns = args[0] if len(args) >= 2 else None
        self.sym = args[1] if len(args) >= 2 else None
        root = args[-1] if len(args) % 2 else UNKNOWN
        self.root = AtomicReference(root if root != UNKNOWN else Unbound(self))
        self.threadBound = False
        self._meta = EMPTY
        self.dynamic = False
        self.public = True

    def setDynamic(self, val=True):
        self.dynamic = val
        return self

    def isDynamic(self):
        return self.dynamic
        
    def setPublic(self, public = True):
        self.public = public
        
    def isPublic(self):
        return self.public
        
    def isBound(self):
        return self.getThreadBinding() is not None \
                or not isinstance(self.root.get(), Unbound)

    def set(self, val):
        self.validate(self.getValidator(), val)
        b = self.getThreadBinding()
        if b is not None:
            if currentThread() != b.thread:
                raise IllegalStateException(
                    "Can't set!: {0} from non-binding thread".format(self.sym))
            b.val = val
            return self

        raise IllegalStateException(
            "Can't change/establish root binding of: {0} with set".
            format(self.sym))
        
    def alterRoot(self, fn, args):
        return self.root.mutate(lambda old: fn(old, *(args if args else ())))

    def hasRoot(self):
        return not isinstance(self.root.get(), Unbound)

    def bindRoot(self, root):
        self.validate(self.getValidator(), root)
        self.root.set(root)
        return self

    def __call__(self, *args, **kw):
        """Exists for Python interop, don't use in clojure code"""
        return self.deref()(*args, **kw)

    def deref(self):
        b = self.getThreadBinding()
        if b is not None:
            return b.val
        return self.root.get()

    def getThreadBinding(self):
        if self.threadBound:
            e = dvals.get(Frame).bindings.entryAt(self)
            if e is not None:
                return e.getValue()
        return None

    def setMeta(self, meta):
        self._meta = meta
        if self._meta and self._meta[STATIC_KEY]:
            self.setDynamic(False)
        return self

    def setMacro(self):
        self.alterMeta(lambda x, y, z: x.assoc(y, z), macrokey, True)

    def writeAsString(self, writer):
        writer.write(repr(self))

    def writeAsReplString(self, writer):
        writer.write(repr(self))

    def __repr__(self):
        if self.ns is not None:
            return "#'{0}/{1}".format(self.ns.__name__, self.sym)
        return "#<Var: {0}>".format(self.sym or "--unnamed--")


class TBox(object):
    def __init__(self, thread, val):
        self.thread = thread
        self.val = val


class Unbound(IFn):
    def __init__(self, v):
        self.v = v

    def __repr__(self):
        return "Unbound {0}".format(self.v)

    def __call__(self, *args, **kwargs):
        raise ArityException(
            "Attempting to call unbound fn: {0}".format(self.v))


class Frame(object):
    def __init__(self, bindings=EMPTY, prev=None):
        self.bindings = bindings
        self.prev = prev

    def clone(self):
        return Frame(self.bindings)


def pushThreadBindings(bindings):
    f = dvals.get(Frame)
    bmap = f.bindings
    for v in bindings:
        value = bindings[v]
        if not v.dynamic:
            raise IllegalStateException(
                "Can't dynamically bind non-dynamic var: {0}/{1}".
                format(v.ns, v.sym))
        v.validate(v.getValidator(), value)
        v.threadBound = True
        bmap = bmap.assoc(v, TBox(currentThread(), value))
    dvals.set(Frame(bmap, f))


def popThreadBindings():
    f = dvals.get(Frame)
    if f.prev is None:
        raise IllegalStateException("Pop without matching push")
    dvals.set(f.prev)


@contextlib.contextmanager
def threadBindings(bindings):
    pushThreadBindings(bindings)
    try:
        yield
    finally:
        popThreadBindings()


def getThreadBindingFrame():
    f = dvals.get(Frame)
    return f


def cloneThreadBindingFrame():
    f = dvals.get(Frame).clone()
    return f


def resetThreadBindingFrame(val):
    dvals.set(val)


########NEW FILE########
__FILENAME__ = main
#!/usr/bin/env python
"""Main entry point to clojure-py: sets import hook, import clojure.core and
define main().
"""

import cPickle
import imp
from optparse import OptionParser
import os.path
import sys
import traceback

from clojure.lang.cljexceptions import NoNamespaceException
from clojure.lang.compiler import Compiler
from clojure.lang.fileseq import StringReader
from clojure.lang.globals import currentCompiler
from clojure.lang.lispreader import read
from clojure.lang.namespace import Namespace, findItem
import clojure.lang.rt as RT
from clojure.lang.symbol import Symbol
from clojure.lang.var import threadBindings


VERSION = "0.2.4"
VERSION_MSG = "clojure-py {0}\nPython {1}".format(VERSION, sys.version)


class MetaImporter(object):
    """A PEP302 import hook for clj files.
    """

    def find_module(self, fullname, path=None):
        """Finds a clj file if there is no package with the same name.
        """
        lastname = fullname.rsplit(".", 1)[-1]
        for d in path or sys.path:
            clj = os.path.join(d, lastname + ".clj")
            pkg = os.path.join(d, lastname, "__init__.py")
            pkgc = getattr(imp, "cache_from_source",
                           lambda path: path + "c")(pkg)
            if (os.path.exists(clj) and
                not (os.path.exists(pkg) or os.path.exists(pkgc))):
                self.path = clj
                return self
        return None

    def load_module(self, name):
        """Loads a clj file, returns the corresponding namespace if it exists.
        
        If the file did not create the corresponding namespace,
        NoNamespaceException (a subclass of ImportError) is raised.
        """
        if name not in sys.modules:
            sys.modules[name] = None # avoids circular imports
            try:
                requireClj(self.path)
            except Exception as exc:
                del sys.modules[name]
                traceback.print_exc()
                raise ImportError("requireClj raised an exception.")
            if sys.modules[name] == None:
                del sys.modules[name]
                raise NoNamespaceException(self.path, name)
            sys.modules[name].__loader__ = self
        return sys.modules[name]

    def is_package(self, name):
        return False


sys.meta_path.append(MetaImporter())
# "" is the directory where the script is run, not the one where it is
# installed.
sys.path.insert(0, "")


def requireClj(filename, stopafter=None):
    """Compiles and executes the code in a clj file.
    
    If `stopafter` is given, then stop execution as soon as the `stopafter`
    name is defined in the current namespace of the compiler.
    """
    with open(filename) as fl:
        r = StringReader(fl.read())

    RT.init()
    comp = Compiler()
    comp.setFile(filename)

    with threadBindings({currentCompiler: comp}): #, open(filename + ".cljc", "w") as o:
        try:
            while True:
                EOF = object()
                s = read(r, False, EOF, True)
                if s is EOF:
                    break
                #cPickle.dump(s, o)
                try:
                    res = comp.compile(s)
                    comp.executeCode(res)
                    if stopafter is not None and hasattr(comp.getNS(), stopafter):
                        break
                except Exception as exp:
                    print s, filename
                    raise
        except IOError as e:
            pass


def main():
    """Main entry point to clojure-py.
    """

    def gobble(option, opt_str, value, parser):
        """Interprets all the remaining arguments as a single argument.
        """
        setattr(parser.values, option.dest, " ".join(parser.rargs))
        del parser.rargs[:]

    parser = OptionParser(
        usage="%prog [options] ... [-c cmd | file | -] [arg] ...",
        version=VERSION_MSG)
    parser.add_option("-c",
        action="callback", dest="cmd", default="", callback=gobble,
        help="program passed in as a string (terminates option list)")
    parser.add_option("-i", action="store_true", dest="interactive",
        help="inspect interactively after running script")
    parser.add_option("-q", action="store_true", dest="quiet",
        help="don't print version message on interactive startup")
    # fooling OptionParser
    parser.add_option("--\b\bfile", action="store_true",
        help="    program read from script file")
    parser.add_option("--\b\b-", action="store_true",
        help="    program read from stdin (default; interactive mode if a tty)")
    parser.add_option("--\b\barg ...", action="store_true",
        help="    arguments passed to program in *command-line-args*")
    args = sys.argv[1:]
    try:
        i = args.index("-")
    except ValueError:
        i = len(args)
    dash_and_post = args[i:]
    opts, command_line_args = parser.parse_args(args[:i])
    source = command_line_args.pop(0) if command_line_args else None
    command_line_args.extend(dash_and_post)
    opts.command_line_args = command_line_args

    RT.init()
    comp = Compiler()

    command_line_args_sym = findItem(Namespace("clojure.core"),
                                     Symbol("*command-line-args*"))
    with threadBindings({currentCompiler: comp,
                         command_line_args_sym: command_line_args}):
        if source:
            requireClj(source)
        if opts.interactive or not source and not opts.cmd:
            import clojure.repl
            clojure.repl.enable_readline()
            clojure.repl.run_repl(opts, comp)


if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = repl
"""Contains enhancements to the REPL that do not belong in the core language.
"""

import atexit
import os
import sys
import traceback

from clojure.lang.compiler import Compiler
from clojure.lang.fileseq import StringReader
from clojure.lang.globals import currentCompiler
from clojure.lang.lispreader import read
from clojure.lang.namespace import Namespace, findItem
from clojure.lang.symbol import Symbol
from clojure.lang.var import Var
import clojure.lang.rt as RT
from clojure.main import VERSION_MSG


def enable_readline():
    """Imports the `readline` module to enable advanced REPL text manipulation
    and command history navigation.

    Returns True on success, otherwise False.
    """
    try:
        import readline
    except ImportError:
        return False

    histfile = os.path.join(os.path.expanduser("~"), ".clojurepyhist")
    if not os.path.isfile(histfile):
        with open(histfile, 'a'):
            os.utime(histfile, None)
        os.chmod(histfile, int('640', 8))
    try:
        readline.read_history_file(histfile)
    except IOError:
        # Pass here as there isn't any history file, so one will be
        # written by atexit
        pass
    atexit.register(readline.write_history_file, histfile)
    return True


def run_repl(opts, comp=None):
    """Initializes and runs the REPL. Assumes that RT.init has been called.

    Repeatedly reads well-formed forms from stdin (with an interactive prompt
    if a tty) and evaluates them (and prints the result if a tty). Exits on
    EOF.
    """
    if not opts.quiet and os.isatty(0):
        print VERSION_MSG

    if comp is None:
        curr = currentCompiler.get(lambda: None)
        if curr == None:
            comp = Compiler()
            currentCompiler.set(comp)
        else:
            comp = curr
    comp.setNS(Symbol("user"))
    core = sys.modules["clojure.core"]
    for i in dir(core):
        if not i.startswith("_"):
            setattr(comp.getNS(), i, getattr(core, i))

    line = opts.cmd
    last3 = [None, None, None]

    def firstLinePrompt():
        return comp.getNS().__name__ + "=> " if os.isatty(0) else ""

    def continuationLinePrompt():
        return "." * len(comp.getNS().__name__) + ".. " if os.isatty(0) else ""

    while True:
        # Evaluating before prompting caters for initially given forms.
        r = StringReader(line)
        while True:
            try:
                s = read(r, False, None, True)
                if s is None:
                    break
                res = comp.compile(s)
                out = comp.executeCode(res)
            except Exception:
                traceback.print_exc()
            else:
                if os.isatty(0):
                    RT.printTo(out)
                last3.pop()
                last3.insert(0, out)
                for i, value in enumerate(last3, 1):
                    v = findItem(Namespace("clojure.core"),
                                 Symbol("*{0}".format(i)))
                    if isinstance(value, Var):
                        v.bindRoot(value.deref())
                        v.setMeta(value.meta())
                    else:
                        v.bindRoot(value)
        try:
            line = raw_input(firstLinePrompt())
            while unbalanced(line):
                line += "\n" + raw_input(continuationLinePrompt())
        except BracketsException as exc:
            print exc
            continue
        except EOFError:
            print
            break


class BracketsException(Exception):
    """Raised in case of non-matching brackets in a line.
    
    Takes a single argument, the unmatched bracket.
    """
    def __str__(self):
        return "Unmatched delimiter '{0}'".format(self.args[0])


def unbalanced(line):
    """Returns whether the brackets in the line are unbalanced.

    Raises BracketsError in case of matching error.
    """
    ignore_pairs = '""', ";\n"
    ignore_closer = ""
    bracket_pairs = "()", "[]", "{}"
    stack = []

    for c in line:
        if ignore_closer:
            if c == ignore_closer:
                ignore_closer = ""
            else:
                continue
        else:
            for op, cl in ignore_pairs:
                if c == op:
                    ignore_closer = cl
                    continue
        for op, cl in bracket_pairs:
            if c == op:
                stack.append(cl)
                continue
            if c == cl:
                if not stack or stack.pop() != c:
                    raise BracketsException(c)
    return bool(stack)

########NEW FILE########
__FILENAME__ = standardimports
"""Lists the symbols names that should be defined in all clojure namespaces.
"""

from clojure.lang.persistentlist import PersistentList
from clojure.lang.ipersistentlist import IPersistentList
from clojure.lang.ipersistentvector import IPersistentVector
from clojure.lang.ipersistentcollection import IPersistentCollection
from clojure.lang.ipersistentmap import IPersistentMap
from clojure.lang.ilookup import ILookup
from clojure.lang.associative import Associative
from clojure.lang.ideref import IDeref
from clojure.lang.seqable import Seqable
from clojure.lang.atom import Atom
from clojure.lang.ref import Ref
from clojure.lang.iobj import IObj
from clojure.lang.lockingtransaction import LockingTransaction

from clojure.lang.iseq import ISeq
from clojure.lang.var import Var
from clojure.lang.cljexceptions import *
from clojure.lang.sequential import Sequential
import clojure

import dis
import sys

sys.path

########NEW FILE########
__FILENAME__ = byteplay
# byteplay - Python bytecode assembler/disassembler.
# Copyright (C) 2006-2010 Noam Yorav-Raphael
# Homepage: http://code.google.com/p/byteplay
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

# Many thanks to Greg X for adding support for Python 2.6 and 2.7!

__version__ = '0.2'

__all__ = ['opmap', 'opname', 'opcodes',
           'cmp_op', 'hasarg', 'hasname', 'hasjrel', 'hasjabs',
           'hasjump', 'haslocal', 'hascompare', 'hasfree', 'hascode',
           'hasflow', 'getse',
           'Opcode', 'SetLineno', 'Label', 'isopcode', 'Code',
           'CodeList', 'printcodelist']

import opcode
from dis import findlabels
import types
from array import array
import operator
import itertools
import sys
import warnings
from io import StringIO

######################################################################
# Define opcodes and information about them

python_version = '.'.join(str(x) for x in sys.version_info[:2])
if python_version not in ('2.4', '2.5', '2.6', '2.7'):
    warnings.warn("byteplay doesn't support Python version "+python_version)

class Opcode(int):
    """An int which represents an opcode - has a nicer repr."""
    def __repr__(self):
        return opname[self]
    __str__ = __repr__

class CodeList(list):
    """A list for storing opcode tuples - has a nicer __str__."""
    def __str__(self):
        f = StringIO()
        printcodelist(self, f)
        return f.getvalue()

opmap = dict((name.replace('+', '_'), Opcode(code))
for name, code in opcode.opmap.items()
if name != 'EXTENDED_ARG')
opname = dict((code, name) for name, code in opmap.items())
opcodes = set(opname)

def globalize_opcodes():
    for name, code in opmap.items():
        globals()[name] = code
        __all__.append(name)
globalize_opcodes()

cmp_op = opcode.cmp_op

hasarg = set(x for x in opcodes if x >= opcode.HAVE_ARGUMENT)
hasconst = set(Opcode(x) for x in opcode.hasconst)
hasname = set(Opcode(x) for x in opcode.hasname)
hasjrel = set(Opcode(x) for x in opcode.hasjrel)
hasjabs = set(Opcode(x) for x in opcode.hasjabs)
hasjump = hasjrel.union(hasjabs)
haslocal = set(Opcode(x) for x in opcode.haslocal)
hascompare = set(Opcode(x) for x in opcode.hascompare)
hasfree = set(Opcode(x) for x in opcode.hasfree)
hascode = set([MAKE_FUNCTION, MAKE_CLOSURE])

class _se:
    """Quick way of defining static stack effects of opcodes"""
    # Taken from assembler.py by Phillip J. Eby
    NOP       = 0,0

    POP_TOP   = 1,0
    ROT_TWO   = 2,2
    ROT_THREE = 3,3
    ROT_FOUR  = 4,4
    DUP_TOP   = 1,2

    UNARY_POSITIVE = UNARY_NEGATIVE = UNARY_NOT = UNARY_CONVERT =\
    UNARY_INVERT = GET_ITER = LOAD_ATTR = 1,1

    IMPORT_FROM = 1,2

    BINARY_POWER = BINARY_MULTIPLY = BINARY_DIVIDE = BINARY_FLOOR_DIVIDE =\
    BINARY_TRUE_DIVIDE = BINARY_MODULO = BINARY_ADD = BINARY_SUBTRACT =\
    BINARY_SUBSCR = BINARY_LSHIFT = BINARY_RSHIFT = BINARY_AND =\
    BINARY_XOR = BINARY_OR = COMPARE_OP = 2,1

    INPLACE_POWER = INPLACE_MULTIPLY = INPLACE_DIVIDE =\
    INPLACE_FLOOR_DIVIDE = INPLACE_TRUE_DIVIDE = INPLACE_MODULO =\
    INPLACE_ADD = INPLACE_SUBTRACT = INPLACE_LSHIFT = INPLACE_RSHIFT =\
    INPLACE_AND = INPLACE_XOR = INPLACE_OR = 2,1

    SLICE_0, SLICE_1, SLICE_2, SLICE_3 =\
    (1,1),(2,1),(2,1),(3,1)
    STORE_SLICE_0, STORE_SLICE_1, STORE_SLICE_2, STORE_SLICE_3 =\
    (2,0),(3,0),(3,0),(4,0)
    DELETE_SLICE_0, DELETE_SLICE_1, DELETE_SLICE_2, DELETE_SLICE_3 =\
    (1,0),(2,0),(2,0),(3,0)

    STORE_SUBSCR = 3,0
    DELETE_SUBSCR = STORE_ATTR = 2,0
    DELETE_ATTR = STORE_DEREF = 1,0
    PRINT_NEWLINE = 0,0
    PRINT_EXPR = PRINT_ITEM = PRINT_NEWLINE_TO = IMPORT_STAR = 1,0
    STORE_NAME = STORE_GLOBAL = STORE_FAST = 1,0
    PRINT_ITEM_TO = 2,0

    LOAD_LOCALS = LOAD_CONST = LOAD_NAME = LOAD_GLOBAL = LOAD_FAST =\
    LOAD_CLOSURE = LOAD_DEREF = BUILD_MAP = 0,1

    DELETE_FAST = DELETE_GLOBAL = DELETE_NAME = 0,0

    EXEC_STMT = 3,0
    BUILD_CLASS = 3,1

    STORE_MAP = MAP_ADD = 2,0
    SET_ADD = 1,0

    if   python_version == '2.4':
        YIELD_VALUE = 1,0
        IMPORT_NAME = 1,1
        LIST_APPEND = 2,0
    elif python_version == '2.5':
        YIELD_VALUE = 1,1
        IMPORT_NAME = 2,1
        LIST_APPEND = 2,0
    elif python_version == '2.6':
        YIELD_VALUE = 1,1
        IMPORT_NAME = 2,1
        LIST_APPEND = 2,0
    elif python_version == '2.7':
        YIELD_VALUE = 1,1
        IMPORT_NAME = 2,1
        LIST_APPEND = 1,0


_se = dict((op, getattr(_se, opname[op]))
for op in opcodes
if hasattr(_se, opname[op]))

hasflow = opcodes - set(_se) -\
          set([CALL_FUNCTION, CALL_FUNCTION_VAR, CALL_FUNCTION_KW,
               CALL_FUNCTION_VAR_KW, BUILD_TUPLE, BUILD_LIST,
               UNPACK_SEQUENCE, BUILD_SLICE, # -- disabled for Python 3 DUP_TOPX,
               RAISE_VARARGS, MAKE_FUNCTION, MAKE_CLOSURE])
if python_version == '2.7':
    hasflow = hasflow - set([BUILD_SET])

def getse(op, arg=None):
    """Get the stack effect of an opcode, as a (pop, push) tuple.

    If an arg is needed and is not given, a ValueError is raised.
    If op isn't a simple opcode, that is, the flow doesn't always continue
    to the next opcode, a ValueError is raised.
    """
    try:
        return _se[op]
    except KeyError:
        # Continue to opcodes with an effect that depends on arg
        pass

    if arg is None:
        raise ValueError("Opcode stack behaviour depends on arg")

    def get_func_tup(arg, nextra):
        if arg > 0xFFFF:
            raise ValueError("Can only split a two-byte argument")
        return (nextra + 1 + (arg & 0xFF) + 2*((arg >> 8) & 0xFF),
                1)

    if op == CALL_FUNCTION:
        return get_func_tup(arg, 0)
    elif op == CALL_FUNCTION_VAR:
        return get_func_tup(arg, 1)
    elif op == CALL_FUNCTION_KW:
        return get_func_tup(arg, 1)
    elif op == CALL_FUNCTION_VAR_KW:
        return get_func_tup(arg, 2)

    elif op == BUILD_TUPLE:
        return arg, 1
    elif op == BUILD_LIST:
        return arg, 1
    elif python_version == '2.7' and op == BUILD_SET:
        return arg, 1
    elif op == UNPACK_SEQUENCE:
        return 1, arg
    elif op == BUILD_SLICE:
        return arg, 1
    elif op == DUP_TOPX:
        return arg, arg*2
    elif op == RAISE_VARARGS:
        return 1+arg, 1
    elif op == MAKE_FUNCTION:
        return 1+arg, 1
    elif op == MAKE_CLOSURE:
        if python_version == '2.4':
            raise ValueError("The stack effect of MAKE_CLOSURE depends on TOS")
        else:
            return 2+arg, 1
    else:
        raise ValueError("The opcode %r isn't recognized or has a special "\
                          "flow control" % op)

class SetLinenoType(object):
    def __repr__(self):
        return 'SetLineno'
SetLineno = SetLinenoType()

class Label(object):
    def __init__(self, name = None):
        self.name = name
    def __repr__(self):
        return "Label: " + str(self.name)
    def __eq__(self, other):
        return isinstance(other, Label) and self.name == other.name

def isopcode(obj):
    """Return whether obj is an opcode - not SetLineno or Label"""
    return obj is not SetLineno and not isinstance(obj, Label)

# Flags from code.h
CO_OPTIMIZED              = 0x0001      # use LOAD/STORE_FAST instead of _NAME
CO_NEWLOCALS              = 0x0002      # only cleared for module/exec code
CO_VARARGS                = 0x0004
CO_VARKEYWORDS            = 0x0008
CO_NESTED                 = 0x0010      # ???
CO_GENERATOR              = 0x0020
CO_NOFREE                 = 0x0040      # set if no free or cell vars
CO_GENERATOR_ALLOWED      = 0x1000      # unused
# The future flags are only used on code generation, so we can ignore them.
# (It does cause some warnings, though.)
CO_FUTURE_DIVISION        = 0x2000
CO_FUTURE_ABSOLUTE_IMPORT = 0x4000
CO_FUTURE_WITH_STATEMENT  = 0x8000


######################################################################
# Define the Code class

class Code(object):
    """An object which holds all the information which a Python code object
    holds, but in an easy-to-play-with representation.

    The attributes are:

    Affecting action
    ----------------
    code - list of 2-tuples: the code
    freevars - list of strings: the free vars of the code (those are names
               of variables created in outer functions and used in the function)
    args - list of strings: the arguments of the code
    varargs - boolean: Does args end with a '*args' argument
    varkwargs - boolean: Does args end with a '**kwargs' argument
    newlocals - boolean: Should a new local namespace be created.
                (True in functions, False for module and exec code)

    Not affecting action
    --------------------
    name - string: the name of the code (co_name)
    filename - string: the file name of the code (co_filename)
    firstlineno - int: the first line number (co_firstlineno)
    docstring - string or None: the docstring (the first item of co_consts,
                if it's str or unicode)

    code is a list of 2-tuples. The first item is an opcode, or SetLineno, or a
    Label instance. The second item is the argument, if applicable, or None.
    code can be a CodeList instance, which will produce nicer output when
    being printed.
    """
    def __init__(self, code, freevars, args, varargs, varkwargs, newlocals,
                 name, filename, firstlineno, docstring):
        self.code = code
        self.freevars = freevars
        self.args = args
        self.varargs = varargs
        self.varkwargs = varkwargs
        self.newlocals = newlocals
        self.name = name
        self.filename = filename
        self.firstlineno = firstlineno
        self.docstring = docstring

    @staticmethod
    def _findlinestarts(code):
        """Find the offsets in a byte code which are start of lines in the
        source.

        Generate pairs (offset, lineno) as described in Python/compile.c.

        This is a modified version of dis.findlinestarts, which allows multiple
        "line starts" with the same line number.
        """
        byte_increments = [ord(c) for c in code.co_lnotab[0::2]]
        line_increments = [ord(c) for c in code.co_lnotab[1::2]]

        lineno = code.co_firstlineno
        addr = 0
        for byte_incr, line_incr in zip(byte_increments, line_increments):
            if byte_incr:
                yield (addr, lineno)
                addr += byte_incr
            lineno += line_incr
        yield (addr, lineno)

    @classmethod
    def from_code(cls, co):
        """Disassemble a Python code object into a Code object."""
        co_code = co.co_code
        labels = dict((addr, Label()) for addr in findlabels(co_code))
        linestarts = dict(cls._findlinestarts(co))
        cellfree = co.co_cellvars + co.co_freevars

        code = CodeList()
        n = len(co_code)
        i = 0
        extended_arg = 0
        while i < n:
            op = Opcode(ord(co_code[i]))
            if i in labels:
                code.append((labels[i], None))
            if i in linestarts:
                code.append((SetLineno, linestarts[i]))
            i += 1
            if op in hascode:
                lastop, lastarg = code[-1]
                if lastop != LOAD_CONST:
                    raise ValueError(\
                    "%s should be preceded by LOAD_CONST code" % op)
                code[-1] = (LOAD_CONST, Code.from_code(lastarg))
            if op not in hasarg:
                code.append((op, None))
            else:
                arg = ord(co_code[i]) + ord(co_code[i+1])*256 + extended_arg
                extended_arg = 0
                i += 2
                if op == opcode.EXTENDED_ARG:
                    extended_arg = arg << 16
                elif op in hasconst:
                    code.append((op, co.co_consts[arg]))
                elif op in hasname:
                    code.append((op, co.co_names[arg]))
                elif op in hasjabs:
                    code.append((op, labels[arg]))
                elif op in hasjrel:
                    code.append((op, labels[i + arg]))
                elif op in haslocal:
                    code.append((op, co.co_varnames[arg]))
                elif op in hascompare:
                    code.append((op, cmp_op[arg]))
                elif op in hasfree:
                    code.append((op, cellfree[arg]))
                else:
                    code.append((op, arg))

        varargs = bool(co.co_flags & CO_VARARGS)
        varkwargs = bool(co.co_flags & CO_VARKEYWORDS)
        newlocals = bool(co.co_flags & CO_NEWLOCALS)
        args = co.co_varnames[:co.co_argcount + varargs + varkwargs]
        if co.co_consts and isinstance(co.co_consts[0], basestring):
            docstring = co.co_consts[0]
        else:
            docstring = None
        return cls(code = code,
            freevars = co.co_freevars,
            args = args,
            varargs = varargs,
            varkwargs = varkwargs,
            newlocals = newlocals,
            name = co.co_name,
            filename = co.co_filename,
            firstlineno = co.co_firstlineno,
            docstring = docstring,
        )

    def __eq__(self, other):
        if (self.freevars != other.freevars or
            self.args != other.args or
            self.varargs != other.varargs or
            self.varkwargs != other.varkwargs or
            self.newlocals != other.newlocals or
            self.name != other.name or
            self.filename != other.filename or
            self.firstlineno != other.firstlineno or
            self.docstring != other.docstring or
            len(self.code) != len(other.code)
            ):
            return False

        # Compare code. This isn't trivial because labels should be matching,
        # not equal.
        labelmapping = {}
        for (op1, arg1), (op2, arg2) in itertools.izip(self.code, other.code):
            if isinstance(op1, Label):
                if labelmapping.setdefault(op1, op2) is not op2:
                    return False
            else:
                if op1 != op2:
                    return False
                if op1 in hasjump:
                    if labelmapping.setdefault(arg1, arg2) is not arg2:
                        return False
                elif op1 in hasarg:
                    if arg1 != arg2:
                        return False
        return True

    def _compute_flags(self):
        opcodes = set(op for op, arg in self.code if isopcode(op))

        optimized = (STORE_NAME not in opcodes and
                     LOAD_NAME not in opcodes and
                     DELETE_NAME not in opcodes)
        generator = (YIELD_VALUE in opcodes)
        nofree = not (opcodes.intersection(hasfree))

        flags = 0
        if optimized: flags |= CO_OPTIMIZED
        if self.newlocals: flags |= CO_NEWLOCALS
        if self.varargs: flags |= CO_VARARGS
        if self.varkwargs: flags |= CO_VARKEYWORDS
        if generator: flags |= CO_GENERATOR
        if nofree: flags |= CO_NOFREE
        return flags

    def _compute_stacksize(self):
        """Get a code list, compute its maximal stack usage."""
        # This is done by scanning the code, and computing for each opcode
        # the stack state at the opcode.
        code = self.code

        # A mapping from labels to their positions in the code list
        label_pos = dict((op, pos)
        for pos, (op, arg) in enumerate(code)
        if isinstance(op, Label))

        # sf_targets are the targets of SETUP_FINALLY opcodes. They are recorded
        # because they have special stack behaviour. If an exception was raised
        # in the block pushed by a SETUP_FINALLY opcode, the block is popped
        # and 3 objects are pushed. On return or continue, the block is popped
        # and 2 objects are pushed. If nothing happened, the block is popped by
        # a POP_BLOCK opcode and 1 object is pushed by a (LOAD_CONST, None)
        # operation.
        #
        # Our solution is to record the stack state of SETUP_FINALLY targets
        # as having 3 objects pushed, which is the maximum. However, to make
        # stack recording consistent, the get_next_stacks function will always
        # yield the stack state of the target as if 1 object was pushed, but
        # this will be corrected in the actual stack recording.

        sf_targets = set(label_pos[arg]
        for op, arg in code
        if op == SETUP_FINALLY)

        # What we compute - for each opcode, its stack state, as an n-tuple.
        # n is the number of blocks pushed. For each block, we record the number
        # of objects pushed.
        stacks = [None] * len(code)

        def get_next_stacks(pos, curstack):
            """Get a code position and the stack state before the operation
            was done, and yield pairs (pos, curstack) for the next positions
            to be explored - those are the positions to which you can get
            from the given (pos, curstack).

            If the given position was already explored, nothing will be yielded.
            """
            op, arg = code[pos]

            if isinstance(op, Label):
                # We should check if we already reached a node only if it is
                # a label.
                if pos in sf_targets:
                    curstack = curstack[:-1] + (curstack[-1] + 2,)
                if stacks[pos] is None:
                    stacks[pos] = curstack
                else:
                    if stacks[pos] != curstack:
                        raise ValueError("Inconsistent code")
                    return

            def newstack(n):
                # Return a new stack, modified by adding n elements to the last
                # block
                if curstack[-1] + n < 0:
                    raise ValueError("Popped a non-existing element")
                return curstack[:-1] + (curstack[-1]+n,)

            if not isopcode(op):
                # label or SetLineno - just continue to next line
                yield pos+1, curstack

            elif op in (STOP_CODE, RETURN_VALUE, RAISE_VARARGS):
                # No place in particular to continue to
                pass

            elif op == MAKE_CLOSURE and python_version == '2.4':
                # This is only relevant in Python 2.4 - in Python 2.5 the stack
                # effect of MAKE_CLOSURE can be calculated from the arg.
                # In Python 2.4, it depends on the number of freevars of TOS,
                # which should be a code object.
                if pos == 0:
                    raise ValueError(\
                    "MAKE_CLOSURE can't be the first opcode")
                lastop, lastarg = code[pos-1]
                if lastop != LOAD_CONST:
                    raise ValueError(\
                    "MAKE_CLOSURE should come after a LOAD_CONST op")
                try:
                    nextrapops = len(lastarg.freevars)
                except AttributeError:
                    try:
                        nextrapops = len(lastarg.co_freevars)
                    except AttributeError:
                        raise ValueError(\
                        "MAKE_CLOSURE preceding const should "\
                        "be a code or a Code object")

                yield pos+1, newstack(-arg-nextrapops)

            elif op not in hasflow:
                # Simple change of stack
                pop, push = getse(op, arg)
                yield pos+1, newstack(push - pop)

            elif op in (JUMP_FORWARD, JUMP_ABSOLUTE):
                # One possibility for a jump
                yield label_pos[arg], curstack

            elif python_version < '2.7' and op in (JUMP_IF_FALSE, JUMP_IF_TRUE):
                # Two possibilities for a jump
                yield label_pos[arg], curstack
                yield pos+1, curstack

            elif python_version >= '2.7' and op in (POP_JUMP_IF_FALSE, POP_JUMP_IF_TRUE):
                # Two possibilities for a jump
                yield label_pos[arg], newstack(-1)
                yield pos+1, newstack(-1)

            elif python_version >= '2.7' and op in (JUMP_IF_TRUE_OR_POP, JUMP_IF_FALSE_OR_POP):
                # Two possibilities for a jump
                yield label_pos[arg], curstack
                yield pos+1, newstack(-1)

            elif op == FOR_ITER:
                # FOR_ITER pushes next(TOS) on success, and pops TOS and jumps
                # on failure
                yield label_pos[arg], newstack(-1)
                yield pos+1, newstack(1)

            elif op == BREAK_LOOP:
                # BREAK_LOOP jumps to a place specified on block creation, so
                # it is ignored here
                pass

            elif op == CONTINUE_LOOP:
                # CONTINUE_LOOP jumps to the beginning of a loop which should
                # already ave been discovered, but we verify anyway.
                # It pops a block.
                if python_version == '2.6':
                    pos, stack = label_pos[arg], curstack[:-1]
                    if stacks[pos] != stack: #this could be a loop with a 'with' inside
                        yield pos, stack[:-1] + (stack[-1]-1,)
                    else:
                        yield pos, stack
                else:
                    yield label_pos[arg], curstack[:-1]

            elif op == SETUP_LOOP:
                # We continue with a new block.
                # On break, we jump to the label and return to current stack
                # state.
                yield label_pos[arg], curstack
                yield pos+1, curstack + (0,)

            elif op == SETUP_EXCEPT:
                # We continue with a new block.
                # On exception, we jump to the label with 3 extra objects on
                # stack
                yield label_pos[arg], newstack(3)
                yield pos+1, curstack + (0,)

            elif op == SETUP_FINALLY:
                # We continue with a new block.
                # On exception, we jump to the label with 3 extra objects on
                # stack, but to keep stack recording consistent, we behave as
                # if we add only 1 object. Extra 2 will be added to the actual
                # recording.
                yield label_pos[arg], newstack(1)
                yield pos+1, curstack + (0,)

            elif python_version == '2.7' and op == SETUP_WITH:
                yield label_pos[arg], curstack
                yield pos+1, newstack(-1) + (1,)

            elif op == POP_BLOCK:
                # Just pop the block
                yield pos+1, curstack[:-1]

            elif op == END_FINALLY:
                # Since stack recording of SETUP_FINALLY targets is of 3 pushed
                # objects (as when an exception is raised), we pop 3 objects.
                yield pos+1, newstack(-3)

            elif op == WITH_CLEANUP:
                # Since WITH_CLEANUP is always found after SETUP_FINALLY
                # targets, and the stack recording is that of a raised
                # exception, we can simply pop 1 object and let END_FINALLY
                # pop the remaining 3.
                if python_version == '2.7':
                    yield pos+1, newstack(2)
                else:
                    yield pos+1, newstack(-1)

            else:
                assert False, "Unhandled opcode: %r" % op


        # Now comes the calculation: open_positions holds positions which are
        # yet to be explored. In each step we take one open position, and
        # explore it by adding the positions to which you can get from it, to
        # open_positions. On the way, we update maxsize.
        # open_positions is a list of tuples: (pos, stack state)
        maxsize = 0
        open_positions = [(0, (0,))]
        while open_positions:
            pos, curstack = open_positions.pop()
            maxsize = max(maxsize, sum(curstack))
            open_positions.extend(get_next_stacks(pos, curstack))

        return maxsize

    def to_code(self):
        """Assemble a Python code object from a Code object."""
        co_argcount = len(self.args) - self.varargs - self.varkwargs
        co_stacksize = self._compute_stacksize()
        co_flags = self._compute_flags()

        co_consts = [self.docstring]
        co_names = []
        co_varnames = list(self.args)

        co_freevars = tuple(self.freevars)

        # We find all cellvars beforehand, for two reasons:
        # 1. We need the number of them to construct the numeric argument
        #    for ops in "hasfree".
        # 2. We need to put arguments which are cell vars in the beginning
        #    of co_cellvars
        cellvars = set(arg for op, arg in self.code
        if isopcode(op) and op in hasfree
        and arg not in co_freevars)
        co_cellvars = [x for x in self.args if x in cellvars]

        def index(seq, item, eq=operator.eq, can_append=True):
            """Find the index of item in a sequence and return it.
            If it is not found in the sequence, and can_append is True,
            it is appended to the sequence.

            eq is the equality operator to use.
            """
            for i, x in enumerate(seq):
                if eq(x, item):
                    return i
            else:
                if can_append:
                    seq.append(item)
                    return len(seq) - 1
                else:
                    raise IndexError("Item not found")

        # List of tuples (pos, label) to be filled later
        jumps = []
        # A mapping from a label to its position
        label_pos = {}
        # Last SetLineno
        lastlineno = self.firstlineno
        lastlinepos = 0

        co_code = array('B')
        co_lnotab = array('B')
        for i, (op, arg) in enumerate(self.code):
            if isinstance(op, Label):
                label_pos[op] = len(co_code)

            elif op is SetLineno:
                incr_lineno = arg - lastlineno
                incr_pos = len(co_code) - lastlinepos
                lastlineno = arg
                lastlinepos = len(co_code)

                if incr_lineno == 0 and incr_pos == 0:
                    co_lnotab.append(0)
                    co_lnotab.append(0)
                else:
                    while incr_pos > 255:
                        co_lnotab.append(255)
                        co_lnotab.append(0)
                        incr_pos -= 255
                    while incr_lineno > 255:
                        co_lnotab.append(incr_pos)
                        co_lnotab.append(255)
                        incr_pos = 0
                        incr_lineno -= 255
                    if incr_pos or incr_lineno:
                        co_lnotab.append(incr_pos)
                        co_lnotab.append(incr_lineno)

            elif op == opcode.EXTENDED_ARG:
                raise ValueError("EXTENDED_ARG not supported in Code objects")

            elif not op in hasarg:
                co_code.append(op)

            else:
                if op in hasconst:
                    if isinstance(arg, Code) and i < len(self.code)-1 and\
                       self.code[i+1][0] in hascode:
                        arg = arg.to_code()
                    arg = index(co_consts, arg, operator.is_)
                elif op in hasname:
                    arg = index(co_names, arg)
                elif op in hasjump:
                    # arg will be filled later
                    jumps.append((len(co_code), arg))
                    arg = 0
                elif op in haslocal:
                    arg = index(co_varnames, arg)
                elif op in hascompare:
                    arg = index(cmp_op, arg, can_append=False)
                elif op in hasfree:
                    try:
                        arg = index(co_freevars, arg, can_append=False)\
                        + len(cellvars)
                    except IndexError:
                        arg = index(co_cellvars, arg)
                else:
                    # arg is ok
                    pass

                if arg > 0xFFFF:
                    co_code.append(opcode.EXTENDED_ARG)
                    co_code.append((arg >> 16) & 0xFF)
                    co_code.append((arg >> 24) & 0xFF)
                co_code.append(op)
                co_code.append(arg & 0xFF)
                co_code.append((arg >> 8) & 0xFF)

        for pos, label in jumps:
            jump = label_pos[label]
            if co_code[pos] in hasjrel:
                jump -= pos+3
            if jump > 0xFFFF:
                raise NotImplementedError("Extended jumps not implemented")
            co_code[pos+1] = jump & 0xFF
            co_code[pos+2] = (jump >> 8) & 0xFF

        co_code = co_code.tostring()
        co_lnotab = co_lnotab.tostring()

        co_consts = tuple(co_consts)
        co_names = tuple(co_names)
        co_varnames = tuple(co_varnames)
        co_nlocals = len(co_varnames)
        co_cellvars = tuple(co_cellvars)

        return types.CodeType(co_argcount, co_nlocals, co_stacksize, co_flags,
            co_code, co_consts, co_names, co_varnames,
            self.filename, self.name, self.firstlineno, co_lnotab,
            co_freevars, co_cellvars)


def printcodelist(codelist, to=sys.stdout):
    """Get a code list. Print it nicely."""

    labeldict = {}
    pendinglabels = []
    for i, (op, arg) in enumerate(codelist):
        if isinstance(op, Label):
            pendinglabels.append(op)
        elif op is SetLineno:
            pass
        else:
            while pendinglabels:
                labeldict[pendinglabels.pop()] = i

    lineno = None
    islabel = False
    for i, (op, arg) in enumerate(codelist):
        if op is SetLineno:
            lineno = arg
            print >> to
            continue

        if isinstance(op, Label):
            islabel = True
            continue

        if lineno is None:
            linenostr = ''
        else:
            linenostr = str(lineno)
            lineno = None

        if islabel:
            islabelstr = '>>'
            islabel = False
        else:
            islabelstr = ''

        if op in hasconst:
            argstr = repr(arg)
        elif op in hasjump:
            try:
                argstr = 'to ' + str(labeldict[arg])
            except KeyError:
                argstr = repr(arg)
        elif op in hasarg:
            argstr = str(arg)
        else:
            argstr = ''

        print >> to, '%3s     %2s %4d %-20s %s' % (
            linenostr,
            islabelstr,
            i,
            op,
            argstr)

def recompile(filename):
    """Create a .pyc by disassembling the file and assembling it again, printing
    a message that the reassembled file was loaded."""
    # Most of the code here based on the compile.py module.
    import os
    import imp
    import marshal
    import struct

    f = open(filename, 'U')
    try:
        timestamp = long(os.fstat(f.fileno()).st_mtime)
    except AttributeError:
        timestamp = long(os.stat(filename).st_mtime)
    codestring = f.read()
    f.close()
    if codestring and codestring[-1] != '\n':
        codestring = codestring + '\n'
    try:
        codeobject = compile(codestring, filename, 'exec')
    except SyntaxError:
        print >> sys.stderr, "Skipping %s - syntax error." % filename
        return
    cod = Code.from_code(codeobject)
    message = "reassembled %r imported.\n" % filename
    cod.code[:0] = [ # __import__('sys').stderr.write(message)
        (LOAD_GLOBAL, '__import__'),
        (LOAD_CONST, 'sys'),
        (CALL_FUNCTION, 1),
        (LOAD_ATTR, 'stderr'),
        (LOAD_ATTR, 'write'),
        (LOAD_CONST, message),
        (CALL_FUNCTION, 1),
        (POP_TOP, None),
                     ]
    codeobject2 = cod.to_code()
    fc = open(filename+'c', 'wb')
    fc.write('\0\0\0\0')
    fc.write(struct.pack('<l', timestamp))
    marshal.dump(codeobject2, fc)
    fc.flush()
    fc.seek(0, 0)
    fc.write(imp.get_magic())
    fc.close()

def recompile_all(path):
    """recursively recompile all .py files in the directory"""
    import os
    if os.path.isdir(path):
        for root, dirs, files in os.walk(path):
            for name in files:
                if name.endswith('.py'):
                    filename = os.path.abspath(os.path.join(root, name))
                    print >> sys.stderr, filename
                    recompile(filename)
    else:
        filename = os.path.abspath(path)
        recompile(filename)

def main():
    import os
    if len(sys.argv) != 2 or not os.path.exists(sys.argv[1]):
        print ("""\
Usage: %s dir

Search recursively for *.py in the given directory, disassemble and assemble
them, adding a note when each file is imported.

Use it to test byteplay like this:
> byteplay.py Lib
> make test

Some FutureWarnings may be raised, but that's expected.

Tip: before doing this, check to see which tests fail even without reassembling
them...
""" % sys.argv[0])
        sys.exit(1)
    recompile_all(sys.argv[1])

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = freeze
## A clojure-py implementation of deep-freeze. Used by the compiler
## for saving code modules
from clojure.lang.protocol import ProtocolFn
from clojure.lang.multimethod import MultiMethod
from clojure.lang.pytypes import *

topID = 0
seenID = topID
codeFreezeID = 1

def registerType(name):
    global topID
    topID += 1
    name = name + "ID"
    globals()["name"] = topID
    
    def identity(fn):
        return fn
        
    return identity
    
writeDispatcher = ProtocolFn("freeze-write")
read = MultiMethod(lambda id, *args: id)


_codeAttrs = filter(lambda x: not x.startswith("_"), dir(pyTypeCode))

def writeCode(code, strm, state):
    strm.write(codeFreezeID)
    
    for attr in _codeAttrs:
        write(getattr(code, attr), strm, state) 
        
writeDispatcher.extend(pyTypeCode, writeCode)


def write(obj, strm, state = None):
    if state is None:
        state = WriterState()
    
    if state.hasSeen(obj):
        strm.write(seenID)
        strm.write(state.getID(obj))
    
    writeDispatcher(obj, strm, state)
    
        

class WriterState(object):
    def __init__(self):
        self.seen = {}
        self.nextIDX = -1
        
    def hasSeen(self, obj):
        return obj in self.seen
        
    def getID(self, obj):
        return self.seen[obj]
        
    def markSeen(self, obj):
        self.nextIDX += 1
        self.seen[obj] = self.nextIDX
        




########NEW FILE########
__FILENAME__ = shared_lock
#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-
###############################################################################
#
# Shared lock (aka reader-writer lock) implementation.
#
# Written by Dmitry Dvoinikov <dmitry@targeted.org>
# Distributed under MIT license.
#
# 2012:
# Edited by Leo Franchi (lfranchi@kde.org) to remove the exc_string dep
#
# The latest source code (complete with self-tests) is available from:
# http://www.targeted.org/python/recipes/shared_lock.py
#
# Requires exc_string module available from either
# http://www.targeted.org/python/recipes/exc_string.py -OR-
# http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/444746
#
# Features:
#
# 1. Supports timeouts. Attempts to acquire a lock occassionally time out in
#    a specified amount of time.
# 2. Fully reentrant - single thread can have any number of both shared and
#    exclusive ownerships on the same lock instance (restricted with the lock
#    semantics of course).
# 3. Supports FIFO order for threads waiting to acquire the lock exclusively.
# 4. Robust and manageable. Can be created in debug mode so that each lock
#    operation causes the internal invariant to be checked (although this
#    certainly slows it down). Can be created with logging so that each lock
#    operation is verbosely logged.
# 5. Prevents either side from starvation by picking the winning thread at
#    random if such behaviour is appropriate.
# 6. Recycles temporary one-time synchronization objects.
# 7. Can be used as a drop-in replacement for threading.Lock, ex.
#    >> from shared_lock import SharedLock as Lock
#    because the semantics and exclusive locking interface are identical to
#    that of threading.Lock.
#
# Synopsis:
#
# class SharedLock(object):
#     def acquire(timeout_sec = None):
#         Attempts to acquire the lock exclusively within the optional timeout.
#         If the timeout is not specified, waits for the lock infinitely.
#         Returns True if the lock has been acquired, False otherwise.
#     def release():
#         Releases the lock previously locked by a call to acquire().
#         Returns None.
#     def acquire_shared(timeout_sec = None):
#         Attempts to acquire the lock in shared mode within the optional
#         timeout. If the timeout is not specified, waits for the lock
#         infinitely. Returns True if the lock has been acquired, False
#         otherwise.
#     def release_shared():
#         Releases the lock previously locked by a call to acquire_shared().
#         Returns None.
#
################################################################################
#
# (c) 2005 Dmitry Dvoinikov <dmitry@targeted.org>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
# of the Software, and to permit persons to whom the Software is furnished to do
# so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
################################################################################

__all__ = [ "SharedLock" ]

################################################################################

from threading import Lock, currentThread, Event
from random import randint
from contextlib import contextmanager
# from exc_string import trace_string

if not hasattr(__builtins__, "sorted"):
    def sorted(seq):
        result = [ x for x in seq ]
        result.sort()
        return result

@contextmanager
def shared_lock(sharedlock):
    sharedlock.acquire_shared()
    try:
        yield {}
    finally:
        sharedlock.release_shared()

@contextmanager
def unique_lock(sharedlock):
    sharedlock.acquire()
    try:
        yield {}
    finally:
        sharedlock.release()

################################################################################

class SharedLock(object):

    def __init__(self, log = None, debug = False):
        """
        Takes two optional parameters, (1) log is an external log function the
        lock would use to send its messages to, ex: lambda s: xprint(s),
        (2) debug is a boolean value, if it's True the lock would be checking
        its internal invariant before and after each call.
        """

        self.__log, self.__debug, self.lckLock = log, debug, Lock()
        self.thrOwner, self.intOwnerDepth, self.dicUsers = None, 0, {}
        self.lstOwners, self.lstUsers, self.lstPooledEvents = [], [], []

    ################################### utility log function

    def _log(self, s):
        thrCurrent = currentThread()
        self.__log("%s @ %.08x %s %s @ %.08x in %s"
                  % (thrCurrent.getName(), id(thrCurrent), s,
                     self._debug_dump(), id(self), ""))

    ################################### debugging lock state dump

    def _debug_dump(self):
        return "SharedLock(Ex:[%s] (%s), Sh:[%s] (%s))" \
               % (self.thrOwner is not None
                  and "%s:%d" % (self.thrOwner.getName(),
                                 self.intOwnerDepth)
                  or "",
                  ", ".join([ "%s:%d" % (th.getName(), dp)
                              for th, evt, dp in self.lstOwners ]),
                  ", ".join(sorted([ "%s:%d" % (th.getName(), dp)
                                   for th, dp in self.dicUsers.iteritems() ])),
                  ", ".join([ "%s:%d" % (th.getName(), dp)
                              for th, evt, dp in self.lstUsers ]))

    def debug_dump(self):
        """
        Returns a printable string describing the current lock state.
        """

        self._lock()
        try:
            return self._debug_dump()
        finally:
            self._unlock()

    ################################### utility predicates

    def _has_owner(self):
        return self.thrOwner is not None

    def _has_pending_owners(self):
        return len(self.lstOwners) > 0

    def _has_users(self):
        return len(self.dicUsers) > 0

    def _has_pending_users(self):
        return len(self.lstUsers) > 0

    ################################### lock invariant

    def _invariant(self): # invariant checks slow down the lock a lot (~3 times)

        # a single thread can hold both shared and exclusive lock
        # as soon as it's the only thread holding either

        if self._has_owner() and self._has_users() \
        and self.dicUsers.keys() != [self.thrOwner]:
            return False

        # if noone is holding the lock, noone should be pending on it

        if not self._has_owner() and not self._has_users():
            return not self._has_pending_owners() \
            and not self._has_pending_users()

        # noone can be holding a lock zero times and vice versa

        if (self._has_owner() and self.intOwnerDepth <= 0) \
        or (not self._has_owner() and self.intOwnerDepth > 0):
            return False

        if len(filter(lambda dp: dp <= 0, self.dicUsers.values())) > 0:
            return False

        # if there is no owner nor pending owners, there should be no
        # pending users (all users must be executing)

        if not self._has_owner() and not self._has_pending_owners() \
        and self._has_pending_users():
            return False

        # if there is no owner nor running users, there should be no
        # pending owners (an owner must be executing)

        if not self._has_owner() and not self._has_users() \
        and self._has_pending_owners():
            return False

        # a thread may be pending on a lock only once, either as user or as owner

        lstPendingThreads = sorted(map(lambda t: t[0], self.lstUsers) +
                                   map(lambda t: t[0], self.lstOwners))

        for i in range(len(lstPendingThreads) - 1):
            if lstPendingThreads[i] is lstPendingThreads[i+1]:
                return False

        return True

    ################################### instance lock

    def _lock(self):
        self.lckLock.acquire()

    def _unlock(self):
        self.lckLock.release()

    ################################### sleep/wakeup event pool

    def _pick_event(self):                      # events are pooled/recycled
        if len(self.lstPooledEvents):           # because creating and then
            return self.lstPooledEvents.pop(0)  # garbage collecting kernel
        else:                                   # objects on each call could
            return Event()                      # be prohibitively expensive

    def _unpick_event(self, _evtEvent):
        self.lstPooledEvents.append(_evtEvent)

    ################################### sleep/wakeup utility

    def _acquire_event(self, _evtEvent, timeout): # puts the thread to sleep until the
                                                  # lock is acquired or timeout elapses

        if timeout is None:
            _evtEvent.wait()
            result = True
        else:
            _evtEvent.wait(timeout)
            result = _evtEvent.isSet()

        thrCurrent = currentThread()

        self._lock()
        try:

            # even if result indicates failure, the thread might still be having
            # the lock (race condition between the isSet() and _lock() above)

            if not result:
                result = _evtEvent.isSet()

            # if the lock has not been acquired, the thread must be removed from
            # the pending list it's on. in case the thread was waiting for the
            # exclusive lock and it previously had shared locks, it's put to sleep
            # again this time infinitely (!), waiting for its shared locks back

            boolReAcquireShared = False

            if not result: # the thread has failed to acquire the lock

                for i, (thrUser, evtEvent, intSharedDepth) in enumerate(self.lstUsers):
                    if thrUser is thrCurrent and evtEvent is _evtEvent:
                        assert intSharedDepth == 1
                        del self.lstUsers[i]
                        break
                else:
                    for i, (thrOwner, evtEvent, intSharedDepth) in enumerate(self.lstOwners):
                        if thrOwner is thrCurrent and evtEvent is _evtEvent:
                            del self.lstOwners[i]
                            if intSharedDepth > 0:
                                if not self._has_owner():
                                    self.dicUsers[thrCurrent] = intSharedDepth
                                else:
                                    self.lstUsers.append((thrCurrent, _evtEvent, intSharedDepth))
                                    boolReAcquireShared = True
                            break
                    else:
                        assert False, "Invalid thread for %s in %s" % \
                                      (self._debug_dump(), "")

                # if a thread has failed to acquire a lock, it's identical as if it had
                # it and then released, therefore other threads should be released now

                self._release_threads()

            if not boolReAcquireShared:
                _evtEvent.clear()
                self._unpick_event(_evtEvent)

            if self.__debug:
                assert self._invariant(), "SharedLock invariant failed: %s in %s" % \
                                          (self._debug_dump(), "")

            if result:
                if self.__log: self._log("acquired")
            else:
                if self.__log: self._log("timed out in %.02f second(s) waiting for" % timeout)
                if boolReAcquireShared:
                    if self.__log: self._log("acquiring %d previously owned shared lock(s) for" % intSharedDepth)

        finally:
            self._unlock()

        if boolReAcquireShared:
            assert self._acquire_event(_evtEvent, None)
            return False

        return result

    def _release_events(self, _lstEvents): # releases waiting thread(s)

        for evtEvent in _lstEvents:
            evtEvent.set()

    ################################### exclusive acquire

    def acquire(self, timeout = None):
        """
        Attempts to acquire the lock exclusively within the optional timeout.
        If the timeout is not specified, waits for the lock infinitely.
        Returns True if the lock has been acquired, False otherwise.
        """

        thrCurrent = currentThread()

        self._lock()
        try:

            if self.__log: self._log("acquiring exclusive")
            if self.__debug:
                assert self._invariant(), "SharedLock invariant failed: %s in %s" % \
                                          (self._debug_dump(), "")

            # this thread already has exclusive lock, the count is incremented

            if thrCurrent is self.thrOwner:

                self.intOwnerDepth += 1
                if self.__debug:
                    assert self._invariant(), "SharedLock invariant failed: %s in %s" % \
                                              (self._debug_dump(), "")
                if self.__log: self._log("acquired exclusive")
                return True

            # this thread already has shared lock, this is the most complicated case

            elif thrCurrent in self.dicUsers:

                # the thread gets exclusive lock immediately if there is no other threads

                if self.dicUsers.keys() == [thrCurrent] \
                and not self._has_pending_users() and not self._has_pending_owners():

                    self.thrOwner = thrCurrent
                    self.intOwnerDepth = 1
                    if self.__debug:
                        assert self._invariant(), "SharedLock invariant failed: %s in %s" % \
                                                  (self._debug_dump(), "")
                    if self.__log: self._log("acquired exclusive")
                    return True

                # the thread releases its shared lock in hope for the future
                # exclusive one

                intSharedDepth = self.dicUsers.pop(thrCurrent) # that many times it had shared lock

                evtEvent = self._pick_event()
                self.lstOwners.append((thrCurrent, evtEvent, intSharedDepth)) # it will be given them back

                self._release_threads()

            # a thread acquires exclusive lock whenever there is no
            # current owner nor running users

            elif not self._has_owner() and not self._has_users():

                self.thrOwner = thrCurrent
                self.intOwnerDepth = 1
                if self.__debug:
                    assert self._invariant(), "SharedLock invariant failed: %s in %s" % \
                                              (self._debug_dump(), "")
                if self.__log: self._log("acquired exclusive")
                return True

            # otherwise the thread registers itself as a pending owner with no
            # prior record of holding shared lock

            else:

                evtEvent = self._pick_event()
                self.lstOwners.append((thrCurrent, evtEvent, 0))

            if self.__debug:
                assert self._invariant(), "SharedLock invariant failed: %s in %s" % \
                                          (self._debug_dump(), "")
            if self.__log: self._log("waiting for exclusive")

        finally:
            self._unlock()

        return self._acquire_event(evtEvent, timeout) # the thread waits for a lock release

    ################################### shared acquire

    def acquire_shared(self, timeout = None):
        """
        Attempts to acquire the lock in shared mode within the optional
        timeout. If the timeout is not specified, waits for the lock
        infinitely. Returns True if the lock has been acquired, False
        otherwise.
        """

        thrCurrent = currentThread()

        self._lock()
        try:

            if self.__log: self._log("acquiring shared")
            if self.__debug:
                assert self._invariant(), "SharedLock invariant failed: %s in %s" % \
                                          (self._debug_dump(), "")

            # this thread already has shared lock, the count is incremented

            if thrCurrent in self.dicUsers:
                self.dicUsers[thrCurrent] += 1
                if self.__debug:
                    assert self._invariant(), "SharedLock invariant failed: %s in %s" % \
                                              (self._debug_dump(), "")
                if self.__log: self._log("acquired shared")
                return True

            # this thread already has exclusive lock, now it also has shared

            elif thrCurrent is self.thrOwner:
                if thrCurrent in self.dicUsers:
                    self.dicUsers[thrCurrent] += 1
                else:
                    self.dicUsers[thrCurrent] = 1
                if self.__debug:
                    assert self._invariant(), "SharedLock invariant failed: %s in %s" % \
                                              (self._debug_dump(), "")
                if self.__log: self._log("acquired shared")
                return True

            # a thread acquires shared lock whenever there is no owner
            # nor pending owners (to prevent owners starvation)

            elif not self._has_owner() and not self._has_pending_owners():
                self.dicUsers[thrCurrent] = 1
                if self.__debug:
                    assert self._invariant(), "SharedLock invariant failed: %s in %s" % \
                                              (self._debug_dump(), "")
                if self.__log: self._log("acquired shared")
                return True

            # otherwise the thread registers itself as a pending user

            else:

                evtEvent = self._pick_event()
                self.lstUsers.append((thrCurrent, evtEvent, 1))

            if self.__debug:
                assert self._invariant(), "SharedLock invariant failed: %s in %s" % \
                                          (self._debug_dump(), "")
            if self.__log: self._log("waiting for shared")

        finally:
            self._unlock()

        return self._acquire_event(evtEvent, timeout) # the thread waits for a lock release

    ###################################

    def _release_threads(self):

        # a decision is made which thread(s) to awake upon a release

        if self._has_owner():
            boolWakeUpOwner = False # noone to awake, the exclusive owner
            boolWakeUpUsers = False # must've released its shared lock
        elif not self._has_pending_owners():
            boolWakeUpOwner = False
            boolWakeUpUsers = self._has_pending_users()
        elif not self._has_users():
            boolWakeUpOwner = not self._has_pending_users() \
                              or randint(0, 1) == 0 # this prevents starvation
            boolWakeUpUsers = self._has_pending_users() and not boolWakeUpOwner
        else:
            boolWakeUpOwner = False # noone to awake, running users prevent
            boolWakeUpUsers = False # pending owners from running

        # the winning thread(s) are released

        lstEvents = []

        if boolWakeUpOwner:
            self.thrOwner, evtEvent, intSharedDepth = self.lstOwners.pop(0)
            self.intOwnerDepth = 1
            if intSharedDepth > 0:
                self.dicUsers[self.thrOwner] = intSharedDepth # restore thread's shared locks
            lstEvents.append(evtEvent)
        elif boolWakeUpUsers:
            for thrUser, evtEvent, intSharedDepth in self.lstUsers:
                self.dicUsers[thrUser] = intSharedDepth
                lstEvents.append(evtEvent)
            del self.lstUsers[:]

        self._release_events(lstEvents)

    ################################### exclusive release

    def release(self):
        """
        Releases the lock previously locked by a call to acquire().
        Returns None.
        """

        thrCurrent = currentThread()

        self._lock()
        try:

            if self.__log: self._log("releasing exclusive")
            if self.__debug:
                assert self._invariant(), "SharedLock invariant failed: %s in %s" % \
                                          (self._debug_dump(), "")

            if thrCurrent is not self.thrOwner:
                raise Exception("Current thread has not acquired the lock")

            # the thread releases its exclusive lock

            self.intOwnerDepth -= 1
            if self.intOwnerDepth > 0:
                if self.__debug:
                    assert self._invariant(), "SharedLock invariant failed: %s in %s" % \
                                              (self._debug_dump(), "")
                if self.__log: self._log("released exclusive")
                return

            self.thrOwner = None

            # a decision is made which pending thread(s) to awake (if any)

            self._release_threads()

            if self.__debug:
                assert self._invariant(), "SharedLock invariant failed: %s in %s" % \
                                          (self._debug_dump(), "")
            if self.__log: self._log("released exclusive")

        finally:
            self._unlock()

    ################################### shared release

    def release_shared(self):
        """
        Releases the lock previously locked by a call to acquire_shared().
        Returns None.
        """

        thrCurrent = currentThread()

        self._lock()
        try:

            if self.__log: self._log("releasing shared")
            if self.__debug:
                assert self._invariant(), "SharedLock invariant failed: %s in %s" % \
                                          (self._debug_dump(), "")

            if thrCurrent not in self.dicUsers:
                raise Exception("Current thread has not acquired the lock")

            # the thread releases its shared lock

            self.dicUsers[thrCurrent] -= 1
            if self.dicUsers[thrCurrent] > 0:
                if self.__debug:
                    assert self._invariant(), "SharedLock invariant failed: %s in %s" % \
                                              (self._debug_dump(), "")
                if self.__log: self._log("released shared")
                return
            else:
                del self.dicUsers[thrCurrent]

            # a decision is made which pending thread(s) to awake (if any)

            self._release_threads()

            if self.__debug:
                assert self._invariant(), "SharedLock invariant failed: %s in %s" % \
                                          (self._debug_dump(), "")
            if self.__log: self._log("released shared")

        finally:
            self._unlock()

################################################################################

if __name__ == "__main__":

    print "self-testing module shared_lock.py:"

    from threading import Thread
    from time import sleep, time
    from random import random
    from math import log10

    log_lock = Lock()
    def log(s):
        log_lock.acquire()
        try:
            print s
        finally:
            log_lock.release()

    def deadlocks(f, t):
        th = Thread(target = f)
        th.setName("Thread")
        th.setDaemon(1)
        th.start()
        th.join(t)
        return th.isAlive()

    def threads(n, *f):
        start = time()
        evt = Event()
        ths = [ Thread(target = f[i % len(f)], args = (evt, )) for i in range(n) ]
        for i, th in enumerate(ths):
            th.setDaemon(1)
            th.setName(f[i % len(f)].__name__)
            th.start()
        evt.set()
        for th in ths:
            th.join()
        return time() - start

    # simple test

    print "simple test:",

    currentThread().setName("MainThread")

    lck = SharedLock(None, True)
    assert lck.debug_dump() == "SharedLock(Ex:[] (), Sh:[] ())"

    assert lck.acquire()
    assert lck.debug_dump() == "SharedLock(Ex:[MainThread:1] (), Sh:[] ())"
    lck.release()
    assert lck.debug_dump() == "SharedLock(Ex:[] (), Sh:[] ())"

    assert lck.acquire_shared()
    assert lck.debug_dump() == "SharedLock(Ex:[] (), Sh:[MainThread:1] ())"
    lck.release_shared()
    assert lck.debug_dump() == "SharedLock(Ex:[] (), Sh:[] ())"

    try:
        lck.release()
    except Exception, e:
        assert str(e) == "Current thread has not acquired the lock"
    else:
        assert False

    try:
        lck.release_shared()
    except Exception, e:
        assert str(e) == "Current thread has not acquired the lock"
    else:
        assert False

    print "ok"

    # recursion test

    print "recursive lock test:",

    lck = SharedLock(None, True)

    assert lck.acquire()
    assert lck.acquire()
    assert lck.debug_dump() == "SharedLock(Ex:[MainThread:2] (), Sh:[] ())"
    lck.release()
    assert lck.debug_dump() == "SharedLock(Ex:[MainThread:1] (), Sh:[] ())"
    lck.release()

    assert lck.acquire_shared()
    assert lck.acquire_shared()
    assert lck.debug_dump() == "SharedLock(Ex:[] (), Sh:[MainThread:2] ())"
    lck.release_shared()
    assert lck.debug_dump() == "SharedLock(Ex:[] (), Sh:[MainThread:1] ())"
    lck.release_shared()

    print "ok"

    # same thread shared/exclusive upgrade test

    print "same thread shared/exclusive upgrade test:",

    lck = SharedLock(None, True)

    def upgrade():

        # ex -> sh <- sh <- ex

        assert lck.debug_dump() == "SharedLock(Ex:[] (), Sh:[] ())"
        assert lck.acquire()
        assert lck.debug_dump() == "SharedLock(Ex:[Thread:1] (), Sh:[] ())"
        assert lck.acquire_shared()
        assert lck.debug_dump() == "SharedLock(Ex:[Thread:1] (), Sh:[Thread:1] ())"
        lck.release_shared()
        assert lck.debug_dump() == "SharedLock(Ex:[Thread:1] (), Sh:[] ())"
        lck.release()
        assert lck.debug_dump() == "SharedLock(Ex:[] (), Sh:[] ())"

        # ex -> sh <- ex <- sh

        assert lck.debug_dump() == "SharedLock(Ex:[] (), Sh:[] ())"
        assert lck.acquire()
        assert lck.debug_dump() == "SharedLock(Ex:[Thread:1] (), Sh:[] ())"
        assert lck.acquire_shared()
        assert lck.debug_dump() == "SharedLock(Ex:[Thread:1] (), Sh:[Thread:1] ())"
        lck.release()
        assert lck.debug_dump() == "SharedLock(Ex:[] (), Sh:[Thread:1] ())"
        lck.release_shared()
        assert lck.debug_dump() == "SharedLock(Ex:[] (), Sh:[] ())"

        # sh -> ex <- ex <- sh

        assert lck.debug_dump() == "SharedLock(Ex:[] (), Sh:[] ())"
        assert lck.acquire_shared()
        assert lck.debug_dump() == "SharedLock(Ex:[] (), Sh:[Thread:1] ())"
        assert lck.acquire()
        assert lck.debug_dump() == "SharedLock(Ex:[Thread:1] (), Sh:[Thread:1] ())"
        lck.release()
        assert lck.debug_dump() == "SharedLock(Ex:[] (), Sh:[Thread:1] ())"
        lck.release_shared()
        assert lck.debug_dump() == "SharedLock(Ex:[] (), Sh:[] ())"

        # sh -> ex <- sh <- ex

        assert lck.debug_dump() == "SharedLock(Ex:[] (), Sh:[] ())"
        assert lck.acquire_shared()
        assert lck.debug_dump() == "SharedLock(Ex:[] (), Sh:[Thread:1] ())"
        assert lck.acquire()
        assert lck.debug_dump() == "SharedLock(Ex:[Thread:1] (), Sh:[Thread:1] ())"
        lck.release_shared()
        assert lck.debug_dump() == "SharedLock(Ex:[Thread:1] (), Sh:[] ())"
        lck.release()
        assert lck.debug_dump() == "SharedLock(Ex:[] (), Sh:[] ())"

    assert not deadlocks(upgrade, 2.0)

    print "ok"

    # timeout test

    print "timeout test:",

    # exclusive/exclusive timeout

    lck = SharedLock(None, True)

    def f(evt):
        evt.wait()
        assert lck.acquire()
        assert lck.debug_dump() == "SharedLock(Ex:[f:1] (), Sh:[] ())"
        sleep(1.0)
        assert lck.debug_dump() == "SharedLock(Ex:[f:1] (g:0), Sh:[] ())"
        lck.release()

    def g(evt):
        evt.wait()
        sleep(0.5)
        assert lck.debug_dump() == "SharedLock(Ex:[f:1] (), Sh:[] ())"
        assert not lck.acquire(0.1)
        assert lck.debug_dump() == "SharedLock(Ex:[f:1] (), Sh:[] ())"
        assert lck.acquire(0.5)
        assert lck.debug_dump() == "SharedLock(Ex:[g:1] (), Sh:[] ())"
        lck.release()

    threads(2, f, g)

    # shared/shared no timeout

    lck = SharedLock(None, True)

    def f(evt):
        evt.wait()
        assert lck.acquire_shared()
        assert lck.debug_dump() == "SharedLock(Ex:[] (), Sh:[f:1] ())"
        sleep(1.0)
        assert lck.debug_dump() == "SharedLock(Ex:[] (), Sh:[f:1] ())"
        lck.release_shared()

    def g(evt):
        evt.wait()
        sleep(0.5)
        assert lck.debug_dump() == "SharedLock(Ex:[] (), Sh:[f:1] ())"
        assert lck.acquire_shared(0.1)
        assert lck.debug_dump() == "SharedLock(Ex:[] (), Sh:[f:1, g:1] ())"
        lck.release_shared()

    threads(2, f, g)

    # exclusive/shared timeout

    lck = SharedLock(None, True)

    def f(evt):
        evt.wait()
        assert lck.acquire()
        assert lck.debug_dump() == "SharedLock(Ex:[f:1] (), Sh:[] ())"
        sleep(1.0)
        assert lck.debug_dump() == "SharedLock(Ex:[f:1] (), Sh:[] (g:1))"
        lck.release()

    def g(evt):
        evt.wait()
        sleep(0.5)
        assert lck.debug_dump() == "SharedLock(Ex:[f:1] (), Sh:[] ())"
        assert not lck.acquire_shared(0.1)
        assert lck.debug_dump() == "SharedLock(Ex:[f:1] (), Sh:[] ())"
        assert lck.acquire_shared(0.5)
        assert lck.debug_dump() == "SharedLock(Ex:[] (), Sh:[g:1] ())"
        lck.release_shared()

    threads(2, f, g)

    # shared/exclusive timeout

    lck = SharedLock(None, True)

    def f(evt):
        evt.wait()
        assert lck.acquire_shared()
        assert lck.debug_dump() == "SharedLock(Ex:[] (), Sh:[f:1] ())"
        sleep(1.0)
        assert lck.debug_dump() == "SharedLock(Ex:[] (g:0), Sh:[f:1] ())"
        lck.release_shared()

    def g(evt):
        evt.wait()
        sleep(0.5)
        assert lck.debug_dump() == "SharedLock(Ex:[] (), Sh:[f:1] ())"
        assert not lck.acquire(0.1)
        assert lck.debug_dump() == "SharedLock(Ex:[] (), Sh:[f:1] ())"
        assert lck.acquire(0.5)
        assert lck.debug_dump() == "SharedLock(Ex:[g:1] (), Sh:[] ())"
        lck.release()

    threads(2, f, g)

    # re-acquiring previously owned shared locks after an upgrade timeout

    lck = SharedLock(None, True)

    def f(evt):
        evt.wait()
        lck.acquire_shared()
        assert lck.debug_dump() == "SharedLock(Ex:[] (), Sh:[f:1] ())"
        sleep(1.0)
        start = time()
        assert not lck.acquire(0.1) # this locks for more than 0.1 sec.
        assert time() - start > 1.0
        assert lck.debug_dump() == "SharedLock(Ex:[] (), Sh:[f:1] ())"

    def g(evt):
        evt.wait()
        sleep(0.5)
        assert lck.debug_dump() == "SharedLock(Ex:[] (), Sh:[f:1] ())"
        lck.acquire()
        assert lck.debug_dump() == "SharedLock(Ex:[g:1] (f:1), Sh:[] ())"
        sleep(1.1)
        lck.release()

    threads(2, f, g)

    print "ok"

    # different threads shared/exclusive upgrade test

    print "different threads shared/exclusive upgrade test:",

    lck = SharedLock(None, True)

    def f(evt):
        evt.wait()

        assert lck.debug_dump() == "SharedLock(Ex:[] (), Sh:[] ())"
        lck.acquire_shared()
        assert lck.debug_dump() == "SharedLock(Ex:[] (), Sh:[f:1] ())"

        sleep(3.0)

        lck.release_shared()

    def g(evt):
        evt.wait()

        sleep(1.0)

        assert lck.debug_dump() == "SharedLock(Ex:[] (), Sh:[f:1] ())"
        lck.acquire_shared()
        assert lck.debug_dump() == "SharedLock(Ex:[] (), Sh:[f:1, g:1] ())"

        sleep(3.0)

        assert lck.debug_dump() == "SharedLock(Ex:[] (h:0), Sh:[g:1] ())"
        lck.acquire()
        assert lck.debug_dump() == "SharedLock(Ex:[g:1] (), Sh:[g:1] ())"

        lck.release()
        lck.release_shared()

    def h(evt):
        evt.wait()

        sleep(2.0)

        assert lck.debug_dump() == "SharedLock(Ex:[] (), Sh:[f:1, g:1] ())"
        lck.acquire()
        assert lck.debug_dump() == "SharedLock(Ex:[h:1] (g:1), Sh:[] ())"

        sleep(1.0)

        lck.release()

    threads(3, f, g, h)

    print "ok"

    # different threads exclusive/exclusive deadlock test

    print "different threads exclusive/exclusive deadlock test:",

    lck = SharedLock(None, True)

    def deadlock(evt):
        lck.acquire()

    assert deadlocks(lambda: threads(2, deadlock), 2.0)

    print "ok"

    # different thread shared/exclusive deadlock test

    print "different threads shared/exclusive deadlock test:",

    lck = SharedLock(None, True)

    def deadlock1(evt):
        lck.acquire()

    def deadlock2(evt):
        lck.acquire_shared()

    assert deadlocks(lambda: threads(2, deadlock1, deadlock2), 2.0)

    print "ok"

    # different thread shared/shared deadlock test

    print "different threads shared/shared no deadlock test:",

    lck = SharedLock(None, True)

    def deadlock(evt):
        lck.acquire_shared()

    assert not deadlocks(lambda: threads(2, deadlock), 2.0)

    print "ok"

    # cross upgrade test

    print "different threads cross upgrade test:",

    lck = SharedLock(None, True)

    def cross(evt):
        lck.acquire_shared()
        sleep(1.0)
        lck.acquire()
        lck.release()
        lck.release_shared()

    assert not deadlocks(lambda: threads(2, cross), 2.0)

    print "ok"

    # exclusive interlock + timing test

    print "exclusive interlock + serialized timing test:",

    lck = SharedLock(None, True)
    val = 0

    def exclusive(evt):
        evt.wait()
        global val
        for i in range(10):
            lck.acquire()
            try:
                assert val == 0
                val += 1
                sleep(0.05 + random() * 0.05)
                assert val == 1
                val -= 1
                sleep(0.05 + random() * 0.05)
                assert val == 0
            finally:
                lck.release()

    assert threads(4, exclusive) > 0.05 * 2 * 10 * 4

    print "ok"

    # shared non-interlock timing test

    print "shared parallel timing test:",

    lck = SharedLock(None, True)

    def shared(evt):
        evt.wait()
        for i in range(10):
            lck.acquire_shared()
            try:
                sleep(0.1)
            finally:
                lck.release_shared()

    assert threads(10, shared) < 0.1 * 10 + 4.0

    print "ok"

    # shared/exclusive test

    print "multiple exclusive/shared threads busy loops:"

    lck, shlck = SharedLock(None, True), Lock()

    ex, sh, start, t = 0, 0, time(), 10.0

    def exclusive(evt):
        global ex, start, t
        evt.wait()
        i = 0
        while i % 100 != 0 or start + t > time():
            i += 1
            lck.acquire()
            try:
                ex += 1
            finally:
                lck.release()

    def shared(evt):
        global sh, start, t
        evt.wait()
        i = 0
        while i % 100 != 0 or start + t > time():
            i += 1
            lck.acquire_shared()
            try:
                shlck.acquire()
                try:
                    sh += 1
                finally:
                    shlck.release()
            finally:
                lck.release_shared()

    # even distribution

    print "2ex/2sh:",
    ex, sh, start = 0, 0, time()
    assert 10.0 < threads(4, exclusive, exclusive, shared, shared) < 12.0
    print "%d/%d:" % (ex, sh),
    assert abs(log10(float(ex) / float(sh))) < 1.3

    print "ok"

    # exclusive starvation

    print "1ex/3sh:",
    ex, sh, start = 0, 0, time()
    assert 10.0 < threads(4, exclusive, shared, shared, shared) < 12.0
    print "%d/%d:" % (ex, sh),
    assert abs(log10(float(ex) / float(sh))) < 1.3

    print "ok"

    # shared starvation

    print "3ex/1sh:",
    ex, sh, start = 0, 0, time()
    assert 10.0 < threads(4, exclusive, exclusive, exclusive, shared) < 12.0
    print "%d/%d:" % (ex, sh),
    assert abs(log10(float(ex) / float(sh))) < 1.3

    print "ok"

    # heavy threading test

    print "exhaustive threaded test (30 seconds):",

    lck = SharedLock(None, True)
    start, t = time(), 30.0

    def f(evt):
        global start, t
        evt.wait()
        while start + t > time():

            sleep(random() * 0.1)

            j = randint(0, 1)
            if j == 0:
                jack = lck.acquire(*(randint(0, 1) == 0 and (random(), ) or ()))
            else:
                jack = lck.acquire_shared(*(randint(0, 1) == 0 and (random(), ) or ()))

            sleep(random() * 0.1)

            k = randint(0, 1)
            if k == 0:
                kack = lck.acquire(*(randint(0, 1) == 0 and (random(), ) or ()))
            else:
                kack = lck.acquire_shared(*(randint(0, 1) == 0 and (random(), ) or ()))

            sleep(random() * 0.1)

            l = randint(0, 1)
            if l == 0:
                lack = lck.acquire(*(randint(0, 1) == 0 and (random(), ) or ()))
            else:
                lack = lck.acquire_shared(*(randint(0, 1) == 0 and (random(), ) or ()))

            sleep(random() * 0.1)

            if lack:
                if l == 0:
                    lck.release()
                else:
                    lck.release_shared()

            sleep(random() * 0.1)

            if kack:
                if k == 0:
                    lck.release()
                else:
                    lck.release_shared()

            sleep(random() * 0.1)

            if jack:
                if j == 0:
                    lck.release()
                else:
                    lck.release_shared()

    f0 = lambda evt: f(evt);
    f1 = lambda evt: f(evt);
    f2 = lambda evt: f(evt);
    f3 = lambda evt: f(evt);
    f4 = lambda evt: f(evt);
    f5 = lambda evt: f(evt);
    f6 = lambda evt: f(evt);
    f7 = lambda evt: f(evt);
    f8 = lambda evt: f(evt);
    f9 = lambda evt: f(evt);

    threads(10, f0, f1, f2, f3, f4, f5, f6, f7, f8, f9)

    print "ok"

    # specific anti-owners scenario (users cooperate by passing the lock
    # to each other to make owner starve to death)

    print "shareds cooperate in attempt to make exclusive starve to death:",

    lck, shlck, hold = SharedLock(None, True), Lock(), 0
    evtlock, stop = Event(), Event()

    def user(evt):

        evt.wait()

        try:

            while not stop.isSet():

                lck.acquire_shared()
                try:

                    evtlock.set()

                    shlck.acquire()
                    try:
                        global hold
                        hold += 1
                    finally:
                        shlck.release()

                    sleep(random() * 0.4)

                    waited = time()
                    while time() - waited < 3.0:
                        shlck.acquire()
                        try:
                            if hold > 1:
                                hold -= 1
                                break
                        finally:
                            shlck.release()

                    if time() - waited >= 3.0: # but in turn they lock themselves
                        raise Exception("didn't work")

                finally:
                    lck.release_shared()

                sleep(random() * 0.1)

        except Exception, e:
            assert str(e) == "didn't work"

    def owner(evt):
        evt.wait()
        evtlock.wait()
        lck.acquire()
        lck.release()
        stop.set()

    assert not deadlocks(lambda: threads(5, owner, user, user, user, user), 10.0)

    print "ok"

    print "benchmark:",

    lck, ii = SharedLock(), 0

    start = time()
    while time() - start < 5.0:
        for i in xrange(100):
            lck.acquire()
            lck.release()
            ii += 1

    print "%d empty lock/unlock cycles per second" % (ii / 5),

    print "ok"

    # all ok

    print "all ok"

################################################################################
# EOF

########NEW FILE########
__FILENAME__ = clojure
import clojure.main

if __name__ == "__main__":
    clojure.main.main()

########NEW FILE########
__FILENAME__ = factorial
def fact(x):
    f = 1
    n = x
    while True:
        if n == 1:
            return f
        else:
            f = f * n
            n = n - 1
            continue


def test(times):
    rem = times
    while True:
        if rem > 0:
            fact(20)
            rem = rem - 1
            continue
        else:
            return

import time
c = time.time()
test(19999999)
print "Elapsed time: " + str((time.time() - c) * 1000) + " msecs"

########NEW FILE########
__FILENAME__ = bootstrap
import clojure
import rpythontest
import sys
fn = rpythontest.main.deref()


def entry_point(argv):
    print fn(0)
    return 2

def target(*args):
    return entry_point, None
    
if __name__ == "__main__":
    entry_point(sys.argv)

########NEW FILE########
__FILENAME__ = bootstrap-clj-tests
import os.path
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import unittest

from clojure.lang.cljkeyword import Keyword
from clojure.lang.namespace import Namespace, findItem
from clojure.lang.var import Var, threadBindings
from clojure.lang.symbol import Symbol
from clojure.main import requireClj


_NS_ = findItem(Namespace("clojure.core"), Symbol("*ns*"))


def mapTest(ns, var):
    class Test(unittest.TestCase):
        def testVar(self):
            with threadBindings({_NS_: var.ns}):
                var()

    name = ns + str(var)
    tst = Test
    tst.__name__ = name
    globals()[name] = tst


for x in os.listdir(os.path.dirname(__file__)):
    if x.endswith(".clj") and x.find("test") >= 0:
        print "Reading tests from",  x
        requireClj(os.path.join(os.path.dirname(__file__),x))
        folder, file = os.path.split(x)
        ns, ext = os.path.splitext(x)
        module = sys.modules["tests."+ns]

        for idx in dir(module):
            var = getattr(module, idx)
            if isinstance(var, Var) and str(var).endswith("tests"):
                meta = var.meta()
                if meta and meta[Keyword("test")]:
                    mapTest(ns, var) 


########NEW FILE########
__FILENAME__ = cons_tests
"""cons_tests.py

Friday, March 30 2012
"""

import re
import unittest
from cStringIO import StringIO

from clojure.lang.iseq import ISeq
from clojure.lang.cons import Cons
import clojure.lang.persistentlist as pl
from clojure.lang.persistentlist import EmptyList
from clojure.lang.cljexceptions import ArityException

uobj = object()
pseudoMetaData = object()

class TestCons(unittest.TestCase):
    def setUp(self):
        # if this raises no exceptions, the others will validate creation
        self.head = "head"
        self.t1 = pl.creator(uobj)
        self.t2 = pl.creator(0, uobj)
        self.t3 = pl.creator(0, 1, uobj)
        self.c1 = Cons(self.head, None)
        self.c2 = Cons(self.head, self.t1)
        # e.g. ("head" 0 uobj)
        self.c3 = Cons(self.head, self.t2)
        self.c4 = Cons(self.head, self.t3)
        # just checking printed structure
        self.printS = Cons(pl.creator(1, 2),
                           pl.creator(pl.creator(3, 4)))
    def test__init___FAIL(self):
        self.assertRaises(ArityException, Cons)
        self.assertRaises(ArityException, Cons, 1, 2, 3, 4)
    # next()
    def testNext_PASS(self):
        c = self.c2.next()
        self.assertTrue(isinstance(c, ISeq))
        self.assertEqual(c.next(), None)
    # first()
    def testFirst_PASS(self):
        self.assertEqual(self.c1.first(), "head")
    # __len__
    def test__len___PASS(self):
        self.assertEqual(self.c1.__len__(), 1)
        self.assertEqual(self.c2.__len__(), 2)
        self.assertEqual(self.c3.__len__(), 3)
        self.assertEqual(self.c4.__len__(), 4)
    # withMeta()
    def testWithMeta_PASS(self):
        c2 = self.c2.withMeta(pseudoMetaData)
        self.assertEqual(c2.meta(), pseudoMetaData)
    # (print s)
    def testWriteAsString_PASS(self):
        csio = StringIO()
        self.printS.writeAsString(csio)
        self.assertEqual(csio.getvalue(), "((1 2) (3 4))")
    # (pr s)
    def testWriteAsReplString_PASS(self):
        csio = StringIO()
        self.printS.writeAsReplString(csio)
        self.assertEqual(csio.getvalue(), "((1 2) (3 4))")
    # str(s)
    def test__str___PASS(self):
        self.assertEqual(self.printS.__str__(), "((1, 2), (3, 4))")
    # make sure the correct namespace is printed
    # repr(s)
    def test__repr___PASS(self):
        regex = r"<clojure\.lang\.cons\.Cons" \
                r" object at 0x[a-fA-F0-9]+ \(\(1 2\) \(3 4\)\)>$"
        self.assertTrue(re.match(regex, self.printS.__repr__()))

########NEW FILE########
__FILENAME__ = emptylist_tests
"""emptylist_tests.py

Thursday, March 29 2012
"""

import unittest
from cStringIO import StringIO

from clojure.lang.persistentlist import EMPTY, EmptyList
from clojure.lang.cljexceptions import IllegalStateException

uobj = object()
pseudoMetaData = object()

class EmptyListTests(unittest.TestCase):
    def setUp(self):
        pass
    def test__hash___PASS(self):
        self.assertEqual(EMPTY.__hash__(), 1)
    # only basic equality tests here
    def test__eq___PASS(self):
        self.assertTrue(EMPTY.__eq__(EMPTY))
        self.assertTrue(EMPTY.__eq__(()))
        self.assertTrue(EMPTY.__eq__([]))
    def test__ne___PASS(self):
        self.assertFalse(EMPTY.__ne__(EMPTY))
        self.assertFalse(EMPTY.__ne__(()))
        self.assertFalse(EMPTY.__ne__([]))
    def test__iter___PASS(self):
        self.assertEqual(EMPTY.__iter__(), None)
    def testWithMeta_PASS(self):
        l1 = EMPTY.withMeta(pseudoMetaData)
        l2 = l1.withMeta(uobj)
        self.assertFalse(l1.meta() is l2.meta())
        # equal with different meta data
        self.assertTrue(l1.__eq__(l2))
    def testFirst_PASS(self):
        self.assertEqual(EMPTY.first(), None)
    def testNext_PASS(self):
        self.assertEqual(EMPTY.next(), None)
    def testMore_PASS(self):
        self.assertTrue(EMPTY.more() is EMPTY)
    def testCons_PASS(self):
        l = EMPTY.cons(uobj)
        self.assertFalse(EMPTY is l)
        self.assertEqual(len(l), 1)
        self.assertEqual(l.first(), uobj)
    def testEmpty_PASS(self):
        self.assertTrue(EMPTY.empty() is EMPTY)
    def testPeek_PASS(self):
        self.assertEqual(EMPTY.peek(), None)
    def testPop_FAIL(self):
        self.assertRaises(IllegalStateException, EMPTY.pop)
    def testCount_PASS(self):
        self.assertEqual(EMPTY.count(), 0)
    def testSeq_PASS(self):
        self.assertEqual(EMPTY.seq(), None)
    def testWriteAsString_PASS(self):
        sio = StringIO()
        EMPTY.writeAsString(sio)
        self.assertEqual(sio.getvalue(), "()")
    def testWriteAsReplString_PASS(self):
        sio = StringIO()
        EMPTY.writeAsReplString(sio)
        self.assertEqual(sio.getvalue(), "()")
    def test__str___PASS(self):
        self.assertEqual(str(EMPTY), "()")
    def test__repr___PASS(self):
        self.assertEqual(repr(EMPTY), "()")
    def test__len___PASS(self):
        self.assertEqual(EMPTY.__len__(), 0)
    

########NEW FILE########
__FILENAME__ = mapentry_tests
"""mapentry_tests.py

Wednesday, March 28 2012
"""

import unittest

import clojure.lang.mapentry as me
from clojure.lang.iseq import ISeq
from clojure.lang.apersistentvector import SubVec
from clojure.lang.persistentvector import PersistentVector
from clojure.lang.cljexceptions import IndexOutOfBoundsException


class TestMapEntry(unittest.TestCase):
    def setUp(self):
        self.mapEntry = me.MapEntry("key", "value")
    def testGetKey_PASS(self):
        self.assertEqual(self.mapEntry.getKey(), "key")
    def testGetValue_PASS(self):
        self.assertEqual(self.mapEntry.getValue(), "value")
    def test__getitem___PASS(self):
        self.assertEqual(self.mapEntry[0], "key")
        self.assertEqual(self.mapEntry[1], "value")
    def test__getitem___FAIL(self):
        self.assertRaises(IndexOutOfBoundsException,
                          self.mapEntry.__getitem__, -1)
        self.assertRaises(IndexOutOfBoundsException,
                          self.mapEntry.__getitem__, 2)
    def testAsVector_PASS(self):
        v = self.mapEntry.asVector()
        self.assertTrue(isinstance(v, PersistentVector))
        self.assertEqual(len(v), 2)
        self.assertEqual(v.nth(0), "key")
        self.assertEqual(v.nth(1), "value")
    def testAssocN_PASS(self):
        v1 = self.mapEntry.assocN(0, "yek")
        self.assertTrue(isinstance(v1, PersistentVector))
        self.assertEqual(len(v1), 2)
        self.assertEqual(v1.nth(0), "yek")
        self.assertEqual(v1.nth(1), "value")
        v2 = self.mapEntry.assocN(1, "eulav")
        self.assertTrue(isinstance(v2, PersistentVector))
        self.assertEqual(len(v2), 2)
        self.assertEqual(v2.nth(0), "key")
        self.assertEqual(v2.nth(1), "eulav")
    def testAssocN_FAIL(self):
        self.assertRaises(IndexOutOfBoundsException,
                          self.mapEntry.assocN, 3, "yek")
    def test__len___Pass(self):
        self.assertEqual(len(self.mapEntry), 2)
    def test__contains___Pass(self):
        self.assertTrue(0 in self.mapEntry)
        self.assertTrue(1 in self.mapEntry)
    def testSeq_PASS(self):
        s = self.mapEntry.seq()
        self.assertTrue(isinstance(s, ISeq))
        self.assertTrue(len(s), 2)
        self.assertTrue(s.first(), "key")
        self.assertTrue(s.next().first(), "value")
    def testCons_PASS(self):
        v = self.mapEntry.cons("foo")
        self.assertTrue(isinstance(v, PersistentVector))
        self.assertEqual(len(v), 3)
        self.assertEqual(v.nth(0), "key")
        self.assertEqual(v.nth(1), "value")
        self.assertEqual(v.nth(2), "foo")
    def testEmpty_PASS(self):
        self.assertEqual(self.mapEntry.empty(), None)
    def testPop_PASS(self):
        v = self.mapEntry.pop()
        self.assertTrue(isinstance(v, PersistentVector))
        self.assertEqual(len(v), 1)
        self.assertEqual(v.nth(0), "key")



########NEW FILE########
__FILENAME__ = new_style_class_audit
## This script will attempt to audit the enitre clojure.lang namespace and insure
## that all classes implement newstyle classes.
import clojure
import clojure.lang
import new
passed = []
failed = []

for module in dir(clojure.lang): # modules
    mod = getattr(clojure.lang, module)
    for itm in dir(mod):
        i = getattr(mod, itm)
        if isinstance(i, new.classobj):
            print module, itm, "FAILED"
            failed.append(i)
        elif isinstance(i, type):
            passed.append([module, itm, ">>>>> PASSED <<<<"])
            
print 
print len(failed), " FAILED"            
print len(passed), " PASSED"
        

########NEW FILE########
__FILENAME__ = persistenthashset_tests
"""persistenthashset_tests.py

Friday, March 30 2012
"""

import re
import unittest
from cStringIO import StringIO

from clojure.lang.iseq import ISeq
from clojure.lang.persistenthashset import PersistentHashSet
from clojure.lang.persistenthashset import create, createWithCheck
from clojure.lang.persistenthashset import EMPTY_MAP, EMPTY as EMPTY_SET
from clojure.lang.cljexceptions import (ArityException,
                                        IllegalArgumentException)

uobj = object()
pseudoMetaData = object()

def sethash(s):
    """Duplicate APersistentSet.__hash__().  This is as useless as the other
    hash *tests*. It's more of a bookmark than anything."""
    hsh = 0
    s = s.seq()
    while s is not None:
        e = s.first()
        if isinstance(e, PersistentHashSet):
            hsh += sethash(e)
        else:
            hsh += hash(e)
        s = s.next()
    return hsh

class TestPersistentHashSet(unittest.TestCase):
    def setUp(self):
        self.s0 = EMPTY_SET
        self.s2 = create(1, uobj)
        self.printS = create(1, self.s0)
    # cons()
    def testCons_PASS(self):
        s1 = self.s0.cons(uobj)
        self.assertEqual(len(s1), 1)
        # silent omission of the duplicate, same as Clojure
        s1_1 = s1.cons(uobj)
        self.assertEqual(len(s1_1), 1)
    # meta()
    def testMeta_PASS(self):
        self.assertEqual(self.s0.meta(), None)
        s0meta = PersistentHashSet(pseudoMetaData, EMPTY_MAP)
        self.assertEqual(s0meta.meta(), pseudoMetaData)
    # withMeta()
    def testWithMeta_PASS(self):
        s0meta = self.s0.withMeta(pseudoMetaData)
        self.assertTrue(s0meta is not self.s0)
        self.assertTrue(s0meta.meta() is not self.s0.meta())
        self.assertEqual(s0meta.meta(), pseudoMetaData)
    # empty()
    def testEmpty_PASS(self):
        s1 = self.s0.cons(uobj)
        s1empty = s1.empty()
        self.assertTrue(s1empty is not s1)
        self.assertEqual(len(s1empty), 0)
    # disjoin()
    def testDisjoin_PASS(self):
        s1 = self.s0.cons(uobj)
        # key not a member, return self
        s0 = s1.disjoin("foo")
        self.assertTrue(s0 is s1)
        self.assertEqual(len(s0), 1)
        # key found
        s0 = s1.disjoin(uobj)
        self.assertTrue(s0 is not s1)
        self.assertEqual(len(s0), 0)
    # create()
    def testCreate_PASS(self):
        s3 = create("foo", 3.0, 9)
        self.assertEqual(len(s3), 3)
        # TODO: how shall we handle this difference from Clojure?
        # s3 = create("foo", 3.0, 3)
        # self.assertEqual(len(s3), 3)   # => 2, not 3
    # createWithCheck()
    def testCreateWithCheck_PASS(self):
        s3 = createWithCheck(["foo", 3.0, 9])
        self.assertEqual(len(s3), 3)
    def testCreateWithCheck_FAIL(self):
        self.assertRaises(IllegalArgumentException, createWithCheck, [9, 9])

    # APersistentSet methods

    # __getitem__()
    def test__getitem___PASS(self):
        self.assertEqual(self.s2.__getitem__(uobj), uobj)
        self.assertEqual(self.s2.__getitem__("foo"), None)
    # __contains__()
    def test__getitem___PASS(self):
        self.assertTrue(self.s2.__contains__(uobj))
        self.assertFalse(self.s2.__contains__("foo"))
        self.assertFalse(self.s0.__contains__("foo"))
    # __len__()
    def test__len___PASS(self):
        self.assertEqual(self.s0.__len__(), 0)
        self.assertEqual(self.s2.__len__(), 2)
    # seq()
    def testSeq_PASS(self):
        self.assertEqual(self.s0.seq(), None)
        seq = self.s2.seq()
        self.assertTrue(isinstance(seq, ISeq))
        first = seq.first()
        second = seq.next().first()
        self.assertTrue(first == 1 or first == uobj)
        self.assertTrue(second == 1 or second == uobj)
        self.assertTrue(second != first)
    # __call__()
    def test__call___PASS(self):
        self.assertEqual(self.s2.__call__(uobj), uobj)
        self.assertFalse(self.s0.__call__(None))
    def test__call___FAIL(self):
        # not enough args
        self.assertRaises(ArityException, self.s0.__call__)
        # too many
        self.assertRaises(ArityException, self.s0.__call__, 1, 2)
    # TODO: check equality again
    def test__eq___PASS(self):
        # simple tests here
        self.assertTrue(self.s2.__eq__(self.s2))
        self.assertFalse(self.s2.__eq__("foo"))
        self.assertTrue(self.s2.__eq__(create(1, uobj)))
        self.assertTrue(self.s2.__eq__(create(uobj, 1)))
    # TODO: check hash again
    def test__hash___PASS(self):
        s = create(1, 2, "foo", 3.3, create(1, 2, "bar"))
        self.assertEqual(s.__hash__(), sethash(s))
    # (print s)
    def testWriteAsString_PASS(self):
        csio = StringIO()
        self.printS.writeAsString(csio)
        outstr = csio.getvalue()
        self.assertTrue(outstr == "#{1 #{}}" or outstr == "#{#{} 1}")
    # (pr s)
    def testWriteAsReplString_PASS(self):
        csio = StringIO()
        self.printS.writeAsReplString(csio)
        outstr = csio.getvalue()
        self.assertTrue(outstr == "#{1 #{}}" or outstr == "#{#{} 1}")
    # str(s)
    def test__str___PASS(self):
        outstr = self.printS.__str__()
        self.assertTrue(outstr == "set([1, set()])"
                        or outstr == "set([set(), 1])")
    # repr(s)
    def test__repr___PASS(self):
        regex = r"<clojure\.lang\.persistenthashset\.PersistentHashSet" \
                r" object at 0x[a-fA-F0-9]+" \
                r" (#\{#\{\} 1\}|#\{1 #\{\}\})>$"
        self.assertTrue(re.match(regex, self.printS.__repr__()))

########NEW FILE########
__FILENAME__ = persistentlist_tests
"""persistentlist_tests.py

Thursday, March 29 2012
"""

import re
import unittest
import operator
from cStringIO import StringIO

from clojure.lang.iseq import ISeq
import clojure.lang.persistentlist as pl
from clojure.lang.persistentlist import PersistentList, EmptyList
from clojure.lang.cljexceptions import (ArityException,
                                        IndexOutOfBoundsException)

uobj = object()
pseudoMetaData = object()

def seqHash(v):
    """Duplicates ASeq.hasheq()"""
    h = 1
    for e in v:
        h = 31 * h + hash(e)
    return h

class TestPersistentList(unittest.TestCase):
    def setUp(self):
        # if this raises no exceptions, the others will validate creation
        self.l0 = pl.creator()
        self.l1 = pl.creator(uobj)
        self.l2 = pl.creator(0, uobj)
        self.l3 = pl.creator(0, 1, uobj)
        self.lR = pl.creator(1, 2, 3, 4, 5) # for reduce test
        # just checking printed structure
        self.printS = pl.creator(pl.creator(1, 2),
                                 pl.creator(3, 4))
    # next()
    def testNext_PASS(self):
        l = self.l2.next()
        self.assertTrue(isinstance(l, ISeq))
        self.assertEqual(l.next(), None)
    # first()
    def testFirst_PASS(self):
        self.assertEqual(self.l0.first(), None)
        self.assertEqual(self.l1.first(), uobj)
    # peek()
    def testPeek_PASS(self):
        self.assertEqual(self.l0.peek(), None)
        self.assertEqual(self.l1.peek(), uobj)
    # pop()
    def testPop_PASS(self):
        l = self.l2.pop()
        self.assertEqual(len(l), 1)
        self.assertEqual(l.first(), uobj)
        self.assertTrue(isinstance(l.pop(), EmptyList))
        
    # No fail test for pop(). There is no empty PersistentList. It's an
    # EmptyList instance instead.
        
    # __len__
    def test__len___PASS(self):
        self.assertEqual(self.l0.__len__(), 0)
        self.assertEqual(self.l1.__len__(), 1)
        self.assertEqual(self.l2.__len__(), 2)
        self.assertEqual(self.l3.__len__(), 3)
    # cons()
    def testCons_PASS(self):
        l1 = self.l0.cons("consed")
        self.assertEqual(len(l1), 1)
        self.assertEqual(l1.first(), "consed")
        l2 = self.l1.cons("consed")
        self.assertEqual(len(l2), 2)
        self.assertEqual(l2.first(), "consed")
    # empty()
    def testEmpty_PASS(self):
        l0 = self.l3.empty()
        self.assertTrue(isinstance(l0, EmptyList))
        self.assertEqual(len(l0), 0)
    # reduce()
    def testReduce_PASS(self):
        # list with one item
        x = pl.creator(42).reduce(operator.add)
        self.assertEqual(x, 42)
        x = pl.creator(42).reduce(operator.add, 42)
        self.assertEqual(x, 84)
        x = pl.creator(42).reduce(operator.add, -42)
        self.assertEqual(x, 0)
        # list with more than one item
        x = self.lR.reduce(operator.add)
        self.assertEqual(x, 15)
        x = self.lR.reduce(operator.add, 5)
        self.assertEqual(x, 20)
        x = self.lR.reduce(operator.add, -15)
        self.assertEqual(x, 0)
        # Can't test an empty PersistentList because EmptyList has no reduce
        # method
    def testReduce_FAIL(self):
        # not enough arguments
        self.assertRaises(ArityException, self.l1.reduce)
        # too many
        self.assertRaises(ArityException, self.l1.reduce, 1, 2, 3)
    # withMeta()
    def testWithMeta_PASS(self):
        # return self
        l1 = self.l1.withMeta(pseudoMetaData)
        l2 = l1.withMeta(pseudoMetaData)
        self.assertTrue(l1 is l2)
        self.assertTrue(l1.meta() is l2.meta())
        # return new PersistentList
        l3 = self.l3.withMeta(uobj)
        self.assertTrue(l3 is not self.l3)
        self.assertTrue(uobj, l3.meta())

    # ASeq methods
        
    # TODO: check equality again
    # __eq__
    def test__eq___PASS(self):
        # only tests simple PersistentList's
        self.assertTrue(self.l1.__eq__(self.l1))
        self.assertTrue(self.l1.__eq__(pl.creator(uobj)))
    # __ne__
    def test__ne___PASS(self):
        # only tests simple PersistentList's
        self.assertFalse(self.l1.__ne__(self.l1))
        self.assertFalse(self.l1.__ne__(pl.creator(uobj)))
    # __getitem__
    def test__getitem___PASS(self):
        self.assertEqual(self.l3[0], 0)
        self.assertEqual(self.l3[1], 1)
        self.assertEqual(self.l3[2], uobj)
    #
    # XXX: These are broken
    # 
    # def test__getitem___FAIL(self):
    #     self.assertRaises(IndexOutOfBoundsException, self.l1.__getitem__, 1)
    #     self.assertRaises(IndexOutOfBoundsException, self.l1.__getitem__, -1)
    # seq()
    def testSeq_PASS(self):
        self.assertTrue(self.l1.seq() is self.l1)
    # more()
    def testMore_PASS(self):
        l1 = self.l2.more()
        self.assertEqual(l1.first(), uobj)
        l0 = self.l1.more()
        self.assertTrue(isinstance(l0, EmptyList))
    # __iter__()
    def test__iter___PASS(self):
        x, y, z = self.l3
        self.assertEqual(x, 0)
        self.assertEqual(y, 1)
        self.assertEqual(z, uobj)
    # TODO: check equality again
    def testHashEq_PASS(self):
        self.assertEqual(self.l1.hasheq(), seqHash(self.l1))
        self.assertEqual(self.l2.hasheq(), seqHash(self.l2))
        self.assertEqual(self.l3.hasheq(), seqHash(self.l3))
        self.assertEqual(self.lR.hasheq(), seqHash(self.lR))
    # (print s)
    def testWriteAsString_PASS(self):
        csio = StringIO()
        self.printS.writeAsString(csio)
        self.assertEqual(csio.getvalue(), "((1 2) (3 4))")
    # (pr s)
    def testWriteAsReplString_PASS(self):
        csio = StringIO()
        self.printS.writeAsReplString(csio)
        self.assertEqual(csio.getvalue(), "((1 2) (3 4))")
    # str(s)
    def test__str___PASS(self):
        self.assertEqual(self.printS.__str__(), "((1, 2), (3, 4))")
    # repr(s)
    def test__repr___PASS(self):
        regex = r"<clojure\.lang\.persistentlist\.PersistentList" \
                r" object at 0x[a-fA-F0-9]+ \(\(1 2\) \(3 4\)\)>$"
        self.assertTrue(re.match(regex, self.printS.__repr__()))

########NEW FILE########
__FILENAME__ = persistenttreemap-tests
from random import randint, shuffle
import unittest

from clojure.lang.persistenttreemap import PersistentTreeMap


class PersistentTreeMapTests(unittest.TestCase):
    def testScaling(self):
        m = PersistentTreeMap()
        ints = range(1000)
        shuffle(ints)
        for i in ints:
            m = m.assoc(i, randint(1, 10))
        self.assertEqual(m.count(), 1000)

    def testAddRemove(self):
        m = PersistentTreeMap()
        ints = range(100)
        shuffle(ints)
        for i in ints:
            m = m.assoc(i, randint(1, 10))
        for i in ints[:10]:
            m = m.without(i)
        self.assertEqual(m.count(), 90)

########NEW FILE########
__FILENAME__ = persistentvector_tests
"""persistentvector_tests.py

Wednesday, March 28 2012
"""

import re
import unittest
from cStringIO import StringIO

import clojure.lang.persistentvector as pv
from clojure.lang.indexableseq import IndexableSeq
from clojure.lang.cljexceptions import (IndexOutOfBoundsException,
                                        IllegalStateException)

uobj = object()
pseudoMetaData = object()

def vecHash(v):
    """Duplicates APersistentVector.__hash__"""
    h = 1
    for e in v:
        h = 31 * h + hash(e)
    return h

class TestPersistentVector(unittest.TestCase):
    def setUp(self):
        self.printV = pv.create(pv.EMPTY, pv.EMPTY)
        self.v3 = pv.vec(["x", "y", "z"])
    # vec(), create()
    def testCreation_PASS(self):
        for k, v in testCreationMap_PASS.items():
            self.assertEqual(k, v)
    # __init__() with meta data, empty()
    def testMetaData_PASS(self):
        for k, v in testMetaDataMap_PASS.items():
            self.assertEqual(k, v)
    # __call__()
    def testCall_PASS(self):
        for k, v in testCallMap_PASS.items():
            self.assertEqual(k, v)
    def testCall_FAIL(self):
        v = pv.vec([])
        # no default argument allowed
        self.assertRaises(IndexOutOfBoundsException, v.__call__, 0)
        self.assertRaises(IndexOutOfBoundsException, v.__call__, 99)
        self.assertRaises(IndexOutOfBoundsException, v.__call__, -323)
    # nth()
    def testNth_PASS(self):
        for k, v in testNthMap_PASS.items():
            self.assertEqual(k, v)
    def testNth_FAIL(self):
        v = pv.vec([])
        # no default argument given
        self.assertRaises(IndexOutOfBoundsException, v.nth, 0)
        self.assertRaises(IndexOutOfBoundsException, v.nth, 99)
        self.assertRaises(IndexOutOfBoundsException, v.nth, -2343)
    # assocN()
    def testAssocN_PASS(self):
        for k, v in testAssocNMap_PASS.items():
            self.assertEqual(k, v)
    # assoc()
    def testAssoc_PASS(self):
        for k, v in testAssocMap_PASS.items():
            self.assertEqual(k, v)
    def testAssoc_FAIL(self):
        v = pv.vec([])
        self.assertRaises(IndexOutOfBoundsException, v.assoc, 2, uobj)
    def testAssocN_FAIL(self):
        v = pv.vec([])
        self.assertRaises(IndexOutOfBoundsException, v.assocN, 2, uobj)
    # __len__()
    def testLen_PASS(self):
        for k, v in testLenMap_PASS.items():
            self.assertEqual(k, v)
    # cons()
    def testCons_PASS(self):
        for k, v in testConsMap_PASS.items():
            self.assertEqual(k, v)
    # pop()
    def testPop_PASS(self):
        for k, v in testPopMap_PASS.items():
            self.assertEqual(k, v)
    def testPop_FAIL(self):
        v = pv.vec([])
        self.assertRaises(IllegalStateException, v.pop)

    # APersistentVector methods (__eq__ needs debugging)

    # peek()
    def testPeek_PASS(self):
        self.assertEqual(self.v3.peek(), "z")
    # seq()
    def testSeq_PASS(self):
        s = self.v3.seq()
        self.assertTrue(isinstance(s, IndexableSeq))
        self.assertEqual(len(s), 3)
        self.assertEqual(s.first(), "x")
    # very basic tests here, do the rest .clj tests
    # better (= v q)
    def test__eq___PASS(self):
        v = pv.vec(["x", "y", "z"])
        self.assertTrue(self.v3 == v)
        self.assertTrue(self.v3 == self.v3)
    # just tests the basic computation and result on []
    # hash(v)
    def test__hash___PASS(self):
        v = pv.vec([1, 2, 3])
        self.assertEqual(v.__hash__(), vecHash(v))
        self.assertEqual(pv.EMPTY.__hash__(), 1)
    # (print v)
    def testWriteAsString_PASS(self):
        csio = StringIO()
        self.printV.writeAsString(csio)
        self.assertEqual(csio.getvalue(), "[[] []]")
    # (pr v)
    def testWriteAsReplString_PASS(self):
        csio = StringIO()
        self.printV.writeAsReplString(csio)
        self.assertEqual(csio.getvalue(), "[[] []]")
    # str(v)
    def test__str___PASS(self):
        self.assertEqual(self.printV.__str__(), "[[], []]")
    # repr(v)
    def test__repr___PASS(self):
        regex = r"<clojure\.lang\.persistentvector\.PersistentVector" \
                r" object at 0x[a-fA-F0-9]+ \[\[\] \[\]\]>$"
        self.assertTrue(re.match(regex, self.printV.__repr__()))


testCreationMap_PASS = {
    # vec
    pv.vec([]): pv.EMPTY,
    pv.vec([uobj])._tail[0]: uobj,
    pv.vec([0, 0, uobj])._tail[2]: uobj,
    # create
    pv.create(): pv.EMPTY,
    pv.create(uobj)._tail[0]: uobj,
    pv.create(0, 0, uobj)._tail[2]: uobj,
    }

testMetaDataMap_PASS = {
    pv.PersistentVector(pseudoMetaData, 0, 5, pv.EMPTY_NODE, []) \
        .meta(): pseudoMetaData,
    pv.PersistentVector(pseudoMetaData, 0, 5, pv.EMPTY_NODE, []) \
        .empty().meta(): pseudoMetaData,
    }
        
testCallMap_PASS = {
    # _tail used
    pv.vec([42])(0): 42,
    pv.vec([0, 42])(1): 42,
    pv.vec([0, 0, 42])(2): 42,
    # force Node creation
    pv.vec(range(32) + [42])(32): 42,
    # larg-ish vec
    pv.vec(range(10000))(9999): 9999,
    }
    
testNthMap_PASS = {
    # in range
    pv.vec([42]).nth(0): 42,
    pv.vec([None]).nth(0): None,
    pv.vec([0, 42]).nth(1): 42,
    pv.vec([0, None]).nth(1): None,
    pv.vec([0, 0, 42]).nth(2): 42,
    pv.vec([0, 0, None]).nth(2): None,
    pv.vec(range(32) + [42]).nth(32): 42,
    pv.vec(range(32) + [None]).nth(32): None,
    # larg-ish vec
    pv.vec(range(10000)).nth(9999): 9999,
    # out of range, default value returned 
    pv.vec([0, 0, 0]).nth(3, uobj): uobj,
    # default value of None returned 
    pv.vec([0, 0, 0]).nth(3, None): None,
    }
    
testAssocNMap_PASS = {
    # modify
    pv.vec([0]).assocN(0, uobj)[0]: uobj,
    pv.vec([0]).assocN(0, None)[0]: None,
    # append
    pv.vec([]).assocN(0, uobj)[0]: uobj,
    pv.vec([]).assocN(0, None)[0]: None,
    # large-ish vec
    pv.vec(range(10000)).assocN(10000, uobj)[10000]: uobj,
    pv.vec(range(10000)).assocN(10000, None)[10000]: None,
    }

testAssocMap_PASS = {
    # modify
    pv.vec([0]).assoc(0, uobj)[0]: uobj,
    pv.vec([0]).assoc(0, None)[0]: None,
    # append
    pv.vec([]).assoc(0, uobj)[0]: uobj,
    pv.vec([]).assoc(0, None)[0]: None,
    # large-ish vec
    pv.vec(range(10000)).assoc(10000, uobj)[10000]: uobj,
    pv.vec(range(10000)).assoc(10000, None)[10000]: None,
    }

testLenMap_PASS = {
    len(pv.vec([])): 0,
    len(pv.vec([0])): 1,
    len(pv.vec([0, 0])): 2,
    len(pv.vec(range(2342))): 2342,
    }

testConsMap_PASS = {
    pv.vec([]).cons(uobj)(0): uobj,
    pv.vec([]).cons(0).cons(uobj)(1): uobj,
    pv.vec([]).cons(0).cons(None)(1): None,
    }

testPopMap_PASS = {
    pv.vec([0]).pop(): pv.EMPTY,
    len(pv.vec(range(33)).pop()): 32,
    }

########NEW FILE########
__FILENAME__ = protocol-tests
from clojure.lang.protocol import ProtocolFn
import unittest

class TestProtocolFunctions(unittest.TestCase):
    def testProtocol(self):
        z = ProtocolFn("foo")
        z.extend(int, lambda x: "int")
        z.extend(ProtocolFn, lambda f: "fn")
        z.extend(float, lambda f: "float")
        
        self.assertEqual(z(1), "int")
        self.assertEqual(z(1.0), "float")
        self.assertEqual(z(z), "fn")
        

########NEW FILE########
__FILENAME__ = reader-tests
#!/usr/bin/python -t
# -*- coding: utf-8 -*-

"""reader-tests.py

Friday, March 16 2012
"""

import re
import string
import unittest

from random import choice
from fractions import Fraction
from clojure.lang.lispreader import read, readDelimitedList
from clojure.lang.symbol import Symbol
from clojure.lang.ipersistentlist import IPersistentList
from clojure.lang.persistentlist import PersistentList
from clojure.lang.persistentlist import EmptyList
from clojure.lang.persistentvector import PersistentVector
from clojure.lang.persistenthashmap import PersistentHashMap
from clojure.lang.persistenthashset import PersistentHashSet
from clojure.lang.fileseq import StringReader
from clojure.lang.cljexceptions import ReaderException
from clojure.lang.pytypes import *


# reader returns this unique *value* if it's out of characters
EOF = object()
# A unique *type* to return at the EOF.
# For use in testReturnedType_PASS().
class Sentinal(object): pass
sentinal = Sentinal()
sentinalType = type(sentinal)

class TestReader(unittest.TestCase):
    # literal integers
    def testIntegerReader_PASS(self):
        # base 8
        for k, v in base8IntegerMap_PASS.items():
            r = StringReader(k)
            self.assertEqual(read(r, False, EOF, False), v)
        # base 10
        for k, v in base10IntegerMap_PASS.items():
            r = StringReader(k)
            self.assertEqual(read(r, False, EOF, False), v)
        # base 16
        for k, v in base16IntegerMap_PASS.items():
            r = StringReader(k)
            self.assertEqual(read(r, False, EOF, False), v)
        # base N
        for k, v in baseNIntegerMap_PASS.items():
            r = StringReader(k)
            self.assertEqual(read(r, False, EOF, False), v)
    def testIntegerReader_FAIL(self):
        for t in integer_FAIL:
            r = StringReader(t)
            self.assertRaises(ReaderException, read, r, False, EOF, False)
    # literal floating point
    def testFloatingPointReader_PASS(self):
        for k, v in floatingPointMap_PASS.items():
            r = StringReader(k)
            self.assertEqual(read(r, False, EOF, False), v)
    def testFloatingPointReader_FAIL(self):
        for t in floatingPoint_FAIL:
            r = StringReader(t)
            self.assertRaises(ReaderException, read, r, False, EOF, False)
    # literal ratios 
    def testRationalReader_PASS(self):
        for k, v in rationalMap_PASS.items():
            r = StringReader(k)
            self.assertEqual(read(r, False, EOF, False), v)
    def testRationalReader_FAIL(self):
        for t in rational_FAIL:
            r = StringReader(t)
            self.assertRaises(ReaderException, read, r, False, EOF, False)
    # literal characters
    def testCharacterReader_PASS(self):
        for k, v in literalCharacterMap_PASS.items():
            r = StringReader(k)
            self.assertEqual(read(r, False, EOF, False), v)
    def testCharacterReader_FAIL(self):
        for s in literalCharacter_FAIL:
            r = StringReader(s)
            self.assertRaises(ReaderException, read, r, False, EOF, False)
    # literal strings
    def testStringReader_PASS(self):
        for k, v in literalStringMap_PASS.items():
            r = StringReader('"' + k + '"')
            self.assertEqual(read(r, False, EOF, False), v)
    def testStringReader_FAIL(self):
        # special case, missing trailing "
        r = StringReader('"foo')
        self.assertRaises(ReaderException, read, r, False, EOF, False)
        for s in literalString_FAIL:
            r = StringReader('"' + s + '"')
            self.assertRaises(ReaderException, read, r, False, EOF, False)
    # literal regex pattern strings
    def testRegexPattern_PASS(self):
        for k, v in regexPatternMap_PASS.items():
            r = StringReader(k)
            self.assertEqual(read(r, False, EOF, False).pattern, v.pattern)
    def testRegexPattern_FAIL(self):
        for s in regexPattern_FAIL:
            r = StringReader(s)
            self.assertRaises(ReaderException, read, r, False, EOF, False)
    # literal raw regex pattern strings
    def testRawRegexPattern_PASS(self):
        for k, v in rawRegexPatternMap_PASS.items():
            r = StringReader(k)
            self.assertEqual(read(r, False, EOF, False).pattern, v.pattern)
    def testRawRegexPattern_FAIL(self):
        for s in rawRegexPattern_FAIL:
            r = StringReader(s)
            self.assertRaises(ReaderException, read, r, False, EOF, False)
    # delimited lists
    def testDelimitedLists_PASS(self):
        # length test
        for k, v in delimitedListLength_PASS.items():
            r = StringReader(k)
            delim = k[-1]
            self.assertEqual(readDelimitedList(delim, r, False), v)
    # returned type tests
    def testReturnedType_PASS(self):
        for k, v in returnedType_PASS.items():
            r = StringReader(k)
            self.assertEqual(type(read(r, False, sentinal, False)), v)
    # raise on EOF
    def testEOFRaisesReaderException(self):
        r = StringReader("")
        self.assertRaises(ReaderException, read, r, True, # <- True
                          EOF, False)
    # miscellaneous failures
    def testMiscellaneous_FAIL(self):
        for s in miscellaneous_FAIL:
            r = StringReader(s)
            self.assertRaises(ReaderException, read, r, False, EOF, False)
            

# ======================================================================
# Literal Integer Cases
# ======================================================================

base8IntegerMap_PASS = {
    "00": 0, "-00": 0, "+00": 0,
    "012345670": 2739128, "-012345670": -2739128, "+012345670": 2739128,
    "06235436235462365452777171623500712635712365712236" :
        140667142011619517350321483099394425046406302L,
    "-06235436235462365452777171623500712635712365712236" :
        -140667142011619517350321483099394425046406302L,
    "+06235436235462365452777171623500712635712365712236" :
        140667142011619517350321483099394425046406302L,
    }

base10IntegerMap_PASS = {
    "0" : 0, "-0" : 0, "+0" : 0,
    "1" : 1, "-1" : -1, "+1" : 1,
    "1234567890" : 1234567890,
    "-1234567890" : -1234567890,
    "+1234567890" : 1234567890,
    "20399572305720357120320399572305720357203" :
        20399572305720357120320399572305720357203L,
    "-20399572305720357120320399572305720357203" :
        -20399572305720357120320399572305720357203L,
    "+20399572305720357120320399572305720357203" :
        20399572305720357120320399572305720357203L,
    }

base16IntegerMap_PASS = {
    "0x0" : 0, "-0x0" : 0, "+0x0" : 0,
    "0X0" : 0, "-0X0" : 0, "+0X0" : 0,
    "0x1234567890abcdefABCDEF" :
        22007822917795467892608495L,
    "-0X1234567890abcdefABCDEF" :
        -22007822917795467892608495L,
    "+0x1234567890abcdefABCDEF" :
        +22007822917795467892608495L,
    }

def gen_baseNIntegerMap_PASS():
    """Return a dict as a string to test the base-N syntax (2r101010)

    This map is eval'd below.

    Each entry is of the form:
        "2r10" : 2

    To see wtf is going on...
    >>> pprint(eval(gen_baseNIntegerMap_PASS()))"""
    # don't change the order of these
    digits = "1023456789aBcDeFgHiJkLmNoPqRsTuVwXyZ"
    entries = []
    for radix in range(2, 37):
        strDigits = digits[:radix]
        res1 = int(strDigits, radix)
        res2 = int('-' + strDigits, radix)
        entry = '"%s":%d, "%s":%d, "%s":%d' \
            % ("%d%s%s" % (radix, choice('rR'), strDigits), res1,
               "-%d%s%s" % (radix, choice('rR'), strDigits), res2,
               "+%d%s%s" % (radix, choice('rR'), strDigits), res1)
        entries.append(entry)
    return "{%s}" % ",".join(entries)

baseNIntegerMap_PASS = eval(gen_baseNIntegerMap_PASS())

integer_FAIL = [
    # no f suffix
    "3333f", "-3333f", "+3333f",
    # Clojure M not a suffix (yet)
    "3333M", "-3333M", "+3333M",
    # 8 not an octal digit
    "08", "-08", "+08",
    # g not a hex digit
    "0xfgaa00", "-0xfgaa00", "+0xfgaa00",
    # z not a base 32 number
    "32rzzz", "-32rzzz", "+32rzzz",
    # radix out of range [2, 36]
     "1r0", "-1r0", "+1r0", "37r0", "-37r0", "+37r0",
    ]

# ======================================================================
# Literal Floating Point Cases
# ======================================================================

floatingPointMap_PASS = {
    # no decimal, exponent
    "0e0" : 0.0, "-0e0" : 0.0, "+0e0" : 0.0,
    "0e-0" : 0.0, "-0e-0" : 0.0, "+0e-0" : 0.0,
    "0E-0" : 0.0, "-0E-0" : 0.0, "+0E-0" : 0.0,
    "0e+0" : 0.0, "-0e+0" : 0.0, "+0e+0" : 0.0,
    "0E+0" : 0.0, "-0E+0" : 0.0, "+0E+0" : 0.0,
    # with decimal, no digit after decimal, exponent
    "0." : 0.0, "-0." : 0.0, "+0." : 0.0,
    "0.e0" : 0.0, "-0.e0" : 0.0, "+0.e0" : 0.0,
    "0.E0" : 0.0, "-0.E0" : 0.0, "+0.E0" : 0.0,
    "0.e-0" : 0.0, "-0.e-0" : 0.0, "+0.e-0" : 0.0,
    "0.E-0" : 0.0, "-0.E-0" : 0.0, "+0.E-0" : 0.0,
    "0.e+0" : 0.0, "-0.e+0" : 0.0, "+0.e+0" : 0.0,
    "0.E+0" : 0.0, "-0.E+0" : 0.0, "+0.E+0" : 0.0,
    # with decimal, digit after decimal, exponent
    "0.0" : 0.0, "-0.0" : 0.0, "+0.0" : 0.0,
    "0.0e0" : 0.0, "-0.0e0" : 0.0, "+0.0e0" : 0.0,
    "0.0E0" : 0.0, "-0.0E0" : 0.0, "+0.0E0" : 0.0,
    "0.0e-0" : 0.0, "-0.0e-0" : 0.0, "+0.0e-0" : 0.0,
    "0.0E-0" : 0.0, "-0.0E-0" : 0.0, "+0.0E-0" : 0.0,
    "0.0e+0" : 0.0, "-0.0e+0" : 0.0, "+0.0e+0" : 0.0,
    "0.0E+0" : 0.0, "-0.0E+0" : 0.0, "+0.0E+0" : 0.0,
    }

floatingPoint_FAIL = [
    # no suffix
    "3.3f", "-3.3f", "+3.3f",
    # s, f, d, l, etc. not an exponent specifier
    "23.0s-4", "-23.0f-4", "+23.0d-4",
    # double decimal
    "3..", "-3..", "+3..",
    ]

# ======================================================================
# Literal Rational Cases
# ======================================================================

rationalMap_PASS = {
    "22/7" : Fraction(22, 7),
    "-22/7" : Fraction(-22, 7),
    "+22/7" : Fraction(22, 7),
    "0/1" : Fraction(0, 1),
    "-0/1" : Fraction(0, 1),
    "+0/1" : Fraction(0, 1),
    # regex was fubar, didn't allow zeros after the first digit
    "100/203" : Fraction(100, 203),
    "-100/203" : Fraction(-100, 203),
    "+100/203" : Fraction(100, 203),
    }

rational_FAIL = [
    # These actually pass in Clojure, but are interpreted as base 10 integers,
    # not base 8.
    "033/029", "-033/029", "+033/029", 
    ]

# ======================================================================
# Literal Character Cases
# ======================================================================

literalCharacterMap_PASS = {
    # basic
    "\\x" : "x",
    "\\ " : " ",
    "\\X" : "X",
    # newline after the \
    """\\
""" : "\n",
    # named characters
    "\\space" : " ",
    "\\newline" : "\n",
    "\\return" : "\r",
    "\\backspace" : "\b",
    "\\formfeed" : "\f",
    "\\tab" : "\t",
    # octal
    "\\o0" : "\x00",
    "\\o41" : "!",
    "\\o377" : u"\u00ff",
    # hex
    "\\u03bb" : u"\u03bb",
    # BZZZZT!
    # Because this file is encoded as UTF-8, and the reader is expecting ASCII,
    # it will crap out every time. 
    # "\\λ" : character(u"\u03bb"),
    }

literalCharacter_FAIL = [
    # According to a random web page:
    # The only reason the range D800:DFFF is invalid is because of UTF-16's
    # inability to encode it.
    "\ud800", "\udfff",
    # missing char at eof
    "\\",
    # not enough digits after \u (\u is the character u)
    "\u1", "\u22", "\u333",
    # too many digits after \u
    "\u03bbb",
    # too many digits after \o
    "\o0333",
    # octal value > 0377
    "\o400"
    ]

# ======================================================================
# Literal String Cases
# These are tests that conform to Clojure. Some Python string syntax is
# not permitted:
# \U, \N{foo}, \x, \v, \a
# ======================================================================
            
literalStringMap_PASS = {
    # basic
    "": "",
    "x": "x",
    "foo": "foo",
    "0123456789": "0123456789",
    "~!@#$%^&*()_+-=[]{}';:/?>.<,": "~!@#$%^&*()_+-=[]{}';:/?>.<,",
    "qwertyuiopasdfghjklzxcvbnm": "qwertyuiopasdfghjklzxcvbnm",
    "QWERTYUIOPASDFGHJKLZXCVBNM": "QWERTYUIOPASDFGHJKLZXCVBNM",
    # escape           |  |<------ trailing escaped escape
    '\\"\\n\\t\\f\\b\\r\\\\': '"\n\t\f\b\r\\',
    # 4 hex digit
    "\u03bb": u"\u03bb",
    "\u03bb@": u"\u03bb@",
    "@\u03bb": u"@\u03bb",
    # octal
    "\\0": "\x00",
    "\\0@": "\x00@",
    "@\\0": "@\x00",
    "\\41": "!",
    "\\41@": "!@",
    "@\\41": "@!",
    "\\176": "~",
    "\\176@": "~@",
    "@\\176": "@~",
    }

literalString_FAIL = [
    # invalid escape characters
    "\\x", "\\a", "\\v", "@\\x", "@\\a", "@\\v", "\\x@", "\\a@", "\\v@",
    "\\o041"
    # not enough digits after \u
    "\\u", "\\u3", "\\u33", "\\u333",
    "@\\u", "@\\u3", "@\\u33", "@\\u333",
    "\\u@", "\\u3@", "\\u33@", "\\u333@",
    # octal value > 0377
    "\\400", "@\\400", "\\400@",
    ]

# ======================================================================
# Regular Expression Pattern
#
# Each key is the string sent to lispreader. The escapes have to be
# handled in such a way as to allow the reader to do escape
# interpretation. If Python would treat the escape special, it needs
# an additional \ before sending it to the reader.
# ======================================================================

regexPatternMap_PASS = {
    # all using #"", not raw #r""
    '#""' : re.compile(""),
    '#"."' : re.compile("."),
    '#"^."' : re.compile("^."),
    '#".$"' : re.compile(".$"),
    '#".*"' : re.compile(".*"),
    '#".+"' : re.compile(".+"),
    '#".?"' : re.compile(".?"),
    '#".*?"' : re.compile(".*?"),
    '#".+?"' : re.compile(".+?"),
    '#".??"' : re.compile(".??"),
    '#".{3}"' : re.compile(".{3}"),
    '#".{3,}"' : re.compile(".{3,}"),
    '#".{,3}"' : re.compile(".{,3}"),
    '#".{3,3}"' : re.compile(".{3,3}"),
    '#".{3,3}"' : re.compile(".{3,3}"),
    '#".{3,3}?"' : re.compile(".{3,3}?"),
    # None of these \ are special. Python will send them to the reader as is.
    # \ . \ ^ \ $, etc.
    '#"\.\^\$\*\+\?\{\}\[\]"' : re.compile("\.\^\$\*\+\?\{\}\[\]"),
    '#"[a-z]"' : re.compile("[a-z]"),
    '#"[]]"' : re.compile("[]]"),
    '#"[-]"' : re.compile("[-]"),
    # Nor are these
    '#"[\-\]\[]"' : re.compile(r"[\-\]\[]"),
    # or these
    '#"[\w\S]"' : re.compile("[\w\S]"),
    '#"[^5]"' : re.compile("[^5]"),
    # or the |
    '#"A|B[|]\|"' : re.compile("A|B[|]\|"),
    # or ( )
    '#"([()]\(\))"' : re.compile("([()]\(\))"),
    '#"(?iLmsux)"' : re.compile("(?iLmsux)"),
    '#"(?iLmsux)"' : re.compile("(?iLmsux)"),
    '#"(:?)"' : re.compile("(:?)"),
    '#"(?P<foo>)"' : re.compile("(?P<foo>)"),
    '#"(?P<foo>)(?P=foo)"' : re.compile("(?P<foo>)(?P=foo)"),
    '#"(?# comment )"' : re.compile("(?# comment )"),
    '#"(?=foo)"' : re.compile("(?=foo)"),
    '#"(?!foo)"' : re.compile("(?!foo)"),
    '#"(?<=foo)bar"' : re.compile("(?<=foo)bar"),
    '#"(?<!foo)bar"' : re.compile("(?<!foo)bar"),
    '#"(?P<foo>)(?(foo)yes|no)"' : re.compile("(?P<foo>)(?(foo)yes|no)"),
    #       |  |<---- Python will send two \'s to the lisp reader, not four
    '#"(.+) \\\\1"' : re.compile("(.+) \\1"),
    '#"(.+) \\\\1"' : re.compile(r"(.+) \1"),
    # send one \ each, so the octal sequences are interpreted in lispreader
    # >>> u"\377" == "\377"   # funky warning on the Python repl
    '#"\\377\\021"' : re.compile(u"\377\021"),
    # Again, send one \ each. Python would interpret \1 as the char 0x01
    # *before* sending it to lispreader.
    '#"[\\1\\2\\3\\4\\5\\6\\7\\10]"' : re.compile("[\1\2\3\4\5\6\7\10]"),
    # Python does not interpret \A, but it does \b
    # The dict value here is a raw string so the char sequence will be:
    # \ A \ \ b \ B, etc.
    '#"\A\\\\b\B\d\D\s\S\w\W\Z"' : re.compile(r"\A\b\B\d\D\s\S\w\W\Z"),
    # dict val is a raw string, and Python interprets all these chars
    '#"\\\\a\\\\b\\\\f\\\\n\\\\r\\\\t\\\\v"' : re.compile(r"\a\b\f\n\r\t\v"),
    # I want Python to interpret here. lispreader will simply return
    # 0x07, 0x08 etc. (no escape interpretation)
    '#"\a\b\f\n\r\t\v"' : re.compile("\a\b\f\n\r\t\v"),
    # Send \ and letter separately. lispreader will see \ n and
    # return 0x0a (reader interpretation)
    '#"\\a\\b\\f\\n\\r\\t\\v"' : re.compile("\a\b\f\n\r\t\v"),
    # \N, \u, and \U are only special in a unicode string (in Python)
    '#"\N{DIGIT ZERO}{5, 10}"' : re.compile(u"\N{DIGIT ZERO}{5, 10}"),
    '#"\u03bb{1,3}"' : re.compile(u"\u03bb{1,3}"),
    '#"\U000003bb{1,3}"' : re.compile(u"\U000003bb{1,3}"),
    # but \x is always special, hence the \\
    '#"\\xff\\x7f"' : re.compile(u"\xff\x7f"),
    
'''#"(?x)
     # foo
     [a-z]
     # bar
     [0-9a-zA-Z_]+
     "''' : re.compile("""(?x)
     # foo
     [a-z]
     # bar
     [0-9a-zA-Z_]+
     """),
    }

regexPattern_FAIL = [
    # # unmatched paren, bracket, (can't make it catch a missing } O_o)
    '#"([()]\(\)"', '#"["',
    # foo not defined
    '#"(?(foo)yes|no)"',
    # bogus escape 
    '#"[\\8]"',
    # need 4 hex digits
    '#"\u"', '#"\u1"', '#"\u12"', '#"\u123"',
    # need 8 hex digits
    '#"\U"', '#"\U1"', '#"\U12"', '#"\U123"', '#"\U1234"', '#"\U12345"',
    '#"\U123456"', '#"\U1234567"',
    # need 2 hex digits
    '#"\\x"', '#"\\x1"',
    # missing }, missing ",  can't escape }
    '#"\N{foo"', '#"\N{foo', '#"\N{foo\\}}"',
    # unknown name
    '#"\N{KLINGON LETTER NG}"',
    # empty {}
    '#"\N{}"', '#"\N{   }"',
    ]

rawRegexPatternMap_PASS = {
    '#r""' : re.compile(r""),
    '#r"\\."' : re.compile(r"\."),
    '#r"\\."' : re.compile(r"\."),
    '#r"\\n"' : re.compile(r"\n"),
    '#r"\.\^\$\*\+\?\{\}\[\]"' : re.compile(r"\.\^\$\*\+\?\{\}\[\]"),
    '#r"[\-\]\[]"' : re.compile(r"[\-\]\[]"),
    '#r"[\w\S]"' : re.compile(r"[\w\S]"),
    '#r"A|B[|]\|"' : re.compile(r"A|B[|]\|"),
    '#r"([()]\(\))"' : re.compile(r"([()]\(\))"),
    '#r"(.+) \\1"' : re.compile(r"(.+) \1"),
    '#r"\\377\\021"' : re.compile(ur"\377\021"),
    '#r"[\\1\\2\\3\\4\\5\\6\\7\\10]"' : re.compile(r"[\1\2\3\4\5\6\7\10]"),
    '#r"\A\\b\B\d\D\s\S\w\W\Z"' : re.compile(r"\A\b\B\d\D\s\S\w\W\Z"),
    '#r"\\a\\b\\f\\n\\r\\t\\v"' : re.compile(r"\a\b\f\n\r\t\v"),
    '#r"\a\b\f\n\r\t\v"' : re.compile("\a\b\f\n\r\t\v"),
    '#r"\N{DIGIT ZERO}{5, 10}"' : re.compile(ur"\N{DIGIT ZERO}{5, 10}"),
    '#r"\u03bb{1,3}"' : re.compile(ur"\u03bb{1,3}"),
    '#r"\\\u03bb{1,3}"' : re.compile(ur"\\u03bb{1,3}"),
    '#r"\\\\\u03bb{1,3}"' : re.compile(ur"\\\u03bb{1,3}"),
    '#r"\\\\\\\u03bb{1,3}"' : re.compile(ur"\\\\u03bb{1,3}"),
    '#r"\U000003bb{1,3}"' : re.compile(ur"\U000003bb{1,3}"),
    '#r"\\xff\\x7f"' : re.compile(ur"\xff\x7f"),
    '#r"\\0"' : re.compile(ur"\0"),
    '#r"\\01"' : re.compile(ur"\01"),
    '#r"\\012"' : re.compile(ur"\012"),
    '''#r"\\
"''' : re.compile(r"""\
"""),
    }

rawRegexPattern_FAIL = [
    # craps out the regex compiler
    '#r"\\x"',
    # can't end with an odd number of \
    '#r"\\"',                   # #r"\"    ; in clojure-py
    '#r"\\\\\\"',               # #r"\\\"  ; in clojure-py
    # missing trailing "
    '#r"foo',
    # need 4 hex digits
    '#r"\u"', '#r"\u1"', '#r"\u12"', '#r"\u123"',
    # need 8 hex digits
    '#r"\U"', '#r"\U1"', '#r"\U12"', '#r"\U123"', '#r"\U1234"', '#r"\U12345"',
    '#r"\U123456"', '#r"\U1234567"',
    ]

# ======================================================================
# Literal Delimited Lists
# ======================================================================

# The keys define the clojure syntax of any object that would result in a call
# to lispreader.readDelimitedList() (minus the leading macro character(s)).
# Some objects like map and set have the same terminating character `}'. So
# there is only one entry for both.
#
# The value is a the expected contents of the Python list returned from
# readDelimitedList(). Integers are used because I don't care what type the
# items are. There are separate tests for that.
delimitedListLength_PASS = {
    "]" : [],
    "}" : [],
    ")" : [],
    "0]" : [0],
    "0)" : [0],
    "0}" : [0],
    "0 0]" : [0, 0],
    "0 0)" : [0, 0],
    "0 0}" : [0, 0],
    }

# ======================================================================
# Returned Type
# ======================================================================
returnedType_PASS = {
    "" : sentinalType,
    "," : sentinalType,
    " " : sentinalType,
    """
""" : sentinalType,
    "\r" : sentinalType,
    "\n" : sentinalType,
    "\r\n" : sentinalType,
    "\n\r" : sentinalType,
    "\t" : sentinalType,
    "\b" : sentinalType,
    "\f" : sentinalType,
    ", \n\r\n\t\n\b\r\f" : sentinalType,
    "\v" : Symbol,              # O_o
    # "\λ" : pyUnicodeType,
    "\\x" : pyStrType,      # TODO: always return unicode, never str
    "%foo" : Symbol,            # not in an anonymous function #()
    "[]" : PersistentVector,
    "()" : EmptyList,
    "{}" : PersistentHashMap,
    '"foo"' : pyStrType,        # TODO: always return unicode, never str
    # "λλλ" : Symbol,
    '#"foo"' : pyRegexType,
    '#r"foo"' : pyRegexType,
    "#()" : PersistentList,
    "#{}" : PersistentHashSet,
    "'foo" : PersistentList,
    "~foo" : PersistentList,
    "~@(foo)" : PersistentList,
    "#^:foo()" : EmptyList,
    "^:foo()" : EmptyList,
    "; comment" : sentinalType,
    "#_ foo" : sentinalType,
    "0" : pyIntType,
    "0x0" : pyIntType,
    "041" : pyIntType,
    "2r10" : pyIntType,
    "2.2" : pyFloatType,
    "2e-3" : pyFloatType,
    "1/2" : Fraction,
    "foo" : Symbol,
    ".3" : Symbol,
    "+.3" : Symbol,
    "-.3" : Symbol,
    "true" : pyBoolType,
    "True" : Symbol,
    "false" : pyBoolType,
    "False" : Symbol,
    "nil" : pyNoneType,
    "None" : Symbol,
    }

# ======================================================================
# Miscellaneous Failures
# Any type of random failures should go here
# ======================================================================

miscellaneous_FAIL = [
    # always raises
    "#<unreadable object>",
    # deref not implemented (yet)
    # reader eval not implemented (yet)
    "#=foo",
    ]

########NEW FILE########
__FILENAME__ = ref-tests
"""ref_tests.py

Thursday, Oct. 25 2012"""

import sys
if (sys.version_info[0], sys.version_info[1]) >= (2, 7):
    import unittest
else:
    import unittest2 as unittest
from threading import Thread, current_thread
from threading import local as thread_local
from contextlib import contextmanager
from time import time, sleep
from itertools import count

from clojure.lang.ref import Ref, TVal
from clojure.lang.lockingtransaction import LockingTransaction, TransactionState, Info
from clojure.lang.cljexceptions import IllegalStateException, TransactionRetryException
from clojure.util.shared_lock import SharedLock

import clojure.lang.persistentvector as pv

class TestRef(unittest.TestCase):
    def setUp(self):
        self.refZero = Ref(0, None)
        self.refOne = Ref(pv.vec(range(10)), None)
    ### Internal state
    def testInternalState_PASS(self):
        ## NOTE depends on number of test cases, ugh
        # self.assertEqual(self.refZero._id, 22)
        # self.assertEqual(self.refOne._id, 23)
        self.assertEqual(self.refZero._faults.get(), 0)
        self.assertEqual(self.refOne._faults.get(), 0)
        self.assertIsNone(self.refZero._tinfo)
        self.assertIsInstance(self.refZero._lock, SharedLock)
        self.assertIsInstance(self.refZero._tvals, TVal)
    def testTVal_PASS(self):
        self.assertEqual(self.refZero._tvals.val, 0)
        self.assertEqual(self.refZero._tvals.point, 0)
        self.assertGreater(self.refZero._tvals.msecs, 0)
        self.assertEqual(self.refZero._tvals.next, self.refZero._tvals)
        self.assertEqual(self.refZero._tvals.prev, self.refZero._tvals)
    ### External API
    def testEquality_PASS(self):
        self.assertEqual(self.refZero, self.refZero)
    def testCurrentValPASS(self):
        self.assertEqual(self.refZero._currentVal(), 0)
    def testDeref_PASS(self):
        self.assertEqual(self.refZero.deref(), 0)
    def testDerefVec_PASS(self):
        self.assertEqual(self.refOne.deref(), pv.vec(range(10)))
    def testSetNoTransaction_FAIL(self):
        self.assertRaises(IllegalStateException, self.refOne.refSet, 1)
    def testAlterNoTransaction_FAIL(self):
        self.assertRaises(IllegalStateException, self.refOne.alter, lambda x: x**2, [])
    def testCommuteNoTransaction_FAIL(self):
        self.assertRaises(IllegalStateException, self.refOne.commute, lambda x: x**2, [])
    def testTouchNoTransaction_FAIL(self):
        self.assertRaises(IllegalStateException, self.refOne.touch)
    def testBound_PASS(self):
        self.assertTrue(self.refOne.isBound())
    def testHistoryLen_PASS(self):
        self.assertEqual(self.refOne.historyCount(), 1)
    def testTrimHistory_PASS(self):
        self.refOne.trimHistory()
        self.assertEqual(self.refOne.historyCount(), 1)

@contextmanager
def running_transaction(thetest):
    # Fake a running transaction
    LockingTransaction._transactions.local = LockingTransaction()
    LockingTransaction._transactions.local._info = Info(TransactionState.Running, LockingTransaction._transactions.local._startPoint)
    LockingTransaction.ensureGet()._readPoint = -1
    LockingTransaction.transactionCounter = count()
    LockingTransaction.ensureGet()._startPoint = time()
    yield
    # Clean up and remove LockingTransaction we created
    LockingTransaction._transactions = thread_local()
    thetest.assertIsNone(LockingTransaction.get())

class TestLockingTransaction(unittest.TestCase):
    def setUp(self):
        self.refZero = Ref(0, None)

    def secondary_op(self, func):
        """
        Utility function, runs the desired function in a secondary thread with
        its own transaction

        func should accept two argument: testclass, and the main thread's LockingTransaction
        """
        def thread_func(testclass, mainTransaction, funcToRun):
            self.assertIsNone(LockingTransaction.get())
            LockingTransaction._transactions.local = LockingTransaction()
            LockingTransaction._transactions.local._info = Info(TransactionState.Running, LockingTransaction._transactions.local._startPoint)
            funcToRun(testclass, mainTransaction)
            LockingTransaction._transactions = thread_local()
            self.assertIsNone(LockingTransaction.get())

        t = Thread(target=thread_func, args=[self, LockingTransaction.ensureGet(), func])
        t.start()

    def lockRef(self, ref, reader=False):
        """
        Locks the desired ref's read or write lock. Creates a side thread that never exits, just holds the lock
        """
        def locker(ref, reader):
            if reader:
                ref._lock.acquire_shared()
            else:
                ref._lock.acquire()

        t = Thread(target=locker, args=[ref, reader])
        t.start()

    def testNone_PASS(self):
        self.assertIsNone(LockingTransaction.get())

    def testCreateThreadLocal_PASS(self):
        with running_transaction(self):
            def secondary(testclass, mainTransaction):
                testclass.assertIsInstance(LockingTransaction.get(), LockingTransaction)
                testclass.assertIsInstance(LockingTransaction.ensureGet(), LockingTransaction)
                # Make sure we're getting a unique locking transaction in this auxiliary thread
                testclass.assertNotEqual(LockingTransaction.ensureGet(), mainTransaction)
            self.assertIsInstance(LockingTransaction.get(), LockingTransaction)
            self.assertIsInstance(LockingTransaction.ensureGet(), LockingTransaction)
            self.secondary_op(secondary)

    def testOrdering_PASS(self):
        with running_transaction(self):
            t = LockingTransaction.ensureGet()
            self.assertEqual(t._readPoint, -1)
            t._updateReadPoint(False)
            self.assertEqual(t._readPoint, 0)
            t._updateReadPoint(False)
            self.assertEqual(t._readPoint, 1)
            self.assertEqual(t._getCommitPoint(), 2)
            self.assertEqual(t._readPoint, 1)

    def testTransactionInfo_PASS(self):
        with running_transaction(self):
            # NOTE assumes transactions don't actually work yet (_info is never set)
            pass

    def testStop_PASS(self):
        with running_transaction(self):
            t = LockingTransaction.ensureGet()
            # NOTE assumes transactions don't actually work yet (_info is never set)
            t._stop_transaction(TransactionState.Killed)
            self.assertIsNone(t._info)

            # Fake running transaction
            t._info = Info(TransactionState.Running, t._readPoint)
            self.assertIsNotNone(t._info)
            self.assertEqual(t._info.status.get(), TransactionState.Running)
            t._stop_transaction(TransactionState.Committed)
            # No way to check for proper status==Committed here since it sets the countdownlatch then immediately sets itself to none
            self.assertIsNone(t._info)

    def testTryLock_PASS(self):
        with running_transaction(self):
            LockingTransaction.ensureGet()._tryWriteLock(self.refZero)

    def testBarge_PASS(self):
        with running_transaction(self):
            def secondary(testclass, mainTransaction):
                ourTransaction = LockingTransaction.ensureGet()
                # Barging should fail as this transaction is too young
                ourTransaction._info = Info(TransactionState.Running, ourTransaction._readPoint)
                ourTransaction._startPoint = time()
                testclass.assertFalse(ourTransaction._barge(mainTransaction._info))

                # Barging should still fail, we are the newer transaction
                sleep(.2)
                testclass.assertFalse(ourTransaction._barge(mainTransaction._info))

                # Fake ourselves being older by resetting our time
                # Now barging should be successful
                ourTransaction._startPoint = mainTransaction._startPoint - 2
                testclass.assertTrue(ourTransaction._barge(mainTransaction._info))

                # Make sure we are still running, and we successfully set the other transaction's
                #  state to Killed
                testclass.assertEqual(ourTransaction._info.status.get(), TransactionState.Running)
                testclass.assertEqual(mainTransaction._info.status.get(), TransactionState.Killed)

            t = LockingTransaction.ensureGet()
            # For test purposes, force this transaction status to be the desired state
            t._startPoint = time()
            t._info = Info(TransactionState.Running, t._startPoint)
            # Get two transactions on two different threads
            self.secondary_op(secondary)

    def testTakeOwnershipBasic_PASS(self):
        with running_transaction(self):
            t = LockingTransaction.ensureGet()

            # Will retry since our readPoint is 0
            self.assertRaises(TransactionRetryException, t._takeOwnership, self.refZero)
            # Make sure we unlocked the lock
            self.assertRaises(Exception, self.refZero._lock.release)

            # Now we set the read points synthetically (e.g. saying this transaction-try  is starting *now*)
            #  so it appears there is no newer write since
            # this transaction
            # Taking ownership should work since no other transactions exist
            t._readPoint = time()
            self.assertEqual(t._takeOwnership(self.refZero), 0)
            self.assertRaises(Exception, self.refZero._lock.release)

    def testTakeOwnershipLocked_PASS(self):
        with running_transaction(self):
            t = LockingTransaction.ensureGet()

            # Set a write lock on the ref, check we get a retry
            self.lockRef(self.refZero)
            self.assertRaises(TransactionRetryException, t._takeOwnership, self.refZero)

    def testTakeOwnershipBarging_PASS(self):
        with running_transaction(self):
            t = LockingTransaction.ensureGet()
            sleep(.1)

            LockingTransaction.ensureGet()._updateReadPoint(False)
            LockingTransaction.ensureGet()._updateReadPoint(False)

            # Give this ref over to another transaction
            def secondary(testclass, mainTransaction):
                t = LockingTransaction.ensureGet()
                t._startPoint = time()
                t._info = Info(TransactionState.Running, t._startPoint)
                # We own the ref now
                testclass.refZero._tinfo = t._info

            # give up the ref
            self.secondary_op(secondary)
            sleep(.1)
            # now try to get it back and successfully barge
            self.assertEqual(t._takeOwnership(self.refZero), 0)
            self.assertEqual(self.refZero._tinfo, t._info)

    def testTakeOwnershipBargeFail_PASS(self):
        with running_transaction(self):
            t = LockingTransaction.ensureGet()

            LockingTransaction.ensureGet()._updateReadPoint(False)
            LockingTransaction.ensureGet()._updateReadPoint(False)

            def secondary(testclass, mainTransaction):
                t = LockingTransaction.ensureGet()
                t._startPoint = time()
                # We own the ref now
                testclass.refZero._tinfo = t._info

            # Try again but time time we won't be successful barging
            self.secondary_op(secondary)

            # We fake being newer, so we aren't allowed to barge an older transaction
            sleep(.2)
            t._startPoint = time()
            t._info.startPoint = time()
            self.assertRaises(TransactionRetryException, t._takeOwnership, self.refZero)
            self.assertRaises(Exception, self.refZero._lock.release)

    def testGetRef_PASS(self):
        # No running transaction
        self.assertRaises(TransactionRetryException, LockingTransaction().getRef, self.refZero)
        with running_transaction(self):
            t = LockingTransaction.ensureGet()

            # Ref has a previously committed value and no in-transaction-value, so check it
            # Since we're faking this test, we need our read point to be > 0
            LockingTransaction.ensureGet()._updateReadPoint(False)
            LockingTransaction.ensureGet()._updateReadPoint(False)
            self.assertEqual(t.getRef(self.refZero), 0)
            # Make sure we unlocked the ref's lock
            self.assertRaises(Exception, self.refZero._lock.release_shared)

            # Give the ref some history and see if it still works. Our read point is 1 and our new value was committed at time 3
            self.refZero._tvals = TVal(100, 3, time(), self.refZero._tvals)
            self.assertEqual(t.getRef(self.refZero), 0)

            # Now we want the latest value
            LockingTransaction.ensureGet()._updateReadPoint(False)
            LockingTransaction.ensureGet()._updateReadPoint(False)
            LockingTransaction.ensureGet()._updateReadPoint(False)
            self.assertEqual(t.getRef(self.refZero), 100)

            # Force the oldest val to be too new to get a fault
            # Now we have a val at history point 2 and 3
            self.refZero._tvals.next.point = 2
            t._readPoint = 1

            # We should retry and update our faults
            self.assertRaises(TransactionRetryException, t.getRef, self.refZero)
            self.assertEqual(self.refZero._faults.get(), 1)

    def testDoSet_PASS(self):
        with running_transaction(self):
            t = LockingTransaction.ensureGet()
            LockingTransaction.ensureGet()._updateReadPoint(False)
            LockingTransaction.ensureGet()._updateReadPoint(False)

            # Do the set and make sure it was set in our various transaction state vars
            t.doSet(self.refZero, 200)
            self.assertTrue(self.refZero in t._sets)
            self.assertTrue(self.refZero in t._vals)
            self.assertEqual(t._vals[self.refZero], 200)
            self.assertEqual(self.refZero._tinfo, t._info)

    def testEnsures_PASS(self):
        with running_transaction(self):
            t = LockingTransaction.ensureGet()

            # Try a normal ensure. Will fail as t has readPoint of -1 and ref has oldest commit point at 0
            self.assertRaises(TransactionRetryException, t.doEnsure, self.refZero)
            self.assertRaises(Exception, self.refZero._lock.release_shared)

            # Now set our transaction to be further in the future, ensure works
            LockingTransaction.ensureGet()._updateReadPoint(False)
            LockingTransaction.ensureGet()._updateReadPoint(False)
            t.doEnsure(self.refZero)
            self.assertTrue(self.refZero in t._ensures)
            # Try again
            t.doEnsure(self.refZero)
            # Make sure it's read by releasing the lock exactly once w/out error
            self.refZero._lock.release_shared()
            self.assertRaises(Exception, self.refZero._lock.release_shared)

    def testEnsures_FAIL(self):
        with running_transaction(self):
            t = LockingTransaction.ensureGet()
            LockingTransaction.ensureGet()._updateReadPoint(False)
            LockingTransaction.ensureGet()._updateReadPoint(False)

            # Make another transaction to simulate a conflict (failed ensure)
            # First, write to it in this thread
            t.doSet(self.refZero, 999)
            def secondary(testclass, mainTransaction):
                t = LockingTransaction.ensureGet()
                LockingTransaction.ensureGet()._updateReadPoint(False)
                LockingTransaction.ensureGet()._updateReadPoint(False)

                # Try an ensure that will fail (and cause a bail)
                testclass.assertRaises(TransactionRetryException, t.doEnsure(testclass.refZero))
                self.assertRaises(Exception, self.refZero._lock.release_shared)

    def testRun_PASS(self):
        # Now we'll run a transaction ourselves
        self.refOne = Ref(111, None)
        self.refTwo = Ref(222, None)

        # Our transaction body will do a ref-set and an alter (increment a ref by 1)
        def body():
            # Body of the transaction!
            self.refZero.refSet(999)
            def incr(val):
                return val + 1
            self.refOne.alter(incr, [])

        # Test our transaction actually made the changes it should have
        LockingTransaction.runInTransaction(body)
        self.assertEqual(self.refZero.deref(), 999)
        self.assertEqual(self.refOne.deref(), 112)
        self.assertEqual(self.refTwo.deref(), 222)

        # Test that the transaction ended properly
        self.assertRaises(IllegalStateException, self.refZero.refSet, 999)


########NEW FILE########
__FILENAME__ = subvec_tests
"""subvec-test.py

Wednesday, March 28 2012
"""

import unittest

import clojure.lang.persistentvector as pv
from clojure.lang.apersistentvector import SubVec
from clojure.lang.persistentvector import PersistentVector
from clojure.lang.cljexceptions import IndexOutOfBoundsException

pseudoMetaData = object()

class TestSubVec(unittest.TestCase):
    def setUp(self):
        # [0 1 2 3 4 5 6 7 8 9]
        #         [4 5 6]
        self.parent = pv.vec(range(10))
        self.sv = SubVec(pseudoMetaData, self.parent, 4, 7)
        self.oneItemSv = SubVec(None, self.parent, 0, 1)
    # nth()
    def testNth_PASS(self):
        self.assertEqual(self.sv.nth(0), 4)
        self.assertEqual(self.sv.nth(1), 5)
        self.assertEqual(self.sv.nth(2), 6)
    def testNth_FAIL(self):
        # below lower bound
        # These are accepted in Clojure, but I think it's a bug.
        self.assertRaises(IndexOutOfBoundsException, self.sv.nth, -4)
        self.assertRaises(IndexOutOfBoundsException, self.sv.nth, -3)
        self.assertRaises(IndexOutOfBoundsException, self.sv.nth, -2)
        self.assertRaises(IndexOutOfBoundsException, self.sv.nth, -1)
        # beyond upper bound
        self.assertRaises(IndexOutOfBoundsException, self.sv.nth, 3)
    def testAssocN_PASS(self):
        # mod
        v1 = self.sv.assocN(1, "foo")
        self.assertTrue(isinstance(v1, SubVec))
        self.assertEqual(len(v1), 3)
        self.assertEqual(v1.nth(1), "foo")
        # append
        v2 = self.sv.assocN(3, "foo")
        self.assertTrue(isinstance(v2, SubVec))
        self.assertEqual(len(v2), 4)
        self.assertEqual(v2.nth(3), "foo")
    def testAssocN_FAIL(self):
        self.assertRaises(IndexOutOfBoundsException, self.sv.assocN, -1, "foo")
        self.assertRaises(IndexOutOfBoundsException, self.sv.assocN, 4, "foo")
    # __len__()
    def test__len___PASS(self):
        self.assertEqual(len(self.sv), 3)
    # empty()
    def testEmpty_PASS(self):
        v = self.sv.empty()
        self.assertEqual(v.meta(), self.sv.meta())
    # pop()
    def testtPop_PASS(self):
        emptyV = self.oneItemSv.pop()
        self.assertTrue(isinstance(emptyV, PersistentVector))
        self.assertEqual(len(emptyV), 0)
        oneLessSv = self.sv.pop()
        self.assertTrue(isinstance(oneLessSv, SubVec))
        self.assertEqual(len(oneLessSv), 2)
        
    # No pop fail test because pop returns an empty PersistentVector.
    # There is no empty SubVec.
        
    # meta()
    def testMeta_PASS(self):
        self.assertEqual(pseudoMetaData, self.sv.meta())
    # withMeta()
    def testWithMeta_PASS(self):
        # return self
        outsv = self.sv.withMeta(pseudoMetaData)
        print id(outsv), id(self.sv)
        self.assertTrue(outsv is self.sv)
        # return new SubVec
        meta = object()
        outsv = self.sv.withMeta(meta)
        self.assertTrue(meta, outsv.meta())

########NEW FILE########
__FILENAME__ = threaded-transaction-tests
"""threaded-transaction-tests.py

These tests exercise the LockingTransaction code
in some multithreaded ways. More comprehensive testing
than the tests in ref-tests.py, which test at a more
granular level.

Friday, Oct. 26 2012"""

import unittest, logging
from threading import Thread, current_thread, local, Event
from time import time, sleep
from itertools import count

from clojure.lang.ref import Ref, TVal
from clojure.lang.lockingtransaction import LockingTransaction, TransactionState, Info, loglock
from clojure.lang.cljexceptions import IllegalStateException, TransactionRetryException
from clojure.util.shared_lock import SharedLock
from clojure.lang.threadutil import AtomicInteger

##
# Basic idea: We want to test the corner cases when different transactions that happen concurrently on different
# threads run into each other at a specified time. e.g. if Transaction 1 (T1) does an in-transaction-write of Ref 1 (R1)
# and Transaction 2 (T2) that was started later tries to do a write on R1, T2 should be retried.
#
# In order to test cross-thread behaviour this granularly we need a bit of leg-work.
# 

# Verbose output for debugging
spew_debug = True

class TestThreadedTransactions(unittest.TestCase):
    spawned_threads = []

    def setUp(self):
        self.main_thread = current_thread()
        self.first_run = local()
        self.first_run.data = True

    def tearDown(self):
        # Join all if not joined with yet
        self.join_all()

    def d(self, str):
        """
        Debug helper
        """
        with loglock:
            if spew_debug:
                print str

    def runTransactionInThread(self, func, autostart=True, postcommit=None):
        """
        Runs the desired function in a transaction on a secondary thread. Optionally
        allows the caller to start the thread manually, and takes an optional postcommit
        function that is run after the transaction is committed
        """
        def thread_func(transaction_func, postcommit_func):
            self.first_run.data = True
            LockingTransaction.runInTransaction(transaction_func)
            if postcommit_func:
                postcommit_func()

        t = Thread(target=thread_func, args=[func, postcommit])
        if autostart:
            t.start()
        self.spawned_threads.append(t)

        return t

    def join_all(self):
        """
        Joins all spawned threads to make sure they have all finished before continuing
        """
        for thread in self.spawned_threads:
            thread.join()
        self.spawned_threads = []

    def testSimpleConcurrency(self):
        def t1():
            sleep(.1)
            self.ref0.refSet(1)
        def t2():
            self.ref0.refSet(2)

        # Delaying t1 means it should commit after t2
        self.ref0 = Ref(0, None)
        self.runTransactionInThread(t1)
        self.runTransactionInThread(t2)
        self.join_all()
        self.assertEqual(self.ref0.deref(), 1)

    def testFault(self):
        # We want to cause a fault on one ref, that means no committed value yet
        t1wait = Event()
        t1launched = Event()

        def t1():
            # This thread tries to read the value after t2 has written to it, but it starts first
            self.d("* Before wait")
            t1wait.wait()
            val = self.refA.deref()
            self.d("* Derefed, asserting fault")
            # Make sure we only successfully got here w/ 1 fault (deref() triggered a retry the first time around)
            self.assertEqual(self.refA._faults.get(), 1)
            self.assertEqual(self.refA.historyCount(), 1)
            self.assertEqual(val, 6)

            self.d("* Refsetting after fault")
            # When committed, we should create another tval in the history chain
            self.refA.refSet(7)

        def t2():
            t1launched.wait()

            # This thread does the committing after t1 started but before it reads the value of refA
            self.d("** Creating ref")
            self.refA = Ref(5, None)
            self.refA.refSet(6)

        def t2committed():
            self.d("** Notify")
            t1wait.set()

        self.runTransactionInThread(t1)
        self.runTransactionInThread(t2, postcommit=t2committed)

        self.d("Notifying t1")
        t1launched.set()

        self.join_all()

        # The write after the fault should have created a new history chain item
        self.assertEqual(self.refA.historyCount(), 2)
        self.d("Len: %s" % self.refA.historyCount())

    def testBarge(self):
        # Barging happens when one transaction tries to do an in-transaction-write to a ref that has
        # an in-transaction-value from another transaction
        t1wait = Event()
        t2wait = Event()

        self.t1counter = 0
        self.t2counter = 0
        
        def t1():
            # We do the first in-transaction-write
            self.refA.refSet(888)

            # Don't commit yet, we want t2 to run and barge us
            self.d("* Notify")
            t2wait.set()
            self.d("* Wait")
            t1wait.wait()
            self.d("* Done")

            self.t1counter += 1

        def t2():
            # Wait till t1 has done its write
            self.d("** Wait")
            t2wait.wait()

            # Try to write to the ref
            # We should try and succeed to barge them: we were started first
            # and should be long-lived enough
            self.d("** Before barge")
            self.refA.refSet(777)

            self.d("** After barge")
            sleep(.1)
            t1wait.set()

            self.t2counter += 1
            
        self.refA = Ref(999, None)
        th1 = self.runTransactionInThread(t1, autostart=False)
        th2 = self.runTransactionInThread(t2, autostart=False)

        # Start thread 1 first, give the GIL a cycle so it waits for t2wait
        th2.start()
        sleep(.1)
        th1.start()

        # Wait for the test to finish
        self.join_all()

        # T2 should have successfully barged T1, so T1 should have been re-run
        # The final value of the ref should be 888, as T1 ran last
        self.assertEqual(self.t1counter, 2)
        self.assertEqual(self.t2counter, 1)
        self.assertEqual(self.refA.deref(), 888)

        self.d("Final value of ref: %s and t1 ran %s times" % (self.refA.deref(), self.t1counter))

    def testCommutes(self):
        # Make sure multiple transactions that occur simultaneously each commute the same ref
        # Hard to check for this behaving properly---it should have fewer retries than if each 
        # transaction did an alter, but if transactions commit at the same time one might have to retry
        # anyway. The difference is usually an order of magnitude, so this test is pretty safe

        self.numruns = AtomicInteger()
        self.numalterruns = AtomicInteger()
        numthreads = 20

        def incr(curval):
            return curval + 1

        def adder(curval, extraval):
            return curval + extraval

        def t1():
            self.numruns.getAndIncrement()
            self.refA.commute(incr, [])

        def t2():
            # self.d("Thread %s (%s): ALTER BEING RUN, total retry num: %s" % (current_thread().ident, id(current_thread()), self.numalterruns.getAndIncrement()))
            self.numalterruns.getAndIncrement()
            self.refB.alter(adder, [100])

        self.refA = Ref(0, None)
        self.refB = Ref(0, None)
        for i in range(numthreads):
            self.runTransactionInThread(t1)

        self.join_all()

        for i in range(numthreads):
            self.runTransactionInThread(t2)

        self.join_all()

        self.d("Commute took %s runs and counter is %s" % (self.numruns.get(), self.refA.deref()))
        self.d("Alter took %s runs and counter is %s" % (self.numalterruns.get(), self.refB.deref()))

        self.assertEqual(self.refA.deref(), numthreads)
        self.assertEqual(self.refB.deref(), 2000)
        self.assertTrue(self.numalterruns.get() >= self.numruns.get())

########NEW FILE########
