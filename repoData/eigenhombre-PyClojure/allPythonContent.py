__FILENAME__ = core
import operator
from funktown import ImmutableDict, ImmutableVector, ImmutableList


class ComparableExpr(object):
    def __eq__(self, other):
        return (isinstance(other, self.__class__)
                and self.__dict__ == other.__dict__)

    def __ne__(self, other):
        return not (self == other)


class Map(ComparableExpr, ImmutableDict):
    def __init__(self, *args, **kwargs):
        if not kwargs:
            if len(args) == 1:
                ImmutableDict.__init__(self, args[0])
            else:
                ImmutableDict.__init__(self)
        else:
            ImmutableDict.__init__(self, kwargs)

    def __eq__(self, other):
        return ImmutableDict.__eq__(self, other)

    def __repr__(self):
        return 'MAP(%s)' % (str(self))

class Atom(ComparableExpr):
    def __init__(self, name=None, value=None):
        self.__name = name

    def name(self):
        return self.__name

    def __repr__(self):
        return "ATOM(%s)" % (self.__name)


class ComparableIter(ComparableExpr):
    def __eq__(self, other):
        try:
            if len(self) != len(other):
                return False
            for a, b in zip(self, other):
                if a != b:
                    return False
        except:
            return False
        else:
            return True


class List(ComparableIter, ImmutableList):
    def __init__(self, *args):
        ImmutableList.__init__(self, args)

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__.upper(),
                           ','.join([str(el) for el in self]))


class Vector(ComparableIter, ImmutableVector):
    def __init__(self, *args):
        ImmutableVector.__init__(self, args)

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__.upper(),
                           str(self))


class Keyword(ComparableExpr):
    def __init__(self, name):
        self.name = name
    def __repr__(self):
        return ":"+self.name


class Function(ComparableExpr):
    pass


class Scope(dict):
    pass


class GlobalScope(Scope):
    def __init__(self, *args, **kwargs):
        Scope.__init__(self, *args, **kwargs)
        # Get all builtin python functions
        python_callables = [(name, obj) for name, obj\
                                in __builtins__.items() if\
                                callable(obj)]
        self.update(python_callables)

        # These functions take a variable number of arguments
        variadic_operators = {'+': ('add', 0),
                              '-': ('sub', 0),
                              '*': ('mul', 1),
                              '/': ('div', 1)}
        def variadic_generator(fname, default):
            func = getattr(operator, fname)
            ret = (lambda *args: reduce(func, args) if args else default)
            # For string representation; otherwise just get 'lambda':
            ret.__name__ = fname
            return ret

        for name, info in variadic_operators.items():
            self[name] = variadic_generator(*info)

        non_variadic_operators = {
            '!': operator.inv,
            '==': operator.eq,
            }
        self.update((name, func) for name, func in\
                        non_variadic_operators.items())


class UnknownVariable(Exception):
    pass


BUILTIN_FUNCTIONS = {}

def register_builtin(name):
    """
    A decorator that registers built in functions.

    @register_builtin("def")
    def def(args, scopes):
        implementation here
    """
    def inner(func):
        BUILTIN_FUNCTIONS[name] = func
        return func
    return inner

@register_builtin("def")
def def_(args, scopes):
    if len(args) != 2:
        raise TypeError("def takes two arguments")
    atom = args.first()
    rhs = args.second()
    if type(atom) is not Atom:
        raise TypeError("First argument to def must be atom")
    scopes[-1][atom.name()] = evaluate(rhs, scopes)


def find_in_scopechain(scopes, name):
    for scope in reversed(scopes):
        try:
            return scope[name]
        except KeyError:
            pass


def tostring(x):
    if x is None:
        return 'nil'
    elif type(x) in (int, float):
        return str(x)
    elif type(x) is Atom:
        return x.name()
    elif type(x) is Keyword:
        return ":"+x.name
    elif x.__class__.__name__ in ['function', 'builtin_function_or_method']:
        return str(x)
    elif type(x) is List:
        inner = ' '.join([tostring(x) for x in x])
        return '(%s)' % inner
    elif type(x) is Vector:
        inner = ' '.join([tostring(x) for x in x])
        return '[%s]' % inner
    elif type(x) is Map:
        inner = ', '.join(['%s %s' % (k, v) for k,v in x.items()])
        return '{%s}' % inner
    else:
        raise TypeError('%s is unknown!' % x)


