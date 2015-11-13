__FILENAME__ = cindex
# This file is part of cldoc.  cldoc is free software: you can
# redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#===- cindex.py - Python Indexing Library Bindings -----------*- python -*--===#
#
#                     The LLVM Compiler Infrastructure
#
# This file is distributed under the University of Illinois Open Source
# License. See LICENSE.TXT for details.
#
#===------------------------------------------------------------------------===#

r"""
Clang Indexing Library Bindings
===============================

This module provides an interface to the Clang indexing library. It is a
low-level interface to the indexing library which attempts to match the Clang
API directly while also being "pythonic". Notable differences from the C API
are:

 * string results are returned as Python strings, not CXString objects.

 * null cursors are translated to None.

 * access to child cursors is done via iteration, not visitation.

The major indexing objects are:

  Index

    The top-level object which manages some global library state.

  TranslationUnit

    High-level object encapsulating the AST for a single translation unit. These
    can be loaded from .ast files or parsed on the fly.

  Cursor

    Generic object for representing a node in the AST.

  SourceRange, SourceLocation, and File

    Objects representing information about the input source.

Most object information is exposed using properties, when the underlying API
call is efficient.
"""

# TODO
# ====
#
# o API support for invalid translation units. Currently we can't even get the
#   diagnostics on failure because they refer to locations in an object that
#   will have been invalidated.
#
# o fix memory management issues (currently client must hold on to index and
#   translation unit, or risk crashes).
#
# o expose code completion APIs.
#
# o cleanup ctypes wrapping, would be nice to separate the ctypes details more
#   clearly, and hide from the external interface (i.e., help(cindex)).
#
# o implement additional SourceLocation, SourceRange, and File methods.

from ctypes import *
import collections

from . import enumerations

# ctypes doesn't implicitly convert c_void_p to the appropriate wrapper
# object. This is a problem, because it means that from_parameter will see an
# integer and pass the wrong value on platforms where int != void*. Work around
# this by marshalling object arguments as void**.
c_object_p = POINTER(c_void_p)

callbacks = {}

### Exception Classes ###

class TranslationUnitLoadError(Exception):
    """Represents an error that occurred when loading a TranslationUnit.

    This is raised in the case where a TranslationUnit could not be
    instantiated due to failure in the libclang library.

    FIXME: Make libclang expose additional error information in this scenario.
    """
    pass

class TranslationUnitSaveError(Exception):
    """Represents an error that occurred when saving a TranslationUnit.

    Each error has associated with it an enumerated value, accessible under
    e.save_error. Consumers can compare the value with one of the ERROR_
    constants in this class.
    """

    # Indicates that an unknown error occurred. This typically indicates that
    # I/O failed during save.
    ERROR_UNKNOWN = 1

    # Indicates that errors during translation prevented saving. The errors
    # should be available via the TranslationUnit's diagnostics.
    ERROR_TRANSLATION_ERRORS = 2

    # Indicates that the translation unit was somehow invalid.
    ERROR_INVALID_TU = 3

    def __init__(self, enumeration, message):
        assert isinstance(enumeration, int)

        if enumeration < 1 or enumeration > 3:
            raise Exception("Encountered undefined TranslationUnit save error "
                            "constant: %d. Please file a bug to have this "
                            "value supported." % enumeration)

        self.save_error = enumeration
        Exception.__init__(self, 'Error %d: %s' % (enumeration, message))

### Structures and Utility Classes ###

class CachedProperty(object):
    """Decorator that lazy-loads the value of a property.

    The first time the property is accessed, the original property function is
    executed. The value it returns is set as the new value of that instance's
    property, replacing the original method.
    """

    def __init__(self, wrapped):
        self.wrapped = wrapped
        try:
            self.__doc__ = wrapped.__doc__
        except:
            pass

    def __get__(self, instance, instance_type=None):
        if instance is None:
            return self

        value = self.wrapped(instance)
        setattr(instance, self.wrapped.__name__, value)

        return value


class _CXString(Structure):
    """Helper for transforming CXString results."""

    _fields_ = [("spelling", c_char_p), ("free", c_int)]

    def __del__(self):
        conf.lib.clang_disposeString(self)

    @staticmethod
    def from_result(res, fn, args):
        assert isinstance(res, _CXString)
        return conf.lib.clang_getCString(res)

class SourceLocation(Structure):
    """
    A SourceLocation represents a particular location within a source file.
    """
    _fields_ = [("ptr_data", c_void_p * 2), ("int_data", c_uint)]
    _data = None

    def _get_instantiation(self):
        if self._data is None:
            f, l, c, o = c_object_p(), c_uint(), c_uint(), c_uint()
            conf.lib.clang_getInstantiationLocation(self, byref(f), byref(l),
                    byref(c), byref(o))
            if f:
                f = File(f)
            else:
                f = None
            self._data = (f, int(l.value), int(c.value), int(o.value))
        return self._data

    @staticmethod
    def from_position(tu, file, line, column):
        """
        Retrieve the source location associated with a given file/line/column in
        a particular translation unit.
        """
        return conf.lib.clang_getLocation(tu, file, line, column)

    @staticmethod
    def from_offset(tu, file, offset):
        """Retrieve a SourceLocation from a given character offset.

        tu -- TranslationUnit file belongs to
        file -- File instance to obtain offset from
        offset -- Integer character offset within file
        """
        return conf.lib.clang_getLocationForOffset(tu, file, offset)

    @property
    def file(self):
        """Get the file represented by this source location."""
        return self._get_instantiation()[0]

    @property
    def line(self):
        """Get the line represented by this source location."""
        return self._get_instantiation()[1]

    @property
    def column(self):
        """Get the column represented by this source location."""
        return self._get_instantiation()[2]

    @property
    def offset(self):
        """Get the file offset represented by this source location."""
        return self._get_instantiation()[3]

    def __eq__(self, other):
        return conf.lib.clang_equalLocations(self, other)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        if self.file:
            filename = self.file.name
        else:
            filename = None
        return "<SourceLocation file %r, line %r, column %r>" % (
            filename, self.line, self.column)

class SourceRange(Structure):
    """
    A SourceRange describes a range of source locations within the source
    code.
    """
    _fields_ = [
        ("ptr_data", c_void_p * 2),
        ("begin_int_data", c_uint),
        ("end_int_data", c_uint)]

    # FIXME: Eliminate this and make normal constructor? Requires hiding ctypes
    # object.
    @staticmethod
    def from_locations(start, end):
        return conf.lib.clang_getRange(start, end)

    @property
    def start(self):
        """
        Return a SourceLocation representing the first character within a
        source range.
        """
        return conf.lib.clang_getRangeStart(self)

    @property
    def end(self):
        """
        Return a SourceLocation representing the last character within a
        source range.
        """
        return conf.lib.clang_getRangeEnd(self)

    def __eq__(self, other):
        return conf.lib.clang_equalRanges(self, other)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return "<SourceRange start %r, end %r>" % (self.start, self.end)

class Diagnostic(object):
    """
    A Diagnostic is a single instance of a Clang diagnostic. It includes the
    diagnostic severity, the message, the location the diagnostic occurred, as
    well as additional source ranges and associated fix-it hints.
    """

    Ignored = 0
    Note    = 1
    Warning = 2
    Error   = 3
    Fatal   = 4

    def __init__(self, ptr):
        self.ptr = ptr

    def __del__(self):
        conf.lib.clang_disposeDiagnostic(self)

    @property
    def severity(self):
        return conf.lib.clang_getDiagnosticSeverity(self)

    @property
    def location(self):
        return conf.lib.clang_getDiagnosticLocation(self)

    @property
    def spelling(self):
        return conf.lib.clang_getDiagnosticSpelling(self)

    @property
    def ranges(self):
        class RangeIterator:
            def __init__(self, diag):
                self.diag = diag

            def __len__(self):
                return int(conf.lib.clang_getDiagnosticNumRanges(self.diag))

            def __getitem__(self, key):
                if (key >= len(self)):
                    raise IndexError
                return conf.lib.clang_getDiagnosticRange(self.diag, key)

        return RangeIterator(self)

    @property
    def fixits(self):
        class FixItIterator:
            def __init__(self, diag):
                self.diag = diag

            def __len__(self):
                return int(conf.lib.clang_getDiagnosticNumFixIts(self.diag))

            def __getitem__(self, key):
                range = SourceRange()
                value = conf.lib.clang_getDiagnosticFixIt(self.diag, key,
                        byref(range))
                if len(value) == 0:
                    raise IndexError

                return FixIt(range, value)

        return FixItIterator(self)

    @property
    def category_number(self):
        """The category number for this diagnostic."""
        return conf.lib.clang_getDiagnosticCategory(self)

    @property
    def category_name(self):
        """The string name of the category for this diagnostic."""
        return conf.lib.clang_getDiagnosticCategoryName(self.category_number)

    @property
    def option(self):
        """The command-line option that enables this diagnostic."""
        return conf.lib.clang_getDiagnosticOption(self, None)

    @property
    def format(self, options=-1):
        if options == -1:
            options = conf.lib.clang_defaultDiagnosticDisplayOptions()

        return conf.lib.clang_formatDiagnostic(self, options)

    @property
    def disable_option(self):
        """The command-line option that disables this diagnostic."""
        disable = _CXString()
        conf.lib.clang_getDiagnosticOption(self, byref(disable))

        return conf.lib.clang_getCString(disable)

    def __repr__(self):
        return "<Diagnostic severity %r, location %r, spelling %r>" % (
            self.severity, self.location, self.spelling)

    def from_param(self):
      return self.ptr

class FixIt(object):
    """
    A FixIt represents a transformation to be applied to the source to
    "fix-it". The fix-it shouldbe applied by replacing the given source range
    with the given value.
    """

    def __init__(self, range, value):
        self.range = range
        self.value = value

    def __repr__(self):
        return "<FixIt range %r, value %r>" % (self.range, self.value)

class TokenGroup(object):
    """Helper class to facilitate token management.

    Tokens are allocated from libclang in chunks. They must be disposed of as a
    collective group.

    One purpose of this class is for instances to represent groups of allocated
    tokens. Each token in a group contains a reference back to an instance of
    this class. When all tokens from a group are garbage collected, it allows
    this class to be garbage collected. When this class is garbage collected,
    it calls the libclang destructor which invalidates all tokens in the group.

    You should not instantiate this class outside of this module.
    """
    def __init__(self, tu, memory, count):
        self._tu = tu
        self._memory = memory
        self._count = count

    def __del__(self):
        conf.lib.clang_disposeTokens(self._tu, self._memory, self._count)

    @staticmethod
    def get_tokens(tu, extent):
        """Helper method to return all tokens in an extent.

        This functionality is needed multiple places in this module. We define
        it here because it seems like a logical place.
        """
        tokens_memory = POINTER(Token)()
        tokens_count = c_uint()

        conf.lib.clang_tokenize(tu, extent, byref(tokens_memory),
                byref(tokens_count))

        count = int(tokens_count.value)

        # If we get no tokens, no memory was allocated. Be sure not to return
        # anything and potentially call a destructor on nothing.
        if count < 1:
            return

        tokens_array = cast(tokens_memory, POINTER(Token * count)).contents

        token_group = TokenGroup(tu, tokens_memory, tokens_count)

        for i in xrange(0, count):
            token = Token()
            token.int_data = tokens_array[i].int_data
            token.ptr_data = tokens_array[i].ptr_data
            token._tu = tu
            token._group = token_group

            yield token

class TokenKind(object):
    """Describes a specific type of a Token."""

    _value_map = {} # int -> TokenKind

    def __init__(self, value, name):
        """Create a new TokenKind instance from a numeric value and a name."""
        self.value = value
        self.name = name

    def __repr__(self):
        return 'TokenKind.%s' % (self.name,)

    @staticmethod
    def from_value(value):
        """Obtain a registered TokenKind instance from its value."""
        result = TokenKind._value_map.get(value, None)

        if result is None:
            raise ValueError('Unknown TokenKind: %d' % value)

        return result

    @staticmethod
    def register(value, name):
        """Register a new TokenKind enumeration.

        This should only be called at module load time by code within this
        package.
        """
        if value in TokenKind._value_map:
            raise ValueError('TokenKind already registered: %d' % value)

        kind = TokenKind(value, name)
        TokenKind._value_map[value] = kind
        setattr(TokenKind, name, kind)

### Cursor Kinds ###

class CursorKind(object):
    """
    A CursorKind describes the kind of entity that a cursor points to.
    """

    # The unique kind objects, indexed by id.
    _kinds = []
    _name_map = None

    def __init__(self, value):
        if value >= len(CursorKind._kinds):
            CursorKind._kinds += [None] * (value - len(CursorKind._kinds) + 1)
        if CursorKind._kinds[value] is not None:
            raise ValueError,'CursorKind already loaded'
        self.value = value
        CursorKind._kinds[value] = self
        CursorKind._name_map = None

    def from_param(self):
        return self.value

    @property
    def name(self):
        """Get the enumeration name of this cursor kind."""
        if self._name_map is None:
            self._name_map = {}
            for key,value in CursorKind.__dict__.items():
                if isinstance(value,CursorKind):
                    self._name_map[value] = key
        return self._name_map[self]

    @staticmethod
    def from_id(id):
        if id >= len(CursorKind._kinds) or CursorKind._kinds[id] is None:
            raise ValueError,'Unknown cursor kind'
        return CursorKind._kinds[id]

    @staticmethod
    def get_all_kinds():
        """Return all CursorKind enumeration instances."""
        return filter(None, CursorKind._kinds)

    def is_declaration(self):
        """Test if this is a declaration kind."""
        return conf.lib.clang_isDeclaration(self)

    def is_reference(self):
        """Test if this is a reference kind."""
        return conf.lib.clang_isReference(self)

    def is_expression(self):
        """Test if this is an expression kind."""
        return conf.lib.clang_isExpression(self)

    def is_statement(self):
        """Test if this is a statement kind."""
        return conf.lib.clang_isStatement(self)

    def is_attribute(self):
        """Test if this is an attribute kind."""
        return conf.lib.clang_isAttribute(self)

    def is_invalid(self):
        """Test if this is an invalid kind."""
        return conf.lib.clang_isInvalid(self)

    def is_translation_unit(self):
        """Test if this is a translation unit kind."""
        return conf.lib.clang_isTranslationUnit(self)

    def is_preprocessing(self):
        """Test if this is a preprocessing kind."""
        return conf.lib.clang_isPreprocessing(self)

    def is_unexposed(self):
        """Test if this is an unexposed kind."""
        return conf.lib.clang_isUnexposed(self)

    def __repr__(self):
        return 'CursorKind.%s' % (self.name,)

# FIXME: Is there a nicer way to expose this enumeration? We could potentially
# represent the nested structure, or even build a class hierarchy. The main
# things we want for sure are (a) simple external access to kinds, (b) a place
# to hang a description and name, (c) easy to keep in sync with Index.h.

###
# Declaration Kinds

# A declaration whose specific kind is not exposed via this interface.
#
# Unexposed declarations have the same operations as any other kind of
# declaration; one can extract their location information, spelling, find their
# definitions, etc. However, the specific kind of the declaration is not
# reported.
CursorKind.UNEXPOSED_DECL = CursorKind(1)

# A C or C++ struct.
CursorKind.STRUCT_DECL = CursorKind(2)

# A C or C++ union.
CursorKind.UNION_DECL = CursorKind(3)

# A C++ class.
CursorKind.CLASS_DECL = CursorKind(4)

# An enumeration.
CursorKind.ENUM_DECL = CursorKind(5)

# A field (in C) or non-static data member (in C++) in a struct, union, or C++
# class.
CursorKind.FIELD_DECL = CursorKind(6)

# An enumerator constant.
CursorKind.ENUM_CONSTANT_DECL = CursorKind(7)

# A function.
CursorKind.FUNCTION_DECL = CursorKind(8)

# A variable.
CursorKind.VAR_DECL = CursorKind(9)

# A function or method parameter.
CursorKind.PARM_DECL = CursorKind(10)

# An Objective-C @interface.
CursorKind.OBJC_INTERFACE_DECL = CursorKind(11)

# An Objective-C @interface for a category.
CursorKind.OBJC_CATEGORY_DECL = CursorKind(12)

# An Objective-C @protocol declaration.
CursorKind.OBJC_PROTOCOL_DECL = CursorKind(13)

# An Objective-C @property declaration.
CursorKind.OBJC_PROPERTY_DECL = CursorKind(14)

# An Objective-C instance variable.
CursorKind.OBJC_IVAR_DECL = CursorKind(15)

# An Objective-C instance method.
CursorKind.OBJC_INSTANCE_METHOD_DECL = CursorKind(16)

# An Objective-C class method.
CursorKind.OBJC_CLASS_METHOD_DECL = CursorKind(17)

# An Objective-C @implementation.
CursorKind.OBJC_IMPLEMENTATION_DECL = CursorKind(18)

# An Objective-C @implementation for a category.
CursorKind.OBJC_CATEGORY_IMPL_DECL = CursorKind(19)

# A typedef.
CursorKind.TYPEDEF_DECL = CursorKind(20)

# A C++ class method.
CursorKind.CXX_METHOD = CursorKind(21)

# A C++ namespace.
CursorKind.NAMESPACE = CursorKind(22)

# A linkage specification, e.g. 'extern "C"'.
CursorKind.LINKAGE_SPEC = CursorKind(23)

# A C++ constructor.
CursorKind.CONSTRUCTOR = CursorKind(24)

# A C++ destructor.
CursorKind.DESTRUCTOR = CursorKind(25)

# A C++ conversion function.
CursorKind.CONVERSION_FUNCTION = CursorKind(26)

# A C++ template type parameter
CursorKind.TEMPLATE_TYPE_PARAMETER = CursorKind(27)

# A C++ non-type template paramater.
CursorKind.TEMPLATE_NON_TYPE_PARAMETER = CursorKind(28)

# A C++ template template parameter.
CursorKind.TEMPLATE_TEMPLATE_PARAMTER = CursorKind(29)

# A C++ function template.
CursorKind.FUNCTION_TEMPLATE = CursorKind(30)

# A C++ class template.
CursorKind.CLASS_TEMPLATE = CursorKind(31)

# A C++ class template partial specialization.
CursorKind.CLASS_TEMPLATE_PARTIAL_SPECIALIZATION = CursorKind(32)

# A C++ namespace alias declaration.
CursorKind.NAMESPACE_ALIAS = CursorKind(33)

# A C++ using directive
CursorKind.USING_DIRECTIVE = CursorKind(34)

# A C++ using declaration
CursorKind.USING_DECLARATION = CursorKind(35)

# A Type alias decl.
CursorKind.TYPE_ALIAS_DECL = CursorKind(36)

# A Objective-C synthesize decl
CursorKind.OBJC_SYNTHESIZE_DECL = CursorKind(37)

# A Objective-C dynamic decl
CursorKind.OBJC_DYNAMIC_DECL = CursorKind(38)

# A C++ access specifier decl.
CursorKind.CXX_ACCESS_SPEC_DECL = CursorKind(39)


###
# Reference Kinds

CursorKind.OBJC_SUPER_CLASS_REF = CursorKind(40)
CursorKind.OBJC_PROTOCOL_REF = CursorKind(41)
CursorKind.OBJC_CLASS_REF = CursorKind(42)

# A reference to a type declaration.
#
# A type reference occurs anywhere where a type is named but not
# declared. For example, given:
#   typedef unsigned size_type;
#   size_type size;
#
# The typedef is a declaration of size_type (CXCursor_TypedefDecl),
# while the type of the variable "size" is referenced. The cursor
# referenced by the type of size is the typedef for size_type.
CursorKind.TYPE_REF = CursorKind(43)
CursorKind.CXX_BASE_SPECIFIER = CursorKind(44)

# A reference to a class template, function template, template
# template parameter, or class template partial specialization.
CursorKind.TEMPLATE_REF = CursorKind(45)

# A reference to a namespace or namepsace alias.
CursorKind.NAMESPACE_REF = CursorKind(46)

# A reference to a member of a struct, union, or class that occurs in
# some non-expression context, e.g., a designated initializer.
CursorKind.MEMBER_REF = CursorKind(47)

# A reference to a labeled statement.
CursorKind.LABEL_REF = CursorKind(48)

# A reference toa a set of overloaded functions or function templates
# that has not yet been resolved to a specific function or function template.
CursorKind.OVERLOADED_DECL_REF = CursorKind(49)

###
# Invalid/Error Kinds

CursorKind.INVALID_FILE = CursorKind(70)
CursorKind.NO_DECL_FOUND = CursorKind(71)
CursorKind.NOT_IMPLEMENTED = CursorKind(72)
CursorKind.INVALID_CODE = CursorKind(73)

###
# Expression Kinds

# An expression whose specific kind is not exposed via this interface.
#
# Unexposed expressions have the same operations as any other kind of
# expression; one can extract their location information, spelling, children,
# etc. However, the specific kind of the expression is not reported.
CursorKind.UNEXPOSED_EXPR = CursorKind(100)

# An expression that refers to some value declaration, such as a function,
# varible, or enumerator.
CursorKind.DECL_REF_EXPR = CursorKind(101)

# An expression that refers to a member of a struct, union, class, Objective-C
# class, etc.
CursorKind.MEMBER_REF_EXPR = CursorKind(102)

# An expression that calls a function.
CursorKind.CALL_EXPR = CursorKind(103)

# An expression that sends a message to an Objective-C object or class.
CursorKind.OBJC_MESSAGE_EXPR = CursorKind(104)

# An expression that represents a block literal.
CursorKind.BLOCK_EXPR = CursorKind(105)

# An integer literal.
CursorKind.INTEGER_LITERAL = CursorKind(106)

# A floating point number literal.
CursorKind.FLOATING_LITERAL = CursorKind(107)

# An imaginary number literal.
CursorKind.IMAGINARY_LITERAL = CursorKind(108)

# A string literal.
CursorKind.STRING_LITERAL = CursorKind(109)

# A character literal.
CursorKind.CHARACTER_LITERAL = CursorKind(110)

# A parenthesized expression, e.g. "(1)".
#
# This AST node is only formed if full location information is requested.
CursorKind.PAREN_EXPR = CursorKind(111)

# This represents the unary-expression's (except sizeof and
# alignof).
CursorKind.UNARY_OPERATOR = CursorKind(112)

# [C99 6.5.2.1] Array Subscripting.
CursorKind.ARRAY_SUBSCRIPT_EXPR = CursorKind(113)

# A builtin binary operation expression such as "x + y" or
# "x <= y".
CursorKind.BINARY_OPERATOR = CursorKind(114)

# Compound assignment such as "+=".
CursorKind.COMPOUND_ASSIGNMENT_OPERATOR = CursorKind(115)

# The ?: ternary operator.
CursorKind.CONDITIONAL_OPERATOR = CursorKind(116)

# An explicit cast in C (C99 6.5.4) or a C-style cast in C++
# (C++ [expr.cast]), which uses the syntax (Type)expr.
#
# For example: (int)f.
CursorKind.CSTYLE_CAST_EXPR = CursorKind(117)

# [C99 6.5.2.5]
CursorKind.COMPOUND_LITERAL_EXPR = CursorKind(118)

# Describes an C or C++ initializer list.
CursorKind.INIT_LIST_EXPR = CursorKind(119)

# The GNU address of label extension, representing &&label.
CursorKind.ADDR_LABEL_EXPR = CursorKind(120)

# This is the GNU Statement Expression extension: ({int X=4; X;})
CursorKind.StmtExpr = CursorKind(121)

# Represents a C11 generic selection.
CursorKind.GENERIC_SELECTION_EXPR = CursorKind(122)

# Implements the GNU __null extension, which is a name for a null
# pointer constant that has integral type (e.g., int or long) and is the same
# size and alignment as a pointer.
#
# The __null extension is typically only used by system headers, which define
# NULL as __null in C++ rather than using 0 (which is an integer that may not
# match the size of a pointer).
CursorKind.GNU_NULL_EXPR = CursorKind(123)

# C++'s static_cast<> expression.
CursorKind.CXX_STATIC_CAST_EXPR = CursorKind(124)

# C++'s dynamic_cast<> expression.
CursorKind.CXX_DYNAMIC_CAST_EXPR = CursorKind(125)

# C++'s reinterpret_cast<> expression.
CursorKind.CXX_REINTERPRET_CAST_EXPR = CursorKind(126)

# C++'s const_cast<> expression.
CursorKind.CXX_CONST_CAST_EXPR = CursorKind(127)

# Represents an explicit C++ type conversion that uses "functional"
# notion (C++ [expr.type.conv]).
#
# Example:
# \code
#   x = int(0.5);
# \endcode
CursorKind.CXX_FUNCTIONAL_CAST_EXPR = CursorKind(128)

# A C++ typeid expression (C++ [expr.typeid]).
CursorKind.CXX_TYPEID_EXPR = CursorKind(129)

# [C++ 2.13.5] C++ Boolean Literal.
CursorKind.CXX_BOOL_LITERAL_EXPR = CursorKind(130)

# [C++0x 2.14.7] C++ Pointer Literal.
CursorKind.CXX_NULL_PTR_LITERAL_EXPR = CursorKind(131)

# Represents the "this" expression in C++
CursorKind.CXX_THIS_EXPR = CursorKind(132)

# [C++ 15] C++ Throw Expression.
#
# This handles 'throw' and 'throw' assignment-expression. When
# assignment-expression isn't present, Op will be null.
CursorKind.CXX_THROW_EXPR = CursorKind(133)

# A new expression for memory allocation and constructor calls, e.g:
# "new CXXNewExpr(foo)".
CursorKind.CXX_NEW_EXPR = CursorKind(134)

# A delete expression for memory deallocation and destructor calls,
# e.g. "delete[] pArray".
CursorKind.CXX_DELETE_EXPR = CursorKind(135)

# Represents a unary expression.
CursorKind.CXX_UNARY_EXPR = CursorKind(136)

# ObjCStringLiteral, used for Objective-C string literals i.e. "foo".
CursorKind.OBJC_STRING_LITERAL = CursorKind(137)

# ObjCEncodeExpr, used for in Objective-C.
CursorKind.OBJC_ENCODE_EXPR = CursorKind(138)

