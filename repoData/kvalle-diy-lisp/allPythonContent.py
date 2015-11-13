__FILENAME__ = asserts
# -*- coding: utf-8 -*-

from .types import LispError
from .parser import unparse


def assert_exp_length(ast, length):
    if len(ast) > length:
        msg = "Malformed %s, too many arguments: %s" % (ast[0], unparse(ast))
        raise LispError(msg)
    elif len(ast) < length:
        msg = "Malformed %s, too few arguments: %s" % (ast[0], unparse(ast))
        raise LispError(msg)


def assert_valid_definition(d):
    if len(d) != 2:
        msg = "Wrong number of arguments for variable definition: %s" % d
        raise LispError(msg)
    elif not isinstance(d[0], str):
        msg = "Attempted to define non-symbol as variable: %s" % d
        raise LispError(msg)


def assert_boolean(p, exp=None):
    if not is_boolean(p):
        msg = "Boolean required, got '%s'. " % unparse(p)
        if exp is not None:
            msg += "Offending expression: %s" % unparse(exp)
        raise LispTypeError(msg)

########NEW FILE########
__FILENAME__ = ast
# -*- coding: utf-8 -*-

from .types import Closure

"""
This module contains a few simple helper functions for
checking the type of ASTs.
"""


def is_symbol(x):
    return isinstance(x, str)


def is_list(x):
    return isinstance(x, list)


def is_boolean(x):
    return isinstance(x, bool)


def is_integer(x):
    return isinstance(x, int)


def is_closure(x):
    return isinstance(x, Closure)


def is_atom(x):
    return (is_symbol(x) or
    	is_integer(x) or
    	is_boolean(x) or
    	is_closure(x))

########NEW FILE########
__FILENAME__ = evaluator
# -*- coding: utf-8 -*-

from .types import Environment, LispError, Closure
from .ast import is_boolean, is_atom, is_symbol, is_list, is_closure, is_integer
from .asserts import assert_exp_length, assert_valid_definition, assert_boolean
from .parser import unparse

"""
This is the Evaluator module. The `evaluate` function below is the heart
of your language, and the focus for most of parts 2 through 6.

A score of useful functions is provided for you, as per the above imports, 
making your work a bit easier. (We're supposed to get through this thing 
in a day, after all.)
"""


def evaluate(ast, env):
    """Evaluate an Abstract Syntax Tree in the specified environment."""
    raise NotImplementedError("DIY")

########NEW FILE########
__FILENAME__ = interpreter
# -*- coding: utf-8 -*-

from os.path import dirname, join

from .evaluator import evaluate
from .parser import parse, unparse, parse_multiple
from .types import Environment


def interpret(source, env=None):
    """
    Interpret a lisp program statement

    Accepts a program statement as a string, interprets it, and then
    returns the resulting lisp expression as string.
    """
    if env is None:
        env = Environment()

    return unparse(evaluate(parse(source), env))


def interpret_file(filename, env=None):
    """
    Interpret a lisp file

    Accepts the name of a lisp file containing a series of statements. 
    Returns the value of the last expression of the file.
    """
    if env is None:
        env = Environment()

    with open(filename, 'r') as sourcefile:
        source = "".join(sourcefile.readlines())

    asts = parse_multiple(source)
    results = [evaluate(ast, env) for ast in asts]
    return unparse(results[-1])

########NEW FILE########
__FILENAME__ = parser
# -*- coding: utf-8 -*-

import re
from .ast import is_boolean, is_list
from .types import LispError

"""
This is the parser module, with the `parse` function which you'll implement as part 1 of
the workshop. Its job is to convert strings into data structures that the evaluator can 
understand. 
"""


def parse(source):
    """Parse string representation of one *single* expression
    into the corresponding Abstract Syntax Tree."""

    raise NotImplementedError("DIY")

##
## Below are a few useful utility functions. These should come in handy when 
## implementing `parse`. We don't want to spend the day implementing parenthesis 
## counting, after all.
## 


def remove_comments(source):
    """Remove from a string anything in between a ; and a linebreak"""
    return re.sub(r";.*\n", "\n", source)


def find_matching_paren(source, start=0):
    """Given a string and the index of an opening parenthesis, determines 
    the index of the matching closing paren."""

    assert source[start] == '('
    pos = start
    open_brackets = 1
    while open_brackets > 0:
        pos += 1
        if len(source) == pos:
            raise LispError("Incomplete expression: %s" % source[start:])
        if source[pos] == '(':
            open_brackets += 1
        if source[pos] == ')':
            open_brackets -= 1
    return pos


def split_exps(source):
    """Splits a source string into subexpressions 
    that can be parsed individually.

    Example: 

        > split_exps("foo bar (baz 123)")
        ["foo", "bar", "(baz 123)"]
    """

    rest = source.strip()
    exps = []
    while rest:
        exp, rest = first_expression(rest)
        exps.append(exp)
    return exps


def first_expression(source):
    """Split string into (exp, rest) where exp is the 
    first expression in the string and rest is the 
    rest of the string after this expression."""
    
    source = source.strip()
    if source[0] == "'":
        exp, rest = first_expression(source[1:])
        return source[0] + exp, rest
    elif source[0] == "(":
        last = find_matching_paren(source)
        return source[:last + 1], source[last + 1:]
    else:
        match = re.match(r"^[^\s)']+", source)
        end = match.end()
        atom = source[:end]
        return atom, source[end:]