def evaluate(x, scopes):
    if type(x) in (int, float):
        return x
    elif type(x) is Atom:
        val = find_in_scopechain(scopes, x.name())
        if not val:
            raise UnknownVariable("Unknown variable: %s" % x.name())
        else:
            return val
    elif type(x) is Keyword:
        return x
    elif type(x) is Vector:
        return apply(Vector, [evaluate(el, scopes) for el in x])
    elif type(x) is Map:
        return Map(dict([(evaluate(k, scopes), evaluate(v, scopes))
                         for k, v in x.items()]))
    elif type(x) is List:
        contents = x
        return eval_list(contents, scopes)
    return x


def eval_list(contents, scopes):
    if contents.empty():
        return List()  # ()
    first = contents.first()
    rest = contents.rest()
    if type(first) is Map:
        if not rest.rest().empty():
            raise TypeError("Map lookup takes one argument")
        return evaluate(first, scopes)[evaluate(rest.first(), scopes)]
    elif type(first) is Atom:
        name = first.name()
        if name in BUILTIN_FUNCTIONS:
            func = BUILTIN_FUNCTIONS[name]
            return func(rest, scopes)
        else:
            val = find_in_scopechain(scopes, name)
            if not val:
                raise UnknownVariable("Function %s is unknown" % name)
            if callable(val):
                args = map((lambda obj: evaluate(obj, scopes)), rest)
                return val(*args)
            else:
                raise TypeError("%s is not callable" % name)

########NEW FILE########
__FILENAME__ = lexer
import ply.lex as lex

class PyClojureLex(object):
    def build(self,**kwargs):
        self.lexer = lex.lex(module=self, **kwargs)
        return self.lexer

    reserved = {'nil': 'NIL'}

    tokens = ['ATOM', 'KEYWORD',
              'NUMBER', 'READMACRO',
              'LBRACKET', 'RBRACKET',
              'LBRACE', 'RBRACE',
              'LPAREN', 'RPAREN'] + list(reserved.values())

    t_LPAREN = r'\('
    t_RPAREN = r'\)'
    t_LBRACKET = r'\['
    t_RBRACKET = r'\]'
    t_LBRACE = r'\{'
    t_RBRACE = r'\}'
    t_ignore = ' ,\t\r'
    t_ignore_COMMENT = r'\;.*'

    def t_KEYWORD(self, t):
        r'\:[a-zA-Z_-]+'
        t.value = t.value[1:]
        return t

    def t_NUMBER(self, t):
        r'[+-]?((\d+(\.\d+)?([eE][+-]?\d+)?)|(\.\d+([eE][+-]?\d+)?))'
        val = t.value
        if '.' in val or 'e' in val.lower():
            t.type = 'FLOAT'
        else:
            t.type = 'INTEGER'
        return t

    def t_ATOM(self, t):
        r'[\*\+\!\-\_a-zA-Z_-]+'
        t.type = self.reserved.get(t.value, 'ATOM')
        return t

    def t_READMACRO(self, t):
        r'[@\'#^`\\.]+'
        # All the possible reader macro chars
        return t

    def t_newline(self, t):
        r'\n+'
        t.lexer.lineno += len(t.value)

    def t_error(self, t):
        print "Illegal character '%s'" % t.value[0]
        t.lexer.skip(1)

########NEW FILE########
__FILENAME__ = parser
import sys
import re
import ply.yacc as yacc
from pyclojure.lexer import PyClojureLex
from pyclojure.core import Atom, Keyword, List, Vector, Map

# BNF grammar for 'lisp'
# sexpr : atom
#       | readmacro sexpr
#       | keyword
#       | float
#       | integer
#       | list
#       | vector
#       | map
#       | nil
# sexprs : sexpr
#        | sexprs sexpr
# list : ( sexprs )
#      | ( )