# ObjCSelectorExpr used for in Objective-C.
CursorKind.OBJC_SELECTOR_EXPR = CursorKind(139)

# Objective-C's protocol expression.
CursorKind.OBJC_PROTOCOL_EXPR = CursorKind(140)

# An Objective-C "bridged" cast expression, which casts between
# Objective-C pointers and C pointers, transferring ownership in the process.
#
# \code
#   NSString *str = (__bridge_transfer NSString *)CFCreateString();
# \endcode
CursorKind.OBJC_BRIDGE_CAST_EXPR = CursorKind(141)

# Represents a C++0x pack expansion that produces a sequence of
# expressions.
#
# A pack expansion expression contains a pattern (which itself is an
# expression) followed by an ellipsis. For example:
CursorKind.PACK_EXPANSION_EXPR = CursorKind(142)

# Represents an expression that computes the length of a parameter
# pack.
CursorKind.SIZE_OF_PACK_EXPR = CursorKind(143)

# A statement whose specific kind is not exposed via this interface.
#
# Unexposed statements have the same operations as any other kind of statement;
# one can extract their location information, spelling, children, etc. However,
# the specific kind of the statement is not reported.
CursorKind.UNEXPOSED_STMT = CursorKind(200)

# A labelled statement in a function.
CursorKind.LABEL_STMT = CursorKind(201)

# A compound statement
CursorKind.COMPOUND_STMT = CursorKind(202)

# A case statement.
CursorKind.CASE_STMT = CursorKind(203)

# A default statement.
CursorKind.DEFAULT_STMT = CursorKind(204)

# An if statement.
CursorKind.IF_STMT = CursorKind(205)

# A switch statement.
CursorKind.SWITCH_STMT = CursorKind(206)

# A while statement.
CursorKind.WHILE_STMT = CursorKind(207)

# A do statement.
CursorKind.DO_STMT = CursorKind(208)

# A for statement.
CursorKind.FOR_STMT = CursorKind(209)

# A goto statement.
CursorKind.GOTO_STMT = CursorKind(210)

# An indirect goto statement.
CursorKind.INDIRECT_GOTO_STMT = CursorKind(211)

# A continue statement.
CursorKind.CONTINUE_STMT = CursorKind(212)

# A break statement.
CursorKind.BREAK_STMT = CursorKind(213)

# A return statement.
CursorKind.RETURN_STMT = CursorKind(214)

# A GNU-style inline assembler statement.
CursorKind.ASM_STMT = CursorKind(215)

# Objective-C's overall @try-@catch-@finally statement.
CursorKind.OBJC_AT_TRY_STMT = CursorKind(216)

# Objective-C's @catch statement.
CursorKind.OBJC_AT_CATCH_STMT = CursorKind(217)

# Objective-C's @finally statement.
CursorKind.OBJC_AT_FINALLY_STMT = CursorKind(218)

# Objective-C's @throw statement.
CursorKind.OBJC_AT_THROW_STMT = CursorKind(219)

# Objective-C's @synchronized statement.
CursorKind.OBJC_AT_SYNCHRONIZED_STMT = CursorKind(220)

# Objective-C's autorealease pool statement.
CursorKind.OBJC_AUTORELEASE_POOL_STMT = CursorKind(221)

# Objective-C's for collection statement.
CursorKind.OBJC_FOR_COLLECTION_STMT = CursorKind(222)

# C++'s catch statement.
CursorKind.CXX_CATCH_STMT = CursorKind(223)

# C++'s try statement.
CursorKind.CXX_TRY_STMT = CursorKind(224)

# C++'s for (* : *) statement.
CursorKind.CXX_FOR_RANGE_STMT = CursorKind(225)

# Windows Structured Exception Handling's try statement.
CursorKind.SEH_TRY_STMT = CursorKind(226)

# Windows Structured Exception Handling's except statement.
CursorKind.SEH_EXCEPT_STMT = CursorKind(227)

# Windows Structured Exception Handling's finally statement.
CursorKind.SEH_FINALLY_STMT = CursorKind(228)

# The null statement.
CursorKind.NULL_STMT = CursorKind(230)

# Adaptor class for mixing declarations with statements and expressions.
CursorKind.DECL_STMT = CursorKind(231)

###
# Other Kinds

# Cursor that represents the translation unit itself.
#
# The translation unit cursor exists primarily to act as the root cursor for
# traversing the contents of a translation unit.
CursorKind.TRANSLATION_UNIT = CursorKind(300)

###
# Attributes

# An attribute whoe specific kind is note exposed via this interface
CursorKind.UNEXPOSED_ATTR = CursorKind(400)

CursorKind.IB_ACTION_ATTR = CursorKind(401)
CursorKind.IB_OUTLET_ATTR = CursorKind(402)
CursorKind.IB_OUTLET_COLLECTION_ATTR = CursorKind(403)

CursorKind.CXX_FINAL_ATTR = CursorKind(404)
CursorKind.CXX_OVERRIDE_ATTR = CursorKind(405)
CursorKind.ANNOTATE_ATTR = CursorKind(406)
CursorKind.ASM_LABEL_ATTR = CursorKind(407)

###
# Preprocessing
CursorKind.PREPROCESSING_DIRECTIVE = CursorKind(500)
CursorKind.MACRO_DEFINITION = CursorKind(501)
CursorKind.MACRO_INSTANTIATION = CursorKind(502)
CursorKind.INCLUSION_DIRECTIVE = CursorKind(503)

### Cursors ###

class Cursor(Structure):
    """
    The Cursor class represents a reference to an element within the AST. It
    acts as a kind of iterator.
    """
    _fields_ = [("_kind_id", c_int), ("xdata", c_int), ("data", c_void_p * 3)]

    @staticmethod
    def from_location(tu, location):
        # We store a reference to the TU in the instance so the TU won't get
        # collected before the cursor.
        cursor = conf.lib.clang_getCursor(tu, location)
        cursor._tu = tu

        return cursor

    def __eq__(self, other):
        return conf.lib.clang_equalCursors(self, other)

    def __ne__(self, other):
        return not self.__eq__(other)

    def is_definition(self):
        """
        Returns true if the declaration pointed at by the cursor is also a
        definition of that entity.
        """
        return conf.lib.clang_isCursorDefinition(self)

    def is_static_method(self):
        """Returns True if the cursor refers to a C++ member function or member
        function template that is declared 'static'.
        """
        return conf.lib.clang_CXXMethod_isStatic(self)

    def is_virtual_method(self):
        """Returns True if the cursor refers to a C++ member function or member
        function template that is declared 'virtual'.
        """
        return conf.lib.clang_CXXMethod_isVirtual(self)

    def get_definition(self):
        """
        If the cursor is a reference to a declaration or a declaration of
        some entity, return a cursor that points to the definition of that
        entity.
        """
        # TODO: Should probably check that this is either a reference or
        # declaration prior to issuing the lookup.
        return conf.lib.clang_getCursorDefinition(self)

    @property
    def access_specifier(self):
        if self.kind == CursorKind.CXX_BASE_SPECIFIER or self.kind == CursorKind.CXX_ACCESS_SPEC_DECL:
            return CXXAccessSpecifier.from_value(conf.lib.clang_getCXXAccessSpecifier(self))
        else:
            return None

    def get_usr(self):
        """Return the Unified Symbol Resultion (USR) for the entity referenced
        by the given cursor (or None).

        A Unified Symbol Resolution (USR) is a string that identifies a
        particular entity (function, class, variable, etc.) within a
        program. USRs can be compared across translation units to determine,
        e.g., when references in one translation refer to an entity defined in
        another translation unit."""
        return conf.lib.clang_getCursorUSR(self)

    @property
    def kind(self):
        """Return the kind of this cursor."""
        return CursorKind.from_id(self._kind_id)

    @property
    def spelling(self):
        """Return the spelling of the entity pointed at by the cursor."""
        if not self.kind.is_declaration():
            # FIXME: clang_getCursorSpelling should be fixed to not assert on
            # this, for consistency with clang_getCursorUSR.
            return None
        if not hasattr(self, '_spelling'):
            self._spelling = conf.lib.clang_getCursorSpelling(self)

        return self._spelling

    @property
    def displayname(self):
        """
        Return the display name for the entity referenced by this cursor.

        The display name contains extra information that helps identify the cursor,
        such as the parameters of a function or template or the arguments of a
        class template specialization.
        """
        if not hasattr(self, '_displayname'):
            self._displayname = conf.lib.clang_getCursorDisplayName(self)

        return self._displayname

    @property
    def location(self):
        """
        Return the source location (the starting character) of the entity
        pointed at by the cursor.
        """
        if not hasattr(self, '_loc'):
            self._loc = conf.lib.clang_getCursorLocation(self)

        return self._loc

    @property
    def extent(self):
        """
        Return the source range (the range of text) occupied by the entity
        pointed at by the cursor.
        """
        if not hasattr(self, '_extent'):
            self._extent = conf.lib.clang_getCursorExtent(self)

        return self._extent

    @property
    def type(self):
        """
        Retrieve the Type (if any) of the entity pointed at by the cursor.
        """
        if not hasattr(self, '_type'):
            self._type = conf.lib.clang_getCursorType(self)

        return self._type

    @property
    def canonical(self):
        """Return the canonical Cursor corresponding to this Cursor.

        The canonical cursor is the cursor which is representative for the
        underlying entity. For example, if you have multiple forward
        declarations for the same class, the canonical cursor for the forward
        declarations will be identical.
        """
        if not hasattr(self, '_canonical'):
            self._canonical = conf.lib.clang_getCanonicalCursor(self)

        return self._canonical

    @property
    def result_type(self):
        """Retrieve the Type of the result for this Cursor."""
        if not hasattr(self, '_result_type'):
            self._result_type = conf.lib.clang_getResultType(self.type)

        return self._result_type

    @property
    def underlying_typedef_type(self):
        """Return the underlying type of a typedef declaration.

        Returns a Type for the typedef this cursor is a declaration for. If
        the current cursor is not a typedef, this raises.
        """
        if not hasattr(self, '_underlying_type'):
            assert self.kind.is_declaration()
            self._underlying_type = \
              conf.lib.clang_getTypedefDeclUnderlyingType(self)

        return self._underlying_type

    @property
    def enum_type(self):
        """Return the integer type of an enum declaration.

        Returns a Type corresponding to an integer. If the cursor is not for an
        enum, this raises.
        """
        if not hasattr(self, '_enum_type'):
            assert self.kind == CursorKind.ENUM_DECL
            self._enum_type = conf.lib.clang_getEnumDeclIntegerType(self)

        return self._enum_type

    @property
    def enum_value(self):
        """Return the value of an enum constant."""
        if not hasattr(self, '_enum_value'):
            assert self.kind == CursorKind.ENUM_CONSTANT_DECL
            # Figure out the underlying type of the enum to know if it
            # is a signed or unsigned quantity.
            underlying_type = self.type
            if underlying_type.kind == TypeKind.ENUM:
                underlying_type = underlying_type.get_declaration().enum_type
            if underlying_type.kind in (TypeKind.CHAR_U,
                                        TypeKind.UCHAR,
                                        TypeKind.CHAR16,
                                        TypeKind.CHAR32,
                                        TypeKind.USHORT,
                                        TypeKind.UINT,
                                        TypeKind.ULONG,
                                        TypeKind.ULONGLONG,
                                        TypeKind.UINT128):
                self._enum_value = \
                  conf.lib.clang_getEnumConstantDeclUnsignedValue(self)
            else:
                self._enum_value = conf.lib.clang_getEnumConstantDeclValue(self)
        return self._enum_value

    @property
    def objc_type_encoding(self):
        """Return the Objective-C type encoding as a str."""
        if not hasattr(self, '_objc_type_encoding'):
            self._objc_type_encoding = \
              conf.lib.clang_getDeclObjCTypeEncoding(self)

        return self._objc_type_encoding

    @property
    def hash(self):
        """Returns a hash of the cursor as an int."""
        if not hasattr(self, '_hash'):
            self._hash = conf.lib.clang_hashCursor(self)

        return self._hash

    def __hash__(self):
        return self.hash

    @property
    def semantic_parent(self):
        """Return the semantic parent for this cursor."""
        if not hasattr(self, '_semantic_parent'):
            self._semantic_parent = conf.lib.clang_getCursorSemanticParent(self)

        return self._semantic_parent

    @property
    def lexical_parent(self):
        """Return the lexical parent for this cursor."""
        if not hasattr(self, '_lexical_parent'):
            self._lexical_parent = conf.lib.clang_getCursorLexicalParent(self)

        return self._lexical_parent

    @property
    def translation_unit(self):
        """Returns the TranslationUnit to which this Cursor belongs."""
        # If this triggers an AttributeError, the instance was not properly
        # created.
        return self._tu

    def get_children(self):
        """Return an iterator for accessing the children of this cursor."""

        # FIXME: Expose iteration from CIndex, PR6125.
        def visitor(child, parent, children):
            # FIXME: Document this assertion in API.
            # FIXME: There should just be an isNull method.
            assert child != conf.lib.clang_getNullCursor()

            # Create reference to TU so it isn't GC'd before Cursor.
            child._tu = self._tu
            children.append(child)
            return 1 # continue
        children = []
        conf.lib.clang_visitChildren(self, callbacks['cursor_visit'](visitor),
            children)
        return iter(children)

    def get_tokens(self):
        """Obtain Token instances formulating that compose this Cursor.

        This is a generator for Token instances. It returns all tokens which
        occupy the extent this cursor occupies.
        """
        return TokenGroup.get_tokens(self._tu, self.extent)

    @staticmethod
    def from_result(res, fn, args):
        assert isinstance(res, Cursor)
        # FIXME: There should just be an isNull method.
        if res == conf.lib.clang_getNullCursor():
            return None

        # Store a reference to the TU in the Python object so it won't get GC'd
        # before the Cursor.
        tu = None
        for arg in args:
            if isinstance(arg, TranslationUnit):
                tu = arg
                break

            if hasattr(arg, 'translation_unit'):
                tu = arg.translation_unit
                break

        assert tu is not None

        res._tu = tu
        return res

    @staticmethod
    def from_cursor_result(res, fn, args):
        assert isinstance(res, Cursor)
        if res == conf.lib.clang_getNullCursor():
            return None

        res._tu = args[0]._tu
        return res

### Type Kinds ###

class TypeKind(object):
    """
    Describes the kind of type.
    """

    # The unique kind objects, indexed by id.
    _kinds = []
    _name_map = None

    def __init__(self, value):
        if value >= len(TypeKind._kinds):
            TypeKind._kinds += [None] * (value - len(TypeKind._kinds) + 1)
        if TypeKind._kinds[value] is not None:
            raise ValueError,'TypeKind already loaded'
        self.value = value
        TypeKind._kinds[value] = self
        TypeKind._name_map = None

    def from_param(self):
        return self.value

    @property
    def name(self):
        """Get the enumeration name of this cursor kind."""
        if self._name_map is None:
            self._name_map = {}
            for key,value in TypeKind.__dict__.items():
                if isinstance(value,TypeKind):
                    self._name_map[value] = key
        return self._name_map[self]

    @property
    def spelling(self):
        """Retrieve the spelling of this TypeKind."""
        return conf.lib.clang_getTypeKindSpelling(self.value)

    @staticmethod
    def from_id(id):
        if id >= len(TypeKind._kinds) or TypeKind._kinds[id] is None:
            raise ValueError,'Unknown type kind %d' % id
        return TypeKind._kinds[id]

    def __repr__(self):
        return 'TypeKind.%s' % (self.name,)

TypeKind.INVALID = TypeKind(0)
TypeKind.UNEXPOSED = TypeKind(1)
TypeKind.VOID = TypeKind(2)
TypeKind.BOOL = TypeKind(3)
TypeKind.CHAR_U = TypeKind(4)
TypeKind.UCHAR = TypeKind(5)
TypeKind.CHAR16 = TypeKind(6)
TypeKind.CHAR32 = TypeKind(7)
TypeKind.USHORT = TypeKind(8)
TypeKind.UINT = TypeKind(9)
TypeKind.ULONG = TypeKind(10)
TypeKind.ULONGLONG = TypeKind(11)
TypeKind.UINT128 = TypeKind(12)
TypeKind.CHAR_S = TypeKind(13)
TypeKind.SCHAR = TypeKind(14)
TypeKind.WCHAR = TypeKind(15)
TypeKind.SHORT = TypeKind(16)
TypeKind.INT = TypeKind(17)
TypeKind.LONG = TypeKind(18)
TypeKind.LONGLONG = TypeKind(19)
TypeKind.INT128 = TypeKind(20)
TypeKind.FLOAT = TypeKind(21)
TypeKind.DOUBLE = TypeKind(22)
TypeKind.LONGDOUBLE = TypeKind(23)
TypeKind.NULLPTR = TypeKind(24)
TypeKind.OVERLOAD = TypeKind(25)
TypeKind.DEPENDENT = TypeKind(26)
TypeKind.OBJCID = TypeKind(27)
TypeKind.OBJCCLASS = TypeKind(28)
TypeKind.OBJCSEL = TypeKind(29)
TypeKind.COMPLEX = TypeKind(100)
TypeKind.POINTER = TypeKind(101)
TypeKind.BLOCKPOINTER = TypeKind(102)
TypeKind.LVALUEREFERENCE = TypeKind(103)
TypeKind.RVALUEREFERENCE = TypeKind(104)
TypeKind.RECORD = TypeKind(105)
TypeKind.ENUM = TypeKind(106)
TypeKind.TYPEDEF = TypeKind(107)
TypeKind.OBJCINTERFACE = TypeKind(108)
TypeKind.OBJCOBJECTPOINTER = TypeKind(109)
TypeKind.FUNCTIONNOPROTO = TypeKind(110)
TypeKind.FUNCTIONPROTO = TypeKind(111)
TypeKind.CONSTANTARRAY = TypeKind(112)
TypeKind.VECTOR = TypeKind(113)
TypeKind.INCOMPLETEARRAY = TypeKind(114)
TypeKind.VARIABLEARRAY = TypeKind(115)
TypeKind.DEPENDENTSIZEDARRAY = TypeKind(116)
TypeKind.MEMBERPOINTER = TypeKind(117)

class Type(Structure):
    """
    The type of an element in the abstract syntax tree.
    """
    _fields_ = [("_kind_id", c_int), ("data", c_void_p * 2)]

    @property
    def kind(self):
        """Return the kind of this type."""
        return TypeKind.from_id(self._kind_id)

    def argument_types(self):
        """Retrieve a container for the non-variadic arguments for this type.

        The returned object is iterable and indexable. Each item in the
        container is a Type instance.
        """
        class ArgumentsIterator(collections.Sequence):
            def __init__(self, parent):
                self.parent = parent
                self.length = None

            def __len__(self):
                if self.length is None:
                    self.length = conf.lib.clang_getNumArgTypes(self.parent)

                return self.length

            def __getitem__(self, key):
                # FIXME Support slice objects.
                if not isinstance(key, int):
                    raise TypeError("Must supply a non-negative int.")

                if key < 0:
                    raise IndexError("Only non-negative indexes are accepted.")

                if key >= len(self):
                    raise IndexError("Index greater than container length: "
                                     "%d > %d" % ( key, len(self) ))

                result = conf.lib.clang_getArgType(self.parent, key)
                if result.kind == TypeKind.INVALID:
                    raise IndexError("Argument could not be retrieved.")

                return result

        assert self.kind == TypeKind.FUNCTIONPROTO
        return ArgumentsIterator(self)

    @property
    def element_type(self):
        """Retrieve the Type of elements within this Type.

        If accessed on a type that is not an array, complex, or vector type, an
        exception will be raised.
        """
        result = conf.lib.clang_getElementType(self)
        if result.kind == TypeKind.INVALID:
            raise Exception('Element type not available on this type.')

        return result

    @property
    def element_count(self):
        """Retrieve the number of elements in this type.

        Returns an int.

        If the Type is not an array or vector, this raises.
        """
        result = conf.lib.clang_getNumElements(self)
        if result < 0:
            raise Exception('Type does not have elements.')

        return result

    @property
    def translation_unit(self):
        """The TranslationUnit to which this Type is associated."""
        # If this triggers an AttributeError, the instance was not properly
        # instantiated.
        return self._tu

    @staticmethod
    def from_result(res, fn, args):
        assert isinstance(res, Type)

        tu = None
        for arg in args:
            if hasattr(arg, 'translation_unit'):
                tu = arg.translation_unit
                break

        assert tu is not None
        res._tu = tu

        return res

    def get_canonical(self):
        """
        Return the canonical type for a Type.

        Clang's type system explicitly models typedefs and all the
        ways a specific type can be represented.  The canonical type
        is the underlying type with all the "sugar" removed.  For
        example, if 'T' is a typedef for 'int', the canonical type for
        'T' would be 'int'.
        """
        return conf.lib.clang_getCanonicalType(self)

    def is_const_qualified(self):
        """Determine whether a Type has the "const" qualifier set.

        This does not look through typedefs that may have added "const"
        at a different level.
        """
        return conf.lib.clang_isConstQualifiedType(self)

    def is_volatile_qualified(self):
        """Determine whether a Type has the "volatile" qualifier set.

        This does not look through typedefs that may have added "volatile"
        at a different level.
        """
        return conf.lib.clang_isVolatileQualifiedType(self)

    def is_restrict_qualified(self):
        """Determine whether a Type has the "restrict" qualifier set.

        This does not look through typedefs that may have added "restrict" at
        a different level.
        """
        return conf.lib.clang_isRestrictQualifiedType(self)

    def is_function_variadic(self):
        """Determine whether this function Type is a variadic function type."""
        assert self.kind == TypeKind.FUNCTIONPROTO

        return conf.lib.clang_isFunctionTypeVariadic(self)

    def is_pod(self):
        """Determine whether this Type represents plain old data (POD)."""
        return conf.lib.clang_isPODType(self)

    def get_pointee(self):
        """
        For pointer types, returns the type of the pointee.
        """
        return conf.lib.clang_getPointeeType(self)

    def get_declaration(self):
        """
        Return the cursor for the declaration of the given type.
        """
        return conf.lib.clang_getTypeDeclaration(self)

    def get_result(self):
        """
        Retrieve the result type associated with a function type.
        """
        return conf.lib.clang_getResultType(self)

    def get_array_element_type(self):
        """
        Retrieve the type of the elements of the array type.
        """
        return conf.lib.clang_getArrayElementType(self)

    def get_array_size(self):
        """
        Retrieve the size of the constant array.
        """
        return conf.lib.clang_getArraySize(self)

    def __eq__(self, other):
        if type(other) != type(self):
            return False

        return conf.lib.clang_equalTypes(self, other)

    def __ne__(self, other):
        return not self.__eq__(other)

## CIndex Objects ##

# CIndex objects (derived from ClangObject) are essentially lightweight
# wrappers attached to some underlying object, which is exposed via CIndex as
# a void*.

class ClangObject(object):
    """
    A helper for Clang objects. This class helps act as an intermediary for
    the ctypes library and the Clang CIndex library.
    """
    def __init__(self, obj):
        assert isinstance(obj, c_object_p) and obj
        self.obj = self._as_parameter_ = obj

    def from_param(self):
        return self._as_parameter_


class _CXUnsavedFile(Structure):
    """Helper for passing unsaved file arguments."""
    _fields_ = [("name", c_char_p), ("contents", c_char_p), ('length', c_ulong)]

class CompletionChunk:
    class Kind:
        def __init__(self, name):
            self.name = name

        def __str__(self):
            return self.name

        def __repr__(self):
            return "<ChunkKind: %s>" % self

    def __init__(self, completionString, key):
        self.cs = completionString
        self.key = key

    def __repr__(self):
        return "{'" + self.spelling + "', " + str(self.kind) + "}"

    @CachedProperty
    def spelling(self):
        return conf.lib.clang_getCompletionChunkText(self.cs, self.key).spelling

    @CachedProperty
    def kind(self):
        res = conf.lib.clang_getCompletionChunkKind(self.cs, self.key)
        return completionChunkKindMap[res]

    @CachedProperty
    def string(self):
        res = conf.lib.clang_getCompletionChunkCompletionString(self.cs,
                                                                self.key)

        if (res):
          return CompletionString(res)
        else:
          None

    def isKindOptional(self):
      return self.kind == completionChunkKindMap[0]

    def isKindTypedText(self):
      return self.kind == completionChunkKindMap[1]

    def isKindPlaceHolder(self):
      return self.kind == completionChunkKindMap[3]

    def isKindInformative(self):
      return self.kind == completionChunkKindMap[4]

    def isKindResultType(self):
      return self.kind == completionChunkKindMap[15]

completionChunkKindMap = {
            0: CompletionChunk.Kind("Optional"),
            1: CompletionChunk.Kind("TypedText"),
            2: CompletionChunk.Kind("Text"),
            3: CompletionChunk.Kind("Placeholder"),
            4: CompletionChunk.Kind("Informative"),
            5: CompletionChunk.Kind("CurrentParameter"),
            6: CompletionChunk.Kind("LeftParen"),
            7: CompletionChunk.Kind("RightParen"),
            8: CompletionChunk.Kind("LeftBracket"),
            9: CompletionChunk.Kind("RightBracket"),
            10: CompletionChunk.Kind("LeftBrace"),
            11: CompletionChunk.Kind("RightBrace"),
            12: CompletionChunk.Kind("LeftAngle"),
            13: CompletionChunk.Kind("RightAngle"),
            14: CompletionChunk.Kind("Comma"),
            15: CompletionChunk.Kind("ResultType"),
            16: CompletionChunk.Kind("Colon"),
            17: CompletionChunk.Kind("SemiColon"),
            18: CompletionChunk.Kind("Equal"),
            19: CompletionChunk.Kind("HorizontalSpace"),
            20: CompletionChunk.Kind("VerticalSpace")}