##
## The functions below, `parse_multiple` and `unparse` are implemented in order for
## the REPL to work. Don't worry about them when implementing the language.
##


def parse_multiple(source):
    """Creates a list of ASTs from program source constituting multiple expressions.

    Example:

        >>> parse_multiple("(foo bar) (baz 1 2 3)")
        [['foo', 'bar'], ['baz', 1, 2, 3]]

    """

    source = remove_comments(source)
    return [parse(exp) for exp in split_exps(source)]


def unparse(ast):
    """Turns an AST back into lisp program source"""

    if is_boolean(ast):
        return "#t" if ast else "#f"
    elif is_list(ast):
        if len(ast) > 0 and ast[0] == "quote":
            return "'%s" % unparse(ast[1])
        else:
            return "(%s)" % " ".join([unparse(x) for x in ast])
    else:
        # integers or symbols (or lambdas)
        return str(ast)

########NEW FILE########
__FILENAME__ = repl
# -*- coding: utf-8 -*-

import os
import sys
from os.path import dirname, relpath, join

from .types import LispError, Environment
from .parser import remove_comments
from .interpreter import interpret, interpret_file

# importing this gives readline goodness when running on systems
# where it is supported (i.e. UNIX-y systems)
import readline


def repl():
    """Start the interactive Read-Eval-Print-Loop"""
    print()
    print("                 " + faded("                             \`.    T       "))
    print("    Welcome to   " + faded("   .--------------.___________) \   |    T  "))
    print("   the DIY-lisp  " + faded("   |//////////////|___________[ ]   !  T |  "))
    print("       REPL      " + faded("   `--------------'           ) (      | !  "))
    print("                 " + faded("                              '-'      !    "))
    print(faded("  use ^D to exit"))
    print()

    env = Environment()
    interpret_file(join(dirname(relpath(__file__)), '..', 'stdlib.diy'), env)
    while True:
        try:
            source = read_expression()
            print(interpret(source, env))
        except LispError as e:
            print(colored("!", "red"))
            print(faded(str(e.__class__.__name__) + ":"))
            print(str(e))
        except KeyboardInterrupt:
            msg = "Interupted. " + faded("(Use ^D to exit)")
            print("\n" + colored("! ", "red") + msg)
        except EOFError:
            print(faded("\nBye! o/"))
            sys.exit(0)
        except Exception as e:
            print(colored("! ", "red") + faded("The Python is showing through…"))
            print(faded("  " + str(e.__class__.__name__) + ":"))
            print(str(e))


def read_expression():
    """Read from stdin until we have at least one s-expression"""

    exp = ""
    open_parens = 0
    while True:
        line, parens = read_line("→  " if not exp.strip() else "…  ")
        open_parens += parens
        exp += line
        if exp.strip() and open_parens <= 0:
            break

    return exp.strip()


def read_line(prompt):
    """Return touple of user input line and number of unclosed parens"""

    line = input(colored(prompt, "grey", "bold"))
    line = remove_comments(line + "\n")
    return line, line.count("(") - line.count(")")


def colored(text, color, attr=None):
    attributes = {
        'bold': 1,
        'dark': 2
    }
    colors = {
        'grey': 30,
        'red': 31,
        'green': 32,
        'yellow': 33,
        'blue': 34,
        'magenta': 35,
        'cyan': 36,
        'white': 37,
        'reset': 0
    }
    format = '\033[%dm'

    if os.getenv('ANSI_COLORS_DISABLED'):
        return text

    color = format % colors[color]
    attr = format % attributes[attr] if attr is not None else ""
    reset = format % colors['reset']

    return color + attr + text + reset


def faded(text):
    return colored(text, "grey", attr='bold')

########NEW FILE########
__FILENAME__ = types
# -*- coding: utf-8 -*-

"""
This module holds some types we'll have use for along the way.

It's your job to implement the Closure and Environment types.
The LispError class you can have for free :)
"""


class LispError(Exception):
    """General lisp error class."""
    pass


class Closure:
    def __init__(self, env, params, body):
        raise NotImplementedError("DIY")

    def __str__(self):
        return "<closure/%d>" % len(self.params)


class Environment:
    def __init__(self, variables=None):
        self.variables = variables if variables else {}

    def lookup(self, symbol):
        raise NotImplementedError("DIY")

    def extend(self, variables):
        raise NotImplementedError("DIY")

    def set(self, symbol, value):
        raise NotImplementedError("DIY")

########NEW FILE########
__FILENAME__ = test_1_parsing
# -*- coding: utf-8 -*-

from nose.tools import assert_equals, assert_raises_regexp

from diylisp.parser import parse, unparse
from diylisp.types import LispError


def test_parse_single_symbol():
    """Parsing a single symbol.

    Symbols are represented by text strings. Parsing a single atom should result
    in an AST consisting of only that symbol."""

    assert_equals('foo', parse('foo'))


def test_parse_boolean():
    """Parsing single booleans.

    Booleans are the special symbols #t and #f. In the ASTs they are represented 
    by Pythons True and False, respectively. """

    assert_equals(True, parse('#t'))
    assert_equals(False, parse('#f'))


