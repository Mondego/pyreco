__FILENAME__ = adapters
from core import Adapter, AdaptationError, Pass
from lib import int_to_bin, bin_to_int, swap_bytes, StringIO
from lib import FlagsContainer, HexString


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
                raise MappingError("no encoding mapping for %r" % (obj,))
            if self.encdefault is Pass:
                return obj
            return self.encdefault
    def _decode(self, obj, context):
        try:
            return self.decoding[obj]
        except (KeyError, TypeError):
            if self.decdefault is NotImplemented:
                raise MappingError("no decoding mapping for %r"  % (obj,))
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
        for name, value in self.flags.iteritems():
            if getattr(obj, name, False):
                flags |= value
        return flags
    def _decode(self, obj, context):
        obj2 = FlagsContainer()
        for name, value in self.flags.iteritems():
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
        obj = "".join(obj)
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
    def __init__(self, subcon, terminators = "\x00", encoding = None):
        StringAdapter.__init__(self, subcon, encoding = encoding)
        self.terminators = terminators
    def _encode(self, obj, context):
        return StringAdapter._encode(self, obj, context) + self.terminators[0]
    def _decode(self, obj, context):
        return StringAdapter._decode(self, obj[:-1], context)

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
        return self.inner_subcon._parse(StringIO(obj), context)
    def _encode(self, obj, context):
        stream = StringIO()
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

from lib import StringIO
from lib import Container, ListContainer, LazyContainer


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

        for name, value in attrs.iteritems():
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

        return self.parse_stream(StringIO(data))

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

        stream = StringIO()
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
        except Exception, e:
            raise SizeofError(e)

    def _sizeof(self, context):
        """
        Override me in your subclass.
        """

        raise SizeofError("Raw Constructs have no size!")

