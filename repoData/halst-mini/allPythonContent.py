__FILENAME__ = mini
import operator as op

from parsimonious.grammar import Grammar


class Mini(object):

    def __init__(self, env={}):
        env['sum'] = lambda *args: sum(args)
        self.env = env

    def parse(self, source):
        grammar = '\n'.join(v.__doc__ for k, v in vars(self.__class__).items()
                      if '__' not in k and hasattr(v, '__doc__') and v.__doc__)
        return Grammar(grammar)['program'].parse(source)

    def eval(self, source):
        node = self.parse(source) if isinstance(source, str) else source
        method = getattr(self, node.expr_name, lambda node, children: children)
        if node.expr_name in ['ifelse', 'func']:
            return method(node)
        return method(node, [self.eval(n) for n in node])

    def program(self, node, children):
        'program = expr*'
        return children

    def expr(self, node, children):
        'expr = _ (func / ifelse / call / infix / assignment / number / name) _'
        return children[1][0]

    def func(self, node):
        'func = "(" parameters ")" _ "->" expr'
        _, params, _, _, _, expr = node
        params = map(self.eval, params)
        def func(*args):
            env = dict(self.env.items() + zip(params, args))
            return Mini(env).eval(expr)
        return func

    def parameters(self, node, children):
        'parameters = lvalue*'
        return children

    def ifelse(self, node):
        'ifelse = "if" expr "then" expr "else" expr'
        _, cond, _, cons, _, alt = node
        return self.eval(cons) if self.eval(cond) else self.eval(alt)

    def call(self, node, children):
        'call = name "(" arguments ")"'
        name, _, arguments, _ = children
        return name(*arguments)

    def arguments(self, node, children):
        'arguments = expr*'
        return children

    def infix(self, node, children):
        'infix = "(" expr operator expr ")"'
        _, expr1, operator, expr2, _ = children
        return operator(expr1, expr2)

    def operator(self, node, children):
        'operator = "+" / "-" / "*" / "/"'
        operators = {'+': op.add, '-': op.sub, '*': op.mul, '/': op.div}
        return operators[node.text]

    def assignment(self, node, children):
        'assignment = lvalue "=" expr'
        lvalue, _, expr = children
        self.env[lvalue] = expr
        return expr

    def lvalue(self, node, children):
        'lvalue = ~"[a-z]+" _'
        return node.text.strip()

    def name(self, node, children):
        'name = ~"[a-z]+" _'
        return self.env.get(node.text.strip(), -1)

    def number(self, node, children):
        'number = ~"[0-9]+"'
        return int(node.text)

    def _(self, node, children):
        '_ = ~"\s*"'

########NEW FILE########
__FILENAME__ = test_mini
from mini import Mini


def test_numbers():
    assert Mini().eval('') == []
    assert Mini().eval('42') == [42]
    assert Mini().eval('42 12') == [42, 12]


def test_variables():
    assert Mini({'a': 42}).eval('a') == [42]
    assert Mini().eval('a = 2 \n a') == [2, 2]


def test_operators():
    assert Mini().eval('(42 + 2)') == [44]
    assert Mini().eval('(42 + (2 * 4))') == [50]


def test_functions():
    assert Mini().eval('sum(10 20)') == [30]
    assert Mini().eval('sum(10 20 30)') == [60]


def test_if():
    assert Mini().eval('if 1 then 42 else 12') == [42]
    assert Mini().eval('if 0 then 42 else 12') == [12]


def test_lambdas():
    assert Mini().eval('addten = (b) -> (b + 10) \n addten(2)')[-1] == 12
    source = 'x = 10 \n addx = (a) -> (a + x) \n addx(2)'
    assert Mini().eval(source)[-1] == 12
    assert Mini().eval('add = (a b) -> (a + b) \n add(42 12)')[-1] == 54


def test_factorial():
    # 0 => 1
    #   => n * (n - 1)!
    source = '''
        factorial = (n) ->
            if n then
                (n * factorial((n - 1)))
            else
                1
        factorial(0)
        factorial(5)
    '''
    assert Mini().eval(source)[1:] == [1, 120]


# github.com/halst/mini

########NEW FILE########