class CompletionString(ClangObject):
    class Availability:
        def __init__(self, name):
            self.name = name

        def __str__(self):
            return self.name

        def __repr__(self):
            return "<Availability: %s>" % self

    def __len__(self):
        self.num_chunks

    @CachedProperty
    def num_chunks(self):
        return conf.lib.clang_getNumCompletionChunks(self.obj)

    def __getitem__(self, key):
        if self.num_chunks <= key:
            raise IndexError
        return CompletionChunk(self.obj, key)

    @property
    def priority(self):
        return conf.lib.clang_getCompletionPriority(self.obj)

    @property
    def availability(self):
        res = conf.lib.clang_getCompletionAvailability(self.obj)
        return availabilityKinds[res]

    @property
    def briefComment(self):
        if conf.function_exists("clang_getCompletionBriefComment"):
            return conf.lib.clang_getCompletionBriefComment(self.obj)
        return _CXString()

    def __repr__(self):
        return " | ".join([str(a) for a in self]) \
               + " || Priority: " + str(self.priority) \
               + " || Availability: " + str(self.availability) \
               + " || Brief comment: " + str(self.briefComment.spelling)

availabilityKinds = {
            0: CompletionChunk.Kind("Available"),
            1: CompletionChunk.Kind("Deprecated"),
            2: CompletionChunk.Kind("NotAvailable")}

class CodeCompletionResult(Structure):
    _fields_ = [('cursorKind', c_int), ('completionString', c_object_p)]

    def __repr__(self):
        return str(CompletionString(self.completionString))

    @property
    def kind(self):
        return CursorKind.from_id(self.cursorKind)

    @property
    def string(self):
        return CompletionString(self.completionString)

class CCRStructure(Structure):
    _fields_ = [('results', POINTER(CodeCompletionResult)),
                ('numResults', c_int)]

    def __len__(self):
        return self.numResults

    def __getitem__(self, key):
        if len(self) <= key:
            raise IndexError

        return self.results[key]

class CodeCompletionResults(ClangObject):
    def __init__(self, ptr):
        assert isinstance(ptr, POINTER(CCRStructure)) and ptr
        self.ptr = self._as_parameter_ = ptr

    def from_param(self):
        return self._as_parameter_

    def __del__(self):
        conf.lib.clang_disposeCodeCompleteResults(self)

    @property
    def results(self):
        return self.ptr.contents

    @property
    def diagnostics(self):
        class DiagnosticsItr:
            def __init__(self, ccr):
                self.ccr= ccr

            def __len__(self):
                return int(\
                  conf.lib.clang_codeCompleteGetNumDiagnostics(self.ccr))

            def __getitem__(self, key):
                return conf.lib.clang_codeCompleteGetDiagnostic(self.ccr, key)

        return DiagnosticsItr(self)


class Index(ClangObject):
    """
    The Index type provides the primary interface to the Clang CIndex library,
    primarily by providing an interface for reading and parsing translation
    units.
    """

    @staticmethod
    def create(excludeDecls=False):
        """
        Create a new Index.
        Parameters:
        excludeDecls -- Exclude local declarations from translation units.
        """
        return Index(conf.lib.clang_createIndex(excludeDecls, 0))

    def __del__(self):
        conf.lib.clang_disposeIndex(self)

    def read(self, path):
        """Load a TranslationUnit from the given AST file."""
        return TranslationUnit.from_ast(path, self)

    def parse(self, path, args=None, unsaved_files=None, options = 0):
        """Load the translation unit from the given source code file by running
        clang and generating the AST before loading. Additional command line
        parameters can be passed to clang via the args parameter.

        In-memory contents for files can be provided by passing a list of pairs
        to as unsaved_files, the first item should be the filenames to be mapped
        and the second should be the contents to be substituted for the
        file. The contents may be passed as strings or file objects.

        If an error was encountered during parsing, a TranslationUnitLoadError
        will be raised.
        """
        return TranslationUnit.from_source(path, args, unsaved_files, options,
                                           self)

class CXXAccessSpecifier:
    INVALID_ACCESS = 0
    PUBLIC = 1
    PROTECTED = 2
    PRIVATE = 3

    def __init__(self, value, name):
        self.value = value
        self.name = name

    def __str__(self):
        return 'CXXAccessSpecifier.' + self.name

    @staticmethod
    def from_value(val):
        for item in dir(CXXAccessSpecifier):
           if item.isupper() and getattr(CXXAccessSpecifier, item) == val:
               return CXXAccessSpecifier(val, item)

        return None

    def __cmp__(self, other):
        return cmp(int(self), int(other))

    def __int__(self):
        return self.value

class TranslationUnit(ClangObject):
    """Represents a source code translation unit.

    This is one of the main types in the API. Any time you wish to interact
    with Clang's representation of a source file, you typically start with a
    translation unit.
    """

    # Default parsing mode.
    PARSE_NONE = 0

    # Instruct the parser to create a detailed processing record containing
    # metadata not normally retained.
    PARSE_DETAILED_PROCESSING_RECORD = 1

    # Indicates that the translation unit is incomplete. This is typically used
    # when parsing headers.
    PARSE_INCOMPLETE = 2

    # Instruct the parser to create a pre-compiled preamble for the translation
    # unit. This caches the preamble (included files at top of source file).
    # This is useful if the translation unit will be reparsed and you don't
    # want to incur the overhead of reparsing the preamble.
    PARSE_PRECOMPILED_PREAMBLE = 4

    # Cache code completion information on parse. This adds time to parsing but
    # speeds up code completion.
    PARSE_CACHE_COMPLETION_RESULTS = 8

    # Flags with values 16 and 32 are deprecated and intentionally omitted.

    # Do not parse function bodies. This is useful if you only care about
    # searching for declarations/definitions.
    PARSE_SKIP_FUNCTION_BODIES = 64

    # Used to indicate that brief documentation comments should be included
    # into the set of code completions returned from this translation unit.
    PARSE_INCLUDE_BRIEF_COMMENTS_IN_CODE_COMPLETION = 128

    @classmethod
    def from_source(cls, filename, args=None, unsaved_files=None, options=0,
                    index=None):
        """Create a TranslationUnit by parsing source.

        This is capable of processing source code both from files on the
        filesystem as well as in-memory contents.

        Command-line arguments that would be passed to clang are specified as
        a list via args. These can be used to specify include paths, warnings,
        etc. e.g. ["-Wall", "-I/path/to/include"].

        In-memory file content can be provided via unsaved_files. This is an
        iterable of 2-tuples. The first element is the str filename. The
        second element defines the content. Content can be provided as str
        source code or as file objects (anything with a read() method). If
        a file object is being used, content will be read until EOF and the
        read cursor will not be reset to its original position.

        options is a bitwise or of TranslationUnit.PARSE_XXX flags which will
        control parsing behavior.

        index is an Index instance to utilize. If not provided, a new Index
        will be created for this TranslationUnit.

        To parse source from the filesystem, the filename of the file to parse
        is specified by the filename argument. Or, filename could be None and
        the args list would contain the filename(s) to parse.

        To parse source from an in-memory buffer, set filename to the virtual
        filename you wish to associate with this source (e.g. "test.c"). The
        contents of that file are then provided in unsaved_files.

        If an error occurs, a TranslationUnitLoadError is raised.

        Please note that a TranslationUnit with parser errors may be returned.
        It is the caller's responsibility to check tu.diagnostics for errors.

        Also note that Clang infers the source language from the extension of
        the input filename. If you pass in source code containing a C++ class
        declaration with the filename "test.c" parsing will fail.
        """
        if args is None:
            args = []

        if unsaved_files is None:
            unsaved_files = []

        if index is None:
            index = Index.create()

        args_array = None
        if len(args) > 0:
            args_array = (c_char_p * len(args))(* args)

        unsaved_array = None
        if len(unsaved_files) > 0:
            unsaved_array = (_CXUnsavedFile * len(unsaved_files))()
            for i, (name, contents) in enumerate(unsaved_files):
                if hasattr(contents, "read"):
                    contents = contents.read()

                unsaved_array[i].name = name
                unsaved_array[i].contents = contents
                unsaved_array[i].length = len(contents)

        ptr = conf.lib.clang_parseTranslationUnit(index, filename, args_array,
                                    len(args), unsaved_array,
                                    len(unsaved_files), options)

        if ptr is None:
            raise TranslationUnitLoadError("Error parsing translation unit.")

        return cls(ptr, index=index)

    @classmethod
    def from_ast_file(cls, filename, index=None):
        """Create a TranslationUnit instance from a saved AST file.

        A previously-saved AST file (provided with -emit-ast or
        TranslationUnit.save()) is loaded from the filename specified.

        If the file cannot be loaded, a TranslationUnitLoadError will be
        raised.

        index is optional and is the Index instance to use. If not provided,
        a default Index will be created.
        """
        if index is None:
            index = Index.create()

        ptr = conf.lib.clang_createTranslationUnit(index, filename)
        if ptr is None:
            raise TranslationUnitLoadError(filename)

        return cls(ptr=ptr, index=index)

    def __init__(self, ptr, index):
        """Create a TranslationUnit instance.

        TranslationUnits should be created using one of the from_* @classmethod
        functions above. __init__ is only called internally.
        """
        assert isinstance(index, Index)

        ClangObject.__init__(self, ptr)

    def __del__(self):
        conf.lib.clang_disposeTranslationUnit(self)

    @property
    def cursor(self):
        """Retrieve the cursor that represents the given translation unit."""
        return conf.lib.clang_getTranslationUnitCursor(self)

    @property
    def spelling(self):
        """Get the original translation unit source file name."""
        return conf.lib.clang_getTranslationUnitSpelling(self)

    def get_includes(self):
        """
        Return an iterable sequence of FileInclusion objects that describe the
        sequence of inclusions in a translation unit. The first object in
        this sequence is always the input file. Note that this method will not
        recursively iterate over header files included through precompiled
        headers.
        """
        def visitor(fobj, lptr, depth, includes):
            if depth > 0:
                loc = lptr.contents
                includes.append(FileInclusion(loc.file, File(fobj), loc, depth))

        # Automatically adapt CIndex/ctype pointers to python objects
        includes = []
        conf.lib.clang_getInclusions(self,
                callbacks['translation_unit_includes'](visitor), includes)

        return iter(includes)

    def get_file(self, filename):
        """Obtain a File from this translation unit."""

        return File.from_name(self, filename)

    def get_location(self, filename, position):
        """Obtain a SourceLocation for a file in this translation unit.

        The position can be specified by passing:

          - Integer file offset. Initial file offset is 0.
          - 2-tuple of (line number, column number). Initial file position is
            (0, 0)
        """
        f = self.get_file(filename)

        if isinstance(position, int):
            return SourceLocation.from_offset(self, f, position)

        return SourceLocation.from_position(self, f, position[0], position[1])

    def get_extent(self, filename, locations):
        """Obtain a SourceRange from this translation unit.

        The bounds of the SourceRange must ultimately be defined by a start and
        end SourceLocation. For the locations argument, you can pass:

          - 2 SourceLocation instances in a 2-tuple or list.
          - 2 int file offsets via a 2-tuple or list.
          - 2 2-tuple or lists of (line, column) pairs in a 2-tuple or list.

        e.g.

        get_extent('foo.c', (5, 10))
        get_extent('foo.c', ((1, 1), (1, 15)))
        """
        f = self.get_file(filename)

        if len(locations) < 2:
            raise Exception('Must pass object with at least 2 elements')

        start_location, end_location = locations

        if hasattr(start_location, '__len__'):
            start_location = SourceLocation.from_position(self, f,
                start_location[0], start_location[1])
        elif isinstance(start_location, int):
            start_location = SourceLocation.from_offset(self, f,
                start_location)

        if hasattr(end_location, '__len__'):
            end_location = SourceLocation.from_position(self, f,
                end_location[0], end_location[1])
        elif isinstance(end_location, int):
            end_location = SourceLocation.from_offset(self, f, end_location)

        assert isinstance(start_location, SourceLocation)
        assert isinstance(end_location, SourceLocation)

        return SourceRange.from_locations(start_location, end_location)

    @property
    def diagnostics(self):
        """
        Return an iterable (and indexable) object containing the diagnostics.
        """
        class DiagIterator:
            def __init__(self, tu):
                self.tu = tu

            def __len__(self):
                return int(conf.lib.clang_getNumDiagnostics(self.tu))

            def __getitem__(self, key):
                diag = conf.lib.clang_getDiagnostic(self.tu, key)
                if not diag:
                    raise IndexError
                return Diagnostic(diag)

        return DiagIterator(self)

    def reparse(self, unsaved_files=None, options=0):
        """
        Reparse an already parsed translation unit.

        In-memory contents for files can be provided by passing a list of pairs
        as unsaved_files, the first items should be the filenames to be mapped
        and the second should be the contents to be substituted for the
        file. The contents may be passed as strings or file objects.
        """
        if unsaved_files is None:
            unsaved_files = []

        unsaved_files_array = 0
        if len(unsaved_files):
            unsaved_files_array = (_CXUnsavedFile * len(unsaved_files))()
            for i,(name,value) in enumerate(unsaved_files):
                if not isinstance(value, str):
                    # FIXME: It would be great to support an efficient version
                    # of this, one day.
                    value = value.read()
                    print value
                if not isinstance(value, str):
                    raise TypeError,'Unexpected unsaved file contents.'
                unsaved_files_array[i].name = name
                unsaved_files_array[i].contents = value
                unsaved_files_array[i].length = len(value)
        ptr = conf.lib.clang_reparseTranslationUnit(self, len(unsaved_files),
                unsaved_files_array, options)

    def save(self, filename):
        """Saves the TranslationUnit to a file.

        This is equivalent to passing -emit-ast to the clang frontend. The
        saved file can be loaded back into a TranslationUnit. Or, if it
        corresponds to a header, it can be used as a pre-compiled header file.

        If an error occurs while saving, a TranslationUnitSaveError is raised.
        If the error was TranslationUnitSaveError.ERROR_INVALID_TU, this means
        the constructed TranslationUnit was not valid at time of save. In this
        case, the reason(s) why should be available via
        TranslationUnit.diagnostics().

        filename -- The path to save the translation unit to.
        """
        options = conf.lib.clang_defaultSaveOptions(self)
        result = int(conf.lib.clang_saveTranslationUnit(self, filename,
                                                        options))
        if result != 0:
            raise TranslationUnitSaveError(result,
                'Error saving TranslationUnit.')

    def codeComplete(self, path, line, column, unsaved_files=None,
                     include_macros=False, include_code_patterns=False,
                     include_brief_comments=False):
        """
        Code complete in this translation unit.

        In-memory contents for files can be provided by passing a list of pairs
        as unsaved_files, the first items should be the filenames to be mapped
        and the second should be the contents to be substituted for the
        file. The contents may be passed as strings or file objects.
        """
        options = 0

        if include_macros:
            options += 1

        if include_code_patterns:
            options += 2

        if include_brief_comments:
            options += 4

        if unsaved_files is None:
            unsaved_files = []

        unsaved_files_array = 0
        if len(unsaved_files):
            unsaved_files_array = (_CXUnsavedFile * len(unsaved_files))()
            for i,(name,value) in enumerate(unsaved_files):
                if not isinstance(value, str):
                    # FIXME: It would be great to support an efficient version
                    # of this, one day.
                    value = value.read()
                    print value
                if not isinstance(value, str):
                    raise TypeError,'Unexpected unsaved file contents.'
                unsaved_files_array[i].name = name
                unsaved_files_array[i].contents = value
                unsaved_files_array[i].length = len(value)
        ptr = conf.lib.clang_codeCompleteAt(self, path, line, column,
                unsaved_files_array, len(unsaved_files), options)
        if ptr:
            return CodeCompletionResults(ptr)
        return None

    def get_tokens(self, locations=None, extent=None):
        """Obtain tokens in this translation unit.

        This is a generator for Token instances. The caller specifies a range
        of source code to obtain tokens for. The range can be specified as a
        2-tuple of SourceLocation or as a SourceRange. If both are defined,
        behavior is undefined.
        """
        if locations is not None:
            extent = SourceRange(start=locations[0], end=locations[1])

        return TokenGroup.get_tokens(self, extent)

class File(ClangObject):
    """
    The File class represents a particular source file that is part of a
    translation unit.
    """

    @staticmethod
    def from_name(translation_unit, file_name):
        """Retrieve a file handle within the given translation unit."""
        return File(conf.lib.clang_getFile(translation_unit, file_name))

    @property
    def name(self):
        """Return the complete file and path name of the file."""
        return conf.lib.clang_getCString(conf.lib.clang_getFileName(self))

    @property
    def time(self):
        """Return the last modification time of the file."""
        return conf.lib.clang_getFileTime(self)

    def __str__(self):
        return self.name

    def __repr__(self):
        return "<File: %s>" % (self.name)

    @staticmethod
    def from_cursor_result(res, fn, args):
        assert isinstance(res, File)

        # Copy a reference to the TranslationUnit to prevent premature GC.
        res._tu = args[0]._tu
        return res

class FileInclusion(object):
    """
    The FileInclusion class represents the inclusion of one source file by
    another via a '#include' directive or as the input file for the translation
    unit. This class provides information about the included file, the including
    file, the location of the '#include' directive and the depth of the included
    file in the stack. Note that the input file has depth 0.
    """

    def __init__(self, src, tgt, loc, depth):
        self.source = src
        self.include = tgt
        self.location = loc
        self.depth = depth

    @property
    def is_input_file(self):
        """True if the included file is the input file."""
        return self.depth == 0

class CompilationDatabaseError(Exception):
    """Represents an error that occurred when working with a CompilationDatabase

    Each error is associated to an enumerated value, accessible under
    e.cdb_error. Consumers can compare the value with one of the ERROR_
    constants in this class.
    """

    # An unknown error occured
    ERROR_UNKNOWN = 0

    # The database could not be loaded
    ERROR_CANNOTLOADDATABASE = 1

    def __init__(self, enumeration, message):
        assert isinstance(enumeration, int)

        if enumeration > 1:
            raise Exception("Encountered undefined CompilationDatabase error "
                            "constant: %d. Please file a bug to have this "
                            "value supported." % enumeration)

        self.cdb_error = enumeration
        Exception.__init__(self, 'Error %d: %s' % (enumeration, message))

class CompileCommand(object):
    """Represents the compile command used to build a file"""
    def __init__(self, cmd, ccmds):
        self.cmd = cmd
        # Keep a reference to the originating CompileCommands
        # to prevent garbage collection
        self.ccmds = ccmds

    @property
    def directory(self):
        """Get the working directory for this CompileCommand"""
        return conf.lib.clang_CompileCommand_getDirectory(self.cmd)

    @property
    def arguments(self):
        """
        Get an iterable object providing each argument in the
        command line for the compiler invocation as a _CXString.

        Invariant : the first argument is the compiler executable
        """
        length = conf.lib.clang_CompileCommand_getNumArgs(self.cmd)
        for i in xrange(length):
            yield conf.lib.clang_CompileCommand_getArg(self.cmd, i)

class CompileCommands(object):
    """
    CompileCommands is an iterable object containing all CompileCommand
    that can be used for building a specific file.
    """
    def __init__(self, ccmds):
        self.ccmds = ccmds

    def __del__(self):
        conf.lib.clang_CompileCommands_dispose(self.ccmds)

    def __len__(self):
        return int(conf.lib.clang_CompileCommands_getSize(self.ccmds))

    def __getitem__(self, i):
        cc = conf.lib.clang_CompileCommands_getCommand(self.ccmds, i)
        if not cc:
            raise IndexError
        return CompileCommand(cc, self)

    @staticmethod
    def from_result(res, fn, args):
        if not res:
            return None
        return CompileCommands(res)

class CompilationDatabase(ClangObject):
    """
    The CompilationDatabase is a wrapper class around
    clang::tooling::CompilationDatabase

    It enables querying how a specific source file can be built.
    """

    def __del__(self):
        conf.lib.clang_CompilationDatabase_dispose(self)

    @staticmethod
    def from_result(res, fn, args):
        if not res:
            raise CompilationDatabaseError(0,
                                           "CompilationDatabase loading failed")
        return CompilationDatabase(res)

    @staticmethod
    def fromDirectory(buildDir):
        """Builds a CompilationDatabase from the database found in buildDir"""
        errorCode = c_uint()
        try:
            cdb = conf.lib.clang_CompilationDatabase_fromDirectory(buildDir,
                byref(errorCode))
        except CompilationDatabaseError as e:
            raise CompilationDatabaseError(int(errorCode.value),
                                           "CompilationDatabase loading failed")
        return cdb

    def getCompileCommands(self, filename):
        """
        Get an iterable object providing all the CompileCommands available to
        build filename. Returns None if filename is not found in the database.
        """
        return conf.lib.clang_CompilationDatabase_getCompileCommands(self,
                                                                     filename)

class Token(Structure):
    """Represents a single token from the preprocessor.

    Tokens are effectively segments of source code. Source code is first parsed
    into tokens before being converted into the AST and Cursors.

    Tokens are obtained from parsed TranslationUnit instances. You currently
    can't create tokens manually.
    """
    _fields_ = [
        ('int_data', c_uint * 4),
        ('ptr_data', c_void_p)
    ]

    @property
    def spelling(self):
        """The spelling of this token.

        This is the textual representation of the token in source.
        """
        return conf.lib.clang_getTokenSpelling(self._tu, self)

    @property
    def kind(self):
        """Obtain the TokenKind of the current token."""
        return TokenKind.from_value(conf.lib.clang_getTokenKind(self))

    @property
    def location(self):
        """The SourceLocation this Token occurs at."""
        return conf.lib.clang_getTokenLocation(self._tu, self)

    @property
    def extent(self):
        """The SourceRange this Token occupies."""
        return conf.lib.clang_getTokenExtent(self._tu, self)

    @property
    def cursor(self):
        """The Cursor this Token corresponds to."""
        cursor = Cursor()

        conf.lib.clang_annotateTokens(self._tu, byref(self), 1, byref(cursor))

        return cursor

# Now comes the plumbing to hook up the C library.

# Register callback types in common container.
callbacks['translation_unit_includes'] = CFUNCTYPE(None, c_object_p,
        POINTER(SourceLocation), c_uint, py_object)
callbacks['cursor_visit'] = CFUNCTYPE(c_int, Cursor, Cursor, py_object)

