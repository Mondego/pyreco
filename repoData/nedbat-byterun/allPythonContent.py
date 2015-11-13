__FILENAME__ = execfile
"""Execute files of Python code."""

import imp
import os
import sys
import tokenize

from .pyvm2 import VirtualMachine


# This code is ripped off from coverage.py.  Define things it expects.
try:
    open_source = tokenize.open     # pylint: disable=E1101
except:
    def open_source(fname):
        """Open a source file the best way."""
        return open(fname, "rU")

NoSource = Exception


def exec_code_object(code, env):
    vm = VirtualMachine()
    vm.run_code(code, f_globals=env)


# from coverage.py:

try:
    # In Py 2.x, the builtins were in __builtin__
    BUILTINS = sys.modules['__builtin__']
except KeyError:
    # In Py 3.x, they're in builtins
    BUILTINS = sys.modules['builtins']


def rsplit1(s, sep):
    """The same as s.rsplit(sep, 1), but works in 2.3"""
    parts = s.split(sep)
    return sep.join(parts[:-1]), parts[-1]


def run_python_module(modulename, args):
    """Run a python module, as though with ``python -m name args...``.

    `modulename` is the name of the module, possibly a dot-separated name.
    `args` is the argument array to present as sys.argv, including the first
    element naming the module being executed.

    """
    openfile = None
    glo, loc = globals(), locals()
    try:
        try:
            # Search for the module - inside its parent package, if any - using
            # standard import mechanics.
            if '.' in modulename:
                packagename, name = rsplit1(modulename, '.')
                package = __import__(packagename, glo, loc, ['__path__'])
                searchpath = package.__path__
            else:
                packagename, name = None, modulename
                searchpath = None  # "top-level search" in imp.find_module()
            openfile, pathname, _ = imp.find_module(name, searchpath)

            # Complain if this is a magic non-file module.
            if openfile is None and pathname is None:
                raise NoSource(
                    "module does not live in a file: %r" % modulename
                    )

            # If `modulename` is actually a package, not a mere module, then we
            # pretend to be Python 2.7 and try running its __main__.py script.
            if openfile is None:
                packagename = modulename
                name = '__main__'
                package = __import__(packagename, glo, loc, ['__path__'])
                searchpath = package.__path__
                openfile, pathname, _ = imp.find_module(name, searchpath)
        except ImportError:
            _, err, _ = sys.exc_info()
            raise NoSource(str(err))
    finally:
        if openfile:
            openfile.close()

    # Finally, hand the file off to run_python_file for execution.
    args[0] = pathname
    run_python_file(pathname, args, package=packagename)


def run_python_file(filename, args, package=None):
    """Run a python file as if it were the main program on the command line.

    `filename` is the path to the file to execute, it need not be a .py file.
    `args` is the argument array to present as sys.argv, including the first
    element naming the file being executed.  `package` is the name of the
    enclosing package, if any.

    """
    # Create a module to serve as __main__
    old_main_mod = sys.modules['__main__']
    main_mod = imp.new_module('__main__')
    sys.modules['__main__'] = main_mod
    main_mod.__file__ = filename
    if package:
        main_mod.__package__ = package
    main_mod.__builtins__ = BUILTINS

    # Set sys.argv and the first path element properly.
    old_argv = sys.argv
    old_path0 = sys.path[0]
    sys.argv = args
    if package:
        sys.path[0] = ''
    else:
        sys.path[0] = os.path.abspath(os.path.dirname(filename))

    try:
        # Open the source file.
        try:
            source_file = open_source(filename)
        except IOError:
            raise NoSource("No file to run: %r" % filename)

        try:
            source = source_file.read()
        finally:
            source_file.close()

        # We have the source.  `compile` still needs the last line to be clean,
        # so make sure it is, then compile a code object from it.
        if not source or source[-1] != '\n':
            source += '\n'
        code = compile(source, filename, "exec")

        # Execute the source file.
        exec_code_object(code, main_mod.__dict__)
    finally:
        # Restore the old __main__
        sys.modules['__main__'] = old_main_mod

        # Restore the old argv and path
        sys.argv = old_argv
        sys.path[0] = old_path0

########NEW FILE########
__FILENAME__ = pyobj
"""Implementations of Python fundamental objects for Byterun."""

import collections
import inspect
import types

import six

PY3, PY2 = six.PY3, not six.PY3


def make_cell(value):
    # Thanks to Alex Gaynor for help with this bit of twistiness.
    # Construct an actual cell object by creating a closure right here,
    # and grabbing the cell object out of the function we create.
    fn = (lambda x: lambda: x)(value)
    if PY3:
        return fn.__closure__[0]
    else:
        return fn.func_closure[0]


class Function(object):
    __slots__ = [
        'func_code', 'func_name', 'func_defaults', 'func_globals',
        'func_locals', 'func_dict', 'func_closure',
        '__name__', '__dict__', '__doc__',
        '_vm', '_func',
    ]

    def __init__(self, name, code, globs, defaults, closure, vm):
        self._vm = vm
        self.func_code = code
        self.func_name = self.__name__ = name or code.co_name
        self.func_defaults = tuple(defaults)
        self.func_globals = globs
        self.func_locals = self._vm.frame.f_locals
        self.__dict__ = {}
        self.func_closure = closure
        self.__doc__ = code.co_consts[0] if code.co_consts else None

        # Sometimes, we need a real Python function.  This is for that.
        kw = {
            'argdefs': self.func_defaults,
        }
        if closure:
            kw['closure'] = tuple(make_cell(0) for _ in closure)
        self._func = types.FunctionType(code, globs, **kw)

    def __repr__(self):         # pragma: no cover
        return '<Function %s at 0x%08x>' % (
            self.func_name, id(self)
        )

    def __get__(self, instance, owner):
        if instance is not None:
            return Method(instance, owner, self)
        if PY2:
            return Method(None, owner, self)
        else:
            return self

    def __call__(self, *args, **kwargs):
        if PY2 and self.func_name in ["<setcomp>", "<dictcomp>", "<genexpr>"]:
            # D'oh! http://bugs.python.org/issue19611 Py2 doesn't know how to
            # inspect set comprehensions, dict comprehensions, or generator
            # expressions properly.  They are always functions of one argument,
            # so just do the right thing.
            assert len(args) == 1 and not kwargs, "Surprising comprehension!"
            callargs = {".0": args[0]}
        else:
            try:
                callargs = inspect.getcallargs(self._func, *args, **kwargs)
            except Exception as e:
                import pudb;pudb.set_trace() # -={XX}=-={XX}=-={XX}=- 
                raise
        frame = self._vm.make_frame(
            self.func_code, callargs, self.func_globals, self.func_locals
        )
        CO_GENERATOR = 32           # flag for "this code uses yield"
        if self.func_code.co_flags & CO_GENERATOR:
            gen = Generator(frame, self._vm)
            frame.generator = gen
            retval = gen
        else:
            retval = self._vm.run_frame(frame)
        return retval


class Class(object):
    def __init__(self, name, bases, methods):
        self.__name__ = name
        self.__bases__ = bases
        self.locals = dict(methods)

    def __call__(self, *args, **kw):
        return Object(self, self.locals, args, kw)

    def __repr__(self):         # pragma: no cover
        return '<Class %s at 0x%08x>' % (self.__name__, id(self))

    def __getattr__(self, name):
        try:
            val = self.locals[name]
        except KeyError:
            raise AttributeError("Fooey: %r" % (name,))
        # Check if we have a descriptor
        get = getattr(val, '__get__', None)
        if get:
            return get(None, self)
        # Not a descriptor, return the value.
        return val


class Object(object):
    def __init__(self, _class, methods, args, kw):
        self._class = _class
        self.locals = methods
        if '__init__' in methods:
            methods['__init__'](self, *args, **kw)

    def __repr__(self):         # pragma: no cover
        return '<%s Instance at 0x%08x>' % (self._class.__name__, id(self))

    def __getattr__(self, name):
        try:
            val = self.locals[name]
        except KeyError:
            raise AttributeError(
                "%r object has no attribute %r" % (self._class.__name__, name)
            )
        # Check if we have a descriptor
        get = getattr(val, '__get__', None)
        if get:
            return get(self, self._class)
        # Not a descriptor, return the value.
        return val


class Method(object):
    def __init__(self, obj, _class, func):
        self.im_self = obj
        self.im_class = _class
        self.im_func = func

    def __repr__(self):         # pragma: no cover
        name = "%s.%s" % (self.im_class.__name__, self.im_func.func_name)
        if self.im_self is not None:
            return '<Bound Method %s of %s>' % (name, self.im_self)
        else:
            return '<Unbound Method %s>' % (name,)

    def __call__(self, *args, **kwargs):
        if self.im_self is not None:
            return self.im_func(self.im_self, *args, **kwargs)
        else:
            return self.im_func(*args, **kwargs)


