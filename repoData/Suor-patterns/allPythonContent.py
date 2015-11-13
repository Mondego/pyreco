__FILENAME__ = cross
import sys


PY2 = sys.version_info.major == 2
PY3 = sys.version_info.major == 3

# Getting back our simple and useful list-returing map in python 3
if map(int, []) == []:
    lmap = map
else:
    lmap = lambda f, seq: list(map(f, seq))

########NEW FILE########
__FILENAME__ = helpers
import ast
from ast import *

from .cross import *


__all__ = ['V', 'N', 'A',
           'make_call', 'make_arguments', 'make_raise',
           'make_assign', 'make_op', 'make_eq', 'make_subscript']


def V(value):
    if isinstance(value, int):
        return Num(n=value)
    else:
        raise TypeError("Don't know how to make AST value from %s" % repr(value))

def N(id):
  return Name(ctx=Load(), id=id)

if PY3:
    def A(id):
        return arg(arg=id, annotation=None)
else:
    def A(id):
        return Name(ctx=Param(), id=id)


def wrap_carefully(value):
    if isinstance(value, ast.expr):
        return value
    else:
        return V(value)


def make_call(func_name, *args):
    return Call(
        func=N(func_name), args=lmap(wrap_carefully, args),
        keywords=[], kwargs=None, starargs=None
    )

def make_arguments(args):
    # Some fields are only needed for python 3,
    # but we pass them always as they are safely ignored by python 2
    return arguments(
        args=args,
        defaults=[], kw_defaults=[],
        kwarg=None, kwargannotation=None, kwonlyargs=[],
        vararg=None, varargannotation=None
    )

if PY3:
    def make_raise(expr):
        return Raise(exc=expr, cause=None)
else:
    def make_raise(expr):
        return Raise(type=expr, inst=None, tback=None)


def make_assign(left, right):
    return Assign(
        targets = [Name(ctx=Store(), id=left)],
        value   = wrap_carefully(right)
    )

def make_op(op_class, left, right):
    return Compare(
        ops         = [op_class()],
        left        = wrap_carefully(left),
        comparators = [wrap_carefully(right)],
    )

def make_eq(left, right):
    return make_op(Eq, left, right)

def make_subscript(expr, index):
    return Subscript(
        value = expr,
        slice = Index(value=wrap_carefully(index)),
        ctx   = Load(),
    )

########NEW FILE########
__FILENAME__ = transform
from ast import *
import meta
from meta.asttools import print_ast
from itertools import chain

from .helpers import *
from .cross import *


def transform_function(func_tree):
    assert all(isinstance(t, If) for t in func_tree.body), \
        'Patterns function should only have if statements'

    # Adjust arglist and decorators
    func_tree.args.args.append(A('value'))
    func_tree.decorator_list = []

    # Transform tests to pattern matching
    for test in func_tree.body:
        cond = test.test

        if isinstance(cond, (Num, Str, List, Tuple, Dict)) and not has_vars(cond):
            test.test = make_eq(N('value'), cond)

        elif isinstance(cond, (Num, Str, Name, Compare, List, Tuple, Dict, BinOp)):
            tests, assigns = destruct_to_tests_and_assigns(N('value'), cond)
            test.test = BoolOp(op=And(), values=tests) if len(tests) > 1 else \
                                              tests[0] if tests else V(1)
            test.body = assigns + test.body

        else:
            raise TypeError("Don't know how to match %s" % meta.dump_python_source(cond).strip())

    func_tree.body = lmap(wrap_tail_expr, func_tree.body)
    func_tree.body.append(make_raise(N('Mismatch')))

    # Set raise Mismatch lineno just after function end
    func_tree.body[-1].lineno = last_lineno(func_tree) + 1

    # print_ast(func_tree)
    # print(meta.dump_python_source(func_tree))


def destruct_to_tests_and_assigns(topic, pattern):
    if isinstance(pattern, (Num, Str)):
        return [make_eq(topic, pattern)], []
    elif isinstance(pattern, Name):
        return [], [make_assign(pattern.id, topic)]
    elif isinstance(pattern, Compare) and len(pattern.ops) == 1 and isinstance(pattern.ops[0], Is):
        return [make_call('isinstance', topic, pattern.comparators[0])], \
               [make_assign(pattern.left.id, topic)]
    elif isinstance(pattern, (List, Tuple, Dict)):
        elts = getattr(pattern, 'elts', []) or getattr(pattern, 'values', [])
        coll_tests = [
            make_call('isinstance', topic, N(pattern.__class__.__name__.lower())),
            make_eq(make_call('len', topic), len(elts))
        ]
        tests, assigns = subscript_tests_and_assigns(topic, pattern)
        return coll_tests + tests, assigns
    elif isinstance(pattern, BinOp) and isinstance(pattern.op, Add) \
         and isinstance(pattern.left, (List, Tuple)) and isinstance(pattern.right, Name):
        coll_tests = [
            make_call('isinstance', topic, N(pattern.left.__class__.__name__.lower())),
            make_op(GtE, make_call('len', topic), len(pattern.left.elts)),
        ]
        coll_assigns = [
            make_assign(pattern.right.id,
                        Subscript(ctx=Load(),
                                  value=topic,
                                  slice=Slice(lower=V(len(pattern.left.elts)), upper=None, step=None)))
        ]
        tests, assigns = subscript_tests_and_assigns(topic, pattern.left)
        return coll_tests + tests, assigns + coll_assigns
    else:
        raise TypeError("Don't know how to match %s" % meta.dump_python_source(pattern).strip())