# Functions strictly alphabetical order.
functionList = [
  ("clang_annotateTokens",
   [TranslationUnit, POINTER(Token), c_uint, POINTER(Cursor)]),

  ("clang_codeCompleteAt",
   [TranslationUnit, c_char_p, c_int, c_int, c_void_p, c_int, c_int],
   POINTER(CCRStructure)),

  ("clang_codeCompleteGetDiagnostic",
   [CodeCompletionResults, c_int],
   Diagnostic),

  ("clang_codeCompleteGetNumDiagnostics",
   [CodeCompletionResults],
   c_int),

  ("clang_createIndex",
   [c_int, c_int],
   c_object_p),

  ("clang_createTranslationUnit",
   [Index, c_char_p],
   c_object_p),

  ("clang_CXXMethod_isStatic",
   [Cursor],
   bool),

  ("clang_CXXMethod_isVirtual",
   [Cursor],
   bool),

  ("clang_defaultSaveOptions",
   [TranslationUnit],
   c_uint),

  ("clang_disposeCodeCompleteResults",
   [CodeCompletionResults]),

# ("clang_disposeCXTUResourceUsage",
#  [CXTUResourceUsage]),

  ("clang_disposeDiagnostic",
   [Diagnostic]),

  ("clang_defaultDiagnosticDisplayOptions",
   [],
   c_uint),

  ("clang_formatDiagnostic",
   [Diagnostic, c_uint],
   _CXString,
   _CXString.from_result),

  ("clang_disposeIndex",
   [Index]),

  ("clang_disposeString",
   [_CXString]),

  ("clang_disposeTokens",
   [TranslationUnit, POINTER(Token), c_uint]),

  ("clang_disposeTranslationUnit",
   [TranslationUnit]),

  ("clang_equalCursors",
   [Cursor, Cursor],
   bool),

  ("clang_equalLocations",
   [SourceLocation, SourceLocation],
   bool),

  ("clang_equalRanges",
   [SourceRange, SourceRange],
   bool),

  ("clang_equalTypes",
   [Type, Type],
   bool),

  ("clang_getArgType",
   [Type, c_uint],
   Type,
   Type.from_result),

  ("clang_getArrayElementType",
   [Type],
   Type,
   Type.from_result),

  ("clang_getArraySize",
   [Type],
   c_longlong),

  ("clang_getCanonicalCursor",
   [Cursor],
   Cursor,
   Cursor.from_cursor_result),

  ("clang_getCanonicalType",
   [Type],
   Type,
   Type.from_result),

  ("clang_getCompletionAvailability",
   [c_void_p],
   c_int),

  ("clang_getCompletionChunkCompletionString",
   [c_void_p, c_int],
   c_object_p),

  ("clang_getCompletionChunkKind",
   [c_void_p, c_int],
   c_int),

  ("clang_getCompletionChunkText",
   [c_void_p, c_int],
   _CXString),

  ("clang_getCompletionPriority",
   [c_void_p],
   c_int),

  ("clang_getCString",
   [_CXString],
   c_char_p),

  ("clang_getCursor",
   [TranslationUnit, SourceLocation],
   Cursor),

  ("clang_getCursorDefinition",
   [Cursor],
   Cursor,
   Cursor.from_result),

  ("clang_getCursorDisplayName",
   [Cursor],
   _CXString,
   _CXString.from_result),

  ("clang_getCursorExtent",
   [Cursor],
   SourceRange),

  ("clang_getCursorLexicalParent",
   [Cursor],
   Cursor,
   Cursor.from_cursor_result),

  ("clang_getCursorLocation",
   [Cursor],
   SourceLocation),

  ("clang_getCursorReferenced",
   [Cursor],
   Cursor,
   Cursor.from_result),

  ("clang_getCursorReferenceNameRange",
   [Cursor, c_uint, c_uint],
   SourceRange),

  ("clang_getCursorSemanticParent",
   [Cursor],
   Cursor,
   Cursor.from_cursor_result),

  ("clang_getCursorSpelling",
   [Cursor],
   _CXString,
   _CXString.from_result),

  ("clang_getCursorType",
   [Cursor],
   Type,
   Type.from_result),

  ("clang_getCursorUSR",
   [Cursor],
   _CXString,
   _CXString.from_result),

# ("clang_getCXTUResourceUsage",
#  [TranslationUnit],
#  CXTUResourceUsage),

  ("clang_getCXXAccessSpecifier",
   [Cursor],
   c_uint),

  ("clang_getDeclObjCTypeEncoding",
   [Cursor],
   _CXString,
   _CXString.from_result),

  ("clang_getDiagnostic",
   [c_object_p, c_uint],
   c_object_p),

  ("clang_getDiagnosticCategory",
   [Diagnostic],
   c_uint),

  ("clang_getDiagnosticCategoryName",
   [c_uint],
   _CXString,
   _CXString.from_result),

  ("clang_getDiagnosticFixIt",
   [Diagnostic, c_uint, POINTER(SourceRange)],
   _CXString,
   _CXString.from_result),

  ("clang_getDiagnosticLocation",
   [Diagnostic],
   SourceLocation),

  ("clang_getDiagnosticNumFixIts",
   [Diagnostic],
   c_uint),

  ("clang_getDiagnosticNumRanges",
   [Diagnostic],
   c_uint),

  ("clang_getDiagnosticOption",
   [Diagnostic, POINTER(_CXString)],
   _CXString,
   _CXString.from_result),

  ("clang_getDiagnosticRange",
   [Diagnostic, c_uint],
   SourceRange),

  ("clang_getDiagnosticSeverity",
   [Diagnostic],
   c_int),

  ("clang_getDiagnosticSpelling",
   [Diagnostic],
   _CXString,
   _CXString.from_result),

  ("clang_getElementType",
   [Type],
   Type,
   Type.from_result),

  ("clang_getEnumConstantDeclUnsignedValue",
   [Cursor],
   c_ulonglong),

  ("clang_getEnumConstantDeclValue",
   [Cursor],
   c_longlong),

  ("clang_getEnumDeclIntegerType",
   [Cursor],
   Type,
   Type.from_result),

  ("clang_getFile",
   [TranslationUnit, c_char_p],
   c_object_p),

  ("clang_getFileName",
   [File],
   _CXString), # TODO go through _CXString.from_result?

  ("clang_getFileTime",
   [File],
   c_uint),

  ("clang_getIBOutletCollectionType",
   [Cursor],
   Type,
   Type.from_result),

  ("clang_getIncludedFile",
   [Cursor],
   File,
   File.from_cursor_result),

  ("clang_getInclusions",
   [TranslationUnit, callbacks['translation_unit_includes'], py_object]),

  ("clang_getInstantiationLocation",
   [SourceLocation, POINTER(c_object_p), POINTER(c_uint), POINTER(c_uint),
    POINTER(c_uint)]),

  ("clang_getLocation",
   [TranslationUnit, File, c_uint, c_uint],
   SourceLocation),

  ("clang_getLocationForOffset",
   [TranslationUnit, File, c_uint],
   SourceLocation),

  ("clang_getNullCursor",
   None,
   Cursor),

  ("clang_getNumArgTypes",
   [Type],
   c_uint),

  ("clang_getNumCompletionChunks",
   [c_void_p],
   c_int),

  ("clang_getNumDiagnostics",
   [c_object_p],
   c_uint),

  ("clang_getNumElements",
   [Type],
   c_longlong),

  ("clang_getNumOverloadedDecls",
   [Cursor],
   c_uint),

  ("clang_getOverloadedDecl",
   [Cursor, c_uint],
   Cursor,
   Cursor.from_cursor_result),

  ("clang_getPointeeType",
   [Type],
   Type,
   Type.from_result),

  ("clang_getRange",
   [SourceLocation, SourceLocation],
   SourceRange),

  ("clang_getRangeEnd",
   [SourceRange],
   SourceLocation),

  ("clang_getRangeStart",
   [SourceRange],
   SourceLocation),

  ("clang_getResultType",
   [Type],
   Type,
   Type.from_result),

  ("clang_getSpecializedCursorTemplate",
   [Cursor],
   Cursor,
   Cursor.from_cursor_result),

  ("clang_getTemplateCursorKind",
   [Cursor],
   c_uint),

  ("clang_getTokenExtent",
   [TranslationUnit, Token],
   SourceRange),

  ("clang_getTokenKind",
   [Token],
   c_uint),

  ("clang_getTokenLocation",
   [TranslationUnit, Token],
   SourceLocation),

  ("clang_getTokenSpelling",
   [TranslationUnit, Token],
   _CXString,
   _CXString.from_result),

  ("clang_getTranslationUnitCursor",
   [TranslationUnit],
   Cursor,
   Cursor.from_result),

  ("clang_getTranslationUnitSpelling",
   [TranslationUnit],
   _CXString,
   _CXString.from_result),

  ("clang_getTUResourceUsageName",
   [c_uint],
   c_char_p),

  ("clang_getTypeDeclaration",
   [Type],
   Cursor,
   Cursor.from_result),

  ("clang_getTypedefDeclUnderlyingType",
   [Cursor],
   Type,
   Type.from_result),

  ("clang_getTypeKindSpelling",
   [c_uint],
   _CXString,
   _CXString.from_result),

  ("clang_hashCursor",
   [Cursor],
   c_uint),

  ("clang_isAttribute",
   [CursorKind],
   bool),

  ("clang_isConstQualifiedType",
   [Type],
   bool),

  ("clang_isCursorDefinition",
   [Cursor],
   bool),

  ("clang_isDeclaration",
   [CursorKind],
   bool),

  ("clang_isExpression",
   [CursorKind],
   bool),

  ("clang_isFileMultipleIncludeGuarded",
   [TranslationUnit, File],
   bool),

  ("clang_isFunctionTypeVariadic",
   [Type],
   bool),

  ("clang_isInvalid",
   [CursorKind],
   bool),

  ("clang_isPODType",
   [Type],
   bool),

  ("clang_isPreprocessing",
   [CursorKind],
   bool),

  ("clang_isReference",
   [CursorKind],
   bool),

  ("clang_isRestrictQualifiedType",
   [Type],
   bool),

  ("clang_isStatement",
   [CursorKind],
   bool),

  ("clang_isTranslationUnit",
   [CursorKind],
   bool),

  ("clang_isUnexposed",
   [CursorKind],
   bool),

  ("clang_isVirtualBase",
   [Cursor],
   bool),

  ("clang_isVolatileQualifiedType",
   [Type],
   bool),

  ("clang_parseTranslationUnit",
   [Index, c_char_p, c_void_p, c_int, c_void_p, c_int, c_int],
   c_object_p),

  ("clang_reparseTranslationUnit",
   [TranslationUnit, c_int, c_void_p, c_int],
   c_int),

  ("clang_saveTranslationUnit",
   [TranslationUnit, c_char_p, c_uint],
   c_int),

  ("clang_tokenize",
   [TranslationUnit, SourceRange, POINTER(POINTER(Token)), POINTER(c_uint)]),

  ("clang_visitChildren",
   [Cursor, callbacks['cursor_visit'], py_object],
   c_uint),
]

class LibclangError(Exception):
    def __init__(self, message):
        self.m = message

    def __str__(self):
        return self.m

def register_function(lib, item, ignore_errors):
    # A function may not exist, if these bindings are used with an older or
    # incompatible version of libclang.so.
    try:
        func = getattr(lib, item[0])
    except AttributeError as e:
        msg = str(e) + ". Please ensure that your python bindings are "\
                       "compatible with your libclang.so version."
        if ignore_errors:
            return
        raise LibclangError(msg)

    if len(item) >= 2:
        func.argtypes = item[1]

    if len(item) >= 3:
        func.restype = item[2]

    if len(item) == 4:
        func.errcheck = item[3]

def register_functions(lib, ignore_errors):
    """Register function prototypes with a libclang library instance.

    This must be called as part of library instantiation so Python knows how
    to call out to the shared library.
    """

    def register(item):
        return register_function(lib, item, ignore_errors)

    map(register, functionList)

class Config:
    library_path = None
    library_file = None
    compatibility_check = True
    loaded = False

    @staticmethod
    def set_library_path(path):
        """Set the path in which to search for libclang"""
        if Config.loaded:
            raise Exception("library path must be set before before using " \
                            "any other functionalities in libclang.")

        Config.library_path = path

    @staticmethod
    def set_library_file(file):
        """Set the exact location of libclang from"""
        if Config.loaded:
            raise Exception("library file must be set before before using " \
                            "any other functionalities in libclang.")

        Config.library_file = path

    @staticmethod
    def set_compatibility_check(check_status):
        """ Perform compatibility check when loading libclang

        The python bindings are only tested and evaluated with the version of
        libclang they are provided with. To ensure correct behavior a (limited)
        compatibility check is performed when loading the bindings. This check
        will throw an exception, as soon as it fails.

        In case these bindings are used with an older version of libclang, parts
        that have been stable between releases may still work. Users of the
        python bindings can disable the compatibility check. This will cause
        the python bindings to load, even though they are written for a newer
        version of libclang. Failures now arise if unsupported or incompatible
        features are accessed. The user is required to test himself if the
        features he is using are available and compatible between different
        libclang versions.
        """
        if Config.loaded:
            raise Exception("compatibility_check must be set before before " \
                            "using any other functionalities in libclang.")

        Config.compatibility_check = check_status

    @CachedProperty
    def lib(self):
        lib = self.get_cindex_library()
        register_functions(lib, not Config.compatibility_check)
        Config.loaded = True
        return lib

    def get_filename(self):
        if Config.library_file:
            return Config.library_file

        import platform
        name = platform.system()

        if name == 'Darwin':
            file = 'libclang.dylib'
        elif name == 'Windows':
            file = 'libclang.dll'
        else:
            file = 'libclang.so'

        if Config.library_path:
            file = Config.library_path + '/' + file

        return file

    def get_cindex_library(self):
        try:
            library = cdll.LoadLibrary(self.get_filename())
        except OSError as e:
            msg = str(e) + ". To provide a path to libclang use " \
                           "Config.set_library_path() or " \
                           "Config.set_library_file()."
            raise LibclangError(msg)

        return library

    def function_exists(self, name):
        try:
            getattr(self.lib, name)
        except AttributeError:
            return False

        return True

def register_enumerations():
    for name, value in enumerations.TokenKinds:
        TokenKind.register(value, name)

conf = Config()
register_enumerations()

__all__ = [
    'Config',
    'CodeCompletionResults',
    'CompilationDatabase',
    'CompileCommands',
    'CompileCommand',
    'CursorKind',
    'Cursor',
    'Diagnostic',
    'File',
    'FixIt',
    'Index',
    'SourceLocation',
    'SourceRange',
    'TokenKind',
    'Token',
    'TranslationUnitLoadError',
    'TranslationUnit',
    'TypeKind',
    'Type',
]

########NEW FILE########
__FILENAME__ = enumerations
#===- enumerations.py - Python Enumerations ------------------*- python -*--===#
#
#                     The LLVM Compiler Infrastructure
#
# This file is distributed under the University of Illinois Open Source
# License. See LICENSE.TXT for details.
#
#===------------------------------------------------------------------------===#

"""
Clang Enumerations
==================

This module provides static definitions of enumerations that exist in libclang.

Enumerations are typically defined as a list of tuples. The exported values are
typically munged into other types or classes at module load time.

All enumerations are centrally defined in this file so they are all grouped
together and easier to audit. And, maybe even one day this file will be
automatically generated by scanning the libclang headers!
"""

# Maps to CXTokenKind. Note that libclang maintains a separate set of token
# enumerations from the C++ API.
TokenKinds = [
    ('PUNCTUATION', 0),
    ('KEYWORD', 1),
    ('IDENTIFIER', 2),
    ('LITERAL', 3),
    ('COMMENT', 4),
]

__all__ = ['TokenKinds']

########NEW FILE########
__FILENAME__ = cmdgenerate
# This file is part of cldoc.  cldoc is free software: you can
# redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
from __future__ import absolute_import

import sys, os, argparse, tempfile, subprocess, shutil

def run_generate(t, opts):
    if opts.type != 'html' and opts.type != 'xml':
        return

    from . import generators

    generator = generators.Xml(t, opts)

    if opts.type == 'html' and opts.static:
        baseout = tempfile.mkdtemp()
    else:
        baseout = opts.output

    xmlout = os.path.join(baseout, 'xml')
    generator.generate(xmlout)

    if opts.type == 'html':
        generators.Html(t).generate(baseout, opts.static, opts.custom_js, opts.custom_css)

        if opts.static:
            # Call node to generate the static website at the actual output
            # directory
            datadir = os.path.join(os.path.dirname(__file__), 'data')
            jsfile = os.path.join(datadir, 'staticsite', 'staticsite.js')

            print('Generating static website...')
            failed = False

            try:
                subprocess.call(['nodejs', jsfile, baseout, opts.output])
            except OSError as e:
                if e.errno == 2:
                    try:
                        subprocess.call(['node', jsfile, baseout, opts.output])
                    except OSError:
                        failed = True
                else:
                    failed = True

            if failed:
                sys.stderr.write("\nFailed to call static site generator. The static site generator uses node.js (http://nodejs.org/). Please make sure you have node installed on your system and try again.\n")

                shutil.rmtree(baseout)
                sys.exit(1)

            shutil.rmtree(baseout)


def run(args):
    try:
        sep = args.index('--')
    except ValueError:
        if not '--help' in args:
            sys.stderr.write('Please use: cldoc generate [CXXFLAGS] -- [OPTIONS] [FILES]\n')
            sys.exit(1)
        else:
            sep = -1

    parser = argparse.ArgumentParser(description='clang based documentation generator.',
                                     usage='%(prog)s generate [CXXFLAGS] -- [OPTIONS] [FILES]')

    parser.add_argument('--quiet', default=False, action='store_const', const=True,
                        help='be quiet about it')

    parser.add_argument('--report', default=False,
                          action='store_const', const=True, help='report documentation coverage and errors')

    parser.add_argument('--output', default=None, metavar='DIR',
                          help='specify the output directory')

    parser.add_argument('--language', default='c++', metavar='LANGUAGE',
                          help='specify the default parse language (c++, c or objc)')

    parser.add_argument('--type', default='html', metavar='TYPE',
                          help='specify the type of output (html or xml, default html)')

    parser.add_argument('--merge', default=[], metavar='FILES', action='append',
                          help='specify additional description files to merge into the documentation')

    parser.add_argument('--merge-filter', default=None, metavar='FILTER',
                          help='specify program to pass merged description files through')

    parser.add_argument('--basedir', default=None, metavar='DIR',
                          help='the project base directory')

    parser.add_argument('--static', default=False, action='store_const', const=True,
                          help='generate a static website (only for when --output is html)')

    parser.add_argument('--custom-js', default=[], metavar='FILES', action='append',
                          help='specify additional javascript files to be merged into the html (only for when --output is html)')

    parser.add_argument('--custom-css', default=[], metavar='FILES', action='append',
                          help='specify additional css files to be merged into the html (only for when --output is html)')

    parser.add_argument('files', nargs='+', help='files to parse')

    restargs = args[sep + 1:]
    cxxflags = args[:sep]

    opts = parser.parse_args(restargs)

    if opts.quiet:
        sys.stdout = open(os.devnull, 'w')

    from . import tree

    if not opts.output:
        sys.stderr.write("Please specify the output directory\n")
        sys.exit(1)

    if opts.static and opts.type != 'html':
        sys.stderr.write("The --static option can only be used with the html output format\n")
        sys.exit(1)

    haslang = False

    for x in cxxflags:
        if x.startswith('-x'):
            haslang = True

    if not haslang:
        cxxflags.append('-x')
        cxxflags.append(opts.language)

    t = tree.Tree(opts.files, cxxflags)

    t.process()

    if opts.merge:
        t.merge(opts.merge_filter, opts.merge)

    t.cross_ref()

    run_generate(t, opts)

# vi:ts=4:et

########NEW FILE########
__FILENAME__ = cmdgir
# This file is part of cldoc.  cldoc is free software: you can
# redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
from __future__ import absolute_import

import sys, argparse, re, os

try:
    from xml.etree import cElementTree as ElementTree
except:
    from xml.etree import ElementTree

from cldoc.clang import cindex

from . import defdict

from . import nodes
from . import generators
from . import comment
from . import example
from . import documentmerger
from . import utf8

def nsgtk(s):
    return '{{{0}}}{1}'.format('http://www.gtk.org/introspection/core/1.0', s)

def nsc(s):
    return '{{{0}}}{1}'.format('http://www.gtk.org/introspection/c/1.0', s)

def nsglib(s):
    return '{{{0}}}{1}'.format('http://www.gtk.org/introspection/glib/1.0', s)

def stripns(tag):
    try:
        pos = tag.index('}')
        return tag[pos+1:]
    except:
        return tag

class Interface(nodes.Class):
    @property
    def classname(self):
        return '{http://jessevdk.github.com/cldoc/gobject/1.0}interface'

class Class(nodes.Class):
    def __init__(self, cursor, comment):
        nodes.Class.__init__(self, cursor, comment)

        # Extract bases
        for b in cursor.bases:
            self.bases.append(nodes.Class.Base(b))

        for i in cursor.implements:
            self.implements.append(nodes.Class.Base(i))

    @property
    def classname(self):
        return '{http://jessevdk.github.com/cldoc/gobject/1.0}class'

class Property(nodes.Node):
    def __init__(self, cursor, comment):
        nodes.Node.__init__(self, cursor, comment)

        self.type = nodes.Type(cursor.type)

    @property
    def classname(self):
        return '{http://jessevdk.github.com/cldoc/gobject/1.0}property'

    @property
    def props(self):
        ret = nodes.Node.props.fget(self)

        mode = []

        if not ('writable' in self.cursor.node.attrib and self.cursor.node.attrib['writable'] == '1'):
            mode.append('readonly')

        if 'construct-only' in self.cursor.node.attrib and self.cursor.node.attrib['construct-only'] == '1':
            mode.append('construct-only')

        if 'construct' in self.cursor.node.attrib and self.cursor.node.attrib['construct'] == '1':
            mode.append('construct')

        if len(mode) > 0:
            ret['mode'] = ",".join(mode)

        return ret

class Boxed(nodes.Struct):
    def __init__(self, cursor, comment):
        nodes.Struct.__init__(self, cursor, comment)

    @property
    def classname(self):
        return '{http://jessevdk.github.com/cldoc/gobject/1.0}boxed'

    @property
    def force_page(self):
        return True

class GirComment(comment.Comment):
    hashref = re.compile('#([a-z_][a-z0-9_]*)', re.I)
    emph = re.compile('<emphasis>(.*?)</emphasis>', re.I)
    title = re.compile('<title>(.*?)</title>', re.I)
    refsect2 = re.compile('(<refsect2 [^>]*>|</refsect2>)\n?', re.I)
    varref = re.compile('@([a-z][a-z0-9_]*)', re.I)
    constref = re.compile('%([a-z_][a-z0-9_]*)', re.I)
    proglisting = re.compile('<informalexample>\s*<programlisting>\s*(.*?)\s*</programlisting>\s*</informalexample>', re.I | re.M)

    def __init__(self, cursor):
        doc = cursor.node.find(nsgtk('doc'))

        if not doc is None:
            text = doc.text
        else:
            text = ''

        text = self.subst_format(text)

        brieftext = text
        doctext = ''

        try:
            firstdot = text.index('.')

            try:
                firstnl = text.index("\n")
            except:
                firstnl = firstdot

            if firstnl < firstdot:
                firstdot = firstnl - 1

            nextnonsp = firstdot + 1

            while nextnonsp < len(text) and text[nextnonsp] != '\n' and not text[nextnonsp].isspace():
                nextnonsp += 1

            if nextnonsp != len(text):
                # Replicate brief and non brief...
                # Insert newline just after .
                brieftext = text[:firstdot]
                doctext = text
        except:
            pass

        if cursor.typename in ['method', 'function', 'virtual-method', 'constructor']:
            # Assemble function argument comments and return value comment
            preat = []
            postat = []

            for param in cursor.children:
                paramdoc = param.node.find(nsgtk('doc'))

                if not paramdoc is None:
                    paramdoc = self.subst_format(paramdoc.text)
                else:
                    paramdoc = '*documentation missing...*'

                preat.append('@{0} {1}'.format(param.spelling, paramdoc.replace('\n', ' ')))

            return_node = cursor.node.find(nsgtk('return-value'))

            if not return_node is None and cursor.type.get_result().spelling != 'void':
                doc = return_node.find(nsgtk('doc'))

                if not doc is None:
                    postat.append('@return {0}'.format(self.subst_format(doc.text).replace('\n', ' ')))
                else:
                    postat.append('@return *documentation missing...*')

            if len(cursor.children) > 0:
                preat.append('')

                if len(doctext) > 0:
                    preat.append('')

            if brieftext == '':
                brieftext = '*documentation missing...*'

            text = brieftext.replace('\n', ' ').rstrip() + "\n" + "\n".join(preat) + doctext

            if len(postat) != 0:
                text += '\n\n' + '\n'.join(postat)
        else:
            if doctext != '':
                text = brieftext + "\n\n" + doctext
            else:
                text = brieftext.replace("\n", ' ')

        comment.Comment.__init__(self, text, None)

    def subst_format(self, text):
        text = GirComment.hashref.sub(lambda x: '<{0}>'.format(x.group(1)), text)
        text = GirComment.varref.sub(lambda x: '<{0}>'.format(x.group(1)), text)
        text = GirComment.constref.sub(lambda x: '`{0}`'.format(x.group(1)), text)
        text = GirComment.emph.sub(lambda x: '*{0}*'.format(x.group(1)), text)
        text = GirComment.title.sub(lambda x: '## {0}'.format(x.group(1)), text)
        text = GirComment.refsect2.sub(lambda x: '', text)
        text = GirComment.proglisting.sub(lambda x: '    [code]\n    {0}\n'.format(x.group(1).replace('\n', '\n    ')), text)

        return text

class GirType:
    builtins = [
        'utf8',
        'gchar',
        'gint',
        'gint8',
        'gint16',
        'gint32',
        'gint64',
        'guint',
        'guint8',
        'guint16',
        'guint32',
        'guint64',
        'gfloat',
        'gdouble',
        'gpointer',
        'gsize',
        'gboolean',
        'none'
    ];

    def __init__(self, node):
        self.node = node
        self.kind = cindex.TypeKind.UNEXPOSED
        self.const_qualified = False

        self.is_out = False
        self.transfer_ownership = 'none'
        self.allow_none = False

        aname = nsc('type')

        if aname in self.node.attrib:
            self.spelling = self.node.attrib[aname]
        else:
            self.spelling = ''

        self._extract_const()
        self._extract_kind()
        self.declaration = None

        retval = self.node.find(nsgtk('return-value'))

        if not retval is None:
            self.return_type = GirCursor(retval).type

            if 'transfer-ownership' in retval.attrib:
                self.return_type.transfer_ownership = retval.attrib['transfer-ownership']

            if 'allow-none' in retval.attrib:
                self.return_type.allow_none = retval.attrib['allow-none'] == '1'
        else:
            self.return_type = None

    def is_builtin(self):
        return self.spelling in GirType.builtins

    def _extract_const(self):
        prefix = 'const '

        if self.spelling.startswith(prefix):
            self.const_qualified = True
            self.spelling = self.spelling[len(prefix):]

    def _extract_kind(self):
        if self.spelling == '':
            return

        if self.spelling.endswith('*'):
            self.kind = cindex.TypeKind.POINTER
            return

        for k in nodes.Type.namemap:
            if nodes.Type.namemap[k] == self.spelling:
                self.kind = k
                break

    def get_pointee(self):
        return GirTypePointer(self)

    def get_result(self):
        return self.return_type

    def get_canonical(self):
        return self

    def get_declaration(self):
        return self.declaration

    def is_const_qualified(self):
        return self.const_qualified

    def resolve_refs(self, resolver):
        if not self.return_type is None:
            self.return_type.resolve_refs(resolver)

        if not self.declaration is None:
            return

        if 'name' in self.node.attrib:
            name = self.node.attrib['name']
            self.declaration = resolver(name)

            if self.spelling == '' and not self.declaration is None:
                self.spelling = self.declaration.spelling

                if self.declaration.typename in ['record', 'class', 'interface']:
                    self.spelling += ' *'
                    self.kind = cindex.TypeKind.POINTER

            elif self.spelling == '' and name in GirType.builtins:
                if name == 'utf8':
                    self.spelling = 'gchar *'
                elif name == 'none':
                    self.spelling = 'void'
                else:
                    self.spelling = name

class GirTypePointer(GirType):
    def __init__(self, tp):
        self.node = tp.node
        self.pointer_type = tp
        self.spelling = tp.spelling[:-1]
        self.kind = cindex.TypeKind.UNEXPOSED
        self.const_qualified = False

        self._extract_const()
        self._extract_kind()

    def get_declaration(self):
        return self.pointer_type.get_declaration()