_quiet = True

class LispLogger(yacc.PlyLogger):
    def debug(self, *args, **kwargs):
        if not _quiet:
            super(type(self), self).debug(*args, **kwargs)

def make_map(args):
    m = {}
    kvlist = [(args[i], args[i+1]) for i in range(0, len(args), 2)]
    for k, v in kvlist:
        m[k] = v
    return Map(m)

def quote_expr(raw):
    return List(Atom('quote'), raw)

def deref_expr(raw):
    return List(Atom('deref'), raw)

def init_type(raw):
    # Due to how python types are initialized, we can just treat them
    # as function calls.
    return raw

# Map from the regex that matches the atom to the function that takes
# in an ast, and modifies it as specified by the macro
READER_MACROS = {
    r'@': deref_expr,
    r'\'': quote_expr,
    r'\.': init_type,
    }

class PyClojureParse(object):
    def build(self):
        return yacc.yacc(module=self, errorlog=LispLogger(sys.stderr))

    tokens = PyClojureLex.tokens
    tokens.remove('NUMBER')
    tokens.extend(('FLOAT', 'INTEGER'))

    def p_sexpr_nil(self, p):
        'sexpr : NIL'
        p[0] = None

    def p_sexpr_atom(self, p):
        'sexpr : ATOM'
        p[0] = Atom(p[1])

    def p_sexpr_readmacro(self, p):
        'sexpr : READMACRO sexpr'
        for regex, func in READER_MACROS.items():
            if re.match(regex, p[1]):
                p[0] = func(p[2])
                return

    def p_keyword(self, p):
        'sexpr : KEYWORD'
        p[0] = Keyword(p[1])

    def p_sexpr_float(self, p):
        'sexpr : FLOAT'
        p[0] = float(p[1])

    def p_sexpr_integer(self, p):
        'sexpr : INTEGER'
        p[0] = int(p[1])

    def p_sexpr_seq(self, p):
        '''
        sexpr : list
              | vector
              | map
        '''
        p[0] = p[1]

    def p_sexprs_sexpr(self, p):
        'sexprs : sexpr'
        p[0] = p[1]

    def p_sexprs_sexprs_sexpr(self, p):
        'sexprs : sexprs sexpr'
        #p[0] = ', '.join((p[1], p[2]))
        if type(p[1]) is list:
            p[0] = p[1]
            p[0].append(p[2])
        else:
            p[0] = [p[1], p[2]]

    def p_list(self, p):
        'list : LPAREN sexprs RPAREN'
        try:
            p[0] = apply(List, p[2])
        except TypeError:
            p[0] = List(p[2])

    def p_empty_list(self, p):
        'list : LPAREN RPAREN'
        p[0] = List()

    def p_vector(self, p):
        'vector : LBRACKET sexprs RBRACKET'
        try:
            p[0] = apply(Vector, p[2])
        except TypeError:
            p[0] = Vector(p[2])

    def p_empty_vector(self, p):
        'vector : LBRACKET RBRACKET'
        p[0] = Vector()

    def p_map(self, p):
        'map : LBRACE sexprs RBRACE'
        p[0] = make_map(p[2])

    def p_empty_map(self, p):
        'map : LBRACE RBRACE'
        p[0] = Map()

    def p_error(self, p):
        if p:
            print(p.lineno, "Syntax error in input at token '%s'" % p.value)
        else:
            print("EOF","Syntax error. No more input.")

########NEW FILE########
__FILENAME__ = repl
#!/usr/bin/env python

import re
import sys

from pyclojure.lexer import PyClojureLex
from pyclojure.parser import PyClojureParse
from pyclojure.core import evaluate, tostring, GlobalScope

try:
    import readline
except ImportError:
    pass
else:
    import os
    histfile = os.path.join(os.path.expanduser("~"), ".pyclojurehist")
    try:
        readline.read_history_file(histfile)
    except IOError:
        # Pass here as there isn't any history file, so one will be
        # written by atexit
        pass
    import atexit
    atexit.register(readline.write_history_file, histfile)

lexer = PyClojureLex().build()
parser = PyClojureParse().build()