class Cell(object):
    """A fake cell for closures.

    Closures keep names in scope by storing them not in a frame, but in a
    separate object called a cell.  Frames share references to cells, and
    the LOAD_DEREF and STORE_DEREF opcodes get and set the value from cells.

    This class acts as a cell, though it has to jump through two hoops to make
    the simulation complete:

        1. In order to create actual FunctionType functions, we have to have
           actual cell objects, which are difficult to make. See the twisty
           double-lambda in __init__.

        2. Actual cell objects can't be modified, so to implement STORE_DEREF,
           we store a one-element list in our cell, and then use [0] as the
           actual value.

    """
    def __init__(self, value):
        self.contents = value

    def get(self):
        return self.contents

    def set(self, value):
        self.contents = value


Block = collections.namedtuple("Block", "type, handler, level")


class Frame(object):
    def __init__(self, f_code, f_globals, f_locals, f_back):
        self.f_code = f_code
        self.f_globals = f_globals
        self.f_locals = f_locals
        self.f_back = f_back
        if f_back:
            self.f_builtins = f_back.f_builtins
        else:
            self.f_builtins = f_locals['__builtins__']
            if hasattr(self.f_builtins, '__dict__'):
                self.f_builtins = self.f_builtins.__dict__

        self.f_lineno = f_code.co_firstlineno
        self.f_lasti = 0

        if f_code.co_cellvars:
            self.cells = {}
            if not f_back.cells:
                f_back.cells = {}
            for var in f_code.co_cellvars:
                # Make a cell for the variable in our locals, or None.
                cell = Cell(self.f_locals.get(var))
                f_back.cells[var] = self.cells[var] = cell
        else:
            self.cells = None

        if f_code.co_freevars:
            if not self.cells:
                self.cells = {}
            for var in f_code.co_freevars:
                assert self.cells is not None
                assert f_back.cells, "f_back.cells: %r" % (f_back.cells,)
                self.cells[var] = f_back.cells[var]

        self.block_stack = []
        self.generator = None

    def __repr__(self):         # pragma: no cover
        return '<Frame at 0x%08x: %r @ %d>' % (
            id(self), self.f_code.co_filename, self.f_lineno
        )

    def line_number(self):
        """Get the current line number the frame is executing."""
        # We don't keep f_lineno up to date, so calculate it based on the
        # instruction address and the line number table.
        lnotab = self.f_code.co_lnotab
        byte_increments = six.iterbytes(lnotab[0::2])
        line_increments = six.iterbytes(lnotab[1::2])

        byte_num = 0
        line_num = self.f_code.co_firstlineno

        for byte_incr, line_incr in zip(byte_increments, line_increments):
            byte_num += byte_incr
            if byte_num > self.f_lasti:
                break
            line_num += line_incr

        return line_num


class Generator(object):
    def __init__(self, g_frame, vm):
        self.gi_frame = g_frame
        self.vm = vm
        self.first = True
        self.finished = False

    def __iter__(self):
        return self

    def next(self):
        # Ordinary iteration is like sending None into a generator.
        if not self.first:
            self.vm.push(None)
        self.first = False
        # To get the next value from an iterator, push its frame onto the
        # stack, and let it run.
        val = self.vm.resume_frame(self.gi_frame)
        if self.finished:
            raise StopIteration
        return val

    __next__ = next

########NEW FILE########
__FILENAME__ = pyvm2
"""A pure-Python Python bytecode interpreter."""
# Based on:
# pyvm2 by Paul Swartz (z3p), from http://www.twistedmatrix.com/users/z3p/

from __future__ import print_function, division
import dis
import inspect
import linecache
import logging
import operator
import sys

import six
from six.moves import reprlib

PY3, PY2 = six.PY3, not six.PY3

from .pyobj import Frame, Block, Method, Object, Function, Class, Generator

log = logging.getLogger(__name__)

if six.PY3:
    byteint = lambda b: b
else:
    byteint = ord

# Create a repr that won't overflow.
repr_obj = reprlib.Repr()
repr_obj.maxother = 120
repper = repr_obj.repr


class VirtualMachineError(Exception):
    """For raising errors in the operation of the VM."""
    pass