class GirCursor:
    kindmap = {
        'parameter': cindex.CursorKind.PARM_DECL
    }

    global_gerror_param = None

    def __init__(self, node):
        self.node = node
        self.typename = stripns(self.node.tag)
        self.children = []
        self.parent = None
        self.bases = None
        self.implements = None

        if 'introspectable' in node.attrib:
            self.introspectable = (node.attrib['introspectable'] != '0')
        else:
            self.introspectable = True

        self.type = self._extract_type()
        self.kind = self._extract_kind()

        self._virtual_param = None

        if self._is_object_type():
            self._create_virtual_param()

        if self.typename == 'member':
            self.enum_value = node.attrib['value']

        self._extract_children()

    def _extract_kind(self):
        if self.typename in GirCursor.kindmap:
            return GirCursor.kindmap[self.typename]
        else:
            return cindex.CursorKind.UNEXPOSED_DECL

    def _extract_type(self):
        if self.typename == 'type':
            return GirType(self.node)

        t = self.node.find(nsgtk('type'))

        if not t is None:
            retval = GirType(t)

            if 'direction' in self.node.attrib:
                retval.is_out = self.node.attrib['direction'] == 'out'

            if 'transfer-ownership' in self.node.attrib and not retval.is_out:
                retval.transfer_ownership = self.node.attrib['transfer-ownership']

            if 'allow-none' in self.node.attrib:
                retval.allow_none = self.node.attrib['allow-none'] == '1'

            return retval

        va = self.node.find(nsgtk('varargs'))

        if not va is None:
            return GirType(va)

        ar = self.node.find(nsgtk('array'))

        if not ar is None:
            return GirType(ar)

        ret = GirType(self.node)
        ret.declaration = self

        return ret

    def _is_object_type(self):
        return self.typename in ['class', 'interface'] or \
               (self.typename == 'record' and nsglib('get-type') in self.node.attrib)

    def _create_virtual_param(self):
        # Make virtual first parameter representing pointer to object
        param = ElementTree.Element(nsgtk('parameter'))

        param.attrib['name'] = 'self'
        param.attrib['transfer-ownership'] = 'none'

        ntp = nsc('type')

        tp = ElementTree.Element(nsgtk('type'))
        tp.attrib['name'] = self.node.attrib['name']
        tp.attrib[ntp] = self.node.attrib[ntp] + '*'

        doc = ElementTree.Element(nsgtk('doc'))
        doc.text = 'a <{0}>.'.format(self.node.attrib[ntp])

        param.append(doc)
        param.append(tp)

        self._virtual_param = param

    def _setup_first_param(self, method):
        method.children.insert(0, GirCursor(self._virtual_param))

    def _make_gerror_param(self):
        if not GirCursor.global_gerror_param is None:
            return GirCursor.global_gerror_param

        param = ElementTree.Element(nsgtk('parameter'))

        param.attrib['name'] = 'error'
        param.attrib['transfer-ownership'] = 'none'
        param.attrib['allow-none'] = '1'

        tp = ElementTree.Element(nsgtk('type'))

        tp.attrib['name'] = 'Error'
        tp.attrib[nsc('type')] = 'GError **'

        doc = ElementTree.Element(nsgtk('doc'))
        doc.text = 'a #GError.'

        param.append(doc)
        param.append(tp)

        GirCursor.global_gerror_param = param
        return param

    def _extract_children(self):
        children = []

        if self.typename in ['function', 'method', 'virtual-method', 'constructor']:
            children = list(self.node.iterfind(nsgtk('parameters') + '/' + nsgtk('parameter')))

            if 'throws' in self.node.attrib and self.node.attrib['throws'] == '1':
                children.append(self._make_gerror_param())

        elif self.typename in ['enumeration', 'bitfield']:
            children = self.node.iterfind(nsgtk('member'))
        elif self.typename in ['record', 'class', 'interface']:
            self.bases = []
            self.implements = []

            def childgen():
                childtypes = ['function', 'method', 'constructor', 'virtual-method', 'property', 'field']

                for child in self.node:
                    if stripns(child.tag) in childtypes:
                        yield child

            children = childgen()

        for child in children:
            cursor = GirCursor(child)

            if not self._virtual_param is None and \
               cursor.typename == 'method' or cursor.typename == 'virtual-method':
                self._setup_first_param(cursor)

            cursor.parent = self
            self.children.append(cursor)

    @property
    def displayname(self):
        return self.name

    @property
    def semantic_parent(self):
        return self.parent

    @property
    def spelling(self):
        if self.typename in ['function', 'method', 'member', 'constructor']:
            n = nsc('identifier')
        elif self.typename in ['parameter', 'field', 'property']:
            n = 'name'
        else:
            n = nsc('type')

        if n in self.node.attrib:
            return self.node.attrib[n]
        else:
            return ''

    def is_static_method(self):
        return False

    def is_virtual_method(self):
        return self.typename == 'virtual-method'

    def is_definition(self):
        return True

    @property
    def name(self):
        return self.spelling

    @property
    def refname(self):
        if nsglib('type-name') in self.node.attrib and 'name' in self.node.attrib:
            return self.node.attrib['name']
        else:
            return None

    @property
    def extent(self):
        return None

    @property
    def location(self):
        return None

    def get_children(self):
        return self.children

    def _add_base(self, b):
        if not b is None:
            self.bases.append(b)

    def _add_implements(self, i):
        if not i is None:
            self.implements.append(i)

    def get_usr(self):
        return self.spelling

    def resolve_refs(self, resolver):
        # Resolve things like types and stuff
        if not self.type is None:
            self.type.resolve_refs(resolver)

        for child in self.children:
            child.resolve_refs(resolver)

        # What about, like, baseclasses...
        if self.typename in ['class', 'interface']:
            if 'parent' in self.node.attrib:
                self._add_base(resolver(self.node.attrib['parent']))

            for implements in self.node.iterfind(nsgtk('implements')):
                self._add_implements(resolver(implements.attrib['name']))

class GirTree(documentmerger.DocumentMerger):
    def __init__(self, category=None):
        self.mapping = {
            'function': self.parse_function,
            'class': self.parse_class,
            'record': self.parse_record,
            'interface': self.parse_interface,
            'enumeration': self.parse_enumeration,
            'callback': self.parse_callback,
            'bitfield': self.parse_enumeration,
            'virtual-method': self.parse_virtual_method,
            'method': self.parse_method,
            'constructor': self.parse_constructor,
            'property': self.parse_property,
            'signal': self.parse_signal,
            'field': self.parse_field,
            'doc': None,
            'implements': None,
            'prerequisite': None,
        }

        self.category_to_node = defdict.Defdict()

        self.root = nodes.Root()
        self.namespaces = {}
        self.processed = {}
        self.map_id_to_cusor = {}
        self.cursor_to_node = {}
        self.exported_namespaces = []
        self.usr_to_node = defdict.Defdict()
        self.qid_to_node = defdict.Defdict()
        self.all_nodes = []

        self.usr_to_node[None] = self.root
        self.qid_to_node[None] = self.root

        if not category is None:
            self.category = self.add_categories([category])
        else:
            self.category = None

        if not self.category is None:
            self.root_node = self.category
        else:
            self.root_node = self.root

    def match_ref(self, child, name):
        if isinstance(name, utf8.string):
            return name == child.name
        else:
            return name.match(child.name)

    def find_ref(self, node, name, goup):
        if node is None:
            return []

        ret = []

        for child in node.resolve_nodes:
            if self.match_ref(child, name):
                ret.append(child)

        if goup and len(ret) == 0:
            return self.find_ref(node.parent, name, True)
        else:
            return ret

    def cross_ref(self, node=None):
        if node is None:
            node = self.root

        if not node.comment is None:
            node.comment.resolve_refs(self.find_ref, node)

        for child in node.children:
            self.cross_ref(child)

        self.markup_code()

    def parse_function(self, cursor):
        return nodes.Function(cursor, GirComment(cursor))

    def parse_struct_children(self, ret):
        for child in ret.cursor.children:
            c = self.parse_cursor(child)

            if not c is None:
                ret.append(c)

    def parse_class(self, cursor):
        ret = Class(cursor, GirComment(cursor))

        ret.typedef = nodes.Typedef(cursor, None)
        self.parse_struct_children(ret)

        return ret

    def parse_signal(self, node):
        # TODO
        return None

    def parse_field(self, cursor):
        if 'private' in cursor.node.attrib and cursor.node.attrib['private'] == '1':
            return None

        return nodes.Field(cursor, GirComment(cursor))

    def parse_constructor(self, cursor):
        return nodes.Function(cursor, GirComment(cursor))

    def parse_virtual_method(self, node):
        # TODO
        return None

    def parse_method(self, cursor):
        return nodes.Function(cursor, GirComment(cursor))

    def parse_property(self, cursor):
        return Property(cursor, GirComment(cursor))

    def parse_boxed(self, cursor):
        ret = Boxed(cursor, GirComment(cursor))
        ret.typedef = nodes.Typedef(cursor, None)

        self.parse_struct_children(ret)
        return ret

    def parse_record(self, cursor):
        if nsglib('is-gtype-struct-for') in cursor.node.attrib:
            return None

        if 'disguised' in cursor.node.attrib and cursor.node.attrib['disguised'] == '1':
            return None

        if nsglib('get-type') in cursor.node.attrib:
            return self.parse_boxed(cursor)

        ret = nodes.Struct(cursor, GirComment(cursor))
        ret.typedef = nodes.Typedef(cursor, None)

        self.parse_struct_children(ret)

        return ret

    def parse_interface(self, cursor):
        ret = Interface(cursor, GirComment(cursor))
        self.parse_struct_children(ret)

        return ret

    def parse_enumeration(self, cursor):
        ret = nodes.Enum(cursor, GirComment(cursor))

        # All enums are typedefs
        ret.typedef = nodes.Typedef(cursor, None)

        for member in cursor.children:
            ret.append(nodes.EnumValue(member, GirComment(member)))

        return ret

    def parse_callback(self, cursor):
        pass

    def parse_cursor(self, cursor):
        if not cursor.introspectable:
            return None

        fn = self.mapping[cursor.typename]

        if not fn is None:
            ret = fn(cursor)

            if not ret is None:
                self.cursor_to_node[cursor] = ret
                self.all_nodes.append(ret)

                return ret
        else:
            return None

    def lookup_gir(self, ns, version):
        dirs = os.getenv('XDG_DATA_DIRS')

        if dirs is None:
            dirs = ['/usr/local/share', '/usr/share']
        else:
            dirs = dirs.split(os.pathsep)

        for d in dirs:
            fname = os.path.join(d, 'gir-1.0', "{0}-{1}.gir".format(ns, version))

            if os.path.exists(fname):
                return fname

        return None

    def gir_split(self, filename):
        name, _ = os.path.splitext(os.path.basename(filename))
        return name.split('-', 2)

    def add_gir(self, filename, included=False):
        ns, version = self.gir_split(filename)

        if (ns, version) in self.processed:
            return

        tree = ElementTree.parse(filename)
        repository = tree.getroot()

        self.processed[(ns, version)] = tree

        # First process includes
        for include in repository.iterfind(nsgtk('include')):
            incname = include.attrib['name']
            incversion = include.attrib['version']

            filename = self.lookup_gir(incname, incversion)

            if filename is None:
                sys.stderr.write('Could not find include `{0}-{1}\'\n'.format(incname, incversion))
                sys.exit(1)

            self.add_gir(filename, True)

        # Then process cursors
        ns = repository.find(nsgtk('namespace'))
        nsname = ns.attrib['name']

        cursors = []

        for child in ns:
            cursor = GirCursor(child)
            refname = cursor.refname

            if not refname is None:
                self.map_id_to_cusor[nsname + '.' + refname] = cursor

            cursors.append(cursor)

        self.namespaces[nsname] = cursors

        if not included:
            self.exported_namespaces.append(nsname)

    def resolve_ref(self, ns):
        def resolver(item):
            item = item.rstrip('*')

            if item in GirType.builtins:
                return None

            if not '.' in item:
                item = ns + '.' + item

            if item in self.map_id_to_cusor:
                return self.map_id_to_cusor[item]
            else:
                return None

        return resolver

    def parse(self):
        # Resolve cursor references
        for ns in self.namespaces:
            for cursor in self.namespaces[ns]:
                cursor.resolve_refs(self.resolve_ref(ns))

        classes = {}

        for ns in self.exported_namespaces:
            for cursor in self.namespaces[ns]:
                node = self.parse_cursor(cursor)

                if not node is None:
                    self.root_node.append(node)

                    if isinstance(node, Class) or isinstance(node, Interface):
                        classes[node.qid] = node

        for qid in classes:
            classes[qid].resolve_bases(classes)

        for node in self.all_nodes:
            self.qid_to_node[node.qid] = node

    def markup_code(self):
        for node in self.all_nodes:
            if node.comment is None:
                continue

            if not node.comment.doc:
                continue

            comps = node.comment.doc.components


            for i in range(len(comps)):
                component = comps[i]

                if not isinstance(component, comment.Comment.Example):
                    continue

                text = str(component)

                ex = example.Example()
                ex.append(text)

                comps[i] = ex

def run(args):
    parser = argparse.ArgumentParser(description='clang based documentation generator.',
                                     usage='%(prog)s gir --output DIR [OPTIONS] GIRFILE')

    parser.add_argument('--quiet', default=False, action='store_const', const=True,
                        help='be quiet about it')

    parser.add_argument('--report', default=False,
                          action='store_const', const=True, help='report documentation coverage and errors')

    parser.add_argument('--output', default=None, metavar='DIR',
                          help='specify the output directory')

    parser.add_argument('--type', default='html', metavar='TYPE',
                          help='specify the type of output (html or xml, default html)')

    parser.add_argument('--merge', default=[], metavar='FILES', action='append',
                          help='specify additional description files to merge into the documentation')

    parser.add_argument('--merge-filter', default=None, metavar='FILTER',
                          help='specify program to pass merged description files through')

    parser.add_argument('--static', default=False, action='store_const', const=True,
                          help='generate a static website (only for when --output is html)')

    parser.add_argument('--category', default=None, metavar='CATEGORY',
                          help='category in which to place all symbols')

    parser.add_argument('--custom-js', default=[], metavar='FILES', action='append',
                          help='specify additional javascript files to be merged into the html (only for when --output is html)')

    parser.add_argument('--custom-css', default=[], metavar='FILES', action='append',
                          help='specify additional css files to be merged into the html (only for when --output is html)')

    parser.add_argument('files', nargs='+', help='gir files to parse')

    opts = parser.parse_args(args)

    t = GirTree(opts.category)

    # Generate artificial tree
    for f in opts.files:
        t.add_gir(f)

    t.parse()

    if opts.merge:
        t.merge(opts.merge_filter, opts.merge)

    t.cross_ref()

    from .cmdgenerate import run_generate

    run_generate(t, opts)

# vi:ts=4:et

########NEW FILE########
__FILENAME__ = cmdinspect
# This file is part of cldoc.  cldoc is free software: you can
# redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
from __future__ import absolute_import

import sys, argparse

def run(args):
    try:
        sep = args.index('--')
    except ValueError:
        if not '--help' in args:
            sys.stderr.write('Please use: cldoc inspect [CXXFLAGS] -- [OPTIONS] [FILES]\n')
            sys.exit(1)
        else:
            sep = 0

    parser = argparse.ArgumentParser(description='clang based documentation generator.',
                                     usage='%(prog)s inspect [CXXFLAGS] -- [OPTIONS] DIRECTORY')

    parser.add_argument('files', nargs='*', help='files to parse')

    restargs = args[sep + 1:]
    cxxflags = args[:sep]

    opts = parser.parse_args(restargs)

    from . import tree
    from . import inspecttree

    t = tree.Tree(opts.files, cxxflags)
    inspecttree.inspect(t)

# vi:ts=4:et

########NEW FILE########
__FILENAME__ = cmdserve
# This file is part of cldoc.  cldoc is free software: you can
# redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
from __future__ import absolute_import

import subprocess, threading, time, sys, argparse, os
import SimpleHTTPServer, SocketServer

class Server(SocketServer.TCPServer):
    allow_reuse_address = True

def handler_bind(directory):
    class Handler(SimpleHTTPServer.SimpleHTTPRequestHandler):
        def end_headers(self):
            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Expires', '0')

            SimpleHTTPServer.SimpleHTTPRequestHandler.end_headers(self)

        def translate_path(self, path):
            while path.startswith('/'):
                path = path[1:]

            path = os.path.join(directory, path)
            return SimpleHTTPServer.SimpleHTTPRequestHandler.translate_path(self, path)

        def log_message(self, format, *args):
            pass

    return Handler

class SocketThread(threading.Thread):
    def __init__(self, directory, host):
        threading.Thread.__init__(self)

        if not ':' in host:
            self.host = host
            self.port = 6060
        else:
            self.host, port = host.split(':')
            self.port = int(port)

        self.httpd = Server((self.host, self.port), handler_bind(directory))

    def shutdown(self):
        self.httpd.shutdown()
        self.httpd.server_close()

    def run(self):
        self.httpd.serve_forever()

def run(args):
    parser = argparse.ArgumentParser(description='clang based documentation generator.',
                                     usage='%(prog)s serve [OPTIONS] [DIRECTORY]')

    parser.add_argument('--address', default=':6060', metavar='HOST:PORT',
                        help='address (host:port) on which to serve documentation')

    parser.add_argument('directory', nargs='?', help='directory to serve', default='.')

    opts = parser.parse_args(args)

    t = SocketThread(opts.directory, opts.address)
    t.start()

    dn = open(os.devnull, 'w')

    if t.host == '':
        url = 'http://localhost:{0}/'.format(t.port)
    else:
        url = 'http://{0}:{1}/'.format(t.host, t.port)

    if sys.platform.startswith('darwin'):
        subprocess.call(('open', url), stdout=dn, stderr=dn)
    elif os.name == 'posix':
        subprocess.call(('xdg-open', url), stdout=dn, stderr=dn)

    while True:
        try:
            time.sleep(3600)
        except KeyboardInterrupt:
            t.shutdown()
            t.join()
            break

# vi:ts=4:et

########NEW FILE########
__FILENAME__ = comment
# This file is part of cldoc.  cldoc is free software: you can
# redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
from clang import cindex
from defdict import Defdict

from cldoc.struct import Struct
from cldoc import utf8

import os, re, sys, bisect

class Sorted(list):
    def __init__(self, key=None):
        if key is None:
            key = lambda x: x

        self.keys = []
        self.key = key

    def insert_bisect(self, item, bi):
        k = self.key(item)
        idx = bi(self.keys, k)

        self.keys.insert(idx, k)
        return super(Sorted, self).insert(idx, item)

    def insert(self, item):
        return self.insert_bisect(item, bisect.bisect_left)

    insert_left = insert

    def insert_right(self, item):
        return self.insert_bisect(item, bisect.bisect_right)

    def bisect(self, item, bi):
        k = self.key(item)

        return bi(self.keys, k)

    def bisect_left(self, item):
        return self.bisect(item, bisect.bisect_left)

    def bisect_right(self, item):
        return self.bisect(item, bisect.bisect_right)

    def find(self, key):
        i = bisect.bisect_left(self.keys, key)

        if i != len(self.keys) and self.keys[i] == key:
            return self[i]
        else:
            return None

class Comment(object):
    class Example(str):
        def __new__(self, s, strip=True):
            if strip:
                s = '\n'.join([self._strip_prefix(x) for x in s.split('\n')])

            return str.__new__(self, s)

        @staticmethod
        def _strip_prefix(s):
            if s.startswith('    '):
                return s[4:]
            else:
                return s

    class String(object):
        def __init__(self, s):
            self.components = [utf8.utf8(s)]

        def _utf8(self):
            return utf8.utf8("").join([utf8.utf8(x) for x in self.components])

        def __str__(self):
            return str(self._utf8())

        def __unicode__(self):
            return unicode(self._utf8())

        def __bytes__(self):
            return bytes(self._utf8())

        def __eq__(self, other):
            if isinstance(other, str):
                return str(self) == other
            elif isinstance(other, unicode):
                return unicode(self) == other
            elif isinstance(other, bytes):
                return bytes(self) == other
            else:
                return object.__cmp__(self, other)

        def __nonzero__(self):
            l = len(self.components)

            return l > 0 and (l > 1 or len(self.components[0]) > 0)

    class MarkdownCode(utf8.utf8):
        pass

    class UnresolvedReference(utf8.utf8):
        reescape = re.compile('[*_]', re.I)

        def __new__(cls, s):
            ns = Comment.UnresolvedReference.reescape.sub(lambda x: '\\' + x.group(0), s)
            ret = utf8.utf8.__new__(cls, utf8.utf8('&lt;{0}&gt;').format(utf8.utf8(ns)))

            ret.orig = s
            return ret

    redocref = re.compile('(?P<isregex>[$]?)<(?:\\[(?P<refname>[^\\]]*)\\])?(?P<ref>operator(?:>>|>|>=)|[^>\n]+)>')
    redoccode = re.compile('^    \\[code\\]\n(?P<code>(?:(?:    .*|)\n)*)', re.M)
    redocmcode = re.compile('(^ *(`{3,}|~{3,}).*?\\2)', re.M | re.S)

    def __init__(self, text, location):
        self.__dict__['docstrings'] = []
        self.__dict__['text'] = text

        self.__dict__['location'] = location
        self.__dict__['_resolved'] = False

        self.doc = text
        self.brief = ''

    def __setattr__(self, name, val):
        if not name in self.docstrings:
            self.docstrings.append(name)

        if isinstance(val, dict):
            for key in val:
                if not isinstance(val[key], Comment.String):
                    val[key] = Comment.String(val[key])
        elif not isinstance(val, Comment.String):
            val = Comment.String(val)

        self.__dict__[name] = val

    def __nonzero__(self):
        return (bool(self.brief) and not (self.brief == u'*documentation missing...*')) or (bool(self.doc) and not (self.doc == u'*documentation missing...*'))

    def redoccode_split(self, doc):
        # Split on C/C++ code
        components = Comment.redoccode.split(doc)
        ret = []

        for i in range(0, len(components), 2):
            r = Comment.redocmcode.split(components[i])

            for j in range(0, len(r), 3):
                ret.append(r[j])

                if j < len(r) - 1:
                    ret.append(Comment.MarkdownCode(r[j + 1]))

            if i < len(components) - 1:
                ret.append(Comment.Example(components[i + 1]))

        return ret

    def redoc_split(self, doc):
        ret = []

        # First split examples
        components = self.redoccode_split(doc)

        for c in components:
            if isinstance(c, Comment.Example) or isinstance(c, Comment.MarkdownCode):
                ret.append((c, None, None))
            else:
                lastpos = 0

                for m in Comment.redocref.finditer(c):
                    span = m.span(0)

                    prefix = c[lastpos:span[0]]
                    lastpos = span[1]

                    ref = m.group('ref')
                    refname = m.group('refname')

                    if not refname:
                        refname = None

                    if len(m.group('isregex')) > 0:
                        ref = re.compile(ref)

                    ret.append((prefix, ref, refname))

                ret.append((c[lastpos:], None, None))

        return ret

    def resolve_refs_for_doc(self, doc, resolver, root):
        comps = self.redoc_split(utf8.utf8(doc))
        components = []

        for pair in comps:
            prefix, name, refname = pair
            components.append(prefix)

            if name is None:
                continue

            if isinstance(name, utf8.string):
                names = name.split('::')
            else:
                names = [name]

            nds = [root]

            for j in range(len(names)):
                newnds = []

                for n in nds:
                    newnds += resolver(n, names[j], j == 0)

                if len(newnds) == 0:
                    break

                nds = newnds

            if len(newnds) > 0:
                components.append((newnds, refname))
            else:
                components.append(Comment.UnresolvedReference(name))

        doc.components = components

    def resolve_refs(self, resolver, root):
        if self.__dict__['_resolved']:
            return

        self.__dict__['_resolved'] = True

        for name in self.docstrings:
            doc = getattr(self, name)

            if not doc:
                continue

            if isinstance(doc, dict):
                for key in doc:
                    if not isinstance(doc[key], Comment.String):
                        doc[key] = Comment.String(doc[key])

                    self.resolve_refs_for_doc(doc[key], resolver, root)
            else:
                self.resolve_refs_for_doc(doc, resolver, root)

class RangeMap(Sorted):
    Item = Struct.define('Item', obj=None, start=0, end=0)

    def __init__(self):
        super(RangeMap, self).__init__(key=lambda x: x.start)

        self.stack = []

    def push(self, obj, start):
        self.stack.append(RangeMap.Item(obj=obj, start=start, end=start))

    def pop(self, end):
        item = self.stack.pop()
        item.end = end

        self.insert(item)

    def insert(self, item, start=None, end=None):
        if not isinstance(item, RangeMap.Item):
            item = RangeMap.Item(obj=item, start=start, end=end)

        self.insert_right(item)

    def find(self, i):
        # Finds object for which i falls in the range of that object
        idx = bisect.bisect_right(self.keys, i)

        # Go back up until falls within end
        while idx > 0:
            idx -= 1

            o = self[idx]

            if i <= o.end:
                return o.obj

        return None

