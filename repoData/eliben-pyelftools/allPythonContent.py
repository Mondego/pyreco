__FILENAME__ = construct_utils
#-------------------------------------------------------------------------------
# elftools: common/construct_utils.py
#
# Some complementary construct utilities
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
from ..construct import Subconstruct, ConstructError, ArrayError


class RepeatUntilExcluding(Subconstruct):
    """ A version of construct's RepeatUntil that doesn't include the last 
        element (which casued the repeat to exit) in the return value.
        
        Only parsing is currently implemented.
        
        P.S. removed some code duplication
    """
    __slots__ = ["predicate"]
    def __init__(self, predicate, subcon):
        Subconstruct.__init__(self, subcon)
        self.predicate = predicate
        self._clear_flag(self.FLAG_COPY_CONTEXT)
        self._set_flag(self.FLAG_DYNAMIC)
    def _parse(self, stream, context):
        obj = []
        try:
            context_for_subcon = context
            if self.subcon.conflags & self.FLAG_COPY_CONTEXT:
                context_for_subcon = context.__copy__()
            
            while True:
                subobj = self.subcon._parse(stream, context_for_subcon)
                if self.predicate(subobj, context):
                    break
                obj.append(subobj)
        except ConstructError as ex:
            raise ArrayError("missing terminator", ex)
        return obj
    def _build(self, obj, stream, context):
        raise NotImplementedError('no building')
    def _sizeof(self, context):
        raise SizeofError("can't calculate size")


########NEW FILE########
__FILENAME__ = exceptions
#-------------------------------------------------------------------------------
# elftools: common/exceptions.py
#
# Exception classes for elftools
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
class ELFError(Exception): 
    pass

class ELFRelocationError(ELFError):
    pass
        
class ELFParseError(ELFError):
    pass

class DWARFError(Exception):
    pass


########NEW FILE########
__FILENAME__ = ordereddict
#-------------------------------------------------------------------------------
# elftools: port of OrderedDict to work on Python < 2.7
#
# Taken from http://code.activestate.com/recipes/576693/ , revision 9
# Code by Raymond Hettinger. License: MIT
#-------------------------------------------------------------------------------
try:
    from thread import get_ident as _get_ident
except ImportError:
    from dummy_thread import get_ident as _get_ident

try:
    from _abcoll import KeysView, ValuesView, ItemsView
except ImportError:
    pass


class OrderedDict(dict):
    'Dictionary that remembers insertion order'
    # An inherited dict maps keys to values.
    # The inherited dict provides __getitem__, __len__, __contains__, and get.
    # The remaining methods are order-aware.
    # Big-O running times for all methods are the same as for regular dictionaries.

    # The internal self.__map dictionary maps keys to links in a doubly linked list.
    # The circular doubly linked list starts and ends with a sentinel element.
    # The sentinel element never gets deleted (this simplifies the algorithm).
    # Each link is stored as a list of length three:  [PREV, NEXT, KEY].

    def __init__(self, *args, **kwds):
        '''Initialize an ordered dictionary.  Signature is the same as for
        regular dictionaries, but keyword arguments are not recommended
        because their insertion order is arbitrary.

        '''
        if len(args) > 1:
            raise TypeError('expected at most 1 arguments, got %d' % len(args))
        try:
            self.__root
        except AttributeError:
            self.__root = root = []                     # sentinel node
            root[:] = [root, root, None]
            self.__map = {}
        self.__update(*args, **kwds)

    def __setitem__(self, key, value, dict_setitem=dict.__setitem__):
        'od.__setitem__(i, y) <==> od[i]=y'
        # Setting a new item creates a new link which goes at the end of the linked
        # list, and the inherited dictionary is updated with the new key/value pair.
        if key not in self:
            root = self.__root
            last = root[0]
            last[1] = root[0] = self.__map[key] = [last, root, key]
        dict_setitem(self, key, value)

    def __delitem__(self, key, dict_delitem=dict.__delitem__):
        'od.__delitem__(y) <==> del od[y]'
        # Deleting an existing item uses self.__map to find the link which is
        # then removed by updating the links in the predecessor and successor nodes.
        dict_delitem(self, key)
        link_prev, link_next, key = self.__map.pop(key)
        link_prev[1] = link_next
        link_next[0] = link_prev

    def __iter__(self):
        'od.__iter__() <==> iter(od)'
        root = self.__root
        curr = root[1]
        while curr is not root:
            yield curr[2]
            curr = curr[1]

    def __reversed__(self):
        'od.__reversed__() <==> reversed(od)'
        root = self.__root
        curr = root[0]
        while curr is not root:
            yield curr[2]
            curr = curr[0]

    def clear(self):
        'od.clear() -> None.  Remove all items from od.'
        try:
            for node in self.__map.itervalues():
                del node[:]
            root = self.__root
            root[:] = [root, root, None]
            self.__map.clear()
        except AttributeError:
            pass
        dict.clear(self)

    def popitem(self, last=True):
        '''od.popitem() -> (k, v), return and remove a (key, value) pair.
        Pairs are returned in LIFO order if last is true or FIFO order if false.

        '''
        if not self:
            raise KeyError('dictionary is empty')
        root = self.__root
        if last:
            link = root[0]
            link_prev = link[0]
            link_prev[1] = root
            root[0] = link_prev
        else:
            link = root[1]
            link_next = link[1]
            root[1] = link_next
            link_next[0] = root
        key = link[2]
        del self.__map[key]
        value = dict.pop(self, key)
        return key, value

    # -- the following methods do not depend on the internal structure --

    def keys(self):
        'od.keys() -> list of keys in od'
        return list(self)

    def values(self):
        'od.values() -> list of values in od'
        return [self[key] for key in self]

    def items(self):
        'od.items() -> list of (key, value) pairs in od'
        return [(key, self[key]) for key in self]

    def iterkeys(self):
        'od.iterkeys() -> an iterator over the keys in od'
        return iter(self)

    def itervalues(self):
        'od.itervalues -> an iterator over the values in od'
        for k in self:
            yield self[k]

    def iteritems(self):
        'od.iteritems -> an iterator over the (key, value) items in od'
        for k in self:
            yield (k, self[k])

    def update(*args, **kwds):
        '''od.update(E, **F) -> None.  Update od from dict/iterable E and F.

        If E is a dict instance, does:           for k in E: od[k] = E[k]
        If E has a .keys() method, does:         for k in E.keys(): od[k] = E[k]
        Or if E is an iterable of items, does:   for k, v in E: od[k] = v
        In either case, this is followed by:     for k, v in F.items(): od[k] = v

        '''
        if len(args) > 2:
            raise TypeError('update() takes at most 2 positional '
                            'arguments (%d given)' % (len(args),))
        elif not args:
            raise TypeError('update() takes at least 1 argument (0 given)')
        self = args[0]
        # Make progressively weaker assumptions about "other"
        other = ()
        if len(args) == 2:
            other = args[1]
        if isinstance(other, dict):
            for key in other:
                self[key] = other[key]
        elif hasattr(other, 'keys'):
            for key in other.keys():
                self[key] = other[key]
        else:
            for key, value in other:
                self[key] = value
        for key, value in kwds.items():
            self[key] = value

    __update = update  # let subclasses override update without breaking __init__

    __marker = object()

    def pop(self, key, default=__marker):
        '''od.pop(k[,d]) -> v, remove specified key and return the corresponding value.
        If key is not found, d is returned if given, otherwise KeyError is raised.

        '''
        if key in self:
            result = self[key]
            del self[key]
            return result
        if default is self.__marker:
            raise KeyError(key)
        return default

    def setdefault(self, key, default=None):
        'od.setdefault(k[,d]) -> od.get(k,d), also set od[k]=d if k not in od'
        if key in self:
            return self[key]
        self[key] = default
        return default

    def __repr__(self, _repr_running={}):
        'od.__repr__() <==> repr(od)'
        call_key = id(self), _get_ident()
        if call_key in _repr_running:
            return '...'
        _repr_running[call_key] = 1
        try:
            if not self:
                return '%s()' % (self.__class__.__name__,)
            return '%s(%r)' % (self.__class__.__name__, self.items())
        finally:
            del _repr_running[call_key]

    def __reduce__(self):
        'Return state information for pickling'
        items = [[k, self[k]] for k in self]
        inst_dict = vars(self).copy()
        for k in vars(OrderedDict()):
            inst_dict.pop(k, None)
        if inst_dict:
            return (self.__class__, (items,), inst_dict)
        return self.__class__, (items,)

    def copy(self):
        'od.copy() -> a shallow copy of od'
        return self.__class__(self)

    @classmethod
    def fromkeys(cls, iterable, value=None):
        '''OD.fromkeys(S[, v]) -> New ordered dictionary with keys from S
        and values equal to v (which defaults to None).

        '''
        d = cls()
        for key in iterable:
            d[key] = value
        return d

    def __eq__(self, other):
        '''od.__eq__(y) <==> od==y.  Comparison to another OD is order-sensitive
        while comparison to a regular mapping is order-insensitive.

        '''
        if isinstance(other, OrderedDict):
            return len(self)==len(other) and self.items() == other.items()
        return dict.__eq__(self, other)

    def __ne__(self, other):
        return not self == other

    # -- the following methods are only used in Python 2.7 --

    def viewkeys(self):
        "od.viewkeys() -> a set-like object providing a view on od's keys"
        return KeysView(self)

    def viewvalues(self):
        "od.viewvalues() -> an object providing a view on od's values"
        return ValuesView(self)

    def viewitems(self):
        "od.viewitems() -> a set-like object providing a view on od's items"
        return ItemsView(self)


########NEW FILE########
__FILENAME__ = py3compat
#-------------------------------------------------------------------------------
# elftools: common/py3compat.py
#
# Python 3 compatibility code
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
import sys
PY3 = sys.version_info[0] == 3


if PY3:
    import io
    StringIO = io.StringIO
    BytesIO = io.BytesIO

    import collections
    OrderedDict = collections.OrderedDict

    _iterkeys = "keys"
    _iteritems = "items"
    _itervalues = "values"

    def bytes2str(b): return b.decode('latin-1')
    def str2bytes(s): return s.encode('latin-1')
    def int2byte(i):return bytes((i,))
    def byte2int(b): return b

    ifilter = filter

    maxint = sys.maxsize
else:
    import cStringIO
    StringIO = BytesIO = cStringIO.StringIO

    from .ordereddict import OrderedDict

    _iterkeys = "iterkeys"
    _iteritems = "iteritems"
    _itervalues = "itervalues"

    def bytes2str(b): return b
    def str2bytes(s): return s
    int2byte = chr
    byte2int = ord

    from itertools import ifilter

    maxint = sys.maxint


def iterkeys(d):
    """Return an iterator over the keys of a dictionary."""
    return getattr(d, _iterkeys)()

def itervalues(d):
    """Return an iterator over the values of a dictionary."""
    return getattr(d, _itervalues)()

def iteritems(d):
    """Return an iterator over the items of a dictionary."""
    return getattr(d, _iteritems)()


########NEW FILE########
__FILENAME__ = utils
#-------------------------------------------------------------------------------
# elftools: common/utils.py
#
# Miscellaneous utilities for elftools
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
from contextlib import contextmanager
from .exceptions import ELFParseError, ELFError, DWARFError
from .py3compat import int2byte
from ..construct import ConstructError


def bytelist2string(bytelist):
    """ Convert a list of byte values (e.g. [0x10 0x20 0x00]) to a bytes object
        (e.g. b'\x10\x20\x00').
    """
    return b''.join(int2byte(b) for b in bytelist)


def struct_parse(struct, stream, stream_pos=None):
    """ Convenience function for using the given struct to parse a stream.
        If stream_pos is provided, the stream is seeked to this position before
        the parsing is done. Otherwise, the current position of the stream is
        used.
        Wraps the error thrown by construct with ELFParseError.
    """
    try:
        if stream_pos is not None:
            stream.seek(stream_pos)
        return struct.parse_stream(stream)
    except ConstructError as e:
        raise ELFParseError(e.message)


def parse_cstring_from_stream(stream, stream_pos=None):
    """ Parse a C-string from the given stream. The string is returned without
        the terminating \x00 byte. If the terminating byte wasn't found, None
        is returned (the stream is exhausted).
        If stream_pos is provided, the stream is seeked to this position before
        the parsing is done. Otherwise, the current position of the stream is
        used.
        Note: a bytes object is returned here, because this is what's read from
        the binary file.
    """
    if stream_pos is not None:
        stream.seek(stream_pos)
    CHUNKSIZE = 64
    chunks = []
    found = False
    while True:
        chunk = stream.read(CHUNKSIZE)
        end_index = chunk.find(b'\x00')
        if end_index >= 0:
            chunks.append(chunk[:end_index])
            found = True
            break
        else:
            chunks.append(chunk)
        if len(chunk) < CHUNKSIZE:
            break
    return b''.join(chunks) if found else None


def elf_assert(cond, msg=''):
    """ Assert that cond is True, otherwise raise ELFError(msg)
    """
    _assert_with_exception(cond, msg, ELFError)


def dwarf_assert(cond, msg=''):
    """ Assert that cond is True, otherwise raise DWARFError(msg)
    """
    _assert_with_exception(cond, msg, DWARFError)


@contextmanager
def preserve_stream_pos(stream):
    """ Usage:
        # stream has some position FOO (return value of stream.tell())
        with preserve_stream_pos(stream):
            # do stuff that manipulates the stream
        # stream still has position FOO
    """
    saved_pos = stream.tell()
    yield
    stream.seek(saved_pos)


#------------------------- PRIVATE -------------------------

def _assert_with_exception(cond, msg, exception_type):
    if not cond:
        raise exception_type(msg)


########NEW FILE########
__FILENAME__ = adapters
from .core import Adapter, AdaptationError, Pass
from .lib import int_to_bin, bin_to_int, swap_bytes
from .lib import FlagsContainer, HexString
from .lib.py3compat import BytesIO, decodebytes


#===============================================================================
# exceptions
#===============================================================================
class BitIntegerError(AdaptationError):
    __slots__ = []
class MappingError(AdaptationError):
    __slots__ = []
class ConstError(AdaptationError):
    __slots__ = []
class ValidationError(AdaptationError):
    __slots__ = []
class PaddingError(AdaptationError):
    __slots__ = []

#===============================================================================
# adapters
#===============================================================================
class BitIntegerAdapter(Adapter):
    """
    Adapter for bit-integers (converts bitstrings to integers, and vice versa).
    See BitField.
    
    Parameters:
    * subcon - the subcon to adapt
    * width - the size of the subcon, in bits
    * swapped - whether to swap byte order (little endian/big endian). 
      default is False (big endian)
    * signed - whether the value is signed (two's complement). the default
      is False (unsigned)
    * bytesize - number of bits per byte, used for byte-swapping (if swapped).
      default is 8.
    """
    __slots__ = ["width", "swapped", "signed", "bytesize"]
    def __init__(self, subcon, width, swapped = False, signed = False, 
                 bytesize = 8):
        Adapter.__init__(self, subcon)
        self.width = width
        self.swapped = swapped
        self.signed = signed
        self.bytesize = bytesize
    def _encode(self, obj, context):
        if obj < 0 and not self.signed:
            raise BitIntegerError("object is negative, but field is not signed",
                obj)
        obj2 = int_to_bin(obj, width = self.width)
        if self.swapped:
            obj2 = swap_bytes(obj2, bytesize = self.bytesize)
        return obj2
    def _decode(self, obj, context):
        if self.swapped:
            obj = swap_bytes(obj, bytesize = self.bytesize)
        return bin_to_int(obj, signed = self.signed)

class MappingAdapter(Adapter):
    """
    Adapter that maps objects to other objects.
    See SymmetricMapping and Enum.
    
    Parameters:
    * subcon - the subcon to map
    * decoding - the decoding (parsing) mapping (a dict)
    * encoding - the encoding (building) mapping (a dict)
    * decdefault - the default return value when the object is not found
      in the decoding mapping. if no object is given, an exception is raised.
      if `Pass` is used, the unmapped object will be passed as-is
    * encdefault - the default return value when the object is not found
      in the encoding mapping. if no object is given, an exception is raised.
      if `Pass` is used, the unmapped object will be passed as-is
    """
    __slots__ = ["encoding", "decoding", "encdefault", "decdefault"]
    def __init__(self, subcon, decoding, encoding, 
                 decdefault = NotImplemented, encdefault = NotImplemented):
        Adapter.__init__(self, subcon)
        self.decoding = decoding
        self.encoding = encoding
        self.decdefault = decdefault
        self.encdefault = encdefault
    def _encode(self, obj, context):
        try:
            return self.encoding[obj]
        except (KeyError, TypeError):
            if self.encdefault is NotImplemented:
                raise MappingError("no encoding mapping for %r [%s]" % (
                    obj, self.subcon.name))
            if self.encdefault is Pass:
                return obj
            return self.encdefault
    def _decode(self, obj, context):
        try:
            return self.decoding[obj]
        except (KeyError, TypeError):
            if self.decdefault is NotImplemented:
                raise MappingError("no decoding mapping for %r [%s]" % (
                    obj, self.subcon.name))
            if self.decdefault is Pass:
                return obj
            return self.decdefault

class FlagsAdapter(Adapter):
    """
    Adapter for flag fields. Each flag is extracted from the number, resulting
    in a FlagsContainer object. Not intended for direct usage.
    See FlagsEnum.
    
    Parameters
    * subcon - the subcon to extract
    * flags - a dictionary mapping flag-names to their value
    """
    __slots__ = ["flags"]
    def __init__(self, subcon, flags):
        Adapter.__init__(self, subcon)
        self.flags = flags
    def _encode(self, obj, context):
        flags = 0
        for name, value in self.flags.items():
            if getattr(obj, name, False):
                flags |= value
        return flags
    def _decode(self, obj, context):
        obj2 = FlagsContainer()
        for name, value in self.flags.items():
            setattr(obj2, name, bool(obj & value))
        return obj2

class StringAdapter(Adapter):
    """
    Adapter for strings. Converts a sequence of characters into a python 
    string, and optionally handles character encoding.
    See String.
    
    Parameters:
    * subcon - the subcon to convert
    * encoding - the character encoding name (e.g., "utf8"), or None to 
      return raw bytes (usually 8-bit ASCII).
    """
    __slots__ = ["encoding"]
    def __init__(self, subcon, encoding = None):
        Adapter.__init__(self, subcon)
        self.encoding = encoding
    def _encode(self, obj, context):
        if self.encoding:
            obj = obj.encode(self.encoding)
        return obj
    def _decode(self, obj, context):
        if self.encoding:
            obj = obj.decode(self.encoding)
        return obj

class PaddedStringAdapter(Adapter):
    r"""
    Adapter for padded strings.
    See String.
    
    Parameters:
    * subcon - the subcon to adapt
    * padchar - the padding character. default is "\x00".
    * paddir - the direction where padding is placed ("right", "left", or 
      "center"). the default is "right". 
    * trimdir - the direction where trimming will take place ("right" or 
      "left"). the default is "right". trimming is only meaningful for
      building, when the given string is too long. 
    """
    __slots__ = ["padchar", "paddir", "trimdir"]
    def __init__(self, subcon, padchar = "\x00", paddir = "right", 
                 trimdir = "right"):
        if paddir not in ("right", "left", "center"):
            raise ValueError("paddir must be 'right', 'left' or 'center'", 
                paddir)
        if trimdir not in ("right", "left"):
            raise ValueError("trimdir must be 'right' or 'left'", trimdir)
        Adapter.__init__(self, subcon)
        self.padchar = padchar
        self.paddir = paddir
        self.trimdir = trimdir
    def _decode(self, obj, context):
        if self.paddir == "right":
            obj = obj.rstrip(self.padchar)
        elif self.paddir == "left":
            obj = obj.lstrip(self.padchar)
        else:
            obj = obj.strip(self.padchar)
        return obj
    def _encode(self, obj, context):
        size = self._sizeof(context)
        if self.paddir == "right":
            obj = obj.ljust(size, self.padchar)
        elif self.paddir == "left":
            obj = obj.rjust(size, self.padchar)
        else:
            obj = obj.center(size, self.padchar)
        if len(obj) > size:
            if self.trimdir == "right":
                obj = obj[:size]
            else:
                obj = obj[-size:]
        return obj

class LengthValueAdapter(Adapter):
    """
    Adapter for length-value pairs. It extracts only the value from the 
    pair, and calculates the length based on the value.
    See PrefixedArray and PascalString.
    
    Parameters:
    * subcon - the subcon returning a length-value pair
    """
    __slots__ = []
    def _encode(self, obj, context):
        return (len(obj), obj)
    def _decode(self, obj, context):
        return obj[1]

class CStringAdapter(StringAdapter):
    r"""
    Adapter for C-style strings (strings terminated by a terminator char).
    
    Parameters:
    * subcon - the subcon to convert
    * terminators - a sequence of terminator chars. default is "\x00".
    * encoding - the character encoding to use (e.g., "utf8"), or None to
      return raw-bytes. the terminator characters are not affected by the 
      encoding.
    """
    __slots__ = ["terminators"]
    def __init__(self, subcon, terminators = b"\x00", encoding = None):
        StringAdapter.__init__(self, subcon, encoding = encoding)
        self.terminators = terminators
    def _encode(self, obj, context):
        return StringAdapter._encode(self, obj, context) + self.terminators[0:1]
    def _decode(self, obj, context):
        return StringAdapter._decode(self, b''.join(obj[:-1]), context)

class TunnelAdapter(Adapter):
    """
    Adapter for tunneling (as in protocol tunneling). A tunnel is construct
    nested upon another (layering). For parsing, the lower layer first parses
    the data (note: it must return a string!), then the upper layer is called
    to parse that data (bottom-up). For building it works in a top-down manner;
    first the upper layer builds the data, then the lower layer takes it and
    writes it to the stream.
    
    Parameters:
    * subcon - the lower layer subcon
    * inner_subcon - the upper layer (tunneled/nested) subcon
    
    Example:
    # a pascal string containing compressed data (zlib encoding), so first
    # the string is read, decompressed, and finally re-parsed as an array
    # of UBInt16
    TunnelAdapter(
        PascalString("data", encoding = "zlib"),
        GreedyRange(UBInt16("elements"))
    )
    """
    __slots__ = ["inner_subcon"]
    def __init__(self, subcon, inner_subcon):
        Adapter.__init__(self, subcon)
        self.inner_subcon = inner_subcon
    def _decode(self, obj, context):
        return self.inner_subcon._parse(BytesIO(obj), context)
    def _encode(self, obj, context):
        stream = BytesIO()
        self.inner_subcon._build(obj, stream, context)
        return stream.getvalue()

class ExprAdapter(Adapter):
    """
    A generic adapter that accepts 'encoder' and 'decoder' as parameters. You
    can use ExprAdapter instead of writing a full-blown class when only a 
    simple expression is needed.
    
    Parameters:
    * subcon - the subcon to adapt
    * encoder - a function that takes (obj, context) and returns an encoded 
      version of obj
    * decoder - a function that takes (obj, context) and returns an decoded 
      version of obj
    
    Example:
    ExprAdapter(UBInt8("foo"), 
        encoder = lambda obj, ctx: obj / 4,
        decoder = lambda obj, ctx: obj * 4,
    )
    """
    __slots__ = ["_encode", "_decode"]
    def __init__(self, subcon, encoder, decoder):
        Adapter.__init__(self, subcon)
        self._encode = encoder
        self._decode = decoder

class HexDumpAdapter(Adapter):
    """
    Adapter for hex-dumping strings. It returns a HexString, which is a string
    """
    __slots__ = ["linesize"]
    def __init__(self, subcon, linesize = 16):
        Adapter.__init__(self, subcon)
        self.linesize = linesize
    def _encode(self, obj, context):
        return obj
    def _decode(self, obj, context):
        return HexString(obj, linesize = self.linesize)

class ConstAdapter(Adapter):
    """
    Adapter for enforcing a constant value ("magic numbers"). When decoding,
    the return value is checked; when building, the value is substituted in.
    
    Parameters:
    * subcon - the subcon to validate
    * value - the expected value
    
    Example:
    Const(Field("signature", 2), "MZ")
    """
    __slots__ = ["value"]
    def __init__(self, subcon, value):
        Adapter.__init__(self, subcon)
        self.value = value
    def _encode(self, obj, context):
        if obj is None or obj == self.value:
            return self.value
        else:
            raise ConstError("expected %r, found %r" % (self.value, obj))
    def _decode(self, obj, context):
        if obj != self.value:
            raise ConstError("expected %r, found %r" % (self.value, obj))
        return obj

class SlicingAdapter(Adapter):
    """
    Adapter for slicing a list (getting a slice from that list)
    
    Parameters:
    * subcon - the subcon to slice
    * start - start index
    * stop - stop index (or None for up-to-end)
    * step - step (or None for every element)
    """
    __slots__ = ["start", "stop", "step"]
    def __init__(self, subcon, start, stop = None):
        Adapter.__init__(self, subcon)
        self.start = start
        self.stop = stop
    def _encode(self, obj, context):
        if self.start is None:
            return obj
        return [None] * self.start + obj
    def _decode(self, obj, context):
        return obj[self.start:self.stop]

class IndexingAdapter(Adapter):
    """
    Adapter for indexing a list (getting a single item from that list)
    
    Parameters:
    * subcon - the subcon to index
    * index - the index of the list to get
    """
    __slots__ = ["index"]
    def __init__(self, subcon, index):
        Adapter.__init__(self, subcon)
        if type(index) is not int:
            raise TypeError("index must be an integer", type(index))
        self.index = index
    def _encode(self, obj, context):
        return [None] * self.index + [obj]
    def _decode(self, obj, context):
        return obj[self.index]

class PaddingAdapter(Adapter):
    r"""
    Adapter for padding.
    
    Parameters:
    * subcon - the subcon to pad
    * pattern - the padding pattern (character). default is "\x00"
    * strict - whether or not to verify, during parsing, that the given 
      padding matches the padding pattern. default is False (unstrict)
    """
    __slots__ = ["pattern", "strict"]
    def __init__(self, subcon, pattern = "\x00", strict = False):
        Adapter.__init__(self, subcon)
        self.pattern = pattern
        self.strict = strict
    def _encode(self, obj, context):
        return self._sizeof(context) * self.pattern
    def _decode(self, obj, context):
        if self.strict:
            expected = self._sizeof(context) * self.pattern
            if obj != expected:
                raise PaddingError("expected %r, found %r" % (expected, obj))
        return obj


#===============================================================================
# validators
#===============================================================================
class Validator(Adapter):
    """
    Abstract class: validates a condition on the encoded/decoded object. 
    Override _validate(obj, context) in deriving classes.
    
    Parameters:
    * subcon - the subcon to validate
    """
    __slots__ = []
    def _decode(self, obj, context):
        if not self._validate(obj, context):
            raise ValidationError("invalid object", obj)
        return obj
    def _encode(self, obj, context):
        return self._decode(obj, context)
    def _validate(self, obj, context):
        raise NotImplementedError()

class OneOf(Validator):
    """
    Validates that the object is one of the listed values.

    :param ``Construct`` subcon: object to validate
    :param iterable valids: a set of valid values

    >>> OneOf(UBInt8("foo"), [4,5,6,7]).parse("\\x05")
    5
    >>> OneOf(UBInt8("foo"), [4,5,6,7]).parse("\\x08")
    Traceback (most recent call last):
        ...
    construct.core.ValidationError: ('invalid object', 8)
    >>>
    >>> OneOf(UBInt8("foo"), [4,5,6,7]).build(5)
    '\\x05'
    >>> OneOf(UBInt8("foo"), [4,5,6,7]).build(9)
    Traceback (most recent call last):
        ...
    construct.core.ValidationError: ('invalid object', 9)
    """
    __slots__ = ["valids"]
    def __init__(self, subcon, valids):
        Validator.__init__(self, subcon)
        self.valids = valids
    def _validate(self, obj, context):
        return obj in self.valids

class NoneOf(Validator):
    """
    Validates that the object is none of the listed values.

    :param ``Construct`` subcon: object to validate
    :param iterable invalids: a set of invalid values

    >>> NoneOf(UBInt8("foo"), [4,5,6,7]).parse("\\x08")
    8
    >>> NoneOf(UBInt8("foo"), [4,5,6,7]).parse("\\x06")
    Traceback (most recent call last):
        ...
    construct.core.ValidationError: ('invalid object', 6)
    """
    __slots__ = ["invalids"]
    def __init__(self, subcon, invalids):
        Validator.__init__(self, subcon)
        self.invalids = invalids
    def _validate(self, obj, context):
        return obj not in self.invalids

########NEW FILE########
__FILENAME__ = core
from struct import Struct as Packer

from .lib.py3compat import BytesIO, advance_iterator, bchr
from .lib import Container, ListContainer, LazyContainer


#===============================================================================
# exceptions
#===============================================================================
class ConstructError(Exception):
    __slots__ = []
class FieldError(ConstructError):
    __slots__ = []
class SizeofError(ConstructError):
    __slots__ = []
class AdaptationError(ConstructError):
    __slots__ = []
class ArrayError(ConstructError):
    __slots__ = []
class RangeError(ConstructError):
    __slots__ = []
class SwitchError(ConstructError):
    __slots__ = []
class SelectError(ConstructError):
    __slots__ = []
class TerminatorError(ConstructError):
    __slots__ = []

#===============================================================================
# abstract constructs
#===============================================================================
class Construct(object):
    """
    The mother of all constructs.

    This object is generally not directly instantiated, and it does not
    directly implement parsing and building, so it is largely only of interest
    to subclass implementors.

    The external user API:

     * parse()
     * parse_stream()
     * build()
     * build_stream()
     * sizeof()

    Subclass authors should not override the external methods. Instead,
    another API is available:

     * _parse()
     * _build()
     * _sizeof()

    There is also a flag API:

     * _set_flag()
     * _clear_flag()
     * _inherit_flags()
     * _is_flag()

    And stateful copying:

     * __getstate__()
     * __setstate__()

    Attributes and Inheritance
    ==========================

    All constructs have a name and flags. The name is used for naming struct
    members and context dictionaries. Note that the name can either be a
    string, or None if the name is not needed. A single underscore ("_") is a
    reserved name, and so are names starting with a less-than character ("<").
    The name should be descriptive, short, and valid as a Python identifier,
    although these rules are not enforced.

    The flags specify additional behavioral information about this construct.
    Flags are used by enclosing constructs to determine a proper course of
    action. Flags are inherited by default, from inner subconstructs to outer
    constructs. The enclosing construct may set new flags or clear existing
    ones, as necessary.

    For example, if FLAG_COPY_CONTEXT is set, repeaters will pass a copy of
    the context for each iteration, which is necessary for OnDemand parsing.
    """

    FLAG_COPY_CONTEXT          = 0x0001
    FLAG_DYNAMIC               = 0x0002
    FLAG_EMBED                 = 0x0004
    FLAG_NESTING               = 0x0008

    __slots__ = ["name", "conflags"]
    def __init__(self, name, flags = 0):
        if name is not None:
            if type(name) is not str:
                raise TypeError("name must be a string or None", name)
            if name == "_" or name.startswith("<"):
                raise ValueError("reserved name", name)
        self.name = name
        self.conflags = flags

    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, self.name)

    def _set_flag(self, flag):
        """
        Set the given flag or flags.

        :param int flag: flag to set; may be OR'd combination of flags
        """

        self.conflags |= flag

    def _clear_flag(self, flag):
        """
        Clear the given flag or flags.

        :param int flag: flag to clear; may be OR'd combination of flags
        """

        self.conflags &= ~flag

    def _inherit_flags(self, *subcons):
        """
        Pull flags from subconstructs.
        """

        for sc in subcons:
            self._set_flag(sc.conflags)

    def _is_flag(self, flag):
        """
        Check whether a given flag is set.

        :param int flag: flag to check
        """

        return bool(self.conflags & flag)

    def __getstate__(self):
        """
        Obtain a dictionary representing this construct's state.
        """

        attrs = {}
        if hasattr(self, "__dict__"):
            attrs.update(self.__dict__)
        slots = []
        c = self.__class__
        while c is not None:
            if hasattr(c, "__slots__"):
                slots.extend(c.__slots__)
            c = c.__base__
        for name in slots:
            if hasattr(self, name):
                attrs[name] = getattr(self, name)
        return attrs

    def __setstate__(self, attrs):
        """
        Set this construct's state to a given state.
        """
        for name, value in attrs.items():
            setattr(self, name, value)

    def __copy__(self):
        """returns a copy of this construct"""
        self2 = object.__new__(self.__class__)
        self2.__setstate__(self.__getstate__())
        return self2

    def parse(self, data):
        """
        Parse an in-memory buffer.

        Strings, buffers, memoryviews, and other complete buffers can be
        parsed with this method.
        """

        return self.parse_stream(BytesIO(data))

    def parse_stream(self, stream):
        """
        Parse a stream.

        Files, pipes, sockets, and other streaming sources of data are handled
        by this method.
        """

        return self._parse(stream, Container())

    def _parse(self, stream, context):
        """
        Override me in your subclass.
        """

        raise NotImplementedError()

    def build(self, obj):
        """
        Build an object in memory.
        """
        stream = BytesIO()
        self.build_stream(obj, stream)
        return stream.getvalue()

    def build_stream(self, obj, stream):
        """
        Build an object directly into a stream.
        """
        self._build(obj, stream, Container())

    def _build(self, obj, stream, context):
        """
        Override me in your subclass.
        """

        raise NotImplementedError()

    def sizeof(self, context=None):
        """
        Calculate the size of this object, optionally using a context.

        Some constructs have no fixed size and can only know their size for a
        given hunk of data; these constructs will raise an error if they are
        not passed a context.

        :param ``Container`` context: contextual data

        :returns: int of the length of this construct
        :raises SizeofError: the size could not be determined
        """

        if context is None:
            context = Container()
        try:
            return self._sizeof(context)
        except Exception as e:
            raise SizeofError(e)

    def _sizeof(self, context):
        """
        Override me in your subclass.
        """

        raise SizeofError("Raw Constructs have no size!")

class Subconstruct(Construct):
    """
    Abstract subconstruct (wraps an inner construct, inheriting its
    name and flags).

    Parameters:
    * subcon - the construct to wrap
    """
    __slots__ = ["subcon"]
    def __init__(self, subcon):
        Construct.__init__(self, subcon.name, subcon.conflags)
        self.subcon = subcon
    def _parse(self, stream, context):
        return self.subcon._parse(stream, context)
    def _build(self, obj, stream, context):
        self.subcon._build(obj, stream, context)
    def _sizeof(self, context):
        return self.subcon._sizeof(context)

class Adapter(Subconstruct):
    """
    Abstract adapter: calls _decode for parsing and _encode for building.

    Parameters:
    * subcon - the construct to wrap
    """
    __slots__ = []
    def _parse(self, stream, context):
        return self._decode(self.subcon._parse(stream, context), context)
    def _build(self, obj, stream, context):
        self.subcon._build(self._encode(obj, context), stream, context)
    def _decode(self, obj, context):
        raise NotImplementedError()
    def _encode(self, obj, context):
        raise NotImplementedError()


#===============================================================================
# Fields
#===============================================================================
def _read_stream(stream, length):
    if length < 0:
        raise ValueError("length must be >= 0", length)
    data = stream.read(length)
    if len(data) != length:
        raise FieldError("expected %d, found %d" % (length, len(data)))
    return data

def _write_stream(stream, length, data):
    if length < 0:
        raise ValueError("length must be >= 0", length)
    if len(data) != length:
        raise FieldError("expected %d, found %d" % (length, len(data)))
    stream.write(data)

class StaticField(Construct):
    """
    A fixed-size byte field.

    :param str name: field name
    :param int length: number of bytes in the field
    """

    __slots__ = ["length"]
    def __init__(self, name, length):
        Construct.__init__(self, name)
        self.length = length
    def _parse(self, stream, context):
        return _read_stream(stream, self.length)
    def _build(self, obj, stream, context):
        _write_stream(stream, self.length, obj)
    def _sizeof(self, context):
        return self.length

class FormatField(StaticField):
    """
    A field that uses ``struct`` to pack and unpack data.

    See ``struct`` documentation for instructions on crafting format strings.

    :param str name: name of the field
    :param str endianness: format endianness string; one of "<", ">", or "="
    :param str format: a single format character
    """

    __slots__ = ["packer"]
    def __init__(self, name, endianity, format):
        if endianity not in (">", "<", "="):
            raise ValueError("endianity must be be '=', '<', or '>'",
                endianity)
        if len(format) != 1:
            raise ValueError("must specify one and only one format char")
        self.packer = Packer(endianity + format)
        StaticField.__init__(self, name, self.packer.size)
    def __getstate__(self):
        attrs = StaticField.__getstate__(self)
        attrs["packer"] = attrs["packer"].format
        return attrs
    def __setstate__(self, attrs):
        attrs["packer"] = Packer(attrs["packer"])
        return StaticField.__setstate__(attrs)
    def _parse(self, stream, context):
        try:
            return self.packer.unpack(_read_stream(stream, self.length))[0]
        except Exception as ex:
            raise FieldError(ex)
    def _build(self, obj, stream, context):
        try:
            _write_stream(stream, self.length, self.packer.pack(obj))
        except Exception as ex:
            raise FieldError(ex)

class MetaField(Construct):
    """
    A variable-length field. The length is obtained at runtime from a
    function.

    :param str name: name of the field
    :param callable lengthfunc: callable that takes a context and returns
                                length as an int

    >>> foo = Struct("foo",
    ...     Byte("length"),
    ...     MetaField("data", lambda ctx: ctx["length"])
    ... )
    >>> foo.parse("\\x03ABC")
    Container(data = 'ABC', length = 3)
    >>> foo.parse("\\x04ABCD")
    Container(data = 'ABCD', length = 4)
    """

    __slots__ = ["lengthfunc"]
    def __init__(self, name, lengthfunc):
        Construct.__init__(self, name)
        self.lengthfunc = lengthfunc
        self._set_flag(self.FLAG_DYNAMIC)
    def _parse(self, stream, context):
        return _read_stream(stream, self.lengthfunc(context))
    def _build(self, obj, stream, context):
        _write_stream(stream, self.lengthfunc(context), obj)
    def _sizeof(self, context):
        return self.lengthfunc(context)


#===============================================================================
# arrays and repeaters
#===============================================================================
class MetaArray(Subconstruct):
    """
    An array (repeater) of a meta-count. The array will iterate exactly
    `countfunc()` times. Will raise ArrayError if less elements are found.
    See also Array, Range and RepeatUntil.

    Parameters:
    * countfunc - a function that takes the context as a parameter and returns
      the number of elements of the array (count)
    * subcon - the subcon to repeat `countfunc()` times

    Example:
    MetaArray(lambda ctx: 5, UBInt8("foo"))
    """
    __slots__ = ["countfunc"]
    def __init__(self, countfunc, subcon):
        Subconstruct.__init__(self, subcon)
        self.countfunc = countfunc
        self._clear_flag(self.FLAG_COPY_CONTEXT)
        self._set_flag(self.FLAG_DYNAMIC)
    def _parse(self, stream, context):
        obj = ListContainer()
        c = 0
        count = self.countfunc(context)
        try:
            if self.subcon.conflags & self.FLAG_COPY_CONTEXT:
                while c < count:
                    obj.append(self.subcon._parse(stream, context.__copy__()))
                    c += 1
            else:
                while c < count:
                    obj.append(self.subcon._parse(stream, context))
                    c += 1
        except ConstructError as ex:
            raise ArrayError("expected %d, found %d" % (count, c), ex)
        return obj
    def _build(self, obj, stream, context):
        count = self.countfunc(context)
        if len(obj) != count:
            raise ArrayError("expected %d, found %d" % (count, len(obj)))
        if self.subcon.conflags & self.FLAG_COPY_CONTEXT:
            for subobj in obj:
                self.subcon._build(subobj, stream, context.__copy__())
        else:
            for subobj in obj:
                self.subcon._build(subobj, stream, context)
    def _sizeof(self, context):
        return self.subcon._sizeof(context) * self.countfunc(context)

class Range(Subconstruct):
    """
    A range-array. The subcon will iterate between `mincount` to `maxcount`
    times. If less than `mincount` elements are found, raises RangeError.
    See also GreedyRange and OptionalGreedyRange.

    The general-case repeater. Repeats the given unit for at least mincount
    times, and up to maxcount times. If an exception occurs (EOF, validation
    error), the repeater exits. If less than mincount units have been
    successfully parsed, a RangeError is raised.

    .. note::
       This object requires a seekable stream for parsing.

    :param int mincount: the minimal count
    :param int maxcount: the maximal count
    :param Construct subcon: the subcon to repeat

    >>> c = Range(3, 7, UBInt8("foo"))
    >>> c.parse("\\x01\\x02")
    Traceback (most recent call last):
      ...
    construct.core.RangeError: expected 3..7, found 2
    >>> c.parse("\\x01\\x02\\x03")
    [1, 2, 3]
    >>> c.parse("\\x01\\x02\\x03\\x04\\x05\\x06")
    [1, 2, 3, 4, 5, 6]
    >>> c.parse("\\x01\\x02\\x03\\x04\\x05\\x06\\x07")
    [1, 2, 3, 4, 5, 6, 7]
    >>> c.parse("\\x01\\x02\\x03\\x04\\x05\\x06\\x07\\x08\\x09")
    [1, 2, 3, 4, 5, 6, 7]
    >>> c.build([1,2])
    Traceback (most recent call last):
      ...
    construct.core.RangeError: expected 3..7, found 2
    >>> c.build([1,2,3,4])
    '\\x01\\x02\\x03\\x04'
    >>> c.build([1,2,3,4,5,6,7,8])
    Traceback (most recent call last):
      ...
    construct.core.RangeError: expected 3..7, found 8
    """

    __slots__ = ["mincount", "maxcout"]
    def __init__(self, mincount, maxcout, subcon):
        Subconstruct.__init__(self, subcon)
        self.mincount = mincount
        self.maxcout = maxcout
        self._clear_flag(self.FLAG_COPY_CONTEXT)
        self._set_flag(self.FLAG_DYNAMIC)
    def _parse(self, stream, context):
        obj = ListContainer()
        c = 0
        try:
            if self.subcon.conflags & self.FLAG_COPY_CONTEXT:
                while c < self.maxcout:
                    pos = stream.tell()
                    obj.append(self.subcon._parse(stream, context.__copy__()))
                    c += 1
            else:
                while c < self.maxcout:
                    pos = stream.tell()
                    obj.append(self.subcon._parse(stream, context))
                    c += 1
        except ConstructError as ex:
            if c < self.mincount:
                raise RangeError("expected %d to %d, found %d" %
                    (self.mincount, self.maxcout, c), ex)
            stream.seek(pos)
        return obj
    def _build(self, obj, stream, context):
        if len(obj) < self.mincount or len(obj) > self.maxcout:
            raise RangeError("expected %d to %d, found %d" %
                (self.mincount, self.maxcout, len(obj)))
        cnt = 0
        try:
            if self.subcon.conflags & self.FLAG_COPY_CONTEXT:
                for subobj in obj:
                    if isinstance(obj, bytes):
                        subobj = bchr(subobj)
                    self.subcon._build(subobj, stream, context.__copy__())
                    cnt += 1
            else:
                for subobj in obj:
                    if isinstance(obj, bytes):
                        subobj = bchr(subobj)
                    self.subcon._build(subobj, stream, context)
                    cnt += 1
        except ConstructError as ex:
            if cnt < self.mincount:
                raise RangeError("expected %d to %d, found %d" %
                    (self.mincount, self.maxcout, len(obj)), ex)
    def _sizeof(self, context):
        raise SizeofError("can't calculate size")

class RepeatUntil(Subconstruct):
    """
    An array that repeats until the predicate indicates it to stop. Note that
    the last element (which caused the repeat to exit) is included in the
    return value.

    Parameters:
    * predicate - a predicate function that takes (obj, context) and returns
      True if the stop-condition is met, or False to continue.
    * subcon - the subcon to repeat.

    Example:
    # will read chars until b\x00 (inclusive)
    RepeatUntil(lambda obj, ctx: obj == b"\x00",
        Field("chars", 1)
    )
    """
    __slots__ = ["predicate"]
    def __init__(self, predicate, subcon):
        Subconstruct.__init__(self, subcon)
        self.predicate = predicate
        self._clear_flag(self.FLAG_COPY_CONTEXT)
        self._set_flag(self.FLAG_DYNAMIC)
    def _parse(self, stream, context):
        obj = []
        try:
            if self.subcon.conflags & self.FLAG_COPY_CONTEXT:
                while True:
                    subobj = self.subcon._parse(stream, context.__copy__())
                    obj.append(subobj)
                    if self.predicate(subobj, context):
                        break
            else:
                while True:
                    subobj = self.subcon._parse(stream, context)
                    obj.append(subobj)
                    if self.predicate(subobj, context):
                        break
        except ConstructError as ex:
            raise ArrayError("missing terminator", ex)
        return obj
    def _build(self, obj, stream, context):
        terminated = False
        if self.subcon.conflags & self.FLAG_COPY_CONTEXT:
            for subobj in obj:
                self.subcon._build(subobj, stream, context.__copy__())
                if self.predicate(subobj, context):
                    terminated = True
                    break
        else:
            for subobj in obj:
                subobj = bchr(subobj)
                self.subcon._build(subobj, stream, context.__copy__())
                if self.predicate(subobj, context):
                    terminated = True
                    break
        if not terminated:
            raise ArrayError("missing terminator")
    def _sizeof(self, context):
        raise SizeofError("can't calculate size")


#===============================================================================
# structures and sequences
#===============================================================================
class Struct(Construct):
    """
    A sequence of named constructs, similar to structs in C. The elements are
    parsed and built in the order they are defined.
    See also Embedded.

    Parameters:
    * name - the name of the structure
    * subcons - a sequence of subconstructs that make up this structure.
    * nested - a keyword-only argument that indicates whether this struct
      creates a nested context. The default is True. This parameter is
      considered "advanced usage", and may be removed in the future.

    Example:
    Struct("foo",
        UBInt8("first_element"),
        UBInt16("second_element"),
        Padding(2),
        UBInt8("third_element"),
    )
    """
    __slots__ = ["subcons", "nested"]
    def __init__(self, name, *subcons, **kw):
        self.nested = kw.pop("nested", True)
        if kw:
            raise TypeError("the only keyword argument accepted is 'nested'", kw)
        Construct.__init__(self, name)
        self.subcons = subcons
        self._inherit_flags(*subcons)
        self._clear_flag(self.FLAG_EMBED)
    def _parse(self, stream, context):
        if "<obj>" in context:
            obj = context["<obj>"]
            del context["<obj>"]
        else:
            obj = Container()
            if self.nested:
                context = Container(_ = context)
        for sc in self.subcons:
            if sc.conflags & self.FLAG_EMBED:
                context["<obj>"] = obj
                sc._parse(stream, context)
            else:
                subobj = sc._parse(stream, context)
                if sc.name is not None:
                    obj[sc.name] = subobj
                    context[sc.name] = subobj
        return obj
    def _build(self, obj, stream, context):
        if "<unnested>" in context:
            del context["<unnested>"]
        elif self.nested:
            context = Container(_ = context)
        for sc in self.subcons:
            if sc.conflags & self.FLAG_EMBED:
                context["<unnested>"] = True
                subobj = obj
            elif sc.name is None:
                subobj = None
            else:
                subobj = getattr(obj, sc.name)
                context[sc.name] = subobj
            sc._build(subobj, stream, context)
    def _sizeof(self, context):
        if self.nested:
            context = Container(_ = context)
        return sum(sc._sizeof(context) for sc in self.subcons)

class Sequence(Struct):
    """
    A sequence of unnamed constructs. The elements are parsed and built in the
    order they are defined.
    See also Embedded.

    Parameters:
    * name - the name of the structure
    * subcons - a sequence of subconstructs that make up this structure.
    * nested - a keyword-only argument that indicates whether this struct
      creates a nested context. The default is True. This parameter is
      considered "advanced usage", and may be removed in the future.

    Example:
    Sequence("foo",
        UBInt8("first_element"),
        UBInt16("second_element"),
        Padding(2),
        UBInt8("third_element"),
    )
    """
    __slots__ = []
    def _parse(self, stream, context):
        if "<obj>" in context:
            obj = context["<obj>"]
            del context["<obj>"]
        else:
            obj = ListContainer()
            if self.nested:
                context = Container(_ = context)
        for sc in self.subcons:
            if sc.conflags & self.FLAG_EMBED:
                context["<obj>"] = obj
                sc._parse(stream, context)
            else:
                subobj = sc._parse(stream, context)
                if sc.name is not None:
                    obj.append(subobj)
                    context[sc.name] = subobj
        return obj
    def _build(self, obj, stream, context):
        if "<unnested>" in context:
            del context["<unnested>"]
        elif self.nested:
            context = Container(_ = context)
        objiter = iter(obj)
        for sc in self.subcons:
            if sc.conflags & self.FLAG_EMBED:
                context["<unnested>"] = True
                subobj = objiter
            elif sc.name is None:
                subobj = None
            else:
                subobj = advance_iterator(objiter)
                context[sc.name] = subobj
            sc._build(subobj, stream, context)

class Union(Construct):
    """
    a set of overlapping fields (like unions in C). when parsing,
    all fields read the same data; when building, only the first subcon
    (called "master") is used.

    Parameters:
    * name - the name of the union
    * master - the master subcon, i.e., the subcon used for building and
      calculating the total size
    * subcons - additional subcons

    Example:
    Union("what_are_four_bytes",
        UBInt32("one_dword"),
        Struct("two_words", UBInt16("first"), UBInt16("second")),
        Struct("four_bytes",
            UBInt8("a"),
            UBInt8("b"),
            UBInt8("c"),
            UBInt8("d")
        ),
    )
    """
    __slots__ = ["parser", "builder"]
    def __init__(self, name, master, *subcons, **kw):
        Construct.__init__(self, name)
        args = [Peek(sc) for sc in subcons]
        args.append(MetaField(None, lambda ctx: master._sizeof(ctx)))
        self.parser = Struct(name, Peek(master, perform_build = True), *args)
        self.builder = Struct(name, master)
    def _parse(self, stream, context):
        return self.parser._parse(stream, context)
    def _build(self, obj, stream, context):
        return self.builder._build(obj, stream, context)
    def _sizeof(self, context):
        return self.builder._sizeof(context)

#===============================================================================
# conditional
#===============================================================================
class Switch(Construct):
    """
    A conditional branch. Switch will choose the case to follow based on
    the return value of keyfunc. If no case is matched, and no default value
    is given, SwitchError will be raised.
    See also Pass.

    Parameters:
    * name - the name of the construct
    * keyfunc - a function that takes the context and returns a key, which
      will ne used to choose the relevant case.
    * cases - a dictionary mapping keys to constructs. the keys can be any
      values that may be returned by keyfunc.
    * default - a default value to use when the key is not found in the cases.
      if not supplied, an exception will be raised when the key is not found.
      You can use the builtin construct Pass for 'do-nothing'.
    * include_key - whether or not to include the key in the return value
      of parsing. defualt is False.

    Example:
    Struct("foo",
        UBInt8("type"),
        Switch("value", lambda ctx: ctx.type, {
                1 : UBInt8("spam"),
                2 : UBInt16("spam"),
                3 : UBInt32("spam"),
                4 : UBInt64("spam"),
            }
        ),
    )
    """

    class NoDefault(Construct):
        def _parse(self, stream, context):
            raise SwitchError("no default case defined")
        def _build(self, obj, stream, context):
            raise SwitchError("no default case defined")
        def _sizeof(self, context):
            raise SwitchError("no default case defined")
    NoDefault = NoDefault("No default value specified")

    __slots__ = ["subcons", "keyfunc", "cases", "default", "include_key"]

    def __init__(self, name, keyfunc, cases, default = NoDefault,
                 include_key = False):
        Construct.__init__(self, name)
        self._inherit_flags(*cases.values())
        self.keyfunc = keyfunc
        self.cases = cases
        self.default = default
        self.include_key = include_key
        self._inherit_flags(*cases.values())
        self._set_flag(self.FLAG_DYNAMIC)
    def _parse(self, stream, context):
        key = self.keyfunc(context)
        obj = self.cases.get(key, self.default)._parse(stream, context)
        if self.include_key:
            return key, obj
        else:
            return obj
    def _build(self, obj, stream, context):
        if self.include_key:
            key, obj = obj
        else:
            key = self.keyfunc(context)
        case = self.cases.get(key, self.default)
        case._build(obj, stream, context)
    def _sizeof(self, context):
        case = self.cases.get(self.keyfunc(context), self.default)
        return case._sizeof(context)

class Select(Construct):
    """
    Selects the first matching subconstruct. It will literally try each of
    the subconstructs, until one matches.

    Notes:
    * requires a seekable stream.

    Parameters:
    * name - the name of the construct
    * subcons - the subcons to try (order-sensitive)
    * include_name - a keyword only argument, indicating whether to include
      the name of the selected subcon in the return value of parsing. default
      is false.

    Example:
    Select("foo",
        UBInt64("large"),
        UBInt32("medium"),
        UBInt16("small"),
        UBInt8("tiny"),
    )
    """
    __slots__ = ["subcons", "include_name"]
    def __init__(self, name, *subcons, **kw):
        include_name = kw.pop("include_name", False)
        if kw:
            raise TypeError("the only keyword argument accepted "
                "is 'include_name'", kw)
        Construct.__init__(self, name)
        self.subcons = subcons
        self.include_name = include_name
        self._inherit_flags(*subcons)
        self._set_flag(self.FLAG_DYNAMIC)
    def _parse(self, stream, context):
        for sc in self.subcons:
            pos = stream.tell()
            context2 = context.__copy__()
            try:
                obj = sc._parse(stream, context2)
            except ConstructError:
                stream.seek(pos)
            else:
                context.__update__(context2)
                if self.include_name:
                    return sc.name, obj
                else:
                    return obj
        raise SelectError("no subconstruct matched")
    def _build(self, obj, stream, context):
        if self.include_name:
            name, obj = obj
            for sc in self.subcons:
                if sc.name == name:
                    sc._build(obj, stream, context)
                    return
        else:
            for sc in self.subcons:
                stream2 = BytesIO()
                context2 = context.__copy__()
                try:
                    sc._build(obj, stream2, context2)
                except Exception:
                    pass
                else:
                    context.__update__(context2)
                    stream.write(stream2.getvalue())
                    return
        raise SelectError("no subconstruct matched", obj)
    def _sizeof(self, context):
        raise SizeofError("can't calculate size")


#===============================================================================
# stream manipulation
#===============================================================================
class Pointer(Subconstruct):
    """
    Changes the stream position to a given offset, where the construction
    should take place, and restores the stream position when finished.
    See also Anchor, OnDemand and OnDemandPointer.

    Notes:
    * requires a seekable stream.

    Parameters:
    * offsetfunc: a function that takes the context and returns an absolute
      stream position, where the construction would take place
    * subcon - the subcon to use at `offsetfunc()`

    Example:
    Struct("foo",
        UBInt32("spam_pointer"),
        Pointer(lambda ctx: ctx.spam_pointer,
            Array(5, UBInt8("spam"))
        )
    )
    """
    __slots__ = ["offsetfunc"]
    def __init__(self, offsetfunc, subcon):
        Subconstruct.__init__(self, subcon)
        self.offsetfunc = offsetfunc
    def _parse(self, stream, context):
        newpos = self.offsetfunc(context)
        origpos = stream.tell()
        stream.seek(newpos)
        obj = self.subcon._parse(stream, context)
        stream.seek(origpos)
        return obj
    def _build(self, obj, stream, context):
        newpos = self.offsetfunc(context)
        origpos = stream.tell()
        stream.seek(newpos)
        self.subcon._build(obj, stream, context)
        stream.seek(origpos)
    def _sizeof(self, context):
        return 0

class Peek(Subconstruct):
    """
    Peeks at the stream: parses without changing the stream position.
    See also Union. If the end of the stream is reached when peeking,
    returns None.

    Notes:
    * requires a seekable stream.

    Parameters:
    * subcon - the subcon to peek at
    * perform_build - whether or not to perform building. by default this
      parameter is set to False, meaning building is a no-op.

    Example:
    Peek(UBInt8("foo"))
    """
    __slots__ = ["perform_build"]
    def __init__(self, subcon, perform_build = False):
        Subconstruct.__init__(self, subcon)
        self.perform_build = perform_build
    def _parse(self, stream, context):
        pos = stream.tell()
        try:
            return self.subcon._parse(stream, context)
        except FieldError:
            pass
        finally:
            stream.seek(pos)
    def _build(self, obj, stream, context):
        if self.perform_build:
            self.subcon._build(obj, stream, context)
    def _sizeof(self, context):
        return 0

class OnDemand(Subconstruct):
    """
    Allows for on-demand (lazy) parsing. When parsing, it will return a
    LazyContainer that represents a pointer to the data, but does not actually
    parses it from stream until it's "demanded".
    By accessing the 'value' property of LazyContainers, you will demand the
    data from the stream. The data will be parsed and cached for later use.
    You can use the 'has_value' property to know whether the data has already
    been demanded.
    See also OnDemandPointer.

    Notes:
    * requires a seekable stream.

    Parameters:
    * subcon -
    * advance_stream - whether or not to advance the stream position. by
      default this is True, but if subcon is a pointer, this should be False.
    * force_build - whether or not to force build. If set to False, and the
      LazyContainer has not been demaned, building is a no-op.

    Example:
    OnDemand(Array(10000, UBInt8("foo"))
    """
    __slots__ = ["advance_stream", "force_build"]
    def __init__(self, subcon, advance_stream = True, force_build = True):
        Subconstruct.__init__(self, subcon)
        self.advance_stream = advance_stream
        self.force_build = force_build
    def _parse(self, stream, context):
        obj = LazyContainer(self.subcon, stream, stream.tell(), context)
        if self.advance_stream:
            stream.seek(self.subcon._sizeof(context), 1)
        return obj
    def _build(self, obj, stream, context):
        if not isinstance(obj, LazyContainer):
            self.subcon._build(obj, stream, context)
        elif self.force_build or obj.has_value:
            self.subcon._build(obj.value, stream, context)
        elif self.advance_stream:
            stream.seek(self.subcon._sizeof(context), 1)

class Buffered(Subconstruct):
    """
    Creates an in-memory buffered stream, which can undergo encoding and
    decoding prior to being passed on to the subconstruct.
    See also Bitwise.

    Note:
    * Do not use pointers inside Buffered

    Parameters:
    * subcon - the subcon which will operate on the buffer
    * encoder - a function that takes a string and returns an encoded
      string (used after building)
    * decoder - a function that takes a string and returns a decoded
      string (used before parsing)
    * resizer - a function that takes the size of the subcon and "adjusts"
      or "resizes" it according to the encoding/decoding process.

    Example:
    Buffered(BitField("foo", 16),
        encoder = decode_bin,
        decoder = encode_bin,
        resizer = lambda size: size / 8,
    )
    """
    __slots__ = ["encoder", "decoder", "resizer"]
    def __init__(self, subcon, decoder, encoder, resizer):
        Subconstruct.__init__(self, subcon)
        self.encoder = encoder
        self.decoder = decoder
        self.resizer = resizer
    def _parse(self, stream, context):
        data = _read_stream(stream, self._sizeof(context))
        stream2 = BytesIO(self.decoder(data))
        return self.subcon._parse(stream2, context)
    def _build(self, obj, stream, context):
        size = self._sizeof(context)
        stream2 = BytesIO()
        self.subcon._build(obj, stream2, context)
        data = self.encoder(stream2.getvalue())
        assert len(data) == size
        _write_stream(stream, self._sizeof(context), data)
    def _sizeof(self, context):
        return self.resizer(self.subcon._sizeof(context))

class Restream(Subconstruct):
    """
    Wraps the stream with a read-wrapper (for parsing) or a
    write-wrapper (for building). The stream wrapper can buffer the data
    internally, reading it from- or writing it to the underlying stream
    as needed. For example, BitStreamReader reads whole bytes from the
    underlying stream, but returns them as individual bits.
    See also Bitwise.

    When the parsing or building is done, the stream's close method
    will be invoked. It can perform any finalization needed for the stream
    wrapper, but it must not close the underlying stream.

    Note:
    * Do not use pointers inside Restream

    Parameters:
    * subcon - the subcon
    * stream_reader - the read-wrapper
    * stream_writer - the write wrapper
    * resizer - a function that takes the size of the subcon and "adjusts"
      or "resizes" it according to the encoding/decoding process.

    Example:
    Restream(BitField("foo", 16),
        stream_reader = BitStreamReader,
        stream_writer = BitStreamWriter,
        resizer = lambda size: size / 8,
    )
    """
    __slots__ = ["stream_reader", "stream_writer", "resizer"]
    def __init__(self, subcon, stream_reader, stream_writer, resizer):
        Subconstruct.__init__(self, subcon)
        self.stream_reader = stream_reader
        self.stream_writer = stream_writer
        self.resizer = resizer
    def _parse(self, stream, context):
        stream2 = self.stream_reader(stream)
        obj = self.subcon._parse(stream2, context)
        stream2.close()
        return obj
    def _build(self, obj, stream, context):
        stream2 = self.stream_writer(stream)
        self.subcon._build(obj, stream2, context)
        stream2.close()
    def _sizeof(self, context):
        return self.resizer(self.subcon._sizeof(context))


#===============================================================================
# miscellaneous
#===============================================================================
class Reconfig(Subconstruct):
    """
    Reconfigures a subconstruct. Reconfig can be used to change the name and
    set and clear flags of the inner subcon.

    Parameters:
    * name - the new name
    * subcon - the subcon to reconfigure
    * setflags - the flags to set (default is 0)
    * clearflags - the flags to clear (default is 0)

    Example:
    Reconfig("foo", UBInt8("bar"))
    """
    __slots__ = []
    def __init__(self, name, subcon, setflags = 0, clearflags = 0):
        Construct.__init__(self, name, subcon.conflags)
        self.subcon = subcon
        self._set_flag(setflags)
        self._clear_flag(clearflags)

class Anchor(Construct):
    """
    Returns the "anchor" (stream position) at the point where it's inserted.
    Useful for adjusting relative offsets to absolute positions, or to measure
    sizes of constructs.
    absolute pointer = anchor + relative offset
    size = anchor_after - anchor_before
    See also Pointer.

    Notes:
    * requires a seekable stream.

    Parameters:
    * name - the name of the anchor

    Example:
    Struct("foo",
        Anchor("base"),
        UBInt8("relative_offset"),
        Pointer(lambda ctx: ctx.relative_offset + ctx.base,
            UBInt8("data")
        )
    )
    """
    __slots__ = []
    def _parse(self, stream, context):
        return stream.tell()
    def _build(self, obj, stream, context):
        context[self.name] = stream.tell()
    def _sizeof(self, context):
        return 0

class Value(Construct):
    """
    A computed value.

    Parameters:
    * name - the name of the value
    * func - a function that takes the context and return the computed value

    Example:
    Struct("foo",
        UBInt8("width"),
        UBInt8("height"),
        Value("total_pixels", lambda ctx: ctx.width * ctx.height),
    )
    """
    __slots__ = ["func"]
    def __init__(self, name, func):
        Construct.__init__(self, name)
        self.func = func
        self._set_flag(self.FLAG_DYNAMIC)
    def _parse(self, stream, context):
        return self.func(context)
    def _build(self, obj, stream, context):
        context[self.name] = self.func(context)
    def _sizeof(self, context):
        return 0

#class Dynamic(Construct):
#    """
#    Dynamically creates a construct and uses it for parsing and building.
#    This allows you to create change the construction tree on the fly.
#    Deprecated.
#
#    Parameters:
#    * name - the name of the construct
#    * factoryfunc - a function that takes the context and returns a new
#      construct object which will be used for parsing and building.
#
#    Example:
#    def factory(ctx):
#        if ctx.bar == 8:
#            return UBInt8("spam")
#        if ctx.bar == 9:
#            return String("spam", 9)
#
#    Struct("foo",
#        UBInt8("bar"),
#        Dynamic("spam", factory),
#    )
#    """
#    __slots__ = ["factoryfunc"]
#    def __init__(self, name, factoryfunc):
#        Construct.__init__(self, name, self.FLAG_COPY_CONTEXT)
#        self.factoryfunc = factoryfunc
#        self._set_flag(self.FLAG_DYNAMIC)
#    def _parse(self, stream, context):
#        return self.factoryfunc(context)._parse(stream, context)
#    def _build(self, obj, stream, context):
#        return self.factoryfunc(context)._build(obj, stream, context)
#    def _sizeof(self, context):
#        return self.factoryfunc(context)._sizeof(context)

class LazyBound(Construct):
    """
    Lazily bound construct, useful for constructs that need to make cyclic
    references (linked-lists, expression trees, etc.).

    Parameters:


    Example:
    foo = Struct("foo",
        UBInt8("bar"),
        LazyBound("next", lambda: foo),
    )
    """
    __slots__ = ["bindfunc", "bound"]
    def __init__(self, name, bindfunc):
        Construct.__init__(self, name)
        self.bound = None
        self.bindfunc = bindfunc
    def _parse(self, stream, context):
        if self.bound is None:
            self.bound = self.bindfunc()
        return self.bound._parse(stream, context)
    def _build(self, obj, stream, context):
        if self.bound is None:
            self.bound = self.bindfunc()
        self.bound._build(obj, stream, context)
    def _sizeof(self, context):
        if self.bound is None:
            self.bound = self.bindfunc()
        return self.bound._sizeof(context)

class Pass(Construct):
    """
    A do-nothing construct, useful as the default case for Switch, or
    to indicate Enums.
    See also Switch and Enum.

    Notes:
    * this construct is a singleton. do not try to instatiate it, as it
      will not work...

    Example:
    Pass
    """
    __slots__ = []
    def _parse(self, stream, context):
        pass
    def _build(self, obj, stream, context):
        assert obj is None
    def _sizeof(self, context):
        return 0
Pass = Pass(None)

class Terminator(Construct):
    """
    Asserts the end of the stream has been reached at the point it's placed.
    You can use this to ensure no more unparsed data follows.

    Notes:
    * this construct is only meaningful for parsing. for building, it's
      a no-op.
    * this construct is a singleton. do not try to instatiate it, as it
      will not work...

    Example:
    Terminator
    """
    __slots__ = []
    def _parse(self, stream, context):
        if stream.read(1):
            raise TerminatorError("expected end of stream")
    def _build(self, obj, stream, context):
        assert obj is None
    def _sizeof(self, context):
        return 0
Terminator = Terminator(None)

########NEW FILE########
__FILENAME__ = debug
"""
Debugging utilities for constructs
"""
from __future__ import print_function
import sys
import traceback
import pdb
import inspect
from .core import Construct, Subconstruct
from .lib import HexString, Container, ListContainer


class Probe(Construct):
    """
    A probe: dumps the context, stack frames, and stream content to the screen
    to aid the debugging process.
    See also Debugger.
    
    Parameters:
    * name - the display name
    * show_stream - whether or not to show stream contents. default is True. 
      the stream must be seekable.
    * show_context - whether or not to show the context. default is True.
    * show_stack - whether or not to show the upper stack frames. default 
      is True.
    * stream_lookahead - the number of bytes to dump when show_stack is set.
      default is 100.
    
    Example:
    Struct("foo",
        UBInt8("a"),
        Probe("between a and b"),
        UBInt8("b"),
    )
    """
    __slots__ = [
        "printname", "show_stream", "show_context", "show_stack", 
        "stream_lookahead"
    ]
    counter = 0
    
    def __init__(self, name = None, show_stream = True, 
                 show_context = True, show_stack = True, 
                 stream_lookahead = 100):
        Construct.__init__(self, None)
        if name is None:
            Probe.counter += 1
            name = "<unnamed %d>" % (Probe.counter,)
        self.printname = name
        self.show_stream = show_stream
        self.show_context = show_context
        self.show_stack = show_stack
        self.stream_lookahead = stream_lookahead
    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, self.printname)
    def _parse(self, stream, context):
        self.printout(stream, context)
    def _build(self, obj, stream, context):
        self.printout(stream, context)
    def _sizeof(self, context):
        return 0
    
    def printout(self, stream, context):
        obj = Container()
        if self.show_stream:
            obj.stream_position = stream.tell()
            follows = stream.read(self.stream_lookahead)
            if not follows:
                obj.following_stream_data = "EOF reached"
            else:
                stream.seek(-len(follows), 1)
                obj.following_stream_data = HexString(follows)
            print
        
        if self.show_context:
            obj.context = context
        
        if self.show_stack:
            obj.stack = ListContainer()
            frames = [s[0] for s in inspect.stack()][1:-1]
            frames.reverse()
            for f in frames:
                a = Container()
                a.__update__(f.f_locals)
                obj.stack.append(a)
        
        print("=" * 80)
        print("Probe", self.printname)
        print(obj)
        print("=" * 80)

class Debugger(Subconstruct):
    """
    A pdb-based debugger. When an exception occurs in the subcon, a debugger
    will appear and allow you to debug the error (and even fix on-the-fly).
    
    Parameters:
    * subcon - the subcon to debug
    
    Example:
    Debugger(
        Enum(UBInt8("foo"),
            a = 1,
            b = 2,
            c = 3
        )
    )
    """
    __slots__ = ["retval"]
    def _parse(self, stream, context):
        try:
            return self.subcon._parse(stream, context)
        except Exception:
            self.retval = NotImplemented
            self.handle_exc("(you can set the value of 'self.retval', "
                "which will be returned)")
            if self.retval is NotImplemented:
                raise
            else:
                return self.retval
    def _build(self, obj, stream, context):
        try:
            self.subcon._build(obj, stream, context)
        except Exception:
            self.handle_exc()
    def handle_exc(self, msg = None):
        print("=" * 80)
        print("Debugging exception of %s:" % (self.subcon,))
        print("".join(traceback.format_exception(*sys.exc_info())[1:]))
        if msg:
            print(msg)
        pdb.post_mortem(sys.exc_info()[2])
        print("=" * 80)


########NEW FILE########
__FILENAME__ = binary
from .py3compat import int2byte


def int_to_bin(number, width=32):
    r"""
    Convert an integer into its binary representation in a bytes object.
    Width is the amount of bits to generate. If width is larger than the actual
    amount of bits required to represent number in binary, sign-extension is
    used. If it's smaller, the representation is trimmed to width bits.
    Each "bit" is either '\x00' or '\x01'. The MSBit is first.

    Examples:

        >>> int_to_bin(19, 5)
        b'\x01\x00\x00\x01\x01'
        >>> int_to_bin(19, 8)
        b'\x00\x00\x00\x01\x00\x00\x01\x01'
    """
    if number < 0:
        number += 1 << width
    i = width - 1
    bits = bytearray(width)
    while number and i >= 0:
        bits[i] = number & 1
        number >>= 1
        i -= 1
    return bytes(bits)


_bit_values = {
    0: 0, 
    1: 1, 
    48: 0, # '0'
    49: 1, # '1'

    # The following are for Python 2, in which iteration over a bytes object
    # yields single-character bytes and not integers.
    '\x00': 0,
    '\x01': 1,
    '0': 0,
    '1': 1,
    }

def bin_to_int(bits, signed=False):
    r"""
    Logical opposite of int_to_bin. Both '0' and '\x00' are considered zero,
    and both '1' and '\x01' are considered one. Set sign to True to interpret
    the number as a 2-s complement signed integer.
    """
    number = 0
    bias = 0
    ptr = 0
    if signed and _bit_values[bits[0]] == 1:
        bits = bits[1:]
        bias = 1 << len(bits)
    for b in bits:
        number <<= 1
        number |= _bit_values[b]
    return number - bias


def swap_bytes(bits, bytesize=8):
    r"""
    Bits is a b'' object containing a binary representation. Assuming each
    bytesize bits constitute a bytes, perform a endianness byte swap. Example:

        >>> swap_bytes(b'00011011', 2)
        b'11100100'
    """
    i = 0
    l = len(bits)
    output = [b""] * ((l // bytesize) + 1)
    j = len(output) - 1
    while i < l:
        output[j] = bits[i : i + bytesize]
        i += bytesize
        j -= 1
    return b"".join(output)


_char_to_bin = {}
_bin_to_char = {}
for i in range(256):
    ch = int2byte(i)
    bin = int_to_bin(i, 8)
    # Populate with for both keys i and ch, to support Python 2 & 3
    _char_to_bin[ch] = bin
    _char_to_bin[i] = bin
    _bin_to_char[bin] = ch


def encode_bin(data):
    """ 
    Create a binary representation of the given b'' object. Assume 8-bit
    ASCII. Example:

        >>> encode_bin('ab')
        b"\x00\x01\x01\x00\x00\x00\x00\x01\x00\x01\x01\x00\x00\x00\x01\x00"
    """
    return b"".join(_char_to_bin[ch] for ch in data)


def decode_bin(data):
    """ 
    Locical opposite of decode_bin.
    """
    if len(data) & 7:
        raise ValueError("Data length must be a multiple of 8")
    i = 0
    j = 0
    l = len(data) // 8
    chars = [b""] * l
    while j < l:
        chars[j] = _bin_to_char[data[i:i+8]]
        i += 8
        j += 1
    return b"".join(chars)


########NEW FILE########
__FILENAME__ = bitstream
from .binary import encode_bin, decode_bin

class BitStreamReader(object):

    __slots__ = ["substream", "buffer", "total_size"]

    def __init__(self, substream):
        self.substream = substream
        self.total_size = 0
        self.buffer = ""

    def close(self):
        if self.total_size % 8 != 0:
            raise ValueError("total size of read data must be a multiple of 8",
                self.total_size)

    def tell(self):
        return self.substream.tell()

    def seek(self, pos, whence = 0):
        self.buffer = ""
        self.total_size = 0
        self.substream.seek(pos, whence)

    def read(self, count):
        if count < 0:
            raise ValueError("count cannot be negative")

        l = len(self.buffer)
        if count == 0:
            data = ""
        elif count <= l:
            data = self.buffer[:count]
            self.buffer = self.buffer[count:]
        else:
            data = self.buffer
            count -= l
            bytes = count // 8
            if count & 7:
                bytes += 1
            buf = encode_bin(self.substream.read(bytes))
            data += buf[:count]
            self.buffer = buf[count:]
        self.total_size += len(data)
        return data

class BitStreamWriter(object):

    __slots__ = ["substream", "buffer", "pos"]

    def __init__(self, substream):
        self.substream = substream
        self.buffer = []
        self.pos = 0

    def close(self):
        self.flush()

    def flush(self):
        bytes = decode_bin("".join(self.buffer))
        self.substream.write(bytes)
        self.buffer = []
        self.pos = 0

    def tell(self):
        return self.substream.tell() + self.pos // 8

    def seek(self, pos, whence = 0):
        self.flush()
        self.substream.seek(pos, whence)

    def write(self, data):
        if not data:
            return
        if type(data) is not str:
            raise TypeError("data must be a string, not %r" % (type(data),))
        self.buffer.append(data)

########NEW FILE########
__FILENAME__ = container
"""
Various containers.
"""

from collections import MutableMapping
from pprint import pformat

def recursion_lock(retval, lock_name = "__recursion_lock__"):
    def decorator(func):
        def wrapper(self, *args, **kw):
            if getattr(self, lock_name, False):
                return retval
            setattr(self, lock_name, True)
            try:
                return func(self, *args, **kw)
            finally:
                setattr(self, lock_name, False)
        wrapper.__name__ = func.__name__
        return wrapper
    return decorator

class Container(MutableMapping):
    """
    A generic container of attributes.

    Containers are the common way to express parsed data.
    """

    def __init__(self, **kw):
        self.__dict__ = kw

    # The core dictionary interface.

    def __getitem__(self, name):
        return self.__dict__[name]

    def __delitem__(self, name):
        del self.__dict__[name]

    def __setitem__(self, name, value):
        self.__dict__[name] = value

    def keys(self):
        return self.__dict__.keys()

    def __len__(self):
        return len(self.__dict__.keys())

    # Extended dictionary interface.

    def update(self, other):
        self.__dict__.update(other)

    __update__ = update

    def __contains__(self, value):
        return value in self.__dict__

    # Rich comparisons.

    def __eq__(self, other):
        try:
            return self.__dict__ == other.__dict__
        except AttributeError:
            return False

    def __ne__(self, other):
        return not self == other

    # Copy interface.

    def copy(self):
        return self.__class__(**self.__dict__)

    __copy__ = copy

    # Iterator interface.

    def __iter__(self):
        return iter(self.__dict__)

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, repr(self.__dict__))

    def __str__(self):
        return "%s(%s)" % (self.__class__.__name__, str(self.__dict__))

class FlagsContainer(Container):
    """
    A container providing pretty-printing for flags.

    Only set flags are displayed.
    """

    @recursion_lock("<...>")
    def __str__(self):
        d = dict((k, self[k]) for k in self
                 if self[k] and not k.startswith("_"))
        return "%s(%s)" % (self.__class__.__name__, pformat(d))

class ListContainer(list):
    """
    A container for lists.
    """

    __slots__ = ["__recursion_lock__"]

    @recursion_lock("[...]")
    def __str__(self):
        return pformat(self)

class LazyContainer(object):

    __slots__ = ["subcon", "stream", "pos", "context", "_value"]

    def __init__(self, subcon, stream, pos, context):
        self.subcon = subcon
        self.stream = stream
        self.pos = pos
        self.context = context
        self._value = NotImplemented

    def __eq__(self, other):
        try:
            return self._value == other._value
        except AttributeError:
            return False

    def __ne__(self, other):
        return not (self == other)

    def __str__(self):
        return self.__pretty_str__()

    def __pretty_str__(self, nesting = 1, indentation = "    "):
        if self._value is NotImplemented:
            text = "<unread>"
        elif hasattr(self._value, "__pretty_str__"):
            text = self._value.__pretty_str__(nesting, indentation)
        else:
            text = str(self._value)
        return "%s: %s" % (self.__class__.__name__, text)

    def read(self):
        self.stream.seek(self.pos)
        return self.subcon._parse(self.stream, self.context)

    def dispose(self):
        self.subcon = None
        self.stream = None
        self.context = None
        self.pos = None

    def _get_value(self):
        if self._value is NotImplemented:
            self._value = self.read()
        return self._value

    value = property(_get_value)

    has_value = property(lambda self: self._value is not NotImplemented)

########NEW FILE########
__FILENAME__ = hex
from .py3compat import byte2int, int2byte, bytes2str


# Map an integer in the inclusive range 0-255 to its string byte representation
_printable = dict((i, ".") for i in range(256))
_printable.update((i, bytes2str(int2byte(i))) for i in range(32, 128))


def hexdump(data, linesize):
    """
    data is a bytes object. The returned result is a string.
    """
    prettylines = []
    if len(data) < 65536:
        fmt = "%%04X   %%-%ds   %%s"
    else:
        fmt = "%%08X   %%-%ds   %%s"
    fmt = fmt % (3 * linesize - 1,)
    for i in range(0, len(data), linesize):
        line = data[i : i + linesize]
        hextext = " ".join('%02x' % byte2int(b) for b in line)
        rawtext = "".join(_printable[byte2int(b)] for b in line)
        prettylines.append(fmt % (i, str(hextext), str(rawtext)))
    return prettylines


class HexString(bytes):
    """
    Represents bytes that will be hex-dumped to a string when its string
    representation is requested.
    """
    def __init__(self, data, linesize = 16):
        self.linesize = linesize

    def __new__(cls, data, *args, **kwargs):
        return bytes.__new__(cls, data)
        
    def __str__(self):
        if not self:
            return "''"
        sep = "\n"
        return sep + sep.join(
            hexdump(self, self.linesize))


########NEW FILE########
__FILENAME__ = py3compat
#-------------------------------------------------------------------------------
# py3compat.py
#
# Some Python2&3 compatibility code
#-------------------------------------------------------------------------------
import sys
PY3 = sys.version_info[0] == 3


if PY3:
    import io
    StringIO = io.StringIO
    BytesIO = io.BytesIO

    def bchr(i):
        """ When iterating over b'...' in Python 2 you get single b'_' chars
            and in Python 3 you get integers. Call bchr to always turn this
            to single b'_' chars.
        """
        return bytes((i,))

    def u(s):
        return s

    def int2byte(i):
        return bytes((i,))

    def byte2int(b):
        return b

    def str2bytes(s):
        return s.encode("latin-1")

    def str2unicode(s):
        return s

    def bytes2str(b):
        return b.decode('latin-1')

    def decodebytes(b, encoding):
        return bytes(b, encoding)

    advance_iterator = next
        
else:
    import cStringIO
    StringIO = BytesIO = cStringIO.StringIO

    int2byte = chr
    byte2int = ord
    bchr = lambda i: i

    def u(s):
        return unicode(s, "unicode_escape")

    def str2bytes(s):
        return s

    def str2unicode(s):
        return unicode(s, "unicode_escape")

    def bytes2str(b):
        return b

    def decodebytes(b, encoding):
        return b.decode(encoding)

    def advance_iterator(it):
        return it.next()


########NEW FILE########
__FILENAME__ = macros
from .lib.py3compat import int2byte
from .lib import (BitStreamReader, BitStreamWriter, encode_bin,
    decode_bin)
from .core import (Struct, MetaField, StaticField, FormatField,
    OnDemand, Pointer, Switch, Value, RepeatUntil, MetaArray, Sequence, Range,
    Select, Pass, SizeofError, Buffered, Restream, Reconfig)
from .adapters import (BitIntegerAdapter, PaddingAdapter,
    ConstAdapter, CStringAdapter, LengthValueAdapter, IndexingAdapter,
    PaddedStringAdapter, FlagsAdapter, StringAdapter, MappingAdapter)


#===============================================================================
# fields
#===============================================================================
def Field(name, length):
    """
    A field consisting of a specified number of bytes.

    :param str name: the name of the field
    :param length: the length of the field. the length can be either an integer
      (StaticField), or a function that takes the context as an argument and
      returns the length (MetaField)
    """
    if callable(length):
        return MetaField(name, length)
    else:
        return StaticField(name, length)

def BitField(name, length, swapped = False, signed = False, bytesize = 8):
    """
    BitFields, as the name suggests, are fields that operate on raw, unaligned
    bits, and therefore must be enclosed in a BitStruct. Using them is very
    similar to all normal fields: they take a name and a length (in bits).

    :param str name: name of the field
    :param int length: number of bits in the field, or a function that takes
                       the context as its argument and returns the length
    :param bool swapped: whether the value is byte-swapped
    :param bool signed: whether the value is signed
    :param int bytesize: number of bits per byte, for byte-swapping

    >>> foo = BitStruct("foo",
    ...     BitField("a", 3),
    ...     Flag("b"),
    ...     Padding(3),
    ...     Nibble("c"),
    ...     BitField("d", 5),
    ... )
    >>> foo.parse("\\xe1\\x1f")
    Container(a = 7, b = False, c = 8, d = 31)
    >>> foo = BitStruct("foo",
    ...     BitField("a", 3),
    ...     Flag("b"),
    ...     Padding(3),
    ...     Nibble("c"),
    ...     Struct("bar",
    ...             Nibble("d"),
    ...             Bit("e"),
    ...     )
    ... )
    >>> foo.parse("\\xe1\\x1f")
    Container(a = 7, b = False, bar = Container(d = 15, e = 1), c = 8)
    """

    return BitIntegerAdapter(Field(name, length),
        length,
        swapped=swapped,
        signed=signed,
        bytesize=bytesize
    )

def Padding(length, pattern = "\x00", strict = False):
    r"""a padding field (value is discarded)
    * length - the length of the field. the length can be either an integer,
      or a function that takes the context as an argument and returns the
      length
    * pattern - the padding pattern (character) to use. default is "\x00"
    * strict - whether or not to raise an exception is the actual padding
      pattern mismatches the desired pattern. default is False.
    """
    return PaddingAdapter(Field(None, length),
        pattern = pattern,
        strict = strict,
    )

def Flag(name, truth = 1, falsehood = 0, default = False):
    """
    A flag.

    Flags are usually used to signify a Boolean value, and this construct
    maps values onto the ``bool`` type.

    .. note:: This construct works with both bit and byte contexts.

    .. warning:: Flags default to False, not True. This is different from the
        C and Python way of thinking about truth, and may be subject to change
        in the future.

    :param str name: field name
    :param int truth: value of truth (default 1)
    :param int falsehood: value of falsehood (default 0)
    :param bool default: default value (default False)
    """

    return SymmetricMapping(Field(name, 1),
        {True : int2byte(truth), False : int2byte(falsehood)},
        default = default,
    )

#===============================================================================
# field shortcuts
#===============================================================================
def Bit(name):
    """a 1-bit BitField; must be enclosed in a BitStruct"""
    return BitField(name, 1)
def Nibble(name):
    """a 4-bit BitField; must be enclosed in a BitStruct"""
    return BitField(name, 4)
def Octet(name):
    """an 8-bit BitField; must be enclosed in a BitStruct"""
    return BitField(name, 8)

def UBInt8(name):
    """unsigned, big endian 8-bit integer"""
    return FormatField(name, ">", "B")
def UBInt16(name):
    """unsigned, big endian 16-bit integer"""
    return FormatField(name, ">", "H")
def UBInt32(name):
    """unsigned, big endian 32-bit integer"""
    return FormatField(name, ">", "L")
def UBInt64(name):
    """unsigned, big endian 64-bit integer"""
    return FormatField(name, ">", "Q")

def SBInt8(name):
    """signed, big endian 8-bit integer"""
    return FormatField(name, ">", "b")
def SBInt16(name):
    """signed, big endian 16-bit integer"""
    return FormatField(name, ">", "h")
def SBInt32(name):
    """signed, big endian 32-bit integer"""
    return FormatField(name, ">", "l")
def SBInt64(name):
    """signed, big endian 64-bit integer"""
    return FormatField(name, ">", "q")

def ULInt8(name):
    """unsigned, little endian 8-bit integer"""
    return FormatField(name, "<", "B")
def ULInt16(name):
    """unsigned, little endian 16-bit integer"""
    return FormatField(name, "<", "H")
def ULInt32(name):
    """unsigned, little endian 32-bit integer"""
    return FormatField(name, "<", "L")
def ULInt64(name):
    """unsigned, little endian 64-bit integer"""
    return FormatField(name, "<", "Q")

def SLInt8(name):
    """signed, little endian 8-bit integer"""
    return FormatField(name, "<", "b")
def SLInt16(name):
    """signed, little endian 16-bit integer"""
    return FormatField(name, "<", "h")
def SLInt32(name):
    """signed, little endian 32-bit integer"""
    return FormatField(name, "<", "l")
def SLInt64(name):
    """signed, little endian 64-bit integer"""
    return FormatField(name, "<", "q")

def UNInt8(name):
    """unsigned, native endianity 8-bit integer"""
    return FormatField(name, "=", "B")
def UNInt16(name):
    """unsigned, native endianity 16-bit integer"""
    return FormatField(name, "=", "H")
def UNInt32(name):
    """unsigned, native endianity 32-bit integer"""
    return FormatField(name, "=", "L")
def UNInt64(name):
    """unsigned, native endianity 64-bit integer"""
    return FormatField(name, "=", "Q")

def SNInt8(name):
    """signed, native endianity 8-bit integer"""
    return FormatField(name, "=", "b")
def SNInt16(name):
    """signed, native endianity 16-bit integer"""
    return FormatField(name, "=", "h")
def SNInt32(name):
    """signed, native endianity 32-bit integer"""
    return FormatField(name, "=", "l")
def SNInt64(name):
    """signed, native endianity 64-bit integer"""
    return FormatField(name, "=", "q")

def BFloat32(name):
    """big endian, 32-bit IEEE floating point number"""
    return FormatField(name, ">", "f")
def LFloat32(name):
    """little endian, 32-bit IEEE floating point number"""
    return FormatField(name, "<", "f")
def NFloat32(name):
    """native endianity, 32-bit IEEE floating point number"""
    return FormatField(name, "=", "f")

def BFloat64(name):
    """big endian, 64-bit IEEE floating point number"""
    return FormatField(name, ">", "d")
def LFloat64(name):
    """little endian, 64-bit IEEE floating point number"""
    return FormatField(name, "<", "d")
def NFloat64(name):
    """native endianity, 64-bit IEEE floating point number"""
    return FormatField(name, "=", "d")


#===============================================================================
# arrays
#===============================================================================
def Array(count, subcon):
    """
    Repeats the given unit a fixed number of times.

    :param int count: number of times to repeat
    :param ``Construct`` subcon: construct to repeat

    >>> c = Array(4, UBInt8("foo"))
    >>> c.parse("\\x01\\x02\\x03\\x04")
    [1, 2, 3, 4]
    >>> c.parse("\\x01\\x02\\x03\\x04\\x05\\x06")
    [1, 2, 3, 4]
    >>> c.build([5,6,7,8])
    '\\x05\\x06\\x07\\x08'
    >>> c.build([5,6,7,8,9])
    Traceback (most recent call last):
      ...
    construct.core.RangeError: expected 4..4, found 5
    """

    if callable(count):
        con = MetaArray(count, subcon)
    else:
        con = MetaArray(lambda ctx: count, subcon)
        con._clear_flag(con.FLAG_DYNAMIC)
    return con

def PrefixedArray(subcon, length_field = UBInt8("length")):
    """an array prefixed by a length field.
    * subcon - the subcon to be repeated
    * length_field - a construct returning an integer
    """
    return LengthValueAdapter(
        Sequence(subcon.name,
            length_field,
            Array(lambda ctx: ctx[length_field.name], subcon),
            nested = False
        )
    )

def OpenRange(mincount, subcon):
    from sys import maxsize
    return Range(mincount, maxsize, subcon)

def GreedyRange(subcon):
    """
    Repeats the given unit one or more times.

    :param ``Construct`` subcon: construct to repeat

    >>> from construct import GreedyRange, UBInt8
    >>> c = GreedyRange(UBInt8("foo"))
    >>> c.parse("\\x01")
    [1]
    >>> c.parse("\\x01\\x02\\x03")
    [1, 2, 3]
    >>> c.parse("\\x01\\x02\\x03\\x04\\x05\\x06")
    [1, 2, 3, 4, 5, 6]
    >>> c.parse("")
    Traceback (most recent call last):
      ...
    construct.core.RangeError: expected 1..2147483647, found 0
    >>> c.build([1,2])
    '\\x01\\x02'
    >>> c.build([])
    Traceback (most recent call last):
      ...
    construct.core.RangeError: expected 1..2147483647, found 0
    """

    return OpenRange(1, subcon)

def OptionalGreedyRange(subcon):
    """
    Repeats the given unit zero or more times. This repeater can't
    fail, as it accepts lists of any length.

    :param ``Construct`` subcon: construct to repeat

    >>> from construct import OptionalGreedyRange, UBInt8
    >>> c = OptionalGreedyRange(UBInt8("foo"))
    >>> c.parse("")
    []
    >>> c.parse("\\x01\\x02")
    [1, 2]
    >>> c.build([])
    ''
    >>> c.build([1,2])
    '\\x01\\x02'
    """

    return OpenRange(0, subcon)


#===============================================================================
# subconstructs
#===============================================================================
def Optional(subcon):
    """an optional construct. if parsing fails, returns None.
    * subcon - the subcon to optionally parse or build
    """
    return Select(subcon.name, subcon, Pass)

def Bitwise(subcon):
    """converts the stream to bits, and passes the bitstream to subcon
    * subcon - a bitwise construct (usually BitField)
    """
    # subcons larger than MAX_BUFFER will be wrapped by Restream instead
    # of Buffered. implementation details, don't stick your nose in :)
    MAX_BUFFER = 1024 * 8
    def resizer(length):
        if length & 7:
            raise SizeofError("size must be a multiple of 8", length)
        return length >> 3
    if not subcon._is_flag(subcon.FLAG_DYNAMIC) and subcon.sizeof() < MAX_BUFFER:
        con = Buffered(subcon,
            encoder = decode_bin,
            decoder = encode_bin,
            resizer = resizer
        )
    else:
        con = Restream(subcon,
            stream_reader = BitStreamReader,
            stream_writer = BitStreamWriter,
            resizer = resizer)
    return con

def Aligned(subcon, modulus = 4, pattern = "\x00"):
    r"""aligns subcon to modulus boundary using padding pattern
    * subcon - the subcon to align
    * modulus - the modulus boundary (default is 4)
    * pattern - the padding pattern (default is \x00)
    """
    if modulus < 2:
        raise ValueError("modulus must be >= 2", modulus)
    def padlength(ctx):
        return (modulus - (subcon._sizeof(ctx) % modulus)) % modulus
    return SeqOfOne(subcon.name,
        subcon,
        # ??????
        # ??????
        # ??????
        # ??????
        Padding(padlength, pattern = pattern),
        nested = False,
    )

def SeqOfOne(name, *args, **kw):
    """a sequence of one element. only the first element is meaningful, the
    rest are discarded
    * name - the name of the sequence
    * args - subconstructs
    * kw - any keyword arguments to Sequence
    """
    return IndexingAdapter(Sequence(name, *args, **kw), index = 0)

def Embedded(subcon):
    """embeds a struct into the enclosing struct.
    * subcon - the struct to embed
    """
    return Reconfig(subcon.name, subcon, subcon.FLAG_EMBED)

def Rename(newname, subcon):
    """renames an existing construct
    * newname - the new name
    * subcon - the subcon to rename
    """
    return Reconfig(newname, subcon)

def Alias(newname, oldname):
    """creates an alias for an existing element in a struct
    * newname - the new name
    * oldname - the name of an existing element
    """
    return Value(newname, lambda ctx: ctx[oldname])


#===============================================================================
# mapping
#===============================================================================
def SymmetricMapping(subcon, mapping, default = NotImplemented):
    """defines a symmetrical mapping: a->b, b->a.
    * subcon - the subcon to map
    * mapping - the encoding mapping (a dict); the decoding mapping is
      achieved by reversing this mapping
    * default - the default value to use when no mapping is found. if no
      default value is given, and exception is raised. setting to Pass would
      return the value "as is" (unmapped)
    """
    reversed_mapping = dict((v, k) for k, v in mapping.items())
    return MappingAdapter(subcon,
        encoding = mapping,
        decoding = reversed_mapping,
        encdefault = default,
        decdefault = default,
    )

def Enum(subcon, **kw):
    """a set of named values mapping.
    * subcon - the subcon to map
    * kw - keyword arguments which serve as the encoding mapping
    * _default_ - an optional, keyword-only argument that specifies the
      default value to use when the mapping is undefined. if not given,
      and exception is raised when the mapping is undefined. use `Pass` to
      pass the unmapped value as-is
    """
    return SymmetricMapping(subcon, kw, kw.pop("_default_", NotImplemented))

def FlagsEnum(subcon, **kw):
    """a set of flag values mapping.
    * subcon - the subcon to map
    * kw - keyword arguments which serve as the encoding mapping
    """
    return FlagsAdapter(subcon, kw)


#===============================================================================
# structs
#===============================================================================
def AlignedStruct(name, *subcons, **kw):
    """a struct of aligned fields
    * name - the name of the struct
    * subcons - the subcons that make up this structure
    * kw - keyword arguments to pass to Aligned: 'modulus' and 'pattern'
    """
    return Struct(name, *(Aligned(sc, **kw) for sc in subcons))

def BitStruct(name, *subcons):
    """a struct of bitwise fields
    * name - the name of the struct
    * subcons - the subcons that make up this structure
    """
    return Bitwise(Struct(name, *subcons))

def EmbeddedBitStruct(*subcons):
    """an embedded BitStruct. no name is necessary.
    * subcons - the subcons that make up this structure
    """
    return Bitwise(Embedded(Struct(None, *subcons)))

#===============================================================================
# strings
#===============================================================================
def String(name, length, encoding=None, padchar=None, paddir="right",
    trimdir="right"):
    """
    A configurable, fixed-length string field.

    The padding character must be specified for padding and trimming to work.

    :param str name: name
    :param int length: length, in bytes
    :param str encoding: encoding (e.g. "utf8") or None for no encoding
    :param str padchar: optional character to pad out strings
    :param str paddir: direction to pad out strings; one of "right", "left",
                       or "both"
    :param str trim: direction to trim strings; one of "right", "left"

    >>> from construct import String
    >>> String("foo", 5).parse("hello")
    'hello'
    >>>
    >>> String("foo", 12, encoding = "utf8").parse("hello joh\\xd4\\x83n")
    u'hello joh\\u0503n'
    >>>
    >>> foo = String("foo", 10, padchar = "X", paddir = "right")
    >>> foo.parse("helloXXXXX")
    'hello'
    >>> foo.build("hello")
    'helloXXXXX'
    """

    con = StringAdapter(Field(name, length), encoding=encoding)
    if padchar is not None:
        con = PaddedStringAdapter(con, padchar=padchar, paddir=paddir,
            trimdir=trimdir)
    return con

def PascalString(name, length_field=UBInt8("length"), encoding=None):
    """
    A length-prefixed string.

    ``PascalString`` is named after the string types of Pascal, which are
    length-prefixed. Lisp strings also follow this convention.

    The length field will appear in the same ``Container`` as the
    ``PascalString``, with the given name.

    :param str name: name
    :param ``Construct`` length_field: a field which will store the length of
                                       the string
    :param str encoding: encoding (e.g. "utf8") or None for no encoding

    >>> foo = PascalString("foo")
    >>> foo.parse("\\x05hello")
    'hello'
    >>> foo.build("hello world")
    '\\x0bhello world'
    >>>
    >>> foo = PascalString("foo", length_field = UBInt16("length"))
    >>> foo.parse("\\x00\\x05hello")
    'hello'
    >>> foo.build("hello")
    '\\x00\\x05hello'
    """

    return StringAdapter(
        LengthValueAdapter(
            Sequence(name,
                length_field,
                Field("data", lambda ctx: ctx[length_field.name]),
            )
        ),
        encoding=encoding,
    )

def CString(name, terminators=b"\x00", encoding=None,
            char_field=Field(None, 1)):
    """
    A string ending in a terminator.

    ``CString`` is similar to the strings of C, C++, and other related
    programming languages.

    By default, the terminator is the NULL byte (b``0x00``).

    :param str name: name
    :param iterable terminators: sequence of valid terminators, in order of
                                 preference
    :param str encoding: encoding (e.g. "utf8") or None for no encoding
    :param ``Construct`` char_field: construct representing a single character

    >>> foo = CString("foo")
    >>> foo.parse(b"hello\\x00")
    b'hello'
    >>> foo.build(b"hello")
    b'hello\\x00'
    >>> foo = CString("foo", terminators = b"XYZ")
    >>> foo.parse(b"helloX")
    b'hello'
    >>> foo.parse(b"helloY")
    b'hello'
    >>> foo.parse(b"helloZ")
    b'hello'
    >>> foo.build(b"hello")
    b'helloX'
    """

    return Rename(name,
        CStringAdapter(
            RepeatUntil(lambda obj, ctx: obj in terminators, char_field),
            terminators=terminators,
            encoding=encoding,
        )
    )


#===============================================================================
# conditional
#===============================================================================
def IfThenElse(name, predicate, then_subcon, else_subcon):
    """an if-then-else conditional construct: if the predicate indicates True,
    `then_subcon` will be used; otherwise `else_subcon`
    * name - the name of the construct
    * predicate - a function taking the context as an argument and returning
      True or False
    * then_subcon - the subcon that will be used if the predicate returns True
    * else_subcon - the subcon that will be used if the predicate returns False
    """
    return Switch(name, lambda ctx: bool(predicate(ctx)),
        {
            True : then_subcon,
            False : else_subcon,
        }
    )

def If(predicate, subcon, elsevalue = None):
    """an if-then conditional construct: if the predicate indicates True,
    subcon will be used; otherwise, `elsevalue` will be returned instead.
    * predicate - a function taking the context as an argument and returning
      True or False
    * subcon - the subcon that will be used if the predicate returns True
    * elsevalue - the value that will be used should the predicate return False.
      by default this value is None.
    """
    return IfThenElse(subcon.name,
        predicate,
        subcon,
        Value("elsevalue", lambda ctx: elsevalue)
    )


#===============================================================================
# misc
#===============================================================================
def OnDemandPointer(offsetfunc, subcon, force_build = True):
    """an on-demand pointer.
    * offsetfunc - a function taking the context as an argument and returning
      the absolute stream position
    * subcon - the subcon that will be parsed from the `offsetfunc()` stream
      position on demand
    * force_build - see OnDemand. by default True.
    """
    return OnDemand(Pointer(offsetfunc, subcon),
        advance_stream = False,
        force_build = force_build
    )

def Magic(data):
    return ConstAdapter(Field(None, len(data)), data)

########NEW FILE########
__FILENAME__ = abbrevtable
#-------------------------------------------------------------------------------
# elftools: dwarf/abbrevtable.py
#
# DWARF abbreviation table
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
from ..common.utils import struct_parse, dwarf_assert


class AbbrevTable(object):
    """ Represents a DWARF abbreviation table.
    """
    def __init__(self, structs, stream, offset):
        """ Create new abbreviation table. Parses the actual table from the
            stream and stores it internally.
        
            structs:
                A DWARFStructs instance for parsing the data
            
            stream, offset:
                The stream and offset into the stream where this abbreviation
                table lives.
        """
        self.structs = structs
        self.stream = stream
        self.offset = offset
        
        self._abbrev_map = self._parse_abbrev_table()

    def get_abbrev(self, code):
        """ Get the AbbrevDecl for a given code. Raise KeyError if no
            declaration for this code exists.
        """
        return AbbrevDecl(code, self._abbrev_map[code])

    def _parse_abbrev_table(self):
        """ Parse the abbrev table from the stream
        """
        map = {}
        self.stream.seek(self.offset)
        while True:
            decl_code = struct_parse(
                struct=self.structs.Dwarf_uleb128(''),
                stream=self.stream)
            if decl_code == 0:
                break
            declaration = struct_parse(
                struct=self.structs.Dwarf_abbrev_declaration,
                stream=self.stream)
            map[decl_code] = declaration
        return map


class AbbrevDecl(object):
    """ Wraps a parsed abbreviation declaration, exposing its fields with 
        dict-like access, and adding some convenience methods.
        
        The abbreviation declaration represents an "entry" that points to it.
    """
    def __init__(self, code, decl):
        self.code = code
        self.decl = decl
    
    def has_children(self):
        """ Does the entry have children?
        """
        return self['children_flag'] == 'DW_CHILDREN_yes'

    def iter_attr_specs(self):
        """ Iterate over the attribute specifications for the entry. Yield
            (name, form) pairs.
        """
        for attr_spec in self['attr_spec']:
            yield attr_spec.name, attr_spec.form
            
    def __getitem__(self, entry):
        return self.decl[entry]


########NEW FILE########
__FILENAME__ = callframe
#-------------------------------------------------------------------------------
# elftools: dwarf/callframe.py
#
# DWARF call frame information
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
import copy
from collections import namedtuple
from ..common.utils import (struct_parse, dwarf_assert, preserve_stream_pos)
from ..common.py3compat import iterkeys
from .structs import DWARFStructs
from .constants import *


class CallFrameInfo(object):
    """ DWARF CFI (Call Frame Info)

        stream, size:
            A stream holding the .debug_frame section, and the size of the
            section in it.

        base_structs:
            The structs to be used as the base for parsing this section.
            Eventually, each entry gets its own structs based on the initial
            length field it starts with. The address_size, however, is taken
            from base_structs. This appears to be a limitation of the DWARFv3
            standard, fixed in v4.
            A discussion I had on dwarf-discuss confirms this.
            So for DWARFv4 we'll take the address size from the CIE header,
            but for earlier versions will use the elfclass of the containing
            file; more sophisticated methods are used by libdwarf and others,
            such as guessing which CU contains which FDEs (based on their
            address ranges) and taking the address_size from those CUs.
    """
    def __init__(self, stream, size, base_structs):
        self.stream = stream
        self.size = size
        self.base_structs = base_structs
        self.entries = None

        # Map between an offset in the stream and the entry object found at this
        # offset. Useful for assigning CIE to FDEs according to the CIE_pointer
        # header field which contains a stream offset.
        self._entry_cache = {}

    def get_entries(self):
        """ Get a list of entries that constitute this CFI. The list consists
            of CIE or FDE objects, in the order of their appearance in the
            section.
        """
        if self.entries is None:
            self.entries = self._parse_entries()
        return self.entries

    #-------------------------

    def _parse_entries(self):
        entries = []
        offset = 0
        while offset < self.size:
            entries.append(self._parse_entry_at(offset))
            offset = self.stream.tell()
        return entries

    def _parse_entry_at(self, offset):
        """ Parse an entry from self.stream starting with the given offset.
            Return the entry object. self.stream will point right after the
            entry.
        """
        if offset in self._entry_cache:
            return self._entry_cache[offset]

        entry_length = struct_parse(
            self.base_structs.Dwarf_uint32(''), self.stream, offset)
        dwarf_format = 64 if entry_length == 0xFFFFFFFF else 32

        entry_structs = DWARFStructs(
            little_endian=self.base_structs.little_endian,
            dwarf_format=dwarf_format,
            address_size=self.base_structs.address_size)

        # Read the next field to see whether this is a CIE or FDE
        CIE_id = struct_parse(
            entry_structs.Dwarf_offset(''), self.stream)

        is_CIE = (
            (dwarf_format == 32 and CIE_id == 0xFFFFFFFF) or
            CIE_id == 0xFFFFFFFFFFFFFFFF)

        if is_CIE:
            header_struct = entry_structs.Dwarf_CIE_header
        else:
            header_struct = entry_structs.Dwarf_FDE_header

        # Parse the header, which goes up to and including the
        # return_address_register field
        header = struct_parse(
            header_struct, self.stream, offset)

        # If this is DWARF version 4 or later, we can have a more precise
        # address size, read from the CIE header.
        if entry_structs.dwarf_version >= 4:
            entry_structs = DWARFStructs(
                little_endian=entry_structs.little_endian,
                dwarf_format=entry_structs.dwarf_format,
                address_size=header.address_size)

        # For convenience, compute the end offset for this entry
        end_offset = (
            offset + header.length +
            entry_structs.initial_length_field_size())

        # At this point self.stream is at the start of the instruction list
        # for this entry
        instructions = self._parse_instructions(
            entry_structs, self.stream.tell(), end_offset)

        if is_CIE:
            self._entry_cache[offset] = CIE(
                header=header, instructions=instructions, offset=offset,
                structs=entry_structs)
        else: # FDE
            with preserve_stream_pos(self.stream):
                cie = self._parse_entry_at(header['CIE_pointer'])
            self._entry_cache[offset] = FDE(
                header=header, instructions=instructions, offset=offset,
                structs=entry_structs, cie=cie)
        return self._entry_cache[offset]

    def _parse_instructions(self, structs, offset, end_offset):
        """ Parse a list of CFI instructions from self.stream, starting with
            the offset and until (not including) end_offset.
            Return a list of CallFrameInstruction objects.
        """
        instructions = []
        while offset < end_offset:
            opcode = struct_parse(structs.Dwarf_uint8(''), self.stream, offset)
            args = []

            primary = opcode & _PRIMARY_MASK
            primary_arg = opcode & _PRIMARY_ARG_MASK
            if primary == DW_CFA_advance_loc:
                args = [primary_arg]
            elif primary == DW_CFA_offset:
                args = [
                    primary_arg,
                    struct_parse(structs.Dwarf_uleb128(''), self.stream)]
            elif primary == DW_CFA_restore:
                args = [primary_arg]
            # primary == 0 and real opcode is extended
            elif opcode in (DW_CFA_nop, DW_CFA_remember_state,
                            DW_CFA_restore_state):
                args = []
            elif opcode == DW_CFA_set_loc:
                args = [
                    struct_parse(structs.Dwarf_target_addr(''), self.stream)]
            elif opcode == DW_CFA_advance_loc1:
                args = [struct_parse(structs.Dwarf_uint8(''), self.stream)]
            elif opcode == DW_CFA_advance_loc2:
                args = [struct_parse(structs.Dwarf_uint16(''), self.stream)]
            elif opcode == DW_CFA_advance_loc4:
                args = [struct_parse(structs.Dwarf_uint32(''), self.stream)]
            elif opcode in (DW_CFA_offset_extended, DW_CFA_register,
                            DW_CFA_def_cfa, DW_CFA_val_offset):
                args = [
                    struct_parse(structs.Dwarf_uleb128(''), self.stream),
                    struct_parse(structs.Dwarf_uleb128(''), self.stream)]
            elif opcode in (DW_CFA_restore_extended, DW_CFA_undefined,
                            DW_CFA_same_value, DW_CFA_def_cfa_register,
                            DW_CFA_def_cfa_offset):
                args = [struct_parse(structs.Dwarf_uleb128(''), self.stream)]
            elif opcode == DW_CFA_def_cfa_offset_sf:
                args = [struct_parse(structs.Dwarf_sleb128(''), self.stream)]
            elif opcode == DW_CFA_def_cfa_expression:
                args = [struct_parse(
                    structs.Dwarf_dw_form['DW_FORM_block'], self.stream)]
            elif opcode in (DW_CFA_expression, DW_CFA_val_expression):
                args = [
                    struct_parse(structs.Dwarf_uleb128(''), self.stream),
                    struct_parse(
                        structs.Dwarf_dw_form['DW_FORM_block'], self.stream)]
            elif opcode in (DW_CFA_offset_extended_sf,
                            DW_CFA_def_cfa_sf, DW_CFA_val_offset_sf):
                args = [
                    struct_parse(structs.Dwarf_uleb128(''), self.stream),
                    struct_parse(structs.Dwarf_sleb128(''), self.stream)]
            else:
                dwarf_assert(False, 'Unknown CFI opcode: 0x%x' % opcode)

            instructions.append(CallFrameInstruction(opcode=opcode, args=args))
            offset = self.stream.tell()
        return instructions


def instruction_name(opcode):
    """ Given an opcode, return the instruction name.
    """
    primary = opcode & _PRIMARY_MASK
    if primary == 0:
        return _OPCODE_NAME_MAP[opcode]
    else:
        return _OPCODE_NAME_MAP[primary]


class CallFrameInstruction(object):
    """ An instruction in the CFI section. opcode is the instruction
        opcode, numeric - as it appears in the section. args is a list of
        arguments (including arguments embedded in the low bits of some
        instructions, when applicable), decoded from the stream.
    """
    def __init__(self, opcode, args):
        self.opcode = opcode
        self.args = args

    def __repr__(self):
        return '%s (0x%x): %s' % (
            instruction_name(self.opcode), self.opcode, self.args)


class CFIEntry(object):
    """ A common base class for CFI entries.
        Contains a header and a list of instructions (CallFrameInstruction).
        offset: the offset of this entry from the beginning of the section
        cie: for FDEs, a CIE pointer is required
    """
    def __init__(self, header, structs, instructions, offset, cie=None):
        self.header = header
        self.structs = structs
        self.instructions = instructions
        self.offset = offset
        self.cie = cie
        self._decoded_table = None

    def get_decoded(self):
        """ Decode the CFI contained in this entry and return a
            DecodedCallFrameTable object representing it. See the documentation
            of that class to understand how to interpret the decoded table.
        """
        if self._decoded_table is None:
            self._decoded_table = self._decode_CFI_table()
        return self._decoded_table

    def __getitem__(self, name):
        """ Implement dict-like access to header entries
        """
        return self.header[name]

    def _decode_CFI_table(self):
        """ Decode the instructions contained in the given CFI entry and return
            a DecodedCallFrameTable.
        """
        if isinstance(self, CIE):
            # For a CIE, initialize cur_line to an "empty" line
            cie = self
            cur_line = dict(pc=0, cfa=None)
            reg_order = []
        else: # FDE
            # For a FDE, we need to decode the attached CIE first, because its
            # decoded table is needed. Its "initial instructions" describe a
            # line that serves as the base (first) line in the FDE's table.
            cie = self.cie
            cie_decoded_table = cie.get_decoded()
            last_line_in_CIE = copy.copy(cie_decoded_table.table[-1])
            cur_line = last_line_in_CIE
            cur_line['pc'] = self['initial_location']
            reg_order = copy.copy(cie_decoded_table.reg_order)

        table = []

        # Keeps a stack for the use of DW_CFA_{remember|restore}_state
        # instructions.
        line_stack = []

        def _add_to_order(regnum):
            if regnum not in cur_line:
                reg_order.append(regnum)

        for instr in self.instructions:
            # Throughout this loop, cur_line is the current line. Some
            # instructions add it to the table, but most instructions just
            # update it without adding it to the table.

            name = instruction_name(instr.opcode)

            if name == 'DW_CFA_set_loc':
                table.append(copy.copy(cur_line))
                cur_line['pc'] = instr.args[0]
            elif name in (  'DW_CFA_advance_loc1', 'DW_CFA_advance_loc2',
                            'DW_CFA_advance_loc4', 'DW_CFA_advance_loc'):
                table.append(copy.copy(cur_line))
                cur_line['pc'] += instr.args[0] * cie['code_alignment_factor']
            elif name == 'DW_CFA_def_cfa':
                cur_line['cfa'] = CFARule(
                    reg=instr.args[0],
                    offset=instr.args[1])
            elif name == 'DW_CFA_def_cfa_sf':
                cur_line['cfa'] = CFARule(
                    reg=instr.args[0],
                    offset=instr.args[1] * cie['code_alignment_factor'])
            elif name == 'DW_CFA_def_cfa_register':
                cur_line['cfa'] = CFARule(
                    reg=instr.args[0],
                    offset=cur_line['cfa'].offset)
            elif name == 'DW_CFA_def_cfa_offset':
                cur_line['cfa'] = CFARule(
                    reg=cur_line['cfa'].reg,
                    offset=instr.args[0])
            elif name == 'DW_CFA_def_cfa_expression':
                cur_line['cfa'] = CFARule(expr=instr.args[0])
            elif name == 'DW_CFA_undefined':
                _add_to_order(instr.args[0])
                cur_line[instr.args[0]] = RegisterRule(RegisterRule.UNDEFINED)
            elif name == 'DW_CFA_same_value':
                _add_to_order(instr.args[0])
                cur_line[instr.args[0]] = RegisterRule(RegisterRule.SAME_VALUE)
            elif name in (  'DW_CFA_offset', 'DW_CFA_offset_extended',
                            'DW_CFA_offset_extended_sf'):
                _add_to_order(instr.args[0])
                cur_line[instr.args[0]] = RegisterRule(
                    RegisterRule.OFFSET,
                    instr.args[1] * cie['data_alignment_factor'])
            elif name in ('DW_CFA_val_offset', 'DW_CFA_val_offset_sf'):
                _add_to_order(instr.args[0])
                cur_line[instr.args[0]] = RegisterRule(
                    RegisterRule.VAL_OFFSET,
                    instr.args[1] * cie['data_alignment_factor'])
            elif name == 'DW_CFA_register':
                _add_to_order(instr.args[0])
                cur_line[instr.args[0]] = RegisterRule(
                    RegisterRule.REGISTER,
                    instr.args[1])
            elif name == 'DW_CFA_expression':
                _add_to_order(instr.args[0])
                cur_line[instr.args[0]] = RegisterRule(
                    RegisterRule.EXPRESSION,
                    instr.args[1])
            elif name == 'DW_CFA_val_expression':
                _add_to_order(instr.args[0])
                cur_line[instr.args[0]] = RegisterRule(
                    RegisterRule.VAL_EXPRESSION,
                    instr.args[1])
            elif name in ('DW_CFA_restore', 'DW_CFA_restore_extended'):
                _add_to_order(instr.args[0])
                dwarf_assert(
                    isinstance(self, FDE),
                    '%s instruction must be in a FDE' % name)
                dwarf_assert(
                    instr.args[0] in last_line_in_CIE,
                    '%s: can not find register in CIE')
                cur_line[instr.args[0]] = last_line_in_CIE[instr.args[0]]
            elif name == 'DW_CFA_remember_state':
                line_stack.append(cur_line)
            elif name == 'DW_CFA_restore_state':
                cur_line = line_stack.pop()

        # The current line is appended to the table after all instructions
        # have ended, in any case (even if there were no instructions).
        table.append(cur_line)
        return DecodedCallFrameTable(table=table, reg_order=reg_order)


# A CIE and FDE have exactly the same functionality, except that a FDE has
# a pointer to its CIE. The functionality was wholly encapsulated in CFIEntry,
# so the CIE and FDE classes exists separately for identification (instead
# of having an explicit "entry_type" field in CFIEntry).
#
class CIE(CFIEntry):
    pass


class FDE(CFIEntry):
    pass


class RegisterRule(object):
    """ Register rules are used to find registers in call frames. Each rule
        consists of a type (enumeration following DWARFv3 section 6.4.1)
        and an optional argument to augment the type.
    """
    UNDEFINED = 'UNDEFINED'
    SAME_VALUE = 'SAME_VALUE'
    OFFSET = 'OFFSET'
    VAL_OFFSET = 'VAL_OFFSET'
    REGISTER = 'REGISTER'
    EXPRESSION = 'EXPRESSION'
    VAL_EXPRESSION = 'VAL_EXPRESSION'
    ARCHITECTURAL = 'ARCHITECTURAL'

    def __init__(self, type, arg=None):
        self.type = type
        self.arg = arg

    def __repr__(self):
        return 'RegisterRule(%s, %s)' % (self.type, self.arg)


class CFARule(object):
    """ A CFA rule is used to compute the CFA for each location. It either
        consists of a register+offset, or a DWARF expression.
    """
    def __init__(self, reg=None, offset=None, expr=None):
        self.reg = reg
        self.offset = offset
        self.expr = expr

    def __repr__(self):
        return 'CFARule(reg=%s, offset=%s, expr=%s)' % (
            self.reg, self.offset, self.expr)


# Represents the decoded CFI for an entry, which is just a large table,
# according to DWARFv3 section 6.4.1
#
# DecodedCallFrameTable is a simple named tuple to group together the table
# and the register appearance order.
#
# table:
#
# A list of dicts that represent "lines" in the decoded table. Each line has
# some special dict entries: 'pc' for the location/program counter (LOC),
# and 'cfa' for the CFARule to locate the CFA on that line.
# The other entries are keyed by register numbers with RegisterRule values,
# and describe the rules for these registers.
#
# reg_order:
#
# A list of register numbers that are described in the table by the order of
# their appearance.
#
DecodedCallFrameTable = namedtuple(
    'DecodedCallFrameTable', 'table reg_order')


#---------------- PRIVATE ----------------#

_PRIMARY_MASK = 0b11000000
_PRIMARY_ARG_MASK = 0b00111111

# This dictionary is filled by automatically scanning the constants module
# for DW_CFA_* instructions, and mapping their values to names. Since all
# names were imported from constants with `import *`, we look in globals()
_OPCODE_NAME_MAP = {}
for name in list(iterkeys(globals())):
    if name.startswith('DW_CFA'):
        _OPCODE_NAME_MAP[globals()[name]] = name





########NEW FILE########
__FILENAME__ = compileunit
#-------------------------------------------------------------------------------
# elftools: dwarf/compileunit.py
#
# DWARF compile unit
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
from .die import DIE


class CompileUnit(object):
    """ A DWARF compilation unit (CU).

            A normal compilation unit typically represents the text and data
            contributed to an executable by a single relocatable object file.
            It may be derived from several source files,
            including pre-processed "include files"

        Serves as a container and context to DIEs that describe objects and code
        belonging to a compilation unit.

        CU header entries can be accessed as dict keys from this object, i.e.
           cu = CompileUnit(...)
           cu['version']  # version field of the CU header

        To get the top-level DIE describing the compilation unit, call the
        get_top_DIE method.
    """
    def __init__(self, header, dwarfinfo, structs, cu_offset, cu_die_offset):
        """ header:
                CU header for this compile unit

            dwarfinfo:
                The DWARFInfo context object which created this one

            structs:
                A DWARFStructs instance suitable for this compile unit

            cu_offset:
                Offset in the stream to the beginning of this CU (its header)

            cu_die_offset:
                Offset in the stream of the top DIE of this CU
        """
        self.dwarfinfo = dwarfinfo
        self.header = header
        self.structs = structs
        self.cu_offset = cu_offset
        self.cu_die_offset = cu_die_offset

        # The abbreviation table for this CU. Filled lazily when DIEs are
        # requested.
        self._abbrev_table = None

        # A list of DIEs belonging to this CU. Lazily parsed.
        self._dielist = []

    def dwarf_format(self):
        """ Get the DWARF format (32 or 64) for this CU
        """
        return self.structs.dwarf_format

    def get_abbrev_table(self):
        """ Get the abbreviation table (AbbrevTable object) for this CU
        """
        if self._abbrev_table is None:
            self._abbrev_table = self.dwarfinfo.get_abbrev_table(
                self['debug_abbrev_offset'])
        return self._abbrev_table

    def get_top_DIE(self):
        """ Get the top DIE (which is either a DW_TAG_compile_unit or
            DW_TAG_partial_unit) of this CU
        """
        return self._get_DIE(0)

    def iter_DIEs(self):
        """ Iterate over all the DIEs in the CU, in order of their appearance.
            Note that null DIEs will also be returned.
        """
        self._parse_DIEs()
        return iter(self._dielist)

    #------ PRIVATE ------#

    def __getitem__(self, name):
        """ Implement dict-like access to header entries
        """
        return self.header[name]

    def _get_DIE(self, index):
        """ Get the DIE at the given index
        """
        self._parse_DIEs()
        return self._dielist[index]

    def _parse_DIEs(self):
        """ Parse all the DIEs pertaining to this CU from the stream and shove
            them sequentially into self._dielist.
            Also set the child/sibling/parent links in the DIEs according
            (unflattening the prefix-order of the DIE tree).
        """
        if len(self._dielist) > 0:
            return

        # Compute the boundary (one byte past the bounds) of this CU in the
        # stream
        cu_boundary = ( self.cu_offset +
                        self['unit_length'] +
                        self.structs.initial_length_field_size())

        # First pass: parse all DIEs and place them into self._dielist
        die_offset = self.cu_die_offset
        while die_offset < cu_boundary:
            die = DIE(
                    cu=self,
                    stream=self.dwarfinfo.debug_info_sec.stream,
                    offset=die_offset)
            self._dielist.append(die)
            die_offset += die.size

        # Second pass - unflatten the DIE tree
        self._unflatten_tree()

    def _unflatten_tree(self):
        """ "Unflatten" the DIE tree from it serial representation, by setting
            the child/sibling/parent links of DIEs.

            Assumes self._dielist was already populated by a linear list of DIEs
            read from the stream section
        """
        # the first DIE in the list is the root node
        root = self._dielist[0]
        parentstack = [root]

        for die in self._dielist[1:]:
            if not die.is_null():
                cur_parent = parentstack[-1]
                # This DIE is a child of the current parent
                cur_parent.add_child(die)
                die.set_parent(cur_parent)
                if die.has_children:
                    parentstack.append(die)
            else:
                # parentstack should not be really empty here. However, some
                # compilers generate DWARF that has extra NULLs in the end and
                # we don't want pyelftools to fail parsing them just because of
                # this.
                if len(parentstack) > 0:
                    # end of children for the current parent
                    parentstack.pop()


########NEW FILE########
__FILENAME__ = constants
#-------------------------------------------------------------------------------
# elftools: dwarf/constants.py
#
# Constants and flags
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------

# Inline codes
#
DW_INL_not_inlined = 0
DW_INL_inlined = 1
DW_INL_declared_not_inlined = 2
DW_INL_declared_inlined = 3


# Source languages
#
DW_LANG_C89 = 0x0001
DW_LANG_C = 0x0002
DW_LANG_Ada83 = 0x0003
DW_LANG_C_plus_plus = 0x0004
DW_LANG_Cobol74 = 0x0005
DW_LANG_Cobol85 = 0x0006
DW_LANG_Fortran77 = 0x0007
DW_LANG_Fortran90 = 0x0008
DW_LANG_Pascal83 = 0x0009
DW_LANG_Modula2 = 0x000a
DW_LANG_Java = 0x000b
DW_LANG_C99 = 0x000c
DW_LANG_Ada95 = 0x000d
DW_LANG_Fortran95 = 0x000e
DW_LANG_PLI = 0x000f
DW_LANG_ObjC = 0x0010
DW_LANG_ObjC_plus_plus = 0x0011
DW_LANG_UPC = 0x0012
DW_LANG_D = 0x0013
DW_LANG_Python = 0x0014
DW_LANG_Mips_Assembler = 0x8001
DW_LANG_Upc = 0x8765
DW_LANG_HP_Bliss = 0x8003
DW_LANG_HP_Basic91 = 0x8004
DW_LANG_HP_Pascal91 = 0x8005
DW_LANG_HP_IMacro = 0x8006
DW_LANG_HP_Assembler = 0x8007


# Encoding
#
DW_ATE_void = 0x0
DW_ATE_address = 0x1
DW_ATE_boolean = 0x2
DW_ATE_complex_float = 0x3
DW_ATE_float = 0x4
DW_ATE_signed = 0x5
DW_ATE_signed_char = 0x6
DW_ATE_unsigned = 0x7
DW_ATE_unsigned_char = 0x8
DW_ATE_imaginary_float = 0x9
DW_ATE_packed_decimal = 0xa
DW_ATE_numeric_string = 0xb
DW_ATE_edited = 0xc
DW_ATE_signed_fixed = 0xd
DW_ATE_unsigned_fixed = 0xe
DW_ATE_decimal_float = 0xf
DW_ATE_UTF = 0x10
DW_ATE_lo_user = 0x80
DW_ATE_hi_user = 0xff
DW_ATE_HP_float80 = 0x80
DW_ATE_HP_complex_float80 = 0x81
DW_ATE_HP_float128 = 0x82
DW_ATE_HP_complex_float128 = 0x83
DW_ATE_HP_floathpintel = 0x84
DW_ATE_HP_imaginary_float80 = 0x85
DW_ATE_HP_imaginary_float128 = 0x86


# Access
#
DW_ACCESS_public = 1
DW_ACCESS_protected = 2
DW_ACCESS_private = 3


# Visibility
#
DW_VIS_local = 1
DW_VIS_exported = 2
DW_VIS_qualified = 3


# Virtuality
#
DW_VIRTUALITY_none = 0
DW_VIRTUALITY_virtual = 1
DW_VIRTUALITY_pure_virtual = 2


# ID case
#
DW_ID_case_sensitive = 0
DW_ID_up_case = 1
DW_ID_down_case = 2
DW_ID_case_insensitive = 3


# Calling convention
#
DW_CC_normal = 0x1
DW_CC_program = 0x2
DW_CC_nocall = 0x3


# Ordering
#
DW_ORD_row_major = 0
DW_ORD_col_major = 1


# Line program opcodes
#
DW_LNS_copy = 0x01
DW_LNS_advance_pc = 0x02
DW_LNS_advance_line = 0x03
DW_LNS_set_file = 0x04
DW_LNS_set_column = 0x05
DW_LNS_negate_stmt = 0x06
DW_LNS_set_basic_block = 0x07
DW_LNS_const_add_pc = 0x08
DW_LNS_fixed_advance_pc = 0x09
DW_LNS_set_prologue_end = 0x0a
DW_LNS_set_epilogue_begin = 0x0b
DW_LNS_set_isa = 0x0c
DW_LNE_end_sequence = 0x01
DW_LNE_set_address = 0x02
DW_LNE_define_file = 0x03


# Call frame instructions
#
# Note that the first 3 instructions have the so-called "primary opcode"
# (as described in DWARFv3 7.23), so only their highest 2 bits take part
# in the opcode decoding. They are kept as constants with the low bits masked
# out, and the callframe module knows how to handle this.
# The other instructions use an "extended opcode" encoded just in the low 6
# bits, with the high 2 bits, so these constants are exactly as they would
# appear in an actual file.
#
DW_CFA_advance_loc = 0b01000000
DW_CFA_offset = 0b10000000
DW_CFA_restore = 0b11000000
DW_CFA_nop = 0x00
DW_CFA_set_loc = 0x01
DW_CFA_advance_loc1 = 0x02
DW_CFA_advance_loc2 = 0x03
DW_CFA_advance_loc4 = 0x04
DW_CFA_offset_extended = 0x05
DW_CFA_restore_extended = 0x06
DW_CFA_undefined = 0x07
DW_CFA_same_value = 0x08
DW_CFA_register = 0x09
DW_CFA_remember_state = 0x0a
DW_CFA_restore_state = 0x0b
DW_CFA_def_cfa = 0x0c
DW_CFA_def_cfa_register = 0x0d
DW_CFA_def_cfa_offset = 0x0e
DW_CFA_def_cfa_expression = 0x0f
DW_CFA_expression = 0x10
DW_CFA_offset_extended_sf = 0x11
DW_CFA_def_cfa_sf = 0x12
DW_CFA_def_cfa_offset_sf = 0x13
DW_CFA_val_offset = 0x14
DW_CFA_val_offset_sf = 0x15
DW_CFA_val_expression = 0x16



########NEW FILE########
__FILENAME__ = descriptions
#-------------------------------------------------------------------------------
# elftools: dwarf/descriptions.py
#
# Textual descriptions of the various values and enums of DWARF
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
from collections import defaultdict

from .constants import *
from .dwarf_expr import GenericExprVisitor
from .die import DIE
from ..common.utils import preserve_stream_pos, dwarf_assert
from ..common.py3compat import bytes2str
from .callframe import instruction_name, CIE, FDE


def set_global_machine_arch(machine_arch):
    global _MACHINE_ARCH
    _MACHINE_ARCH = machine_arch


def describe_attr_value(attr, die, section_offset):
    """ Given an attribute attr, return the textual representation of its
        value, suitable for tools like readelf.

        To cover all cases, this function needs some extra arguments:

        die: the DIE this attribute was extracted from
        section_offset: offset in the stream of the section the DIE belongs to
    """
    descr_func = _ATTR_DESCRIPTION_MAP[attr.form]
    val_description = descr_func(attr, die, section_offset)

    # For some attributes we can display further information
    extra_info_func = _EXTRA_INFO_DESCRIPTION_MAP[attr.name]
    extra_info = extra_info_func(attr, die, section_offset)
    return str(val_description) + '\t' + extra_info


def describe_CFI_instructions(entry):
    """ Given a CFI entry (CIE or FDE), return the textual description of its
        instructions.
    """
    def _assert_FDE_instruction(instr):
        dwarf_assert(
            isinstance(entry, FDE),
            'Unexpected instruction "%s" for a CIE' % instr)

    def _full_reg_name(regnum):
        return 'r%s (%s)' % (regnum, describe_reg_name(regnum))

    if isinstance(entry, CIE):
        cie = entry
    else: # FDE
        cie = entry.cie
        pc = entry['initial_location']

    s = ''
    for instr in entry.instructions:
        name = instruction_name(instr.opcode)

        if name in ('DW_CFA_offset',
                    'DW_CFA_offset_extended', 'DW_CFA_offset_extended_sf',
                    'DW_CFA_val_offset', 'DW_CFA_val_offset_sf'):
            s += '  %s: %s at cfa%+d\n' % (
                name, _full_reg_name(instr.args[0]),
                instr.args[1] * cie['data_alignment_factor'])
        elif name in (  'DW_CFA_restore', 'DW_CFA_restore_extended',
                        'DW_CFA_undefined', 'DW_CFA_same_value',
                        'DW_CFA_def_cfa_register'):
            s += '  %s: %s\n' % (name, _full_reg_name(instr.args[0]))
        elif name == 'DW_CFA_register':
            s += '  %s: %s in %s' % (
                name, _full_reg_name(instr.args[0]),
                _full_reg_name(instr.args[1]))
        elif name == 'DW_CFA_set_loc':
            pc = instr.args[0]
            s += '  %s: %08x\n' % (name, pc)
        elif name in (  'DW_CFA_advance_loc1', 'DW_CFA_advance_loc2',
                        'DW_CFA_advance_loc4', 'DW_CFA_advance_loc'):
            _assert_FDE_instruction(instr)
            factored_offset = instr.args[0] * cie['code_alignment_factor']
            s += '  %s: %s to %016x\n' % (
                name, factored_offset, factored_offset + pc)
            pc += factored_offset
        elif name in (  'DW_CFA_remember_state', 'DW_CFA_restore_state',
                        'DW_CFA_nop'):
            s += '  %s\n' % name
        elif name == 'DW_CFA_def_cfa':
            s += '  %s: %s ofs %s\n' % (
                name, _full_reg_name(instr.args[0]), instr.args[1])
        elif name == 'DW_CFA_def_cfa_sf':
            s += '  %s: %s ofs %s\n' % (
                name, _full_reg_name(instr.args[0]),
                instr.args[1] * cie['data_alignment_factor'])
        elif name == 'DW_CFA_def_cfa_offset':
            s += '  %s: %s\n' % (name, instr.args[0])
        elif name == 'DW_CFA_def_cfa_expression':
            expr_dumper = ExprDumper(entry.structs)
            expr_dumper.process_expr(instr.args[0])
            s += '  %s: (%s)\n' % (name, expr_dumper.get_str())
        elif name == 'DW_CFA_expression':
            expr_dumper = ExprDumper(entry.structs)
            expr_dumper.process_expr(instr.args[1])
            s += '  %s: %s (%s)\n' % (
                name, _full_reg_name(instr.args[0]), expr_dumper.get_str())
        else:
            s += '  %s: <??>\n' % name

    return s


def describe_CFI_register_rule(rule):
    s = _DESCR_CFI_REGISTER_RULE_TYPE[rule.type]
    if rule.type in ('OFFSET', 'VAL_OFFSET'):
        s += '%+d' % rule.arg
    elif rule.type == 'REGISTER':
        s += describe_reg_name(rule.arg)
    return s


def describe_CFI_CFA_rule(rule):
    if rule.expr:
        return 'exp'
    else:
        return '%s%+d' % (describe_reg_name(rule.reg), rule.offset)


def describe_DWARF_expr(expr, structs):
    """ Textual description of a DWARF expression encoded in 'expr'.
        structs should come from the entity encompassing the expression - it's
        needed to be able to parse it correctly.
    """
    # Since this function can be called a lot, initializing a fresh new
    # ExprDumper per call is expensive. So a rudimentary caching scheme is in
    # place to create only one such dumper per instance of structs.
    cache_key = id(structs)
    if cache_key not in _DWARF_EXPR_DUMPER_CACHE:
        _DWARF_EXPR_DUMPER_CACHE[cache_key] = \
            ExprDumper(structs)
    dwarf_expr_dumper = _DWARF_EXPR_DUMPER_CACHE[cache_key]
    dwarf_expr_dumper.clear()
    dwarf_expr_dumper.process_expr(expr)
    return '(' + dwarf_expr_dumper.get_str() + ')'


def describe_reg_name(regnum, machine_arch=None):
    """ Provide a textual description for a register name, given its serial
        number. The number is expected to be valid.
    """
    if machine_arch is None:
        machine_arch = _MACHINE_ARCH

    if machine_arch == 'x86':
        return _REG_NAMES_x86[regnum]
    elif machine_arch == 'x64':
        return _REG_NAMES_x64[regnum]
    else:
        return '<none>'

#-------------------------------------------------------------------------------

# The machine architecture. Set globally via set_global_machine_arch
#
_MACHINE_ARCH = None


def _describe_attr_ref(attr, die, section_offset):
    return '<0x%x>' % (attr.value + die.cu.cu_offset)

def _describe_attr_value_passthrough(attr, die, section_offset):
    return attr.value

def _describe_attr_hex(attr, die, section_offset):
    return '0x%x' % (attr.value)

def _describe_attr_hex_addr(attr, die, section_offset):
    return '<0x%x>' % (attr.value)

def _describe_attr_split_64bit(attr, die, section_offset):
    low_word = attr.value & 0xFFFFFFFF
    high_word = (attr.value >> 32) & 0xFFFFFFFF
    return '0x%x 0x%x' % (low_word, high_word)

def _describe_attr_strp(attr, die, section_offset):
    return '(indirect string, offset: 0x%x): %s' % (
        attr.raw_value, bytes2str(attr.value))

def _describe_attr_string(attr, die, section_offset):
    return bytes2str(attr.value)

def _describe_attr_debool(attr, die, section_offset):
    """ To be consistent with readelf, generate 1 for True flags, 0 for False
        flags.
    """
    return '1' if attr.value else '0'

def _describe_attr_present(attr, die, section_offset):
    """ Some forms may simply mean that an attribute is present,
        without providing any value.
    """
    return '1'

def _describe_attr_block(attr, die, section_offset):
    s = '%s byte block: ' % len(attr.value)
    s += ' '.join('%x' % item for item in attr.value) + ' '
    return s


_ATTR_DESCRIPTION_MAP = defaultdict(
    lambda: _describe_attr_value_passthrough, # default_factory

    DW_FORM_ref1=_describe_attr_ref,
    DW_FORM_ref2=_describe_attr_ref,
    DW_FORM_ref4=_describe_attr_ref,
    DW_FORM_ref8=_describe_attr_split_64bit,
    DW_FORM_ref_udata=_describe_attr_ref,
    DW_FORM_ref_addr=_describe_attr_hex_addr,
    DW_FORM_data4=_describe_attr_hex,
    DW_FORM_data8=_describe_attr_hex,
    DW_FORM_addr=_describe_attr_hex,
    DW_FORM_sec_offset=_describe_attr_hex,
    DW_FORM_flag=_describe_attr_debool,
    DW_FORM_data1=_describe_attr_value_passthrough,
    DW_FORM_data2=_describe_attr_value_passthrough,
    DW_FORM_sdata=_describe_attr_value_passthrough,
    DW_FORM_udata=_describe_attr_value_passthrough,
    DW_FORM_string=_describe_attr_string,
    DW_FORM_strp=_describe_attr_strp,
    DW_FORM_block1=_describe_attr_block,
    DW_FORM_block2=_describe_attr_block,
    DW_FORM_block4=_describe_attr_block,
    DW_FORM_block=_describe_attr_block,
    DW_FORM_flag_present=_describe_attr_present,
    DW_FORM_exprloc=_describe_attr_block,
    DW_FORM_ref_sig8=_describe_attr_ref,
)


_DESCR_DW_INL = {
    DW_INL_not_inlined: '(not inlined)',
    DW_INL_inlined: '(inlined)',
    DW_INL_declared_not_inlined: '(declared as inline but ignored)',
    DW_INL_declared_inlined: '(declared as inline and inlined)',
}

_DESCR_DW_LANG = {
    DW_LANG_C89: '(ANSI C)',
    DW_LANG_C: '(non-ANSI C)',
    DW_LANG_Ada83: '(Ada)',
    DW_LANG_C_plus_plus: '(C++)',
    DW_LANG_Cobol74: '(Cobol 74)',
    DW_LANG_Cobol85: '(Cobol 85)',
    DW_LANG_Fortran77: '(FORTRAN 77)',
    DW_LANG_Fortran90: '(Fortran 90)',
    DW_LANG_Pascal83: '(ANSI Pascal)',
    DW_LANG_Modula2: '(Modula 2)',
    DW_LANG_Java: '(Java)',
    DW_LANG_C99: '(ANSI C99)',
    DW_LANG_Ada95: '(ADA 95)',
    DW_LANG_Fortran95: '(Fortran 95)',
    DW_LANG_PLI: '(PLI)',
    DW_LANG_ObjC: '(Objective C)',
    DW_LANG_ObjC_plus_plus: '(Objective C++)',
    DW_LANG_UPC: '(Unified Parallel C)',
    DW_LANG_D: '(D)',
    DW_LANG_Python: '(Python)',
    DW_LANG_Mips_Assembler: '(MIPS assembler)',
    DW_LANG_Upc: '(nified Parallel C)',
    DW_LANG_HP_Bliss: '(HP Bliss)',
    DW_LANG_HP_Basic91: '(HP Basic 91)',
    DW_LANG_HP_Pascal91: '(HP Pascal 91)',
    DW_LANG_HP_IMacro: '(HP IMacro)',
    DW_LANG_HP_Assembler: '(HP assembler)',
}

_DESCR_DW_ATE = {
    DW_ATE_void: '(void)',
    DW_ATE_address: '(machine address)',
    DW_ATE_boolean: '(boolean)',
    DW_ATE_complex_float: '(complex float)',
    DW_ATE_float: '(float)',
    DW_ATE_signed: '(signed)',
    DW_ATE_signed_char: '(signed char)',
    DW_ATE_unsigned: '(unsigned)',
    DW_ATE_unsigned_char: '(unsigned char)',
    DW_ATE_imaginary_float: '(imaginary float)',
    DW_ATE_decimal_float: '(decimal float)',
    DW_ATE_packed_decimal: '(packed_decimal)',
    DW_ATE_numeric_string: '(numeric_string)',
    DW_ATE_edited: '(edited)',
    DW_ATE_signed_fixed: '(signed_fixed)',
    DW_ATE_unsigned_fixed: '(unsigned_fixed)',
    DW_ATE_HP_float80: '(HP_float80)',
    DW_ATE_HP_complex_float80: '(HP_complex_float80)',
    DW_ATE_HP_float128: '(HP_float128)',
    DW_ATE_HP_complex_float128: '(HP_complex_float128)',
    DW_ATE_HP_floathpintel: '(HP_floathpintel)',
    DW_ATE_HP_imaginary_float80: '(HP_imaginary_float80)',
    DW_ATE_HP_imaginary_float128: '(HP_imaginary_float128)',
}

_DESCR_DW_ACCESS = {
    DW_ACCESS_public: '(public)',
    DW_ACCESS_protected: '(protected)',
    DW_ACCESS_private: '(private)',
}

_DESCR_DW_VIS = {
    DW_VIS_local: '(local)',
    DW_VIS_exported: '(exported)',
    DW_VIS_qualified: '(qualified)',
}

_DESCR_DW_VIRTUALITY = {
    DW_VIRTUALITY_none: '(none)',
    DW_VIRTUALITY_virtual: '(virtual)',
    DW_VIRTUALITY_pure_virtual: '(pure virtual)',
}

_DESCR_DW_ID_CASE = {
    DW_ID_case_sensitive: '(case_sensitive)',
    DW_ID_up_case: '(up_case)',
    DW_ID_down_case: '(down_case)',
    DW_ID_case_insensitive: '(case_insensitive)',
}

_DESCR_DW_CC = {
    DW_CC_normal: '(normal)',
    DW_CC_program: '(program)',
    DW_CC_nocall: '(nocall)',
}

_DESCR_DW_ORD = {
    DW_ORD_row_major: '(row major)',
    DW_ORD_col_major: '(column major)',
}

_DESCR_CFI_REGISTER_RULE_TYPE = dict(
    UNDEFINED='u',
    SAME_VALUE='s',
    OFFSET='c',
    VAL_OFFSET='v',
    REGISTER='',
    EXPRESSION='exp',
    VAL_EXPRESSION='vexp',
    ARCHITECTURAL='a',
)

def _make_extra_mapper(mapping, default, default_interpolate_value=False):
    """ Create a mapping function from attribute parameters to an extra
        value that should be displayed.
    """
    def mapper(attr, die, section_offset):
        if default_interpolate_value:
            d = default % attr.value
        else:
            d = default
        return mapping.get(attr.value, d)
    return mapper


def _make_extra_string(s=''):
    """ Create an extra function that just returns a constant string.
    """
    def extra(attr, die, section_offset):
        return s
    return extra


_DWARF_EXPR_DUMPER_CACHE = {}

def _location_list_extra(attr, die, section_offset):
    # According to section 2.6 of the DWARF spec v3, class loclistptr means
    # a location list, and class block means a location expression.
    #
    if attr.form in ('DW_FORM_data4', 'DW_FORM_data8'):
        return '(location list)'
    else:
        return describe_DWARF_expr(attr.value, die.cu.structs)


def _import_extra(attr, die, section_offset):
    # For DW_AT_import the value points to a DIE (that can be either in the
    # current DIE's CU or in another CU, depending on the FORM). The extra
    # information for it is the abbreviation number in this DIE and its tag.
    if attr.form == 'DW_FORM_ref_addr':
        # Absolute offset value
        ref_die_offset = section_offset + attr.value
    else:
        # Relative offset to the current DIE's CU
        ref_die_offset = attr.value + die.cu.cu_offset

    # Now find the CU this DIE belongs to (since we have to find its abbrev
    # table). This is done by linearly scanning through all CUs, looking for
    # one spanning an address space containing the referred DIE's offset.
    for cu in die.dwarfinfo.iter_CUs():
        if cu['unit_length'] + cu.cu_offset > ref_die_offset >= cu.cu_offset:
            # Once we have the CU, we can actually parse this DIE from the
            # stream.
            with preserve_stream_pos(die.stream):
                ref_die = DIE(cu, die.stream, ref_die_offset)
            #print '&&& ref_die', ref_die
            return '[Abbrev Number: %s (%s)]' % (
                ref_die.abbrev_code, ref_die.tag)

    return '[unknown]'


_EXTRA_INFO_DESCRIPTION_MAP = defaultdict(
    lambda: _make_extra_string(''), # default_factory

    DW_AT_inline=_make_extra_mapper(
        _DESCR_DW_INL, '(Unknown inline attribute value: %x',
        default_interpolate_value=True),
    DW_AT_language=_make_extra_mapper(
        _DESCR_DW_LANG, '(Unknown: %x)', default_interpolate_value=True),
    DW_AT_encoding=_make_extra_mapper(_DESCR_DW_ATE, '(unknown type)'),
    DW_AT_accessibility=_make_extra_mapper(
        _DESCR_DW_ACCESS, '(unknown accessibility)'),
    DW_AT_visibility=_make_extra_mapper(
        _DESCR_DW_VIS, '(unknown visibility)'),
    DW_AT_virtuality=_make_extra_mapper(
        _DESCR_DW_VIRTUALITY, '(unknown virtuality)'),
    DW_AT_identifier_case=_make_extra_mapper(
        _DESCR_DW_ID_CASE, '(unknown case)'),
    DW_AT_calling_convention=_make_extra_mapper(
        _DESCR_DW_CC, '(unknown convention)'),
    DW_AT_ordering=_make_extra_mapper(
        _DESCR_DW_ORD, '(undefined)'),
    DW_AT_frame_base=_location_list_extra,
    DW_AT_location=_location_list_extra,
    DW_AT_string_length=_location_list_extra,
    DW_AT_return_addr=_location_list_extra,
    DW_AT_data_member_location=_location_list_extra,
    DW_AT_vtable_elem_location=_location_list_extra,
    DW_AT_segment=_location_list_extra,
    DW_AT_static_link=_location_list_extra,
    DW_AT_use_location=_location_list_extra,
    DW_AT_allocated=_location_list_extra,
    DW_AT_associated=_location_list_extra,
    DW_AT_data_location=_location_list_extra,
    DW_AT_stride=_location_list_extra,
    DW_AT_import=_import_extra,
)

# 8 in a line, for easier counting
_REG_NAMES_x86 = [
    'eax', 'ecx', 'edx', 'ebx', 'esp', 'ebp', 'esi', 'edi',
    'eip', 'eflags', '<none>', 'st0', 'st1', 'st2', 'st3', 'st4',
    'st5', 'st6', 'st7', '<none>', '<none>', 'xmm0', 'xmm1', 'xmm2',
    'xmm3', 'xmm4', 'xmm5', 'xmm6', 'xmm7', 'mm0', 'mm1', 'mm2',
    'mm3', 'mm4', 'mm5', 'mm6', 'mm7', 'fcw', 'fsw', 'mxcsr',
    'es', 'cs', 'ss', 'ds', 'fs', 'gs', '<none>', '<none>', 'tr', 'ldtr'
]

_REG_NAMES_x64 = [
    'rax', 'rdx', 'rcx', 'rbx', 'rsi', 'rdi', 'rbp', 'rsp',
    'r8',  'r9',  'r10', 'r11', 'r12', 'r13', 'r14', 'r15',
    'rip', 'xmm0',  'xmm1',  'xmm2',  'xmm3', 'xmm4', 'xmm5', 'xmm6',
    'xmm7', 'xmm8', 'xmm9', 'xmm10', 'xmm11', 'xmm12', 'xmm13', 'xmm14',
    'xmm15', 'st0', 'st1', 'st2', 'st3', 'st4', 'st5', 'st6',
    'st7', 'mm0', 'mm1', 'mm2', 'mm3', 'mm4', 'mm5', 'mm6',
    'mm7', 'rflags', 'es', 'cs', 'ss', 'ds', 'fs', 'gs',
    '<none>', '<none>', 'fs.base', 'gs.base', '<none>', '<none>', 'tr', 'ldtr',
    'mxcsr', 'fcw', 'fsw'
]


class ExprDumper(GenericExprVisitor):
    """ A concrete visitor for DWARF expressions that dumps a textual
        representation of the complete expression.

        Usage: after creation, call process_expr, and then get_str for a
        semicolon-delimited string representation of the decoded expression.
    """
    def __init__(self, structs):
        super(ExprDumper, self).__init__(structs)
        self._init_lookups()
        self._str_parts = []

    def clear(self):
        self._str_parts = []

    def get_str(self):
        return '; '.join(self._str_parts)

    def _init_lookups(self):
        self._ops_with_decimal_arg = set([
            'DW_OP_const1u', 'DW_OP_const1s', 'DW_OP_const2u', 'DW_OP_const2s',
            'DW_OP_const4u', 'DW_OP_const4s', 'DW_OP_constu', 'DW_OP_consts',
            'DW_OP_pick', 'DW_OP_plus_uconst', 'DW_OP_bra', 'DW_OP_skip',
            'DW_OP_fbreg', 'DW_OP_piece', 'DW_OP_deref_size',
            'DW_OP_xderef_size', 'DW_OP_regx',])

        for n in range(0, 32):
            self._ops_with_decimal_arg.add('DW_OP_breg%s' % n)

        self._ops_with_two_decimal_args = set([
            'DW_OP_const8u', 'DW_OP_const8s', 'DW_OP_bregx', 'DW_OP_bit_piece'])

        self._ops_with_hex_arg = set(
            ['DW_OP_addr', 'DW_OP_call2', 'DW_OP_call4', 'DW_OP_call_ref'])

    def _after_visit(self, opcode, opcode_name, args):
        self._str_parts.append(self._dump_to_string(opcode, opcode_name, args))

    def _dump_to_string(self, opcode, opcode_name, args):
        if len(args) == 0:
            if opcode_name.startswith('DW_OP_reg'):
                regnum = int(opcode_name[9:])
                return '%s (%s)' % (
                    opcode_name,
                    describe_reg_name(regnum, _MACHINE_ARCH))
            else:
                return opcode_name
        elif opcode_name in self._ops_with_decimal_arg:
            if opcode_name.startswith('DW_OP_breg'):
                regnum = int(opcode_name[10:])
                return '%s (%s): %s' % (
                    opcode_name,
                    describe_reg_name(regnum, _MACHINE_ARCH),
                    args[0])
            elif opcode_name.endswith('regx'):
                # applies to both regx and bregx
                return '%s: %s (%s)' % (
                    opcode_name,
                    args[0],
                    describe_reg_name(args[0], _MACHINE_ARCH))
            else:
                return '%s: %s' % (opcode_name, args[0])
        elif opcode_name in self._ops_with_hex_arg:
            return '%s: %x' % (opcode_name, args[0])
        elif opcode_name in self._ops_with_two_decimal_args:
            return '%s: %s %s' % (opcode_name, args[0], args[1])
        else:
            return '<unknown %s>' % opcode_name




########NEW FILE########
__FILENAME__ = die
#-------------------------------------------------------------------------------
# elftools: dwarf/die.py
#
# DWARF Debugging Information Entry
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
from collections import namedtuple
import os

from ..common.exceptions import DWARFError
from ..common.py3compat import OrderedDict, bytes2str, iteritems
from ..common.utils import struct_parse, preserve_stream_pos
from .enums import DW_FORM_raw2name


# AttributeValue - describes an attribute value in the DIE:
#
# name:
#   The name (DW_AT_*) of this attribute
#
# form:
#   The DW_FORM_* name of this attribute
#
# value:
#   The value parsed from the section and translated accordingly to the form
#   (e.g. for a DW_FORM_strp it's the actual string taken from the string table)
#
# raw_value:
#   Raw value as parsed from the section - used for debugging and presentation
#   (e.g. for a DW_FORM_strp it's the raw string offset into the table)
#
# offset:
#   Offset of this attribute's value in the stream (absolute offset, relative
#   the beginning of the whole stream)
#
AttributeValue = namedtuple(
    'AttributeValue', 'name form value raw_value offset')


class DIE(object):
    """ A DWARF debugging information entry. On creation, parses itself from
        the stream. Each DIE is held by a CU.

        Accessible attributes:

            tag:
                The DIE tag

            size:
                The size this DIE occupies in the section

            offset:
                The offset of this DIE in the stream

            attributes:
                An ordered dictionary mapping attribute names to values. It's
                ordered to preserve the order of attributes in the section

            has_children:
                Specifies whether this DIE has children

            abbrev_code:
                The abbreviation code pointing to an abbreviation entry (note
                that this is for informational pusposes only - this object
                interacts with its abbreviation table transparently).

        See also the public methods.
    """
    def __init__(self, cu, stream, offset):
        """ cu:
                CompileUnit object this DIE belongs to. Used to obtain context
                information (structs, abbrev table, etc.)

            stream, offset:
                The stream and offset into it where this DIE's data is located
        """
        self.cu = cu
        self.dwarfinfo = self.cu.dwarfinfo # get DWARFInfo context
        self.stream = stream
        self.offset = offset

        self.attributes = OrderedDict()
        self.tag = None
        self.has_children = None
        self.abbrev_code = None
        self.size = 0
        self._children = []
        self._parent = None

        self._parse_DIE()

    def is_null(self):
        """ Is this a null entry?
        """
        return self.tag is None

    def get_parent(self):
        """ The parent DIE of this DIE. None if the DIE has no parent (i.e. a
            top-level DIE).
        """
        return self._parent

    def get_full_path(self):
        """ Return the full path filename for the DIE.

            The filename is the join of 'DW_AT_comp_dir' and 'DW_AT_name',
            either of which may be missing in practice. Note that its value is
            usually a string taken from the .debug_string section and the
            returned value will be a string.
        """
        comp_dir_attr = self.attributes.get('DW_AT_comp_dir', None)
        comp_dir = bytes2str(comp_dir_attr.value) if comp_dir_attr else ''
        fname_attr = self.attributes.get('DW_AT_name', None)
        fname = bytes2str(fname_attr.value) if fname_attr else ''
        return os.path.join(comp_dir, fname)

    def iter_children(self):
        """ Yield all children of this DIE
        """
        return iter(self._children)

    def iter_siblings(self):
        """ Yield all siblings of this DIE
        """
        if self._parent:
            for sibling in self._parent.iter_children():
                if sibling is not self:
                    yield sibling
        else:
            raise StopIteration()

    # The following methods are used while creating the DIE and should not be
    # interesting to consumers
    #
    def add_child(self, die):
        self._children.append(die)

    def set_parent(self, die):
        self._parent = die

    #------ PRIVATE ------#

    def __repr__(self):
        s = 'DIE %s, size=%s, has_chidren=%s\n' % (
            self.tag, self.size, self.has_children)
        for attrname, attrval in iteritems(self.attributes):
            s += '    |%-18s:  %s\n' % (attrname, attrval)
        return s

    def __str__(self):
        return self.__repr__()

    def _parse_DIE(self):
        """ Parses the DIE info from the section, based on the abbreviation
            table of the CU
        """
        structs = self.cu.structs

        # A DIE begins with the abbreviation code. Read it and use it to
        # obtain the abbrev declaration for this DIE.
        # Note: here and elsewhere, preserve_stream_pos is used on operations
        # that manipulate the stream by reading data from it.
        #
        self.abbrev_code = struct_parse(
            structs.Dwarf_uleb128(''), self.stream, self.offset)

        # This may be a null entry
        if self.abbrev_code == 0:
            self.size = self.stream.tell() - self.offset
            return

        with preserve_stream_pos(self.stream):
            abbrev_decl = self.cu.get_abbrev_table().get_abbrev(
                self.abbrev_code)
        self.tag = abbrev_decl['tag']
        self.has_children = abbrev_decl.has_children()

        # Guided by the attributes listed in the abbreviation declaration, parse
        # values from the stream.
        #
        for name, form in abbrev_decl.iter_attr_specs():
            attr_offset = self.stream.tell()
            raw_value = struct_parse(structs.Dwarf_dw_form[form], self.stream)

            value = self._translate_attr_value(form, raw_value)
            self.attributes[name] = AttributeValue(
                name=name,
                form=form,
                value=value,
                raw_value=raw_value,
                offset=attr_offset)

        self.size = self.stream.tell() - self.offset

    def _translate_attr_value(self, form, raw_value):
        """ Translate a raw attr value according to the form
        """
        value = None
        if form == 'DW_FORM_strp':
            with preserve_stream_pos(self.stream):
                value = self.dwarfinfo.get_string_from_table(raw_value)
        elif form == 'DW_FORM_flag':
            value = not raw_value == 0
        elif form == 'DW_FORM_indirect':
            try:
                form = DW_FORM_raw2name[raw_value]
            except KeyError as err:
                raise DWARFError(
                        'Found DW_FORM_indirect with unknown raw_value=' +
                        str(raw_value))

            raw_value = struct_parse(
                self.cu.structs.Dwarf_dw_form[form], self.stream)
            # Let's hope this doesn't get too deep :-)
            return self._translate_attr_value(form, raw_value)
        else:
            value = raw_value
        return value

########NEW FILE########
__FILENAME__ = dwarfinfo
#-------------------------------------------------------------------------------
# elftools: dwarf/dwarfinfo.py
#
# DWARFInfo - Main class for accessing DWARF debug information
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
from collections import namedtuple

from ..common.exceptions import DWARFError
from ..common.utils import (struct_parse, dwarf_assert,
                            parse_cstring_from_stream)
from .structs import DWARFStructs
from .compileunit import CompileUnit
from .abbrevtable import AbbrevTable
from .lineprogram import LineProgram
from .callframe import CallFrameInfo
from .locationlists import LocationLists
from .ranges import RangeLists


# Describes a debug section
#
# stream: a stream object containing the data of this section
# name: section name in the container file
# global_offset: the global offset of the section in its container file
# size: the size of the section's data, in bytes
#
# 'name' and 'global_offset' are for descriptional purposes only and
# aren't strictly required for the DWARF parsing to work.
#
DebugSectionDescriptor = namedtuple('DebugSectionDescriptor',
    'stream name global_offset size')


# Some configuration parameters for the DWARF reader. This exists to allow
# DWARFInfo to be independent from any specific file format/container.
#
# little_endian:
#   boolean flag specifying whether the data in the file is little endian
#
# machine_arch:
#   Machine architecture as a string. For example 'x86' or 'x64'
#
# default_address_size:
#   The default address size for the container file (sizeof pointer, in bytes)
#
DwarfConfig = namedtuple('DwarfConfig',
    'little_endian machine_arch default_address_size')


class DWARFInfo(object):
    """ Acts also as a "context" to other major objects, bridging between
        various parts of the debug infromation.
    """
    def __init__(self,
            config,
            debug_info_sec,
            debug_abbrev_sec,
            debug_frame_sec,
            eh_frame_sec,
            debug_str_sec,
            debug_loc_sec,
            debug_ranges_sec,
            debug_line_sec):
        """ config:
                A DwarfConfig object

            debug_*_sec:
                DebugSectionDescriptor for a section. Pass None for sections
                that don't exist. These arguments are best given with
                keyword syntax.
        """
        self.config = config
        self.debug_info_sec = debug_info_sec
        self.debug_abbrev_sec = debug_abbrev_sec
        self.debug_frame_sec = debug_frame_sec
        self.eh_frame_sec = eh_frame_sec
        self.debug_str_sec = debug_str_sec
        self.debug_loc_sec = debug_loc_sec
        self.debug_ranges_sec = debug_ranges_sec
        self.debug_line_sec = debug_line_sec

        # This is the DWARFStructs the context uses, so it doesn't depend on
        # DWARF format and address_size (these are determined per CU) - set them
        # to default values.
        self.structs = DWARFStructs(
            little_endian=self.config.little_endian,
            dwarf_format=32,
            address_size=self.config.default_address_size)

        # Cache for abbrev tables: a dict keyed by offset
        self._abbrevtable_cache = {}

    def iter_CUs(self):
        """ Yield all the compile units (CompileUnit objects) in the debug info
        """
        return self._parse_CUs_iter()

    def get_abbrev_table(self, offset):
        """ Get an AbbrevTable from the given offset in the debug_abbrev
            section.

            The only verification done on the offset is that it's within the
            bounds of the section (if not, an exception is raised).
            It is the caller's responsibility to make sure the offset actually
            points to a valid abbreviation table.

            AbbrevTable objects are cached internally (two calls for the same
            offset will return the same object).
        """
        dwarf_assert(
            offset < self.debug_abbrev_sec.size,
            "Offset '0x%x' to abbrev table out of section bounds" % offset)
        if offset not in self._abbrevtable_cache:
            self._abbrevtable_cache[offset] = AbbrevTable(
                structs=self.structs,
                stream=self.debug_abbrev_sec.stream,
                offset=offset)
        return self._abbrevtable_cache[offset]

    def get_string_from_table(self, offset):
        """ Obtain a string from the string table section, given an offset
            relative to the section.
        """
        return parse_cstring_from_stream(self.debug_str_sec.stream, offset)

    def line_program_for_CU(self, CU):
        """ Given a CU object, fetch the line program it points to from the
            .debug_line section.
            If the CU doesn't point to a line program, return None.
        """
        # The line program is pointed to by the DW_AT_stmt_list attribute of
        # the top DIE of a CU.
        top_DIE = CU.get_top_DIE()
        if 'DW_AT_stmt_list' in top_DIE.attributes:
            return self._parse_line_program_at_offset(
                    top_DIE.attributes['DW_AT_stmt_list'].value, CU.structs)
        else:
            return None

    def has_CFI(self):
        """ Does this dwarf info have a dwarf_frame CFI section?
        """
        return self.debug_frame_sec is not None

    def CFI_entries(self):
        """ Get a list of dwarf_frame CFI entries from the .debug_frame section.
        """
        cfi = CallFrameInfo(
            stream=self.debug_frame_sec.stream,
            size=self.debug_frame_sec.size,
            base_structs=self.structs)
        return cfi.get_entries()

    def has_EH_CFI(self):
        """ Does this dwarf info have a eh_frame CFI section?
        """
        return self.eh_frame_sec is not None

    def EH_CFI_entries(self):
        """ Get a list of eh_frame CFI entries from the .eh_frame section.
        """
        cfi = CallFrameInfo(
            stream=self.eh_frame_sec.stream,
            size=self.eh_frame_sec.size,
            base_structs=self.structs)
        return cfi.get_entries()

    def location_lists(self):
        """ Get a LocationLists object representing the .debug_loc section of
            the DWARF data, or None if this section doesn't exist.
        """
        if self.debug_loc_sec:
            return LocationLists(self.debug_loc_sec.stream, self.structs)
        else:
            return None

    def range_lists(self):
        """ Get a RangeLists object representing the .debug_ranges section of
            the DWARF data, or None if this section doesn't exist.
        """
        if self.debug_ranges_sec:
            return RangeLists(self.debug_ranges_sec.stream, self.structs)
        else:
            return None

    #------ PRIVATE ------#

    def _parse_CUs_iter(self):
        """ Parse CU entries from debug_info. Yield CUs in order of appearance.
        """
        offset = 0
        while offset < self.debug_info_sec.size:
            cu = self._parse_CU_at_offset(offset)
            # Compute the offset of the next CU in the section. The unit_length
            # field of the CU header contains its size not including the length
            # field itself.
            offset = (  offset +
                        cu['unit_length'] +
                        cu.structs.initial_length_field_size())
            yield cu

    def _parse_CU_at_offset(self, offset):
        """ Parse and return a CU at the given offset in the debug_info stream.
        """
        # Section 7.4 (32-bit and 64-bit DWARF Formats) of the DWARF spec v3
        # states that the first 32-bit word of the CU header determines
        # whether the CU is represented with 32-bit or 64-bit DWARF format.
        #
        # So we peek at the first word in the CU header to determine its
        # dwarf format. Based on it, we then create a new DWARFStructs
        # instance suitable for this CU and use it to parse the rest.
        #
        initial_length = struct_parse(
            self.structs.Dwarf_uint32(''), self.debug_info_sec.stream, offset)
        dwarf_format = 64 if initial_length == 0xFFFFFFFF else 32

        # At this point we still haven't read the whole header, so we don't
        # know the address_size. Therefore, we're going to create structs
        # with a default address_size=4. If, after parsing the header, we
        # find out address_size is actually 8, we just create a new structs
        # object for this CU.
        #
        cu_structs = DWARFStructs(
            little_endian=self.config.little_endian,
            dwarf_format=dwarf_format,
            address_size=4)

        cu_header = struct_parse(
            cu_structs.Dwarf_CU_header, self.debug_info_sec.stream, offset)
        if cu_header['address_size'] == 8:
            cu_structs = DWARFStructs(
                little_endian=self.config.little_endian,
                dwarf_format=dwarf_format,
                address_size=8)

        cu_die_offset = self.debug_info_sec.stream.tell()
        dwarf_assert(
            self._is_supported_version(cu_header['version']),
            "Expected supported DWARF version. Got '%s'" % cu_header['version'])
        return CompileUnit(
                header=cu_header,
                dwarfinfo=self,
                structs=cu_structs,
                cu_offset=offset,
                cu_die_offset=cu_die_offset)

    def _is_supported_version(self, version):
        """ DWARF version supported by this parser
        """
        return 2 <= version <= 4

    def _parse_line_program_at_offset(self, debug_line_offset, structs):
        """ Given an offset to the .debug_line section, parse the line program
            starting at this offset in the section and return it.
            structs is the DWARFStructs object used to do this parsing.
        """
        lineprog_header = struct_parse(
            structs.Dwarf_lineprog_header,
            self.debug_line_sec.stream,
            debug_line_offset)

        # Calculate the offset to the next line program (see DWARF 6.2.4)
        end_offset = (  debug_line_offset + lineprog_header['unit_length'] +
                        structs.initial_length_field_size())

        return LineProgram(
            header=lineprog_header,
            stream=self.debug_line_sec.stream,
            structs=structs,
            program_start_offset=self.debug_line_sec.stream.tell(),
            program_end_offset=end_offset)


########NEW FILE########
__FILENAME__ = dwarf_expr
#-------------------------------------------------------------------------------
# elftools: dwarf/dwarf_expr.py
#
# Decoding DWARF expressions
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
from ..common.py3compat import BytesIO, iteritems
from ..common.utils import struct_parse, bytelist2string


# DWARF expression opcodes. name -> opcode mapping
DW_OP_name2opcode = dict(
    DW_OP_addr=0x03,
    DW_OP_deref=0x06,
    DW_OP_const1u=0x08,
    DW_OP_const1s=0x09,
    DW_OP_const2u=0x0a,
    DW_OP_const2s=0x0b,
    DW_OP_const4u=0x0c,
    DW_OP_const4s=0x0d,
    DW_OP_const8u=0x0e,
    DW_OP_const8s=0x0f,
    DW_OP_constu=0x10,
    DW_OP_consts=0x11,
    DW_OP_dup=0x12,
    DW_OP_drop=0x13,
    DW_OP_over=0x14,
    DW_OP_pick=0x15,
    DW_OP_swap=0x16,
    DW_OP_rot=0x17,
    DW_OP_xderef=0x18,
    DW_OP_abs=0x19,
    DW_OP_and=0x1a,
    DW_OP_div=0x1b,
    DW_OP_minus=0x1c,
    DW_OP_mod=0x1d,
    DW_OP_mul=0x1e,
    DW_OP_neg=0x1f,
    DW_OP_not=0x20,
    DW_OP_or=0x21,
    DW_OP_plus=0x22,
    DW_OP_plus_uconst=0x23,
    DW_OP_shl=0x24,
    DW_OP_shr=0x25,
    DW_OP_shra=0x26,
    DW_OP_xor=0x27,
    DW_OP_bra=0x28,
    DW_OP_eq=0x29,
    DW_OP_ge=0x2a,
    DW_OP_gt=0x2b,
    DW_OP_le=0x2c,
    DW_OP_lt=0x2d,
    DW_OP_ne=0x2e,
    DW_OP_skip=0x2f,
    DW_OP_regx=0x90,
    DW_OP_fbreg=0x91,
    DW_OP_bregx=0x92,
    DW_OP_piece=0x93,
    DW_OP_deref_size=0x94,
    DW_OP_xderef_size=0x95,
    DW_OP_nop=0x96,
    DW_OP_push_object_address=0x97,
    DW_OP_call2=0x98,
    DW_OP_call4=0x99,
    DW_OP_call_ref=0x9a,
    DW_OP_form_tls_address=0x9b,
    DW_OP_call_frame_cfa=0x9c,
    DW_OP_bit_piece=0x9d,
)

def _generate_dynamic_values(map, prefix, index_start, index_end, value_start):
    """ Generate values in a map (dict) dynamically. Each key starts with
        a (string) prefix, followed by an index in the inclusive range
        [index_start, index_end]. The values start at value_start.
    """
    for index in range(index_start, index_end + 1):
        name = '%s%s' % (prefix, index)
        value = value_start + index - index_start
        map[name] = value

_generate_dynamic_values(DW_OP_name2opcode, 'DW_OP_lit', 0, 31, 0x30)
_generate_dynamic_values(DW_OP_name2opcode, 'DW_OP_reg', 0, 31, 0x50)
_generate_dynamic_values(DW_OP_name2opcode, 'DW_OP_breg', 0, 31, 0x70)

# opcode -> name mapping
DW_OP_opcode2name = dict((v, k) for k, v in iteritems(DW_OP_name2opcode))


class GenericExprVisitor(object):
    """ A DWARF expression is a sequence of instructions encoded in a block
        of bytes. This class decodes the sequence into discrete instructions
        with their arguments and allows generic "visiting" to process them.

        Usage: subclass this class, and override the needed methods. The
        easiest way would be to just override _after_visit, which gets passed
        each decoded instruction (with its arguments) in order. Clients of
        the visitor then just execute process_expr. The subclass can keep
        its own internal information updated in _after_visit and provide
        methods to extract it. For a good example of this usage, see the
        ExprDumper class in the descriptions module.

        A more complex usage could be to override visiting methods for
        specific instructions, by placing them into the dispatch table.
    """
    def __init__(self, structs):
        self.structs = structs
        self._init_dispatch_table()
        self.stream = None
        self._cur_opcode = None
        self._cur_opcode_name = None
        self._cur_args = []

    def process_expr(self, expr):
        """ Process (visit) a DWARF expression. expr should be a list of
            (integer) byte values.
        """
        self.stream = BytesIO(bytelist2string(expr))

        while True:
            # Get the next opcode from the stream. If nothing is left in the
            # stream, we're done.
            byte = self.stream.read(1)
            if len(byte) == 0:
                break

            # Decode the opcode and its name
            self._cur_opcode = ord(byte)
            self._cur_opcode_name = DW_OP_opcode2name.get(
                self._cur_opcode, 'OP:0x%x' % self._cur_opcode)
            # Will be filled in by visitors
            self._cur_args = [] 

            # Dispatch to a visitor function
            visitor = self._dispatch_table.get(
                    self._cur_opcode,
                    self._default_visitor)
            visitor(self._cur_opcode, self._cur_opcode_name)

            # Finally call the post-visit function
            self._after_visit(
                    self._cur_opcode, self._cur_opcode_name, self._cur_args)

    def _after_visit(self, opcode, opcode_name, args):
        pass
        
    def _default_visitor(self, opcode, opcode_name):
        pass
        
    def _visit_OP_with_no_args(self, opcode, opcode_name):
        self._cur_args = []

    def _visit_OP_addr(self, opcode, opcode_name):
        self._cur_args = [
                struct_parse(self.structs.Dwarf_target_addr(''), self.stream)]

    def _make_visitor_arg_struct(self, struct_arg):
        """ Create a visitor method for an opcode that that accepts a single
            argument, specified by a struct.
        """
        def visitor(opcode, opcode_name):
            self._cur_args = [struct_parse(struct_arg, self.stream)]
        return visitor

    def _make_visitor_arg_struct2(self, struct_arg1, struct_arg2):
        """ Create a visitor method for an opcode that that accepts two
            arguments, specified by structs.
        """
        def visitor(opcode, opcode_name):
            self._cur_args = [
                struct_parse(struct_arg1, self.stream),
                struct_parse(struct_arg2, self.stream)]
        return visitor

    def _init_dispatch_table(self):
        self._dispatch_table = {}
        def add(opcode_name, func):
            self._dispatch_table[DW_OP_name2opcode[opcode_name]] = func
            
        add('DW_OP_addr', self._visit_OP_addr)
        add('DW_OP_const1u', 
            self._make_visitor_arg_struct(self.structs.Dwarf_uint8('')))
        add('DW_OP_const1s', 
            self._make_visitor_arg_struct(self.structs.Dwarf_int8('')))
        add('DW_OP_const2u', 
            self._make_visitor_arg_struct(self.structs.Dwarf_uint16('')))
        add('DW_OP_const2s', 
            self._make_visitor_arg_struct(self.structs.Dwarf_int16('')))
        add('DW_OP_const4u', 
            self._make_visitor_arg_struct(self.structs.Dwarf_uint32('')))
        add('DW_OP_const4s', 
            self._make_visitor_arg_struct(self.structs.Dwarf_int32('')))
        add('DW_OP_const8u', 
            self._make_visitor_arg_struct2(
                self.structs.Dwarf_uint32(''),
                self.structs.Dwarf_uint32('')))
        add('DW_OP_const8s', 
            self._make_visitor_arg_struct2(
                self.structs.Dwarf_int32(''),
                self.structs.Dwarf_int32('')))
        add('DW_OP_constu',
            self._make_visitor_arg_struct(self.structs.Dwarf_uleb128('')))
        add('DW_OP_consts',
            self._make_visitor_arg_struct(self.structs.Dwarf_sleb128('')))
        add('DW_OP_pick',
            self._make_visitor_arg_struct(self.structs.Dwarf_uint8('')))
        add('DW_OP_plus_uconst',
            self._make_visitor_arg_struct(self.structs.Dwarf_uleb128('')))
        add('DW_OP_bra', 
            self._make_visitor_arg_struct(self.structs.Dwarf_int16('')))
        add('DW_OP_skip', 
            self._make_visitor_arg_struct(self.structs.Dwarf_int16('')))

        for opname in [ 'DW_OP_deref', 'DW_OP_dup', 'DW_OP_drop', 'DW_OP_over',
                        'DW_OP_swap', 'DW_OP_swap', 'DW_OP_rot', 'DW_OP_xderef',
                        'DW_OP_abs', 'DW_OP_and', 'DW_OP_div', 'DW_OP_minus',
                        'DW_OP_mod', 'DW_OP_mul', 'DW_OP_neg', 'DW_OP_not',
                        'DW_OP_plus', 'DW_OP_shl', 'DW_OP_shr', 'DW_OP_shra',
                        'DW_OP_xor', 'DW_OP_eq', 'DW_OP_ge', 'DW_OP_gt',
                        'DW_OP_le', 'DW_OP_lt', 'DW_OP_ne', 'DW_OP_nop',
                        'DW_OP_push_object_address', 'DW_OP_form_tls_address',
                        'DW_OP_call_frame_cfa']:
            add(opname, self._visit_OP_with_no_args)

        for n in range(0, 32):
            add('DW_OP_lit%s' % n, self._visit_OP_with_no_args)
            add('DW_OP_reg%s' % n, self._visit_OP_with_no_args)
            add('DW_OP_breg%s' % n, 
                self._make_visitor_arg_struct(self.structs.Dwarf_sleb128('')))

        add('DW_OP_fbreg',
            self._make_visitor_arg_struct(self.structs.Dwarf_sleb128('')))
        add('DW_OP_regx',
            self._make_visitor_arg_struct(self.structs.Dwarf_uleb128('')))
        add('DW_OP_bregx',
            self._make_visitor_arg_struct2(
                self.structs.Dwarf_uleb128(''),
                self.structs.Dwarf_sleb128('')))
        add('DW_OP_piece',
            self._make_visitor_arg_struct(self.structs.Dwarf_uleb128('')))
        add('DW_OP_bit_piece',
            self._make_visitor_arg_struct2(
                self.structs.Dwarf_uleb128(''),
                self.structs.Dwarf_uleb128('')))
        add('DW_OP_deref_size',
            self._make_visitor_arg_struct(self.structs.Dwarf_int8('')))
        add('DW_OP_xderef_size',
            self._make_visitor_arg_struct(self.structs.Dwarf_int8('')))
        add('DW_OP_call2',
            self._make_visitor_arg_struct(self.structs.Dwarf_uint16('')))
        add('DW_OP_call4',
            self._make_visitor_arg_struct(self.structs.Dwarf_uint32('')))
        add('DW_OP_call_ref',
            self._make_visitor_arg_struct(self.structs.Dwarf_offset('')))



########NEW FILE########
__FILENAME__ = enums
#-------------------------------------------------------------------------------
# elftools: dwarf/enums.py
#
# Mappings of enum names to values
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
from ..construct import Pass
from ..common.py3compat import iteritems


ENUM_DW_TAG = dict(
    DW_TAG_null                     = 0x00,
    DW_TAG_array_type               = 0x01,
    DW_TAG_class_type               = 0x02,
    DW_TAG_entry_point              = 0x03,
    DW_TAG_enumeration_type         = 0x04,
    DW_TAG_formal_parameter         = 0x05,
    DW_TAG_imported_declaration     = 0x08,
    DW_TAG_label                    = 0x0a,
    DW_TAG_lexical_block            = 0x0b,
    DW_TAG_member                   = 0x0d,
    DW_TAG_pointer_type             = 0x0f,
    DW_TAG_reference_type           = 0x10,
    DW_TAG_compile_unit             = 0x11,
    DW_TAG_string_type              = 0x12,
    DW_TAG_structure_type           = 0x13,
    DW_TAG_subroutine_type          = 0x15,
    DW_TAG_typedef                  = 0x16,
    DW_TAG_union_type               = 0x17,
    DW_TAG_unspecified_parameters   = 0x18,
    DW_TAG_variant                  = 0x19,
    DW_TAG_common_block             = 0x1a,
    DW_TAG_common_inclusion         = 0x1b,
    DW_TAG_inheritance              = 0x1c,
    DW_TAG_inlined_subroutine       = 0x1d,
    DW_TAG_module                   = 0x1e,
    DW_TAG_ptr_to_member_type       = 0x1f,
    DW_TAG_set_type                 = 0x20,
    DW_TAG_subrange_type            = 0x21,
    DW_TAG_with_stmt                = 0x22,
    DW_TAG_access_declaration       = 0x23,
    DW_TAG_base_type                = 0x24,
    DW_TAG_catch_block              = 0x25,
    DW_TAG_const_type               = 0x26,
    DW_TAG_constant                 = 0x27,
    DW_TAG_enumerator               = 0x28,
    DW_TAG_file_type                = 0x29,
    DW_TAG_friend                   = 0x2a,
    DW_TAG_namelist                 = 0x2b,
    DW_TAG_namelist_item            = 0x2c,
    DW_TAG_namelist_items           = 0x2c,
    DW_TAG_packed_type              = 0x2d,
    DW_TAG_subprogram               = 0x2e,

    # The DWARF standard defines these as _parameter, not _param, but we
    # maintain compatibility with readelf.
    DW_TAG_template_type_param      = 0x2f,
    DW_TAG_template_value_param     = 0x30,

    DW_TAG_thrown_type              = 0x31,
    DW_TAG_try_block                = 0x32,
    DW_TAG_variant_part             = 0x33,
    DW_TAG_variable                 = 0x34,
    DW_TAG_volatile_type            = 0x35,
    DW_TAG_dwarf_procedure          = 0x36,
    DW_TAG_restrict_type            = 0x37,
    DW_TAG_interface_type           = 0x38,
    DW_TAG_namespace                = 0x39,
    DW_TAG_imported_module          = 0x3a,
    DW_TAG_unspecified_type         = 0x3b,
    DW_TAG_partial_unit             = 0x3c,
    DW_TAG_imported_unit            = 0x3d,
    DW_TAG_mutable_type             = 0x3e,
    DW_TAG_condition                = 0x3f,
    DW_TAG_shared_type              = 0x40,
    DW_TAG_type_unit                = 0x41,
    DW_TAG_rvalue_reference_type    = 0x42,

    DW_TAG_lo_user                  = 0x4080,
    DW_TAG_hi_user                  = 0xffff,

    _default_                       = Pass,
)


ENUM_DW_CHILDREN = dict(
    DW_CHILDREN_no  = 0x00,
    DW_CHILDREN_yes = 0x01,
)


ENUM_DW_AT = dict(
    DW_AT_null                  = 0x00,
    DW_AT_sibling               = 0x01,
    DW_AT_location              = 0x02,
    DW_AT_name                  = 0x03,
    DW_AT_ordering              = 0x09,
    DW_AT_subscr_data           = 0x0a,
    DW_AT_byte_size             = 0x0b,
    DW_AT_bit_offset            = 0x0c,
    DW_AT_bit_size              = 0x0d,
    DW_AT_element_list          = 0x0f,
    DW_AT_stmt_list             = 0x10,
    DW_AT_low_pc                = 0x11,
    DW_AT_high_pc               = 0x12,
    DW_AT_language              = 0x13,
    DW_AT_member                = 0x14,
    DW_AT_discr                 = 0x15,
    DW_AT_discr_value           = 0x16,
    DW_AT_visibility            = 0x17,
    DW_AT_import                = 0x18,
    DW_AT_string_length         = 0x19,
    DW_AT_common_reference      = 0x1a,
    DW_AT_comp_dir              = 0x1b,
    DW_AT_const_value           = 0x1c,
    DW_AT_containing_type       = 0x1d,
    DW_AT_default_value         = 0x1e,
    DW_AT_inline                = 0x20,
    DW_AT_is_optional           = 0x21,
    DW_AT_lower_bound           = 0x22,
    DW_AT_producer              = 0x25,
    DW_AT_prototyped            = 0x27,
    DW_AT_return_addr           = 0x2a,
    DW_AT_start_scope           = 0x2c,
    DW_AT_bit_stride            = 0x2e,
    DW_AT_stride_size           = 0x2e,
    DW_AT_upper_bound           = 0x2f,
    DW_AT_abstract_origin       = 0x31,
    DW_AT_accessibility         = 0x32,
    DW_AT_address_class         = 0x33,
    DW_AT_artificial            = 0x34,
    DW_AT_base_types            = 0x35,
    DW_AT_calling_convention    = 0x36,
    DW_AT_count                 = 0x37,
    DW_AT_data_member_location  = 0x38,
    DW_AT_decl_column           = 0x39,
    DW_AT_decl_file             = 0x3a,
    DW_AT_decl_line             = 0x3b,
    DW_AT_declaration           = 0x3c,
    DW_AT_discr_list            = 0x3d,
    DW_AT_encoding              = 0x3e,
    DW_AT_external              = 0x3f,
    DW_AT_frame_base            = 0x40,
    DW_AT_friend                = 0x41,
    DW_AT_identifier_case       = 0x42,
    DW_AT_macro_info            = 0x43,
    DW_AT_namelist_item         = 0x44,
    DW_AT_priority              = 0x45,
    DW_AT_segment               = 0x46,
    DW_AT_specification         = 0x47,
    DW_AT_static_link           = 0x48,
    DW_AT_type                  = 0x49,
    DW_AT_use_location          = 0x4a,
    DW_AT_variable_parameter    = 0x4b,
    DW_AT_virtuality            = 0x4c,
    DW_AT_vtable_elem_location  = 0x4d,
    DW_AT_allocated             = 0x4e,
    DW_AT_associated            = 0x4f,
    DW_AT_data_location         = 0x50,
    DW_AT_byte_stride           = 0x51,
    DW_AT_stride                = 0x51,
    DW_AT_entry_pc              = 0x52,
    DW_AT_use_UTF8              = 0x53,
    DW_AT_extension             = 0x54,
    DW_AT_ranges                = 0x55,
    DW_AT_trampoline            = 0x56,
    DW_AT_call_column           = 0x57,
    DW_AT_call_file             = 0x58,
    DW_AT_call_line             = 0x59,
    DW_AT_description           = 0x5a,
    DW_AT_binary_scale          = 0x5b,
    DW_AT_decimal_scale         = 0x5c,
    DW_AT_small                 = 0x5d,
    DW_AT_decimal_sign          = 0x5e,
    DW_AT_digit_count           = 0x5f,
    DW_AT_picture_string        = 0x60,
    DW_AT_mutable               = 0x61,
    DW_AT_threads_scaled        = 0x62,
    DW_AT_explicit              = 0x63,
    DW_AT_object_pointer        = 0x64,
    DW_AT_endianity             = 0x65,
    DW_AT_elemental             = 0x66,
    DW_AT_pure                  = 0x67,
    DW_AT_recursive             = 0x68,
    DW_AT_signature             = 0x69,
    DW_AT_main_subprogram       = 0x6a,
    DW_AT_data_bit_offset       = 0x6b,
    DW_AT_const_expr            = 0x6c,
    DW_AT_enum_class            = 0x6d,
    DW_AT_linkage_name          = 0x6e,

    DW_AT_MIPS_fde                      = 0x2001,
    DW_AT_MIPS_loop_begin               = 0x2002,
    DW_AT_MIPS_tail_loop_begin          = 0x2003,
    DW_AT_MIPS_epilog_begin             = 0x2004,
    DW_AT_MIPS_loop_unroll_factor       = 0x2005,
    DW_AT_MIPS_software_pipeline_depth  = 0x2006,
    DW_AT_MIPS_linkage_name             = 0x2007,
    DW_AT_MIPS_stride                   = 0x2008,
    DW_AT_MIPS_abstract_name            = 0x2009,
    DW_AT_MIPS_clone_origin             = 0x200a,
    DW_AT_MIPS_has_inlines              = 0x200b,
    DW_AT_MIPS_stride_byte              = 0x200c,
    DW_AT_MIPS_stride_elem              = 0x200d,
    DW_AT_MIPS_ptr_dopetype             = 0x200e,
    DW_AT_MIPS_allocatable_dopetype     = 0x200f,
    DW_AT_MIPS_assumed_shape_dopetype   = 0x2010,
    DW_AT_MIPS_assumed_size             = 0x2011,

    DW_AT_sf_names                      = 0x2101,
    DW_AT_src_info                      = 0x2102,
    DW_AT_mac_info                      = 0x2103,
    DW_AT_src_coords                    = 0x2104,
    DW_AT_body_begin                    = 0x2105,
    DW_AT_body_end                      = 0x2106,
    DW_AT_GNU_vector                    = 0x2107,
    DW_AT_GNU_template_name             = 0x2110,

    DW_AT_GNU_call_site_value               = 0x2111,
    DW_AT_GNU_call_site_data_value          = 0x2112,
    DW_AT_GNU_call_site_target              = 0x2113,
    DW_AT_GNU_call_site_target_clobbered    = 0x2114,
    DW_AT_GNU_tail_call                     = 0x2115,
    DW_AT_GNU_all_tail_call_sites           = 0x2116,
    DW_AT_GNU_all_call_sites                = 0x2117,
    DW_AT_GNU_all_source_call_sites         = 0x2118,

    DW_AT_APPLE_optimized               = 0x3fe1,
    DW_AT_APPLE_flags                   = 0x3fe2,
    DW_AT_APPLE_isa                     = 0x3fe3,
    DW_AT_APPLE_block                   = 0x3fe4,
    DW_AT_APPLE_major_runtime_vers      = 0x3fe5,
    DW_AT_APPLE_runtime_class           = 0x3fe6,
    DW_AT_APPLE_omit_frame_ptr          = 0x3fe7,
    DW_AT_APPLE_property_name           = 0x3fe8,
    DW_AT_APPLE_property_getter         = 0x3fe9,
    DW_AT_APPLE_property_setter         = 0x3fea,
    DW_AT_APPLE_property_attribute      = 0x3feb,
    DW_AT_APPLE_objc_complete_type      = 0x3fec,
    DW_AT_APPLE_property                = 0x3fed,

    _default_ = Pass,
)


ENUM_DW_FORM = dict(
    DW_FORM_null            = 0x00,
    DW_FORM_addr            = 0x01,
    DW_FORM_block2          = 0x03,
    DW_FORM_block4          = 0x04,
    DW_FORM_data2           = 0x05,
    DW_FORM_data4           = 0x06,
    DW_FORM_data8           = 0x07,
    DW_FORM_string          = 0x08,
    DW_FORM_block           = 0x09,
    DW_FORM_block1          = 0x0a,
    DW_FORM_data1           = 0x0b,
    DW_FORM_flag            = 0x0c,
    DW_FORM_sdata           = 0x0d,
    DW_FORM_strp            = 0x0e,
    DW_FORM_udata           = 0x0f,
    DW_FORM_ref_addr        = 0x10,
    DW_FORM_ref1            = 0x11,
    DW_FORM_ref2            = 0x12,
    DW_FORM_ref4            = 0x13,
    DW_FORM_ref8            = 0x14,
    DW_FORM_ref_udata       = 0x15,
    DW_FORM_indirect        = 0x16,
    DW_FORM_sec_offset      = 0x17,
    DW_FORM_exprloc         = 0x18,
    DW_FORM_flag_present    = 0x19,
    DW_FORM_ref_sig8        = 0x20,

    DW_FORM_GNU_strp_alt    = 0x1f21,
    DW_FORM_GNU_ref_alt     = 0x1f20,
    _default_               = Pass,
)

# Inverse mapping for ENUM_DW_FORM
DW_FORM_raw2name = dict((v, k) for k, v in iteritems(ENUM_DW_FORM))


########NEW FILE########
__FILENAME__ = lineprogram
#-------------------------------------------------------------------------------
# elftools: dwarf/lineprogram.py
#
# DWARF line number program
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
import os
import copy
from collections import namedtuple

from ..common.utils import struct_parse
from .constants import *


# LineProgramEntry - an entry in the line program.
# A line program is a sequence of encoded entries. Some of these entries add a
# new LineState (mapping between line and address), and some don't.
#
# command:
#   The command/opcode - always numeric. For standard commands - it's the opcode
#   that can be matched with one of the DW_LNS_* constants. For extended commands
#   it's the extended opcode that can be matched with one of the DW_LNE_*
#   constants. For special commands, it's the opcode itself.
#
# args:
#   A list of decoded arguments of the command.
#
# is_extended:
#   Since extended commands are encoded by a zero followed by an extended
#   opcode, and these extended opcodes overlap with other opcodes, this
#   flag is needed to mark that the command has an extended opcode.
#
# state:
#   For commands that add a new state, it's the relevant LineState object.
#   For commands that don't add a new state, it's None.
#
LineProgramEntry = namedtuple(
    'LineProgramEntry', 'command is_extended args state')


class LineState(object):
    """ Represents a line program state (or a "row" in the matrix
        describing debug location information for addresses).
        The instance variables of this class are the "state machine registers"
        described in section 6.2.2 of DWARFv3
    """
    def __init__(self, default_is_stmt):
        self.address = 0
        self.file = 1
        self.line = 1
        self.column = 0
        self.is_stmt = default_is_stmt
        self.basic_block = False
        self.end_sequence = False
        self.prologue_end = False
        self.epilogue_begin = False
        self.isa = 0

    def __repr__(self):
        a = ['<LineState %x:' % id(self)]
        a.append('  address = 0x%x' % self.address)
        for attr in ('file', 'line', 'column', 'is_stmt', 'basic_block',
                     'end_sequence', 'prologue_end', 'epilogue_begin', 'isa'):
            a.append('  %s = %s' % (attr, getattr(self, attr)))
        return '\n'.join(a) + '>\n'


class LineProgram(object):
    """ Builds a "line table", which is essentially the matrix described
        in section 6.2 of DWARFv3. It's a list of LineState objects,
        sorted by increasing address, so it can be used to obtain the
        state information for each address.
    """
    def __init__(self, header, stream, structs,
                 program_start_offset, program_end_offset):
        """ 
            header:
                The header of this line program. Note: LineProgram may modify
                its header by appending file entries if DW_LNE_define_file
                instructions are encountered.

            stream:
                The stream this program can be read from.

            structs:
                A DWARFStructs instance suitable for this line program

            program_{start|end}_offset:
                Offset in the debug_line section stream where this program
                starts (the actual program, after the header), and where it
                ends.
                The actual range includes start but not end: [start, end - 1]
        """
        self.stream = stream
        self.header = header
        self.structs = structs
        self.program_start_offset = program_start_offset
        self.program_end_offset = program_end_offset
        self._decoded_entries = None

    def get_entries(self):
        """ Get the decoded entries for this line program. Return a list of
            LineProgramEntry objects.
            Note that this contains more information than absolutely required
            for the line table. The line table can be easily extracted from
            the list of entries by looking only at entries with non-None
            state. The extra information is mainly for the purposes of display
            with readelf and debugging.
        """
        if self._decoded_entries is None:
            self._decoded_entries = self._decode_line_program()
        return self._decoded_entries

    #------ PRIVATE ------#
    
    def __getitem__(self, name):
        """ Implement dict-like access to header entries
        """
        return self.header[name]

    def _decode_line_program(self):
        entries = []
        state = LineState(self.header['default_is_stmt'])

        def add_entry_new_state(cmd, args, is_extended=False):
            # Add an entry that sets a new state.
            # After adding, clear some state registers.
            entries.append(LineProgramEntry(
                cmd, is_extended, args, copy.copy(state)))
            state.basic_block = False
            state.prologue_end = False
            state.epilogue_begin = False

        def add_entry_old_state(cmd, args, is_extended=False):
            # Add an entry that doesn't visibly set a new state
            entries.append(LineProgramEntry(cmd, is_extended, args, None))

        offset = self.program_start_offset
        while offset < self.program_end_offset:
            opcode = struct_parse(
                self.structs.Dwarf_uint8(''), 
                self.stream,
                offset)

            # As an exercise in avoiding premature optimization, if...elif
            # chains are used here for standard and extended opcodes instead
            # of dispatch tables. This keeps the code much cleaner. Besides,
            # the majority of instructions in a typical program are special
            # opcodes anyway.
            if opcode >= self.header['opcode_base']:
                # Special opcode (follow the recipe in 6.2.5.1)
                adjusted_opcode = opcode - self['opcode_base']
                address_addend = ((adjusted_opcode // self['line_range']) *
                                  self['minimum_instruction_length'])
                state.address += address_addend
                line_addend = (self['line_base'] + 
                               adjusted_opcode % self['line_range'])
                state.line += line_addend
                add_entry_new_state(opcode, [line_addend, address_addend])
            elif opcode == 0:
                # Extended opcode: start with a zero byte, followed by
                # instruction size and the instruction itself.
                inst_len = struct_parse(self.structs.Dwarf_uleb128(''),
                                        self.stream)
                ex_opcode = struct_parse(self.structs.Dwarf_uint8(''),
                                         self.stream)

                if ex_opcode == DW_LNE_end_sequence:
                    state.end_sequence = True
                    add_entry_new_state(ex_opcode, [], is_extended=True)
                    # reset state
                    state = LineState(self.header['default_is_stmt']) 
                elif ex_opcode == DW_LNE_set_address:
                    operand = struct_parse(self.structs.Dwarf_target_addr(''),
                                           self.stream)
                    state.address = operand
                    add_entry_old_state(ex_opcode, [operand], is_extended=True)
                elif ex_opcode == DW_LNE_define_file:
                    operand = struct_parse(
                        self.structs.Dwarf_lineprog_file_entry, self.stream)
                    self['file_entry'].append(operand)
                    add_entry_old_state(ex_opcode, [operand], is_extended=True)
                else:
                    # Unknown, but need to roll forward the stream because the
                    # length is specified. Seek forward inst_len - 1 because
                    # we've already read the extended opcode, which takes part
                    # in the length.
                    self.stream.seek(inst_len - 1, os.SEEK_CUR)
            else: # 0 < opcode < opcode_base
                # Standard opcode
                if opcode == DW_LNS_copy:
                    add_entry_new_state(opcode, [])
                elif opcode == DW_LNS_advance_pc:
                    operand = struct_parse(self.structs.Dwarf_uleb128(''),
                                           self.stream)
                    address_addend = (
                        operand * self.header['minimum_instruction_length'])
                    state.address += address_addend
                    add_entry_old_state(opcode, [address_addend])
                elif opcode == DW_LNS_advance_line:
                    operand = struct_parse(self.structs.Dwarf_sleb128(''),
                                           self.stream)
                    state.line += operand
                elif opcode == DW_LNS_set_file:
                    operand = struct_parse(self.structs.Dwarf_uleb128(''),
                                           self.stream)
                    state.file = operand
                    add_entry_old_state(opcode, [operand])
                elif opcode == DW_LNS_set_column:
                    operand = struct_parse(self.structs.Dwarf_uleb128(''),
                                           self.stream)
                    state.column = operand
                    add_entry_old_state(opcode, [operand])
                elif opcode == DW_LNS_negate_stmt:
                    state.is_stmt = not state.is_stmt
                    add_entry_old_state(opcode, [])
                elif opcode == DW_LNS_set_basic_block:
                    state.basic_block = True
                    add_entry_old_state(opcode, [])
                elif opcode == DW_LNS_const_add_pc:
                    adjusted_opcode = 255 - self['opcode_base']
                    address_addend = ((adjusted_opcode // self['line_range']) *
                                      self['minimum_instruction_length'])
                    state.address += address_addend
                    add_entry_old_state(opcode, [address_addend])
                elif opcode == DW_LNS_fixed_advance_pc:
                    operand = struct_parse(self.structs.Dwarf_uint16(''),
                                           self.stream)
                    state.address += operand
                    add_entry_old_state(opcode, [operand])
                elif opcode == DW_LNS_set_prologue_end:
                    state.prologue_end = True
                    add_entry_old_state(opcode, [])
                elif opcode == DW_LNS_set_epilogue_begin:
                    state.epilogue_begin = True
                    add_entry_old_state(opcode, [])
                elif opcode == DW_LNS_set_isa:
                    operand = struct_parse(self.structs.Dwarf_uleb128(''),
                                           self.stream)
                    state.isa = operand
                    add_entry_old_state(opcode, [operand])
                else:
                    dwarf_assert(False, 'Invalid standard line program opcode: %s' % (
                        opcode,))
            offset = self.stream.tell()
        return entries


########NEW FILE########
__FILENAME__ = locationlists
#-------------------------------------------------------------------------------
# elftools: dwarf/locationlists.py
#
# DWARF location lists section decoding (.debug_loc)
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
import os
from collections import namedtuple

from ..common.utils import struct_parse


LocationEntry = namedtuple('LocationEntry', 'begin_offset end_offset loc_expr')
BaseAddressEntry = namedtuple('BaseAddressEntry', 'base_address')


class LocationLists(object):
    """ A single location list is a Python list consisting of LocationEntry or
        BaseAddressEntry objects.
    """
    def __init__(self, stream, structs):
        self.stream = stream
        self.structs = structs
        self._max_addr = 2 ** (self.structs.address_size * 8) - 1
        
    def get_location_list_at_offset(self, offset):
        """ Get a location list at the given offset in the section.
        """
        self.stream.seek(offset, os.SEEK_SET)
        return self._parse_location_list_from_stream()

    def iter_location_lists(self):
        """ Yield all location lists found in the section.
        """
        # Just call _parse_location_list_from_stream until the stream ends
        self.stream.seek(0, os.SEEK_END)
        endpos = self.stream.tell()

        self.stream.seek(0, os.SEEK_SET)
        while self.stream.tell() < endpos:
            yield self._parse_location_list_from_stream()

    #------ PRIVATE ------#

    def _parse_location_list_from_stream(self):
        lst = []
        while True:
            begin_offset = struct_parse(
                self.structs.Dwarf_target_addr(''), self.stream)
            end_offset = struct_parse(
                self.structs.Dwarf_target_addr(''), self.stream)
            if begin_offset == 0 and end_offset == 0:
                # End of list - we're done.
                break
            elif begin_offset == self._max_addr:
                # Base address selection entry
                lst.append(BaseAddressEntry(base_address=end_offset))
            else: 
                # Location list entry
                expr_len = struct_parse(
                    self.structs.Dwarf_uint16(''), self.stream)
                loc_expr = [struct_parse(self.structs.Dwarf_uint8(''),
                                         self.stream)
                                for i in range(expr_len)]
                lst.append(LocationEntry(
                    begin_offset=begin_offset,
                    end_offset=end_offset,
                    loc_expr=loc_expr))
        return lst


########NEW FILE########
__FILENAME__ = ranges
#-------------------------------------------------------------------------------
# elftools: dwarf/ranges.py
#
# DWARF ranges section decoding (.debug_ranges)
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
import os
from collections import namedtuple

from ..common.utils import struct_parse


RangeEntry = namedtuple('RangeEntry', 'begin_offset end_offset')
BaseAddressEntry = namedtuple('BaseAddressEntry', 'base_address')


class RangeLists(object):
    """ A single range list is a Python list consisting of RangeEntry or
        BaseAddressEntry objects.
    """
    def __init__(self, stream, structs):
        self.stream = stream
        self.structs = structs
        self._max_addr = 2 ** (self.structs.address_size * 8) - 1

    def get_range_list_at_offset(self, offset):
        """ Get a range list at the given offset in the section.
        """
        self.stream.seek(offset, os.SEEK_SET)
        return self._parse_range_list_from_stream()

    def iter_range_lists(self):
        """ Yield all range lists found in the section.
        """
        # Just call _parse_range_list_from_stream until the stream ends
        self.stream.seek(0, os.SEEK_END)
        endpos = self.stream.tell()

        self.stream.seek(0, os.SEEK_SET)
        while self.stream.tell() < endpos:
            yield self._parse_range_list_from_stream()

    #------ PRIVATE ------#

    def _parse_range_list_from_stream(self):
        lst = []
        while True:
            begin_offset = struct_parse(
                self.structs.Dwarf_target_addr(''), self.stream)
            end_offset = struct_parse(
                self.structs.Dwarf_target_addr(''), self.stream)
            if begin_offset == 0 and end_offset == 0:
                # End of list - we're done.
                break
            elif begin_offset == self._max_addr:
                # Base address selection entry
                lst.append(BaseAddressEntry(base_address=end_offset))
            else: 
                # Range entry
                lst.append(RangeEntry(
                    begin_offset=begin_offset,
                    end_offset=end_offset))
        return lst




########NEW FILE########
__FILENAME__ = structs
#-------------------------------------------------------------------------------
# elftools: dwarf/structs.py
#
# Encapsulation of Construct structs for parsing DWARF, adjusted for correct
# endianness and word-size.
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
from ..construct import (
    UBInt8, UBInt16, UBInt32, UBInt64, ULInt8, ULInt16, ULInt32, ULInt64,
    SBInt8, SBInt16, SBInt32, SBInt64, SLInt8, SLInt16, SLInt32, SLInt64,
    Adapter, Struct, ConstructError, If, RepeatUntil, Field, Rename, Enum,
    Array, PrefixedArray, CString, Embed, StaticField
    )
from ..common.construct_utils import RepeatUntilExcluding

from .enums import *


class DWARFStructs(object):
    """ Exposes Construct structs suitable for parsing information from DWARF
        sections. Each compile unit in DWARF info can have its own structs
        object. Keep in mind that these structs have to be given a name (by
        calling them with a name) before being used for parsing (like other
        Construct structs). Those that should be used without a name are marked
        by (+).

        Accessible attributes (mostly as described in chapter 7 of the DWARF
        spec v3):

            Dwarf_[u]int{8,16,32,64):
                Data chunks of the common sizes

            Dwarf_offset:
                32-bit or 64-bit word, depending on dwarf_format

            Dwarf_target_addr:
                32-bit or 64-bit word, depending on address size

            Dwarf_initial_length:
                "Initial length field" encoding
                section 7.4

            Dwarf_{u,s}leb128:
                ULEB128 and SLEB128 variable-length encoding

            Dwarf_CU_header (+):
                Compilation unit header

            Dwarf_abbrev_declaration (+):
                Abbreviation table declaration - doesn't include the initial
                code, only the contents.

            Dwarf_dw_form (+):
                A dictionary mapping 'DW_FORM_*' keys into construct Structs
                that parse such forms. These Structs have already been given
                dummy names.

            Dwarf_lineprog_header (+):
                Line program header

            Dwarf_lineprog_file_entry (+):
                A single file entry in a line program header or instruction

            Dwarf_CIE_header (+):
                A call-frame CIE

            Dwarf_FDE_header (+):
                A call-frame FDE

        See also the documentation of public methods.
    """
    def __init__(self,
                 little_endian, dwarf_format, address_size, dwarf_version=2):
        """ dwarf_version:
                Numeric DWARF version

            little_endian:
                True if the file is little endian, False if big

            dwarf_format:
                DWARF Format: 32 or 64-bit (see spec section 7.4)

            address_size:
                Target machine address size, in bytes (4 or 8). (See spec
                section 7.5.1)
        """
        assert dwarf_format == 32 or dwarf_format == 64
        assert address_size == 8 or address_size == 4
        self.little_endian = little_endian
        self.dwarf_format = dwarf_format
        self.address_size = address_size
        self.dwarf_version = dwarf_version
        self._create_structs()

    def initial_length_field_size(self):
        """ Size of an initial length field.
        """
        return 4 if self.dwarf_format == 32 else 12

    def _create_structs(self):
        if self.little_endian:
            self.Dwarf_uint8 = ULInt8
            self.Dwarf_uint16 = ULInt16
            self.Dwarf_uint32 = ULInt32
            self.Dwarf_uint64 = ULInt64
            self.Dwarf_offset = ULInt32 if self.dwarf_format == 32 else ULInt64
            self.Dwarf_target_addr = (
                ULInt32 if self.address_size == 4 else ULInt64)
            self.Dwarf_int8 = SLInt8
            self.Dwarf_int16 = SLInt16
            self.Dwarf_int32 = SLInt32
            self.Dwarf_int64 = SLInt64
        else:
            self.Dwarf_uint8 = UBInt8
            self.Dwarf_uint16 = UBInt16
            self.Dwarf_uint32 = UBInt32
            self.Dwarf_uint64 = UBInt64
            self.Dwarf_offset = UBInt32 if self.dwarf_format == 32 else UBInt64
            self.Dwarf_target_addr = (
                UBInt32 if self.address_size == 4 else UBInt64)
            self.Dwarf_int8 = SBInt8
            self.Dwarf_int16 = SBInt16
            self.Dwarf_int32 = SBInt32
            self.Dwarf_int64 = SBInt64

        self._create_initial_length()
        self._create_leb128()
        self._create_cu_header()
        self._create_abbrev_declaration()
        self._create_dw_form()
        self._create_lineprog_header()
        self._create_callframe_entry_headers()

    def _create_initial_length(self):
        def _InitialLength(name):
            # Adapts a Struct that parses forward a full initial length field.
            # Only if the first word is the continuation value, the second
            # word is parsed from the stream.
            #
            return _InitialLengthAdapter(
                Struct(name,
                    self.Dwarf_uint32('first'),
                    If(lambda ctx: ctx.first == 0xFFFFFFFF,
                        self.Dwarf_uint64('second'),
                        elsevalue=None)))
        self.Dwarf_initial_length = _InitialLength

    def _create_leb128(self):
        self.Dwarf_uleb128 = _ULEB128
        self.Dwarf_sleb128 = _SLEB128

    def _create_cu_header(self):
        self.Dwarf_CU_header = Struct('Dwarf_CU_header',
            self.Dwarf_initial_length('unit_length'),
            self.Dwarf_uint16('version'),
            self.Dwarf_offset('debug_abbrev_offset'),
            self.Dwarf_uint8('address_size'))

    def _create_abbrev_declaration(self):
        self.Dwarf_abbrev_declaration = Struct('Dwarf_abbrev_entry',
            Enum(self.Dwarf_uleb128('tag'), **ENUM_DW_TAG),
            Enum(self.Dwarf_uint8('children_flag'), **ENUM_DW_CHILDREN),
            RepeatUntilExcluding(
                lambda obj, ctx:
                    obj.name == 'DW_AT_null' and obj.form == 'DW_FORM_null',
                Struct('attr_spec',
                    Enum(self.Dwarf_uleb128('name'), **ENUM_DW_AT),
                    Enum(self.Dwarf_uleb128('form'), **ENUM_DW_FORM))))

    def _create_dw_form(self):
        self.Dwarf_dw_form = dict(
            DW_FORM_addr=self.Dwarf_target_addr(''),

            DW_FORM_block1=self._make_block_struct(self.Dwarf_uint8),
            DW_FORM_block2=self._make_block_struct(self.Dwarf_uint16),
            DW_FORM_block4=self._make_block_struct(self.Dwarf_uint32),
            DW_FORM_block=self._make_block_struct(self.Dwarf_uleb128),

            # All DW_FORM_data<n> forms are assumed to be unsigned
            DW_FORM_data1=self.Dwarf_uint8(''),
            DW_FORM_data2=self.Dwarf_uint16(''),
            DW_FORM_data4=self.Dwarf_uint32(''),
            DW_FORM_data8=self.Dwarf_uint64(''),
            DW_FORM_sdata=self.Dwarf_sleb128(''),
            DW_FORM_udata=self.Dwarf_uleb128(''),

            DW_FORM_string=CString(''),
            DW_FORM_strp=self.Dwarf_offset(''),
            DW_FORM_flag=self.Dwarf_uint8(''),

            DW_FORM_ref1=self.Dwarf_uint8(''),
            DW_FORM_ref2=self.Dwarf_uint16(''),
            DW_FORM_ref4=self.Dwarf_uint32(''),
            DW_FORM_ref8=self.Dwarf_uint64(''),
            DW_FORM_ref_udata=self.Dwarf_uleb128(''),
            DW_FORM_ref_addr=self.Dwarf_offset(''),

            DW_FORM_indirect=self.Dwarf_uleb128(''),

            # New forms in DWARFv4
            DW_FORM_flag_present = StaticField('', 0),
            DW_FORM_sec_offset = self.Dwarf_offset(''),
            DW_FORM_exprloc = self._make_block_struct(self.Dwarf_uleb128),
            DW_FORM_ref_sig8 = self.Dwarf_offset(''),

            DW_FORM_GNU_strp_alt=self.Dwarf_offset(''),
            DW_FORM_GNU_ref_alt=self.Dwarf_offset(''),
            DW_AT_GNU_all_call_sites=self.Dwarf_uleb128(''),
        )

    def _create_lineprog_header(self):
        # A file entry is terminated by a NULL byte, so we don't want to parse
        # past it. Therefore an If is used.
        self.Dwarf_lineprog_file_entry = Struct('file_entry',
            CString('name'),
            If(lambda ctx: len(ctx.name) != 0,
                Embed(Struct('',
                    self.Dwarf_uleb128('dir_index'),
                    self.Dwarf_uleb128('mtime'),
                    self.Dwarf_uleb128('length')))))

        self.Dwarf_lineprog_header = Struct('Dwarf_lineprog_header',
            self.Dwarf_initial_length('unit_length'),
            self.Dwarf_uint16('version'),
            self.Dwarf_offset('header_length'),
            self.Dwarf_uint8('minimum_instruction_length'),
            self.Dwarf_uint8('default_is_stmt'),
            self.Dwarf_int8('line_base'),
            self.Dwarf_uint8('line_range'),
            self.Dwarf_uint8('opcode_base'),
            Array(lambda ctx: ctx['opcode_base'] - 1,
                  self.Dwarf_uint8('standard_opcode_lengths')),
            RepeatUntilExcluding(
                lambda obj, ctx: obj == b'',
                CString('include_directory')),
            RepeatUntilExcluding(
                lambda obj, ctx: len(obj.name) == 0,
                self.Dwarf_lineprog_file_entry),
            )

    def _create_callframe_entry_headers(self):
        # The CIE header was modified in DWARFv4.
        if self.dwarf_version == 4:
            self.Dwarf_CIE_header = Struct('Dwarf_CIE_header',
                self.Dwarf_initial_length('length'),
                self.Dwarf_offset('CIE_id'),
                self.Dwarf_uint8('version'),
                CString('augmentation'),
                self.Dwarf_uint8('address_size'),
                self.Dwarf_uint8('segment_size'),
                self.Dwarf_uleb128('code_alignment_factor'),
                self.Dwarf_sleb128('data_alignment_factor'),
                self.Dwarf_uleb128('return_address_register'))
        else:
            self.Dwarf_CIE_header = Struct('Dwarf_CIE_header',
                self.Dwarf_initial_length('length'),
                self.Dwarf_offset('CIE_id'),
                self.Dwarf_uint8('version'),
                CString('augmentation'),
                self.Dwarf_uleb128('code_alignment_factor'),
                self.Dwarf_sleb128('data_alignment_factor'),
                self.Dwarf_uleb128('return_address_register'))

        self.Dwarf_FDE_header = Struct('Dwarf_FDE_header',
            self.Dwarf_initial_length('length'),
            self.Dwarf_offset('CIE_pointer'),
            self.Dwarf_target_addr('initial_location'),
            self.Dwarf_target_addr('address_range'))

    def _make_block_struct(self, length_field):
        """ Create a struct for DW_FORM_block<size>
        """
        return PrefixedArray(
                    subcon=self.Dwarf_uint8('elem'),
                    length_field=length_field(''))


class _InitialLengthAdapter(Adapter):
    """ A standard Construct adapter that expects a sub-construct
        as a struct with one or two values (first, second).
    """
    def _decode(self, obj, context):
        if obj.first < 0xFFFFFF00:
            return obj.first
        else:
            if obj.first == 0xFFFFFFFF:
                return obj.second
            else:
                raise ConstructError("Failed decoding initial length for %X" % (
                    obj.first))


def _LEB128_reader():
    """ Read LEB128 variable-length data from the stream. The data is terminated
        by a byte with 0 in its highest bit.
    """
    return RepeatUntil(
                lambda obj, ctx: ord(obj) < 0x80,
                Field(None, 1))


class _ULEB128Adapter(Adapter):
    """ An adapter for ULEB128, given a sequence of bytes in a sub-construct.
    """
    def _decode(self, obj, context):
        value = 0
        for b in reversed(obj):
            value = (value << 7) + (ord(b) & 0x7F)
        return value


class _SLEB128Adapter(Adapter):
    """ An adapter for SLEB128, given a sequence of bytes in a sub-construct.
    """
    def _decode(self, obj, context):
        value = 0
        for b in reversed(obj):
            value = (value << 7) + (ord(b) & 0x7F)
        if ord(obj[-1]) & 0x40:
            # negative -> sign extend
            #
            value |= - (1 << (7 * len(obj)))
        return value


def _ULEB128(name):
    """ A construct creator for ULEB128 encoding.
    """
    return Rename(name, _ULEB128Adapter(_LEB128_reader()))


def _SLEB128(name):
    """ A construct creator for SLEB128 encoding.
    """
    return Rename(name, _SLEB128Adapter(_LEB128_reader()))



########NEW FILE########
__FILENAME__ = constants
#-------------------------------------------------------------------------------
# elftools: elf/constants.py
#
# Constants and flags, placed into classes for namespacing
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------

class E_FLAGS(object):
    """ Flag values for the e_flags field of the ELF header
    """
    EF_ARM_EABIMASK=0xFF000000
    EF_ARM_EABI_VER1=0x01000000
    EF_ARM_EABI_VER2=0x02000000
    EF_ARM_EABI_VER3=0x03000000
    EF_ARM_EABI_VER4=0x04000000
    EF_ARM_EABI_VER5=0x05000000
    EF_ARM_GCCMASK=0x00400FFF
    EF_ARM_HASENTRY=0x02
    EF_ARM_SYMSARESORTED=0x04
    EF_ARM_DYNSYMSUSESEGIDX=0x8
    EF_ARM_MAPSYMSFIRST=0x10
    EF_ARM_LE8=0x00400000
    EF_ARM_BE8=0x00800000
    EF_ARM_ABI_FLOAT_SOFT=0x00000200
    EF_ARM_ABI_FLOAT_HARD=0x00000400

class SHN_INDICES(object):
    """ Special section indices
    """
    SHN_UNDEF=0
    SHN_LORESERVE=0xff00
    SHN_LOPROC=0xff00
    SHN_HIPROC=0xff1f
    SHN_ABS=0xfff1
    SHN_COMMON=0xfff2
    SHN_HIRESERVE=0xffff


class SH_FLAGS(object):
    """ Flag values for the sh_flags field of section headers
    """
    SHF_WRITE=0x1
    SHF_ALLOC=0x2
    SHF_EXECINSTR=0x4
    SHF_MERGE=0x10
    SHF_STRINGS=0x20
    SHF_INFO_LINK=0x40
    SHF_LINK_ORDER=0x80
    SHF_OS_NONCONFORMING=0x100
    SHF_GROUP=0x200
    SHF_TLS=0x400
    SHF_MASKOS=0x0ff00000
    SHF_EXCLUDE=0x80000000
    SHF_MASKPROC=0xf0000000


class P_FLAGS(object):
    """ Flag values for the p_flags field of program headers
    """
    PF_X=0x1
    PF_W=0x2
    PF_R=0x4
    PF_MASKOS=0x00FF0000
    PF_MASKPROC=0xFF000000


# symbol info flags for entries
# in the .SUNW_syminfo section
class SUNW_SYMINFO_FLAGS(object):
    """ Flags for the si_flags field of entries
        in the .SUNW_syminfo section
    """
    SYMINFO_FLG_DIRECT=0x1
    SYMINFO_FLG_FILTER=0x2
    SYMINFO_FLG_COPY=0x4
    SYMINFO_FLG_LAZYLOAD=0x8
    SYMINFO_FLG_DIRECTBIND=0x10
    SYMINFO_FLG_NOEXTDIRECT=0x20
    SYMINFO_FLG_AUXILIARY=0x40
    SYMINFO_FLG_INTERPOSE=0x80
    SYMINFO_FLG_CAP=0x100
    SYMINFO_FLG_DEFERRED=0x200

class VER_FLAGS(object):
    VER_FLG_BASE=0x1
    VER_FLG_WEAK=0x2
    VER_FLG_INFO=0x4 

########NEW FILE########
__FILENAME__ = descriptions
#-------------------------------------------------------------------------------
# elftools: elf/descriptions.py
#
# Textual descriptions of the various enums and flags of ELF
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
from .enums import (
    ENUM_D_TAG, ENUM_E_VERSION, ENUM_RELOC_TYPE_i386, ENUM_RELOC_TYPE_x64,
        ENUM_RELOC_TYPE_ARM, ENUM_RELOC_TYPE_AARCH64)
from .constants import P_FLAGS, SH_FLAGS, SUNW_SYMINFO_FLAGS, VER_FLAGS
from ..common.py3compat import iteritems


def describe_ei_class(x):
    return _DESCR_EI_CLASS.get(x, _unknown)

def describe_ei_data(x):
    return _DESCR_EI_DATA.get(x, _unknown)

def describe_ei_version(x):
    s = '%d' % ENUM_E_VERSION[x]
    if x == 'EV_CURRENT':
        s += ' (current)'
    return s

def describe_ei_osabi(x):
    return _DESCR_EI_OSABI.get(x, _unknown)

def describe_e_type(x):
    return _DESCR_E_TYPE.get(x, _unknown)

def describe_e_machine(x):
    return _DESCR_E_MACHINE.get(x, _unknown)

def describe_e_version_numeric(x):
    return '0x%x' % ENUM_E_VERSION[x]

def describe_p_type(x):
    return _DESCR_P_TYPE.get(x, _unknown)

def describe_p_flags(x):
    s = ''
    for flag in (P_FLAGS.PF_R, P_FLAGS.PF_W, P_FLAGS.PF_X):
        s += _DESCR_P_FLAGS[flag] if (x & flag) else ' '
    return s

def describe_sh_type(x):
    return _DESCR_SH_TYPE.get(x, _unknown)

def describe_sh_flags(x):
    s = ''
    for flag in (
            SH_FLAGS.SHF_WRITE, SH_FLAGS.SHF_ALLOC, SH_FLAGS.SHF_EXECINSTR,
            SH_FLAGS.SHF_MERGE, SH_FLAGS.SHF_STRINGS, SH_FLAGS.SHF_INFO_LINK,
            SH_FLAGS.SHF_LINK_ORDER, SH_FLAGS.SHF_OS_NONCONFORMING,
            SH_FLAGS.SHF_GROUP, SH_FLAGS.SHF_TLS, SH_FLAGS.SHF_EXCLUDE):
        s += _DESCR_SH_FLAGS[flag] if (x & flag) else ''
    return s

def describe_symbol_type(x):
    return _DESCR_ST_INFO_TYPE.get(x, _unknown)

def describe_symbol_bind(x):
    return _DESCR_ST_INFO_BIND.get(x, _unknown)

def describe_symbol_visibility(x):
    return _DESCR_ST_VISIBILITY.get(x, _unknown)

def describe_symbol_shndx(x):
    return _DESCR_ST_SHNDX.get(x, '%3s' % x)

def describe_reloc_type(x, elffile):
    arch = elffile.get_machine_arch()
    if arch == 'x86':
        return _DESCR_RELOC_TYPE_i386.get(x, _unknown)
    elif arch == 'x64':
        return _DESCR_RELOC_TYPE_x64.get(x, _unknown)
    elif arch == 'ARM':
        return _DESCR_RELOC_TYPE_ARM.get(x, _unknown)
    elif arch == 'AArch64':
        return _DESCR_RELOC_TYPE_AARCH64.get(x, _unknown)
    else:
        return 'unrecognized: %-7x' % (x & 0xFFFFFFFF)

def describe_dyn_tag(x):
    return _DESCR_D_TAG.get(x, _unknown)


def describe_syminfo_flags(x):
    return ''.join(_DESCR_SYMINFO_FLAGS[flag] for flag in (
        SUNW_SYMINFO_FLAGS.SYMINFO_FLG_CAP,
        SUNW_SYMINFO_FLAGS.SYMINFO_FLG_DIRECT,
        SUNW_SYMINFO_FLAGS.SYMINFO_FLG_FILTER,
        SUNW_SYMINFO_FLAGS.SYMINFO_FLG_AUXILIARY,
        SUNW_SYMINFO_FLAGS.SYMINFO_FLG_DIRECTBIND,
        SUNW_SYMINFO_FLAGS.SYMINFO_FLG_COPY,
        SUNW_SYMINFO_FLAGS.SYMINFO_FLG_LAZYLOAD,
        SUNW_SYMINFO_FLAGS.SYMINFO_FLG_NOEXTDIRECT,
        SUNW_SYMINFO_FLAGS.SYMINFO_FLG_INTERPOSE,
        SUNW_SYMINFO_FLAGS.SYMINFO_FLG_DEFERRED) if x & flag)

def describe_symbol_boundto(x):
    return _DESCR_SYMINFO_BOUNDTO.get(x, '%3s' % x)

def describe_ver_flags(x):
    return ' | '.join(_DESCR_VER_FLAGS[flag] for flag in (
        VER_FLAGS.VER_FLG_WEAK,
        VER_FLAGS.VER_FLG_BASE,
        VER_FLAGS.VER_FLG_INFO) if x & flag)

#-------------------------------------------------------------------------------
_unknown = '<unknown>'


_DESCR_EI_CLASS = dict(
    ELFCLASSNONE='none',
    ELFCLASS32='ELF32',
    ELFCLASS64='ELF64',
)

_DESCR_EI_DATA = dict(
    ELFDATANONE='none',
    ELFDATA2LSB="2's complement, little endian",
    ELFDATA2MSB="2's complement, big endian",
)

_DESCR_EI_OSABI = dict(
    ELFOSABI_SYSV='UNIX - System V',
    ELFOSABI_HPUX='UNIX - HP-UX',
    ELFOSABI_NETBSD='UNIX - NetBSD',
    ELFOSABI_LINUX='UNIX - Linux',
    ELFOSABI_HURD='UNIX - GNU/Hurd',
    ELFOSABI_SOLARIS='UNIX - Solaris',
    ELFOSABI_AIX='UNIX - AIX',
    ELFOSABI_IRIX='UNIX - IRIX',
    ELFOSABI_FREEBSD='UNIX - FreeBSD',
    ELFOSABI_TRU64='UNIX - TRU64',
    ELFOSABI_MODESTO='Novell - Modesto',
    ELFOSABI_OPENBSD='UNIX - OpenBSD',
    ELFOSABI_OPENVMS='VMS - OpenVMS',
    ELFOSABI_NSK='HP - Non-Stop Kernel',
    ELFOSABI_AROS='AROS',
    ELFOSABI_ARM='ARM',
    ELFOSABI_STANDALONE='Standalone App',
)

_DESCR_E_TYPE = dict(
    ET_NONE='NONE (None)',
    ET_REL='REL (Relocatable file)',
    ET_EXEC='EXEC (Executable file)',
    ET_DYN='DYN (Shared object file)',
    ET_CORE='CORE (Core file)',
    PROC_SPECIFIC='Processor Specific',
)

_DESCR_E_MACHINE = dict(
    EM_NONE='None',
    EM_M32='WE32100',
    EM_SPARC='Sparc',
    EM_386='Intel 80386',
    EM_68K='MC68000',
    EM_88K='MC88000',
    EM_860='Intel 80860',
    EM_MIPS='MIPS R3000',
    EM_S370='IBM System/370',
    EM_MIPS_RS4_BE='MIPS 4000 big-endian',
    EM_IA_64='Intel IA-64',
    EM_X86_64='Advanced Micro Devices X86-64',
    EM_AVR='Atmel AVR 8-bit microcontroller',
    EM_ARM='ARM',
    EM_AARCH64='AArch64',
    RESERVED='RESERVED',
)

_DESCR_P_TYPE = dict(
    PT_NULL='NULL',
    PT_LOAD='LOAD',
    PT_DYNAMIC='DYNAMIC',
    PT_INTERP='INTERP',
    PT_NOTE='NOTE',
    PT_SHLIB='SHLIB',
    PT_PHDR='PHDR',
    PT_GNU_EH_FRAME='GNU_EH_FRAME',
    PT_GNU_STACK='GNU_STACK',
    PT_GNU_RELRO='GNU_RELRO',
    PT_ARM_ARCHEXT='ARM_ARCHEXT',
    PT_ARM_EXIDX='ARM_EXIDX',
    PT_ARM_UNWIND='ARM_UNWIND',
    PT_AARCH64_ARCHEXT='AARCH64_ARCHEXT',
    PT_AARCH64_UNWIND='AARCH64_UNWIND',
)

_DESCR_P_FLAGS = {
    P_FLAGS.PF_X: 'E',
    P_FLAGS.PF_R: 'R',
    P_FLAGS.PF_W: 'W',
}

_DESCR_SH_TYPE = dict(
    SHT_NULL='NULL',
    SHT_PROGBITS='PROGBITS',
    SHT_SYMTAB='SYMTAB',
    SHT_STRTAB='STRTAB',
    SHT_RELA='RELA',
    SHT_HASH='HASH',
    SHT_DYNAMIC='DYNAMIC',
    SHT_NOTE='NOTE',
    SHT_NOBITS='NOBITS',
    SHT_REL='REL',
    SHT_SHLIB='SHLIB',
    SHT_DYNSYM='DYNSYM',
    SHT_INIT_ARRAY='INIT_ARRAY',
    SHT_FINI_ARRAY='FINI_ARRAY',
    SHT_PREINIT_ARRAY='PREINIT_ARRAY',
    SHT_GNU_HASH='GNU_HASH',
    SHT_GROUP='GROUP',
    SHT_SYMTAB_SHNDX='SYMTAB SECTION INDICIES',
    SHT_GNU_verdef='VERDEF',
    SHT_GNU_verneed='VERNEED',
    SHT_GNU_versym='VERSYM',
    SHT_GNU_LIBLIST='GNU_LIBLIST',
    SHT_ARM_EXIDX='ARM_EXIDX',
    SHT_ARM_PREEMPTMAP='ARM_PREEMPTMAP',
    SHT_ARM_ATTRIBUTES='ARM_ATTRIBUTES',
    SHT_ARM_DEBUGOVERLAY='ARM_DEBUGOVERLAY',
)

_DESCR_SH_FLAGS = {
    SH_FLAGS.SHF_WRITE: 'W',
    SH_FLAGS.SHF_ALLOC: 'A',
    SH_FLAGS.SHF_EXECINSTR: 'X',
    SH_FLAGS.SHF_MERGE: 'M',
    SH_FLAGS.SHF_STRINGS: 'S',
    SH_FLAGS.SHF_INFO_LINK: 'I',
    SH_FLAGS.SHF_LINK_ORDER: 'L',
    SH_FLAGS.SHF_OS_NONCONFORMING: 'O',
    SH_FLAGS.SHF_GROUP: 'G',
    SH_FLAGS.SHF_TLS: 'T',
    SH_FLAGS.SHF_EXCLUDE: 'E',
}

_DESCR_ST_INFO_TYPE = dict(
    STT_NOTYPE='NOTYPE',
    STT_OBJECT='OBJECT',
    STT_FUNC='FUNC',
    STT_SECTION='SECTION',
    STT_FILE='FILE',
    STT_COMMON='COMMON',
    STT_TLS='TLS',
    STT_NUM='NUM',
    STT_RELC='RELC',
    STT_SRELC='SRELC',
)

_DESCR_ST_INFO_BIND = dict(
    STB_LOCAL='LOCAL',
    STB_GLOBAL='GLOBAL',
    STB_WEAK='WEAK',
)

_DESCR_ST_VISIBILITY = dict(
    STV_DEFAULT='DEFAULT',
    STV_INTERNAL='INTERNAL',
    STV_HIDDEN='HIDDEN',
    STV_PROTECTED='PROTECTED',
    STV_EXPORTED='EXPORTED',
    STV_SINGLETON='SINGLETON',
    STV_ELIMINATE='ELIMINATE',
)

_DESCR_ST_SHNDX = dict(
    SHN_UNDEF='UND',
    SHN_ABS='ABS',
    SHN_COMMON='COM',
)

_DESCR_SYMINFO_FLAGS = {
    SUNW_SYMINFO_FLAGS.SYMINFO_FLG_DIRECT: 'D',
    SUNW_SYMINFO_FLAGS.SYMINFO_FLG_DIRECTBIND: 'B',
    SUNW_SYMINFO_FLAGS.SYMINFO_FLG_COPY: 'C',
    SUNW_SYMINFO_FLAGS.SYMINFO_FLG_LAZYLOAD: 'L',
    SUNW_SYMINFO_FLAGS.SYMINFO_FLG_NOEXTDIRECT: 'N',
    SUNW_SYMINFO_FLAGS.SYMINFO_FLG_AUXILIARY: 'A',
    SUNW_SYMINFO_FLAGS.SYMINFO_FLG_FILTER: 'F',
    SUNW_SYMINFO_FLAGS.SYMINFO_FLG_INTERPOSE: 'I',
    SUNW_SYMINFO_FLAGS.SYMINFO_FLG_CAP: 'S',
    SUNW_SYMINFO_FLAGS.SYMINFO_FLG_DEFERRED: 'P',
}

_DESCR_SYMINFO_BOUNDTO = dict(
    SYMINFO_BT_SELF='<self>',
    SYMINFO_BT_PARENT='<parent>',
    SYMINFO_BT_NONE='',
    SYMINFO_BT_EXTERN='<extern>',
)

_DESCR_VER_FLAGS = {
    0: '',
    VER_FLAGS.VER_FLG_BASE: 'BASE',
    VER_FLAGS.VER_FLG_WEAK: 'WEAK',
    VER_FLAGS.VER_FLG_INFO: 'INFO',
}

_DESCR_RELOC_TYPE_i386 = dict(
        (v, k) for k, v in iteritems(ENUM_RELOC_TYPE_i386))

_DESCR_RELOC_TYPE_x64 = dict(
        (v, k) for k, v in iteritems(ENUM_RELOC_TYPE_x64))

_DESCR_RELOC_TYPE_ARM = dict(
        (v, k) for k, v in iteritems(ENUM_RELOC_TYPE_ARM))

_DESCR_RELOC_TYPE_AARCH64 = dict(
        (v, k) for k, v in iteritems(ENUM_RELOC_TYPE_AARCH64))

_DESCR_D_TAG = dict(
        (v, k) for k, v in iteritems(ENUM_D_TAG))

########NEW FILE########
__FILENAME__ = dynamic
#-------------------------------------------------------------------------------
# elftools: elf/dynamic.py
#
# ELF Dynamic Tags
#
# Mike Frysinger (vapier@gentoo.org)
# This code is in the public domain
#-------------------------------------------------------------------------------
import itertools

from .sections import Section
from .segments import Segment
from ..common.exceptions import ELFError
from ..common.utils import struct_parse


class DynamicTag(object):
    """ Dynamic Tag object - representing a single dynamic tag entry from a
        dynamic section.

        Allows dictionary-like access to the dynamic structure. For special
        tags (those listed in the _HANDLED_TAGS set below), creates additional
        attributes for convenience. For example, .soname will contain the actual
        value of DT_SONAME (fetched from the dynamic symbol table).
    """
    _HANDLED_TAGS = frozenset(
        ['DT_NEEDED', 'DT_RPATH', 'DT_RUNPATH', 'DT_SONAME',
         'DT_SUNW_FILTER'])

    def __init__(self, entry, stringtable):
        if stringtable is None:
            raise ELFError('Creating DynamicTag without string table')
        self.entry = entry
        if entry.d_tag in self._HANDLED_TAGS:
            setattr(self, entry.d_tag[3:].lower(),
                    stringtable.get_string(self.entry.d_val))

    def __getitem__(self, name):
        """ Implement dict-like access to entries
        """
        return self.entry[name]

    def __repr__(self):
        return '<DynamicTag (%s): %r>' % (self.entry.d_tag, self.entry)

    def __str__(self):
        if self.entry.d_tag in self._HANDLED_TAGS:
            s = '"%s"' % getattr(self, self.entry.d_tag[3:].lower())
        else:
            s = '%#x' % self.entry.d_ptr
        return '<DynamicTag (%s) %s>' % (self.entry.d_tag, s)


class Dynamic(object):
    """ Shared functionality between dynamic sections and segments.
    """
    def __init__(self, stream, elffile, stringtable, position):
        self._stream = stream
        self._elffile = elffile
        self._elfstructs = elffile.structs
        self._num_tags = -1
        self._offset = position
        self._tagsize = self._elfstructs.Elf_Dyn.sizeof()
        self._stringtable = stringtable

    def iter_tags(self, type=None):
        """ Yield all tags (limit to |type| if specified)
        """
        for n in itertools.count():
            tag = self.get_tag(n)
            if type is None or tag.entry.d_tag == type:
                yield tag
            if tag.entry.d_tag == 'DT_NULL':
                break

    def get_tag(self, n):
        """ Get the tag at index #n from the file (DynamicTag object)
        """
        offset = self._offset + n * self._tagsize
        entry = struct_parse(
            self._elfstructs.Elf_Dyn,
            self._stream,
            stream_pos=offset)
        return DynamicTag(entry, self._stringtable)

    def num_tags(self):
        """ Number of dynamic tags in the file
        """
        if self._num_tags != -1:
            return self._num_tags

        for n in itertools.count():
            tag = self.get_tag(n)
            if tag.entry.d_tag == 'DT_NULL':
                self._num_tags = n + 1
                return self._num_tags


class DynamicSection(Section, Dynamic):
    """ ELF dynamic table section.  Knows how to process the list of tags.
    """
    def __init__(self, header, name, stream, elffile):
        Section.__init__(self, header, name, stream)
        stringtable = elffile.get_section(header['sh_link'])
        Dynamic.__init__(self, stream, elffile, stringtable, self['sh_offset'])


class DynamicSegment(Segment, Dynamic):
    """ ELF dynamic table segment.  Knows how to process the list of tags.
    """
    def __init__(self, header, stream, elffile):
        # The string table section to be used to resolve string names in
        # the dynamic tag array is the one pointed at by the sh_link field
        # of the dynamic section header.
        # So we must look for the dynamic section contained in the dynamic
        # segment, we do so by searching for the dynamic section whose content
        # is located at the same offset as the dynamic segment
        stringtable = None
        for section in elffile.iter_sections():
            if (isinstance(section, DynamicSection) and
                    section['sh_offset'] == header['p_offset']):
                stringtable = elffile.get_section(section['sh_link'])
                break
        Segment.__init__(self, header, stream)
        Dynamic.__init__(self, stream, elffile, stringtable, self['p_offset'])

########NEW FILE########
__FILENAME__ = elffile
#-------------------------------------------------------------------------------
# elftools: elf/elffile.py
#
# ELFFile - main class for accessing ELF files
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
from ..common.py3compat import BytesIO
from ..common.exceptions import ELFError
from ..common.utils import struct_parse, elf_assert
from ..construct import ConstructError
from .structs import ELFStructs
from .sections import (
        Section, StringTableSection, SymbolTableSection,
        SUNWSyminfoTableSection, NullSection)
from .dynamic import DynamicSection, DynamicSegment
from .relocation import RelocationSection, RelocationHandler
from .gnuversions import (
        GNUVerNeedSection, GNUVerDefSection,
        GNUVerSymSection)
from .segments import Segment, InterpSegment
from ..dwarf.dwarfinfo import DWARFInfo, DebugSectionDescriptor, DwarfConfig


class ELFFile(object):
    """ Creation: the constructor accepts a stream (file-like object) with the
        contents of an ELF file.

        Accessible attributes:

            stream:
                The stream holding the data of the file - must be a binary
                stream (bytes, not string).

            elfclass:
                32 or 64 - specifies the word size of the target machine

            little_endian:
                boolean - specifies the target machine's endianness

            header:
                the complete ELF file header

            e_ident_raw:
                the raw e_ident field of the header
    """
    def __init__(self, stream):
        self.stream = stream
        self._identify_file()
        self.structs = ELFStructs(
            little_endian=self.little_endian,
            elfclass=self.elfclass)
        self.header = self._parse_elf_header()

        self.stream.seek(0)
        self.e_ident_raw = self.stream.read(16)

        self._file_stringtable_section = self._get_file_stringtable()
        self._section_name_map = None

    def num_sections(self):
        """ Number of sections in the file
        """
        return self['e_shnum']

    def get_section(self, n):
        """ Get the section at index #n from the file (Section object or a
            subclass)
        """
        section_header = self._get_section_header(n)
        return self._make_section(section_header)

    def get_section_by_name(self, name):
        """ Get a section from the file, by name. Return None if no such
            section exists.
        """
        # The first time this method is called, construct a name to number
        # mapping
        #
        if self._section_name_map is None:
            self._section_name_map = {}
            for i, sec in enumerate(self.iter_sections()):
                self._section_name_map[sec.name] = i
        secnum = self._section_name_map.get(name, None)
        return None if secnum is None else self.get_section(secnum)

    def iter_sections(self):
        """ Yield all the sections in the file
        """
        for i in range(self.num_sections()):
            yield self.get_section(i)

    def num_segments(self):
        """ Number of segments in the file
        """
        return self['e_phnum']

    def get_segment(self, n):
        """ Get the segment at index #n from the file (Segment object)
        """
        segment_header = self._get_segment_header(n)
        return self._make_segment(segment_header)

    def iter_segments(self):
        """ Yield all the segments in the file
        """
        for i in range(self.num_segments()):
            yield self.get_segment(i)

    def has_dwarf_info(self):
        """ Check whether this file appears to have debugging information.
            We assume that if it has the debug_info section, it has all theother
            required sections as well.
        """
        return bool(self.get_section_by_name(b'.debug_info'))

    def get_dwarf_info(self, relocate_dwarf_sections=True):
        """ Return a DWARFInfo object representing the debugging information in
            this file.

            If relocate_dwarf_sections is True, relocations for DWARF sections
            are looked up and applied.
        """
        # Expect that has_dwarf_info was called, so at least .debug_info is
        # present.
        # Sections that aren't found will be passed as None to DWARFInfo.
        #
        debug_sections = {}
        for secname in (b'.debug_info', b'.debug_abbrev', b'.debug_str',
                        b'.debug_line', b'.debug_frame',
                        b'.debug_loc', b'.debug_ranges'):
            section = self.get_section_by_name(secname)
            if section is None:
                debug_sections[secname] = None
            else:
                debug_sections[secname] = self._read_dwarf_section(
                    section,
                    relocate_dwarf_sections)

        return DWARFInfo(
                config=DwarfConfig(
                    little_endian=self.little_endian,
                    default_address_size=self.elfclass // 8,
                    machine_arch=self.get_machine_arch()),
                debug_info_sec=debug_sections[b'.debug_info'],
                debug_abbrev_sec=debug_sections[b'.debug_abbrev'],
                debug_frame_sec=debug_sections[b'.debug_frame'],
                # TODO(eliben): reading of eh_frame is not hooked up yet
                eh_frame_sec=None,
                debug_str_sec=debug_sections[b'.debug_str'],
                debug_loc_sec=debug_sections[b'.debug_loc'],
                debug_ranges_sec=debug_sections[b'.debug_ranges'],
                debug_line_sec=debug_sections[b'.debug_line'])

    def get_machine_arch(self):
        """ Return the machine architecture, as detected from the ELF header.
            Not all architectures are supported at the moment.
        """
        if self['e_machine'] == 'EM_X86_64':
            return 'x64'
        elif self['e_machine'] in ('EM_386', 'EM_486'):
            return 'x86'
        elif self['e_machine'] == 'EM_ARM':
            return 'ARM'
        elif self['e_machine'] == 'EM_AARCH64':
            return 'AArch64'
        else:
            return '<unknown>'

    #-------------------------------- PRIVATE --------------------------------#

    def __getitem__(self, name):
        """ Implement dict-like access to header entries
        """
        return self.header[name]

    def _identify_file(self):
        """ Verify the ELF file and identify its class and endianness.
        """
        # Note: this code reads the stream directly, without using ELFStructs,
        # since we don't yet know its exact format. ELF was designed to be
        # read like this - its e_ident field is word-size and endian agnostic.
        #
        self.stream.seek(0)
        magic = self.stream.read(4)
        elf_assert(magic == b'\x7fELF', 'Magic number does not match')

        ei_class = self.stream.read(1)
        if ei_class == b'\x01':
            self.elfclass = 32
        elif ei_class == b'\x02':
            self.elfclass = 64
        else:
            raise ELFError('Invalid EI_CLASS %s' % repr(ei_class))

        ei_data = self.stream.read(1)
        if ei_data == b'\x01':
            self.little_endian = True
        elif ei_data == b'\x02':
            self.little_endian = False
        else:
            raise ELFError('Invalid EI_DATA %s' % repr(ei_data))

    def _section_offset(self, n):
        """ Compute the offset of section #n in the file
        """
        return self['e_shoff'] + n * self['e_shentsize']

    def _segment_offset(self, n):
        """ Compute the offset of segment #n in the file
        """
        return self['e_phoff'] + n * self['e_phentsize']

    def _make_segment(self, segment_header):
        """ Create a Segment object of the appropriate type
        """
        segtype = segment_header['p_type']
        if segtype == 'PT_INTERP':
            return InterpSegment(segment_header, self.stream)
        elif segtype == 'PT_DYNAMIC':
            return DynamicSegment(segment_header, self.stream, self)
        else:
            return Segment(segment_header, self.stream)

    def _get_section_header(self, n):
        """ Find the header of section #n, parse it and return the struct
        """
        return struct_parse(
            self.structs.Elf_Shdr,
            self.stream,
            stream_pos=self._section_offset(n))

    def _get_section_name(self, section_header):
        """ Given a section header, find this section's name in the file's
            string table
        """
        name_offset = section_header['sh_name']
        return self._file_stringtable_section.get_string(name_offset)

    def _make_section(self, section_header):
        """ Create a section object of the appropriate type
        """
        name = self._get_section_name(section_header)
        sectype = section_header['sh_type']

        if sectype == 'SHT_STRTAB':
            return StringTableSection(section_header, name, self.stream)
        elif sectype == 'SHT_NULL':
            return NullSection(section_header, name, self.stream)
        elif sectype in ('SHT_SYMTAB', 'SHT_DYNSYM', 'SHT_SUNW_LDYNSYM'):
            return self._make_symbol_table_section(section_header, name)
        elif sectype == 'SHT_SUNW_syminfo':
            return self._make_sunwsyminfo_table_section(section_header, name)
        elif sectype == 'SHT_GNU_verneed':
            return self._make_gnu_verneed_section(section_header, name)
        elif sectype == 'SHT_GNU_verdef':
            return self._make_gnu_verdef_section(section_header, name)
        elif sectype == 'SHT_GNU_versym':
            return self._make_gnu_versym_section(section_header, name)
        elif sectype in ('SHT_REL', 'SHT_RELA'):
            return RelocationSection(
                section_header, name, self.stream, self)
        elif sectype == 'SHT_DYNAMIC':
            return DynamicSection(section_header, name, self.stream, self)
        else:
            return Section(section_header, name, self.stream)

    def _make_symbol_table_section(self, section_header, name):
        """ Create a SymbolTableSection
        """
        linked_strtab_index = section_header['sh_link']
        strtab_section = self.get_section(linked_strtab_index)
        return SymbolTableSection(
            section_header, name, self.stream,
            elffile=self,
            stringtable=strtab_section)

    def _make_sunwsyminfo_table_section(self, section_header, name):
        """ Create a SUNWSyminfoTableSection
        """
        linked_strtab_index = section_header['sh_link']
        strtab_section = self.get_section(linked_strtab_index)
        return SUNWSyminfoTableSection(
            section_header, name, self.stream,
            elffile=self,
            symboltable=strtab_section)

    def _make_gnu_verneed_section(self, section_header, name):
        """ Create a GNUVerNeedSection
        """
        linked_strtab_index = section_header['sh_link']
        strtab_section = self.get_section(linked_strtab_index)
        return GNUVerNeedSection(
            section_header, name, self.stream,
            elffile=self,
            stringtable=strtab_section)

    def _make_gnu_verdef_section(self, section_header, name):
        """ Create a GNUVerDefSection
        """
        linked_strtab_index = section_header['sh_link']
        strtab_section = self.get_section(linked_strtab_index)
        return GNUVerDefSection(
            section_header, name, self.stream,
            elffile=self,
            stringtable=strtab_section)

    def _make_gnu_versym_section(self, section_header, name):
        """ Create a GNUVerSymSection
        """
        linked_strtab_index = section_header['sh_link']
        strtab_section = self.get_section(linked_strtab_index)
        return GNUVerSymSection(
            section_header, name, self.stream,
            elffile=self,
            symboltable=strtab_section)

    def _get_segment_header(self, n):
        """ Find the header of segment #n, parse it and return the struct
        """
        return struct_parse(
            self.structs.Elf_Phdr,
            self.stream,
            stream_pos=self._segment_offset(n))

    def _get_file_stringtable(self):
        """ Find the file's string table section
        """
        stringtable_section_num = self['e_shstrndx']
        return StringTableSection(
                header=self._get_section_header(stringtable_section_num),
                name='',
                stream=self.stream)

    def _parse_elf_header(self):
        """ Parses the ELF file header and assigns the result to attributes
            of this object.
        """
        return struct_parse(self.structs.Elf_Ehdr, self.stream, stream_pos=0)

    def _read_dwarf_section(self, section, relocate_dwarf_sections):
        """ Read the contents of a DWARF section from the stream and return a
            DebugSectionDescriptor. Apply relocations if asked to.
        """
        self.stream.seek(section['sh_offset'])
        # The section data is read into a new stream, for processing
        section_stream = BytesIO()
        section_stream.write(self.stream.read(section['sh_size']))

        if relocate_dwarf_sections:
            reloc_handler = RelocationHandler(self)
            reloc_section = reloc_handler.find_relocations_for_section(section)
            if reloc_section is not None:
                reloc_handler.apply_section_relocations(
                        section_stream, reloc_section)

        return DebugSectionDescriptor(
                stream=section_stream,
                name=section.name,
                global_offset=section['sh_offset'],
                size=section['sh_size'])



########NEW FILE########
__FILENAME__ = enums
#-------------------------------------------------------------------------------
# elftools: elf/enums.py
#
# Mappings of enum names to values
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
from ..construct import Pass


# e_ident[EI_CLASS] in the ELF header
ENUM_EI_CLASS = dict(
    ELFCLASSNONE=0,
    ELFCLASS32=1,
    ELFCLASS64=2
)

# e_ident[EI_DATA] in the ELF header
ENUM_EI_DATA = dict(
    ELFDATANONE=0,
    ELFDATA2LSB=1,
    ELFDATA2MSB=2
)

# e_version in the ELF header
ENUM_E_VERSION = dict(
    EV_NONE=0,
    EV_CURRENT=1,
    _default_=Pass,
)

# e_ident[EI_OSABI] in the ELF header
ENUM_EI_OSABI = dict(
    ELFOSABI_SYSV=0,
    ELFOSABI_HPUX=1,
    ELFOSABI_NETBSD=2,
    ELFOSABI_LINUX=3,
    ELFOSABI_HURD=4,
    ELFOSABI_SOLARIS=6,
    ELFOSABI_AIX=7,
    ELFOSABI_IRIX=8,
    ELFOSABI_FREEBSD=9,
    ELFOSABI_TRU64=10,
    ELFOSABI_MODESTO=11,
    ELFOSABI_OPENBSD=12,
    ELFOSABI_OPENVMS=13,
    ELFOSABI_NSK=14,
    ELFOSABI_AROS=15,
    ELFOSABI_ARM_AEABI=64,
    ELFOSABI_ARM=97,
    ELFOSABI_STANDALONE=255,
    _default_=Pass,
)

# e_type in the ELF header
ENUM_E_TYPE = dict(
    ET_NONE=0,
    ET_REL=1,
    ET_EXEC=2,
    ET_DYN=3,
    ET_CORE=4,
    ET_LOPROC=0xff00,
    ET_HIPROC=0xffff,
    _default_=Pass,
)

# e_machine in the ELF header
ENUM_E_MACHINE = dict(
    EM_NONE=0,
    EM_M32=1,
    EM_SPARC=2,
    EM_386=3,
    EM_68K=4,
    EM_88K=5,
    EM_860=7,
    EM_MIPS=8,
    EM_S370=9,
    EM_MIPS_RS3_LE=10,
    EM_PARISC=15,
    EM_VPP500=17,
    EM_SPARC32PLUS=18,
    EM_960=19,
    EM_PPC=20,
    EM_PPC64=21,
    EM_S390=22,
    EM_V800=36,
    EM_FR20=37,
    EM_RH32=38,
    EM_RCE=39,
    EM_ARM=40,
    EM_ALPHA=41,
    EM_SH=42,
    EM_SPARCV9=43,
    EM_TRICORE=44,
    EM_ARC=45,
    EM_H8_300=46,
    EM_H8_300H=47,
    EM_H8S=48,
    EM_H8_500=49,
    EM_IA_64=50,
    EM_MIPS_X=51,
    EM_COLDFIRE=52,
    EM_68HC12=53,
    EM_MMA=54,
    EM_PCP=55,
    EM_NCPU=56,
    EM_NDR1=57,
    EM_STARCORE=58,
    EM_ME16=59,
    EM_ST100=60,
    EM_TINYJ=61,
    EM_X86_64=62,
    EM_PDSP=63,
    EM_PDP10=64,
    EM_PDP11=65,
    EM_FX66=66,
    EM_ST9PLUS=67,
    EM_ST7=68,
    EM_68HC16=69,
    EM_68HC11=70,
    EM_68HC08=71,
    EM_68HC05=72,
    EM_SVX=73,
    EM_ST19=74,
    EM_VAX=75,
    EM_CRIS=76,
    EM_JAVELIN=77,
    EM_FIREPATH=78,
    EM_ZSP=79,
    EM_MMIX=80,
    EM_HUANY=81,
    EM_PRISM=82,
    EM_AVR=83,
    EM_FR30=84,
    EM_D10V=85,
    EM_D30V=86,
    EM_V850=87,
    EM_M32R=88,
    EM_MN10300=89,
    EM_MN10200=90,
    EM_PJ=91,
    EM_OPENRISC=92,
    EM_ARC_A5=93,
    EM_XTENSA=94,
    EM_VIDEOCORE=95,
    EM_TMM_GPP=96,
    EM_NS32K=97,
    EM_TPC=98,
    EM_SNP1K=99,
    EM_ST200=100,
    EM_IP2K=101,
    EM_MAX=102,
    EM_CR=103,
    EM_F2MC16=104,
    EM_MSP430=105,
    EM_BLACKFIN=106,
    EM_SE_C33=107,
    EM_SEP=108,
    EM_ARCA=109,
    EM_UNICORE=110,
    EM_L10M=180,
    EM_AARCH64=183,
    _default_=Pass,
)

# sh_type in the section header
ENUM_SH_TYPE = dict(
    SHT_NULL=0,
    SHT_PROGBITS=1,
    SHT_SYMTAB=2,
    SHT_STRTAB=3,
    SHT_RELA=4,
    SHT_HASH=5,
    SHT_DYNAMIC=6,
    SHT_NOTE=7,
    SHT_NOBITS=8,
    SHT_REL=9,
    SHT_SHLIB=10,
    SHT_DYNSYM=11,
    SHT_INIT_ARRAY=14,
    SHT_FINI_ARRAY=15,
    SHT_PREINIT_ARRAY=16,
    SHT_GROUP=17,
    SHT_SYMTAB_SHNDX=18,
    SHT_NUM=19,
    SHT_LOOS=0x60000000,
    SHT_GNU_HASH=0x6ffffff6,
    SHT_GNU_verdef=0x6ffffffd,  # also SHT_SUNW_verdef
    SHT_GNU_verneed=0x6ffffffe, # also SHT_SUNW_verneed
    SHT_GNU_versym=0x6fffffff,  # also SHT_SUNW_versym
    SHT_LOPROC=0x70000000,
    SHT_HIPROC=0x7fffffff,
    SHT_LOUSER=0x80000000,
    SHT_HIUSER=0xffffffff,
    SHT_AMD64_UNWIND=0x70000001,
    SHT_SUNW_LDYNSYM=0x6ffffff3,
    SHT_SUNW_syminfo=0x6ffffffc,
    SHT_ARM_EXIDX=0x70000001,
    SHT_ARM_PREEMPTMAP=0x70000002,
    SHT_ARM_ATTRIBUTES=0x70000003,
    SHT_ARM_DEBUGOVERLAY=0x70000004,
    _default_=Pass,
)

# p_type in the program header
# some values scavenged from the ELF headers in binutils-2.21
ENUM_P_TYPE = dict(
    PT_NULL=0,
    PT_LOAD=1,
    PT_DYNAMIC=2,
    PT_INTERP=3,
    PT_NOTE=4,
    PT_SHLIB=5,
    PT_PHDR=6,
    PT_TLS=7,
    PT_LOPROC=0x70000000,
    PT_HIPROC=0x7fffffff,
    PT_GNU_EH_FRAME=0x6474e550,
    PT_GNU_STACK=0x6474e551,
    PT_GNU_RELRO=0x6474e552,
    PT_ARM_ARCHEXT=0x70000000,
    PT_ARM_EXIDX=0x70000001,
    PT_ARM_UNWIND=0x70000001,
    PT_AARCH64_ARCHEXT=0x70000000,
    PT_AARCH64_UNWIND=0x70000001,
    _default_=Pass,
)

# st_info bindings in the symbol header
ENUM_ST_INFO_BIND = dict(
    STB_LOCAL=0,
    STB_GLOBAL=1,
    STB_WEAK=2,
    STB_NUM=3,
    STB_LOOS=10,
    STB_HIOS=12,
    STB_LOPROC=13,
    STB_HIPROC=15,
    _default_=Pass,
)

# st_info type in the symbol header
ENUM_ST_INFO_TYPE = dict(
    STT_NOTYPE=0,
    STT_OBJECT=1,
    STT_FUNC=2,
    STT_SECTION=3,
    STT_FILE=4,
    STT_COMMON=5,
    STT_TLS=6,
    STT_NUM=7,
    STT_RELC=8,
    STT_SRELC=9,
    STT_LOOS=10,
    STT_HIOS=12,
    STT_LOPROC=13,
    STT_HIPROC=15,
    _default_=Pass,
)

# visibility from st_other
ENUM_ST_VISIBILITY = dict(
    STV_DEFAULT=0,
    STV_INTERNAL=1,
    STV_HIDDEN=2,
    STV_PROTECTED=3,
    STV_EXPORTED=4,
    STV_SINGLETON=5,
    STV_ELIMINATE=6,
    _default_=Pass,
)

# st_shndx
ENUM_ST_SHNDX = dict(
    SHN_UNDEF=0,
    SHN_ABS=0xfff1,
    SHN_COMMON=0xfff2,
    _default_=Pass,
)

# d_tag
ENUM_D_TAG = dict(
    DT_NULL=0,
    DT_NEEDED=1,
    DT_PLTRELSZ=2,
    DT_PLTGOT=3,
    DT_HASH=4,
    DT_STRTAB=5,
    DT_SYMTAB=6,
    DT_RELA=7,
    DT_RELASZ=8,
    DT_RELAENT=9,
    DT_STRSZ=10,
    DT_SYMENT=11,
    DT_INIT=12,
    DT_FINI=13,
    DT_SONAME=14,
    DT_RPATH=15,
    DT_SYMBOLIC=16,
    DT_REL=17,
    DT_RELSZ=18,
    DT_RELENT=19,
    DT_PLTREL=20,
    DT_DEBUG=21,
    DT_TEXTREL=22,
    DT_JMPREL=23,
    DT_BIND_NOW=24,
    DT_INIT_ARRAY=25,
    DT_FINI_ARRAY=26,
    DT_INIT_ARRAYSZ=27,
    DT_FINI_ARRAYSZ=28,
    DT_RUNPATH=29,
    DT_FLAGS=30,
    DT_ENCODING=32,
    DT_PREINIT_ARRAY=32,
    DT_PREINIT_ARRAYSZ=33,
    DT_NUM=34,
    DT_LOOS=0x6000000d,
    DT_SUNW_AUXILIARY=0x6000000d,
    DT_SUNW_RTLDINF=0x6000000e,
    DT_SUNW_FILTER=0x6000000f,
    DT_SUNW_CAP=0x60000010,
    DT_SUNW_SYMTAB=0x60000011,
    DT_SUNW_SYMSZ=0x60000012,
    DT_SUNW_ENCODING=0x60000013,
    DT_SUNW_SORTENT=0x60000013,
    DT_SUNW_SYMSORT=0x60000014,
    DT_SUNW_SYMSORTSZ=0x60000015,
    DT_SUNW_TLSSORT=0x60000016,
    DT_SUNW_TLSSORTSZ=0x60000017,
    DT_SUNW_CAPINFO=0x60000018,
    DT_SUNW_STRPAD=0x60000019,
    DT_SUNW_CAPCHAIN=0x6000001a,
    DT_SUNW_LDMACH=0x6000001b,
    DT_SUNW_CAPCHAINENT=0x6000001d,
    DT_SUNW_CAPCHAINSZ=0x6000001f,
    DT_HIOS=0x6ffff000,
    DT_LOPROC=0x70000000,
    DT_HIPROC=0x7fffffff,
    DT_PROCNUM=0x35,
    DT_VALRNGLO=0x6ffffd00,
    DT_GNU_PRELINKED=0x6ffffdf5,
    DT_GNU_CONFLICTSZ=0x6ffffdf6,
    DT_GNU_LIBLISTSZ=0x6ffffdf7,
    DT_CHECKSUM=0x6ffffdf8,
    DT_PLTPADSZ=0x6ffffdf9,
    DT_MOVEENT=0x6ffffdfa,
    DT_MOVESZ=0x6ffffdfb,
    DT_SYMINSZ=0x6ffffdfe,
    DT_SYMINENT=0x6ffffdff,
    DT_GNU_HASH=0x6ffffef5,
    DT_TLSDESC_PLT=0x6ffffef6,
    DT_TLSDESC_GOT=0x6ffffef7,
    DT_GNU_CONFLICT=0x6ffffef8,
    DT_GNU_LIBLIST=0x6ffffef9,
    DT_CONFIG=0x6ffffefa,
    DT_DEPAUDIT=0x6ffffefb,
    DT_AUDIT=0x6ffffefc,
    DT_PLTPAD=0x6ffffefd,
    DT_MOVETAB=0x6ffffefe,
    DT_SYMINFO=0x6ffffeff,
    DT_VERSYM=0x6ffffff0,
    DT_RELACOUNT=0x6ffffff9,
    DT_RELCOUNT=0x6ffffffa,
    DT_FLAGS_1=0x6ffffffb,
    DT_VERDEF=0x6ffffffc,
    DT_VERDEFNUM=0x6ffffffd,
    DT_VERNEED=0x6ffffffe,
    DT_VERNEEDNUM=0x6fffffff,
    DT_AUXILIARY=0x7ffffffd,
    DT_FILTER=0x7fffffff,
    _default_=Pass,
)

ENUM_RELOC_TYPE_i386 = dict(
    R_386_NONE=0,
    R_386_32=1,
    R_386_PC32=2,
    R_386_GOT32=3,
    R_386_PLT32=4,
    R_386_COPY=5,
    R_386_GLOB_DAT=6,
    R_386_JUMP_SLOT=7,
    R_386_RELATIVE=8,
    R_386_GOTOFF=9,
    R_386_GOTPC=10,
    R_386_32PLT=11,
    R_386_TLS_TPOFF=14,
    R_386_TLS_IE=15,
    R_386_TLS_GOTIE=16,
    R_386_TLS_LE=17,
    R_386_TLS_GD=18,
    R_386_TLS_LDM=19,
    R_386_16=20,
    R_386_PC16=21,
    R_386_8=22,
    R_386_PC8=23,
    R_386_TLS_GD_32=24,
    R_386_TLS_GD_PUSH=25,
    R_386_TLS_GD_CALL=26,
    R_386_TLS_GD_POP=27,
    R_386_TLS_LDM_32=28,
    R_386_TLS_LDM_PUSH=29,
    R_386_TLS_LDM_CALL=30,
    R_386_TLS_LDM_POP=31,
    R_386_TLS_LDO_32=32,
    R_386_TLS_IE_32=33,
    R_386_TLS_LE_32=34,
    R_386_TLS_DTPMOD32=35,
    R_386_TLS_DTPOFF32=36,
    R_386_TLS_TPOFF32=37,
    R_386_TLS_GOTDESC=39,
    R_386_TLS_DESC_CALL=40,
    R_386_TLS_DESC=41,
    R_386_IRELATIVE=42,
    R_386_USED_BY_INTEL_200=200,
    R_386_GNU_VTINHERIT=250,
    R_386_GNU_VTENTRY=251,
    _default_=Pass,
)

ENUM_RELOC_TYPE_x64 = dict(
    R_X86_64_NONE=0,
    R_X86_64_64=1,
    R_X86_64_PC32=2,
    R_X86_64_GOT32=3,
    R_X86_64_PLT32=4,
    R_X86_64_COPY=5,
    R_X86_64_GLOB_DAT=6,
    R_X86_64_JUMP_SLOT=7,
    R_X86_64_RELATIVE=8,
    R_X86_64_GOTPCREL=9,
    R_X86_64_32=10,
    R_X86_64_32S=11,
    R_X86_64_16=12,
    R_X86_64_PC16=13,
    R_X86_64_8=14,
    R_X86_64_PC8=15,
    R_X86_64_DTPMOD64=16,
    R_X86_64_DTPOFF64=17,
    R_X86_64_TPOFF64=18,
    R_X86_64_TLSGD=19,
    R_X86_64_TLSLD=20,
    R_X86_64_DTPOFF32=21,
    R_X86_64_GOTTPOFF=22,
    R_X86_64_TPOFF32=23,
    R_X86_64_PC64=24,
    R_X86_64_GOTOFF64=25,
    R_X86_64_GOTPC32=26,
    R_X86_64_GOT64=27,
    R_X86_64_GOTPCREL64=28,
    R_X86_64_GOTPC64=29,
    R_X86_64_GOTPLT64=30,
    R_X86_64_PLTOFF64=31,
    R_X86_64_GOTPC32_TLSDESC=34,
    R_X86_64_TLSDESC_CALL=35,
    R_X86_64_TLSDESC=36,
    R_X86_64_IRELATIVE=37,
    R_X86_64_GNU_VTINHERIT=250,
    R_X86_64_GNU_VTENTRY=251,
    _default_=Pass,
)

# Sunw Syminfo Bound To special values
ENUM_SUNW_SYMINFO_BOUNDTO = dict(
    SYMINFO_BT_SELF=0xffff,
    SYMINFO_BT_PARENT=0xfffe,
    SYMINFO_BT_NONE=0xfffd,
    SYMINFO_BT_EXTERN=0xfffc,
    _default_=Pass,
)

# Versym section, version dependency index
ENUM_VERSYM = dict(
    VER_NDX_LOCAL=0,
    VER_NDX_GLOBAL=1,
    VER_NDX_LORESERVE=0xff00,
    VER_NDX_ELIMINATE=0xff01,
    _default_=Pass,
)
# Sunw Syminfo Bound To special values
ENUM_SUNW_SYMINFO_BOUNDTO = dict(
    SYMINFO_BT_SELF=0xffff,
    SYMINFO_BT_PARENT=0xfffe,
    SYMINFO_BT_NONE=0xfffd,
    SYMINFO_BT_EXTERN=0xfffc,
    _default_=Pass,
)

ENUM_RELOC_TYPE_ARM = dict(
    R_ARM_NONE=0,
    R_ARM_PC24=1,
    R_ARM_ABS32=2,
    R_ARM_REL32=3,
    R_ARM_LDR_PC_G0=4,
    R_ARM_ABS16=5,
    R_ARM_ABS12=6,
    R_ARM_THM_ABS5=7,
    R_ARM_ABS8=8,
    R_ARM_SBREL32=9,
    R_ARM_THM_CALL=10,
    R_ARM_THM_PC8=11,
    R_ARM_BREL_ADJ=12,
    R_ARM_SWI24=13,
    R_ARM_THM_SWI8=14,
    R_ARM_XPC25=15,
    R_ARM_THM_XPC22=16,
    R_ARM_TLS_DTPMOD32=17,
    R_ARM_TLS_DTPOFF32=18,
    R_ARM_TLS_TPOFF32=19,
    R_ARM_COPY=20,
    R_ARM_GLOB_DAT=21,
    R_ARM_JUMP_SLOT=22,
    R_ARM_RELATIVE=23,
    R_ARM_GOTOFF32=24,
    R_ARM_BASE_PREL=25,
    R_ARM_GOT_BREL=26,
    R_ARM_PLT32=27,
    R_ARM_CALL=28,
    R_ARM_JUMP24=29,
    R_ARM_THM_JUMP24=30,
    R_ARM_BASE_ABS=31,
    R_ARM_ALU_PCREL_7_0=32,
    R_ARM_ALU_PCREL_15_8=33,
    R_ARM_ALU_PCREL_23_15=34,
    R_ARM_LDR_SBREL_11_0_NC=35,
    R_ARM_ALU_SBREL_19_12_NC=36,
    R_ARM_ALU_SBREL_27_20_CK=37,
    R_ARM_TARGET1=38,
    R_ARM_SBREL31=39,
    R_ARM_V4BX=40,
    R_ARM_TARGET2=41,
    R_ARM_PREL31=42,
    R_ARM_MOVW_ABS_NC=43,
    R_ARM_MOVT_ABS=44,
    R_ARM_MOVW_PREL_NC=45,
    R_ARM_MOVT_PREL=46,
    R_ARM_THM_MOVW_ABS_NC=47,
    R_ARM_THM_MOVT_ABS=48,
    R_ARM_THM_MOVW_PREL_NC=49,
    R_ARM_THM_MOVT_PREL=50,
    R_ARM_THM_JUMP19=51,
    R_ARM_THM_JUMP6=52,
    R_ARM_THM_ALU_PREL_11_0=53,
    R_ARM_THM_PC12=54,
    R_ARM_ABS32_NOI=55,
    R_ARM_REL32_NOI=56,
    R_ARM_ALU_PC_G0_NC=57,
    R_ARM_ALU_PC_G0=58,
    R_ARM_ALU_PC_G1_NC=59,
    R_ARM_ALU_PC_G1=60,
    R_ARM_ALU_PC_G2=61,
    R_ARM_LDR_PC_G1=62,
    R_ARM_LDR_PC_G2=63,
    R_ARM_LDRS_PC_G0=64,
    R_ARM_LDRS_PC_G1=65,
    R_ARM_LDRS_PC_G2=66,
    R_ARM_LDC_PC_G0=67,
    R_ARM_LDC_PC_G1=68,
    R_ARM_LDC_PC_G2=69,
    R_ARM_ALU_SB_G0_NC=70,
    R_ARM_ALU_SB_G0=71,
    R_ARM_ALU_SB_G1_NC=72,
    R_ARM_ALU_SB_G1=73,
    R_ARM_ALU_SB_G2=74,
    R_ARM_LDR_SB_G0=75,
    R_ARM_LDR_SB_G1=76,
    R_ARM_LDR_SB_G2=77,
    R_ARM_LDRS_SB_G0=78,
    R_ARM_LDRS_SB_G1=79,
    R_ARM_LDRS_SB_G2=80,
    R_ARM_LDC_SB_G0=81,
    R_ARM_LDC_SB_G1=82,
    R_ARM_LDC_SB_G2=83,
    R_ARM_MOVW_BREL_NC=84,
    R_ARM_MOVT_BREL=85,
    R_ARM_MOVW_BREL=86,
    R_ARM_THM_MOVW_BREL_NC=87,
    R_ARM_THM_MOVT_BREL=88,
    R_ARM_THM_MOVW_BREL=89,
    R_ARM_PLT32_ABS=94,
    R_ARM_GOT_ABS=95,
    R_ARM_GOT_PREL=96,
    R_ARM_GOT_BREL12=97,
    R_ARM_GOTOFF12=98,
    R_ARM_GOTRELAX=99,
    R_ARM_GNU_VTENTRY=100,
    R_ARM_GNU_VTINHERIT=101,
    R_ARM_THM_JUMP11=102,
    R_ARM_THM_JUMP8=103,
    R_ARM_TLS_GD32=104,
    R_ARM_TLS_LDM32=105,
    R_ARM_TLS_LDO32=106,
    R_ARM_TLS_IE32=107,
    R_ARM_TLS_LE32=108,
    R_ARM_TLS_LDO12=109,
    R_ARM_TLS_LE12=110,
    R_ARM_TLS_IE12GP=111,
    R_ARM_PRIVATE_0=112,
    R_ARM_PRIVATE_1=113,
    R_ARM_PRIVATE_2=114,
    R_ARM_PRIVATE_3=115,
    R_ARM_PRIVATE_4=116,
    R_ARM_PRIVATE_5=117,
    R_ARM_PRIVATE_6=118,
    R_ARM_PRIVATE_7=119,
    R_ARM_PRIVATE_8=120,
    R_ARM_PRIVATE_9=121,
    R_ARM_PRIVATE_10=122,
    R_ARM_PRIVATE_11=123,
    R_ARM_PRIVATE_12=124,
    R_ARM_PRIVATE_13=125,
    R_ARM_PRIVATE_14=126,
    R_ARM_PRIVATE_15=127,
    R_ARM_ME_TOO=128,
    R_ARM_THM_TLS_DESCSEQ16=129,
    R_ARM_THM_TLS_DESCSEQ32=130,
    R_ARM_THM_GOT_BREL12=131,
    R_ARM_IRELATIVE=140,
)

ENUM_RELOC_TYPE_AARCH64 = dict(
    R_AARCH64_NONE=256,
    R_AARCH64_ABS64=257,
    R_AARCH64_ABS32=258,
    R_AARCH64_ABS16=259,
    R_AARCH64_PREL64=260,
    R_AARCH64_PREL32=261,
    R_AARCH64_PREL16=262,
    R_AARCH64_MOVW_UABS_G0=263,
    R_AARCH64_MOVW_UABS_G0_NC=264,
    R_AARCH64_MOVW_UABS_G1=265,
    R_AARCH64_MOVW_UABS_G1_NC=266,
    R_AARCH64_MOVW_UABS_G2=267,
    R_AARCH64_MOVW_UABS_G2_NC=268,
    R_AARCH64_MOVW_UABS_G3=269,
    R_AARCH64_MOVW_SABS_G0=270,
    R_AARCH64_MOVW_SABS_G1=271,
    R_AARCH64_MOVW_SABS_G2=272,
    R_AARCH64_LD_PREL_LO19=273,
    R_AARCH64_ADR_PREL_LO21=274,
    R_AARCH64_ADR_PREL_PG_HI21=275,
    R_AARCH64_ADR_PREL_PG_HI21_NC=276,
    R_AARCH64_ADD_ABS_LO12_NC=277,
    R_AARCH64_LDST8_ABS_LO12_NC=278,
    R_AARCH64_TSTBR14=279,
    R_AARCH64_CONDBR19=280,
    R_AARCH64_JUMP26=282,
    R_AARCH64_CALL26=283,
    R_AARCH64_LDST16_ABS_LO12_NC=284,
    R_AARCH64_LDST32_ABS_LO12_NC=285,
    R_AARCH64_LDST64_ABS_LO12_NC=286,
    R_AARCH64_MOVW_PREL_G0=287,
    R_AARCH64_MOVW_PREL_G0_NC=288,
    R_AARCH64_MOVW_PREL_G1=289,
    R_AARCH64_MOVW_PREL_G1_NC=290,
    R_AARCH64_MOVW_PREL_G2=291,
    R_AARCH64_MOVW_PREL_G2_NC=292,
    R_AARCH64_MOVW_PREL_G3=293,
    R_AARCH64_MOVW_GOTOFF_G0=300,
    R_AARCH64_MOVW_GOTOFF_G0_NC=301,
    R_AARCH64_MOVW_GOTOFF_G1=302,
    R_AARCH64_MOVW_GOTOFF_G1_NC=303,
    R_AARCH64_MOVW_GOTOFF_G2=304,
    R_AARCH64_MOVW_GOTOFF_G2_NC=305,
    R_AARCH64_MOVW_GOTOFF_G3=306,
    R_AARCH64_GOTREL64=307,
    R_AARCH64_GOTREL32=308,
    R_AARCH64_GOT_LD_PREL19=309,
    R_AARCH64_LD64_GOTOFF_LO15=310,
    R_AARCH64_ADR_GOT_PAGE=311,
    R_AARCH64_LD64_GOT_LO12_NC=312,
    R_AARCH64_TLSGD_ADR_PREL21=512,
    R_AARCH64_TLSGD_ADR_PAGE21=513,
    R_AARCH64_TLSGD_ADD_LO12_NC=514,
    R_AARCH64_TLSGD_MOVW_G1=515,
    R_AARCH64_TLSGD_MOVW_G0_NC=516,
    R_AARCH64_TLSLD_ADR_PREL21=517,
    R_AARCH64_TLSLD_ADR_PAGE21=518,
    R_AARCH64_TLSLD_ADD_LO12_NC=519,
    R_AARCH64_TLSLD_MOVW_G1=520,
    R_AARCH64_TLSLD_MOVW_G0_NC=521,
    R_AARCH64_TLSLD_LD_PREL19=522,
    R_AARCH64_TLSLD_MOVW_DTPREL_G2=523,
    R_AARCH64_TLSLD_MOVW_DTPREL_G1=524,
    R_AARCH64_TLSLD_MOVW_DTPREL_G1_NC=525,
    R_AARCH64_TLSLD_MOVW_DTPREL_G0=526,
    R_AARCH64_TLSLD_MOVW_DTPREL_G0_NC=527,
    R_AARCH64_TLSLD_ADD_DTPREL_HI12=528,
    R_AARCH64_TLSLD_ADD_DTPREL_LO12=529,
    R_AARCH64_TLSLD_ADD_DTPREL_LO12_NC=530,
    R_AARCH64_TLSLD_LDST8_DTPREL_LO12=531,
    R_AARCH64_TLSLD_LDST8_DTPREL_LO12_NC=532,
    R_AARCH64_TLSLD_LDST16_DTPREL_LO12=533,
    R_AARCH64_TLSLD_LDST16_DTPREL_LO12_NC=534,
    R_AARCH64_TLSLD_LDST32_DTPREL_LO12=535,
    R_AARCH64_TLSLD_LDST32_DTPREL_LO12_NC=536,
    R_AARCH64_TLSLD_LDST64_DTPREL_LO12=537,
    R_AARCH64_TLSLD_LDST64_DTPREL_LO12_NC=538,
    R_AARCH64_TLSIE_MOVW_GOTTPREL_G1=539,
    R_AARCH64_TLSIE_MOVW_GOTTPREL_G0_NC=540,
    R_AARCH64_TLSIE_ADR_GOTTPREL_PAGE21=541,
    R_AARCH64_TLSIE_LD64_GOTTPREL_LO12_NC=542,
    R_AARCH64_TLSIE_LD_GOTTPREL_PREL19=543,
    R_AARCH64_TLSLE_MOVW_TPREL_G2=544,
    R_AARCH64_TLSLE_MOVW_TPREL_G1=545,
    R_AARCH64_TLSLE_MOVW_TPREL_G1_NC=546,
    R_AARCH64_TLSLE_MOVW_TPREL_G0=547,
    R_AARCH64_TLSLE_MOVW_TPREL_G0_NC=548,
    R_AARCH64_TLSLE_ADD_TPREL_HI12=549,
    R_AARCH64_TLSLE_ADD_TPREL_LO12=550,
    R_AARCH64_TLSLE_ADD_TPREL_LO12_NC=551,
    R_AARCH64_TLSLE_LDST8_TPREL_LO12=552,
    R_AARCH64_TLSLE_LDST8_TPREL_LO12_NC=553,
    R_AARCH64_TLSLE_LDST16_TPREL_LO12=554,
    R_AARCH64_TLSLE_LDST16_TPREL_LO12_NC=555,
    R_AARCH64_TLSLE_LDST32_TPREL_LO12=556,
    R_AARCH64_TLSLE_LDST32_TPREL_LO12_NC=557,
    R_AARCH64_TLSLE_LDST64_TPREL_LO12=558,
    R_AARCH64_TLSLE_LDST64_TPREL_LO12_NC=559,
    R_AARCH64_COPY=1024,
    R_AARCH64_GLOB_DAT=1025,
    R_AARCH64_JUMP_SLOT=1026,
    R_AARCH64_RELATIVE=1027,
    R_AARCH64_TLS_DTPREL64=1028,
    R_AARCH64_TLS_DTPMOD64=1029,
    R_AARCH64_TLS_TPREL64=1030,
    R_AARCH64_TLS_DTPREL32=1031,
    R_AARCH64_TLS_DTPMOD32=1032,
    R_AARCH64_TLS_TPREL32=1033,
)

########NEW FILE########
__FILENAME__ = gnuversions
#------------------------------------------------------------------------------
# elftools: elf/gnuversions.py
#
# ELF sections
#
# Yann Rouillard (yann@pleiades.fr.eu.org)
# This code is in the public domain
#------------------------------------------------------------------------------
from ..construct import CString
from ..common.utils import struct_parse, elf_assert
from .sections import Section, Symbol


class Version(object):
    """ Version object - representing a version definition or dependency
        entry from a "Version Needed" or a "Version Dependency" table section.

        This kind of entry contains a pointer to an array of auxiliary entries
        that store the information about version names or dependencies.
        These entries are not stored in this object and should be accessed
        through the appropriate method of a section object which will return
        an iterator of VersionAuxiliary objects.

        Similarly to Section objects, allows dictionary-like access to
        verdef/verneed entry
    """
    def __init__(self, entry, name=None):
        self.entry = entry
        self.name = name

    def __getitem__(self, name):
        """ Implement dict-like access to entry
        """
        return self.entry[name]


class VersionAuxiliary(object):
    """ Version Auxiliary object - representing an auxiliary entry of a version
        definition or dependency entry

        Similarly to Section objects, allows dictionary-like access to the
        verdaux/vernaux entry
    """
    def __init__(self, entry, name):
        self.entry = entry
        self.name = name

    def __getitem__(self, name):
        """ Implement dict-like access to entries
        """
        return self.entry[name]


class GNUVersionSection(Section):
    """ Common ancestor class for ELF SUNW|GNU Version Needed/Dependency
        sections class which contains shareable code
    """

    def __init__(self, header, name, stream, elffile, stringtable,
                 field_prefix, version_struct, version_auxiliaries_struct):
        super(GNUVersionSection, self).__init__(header, name, stream)
        self.elffile = elffile
        self.stringtable = stringtable
        self.field_prefix = field_prefix
        self.version_struct = version_struct
        self.version_auxiliaries_struct = version_auxiliaries_struct

    def num_versions(self):
        """ Number of version entries in the section
        """
        return self['sh_info']

    def _field_name(self, name, auxiliary=False):
        """ Return the real field's name of version or a version auxiliary
            entry
        """
        middle = 'a_' if auxiliary else '_'
        return self.field_prefix + middle + name

    def _iter_version_auxiliaries(self, entry_offset, count):
        """ Yield all auxiliary entries of a version entry
        """
        name_field = self._field_name('name', auxiliary=True)
        next_field = self._field_name('next', auxiliary=True)

        for _ in range(count):
            entry = struct_parse(
                        self.version_auxiliaries_struct,
                        self.stream,
                        stream_pos=entry_offset)

            name = self.stringtable.get_string(entry[name_field])
            version_aux = VersionAuxiliary(entry, name)
            yield version_aux

            entry_offset += entry[next_field]

    def iter_versions(self):
        """ Yield all the version entries in the section
            Each time it returns the main version structure
            and an iterator to walk through its auxiliaries entries
        """
        aux_field = self._field_name('aux')
        count_field = self._field_name('cnt')
        next_field = self._field_name('next')

        entry_offset = self['sh_offset']
        for _ in range(self.num_versions()):
            entry = struct_parse(
                self.version_struct,
                self.stream,
                stream_pos=entry_offset)

            elf_assert(entry[count_field] > 0,
                'Expected number of version auxiliary entries (%s) to be > 0'
                'for the following version entry: %s' % (
                    count_field, str(entry)))

            version = Version(entry)
            aux_entries_offset = entry_offset + entry[aux_field]
            version_auxiliaries_iter = self._iter_version_auxiliaries(
                    aux_entries_offset, entry[count_field])

            yield version, version_auxiliaries_iter

            entry_offset += entry[next_field]


class GNUVerNeedSection(GNUVersionSection):
    """ ELF SUNW or GNU Version Needed table section.
        Has an associated StringTableSection that's passed in the constructor.
    """
    def __init__(self, header, name, stream, elffile, stringtable):
        super(GNUVerNeedSection, self).__init__(
                header, name, stream, elffile, stringtable, 'vn',
                elffile.structs.Elf_Verneed, elffile.structs.Elf_Vernaux)
        self._has_indexes = None

    def has_indexes(self):
        """ Return True if at least one version definition entry has an index
            that is stored in the vna_other field.
            This information is used for symbol versioning
        """
        if self._has_indexes is None:
            self._has_indexes = False
            for _, vernaux_iter in self.iter_versions():
                for vernaux in vernaux_iter:
                    if vernaux['vna_other']:
                        self._has_indexes = True
                        break

        return self._has_indexes

    def iter_versions(self):
        for verneed, vernaux in super(GNUVerNeedSection, self).iter_versions():
            verneed.name = self.stringtable.get_string(verneed['vn_file'])
            yield verneed, vernaux

    def get_version(self, index):
        """ Get the version information located at index #n in the table
            Return boths the verneed structure and the vernaux structure
            that contains the name of the version
        """
        for verneed, vernaux_iter in self.iter_versions():
            for vernaux in vernaux_iter:
                if vernaux['vna_other'] == index:
                    return verneed, vernaux

        return None


class GNUVerDefSection(GNUVersionSection):
    """ ELF SUNW or GNU Version Definition table section.
        Has an associated StringTableSection that's passed in the constructor.
    """
    def __init__(self, header, name, stream, elffile, stringtable):
        super(GNUVerDefSection, self).__init__(
                header, name, stream, elffile, stringtable, 'vd',
                elffile.structs.Elf_Verdef, elffile.structs.Elf_Verdaux)

    def get_version(self, index):
        """ Get the version information located at index #n in the table
            Return boths the verdef structure and an iterator to retrieve
            both the version names and dependencies in the form of
            verdaux entries
        """
        for verdef, verdaux_iter in self.iter_versions():
            if verdef['vd_ndx'] == index:
                return verdef, verdaux_iter

        return None


class GNUVerSymSection(Section):
    """ ELF SUNW or GNU Versym table section.
        Has an associated SymbolTableSection that's passed in the constructor.
    """
    def __init__(self, header, name, stream, elffile, symboltable):
        super(GNUVerSymSection, self).__init__(header, name, stream)
        self.elffile = elffile
        self.elfstructs = self.elffile.structs
        self.symboltable = symboltable

    def num_symbols(self):
        """ Number of symbols in the table
        """
        return self['sh_size'] // self['sh_entsize']

    def get_symbol(self, n):
        """ Get the symbol at index #n from the table (Symbol object)
            It begins at 1 and not 0 since the first entry is used to
            store the current version of the syminfo table
        """
        # Grab the symbol's entry from the stream
        entry_offset = self['sh_offset'] + n * self['sh_entsize']
        entry = struct_parse(
            self.elfstructs.Elf_Versym,
            self.stream,
            stream_pos=entry_offset)
        # Find the symbol name in the associated symbol table
        name = self.symboltable.get_symbol(n).name
        return Symbol(entry, name)

    def iter_symbols(self):
        """ Yield all the symbols in the table
        """
        for i in range(self.num_symbols()):
            yield self.get_symbol(i)

########NEW FILE########
__FILENAME__ = relocation
#-------------------------------------------------------------------------------
# elftools: elf/relocation.py
#
# ELF relocations
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
from collections import namedtuple

from ..common.exceptions import ELFRelocationError
from ..common.utils import elf_assert, struct_parse
from .sections import Section
from .enums import ENUM_RELOC_TYPE_i386, ENUM_RELOC_TYPE_x64


class Relocation(object):
    """ Relocation object - representing a single relocation entry. Allows
        dictionary-like access to the entry's fields.

        Can be either a REL or RELA relocation.
    """
    def __init__(self, entry, elffile):
        self.entry = entry
        self.elffile = elffile

    def is_RELA(self):
        """ Is this a RELA relocation? If not, it's REL.
        """
        return 'r_addend' in self.entry

    def __getitem__(self, name):
        """ Dict-like access to entries
        """
        return self.entry[name]

    def __repr__(self):
        return '<Relocation (%s): %s>' % (
                'RELA' if self.is_RELA() else 'REL',
                self.entry)

    def __str__(self):
        return self.__repr__()


class RelocationSection(Section):
    """ ELF relocation section. Serves as a collection of Relocation entries.
    """
    def __init__(self, header, name, stream, elffile):
        super(RelocationSection, self).__init__(header, name, stream)
        self.elffile = elffile
        self.elfstructs = self.elffile.structs
        if self.header['sh_type'] == 'SHT_REL':
            expected_size = self.elfstructs.Elf_Rel.sizeof()
            self.entry_struct = self.elfstructs.Elf_Rel
        elif self.header['sh_type'] == 'SHT_RELA':
            expected_size = self.elfstructs.Elf_Rela.sizeof()
            self.entry_struct = self.elfstructs.Elf_Rela
        else:
            elf_assert(False, 'Unknown relocation type section')

        elf_assert(
            self.header['sh_entsize'] == expected_size,
            'Expected sh_entsize of SHT_REL section to be %s' % expected_size)

    def is_RELA(self):
        """ Is this a RELA relocation section? If not, it's REL.
        """
        return self.header['sh_type'] == 'SHT_RELA'

    def num_relocations(self):
        """ Number of relocations in the section
        """
        return self['sh_size'] // self['sh_entsize']

    def get_relocation(self, n):
        """ Get the relocation at index #n from the section (Relocation object)
        """
        entry_offset = self['sh_offset'] + n * self['sh_entsize']
        entry = struct_parse(
            self.entry_struct,
            self.stream,
            stream_pos=entry_offset)
        return Relocation(entry, self.elffile)

    def iter_relocations(self):
        """ Yield all the relocations in the section
        """
        for i in range(self.num_relocations()):
            yield self.get_relocation(i)


class RelocationHandler(object):
    """ Handles the logic of relocations in ELF files.
    """
    def __init__(self, elffile):
        self.elffile = elffile

    def find_relocations_for_section(self, section):
        """ Given a section, find the relocation section for it in the ELF
            file. Return a RelocationSection object, or None if none was
            found.
        """
        reloc_section_names = (
                b'.rel' + section.name,
                b'.rela' + section.name)
        # Find the relocation section aimed at this one. Currently assume
        # that either .rel or .rela section exists for this section, but
        # not both.
        for relsection in self.elffile.iter_sections():
            if (    isinstance(relsection, RelocationSection) and
                    relsection.name in reloc_section_names):
                return relsection
        return None

    def apply_section_relocations(self, stream, reloc_section):
        """ Apply all relocations in reloc_section (a RelocationSection object)
            to the given stream, that contains the data of the section that is
            being relocated. The stream is modified as a result.
        """
        # The symbol table associated with this relocation section
        symtab = self.elffile.get_section(reloc_section['sh_link'])
        for reloc in reloc_section.iter_relocations():
            self._do_apply_relocation(stream, reloc, symtab)

    def _do_apply_relocation(self, stream, reloc, symtab):
        # Preparations for performing the relocation: obtain the value of
        # the symbol mentioned in the relocation, as well as the relocation
        # recipe which tells us how to actually perform it.
        # All peppered with some sanity checking.
        if reloc['r_info_sym'] >= symtab.num_symbols():
            raise ELFRelocationError(
                'Invalid symbol reference in relocation: index %s' % (
                    reloc['r_info_sym']))
        sym_value = symtab.get_symbol(reloc['r_info_sym'])['st_value']

        reloc_type = reloc['r_info_type']
        recipe = None

        if self.elffile.get_machine_arch() == 'x86':
            if reloc.is_RELA():
                raise ELFRelocationError(
                    'Unexpected RELA relocation for x86: %s' % reloc)
            recipe = self._RELOCATION_RECIPES_X86.get(reloc_type, None)
        elif self.elffile.get_machine_arch() == 'x64':
            if not reloc.is_RELA():
                raise ELFRelocationError(
                    'Unexpected REL relocation for x64: %s' % reloc)
            recipe = self._RELOCATION_RECIPES_X64.get(reloc_type, None)

        if recipe is None:
            raise ELFRelocationError(
                    'Unsupported relocation type: %s' % reloc_type)

        # So now we have everything we need to actually perform the relocation.
        # Let's get to it:

        # 0. Find out which struct we're going to be using to read this value
        #    from the stream and write it back.
        if recipe.bytesize == 4:
            value_struct = self.elffile.structs.Elf_word('')
        elif recipe.bytesize == 8:
            value_struct = self.elffile.structs.Elf_word64('')
        else:
            raise ELFRelocationError('Invalid bytesize %s for relocation' %
                    recipe_bytesize)

        # 1. Read the value from the stream (with correct size and endianness)
        original_value = struct_parse(
            value_struct,
            stream,
            stream_pos=reloc['r_offset'])
        # 2. Apply the relocation to the value, acting according to the recipe
        relocated_value = recipe.calc_func(
            value=original_value,
            sym_value=sym_value,
            offset=reloc['r_offset'],
            addend=reloc['r_addend'] if recipe.has_addend else 0)
        # 3. Write the relocated value back into the stream
        stream.seek(reloc['r_offset'])

        # Make sure the relocated value fits back by wrapping it around. This
        # looks like a problem, but it seems to be the way this is done in
        # binutils too.
        relocated_value = relocated_value % (2 ** (recipe.bytesize * 8))
        value_struct.build_stream(relocated_value, stream)

    # Relocations are represented by "recipes". Each recipe specifies:
    #  bytesize: The number of bytes to read (and write back) to the section.
    #            This is the unit of data on which relocation is performed.
    #  has_addend: Does this relocation have an extra addend?
    #  calc_func: A function that performs the relocation on an extracted
    #             value, and returns the updated value.
    #
    _RELOCATION_RECIPE_TYPE = namedtuple('_RELOCATION_RECIPE_TYPE',
        'bytesize has_addend calc_func')

    def _reloc_calc_identity(value, sym_value, offset, addend=0):
        return value

    def _reloc_calc_sym_plus_value(value, sym_value, offset, addend=0):
        return sym_value + value

    def _reloc_calc_sym_plus_value_pcrel(value, sym_value, offset, addend=0):
        return sym_value + value - offset

    def _reloc_calc_sym_plus_addend(value, sym_value, offset, addend=0):
        return sym_value + addend

    def _reloc_calc_sym_plus_addend_pcrel(value, sym_value, offset, addend=0):
        return sym_value + addend - offset

    _RELOCATION_RECIPES_X86 = {
        ENUM_RELOC_TYPE_i386['R_386_NONE']: _RELOCATION_RECIPE_TYPE(
            bytesize=4, has_addend=False, calc_func=_reloc_calc_identity),
        ENUM_RELOC_TYPE_i386['R_386_32']: _RELOCATION_RECIPE_TYPE(
            bytesize=4, has_addend=False,
            calc_func=_reloc_calc_sym_plus_value),
        ENUM_RELOC_TYPE_i386['R_386_PC32']: _RELOCATION_RECIPE_TYPE(
            bytesize=4, has_addend=False,
            calc_func=_reloc_calc_sym_plus_value_pcrel),
    }

    _RELOCATION_RECIPES_X64 = {
        ENUM_RELOC_TYPE_x64['R_X86_64_NONE']: _RELOCATION_RECIPE_TYPE(
            bytesize=8, has_addend=True, calc_func=_reloc_calc_identity),
        ENUM_RELOC_TYPE_x64['R_X86_64_64']: _RELOCATION_RECIPE_TYPE(
            bytesize=8, has_addend=True, calc_func=_reloc_calc_sym_plus_addend),
        ENUM_RELOC_TYPE_x64['R_X86_64_PC32']: _RELOCATION_RECIPE_TYPE(
            bytesize=8, has_addend=True,
            calc_func=_reloc_calc_sym_plus_addend_pcrel),
        ENUM_RELOC_TYPE_x64['R_X86_64_32']: _RELOCATION_RECIPE_TYPE(
            bytesize=4, has_addend=True, calc_func=_reloc_calc_sym_plus_addend),
        ENUM_RELOC_TYPE_x64['R_X86_64_32S']: _RELOCATION_RECIPE_TYPE(
            bytesize=4, has_addend=True, calc_func=_reloc_calc_sym_plus_addend),
    }



########NEW FILE########
__FILENAME__ = sections
#-------------------------------------------------------------------------------
# elftools: elf/sections.py
#
# ELF sections
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
from ..common.utils import struct_parse, elf_assert, parse_cstring_from_stream


class Section(object):
    """ Base class for ELF sections. Also used for all sections types that have
        no special functionality.

        Allows dictionary-like access to the section header. For example:
         > sec = Section(...)
         > sec['sh_type']  # section type
    """
    def __init__(self, header, name, stream):
        self.header = header
        self.name = name
        self.stream = stream

    def data(self):
        """ The section data from the file.
        """
        self.stream.seek(self['sh_offset'])
        return self.stream.read(self['sh_size'])

    def is_null(self):
        """ Is this a null section?
        """
        return False

    def __getitem__(self, name):
        """ Implement dict-like access to header entries
        """
        return self.header[name]

    def __eq__(self, other):
        return self.header == other.header
    def __hash__(self):
        return hash(self.header)


class NullSection(Section):
    """ ELF NULL section
    """
    def __init__(self, header, name, stream):
        super(NullSection, self).__init__(header, name, stream)

    def is_null(self):
        return True


class StringTableSection(Section):
    """ ELF string table section.
    """
    def __init__(self, header, name, stream):
        super(StringTableSection, self).__init__(header, name, stream)

    def get_string(self, offset):
        """ Get the string stored at the given offset in this string table.
        """
        table_offset = self['sh_offset']
        s = parse_cstring_from_stream(self.stream, table_offset + offset)
        return s


class SymbolTableSection(Section):
    """ ELF symbol table section. Has an associated StringTableSection that's
        passed in the constructor.
    """
    def __init__(self, header, name, stream, elffile, stringtable):
        super(SymbolTableSection, self).__init__(header, name, stream)
        self.elffile = elffile
        self.elfstructs = self.elffile.structs
        self.stringtable = stringtable
        elf_assert(self['sh_entsize'] > 0,
                'Expected entry size of section %r to be > 0' % name)
        elf_assert(self['sh_size'] % self['sh_entsize'] == 0,
                'Expected section size to be a multiple of entry size in section %r' % name)

    def num_symbols(self):
        """ Number of symbols in the table
        """
        return self['sh_size'] // self['sh_entsize']

    def get_symbol(self, n):
        """ Get the symbol at index #n from the table (Symbol object)
        """
        # Grab the symbol's entry from the stream
        entry_offset = self['sh_offset'] + n * self['sh_entsize']
        entry = struct_parse(
            self.elfstructs.Elf_Sym,
            self.stream,
            stream_pos=entry_offset)
        # Find the symbol name in the associated string table
        name = self.stringtable.get_string(entry['st_name'])
        return Symbol(entry, name)

    def iter_symbols(self):
        """ Yield all the symbols in the table
        """
        for i in range(self.num_symbols()):
            yield self.get_symbol(i)


class Symbol(object):
    """ Symbol object - representing a single symbol entry from a symbol table
        section.

        Similarly to Section objects, allows dictionary-like access to the
        symbol entry.
    """
    def __init__(self, entry, name):
        self.entry = entry
        self.name = name

    def __getitem__(self, name):
        """ Implement dict-like access to entries
        """
        return self.entry[name]


class SUNWSyminfoTableSection(Section):
    """ ELF .SUNW Syminfo table section.
        Has an associated SymbolTableSection that's passed in the constructor.
    """
    def __init__(self, header, name, stream, elffile, symboltable):
        super(SUNWSyminfoTableSection, self).__init__(header, name, stream)
        self.elffile = elffile
        self.elfstructs = self.elffile.structs
        self.symboltable = symboltable

    def num_symbols(self):
        """ Number of symbols in the table
        """
        return self['sh_size'] // self['sh_entsize'] - 1

    def get_symbol(self, n):
        """ Get the symbol at index #n from the table (Symbol object).
            It begins at 1 and not 0 since the first entry is used to
            store the current version of the syminfo table.
        """
        # Grab the symbol's entry from the stream
        entry_offset = self['sh_offset'] + n * self['sh_entsize']
        entry = struct_parse(
            self.elfstructs.Elf_Sunw_Syminfo,
            self.stream,
            stream_pos=entry_offset)
        # Find the symbol name in the associated symbol table
        name = self.symboltable.get_symbol(n).name
        return Symbol(entry, name)

    def iter_symbols(self):
        """ Yield all the symbols in the table
        """
        for i in range(1, self.num_symbols() + 1):
            yield self.get_symbol(i)

########NEW FILE########
__FILENAME__ = segments
#-------------------------------------------------------------------------------
# elftools: elf/segments.py
#
# ELF segments
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
from ..construct import CString
from ..common.utils import struct_parse
from .constants import SH_FLAGS


class Segment(object):
    def __init__(self, header, stream):
        self.header = header
        self.stream = stream

    def data(self):
        """ The segment data from the file.
        """
        self.stream.seek(self['p_offset'])
        return self.stream.read(self['p_filesz'])

    def __getitem__(self, name):
        """ Implement dict-like access to header entries
        """
        return self.header[name]

    def section_in_segment(self, section):
        """ Is the given section contained in this segment?

            Note: this tries to reproduce the intricate rules of the
            ELF_SECTION_IN_SEGMENT_STRICT macro of the header
            elf/include/internal.h in the source of binutils.
        """
        # Only the 'strict' checks from ELF_SECTION_IN_SEGMENT_1 are included
        segtype = self['p_type']
        sectype = section['sh_type']
        secflags = section['sh_flags']

        # Only PT_LOAD, PT_GNU_RELR0 and PT_TLS segments can contain SHF_TLS
        # sections
        if (    secflags & SH_FLAGS.SHF_TLS and
                segtype in ('PT_TLS', 'PT_GNU_RELR0', 'PT_LOAD')):
            return False
        # PT_TLS segment contains only SHF_TLS sections, PT_PHDR no sections
        # at all
        elif (  (secflags & SH_FLAGS.SHF_TLS) != 0 and
                segtype not in ('PT_TLS', 'PT_PHDR')):
            return False

        # In ELF_SECTION_IN_SEGMENT_STRICT the flag check_vma is on, so if
        # this is an alloc section, check whether its VMA is in bounds.
        if secflags & SH_FLAGS.SHF_ALLOC:
            secaddr = section['sh_addr']
            vaddr = self['p_vaddr']

            # This checks that the section is wholly contained in the segment.
            # The third condition is the 'strict' one - an empty section will
            # not match at the very end of the segment (unless the segment is
            # also zero size, which is handled by the second condition).
            if not (secaddr >= vaddr and
                    secaddr - vaddr + section['sh_size'] <= self['p_memsz'] and
                    secaddr - vaddr <= self['p_memsz'] - 1):
                return False

        # If we've come this far and it's a NOBITS section, it's in the segment
        if sectype == 'SHT_NOBITS':
            return True

        secoffset = section['sh_offset']
        poffset = self['p_offset']

        # Same logic as with secaddr vs. vaddr checks above, just on offsets in
        # the file
        return (secoffset >= poffset and
                secoffset - poffset + section['sh_size'] <= self['p_filesz'] and
                secoffset - poffset <= self['p_filesz'] - 1)


class InterpSegment(Segment):
    """ INTERP segment. Knows how to obtain the path to the interpreter used
        for this ELF file.
    """
    def __init__(self, header, stream):
        super(InterpSegment, self).__init__(header, stream)

    def get_interp_name(self):
        """ Obtain the interpreter path used for this ELF file.
        """
        path_offset = self['p_offset']
        return struct_parse(
            CString(''),
            self.stream,
            stream_pos=path_offset)



########NEW FILE########
__FILENAME__ = structs
#-------------------------------------------------------------------------------
# elftools: elf/structs.py
#
# Encapsulation of Construct structs for parsing an ELF file, adjusted for
# correct endianness and word-size.
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
from ..construct import (
    UBInt8, UBInt16, UBInt32, UBInt64,
    ULInt8, ULInt16, ULInt32, ULInt64,
    SBInt32, SLInt32, SBInt64, SLInt64,
    Struct, Array, Enum, Padding, BitStruct, BitField, Value,
    )

from .enums import *


class ELFStructs(object):
    """ Accessible attributes:

            Elf_{byte|half|word|word64|addr|offset|sword|xword|xsword}:
                Data chunks, as specified by the ELF standard, adjusted for
                correct endianness and word-size.

            Elf_Ehdr:
                ELF file header

            Elf_Phdr:
                Program header

            Elf_Shdr:
                Section header

            Elf_Sym:
                Symbol table entry

            Elf_Rel, Elf_Rela:
                Entries in relocation sections
    """
    def __init__(self, little_endian=True, elfclass=32):
        assert elfclass == 32 or elfclass == 64
        self.little_endian = little_endian
        self.elfclass = elfclass
        self._create_structs()

    def _create_structs(self):
        if self.little_endian:
            self.Elf_byte = ULInt8
            self.Elf_half = ULInt16
            self.Elf_word = ULInt32
            self.Elf_word64 = ULInt64
            self.Elf_addr = ULInt32 if self.elfclass == 32 else ULInt64
            self.Elf_offset = self.Elf_addr
            self.Elf_sword = SLInt32
            self.Elf_xword = ULInt32 if self.elfclass == 32 else ULInt64
            self.Elf_sxword = SLInt32 if self.elfclass == 32 else SLInt64
        else:
            self.Elf_byte = UBInt8
            self.Elf_half = UBInt16
            self.Elf_word = UBInt32
            self.Elf_word64 = UBInt64
            self.Elf_addr = UBInt32 if self.elfclass == 32 else UBInt64
            self.Elf_offset = self.Elf_addr
            self.Elf_sword = SBInt32
            self.Elf_xword = UBInt32 if self.elfclass == 32 else UBInt64
            self.Elf_sxword = SBInt32 if self.elfclass == 32 else SBInt64

        self._create_ehdr()
        self._create_phdr()
        self._create_shdr()
        self._create_sym()
        self._create_rel()
        self._create_dyn()
        self._create_sunw_syminfo()
        self._create_gnu_verneed()
        self._create_gnu_verdef()
        self._create_gnu_versym()

    def _create_ehdr(self):
        self.Elf_Ehdr = Struct('Elf_Ehdr',
            Struct('e_ident',
                Array(4, self.Elf_byte('EI_MAG')),
                Enum(self.Elf_byte('EI_CLASS'), **ENUM_EI_CLASS),
                Enum(self.Elf_byte('EI_DATA'), **ENUM_EI_DATA),
                Enum(self.Elf_byte('EI_VERSION'), **ENUM_E_VERSION),
                Enum(self.Elf_byte('EI_OSABI'), **ENUM_EI_OSABI),
                self.Elf_byte('EI_ABIVERSION'),
                Padding(7)
            ),
            Enum(self.Elf_half('e_type'), **ENUM_E_TYPE),
            Enum(self.Elf_half('e_machine'), **ENUM_E_MACHINE),
            Enum(self.Elf_word('e_version'), **ENUM_E_VERSION),
            self.Elf_addr('e_entry'),
            self.Elf_offset('e_phoff'),
            self.Elf_offset('e_shoff'),
            self.Elf_word('e_flags'),
            self.Elf_half('e_ehsize'),
            self.Elf_half('e_phentsize'),
            self.Elf_half('e_phnum'),
            self.Elf_half('e_shentsize'),
            self.Elf_half('e_shnum'),
            self.Elf_half('e_shstrndx'),
        )

    def _create_phdr(self):
        if self.elfclass == 32:
            self.Elf_Phdr = Struct('Elf_Phdr',
                Enum(self.Elf_word('p_type'), **ENUM_P_TYPE),
                self.Elf_offset('p_offset'),
                self.Elf_addr('p_vaddr'),
                self.Elf_addr('p_paddr'),
                self.Elf_word('p_filesz'),
                self.Elf_word('p_memsz'),
                self.Elf_word('p_flags'),
                self.Elf_word('p_align'),
            )
        else: # 64
            self.Elf_Phdr = Struct('Elf_Phdr',
                Enum(self.Elf_word('p_type'), **ENUM_P_TYPE),
                self.Elf_word('p_flags'),
                self.Elf_offset('p_offset'),
                self.Elf_addr('p_vaddr'),
                self.Elf_addr('p_paddr'),
                self.Elf_xword('p_filesz'),
                self.Elf_xword('p_memsz'),
                self.Elf_xword('p_align'),
            )

    def _create_shdr(self):
        self.Elf_Shdr = Struct('Elf_Shdr',
            self.Elf_word('sh_name'),
            Enum(self.Elf_word('sh_type'), **ENUM_SH_TYPE),
            self.Elf_xword('sh_flags'),
            self.Elf_addr('sh_addr'),
            self.Elf_offset('sh_offset'),
            self.Elf_xword('sh_size'),
            self.Elf_word('sh_link'),
            self.Elf_word('sh_info'),
            self.Elf_xword('sh_addralign'),
            self.Elf_xword('sh_entsize'),
        )

    def _create_rel(self):
        # r_info is also taken apart into r_info_sym and r_info_type.
        # This is done in Value to avoid endianity issues while parsing.
        if self.elfclass == 32:
            r_info_sym = Value('r_info_sym',
                lambda ctx: (ctx['r_info'] >> 8) & 0xFFFFFF)
            r_info_type = Value('r_info_type',
                lambda ctx: ctx['r_info'] & 0xFF)
        else: # 64
            r_info_sym = Value('r_info_sym',
                lambda ctx: (ctx['r_info'] >> 32) & 0xFFFFFFFF)
            r_info_type = Value('r_info_type',
                lambda ctx: ctx['r_info'] & 0xFFFFFFFF)

        self.Elf_Rel = Struct('Elf_Rel',
            self.Elf_addr('r_offset'),
            self.Elf_xword('r_info'),
            r_info_sym,
            r_info_type,
        )
        self.Elf_Rela = Struct('Elf_Rela',
            self.Elf_addr('r_offset'),
            self.Elf_xword('r_info'),
            r_info_sym,
            r_info_type,
            self.Elf_sxword('r_addend'),
        )

    def _create_dyn(self):
        self.Elf_Dyn = Struct('Elf_Dyn',
            Enum(self.Elf_sxword('d_tag'), **ENUM_D_TAG),
            self.Elf_xword('d_val'),
            Value('d_ptr', lambda ctx: ctx['d_val']),
        )

    def _create_sym(self):
        # st_info is hierarchical. To access the type, use
        # container['st_info']['type']
        st_info_struct = BitStruct('st_info',
            Enum(BitField('bind', 4), **ENUM_ST_INFO_BIND),
            Enum(BitField('type', 4), **ENUM_ST_INFO_TYPE))
        # st_other is hierarchical. To access the visibility,
        # use container['st_other']['visibility']
        st_other_struct = BitStruct('st_other',
            Padding(5),
            Enum(BitField('visibility', 3), **ENUM_ST_VISIBILITY))
        if self.elfclass == 32:
            self.Elf_Sym = Struct('Elf_Sym',
                self.Elf_word('st_name'),
                self.Elf_addr('st_value'),
                self.Elf_word('st_size'),
                st_info_struct,
                st_other_struct,
                Enum(self.Elf_half('st_shndx'), **ENUM_ST_SHNDX),
            )
        else:
            self.Elf_Sym = Struct('Elf_Sym',
                self.Elf_word('st_name'),
                st_info_struct,
                st_other_struct,
                Enum(self.Elf_half('st_shndx'), **ENUM_ST_SHNDX),
                self.Elf_addr('st_value'),
                self.Elf_xword('st_size'),
            )

    def _create_sunw_syminfo(self):
        self.Elf_Sunw_Syminfo = Struct('Elf_Sunw_Syminfo',
            Enum(self.Elf_half('si_boundto'), **ENUM_SUNW_SYMINFO_BOUNDTO),
            self.Elf_half('si_flags'),
        )

    def _create_gnu_verneed(self):
        # Structure of "version needed" entries is documented in
        # Oracle "Linker and Libraries Guide", Chapter 7 Object File Format
        self.Elf_Verneed = Struct('Elf_Verneed',
            self.Elf_half('vn_version'),
            self.Elf_half('vn_cnt'),
            self.Elf_word('vn_file'),
            self.Elf_word('vn_aux'),
            self.Elf_word('vn_next'),
        )
        self.Elf_Vernaux = Struct('Elf_Vernaux',
            self.Elf_word('vna_hash'),
            self.Elf_half('vna_flags'),
            self.Elf_half('vna_other'),
            self.Elf_word('vna_name'),
            self.Elf_word('vna_next'),
        )

    def _create_gnu_verdef(self):
        # Structure off "version definition" entries are documented in
        # Oracle "Linker and Libraries Guide", Chapter 7 Object File Format
        self.Elf_Verdef = Struct('Elf_Verdef',
            self.Elf_half('vd_version'),
            self.Elf_half('vd_flags'),
            self.Elf_half('vd_ndx'),
            self.Elf_half('vd_cnt'),
            self.Elf_word('vd_hash'),
            self.Elf_word('vd_aux'),
            self.Elf_word('vd_next'),
        )
        self.Elf_Verdaux = Struct('Elf_Verdaux',
            self.Elf_word('vda_name'),
            self.Elf_word('vda_next'),
        )

    def _create_gnu_versym(self):
        # Structure off "version symbol" entries are documented in
        # Oracle "Linker and Libraries Guide", Chapter 7 Object File Format
        self.Elf_Versym = Struct('Elf_Versym',
            Enum(self.Elf_half('ndx'), **ENUM_VERSYM),
        )

########NEW FILE########
__FILENAME__ = dwarf_decode_address
#-------------------------------------------------------------------------------
# elftools example: dwarf_decode_address.py
#
# Decode an address in an ELF file to find out which function it belongs to
# and from which filename/line it comes in the original source file.
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
from __future__ import print_function
import sys

# If pyelftools is not installed, the example can also run from the root or
# examples/ dir of the source distribution.
sys.path[0:0] = ['.', '..']

from elftools.common.py3compat import maxint, bytes2str
from elftools.elf.elffile import ELFFile


def process_file(filename, address):
    print('Processing file:', filename)
    with open(filename, 'rb') as f:
        elffile = ELFFile(f)

        if not elffile.has_dwarf_info():
            print('  file has no DWARF info')
            return

        # get_dwarf_info returns a DWARFInfo context object, which is the
        # starting point for all DWARF-based processing in pyelftools.
        dwarfinfo = elffile.get_dwarf_info()

        funcname = decode_funcname(dwarfinfo, address)
        file, line = decode_file_line(dwarfinfo, address)

        print('Function:', bytes2str(funcname))
        print('File:', bytes2str(file))
        print('Line:', line)


def decode_funcname(dwarfinfo, address):
    # Go over all DIEs in the DWARF information, looking for a subprogram
    # entry with an address range that includes the given address. Note that
    # this simplifies things by disregarding subprograms that may have
    # split address ranges.
    for CU in dwarfinfo.iter_CUs():
        for DIE in CU.iter_DIEs():
            try:
                if DIE.tag == 'DW_TAG_subprogram':
                    lowpc = DIE.attributes['DW_AT_low_pc'].value
                    highpc = DIE.attributes['DW_AT_high_pc'].value
                    if lowpc <= address <= highpc:
                        return DIE.attributes['DW_AT_name'].value
            except KeyError:
                continue
    return None


def decode_file_line(dwarfinfo, address):
    # Go over all the line programs in the DWARF information, looking for
    # one that describes the given address.
    for CU in dwarfinfo.iter_CUs():
        # First, look at line programs to find the file/line for the address
        lineprog = dwarfinfo.line_program_for_CU(CU)
        prevstate = None
        for entry in lineprog.get_entries():
            # We're interested in those entries where a new state is assigned
            if entry.state is None or entry.state.end_sequence:
                continue
            # Looking for a range of addresses in two consecutive states that
            # contain the required address.
            if prevstate and prevstate.address <= address < entry.state.address:
                filename = lineprog['file_entry'][prevstate.file - 1].name
                line = prevstate.line
                return filename, line
            prevstate = entry.state
    return None, None


if __name__ == '__main__':
    for filename in sys.argv[1:]:
        # For testing we use a hardcoded address.
        process_file(filename, 0x400503)


########NEW FILE########
__FILENAME__ = dwarf_die_tree
#-------------------------------------------------------------------------------
# elftools example: dwarf_die_tree.py
#
# In the .debug_info section, Dwarf Information Entries (DIEs) form a tree.
# pyelftools provides easy access to this tree, as demonstrated here.
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
from __future__ import print_function
import sys

# If pyelftools is not installed, the example can also run from the root or
# examples/ dir of the source distribution.
sys.path[0:0] = ['.', '..']

from elftools.elf.elffile import ELFFile


def process_file(filename):
    print('Processing file:', filename)
    with open(filename, 'rb') as f:
        elffile = ELFFile(f)

        if not elffile.has_dwarf_info():
            print('  file has no DWARF info')
            return

        # get_dwarf_info returns a DWARFInfo context object, which is the
        # starting point for all DWARF-based processing in pyelftools.
        dwarfinfo = elffile.get_dwarf_info()

        for CU in dwarfinfo.iter_CUs():
            # DWARFInfo allows to iterate over the compile units contained in
            # the .debug_info section. CU is a CompileUnit object, with some
            # computed attributes (such as its offset in the section) and
            # a header which conforms to the DWARF standard. The access to
            # header elements is, as usual, via item-lookup.
            print('  Found a compile unit at offset %s, length %s' % (
                CU.cu_offset, CU['unit_length']))

            # Start with the top DIE, the root for this CU's DIE tree
            top_DIE = CU.get_top_DIE()
            print('    Top DIE with tag=%s' % top_DIE.tag)

            # We're interested in the filename...
            print('    name=%s' % top_DIE.get_full_path())

            # Display DIEs recursively starting with top_DIE
            die_info_rec(top_DIE)


def die_info_rec(die, indent_level='    '):
    """ A recursive function for showing information about a DIE and its
        children.
    """
    print(indent_level + 'DIE tag=%s' % die.tag)
    child_indent = indent_level + '  '
    for child in die.iter_children():
        die_info_rec(child, child_indent)


if __name__ == '__main__':
    for filename in sys.argv[1:]:
        process_file(filename)







########NEW FILE########
__FILENAME__ = dwarf_location_lists
#-------------------------------------------------------------------------------
# elftools example: dwarf_location_lists.py
#
# Examine DIE entries which have location list values, and decode these
# location lists.
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
from __future__ import print_function
import sys

# If pyelftools is not installed, the example can also run from the root or
# examples/ dir of the source distribution.
sys.path[0:0] = ['.', '..']


from elftools.common.py3compat import itervalues
from elftools.elf.elffile import ELFFile
from elftools.dwarf.descriptions import (
    describe_DWARF_expr, set_global_machine_arch)
from elftools.dwarf.locationlists import LocationEntry


def process_file(filename):
    print('Processing file:', filename)
    with open(filename, 'rb') as f:
        elffile = ELFFile(f)

        if not elffile.has_dwarf_info():
            print('  file has no DWARF info')
            return

        # get_dwarf_info returns a DWARFInfo context object, which is the
        # starting point for all DWARF-based processing in pyelftools.
        dwarfinfo = elffile.get_dwarf_info()

        # The location lists are extracted by DWARFInfo from the .debug_loc
        # section, and returned here as a LocationLists object.
        location_lists = dwarfinfo.location_lists()

        # This is required for the descriptions module to correctly decode
        # register names contained in DWARF expressions.
        set_global_machine_arch(elffile.get_machine_arch())

        for CU in dwarfinfo.iter_CUs():
            # DWARFInfo allows to iterate over the compile units contained in
            # the .debug_info section. CU is a CompileUnit object, with some
            # computed attributes (such as its offset in the section) and
            # a header which conforms to the DWARF standard. The access to
            # header elements is, as usual, via item-lookup.
            print('  Found a compile unit at offset %s, length %s' % (
                CU.cu_offset, CU['unit_length']))

            # A CU provides a simple API to iterate over all the DIEs in it.
            for DIE in CU.iter_DIEs():
                # Go over all attributes of the DIE. Each attribute is an
                # AttributeValue object (from elftools.dwarf.die), which we
                # can examine.
                for attr in itervalues(DIE.attributes):
                    if attribute_has_location_list(attr):
                        # This is a location list. Its value is an offset into
                        # the .debug_loc section, so we can use the location
                        # lists object to decode it.
                        loclist = location_lists.get_location_list_at_offset(
                            attr.value)

                        print('   DIE %s. attr %s.\n%s' % (
                            DIE.tag,
                            attr.name,
                            show_loclist(loclist, dwarfinfo, indent='      ')))


def show_loclist(loclist, dwarfinfo, indent):
    """ Display a location list nicely, decoding the DWARF expressions
        contained within.
    """
    d = []
    for loc_entity in loclist:
        if isinstance(loc_entity, LocationEntry):
            d.append('%s <<%s>>' % (
                loc_entity,
                describe_DWARF_expr(loc_entity.loc_expr, dwarfinfo.structs)))
        else:
            d.append(str(loc_entity))
    return '\n'.join(indent + s for s in d)


def attribute_has_location_list(attr):
    """ Only some attributes can have location list values, if they have the
        required DW_FORM (loclistptr "class" in DWARF spec v3)
    """
    if (attr.name in (  'DW_AT_location', 'DW_AT_string_length',
                        'DW_AT_const_value', 'DW_AT_return_addr',
                        'DW_AT_data_member_location', 'DW_AT_frame_base',
                        'DW_AT_segment', 'DW_AT_static_link',
                        'DW_AT_use_location', 'DW_AT_vtable_elem_location')):
        if attr.form in ('DW_FORM_data4', 'DW_FORM_data8'):
            return True
    return False


if __name__ == '__main__':
    for filename in sys.argv[1:]:
        process_file(filename)







########NEW FILE########
__FILENAME__ = dwarf_range_lists
#-------------------------------------------------------------------------------
# elftools example: dwarf_range_lists.py
#
# Examine DIE entries which have range list values, and decode these range
# lists.
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
from __future__ import print_function
import sys

# If pyelftools is not installed, the example can also run from the root or
# examples/ dir of the source distribution.
sys.path[0:0] = ['.', '..']

from elftools.common.py3compat import itervalues
from elftools.elf.elffile import ELFFile
from elftools.dwarf.descriptions import (
    describe_DWARF_expr, set_global_machine_arch)
from elftools.dwarf.ranges import RangeEntry


def process_file(filename):
    print('Processing file:', filename)
    with open(filename, 'rb') as f:
        elffile = ELFFile(f)

        if not elffile.has_dwarf_info():
            print('  file has no DWARF info')
            return

        # get_dwarf_info returns a DWARFInfo context object, which is the
        # starting point for all DWARF-based processing in pyelftools.
        dwarfinfo = elffile.get_dwarf_info()

        # The range lists are extracted by DWARFInfo from the .debug_ranges
        # section, and returned here as a RangeLists object.
        range_lists = dwarfinfo.range_lists()
        if range_lists is None:
            print('  file has no .debug_ranges section')
            return

        for CU in dwarfinfo.iter_CUs():
            # DWARFInfo allows to iterate over the compile units contained in
            # the .debug_info section. CU is a CompileUnit object, with some
            # computed attributes (such as its offset in the section) and
            # a header which conforms to the DWARF standard. The access to
            # header elements is, as usual, via item-lookup.
            print('  Found a compile unit at offset %s, length %s' % (
                CU.cu_offset, CU['unit_length']))

            # A CU provides a simple API to iterate over all the DIEs in it.
            for DIE in CU.iter_DIEs():
                # Go over all attributes of the DIE. Each attribute is an
                # AttributeValue object (from elftools.dwarf.die), which we
                # can examine.
                for attr in itervalues(DIE.attributes):
                    if attribute_has_range_list(attr):
                        # This is a range list. Its value is an offset into
                        # the .debug_ranges section, so we can use the range
                        # lists object to decode it.
                        rangelist = range_lists.get_range_list_at_offset(
                            attr.value)

                        print('   DIE %s. attr %s.\n%s' % (
                            DIE.tag,
                            attr.name,
                            rangelist))


def attribute_has_range_list(attr):
    """ Only some attributes can have range list values, if they have the
        required DW_FORM (rangelistptr "class" in DWARF spec v3)
    """
    if attr.name == 'DW_AT_ranges':
        if attr.form in ('DW_FORM_data4', 'DW_FORM_data8'):
            return True
    return False


if __name__ == '__main__':
    for filename in sys.argv[1:]:
        process_file(filename)








########NEW FILE########
__FILENAME__ = elfclass_address_size
#-------------------------------------------------------------------------------
# elftools example: elfclass_address_size.py
#
# This example explores the ELF class (32 or 64-bit) and address size in each
# of the CUs in the DWARF information.
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
from __future__ import print_function
import sys

# If pyelftools is not installed, the example can also run from the root or
# examples/ dir of the source distribution.
sys.path[0:0] = ['.', '..']

from elftools.elf.elffile import ELFFile


def process_file(filename):
    with open(filename, 'rb') as f:
        elffile = ELFFile(f)
        # elfclass is a public attribute of ELFFile, read from its header
        print('%s: elfclass is %s' % (filename, elffile.elfclass))

        if elffile.has_dwarf_info():
            dwarfinfo = elffile.get_dwarf_info()
            for CU in dwarfinfo.iter_CUs():
                # cu_offset is a public attribute of CU
                # address_size is part of the CU header
                print('  CU at offset 0x%x. address_size is %s' % (
                    CU.cu_offset, CU['address_size']))


if __name__ == '__main__':
    for filename in sys.argv[1:]:
        process_file(filename)


########NEW FILE########
__FILENAME__ = elf_low_high_api
#-------------------------------------------------------------------------------
# elftools example: elf_low_high_api.py
#
# A simple example that shows some usage of the low-level API pyelftools
# provides versus the high-level API while inspecting an ELF file's symbol
# table.
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
from __future__ import print_function
import sys

# If pyelftools is not installed, the example can also run from the root or
# examples/ dir of the source distribution.
sys.path[0:0] = ['.', '..']

from elftools.common.py3compat import bytes2str
from elftools.elf.elffile import ELFFile
from elftools.elf.sections import SymbolTableSection


def process_file(filename):
    print('Processing file:', filename)
    with open(filename, 'rb') as f:
        section_info_lowlevel(f)
        f.seek(0)
        section_info_highlevel(f)


def section_info_lowlevel(stream):
    print('Low level API...')
    # We'll still be using the ELFFile context object. It's just too
    # convenient to give up, even in the low-level API demonstation :-)
    elffile = ELFFile(stream)

    # The e_shnum ELF header field says how many sections there are in a file
    print('  %s sections' % elffile['e_shnum'])

    # Try to find the symbol table
    for i in range(elffile['e_shnum']):
        section_offset = elffile['e_shoff'] + i * elffile['e_shentsize']
        # Parse the section header using structs.Elf_Shdr
        stream.seek(section_offset)
        section_header = elffile.structs.Elf_Shdr.parse_stream(stream)
        if section_header['sh_type'] == 'SHT_SYMTAB':
            # Some details about the section. Note that the section name is a
            # pointer to the object's string table, so it's only a number
            # here. To get to the actual name one would need to parse the string
            # table section and extract the name from there (or use the
            # high-level API!)
            print('  Section name: %s, type: %s' % (
                    section_header['sh_name'], section_header['sh_type']))
            break
    else:
        print('  No symbol table found. Perhaps this ELF has been stripped?')


def section_info_highlevel(stream):
    print('High level API...')
    elffile = ELFFile(stream)

    # Just use the public methods of ELFFile to get what we need
    # Note that section names, like everything read from the file, are bytes
    # objects.
    print('  %s sections' % elffile.num_sections())
    section = elffile.get_section_by_name(b'.symtab')

    if not section:
        print('  No symbol table found. Perhaps this ELF has been stripped?')
        return

    # A section type is in its header, but the name was decoded and placed in
    # a public attribute.
    # bytes2str is used to print the name of the section for consistency of
    # output between Python 2 and 3. The section name is a bytes object.
    print('  Section name: %s, type: %s' %(
        bytes2str(section.name), section['sh_type']))

    # But there's more... If this section is a symbol table section (which is
    # the case in the sample ELF file that comes with the examples), we can
    # get some more information about it.
    if isinstance(section, SymbolTableSection):
        num_symbols = section.num_symbols()
        print("  It's a symbol section with %s symbols" % num_symbols)
        print("  The name of the last symbol in the section is: %s" % (
            bytes2str(section.get_symbol(num_symbols - 1).name)))


if __name__ == '__main__':
    for filename in sys.argv[1:]:
        process_file(filename)



########NEW FILE########
__FILENAME__ = elf_relocations
#-------------------------------------------------------------------------------
# elftools example: elf_relocations.py
#
# An example of obtaining a relocation section from an ELF file and examining
# the relocation entries it contains.
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
from __future__ import print_function
import sys

# If pyelftools is not installed, the example can also run from the root or
# examples/ dir of the source distribution.
sys.path[0:0] = ['.', '..']


from elftools.common.py3compat import bytes2str
from elftools.elf.elffile import ELFFile
from elftools.elf.relocation import RelocationSection


def process_file(filename):
    print('Processing file:', filename)
    with open(filename, 'rb') as f:
        elffile = ELFFile(f)

        # Read the .rela.dyn section from the file, by explicitly asking
        # ELFFile for this section
        # Recall that section names are bytes objects
        reladyn_name = b'.rela.dyn'
        reladyn = elffile.get_section_by_name(reladyn_name)

        if not isinstance(reladyn, RelocationSection):
            print('  The file has no %s section' % bytes2str(reladyn_name))

        print('  %s section with %s relocations' % (
            bytes2str(reladyn_name), reladyn.num_relocations()))

        for reloc in reladyn.iter_relocations():
            print('    Relocation (%s)' % 'RELA' if reloc.is_RELA() else 'REL')
            # Relocation entry attributes are available through item lookup
            print('      offset = %s' % reloc['r_offset'])


if __name__ == '__main__':
    for filename in sys.argv[1:]:
        process_file(filename)


########NEW FILE########
__FILENAME__ = elf_show_debug_sections
#-------------------------------------------------------------------------------
# elftools example: elf_show_debug_sections.py
#
# Show the names of all .debug_* sections in ELF files.
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
from __future__ import print_function
import sys

# If pyelftools is not installed, the example can also run from the root or
# examples/ dir of the source distribution.
sys.path[0:0] = ['.', '..']

from elftools.common.py3compat import bytes2str
from elftools.elf.elffile import ELFFile


def process_file(filename):
    print('In file:', filename)
    with open(filename, 'rb') as f:
        elffile = ELFFile(f)

        for section in elffile.iter_sections():
            # Section names are bytes objects
            if section.name.startswith(b'.debug'):
                print('  ' + bytes2str(section.name))


if __name__ == '__main__':
    for filename in sys.argv[1:]:
        process_file(filename)


########NEW FILE########
__FILENAME__ = examine_dwarf_info
#-------------------------------------------------------------------------------
# elftools example: examine_dwarf_info.py
#
# An example of examining information in the .debug_info section of an ELF file.
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
from __future__ import print_function
import sys

# If pyelftools is not installed, the example can also run from the root or
# examples/ dir of the source distribution.
sys.path[0:0] = ['.', '..']

from elftools.elf.elffile import ELFFile


def process_file(filename):
    print('Processing file:', filename)
    with open(filename, 'rb') as f:
        elffile = ELFFile(f)

        if not elffile.has_dwarf_info():
            print('  file has no DWARF info')
            return

        # get_dwarf_info returns a DWARFInfo context object, which is the
        # starting point for all DWARF-based processing in pyelftools.
        dwarfinfo = elffile.get_dwarf_info()

        for CU in dwarfinfo.iter_CUs():
            # DWARFInfo allows to iterate over the compile units contained in
            # the .debug_info section. CU is a CompileUnit object, with some
            # computed attributes (such as its offset in the section) and
            # a header which conforms to the DWARF standard. The access to
            # header elements is, as usual, via item-lookup.
            print('  Found a compile unit at offset %s, length %s' % (
                CU.cu_offset, CU['unit_length']))

            # The first DIE in each compile unit describes it.
            top_DIE = CU.get_top_DIE()
            print('    Top DIE with tag=%s' % top_DIE.tag)

            # We're interested in the filename...
            print('    name=%s' % top_DIE.get_full_path())

if __name__ == '__main__':
    for filename in sys.argv[1:]:
        process_file(filename)






########NEW FILE########
__FILENAME__ = readelf
#!/usr/bin/env python
#-------------------------------------------------------------------------------
# scripts/readelf.py
#
# A clone of 'readelf' in Python, based on the pyelftools library
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
import os, sys
from optparse import OptionParser
import string

# For running from development directory. It should take precedence over the
# installed pyelftools.
sys.path.insert(0, '.')


from elftools import __version__
from elftools.common.exceptions import ELFError
from elftools.common.py3compat import (
        ifilter, byte2int, bytes2str, itervalues, str2bytes)
from elftools.elf.elffile import ELFFile
from elftools.elf.dynamic import DynamicSection, DynamicSegment
from elftools.elf.enums import ENUM_D_TAG
from elftools.elf.segments import InterpSegment
from elftools.elf.sections import SymbolTableSection
from elftools.elf.gnuversions import (
    GNUVerSymSection, GNUVerDefSection,
    GNUVerNeedSection,
    )
from elftools.elf.relocation import RelocationSection
from elftools.elf.descriptions import (
    describe_ei_class, describe_ei_data, describe_ei_version,
    describe_ei_osabi, describe_e_type, describe_e_machine,
    describe_e_version_numeric, describe_p_type, describe_p_flags,
    describe_sh_type, describe_sh_flags,
    describe_symbol_type, describe_symbol_bind, describe_symbol_visibility,
    describe_symbol_shndx, describe_reloc_type, describe_dyn_tag,
    describe_ver_flags,
    )
from elftools.elf.constants import E_FLAGS
from elftools.dwarf.dwarfinfo import DWARFInfo
from elftools.dwarf.descriptions import (
    describe_reg_name, describe_attr_value, set_global_machine_arch,
    describe_CFI_instructions, describe_CFI_register_rule,
    describe_CFI_CFA_rule,
    )
from elftools.dwarf.constants import (
    DW_LNS_copy, DW_LNS_set_file, DW_LNE_define_file)
from elftools.dwarf.callframe import CIE, FDE


class ReadElf(object):
    """ display_* methods are used to emit output into the output stream
    """
    def __init__(self, file, output):
        """ file:
                stream object with the ELF file to read

            output:
                output stream to write to
        """
        self.elffile = ELFFile(file)
        self.output = output

        # Lazily initialized if a debug dump is requested
        self._dwarfinfo = None

        self._versioninfo = None

    def display_file_header(self):
        """ Display the ELF file header
        """
        self._emitline('ELF Header:')
        self._emit('  Magic:   ')
        self._emitline(' '.join('%2.2x' % byte2int(b)
                                    for b in self.elffile.e_ident_raw))
        header = self.elffile.header
        e_ident = header['e_ident']
        self._emitline('  Class:                             %s' %
                describe_ei_class(e_ident['EI_CLASS']))
        self._emitline('  Data:                              %s' %
                describe_ei_data(e_ident['EI_DATA']))
        self._emitline('  Version:                           %s' %
                describe_ei_version(e_ident['EI_VERSION']))
        self._emitline('  OS/ABI:                            %s' %
                describe_ei_osabi(e_ident['EI_OSABI']))
        self._emitline('  ABI Version:                       %d' %
                e_ident['EI_ABIVERSION'])
        self._emitline('  Type:                              %s' %
                describe_e_type(header['e_type']))
        self._emitline('  Machine:                           %s' %
                describe_e_machine(header['e_machine']))
        self._emitline('  Version:                           %s' %
                describe_e_version_numeric(header['e_version']))
        self._emitline('  Entry point address:               %s' %
                self._format_hex(header['e_entry']))
        self._emit('  Start of program headers:          %s' %
                header['e_phoff'])
        self._emitline(' (bytes into file)')
        self._emit('  Start of section headers:          %s' %
                header['e_shoff'])
        self._emitline(' (bytes into file)')
        self._emitline('  Flags:                             %s%s' %
                (self._format_hex(header['e_flags']),
                self.decode_flags(header['e_flags'])))
        self._emitline('  Size of this header:               %s (bytes)' %
                header['e_ehsize'])
        self._emitline('  Size of program headers:           %s (bytes)' %
                header['e_phentsize'])
        self._emitline('  Number of program headers:         %s' %
                header['e_phnum'])
        self._emitline('  Size of section headers:           %s (bytes)' %
                header['e_shentsize'])
        self._emitline('  Number of section headers:         %s' %
                header['e_shnum'])
        self._emitline('  Section header string table index: %s' %
                header['e_shstrndx'])

    def decode_flags(self, flags):
        description = ""
        if self.elffile['e_machine'] == "EM_ARM":
            if flags & E_FLAGS.EF_ARM_HASENTRY:
                description += ", has entry point"

            version = flags & E_FLAGS.EF_ARM_EABIMASK
            if version == E_FLAGS.EF_ARM_EABI_VER5:
                description += ", Version5 EABI"
        return description

    def display_program_headers(self, show_heading=True):
        """ Display the ELF program headers.
            If show_heading is True, displays the heading for this information
            (Elf file type is...)
        """
        self._emitline()
        if self.elffile.num_segments() == 0:
            self._emitline('There are no program headers in this file.')
            return

        elfheader = self.elffile.header
        if show_heading:
            self._emitline('Elf file type is %s' %
                describe_e_type(elfheader['e_type']))
            self._emitline('Entry point is %s' %
                self._format_hex(elfheader['e_entry']))
            # readelf weirness - why isn't e_phoff printed as hex? (for section
            # headers, it is...)
            self._emitline('There are %s program headers, starting at offset %s' % (
                elfheader['e_phnum'], elfheader['e_phoff']))
            self._emitline()

        self._emitline('Program Headers:')

        # Now comes the table of program headers with their attributes. Note
        # that due to different formatting constraints of 32-bit and 64-bit
        # addresses, there are some conditions on elfclass here.
        #
        # First comes the table heading
        #
        if self.elffile.elfclass == 32:
            self._emitline('  Type           Offset   VirtAddr   PhysAddr   FileSiz MemSiz  Flg Align')
        else:
            self._emitline('  Type           Offset             VirtAddr           PhysAddr')
            self._emitline('                 FileSiz            MemSiz              Flags  Align')

        # Now the entries
        #
        for segment in self.elffile.iter_segments():
            self._emit('  %-14s ' % describe_p_type(segment['p_type']))

            if self.elffile.elfclass == 32:
                self._emitline('%s %s %s %s %s %-3s %s' % (
                    self._format_hex(segment['p_offset'], fieldsize=6),
                    self._format_hex(segment['p_vaddr'], fullhex=True),
                    self._format_hex(segment['p_paddr'], fullhex=True),
                    self._format_hex(segment['p_filesz'], fieldsize=5),
                    self._format_hex(segment['p_memsz'], fieldsize=5),
                    describe_p_flags(segment['p_flags']),
                    self._format_hex(segment['p_align'])))
            else: # 64
                self._emitline('%s %s %s' % (
                    self._format_hex(segment['p_offset'], fullhex=True),
                    self._format_hex(segment['p_vaddr'], fullhex=True),
                    self._format_hex(segment['p_paddr'], fullhex=True)))
                self._emitline('                 %s %s  %-3s    %s' % (
                    self._format_hex(segment['p_filesz'], fullhex=True),
                    self._format_hex(segment['p_memsz'], fullhex=True),
                    describe_p_flags(segment['p_flags']),
                    # lead0x set to False for p_align, to mimic readelf.
                    # No idea why the difference from 32-bit mode :-|
                    self._format_hex(segment['p_align'], lead0x=False)))

            if isinstance(segment, InterpSegment):
                self._emitline('      [Requesting program interpreter: %s]' %
                    bytes2str(segment.get_interp_name()))

        # Sections to segments mapping
        #
        if self.elffile.num_sections() == 0:
            # No sections? We're done
            return

        self._emitline('\n Section to Segment mapping:')
        self._emitline('  Segment Sections...')

        for nseg, segment in enumerate(self.elffile.iter_segments()):
            self._emit('   %2.2d     ' % nseg)

            for section in self.elffile.iter_sections():
                if (    not section.is_null() and
                        segment.section_in_segment(section)):
                    self._emit('%s ' % bytes2str(section.name))

            self._emitline('')

    def display_section_headers(self, show_heading=True):
        """ Display the ELF section headers
        """
        elfheader = self.elffile.header
        if show_heading:
            self._emitline('There are %s section headers, starting at offset %s' % (
                elfheader['e_shnum'], self._format_hex(elfheader['e_shoff'])))

        self._emitline('\nSection Header%s:' % (
            's' if elfheader['e_shnum'] > 1 else ''))

        # Different formatting constraints of 32-bit and 64-bit addresses
        #
        if self.elffile.elfclass == 32:
            self._emitline('  [Nr] Name              Type            Addr     Off    Size   ES Flg Lk Inf Al')
        else:
            self._emitline('  [Nr] Name              Type             Address           Offset')
            self._emitline('       Size              EntSize          Flags  Link  Info  Align')

        # Now the entries
        #
        for nsec, section in enumerate(self.elffile.iter_sections()):
            self._emit('  [%2u] %-17.17s %-15.15s ' % (
                nsec, bytes2str(section.name), describe_sh_type(section['sh_type'])))

            if self.elffile.elfclass == 32:
                self._emitline('%s %s %s %s %3s %2s %3s %2s' % (
                    self._format_hex(section['sh_addr'], fieldsize=8, lead0x=False),
                    self._format_hex(section['sh_offset'], fieldsize=6, lead0x=False),
                    self._format_hex(section['sh_size'], fieldsize=6, lead0x=False),
                    self._format_hex(section['sh_entsize'], fieldsize=2, lead0x=False),
                    describe_sh_flags(section['sh_flags']),
                    section['sh_link'], section['sh_info'],
                    section['sh_addralign']))
            else: # 64
                self._emitline(' %s  %s' % (
                    self._format_hex(section['sh_addr'], fullhex=True, lead0x=False),
                    self._format_hex(section['sh_offset'],
                        fieldsize=16 if section['sh_offset'] > 0xffffffff else 8,
                        lead0x=False)))
                self._emitline('       %s  %s %3s      %2s   %3s     %s' % (
                    self._format_hex(section['sh_size'], fullhex=True, lead0x=False),
                    self._format_hex(section['sh_entsize'], fullhex=True, lead0x=False),
                    describe_sh_flags(section['sh_flags']),
                    section['sh_link'], section['sh_info'],
                    section['sh_addralign']))

        self._emitline('Key to Flags:')
        self._emit('  W (write), A (alloc), X (execute), M (merge), S (strings)')
        if self.elffile['e_machine'] in ('EM_X86_64', 'EM_L10M'):
            self._emitline(', l (large)')
        else:
            self._emitline()
        self._emitline('  I (info), L (link order), G (group), T (TLS), E (exclude), x (unknown)')
        self._emitline('  O (extra OS processing required) o (OS specific), p (processor specific)')

    def display_symbol_tables(self):
        """ Display the symbol tables contained in the file
        """
        self._init_versioninfo()

        for section in self.elffile.iter_sections():
            if not isinstance(section, SymbolTableSection):
                continue

            if section['sh_entsize'] == 0:
                self._emitline("\nSymbol table '%s' has a sh_entsize of zero!" % (
                    bytes2str(section.name)))
                continue

            self._emitline("\nSymbol table '%s' contains %s entries:" % (
                bytes2str(section.name), section.num_symbols()))

            if self.elffile.elfclass == 32:
                self._emitline('   Num:    Value  Size Type    Bind   Vis      Ndx Name')
            else: # 64
                self._emitline('   Num:    Value          Size Type    Bind   Vis      Ndx Name')

            for nsym, symbol in enumerate(section.iter_symbols()):

                version_info = ''
                # readelf doesn't display version info for Solaris versioning
                if (section['sh_type'] == 'SHT_DYNSYM' and
                        self._versioninfo['type'] == 'GNU'):
                    version = self._symbol_version(nsym)
                    if (version['name'] != bytes2str(symbol.name) and
                        version['index'] not in ('VER_NDX_LOCAL',
                                                 'VER_NDX_GLOBAL')):
                        if version['filename']:
                            # external symbol
                            version_info = '@%(name)s (%(index)i)' % version
                        else:
                            # internal symbol
                            if version['hidden']:
                                version_info = '@%(name)s' % version
                            else:
                                version_info = '@@%(name)s' % version

                # symbol names are truncated to 25 chars, similarly to readelf
                self._emitline('%6d: %s %5d %-7s %-6s %-7s %4s %.25s%s' % (
                    nsym,
                    self._format_hex(
                        symbol['st_value'], fullhex=True, lead0x=False),
                    symbol['st_size'],
                    describe_symbol_type(symbol['st_info']['type']),
                    describe_symbol_bind(symbol['st_info']['bind']),
                    describe_symbol_visibility(symbol['st_other']['visibility']),
                    describe_symbol_shndx(symbol['st_shndx']),
                    bytes2str(symbol.name),
                    version_info))

    def display_dynamic_tags(self):
        """ Display the dynamic tags contained in the file
        """
        has_dynamic_sections = False
        for section in self.elffile.iter_sections():
            if not isinstance(section, DynamicSection):
                continue

            has_dynamic_sections = True
            self._emitline("\nDynamic section at offset %s contains %s entries:" % (
                self._format_hex(section['sh_offset']),
                section.num_tags()))
            self._emitline("  Tag        Type                         Name/Value")

            padding = 20 + (8 if self.elffile.elfclass == 32 else 0)
            for tag in section.iter_tags():
                if tag.entry.d_tag == 'DT_NEEDED':
                    parsed = 'Shared library: [%s]' % bytes2str(tag.needed)
                elif tag.entry.d_tag == 'DT_RPATH':
                    parsed = 'Library rpath: [%s]' % bytes2str(tag.rpath)
                elif tag.entry.d_tag == 'DT_RUNPATH':
                    parsed = 'Library runpath: [%s]' % bytes2str(tag.runpath)
                elif tag.entry.d_tag == 'DT_SONAME':
                    parsed = 'Library soname: [%s]' % bytes2str(tag.soname)
                elif tag.entry.d_tag.endswith(('SZ', 'ENT')):
                    parsed = '%i (bytes)' % tag['d_val']
                elif tag.entry.d_tag.endswith(('NUM', 'COUNT')):
                    parsed = '%i' % tag['d_val']
                elif tag.entry.d_tag == 'DT_PLTREL':
                    s = describe_dyn_tag(tag.entry.d_val)
                    if s.startswith('DT_'):
                        s = s[3:]
                    parsed = '%s' % s
                else:
                    parsed = '%#x' % tag['d_val']

                self._emitline(" %s %-*s %s" % (
                    self._format_hex(ENUM_D_TAG.get(tag.entry.d_tag, tag.entry.d_tag),
                        fullhex=True, lead0x=True),
                    padding,
                    '(%s)' % (tag.entry.d_tag[3:],),
                    parsed))
        if not has_dynamic_sections:
            # readelf only prints this if there is at least one segment
            if self.elffile.num_segments():
                self._emitline("\nThere is no dynamic section in this file.")

    def display_relocations(self):
        """ Display the relocations contained in the file
        """
        has_relocation_sections = False
        for section in self.elffile.iter_sections():
            if not isinstance(section, RelocationSection):
                continue

            has_relocation_sections = True
            self._emitline("\nRelocation section '%s' at offset %s contains %s entries:" % (
                bytes2str(section.name),
                self._format_hex(section['sh_offset']),
                section.num_relocations()))
            if section.is_RELA():
                self._emitline("  Offset          Info           Type           Sym. Value    Sym. Name + Addend")
            else:
                self._emitline(" Offset     Info    Type            Sym.Value  Sym. Name")

            # The symbol table section pointed to in sh_link
            symtable = self.elffile.get_section(section['sh_link'])

            for rel in section.iter_relocations():
                hexwidth = 8 if self.elffile.elfclass == 32 else 12
                self._emit('%s  %s %-17.17s' % (
                    self._format_hex(rel['r_offset'],
                        fieldsize=hexwidth, lead0x=False),
                    self._format_hex(rel['r_info'],
                        fieldsize=hexwidth, lead0x=False),
                    describe_reloc_type(
                        rel['r_info_type'], self.elffile)))

                if rel['r_info_sym'] == 0:
                    self._emitline()
                    continue

                symbol = symtable.get_symbol(rel['r_info_sym'])
                # Some symbols have zero 'st_name', so instead what's used is
                # the name of the section they point at
                if symbol['st_name'] == 0:
                    symsec = self.elffile.get_section(symbol['st_shndx'])
                    symbol_name = symsec.name
                else:
                    symbol_name = symbol.name
                self._emit(' %s %s%22.22s' % (
                    self._format_hex(
                        symbol['st_value'],
                        fullhex=True, lead0x=False),
                    '  ' if self.elffile.elfclass == 32 else '',
                    bytes2str(symbol_name)))
                if section.is_RELA():
                    self._emit(' %s %x' % (
                        '+' if rel['r_addend'] >= 0 else '-',
                        abs(rel['r_addend'])))
                self._emitline()

        if not has_relocation_sections:
            self._emitline('\nThere are no relocations in this file.')

    def display_version_info(self):
        """ Display the version info contained in the file
        """
        self._init_versioninfo()

        if not self._versioninfo['type']:
            self._emitline("\nNo version information found in this file.")
            return

        for section in self.elffile.iter_sections():
            if isinstance(section, GNUVerSymSection):
                self._print_version_section_header(
                    section, 'Version symbols', lead0x=False)

                num_symbols = section.num_symbols()
    
                # Symbol version info are printed four by four entries 
                for idx_by_4 in range(0, num_symbols, 4):

                    self._emit('  %03x:' % idx_by_4)

                    for idx in range(idx_by_4, min(idx_by_4 + 4, num_symbols)):

                        symbol_version = self._symbol_version(idx)
                        if symbol_version['index'] == 'VER_NDX_LOCAL':
                            version_index = 0
                            version_name = '(*local*)'
                        elif symbol_version['index'] == 'VER_NDX_GLOBAL':
                            version_index = 1
                            version_name = '(*global*)'
                        else:
                            version_index = symbol_version['index']
                            version_name = '(%(name)s)' % symbol_version

                        visibility = 'h' if symbol_version['hidden'] else ' '

                        self._emit('%4x%s%-13s' % (
                            version_index, visibility, version_name))

                    self._emitline()

            elif isinstance(section, GNUVerDefSection):
                self._print_version_section_header(
                    section, 'Version definition', indent=2)

                offset = 0
                for verdef, verdaux_iter in section.iter_versions():
                    verdaux = next(verdaux_iter)

                    name = verdaux.name
                    if verdef['vd_flags']:
                        flags = describe_ver_flags(verdef['vd_flags'])
                        # Mimic exactly the readelf output
                        flags += ' '
                    else:
                        flags = 'none'

                    self._emitline('  %s: Rev: %i  Flags: %s  Index: %i'
                                   '  Cnt: %i  Name: %s' % (
                            self._format_hex(offset, fieldsize=6,
                                             alternate=True),
                            verdef['vd_version'], flags, verdef['vd_ndx'],
                            verdef['vd_cnt'], bytes2str(name)))

                    verdaux_offset = (
                            offset + verdef['vd_aux'] + verdaux['vda_next'])
                    for idx, verdaux in enumerate(verdaux_iter, start=1):
                        self._emitline('  %s: Parent %i: %s' %
                            (self._format_hex(verdaux_offset, fieldsize=4),
                                              idx, bytes2str(verdaux.name)))
                        verdaux_offset += verdaux['vda_next']

                    offset += verdef['vd_next']

            elif isinstance(section, GNUVerNeedSection):
                self._print_version_section_header(section, 'Version needs')

                offset = 0
                for verneed, verneed_iter in section.iter_versions():

                    self._emitline('  %s: Version: %i  File: %s  Cnt: %i' % (
                            self._format_hex(offset, fieldsize=6,
                                             alternate=True),
                            verneed['vn_version'], bytes2str(verneed.name),
                            verneed['vn_cnt']))

                    vernaux_offset = offset + verneed['vn_aux']
                    for idx, vernaux in enumerate(verneed_iter, start=1):
                        if vernaux['vna_flags']:
                            flags = describe_ver_flags(vernaux['vna_flags'])
                            # Mimic exactly the readelf output
                            flags += ' '
                        else:
                            flags = 'none'

                        self._emitline(
                            '  %s:   Name: %s  Flags: %s  Version: %i' % (
                                self._format_hex(vernaux_offset, fieldsize=4),
                                bytes2str(vernaux.name), flags,
                                vernaux['vna_other']))

                        vernaux_offset += vernaux['vna_next']

                    offset += verneed['vn_next']

    def display_hex_dump(self, section_spec):
        """ Display a hex dump of a section. section_spec is either a section
            number or a name.
        """
        section = self._section_from_spec(section_spec)
        if section is None:
            self._emitline("Section '%s' does not exist in the file!" % (
                section_spec))
            return

        self._emitline("\nHex dump of section '%s':" % bytes2str(section.name))
        self._note_relocs_for_section(section)
        addr = section['sh_addr']
        data = section.data()
        dataptr = 0

        while dataptr < len(data):
            bytesleft = len(data) - dataptr
            # chunks of 16 bytes per line
            linebytes = 16 if bytesleft > 16 else bytesleft

            self._emit('  %s ' % self._format_hex(addr, fieldsize=8))
            for i in range(16):
                if i < linebytes:
                    self._emit('%2.2x' % byte2int(data[dataptr + i]))
                else:
                    self._emit('  ')
                if i % 4 == 3:
                    self._emit(' ')

            for i in range(linebytes):
                c = data[dataptr + i : dataptr + i + 1]
                if byte2int(c[0]) >= 32 and byte2int(c[0]) < 0x7f:
                    self._emit(bytes2str(c))
                else:
                    self._emit(bytes2str(b'.'))

            self._emitline()
            addr += linebytes
            dataptr += linebytes

        self._emitline()

    def display_string_dump(self, section_spec):
        """ Display a strings dump of a section. section_spec is either a
            section number or a name.
        """
        section = self._section_from_spec(section_spec)
        if section is None:
            self._emitline("Section '%s' does not exist in the file!" % (
                section_spec))
            return

        self._emitline("\nString dump of section '%s':" % bytes2str(section.name))

        found = False
        data = section.data()
        dataptr = 0

        while dataptr < len(data):
            while ( dataptr < len(data) and
                    not (32 <= byte2int(data[dataptr]) <= 127)):
                dataptr += 1

            if dataptr >= len(data):
                break

            endptr = dataptr
            while endptr < len(data) and byte2int(data[endptr]) != 0:
                endptr += 1

            found = True
            self._emitline('  [%6x]  %s' % (
                dataptr, bytes2str(data[dataptr:endptr])))

            dataptr = endptr

        if not found:
            self._emitline('  No strings found in this section.')
        else:
            self._emitline()

    def display_debug_dump(self, dump_what):
        """ Dump a DWARF section
        """
        self._init_dwarfinfo()
        if self._dwarfinfo is None:
            return

        set_global_machine_arch(self.elffile.get_machine_arch())

        if dump_what == 'info':
            self._dump_debug_info()
        elif dump_what == 'decodedline':
            self._dump_debug_line_programs()
        elif dump_what == 'frames':
            self._dump_debug_frames()
        elif dump_what == 'frames-interp':
            self._dump_debug_frames_interp()
        else:
            self._emitline('debug dump not yet supported for "%s"' % dump_what)

    def _format_hex(self, addr, fieldsize=None, fullhex=False, lead0x=True,
                    alternate=False):
        """ Format an address into a hexadecimal string.

            fieldsize:
                Size of the hexadecimal field (with leading zeros to fit the
                address into. For example with fieldsize=8, the format will
                be %08x
                If None, the minimal required field size will be used.

            fullhex:
                If True, override fieldsize to set it to the maximal size
                needed for the elfclass

            lead0x:
                If True, leading 0x is added

            alternate:
                If True, override lead0x to emulate the alternate
                hexadecimal form specified in format string with the #
                character: only non-zero values are prefixed with 0x.
                This form is used by readelf.
        """
        if alternate:
            if addr == 0:
                lead0x = False
            else:
                lead0x = True
                fieldsize -= 2

        s = '0x' if lead0x else ''
        if fullhex:
            fieldsize = 8 if self.elffile.elfclass == 32 else 16
        if fieldsize is None:
            field = '%x'
        else:
            field = '%' + '0%sx' % fieldsize
        return s + field % addr

    def _print_version_section_header(self, version_section, name, lead0x=True,
                                      indent=1):
        """ Print a section header of one version related section (versym,
            verneed or verdef) with some options to accomodate readelf
            little differences between each header (e.g. indentation
            and 0x prefixing).
        """
        if hasattr(version_section, 'num_versions'):
            num_entries = version_section.num_versions()
        else:
            num_entries = version_section.num_symbols()

        self._emitline("\n%s section '%s' contains %s entries:" %
            (name, bytes2str(version_section.name), num_entries))
        self._emitline('%sAddr: %s  Offset: %s  Link: %i (%s)' % (
            ' ' * indent,
            self._format_hex(
                version_section['sh_addr'], fieldsize=16, lead0x=lead0x),
            self._format_hex(
                version_section['sh_offset'], fieldsize=6, lead0x=True),
            version_section['sh_link'],
            bytes2str(
                self.elffile.get_section(version_section['sh_link']).name)
            )
        )

    def _init_versioninfo(self):
        """ Search and initialize informations about version related sections
            and the kind of versioning used (GNU or Solaris).
        """
        if self._versioninfo is not None:
            return

        self._versioninfo = {'versym': None, 'verdef': None,
                             'verneed': None, 'type': None}

        for section in self.elffile.iter_sections():
            if isinstance(section, GNUVerSymSection):
                self._versioninfo['versym'] = section
            elif isinstance(section, GNUVerDefSection):
                self._versioninfo['verdef'] = section
            elif isinstance(section, GNUVerNeedSection):
                self._versioninfo['verneed'] = section
            elif isinstance(section, DynamicSection):
                for tag in section.iter_tags():
                    if tag['d_tag'] == 'DT_VERSYM':
                        self._versioninfo['type'] = 'GNU'
                        break

        if not self._versioninfo['type'] and (
                self._versioninfo['verneed'] or self._versioninfo['verdef']):
            self._versioninfo['type'] = 'Solaris'

    def _symbol_version(self, nsym):
        """ Return a dict containing information on the
                   or None if no version information is available
        """
        self._init_versioninfo()

        symbol_version = dict.fromkeys(('index', 'name', 'filename', 'hidden'))

        if (not self._versioninfo['versym'] or
                nsym >= self._versioninfo['versym'].num_symbols()):
            return None

        symbol = self._versioninfo['versym'].get_symbol(nsym)
        index = symbol.entry['ndx']
        if not index in ('VER_NDX_LOCAL', 'VER_NDX_GLOBAL'):
            index = int(index)

            if self._versioninfo['type'] == 'GNU':
                # In GNU versioning mode, the highest bit is used to
                # store wether the symbol is hidden or not
                if index & 0x8000:
                    index &= ~0x8000
                    symbol_version['hidden'] = True

            if (self._versioninfo['verdef'] and
                    index <= self._versioninfo['verdef'].num_versions()):
                _, verdaux_iter = \
                        self._versioninfo['verdef'].get_version(index)
                symbol_version['name'] = bytes2str(next(verdaux_iter).name)
            else:
                verneed, vernaux = \
                        self._versioninfo['verneed'].get_version(index)
                symbol_version['name'] = bytes2str(vernaux.name)
                symbol_version['filename'] = bytes2str(verneed.name)

        symbol_version['index'] = index
        return symbol_version

    def _section_from_spec(self, spec):
        """ Retrieve a section given a "spec" (either number or name).
            Return None if no such section exists in the file.
        """
        try:
            num = int(spec)
            if num < self.elffile.num_sections():
                return self.elffile.get_section(num)
            else:
                return None
        except ValueError:
            # Not a number. Must be a name then
            return self.elffile.get_section_by_name(str2bytes(spec))

    def _note_relocs_for_section(self, section):
        """ If there are relocation sections pointing to the givne section,
            emit a note about it.
        """
        for relsec in self.elffile.iter_sections():
            if isinstance(relsec, RelocationSection):
                info_idx = relsec['sh_info']
                if self.elffile.get_section(info_idx) == section:
                    self._emitline('  Note: This section has relocations against it, but these have NOT been applied to this dump.')
                    return

    def _init_dwarfinfo(self):
        """ Initialize the DWARF info contained in the file and assign it to
            self._dwarfinfo.
            Leave self._dwarfinfo at None if no DWARF info was found in the file
        """
        if self._dwarfinfo is not None:
            return

        if self.elffile.has_dwarf_info():
            self._dwarfinfo = self.elffile.get_dwarf_info()
        else:
            self._dwarfinfo = None

    def _dump_debug_info(self):
        """ Dump the debugging info section.
        """
        self._emitline('Contents of the .debug_info section:\n')

        # Offset of the .debug_info section in the stream
        section_offset = self._dwarfinfo.debug_info_sec.global_offset

        for cu in self._dwarfinfo.iter_CUs():
            self._emitline('  Compilation Unit @ offset %s:' %
                self._format_hex(cu.cu_offset))
            self._emitline('   Length:        %s (%s)' % (
                self._format_hex(cu['unit_length']),
                '%s-bit' % cu.dwarf_format()))
            self._emitline('   Version:       %s' % cu['version']),
            self._emitline('   Abbrev Offset: %s' % (
                self._format_hex(cu['debug_abbrev_offset']))),
            self._emitline('   Pointer Size:  %s' % cu['address_size'])

            # The nesting depth of each DIE within the tree of DIEs must be
            # displayed. To implement this, a counter is incremented each time
            # the current DIE has children, and decremented when a null die is
            # encountered. Due to the way the DIE tree is serialized, this will
            # correctly reflect the nesting depth
            #
            die_depth = 0
            for die in cu.iter_DIEs():
                self._emitline(' <%s><%x>: Abbrev Number: %s%s' % (
                    die_depth,
                    die.offset,
                    die.abbrev_code,
                    (' (%s)' % die.tag) if not die.is_null() else ''))
                if die.is_null():
                    die_depth -= 1
                    continue

                for attr in itervalues(die.attributes):
                    name = attr.name
                    # Unknown attribute values are passed-through as integers
                    if isinstance(name, int):
                        name = 'Unknown AT value: %x' % name
                    self._emitline('    <%2x>   %-18s: %s' % (
                        attr.offset,
                        name,
                        describe_attr_value(
                            attr, die, section_offset)))

                if die.has_children:
                    die_depth += 1

        self._emitline()

    def _dump_debug_line_programs(self):
        """ Dump the (decoded) line programs from .debug_line
            The programs are dumped in the order of the CUs they belong to.
        """
        self._emitline('Decoded dump of debug contents of section .debug_line:\n')

        for cu in self._dwarfinfo.iter_CUs():
            lineprogram = self._dwarfinfo.line_program_for_CU(cu)

            cu_filename = bytes2str(lineprogram['file_entry'][0].name)
            if len(lineprogram['include_directory']) > 0:
                dir_index = lineprogram['file_entry'][0].dir_index
                if dir_index > 0:
                    dir = lineprogram['include_directory'][dir_index - 1]
                else:
                    dir = b'.'
                cu_filename = '%s/%s' % (bytes2str(dir), cu_filename)

            self._emitline('CU: %s:' % cu_filename)
            self._emitline('File name                            Line number    Starting address')

            # Print each state's file, line and address information. For some
            # instructions other output is needed to be compatible with
            # readelf.
            for entry in lineprogram.get_entries():
                state = entry.state
                if state is None:
                    # Special handling for commands that don't set a new state
                    if entry.command == DW_LNS_set_file:
                        file_entry = lineprogram['file_entry'][entry.args[0] - 1]
                        if file_entry.dir_index == 0:
                            # current directory
                            self._emitline('\n./%s:[++]' % (
                                bytes2str(file_entry.name)))
                        else:
                            self._emitline('\n%s/%s:' % (
                                bytes2str(lineprogram['include_directory'][file_entry.dir_index - 1]),
                                bytes2str(file_entry.name)))
                    elif entry.command == DW_LNE_define_file:
                        self._emitline('%s:' % (
                            bytes2str(lineprogram['include_directory'][entry.args[0].dir_index])))
                elif not state.end_sequence:
                    # readelf doesn't print the state after end_sequence
                    # instructions. I think it's a bug but to be compatible
                    # I don't print them too.
                    self._emitline('%-35s  %11d  %18s' % (
                        bytes2str(lineprogram['file_entry'][state.file - 1].name),
                        state.line,
                        '0' if state.address == 0 else
                               self._format_hex(state.address)))
                if entry.command == DW_LNS_copy:
                    # Another readelf oddity...
                    self._emitline()

    def _dump_debug_frames(self):
        """ Dump the raw frame information from .debug_frame
        """
        if not self._dwarfinfo.has_CFI():
            return
        self._emitline('Contents of the .debug_frame section:')

        for entry in self._dwarfinfo.CFI_entries():
            if isinstance(entry, CIE):
                self._emitline('\n%08x %s %s CIE' % (
                    entry.offset,
                    self._format_hex(entry['length'], fullhex=True, lead0x=False),
                    self._format_hex(entry['CIE_id'], fullhex=True, lead0x=False)))
                self._emitline('  Version:               %d' % entry['version'])
                self._emitline('  Augmentation:          "%s"' % bytes2str(entry['augmentation']))
                self._emitline('  Code alignment factor: %u' % entry['code_alignment_factor'])
                self._emitline('  Data alignment factor: %d' % entry['data_alignment_factor'])
                self._emitline('  Return address column: %d' % entry['return_address_register'])
                self._emitline()
            else: # FDE
                self._emitline('\n%08x %s %s FDE cie=%08x pc=%s..%s' % (
                    entry.offset,
                    self._format_hex(entry['length'], fullhex=True, lead0x=False),
                    self._format_hex(entry['CIE_pointer'], fullhex=True, lead0x=False),
                    entry.cie.offset,
                    self._format_hex(entry['initial_location'], fullhex=True, lead0x=False),
                    self._format_hex(
                        entry['initial_location'] + entry['address_range'],
                        fullhex=True, lead0x=False)))

            self._emit(describe_CFI_instructions(entry))
        self._emitline()

    def _dump_debug_frames_interp(self):
        """ Dump the interpreted (decoded) frame information from .debug_frame
        """
        if not self._dwarfinfo.has_CFI():
            return

        self._emitline('Contents of the .debug_frame section:')

        for entry in self._dwarfinfo.CFI_entries():
            if isinstance(entry, CIE):
                self._emitline('\n%08x %s %s CIE "%s" cf=%d df=%d ra=%d' % (
                    entry.offset,
                    self._format_hex(entry['length'], fullhex=True, lead0x=False),
                    self._format_hex(entry['CIE_id'], fullhex=True, lead0x=False),
                    bytes2str(entry['augmentation']),
                    entry['code_alignment_factor'],
                    entry['data_alignment_factor'],
                    entry['return_address_register']))
                ra_regnum = entry['return_address_register']
            else: # FDE
                self._emitline('\n%08x %s %s FDE cie=%08x pc=%s..%s' % (
                    entry.offset,
                    self._format_hex(entry['length'], fullhex=True, lead0x=False),
                    self._format_hex(entry['CIE_pointer'], fullhex=True, lead0x=False),
                    entry.cie.offset,
                    self._format_hex(entry['initial_location'], fullhex=True, lead0x=False),
                    self._format_hex(entry['initial_location'] + entry['address_range'],
                        fullhex=True, lead0x=False)))
                ra_regnum = entry.cie['return_address_register']

            # Print the heading row for the decoded table
            self._emit('   LOC')
            self._emit('  ' if entry.structs.address_size == 4 else '          ')
            self._emit(' CFA      ')

            # Decode the table nad look at the registers it describes.
            # We build reg_order here to match readelf's order. In particular,
            # registers are sorted by their number, and the register matching
            # ra_regnum is always listed last with a special heading.
            decoded_table = entry.get_decoded()
            reg_order = sorted(ifilter(
                lambda r: r != ra_regnum,
                decoded_table.reg_order))

            # Headings for the registers
            for regnum in reg_order:
                self._emit('%-6s' % describe_reg_name(regnum))
            self._emitline('ra      ')

            # Now include ra_regnum in reg_order to print its values similarly
            # to the other registers.
            reg_order.append(ra_regnum)
            for line in decoded_table.table:
                self._emit(self._format_hex(
                    line['pc'], fullhex=True, lead0x=False))
                self._emit(' %-9s' % describe_CFI_CFA_rule(line['cfa']))

                for regnum in reg_order:
                    if regnum in line:
                        s = describe_CFI_register_rule(line[regnum])
                    else:
                        s = 'u'
                    self._emit('%-6s' % s)
                self._emitline()
        self._emitline()

    def _emit(self, s=''):
        """ Emit an object to output
        """
        self.output.write(str(s))

    def _emitline(self, s=''):
        """ Emit an object to output, followed by a newline
        """
        self.output.write(str(s) + '\n')


SCRIPT_DESCRIPTION = 'Display information about the contents of ELF format files'
VERSION_STRING = '%%prog: based on pyelftools %s' % __version__


def main(stream=None):
    # parse the command-line arguments and invoke ReadElf
    optparser = OptionParser(
            usage='usage: %prog [options] <elf-file>',
            description=SCRIPT_DESCRIPTION,
            add_help_option=False, # -h is a real option of readelf
            prog='readelf.py',
            version=VERSION_STRING)
    optparser.add_option('-d', '--dynamic',
            action='store_true', dest='show_dynamic_tags',
            help='Display the dynamic section')
    optparser.add_option('-H', '--help',
            action='store_true', dest='help',
            help='Display this information')
    optparser.add_option('-h', '--file-header',
            action='store_true', dest='show_file_header',
            help='Display the ELF file header')
    optparser.add_option('-l', '--program-headers', '--segments',
            action='store_true', dest='show_program_header',
            help='Display the program headers')
    optparser.add_option('-S', '--section-headers', '--sections',
            action='store_true', dest='show_section_header',
            help="Display the sections' headers")
    optparser.add_option('-e', '--headers',
            action='store_true', dest='show_all_headers',
            help='Equivalent to: -h -l -S')
    optparser.add_option('-s', '--symbols', '--syms',
            action='store_true', dest='show_symbols',
            help='Display the symbol table')
    optparser.add_option('-r', '--relocs',
            action='store_true', dest='show_relocs',
            help='Display the relocations (if present)')
    optparser.add_option('-x', '--hex-dump',
            action='store', dest='show_hex_dump', metavar='<number|name>',
            help='Dump the contents of section <number|name> as bytes')
    optparser.add_option('-p', '--string-dump',
            action='store', dest='show_string_dump', metavar='<number|name>',
            help='Dump the contents of section <number|name> as strings')
    optparser.add_option('-V', '--version-info',
            action='store_true', dest='show_version_info',
            help='Display the version sections (if present)')
    optparser.add_option('--debug-dump',
            action='store', dest='debug_dump_what', metavar='<what>',
            help=(
                'Display the contents of DWARF debug sections. <what> can ' +
                'one of {info,decodedline,frames,frames-interp}'))

    options, args = optparser.parse_args()

    if options.help or len(args) == 0:
        optparser.print_help()
        sys.exit(0)

    if options.show_all_headers:
        do_file_header = do_section_header = do_program_header = True
    else:
        do_file_header = options.show_file_header
        do_section_header = options.show_section_header
        do_program_header = options.show_program_header

    with open(args[0], 'rb') as file:
        try:
            readelf = ReadElf(file, stream or sys.stdout)
            if do_file_header:
                readelf.display_file_header()
            if do_section_header:
                readelf.display_section_headers(
                        show_heading=not do_file_header)
            if do_program_header:
                readelf.display_program_headers(
                        show_heading=not do_file_header)
            if options.show_dynamic_tags:
                readelf.display_dynamic_tags()
            if options.show_symbols:
                readelf.display_symbol_tables()
            if options.show_relocs:
                readelf.display_relocations()
            if options.show_version_info:
                readelf.display_version_info()
            if options.show_hex_dump:
                readelf.display_hex_dump(options.show_hex_dump)
            if options.show_string_dump:
                readelf.display_string_dump(options.show_string_dump)
            if options.debug_dump_what:
                readelf.display_debug_dump(options.debug_dump_what)
        except ELFError as ex:
            sys.stderr.write('ELF error: %s\n' % ex)
            sys.exit(1)


def profile_main():
    # Run 'main' redirecting its output to readelfout.txt
    # Saves profiling information in readelf.profile
    PROFFILE = 'readelf.profile'
    import cProfile
    cProfile.run('main(open("readelfout.txt", "w"))', PROFFILE)

    # Dig in some profiling stats
    import pstats
    p = pstats.Stats(PROFFILE)
    p.sort_stats('cumulative').print_stats(25)


#-------------------------------------------------------------------------------
if __name__ == '__main__':
    main()
    #profile_main()



########NEW FILE########
__FILENAME__ = all_tests
#!/usr/bin/env python
#-------------------------------------------------------------------------------
# test/all_tests.py
#
# Run all pyelftools tests.
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
from __future__ import print_function
import subprocess, sys
from utils import is_in_rootdir

def run_test_script(path):
    cmd = [sys.executable, path]
    print("Running '%s'" % ' '.join(cmd))
    subprocess.check_call(cmd)

def main():
    if not is_in_rootdir():
        testlog.error('Error: Please run me from the root dir of pyelftools!')
        return 1
    run_test_script('test/run_all_unittests.py')
    run_test_script('test/run_examples_test.py')
    run_test_script('test/run_readelf_tests.py')

if __name__ == '__main__':
    sys.exit(main())

########NEW FILE########
__FILENAME__ = run_all_unittests
#!/usr/bin/env python
#-------------------------------------------------------------------------------
# test/run_all_unittests.py
#
# Run all unit tests (alternative to running 'python -m unittest discover ...')
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
from __future__ import print_function

import os, sys

try:
    import unittest2 as unittest
except ImportError:
    import unittest


def main():
    if not os.path.isdir('test'):
        print('!! Please execute from the root directory of pyelftools')
        return 1
    else:
        tests = unittest.TestLoader().discover('test', 'test*.py', 'test')
        result = unittest.TextTestRunner().run(tests)
        if result.wasSuccessful():
            return 0
        else:
            return 1

if __name__ == '__main__':
    sys.exit(main())

########NEW FILE########
__FILENAME__ = run_examples_test
#!/usr/bin/env python
#-------------------------------------------------------------------------------
# test/run_examples_test.py
#
# Run the examples and compare their output to a reference
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
import os, sys
import logging
from utils import setup_syspath; setup_syspath()
from utils import run_exe, is_in_rootdir, dump_output_to_temp_files


# Create a global logger object
#
testlog = logging.getLogger('run_examples_test')
testlog.setLevel(logging.DEBUG)
testlog.addHandler(logging.StreamHandler(sys.stdout))


def discover_examples():
    """ Return paths to all example scripts. Assume we're in the root source
        dir of pyelftools.
    """
    root = './examples'
    for filename in os.listdir(root):
        if os.path.splitext(filename)[1] == '.py':
            yield os.path.join(root, filename)


def reference_output_path(example_path):
    """ Compute the reference output path from a given example path.
    """
    examples_root, example_name = os.path.split(example_path)
    example_noext, _ = os.path.splitext(example_name)
    return os.path.join(examples_root, 'reference_output', example_noext + '.out')


def run_example_and_compare(example_path):
    testlog.info("Example '%s'" % example_path)

    reference_path = reference_output_path(example_path)
    ref_str = ''
    try:
        with open(reference_path) as ref_f:
            ref_str = ref_f.read()
    except (IOError, OSError) as e:
        testlog.info('.......ERROR - reference output cannot be read! - %s' % e)
        return False

    rc, example_out = run_exe(example_path, ['./examples/sample_exe64.elf'])
    if rc != 0:
        testlog.info('.......ERROR - example returned error code %s' % rc)
        return False

    # Comparison is done as lists of lines, to avoid EOL problems
    if example_out.split() == ref_str.split():
        return True
    else:
        testlog.info('.......FAIL comparison')
        dump_output_to_temp_files(testlog, example_out)
        return False


def main():
    if not is_in_rootdir():
        testlog.error('Error: Please run me from the root dir of pyelftools!')
        return 1

    success = True
    for example_path in discover_examples():
        if success:
            success = success and run_example_and_compare(example_path)

    if success:
        testlog.info('\nConclusion: SUCCESS')
        return 0
    else:
        testlog.info('\nConclusion: FAIL')
        return 1


if __name__ == '__main__':
    sys.exit(main())


########NEW FILE########
__FILENAME__ = run_readelf_tests
#!/usr/bin/env python
#-------------------------------------------------------------------------------
# test/run_readelf_tests.py
#
# Automatic test runner for elftools & readelf
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
import os, sys
import re
from difflib import SequenceMatcher
from optparse import OptionParser
import logging
import platform
from utils import setup_syspath; setup_syspath()
from utils import run_exe, is_in_rootdir, dump_output_to_temp_files


# Create a global logger object
#
testlog = logging.getLogger('run_tests')
testlog.setLevel(logging.DEBUG)
testlog.addHandler(logging.StreamHandler(sys.stdout))

# Set the path for calling readelf. We carry our own version of readelf around,
# because binutils tend to change its output even between daily builds of the
# same minor release and keeping track is a headache.
READELF_PATH = 'test/external_tools/readelf'
if not os.path.exists(READELF_PATH):
    READELF_PATH = 'readelf'

def discover_testfiles(rootdir):
    """ Discover test files in the given directory. Yield them one by one.
    """
    for filename in os.listdir(rootdir):
        _, ext = os.path.splitext(filename)
        if ext == '.elf':
            yield os.path.join(rootdir, filename)


def run_test_on_file(filename, verbose=False):
    """ Runs a test on the given input filename. Return True if all test
        runs succeeded.
    """
    success = True
    testlog.info("Test file '%s'" % filename)
    for option in [
            '-e', '-d', '-s', '-r', '-x.text', '-p.shstrtab', '-V',
            '--debug-dump=info', '--debug-dump=decodedline',
            '--debug-dump=frames', '--debug-dump=frames-interp']:
        if verbose: testlog.info("..option='%s'" % option)
        # stdouts will be a 2-element list: output of readelf and output
        # of scripts/readelf.py
        stdouts = []
        for exe_path in [READELF_PATH, 'scripts/readelf.py']:
            args = [option, filename]
            if verbose: testlog.info("....executing: '%s %s'" % (
                exe_path, ' '.join(args)))
            rc, stdout = run_exe(exe_path, args)
            if rc != 0:
                testlog.error("@@ aborting - '%s' returned '%s'" % (exe_path, rc))
                return False
            stdouts.append(stdout)
        if verbose: testlog.info('....comparing output...')
        rc, errmsg = compare_output(*stdouts)
        if rc:
            if verbose: testlog.info('.......................SUCCESS')
        else:
            success = False
            testlog.info('.......................FAIL')
            testlog.info('....for option "%s"' % option)
            testlog.info('....Output #1 is readelf, Output #2 is pyelftools')
            testlog.info('@@ ' + errmsg)
            dump_output_to_temp_files(testlog, *stdouts)
    return success


def compare_output(s1, s2):
    """ Compare stdout strings s1 and s2.
        s1 is from readelf, s2 from elftools readelf.py
        Return pair success, errmsg. If comparison succeeds, success is True
        and errmsg is empty. Otherwise success is False and errmsg holds a
        description of the mismatch.

        Note: this function contains some rather horrible hacks to ignore
        differences which are not important for the verification of pyelftools.
        This is due to some intricacies of binutils's readelf which pyelftools
        doesn't currently implement, features that binutils doesn't support,
        or silly inconsistencies in the output of readelf, which I was reluctant
        to replicate. Read the documentation for more details.
    """
    def prepare_lines(s):
        return [line for line in s.lower().splitlines() if line.strip() != '']
    def filter_readelf_lines(lines):
        filter_out = False
        for line in lines:
            if 'of the .eh_frame section' in line:
                filter_out = True
            elif 'of the .debug_frame section' in line:
                filter_out = False
            if not filter_out:
                if not line.startswith('unknown: length'):
                    yield line

    lines1 = prepare_lines(s1)
    lines2 = prepare_lines(s2)

    lines1 = list(filter_readelf_lines(lines1))

    flag_after_symtable = False

    if len(lines1) != len(lines2):
        return False, 'Number of lines different: %s vs %s' % (
                len(lines1), len(lines2))

    for i in range(len(lines1)):
        if 'symbol table' in lines1[i]:
            flag_after_symtable = True

        # Compare ignoring whitespace
        lines1_parts = lines1[i].split()
        lines2_parts = lines2[i].split()

        if ''.join(lines1_parts) != ''.join(lines2_parts):
            ok = False

            try:
                # Ignore difference in precision of hex representation in the
                # last part (i.e. 008f3b vs 8f3b)
                if (''.join(lines1_parts[:-1]) == ''.join(lines2_parts[:-1]) and
                    int(lines1_parts[-1], 16) == int(lines2_parts[-1], 16)):
                    ok = True
            except ValueError:
                pass

            sm = SequenceMatcher()
            sm.set_seqs(lines1[i], lines2[i])
            changes = sm.get_opcodes()
            if flag_after_symtable:
                # Detect readelf's adding @ with lib and version after
                # symbol name.
                if (    len(changes) == 2 and changes[1][0] == 'delete' and
                        lines1[i][changes[1][1]] == '@'):
                    ok = True
            elif 'at_const_value' in lines1[i]:
                # On 32-bit machines, readelf doesn't correctly represent
                # some boundary LEB128 numbers
                val = lines2_parts[-1]
                num2 = int(val, 16 if val.startswith('0x') else 10)
                if num2 <= -2**31 and '32' in platform.architecture()[0]:
                    ok = True
            elif 'os/abi' in lines1[i]:
                if 'unix - gnu' in lines1[i] and 'unix - linux' in lines2[i]:
                    ok = True
            elif (  'unknown at value' in lines1[i] and
                    'dw_at_apple' in lines2[i]):
                ok = True
            else:
                for s in ('t (tls)', 'l (large)'):
                    if s in lines1[i] or s in lines2[i]:
                        ok = True
                        break
            if not ok:
                errmsg = 'Mismatch on line #%s:\n>>%s<<\n>>%s<<\n (%r)' % (
                    i, lines1[i], lines2[i], changes)
                return False, errmsg
    return True, ''


def main():
    if not is_in_rootdir():
        testlog.error('Error: Please run me from the root dir of pyelftools!')
        return 1

    optparser = OptionParser(
        usage='usage: %prog [options] [file] [file] ...',
        prog='run_readelf_tests.py')
    optparser.add_option('-V', '--verbose',
        action='store_true', dest='verbose',
        help='Verbose output')
    options, args = optparser.parse_args()

    if options.verbose:
        testlog.info('Running in verbose mode')
        testlog.info('Python executable = %s' % sys.executable)
        testlog.info('readelf path = %s' % READELF_PATH)
        testlog.info('Given list of files: %s' % args)

    # If file names are given as command-line arguments, only these files
    # are taken as inputs. Otherwise, autodiscovery is performed.
    #
    if len(args) > 0:
        filenames = args
    else:
        filenames = list(discover_testfiles('test/testfiles_for_readelf'))

    success = True
    for filename in filenames:
        if success:
            success = success and run_test_on_file(
                                    filename,
                                    verbose=options.verbose)

    if success:
        testlog.info('\nConclusion: SUCCESS')
        return 0
    else:
        testlog.info('\nConclusion: FAIL')
        return 1


if __name__ == '__main__':
    sys.exit(main())


########NEW FILE########
__FILENAME__ = test_arm_support
#-------------------------------------------------------------------------------
# elftools tests
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
try:
    import unittest2 as unittest
except ImportError:
    import unittest
import os

from utils import setup_syspath; setup_syspath()
from elftools.elf.elffile import ELFFile

class TestARMSupport(unittest.TestCase):
    def test_hello(self):
        with open(os.path.join('test', 'testfiles_for_unittests',
                               'simple_gcc.elf.arm'), 'rb') as f:
            elf = ELFFile(f)
            self.assertEqual(elf.get_machine_arch(), 'ARM')

            # Check some other properties of this ELF file derived from readelf
            self.assertEqual(elf['e_entry'], 0x8018)
            self.assertEqual(elf.num_sections(), 14)
            self.assertEqual(elf.num_segments(), 2)

    def test_DWARF_indirect_forms(self):
        # This file uses a lot of DW_FORM_indirect, and is also an ARM ELF
        # with non-trivial DWARF info.
        # So this is a simple sanity check that we can successfully parse it
        # and extract the expected amount of CUs.
        with open(os.path.join('test', 'testfiles_for_unittests',
                               'arm_with_form_indirect.elf'), 'rb') as f:
            elffile = ELFFile(f)
            self.assertTrue(elffile.has_dwarf_info())

            dwarfinfo = elffile.get_dwarf_info()
            all_CUs = list(dwarfinfo.iter_CUs())
            self.assertEqual(len(all_CUs), 9)

if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = test_callframe
#-------------------------------------------------------------------------------
# elftools tests
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
try:
    import unittest2 as unittest
except ImportError:
    import unittest

from utils import setup_syspath; setup_syspath()
from elftools.common.py3compat import BytesIO
from elftools.dwarf.callframe import (
    CallFrameInfo, CIE, FDE, instruction_name, CallFrameInstruction,
    RegisterRule)
from elftools.dwarf.structs import DWARFStructs
from elftools.dwarf.descriptions import (describe_CFI_instructions,
    set_global_machine_arch)


class TestCallFrame(unittest.TestCase):
    def assertInstruction(self, instr, name, args):
        self.assertIsInstance(instr, CallFrameInstruction)
        self.assertEqual(instruction_name(instr.opcode), name)
        self.assertEqual(instr.args, args)

    def test_spec_sample_d6(self):
        # D.6 sample in DWARFv3
        s = BytesIO()
        data = (b'' +
            # first comes the CIE
            b'\x20\x00\x00\x00' +        # length
            b'\xff\xff\xff\xff' +        # CIE_id
            b'\x03\x00\x04\x7c' +        # version, augmentation, caf, daf
            b'\x08' +                    # return address
            b'\x0c\x07\x00' +
            b'\x08\x00' +
            b'\x07\x01' +
            b'\x07\x02' +
            b'\x07\x03' +
            b'\x08\x04' +
            b'\x08\x05' +
            b'\x08\x06' +
            b'\x08\x07' +
            b'\x09\x08\x01' +
            b'\x00' +

            # then comes the FDE
            b'\x28\x00\x00\x00' +        # length
            b'\x00\x00\x00\x00' +        # CIE_pointer (to CIE at 0)
            b'\x44\x33\x22\x11' +        # initial_location
            b'\x54\x00\x00\x00' +        # address range
            b'\x41' +
            b'\x0e\x0c' + b'\x41' +
            b'\x88\x01' + b'\x41' +
            b'\x86\x02' + b'\x41' +
            b'\x0d\x06' + b'\x41' +
            b'\x84\x03' + b'\x4b' +
            b'\xc4' + b'\x41' +
            b'\xc6' +
            b'\x0d\x07' + b'\x41' +
            b'\xc8' + b'\x41' +
            b'\x0e\x00' +
            b'\x00\x00'
            )
        s.write(data)

        structs = DWARFStructs(little_endian=True, dwarf_format=32, address_size=4)
        cfi = CallFrameInfo(s, len(data), structs)
        entries = cfi.get_entries()

        self.assertEqual(len(entries), 2)
        self.assertIsInstance(entries[0], CIE)
        self.assertEqual(entries[0]['length'], 32)
        self.assertEqual(entries[0]['data_alignment_factor'], -4)
        self.assertEqual(entries[0]['return_address_register'], 8)
        self.assertEqual(len(entries[0].instructions), 11)
        self.assertInstruction(entries[0].instructions[0],
            'DW_CFA_def_cfa', [7, 0])
        self.assertInstruction(entries[0].instructions[8],
            'DW_CFA_same_value', [7])
        self.assertInstruction(entries[0].instructions[9],
            'DW_CFA_register', [8, 1])

        self.assertTrue(isinstance(entries[1], FDE))
        self.assertEqual(entries[1]['length'], 40)
        self.assertEqual(entries[1]['CIE_pointer'], 0)
        self.assertEqual(entries[1]['address_range'], 84)
        self.assertIs(entries[1].cie, entries[0])
        self.assertEqual(len(entries[1].instructions), 21)
        self.assertInstruction(entries[1].instructions[0],
            'DW_CFA_advance_loc', [1])
        self.assertInstruction(entries[1].instructions[1],
            'DW_CFA_def_cfa_offset', [12])
        self.assertInstruction(entries[1].instructions[9],
            'DW_CFA_offset', [4, 3])
        self.assertInstruction(entries[1].instructions[18],
            'DW_CFA_def_cfa_offset', [0])
        self.assertInstruction(entries[1].instructions[20],
            'DW_CFA_nop', [])

        # Now let's decode it...
        decoded_CIE = entries[0].get_decoded()
        self.assertEqual(decoded_CIE.reg_order, list(range(9)))
        self.assertEqual(len(decoded_CIE.table), 1)
        self.assertEqual(decoded_CIE.table[0]['cfa'].reg, 7)
        self.assertEqual(decoded_CIE.table[0]['pc'], 0)
        self.assertEqual(decoded_CIE.table[0]['cfa'].offset, 0)
        self.assertEqual(decoded_CIE.table[0][4].type, RegisterRule.SAME_VALUE)
        self.assertEqual(decoded_CIE.table[0][8].type, RegisterRule.REGISTER)
        self.assertEqual(decoded_CIE.table[0][8].arg, 1)

        decoded_FDE = entries[1].get_decoded()
        self.assertEqual(decoded_FDE.reg_order, list(range(9)))
        self.assertEqual(decoded_FDE.table[0]['cfa'].reg, 7)
        self.assertEqual(decoded_FDE.table[0]['cfa'].offset, 0)
        self.assertEqual(decoded_FDE.table[0]['pc'], 0x11223344)
        self.assertEqual(decoded_FDE.table[0][8].type, RegisterRule.REGISTER)
        self.assertEqual(decoded_FDE.table[0][8].arg, 1)
        self.assertEqual(decoded_FDE.table[1]['cfa'].reg, 7)
        self.assertEqual(decoded_FDE.table[1]['cfa'].offset, 12)
        self.assertEqual(decoded_FDE.table[2][8].type, RegisterRule.OFFSET)
        self.assertEqual(decoded_FDE.table[2][8].arg, -4)
        self.assertEqual(decoded_FDE.table[2][4].type, RegisterRule.SAME_VALUE)
        self.assertEqual(decoded_FDE.table[5]['pc'], 0x11223344 + 20)
        self.assertEqual(decoded_FDE.table[5][4].type, RegisterRule.OFFSET)
        self.assertEqual(decoded_FDE.table[5][4].arg, -12)
        self.assertEqual(decoded_FDE.table[6]['pc'], 0x11223344 + 64)
        self.assertEqual(decoded_FDE.table[9]['pc'], 0x11223344 + 76)

    def test_describe_CFI_instructions(self):
        # The data here represents a single CIE
        data = (b'' +
            b'\x16\x00\x00\x00' +        # length
            b'\xff\xff\xff\xff' +        # CIE_id
            b'\x03\x00\x04\x7c' +        # version, augmentation, caf, daf
            b'\x08' +                    # return address
            b'\x0c\x07\x02' +
            b'\x10\x02\x07\x03\x01\x02\x00\x00\x06\x06')
        s = BytesIO(data)

        structs = DWARFStructs(little_endian=True, dwarf_format=32, address_size=4)
        cfi = CallFrameInfo(s, len(data), structs)
        entries = cfi.get_entries()

        set_global_machine_arch('x86')
        self.assertEqual(describe_CFI_instructions(entries[0]),
            (   '  DW_CFA_def_cfa: r7 (edi) ofs 2\n' +
                '  DW_CFA_expression: r2 (edx) (DW_OP_addr: 201; DW_OP_deref; DW_OP_deref)\n'))


if __name__ == '__main__':
    unittest.main()



########NEW FILE########
__FILENAME__ = test_double_dynstr_section
#------------------------------------------------------------------------------
# elftools tests
#
# Yann Rouillard (yann@pleiades.fr.eu.org)
# This code is in the public domain
#------------------------------------------------------------------------------
try:
    import unittest2 as unittest
except ImportError:
    import unittest
import os

from utils import setup_syspath; setup_syspath()
from elftools.elf.elffile import ELFFile
from elftools.elf.dynamic import DynamicSection, DynamicTag


class TestDoubleDynstrSections(unittest.TestCase):
    """ This test make sure than dynamic tags
        are properly analyzed when two .dynstr
        sections are present in an elf file
    """

    reference_data = [
        b'libz.so.1',
        b'libc.so.6',
        b'lib_versioned.so.1',
    ]

    def _test_double_dynstr_section_generic(self, testfile):

        with open(os.path.join('test', 'testfiles_for_unittests', testfile),
                  'rb') as f:
            elf = ELFFile(f)
            for section in elf.iter_sections():
                if isinstance(section, DynamicSection):
                    d_tags = [getattr(x, x.entry.d_tag[3:].lower())
                              for x in section.iter_tags()
                              if x.entry.d_tag in DynamicTag._HANDLED_TAGS]
                    self.assertListEqual(
                            TestDoubleDynstrSections.reference_data,
                            d_tags)
                    return
            self.fail('No dynamic section found !!')


    def test_double_dynstr_section(self):
        """ First test with the good dynstr section first
        """
        self._test_double_dynstr_section_generic(
                'lib_with_two_dynstr_sections.so.1.elf')

    def test_double_dynstr_section_reverse(self):
        """ Second test with the good dynstr section last
        """
        self._test_double_dynstr_section_generic(
                'lib_with_two_dynstr_sections_reversed.so.1.elf')


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_dwarf_expr
#-------------------------------------------------------------------------------
# elftools tests
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
try:
    import unittest2 as unittest
except ImportError:
    import unittest

from utils import setup_syspath; setup_syspath()
from elftools.dwarf.descriptions import ExprDumper, set_global_machine_arch
from elftools.dwarf.structs import DWARFStructs


class TestExprDumper(unittest.TestCase):
    structs32 = DWARFStructs(
            little_endian=True,
            dwarf_format=32,
            address_size=4)

    def setUp(self):
        self.visitor = ExprDumper(self.structs32)
        set_global_machine_arch('x64')

    def test_basic_single(self):
        self.visitor.process_expr([0x1b])
        self.assertEqual(self.visitor.get_str(),
            'DW_OP_div')

        self.setUp()
        self.visitor.process_expr([0x74, 0x82, 0x01])
        self.assertEqual(self.visitor.get_str(),
            'DW_OP_breg4 (rsi): 130')

        self.setUp()
        self.visitor.process_expr([0x91, 0x82, 0x01])
        self.assertEqual(self.visitor.get_str(),
            'DW_OP_fbreg: 130')

        self.setUp()
        self.visitor.process_expr([0x51])
        self.assertEqual(self.visitor.get_str(),
            'DW_OP_reg1 (rdx)')

        self.setUp()
        self.visitor.process_expr([0x90, 16])
        self.assertEqual(self.visitor.get_str(),
            'DW_OP_regx: 16 (rip)')

        self.setUp()
        self.visitor.process_expr([0x9d, 0x8f, 0x0A, 0x90, 0x01])
        self.assertEqual(self.visitor.get_str(),
            'DW_OP_bit_piece: 1295 144')

    def test_basic_sequence(self):
        self.visitor.process_expr([0x03, 0x01, 0x02, 0, 0, 0x06, 0x06])
        self.assertEqual(self.visitor.get_str(),
            'DW_OP_addr: 201; DW_OP_deref; DW_OP_deref')

        self.setUp()
        self.visitor.process_expr([0x15, 0xFF, 0x0b, 0xf1, 0xff])
        self.assertEqual(self.visitor.get_str(),
            'DW_OP_pick: 255; DW_OP_const2s: -15')

        self.setUp()
        self.visitor.process_expr([0x1d, 0x1e, 0x1d, 0x1e, 0x1d, 0x1e])
        self.assertEqual(self.visitor.get_str(),
            'DW_OP_mod; DW_OP_mul; DW_OP_mod; DW_OP_mul; DW_OP_mod; DW_OP_mul')


if __name__ == '__main__':
    unittest.main()



########NEW FILE########
__FILENAME__ = test_dwarf_lineprogram
#-------------------------------------------------------------------------------
# elftools tests
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
try:
    import unittest2 as unittest
except ImportError:
    import unittest

from utils import setup_syspath; setup_syspath()
from elftools.common.py3compat import BytesIO, iteritems
from elftools.dwarf.lineprogram import LineProgram, LineState, LineProgramEntry
from elftools.dwarf.structs import DWARFStructs
from elftools.dwarf.constants import *


class TestLineProgram(unittest.TestCase):
    def _make_program_in_stream(self, stream):
        """ Create a LineProgram from the given program encoded in a stream
        """
        ds = DWARFStructs(little_endian=True, dwarf_format=32, address_size=4)
        header = ds.Dwarf_lineprog_header.parse(
            b'\x04\x10\x00\x00' +    # initial lenght
            b'\x03\x00' +            # version
            b'\x20\x00\x00\x00' +    # header length
            b'\x01\x01\x01\x0F' +    # flags
            b'\x0A' +                # opcode_base
            b'\x00\x01\x04\x08\x0C\x01\x01\x01\x00' + # standard_opcode_lengths
            # 2 dir names followed by a NULL
            b'\x61\x62\x00\x70\x00\x00' +
            # a file entry
            b'\x61\x72\x00\x0C\x0D\x0F' +
            # and another entry
            b'\x45\x50\x51\x00\x86\x12\x07\x08' +
            # followed by NULL
            b'\x00')

        lp = LineProgram(header, stream, ds, 0, len(stream.getvalue()))
        return lp

    def assertLineState(self, state, **kwargs):
        """ Assert that the state attributes specified in kwargs have the given
            values (the rest are default).
        """
        for k, v in iteritems(kwargs):
            self.assertEqual(getattr(state, k), v)

    def test_spec_sample_59(self):
        # Sample in figure 59 of DWARFv3
        s = BytesIO()
        s.write(
            b'\x02\xb9\x04' +
            b'\x0b' +
            b'\x38' +
            b'\x82' +
            b'\x73' +
            b'\x02\x02' +
            b'\x00\x01\x01')

        lp = self._make_program_in_stream(s)
        linetable = lp.get_entries()

        self.assertEqual(len(linetable), 7)
        self.assertIs(linetable[0].state, None)  # doesn't modify state
        self.assertEqual(linetable[0].command, DW_LNS_advance_pc)
        self.assertEqual(linetable[0].args, [0x239])
        self.assertLineState(linetable[1].state, address=0x239, line=3)
        self.assertEqual(linetable[1].command, 0xb)
        self.assertEqual(linetable[1].args, [2, 0])
        self.assertLineState(linetable[2].state, address=0x23c, line=5)
        self.assertLineState(linetable[3].state, address=0x244, line=6)
        self.assertLineState(linetable[4].state, address=0x24b, line=7, end_sequence=False)
        self.assertEqual(linetable[5].command, DW_LNS_advance_pc)
        self.assertEqual(linetable[5].args, [2])
        self.assertLineState(linetable[6].state, address=0x24d, line=7, end_sequence=True)

    def test_spec_sample_60(self):
        # Sample in figure 60 of DWARFv3
        s = BytesIO()
        s.write(
            b'\x09\x39\x02' +
            b'\x0b' +
            b'\x09\x03\x00' +
            b'\x0b' +
            b'\x09\x08\x00' +
            b'\x0a' +
            b'\x09\x07\x00' +
            b'\x0a' +
            b'\x09\x02\x00' +
            b'\x00\x01\x01')

        lp = self._make_program_in_stream(s)
        linetable = lp.get_entries()

        self.assertEqual(len(linetable), 10)
        self.assertIs(linetable[0].state, None)  # doesn't modify state
        self.assertEqual(linetable[0].command, DW_LNS_fixed_advance_pc)
        self.assertEqual(linetable[0].args, [0x239])
        self.assertLineState(linetable[1].state, address=0x239, line=3)
        self.assertLineState(linetable[3].state, address=0x23c, line=5)
        self.assertLineState(linetable[5].state, address=0x244, line=6)
        self.assertLineState(linetable[7].state, address=0x24b, line=7, end_sequence=False)
        self.assertLineState(linetable[9].state, address=0x24d, line=7, end_sequence=True)


if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = test_dwarf_range_lists
#-------------------------------------------------------------------------------
# elftools tests
#
# Eli Bendersky (eliben@gmail.com), Santhosh Kumar Mani (santhoshmani@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
try:
    import unittest2 as unittest
except ImportError:
    import unittest
import os

from utils import setup_syspath; setup_syspath()
from elftools.elf.elffile import ELFFile

class TestRangeLists(unittest.TestCase):
    # Test the absence of .debug_ranges section
    def test_range_list_absence(self):
        with open(os.path.join('test', 'testfiles_for_unittests',
                               'arm_with_form_indirect.elf'), 'rb') as f:
            elffile = ELFFile(f)
            self.assertTrue(elffile.has_dwarf_info())
            self.assertIsNone(elffile.get_dwarf_info().range_lists())

    # Test the presence of .debug_ranges section
    def test_range_list_presence(self):
        with open(os.path.join('test', 'testfiles_for_unittests',
                               'sample_exe64.elf'), 'rb') as f:
            elffile = ELFFile(f)
            self.assertTrue(elffile.has_dwarf_info())
            self.assertIsNotNone(elffile.get_dwarf_info().range_lists())

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_dwarf_structs
#-------------------------------------------------------------------------------
# elftools tests
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
try:
    import unittest2 as unittest
except ImportError:
    import unittest

from utils import setup_syspath; setup_syspath()
from elftools.dwarf.structs import DWARFStructs


class TestDWARFStructs(unittest.TestCase):
    def test_lineprog_header(self):
        ds = DWARFStructs(little_endian=True, dwarf_format=32, address_size=4)

        c = ds.Dwarf_lineprog_header.parse(
            b'\x04\x10\x00\x00' +    # initial lenght
            b'\x05\x02' +            # version
            b'\x20\x00\x00\x00' +    # header length
            b'\x05\x10\x40\x50' +    # until and including line_range
            b'\x06' +                # opcode_base
            b'\x00\x01\x04\x08\x0C' + # standard_opcode_lengths
            # 2 dir names followed by a NULL
            b'\x61\x62\x00\x70\x00\x00' +
            # a file entry
            b'\x61\x72\x00\x0C\x0D\x0F' +
            # and another entry
            b'\x45\x50\x51\x00\x86\x12\x07\x08' +
            # followed by NULL
            b'\x00')

        self.assertEqual(c.version, 0x205)
        self.assertEqual(c.opcode_base, 6)
        self.assertEqual(c.standard_opcode_lengths, [0, 1, 4, 8, 12])
        self.assertEqual(c.include_directory, [b'ab', b'p'])
        self.assertEqual(len(c.file_entry), 2)
        self.assertEqual(c.file_entry[0].name, b'ar')
        self.assertEqual(c.file_entry[1].name, b'EPQ')
        self.assertEqual(c.file_entry[1].dir_index, 0x12 * 128 + 6)


if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = test_dynamic
#-------------------------------------------------------------------------------
# elftools tests
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
try:
    import unittest2 as unittest
except ImportError:
    import unittest
import os

from utils import setup_syspath; setup_syspath()
from elftools.common.exceptions import ELFError
from elftools.elf.dynamic import DynamicTag


class TestDynamicTag(unittest.TestCase):
    def test_requires_stringtable(self):
        with self.assertRaises(ELFError):
            dt = DynamicTag('', None)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_gnuversions
#------------------------------------------------------------------------------
# elftools tests
#
# Yann Rouillard (yann@pleiades.fr.eu.org)
# This code is in the public domain
#------------------------------------------------------------------------------
try:
    import unittest2 as unittest
except ImportError:
    import unittest
import os

from utils import setup_syspath
setup_syspath()
from elftools.elf.elffile import ELFFile
from elftools.elf.constants import VER_FLAGS
from elftools.elf.gnuversions import (
        GNUVerNeedSection, GNUVerDefSection,
        GNUVerSymSection)


class TestSymbolVersioning(unittest.TestCase):

    versym_reference_data = [
        {'name': b'', 'ndx': 'VER_NDX_LOCAL'},
        {'name': b'', 'ndx': 'VER_NDX_LOCAL'},
        {'name': b'_ITM_deregisterTMCloneTable', 'ndx': 'VER_NDX_LOCAL'},
        {'name': b'puts', 'ndx': 5},
        {'name': b'strlcat', 'ndx': 'VER_NDX_LOCAL'},
        {'name': b'__stack_chk_fail', 'ndx': 6},
        {'name': b'__gmon_start__', 'ndx': 'VER_NDX_LOCAL'},
        {'name': b'gzoffset', 'ndx': 7},
        {'name': b'_Jv_RegisterClasses', 'ndx': 'VER_NDX_LOCAL'},
        {'name': b'_ITM_registerTMCloneTable', 'ndx': 'VER_NDX_LOCAL'},
        {'name': b'__cxa_finalize', 'ndx': 5},
        {'name': b'_edata', 'ndx': 'VER_NDX_GLOBAL'},
        {'name': b'VER_1.0', 'ndx': 2},
        {'name': b'function1_ver1_1', 'ndx': 'VER_NDX_GLOBAL'},
        {'name': b'_end', 'ndx': 'VER_NDX_GLOBAL'},
        {'name': b'function1', 'ndx': 4 | 0x8000},
        {'name': b'__bss_start', 'ndx': 'VER_NDX_GLOBAL'},
        {'name': b'function1', 'ndx': 2},
        {'name': b'VER_1.1', 'ndx': 3},
        {'name': b'_init', 'ndx': 'VER_NDX_GLOBAL'},
        {'name': b'function1_ver1_0', 'ndx': 'VER_NDX_GLOBAL'},
        {'name': b'_fini', 'ndx': 'VER_NDX_GLOBAL'},
        {'name': b'VER_1.2', 'ndx': 4},
        {'name': b'function2', 'ndx': 3},
    ]

    def test_versym_section(self):

        reference_data = TestSymbolVersioning.versym_reference_data

        with open(os.path.join('test', 'testfiles_for_unittests',
                               'lib_versioned64.so.1.elf'), 'rb') as f:
            elf = ELFFile(f)
            versym_section = None
            for section in elf.iter_sections():
                if isinstance(section, GNUVerSymSection):
                    versym_section = section
                    break

            self.assertIsNotNone(versym_section)

            for versym, ref_versym in zip(section.iter_symbols(),
                                                   reference_data):
                self.assertEqual(versym.name, ref_versym['name'])
                self.assertEqual(versym['ndx'], ref_versym['ndx'])

    verneed_reference_data = [
        {'name': b'libz.so.1', 'vn_version': 1, 'vn_cnt': 1,
         'vernaux': [
            {'name': b'ZLIB_1.2.3.5', 'vna_flags': 0, 'vna_other': 7}]},
        {'name': b'libc.so.6', 'vn_version': 1, 'vn_cnt': 2,
         'vernaux': [
            {'name': b'GLIBC_2.4', 'vna_flags': 0, 'vna_other': 6},
            {'name': b'GLIBC_2.2.5', 'vna_flags': 0, 'vna_other': 5}]},
        ]

    def test_verneed_section(self):

        reference_data = TestSymbolVersioning.verneed_reference_data

        with open(os.path.join('test', 'testfiles_for_unittests',
                               'lib_versioned64.so.1.elf'), 'rb') as f:
            elf = ELFFile(f)
            verneed_section = None
            for section in elf.iter_sections():
                if isinstance(section, GNUVerNeedSection):
                    verneed_section = section
                    break

            self.assertIsNotNone(verneed_section)

            for (verneed, vernaux_iter), ref_verneed in zip(
                    section.iter_versions(), reference_data):

                self.assertEqual(verneed.name, ref_verneed['name'])
                self.assertEqual(verneed['vn_cnt'], ref_verneed['vn_cnt'])
                self.assertEqual(verneed['vn_version'],
                                 ref_verneed['vn_version'])

                for vernaux, ref_vernaux in zip(
                        vernaux_iter, ref_verneed['vernaux']):

                    self.assertEqual(vernaux.name, ref_vernaux['name'])
                    self.assertEqual(vernaux['vna_flags'],
                                     ref_vernaux['vna_flags'])
                    self.assertEqual(vernaux['vna_other'],
                                     ref_vernaux['vna_other'])

    verdef_reference_data = [
        {'vd_ndx': 1, 'vd_version': 1, 'vd_flags': VER_FLAGS.VER_FLG_BASE,
         'vd_cnt': 1,
         'verdaux': [
            {'name': b'lib_versioned.so.1'}]},
        {'vd_ndx': 2, 'vd_version': 1, 'vd_flags': 0, 'vd_cnt': 1,
         'verdaux': [
            {'name': b'VER_1.0'}]},
        {'vd_ndx': 3, 'vd_version': 1, 'vd_flags': 0, 'vd_cnt': 2,
         'verdaux': [
            {'name': b'VER_1.1'},
            {'name': b'VER_1.0'}]},
        {'vd_ndx': 4, 'vd_version': 1, 'vd_flags': 0, 'vd_cnt': 2,
         'verdaux': [
            {'name': b'VER_1.2'},
            {'name': b'VER_1.1'}]},
        ]

    def test_verdef_section(self):

        reference_data = TestSymbolVersioning.verdef_reference_data

        with open(os.path.join('test', 'testfiles_for_unittests',
                               'lib_versioned64.so.1.elf'), 'rb') as f:
            elf = ELFFile(f)
            verneed_section = None
            for section in elf.iter_sections():
                if isinstance(section, GNUVerDefSection):
                    verdef_section = section
                    break

            self.assertIsNotNone(verdef_section)

            for (verdef, verdaux_iter), ref_verdef in zip(
                    section.iter_versions(), reference_data):

                self.assertEqual(verdef['vd_ndx'], ref_verdef['vd_ndx'])
                self.assertEqual(verdef['vd_version'],
                                 ref_verdef['vd_version'])
                self.assertEqual(verdef['vd_flags'], ref_verdef['vd_flags'])
                self.assertEqual(verdef['vd_cnt'], ref_verdef['vd_cnt'])

                for verdaux, ref_verdaux in zip(
                        verdaux_iter, ref_verdef['verdaux']):
                    self.assertEqual(verdaux.name, ref_verdaux['name'])

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_solaris_support
#-------------------------------------------------------------------------------
# elftools tests
#
# Yann Rouillard (yann@pleiades.fr.eu.org)
# This code is in the public domain
#-------------------------------------------------------------------------------
try:
    import unittest2 as unittest
except ImportError:
    import unittest
import os
import copy

from utils import setup_syspath; setup_syspath()
from elftools.elf.elffile import ELFFile
from elftools.elf.constants import SUNW_SYMINFO_FLAGS


class TestSolarisSupport(unittest.TestCase):

    def _test_SUNW_syminfo_section_generic(self, testfile):
        with open(os.path.join('test', 'testfiles_for_unittests',
                               testfile), 'rb') as f:
            elf = ELFFile(f)
            syminfo_section = elf.get_section_by_name(b'.SUNW_syminfo')
            self.assertIsNotNone(syminfo_section)

            # The test files were compiled against libc.so.1 with
            # direct binding, hence the libc symbols used
            # (exit, atexit and _exit) have the direct binding flags
            # in the syminfo table.
            # We check that this is properly detected.
            exit_symbols = [s for s in syminfo_section.iter_symbols()
                            if b'exit' in s.name]
            self.assertNotEqual(len(exit_symbols), 0)

            for symbol in exit_symbols:
                # libc.so.1 has the index 0 in the dynamic table
                self.assertEqual(symbol['si_boundto'], 0)
                self.assertEqual(symbol['si_flags'],
                                 SUNW_SYMINFO_FLAGS.SYMINFO_FLG_DIRECT |
                                 SUNW_SYMINFO_FLAGS.SYMINFO_FLG_DIRECTBIND)

    def test_SUNW_syminfo_section_x86(self):
        self._test_SUNW_syminfo_section_generic('exe_solaris32_cc.elf')

    def test_SUNW_syminfo_section_x64(self):
        self._test_SUNW_syminfo_section_generic('exe_solaris64_cc.elf')

    def test_SUNW_syminfo_section_sparc32(self):
        self._test_SUNW_syminfo_section_generic('exe_solaris32_cc.sparc.elf')

    def test_SUNW_syminfo_section_sparc64(self):
        self._test_SUNW_syminfo_section_generic('exe_solaris64_cc.sparc.elf')

    ldsynsym_reference_data = [b'', b'exe_solaris32.elf', b'crti.s', b'crt1.o',
                               b'crt1.s', b'fsr.s', b'values-Xa.c',
                               b'exe_solaris64.elf.c', b'crtn.s']

    def _test_SUNW_ldynsym_section_generic(self, testfile, reference_data):
        with open(os.path.join('test', 'testfiles_for_unittests',
                               testfile), 'rb') as f:
            elf = ELFFile(f)
            ldynsym_section = elf.get_section_by_name(b'.SUNW_ldynsym')
            self.assertIsNotNone(ldynsym_section)

            for symbol, ref_symbol_name in zip(
                    ldynsym_section.iter_symbols(), reference_data):

                self.assertEqual(symbol.name, ref_symbol_name)

    def test_SUNW_ldynsym_section_x86(self):
        reference_data = TestSolarisSupport.ldsynsym_reference_data
        self._test_SUNW_ldynsym_section_generic('exe_solaris32_cc.elf',
                                                reference_data)

    def test_SUNW_ldynsym_section_x64(self):
        reference_data = copy.deepcopy(
            TestSolarisSupport.ldsynsym_reference_data)
        reference_data[1] = b'exe_solaris64.elf'
        reference_data[3] = b'crt1x.o'
        reference_data[5] = b'fsrx.s'
        self._test_SUNW_ldynsym_section_generic('exe_solaris64_cc.elf',
                                                reference_data)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_utils
#-------------------------------------------------------------------------------
# elftools tests
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
try:
    import unittest2 as unittest
except ImportError:
    import unittest
from random import randint

from utils import setup_syspath; setup_syspath()
from elftools.common.py3compat import int2byte, BytesIO
from elftools.common.utils import (parse_cstring_from_stream,
        preserve_stream_pos)


class Test_parse_cstring_from_stream(unittest.TestCase):
    def _make_random_bytes(self, n):
        return b''.join(int2byte(randint(32, 127)) for i in range(n))

    def test_small1(self):
        sio = BytesIO(b'abcdefgh\x0012345')
        self.assertEqual(parse_cstring_from_stream(sio), b'abcdefgh')
        self.assertEqual(parse_cstring_from_stream(sio, 2), b'cdefgh')
        self.assertEqual(parse_cstring_from_stream(sio, 8), b'')

    def test_small2(self):
        sio = BytesIO(b'12345\x006789\x00abcdefg\x00iii')
        self.assertEqual(parse_cstring_from_stream(sio), b'12345')
        self.assertEqual(parse_cstring_from_stream(sio, 5), b'')
        self.assertEqual(parse_cstring_from_stream(sio, 6), b'6789')

    def test_large1(self):
        text = b'i' * 400 + b'\x00' + b'bb'
        sio = BytesIO(text)
        self.assertEqual(parse_cstring_from_stream(sio), b'i' * 400)
        self.assertEqual(parse_cstring_from_stream(sio, 150), b'i' * 250)

    def test_large2(self):
        text = self._make_random_bytes(5000) + b'\x00' + b'jujajaja'
        sio = BytesIO(text)
        self.assertEqual(parse_cstring_from_stream(sio), text[:5000])
        self.assertEqual(parse_cstring_from_stream(sio, 2348), text[2348:5000])


class Test_preserve_stream_pos(unittest.TestCase):
    def test_basic(self):
        sio = BytesIO(b'abcdef')
        with preserve_stream_pos(sio):
            sio.seek(4)
        self.assertEqual(sio.tell(), 0)

        sio.seek(5)
        with preserve_stream_pos(sio):
            sio.seek(0)
        self.assertEqual(sio.tell(), 5)


if __name__ == '__main__':
    unittest.main()




########NEW FILE########
__FILENAME__ = utils
#-------------------------------------------------------------------------------
# test/utils.py
#
# Some common utils for tests
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
import os, sys, subprocess, tempfile

# This module should not import elftools before setup_syspath() is called!
# See the Hacking Guide in the documentation for more details.

def setup_syspath():
    """ Setup sys.path so that tests pick up local pyelftools before the
        installed one when run from development directory.
    """
    if sys.path[0] != '.':
        sys.path.insert(0, '.')


def run_exe(exe_path, args=[]):
    """ Runs the given executable as a subprocess, given the
        list of arguments. Captures its return code (rc) and stdout and
        returns a pair: rc, stdout_str
    """
    popen_cmd = [exe_path] + args
    if os.path.splitext(exe_path)[1] == '.py':
        popen_cmd.insert(0, sys.executable)
    proc = subprocess.Popen(popen_cmd, stdout=subprocess.PIPE)
    proc_stdout = proc.communicate()[0]
    from elftools.common.py3compat import bytes2str
    return proc.returncode, bytes2str(proc_stdout)


def is_in_rootdir():
    """ Check whether the current dir is the root dir of pyelftools
    """
    return os.path.isdir('test') and os.path.isdir('elftools')


def dump_output_to_temp_files(testlog, *args):
    """ Dumps the output strings given in 'args' to temp files: one for each
        arg.
    """
    for i, s in enumerate(args):
        fd, path = tempfile.mkstemp(
                prefix='out' + str(i + 1) + '_',
                suffix='.stdout')
        file = os.fdopen(fd, 'w')
        file.write(s)
        file.close()
        testlog.info('@@ Output #%s dumped to file: %s' % (i + 1, path))


########NEW FILE########
__FILENAME__ = z
#-------------------------------------------------------------------------------
# elftools
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------

# Just a script for playing around with pyelftools during testing
# please ignore it!
#
from __future__ import print_function

import sys, pprint
from elftools.elf.structs import ELFStructs
from elftools.elf.elffile import ELFFile
from elftools.elf.sections import *

from elftools.elf.relocation import *


stream = open('test/testfiles/exe_simple64.elf', 'rb')

efile = ELFFile(stream)
print('elfclass', efile.elfclass)
print('===> %s sections!' % efile.num_sections())
print(efile.header)

dinfo = efile.get_dwarf_info()
from elftools.dwarf.locationlists import LocationLists
from elftools.dwarf.descriptions import describe_DWARF_expr
llists = LocationLists(dinfo.debug_loc_sec.stream, dinfo.structs)
for loclist in llists.iter_location_lists():
    print('----> loclist!')
    for li in loclist:
        print(li)
        print(describe_DWARF_expr(li.loc_expr, dinfo.structs))



########NEW FILE########