def subscript_tests_and_assigns(topic, pattern):
    tests = []
    assigns = []
    items = enumerate(pattern.elts) if hasattr(pattern, 'elts') else zip(pattern.keys, pattern.values)
    for key, elt in items:
        t, a = destruct_to_tests_and_assigns(make_subscript(topic, key), elt)
        tests.extend(t)
        assigns.extend(a)
    return tests, assigns


def wrap_tail_expr(if_expr):
    """
    Wrap last expression in if body with Return node
    """
    if isinstance(if_expr.body[-1], Expr):
        if_expr.body[-1] = Return(value=if_expr.body[-1].value)
    return if_expr


def has_vars(expr):
    if isinstance(expr, (Tuple, List)):
        return any(has_vars(el) for el in expr.elts)
    elif isinstance(expr, Dict):
        return any(has_vars(e) for e in chain(expr.values, expr.keys))
    elif isinstance(expr, (Name, Compare)):
        return True
    elif isinstance(expr, (Num, Str)):
        return False
    else:
        raise TypeError("Don't know how to handle %s" % expr)


def last_lineno(node):
    lineno = getattr(node, 'lineno', None)
    if hasattr(node, 'body'):
        linenos = (last_lineno(n) for n in reversed(node.body))
        return next((n for n in linenos if n is not None), lineno)
    else:
        return lineno

########NEW FILE########
__FILENAME__ = test_examples
import pytest
from patterns import patterns, Mismatch


def test_factorial():
    @patterns
    def factorial():
        if 0: 1
        if n is int: n * factorial(n-1)
        if []: []
        if [x] + xs: [factorial(x)] + factorial(xs)
        if {'n': n, 'f': f}: f(factorial(n))

    assert factorial(0) == 1
    assert factorial(5) == 120
    assert factorial([3,4,2]) == [6, 24, 2]
    assert factorial({'n': [5, 1], 'f': sum}) == 121


def test_depth():
    def make_node(v, l=None, r=None):
        return ('Tree', v, l, r)

    @patterns
    def depth():
        if ('Tree', _, l, r): 1 + max(depth(l), depth(r))
        if None: 0

    n1 = make_node(1)
    n2 = make_node(2, n1)
    n3 = make_node(3, n1, n1)
    n4 = make_node(4, n2, n3)

    assert depth(None) == 0
    assert depth(n1) == 1
    assert depth(n2) == 2
    assert depth(n3) == 2
    assert depth(n4) == 3


def test_chatter():
    botname = "Chatty"

    @patterns
    def answer():
        if ['hello']: "Hello, my name is %s" % botname
        if ['hello', 'my', 'name', 'is', name]: "Hello, %s!" % name.capitalize()
        if ['how', 'much', 'is'] + expr: "It is %d" % eval(' '.join(expr))
        if ['bye']: "Good bye!"

    @patterns
    def chatterbot():
        if l is list: answer([s.lower() for s in l])
        if s is str: chatterbot(s.split())

    assert chatterbot("hello") == "Hello, my name is Chatty"
    assert chatterbot("how much is 5 * 10") == "It is 50"
    assert chatterbot("how much is 5 - 10") == "It is -5"
    assert chatterbot("how much is 5 + 10 - 1") == "It is 14"
    assert chatterbot("how much is 5 + 10 - 1") == "It is 14"
    assert chatterbot("hello my name is alice") == "Hello, Alice!"

########NEW FILE########
__FILENAME__ = test_patterns
import pytest
from patterns import patterns, Mismatch


def test_const():
    @patterns
    def const():
        if 1: 'int'
        if 'hi': 'str'

    assert const(1) == 'int'
    assert const('hi') == 'str'
    with pytest.raises(Mismatch): const(2)
    with pytest.raises(Mismatch): const({})