class CommentsDatabase(object):
    cldoc_instrre = re.compile('^cldoc:([a-zA-Z_-]+)(\(([^\)]*)\))?')

    def __init__(self, filename, tu):
        self.filename = filename

        self.categories = RangeMap()
        self.comments = Sorted(key=lambda x: x.location.offset)

        self.extract(filename, tu)

    def parse_cldoc_instruction(self, token, s):
        m = CommentsDatabase.cldoc_instrre.match(s)

        if not m:
            return False

        func = m.group(1)
        args = m.group(3)

        if args:
            args = [x.strip() for x in args.split(",")]
        else:
            args = []

        name = 'cldoc_instruction_{0}'.format(func.replace('-', '_'))

        if hasattr(self, name):
            getattr(self, name)(token, args)
        else:
            sys.stderr.write('Invalid cldoc instruction: {0}\n'.format(func))
            sys.exit(1)

        return True

    @property
    def category_names(self):
        for item in self.categories:
            yield item.obj

    def location_to_str(self, loc):
        return '{0}:{1}:{2}'.format(loc.file.name, loc.line, loc.column)

    def cldoc_instruction_begin_category(self, token, args):
        if len(args) != 1:
            sys.stderr.write('No category name specified (at {0})\n'.format(self.location_to_str(token.location)))

            sys.exit(1)

        category = args[0]
        self.categories.push(category, token.location.offset)

    def cldoc_instruction_end_category(self, token, args):
        if len(self.categories.stack) == 0:
            sys.stderr.write('Failed to end cldoc category: no category to end (at {0})\n'.format(self.location_to_str(token.location)))

            sys.exit(1)

        last = self.categories.stack[-1]

        if len(args) == 1 and last.obj != args[0]:
            sys.stderr.write('Failed to end cldoc category: current category is `{0}\', not `{1}\' (at {2})\n'.format(last.obj, args[0], self.location_to_str(token.location)))

            sys.exit(1)

        self.categories.pop(token.extent.end.offset)

    def lookup_category(self, location):
        if location.file.name != self.filename:
            return None

        return self.categories.find(location.offset)

    def lookup(self, location):
        if location.file.name != self.filename:
            return None

        return self.comments.find(location.offset)

    def extract(self, filename, tu):
        """
        extract extracts comments from a translation unit for a given file by
        iterating over all the tokens in the TU, locating the COMMENT tokens and
        finding out to which cursors the comments semantically belong.
        """
        it = tu.get_tokens(extent=tu.get_extent(filename, (0, int(os.stat(filename).st_size))))

        while True:
            try:
                self.extract_loop(it)
            except StopIteration:
                break

    def extract_one(self, token, s):
        # Parse special cldoc:<instruction>() comments for instructions
        if self.parse_cldoc_instruction(token, s.strip()):
            return

        comment = Comment(s, token.location)
        self.comments.insert(comment)

    def extract_loop(self, iter):
        token = iter.next()

        # Skip until comment found
        while token.kind != cindex.TokenKind.COMMENT:
            token = iter.next()

        comments = []
        prev = None

        # Concatenate individual comments together, but only if they are strictly
        # adjacent
        while token.kind == cindex.TokenKind.COMMENT:
            cleaned = self.clean(token)

            # Process instructions directly, now
            if (not cleaned is None) and (not CommentsDatabase.cldoc_instrre.match(cleaned) is None):
                comments = [cleaned]
                break

            # Check adjacency
            if not prev is None and prev.extent.end.line + 1 < token.extent.start.line:
                # Empty previous comment
                comments = []

            if not cleaned is None:
                comments.append(cleaned)

            prev = token
            token = iter.next()

        if len(comments) > 0:
            self.extract_one(token, "\n".join(comments))

    def clean(self, token):
        prelen = token.extent.start.column - 1
        comment = token.spelling.strip()

        if comment.startswith('//'):
            if len(comment) > 2 and comment[2] == '-':
                return None

            return comment[2:].strip()
        elif comment.startswith('/*') and comment.endswith('*/'):
            if comment[2] == '-':
                return None

            lines = comment[2:-2].splitlines()

            if len(lines) == 1 and len(lines[0]) > 0 and lines[0][0] == ' ':
                return lines[0][1:].rstrip()

            retl = []

            for line in lines:
                if prelen == 0 or line[0:prelen].isspace():
                    line = line[prelen:].rstrip()

                    if line.startswith(' *') or line.startswith('  '):
                        line = line[2:]

                        if len(line) > 0 and line[0] == ' ':
                            line = line[1:]

                retl.append(line)

            return "\n".join(retl)
        else:
            return comment

from pyparsing import *

class Parser:
    ParserElement.setDefaultWhitespaceChars(' \t\r')

    identifier = Word(alphas + '_', alphanums + '_')

    brief = restOfLine.setResultsName('brief') + lineEnd

    paramdesc = restOfLine + ZeroOrMore(lineEnd + ~('@' | lineEnd) + Regex('[^\n]+')) + lineEnd.suppress()
    param = '@' + identifier.setResultsName('name') + White() + Combine(paramdesc).setResultsName('description')

    preparams = ZeroOrMore(param.setResultsName('preparam', listAllMatches=True))
    postparams = ZeroOrMore(param.setResultsName('postparam', listAllMatches=True))

    bodyline = NotAny('@') + (lineEnd | (Regex('[^\n]+') + lineEnd))
    body = ZeroOrMore(lineEnd) + Combine(ZeroOrMore(bodyline)).setResultsName('body')

    doc = brief + preparams + body + postparams

    @staticmethod
    def parse(s):
        return Parser.doc.parseString(s)

# vi:ts=4:et

########NEW FILE########
__FILENAME__ = defdict
# This file is part of cldoc.  cldoc is free software: you can
# redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
class Defdict(dict):
    def __missing__(self, key):
        return None

# vi:ts=4:et

########NEW FILE########
__FILENAME__ = documentmerger
import os, subprocess

import comment
import nodes
import sys, re

class DocumentMerger:
    reinclude = re.compile('#<cldoc:include[(]([^)]*)[)]>')

    def merge(self, mfilter, files):
        for f in files:
            if os.path.basename(f).startswith('.'):
                continue

            if os.path.isdir(f):
                self.merge(mfilter, [os.path.join(f, x) for x in os.listdir(f)])
            elif f.endswith('.md'):
                self._merge_file(mfilter, f)

    def _split_categories(self, filename, contents):
        lines = contents.splitlines()

        ret = {}

        category = None
        doc = []
        first = False
        ordered = []

        for line in lines:
            prefix = '#<cldoc:'

            line = line.rstrip('\n')

            if first:
                first = False

                if line == '':
                    continue

            if line.startswith(prefix) and line.endswith('>'):
                if len(doc) > 0 and not category:
                    sys.stderr.write('Failed to merge file `{0}\': no #<cldoc:id> specified\n'.format(filename))
                    sys.exit(1)

                if category:
                    if not category in ret:
                        ordered.append(category)

                    ret[category] = "\n".join(doc)

                doc = []
                category = line[len(prefix):-1]
                first = True
            else:
                doc.append(line)

        if category:
            if not category in ret:
                ordered.append(category)

            ret[category] = "\n".join(doc)
        elif len(doc) > 0:
            sys.stderr.write('Failed to merge file `{0}\': no #<cldoc:id> specified\n'.format(filename))
            sys.exit(1)

        return [[c, ret[c]] for c in ordered]

    def _normalized_qid(self, qid):
        if qid == 'index':
            return None

        if qid.startswith('::'):
            return qid[2:]

        return qid

    def _do_include(self, mfilter, filename, relpath):
        if not os.path.isabs(relpath):
            relpath = os.path.join(os.path.dirname(filename), relpath)

        return self._read_merge_file(mfilter, relpath)

    def _process_includes(self, mfilter, filename, contents):
        def repl(m):
            return self._do_include(mfilter, filename, m.group(1))

        return DocumentMerger.reinclude.sub(repl, contents)

    def _read_merge_file(self, mfilter, filename):
        if not mfilter is None:
            contents = unicode(subprocess.check_output([mfilter, filename]), 'utf-8')
        else:
            contents = unicode(open(filename).read(), 'utf-8')

        return self._process_includes(mfilter, filename, contents)

    def _merge_file(self, mfilter, filename):
        contents = self._read_merge_file(mfilter, filename)
        categories = self._split_categories(filename, contents)

        for (category, docstr) in categories:
            parts = category.split('/')

            qid = self._normalized_qid(parts[0])
            key = 'doc'

            if len(parts) > 1:
                key = parts[1]

            if not self.qid_to_node[qid]:
                self.add_categories([qid])
                node = self.category_to_node[qid]
            else:
                node = self.qid_to_node[qid]

            if key == 'doc':
                node.merge_comment(comment.Comment(docstr, None), override=True)
            else:
                sys.stderr.write('Unknown type `{0}\' for id `{1}\'\n'.format(key, parts[0]))
                sys.exit(1)

    def add_categories(self, categories):
        root = None

        for category in categories:
            parts = category.split('::')

            root = self.root
            fullname = ''

            for i in range(len(parts)):
                part = parts[i]
                found = False

                if i != 0:
                    fullname += '::'

                fullname += part

                for child in root.children:
                    if isinstance(child, nodes.Category) and child.name == part:
                        root = child
                        found = True
                        break

                if not found:
                    s = nodes.Category(part)

                    root.append(s)
                    root = s

                    self.category_to_node[fullname] = s
                    self.qid_to_node[s.qid] = s
                    self.all_nodes.append(s)

        return root

# vi:ts=4:et

########NEW FILE########
__FILENAME__ = example
# This file is part of cldoc.  cldoc is free software: you can
# redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
from cldoc.struct import Struct

from . import utf8

class Example(list):
    Item = Struct.define('Item', text='', classes=None)

    def append(self, text, classes=None):
        if isinstance(classes, utf8.string):
            classes = [classes]

        list.append(self, Example.Item(text=text, classes=classes))

# vi:ts=4:et

########NEW FILE########
__FILENAME__ = generator
# This file is part of cldoc.  cldoc is free software: you can
# redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
class Generator(object):
    def __init__(self, tree=None, opts=None):
        self.tree = tree
        self.options = opts

    def generate(self, outdir):
        self.outdir = outdir

        for node in self.tree.root.sorted_children():
            self.generate_node(node)

    def generate_node(self, node, passfunc=None):
        for child in node.sorted_children():
            if passfunc is None or passfunc(child):
                self.generate_node(child)

# vi:ts=4:et

########NEW FILE########
__FILENAME__ = html
# This file is part of cldoc.  cldoc is free software: you can
# redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
from __future__ import absolute_import

import inspect, os, shutil, json

from .generator import Generator
from .search import Search

class Html(Generator):
    def generate(self, output, isstatic, customjs=[], customcss=[]):
        # Write out json document for search
        self.write_search(output)

        d = os.path.dirname(__file__)

        datadir = os.path.abspath(os.path.join(d, '..', 'data'))
        index = os.path.join(datadir, 'index.html')

        try:
            os.makedirs(datadir)
        except:
            pass

        outfile = os.path.join(output, 'index.html')

        jstags = ['<script type="text/javascript" src="{0}"></script>'.format(x) for x in customjs]
        csstags = ['<link rel="stylesheet" href="{0}" type="text/css" charset="utf-8"/>'.format(x) for x in customcss]

        with open(index) as f:
            content = f.read()

            templ = '<meta type="custom-js" />'
            content = content.replace(templ, " ".join(jstags))

            templ = '<meta type="custom-css" />'
            content = content.replace(templ, " ".join(csstags))

            with open(outfile, 'w') as o:
                o.write(content)

        print('Generated `{0}\''.format(outfile))

    def write_search(self, output):
        search = Search(self.tree)

        records = [None] * len(search.records)

        for r in range(len(search.records)):
            rec = search.records[r]

            records[r] = (
                rec.s,
                rec.node.refid,
            )

        outfile = os.path.join(output, 'search.json')
        f = file(outfile, 'w')
        f.write(json.dumps({'records': records, 'suffixes': search.db}))
        f.close()


# vi:ts=4:et

########NEW FILE########
__FILENAME__ = report
# This file is part of cldoc.  cldoc is free software: you can
# redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
from __future__ import absolute_import

import inspect, os, shutil

from cldoc.struct import Struct
from cldoc.clang import cindex
from cldoc.comment import Comment

from cldoc import nodes

from xml.etree import ElementTree

class Report:
    Coverage = Struct.define('Coverage', name='', documented=[], undocumented=[])

    def __init__(self, tree, options):
        self.tree = tree
        self.options = options

    def indent(self, elem, level=0):
        i = "\n" + "  " * level

        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = i + "  "

            for e in elem:
                self.indent(e, level + 1)

                if not e.tail or not e.tail.strip():
                    e.tail = i + "  "
            if not e.tail or not e.tail.strip():
                e.tail = i
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = i

    def make_location(self, loc):
        elem = ElementTree.Element('location')

        if self.options.basedir:
            start = self.options.basedir
        else:
            start = os.curdir

        elem.set('file', os.path.relpath(str(loc.file), start))
        elem.set('line', str(loc.line))
        elem.set('column', str(loc.column))

        return elem

    def arguments(self, root):
        elem = ElementTree.Element('arguments')
        root.append(elem)

        for node in self.tree.all_nodes:
            if not isinstance(node, nodes.Function):
                continue

            if node.access == cindex.CXXAccessSpecifier.PRIVATE:
                continue

            if node.comment is None:
                continue

            # Check documented arguments
            notdocumented = []
            misspelled = []

            cm = node.comment
            argnames = {}

            for name in node.argument_names:
                argnames[name] = False

            for k in cm.params:
                if self._is_undocumented_comment(cm.params[k]):
                    continue

                if k in argnames:
                    argnames[k] = True
                else:
                    misspelled.append(k)

            for k in argnames:
                if not argnames[k]:
                    notdocumented.append(k)

            if node.return_type.typename != 'void' and not hasattr(cm, 'returns'):
                missingret = True
            elif hasattr(cm, 'returns') and self._is_undocumented_comment(cm.returns):
                missingret = True
            else:
                missingret = False

            if len(notdocumented) > 0 or len(misspelled) > 0 or missingret:
                e = ElementTree.Element('function')
                e.set('id', node.qid)
                e.set('name', node.name)

                for loc in node.comment_locations:
                    e.append(self.make_location(loc))

                if missingret:
                    ee = ElementTree.Element('undocumented-return')
                    e.append(ee)

                for ndoc in notdocumented:
                    ee = ElementTree.Element('undocumented')
                    ee.set('name', ndoc)
                    e.append(ee)

                for mis in misspelled:
                    ee = ElementTree.Element('misspelled')
                    ee.set('name', mis)
                    e.append(ee)

                elem.append(e)

    def _is_undocumented_comment(self, cm):
        return not bool(cm)

    def coverage(self, root):
        pertype = {}

        for node in self.tree.all_nodes:
            cname = node.__class__.__name__

            if node.access == cindex.CXXAccessSpecifier.PRIVATE:
                continue

            if not cname in pertype:
                pertype[cname] = Report.Coverage(name=cname.lower())

            if not self._is_undocumented_comment(node.comment):
                pertype[cname].documented.append(node)
            else:
                pertype[cname].undocumented.append(node)

        cov = ElementTree.Element('coverage')
        root.append(cov)

        for item in pertype.values():
            elem = ElementTree.Element('type')
            elem.set('name', item.name)
            elem.set('documented', str(len(item.documented)))
            elem.set('undocumented', str(len(item.undocumented)))

            item.undocumented.sort(key=lambda x: x.qid)

            for undoc in item.undocumented:
                e = ElementTree.Element('undocumented')
                e.set('id', undoc.qid)
                e.set('name', undoc.name)

                for loc in undoc.comment_locations:
                    e.append(self.make_location(loc))

                elem.append(e)

            cov.append(elem)

    def references(self, root):
        elem = ElementTree.Element('references')
        root.append(elem)

        for node in self.tree.all_nodes:
            if node.comment is None:
                continue

            ee = None

            for name in node.comment.docstrings:
                cm = getattr(node.comment, name)

                if not isinstance(cm, dict):
                    cm = {None: cm}

                for k in cm:
                    en = None

                    for component in cm[k].components:
                        if isinstance(component, Comment.UnresolvedReference):
                            if ee is None:
                                ee = ElementTree.Element(node.classname)

                                ee.set('name', node.name)
                                ee.set('id', node.qid)

                                for loc in node.comment_locations:
                                    ee.append(self.make_location(loc))

                                elem.append(ee)

                            if en is None:
                                en = ElementTree.Element('doctype')

                                en.set('name', name)

                                if not k is None:
                                    en.set('component', k)

                                ee.append(en)

                            er = ElementTree.Element('ref')
                            er.set('name', component.orig)
                            en.append(er)

    def generate(self, filename):
        root = ElementTree.Element('report')
        root.set('id', filename)
        root.set('title', 'Documention generator')

        doc = ElementTree.Element('doc')
        doc.text = """
This page provides a documentation coverage report. Any undocumented symbols
are reported here together with the location of where you should document them.

This report contains the following sections:

1. [Coverage](#{0}/coverage): The documented symbols coverage.
2. [Arguments](#{0}/arguments): Errors about undocumented, misspelled function arguments and
return values.
3. [References](#{0}/references): Unresolved cross references.
""".format(filename)

        root.append(doc)

        self.coverage(root)
        self.arguments(root)
        self.references(root)

        return root

# vi:ts=4:et

########NEW FILE########
__FILENAME__ = search
# This file is part of cldoc.  cldoc is free software: you can
# redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
from __future__ import absolute_import

import bisect
from cldoc.clang import cindex
from cldoc.struct import Struct

class Search:
    Record = Struct.define('Record', node=None, s='', id=0)

    def __init__(self, tree):
        self.records = []
        self.suffixes = []
        self.db = []

        for node in tree.root.descendants():
            if not node._refid is None and node.access != cindex.CXXAccessSpecifier.PRIVATE:
                self.make_index(node)

    def make_index(self, node):
        name = node.qid.lower()

        r = Search.Record(node=node, s=name, id=len(self.records))
        self.records.append(r)

        for i in range(len(name) - 3):
            suffix = name[i:]

            # Determine where to insert the suffix
            idx = bisect.bisect_left(self.suffixes, suffix)

            if idx != len(self.suffixes) and self.suffixes[idx] == suffix:
                self.db[idx].append((r.id, i))
            else:
                self.suffixes.insert(idx, suffix)
                self.db.insert(idx, [(r.id, i)])

# vi:ts=4:et

########NEW FILE########
__FILENAME__ = xml
# This file is part of cldoc.  cldoc is free software: you can
# redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
from __future__ import absolute_import
from cldoc.clang import cindex

from .generator import Generator
from cldoc import nodes
from cldoc import example
from cldoc import utf8

from xml.etree import ElementTree
import sys, os

class Xml(Generator):
    def generate(self, outdir):
        if not outdir:
            outdir = 'xml'

        try:
            os.makedirs(outdir)
        except OSError:
            pass

        ElementTree.register_namespace('gobject', 'http://jessevdk.github.com/cldoc/gobject/1.0')
        ElementTree.register_namespace('cldoc', 'http://jessevdk.github.com/cldoc/1.0')

        self.index = ElementTree.Element('index')
        self.written = {}

        self.indexmap = {
            self.tree.root: self.index
        }

        cm = self.tree.root.comment

        if cm:
            if cm.brief:
                self.index.append(self.doc_to_xml(self.tree.root, cm.brief, 'brief'))

            if cm.doc:
                self.index.append(self.doc_to_xml(self.tree.root, cm.doc))

        Generator.generate(self, outdir)

        if self.options.report:
            self.add_report()

        self.write_xml(self.index, 'index.xml')

        print('Generated `{0}\''.format(outdir))

    def add_report(self):
        from .report import Report

        reportname = 'report'

        while reportname + '.xml' in self.written:
            reportname = '_' + reportname

        page = Report(self.tree, self.options).generate(reportname)

        elem = ElementTree.Element('report')
        elem.set('name', 'Documentation generator')
        elem.set('ref', reportname)

        self.index.append(elem)

        self.write_xml(page, reportname + '.xml')

    def indent(self, elem, level=0):
        i = "\n" + "  " * level

        if elem.tag == 'doc':
            return

        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = i + "  "

            for e in elem:
                self.indent(e, level + 1)

                if not e.tail or not e.tail.strip():
                    e.tail = i + "  "
            if not e.tail or not e.tail.strip():
                e.tail = i
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = i

    def write_xml(self, elem, fname):
        self.written[fname] = True

        elem.attrib['xmlns'] = 'http://jessevdk.github.com/cldoc/1.0'

        tree = ElementTree.ElementTree(elem)

        self.indent(tree.getroot())

        f = open(os.path.join(self.outdir, fname), 'w')
        tree.write(f, encoding='utf-8', xml_declaration=True)

        f.close()

    def is_page(self, node):
        if node.force_page:
            return True

        if isinstance(node, nodes.Class):
            for child in node.children:
                if not (isinstance(child, nodes.Field) or \
                        isinstance(child, nodes.Variable) or \
                        isinstance(child, nodes.TemplateTypeParameter)):
                    return True

            return False

        pagecls = [nodes.Namespace, nodes.Category, nodes.Root]

        for cls in pagecls:
            if isinstance(node, cls):
                return True

        if isinstance(node, nodes.Typedef) and len(node.children) > 0:
            return True

        return False

    def is_top(self, node):
        if self.is_page(node):
            return True

        if node.parent == self.tree.root:
            return True

        return False

    def refid(self, node):
        if not node._refid is None:
            return node._refid

        parent = node

        meid = node.qid

        if not node.parent or (isinstance(node.parent, nodes.Root) and not self.is_page(node)):
            return 'index#' + meid

        # Find topmost parent
        while not self.is_page(parent):
            parent = parent.parent

        if not node is None:
            node._refid = parent.qid + '#' + meid
            return node._refid
        else:
            return None

    def add_ref_node_id(self, node, elem):
        r = self.refid(node)

        if not r is None:
            elem.set('ref', r)

    def add_ref_id(self, cursor, elem):
        if not cursor:
            return

        if cursor in self.tree.cursor_to_node:
            node = self.tree.cursor_to_node[cursor]
        elif cursor.get_usr() in self.tree.usr_to_node:
            node = self.tree.usr_to_node[cursor.get_usr()]
        else:
            return

        self.add_ref_node_id(node, elem)

    def type_to_xml(self, tp, parent=None):
        elem = ElementTree.Element('type')

        if tp.is_constant_array:
            elem.set('size', str(tp.constant_array_size))
            elem.append(self.type_to_xml(tp.element_type, parent))
        else:
            elem.set('name', tp.typename_for(parent))

        if len(tp.qualifier) > 0:
            elem.set('qualifier', tp.qualifier_string)

        if tp.builtin:
            elem.set('builtin', 'yes')

        if tp.is_out:
            elem.set('out', 'yes')

        if tp.transfer_ownership != 'none':
            elem.set('transfer-ownership', tp.transfer_ownership)

        if tp.allow_none:
            elem.set('allow-none', 'yes')

        self.add_ref_id(tp.decl, elem)
        return elem

    def enumvalue_to_xml(self, node, elem):
        elem.set('value', str(node.value))

    def enum_to_xml(self, node, elem):
        if not node.typedef is None:
            elem.set('typedef', 'yes')

        if node.isclass:
            elem.set('class', 'yes')

    def struct_to_xml(self, node, elem):
        self.class_to_xml(node, elem)

        if not node.typedef is None:
            elem.set('typedef', 'yes')

    def templatetypeparameter_to_xml(self, node, elem):
        dt = node.default_type

        if not dt is None:
            d = ElementTree.Element('default')

            d.append(self.type_to_xml(dt))
            elem.append(d)

    def templatenontypeparameter_to_xml(self, node, elem):
        elem.append(self.type_to_xml(node.type))

    def function_to_xml(self, node, elem):
        if not (isinstance(node, nodes.Constructor) or
                isinstance(node, nodes.Destructor)):
            ret = ElementTree.Element('return')

            if not node.comment is None and hasattr(node.comment, 'returns') and node.comment.returns:
                ret.append(self.doc_to_xml(node, node.comment.returns))

            tp = self.type_to_xml(node.return_type, node.parent)

            ret.append(tp)
            elem.append(ret)

        for arg in node.arguments:
            ret = ElementTree.Element('argument')
            ret.set('name', arg.name)
            ret.set('id', arg.qid)

            if not node.comment is None and arg.name in node.comment.params:
                ret.append(self.doc_to_xml(node, node.comment.params[arg.name]))

            ret.append(self.type_to_xml(arg.type, node.parent))
            elem.append(ret)

    def method_to_xml(self, node, elem):
        self.function_to_xml(node, elem)

        if len(node.override) > 0:
            elem.set('override', 'yes')

        for ov in node.override:
            ovelem = ElementTree.Element('override')

            ovelem.set('name', ov.qid_to(node.qid))
            self.add_ref_node_id(ov, ovelem)

            elem.append(ovelem)

        if node.virtual:
            elem.set('virtual', 'yes')

        if node.static:
            elem.set('static', 'yes')

        if node.abstract:
            elem.set('abstract', 'yes')

    def typedef_to_xml(self, node, elem):
        elem.append(self.type_to_xml(node.type, node))

    def typedef_to_xml_ref(self, node, elem):
        elem.append(self.type_to_xml(node.type, node))

    def variable_to_xml(self, node, elem):
        elem.append(self.type_to_xml(node.type, node.parent))

    def property_to_xml(self, node, elem):
        elem.append(self.type_to_xml(node.type, node.parent))

    def set_access_attribute(self, node, elem):
        if node.access == cindex.CXXAccessSpecifier.PROTECTED:
            elem.set('access', 'protected')
        elif node.access == cindex.CXXAccessSpecifier.PRIVATE:
            elem.set('access', 'private')
        elif node.access == cindex.CXXAccessSpecifier.PUBLIC:
            elem.set('access', 'public')

    def process_bases(self, node, elem, bases, tagname):
        for base in bases:
            child = ElementTree.Element(tagname)

            self.set_access_attribute(base, child)

            child.append(self.type_to_xml(base.type, node))

            if base.node and not base.node.comment is None and base.node.comment.brief:
                child.append(self.doc_to_xml(base.node, base.node.comment.brief, 'brief'))

            elem.append(child)

    def process_subclasses(self, node, elem, subclasses, tagname):
        for subcls in subclasses:
            child = ElementTree.Element(tagname)

            self.set_access_attribute(subcls, child)
            self.add_ref_node_id(subcls, child)

            child.set('name', subcls.qid_to(node.qid))

            if not subcls.comment is None and subcls.comment.brief:
                child.append(self.doc_to_xml(subcls, subcls.comment.brief, 'brief'))

            elem.append(child)

    def class_to_xml(self, node, elem):
        self.process_bases(node, elem, node.bases, 'base')
        self.process_bases(node, elem, node.implements, 'implements')

        self.process_subclasses(node, elem, node.subclasses, 'subclass')
        self.process_subclasses(node, elem, node.implemented_by, 'implementedby')

        hasabstract = False
        allabstract = True

        for method in node.methods:
            if method.abstract:
                hasabstract = True
            else:
                allabstract = False

        if hasabstract:
            if allabstract:
                elem.set('interface', 'true')
            else:
                elem.set('abstract', 'true')

    def field_to_xml(self, node, elem):
        elem.append(self.type_to_xml(node.type, node.parent))

    def doc_to_xml(self, parent, doc, tagname='doc'):
        doce = ElementTree.Element(tagname)

        s = ''
        last = None

        for component in doc.components:
            if isinstance(component, utf8.string):
                s += component
            elif isinstance(component, example.Example):
                # Make highlighting
                if last is None:
                    doce.text = s
                else:
                    last.tail = s

                s = ''

                code = ElementTree.Element('code')
                doce.append(code)

                last = code

                for item in component:
                    if item.classes is None:
                        s += item.text
                    else:
                        last.tail = s

                        s = ''
                        par = code

                        for cls in item.classes:
                            e = ElementTree.Element(cls)

                            par.append(e)
                            par = e

                        par.text = item.text
                        last = par

                if last == code:
                    last.text = s
                else:
                    last.tail = s

                s = ''
                last = code
            else:
                if last is None:
                    doce.text = s
                else:
                    last.tail = s

                s = ''

                nds = component[0]
                refname = component[1]

                # Make multiple refs
                for ci in range(len(nds)):
                    cc = nds[ci]

                    last = ElementTree.Element('ref')

                    if refname:
                        last.text = refname
                    else:
                        last.text = parent.qlbl_from(cc)

                    self.add_ref_node_id(cc, last)

                    if ci != len(nds) - 1:
                        if ci == len(nds) - 2:
                            last.tail = ' and '
                        else:
                            last.tail = ', '

                    doce.append(last)

        if last is None:
            doce.text = s
        else:
            last.tail = s

        return doce

    def call_type_specific(self, node, elem, fn):
        clss = [node.__class__]

        while len(clss) > 0:
            cls = clss[0]
            clss = clss[1:]

            if cls == nodes.Node:
                continue

            nm = cls.__name__.lower() + '_' + fn

            if hasattr(self, nm):
                getattr(self, nm)(node, elem)
                break

            if cls != nodes.Node:
                clss.extend(cls.__bases__)

    def node_to_xml(self, node):
        elem = ElementTree.Element(node.classname)
        props = node.props

        for prop in props:
            if props[prop]:
                elem.set(prop, props[prop])

        if not node.comment is None and node.comment.brief:
            elem.append(self.doc_to_xml(node, node.comment.brief, 'brief'))

        if not node.comment is None and node.comment.doc:
            elem.append(self.doc_to_xml(node, node.comment.doc))

        self.call_type_specific(node, elem, 'to_xml')

        for child in node.sorted_children():
            if child.access == cindex.CXXAccessSpecifier.PRIVATE:
                continue

            self.refid(child)

            if self.is_page(child):
                chelem = self.node_to_xml_ref(child)
            else:
                chelem = self.node_to_xml(child)

            elem.append(chelem)

        return elem

    def templated_to_xml_ref(self, node, element):
        for child in node.sorted_children():
            if not (isinstance(child, nodes.TemplateTypeParameter) or isinstance(child, nodes.TemplateNonTypeParameter)):
                continue

            element.append(self.node_to_xml(child))

    def generate_page(self, node):
        elem = self.node_to_xml(node)
        self.write_xml(elem, node.qid + '.xml')

    def node_to_xml_ref(self, node):
        elem = ElementTree.Element(node.classname)
        props = node.props

        # Add reference item to index
        self.add_ref_node_id(node, elem)

        if 'name' in props:
            elem.set('name', props['name'])

        if not node.comment is None and node.comment.brief:
            elem.append(self.doc_to_xml(node, node.comment.brief, 'brief'))

        self.call_type_specific(node, elem, 'to_xml_ref')

        return elem

    def generate_node(self, node):
        # Ignore private stuff
        if node.access == cindex.CXXAccessSpecifier.PRIVATE:
            return

        self.refid(node)

        if self.is_page(node):
            elem = self.node_to_xml_ref(node)

            self.indexmap[node.parent].append(elem)
            self.indexmap[node] = elem

            self.generate_page(node)
        elif self.is_top(node):
            self.index.append(self.node_to_xml(node))

        if isinstance(node, nodes.Namespace) or isinstance(node, nodes.Category):
            # Go deep for namespaces and categories
            Generator.generate_node(self, node)
        elif isinstance(node, nodes.Class):
            # Go deep, but only for inner classes
            Generator.generate_node(self, node, lambda x: isinstance(x, nodes.Class))