def main():
    global_scope = GlobalScope()
    scopechain = [global_scope]
    while True:
        try:
            txt = raw_input("pyclojure> ")
            if re.search('^\s*$', txt):
                continue
            else:
                print(tostring(evaluate(
                            parser.parse(txt, lexer=lexer), scopechain)))
        except EOFError:
            break
        except KeyboardInterrupt:
            print  # Give user a newline after Cntrl-C for readability
            break
        except Exception, e:
            print e
            #  return 1  <-- for now, we assume interactive session at REPL.
            #  later/soon, we should handle source files as well.


if __name__ == "__main__":
    exit_code = main()
    if exit_code:
        sys.exit(exit_code)

########NEW FILE########
__FILENAME__ = test_lisp
from pyclojure.lexer import PyClojureLex  # Need tokens for parser
from pyclojure.parser import PyClojureParse
from pyclojure.core import (Atom, Keyword, Vector, List, Map, Scope, evaluate,
                            tostring, UnknownVariable, GlobalScope)


def test_lexer():
    lexer = PyClojureLex().build()
    lexer.input("""(a
                      (nested) list (of 534 atoms [and :symbols]
                          (and lists)))  ;; with comments
                """)
    assert 20 == len([tok for tok in lexer])
    lexer.input("")
    assert [tok for tok in lexer] == []


def test_parser():
    parse = PyClojureParse().build().parse
    assert parse("an_atom") == Atom('an_atom')
    assert parse("(simple_list)") == List(Atom('simple_list'))
    assert parse('(two elements)') == List(Atom('two'),
                                                  Atom('elements'))
    assert (parse("(three element list)") ==
            List(Atom('three'), Atom('element'), Atom('list')))
    assert parse('666') == 666
    assert (parse('(a (nested (list)))') ==
            List(Atom('a'), List(Atom('nested'), List(Atom('list')))))
    assert parse('()') == List()


def test_reader_macros():
    parse = PyClojureParse().build().parse
    assert parse("@a") == parse("(deref a)")
    assert parse("'a") == parse("(quote a)")
    assert parse("(.float 3)") == parse("(float 3)")
    assert parse("'(1 2 3)") == parse("(quote (1 2 3))")


def test_core():
    Atom()
    Atom('a')
    Atom(name='a', value=6)
    List()
    List(Atom('car'))
    List(Atom('car'), Atom('cadr'), 666)
    List(List())
    List(List('car'))
    Vector()
    Vector(1, 2, 3)
    Keyword("a")
    assert Atom() == Atom()
    assert List() == List()
    assert List(1) == List(1)
    assert List(2) != List(1)
    assert List(1, 2) != List(2, 1)
    assert List(1, 2) == List(1, 2)
    assert List(Atom()) == List(Atom())
    assert List(Atom('a')) == List(Atom('a'))
    assert List(Atom('b')) != List(Atom('a'))
    assert Vector(1, 2) != Vector(2, 1)
    assert Vector(1, 2) == Vector(1, 2)
    assert Vector(1, 2) == List(1, 2)
    assert Keyword("a") == Keyword("a")
    assert Keyword("a") != Keyword("b")
    Map()
    Map(x=1)
    assert Map(x=1).keys() == ['x']
    assert Map(x=1) == Map(x=1)
    assert Map(x=1) != Map(x=2)
    assert Map(x=1) != Map(x=1, a=3)
    assert Map(x=1)["x"] == 1


def test_python_compat():
    assert List(1, 2, 3) == [1, 2, 3]
    assert Map() == {}
    assert Map(a=3) == {'a': 3}
    assert Map(a=3) != ['a', 3]
    assert Vector(*range(10)) == range(10)
    assert map(abs, List(-1, -2, -3)) == List(1, 2, 3)
    def infinite_gen():
        x = 1
        while 1:
            x += 1
            yield x
    assert List(1, 2, 3) != infinite_gen()
    assert List(1, 2) != List(1, 2, 3)


def evalparser():
    parse = PyClojureParse().build().parse
    scopechain = [GlobalScope()]
    def evalparse(x):
        return evaluate(parse(x), scopechain)
    return evalparse