class Subconstruct(Construct):
    """
    Abstract parent class of all subconstructs.

    Subconstructs wrap an inner Construct, inheriting its name and flags.

    :param ``Construct`` subcon: the construct to wrap
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
    Abstract adapter parent class.

    Adapters should implement ``_decode()`` and ``_encode()``.

    :param ``Construct`` subcon: the construct to wrap
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
        except Exception, ex:
            raise FieldError(ex)
    def _build(self, obj, stream, context):
        try:
            _write_stream(stream, self.length, self.packer.pack(obj))
        except Exception, ex:
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
        except ConstructError, ex:
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
        except ConstructError, ex:
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
                    self.subcon._build(subobj, stream, context.__copy__())
                    cnt += 1
            else:
                for subobj in obj:
                    self.subcon._build(subobj, stream, context)
                    cnt += 1
        except ConstructError, ex:
            if cnt < self.mincount:
                raise RangeError("expected %d to %d, found %d" %
                    (self.mincount, self.maxcout, len(obj)), ex)
    def _sizeof(self, context):
        raise SizeofError("can't calculate size")

class RepeatUntil(Subconstruct):
    """
    An array that repeat until the predicate indicates it to stop. Note that
    the last element (which caused the repeat to exit) is included in the
    return value.

    Parameters:
    * predicate - a predicate function that takes (obj, context) and returns
      True if the stop-condition is met, or False to continue.
    * subcon - the subcon to repeat.

    Example:
    # will read chars until \x00 (inclusive)
    RepeatUntil(lambda obj, ctx: obj == "\x00",
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
        except ConstructError, ex:
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
                subobj = objiter.next()
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
                stream2 = StringIO()
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
        stream2 = StringIO(self.decoder(data))
        return self.subcon._parse(stream2, context)
    def _build(self, obj, stream, context):
        size = self._sizeof(context)
        stream2 = StringIO()
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
    The **anchor**, or stream position at a point in a Construct.

    Anchors are useful for adjusting relative offsets to absolute positions,
    or to measure sizes of Constructs.

    To get an absolute pointer, use an Anchor plus a relative offset. To get a
    size, place two Anchors and measure their difference.

    :param str name: the name of the anchor

    .. note::

       Anchor requires a seekable stream, or at least a tellable stream; it is
       implemented using the ``tell()`` method of file-like objects.

    .. seealso:: Pointer
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
import sys
import traceback
import pdb
import inspect
from core import Construct, Subconstruct
from lib import HexString, Container, ListContainer


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
        
        print "=" * 80
        print "Probe", self.printname
        print obj
        print "=" * 80

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
        print "=" * 80
        print "Debugging exception of %s:" % (self.subcon,)
        print "".join(traceback.format_exception(*sys.exc_info())[1:])
        if msg:
            print msg
        pdb.post_mortem(sys.exc_info()[2])
        print "=" * 80





























########NEW FILE########
__FILENAME__ = cap
"""
tcpdump capture file
"""
from construct import *
import time
from datetime import datetime


class MicrosecAdapter(Adapter):
    def _decode(self, obj, context):
        return datetime.fromtimestamp(obj[0] + (obj[1] / 1000000.0))
    def _encode(self, obj, context):
        offset = time.mktime(*obj.timetuple())
        sec = int(offset)
        usec = (offset - sec) * 1000000
        return (sec, usec)

packet = Struct("packet",
    MicrosecAdapter(
        Sequence("time", 
            ULInt32("time"),
            ULInt32("usec"),
        )
    ),
    ULInt32("length"),
    Padding(4),
    HexDumpAdapter(Field("data", lambda ctx: ctx.length)),
)

cap_file = Struct("cap_file",
    Padding(24),
    Rename("packets", OptionalGreedyRange(packet)),
)


if __name__ == "__main__":
    obj = cap_file.parse_stream(open("../../tests/cap2.cap", "rb"))
    print len(obj.packets)


















########NEW FILE########
__FILENAME__ = snoop
"""
what : snoop v2 capture file.
 how : http://tools.ietf.org/html/rfc1761
 who : jesse @ housejunkie . ca
"""

import time
from construct import (
        Adapter,
        Enum,
        Field,
        GreedyRange,
        HexDumpAdapter,
        Magic,
        OptionalGreedyRange,
        Padding,
        Struct,
        UBInt32,
    )

class EpochTimeStampAdapter(Adapter):
    """ Convert epoch timestamp <-> localtime """

    def _decode(self, obj, context):
        return time.ctime(obj)
    def _encode(self, obj, context):
        return int(time.mktime(time.strptime(obj)))

packet_record = Struct("packet_record",
        UBInt32("original_length"),
        UBInt32("included_length"),
        UBInt32("record_length"),
        UBInt32("cumulative_drops"),
        EpochTimeStampAdapter(UBInt32("timestamp_seconds")),
        UBInt32("timestamp_microseconds"),
        HexDumpAdapter(Field("data", lambda ctx: ctx.included_length)),
        # 24 being the static length of the packet_record header
        Padding(lambda ctx: ctx.record_length - ctx.included_length - 24),
    )

datalink_type = Enum(UBInt32("datalink"),
        IEEE802dot3 = 0,
        IEEE802dot4 = 1,
        IEEE802dot5 = 2,
        IEEE802dot6 = 3,
        ETHERNET = 4,
        HDLC = 5,
        CHARSYNC = 6,
        IBMCHANNEL = 7,
        FDDI = 8,
        OTHER = 9,
        UNASSIGNED = 10,
    )

snoop_file = Struct("snoop",
        Magic("snoop\x00\x00\x00"),
        UBInt32("version"), # snoop v1 is deprecated
        datalink_type,
        OptionalGreedyRange(packet_record),
    )

########NEW FILE########
__FILENAME__ = elf32
"""
Executable and Linkable Format (ELF), 32 bit, big or little endian
Used on *nix systems as a replacement of the older a.out format

Big-endian support kindly submitted by Craig McQueen (mcqueen-c#edsrd1!yzk!co!jp)
"""
from construct import *


def elf32_body(ElfInt16, ElfInt32):
    elf32_program_header = Struct("program_header",
        Enum(ElfInt32("type"),
            NULL = 0,
            LOAD = 1,
            DYNAMIC = 2,
            INTERP = 3,
            NOTE = 4,
            SHLIB = 5,
            PHDR = 6,
            _default_ = Pass,
        ),
        ElfInt32("offset"),
        ElfInt32("vaddr"),
        ElfInt32("paddr"),
        ElfInt32("file_size"),
        ElfInt32("mem_size"),
        ElfInt32("flags"),
        ElfInt32("align"),
    )
    
    elf32_section_header = Struct("section_header",
        ElfInt32("name_offset"),
        Pointer(lambda ctx: ctx._.strtab_data_offset + ctx.name_offset,
            CString("name")
        ),
        Enum(ElfInt32("type"), 
            NULL = 0,
            PROGBITS = 1,
            SYMTAB = 2,
            STRTAB = 3,
            RELA = 4,
            HASH = 5,
            DYNAMIC = 6,
            NOTE = 7,
            NOBITS = 8,
            REL = 9,
            SHLIB = 10,
            DYNSYM = 11,
            _default_ = Pass,
        ),
        ElfInt32("flags"),
        ElfInt32("addr"),
        ElfInt32("offset"),
        ElfInt32("size"),
        ElfInt32("link"),
        ElfInt32("info"),
        ElfInt32("align"),
        ElfInt32("entry_size"),
        OnDemandPointer(lambda ctx: ctx.offset,
            HexDumpAdapter(Field("data", lambda ctx: ctx.size))
        ),
    )
    
    return Struct("body",
        Enum(ElfInt16("type"),
            NONE = 0,
            RELOCATABLE = 1,
            EXECUTABLE = 2,
            SHARED = 3,
            CORE = 4,
        ),
        Enum(ElfInt16("machine"),
            NONE = 0,
            M32 = 1,
            SPARC = 2,
            I386 = 3,
            Motorolla68K = 4,
            Motorolla88K = 5,
            Intel860 = 7,
            MIPS = 8,
            _default_ = Pass
        ),
        ElfInt32("version"),
        ElfInt32("entry"),
        ElfInt32("ph_offset"),
        ElfInt32("sh_offset"),
        ElfInt32("flags"),
        ElfInt16("header_size"),
        ElfInt16("ph_entry_size"),
        ElfInt16("ph_count"),
        ElfInt16("sh_entry_size"),
        ElfInt16("sh_count"),
        ElfInt16("strtab_section_index"),
        
        # calculate the string table data offset (pointer arithmetics)
        # ugh... anyway, we need it in order to read the section names, later on
        Pointer(lambda ctx: 
            ctx.sh_offset + ctx.strtab_section_index * ctx.sh_entry_size + 16,
            ElfInt32("strtab_data_offset"),
        ),
        
        # program header table
        Rename("program_table",
            Pointer(lambda ctx: ctx.ph_offset,
                Array(lambda ctx: ctx.ph_count,
                    elf32_program_header
                )
            )
        ),
        
        # section table
        Rename("sections", 
            Pointer(lambda ctx: ctx.sh_offset,
                Array(lambda ctx: ctx.sh_count,
                    elf32_section_header
                )
            )
        ),    
    )

elf32_body_little_endian = elf32_body(ULInt16, ULInt32)
elf32_body_big_endian = elf32_body(UBInt16, UBInt32)

def Magic(name, value):
    return Const(Bytes(name, len(value)), value)

elf32_file = Struct("elf32_file",
    Struct("identifier",
        Magic("magic", "\x7fELF"),
        Enum(Byte("file_class"),
            NONE = 0,
            CLASS32 = 1,
            CLASS64 = 2,
        ),
        Enum(Byte("encoding"),
            NONE = 0,
            LSB = 1,
            MSB = 2,            
        ),
        Byte("version"),
        Padding(9),
    ),
    Embedded(IfThenElse("body", lambda ctx: ctx.identifier.encoding == "LSB",
        elf32_body_little_endian,
        elf32_body_big_endian,
    )),
)


if __name__ == "__main__":
    obj = elf32_file.parse_stream(open("../../tests/_ctypes_test.so", "rb"))
    #[s.data.value for s in obj.sections]
    print obj




########NEW FILE########
__FILENAME__ = pe32
"""
Portable Executable (PE) 32 bit, little endian
Used on MSWindows systems (including DOS) for EXEs and DLLs

1999 paper:
http://download.microsoft.com/download/1/6/1/161ba512-40e2-4cc9-843a-923143f3456c/pecoff.doc

2006 with updates relevant for .NET:
http://download.microsoft.com/download/9/c/5/9c5b2167-8017-4bae-9fde-d599bac8184a/pecoff_v8.doc
"""
from construct import *
import time


class UTCTimeStampAdapter(Adapter):
    def _decode(self, obj, context):
        return time.ctime(obj)
    def _encode(self, obj, context):
        return int(time.mktime(time.strptime(obj)))

def UTCTimeStamp(name):
    return UTCTimeStampAdapter(ULInt32(name))

class NamedSequence(Adapter):
    """
    creates a mapping between the elements of a sequence and their respective
    names. this is useful for sequences of a variable length, where each
    element in the sequence has a name (as is the case with the data 
    directories of the PE header)
    """
    __slots__ = ["mapping", "rev_mapping"]
    prefix = "unnamed_"
    def __init__(self, subcon, mapping):
        Adapter.__init__(self, subcon)
        self.mapping = mapping
        self.rev_mapping = dict((v, k) for k, v in mapping.iteritems())
    def _encode(self, obj, context):
        d = obj.__dict__
        obj2 = [None] * len(d)
        for name, value in d.iteritems():
            if name in self.rev_mapping:
                index = self.rev_mapping[name]
            elif name.startswith("__"):
                obj2.pop(-1)
                continue
            elif name.startswith(self.prefix):
                index = int(name.split(self.prefix)[1])
            else:
                raise ValueError("no mapping defined for %r" % (name,))
            obj2[index] = value
        return obj2
    def _decode(self, obj, context):
        obj2 = Container()
        for i, item in enumerate(obj):
            if i in self.mapping:
                name = self.mapping[i]
            else:
                name = "%s%d" % (self.prefix, i)
            setattr(obj2, name, item)
        return obj2


msdos_header = Struct("msdos_header",
    Magic("MZ"),
    ULInt16("partPag"),
    ULInt16("page_count"),
    ULInt16("relocation_count"),
    ULInt16("header_size"),
    ULInt16("minmem"),
    ULInt16("maxmem"),
    ULInt16("relocation_stackseg"),
    ULInt16("exe_stackptr"),
    ULInt16("checksum"),
    ULInt16("exe_ip"),
    ULInt16("relocation_codeseg"),
    ULInt16("table_offset"),
    ULInt16("overlay"),
    Padding(8),
    ULInt16("oem_id"),
    ULInt16("oem_info"),
    Padding(20),
    ULInt32("coff_header_pointer"),
    Anchor("_assembly_start"),
    OnDemand(
        HexDumpAdapter(
            Field("code", 
                lambda ctx: ctx.coff_header_pointer - ctx._assembly_start
            )
        )
    ),
)

symbol_table = Struct("symbol_table",
    String("name", 8, padchar = "\x00"),
    ULInt32("value"),
    Enum(ExprAdapter(SLInt16("section_number"),
            encoder = lambda obj, ctx: obj + 1,
            decoder = lambda obj, ctx: obj - 1,
        ),
        UNDEFINED = -1,
        ABSOLUTE = -2,
        DEBUG = -3,
        _default_ = Pass,
    ),
    Enum(ULInt8("complex_type"),
        NULL = 0,
        POINTER = 1,
        FUNCTION = 2,
        ARRAY = 3,
    ),
    Enum(ULInt8("base_type"),
        NULL = 0,
        VOID = 1,
        CHAR = 2,
        SHORT = 3,
        INT = 4,
        LONG = 5,
        FLOAT = 6,
        DOUBLE = 7,
        STRUCT = 8,
        UNION = 9,
        ENUM = 10,
        MOE = 11,
        BYTE = 12,
        WORD = 13,
        UINT = 14,
        DWORD = 15,
    ),
    Enum(ULInt8("storage_class"),
        END_OF_FUNCTION = 255,
        NULL = 0,
        AUTOMATIC = 1,
        EXTERNAL = 2,
        STATIC = 3,
        REGISTER = 4,
        EXTERNAL_DEF = 5,
        LABEL = 6,
        UNDEFINED_LABEL = 7,
        MEMBER_OF_STRUCT = 8,
        ARGUMENT = 9,
        STRUCT_TAG = 10,
        MEMBER_OF_UNION = 11,
        UNION_TAG = 12,
        TYPE_DEFINITION = 13,
        UNDEFINED_STATIC = 14,
        ENUM_TAG = 15,
        MEMBER_OF_ENUM = 16,
        REGISTER_PARAM = 17,
        BIT_FIELD = 18,
        BLOCK = 100,
        FUNCTION = 101,
        END_OF_STRUCT = 102,
        FILE = 103,
        SECTION = 104,
        WEAK_EXTERNAL = 105,
    ),
    ULInt8("number_of_aux_symbols"),
    Array(lambda ctx: ctx.number_of_aux_symbols,
        Bytes("aux_symbols", 18)
    )
)

coff_header = Struct("coff_header",
    Magic("PE\x00\x00"),
    Enum(ULInt16("machine_type"),
        UNKNOWN = 0x0,
        AM33 = 0x1d3,
        AMD64 = 0x8664,
        ARM = 0x1c0,
        EBC = 0xebc,
        I386 = 0x14c,
        IA64 = 0x200,
        M32R = 0x9041,
        MIPS16 = 0x266,
        MIPSFPU = 0x366,
        MIPSFPU16 = 0x466,
        POWERPC = 0x1f0,
        POWERPCFP = 0x1f1,
        R4000 = 0x166,
        SH3 = 0x1a2,
        SH3DSP = 0x1a3,
        SH4 = 0x1a6,
        SH5= 0x1a8,
        THUMB = 0x1c2,
        WCEMIPSV2 = 0x169,
        _default_ = Pass
    ),
    ULInt16("number_of_sections"),
    UTCTimeStamp("time_stamp"),
    ULInt32("symbol_table_pointer"),
    ULInt32("number_of_symbols"),
    ULInt16("optional_header_size"),
    FlagsEnum(ULInt16("characteristics"),
        RELOCS_STRIPPED = 0x0001,
        EXECUTABLE_IMAGE = 0x0002,
        LINE_NUMS_STRIPPED = 0x0004,
        LOCAL_SYMS_STRIPPED = 0x0008,
        AGGRESSIVE_WS_TRIM = 0x0010,
        LARGE_ADDRESS_AWARE = 0x0020,
        MACHINE_16BIT = 0x0040,
        BYTES_REVERSED_LO = 0x0080,
        MACHINE_32BIT = 0x0100,
        DEBUG_STRIPPED = 0x0200,
        REMOVABLE_RUN_FROM_SWAP = 0x0400,
        SYSTEM = 0x1000,
        DLL = 0x2000,
        UNIPROCESSOR_ONLY = 0x4000,
        BIG_ENDIAN_MACHINE = 0x8000,
    ),
    
    # symbol table
    Pointer(lambda ctx: ctx.symbol_table_pointer,
        Array(lambda ctx: ctx.number_of_symbols, symbol_table)
    )
)

def PEPlusField(name):
    return IfThenElse(name, lambda ctx: ctx.pe_type == "PE32_plus",
        ULInt64(None),
        ULInt32(None),
    )

optional_header = Struct("optional_header",
    # standard fields
    Enum(ULInt16("pe_type"),
        PE32 = 0x10b,
        PE32_plus = 0x20b,
    ),
    ULInt8("major_linker_version"),
    ULInt8("minor_linker_version"),
    ULInt32("code_size"),
    ULInt32("initialized_data_size"),
    ULInt32("uninitialized_data_size"),
    ULInt32("entry_point_pointer"),
    ULInt32("base_of_code"),
    
    # only in PE32 files
    If(lambda ctx: ctx.pe_type == "PE32",
        ULInt32("base_of_data")
    ),
    
    # WinNT-specific fields
    PEPlusField("image_base"),
    ULInt32("section_aligment"),
    ULInt32("file_alignment"),
    ULInt16("major_os_version"),
    ULInt16("minor_os_version"),
    ULInt16("major_image_version"),
    ULInt16("minor_image_version"),
    ULInt16("major_subsystem_version"),
    ULInt16("minor_subsystem_version"),
    Padding(4),
    ULInt32("image_size"),
    ULInt32("headers_size"),
    ULInt32("checksum"),
    Enum(ULInt16("subsystem"),
        UNKNOWN = 0,
        NATIVE = 1,
        WINDOWS_GUI = 2,
        WINDOWS_CUI = 3,
        POSIX_CIU = 7,
        WINDOWS_CE_GUI = 9,
        EFI_APPLICATION = 10,
        EFI_BOOT_SERVICE_DRIVER = 11,
        EFI_RUNTIME_DRIVER = 12,
        EFI_ROM = 13,
        XBOX = 14,
        _defualt_ = Pass
    ),
    FlagsEnum(ULInt16("dll_characteristics"),
        NO_BIND = 0x0800,
        WDM_DRIVER = 0x2000,
        TERMINAL_SERVER_AWARE = 0x8000,
    ),
    PEPlusField("reserved_stack_size"),
    PEPlusField("stack_commit_size"),
    PEPlusField("reserved_heap_size"),
    PEPlusField("heap_commit_size"),
    ULInt32("loader_flags"),
    ULInt32("number_of_data_directories"),
    
    NamedSequence(
        Array(lambda ctx: ctx.number_of_data_directories,
            Struct("data_directories",
                ULInt32("address"),
                ULInt32("size"),
            )
        ),
        mapping = {
            0 : 'export_table',
            1 : 'import_table',
            2 : 'resource_table',
            3 : 'exception_table',
            4 : 'certificate_table',
            5 : 'base_relocation_table',
            6 : 'debug',
            7 : 'architecture',
            8 : 'global_ptr',
            9 : 'tls_table',
            10 : 'load_config_table',
            11 : 'bound_import',
            12 : 'import_address_table',
            13 : 'delay_import_descriptor',
            14 : 'complus_runtime_header',
        }
    ),
)

section = Struct("section",
    String("name", 8, padchar = "\x00"),
    ULInt32("virtual_size"),
    ULInt32("virtual_address"),
    ULInt32("raw_data_size"),
    ULInt32("raw_data_pointer"),
    ULInt32("relocations_pointer"),
    ULInt32("line_numbers_pointer"),
    ULInt16("number_of_relocations"),
    ULInt16("number_of_line_numbers"),
    FlagsEnum(ULInt32("characteristics"),
        TYPE_REG = 0x00000000,
        TYPE_DSECT = 0x00000001,
        TYPE_NOLOAD = 0x00000002,
        TYPE_GROUP = 0x00000004,
        TYPE_NO_PAD = 0x00000008,
        TYPE_COPY = 0x00000010,
        CNT_CODE = 0x00000020,
        CNT_INITIALIZED_DATA = 0x00000040,
        CNT_UNINITIALIZED_DATA = 0x00000080,
        LNK_OTHER = 0x00000100,
        LNK_INFO = 0x00000200,
        TYPE_OVER = 0x00000400,
        LNK_REMOVE = 0x00000800,
        LNK_COMDAT = 0x00001000,
        MEM_FARDATA = 0x00008000,
        MEM_PURGEABLE = 0x00020000,
        MEM_16BIT = 0x00020000,
        MEM_LOCKED = 0x00040000,
        MEM_PRELOAD = 0x00080000,
        ALIGN_1BYTES = 0x00100000,
        ALIGN_2BYTES = 0x00200000,
        ALIGN_4BYTES = 0x00300000,
        ALIGN_8BYTES = 0x00400000,
        ALIGN_16BYTES = 0x00500000,
        ALIGN_32BYTES = 0x00600000,
        ALIGN_64BYTES = 0x00700000,
        ALIGN_128BYTES = 0x00800000,
        ALIGN_256BYTES = 0x00900000,
        ALIGN_512BYTES = 0x00A00000,
        ALIGN_1024BYTES = 0x00B00000,
        ALIGN_2048BYTES = 0x00C00000,
        ALIGN_4096BYTES = 0x00D00000,
        ALIGN_8192BYTES = 0x00E00000,
        LNK_NRELOC_OVFL = 0x01000000,
        MEM_DISCARDABLE = 0x02000000,
        MEM_NOT_CACHED = 0x04000000,
        MEM_NOT_PAGED = 0x08000000,
        MEM_SHARED = 0x10000000,
        MEM_EXECUTE = 0x20000000,
        MEM_READ = 0x40000000,
        MEM_WRITE = 0x80000000,        
    ),
    
    OnDemandPointer(lambda ctx: ctx.raw_data_pointer,
        HexDumpAdapter(Field("raw_data", lambda ctx: ctx.raw_data_size))
    ),
    
    OnDemandPointer(lambda ctx: ctx.line_numbers_pointer,
        Array(lambda ctx: ctx.number_of_line_numbers,
            Struct("line_numbers",
                ULInt32("type"),
                ULInt16("line_number"),
            )
        )
    ),
    
    OnDemandPointer(lambda ctx: ctx.relocations_pointer,
        Array(lambda ctx: ctx.number_of_relocations,
            Struct("relocations",
                ULInt32("virtual_address"),
                ULInt32("symbol_table_index"),
                ULInt16("type"),
            )
        )
    ),
)

pe32_file = Struct("pe32_file",
    # headers
    msdos_header,
    coff_header,
    Anchor("_start_of_optional_header"),
    optional_header,
    Anchor("_end_of_optional_header"),
    Padding(lambda ctx: min(0, 
            ctx.coff_header.optional_header_size - 
            ctx._end_of_optional_header +
            ctx._start_of_optional_header
        )
    ),
    
    # sections
    Array(lambda ctx: ctx.coff_header.number_of_sections, section)   
)


if __name__ == "__main__":
    print pe32_file.parse_stream(open("../../tests/NOTEPAD.EXE", "rb"))
    print pe32_file.parse_stream(open("../../tests/sqlite3.dll", "rb"))












########NEW FILE########
__FILENAME__ = ext2
"""
Extension 2 (ext2)
Used in Linux systems
"""
from construct import *


Char = SLInt8
UChar = ULInt8
Short = SLInt16
UShort = ULInt16
Long = SLInt32
ULong = ULInt32

def BlockPointer(name):
    return Struct(name,
        ULong("block_number"),
        OnDemandPointer(lambda ctx: ctx["block_number"]),
    )

superblock = Struct("superblock",
    ULong('inodes_count'),
    ULong('blocks_count'),
    ULong('reserved_blocks_count'),
    ULong('free_blocks_count'),
    ULong('free_inodes_count'),
    ULong('first_data_block'),
    Enum(ULong('log_block_size'), 
        OneKB = 0,
        TwoKB = 1,
        FourKB = 2,
    ),
    Long('log_frag_size'),
    ULong('blocks_per_group'),
    ULong('frags_per_group'),
    ULong('inodes_per_group'),
    ULong('mtime'),
    ULong('wtime'),
    UShort('mnt_count'),
    Short('max_mnt_count'),
    Const(UShort('magic'), 0xEF53),
    UShort('state'),
    UShort('errors'),
    Padding(2),
    ULong('lastcheck'),
    ULong('checkinterval'),
    ULong('creator_os'),
    ULong('rev_level'),
    Padding(235 * 4),
)

group_descriptor = Struct("group_descriptor",
    ULong('block_bitmap'),
    ULong('inode_bitmap'),
    ULong('inode_table'),
    UShort('free_blocks_count'),
    UShort('free_inodes_count'),
    UShort('used_dirs_count'),
    Padding(14),
)

inode = Struct("inode",
    FlagsEnum(UShort('mode'),
        IXOTH = 0x0001,
        IWOTH = 0x0002,
        IROTH = 0x0004,
        IRWXO = 0x0007,
        IXGRP = 0x0008,
        IWGRP = 0x0010,
        IRGRP = 0x0020,
        IRWXG = 0x0038,
        IXUSR = 0x0040,
        IWUSR = 0x0080,
        IRUSR = 0x0100,
        IRWXU = 0x01C0,
        ISVTX = 0x0200,
        ISGID = 0x0400,
        ISUID = 0x0800,
        IFIFO = 0x1000,
        IFCHR = 0x2000,
        IFDIR = 0x4000,
        IFBLK = 0x6000,
        IFREG = 0x8000,
        IFLNK = 0xC000,
        IFSOCK = 0xA000,
        IFMT = 0xF000,
    ),
    UShort('uid'),
    ULong('size'),
    ULong('atime'),
    ULong('ctime'),
    ULong('mtime'),
    ULong('dtime'),
    UShort('gid'),
    UShort('links_count'),
    ULong('blocks'),
    FlagsEnum(ULong('flags'),
        SecureDelete = 0x0001,
        AllowUndelete = 0x0002,
        Compressed = 0x0004,
        Synchronous = 0x0008,
    ),
    Padding(4),
    StrictRepeater(12, ULong('blocks')),
    ULong("indirect1_block"),
    ULong("indirect2_block"),
    ULong("indirect3_block"),
    ULong('version'),
    ULong('file_acl'),
    ULong('dir_acl'),
    ULong('faddr'),
    UChar('frag'),
    Byte('fsize'),
    Padding(10)   ,
)

# special inodes
EXT2_BAD_INO = 1
EXT2_ROOT_INO = 2
EXT2_ACL_IDX_INO = 3
EXT2_ACL_DATA_INO = 4
EXT2_BOOT_LOADER_INO = 5
EXT2_UNDEL_DIR_INO = 6
EXT2_FIRST_INO = 11 

directory_record = Struct("directory_entry",
    ULong("inode"),
    UShort("rec_length"),
    UShort("name_length"),
    Field("name", lambda ctx: ctx["name_length"]),
    Padding(lambda ctx: ctx["rec_length"] - ctx["name_length"])
)


print superblock.sizeof()























########NEW FILE########
__FILENAME__ = mbr
"""
Master Boot Record
The first sector on disk, contains the partition table, bootloader, et al.

http://www.win.tue.nl/~aeb/partitions/partition_types-1.html
"""
from construct import *


mbr = Struct("mbr",
    HexDumpAdapter(Bytes("bootloader_code", 446)),
    Array(4,
        Struct("partitions",
            Enum(Byte("state"),
                INACTIVE = 0x00,
                ACTIVE = 0x80,
            ),
            BitStruct("beginning",
                Octet("head"),
                Bits("sect", 6),
                Bits("cyl", 10),
            ),
            Enum(UBInt8("type"),
                Nothing = 0x00,
                FAT12 = 0x01,
                XENIX_ROOT = 0x02,
                XENIX_USR = 0x03,
                FAT16_old = 0x04,
                Extended_DOS = 0x05,
                FAT16 = 0x06,
                FAT32 = 0x0b,
                FAT32_LBA = 0x0c,
                NTFS = 0x07,
                LINUX_SWAP = 0x82,
                LINUX_NATIVE = 0x83,
                _default_ = Pass,
            ),
            BitStruct("ending",
                Octet("head"),
                Bits("sect", 6),
                Bits("cyl", 10),
            ),
            UBInt32("sector_offset"), # offset from MBR in sectors
            UBInt32("size"), # in sectors
        )
    ),
    Const(Bytes("signature", 2), "\x55\xAA"),
)



if __name__ == "__main__":
    cap1 = (
    "33C08ED0BC007CFB5007501FFCBE1B7CBF1B065057B9E501F3A4CBBDBE07B104386E00"
    "7C09751383C510E2F4CD188BF583C610497419382C74F6A0B507B4078BF0AC3C0074FC"
    "BB0700B40ECD10EBF2884E10E84600732AFE4610807E040B740B807E040C7405A0B607"
    "75D2804602068346080683560A00E821007305A0B607EBBC813EFE7D55AA740B807E10"
    "0074C8A0B707EBA98BFC1E578BF5CBBF05008A5600B408CD1372238AC1243F988ADE8A"
    "FC43F7E38BD186D6B106D2EE42F7E239560A77237205394608731CB80102BB007C8B4E"
    "028B5600CD1373514F744E32E48A5600CD13EBE48A560060BBAA55B441CD13723681FB"
    "55AA7530F6C101742B61606A006A00FF760AFF76086A0068007C6A016A10B4428BF4CD"
    "136161730E4F740B32E48A5600CD13EBD661F9C3496E76616C69642070617274697469"
    "6F6E207461626C65004572726F72206C6F6164696E67206F7065726174696E67207379"
    "7374656D004D697373696E67206F7065726174696E672073797374656D000000000000"
    "0000000000000000000000000000000000000000000000000000000000000000000000"
    "00000000000000000000000000000000002C4463B7BDB7BD00008001010007FEFFFF3F"
    "000000371671020000C1FF0FFEFFFF761671028A8FDF06000000000000000000000000"
    "000000000000000000000000000000000000000055AA"        
    ).decode("hex")
    
    print mbr.parse(cap1)






########NEW FILE########
__FILENAME__ = bmp
"""
Windows/OS2 Bitmap (BMP)
this could have been a perfect show-case file format, but they had to make
it ugly (all sorts of alignment or
"""
from construct import *


#===============================================================================
# pixels: uncompressed
#===============================================================================
def UncompressedRows(subcon, align_to_byte = False):
    """argh! lines must be aligned to a 4-byte boundary, and bit-pixel
    lines must be aligned to full bytes..."""
    if align_to_byte:
        line_pixels = Bitwise(
            Aligned(Array(lambda ctx: ctx.width, subcon), modulus = 8)
        )
    else:
        line_pixels = Array(lambda ctx: ctx.width, subcon)
    return Array(lambda ctx: ctx.height,
        Aligned(line_pixels, modulus = 4)
    )

uncompressed_pixels = Switch("uncompressed", lambda ctx: ctx.bpp,
    {
        1 : UncompressedRows(Bit("index"), align_to_byte = True),
        4 : UncompressedRows(Nibble("index"), align_to_byte = True),
        8 : UncompressedRows(Byte("index")),
        24 : UncompressedRows(
            Sequence("rgb", Byte("red"), Byte("green"), Byte("blue"))
        ),
    }
)

#===============================================================================
# pixels: Run Length Encoding (RLE) 8 bit
#===============================================================================
class RunLengthAdapter(Adapter):
    def _encode(self, obj):
        return len(obj), obj[0]
    def _decode(self, obj):
        length, value = obj
        return [value] * length

rle8pixel = RunLengthAdapter(
    Sequence("rle8pixel",
        Byte("length"),
        Byte("value")
    )
)

#===============================================================================
# file structure
#===============================================================================
bitmap_file = Struct("bitmap_file",
    # header
    Const(String("signature", 2), "BM"),
    ULInt32("file_size"),
    Padding(4),
    ULInt32("data_offset"),
    ULInt32("header_size"),
    Enum(Alias("version", "header_size"),
        v2 = 12,
        v3 = 40,
        v4 = 108,
    ),
    ULInt32("width"),
    ULInt32("height"),
    Value("number_of_pixels", lambda ctx: ctx.width * ctx.height),
    ULInt16("planes"),
    ULInt16("bpp"), # bits per pixel
    Enum(ULInt32("compression"),
        Uncompressed = 0,
        RLE8 = 1,
        RLE4 = 2,
        Bitfields = 3,
        JPEG = 4,
        PNG = 5,
    ),
    ULInt32("image_data_size"), # in bytes
    ULInt32("horizontal_dpi"),
    ULInt32("vertical_dpi"),
    ULInt32("colors_used"),
    ULInt32("important_colors"),

    # palette (24 bit has no palette)
    OnDemand(
        Array(lambda ctx: 2 ** ctx.bpp if ctx.bpp <= 8 else 0,
            Struct("palette",
                Byte("blue"),
                Byte("green"),
                Byte("red"),
                Padding(1),
            )
        )
    ),

    # pixels
    OnDemandPointer(lambda ctx: ctx.data_offset,
        Switch("pixels", lambda ctx: ctx.compression,
            {
                "Uncompressed" : uncompressed_pixels,
            }
        ),
    ),
)


if __name__ == "__main__":
    obj = bitmap_file.parse_stream(open("../../tests/bitmap8.bmp", "rb"))
    print obj
    print repr(obj.pixels.value)

########NEW FILE########
__FILENAME__ = emf
"""
Enhanced Meta File
"""
from construct import *


record_type = Enum(ULInt32("record_type"),
    ABORTPATH = 68,
    ANGLEARC = 41,
    ARC = 45,
    ARCTO = 55,
    BEGINPATH = 59,
    BITBLT = 76,
    CHORD = 46,
    CLOSEFIGURE = 61,
    CREATEBRUSHINDIRECT = 39,
    CREATEDIBPATTERNBRUSHPT = 94,
    CREATEMONOBRUSH = 93,
    CREATEPALETTE = 49,
    CREATEPEN = 38,
    DELETEOBJECT = 40,
    ELLIPSE = 42,
    ENDPATH = 60,
    EOF = 14,
    EXCLUDECLIPRECT = 29,
    EXTCREATEFONTINDIRECTW = 82,
    EXTCREATEPEN = 95,
    EXTFLOODFILL = 53,
    EXTSELECTCLIPRGN = 75,
    EXTTEXTOUTA = 83,
    EXTTEXTOUTW = 84,
    FILLPATH = 62,
    FILLRGN = 71,
    FLATTENPATH = 65,
    FRAMERGN = 72,
    GDICOMMENT = 70,
    HEADER = 1,
    INTERSECTCLIPRECT = 30,
    INVERTRGN = 73,
    LINETO = 54,
    MASKBLT = 78,
    MODIFYWORLDTRANSFORM = 36,
    MOVETOEX = 27,
    OFFSETCLIPRGN = 26,
    PAINTRGN = 74,
    PIE = 47,
    PLGBLT = 79,
    POLYBEZIER = 2,
    POLYBEZIER16 = 85,
    POLYBEZIERTO = 5,
    POLYBEZIERTO16 = 88,
    POLYDRAW = 56,
    POLYDRAW16 = 92,
    POLYGON = 3,
    POLYGON16 = 86,
    POLYLINE = 4,
    POLYLINE16 = 87,
    POLYLINETO = 6,
    POLYLINETO16 = 89,
    POLYPOLYGON = 8,
    POLYPOLYGON16 = 91,
    POLYPOLYLINE = 7,
    POLYPOLYLINE16 = 90,
    POLYTEXTOUTA = 96,
    POLYTEXTOUTW = 97,
    REALIZEPALETTE = 52,
    RECTANGLE = 43,
    RESIZEPALETTE = 51,
    RESTOREDC = 34,
    ROUNDRECT = 44,
    SAVEDC = 33,
    SCALEVIEWPORTEXTEX = 31,
    SCALEWINDOWEXTEX = 32,
    SELECTCLIPPATH = 67,
    SELECTOBJECT = 37,
    SELECTPALETTE = 48,
    SETARCDIRECTION = 57,
    SETBKCOLOR = 25,
    SETBKMODE = 18,
    SETBRUSHORGEX = 13,
    SETCOLORADJUSTMENT = 23,
    SETDIBITSTODEVICE = 80,
    SETMAPMODE = 17,
    SETMAPPERFLAGS = 16,
    SETMETARGN = 28,
    SETMITERLIMIT = 58,
    SETPALETTEENTRIES = 50,
    SETPIXELV = 15,
    SETPOLYFILLMODE = 19,
    SETROP2 = 20,
    SETSTRETCHBLTMODE = 21,
    SETTEXTALIGN = 22,
    SETTEXTCOLOR = 24,
    SETVIEWPORTEXTEX = 11,
    SETVIEWPORTORGEX = 12,
    SETWINDOWEXTEX = 9,
    SETWINDOWORGEX = 10,
    SETWORLDTRANSFORM = 35,
    STRETCHBLT = 77,
    STRETCHDIBITS = 81,
    STROKEANDFILLPATH = 63,
    STROKEPATH = 64,
    WIDENPATH = 66,
    _default_ = Pass,
)

generic_record = Struct("records",
    record_type,
    ULInt32("record_size"),      # Size of the record in bytes 
    Union("params",              # Parameters
        Field("raw", lambda ctx: ctx._.record_size - 8),
        Array(lambda ctx: (ctx._.record_size - 8) // 4, ULInt32("params"))
    ),
)

header_record = Struct("header_record",
    Const(record_type, "HEADER"),
    ULInt32("record_size"),              # Size of the record in bytes 
    SLInt32("bounds_left"),              # Left inclusive bounds 
    SLInt32("bounds_right"),             # Right inclusive bounds 
    SLInt32("bounds_top"),               # Top inclusive bounds 
    SLInt32("bounds_bottom"),            # Bottom inclusive bounds 
    SLInt32("frame_left"),               # Left side of inclusive picture frame 
    SLInt32("frame_right"),              # Right side of inclusive picture frame 
    SLInt32("frame_top"),                # Top side of inclusive picture frame 
    SLInt32("frame_bottom"),             # Bottom side of inclusive picture frame 
    Const(ULInt32("signature"), 0x464D4520),
    ULInt32("version"),                  # Version of the metafile 
    ULInt32("size"),                     # Size of the metafile in bytes 
    ULInt32("num_of_records"),           # Number of records in the metafile 
    ULInt16("num_of_handles"),           # Number of handles in the handle table 
    Padding(2),
    ULInt32("description_size"),         # Size of description string in WORDs 
    ULInt32("description_offset"),       # Offset of description string in metafile 
    ULInt32("num_of_palette_entries"),   # Number of color palette entries 
    SLInt32("device_width_pixels"),      # Width of reference device in pixels 
    SLInt32("device_height_pixels"),     # Height of reference device in pixels 
    SLInt32("device_width_mm"),          # Width of reference device in millimeters
    SLInt32("device_height_mm"),         # Height of reference device in millimeters
    
    # description string
    Pointer(lambda ctx: ctx.description_offset,
        StringAdapter(
            Array(lambda ctx: ctx.description_size,
                Field("description", 2)
            )
        )
    ),
    
    # padding up to end of record
    Padding(lambda ctx: ctx.record_size - 88),
)

emf_file = Struct("emf_file",
    header_record,
    Array(lambda ctx: ctx.header_record.num_of_records - 1, 
        generic_record
    ),
)


if __name__ == "__main__":
    obj = emf_file.parse_stream(open("../../tests/emf1.emf", "rb"))
    print obj



































########NEW FILE########
__FILENAME__ = png
"""
Portable Network Graphics (PNG) file format
Official spec: http://www.w3.org/TR/PNG

Original code contributed by Robin Munn (rmunn at pobox dot com)
(although the code has been extensively reorganized to meet Construct's
coding conventions)
"""
from construct import *


#===============================================================================
# utils
#===============================================================================
def Coord(name, field=UBInt8):
    return Struct(name,
        field("x"),
        field("y"),
    )

compression_method = Enum(UBInt8("compression_method"),
    deflate = 0,
    _default_ = Pass
)


#===============================================================================
# 11.2.3: PLTE - Palette
#===============================================================================
plte_info = Struct("plte_info",
    Value("num_entries", lambda ctx: ctx._.length / 3),
    Array(lambda ctx: ctx.num_entries,
        Struct("palette_entries",
            UBInt8("red"),
            UBInt8("green"),
            UBInt8("blue"),
        ),
    ),
)

#===============================================================================
# 11.2.4: IDAT - Image data
#===============================================================================
idat_info = OnDemand(
    Field("idat_info", lambda ctx: ctx.length),
)

#===============================================================================
# 11.3.2.1: tRNS - Transparency
#===============================================================================
trns_info = Switch("trns_info", lambda ctx: ctx._.image_header.color_type, 
    {
        "greyscale": Struct("data",
            UBInt16("grey_sample")
        ),
        "truecolor": Struct("data",
            UBInt16("red_sample"),
            UBInt16("blue_sample"),
            UBInt16("green_sample"),
        ),
        "indexed": Array(lambda ctx: ctx.length,
            UBInt8("alpha"),
        ),
    }
)

#===============================================================================
# 11.3.3.1: cHRM - Primary chromacities and white point
#===============================================================================
chrm_info = Struct("chrm_info",
    Coord("white_point", UBInt32),
    Coord("red", UBInt32),
    Coord("green", UBInt32),
    Coord("blue", UBInt32),
)

#===============================================================================
# 11.3.3.2: gAMA - Image gamma
#===============================================================================
gama_info = Struct("gama_info",
    UBInt32("gamma"),
)

#===============================================================================
# 11.3.3.3: iCCP - Embedded ICC profile
#===============================================================================
iccp_info = Struct("iccp_info",
    CString("name"),
    compression_method,
    Field("compressed_profile", 
        lambda ctx: ctx._.length - (len(ctx.name) + 2)
    ),
)

#===============================================================================
# 11.3.3.4: sBIT - Significant bits
#===============================================================================
sbit_info = Switch("sbit_info", lambda ctx: ctx._.image_header.color_type, 
    {
        "greyscale": Struct("data",
            UBInt8("significant_grey_bits"),
        ),
        "truecolor": Struct("data",
            UBInt8("significant_red_bits"),
            UBInt8("significant_green_bits"),
            UBInt8("significant_blue_bits"),
        ),
        "indexed": Struct("data",
            UBInt8("significant_red_bits"),
            UBInt8("significant_green_bits"),
            UBInt8("significant_blue_bits"),
        ),
        "greywithalpha": Struct("data",
            UBInt8("significant_grey_bits"),
            UBInt8("significant_alpha_bits"),
        ),
        "truewithalpha": Struct("data",
            UBInt8("significant_red_bits"),
            UBInt8("significant_green_bits"),
            UBInt8("significant_blue_bits"),
            UBInt8("significant_alpha_bits"),
        ),
    }
)

#===============================================================================
# 11.3.3.5: sRGB - Standard RPG color space
#===============================================================================
srgb_info = Struct("srgb_info",
    Enum(UBInt8("rendering_intent"),
        perceptual = 0,
        relative_colorimetric = 1,
        saturation = 2,
        absolute_colorimetric = 3,
        _default_ = Pass,
    ),
)

#===============================================================================
# 11.3.4.3: tEXt - Textual data
#===============================================================================
text_info = Struct("text_info",
    CString("keyword"),
    Field("text", lambda ctx: ctx._.length - (len(ctx.keyword) + 1)),
)

#===============================================================================
# 11.3.4.4: zTXt - Compressed textual data
#===============================================================================
ztxt_info = Struct("ztxt_info",
    CString("keyword"),
    compression_method,
    OnDemand(
        Field("compressed_text",
            # As with iCCP, length is chunk length, minus length of
            # keyword, minus two: one byte for the null terminator,
            # and one byte for the compression method.
            lambda ctx: ctx._.length - (len(ctx.keyword) + 2),
        ),
    ),
)

#===============================================================================
# 11.3.4.5: iTXt - International textual data
#===============================================================================
itxt_info = Struct("itxt_info",
    CString("keyword"),
    UBInt8("compression_flag"),
    compression_method,
    CString("language_tag"),
    CString("translated_keyword"),
    OnDemand(
        Field("text",
            lambda ctx: ctx._.length - (len(ctx.keyword) + 
            len(ctx.language_tag) + len(ctx.translated_keyword) + 5),
        ),
    ),
)

#===============================================================================
# 11.3.5.1: bKGD - Background color
#===============================================================================
bkgd_info = Switch("bkgd_info", lambda ctx: ctx._.image_header.color_type, 
    {
        "greyscale": Struct("data",
            UBInt16("background_greyscale_value"),
            Alias("grey", "background_greyscale_value"),
        ),
        "greywithalpha": Struct("data",
            UBInt16("background_greyscale_value"),
            Alias("grey", "background_greyscale_value"),
        ),
        "truecolor": Struct("data",
            UBInt16("background_red_value"),
            UBInt16("background_green_value"),
            UBInt16("background_blue_value"),
            Alias("red", "background_red_value"),
            Alias("green", "background_green_value"),
            Alias("blue", "background_blue_value"),
        ),
        "truewithalpha": Struct("data",
            UBInt16("background_red_value"),
            UBInt16("background_green_value"),
            UBInt16("background_blue_value"),
            Alias("red", "background_red_value"),
            Alias("green", "background_green_value"),
            Alias("blue", "background_blue_value"),
        ),
        "indexed": Struct("data",
            UBInt16("background_palette_index"),
            Alias("index", "background_palette_index"),
        ),
    }
)

#===============================================================================
# 11.3.5.2: hIST - Image histogram
#===============================================================================
hist_info = Array(lambda ctx: ctx._.length / 2,
    UBInt16("frequency"),
)

#===============================================================================
# 11.3.5.3: pHYs - Physical pixel dimensions
#===============================================================================
phys_info = Struct("phys_info",
    UBInt32("pixels_per_unit_x"),
    UBInt32("pixels_per_unit_y"),
    Enum(UBInt8("unit"),
        unknown = 0,
        meter = 1,
        _default_ = Pass
    ),
)

#===============================================================================
# 11.3.5.4: sPLT - Suggested palette
#===============================================================================
def splt_info_data_length(ctx):
    if ctx.sample_depth == 8:
        entry_size = 6
    else:
        entry_size = 10
    return (ctx._.length - len(ctx.name) - 2) / entry_size

splt_info = Struct("data",
    CString("name"),
    UBInt8("sample_depth"),
    Array(lambda ctx: splt_info_data_length,
        IfThenElse("table", lambda ctx: ctx.sample_depth == 8,
            # Sample depth 8
            Struct("table",
                UBInt8("red"),
                UBInt8("green"),
                UBInt8("blue"),
                UBInt8("alpha"),
                UBInt16("frequency"),
            ),
            # Sample depth 16
            Struct("table",
                UBInt16("red"),
                UBInt16("green"),
                UBInt16("blue"),
                UBInt16("alpha"),
                UBInt16("frequency"),
            ),
        ),
    ),
)

#===============================================================================
# 11.3.6.1: tIME - Image last-modification time
#===============================================================================
time_info = Struct("data",
    UBInt16("year"),
    UBInt8("month"),
    UBInt8("day"),
    UBInt8("hour"),
    UBInt8("minute"),
    UBInt8("second"),
)

#===============================================================================
# chunks
#===============================================================================
default_chunk_info = OnDemand(
    HexDumpAdapter(Field(None, lambda ctx: ctx.length))
)

chunk = Struct("chunk",
    UBInt32("length"),
    String("type", 4),
    Switch("data", lambda ctx: ctx.type, 
        {
            "PLTE" : plte_info,
            "IEND" : Pass,
            "IDAT" : idat_info,
            "tRNS" : trns_info,
            "cHRM" : chrm_info,
            "gAMA" : gama_info,
            "iCCP" : iccp_info,
            "sBIT" : sbit_info,
            "sRGB" : srgb_info,
            "tEXt" : text_info,
            "zTXt" : ztxt_info,
            "iTXt" : itxt_info,
            "bKGD" : bkgd_info,
            "hIST" : hist_info,
            "pHYs" : phys_info,
            "sPLT" : splt_info,
            "tIME" : time_info,
        },
        default = default_chunk_info,
    ),
    UBInt32("crc"),
)

image_header_chunk = Struct("image_header",
    UBInt32("length"),
    Const(String("type", 4), "IHDR"),
    UBInt32("width"),
    UBInt32("height"),
    UBInt8("bit_depth"),
    Enum(UBInt8("color_type"),
        greyscale = 0,
        truecolor = 2,
        indexed = 3,
        greywithalpha = 4,
        truewithalpha = 6,
        _default_ = Pass,
    ),
    compression_method,
    Enum(UBInt8("filter_method"),
        # "adaptive filtering with five basic filter types"
        adaptive5 = 0,
        _default_ = Pass,
    ),
    Enum(UBInt8("interlace_method"),
        none = 0,
        adam7 = 1,
        _default_ = Pass,
    ),
    UBInt32("crc"),
)


#===============================================================================
# the complete PNG file
#===============================================================================
png_file = Struct("png",
    Magic("\x89PNG\r\n\x1a\n"),
    image_header_chunk,
    Rename("chunks", GreedyRange(chunk)),
)

########NEW FILE########
__FILENAME__ = wmf
"""
Windows Meta File
"""
from construct import *


wmf_record = Struct("records",
    ULInt32("size"), # size in words, including the size, function and params
    Enum(ULInt16("function"),
        AbortDoc = 0x0052,
        Aldus_Header = 0x0001,
        AnimatePalette = 0x0436,
        Arc = 0x0817,
        BitBlt = 0x0922,
        Chord = 0x0830,
        CLP_Header16 = 0x0002,
        CLP_Header32 = 0x0003,
        CreateBitmap = 0x06FE,
        CreateBitmapIndirect = 0x02FD,
        CreateBrush = 0x00F8,
        CreateBrushIndirect = 0x02FC,
        CreateFontIndirect = 0x02FB,
        CreatePalette = 0x00F7,
        CreatePatternBrush = 0x01F9,
        CreatePenIndirect = 0x02FA,
        CreateRegion = 0x06FF,
        DeleteObject = 0x01F0,
        DibBitblt = 0x0940,
        DibCreatePatternBrush = 0x0142,
        DibStretchBlt = 0x0B41,
        DrawText = 0x062F,
        Ellipse = 0x0418,
        EndDoc = 0x005E,
        EndPage = 0x0050,
        EOF = 0x0000,
        Escape = 0x0626,
        ExcludeClipRect = 0x0415,
        ExtFloodFill = 0x0548,
        ExtTextOut = 0x0A32,
        FillRegion = 0x0228,
        FloodFill = 0x0419,
        FrameRegion = 0x0429,
        Header = 0x0004,
        IntersectClipRect = 0x0416,
        InvertRegion = 0x012A,
        LineTo = 0x0213,
        MoveTo = 0x0214,
        OffsetClipRgn = 0x0220,
        OffsetViewportOrg = 0x0211,
        OffsetWindowOrg = 0x020F,
        PaintRegion = 0x012B,
        PatBlt = 0x061D,
        Pie = 0x081A,
        Polygon = 0x0324,
        Polyline = 0x0325,
        PolyPolygon = 0x0538,
        RealizePalette = 0x0035,
        Rectangle = 0x041B,
        ResetDC = 0x014C,
        ResizePalette = 0x0139,
        RestoreDC = 0x0127,
        RoundRect = 0x061C,
        SaveDC = 0x001E,
        ScaleViewportExt = 0x0412,
        ScaleWindowExt = 0x0410,
        SelectClipRegion = 0x012C,
        SelectObject = 0x012D,
        SelectPalette = 0x0234,
        SetBKColor = 0x0201,
        SetBKMode = 0x0102,
        SetDibToDev = 0x0D33,
        SelLayout = 0x0149,
        SetMapMode = 0x0103,
        SetMapperFlags = 0x0231,
        SetPalEntries = 0x0037,
        SetPixel = 0x041F,
        SetPolyFillMode = 0x0106,
        SetReLabs = 0x0105,
        SetROP2 = 0x0104,
        SetStretchBltMode = 0x0107,
        SetTextAlign = 0x012E,
        SetTextCharExtra = 0x0108,
        SetTextColor = 0x0209,
        SetTextJustification = 0x020A,
        SetViewportExt = 0x020E,
        SetViewportOrg = 0x020D,
        SetWindowExt = 0x020C,
        SetWindowOrg = 0x020B,
        StartDoc = 0x014D,
        StartPage = 0x004F,
        StretchBlt = 0x0B23,
        StretchDIB = 0x0F43,
        TextOut = 0x0521,
        _default_ = Pass,
    ),
    Array(lambda ctx: ctx.size - 3, ULInt16("params")),
)

wmf_placeable_header = Struct("placeable_header",
  Const(ULInt32("key"), 0x9AC6CDD7),
  ULInt16("handle"),
  SLInt16("left"),
  SLInt16("top"),
  SLInt16("right"),
  SLInt16("bottom"),
  ULInt16("units_per_inch"),
  Padding(4),
  ULInt16("checksum")
)

wmf_file = Struct("wmf_file",
    # --- optional placeable header ---
    Optional(wmf_placeable_header),

    # --- header ---
    Enum(ULInt16("type"),
        InMemory = 0,
        File = 1,
    ),
    Const(ULInt16("header_size"), 9),
    ULInt16("version"),
    ULInt32("size"), # file size is in words
    ULInt16("number_of_objects"),
    ULInt32("size_of_largest_record"),
    ULInt16("number_of_params"),

    # --- records ---
    GreedyRange(wmf_record)
)

########NEW FILE########
__FILENAME__ = binary
def int_to_bin(number, width = 32):
    if number < 0:
        number += 1 << width
    i = width - 1
    bits = ["\x00"] * width
    while number and i >= 0:
        bits[i] = "\x00\x01"[number & 1]
        number >>= 1
        i -= 1
    return "".join(bits)

_bit_values = {"\x00" : 0, "\x01" : 1, "0" : 0, "1" : 1}
def bin_to_int(bits, signed = False):
    number = 0
    bias = 0
    if signed and _bit_values[bits[0]] == 1:
        bits = bits[1:]
        bias = 1 << len(bits)
    for b in bits:
        number <<= 1
        number |= _bit_values[b]
    return number - bias

def swap_bytes(bits, bytesize = 8):
    i = 0
    l = len(bits)
    output = [""] * ((l // bytesize) + 1)
    j = len(output) - 1
    while i < l:
        output[j] = bits[i : i + bytesize]
        i += bytesize
        j -= 1
    return "".join(output)

_char_to_bin = {}
_bin_to_char = {}
for i in range(256):
    ch = chr(i)
    bin = int_to_bin(i, 8)
    _char_to_bin[ch] = bin
    _bin_to_char[bin] = ch
    _bin_to_char[bin] = ch

def encode_bin(data):
    return "".join(_char_to_bin[ch] for ch in data)

def decode_bin(data):
    if len(data) & 7:
        raise ValueError("Data length must be a multiple of 8")

    i = 0
    j = 0
    l = len(data) // 8
    chars = [""] * l
    while j < l:
        chars[j] = _bin_to_char[data[i:i+8]]
        i += 8
        j += 1
    return "".join(chars)

########NEW FILE########
__FILENAME__ = bitstream
from construct.lib.binary import encode_bin, decode_bin

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

from UserDict import DictMixin
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

class Container(object, DictMixin):
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

    # Extended dictionary interface.

    def update(self, other):
        self.__dict__.update(other)

    __update__ = update

    def __contains__(self, value):
        return value in self.__dict__

    def iteritems(self):
        return self.__dict__.iteritems()

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
            text = repr(self._value)
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
_printable = dict((chr(i), ".") for i in range(256))
_printable.update((chr(i), chr(i)) for i in range(32, 128))

def hexdump(data, linesize):
    prettylines = []
    if len(data) < 65536:
        fmt = "%%04X   %%-%ds   %%s"
    else:
        fmt = "%%08X   %%-%ds   %%s"
    fmt = fmt % (3 * linesize - 1,)
    for i in xrange(0, len(data), linesize):
        line = data[i : i + linesize]
        hextext = " ".join(b.encode("hex") for b in line)
        rawtext = "".join(_printable[b] for b in line)
        prettylines.append(fmt % (i, hextext, rawtext))
    return prettylines

class HexString(str):
    """
    represents a string that will be hex-dumped (only via __pretty_str__).
    this class derives of str, and behaves just like a normal string in all
    other contexts.
    """

    def __init__(self, data, linesize = 16):
        self.linesize = linesize

    def __new__(cls, data, *args, **kwargs):
        return str.__new__(cls, data)

    def __str__(self):
        if not self:
            return "''"
        sep = "\n"
        return sep + sep.join(hexdump(self, self.linesize))

########NEW FILE########
__FILENAME__ = macros
from construct.lib import BitStreamReader, BitStreamWriter, encode_bin, decode_bin
from construct.core import (Struct, MetaField, StaticField, FormatField,
    OnDemand, Pointer, Switch, Value, RepeatUntil, MetaArray, Sequence, Range,
    Select, Pass, SizeofError, Buffered, Restream, Reconfig)
from construct.adapters import (BitIntegerAdapter, PaddingAdapter,
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
        {True : chr(truth), False : chr(falsehood)},
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
    from sys import maxint
    return Range(mincount, maxint, subcon)

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
    reversed_mapping = dict((v, k) for k, v in mapping.iteritems())
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

def CString(name, terminators="\x00", encoding=None,
    char_field=Field(None, 1)):
    """
    A string ending in a terminator.

    ``CString`` is similar to the strings of C, C++, and other related
    programming languages.

    By default, the terminator is the NULL byte (``0x00``).

    :param str name: name
    :param iterable terminators: sequence of valid terminators, in order of
                                 preference
    :param str encoding: encoding (e.g. "utf8") or None for no encoding
    :param ``Construct`` char_field: construct representing a single character

    >>> foo = CString("foo")
    >>> foo.parse("hello\\x00")
    'hello'
    >>> foo.build("hello")
    'hello\\x00'
    >>> foo = CString("foo", terminators = "XYZ")
    >>> foo.parse("helloX")
    'hello'
    >>> foo.parse("helloY")
    'hello'
    >>> foo.parse("helloZ")
    'hello'
    >>> foo.build("hello")
    'helloX'
    """

    return Rename(name,
        CStringAdapter(
            RepeatUntil(lambda obj, ctx: obj in terminators,
                char_field,
            ),
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
__FILENAME__ = dns
"""
Domain Name System (TCP/IP protocol stack)
"""
from construct import *
from construct.protocols.layer3.ipv4 import IpAddressAdapter


class DnsStringAdapter(Adapter):
    def _encode(self, obj, context):
        parts = obj.split(".")
        parts.append("")
        return parts
    def _decode(self, obj, context):
        return ".".join(obj[:-1])

dns_record_class = Enum(UBInt16("class"),
    RESERVED = 0,
    INTERNET = 1,
    CHAOS = 3,
    HESIOD = 4,
    NONE = 254,
    ANY = 255,
)

dns_record_type = Enum(UBInt16("type"),
    IPv4 = 1,
    AUTHORITIVE_NAME_SERVER = 2,
    CANONICAL_NAME = 5,
    NULL = 10,
    MAIL_EXCHANGE = 15,
    TEXT = 16,
    X25 = 19,
    ISDN = 20,
    IPv6 = 28,
    UNSPECIFIED = 103,
    ALL = 255,
)

query_record = Struct("query_record",
    DnsStringAdapter(
        RepeatUntil(lambda obj, ctx: obj == "",
            PascalString("name")
        )
    ),
    dns_record_type,
    dns_record_class,
)

rdata = Field("rdata", lambda ctx: ctx.rdata_length)

resource_record = Struct("resource_record",
    CString("name", terminators = "\xc0\x00"),
    Padding(1),
    dns_record_type,
    dns_record_class,
    UBInt32("ttl"),
    UBInt16("rdata_length"),
    IfThenElse("data", lambda ctx: ctx.type == "IPv4",
        IpAddressAdapter(rdata),
        rdata
    )
)

dns = Struct("dns",
    UBInt16("id"),
    BitStruct("flags",
        Enum(Bit("type"),
            QUERY = 0,
            RESPONSE = 1,
        ),
        Enum(Nibble("opcode"),
            STANDARD_QUERY = 0,
            INVERSE_QUERY = 1,
            SERVER_STATUS_REQUEST = 2,
            NOTIFY = 4,
            UPDATE = 5,
        ),
        Flag("authoritive_answer"),
        Flag("truncation"),
        Flag("recurssion_desired"),
        Flag("recursion_available"),
        Padding(1),
        Flag("authenticated_data"),
        Flag("checking_disabled"),
        Enum(Nibble("response_code"),
            SUCCESS = 0,
            FORMAT_ERROR = 1,
            SERVER_FAILURE = 2,
            NAME_DOES_NOT_EXIST = 3,
            NOT_IMPLEMENTED = 4,
            REFUSED = 5,
            NAME_SHOULD_NOT_EXIST = 6,
            RR_SHOULD_NOT_EXIST = 7,
            RR_SHOULD_EXIST = 8,
            NOT_AUTHORITIVE = 9,
            NOT_ZONE = 10,
        ),
    ),
    UBInt16("question_count"),
    UBInt16("answer_count"),
    UBInt16("authority_count"),
    UBInt16("additional_count"),
    Array(lambda ctx: ctx.question_count,
        Rename("questions", query_record),
    ),
    Rename("answers", 
        Array(lambda ctx: ctx.answer_count, resource_record)
    ),
    Rename("authorities",
        Array(lambda ctx: ctx.authority_count, resource_record)
    ),
    Array(lambda ctx: ctx.additional_count,
        Rename("additionals", resource_record),
    ),
)


if __name__ == "__main__":
    cap1 = (
    "2624010000010000000000000377777706676f6f676c6503636f6d0000010001"
    ).decode("hex")
    
    cap2 = (
    "2624818000010005000600060377777706676f6f676c6503636f6d0000010001c00c00"
    "05000100089065000803777777016cc010c02c0001000100000004000440e9b768c02c"
    "0001000100000004000440e9b793c02c0001000100000004000440e9b763c02c000100"
    "0100000004000440e9b767c030000200010000a88600040163c030c030000200010000"
    "a88600040164c030c030000200010000a88600040165c030c030000200010000a88600"
    "040167c030c030000200010000a88600040161c030c030000200010000a88600040162"
    "c030c0c00001000100011d0c0004d8ef3509c0d0000100010000ca7c000440e9b309c0"
    "80000100010000c4c5000440e9a109c0900001000100004391000440e9b709c0a00001"
    "00010000ca7c000442660b09c0b00001000100000266000440e9a709"
    ).decode("hex")

    obj = dns.parse(cap1)
    print obj
    print repr(dns.build(obj))
    
    print "-" * 80
    
    obj = dns.parse(cap2)
    print obj
    print repr(dns.build(obj))
    
    



########NEW FILE########
__FILENAME__ = http
"""
Hyper Text Transfer Protocol (TCP/IP protocol stack)

Construct is not meant for text manipulation, and is probably not the right
tool for the job, but I wanted to demonstrate how this could be done using
the provided `text` module.
"""
from construct import *
from construct.text import *


class HttpParamDictAdapter(Adapter):
    """turns the sequence of params into a dict"""
    def _encode(self, obj, context):
        return [Container(name = k, value = v) for k, v in obj.iteritems()]
    def _decode(self, obj, context):
        return dict((o.name, o.value) for o in obj)


lineterm = Literal("\r\n")
space = Whitespace()

# http parameter: 'name: value\r\n'
http_param = Struct("params",
    StringUpto("name", ":\r\n"),
    Literal(":"),
    space,
    StringUpto("value", "\r"),
    lineterm,
)

http_params = HttpParamDictAdapter(
    OptionalGreedyRange(http_param)
)

# request: command and params
http_request = Struct("request",
    StringUpto("command", " "),
    space,
    StringUpto("url", " "),
    space,
    Literal("HTTP/"),
    StringUpto("version", "\r"),
    lineterm,
    http_params,
    lineterm,
)

# reply: header (answer and params) and data
http_reply = Struct("reply",
    Literal("HTTP/"),
    StringUpto("version", " "),
    space,
    DecNumber("code"),
    space,
    StringUpto("text", "\r"),
    lineterm,
    http_params,
    lineterm,
    HexDumpAdapter(
        Field("data", lambda ctx: int(ctx["params"]["Content-length"]))
    ),
)

# session: request followed reply
http_session = Struct("session",
    http_request,
    http_reply,
)


if __name__ == "__main__":
    cap1 = (
    "474554202f636e6e2f2e656c656d656e742f696d672f312e352f6365696c696e672f6e"
    "61765f706970656c696e655f646b626c75652e67696620485454502f312e310d0a486f"
    "73743a20692e636e6e2e6e65740d0a557365722d4167656e743a204d6f7a696c6c612f"
    "352e30202857696e646f77733b20553b2057696e646f7773204e5420352e313b20656e"
    "2d55533b2072763a312e382e3129204765636b6f2f3230303631303130204669726566"
    "6f782f322e300d0a4163636570743a20696d6167652f706e672c2a2f2a3b713d302e35"
    "0d0a4163636570742d4c616e67756167653a20656e2d75732c656e3b713d302e350d0a"
    "4163636570742d456e636f64696e673a20677a69702c6465666c6174650d0a41636365"
    "70742d436861727365743a2049534f2d383835392d312c7574662d383b713d302e372c"
    "2a3b713d302e370d0a4b6565702d416c6976653a203330300d0a436f6e6e656374696f"
    "6e3a206b6565702d616c6976650d0a526566657265723a20687474703a2f2f7777772e"
    "636e6e2e636f6d2f0d0a0d0a485454502f312e3120323030204f4b0d0a446174653a20"
    "53756e2c2031302044656320323030362031373a34383a303120474d540d0a53657276"
    "65723a204170616368650d0a436f6e74656e742d747970653a20696d6167652f676966"
    "0d0a457461673a202266313232383761352d63642d3562312d30220d0a4c6173742d6d"
    "6f6469666965643a204d6f6e2c2032372046656220323030362032323a33393a303920"
    "474d540d0a436f6e74656e742d6c656e6774683a20313435370d0a4163636570742d72"
    "616e6765733a2062797465730d0a4b6565702d416c6976653a2074696d656f75743d35"
    "2c206d61783d313032340d0a436f6e6e656374696f6e3a204b6565702d416c6976650d"
    "0a0d0a47494638396148001600f7000037618d436a94ebf0f4cad5e1bccad93a638fd2"
    "dce639628e52769c97adc44c7299426a93dce3eb6182a5dee5ec5d7fa338628d466d95"
    "88a1bb3c65907b97b4d43f3ba7bacdd9e1eaa6b8cce6ebf1dc5a59cc1313718faed8e0"
    "e99fb3c8ced9e350759b6989aa6787a85e80a391a8c0ffffffbbc9d8b1c2d3e0e7eed1"
    "dae5c2cfdcd2dbe57c98b4e7ecf23b648f587ba098aec4859eb9e4e9ef3e67918aa3bc"
    "aebfd17793b1cfd9e4abbdcfbfcddbb3c3d44b71995a7da13f6791a5b8cccbd6e17491"
    "b051759cd535327390afc7d2dfb8c7d7b0c0d24e739a7693b19bb0c64f749ac3cfdd49"
    "6f97afc0d14f749b3d66916e8cacb167758ba3bdd84b4c476e96c8d4e0d84340406892"
    "597ca0d53331adbed0a3b7cb52779d6f8ead9eb2c87a96b3a6b9cc567a9f94aac294ab"
    "c24b70985a7ca1b5c5d5b9c8d7aabccfd94849819bb7acbdd0c5d1dedb5253486f9744"
    "6c95da4943ae3832b7464fc40e0e3d659096acc3546d93c63c42796b88dce4eb815b74"
    "d02d1e9db2c7dc4a4a89a1bbc2393cd8413e9aafc5d01d1eb7c6d6da4142d43837c542"
    "48d3dce6687897d3322a829cb8d93438b2c2d3cd2120c4d1dd95abc3d6dfe8ca0e0cd8"
    "4c45e1e7eeb6c5d5cdd7e2d93c3c6c8bab5f5a73b14c56c6282b5b6386cd2826cf2829"
    "d5dee73e638c9f788acf3626686683436790d02724d32f2f7f728cde6261dd6864df6d"
    "6bc0353ecc3537dd545499617387637a864a5e8e697fd437388ca5be90a7c085687e8f"
    "a6bfd31d1e48648ce26665476d96d93137cd100fcb4944587195c02e34cd1619d94342"
    "7d7a95da4141da4343d63930d73c3399677bc3d0ddd22a2ad01f22d42f2d6d7d9dd124"
    "1de14b516384a6c64c52a64b58ab49514969915b7ea2c3636a734a5daa5255d9454468"
    "87a9bb3439be3b39dc353ecf26245e7396bc444c585d806081a46283a6dd615dd74a46"
    "dd675dd74138c90909dbe2ea6d8cac834d6489a2bcb15a65c34851b8636d54789e5679"
    "9ec26e78ae5762c20000d0dae4955c68dde4ecc0676fe0e6ed87a0bb4a7098446b948c"
    "a4bd8f6980aa39317d98b5c50b0d21f90400000000002c00000000480016000008ff00"
    "01081c48b0a0c18308132a5c583000c38710234a04e070a2c58b122b62dcc8d1a0c68e"
    "20377ec4c802038290080f24b08070e4453627d0b8406950828f160f0eba9c38228311"
    "09340df2f0704f8c4e83b4b2d98a82e79fb703b77c455a06204e33816226e1100140e5"
    "191f024d267c43a18005270a17241830e8e8c051fcb88d2b044f8e3860b0be914aa5ea"
    "53bf6d02cd40da5206800d01fe189d2b500744c217022204729c10028d220edc0a74b5"
    "2a0dbb6a98a8c1d160281d2f0dd7e8595b24f086010c5c007c3921d0c11726002e0df8"
    "9153c18f79057a5ce8d10000901a066c00b8b2a40365292704680610cd8a103b02ed15"
    "db706a8ea45d539471ff222450460a3e0a00207104a08100272978e4d9c7020500062c"
    "b0a5d84124170a2e9e9c018e00fa7c90c4112d3c01803a5a48e71141d058b78940ed94"
    "f30b20b1109385206d6c204c792b78915e17678cd14208000c80c0000a3651830561c4"
    "20401766bcb1441004a447003e044c13c28c00f8b186830d1164ca1d6968f28a1e7f54"
    "10c53a1590f38c31c8e062496b068011847a2a0ce442154a54e20e0060e8e001191444"
    "e0c6070ba8a0440e5c994001013b70501c00d01149d047740493cc14c3e8c24a16adf4"
    "d2082a9d4893491b7d08a4c3058401a00803035de14018393803050a4c5ca0861bf920"
    "20c01b176061c01000d4034415304c100e0010c88e5204a50f16248a368984b2073388"
    "00008a3cf100d08d39a5084442065bb597c4401390108109631c820e0058acc0001a33"
    "c0b0c02364ccf20e005e1c01c10a17b001c00c6b5132dd450f64d0040d0909000e470f"
    "78e0402deb5ef4c1315a1470d0016a2cc09104438e70101520bd00c4044119844d0c08"
    "71d0f0c40c7549f1c506895102c61c53d1051125941010003b").decode("hex")
    x = http_session.parse(cap1)
    print x
    #print x.request.url
    #print x.request.params["Referer"]
    #print x.reply.params["Server"]
    #print "-" * 80
    #print x














########NEW FILE########
__FILENAME__ = telnet
"""
Telnet (TCP/IP protocol stack)

http://support.microsoft.com/kb/231866
"""
from construct import *
from construct.text import *


command_code = Enum(Byte("code"),
    SE = 240,                       # suboption end
    NOP = 241,                      # no-op
    Data_Mark = 242,                #
    Break = 243,                    #
    Suspend = 244,                  #
    Abort_output = 245,             #
    Are_You_There = 246,            #
    Erase_Char = 247,               #
    Erase_Line = 248,               #
    Go_Ahead = 249,                 # other side can transmit now
    SB = 250,                       # suboption begin
    WILL = 251,                     # send says it will do option
    WONT = 252,                     # send says it will NOT do option
    DO = 253,                       # sender asks other side to do option
    DONT = 254,                     # sender asks other side NOT to do option
    IAC = 255,                      # interpretr as command (escape char)
)

option_code = Enum(Byte("option"),
    TRANSMIT_BINARY = 0,
    ECHO = 1,
    RECONNECTION = 2,
    SUPPRESS_GO_AHEAD = 3,
    APPROX_MESSAGE_SIZE_NEGOTIATION = 4,
    STATUS = 5,
    TIMING_MARK = 6,
    RCTE = 7,
    OUTPUT_LINE_WIDTH = 8,
    OUTPUT_PAGE_SIZE = 9,
    NAOCRD = 10,
    NAOHTS = 11,
    NAOHTD = 12,
    NAOFFD = 13,
    NAOVTS = 14,
    NAOVTD = 15,
    NAOLFD = 16,
    EXTENDED_ASCII = 17,
    LOGOUT = 18,
    BM = 19,
    DATA_ENTRY_TERMINAL = 20,
    SUPDUP = 21,
    SUPDUP_OUTPUT = 22,
    SEND_LOCATION = 23,
    TERMINAL_TYPE = 24,
    END_OF_RECORD = 25,
    TUID = 26,
    OUTMRK = 27,
    TTYLOC = 28,
    TELNET_3270_REGIME = 29,
    X3_PAD = 30,
    NAWS = 31,
    TERMINAL_SPEED = 32,
    REMOTE_FLOW_CONTROL = 33,
    LINEMODE = 34,
    X_DISPLAY_LOCATION = 35,
    ENVIRONMENT_OPTION = 36,
    AUTHENTICATION = 37,
    ENCRYPTION_OPTION = 38,
    NEW_ENVIRONMENT_OPTION = 39,
    TN3270E = 40,
    XAUTH = 41,
    CHARSET = 42,
    RSP = 43,
    COM_PORT_CONTROL_OPTION = 44,
    TELNET_SUPPRESS_LOCAL_ECHO = 45,
    TELNET_START_TLS = 46,
    _default_ = Pass,
)

class LookaheadAdapter(Adapter):
    def _encode(self, obj, context):
        if obj == "\xff":
            obj = "\xff\xff"
        return obj
    def _decode(self, obj, context):
        first, second = obj
        if first == "\xff":
            if second == "\xff":
                return "\xff"
            else:
                raise ValidationError("IAC")
        else:
            return second

def TelnetData(name):
    return StringAdapter(
        GreedyRange(
            LookaheadAdapter(
                Sequence(name,
                    Char("data"),
                    Peek(Char("next")),
                )
            )
        )
    )

telnet_suboption = Struct("suboption",
    option_code,
    TelnetData("parameters"),
)

telnet_command = Struct("command",
    Literal("\xff"),
    command_code,
    Switch("option", lambda ctx: ctx.code,
        {
            "WILL" : option_code,
            "WONT" : option_code,
            "DO" : option_code,
            "DONT" : option_code,
            "SB" : telnet_suboption,
        },
        default = Pass,
    ),
)

telnet_unit = Select("telnet_unit",
    HexDumpAdapter(TelnetData("data")),
    telnet_command,
)

telnet_session = Rename("telnet_session", GreedyRange(telnet_unit))


if __name__ == "__main__":
    # note: this capture contains both the client and server sides
    # so you'll see echos and stuff all mingled. it's not Construct's
    # fault, i was just too lazy to separate the two.
    cap1 = (
    "fffd25fffb25fffa2501fff0fffa25000000fff0fffb26fffd18fffd20fffd23fffd27"
    "fffd24fffe26fffb18fffb1ffffc20fffc23fffb27fffc24fffd1ffffa2701fff0fffa"
    "1801fff0fffa1f009d0042fff0fffa2700fff0fffa1800414e5349fff0fffb03fffd01"
    "fffd22fffb05fffd21fffd03fffb01fffc22fffe05fffc21fffe01fffb01fffd06fffd"
    "00fffc010d0a7364662e6c6f6e65737461722e6f726720287474797239290d0a696620"
    "6e65772c206c6f67696e20276e657727202e2e0d0a0d0a6c6f67696e3a20fffd01fffc"
    "06fffb006e6e657765770d0a0d0a0d0a4c617374206c6f67696e3a2054687520446563"
    "2032312032303a31333a353320323030362066726f6d2038372e36392e34312e323034"
    "2e6361626c652e3031322e6e65742e696c206f6e2074747972760d0a0d0a596f752077"
    "696c6c206e6f7720626520636f6e6e656374656420746f204e455755534552206d6b61"
    "636374207365727665722e0d0a506c65617365206c6f67696e20617320276e65772720"
    "7768656e2070726f6d707465642e0d0a0d0a5b52455455524e5d202d2054484953204d"
    "41592054414b452041204d4f4d454e54202e2e201b5b481b5b4a547279696e67203139"
    "322e39342e37332e32302e2e2e0d0a436f6e6e656374656420746f206f6c2e66726565"
    "7368656c6c2e6f72672e0d0a4573636170652063686172616374657220697320276f66"
    "66272e0d0a0d0a7364662e6c6f6e65737461722e6f726720287474797033290d0a6966"
    "206e65772c206c6f67696e20276e657727202e2e0d0a0d0a6c6f67696e3a206e6e6577"
    "65770d0a0d0a0d0a4c617374206c6f67696e3a20546875204465632032312032303a30"
    "343a303120323030362066726f6d207364662e6c6f6e65737461722e6f7267206f6e20"
    "74747970390d0a1b5b481b5b4a57656c636f6d6520746f207468652053444620507562"
    "6c69632041636365737320554e49582053797374656d202d204573742e20313938370d"
    "0a596f75206172652074686520333735746820677565737420746f6461792c206c6f67"
    "67656420696e206f6e2032312d4465632d30362032303a31353a32332e0d0a0d0a4172"
    "6520796f75207573696e672057696e646f777320324b206f722058503f2028592f4e29"
    "200d0a202020202020202d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d"
    "2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d0d0a2020202020207c20494d504f52"
    "54414e54212020504c4541534520524541442054484953205645525920434152454655"
    "4c4c59207c0d0a202020202020202d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d"
    "2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d0d0a0d0a54686572652069"
    "7320612062756720696e207468652057696e646f777328746d292032303030202f2058"
    "502054454c4e455420636c69656e742077686963680d0a63617573657320697420746f"
    "2073656e642061203c43523e3c4c463e2028646f75626c652072657475726e29206279"
    "2064656661756c742e202049660d0a796f7520617265207573696e672057696e646f77"
    "7328746d292054454c4e455420796f75204d55535420636f7272656374207468697320"
    "5249474854204e4f570d0a696e206f7264657220746f20434f4e54494e55452e202050"
    "6c656173652074616b652074686520666f6c6c6f77696e6720342073746570733a0d0a"
    "0d0a2020312e202045534341504520746f207468652054454c4e45543e2070726f6d70"
    "74206279207072657373696e67205b4354524c5d207769746820796f7572205d206b65"
    "790d0a2020322e2020417420796f75722054454c4e45543e2070726f6d707420747970"
    "653a202027756e7365742063726c66270d0a20202020202028446f206e6f7420747970"
    "652027717569742720616674657220746869732073746570290d0a2020332e20205468"
    "656e20707265737320796f7572205b454e5445525d206b657920545749434520746f20"
    "72657475726e20746f205344460d0a2020342e20205479706520276d6b616363742720"
    "746f2063726561746520796f7572206e657720534446206163636f756e740d0a0d0a41"
    "6e20616c7465726e61746976652054454c4e455420636c69656e743a2020687474703a"
    "2f2f736466312e6f72672f74656c6e65740d0a0d0a46455020436f6d6d616e643a206d"
    "6d6b6b61616363636374740d0d0a1b5b481b5b4a0d0a504c4541534520524541442054"
    "484953204341524546554c4c593a0d0a0d0a596f75206172652061626f757420746f20"
    "637265617465206120554e4958207368656c6c206163636f756e742e20205468697320"
    "6163636f756e74206d617920626520756e6c696b650d0a616e797468696e6720796f75"
    "2776652075736564206265666f72652e20205765207572676520796f7520746f206361"
    "726566756c6c79207265616420616c6c2074686520746578740d0a646973706c617965"
    "64206f6e20796f7572207465726d696e616c2c2061732069742077696c6c2061696465"
    "20796f7520696e20796f7572206c6561726e696e672e0d0a576520616c736f20656e63"
    "6f757261676520796f7520746f2074727920616c6c2074686520636f6d6d616e647320"
    "617661696c61626c65207769746820796f7572206e65770d0a6163636f756e742e2020"
    "546865726520617265206d616e79207479706573206f662067616d65732c206170706c"
    "69636174696f6e7320616e64207574696c69746965730d0a796f752077696c6c206265"
    "2061626c6520746f20696e7374616e746c792072756e20696e206a7573742061206665"
    "77206d6f6d656e74732e2020496620796f75206172650d0a6c6f6f6b696e6720666f72"
    "206120706172746963756c617220636f6d6d616e64206f722076657273696f6e206f66"
    "206120636f6d6d616e64207468617420776520646f206e6f740d0a686176652c207468"
    "65726520617265207761797320746f2072657175657374207468617420697420626520"
    "696e7374616c6c65642e2020576520616c736f206f666665720d0a4449414c55502061"
    "636365737320696e207468652055534120616e642043616e6164612077686963682079"
    "6f752077696c6c2062652061626c6520746f206c6561726e2061626f75740d0a73686f"
    "72746c792e202042652070617469656e742c2072656164207768617420697320646973"
    "706c61796564202d204578706c6f726520616e6420456e6a6f79210d0a0d0a5b524554"
    "55524e5d0d0d0a0d0a46697273742c20796f75206e65656420746f2063686f6f736520"
    "61204c4f47494e2e202041204c4f47494e20616c6c6f777320796f7520746f204c4f47"
    "20494e0d0a746f207468652073797374656d2e2020596f7572204c4f47494e2063616e"
    "206265203120746f2038206368617261637465727320696e206c656e67746820616e64"
    "0d0a63616e20626520636f6d706f736564206f6620616c706861206e756d6572696320"
    "636861726163746572732e0d0a0d0a5768617420776f756c6420796f75206c696b6520"
    "746f2075736520666f7220796f7572206c6f67696e3f20737365626562756c756c6261"
    "62610d0d0a0d0a436f6e67726174756c6174696f6e732c20796f75277665207069636b"
    "6564206120434c45414e20757365722069642e20205768617420646f65732074686973"
    "206d65616e3f0d0a576520706572666f726d206461696c7920617564697473206f6e20"
    "6f7572206d61696c73657276657220776869636820616c6c6f777320757320746f2063"
    "6865636b206f6e20617474656d7074730d0a6f6620656d61696c2064656c6976657279"
    "20666f72206e6f6e2d6578697374656e74206c6f67696e732c206c696b652027736562"
    "756c6261272e202049662027736562756c626127207761730d0a746172676574746564"
    "20666f7220656d61696c2c20697420776f756c64206c696b656c792068617665206265"
    "656e20554345206f72207370616d2e2020486f77657665722c2074686572650d0a6861"
    "7665206265656e204e4f20617474656d70747320746f20656d61696c2027736562756c"
    "6261407364662e6c6f6e65737461722e6f72672720696e207468652070617374203234"
    "3020646179732c0d0a7768696368206d65616e732069742069732061205350414d2046"
    "524545206c6f67696e2e2020506c656173652070726f7465637420697420616e642065"
    "6e6a6f79210d0a0d0a636f6e74696e75653f20287965732f6e6f29207965730d796573"
    "0d0a1b5b481b5b4a1b5b3f31681b3d1b5b36363b31481b5b4b0d0a0d0a2a2a6c696d69"
    "746174696f6e7320616e6420706f6c6963792a2a0d0a20205f5f5f5f5f5f5f5f5f5f5f"
    "5f5f5f5f5f5f5f5f5f5f5f5f5f5f5f5f5f5f5f5f5f5f5f5f5f5f5f5f5f5f5f5f5f5f5f"
    "5f5f5f5f5f5f5f5f5f5f5f5f5f5f5f5f5f5f5f5f5f5f5f5f5f5f5f5f0d0a0d0a546865"
    "20534446205075626c69632041636365737320554e49582053797374656d2c20612035"
    "303128632937206e6f6e2d70726f66697420636f72706f726174696f6e2c0d0a726573"
    "65727665732074686520726967687420746f2064656e792061636365737320746f2061"
    "6e796f6e65207265676172646c6573732069662074686520757365720d0a686173206d"
    "616465206120646f6e6174696f6e206f722070616964206d656d626572736869702064"
    "7565732e2020496620612075736572277320616374697669746965730d0a6172652069"
    "6e74657266657272696e67207769746820616e6f746865722075736572206f72207573"
    "65727320286f6e20746869732073797374656d206f72206f6e0d0a616e6f7468657229"
    "20746865207573657220696e207175657374696f6e2077696c6c206861766520746865"
    "6972206163636f756e7420616363657373206c696d697465640d0a6f7220706f737369"
    "626c792072656d6f7665642e20205370616d6d696e67206f6620616e7920736f727420"
    "6973206e6f74207065726d697474656420616e6420776f756c640d0a726573756c7420"
    "696e206163636f756e742072656d6f76616c2e2020496c6c6567616c20616374697669"
    "746965732074686174206163746976656c7920696e766f6c7665200d0a534446202869"
    "64206573742c207573696e672053444620746f2072756e20637261636b206f7220666f"
    "72206775657373696e672070617373776f72647320616e642f6f720d0a74726164696e"
    "6720636f70797269676874656420776f726b292077696c6c206d6f7374206c696b656c"
    "7920726573756c7420696e206163636f756e742072656d6f76616c2e0d0a0d0a546865"
    "20534446205075626c69632041636365737320554e49582053797374656d206d616b65"
    "73206e6f2067756172616e7465657320696e207468652072656c696162696c6974790d"
    "0a6f7220707265736572766174696f6e206f66206163636f756e742061636365737369"
    "62696c6974792c20656d61696c2073656e74206f722072656365697665642c0d0a6669"
    "6c65732075706c6f61646564206f722063726561746564206279206f6e6c696e652065"
    "646974696e67206f7220636f6d70696c6174696f6e2e2020546861740d0a6265696e67"
    "20736169642c2064617461206c6f73732073686f756c64206f6e6c79206f6363757220"
    "647572696e67206120636174617374726f706869632068617264776172650d0a666169"
    "6c75726520696e20776869636820637269746963616c2066696c657320776f756c6420"
    "626520726573746f7265642066726f6d20746170652061726368697665732e200d0a0d"
    "0a4d656d62657273206f662074686520534446205075626c6963204163636573732055"
    "4e49582053797374656d2061726520657870656374656420746f20636f6e647563740d"
    "0a7468656d73656c76657320696e20616e20617070726f70726961746520616e642072"
    "6561736f6e61626c65206d616e6e6572207768656e207573696e67206f757220666163"
    "696c69746965732e0d0a0d0a4c69666574696d652041525041206d656d626572736869"
    "70206973206261736564206f6e20746865206c69666574696d65206f66205344462c20"
    "6e6f74206f66207468650d0a7573657220616e64206973206e6f6e2d7472616e736665"
    "7261626c652e20205344462068617320657869737465642073696e6365203139383720"
    "616e6420776974680d0a796f757220737570706f7274206974206a757374206d696768"
    "74206f7574206c69766520796f752e203b2d290d0a2020200d0a416e7920696c6c6567"
    "616c206163746976697469657320776869636820696e636c756465732c206275742063"
    "65727461696e6c792069736e2774206c696d6974656420746f0d0a7370616d6d696e67"
    "2c20706f7274666c6f6f64696e672c20706f72747363616e6e696e672c206972632062"
    "6f7473206f7220756e617474656e6465642070726f6365737365730d0a696e74656e64"
    "6564206173206120626f742c20656e6372797074696f6e20637261636b696e672c2075"
    "6e617574686f726973656420636f6e6e656374696f6e7320746f0d0a72656d6f746520"
    "686f73747320616e6420616e7920736f7274206f66207363616d2063616e207265616c"
    "6c79206e6f7420626520746f6c65726174656420686572652e0d0a5768793f20426563"
    "6175736520746865726520617265206d616e792068657265206f6e2074686973207379"
    "7374656d20746861742063616e207375666665722066726f6d0d0a7468697320736f72"
    "74206f662061627573652e2020496620796f752077616e7420746f2075736520534446"
    "2c20796f75207265616c6c79206861766520746f20636172650d0a61626f7574207468"
    "69732073797374656d20616e64207468652070656f706c6520686572652e2020496620"
    "796f7520646f6e27742077616e7420746f20636172652c207468656e0d0a796f752072"
    "65616c6c792073686f756c646e2774207573652074686973207265736f757263652e0d"
    "0a1b5b36363b31481b5b4b1b5b3f316c1b3e0d0a49206167726565207769746820796f"
    "757220706f6c69637920616e642061636365707420697420287965732f6e6f293a2079"
    "79657365730d0d0a0d0a4279206167726565696e6720616e6420616363657074696e67"
    "206f757220706f6c69637920776520747275737420796f7520746f0d0a666f6c6c6f77"
    "2069742e20205468616e6b20796f7520616e6420626520726573706f6e7369626c6521"
    "0d0a0d0a5b52455455524e5d0d0d0a1b5b481b5b4a534556454e20564552592053494d"
    "504c45205155455354494f4e533a0d0a0d0a506c656173652070726f76696465207468"
    "6520666f6c6c6f77696e6720696e666f726d6174696f6e2e2020596f757220686f6e65"
    "737479206973207265717565737465640d0a617320697420697320637269746963616c"
    "20696e206d61696e7461696e696e672074686520696e74656772697479206f66206f75"
    "722073797374656d2e20204e65770d0a6163636f756e7473207769746820626f677573"
    "20696e666f726d6174696f6e206d617920626520707572676564202a776974686f7574"
    "2a207761726e696e672e0d0a0d0a4354524c2d552077696c6c20636c65617220696e70"
    "7574202e2e0d0a0d0a596f75722046756c6c204e616d653a202020202066666f6f6f6f"
    "626261617272085e48085e4808080808080808085e485e485e485e485e485e485e485e"
    "48035e43035e4315082008082008082008082008082008082008082008082008082008"
    "0820080820080820080820080820080820080820080820080820080820080820080820"
    "08082008082008082008082008082008082008082008082008082008"
    ).decode("hex")
    print telnet_session.parse(cap1)

########NEW FILE########
__FILENAME__ = ipstack
"""
TCP/IP Protocol Stack
Note: before parsing the application layer over a TCP stream, you must
first combine all the TCP frames into a stream. See utils.tcpip for
some solutions
"""
from construct import Struct, Rename, HexDumpAdapter, Field, Switch, Pass
from construct.protocols.layer2.ethernet import ethernet_header
from construct.protocols.layer3.ipv4 import ipv4_header
from construct.protocols.layer3.ipv6 import ipv6_header
from construct.protocols.layer4.tcp import tcp_header
from construct.protocols.layer4.udp import udp_header


layer4_tcp = Struct("layer4_tcp",
    Rename("header", tcp_header),
    HexDumpAdapter(
        Field("next", lambda ctx:
            ctx["_"]["header"].payload_length - ctx["header"].header_length
        )
    ),
)

layer4_udp = Struct("layer4_udp",
    Rename("header", udp_header),
    HexDumpAdapter(
        Field("next", lambda ctx: ctx["header"].payload_length)
    ),
)

layer3_payload = Switch("next", lambda ctx: ctx["header"].protocol,
    {
        "TCP" : layer4_tcp,
        "UDP" : layer4_udp,
    },
    default = Pass
)

layer3_ipv4 = Struct("layer3_ipv4",
    Rename("header", ipv4_header),
    layer3_payload,
)

layer3_ipv6 = Struct("layer3_ipv6",
    Rename("header", ipv6_header),
    layer3_payload,
)

layer2_ethernet = Struct("layer2_ethernet",
    Rename("header", ethernet_header),
    Switch("next", lambda ctx: ctx["header"].type,
        {
            "IPv4" : layer3_ipv4,
            "IPv6" : layer3_ipv6,
        },
        default = Pass,
    )
)

ip_stack = Rename("ip_stack", layer2_ethernet)


if __name__ == "__main__":
    cap1 = (
    "0011508c283c001150886b570800450001e971474000800684e4c0a80202525eedda11"
    "2a0050d98ec61d54fe977d501844705dcc0000474554202f20485454502f312e310d0a"
    "486f73743a207777772e707974686f6e2e6f72670d0a557365722d4167656e743a204d"
    "6f7a696c6c612f352e30202857696e646f77733b20553b2057696e646f7773204e5420"
    "352e313b20656e2d55533b2072763a312e382e302e3129204765636b6f2f3230303630"
    "3131312046697265666f782f312e352e302e310d0a4163636570743a20746578742f78"
    "6d6c2c6170706c69636174696f6e2f786d6c2c6170706c69636174696f6e2f7868746d"
    "6c2b786d6c2c746578742f68746d6c3b713d302e392c746578742f706c61696e3b713d"
    "302e382c696d6167652f706e672c2a2f2a3b713d302e350d0a4163636570742d4c616e"
    "67756167653a20656e2d75732c656e3b713d302e350d0a4163636570742d456e636f64"
    "696e673a20677a69702c6465666c6174650d0a4163636570742d436861727365743a20"
    "49534f2d383835392d312c7574662d383b713d302e372c2a3b713d302e370d0a4b6565"
    "702d416c6976653a203330300d0a436f6e6e656374696f6e3a206b6565702d616c6976"
    "650d0a507261676d613a206e6f2d63616368650d0a43616368652d436f6e74726f6c3a"
    "206e6f2d63616368650d0a0d0a"
    ).decode("hex")

    cap2 = (
    "0002e3426009001150f2c280080045900598fd22000036063291d149baeec0a8023c00"
    "500cc33b8aa7dcc4e588065010ffffcecd0000485454502f312e3120323030204f4b0d"
    "0a446174653a204672692c2031352044656320323030362032313a32363a323520474d"
    "540d0a5033503a20706f6c6963797265663d22687474703a2f2f7033702e7961686f6f"
    "2e636f6d2f7733632f7033702e786d6c222c2043503d2243414f2044535020434f5220"
    "4355522041444d20444556205441492050534120505344204956416920495644692043"
    "4f4e692054454c6f204f545069204f55522044454c692053414d69204f54526920554e"
    "5269205055426920494e4420504859204f4e4c20554e49205055522046494e20434f4d"
    "204e415620494e542044454d20434e542053544120504f4c204845412050524520474f"
    "56220d0a43616368652d436f6e74726f6c3a20707269766174650d0a566172793a2055"
    "7365722d4167656e740d0a5365742d436f6f6b69653a20443d5f796c683d58336f444d"
    "54466b64476c6f5a7a567842463954417a49334d5459784e446b4563476c6b417a4578"
    "4e6a59794d5463314e5463456447567a64414d7742485274634777446157356b5a5867"
    "7462412d2d3b20706174683d2f3b20646f6d61696e3d2e7961686f6f2e636f6d0d0a43"
    "6f6e6e656374696f6e3a20636c6f73650d0a5472616e736665722d456e636f64696e67"
    "3a206368756e6b65640d0a436f6e74656e742d547970653a20746578742f68746d6c3b"
    "20636861727365743d7574662d380d0a436f6e74656e742d456e636f64696e673a2067"
    "7a69700d0a0d0a366263382020200d0a1f8b0800000000000003dcbd6977db38b200fa"
    "f9fa9cf90f88326dd9b1169212b5d891739cd84ed2936d1277a7d3cbf1a1484a624c91"
    "0c4979893bbfec7d7bbfec556121012eb29d65e6be7be7762c9240a1502854150a85c2"
    "c37b87af9f9c7c7873449e9dbc7c41defcf2f8c5f327a4d1ee76dff79e74bb872787ec"
    "43bfa3e9ddeed1ab06692cd234daed762f2e2e3a17bd4e18cfbb276fbb8b74e9f7bb49"
    "1a7b76da7152a7b1bff110dfed3f5cb896030f4b37b508566dbb9f56def9a4f1240c52"
    "3748db275791db20367b9a3452f732a5d0f688bdb0e2c44d27bf9c1cb7470830b1632f"
    "4a490a3578c18fd6b9c5dec2f7732b2641783109dc0b7268a56e2bd527a931497b93b4"
    "3f49cd493a98a4c3493a9aa4e349aa6bf01f7cd78d89d6b2ed49b3d9baf223f8b307b5"
    "004a67eea627ded2dddadedb78d8656de428f856305f5973779223b0fff05ebbbde1db"
    "67082a499289ae0f06863e1c8f4c0639eaccbdd9a3547abf798a1f0ec6c73fafd2e4f1"
    "51ffd5f1c9e2f9e37ff74e74fbddd941b375eadb0942b3e3d5723a69f6060373a6cff4"
    "9e6df586dac8b11c4d1f1afd81319b0df45e6fd4925a6cee6db4dbfb19e225bc1b12e5"
    "6a098aed9309715c3b74dc5fde3e7f122ea3308061dac22f4018a4f8878367af5f4f2e"
    "bcc001a2d187bfffbefeb2477f75026be9269165bb93d92ab0532f0cb68264fbda9b6d"
    "dd0b92bfff867f3abe1bccd3c5f675eca6ab3820c1caf7f7be20e05363029f93c8f7d2"
    "ad46a7b1bd475ff62614f2de2c8cb7f08537d93a35fed0fe9a4c1af44363fb91beabed"
    "790f4f0d0e7a6f67c7dbbe3eedfd01e5bcbffe9a64bf289e00307bb1f7852371dadb13"
    "3df0c3798efba9d93a1db44e87dbd7d8b4cf50e95c780e304be745389fbbf11ef4cddf"
    "dcf4b162d629fa94d7defbe2fa892b3ece2c78d8fb221a84517003476a73dc3ad535d6"
    "e22c7fbd0db8cf3a511ca6211d3e28933fed9d8ea54f381f66c0c7f2cb0e4c3898ad2b"
    "3b0de3c9e918bf25abc88d6ddf02d65581418f94174addc9ebe94717e67ce557207b6d"
    "45f892773ae393adc62af57c18ecd27b46e5aa2feea5b58c7c173e6d94be1d3bd5afa3"
    "fcf571d409ded9b1eb06ef3d275d00c36f25f4916c6ed2a911cef88b0e4c0ecfa7a5b6"
    "27936600b3d28d9bdbe411"
    ).decode("hex")

    obj = ip_stack.parse(cap1)
    print obj
    print repr(ip_stack.build(obj))

    print "-" * 80

    obj = ip_stack.parse(cap2)
    print obj
    print repr(ip_stack.build(obj))

########NEW FILE########
__FILENAME__ = arp
"""
Ethernet (TCP/IP protocol stack)
"""
from construct import *
from ethernet import MacAddressAdapter
from construct.protocols.layer3.ipv4 import IpAddressAdapter



def HwAddress(name):
    return IfThenElse(name, lambda ctx: ctx.hardware_type == "ETHERNET",
        MacAddressAdapter(Field("data", lambda ctx: ctx.hwaddr_length)),
        Field("data", lambda ctx: ctx.hwaddr_length)
    )

def ProtoAddress(name):
    return IfThenElse(name, lambda ctx: ctx.protocol_type == "IP",
        IpAddressAdapter(Field("data", lambda ctx: ctx.protoaddr_length)),
        Field("data", lambda ctx: ctx.protoaddr_length)
    )

arp_header = Struct("arp_header",
    Enum(UBInt16("hardware_type"),
        ETHERNET = 1,
        EXPERIMENTAL_ETHERNET = 2,
        ProNET_TOKEN_RING = 4,
        CHAOS = 5,
        IEEE802 = 6,
        ARCNET = 7,
        HYPERCHANNEL = 8,
        ULTRALINK = 13,
        FRAME_RELAY = 15,
        FIBRE_CHANNEL = 18,
        IEEE1394 = 24,
        HIPARP = 28,
        ISO7816_3 = 29,
        ARPSEC = 30,
        IPSEC_TUNNEL = 31,
        INFINIBAND = 32,
    ),
    Enum(UBInt16("protocol_type"),
        IP = 0x0800,
    ),
    UBInt8("hwaddr_length"),
    UBInt8("protoaddr_length"),
    Enum(UBInt16("opcode"),
        REQUEST = 1,
        REPLY = 2,
        REQUEST_REVERSE = 3,
        REPLY_REVERSE = 4,
        DRARP_REQUEST = 5,
        DRARP_REPLY = 6,
        DRARP_ERROR = 7,
        InARP_REQUEST = 8,
        InARP_REPLY = 9,
        ARP_NAK = 10
        
    ),
    HwAddress("source_hwaddr"),
    ProtoAddress("source_protoaddr"),
    HwAddress("dest_hwaddr"),
    ProtoAddress("dest_protoaddr"),
)

rarp_header = Rename("rarp_header", arp_header)


if __name__ == "__main__":
    cap1 = "00010800060400010002e3426009c0a80204000000000000c0a80201".decode("hex")
    obj = arp_header.parse(cap1)
    print obj
    print repr(arp_header.build(obj))

    print "-" * 80
    
    cap2 = "00010800060400020011508c283cc0a802010002e3426009c0a80204".decode("hex")
    obj = arp_header.parse(cap2)
    print obj
    print repr(arp_header.build(obj))














########NEW FILE########
__FILENAME__ = ethernet
"""
Ethernet (TCP/IP protocol stack)
"""
from construct import *


class MacAddressAdapter(Adapter):
    def _encode(self, obj, context):
        return obj.replace("-", "").decode("hex")
    def _decode(self, obj, context):
        return "-".join(b.encode("hex") for b in obj)

def MacAddress(name):
    return MacAddressAdapter(Bytes(name, 6))

ethernet_header = Struct("ethernet_header",
    MacAddress("destination"),
    MacAddress("source"),
    Enum(UBInt16("type"),
        IPv4 = 0x0800,
        ARP = 0x0806,
        RARP = 0x8035,
        X25 = 0x0805,
        IPX = 0x8137,
        IPv6 = 0x86DD,
        _default_ = Pass,
    ),
)


if __name__ == "__main__":
    cap = "0011508c283c0002e34260090800".decode("hex")
    obj = ethernet_header.parse(cap)
    print obj
    print repr(ethernet_header.build(obj))


########NEW FILE########
__FILENAME__ = mtp2
"""
Message Transport Part 2 (SS7 protocol stack)
(untested)
"""
from construct import *


mtp2_header = BitStruct("mtp2_header",
    Octet("flag1"),
    Bits("bsn", 7),
    Bit("bib"),
    Bits("fsn", 7),
    Bit("sib"),
    Octet("length"),
    Octet("service_info"),
    Octet("signalling_info"),
    Bits("crc", 16),
    Octet("flag2"),
)



########NEW FILE########
__FILENAME__ = dhcpv4
"""
Dynamic Host Configuration Protocol for IPv4

http://www.networksorcery.com/enp/protocol/dhcp.htm
http://www.networksorcery.com/enp/protocol/bootp/options.htm
"""
from construct import *
from ipv4 import IpAddress


dhcp_option = Struct("dhcp_option",
    Enum(Byte("code"),
        Pad = 0,
        Subnet_Mask = 1,
        Time_Offset = 2,
        Router = 3,
        Time_Server = 4,
        Name_Server = 5,
        Domain_Name_Server = 6,
        Log_Server = 7,
        Quote_Server = 8,
        LPR_Server = 9,
        Impress_Server = 10,
        Resource_Location_Server = 11,
        Host_Name = 12,
        Boot_File_Size = 13,
        Merit_Dump_File = 14,
        Domain_Name = 15,
        Swap_Server = 16,
        Root_Path = 17,
        Extensions_Path = 18,
        IP_Forwarding_enabledisable = 19,
        Nonlocal_Source_Routing_enabledisable = 20,
        Policy_Filter = 21,
        Maximum_Datagram_Reassembly_Size = 22,
        Default_IP_TTL = 23,
        Path_MTU_Aging_Timeout = 24,
        Path_MTU_Plateau_Table = 25,
        Interface_MTU = 26,
        All_Subnets_are_Local = 27,
        Broadcast_Address = 28,
        Perform_Mask_Discovery = 29,
        Mask_supplier = 30,
        Perform_router_discovery = 31,
        Router_solicitation_address = 32,
        Static_routing_table = 33,
        Trailer_encapsulation = 34,
        ARP_cache_timeout = 35,
        Ethernet_encapsulation = 36,
        Default_TCP_TTL = 37,
        TCP_keepalive_interval = 38,
        TCP_keepalive_garbage = 39,
        Network_Information_Service_domain = 40,
        Network_Information_Servers = 41,
        NTP_servers = 42,
        Vendor_specific_information = 43,
        NetBIOS_over_TCPIP_name_server = 44,
        NetBIOS_over_TCPIP_Datagram_Distribution_Server = 45,
        NetBIOS_over_TCPIP_Node_Type = 46,
        NetBIOS_over_TCPIP_Scope = 47,
        X_Window_System_Font_Server = 48,
        X_Window_System_Display_Manager = 49,
        Requested_IP_Address = 50,
        IP_address_lease_time = 51,
        Option_overload = 52,
        DHCP_message_type = 53,
        Server_identifier = 54,
        Parameter_request_list = 55,
        Message = 56,
        Maximum_DHCP_message_size = 57,
        Renew_time_value = 58,
        Rebinding_time_value = 59,
        Class_identifier = 60,
        Client_identifier = 61,
        NetWareIP_Domain_Name = 62,
        NetWareIP_information = 63,
        Network_Information_Service_Domain = 64,
        Network_Information_Service_Servers = 65,
        TFTP_server_name = 66,
        Bootfile_name = 67,
        Mobile_IP_Home_Agent = 68,
        Simple_Mail_Transport_Protocol_Server = 69,
        Post_Office_Protocol_Server = 70,
        Network_News_Transport_Protocol_Server = 71,
        Default_World_Wide_Web_Server = 72,
        Default_Finger_Server = 73,
        Default_Internet_Relay_Chat_Server = 74,
        StreetTalk_Server = 75,
        StreetTalk_Directory_Assistance_Server = 76,
        User_Class_Information = 77,
        SLP_Directory_Agent = 78,
        SLP_Service_Scope = 79,
        Rapid_Commit = 80,
        Fully_Qualified_Domain_Name = 81,
        Relay_Agent_Information = 82,
        Internet_Storage_Name_Service = 83,
        NDS_servers = 85,
        NDS_tree_name = 86,
        NDS_context = 87,
        BCMCS_Controller_Domain_Name_list = 88,
        BCMCS_Controller_IPv4_address_list = 89,
        Authentication = 90,
        Client_last_transaction_time = 91,
        Associated_ip = 92,
        Client_System_Architecture_Type = 93,
        Client_Network_Interface_Identifier = 94,
        Lightweight_Directory_Access_Protocol = 95,
        Client_Machine_Identifier = 97,
        Open_Group_User_Authentication = 98,
        Autonomous_System_Number = 109,
        NetInfo_Parent_Server_Address = 112,
        NetInfo_Parent_Server_Tag = 113,
        URL = 114,
        Auto_Configure = 116,
        Name_Service_Search = 117,
        Subnet_Selection = 118,
        DNS_domain_search_list = 119,
        SIP_Servers_DHCP_Option = 120,
        Classless_Static_Route_Option = 121,
        CableLabs_Client_Configuration = 122,
        GeoConf = 123,
    ),
    Switch("value", lambda ctx: ctx.code,
        {
            # codes without any value
            "Pad" : Pass,
        },
        # codes followed by length and value fields
        default = Struct("value",
            Byte("length"),
            Field("data", lambda ctx: ctx.length),
        )
    )
)

dhcp_header = Struct("dhcp_header",
    Enum(Byte("opcode"),
        BootRequest = 1,
        BootReply = 2,
    ),
    Enum(Byte("hardware_type"),
        Ethernet = 1,
        Experimental_Ethernet = 2,
        ProNET_Token_Ring = 4,
        Chaos = 5,
        IEEE_802 = 6,
        ARCNET = 7,
        Hyperchannel = 8,
        Lanstar = 9,        
    ),
    Byte("hardware_address_length"),
    Byte("hop_count"),
    UBInt32("transaction_id"),
    UBInt16("elapsed_time"),
    BitStruct("flags",
        Flag("boardcast"),
        Padding(15),
    ),
    IpAddress("client_addr"),
    IpAddress("your_addr"),
    IpAddress("server_addr"),
    IpAddress("gateway_addr"),
    IpAddress("client_addr"),
    Bytes("client_hardware_addr", 16),
    Bytes("server_host_name", 64),
    Bytes("boot_filename", 128),
    # BOOTP/DHCP options
    # "The first four bytes contain the (decimal) values 99, 130, 83 and 99"
    Const(Bytes("magic", 4), "\x63\x82\x53\x63"),
    Rename("options", OptionalGreedyRange(dhcp_option)),
)


if __name__ == "__main__":
    test = (
        "01" "01" "08" "ff" "11223344" "1234" "0000" 
        "11223344" "aabbccdd" "11223444" "aabbccdd" "11223344"
        
        "11223344556677889900aabbccddeeff"
        
        "41414141414141414141414141414141" "41414141414141414141414141414141"
        "41414141414141414141414141414141" "41414141414141414141414141414141"
        
        "42424242424242424242424242424242" "42424242424242424242424242424242"
        "42424242424242424242424242424242" "42424242424242424242424242424242"
        "42424242424242424242424242424242" "42424242424242424242424242424242"
        "42424242424242424242424242424242" "42424242424242424242424242424242"
        
        "63825363"
        
        "0104ffffff00"
        "00"
        "060811223344aabbccdd"
    ).decode("hex")
    
    print dhcp_header.parse(test)















########NEW FILE########
__FILENAME__ = dhcpv6
"""
the Dynamic Host Configuration Protocol (DHCP) for IPv6

http://www.networksorcery.com/enp/rfc/rfc3315.txt
"""
from construct import *
from ipv6 import Ipv6Address


dhcp_option = Struct("dhcp_option",
    Enum(UBInt16("code"),
        OPTION_CLIENTID = 1,
        OPTION_SERVERID = 2,
        OPTION_IA_NA = 3,
        OPTION_IA_TA = 4,
        OPTION_IAADDR = 5,
        OPTION_ORO = 6,
        OPTION_PREFERENCE = 7,
        OPTION_ELAPSED_TIME = 8,
        OPTION_RELAY_MSG = 9,
        OPTION_AUTH = 11,
        OPTION_UNICAST = 12,
        OPTION_STATUS_CODE = 13,
        OPTION_RAPID_COMMIT = 14,
        OPTION_USER_CLASS = 15,
        OPTION_VENDOR_CLASS = 16,
        OPTION_VENDOR_OPTS = 17,
        OPTION_INTERFACE_ID = 18,
        OPTION_RECONF_MSG = 19,
        OPTION_RECONF_ACCEPT = 20,
        SIP_SERVERS_DOMAIN_NAME_LIST = 21,
        SIP_SERVERS_IPV6_ADDRESS_LIST = 22,
        DNS_RECURSIVE_NAME_SERVER = 23,
        DOMAIN_SEARCH_LIST = 24,
        OPTION_IA_PD = 25,
        OPTION_IAPREFIX = 26,
        OPTION_NIS_SERVERS = 27,
        OPTION_NISP_SERVERS = 28,
        OPTION_NIS_DOMAIN_NAME = 29,
        OPTION_NISP_DOMAIN_NAME = 30,
        SNTP_SERVER_LIST = 31,
        INFORMATION_REFRESH_TIME = 32,
        BCMCS_CONTROLLER_DOMAIN_NAME_LIST = 33,
        BCMCS_CONTROLLER_IPV6_ADDRESS_LIST = 34,
        OPTION_GEOCONF_CIVIC = 36,
        OPTION_REMOTE_ID = 37,
        RELAY_AGENT_SUBSCRIBER_ID = 38,
        OPTION_CLIENT_FQDN = 39,        
    ),
    UBInt16("length"),
    Field("data", lambda ctx: ctx.length),
)

client_message = Struct("client_message",
    Bitwise(BitField("transaction_id", 24)),
)

relay_message = Struct("relay_message",
    Byte("hop_count"),
    Ipv6Address("linkaddr"),
    Ipv6Address("peeraddr"),
)

dhcp_message = Struct("dhcp_message",
    Enum(Byte("msgtype"),
        # these are client-server messages
        SOLICIT = 1,
        ADVERTISE = 2,
        REQUEST = 3,
        CONFIRM = 4,
        RENEW = 5,
        REBIND = 6,
        REPLY = 7,
        RELEASE_ = 8,
        DECLINE_ = 9,
        RECONFIGURE = 10,
        INFORMATION_REQUEST = 11,
        # these two are relay messages
        RELAY_FORW = 12,
        RELAY_REPL = 13,
    ),
    # relay messages have a different structure from client-server messages
    Switch("params", lambda ctx: ctx.msgtype,
        {
            "RELAY_FORW" : relay_message,
            "RELAY_REPL" : relay_message,
        },
        default = client_message,
    ),
    Rename("options", GreedyRange(dhcp_option)),
)


if __name__ == "__main__":
    test1 = "\x03\x11\x22\x33\x00\x17\x00\x03ABC\x00\x05\x00\x05HELLO"
    test2 = "\x0c\x040123456789abcdef0123456789abcdef\x00\x09\x00\x0bhello world\x00\x01\x00\x00"
    print dhcp_message.parse(test1)
    print dhcp_message.parse(test2)














########NEW FILE########
__FILENAME__ = icmpv4
"""
Internet Control Message Protocol for IPv4 (TCP/IP protocol stack)
"""
from construct import *
from ipv4 import IpAddress


echo_payload = Struct("echo_payload",
    UBInt16("identifier"),
    UBInt16("sequence"),
    Bytes("data", 32), # length is implementation dependent... 
                       # is anyone using more than 32 bytes?
)

dest_unreachable_payload = Struct("dest_unreachable_payload",
    Padding(2),
    UBInt16("next_hop_mtu"),
    IpAddress("host"),
    Bytes("echo", 8),
)

dest_unreachable_code = Enum(Byte("code"),
    Network_unreachable_error = 0,
    Host_unreachable_error = 1,
    Protocol_unreachable_error = 2,
    Port_unreachable_error = 3,
    The_datagram_is_too_big = 4,
    Source_route_failed_error = 5,
    Destination_network_unknown_error = 6,
    Destination_host_unknown_error = 7,
    Source_host_isolated_error = 8,
    Desination_administratively_prohibited = 9,
    Host_administratively_prohibited2 = 10,
    Network_TOS_unreachable = 11,
    Host_TOS_unreachable = 12,
)

icmp_header = Struct("icmp_header",
    Enum(Byte("type"),
        Echo_reply = 0,
        Destination_unreachable = 3,
        Source_quench = 4,
        Redirect = 5,
        Alternate_host_address = 6,
        Echo_request = 8,
        Router_advertisement = 9,
        Router_solicitation = 10,
        Time_exceeded = 11,
        Parameter_problem = 12,
        Timestamp_request = 13,
        Timestamp_reply = 14,
        Information_request = 15,
        Information_reply = 16,
        Address_mask_request = 17,
        Address_mask_reply = 18,
        _default_ = Pass,
    ),
    Switch("code", lambda ctx: ctx.type, 
        {
            "Destination_unreachable" : dest_unreachable_code,
        },
        default = Byte("code"),
    ),
    UBInt16("crc"),
    Switch("payload", lambda ctx: ctx.type, 
        {
            "Echo_reply" : echo_payload,
            "Echo_request" : echo_payload,
            "Destination_unreachable" : dest_unreachable_payload,
        }, 
        default = Pass
    )
)


if __name__ == "__main__":
    cap1 = ("0800305c02001b006162636465666768696a6b6c6d6e6f70717273747576776162"
        "63646566676869").decode("hex")
    cap2 = ("0000385c02001b006162636465666768696a6b6c6d6e6f70717273747576776162"
        "63646566676869").decode("hex")
    cap3 = ("0301000000001122aabbccdd0102030405060708").decode("hex")
    
    print icmp_header.parse(cap1)
    print icmp_header.parse(cap2)
    print icmp_header.parse(cap3)












########NEW FILE########
__FILENAME__ = igmpv2
"""
What : Internet Group Management Protocol, Version 2
 How : http://www.ietf.org/rfc/rfc2236.txt
 Who : jesse @ housejunkie . ca
"""

from construct import (
    Byte,
    Enum,
    Struct,
    UBInt16,
    UBInt32,
)
from construct.protocols.layer3.ipv4 import IpAddress

igmp_type = Enum(Byte("igmp_type"), 
    MEMBERSHIP_QUERY = 0x11,
    MEMBERSHIP_REPORT_V1 = 0x12,
    MEMBERSHIP_REPORT_V2 = 0x16,
    LEAVE_GROUP = 0x17,
)

igmpv2_header = Struct("igmpv2_header",
    igmp_type,
    Byte("max_resp_time"),
    UBInt16("checksum"),
    IpAddress("group_address"),
)

if __name__ == '__main__':
    
    capture = "1600FA01EFFFFFFD".decode("hex")
    print igmpv2_header.parse(capture)

########NEW FILE########
__FILENAME__ = ipv4
"""
Internet Protocol version 4 (TCP/IP protocol stack)
"""
from construct import *


class IpAddressAdapter(Adapter):
    def _encode(self, obj, context):
        return "".join(chr(int(b)) for b in obj.split("."))
    def _decode(self, obj, context):
        return ".".join(str(ord(b)) for b in obj)

def IpAddress(name):
    return IpAddressAdapter(Bytes(name, 4))

def ProtocolEnum(code):
    return Enum(code,
        ICMP = 1,
        TCP = 6,
        UDP = 17,
    )

ipv4_header = Struct("ip_header",
    EmbeddedBitStruct(
        Const(Nibble("version"), 4),
        ExprAdapter(Nibble("header_length"), 
            decoder = lambda obj, ctx: obj * 4, 
            encoder = lambda obj, ctx: obj / 4
        ),
    ),
    BitStruct("tos",
        Bits("precedence", 3),
        Flag("minimize_delay"),
        Flag("high_throuput"),
        Flag("high_reliability"),
        Flag("minimize_cost"),
        Padding(1),
    ),
    UBInt16("total_length"),
    Value("payload_length", lambda ctx: ctx.total_length - ctx.header_length),
    UBInt16("identification"),
    EmbeddedBitStruct(
        Struct("flags",
            Padding(1),
            Flag("dont_fragment"),
            Flag("more_fragments"),
        ),
        Bits("frame_offset", 13),
    ),
    UBInt8("ttl"),
    ProtocolEnum(UBInt8("protocol")),
    UBInt16("checksum"),
    IpAddress("source"),
    IpAddress("destination"),
    Field("options", lambda ctx: ctx.header_length - 20),
)


if __name__ == "__main__":
    cap = "4500003ca0e3000080116185c0a80205d474a126".decode("hex")
    obj = ipv4_header.parse(cap)
    print obj
    print repr(ipv4_header.build(obj))










########NEW FILE########
__FILENAME__ = ipv6
"""
Internet Protocol version 6 (TCP/IP protocol stack)
"""
from construct import *
from ipv4 import ProtocolEnum


class Ipv6AddressAdapter(Adapter):
    def _encode(self, obj, context):
        return "".join(part.decode("hex") for part in obj.split(":"))
    def _decode(self, obj, context):
        return ":".join(b.encode("hex") for b in obj)

def Ipv6Address(name):
    return Ipv6AddressAdapter(Bytes(name, 16))


ipv6_header = Struct("ip_header",
    EmbeddedBitStruct(
        OneOf(Bits("version", 4), [6]),
        Bits("traffic_class", 8),
        Bits("flow_label", 20),
    ),
    UBInt16("payload_length"),
    ProtocolEnum(UBInt8("protocol")),
    UBInt8("hoplimit"),
    Alias("ttl", "hoplimit"),
    Ipv6Address("source"),
    Ipv6Address("destination"),
)


if __name__ == "__main__":
    o = ipv6_header.parse("\x6f\xf0\x00\x00\x01\x02\x06\x80"
        "0123456789ABCDEF" "FEDCBA9876543210"
        )
    print o
    print repr(ipv6_header.build(o))







########NEW FILE########
__FILENAME__ = mtp3
"""
Message Transport Part 3 (SS7 protocol stack)
(untested)
"""
from construct import *


mtp3_header = BitStruct("mtp3_header",
    Nibble("service_indicator"),
    Nibble("subservice"),
)


########NEW FILE########
__FILENAME__ = isup
"""
ISDN User Part (SS7 protocol stack)
"""
from construct import *


isup_header = Struct("isup_header",
    Bytes("routing_label", 5),
    UBInt16("cic"),
    UBInt8("message_type"),
    # mandatory fixed parameters
    # mandatory variable parameters
    # optional parameters
)


########NEW FILE########
__FILENAME__ = tcp
"""
Transmission Control Protocol (TCP/IP protocol stack)
"""
from construct import *


tcp_header = Struct("tcp_header",
    UBInt16("source"),
    UBInt16("destination"),
    UBInt32("seq"),
    UBInt32("ack"),
    EmbeddedBitStruct(
        ExprAdapter(Nibble("header_length"), 
            encoder = lambda obj, ctx: obj / 4,
            decoder = lambda obj, ctx: obj * 4,
        ),
        Padding(3),
        Struct("flags",
            Flag("ns"),
            Flag("cwr"),
            Flag("ece"),
            Flag("urg"),
            Flag("ack"),
            Flag("psh"),
            Flag("rst"),
            Flag("syn"),
            Flag("fin"),
        ),
    ),
    UBInt16("window"),
    UBInt16("checksum"),
    UBInt16("urgent"),
    Field("options", lambda ctx: ctx.header_length - 20),
)

if __name__ == "__main__":
    cap = "0db5005062303fb21836e9e650184470c9bc0000".decode("hex")
    
    obj = tcp_header.parse(cap)
    print obj
    print repr(tcp_header.build(obj))

















########NEW FILE########
__FILENAME__ = udp
"""
User Datagram Protocol (TCP/IP protocol stack)
"""
from construct import *


udp_header = Struct("udp_header",
    Value("header_length", lambda ctx: 8),
    UBInt16("source"),
    UBInt16("destination"),
    ExprAdapter(UBInt16("payload_length"), 
        encoder = lambda obj, ctx: obj + 8,
        decoder = lambda obj, ctx: obj - 8,
    ),
    UBInt16("checksum"),
)

if __name__ == "__main__":
    cap = "0bcc003500280689".decode("hex")
    obj = udp_header.parse(cap)
    print obj
    print repr(udp_header.build(obj))



########NEW FILE########
__FILENAME__ = csvtest
from construct import *
from construct.text import *


class LineSplitAdapter(Adapter):
   def _decode(self, obj, context):
       return obj.split('\t')
   def _encode(self, obj, context):
       return '\t'.join(obj)+'\n'

sectionrow = Struct('sectionrow',
    QuotedString('sectionname', start_quote='[', end_quote=']'),
    Line('restofline'),
    Literal('\n'),
)

fieldsrow = Struct('fieldsrow',
    Literal('FIELDS\t'),
    LineSplitAdapter(
        Line('items')
    ),
    Literal('\n'),
)

data = Struct('data',
    OptionalGreedyRange(
        Struct('data',
            Literal('DATA\t'),
            LineSplitAdapter(
                Line('items')
            ),
            Literal('\n'),
        )
    )
)

section = Struct('section',
    sectionrow,
    fieldsrow,
    data,
    Literal('\n')
)

sections = Struct('sections',
    GreedyRange(section)
)


if __name__ == "__main__":
    import psyco
    psyco.full()
    numdatarows = 2000
    
    tsvstring = (
    '[ENGINEBAY]'+'\t'*80 + '\n' + 
    'FIELDS'+('\tTIMESTAMP\tVOLTAGE\tCURRENT\tTEMPERATURE'*20) + '\n' + 
    ('DATA'+('\t12:13:14.15\t1.2345\t2.3456\t345.67'*20) +
    '\n')*numdatarows + '\n' + 
    '[CARGOBAY]'+'\t'*80 + '\n' + 
    'FIELDS'+('\tTIMESTAMP\tVOLTAGE\tCURRENT\tTEMPERATURE'*20) + '\n' + 
    ('DATA'+('\t12:13:14.15\t1.2345\t2.3456\t345.67'*20) +
    '\n')*numdatarows + '\n' + 
    '[FRONTWHEELWELL]'+'\t'*80 + '\n' + 
    'FIELDS'+('\tTIMESTAMP\tVOLTAGE\tCURRENT\tTEMPERATURE'*20) + '\n' + 
    ('DATA'+('\t12:13:14.15\t1.2345\t2.3456\t345.67'*20) +
    '\n')*numdatarows + '\n' + 
    '[REARWHEELWELL]'+'\t'*80 + '\n' + 
    'FIELDS'+('\tTIMESTAMP\tVOLTAGE\tCURRENT\tTEMPERATURE'*20) + '\n' +
    ('DATA'+('\t12:13:14.15\t1.2345\t2.3456\t345.67'*20) + '\n') * numdatarows + '\n'
    )
    
    #print len(tsvstring)
    
    import time
    t = time.time()
    x = sections.parse(tsvstring)
    print time.time() - t
    # 43.2030000687 / 3.10899996758 with psyco (x13)
    
    t = time.time()
    s = sections.build(x)
    print time.time() - t
    # 39.625 / 2.65700006485 with psyco (x14)
    
    print s == tsvstring
    # True










########NEW FILE########
__FILENAME__ = debug
from construct import *


foo = Struct("foo",
    UBInt8("bar"),
    Debugger(
        Enum(UBInt8("spam"),
            ABC = 1,
            DEF = 2,
            GHI = 3,
        )
    ),
    UBInt8("eggs"),
)


print foo.parse("\x01\x02\x03")

print foo.parse("\x01\x04\x03")


########NEW FILE########
__FILENAME__ = test_snoop
from unittest import TestCase

from construct.formats.data.snoop import snoop_file

data = """
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
NlDy4QAAaWMJAAcAAIoAYHDMW4kAUqqqAwgAB4CbAEo52wAAD63/2wL9AiF6D63b/QAVUklDIENh
bGVuZGFyIFNlcnZlciAzDk5VRCAyLjAgU2VydmVyEFJFU0VBUkNIIElNQUdJTkcAAAA8AAAAPAAA
AFQAAAAANlDy4QAAgX0JAAcAACsIAIcavmkALqqqAwgAB4CbACYAAAAAAFH/TgICAiH1D6uN/gAB
PQNOUkwLUEFUSE9MT0dZL0UAAABCAAAAQgAAAFwAAAAANlDy4QAAycUIACCSbaEABikhIrsIAEUA
ADQVSwAAPAZdqoFvA8iBbwUpBbEAFjnH6a2ECrLOgBA+OOw1AAABAQgKNrAdQQK1icQCtQAAAFwA
AABcAAAAdAAAAAA2UPLhAALGPf///////wAgSAT9jAgARQAATvBrAACAEVoLgW/tSYFv//8AiQCJ
ADqQvt0EARAAAQAAAAAAACBFTkVGRUVFSkVERUpFT0VGRlBFSEVKQ0FDQUNBQ0FCTwAAIAABAAAA
XAAAAFwAAAB0AAAAADZQ8uEAA0At////////ACBIBP2MCABFAABO8WsAAIARWQuBb+1JgW///wCJ
AIkAOnqv3QoBEAABAAAAAAAAIEVORUZFRUVKRURFSkVPRUZGUEVKRU9FR0VGRURGRUJMAAAgAAEA
AAA8AAAAPAAAAFQAAAAANlDy4QAEcewJAIeQ//8IAIcKPEUIiRgAaE4AAAAcEFhZUF8wODAwODcw
QTNDNDUAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAFWAAABVgAAAXAAAAAANlDy4QAEgHP///////8I
AIcKPEUIAEUAAUgAoQAAQBFyroFvA3iBb///AEQAQwE0AAABAQYAAAAAAAAAAACBbwN4AAAAAAAA
AACBbwENCACHCjxFAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAB4MGEzYzQ1LnBybQAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
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
AIkAOvi+pS4BEAABAAAAAAAAIEVGRkFFSkVFRUZFTkVKRVBFTUVQRUhGSkNBQ0FDQUJMAAAgAAEA
AABcAAAAXAAAAHQAAAAANlDy4gAHEJr///////8AIEgE/YwIAEUAAE78awAAgBFOC4Fv7UmBb///
AIkAiQA6eqndEAEQAAEAAAAAAAAgRU5FRkVFRUpFREVKRU9FRkZQRUpFT0VHRUZFREZFQkwAACAA
AQAAADIAAAAyAAAATAAAAAA2UPLiAAep+wkAB////wgAB/fXPwAkqqoDAAAAgPMAAYCbBgQAAQgA
B/fXPwAAVz8AAAAAAAAAAB6tAAAAAAA8AAAAPAAAAFQAAAAANlDy4gAIss2rAAADAACqAAQAEEVg
AyIADQIAAKoABAAQRQPaBQAAAAAAAAAAAKoABADKRA8AAAKqqgAAAAAAAAAAAAAAAABgAAAAYAAA
AHgAAAAANlDy4gAKOtEJAAcAAIoAYHDMW4kAUqqqAwgAB4CbAEo52wAAD63/2wL9AiF6D63b/QAV
UklDIENhbGVuZGFyIFNlcnZlciAzDk5VRCAyLjAgU2VydmVyEFJFU0VBUkNIIElNQUdJTkcAAAA5
AAAAOQAAAFQAAAAANlDy4gAK1qgJAAf///8IAIcavmgAK6qqAwgAB4CbACMAAAAAAD///QEBAQA/
CP0ACoAAY4IPpYAPpYIACoAAY4JydmUAAADYAAAA2AAAAPAAAAAANlDy4gAK5HT///////8AIEgE
/YwIAEUAAMr+awAAgBFLj4Fv7UmBb///AIoAigC2oN0RGt0cgW/tSQCKAKAAACBFQkZHRUZFT0VI
RUZGQ0NBQ0FDQUNBQ0FDQUNBQ0FBQQAgRURFUEVORkFGUEZDRUZGREVQRkZGQ0VERUZGRENBQk4A
/1NNQiUAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAARAAAGAAAAAAAAAAAA6AMAAAAAAAAAAAYA
VgADAAEAAQACABcAXE1BSUxTTE9UXEJST1dTRQAJBANDAAAAAACAAAAAgAAAAJgAAAAANlDy4gAM
Xq6rAAQBAgGqAAQA1ERgB3AAqwAEAQIBAgCqAAQA1ESgAAgAAIAEAQAABkRBTVJPRACAAf+DAAQA
AAAAAAAAAAAQAwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAhAWJp2o0NPWcAANFV0EAAAAA
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
BwcIAIcTNHcAJkJCAwAAAAAAAAIIAIcDNHcAAAAAAAIIAIcDNHeAAQAAFAACAA8AAAAA+wAAAPsA
AAEUAAAAADZQ8uMACKhI////////ACCvOZcwCABFAADt5wAAACARBB6Bb6wDgW///wCKAIoA2Y+N
EQIATYFvrAMAigDDAAAgRkRFRUZBRkNFQkVDRUlGRkNBQ0FDQUNBQ0FDQUNBQUEAIEVFRUZGQUZF
Q0FFUEVHQ0FFREVCRkNFRUNBQ0FDQUJOAP9TTUIlAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
EQAAKQAAAAAAAAAAAAAAAAAAAAAAAAApAFYAAwABAAEAAgA6AFxNQUlMU0xPVFxCUk9XU0UAAUOg
uw0AU0RQUkFCSFUAAAAAAAAAAAQAAyBBABUEVapTRFBSQUJIVQAAAAAAPAAAADwAAABUAAAAADZQ
8uMACLNU////////AAAyJQ//CAYAAQgABgQAAQAAMiUP/4FvqEMAAAAAAACBb6wDRQAAzDscAAB+
EQAAgW+ZCf//AAAA+gAAAPoAAAEUAAAAADZQ8uMACNlP////////ACCv1f40CABFAADsy2wAACAR
vleBbw1fgW///wCKAIoA2DC2EQIE+YFvDV8AigDCAAAgRUdGQ0VGRUZFTkVCRU9DQUNBQ0FDQUNB
Q0FDQUNBQUEAIEVFRUZGQUZFQ0FFUEVHQ0FFREVCRkNFRUNBQ0FDQUJOAP9TTUIlAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAEQAAKAAAAAAAAAAAAAAAAAAAAAAAAAAoAFYAAwABAAEAAgA5AFxN
QUlMU0xPVFxCUk9XU0UAAfaguw0ARlJFRU1BTgAAAAAAAAAAAAQAAyBBABUEVapwZW50aXVtAGl1
AAAAPAAAADwAAABUAAAAADZQ8uMACORY////////AAAyJQ//CAYAAQgABgQAAQAAMiUP/4FvqEMA
AAAAAACBbw1fRQAAzDscAAB+EQAAgW+ZCf//AAAA/AAAAPwAAAEUAAAAADZQ8uMACYjI////////
AKDJH1qBCABFAADuJAMAACARxxWBb6wIgW///wCKAIoA2qgYEQIAXoFvrAgAigDEAAAgRU5FUEVQ
RUVGSkNBQ0FDQUNBQ0FDQUNBQ0FDQUNBQUEAIEVFRUZGQUZFQ0FFUEVHQ0FFREVCRkNFRUNBQ0FD
QUJOAP9TTUIlAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAEQAAKgAAAAAAAAAAAAAAAAAAAAAA
AAAqAFYAAwABAAEAAgA7AFxNQUlMU0xPVFxCUk9XU0UAAVGguw0ATU9PRFkAAAAAAAAAAAAAAAQA
AyJBABUEVapqIG0gbW9vZHkAAAAAPAAAADwAAABUAAAAADZQ8uMACZPW////////AAAyJQ//CAYA
AQgABgQAAQAAMiUP/4FvqEMAAAAAAACBb6wIRQAAzDscAAB+EQAAgW+ZCf//AAAATgAAAE4AAABo
AAAAADZQ8uMAChHTCQAHAACICACHGr5oAECqqgMIAAeAmwA4AAAAAAA///0CAgIhTgA2ZP4AD1NV
UkdFUlktUExBU1RJQwtMYXNlcldyaXRlcgdTVVJHRVJZAE4AAABOAAAATgAAAGgAAAAANlDy4wAK
N4kJAAcAAIgIAIcavmgAQKqqAwgAB4CbADgAAAAAAD///QICAiFPADZk/gAPU1VSR0VSWS1DQVJE
SUFDC0xhc2VyV3JpdGVyB1NVUkdFUlkATgAAAE4AAABOAAAAaAAAAAA2UPLjAApcJQkABwAAiAgA
hxq+aABAqqoDCAAHgJsAOAAAAAAAP//9AgICIVAANmT+AA9TVVJHRVJZLUFETUlOIDELTGFzZXJX
cml0ZXIHU1VSR0VSWQBOAAAAXAAAAFwAAAB0AAAAADZQ8uMACr2A////////AGCXCO7wCABFAABO
TGQAAIARNUCBb7YcgW///wCJAIkAOvi4pTQBEAABAAAAAAAAIEVGRkFFSkVFRUZFTkVKRVBFTUVQ
RUhGSkNBQ0FDQUJMAAAgAAEAAABcAAAAXAAAAHQAAAAANlDy4wAK4Qr///////8AIEgE/YwIAEUA
AE4CbAAAgBFIC4Fv7UmBb///AIkAiQA6eqPdFgEQAAEAAAAAAAAgRU5FRkVFRUpFREVKRU9FRkZQ
RUpFT0VHRUZFREZFQkwAACAAAQAAAFwAAABcAAAAdAAAAAA2UPLjAArukf///////wAQWh8WzggA
RQAATjm/AACAEUc6gW+2x4Fv//8AiQCJADoHKLkKARAAAQAAAAAAACBFS0ZERkFFT0ZDRU5GQUZF
RUhGREVDRkRGREVFRUpGQwAAIAABAAAAMwAAADMAAABMAAAAADZQ8uMAC22i////////CAARCFdl
ACXg4AP//wAiAAQAAAAC////////BFIAAAACCAARCFdlRZEAAwAEUgAAADAAAAAwAAAASAAAAAA2
UPLjAAtuYP///////wgAEQhXZQAi//8AIgAEEwAAAf///////wRSEwAAAQgAEQhXZUWRAAMABAAA
ADwAAAA8AAAAVAAAAAA2UPLjAAtvA////////wgAEQhXZYE3//8AIgAEAAAAAP///////wRSAAAA
AAgAEQhXZUWRAAMABAMABFIAAgU1VEVLMAAAADgAAAA4AAAAUAAAAAA2UPLjAAtvrf///////wgA
EQhXZQAqqqoDAAAAgTf//wAiAAQAAAAA////////BFIAAAAACAARCFdlRZEAAwAEAAAARwAAAEcA
AABgAAAAADZQ8uMAC/rQCQAHAADlCACHKiZBADmqqgMIAAeAmwAxAAAAAABR/z4CAgIhxAAfpP0A
AT0MU3Rhck5pbmUgS2V5DUlCVCAzcmQgZmxvb3IAAAAAWQAAAFkAAAB0AAAAADZQ8uMADCElCQAH
AADjCACHKiZBAEuqqgMIAAeAmwBDAAAAAABR/z4CAgIhowAuy/0ADEREUyBDYWxlbmRlcg5OVUQg
Mi4wIFNlcnZlchJERU5UQUwgRElBR05PU1RJQ1MASUMAAAD4AAAA+AAAARAAAAAANlDy4wAMQhv/
//////8AgK24bvEIAEUAAOqG/AAAgBGgvYFvD2uBb///AIoAigDWbykRAgd+gW8PawCKAMAAACBF
SEVCRkNFREVKRUJDQUNBQ0FDQUNBQ0FDQUNBQ0FBQQAgRUVFRkZBRkVDQUVQRUdDQUVERUJGQ0VF
Q0FDQUNBQk4A/1NNQiUAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAARAAAmAAAAAAAAAAAAAAAA
AAAAAAAAACYAVgADAAEAAQACADcAXE1BSUxTTE9UXEJST1dTRQABr6C7DQBHQVJDSUEAAAAAAAAA
AAAABAADIkEAFQRVqlVTRVIxAAAAAEwAAABMAAAAZAAAAAA2UPLjAA0VkQkABwAAfAgAhxM1BAA+
qqoDCAAHgJsANgAAAAAAUf/gAgICIc0ATCb9AAgxMjYzMjc2MwxTdGFyTmluZSBLZXkLUGxleHVz
IE1haW4AAABMAAAATAAAAGQAAAAANlDy4wANMZgJAAcAAHwIAIcTNQQAPqqqAwgAB4CbADYAAAAA
AFH/4AICAiHMAEwm/QAIMTI1ODQ3NDEMU3Rhck5pbmUgS2V5C1BsZXh1cyBNYWluAAAAgAAAAIAA
AACYAAAAADZQ8uMADWAQqwAEAQEBqgAEAAdEYAdwAKsABAEBAQEAqgAEAAdEoAAIAACABAEAAAZC
SUxCTyAAgAH/gwAEAAAAAAAAAAAAEAMAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAIQFC5VL
PDT1nAADRVdBAAAAAAAAAAAAAAAAAAD4A2V/TQEAAADYAAAA2AAAAPAAAAAANlDy4wAOlPP/////
//8AYJcI7vAIAEUAAMpOZAAAgBEyxIFvthyBb///AIoAigC2QGMRGqVAgW+2HACKAKAAACBFSUVG
RkNFQ0VQRU1FRUREQ0FDQUNBQ0FDQUNBQ0FBQQAgRkRGQUVJRkRGRUVCRUdFR0NBQ0FDQUNBQ0FD
QUNBQk4A/1NNQiUAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAARAAAGAAAAAAAAAAAA6AMAAAAA
AAAAAAYAVgADAAEAAQACABcAXE1BSUxTTE9UXEJST1dTRQAJBDkDAAAAAACmAAAApgAAAMAAAAAA
NlDy4wAOt7kABikhIrsIACCSbaEIAEUQAJjA7EAA/wauk4FvBSmBbwPIABYFsYQKs445x+mtgBgn
mEFQAAABAQgKArWK9jawHUUAAABaVN6L2lMh6zY8OuUOfQ6CmZeR8mMPbU9T0GhpcPxZHN7bzege
o4KJEF/4clymm1N6SxJCQKb3LHmeqmUMZTZMjQmOprFqgn3fCus6qHpO53pafpuWWYmmhMvMcS5Y
/aO9DmMAAABCAAAAQgAAAFwAAAAANlDy4wAPIUQIACCSbaEABikhIrsIAEUAADQVUQAAPAZdpIFv
A8iBbwUpBbEAFjnH6a2ECrPygBA+OOnZAAABAQgKNrAdRwK1ivYCtQAAAIAAAACAAAAAmAAAAAA2
UPLkAAD8MqsABAEBAaoABAAVRGAHcACrAAQBAQEBAKoABAAVRKAACAAAgAQBAAAGQVJXRU4gAIAB
/4MABAAAAAAAAAAAABADAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACEBW/yaz409ZwAA0VX
QQAAAAAAAAAAAAAAAAgAK+YOZzcBAAAAkgAAAJIAAACsAAAAADZQ8uQAAUBk////////AKDJ8l4d
CABFAACENGsAAEARMdWBbxFLgW///wXlAG8AcJZoNldUegAAAAAAAAACAAGGoAAAAAIAAAAFAAAA
AQAAACA2UPPOAAAAC2hhbnNlbi1sYWIzAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAGGpAAAAAIAAAAC
AAAAEAAAAAxiaW9jaGVtaXN0cnkAAAAAAEsAAABLAAAAZAAAAAA2UPLkAAFxsAkAB////wgAhxq+
aQA9qqoDCAAHgJsANQAAAAAAUf9OAQEBAFEITgAKgABjggAFgQAFggAGgQAGggAHgQAHgg+rgA+r
ggAKgABjggAAAABeAAAAXgAAAHgAAAAANlDy5AACM9f///////8AIK85l/wAUP//AFAABAAAAAD/
//////8EVRMAAAEAIK85l/wEVRABJwBNAAQAIwAAACMAAwAGAEVQSURFTUlPTE9HWSAgAAEBAl9f
TVNCUk9XU0VfXwIBAF4AAAA8AAAAPAAAAFQAAAAANlDy5AACeZn///////8AEFoKQzkIBgABCAAG
BAABABBaCkM5gW+yEQAAAAAAAIFv9ikAAAAAAAAAAAAAAAAAAAAAAAAAAABiAAAAYgAAAHwAAAAA
NlDy5AACqXUIACstuI6qAAQAAkSAQVQABgAAAAgAK+KGTAAAAAADAQMDAQZaSU5HRVIAAAAAAAAA
AAAAAAAAAAAAAAA1EAAAAP9TTUIlAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAEQAAAAAAPAAA
ADwAAABUAAAAADZQ8uQAAwdI////////ABBaCkM5CAYAAQgABgQAAQAQWgpDOYFvshEAAAAAAACB
b/Y6AAAAAAAAAAAAAAAAAAAAAAAAAAAANAAAADQAAABMAAAAADZQ8uQAAybOAYDCAAAAAGA+yU87
ACZCQgMAAAAAAAABAOCjPsEAAAAAAAABAOCjPsEAgUQAABQAAgAPAAAAADwAAAA8AAAAVAAAAAA2
UPLkAAOMyv///////wAQWgpDOQgGAAEIAAYEAAEAEFoKQzmBb7IRAAAAAAAAgW/2OQAAAAAAAAAA
AAAAAAAAAAAAAAAAAGAAAABgAAAAeAAAAAA2UPLkAAS4RAkABwAAigBgcMxbiQBSqqoDCAAHgJsA
SjnbAAAPrf/bAv0CIXoPrdv9ABVSSUMgQ2FsZW5kYXIgU2VydmVyIDMOTlVEIDIuMCBTZXJ2ZXIQ
UkVTRUFSQ0ggSU1BR0lORwAAADIAAAAyAAAATAAAAAA2UPLkAAT6fwkAB////wAFAoYeAQAkqqoD
AAAAgPMAAYCbBgQAAQAFAoYeAQAAEdUAAAAAAAAAAEUDAAAAAACSAAAAkgAAAKwAAAAANlDy5AAF
v+D///////8AoMnyXh0IAEUAAIQ0bwAAQBEx0YFvEUuBb///BeYAbwBwGds2XNEBAAAAAAAAAAIA
AYagAAAAAgAAAAUAAAABAAAAIDZQ884AAAALaGFuc2VuLWxhYjMAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAYakAAAAAgAAAAIAAAAQAAAADGJpb2NoZW1pc3RyeQAAAAAAPAAAADwAAABUAAAAADZQ8uQA
BhyD////////AGAIKz/qCAYAAQgABgQAAQBgCCs/6oFv3SEAAAAAAACBbwENAQ0BDQENAQ0BDQEN
AQ0BDQENAAAAXAAAAFwAAAB0AAAAADZQ8uQABvEa////////AGCXCO7wCABFAABOUWQAAIARMECB
b7YcgW///wCJAIkAOvi4pTQBEAABAAAAAAAAIEVGRkFFSkVFRUZFTkVKRVBFTUVQRUhGSkNBQ0FD
QUJMAAAgAAEAAACAAAAAgAAAAJgAAAAANlDy5AAG/cirAAQBAQGqAAQADERgB3AAqwAEAQEBAQCq
AAQADESgAAgAAIAEAQAABkJBTElOIACAAf+DAAQAAAAAAAAAAAAfAwAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAhAWAWu83NPWcAANFWEEAAAAAAAAAAAAAAAAIACsvrPwkAAAAAFwAAABcAAAA
dAAAAAA2UPLkAAcQWP///////wAgSAT9jAgARQAATgRsAACAEUYLgW/tSYFv//8AiQCJADp6o90W
ARAAAQAAAAAAACBFTkVGRUVFSkVERUpFT0VGRlBFSkVPRUdFRkVERkVCTAAAIAABAAAAXAAAAFwA
AAB0AAAAADZQ8uQABx3O////////ABBaHxbOCABFAABOPr8AAIARQjqBb7bHgW///wCJAIkAOgco
uQoBEAABAAAAAAAAIEVLRkRGQUVPRkNFTkZBRkVFSEZERUNGREZERUVFSkZDAAAgAAEAAABHAAAA
RwAAAGAAAAAANlDy5AAH/vgDAAAAAAEAoMkWnhQAOfDwAywA/+8IAAAAAAAAAEpTUE5STVBUR1NC
U1NESVJGQU1QMzMgICAgICAgICAGAKDJFp4U+HcAAAAAAABZAAAAWQAAAHQAAAAANlDy5AAIcsgJ
AAcAAOMIAIcqJkEAS6qqAwgAB4CbAEMAAAAAAFH/PgICAiGjAC7L/QAMRERTIENhbGVuZGVyDk5V
RCAyLjAgU2VydmVyEkRFTlRBTCBESUFHTk9TVElDUwBJQwAAADwAAAA8AAAAVAAAAAA2UPLkAAir
A6sAAAMAAKoABAAMRGADKQALAgAAqgAEAAxEAtoFQAAPAAAWAAAAAAAAAA6qAAQAykTAqgAEAAtE
wAACAAAAAEcAAABHAAAAYAAAAAA2UPLkAAlKwgkABwAA5QgAhyomQQA5qqoDCAAHgJsAMQAAAAAA
Uf8+AgICIcQAH6T9AAE9DFN0YXJOaW5lIEtleQ1JQlQgM3JkIGZsb29yAAAAADwAAAA8AAAAVAAA
AAA2UPLkAAnL/AkABwAAKwgAhxq+aQAuqqoDCAAHgJsAJgAAAAAAUf9OAgICIfUPq43+AAE9A05S
TAtQQVRIT0xPR1kvRQAAAEwAAABMAAAAZAAAAAA2UPLkAAoyCgkABwAAfAgAhxM1BAA+qqoDCAAH
gJsANgAAAAAAUf/gAgICIc0ATCb9AAgxMjYzMjc2MwxTdGFyTmluZSBLZXkLUGxleHVzIE1haW4A
AABMAAAATAAAAGQAAAAANlDy5AAKTs0JAAcAAHwIAIcTNQQAPqqqAwgAB4CbADYAAAAAAFH/4AIC
AiHMAEwm/QAIMTI1ODQ3NDEMU3Rhck5pbmUgS2V5C1BsZXh1cyBNYWluAAAAbgAAAG4AAACIAAAA
ADZQ8uQAC4Dz////////AKDJJFTBAGD//wBgAAQTAAAB////////BFITAAABAKDJJFTBQAgAAgZA
Uk9PTS01MThGAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAEwAAAQCgySRU
weiFAAEAbgAAAFwAAABcAAAAdAAAAAA2UPLkAAwY7P///////wCgydHDtwgARQAATo9YAACAEZzi
gW8LhoFv//8AiQCJADp/zeumARAAAQAAAAAAACBFS0ZERkFFT0ZDRU5GQUZFRUhGREVDRkRGREVF
RUpGQwAAIAABAAAAcgAAAHIAAACMAAAAADZQ8uQADXsU////////CAAHpMrmAGTg4AP//wBgAAQA
AAAC////////BFIAAAACCAAHpMrmBFIAAgYYQVBQTEVfTFdhNGNhZTYAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAggAB6TK5kALAAExCwAAAABeAAAAXgAAAHgAAAAANlDy5AAO
Kf3///////8AIK85l/wAUP//AFAAFAAAAAD///////8EVRMAAAEAIK85l/wEVRABJwBNAAQAIwAA
ACMAAwAGAEVQSURFTUlPTE9HWSAgAAEBAl9fTVNCUk9XU0VfXwIBAF4AAABiAAAAYgAAAHwAAAAA
NlDy5AAOK7L///////8AYJcFDTEAU+DgA///AFABFAAAAAL///////8EVRMAAAEAIK85l/wEVRMA
AAFNAAQAIwAAACMAAwAGAEVQSURFTUlPTE9HWSAgAAEBAl9fTVNCUk9XU0VfXwIBAF8CAAAAXAAA
AFwAAAB0AAAAADZQ8uQADpT6////////AGCXCO7wCABFAABOUmQAAIARL0CBb7YcgW///wCJAIkA
OviypToBEAABAAAAAAAAIEVGRkFFSkVFRUZFTkVKRVBFTUVQRUhGSkNBQ0FDQUJMAAAgAAEAAACW
AAAAlgAAALAAAAAANlDy5AAO3wcABikhIrsIACCSbaEIAEUQAIjA7UAA/wauooFvBSmBbwPIABYF
sYQKs/I5x+mtgBgnmKJyAAABAQgKArWLWzawHUcAAABPOEzZZJBozNsJfDQLrXqLzXutMrAVQ2FL
4I8x/xOEGqTMdFGaKi4COI2HOeGDBLNW1T4Pljc++HiOJaPpczg0W9koIasEv+QrnPgLxKpmpERa
fgAAAPMAAADzAAABDAAAAAA2UPLkAA70Pv///////wAQSy6rkggARQAA5fxVAACAES1fgW8NdYFv
//8AigCKANHk7xEagJKBbw11AIoAuwAAIEZBRURFTkZEREJERUVPRkVDQUNBQ0FDQUNBQ0FDQUNB
ACBFTUVKRUNGQ0VCRkNGSkNBQ0FDQUNBQ0FDQUNBQ0FCTgD/U01CJQAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAABEAACEAAAAAAAAAAADoAwAAAAAAAAAAIQBWAAMAAQAAAAIAMgBcTUFJTFNMT1Rc
QlJPV1NFAAEAgPwKAFBDTVMxNE5UAAAAAAAAAAAEAAMQAQAPAVWqAAAAAAA5AAAAOQAAAFQAAAAA
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
AAAAAAAAgW8NjA2MDYwNjA2MDYwNjA2MDYwNjAAAADkAAAA5AAAAVAAAAAA2UPLlAAmtTQkAB///
/wgAhxM1BQArqqoDCAAHgJsAIwAAAAAAUf/xAQEBAFEI8QAKgABjggAKgABjgg+hgA+hgm5ppgAA
AFwAAABcAAAAdAAAAAA2UPLlAArIff///////wBglwju8AgARQAATlZkAACAEStAgW+2HIFv//8A
iQCJADr4sqU6ARAAAQAAAAAAACBFRkZBRUpFRUVGRU5FSkVQRU1FUEVIRkpDQUNBQ0FCTAAAIAAB
AAAAXAAAAFwAAAB0AAAAADZQ8uUACs9o////////AKDJnSgjCABFAABO4IAAAIARS9aBbwtqgW//
/wCJAIkAOqTKz9wBEAABAAAAAAAAIEVORkpFREVQRlBFTUVCRUNDQUNBQ0FDQUNBQ0FDQUNBAAAg
AAEAAAA8AAAAPAAAAFQAAAAANlDy5QAK1WH///////8AYAgYb4kIBgABCAAGBAABAGAIGG+JgW+g
BAAAAAAAAIFvC2oLagtqC2oLagtqC2oLagtqC2oAAABcAAAAXAAAAHQAAAAANlDy5QAK4Nr/////
//8AIEgE/YwIAEUAAE4GbAAAgBFEC4Fv7UmBb///AIkAiQA6d5/dGgEQAAEAAAAAAAAgRU5FRkVF
RUpFREVKRU9FRkZQRUpFT0VHRUZFREZFQk8AACAAAQAAAOEAAADhAAAA/AAAAAA2UPLlAArnMv//
/////wAgSAT9jAgARQAA0wdsAACAEUKGgW/tSYFv//8AigCKAL+G9REa3RiBb+1JAIoAqQAAIEVC
RkdFRkVPRUhFRkZDQ0FDQUNBQ0FDQUNBQ0FDQUFBACBFTkVGRUVFSkVERUpFT0VGRlBFSkVPRUdF
RkVERkVCTwD/U01CJQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABEAAA8AAAAAAAAAAADoAwAA
AAAAAAAADwBWAAMAAQABAAIAIABcTUFJTFNMT1RcQlJPV1NFAAgAAAAAAAAAAAAAAAAAAAAAAAAA
ADwAAAA8AAAAVAAAAAA2UPLlAArr9v///////wAQWgqTbwgGAAEIAAYEAAEAEFoKk2+BbxD2AAAA
AAAAgW/tSQAAAAAAAAAAAAAAAAAAAAAAAAAAADwAAAA8AAAAVAAAAAA2UPLlAArsQf///////wAQ
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
""".decode("base64")

########NEW FILE########
__FILENAME__ = test_container
import unittest

from construct.lib.container import Container, ListContainer

class TestContainer(unittest.TestCase):

    def test_getattr(self):
        c = Container(a=1)
        self.assertEqual(c["a"], c.a)

    def test_setattr(self):
        c = Container()
        c.a = 1
        self.assertEqual(c["a"], 1)

    def test_delattr(self):
        c = Container(a=1)
        del c.a
        self.assertFalse("a" in c)

    def test_update(self):
        c = Container(a=1)
        d = Container()
        d.update(c)
        self.assertEqual(d.a, 1)

    def test_eq_eq(self):
        c = Container(a=1)
        d = Container(a=1)
        self.assertEqual(c, d)

    def test_ne_wrong_type(self):
        c = Container(a=1)
        d = {"a": 1}
        self.assertNotEqual(c, d)

    def test_ne_wrong_key(self):
        c = Container(a=1)
        d = Container(b=1)
        self.assertNotEqual(c, d)

    def test_ne_wrong_value(self):
        c = Container(a=1)
        d = Container(a=2)
        self.assertNotEqual(c, d)

    def test_copy(self):
        c = Container(a=1)
        d = c.copy()
        self.assertEqual(c, d)
        self.assertTrue(c is not d)

    def test_copy_module(self):
        from copy import copy

        c = Container(a=1)
        d = copy(c)
        self.assertEqual(c, d)
        self.assertTrue(c is not d)

    def test_bool_false(self):
        c = Container()
        self.assertFalse(c)

    def test_bool_true(self):
        c = Container(a=1)
        self.assertTrue(c)

    def test_in(self):
        c = Container(a=1)
        self.assertTrue("a" in c)

    def test_not_in(self):
        c = Container()
        self.assertTrue("a" not in c)

    def test_repr(self):
        c = Container(a=1, b=2)
        repr(c)

    def test_repr_recursive(self):
        c = Container(a=1, b=2)
        c.c = c
        repr(c)

    def test_str(self):
        c = Container(a=1, b=2)
        str(c)

    def test_str_recursive(self):
        c = Container(a=1, b=2)
        c.c = c
        str(c)

class TestListContainer(unittest.TestCase):

    def test_str(self):
        l = ListContainer(range(5))
        str(l)

########NEW FILE########
__FILENAME__ = t1
from construct import *


s = Aligned(
    Struct('test',
        Byte('length'),
        Array(lambda ctx: ctx.length, Byte('x')),
    )
)
print Debugger(s).parse("\x03aaab")



########NEW FILE########
__FILENAME__ = testall

import os
from subprocess import call


basepath = os.path.abspath("..")

def scan(path, failures):
    if os.path.isdir(path):
        for subpath in os.listdir(path):
            scan(os.path.join(path, subpath), failures)
    elif os.path.isfile(path) and path.endswith(".py"):
        dirname, name = os.path.split(path)
        os.chdir(dirname)
        errorcode = call("python %s > %s 2> %s" % (name, os.devnull, os.devnull), shell=True)
        if errorcode != 0:
            failures.append((path, errorcode))

failures = []
print "testing packages"

scan(os.path.join(basepath, "formats"), failures)
scan(os.path.join(basepath, "protocols"), failures)

if not failures:
    print "success"
else:
    print "%d errors:" % (len(failures),)
    for fn, ec in failures:
        print "     %s" % (fn,)



########NEW FILE########
__FILENAME__ = test_adaptors
import unittest

from construct import Field, UBInt8
from construct import OneOf, NoneOf, HexDumpAdapter
from construct import ValidationError

class TestHexDumpAdapter(unittest.TestCase):

    def setUp(self):
        self.hda = HexDumpAdapter(Field("hexdumpadapter", 6))

    def test_trivial(self):
        pass

    def test_parse(self):
        self.assertEqual(self.hda.parse("abcdef"), "abcdef")

    def test_build(self):
        self.assertEqual(self.hda.build("abcdef"), "abcdef")

    def test_str(self):
        pretty = str(self.hda.parse("abcdef")).strip()
        offset, digits, ascii = [i.strip() for i in pretty.split("  ") if i]
        self.assertEqual(offset, "0000")
        self.assertEqual(digits, "61 62 63 64 65 66")
        self.assertEqual(ascii, "abcdef")

class TestNoneOf(unittest.TestCase):

    def setUp(self):
        self.n = NoneOf(UBInt8("foo"), [4, 5, 6, 7])

    def test_trivial(self):
        pass

    def test_parse(self):
        self.assertEqual(self.n.parse("\x08"), 8)

    def test_parse_invalid(self):
        self.assertRaises(ValidationError, self.n.parse, "\x06")

class TestOneOf(unittest.TestCase):

    def setUp(self):
        self.o = OneOf(UBInt8("foo"), [4, 5, 6, 7])

    def test_trivial(self):
        pass

    def test_parse(self):
        self.assertEqual(self.o.parse("\x05"), 5)

    def test_parse_invalid(self):
        self.assertRaises(ValidationError, self.o.parse, "\x08")

    def test_build(self):
        self.assertEqual(self.o.build(5), "\x05")

    def test_build_invalid(self):
        self.assertRaises(ValidationError, self.o.build, 9)

########NEW FILE########
__FILENAME__ = test_ast
import unittest

from construct import *
from construct.text import *

class NodeAdapter(Adapter):
    def __init__(self, factory, subcon):
        Adapter.__init__(self, subcon)
        self.factory = factory
    def _decode(self, obj, context):
        return self.factory(obj)


#===============================================================================
# AST nodes
#===============================================================================
class Node(Container):
    def __init__(self, name, **kw):
        Container.__init__(self)
        self.name = name
        for k, v in kw.iteritems():
            setattr(self, k, v)
    
    def accept(self, visitor):
        return getattr(visitor, "visit_%s" % self.name)(self)

def binop_node(obj):
    lhs, rhs = obj
    if rhs is None:
        return lhs
    else:
        op, rhs = rhs
        return Node("binop", lhs=lhs, op=op, rhs=rhs)

def literal_node(value):
    return Node("literal", value = value)


#===============================================================================
# concrete grammar
#===============================================================================
ws = Whitespace()
term = IndexingAdapter(
    Sequence("term",
        ws, 
        Select("term", 
            NodeAdapter(literal_node, DecNumber("number")), 
            IndexingAdapter(
                Sequence("subexpr", 
                    Literal("("), 
                    LazyBound("expr", lambda: expr), 
                    Literal(")")
                ),
                index = 0
            ),
        ),
        ws,
    ),
    index = 0
)

def OptSeq(name, *args):
    return Optional(Sequence(name, *args))

expr1 = NodeAdapter(binop_node, 
    Sequence("expr1", 
        term,
        OptSeq("rhs",
            CharOf("op", "*/"), 
            LazyBound("rhs", lambda: expr1)
        ),
    )
)

expr2 = NodeAdapter(binop_node, 
    Sequence("expr2", 
        expr1, 
        OptSeq("rhs",
            CharOf("op", "+-"), 
            LazyBound("rhs", lambda: expr2)
        ),
    )
)

expr = expr2


#===============================================================================
# evaluation visitor
#===============================================================================
class EvalVisitor(object):
    def visit_literal(self, obj):
        return obj.value
    def visit_binop(self, obj):
        lhs = obj.lhs.accept(self)
        op = obj.op
        rhs = obj.rhs.accept(self)
        if op == "+":
            return lhs + rhs
        elif op == "-":
            return lhs - rhs
        elif op == "*":
            return lhs * rhs
        elif op == "/":
            return lhs / rhs
        else:
            raise ValueError("invalid op", op)

ev = EvalVisitor()

class TestSomethingSomething(unittest.TestCase):

    def test_that_one_thing(self):
        node = expr.parse("2*3+4")
        self.assertEqual(node.name, "binop")
        self.assertEqual(node.op, "+")
        self.assertEqual(node.rhs.name, "literal")
        self.assertEqual(node.rhs.value, 4)
        self.assertEqual(node.lhs.name, "binop")
        self.assertEqual(node.lhs.op, "*")
        self.assertEqual(node.lhs.rhs.name, "literal")
        self.assertEqual(node.lhs.rhs.value, 3)
        self.assertEqual(node.lhs.lhs.name, "literal")
        self.assertEqual(node.lhs.lhs.value, 2)

    def test_that_other_thing(self):
        node = expr.parse("2*(3+4)")
        self.assertEqual(node.name, "binop")
        self.assertEqual(node.op, "*")
        self.assertEqual(node.rhs.name, "binop")
        self.assertEqual(node.rhs.op, "+")
        self.assertEqual(node.rhs.rhs.name, "literal")
        self.assertEqual(node.rhs.rhs.value, 4)
        self.assertEqual(node.rhs.lhs.name, "literal")
        self.assertEqual(node.rhs.lhs.value, 3)
        self.assertEqual(node.lhs.name, "literal")
        self.assertEqual(node.lhs.value, 2)

########NEW FILE########
__FILENAME__ = test_bit
import unittest

from construct import BitField, BitStruct, Struct, Container
from construct import Bit, Flag, Nibble, Padding

class TestBitStruct(unittest.TestCase):

    def test_parse(self):
        struct = BitStruct("foo",
            BitField("a", 3),
            Flag("b"),
            Padding(3),
            Nibble("c"),
            BitField("d", 5),
        )
        self.assertEqual(struct.parse("\xe1\x1f"),
            Container(a=7, b=False, c=8, d=31))

    def test_parse_nested(self):
        struct = BitStruct("foo",
            BitField("a", 3),
            Flag("b"),
            Padding(3),
            Nibble("c"),
            Struct("bar",
                Nibble("d"),
                Bit("e"),
            )
        )
        self.assertEqual(struct.parse("\xe1\x1f"),
            Container(a=7, b=False, bar=Container(d=15, e=1), c=8))

########NEW FILE########
__FILENAME__ = test_core
import unittest

from construct import Struct, MetaField, StaticField, FormatField
from construct import Container, Byte
from construct import FieldError, SizeofError

class TestStaticField(unittest.TestCase):

    def setUp(self):
        self.sf = StaticField("staticfield", 2)

    def test_trivial(self):
        pass

    def test_parse(self):
        self.assertEqual(self.sf.parse("ab"), "ab")

    def test_build(self):
        self.assertEqual(self.sf.build("ab"), "ab")

    def test_parse_too_short(self):
        self.assertRaises(FieldError, self.sf.parse, "a")

    def test_build_too_short(self):
        self.assertRaises(FieldError, self.sf.build, "a")

    def test_sizeof(self):
        self.assertEqual(self.sf.sizeof(), 2)

class TestFormatField(unittest.TestCase):

    def setUp(self):
        self.ff = FormatField("formatfield", "<", "L")

    def test_trivial(self):
        pass

    def test_parse(self):
        self.assertEqual(self.ff.parse("\x12\x34\x56\x78"), 0x78563412)

    def test_build(self):
        self.assertEqual(self.ff.build(0x78563412), "\x12\x34\x56\x78")

    def test_parse_too_short(self):
        self.assertRaises(FieldError, self.ff.parse, "\x12\x34\x56")

    def test_build_too_long(self):
        self.assertRaises(FieldError, self.ff.build, 9e9999)

    def test_sizeof(self):
        self.assertEqual(self.ff.sizeof(), 4)

class TestMetaField(unittest.TestCase):

    def setUp(self):
        self.mf = MetaField("metafield", lambda context: 3)

    def test_trivial(self):
        pass

    def test_parse(self):
        self.assertEqual(self.mf.parse("abc"), "abc")

    def test_build(self):
        self.assertEqual(self.mf.build("abc"), "abc")

    def test_parse_too_short(self):
        self.assertRaises(FieldError, self.mf.parse, "ab")

    def test_build_too_short(self):
        self.assertRaises(FieldError, self.mf.build, "ab")

    def test_sizeof(self):
        self.assertEqual(self.mf.sizeof(), 3)

class TestMetaFieldStruct(unittest.TestCase):

    def setUp(self):
        self.mf = MetaField("data", lambda context: context["length"])
        self.s = Struct("foo", Byte("length"), self.mf)

    def test_trivial(self):
        pass

    def test_parse(self):
        c = self.s.parse("\x03ABC")
        self.assertEqual(c.length, 3)
        self.assertEqual(c.data, "ABC")

        c = self.s.parse("\x04ABCD")
        self.assertEqual(c.length, 4)
        self.assertEqual(c.data, "ABCD")

    def test_sizeof_default(self):
        self.assertRaises(SizeofError, self.mf.sizeof)

    def test_sizeof(self):
        context = Container(length=4)
        self.assertEqual(self.mf.sizeof(context), 4)

########NEW FILE########
__FILENAME__ = test_lib
import unittest

from construct.lib.binary import (int_to_bin, bin_to_int, swap_bytes,
    encode_bin, decode_bin)

class TestBinary(unittest.TestCase):
    pass

    def test_int_to_bin(self):
        self.assertEqual(int_to_bin(19, 5), "\x01\x00\x00\x01\x01")

    def test_int_to_bin_signed(self):
        self.assertEqual(int_to_bin(-13, 5), "\x01\x00\x00\x01\x01")

    def test_bin_to_int(self):
        self.assertEqual(bin_to_int("\x01\x00\x00\x01\x01"), 19)

    def test_bin_to_int_signed(self):
        self.assertEqual(bin_to_int("\x01\x00\x00\x01\x01", True), -13)

    def test_swap_bytes(self):
        self.assertEqual(swap_bytes("aaaabbbbcccc", 4), "ccccbbbbaaaa")

    def test_encode_bin(self):
        self.assertEqual(encode_bin("ab"),
            "\x00\x01\x01\x00\x00\x00\x00\x01\x00\x01\x01\x00\x00\x00\x01\x00")

    def test_decode_bin(self):
        self.assertEqual(decode_bin(
            "\x00\x01\x01\x00\x00\x00\x00\x01\x00\x01\x01\x00\x00\x00\x01\x00"),
            "ab")

    def test_decode_bin_length(self):
        self.assertRaises(ValueError, decode_bin, "\x00")

########NEW FILE########
__FILENAME__ = test_mapping
import unittest

from construct import Flag

class TestFlag(unittest.TestCase):

    def test_parse(self):
        flag = Flag("flag")
        self.assertTrue(flag.parse("\x01"))

    def test_parse_flipped(self):
        flag = Flag("flag", truth=0, falsehood=1)
        self.assertFalse(flag.parse("\x01"))

    def test_parse_default(self):
        flag = Flag("flag")
        self.assertFalse(flag.parse("\x02"))

    def test_parse_default_true(self):
        flag = Flag("flag", default=True)
        self.assertTrue(flag.parse("\x02"))

    def test_build(self):
        flag = Flag("flag")
        self.assertEqual(flag.build(True), "\x01")

    def test_build_flipped(self):
        flag = Flag("flag", truth=0, falsehood=1)
        self.assertEqual(flag.build(True), "\x00")

########NEW FILE########
__FILENAME__ = test_repeaters
import unittest

from construct import UBInt8
from construct import Repeater
from construct import StrictRepeater, GreedyRepeater, OptionalGreedyRepeater
from construct import ArrayError, RangeError

class TestRepeater(unittest.TestCase):

    def setUp(self):
        self.c = Repeater(3, 7, UBInt8("foo"))

    def test_trivial(self):
        pass

    def test_parse(self):
        self.assertEqual(self.c.parse("\x01\x02\x03"), [1, 2, 3])
        self.assertEqual(self.c.parse("\x01\x02\x03\x04\x05\x06"),
            [1, 2, 3, 4, 5, 6])
        self.assertEqual(self.c.parse("\x01\x02\x03\x04\x05\x06\x07"),
            [1, 2, 3, 4, 5, 6, 7])
        self.assertEqual(self.c.parse("\x01\x02\x03\x04\x05\x06\x07\x08\x09"),
            [1, 2, 3, 4, 5, 6, 7])

    def test_build(self):
        self.assertEqual(self.c.build([1, 2, 3, 4]), "\x01\x02\x03\x04")

    def test_build_undersized(self):
        self.assertRaises(RangeError, self.c.build, [1, 2])

    def test_build_oversized(self):
        self.assertRaises(RangeError, self.c.build, [1, 2, 3, 4, 5, 6, 7, 8])

class TestStrictRepeater(unittest.TestCase):

    def setUp(self):
        self.c = StrictRepeater(4, UBInt8("foo"))

    def test_trivial(self):
        pass

    def test_parse(self):
        self.assertEqual(self.c.parse("\x01\x02\x03\x04"), [1, 2, 3, 4])
        self.assertEqual(self.c.parse("\x01\x02\x03\x04\x05\x06"),
            [1, 2, 3, 4])

    def test_build(self):
        self.assertEqual(self.c.build([5, 6, 7, 8]), "\x05\x06\x07\x08")

    def test_build_oversized(self):
        self.assertRaises(ArrayError, self.c.build, [5, 6, 7, 8, 9])

    def test_build_undersized(self):
        self.assertRaises(ArrayError, self.c.build, [5, 6, 7])

class TestGreedyRepeater(unittest.TestCase):

    def setUp(self):
        self.c = GreedyRepeater(UBInt8("foo"))

    def test_trivial(self):
        pass

    def test_empty_parse(self):
        self.assertRaises(RangeError, self.c.parse, "")

    def test_parse(self):
        self.assertEqual(self.c.parse("\x01"), [1])
        self.assertEqual(self.c.parse("\x01\x02\x03"), [1, 2, 3])
        self.assertEqual(self.c.parse("\x01\x02\x03\x04\x05\x06"),
            [1, 2, 3, 4, 5, 6])

    def test_empty_build(self):
        self.assertRaises(RangeError, self.c.build, [])

    def test_build(self):
        self.assertEqual(self.c.build([1, 2]), "\x01\x02")

class TestOptionalGreedyRepeater(unittest.TestCase):

    def setUp(self):
        self.c = OptionalGreedyRepeater(UBInt8("foo"))

    def test_trivial(self):
        pass

    def test_empty_parse(self):
        self.assertEqual(self.c.parse(""), [])

    def test_parse(self):
        self.assertEqual(self.c.parse("\x01\x02"), [1, 2])

    def test_empty_build(self):
        self.assertEqual(self.c.build([]), "")

    def test_build(self):
        self.assertEqual(self.c.build([1, 2]), "\x01\x02")

########NEW FILE########
__FILENAME__ = test_strings
import unittest

from construct import String, PascalString, CString, UBInt16

class TestString(unittest.TestCase):

    def test_parse(self):
        s = String("foo", 5)
        self.assertEqual(s.parse("hello"), "hello")

    def test_parse_utf8(self):
        s = String("foo", 12, encoding="utf8")
        self.assertEqual(s.parse("hello joh\xd4\x83n"), u"hello joh\u0503n")

    def test_parse_padded(self):
        s = String("foo", 10, padchar="X", paddir="right")
        self.assertEqual(s.parse("helloXXXXX"), "hello")

    def test_parse_padded_left(self):
        s = String("foo", 10, padchar="X", paddir="left")
        self.assertEqual(s.parse("XXXXXhello"), "hello")

    def test_parse_padded_center(self):
        s = String("foo", 10, padchar="X", paddir="center")
        self.assertEqual(s.parse("XXhelloXXX"), "hello")

    def test_build(self):
        s = String("foo", 5)
        self.assertEqual(s.build("hello"), "hello")

    def test_build_utf8(self):
        s = String("foo", 12, encoding="utf8")
        self.assertEqual(s.build(u"hello joh\u0503n"), "hello joh\xd4\x83n")

    def test_build_padded(self):
        s = String("foo", 10, padchar="X", paddir="right")
        self.assertEqual(s.build("hello"), "helloXXXXX")

    def test_build_padded_left(self):
        s = String("foo", 10, padchar="X", paddir="left")
        self.assertEqual(s.build("hello"), "XXXXXhello")

    def test_build_padded_center(self):
        s = String("foo", 10, padchar="X", paddir="center")
        self.assertEqual(s.build("hello"), "XXhelloXXX")

class TestPascalString(unittest.TestCase):

    def test_parse(self):
        s = PascalString("foo")
        self.assertEqual(s.parse("\x05hello"), "hello")

    def test_build(self):
        s = PascalString("foo")
        self.assertEqual(s.build("hello world"), "\x0bhello world")

    def test_parse_custom_length_field(self):
        s = PascalString("foo", length_field=UBInt16("length"))
        self.assertEqual(s.parse("\x00\x05hello"), "hello")

    def test_build_custom_length_field(self):
        s = PascalString("foo", length_field=UBInt16("length"))
        self.assertEqual(s.build("hello"), "\x00\x05hello")

class TestCString(unittest.TestCase):

    def test_parse(self):
        s = CString("foo")
        self.assertEqual(s.parse("hello\x00"), "hello")

    def test_build(self):
        s = CString("foo")
        self.assertEqual(s.build("hello"), "hello\x00")

    def test_parse_terminator(self):
        s = CString("foo", terminators="XYZ")
        self.assertEqual(s.parse("helloX"), "hello")
        self.assertEqual(s.parse("helloY"), "hello")
        self.assertEqual(s.parse("helloZ"), "hello")

    def test_build_terminator(self):
        s = CString("foo", terminators="XYZ")
        self.assertEqual(s.build("hello"), "helloX")

########NEW FILE########
__FILENAME__ = test_text
import unittest

from construct.text import Whitespace
from construct import RangeError

class TestWhitespace(unittest.TestCase):

    def test_parse(self):
        self.assertEqual(Whitespace().parse(" \t\t "), None)

    def test_parse_required(self):
        self.assertRaises(RangeError, Whitespace(optional=False).parse, "X")

    def test_build(self):
        self.assertEqual(Whitespace().build(None), " ")

########NEW FILE########
__FILENAME__ = text
from construct.text import *


ws = Whitespace(" \t\r\n")

term = Select("term",
    DecNumber("dec"),
    Identifier("symbol"),
    IndexingAdapter(
        Sequence("expr",
            Literal("("),
            ws,
            LazyBound("expr", lambda: expr),
            ws,
            Literal(")"),
        ),
        0
    ),
)

expr1 = Select("expr1",
    Sequence("node", 
        term,
        ws,
        CharOf("binop", "*/"),
        ws,
        LazyBound("rhs", lambda: expr1),
    ),
    term,
)

expr2 = Select("expr2",
    Sequence("node", 
        expr1,
        ws,
        CharOf("binop", "+-"),
        ws,
        LazyBound("rhs", lambda: expr2),
    ),
    expr1,
)

expr = expr2

def eval2(node):
    if type(node) is int:
        return node
    lhs = eval2(node[0])
    op = node[1]
    rhs = eval2(node[2])
    if op == "+":
        return lhs + rhs
    elif op == "-":
        return lhs - rhs
    elif op == "*":
        return lhs * rhs
    elif op == "/":
        return lhs / rhs
    assert False

print expr.parse("(1 + 2)*3")
print eval2(expr.parse("(1 + 2)*3"))
print expr.build([[1, "+", 2], "*", 3])















########NEW FILE########
__FILENAME__ = unit
import sys
from construct import *
from construct.text import *
from construct.lib import LazyContainer


# some tests require doing bad things...
import warnings
warnings.filterwarnings("ignore", category = DeprecationWarning)


# declarative to the bitter end!
tests = [
    #
    # constructs
    #
    [MetaArray(lambda ctx: 3, UBInt8("metaarray")).parse, "\x01\x02\x03", [1,2,3], None],
    [MetaArray(lambda ctx: 3, UBInt8("metaarray")).parse, "\x01\x02", None, ArrayError],
    [MetaArray(lambda ctx: 3, UBInt8("metaarray")).build, [1,2,3], "\x01\x02\x03", None],
    [MetaArray(lambda ctx: 3, UBInt8("metaarray")).build, [1,2], None, ArrayError],
    
    [Range(3, 5, UBInt8("range")).parse, "\x01\x02\x03", [1,2,3], None],
    [Range(3, 5, UBInt8("range")).parse, "\x01\x02\x03\x04", [1,2,3,4], None],
    [Range(3, 5, UBInt8("range")).parse, "\x01\x02\x03\x04\x05", [1,2,3,4,5], None],
    [Range(3, 5, UBInt8("range")).parse, "\x01\x02", None, RangeError],
    [Range(3, 5, UBInt8("range")).build, [1,2,3], "\x01\x02\x03", None],
    [Range(3, 5, UBInt8("range")).build, [1,2,3,4], "\x01\x02\x03\x04", None],
    [Range(3, 5, UBInt8("range")).build, [1,2,3,4,5], "\x01\x02\x03\x04\x05", None],
    [Range(3, 5, UBInt8("range")).build, [1,2], None, RangeError],
    [Range(3, 5, UBInt8("range")).build, [1,2,3,4,5,6], None, RangeError],
    
    [RepeatUntil(lambda obj, ctx: obj == 9, UBInt8("repeatuntil")).parse, "\x02\x03\x09", [2,3,9], None],
    [RepeatUntil(lambda obj, ctx: obj == 9, UBInt8("repeatuntil")).parse, "\x02\x03\x08", None, ArrayError],
    [RepeatUntil(lambda obj, ctx: obj == 9, UBInt8("repeatuntil")).build, [2,3,9], "\x02\x03\x09", None],
    [RepeatUntil(lambda obj, ctx: obj == 9, UBInt8("repeatuntil")).build, [2,3,8], None, ArrayError],
    
    [Struct("struct", UBInt8("a"), UBInt16("b")).parse, "\x01\x00\x02", Container(a=1,b=2), None],
    [Struct("struct", UBInt8("a"), UBInt16("b"), Struct("foo", UBInt8("c"), UBInt8("d"))).parse, "\x01\x00\x02\x03\x04", Container(a=1,b=2,foo=Container(c=3,d=4)), None],
    [Struct("struct", UBInt8("a"), UBInt16("b"), Embedded(Struct("foo", UBInt8("c"), UBInt8("d")))).parse, "\x01\x00\x02\x03\x04", Container(a=1,b=2,c=3,d=4), None],
    [Struct("struct", UBInt8("a"), UBInt16("b")).build, Container(a=1,b=2), "\x01\x00\x02", None],
    [Struct("struct", UBInt8("a"), UBInt16("b"), Struct("foo", UBInt8("c"), UBInt8("d"))).build, Container(a=1,b=2,foo=Container(c=3,d=4)), "\x01\x00\x02\x03\x04", None],
    [Struct("struct", UBInt8("a"), UBInt16("b"), Embedded(Struct("foo", UBInt8("c"), UBInt8("d")))).build, Container(a=1,b=2,c=3,d=4), "\x01\x00\x02\x03\x04", None],
    
    [Sequence("sequence", UBInt8("a"), UBInt16("b")).parse, "\x01\x00\x02", [1,2], None],
    [Sequence("sequence", UBInt8("a"), UBInt16("b"), Sequence("foo", UBInt8("c"), UBInt8("d"))).parse, "\x01\x00\x02\x03\x04", [1,2,[3,4]], None],
    [Sequence("sequence", UBInt8("a"), UBInt16("b"), Embedded(Sequence("foo", UBInt8("c"), UBInt8("d")))).parse, "\x01\x00\x02\x03\x04", [1,2,3,4], None],
    [Sequence("sequence", UBInt8("a"), UBInt16("b")).build, [1,2], "\x01\x00\x02", None],
    [Sequence("sequence", UBInt8("a"), UBInt16("b"), Sequence("foo", UBInt8("c"), UBInt8("d"))).build, [1,2,[3,4]], "\x01\x00\x02\x03\x04", None],
    [Sequence("sequence", UBInt8("a"), UBInt16("b"), Embedded(Sequence("foo", UBInt8("c"), UBInt8("d")))).build, [1,2,3,4], "\x01\x00\x02\x03\x04", None],
    
    [Switch("switch", lambda ctx: 5, {1:UBInt8("x"), 5:UBInt16("y")}).parse, "\x00\x02", 2, None],
    [Switch("switch", lambda ctx: 6, {1:UBInt8("x"), 5:UBInt16("y")}).parse, "\x00\x02", None, SwitchError],
    [Switch("switch", lambda ctx: 6, {1:UBInt8("x"), 5:UBInt16("y")}, default = UBInt8("x")).parse, "\x00\x02", 0, None],
    [Switch("switch", lambda ctx: 5, {1:UBInt8("x"), 5:UBInt16("y")}, include_key = True).parse, "\x00\x02", (5, 2), None],
    [Switch("switch", lambda ctx: 5, {1:UBInt8("x"), 5:UBInt16("y")}).build, 2, "\x00\x02", None],
    [Switch("switch", lambda ctx: 6, {1:UBInt8("x"), 5:UBInt16("y")}).build, 9, None, SwitchError],
    [Switch("switch", lambda ctx: 6, {1:UBInt8("x"), 5:UBInt16("y")}, default = UBInt8("x")).build, 9, "\x09", None],
    [Switch("switch", lambda ctx: 5, {1:UBInt8("x"), 5:UBInt16("y")}, include_key = True).build, ((5, 2),), "\x00\x02", None],
    [Switch("switch", lambda ctx: 5, {1:UBInt8("x"), 5:UBInt16("y")}, include_key = True).build, ((89, 2),), None, SwitchError],
    
    [Select("select", UBInt32("a"), UBInt16("b"), UBInt8("c")).parse, "\x07", 7, None],
    [Select("select", UBInt32("a"), UBInt16("b")).parse, "\x07", None, SelectError],
    [Select("select", UBInt32("a"), UBInt16("b"), UBInt8("c"), include_name = True).parse, "\x07", ("c", 7), None],
    [Select("select", UBInt32("a"), UBInt16("b"), UBInt8("c")).build, 7, "\x00\x00\x00\x07", None],
    [Select("select", UBInt32("a"), UBInt16("b"), UBInt8("c"), include_name = True).build, (("c", 7),), "\x07", None],
    [Select("select", UBInt32("a"), UBInt16("b"), UBInt8("c"), include_name = True).build, (("d", 7),), None, SelectError],
    
    [Peek(UBInt8("peek")).parse, "\x01", 1, None],
    [Peek(UBInt8("peek")).parse, "", None, None],
    [Peek(UBInt8("peek")).build, 1, "", None],
    [Peek(UBInt8("peek"), perform_build = True).build, 1, "\x01", None],
    [Struct("peek", Peek(UBInt8("a")), UBInt16("b")).parse, "\x01\x02", Container(a=1,b=0x102), None],
    [Struct("peek", Peek(UBInt8("a")), UBInt16("b")).build, Container(a=1,b=0x102), "\x01\x02", None],
    
    [Value("value", lambda ctx: "moo").parse, "", "moo", None],
    [Value("value", lambda ctx: "moo").build, None, "", None],
    
    [Anchor("anchor").parse, "", 0, None],
    [Anchor("anchor").build, None, "", None],
    
    [LazyBound("lazybound", lambda: UBInt8("foo")).parse, "\x02", 2, None],
    [LazyBound("lazybound", lambda: UBInt8("foo")).build, 2, "\x02", None],
    
    [Pass.parse, "", None, None],
    [Pass.build, None, "", None],

    [Terminator.parse, "", None, None],
    [Terminator.parse, "x", None, TerminatorError],
    [Terminator.build, None, "", None],
    
    [Pointer(lambda ctx: 2, UBInt8("pointer")).parse, "\x00\x00\x07", 7, None],
    [Pointer(lambda ctx: 2, UBInt8("pointer")).build, 7, "\x00\x00\x07", None],
    
    [OnDemand(UBInt8("ondemand")).parse("\x08").read, (), 8, None],
    [Struct("ondemand", UBInt8("a"), OnDemand(UBInt8("b")), UBInt8("c")).parse, 
        "\x07\x08\x09", Container(a=7,b=LazyContainer(None, None, None, None),c=9), None],
    [Struct("ondemand", UBInt8("a"), OnDemand(UBInt8("b"), advance_stream = False), UBInt8("c")).parse, 
        "\x07\x09", Container(a=7,b=LazyContainer(None, None, None, None),c=9), None],
    
    [OnDemand(UBInt8("ondemand")).build, 8, "\x08", None],
    [Struct("ondemand", UBInt8("a"), OnDemand(UBInt8("b")), UBInt8("c")).build, 
        Container(a=7,b=8,c=9), "\x07\x08\x09", None],
    [Struct("ondemand", UBInt8("a"), OnDemand(UBInt8("b"), force_build = False), UBInt8("c")).build, 
        Container(a=7,b=LazyContainer(None, None, None, None),c=9), "\x07\x00\x09", None],
    [Struct("ondemand", UBInt8("a"), OnDemand(UBInt8("b"), force_build = False, advance_stream = False), UBInt8("c")).build, 
        Container(a=7,b=LazyContainer(None, None, None, None),c=9), "\x07\x09", None],
    
    [Struct("reconfig", Reconfig("foo", UBInt8("bar"))).parse, "\x01", Container(foo=1), None],
    [Struct("reconfig", Reconfig("foo", UBInt8("bar"))).build, Container(foo=1), "\x01", None],
    
    [Buffered(UBInt8("buffered"), lambda x:x, lambda x:x, lambda x:x).parse, 
        "\x07", 7, None],
    [Buffered(GreedyRange(UBInt8("buffered")), lambda x:x, lambda x:x, lambda x:x).parse, 
        "\x07", None, SizeofError],
    [Buffered(UBInt8("buffered"), lambda x:x, lambda x:x, lambda x:x).build, 
        7, "\x07", None],
    [Buffered(GreedyRange(UBInt8("buffered")), lambda x:x, lambda x:x, lambda x:x).build, 
        [7], None, SizeofError],
    
    [Restream(UBInt8("restream"), lambda x:x, lambda x:x, lambda x:x).parse,
        "\x07", 7, None],
    [Restream(GreedyRepeater(UBInt8("restream")), lambda x:x, lambda x:x, lambda x:x).parse,
        "\x07", [7], None],
    [Restream(UBInt8("restream"), lambda x:x, lambda x:x, lambda x:x).parse,
        "\x07", 7, None],
    [Restream(GreedyRepeater(UBInt8("restream")), lambda x:x, lambda x:x, lambda x:x).parse,
        "\x07", [7], None],
    
    #
    # adapters
    #
    [BitIntegerAdapter(Field("bitintegeradapter", 8), 8).parse, "\x01" * 8, 255, None],
    [BitIntegerAdapter(Field("bitintegeradapter", 8), 8, signed = True).parse, "\x01" * 8, -1, None],
    [BitIntegerAdapter(Field("bitintegeradapter", 8), 8, swapped = True, bytesize = 4).parse, 
        "\x01" * 4 + "\x00" * 4, 0x0f, None],
    [BitIntegerAdapter(Field("bitintegeradapter", 8), 8).build, 255, "\x01" * 8, None],
    [BitIntegerAdapter(Field("bitintegeradapter", 8), 8).build, -1, None, BitIntegerError],
    [BitIntegerAdapter(Field("bitintegeradapter", 8), 8, signed = True).build, -1, "\x01" * 8, None],
    [BitIntegerAdapter(Field("bitintegeradapter", 8), 8, swapped = True, bytesize = 4).build, 
        0x0f, "\x01" * 4 + "\x00" * 4, None],
    
    [MappingAdapter(UBInt8("mappingadapter"), {2:"x",3:"y"}, {"x":2,"y":3}).parse,
        "\x03", "y", None],
    [MappingAdapter(UBInt8("mappingadapter"), {2:"x",3:"y"}, {"x":2,"y":3}).parse,
        "\x04", None, MappingError],
    [MappingAdapter(UBInt8("mappingadapter"), {2:"x",3:"y"}, {"x":2,"y":3}, decdefault="foo").parse,
        "\x04", "foo", None],
    [MappingAdapter(UBInt8("mappingadapter"), {2:"x",3:"y"}, {"x":2,"y":3}, decdefault=Pass).parse,
        "\x04", 4, None],
    [MappingAdapter(UBInt8("mappingadapter"), {2:"x",3:"y"}, {"x":2,"y":3}).build,
        "y", "\x03", None],
    [MappingAdapter(UBInt8("mappingadapter"), {2:"x",3:"y"}, {"x":2,"y":3}).build,
        "z", None, MappingError],
    [MappingAdapter(UBInt8("mappingadapter"), {2:"x",3:"y"}, {"x":2,"y":3}, encdefault=17).build,
        "foo", "\x11", None],
    [MappingAdapter(UBInt8("mappingadapter"), {2:"x",3:"y"}, {"x":2,"y":3}, encdefault=Pass).build,
        4, "\x04", None],
        
    [FlagsAdapter(UBInt8("flagsadapter"), {"a":1,"b":2,"c":4,"d":8,"e":16,"f":32,"g":64,"h":128}).parse, 
        "\x81", Container(a=True, b=False,c=False,d=False,e=False,f=False,g=False,h=True), None],
    [FlagsAdapter(UBInt8("flagsadapter"), {"a":1,"b":2,"c":4,"d":8,"e":16,"f":32,"g":64,"h":128}).build, 
        Container(a=True, b=False,c=False,d=False,e=False,f=False,g=False,h=True), "\x81", None],
    
    [IndexingAdapter(Array(3, UBInt8("indexingadapter")), 2).parse, "\x11\x22\x33", 0x33, None],
    [IndexingAdapter(Array(3, UBInt8("indexingadapter")), 2)._encode, (0x33, {}), [None, None, 0x33], None],
    
    [SlicingAdapter(Array(3, UBInt8("indexingadapter")), 1, 3).parse, "\x11\x22\x33", [0x22, 0x33], None],
    [SlicingAdapter(Array(3, UBInt8("indexingadapter")), 1, 3)._encode, ([0x22, 0x33], {}), [None, 0x22, 0x33], None],
    
    [PaddingAdapter(Field("paddingadapter", 4)).parse, "abcd", "abcd", None],
    [PaddingAdapter(Field("paddingadapter", 4), strict = True).parse, "abcd", None, PaddingError],
    [PaddingAdapter(Field("paddingadapter", 4), strict = True).parse, "\x00\x00\x00\x00", "\x00\x00\x00\x00", None],
    [PaddingAdapter(Field("paddingadapter", 4)).build, "abcd", "\x00\x00\x00\x00", None],
    
    [LengthValueAdapter(Sequence("lengthvalueadapter", UBInt8("length"), Field("value", lambda ctx: ctx.length))).parse,
        "\x05abcde", "abcde", None],
    [LengthValueAdapter(Sequence("lengthvalueadapter", UBInt8("length"), Field("value", lambda ctx: ctx.length))).build,
        "abcde", "\x05abcde", None],
        
    [TunnelAdapter(PascalString("data", encoding = "zlib"), GreedyRange(UBInt16("elements"))).parse, 
        "\rx\x9cc`f\x18\x16\x10\x00u\xf8\x01-", [3] * 100, None],
    [TunnelAdapter(PascalString("data", encoding = "zlib"), GreedyRange(UBInt16("elements"))).build, 
        [3] * 100, "\rx\x9cc`f\x18\x16\x10\x00u\xf8\x01-", None],
    
    [Const(Field("const", 2), "MZ").parse, "MZ", "MZ", None],
    [Const(Field("const", 2), "MZ").parse, "MS", None, ConstError],
    [Const(Field("const", 2), "MZ").build, "MZ", "MZ", None],
    [Const(Field("const", 2), "MZ").build, "MS", None, ConstError],
    [Const(Field("const", 2), "MZ").build, None, "MZ", None],
    
    [ExprAdapter(UBInt8("expradapter"), 
        encoder = lambda obj, ctx: obj / 7, 
        decoder = lambda obj, ctx: obj * 7).parse, 
        "\x06", 42, None],
    [ExprAdapter(UBInt8("expradapter"), 
        encoder = lambda obj, ctx: obj / 7, 
        decoder = lambda obj, ctx: obj * 7).build, 
        42, "\x06", None],
    #
    # text
    #
    [QuotedString("foo", start_quote = "{", end_quote = "}", esc_char = "-").parse,
        "{hello-} world}", "hello} world", None],
    [QuotedString("foo", start_quote = "{", end_quote = "}", esc_char = None).parse,
        "{hello-} world}", "hello-", None],
    [QuotedString("foo", start_quote = "{", end_quote = "}", esc_char = None, allow_eof = True).parse,
        "{hello world", "hello world", None],
    [QuotedString("foo", start_quote = "{", end_quote = "}", esc_char = None, allow_eof = False).parse,
        "{hello world", None, FieldError],
    [QuotedString("foo", start_quote = "{", end_quote = "}", esc_char = "-").build,
        "hello} world", "{hello-} world}", None],
    [QuotedString("foo", start_quote = "{", end_quote = "}", esc_char = None).build,
        "hello}", None, QuotedStringError],

    [Identifier("identifier").parse, "ab_c8 XXX", "ab_c8", None],
    [Identifier("identifier").parse, "_c8 XXX", "_c8", None],
    [Identifier("identifier").parse, "2c8 XXX", None, ValidationError],
    [Identifier("identifier").build, "ab_c8", "ab_c8", None],
    [Identifier("identifier").build, "_c8", "_c8", None],
    [Identifier("identifier").build, "2c8", None, ValidationError],
    
    [TextualIntAdapter(Field("textintadapter", 3)).parse, "234", 234, None],
    [TextualIntAdapter(Field("textintadapter", 3), radix = 16).parse, "234", 0x234, None],
    [TextualIntAdapter(Field("textintadapter", 3)).build, 234, "234", None],
    [TextualIntAdapter(Field("textintadapter", 3), radix = 16).build, 0x234, "234", None],
    # [TextualIntAdapter(Field("textintadapter", 3)).build, 23, "023", None],
    
    [StringUpto("stringupto", "XY").parse, "helloX", "hello", None],
    [StringUpto("stringupto", "XY").parse, "helloY", "hello", None],
    [StringUpto("stringupto", "XY").build, "helloX", "hello", None],
    
    #
    # macros
    #
    [Aligned(UBInt8("aligned")).parse, "\x01\x00\x00\x00", 1, None],
    [Aligned(UBInt8("aligned")).build, 1, "\x01\x00\x00\x00", None],
    [Struct("aligned", Aligned(UBInt8("a")), UBInt8("b")).parse, 
        "\x01\x00\x00\x00\x02", Container(a=1,b=2), None],
    [Struct("aligned", Aligned(UBInt8("a")), UBInt8("b")).build, 
        Container(a=1,b=2), "\x01\x00\x00\x00\x02", None],
    
    [Bitwise(Field("bitwise", 8)).parse, "\xff", "\x01" * 8, None],
    [Bitwise(Field("bitwise", lambda ctx: 8)).parse, "\xff", "\x01" * 8, None],
    [Bitwise(Field("bitwise", 8)).build, "\x01" * 8, "\xff", None],
    [Bitwise(Field("bitwise", lambda ctx: 8)).build, "\x01" * 8, "\xff", None],
    
    [Union("union", 
        UBInt32("a"), 
        Struct("b", UBInt16("a"), UBInt16("b")), 
        BitStruct("c", Padding(4), Octet("a"), Padding(4)), 
        Struct("d", UBInt8("a"), UBInt8("b"), UBInt8("c"), UBInt8("d")),
        Embedded(Struct("q", UBInt8("e"))),
        ).parse,
        "\x11\x22\x33\x44",
        Container(a=0x11223344, 
            b=Container(a=0x1122, b=0x3344), 
            c=Container(a=0x12),
            d=Container(a=0x11, b=0x22, c=0x33, d=0x44),
            e=0x11,
        ),
        None],
    [Union("union", 
        UBInt32("a"), 
        Struct("b", UBInt16("a"), UBInt16("b")), 
        BitStruct("c", Padding(4), Octet("a"), Padding(4)), 
        Struct("d", UBInt8("a"), UBInt8("b"), UBInt8("c"), UBInt8("d")), 
        Embedded(Struct("q", UBInt8("e"))),
        ).build,
        Container(a=0x11223344, 
            b=Container(a=0x1122, b=0x3344), 
            c=Container(a=0x12),
            d=Container(a=0x11, b=0x22, c=0x33, d=0x44),
            e=0x11,
        ),
        "\x11\x22\x33\x44",
        None],

    [Enum(UBInt8("enum"),q=3,r=4,t=5).parse, "\x04", "r", None],
    [Enum(UBInt8("enum"),q=3,r=4,t=5).parse, "\x07", None, MappingError],
    [Enum(UBInt8("enum"),q=3,r=4,t=5, _default_ = "spam").parse, "\x07", "spam", None],
    [Enum(UBInt8("enum"),q=3,r=4,t=5, _default_ =Pass).parse, "\x07", 7, None],
    [Enum(UBInt8("enum"),q=3,r=4,t=5).build, "r", "\x04", None],
    [Enum(UBInt8("enum"),q=3,r=4,t=5).build, "spam", None, MappingError],
    [Enum(UBInt8("enum"),q=3,r=4,t=5, _default_ = 9).build, "spam", "\x09", None],
    [Enum(UBInt8("enum"),q=3,r=4,t=5, _default_ =Pass).build, 9, "\x09", None],

    [PrefixedArray(UBInt8("array"), UBInt8("count")).parse, "\x03\x01\x01\x01", [1,1,1], None],
    [PrefixedArray(UBInt8("array"), UBInt8("count")).parse, "\x03\x01\x01", None, ArrayError],
    [PrefixedArray(UBInt8("array"), UBInt8("count")).build, [1,1,1], "\x03\x01\x01\x01", None],
    
    [IfThenElse("ifthenelse", lambda ctx: True, UBInt8("then"), UBInt16("else")).parse, 
        "\x01", 1, None],
    [IfThenElse("ifthenelse", lambda ctx: False, UBInt8("then"), UBInt16("else")).parse, 
        "\x00\x01", 1, None],
    [IfThenElse("ifthenelse", lambda ctx: True, UBInt8("then"), UBInt16("else")).build, 
        1, "\x01", None],
    [IfThenElse("ifthenelse", lambda ctx: False, UBInt8("then"), UBInt16("else")).build, 
        1, "\x00\x01", None],
    
    [Magic("MZ").parse, "MZ", "MZ", None],
    [Magic("MZ").parse, "ELF", None, ConstError],
    [Magic("MZ").build, None, "MZ", None],
]


def run_tests(tests):
    errors = []
    for func, args, res, exctype in tests:
        if type(args) is not tuple:
            args = (args,)
        try:
            r = func(*args)
        except:
            t, ex, tb = sys.exc_info()
            if exctype is None:
                errors.append("[%s]: unexpected exception %r" % (func, ex))
                continue
            if t is not exctype:
                errors.append("[%s]: raised %r, expected %r" % (func, t, exctype))
                continue
        else:
            if exctype is not None:
                errors.append("[%s]: expected exception %r" % (func, exctype))
                continue
            if r != res:
                errors.append("[%s]: returned %r, expected %r" % (func, r, res))
                continue
    return errors


def run_all():
    errors = run_tests(tests)
    if not errors:
        print "success"
    else:
        print "errors:"
        for e in errors:
            print "   ", e

if __name__ == "__main__":
    run_all()

########NEW FILE########
__FILENAME__ = ast
from construct.core import Container
from construct.adapters import Adapter

class AstNode(Container):
    def __init__(self, nodetype, **kw):
        Container.__init__(self)
        self.nodetype = nodetype
        for k, v in sorted(kw.iteritems()):
            setattr(self, k, v)

    def accept(self, visitor):
        return getattr(visitor, "visit_%s" % (self.nodetype,))(self)

class AstTransformator(Adapter):
    def _decode(self, obj, context):
        return self.to_ast(obj, context)
    def _encode(self, obj, context):
        return self.to_cst(obj, context)

########NEW FILE########
__FILENAME__ = common
"""
common constructs for typical programming languages (numbers, strings, ...)
"""
from construct.core import (Construct, ConstructError, FieldError,
    SizeofError)
from construct.adapters import (Adapter, StringAdapter, IndexingAdapter,
    ConstAdapter, OneOf, NoneOf)
from construct.macros import (Field, OptionalGreedyRange, GreedyRange,
    Sequence, Optional)


#===============================================================================
# exceptions
#===============================================================================
class QuotedStringError(ConstructError):
    __slots__ = []


#===============================================================================
# constructs
#===============================================================================
class QuotedString(Construct):
    r"""
    A quoted string (begins with an opening-quote, terminated by a
    closing-quote, which may be escaped by an escape character)

    Parameters:
    * name - the name of the field
    * start_quote - the opening quote character. default is '"'
    * end_quote - the closing quote character. default is '"'
    * esc_char - the escape character, or None to disable escaping. defualt
      is "\" (backslash)
    * encoding - the character encoding (e.g., "utf8"), or None to return
      raw bytes. defualt is None.
    * allow_eof - whether to allow EOF before the closing quote is matched.
      if False, an exception will be raised when EOF is reached by the closing
      quote is missing. default is False.

    Example:
    QuotedString("foo", start_quote = "{", end_quote = "}", esc_char = None)
    """
    __slots__ = [
        "start_quote", "end_quote", "char", "esc_char", "encoding",
        "allow_eof"
    ]
    def __init__(self, name, start_quote = '"', end_quote = None,
                 esc_char = '\\', encoding = None, allow_eof = False):
        Construct.__init__(self, name)
        if end_quote is None:
            end_quote = start_quote
        self.start_quote = Literal(start_quote)
        self.char = Char("char")
        self.end_quote = end_quote
        self.esc_char = esc_char
        self.encoding = encoding
        self.allow_eof = allow_eof

    def _parse(self, stream, context):
        self.start_quote._parse(stream, context)
        text = []
        escaped = False
        try:
            while True:
                ch = self.char._parse(stream, context)
                if ch == self.esc_char:
                    if escaped:
                        text.append(ch)
                        escaped = False
                    else:
                        escaped = True
                elif ch == self.end_quote and not escaped:
                    break
                else:
                    text.append(ch)
                    escaped = False
        except FieldError:
            if not self.allow_eof:
                raise
        text = "".join(text)
        if self.encoding is not None:
            text = text.decode(self.encoding)
        return text

    def _build(self, obj, stream, context):
        self.start_quote._build(None, stream, context)
        if self.encoding:
            obj = obj.encode(self.encoding)
        for ch in obj:
            if ch == self.esc_char:
                self.char._build(self.esc_char, stream, context)
            elif ch == self.end_quote:
                if self.esc_char is None:
                    raise QuotedStringError("found ending quote in data, "
                        "but no escape char defined", ch)
                else:
                    self.char._build(self.esc_char, stream, context)
            self.char._build(ch, stream, context)
        self.char._build(self.end_quote, stream, context)

    def _sizeof(self, context):
        raise SizeofError("can't calculate size")


#===============================================================================
# macros
#===============================================================================
class WhitespaceAdapter(Adapter):
    """
    Adapter for whitespace sequences; do not use directly.
    See Whitespace.

    Parameters:
    * subcon - the subcon to adapt
    * build_char - the character used for encoding (building)
    """
    __slots__ = ["build_char"]
    def __init__(self, subcon, build_char):
        Adapter.__init__(self, subcon)
        self.build_char = build_char
    def _encode(self, obj, context):
        return self.build_char
    def _decode(self, obj, context):
        return None

def Whitespace(charset = " \t", optional = True):
    """whitespace (space that is ignored between tokens). when building, the
    first character of the charset is used.
    * charset - the set of characters that are considered whitespace. default
      is space and tab.
    * optional - whether or not whitespace is optional. default is True.
    """
    con = CharOf(None, charset)
    if optional:
        con = OptionalGreedyRange(con)
    else:
        con = GreedyRange(con)
    return WhitespaceAdapter(con, build_char = charset[0])

def Literal(text):
    """matches a literal string in the text
    * text - the text (string) to match
    """
    return ConstAdapter(Field(None, len(text)), text)

def Char(name):
    """a one-byte character"""
    return Field(name, 1)

def CharOf(name, charset):
    """matches only characters of a given charset
    * name - the name of the field
    * charset - the set of valid characters
    """
    return OneOf(Char(name), charset)

def CharNoneOf(name, charset):
    """matches only characters that do not belong to a given charset
    * name - the name of the field
    * charset - the set of invalid characters
    """
    return NoneOf(Char(name), charset)

def Alpha(name):
    """a letter character (A-Z, a-z)"""
    return CharOf(name, set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'))

def Digit(name):
    """a digit character (0-9)"""
    return CharOf(name, set('0123456789'))

def AlphaDigit(name):
    """an alphanumeric character (A-Z, a-z, 0-9)"""
    return CharOf(name, set("0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"))

def BinDigit(name):
    """a binary digit (0-1)"""
    return CharOf(name, set('01'))

def HexDigit(name):
    """a hexadecimal digit (0-9, A-F, a-f)"""
    return CharOf(name, set('0123456789abcdefABCDEF'))

def Word(name):
    """a sequence of letters"""
    return StringAdapter(GreedyRange(Alpha(name)))

class TextualIntAdapter(Adapter):
    """
    Adapter for textual integers

    Parameters:
    * subcon - the subcon to adapt
    * radix - the base of the integer (decimal, hexadecimal, binary, ...)
    * digits - the sequence of digits of that radix
    """
    __slots__ = ["radix", "digits"]
    def __init__(self, subcon, radix = 10, digits = "0123456789abcdef"):
        Adapter.__init__(self, subcon)
        if radix > len(digits):
            raise ValueError("not enough digits for radix %d" % (radix,))
        self.radix = radix
        self.digits = digits
    def _encode(self, obj, context):
        chars = []
        if obj < 0:
            chars.append("-")
            n = -obj
        else:
            n = obj
        r = self.radix
        digs = self.digits
        while n > 0:
            n, d = divmod(n, r)
            chars.append(digs[d])
        # obj2 = "".join(reversed(chars))
        # filler = digs[0] * (self._sizeof(context) - len(obj2))
        # return filler + obj2
        return "".join(reversed(chars))
    def _decode(self, obj, context):
        return int("".join(obj), self.radix)

def DecNumber(name):
    """decimal number"""
    return TextualIntAdapter(GreedyRange(Digit(name)))

def BinNumber(name):
    """binary number"""
    return TextualIntAdapter(GreedyRange(BinDigit(name)), 2)

def HexNumber(name):
    """hexadecimal number"""
    return TextualIntAdapter(GreedyRange(HexDigit(name)), 16)

class TextualFloatAdapter(Adapter):
    def _decode(self, obj, context):
        whole, frac, exp = obj
        mantissa = "".join(whole) + "." + "".join(frac)
        if exp:
            sign, value = exp
            if not sign:
                sign = ""
            return float(mantissa + "e" + sign + "".join(value))
        else:
            return float(mantissa)
    def _encode(self, obj, context):
        obj = str(obj)
        exp = None
        if "e" in obj:
            obj, exp = obj.split("e")
            sign = exp[0]
            value = exp[1:]
            exp = [sign, value]
        whole, frac = obj.split(".")
        return [whole, frac, exp]

def FloatNumber(name):
    return TextualFloatAdapter(
        Sequence(name,
            GreedyRange(Digit("whole")),
            Literal("."),
            GreedyRange(Digit("frac")),
            Optional(
                Sequence("exp",
                    Literal("e"),
                    Optional(CharOf("sign", "+-")),
                    GreedyRange(Digit("value")),
                )
            )
        )
    )

def StringUpto(name, terminators, consume_terminator = False, allow_eof = True):
    """a string that stretches up to a terminator, or EOF. this is a more
    flexible version of CString.
    * name - the name of the field
    * terminator - the set of terminator characters
    * consume_terminator - whether to consume the terminator character. the
      default is False.
    * allow_eof - whether to allow EOF to terminate the string. the default
      is True. this option is applicable only if consume_terminator is set.
    """
    con = StringAdapter(OptionalGreedyRange(CharNoneOf(name, terminators)))
    if not consume_terminator:
        return con
    if allow_eof:
        term = Optional(CharOf(None, terminators))
    else:
        term = CharOf(None, terminators)
    return IndexingAdapter(Sequence("foo", con, term), index = 0)

def Line(name, consume_terminator = True, allow_eof = True):
    r"""a textual line (up to "\n")
    * name - the name of the field
    * consume_terminator - whether to consume the newline character. the
      default is True.
    * allow_eof - whether to allow EOF to terminate the string. the default
      is True. this option is applicable only if consume_terminator is set.
    """
    return StringUpto(name, "\n",
        consume_terminator = consume_terminator,
        allow_eof = allow_eof
    )

class IdentifierAdapter(Adapter):
    """
    Adapter for programmatic identifiers

    Parameters:
    * subcon - the subcon to adapt
    """
    def _encode(self, obj, context):
        return obj[0], obj[1:]
    def _decode(self, obj, context):
        return obj[0] + "".join(obj[1])

def Identifier(name,
               headset = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_"),
               tailset = set("0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_")
    ):
    """a programmatic identifier (symbol). must start with a char of headset,
    followed by a sequence of tailset characters
    * name - the name of the field
    * headset - charset for the first character. default is A-Z, a-z, and _
    * tailset - charset for the tail. default is A-Z, a-z, 0-9 and _
    """
    return IdentifierAdapter(
        Sequence(name,
            CharOf("head", headset),
            OptionalGreedyRange(CharOf("tail", tailset)),
        )
    )

########NEW FILE########
__FILENAME__ = test
from construct import *
from construct.text import *



#===============================================================================
# AST transfomations
#===============================================================================
class NumberTransformator(AstTransformator):
    def to_ast(self, obj, context):
        return AstNode("number", value = obj)

class StringTransformator(AstTransformator):
    def to_ast(self, obj, context):
        return AstNode("string", value = obj)

class SymbolTransformator(AstTransformator):
    keywords = set([
        "if", "for", "while", "else", "def", "import", "in", "and", "or",
        "not", "as", "from", "return", "const", "var",
    ])
    def to_ast(self, obj, context):
        if obj in self.keywords:
            return AstNode("error", 
                message = "reserved word used as a symbol", 
                args = [obj]
            )
        else:
            return AstNode("symbol", name = obj)

class CommentTransformator(AstTransformator):
    def to_ast(self, obj, context):
        return AstNode("comment", text = obj)

class CallTransformator(AstTransformator):
    def to_ast(self, obj, context):
        symbol, args, lastarg = obj
        args.append(lastarg)
        return AstNode("call", name = symbol, args = args)

class ExprTransformator(AstTransformator):
    def to_ast(self, obj, context):
        lhs, rhs = obj
        if rhs is None:
            return lhs
        else:
            op, rhs = rhs
            return AstNode("expr", lhs = lhs, op = op, rhs = rhs)

class VardefTransformator(AstTransformator):
    def to_ast(self, obj, context):
        args, lastarg = obj
        vars = []
        for name, type, init in args:
            args.append((name, type, init))
        name, type, init = lastarg
        vars.append((name, type, init))
        return AstNode("vardef", vars = vars)

class AsgnTransformator(AstTransformator):
    def to_ast(self, obj, context):
        name, expr = obj
        return AstNode("asgnstmt", name = name, expr = expr)

class IfTransformator(AstTransformator):
    def to_ast(self, obj, context):
        return AstNode("ifstmt", 
            cond = obj.cond, 
            thencode = obj.thencode, 
            elsecode = obj.elsecode
        )

class WhileTransformator(AstTransformator):
    def to_ast(self, obj, context):
        return AstNode("whilestmt", cond = obj.cond, code = obj.code) 

class BlockTransformator(AstTransformator):
    def to_ast(self, obj, context):
        return AstNode("block", statements = obj)

class RootTransformator(AstTransformator):
    def to_ast(self, obj, context):
        return AstNode("root", statements = obj)


#===============================================================================
# macros
#===============================================================================
def OptSeq(name, *subcons):
    return Optional(Sequence(name, *subcons))

def SeqOfOne(name, *subcons):
    return IndexingAdapter(Sequence(name, *subcons), index = 0)

def OptSeqOfOne(name, *subcons):
    return Optional(SeqOfOne(name, *subcons))

def Expr(name):
    return LazyBound(name, lambda: expr2)


#===============================================================================
# grammar
#===============================================================================
ws = Whitespace(" \t\r\n")
rws = Whitespace(" \t\r\n", optional = False)

number = NumberTransformator(
    Select("num", 
        FloatNumber("flt"), 
        SeqOfOne("hex",
            Literal("0x"),
            HexNumber("value"),
        ),
        DecNumber("dec"),
    )
)

symbol = SymbolTransformator(Identifier("symbol"))

call = CallTransformator(
    Sequence("call",
        symbol,
        ws,
        Literal("("),
        OptionalGreedyRange(
            SeqOfOne("args",
                Expr("expr"),
                Literal(","),
            )
        ),
        Optional(Expr("expr")),
        Literal(")"),
    )
)

comment = CommentTransformator(
    SeqOfOne("comment",
        Literal("/*"),
        StringUpto("text", "*/"),
        Literal("*/"),
    )
)

term = SeqOfOne("term",
    ws,
    Select("term",
        number,
        call,
        symbol,
        SeqOfOne("subexpr",
            Literal("("),
            Expr("subexpr"),
            Literal(")"),
        )
    ),
    ws,
)

expr1 = ExprTransformator(
    Sequence("expr1",
        term,
        OptSeq("rhs",
            CharOf("op", "*/"),
            LazyBound("expr1", lambda: expr1),
        )
    )
)
expr2 = ExprTransformator(
    Sequence("expr2",
        expr1,
        OptSeq("rhs",
            CharOf("op", "+-"),
            LazyBound("expr2", lambda: expr2),
        )
    )
)

asgnstmt = AsgnTransformator(
    Sequence("asgnstmt",
        symbol,
        ws,
        Literal("="),
        Expr("expr"),
        Literal(";"),
    )
)

vardef_elem = Sequence("vardef_elem",
    Identifier("name"),
    ws,
    Literal("as"),
    ws,
    Identifier("type"),
    OptSeqOfOne("init",
        ws,
        Literal("="),
        Expr("expr"),
    )
)
vardef = VardefTransformator(
    Sequence("vardef",
        Literal("var"),
        rws,
        OptionalGreedyRange(
            SeqOfOne("names",
                ws,
                vardef_elem,
                ws,
                Literal(","),
            )
        ),
        ws,
        vardef_elem,
        ws,
        Literal(";"),
    )
)

stmt = SeqOfOne("stmt",
    ws,
    Select("stmt",
        comment,
        LazyBound("if", lambda: ifstmt),
        LazyBound("while", lambda: whilestmt),
        asgnstmt,
        vardef,
        SeqOfOne("expr",
            Expr("expr"), 
            Literal(";")
        ),
    ),
    ws,
)
        
def Block(name):
    return BlockTransformator(
        Select(name,
            SeqOfOne("multi",
                ws,
                Literal("{"),
                OptionalGreedyRange(stmt),
                Literal("}"),
                ws,
            ),
            Sequence("single", stmt),
        )
    )

ifstmt = IfTransformator(
    Struct("ifstmt", 
        Literal("if"),
        ws,
        Literal("("),
        Expr("cond"),
        Literal(")"),
        Block("thencode"),
        Optional(
            SeqOfOne("elsecode",
                Literal("else"),
                Block("code"),
            )
        ),
    )
)

whilestmt = WhileTransformator(
    Struct("whilestmt", 
        Literal("while"),
        ws,
        Literal("("),
        Expr("cond"),
        Literal(")"),
        Block("code"),
    )
)

root = RootTransformator(
    OptionalGreedyRange(stmt)
)

test = """var x as int, y as int;"""

print vardef.parse(test)























########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Construct documentation build configuration file, created by
# sphinx-quickstart on Fri Dec 24 05:23:18 2010.
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
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.doctest']

autodoc_default_flags = ["members"]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Construct'
copyright = u'2010, Tomer Filiba'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '2.1'
# The full version, including alpha/beta/rc tags.
release = '2.1'

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
htmlhelp_basename = 'Constructdoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'construct.tex', u'Construct Documentation',
   u'Tomer Filiba', 'manual'),
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
    ('index', 'construct', u'Construct Documentation',
     [u'Tomer Filiba'], 1)
]

########NEW FILE########