# vi:ts=4:et

########NEW FILE########
__FILENAME__ = includepaths
# This file is part of cldoc.  cldoc is free software: you can
# redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
import os, subprocess

def flags(f):
    devnull = open(os.devnull)

    p = subprocess.Popen(['clang++', '-E', '-xc++'] + f + ['-v', '-'],
                         stdin=devnull,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)

    devnull.close()

    lines = p.communicate()[1].splitlines()
    init = False
    paths = []

    for line in lines:
        if line.startswith('#include <...>'):
            init = True
        elif line.startswith('End of search list.'):
            init = False
        elif init:
            p = line.strip()

            suffix = ' (framework directory)'

            if p.endswith(suffix):
                p = p[:-len(suffix)]

            paths.append(p)

    return ['-I{0}'.format(x) for x in paths] + f

# vi:ts=4:et

########NEW FILE########
__FILENAME__ = inspecttree
# -*- coding: utf-8 -*-
# This file is part of cldoc.  cldoc is free software: you can
# redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

from clang import cindex
import os, sys

def inspect_print_row(a, b, link=None):
    from xml.sax.saxutils import escape

    b = escape(str(b))

    if link:
        b = "<a href='#" + escape(link) + "'>" + b + "</a>"

    print "<tr><td>%s</td><td>%s</td></tr>" % (escape(str(a)), b)

def inspect_print_subtype(name, tp, subtype, indent=1):
    if not subtype or tp == subtype or subtype.kind == cindex.TypeKind.INVALID:
        return

    inspect_print_row('  ' * indent + '→ .' + name + '.kind', subtype.kind)
    inspect_print_row('  ' * indent + '→ .' + name + '.spelling', subtype.kind.spelling)
    inspect_print_row('  ' * indent + '→ .' + name + '.is_const_qualified', subtype.is_const_qualified())

    if subtype.kind == cindex.TypeKind.CONSTANTARRAY:
        etype = subtype.get_array_element_type()
        num = subtype.get_array_size()

        inspect_print_subtype('array_type', subtype, etype, indent + 1)
        inspect_print_row('  ' * (indent + 1) + '→ .size', str(num))

    decl = subtype.get_declaration()

    if decl:
        inspect_print_row('  ' * indent + '→ .' + name + '.declaration', decl.displayname, decl.get_usr())

    inspect_print_subtype('get_canonical', subtype, subtype.get_canonical(), indent + 1)
    inspect_print_subtype('get_pointee', subtype, subtype.get_pointee(), indent + 1)
    inspect_print_subtype('get_result', subtype, subtype.get_result(), indent + 1)

def inspect_cursor(tree, cursor, indent):
    from xml.sax.saxutils import escape

    if not cursor.location.file:
        return

    if not str(cursor.location.file) in tree.files:
        return

    print "<table id='" + escape(cursor.get_usr()) + "' class='cursor' style='margin-left: " + str(indent * 20) + "px;'>"

    inspect_print_row('kind', cursor.kind)
    inspect_print_row('  → .is_declaration', cursor.kind.is_declaration())
    inspect_print_row('  → .is_reference', cursor.kind.is_reference())
    inspect_print_row('  → .is_expression', cursor.kind.is_expression())
    inspect_print_row('  → .is_statement', cursor.kind.is_statement())
    inspect_print_row('  → .is_attribute', cursor.kind.is_attribute())
    inspect_print_row('  → .is_invalid', cursor.kind.is_invalid())
    inspect_print_row('  → .is_preprocessing', cursor.kind.is_preprocessing())

    inspect_print_subtype('type', None, cursor.type, 0)

    inspect_print_row('usr', cursor.get_usr())
    inspect_print_row('spelling', cursor.spelling)
    inspect_print_row('displayname', cursor.displayname)
    inspect_print_row('location', "%s (%d:%d - %d:%d)" % (os.path.basename(str(cursor.location.file)), cursor.extent.start.line, cursor.extent.start.column, cursor.extent.end.line, cursor.extent.end.column))
    inspect_print_row('is_definition', cursor.is_definition())
    inspect_print_row('is_virtual_method', cursor.is_virtual_method())
    inspect_print_row('is_static_method', cursor.is_static_method())

    spec = cursor.access_specifier

    if not spec is None:
        inspect_print_row('access_specifier', spec)

    defi = cursor.get_definition()

    if defi and defi != cursor:
        inspect_print_row('definition', defi.displayname, link=defi.get_usr())

    if cursor.kind == cindex.CursorKind.CXX_METHOD:
        for t in cursor.type.argument_types():
            inspect_print_subtype('argument', None, t)

    print "</table>"

def inspect_cursors(tree, cursors, indent=0):
    for cursor in cursors:
        inspect_cursor(tree, cursor, indent)

        if (not cursor.location.file) or str(cursor.location.file) in tree.files:
            inspect_cursors(tree, cursor.get_children(), indent + 1)

def inspect_tokens(tree, filename, tu):
    it = tu.get_tokens(extent=tu.get_extent(filename, (0, os.stat(filename).st_size)))

    print "<table class='tokens'>"

    for token in it:
        print "<tr>"
        print "<td>%s</td>" % (token.kind,)
        print "<td>" + token.spelling + "</td>"
        print "<td>%s</td>" % (token.cursor.kind,)
        print "<td>%d:%d</td>" % (token.extent.start.line, token.extent.start.column,)
        print "</tr>"

    print "</table>"

def inspect(tree):
    index = cindex.Index.create()

    print """<html>
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8">
<style type='text/css'>
div.filename {
padding: 3px;
background-color: #eee;
}

table.cursor {
border-collapse: collapse;
margin-bottom: 10px;
}

a {
color: #3791db;
}

table.cursor tr td:first-child {
font-weight: bold;
padding-right: 10px;
color: #666;
vertical-align: top;
}
</style>
</head>
<body>"""

    for f in tree.files:
        tu = index.parse(f, tree.flags)

        if not tu:
            sys.stderr.write("Could not parse file %s...\n" % (f,))
            sys.exit(1)

        print "<div class='file'><div class='filename'>" + f + "</div>"

        inspect_tokens(tree, f, tu)

        # Recursively inspect cursors
        inspect_cursors(tree, tu.cursor.get_children())

        print "</div>"

    print "</body>\n</html>"

# vi:ts=4:et

########NEW FILE########
__FILENAME__ = category
# This file is part of cldoc.  cldoc is free software: you can
# redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
from node import Node

class Category(Node):
    def __init__(self, name):
        Node.__init__(self, None, None)

        self._name = name

    @property
    def name(self):
        return self._name

    @property
    def is_unlabeled(self):
        return True

    def sorted_children(self):
        return list(self.children)

# vi:ts=4:et

########NEW FILE########
__FILENAME__ = cclass
# This file is part of cldoc.  cldoc is free software: you can
# redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
from node import Node
from method import Method
from ctype import Type
from cldoc.clang import cindex

class Class(Node):
    kind = cindex.CursorKind.CLASS_DECL

    class Base:
        def __init__(self, cursor, access=cindex.CXXAccessSpecifier.PUBLIC):
            self.cursor = cursor
            self.access = access
            self.type = Type(cursor.type, cursor=cursor)
            self.node = None

    def __init__(self, cursor, comment):
        super(Class, self).__init__(cursor, comment)

        self.process_children = True
        self.current_access = cindex.CXXAccessSpecifier.PRIVATE
        self.bases = []
        self.implements = []
        self.implemented_by = []
        self.subclasses = []
        self.name_to_method = {}

    def _all_bases(self):
        for b in self.bases:
            yield b

        for b in self.implements:
            yield b

    def resolve_bases(self, mapping):
        for b in self.bases:
            tpname = b.type.typename

            if tpname in mapping:
                b.node = mapping[tpname]
                b.node.subclasses.append(self)

        for b in self.implements:
            tpname = b.type.typename

            if tpname in mapping:
                b.node = mapping[tpname]
                b.node.implemented_by.append(self)

    @property
    def resolve_nodes(self):
        for child in Node.resolve_nodes.fget(self):
            yield child

        for base in self._all_bases():
            if base.node and base.access != cindex.CXXAccessSpecifier.PRIVATE:
                yield base.node

                for child in base.node.resolve_nodes:
                    yield child

    def append(self, child):
        super(Class, self).append(child)

        if isinstance(child, Method):
            self.name_to_method[child.name] = child

    @property
    def methods(self):
        for child in self.children:
            if isinstance(child, Method):
                yield child

    def visit(self, cursor, citer):
        if cursor.kind == cindex.CursorKind.CXX_ACCESS_SPEC_DECL:
            self.current_access = cursor.access_specifier
            return []
        elif cursor.kind == cindex.CursorKind.CXX_BASE_SPECIFIER:
            # Add base
            self.bases.append(Class.Base(cursor.type.get_declaration(), cursor.access_specifier))
            return []

        return Node.visit(self, cursor, citer)

    @property
    def force_page(self):
        return True

# vi:ts=4:et

########NEW FILE########
__FILENAME__ = classtemplate
# This file is part of cldoc.  cldoc is free software: you can
# redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
from .node import Node
from .cclass import Class
from .cstruct import Struct
from .templated import Templated

from cldoc.clang import cindex

class StructTemplate(Struct, Templated):
    kind = None

    def __init__(self, cursor, comment):
        super(StructTemplate, self).__init__(cursor, comment)

class ClassTemplate(Class, Templated):
    kind = None

    def __init__(self, cursor, comment):
        super(ClassTemplate, self).__init__(cursor, comment)

class ClassTemplatePlexer(Node):
    kind = cindex.CursorKind.CLASS_TEMPLATE

    def __new__(cls, cursor, comment):
        # Check manually if this is actually a struct, so that we instantiate
        # the right thing. I'm not sure there is another way to do this right now
        l = list(cursor.get_tokens())

        for i in range(len(l)):
            if l[i].kind == cindex.TokenKind.PUNCTUATION and l[i].spelling == '>':
                if i < len(l) - 2:
                    if l[i + 1].kind == cindex.TokenKind.KEYWORD and \
                       l[i + 1].spelling == 'struct':
                        return StructTemplate(cursor, comment)
                break

        return ClassTemplate(cursor, comment)

# vi:ts=4:et

########NEW FILE########
__FILENAME__ = constructor
# This file is part of cldoc.  cldoc is free software: you can
# redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
from method import Method
from cldoc.clang import cindex

class Constructor(Method):
    kind = cindex.CursorKind.CONSTRUCTOR

    def __init__(self, cursor, comment):
        Method.__init__(self, cursor, comment)

# vi:ts=4:et

########NEW FILE########
__FILENAME__ = conversionfunction
# This file is part of cldoc.  cldoc is free software: you can
# redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
from method import Method
from cldoc.clang import cindex

class ConversionFunction(Method):
    kind = cindex.CursorKind.CONVERSION_FUNCTION

    def __init__(self, cursor, comment):
        Method.__init__(self, cursor, comment)

# vi:ts=4:et

########NEW FILE########
__FILENAME__ = cstruct
# This file is part of cldoc.  cldoc is free software: you can
# redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
from cldoc.clang import cindex
from .cclass import Class

class Struct(Class):
    kind = cindex.CursorKind.STRUCT_DECL

    def __init__(self, cursor, comment):
        Class.__init__(self, cursor, comment)

        self.typedef = None
        self.current_access = cindex.CXXAccessSpecifier.PUBLIC

    @property
    def is_anonymous(self):
        return not Class.name.fget(self)

    @property
    def comment(self):
        ret = Class.comment.fget(self)

        if not ret and self.typedef:
            ret = self.typedef.comment

        return ret

    @property
    def name(self):
        if not self.typedef is None:
            # The name is really the one of the typedef
            return self.typedef.name
        else:
            return Class.name.fget(self)

# vi:ts=4:et

########NEW FILE########
__FILENAME__ = ctype
# This file is part of cldoc.  cldoc is free software: you can
# redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
from cldoc.clang import cindex
from node import Node

class Type(Node):
    kindmap = {
        cindex.TypeKind.POINTER: '*',
        cindex.TypeKind.LVALUEREFERENCE: '&',
    }

    namemap = {
        cindex.TypeKind.VOID: 'void',
        cindex.TypeKind.BOOL: 'bool',
        cindex.TypeKind.CHAR_U: 'char',
        cindex.TypeKind.UCHAR: 'unsigned char',
        cindex.TypeKind.CHAR16: 'char16_t',
        cindex.TypeKind.CHAR32: 'char32_t',
        cindex.TypeKind.USHORT: 'unsigned short',
        cindex.TypeKind.UINT: 'unsigned int',
        cindex.TypeKind.ULONG: 'unsigned long',
        cindex.TypeKind.ULONGLONG: 'unsigned long long',
        cindex.TypeKind.UINT128: 'uint128_t',
        cindex.TypeKind.CHAR_S: 'char',
        cindex.TypeKind.SCHAR: 'signed char',
        cindex.TypeKind.WCHAR: 'wchar_t',
        cindex.TypeKind.SHORT: 'unsigned short',
        cindex.TypeKind.INT: 'int',
        cindex.TypeKind.LONG: 'long',
        cindex.TypeKind.LONGLONG: 'long long',
        cindex.TypeKind.INT128: 'int128_t',
        cindex.TypeKind.FLOAT: 'float',
        cindex.TypeKind.DOUBLE: 'double',
        cindex.TypeKind.LONGDOUBLE: 'long double',
        cindex.TypeKind.NULLPTR: 'float',
    }

    def __init__(self, tp, cursor=None):
        Node.__init__(self, None, None)

        self.tp = tp

        self._qualifier = []
        self._declared = None
        self._builtin = False
        self._cursor = cursor

        self.extract(tp)

    @property
    def is_constant_array(self):
        return self.tp.kind == cindex.TypeKind.CONSTANTARRAY

    @property
    def is_out(self):
        if hasattr(self.tp, 'is_out'):
            return self.tp.is_out
        else:
            return False

    @property
    def transfer_ownership(self):
        if hasattr(self.tp, 'transfer_ownership'):
            return self.tp.transfer_ownership
        else:
            return 'none'

    @property
    def allow_none(self):
        if hasattr(self.tp, 'allow_none'):
            return self.tp.allow_none
        else:
            return False

    @property
    def element_type(self):
        return self._element_type

    @property
    def constant_array_size(self):
        return self._array_size

    def _full_typename(self, decl):
        parent = decl.semantic_parent
        meid = decl.displayname

        if not parent or parent.kind == cindex.CursorKind.TRANSLATION_UNIT:
            return meid

        if not meid:
            return self._full_typename(parent)

        parval = self._full_typename(parent)

        if parval:
            return parval + '::' + meid
        else:
            return meid

    def extract(self, tp):
        if tp.is_const_qualified():
            self._qualifier.append('const')

        if hasattr(tp, 'is_builtin'):
            self._builtin = tp.is_builtin()

        if tp.kind in Type.kindmap:
            self.extract(tp.get_pointee())
            self._qualifier.append(Type.kindmap[tp.kind])

            return
        elif tp.kind == cindex.TypeKind.CONSTANTARRAY:
            self._element_type = Type(tp.get_array_element_type())
            self._array_size = tp.get_array_size()

        self._decl = tp.get_declaration()

        if self._decl and self._decl.displayname:
            self._typename = self._full_typename(self._decl)
        elif tp.kind in Type.namemap:
            self._typename = Type.namemap[tp.kind]
            self._builtin = True
        elif tp.kind != cindex.TypeKind.CONSTANTARRAY and hasattr(tp, 'spelling'):
            self._typename = tp.spelling
        elif (not self._cursor is None):
            self._typename = self._cursor.displayname
        else:
            self._typename = ''

    @property
    def builtin(self):
        return self._builtin

    @property
    def typename(self):
        if self.is_constant_array:
            return self._element_type.typename
        else:
            return self._typename

    def typename_for(self, node):
        if self.is_constant_array:
            return self._element_type.typename_for(node)

        if node is None or not '::' in self._typename:
            return self._typename

        return node.qid_from(self._typename)

    @property
    def decl(self):
        return self._decl

    @property
    def qualifier(self):
        return self._qualifier

    @property
    def qualifier_string(self):
        ret = ''

        for x in self._qualifier:
            if x != '*' or (len(ret) != 0 and ret[-1] != '*'):
                ret += ' '

            ret += x

        return ret

# vi:ts=4:et

########NEW FILE########
__FILENAME__ = destructor
# This file is part of cldoc.  cldoc is free software: you can
# redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
from method import Method
from cldoc.clang import cindex

class Destructor(Method):
    kind = cindex.CursorKind.DESTRUCTOR

    def __init__(self, cursor, comment):
        Method.__init__(self, cursor, comment)

# vi:ts=4:et

########NEW FILE########
__FILENAME__ = enum
# This file is part of cldoc.  cldoc is free software: you can
# redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
from node import Node
from cldoc.clang import cindex

class Enum(Node):
    kind = cindex.CursorKind.ENUM_DECL

    def __init__(self, cursor, comment):
        Node.__init__(self, cursor, comment)

        self.typedef = None
        self.process_children = True
        self.isclass = False

        if hasattr(self.cursor, 'get_tokens'):
            try:
                tokens = self.cursor.get_tokens()
                tokens.next()

                tt = tokens.next()

                if tt.kind == cindex.TokenKind.KEYWORD and tt.spelling == 'class':
                    self.isclass = True
            except StopIteration:
                pass

    @property
    def is_anonymous(self):
        return not self.isclass

    @property
    def comment(self):
        ret = Node.comment.fget(self)

        if not ret and self.typedef:
            ret = self.typedef.comment

        return ret

    @property
    def name(self):
        if not self.typedef is None:
            # The name is really the one of the typedef
            return self.typedef.name
        else:
            return Node.name.fget(self)

    def sorted_children(self):
        return list(self.children)

# vi:ts=4:et

########NEW FILE########
__FILENAME__ = enumvalue
# This file is part of cldoc.  cldoc is free software: you can
# redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
from node import Node
from cldoc.clang import cindex

class EnumValue(Node):
    kind = cindex.CursorKind.ENUM_CONSTANT_DECL

    def __init__(self, cursor, comment):
        Node.__init__(self, cursor, comment)

    def compare_sort(self, other):
        if not isinstance(other, EnumValue) or not hasattr(self.cursor, 'location'):
            return Node.compare_sort(self, other)

        loc1 = self.cursor.location
        loc2 = other.cursor.location

        if loc1.line != loc2.line:
            return cmp(loc1.line, loc2.line)
        else:
            return cmp(loc1.column, loc2.column)

    @property
    def value(self):
        return self.cursor.enum_value

# vi:ts=4:et

########NEW FILE########
__FILENAME__ = field
# This file is part of cldoc.  cldoc is free software: you can
# redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
from node import Node
from ctype import Type
from cldoc.clang import cindex

class Field(Node):
    kind = cindex.CursorKind.FIELD_DECL

    def __init__(self, cursor, comment):
        Node.__init__(self, cursor, comment)
        self.type = Type(cursor.type, cursor=cursor)

    def compare_same(self, other):
        return cmp(self.sort_index, other.sort_index)

# vi:ts=4:et

########NEW FILE########
__FILENAME__ = function
# This file is part of cldoc.  cldoc is free software: you can
# redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
from node import Node
from cldoc.clang import cindex
from ctype import Type
from cldoc.comment import Comment
from cldoc.comment import Parser

import re

class Argument:
    def __init__(self, func, cursor):
        self.cursor = cursor
        self.parent = func
        self._type = None

        for child in cursor.get_children():
            if child.kind == cindex.CursorKind.TYPE_REF:
                self._type = Type(self.cursor.type, cursor=child)
                break

        if self._type is None:
            self._type = Type(self.cursor.type)

        self._refid = None

    @property
    def refid(self):
        return self.parent.refid + '::' + self.name

    @property
    def name(self):
        return self.cursor.spelling

    @property
    def type(self):
        return self._type

    @property
    def qid(self):
        return self.parent.qid + '::' + self.name

    @property
    def force_page(self):
        return False

    def semantic_path_until(self, other):
        ret = self.parent.semantic_path_until(other)
        ret.append(self)

        return ret

    def qlbl_from(self, other):
        return self.parent.qlbl_from(other) + '::' + self.name

    def qlbl_to(self, other):
        return other.qlbl_from(self)

    @property
    def semantic_parent(self):
        return self.parent

    @property
    def is_unlabeled(self):
        return False

class Function(Node):
    kind = cindex.CursorKind.FUNCTION_DECL

    def __init__(self, cursor, comment):
        super(Function, self).__init__(cursor, comment)

        self._return_type = Type(self.cursor.type.get_result())
        self._arguments = []

        for child in cursor.get_children():
            if child.kind != cindex.CursorKind.PARM_DECL:
                continue

            self._arguments.append(Argument(self, child))

    @property
    def qid(self):
        return self.name

    @property
    def semantic_parent(self):
        from namespace import Namespace

        if isinstance(self.parent, Namespace):
            return self.parent
        else:
            return None

    @property
    def resolve_nodes(self):
        for arg in self._arguments:
            yield arg

    @property
    def argument_names(self):
        for k in self._arguments:
            yield k.name

    def parse_comment(self):
        super(Function, self).parse_comment()
        self._comment.params = {}

        for pre in self._parsed_comment.preparam:
            self._comment.params[pre.name] = pre.description

        for post in self._parsed_comment.postparam:
            if post.name == 'return':
                self._comment.returns = post.description

    @property
    def return_type(self):
        return self._return_type

    @property
    def arguments(self):
        return list(self._arguments)

# vi:ts=4:et

########NEW FILE########
__FILENAME__ = functiontemplate
# This file is part of cldoc.  cldoc is free software: you can
# redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
from node import Node
from method import Method
from function import Function
from ctype import Type
from templated import Templated

from cldoc.clang import cindex

class FunctionTemplate(Templated, Function):
    kind = None

    def __init__(self, cursor, comment):
        super(FunctionTemplate, self).__init__(cursor, comment)

class MethodTemplate(Templated, Method):
    kind = None

    def __init__(self, cursor, comment):
        super(MethodTemplate, self).__init__(cursor, comment)

class FunctionTemplatePlexer(Node):
    kind = cindex.CursorKind.FUNCTION_TEMPLATE

    def __new__(cls, cursor, comment):
        if not cursor is None and (cursor.semantic_parent.kind == cindex.CursorKind.CLASS_DECL or \
                                   cursor.semantic_parent.kind == cindex.CursorKind.CLASS_TEMPLATE or \
                                   cursor.semantic_parent.kind == cindex.CursorKind.STRUCT_DECL):
            return MethodTemplate(cursor, comment)
        else:
            return FunctionTemplate(cursor, comment)

# vi:ts=4:et

########NEW FILE########
__FILENAME__ = method
# This file is part of cldoc.  cldoc is free software: you can
# redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
from function import Function
from node import Node