def test_container_const():
    class L(list): pass

    @patterns
    def const():
        if [1, 2]: 'list'
        if (1, 2): 'tuple'

    assert const([1, 2]) == 'list'
    assert const((1, 2)) == 'tuple'
    assert const(L([1, 2])) == 'list'


def test_complex_body():
    @patterns
    def const():
        if 1:
            x = 'int'
            x
        if 'hi':
            return 'str'

    assert const(1) == 'int'
    assert const('hi') == 'str'


def test_global_ref():
    @patterns
    def _global():
        if '': test_global_ref

    assert _global('') is test_global_ref


def test_local_ref():
    local_var = object()

    @patterns
    def _local():
        if '': local_var

    assert _local('') is local_var
    local_var = object()
    assert _local('') is local_var


def test_capture():
    @patterns
    def capture():
        if y: y - 1

    assert capture(41) == 40


def test_typing():
    @patterns
    def typing():
        if n is int: n + 1
        if s is (str, float): 'str_or_float'

    assert typing(42) == 43
    assert typing('42') == 'str_or_float'
    assert typing(3.14) == 'str_or_float'


def test_destruct_tuple():
    @patterns
    def destruct():
        if (x, 0): 0
        if (x, 1): x
        if (x, y): x + destruct((x, y - 1))
        if (_,): raise ValueError('Give me pair')

    assert destruct((2, 0)) == 0
    assert destruct((2, 1)) == 2
    assert destruct((2, 2)) == 4
    assert destruct((5, 5)) == 25
    with pytest.raises(ValueError): destruct((2,))
    with pytest.raises(Mismatch): destruct(1)


def test_destruct_dict():
    @patterns
    def destruct():
        if {}: 0
        if {'a': a}: raise TypeError
        if {'a': a, 'b': b}: a * b
        # TODO: short form like this:
        #           if {a, b}: a * b
        #       how handle sets?

    assert destruct({}) == 0
    assert destruct({'a': 6, 'b': 7}) == 42
    with pytest.raises(Mismatch): destruct({'a': 6, 'b': 7, 'c': None})


def test_nested_tuples():
    @patterns
    def destruct():
        if ((1, 2), 3, x): x
        if ((1, x), 3, 4): x
        if ((1, x), 3, y): x + y

    assert destruct(((1, 2), 3, 'world')) == 'world'
    assert destruct(((1, 'hi'), 3, 4)) == 'hi'
    assert destruct(((1, 'hi'), 3, 'world')) == 'hiworld'
    assert destruct(((1, 2), 3, 4)) == 4


def test_swallow():
    @patterns
    def swallow():
        if (1, x): 1 + '1'

    with pytest.raises(TypeError): swallow((1, 2))


def test_nested_types():
    @patterns
    def destruct():
        if (x is int, y is int): x * y
        if (s is str, n is int): len(s) * n
        if (s is str, t is str): s + t

    assert destruct((6, 7)) == 42
    assert destruct(('hi', 3)) == 6
    assert destruct(('hi', 'world')) == 'hiworld'


def test_tail_destruct():
    @patterns
    def tail_destruct():
        if []: 0
        if [x] + xs: tail_destruct(xs) + 1
        if (): ''
        if (x is int,) + xs: 't' + tail_destruct(xs)
        if (s is str,) + xs: s + tail_destruct(xs)

    assert tail_destruct([]) == 0
    assert tail_destruct([7]) == 1
    assert tail_destruct([1,2,3]) == 3

    assert tail_destruct(()) == ''
    assert tail_destruct((1,)) == 't'
    assert tail_destruct((1,2,3)) == 'ttt'
    assert tail_destruct((1,'X',2)) == 'tXt'


def test_nested_capture():
    @patterns
    def answer():
        # captute names should be diffrent here to get NameError
        # if some structure is not handled properly
        if [l]: 'list: %s' % l
        if (t,): 'tuple: %s' % t
        if {'key': d}: 'dict: %s' % d

    assert answer(['alice']) == 'list: alice'
    assert answer(('alice',)) == 'tuple: alice'
    assert answer({'key': 'alice'}) == 'dict: alice'


def test_wrong_pattern():
    def wrong():
        @patterns
        def _wrong():
            if map(): 1

    with pytest.raises(TypeError): wrong()


def test_exception():
    import sys, inspect
    class E(Exception): pass

    BASE_LINE = inspect.currentframe().f_lineno

    @patterns
    def exception():
        if 1: raise E
        if 2:
            raise E

    for value, exc, line in [(1, E, BASE_LINE+4), (2, E, BASE_LINE+6), (3, Mismatch, BASE_LINE+7)]:
        try:
            exception(value)
        except exc:
            _, _, exc_traceback = sys.exc_info()
            assert line == exc_traceback.tb_next.tb_lineno

########NEW FILE########