class VirtualMachine(object):
    def __init__(self):
        # The call stack of frames.
        self.frames = []
        # The current frame.
        self.frame = None
        # The data stack.
        self.stack = []
        self.return_value = None
        self.last_exception = None

    def top(self):
        """Return the value at the top of the stack, with no changes."""
        return self.stack[-1]

    def pop(self, i=0):
        """Pop a value from the stack.

        Default to the top of the stack, but `i` can be a count from the top
        instead.

        """
        return self.stack.pop(-1-i)

    def push(self, *vals):
        """Push values onto the value stack."""
        self.stack.extend(vals)

    def popn(self, n):
        """Pop a number of values from the value stack.

        A list of `n` values is returned, the deepest value first.

        """
        if n:
            ret = self.stack[-n:]
            self.stack[-n:] = []
            return ret
        else:
            return []

    def peek(self, n):
        """Get a value `n` entries down in the stack, without changing the stack."""
        return self.stack[-n]

    def jump(self, jump):
        """Move the bytecode pointer to `jump`, so it will execute next."""
        self.frame.f_lasti = jump

    def push_block(self, type, handler=None, level=None):
        if level is None:
            level = len(self.stack)
        self.frame.block_stack.append(Block(type, handler, level))

    def pop_block(self):
        return self.frame.block_stack.pop()

    def make_frame(self, code, callargs={}, f_globals=None, f_locals=None):
        log.info("make_frame: code=%r, callargs=%s" % (code, repper(callargs)))
        if f_globals is not None:
            f_globals = f_globals
            if f_locals is None:
                f_locals = f_globals
        elif self.frames:
            f_globals = self.frame.f_globals
            f_locals = {}
        else:
            f_globals = f_locals = {
                '__builtins__': __builtins__,
                '__name__': '__main__',
                '__doc__': None,
                '__package__': None,
            }
        f_locals.update(callargs)
        frame = Frame(code, f_globals, f_locals, self.frame)
        return frame

    def push_frame(self, frame):
        self.frames.append(frame)
        self.frame = frame

    def pop_frame(self):
        self.frames.pop()
        if self.frames:
            self.frame = self.frames[-1]
        else:
            self.frame = None

    def print_frames(self):
        """Print the call stack, for debugging."""
        for f in self.frames:
            filename = f.f_code.co_filename
            lineno = f.line_number()
            print('  File "%s", line %d, in %s' % (
                filename, lineno, f.f_code.co_name
            ))
            linecache.checkcache(filename)
            line = linecache.getline(filename, lineno, f.f_globals)
            if line:
                print('    ' + line.strip())

    def resume_frame(self, frame):
        frame.f_back = self.frame
        val = self.run_frame(frame)
        frame.f_back = None
        return val

    def run_code(self, code, f_globals=None, f_locals=None):
        frame = self.make_frame(code, f_globals=f_globals, f_locals=f_locals)
        val = self.run_frame(frame)
        # Check some invariants
        if self.frames:            # pragma: no cover
            raise VirtualMachineError("Frames left over!")
        if self.stack:             # pragma: no cover
            raise VirtualMachineError("Data left on stack! %r" % self.stack)

        return val

    def unwind_block(self, block):
        if block.type == 'except-handler':
            offset = 3
        else:
            offset = 0

        while len(self.stack) > block.level + offset:
            self.pop()

        if block.type == 'except-handler':
            tb, value, exctype = self.popn(3)
            self.last_exception = exctype, value, tb

    def run_frame(self, frame):
        """Run a frame until it returns (somehow).

        Exceptions are raised, the return value is returned.

        """
        self.push_frame(frame)
        while True:
            opoffset = frame.f_lasti
            byteCode = byteint(frame.f_code.co_code[opoffset])
            frame.f_lasti += 1
            byteName = dis.opname[byteCode]
            arg = None
            arguments = []
            if byteCode >= dis.HAVE_ARGUMENT:
                arg = frame.f_code.co_code[frame.f_lasti:frame.f_lasti+2]
                frame.f_lasti += 2
                intArg = byteint(arg[0]) + (byteint(arg[1]) << 8)
                if byteCode in dis.hasconst:
                    arg = frame.f_code.co_consts[intArg]
                elif byteCode in dis.hasfree:
                    if intArg < len(frame.f_code.co_cellvars):
                        arg = frame.f_code.co_cellvars[intArg]
                    else:
                        var_idx = intArg - len(frame.f_code.co_cellvars)
                        arg = frame.f_code.co_freevars[var_idx]
                elif byteCode in dis.hasname:
                    arg = frame.f_code.co_names[intArg]
                elif byteCode in dis.hasjrel:
                    arg = frame.f_lasti + intArg
                elif byteCode in dis.hasjabs:
                    arg = intArg
                elif byteCode in dis.haslocal:
                    arg = frame.f_code.co_varnames[intArg]
                else:
                    arg = intArg
                arguments = [arg]

            if log.isEnabledFor(logging.INFO):
                op = "%d: %s" % (opoffset, byteName)
                if arguments:
                    op += " %r" % (arguments[0],)
                indent = "    "*(len(self.frames)-1)
                stack_rep = repper(self.stack)
                block_stack_rep = repper(self.frame.block_stack)

                log.info("  %sdata: %s" % (indent, stack_rep))
                log.info("  %sblks: %s" % (indent, block_stack_rep))
                log.info("%s%s" % (indent, op))

            # When unwinding the block stack, we need to keep track of why we
            # are doing it.
            why = None

            try:
                if byteName.startswith('UNARY_'):
                    self.unaryOperator(byteName[6:])
                elif byteName.startswith('BINARY_'):
                    self.binaryOperator(byteName[7:])
                elif byteName.startswith('INPLACE_'):
                    self.inplaceOperator(byteName[8:])
                elif 'SLICE+' in byteName:
                    self.sliceOperator(byteName)
                else:
                    # dispatch
                    bytecode_fn = getattr(self, 'byte_%s' % byteName, None)
                    if not bytecode_fn:            # pragma: no cover
                        raise VirtualMachineError(
                            "unknown bytecode type: %s" % byteName
                        )
                    why = bytecode_fn(*arguments)

            except:
                # deal with exceptions encountered while executing the op.
                self.last_exception = sys.exc_info()[:2] + (None,)
                log.exception("Caught exception during execution")
                why = 'exception'

            # Deal with any block management we need to do.

            if why == 'exception':
                # TODO: ceval calls PyTraceBack_Here, not sure what that does.
                pass

            if why == 'reraise':
                why = 'exception'

            if why != 'yield':
                while why and frame.block_stack:

                    assert why != 'yield'

                    block = frame.block_stack[-1]
                    if block.type == 'loop' and why == 'continue':
                        self.jump(self.return_value)
                        why = None
                        break

                    self.pop_block()
                    self.unwind_block(block)

                    if block.type == 'loop' and why == 'break':
                        why = None
                        self.jump(block.handler)
                        break

                    if PY2:
                        if (
                            block.type == 'finally' or
                            (block.type == 'setup-except' and why == 'exception') or
                            block.type == 'with'
                        ):
                            if why == 'exception':
                                exctype, value, tb = self.last_exception
                                self.push(tb, value, exctype)
                            else:
                                if why in ('return', 'continue'):
                                    self.push(self.return_value)
                                self.push(why)

                            why = None
                            self.jump(block.handler)
                            break
                    elif PY3:
                        if (
                            why == 'exception' and
                            block.type in ['setup-except', 'finally']
                        ):
                            self.push_block('except-handler')
                            exctype, value, tb = self.last_exception
                            self.push(tb, value, exctype)
                            # PyErr_Normalize_Exception goes here
                            self.push(tb, value, exctype)
                            why = None
                            self.jump(block.handler)

                        elif block.type == 'finally':
                            if why in ('return', 'continue'):
                                self.push(self.return_value)
                            self.push(why)

                            why = None
                            self.jump(block.handler)
                            break

            if why:
                break

        self.pop_frame()

        if why == 'exception':
            six.reraise(*self.last_exception)

        return self.return_value



    ## Stack manipulation

    def byte_LOAD_CONST(self, const):
        self.push(const)

    def byte_POP_TOP(self):
        self.pop()

    def byte_DUP_TOP(self):
        self.push(self.top())

    def byte_DUP_TOPX(self, count):
        items = self.popn(count)
        for i in [1, 2]:
            self.push(*items)

    def byte_DUP_TOP_TWO(self):
        # Py3 only
        a, b = self.popn(2)
        self.push(a, b, a, b)

    def byte_ROT_TWO(self):
        a, b = self.popn(2)
        self.push(b, a)

    def byte_ROT_THREE(self):
        a, b, c = self.popn(3)
        self.push(c, a, b)

    def byte_ROT_FOUR(self):
        a, b, c, d = self.popn(4)
        self.push(d, a, b, c)

    ## Names

    def byte_LOAD_NAME(self, name):
        frame = self.frame
        if name in frame.f_locals:
            val = frame.f_locals[name]
        elif name in frame.f_globals:
            val = frame.f_globals[name]
        elif name in frame.f_builtins:
            val = frame.f_builtins[name]
        else:
            raise NameError("name '%s' is not defined" % name)
        self.push(val)

    def byte_STORE_NAME(self, name):
        self.frame.f_locals[name] = self.pop()

    def byte_DELETE_NAME(self, name):
        del self.frame.f_locals[name]

    def byte_LOAD_FAST(self, name):
        if name in self.frame.f_locals:
            val = self.frame.f_locals[name]
        else:
            raise UnboundLocalError(
                "local variable '%s' referenced before assignment" % name
            )
        self.push(val)

    def byte_STORE_FAST(self, name):
        self.frame.f_locals[name] = self.pop()

    def byte_DELETE_FAST(self, name):
        del self.frame.f_locals[name]

    def byte_LOAD_GLOBAL(self, name):
        f = self.frame
        if name in f.f_globals:
            val = f.f_globals[name]
        elif name in f.f_builtins:
            val = f.f_builtins[name]
        else:
            raise NameError("global name '%s' is not defined" % name)
        self.push(val)

    def byte_LOAD_DEREF(self, name):
        self.push(self.frame.cells[name].get())

    def byte_STORE_DEREF(self, name):
        self.frame.cells[name].set(self.pop())

    def byte_LOAD_LOCALS(self):
        self.push(self.frame.f_locals)

    ## Operators

    UNARY_OPERATORS = {
        'POSITIVE': operator.pos,
        'NEGATIVE': operator.neg,
        'NOT':      operator.not_,
        'CONVERT':  repr,
        'INVERT':   operator.invert,
    }

    def unaryOperator(self, op):
        x = self.pop()
        self.push(self.UNARY_OPERATORS[op](x))

    BINARY_OPERATORS = {
        'POWER':    pow,
        'MULTIPLY': operator.mul,
        'DIVIDE':   getattr(operator, 'div', lambda x, y: None),
        'FLOOR_DIVIDE': operator.floordiv,
        'TRUE_DIVIDE':  operator.truediv,
        'MODULO':   operator.mod,
        'ADD':      operator.add,
        'SUBTRACT': operator.sub,
        'SUBSCR':   operator.getitem,
        'LSHIFT':   operator.lshift,
        'RSHIFT':   operator.rshift,
        'AND':      operator.and_,
        'XOR':      operator.xor,
        'OR':       operator.or_,
    }

    def binaryOperator(self, op):
        x, y = self.popn(2)
        self.push(self.BINARY_OPERATORS[op](x, y))

    def inplaceOperator(self, op):
        x, y = self.popn(2)
        if op == 'POWER':
            x **= y
        elif op == 'MULTIPLY':
            x *= y
        elif op in ['DIVIDE', 'FLOOR_DIVIDE']:
            x //= y
        elif op == 'TRUE_DIVIDE':
            x /= y
        elif op == 'MODULO':
            x %= y
        elif op == 'ADD':
            x += y
        elif op == 'SUBTRACT':
            x -= y
        elif op == 'LSHIFT':
            x <<= y
        elif op == 'RSHIFT':
            x >>= y
        elif op == 'AND':
            x &= y
        elif op == 'XOR':
            x ^= y
        elif op == 'OR':
            x |= y
        else:           # pragma: no cover
            raise VirtualMachineError("Unknown in-place operator: %r" % op)
        self.push(x)

    def sliceOperator(self, op):
        start = 0
        end = None          # we will take this to mean end
        op, count = op[:-2], int(op[-1])
        if count == 1:
            start = self.pop()
        elif count == 2:
            end = self.pop()
        elif count == 3:
            end = self.pop()
            start = self.pop()
        l = self.pop()
        if end is None:
            end = len(l)
        if op.startswith('STORE_'):
            l[start:end] = self.pop()
        elif op.startswith('DELETE_'):
            del l[start:end]
        else:
            self.push(l[start:end])

    COMPARE_OPERATORS = [
        operator.lt,
        operator.le,
        operator.eq,
        operator.ne,
        operator.gt,
        operator.ge,
        lambda x, y: x in y,
        lambda x, y: x not in y,
        lambda x, y: x is y,
        lambda x, y: x is not y,
        lambda x, y: issubclass(x, Exception) and issubclass(x, y),
    ]

    def byte_COMPARE_OP(self, opnum):
        x, y = self.popn(2)
        self.push(self.COMPARE_OPERATORS[opnum](x, y))

    ## Attributes and indexing

    def byte_LOAD_ATTR(self, attr):
        obj = self.pop()
        val = getattr(obj, attr)
        self.push(val)

    def byte_STORE_ATTR(self, name):
        val, obj = self.popn(2)
        setattr(obj, name, val)

    def byte_DELETE_ATTR(self, name):
        obj = self.pop()
        delattr(obj, name)

    def byte_STORE_SUBSCR(self):
        val, obj, subscr = self.popn(3)
        obj[subscr] = val

    def byte_DELETE_SUBSCR(self):
        obj, subscr = self.popn(2)
        del obj[subscr]

    ## Building

    def byte_BUILD_TUPLE(self, count):
        elts = self.popn(count)
        self.push(tuple(elts))

    def byte_BUILD_LIST(self, count):
        elts = self.popn(count)
        self.push(elts)

    def byte_BUILD_SET(self, count):
        # TODO: Not documented in Py2 docs.
        elts = self.popn(count)
        self.push(set(elts))

    def byte_BUILD_MAP(self, size):
        # size is ignored.
        self.push({})

    def byte_STORE_MAP(self):
        the_map, val, key = self.popn(3)
        the_map[key] = val
        self.push(the_map)

    def byte_UNPACK_SEQUENCE(self, count):
        seq = self.pop()
        for x in reversed(seq):
            self.push(x)

    def byte_BUILD_SLICE(self, count):
        if count == 2:
            x, y = self.popn(2)
            self.push(slice(x, y))
        elif count == 3:
            x, y, z = self.popn(3)
            self.push(slice(x, y, z))
        else:           # pragma: no cover
            raise VirtualMachineError("Strange BUILD_SLICE count: %r" % count)

    def byte_LIST_APPEND(self, count):
        val = self.pop()
        the_list = self.peek(count)
        the_list.append(val)

    def byte_SET_ADD(self, count):
        val = self.pop()
        the_set = self.peek(count)
        the_set.add(val)

    def byte_MAP_ADD(self, count):
        val, key = self.popn(2)
        the_map = self.peek(count)
        the_map[key] = val

    ## Printing

    if 0:   # Only used in the interactive interpreter, not in modules.
        def byte_PRINT_EXPR(self):
            print(self.pop())

    def byte_PRINT_ITEM(self):
        item = self.pop()
        self.print_item(item)

    def byte_PRINT_ITEM_TO(self):
        to = self.pop()
        item = self.pop()
        self.print_item(item, to)

    def byte_PRINT_NEWLINE(self):
        self.print_newline()

    def byte_PRINT_NEWLINE_TO(self):
        to = self.pop()
        self.print_newline(to)

    def print_item(self, item, to=None):
        if to is None:
            to = sys.stdout
        if to.softspace:
            print(" ", end="", file=to)
            to.softspace = 0
        print(item, end="", file=to)
        if isinstance(item, str):
            if (not item) or (not item[-1].isspace()) or (item[-1] == " "):
                to.softspace = 1
        else:
            to.softspace = 1

    def print_newline(self, to=None):
        if to is None:
            to = sys.stdout
        print("", file=to)
        to.softspace = 0

    ## Jumps

    def byte_JUMP_FORWARD(self, jump):
        self.jump(jump)

    def byte_JUMP_ABSOLUTE(self, jump):
        self.jump(jump)

    if 0:   # Not in py2.7
        def byte_JUMP_IF_TRUE(self, jump):
            val = self.top()
            if val:
                self.jump(jump)

        def byte_JUMP_IF_FALSE(self, jump):
            val = self.top()
            if not val:
                self.jump(jump)

    def byte_POP_JUMP_IF_TRUE(self, jump):
        val = self.pop()
        if val:
            self.jump(jump)

    def byte_POP_JUMP_IF_FALSE(self, jump):
        val = self.pop()
        if not val:
            self.jump(jump)

    def byte_JUMP_IF_TRUE_OR_POP(self, jump):
        val = self.top()
        if val:
            self.jump(jump)
        else:
            self.pop()

    def byte_JUMP_IF_FALSE_OR_POP(self, jump):
        val = self.top()
        if not val:
            self.jump(jump)
        else:
            self.pop()

    ## Blocks

    def byte_SETUP_LOOP(self, dest):
        self.push_block('loop', dest)

    def byte_GET_ITER(self):
        self.push(iter(self.pop()))

    def byte_FOR_ITER(self, jump):
        iterobj = self.top()
        try:
            v = next(iterobj)
            self.push(v)
        except StopIteration:
            self.pop()
            self.jump(jump)

    def byte_BREAK_LOOP(self):
        return 'break'

    def byte_CONTINUE_LOOP(self, dest):
        # This is a trick with the return value.
        # While unrolling blocks, continue and return both have to preserve
        # state as the finally blocks are executed.  For continue, it's
        # where to jump to, for return, it's the value to return.  It gets
        # pushed on the stack for both, so continue puts the jump destination
        # into return_value.
        self.return_value = dest
        return 'continue'

    def byte_SETUP_EXCEPT(self, dest):
        self.push_block('setup-except', dest)

    def byte_SETUP_FINALLY(self, dest):
        self.push_block('finally', dest)

    def byte_END_FINALLY(self):
        v = self.pop()
        if isinstance(v, str):
            why = v
            if why in ('return', 'continue'):
                self.return_value = self.pop()
            if why == 'silenced':       # PY3
                block = self.pop_block()
                assert block.type == 'except-handler'
                self.unwind_block(block)
                why = None
        elif v is None:
            why = None
        elif issubclass(v, BaseException):
            exctype = v
            val = self.pop()
            tb = self.pop()
            self.last_exception = (exctype, val, tb)
            why = 'reraise'
        else:       # pragma: no cover
            raise VirtualMachineError("Confused END_FINALLY")
        return why

    def byte_POP_BLOCK(self):
        self.pop_block()

    if PY2:
        def byte_RAISE_VARARGS(self, argc):
            # NOTE: the dis docs are completely wrong about the order of the
            # operands on the stack!
            exctype = val = tb = None
            if argc == 0:
                exctype, val, tb = self.last_exception
            elif argc == 1:
                exctype = self.pop()
            elif argc == 2:
                val = self.pop()
                exctype = self.pop()
            elif argc == 3:
                tb = self.pop()
                val = self.pop()
                exctype = self.pop()

            # There are a number of forms of "raise", normalize them somewhat.
            if isinstance(exctype, BaseException):
                val = exctype
                exctype = type(val)

            self.last_exception = (exctype, val, tb)

            if tb:
                return 'reraise'
            else:
                return 'exception'

    elif PY3:
        def byte_RAISE_VARARGS(self, argc):
            cause = exc = None
            if argc == 2:
                cause = self.pop()
                exc = self.pop()
            elif argc == 1:
                exc = self.pop()
            return self.do_raise(exc, cause)

        def do_raise(self, exc, cause):
            if exc is None:         # reraise
                exc_type, val, tb = self.last_exception
                if exc_type is None:
                    return 'exception'      # error
                else:
                    return 'reraise'

            elif type(exc) == type:
                # As in `raise ValueError`
                exc_type = exc
                val = exc()             # Make an instance.
            elif isinstance(exc, BaseException):
                # As in `raise ValueError('foo')`
                exc_type = type(exc)
                val = exc
            else:
                return 'exception'      # error

            # If you reach this point, you're guaranteed that
            # val is a valid exception instance and exc_type is its class.
            # Now do a similar thing for the cause, if present.
            if cause:
                if type(cause) == type:
                    cause = cause()
                elif not isinstance(cause, BaseException):
                    return 'exception'  # error

                val.__cause__ = cause

            self.last_exception = exc_type, val, val.__traceback__
            return 'exception'

    def byte_POP_EXCEPT(self):
        block = self.pop_block()
        if block.type != 'except-handler':
            raise Exception("popped block is not an except handler")
        self.unwind_block(block)

    def byte_SETUP_WITH(self, dest):
        ctxmgr = self.pop()
        self.push(ctxmgr.__exit__)
        ctxmgr_obj = ctxmgr.__enter__()
        if PY2:
            self.push_block('with', dest)
        elif PY3:
            self.push_block('finally', dest)
        self.push(ctxmgr_obj)

    def byte_WITH_CLEANUP(self):
        # The code here does some weird stack manipulation: the exit function
        # is buried in the stack, and where depends on what's on top of it.
        # Pull out the exit function, and leave the rest in place.
        v = w = None
        u = self.top()
        if u is None:
            exit_func = self.pop(1)
        elif isinstance(u, str):
            if u in ('return', 'continue'):
                exit_func = self.pop(2)
            else:
                exit_func = self.pop(1)
            u = None
        elif issubclass(u, BaseException):
            if PY2:
                w, v, u = self.popn(3)
                exit_func = self.pop()
                self.push(w, v, u)
            elif PY3:
                w, v, u = self.popn(3)
                tp, exc, tb = self.popn(3)
                exit_func = self.pop()
                self.push(tp, exc, tb)
                self.push(None)
                self.push(w, v, u)
                block = self.pop_block()
                assert block.type == 'except-handler'
                self.push_block(block.type, block.handler, block.level-1)
        else:       # pragma: no cover
            raise VirtualMachineError("Confused WITH_CLEANUP")
        exit_ret = exit_func(u, v, w)
        err = (u is not None) and bool(exit_ret)
        if err:
            # An error occurred, and was suppressed
            if PY2:
                self.popn(3)
                self.push(None)
            elif PY3:
                self.push('silenced')

    ## Functions

    def byte_MAKE_FUNCTION(self, argc):
        if PY3:
            name = self.pop()
        else:
            name = None
        code = self.pop()
        defaults = self.popn(argc)
        globs = self.frame.f_globals
        fn = Function(name, code, globs, defaults, None, self)
        self.push(fn)

    def byte_LOAD_CLOSURE(self, name):
        self.push(self.frame.cells[name])

    def byte_MAKE_CLOSURE(self, argc):
        if PY3:
            # TODO: the py3 docs don't mention this change.
            name = self.pop()
        else:
            name = None
        closure, code = self.popn(2)
        defaults = self.popn(argc)
        globs = self.frame.f_globals
        fn = Function(None, code, globs, defaults, closure, self)
        self.push(fn)

    def byte_CALL_FUNCTION(self, arg):
        return self.call_function(arg, [], {})

    def byte_CALL_FUNCTION_VAR(self, arg):
        args = self.pop()
        return self.call_function(arg, args, {})

    def byte_CALL_FUNCTION_KW(self, arg):
        kwargs = self.pop()
        return self.call_function(arg, [], kwargs)

    def byte_CALL_FUNCTION_VAR_KW(self, arg):
        args, kwargs = self.popn(2)
        return self.call_function(arg, args, kwargs)

    def isinstance(self, obj, cls):
        if isinstance(obj, Object):
            return issubclass(obj._class, cls)
        elif isinstance(cls, Class):
            return False
        else:
            return isinstance(obj, cls)

    def call_function(self, arg, args, kwargs):
        lenKw, lenPos = divmod(arg, 256)
        namedargs = {}
        for i in range(lenKw):
            key, val = self.popn(2)
            namedargs[key] = val
        namedargs.update(kwargs)
        posargs = self.popn(lenPos)
        posargs.extend(args)

        func = self.pop()
        frame = self.frame
        if hasattr(func, 'im_func'):
            # Methods get self as an implicit first parameter.
            if func.im_self:
                posargs.insert(0, func.im_self)
            # The first parameter must be the correct type.
            if not self.isinstance(posargs[0], func.im_class):
                raise TypeError(
                    'unbound method %s() must be called with %s instance '
                    'as first argument (got %s instance instead)' % (
                        func.im_func.func_name,
                        func.im_class.__name__,
                        type(posargs[0]).__name__,
                    )
                )
            func = func.im_func
        retval = func(*posargs, **namedargs)
        self.push(retval)

    def byte_RETURN_VALUE(self):
        self.return_value = self.pop()
        if self.frame.generator:
            self.frame.generator.finished = True
        return "return"

    def byte_YIELD_VALUE(self):
        self.return_value = self.pop()
        return "yield"

    ## Importing

    def byte_IMPORT_NAME(self, name):
        level, fromlist = self.popn(2)
        frame = self.frame
        self.push(
            __import__(name, frame.f_globals, frame.f_locals, fromlist, level)
        )

    def byte_IMPORT_STAR(self):
        # TODO: this doesn't use __all__ properly.
        mod = self.pop()
        for attr in dir(mod):
            if attr[0] != '_':
                self.frame.f_locals[attr] = getattr(mod, attr)

    def byte_IMPORT_FROM(self, name):
        mod = self.top()
        self.push(getattr(mod, name))

    ## And the rest...

    def byte_EXEC_STMT(self):
        stmt, globs, locs = self.popn(3)
        six.exec_(stmt, globs, locs)

    def byte_BUILD_CLASS(self):
        name, bases, methods = self.popn(3)
        self.push(Class(name, bases, methods))

    def byte_LOAD_BUILD_CLASS(self):
        # New in py3
        self.push(__build_class__)

    def byte_STORE_LOCALS(self):
        self.frame.f_locals = self.pop()

    if 0:   # Not in py2.7
        def byte_SET_LINENO(self, lineno):
            self.frame.f_lineno = lineno