from cldoc.clang import cindex
from cldoc.comment import Comment

class Method(Function):
    kind = cindex.CursorKind.CXX_METHOD

    def __init__(self, cursor, comment):
        super(Method, self).__init__(cursor, comment)

        self.static = cursor.is_static_method()
        self.virtual = cursor.is_virtual_method()

        self.abstract = True
        self._override = None

        self.update_abstract(cursor)

    @property
    def qid(self):
        return Node.qid.fget(self)

    @property
    def override(self):
        if not self._override is None:
            return self._override

        # Lookup in bases, recursively
        bases = list(self.parent.bases)
        mname = self.name

        self._override = []

        while len(bases) > 0:
            b = bases[0]
            bases = bases[1:]

            if not b.node:
                continue

            b = b.node

            if mname in b.name_to_method:
                self._override.append(b.name_to_method[mname])
            else:
                # Look in the bases of bases also
                bases = bases + b.bases

        return self._override

    @property
    def comment(self):
        cm = Function.comment.fget(self)

        if not cm:
            return cm

        if cm.text.strip() == '@inherit':
            for ov in self.override:
                ovcm = ov.comment

                if ovcm:
                    self.merge_comment(Comment(ovcm.text, ovcm.location), True)
                    return self._comment

        return cm

    @property
    def semantic_parent(self):
        return Node.semantic_parent.fget(self)

    def update_abstract(self, cursor):
        if cursor.is_definition() or cursor.get_definition():
            self.abstract = False

    def add_ref(self, cursor):
        super(Method, self).add_ref(cursor)
        self.update_abstract(cursor)

# vi:ts=4:et

########NEW FILE########
__FILENAME__ = namespace
# This file is part of cldoc.  cldoc is free software: you can
# redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
from node import Node
from cldoc.clang import cindex
from root import Root

class Namespace(Node):
    kind = cindex.CursorKind.NAMESPACE

    def __init__(self, cursor, comment):
        Node.__init__(self, cursor, comment)

        self.process_children = True

# vi:ts=4:et

########NEW FILE########
__FILENAME__ = node
# This file is part of cldoc.  cldoc is free software: you can
# redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
from cldoc.clang import cindex
from cldoc.comment import Comment
from cldoc.comment import Parser

from cldoc import utf8

import re

class Node(object):
    class SortId:
        CATEGORY = 0
        NAMESPACE = 1
        TEMPLATETYPEPARAMETER = 2
        CLASS = 3
        ENUM = 4
        ENUMVALUE = 5
        FIELD = 6
        TYPEDEF = 7
        CONSTRUCTOR = 8
        DESTRUCTOR = 9
        METHOD = 10
        FUNCTION = 11

    def __init__(self, cursor, comment):
        self.cursor = cursor
        self._comment = comment
        self.children = []
        self.parent = None
        self.access = cindex.CXXAccessSpecifier.PUBLIC
        self._comment_locations = []
        self._refs = []
        self.sort_index = 0
        self.num_anon = 0
        self.anonymous_id = 0
        self._refid = None

        self.sortid = 0
        cls = self.__class__

        while cls.__name__ != 'object':
            nm = cls.__name__.upper()

            if hasattr(Node.SortId, nm):
                self.sortid = getattr(Node.SortId, nm)
                break
            else:
                cls = cls.__base__

        self.process_children = False

        if self._comment:
            self.parse_comment()

    @property
    def refid(self):
        if not self._refid is None:
            return self._refid
        else:
            return self.qid

    @property
    def is_anonymous(self):
        return False

    def qid_from_to(self, nq, mq):
        # Find the minimal required typename from the perspective of <node>
        # to reach our type
        lnq = nq.split('::')
        lmq = mq.split('::')

        if nq == mq:
            return lmq[-1]

        for i in range(min(len(lnq), len(lmq))):
            if lnq[i] != lmq[i]:
                return "::".join(lmq[i:])

        if len(lnq) > len(lmq):
            return lmq[-1]
        else:
            return "::".join(lmq[len(lnq):])

    def qid_from(self, qid):
        return self.qid_from_to(self.qid, qid)

    def qid_to(self, qid):
        return self.qid_from_to(qid, self.qid)

    def semantic_path_until(self, parent):
        ret = []

        if parent == self:
            return [self]

        p = self

        while (not p is None) and p != parent:
            ret.insert(0, p)

            sp = p.semantic_parent
            p = p.parent

            while p != sp:
                if p == parent:
                    return ret

                p = p.parent

        return ret

    @property
    def is_unlabeled(self):
        return False

    def qlbl_from(self, other):
        p = other.semantic_path_until(self)

        i = 0

        while i < (len(p) - 1) and p[i].is_unlabeled:
            i += 1

        return utf8.utf8('::').join(filter(lambda x: x, [q.name for q in p[i:]]))

    def qlbl_to(self, other):
        return other.qlbl_from(self)

    def add_ref(self, cursor):
        self._refs.append(cursor)
        self.add_comment_location(cursor.extent.start)

    def add_comment_location(self, location):
        self._comment_locations.append(location)

    @property
    def comment_locations(self):
        if self.cursor:
            ext = self.cursor.extent

            if not ext is None:
                yield ext.start

        for loc in self._comment_locations:
            yield loc

    def parse_comment(self):
        # Just extract brief and doc
        self._parsed_comment = Parser.parse(self._comment.text)

        if len(self._parsed_comment.brief) > 0:
            self._comment.brief = self._parsed_comment.brief
            self._comment.doc = self._parsed_comment.body

    @property
    def natural_sort_name(self):
        return [int(text) if text.isdigit() else text.lower() for text in re.split('([0-9]+)', self.name)]

    def compare_same(self, other):
        if self.name and other.name:
            return cmp(self.natural_sort_name, other.natural_sort_name)
        else:
            return 0

    def compare_sort(self, other):
        ret = cmp(self.access, other.access)

        if ret == 0:
            ret = cmp(self.sortid, other.sortid)

        if ret == 0:
            ret = self.compare_same(other)

        return ret

    @property
    def resolve_nodes(self):
        for child in self.children:
            yield child

            if child.is_anonymous:
                for ev in child.children:
                    yield ev

    @property
    def name(self):
        if self.cursor is None:
            ret = ''
        else:
            ret = self.cursor.spelling

        if ret == '' and self.anonymous_id > 0:
            return '(anonymous::' + str(self.anonymous_id) + ')'
        else:
            return ret

    def descendants(self):
        for child in self.children:
            yield child

            for d in child.descendants():
                yield d

    def sorted_children(self):
        ret = list(self.children)
        ret.sort(lambda x, y: x.compare_sort(y))

        return ret

    @property
    def semantic_parent(self):
        parent = self.parent

        while (not parent is None) and parent.is_anonymous:
            parent = parent.parent

        return parent

    @property
    def qid(self):
        meid = self.name

        parent = self.semantic_parent

        if not parent:
            return meid
        else:
            q = self.parent.qid

            if not q:
                return meid

            if not meid:
                return q

            return q + '::' + meid

    @property
    def comment(self):
        return self._comment

    @property
    def props(self):
        ret = {
            'id': self.qid,
            'name': self.name,
        }

        if self.is_anonymous:
            ret['anonymous'] = 'yes'

        if self.access == cindex.CXXAccessSpecifier.PROTECTED:
            ret['access'] = 'protected'
        elif self.access == cindex.CXXAccessSpecifier.PRIVATE:
            ret['access'] = 'private'

        return ret

    @property
    def classname(self):
        return self.__class__.__name__.lower()

    def append(self, child):
        child.sort_index = len(self.children)
        self.children.append(child)
        child.parent = self

        if not child.name:
            self.num_anon += 1
            child.anonymous_id = self.num_anon

    def visit(self, cursor, citer):
        return None

    def merge_comment(self, comment, override=False):
        if not comment:
            return

        if not override and self._comment:
            return

        self._comment = comment
        self.parse_comment()

    @staticmethod
    def _subclasses(cls):
        for c in cls.__subclasses__():
            yield c

            for cc in Node._subclasses(c):
                yield cc

    @staticmethod
    def subclasses():
        return Node._subclasses(Node)

    @property
    def force_page(self):
        return False

# vi:ts=4:et

########NEW FILE########
__FILENAME__ = root
# This file is part of cldoc.  cldoc is free software: you can
# redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
from node import Node

class Root(Node):
    def __init__(self):
        Node.__init__(self, None, None)

    @property
    def is_anonymous(self):
        return True

# vi:ts=4:et

########NEW FILE########
__FILENAME__ = templated
# This file is part of cldoc.  cldoc is free software: you can
# redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
from .node import Node
from .templatetypeparameter import TemplateTypeParameter, TemplateNonTypeParameter
from cldoc.comment import Comment
from cldoc.comment import Parser
import re

class Templated(Node):
    def __init__(self, cursor, comment):
        super(Templated, self).__init__(cursor, comment)

        self._template_types = {}
        self._template_type_comments = {}

        self.process_children = True

    @property
    def template_type_names(self):
        for t in self._template_types:
            yield t

    def sorted_children(self):
        return list(self.children)

    def append(self, child):
        if isinstance(child, TemplateTypeParameter) or \
           isinstance(child, TemplateNonTypeParameter):
            self._template_types[child.name] = child

            if child.name in self._template_type_comments:
                if hasattr(self._comment, 'params') and (child.name in self._comment.params):
                    del self._comment.params[child.name]

                child.merge_comment(self._template_type_comments[child.name])

        super(Templated, self).append(child)

    def parse_comment(self):
        super(Templated, self).parse_comment()

        for p in self._parsed_comment.preparam:
            cm = Comment(p.description, self._comment.location)
            self._template_type_comments[p.name] = cm

            if p.name in self._template_types:
                if hasattr(self._comment, 'params') and (p.name in self._comment.params):
                    del self._comment.params[p.name]

                self._template_types[p.name].merge_comment(cm)

# vi:ts=4:et

########NEW FILE########
__FILENAME__ = templatetypeparameter
# This file is part of cldoc.  cldoc is free software: you can
# redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
from .node import Node
from .ctype import Type
from cldoc.clang import cindex

class TemplateTypeParameter(Node):
    kind = cindex.CursorKind.TEMPLATE_TYPE_PARAMETER

    def __init__(self, cursor, comment):
        Node.__init__(self, cursor, comment)

        self._default_type = None

        for child in self.cursor.get_children():
            if child.kind == cindex.CursorKind.TYPE_REF:
                self._default_type = Type(child.type, cursor=child)
                break

    @property
    def name(self):
        return self.cursor.spelling

    @property
    def default_type(self):
        return self._default_type

    @property
    def access(self):
        return cindex.CXXAccessSpecifier.PUBLIC

    @access.setter
    def access(self, val):
        pass

    def compare_same(self, other):
        return cmp(self.sort_index, other.sort_index)

class TemplateNonTypeParameter(Node):
    kind = cindex.CursorKind.TEMPLATE_NON_TYPE_PARAMETER

    def __init__(self, cursor, comment):
        super(TemplateNonTypeParameter, self).__init__(cursor, comment)

        self._type = Type(self.cursor.type, cursor=self.cursor)
        self._default_value = None

        for child in self.cursor.get_children():
            if child.kind == cindex.CursorKind.TYPE_REF:
                continue

            self._default_value = ''.join([t.spelling for t in child.get_tokens()][:-1])
            break

    @property
    def name(self):
        return self.cursor.spelling

    @property
    def access(self):
        return cindex.CXXAccessSpecifier.PUBLIC

    @access.setter
    def access(self, val):
        pass

    @property
    def props(self):
        ret = Node.props.fget(self)
        ret['default'] = self._default_value

        return ret

    @property
    def type(self):
        return self._type

    @property
    def default_value(self):
        return self._default_value

    def compare_same(self, other):
        return cmp(self.sort_index, other.sort_index)

# vi:ts=4:et

########NEW FILE########
__FILENAME__ = typedef
# This file is part of cldoc.  cldoc is free software: you can
# redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
from node import Node
from cldoc.clang import cindex
from ctype import Type

class Typedef(Node):
    kind = cindex.CursorKind.TYPEDEF_DECL

    def __init__(self, cursor, comment):
        Node.__init__(self, cursor, comment)

        self.process_children = True
        self.type = Type(self.cursor.type.get_canonical(), cursor=self.cursor)

    def visit(self, cursor, citer):
        if cursor.kind == cindex.CursorKind.TYPE_REF:
            self.type = Type(cursor.type, cursor=cursor)

        return []



# vi:ts=4:et

########NEW FILE########
__FILENAME__ = union
# This file is part of cldoc.  cldoc is free software: you can
# redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
from node import Node
from cldoc.clang import cindex

class Union(Node):
    kind = cindex.CursorKind.UNION_DECL

    def __init__(self, cursor, comment):
        Node.__init__(self, cursor, comment)

        self.process_children = True
        self.sortid = Node.SortId.FIELD

    @property
    def is_anonymous(self):
        return not self.cursor.spelling

    @property
    def bases(self):
        return []

    def compare_same(self, other):
        return cmp(self.sort_index, other.sort_index)

# vi:ts=4:et

########NEW FILE########
__FILENAME__ = variable
# This file is part of cldoc.  cldoc is free software: you can
# redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
from node import Node
from ctype import Type
from cldoc.clang import cindex

class Variable(Node):
    kind = cindex.CursorKind.VAR_DECL

    def __init__(self, cursor, comment):
        Node.__init__(self, cursor, comment)

        self.type = Type(cursor.type, cursor=cursor)

# vi:ts=4:et

########NEW FILE########
__FILENAME__ = struct
# This file is part of cldoc.  cldoc is free software: you can
# redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
import copy

class Struct(object):
    def __init__(self, **kwargs):
        for key in kwargs:
            setattr(self, key, kwargs[key])

    @staticmethod
    def define(_name, **kwargs):
        defaults = kwargs

        class subclass(Struct):
            def __init__(self, **kwargs):
                defs = copy.deepcopy(defaults)

                for key in kwargs:
                    if not key in defs:
                        raise AttributeError("'{0}' has no attribute '{1}'".format(_name, key))
                    else:
                        defs[key] = kwargs[key]

                super(subclass, self).__init__(**defs)

        subclass.__name__ = _name
        return subclass

########NEW FILE########
__FILENAME__ = tree
# This file is part of cldoc.  cldoc is free software: you can
# redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
# -*- coding: utf-8 -*-

from clang import cindex
import tempfile

from defdict import Defdict

import comment
import nodes
import includepaths
import documentmerger

from . import example
from . import utf8

import os, sys, sets, re, glob, platform

if platform.system() == 'Darwin':
    libclang = '/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/lib/libclang.dylib'

    if os.path.exists(libclang):
        cindex.Config.set_library_path(os.path.dirname(libclang))

class Tree(documentmerger.DocumentMerger):
    def __init__(self, files, flags):
        self.processed = {}
        self.files = [os.path.realpath(f) for f in files]
        self.flags = includepaths.flags(flags)

        # Sort files on sources, then headers
        self.files.sort(lambda a, b: cmp(self.is_header(a), self.is_header(b)))

        self.processing = {}
        self.kindmap = {}

        # Things to skip
        self.kindmap[cindex.CursorKind.USING_DIRECTIVE] = None

        # Create a map from CursorKind to classes representing those cursor
        # kinds.
        for cls in nodes.Node.subclasses():
            if hasattr(cls, 'kind'):
                self.kindmap[cls.kind] = cls

        self.root = nodes.Root()

        self.all_nodes = []
        self.cursor_to_node = Defdict()
        self.usr_to_node = Defdict()
        self.qid_to_node = Defdict()

        # Map from category name to the nodes.Category for that category
        self.category_to_node = Defdict()

        # Map from filename to comment.CommentsDatabase
        self.commentsdbs = Defdict()

        self.qid_to_node[None] = self.root
        self.usr_to_node[None] = self.root

    def is_header(self, filename):
        return filename.endswith('.hh') or filename.endswith('.hpp') or filename.endswith('.h')

    def find_node_comment(self, node):
        for location in node.comment_locations:
            db = self.commentsdbs[location.file.name]

            if db:
                cm = db.lookup(location)

                if cm:
                    return cm

        return None

    def process(self):
        """
        process processes all the files with clang and extracts all relevant
        nodes from the generated AST
        """

        index = cindex.Index.create()
        self.headers = {}

        for f in self.files:
            if f in self.processed:
                continue

            print "Processing `%s'" % (os.path.basename(f),)

            tu = index.parse(f, self.flags)

            if len(tu.diagnostics) != 0:
                fatal = False

                for d in tu.diagnostics:
                    sys.stderr.write(d.format)
                    sys.stderr.write("\n")

                    if d.severity == cindex.Diagnostic.Fatal or \
                       d.severity == cindex.Diagnostic.Error:
                        fatal = True

                if fatal:
                    sys.stderr.write("\nCould not generate documentation due to parser errors\n")
                    sys.exit(1)

            if not tu:
                sys.stderr.write("Could not parse file %s...\n" % (f,))
                sys.exit(1)

            # Extract comments from files and included files that we are
            # supposed to inspect
            extractfiles = [f]

            for inc in tu.get_includes():
                filename = str(inc.include)
                self.headers[filename] = True

                if filename in self.processed or (not filename in self.files) or filename in extractfiles:
                    continue

                extractfiles.append(filename)

            for e in extractfiles:
                db = comment.CommentsDatabase(e, tu)

                self.add_categories(db.category_names)
                self.commentsdbs[e] = db

            self.visit(tu.cursor.get_children())

            for f in self.processing:
                self.processed[f] = True

            self.processing = {}

        # Construct hierarchy of nodes.
        for node in self.all_nodes:
            q = node.qid

            if node.parent is None:
                par = self.find_parent(node)

                # Lookup categories for things in the root
                if (par is None or par == self.root) and (not node.cursor is None):
                    location = node.cursor.extent.start
                    db = self.commentsdbs[location.file.name]

                    if db:
                        par = self.category_to_node[db.lookup_category(location)]

                if par is None:
                    par = self.root

                par.append(node)

            # Resolve comment
            cm = self.find_node_comment(node)

            if cm:
                node.merge_comment(cm)

        # Keep track of classes to resolve bases and subclasses
        classes = {}

        # Map final qid to node
        for node in self.all_nodes:
            q = node.qid
            self.qid_to_node[q] = node

            if isinstance(node, nodes.Class):
                classes[q] = node

        # Resolve bases and subclasses
        for qid in classes:
            classes[qid].resolve_bases(classes)

        self.markup_code(index)

    def markup_code(self, index):
        for node in self.all_nodes:
            if node.comment is None:
                continue

            if not node.comment.doc:
                continue

            comps = node.comment.doc.components

            for i in range(len(comps)):
                component = comps[i]

                if not isinstance(component, comment.Comment.Example):
                    continue

                text = str(component)

                tmpfile = tempfile.NamedTemporaryFile(delete=False)
                tmpfile.write(text)
                filename = tmpfile.name
                tmpfile.close()

                tu = index.parse(filename, self.flags, options=1)
                tokens = tu.get_tokens(extent=tu.get_extent(filename, (0, os.stat(filename).st_size)))
                os.unlink(filename)

                hl = []
                incstart = None

                for token in tokens:
                    start = token.extent.start.offset
                    end = token.extent.end.offset

                    if token.kind == cindex.TokenKind.KEYWORD:
                        hl.append((start, end, 'keyword'))
                        continue
                    elif token.kind == cindex.TokenKind.COMMENT:
                        hl.append((start, end, 'comment'))

                    cursor = token.cursor

                    if cursor.kind == cindex.CursorKind.PREPROCESSING_DIRECTIVE:
                        hl.append((start, end, 'preprocessor'))
                    elif cursor.kind == cindex.CursorKind.INCLUSION_DIRECTIVE and incstart is None:
                        incstart = cursor
                    elif (not incstart is None) and \
                         token.kind == cindex.TokenKind.PUNCTUATION and \
                         token.spelling == '>':
                        hl.append((incstart.extent.start.offset, end, 'preprocessor'))
                        incstart = None

                ex = example.Example()
                lastpos = 0

                for ih in range(len(hl)):
                    h = hl[ih]

                    ex.append(text[lastpos:h[0]])
                    ex.append(text[h[0]:h[1]], h[2])

                    lastpos = h[1]

                ex.append(text[lastpos:])
                comps[i] = ex

    def match_ref(self, child, name):
        if isinstance(name, utf8.string):
            return name == child.name
        else:
            return name.match(child.name)

    def find_ref(self, node, name, goup):
        if node is None:
            return []

        ret = []

        for child in node.resolve_nodes:
            if self.match_ref(child, name):
                ret.append(child)

        if goup and len(ret) == 0:
            return self.find_ref(node.parent, name, True)
        else:
            return ret

    def cross_ref(self, node = None):
        if node is None:
            node = self.root

        if not node.comment is None:
            node.comment.resolve_refs(self.find_ref, node)

        for child in node.children:
            self.cross_ref(child)

    def decl_on_c_struct(self, node, tp):
        n = self.cursor_to_node[tp.decl]

        if isinstance(n, nodes.Struct) or \
           isinstance(n, nodes.Typedef) or \
           isinstance(n, nodes.Enum):
            return n

        return None

    def c_function_is_constructor(self, node):
        hints = ['new', 'init', 'alloc', 'create']

        for hint in hints:
            if node.name.startswith(hint + "_") or \
               node.name.endswith("_" + hint):
                return True

        return False

    def node_on_c_struct(self, node):
        if isinstance(node, nodes.Method) or \
           not isinstance(node, nodes.Function):
            return None

        decl = None

        if self.c_function_is_constructor(node):
            decl = self.decl_on_c_struct(node, node.return_type)

        if not decl:
            args = node.arguments

            if len(args) > 0:
                decl = self.decl_on_c_struct(node, args[0].type)

        return decl

    def find_parent(self, node):
        cursor = node.cursor

        # If node is a C function, then see if we should group it to a struct
        parent = self.node_on_c_struct(node)

        if parent:
            return parent

        while cursor:
            cursor = cursor.semantic_parent
            parent = self.cursor_to_node[cursor]

            if parent:
                return parent

        return self.root

    def register_node(self, node, parent=None):
        self.all_nodes.append(node)

        self.usr_to_node[node.cursor.get_usr()] = node
        self.cursor_to_node[node.cursor] = node

        # Typedefs in clang are not parents of typedefs, but we like it better
        # that way, explicitly set the parent directly here
        if parent and isinstance(parent, nodes.Typedef):
            parent.append(node)

        if parent and hasattr(parent, 'current_access'):
            node.access = parent.current_access

    def register_anon_typedef(self, node, parent):
        node.typedef = parent
        node.add_comment_location(parent.cursor.extent.start)

        self.all_nodes.remove(parent)

        # Map references to the typedef directly to the node
        self.usr_to_node[parent.cursor.get_usr()] = node
        self.cursor_to_node[parent.cursor] = node

    def cursor_is_exposed(self, cursor):
        # Only cursors which are in headers are exposed.
        filename = str(cursor.location.file)
        return filename in self.headers or self.is_header(filename)

    def visit(self, citer, parent=None):
        """
        visit iterates over the provided cursor iterator and creates nodes
        from the AST cursors.
        """
        if not citer:
            return

        while True:
            try:
                item = citer.next()
            except StopIteration:
                return

            # Check the source of item
            if not item.location.file:
                self.visit(item.get_children())
                continue

            # Ignore files we already processed
            if str(item.location.file) in self.processed:
                continue

            # Ignore files other than the ones we are scanning for
            if not str(item.location.file) in self.files:
                continue

            # Ignore unexposed things
            if item.kind == cindex.CursorKind.UNEXPOSED_DECL:
                self.visit(item.get_children(), parent)
                continue

            self.processing[str(item.location.file)] = True

            if item.kind in self.kindmap:
                cls = self.kindmap[item.kind]

                if not cls:
                    # Skip
                    continue

                # see if we already have a node for this thing
                node = self.usr_to_node[item.get_usr()]

                if not node:
                    # Only register new nodes if they are exposed.
                    if self.cursor_is_exposed(item):
                        node = cls(item, None)
                        self.register_node(node, parent)

                elif isinstance(parent, nodes.Typedef) and isinstance(node, nodes.Struct):
                    # Typedefs are handled a bit specially because what happens
                    # is that clang first exposes an unnamed struct/enum, and
                    # then exposes the typedef, with as a child again the
                    # cursor to the already defined struct/enum. This is a
                    # bit reversed as to how we normally process things.
                    self.register_anon_typedef(node, parent)
                else:
                    self.cursor_to_node[item] = node
                    node.add_ref(item)

                if node and node.process_children:
                    self.visit(item.get_children(), node)
            else:
                par = self.cursor_to_node[item.semantic_parent]

                if not par:
                    par = parent

                if par:
                    ret = par.visit(item, citer)

                    if not ret is None:
                        for node in ret:
                            self.register_node(node, par)

                ignoretop = [cindex.CursorKind.TYPE_REF, cindex.CursorKind.PARM_DECL]

                if (not par or ret is None) and not item.kind in ignoretop:
                    sys.stderr.write("Unhandled cursor: %s\n" % (item.kind))

# vi:ts=4:et

########NEW FILE########
__FILENAME__ = utf8
try:
    unicode # Just to see if it exists
    basecls = unicode

    def makeutf8(s):
        if not isinstance(s, unicode):
            if hasattr(s, '__unicode__'):
                return unicode(s)

            return str(s).decode('utf-8')

        return s
except:
    basecls = str

    def makeutf8(s):
        if not isinstance(s, str):
            if hasattr(s, '__str__'):
                return str(s)
            elif hasattr(s, '__bytes__'):
                return s.__bytes__().decode('utf-8')

        return s

string = basecls

class utf8(string):
    def __init__(self, s):
        super(utf8, self).__init__(makeutf8(s))

    def __str__(self):
        if not isinstance(self, str):
            return self.encode('utf-8')
        else:
            return self

    def __bytes__(self):
        return self.encode('utf-8')

    def __unicode__(self):
        return self

    def __add__(self, other):
        return utf8(super(utf8, self).__add__(makeutf8(other)))

# vi:ts=4:et

########NEW FILE########