def test_parse_integer():
    """Parsing single integer.

    Integers are represented in the ASTs as Python ints.

    Tip: String objects have a handy .isdigit() method.
    """

    assert_equals(42, parse('42'))
    assert_equals(1337, parse('1337'))


def test_parse_list_of_symbols():
    """Parsing list of only symbols.

    A list is represented by a number of elements surrounded by parens. Python lists 
    are used to represent lists as ASTs.

    Tip: The useful helper function `find_matching_paren` is already provided in
    `parse.py`.
    """

    assert_equals(['foo', 'bar', 'baz'], parse('(foo bar baz)'))
    assert_equals([], parse('()'))


def test_parse_list_of_mixed_types():
    """Parsing a list containing different types.

    When parsing lists, make sure each of the sub-expressions are also parsed 
    properly."""

    assert_equals(['foo', True, 123], parse('(foo #t 123)'))


def test_parse_on_nested_list():
    """Parsing should also handle nested lists properly."""

    program = '(foo (bar ((#t)) x) (baz y))'
    ast = ['foo',
           ['bar', [[True]], 'x'],
           ['baz', 'y']]
    assert_equals(ast, parse(program))


def test_parse_exception_missing_paren():
    """The proper exception should be raised if the expresions is incomplete."""

    with assert_raises_regexp(LispError, 'Incomplete expression'):
        parse('(foo (bar x y)')


def test_parse_exception_extra_paren():
    """Another exception is raised if the expression is too large.

    The parse function expects to receive only one single expression. Anything
    more than this, should result in the proper exception."""

    with assert_raises_regexp(LispError, 'Expected EOF'):
        parse('(foo (bar x y)))')


def test_parse_with_extra_whitespace():
    """Excess whitespace should be removed."""

    program = """

       (program    with   much        whitespace)
    """

    expected_ast = ['program', 'with', 'much', 'whitespace']
    assert_equals(expected_ast, parse(program))


def test_parse_comments():
    """All comments should be stripped away as part of the parsing."""

    program = """
    ;; this first line is a comment
    (define variable
        ; here is another comment
        (if #t 
            42 ; inline comment!
            (something else)))
    """
    expected_ast = ['define', 'variable',
                    ['if', True,
                     42,
                     ['something', 'else']]]
    assert_equals(expected_ast, parse(program))


def test_parse_larger_example():
    """Test a larger example to check that everything works as expected"""

    program = """
        (define fact 
        ;; Factorial function
        (lambda (n) 
            (if (<= n 1) 
                1 ; Factorial of 0 is 1, and we deny 
                  ; the existence of negative numbers
                (* n (fact (- n 1))))))
    """
    ast = ['define', 'fact',
           ['lambda', ['n'],
            ['if', ['<=', 'n', 1],
             1,
             ['*', 'n', ['fact', ['-', 'n', 1]]]]]]
    assert_equals(ast, parse(program))

## The following tests checks that quote expansion works properly


def test_expand_single_quoted_symbol():
    """Quoting is a shorthand syntax for calling the `quote` form.

    Examples:

        'foo -> (quote foo)
        '(foo bar) -> (quote (foo bar))

    """
    assert_equals(["foo", ["quote", "nil"]], parse("(foo 'nil)"))


def test_nested_quotes():
    assert_equals(["quote", ["quote", ["quote", ["quote", "foo"]]]], parse("''''foo"))


def test_expand_crazy_quote_combo():
    """One final test to see that quote expansion works."""

    source = "'(this ''''(makes ''no) 'sense)"
    assert_equals(source, unparse(parse(source)))

########NEW FILE########
__FILENAME__ = test_2_evaluating_simple_expressions
# -*- coding: utf-8 -*-

from nose.tools import assert_equals, assert_raises

from diylisp.types import LispError
from diylisp.types import Environment
from diylisp.evaluator import evaluate
from diylisp.parser import parse

"""
We will start by implementing evaluation of simple expressions.
"""


def test_evaluating_boolean():
    """Booleans should evaluate to themselves."""
    assert_equals(True, evaluate(True, Environment()))
    assert_equals(False, evaluate(False, Environment()))


def test_evaluating_integer():
    """...and so should integers."""
    assert_equals(42, evaluate(42, Environment()))


def test_evaluating_quote():
    """When a call is done to the `quote` form, the argument should be returned without 
    being evaluated.

    (quote foo) -> foo
    """

    assert_equals("foo", evaluate(["quote", "foo"], Environment()))
    assert_equals([1, 2, False], evaluate(["quote", [1, 2, False]], Environment()))


def test_evaluating_atom_function():
    """The `atom` form is used to determine whether an expression is an atom.

    Atoms are expressions that are not list, i.e. integers, booleans or symbols.
    Remember that the argument to `atom` must be evaluated before the check is done.
    """

    assert_equals(True, evaluate(["atom", True], Environment()))
    assert_equals(True, evaluate(["atom", False], Environment()))
    assert_equals(True, evaluate(["atom", 42], Environment()))
    assert_equals(True, evaluate(["atom", ["quote", "foo"]], Environment()))
    assert_equals(False, evaluate(["atom", ["quote", [1, 2]]], Environment()))