########NEW FILE########
__FILENAME__ = __main__
"""A main program for Byterun."""

import argparse
import logging

from . import execfile

parser = argparse.ArgumentParser(
    prog="byterun",
    description="Run Python programs with a Python bytecode interpreter.",
)
parser.add_argument(
    '-m', dest='module', action='store_true',
    help="prog is a module name, not a file name.",
)
parser.add_argument(
    '-v', '--versbose', dest='verbose', action='store_true',
    help="trace the execution of the bytecode.",
)
parser.add_argument(
    'prog',
    help="The program to run.",
)
parser.add_argument(
    'args', nargs=argparse.REMAINDER,
    help="Arguments to pass to the program.",
)
args = parser.parse_args()

if args.module:
    run_fn = execfile.run_python_module
else:
    run_fn = execfile.run_python_file

level = logging.DEBUG if args.verbose else logging.WARNING
logging.basicConfig(level=level)

argv = [args.prog] + args.args
run_fn(args.prog, argv)

########NEW FILE########
__FILENAME__ = test_basic
"""Basic tests for Byterun."""

from __future__ import print_function
from . import vmtest

import six

PY3, PY2 = six.PY3, not six.PY3


class TestIt(vmtest.VmTestCase):
    def test_constant(self):
        self.assert_ok("17")

    def test_for_loop(self):
        self.assert_ok("""\
            out = ""
            for i in range(5):
                out = out + str(i)
            print(out)
            """)

    def test_inplace_operators(self):
        self.assert_ok("""\
            x, y = 2, 3
            x **= y
            assert x == 8 and y == 3
            x *= y
            assert x == 24 and y == 3
            x //= y
            assert x == 8 and y == 3
            x %= y
            assert x == 2 and y == 3
            x += y
            assert x == 5 and y == 3
            x -= y
            assert x == 2 and y == 3
            x <<= y
            assert x == 16 and y == 3
            x >>= y
            assert x == 2 and y == 3

            x = 0x8F
            x &= 0xA5
            assert x == 0x85
            x |= 0x10
            assert x == 0x95
            x ^= 0x33
            assert x == 0xA6
            """)

    if PY2:
        def test_inplace_division(self):
            self.assert_ok("""\
                x, y = 24, 3
                x /= y
                assert x == 8 and y == 3
                assert isinstance(x, int)
                x /= y
                assert x == 2 and y == 3
                assert isinstance(x, int)
                """)
    elif PY3:
        def test_inplace_division(self):
            self.assert_ok("""\
                x, y = 24, 3
                x /= y
                assert x == 8.0 and y == 3
                assert isinstance(x, float)
                x /= y
                assert x == (8.0/3.0) and y == 3
                assert isinstance(x, float)
                """)

    def test_slice(self):
        self.assert_ok("""\
            print("hello, world"[3:8])
            """)
        self.assert_ok("""\
            print("hello, world"[:8])
            """)
        self.assert_ok("""\
            print("hello, world"[3:])
            """)
        self.assert_ok("""\
            print("hello, world"[:])
            """)
        self.assert_ok("""\
            print("hello, world"[::-1])
            """)
        self.assert_ok("""\
            print("hello, world"[3:8:2])
            """)

    def test_slice_assignment(self):
        self.assert_ok("""\
            l = list(range(10))
            l[3:8] = ["x"]
            print(l)
            """)
        self.assert_ok("""\
            l = list(range(10))
            l[:8] = ["x"]
            print(l)
            """)
        self.assert_ok("""\
            l = list(range(10))
            l[3:] = ["x"]
            print(l)
            """)
        self.assert_ok("""\
            l = list(range(10))
            l[:] = ["x"]
            print(l)
            """)

    def test_slice_deletion(self):
        self.assert_ok("""\
            l = list(range(10))
            del l[3:8]
            print(l)
            """)
        self.assert_ok("""\
            l = list(range(10))
            del l[:8]
            print(l)
            """)
        self.assert_ok("""\
            l = list(range(10))
            del l[3:]
            print(l)
            """)
        self.assert_ok("""\
            l = list(range(10))
            del l[:]
            print(l)
            """)
        self.assert_ok("""\
            l = list(range(10))
            del l[::2]
            print(l)
            """)

    def test_building_stuff(self):
        self.assert_ok("""\
            print((1+1, 2+2, 3+3))
            """)
        self.assert_ok("""\
            print([1+1, 2+2, 3+3])
            """)
        self.assert_ok("""\
            print({1:1+1, 2:2+2, 3:3+3})
            """)

    def test_subscripting(self):
        self.assert_ok("""\
            l = list(range(10))
            print("%s %s %s" % (l[0], l[3], l[9]))
            """)
        self.assert_ok("""\
            l = list(range(10))
            l[5] = 17
            print(l)
            """)
        self.assert_ok("""\
            l = list(range(10))
            del l[5]
            print(l)
            """)

    def test_generator_expression(self):
        self.assert_ok("""\
            x = "-".join(str(z) for z in range(5))
            assert x == "0-1-2-3-4"
            """)
        # From test_regr.py
        # This failed a different way than the previous join when genexps were
        # broken:
        self.assert_ok("""\
            from textwrap import fill
            x = set(['test_str'])
            width = 70
            indent = 4
            blanks = ' ' * indent
            res = fill(' '.join(str(elt) for elt in sorted(x)), width,
                        initial_indent=blanks, subsequent_indent=blanks)
            print(res)
            """)
    def test_list_comprehension(self):
        self.assert_ok("""\
            x = [z*z for z in range(5)]
            assert x == [0, 1, 4, 9, 16]
            """)

    def test_dict_comprehension(self):
        self.assert_ok("""\
            x = {z:z*z for z in range(5)}
            assert x == {0:0, 1:1, 2:4, 3:9, 4:16}
            """)

    def test_set_comprehension(self):
        self.assert_ok("""\
            x = {z*z for z in range(5)}
            assert x == {0, 1, 4, 9, 16}
            """)

    def test_strange_sequence_ops(self):
        # from stdlib: test/test_augassign.py
        self.assert_ok("""\
            x = [1,2]
            x += [3,4]
            x *= 2

            assert x == [1, 2, 3, 4, 1, 2, 3, 4]

            x = [1, 2, 3]
            y = x
            x[1:2] *= 2
            y[1:2] += [1]

            assert x == [1, 2, 1, 2, 3]
            assert x is y
            """)

    def test_unary_operators(self):
        self.assert_ok("""\
            x = 8
            print(-x, ~x, not x)
            """)

    def test_attributes(self):
        self.assert_ok("""\
            l = lambda: 1   # Just to have an object...
            l.foo = 17
            print(hasattr(l, "foo"), l.foo)
            del l.foo
            print(hasattr(l, "foo"))
            """)

    def test_attribute_inplace_ops(self):
        self.assert_ok("""\
            l = lambda: 1   # Just to have an object...
            l.foo = 17
            l.foo -= 3
            print(l.foo)
            """)

    def test_deleting_names(self):
        self.assert_ok("""\
            g = 17
            assert g == 17
            del g
            g
            """, raises=NameError)

    def test_deleting_local_names(self):
        self.assert_ok("""\
            def f():
                l = 23
                assert l == 23
                del l
                l
            f()
            """, raises=NameError)

    def test_import(self):
        self.assert_ok("""\
            import math
            print(math.pi, math.e)
            from math import sqrt
            print(sqrt(2))
            from math import *
            print(sin(2))
            """)

    def test_classes(self):
        self.assert_ok("""\
            class Thing(object):
                def __init__(self, x):
                    self.x = x
                def meth(self, y):
                    return self.x * y
            thing1 = Thing(2)
            thing2 = Thing(3)
            print(thing1.x, thing2.x)
            print(thing1.meth(4), thing2.meth(5))
            """)

    def test_calling_methods_wrong(self):
        self.assert_ok("""\
            class Thing(object):
                def __init__(self, x):
                    self.x = x
                def meth(self, y):
                    return self.x * y
            thing1 = Thing(2)
            print(Thing.meth(14))
            """, raises=TypeError)

    def test_calling_subclass_methods(self):
        self.assert_ok("""\
            class Thing(object):
                def foo(self):
                    return 17

            class SubThing(Thing):
                pass

            st = SubThing()
            print(st.foo())
            """)

    def test_attribute_access(self):
        self.assert_ok("""\
            class Thing(object):
                z = 17
                def __init__(self):
                    self.x = 23
            t = Thing()
            print(Thing.z)
            print(t.z)
            print(t.x)
            """)

        self.assert_ok("""\
            class Thing(object):
                z = 17
                def __init__(self):
                    self.x = 23
            t = Thing()
            print(t.xyzzy)
            """, raises=AttributeError)

    def test_staticmethods(self):
        self.assert_ok("""\
            class Thing(object):
                @staticmethod
                def smeth(x):
                    print(x)
                @classmethod
                def cmeth(cls, x):
                    print(x)

            Thing.smeth(1492)
            Thing.cmeth(1776)
            """)

    def test_unbound_methods(self):
        self.assert_ok("""\
            class Thing(object):
                def meth(self, x):
                    print(x)
            m = Thing.meth
            m(Thing(), 1815)
            """)

    def test_callback(self):
        self.assert_ok("""\
            def lcase(s):
                return s.lower()
            l = ["xyz", "ABC"]
            l.sort(key=lcase)
            print(l)
            assert l == ["ABC", "xyz"]
            """)

    def test_unpacking(self):
        self.assert_ok("""\
            a, b, c = (1, 2, 3)
            assert a == 1
            assert b == 2
            assert c == 3
            """)

    if PY2:
        def test_exec_statement(self):
            self.assert_ok("""\
                g = {}
                exec "a = 11" in g, g
                assert g['a'] == 11
                """)
    elif PY3:
        def test_exec_statement(self):
            self.assert_ok("""\
                g = {}
                exec("a = 11", g, g)
                assert g['a'] == 11
                """)

    def test_jump_if_true_or_pop(self):
        self.assert_ok("""\
            def f(a, b):
                return a or b
            assert f(17, 0) == 17
            assert f(0, 23) == 23
            assert f(0, "") == ""
            """)

    def test_jump_if_false_or_pop(self):
        self.assert_ok("""\
            def f(a, b):
                return not(a and b)
            assert f(17, 0) is True
            assert f(0, 23) is True
            assert f(0, "") is True
            assert f(17, 23) is False
            """)

    def test_pop_jump_if_true(self):
        self.assert_ok("""\
            def f(a):
                if not a:
                    return 'foo'
                else:
                    return 'bar'
            assert f(0) == 'foo'
            assert f(1) == 'bar'
            """)

    def test_decorator(self):
        self.assert_ok("""\
            def verbose(func):
                def _wrapper(*args, **kwargs):
                    return func(*args, **kwargs)
                return _wrapper

            @verbose
            def add(x, y):
                return x+y

            add(7, 3)
            """)

    def test_multiple_classes(self):
        # Making classes used to mix together all the class-scoped values
        # across classes.  This test would fail because A.__init__ would be
        # over-written with B.__init__, and A(1, 2, 3) would complain about
        # too many arguments.
        self.assert_ok("""\
            class A(object):
                def __init__(self, a, b, c):
                    self.sum = a + b + c

            class B(object):
                def __init__(self, x):
                    self.x = x

            a = A(1, 2, 3)
            b = B(7)
            print(a.sum)
            print(b.x)
            """)


