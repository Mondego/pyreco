__FILENAME__ = configure
#! /usr/bin/env python

from aksetup_helper import configure_frontend
configure_frontend()

########NEW FILE########
__FILENAME__ = translate
from __future__ import division, with_statement

__copyright__ = "Copyright (C) 2009 Andreas Kloeckner"

__license__ = """
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

import cgen
import numpy as np
import re
from pymbolic.parser import Parser as ExpressionParserBase
from pymbolic.mapper import CombineMapper
import pymbolic.primitives
from pymbolic.mapper.c_code import CCodeMapper as CCodeMapperBase

from warnings import warn

import pytools.lex


class TranslatorWarning(UserWarning):
    pass


class TranslationError(RuntimeError):
    pass


# {{{ AST components

def dtype_to_ctype(dtype):
    if dtype is None:
        raise ValueError("dtype may not be None")

    dtype = np.dtype(dtype)
    if dtype == np.int64:
        return "long"
    elif dtype == np.uint64:
        return "unsigned long"
    elif dtype == np.int32:
        return "int"
    elif dtype == np.uint32:
        return "unsigned int"
    elif dtype == np.int16:
        return "short int"
    elif dtype == np.uint16:
        return "short unsigned int"
    elif dtype == np.int8:
        return "signed char"
    elif dtype == np.uint8:
        return "unsigned char"
    elif dtype == np.float32:
        return "float"
    elif dtype == np.float64:
        return "double"
    elif dtype == np.complex64:
        return "cfloat_t"
    elif dtype == np.complex128:
        return "cdouble_t"
    else:
        raise ValueError("unable to map dtype '%s'" % dtype)


class POD(cgen.POD):
    def get_decl_pair(self):
        return [dtype_to_ctype(self.dtype)], self.name

# }}}


# {{{ expression parser

_less_than = intern("less_than")
_greater_than = intern("greater_than")
_less_equal = intern("less_equal")
_greater_equal = intern("greater_equal")
_equal = intern("equal")
_not_equal = intern("not_equal")

_not = intern("not")
_and = intern("and")
_or = intern("or")


class TypedLiteral(pymbolic.primitives.Leaf):
    def __init__(self, value, dtype):
        self.value = value
        self.dtype = np.dtype(dtype)

    def __getinitargs__(self):
        return self.value, self.dtype

    mapper_method = intern("map_literal")


class FortranExpressionParser(ExpressionParserBase):
    # FIXME double/single prec literals

    lex_table = [
        (_less_than, pytools.lex.RE(r"\.lt\.", re.I)),
        (_greater_than, pytools.lex.RE(r"\.gt\.", re.I)),
        (_less_equal, pytools.lex.RE(r"\.le\.", re.I)),
        (_greater_equal, pytools.lex.RE(r"\.ge\.", re.I)),
        (_equal, pytools.lex.RE(r"\.eq\.", re.I)),
        (_not_equal, pytools.lex.RE(r"\.ne\.", re.I)),

        (_not, pytools.lex.RE(r"\.not\.", re.I)),
        (_and, pytools.lex.RE(r"\.and\.", re.I)),
        (_or, pytools.lex.RE(r"\.or\.", re.I)),
        ] + ExpressionParserBase.lex_table

    def __init__(self, tree_walker):
        self.tree_walker = tree_walker

    _PREC_FUNC_ARGS = 1

    def parse_terminal(self, pstate):
        scope = self.tree_walker.scope_stack[-1]

        from pymbolic.primitives import Subscript, Call, Variable
        from pymbolic.parser import (
            _identifier, _openpar, _closepar, _float)

        next_tag = pstate.next_tag()
        if next_tag is _float:
            value = pstate.next_str_and_advance().lower()
            if "d" in value:
                dtype = np.float64
            else:
                dtype = np.float32

            value = value.replace("d", "e")
            if value.startswith("."):
                prev_value = value
                value = "0"+value
                print value, prev_value
            elif value.startswith("-."):
                prev_value = value
                value = "-0"+value[1:]
                print value, prev_value
            return TypedLiteral(value, dtype)

        elif next_tag is _identifier:
            name = pstate.next_str_and_advance()

            if pstate.is_at_end() or pstate.next_tag() is not _openpar:
                # not a subscript
                scope.use_name(name)

                return Variable(name)

            left_exp = Variable(name)

            pstate.advance()
            pstate.expect_not_end()

            if scope.is_known(name):
                cls = Subscript
            else:
                cls = Call

            if pstate.next_tag is _closepar:
                pstate.advance()
                left_exp = cls(left_exp, ())
            else:
                args = self.parse_expression(pstate, self._PREC_FUNC_ARGS)
                if not isinstance(args, tuple):
                    args = (args,)
                left_exp = cls(left_exp, args)
                pstate.expect(_closepar)
                pstate.advance()

            return left_exp
        else:
            return ExpressionParserBase.parse_terminal(
                    self, pstate)

    COMP_MAP = {
            _less_than: "<",
            _less_equal: "<=",
            _greater_than: ">",
            _greater_equal: ">=",
            _equal: "==",
            _not_equal: "!=",
            }

    def parse_prefix(self, pstate, min_precedence=0):
        from pymbolic.parser import _PREC_UNARY
        import pymbolic.primitives as primitives

        pstate.expect_not_end()

        if pstate.is_next(_not):
            pstate.advance()
            return primitives.LogicalNot(
                    self.parse_expression(pstate, _PREC_UNARY))
        else:
            return ExpressionParserBase.parse_prefix(self, pstate)

    def parse_postfix(self, pstate, min_precedence, left_exp):
        from pymbolic.parser import (
                _PREC_CALL, _PREC_COMPARISON, _openpar,
                _PREC_LOGICAL_OR, _PREC_LOGICAL_AND)
        from pymbolic.primitives import (
                ComparisonOperator, LogicalAnd, LogicalOr)

        next_tag = pstate.next_tag()
        if next_tag is _openpar and _PREC_CALL > min_precedence:
            raise TranslationError("parenthesis operator only works on names")
        elif next_tag in self.COMP_MAP and _PREC_COMPARISON > min_precedence:
            pstate.advance()
            left_exp = ComparisonOperator(
                    left_exp,
                    self.COMP_MAP[next_tag],
                    self.parse_expression(pstate, _PREC_COMPARISON))
            did_something = True
        elif next_tag is _and and _PREC_LOGICAL_AND > min_precedence:
            pstate.advance()
            left_exp = LogicalAnd((left_exp,
                    self.parse_expression(pstate, _PREC_LOGICAL_AND)))
            did_something = True
        elif next_tag is _or and _PREC_LOGICAL_OR > min_precedence:
            pstate.advance()
            left_exp = LogicalOr((left_exp,
                    self.parse_expression(pstate, _PREC_LOGICAL_OR)))
            did_something = True
        else:
            left_exp, did_something = ExpressionParserBase.parse_postfix(
                    self, pstate, min_precedence, left_exp)

            if isinstance(left_exp, tuple) and min_precedence < self._PREC_FUNC_ARGS:
                # this must be a complex literal
                assert len(left_exp) == 2
                r, i = left_exp

                dtype = (r.dtype.type(0) + i.dtype.type(0))
                if dtype == np.float32:
                    dtype = np.complex64
                else:
                    dtype = np.complex128

                left_exp = TypedLiteral(left_exp, dtype)

        return left_exp, did_something

# }}}


# {{{ expression generator

class TypeInferenceMapper(CombineMapper):
    def __init__(self, scope):
        self.scope = scope

    def combine(self, dtypes):
        return sum(dtype.type(1) for dtype in dtypes).dtype

    def map_literal(self, expr):
        return expr.dtype

    def map_constant(self, expr):
        return np.asarray(expr).dtype

    def map_variable(self, expr):
        return self.scope.get_type(expr.name)

    def map_call(self, expr):
        name = expr.function.name
        if name == "fromreal":
            arg, = expr.parameters
            base_dtype = self.rec(arg)
            tgt_real_dtype = (np.float32(0)+base_dtype.type(0)).dtype
            assert tgt_real_dtype.kind == "f"
            if tgt_real_dtype == np.float32:
                return np.dtype(np.complex64)
            elif tgt_real_dtype == np.float64:
                return np.dtype(np.complex128)
            else:
                raise RuntimeError("unexpected complex type")

        else:
            return CombineMapper.map_call(self, expr)


class ComplexCCodeMapper(CCodeMapperBase):
    def __init__(self, infer_type):
        CCodeMapperBase.__init__(self)
        self.infer_type = infer_type

    def complex_type_name(self, dtype):
        if dtype == np.complex64:
            return "cfloat"
        if dtype == np.complex128:
            return "cdouble"
        else:
            raise RuntimeError

    def map_sum(self, expr, enclosing_prec):
        tgt_dtype = self.infer_type(expr)
        is_complex = tgt_dtype.kind == 'c'

        if not is_complex:
            return CCodeMapperBase.map_sum(self, expr, enclosing_prec)
        else:
            tgt_name = self.complex_type_name(tgt_dtype)

            reals = [child for child in expr.children
                    if 'c' != self.infer_type(child).kind]
            complexes = [child for child in expr.children
                    if 'c' == self.infer_type(child).kind]

            from pymbolic.mapper.stringifier import PREC_SUM
            real_sum = self.join_rec(" + ", reals, PREC_SUM)
            complex_sum = self.join_rec(" + ", complexes, PREC_SUM)

            if real_sum:
                result = "%s_fromreal(%s) + %s" % (tgt_name, real_sum, complex_sum)
            else:
                result = complex_sum

            return self.parenthesize_if_needed(result, enclosing_prec, PREC_SUM)

    def map_product(self, expr, enclosing_prec):
        tgt_dtype = self.infer_type(expr)
        is_complex = 'c' == tgt_dtype.kind

        if not is_complex:
            return CCodeMapperBase.map_product(self, expr, enclosing_prec)
        else:
            tgt_name = self.complex_type_name(tgt_dtype)

            reals = [child for child in expr.children
                    if 'c' != self.infer_type(child).kind]
            complexes = [child for child in expr.children
                    if 'c' == self.infer_type(child).kind]

            from pymbolic.mapper.stringifier import PREC_PRODUCT, PREC_NONE
            real_prd = self.join_rec("*", reals, PREC_PRODUCT)

            if len(complexes) == 1:
                myprec = PREC_PRODUCT
            else:
                myprec = PREC_NONE

            complex_prd = self.rec(complexes[0], myprec)
            for child in complexes[1:]:
                complex_prd = "%s_mul(%s, %s)" % (
                        tgt_name, complex_prd,
                        self.rec(child, PREC_NONE))

            if real_prd:
                # elementwise semantics are correct
                result = "%s * %s" % (real_prd, complex_prd)
            else:
                result = complex_prd

            return self.parenthesize_if_needed(result, enclosing_prec, PREC_PRODUCT)

    def map_quotient(self, expr, enclosing_prec):
        from pymbolic.mapper.stringifier import PREC_NONE
        n_complex = 'c' == self.infer_type(expr.numerator).kind
        d_complex = 'c' == self.infer_type(expr.denominator).kind

        tgt_dtype = self.infer_type(expr)

        if not (n_complex or d_complex):
            return CCodeMapperBase.map_quotient(self, expr, enclosing_prec)
        elif n_complex and not d_complex:
            # elementwise semnatics are correct
            return CCodeMapperBase.map_quotient(self, expr, enclosing_prec)
        elif not n_complex and d_complex:
            return "%s_rdivide(%s, %s)" % (
                    self.complex_type_name(tgt_dtype),
                    self.rec(expr.numerator, PREC_NONE),
                    self.rec(expr.denominator, PREC_NONE))
        else:
            return "%s_divide(%s, %s)" % (
                    self.complex_type_name(tgt_dtype),
                    self.rec(expr.numerator, PREC_NONE),
                    self.rec(expr.denominator, PREC_NONE))

    def map_remainder(self, expr, enclosing_prec):
        tgt_dtype = self.infer_type(expr)
        if 'c' == tgt_dtype.kind:
            raise RuntimeError("complex remainder not defined")

        return CCodeMapperBase.map_remainder(self, expr, enclosing_prec)

    def map_power(self, expr, enclosing_prec):
        from pymbolic.mapper.stringifier import PREC_NONE

        tgt_dtype = self.infer_type(expr)
        if 'c' == tgt_dtype.kind:
            if expr.exponent in [2, 3, 4]:
                value = expr.base
                for i in range(expr.exponent-1):
                    value = value * expr.base
                return self.rec(value, enclosing_prec)
            else:
                b_complex = 'c' == self.infer_type(expr.base).kind
                e_complex = 'c' == self.infer_type(expr.exponent).kind

                if b_complex and not e_complex:
                    return "%s_powr(%s, %s)" % (
                            self.complex_type_name(tgt_dtype),
                            self.rec(expr.base, PREC_NONE),
                            self.rec(expr.exponent, PREC_NONE))
                else:
                    return "%s_pow(%s, %s)" % (
                            self.complex_type_name(tgt_dtype),
                            self.rec(expr.base, PREC_NONE),
                            self.rec(expr.exponent, PREC_NONE))

        return CCodeMapperBase.map_power(self, expr, enclosing_prec)


class CCodeMapper(ComplexCCodeMapper):
    # Whatever is needed to mop up after Fortran goes here.
    # Stuff that deals with generating real-valued code
    # from complex code goes above.

    def __init__(self, translator, scope):
        ComplexCCodeMapper.__init__(self, scope.get_type_inference_mapper())
        self.translator = translator
        self.scope = scope

    def map_subscript(self, expr, enclosing_prec):
        idx_dtype = self.infer_type(expr.index)
        if not 'i' == idx_dtype.kind or 'u' == idx_dtype.kind:
            ind_prefix = "(int) "
        else:
            ind_prefix = ""

        idx = expr.index
        if isinstance(idx, tuple) and len(idx) == 1:
            idx, = idx

        from pymbolic.mapper.stringifier import PREC_NONE, PREC_CALL
        return self.parenthesize_if_needed(
                self.format("%s[%s%s]",
                    self.scope.translate_var_name(expr.aggregate.name),
                    ind_prefix,
                    self.rec(idx, PREC_NONE)),
                enclosing_prec, PREC_CALL)

    def map_call(self, expr, enclosing_prec):
        from pymbolic.mapper.stringifier import PREC_NONE

        tgt_dtype = self.infer_type(expr)

        name = expr.function.name
        if 'f' == tgt_dtype.kind and name == "abs":
            name = "fabs"

        if 'c' == tgt_dtype.kind:
            if name in ["conjg", "dconjg"]:
                name = "conj"

            if name[:2] == "cd" and name[2:] in ["log", "exp", "sqrt"]:
                name = name[2:]

            if name == "aimag":
                name = "imag"

            if name == "dble":
                name = "real"

            name = "%s_%s" % (
                    self.complex_type_name(tgt_dtype),
                    name)

        return self.format("%s(%s)",
                name,
                self.join_rec(", ", expr.parameters, PREC_NONE))

    def map_variable(self, expr, enclosing_prec):
        # guaranteed to not be a subscript or a call

        name = expr.name
        shape = self.scope.get_shape(name)
        name = self.scope.translate_var_name(name)
        if expr.name in self.scope.arg_names:
            arg_idx = self.scope.arg_names.index(name)
            if self.translator.arg_needs_pointer(
                    self.scope.subprogram_name, arg_idx):
                return "*"+name
            else:
                return name
        elif shape not in [(), None]:
            return "*"+name
        else:
            return name

    def map_literal(self, expr, enclosing_prec):
        from pymbolic.mapper.stringifier import PREC_NONE
        if expr.dtype.kind == "c":
            r, i = expr.value
            return "{ %s, %s }" % (self.rec(r, PREC_NONE), self.rec(i, PREC_NONE))
        else:
            return expr.value

    def map_wildcard(self, expr, enclosing_prec):
        return ":"


# }}}

class Scope(object):
    def __init__(self, subprogram_name, arg_names=set()):
        self.subprogram_name = subprogram_name

        # map name to data
        self.data_statements = {}

        # map first letter to type
        self.implicit_types = {}

        # map name to dim tuple
        self.dim_map = {}

        # map name to dim tuple
        self.type_map = {}

        # map name to data
        self.data = {}

        self.arg_names = arg_names

        self.used_names = set()

        self.type_inf_mapper = None

    def known_names(self):
        return (self.used_names
                | set(self.dim_map.iterkeys())
                | set(self.type_map.iterkeys()))

    def is_known(self, name):
        return (name in self.used_names
                or name in self.dim_map
                or name in self.type_map)

    def use_name(self, name):
        self.used_names.add(name)

    def get_type(self, name):
        try:
            return self.type_map[name]
        except KeyError:

            if self.implicit_types is None:
                raise TranslationError(
                        "no type for '%s' found in implict none routine"
                        % name)

            return self.implicit_types.get(name[0], np.dtype(np.int32))

    def get_shape(self, name):
        return self.dim_map.get(name, ())

    def get_type_inference_mapper(self):
        if self.type_inf_mapper is None:
            self.type_inf_mapper = TypeInferenceMapper(self)

        return self.type_inf_mapper

    def translate_var_name(self, name):
        shape = self.dim_map.get(name)
        if name in self.data and shape is not None:
            return "%s_%s" % (self.subprogram_name, name)
        else:
            return name


class FTreeWalkerBase(object):
    def __init__(self):
        self.scope_stack = []

        self.expr_parser = FortranExpressionParser(self)

    def rec(self, expr, *args, **kwargs):
        mro = list(type(expr).__mro__)
        dispatch_class = kwargs.pop("dispatch_class", type(self))

        while mro:
            method_name = "map_"+mro.pop(0).__name__

            try:
                method = getattr(dispatch_class, method_name)
            except AttributeError:
                pass
            else:
                return method(self, expr, *args, **kwargs)

        raise NotImplementedError(
                "%s does not know how to map type '%s'"
                % (type(self).__name__,
                    type(expr)))

    ENTITY_RE = re.compile(
            r"^(?P<name>[_0-9a-zA-Z]+)"
            "(\((?P<shape>[-+*0-9:a-zA-Z,]+)\))?$")

    def parse_dimension_specs(self, dim_decls):
        def parse_bounds(bounds_str):
            start_end = bounds_str.split(":")

            assert 1 <= len(start_end) <= 2

            return tuple(self.parse_expr(s) for s in start_end)

        for decl in dim_decls:
            entity_match = self.ENTITY_RE.match(decl)
            assert entity_match

            groups = entity_match.groupdict()
            name = groups["name"]
            assert name

            if groups["shape"]:
                shape = [parse_bounds(s) for s in groups["shape"].split(",")]
            else:
                shape = None

            yield name, shape

    def __call__(self, expr, *args, **kwargs):
        return self.rec(expr, *args, **kwargs)

    # {{{ expressions

    def parse_expr(self, expr_str):
        return self.expr_parser(expr_str)

    # }}}


class ArgumentAnalayzer(FTreeWalkerBase):
    def __init__(self):
        FTreeWalkerBase.__init__(self)

        # map (func, arg_nr) to
        # 'w' for 'needs pointer'
        # [] for no obstacle to de-pointerification known
        # [(func_name, arg_nr), ...] # depends on how this arg is used

        self.arg_usage_info = {}

    def arg_needs_pointer(self, func, arg_nr):
        data = self.arg_usage_info.get((func, arg_nr), [])

        if isinstance(data, list):
            return any(
                    self.arg_needs_pointer(sub_func, sub_arg_nr)
                    for sub_func, sub_arg_nr in data)

        return True

    # {{{ map_XXX functions

    def map_BeginSource(self, node):
        scope = Scope(None)
        self.scope_stack.append(scope)

        for c in node.content:
            self.rec(c)

    def map_Subroutine(self, node):
        scope = Scope(node.name, list(node.args))
        self.scope_stack.append(scope)

        for c in node.content:
            self.rec(c)

        self.scope_stack.pop()

    def map_EndSubroutine(self, node):
        pass

    def map_Implicit(self, node):
        pass

    # {{{ types, declarations

    def map_Equivalence(self, node):
        raise NotImplementedError("equivalence")

    def map_Dimension(self, node):
        scope = self.scope_stack[-1]

        for name, shape in self.parse_dimension_specs(node.items):
            if name in scope.arg_names:
                arg_idx = scope.arg_names.index(name)
                self.arg_usage_info[scope.subprogram_name, arg_idx] = "w"

    def map_External(self, node):
        pass

    def map_type_decl(self, node):
        scope = self.scope_stack[-1]

        for name, shape in self.parse_dimension_specs(node.entity_decls):
            if shape is not None and name in scope.arg_names:
                arg_idx = scope.arg_names.index(name)
                self.arg_usage_info[scope.subprogram_name, arg_idx] = "w"

    map_Logical = map_type_decl
    map_Integer = map_type_decl
    map_Real = map_type_decl
    map_Complex = map_type_decl

    # }}}

    def map_Data(self, node):
        pass

    def map_Parameter(self, node):
        raise NotImplementedError("parameter")

    # {{{ I/O

    def map_Open(self, node):
        pass

    def map_Format(self, node):
        pass

    def map_Write(self, node):
        pass

    def map_Print(self, node):
        pass

    def map_Read1(self, node):
        pass

    # }}}

    def map_Assignment(self, node):
        scope = self.scope_stack[-1]

        lhs = self.parse_expr(node.variable)

        from pymbolic.primitives import Subscript, Call
        if isinstance(lhs, Subscript):
            lhs_name = lhs.aggregate.name
        elif isinstance(lhs, Call):
            # in absence of dim info, subscripts get parsed as calls
            lhs_name = lhs.function.name
        else:
            lhs_name = lhs.name

        if lhs_name in scope.arg_names:
            arg_idx = scope.arg_names.index(lhs_name)
            self.arg_usage_info[scope.subprogram_name, arg_idx] = "w"

    def map_Allocate(self, node):
        raise NotImplementedError("allocate")

    def map_Deallocate(self, node):
        raise NotImplementedError("deallocate")

    def map_Save(self, node):
        raise NotImplementedError("save")

    def map_Line(self, node):
        raise NotImplementedError

    def map_Program(self, node):
        raise NotImplementedError

    def map_Entry(self, node):
        raise NotImplementedError

    # {{{ control flow

    def map_Goto(self, node):
        pass

    def map_Call(self, node):
        scope = self.scope_stack[-1]

        from pymbolic.primitives import Subscript, Variable
        for i, arg_str in enumerate(node.items):
            arg = self.parse_expr(arg_str)
            if isinstance(arg, (Variable, Subscript)):
                if isinstance(arg, Subscript):
                    arg_name = arg.aggregate.name
                else:
                    arg_name = arg.name

                if arg_name in scope.arg_names:
                    arg_idx = scope.arg_names.index(arg_name)
                    arg_usage = self.arg_usage_info.setdefault(
                            (scope.subprogram_name, arg_idx),
                            [])
                    if isinstance(arg_usage, list):
                        arg_usage.append((node.designator, i))

    def map_Return(self, node):
        pass

    def map_ArithmeticIf(self, node):
        pass

    def map_If(self, node):
        for c in node.content:
            self.rec(c)

    def map_IfThen(self, node):
        for c in node.content:
            self.rec(c)

    def map_ElseIf(self, node):
        pass

    def map_Else(self, node):
        pass

    def map_EndIfThen(self, node):
        pass

    def map_Do(self, node):
        for c in node.content:
            self.rec(c)

    def map_EndDo(self, node):
        pass

    def map_Continue(self, node):
        pass

    def map_Stop(self, node):
        pass

    def map_Comment(self, node):
        pass

    # }}}

    # }}}


# {{{ translator

class F2CLTranslator(FTreeWalkerBase):
    def __init__(self, addr_space_hints, force_casts, arg_info,
            use_restrict_pointers):
        FTreeWalkerBase.__init__(self)
        self.addr_space_hints = addr_space_hints
        self.force_casts = force_casts
        self.arg_info = arg_info
        self.use_restrict_pointers = use_restrict_pointers

    def arg_needs_pointer(self, subprogram_name, arg_index):
        return self.arg_info.arg_needs_pointer(subprogram_name, arg_index)

    # {{{ declaration helpers

    def get_declarator(self, name):
        scope = self.scope_stack[-1]
        return POD(scope.get_type(name), name)

    def get_declarations(self):
        scope = self.scope_stack[-1]

        result = []
        pre_func_decl = []

        def gen_shape(start_end):
            return ":".join(self.gen_expr(s) for s in start_end)

        for name in sorted(scope.known_names()):
            shape = scope.dim_map.get(name)

            if shape is not None:
                dim_stmt = cgen.Statement(
                    "dimension \"fortran\" %s[%s]" % (
                        scope.translate_var_name(name),
                        ", ".join(gen_shape(s) for s in shape)
                        ))

                # cannot omit 'dimension' decl even for rank-1 args:
                result.append(dim_stmt)

            if name in scope.data:
                assert name not in scope.arg_names

                data = scope.data[name]

                if shape is None:
                    assert len(data) == 1
                    result.append(
                            cgen.Initializer(
                                self.get_declarator(name),
                                self.gen_expr(data[0])
                                ))
                else:
                    from cgen.opencl import CLConstant
                    pre_func_decl.append(
                            cgen.Initializer(
                                CLConstant(
                                    cgen.ArrayOf(self.get_declarator(
                                        "%s_%s" % (scope.subprogram_name, name)))),
                                "{ %s }" % ",\n".join(self.gen_expr(x) for x in data)
                                ))
            else:
                if name not in scope.arg_names:
                    if shape is not None:
                        result.append(cgen.Statement(
                            "%s %s[nitemsof(%s)]"
                                % (
                                    dtype_to_ctype(scope.get_type(name)),
                                    name, name)))
                    else:
                        result.append(self.get_declarator(name))

        return pre_func_decl, result

    def map_statement_list(self, content):
        body = []

        for c in content:
            mapped = self.rec(c)
            if mapped is None:
                warn("mapping '%s' returned None" % type(c))
            elif isinstance(mapped, list):
                body.extend(mapped)
            else:
                body.append(mapped)

        return body

    # }}}

    # {{{ map_XXX functions

    def map_BeginSource(self, node):
        scope = Scope(None)
        self.scope_stack.append(scope)

        return self.map_statement_list(node.content)

    def map_Subroutine(self, node):
        assert not node.prefix
        assert not hasattr(node, "suffix")

        scope = Scope(node.name, list(node.args))
        self.scope_stack.append(scope)

        body = self.map_statement_list(node.content)

        pre_func_decl, in_func_decl = self.get_declarations()
        body = in_func_decl + [cgen.Line()] + body

        if isinstance(body[-1], cgen.Statement) and body[-1].text == "return":
            body.pop()

        def get_arg_decl(arg_idx, arg_name):
            decl = self.get_declarator(arg_name)

            if self.arg_needs_pointer(node.name, arg_idx):
                hint = self.addr_space_hints.get((node.name, arg_name))
                if hint:
                    decl = hint(cgen.Pointer(decl))
                else:
                    if self.use_restrict_pointers:
                        decl = cgen.RestrictPointer(decl)
                    else:
                        decl = cgen.Pointer(decl)

            return decl

        result = cgen.FunctionBody(
                cgen.FunctionDeclaration(
                    cgen.Value("void", node.name),
                    [get_arg_decl(i, arg) for i, arg in enumerate(node.args)]
                    ),
                cgen.Block(body))

        self.scope_stack.pop()
        if pre_func_decl:
            return pre_func_decl + [cgen.Line(), result]
        else:
            return result

    def map_EndSubroutine(self, node):
        return []

    def map_Implicit(self, node):
        scope = self.scope_stack[-1]

        if not node.items:
            assert not scope.implicit_types
            scope.implicit_types = None

        for stmt, specs in node.items:
            tp = self.dtype_from_stmt(stmt)
            for start, end in specs:
                for char_code in range(ord(start), ord(end)+1):
                    scope.implicit_types[chr(char_code)] = tp

        return []

    # {{{ types, declarations

    def map_Equivalence(self, node):
        raise NotImplementedError("equivalence")

    TYPE_MAP = {
            ("real", "4"): np.float32,
            ("real", "8"): np.float64,
            ("real", "16"): np.float128,

            ("complex", "8"): np.complex64,
            ("complex", "16"): np.complex128,
            ("complex", "32"): np.complex256,

            ("integer", ""): np.int32,
            ("integer", "4"): np.int32,
            ("complex", "8"): np.int64,
            }

    def dtype_from_stmt(self, stmt):
        length, kind = stmt.selector
        assert not kind
        return np.dtype(self.TYPE_MAP[(type(stmt).__name__.lower(), length)])

    def map_type_decl(self, node):
        scope = self.scope_stack[-1]

        tp = self.dtype_from_stmt(node)

        for name, shape in self.parse_dimension_specs(node.entity_decls):
            if shape is not None:
                assert name not in scope.dim_map
                scope.dim_map[name] = shape
                scope.use_name(name)

            assert name not in scope.type_map
            scope.type_map[name] = tp

        return []

    map_Logical = map_type_decl
    map_Integer = map_type_decl
    map_Real = map_type_decl
    map_Complex = map_type_decl

    def map_Dimension(self, node):
        scope = self.scope_stack[-1]

        for name, shape in self.parse_dimension_specs(node.items):
            if shape is not None:
                assert name not in scope.dim_map
                scope.dim_map[name] = shape
                scope.use_name(name)

        return []

    def map_External(self, node):
        raise NotImplementedError("external")

    # }}}

    def map_Data(self, node):
        scope = self.scope_stack[-1]

        for name, data in node.stmts:
            name, = name
            assert name not in scope.data
            scope.data[name] = [self.parse_expr(i) for i in data]

        return []

    def map_Parameter(self, node):
        raise NotImplementedError("parameter")

    # {{{ I/O

    def map_Open(self, node):
        raise NotImplementedError

    def map_Format(self, node):
        warn("'format' unsupported", TranslatorWarning)

    def map_Write(self, node):
        warn("'write' unsupported", TranslatorWarning)

    def map_Print(self, node):
        warn("'print' unsupported", TranslatorWarning)

    def map_Read1(self, node):
        warn("'read' unsupported", TranslatorWarning)

    # }}}

    def map_Assignment(self, node):
        lhs = self.parse_expr(node.variable)
        from pymbolic.primitives import Subscript
        if isinstance(lhs, Subscript):
            lhs_name = lhs.aggregate.name
        else:
            lhs_name = lhs.name

        scope = self.scope_stack[-1]
        scope.use_name(lhs_name)
        infer_type = scope.get_type_inference_mapper()

        rhs = self.parse_expr(node.expr)
        lhs_dtype = infer_type(lhs)
        rhs_dtype = infer_type(rhs)

        # check for silent truncation of complex
        if lhs_dtype.kind != 'c' and rhs_dtype.kind == 'c':
            from pymbolic import var
            rhs = var("real")(rhs)
        # check for silent widening of real
        if lhs_dtype.kind == 'c' and rhs_dtype.kind != 'c':
            from pymbolic import var
            rhs = var("fromreal")(rhs)

        return cgen.Assign(self.gen_expr(lhs), self.gen_expr(rhs))

    def map_Allocate(self, node):
        raise NotImplementedError("allocate")

    def map_Deallocate(self, node):
        raise NotImplementedError("deallocate")

    def map_Save(self, node):
        raise NotImplementedError("save")

    def map_Line(self, node):
        #from warnings import warn
        #warn("Encountered a 'line': %s" % node)
        raise NotImplementedError

    def map_Program(self, node):
        raise NotImplementedError

    def map_Entry(self, node):
        raise NotImplementedError

    # {{{ control flow

    def map_Goto(self, node):
        return cgen.Statement("goto label_%s" % node.label)

    def map_Call(self, node):
        def transform_arg(i, arg_str):
            expr = self.parse_expr(arg_str)
            result = self.gen_expr(expr)
            if self.arg_needs_pointer(node.designator, i):
                result = "&"+result

            cast = self.force_casts.get(
                    (node.designator, i))
            if cast is not None:
                result = "(%s) (%s)" % (cast, result)

            return result

        return cgen.Statement("%s(%s)" % (
            node.designator,
            ", ".join(transform_arg(i, arg_str)
                for i, arg_str in enumerate(node.items))))

    def map_Return(self, node):
        return cgen.Statement("return")

    def map_ArithmeticIf(self, node):
        raise NotImplementedError

    def map_If(self, node):
        return cgen.If(self.transform_expr(node.expr),
                self.rec(node.content[0]))

    def map_IfThen(self, node):
        current_cond = self.transform_expr(node.expr)

        blocks_and_conds = []
        else_block = []

        def end_block():
            if current_body:
                if current_cond is None:
                    else_block[:] = self.map_statement_list(current_body)
                else:
                    blocks_and_conds.append(
                            (current_cond, cgen.block_if_necessary(
                                self.map_statement_list(current_body))))

            del current_body[:]

        from fparser.statements import Else, ElseIf
        i = 0
        current_body = []
        while i < len(node.content):
            c = node.content[i]
            if isinstance(c, ElseIf):
                end_block()
                current_cond = self.transform_expr(c.expr)
            elif isinstance(c, Else):
                end_block()
                current_cond = None
            else:
                current_body.append(c)

            i += 1
        end_block()

        def block_or_none(body):
            if not body:
                return None
            else:
                return cgen.block_if_necessary(body)

        return cgen.make_multiple_ifs(
                blocks_and_conds,
                block_or_none(else_block))

    def map_EndIfThen(self, node):
        return []

    def map_Do(self, node):
        scope = self.scope_stack[-1]

        body = self.map_statement_list(node.content)

        if node.loopcontrol:
            loop_var, loop_bounds = node.loopcontrol.split("=")
            loop_var = loop_var.strip()
            scope.use_name(loop_var)
            loop_bounds = [self.parse_expr(s) for s in loop_bounds.split(",")]

            if len(loop_bounds) == 2:
                start, stop = loop_bounds
                step = 1
            elif len(loop_bounds) == 3:
                start, stop, step = loop_bounds
            else:
                raise RuntimeError("loop bounds not understood: %s"
                        % node.loopcontrol)

            if not isinstance(step, int):
                print type(step)
                raise TranslationError(
                        "non-constant steps not yet supported: %s" % step)

            if step < 0:
                comp_op = ">="
            else:
                comp_op = "<="

            return cgen.For(
                    "%s = %s" % (loop_var, self.gen_expr(start)),
                    "%s %s %s" % (loop_var, comp_op, self.gen_expr(stop)),
                    "%s += %s" % (loop_var, self.gen_expr(step)),
                    cgen.block_if_necessary(body))

        else:
            raise NotImplementedError("unbounded do loop")

    def map_EndDo(self, node):
        return []

    def map_Continue(self, node):
        return cgen.Statement("label_%s:" % node.label)

    def map_Stop(self, node):
        raise NotImplementedError("stop")

    def map_Comment(self, node):
        if node.content:
            return cgen.LineComment(node.content.strip())
        else:
            return []

    # }}}

    # }}}

    # {{{ expressions

    def gen_expr(self, expr):
        scope = self.scope_stack[-1]
        return CCodeMapper(self, scope)(expr)

    def transform_expr(self, expr_str):
        return self.gen_expr(self.expr_parser(expr_str))

    # }}}

# }}}


def f2cl(source, free_form=False, strict=True,
        addr_space_hints={}, force_casts={},
        do_arg_analysis=True,
        use_restrict_pointers=False,
        try_compile=False):
    from fparser import api
    tree = api.parse(source, isfree=free_form, isstrict=strict,
            analyze=False, ignore_comments=False)

    arg_info = ArgumentAnalayzer()
    if do_arg_analysis:
        arg_info(tree)

    source = F2CLTranslator(addr_space_hints, force_casts,
            arg_info, use_restrict_pointers=use_restrict_pointers)(tree)

    func_decls = []
    for entry in source:
        if isinstance(entry, cgen.FunctionBody):
            func_decls.append(entry.fdecl)

    mod = cgen.Module(func_decls + [cgen.Line()] + source)

    #open("pre-cnd.cl", "w").write(str(mod))

    from cnd import transform_cl
    str_mod = transform_cl(str(mod))

    if try_compile:
        import pyopencl as cl
        ctx = cl.create_some_context()
        cl.Program(ctx, """
            #pragma OPENCL EXTENSION cl_khr_fp64: enable
            #include <pyopencl-complex.h>
            """).build()
    return str_mod


def f2cl_files(source_file, target_file, **kwargs):
    mod = f2cl(open(source_file).read(), **kwargs)
    open(target_file, "w").write(mod)


if __name__ == "__main__":
    from cgen.opencl import CLConstant

    if 0:
        f2cl_files("hank107.f", "hank107.cl",
                addr_space_hints={
                    ("hank107p", "p"): CLConstant,
                    ("hank107pc", "p"): CLConstant,
                    },
                force_casts={
                    ("hank107p", 0): "__constant cdouble_t *",
                    })

        f2cl_files("cdjseval2d.f", "cdjseval2d.cl")

    f2cl_files("hank103.f", "hank103.cl",
            addr_space_hints={
                ("hank103p", "p"): CLConstant,
                ("hank103pc", "p"): CLConstant,
                },
            force_casts={
                ("hank103p", 0): "__constant cdouble_t *",
                },
            try_compile=True)

# vim: foldmethod=marker

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# PyOpenCL documentation build configuration file, created by
# sphinx-quickstart on Fri Jun 13 00:51:19 2008.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# The contents of this file are pickled, so don't put values in the namespace
# that aren't pickleable (module imports are okay, they're removed automatically).
#
# All configuration values have a default value; values that are commented out
# serve to show the default value.

#import sys, os

# If your extensions are in another directory, add it here. If the directory
# is relative to the documentation root, use os.path.abspath to make it
# absolute, like shown here.
#sys.path.append(os.path.abspath('some/directory'))

# General configuration
# ---------------------

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = [
        'sphinx.ext.intersphinx',
        'sphinx.ext.autodoc',
        'sphinx.ext.doctest',
        ]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

exclude_patterns = ['subst.rst']

# The suffix of source filenames.
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

# General substitutions.
project = 'PyOpenCL'
copyright = '2009, Andreas Kloeckner'

# The default replacements for |version| and |release|, also used in various
# other places throughout the built documents.
#
# The short X.Y version.
ver_dic = {}
execfile("../pyopencl/version.py", ver_dic)
version = ".".join(str(x) for x in ver_dic["VERSION"])
# The full version, including alpha/beta/rc tags.
release = ver_dic["VERSION_TEXT"]

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

try:
    import sphinx_bootstrap_theme
except:
    from warnings import warn
    warn("I would like to use the sphinx bootstrap theme, but can't find it.\n"
            "'pip install sphinx_bootstrap_theme' to fix.")
else:
    # Activate the theme.
    html_theme = 'bootstrap'
    html_theme_path = sphinx_bootstrap_theme.get_html_theme_path()

    # Theme options are theme-specific and customize the look and feel of a
    # theme further.  For a list of options available for each theme, see the
    # documentation.
    html_theme_options = {
            "navbar_fixed_top": "true",
            "navbar_site_name": "Contents",
            'bootstrap_version': '3',
            'source_link_position': 'footer',
            }

# The style sheet to use for HTML and HTML Help pages. A file of that name
# must exist either in Sphinx' static/ path, or in one of the custom paths
# given in html_static_path.
#html_style = 'default.css'

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# The name of an image file (within the static path) to place at the top of
# the sidebar.
#html_logo = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

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

# If true, the reST sources are included in the HTML build as _sources/<name>.
html_copy_source = False

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# If nonempty, this is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = ''

# Output file base name for HTML help builder.
htmlhelp_basename = 'PyOpenClDoc'


# Options for LaTeX output
# ------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, document class [howto/manual]).
latex_documents = [
        ('index', 'pyopencl.tex', 'PyOpenCL Documentation',
            'Andreas Kloeckner', 'manual'),
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

intersphinx_mapping = {
        'http://docs.python.org/dev': None,
        'http://docs.scipy.org/doc/numpy/': None,
        'http://docs.makotemplates.org/en/latest/': None,
        }

autoclass_content = "both"

########NEW FILE########
__FILENAME__ = make_constants
__copyright__ = "Copyright (C) 2009 Andreas Kloeckner"

__license__ = """
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

import pyopencl as cl

fission = ("cl_ext_device_fission", "2011.1")
nv_devattr = ("cl_nv_device_attribute_query", "0.92")
gl_sharing = ("cl_khr_gl_sharing", "0.92")
cl_11 = ("CL_1.1", "0.92")
cl_12 = ("CL_1.2", "2011.2")
amd_devattr = ("cl_amd_device_attribute_query", "2013.2")


def get_extra_lines(tup):
    ext_name, pyopencl_ver = tup
    if ext_name is not None:
        if ext_name.startswith("CL_"):
            # capital letters -> CL version, not extension
            yield ""
            yield "    Available with OpenCL %s." % (
                    ext_name[3:])
            yield ""

        else:
            yield ""
            yield "    Available with the ``%s`` extension." % ext_name
            yield ""

    if pyopencl_ver is not None:
        yield ""
        yield "    .. versionadded:: %s" % pyopencl_ver
        yield ""

const_ext_lookup = {
        cl.status_code: {
            "PLATFORM_NOT_FOUND_KHR": ("cl_khr_icd", "2011.1"),

            "INVALID_GL_SHAREGROUP_REFERENCE_KHR": gl_sharing,

            "MISALIGNED_SUB_BUFFER_OFFSET": cl_11,
            "EXEC_STATUS_ERROR_FOR_EVENTS_IN_WAIT_LIST": cl_11,
            "INVALID_GLOBAL_WORK_SIZE": cl_11,

            "COMPILE_PROGRAM_FAILURE": cl_12,
            "LINKER_NOT_AVAILABLE": cl_12,
            "LINK_PROGRAM_FAILURE": cl_12,
            "DEVICE_PARTITION_FAILED": cl_12,
            "KERNEL_ARG_INFO_NOT_AVAILABLE": cl_12,
            "INVALID_IMAGE_DESCRIPTOR": cl_12,
            "INVALID_COMPILER_OPTIONS": cl_12,
            "INVALID_LINKER_OPTIONS": cl_12,
            "INVALID_DEVICE_PARTITION_COUNT": cl_12,

            },

        cl.device_info: {
            "PREFERRED_VECTOR_WIDTH_HALF": cl_11,
            "HOST_UNIFIED_MEMORY": cl_11,
            "NATIVE_VECTOR_WIDTH_CHAR": cl_11,
            "NATIVE_VECTOR_WIDTH_SHORT": cl_11,
            "NATIVE_VECTOR_WIDTH_INT": cl_11,
            "NATIVE_VECTOR_WIDTH_LONG": cl_11,
            "NATIVE_VECTOR_WIDTH_FLOAT": cl_11,
            "NATIVE_VECTOR_WIDTH_DOUBLE": cl_11,
            "NATIVE_VECTOR_WIDTH_HALF": cl_11,
            "OPENCL_C_VERSION": cl_11,
            "COMPUTE_CAPABILITY_MAJOR_NV": nv_devattr,
            "COMPUTE_CAPABILITY_MINOR_NV": nv_devattr,
            "REGISTERS_PER_BLOCK_NV": nv_devattr,
            "WARP_SIZE_NV": nv_devattr,
            "GPU_OVERLAP_NV": nv_devattr,
            "KERNEL_EXEC_TIMEOUT_NV": nv_devattr,
            "INTEGRATED_MEMORY_NV": nv_devattr,

            "DOUBLE_FP_CONFIG":
            ("cl_khr_fp64", "2011.1"),
            "HALF_FP_CONFIG":
            ("cl_khr_fp16", "2011.1"),

            "PROFILING_TIMER_OFFSET_AMD": amd_devattr,
            "TOPOLOGY_AMD": amd_devattr,
            "BOARD_NAME_AMD": amd_devattr,
            "GLOBAL_FREE_MEMORY_AMD": amd_devattr,
            "SIMD_PER_COMPUTE_UNIT_AMD": amd_devattr,
            "SIMD_WIDTH_AMD": amd_devattr,
            "SIMD_INSTRUCTION_WIDTH_AMD": amd_devattr,
            "WAVEFRONT_WIDTH_AMD": amd_devattr,
            "GLOBAL_MEM_CHANNELS_AMD": amd_devattr,
            "GLOBAL_MEM_CHANNEL_BANKS_AMD": amd_devattr,
            "GLOBAL_MEM_CHANNEL_BANK_WIDTH_AMD": amd_devattr,
            "LOCAL_MEM_SIZE_PER_COMPUTE_UNIT_AMD": amd_devattr,
            "LOCAL_MEM_BANKS_AMD": amd_devattr,

            "MAX_ATOMIC_COUNTERS_EXT":
            ("cl_ext_atomic_counters_64", "2013.2"),

            "PARENT_DEVICE_EXT":
            fission,
            "PARTITION_TYPES_EXT":
            fission,
            "AFFINITY_DOMAINS_EXT":
            fission,
            "REFERENCE_COUNT_EXT":
            fission,
            "PARTITION_STYLE_EXT": fission,

            "LINKER_AVAILABLE": cl_12,
            "BUILT_IN_KERNELS": cl_12,
            "IMAGE_MAX_BUFFER_SIZE": cl_12,
            "IMAGE_MAX_ARRAY_SIZE": cl_12,
            "PARENT_DEVICE": cl_12,
            "PARTITION_MAX_SUB_DEVICES": cl_12,
            "PARTITION_PROPERTIES": cl_12,
            "PARTITION_AFFINITY_DOMAIN": cl_12,
            "PARTITION_TYPE": cl_12,
            "REFERENCE_COUNT": cl_12,
            "PREFERRED_INTEROP_USER_SYNC": cl_12,
            "PRINTF_BUFFER_SIZE": cl_12,
            },

        cl.mem_object_type: {
            "IMAGE2D_ARRAY": cl_12,
            "IMAGE1D": cl_12,
            "IMAGE1D_ARRAY": cl_12,
            "IMAGE1D_BUFFER": cl_12,
            },

        cl.device_type: {
            "CUSTOM": cl_12,
            },

        cl.context_properties: {
            "GL_CONTEXT_KHR": gl_sharing,
            "EGL_DISPLAY_KHR": gl_sharing,
            "GLX_DISPLAY_KHR": gl_sharing,
            "WGL_HDC_KHR": gl_sharing,
            "CGL_SHAREGROUP_KHR": gl_sharing,

            "OFFLINE_DEVICES_AMD":
            ("cl_amd_offline_devices", "2011.1"),
            },

        cl.device_fp_config: {
            "SOFT_FLOAT": cl_11,
            "CORRECTLY_ROUNDED_DIVIDE_SQRT": cl_12,
            },

        cl.context_info: {
            "NUM_DEVICES": cl_11,
            "INTEROP_USER_SYNC": cl_12,
            },

        cl.channel_order: {
            "Rx": cl_11,
            "RGx": cl_11,
            "RGBx": cl_11,
            },

        cl.kernel_work_group_info: {
            "PREFERRED_WORK_GROUP_SIZE_MULTIPLE": cl_11,
            "PRIVATE_MEM_SIZE": cl_11,
            "GLOBAL_WORK_SIZE": cl_12,
            },

        cl.addressing_mode: {
            "MIRRORED_REPEAT": cl_11,
            },

        cl.event_info: {
            "CONTEXT": cl_11,
            },

        cl.mem_info: {
            "ASSOCIATED_MEMOBJECT": cl_11,
            "OFFSET": cl_11,
            },

        cl.image_info: {
            "ARRAY_SIZE": cl_12,
            "BUFFER": cl_12,
            "NUM_MIP_LEVELS": cl_12,
            "NUM_SAMPLES": cl_12,
            },

        cl.map_flags: {
            "WRITE_INVALIDATE_REGION": cl_12,
            },

        cl.program_info: {
            "NUM_KERNELS": cl_12,
            "KERNEL_NAMES": cl_12,
            },

        cl.program_build_info: {
            "BINARY_TYPE": cl_12,
            },

        cl.program_binary_type: {
            "NONE": cl_12,
            "COMPILED_OBJECT": cl_12,
            "LIBRARY": cl_12,
            "EXECUTABLE": cl_12,
            },

        cl.kernel_info: {
            "ATTRIBUTES": cl_12,
            },

        cl.kernel_arg_info: {
            "ADDRESS_QUALIFIER": cl_12,
            "ACCESS_QUALIFIER": cl_12,
            "TYPE_NAME": cl_12,
            "ARG_NAME": cl_12,
            },

        cl.kernel_arg_address_qualifier: {
            "GLOBAL": cl_12,
            "LOCAL": cl_12,
            "CONSTANT": cl_12,
            "PRIVATE": cl_12,
            },

        cl.kernel_arg_access_qualifier: {
            "READ_ONLY": cl_12,
            "WRITE_ONLY": cl_12,
            "READ_WRITE": cl_12,
            "NONE": cl_12,
            },

        cl.command_type: {
            "READ_BUFFER_RECT": cl_11,
            "WRITE_BUFFER_RECT": cl_11,
            "COPY_BUFFER_RECT": cl_11,
            "USER": cl_11,
            "MIGRATE_MEM_OBJECT_EXT": ("cl_ext_migrate_memobject", "2011.2"),
            "BARRIER": cl_12,
            "MIGRATE_MEM_OBJECTS": cl_12,
            "FILL_BUFFER": cl_12,
            "FILL_IMAGE": cl_12,
            },

        cl.mem_flags: {
            "USE_PERSISTENT_MEM_AMD":
            ("cl_amd_device_memory_flags", "2011.1"),
            "HOST_WRITE_ONLY": cl_12,
            },

        cl.device_partition_property: {
            "EQUALLY": cl_12,
            "BY_COUNTS": cl_12,
            "BY_NAMES": cl_12,
            "BY_AFFINITY_DOMAIN": cl_12,

            "PROPERTIES_LIST_END": cl_12,
            "PARTITION_BY_COUNTS_LIST_END": cl_12,
            "PARTITION_BY_NAMES_LIST_END": cl_12,
            },

        cl.device_affinity_domain: {
            "NUMA": cl_12,
            "L4_CACHE": cl_12,
            "L3_CACHE": cl_12,
            "L2_CACHE": cl_12,
            "L1_CACHE": cl_12,
            "NEXT_PARITIONNABLE": cl_12,
            },

        cl.device_partition_property_ext: {
            "EQUALLY": fission,
            "BY_COUNTS": fission,
            "BY_NAMES": fission,
            "BY_AFFINITY_DOMAIN": fission,

            "PROPERTIES_LIST_END": fission,
            "PARTITION_BY_COUNTS_LIST_END": fission,
            "PARTITION_BY_NAMES_LIST_END": fission,
            },
        cl.affinity_domain_ext: {
            "L1_CACHE": fission,
            "L2_CACHE": fission,
            "L3_CACHE": fission,
            "L4_CACHE": fission,
            "NUMA": fission,
            "NEXT_FISSIONABLE": fission,
            },

        cl.mem_migration_flags: {
            "HOST": cl_12,
            "CONTENT_UNDEFINED": cl_12,
            },

        cl.migrate_mem_object_flags_ext: {
            "HOST": ("cl_ext_migrate_memobject", "2011.2"),
            },
        }
try:
    gl_ci = cl.gl_context_info
except AttributeError:
    pass
else:
    const_ext_lookup[gl_ci] = {
            getattr(gl_ci, "CURRENT_DEVICE_FOR_GL_CONTEXT_KHR", None):
            gl_sharing,

            getattr(gl_ci, "DEVICES_FOR_GL_CONTEXT_KHR", None):
            gl_sharing,
            }

cls_ext_lookup = {
        #cl.buffer_create_type: ("CL_1.1", "0.92"),
        }


def doc_class(cls):
    print ".. class :: %s" % cls.__name__
    print
    if cls.__name__.startswith("gl_"):
        print "    Only available when PyOpenCL is compiled with GL support."
        print "    See :func:`have_gl`."
        print

    if cls in cls_ext_lookup:
        for l in get_extra_lines(cls_ext_lookup[cls]):
            print l

    cls_const_ext = const_ext_lookup.get(cls, {})
    for name in sorted(dir(cls)):
        if not name.startswith("_") and not name in ["to_string", "names", "values"]:
            print "    .. attribute :: %s" % name

            if name in cls_const_ext:
                for l in get_extra_lines(cls_const_ext[name]):
                    print "    "+l

    print "    .. method :: to_string(value)"
    print
    print "        Returns a :class:`str` representing *value*."
    print
    print "        .. versionadded:: 0.91"
    print


if not cl.have_gl():
    print ".. warning::"
    print
    print "    This set of PyOpenCL documentation is incomplete because it"
    print "    was generated on a PyOpenCL build that did not support OpenGL."
    print

print ".. This is an automatically generated file. DO NOT EDIT"
print
for cls in cl.CONSTANT_CLASSES:
    doc_class(cls)

########NEW FILE########
__FILENAME__ = benchmark
# example provided by Roger Pau Monn'e

from __future__ import print_function
import pyopencl as cl
import numpy
import numpy.linalg as la
import datetime
from time import time

data_points = 2**23 # ~8 million data points, ~32 MB data
workers = 2**8 # 256 workers, play with this to see performance differences
               # eg: 2**0 => 1 worker will be non-parallel execution on gpu
               # data points must be a multiple of workers

a = numpy.random.rand(data_points).astype(numpy.float32)
b = numpy.random.rand(data_points).astype(numpy.float32)
c_result = numpy.empty_like(a)

# Speed in normal CPU usage
time1 = time()
c_temp = (a+b) # adds each element in a to its corresponding element in b
c_temp = c_temp * c_temp # element-wise multiplication
c_result = c_temp * (a/2.0) # element-wise half a and multiply
time2 = time()

print("Execution time of test without OpenCL: ", time2 - time1, "s")


for platform in cl.get_platforms():
    for device in platform.get_devices():
        print("===============================================================")
        print("Platform name:", platform.name)
        print("Platform profile:", platform.profile)
        print("Platform vendor:", platform.vendor)
        print("Platform version:", platform.version)
        print("---------------------------------------------------------------")
        print("Device name:", device.name)
        print("Device type:", cl.device_type.to_string(device.type))
        print("Device memory: ", device.global_mem_size//1024//1024, 'MB')
        print("Device max clock speed:", device.max_clock_frequency, 'MHz')
        print("Device compute units:", device.max_compute_units)
        print("Device max work group size:", device.max_work_group_size)
        print("Device max work item sizes:", device.max_work_item_sizes)

        # Simnple speed test
        ctx = cl.Context([device])
        queue = cl.CommandQueue(ctx, 
                properties=cl.command_queue_properties.PROFILING_ENABLE)

        mf = cl.mem_flags
        a_buf = cl.Buffer(ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=a)
        b_buf = cl.Buffer(ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=b)
        dest_buf = cl.Buffer(ctx, mf.WRITE_ONLY, b.nbytes)

        prg = cl.Program(ctx, """
            __kernel void sum(__global const float *a,
            __global const float *b, __global float *c)
            {
                        int gid = get_global_id(0);
                        float a_temp;
                        float b_temp;
                        float c_temp;

                        a_temp = a[gid]; // my a element (by global ref)
                        b_temp = b[gid]; // my b element (by global ref)
                        
                        c_temp = a_temp+b_temp; // sum of my elements
                        c_temp = c_temp * c_temp; // product of sums
                        c_temp = c_temp * (a_temp/2.0); // times 1/2 my a

                        c[gid] = c_temp; // store result in global memory
                }
                """).build()

        global_size=(data_points,)
        local_size=(workers,)
        preferred_multiple = cl.Kernel(prg, 'sum').get_work_group_info( \
            cl.kernel_work_group_info.PREFERRED_WORK_GROUP_SIZE_MULTIPLE, \
            device)

        print("Data points:", data_points)
        print("Workers:", workers)
        print("Preferred work group size multiple:", preferred_multiple)

        if (workers % preferred_multiple):
            print("Number of workers not a preferred multiple (%d*N)." \
                    % (preferred_multiple))
            print("Performance may be reduced.")

        exec_evt = prg.sum(queue, global_size, local_size, a_buf, b_buf, dest_buf)
        exec_evt.wait()
        elapsed = 1e-9*(exec_evt.profile.end - exec_evt.profile.start)

        print("Execution time of test: %g s" % elapsed)

        c = numpy.empty_like(a)
        cl.enqueue_read_buffer(queue, dest_buf, c).wait()
        equal = numpy.all( c == c_result)

        if not equal:
                print("Results doesn't match!!")
        else:
                print("Results OK")

########NEW FILE########
__FILENAME__ = demo-struct-reduce
import numpy as np
import pyopencl as cl

def make_collector_dtype(device):
    dtype = np.dtype([
        ("cur_min", np.int32),
        ("cur_max", np.int32),
        ("pad", np.int32),
        ])

    name = "minmax_collector"
    from pyopencl.tools import get_or_register_dtype, match_dtype_to_c_struct

    dtype, c_decl = match_dtype_to_c_struct(device, name, dtype)
    dtype = get_or_register_dtype(name, dtype)

    return dtype, c_decl

ctx = cl.create_some_context()
queue = cl.CommandQueue(ctx)

mmc_dtype, mmc_c_decl = make_collector_dtype(ctx.devices[0])

preamble = mmc_c_decl + r"""//CL//

    minmax_collector mmc_neutral()
    {
        // FIXME: needs infinity literal in real use, ok here
        minmax_collector result;
        result.cur_min = 1<<30;
        result.cur_max = -(1<<30);
        return result;
    }

    minmax_collector mmc_from_scalar(float x)
    {
        minmax_collector result;
        result.cur_min = x;
        result.cur_max = x;
        return result;
    }

    minmax_collector agg_mmc(minmax_collector a, minmax_collector b)
    {
        minmax_collector result = a;
        if (b.cur_min < result.cur_min)
            result.cur_min = b.cur_min;
        if (b.cur_max > result.cur_max)
            result.cur_max = b.cur_max;
        return result;
    }

    """

from pyopencl.clrandom import rand as clrand
a_gpu = clrand(queue, (20000,), dtype=np.int32, a=0, b=10**6)
a = a_gpu.get()

from pyopencl.reduction import ReductionKernel
red = ReductionKernel(ctx, mmc_dtype,
        neutral="mmc_neutral()",
        reduce_expr="agg_mmc(a, b)", map_expr="mmc_from_scalar(x[i])",
        arguments="__global int *x", preamble=preamble)

minmax = red(a_gpu).get()

assert abs(minmax["cur_min"] - np.min(a)) < 1e-5
assert abs(minmax["cur_max"] - np.max(a)) < 1e-5

########NEW FILE########
__FILENAME__ = demo
import pyopencl as cl
import numpy
import numpy.linalg as la

a = numpy.random.rand(50000).astype(numpy.float32)
b = numpy.random.rand(50000).astype(numpy.float32)

ctx = cl.create_some_context()
queue = cl.CommandQueue(ctx)

mf = cl.mem_flags
a_buf = cl.Buffer(ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=a)
b_buf = cl.Buffer(ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=b)
dest_buf = cl.Buffer(ctx, mf.WRITE_ONLY, b.nbytes)

prg = cl.Program(ctx, """
    __kernel void sum(__global const float *a,
    __global const float *b, __global float *c)
    {
      int gid = get_global_id(0);
      c[gid] = a[gid] + b[gid];
    }
    """).build()

prg.sum(queue, a.shape, None, a_buf, b_buf, dest_buf)

a_plus_b = numpy.empty_like(a)
cl.enqueue_copy(queue, a_plus_b, dest_buf)

print(la.norm(a_plus_b - (a+b)), la.norm(a_plus_b))

########NEW FILE########
__FILENAME__ = demo_array
import pyopencl as cl
import pyopencl.array as cl_array
import numpy
import numpy.linalg as la

a = numpy.random.rand(50000).astype(numpy.float32)
b = numpy.random.rand(50000).astype(numpy.float32)

ctx = cl.create_some_context()
queue = cl.CommandQueue(ctx)

a_dev = cl_array.to_device(queue, a)
b_dev = cl_array.to_device(queue, b)
dest_dev = cl_array.empty_like(a_dev)

prg = cl.Program(ctx, """
    __kernel void sum(__global const float *a,
    __global const float *b, __global float *c)
    {
      int gid = get_global_id(0);
      c[gid] = a[gid] + b[gid];
    }
    """).build()

prg.sum(queue, a.shape, None, a_dev.data, b_dev.data, dest_dev.data)

print(la.norm((dest_dev - (a_dev+b_dev)).get()))

########NEW FILE########
__FILENAME__ = demo_elementwise
import pyopencl as cl
import pyopencl.array as cl_array
import numpy

ctx = cl.create_some_context()
queue = cl.CommandQueue(ctx)

n = 10
a_gpu = cl_array.to_device(
        queue, numpy.random.randn(n).astype(numpy.float32))
b_gpu = cl_array.to_device(
        queue, numpy.random.randn(n).astype(numpy.float32))

from pyopencl.elementwise import ElementwiseKernel
lin_comb = ElementwiseKernel(ctx,
        "float a, float *x, "
        "float b, float *y, "
        "float *z",
        "z[i] = a*x[i] + b*y[i]",
        "linear_combination")

c_gpu = cl_array.empty_like(a_gpu)
lin_comb(5, a_gpu, 6, b_gpu, c_gpu)

import numpy.linalg as la
assert la.norm((c_gpu - (5*a_gpu+6*b_gpu)).get()) < 1e-5

########NEW FILE########
__FILENAME__ = demo_elementwise_complex
import pyopencl as cl
import pyopencl.array as cl_array
import numpy
import numpy.linalg as la

ctx = cl.create_some_context()
queue = cl.CommandQueue(ctx)

n = 10
a_gpu = cl_array.to_device(queue,
        ( numpy.random.randn(n) + 1j*numpy.random.randn(n)
            ).astype(numpy.complex64))
b_gpu = cl_array.to_device(queue,
        ( numpy.random.randn(n) + 1j*numpy.random.randn(n)
            ).astype(numpy.complex64))

from pyopencl.elementwise import ElementwiseKernel
complex_prod = ElementwiseKernel(ctx,
        "float a, "
        "float2 *x, "
        "float2 *y, "
        "float2 *z",
        "z[i] = a * complex_mul(x[i], y[i])",
        "complex_prod",
        preamble="""
        #define complex_ctr(x, y) (float2)(x, y)
        #define complex_mul(a, b) complex_ctr(mad(-(a).y, (b).y, (a).x * (b).x), mad((a).y, (b).x, (a).x * (b).y))
        #define complex_div_scalar(a, b) complex_ctr((a).x / (b), (a).y / (b))
        #define conj(a) complex_ctr((a).x, -(a).y)
        #define conj_transp(a) complex_ctr(-(a).y, (a).x)
        #define conj_transp_and_mul(a, b) complex_ctr(-(a).y * (b), (a).x * (b))
        """)

complex_add = ElementwiseKernel(ctx,
        "float2 *x, "
        "float2 *y, "
        "float2 *z",
        "z[i] = x[i] + y[i]",
        "complex_add")

real_part = ElementwiseKernel(ctx,
        "float2 *x, float *z",
        "z[i] = x[i].x",
        "real_part")

c_gpu = cl_array.empty_like(a_gpu)
complex_prod(5, a_gpu, b_gpu, c_gpu)

c_gpu_real = cl_array.empty(queue, len(a_gpu), dtype=numpy.float32)
real_part(c_gpu, c_gpu_real)
print c_gpu.get().real - c_gpu_real.get()

print la.norm(c_gpu.get() - (5*a_gpu.get()*b_gpu.get()))
assert la.norm(c_gpu.get() - (5*a_gpu.get()*b_gpu.get())) < 1e-5

########NEW FILE########
__FILENAME__ = demo_mandelbrot
# I found this example for PyCuda here:
# http://wiki.tiker.net/PyCuda/Examples/Mandelbrot
#
# An improved sequential/pure Python code was contributed
# by CRVSADER//KY <crusaderky@gmail.com>.
#
# I adapted it for PyOpenCL. Hopefully it is useful to someone.
# July 2010, HolgerRapp@gmx.net
#
# Original readme below these lines.

# Mandelbrot calculate using GPU, Serial numpy and faster numpy
# Use to show the speed difference between CPU and GPU calculations
# ian@ianozsvald.com March 2010

# Based on vegaseat's TKinter/numpy example code from 2006
# http://www.daniweb.com/code/snippet216851.html#
# with minor changes to move to numpy from the obsolete Numeric

import time

import numpy as np

import pyopencl as cl

# You can choose a calculation routine below (calc_fractal), uncomment
# one of the three lines to test the three variations
# Speed notes are listed in the same place

# set width and height of window, more pixels take longer to calculate
w = 2048
h = 2048


def calc_fractal_opencl(q, maxiter):
    ctx = cl.create_some_context()
    queue = cl.CommandQueue(ctx)

    output = np.empty(q.shape, dtype=np.uint16)

    mf = cl.mem_flags
    q_opencl = cl.Buffer(ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=q)
    output_opencl = cl.Buffer(ctx, mf.WRITE_ONLY, output.nbytes)

    prg = cl.Program(ctx, """
    #pragma OPENCL EXTENSION cl_khr_byte_addressable_store : enable
    __kernel void mandelbrot(__global float2 *q,
                     __global ushort *output, ushort const maxiter)
    {
        int gid = get_global_id(0);
        float nreal, real = 0;
        float imag = 0;

        output[gid] = 0;

        for(int curiter = 0; curiter < maxiter; curiter++) {
            nreal = real*real - imag*imag + q[gid].x;
            imag = 2* real*imag + q[gid].y;
            real = nreal;

            if (real*real + imag*imag > 4.0f)
                 output[gid] = curiter;
        }
    }
    """).build()

    prg.mandelbrot(queue, output.shape, None, q_opencl,
                   output_opencl, np.uint16(maxiter))

    cl.enqueue_copy(queue, output, output_opencl).wait()

    return output


def calc_fractal_serial(q, maxiter):
    # calculate z using pure python on a numpy array
    # note that, unlike the other two implementations,
    # the number of iterations per point is NOT constant
    z = np.zeros(q.shape, complex)
    output = np.resize(np.array(0,), q.shape)
    for i in range(len(q)):
        for iter in range(maxiter):
            z[i] = z[i]*z[i] + q[i]
            if abs(z[i]) > 2.0:
                output[i] = iter
                break
    return output


def calc_fractal_numpy(q, maxiter):
    # calculate z using numpy, this is the original
    # routine from vegaseat's URL
    output = np.resize(np.array(0,), q.shape)
    z = np.zeros(q.shape, np.complex64)

    for it in range(maxiter):
        z = z*z + q
        done = np.greater(abs(z), 2.0)
        q = np.where(done, 0+0j, q)
        z = np.where(done, 0+0j, z)
        output = np.where(done, it, output)
    return output

# choose your calculation routine here by uncommenting one of the options
calc_fractal = calc_fractal_opencl
# calc_fractal = calc_fractal_serial
# calc_fractal = calc_fractal_numpy

if __name__ == '__main__':
    try:
        import Tkinter as tk
    except ImportError:
        # Python 3
        import tkinter as tk
    from PIL import Image, ImageTk

    class Mandelbrot(object):
        def __init__(self):
            # create window
            self.root = tk.Tk()
            self.root.title("Mandelbrot Set")
            self.create_image()
            self.create_label()
            # start event loop
            self.root.mainloop()

        def draw(self, x1, x2, y1, y2, maxiter=30):
            # draw the Mandelbrot set, from numpy example
            xx = np.arange(x1, x2, (x2-x1)/w)
            yy = np.arange(y2, y1, (y1-y2)/h) * 1j
            q = np.ravel(xx+yy[:, np.newaxis]).astype(np.complex64)

            start_main = time.time()
            output = calc_fractal(q, maxiter)
            end_main = time.time()

            secs = end_main - start_main
            print("Main took", secs)

            self.mandel = (output.reshape((h, w)) /
                           float(output.max()) * 255.).astype(np.uint8)

        def create_image(self):
            """"
            create the image from the draw() string
            """
            # you can experiment with these x and y ranges
            self.draw(-2.13, 0.77, -1.3, 1.3)
            self.im = Image.fromarray(self.mandel)
            self.im.putpalette([i for rgb in ((j, 0, 0) for j in range(255))
                                for i in rgb])

        def create_label(self):
            # put the image on a label widget
            self.image = ImageTk.PhotoImage(self.im)
            self.label = tk.Label(self.root, image=self.image)
            self.label.pack()

    # test the class
    test = Mandelbrot()

########NEW FILE########
__FILENAME__ = demo_meta_codepy
import pyopencl as cl
import numpy
import numpy.linalg as la

local_size = 256
thread_strides = 32
macroblock_count = 33
dtype = numpy.float32
total_size = local_size*thread_strides*macroblock_count

ctx = cl.create_some_context()
queue = cl.CommandQueue(ctx)

a = numpy.random.randn(total_size).astype(dtype)
b = numpy.random.randn(total_size).astype(dtype)

mf = cl.mem_flags
a_buf = cl.Buffer(ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=a)
b_buf = cl.Buffer(ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=b)
c_buf = cl.Buffer(ctx, mf.WRITE_ONLY, b.nbytes)

from codepy.cgen import FunctionBody, \
        FunctionDeclaration, Typedef, POD, Value, \
        Pointer, Module, Block, Initializer, Assign, Const
from codepy.cgen.opencl import CLKernel, CLGlobal, \
        CLRequiredWorkGroupSize

mod = Module([
    FunctionBody(
        CLKernel(CLRequiredWorkGroupSize((local_size,),
            FunctionDeclaration(
            Value("void", "add"),
            arg_decls=[CLGlobal(Pointer(Const(POD(dtype, name))))
                for name in ["tgt", "op1", "op2"]]))),
        Block([
            Initializer(POD(numpy.int32, "idx"), 
                "get_local_id(0) + %d * get_group_id(0)"
                % (local_size*thread_strides))
            ]+[
            Assign(
                "tgt[idx+%d]" % (o*local_size),
                "op1[idx+%d] + op2[idx+%d]" % (
                    o*local_size, 
                    o*local_size))
            for o in range(thread_strides)]))])

knl = cl.Program(ctx, str(mod)).build().add

knl(queue, (local_size*macroblock_count,), (local_size,),
        c_buf, a_buf, b_buf)

c = numpy.empty_like(a)
cl.enqueue_read_buffer(queue, c_buf, c).wait()

assert la.norm(c-(a+b)) == 0


########NEW FILE########
__FILENAME__ = demo_meta_template
import pyopencl as cl
import numpy
import numpy.linalg as la

local_size = 256
thread_strides = 32
macroblock_count = 33
dtype = numpy.float32
total_size = local_size*thread_strides*macroblock_count

ctx = cl.create_some_context()
queue = cl.CommandQueue(ctx)

a = numpy.random.randn(total_size).astype(dtype)
b = numpy.random.randn(total_size).astype(dtype)

mf = cl.mem_flags
a_buf = cl.Buffer(ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=a)
b_buf = cl.Buffer(ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=b)
c_buf = cl.Buffer(ctx, mf.WRITE_ONLY, b.nbytes)

from mako.template import Template

tpl = Template("""
    __kernel void add(
            __global ${ type_name } *tgt, 
            __global const ${ type_name } *op1, 
            __global const ${ type_name } *op2)
    {
      int idx = get_local_id(0)
        + ${ local_size } * ${ thread_strides }
        * get_group_id(0);

      % for i in range(thread_strides):
          <% offset = i*local_size %>
          tgt[idx + ${ offset }] = 
            op1[idx + ${ offset }] 
            + op2[idx + ${ offset } ];
      % endfor
    }""")

rendered_tpl = tpl.render(type_name="float", 
    local_size=local_size, thread_strides=thread_strides)

knl = cl.Program(ctx, str(rendered_tpl)).build().add

knl(queue, (local_size*macroblock_count,), (local_size,),
        c_buf, a_buf, b_buf)

c = numpy.empty_like(a)
cl.enqueue_read_buffer(queue, c_buf, c).wait()

assert la.norm(c-(a+b)) == 0

########NEW FILE########
__FILENAME__ = download-examples-from-wiki
#! /usr/bin/env python

import xmlrpclib
destwiki = xmlrpclib.ServerProxy("http://wiki.tiker.net?action=xmlrpc2")

import os
try:
    os.mkdir("wiki-examples")
except OSError:
    pass

print "downloading  wiki examples to wiki-examples/..."
print "fetching page list..."
all_pages = destwiki.getAllPages()


from os.path import exists

for page in all_pages:
    if not page.startswith("PyOpenCL/Examples/"):
        continue

    print page
    try:
        content = destwiki.getPage(page)

        import re
        match = re.search(r"\{\{\{\#\!python(.*)\}\}\}", content, re.DOTALL)
        code = match.group(1)

        match = re.search("([^/]+)$", page)
        fname = match.group(1)

        outfname = os.path.join("wiki-examples", fname+".py")
        if exists(outfname):
            print "%s exists, refusing to overwrite." % outfname
        else:
            outf = open(outfname, "w")
            outf.write(code)
            outf.close()

        for att_name in destwiki.listAttachments(page):
            content = destwiki.getAttachment(page, att_name)

            outfname = os.path.join("wiki-examples", att_name)
            if exists(outfname):
                print "%s exists, refusing to overwrite." % outfname
            else:
                outf = open(outfname, "w")
                outf.write(str(content))
                outf.close()

    except Exception, e:
        print "Error when processing %s: %s" % (page, e)
        from traceback import print_exc
        print_exc()

########NEW FILE########
__FILENAME__ = dump-performance
from __future__ import division
import pyopencl as cl
import pyopencl.characterize.performance as perf




def main():
    ctx = cl.create_some_context()

    prof_overhead, latency = perf.get_profiling_overhead(ctx)
    print "command latency: %g s" % latency
    print "profiling overhead: %g s -> %.1f %%" % (
            prof_overhead, 100*prof_overhead/latency)
    queue = cl.CommandQueue(ctx, properties=cl.command_queue_properties.PROFILING_ENABLE)

    print "empty kernel: %g s" % perf.get_empty_kernel_time(queue)
    print "float32 add: %g GOps/s" % (perf.get_add_rate(queue)/1e9)

    for tx_type in [
            perf.HostToDeviceTransfer,
            perf.DeviceToHostTransfer,
            perf.DeviceToDeviceTransfer]:
        print "----------------------------------------"
        print tx_type.__name__
        print "----------------------------------------"

        print "latency: %g s" % perf.transfer_latency(queue, tx_type)
        for i in range(6, 28, 2):
            bs = 1<<i
            print "bandwidth @ %d bytes: %g GB/s" % (
                    bs, perf.transfer_bandwidth(queue, tx_type, bs)/1e9)




if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = dump-properties
import pyopencl as cl
from optparse import OptionParser

parser = OptionParser()
parser.add_option("-s", "--short", action="store_true",
                  help="don't print all device properties")

(options, args) = parser.parse_args()


def print_info(obj, info_cls):
    for info_name in sorted(dir(info_cls)):
        if not info_name.startswith("_") and info_name != "to_string":
            info = getattr(info_cls, info_name)
            try:
                info_value = obj.get_info(info)
            except:
                info_value = "<error>"

            if (info_cls == cl.device_info and info_name == "PARTITION_TYPES_EXT"
                    and isinstance(info_value, list)):
                print("%s: %s" % (info_name, [
                    cl.device_partition_property_ext.to_string(v,
                        "<unknown device partition property %d>")
                    for v in info_value]))
            else:
                try:
                    print("%s: %s" % (info_name, info_value))
                except:
                    print("%s: <error>") % info_name

for platform in cl.get_platforms():
    print(75*"=")
    print(platform)
    print(75*"=")
    if not options.short:
        print_info(platform, cl.platform_info)

    for device in platform.get_devices():
        if not options.short:
            print(75*"-")
        print(device)
        if not options.short:
            print(75*"-")
            print_info(device, cl.device_info)
            ctx = cl.Context([device])
            for mf in [
                    cl.mem_flags.READ_ONLY,
                    #cl.mem_flags.READ_WRITE,
                    #cl.mem_flags.WRITE_ONLY
                    ]:
                for itype in [
                        cl.mem_object_type.IMAGE2D,
                        cl.mem_object_type.IMAGE3D
                        ]:
                    try:
                        formats = cl.get_supported_image_formats(ctx, mf, itype)
                    except:
                        formats = "<error>"
                    else:
                        def str_chd_type(chdtype):
                            result = cl.channel_type.to_string(chdtype,
                                    "<unknown channel data type %d>")

                            result = result.replace("_INT", "")
                            result = result.replace("UNSIGNED", "U")
                            result = result.replace("SIGNED", "S")
                            result = result.replace("NORM", "N")
                            result = result.replace("FLOAT", "F")
                            return result

                        formats = ", ".join(
                                "%s-%s" % (
                                    cl.channel_order.to_string(iform.channel_order,
                                        "<unknown channel order 0x%x>"),
                                    str_chd_type(iform.channel_data_type))
                                for iform in formats)

                    print "%s %s FORMATS: %s\n" % (
                            cl.mem_object_type.to_string(itype),
                            cl.mem_flags.to_string(mf),
                            formats)
            del ctx

########NEW FILE########
__FILENAME__ = gl_interop_demo
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.raw.GL.VERSION.GL_1_5 import glBufferData as rawGlBufferData
import pyopencl as cl


n_vertices = 10000

src = """

__kernel void generate_sin(__global float2* a)
{
    int id = get_global_id(0);
    int n = get_global_size(0);
    float r = (float)id / (float)n;
    float x = r * 16.0f * 3.1415f;
    a[id].x = r * 2.0f - 1.0f;
    a[id].y = native_sin(x);
}

"""

def initialize():
    platform = cl.get_platforms()[0]

    from pyopencl.tools import get_gl_sharing_context_properties
    import sys
    if sys.platform == "darwin":
        ctx = cl.Context(properties=get_gl_sharing_context_properties(),
                devices=[])
    else:
        # Some OSs prefer clCreateContextFromType, some prefer
        # clCreateContext. Try both.
        try:
            ctx = cl.Context(properties=[
                (cl.context_properties.PLATFORM, platform)]
                + get_gl_sharing_context_properties())
        except:
            ctx = cl.Context(properties=[
                (cl.context_properties.PLATFORM, platform)]
                + get_gl_sharing_context_properties(),
                devices = [platform.get_devices()[0]])

    glClearColor(1, 1, 1, 1)
    glColor(0, 0, 1)
    vbo = glGenBuffers(1)
    glBindBuffer(GL_ARRAY_BUFFER, vbo)
    rawGlBufferData(GL_ARRAY_BUFFER, n_vertices * 2 * 4, None, GL_STATIC_DRAW)
    glEnableClientState(GL_VERTEX_ARRAY)
    glVertexPointer(2, GL_FLOAT, 0, None)
    coords_dev = cl.GLBuffer(ctx, cl.mem_flags.READ_WRITE, int(vbo))
    prog = cl.Program(ctx, src).build()
    queue = cl.CommandQueue(ctx)
    cl.enqueue_acquire_gl_objects(queue, [coords_dev])
    prog.generate_sin(queue, (n_vertices,), None, coords_dev)
    cl.enqueue_release_gl_objects(queue, [coords_dev])
    queue.finish()
    glFlush()

def display():
    glClear(GL_COLOR_BUFFER_BIT)
    glDrawArrays(GL_LINE_STRIP, 0, n_vertices)
    glFlush()

def reshape(w, h):
    glViewport(0, 0, w, h)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    glMatrixMode(GL_MODELVIEW)

if __name__ == '__main__':
    import sys
    glutInit(sys.argv)
    if len(sys.argv) > 1:
        n_vertices = int(sys.argv[1])
    glutInitWindowSize(800, 160)
    glutInitWindowPosition(0, 0)
    glutCreateWindow('OpenCL/OpenGL Interop Tutorial: Sin Generator')
    glutDisplayFunc(display)
    glutReshapeFunc(reshape)
    initialize()
    glutMainLoop()

########NEW FILE########
__FILENAME__ = gl_particle_animation
# Visualization of particles with gravity
# Source: http://enja.org/2010/08/27/adventures-in-opencl-part-2-particles-with-opengl/

import pyopencl as cl # OpenCL - GPU computing interface
mf = cl.mem_flags
from pyopencl.tools import get_gl_sharing_context_properties
from OpenGL.GL import * # OpenGL - GPU rendering interface
from OpenGL.GLU import * # OpenGL tools (mipmaps, NURBS, perspective projection, shapes)
from OpenGL.GLUT import * # OpenGL tool to make a visualization window
from OpenGL.arrays import vbo 
import numpy # Number tools
import sys # System tools (path, modules, maxint)

width = 800
height = 600
num_particles = 100000
time_step = .005
mouse_down = False
mouse_old = {'x': 0., 'y': 0.}
rotate = {'x': 0., 'y': 0., 'z': 0.}
translate = {'x': 0., 'y': 0., 'z': 0.}
initial_translate = {'x': 0., 'y': 0., 'z': -2.5}

def glut_window():
    glutInit(sys.argv)
    glutInitDisplayMode(GLUT_RGBA | GLUT_DOUBLE | GLUT_DEPTH)
    glutInitWindowSize(width, height)
    glutInitWindowPosition(0, 0)
    window = glutCreateWindow("Particle Simulation")

    glutDisplayFunc(on_display)  # Called by GLUT every frame
    glutKeyboardFunc(on_key)
    glutMouseFunc(on_click)
    glutMotionFunc(on_mouse_move)
    glutTimerFunc(10, on_timer, 10)  # Call draw every 30 ms

    glViewport(0, 0, width, height)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(60., width / float(height), .1, 1000.)

    return(window)

def initial_buffers(num_particles):
    np_position = numpy.ndarray((num_particles, 4), dtype=numpy.float32)
    np_color = numpy.ndarray((num_particles, 4), dtype=numpy.float32)
    np_velocity = numpy.ndarray((num_particles, 4), dtype=numpy.float32)

    np_position[:,0] = numpy.sin(numpy.arange(0., num_particles) * 2.001 * numpy.pi / num_particles) 
    np_position[:,0] *= numpy.random.random_sample((num_particles,)) / 3. + .2
    np_position[:,1] = numpy.cos(numpy.arange(0., num_particles) * 2.001 * numpy.pi / num_particles) 
    np_position[:,1] *= numpy.random.random_sample((num_particles,)) / 3. + .2
    np_position[:,2] = 0.
    np_position[:,3] = 1.

    np_color[:,:] = [1.,1.,1.,1.] # White particles

    np_velocity[:,0] = np_position[:,0] * 2.
    np_velocity[:,1] = np_position[:,1] * 2.
    np_velocity[:,2] = 3.
    np_velocity[:,3] = numpy.random.random_sample((num_particles, ))
    
    gl_position = vbo.VBO(data=np_position, usage=GL_DYNAMIC_DRAW, target=GL_ARRAY_BUFFER)
    gl_position.bind()
    gl_color = vbo.VBO(data=np_color, usage=GL_DYNAMIC_DRAW, target=GL_ARRAY_BUFFER)
    gl_color.bind()

    return (np_position, np_velocity, gl_position, gl_color)

def on_timer(t):
    glutTimerFunc(t, on_timer, t)
    glutPostRedisplay()

def on_key(*args):
    if args[0] == '\033' or args[0] == 'q':
        sys.exit()

def on_click(button, state, x, y):
    mouse_old['x'] = x
    mouse_old['y'] = y

def on_mouse_move(x, y):
    rotate['x'] += (y - mouse_old['y']) * .2
    rotate['y'] += (x - mouse_old['x']) * .2

    mouse_old['x'] = x
    mouse_old['y'] = y

def on_display():
    """Render the particles"""        
    # Update or particle positions by calling the OpenCL kernel
    cl.enqueue_acquire_gl_objects(queue, [cl_gl_position, cl_gl_color])
    kernelargs = (cl_gl_position, cl_gl_color, cl_velocity, cl_start_position, cl_start_velocity, numpy.float32(time_step))
    program.particle_fountain(queue, (num_particles,), None, *(kernelargs))
    cl.enqueue_release_gl_objects(queue, [cl_gl_position, cl_gl_color])
    queue.finish()
    glFlush()

    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

    # Handle mouse transformations
    glTranslatef(initial_translate['x'], initial_translate['y'], initial_translate['z'])
    glRotatef(rotate['x'], 1, 0, 0)
    glRotatef(rotate['y'], 0, 1, 0) #we switched around the axis so make this rotate_z
    glTranslatef(translate['x'], translate['y'], translate['z'])
    
    # Render the particles
    glEnable(GL_POINT_SMOOTH)
    glPointSize(2)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    # Set up the VBOs
    gl_color.bind()
    glColorPointer(4, GL_FLOAT, 0, gl_color)
    gl_position.bind()
    glVertexPointer(4, GL_FLOAT, 0, gl_position)
    glEnableClientState(GL_VERTEX_ARRAY)
    glEnableClientState(GL_COLOR_ARRAY)

    # Draw the VBOs
    glDrawArrays(GL_POINTS, 0, num_particles)

    glDisableClientState(GL_COLOR_ARRAY)
    glDisableClientState(GL_VERTEX_ARRAY)

    glDisable(GL_BLEND)

    glutSwapBuffers()

window = glut_window()

(np_position, np_velocity, gl_position, gl_color) = initial_buffers(num_particles)

platform = cl.get_platforms()[0]
context = cl.Context(properties=[(cl.context_properties.PLATFORM, platform)] + get_gl_sharing_context_properties())  
queue = cl.CommandQueue(context)

cl_velocity = cl.Buffer(context, mf.COPY_HOST_PTR, hostbuf=np_velocity)
cl_start_position = cl.Buffer(context, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=np_position)
cl_start_velocity = cl.Buffer(context, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=np_velocity)

cl_gl_position = cl.GLBuffer(context, mf.READ_WRITE, int(gl_position.buffers[0]))
cl_gl_color = cl.GLBuffer(context, mf.READ_WRITE, int(gl_color.buffers[0]))

kernel = """__kernel void particle_fountain(__global float4* position, 
                                            __global float4* color, 
                                            __global float4* velocity, 
                                            __global float4* start_position, 
                                            __global float4* start_velocity, 
                                            float time_step)
{
    unsigned int i = get_global_id(0);
    float4 p = position[i];
    float4 v = velocity[i];
    float life = velocity[i].w;
    life -= time_step;
    if (life <= 0.f)
    {
        p = start_position[i];
        v = start_velocity[i];
        life = 1.0f;    
    }

    v.z -= 9.8f*time_step;
    p.x += v.x*time_step;
    p.y += v.y*time_step;
    p.z += v.z*time_step;
    v.w = life;

    position[i] = p;
    velocity[i] = v;

    color[i].w = life; /* Fade points as life decreases */
}"""
program = cl.Program(context, kernel).build()

glutMainLoop()
########NEW FILE########
__FILENAME__ = narray
# example by Roger Pau Monn'e
import pyopencl as cl
import numpy as np

demo_r = np.empty( (500,5), dtype=np.uint32)
ctx = cl.create_some_context()
queue = cl.CommandQueue(ctx)

mf = cl.mem_flags
demo_buf = cl.Buffer(ctx, mf.WRITE_ONLY, demo_r.nbytes)

prg = cl.Program(ctx,
"""
__kernel void demo(__global uint *demo)
{
    int i;
    int gid = get_global_id(0);
    for(i=0; i<5;i++)
    {
        demo[gid*5+i] = (uint) 1;
    }
}""")

try:
    prg.build()
except:
    print("Error:")
    print(prg.get_build_info(ctx.devices[0], cl.program_build_info.LOG))
    raise

prg.demo(queue, (500,), None, demo_buf)
cl.enqueue_read_buffer(queue, demo_buf, demo_r).wait()

for res in demo_r:
    print(res)


########NEW FILE########
__FILENAME__ = transpose
# Transposition of a matrix
# originally for PyCUDA by Hendrik Riedmann <riedmann@dam.brown.edu>

from __future__ import division
import pyopencl as cl
import numpy
import numpy.linalg as la




block_size = 16




class NaiveTranspose:
    def __init__(self, ctx):
        self.kernel = cl.Program(ctx, """
        __kernel
        void transpose(
          __global float *a_t, __global float *a,
          unsigned a_width, unsigned a_height)
        {
          int read_idx = get_global_id(0) + get_global_id(1) * a_width;
          int write_idx = get_global_id(1) + get_global_id(0) * a_height;

          a_t[write_idx] = a[read_idx];
        }
        """% {"block_size": block_size}).build().transpose

    def __call__(self, queue, tgt, src, shape):
        w, h = shape
        assert w % block_size == 0
        assert h % block_size == 0

        return self.kernel(queue, (w, h), (block_size, block_size),
            tgt, src, numpy.uint32(w), numpy.uint32(h))




class SillyTranspose(NaiveTranspose):
    def __call__(self, queue, tgt, src, shape):
        w, h = shape
        assert w % block_size == 0
        assert h % block_size == 0

        return self.kernel(queue, (w, h), None,
            tgt, src, numpy.uint32(w), numpy.uint32(h))




class TransposeWithLocal:
    def __init__(self, ctx):
        self.kernel = cl.Program(ctx, """
        #define BLOCK_SIZE %(block_size)d
        #define A_BLOCK_STRIDE (BLOCK_SIZE * a_width)
        #define A_T_BLOCK_STRIDE (BLOCK_SIZE * a_height)

        __kernel __attribute__((reqd_work_group_size(BLOCK_SIZE, BLOCK_SIZE, 1)))
        void transpose(
          __global float *a_t, __global float *a,
          unsigned a_width, unsigned a_height,
          __local float *a_local)
        {
          int base_idx_a   =
            get_group_id(0) * BLOCK_SIZE +
            get_group_id(1) * A_BLOCK_STRIDE;
          int base_idx_a_t =
            get_group_id(1) * BLOCK_SIZE +
            get_group_id(0) * A_T_BLOCK_STRIDE;

          int glob_idx_a   = base_idx_a + get_local_id(0) + a_width * get_local_id(1);
          int glob_idx_a_t = base_idx_a_t + get_local_id(0) + a_height * get_local_id(1);

          a_local[get_local_id(1)*BLOCK_SIZE+get_local_id(0)] = a[glob_idx_a];

          barrier(CLK_LOCAL_MEM_FENCE);

          a_t[glob_idx_a_t] = a_local[get_local_id(0)*BLOCK_SIZE+get_local_id(1)];
        }
        """% {"block_size": block_size}).build().transpose

    def __call__(self, queue, tgt, src, shape):
        w, h = shape
        assert w % block_size == 0
        assert h % block_size == 0

        return self.kernel(queue, (w, h), (block_size, block_size),
            tgt, src, numpy.uint32(w), numpy.uint32(h),
            cl.LocalMemory(4*block_size*(block_size+1)))




def transpose_using_cl(ctx, queue, cpu_src, cls):
    mf = cl.mem_flags
    a_buf = cl.Buffer(ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=cpu_src)
    a_t_buf = cl.Buffer(ctx, mf.WRITE_ONLY, size=cpu_src.nbytes)
    cls(ctx)(queue, a_t_buf, a_buf, cpu_src.shape)

    w, h = cpu_src.shape
    result = numpy.empty((h, w), dtype=cpu_src.dtype)
    cl.enqueue_read_buffer(queue, a_t_buf, result).wait()

    a_buf.release()
    a_t_buf.release()

    return result





def check_transpose():
    for cls in [NaiveTranspose, SillyTranspose, TransposeWithLocal]:
        print("checking", cls.__name__)
        ctx = cl.create_some_context()

        for dev in ctx.devices:
            assert dev.local_mem_size > 0

        queue = cl.CommandQueue(ctx)

        for i in numpy.arange(10, 13, 0.125):
            size = int(((2**i) // 32) * 32)
            print(size)

            source = numpy.random.rand(size, size).astype(numpy.float32)
            result = transpose_using_cl(ctx, queue, source, NaiveTranspose)

            err = source.T - result
            err_norm = la.norm(err)

            assert err_norm == 0, (size, err_norm)




def benchmark_transpose():
    ctx = cl.create_some_context()

    for dev in ctx.devices:
        assert dev.local_mem_size > 0

    queue = cl.CommandQueue(ctx, 
            properties=cl.command_queue_properties.PROFILING_ENABLE)

    sizes = [int(((2**i) // 32) * 32)
            for i in numpy.arange(10, 13, 0.125)]
            #for i in numpy.arange(10, 10.5, 0.125)]

    mem_bandwidths = {}

    methods = [SillyTranspose, NaiveTranspose, TransposeWithLocal]
    for cls in methods:
        name = cls.__name__.replace("Transpose", "")

        mem_bandwidths[cls] = meth_mem_bws = []

        for size in sizes:

            source = numpy.random.rand(size, size).astype(numpy.float32)

            mf = cl.mem_flags
            a_buf = cl.Buffer(ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=source)
            a_t_buf = cl.Buffer(ctx, mf.WRITE_ONLY, size=source.nbytes)
            method = cls(ctx)

            for i in range(4):
                method(queue, a_t_buf, a_buf, source.shape)

            count = 12
            events = []
            for i in range(count):
                events.append(method(queue, a_t_buf, a_buf, source.shape))

            events[-1].wait()
            time = sum(evt.profile.end - evt.profile.start for evt in events)

            mem_bw = 2*source.nbytes*count/(time*1e-9)
            print("benchmarking", name, size, mem_bw/1e9, "GB/s")
            meth_mem_bws.append(mem_bw)

            a_buf.release()
            a_t_buf.release()

    from matplotlib.pyplot import clf, plot, title, xlabel, ylabel, \
            savefig, legend, grid
    for i in range(len(methods)):
        clf()
        for j in range(i+1):
            method = methods[j]
            name = method.__name__.replace("Transpose", "")
            plot(sizes, numpy.array(mem_bandwidths[method])/1e9, "o-", label=name)

        xlabel("Matrix width/height $N$")
        ylabel("Memory Bandwidth [GB/s]")
        legend(loc="best")
        grid()

        savefig("transpose-benchmark-%d.pdf" % i)






#check_transpose()
benchmark_transpose()


########NEW FILE########
__FILENAME__ = algorithm
"""Scan primitive."""

from __future__ import division

__copyright__ = """Copyright 2011-2012 Andreas Kloeckner"""

__license__ = """
Permission is hereby granted, free of charge, to any person
obtaining a copy of this software and associated documentation
files (the "Software"), to deal in the Software without
restriction, including without limitation the rights to use,
copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following
conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.
"""

import numpy as np
import pyopencl as cl
import pyopencl.array  # noqa
from pyopencl.scan import ScanTemplate
from pyopencl.tools import dtype_to_ctype
from pytools import memoize, memoize_method, Record
from mako.template import Template


# {{{ copy_if

_copy_if_template = ScanTemplate(
        arguments="item_t *ary, item_t *out, scan_t *count",
        input_expr="(%(predicate)s) ? 1 : 0",
        scan_expr="a+b", neutral="0",
        output_statement="""
            if (prev_item != item) out[item-1] = ary[i];
            if (i+1 == N) *count = item;
            """,
        template_processor="printf")


def extract_extra_args_types_values(extra_args):
    from pyopencl.tools import VectorArg, ScalarArg

    extra_args_types = []
    extra_args_values = []
    for name, val in extra_args:
        if isinstance(val, cl.array.Array):
            extra_args_types.append(VectorArg(val.dtype, name, with_offset=False))
            extra_args_values.append(val)
        elif isinstance(val, np.generic):
            extra_args_types.append(ScalarArg(val.dtype, name))
            extra_args_values.append(val)
        else:
            raise RuntimeError("argument '%d' not understood" % name)

    return tuple(extra_args_types), extra_args_values


def copy_if(ary, predicate, extra_args=[], preamble="", queue=None, wait_for=None):
    """Copy the elements of *ary* satisfying *predicate* to an output array.

    :arg predicate: a C expression evaluating to a `bool`, represented as a string.
        The value to test is available as `ary[i]`, and if the expression evaluates
        to `true`, then this value ends up in the output.
    :arg extra_args: |scan_extra_args|
    :arg preamble: |preamble|
    :arg wait_for: |explain-waitfor|
    :returns: a tuple *(out, count, event)* where *out* is the output array, *count*
        is an on-device scalar (fetch to host with `count.get()`) indicating
        how many elements satisfied *predicate*, and *event* is a
        :class:`pyopencl.Event` for dependency management. *out* is allocated
        to the same length as *ary*, but only the first *count* entries carry
        meaning.

    .. versionadded:: 2013.1
    """
    if len(ary) > np.iinfo(np.int32).max:
        scan_dtype = np.int64
    else:
        scan_dtype = np.int32

    extra_args_types, extra_args_values = extract_extra_args_types_values(extra_args)

    knl = _copy_if_template.build(ary.context,
            type_aliases=(("scan_t", scan_dtype), ("item_t", ary.dtype)),
            var_values=(("predicate", predicate),),
            more_preamble=preamble, more_arguments=extra_args_types)
    out = cl.array.empty_like(ary)
    count = ary._new_with_changes(data=None, offset=0,
            shape=(), strides=(), dtype=scan_dtype)

    # **dict is a Py2.5 workaround
    evt = knl(ary, out, count, *extra_args_values,
            **dict(queue=queue, wait_for=wait_for))

    return out, count, evt

# }}}


# {{{ remove_if

def remove_if(ary, predicate, extra_args=[], preamble="", queue=None, wait_for=None):
    """Copy the elements of *ary* not satisfying *predicate* to an output array.

    :arg predicate: a C expression evaluating to a `bool`, represented as a string.
        The value to test is available as `ary[i]`, and if the expression evaluates
        to `false`, then this value ends up in the output.
    :arg extra_args: |scan_extra_args|
    :arg preamble: |preamble|
    :arg wait_for: |explain-waitfor|
    :returns: a tuple *(out, count, event)* where *out* is the output array, *count*
        is an on-device scalar (fetch to host with `count.get()`) indicating
        how many elements did not satisfy *predicate*, and *event* is a
        :class:`pyopencl.Event` for dependency management.

    .. versionadded:: 2013.1
    """
    return copy_if(ary, "!(%s)" % predicate, extra_args=extra_args,
            preamble=preamble, queue=queue, wait_for=wait_for)

# }}}


# {{{ partition

_partition_template = ScanTemplate(
        arguments=(
            "item_t *ary, item_t *out_true, item_t *out_false, "
            "scan_t *count_true"),
        input_expr="(%(predicate)s) ? 1 : 0",
        scan_expr="a+b", neutral="0",
        output_statement="""//CL//
                if (prev_item != item)
                    out_true[item-1] = ary[i];
                else
                    out_false[i-item] = ary[i];
                if (i+1 == N) *count_true = item;
                """,
        template_processor="printf")


def partition(ary, predicate, extra_args=[], preamble="", queue=None, wait_for=None):
    """Copy the elements of *ary* into one of two arrays depending on whether
    they satisfy *predicate*.

    :arg predicate: a C expression evaluating to a `bool`, represented as a string.
        The value to test is available as `ary[i]`.
    :arg extra_args: |scan_extra_args|
    :arg preamble: |preamble|
    :arg wait_for: |explain-waitfor|
    :returns: a tuple *(out_true, out_false, count, event)* where *count*
        is an on-device scalar (fetch to host with `count.get()`) indicating
        how many elements satisfied the predicate, and *event* is a
        :class:`pyopencl.Event` for dependency management.

    .. versionadded:: 2013.1
    """
    if len(ary) > np.iinfo(np.uint32).max:
        scan_dtype = np.uint64
    else:
        scan_dtype = np.uint32

    extra_args_types, extra_args_values = extract_extra_args_types_values(extra_args)

    knl = _partition_template.build(
            ary.context,
            type_aliases=(("item_t", ary.dtype), ("scan_t", scan_dtype)),
            var_values=(("predicate", predicate),),
            more_preamble=preamble, more_arguments=extra_args_types)

    out_true = cl.array.empty_like(ary)
    out_false = cl.array.empty_like(ary)
    count = ary._new_with_changes(data=None, offset=0,
            shape=(), strides=(), dtype=scan_dtype)

    # **dict is a Py2.5 workaround
    evt = knl(ary, out_true, out_false, count, *extra_args_values,
            **dict(queue=queue, wait_for=wait_for))

    return out_true, out_false, count, evt

# }}}


# {{{ unique

_unique_template = ScanTemplate(
        arguments="item_t *ary, item_t *out, scan_t *count_unique",
        input_fetch_exprs=[
            ("ary_im1", "ary", -1),
            ("ary_i", "ary", 0),
            ],
        input_expr="(i == 0) || (IS_EQUAL_EXPR(ary_im1, ary_i) ? 0 : 1)",
        scan_expr="a+b", neutral="0",
        output_statement="""
                if (prev_item != item) out[item-1] = ary[i];
                if (i+1 == N) *count_unique = item;
                """,
        preamble="#define IS_EQUAL_EXPR(a, b) %(macro_is_equal_expr)s\n",
        template_processor="printf")


def unique(ary, is_equal_expr="a == b", extra_args=[], preamble="",
        queue=None, wait_for=None):
    """Copy the elements of *ary* into the output if *is_equal_expr*, applied to the
    array element and its predecessor, yields false.

    Works like the UNIX command :program:`uniq`, with a potentially custom
    comparison.  This operation is often used on sorted sequences.

    :arg is_equal_expr: a C expression evaluating to a `bool`,
        represented as a string.  The elements being compared are
        available as `a` and `b`. If this expression yields `false`, the
        two are considered distinct.
    :arg extra_args: |scan_extra_args|
    :arg preamble: |preamble|
    :arg wait_for: |explain-waitfor|
    :returns: a tuple *(out, count, event)* where *out* is the output array, *count*
        is an on-device scalar (fetch to host with `count.get()`) indicating
        how many elements satisfied the predicate, and *event* is a
        :class:`pyopencl.Event` for dependency management.

    .. versionadded:: 2013.1
    """

    if len(ary) > np.iinfo(np.uint32).max:
        scan_dtype = np.uint64
    else:
        scan_dtype = np.uint32

    extra_args_types, extra_args_values = extract_extra_args_types_values(extra_args)

    knl = _unique_template.build(
            ary.context,
            type_aliases=(("item_t", ary.dtype), ("scan_t", scan_dtype)),
            var_values=(("macro_is_equal_expr", is_equal_expr),),
            more_preamble=preamble, more_arguments=extra_args_types)

    out = cl.array.empty_like(ary)
    count = ary._new_with_changes(data=None, offset=0,
            shape=(), strides=(), dtype=scan_dtype)

    # **dict is a Py2.5 workaround
    evt = knl(ary, out, count, *extra_args_values,
            **dict(queue=queue, wait_for=wait_for))

    return out, count, evt

# }}}


# {{{ radix_sort

def to_bin(n):
    # Py 2.5 has no built-in bin()
    digs = []
    while n:
        digs.append(str(n % 2))
        n >>= 1

    return ''.join(digs[::-1])


def _padded_bin(i, l):
    s = to_bin(i)
    while len(s) < l:
        s = '0' + s
    return s


@memoize
def _make_sort_scan_type(device, bits, index_dtype):
    name = "pyopencl_sort_scan_%s_%dbits_t" % (
            index_dtype.type.__name__, bits)

    fields = []
    for mnr in range(2**bits):
        fields.append(('c%s' % _padded_bin(mnr, bits), index_dtype))

    dtype = np.dtype(fields)

    from pyopencl.tools import get_or_register_dtype, match_dtype_to_c_struct
    dtype, c_decl = match_dtype_to_c_struct(device, name, dtype)

    dtype = get_or_register_dtype(name, dtype)
    return name, dtype, c_decl

# {{{ types, helpers preamble

RADIX_SORT_PREAMBLE_TPL = Template(r"""//CL//
    typedef ${scan_ctype} scan_t;
    typedef ${key_ctype} key_t;
    typedef ${index_ctype} index_t;

    // #define DEBUG
    #ifdef DEBUG
        #define dbg_printf(ARGS) printf ARGS
    #else
        #define dbg_printf(ARGS) /* */
    #endif

    index_t get_count(scan_t s, int mnr)
    {
        return ${get_count_branch("")};
    }

    #define BIN_NR(key_arg) ((key_arg >> base_bit) & ${2**bits - 1})

""", strict_undefined=True)

# }}}

# {{{ scan helpers

RADIX_SORT_SCAN_PREAMBLE_TPL = Template(r"""//CL//
    scan_t scan_t_neutral()
    {
        scan_t result;
        %for mnr in range(2**bits):
            result.c${padded_bin(mnr, bits)} = 0;
        %endfor
        return result;
    }

    // considers bits (base_bit+bits-1, ..., base_bit)
    scan_t scan_t_from_value(
        key_t key,
        int base_bit,
        int i
    )
    {
        // extract relevant bit range
        key_t bin_nr = BIN_NR(key);

        dbg_printf(("i: %d key:%d bin_nr:%d\n", i, key, bin_nr));

        scan_t result;
        %for mnr in range(2**bits):
            result.c${padded_bin(mnr, bits)} = (bin_nr == ${mnr});
        %endfor

        return result;
    }

    scan_t scan_t_add(scan_t a, scan_t b, bool across_seg_boundary)
    {
        %for mnr in range(2**bits):
            <% field = "c"+padded_bin(mnr, bits) %>
            b.${field} = a.${field} + b.${field};
        %endfor

        return b;
    }
""", strict_undefined=True)

RADIX_SORT_OUTPUT_STMT_TPL = Template(r"""//CL//
    {
        key_t key = ${key_expr};
        key_t my_bin_nr = BIN_NR(key);

        index_t previous_bins_size = 0;
        %for mnr in range(2**bits):
            previous_bins_size +=
                (my_bin_nr > ${mnr})
                    ? last_item.c${padded_bin(mnr, bits)}
                    : 0;
        %endfor

        index_t tgt_idx =
            previous_bins_size
            + get_count(item, my_bin_nr) - 1;

        %for arg_name in sort_arg_names:
            sorted_${arg_name}[tgt_idx] = ${arg_name}[i];
        %endfor
    }
""", strict_undefined=True)

# }}}


# {{{ driver

class RadixSort(object):
    """Provides a general `radix sort <https://en.wikipedia.org/wiki/Radix_sort>`_
    on the compute device.

    .. versionadded:: 2013.1
    """
    def __init__(self, context, arguments, key_expr, sort_arg_names,
            bits_at_a_time=2, index_dtype=np.int32, key_dtype=np.uint32,
            options=[]):
        """
        :arg arguments: A string of comma-separated C argument declarations.
            If *arguments* is specified, then *input_expr* must also be
            specified. All types used here must be known to PyOpenCL.
            (see :func:`pyopencl.tools.get_or_register_dtype`).
        :arg key_expr: An integer-valued C expression returning the
            key based on which the sort is performed. The array index
            for which the key is to be computed is available as `i`.
            The expression may refer to any of the *arguments*.
        :arg sort_arg_names: A list of argument names whose corresponding
            array arguments will be sorted according to *key_expr*.
        """

        # {{{ arg processing

        from pyopencl.tools import parse_arg_list
        self.arguments = parse_arg_list(arguments)
        del arguments

        self.sort_arg_names = sort_arg_names
        self.bits = int(bits_at_a_time)
        self.index_dtype = np.dtype(index_dtype)
        self.key_dtype = np.dtype(key_dtype)

        self.options = options

        # }}}

        # {{{ kernel creation

        scan_ctype, scan_dtype, scan_t_cdecl = \
                _make_sort_scan_type(context.devices[0], self.bits, self.index_dtype)

        from pyopencl.tools import VectorArg, ScalarArg
        scan_arguments = (
                list(self.arguments)
                + [VectorArg(arg.dtype, "sorted_"+arg.name) for arg in self.arguments
                    if arg.name in sort_arg_names]
                + [ScalarArg(np.int32, "base_bit")])

        def get_count_branch(known_bits):
            if len(known_bits) == self.bits:
                return "s.c%s" % known_bits

            boundary_mnr = known_bits + "1" + (self.bits-len(known_bits)-1)*"0"

            return ("((mnr < %s) ? %s : %s)" % (
                int(boundary_mnr, 2),
                get_count_branch(known_bits+"0"),
                get_count_branch(known_bits+"1")))

        codegen_args = dict(
                bits=self.bits,
                key_ctype=dtype_to_ctype(self.key_dtype),
                key_expr=key_expr,
                index_ctype=dtype_to_ctype(self.index_dtype),
                index_type_max=np.iinfo(self.index_dtype).max,
                padded_bin=_padded_bin,
                scan_ctype=scan_ctype,
                sort_arg_names=sort_arg_names,
                get_count_branch=get_count_branch,
                )

        preamble = scan_t_cdecl+RADIX_SORT_PREAMBLE_TPL.render(**codegen_args)
        scan_preamble = preamble \
                + RADIX_SORT_SCAN_PREAMBLE_TPL.render(**codegen_args)

        from pyopencl.scan import GenericScanKernel
        self.scan_kernel = GenericScanKernel(
                context, scan_dtype,
                arguments=scan_arguments,
                input_expr="scan_t_from_value(%s, base_bit, i)" % key_expr,
                scan_expr="scan_t_add(a, b, across_seg_boundary)",
                neutral="scan_t_neutral()",
                output_statement=RADIX_SORT_OUTPUT_STMT_TPL.render(**codegen_args),
                preamble=scan_preamble, options=self.options)

        for i, arg in enumerate(self.arguments):
            if isinstance(arg, VectorArg):
                self.first_array_arg_idx = i

        # }}}

    def __call__(self, *args, **kwargs):
        """Run the radix sort. In addition to *args* which must match the
        *arguments* specification on the constructor, the following
        keyword arguments are supported:

        :arg key_bits: specify how many bits (starting from least-significant)
            there are in the key.
        :arg allocator: See the *allocator* argument of :func:`pyopencl.array.empty`.
        :arg queue: A :class:`pyopencl.CommandQueue`, defaulting to the
            one from the first argument array.
        :arg wait_for: |explain-waitfor|
        :returns: A tuple ``(sorted, event)``. *sorted* consists of sorted
            copies of the arrays named in *sorted_args*, in the order of that
            list. *event* is a :class:`pyopencl.Event` for dependency management.
        """

        wait_for = kwargs.pop("wait_for", None)

        # {{{ run control

        key_bits = kwargs.pop("key_bits", None)
        if key_bits is None:
            key_bits = int(np.iinfo(self.key_dtype).bits)

        n = len(args[self.first_array_arg_idx])

        allocator = kwargs.pop("allocator", None)
        if allocator is None:
            allocator = args[self.first_array_arg_idx].allocator

        queue = kwargs.pop("allocator", None)
        if queue is None:
            queue = args[self.first_array_arg_idx].queue

        args = list(args)

        base_bit = 0
        while base_bit < key_bits:
            sorted_args = [
                    cl.array.empty(queue, n, arg_descr.dtype, allocator=allocator)
                    for arg_descr in self.arguments
                    if arg_descr.name in self.sort_arg_names]

            scan_args = args + sorted_args + [base_bit]

            last_evt = self.scan_kernel(*scan_args,
                    **dict(queue=queue, wait_for=wait_for))
            wait_for = [last_evt]

            # substitute sorted
            for i, arg_descr in enumerate(self.arguments):
                if arg_descr.name in self.sort_arg_names:
                    args[i] = sorted_args[self.sort_arg_names.index(arg_descr.name)]

            base_bit += self.bits

        return [arg_val
                for arg_descr, arg_val in zip(self.arguments, args)
                if arg_descr.name in self.sort_arg_names], last_evt

        # }}}

# }}}

# }}}


# {{{ generic parallel list builder

# {{{ kernel template

_LIST_BUILDER_TEMPLATE = Template("""//CL//
% if double_support:
    #pragma OPENCL EXTENSION cl_khr_fp64: enable
    #define PYOPENCL_DEFINE_CDOUBLE
% endif

#include <pyopencl-complex.h>

${preamble}

// {{{ declare helper macros for user interface

typedef ${index_type} index_type;

%if is_count_stage:
    #define PLB_COUNT_STAGE

    %for name, dtype in list_names_and_dtypes:
        %if name in count_sharing:
            #define APPEND_${name}(value) { /* nothing */ }
        %else:
            #define APPEND_${name}(value) { ++(*plb_loc_${name}_count); }
        %endif
    %endfor
%else:
    #define PLB_WRITE_STAGE

    %for name, dtype in list_names_and_dtypes:
        %if name in count_sharing:
            #define APPEND_${name}(value) \
                { plb_${name}_list[(*plb_${count_sharing[name]}_index) - 1] \
                    = value; }
        %else:
            #define APPEND_${name}(value) \
                { plb_${name}_list[(*plb_${name}_index)++] = value; }
        %endif
    %endfor
%endif

#define LIST_ARG_DECL ${user_list_arg_decl}
#define LIST_ARGS ${user_list_args}
#define USER_ARG_DECL ${user_arg_decl}
#define USER_ARGS ${user_args}

// }}}

${generate_template}

// {{{ kernel entry point

__kernel
%if do_not_vectorize:
__attribute__((reqd_work_group_size(1, 1, 1)))
%endif
void ${kernel_name}(${kernel_list_arg_decl} USER_ARG_DECL index_type n)

{
    %if not do_not_vectorize:
        int lid = get_local_id(0);
        index_type gsize = get_global_size(0);
        index_type work_group_start = get_local_size(0)*get_group_id(0);
        for (index_type i = work_group_start + lid; i < n; i += gsize)
    %else:
        const int chunk_size = 128;
        index_type chunk_base = get_global_id(0)*chunk_size;
        index_type gsize = get_global_size(0);
        for (; chunk_base < n; chunk_base += gsize*chunk_size)
        for (index_type i = chunk_base; i < min(n, chunk_base+chunk_size); ++i)
    %endif
    {
        %if is_count_stage:
            %for name, dtype in list_names_and_dtypes:
                %if name not in count_sharing:
                    index_type plb_loc_${name}_count = 0;
                %endif
            %endfor
        %else:
            %for name, dtype in list_names_and_dtypes:
                %if name not in count_sharing:
                    index_type plb_${name}_index =
                        plb_${name}_start_index[i];
                %endif
            %endfor
        %endif

        generate(${kernel_list_arg_values} USER_ARGS i);

        %if is_count_stage:
            %for name, dtype in list_names_and_dtypes:
                %if name not in count_sharing:
                    plb_${name}_count[i] = plb_loc_${name}_count;
                %endif
            %endfor
        %endif
    }
}

// }}}

""", strict_undefined=True)

# }}}


def _get_arg_decl(arg_list):
    result = ""
    for arg in arg_list:
        result += arg.declarator() + ", "

    return result


def _get_arg_list(arg_list, prefix=""):
    result = ""
    for arg in arg_list:
        result += prefix + arg.name + ", "

    return result


class BuiltList(Record):
    pass


class ListOfListsBuilder:
    """Generates and executes code to produce a large number of variable-size
    lists, simply.

    .. note:: This functionality is provided as a preview. Its interface
        is subject to change until this notice is removed.

    .. versionadded:: 2013.1

    Here's a usage example::

        from pyopencl.algorithm import ListOfListsBuilder
        builder = ListOfListsBuilder(context, [("mylist", np.int32)], \"\"\"
                void generate(LIST_ARG_DECL USER_ARG_DECL index_type i)
                {
                    int count = i % 4;
                    for (int j = 0; j < count; ++j)
                    {
                        APPEND_mylist(count);
                    }
                }
                \"\"\", arg_decls=[])

        result, event = builder(queue, 2000)

        inf = result["mylist"]
        assert inf.count == 3000
        assert (inf.list.get()[-6:] == [1, 2, 2, 3, 3, 3]).all()

    The function `generate` above is called once for each "input object".
    Each input object can then generate zero or more list entries.
    The number of these input objects is given to :meth:`__call__` as *n_objects*.
    List entries are generated by calls to `APPEND_<list name>(value)`.
    Multiple lists may be generated at once.

    """
    def __init__(self, context, list_names_and_dtypes, generate_template,
            arg_decls, count_sharing=None, devices=None,
            name_prefix="plb_build_list", options=[], preamble="",
            debug=False, complex_kernel=False):
        """
        :arg context: A :class:`pyopencl.Context`.
        :arg list_names_and_dtypes: a list of `(name, dtype)` tuples
            indicating the lists to be built.
        :arg generate_template: a snippet of C as described below
        :arg arg_decls: A string of comma-separated C argument declarations.
        :arg count_sharing: A mapping consisting of `(child, mother)`
            indicating that `mother` and `child` will always have the
            same number of indices, and the `APPEND` to `mother`
            will always happen *before* the `APPEND` to the child.
        :arg name_prefix: the name prefix to use for the compiled kernels
        :arg options: OpenCL compilation options for kernels using
            *generate_template*.
        :arg complex_kernel: If `True`, prevents vectorization on CPUs.

        *generate_template* may use the following C macros/identifiers:

        * `index_type`: expands to C identifier for the index type used
          for the calculation
        * `USER_ARG_DECL`: expands to the C declarator for `arg_decls`
        * `USER_ARGS`: a list of C argument values corresponding to
          `user_arg_decl`
        * `LIST_ARG_DECL`: expands to a C argument list representing the
          data for the output lists. These are escaped prefixed with
          `"plg_"` so as to not interfere with user-provided names.
        * `LIST_ARGS`: a list of C argument values corresponding to
          `LIST_ARG_DECL`
        * `APPEND_name(entry)`: inserts `entry` into the list `name`.
          *entry* must be a valid C expression of the correct type.

        All argument-list related macros have a trailing comma included
        if they are non-empty.

        *generate_template* must supply a function:

        .. code-block:: c

            void generate(USER_ARG_DECL LIST_ARG_DECL index_type i)
            {
                APPEND_mylist(5);
            }

        Internally, the `kernel_template` is expanded (at least) twice. Once,
        for a 'counting' stage where the size of all the lists is determined,
        and a second time, for a 'generation' stage where the lists are
        actually filled. A `generate` function that has side effects beyond
        calling `append` is therefore ill-formed.
        """

        if devices is None:
            devices = context.devices

        if count_sharing is None:
            count_sharing = {}

        self.context = context
        self.devices = devices

        self.list_names_and_dtypes = list_names_and_dtypes
        self.generate_template = generate_template

        from pyopencl.tools import parse_arg_list
        self.arg_decls = parse_arg_list(arg_decls)

        self.count_sharing = count_sharing

        self.name_prefix = name_prefix
        self.preamble = preamble
        self.options = options

        self.debug = debug

        self.complex_kernel = complex_kernel

    # {{{ kernel generators

    @memoize_method
    def get_scan_kernel(self, index_dtype):
        from pyopencl.scan import GenericScanKernel
        return GenericScanKernel(
                self.context, index_dtype,
                arguments="__global %s *ary" % dtype_to_ctype(index_dtype),
                input_expr="ary[i]",
                scan_expr="a+b", neutral="0",
                output_statement="ary[i+1] = item;",
                devices=self.devices)

    def do_not_vectorize(self):
        from pytools import any
        return (self.complex_kernel
                and any(dev.type & cl.device_type.CPU
                    for dev in self.context.devices))

    @memoize_method
    def get_count_kernel(self, index_dtype):
        index_ctype = dtype_to_ctype(index_dtype)
        from pyopencl.tools import VectorArg, OtherArg
        kernel_list_args = [
                VectorArg(index_dtype, "plb_%s_count" % name)
                    for name, dtype in self.list_names_and_dtypes
                    if name not in self.count_sharing]

        user_list_args = []
        for name, dtype in self.list_names_and_dtypes:
            if name in self.count_sharing:
                continue

            name = "plb_loc_%s_count" % name
            user_list_args.append(OtherArg("%s *%s" % (
                index_ctype, name), name))

        kernel_name = self.name_prefix+"_count"

        from pyopencl.characterize import has_double_support
        src = _LIST_BUILDER_TEMPLATE.render(
                is_count_stage=True,
                kernel_name=kernel_name,
                double_support=all(has_double_support(dev) for dev in
                    self.context.devices),
                debug=self.debug,
                do_not_vectorize=self.do_not_vectorize(),

                kernel_list_arg_decl=_get_arg_decl(kernel_list_args),
                kernel_list_arg_values=_get_arg_list(user_list_args, prefix="&"),
                user_list_arg_decl=_get_arg_decl(user_list_args),
                user_list_args=_get_arg_list(user_list_args),
                user_arg_decl=_get_arg_decl(self.arg_decls),
                user_args=_get_arg_list(self.arg_decls),

                list_names_and_dtypes=self.list_names_and_dtypes,
                count_sharing=self.count_sharing,
                name_prefix=self.name_prefix,
                generate_template=self.generate_template,
                preamble=self.preamble,

                index_type=index_ctype,
                )

        src = str(src)

        prg = cl.Program(self.context, src).build(self.options)
        knl = getattr(prg, kernel_name)

        from pyopencl.tools import get_arg_list_scalar_arg_dtypes
        knl.set_scalar_arg_dtypes(get_arg_list_scalar_arg_dtypes(
            kernel_list_args+self.arg_decls) + [index_dtype])

        return knl

    @memoize_method
    def get_write_kernel(self, index_dtype):
        index_ctype = dtype_to_ctype(index_dtype)
        from pyopencl.tools import VectorArg, OtherArg
        kernel_list_args = []
        kernel_list_arg_values = ""
        user_list_args = []

        for name, dtype in self.list_names_and_dtypes:
            list_name = "plb_%s_list" % name
            list_arg = VectorArg(dtype, list_name)

            kernel_list_args.append(list_arg)
            user_list_args.append(list_arg)

            if name in self.count_sharing:
                kernel_list_arg_values += "%s, " % list_name
                continue

            kernel_list_args.append(
                    VectorArg(index_dtype, "plb_%s_start_index" % name))

            index_name = "plb_%s_index" % name
            user_list_args.append(OtherArg("%s *%s" % (
                index_ctype, index_name), index_name))

            kernel_list_arg_values += "%s, &%s, " % (list_name, index_name)

        kernel_name = self.name_prefix+"_write"

        from pyopencl.characterize import has_double_support
        src = _LIST_BUILDER_TEMPLATE.render(
                is_count_stage=False,
                kernel_name=kernel_name,
                double_support=all(has_double_support(dev) for dev in
                    self.context.devices),
                debug=self.debug,
                do_not_vectorize=self.do_not_vectorize(),

                kernel_list_arg_decl=_get_arg_decl(kernel_list_args),
                kernel_list_arg_values=kernel_list_arg_values,
                user_list_arg_decl=_get_arg_decl(user_list_args),
                user_list_args=_get_arg_list(user_list_args),
                user_arg_decl=_get_arg_decl(self.arg_decls),
                user_args=_get_arg_list(self.arg_decls),

                list_names_and_dtypes=self.list_names_and_dtypes,
                count_sharing=self.count_sharing,
                name_prefix=self.name_prefix,
                generate_template=self.generate_template,
                preamble=self.preamble,

                index_type=index_ctype,
                )

        src = str(src)

        prg = cl.Program(self.context, src).build(self.options)
        knl = getattr(prg, kernel_name)

        from pyopencl.tools import get_arg_list_scalar_arg_dtypes
        knl.set_scalar_arg_dtypes(get_arg_list_scalar_arg_dtypes(
            kernel_list_args+self.arg_decls) + [index_dtype])

        return knl

    # }}}

    # {{{ driver

    def __call__(self, queue, n_objects, *args, **kwargs):
        """
        :arg args: arguments corresponding to arg_decls in the constructor.
            :class:`pyopencl.array.Array` are not allowed directly and should
            be passed as their :attr:`pyopencl.array.Array.data` attribute instead.
        :arg allocator: optionally, the allocator to use to allocate new
            arrays.
        :arg wait_for: |explain-waitfor|
        :returns: a tuple ``(lists, event)``, where
            *lists* a mapping from (built) list names to objects which
            have attributes

            * ``count`` for the total number of entries in all lists combined
            * ``lists`` for the array containing all lists.
            * ``starts`` for the array of starting indices in `lists`.
              `starts` is built so that it has n+1 entries, so that
              the *i*'th entry is the start of the *i*'th list, and the
              *i*'th entry is the index one past the *i*'th list's end,
              even for the last list.

              This implies that all lists are contiguous.

              *event* is a :class:`pyopencl.Event` for dependency management.
        """
        if n_objects >= int(np.iinfo(np.int32).max):
            index_dtype = np.int64
        else:
            index_dtype = np.int32
        index_dtype = np.dtype(index_dtype)

        allocator = kwargs.pop("allocator", None)
        wait_for = kwargs.pop("wait_for", None)
        if kwargs:
            raise TypeError("invalid keyword arguments: '%s'" % ", ".join(kwargs))

        result = {}
        count_list_args = []

        if wait_for is None:
            wait_for = []

        count_kernel = self.get_count_kernel(index_dtype)
        write_kernel = self.get_write_kernel(index_dtype)
        scan_kernel = self.get_scan_kernel(index_dtype)

        # {{{ allocate memory for counts

        for name, dtype in self.list_names_and_dtypes:
            if name in self.count_sharing:
                continue

            counts = cl.array.empty(queue,
                    (n_objects + 1), index_dtype, allocator=allocator)
            counts[-1] = 0
            wait_for = wait_for + counts.events

            # The scan will turn the "counts" array into the "starts" array
            # in-place.
            result[name] = BuiltList(starts=counts)
            count_list_args.append(counts.data)

        # }}}

        if self.debug:
            gsize = (1,)
            lsize = (1,)
        elif self.complex_kernel and queue.device.type == cl.device_type.CPU:
            gsize = (4*queue.device.max_compute_units,)
            lsize = (1,)
        else:
            from pyopencl.array import splay
            gsize, lsize = splay(queue, n_objects)

        count_event = count_kernel(queue, gsize, lsize,
                *(tuple(count_list_args) + args + (n_objects,)),
                **dict(wait_for=wait_for))

        # {{{ run scans

        scan_events = []

        for name, dtype in self.list_names_and_dtypes:
            if name in self.count_sharing:
                continue

            info_record = result[name]
            starts_ary = info_record.starts
            evt = scan_kernel(starts_ary, wait_for=[count_event],
                    size=n_objects)

            starts_ary.setitem(0, 0, queue=queue, wait_for=[evt])
            scan_events.extend(starts_ary.events)

            # retrieve count
            info_record.count = int(starts_ary[-1].get())

        # }}}

        # {{{ deal with count-sharing lists, allocate memory for lists

        write_list_args = []
        for name, dtype in self.list_names_and_dtypes:
            if name in self.count_sharing:
                sharing_from = self.count_sharing[name]

                info_record = result[name] = BuiltList(
                        count=result[sharing_from].count,
                        starts=result[sharing_from].starts,
                        )

            else:
                info_record = result[name]

            info_record.lists = cl.array.empty(queue,
                    info_record.count, dtype, allocator=allocator)
            write_list_args.append(info_record.lists.data)

            if name not in self.count_sharing:
                write_list_args.append(info_record.starts.data)

        # }}}

        evt = write_kernel(queue, gsize, lsize,
                *(tuple(write_list_args) + args + (n_objects,)),
                **dict(wait_for=scan_events))

        return result, evt

    # }}}

# }}}


# {{{ key-value sorting

class _KernelInfo(Record):
    pass


def _make_cl_int_literal(value, dtype):
    iinfo = np.iinfo(dtype)
    result = str(int(value))
    if dtype.itemsize == 8:
        result += "l"
    if int(iinfo.min) < 0:
        result += "u"

    return result


class KeyValueSorter(object):
    """Given arrays *values* and *keys* of equal length
    and a number *nkeys* of keys, returns a tuple `(starts,
    lists)`, as follows: *values* and *keys* are sorted
    by *keys*, and the sorted *values* is returned as
    *lists*. Then for each index *i* in `range(nkeys)`,
    *starts[i]* is written to indicating where the
    group of *values* belonging to the key with index
    *i* begins. It implicitly ends at *starts[i+1]*.

    `starts` is built so that it has `nkeys+1` entries, so that
    the *i*'th entry is the start of the *i*'th list, and the
    *i*'th entry is the index one past the *i*'th list's end,
    even for the last list.

    This implies that all lists are contiguous.

    .. note:: This functionality is provided as a preview. Its
        interface is subject to change until this notice is removed.

    .. versionadded:: 2013.1
    """

    def __init__(self, context):
        self.context = context

    @memoize_method
    def get_kernels(self, key_dtype, value_dtype, starts_dtype):
        from pyopencl.algorithm import RadixSort
        from pyopencl.tools import VectorArg, ScalarArg

        by_target_sorter = RadixSort(
                self.context, [
                    VectorArg(value_dtype, "values"),
                    VectorArg(key_dtype, "keys"),
                    ],
                key_expr="keys[i]",
                sort_arg_names=["values", "keys"])

        from pyopencl.elementwise import ElementwiseTemplate
        start_finder = ElementwiseTemplate(
                arguments="""//CL//
                starts_t *key_group_starts,
                key_t *keys_sorted_by_key,
                """,

                operation=r"""//CL//
                key_t my_key = keys_sorted_by_key[i];

                if (i == 0 || my_key != keys_sorted_by_key[i-1])
                    key_group_starts[my_key] = i;
                """,
                name="find_starts").build(self.context,
                        type_aliases=(
                            ("key_t", starts_dtype),
                            ("starts_t", starts_dtype),
                            ),
                        var_values=())

        from pyopencl.scan import GenericScanKernel
        bound_propagation_scan = GenericScanKernel(
                self.context, starts_dtype,
                arguments=[
                    VectorArg(starts_dtype, "starts"),
                    # starts has length n+1
                    ScalarArg(key_dtype, "nkeys"),
                    ],
                input_expr="starts[nkeys-i]",
                scan_expr="min(a, b)",
                neutral=_make_cl_int_literal(
                    np.iinfo(starts_dtype).max, starts_dtype),
                output_statement="starts[nkeys-i] = item;")

        return _KernelInfo(
                by_target_sorter=by_target_sorter,
                start_finder=start_finder,
                bound_propagation_scan=bound_propagation_scan)

    def __call__(self, queue, keys, values, nkeys,
            starts_dtype, allocator=None, wait_for=None):
        if allocator is None:
            allocator = values.allocator

        knl_info = self.get_kernels(keys.dtype, values.dtype,
                starts_dtype)

        (values_sorted_by_key, keys_sorted_by_key), evt = knl_info.by_target_sorter(
                values, keys, queue=queue, wait_for=wait_for)

        starts = (cl.array.empty(queue, (nkeys+1), starts_dtype, allocator=allocator)
                .fill(len(values_sorted_by_key), wait_for=[evt]))
        evt, = starts.events

        evt = knl_info.start_finder(starts, keys_sorted_by_key,
                range=slice(len(keys_sorted_by_key)),
                wait_for=[evt])

        evt = knl_info.bound_propagation_scan(starts, nkeys,
                queue=queue, wait_for=[evt])

        return starts, values_sorted_by_key, evt

# }}}

# vim: filetype=pyopencl:fdm=marker

########NEW FILE########
__FILENAME__ = array
"""CL device arrays."""

from __future__ import division

__copyright__ = "Copyright (C) 2009 Andreas Kloeckner"

__license__ = """
Permission is hereby granted, free of charge, to any person
obtaining a copy of this software and associated documentation
files (the "Software"), to deal in the Software without
restriction, including without limitation the rights to use,
copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following
conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.
"""


import numpy as np
import pyopencl.elementwise as elementwise
import pyopencl as cl
from pytools import memoize_method
from pyopencl.compyte.array import (
        as_strided as _as_strided,
        f_contiguous_strides as _f_contiguous_strides,
        c_contiguous_strides as _c_contiguous_strides,
        ArrayFlags as _ArrayFlags,
        get_common_dtype as _get_common_dtype_base)
from pyopencl.compyte.dtypes import DTypeDict as _DTypeDict
from pyopencl.characterize import has_double_support


def _get_common_dtype(obj1, obj2, queue):
    return _get_common_dtype_base(obj1, obj2,
            has_double_support(queue.device))

# Work around PyPy not currently supporting the object dtype.
# (Yes, it doesn't even support checking!)
# (as of May 27, 2014 on PyPy 2.3)
try:
    np.dtype(object)

    def _dtype_is_object(t):
        return t == object
except:
    def _dtype_is_object(t):
        return False

# {{{ vector types

class vec:
    pass


def _create_vector_types():
    field_names = ["x", "y", "z", "w"]

    from pyopencl.tools import get_or_register_dtype

    vec.types = {}
    vec.type_to_scalar_and_count = _DTypeDict()

    counts = [2, 3, 4, 8, 16]

    for base_name, base_type in [
            ('char', np.int8),
            ('uchar', np.uint8),
            ('short', np.int16),
            ('ushort', np.uint16),
            ('int', np.int32),
            ('uint', np.uint32),
            ('long', np.int64),
            ('ulong', np.uint64),
            ('float', np.float32),
            ('double', np.float64),
            ]:
        for count in counts:
            name = "%s%d" % (base_name, count)

            titles = field_names[:count]

            padded_count = count
            if count == 3:
                padded_count = 4

            names = ["s%d" % i for i in range(count)]
            while len(names) < padded_count:
                names.append("padding%d" % (len(names)-count))

            if len(titles) < len(names):
                titles.extend((len(names)-len(titles))*[None])

            try:
                dtype = np.dtype(dict(
                    names=names,
                    formats=[base_type]*padded_count,
                    titles=titles))
            except NotImplementedError:
                try:
                    dtype = np.dtype([((n, title), base_type)
                                      for (n, title) in zip(names, titles)])
                except TypeError:
                    dtype = np.dtype([(n, base_type) for (n, title)
                                      in zip(names, titles)])

            get_or_register_dtype(name, dtype)

            setattr(vec, name, dtype)

            def create_array(dtype, count, padded_count, *args, **kwargs):
                if len(args) < count:
                    from warnings import warn
                    warn("default values for make_xxx are deprecated;"
                            " instead specify all parameters or use"
                            " array.vec.zeros_xxx", DeprecationWarning)
                padded_args = tuple(list(args)+[0]*(padded_count-len(args)))
                array = eval("array(padded_args, dtype=dtype)",
                        dict(array=np.array, padded_args=padded_args,
                        dtype=dtype))
                for key, val in kwargs.items():
                    array[key] = val
                return array

            setattr(vec, "make_"+name, staticmethod(eval(
                    "lambda *args, **kwargs: create_array(dtype, %i, %i, "
                    "*args, **kwargs)" % (count, padded_count),
                    dict(create_array=create_array, dtype=dtype))))
            setattr(vec, "filled_"+name, staticmethod(eval(
                    "lambda val: vec.make_%s(*[val]*%i)" % (name, count))))
            setattr(vec, "zeros_"+name,
                    staticmethod(eval("lambda: vec.filled_%s(0)" % (name))))
            setattr(vec, "ones_"+name,
                    staticmethod(eval("lambda: vec.filled_%s(1)" % (name))))

            vec.types[np.dtype(base_type), count] = dtype
            vec.type_to_scalar_and_count[dtype] = np.dtype(base_type), count

_create_vector_types()

# }}}


# {{{ helper functionality

def splay(queue, n, kernel_specific_max_wg_size=None):
    dev = queue.device
    max_work_items = _builtin_min(128, dev.max_work_group_size)

    if kernel_specific_max_wg_size is not None:
        from __builtin__ import min
        max_work_items = min(max_work_items, kernel_specific_max_wg_size)

    min_work_items = _builtin_min(32, max_work_items)
    max_groups = dev.max_compute_units * 4 * 8
    # 4 to overfill the device
    # 8 is an Nvidia constant--that's how many
    # groups fit onto one compute device

    if n < min_work_items:
        group_count = 1
        work_items_per_group = min_work_items
    elif n < (max_groups * min_work_items):
        group_count = (n + min_work_items - 1) // min_work_items
        work_items_per_group = min_work_items
    elif n < (max_groups * max_work_items):
        group_count = max_groups
        grp = (n + min_work_items - 1) // min_work_items
        work_items_per_group = (
                (grp + max_groups - 1) // max_groups) * min_work_items
    else:
        group_count = max_groups
        work_items_per_group = max_work_items

    #print "n:%d gc:%d wipg:%d" % (n, group_count, work_items_per_group)
    return (group_count*work_items_per_group,), (work_items_per_group,)


def elwise_kernel_runner(kernel_getter):
    """Take a kernel getter of the same signature as the kernel
    and return a function that invokes that kernel.

    Assumes that the zeroth entry in *args* is an :class:`Array`.
    """

    def kernel_runner(*args, **kwargs):
        repr_ary = args[0]
        queue = kwargs.pop("queue", None) or repr_ary.queue
        wait_for = kwargs.pop("wait_for", None)

        # wait_for must be a copy, because we modify it in-place below
        if wait_for is None:
            wait_for = []
        else:
            wait_for = list(wait_for)

        knl = kernel_getter(*args, **kwargs)

        gs, ls = repr_ary.get_sizes(queue,
                knl.get_work_group_info(
                    cl.kernel_work_group_info.WORK_GROUP_SIZE,
                    queue.device))

        assert isinstance(repr_ary, Array)

        actual_args = []
        for arg in args:
            if isinstance(arg, Array):
                if not arg.flags.forc:
                    raise RuntimeError("only contiguous arrays may "
                            "be used as arguments to this operation")
                actual_args.append(arg.base_data)
                actual_args.append(arg.offset)
                wait_for.extend(arg.events)
            else:
                actual_args.append(arg)
        actual_args.append(repr_ary.size)

        return knl(queue, gs, ls, *actual_args, **dict(wait_for=wait_for))

    try:
        from functools import update_wrapper
    except ImportError:
        return kernel_runner
    else:
        return update_wrapper(kernel_runner, kernel_getter)


class DefaultAllocator(cl.tools.DeferredAllocator):
    def __init__(self, *args, **kwargs):
        from warnings import warn
        warn("pyopencl.array.DefaultAllocator is deprecated. "
                "It will be continue to exist throughout the 2013.x "
                "versions of PyOpenCL.",
                DeprecationWarning, 2)
        cl.tools.DeferredAllocator.__init__(self, *args, **kwargs)


def _make_strides(itemsize, shape, order):
    if order in "fF":
        return _f_contiguous_strides(itemsize, shape)
    elif order in "cC":
        return _c_contiguous_strides(itemsize, shape)
    else:
        raise ValueError("invalid order: %s" % order)

# }}}


# {{{ array class

class ArrayHasOffsetError(ValueError):
    """
    .. versionadded:: 2013.1
    """

    def __init__(self, val="The operation you are attempting does not yet "
                "support arrays that start at an offset from the beginning "
                "of their buffer."):
        ValueError.__init__(self, val)


class _copy_queue:
    pass


class Array(object):
    """A :class:`numpy.ndarray` work-alike that stores its data and performs
    its computations on the compute device.  *shape* and *dtype* work exactly
    as in :mod:`numpy`.  Arithmetic methods in :class:`Array` support the
    broadcasting of scalars. (e.g. `array+5`)

    *cqa* must be a :class:`pyopencl.CommandQueue` or a :class:`pyopencl.Context`.

    If it is a queue, *cqa* specifies the queue in which the array carries out
    its computations by default. If a default queue (and thereby overloaded
    operators and many other niceties) are not desired, pass a
    :class:`Context`.

    *cqa* will at some point be renamed *cq*, so it should be considered
    'positional-only'. Arguments starting from 'order' should be considered
    keyword-only.

    *allocator* may be `None` or a callable that, upon being called with an
    argument of the number of bytes to be allocated, returns an
    :class:`pyopencl.Buffer` object. (A :class:`pyopencl.tools.MemoryPool`
    instance is one useful example of an object to pass here.)

    .. versionchanged:: 2011.1
        Renamed *context* to *cqa*, made it general-purpose.

        All arguments beyond *order* should be considered keyword-only.

    .. attribute :: data

        The :class:`pyopencl.MemoryObject` instance created for the memory that
        backs this :class:`Array`.

        .. versionchanged:: 2013.1

            If a non-zero :attr:`offset` has been specified for this array,
            this will fail with :exc:`ArrayHasOffsetError`.

    .. attribute :: base_data

        The :class:`pyopencl.MemoryObject` instance created for the memory that
        backs this :class:`Array`. Unlike :attr:`data`, the base address of
        *base_data* is allowed to be different from the beginning of the array.
        The actual beginning is the base address of *base_data* plus
        :attr:`offset` in units of :attr:`dtype`.

        Unlike :attr:`data`, retrieving :attr:`base_data` always succeeds.

        .. versionadded:: 2013.1

    .. attribute :: offset

        See :attr:`base_data`.

        .. versionadded:: 2013.1

    .. attribute :: shape

        The tuple of lengths of each dimension in the array.

    .. attribute :: dtype

        The :class:`numpy.dtype` of the items in the GPU array.

    .. attribute :: size

        The number of meaningful entries in the array. Can also be computed by
        multiplying up the numbers in :attr:`shape`.

    .. attribute :: nbytes

        The size of the entire array in bytes. Computed as :attr:`size` times
        ``dtype.itemsize``.

    .. attribute :: strides

        Tuple of bytes to step in each dimension when traversing an array.

    .. attribute :: flags

        Return an object with attributes `c_contiguous`, `f_contiguous` and
        `forc`, which may be used to query contiguity properties in analogy to
        :attr:`numpy.ndarray.flags`.

    .. rubric:: Methods

    .. automethod :: with_queue

    .. automethod :: __len__
    .. automethod :: reshape
    .. automethod :: ravel
    .. automethod :: view
    .. automethod :: set
    .. automethod :: get
    .. automethod :: copy

    .. automethod :: __str__
    .. automethod :: __repr__

    .. automethod :: mul_add
    .. automethod :: __add__
    .. automethod :: __sub__
    .. automethod :: __iadd__
    .. automethod :: __isub__
    .. automethod :: __neg__
    .. automethod :: __mul__
    .. automethod :: __div__
    .. automethod :: __rdiv__
    .. automethod :: __pow__

    .. automethod :: __abs__

    .. UNDOC reverse()

    .. automethod :: fill

    .. automethod :: astype

    .. autoattribute :: real
    .. autoattribute :: imag
    .. automethod :: conj

    .. automethod :: __getitem__
    .. automethod :: __setitem__

    .. automethod :: setitem

    .. automethod :: map_to_host

    .. rubric:: Comparisons, conditionals, any, all

    .. versionadded:: 2013.2

    Boolean arrays are stored as :class:`numpy.int8` because ``bool``
    has an unspecified size in the OpenCL spec.

    .. automethod :: __nonzero__

        Only works for device scalars. (i.e. "arrays" with ``shape == ()``.)

    .. automethod :: any
    .. automethod :: all

    .. automethod :: __eq__
    .. automethod :: __ne__
    .. automethod :: __lt__
    .. automethod :: __le__
    .. automethod :: __gt__
    .. automethod :: __ge__
    """

    __array_priority__ = 100

    def __init__(self, cqa, shape, dtype, order="C", allocator=None,
            data=None, offset=0, queue=None, strides=None, events=None):
        # {{{ backward compatibility

        from warnings import warn
        if queue is not None:
            warn("Passing the queue to the array through anything but the "
                    "first argument of the Array constructor is deprecated. "
                    "This will be continue to be accepted throughout the "
                    "2013.[0-6] versions of PyOpenCL.",
                    DeprecationWarning, 2)

        if isinstance(cqa, cl.CommandQueue):
            if queue is not None:
                raise TypeError("can't specify queue in 'cqa' and "
                        "'queue' arguments")
            queue = cqa

        elif isinstance(cqa, cl.Context):
            context = cqa

            if queue is not None:
                raise TypeError("may not pass a context and a queue "
                        "(just pass the queue)")
            if allocator is not None:
                # "is" would be wrong because two Python objects are allowed
                # to hold handles to the same context.

                # FIXME It would be nice to check this. But it would require
                # changing the allocator interface. Trust the user for now.

                #assert allocator.context == context
                pass

        else:
            # cqa is assumed to be an allocator
            warn("Passing an allocator for the 'cqa' parameter is deprecated. "
                    "This usage will be continue to be accepted throughout "
                    "the 2013.[0-6] versions of PyOpenCL.",
                    DeprecationWarning, stacklevel=2)
            if allocator is not None:
                raise TypeError("can't specify allocator in 'cqa' and "
                        "'allocator' arguments")

            allocator = cqa

        # Queue-less arrays do have a purpose in life.
        # They don't do very much, but at least they don't run kernels
        # in random queues.
        #
        # See also :meth:`with_queue`.

        # }}}

        # invariant here: allocator, queue set

        # {{{ determine shape and strides
        dtype = np.dtype(dtype)

        try:
            s = 1
            for dim in shape:
                s *= dim
        except TypeError:
            import sys
            if sys.version_info >= (3,):
                admissible_types = (int, np.integer)
            else:
                admissible_types = (int, long, np.integer)

            if not isinstance(shape, admissible_types):
                raise TypeError("shape must either be iterable or "
                        "castable to an integer")
            s = shape
            shape = (shape,)

        if isinstance(s, np.integer):
            # bombs if s is a Python integer
            s = np.asscalar(s)

        if strides is None:
            strides = _make_strides(dtype.itemsize, shape, order)

        else:
            # FIXME: We should possibly perform some plausibility
            # checking on 'strides' here.

            strides = tuple(strides)

        # }}}

        if _dtype_is_object(dtype):
            raise TypeError("object arrays on the compute device are not allowed")

        self.queue = queue
        self.shape = shape
        self.dtype = dtype
        self.strides = strides
        if events is None:
            self.events = []
        else:
            self.events = events

        self.size = s
        alloc_nbytes = self.nbytes = self.dtype.itemsize * self.size

        self.allocator = allocator

        if data is None:
            if not alloc_nbytes:
                # Work around CL not allowing zero-sized buffers.
                alloc_nbytes = 1

            if allocator is None:
                # FIXME remove me when queues become required
                if queue is not None:
                    context = queue.context

                self.base_data = cl.Buffer(
                        context, cl.mem_flags.READ_WRITE, alloc_nbytes)
            else:
                self.base_data = self.allocator(alloc_nbytes)
        else:
            self.base_data = data

        self.offset = offset

    @property
    def context(self):
        return self.base_data.context

    @property
    def data(self):
        if self.offset:
            raise ArrayHasOffsetError()
        else:
            return self.base_data

    @property
    @memoize_method
    def flags(self):
        return _ArrayFlags(self)

    def _new_with_changes(self, data, offset, shape=None, dtype=None,
            strides=None, queue=_copy_queue):
        """
        :arg data: *None* means alocate a new array.
        """
        if shape is None:
            shape = self.shape
        if dtype is None:
            dtype = self.dtype
        if strides is None:
            strides = self.strides
        if queue is _copy_queue:
            queue = self.queue

        if queue is not None:
            return Array(queue, shape, dtype, allocator=self.allocator,
                    strides=strides, data=data, offset=offset,
                    events=self.events)
        else:
            return Array(self.context, shape, dtype, queue=queue,
                    strides=strides, data=data, offset=offset,
                    events=self.events, allocator=self.allocator)

    def with_queue(self, queue):
        """Return a copy of *self* with the default queue set to *queue*.

        *None* is allowed as a value for *queue*.

        .. versionadded:: 2013.1
        """

        if queue is not None:
            assert queue.context == self.context

        return self._new_with_changes(self.base_data, self.offset,
                queue=queue)

    #@memoize_method FIXME: reenable
    def get_sizes(self, queue, kernel_specific_max_wg_size=None):
        if not self.flags.forc:
            raise NotImplementedError("cannot operate on non-contiguous array")
        return splay(queue, self.size,
                kernel_specific_max_wg_size=kernel_specific_max_wg_size)

    def set(self, ary, queue=None, async=False):
        """Transfer the contents the :class:`numpy.ndarray` object *ary*
        onto the device.

        *ary* must have the same dtype and size (not necessarily shape) as
        *self*.
        """

        assert ary.size == self.size
        assert ary.dtype == self.dtype

        if not ary.flags.forc:
            raise RuntimeError("cannot set from non-contiguous array")

            ary = ary.copy()

        if ary.strides != self.strides:
            from warnings import warn
            warn("Setting array from one with different "
                    "strides/storage order. This will cease to work "
                    "in 2013.x.",
                    stacklevel=2)

        if self.size:
            cl.enqueue_copy(queue or self.queue, self.base_data, ary,
                    device_offset=self.offset,
                    is_blocking=not async)

    def get(self, queue=None, ary=None, async=False):
        """Transfer the contents of *self* into *ary* or a newly allocated
        :mod:`numpy.ndarray`. If *ary* is given, it must have the right
        size (not necessarily shape) and dtype.
        """

        if ary is None:
            ary = np.empty(self.shape, self.dtype)

            ary = _as_strided(ary, strides=self.strides)
        else:
            if ary.size != self.size:
                raise TypeError("'ary' has non-matching size")
            if ary.dtype != self.dtype:
                raise TypeError("'ary' has non-matching type")

        assert self.flags.forc, "Array in get() must be contiguous"

        if self.size:
            cl.enqueue_copy(queue or self.queue, ary, self.base_data,
                    device_offset=self.offset,
                    is_blocking=not async)

        return ary

    def copy(self, queue=None):
        """.. versionadded:: 2013.1"""

        queue = queue or self.queue
        result = self._new_like_me()
        cl.enqueue_copy(queue, result.base_data, self.base_data,
                src_offset=self.offset, byte_count=self.nbytes)

        return result

    def __str__(self):
        return str(self.get())

    def __repr__(self):
        return repr(self.get())

    def __hash__(self):
        raise TypeError("pyopencl arrays are not hashable.")

    # {{{ kernel invocation wrappers

    @staticmethod
    @elwise_kernel_runner
    def _axpbyz(out, afac, a, bfac, b, queue=None):
        """Compute ``out = selffac * self + otherfac*other``,
        where *other* is an array."""
        assert out.shape == a.shape
        assert out.shape == b.shape

        return elementwise.get_axpbyz_kernel(
                out.context, a.dtype, b.dtype, out.dtype)

    @staticmethod
    @elwise_kernel_runner
    def _axpbz(out, a, x, b, queue=None):
        """Compute ``z = a * x + b``, where *b* is a scalar."""
        a = np.array(a)
        b = np.array(b)
        assert out.shape == x.shape
        return elementwise.get_axpbz_kernel(out.context,
                a.dtype, x.dtype, b.dtype, out.dtype)

    @staticmethod
    @elwise_kernel_runner
    def _elwise_multiply(out, a, b, queue=None):
        assert out.shape == a.shape
        assert out.shape == b.shape
        return elementwise.get_multiply_kernel(
                a.context, a.dtype, b.dtype, out.dtype)

    @staticmethod
    @elwise_kernel_runner
    def _rdiv_scalar(out, ary, other, queue=None):
        other = np.array(other)
        assert out.shape == ary.shape
        return elementwise.get_rdivide_elwise_kernel(
                out.context, ary.dtype, other.dtype, out.dtype)

    @staticmethod
    @elwise_kernel_runner
    def _div(out, self, other, queue=None):
        """Divides an array by another array."""

        assert self.shape == other.shape

        return elementwise.get_divide_kernel(self.context,
                self.dtype, other.dtype, out.dtype)

    @staticmethod
    @elwise_kernel_runner
    def _fill(result, scalar):
        return elementwise.get_fill_kernel(result.context, result.dtype)

    @staticmethod
    @elwise_kernel_runner
    def _abs(result, arg):
        if arg.dtype.kind == "c":
            from pyopencl.elementwise import complex_dtype_to_name
            fname = "%s_abs" % complex_dtype_to_name(arg.dtype)
        elif arg.dtype.kind == "f":
            fname = "fabs"
        elif arg.dtype.kind in ["u", "i"]:
            fname = "abs"
        else:
            raise TypeError("unsupported dtype in _abs()")

        return elementwise.get_unary_func_kernel(
                arg.context, fname, arg.dtype, out_dtype=result.dtype)

    @staticmethod
    @elwise_kernel_runner
    def _real(result, arg):
        from pyopencl.elementwise import complex_dtype_to_name
        fname = "%s_real" % complex_dtype_to_name(arg.dtype)
        return elementwise.get_unary_func_kernel(
                arg.context, fname, arg.dtype, out_dtype=result.dtype)

    @staticmethod
    @elwise_kernel_runner
    def _imag(result, arg):
        from pyopencl.elementwise import complex_dtype_to_name
        fname = "%s_imag" % complex_dtype_to_name(arg.dtype)
        return elementwise.get_unary_func_kernel(
                arg.context, fname, arg.dtype, out_dtype=result.dtype)

    @staticmethod
    @elwise_kernel_runner
    def _conj(result, arg):
        from pyopencl.elementwise import complex_dtype_to_name
        fname = "%s_conj" % complex_dtype_to_name(arg.dtype)
        return elementwise.get_unary_func_kernel(
                arg.context, fname, arg.dtype, out_dtype=result.dtype)

    @staticmethod
    @elwise_kernel_runner
    def _pow_scalar(result, ary, exponent):
        exponent = np.array(exponent)
        return elementwise.get_pow_kernel(result.context,
                ary.dtype, exponent.dtype, result.dtype,
                is_base_array=True, is_exp_array=False)

    @staticmethod
    @elwise_kernel_runner
    def _rpow_scalar(result, base, exponent):
        base = np.array(base)
        return elementwise.get_pow_kernel(result.context,
                base.dtype, exponent.dtype, result.dtype,
                is_base_array=False, is_exp_array=True)

    @staticmethod
    @elwise_kernel_runner
    def _pow_array(result, base, exponent):
        return elementwise.get_pow_kernel(
                result.context, base.dtype, exponent.dtype, result.dtype,
                is_base_array=True, is_exp_array=True)

    @staticmethod
    @elwise_kernel_runner
    def _reverse(result, ary):
        return elementwise.get_reverse_kernel(result.context, ary.dtype)

    @staticmethod
    @elwise_kernel_runner
    def _copy(dest, src):
        return elementwise.get_copy_kernel(
                dest.context, dest.dtype, src.dtype)

    def _new_like_me(self, dtype=None, queue=None):
        strides = None
        if dtype is None:
            dtype = self.dtype
        else:
            if dtype == self.dtype:
                strides = self.strides

        queue = queue or self.queue
        if queue is not None:
            return self.__class__(queue, self.shape, dtype,
                    allocator=self.allocator, strides=strides)
        elif self.allocator is not None:
            return self.__class__(self.allocator, self.shape, dtype,
                    strides=strides)
        else:
            return self.__class__(self.context, self.shape, dtype,
                    strides=strides)

    # }}}

    # {{{ operators

    def mul_add(self, selffac, other, otherfac, queue=None):
        """Return `selffac * self + otherfac*other`.
        """
        result = self._new_like_me(
                _get_common_dtype(self, other, queue or self.queue))
        self._axpbyz(result, selffac, self, otherfac, other)
        return result

    def __add__(self, other):
        """Add an array with an array or an array with a scalar."""

        if isinstance(other, Array):
            # add another vector
            result = self._new_like_me(
                    _get_common_dtype(self, other, self.queue))
            self._axpbyz(result,
                    self.dtype.type(1), self,
                    other.dtype.type(1), other)
            return result
        else:
            # add a scalar
            if other == 0:
                return self.copy()
            else:
                common_dtype = _get_common_dtype(self, other, self.queue)
                result = self._new_like_me(common_dtype)
                self._axpbz(result, self.dtype.type(1),
                        self, common_dtype.type(other))
                return result

    __radd__ = __add__

    def __sub__(self, other):
        """Substract an array from an array or a scalar from an array."""

        if isinstance(other, Array):
            result = self._new_like_me(
                    _get_common_dtype(self, other, self.queue))
            self._axpbyz(result,
                    self.dtype.type(1), self,
                    other.dtype.type(-1), other)
            return result
        else:
            # subtract a scalar
            if other == 0:
                return self.copy()
            else:
                result = self._new_like_me(
                        _get_common_dtype(self, other, self.queue))
                self._axpbz(result, self.dtype.type(1), self, -other)
                return result

    def __rsub__(self, other):
        """Substracts an array by a scalar or an array::

           x = n - self
        """
        common_dtype = _get_common_dtype(self, other, self.queue)
        # other must be a scalar
        result = self._new_like_me(common_dtype)
        self._axpbz(result, self.dtype.type(-1), self,
                common_dtype.type(other))
        return result

    def __iadd__(self, other):
        if isinstance(other, Array):
            self._axpbyz(self,
                    self.dtype.type(1), self,
                    other.dtype.type(1), other)
            return self
        else:
            self._axpbz(self, self.dtype.type(1), self, other)
            return self

    def __isub__(self, other):
        if isinstance(other, Array):
            self._axpbyz(self, self.dtype.type(1), self,
                    other.dtype.type(-1), other)
            return self
        else:
            self._axpbz(self, self.dtype.type(1), self, -other)
            return self

    def __neg__(self):
        result = self._new_like_me()
        self._axpbz(result, -1, self, 0)
        return result

    def __mul__(self, other):
        if isinstance(other, Array):
            result = self._new_like_me(
                    _get_common_dtype(self, other, self.queue))
            self._elwise_multiply(result, self, other)
            return result
        else:
            common_dtype = _get_common_dtype(self, other, self.queue)
            result = self._new_like_me(common_dtype)
            self._axpbz(result,
                    common_dtype.type(other), self, self.dtype.type(0))
            return result

    def __rmul__(self, scalar):
        common_dtype = _get_common_dtype(self, scalar, self.queue)
        result = self._new_like_me(common_dtype)
        self._axpbz(result,
                common_dtype.type(scalar), self, self.dtype.type(0))
        return result

    def __imul__(self, other):
        if isinstance(other, Array):
            self._elwise_multiply(self, self, other)
        else:
            # scalar
            self._axpbz(self, other, self, self.dtype.type(0))

        return self

    def __div__(self, other):
        """Divides an array by an array or a scalar, i.e. ``self / other``.
        """
        if isinstance(other, Array):
            result = self._new_like_me(
                    _get_common_dtype(self, other, self.queue))
            self._div(result, self, other)
        else:
            if other == 1:
                return self.copy()
            else:
                # create a new array for the result
                common_dtype = _get_common_dtype(self, other, self.queue)
                result = self._new_like_me(common_dtype)
                self._axpbz(result,
                        common_dtype.type(1/other), self, self.dtype.type(0))

        return result

    __truediv__ = __div__

    def __rdiv__(self, other):
        """Divides an array by a scalar or an array, i.e. ``other / self``.
        """

        if isinstance(other, Array):
            result = self._new_like_me(
                    _get_common_dtype(self, other, self.queue))
            other._div(result, self)
        else:
            # create a new array for the result
            common_dtype = _get_common_dtype(self, other, self.queue)
            result = self._new_like_me(common_dtype)
            self._rdiv_scalar(result, self, common_dtype.type(other))

        return result

    __rtruediv__ = __rdiv__

    def fill(self, value, queue=None, wait_for=None):
        """Fill the array with *scalar*.

        :returns: *self*.
        """
        self.events.append(
                self._fill(self, value, queue=queue, wait_for=wait_for))

        return self

    def __len__(self):
        """Returns the size of the leading dimension of *self*."""
        if len(self.shape):
            return self.shape[0]
        else:
            return TypeError("scalar has no len()")

    def __abs__(self):
        """Return a `Array` of the absolute values of the elements
        of *self*.
        """

        result = self._new_like_me(self.dtype.type(0).real.dtype)
        self._abs(result, self)
        return result

    def __pow__(self, other):
        """Exponentiation by a scalar or elementwise by another
        :class:`Array`.
        """

        if isinstance(other, Array):
            assert self.shape == other.shape

            result = self._new_like_me(
                    _get_common_dtype(self, other, self.queue))
            self._pow_array(result, self, other)
        else:
            result = self._new_like_me(
                    _get_common_dtype(self, other, self.queue))
            self._pow_scalar(result, self, other)

        return result

    def __rpow__(self, other):
        # other must be a scalar
        common_dtype = _get_common_dtype(self, other, self.queue)
        result = self._new_like_me(common_dtype)
        self._rpow_scalar(result, common_dtype.type(other), self)
        return result

    # }}}

    def reverse(self, queue=None):
        """Return this array in reversed order. The array is treated
        as one-dimensional.
        """

        result = self._new_like_me()
        self._reverse(result, self)
        return result

    def astype(self, dtype, queue=None):
        """Return a copy of *self*, cast to *dtype*."""
        if dtype == self.dtype:
            return self.copy()

        result = self._new_like_me(dtype=dtype)
        self._copy(result, self, queue=queue)
        return result

    # {{{ rich comparisons, any, all

    def __nonzero__(self):
        if self.shape == ():
            return bool(self.get())
        else:
            raise ValueError("The truth value of an array with "
                    "more than one element is ambiguous. Use a.any() or a.all()")

    def any(self, queue=None, wait_for=None):
        from pyopencl.reduction import get_any_kernel
        krnl = get_any_kernel(self.context, self.dtype)
        return krnl(self, queue=queue, wait_for=wait_for)

    def all(self, queue=None, wait_for=None):
        from pyopencl.reduction import get_all_kernel
        krnl = get_all_kernel(self.context, self.dtype)
        return krnl(self, queue=queue, wait_for=wait_for)

    @staticmethod
    @elwise_kernel_runner
    def _scalar_comparison(out, a, b, queue=None, op=None):
        return elementwise.get_array_scalar_comparison_kernel(
                out.context, op, a.dtype)

    @staticmethod
    @elwise_kernel_runner
    def _array_comparison(out, a, b, queue=None, op=None):
        if a.shape != b.shape:
            raise ValueError("shapes of comparison arguments do not match")
        return elementwise.get_array_comparison_kernel(
                out.context, op, a.dtype, b.dtype)

    def __eq__(self, other):
        if isinstance(other, Array):
            result = self._new_like_me(np.int8)
            self._array_comparison(result, self, other, op="==")
            return result
        else:
            result = self._new_like_me(np.int8)
            self._scalar_comparison(result, self, other, op="==")
            return result

    def __ne__(self, other):
        if isinstance(other, Array):
            result = self._new_like_me(np.int8)
            self._array_comparison(result, self, other, op="!=")
            return result
        else:
            result = self._new_like_me(np.int8)
            self._scalar_comparison(result, self, other, op="!=")
            return result

    def __le__(self, other):
        if isinstance(other, Array):
            result = self._new_like_me(np.int8)
            self._array_comparison(result, self, other, op="<=")
            return result
        else:
            result = self._new_like_me(np.int8)
            self._scalar_comparison(result, self, other, op="<=")
            return result

    def __ge__(self, other):
        if isinstance(other, Array):
            result = self._new_like_me(np.int8)
            self._array_comparison(result, self, other, op=">=")
            return result
        else:
            result = self._new_like_me(np.int8)
            self._scalar_comparison(result, self, other, op=">=")
            return result

    def __lt__(self, other):
        if isinstance(other, Array):
            result = self._new_like_me(np.int8)
            self._array_comparison(result, self, other, op="<")
            return result
        else:
            result = self._new_like_me(np.int8)
            self._scalar_comparison(result, self, other, op="<")
            return result

    def __gt__(self, other):
        if isinstance(other, Array):
            result = self._new_like_me(np.int8)
            self._array_comparison(result, self, other, op=">")
            return result
        else:
            result = self._new_like_me(np.int8)
            self._scalar_comparison(result, self, other, op=">")
            return result

    # }}}

    # {{{ complex-valued business

    def real(self):
        if self.dtype.kind == "c":
            result = self._new_like_me(self.dtype.type(0).real.dtype)
            self._real(result, self)
            return result
        else:
            return self
    real = property(real, doc=".. versionadded:: 2012.1")

    def imag(self):
        if self.dtype.kind == "c":
            result = self._new_like_me(self.dtype.type(0).real.dtype)
            self._imag(result, self)
            return result
        else:
            return zeros_like(self)
    imag = property(imag, doc=".. versionadded:: 2012.1")

    def conj(self):
        """.. versionadded:: 2012.1"""
        if self.dtype.kind == "c":
            result = self._new_like_me()
            self._conj(result, self)
            return result
        else:
            return self

    # }}}

    def finish(self):
        # undoc
        if self.events:
            cl.wait_for_events(self.events)
            del self.events[:]

    # {{{ views

    def reshape(self, *shape, **kwargs):
        """Returns an array containing the same data with a new shape."""

        order = kwargs.pop("order", "C")
        if kwargs:
            raise TypeError("unexpected keyword arguments: %s"
                    % kwargs.keys())

        # TODO: add more error-checking, perhaps
        if isinstance(shape[0], tuple) or isinstance(shape[0], list):
            shape = tuple(shape[0])

        if shape == self.shape:
            return self

        size = reduce(lambda x, y: x * y, shape, 1)
        if size != self.size:
            raise ValueError("total size of new array must be unchanged")

        return self._new_with_changes(
                data=self.base_data, offset=self.offset, shape=shape,
                strides=_make_strides(self.dtype.itemsize, shape, order))

    def ravel(self):
        """Returns flattened array containing the same data."""
        return self.reshape(self.size)

    def view(self, dtype=None):
        """Returns view of array with the same data. If *dtype* is different
        from current dtype, the actual bytes of memory will be reinterpreted.
        """

        if dtype is None:
            dtype = self.dtype

        old_itemsize = self.dtype.itemsize
        itemsize = np.dtype(dtype).itemsize

        from pytools import argmin2
        min_stride_axis = argmin2(
                (axis, abs(stride))
                for axis, stride in enumerate(self.strides))

        if self.shape[min_stride_axis] * old_itemsize % itemsize != 0:
            raise ValueError("new type not compatible with array")

        new_shape = (
                self.shape[:min_stride_axis]
                + (self.shape[min_stride_axis] * old_itemsize // itemsize,)
                + self.shape[min_stride_axis+1:])
        new_strides = (
                self.strides[:min_stride_axis]
                + (self.strides[min_stride_axis] * itemsize // old_itemsize,)
                + self.strides[min_stride_axis+1:])

        return self._new_with_changes(
                self.base_data, self.offset,
                shape=new_shape, dtype=dtype,
                strides=new_strides)

    # }}}

    def map_to_host(self, queue=None, flags=None, is_blocking=True, wait_for=None):
        """If *is_blocking*, return a :class:`numpy.ndarray` corresponding to the
        same memory as *self*.

        If *is_blocking* is not true, return a tuple ``(ary, evt)``, where
        *ary* is the above-mentioned array.

        The host array is obtained using :func:`pyopencl.enqueue_map_buffer`.
        See there for further details.

        :arg flags: A combination of :class:`pyopencl.map_flags`.
            Defaults to read-write.

        .. versionadded :: 2013.2
        """

        if flags is None:
            flags = cl.map_flags.READ | cl.map_flags.WRITE

        ary, evt = cl.enqueue_map_buffer(
                queue or self.queue, self.base_data, flags, self.offset,
                self.shape, self.dtype, strides=self.strides, wait_for=wait_for,
                is_blocking=is_blocking)

        if is_blocking:
            return ary
        else:
            return ary, evt

    # {{{ getitem/setitem

    def __getitem__(self, index):
        """
        .. versionadded:: 2013.1
        """

        if isinstance(index, Array):
            if index.dtype.kind != "i":
                raise TypeError(
                        "fancy indexing is only allowed with integers")
            if len(index.shape) != 1:
                raise NotImplementedError(
                        "multidimensional fancy indexing is not supported")
            if len(self.shape) != 1:
                raise NotImplementedError(
                        "fancy indexing into a multi-d array is not supported")

            return take(self, index)

        if not isinstance(index, tuple):
            index = (index,)

        new_shape = []
        new_offset = self.offset
        new_strides = []

        seen_ellipsis = False

        index_axis = 0
        array_axis = 0
        while index_axis < len(index):
            index_entry = index[index_axis]

            if array_axis > len(self.shape):
                raise IndexError("too many axes in index")

            if isinstance(index_entry, slice):
                start, stop, idx_stride = index_entry.indices(
                        self.shape[array_axis])

                array_stride = self.strides[array_axis]

                new_shape.append((stop-start)//idx_stride)
                new_strides.append(idx_stride*array_stride)
                new_offset += array_stride*start

                index_axis += 1
                array_axis += 1

            elif isinstance(index_entry, (int, np.integer)):
                array_shape = self.shape[array_axis]
                if index_entry < 0:
                    index_entry += array_shape

                if not (0 <= index_entry < array_shape):
                    raise IndexError(
                            "subindex in axis %d out of range" % index_axis)

                new_offset += self.strides[array_axis]*index_entry

                index_axis += 1
                array_axis += 1

            elif index_entry is Ellipsis:
                index_axis += 1

                remaining_index_count = len(index) - index_axis
                new_array_axis = len(self.shape) - remaining_index_count
                if new_array_axis < array_axis:
                    raise IndexError("invalid use of ellipsis in index")
                while array_axis < new_array_axis:
                    new_shape.append(self.shape[array_axis])
                    new_strides.append(self.strides[array_axis])
                    array_axis += 1

                if seen_ellipsis:
                    raise IndexError(
                            "more than one ellipsis not allowed in index")
                seen_ellipsis = True

            else:
                raise IndexError("invalid subindex in axis %d" % index_axis)

        while array_axis < len(self.shape):
            new_shape.append(self.shape[array_axis])
            new_strides.append(self.strides[array_axis])

            array_axis += 1

        return self._new_with_changes(
                self.base_data, offset=new_offset,
                shape=tuple(new_shape),
                strides=tuple(new_strides))

    def setitem(self, subscript, value, queue=None, wait_for=None):
        """Like :meth:`__setitem__`, but with the ability to specify
        a *queue* and *wait_for*.

        .. versionadded:: 2013.1

        .. versionchanged:: 2013.2

            Added *wait_for*.
        """

        if isinstance(subscript, Array):
            if subscript.dtype.kind != "i":
                raise TypeError(
                        "fancy indexing is only allowed with integers")
            if len(subscript.shape) != 1:
                raise NotImplementedError(
                        "multidimensional fancy indexing is not supported")
            if len(self.shape) != 1:
                raise NotImplementedError(
                        "fancy indexing into a multi-d array is supported")

            multi_put([value], subscript, out=[self], queue=self.queue,
                    wait_for=wait_for)
            return

        queue = queue or self.queue or value.queue

        subarray = self[subscript]

        if isinstance(value, np.ndarray):
            if subarray.shape == value.shape and subarray.strides == value.strides:
                self.events.append(
                        cl.enqueue_copy(queue, subarray.base_data,
                            value, device_offset=subarray.offset, wait_for=wait_for))
                return
            else:
                value = to_device(queue, value, self.allocator)

        if isinstance(value, Array):
            if len(subarray.shape) != len(value.shape):
                raise NotImplementedError("broadcasting is not "
                        "supported in __setitem__")
            if subarray.shape != value.shape:
                raise ValueError("cannot assign between arrays of "
                        "differing shapes")
            if subarray.strides != value.strides:
                raise ValueError("cannot assign between arrays of "
                        "differing strides")

            self._copy(subarray, value, queue=queue, wait_for=wait_for)

        else:
            # Let's assume it's a scalar
            subarray.fill(value, queue=queue, wait_for=wait_for)

    def __setitem__(self, subscript, value):
        """Set the slice of *self* identified *subscript* to *value*.

        *value* is allowed to be:

        * A :class:`Array` of the same :attr:`shape` and (for now) :attr:`strides`,
          but with potentially different :attr:`dtype`.
        * A :class:`numpy.ndarray` of the same :attr:`shape` and (for now)
          :attr:`strides`, but with potentially different :attr:`dtype`.
        * A scalar.

        Non-scalar broadcasting is not currently supported.

        .. versionadded:: 2013.1
        """
        self.setitem(subscript, value)

    # }}}

# }}}


def as_strided(ary, shape=None, strides=None):
    """Make an :class:`Array` from the given array with the given
    shape and strides.
    """

    # undocumented for the moment

    shape = shape or ary.shape
    strides = strides or ary.strides

    return Array(ary.queue, shape, ary.dtype, allocator=ary.allocator,
            data=ary.data, strides=strides)

# }}}


# {{{ creation helpers

def to_device(queue, ary, allocator=None, async=False):
    """Return a :class:`Array` that is an exact copy of the
    :class:`numpy.ndarray` instance *ary*.

    See :class:`Array` for the meaning of *allocator*.

    .. versionchanged:: 2011.1
        *context* argument was deprecated.
    """

    if _dtype_is_object(ary.dtype):
        raise RuntimeError("to_device does not work on object arrays.")

    result = Array(queue, ary.shape, ary.dtype,
                    allocator=allocator, strides=ary.strides)
    result.set(ary, async=async)
    return result


empty = Array


def zeros(queue, shape, dtype, order="C", allocator=None):
    """Same as :func:`empty`, but the :class:`Array` is zero-initialized before
    being returned.

    .. versionchanged:: 2011.1
        *context* argument was deprecated.
    """

    result = Array(queue, shape, dtype,
            order=order, allocator=allocator)
    zero = np.zeros((), dtype)
    result.fill(zero)
    return result


def empty_like(ary):
    """Make a new, uninitialized :class:`Array` having the same properties
    as *other_ary*.
    """

    return ary._new_with_changes(data=None, offset=0)


def zeros_like(ary):
    """Make a new, zero-initialized :class:`Array` having the same properties
    as *other_ary*.
    """

    result = empty_like(ary)
    zero = np.zeros((), ary.dtype)
    result.fill(zero)
    return result


@elwise_kernel_runner
def _arange_knl(result, start, step):
    return elementwise.get_arange_kernel(
            result.context, result.dtype)


def arange(queue, *args, **kwargs):
    """Create a :class:`Array` filled with numbers spaced `step` apart,
    starting from `start` and ending at `stop`.

    For floating point arguments, the length of the result is
    `ceil((stop - start)/step)`.  This rule may result in the last
    element of the result being greater than `stop`.

    *dtype*, if not specified, is taken as the largest common type
    of *start*, *stop* and *step*.

    .. versionchanged:: 2011.1
        *context* argument was deprecated.

    .. versionchanged:: 2011.2
        *allocator* keyword argument was added.
    """

    # argument processing -----------------------------------------------------

    # Yuck. Thanks, numpy developers. ;)
    from pytools import Record

    class Info(Record):
        pass

    explicit_dtype = False

    inf = Info()
    inf.start = None
    inf.stop = None
    inf.step = None
    inf.dtype = None
    inf.allocator = None
    inf.wait_for = []

    if isinstance(args[-1], np.dtype):
        inf.dtype = args[-1]
        args = args[:-1]
        explicit_dtype = True

    argc = len(args)
    if argc == 0:
        raise ValueError("stop argument required")
    elif argc == 1:
        inf.stop = args[0]
    elif argc == 2:
        inf.start = args[0]
        inf.stop = args[1]
    elif argc == 3:
        inf.start = args[0]
        inf.stop = args[1]
        inf.step = args[2]
    else:
        raise ValueError("too many arguments")

    admissible_names = ["start", "stop", "step", "dtype", "allocator"]
    for k, v in kwargs.iteritems():
        if k in admissible_names:
            if getattr(inf, k) is None:
                setattr(inf, k, v)
                if k == "dtype":
                    explicit_dtype = True
            else:
                raise ValueError(
                        "may not specify '%s' by position and keyword" % k)
        else:
            raise ValueError("unexpected keyword argument '%s'" % k)

    if inf.start is None:
        inf.start = 0
    if inf.step is None:
        inf.step = 1
    if inf.dtype is None:
        inf.dtype = np.array([inf.start, inf.stop, inf.step]).dtype

    # actual functionality ----------------------------------------------------
    dtype = np.dtype(inf.dtype)
    start = dtype.type(inf.start)
    step = dtype.type(inf.step)
    stop = dtype.type(inf.stop)
    wait_for = inf.wait_for

    if not explicit_dtype:
        raise TypeError("arange requires a dtype argument")

    from math import ceil
    size = int(ceil((stop-start)/step))

    result = Array(queue, (size,), dtype, allocator=inf.allocator)
    result.events.append(
            _arange_knl(result, start, step, queue=queue, wait_for=wait_for))
    return result

# }}}


# {{{ take/put/concatenate/diff

@elwise_kernel_runner
def _take(result, ary, indices):
    return elementwise.get_take_kernel(
            result.context, result.dtype, indices.dtype)


def take(a, indices, out=None, queue=None, wait_for=None):
    """Return the :class:`Array` ``[a[indices[0]], ..., a[indices[n]]]``.
    For the moment, *a* must be a type that can be bound to a texture.
    """

    queue = queue or a.queue
    if out is None:
        out = Array(queue, indices.shape, a.dtype, allocator=a.allocator)

    assert len(indices.shape) == 1
    out.events.append(
            _take(out, a, indices, queue=queue, wait_for=wait_for))
    return out


def multi_take(arrays, indices, out=None, queue=None):
    if not len(arrays):
        return []

    assert len(indices.shape) == 1

    from pytools import single_valued
    a_dtype = single_valued(a.dtype for a in arrays)
    a_allocator = arrays[0].dtype
    context = indices.context
    queue = queue or indices.queue

    vec_count = len(arrays)

    if out is None:
        out = [Array(context, queue, indices.shape, a_dtype,
            allocator=a_allocator)
                for i in range(vec_count)]
    else:
        if len(out) != len(arrays):
            raise ValueError("out and arrays must have the same length")

    chunk_size = _builtin_min(vec_count, 10)

    def make_func_for_chunk_size(chunk_size):
        knl = elementwise.get_take_kernel(
                indices.context, a_dtype, indices.dtype,
                vec_count=chunk_size)
        knl.set_block_shape(*indices._block)
        return knl

    knl = make_func_for_chunk_size(chunk_size)

    for start_i in range(0, len(arrays), chunk_size):
        chunk_slice = slice(start_i, start_i+chunk_size)

        if start_i + chunk_size > vec_count:
            knl = make_func_for_chunk_size(vec_count-start_i)

        gs, ls = indices.get_sizes(queue,
                knl.get_work_group_info(
                    cl.kernel_work_group_info.WORK_GROUP_SIZE,
                    queue.device))

        knl(queue, gs, ls,
                indices.data,
                *([o.data for o in out[chunk_slice]]
                    + [i.data for i in arrays[chunk_slice]]
                    + [indices.size]))

    return out


def multi_take_put(arrays, dest_indices, src_indices, dest_shape=None,
        out=None, queue=None, src_offsets=None):
    if not len(arrays):
        return []

    from pytools import single_valued
    a_dtype = single_valued(a.dtype for a in arrays)
    a_allocator = arrays[0].allocator
    context = src_indices.context
    queue = queue or src_indices.queue

    vec_count = len(arrays)

    if out is None:
        out = [Array(queue, dest_shape, a_dtype, allocator=a_allocator)
                for i in range(vec_count)]
    else:
        if a_dtype != single_valued(o.dtype for o in out):
            raise TypeError("arrays and out must have the same dtype")
        if len(out) != vec_count:
            raise ValueError("out and arrays must have the same length")

    if src_indices.dtype != dest_indices.dtype:
        raise TypeError(
                "src_indices and dest_indices must have the same dtype")

    if len(src_indices.shape) != 1:
        raise ValueError("src_indices must be 1D")

    if src_indices.shape != dest_indices.shape:
        raise ValueError(
                "src_indices and dest_indices must have the same shape")

    if src_offsets is None:
        src_offsets_list = []
    else:
        src_offsets_list = src_offsets
        if len(src_offsets) != vec_count:
            raise ValueError(
                    "src_indices and src_offsets must have the same length")

    max_chunk_size = 10

    chunk_size = _builtin_min(vec_count, max_chunk_size)

    def make_func_for_chunk_size(chunk_size):
        return elementwise.get_take_put_kernel(context,
                a_dtype, src_indices.dtype,
                with_offsets=src_offsets is not None,
                vec_count=chunk_size)

    knl = make_func_for_chunk_size(chunk_size)

    for start_i in range(0, len(arrays), chunk_size):
        chunk_slice = slice(start_i, start_i+chunk_size)

        if start_i + chunk_size > vec_count:
            knl = make_func_for_chunk_size(vec_count-start_i)

        gs, ls = src_indices.get_sizes(queue,
                knl.get_work_group_info(
                    cl.kernel_work_group_info.WORK_GROUP_SIZE,
                    queue.device))

        from pytools import flatten
        knl(queue, gs, ls,
                *([o.data for o in out[chunk_slice]]
                    + [dest_indices.base_data,
                        dest_indices.offset,
                        src_indices.base_data,
                        src_indices.offset]
                    + list(flatten(
                        (i.base_data, i.offset)
                        for i in arrays[chunk_slice]))
                    + src_offsets_list[chunk_slice]
                    + [src_indices.size]))

    return out


def multi_put(arrays, dest_indices, dest_shape=None, out=None, queue=None,
        wait_for=None):
    if not len(arrays):
        return []

    from pytools import single_valued
    a_dtype = single_valued(a.dtype for a in arrays)
    a_allocator = arrays[0].allocator
    context = dest_indices.context
    queue = queue or dest_indices.queue

    vec_count = len(arrays)

    if out is None:
        out = [Array(queue, dest_shape, a_dtype,
            allocator=a_allocator, queue=queue)
            for i in range(vec_count)]
    else:
        if a_dtype != single_valued(o.dtype for o in out):
            raise TypeError("arrays and out must have the same dtype")
        if len(out) != vec_count:
            raise ValueError("out and arrays must have the same length")

    if len(dest_indices.shape) != 1:
        raise ValueError("dest_indices must be 1D")

    chunk_size = _builtin_min(vec_count, 10)

    def make_func_for_chunk_size(chunk_size):
        knl = elementwise.get_put_kernel(
                context,
                a_dtype, dest_indices.dtype, vec_count=chunk_size)
        return knl

    knl = make_func_for_chunk_size(chunk_size)

    for start_i in range(0, len(arrays), chunk_size):
        chunk_slice = slice(start_i, start_i+chunk_size)

        if start_i + chunk_size > vec_count:
            knl = make_func_for_chunk_size(vec_count-start_i)

        gs, ls = dest_indices.get_sizes(queue,
                knl.get_work_group_info(
                    cl.kernel_work_group_info.WORK_GROUP_SIZE,
                    queue.device))

        from pytools import flatten
        evt = knl(queue, gs, ls,
                *(
                    list(flatten(
                        (o.base_data, o.offset)
                        for o in out[chunk_slice]))
                    + [dest_indices.base_data, dest_indices.offset]
                    + list(flatten(
                        (i.base_data, i.offset)
                        for i in arrays[chunk_slice]))
                    + [dest_indices.size]),
                **dict(wait_for=wait_for))

        # FIXME should wait on incoming events

        for o in out[chunk_slice]:
            o.events.append(evt)

    return out


def concatenate(arrays, axis=0, queue=None, allocator=None):
    """
    .. versionadded:: 2013.1
    """
    # {{{ find properties of result array

    shape = None

    for i_ary, ary in enumerate(arrays):
        queue = queue or ary.queue
        allocator = allocator or ary.allocator

        if shape is None:
            # first array
            shape = list(ary.shape)
        else:
            if len(ary.shape) != len(shape):
                raise ValueError("%d'th array has different number of axes "
                        "(shold have %d, has %d)"
                        % (i_ary, len(ary.shape), len(shape)))

            ary_shape_list = list(ary.shape)
            if (ary_shape_list[:axis] != shape[:axis]
                    or ary_shape_list[axis+1:] != shape[axis+1:]):
                raise ValueError("%d'th array has residual not matching "
                        "other arrays" % i_ary)

            shape[axis] += ary.shape[axis]

    # }}}

    shape = tuple(shape)
    dtype = np.find_common_type([ary.dtype for ary in arrays], [])
    result = empty(queue, shape, dtype, allocator=allocator)

    full_slice = (slice(None),) * len(shape)

    base_idx = 0
    for ary in arrays:
        my_len = ary.shape[axis]
        result.setitem(
                full_slice[:axis]
                + (slice(base_idx, base_idx+my_len),)
                + full_slice[axis+1:],
                ary)

        base_idx += my_len

    return result


@elwise_kernel_runner
def _diff(result, array):
    return elementwise.get_diff_kernel(array.context, array.dtype)


def diff(array, queue=None, allocator=None):
    """
    .. versionadded:: 2013.2
    """

    if len(array.shape) != 1:
        raise ValueError("multi-D arrays are not supported")

    n, = array.shape

    queue = queue or array.queue
    allocator = allocator or array.allocator

    result = empty(queue, (n-1,), array.dtype, allocator=allocator)
    _diff(result, array, queue=queue)
    return result

# }}}


# {{{ conditionals

@elwise_kernel_runner
def _if_positive(result, criterion, then_, else_):
    return elementwise.get_if_positive_kernel(
            result.context, criterion.dtype, then_.dtype)


def if_positive(criterion, then_, else_, out=None, queue=None):
    """Return an array like *then_*, which, for the element at index *i*,
    contains *then_[i]* if *criterion[i]>0*, else *else_[i]*.
    """

    if not (criterion.shape == then_.shape == else_.shape):
        raise ValueError("shapes do not match")

    if not (then_.dtype == else_.dtype):
        raise ValueError("dtypes do not match")

    if out is None:
        out = empty_like(then_)
    _if_positive(out, criterion, then_, else_, queue=queue)
    return out


def maximum(a, b, out=None, queue=None):
    """Return the elementwise maximum of *a* and *b*."""

    # silly, but functional
    return if_positive(a.mul_add(1, b, -1, queue=queue), a, b,
            queue=queue, out=out)


def minimum(a, b, out=None, queue=None):
    """Return the elementwise minimum of *a* and *b*."""
    # silly, but functional
    return if_positive(a.mul_add(1, b, -1, queue=queue), b, a,
            queue=queue, out=out)

# }}}


# {{{ reductions
_builtin_sum = sum
_builtin_min = min
_builtin_max = max


def sum(a, dtype=None, queue=None):
    """
    .. versionadded:: 2011.1
    """
    from pyopencl.reduction import get_sum_kernel
    krnl = get_sum_kernel(a.context, dtype, a.dtype)
    return krnl(a, queue=queue)


def dot(a, b, dtype=None, queue=None):
    """
    .. versionadded:: 2011.1
    """
    from pyopencl.reduction import get_dot_kernel
    krnl = get_dot_kernel(a.context, dtype, a.dtype, b.dtype)
    return krnl(a, b, queue=queue)


def vdot(a, b, dtype=None, queue=None):
    """Like :func:`numpy.vdot`.

    .. versionadded:: 2013.1
    """
    from pyopencl.reduction import get_dot_kernel
    krnl = get_dot_kernel(a.context, dtype, a.dtype, b.dtype,
            conjugate_first=True)
    return krnl(a, b, queue=queue)


def subset_dot(subset, a, b, dtype=None, queue=None):
    """
    .. versionadded:: 2011.1
    """
    from pyopencl.reduction import get_subset_dot_kernel
    krnl = get_subset_dot_kernel(
            a.context, dtype, subset.dtype, a.dtype, b.dtype)
    return krnl(subset, a, b, queue=queue)


def _make_minmax_kernel(what):
    def f(a, queue=None):
        from pyopencl.reduction import get_minmax_kernel
        krnl = get_minmax_kernel(a.context, what, a.dtype)
        return krnl(a,  queue=queue)

    return f

min = _make_minmax_kernel("min")
min.__doc__ = """
    .. versionadded:: 2011.1
    """

max = _make_minmax_kernel("max")
max.__doc__ = """
    .. versionadded:: 2011.1
    """


def _make_subset_minmax_kernel(what):
    def f(subset, a, queue=None):
        from pyopencl.reduction import get_subset_minmax_kernel
        krnl = get_subset_minmax_kernel(a.context, what, a.dtype, subset.dtype)
        return krnl(subset, a,  queue=queue)

    return f

subset_min = _make_subset_minmax_kernel("min")
subset_min.__doc__ = """.. versionadded:: 2011.1"""
subset_max = _make_subset_minmax_kernel("max")
subset_max.__doc__ = """.. versionadded:: 2011.1"""

# }}}


# {{{ scans

def cumsum(a, output_dtype=None, queue=None,
        wait_for=None, return_event=False):
    # undocumented for now

    """
    .. versionadded:: 2013.1
    """

    if output_dtype is None:
        output_dtype = a.dtype

    result = a._new_like_me(output_dtype)

    from pyopencl.scan import get_cumsum_kernel
    krnl = get_cumsum_kernel(a.context, a.dtype, output_dtype)
    evt = krnl(a, result, queue=queue, wait_for=wait_for)

    if return_event:
        return evt, result
    else:
        return result

# }}}

# vim: foldmethod=marker

########NEW FILE########
__FILENAME__ = cache
"""PyOpenCL compiler cache."""

from __future__ import division

__copyright__ = "Copyright (C) 2011 Andreas Kloeckner"

__license__ = """
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

import pyopencl._cl as _cl
import re
import sys
import os
from pytools import Record

try:
    import hashlib
    new_hash = hashlib.md5
except ImportError:
    # for Python << 2.5
    import md5
    new_hash = md5.new


def _erase_dir(dir):
    from os import listdir, unlink, rmdir
    from os.path import join
    for name in listdir(dir):
        unlink(join(dir, name))
    rmdir(dir)


def update_checksum(checksum, obj):
    if isinstance(obj, unicode):
        checksum.update(obj.encode("utf8"))
    else:
        checksum.update(obj)


# {{{ cleanup

class CleanupBase(object):
    pass


class CleanupManager(CleanupBase):
    def __init__(self):
        self.cleanups = []

    def register(self, c):
        self.cleanups.insert(0, c)

    def clean_up(self):
        for c in self.cleanups:
            c.clean_up()

    def error_clean_up(self):
        for c in self.cleanups:
            c.error_clean_up()


class CacheLockManager(CleanupBase):
    def __init__(self, cleanup_m, cache_dir):
        if cache_dir is not None:
            self.lock_file = os.path.join(cache_dir, "lock")

            attempts = 0
            while True:
                try:
                    self.fd = os.open(self.lock_file,
                            os.O_CREAT | os.O_WRONLY | os.O_EXCL)
                    break
                except OSError:
                    pass

                from time import sleep
                sleep(1)

                attempts += 1

                if attempts > 10:
                    from warnings import warn
                    warn("could not obtain cache lock--delete '%s' if necessary"
                            % self.lock_file)

            cleanup_m.register(self)

    def clean_up(self):
        import os
        os.close(self.fd)
        os.unlink(self.lock_file)

    def error_clean_up(self):
        pass


class ModuleCacheDirManager(CleanupBase):
    def __init__(self, cleanup_m, path):
        from os import mkdir

        self.path = path
        try:
            mkdir(self.path)
            cleanup_m.register(self)
            self.existed = False
        except OSError:
            self.existed = True

    def sub(self, n):
        from os.path import join
        return join(self.path, n)

    def reset(self):
        import os
        _erase_dir(self.path)
        os.mkdir(self.path)

    def clean_up(self):
        pass

    def error_clean_up(self):
        _erase_dir(self.path)

# }}}


# {{{ #include dependency handling

C_INCLUDE_RE = re.compile(r'^\s*\#\s*include\s+[<"](.+)[">]\s*$',
        re.MULTILINE)


def get_dependencies(src, include_path):
    result = {}

    from os.path import realpath, join

    def _inner(src):
        for match in C_INCLUDE_RE.finditer(src):
            included = match.group(1)

            found = False
            for ipath in include_path:
                included_file_name = realpath(join(ipath, included))

                if included_file_name not in result:
                    try:
                        src_file = open(included_file_name, "rt")
                    except IOError:
                        continue

                    try:
                        included_src = src_file.read()
                    finally:
                        src_file.close()

                    # jrevent infinite recursion if some header file appears to
                    # include itself
                    result[included_file_name] = None

                    checksum = new_hash()
                    update_checksum(checksum, included_src)
                    _inner(included_src)

                    result[included_file_name] = (
                            os.stat(included_file_name).st_mtime,
                            checksum.hexdigest(),
                            )

                    found = True
                    break  # stop searching the include path

            if not found:
                pass

    _inner(src)

    result = list((name,) + vals for name, vals in result.iteritems())
    result.sort()

    return result


def get_file_md5sum(fname):
    checksum = new_hash()
    inf = open(fname)
    try:
        contents = inf.read()
    finally:
        inf.close()
    update_checksum(checksum, contents)
    return checksum.hexdigest()


def check_dependencies(deps):
    for name, date, md5sum in deps:
        try:
            possibly_updated = os.stat(name).st_mtime != date
        except OSError:
            return False
        else:
            if possibly_updated and md5sum != get_file_md5sum(name):
                return False

    return True

# }}}


# {{{ key generation

def get_device_cache_id(device):
    from pyopencl.version import VERSION
    platform = device.platform
    return (VERSION,
            platform.vendor, platform.name, platform.version,
            device.vendor, device.name, device.version, device.driver_version)


def get_cache_key(device, options, src):
    checksum = new_hash()
    update_checksum(checksum, src)
    update_checksum(checksum, " ".join(options))
    update_checksum(checksum, str(get_device_cache_id(device)))
    return checksum.hexdigest()

# }}}


def retrieve_from_cache(cache_dir, cache_key):
    class _InvalidInfoFile(RuntimeError):
        pass

    from os.path import join, isdir
    module_cache_dir = join(cache_dir, cache_key)
    if not isdir(module_cache_dir):
        return None

    cleanup_m = CleanupManager()
    try:
        try:
            CacheLockManager(cleanup_m, cache_dir)

            mod_cache_dir_m = ModuleCacheDirManager(cleanup_m, module_cache_dir)
            info_path = mod_cache_dir_m.sub("info")
            binary_path = mod_cache_dir_m.sub("binary")

            # {{{ load info file

            try:
                from cPickle import load

                try:
                    info_file = open(info_path, "rb")
                except IOError:
                    raise _InvalidInfoFile()

                try:
                    try:
                        info = load(info_file)
                    except EOFError:
                        raise _InvalidInfoFile()
                finally:
                    info_file.close()

            except _InvalidInfoFile:
                mod_cache_dir_m.reset()
                from warnings import warn
                warn("PyOpenCL encountered an invalid info file for cache key %s"
                        % cache_key)
                return None

            # }}}

            # {{{ load binary

            binary_file = open(binary_path, "rb")
            try:
                binary = binary_file.read()
            finally:
                binary_file.close()

            # }}}

            if check_dependencies(info.dependencies):
                return binary, info.log
            else:
                mod_cache_dir_m.reset()

        except:
            cleanup_m.error_clean_up()
            raise
    finally:
        cleanup_m.clean_up()


# {{{ top-level driver

class _SourceInfo(Record):
    pass


def _create_built_program_from_source_cached(ctx, src, options, devices, cache_dir):
    from os.path import join

    include_path = ["."]

    option_idx = 0
    while option_idx < len(options):
        option = options[option_idx].strip()
        if option.startswith("-I") or option.startswith("/I"):
            if len(option) == 2:
                if option_idx+1 < len(options):
                    include_path.append(options[option_idx+1])
                option_idx += 2
            else:
                include_path.append(option[2:].lstrip())
                option_idx += 1
        else:
            option_idx += 1

    if cache_dir is None:
        from tempfile import gettempdir
        import getpass
        cache_dir = join(gettempdir(),
                "pyopencl-compiler-cache-v2-uid%s-py%s" % (
                    getpass.getuser(), ".".join(str(i) for i in sys.version_info)))

    # {{{ ensure cache directory exists

    try:
        os.mkdir(cache_dir)
    except OSError, e:
        from errno import EEXIST
        if e.errno != EEXIST:
            raise

    # }}}

    if devices is None:
        devices = ctx.devices

    cache_keys = [get_cache_key(device, options, src) for device in devices]

    binaries = []
    to_be_built_indices = []
    logs = []
    for i, (device, cache_key) in enumerate(zip(devices, cache_keys)):
        cache_result = retrieve_from_cache(cache_dir, cache_key)

        if cache_result is None:
            to_be_built_indices.append(i)
            binaries.append(None)
            logs.append(None)
        else:
            binary, log = cache_result
            binaries.append(binary)
            logs.append(log)

    message = (75*"="+"\n").join(
            "Build on %s succeeded, but said:\n\n%s" % (dev, log)
            for dev, log in zip(devices, logs)
            if log is not None and log.strip())

    if message:
        from pyopencl import compiler_output
        compiler_output(
                "Built kernel retrieved from cache. Original from-source "
                "build had warnings:\n"+message)

    # {{{ build on the build-needing devices, in one go

    result = None
    already_built = False

    if to_be_built_indices:
        # defeat implementation caches:
        from uuid import uuid4
        src = src + "\n\n__constant int pyopencl_defeat_cache_%s = 0;" % (
                uuid4().hex)

        prg = _cl._Program(ctx, src)
        prg.build(options, [devices[i] for i in to_be_built_indices])

        prg_devs = prg.get_info(_cl.program_info.DEVICES)
        prg_bins = prg.get_info(_cl.program_info.BINARIES)
        prg_logs = prg._get_build_logs()

        for dest_index in to_be_built_indices:
            dev = devices[dest_index]
            src_index = prg_devs.index(dev)
            binaries[dest_index] = prg_bins[src_index]
            _, logs[dest_index] = prg_logs[src_index]

        if len(to_be_built_indices) == len(devices):
            # Important special case: if code for all devices was built,
            # then we may simply use the program that we just built as the
            # final result.

            result = prg
            already_built = True

    if result is None:
        result = _cl._Program(ctx, devices, binaries)

    # }}}

    # {{{ save binaries to cache

    if to_be_built_indices:
        cleanup_m = CleanupManager()
        try:
            try:
                CacheLockManager(cleanup_m, cache_dir)

                for i in to_be_built_indices:
                    cache_key = cache_keys[i]
                    device = devices[i]
                    binary = binaries[i]

                    mod_cache_dir_m = ModuleCacheDirManager(cleanup_m,
                            join(cache_dir, cache_key))
                    info_path = mod_cache_dir_m.sub("info")
                    binary_path = mod_cache_dir_m.sub("binary")
                    source_path = mod_cache_dir_m.sub("source.cl")

                    outf = open(source_path, "wt")
                    outf.write(src)
                    outf.close()

                    outf = open(binary_path, "wb")
                    outf.write(binary)
                    outf.close()

                    from cPickle import dump
                    info_file = open(info_path, "wb")
                    dump(_SourceInfo(
                        dependencies=get_dependencies(src, include_path),
                        log=logs[i]), info_file)
                    info_file.close()

            except:
                cleanup_m.error_clean_up()
                raise
        finally:
            cleanup_m.clean_up()

    # }}}

    return result, already_built


def create_built_program_from_source_cached(ctx, src, options=[], devices=None,
        cache_dir=None):
    try:
        if cache_dir is not False:
            prg, already_built = _create_built_program_from_source_cached(
                    ctx, src, options, devices, cache_dir)
        else:
            prg = _cl._Program(ctx, src)
            already_built = False

    except Exception, e:
        raise
        from pyopencl import Error
        if (isinstance(e, Error)
                and e.code == _cl.status_code.BUILD_PROGRAM_FAILURE):
            # no need to try again
            raise

        from warnings import warn
        from traceback import format_exc
        warn("PyOpenCL compiler caching failed with an exception:\n"
                "[begin exception]\n%s[end exception]"
                % format_exc())

        prg = _cl._Program(ctx, src)
        already_built = False

    if not already_built:
        prg.build(options, devices)

    return prg

# }}}

# vim: foldmethod=marker

########NEW FILE########
__FILENAME__ = capture_call
from __future__ import with_statement, division

__copyright__ = "Copyright (C) 2013 Andreas Kloeckner"

__license__ = """
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""


import pyopencl as cl
import numpy as np
from pytools.py_codegen import PythonCodeGenerator, Indentation


def capture_kernel_call(kernel, filename, queue, g_size, l_size, *args, **kwargs):
    try:
        source = kernel._source
    except AttributeError:
        raise RuntimeError("cannot capture call, kernel source not available")

    if source is None:
        raise RuntimeError("cannot capture call, kernel source not available")

    cg = PythonCodeGenerator()

    cg("# generated by pyopencl.capture_call")
    cg("")
    cg("import numpy as np")
    cg("import pyopencl as cl")
    cg("from base64 import b64decode")
    cg("from zlib import decompress")
    cg("mf = cl.mem_flags")
    cg("")

    cg('CODE = r"""//CL//')
    for l in source.split("\n"):
        cg(l)
    cg('"""')

    # {{{ invocation

    arg_data = []

    cg("")
    cg("")
    cg("def main():")
    with Indentation(cg):
        cg("ctx = cl.create_some_context()")
        cg("queue = cl.CommandQueue(ctx)")
        cg("")

        kernel_args = []

        for i, arg in enumerate(args):
            if isinstance(arg, cl.Buffer):
                buf = bytearray(arg.size)
                cl.enqueue_copy(queue, buf, arg)
                arg_data.append(("arg%d_data" % i, buf))
                cg("arg%d = cl.Buffer(ctx, "
                        "mf.READ_WRITE | cl.mem_flags.COPY_HOST_PTR,"
                        % i)
                cg("    hostbuf=decompress(b64decode(arg%d_data)))"
                        % i)
                kernel_args.append("arg%d" % i)
            elif isinstance(arg, (int, float)):
                kernel_args.append(repr(arg))
            elif isinstance(arg, np.integer):
                kernel_args.append("np.%s(%s)" % (
                    arg.dtype.type.__name__, repr(int(arg))))
            elif isinstance(arg, np.floating):
                kernel_args.append("np.%s(%s)" % (
                    arg.dtype.type.__name__, repr(float(arg))))
            elif isinstance(arg, np.complexfloating):
                kernel_args.append("np.%s(%s)" % (
                    arg.dtype.type.__name__, repr(complex(arg))))
            else:
                try:
                    arg_buf = buffer(arg)
                except:
                    raise RuntimeError("cannot capture: "
                            "unsupported arg nr %d (0-based)" % i)

                arg_data.append(("arg%d_data" % i, arg_buf))
                kernel_args.append("decompress(b64decode(arg%d_data))" % i)

        cg("")

        g_times_l = kwargs.get("g_times_l", False)
        if g_times_l:
            dim = max(len(g_size), len(l_size))
            l_size = l_size + (1,) * (dim-len(l_size))
            g_size = g_size + (1,) * (dim-len(g_size))
            g_size = tuple(
                    gs*ls for gs, ls in zip(g_size, l_size))

        global_offset = kwargs.get("global_offset", None)
        if global_offset is not None:
            kernel_args.append("global_offset=%s" % repr(global_offset))

        cg("prg = cl.Program(ctx, CODE).build()")
        cg("knl = prg.%s" % kernel.function_name)
        if hasattr(kernel, "_arg_type_chars"):
            cg("knl._arg_type_chars = %s" % repr(kernel._arg_type_chars))
        cg("knl(queue, %s, %s," % (repr(g_size), repr(l_size)))
        cg("    %s)" % ", ".join(kernel_args))
        cg("")
        cg("queue.finish()")

    # }}}

    # {{{ data

    from zlib import compress
    from base64 import b64encode
    cg("")
    line_len = 70

    for name, val in arg_data:
        cg("%s = (" % name)
        with Indentation(cg):
            val = str(b64encode(compress(buffer(val))))
            i = 0
            while i < len(val):
                cg(repr(val[i:i+line_len]))
                i += line_len

            cg(")")

    # }}}

    # {{{ file trailer

    cg("")
    cg("if __name__ == \"__main__\":")
    with Indentation(cg):
        cg("main()")
    cg("")

    cg("# vim: filetype=pyopencl")

    # }}}

    with open(filename, "w") as outf:
        outf.write(cg.get())

########NEW FILE########
__FILENAME__ = performance
from __future__ import division

__copyright__ = "Copyright (C) 2009 Andreas Kloeckner"

__license__ = """
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

import pyopencl as cl
import numpy as np




# {{{ timing helpers

class Timer:
    def __init__(self, queue):
        self.queue = queue

    def start(self):
        pass

    def stop(self):
        pass

    def add_event(self, evt):
        pass

    def get_elapsed(self):
        pass




class WallTimer(Timer):
    def start(self):
        from time import time
        self.queue.finish()
        self.start = time()

    def stop(self):
        from time import time
        self.queue.finish()
        self.end = time()

    def get_elapsed(self):
        return self.end-self.start




def _get_time(queue, f, timer_factory=None, desired_duration=0.1,
        warmup_rounds=3):

    if timer_factory is None:
        timer_factory = WallTimer

    count = 1

    while True:
        timer = timer_factory(queue)

        for i in xrange(warmup_rounds):
            f()
        warmup_rounds = 0

        timer.start()
        for i in xrange(count):
            timer.add_event(f())
        timer.stop()

        elapsed = timer.get_elapsed()
        if elapsed < desired_duration:
            if elapsed == 0:
                count *= 5
            else:
                new_count = int(desired_duration/elapsed)

                new_count = max(2*count, new_count)
                new_count = min(10*count, new_count)
                count = new_count

        else:
            return elapsed/count

# }}}




# {{{ transfer measurements

class HostDeviceTransferBase(object):
    def __init__(self, queue, block_size):
        self.queue = queue
        self.host_buf = np.empty(block_size, dtype=np.uint8)
        self.dev_buf = cl.Buffer(queue.context, cl.mem_flags.READ_WRITE, block_size)

class HostToDeviceTransfer(HostDeviceTransferBase):
    def do(self):
        return cl.enqueue_copy(self. queue, self.dev_buf, self.host_buf)

class DeviceToHostTransfer(HostDeviceTransferBase):
    def do(self):
        return cl.enqueue_copy(self. queue, self.host_buf, self.dev_buf)

class DeviceToDeviceTransfer(object):
    def __init__(self, queue, block_size):
        self.queue = queue
        self.dev_buf_1 = cl.Buffer(queue.context, cl.mem_flags.READ_WRITE, block_size)
        self.dev_buf_2 = cl.Buffer(queue.context, cl.mem_flags.READ_WRITE, block_size)

    def do(self):
        return cl.enqueue_copy(self. queue, self.dev_buf_2, self.dev_buf_1)

class HostToDeviceTransfer(HostDeviceTransferBase):
    def do(self):
        return cl.enqueue_copy(self. queue, self.dev_buf, self.host_buf)


def transfer_latency(queue, transfer_type, timer_factory=None):
    transfer = transfer_type(queue, 1)
    return _get_time(queue, transfer.do, timer_factory=timer_factory)

def transfer_bandwidth(queue, transfer_type, block_size, timer_factory=None):
    """Measures one-sided bandwidth."""

    transfer = transfer_type(queue, block_size)
    return block_size/_get_time(queue, transfer.do, timer_factory=timer_factory)

# }}}




def get_profiling_overhead(ctx, timer_factory=None):
    no_prof_queue = cl.CommandQueue(ctx)
    transfer = DeviceToDeviceTransfer(no_prof_queue, 1)
    no_prof_time = _get_time(no_prof_queue, transfer.do, timer_factory=timer_factory)

    prof_queue = cl.CommandQueue(ctx,
            properties=cl.command_queue_properties.PROFILING_ENABLE)
    transfer = DeviceToDeviceTransfer(prof_queue, 1)
    prof_time = _get_time(prof_queue, transfer.do, timer_factory=timer_factory)

    return prof_time - no_prof_time, prof_time

def get_empty_kernel_time(queue, timer_factory=None):
    prg = cl.Program(queue.context, """
        __kernel void empty()
        { }
        """).build()

    knl = prg.empty

    def f():
        knl(queue, (1,), None)

    return _get_time(queue, f, timer_factory=timer_factory)

def _get_full_machine_kernel_rate(queue, src, args, name="benchmark", timer_factory=None):
    prg = cl.Program(queue.context, src).build()

    knl = getattr(prg, name)

    dev = queue.device
    global_size = 4 * dev.max_compute_units
    def f():
        knl(queue, (global_size,), None, *args)

    rates = []
    num_dips = 0

    while True:
        elapsed = _get_time(queue, f, timer_factory=timer_factory)
        rate = global_size/elapsed
        print global_size, rate, num_dips

        keep_trying = not rates

        if rates and rate > 1.05*max(rates): # big improvement
            keep_trying = True
            num_dips = 0

        if rates and rate < 0.9*max(rates) and num_dips < 3: # big dip
            keep_trying = True
            num_dips += 1

        if keep_trying:
            global_size *= 2
            last_rate = rate
            rates.append(rate)
        else:
            rates.append(rate)
            return max(rates)

def get_add_rate(queue, type="float", timer_factory=None):
    return 50*10*_get_full_machine_kernel_rate(queue, """
        typedef %(op_t)s op_t;
        __kernel void benchmark()
        {
            local op_t tgt[1024];
            op_t val = get_global_id(0);

            for (int i = 0; i < 10; ++i)
            {
                val += val; val += val; val += val; val += val; val += val;
                val += val; val += val; val += val; val += val; val += val;

                val += val; val += val; val += val; val += val; val += val;
                val += val; val += val; val += val; val += val; val += val;

                val += val; val += val; val += val; val += val; val += val;
                val += val; val += val; val += val; val += val; val += val;

                val += val; val += val; val += val; val += val; val += val;
                val += val; val += val; val += val; val += val; val += val;

                val += val; val += val; val += val; val += val; val += val;
                val += val; val += val; val += val; val += val; val += val;
            }
            tgt[get_local_id(0)] = val;
        }
        """ % dict(op_t=type), ())




# vim: foldmethod=marker:filetype=pyopencl

########NEW FILE########
__FILENAME__ = clmath
__copyright__ = "Copyright (C) 2009 Andreas Kloeckner"

__license__ = """
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

import pyopencl.array as cl_array
import pyopencl.elementwise as elementwise
from pyopencl.array import _get_common_dtype
import numpy as np


def _make_unary_array_func(name):
    @cl_array.elwise_kernel_runner
    def knl_runner(result, arg):
        if arg.dtype.kind == "c":
            from pyopencl.elementwise import complex_dtype_to_name
            fname = "%s_%s" % (complex_dtype_to_name(arg.dtype), name)
        else:
            fname = name

        return elementwise.get_unary_func_kernel(
                result.context, fname, arg.dtype)

    def f(array, queue=None):
        result = array._new_like_me(queue=queue)
        knl_runner(result, array, queue=queue)
        return result

    return f

# See table 6.8 in the CL 1.1 spec
acos = _make_unary_array_func("acos")
acosh = _make_unary_array_func("acosh")
acospi = _make_unary_array_func("acospi")

asin = _make_unary_array_func("asin")
asinh = _make_unary_array_func("asinh")
asinpi = _make_unary_array_func("asinpi")


@cl_array.elwise_kernel_runner
def _atan2(result, arg1, arg2):
    return elementwise.get_float_binary_func_kernel(
        result.context, "atan2", arg1.dtype, arg2.dtype, result.dtype)


@cl_array.elwise_kernel_runner
def _atan2pi(result, arg1, arg2):
    return elementwise.get_float_binary_func_kernel(
        result.context, "atan2pi", arg1.dtype, arg2.dtype, result.dtype)


atan = _make_unary_array_func("atan")


def atan2(y, x, queue=None):
    """
    .. versionadded:: 2013.1
    """
    queue = queue or y.queue
    result = y._new_like_me(_get_common_dtype(y, x, queue))
    _atan2(result, y, x, queue=queue)
    return result


atanh = _make_unary_array_func("atanh")
atanpi = _make_unary_array_func("atanpi")


def atan2pi(y, x, queue=None):
    """
    .. versionadded:: 2013.1
    """
    queue = queue or y.queue
    result = y._new_like_me(_get_common_dtype(y, x, queue))
    _atan2pi(result, y, x, queue=queue)
    return result


cbrt = _make_unary_array_func("cbrt")
ceil = _make_unary_array_func("ceil")
# TODO: copysign

cos = _make_unary_array_func("cos")
cosh = _make_unary_array_func("cosh")
cospi = _make_unary_array_func("cospi")

erfc = _make_unary_array_func("erfc")
erf = _make_unary_array_func("erf")
exp = _make_unary_array_func("exp")
exp2 = _make_unary_array_func("exp2")
exp10 = _make_unary_array_func("exp10")
expm1 = _make_unary_array_func("expm1")

fabs = _make_unary_array_func("fabs")
# TODO: fdim
floor = _make_unary_array_func("floor")
# TODO: fma
# TODO: fmax
# TODO: fmin


@cl_array.elwise_kernel_runner
def _fmod(result, arg, mod):
    return elementwise.get_fmod_kernel(result.context, result.dtype,
                                       arg.dtype, mod.dtype)


def fmod(arg, mod, queue=None):
    """Return the floating point remainder of the division `arg/mod`,
    for each element in `arg` and `mod`."""
    queue = (queue or arg.queue) or mod.queue
    result = arg._new_like_me(_get_common_dtype(arg, mod, queue))
    _fmod(result, arg, mod, queue=queue)
    return result

# TODO: fract


@cl_array.elwise_kernel_runner
def _frexp(sig, expt, arg):
    return elementwise.get_frexp_kernel(sig.context, sig.dtype,
                                        expt.dtype, arg.dtype)


def frexp(arg, queue=None):
    """Return a tuple `(significands, exponents)` such that
    `arg == significand * 2**exponent`.
    """
    sig = arg._new_like_me(queue=queue)
    expt = arg._new_like_me(queue=queue)
    _frexp(sig, expt, arg, queue=queue)
    return sig, expt

# TODO: hypot


ilogb = _make_unary_array_func("ilogb")


@cl_array.elwise_kernel_runner
def _ldexp(result, sig, exp):
    return elementwise.get_ldexp_kernel(result.context, result.dtype,
                                        sig.dtype, exp.dtype)


def ldexp(significand, exponent, queue=None):
    """Return a new array of floating point values composed from the
    entries of `significand` and `exponent`, paired together as
    `result = significand * 2**exponent`.
    """
    result = significand._new_like_me(queue=queue)
    _ldexp(result, significand, exponent)
    return result

lgamma = _make_unary_array_func("lgamma")
# TODO: lgamma_r

log = _make_unary_array_func("log")
log2 = _make_unary_array_func("log2")
log10 = _make_unary_array_func("log10")
log1p = _make_unary_array_func("log1p")
logb = _make_unary_array_func("logb")

# TODO: mad
# TODO: maxmag
# TODO: minmag


@cl_array.elwise_kernel_runner
def _modf(intpart, fracpart, arg):
    return elementwise.get_modf_kernel(intpart.context, intpart.dtype,
                                       fracpart.dtype, arg.dtype)


def modf(arg, queue=None):
    """Return a tuple `(fracpart, intpart)` of arrays containing the
    integer and fractional parts of `arg`.
    """
    intpart = arg._new_like_me(queue=queue)
    fracpart = arg._new_like_me(queue=queue)
    _modf(intpart, fracpart, arg, queue=queue)
    return fracpart, intpart

nan = _make_unary_array_func("nan")

# TODO: nextafter
# TODO: remainder
# TODO: remquo

rint = _make_unary_array_func("rint")
# TODO: rootn
round = _make_unary_array_func("round")

sin = _make_unary_array_func("sin")
# TODO: sincos
sinh = _make_unary_array_func("sinh")
sinpi = _make_unary_array_func("sinpi")

sqrt = _make_unary_array_func("sqrt")

tan = _make_unary_array_func("tan")
tanh = _make_unary_array_func("tanh")
tanpi = _make_unary_array_func("tanpi")
tgamma = _make_unary_array_func("tgamma")
trunc = _make_unary_array_func("trunc")


# no point wrapping half_ or native_

# TODO: table 6.10, integer functions
# TODO: table 6.12, clamp et al

@cl_array.elwise_kernel_runner
def _bessel_jn(result, n, x):
    return elementwise.get_bessel_kernel(result.context, "j", result.dtype,
                                         np.dtype(type(n)), x.dtype)


@cl_array.elwise_kernel_runner
def _bessel_yn(result, n, x):
    return elementwise.get_bessel_kernel(result.context, "y", result.dtype,
                                         np.dtype(type(n)), x.dtype)


def bessel_jn(n, x, queue=None):
    result = x._new_like_me(queue=queue)
    _bessel_jn(result, n, x)
    return result


def bessel_yn(n, x, queue=None):
    result = x._new_like_me(queue=queue)
    _bessel_yn(result, n, x)
    return result

########NEW FILE########
__FILENAME__ = clrandom
# encoding: utf8
from __future__ import division

__copyright__ = "Copyright (C) 2009 Andreas Kloeckner"

__license__ = """
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""


# {{{ documentation

__doc__ = u"""
PyOpenCL now includes and uses the `RANLUXCL random number generator
<https://bitbucket.org/ivarun/ranluxcl/>`_ by Ivar Ursin Nikolaisen.  In
addition to being usable through the convenience functions above, it is
available in any piece of code compiled through PyOpenCL by::

    #include <pyopencl-ranluxcl.cl>

See the `source
<https://github.com/pyopencl/pyopencl/blob/master/src/cl/pyopencl-ranluxcl.cl>`_
for some documentation if you're planning on using RANLUXCL directly.

The RANLUX generator is described in the following two articles. If you use the
generator for scientific purposes, please consider citing them:

* Martin Lüscher, A portable high-quality random number generator for lattice
  field theory simulations, `Computer Physics Communications 79 (1994) 100-110
  <http://dx.doi.org/10.1016/0010-4655(94)90232-1>`_

* F. James, RANLUX: A Fortran implementation of the high-quality pseudorandom
  number generator of Lüscher, `Computer Physics Communications 79 (1994) 111-114
  <http://dx.doi.org/10.1016/0010-4655(94)90233-X>`_
"""

# }}}

import pyopencl as cl
import pyopencl.array as cl_array
from pyopencl.tools import first_arg_dependent_memoize
from pytools import memoize_method

import numpy as np


class RanluxGenerator(object):
    """
    .. versionadded:: 2011.2

    .. attribute:: state

        A :class:`pyopencl.array.Array` containing the state of the generator.

    .. attribute:: nskip

        nskip is an integer which can (optionally) be defined in the kernel
        code as RANLUXCL_NSKIP. If this is done the generator will be faster
        for luxury setting 0 and 1, or when the p-value is manually set to a
        multiple of 24.
    """

    def __init__(self, queue, num_work_items=None,
            luxury=None, seed=None, no_warmup=False,
            use_legacy_init=False, max_work_items=None):
        """
        :param queue: :class:`pyopencl.CommandQueue`, only used for initialization
        :param luxury: the "luxury value" of the generator, and should be 0-4,
            where 0 is fastest and 4 produces the best numbers. It can also be
            >=24, in which case it directly sets the p-value of RANLUXCL.
        :param num_work_items: is the number of generators to initialize,
            usually corresponding to the number of work-items in the NDRange
            RANLUXCL will be used with.  May be `None`, in which case a default
            value is used.
        :param max_work_items: should reflect the maximum number of work-items
            that will be used on any parallel instance of RANLUXCL. So for
            instance if we are launching 5120 work-items on GPU1 and 10240
            work-items on GPU2, GPU1's RANLUXCLTab would be generated by
            calling ranluxcl_intialization with numWorkitems = 5120 while
            GPU2's RANLUXCLTab would use numWorkitems = 10240. However
            maxWorkitems must be at least 10240 for both GPU1 and GPU2, and it
            must be set to the same value for both. (may be `None`)

        .. versionchanged:: 2013.1
            Added default value for `num_work_items`.
        """

        if luxury is None:
            luxury = 4

        if num_work_items is None:
            if queue.device.type & cl.device_type.CPU:
                num_work_items = 8 * queue.device.max_compute_units
            else:
                num_work_items = 64 * queue.device.max_compute_units

        if seed is None:
            from time import time
            seed = int(time()*1e6) % 2 << 30

        self.context = queue.context
        self.luxury = luxury
        self.num_work_items = num_work_items

        from pyopencl.characterize import has_double_support
        self.support_double = has_double_support(queue.device)

        self.no_warmup = no_warmup
        self.use_legacy_init = use_legacy_init
        self.max_work_items = max_work_items

        src = """
            %(defines)s

            #include <pyopencl-ranluxcl.cl>

            kernel void init_ranlux(unsigned seeds,
                global ranluxcl_state_t *ranluxcltab)
            {
              if (get_global_id(0) < %(num_work_items)d)
                ranluxcl_initialization(seeds, ranluxcltab);
            }
            """ % {
                    "defines": self.generate_settings_defines(),
                    "num_work_items": num_work_items
                }
        prg = cl.Program(queue.context, src).build()

        # {{{ compute work group size

        wg_size = None

        import sys
        import platform
        if ("darwin" in sys.platform
                and "Apple" in queue.device.platform.vendor
                and platform.mac_ver()[0].startswith("10.7")
                and queue.device.type & cl.device_type.CPU):
            wg_size = (1,)

        self.wg_size = wg_size

        # }}}

        self.state = cl_array.empty(queue, (num_work_items, 112), dtype=np.uint8)
        self.state.fill(17)

        prg.init_ranlux(queue, (num_work_items,), self.wg_size, np.uint32(seed),
                self.state.data)

    def generate_settings_defines(self, include_double_pragma=True):
        lines = []
        if include_double_pragma and self.support_double:
            lines.append("#pragma OPENCL EXTENSION cl_khr_fp64 : enable")

        lines.append("#define RANLUXCL_LUX %d" % self.luxury)

        if self.no_warmup:
            lines.append("#define RANLUXCL_NO_WARMUP")

        if self.support_double:
            lines.append("#define RANLUXCL_SUPPORT_DOUBLE")

        if self.use_legacy_init:
            lines.append("#define RANLUXCL_USE_LEGACY_INITIALIZATION")

            if self.max_work_items:
                lines.append(
                        "#define RANLUXCL_MAXWORKITEMS %d" % self.max_work_items)

        return "\n".join(lines)

    @memoize_method
    def get_gen_kernel(self, dtype, distribution="uniform"):
        size_multiplier = 1
        arg_dtype = dtype

        if dtype == np.float64:
            bits = 64
            c_type = "double"
            rng_expr = "(shift + scale * gen)"
        elif dtype == np.float32:
            bits = 32
            c_type = "float"
            rng_expr = "(shift + scale * gen)"
        elif dtype == cl_array.vec.float2:
            bits = 32
            c_type = "float"
            rng_expr = "(shift + scale * gen)"
            size_multiplier = 2
            arg_dtype = np.float32
        elif dtype in [cl_array.vec.float3, cl_array.vec.float4]:
            bits = 32
            c_type = "float"
            rng_expr = "(shift + scale * gen)"
            size_multiplier = 4
            arg_dtype = np.float32
        elif dtype == np.int32:
            assert distribution == "uniform"
            bits = 32
            c_type = "int"
            rng_expr = ("(shift "
                    "+ convert_int4((float) scale * gen) "
                    "+ convert_int4((float) (scale / (1<<24)) * gen))")
        else:
            raise TypeError("unsupported RNG data type '%s'" % dtype)

        rl_flavor = "%d%s" % (bits, {
                "uniform": "",
                "normal": "norm"
                }[distribution])

        src = """//CL//
            %(defines)s

            #include <pyopencl-ranluxcl.cl>

            typedef %(output_t)s output_t;
            typedef %(output_t)s4 output_vec_t;
            #define NUM_WORKITEMS %(num_work_items)d
            #define RANLUX_FUNC ranluxcl%(rlflavor)s
            #define GET_RANDOM_NUM(gen) %(rng_expr)s

            kernel void generate(
                global ranluxcl_state_t *ranluxcltab,
                global output_t *output,
                unsigned long out_size,
                output_t scale,
                output_t shift)
            {

              ranluxcl_state_t ranluxclstate;
              ranluxcl_download_seed(&ranluxclstate, ranluxcltab);

              // output bulk
              unsigned long idx = get_global_id(0)*4;
              while (idx + 4 < out_size)
              {
                  vstore4(
                      GET_RANDOM_NUM(RANLUX_FUNC(&ranluxclstate)),
                      idx >> 2, output);
                  idx += 4*NUM_WORKITEMS;
              }

              // output tail
              output_vec_t tail_ran = GET_RANDOM_NUM(RANLUX_FUNC(&ranluxclstate));
              if (idx < out_size)
                output[idx] = tail_ran.x;
              if (idx+1 < out_size)
                output[idx+1] = tail_ran.y;
              if (idx+2 < out_size)
                output[idx+2] = tail_ran.z;
              if (idx+3 < out_size)
                output[idx+3] = tail_ran.w;

              ranluxcl_upload_seed(&ranluxclstate, ranluxcltab);
            }
            """ % {
                "defines": self.generate_settings_defines(),
                "rlflavor": rl_flavor,
                "output_t": c_type,
                "num_work_items": self.num_work_items,
                "rng_expr": rng_expr
            }

        prg = cl.Program(self.context, src).build()
        knl = prg.generate
        knl.set_scalar_arg_dtypes([None, None, np.uint64, arg_dtype, arg_dtype])

        return knl, size_multiplier

    def fill_uniform(self, ary, a=0, b=1, queue=None):
        """Fill *ary* with uniformly distributed random numbers in the interval
        *(a, b)*, endpoints excluded.
        """

        if queue is None:
            queue = ary.queue

        knl, size_multiplier = self.get_gen_kernel(ary.dtype, "uniform")
        knl(queue,
                (self.num_work_items,), None,
                self.state.data, ary.data, ary.size*size_multiplier,
                b-a, a)

    def uniform(self, *args, **kwargs):
        """Make a new empty array, apply :meth:`fill_uniform` to it.
        """
        a = kwargs.pop("a", 0)
        b = kwargs.pop("b", 1)

        result = cl_array.empty(*args, **kwargs)

        self.fill_uniform(result, queue=result.queue, a=a, b=b)
        return result

    def fill_normal(self, ary, mu=0, sigma=1, queue=None):
        """Fill *ary* with normally distributed numbers with mean *mu* and
        standard deviation *sigma*.
        """

        if queue is None:
            queue = ary.queue

        knl, size_multiplier = self.get_gen_kernel(ary.dtype, "normal")
        knl(queue,
                (self.num_work_items,), self.wg_size,
                self.state.data, ary.data, ary.size*size_multiplier, sigma, mu)

    def normal(self, *args, **kwargs):
        """Make a new empty array, apply :meth:`fill_normal` to it.
        """
        mu = kwargs.pop("mu", 0)
        sigma = kwargs.pop("sigma", 1)

        result = cl_array.empty(*args, **kwargs)

        self.fill_normal(result, queue=result.queue, mu=mu, sigma=sigma)
        return result

    @memoize_method
    def get_sync_kernel(self):
        src = """//CL//
            %(defines)s

            #include <pyopencl-ranluxcl.cl>

            kernel void sync(
                global ranluxcl_state_t *ranluxcltab)
            {
              ranluxcl_state_t ranluxclstate;
              ranluxcl_download_seed(&ranluxclstate, ranluxcltab);
              ranluxcl_synchronize(&ranluxclstate);
              ranluxcl_upload_seed(&ranluxclstate, ranluxcltab);
            }
            """ % {
                "defines": self.generate_settings_defines(),
            }
        prg = cl.Program(self.context, src).build()
        return prg.sync

    def synchronize(self, queue):
        """The generator gets inefficient when different work items invoke the
        generator a differing number of times. This function ensures
        efficiency.
        """

        self.get_sync_kernel()(queue, (self.num_work_items,),
                self.wg_size, self.state.data)


@first_arg_dependent_memoize
def _get_generator(queue, luxury=None):
    gen = RanluxGenerator(queue, luxury=luxury)
    queue.finish()
    return gen


def fill_rand(result, queue=None, luxury=4, a=0, b=1):
    """Fill *result* with random values of `dtype` in the range [0,1).
    """
    if queue is None:
        queue = result.queue
    gen = _get_generator(queue, luxury=luxury)
    gen.fill_uniform(result, a=a, b=b)


def rand(queue, shape, dtype, luxury=None, a=0, b=1):
    """Return an array of `shape` filled with random values of `dtype`
    in the range [a,b).
    """

    from pyopencl.array import Array
    gen = _get_generator(queue, luxury)
    result = Array(queue, shape, dtype)
    gen.fill_uniform(result, a=a, b=b)
    return result


# vim: filetype=pyopencl:foldmethod=marker

########NEW FILE########
__FILENAME__ = elementwise
"""Elementwise functionality."""

from __future__ import division

__copyright__ = "Copyright (C) 2009 Andreas Kloeckner"

__license__ = """
Permission is hereby granted, free of charge, to any person
obtaining a copy of this software and associated documentation
files (the "Software"), to deal in the Software without
restriction, including without limitation the rights to use,
copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following
conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.
"""


from pyopencl.tools import context_dependent_memoize
import numpy as np
import pyopencl as cl
from pytools import memoize_method
from pyopencl.tools import (dtype_to_ctype, VectorArg, ScalarArg,
        KernelTemplateBase)


# {{{ elementwise kernel code generator

def get_elwise_program(context, arguments, operation,
        name="elwise_kernel", options=[],
        preamble="", loop_prep="", after_loop="",
        use_range=False):

    if use_range:
        body = r"""//CL//
          if (step < 0)
          {
            for (i = start + (work_group_start + lid)*step;
              i > stop; i += gsize*step)
            {
              %(operation)s;
            }
          }
          else
          {
            for (i = start + (work_group_start + lid)*step;
              i < stop; i += gsize*step)
            {
              %(operation)s;
            }
          }
          """
    else:
        body = """//CL//
          for (i = work_group_start + lid; i < n; i += gsize)
          {
            %(operation)s;
          }
          """

    import re
    return_match = re.search(r"\breturn\b", operation)
    if return_match is not None:
        from warnings import warn
        warn("Using a 'return' statement in an element-wise operation will "
                "likely lead to incorrect results. Use "
                "PYOPENCL_ELWISE_CONTINUE instead.",
                stacklevel=3)

    source = ("""//CL//
        %(preamble)s

        #define PYOPENCL_ELWISE_CONTINUE continue

        __kernel void %(name)s(%(arguments)s)
        {
          int lid = get_local_id(0);
          int gsize = get_global_size(0);
          int work_group_start = get_local_size(0)*get_group_id(0);
          long i;

          %(loop_prep)s;
          %(body)s
          %(after_loop)s;
        }
        """ % {
            "arguments": ", ".join(arg.declarator() for arg in arguments),
            "name": name,
            "preamble": preamble,
            "loop_prep": loop_prep,
            "after_loop": after_loop,
            "body": body % dict(operation=operation),
            })

    from pyopencl import Program
    return Program(context, source).build(options)


def get_elwise_kernel_and_types(context, arguments, operation,
        name="elwise_kernel", options=[], preamble="", use_range=False,
        **kwargs):

    from pyopencl.tools import parse_arg_list, get_arg_offset_adjuster_code
    parsed_args = parse_arg_list(arguments, with_offset=True)

    auto_preamble = kwargs.pop("auto_preamble", True)

    pragmas = []
    includes = []
    have_double_pragma = False
    have_complex_include = False

    if auto_preamble:
        for arg in parsed_args:
            if arg.dtype in [np.float64, np.complex128]:
                if not have_double_pragma:
                    pragmas.append(
                            "#pragma OPENCL EXTENSION cl_khr_fp64: enable\n"
                            "#define PYOPENCL_DEFINE_CDOUBLE\n")
                    have_double_pragma = True
            if arg.dtype.kind == 'c':
                if not have_complex_include:
                    includes.append("#include <pyopencl-complex.h>\n")
                    have_complex_include = True

    if pragmas or includes:
        preamble = "\n".join(pragmas+includes) + "\n" + preamble

    if use_range:
        parsed_args.extend([
            ScalarArg(np.intp, "start"),
            ScalarArg(np.intp, "stop"),
            ScalarArg(np.intp, "step"),
            ])
    else:
        parsed_args.append(ScalarArg(np.intp, "n"))

    loop_prep = kwargs.pop("loop_prep", "")
    loop_prep = get_arg_offset_adjuster_code(parsed_args) + loop_prep
    prg = get_elwise_program(
        context, parsed_args, operation,
        name=name, options=options, preamble=preamble,
        use_range=use_range, loop_prep=loop_prep, **kwargs)

    from pyopencl.tools import get_arg_list_scalar_arg_dtypes

    kernel = getattr(prg, name)
    kernel.set_scalar_arg_dtypes(get_arg_list_scalar_arg_dtypes(parsed_args))

    return kernel, parsed_args


def get_elwise_kernel(context, arguments, operation,
        name="elwise_kernel", options=[], **kwargs):
    """Return a L{pyopencl.Kernel} that performs the same scalar operation
    on one or several vectors.
    """
    func, arguments = get_elwise_kernel_and_types(
        context, arguments, operation,
        name=name, options=options, **kwargs)

    return func

# }}}


# {{{ ElementwiseKernel driver

class ElementwiseKernel:
    """
    A kernel that takes a number of scalar or vector *arguments* and performs
    an *operation* specified as a snippet of C on these arguments.

    :arg arguments: a string formatted as a C argument list.
    :arg operation: a snippet of C that carries out the desired 'map'
        operation.  The current index is available as the variable *i*.
        *operation* may contain the statement ``PYOPENCL_ELWISE_CONTINUE``,
        which will terminate processing for the current element.
    :arg name: the function name as which the kernel is compiled
    :arg options: passed unmodified to :meth:`pyopencl.Program.build`.
    :arg preamble: a piece of C source code that gets inserted outside of the
        function context in the elementwise operation's kernel source code.

    .. warning :: Using a `return` statement in *operation* will lead to
        incorrect results, as some elements may never get processed. Use
        ``PYOPENCL_ELWISE_CONTINUE`` instead.

    .. versionchanged:: 2013.1
        Added ``PYOPENCL_ELWISE_CONTINUE``.
    """

    def __init__(self, context, arguments, operation,
            name="elwise_kernel", options=[], **kwargs):
        self.context = context
        self.arguments = arguments
        self.operation = operation
        self.name = name
        self.options = options
        self.kwargs = kwargs

    @memoize_method
    def get_kernel(self, use_range):
        knl, arg_descrs = get_elwise_kernel_and_types(
            self.context, self.arguments, self.operation,
            name=self.name, options=self.options,
            use_range=use_range, **self.kwargs)

        for arg in arg_descrs:
            if isinstance(arg, VectorArg) and not arg.with_offset:
                from warnings import warn
                warn("ElementwiseKernel '%s' used with VectorArgs that do not "
                        "have offset support enabled. This usage is deprecated. "
                        "Just pass with_offset=True to VectorArg, everything should "
                        "sort itself out automatically." % self.name,
                        DeprecationWarning)

        if not [i for i, arg in enumerate(arg_descrs)
                if isinstance(arg, VectorArg)]:
            raise RuntimeError(
                "ElementwiseKernel can only be used with "
                "functions that have at least one "
                "vector argument")
        return knl, arg_descrs

    def __call__(self, *args, **kwargs):
        repr_vec = None

        range_ = kwargs.pop("range", None)
        slice_ = kwargs.pop("slice", None)

        use_range = range_ is not None or slice_ is not None
        kernel, arg_descrs = self.get_kernel(use_range)

        # {{{ assemble arg array

        invocation_args = []
        for arg, arg_descr in zip(args, arg_descrs):
            if isinstance(arg_descr, VectorArg):
                if not arg.flags.forc:
                    raise RuntimeError("ElementwiseKernel cannot "
                            "deal with non-contiguous arrays")

                if repr_vec is None:
                    repr_vec = arg

                invocation_args.append(arg.base_data)
                if arg_descr.with_offset:
                    invocation_args.append(arg.offset)
            else:
                invocation_args.append(arg)

        # }}}

        queue = kwargs.pop("queue", None)
        wait_for = kwargs.pop("wait_for", None)
        if kwargs:
            raise TypeError("unknown keyword arguments: '%s'"
                    % ", ".join(kwargs))

        if queue is None:
            queue = repr_vec.queue

        if slice_ is not None:
            if range_ is not None:
                raise TypeError("may not specify both range and slice "
                        "keyword arguments")

            range_ = slice(*slice_.indices(repr_vec.size))

        max_wg_size = kernel.get_work_group_info(
                cl.kernel_work_group_info.WORK_GROUP_SIZE,
                queue.device)

        if range_ is not None:
            start = range_.start
            if start is None:
                start = 0
            invocation_args.append(start)
            invocation_args.append(range_.stop)
            if range_.step is None:
                step = 1
            else:
                step = range_.step

            invocation_args.append(step)

            from pyopencl.array import splay
            gs, ls = splay(queue,
                    abs(range_.stop - start)//step,
                    max_wg_size)
        else:
            invocation_args.append(repr_vec.size)
            gs, ls = repr_vec.get_sizes(queue, max_wg_size)

        kernel.set_args(*invocation_args)
        return cl.enqueue_nd_range_kernel(queue, kernel,
                gs, ls, wait_for=wait_for)

# }}}


# {{{ template

class ElementwiseTemplate(KernelTemplateBase):
    def __init__(self,
            arguments, operation, name="elwise", preamble="",
            template_processor=None):

        KernelTemplateBase.__init__(self,
                template_processor=template_processor)
        self.arguments = arguments
        self.operation = operation
        self.name = name
        self.preamble = preamble

    def build_inner(self, context, type_aliases=(), var_values=(),
            more_preamble="", more_arguments=(), declare_types=(),
            options=()):
        renderer = self.get_renderer(
                type_aliases, var_values, context, options)

        arg_list = renderer.render_argument_list(
                self.arguments, more_arguments, with_offset=True)
        type_decl_preamble = renderer.get_type_decl_preamble(
                context.devices[0], declare_types, arg_list)

        return ElementwiseKernel(context,
            arg_list, renderer(self.operation),
            name=renderer(self.name), options=list(options),
            preamble=(
                type_decl_preamble
                + "\n"
                + renderer(self.preamble + "\n" + more_preamble)),
            auto_preamble=False)

# }}}


# {{{ kernels supporting array functionality

@context_dependent_memoize
def get_take_kernel(context, dtype, idx_dtype, vec_count=1):
    ctx = {
            "idx_tp": dtype_to_ctype(idx_dtype),
            "tp": dtype_to_ctype(dtype),
            }

    args = ([VectorArg(dtype, "dest" + str(i), with_offset=True)
             for i in range(vec_count)]
            + [VectorArg(dtype, "src" + str(i), with_offset=True)
               for i in range(vec_count)]
            + [VectorArg(idx_dtype, "idx", with_offset=True)])
    body = (
            ("%(idx_tp)s src_idx = idx[i];\n" % ctx)
            + "\n".join(
                "dest%d[i] = src%d[src_idx];" % (i, i)
                for i in range(vec_count)))

    return get_elwise_kernel(context, args, body, name="take")


@context_dependent_memoize
def get_take_put_kernel(context, dtype, idx_dtype, with_offsets, vec_count=1):
    ctx = {
            "idx_tp": dtype_to_ctype(idx_dtype),
            "tp": dtype_to_ctype(dtype),
            }

    args = [
            VectorArg(dtype, "dest%d" % i)
                for i in range(vec_count)
            ] + [
                VectorArg(idx_dtype, "gmem_dest_idx", with_offset=True),
                VectorArg(idx_dtype, "gmem_src_idx", with_offset=True),
            ] + [
                VectorArg(dtype, "src%d" % i, with_offset=True)
                for i in range(vec_count)
            ] + [
                ScalarArg(idx_dtype, "offset%d" % i)
                    for i in range(vec_count) if with_offsets
            ]

    if with_offsets:
        def get_copy_insn(i):
            return ("dest%d[dest_idx] = "
                    "src%d[src_idx+offset%d];"
                    % (i, i, i))
    else:
        def get_copy_insn(i):
            return ("dest%d[dest_idx] = "
                    "src%d[src_idx];" % (i, i))

    body = (("%(idx_tp)s src_idx = gmem_src_idx[i];\n"
                "%(idx_tp)s dest_idx = gmem_dest_idx[i];\n" % ctx)
            + "\n".join(get_copy_insn(i) for i in range(vec_count)))

    return get_elwise_kernel(context, args, body, name="take_put")


@context_dependent_memoize
def get_put_kernel(context, dtype, idx_dtype, vec_count=1):
    ctx = {
            "idx_tp": dtype_to_ctype(idx_dtype),
            "tp": dtype_to_ctype(dtype),
            }

    args = [
            VectorArg(dtype, "dest%d" % i, with_offset=True)
                for i in range(vec_count)
            ] + [
                VectorArg(idx_dtype, "gmem_dest_idx", with_offset=True),
            ] + [
                VectorArg(dtype, "src%d" % i, with_offset=True)
                for i in range(vec_count)
            ]

    body = (
            "%(idx_tp)s dest_idx = gmem_dest_idx[i];\n" % ctx
            + "\n".join("dest%d[dest_idx] = src%d[i];" % (i, i)
                for i in range(vec_count)))

    return get_elwise_kernel(context, args, body, name="put")


@context_dependent_memoize
def get_copy_kernel(context, dtype_dest, dtype_src):
    src = "src[i]"
    if dtype_dest.kind == "c" != dtype_src.kind:
        src = "%s_fromreal(%s)" % (complex_dtype_to_name(dtype_dest), src)

    if dtype_dest.kind == "c" and dtype_src != dtype_dest:
        src = "%s_cast(%s)" % (complex_dtype_to_name(dtype_dest), src),

    return get_elwise_kernel(context,
            "%(tp_dest)s *dest, %(tp_src)s *src" % {
                "tp_dest": dtype_to_ctype(dtype_dest),
                "tp_src": dtype_to_ctype(dtype_src),
                },
            "dest[i] = %s" % src,
            name="copy")


@context_dependent_memoize
def get_linear_combination_kernel(summand_descriptors,
        dtype_z):
    # TODO: Port this!
    raise NotImplementedError

    from pyopencl.tools import dtype_to_ctype
    from pyopencl.elementwise import \
            VectorArg, ScalarArg, get_elwise_module

    args = []
    preamble = []
    loop_prep = []
    summands = []
    tex_names = []

    for i, (is_gpu_scalar, scalar_dtype, vector_dtype) in \
            enumerate(summand_descriptors):
        if is_gpu_scalar:
            preamble.append(
                    "texture <%s, 1, cudaReadModeElementType> tex_a%d;"
                    % (dtype_to_ctype(scalar_dtype, with_fp_tex_hack=True), i))
            args.append(VectorArg(vector_dtype, "x%d" % i, with_offset=True))
            tex_names.append("tex_a%d" % i)
            loop_prep.append(
                    "%s a%d = fp_tex1Dfetch(tex_a%d, 0)"
                    % (dtype_to_ctype(scalar_dtype), i, i))
        else:
            args.append(ScalarArg(scalar_dtype, "a%d" % i))
            args.append(VectorArg(vector_dtype, "x%d" % i, with_offset=True))

        summands.append("a%d*x%d[i]" % (i, i))

    args.append(VectorArg(dtype_z, "z", with_offset=True))
    args.append(ScalarArg(np.uintp, "n"))

    mod = get_elwise_module(args,
            "z[i] = " + " + ".join(summands),
            "linear_combination",
            preamble="\n".join(preamble),
            loop_prep=";\n".join(loop_prep))

    func = mod.get_function("linear_combination")
    tex_src = [mod.get_texref(tn) for tn in tex_names]
    func.prepare("".join(arg.struct_char for arg in args),
            (1, 1, 1), texrefs=tex_src)

    return func, tex_src


def complex_dtype_to_name(dtype):
    if dtype == np.complex128:
        return "cdouble"
    elif dtype == np.complex64:
        return "cfloat"
    else:
        raise RuntimeError("invalid complex type")


def real_dtype(dtype):
    return dtype.type(0).real.dtype


@context_dependent_memoize
def get_axpbyz_kernel(context, dtype_x, dtype_y, dtype_z):
    ax = "a*x[i]"
    by = "b*y[i]"

    x_is_complex = dtype_x.kind == "c"
    y_is_complex = dtype_y.kind == "c"
    z_is_complex = dtype_z.kind == "c"

    if x_is_complex:
        ax = "%s_mul(a, x[i])" % complex_dtype_to_name(dtype_x)

    if y_is_complex:
        by = "%s_mul(b, y[i])" % complex_dtype_to_name(dtype_y)

    if x_is_complex and not y_is_complex:
        by = "%s_fromreal(%s)" % (complex_dtype_to_name(dtype_x), by)

    if not x_is_complex and y_is_complex:
        ax = "%s_fromreal(%s)" % (complex_dtype_to_name(dtype_y), ax)

    result = "%s + %s" % (ax, by)
    if z_is_complex:
        result = "%s_cast(%s)" % (complex_dtype_to_name(dtype_z), result)

    return get_elwise_kernel(context,
            "%(tp_z)s *z, %(tp_x)s a, %(tp_x)s *x, %(tp_y)s b, %(tp_y)s *y" % {
                "tp_x": dtype_to_ctype(dtype_x),
                "tp_y": dtype_to_ctype(dtype_y),
                "tp_z": dtype_to_ctype(dtype_z),
                },
            "z[i] = %s" % result,
            name="axpbyz")


@context_dependent_memoize
def get_axpbz_kernel(context, dtype_a, dtype_x, dtype_b, dtype_z):
    a_is_complex = dtype_a.kind == "c"
    x_is_complex = dtype_x.kind == "c"
    b_is_complex = dtype_b.kind == "c"

    z_is_complex = dtype_z.kind == "c"

    ax = "a*x[i]"
    if a_is_complex and x_is_complex:
        a = "a"
        x = "x[i]"

        if dtype_a != dtype_z:
            a = "%s_cast(%s)" % (complex_dtype_to_name(dtype_z), a)
        if dtype_x != dtype_z:
            x = "%s_cast(%s)" % (complex_dtype_to_name(dtype_z), x)

        ax = "%s_mul(%s, %s)" % (complex_dtype_to_name(dtype_z), a, x)

    # The following two are workarounds for Apple on OS X 10.8.
    # They're not really necessary.

    elif a_is_complex and not x_is_complex:
        ax = "a*((%s) x[i])" % dtype_to_ctype(real_dtype(dtype_a))
    elif not a_is_complex and x_is_complex:
        ax = "((%s) a)*x[i]" % dtype_to_ctype(real_dtype(dtype_x))

    b = "b"
    if z_is_complex and not b_is_complex:
        b = "%s_fromreal(%s)" % (complex_dtype_to_name(dtype_z), b)

    if z_is_complex and not (a_is_complex or x_is_complex):
        ax = "%s_fromreal(%s)" % (complex_dtype_to_name(dtype_z), ax)

    if z_is_complex:
        ax = "%s_cast(%s)" % (complex_dtype_to_name(dtype_z), ax)
        b = "%s_cast(%s)" % (complex_dtype_to_name(dtype_z), b)

    return get_elwise_kernel(context,
            "%(tp_z)s *z, %(tp_a)s a, %(tp_x)s *x,%(tp_b)s b" % {
                "tp_a": dtype_to_ctype(dtype_a),
                "tp_x": dtype_to_ctype(dtype_x),
                "tp_b": dtype_to_ctype(dtype_b),
                "tp_z": dtype_to_ctype(dtype_z),
                },
            "z[i] = %s + %s" % (ax, b),
            name="axpb")


@context_dependent_memoize
def get_multiply_kernel(context, dtype_x, dtype_y, dtype_z):
    x_is_complex = dtype_x.kind == "c"
    y_is_complex = dtype_y.kind == "c"
    z_is_complex = dtype_z.kind == "c"

    x = "x[i]"
    y = "y[i]"

    if x_is_complex and dtype_x != dtype_z:
        x = "%s_cast(%s)" % (complex_dtype_to_name(dtype_z), x)
    if y_is_complex and dtype_y != dtype_z:
        y = "%s_cast(%s)" % (complex_dtype_to_name(dtype_z), y)

    if x_is_complex and y_is_complex:
        xy = "%s_mul(%s, %s)" % (complex_dtype_to_name(dtype_z), x, y)

    else:
        xy = "%s * %s" % (x, y)

    if z_is_complex:
        xy = "%s_cast(%s)" % (complex_dtype_to_name(dtype_z), xy)

    return get_elwise_kernel(context,
            "%(tp_z)s *z, %(tp_x)s *x, %(tp_y)s *y" % {
                "tp_x": dtype_to_ctype(dtype_x),
                "tp_y": dtype_to_ctype(dtype_y),
                "tp_z": dtype_to_ctype(dtype_z),
                },
            "z[i] = %s" % xy,
            name="multiply")


@context_dependent_memoize
def get_divide_kernel(context, dtype_x, dtype_y, dtype_z):
    x_is_complex = dtype_x.kind == "c"
    y_is_complex = dtype_y.kind == "c"
    z_is_complex = dtype_z.kind == "c"

    x = "x[i]"
    y = "y[i]"

    if z_is_complex and dtype_x != dtype_y:
        if x_is_complex and dtype_x != dtype_z:
            x = "%s_cast(%s)" % (complex_dtype_to_name(dtype_z), x)
        if y_is_complex and dtype_y != dtype_z:
            y = "%s_cast(%s)" % (complex_dtype_to_name(dtype_z), y)

    if x_is_complex and y_is_complex:
        xoy = "%s_divide(%s, %s)" % (complex_dtype_to_name(dtype_z), x, y)
    elif not x_is_complex and y_is_complex:

        xoy = "%s_rdivide(%s, %s)" % (complex_dtype_to_name(dtype_z), x, y)
    else:
        xoy = "%s / %s" % (x, y)

    if z_is_complex:
        xoy = "%s_cast(%s)" % (complex_dtype_to_name(dtype_z), xoy)

    return get_elwise_kernel(context,
            "%(tp_z)s *z, %(tp_x)s *x, %(tp_y)s *y" % {
                "tp_x": dtype_to_ctype(dtype_x),
                "tp_y": dtype_to_ctype(dtype_y),
                "tp_z": dtype_to_ctype(dtype_z),
                },
            "z[i] = %s" % xoy,
            name="divide")


@context_dependent_memoize
def get_rdivide_elwise_kernel(context, dtype_x, dtype_y, dtype_z):
    # implements y / x!
    x_is_complex = dtype_x.kind == "c"
    y_is_complex = dtype_y.kind == "c"
    z_is_complex = dtype_z.kind == "c"

    x = "x[i]"
    y = "y"

    if z_is_complex and dtype_x != dtype_y:
        if x_is_complex and dtype_x != dtype_z:
            x = "%s_cast(%s)" % (complex_dtype_to_name(dtype_z), x)
        if y_is_complex and dtype_y != dtype_z:
            y = "%s_cast(%s)" % (complex_dtype_to_name(dtype_z), y)

    if x_is_complex and y_is_complex:
        yox = "%s_divide(%s, %s)" % (complex_dtype_to_name(dtype_z), y, x)
    elif not y_is_complex and x_is_complex:
        yox = "%s_rdivide(%s, %s)" % (complex_dtype_to_name(dtype_x), y, x)
    else:
        yox = "%s / %s" % (y, x)

    return get_elwise_kernel(context,
            "%(tp_z)s *z, %(tp_x)s *x, %(tp_y)s y" % {
                "tp_x": dtype_to_ctype(dtype_x),
                "tp_y": dtype_to_ctype(dtype_y),
                "tp_z": dtype_to_ctype(dtype_z),
                },
            "z[i] = %s" % yox,
            name="divide_r")


@context_dependent_memoize
def get_fill_kernel(context, dtype):
    return get_elwise_kernel(context,
            "%(tp)s *z, %(tp)s a" % {
                "tp": dtype_to_ctype(dtype),
                },
            "z[i] = a",
            name="fill")


@context_dependent_memoize
def get_reverse_kernel(context, dtype):
    return get_elwise_kernel(context,
            "%(tp)s *z, %(tp)s *y" % {
                "tp": dtype_to_ctype(dtype),
                },
            "z[i] = y[n-1-i]",
            name="reverse")


@context_dependent_memoize
def get_arange_kernel(context, dtype):
    if dtype.kind == "c":
        i = "%s_fromreal(i)" % complex_dtype_to_name(dtype)
    else:
        i = "(%s) i" % dtype_to_ctype(dtype)

    return get_elwise_kernel(context, [
        VectorArg(dtype, "z", with_offset=True),
        ScalarArg(dtype, "start"),
        ScalarArg(dtype, "step"),
        ],
        "z[i] = start + %s*step" % i,
        name="arange")


@context_dependent_memoize
def get_pow_kernel(context, dtype_x, dtype_y, dtype_z,
        is_base_array, is_exp_array):
    if is_base_array:
        x = "x[i]"
        x_ctype = "%(tp_x)s *x"
    else:
        x = "x"
        x_ctype = "%(tp_x)s x"

    if is_exp_array:
        y = "y[i]"
        y_ctype = "%(tp_y)s *y"
    else:
        y = "y"
        y_ctype = "%(tp_y)s y"

    x_is_complex = dtype_x.kind == "c"
    y_is_complex = dtype_y.kind == "c"
    z_is_complex = dtype_z.kind == "c"

    if z_is_complex and dtype_x != dtype_y:
        if x_is_complex and dtype_x != dtype_z:
            x = "%s_cast(%s)" % (complex_dtype_to_name(dtype_z), x)
        if y_is_complex and dtype_y != dtype_z:
            y = "%s_cast(%s)" % (complex_dtype_to_name(dtype_z), y)
    elif dtype_x != dtype_y:
        if dtype_x != dtype_z:
            x = "(%s) (%s)" % (dtype_to_ctype(dtype_z), x)
        if dtype_y != dtype_z:
            y = "(%s) (%s)" % (dtype_to_ctype(dtype_z), y)

    if x_is_complex and y_is_complex:
        result = "%s_pow(%s, %s)" % (complex_dtype_to_name(dtype_z), x, y)
    elif x_is_complex and not y_is_complex:
        result = "%s_powr(%s, %s)" % (complex_dtype_to_name(dtype_z), x, y)
    elif not x_is_complex and y_is_complex:
        result = "%s_rpow(%s, %s)" % (complex_dtype_to_name(dtype_z), x, y)
    else:
        result = "pow(%s, %s)" % (x, y)

    return get_elwise_kernel(context,
            ("%(tp_z)s *z, " + x_ctype + ", "+y_ctype) % {
                "tp_x": dtype_to_ctype(dtype_x),
                "tp_y": dtype_to_ctype(dtype_y),
                "tp_z": dtype_to_ctype(dtype_z),
                },
            "z[i] = %s" % result,
            name="pow_method")


@context_dependent_memoize
def get_array_scalar_comparison_kernel(context, operator, dtype_a):
    return get_elwise_kernel(context, [
        VectorArg(np.int8, "out", with_offset=True),
        VectorArg(dtype_a, "a", with_offset=True),
        ScalarArg(dtype_a, "b"),
        ],
        "out[i] = a[i] %s b" % operator,
        name="scalar_comparison_kernel")


@context_dependent_memoize
def get_array_comparison_kernel(context, operator, dtype_a, dtype_b):
    return get_elwise_kernel(context, [
        VectorArg(np.int8, "out", with_offset=True),
        VectorArg(dtype_a, "a", with_offset=True),
        VectorArg(dtype_b, "b", with_offset=True),
        ],
        "out[i] = a[i] %s b[i]" % operator,
        name="comparison_kernel")


@context_dependent_memoize
def get_unary_func_kernel(context, func_name, in_dtype, out_dtype=None):
    if out_dtype is None:
        out_dtype = in_dtype

    return get_elwise_kernel(context, [
        VectorArg(out_dtype, "z", with_offset=True),
        VectorArg(in_dtype, "y", with_offset=True),
        ],
        "z[i] = %s(y[i])" % func_name,
        name="%s_kernel" % func_name)


@context_dependent_memoize
def get_binary_func_kernel(context, func_name, x_dtype, y_dtype, out_dtype,
                           preamble="", name=None):
    return get_elwise_kernel(context, [
        VectorArg(out_dtype, "z", with_offset=True),
        VectorArg(x_dtype, "x", with_offset=True),
        VectorArg(y_dtype, "y", with_offset=True),
        ],
        "z[i] = %s(x[i], y[i])" % func_name,
        name="%s_kernel" % func_name if name is None else name,
        preamble=preamble)


@context_dependent_memoize
def get_float_binary_func_kernel(context, func_name, x_dtype, y_dtype,
                                 out_dtype, preamble="", name=None):
    if (np.array(0, x_dtype) * np.array(0, y_dtype)).itemsize > 4:
        arg_type = 'double'
        preamble = """
        #pragma OPENCL EXTENSION cl_khr_fp64: enable
        #define PYOPENCL_DEFINE_CDOUBLE
        """ + preamble
    else:
        arg_type = 'float'
    return get_elwise_kernel(context, [
        VectorArg(out_dtype, "z", with_offset=True),
        VectorArg(x_dtype, "x", with_offset=True),
        VectorArg(y_dtype, "y", with_offset=True),
        ],
        "z[i] = %s((%s)x[i], (%s)y[i])" % (func_name, arg_type, arg_type),
        name="%s_kernel" % func_name if name is None else name,
        preamble=preamble)


@context_dependent_memoize
def get_fmod_kernel(context, out_dtype=np.float32, arg_dtype=np.float32,
                    mod_dtype=np.float32):
    return get_float_binary_func_kernel(context, 'fmod', arg_dtype,
                                        mod_dtype, out_dtype)


@context_dependent_memoize
def get_modf_kernel(context, int_dtype=np.float32,
                    frac_dtype=np.float32, x_dtype=np.float32):
    return get_elwise_kernel(context, [
        VectorArg(int_dtype, "intpart", with_offset=True),
        VectorArg(frac_dtype, "fracpart", with_offset=True),
        VectorArg(x_dtype, "x", with_offset=True),
        ],
        """
        fracpart[i] = modf(x[i], &intpart[i])
        """,
        name="modf_kernel")


@context_dependent_memoize
def get_frexp_kernel(context, sign_dtype=np.float32, exp_dtype=np.float32,
                     x_dtype=np.float32):
    return get_elwise_kernel(context, [
        VectorArg(sign_dtype, "significand", with_offset=True),
        VectorArg(exp_dtype, "exponent", with_offset=True),
        VectorArg(x_dtype, "x", with_offset=True),
        ],
        """
        int expt = 0;
        significand[i] = frexp(x[i], &expt);
        exponent[i] = expt;
        """,
        name="frexp_kernel")


@context_dependent_memoize
def get_ldexp_kernel(context, out_dtype=np.float32, sig_dtype=np.float32,
                     expt_dtype=np.float32):
    return get_binary_func_kernel(
        context, '_PYOCL_LDEXP', sig_dtype, expt_dtype, out_dtype,
        preamble="#define _PYOCL_LDEXP(x, y) ldexp(x, (int)(y))",
        name="ldexp_kernel")


@context_dependent_memoize
def get_bessel_kernel(context, which_func, out_dtype=np.float64,
                      order_dtype=np.int32, x_dtype=np.float64):
    return get_elwise_kernel(context, [
        VectorArg(out_dtype, "z", with_offset=True),
        ScalarArg(order_dtype, "ord_n"),
        VectorArg(x_dtype, "x", with_offset=True),
        ],
        "z[i] = bessel_%sn(ord_n, x[i])" % which_func,
        name="bessel_%sn_kernel" % which_func,
        preamble="""
        #pragma OPENCL EXTENSION cl_khr_fp64: enable
        #define PYOPENCL_DEFINE_CDOUBLE
        #include <pyopencl-bessel-%s.cl>
        """ % which_func)


@context_dependent_memoize
def get_diff_kernel(context, dtype):
    return get_elwise_kernel(context, [
            VectorArg(dtype, "result", with_offset=True),
            VectorArg(dtype, "array", with_offset=True),
            ],
            "result[i] = array[i+1] - array[i]",
            name="diff")


@context_dependent_memoize
def get_if_positive_kernel(context, crit_dtype, dtype):
    return get_elwise_kernel(context, [
            VectorArg(dtype, "result", with_offset=True),
            VectorArg(crit_dtype, "crit", with_offset=True),
            VectorArg(dtype, "then_", with_offset=True),
            VectorArg(dtype, "else_", with_offset=True),
            ],
            "result[i] = crit[i] > 0 ? then_[i] : else_[i]",
            name="if_positive")

# }}}

# vim: fdm=marker:filetype=pyopencl

########NEW FILE########
__FILENAME__ = ipython
from __future__ import division

from IPython.core.magic import (magics_class, Magics, cell_magic)

import pyopencl as cl


@magics_class
class PyOpenCLMagics(Magics):
    @cell_magic
    def cl_kernel(self, line, cell):
        try:
            ctx = self.shell.user_ns["cl_ctx"]
        except KeyError:
            ctx = None

        if not isinstance(ctx, cl.Context):
            ctx = None

        if ctx is None:
            try:
                ctx = self.shell.user_ns["ctx"]
            except KeyError:
                ctx = None

        if ctx is None:
            raise RuntimeError("unable to locate cl context, which must be "
                    "present in namespace as 'cl_ctx' or 'ctx'")

        prg = cl.Program(ctx, cell.encode("utf8")).build()

        for knl in prg.all_kernels():
            self.shell.user_ns[knl.function_name] = knl


def load_ipython_extension(ip):
    ip.register_magics(PyOpenCLMagics)

########NEW FILE########
__FILENAME__ = reduction
"""Computation of reductions on vectors."""

from __future__ import division

__copyright__ = "Copyright (C) 2010 Andreas Kloeckner"

__license__ = """
Permission is hereby granted, free of charge, to any person
obtaining a copy of this software and associated documentation
files (the "Software"), to deal in the Software without
restriction, including without limitation the rights to use,
copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following
conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.

Based on code/ideas by Mark Harris <mharris@nvidia.com>.
None of the original source code remains.
"""


import pyopencl as cl
from pyopencl.tools import (
        context_dependent_memoize,
        dtype_to_ctype, KernelTemplateBase,
        _process_code_for_macro)
import numpy as np


# {{{ kernel source

KERNEL = """//CL//
    #define GROUP_SIZE ${group_size}
    #define READ_AND_MAP(i) (${map_expr})
    #define REDUCE(a, b) (${reduce_expr})

    % if double_support:
        #pragma OPENCL EXTENSION cl_khr_fp64: enable
        #define PYOPENCL_DEFINE_CDOUBLE
    % endif

    #include <pyopencl-complex.h>

    ${preamble}

    typedef ${out_type} out_type;

    __kernel void ${name}(
      __global out_type *out, ${arguments},
      unsigned int seq_count, unsigned int n)
    {
       ${arg_prep}

        __local out_type ldata[GROUP_SIZE];

        unsigned int lid = get_local_id(0);

        unsigned int i = get_group_id(0)*GROUP_SIZE*seq_count + lid;

        out_type acc = ${neutral};
        for (unsigned s = 0; s < seq_count; ++s)
        {
          if (i >= n)
            break;
          acc = REDUCE(acc, READ_AND_MAP(i));

          i += GROUP_SIZE;
        }

        ldata[lid] = acc;

        <%
          cur_size = group_size
        %>

        % while cur_size > no_sync_size:
            barrier(CLK_LOCAL_MEM_FENCE);

            <%
            new_size = cur_size // 2
            assert new_size * 2 == cur_size
            %>

            if (lid < ${new_size})
            {
                ldata[lid] = REDUCE(
                  ldata[lid],
                  ldata[lid + ${new_size}]);
            }

            <% cur_size = new_size %>

        % endwhile

        % if cur_size > 1:
            ## we need to synchronize one last time for entry into the
            ## no-sync region.

            barrier(CLK_LOCAL_MEM_FENCE);

            <%
            # NB: There's an exact duplicate of this calculation in the
            # %while loop below.

            new_size = cur_size // 2
            assert new_size * 2 == cur_size
            %>

            if (lid < ${new_size})
            {
                __local volatile out_type *lvdata = ldata;
                % while cur_size > 1:
                    <%
                    new_size = cur_size // 2
                    assert new_size * 2 == cur_size
                    %>

                    lvdata[lid] = REDUCE(
                      lvdata[lid],
                      lvdata[lid + ${new_size}]);

                    <% cur_size = new_size %>

                % endwhile

            }
        % endif

        if (lid == 0) out[get_group_id(0)] = ldata[0];
    }
    """

# }}}


# {{{ internal codegen frontends

def _get_reduction_source(
        ctx, out_type, out_type_size,
        neutral, reduce_expr, map_expr, parsed_args,
        name="reduce_kernel", preamble="", arg_prep="",
        device=None, max_group_size=None):

    if device is not None:
        devices = [device]
    else:
        devices = ctx.devices

    # {{{ compute group size

    def get_dev_group_size(device):
        # dirty fix for the RV770 boards
        max_work_group_size = device.max_work_group_size
        if "RV770" in device.name:
            max_work_group_size = 64

        # compute lmem limit
        from pytools import div_ceil
        lmem_wg_size = div_ceil(max_work_group_size, out_type_size)
        result = min(max_work_group_size, lmem_wg_size)

        # round down to power of 2
        from pyopencl.tools import bitlog2
        return 2**bitlog2(result)

    group_size = min(get_dev_group_size(dev) for dev in devices)

    if max_group_size is not None:
        group_size = min(max_group_size, group_size)

    # }}}

    # {{{ compute synchronization-less group size

    def get_dev_no_sync_size(device):
        from pyopencl.characterize import get_simd_group_size
        result = get_simd_group_size(device, out_type_size)

        if result is None:
            from warnings import warn
            warn("Reduction might be unnecessarily slow: "
                    "can't query SIMD group size")
            return 1

        return result

    no_sync_size = min(get_dev_no_sync_size(dev) for dev in devices)

    # }}}

    from mako.template import Template
    from pytools import all
    from pyopencl.characterize import has_double_support
    src = str(Template(KERNEL).render(
        out_type=out_type,
        arguments=", ".join(arg.declarator() for arg in parsed_args),
        group_size=group_size,
        no_sync_size=no_sync_size,
        neutral=neutral,
        reduce_expr=_process_code_for_macro(reduce_expr),
        map_expr=_process_code_for_macro(map_expr),
        name=name,
        preamble=preamble,
        arg_prep=arg_prep,
        double_support=all(has_double_support(dev) for dev in devices),
        ))

    from pytools import Record

    class ReductionInfo(Record):
        pass

    return ReductionInfo(
            context=ctx,
            source=src,
            group_size=group_size)


def get_reduction_kernel(stage,
         ctx, dtype_out,
         neutral, reduce_expr, map_expr=None, arguments=None,
         name="reduce_kernel", preamble="",
         device=None, options=[], max_group_size=None):

    if map_expr is None:
        if stage == 2:
            map_expr = "pyopencl_reduction_inp[i]"
        else:
            map_expr = "in[i]"

    from pyopencl.tools import (
            parse_arg_list, get_arg_list_scalar_arg_dtypes,
            get_arg_offset_adjuster_code, VectorArg)

    arg_prep = ""
    if stage == 1 and arguments is not None:
        arguments = parse_arg_list(arguments, with_offset=True)
        arg_prep = get_arg_offset_adjuster_code(arguments)

    if stage == 2 and arguments is not None:
        arguments = parse_arg_list(arguments)
        arguments = (
                [VectorArg(dtype_out, "pyopencl_reduction_inp")]
                + arguments)

    inf = _get_reduction_source(
            ctx, dtype_to_ctype(dtype_out), dtype_out.itemsize,
            neutral, reduce_expr, map_expr, arguments,
            name, preamble, arg_prep, device, max_group_size)

    inf.program = cl.Program(ctx, inf.source)
    inf.program.build(options)
    inf.kernel = getattr(inf.program, name)

    inf.arg_types = arguments

    inf.kernel.set_scalar_arg_dtypes(
            [None]
            + get_arg_list_scalar_arg_dtypes(inf.arg_types)
            + [np.uint32]*2)

    return inf

# }}}


# {{{ main reduction kernel

class ReductionKernel:
    def __init__(self, ctx, dtype_out,
            neutral, reduce_expr, map_expr=None, arguments=None,
            name="reduce_kernel", options=[], preamble=""):

        dtype_out = self.dtype_out = np.dtype(dtype_out)

        max_group_size = None
        trip_count = 0

        while True:
            self.stage_1_inf = get_reduction_kernel(1, ctx,
                    dtype_out,
                    neutral, reduce_expr, map_expr, arguments,
                    name=name+"_stage1", options=options, preamble=preamble,
                    max_group_size=max_group_size)

            kernel_max_wg_size = self.stage_1_inf.kernel.get_work_group_info(
                    cl.kernel_work_group_info.WORK_GROUP_SIZE,
                    ctx.devices[0])

            if self.stage_1_inf.group_size <= kernel_max_wg_size:
                break
            else:
                max_group_size = kernel_max_wg_size

            trip_count += 1
            assert trip_count <= 2

        self.stage_2_inf = get_reduction_kernel(2, ctx,
                dtype_out,
                neutral, reduce_expr, arguments=arguments,
                name=name+"_stage2", options=options, preamble=preamble,
                max_group_size=max_group_size)

        from pytools import any
        from pyopencl.tools import VectorArg
        assert any(
                isinstance(arg_tp, VectorArg)
                for arg_tp in self.stage_1_inf.arg_types), \
                "ReductionKernel can only be used with functions " \
                "that have at least one vector argument"

    def __call__(self, *args, **kwargs):
        MAX_GROUP_COUNT = 1024
        SMALL_SEQ_COUNT = 4

        from pyopencl.array import empty

        stage_inf = self.stage_1_inf

        queue = kwargs.pop("queue", None)
        wait_for = kwargs.pop("wait_for", None)
        return_event = kwargs.pop("return_event", False)

        if kwargs:
            raise TypeError("invalid keyword argument to reduction kernel")

        stage1_args = args

        while True:
            invocation_args = []
            vectors = []

            from pyopencl.tools import VectorArg
            for arg, arg_tp in zip(args, stage_inf.arg_types):
                if isinstance(arg_tp, VectorArg):
                    if not arg.flags.forc:
                        raise RuntimeError("ReductionKernel cannot "
                                "deal with non-contiguous arrays")

                    vectors.append(arg)
                    invocation_args.append(arg.base_data)
                    if arg_tp.with_offset:
                        invocation_args.append(arg.offset)
                else:
                    invocation_args.append(arg)

            repr_vec = vectors[0]
            sz = repr_vec.size

            if queue is not None:
                use_queue = queue
            else:
                use_queue = repr_vec.queue

            if sz <= stage_inf.group_size*SMALL_SEQ_COUNT*MAX_GROUP_COUNT:
                total_group_size = SMALL_SEQ_COUNT*stage_inf.group_size
                group_count = (sz + total_group_size - 1) // total_group_size
                seq_count = SMALL_SEQ_COUNT
            else:
                group_count = MAX_GROUP_COUNT
                macrogroup_size = group_count*stage_inf.group_size
                seq_count = (sz + macrogroup_size - 1) // macrogroup_size

            if group_count == 1:
                result = empty(use_queue,
                        (), self.dtype_out,
                        allocator=repr_vec.allocator)
            else:
                result = empty(use_queue,
                        (group_count,), self.dtype_out,
                        allocator=repr_vec.allocator)

            last_evt = stage_inf.kernel(
                    use_queue,
                    (group_count*stage_inf.group_size,),
                    (stage_inf.group_size,),
                    *([result.data]+invocation_args+[seq_count, sz]),
                    **dict(wait_for=wait_for))
            wait_for = [last_evt]

            if group_count == 1:
                if return_event:
                    return result, last_evt
                else:
                    return result
            else:
                stage_inf = self.stage_2_inf
                args = (result,) + stage1_args

# }}}


# {{{ template

class ReductionTemplate(KernelTemplateBase):
    def __init__(self,
            arguments, neutral, reduce_expr, map_expr=None,
            is_segment_start_expr=None, input_fetch_exprs=[],
            name_prefix="reduce", preamble="", template_processor=None):

        KernelTemplateBase.__init__(
                self, template_processor=template_processor)
        self.arguments = arguments
        self.reduce_expr = reduce_expr
        self.neutral = neutral
        self.map_expr = map_expr
        self.name_prefix = name_prefix
        self.preamble = preamble

    def build_inner(self, context, type_aliases=(), var_values=(),
            more_preamble="", more_arguments=(), declare_types=(),
            options=(), devices=None):
        renderer = self.get_renderer(
                type_aliases, var_values, context, options)

        arg_list = renderer.render_argument_list(
                self.arguments, more_arguments)

        type_decl_preamble = renderer.get_type_decl_preamble(
                context.devices[0], declare_types, arg_list)

        return ReductionKernel(context, renderer.type_aliases["reduction_t"],
                renderer(self.neutral), renderer(self.reduce_expr),
                renderer(self.map_expr),
                renderer.render_argument_list(self.arguments, more_arguments),
                name=renderer(self.name_prefix), options=list(options),
                preamble=(
                    type_decl_preamble
                    + "\n"
                    + renderer(self.preamble + "\n" + more_preamble)))

# }}}


# {{{ array reduction kernel getters

@context_dependent_memoize
def get_any_kernel(ctx, dtype_in):
    from pyopencl.tools import VectorArg
    return ReductionKernel(ctx, np.int8, "false", "a || b",
            map_expr="(bool) (in[i])",
            arguments=[VectorArg(dtype_in, "in")])


@context_dependent_memoize
def get_all_kernel(ctx, dtype_in):
    from pyopencl.tools import VectorArg
    return ReductionKernel(ctx, np.int8, "true", "a && b",
            map_expr="(bool) (in[i])",
            arguments=[VectorArg(dtype_in, "in")])


@context_dependent_memoize
def get_sum_kernel(ctx, dtype_out, dtype_in):
    if dtype_out is None:
        dtype_out = dtype_in

    return ReductionKernel(ctx, dtype_out, "0", "a+b",
            arguments="const %(tp)s *in"
            % {"tp": dtype_to_ctype(dtype_in)})


def _get_dot_expr(dtype_out, dtype_a, dtype_b, conjugate_first,
        has_double_support, index_expr="i"):
    if dtype_b is None:
        if dtype_a is None:
            dtype_b = dtype_out
        else:
            dtype_b = dtype_a

    if dtype_out is None:
        from pyopencl.compyte.array import get_common_dtype
        dtype_out = get_common_dtype(
                dtype_a.type(0), dtype_b.type(0),
                has_double_support)

    a_real_dtype = dtype_a.type(0).real.dtype
    b_real_dtype = dtype_b.type(0).real.dtype
    out_real_dtype = dtype_out.type(0).real.dtype

    a_is_complex = dtype_a.kind == "c"
    b_is_complex = dtype_b.kind == "c"
    out_is_complex = dtype_out.kind == "c"

    from pyopencl.elementwise import complex_dtype_to_name

    if a_is_complex and b_is_complex:
        a = "a[%s]" % index_expr
        b = "b[%s]" % index_expr
        if dtype_a != dtype_out:
            a = "%s_cast(%s)" % (complex_dtype_to_name(dtype_out), a)
        if dtype_b != dtype_out:
            b = "%s_cast(%s)" % (complex_dtype_to_name(dtype_out), b)

        if conjugate_first and a_is_complex:
            a = "%s_conj(%s)" % (
                    complex_dtype_to_name(dtype_out), a)

        map_expr = "%s_mul(%s, %s)" % (
                complex_dtype_to_name(dtype_out), a, b)
    else:
        a = "a[%s]" % index_expr
        b = "b[%s]" % index_expr

        if out_is_complex:
            if a_is_complex and dtype_a != dtype_out:
                a = "%s_cast(%s)" % (complex_dtype_to_name(dtype_out), a)
            if b_is_complex and dtype_b != dtype_out:
                b = "%s_cast(%s)" % (complex_dtype_to_name(dtype_out), b)

            if not a_is_complex and a_real_dtype != out_real_dtype:
                a = "(%s) (%s)" % (dtype_to_ctype(out_real_dtype), a)
            if not b_is_complex and b_real_dtype != out_real_dtype:
                b = "(%s) (%s)" % (dtype_to_ctype(out_real_dtype), b)

        if conjugate_first and a_is_complex:
            a = "%s_conj(%s)" % (
                    complex_dtype_to_name(dtype_out), a)

        map_expr = "%s*%s" % (a, b)

    return map_expr, dtype_out, dtype_b


@context_dependent_memoize
def get_dot_kernel(ctx, dtype_out, dtype_a=None, dtype_b=None,
        conjugate_first=False):
    from pyopencl.characterize import has_double_support
    map_expr, dtype_out, dtype_b = _get_dot_expr(
            dtype_out, dtype_a, dtype_b, conjugate_first,
            has_double_support=has_double_support(ctx.devices[0]))

    return ReductionKernel(ctx, dtype_out, neutral="0",
            reduce_expr="a+b", map_expr=map_expr,
            arguments=
            "const %(tp_a)s *a, "
            "const %(tp_b)s *b" % {
                "tp_a": dtype_to_ctype(dtype_a),
                "tp_b": dtype_to_ctype(dtype_b),
                })


@context_dependent_memoize
def get_subset_dot_kernel(ctx, dtype_out, dtype_subset, dtype_a=None, dtype_b=None,
        conjugate_first=False):
    from pyopencl.characterize import has_double_support
    map_expr, dtype_out, dtype_b = _get_dot_expr(
            dtype_out, dtype_a, dtype_b, conjugate_first,
            has_double_support=has_double_support(ctx.devices[0]),
            index_expr="lookup_tbl[i]")

    # important: lookup_tbl must be first--it controls the length
    return ReductionKernel(ctx, dtype_out, neutral="0",
            reduce_expr="a+b", map_expr=map_expr,
            arguments=
            "const %(tp_lut)s *lookup_tbl, "
            "const %(tp_a)s *a, "
            "const %(tp_b)s *b" % {
            "tp_lut": dtype_to_ctype(dtype_subset),
            "tp_a": dtype_to_ctype(dtype_a),
            "tp_b": dtype_to_ctype(dtype_b),
            })


def get_minmax_neutral(what, dtype):
    dtype = np.dtype(dtype)
    if issubclass(dtype.type, np.inexact):
        if what == "min":
            return "MY_INFINITY"
        elif what == "max":
            return "-MY_INFINITY"
        else:
            raise ValueError("what is not min or max.")
    else:
        if what == "min":
            return str(np.iinfo(dtype).max)
        elif what == "max":
            return str(np.iinfo(dtype).min)
        else:
            raise ValueError("what is not min or max.")


@context_dependent_memoize
def get_minmax_kernel(ctx, what, dtype):
    if dtype.kind == "f":
        reduce_expr = "f%s(a,b)" % what
    elif dtype.kind in "iu":
        reduce_expr = "%s(a,b)" % what
    else:
        raise TypeError("unsupported dtype specified")

    return ReductionKernel(ctx, dtype,
            neutral=get_minmax_neutral(what, dtype),
            reduce_expr="%(reduce_expr)s" % {"reduce_expr": reduce_expr},
            arguments="const %(tp)s *in" % {
                "tp": dtype_to_ctype(dtype),
                }, preamble="#define MY_INFINITY (1./0)")


@context_dependent_memoize
def get_subset_minmax_kernel(ctx, what, dtype, dtype_subset):
    if dtype.kind == "f":
        reduce_expr = "f%s(a,b)" % what
    elif dtype.kind in "iu":
        reduce_expr = "%s(a,b)" % what
    else:
        raise TypeError("unsupported dtype specified")

    return ReductionKernel(ctx, dtype,
            neutral=get_minmax_neutral(what, dtype),
            reduce_expr="%(reduce_expr)s" % {"reduce_expr": reduce_expr},
            map_expr="in[lookup_tbl[i]]",
            arguments=
            "const %(tp_lut)s *lookup_tbl, "
            "const %(tp)s *in" % {
            "tp": dtype_to_ctype(dtype),
            "tp_lut": dtype_to_ctype(dtype_subset),
            }, preamble="#define MY_INFINITY (1./0)")

# }}}

# vim: filetype=pyopencl:fdm=marker

########NEW FILE########
__FILENAME__ = scan
"""Scan primitive."""

from __future__ import division

__copyright__ = """
Copyright 2011-2012 Andreas Kloeckner
Copyright 2008-2011 NVIDIA Corporation
"""

__license__ = """
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Derived from thrust/detail/backend/cuda/detail/fast_scan.inl
within the Thrust project, https://code.google.com/p/thrust/

"""

# Direct link to thrust source:
# https://code.google.com/p/thrust/source/browse/thrust/detail/backend/cuda/detail/fast_scan.inl # noqa

import numpy as np

import pyopencl as cl
import pyopencl.array  # noqa
from pyopencl.tools import (dtype_to_ctype, bitlog2,
        KernelTemplateBase, _process_code_for_macro,
        get_arg_list_scalar_arg_dtypes,
        context_dependent_memoize)

import pyopencl._mymako as mako
from pyopencl._cluda import CLUDA_PREAMBLE


# {{{ preamble

SHARED_PREAMBLE = CLUDA_PREAMBLE + """//CL//
#define WG_SIZE ${wg_size}

#define SCAN_EXPR(a, b, across_seg_boundary) ${scan_expr}
#define INPUT_EXPR(i) (${input_expr})
%if is_segmented:
    #define IS_SEG_START(i, a) (${is_segment_start_expr})
%endif

${preamble}

typedef ${dtype_to_ctype(scan_dtype)} scan_type;
typedef ${dtype_to_ctype(index_dtype)} index_type;

// NO_SEG_BOUNDARY is the largest representable integer in index_type.
// This assumption is used in code below.
#define NO_SEG_BOUNDARY ${str(np.iinfo(index_dtype).max)}
"""

# }}}

# {{{ main scan code

# Algorithm: Each work group is responsible for one contiguous
# 'interval'. There are just enough intervals to fill all compute
# units.  Intervals are split into 'units'. A unit is what gets
# worked on in parallel by one work group.
#
# in index space:
# interval > unit > local-parallel > k-group
#
# (Note that there is also a transpose in here: The data is read
# with local ids along linear index order.)
#
# Each unit has two axes--the local-id axis and the k axis.
#
# unit 0:
# | | | | | | | | | | ----> lid
# | | | | | | | | | |
# | | | | | | | | | |
# | | | | | | | | | |
# | | | | | | | | | |
#
# |
# v k (fastest-moving in linear index)
#
# unit 1:
# | | | | | | | | | | ----> lid
# | | | | | | | | | |
# | | | | | | | | | |
# | | | | | | | | | |
# | | | | | | | | | |
#
# |
# v k (fastest-moving in linear index)
#
# ...
#
# At a device-global level, this is a three-phase algorithm, in
# which first each interval does its local scan, then a scan
# across intervals exchanges data globally, and the final update
# adds the exchanged sums to each interval.
#
# Exclusive scan is realized by allowing look-behind (access to the
# preceding item) in the final update, by means of a local shift.
#
# NOTE: All segment_start_in_X indices are relative to the start
# of the array.

SCAN_INTERVALS_SOURCE = SHARED_PREAMBLE + r"""//CL//

#define K ${k_group_size}

// #define DEBUG
#ifdef DEBUG
    #define pycl_printf(ARGS) printf ARGS
#else
    #define pycl_printf(ARGS) /* */
#endif

KERNEL
REQD_WG_SIZE(WG_SIZE, 1, 1)
void ${kernel_name}(
    ${argument_signature},
    GLOBAL_MEM scan_type *restrict partial_scan_buffer,
    const index_type N,
    const index_type interval_size
    %if is_first_level:
        , GLOBAL_MEM scan_type *restrict interval_results
    %endif
    %if is_segmented and is_first_level:
        // NO_SEG_BOUNDARY if no segment boundary in interval.
        , GLOBAL_MEM index_type *restrict g_first_segment_start_in_interval
    %endif
    %if store_segment_start_flags:
        , GLOBAL_MEM char *restrict g_segment_start_flags
    %endif
    )
{
    // index K in first dimension used for carry storage
    %if use_bank_conflict_avoidance:
        // Avoid bank conflicts by adding a single 32-bit value to the size of
        // the scan type.
        struct __attribute__ ((__packed__)) wrapped_scan_type
        {
            scan_type value;
            int dummy;
        };
        LOCAL_MEM struct wrapped_scan_type ldata[K + 1][WG_SIZE + 1];
    %else:
        struct wrapped_scan_type
        {
            scan_type value;
        };

        // padded in WG_SIZE to avoid bank conflicts
        LOCAL_MEM struct wrapped_scan_type ldata[K + 1][WG_SIZE];
    %endif

    %if is_segmented:
        LOCAL_MEM char l_segment_start_flags[K][WG_SIZE];
        LOCAL_MEM index_type l_first_segment_start_in_subtree[WG_SIZE];

        // only relevant/populated for local id 0
        index_type first_segment_start_in_interval = NO_SEG_BOUNDARY;

        index_type first_segment_start_in_k_group, first_segment_start_in_subtree;
    %endif

    // {{{ declare local data for input_fetch_exprs if any of them are stenciled

    <%
        fetch_expr_offsets = {}
        for name, arg_name, ife_offset in input_fetch_exprs:
            fetch_expr_offsets.setdefault(arg_name, set()).add(ife_offset)

        local_fetch_expr_args = set(
            arg_name
            for arg_name, ife_offsets in fetch_expr_offsets.items()
            if -1 in ife_offsets or len(ife_offsets) > 1)
    %>

    %for arg_name in local_fetch_expr_args:
        LOCAL_MEM ${arg_ctypes[arg_name]} l_${arg_name}[WG_SIZE*K];
    %endfor

    // }}}

    const index_type interval_begin = interval_size * GID_0;
    const index_type interval_end   = min(interval_begin + interval_size, N);

    const index_type unit_size  = K * WG_SIZE;

    index_type unit_base = interval_begin;

    %for is_tail in [False, True]:

        %if not is_tail:
            for(; unit_base + unit_size <= interval_end; unit_base += unit_size)
        %else:
            if (unit_base < interval_end)
        %endif

        {

            // {{{ carry out input_fetch_exprs
            // (if there are ones that need to be fetched into local)

            %if local_fetch_expr_args:
                for(index_type k = 0; k < K; k++)
                {
                    const index_type offset = k*WG_SIZE + LID_0;
                    const index_type read_i = unit_base + offset;

                    %for arg_name in local_fetch_expr_args:
                        %if is_tail:
                        if (read_i < interval_end)
                        %endif
                        {
                            l_${arg_name}[offset] = ${arg_name}[read_i];
                        }
                    %endfor
                }

                local_barrier();
            %endif

            pycl_printf(("after input_fetch_exprs\n"));

            // }}}

            // {{{ read a unit's worth of data from global

            for(index_type k = 0; k < K; k++)
            {
                const index_type offset = k*WG_SIZE + LID_0;
                const index_type read_i = unit_base + offset;

                %if is_tail:
                if (read_i < interval_end)
                %endif
                {
                    %for name, arg_name, ife_offset in input_fetch_exprs:
                        ${arg_ctypes[arg_name]} ${name};

                        %if arg_name in local_fetch_expr_args:
                            if (offset + ${ife_offset} >= 0)
                                ${name} = l_${arg_name}[offset + ${ife_offset}];
                            else if (read_i + ${ife_offset} >= 0)
                                ${name} = ${arg_name}[read_i + ${ife_offset}];
                            /*
                            else
                                if out of bounds, name is left undefined */

                        %else:
                            // ${arg_name} gets fetched directly from global
                            ${name} = ${arg_name}[read_i];

                        %endif
                    %endfor

                    scan_type scan_value = INPUT_EXPR(read_i);

                    const index_type o_mod_k = offset % K;
                    const index_type o_div_k = offset / K;
                    ldata[o_mod_k][o_div_k].value = scan_value;

                    %if is_segmented:
                        bool is_seg_start = IS_SEG_START(read_i, scan_value);
                        l_segment_start_flags[o_mod_k][o_div_k] = is_seg_start;
                    %endif
                    %if store_segment_start_flags:
                        g_segment_start_flags[read_i] = is_seg_start;
                    %endif
                }
            }

            pycl_printf(("after read from global\n"));

            // }}}

            // {{{ carry in from previous unit, if applicable

            %if is_segmented:
                local_barrier();

                first_segment_start_in_k_group = NO_SEG_BOUNDARY;
                if (l_segment_start_flags[0][LID_0])
                    first_segment_start_in_k_group = unit_base + K*LID_0;
            %endif

            if (LID_0 == 0 && unit_base != interval_begin)
            {
                ldata[0][0].value = SCAN_EXPR(
                    ldata[K][WG_SIZE - 1].value, ldata[0][0].value,
                    %if is_segmented:
                        (l_segment_start_flags[0][0])
                    %else:
                        false
                    %endif
                    );
            }

            pycl_printf(("after carry-in\n"));

            // }}}

            local_barrier();

            // {{{ scan along k (sequentially in each work item)

            scan_type sum = ldata[0][LID_0].value;

            %if is_tail:
                const index_type offset_end = interval_end - unit_base;
            %endif

            for(index_type k = 1; k < K; k++)
            {
                %if is_tail:
                if (K * LID_0 + k < offset_end)
                %endif
                {
                    scan_type tmp = ldata[k][LID_0].value;
                    index_type seq_i = unit_base + K*LID_0 + k;

                    %if is_segmented:
                    if (l_segment_start_flags[k][LID_0])
                    {
                        first_segment_start_in_k_group = min(
                            first_segment_start_in_k_group,
                            seq_i);
                    }
                    %endif

                    sum = SCAN_EXPR(sum, tmp,
                        %if is_segmented:
                            (l_segment_start_flags[k][LID_0])
                        %else:
                            false
                        %endif
                        );

                    ldata[k][LID_0].value = sum;
                }
            }

            pycl_printf(("after scan along k\n"));

            // }}}

            // store carry in out-of-bounds (padding) array entry (index K) in
            // the K direction
            ldata[K][LID_0].value = sum;

            %if is_segmented:
                l_first_segment_start_in_subtree[LID_0] =
                    first_segment_start_in_k_group;
            %endif

            local_barrier();

            // {{{ tree-based local parallel scan

            // This tree-based scan works as follows:
            // - Each work item adds the previous item to its current state
            // - barrier
            // - Each work item adds in the item from two positions to the left
            // - barrier
            // - Each work item adds in the item from four positions to the left
            // ...
            // At the end, each item has summed all prior items.

            // across k groups, along local id
            // (uses out-of-bounds k=K array entry for storage)

            scan_type val = ldata[K][LID_0].value;

            <% scan_offset = 1 %>

            % while scan_offset <= wg_size:
                // {{{ reads from local allowed, writes to local not allowed

                if (LID_0 >= ${scan_offset})
                {
                    scan_type tmp = ldata[K][LID_0 - ${scan_offset}].value;
                    % if is_tail:
                    if (K*LID_0 < offset_end)
                    % endif
                    {
                        val = SCAN_EXPR(tmp, val,
                            %if is_segmented:
                                (l_first_segment_start_in_subtree[LID_0]
                                    != NO_SEG_BOUNDARY)
                            %else:
                                false
                            %endif
                            );
                    }

                    %if is_segmented:
                        // Prepare for l_first_segment_start_in_subtree, below.

                        // Note that this update must take place *even* if we're
                        // out of bounds.

                        first_segment_start_in_subtree = min(
                            l_first_segment_start_in_subtree[LID_0],
                            l_first_segment_start_in_subtree
                                [LID_0 - ${scan_offset}]);
                    %endif
                }
                %if is_segmented:
                    else
                    {
                        first_segment_start_in_subtree =
                            l_first_segment_start_in_subtree[LID_0];
                    }
                %endif

                // }}}

                local_barrier();

                // {{{ writes to local allowed, reads from local not allowed

                ldata[K][LID_0].value = val;
                %if is_segmented:
                    l_first_segment_start_in_subtree[LID_0] =
                        first_segment_start_in_subtree;
                %endif

                // }}}

                local_barrier();

                %if 0:
                if (LID_0 == 0)
                {
                    printf("${scan_offset}: ");
                    for (int i = 0; i < WG_SIZE; ++i)
                    {
                        if (l_first_segment_start_in_subtree[i] == NO_SEG_BOUNDARY)
                            printf("- ");
                        else
                            printf("%d ", l_first_segment_start_in_subtree[i]);
                    }
                    printf("\n");
                }
                %endif

                <% scan_offset *= 2 %>
            % endwhile

            pycl_printf(("after tree scan\n"));

            // }}}

            // {{{ update local values

            if (LID_0 > 0)
            {
                sum = ldata[K][LID_0 - 1].value;

                for(index_type k = 0; k < K; k++)
                {
                    %if is_tail:
                    if (K * LID_0 + k < offset_end)
                    %endif
                    {
                        scan_type tmp = ldata[k][LID_0].value;
                        ldata[k][LID_0].value = SCAN_EXPR(sum, tmp,
                            %if is_segmented:
                                (unit_base + K * LID_0 + k
                                    >= first_segment_start_in_k_group)
                            %else:
                                false
                            %endif
                            );
                    }
                }
            }

            %if is_segmented:
                if (LID_0 == 0)
                {
                    // update interval-wide first-seg variable from current unit
                    first_segment_start_in_interval = min(
                        first_segment_start_in_interval,
                        l_first_segment_start_in_subtree[WG_SIZE-1]);
                }
            %endif

            pycl_printf(("after local update\n"));

            // }}}

            local_barrier();

            // {{{ write data

            %if is_gpu:
            {
                // work hard with index math to achieve contiguous 32-bit stores
                __global int *dest =
                    (__global int *) (partial_scan_buffer + unit_base);

                <%

                assert scan_dtype.itemsize % 4 == 0

                ints_per_wg = wg_size
                ints_to_store = scan_dtype.itemsize*wg_size*k_group_size // 4

                %>

                const index_type scan_types_per_int = ${scan_dtype.itemsize//4};

                %for store_base in range(0, ints_to_store, ints_per_wg):
                    <%

                    # Observe that ints_to_store is divisible by the work group
                    # size already, so we won't go out of bounds that way.
                    assert store_base + ints_per_wg <= ints_to_store

                    %>

                    %if is_tail:
                    if (${store_base} + LID_0 <
                        scan_types_per_int*(interval_end - unit_base))
                    %endif
                    {
                        index_type linear_index = ${store_base} + LID_0;
                        index_type linear_scan_data_idx =
                            linear_index / scan_types_per_int;
                        index_type remainder =
                            linear_index - linear_scan_data_idx * scan_types_per_int;

                        __local int *src = (__local int *) &(
                            ldata
                                [linear_scan_data_idx % K]
                                [linear_scan_data_idx / K].value);

                        dest[linear_index] = src[remainder];
                    }
                %endfor
            }
            %else:
            for (index_type k = 0; k < K; k++)
            {
                const index_type offset = k*WG_SIZE + LID_0;

                %if is_tail:
                if (unit_base + offset < interval_end)
                %endif
                {
                    pycl_printf(("write: %d\n", unit_base + offset));
                    partial_scan_buffer[unit_base + offset] =
                        ldata[offset % K][offset / K].value;
                }
            }
            %endif

            pycl_printf(("after write\n"));

            // }}}

            local_barrier();
        }

    % endfor

    // write interval sum
    %if is_first_level:
        if (LID_0 == 0)
        {
            interval_results[GID_0] = partial_scan_buffer[interval_end - 1];
            %if is_segmented:
                g_first_segment_start_in_interval[GID_0] =
                    first_segment_start_in_interval;
            %endif
        }
    %endif
}
"""

# }}}

# {{{ update

UPDATE_SOURCE = SHARED_PREAMBLE + r"""//CL//

KERNEL
REQD_WG_SIZE(WG_SIZE, 1, 1)
void ${name_prefix}_final_update(
    ${argument_signature},
    const index_type N,
    const index_type interval_size,
    GLOBAL_MEM scan_type *restrict interval_results,
    GLOBAL_MEM scan_type *restrict partial_scan_buffer
    %if is_segmented:
        , GLOBAL_MEM index_type *restrict g_first_segment_start_in_interval
    %endif
    %if is_segmented and use_lookbehind_update:
        , GLOBAL_MEM char *restrict g_segment_start_flags
    %endif
    )
{
    %if use_lookbehind_update:
        LOCAL_MEM scan_type ldata[WG_SIZE];
    %endif
    %if is_segmented and use_lookbehind_update:
        LOCAL_MEM char l_segment_start_flags[WG_SIZE];
    %endif

    const index_type interval_begin = interval_size * GID_0;
    const index_type interval_end = min(interval_begin + interval_size, N);

    // carry from last interval
    scan_type carry = ${neutral};
    if (GID_0 != 0)
        carry = interval_results[GID_0 - 1];

    %if is_segmented:
        const index_type first_seg_start_in_interval =
            g_first_segment_start_in_interval[GID_0];
    %endif

    %if not is_segmented and 'last_item' in output_statement:
        scan_type last_item = interval_results[GDIM_0-1];
    %endif

    %if not use_lookbehind_update:
        // {{{ no look-behind ('prev_item' not in output_statement -> simpler)

        index_type update_i = interval_begin+LID_0;

        %if is_segmented:
            index_type seg_end = min(first_seg_start_in_interval, interval_end);
        %endif

        for(; update_i < interval_end; update_i += WG_SIZE)
        {
            scan_type partial_val = partial_scan_buffer[update_i];
            scan_type item = SCAN_EXPR(carry, partial_val,
                %if is_segmented:
                    (update_i >= seg_end)
                %else:
                    false
                %endif
                );
            index_type i = update_i;

            { ${output_statement}; }
        }

        // }}}
    %else:
        // {{{ allow look-behind ('prev_item' in output_statement -> complicated)

        // We are not allowed to branch across barriers at a granularity smaller
        // than the whole workgroup. Therefore, the for loop is group-global,
        // and there are lots of local ifs.

        index_type group_base = interval_begin;
        scan_type prev_item = carry; // (A)

        for(; group_base < interval_end; group_base += WG_SIZE)
        {
            index_type update_i = group_base+LID_0;

            // load a work group's worth of data
            if (update_i < interval_end)
            {
                scan_type tmp = partial_scan_buffer[update_i];

                tmp = SCAN_EXPR(carry, tmp,
                    %if is_segmented:
                        (update_i >= first_seg_start_in_interval)
                    %else:
                        false
                    %endif
                    );

                ldata[LID_0] = tmp;

                %if is_segmented:
                    l_segment_start_flags[LID_0] = g_segment_start_flags[update_i];
                %endif
            }

            local_barrier();

            // find prev_item
            if (LID_0 != 0)
                prev_item = ldata[LID_0 - 1];
            /*
            else
                prev_item = carry (see (A)) OR last tail (see (B));
            */

            if (update_i < interval_end)
            {
                %if is_segmented:
                    if (l_segment_start_flags[LID_0])
                        prev_item = ${neutral};
                %endif

                scan_type item = ldata[LID_0];
                index_type i = update_i;
                { ${output_statement}; }
            }

            if (LID_0 == 0)
                prev_item = ldata[WG_SIZE - 1]; // (B)

            local_barrier();
        }

        // }}}
    %endif
}
"""

# }}}


# {{{ driver

# {{{ helpers

def _round_down_to_power_of_2(val):
    result = 2**bitlog2(val)
    if result > val:
        result >>= 1

    assert result <= val
    return result

_PREFIX_WORDS = set("""
        ldata partial_scan_buffer global scan_offset
        segment_start_in_k_group carry
        g_first_segment_start_in_interval IS_SEG_START tmp Z
        val l_first_segment_start_in_subtree unit_size
        index_type interval_begin interval_size offset_end K
        SCAN_EXPR do_update WG_SIZE
        first_segment_start_in_k_group scan_type
        segment_start_in_subtree offset interval_results interval_end
        first_segment_start_in_subtree unit_base
        first_segment_start_in_interval k INPUT_EXPR
        prev_group_sum prev pv value partial_val pgs
        is_seg_start update_i scan_item_at_i seq_i read_i
        l_ o_mod_k o_div_k l_segment_start_flags scan_value sum
        first_seg_start_in_interval g_segment_start_flags
        group_base seg_end my_val DEBUG ARGS
        ints_to_store ints_per_wg scan_types_per_int linear_index
        linear_scan_data_idx dest src store_base wrapped_scan_type
        dummy

        LID_2 LID_1 LID_0
        LDIM_0 LDIM_1 LDIM_2
        GDIM_0 GDIM_1 GDIM_2
        GID_0 GID_1 GID_2
        """.split())

_IGNORED_WORDS = set("""
        4 8 32

        typedef for endfor if void while endwhile endfor endif else const printf
        None return bool n char true false ifdef pycl_printf str range assert
        np iinfo max itemsize __packed__ struct restrict

        set iteritems len setdefault

        GLOBAL_MEM LOCAL_MEM_ARG WITHIN_KERNEL LOCAL_MEM KERNEL REQD_WG_SIZE
        local_barrier
        CLK_LOCAL_MEM_FENCE OPENCL EXTENSION
        pragma __attribute__ __global __kernel __local
        get_local_size get_local_id cl_khr_fp64 reqd_work_group_size
        get_num_groups barrier get_group_id

        _final_update _debug_scan kernel_name

        positions all padded integer its previous write based writes 0
        has local worth scan_expr to read cannot not X items False bank
        four beginning follows applicable item min each indices works side
        scanning right summed relative used id out index avoid current state
        boundary True across be This reads groups along Otherwise undetermined
        store of times prior s update first regardless Each number because
        array unit from segment conflicts two parallel 2 empty define direction
        CL padding work tree bounds values and adds
        scan is allowed thus it an as enable at in occur sequentially end no
        storage data 1 largest may representable uses entry Y meaningful
        computations interval At the left dimension know d
        A load B group perform shift tail see last OR
        this add fetched into are directly need
        gets them stenciled that undefined
        there up any ones or name only relevant populated
        even wide we Prepare int seg Note re below place take variable must
        intra Therefore find code assumption
        branch workgroup complicated granularity phase remainder than simpler
        We smaller look ifs lots self behind allow barriers whole loop
        after already Observe achieve contiguous stores hard go with by math
        size won t way divisible bit so Avoid declare adding single type

        is_tail is_first_level input_expr argument_signature preamble
        double_support neutral output_statement
        k_group_size name_prefix is_segmented index_dtype scan_dtype
        wg_size is_segment_start_expr fetch_expr_offsets
        arg_ctypes ife_offsets input_fetch_exprs def
        ife_offset arg_name local_fetch_expr_args update_body
        update_loop_lookbehind update_loop_plain update_loop
        use_lookbehind_update store_segment_start_flags
        update_loop first_seg scan_dtype dtype_to_ctype
        is_gpu use_bank_conflict_avoidance

        a b prev_item i last_item prev_value
        N NO_SEG_BOUNDARY across_seg_boundary
        """.split())


def _make_template(s):
    leftovers = set()

    def replace_id(match):
        # avoid name clashes with user code by adding 'psc_' prefix to
        # identifiers.

        word = match.group(1)
        if word in _IGNORED_WORDS:
            return word
        elif word in _PREFIX_WORDS:
            return "psc_"+word
        else:
            leftovers.add(word)
            return word

    import re
    s = re.sub(r"\b([a-zA-Z0-9_]+)\b", replace_id, s)

    if leftovers:
        from warnings import warn
        warn("leftover words in identifier prefixing: " + " ".join(leftovers))

    return mako.template.Template(s, strict_undefined=True)

from pytools import Record


class _ScanKernelInfo(Record):
    pass

# }}}


class ScanPerformanceWarning(UserWarning):
    pass


class _GenericScanKernelBase(object):
    # {{{ constructor, argument processing

    def __init__(self, ctx, dtype,
            arguments, input_expr, scan_expr, neutral, output_statement,
            is_segment_start_expr=None, input_fetch_exprs=[],
            index_dtype=np.int32,
            name_prefix="scan", options=[], preamble="", devices=None):
        """
        :arg ctx: a :class:`pyopencl.Context` within which the code
            for this scan kernel will be generated.
        :arg dtype: the :class:`numpy.dtype` with which the scan will
            be performed. May be a structured type if that type was registered
            through :func:`pyopencl.tools.get_or_register_dtype`.
        :arg arguments: A string of comma-separated C argument declarations.
            If *arguments* is specified, then *input_expr* must also be
            specified. All types used here must be known to PyOpenCL.
            (see :func:`pyopencl.tools.get_or_register_dtype`).
        :arg scan_expr: The associative, binary operation carrying out the scan,
            represented as a C string. Its two arguments are available as `a`
            and `b` when it is evaluated. `b` is guaranteed to be the
            'element being updated', and `a` is the increment. Thus,
            if some data is supposed to just propagate along without being
            modified by the scan, it should live in `b`.

            This expression may call functions given in the *preamble*.

            Another value available to this expression is `across_seg_boundary`,
            a C `bool` indicating whether this scan update is crossing a
            segment boundary, as defined by `is_segment_start_expr`.
            The scan routine does not implement segmentation
            semantics on its own. It relies on `scan_expr` to do this.
            This value is available (but always `false`) even for a
            non-segmented scan.

            .. note::

                In early pre-releases of the segmented scan,
                segmentation semantics were implemented *without*
                relying on `scan_expr`.

        :arg input_expr: A C expression, encoded as a string, resulting
            in the values to which the scan is applied. This may be used
            to apply a mapping to values stored in *arguments* before being
            scanned. The result of this expression must match *dtype*.
            The index intended to be mapped is available as `i` in this
            expression. This expression may also use the variables defined
            by *input_fetch_expr*.

            This expression may also call functions given in the *preamble*.
        :arg output_statement: a C statement that writes
            the output of the scan. It has access to the scan result as `item`,
            the preceding scan result item as `prev_item`, and the current index
            as `i`. `prev_item` in a segmented scan will be the neutral element
            at a segment boundary, not the immediately preceding item.

            Using *prev_item* in output statement has a small run-time cost.
            `prev_item` enables the construction of an exclusive scan.

            For non-segmented scans, *output_statement* may also reference
            `last_item`, which evaluates to the scan result of the last
            array entry.
        :arg is_segment_start_expr: A C expression, encoded as a string,
            resulting in a C `bool` value that determines whether a new
            scan segments starts at index *i*.  If given, makes the scan a
            segmented scan. Has access to the current index `i`, the result
            of *input_expr* as a, and in addition may use *arguments* and
            *input_fetch_expr* variables just like *input_expr*.

            If it returns true, then previous sums will not spill over into the
            item with index *i* or subsequent items.
        :arg input_fetch_exprs: a list of tuples *(NAME, ARG_NAME, OFFSET)*.
            An entry here has the effect of doing the equivalent of the following
            before input_expr::

                ARG_NAME_TYPE NAME = ARG_NAME[i+OFFSET];

            `OFFSET` is allowed to be 0 or -1, and `ARG_NAME_TYPE` is the type
            of `ARG_NAME`.
        :arg preamble: |preamble|

        The first array in the argument list determines the size of the index
        space over which the scan is carried out, and thus the values over
        which the index *i* occurring in a number of code fragments in
        arguments above will vary.

        All code fragments further have access to N, the number of elements
        being processed in the scan.
        """

        self.context = ctx
        dtype = self.dtype = np.dtype(dtype)

        if neutral is None:
            from warnings import warn
            warn("not specifying 'neutral' is deprecated and will lead to "
                    "wrong results if your scan is not in-place or your "
                    "'output_statement' does something otherwise non-trivial",
                    stacklevel=2)

        if dtype.itemsize % 4 != 0:
            raise TypeError("scan value type must have size divisible by 4 bytes")

        self.index_dtype = np.dtype(index_dtype)
        if np.iinfo(self.index_dtype).min >= 0:
            raise TypeError("index_dtype must be signed")

        if devices is None:
            devices = ctx.devices
        self.devices = devices
        self.options = options

        from pyopencl.tools import parse_arg_list
        self.parsed_args = parse_arg_list(arguments)
        from pyopencl.tools import VectorArg
        self.first_array_idx = [
                i for i, arg in enumerate(self.parsed_args)
                if isinstance(arg, VectorArg)][0]

        self.input_expr = input_expr

        self.is_segment_start_expr = is_segment_start_expr
        self.is_segmented = is_segment_start_expr is not None
        if self.is_segmented:
            is_segment_start_expr = _process_code_for_macro(is_segment_start_expr)

        self.output_statement = output_statement

        for name, arg_name, ife_offset in input_fetch_exprs:
            if ife_offset not in [0, -1]:
                raise RuntimeError("input_fetch_expr offsets must either be 0 or -1")
        self.input_fetch_exprs = input_fetch_exprs

        arg_dtypes = {}
        arg_ctypes = {}
        for arg in self.parsed_args:
            arg_dtypes[arg.name] = arg.dtype
            arg_ctypes[arg.name] = dtype_to_ctype(arg.dtype)

        self.options = options
        self.name_prefix = name_prefix

        # {{{ set up shared code dict

        from pytools import all
        from pyopencl.characterize import has_double_support

        self.code_variables = dict(
            np=np,
            dtype_to_ctype=dtype_to_ctype,
            preamble=preamble,
            name_prefix=name_prefix,
            index_dtype=self.index_dtype,
            scan_dtype=dtype,
            is_segmented=self.is_segmented,
            arg_dtypes=arg_dtypes,
            arg_ctypes=arg_ctypes,
            scan_expr=_process_code_for_macro(scan_expr),
            neutral=_process_code_for_macro(neutral),
            is_gpu=bool(self.devices[0].type & cl.device_type.GPU),
            double_support=all(
                has_double_support(dev) for dev in devices),
            )

        # }}}

        self.finish_setup()

    # }}}


class GenericScanKernel(_GenericScanKernelBase):
    """Generates and executes code that performs prefix sums ("scans") on
    arbitrary types, with many possible tweaks.

    Usage example::

        from pyopencl.scan import GenericScanKernel
        knl = GenericScanKernel(
                context, np.int32,
                arguments="__global int *ary",
                input_expr="ary[i]",
                scan_expr="a+b", neutral="0",
                output_statement="ary[i+1] = item;")

        a = cl.array.arange(queue, 10000, dtype=np.int32)
        scan_kernel(a, queue=queue)

    """

    def finish_setup(self):
        use_lookbehind_update = "prev_item" in self.output_statement
        self.store_segment_start_flags = self.is_segmented and use_lookbehind_update

        # {{{ find usable workgroup/k-group size, build first-level scan

        trip_count = 0

        avail_local_mem = min(
                dev.local_mem_size
                for dev in self.devices)

        is_cpu = self.devices[0].type & cl.device_type.CPU
        is_gpu = self.devices[0].type & cl.device_type.GPU

        if is_cpu:
            # (about the widest vector a CPU can support, also taking
            # into account that CPUs don't hide latency by large work groups
            max_scan_wg_size = 16
            wg_size_multiples = 4
        else:
            max_scan_wg_size = min(dev.max_work_group_size for dev in self.devices)
            wg_size_multiples = 64

        use_bank_conflict_avoidance = (
                self.dtype.itemsize > 4 and self.dtype.itemsize % 8 == 0 and is_gpu)

        # k_group_size should be a power of two because of in-kernel
        # division by that number.

        solutions = []
        for k_exp in range(0, 9):
            for wg_size in range(wg_size_multiples, max_scan_wg_size+1,
                    wg_size_multiples):

                k_group_size = 2**k_exp
                lmem_use = self.get_local_mem_use(wg_size, k_group_size,
                        use_bank_conflict_avoidance)
                if lmem_use + 256 <= avail_local_mem:
                    solutions.append((wg_size*k_group_size, k_group_size, wg_size))

        if is_gpu:
            from pytools import any
            for wg_size_floor in [256, 192, 128]:
                have_sol_above_floor = any(wg_size >= wg_size_floor
                        for _, _, wg_size in solutions)

                if have_sol_above_floor:
                    # delete all solutions not meeting the wg size floor
                    solutions = [(total, k_group_size, wg_size)
                            for total, k_group_size, wg_size in solutions
                            if wg_size >= wg_size_floor]
                    break

        _, k_group_size, max_scan_wg_size = max(solutions)

        while True:
            candidate_scan_info = self.build_scan_kernel(
                    max_scan_wg_size, self.parsed_args,
                    _process_code_for_macro(self.input_expr),
                    self.is_segment_start_expr,
                    input_fetch_exprs=self.input_fetch_exprs,
                    is_first_level=True,
                    store_segment_start_flags=self.store_segment_start_flags,
                    k_group_size=k_group_size,
                    use_bank_conflict_avoidance=use_bank_conflict_avoidance)

            # Will this device actually let us execute this kernel
            # at the desired work group size? Building it is the
            # only way to find out.
            kernel_max_wg_size = min(
                    candidate_scan_info.kernel.get_work_group_info(
                        cl.kernel_work_group_info.WORK_GROUP_SIZE,
                        dev)
                    for dev in self.devices)

            if candidate_scan_info.wg_size <= kernel_max_wg_size:
                break
            else:
                max_scan_wg_size = min(kernel_max_wg_size, max_scan_wg_size)

            trip_count += 1
            assert trip_count <= 20

        self.first_level_scan_info = candidate_scan_info
        assert (_round_down_to_power_of_2(candidate_scan_info.wg_size)
                == candidate_scan_info.wg_size)

        # }}}

        # {{{ build second-level scan

        from pyopencl.tools import VectorArg
        second_level_arguments = self.parsed_args + [
                VectorArg(self.dtype, "interval_sums")]

        second_level_build_kwargs = {}
        if self.is_segmented:
            second_level_arguments.append(
                    VectorArg(self.index_dtype,
                        "g_first_segment_start_in_interval_input"))

            # is_segment_start_expr answers the question "should previous sums
            # spill over into this item". And since
            # g_first_segment_start_in_interval_input answers the question if a
            # segment boundary was found in an interval of data, then if not,
            # it's ok to spill over.
            second_level_build_kwargs["is_segment_start_expr"] = \
                    "g_first_segment_start_in_interval_input[i] != NO_SEG_BOUNDARY"
        else:
            second_level_build_kwargs["is_segment_start_expr"] = None

        self.second_level_scan_info = self.build_scan_kernel(
                max_scan_wg_size,
                arguments=second_level_arguments,
                input_expr="interval_sums[i]",
                input_fetch_exprs=[],
                is_first_level=False,
                store_segment_start_flags=False,
                k_group_size=k_group_size,
                use_bank_conflict_avoidance=use_bank_conflict_avoidance,
                **second_level_build_kwargs)

        # }}}

        # {{{ build final update kernel

        self.update_wg_size = min(max_scan_wg_size, 256)

        final_update_tpl = _make_template(UPDATE_SOURCE)
        final_update_src = str(final_update_tpl.render(
            wg_size=self.update_wg_size,
            output_statement=self.output_statement,
            argument_signature=", ".join(
                arg.declarator() for arg in self.parsed_args),
            is_segment_start_expr=self.is_segment_start_expr,
            input_expr=_process_code_for_macro(self.input_expr),
            use_lookbehind_update=use_lookbehind_update,
            **self.code_variables))

        final_update_prg = cl.Program(
                self.context, final_update_src).build(self.options)
        self.final_update_knl = getattr(
                final_update_prg,
                self.name_prefix+"_final_update")
        update_scalar_arg_dtypes = (
                get_arg_list_scalar_arg_dtypes(self.parsed_args)
                + [self.index_dtype, self.index_dtype, None, None])
        if self.is_segmented:
            # g_first_segment_start_in_interval
            update_scalar_arg_dtypes.append(None)
        if self.store_segment_start_flags:
            update_scalar_arg_dtypes.append(None)  # g_segment_start_flags
        self.final_update_knl.set_scalar_arg_dtypes(update_scalar_arg_dtypes)

        # }}}

    # {{{ scan kernel build/properties

    def get_local_mem_use(self, k_group_size, wg_size, use_bank_conflict_avoidance):
        arg_dtypes = {}
        for arg in self.parsed_args:
            arg_dtypes[arg.name] = arg.dtype

        fetch_expr_offsets = {}
        for name, arg_name, ife_offset in self.input_fetch_exprs:
            fetch_expr_offsets.setdefault(arg_name, set()).add(ife_offset)

        itemsize = self.dtype.itemsize
        if use_bank_conflict_avoidance:
            itemsize += 4

        return (
                # ldata
                itemsize*(k_group_size+1)*(wg_size+1)

                # l_segment_start_flags
                + k_group_size*wg_size

                # l_first_segment_start_in_subtree
                + self.index_dtype.itemsize*wg_size

                + k_group_size*wg_size*sum(
                    arg_dtypes[arg_name].itemsize
                    for arg_name, ife_offsets in fetch_expr_offsets.items()
                    if -1 in ife_offsets or len(ife_offsets) > 1))

    def build_scan_kernel(self, max_wg_size, arguments, input_expr,
            is_segment_start_expr, input_fetch_exprs, is_first_level,
            store_segment_start_flags, k_group_size,
            use_bank_conflict_avoidance):
        scalar_arg_dtypes = get_arg_list_scalar_arg_dtypes(arguments)

        # Empirically found on Nv hardware: no need to be bigger than this size
        wg_size = _round_down_to_power_of_2(
                min(max_wg_size, 256))

        kernel_name = self.code_variables["name_prefix"]+"_scan_intervals"
        if is_first_level:
            kernel_name += "_lev1"
        else:
            kernel_name += "_lev2"

        scan_tpl = _make_template(SCAN_INTERVALS_SOURCE)
        scan_src = str(scan_tpl.render(
            wg_size=wg_size,
            input_expr=input_expr,
            k_group_size=k_group_size,
            argument_signature=", ".join(arg.declarator() for arg in arguments),
            is_segment_start_expr=is_segment_start_expr,
            input_fetch_exprs=input_fetch_exprs,
            is_first_level=is_first_level,
            store_segment_start_flags=store_segment_start_flags,
            use_bank_conflict_avoidance=use_bank_conflict_avoidance,
            kernel_name=kernel_name,
            **self.code_variables))

        prg = cl.Program(self.context, scan_src).build(self.options)

        knl = getattr(prg, kernel_name)

        scalar_arg_dtypes.extend(
                (None, self.index_dtype, self. index_dtype))
        if is_first_level:
            scalar_arg_dtypes.append(None)  # interval_results
        if self.is_segmented and is_first_level:
            scalar_arg_dtypes.append(None)  # g_first_segment_start_in_interval
        if store_segment_start_flags:
            scalar_arg_dtypes.append(None)  # g_segment_start_flags
        knl.set_scalar_arg_dtypes(scalar_arg_dtypes)

        return _ScanKernelInfo(
                kernel=knl, wg_size=wg_size, knl=knl, k_group_size=k_group_size)

    # }}}

    def __call__(self, *args, **kwargs):
        # {{{ argument processing

        allocator = kwargs.get("allocator")
        queue = kwargs.get("queue")
        n = kwargs.get("size")
        wait_for = kwargs.get("wait_for")

        if len(args) != len(self.parsed_args):
            raise TypeError("expected %d arguments, got %d" %
                    (len(self.parsed_args), len(args)))

        first_array = args[self.first_array_idx]
        allocator = allocator or first_array.allocator
        queue = queue or first_array.queue

        if n is None:
            n, = first_array.shape

        if n == 0:
            # We're done here. (But pretend to return an event.)
            return cl.enqueue_marker(queue, wait_for=wait_for)

        data_args = []
        from pyopencl.tools import VectorArg
        for arg_descr, arg_val in zip(self.parsed_args, args):
            if isinstance(arg_descr, VectorArg):
                data_args.append(arg_val.data)
            else:
                data_args.append(arg_val)

        # }}}

        l1_info = self.first_level_scan_info
        l2_info = self.second_level_scan_info

        # see CL source above for terminology
        unit_size = l1_info.wg_size * l1_info.k_group_size
        max_intervals = 3*max(dev.max_compute_units for dev in self.devices)

        from pytools import uniform_interval_splitting
        interval_size, num_intervals = uniform_interval_splitting(
                n, unit_size, max_intervals)

        # {{{ allocate some buffers

        interval_results = cl.array.empty(queue,
                num_intervals, dtype=self.dtype,
                allocator=allocator)

        partial_scan_buffer = cl.array.empty(
                queue, n, dtype=self.dtype,
                allocator=allocator)

        if self.store_segment_start_flags:
            segment_start_flags = cl.array.empty(
                    queue, n, dtype=np.bool,
                    allocator=allocator)

        # }}}

        # {{{ first level scan of interval (one interval per block)

        scan1_args = data_args + [
                partial_scan_buffer.data, n, interval_size, interval_results.data,
                ]

        if self.is_segmented:
            first_segment_start_in_interval = cl.array.empty(queue,
                    num_intervals, dtype=self.index_dtype,
                    allocator=allocator)
            scan1_args.append(first_segment_start_in_interval.data)

        if self.store_segment_start_flags:
            scan1_args.append(segment_start_flags.data)

        l1_evt = l1_info.kernel(
                queue, (num_intervals,), (l1_info.wg_size,),
                *scan1_args, **dict(g_times_l=True, wait_for=wait_for))

        # }}}

        # {{{ second level scan of per-interval results

        # can scan at most one interval
        assert interval_size >= num_intervals

        scan2_args = data_args + [
                interval_results.data,  # interval_sums
                ]
        if self.is_segmented:
            scan2_args.append(first_segment_start_in_interval.data)
        scan2_args = scan2_args + [
                interval_results.data,  # partial_scan_buffer
                num_intervals, interval_size]

        l2_evt = l2_info.kernel(
                queue, (1,), (l1_info.wg_size,),
                *scan2_args, **dict(g_times_l=True, wait_for=[l1_evt]))

        # }}}

        # {{{ update intervals with result of interval scan

        upd_args = data_args + [
                n, interval_size, interval_results.data, partial_scan_buffer.data]
        if self.is_segmented:
            upd_args.append(first_segment_start_in_interval.data)
        if self.store_segment_start_flags:
            upd_args.append(segment_start_flags.data)

        return self.final_update_knl(
                queue, (num_intervals,), (self.update_wg_size,),
                *upd_args, **dict(g_times_l=True, wait_for=[l2_evt]))

        # }}}

# }}}

# {{{ debug kernel

DEBUG_SCAN_TEMPLATE = SHARED_PREAMBLE + r"""//CL//

KERNEL
REQD_WG_SIZE(1, 1, 1)
void ${name_prefix}_debug_scan(
    ${argument_signature},
    const index_type N)
{
    scan_type item = ${neutral};
    scan_type prev_item;

    for (index_type i = 0; i < N; ++i)
    {
        %for name, arg_name, ife_offset in input_fetch_exprs:
            ${arg_ctypes[arg_name]} ${name};
            %if ife_offset < 0:
                if (i+${ife_offset} >= 0)
                    ${name} = ${arg_name}[i+offset];
            %else:
                ${name} = ${arg_name}[i];
            %endif
        %endfor

        scan_type my_val = INPUT_EXPR(i);

        prev_item = item;
        %if is_segmented:
            bool is_seg_start = IS_SEG_START(i, my_val);
        %endif

        item = SCAN_EXPR(prev_item, my_val,
            %if is_segmented:
                is_seg_start
            %else:
                false
            %endif
            );

        {
            ${output_statement};
        }
    }
}
"""


class GenericDebugScanKernel(_GenericScanKernelBase):
    def finish_setup(self):
        scan_tpl = _make_template(DEBUG_SCAN_TEMPLATE)
        scan_src = str(scan_tpl.render(
            output_statement=self.output_statement,
            argument_signature=", ".join(
                arg.declarator() for arg in self.parsed_args),
            is_segment_start_expr=self.is_segment_start_expr,
            input_expr=_process_code_for_macro(self.input_expr),
            input_fetch_exprs=self.input_fetch_exprs,
            wg_size=1,
            **self.code_variables))

        scan_prg = cl.Program(self.context, scan_src).build(self.options)
        self.kernel = getattr(
                scan_prg, self.name_prefix+"_debug_scan")
        scalar_arg_dtypes = (
                get_arg_list_scalar_arg_dtypes(self.parsed_args)
                + [self.index_dtype])
        self.kernel.set_scalar_arg_dtypes(scalar_arg_dtypes)

    def __call__(self, *args, **kwargs):
        # {{{ argument processing

        allocator = kwargs.get("allocator")
        queue = kwargs.get("queue")
        n = kwargs.get("size")
        wait_for = kwargs.get("wait_for")

        if len(args) != len(self.parsed_args):
            raise TypeError("expected %d arguments, got %d" %
                    (len(self.parsed_args), len(args)))

        first_array = args[self.first_array_idx]
        allocator = allocator or first_array.allocator
        queue = queue or first_array.queue

        if n is None:
            n, = first_array.shape

        data_args = []
        from pyopencl.tools import VectorArg
        for arg_descr, arg_val in zip(self.parsed_args, args):
            if isinstance(arg_descr, VectorArg):
                data_args.append(arg_val.data)
            else:
                data_args.append(arg_val)

        # }}}

        return self.kernel(queue, (1,), (1,),
                *(data_args + [n]), **dict(wait_for=wait_for))

# }}}


# {{{ compatibility interface

class _LegacyScanKernelBase(GenericScanKernel):
    def __init__(self, ctx, dtype,
            scan_expr, neutral=None,
            name_prefix="scan", options=[], preamble="", devices=None):
        scan_ctype = dtype_to_ctype(dtype)
        GenericScanKernel.__init__(self,
                ctx, dtype,
                arguments="__global %s *input_ary, __global %s *output_ary" % (
                    scan_ctype, scan_ctype),
                input_expr="input_ary[i]",
                scan_expr=scan_expr,
                neutral=neutral,
                output_statement=self.ary_output_statement,
                options=options, preamble=preamble, devices=devices)

    def __call__(self, input_ary, output_ary=None, allocator=None, queue=None):
        allocator = allocator or input_ary.allocator
        queue = queue or input_ary.queue or output_ary.queue

        if output_ary is None:
            output_ary = input_ary

        if isinstance(output_ary, (str, unicode)) and output_ary == "new":
            output_ary = cl.array.empty_like(input_ary, allocator=allocator)

        if input_ary.shape != output_ary.shape:
            raise ValueError("input and output must have the same shape")

        if not input_ary.flags.forc:
            raise RuntimeError("ScanKernel cannot "
                    "deal with non-contiguous arrays")

        n, = input_ary.shape

        if not n:
            return output_ary

        GenericScanKernel.__call__(self,
                input_ary, output_ary, allocator=allocator, queue=queue)

        return output_ary


class InclusiveScanKernel(_LegacyScanKernelBase):
    ary_output_statement = "output_ary[i] = item;"


class ExclusiveScanKernel(_LegacyScanKernelBase):
    ary_output_statement = "output_ary[i] = prev_item;"

# }}}


# {{{ template

class ScanTemplate(KernelTemplateBase):
    def __init__(self,
            arguments, input_expr, scan_expr, neutral, output_statement,
            is_segment_start_expr=None, input_fetch_exprs=[],
            name_prefix="scan", preamble="", template_processor=None):

        KernelTemplateBase.__init__(self, template_processor=template_processor)
        self.arguments = arguments
        self.input_expr = input_expr
        self.scan_expr = scan_expr
        self.neutral = neutral
        self.output_statement = output_statement
        self.is_segment_start_expr = is_segment_start_expr
        self.input_fetch_exprs = input_fetch_exprs
        self.name_prefix = name_prefix
        self.preamble = preamble

    def build_inner(self, context, type_aliases=(), var_values=(),
            more_preamble="", more_arguments=(), declare_types=(),
            options=(), devices=None, scan_cls=GenericScanKernel):
        renderer = self.get_renderer(type_aliases, var_values, context, options)

        arg_list = renderer.render_argument_list(self.arguments, more_arguments)

        type_decl_preamble = renderer.get_type_decl_preamble(
                context.devices[0], declare_types, arg_list)

        return scan_cls(context, renderer.type_aliases["scan_t"],
            renderer.render_argument_list(self.arguments, more_arguments),
            renderer(self.input_expr), renderer(self.scan_expr),
            renderer(self.neutral), renderer(self.output_statement),
            is_segment_start_expr=renderer(self.is_segment_start_expr),
            input_fetch_exprs=self.input_fetch_exprs,
            index_dtype=renderer.type_aliases.get("index_t", np.int32),
            name_prefix=renderer(self.name_prefix), options=list(options),
            preamble=(
                type_decl_preamble
                + "\n"
                + renderer(self.preamble + "\n" + more_preamble)),
            devices=devices)

# }}}


# {{{ 'canned' scan kernels

@context_dependent_memoize
def get_cumsum_kernel(context, input_dtype, output_dtype):
    from pyopencl.tools import VectorArg
    return GenericScanKernel(
        context, output_dtype,
        arguments=[
            VectorArg(input_dtype, "input"),
            VectorArg(output_dtype, "output"),
            ],
        input_expr="input[i]",
        scan_expr="a+b", neutral="0",
        output_statement="""
            output[i] = item;
            """)

# }}}

# vim: filetype=pyopencl:fdm=marker

########NEW FILE########
__FILENAME__ = tools
"""Various helpful bits and pieces without much of a common theme."""

from __future__ import division

__copyright__ = "Copyright (C) 2010 Andreas Kloeckner"

__license__ = """
Permission is hereby granted, free of charge, to any person
obtaining a copy of this software and associated documentation
files (the "Software"), to deal in the Software without
restriction, including without limitation the rights to use,
copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following
conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.
"""


import numpy as np
from decorator import decorator
import pyopencl as cl
from pytools import memoize, memoize_method

import re

from pyopencl.compyte.dtypes import (  # noqa
        get_or_register_dtype, TypeNameNotKnown,
        register_dtype, dtype_to_ctype,
        dtype_hashable as _dtype_hashable,
        dtype_to_key as _dtype_to_key)


def _register_types():
    from pyopencl.compyte.dtypes import _fill_dtype_registry
    import struct

    _fill_dtype_registry(respect_windows=False, include_bool=False)

    get_or_register_dtype("cfloat_t", np.complex64)
    get_or_register_dtype("cdouble_t", np.complex128)

    is_64_bit = struct.calcsize('@P') * 8 == 64
    if not is_64_bit:
        get_or_register_dtype(
                ["unsigned long", "unsigned long int"], np.uint64)
        get_or_register_dtype(
                ["signed long", "signed long int", "long int"], np.int64)

_register_types()


# {{{ imported names

bitlog2 = cl.bitlog2

PooledBuffer = cl.PooledBuffer

from pyopencl._cl import _tools_DeferredAllocator as DeferredAllocator
from pyopencl._cl import (  # noqa
        _tools_ImmediateAllocator as ImmediateAllocator)


class CLAllocator(DeferredAllocator):
    def __init__(self, *args, **kwargs):
        from warnings import warn
        warn("pyopencl.tools.CLAllocator is deprecated. "
                "It will be continue to exist throughout the 2013.x "
                "versions of PyOpenCL. Use {Deferred,Immediate}Allocator.",
                DeprecationWarning, 2)
        DeferredAllocator.__init__(self, *args, **kwargs)

MemoryPool = cl.MemoryPool

# }}}


# {{{ first-arg caches

_first_arg_dependent_caches = []


@decorator
def first_arg_dependent_memoize(func, cl_object, *args):
    """Provides memoization for a function. Typically used to cache
    things that get created inside a :class:`pyopencl.Context`, e.g. programs
    and kernels. Assumes that the first argument of the decorated function is
    an OpenCL object that might go away, such as a :class:`pyopencl.Context` or
    a :class:`pyopencl.CommandQueue`, and based on which we might want to clear
    the cache.

    .. versionadded:: 2011.2
    """
    try:
        ctx_dict = func._pyopencl_first_arg_dep_memoize_dic
    except AttributeError:
        # FIXME: This may keep contexts alive longer than desired.
        # But I guess since the memory in them is freed, who cares.
        ctx_dict = func._pyopencl_first_arg_dep_memoize_dic = {}
        _first_arg_dependent_caches.append(ctx_dict)

    try:
        return ctx_dict[cl_object][args]
    except KeyError:
        arg_dict = ctx_dict.setdefault(cl_object, {})
        result = func(cl_object, *args)
        arg_dict[args] = result
        return result

context_dependent_memoize = first_arg_dependent_memoize


def first_arg_dependent_memoize_nested(nested_func):
    """Provides memoization for nested functions. Typically used to cache
    things that get created inside a :class:`pyopencl.Context`, e.g. programs
    and kernels. Assumes that the first argument of the decorated function is
    an OpenCL object that might go away, such as a :class:`pyopencl.Context` or
    a :class:`pyopencl.CommandQueue`, and will therefore respond to
    :func:`clear_first_arg_caches`.

    .. versionadded:: 2013.1

    Requires Python 2.5 or newer.
    """

    from functools import wraps
    cache_dict_name = intern("_memoize_inner_dic_%s_%s_%d"
            % (nested_func.__name__, nested_func.func_code.co_filename,
                nested_func.func_code.co_firstlineno))

    from inspect import currentframe
    # prevent ref cycle
    try:
        caller_frame = currentframe().f_back
        cache_context = caller_frame.f_globals[
                caller_frame.f_code.co_name]
    finally:
        #del caller_frame
        pass

    try:
        cache_dict = getattr(cache_context, cache_dict_name)
    except AttributeError:
        cache_dict = {}
        _first_arg_dependent_caches.append(cache_dict)
        setattr(cache_context, cache_dict_name, cache_dict)

    @wraps(nested_func)
    def new_nested_func(cl_object, *args):
        try:
            return cache_dict[cl_object][args]
        except KeyError:
            arg_dict = cache_dict.setdefault(cl_object, {})
            result = nested_func(cl_object, *args)
            arg_dict[args] = result
            return result

    return new_nested_func


def clear_first_arg_caches():
    """Empties all first-argument-dependent memoization caches. Also releases
    all held reference contexts. If it is important to you that the
    program detaches from its context, you might need to call this
    function to free all remaining references to your context.

    .. versionadded:: 2011.2
    """
    for cache in _first_arg_dependent_caches:
        cache.clear()

import atexit
atexit.register(clear_first_arg_caches)

# }}}


def get_test_platforms_and_devices(plat_dev_string=None):
    """Parse a string of the form 'PYOPENCL_TEST=0:0,1;intel:i5'.

    :return: list of tuples (platform, [device, device, ...])
    """

    if plat_dev_string is None:
        import os
        plat_dev_string = os.environ.get("PYOPENCL_TEST", None)

    def find_cl_obj(objs, identifier):
        try:
            num = int(identifier)
        except Exception:
            pass
        else:
            return objs[num]

        found = False
        for obj in objs:
            if identifier.lower() in (obj.name + ' ' + obj.vendor).lower():
                return obj
        if not found:
            raise RuntimeError("object '%s' not found" % identifier)

    if plat_dev_string:
        result = []

        for entry in plat_dev_string.split(";"):
            lhsrhs = entry.split(":")

            if len(lhsrhs) == 1:
                platform = find_cl_obj(cl.get_platforms(), lhsrhs[0])
                result.append((platform, platform.get_devices()))

            elif len(lhsrhs) != 2:
                raise RuntimeError("invalid syntax of PYOPENCL_TEST")
            else:
                plat_str, dev_strs = lhsrhs

                platform = find_cl_obj(cl.get_platforms(), plat_str)
                devs = platform.get_devices()
                result.append(
                        (platform,
                            [find_cl_obj(devs, dev_id)
                                for dev_id in dev_strs.split(",")]))

        return result

    else:
        return [
                (platform, platform.get_devices())
                for platform in cl.get_platforms()]


def pytest_generate_tests_for_pyopencl(metafunc):
    class ContextFactory:
        def __init__(self, device):
            self.device = device

        def __call__(self):
            # Get rid of leftovers from past tests.
            # CL implementations are surprisingly limited in how many
            # simultaneous contexts they allow...

            clear_first_arg_caches()

            from gc import collect
            collect()

            return cl.Context([self.device])

        def __str__(self):
            return "<context factory for %s>" % self.device

    test_plat_and_dev = get_test_platforms_and_devices()

    if ("device" in metafunc.funcargnames
            or "ctx_factory" in metafunc.funcargnames
            or "ctx_getter" in metafunc.funcargnames):
        arg_dict = {}

        for platform, plat_devs in test_plat_and_dev:
            if "platform" in metafunc.funcargnames:
                arg_dict["platform"] = platform

            for device in plat_devs:
                if "device" in metafunc.funcargnames:
                    arg_dict["device"] = device

                if "ctx_factory" in metafunc.funcargnames:
                    arg_dict["ctx_factory"] = ContextFactory(device)

                if "ctx_getter" in metafunc.funcargnames:
                    from warnings import warn
                    warn("The 'ctx_getter' arg is deprecated in "
                            "favor of 'ctx_factory'.",
                            DeprecationWarning)
                    arg_dict["ctx_getter"] = ContextFactory(device)

                metafunc.addcall(funcargs=arg_dict.copy(),
                        id=", ".join("%s=%s" % (arg, value)
                                for arg, value in arg_dict.iteritems()))

    elif "platform" in metafunc.funcargnames:
        for platform, plat_devs in test_plat_and_dev:
            metafunc.addcall(
                    funcargs=dict(platform=platform),
                    id=str(platform))


# {{{ C argument lists

class Argument(object):
    pass


class DtypedArgument(Argument):
    def __init__(self, dtype, name):
        self.dtype = np.dtype(dtype)
        self.name = name

    def __repr__(self):
        return "%s(%r, %s)" % (
                self.__class__.__name__,
                self.name,
                self.dtype)


class VectorArg(DtypedArgument):
    def __init__(self, dtype, name, with_offset=False):
        DtypedArgument.__init__(self, dtype, name)
        self.with_offset = with_offset

    def declarator(self):
        if self.with_offset:
            # Two underscores -> less likelihood of a name clash.
            return "__global %s *%s__base, long %s__offset" % (
                    dtype_to_ctype(self.dtype), self.name, self.name)
        else:
            result = "__global %s *%s" % (dtype_to_ctype(self.dtype), self.name)

        return result


class ScalarArg(DtypedArgument):
    def declarator(self):
        return "%s %s" % (dtype_to_ctype(self.dtype), self.name)


class OtherArg(Argument):
    def __init__(self, declarator, name):
        self.decl = declarator
        self.name = name

    def declarator(self):
        return self.decl


def parse_c_arg(c_arg, with_offset=False):
    for aspace in ["__local", "__constant"]:
        if aspace in c_arg:
            raise RuntimeError("cannot deal with local or constant "
                    "OpenCL address spaces in C argument lists ")

    c_arg = c_arg.replace("__global", "")

    if with_offset:
        vec_arg_factory = lambda dtype, name: \
                VectorArg(dtype, name, with_offset=True)
    else:
        vec_arg_factory = VectorArg

    from pyopencl.compyte.dtypes import parse_c_arg_backend
    return parse_c_arg_backend(c_arg, ScalarArg, vec_arg_factory)


def parse_arg_list(arguments, with_offset=False):
    """Parse a list of kernel arguments. *arguments* may be a comma-separate
    list of C declarators in a string, a list of strings representing C
    declarators, or :class:`Argument` objects.
    """

    if isinstance(arguments, str):
        arguments = arguments.split(",")

    def parse_single_arg(obj):
        if isinstance(obj, str):
            from pyopencl.tools import parse_c_arg
            return parse_c_arg(obj, with_offset=with_offset)
        else:
            return obj

    return [parse_single_arg(arg) for arg in arguments]


def get_arg_list_scalar_arg_dtypes(arg_types):
    result = []

    for arg_type in arg_types:
        if isinstance(arg_type, ScalarArg):
            result.append(arg_type.dtype)
        elif isinstance(arg_type, VectorArg):
            result.append(None)
            if arg_type.with_offset:
                result.append(np.int64)
        else:
            raise RuntimeError("arg type not understood: %s" % type(arg_type))

    return result


def get_arg_offset_adjuster_code(arg_types):
    result = []

    for arg_type in arg_types:
        if isinstance(arg_type, VectorArg) and arg_type.with_offset:
            result.append("__global %(type)s *%(name)s = "
                    "(__global %(type)s *) "
                    "((__global char *) %(name)s__base + %(name)s__offset);"
                    % dict(
                        type=dtype_to_ctype(arg_type.dtype),
                        name=arg_type.name))

    return "\n".join(result)


# }}}


def get_gl_sharing_context_properties():
    ctx_props = cl.context_properties

    from OpenGL import platform as gl_platform, GLX, WGL

    props = []

    import sys
    if sys.platform in ["linux", "linux2"]:
        props.append(
            (ctx_props.GL_CONTEXT_KHR, gl_platform.GetCurrentContext()))
        props.append(
                (ctx_props.GLX_DISPLAY_KHR,
                    GLX.glXGetCurrentDisplay()))
    elif sys.platform == "win32":
        props.append(
            (ctx_props.GL_CONTEXT_KHR, gl_platform.GetCurrentContext()))
        props.append(
                (ctx_props.WGL_HDC_KHR,
                    WGL.wglGetCurrentDC()))
    elif sys.platform == "darwin":
        props.append(
            (ctx_props.CONTEXT_PROPERTY_USE_CGL_SHAREGROUP_APPLE,
                cl.get_apple_cgl_share_group()))
    else:
        raise NotImplementedError("platform '%s' not yet supported"
                % sys.platform)

    return props


class _CDeclList:
    def __init__(self, device):
        self.device = device
        self.declared_dtypes = set()
        self.declarations = []
        self.saw_double = False
        self.saw_complex = False

    def add_dtype(self, dtype):
        dtype = np.dtype(dtype)

        if dtype in [np.float64 or np.complex128]:
            self.saw_double = True

        if dtype.kind == "c":
            self.saw_complex = True

        if dtype.kind != "V":
            return

        if dtype in self.declared_dtypes:
            return

        from pyopencl.array import vec
        if dtype in vec.type_to_scalar_and_count:
            return

        for name, field_data in dtype.fields.iteritems():
            field_dtype, offset = field_data[:2]
            self.add_dtype(field_dtype)

        _, cdecl = match_dtype_to_c_struct(
                self.device, dtype_to_ctype(dtype), dtype)

        self.declarations.append(cdecl)
        self.declared_dtypes.add(dtype)

    def visit_arguments(self, arguments):
        for arg in arguments:
            dtype = arg.dtype
            if dtype in [np.float64 or np.complex128]:
                self.saw_double = True

            if dtype.kind == "c":
                self.saw_complex = True

    def get_declarations(self):
        result = "\n\n".join(self.declarations)

        if self.saw_complex:
            result = (
                    "#include <pyopencl-complex.h>\n\n"
                    + result)

        if self.saw_double:
            result = (
                    "#pragma OPENCL EXTENSION cl_khr_fp64: enable\n"
                    "#define PYOPENCL_DEFINE_CDOUBLE\n"
                    + result)

        return result

if _dtype_hashable:
    _memoize_match_dtype_to_c_struct = memoize
else:
    import json as _json
    _memoize_match_dtype_to_c_struct = memoize(
        key=lambda device, name, dtype, context=None:
        (device, name, _dtype_to_key(dtype), context))

@_memoize_match_dtype_to_c_struct
def match_dtype_to_c_struct(device, name, dtype, context=None):
    """Return a tuple `(dtype, c_decl)` such that the C struct declaration
    in `c_decl` and the structure :class:`numpy.dtype` instance `dtype`
    have the same memory layout.

    Note that *dtype* may be modified from the value that was passed in,
    for example to insert padding.

    (As a remark on implementation, this routine runs a small kernel on
    the given *device* to ensure that :mod:`numpy` and C offsets and
    sizes match.)

    .. versionadded: 2013.1

    This example explains the use of this function::

        >>> import numpy as np
        >>> import pyopencl as cl
        >>> import pyopencl.tools
        >>> ctx = cl.create_some_context()
        >>> dtype = np.dtype([("id", np.uint32), ("value", np.float32)])
        >>> dtype, c_decl = pyopencl.tools.match_dtype_to_c_struct(
        ...     ctx.devices[0], 'id_val', dtype)
        >>> print c_decl
        typedef struct {
          unsigned id;
          float value;
        } id_val;
        >>> print dtype
        [('id', '<u4'), ('value', '<f4')]
        >>> cl.tools.get_or_register_dtype('id_val', dtype)

    As this example shows, it is important to call
    :func:`get_or_register_dtype` on the modified `dtype` returned by this
    function, not the original one.
    """

    fields = sorted(dtype.fields.iteritems(),
            key=lambda (name, (dtype, offset)): offset)

    c_fields = []
    for field_name, (field_dtype, offset) in fields:
        c_fields.append("  %s %s;" % (dtype_to_ctype(field_dtype), field_name))

    c_decl = "typedef struct {\n%s\n} %s;\n\n" % (
            "\n".join(c_fields),
            name)

    cdl = _CDeclList(device)
    for field_name, (field_dtype, offset) in fields:
        cdl.add_dtype(field_dtype)

    pre_decls = cdl.get_declarations()

    offset_code = "\n".join(
            "result[%d] = pycl_offsetof(%s, %s);" % (i+1, name, field_name)
            for i, (field_name, (field_dtype, offset)) in enumerate(fields))

    src = r"""
        #define pycl_offsetof(st, m) \
                 ((size_t) ((__local char *) &(dummy.m) \
                 - (__local char *)&dummy ))

        %(pre_decls)s

        %(my_decl)s

        __kernel void get_size_and_offsets(__global size_t *result)
        {
            result[0] = sizeof(%(my_type)s);
            __local %(my_type)s dummy;
            %(offset_code)s
        }
    """ % dict(
            pre_decls=pre_decls,
            my_decl=c_decl,
            my_type=name,
            offset_code=offset_code)

    if context is None:
        context = cl.Context([device])

    queue = cl.CommandQueue(context)

    prg = cl.Program(context, src)
    knl = prg.build(devices=[device]).get_size_and_offsets

    import pyopencl.array  # noqa
    result_buf = cl.array.empty(queue, 1+len(fields), np.uintp)
    knl(queue, (1,), (1,), result_buf.data)
    queue.finish()
    size_and_offsets = result_buf.get()

    size = int(size_and_offsets[0])

    from pytools import any
    offsets = size_and_offsets[1:]
    if any(ofs >= size for ofs in offsets):
        # offsets not plausible

        if dtype.itemsize == size:
            # If sizes match, use numpy's idea of the offsets.
            offsets = [offset
                    for field_name, (field_dtype, offset) in fields]
        else:
            raise RuntimeError(
                    "cannot discover struct layout on '%s'" % device)

    result_buf.data.release()
    del knl
    del prg
    del queue
    del context

    try:
        dtype_arg_dict = {
            'names': [field_name
                      for field_name, (field_dtype, offset) in fields],
            'formats': [field_dtype
                        for field_name, (field_dtype, offset) in fields],
            'offsets': [int(x) for x in offsets],
            'itemsize': int(size_and_offsets[0]),
            }
        dtype = np.dtype(dtype_arg_dict)
        if dtype.itemsize != size_and_offsets[0]:
            # "Old" versions of numpy (1.6.x?) silently ignore "itemsize". Boo.
            dtype_arg_dict["names"].append("_pycl_size_fixer")
            dtype_arg_dict["formats"].append(np.uint8)
            dtype_arg_dict["offsets"].append(int(size_and_offsets[0])-1)
            dtype = np.dtype(dtype_arg_dict)
    except NotImplementedError:
        def calc_field_type():
            total_size = 0
            padding_count = 0
            for offset, (field_name, (field_dtype, _)) in zip(offsets, fields):
                if offset > total_size:
                    padding_count += 1
                    yield ('__pycl_padding%d' % padding_count,
                           'V%d' % offset - total_size)
                yield field_name, field_dtype
                total_size = field_dtype.itemsize + offset
        dtype = np.dtype(list(calc_field_type()))

    assert dtype.itemsize == size_and_offsets[0]

    return dtype, c_decl

if _dtype_hashable:
    _memoize_dtype_to_c_struct = memoize
else:
    import json as _json
    _memoize_dtype_to_c_struct = memoize(
        key=lambda device, dtype: (device, _dtype_to_key(dtype)))

@_memoize_dtype_to_c_struct
def dtype_to_c_struct(device, dtype):
    matched_dtype, c_decl = match_dtype_to_c_struct(
            device, dtype_to_ctype(dtype), dtype)

    def dtypes_match():
        result = len(dtype.fields) == len(matched_dtype.fields)

        for name, val in dtype.fields.iteritems():
            result = result and matched_dtype.fields[name] == val

        return result

    assert dtypes_match()

    return c_decl


# {{{ code generation/templating helper

def _process_code_for_macro(code):
    code = code.replace("//CL//", "\n")

    if "//" in code:
        raise RuntimeError("end-of-line comments ('//') may not be used in "
                "code snippets")

    return code.replace("\n", " \\\n")


class _SimpleTextTemplate:
    def __init__(self, txt):
        self.txt = txt

    def render(self, context):
        return self.txt


class _PrintfTextTemplate:
    def __init__(self, txt):
        self.txt = txt

    def render(self, context):
        return self.txt % context


class _MakoTextTemplate:
    def __init__(self, txt):
        from mako.template import Template
        self.template = Template(txt, strict_undefined=True)

    def render(self, context):
        return self.template.render(**context)


class _ArgumentPlaceholder:
    """A placeholder for subclasses of :class:`DtypedArgument`. This is needed
    because the concrete dtype of the argument is not known at template
    creation time--it may be a type alias that will only be filled in
    at run time. These types take the place of these proto-arguments until
    all types are known.

    See also :class:`_TemplateRenderer.render_arg`.
    """

    def __init__(self, typename, name, **extra_kwargs):
        self.typename = typename
        self.name = name
        self.extra_kwargs = extra_kwargs


class _VectorArgPlaceholder(_ArgumentPlaceholder):
    target_class = VectorArg


class _ScalarArgPlaceholder(_ArgumentPlaceholder):
    target_class = ScalarArg


class _TemplateRenderer(object):
    def __init__(self, template, type_aliases, var_values, context=None,
            options=[]):
        self.template = template
        self.type_aliases = dict(type_aliases)
        self.var_dict = dict(var_values)

        for name in self.var_dict:
            if name.startswith("macro_"):
                self.var_dict[name] = _process_code_for_macro(
                        self.var_dict[name])

        self.context = context
        self.options = options

    def __call__(self, txt):
        if txt is None:
            return txt

        result = self.template.get_text_template(txt).render(self.var_dict)

        return str(result)

    def get_rendered_kernel(self, txt, kernel_name):
        prg = cl.Program(self.context, self(txt)).build(self.options)

        kernel_name_prefix = self.var_dict.get("kernel_name_prefix")
        if kernel_name_prefix is not None:
            kernel_name = kernel_name_prefix+kernel_name

        return getattr(prg, kernel_name)

    def parse_type(self, typename):
        if isinstance(typename, str):
            try:
                return self.type_aliases[typename]
            except KeyError:
                from pyopencl.compyte.dtypes import NAME_TO_DTYPE
                return NAME_TO_DTYPE[typename]
        else:
            return np.dtype(typename)

    def render_arg(self, arg_placeholder):
        return arg_placeholder.target_class(
                self.parse_type(arg_placeholder.typename),
                arg_placeholder.name,
                **arg_placeholder.extra_kwargs)

    _C_COMMENT_FINDER = re.compile(r"/\*.*?\*/")

    def render_argument_list(self, *arg_lists, **kwargs):
        with_offset = kwargs.pop("with_offset", False)
        if kwargs:
            raise TypeError("unrecognized kwargs: " + ", ".join(kwargs))

        all_args = []

        for arg_list in arg_lists:
            if isinstance(arg_list, str):
                arg_list = str(
                        self.template
                        .get_text_template(arg_list).render(self.var_dict))
                arg_list = self._C_COMMENT_FINDER.sub("", arg_list)
                arg_list = arg_list.replace("\n", " ")

                all_args.extend(arg_list.split(","))
            else:
                all_args.extend(arg_list)

        if with_offset:
            vec_arg_factory = lambda typename, name: \
                    _VectorArgPlaceholder(typename, name, with_offset=True)
        else:
            vec_arg_factory = _VectorArgPlaceholder

        from pyopencl.compyte.dtypes import parse_c_arg_backend
        parsed_args = []
        for arg in all_args:
            if isinstance(arg, str):
                arg = arg.strip()
                if not arg:
                    continue

                ph = parse_c_arg_backend(arg,
                        _ScalarArgPlaceholder, vec_arg_factory,
                        name_to_dtype=lambda x: x)
                parsed_arg = self.render_arg(ph)

            elif isinstance(arg, Argument):
                parsed_arg = arg
            elif isinstance(arg, tuple):
                parsed_arg = ScalarArg(self.parse_type(arg[0]), arg[1])

            parsed_args.append(parsed_arg)

        return parsed_args

    def get_type_decl_preamble(self, device, decl_type_names, arguments=None):
        cdl = _CDeclList(device)

        for typename in decl_type_names:
            cdl.add_dtype(self.parse_type(typename))

        if arguments is not None:
            cdl.visit_arguments(arguments)

        for tv in self.type_aliases.itervalues():
            cdl.add_dtype(tv)

        type_alias_decls = [
                "typedef %s %s;" % (dtype_to_ctype(val), name)
                for name, val in self.type_aliases.iteritems()
                ]

        return cdl.get_declarations() + "\n" + "\n".join(type_alias_decls)


class KernelTemplateBase(object):
    def __init__(self, template_processor=None):
        self.template_processor = template_processor

        self.build_cache = {}
        _first_arg_dependent_caches.append(self.build_cache)

    def get_preamble(self):
        pass

    _TEMPLATE_PROCESSOR_PATTERN = re.compile(r"^//CL(?::([a-zA-Z0-9_]+))?//")

    @memoize_method
    def get_text_template(self, txt):
        proc_match = self._TEMPLATE_PROCESSOR_PATTERN.match(txt)
        tpl_processor = None

        if proc_match is not None:
            tpl_processor = proc_match.group(1)
            # chop off //CL// mark
            txt = txt[len(proc_match.group(0)):]
        if tpl_processor is None:
            tpl_processor = self.template_processor

        if tpl_processor is None or tpl_processor == "none":
            return _SimpleTextTemplate(txt)
        elif tpl_processor == "printf":
            return _PrintfTextTemplate(txt)
        elif tpl_processor == "mako":
            return _MakoTextTemplate(txt)
        else:
            raise RuntimeError(
                    "unknown template processor '%s'" % proc_match.group(1))

    def get_renderer(self, type_aliases, var_values, context=None, options=[]):
        return _TemplateRenderer(self, type_aliases, var_values)

    def build(self, context, *args, **kwargs):
        """Provide caching for an :meth:`build_inner`."""

        cache_key = (context, args, tuple(sorted(kwargs.iteritems())))
        try:
            return self.build_cache[cache_key]
        except KeyError:
            result = self.build_inner(context, *args, **kwargs)
            self.build_cache[cache_key] = result
            return result

# }}}


# {{{ array_module

class _CLFakeArrayModule:
    def __init__(self, queue):
        self.queue = queue

    @property
    def ndarray(self):
        from pyopencl.array import Array
        return Array

    def dot(self, x, y):
        from pyopencl.array import dot
        return dot(x, y, queue=self.queue).get()

    def vdot(self, x, y):
        from pyopencl.array import vdot
        return vdot(x, y, queue=self.queue).get()

    def empty(self, shape, dtype, order="C"):
        from pyopencl.array import empty
        return empty(self.queue, shape, dtype, order=order)


def array_module(a):
    if isinstance(a, np.ndarray):
        return np
    else:
        from pyopencl.array import Array
        if isinstance(a, Array):
            return _CLFakeArrayModule(a.queue)
        else:
            raise TypeError("array type not understood: %s" % type(a))

# }}}

# vim: foldmethod=marker

########NEW FILE########
__FILENAME__ = version
VERSION = (2014, 1)
VERSION_STATUS = ""
VERSION_TEXT = ".".join(str(x) for x in VERSION) + VERSION_STATUS

########NEW FILE########
__FILENAME__ = _cluda
__copyright__ = "Copyright (C) 2009 Andreas Kloeckner"

__license__ = """
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""




CLUDA_PREAMBLE = """
#define local_barrier() barrier(CLK_LOCAL_MEM_FENCE);

#define WITHIN_KERNEL /* empty */
#define KERNEL __kernel
#define GLOBAL_MEM __global
#define LOCAL_MEM __local
#define LOCAL_MEM_ARG __local
#define REQD_WG_SIZE(X,Y,Z) __attribute__((reqd_work_group_size(X, Y, Z)))

#define LID_0 get_local_id(0)
#define LID_1 get_local_id(1)
#define LID_2 get_local_id(2)

#define GID_0 get_group_id(0)
#define GID_1 get_group_id(1)
#define GID_2 get_group_id(2)

#define LDIM_0 get_local_size(0)
#define LDIM_1 get_local_size(1)
#define LDIM_2 get_local_size(2)

#define GDIM_0 get_num_groups(0)
#define GDIM_1 get_num_groups(1)
#define GDIM_2 get_num_groups(2)

% if double_support:
    #pragma OPENCL EXTENSION cl_khr_fp64: enable
% endif
"""





########NEW FILE########
__FILENAME__ = _mymako
try:
    import mako.template
except ImportError:
    raise ImportError(
            "Some of PyOpenCL's facilities require the Mako templating engine.\n"
            "You or a piece of software you have used has tried to call such a\n"
            "part of PyOpenCL, but there was a problem importing Mako.\n\n"
            "You may install mako now by typing one of:\n"
            "- easy_install Mako\n"
            "- pip install Mako\n"
            "- aptitude install python-mako\n"
            "\nor whatever else is appropriate for your system.")

from mako import *

########NEW FILE########
__FILENAME__ = test_algorithm
#! /usr/bin/env python

from __future__ import division, with_statement

__copyright__ = "Copyright (C) 2013 Andreas Kloeckner"

__license__ = """
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

import numpy as np
import numpy.linalg as la
import sys
from pytools import memoize
from test_array import general_clrand

import pytest

import pyopencl as cl
import pyopencl.array as cl_array  # noqa
from pyopencl.tools import (  # noqa
        pytest_generate_tests_for_pyopencl as pytest_generate_tests)
from pyopencl.characterize import has_double_support
from pyopencl.scan import InclusiveScanKernel, ExclusiveScanKernel


# {{{ elementwise

def test_elwise_kernel(ctx_factory):
    context = ctx_factory()
    queue = cl.CommandQueue(context)

    from pyopencl.clrandom import rand as clrand

    a_gpu = clrand(queue, (50,), np.float32)
    b_gpu = clrand(queue, (50,), np.float32)

    from pyopencl.elementwise import ElementwiseKernel
    lin_comb = ElementwiseKernel(context,
            "float a, float *x, float b, float *y, float *z",
            "z[i] = a*x[i] + b*y[i]",
            "linear_combination")

    c_gpu = cl_array.empty_like(a_gpu)
    lin_comb(5, a_gpu, 6, b_gpu, c_gpu)

    assert la.norm((c_gpu - (5 * a_gpu + 6 * b_gpu)).get()) < 1e-5


def test_elwise_kernel_with_options(ctx_factory):
    from pyopencl.clrandom import rand as clrand
    from pyopencl.elementwise import ElementwiseKernel

    context = ctx_factory()
    queue = cl.CommandQueue(context)

    in_gpu = clrand(queue, (50,), np.float32)

    options = ['-D', 'ADD_ONE']
    add_one = ElementwiseKernel(
        context,
        "float* out, const float *in",
        """
        out[i] = in[i]
        #ifdef ADD_ONE
            +1
        #endif
        ;
        """,
        options=options,
        )

    out_gpu = cl_array.empty_like(in_gpu)
    add_one(out_gpu, in_gpu)

    gt = in_gpu.get() + 1
    gv = out_gpu.get()
    assert la.norm(gv - gt) < 1e-5


def test_ranged_elwise_kernel(ctx_factory):
    context = ctx_factory()
    queue = cl.CommandQueue(context)

    from pyopencl.elementwise import ElementwiseKernel
    set_to_seven = ElementwiseKernel(context,
            "float *z", "z[i] = 7", "set_to_seven")

    for i, slc in enumerate([
            slice(5, 20000),
            slice(5, 20000, 17),
            slice(3000, 5, -1),
            slice(1000, -1),
            ]):

        a_gpu = cl_array.zeros(queue, (50000,), dtype=np.float32)
        a_cpu = np.zeros(a_gpu.shape, a_gpu.dtype)

        a_cpu[slc] = 7
        set_to_seven(a_gpu, slice=slc)

        assert (a_cpu == a_gpu.get()).all()


def test_take(ctx_factory):
    context = ctx_factory()
    queue = cl.CommandQueue(context)

    idx = cl_array.arange(queue, 0, 200000, 2, dtype=np.uint32)
    a = cl_array.arange(queue, 0, 600000, 3, dtype=np.float32)
    result = cl_array.take(a, idx)
    assert ((3 * idx).get() == result.get()).all()


def test_arange(ctx_factory):
    context = ctx_factory()
    queue = cl.CommandQueue(context)

    n = 5000
    a = cl_array.arange(queue, n, dtype=np.float32)
    assert (np.arange(n, dtype=np.float32) == a.get()).all()


def test_reverse(ctx_factory):
    context = ctx_factory()
    queue = cl.CommandQueue(context)

    n = 5000
    a = np.arange(n).astype(np.float32)
    a_gpu = cl_array.to_device(queue, a)

    a_gpu = a_gpu.reverse()

    assert (a[::-1] == a_gpu.get()).all()


def test_if_positive(ctx_factory):
    context = ctx_factory()
    queue = cl.CommandQueue(context)

    from pyopencl.clrandom import rand as clrand

    l = 20000
    a_gpu = clrand(queue, (l,), np.float32)
    b_gpu = clrand(queue, (l,), np.float32)
    a = a_gpu.get()
    b = b_gpu.get()

    max_a_b_gpu = cl_array.maximum(a_gpu, b_gpu)
    min_a_b_gpu = cl_array.minimum(a_gpu, b_gpu)

    print(max_a_b_gpu)
    print(np.maximum(a, b))

    assert la.norm(max_a_b_gpu.get() - np.maximum(a, b)) == 0
    assert la.norm(min_a_b_gpu.get() - np.minimum(a, b)) == 0


def test_take_put(ctx_factory):
    context = ctx_factory()
    queue = cl.CommandQueue(context)

    for n in [5, 17, 333]:
        one_field_size = 8
        buf_gpu = cl_array.zeros(queue,
                n * one_field_size, dtype=np.float32)
        dest_indices = cl_array.to_device(queue,
                np.array([0, 1, 2,  3, 32, 33, 34, 35], dtype=np.uint32))
        read_map = cl_array.to_device(queue,
                np.array([7, 6, 5, 4, 3, 2, 1, 0], dtype=np.uint32))

        cl_array.multi_take_put(
                arrays=[buf_gpu for i in range(n)],
                dest_indices=dest_indices,
                src_indices=read_map,
                src_offsets=[i * one_field_size for i in range(n)],
                dest_shape=(96,))


def test_astype(ctx_factory):
    context = ctx_factory()
    queue = cl.CommandQueue(context)

    from pyopencl.clrandom import rand as clrand

    if not has_double_support(context.devices[0]):
        from pytest import skip
        skip("double precision not supported on %s" % context.devices[0])

    a_gpu = clrand(queue, (2000,), dtype=np.float32)

    a = a_gpu.get().astype(np.float64)
    a2 = a_gpu.astype(np.float64).get()

    assert a2.dtype == np.float64
    assert la.norm(a - a2) == 0, (a, a2)

    a_gpu = clrand(queue, (2000,), dtype=np.float64)

    a = a_gpu.get().astype(np.float32)
    a2 = a_gpu.astype(np.float32).get()

    assert a2.dtype == np.float32
    assert la.norm(a - a2) / la.norm(a) < 1e-7

# }}}


# {{{ reduction

def test_sum(ctx_factory):
    from pytest import importorskip
    importorskip("mako")

    context = ctx_factory()
    queue = cl.CommandQueue(context)

    n = 200000
    for dtype in [np.float32, np.complex64]:
        a_gpu = general_clrand(queue, (n,), dtype)

        a = a_gpu.get()

        for slc in [
                slice(None),
                slice(1000, 3000),
                slice(1000, -3000),
                slice(1000, None),
                ]:
            sum_a = np.sum(a[slc])
            sum_a_gpu = cl_array.sum(a_gpu[slc]).get()

            assert abs(sum_a_gpu - sum_a) / abs(sum_a) < 1e-4


def test_minmax(ctx_factory):
    from pytest import importorskip
    importorskip("mako")

    context = ctx_factory()
    queue = cl.CommandQueue(context)

    from pyopencl.clrandom import rand as clrand

    if has_double_support(context.devices[0]):
        dtypes = [np.float64, np.float32, np.int32]
    else:
        dtypes = [np.float32, np.int32]

    for what in ["min", "max"]:
        for dtype in dtypes:
            a_gpu = clrand(queue, (200000,), dtype)
            a = a_gpu.get()

            op_a = getattr(np, what)(a)
            op_a_gpu = getattr(cl_array, what)(a_gpu).get()

            assert op_a_gpu == op_a, (op_a_gpu, op_a, dtype, what)


def test_subset_minmax(ctx_factory):
    from pytest import importorskip
    importorskip("mako")

    context = ctx_factory()
    queue = cl.CommandQueue(context)

    from pyopencl.clrandom import rand as clrand

    l_a = 200000
    gran = 5
    l_m = l_a - l_a // gran + 1

    if has_double_support(context.devices[0]):
        dtypes = [np.float64, np.float32, np.int32]
    else:
        dtypes = [np.float32, np.int32]

    for dtype in dtypes:
        a_gpu = clrand(queue, (l_a,), dtype)
        a = a_gpu.get()

        meaningful_indices_gpu = cl_array.zeros(
                queue, l_m, dtype=np.int32)
        meaningful_indices = meaningful_indices_gpu.get()
        j = 0
        for i in range(len(meaningful_indices)):
            meaningful_indices[i] = j
            j = j + 1
            if j % gran == 0:
                j = j + 1

        meaningful_indices_gpu = cl_array.to_device(
                queue, meaningful_indices)
        b = a[meaningful_indices]

        min_a = np.min(b)
        min_a_gpu = cl_array.subset_min(meaningful_indices_gpu, a_gpu).get()

        assert min_a_gpu == min_a


def test_dot(ctx_factory):
    from pytest import importorskip
    importorskip("mako")

    context = ctx_factory()
    queue = cl.CommandQueue(context)

    dtypes = [np.float32, np.complex64]
    if has_double_support(context.devices[0]):
        dtypes.extend([np.float64, np.complex128])

    for a_dtype in dtypes:
        for b_dtype in dtypes:
            print(a_dtype, b_dtype)
            a_gpu = general_clrand(queue, (200000,), a_dtype)
            a = a_gpu.get()
            b_gpu = general_clrand(queue, (200000,), b_dtype)
            b = b_gpu.get()

            dot_ab = np.dot(a, b)
            dot_ab_gpu = cl_array.dot(a_gpu, b_gpu).get()

            assert abs(dot_ab_gpu - dot_ab) / abs(dot_ab) < 1e-4

            vdot_ab = np.vdot(a, b)
            vdot_ab_gpu = cl_array.vdot(a_gpu, b_gpu).get()

            assert abs(vdot_ab_gpu - vdot_ab) / abs(vdot_ab) < 1e-4


@memoize
def make_mmc_dtype(device):
    dtype = np.dtype([
        ("cur_min", np.int32),
        ("cur_max", np.int32),
        ("pad", np.int32),
        ])

    name = "minmax_collector"
    from pyopencl.tools import get_or_register_dtype, match_dtype_to_c_struct

    dtype, c_decl = match_dtype_to_c_struct(device, name, dtype)
    dtype = get_or_register_dtype(name, dtype)

    return dtype, c_decl


def test_struct_reduce(ctx_factory):
    pytest.importorskip("mako")

    context = ctx_factory()
    queue = cl.CommandQueue(context)

    dev, = context.devices
    if (dev.vendor == "NVIDIA" and dev.platform.vendor == "Apple"
            and dev.driver_version == "8.12.47 310.40.00.05f01"):
        pytest.skip("causes a compiler hang on Apple/Nv GPU")

    mmc_dtype, mmc_c_decl = make_mmc_dtype(context.devices[0])

    preamble = mmc_c_decl + r"""//CL//

    minmax_collector mmc_neutral()
    {
        // FIXME: needs infinity literal in real use, ok here
        minmax_collector result;
        result.cur_min = 1<<30;
        result.cur_max = -(1<<30);
        return result;
    }

    minmax_collector mmc_from_scalar(float x)
    {
        minmax_collector result;
        result.cur_min = x;
        result.cur_max = x;
        return result;
    }

    minmax_collector agg_mmc(minmax_collector a, minmax_collector b)
    {
        minmax_collector result = a;
        if (b.cur_min < result.cur_min)
            result.cur_min = b.cur_min;
        if (b.cur_max > result.cur_max)
            result.cur_max = b.cur_max;
        return result;
    }

    """

    from pyopencl.clrandom import rand as clrand
    a_gpu = clrand(queue, (20000,), dtype=np.int32, a=0, b=10**6)
    a = a_gpu.get()

    from pyopencl.reduction import ReductionKernel
    red = ReductionKernel(context, mmc_dtype,
            neutral="mmc_neutral()",
            reduce_expr="agg_mmc(a, b)", map_expr="mmc_from_scalar(x[i])",
            arguments="__global int *x", preamble=preamble)

    minmax = red(a_gpu).get()
    #print minmax["cur_min"], minmax["cur_max"]
    #print np.min(a), np.max(a)

    assert abs(minmax["cur_min"] - np.min(a)) < 1e-5
    assert abs(minmax["cur_max"] - np.max(a)) < 1e-5

# }}}


# {{{ scan-related

def summarize_error(obtained, desired, orig, thresh=1e-5):
    from pytest import importorskip
    importorskip("mako")

    err = obtained - desired
    ok_count = 0
    bad_count = 0

    bad_limit = 200

    def summarize_counts():
        if ok_count:
            entries.append("<%d ok>" % ok_count)
        if bad_count >= bad_limit:
            entries.append("<%d more bad>" % (bad_count-bad_limit))

    entries = []
    for i, val in enumerate(err):
        if abs(val) > thresh:
            if ok_count:
                summarize_counts()
                ok_count = 0

            bad_count += 1

            if bad_count < bad_limit:
                entries.append("%r (want: %r, got: %r, orig: %r)" % (
                    obtained[i], desired[i], obtained[i], orig[i]))
        else:
            if bad_count:
                summarize_counts()
                bad_count = 0

            ok_count += 1

    summarize_counts()

    return " ".join(entries)

scan_test_counts = [
    10,
    2 ** 8 - 1,
    2 ** 8,
    2 ** 8 + 1,
    2 ** 10 - 5,
    2 ** 10,
    2 ** 10 + 5,
    2 ** 12 - 5,
    2 ** 12,
    2 ** 12 + 5,
    2 ** 20 - 2 ** 18,
    2 ** 20 - 2 ** 18 + 5,
    2 ** 20 + 1,
    2 ** 20,
    2 ** 23 + 3,
    # larger sizes cause out of memory on low-end AMD APUs
    ]


@pytest.mark.parametrize("dtype", [np.int32, np.int64])
@pytest.mark.parametrize("scan_cls", [InclusiveScanKernel, ExclusiveScanKernel])
def test_scan(ctx_factory, dtype, scan_cls):
    from pytest import importorskip
    importorskip("mako")

    context = ctx_factory()
    queue = cl.CommandQueue(context)

    knl = scan_cls(context, dtype, "a+b", "0")

    for n in scan_test_counts:
        host_data = np.random.randint(0, 10, n).astype(dtype)
        dev_data = cl_array.to_device(queue, host_data)

        # /!\ fails on Nv GT2?? for some drivers
        assert (host_data == dev_data.get()).all()

        knl(dev_data)

        desired_result = np.cumsum(host_data, axis=0)
        if scan_cls is ExclusiveScanKernel:
            desired_result -= host_data

        is_ok = (dev_data.get() == desired_result).all()
        if 1 and not is_ok:
            print("something went wrong, summarizing error...")
            print(summarize_error(dev_data.get(), desired_result, host_data))

        print("dtype:%s n:%d %s worked:%s" % (dtype, n, scan_cls, is_ok))
        assert is_ok
        from gc import collect
        collect()


def test_copy_if(ctx_factory):
    from pytest import importorskip
    importorskip("mako")

    context = ctx_factory()
    queue = cl.CommandQueue(context)

    from pyopencl.clrandom import rand as clrand
    for n in scan_test_counts:
        a_dev = clrand(queue, (n,), dtype=np.int32, a=0, b=1000)
        a = a_dev.get()

        from pyopencl.algorithm import copy_if

        crit = a_dev.dtype.type(300)
        selected = a[a > crit]
        selected_dev, count_dev, evt = copy_if(
                a_dev, "ary[i] > myval", [("myval", crit)])

        assert (selected_dev.get()[:count_dev.get()] == selected).all()
        from gc import collect
        collect()


def test_partition(ctx_factory):
    from pytest import importorskip
    importorskip("mako")

    context = ctx_factory()
    queue = cl.CommandQueue(context)

    from pyopencl.clrandom import rand as clrand
    for n in scan_test_counts:
        print("part", n)

        a_dev = clrand(queue, (n,), dtype=np.int32, a=0, b=1000)
        a = a_dev.get()

        crit = a_dev.dtype.type(300)
        true_host = a[a > crit]
        false_host = a[a <= crit]

        from pyopencl.algorithm import partition
        true_dev, false_dev, count_true_dev, evt = partition(
                a_dev, "ary[i] > myval", [("myval", crit)])

        count_true_dev = count_true_dev.get()

        assert (true_dev.get()[:count_true_dev] == true_host).all()
        assert (false_dev.get()[:n-count_true_dev] == false_host).all()


def test_unique(ctx_factory):
    from pytest import importorskip
    importorskip("mako")

    context = ctx_factory()
    queue = cl.CommandQueue(context)

    from pyopencl.clrandom import rand as clrand
    for n in scan_test_counts:
        a_dev = clrand(queue, (n,), dtype=np.int32, a=0, b=1000)
        a = a_dev.get()
        a = np.sort(a)
        a_dev = cl_array.to_device(queue, a)

        a_unique_host = np.unique(a)

        from pyopencl.algorithm import unique
        a_unique_dev, count_unique_dev, evt = unique(a_dev)

        count_unique_dev = count_unique_dev.get()

        assert (a_unique_dev.get()[:count_unique_dev] == a_unique_host).all()
        from gc import collect
        collect()


def test_index_preservation(ctx_factory):
    from pytest import importorskip
    importorskip("mako")

    context = ctx_factory()
    queue = cl.CommandQueue(context)

    from pyopencl.scan import GenericScanKernel, GenericDebugScanKernel
    classes = [GenericScanKernel]

    dev = context.devices[0]
    if dev.type & cl.device_type.CPU:
        classes.append(GenericDebugScanKernel)

    for cls in classes:
        for n in scan_test_counts:
            knl = cls(
                    context, np.int32,
                    arguments="__global int *out",
                    input_expr="i",
                    scan_expr="b", neutral="0",
                    output_statement="""
                        out[i] = item;
                        """)

            out = cl_array.empty(queue, n, dtype=np.int32)
            knl(out)

            assert (out.get() == np.arange(n)).all()
            from gc import collect
            collect()


def test_segmented_scan(ctx_factory):
    from pytest import importorskip
    importorskip("mako")

    context = ctx_factory()
    queue = cl.CommandQueue(context)

    from pyopencl.tools import dtype_to_ctype
    dtype = np.int32
    ctype = dtype_to_ctype(dtype)

    #for is_exclusive in [False, True]:
    for is_exclusive in [True, False]:
        if is_exclusive:
            output_statement = "out[i] = prev_item"
        else:
            output_statement = "out[i] = item"

        from pyopencl.scan import GenericScanKernel
        knl = GenericScanKernel(context, dtype,
                arguments="__global %s *ary, __global char *segflags, "
                    "__global %s *out" % (ctype, ctype),
                input_expr="ary[i]",
                scan_expr="across_seg_boundary ? b : (a+b)", neutral="0",
                is_segment_start_expr="segflags[i]",
                output_statement=output_statement,
                options=[])

        np.set_printoptions(threshold=2000)
        from random import randrange
        from pyopencl.clrandom import rand as clrand
        for n in scan_test_counts:
            a_dev = clrand(queue, (n,), dtype=dtype, a=0, b=10)
            a = a_dev.get()

            if 10 <= n < 20:
                seg_boundaries_values = [
                        [0, 9],
                        [0, 3],
                        [4, 6],
                        ]
            else:
                seg_boundaries_values = []
                for i in range(10):
                    seg_boundary_count = max(2, min(100, randrange(0, int(0.4*n))))
                    seg_boundaries = [
                            randrange(n) for i in range(seg_boundary_count)]
                    if n >= 1029:
                        seg_boundaries.insert(0, 1028)
                    seg_boundaries.sort()
                    seg_boundaries_values.append(seg_boundaries)

            for seg_boundaries in seg_boundaries_values:
                #print "BOUNDARIES", seg_boundaries
                #print a

                seg_boundary_flags = np.zeros(n, dtype=np.uint8)
                seg_boundary_flags[seg_boundaries] = 1
                seg_boundary_flags_dev = cl_array.to_device(
                        queue, seg_boundary_flags)

                seg_boundaries.insert(0, 0)

                result_host = a.copy()
                for i, seg_start in enumerate(seg_boundaries):
                    if i+1 < len(seg_boundaries):
                        seg_end = seg_boundaries[i+1]
                    else:
                        seg_end = None

                    if is_exclusive:
                        result_host[seg_start+1:seg_end] = np.cumsum(
                                a[seg_start:seg_end][:-1])
                        result_host[seg_start] = 0
                    else:
                        result_host[seg_start:seg_end] = np.cumsum(
                                a[seg_start:seg_end])

                #print "REF", result_host

                result_dev = cl_array.empty_like(a_dev)
                knl(a_dev, seg_boundary_flags_dev, result_dev)

                #print "RES", result_dev
                is_correct = (result_dev.get() == result_host).all()
                if not is_correct:
                    diff = result_dev.get() - result_host
                    print("RES-REF", diff)
                    print("ERRWHERE", np.where(diff))
                    print(n, list(seg_boundaries))

                assert is_correct
                from gc import collect
                collect()

            print("%d excl:%s done" % (n, is_exclusive))


def test_sort(ctx_factory):
    from pytest import importorskip
    importorskip("mako")

    context = ctx_factory()
    queue = cl.CommandQueue(context)

    dtype = np.int32

    from pyopencl.algorithm import RadixSort
    sort = RadixSort(context, "int *ary", key_expr="ary[i]",
            sort_arg_names=["ary"])

    from pyopencl.clrandom import RanluxGenerator
    rng = RanluxGenerator(queue, seed=15)

    from time import time

    # intermediate arrays for largest size cause out-of-memory on low-end GPUs
    for n in scan_test_counts[:-1]:
        print(n)

        print("  rng")
        a_dev = rng.uniform(queue, (n,), dtype=dtype, a=0, b=2**16)
        a = a_dev.get()

        dev_start = time()
        print("  device")
        (a_dev_sorted,), evt = sort(a_dev, key_bits=16)
        queue.finish()
        dev_end = time()
        print("  numpy")
        a_sorted = np.sort(a)
        numpy_end = time()

        numpy_elapsed = numpy_end-dev_end
        dev_elapsed = dev_end-dev_start
        print ("  dev: %.2f MKeys/s numpy: %.2f MKeys/s ratio: %.2fx" % (
                1e-6*n/dev_elapsed, 1e-6*n/numpy_elapsed, numpy_elapsed/dev_elapsed))
        assert (a_dev_sorted.get() == a_sorted).all()


def test_list_builder(ctx_factory):
    from pytest import importorskip
    importorskip("mako")

    context = ctx_factory()
    queue = cl.CommandQueue(context)

    from pyopencl.algorithm import ListOfListsBuilder
    builder = ListOfListsBuilder(context, [("mylist", np.int32)], """//CL//
            void generate(LIST_ARG_DECL USER_ARG_DECL index_type i)
            {
                int count = i % 4;
                for (int j = 0; j < count; ++j)
                {
                    APPEND_mylist(count);
                }
            }
            """, arg_decls=[])

    result, evt = builder(queue, 2000)

    inf = result["mylist"]
    assert inf.count == 3000
    assert (inf.lists.get()[-6:] == [1, 2, 2, 3, 3, 3]).all()


def test_key_value_sorter(ctx_factory):
    from pytest import importorskip
    importorskip("mako")

    context = ctx_factory()
    queue = cl.CommandQueue(context)

    n = 10**5
    nkeys = 2000
    from pyopencl.clrandom import rand as clrand
    keys = clrand(queue, n, np.int32, b=nkeys)
    values = clrand(queue, n, np.int32, b=n).astype(np.int64)

    assert np.max(keys.get()) < nkeys

    from pyopencl.algorithm import KeyValueSorter
    kvs = KeyValueSorter(context)
    starts, lists, evt = kvs(queue, keys, values, nkeys, starts_dtype=np.int32)

    starts = starts.get()
    lists = lists.get()

    mydict = dict()
    for k, v in zip(keys.get(), values.get()):
        mydict.setdefault(k, []).append(v)

    for i in range(nkeys):
        start, end = starts[i:i+2]
        assert sorted(mydict[i]) == sorted(lists[start:end])

# }}}


if __name__ == "__main__":
    if len(sys.argv) > 1:
        exec(sys.argv[1])
    else:
        from py.test.cmdline import main
        main([__file__])

# vim: filetype=pyopencl:fdm=marker

########NEW FILE########
__FILENAME__ = test_array
#! /usr/bin/env python
from __future__ import division, with_statement

__copyright__ = "Copyright (C) 2009 Andreas Kloeckner"

__license__ = """
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

import numpy as np
import numpy.linalg as la
import sys

import pyopencl as cl
import pyopencl.array as cl_array
import pyopencl.tools as cl_tools
from pyopencl.tools import (  # noqa
        pytest_generate_tests_for_pyopencl as pytest_generate_tests)
from pyopencl.characterize import has_double_support


# {{{ helpers

TO_REAL = {
        np.dtype(np.complex64): np.float32,
        np.dtype(np.complex128): np.float64
        }


def general_clrand(queue, shape, dtype):
    from pyopencl.clrandom import rand as clrand

    dtype = np.dtype(dtype)
    if dtype.kind == "c":
        real_dtype = dtype.type(0).real.dtype
        return clrand(queue, shape, real_dtype) + 1j*clrand(queue, shape, real_dtype)
    else:
        return clrand(queue, shape, dtype)


def make_random_array(queue, dtype, size):
    from pyopencl.clrandom import rand

    dtype = np.dtype(dtype)
    if dtype.kind == "c":
        real_dtype = TO_REAL[dtype]
        return (rand(queue, shape=(size,), dtype=real_dtype).astype(dtype)
                + rand(queue, shape=(size,), dtype=real_dtype).astype(dtype)
                * dtype.type(1j))
    else:
        return rand(queue, shape=(size,), dtype=dtype)

# }}}


# {{{ dtype-related

def test_basic_complex(ctx_factory):
    context = ctx_factory()
    queue = cl.CommandQueue(context)

    from pyopencl.clrandom import rand

    size = 500

    ary = (rand(queue, shape=(size,), dtype=np.float32).astype(np.complex64)
            + rand(queue, shape=(size,), dtype=np.float32).astype(np.complex64) * 1j)
    c = np.complex64(5+7j)

    host_ary = ary.get()
    assert la.norm((ary*c).get() - c*host_ary) < 1e-5 * la.norm(host_ary)


def test_mix_complex(ctx_factory):
    context = ctx_factory()
    queue = cl.CommandQueue(context)

    size = 10

    dtypes = [
            (np.float32, np.complex64),
            #(np.int32, np.complex64),
            ]

    if has_double_support(context.devices[0]):
        dtypes.extend([
            (np.float32, np.float64),
            (np.float32, np.complex128),
            (np.float64, np.complex64),
            (np.float64, np.complex128),
            ])

    from operator import add, mul, sub, truediv
    for op in [add, sub, mul, truediv, pow]:
        for dtype_a0, dtype_b0 in dtypes:
            for dtype_a, dtype_b in [
                    (dtype_a0, dtype_b0),
                    (dtype_b0, dtype_a0),
                    ]:
                for is_scalar_a, is_scalar_b in [
                        (False, False),
                        (False, True),
                        (True, False),
                        ]:
                    if is_scalar_a:
                        ary_a = make_random_array(queue, dtype_a, 1).get()[0]
                        host_ary_a = ary_a
                    else:
                        ary_a = make_random_array(queue, dtype_a, size)
                        host_ary_a = ary_a.get()

                    if is_scalar_b:
                        ary_b = make_random_array(queue, dtype_b, 1).get()[0]
                        host_ary_b = ary_b
                    else:
                        ary_b = make_random_array(queue, dtype_b, size)
                        host_ary_b = ary_b.get()

                    print(op, dtype_a, dtype_b, is_scalar_a, is_scalar_b)
                    dev_result = op(ary_a, ary_b).get()
                    host_result = op(host_ary_a, host_ary_b)

                    if host_result.dtype != dev_result.dtype:
                        # This appears to be a numpy bug, where we get
                        # served a Python complex that is really a
                        # smaller numpy complex.

                        print("HOST_DTYPE: %s DEV_DTYPE: %s" % (
                                host_result.dtype, dev_result.dtype))

                        dev_result = dev_result.astype(host_result.dtype)

                    err = la.norm(host_result-dev_result)/la.norm(host_result)
                    print(err)
                    correct = err < 1e-5
                    if not correct:
                        print(host_result)
                        print(dev_result)
                        print(host_result - dev_result)

                    assert correct


def test_pow_neg1_vs_inv(ctx_factory):
    ctx = ctx_factory()
    queue = cl.CommandQueue(ctx)

    device = ctx.devices[0]
    if not has_double_support(device):
        from pytest import skip
        skip("double precision not supported on %s" % device)

    a_dev = make_random_array(queue, np.complex128, 20000)

    res1 = (a_dev ** (-1)).get()
    res2 = (1/a_dev).get()
    ref = 1/a_dev.get()

    assert la.norm(res1-ref, np.inf) / la.norm(ref) < 1e-13
    assert la.norm(res2-ref, np.inf) / la.norm(ref) < 1e-13


def test_vector_fill(ctx_factory):
    context = ctx_factory()
    queue = cl.CommandQueue(context)

    a_gpu = cl_array.Array(queue, 100, dtype=cl_array.vec.float4)
    a_gpu.fill(cl_array.vec.make_float4(0.0, 0.0, 1.0, 0.0))
    a = a_gpu.get()
    assert a.dtype is cl_array.vec.float4

    a_gpu = cl_array.zeros(queue, 100, dtype=cl_array.vec.float4)


def test_absrealimag(ctx_factory):
    context = ctx_factory()
    queue = cl.CommandQueue(context)

    def real(x):
        return x.real

    def imag(x):
        return x.imag

    def conj(x):
        return x.conj()

    n = 111
    for func in [abs, real, imag, conj]:
        for dtype in [np.int32, np.float32, np.complex64]:
            print(func, dtype)
            a = -make_random_array(queue, dtype, n)

            host_res = func(a.get())
            dev_res = func(a).get()

            correct = np.allclose(dev_res, host_res)
            if not correct:
                print(dev_res)
                print(host_res)
                print(dev_res-host_res)
            assert correct

# }}}


# {{{ operators

def test_rmul_yields_right_type(ctx_factory):
    context = ctx_factory()
    queue = cl.CommandQueue(context)

    a = np.array([1, 2, 3, 4, 5]).astype(np.float32)
    a_gpu = cl_array.to_device(queue, a)

    two_a = 2*a_gpu
    assert isinstance(two_a, cl_array.Array)

    two_a = np.float32(2)*a_gpu
    assert isinstance(two_a, cl_array.Array)


def test_pow_array(ctx_factory):
    context = ctx_factory()
    queue = cl.CommandQueue(context)

    a = np.array([1, 2, 3, 4, 5]).astype(np.float32)
    a_gpu = cl_array.to_device(queue, a)

    result = pow(a_gpu, a_gpu).get()
    assert (np.abs(a ** a - result) < 1e-3).all()

    result = (a_gpu ** a_gpu).get()
    assert (np.abs(pow(a, a) - result) < 1e-3).all()


def test_pow_number(ctx_factory):
    context = ctx_factory()
    queue = cl.CommandQueue(context)

    a = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]).astype(np.float32)
    a_gpu = cl_array.to_device(queue, a)

    result = pow(a_gpu, 2).get()
    assert (np.abs(a ** 2 - result) < 1e-3).all()


def test_multiply(ctx_factory):
    """Test the muliplication of an array with a scalar. """

    context = ctx_factory()
    queue = cl.CommandQueue(context)

    for sz in [10, 50000]:
        for dtype, scalars in [
                (np.float32, [2]),
                (np.complex64, [2j]),
                ]:
            for scalar in scalars:
                a_gpu = make_random_array(queue, dtype, sz)
                a = a_gpu.get()
                a_mult = (scalar * a_gpu).get()

                assert (a * scalar == a_mult).all()


def test_multiply_array(ctx_factory):
    """Test the multiplication of two arrays."""

    context = ctx_factory()
    queue = cl.CommandQueue(context)

    a = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]).astype(np.float32)

    a_gpu = cl_array.to_device(queue, a)
    b_gpu = cl_array.to_device(queue, a)

    a_squared = (b_gpu * a_gpu).get()

    assert (a * a == a_squared).all()


def test_addition_array(ctx_factory):
    """Test the addition of two arrays."""

    context = ctx_factory()
    queue = cl.CommandQueue(context)

    a = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]).astype(np.float32)
    a_gpu = cl_array.to_device(queue, a)
    a_added = (a_gpu + a_gpu).get()

    assert (a + a == a_added).all()


def test_addition_scalar(ctx_factory):
    """Test the addition of an array and a scalar."""

    context = ctx_factory()
    queue = cl.CommandQueue(context)

    a = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]).astype(np.float32)
    a_gpu = cl_array.to_device(queue, a)
    a_added = (7 + a_gpu).get()

    assert (7 + a == a_added).all()


def test_substract_array(ctx_factory):
    """Test the substraction of two arrays."""
    #test data
    a = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]).astype(np.float32)
    b = np.array([10, 20, 30, 40, 50,
                  60, 70, 80, 90, 100]).astype(np.float32)

    context = ctx_factory()
    queue = cl.CommandQueue(context)

    a_gpu = cl_array.to_device(queue, a)
    b_gpu = cl_array.to_device(queue, b)

    result = (a_gpu - b_gpu).get()
    assert (a - b == result).all()

    result = (b_gpu - a_gpu).get()
    assert (b - a == result).all()


def test_substract_scalar(ctx_factory):
    """Test the substraction of an array and a scalar."""

    context = ctx_factory()
    queue = cl.CommandQueue(context)

    #test data
    a = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]).astype(np.float32)

    #convert a to a gpu object
    a_gpu = cl_array.to_device(queue, a)

    result = (a_gpu - 7).get()
    assert (a - 7 == result).all()

    result = (7 - a_gpu).get()
    assert (7 - a == result).all()


def test_divide_scalar(ctx_factory):
    """Test the division of an array and a scalar."""

    context = ctx_factory()
    queue = cl.CommandQueue(context)

    a = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]).astype(np.float32)
    a_gpu = cl_array.to_device(queue, a)

    result = (a_gpu / 2).get()
    assert (a / 2 == result).all()

    result = (2 / a_gpu).get()
    assert (np.abs(2 / a - result) < 1e-5).all()


def test_divide_array(ctx_factory):
    """Test the division of an array and a scalar. """

    context = ctx_factory()
    queue = cl.CommandQueue(context)

    #test data
    a = np.array([10, 20, 30, 40, 50, 60, 70, 80, 90, 100]).astype(np.float32)
    b = np.array([10, 10, 10, 10, 10, 10, 10, 10, 10, 10]).astype(np.float32)

    a_gpu = cl_array.to_device(queue, a)
    b_gpu = cl_array.to_device(queue, b)

    a_divide = (a_gpu / b_gpu).get()
    assert (np.abs(a / b - a_divide) < 1e-3).all()

    a_divide = (b_gpu / a_gpu).get()
    assert (np.abs(b / a - a_divide) < 1e-3).all()

# }}}


# {{{ RNG

def test_random(ctx_factory):
    context = ctx_factory()
    queue = cl.CommandQueue(context)

    from pyopencl.clrandom import RanluxGenerator

    if has_double_support(context.devices[0]):
        dtypes = [np.float32, np.float64]
    else:
        dtypes = [np.float32]

    gen = RanluxGenerator(queue, 5120)

    for ary_size in [300, 301, 302, 303, 10007]:
        for dtype in dtypes:
            ran = cl_array.zeros(queue, ary_size, dtype)
            gen.fill_uniform(ran)
            assert (0 < ran.get()).all()
            assert (ran.get() < 1).all()

            gen.synchronize(queue)

            ran = cl_array.zeros(queue, ary_size, dtype)
            gen.fill_uniform(ran, a=4, b=7)
            assert (4 < ran.get()).all()
            assert (ran.get() < 7).all()

            ran = gen.normal(queue, (10007,), dtype, mu=4, sigma=3)

    dtypes = [np.int32]
    for dtype in dtypes:
        ran = gen.uniform(queue, (10000007,), dtype, a=200, b=300)
        assert (200 <= ran.get()).all()
        assert (ran.get() < 300).all()
        #from matplotlib import pyplot as pt
        #pt.hist(ran.get())
        #pt.show()

# }}}


# {{{ misc

def test_numpy_integer_shape(ctx_factory):
    try:
        list(np.int32(17))
    except:
        pass
    else:
        from pytest import skip
        skip("numpy implementation does not handle scalar correctly.")
    context = ctx_factory()
    queue = cl.CommandQueue(context)

    cl_array.empty(queue, np.int32(17), np.float32)
    cl_array.empty(queue, (np.int32(17), np.int32(17)), np.float32)


def test_len(ctx_factory):
    context = ctx_factory()
    queue = cl.CommandQueue(context)

    a = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]).astype(np.float32)
    a_cpu = cl_array.to_device(queue, a)
    assert len(a_cpu) == 10


def test_stride_preservation(ctx_factory):
    context = ctx_factory()
    queue = cl.CommandQueue(context)

    A = np.random.rand(3, 3)
    AT = A.T
    print(AT.flags.f_contiguous, AT.flags.c_contiguous)
    AT_GPU = cl_array.to_device(queue, AT)
    print(AT_GPU.flags.f_contiguous, AT_GPU.flags.c_contiguous)
    assert np.allclose(AT_GPU.get(), AT)


def test_nan_arithmetic(ctx_factory):
    context = ctx_factory()
    queue = cl.CommandQueue(context)

    def make_nan_contaminated_vector(size):
        shape = (size,)
        a = np.random.randn(*shape).astype(np.float32)
        from random import randrange
        for i in range(size // 10):
            a[randrange(0, size)] = float('nan')
        return a

    size = 1 << 20

    a = make_nan_contaminated_vector(size)
    a_gpu = cl_array.to_device(queue, a)
    b = make_nan_contaminated_vector(size)
    b_gpu = cl_array.to_device(queue, b)

    ab = a * b
    ab_gpu = (a_gpu * b_gpu).get()

    assert (np.isnan(ab) == np.isnan(ab_gpu)).all()


def test_mem_pool_with_arrays(ctx_factory):
    context = ctx_factory()
    queue = cl.CommandQueue(context)
    mem_pool = cl_tools.MemoryPool(cl_tools.ImmediateAllocator(queue))

    a_dev = cl_array.arange(queue, 2000, dtype=np.float32, allocator=mem_pool)
    b_dev = cl_array.to_device(queue, np.arange(2000), allocator=mem_pool) + 4000

    assert a_dev.allocator is mem_pool
    assert b_dev.allocator is mem_pool


def test_view(ctx_factory):
    context = ctx_factory()
    queue = cl.CommandQueue(context)

    a = np.arange(128).reshape(8, 16).astype(np.float32)
    a_dev = cl_array.to_device(queue, a)

    # same dtype
    view = a_dev.view()
    assert view.shape == a_dev.shape and view.dtype == a_dev.dtype

    # larger dtype
    view = a_dev.view(np.complex64)
    assert view.shape == (8, 8) and view.dtype == np.complex64

    # smaller dtype
    view = a_dev.view(np.int16)
    assert view.shape == (8, 32) and view.dtype == np.int16


def test_diff(ctx_factory):
    context = ctx_factory()
    queue = cl.CommandQueue(context)

    from pyopencl.clrandom import rand as clrand

    l = 20000
    a_dev = clrand(queue, (l,), dtype=np.float32)
    a = a_dev.get()

    err = la.norm(
            (cl.array.diff(a_dev).get() - np.diff(a)))
    assert err < 1e-4

# }}}


# {{{ slices, concatenation

def test_slice(ctx_factory):
    context = ctx_factory()
    queue = cl.CommandQueue(context)

    from pyopencl.clrandom import rand as clrand

    l = 20000
    a_gpu = clrand(queue, (l,), dtype=np.float32)
    b_gpu = clrand(queue, (l,), dtype=np.float32)
    a = a_gpu.get()
    b = b_gpu.get()

    from random import randrange
    for i in range(20):
        start = randrange(l)
        end = randrange(start, l)

        a_gpu_slice = 2*a_gpu[start:end]
        a_slice = 2*a[start:end]

        assert la.norm(a_gpu_slice.get() - a_slice) == 0

    for i in range(20):
        start = randrange(l)
        end = randrange(start, l)

        a_gpu[start:end] = 2*b[start:end]
        a[start:end] = 2*b[start:end]

        assert la.norm(a_gpu.get() - a) == 0

    for i in range(20):
        start = randrange(l)
        end = randrange(start, l)

        a_gpu[start:end] = 2*b_gpu[start:end]
        a[start:end] = 2*b[start:end]

        assert la.norm(a_gpu.get() - a) == 0


def test_concatenate(ctx_factory):
    context = ctx_factory()
    queue = cl.CommandQueue(context)

    from pyopencl.clrandom import rand as clrand

    a_dev = clrand(queue, (5, 15, 20), dtype=np.float32)
    b_dev = clrand(queue, (4, 15, 20), dtype=np.float32)
    c_dev = clrand(queue, (3, 15, 20), dtype=np.float32)
    a = a_dev.get()
    b = b_dev.get()
    c = c_dev.get()

    cat_dev = cl.array.concatenate((a_dev, b_dev, c_dev))
    cat = np.concatenate((a, b, c))

    assert la.norm(cat - cat_dev.get()) == 0

# }}}


# {{{ conditionals, any, all

def test_comparisons(ctx_factory):
    context = ctx_factory()
    queue = cl.CommandQueue(context)

    from pyopencl.clrandom import rand as clrand

    l = 20000
    a_dev = clrand(queue, (l,), dtype=np.float32)
    b_dev = clrand(queue, (l,), dtype=np.float32)

    a = a_dev.get()
    b = b_dev.get()

    import operator as o
    for op in [o.eq, o.ne, o.le, o.lt, o.ge, o.gt]:
        res_dev = op(a_dev, b_dev)
        res = op(a, b)

        assert (res_dev.get() == res).all()

        res_dev = op(a_dev, 0)
        res = op(a, 0)

        assert (res_dev.get() == res).all()

        res_dev = op(0, b_dev)
        res = op(0, b)

        assert (res_dev.get() == res).all()


def test_any_all(ctx_factory):
    context = ctx_factory()
    queue = cl.CommandQueue(context)

    l = 20000
    a_dev = cl_array.zeros(queue, (l,), dtype=np.int8)

    assert not a_dev.all()
    assert not a_dev.any()

    a_dev[15213] = 1

    assert not a_dev.all()
    assert a_dev.any()

    a_dev.fill(1)

    assert a_dev.all()
    assert a_dev.any()

# }}}


def test_map_to_host(ctx_factory):
    context = ctx_factory()
    queue = cl.CommandQueue(context)

    if context.devices[0].type & cl.device_type.GPU:
        mf = cl.mem_flags
        allocator = cl_tools.DeferredAllocator(
                context, mf.READ_WRITE | mf.ALLOC_HOST_PTR)
    else:
        allocator = None

    a_dev = cl_array.zeros(queue, (5, 6, 7,), dtype=np.float32, allocator=allocator)
    a_dev[3, 2, 1] = 10
    a_host = a_dev.map_to_host()
    a_host[1, 2, 3] = 10

    a_host_saved = a_host.copy()
    a_host.base.release(queue)

    a_dev.finish()

    print("DEV[HOST_WRITE]", a_dev.get()[1, 2, 3])
    print("HOST[DEV_WRITE]", a_host_saved[3, 2, 1])

    assert (a_host_saved == a_dev.get()).all()


def test_view_and_strides(ctx_factory):
    context = ctx_factory()
    queue = cl.CommandQueue(context)

    from pyopencl.clrandom import rand as clrand

    X = clrand(queue, (5, 10), dtype=np.float32)
    Y = X[:3, :5]
    y = Y.view()

    assert y.shape == Y.shape
    assert y.strides == Y.strides

    import pytest
    with pytest.raises(AssertionError):
        assert (y.get() == X.get()[:3, :5]).all()


if __name__ == "__main__":
    # make sure that import failures get reported, instead of skipping the
    # tests.
    if len(sys.argv) > 1:
        exec(sys.argv[1])
    else:
        from py.test.cmdline import main
        main([__file__])

# vim: filetype=pyopencl:fdm=marker

########NEW FILE########
__FILENAME__ = test_clmath
from __future__ import division

__copyright__ = "Copyright (C) 2009 Andreas Kloeckner"

__license__ = """
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""
import math
import numpy as np


def have_cl():
    try:
        import pyopencl  # noqa
        return True
    except:
        return False

if have_cl():
    import pyopencl.array as cl_array
    import pyopencl as cl
    import pyopencl.clmath as clmath
    from pyopencl.tools import (  # noqa
            pytest_generate_tests_for_pyopencl
            as pytest_generate_tests)
    from pyopencl.characterize import has_double_support

try:
    import faulthandler
except ImportError:
    pass
else:
    faulthandler.enable()


sizes = [10, 128, 1 << 10, 1 << 11, 1 << 13]


numpy_func_names = {
        "asin": "arcsin",
        "acos": "arccos",
        "atan": "arctan",
        }


def make_unary_function_test(name, limits=(0, 1), threshold=0, use_complex=False):
    (a, b) = limits
    a = float(a)
    b = float(b)

    def test(ctx_factory):
        context = ctx_factory()
        queue = cl.CommandQueue(context)

        gpu_func = getattr(clmath, name)
        cpu_func = getattr(np, numpy_func_names.get(name, name))

        if has_double_support(context.devices[0]):
            if use_complex:
                dtypes = [np.float32, np.float64, np.complex64, np.complex128]
            else:
                dtypes = [np.float32, np.float64]
        else:
            if use_complex:
                dtypes = [np.float32, np.complex64]
            else:
                dtypes = [np.float32]

        for s in sizes:
            for dtype in dtypes:
                dtype = np.dtype(dtype)

                args = cl_array.arange(queue, a, b, (b-a)/s, dtype=dtype)
                if dtype.kind == "c":
                    # args = args + dtype.type(1j) * args
                    args = args + args * dtype.type(1j)

                gpu_results = gpu_func(args).get()
                cpu_results = cpu_func(args.get())

                my_threshold = threshold
                if dtype.kind == "c" and isinstance(use_complex, float):
                    my_threshold = use_complex

                max_err = np.max(np.abs(cpu_results - gpu_results))
                assert (max_err <= my_threshold).all(), \
                        (max_err, name, dtype)

    return test


if have_cl():
    test_ceil = make_unary_function_test("ceil", (-10, 10))
    test_floor = make_unary_function_test("ceil", (-10, 10))
    test_fabs = make_unary_function_test("fabs", (-10, 10))
    test_exp = make_unary_function_test("exp", (-3, 3), 1e-5, use_complex=True)
    test_log = make_unary_function_test("log", (1e-5, 1), 1e-6, use_complex=True)
    test_log10 = make_unary_function_test("log10", (1e-5, 1), 5e-7)
    test_sqrt = make_unary_function_test("sqrt", (1e-5, 1), 3e-7, use_complex=True)

    test_sin = make_unary_function_test("sin", (-10, 10), 2e-7, use_complex=2e-2)
    test_cos = make_unary_function_test("cos", (-10, 10), 2e-7, use_complex=2e-2)
    test_asin = make_unary_function_test("asin", (-0.9, 0.9), 5e-7)
    test_acos = make_unary_function_test("acos", (-0.9, 0.9), 5e-7)
    test_tan = make_unary_function_test("tan",
            (-math.pi/2 + 0.1, math.pi/2 - 0.1), 4e-5, use_complex=True)
    test_atan = make_unary_function_test("atan", (-10, 10), 2e-7)

    test_sinh = make_unary_function_test("sinh", (-3, 3), 2e-6, use_complex=2e-3)
    test_cosh = make_unary_function_test("cosh", (-3, 3), 2e-6, use_complex=2e-3)
    test_tanh = make_unary_function_test("tanh", (-3, 3), 2e-6, use_complex=True)


def test_atan2(ctx_factory):
    context = ctx_factory()
    queue = cl.CommandQueue(context)

    for s in sizes:
        a = (cl_array.arange(queue, s, dtype=np.float32) - np.float32(s / 2)) / 100
        a2 = (s / 2 - 1 - cl_array.arange(queue, s, dtype=np.float32)) / 100
        b = clmath.atan2(a, a2)

        a = a.get()
        a2 = a2.get()
        b = b.get()

        for i in range(s):
            assert abs(math.atan2(a[i], a2[i]) - b[i]) < 1e-6


def test_atan2pi(ctx_factory):
    context = ctx_factory()
    queue = cl.CommandQueue(context)

    for s in sizes:
        a = (cl_array.arange(queue, s, dtype=np.float32) - np.float32(s / 2)) / 100
        a2 = (s / 2 - 1 - cl_array.arange(queue, s, dtype=np.float32)) / 100
        b = clmath.atan2pi(a, a2)

        a = a.get()
        a2 = a2.get()
        b = b.get()

        for i in range(s):
            assert abs(math.atan2(a[i], a2[i]) / math.pi - b[i]) < 1e-6


def test_fmod(ctx_factory):
    context = ctx_factory()
    queue = cl.CommandQueue(context)

    for s in sizes:
        a = cl_array.arange(queue, s, dtype=np.float32)/10
        a2 = cl_array.arange(queue, s, dtype=np.float32)/45.2 + 0.1
        b = clmath.fmod(a, a2)

        a = a.get()
        a2 = a2.get()
        b = b.get()

        for i in range(s):
            assert math.fmod(a[i], a2[i]) == b[i]


def test_ldexp(ctx_factory):
    context = ctx_factory()
    queue = cl.CommandQueue(context)

    for s in sizes:
        a = cl_array.arange(queue, s, dtype=np.float32)
        a2 = cl_array.arange(queue, s, dtype=np.float32)*1e-3
        b = clmath.ldexp(a, a2)

        a = a.get()
        a2 = a2.get()
        b = b.get()

        for i in range(s):
            assert math.ldexp(a[i], int(a2[i])) == b[i]


def test_modf(ctx_factory):
    context = ctx_factory()
    queue = cl.CommandQueue(context)

    for s in sizes:
        a = cl_array.arange(queue, s, dtype=np.float32)/10
        fracpart, intpart = clmath.modf(a)

        a = a.get()
        intpart = intpart.get()
        fracpart = fracpart.get()

        for i in range(s):
            fracpart_true, intpart_true = math.modf(a[i])

            assert intpart_true == intpart[i]
            assert abs(fracpart_true - fracpart[i]) < 1e-4


def test_frexp(ctx_factory):
    context = ctx_factory()
    queue = cl.CommandQueue(context)

    for s in sizes:
        a = cl_array.arange(queue, s, dtype=np.float32)/10
        significands, exponents = clmath.frexp(a)

        a = a.get()
        significands = significands.get()
        exponents = exponents.get()

        for i in range(s):
            sig_true, ex_true = math.frexp(a[i])

            assert sig_true == significands[i]
            assert ex_true == exponents[i]


def test_bessel(ctx_factory):
    try:
        import scipy.special as spec
    except ImportError:
        from pytest import skip
        skip("scipy not present--cannot test Bessel function")

    ctx = ctx_factory()
    queue = cl.CommandQueue(ctx)

    if not has_double_support(ctx.devices[0]):
        from pytest import skip
        skip("no double precision support--cannot test bessel function")

    nterms = 30

    try:
        from pyfmmlib import jfuns2d, hank103_vec
    except ImportError:
        use_pyfmmlib = False
    else:
        use_pyfmmlib = True

    print("PYFMMLIB", use_pyfmmlib)

    if use_pyfmmlib:
        a = np.logspace(-3, 3, 10**6)
    else:
        a = np.logspace(-5, 5, 10**6)

    for which_func, cl_func, scipy_func, is_rel in [
            ("j", clmath.bessel_jn, spec.jn, False),
            ("y", clmath.bessel_yn, spec.yn, True)
            ]:
        if is_rel:
            def get_err(check, ref):
                return np.max(np.abs(check-ref)) / np.max(np.abs(ref))
        else:
            def get_err(check, ref):
                return np.max(np.abs(check-ref))

        if use_pyfmmlib:
            pfymm_result = np.empty((len(a), nterms), dtype=np.complex128)
            if which_func == "j":
                for i, a_i in enumerate(a):
                    if i % 100000 == 0:
                        print("%.1f %%" % (100 * i/len(a)))
                    ier, fjs, _, _ = jfuns2d(nterms, a_i, 1, 0, 10000)
                    pfymm_result[i] = fjs[:nterms]
                assert ier == 0
            elif which_func == "y":
                h0, h1 = hank103_vec(a, ifexpon=1)
                pfymm_result[:, 0] = h0.imag
                pfymm_result[:, 1] = h1.imag

        a_dev = cl_array.to_device(queue, a)

        for n in range(0, nterms):
            cl_bessel = cl_func(n, a_dev).get()
            scipy_bessel = scipy_func(n, a)

            error_scipy = get_err(cl_bessel, scipy_bessel)
            assert error_scipy < 1e-10, error_scipy

            if use_pyfmmlib and (
                    which_func == "j"
                    or
                    (which_func == "y" and n in [0, 1])):
                pyfmm_bessel = pfymm_result[:, n]
                error_pyfmm = get_err(cl_bessel, pyfmm_bessel)
                assert error_pyfmm < 1e-10, error_pyfmm
                error_pyfmm_scipy = get_err(scipy_bessel, pyfmm_bessel)
                print(which_func, n, error_scipy, error_pyfmm, error_pyfmm_scipy)
            else:
                print(which_func, n, error_scipy)

            assert not np.isnan(cl_bessel).any()

            if 0 and n == 15:
                import matplotlib.pyplot as pt
                #pt.plot(scipy_bessel)
                #pt.plot(cl_bessel)

                pt.loglog(a, np.abs(cl_bessel-scipy_bessel), label="vs scipy")
                if use_pyfmmlib:
                    pt.loglog(a, np.abs(cl_bessel-pyfmm_bessel), label="vs pyfmmlib")
                pt.legend()
                pt.show()


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        exec(sys.argv[1])
    else:
        from py.test.cmdline import main
        main([__file__])

########NEW FILE########
__FILENAME__ = test_wrapper
from __future__ import division

__copyright__ = "Copyright (C) 2009 Andreas Kloeckner"

__license__ = """
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

import numpy as np
import numpy.linalg as la

import pyopencl as cl
import pyopencl.array as cl_array
from pyopencl.tools import (  # noqa
        pytest_generate_tests_for_pyopencl as pytest_generate_tests)

# Are CL implementations crashy? You be the judge. :)
try:
    import faulthandler  # noqa
except ImportError:
    pass
else:
    faulthandler.enable()


def test_get_info(ctx_factory):
    ctx = ctx_factory()
    device, = ctx.devices
    platform = device.platform

    failure_count = [0]

    pocl_quirks = [
        (cl.Buffer, cl.mem_info.OFFSET),
        (cl.Program, cl.program_info.BINARIES),
        (cl.Program, cl.program_info.BINARY_SIZES),
    ]
    if ctx._get_cl_version() >= (1, 2) and cl.get_cl_header_version() >= (1, 2):
        pocl_quirks.extend([
            (cl.Program, cl.program_info.KERNEL_NAMES),
            (cl.Program, cl.program_info.NUM_KERNELS),
        ])
    CRASH_QUIRKS = [
            (("NVIDIA Corporation", "NVIDIA CUDA",
                "OpenCL 1.0 CUDA 3.0.1"),
                [
                    (cl.Event, cl.event_info.COMMAND_QUEUE),
                    ]),
            (("The pocl project", "Portable Computing Language",
                "OpenCL 1.2 pocl 0.8-pre"),
                    pocl_quirks),
            (("The pocl project", "Portable Computing Language",
                "OpenCL 1.2 pocl 0.8"),
                pocl_quirks),
            (("The pocl project", "Portable Computing Language",
                "OpenCL 1.2 pocl 0.9-pre"),
                pocl_quirks),
            (("The pocl project", "Portable Computing Language",
                "OpenCL 1.2 pocl 0.9"),
                pocl_quirks),
            (("Apple", "Apple",
                "OpenCL 1.2 (Apr 25 2013 18:32:06)"),
                [
                    (cl.Program, cl.program_info.SOURCE),
                    ]),
            ]
    QUIRKS = []

    plat_quirk_key = (
            platform.vendor,
            platform.name,
            platform.version)

    def find_quirk(quirk_list, cl_obj, info):
        for entry_plat_key, quirks in quirk_list:
            if entry_plat_key == plat_quirk_key:
                for quirk_cls, quirk_info in quirks:
                    if (isinstance(cl_obj, quirk_cls)
                            and quirk_info == info):
                        return True

        return False

    def do_test(cl_obj, info_cls, func=None, try_attr_form=True):
        if func is None:
            def func(info):
                cl_obj.get_info(info)

        for info_name in dir(info_cls):
            if not info_name.startswith("_") and info_name != "to_string":
                print(info_cls, info_name)
                info = getattr(info_cls, info_name)

                if find_quirk(CRASH_QUIRKS, cl_obj, info):
                    print("not executing get_info", type(cl_obj), info_name)
                    print("(known crash quirk for %s)" % platform.name)
                    continue

                try:
                    func(info)
                except:
                    msg = "failed get_info", type(cl_obj), info_name

                    if find_quirk(QUIRKS, cl_obj, info):
                        msg += ("(known quirk for %s)" % platform.name)
                    else:
                        failure_count[0] += 1

                if try_attr_form:
                    try:
                        getattr(cl_obj, info_name.lower())
                    except:
                        print("failed attr-based get_info", type(cl_obj), info_name)

                        if find_quirk(QUIRKS, cl_obj, info):
                            print("(known quirk for %s)" % platform.name)
                        else:
                            failure_count[0] += 1

    do_test(platform, cl.platform_info)
    do_test(device, cl.device_info)
    do_test(ctx, cl.context_info)

    props = 0
    if (device.queue_properties
            & cl.command_queue_properties.PROFILING_ENABLE):
        profiling = True
        props = cl.command_queue_properties.PROFILING_ENABLE
    queue = cl.CommandQueue(ctx,
            properties=props)
    do_test(queue, cl.command_queue_info)

    prg = cl.Program(ctx, """
        __kernel void sum(__global float *a)
        { a[get_global_id(0)] *= 2; }
        """).build()
    do_test(prg, cl.program_info)
    do_test(prg, cl.program_build_info,
            lambda info: prg.get_build_info(device, info),
            try_attr_form=False)

    n = 2000
    a_buf = cl.Buffer(ctx, 0, n*4)

    do_test(a_buf, cl.mem_info)

    kernel = prg.sum
    do_test(kernel, cl.kernel_info)

    evt = kernel(queue, (n,), None, a_buf)
    do_test(evt, cl.event_info)

    if profiling:
        evt.wait()
        do_test(evt, cl.profiling_info,
                lambda info: evt.get_profiling_info(info),
                try_attr_form=False)

    # crashes on intel...
    if device.image_support and platform.vendor not in [
            "Intel(R) Corporation",
            "The pocl project",
            ]:
        smp = cl.Sampler(ctx, False,
                cl.addressing_mode.CLAMP,
                cl.filter_mode.NEAREST)
        do_test(smp, cl.sampler_info)

        img_format = cl.get_supported_image_formats(
                ctx, cl.mem_flags.READ_ONLY, cl.mem_object_type.IMAGE2D)[0]

        img = cl.Image(ctx, cl.mem_flags.READ_ONLY, img_format, (128, 256))
        assert img.shape == (128, 256)

        img.depth
        img.image.depth
        do_test(img, cl.image_info,
                lambda info: img.get_image_info(info))


def test_int_ptr(ctx_factory):
    def do_test(obj):
        new_obj = type(obj).from_int_ptr(obj.int_ptr)
        assert obj == new_obj
        assert type(obj) is type(new_obj)

    ctx = ctx_factory()
    device, = ctx.devices
    platform = device.platform
    do_test(device)
    do_test(platform)
    do_test(ctx)

    queue = cl.CommandQueue(ctx)
    do_test(queue)

    evt = cl.enqueue_marker(queue)
    do_test(evt)

    prg = cl.Program(ctx, """
        __kernel void sum(__global float *a)
        { a[get_global_id(0)] *= 2; }
        """).build()

    do_test(prg)
    do_test(prg.sum)

    n = 2000
    a_buf = cl.Buffer(ctx, 0, n*4)
    do_test(a_buf)

    # crashes on intel...
    if device.image_support and platform.vendor not in [
            "Intel(R) Corporation",
            "The pocl project",
            ]:
        smp = cl.Sampler(ctx, False,
                cl.addressing_mode.CLAMP,
                cl.filter_mode.NEAREST)
        do_test(smp)

        img_format = cl.get_supported_image_formats(
                ctx, cl.mem_flags.READ_ONLY, cl.mem_object_type.IMAGE2D)[0]

        img = cl.Image(ctx, cl.mem_flags.READ_ONLY, img_format, (128, 256))
        do_test(img)


def test_invalid_kernel_names_cause_failures(ctx_factory):
    ctx = ctx_factory()
    device = ctx.devices[0]
    prg = cl.Program(ctx, """
        __kernel void sum(__global float *a)
        { a[get_global_id(0)] *= 2; }
        """).build()

    if ctx.devices[0].platform.vendor == "The pocl project":
        # https://bugs.launchpad.net/pocl/+bug/1184464

        import pytest
        pytest.skip("pocl doesn't like invalid kernel names")

    try:
        prg.sam
        raise RuntimeError("invalid kernel name did not cause error")
    except AttributeError:
        pass
    except RuntimeError:
        if "Intel" in device.platform.vendor:
            from pytest import xfail
            xfail("weird exception from OpenCL implementation "
                    "on invalid kernel name--are you using "
                    "Intel's implementation? (if so, known bug in Intel CL)")
        else:
            raise


def test_image_format_constructor():
    # doesn't need image support to succeed
    iform = cl.ImageFormat(cl.channel_order.RGBA, cl.channel_type.FLOAT)

    assert iform.channel_order == cl.channel_order.RGBA
    assert iform.channel_data_type == cl.channel_type.FLOAT
    assert not iform.__dict__


def test_nonempty_supported_image_formats(ctx_factory):
    context = ctx_factory()

    device = context.devices[0]

    if device.image_support:
        assert len(cl.get_supported_image_formats(
                context, cl.mem_flags.READ_ONLY, cl.mem_object_type.IMAGE2D)) > 0
    else:
        from pytest import skip
        skip("images not supported on %s" % device.name)


def test_that_python_args_fail(ctx_factory):
    context = ctx_factory()

    prg = cl.Program(context, """
        __kernel void mult(__global float *a, float b, int c)
        { a[get_global_id(0)] *= (b+c); }
        """).build()

    a = np.random.rand(50000)
    queue = cl.CommandQueue(context)
    mf = cl.mem_flags
    a_buf = cl.Buffer(context, mf.READ_WRITE | mf.COPY_HOST_PTR, hostbuf=a)

    knl = cl.Kernel(prg, "mult")
    try:
        knl(queue, a.shape, None, a_buf, 2, 3)
        assert False, "PyOpenCL should not accept bare Python types as arguments"
    except cl.LogicError:
        pass

    try:
        prg.mult(queue, a.shape, None, a_buf, float(2), 3)
        assert False, "PyOpenCL should not accept bare Python types as arguments"
    except cl.LogicError:
        pass

    prg.mult(queue, a.shape, None, a_buf, np.float32(2), np.int32(3))

    a_result = np.empty_like(a)
    cl.enqueue_read_buffer(queue, a_buf, a_result).wait()


def test_image_2d(ctx_factory):
    context = ctx_factory()

    device, = context.devices

    if not device.image_support:
        from pytest import skip
        skip("images not supported on %s" % device)

    if "Intel" in device.vendor and "31360.31426" in device.version:
        from pytest import skip
        skip("images crashy on %s" % device)
    if "pocl" in device.platform.vendor and (
            "0.8" in device.platform.version or
            "0.9" in device.platform.version
            ):
        from pytest import skip
        skip("images crashy on %s" % device)

    prg = cl.Program(context, """
        __kernel void copy_image(
          __global float *dest,
          __read_only image2d_t src,
          sampler_t samp,
          int stride0)
        {
          int d0 = get_global_id(0);
          int d1 = get_global_id(1);
          /*
          const sampler_t samp =
            CLK_NORMALIZED_COORDS_FALSE
            | CLK_ADDRESS_CLAMP
            | CLK_FILTER_NEAREST;
            */
          dest[d0*stride0 + d1] = read_imagef(src, samp, (float2)(d1, d0)).x;
        }
        """).build()

    num_channels = 1
    a = np.random.rand(1024, 512, num_channels).astype(np.float32)
    if num_channels == 1:
        a = a[:, :, 0]

    queue = cl.CommandQueue(context)
    try:
        a_img = cl.image_from_array(context, a, num_channels)
    except cl.RuntimeError:
        import sys
        exc = sys.exc_info()[1]
        if exc.code == cl.status_code.IMAGE_FORMAT_NOT_SUPPORTED:
            from pytest import skip
            skip("required image format not supported on %s" % device.name)
        else:
            raise

    a_dest = cl.Buffer(context, cl.mem_flags.READ_WRITE, a.nbytes)

    samp = cl.Sampler(context, False,
            cl.addressing_mode.CLAMP,
            cl.filter_mode.NEAREST)
    prg.copy_image(queue, a.shape, None, a_dest, a_img, samp,
            np.int32(a.strides[0]/a.dtype.itemsize))

    a_result = np.empty_like(a)
    cl.enqueue_copy(queue, a_result, a_dest)

    good = la.norm(a_result - a) == 0
    if not good:
        if queue.device.type & cl.device_type.CPU:
            assert good, ("The image implementation on your CPU CL platform '%s' "
                    "returned bad values. This is bad, but common."
                    % queue.device.platform)
        else:
            assert good


def test_image_3d(ctx_factory):
    #test for image_from_array for 3d image of float2
    context = ctx_factory()

    device, = context.devices

    if not device.image_support:
        from pytest import skip
        skip("images not supported on %s" % device)

    if device.platform.vendor == "Intel(R) Corporation":
        from pytest import skip
        skip("images crashy on %s" % device)

    prg = cl.Program(context, """
        __kernel void copy_image_plane(
          __global float2 *dest,
          __read_only image3d_t src,
          sampler_t samp,
          int stride0,
          int stride1)
        {
          int d0 = get_global_id(0);
          int d1 = get_global_id(1);
          int d2 = get_global_id(2);
          /*
          const sampler_t samp =
            CLK_NORMALIZED_COORDS_FALSE
            | CLK_ADDRESS_CLAMP
            | CLK_FILTER_NEAREST;
            */
          dest[d0*stride0 + d1*stride1 + d2] = read_imagef(
                src, samp, (float4)(d2, d1, d0, 0)).xy;
        }
        """).build()

    num_channels = 2
    shape = (3, 4, 2)
    a = np.random.random(shape + (num_channels,)).astype(np.float32)

    queue = cl.CommandQueue(context)
    try:
        a_img = cl.image_from_array(context, a, num_channels)
    except cl.RuntimeError:
        import sys
        exc = sys.exc_info()[1]
        if exc.code == cl.status_code.IMAGE_FORMAT_NOT_SUPPORTED:
            from pytest import skip
            skip("required image format not supported on %s" % device.name)
        else:
            raise

    a_dest = cl.Buffer(context, cl.mem_flags.READ_WRITE, a.nbytes)

    samp = cl.Sampler(context, False,
            cl.addressing_mode.CLAMP,
            cl.filter_mode.NEAREST)
    prg.copy_image_plane(queue, shape, None, a_dest, a_img, samp,
                         np.int32(a.strides[0]/a.itemsize/num_channels),
                         np.int32(a.strides[1]/a.itemsize/num_channels),
                         )

    a_result = np.empty_like(a)
    cl.enqueue_copy(queue, a_result, a_dest)

    good = la.norm(a_result - a) == 0
    if not good:
        if queue.device.type & cl.device_type.CPU:
            assert good, ("The image implementation on your CPU CL platform '%s' "
                    "returned bad values. This is bad, but common."
                    % queue.device.platform)
        else:
            assert good


def test_copy_buffer(ctx_factory):
    context = ctx_factory()

    queue = cl.CommandQueue(context)
    mf = cl.mem_flags

    a = np.random.rand(50000).astype(np.float32)
    b = np.empty_like(a)

    buf1 = cl.Buffer(context, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=a)
    buf2 = cl.Buffer(context, mf.WRITE_ONLY, b.nbytes)

    cl.enqueue_copy_buffer(queue, buf1, buf2).wait()
    cl.enqueue_read_buffer(queue, buf2, b).wait()

    assert la.norm(a - b) == 0


def test_mempool(ctx_factory):
    from pyopencl.tools import MemoryPool, ImmediateAllocator

    context = ctx_factory()
    queue = cl.CommandQueue(context)

    pool = MemoryPool(ImmediateAllocator(queue))
    alloc_queue = []

    e0 = 12

    for e in range(e0-6, e0-4):
        for i in range(100):
            alloc_queue.append(pool.allocate(1 << e))
            if len(alloc_queue) > 10:
                alloc_queue.pop(0)
    del alloc_queue
    pool.stop_holding()


def test_mempool_2():
    from pyopencl.tools import MemoryPool
    from random import randrange

    for i in range(2000):
        s = randrange(1 << 31) >> randrange(32)
        bin_nr = MemoryPool.bin_number(s)
        asize = MemoryPool.alloc_size(bin_nr)

        assert asize >= s, s
        assert MemoryPool.bin_number(asize) == bin_nr, s
        assert asize < asize*(1+1/8)


def test_vector_args(ctx_factory):
    context = ctx_factory()
    queue = cl.CommandQueue(context)

    prg = cl.Program(context, """
        __kernel void set_vec(float4 x, __global float4 *dest)
        { dest[get_global_id(0)] = x; }
        """).build()

    x = cl_array.vec.make_float4(1, 2, 3, 4)
    dest = np.empty(50000, cl_array.vec.float4)
    mf = cl.mem_flags
    dest_buf = cl.Buffer(context, mf.READ_WRITE | mf.COPY_HOST_PTR, hostbuf=dest)

    prg.set_vec(queue, dest.shape, None, x, dest_buf)

    cl.enqueue_read_buffer(queue, dest_buf, dest).wait()

    assert (dest == x).all()


def test_header_dep_handling(ctx_factory):
    context = ctx_factory()

    from os.path import exists
    assert exists("empty-header.h")  # if this fails, change dir to pyopencl/test

    kernel_src = """
    #include <empty-header.h>
    kernel void zonk(global int *a)
    {
      *a = 5;
    }
    """

    import os

    cl.Program(context, kernel_src).build(["-I", os.getcwd()])
    cl.Program(context, kernel_src).build(["-I", os.getcwd()])


def test_context_dep_memoize(ctx_factory):
    context = ctx_factory()

    from pyopencl.tools import context_dependent_memoize

    counter = [0]

    @context_dependent_memoize
    def do_something(ctx):
        counter[0] += 1

    do_something(context)
    do_something(context)

    assert counter[0] == 1


def test_can_build_binary(ctx_factory):
    ctx = ctx_factory()
    device, = ctx.devices
    platform = device.platform

    if (platform.vendor == "The pocl project" and
        platform.name == "Portable Computing Language"):
        # Segfault on pocl 0.9
        from pytest import skip
        skip("pocl doesn't like getting PROGRAM_BINARIES")

    program = cl.Program(ctx, """
    __kernel void simple(__global float *in, __global float *out)
    {
        out[get_global_id(0)] = in[get_global_id(0)];
    }""")
    program.build()
    binary = program.get_info(cl.program_info.BINARIES)[0]

    foo = cl.Program(ctx, [device], [binary])
    foo.build()


if __name__ == "__main__":
    # make sure that import failures get reported, instead of skipping the tests.
    import pyopencl  # noqa

    import sys
    if len(sys.argv) > 1:
        exec(sys.argv[1])
    else:
        from py.test.cmdline import main
        main([__file__])

########NEW FILE########