def test_evaluating_eq_function():
    """The `eq` form is used to check whether two expressions are the same atom."""

    assert_equals(True, evaluate(["eq", 1, 1], Environment()))
    assert_equals(False, evaluate(["eq", 1, 2], Environment()))

    # From this point, the ASTs might sometimes be too long or cummbersome to
    # write down explicitly, and we'll use `parse` to make them for us.
    # Remember, if you need to have a look at exactly what is passed to `evaluate`, 
    # just add a print statement in the test (or in `evaluate`).

    assert_equals(True, evaluate(parse("(eq 'foo 'foo)"), Environment()))
    assert_equals(False, evaluate(parse("(eq 'foo 'bar)"), Environment()))

    # Lists are never equal, because lists are not atoms
    assert_equals(False, evaluate(parse("(eq '(1 2 3) '(1 2 3))"), Environment()))


def test_basic_math_operators():
    """To be able to do anything useful, we need some basic math operators.

    Since we only operate with integers, `/` must represent integer division.
    `mod` is the modulo operator.
    """

    assert_equals(4, evaluate(["+", 2, 2], Environment()))
    assert_equals(1, evaluate(["-", 2, 1], Environment()))
    assert_equals(3, evaluate(["/", 6, 2], Environment()))
    assert_equals(3, evaluate(["/", 7, 2], Environment()))
    assert_equals(6, evaluate(["*", 2, 3], Environment()))
    assert_equals(1, evaluate(["mod", 7, 2], Environment()))
    assert_equals(True, evaluate([">", 7, 2], Environment()))
    assert_equals(False, evaluate([">", 2, 7], Environment()))
    assert_equals(False, evaluate([">", 7, 7], Environment()))


def test_math_operators_only_work_on_numbers():
    """The math functions should only allow numbers as arguments."""

    with assert_raises(LispError):
        evaluate(parse("(+ 1 'foo)"), Environment())
    with assert_raises(LispError):
        evaluate(parse("(- 1 'foo)"), Environment())
    with assert_raises(LispError):
        evaluate(parse("(/ 1 'foo)"), Environment())
    with assert_raises(LispError):
        evaluate(parse("(mod 1 'foo)"), Environment())

########NEW FILE########
__FILENAME__ = test_3_evaluating_complex_expressions
# -*- coding: utf-8 -*-

from nose.tools import assert_equals

from diylisp.types import Environment
from diylisp.evaluator import evaluate
from diylisp.parser import parse

def test_nested_expression():
    """Remember, functions should evaluate their arguments. 

    (Except `quote` and `if`, that is, which aren't really functions...) Thus, 
    nested expressions should work just fine without any further work at this 
    point.

    If this test is failing, make sure that `+`, `>` and so on is evaluating 
    their arguments before operating on them."""

    nested_expression = parse("(eq #f (> (- (+ 1 3) (* 2 (mod 7 4))) 4))")
    assert_equals(True, evaluate(nested_expression, Environment()))


def test_basic_if_statement():
    """If statements are the basic control structures.

    The `if` should first evaluate its first argument. If this evaluates to true, then
    the second argument is evaluated and returned. Otherwise the third and last argument
    is evaluated and returned instead."""

    if_expression = parse("(if #t 42 1000)")
    assert_equals(42, evaluate(if_expression, Environment()))
    if_expression = parse("(if #f 42 1000)")
    assert_equals(1000, evaluate(if_expression, Environment()))
    if_expression = parse("(if #t #t #f)")
    assert_equals(True, evaluate(if_expression, Environment()))


def test_that_only_correct_branch_is_evaluated():
    """The branch of the if statement that is discarded should never be evaluated."""

    if_expression = parse("(if #f (this should not be evaluated) 42)")
    assert_equals(42, evaluate(if_expression, Environment()))

def test_if_with_sub_expressions():
    """A final test with a more complex if expression.
    This test should already be passing if the above ones are."""

    if_expression = parse("""
        (if (> 1 2)
            (- 1000 1)
            (+ 40 (- 3 1)))
    """)
    assert_equals(42, evaluate(if_expression, Environment()))

########NEW FILE########
__FILENAME__ = test_4_working_with_variables_and_environments
# -*- coding: utf-8 -*-

from nose.tools import assert_equals, assert_raises_regexp

from diylisp.types import LispError, Environment
from diylisp.evaluator import evaluate
from diylisp.parser import parse

"""
Before we go on to evaluating programs using variables, we need to implement
an envionment to store them in.

It is time to fill in the blanks in the `Environment` class located in `types.py`.
"""


def test_simple_lookup():
    """An environment should store variables and provide lookup."""

    env = Environment({"var": 42})
    assert_equals(42, env.lookup("var"))


def test_lookup_on_missing_raises_exception():
    """When looking up an undefined symbol, an error should be raised.

    The error message should contain the relevant symbol, and inform that it has 
    not been defined."""

    with assert_raises_regexp(LispError, "my-missing-var"):
        empty_env = Environment()
        empty_env.lookup("my-missing-var")


def test_lookup_from_inner_env():
    """The `extend` function returns a new environment extended with more bindings."""

    env = Environment({"foo": 42})
    env = env.extend({"bar": True})
    assert_equals(42, env.lookup("foo"))
    assert_equals(True, env.lookup("bar"))