if PY2:
    class TestPrinting(vmtest.VmTestCase):
        def test_printing(self):
            self.assert_ok("print 'hello'")
            self.assert_ok("a = 3; print a+4")
            self.assert_ok("""
                print 'hi', 17, u'bye', 23,
                print "", "\t", "the end"
                """)

        def test_printing_in_a_function(self):
            self.assert_ok("""\
                def fn():
                    print "hello"
                fn()
                print "bye"
                """)

        def test_printing_to_a_file(self):
            self.assert_ok("""\
                import sys
                print >>sys.stdout, 'hello', 'there'
                """)


class TestLoops(vmtest.VmTestCase):
    def test_for(self):
        self.assert_ok("""\
            for i in range(10):
                print(i)
            print("done")
            """)

    def test_break(self):
        self.assert_ok("""\
            for i in range(10):
                print(i)
                if i == 7:
                    break
            print("done")
            """)

    def test_continue(self):
        # fun fact: this doesn't use CONTINUE_LOOP
        self.assert_ok("""\
            for i in range(10):
                if i % 3 == 0:
                    continue
                print(i)
            print("done")
            """)

    def test_continue_in_try_except(self):
        self.assert_ok("""\
            for i in range(10):
                try:
                    if i % 3 == 0:
                        continue
                    print(i)
                except ValueError:
                    pass
            print("done")
            """)

    def test_continue_in_try_finally(self):
        self.assert_ok("""\
            for i in range(10):
                try:
                    if i % 3 == 0:
                        continue
                    print(i)
                finally:
                    print(".")
            print("done")
            """)