def test_eval():
    evalparse = evalparser()
    assert evalparse("666") == 666
    assert evalparse("6.66") == 6.66
    assert evalparse("nil") == None
    assert evalparse("()") == List()
    assert evalparse("[]") == Vector()
    assert evalparse("[1 2 3]") == Vector(1, 2, 3)
    assert evalparse("{}") == Map()
    m = Map({1:2})
    assert evalparse("{1 2}") == m
    m = Map({1:2, 3:4})
    assert evalparse("{1 2, 3 4}") == m

    try:
        evalparse("a")
        assert False, "UnknownVariable exception not raised!"
    except UnknownVariable:
        pass
    try:
        evalparse("(x)")
        assert False, "UnknownVariable exception not raised!"
    except UnknownVariable:
        pass
    evalparse("(def a 777)")
    assert evalparse("a") == 777
    assert evalparse("a") == 777
    evalparse("(def a 666)")
    assert evalparse("a") == 666
    assert evalparse("[1 a]") == Vector(1, 666)
    assert evalparse(":a") == Keyword("a")
    assert evalparse("(+ 2 2)") == 4
    assert evalparse("(+)") == 0
    assert evalparse("(+ 1 2 3 4)") == 10
    assert evalparse("(*)") == 1
    assert evalparse("(* 1 2 3 4 5)") == 120
    assert evalparse("(+ 2 (+ 2 3))") == 7
    assert evalparse("{}") == Map()
    assert evalparse("{1 2}") == Map({1: 2})
    assert evalparse("({1 2} 1)") == 2
    assert evalparse("({a 1} 666)") == 1
    assert evalparse("({666 1} a)") == 1
    assert evalparse("({a 2 3 a} a)") == 2
    assert evalparse("({a 2 3 a} 3)") == 666


def test_function_calling():
    '''
    Test builtin function calling
    '''
    evalparse = evalparser()
    assert evalparse("(abs (- 0 100))") == 100
    assert evalparse("(round 3.3)") == 3.0
    evalparse("(def a 3)")
    assert evalparse("a") == 3
    try:
        evalparse("(def a 3 2)")
        assert False, "TypeError expected"
    except TypeError:
        pass
    try:
        evalparse("(def 3 a)")
        assert False, "TypeError expected"
    except TypeError:
        pass

def test_float_parsing():
    '''
    Test builtin python function calling
    '''
    evalparse = evalparser()
    assert evalparse("1") == 1
    assert evalparse("1.2") == 1.2
    assert evalparse(".12") == .12
    assert evalparse("0.12") == .12
    assert evalparse("0.12E2") == 12
    assert evalparse("-0.12E+02") == -12
    assert evalparse("-0.12E-2") == -.0012
    assert evalparse("(.float 3)") == 3.0
    assert 'function abs' in str(evalparse("abs"))
    assert 'function add' in str(evalparse("+"))


def test_to_string():
    parse = PyClojureParse().build().parse
    assert tostring(parse("nil")) =="nil"
    assert tostring(parse("666")) =="666"
    assert tostring(parse("6.66")) == "6.66"
    assert tostring(parse("666e-2")) == "6.66"
    assert tostring(parse("-666")) =="-666"
    assert tostring(parse("-6.66")) == "-6.66"
    assert tostring(parse("-666e-2")) == "-6.66"
    assert tostring(parse("()")) == "()"
    assert tostring(parse("(a)")) == "(a)"
    assert tostring(parse("(a b)")) == "(a b)"
    assert tostring(parse("(a (b c))")) == "(a (b c))"
    assert tostring(parse("[]")) == "[]"
    assert tostring(parse(":a")) == ":a"
    assert tostring(parse("{}")) == "{}"
    assert tostring(parse("{1 2}")) == "{1 2}"
    assert tostring(parse("{1 2 3 4}")) == "{1 2, 3 4}"


def test_scope():
    '''
    Fixme - eventually add tests for nested scope, lexical scope, etc.
    '''
    s = Scope()
    s["a"] = 666

########NEW FILE########