def test_lookup_deeply_nested_var():
    """Extending overwrites old bindings to the same variable name."""

    env = Environment({"a": 1}).extend({"b": 2}).extend({"c": 3}).extend({"foo": 100})
    assert_equals(100, env.lookup("foo"))


def test_extend_returns_new_environment():
    """The extend method should create a new environment, leaving the old one unchanged."""

    env = Environment({"foo": 1})
    extended = env.extend({"foo": 2})

    assert_equals(1, env.lookup("foo"))
    assert_equals(2, extended.lookup("foo"))


def test_set_changes_environment_in_place():
    """When calling `set` the environment should be updated"""

    env = Environment()
    env.set("foo", 2)
    assert_equals(2, env.lookup("foo"))


def test_redefine_variables_illegal():
    """Variables can only be defined once.

    Setting a variable in an environment where it is already defined should result
    in an appropriate error.
    """

    env = Environment({"foo": 1})
    with assert_raises_regexp(LispError, "already defined"):
        env.set("foo", 2)


"""
With the `Environment` working, it's time to implement evaluation of expressions 
with variables.
"""


def test_evaluating_symbol():
    """Symbols (other than #t and #f) are treated as variable references.

    When evaluating a symbol, the corresponding value should be looked up in the 
    environment."""

    env = Environment({"foo": 42})
    assert_equals(42, evaluate("foo", env))


def test_lookup_missing_variable():
    """Referencing undefined variables should raise an appropriate exception.

    This test should already be working if you implemented the environment correctly."""

    with assert_raises_regexp(LispError, "my-var"):
        evaluate("my-var", Environment())


def test_define():
    """Test of simple define statement.

    The `define` form is used to define new bindings in the environment.
    A `define` call should result in a change in the environment. What you
    return from evaluating the definition is not important (although it 
    affects what is printed in the REPL)."""

    env = Environment()
    evaluate(parse("(define x 1000)"), env)
    assert_equals(1000, env.lookup("x"))


def test_define_with_wrong_number_of_arguments():
    """Defines should have exactly two arguments, or raise an error"""

    with assert_raises_regexp(LispError, "Wrong number of arguments"):
        evaluate(parse("(define x)"), Environment())

    with assert_raises_regexp(LispError, "Wrong number of arguments"):
        evaluate(parse("(define x 1 2)"), Environment())


def test_define_with_nonsymbol_as_variable():
    """Defines require the first argument to be a symbol."""

    with assert_raises_regexp(LispError, "non-symbol"):
        evaluate(parse("(define #t 42)"), Environment())


def test_variable_lookup_after_define():
    """Test define and lookup variable in same environment.

    This test should already be working when the above ones are passing."""

    env = Environment()
    evaluate(parse("(define foo (+ 2 2))"), env)
    assert_equals(4, evaluate("foo", env))

########NEW FILE########
__FILENAME__ = test_5_adding_functions_to_the_mix
# -*- coding: utf-8 -*-

from nose.tools import assert_equals, assert_raises_regexp, \
    assert_raises, assert_true, assert_is_instance

from diylisp.ast import is_list
from diylisp.evaluator import evaluate
from diylisp.parser import parse
from diylisp.types import Closure, LispError, Environment

"""
This part is all about defining and using functions.

We'll start by implementing the `lambda` form which is used to create function closures.
"""


def test_lambda_evaluates_to_lambda():
    """The lambda form should evaluate to a Closure"""

    ast = ["lambda", [], 42]
    closure = evaluate(ast, Environment())
    assert_is_instance(closure, Closure)


def test_lambda_closure_keeps_defining_env():
    """The closure should keep a copy of the environment where it was defined.

    Once we start calling functions later, we'll need access to the environment
    from when the function was created in order to resolve all free variables."""

    env = Environment({"foo": 1, "bar": 2})
    ast = ["lambda", [], 42]
    closure = evaluate(ast, env)
    assert_equals(closure.env, env)


def test_lambda_closure_holds_function():
    """The closure contains the parameter list and function body too."""

    closure = evaluate(parse("(lambda (x y) (+ x y))"), Environment())

    assert_equals(["x", "y"], closure.params)
    assert_equals(["+", "x", "y"], closure.body)


def test_lambda_arguments_are_lists():
    """The parameters of a `lambda` should be a list."""

    closure = evaluate(parse("(lambda (x y) (+ x y))"), Environment())
    assert_true(is_list(closure.params))

    with assert_raises(LispError):
        evaluate(parse("(lambda not-a-list (body of fn))"), Environment())


def test_lambda_number_of_arguments():
    """The `lambda` form should expect exactly two arguments."""

    with assert_raises_regexp(LispError, "number of arguments"):
        evaluate(parse("(lambda (foo) (bar) (baz))"), Environment())


def test_defining_lambda_with_error_in_body():
    """The function body should not be evaluated when the lambda is defined.

    The call to `lambda` should return a function closure holding, among other things
    the function body. The body should not be evaluated before the function is called."""

    ast = parse("""
            (lambda (x y)
                (function body ((that) would never) work))
    """)
    assert_is_instance(evaluate(ast, Environment()), Closure)