class TestComparisons(vmtest.VmTestCase):
    def test_in(self):
        self.assert_ok("""\
            assert "x" in "xyz"
            assert "x" not in "abc"
            assert "x" in ("x", "y", "z")
            assert "x" not in ("a", "b", "c")
            """)

    def test_less(self):
        self.assert_ok("""\
            assert 1 < 3
            assert 1 <= 2 and 1 <= 1
            assert "a" < "b"
            assert "a" <= "b" and "a" <= "a"
            """)

    def test_greater(self):
        self.assert_ok("""\
            assert 3 > 1
            assert 3 >= 1 and 3 >= 3
            assert "z" > "a"
            assert "z" >= "a" and "z" >= "z"
            """)

########NEW FILE########
__FILENAME__ = test_exceptions
"""Test exceptions for Byterun."""

from __future__ import print_function
from . import vmtest

import six

PY3, PY2 = six.PY3, not six.PY3


class TestExceptions(vmtest.VmTestCase):
    def test_catching_exceptions(self):
        # Catch the exception precisely
        self.assert_ok("""\
            try:
                [][1]
                print("Shouldn't be here...")
            except IndexError:
                print("caught it!")
            """)
        # Catch the exception by a parent class
        self.assert_ok("""\
            try:
                [][1]
                print("Shouldn't be here...")
            except Exception:
                print("caught it!")
            """)
        # Catch all exceptions
        self.assert_ok("""\
            try:
                [][1]
                print("Shouldn't be here...")
            except:
                print("caught it!")
            """)

    def test_raise_exception(self):
        self.assert_ok("raise Exception('oops')", raises=Exception)

    def test_raise_exception_class(self):
        self.assert_ok("raise ValueError", raises=ValueError)

    if PY2:
        def test_raise_exception_2args(self):
            self.assert_ok("raise ValueError, 'bad'", raises=ValueError)

        def test_raise_exception_3args(self):
            self.assert_ok("""\
                from sys import exc_info
                try:
                    raise Exception
                except:
                    _, _, tb = exc_info()
                raise ValueError, "message", tb
                """, raises=ValueError)

    def test_raise_and_catch_exception(self):
        self.assert_ok("""\
            try:
                raise ValueError("oops")
            except ValueError as e:
                print("Caught: %s" % e)
            print("All done")
            """)

    if PY3:
        def test_raise_exception_from(self):
            self.assert_ok(
                "raise ValueError from NameError",
                raises=ValueError
            )

    def test_raise_and_catch_exception_in_function(self):
        self.assert_ok("""\
            def fn():
                raise ValueError("oops")

            try:
                fn()
            except ValueError as e:
                print("Caught: %s" % e)
            print("done")
            """)

    def test_global_name_error(self):
        self.assert_ok("fooey", raises=NameError)
        self.assert_ok("""\
            try:
                fooey
                print("Yes fooey?")
            except NameError:
                print("No fooey")
            """)

    def test_local_name_error(self):
        self.assert_ok("""\
            def fn():
                fooey
            fn()
            """, raises=NameError)

    def test_catch_local_name_error(self):
        self.assert_ok("""\
            def fn():
                try:
                    fooey
                    print("Yes fooey?")
                except NameError:
                    print("No fooey")
            fn()
            """)

    def test_reraise(self):
        self.assert_ok("""\
            def fn():
                try:
                    fooey
                    print("Yes fooey?")
                except NameError:
                    print("No fooey")
                    raise
            fn()
            """, raises=NameError)

    def test_reraise_explicit_exception(self):
        self.assert_ok("""\
            def fn():
                try:
                    raise ValueError("ouch")
                except ValueError as e:
                    print("Caught %s" % e)
                    raise
            fn()
            """, raises=ValueError)

    def test_finally_while_throwing(self):
        self.assert_ok("""\
            def fn():
                try:
                    print("About to..")
                    raise ValueError("ouch")
                finally:
                    print("Finally")
            fn()
            print("Done")
            """, raises=ValueError)

    def test_coverage_issue_92(self):
        self.assert_ok("""\
            l = []
            for i in range(3):
                try:
                    l.append(i)
                finally:
                    l.append('f')
                l.append('e')
            l.append('r')
            print(l)
            assert l == [0, 'f', 'e', 1, 'f', 'e', 2, 'f', 'e', 'r']
            """)

########NEW FILE########
__FILENAME__ = test_functions
"""Test functions etc, for Byterun."""

from __future__ import print_function
from . import vmtest


class TestFunctions(vmtest.VmTestCase):
    def test_functions(self):
        self.assert_ok("""\
            def fn(a, b=17, c="Hello", d=[]):
                d.append(99)
                print(a, b, c, d)
            fn(1)
            fn(2, 3)
            fn(3, c="Bye")
            fn(4, d=["What?"])
            fn(5, "b", "c")
            """)

    def test_recursion(self):
        self.assert_ok("""\
            def fact(n):
                if n <= 1:
                    return 1
                else:
                    return n * fact(n-1)
            f6 = fact(6)
            print(f6)
            assert f6 == 720
            """)

    def test_calling_functions_with_args_kwargs(self):
        self.assert_ok("""\
            def fn(a, b=17, c="Hello", d=[]):
                d.append(99)
                print(a, b, c, d)
            fn(6, *[77, 88])
            fn(**{'c': 23, 'a': 7})
            fn(6, *[77], **{'c': 23, 'd': [123]})
            """)

    def test_defining_functions_with_args_kwargs(self):
        self.assert_ok("""\
            def fn(*args):
                print("args is %r" % (args,))
            fn(1, 2)
            """)
        self.assert_ok("""\
            def fn(**kwargs):
                print("kwargs is %r" % (kwargs,))
            fn(red=True, blue=False)
            """)
        self.assert_ok("""\
            def fn(*args, **kwargs):
                print("args is %r" % (args,))
                print("kwargs is %r" % (kwargs,))
            fn(1, 2, red=True, blue=False)
            """)
        self.assert_ok("""\
            def fn(x, y, *args, **kwargs):
                print("x is %r, y is %r" % (x, y))
                print("args is %r" % (args,))
                print("kwargs is %r" % (kwargs,))
            fn('a', 'b', 1, 2, red=True, blue=False)
            """)

    def test_defining_functions_with_empty_args_kwargs(self):
        self.assert_ok("""\
            def fn(*args):
                print("args is %r" % (args,))
            fn()
            """)
        self.assert_ok("""\
            def fn(**kwargs):
                print("kwargs is %r" % (kwargs,))
            fn()
            """)
        self.assert_ok("""\
            def fn(*args, **kwargs):
                print("args is %r, kwargs is %r" % (args, kwargs))
            fn()
            """)

    def test_partial(self):
        self.assert_ok("""\
            from _functools import partial

            def f(a,b):
                return a-b

            f7 = partial(f, 7)
            four = f7(3)
            assert four == 4
            """)

    def test_partial_with_kwargs(self):
        self.assert_ok("""\
            from _functools import partial

            def f(a,b,c=0,d=0):
                return (a,b,c,d)

            f7 = partial(f, b=7, c=1)
            them = f7(10)
            assert them == (10,7,1,0)
            """)

    def test_wraps(self):
        self.assert_ok("""\
            from functools import wraps
            def my_decorator(f):
                dec = wraps(f)
                def wrapper(*args, **kwds):
                    print('Calling decorated function')
                    return f(*args, **kwds)
                wrapper = dec(wrapper)
                return wrapper

            @my_decorator
            def example():
                '''Docstring'''
                return 17

            assert example() == 17
            """)


class TestClosures(vmtest.VmTestCase):
    def test_closures(self):
        self.assert_ok("""\
            def make_adder(x):
                def add(y):
                    return x+y
                return add
            a = make_adder(10)
            print(a(7))
            assert a(7) == 17
            """)

    def test_closures_store_deref(self):
        self.assert_ok("""\
            def make_adder(x):
                z = x+1
                def add(y):
                    return x+y+z
                return add
            a = make_adder(10)
            print(a(7))
            assert a(7) == 28
            """)

    def test_closures_in_loop(self):
        self.assert_ok("""\
            def make_fns(x):
                fns = []
                for i in range(x):
                    fns.append(lambda i=i: i)
                return fns
            fns = make_fns(3)
            for f in fns:
                print(f())
            assert (fns[0](), fns[1](), fns[2]()) == (0, 1, 2)
            """)

    def test_closures_with_defaults(self):
        self.assert_ok("""\
            def make_adder(x, y=13, z=43):
                def add(q, r=11):
                    return x+y+z+q+r
                return add
            a = make_adder(10, 17)
            print(a(7))
            assert a(7) == 88
            """)

    def test_deep_closures(self):
        self.assert_ok("""\
            def f1(a):
                b = 2*a
                def f2(c):
                    d = 2*c
                    def f3(e):
                        f = 2*e
                        def f4(g):
                            h = 2*g
                            return a+b+c+d+e+f+g+h
                        return f4
                    return f3
                return f2
            answer = f1(3)(4)(5)(6)
            print(answer)
            assert answer == 54
            """)


class TestGenerators(vmtest.VmTestCase):
    def test_first(self):
        self.assert_ok("""\
            def two():
                yield 1
                yield 2
            for i in two():
                print(i)
            """)

    def test_partial_generator(self):
        self.assert_ok("""\
            from _functools import partial

            def f(a,b):
                num = a+b
                while num:
                    yield num
                    num -= 1

            f2 = partial(f, 2)
            three = f2(1)
            assert list(three) == [3,2,1]
            """)

    def test_yield_multiple_values(self):
        self.assert_ok("""\
            def triples():
                yield 1, 2, 3
                yield 4, 5, 6

            for a, b, c in triples():
                print(a, b, c)
            """)

    def test_generator_from_generator2(self):
        self.assert_ok("""\
            g = (x*x for x in range(3))
            print(list(g))

            g = (x*x for x in range(5))
            g = (y+1 for y in g)
            print(list(g))
            """)

    def test_generator_from_generator(self):
        self.assert_ok("""\
            class Thing(object):
                RESOURCES = ('abc', 'def')
                def get_abc(self):
                    return "ABC"
                def get_def(self):
                    return "DEF"
                def resource_info(self):
                    for name in self.RESOURCES:
                        get_name = 'get_' + name
                        yield name, getattr(self, get_name)

                def boom(self):
                    #d = list((name, get()) for name, get in self.resource_info())
                    d = [(name, get()) for name, get in self.resource_info()]
                    return d

            print(Thing().boom())
            """)

########NEW FILE########
__FILENAME__ = test_with
"""Test the with statement for Byterun."""

from __future__ import print_function
from . import vmtest