"""
Now that we have the `lambda` form implemented, let's see if we can call some functions.

When evaluating ASTs which are lists, if the first element isn't one of the special forms
we have been working with so far, it is a function call. The first element of the list is
the function, and the rest of the elements are arguments.
"""


def test_evaluating_call_to_closure():
    """The first case we'll handle is when the AST is a list with an actual closure
    as the first element.

    In this first test, we'll start with a closure with no arguments and no free
    variables. All we need to do is to evaluate and return the function body."""

    closure = evaluate(parse("(lambda () (+ 1 2))"), Environment())
    ast = [closure]
    result = evaluate(ast, Environment())
    assert_equals(3, result)


def test_evaluating_call_to_closure_with_arguments():
    """The function body must be evaluated in an environment where the parameters are bound.

    Create an environment where the function parameters (which are stored in the closure)
    are bound to the actual argument values in the function call. Use this environment
    when evaluating the function body."""

    env = Environment()
    closure = evaluate(parse("(lambda (a b) (+ a b))"), env)
    ast = [closure, 4, 5]

    assert_equals(9, evaluate(ast, env))


def test_call_to_function_should_evaluate_arguments():
    """Call to function should evaluate all arguments.

    When a function is applied, the arguments should be evaluated before being bound
    to the parameter names."""

    env = Environment()
    closure = evaluate(parse("(lambda (a) (+ a 5))"), env)
    ast = [closure, parse("(if #f 0 (+ 10 10))")]

    assert_equals(25, evaluate(ast, env))


def test_evaluating_call_to_closure_with_free_variables():
    """The body should be evaluated in the environment from the closure.

    The function's free variables, i.e. those not specified as part of the parameter list,
    should be looked up in the environment from where the function was defined. This is
    the environment included in the closure. Make sure this environment is used when
    evaluating the body."""

    closure = evaluate(parse("(lambda (x) (+ x y))"), Environment({"y": 1}))
    ast = [closure, 0]
    result = evaluate(ast, Environment({"y": 2}))
    assert_equals(1, result)


"""
Okay, now we're able to evaluate ASTs with closures as the first element. But normally
the closures don't just happen to be there all by themselves. Generally we'll find some
expression, evaluate it to a closure, and then evaluate a new AST with the closure just
like we did above.

(some-exp arg1 arg2 ...) -> (closure arg1 arg2 ...) -> result-of-function-call

"""


def test_calling_very_simple_function_in_environment():
    """A call to a symbol corresponds to a call to its value in the environment.

    When a symbol is the first element of the AST list, it is resolved to its value in
    the environment (which should be a function closure). An AST with the variables
    replaced with its value should then be evaluated instead."""

    env = Environment()
    evaluate(parse("(define add (lambda (x y) (+ x y)))"), env)
    assert_is_instance(env.lookup("add"), Closure)

    result = evaluate(parse("(add 1 2)"), env)
    assert_equals(3, result)


def test_calling_lambda_directly():
    """It should be possible to define and call functions directly.

    A lambda definition in the call position of an AST should be evaluated, and then
    evaluated as before."""

    ast = parse("((lambda (x) x) 42)")
    result = evaluate(ast, Environment())
    assert_equals(42, result)


def test_calling_complex_expression_which_evaluates_to_function():
    """Actually, all ASTs that are not atoms should be evaluated and then called.

    In this test, a call is done to the if-expression. The `if` should be evaluated,
    which will result in a `lambda` expression. The lambda is evaluated, giving a
    closure. The result is an AST with a `closure` as the first element, which we
    already know how to evaluate."""

    ast = parse("""
        ((if #f
             wont-evaluate-this-branch
             (lambda (x) (+ x y)))
         2)
    """)
    env = Environment({'y': 3})
    assert_equals(5, evaluate(ast, env))


"""
Now that we have the happy cases working, let's see what should happen when
function calls are done incorrectly.
"""


def test_calling_atom_raises_exception():
    """A function call to a non-function should result in an error."""

    with assert_raises_regexp(LispError, "not a function"):
        evaluate(parse("(#t 'foo 'bar)"), Environment())
    with assert_raises_regexp(LispError, "not a function"):
        evaluate(parse("(42)"), Environment())


def test_make_sure_arguments_to_functions_are_evaluated():
    """The arguments passed to functions should be evaluated

    We should accept parameters that are produced through function
    calls. If you are seeing stack overflows, e.g.

    RuntimeError: maximum recursion depth exceeded while calling a Python object

    then you should double-check that you are properly evaluating the passed
    function arguments."""

    env = Environment()
    res = evaluate(parse("((lambda (x) x) (+ 1 2))"), env)
    assert_equals(res, 3)


def test_calling_with_wrong_number_of_arguments():
    """Functions should raise exceptions when called with wrong number of arguments."""

    env = Environment()
    evaluate(parse("(define fn (lambda (p1 p2) 'whatwever))"), env)
    error_msg = "wrong number of arguments, expected 2 got 3"
    with assert_raises_regexp(LispError, error_msg):
        evaluate(parse("(fn 1 2 3)"), env)


"""
One final test to see that recursive functions are working as expected.
The good news: this should already be working by now :)
"""


def test_calling_function_recursively():
    """Tests that a named function is included in the environment
    where it is evaluated."""

    env = Environment()
    evaluate(parse("""
        (define my-fn
            ;; A meaningless, but recursive, function
            (lambda (x)
                (if (eq x 0)
                    42
                    (my-fn (- x 1)))))
    """), env)

    assert_equals(42, evaluate(parse("(my-fn 0)"), env))
    assert_equals(42, evaluate(parse("(my-fn 10)"), env))

########NEW FILE########
__FILENAME__ = test_6_working_with_lists
# -*- coding: utf-8 -*-

from nose.tools import assert_equals, assert_raises

from diylisp.evaluator import evaluate
from diylisp.parser import parse
from diylisp.types import LispError, Environment


def test_creating_lists_by_quoting():
    """One way to create lists is by quoting.

    We have already implemented `quote` so this test should already be
    passing.

    The reason we need to use `quote` here is that otherwise the expression would
    be seen as a call to the first element -- `1` in this case, which obviously isn't
    even a function."""

    assert_equals(parse("(1 2 3 #t)"),
                  evaluate(parse("'(1 2 3 #t)"), Environment()))


def test_creating_list_with_cons():
    """The `cons` functions prepends an element to the front of a list."""

    result = evaluate(parse("(cons 0 '(1 2 3))"), Environment())
    assert_equals(parse("(0 1 2 3)"), result)


def test_creating_longer_lists_with_only_cons():
    """`cons` needs to evaluate it's arguments.

    Like all the other special forms and functions in our language, `cons` is 
    call-by-value. This means that the arguments must be evaluated before we 
    create the list with their values."""

    result = evaluate(parse("(cons 3 (cons (- 4 2) (cons 1 '())))"), Environment())
    assert_equals(parse("(3 2 1)"), result)


def test_getting_first_element_from_list():
    """`head` extracts the first element of a list."""

    assert_equals(1, evaluate(parse("(head '(1 2 3 4 5))"), Environment()))


def test_getting_first_element_from_empty_list():
    """If the list is empty there is no first element, and `head should raise an error."""

    with assert_raises(LispError):
        evaluate(parse("(head (quote ()))"), Environment())


def test_getting_tail_of_list():
    """`tail` returns the tail of the list.

    The tail is the list retained after removing the first element."""

    assert_equals([2, 3], evaluate(parse("(tail '(1 2 3))"), Environment()))


def test_checking_whether_list_is_empty():
    """The `empty` form checks whether or not a list is empty."""

    assert_equals(False, evaluate(parse("(empty '(1 2 3))"), Environment()))
    assert_equals(False, evaluate(parse("(empty '(1))"), Environment()))

    assert_equals(True, evaluate(parse("(empty '())"), Environment()))
    assert_equals(True, evaluate(parse("(empty (tail '(1)))"), Environment()))

########NEW FILE########
__FILENAME__ = test_7_using_the_language
# -*- coding: utf-8 -*-

from nose.tools import assert_equals
from os.path import dirname, relpath, join

from diylisp.interpreter import interpret, interpret_file
from diylisp.types import Environment

env = Environment()
path = join(dirname(relpath(__file__)), '..', 'stdlib.diy')
interpret_file(path, env)

"""
Consider these tests as suggestions for what a standard library for
your language could contain. Each test function tests the implementation
of one stdlib function.

Put the implementation in the file `stdlib.diy` at the root directory
of the repository. The first function, `not` is already defined for you.
It's your job to create the rest, or perhaps somthing completely different?

Anything you put in `stdlib.diy` is also available from the REPL, so feel
free to test things out there.

    $ ./repl 
    →  (not #t)
    #f

PS: Note that in these tests, `interpret` is used. In addition to parsing 
and evaluating, it "unparses" the result, hence strings such as "#t" as the 
expected result instead of `True`.
"""


def test_not():
    assert_equals("#t", interpret('(not #f)', env))
    assert_equals("#f", interpret('(not #t)', env))


def test_or():
    assert_equals("#f", interpret('(or #f #f)', env))
    assert_equals("#t", interpret('(or #t #f)', env))
    assert_equals("#t", interpret('(or #f #t)', env))
    assert_equals("#t", interpret('(or #t #t)', env))


def test_and():
    assert_equals("#f", interpret('(and #f #f)', env))
    assert_equals("#f", interpret('(and #t #f)', env))
    assert_equals("#f", interpret('(and #f #t)', env))
    assert_equals("#t", interpret('(and #t #t)', env))


def test_xor():
    assert_equals("#f", interpret('(xor #f #f)', env))
    assert_equals("#t", interpret('(xor #t #f)', env))
    assert_equals("#t", interpret('(xor #f #t)', env))
    assert_equals("#f", interpret('(xor #t #t)', env))


def test_greater_or_equal():
    assert_equals("#f", interpret('(>= 1 2)', env))
    assert_equals("#t", interpret('(>= 2 2)', env))
    assert_equals("#t", interpret('(>= 2 1)', env))


def test_less_or_equal():
    assert_equals("#t", interpret('(<= 1 2)', env))
    assert_equals("#t", interpret('(<= 2 2)', env))
    assert_equals("#f", interpret('(<= 2 1)', env))