class TestWithStatement(vmtest.VmTestCase):

    def test_simple_context_manager(self):
        self.assert_ok("""\
            class NullContext(object):
                def __enter__(self):
                    l.append('i')
                    # __enter__ usually returns self, but doesn't have to.
                    return 17

                def __exit__(self, exc_type, exc_val, exc_tb):
                    l.append('o')
                    return False

            l = []
            for i in range(3):
                with NullContext() as val:
                    assert val == 17
                    l.append('w')
                l.append('e')
            l.append('r')
            s = ''.join(l)
            print("Look: %r" % s)
            assert s == "iwoeiwoeiwoer"
            """)

    def test_raise_in_context_manager(self):
        self.assert_ok("""\
            class NullContext(object):
                def __enter__(self):
                    l.append('i')
                    return self

                def __exit__(self, exc_type, exc_val, exc_tb):
                    assert exc_type is ValueError, \\
                        "Expected ValueError: %r" % exc_type
                    l.append('o')
                    return False

            l = []
            try:
                with NullContext():
                    l.append('w')
                    raise ValueError("Boo!")
                l.append('e')
            except ValueError:
                l.append('x')
            l.append('r')
            s = ''.join(l)
            print("Look: %r" % s)
            assert s == "iwoxr"
            """)

    def test_suppressed_raise_in_context_manager(self):
        self.assert_ok("""\
            class SuppressingContext(object):
                def __enter__(self):
                    l.append('i')
                    return self

                def __exit__(self, exc_type, exc_val, exc_tb):
                    assert exc_type is ValueError, \\
                        "Expected ValueError: %r" % exc_type
                    l.append('o')
                    return True

            l = []
            try:
                with SuppressingContext():
                    l.append('w')
                    raise ValueError("Boo!")
                l.append('e')
            except ValueError:
                l.append('x')
            l.append('r')
            s = ''.join(l)
            print("Look: %r" % s)
            assert s == "iwoer"
            """)

    def test_return_in_with(self):
        self.assert_ok("""\
            class NullContext(object):
                def __enter__(self):
                    l.append('i')
                    return self

                def __exit__(self, exc_type, exc_val, exc_tb):
                    l.append('o')
                    return False

            l = []
            def use_with(val):
                with NullContext():
                    l.append('w')
                    return val
                l.append('e')

            assert use_with(23) == 23
            l.append('r')
            s = ''.join(l)
            print("Look: %r" % s)
            assert s == "iwor"
            """)

    def test_continue_in_with(self):
        self.assert_ok("""\
            class NullContext(object):
                def __enter__(self):
                    l.append('i')
                    return self

                def __exit__(self, exc_type, exc_val, exc_tb):
                    l.append('o')
                    return False

            l = []
            for i in range(3):
                with NullContext():
                    l.append('w')
                    if i % 2:
                       continue
                    l.append('z')
                l.append('e')

            l.append('r')
            s = ''.join(l)
            print("Look: %r" % s)
            assert s == "iwzoeiwoiwzoer"
            """)

    def test_break_in_with(self):
        self.assert_ok("""\
            class NullContext(object):
                def __enter__(self):
                    l.append('i')
                    return self

                def __exit__(self, exc_type, exc_val, exc_tb):
                    l.append('o')
                    return False

            l = []
            for i in range(3):
                with NullContext():
                    l.append('w')
                    if i % 2:
                       break
                    l.append('z')
                l.append('e')

            l.append('r')
            s = ''.join(l)
            print("Look: %r" % s)
            assert s == "iwzoeiwor"
            """)

    def test_raise_in_with(self):
        self.assert_ok("""\
            class NullContext(object):
                def __enter__(self):
                    l.append('i')
                    return self

                def __exit__(self, exc_type, exc_val, exc_tb):
                    l.append('o')
                    return False

            l = []
            try:
                with NullContext():
                    l.append('w')
                    raise ValueError("oops")
                    l.append('z')
                l.append('e')
            except ValueError as e:
                assert str(e) == "oops"
                l.append('x')
            l.append('r')
            s = ''.join(l)
            print("Look: %r" % s)
            assert s == "iwoxr", "What!?"
            """)

    def test_at_context_manager_simplified(self):
        self.assert_ok("""\
            class GeneratorContextManager(object):
                def __init__(self, gen):
                    self.gen = gen

                def __enter__(self):
                    try:
                        return next(self.gen)
                    except StopIteration:
                        raise RuntimeError("generator didn't yield")

                def __exit__(self, type, value, traceback):
                    if type is None:
                        try:
                            next(self.gen)
                        except StopIteration:
                            return
                        else:
                            raise RuntimeError("generator didn't stop")
                    else:
                        if value is None:
                            value = type()
                        try:
                            self.gen.throw(type, value, traceback)
                            raise RuntimeError(
                                "generator didn't stop after throw()"
                            )
                        except StopIteration as exc:
                            return exc is not value
                        except:
                            if sys.exc_info()[1] is not value:
                                raise

            def contextmanager(func):
                def helper(*args, **kwds):
                    return GeneratorContextManager(func(*args, **kwds))
                return helper

            @contextmanager
            def my_context_manager(val):
                yield val

            with my_context_manager(17) as x:
                assert x == 17
            """)

    def test_at_context_manager_complete(self):
        # The complete code for an @contextmanager example, lifted from
        # the stdlib.
        self.assert_ok("""\
            from _functools import partial

            WRAPPER_ASSIGNMENTS = ('__module__', '__name__', '__doc__')
            WRAPPER_UPDATES = ('__dict__',)

            def update_wrapper(wrapper,
                            wrapped,
                            assigned = WRAPPER_ASSIGNMENTS,
                            updated = WRAPPER_UPDATES):
                for attr in assigned:
                    setattr(wrapper, attr, getattr(wrapped, attr))
                for attr in updated:
                    getattr(wrapper, attr).update(getattr(wrapped, attr, {}))
                # Return the wrapper so this can be used as a decorator
                # via partial().
                return wrapper

            def wraps(wrapped,
                    assigned = WRAPPER_ASSIGNMENTS,
                    updated = WRAPPER_UPDATES):
                return partial(update_wrapper, wrapped=wrapped,
                            assigned=assigned, updated=updated)

            class GeneratorContextManager(object):
                def __init__(self, gen):
                    self.gen = gen

                def __enter__(self):
                    try:
                        return next(self.gen)
                    except StopIteration:
                        raise RuntimeError("generator didn't yield")

                def __exit__(self, type, value, traceback):
                    if type is None:
                        try:
                            next(self.gen)
                        except StopIteration:
                            return
                        else:
                            raise RuntimeError("generator didn't stop")
                    else:
                        if value is None:
                            value = type()
                        try:
                            self.gen.throw(type, value, traceback)
                            raise RuntimeError(
                                "generator didn't stop after throw()"
                            )
                        except StopIteration as exc:
                            return exc is not value
                        except:
                            if sys.exc_info()[1] is not value:
                                raise

            def contextmanager(func):
                @wraps(func)
                def helper(*args, **kwds):
                    return GeneratorContextManager(func(*args, **kwds))
                return helper

            @contextmanager
            def my_context_manager(val):
                yield val

            with my_context_manager(17) as x:
                assert x == 17
            """)

########NEW FILE########
__FILENAME__ = vmtest
"""Testing tools for byterun."""

from __future__ import print_function

import dis
import sys
import textwrap
import types
import unittest

import six

from byterun.pyvm2 import VirtualMachine, VirtualMachineError

# Make this false if you need to run the debugger inside a test.
CAPTURE_STDOUT = ('-s' not in sys.argv)
# Make this false to see the traceback from a failure inside pyvm2.
CAPTURE_EXCEPTION = 1


def dis_code(code):
    """Disassemble `code` and all the code it refers to."""
    for const in code.co_consts:
        if isinstance(const, types.CodeType):
            dis_code(const)

    print("")
    print(code)
    dis.dis(code)


class VmTestCase(unittest.TestCase):

    def assert_ok(self, code, raises=None):
        """Run `code` in our VM and in real Python: they behave the same."""

        code = textwrap.dedent(code)
        code = compile(code, "<%s>" % self.id(), "exec", 0, 1)

        # Print the disassembly so we'll see it if the test fails.
        dis_code(code)

        real_stdout = sys.stdout

        # Run the code through our VM.

        vm_stdout = six.StringIO()
        if CAPTURE_STDOUT:              # pragma: no branch
            sys.stdout = vm_stdout
        vm = VirtualMachine()

        vm_value = vm_exc = None
        try:
            vm_value = vm.run_code(code)
        except VirtualMachineError:         # pragma: no cover
            # If the VM code raises an error, show it.
            raise
        except AssertionError:              # pragma: no cover
            # If test code fails an assert, show it.
            raise
        except Exception as e:
            # Otherwise, keep the exception for comparison later.
            if not CAPTURE_EXCEPTION:       # pragma: no cover
                raise
            vm_exc = e
        finally:
            real_stdout.write("-- stdout ----------\n")
            real_stdout.write(vm_stdout.getvalue())

        # Run the code through the real Python interpreter, for comparison.

        py_stdout = six.StringIO()
        sys.stdout = py_stdout

        py_value = py_exc = None
        globs = {}
        try:
            py_value = eval(code, globs, globs)
        except AssertionError:              # pragma: no cover
            raise
        except Exception as e:
            py_exc = e

        sys.stdout = real_stdout

        self.assert_same_exception(vm_exc, py_exc)
        self.assertEqual(vm_stdout.getvalue(), py_stdout.getvalue())
        self.assertEqual(vm_value, py_value)
        if raises:
            self.assertIsInstance(vm_exc, raises)
        else:
            self.assertIsNone(vm_exc)

    def assert_same_exception(self, e1, e2):
        """Exceptions don't implement __eq__, check it ourselves."""
        self.assertEqual(str(e1), str(e2))
        self.assertIs(type(e1), type(e2))

########NEW FILE########