def test_less_than():
    assert_equals("#t", interpret('(< 1 2)', env))
    assert_equals("#f", interpret('(< 2 2)', env))
    assert_equals("#f", interpret('(< 2 1)', env))


def test_sum():
    assert_equals("5", interpret("(sum '(1 1 1 1 1))", env))
    assert_equals("10", interpret("(sum '(1 2 3 4))", env))
    assert_equals("0", interpret("(sum '())", env))


def test_length():
    assert_equals("5", interpret("(length '(1 2 3 4 5))", env))
    assert_equals("3", interpret("(length '(#t '(1 2 3) 'foo-bar))", env))
    assert_equals("0", interpret("(length '())", env))


def test_append():
    assert_equals("(1 2 3 4 5)", interpret("(append '(1 2) '(3 4 5))", env))
    assert_equals("(#t #f 'maybe)", interpret("(append '(#t) '(#f 'maybe))", env))
    assert_equals("()", interpret("(append '() '())", env))


def test_filter():
    interpret("""
        (define even
            (lambda (x)
                (eq (mod x 2) 0)))
    """, env)
    assert_equals("(2 4 6)", interpret("(filter even '(1 2 3 4 5 6))", env))


def test_map():
    interpret("""
        (define inc
            (lambda (x) (+ 1 x)))
    """, env)
    assert_equals("(2 3 4)", interpret("(map inc '(1 2 3))", env))


def test_reverse():
    assert_equals("(4 3 2 1)", interpret("(reverse '(1 2 3 4))", env))
    assert_equals("()", interpret("(reverse '())", env))


def test_range():
    assert_equals("(1 2 3 4 5)", interpret("(range 1 5)", env))
    assert_equals("(1)", interpret("(range 1 1)", env))
    assert_equals("()", interpret("(range 2 1)", env))


def test_sort():
    assert_equals("(1 2 3 4 5 6 7)",
                  interpret("(sort '(6 3 7 2 4 1 5))", env))
    assert_equals("()", interpret("'()", env))

########NEW FILE########
__FILENAME__ = test_provided_code
# -*- coding: utf-8 -*-

from nose.tools import assert_equals, assert_raises_regexp, assert_raises

from diylisp.parser import unparse, find_matching_paren
from diylisp.types import LispError

"""
This module contains a few tests for the code provided for part 1.
All tests here should already pass, and should be of no concern to
you as a workshop attendee.
"""

## Tests for find_matching_paren function in parser.py


def test_find_matching_paren():
    source = "(foo (bar) '(this ((is)) quoted))"
    assert_equals(32, find_matching_paren(source, 0))
    assert_equals(9, find_matching_paren(source, 5))


def test_find_matching_empty_parens():
    assert_equals(1, find_matching_paren("()", 0))


def test_find_matching_paren_throws_exception_on_bad_initial_position():
    """If asked to find closing paren from an index where there is no opening
    paren, the function should raise an error"""

    with assert_raises(AssertionError):
        find_matching_paren("string without parens", 4)


def test_find_matching_paren_throws_exception_on_no_closing_paren():
    """The function should raise error when there is no matching paren to be found"""

    with assert_raises_regexp(LispError, "Incomplete expression"):
        find_matching_paren("string (without closing paren", 7)

## Tests for unparse in parser.py


def test_unparse_atoms():
    assert_equals("123", unparse(123))
    assert_equals("#t", unparse(True))
    assert_equals("#f", unparse(False))
    assert_equals("foo", unparse("foo"))


def test_unparse_list():
    assert_equals("((foo bar) baz)", unparse([["foo", "bar"], "baz"]))


def test_unparse_quotes():
    assert_equals("''(foo 'bar '(1 2))", unparse(
        ["quote", ["quote", ["foo", ["quote", "bar"], ["quote", [1, 2]]]]]))


def test_unparse_bool():
    assert_equals("#t", unparse(True))
    assert_equals("#f", unparse(False))


def test_unparse_int():
    assert_equals("1", unparse(1))
    assert_equals("1337", unparse(1337))
    assert_equals("-42", unparse(-42))


def test_unparse_symbol():
    assert_equals("+", unparse("+"))
    assert_equals("foo", unparse("foo"))
    assert_equals("lambda", unparse("lambda"))


def test_unparse_another_list():
    assert_equals("(1 2 3)", unparse([1, 2, 3]))
    assert_equals("(if #t 42 #f)",
                  unparse(["if", True, 42, False]))


def test_unparse_other_quotes():
    assert_equals("'foo", unparse(["quote", "foo"]))
    assert_equals("'(1 2 3)",
                  unparse(["quote", [1, 2, 3]]))


def test_unparse_empty_list():
    assert_equals("()", unparse([]))

########NEW FILE########
__FILENAME__ = test_sanity_checks
# -*- coding: utf-8 -*-

from nose.tools import assert_equals

from diylisp.interpreter import interpret
from diylisp.types import Environment


def test_gcd():
    """Tests Greates Common Dividor (GCD)."""

    program = """
        (define gcd
            (lambda (a b)
                (if (eq b 0)
                    a 
                    (gcd b (mod a b)))))
    """

    env = Environment()
    interpret(program, env)

    assert_equals("6", interpret("(gcd 108 30)", env))
    assert_equals("1", interpret("(gcd 17 5)", env))

########NEW FILE########
